// api/_lib/roofing-gl-export.js
// SAIRNroofing gap A5 -- accounting integration.
//
// PURE -- no I/O, no LLM, no network. Money arithmetic only, and none of it new.
//
// ── THE GAP, AND WHY IT IS THE LAST ONE STANDING ─────────────────────────
// The 2026-08-26 worldwide competitive-gap audit's Tier-A item A5:
// "Accounting integration -- QuickBooks-integration absence is a named G2
// complaint against Roofr specifically. Not present."
//
// Re-derived 2026-09-17 across every SAIRNroofing row: eleven of twelve are
// now closed or deliberately refused, and A5 was the only one still returning
// ZERO on every marker -- QuickBooks, QBO, Xero, general ledger, IIF, chart of
// accounts, all 0 in sairnroofing.html. No partial, no disclosure banner,
// nothing.
//
// ── THIS IS AN EXPORT. IT IS NOT A SYNC, AND THE PANEL SAYS SO ───────────
// The single most important sentence in this file. A QuickBooks Online
// INTEGRATION means an Intuit developer account, an OAuth 2.0 authorisation
// code flow, a refresh-token lifecycle, and a per-app review before it may
// touch a real company file. None of that is engineering this app can do
// alone, and a screen headed "QuickBooks" with a file download behind it
// would be the same claim-without-substance this codebase keeps finding.
//
// api/_lib/roofing-supplier-match.js made exactly this call for B6 four
// commits of history ago, and its panel carries a banner reading "This is not
// an EDI connection". The same banner belongs here and for the same reason.
//
// WHAT IS BUILDABLE, AND IS WHERE THE WORK ACTUALLY IS, is the journal. An
// accountant importing a roofer's month does not need an API; they need
// double-entry lines that balance, coded to the accounts that roofer actually
// uses, with retainage in the right place. That is the half this file is.
//
// ── NOTHING IS SEEDED. THE CHART OF ACCOUNTS IS THE CONTRACTOR'S ────────
// Same posture as roofing-warranties.js (no GAF tier list) and
// roofing-prequal.js (EMR recorded, never judged), and for a sharper reason
// than either: an account number is not a fact about roofing, it is a fact
// about one company's books. 4000 is revenue in one chart and a payroll
// expense in the next. Posting a roofer's income to a number this file made
// up produces a trial balance that imports cleanly and is wrong, which is the
// worst available outcome -- it looks like it worked.
//
// So every account arrives from the contractor, by ROLE, and an unmapped role
// REFUSES THE EXPORT rather than posting to a default or a suspense account.
// A suspense account is the seeded-default problem wearing a respectable name.
//
// ── THE BASIS IS STATED, NEVER DEFAULTED ────────────────────────────────
// Accrual and cash basis produce different journals from the same invoices,
// and which one a roofer files on is a decision their accountant made, not a
// preference this module may guess. `basis` is required and an absent one is
// refused -- the same call sairnmechanical's credential form makes on
// has_expiry, where guessing "it probably expires" would be wrong about a
// legal document.
//
//   accrual  revenue is recognised when the invoice is ISSUED
//   cash     revenue is recognised when the payment ARRIVES
//
// ── RETAINAGE IS ITS OWN RECEIVABLE, WHICH IS THE ROOFING-SPECIFIC BIT ──
// A generic export posts the whole invoice to Accounts Receivable. On a
// progress-billed roofing job that is wrong: retainage held is not collectible
// on normal terms, it is released at completion, and an ageing report that
// treats it as ordinary AR shows a contractor money they cannot chase. It gets
// its own role and its own line.
//
// ── AND IT REFUSES TO EMIT AN UNBALANCED JOURNAL ────────────────────────
// Debits must equal credits to the cent or nothing is returned. An unbalanced
// journal that imports is worse than one that does not: the accounting package
// will either reject it after the fact or, worse, book the difference somewhere
// nobody looks.
//
// THAT GUARD IS CURRENTLY UNREACHABLE AND IT IS KEPT ANYWAY, which is worth
// writing down rather than leaving for somebody to discover and delete as dead
// code. The arithmetic below cannot unbalance: debits are always `total`,
// credits are always `(total - tax) + tax`, and retainage SPLITS the debit
// rather than adding to it. Two deliberate corruptions of a summary were driven
// through it in roofing-gl-export.test.js -- a total that does not equal its
// parts, and a tax the total does not include -- and both stayed balanced.
//
// It fires the day a line type is added that does not self-balance: a discount,
// a write-off, a credit note. That is precisely when nobody would be looking
// for it, which is why an unreachable guard is still the right thing here. What
// is NOT claimed is that it has been seen to fire on real input.

'use strict';

// ── THE ROLES, AND WHY THEY ARE ROLES RATHER THAN NUMBERS ────────────────
// Named by what they DO in the journal. The contractor maps each to whatever
// their own chart calls it. Adding a role here is a breaking change for every
// stored map, which is the right amount of friction for this list.
const ACCOUNT_ROLES = [
  'accounts_receivable',   // billed and collectible on normal terms
  'retainage_receivable',  // billed, held back, released at completion
  'revenue',               // the work itself
  'sales_tax_payable',     // collected on behalf of the state, never revenue
  'cash'                   // where a payment lands
];

const BASES = ['accrual', 'cash'];

function num(v) {
  if (typeof v === 'number' && isFinite(v)) return v;
  if (typeof v === 'string' && v.trim() !== '' && isFinite(Number(v))) return Number(v);
  return null;
}
function str(v) { return typeof v === 'string' && v.trim() !== '' ? v.trim() : null; }
// Cents, once, in one place -- the same reason roofing-billing.js has its own
// money(): a second rounding rule is a second answer.
function money(v) { return Math.round((num(v) || 0) * 100) / 100; }

// ── THE ACCOUNT MAP ──────────────────────────────────────────────────────
// { accounts_receivable: '1200', revenue: '4000', ... }. Every role required.
// A blank string is treated as ABSENT rather than as an account called "",
// because an empty input box is the commonest way this arrives.
function validateAccountMap(map) {
  const problems = [];
  if (!map || typeof map !== 'object') return ['no account map supplied'];
  ACCOUNT_ROLES.forEach(function (role) {
    if (!str(map[role])) {
      problems.push('no account mapped for ' + role);
    }
  });
  // A DUPLICATE MAPPING IS REPORTED, NOT REFUSED. Two roles sharing one
  // account is unusual and is sometimes deliberate -- a small roofer may hold
  // retainage in the same receivable account. It is surfaced so nobody
  // discovers it in a trial balance, and it is the contractor's call.
  const seen = {};
  ACCOUNT_ROLES.forEach(function (role) {
    const acct = str(map[role]);
    if (!acct) return;
    (seen[acct] = seen[acct] || []).push(role);
  });
  const shared = Object.keys(seen).filter(function (a) { return seen[a].length > 1; });
  return { problems: problems, shared: shared.map(function (a) {
    return { account: a, roles: seen[a] };
  }) };
}

function line(account, role, debit, credit, memo, ref) {
  return {
    account: account,
    role: role,
    debit: money(debit),
    credit: money(credit),
    memo: memo,
    ref: ref
  };
}

// ── ONE INVOICE -> ITS LINES ─────────────────────────────────────────────
// `summary` is roofing-billing.js's summarizeInvoice() output, passed IN
// rather than recomputed. Deliberate: the invoice total on the accountant's
// journal and the invoice total on the customer's screen must be the same
// number produced by the same code, and this module having its own would be a
// second place for them to disagree. That is the lesson roofing-billing.js
// already records about the derived balance.
function invoiceLines(invoice, summary, map, basis, retainageHeld) {
  const ref = str(invoice && invoice.id) || str(invoice && invoice.invoice_id) || '(no id)';
  const memo = 'Invoice ' + ref + (str(invoice && invoice.job_id) ? ' / job ' + invoice.job_id : '');
  const out = [];
  if (basis !== 'accrual') return out;   // cash basis recognises nothing here

  const total = money(summary.total);
  const tax = money(summary.tax);
  const revenue = money(total - tax);
  const held = money(retainageHeld || 0);

  // RETAINAGE SPLITS THE RECEIVABLE, IT DOES NOT REDUCE THE REVENUE. The work
  // was performed and billed; only the collection is deferred. Booking it as
  // less revenue would understate the month and overstate the next one.
  if (held > 0) {
    out.push(line(map.retainage_receivable, 'retainage_receivable', held, 0,
                  memo + ' (retainage held)', ref));
    out.push(line(map.accounts_receivable, 'accounts_receivable', money(total - held), 0, memo, ref));
  } else {
    out.push(line(map.accounts_receivable, 'accounts_receivable', total, 0, memo, ref));
  }
  out.push(line(map.revenue, 'revenue', 0, revenue, memo, ref));
  // NO ZERO LINE. A tax line of 0.00 on an invoice with no tax is noise in a
  // journal an accountant reads by eye.
  if (tax !== 0) {
    out.push(line(map.sales_tax_payable, 'sales_tax_payable', 0, tax, memo + ' (sales tax)', ref));
  }
  return out;
}

// ── ONE PAYMENT -> ITS LINES ─────────────────────────────────────────────
function paymentLines(invoice, payment, map, basis) {
  const ref = str(invoice && invoice.id) || str(invoice && invoice.invoice_id) || '(no id)';
  const amt = money(payment && payment.amount);
  if (amt === 0) return [];
  const memo = 'Payment on invoice ' + ref
    + (str(payment && payment.method) ? ' (' + payment.method + ')' : '');
  const out = [line(map.cash, 'cash', amt, 0, memo, ref)];
  // ACCRUAL clears the receivable the invoice raised. CASH BASIS never raised
  // one, so the credit is revenue -- and the sales tax is NOT separated here,
  // because on a cash basis the liability arises with the receipt and
  // splitting it needs the invoice's tax proportion, which is a decision about
  // partial payments this module will not make silently. Stated in
  // `notes` rather than guessed.
  out.push(basis === 'accrual'
    ? line(map.accounts_receivable, 'accounts_receivable', 0, amt, memo, ref)
    : line(map.revenue, 'revenue', 0, amt, memo, ref));
  return out;
}

function totalsOf(lines) {
  let d = 0, c = 0;
  lines.forEach(function (l) { d += l.debit; c += l.credit; });
  return { debits: money(d), credits: money(c), difference: money(d - c) };
}

// ── THE EXPORT ───────────────────────────────────────────────────────────
// invoices: [{ id, job_id, line_items, tax_rate|tax, payments:[{amount,method,date}] }]
// summaries: id -> summarizeInvoice(invoice), supplied by the caller.
// retainage: id -> amount held back on that invoice (from wip-accounting).
function buildExport(input, map, opts) {
  input = input || {};
  opts = opts || {};
  const basis = str(opts.basis);
  const problems = [];

  // REFUSED, NOT DEFAULTED. See the header.
  if (!basis) {
    problems.push('basis is required and is not defaulted: pass "accrual" or '
      + '"cash". The same invoices produce different journals under each, and '
      + 'which one this roofer files on is their accountant\'s decision.');
  } else if (BASES.indexOf(basis) === -1) {
    problems.push('basis must be one of: ' + BASES.join(', '));
  }

  const mapCheck = validateAccountMap(map);
  const mapProblems = Array.isArray(mapCheck) ? mapCheck : mapCheck.problems;
  const shared = Array.isArray(mapCheck) ? [] : mapCheck.shared;
  mapProblems.forEach(function (p) { problems.push(p); });

  if (problems.length) {
    // NOTHING PARTIAL IS RETURNED. A journal missing the rows whose account
    // could not be resolved is an unbalanced journal that looks complete.
    return { ok: false, problems: problems, lines: [], totals: null,
             shared_accounts: shared, notes: [] };
  }

  const invoices = Array.isArray(input.invoices) ? input.invoices : [];
  const summaries = input.summaries || {};
  const retainage = input.retainage || {};
  const lines = [];
  const notes = [];
  const skipped = [];

  invoices.forEach(function (inv) {
    const id = str(inv && inv.id) || str(inv && inv.invoice_id);
    const summary = id ? summaries[id] : null;
    if (!summary) {
      // COUNTED AND NAMED, never dropped quietly -- an invoice missing from a
      // month's journal is the defect this whole file exists to avoid.
      skipped.push({ invoice: id || '(no id)', reason: 'no summary supplied for this invoice' });
      return;
    }
    invoiceLines(inv, summary, map, basis, retainage[id]).forEach(function (l) { lines.push(l); });
    const payments = Array.isArray(inv.payments) ? inv.payments : [];
    payments.forEach(function (p) {
      paymentLines(inv, p, map, basis).forEach(function (l) { lines.push(l); });
    });
  });

  const totals = totalsOf(lines);
  if (totals.difference !== 0) {
    return {
      ok: false,
      problems: ['the journal does not balance: debits ' + totals.debits
        + ' against credits ' + totals.credits + ', a difference of '
        + totals.difference + '. Nothing is returned -- an unbalanced journal '
        + 'that imports is worse than one that does not.'],
      lines: [], totals: totals, shared_accounts: shared, skipped: skipped, notes: notes
    };
  }

  if (basis === 'cash') {
    notes.push('CASH BASIS: sales tax is not separated on a receipt. The whole '
      + 'payment is credited to revenue, because splitting it needs the '
      + 'invoice\'s tax proportion and this module will not apportion a partial '
      + 'payment without being told how.');
  }
  if (shared.length) {
    shared.forEach(function (s) {
      notes.push('account ' + s.account + ' is mapped to more than one role ('
        + s.roles.join(', ') + '). Allowed, and surfaced so it is not '
        + 'discovered in a trial balance.');
    });
  }
  if (skipped.length) {
    notes.push(skipped.length + ' invoice(s) were NOT exported and are listed '
      + 'in `skipped`. They are absent from these totals.');
  }

  return { ok: true, problems: [], lines: lines, totals: totals,
           shared_accounts: shared, skipped: skipped, notes: notes, basis: basis };
}

// ── CSV, AND DELIBERATELY NOT IIF ────────────────────────────────────────
// IIF is QuickBooks DESKTOP's format. Intuit has not recommended it for new
// work in years and QuickBooks Online cannot import it at all, so emitting an
// .iif and calling it QuickBooks support would be precisely the overclaim the
// header refuses. A journal CSV is what QuickBooks Online, Xero and every
// accountant's own import tool actually take.
function toCsv(result) {
  if (!result || !result.ok) return null;
  const head = ['date', 'account', 'role', 'debit', 'credit', 'memo', 'reference'];
  // ── FORMULA INJECTION, AND THIS ONE WAS THE WORST CASE ON THE PLATFORM ──
  // (2026-09-17.) The local quoter this replaces was CONDITIONAL -- it quoted
  // only when the value contained a comma, quote or newline -- so a memo of
  // `=cmd|'/c calc'!A0` was written out COMPLETELY BARE. `memo` is free text
  // from a roofing job, and the file's own purpose is to be handed to an
  // accountant and imported. Every other site on the platform at least wrapped
  // the cell in quotes, which does not help either but is less naked.
  //
  // api/_lib/csv-cell.js is deliberately not number-blind: the debit and credit
  // columns below are money, and a credit emitted as `'-50.00` would arrive as
  // TEXT and drop out of every SUM in the accountant's spreadsheet. That is why
  // the guard is conditional on the cell not parsing as a number.
  const q = require('./csv-cell.js').csvCell;
  const rows = [head.join(',')];
  result.lines.forEach(function (l) {
    rows.push([q(l.date || ''), q(l.account), q(l.role),
               q(l.debit ? l.debit.toFixed(2) : ''),
               q(l.credit ? l.credit.toFixed(2) : ''),
               q(l.memo), q(l.ref)].join(','));
  });
  return rows.join('\r\n');
}

module.exports = {
  ACCOUNT_ROLES,
  BASES,
  validateAccountMap,
  invoiceLines,
  paymentLines,
  totalsOf,
  buildExport,
  toCsv
};
