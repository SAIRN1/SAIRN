// api/_lib/roofing-claims.js
// SAIRNroofing Phase 3b -- insurance claim record + photo evidence.
//
// PURE -- no I/O. This module owns the two things a claim must get right and
// that are easy to get subtly wrong: the money lifecycle, and the status
// pipeline. The reconciliation engine that compares an adjuster's line items
// against the measured scope is Phase 3c and lives elsewhere -- this file
// deliberately does NOT reconcile anything.
//
// ── THE MONEY RULE, ENFORCED HERE RATHER THAN TRUSTED ────────────────────
// The scope doc is emphatic and correct: the seven money fields are SEPARATE,
// never one collapsed "amount". Conflating them is precisely how a contractor
// loses the recoverable-depreciation release -- ACV and RCV differ by exactly
// the depreciation, and the release is a distinct event that funds only after
// the final invoice.
//
// normalizeMoney() stores each field independently and NEVER writes a computed
// total back as if it were entered. summarizeMoney() exposes a derived display
// balance, but labels it derived and recomputes it every read -- it is never
// persisted, so it can never drift from or overwrite the real figures.

'use strict';

// The seven money fields, in lifecycle order. Amounts are dollars (numbers);
// the two "received/submitted" milestones are dates or null; the release is a
// dollar amount that lands last.
const MONEY_FIELDS = [
  'rcv',                              // Replacement Cost Value -- full scope
  'depreciation',                     // held back until work is done
  'acv',                              // Actual Cash Value = RCV - depreciation (ENTERED, not computed)
  'deductible',                       // the homeowner's responsibility
  'acv_check_received',               // date the first (ACV) cheque arrived, or null
  'final_invoice_submitted',          // date the final invoice went to the carrier, or null
  'recoverable_depreciation_released' // dollar amount released after final invoice, or null
];
const MONEY_AMOUNT_FIELDS = ['rcv', 'depreciation', 'acv', 'deductible', 'recoverable_depreciation_released'];
const MONEY_DATE_FIELDS = ['acv_check_received', 'final_invoice_submitted'];

// The real seven-step lifecycle (scope 5.1), plus the honest waiting state.
// Ordered, so the UI and the server agree on progression without a fake %.
const CLAIM_STATUSES = [
  'loss_reported',        // 1. homeowner reports the loss
  'adjuster_assigned',    // 2. carrier assigns a field adjuster
  'adjuster_meeting',     // 3. contractor meets the adjuster on the roof
  'scope_written',        // 4. adjuster writes the scope (in Xactimate)
  'contingency_signed',   // 5. contingency agreement + supplements filed
  'install_complete',     // 6. install done at carrier-approved scope
  'depreciation_released' // 7. ACV cheque funded; recoverable depreciation released
];
// Not a step of its own -- a flag any step can carry, so "we are stalled on the
// carrier" is honest rather than a frozen progress bar pretending to advance.
const WAITING_FLAG = 'waiting_on_carrier';

const PERILS = ['hail', 'wind', 'hurricane', 'fire', 'water', 'ice_dam', 'fallen_tree', 'other'];
const POLICY_TYPES = ['RCV', 'ACV']; // Replacement Cost vs Actual Cash Value policy

// Damage/phase tags for evidence photos (scope 5.3: tagged by elevation/slope
// and damage type; captured at the adjuster meeting and again at tear-off --
// tear-off photos are the evidentiary basis for the hidden-damage supplement).
const PHOTO_PHASES = ['adjuster_meeting', 'tear_off', 'in_progress', 'completion'];
const ELEVATIONS = ['front', 'rear', 'left', 'right', 'other'];

function isNum(n) { return typeof n === 'number' && isFinite(n); }
function isDate(s) { return typeof s === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(s); }

// Store each money field independently. Coerces the amount fields to numbers
// and the date fields to a real date or null. Crucially it does NOT compute acv
// from rcv - depreciation: acv is what the carrier's paperwork actually says,
// and if it disagrees with rcv - depreciation that disagreement is real
// information a supplement is built on, not an error to silently "fix".
function normalizeMoney(input) {
  const out = {};
  const problems = [];
  input = input || {};
  MONEY_AMOUNT_FIELDS.forEach(function (f) {
    if (input[f] === undefined || input[f] === null || input[f] === '') { out[f] = null; return; }
    const n = Number(input[f]);
    if (!isNum(n)) { problems.push(f + ' must be a number'); out[f] = null; return; }
    if (n < 0) { problems.push(f + ' cannot be negative'); out[f] = null; return; }
    out[f] = n;
  });
  MONEY_DATE_FIELDS.forEach(function (f) {
    if (!input[f]) { out[f] = null; return; }
    if (!isDate(input[f])) { problems.push(f + ' must be a date (YYYY-MM-DD)'); out[f] = null; return; }
    out[f] = input[f];
  });
  return { money: out, problems: problems };
}

// Read-only summary. Every real figure is passed through untouched; the derived
// values are clearly marked and recomputed here, never stored.
function summarizeMoney(money) {
  money = money || {};
  const rcv = money.rcv, dep = money.depreciation, acv = money.acv;
  // acv_implied is what ACV *would* be from RCV and depreciation. It exists to
  // SURFACE a mismatch with the entered acv, not to replace it -- a mismatch is
  // a real signal, and this is the honest place to show it.
  const acvImplied = (isNum(rcv) && isNum(dep)) ? +(rcv - dep).toFixed(2) : null;
  const acvMismatch = (isNum(acv) && acvImplied !== null) ? (Math.abs(acv - acvImplied) > 0.005) : false;
  return {
    entered: {
      rcv: rcv == null ? null : rcv,
      depreciation: dep == null ? null : dep,
      acv: acv == null ? null : acv,
      deductible: money.deductible == null ? null : money.deductible,
      acv_check_received: money.acv_check_received || null,
      final_invoice_submitted: money.final_invoice_submitted || null,
      recoverable_depreciation_released: money.recoverable_depreciation_released == null ? null : money.recoverable_depreciation_released
    },
    derived: {
      acv_implied: acvImplied,           // rcv - depreciation, DISPLAY ONLY
      acv_mismatch: acvMismatch,         // entered acv disagrees with the implied one
      depreciation_still_out: (isNum(dep) && !isNum(money.recoverable_depreciation_released))
        ? dep : (isNum(dep) && isNum(money.recoverable_depreciation_released)
          ? +(dep - money.recoverable_depreciation_released).toFixed(2) : null)
    }
  };
}

function isValidStatus(s) { return CLAIM_STATUSES.indexOf(s) !== -1; }
function statusIndex(s) { return CLAIM_STATUSES.indexOf(s); }

// Required-field check for a claim. Money is validated separately by
// normalizeMoney so a claim can be opened before any dollar figure is known --
// the carrier and claim number come first, the money arrives over 45-90 days.
function validateClaim(payload) {
  const problems = [];
  if (!payload || !payload.id) problems.push('id is required');
  if (!payload || !payload.job_id) problems.push('job_id is required (a claim belongs to a job)');
  if (!payload || !payload.carrier) problems.push('carrier is required');
  if (!payload || !payload.claim_number) problems.push('claim_number is required');
  if (payload && payload.status && !isValidStatus(payload.status)) {
    problems.push('status must be one of: ' + CLAIM_STATUSES.join(', '));
  }
  if (payload && payload.peril && PERILS.indexOf(payload.peril) === -1) {
    problems.push('peril must be one of: ' + PERILS.join(', '));
  }
  if (payload && payload.policy_type && POLICY_TYPES.indexOf(payload.policy_type) === -1) {
    problems.push('policy_type must be RCV or ACV');
  }
  if (payload && payload.date_of_loss && !isDate(payload.date_of_loss)) {
    problems.push('date_of_loss must be a date (YYYY-MM-DD)');
  }
  return problems;
}

function validatePhoto(payload) {
  const problems = [];
  if (!payload || !payload.id) problems.push('id is required');
  if (!payload || !payload.claim_id) problems.push('claim_id is required');
  if (payload && payload.phase && PHOTO_PHASES.indexOf(payload.phase) === -1) {
    problems.push('phase must be one of: ' + PHOTO_PHASES.join(', '));
  }
  if (payload && payload.elevation && ELEVATIONS.indexOf(payload.elevation) === -1) {
    problems.push('elevation must be one of: ' + ELEVATIONS.join(', '));
  }
  return problems;
}

module.exports = {
  MONEY_FIELDS,
  MONEY_AMOUNT_FIELDS,
  MONEY_DATE_FIELDS,
  CLAIM_STATUSES,
  WAITING_FLAG,
  PERILS,
  POLICY_TYPES,
  PHOTO_PHASES,
  ELEVATIONS,
  normalizeMoney,
  summarizeMoney,
  isValidStatus,
  statusIndex,
  validateClaim,
  validatePhoto
};
