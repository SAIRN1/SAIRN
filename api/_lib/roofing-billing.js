// api/_lib/roofing-billing.js
// SAIRNroofing Phase 4b -- estimate -> proposal -> invoice.
//
// PURE -- no I/O, no LLM. Money arithmetic only.
//
// ── THE ONE THING THIS PHASE MUST NOT GET WRONG ──────────────────────────
// A PROPOSAL SNAPSHOTS THE PRICE. It does not reference the live estimate on
// rf_jobs.data.estimate. If it did, editing the estimate after sending would
// retroactively change what the customer was told they were quoted -- and
// neither party would see it happen. sql/sairnroofing_claims_schema.sql
// already makes this argument about tear-off photos ("evidence that can be
// edited after the fact is not evidence"); a price you put in front of a
// customer is the same kind of fact.
//
// So rf_proposals is APPEND-ONLY and every issued row carries its own copy of
// the line items. Re-pricing produces a NEW proposal, which is also what
// honestly happened.
//
// ── WHAT IS DERIVED AND THEREFORE NEVER STORED ───────────────────────────
// The invoice BALANCE. Same discipline as roofing-claims.js's money_summary
// and the 3c supplement worksheet: recomputed on every read from the stored
// line items and the stored payments, so it cannot drift from, or overwrite,
// the real figures. A stored balance is a number that was true once.
//
// Totals ARE recomputed server-side from quantity x unit_price rather than
// trusted from the client -- the same rule the Phase 2 estimate block already
// applies, so a client-side arithmetic bug cannot save a wrong total.
//
// ── NOTHING IS DEFAULTED ─────────────────────────────────────────────────
// No tax rate, no overhead, no profit margin. The estimate block refuses to
// invent a per-square-foot cost and calls that "exactly the fabricated-figure
// class Guardian checks for"; a tax rate guessed from the job's state is the
// same error wearing a different hat. Roofing tax genuinely turns on whether
// the work is a capital improvement, which is a question about the job and the
// jurisdiction, not something a default can answer.
//
// ── FIELD NAMES ARE THE STANDARD EXPORT ONES, ON PURPOSE ─────────────────
// description / quantity / unit_price / amount / subtotal / tax / total /
// terms / bill_to, rather than the app's internal label/qty/unit_cost. An
// accounting export is out of scope for 4b (recorded as a closed decision),
// but naming these the SAIRN way now would buy a relabelling job later for
// nothing. Same reasoning as SAIRNdental capturing location_id early.

'use strict';

// A proposal's life. Append-only: each is a row, never an edit.
const PROPOSAL_EVENTS = ['issued', 'accepted', 'declined', 'withdrawn'];

// An invoice header is mutable while it is a draft. 'void' rather than delete:
// there is no delete path in this app and a voided invoice is a real part of
// the record a bookkeeper needs to see.
const INVOICE_STATUSES = ['draft', 'issued', 'paid', 'void'];

// How an acceptance was captured. Michael's call 2026-08-25: a signature is
// OPTIONAL per proposal, because acceptance genuinely varies by job size and
// by whether the job is insurance-linked. Both paths get the same append-only
// discipline; the difference is only how strong the evidence is.
const ACCEPTANCE_METHODS = ['signature', 'in_person', 'email', 'phone', 'other'];

const PAYMENT_METHODS = ['check', 'cash', 'card', 'ach', 'insurance_check', 'other'];

function isNum(n) { return typeof n === 'number' && isFinite(n); }
// null/''/undefined are ABSENT, not zero. Number(null) is 0, so the naive
// version treated "no tax given" as "an explicit tax of 0" and reported
// tax_basis 'amount' on an invoice that had no tax input at all. Caught by the
// suite below.
function num(v) { if (v === null || v === undefined || v === '') return null; const n = Number(v); return isNum(n) ? n : null; }
function str(v) { return typeof v === 'string' ? v.trim() : ''; }
function isDate(s) { return typeof s === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(s); }
function money(n) { return Math.round(n * 100) / 100; }

// Recompute every line from quantity x unit_price. A client-supplied `amount`
// is IGNORED, not validated -- validating it would mean deciding what to do
// when it disagrees, and there is only one right answer.
function normalizeLineItems(items) {
  return (Array.isArray(items) ? items : []).map(function (it) {
    const quantity = num(it && it.quantity) || 0;
    const unitPrice = num(it && it.unit_price) || 0;
    return {
      description: String((it && it.description) || '').slice(0, 300),
      quantity: quantity,
      unit: String((it && it.unit) || '').slice(0, 40),
      unit_price: unitPrice,
      amount: money(quantity * unitPrice)
    };
  });
}

// Subtotal, tax and total from the lines and a caller-supplied rate or amount.
// tax_rate is a PERCENT (7.5 means 7.5%). If both a rate and an explicit
// amount are given the explicit amount wins and the fact is reported --
// silently preferring one would hide a real disagreement in the input.
function computeTotals(lineItems, taxRate, taxAmount) {
  const lines = normalizeLineItems(lineItems);
  const subtotal = money(lines.reduce(function (s, l) { return s + l.amount; }, 0));
  const rate = num(taxRate);
  const explicit = num(taxAmount);
  const problems = [];
  let tax = 0;
  let basis = 'none';
  if (explicit !== null) {
    tax = money(explicit);
    basis = 'amount';
    if (rate !== null && rate !== 0) problems.push('both a tax rate and a tax amount were given; the amount was used');
  } else if (rate !== null) {
    tax = money(subtotal * (rate / 100));
    basis = 'rate';
  }
  return {
    line_items: lines,
    subtotal: subtotal,
    tax_rate: basis === 'rate' ? rate : null,
    tax: tax,
    tax_basis: basis,
    total: money(subtotal + tax),
    problems: problems
  };
}

function validateProposal(payload) {
  const problems = [];
  if (!payload || typeof payload !== 'object') return ['no proposal supplied'];
  if (!str(payload.id)) problems.push('proposal_id (payload.id) is required');
  if (!str(payload.job_id)) problems.push('job_id is required');
  if (PROPOSAL_EVENTS.indexOf(payload.event_type) === -1) {
    problems.push('event_type must be one of: ' + PROPOSAL_EVENTS.join(', '));
  }
  if (payload.event_type === 'issued') {
    if (!Array.isArray(payload.line_items) || !payload.line_items.length) {
      problems.push('an issued proposal must carry the line items it was issued with -- it snapshots the price, it does not point at the estimate');
    }
    if (!isDate(payload.issued_on)) problems.push('issued_on must be YYYY-MM-DD');
  }
  if (payload.event_type === 'accepted' || payload.event_type === 'declined' || payload.event_type === 'withdrawn') {
    if (!str(payload.supersedes)) problems.push('this event must name the issued proposal_id it responds to');
    if (!isDate(payload.decided_on)) problems.push('decided_on must be YYYY-MM-DD');
  }
  if (payload.event_type === 'accepted') {
    if (ACCEPTANCE_METHODS.indexOf(payload.acceptance_method) === -1) {
      problems.push('acceptance_method must be one of: ' + ACCEPTANCE_METHODS.join(', '));
    }
    if (payload.acceptance_method === 'signature' && !str(payload.signature_data)) {
      problems.push('acceptance_method is signature but no signature was captured');
    }
    if (!str(payload.accepted_by)) problems.push('accepted_by is required -- who accepted it');
  }
  return problems;
}

function validateInvoice(payload) {
  const problems = [];
  if (!payload || typeof payload !== 'object') return ['no invoice supplied'];
  if (!str(payload.id)) problems.push('invoice_id (payload.id) is required');
  if (!str(payload.job_id)) problems.push('job_id is required');
  if (payload.status !== undefined && INVOICE_STATUSES.indexOf(payload.status) === -1) {
    problems.push('status must be one of: ' + INVOICE_STATUSES.join(', '));
  }
  if (payload.issue_date !== undefined && payload.issue_date && !isDate(payload.issue_date)) {
    problems.push('issue_date must be YYYY-MM-DD');
  }
  if (payload.due_date !== undefined && payload.due_date && !isDate(payload.due_date)) {
    problems.push('due_date must be YYYY-MM-DD');
  }
  if (payload.status === 'issued' && !isDate(payload.issue_date)) {
    problems.push('an issued invoice needs an issue_date');
  }
  return problems;
}

function validatePayment(payload) {
  const problems = [];
  if (!payload || typeof payload !== 'object') return ['no payment supplied'];
  if (!str(payload.payment_id)) problems.push('payment_id is required');
  const amt = num(payload.amount);
  if (amt === null || amt === 0) problems.push('amount must be a non-zero number');
  if (!isDate(payload.received_on)) problems.push('received_on must be YYYY-MM-DD');
  if (payload.method !== undefined && PAYMENT_METHODS.indexOf(payload.method) === -1) {
    problems.push('method must be one of: ' + PAYMENT_METHODS.join(', '));
  }
  // A correction is a NEGATIVE entry that names what it reverses, never an
  // edit to the original -- the payments array is append-only in practice
  // because the server does the appending.
  if (amt !== null && amt < 0 && !str(payload.reverses)) {
    problems.push('a negative payment must name the payment_id it reverses');
  }
  return problems;
}

// The derived view of one invoice. NEVER STORED.
function summarizeInvoice(invoice) {
  invoice = invoice || {};
  const totals = computeTotals(invoice.line_items, invoice.tax_rate, invoice.tax);
  const payments = Array.isArray(invoice.payments) ? invoice.payments : [];
  const paid = money(payments.reduce(function (s, p) { return s + (num(p && p.amount) || 0); }, 0));
  const balance = money(totals.total - paid);
  return {
    subtotal: totals.subtotal,
    tax: totals.tax,
    tax_basis: totals.tax_basis,
    total: totals.total,
    paid: paid,
    balance: balance,
    payment_count: payments.length,
    // Stated rather than inferred by the caller: an invoice can be over-paid
    // (a duplicated cheque, an insurer paying more than billed) and that is a
    // real condition worth surfacing, not a negative to hide.
    settlement: balance === 0 ? 'settled' : (balance > 0 ? 'outstanding' : 'overpaid'),
    problems: totals.problems
  };
}

// Where a job's proposals stand. Takes the whole append-only chain.
function proposalState(events) {
  const rows = Array.isArray(events) ? events.slice() : [];
  const issued = rows
    .filter(function (e) { return e && e.event_type === 'issued'; })
    .sort(function (a, b) { return String(a.issued_on || '') < String(b.issued_on || '') ? -1 : 1; });
  const latest = issued.length ? issued[issued.length - 1] : null;
  if (!latest) {
    return { ok: true, issued_count: 0, latest: null, status: 'none', decision: null, totals: null };
  }
  // Only a decision naming THIS proposal counts. A decision on a superseded
  // proposal must not decide the current one -- re-quoting after a decline is
  // ordinary, and the old decline must not stick to the new price.
  const decision = rows.filter(function (e) {
    return e && e.supersedes === latest.proposal_id &&
      ['accepted', 'declined', 'withdrawn'].indexOf(e.event_type) !== -1;
  }).sort(function (a, b) { return String(a.decided_on || '') < String(b.decided_on || '') ? -1 : 1; }).pop() || null;
  const totals = computeTotals(latest.line_items, latest.tax_rate, latest.tax);
  return {
    ok: true,
    issued_count: issued.length,
    latest: latest,
    status: decision ? decision.event_type : 'awaiting_decision',
    decision: decision,
    totals: totals,
    // Surfaced because it is the thing a contractor forgets: an accepted
    // proposal is the scope you are contractually on the hook for, and a later
    // issued proposal that nobody decided does not replace it.
    superseded_count: issued.length - 1
  };
}

// Compare an invoice against the claim it is linked to.
//
// CORRECTION TO AN EARLIER FRAMING: the claim's `final_invoice_submitted` is a
// DATE, not an amount (see roofing-claims.js MONEY_FIELDS). The invoice amount
// has no home on the claim at all, so this is not an amount-vs-amount check.
// What is worth comparing is the invoice total against what the claim says is
// collectible, and the invoice's issue date against the milestone.
//
// Everything here is INFORMATION, never an error: a gap between what you
// billed and what the carrier approved is exactly the conversation a
// supplement exists to have, the same way summarizeMoney surfaces the ACV/RCV
// gap rather than "correcting" it.
function reconcileAgainstClaim(invoice, claim) {
  if (!invoice) return { ok: false, error: { code: 'NO_INVOICE', message: 'no invoice supplied' } };
  if (!claim) return { ok: true, linked: false, notes: ['this invoice is not linked to a claim'] };
  const inv = summarizeInvoice(invoice);
  const rcv = num(claim.rcv);
  const deductible = num(claim.deductible);
  const notes = [];

  // What the carrier's own numbers imply is collectible in total, before any
  // supplement. Null unless the figures needed are actually present -- an
  // absent RCV must not read as zero.
  const carrierScope = rcv === null ? null : money(rcv);
  let variance = null;
  if (carrierScope !== null) {
    variance = money(inv.total - carrierScope);
    if (variance > 0) notes.push('invoiced ' + variance + ' MORE than the claim\'s RCV -- if that is real work, it belongs in a supplement, not an unexplained overage');
    else if (variance < 0) notes.push('invoiced ' + Math.abs(variance) + ' LESS than the claim\'s RCV -- check nothing approved was left off');
    else notes.push('invoice total matches the claim\'s RCV exactly');
  } else {
    notes.push('the claim has no RCV recorded, so the invoice cannot be compared against the approved scope');
  }
  if (deductible !== null) {
    notes.push('the homeowner\'s deductible of ' + deductible + ' is their responsibility and is not waivable -- it must appear as collected, not absorbed');
  }

  // The date milestone. The claim field is the date the final invoice went to
  // the carrier; the invoice knows when it was issued.
  const claimDate = str(claim.final_invoice_submitted) || null;
  const invDate = str(invoice.issue_date) || null;
  let milestone = 'not_submitted';
  if (claimDate && invDate) milestone = claimDate === invDate ? 'matches' : 'differs';
  else if (claimDate && !invDate) milestone = 'claim_only';
  else if (!claimDate && invDate) milestone = 'invoice_only';
  if (milestone === 'differs') notes.push('the claim records the final invoice as submitted ' + claimDate + ' but this invoice is dated ' + invDate);
  if (milestone === 'invoice_only') notes.push('this invoice has an issue date but the claim has no final_invoice_submitted recorded -- the milestone has not been logged');

  return {
    ok: true, linked: true,
    claim_id: claim.claim_id || null,
    invoice_total: inv.total,
    claim_rcv: carrierScope,
    variance: variance,
    deductible: deductible,
    milestone: milestone,
    notes: notes,
    // The two records stay independent on purpose (Michael's call 2026-08-25):
    // nothing here writes back to the claim, and neither figure is derived
    // from the other. A mismatch is information.
    disclosure: 'The invoice and the claim are separate records. This comparison is information, not a correction -- neither number was changed.'
  };
}

module.exports = {
  PROPOSAL_EVENTS,
  INVOICE_STATUSES,
  ACCEPTANCE_METHODS,
  PAYMENT_METHODS,
  normalizeLineItems,
  computeTotals,
  validateProposal,
  validateInvoice,
  validatePayment,
  summarizeInvoice,
  proposalState,
  reconcileAgainstClaim
};
