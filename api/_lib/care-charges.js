// api/_lib/care-charges.js
// SAIRNcare Phase 3 item 2: clinical documentation -> billing charges, with no
// manual reconciliation step.
//
// PURE -- no I/O, same as the other Phase 1-3 engines.
//
// THE PROBLEM THIS SOLVES: documentation and billing normally live apart, and
// somebody re-keys one into the other at month end. That re-keying step is
// where revenue leaks -- a recorded service that nobody transcribed is simply
// never billed, and nothing in either system notices.
//
// THE RULE THAT MAKES THIS SAFE: a charge is only ever produced from a REAL
// RECORDED DOCUMENTATION EVENT. This module never estimates, never annualises,
// never fills a gap with an average, and never bills for a service that has no
// record behind it. Every charge line it emits carries the id of the exact
// document it came from, so any figure can be walked back to its source.
//
// AND THE ONE THAT MAKES IT HONEST: a chargeable event whose rate the facility
// has not configured is NOT silently dropped and NOT billed at zero. It is
// returned in `unpriced` so the gap is visible. Dropping it would recreate the
// exact revenue leak this exists to close, just one layer further in.

'use strict';

// Which documented events can become a charge, and where the rate comes from.
// Rates live on the facility's own rate card -- this module holds no money.
const CHARGEABLE = {
  // A documented ADL assessment is a billable clinical service in facilities
  // that bill assessments separately. Off by default (rate absent = unpriced).
  adl_assessment: { label: 'ADL assessment', rate_key: 'adl_assessment_rate' },
  // A medication administration, where the facility bills med management
  // per administration rather than folding it into the care-level rate.
  medication_administration: { label: 'Medication administration', rate_key: 'med_admin_rate' },
  // A documented activity attendance, for facilities billing therapeutic
  // programming separately.
  activity_attendance: { label: 'Activity attendance', rate_key: 'activity_rate' }
};

function round2(n) { return Math.round(Number(n) * 100) / 100; }

function inMonth(dateStr, monthStr) {
  return typeof dateStr === 'string' && dateStr.slice(0, 7) === monthStr;
}

// Turn documented events into charge lines for one resident-month.
//
// events: [{ id, type, resident_id, date, quantity?, description? }]
// rate_card: the facility's rate card object
function deriveCharges(opts) {
  opts = opts || {};
  const month = opts.month;
  const residentId = opts.resident_id;
  const rateCard = opts.rate_card || {};
  if (!/^\d{4}-\d{2}$/.test(String(month || ''))) {
    return { ok: false, error: { code: 'BAD_MONTH', message: 'month must be YYYY-MM' } };
  }
  if (!residentId) {
    return { ok: false, error: { code: 'NO_RESIDENT', message: 'resident_id is required' } };
  }

  const events = (opts.events || []).filter((e) =>
    e && e.resident_id === residentId && inMonth(e.date, month)
  );

  const lines = [];
  const unpriced = [];
  const unknownType = [];

  events.forEach((e) => {
    const spec = CHARGEABLE[e.type];
    if (!spec) {
      // Not billable and not an error -- most documentation isn't a charge.
      // Recorded separately so a genuinely new event type is visible rather
      // than silently ignored forever.
      unknownType.push({ event_id: e.id, type: e.type });
      return;
    }
    const rate = Number(rateCard[spec.rate_key]);
    const qty = e.quantity == null ? 1 : Number(e.quantity);
    if (!isFinite(qty) || qty <= 0) {
      unpriced.push({
        event_id: e.id, type: e.type, label: spec.label, date: e.date,
        reason: 'The documented quantity is missing or not a positive number.'
      });
      return;
    }
    if (!isFinite(rate) || rate <= 0) {
      // NOT billed at zero, NOT dropped. Visible.
      unpriced.push({
        event_id: e.id, type: e.type, label: spec.label, date: e.date, quantity: qty,
        reason: 'No rate is configured for ' + spec.label.toLowerCase() + ' (' + spec.rate_key + '). This documented service is not being billed until a rate is set.'
      });
      return;
    }
    lines.push({
      event_id: e.id,
      type: e.type,
      label: spec.label,
      date: e.date,
      quantity: qty,
      unit_rate: round2(rate),
      amount: round2(rate * qty),
      description: e.description || ''
    });
  });

  lines.sort((a, b) => (a.date < b.date ? -1 : (a.date > b.date ? 1 : 0)));
  const total = round2(lines.reduce((s, l) => s + l.amount, 0));

  return {
    ok: true,
    resident_id: residentId,
    month: month,
    lines: lines,
    total: total,
    unpriced: unpriced,
    unbillable_event_types: unknownType,
    // The reconciliation contract: how many documented chargeable events were
    // seen, and how many actually became money. A gap here IS the revenue leak,
    // stated as a number rather than left for someone to notice.
    reconciliation: {
      documented_chargeable_events: lines.length + unpriced.length,
      billed_events: lines.length,
      unbilled_events: unpriced.length,
      fully_reconciled: unpriced.length === 0
    }
  };
}

// Compare derived charges against what an invoice already carries, so a
// regenerate can show exactly what changed and why -- the audit trail that
// replaces the manual reconciliation step.
function reconcileAgainstInvoice(derived, existingLines) {
  const prior = existingLines || [];
  const priorById = {};
  prior.forEach((l) => { if (l && l.event_id) priorById[l.event_id] = l; });
  const derivedById = {};
  (derived.lines || []).forEach((l) => { derivedById[l.event_id] = l; });

  const added = (derived.lines || []).filter((l) => !priorById[l.event_id]);
  const removed = prior.filter((l) => l && l.event_id && !derivedById[l.event_id]);
  const changed = (derived.lines || []).filter((l) => {
    const p = priorById[l.event_id];
    return p && round2(p.amount) !== round2(l.amount);
  }).map((l) => ({ event_id: l.event_id, from: round2(priorById[l.event_id].amount), to: round2(l.amount) }));

  return {
    added: added, removed: removed, changed: changed,
    unchanged_count: (derived.lines || []).length - added.length - changed.length,
    net_change: round2(
      added.reduce((s, l) => s + l.amount, 0)
      - removed.reduce((s, l) => s + Number(l.amount || 0), 0)
      + changed.reduce((s, c) => s + (c.to - c.from), 0)
    )
  };
}

module.exports = { CHARGEABLE, deriveCharges, reconcileAgainstInvoice };
