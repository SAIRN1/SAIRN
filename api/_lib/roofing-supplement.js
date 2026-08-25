// api/_lib/roofing-supplement.js
// SAIRNroofing Phase 3c -- supplement reconciliation engine.
//
// PURE -- no I/O. This is the mechanical heart of the whole roofing bet, and
// the scope doc is emphatic about what it must and must NOT be:
//
//   "supplements and negotiations are NOT about opinion. They are about whether
//    a specific line item was included in the estimate or not, and whether the
//    quantity is correct."
//
// So this engine does DETERMINISTIC ARITHMETIC against the measured scope and
// NOTHING ELSE. It never asks an LLM what the adjuster "should" have included,
// and it never fuzzy-matches line-item text -- a text-similarity guess IS an
// opinion, and the moment an opinion enters, the number stops being defensible
// in front of an adjuster who has the same price list you do.
//
// ── HOW MATCHING WORKS, AND WHY IT IS EXPLICIT ───────────────────────────
// The contractor assigns each of their expected line items an item_key, and
// tags each imported adjuster line with the same key when they enter it. The
// engine matches on that key ALONE. No description parsing, no synonym table.
// If the contractor has not keyed a line, it is simply unmatched data -- the
// engine never invents the correspondence.
//
// ── TWO CLASSES OF SUPPLEMENT, ONLY ONE IS COMPUTED ──────────────────────
//   DERIVED (quantity_correction / omitted_item): computed here, purely from
//     measured quantity vs the adjuster's quantity. A shortfall is arithmetic.
//   ASSERTED (code_upgrade / hidden_damage): NOT computable from an aerial
//     measurement -- hidden damage is, by definition, what the measurement
//     could not see, which is exactly why tear-off photos exist. The engine
//     does not decide these; the contractor asserts them, and the engine's job
//     is to REQUIRE a photo citation and total them, never to opine that they
//     belong.
//
// ── CLOSED DECISION (2026-08-25): THE PUBLIC-ADJUSTER BOUNDARY ───────────
// Recorded here, in the source, the way SAIRNcash's Bridge exclusion is -- so
// it cannot quietly reappear as a "feature request" later.
//
// Tex. Ins. Code 4102.163: "A roofing contractor may not act as a public
// adjuster or advertise to adjust claims for any property for which the
// contractor is providing or may provide roofing services, regardless of
// whether the contractor holds a license under this chapter." The Texas
// Department of Insurance lists the prohibited conduct as offering to negotiate
// settlements, promising recovery of funds, or representing the policyholder in
// coverage discussions. Violations carry administrative, criminal and civil
// penalties. Florida (Fla. Stat. 626.854) and other states draw a similar line.
//
// THIS ENGINE IS ON THE RIGHT SIDE OF THAT LINE BY CONSTRUCTION, and it is
// worth being precise about why, because the property is fragile:
//   - It compares line items arithmetically against a measurement the
//     contractor took. It states a quantity difference; it does not argue for a
//     payment.
//   - It never asserts what the adjuster "should" have included. The two
//     supplement classes exist precisely so the computed ones stay factual and
//     the judgement ones stay attributed to the contractor.
//   - The contractor files the worksheet themselves. The app transmits nothing
//     to a carrier and holds no relationship with one -- see also the scope
//     doc's Xactimate decision (5.4), which stays out of v1 for its own
//     reasons.
//
// WHAT IS THEREFORE OUT OF SCOPE, permanently, absent counsel: negotiation
// scripts or talking points, "what should I ask the adjuster for" generation,
// carrier-specific settlement guidance, any LLM opinion on coverage, and any
// UI language that promises recovery, maximisation or negotiation on the
// owner's behalf. The panel copy was audited against this on 2026-08-25 and the
// operations assistant's system prompt now declines claim-strategy questions
// outright rather than answering them from general knowledge.

'use strict';

const REASON_CODES = ['code_upgrade', 'hidden_damage', 'quantity_correction', 'omitted_item'];
// Which reasons the engine computes vs which the contractor asserts.
const DERIVED_REASONS = ['quantity_correction', 'omitted_item'];
const ASSERTED_REASONS = ['code_upgrade', 'hidden_damage'];

function isNum(n) { return typeof n === 'number' && isFinite(n); }
function num(v) { const n = Number(v); return isNum(n) ? n : null; }
function round2(n) { return Math.round(n * 100) / 100; }

// Reconcile one claim's supplement worksheet.
//
//   measured        : { <quantity_key>: number }   -- the Phase 2 measured scope
//   expected_items  : [{ item_key, label, measured_from, unit, unit_price }]
//   adjuster_lines  : [{ item_key, description, quantity, unit_price }]
//   asserted_lines  : [{ reason_code, description, quantity, unit, unit_price, photo_ids:[], note }]
//   tolerance       : quantity units within which a match is "correct" (default 0)
//
// Returns { ok, derived, asserted, totals, problems }. Never throws on bad
// data -- it collects problems so the worksheet can show them next to the line.
function reconcile(input) {
  input = input || {};
  const measured = input.measured || {};
  const expected = Array.isArray(input.expected_items) ? input.expected_items : [];
  const adjuster = Array.isArray(input.adjuster_lines) ? input.adjuster_lines : [];
  const asserted = Array.isArray(input.asserted_lines) ? input.asserted_lines : [];
  const tolerance = isNum(input.tolerance) ? Math.abs(input.tolerance) : 0;
  const problems = [];

  // Index adjuster lines by item_key. A duplicate key is a real data problem
  // (two adjuster lines claiming the same item) -- flagged, and the quantities
  // summed so the comparison is against the adjuster's total for that item.
  const adjByKey = Object.create(null);
  adjuster.forEach(function (a) {
    const key = a && a.item_key;
    if (!key) { problems.push('an adjuster line has no item_key and cannot be reconciled: ' + JSON.stringify(a && a.description || a)); return; }
    const q = num(a.quantity);
    if (q === null) { problems.push('adjuster line "' + key + '" has a non-numeric quantity'); return; }
    if (!adjByKey[key]) adjByKey[key] = { quantity: 0, unit_price: num(a.unit_price), lines: 0 };
    adjByKey[key].quantity += q;
    adjByKey[key].lines += 1;
  });
  Object.keys(adjByKey).forEach(function (k) {
    if (adjByKey[k].lines > 1) problems.push('adjuster has ' + adjByKey[k].lines + ' lines keyed "' + k + '"; quantities were summed');
  });

  const derived = [];
  expected.forEach(function (e) {
    const key = e && e.item_key;
    if (!key) { problems.push('an expected item has no item_key'); return; }
    const measuredQty = num(measured[e.measured_from]);
    const unitPrice = num(e.unit_price);
    if (measuredQty === null) {
      derived.push({ item_key: key, label: e.label || key, status: 'no_measurement',
        reason_code: null, expected_qty: null, adjuster_qty: (adjByKey[key] ? adjByKey[key].quantity : null),
        shortfall_qty: null, unit_price: unitPrice, supplement_amount: 0,
        note: 'no measured value for "' + e.measured_from + '" -- cannot reconcile this item' });
      return;
    }
    const adj = adjByKey[key];
    if (!adj) {
      // The adjuster has no line for a measured item at all -> omitted.
      const amount = unitPrice !== null ? round2(measuredQty * unitPrice) : 0;
      derived.push({ item_key: key, label: e.label || key, status: 'omitted',
        reason_code: 'omitted_item', expected_qty: measuredQty, adjuster_qty: 0,
        shortfall_qty: measuredQty, unit_price: unitPrice, supplement_amount: amount });
      return;
    }
    const shortfall = measuredQty - adj.quantity;
    if (shortfall > tolerance) {
      const price = unitPrice !== null ? unitPrice : adj.unit_price;
      const amount = price !== null ? round2(shortfall * price) : 0;
      derived.push({ item_key: key, label: e.label || key, status: 'quantity_short',
        reason_code: 'quantity_correction', expected_qty: measuredQty, adjuster_qty: adj.quantity,
        shortfall_qty: round2(shortfall), unit_price: price, supplement_amount: amount });
    } else if (shortfall < -tolerance) {
      // The adjuster allowed MORE than measured. Not a supplement -- surfaced
      // as information, never as a negative amount that would net against a
      // real shortfall elsewhere and hide it.
      derived.push({ item_key: key, label: e.label || key, status: 'adjuster_over',
        reason_code: null, expected_qty: measuredQty, adjuster_qty: adj.quantity,
        shortfall_qty: 0, unit_price: unitPrice, supplement_amount: 0,
        note: 'adjuster allowed ' + round2(-shortfall) + ' more than measured -- no supplement' });
    } else {
      derived.push({ item_key: key, label: e.label || key, status: 'matched',
        reason_code: null, expected_qty: measuredQty, adjuster_qty: adj.quantity,
        shortfall_qty: 0, unit_price: unitPrice, supplement_amount: 0 });
    }
  });

  // Asserted lines: contractor-added, evidence-required. Each MUST cite at
  // least one photo and carry an ASSERTED reason. An asserted line with no
  // photo is kept but marked invalid with supplement_amount 0, so it can never
  // silently inflate the total -- the evidence is the whole basis for it.
  const assertedOut = asserted.map(function (a) {
    const reason = a && a.reason_code;
    const qty = num(a && a.quantity);
    const price = num(a && a.unit_price);
    const photos = Array.isArray(a && a.photo_ids) ? a.photo_ids.filter(Boolean) : [];
    const issues = [];
    if (ASSERTED_REASONS.indexOf(reason) === -1) issues.push('reason_code must be code_upgrade or hidden_damage');
    if (photos.length === 0) issues.push('at least one photo_id is required -- an asserted supplement without evidence cannot be counted');
    if (qty === null || qty <= 0) issues.push('a positive quantity is required');
    if (price === null || price < 0) issues.push('a valid unit_price is required');
    const valid = issues.length === 0;
    return {
      reason_code: reason || null,
      description: (a && a.description) || '',
      quantity: qty, unit: (a && a.unit) || '', unit_price: price,
      photo_ids: photos, note: (a && a.note) || '',
      valid: valid, issues: issues,
      supplement_amount: valid ? round2(qty * price) : 0
    };
  });

  const derivedTotal = derived.reduce(function (s, d) { return s + d.supplement_amount; }, 0);
  const assertedTotal = assertedOut.reduce(function (s, a) { return s + a.supplement_amount; }, 0);

  return {
    ok: true,
    derived: derived,
    asserted: assertedOut,
    totals: {
      derived_supplement: round2(derivedTotal),
      asserted_supplement: round2(assertedTotal),
      total_supplement: round2(derivedTotal + assertedTotal),
      omitted_count: derived.filter(function (d) { return d.status === 'omitted'; }).length,
      quantity_short_count: derived.filter(function (d) { return d.status === 'quantity_short'; }).length,
      asserted_invalid_count: assertedOut.filter(function (a) { return !a.valid; }).length
    },
    problems: problems
  };
}

module.exports = {
  REASON_CODES,
  DERIVED_REASONS,
  ASSERTED_REASONS,
  reconcile
};
