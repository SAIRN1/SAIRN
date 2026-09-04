// api/_lib/dental-ledger.js
//
// Server-side validation for SAIRNdental's money ledger, starting with
// dnt_payments.
//
// ── WHY THIS FILE EXISTS ──────────────────────────────────────────────────
// docs/SAIRN-OPEN-WORK-INDEX.md: "The generic DNT_RESOURCES write validates
// payload.id and nothing else, for FIFTEEN resources." That row says plainly
// how to close it: NOT all fifteen in one pass, but one resource at a time,
// highest stakes first. This is the first one.
//
// dnt_payments was chosen after measuring what a bad row actually does to the
// numbers a practice reads, rather than by picking the scariest-sounding
// table. Every rule below traces to a specific line in sairndental.html:
//
//   1. A NEGATIVE amount INFLATES what the practice is owed. dnAging() builds
//      `pool` as the sum of a patient's payments, then does
//          applied = Math.min(pool, owed); pool -= applied; rem = owed - applied
//      With a negative pool, `applied` is negative, so `rem` comes out LARGER
//      than the charge itself and the outstanding total climbs. The charge
//      side is guarded (`if (owed < 0) owed = 0`); the payment side is not.
//      That asymmetry is why payments and not charges went first.
//
//   2. A NON-NUMERIC amount silently becomes ZERO. Every consumer reads
//      `Number(p.amount) || 0` -- patientBalance(), dnAging(). A real payment
//      of "1,250.00" (a string with a comma, from any caller that is not this
//      app) is not an error anywhere; it is simply money that stops existing.
//
//   3. A MISSING patient_id orphans the row. patientBalance() and dnAging()
//      both key payments by patient_id, so a payment with none is counted by
//      nothing -- the practice banked the money and every report still says
//      the patient owes it.
//
// None of the three throws, none renders an error, and all three produce a
// plausible number. That is the shape sairn-silent-failure-sweep exists for.
//
// ── WHY THIS ONE IS ALSO THE SAFEST OF THE FIFTEEN, checked not assumed ───
// The index row warns that validating a resource can make a LEGACY row
// unwritable -- true of dnt_patients, where icapSaveToPatient() re-saves a
// whole existing record. It is NOT true here. dnt_payments is append-only in
// fact and not only in intent: `sdnData('write','dnt_payments',...)` appears
// exactly once in sairndental.html, inside addPaymentEntry(), which only ever
// creates. dntSyncFromServer() READS and merges into localStorage; it never
// writes back. So no path re-sends an existing payment, and a pre-existing bad
// row cannot be blocked by this because nothing tries to store it again.
//
// ── WHAT IS DELIBERATELY NOT VALIDATED ────────────────────────────────────
//   * THAT THE PATIENT EXISTS. That is a read before every write, and this
//     handler serves a provider-scoped app where the caller may legitimately
//     not be able to see the patient list. Same reasoning as the GFE block in
//     api/sd-data.js, which pays for its two extra reads only on issue.
//   * THE METHOD, beyond requiring something. The app's select offers
//     Cash/Card/Check, but an enum here would refuse ACH or a card brand later
//     and protects against none of the three failures above.
//   * AN UPPER BOUND on the amount. There is no such rule anywhere in this
//     app, and inventing a ceiling would be fabricating a policy the practice
//     never set.
//   * THE DATE. dnAging() ages CHARGES, not payments, so a payment's date does
//     not enter the arithmetic. Charges already disclose their undated rows.

// A money value the ledger can actually add up. Type-checked before parsing on
// purpose: Number(true) is 1 and Number([5]) is 5, so a bare Number() test
// would accept a boolean and a single-element array as a payment.
function isPositiveMoney(v) {
  if (typeof v !== 'number' && typeof v !== 'string') return false;
  const n = Number(v);
  return Number.isFinite(n) && n > 0;
}

// Returns a message when the row must be refused, or null when it is fine.
// A message rather than a boolean because the caller shows it to a person, and
// a code on its own does not say what to do about it -- the same standard as
// dental-guardian.js's guardianProblem().
//
// A numeric STRING is accepted. Every consumer already reads the field through
// Number(), so "125.00" adds up correctly, and refusing it would reject a
// well-formed payment for a formatting preference. What is refused is a value
// that cannot become a number at all, which is the case that silently becomes
// zero.
function paymentProblem(record) {
  const r = record || {};
  const patientId = String(r.patient_id == null ? '' : r.patient_id).trim();
  if (!patientId) {
    return 'This payment is not attached to a patient, so no balance or ageing '
         + 'report can count it. Send patient_id with the payment.';
  }
  if (!isPositiveMoney(r.amount)) {
    return 'A payment amount must be a number greater than zero. A negative '
         + 'amount increases what the practice appears to be owed, and a value '
         + 'that is not a number is read as zero, so the payment disappears '
         + 'from the patient balance and the ageing report. To reverse a '
         + 'payment, record the correction as its own entry rather than a '
         + 'negative one.';
  }
  return null;
}

// Same test as isPositiveMoney but zero is legitimate: a charge with no
// insurance coverage carries estimated_insurance_portion 0, which is what
// computeEstimatedInsurance() returns when lookupCoverage() finds no rule.
function isNonNegativeMoney(v) {
  if (typeof v !== 'number' && typeof v !== 'string') return false;
  const n = Number(v);
  return Number.isFinite(n) && n >= 0;
}

// ── dnt_charges, THE SECOND OF THE FIFTEEN (2026-09-04) ───────────────────
// Recorded as the next one when dnt_payments shipped, with the reason: a bad
// charge is clamped by dnAging()'s `if (owed < 0) owed = 0`, so it corrupts
// less than a bad payment. MEASURED AGAIN HERE RATHER THAN ASSUMED FROM THAT
// SENTENCE, and the clamp turns out to cover only half the app:
//
//   * dnAging() clamps, per charge.
//   * patientBalance() DOES NOT. It is
//         balanceDue = (totalCharges - totalEstInsurance) - totalPayments
//     with no floor anywhere, so a negative amount reduces what the patient
//     owes directly, and can drive Balance Due below zero -- which the billing
//     panel renders in the OK colour, as though the patient were in credit.
//
//   So the two views DISAGREE on the same charge: the billing KPI moves and
//   the ageing report does not. Two numbers about one patient, one of them
//   lying, which is the shape sairn-silent-failure-sweep names explicitly.
//
// A NON-NUMERIC amount is worse than it looks for the same reason. Every total
// reads Number(x) || 0, so the charge contributes nothing -- while the charges
// TABLE right beside the total renders fmt(c.amount) and shows it. A row
// visible in the list and absent from the sum next to it, on one screen.
//
// APPEND-ONLY IN FACT, re-checked for THIS resource rather than carried over
// from the payments case: sdnData('write','dnt_charges',...) appears exactly
// once in sairndental.html, in addChargeEntry(), which only creates. Nothing
// re-sends an existing charge, so no legacy row can be blocked by this.
//
// ── WHAT IS DELIBERATELY NOT VALIDATED, AND THE INTERESTING ONE IS WHY ────
// estimated_insurance_portion is checked for TYPE and SIGN and NOT against the
// charge amount. An estimate larger than the charge is a real defect -- it
// makes patientBalance() report a credit while dnAging() floors at zero -- but
// it is reachable from the app itself WITHOUT a bad charge:
// computeEstimatedInsurance() multiplies the amount by a dnt_coverage_rules
// row's coverage_percent, and that resource is on the same unvalidated generic
// write. The browser caps the percent at 0-100 in addCoverageRule(); the
// server does not. So a 150% rule produces an over-estimate on a perfectly
// correct charge, and refusing the CHARGE would punish the wrong record and
// block work the practice cannot fix from the charge screen.
//
// The relation belongs to the coverage rule. dnt_coverage_rules is therefore
// the recorded THIRD resource, and this is the reason -- written down here so
// the next reader does not have to re-derive it, and so nobody adds an
// `est <= amount` check to this function believing it was simply forgotten.
function chargeProblem(record) {
  const r = record || {};
  const patientId = String(r.patient_id == null ? '' : r.patient_id).trim();
  if (!patientId) {
    return 'This charge is not attached to a patient, so no balance or ageing '
         + 'report can count it. Send patient_id with the charge.';
  }
  if (!isPositiveMoney(r.amount)) {
    return 'A charge amount must be a number greater than zero. A negative '
         + 'amount reduces what the patient owes on the billing panel while '
         + 'the ageing report ignores it, so the two disagree, and a value '
         + 'that is not a number is read as zero -- the charge then shows in '
         + 'the charges table and counts for nothing in the total beside it. '
         + 'To write off or reverse a charge, record the correction as its own '
         + 'entry rather than a negative one.';
  }
  if (r.estimated_insurance_portion !== undefined
      && r.estimated_insurance_portion !== null
      && !isNonNegativeMoney(r.estimated_insurance_portion)) {
    return 'The estimated insurance portion must be a number of zero or more. '
         + 'A negative value increases what the patient appears to owe, and a '
         + 'value that is not a number is read as zero, which overstates the '
         + 'patient responsibility shown on their charge line. Leave the field '
         + 'out entirely if there is no estimate.';
  }
  return null;
}

// ── dnt_coverage_rules, THE THIRD OF THE FIFTEEN (2026-09-04) ─────────────
// It is here rather than in its own module because it is not really a third
// subject: a coverage rule is the INPUT to the estimate that charges carry,
// and the reason it is being validated at all was written down while doing
// charges. Keeping the three together puts the reasoning where the next
// reader will look for it.
//
// THIS ONE IS NOT A RULE I INVENTED. sairndental.html's addCoverageRule()
// already refuses a percent outside 0-100:
//
//     if (isNaN(pct) || pct < 0 || pct > 100) { toast('Coverage percent must
//     be 0-100'); return; }
//
// in browser JavaScript, and the generic write accepted 150 regardless. Same
// shape as the guardian rule and 45 CFR 149.610(c)(1), both of which were
// enforced in the browser and nowhere else until 2026-09-04. This moves the
// app's own stated rule to the server; it does not add a new policy.
//
// WHAT A BAD RULE DOES, traced rather than imagined. lookupCoverage() returns
// Number(match.coverage_percent) || 0 and computeEstimatedInsurance()
// multiplies the charge by pct/100, LOCKING THE RESULT ONTO THE CHARGE
// PERMANENTLY -- the app never recomputes an existing charge's estimate. So a
// bad rule does not show up as a bad rule; it shows up later as a wrong number
// on charges that have already been written:
//
//   * OVER 100 -- the estimate exceeds the charge, so patientBalance() reports
//     a CREDIT while dnAging() floors at zero. This is the defect that was
//     deliberately not fixed on the charge side, because refusing the charge
//     would punish the correct record; this is where it belongs.
//   * NEGATIVE -- the estimate is negative, so patientBalance() ADDS it to
//     what the patient owes and dnAging()'s `owed = amount - est` grows. The
//     patient is billed for more than the charge.
//   * NON-NUMERIC -- `|| 0` makes it zero per cent, so the patient is billed
//     the full amount on a procedure their plan covers. Meanwhile rCoverage()
//     renders H(c.coverage_percent) + '%' verbatim, so the rules table shows
//     "abc%" while every estimate computed from it uses 0. The table and the
//     arithmetic disagree, and only the table is visible.
//   * NO payer OR NO procedure_type_id -- lookupCoverage() matches on both,
//     case-insensitively and exactly, so such a rule can never match anything.
//     It is configuration the practice believes is in place and that can never
//     apply. The app's "no coverage rule on file" message is honest, which is
//     exactly what makes this invisible.
//
// APPEND-ONLY IN FACT, re-checked for THIS resource rather than carried over:
// sdnData('write','dnt_coverage_rules',...) appears exactly once, in
// addCoverageRule(), which only creates. removeCoverageRule() is local-only
// and says so. No legacy rule can be blocked by this.
//
// DELIBERATELY NOT DONE HERE: a duplicate check on (payer, procedure_type_id).
// lookupCoverage() uses .find(), so with two matching rules the applied
// percentage is decided by ROW ORDER -- the same defect the dnt_providers
// branch refuses explicitly for linked_employee_id, and it has the same
// ready-made fix shape. It is left out because it is a different kind of
// change: it needs a read before the write and a 409, where everything in this
// module is a pure function of the payload. Recorded as its own row instead of
// bundled in.
// One message, used by both percent branches below, because they are one rule
// -- and because a reader who hits it needs the CONSEQUENCE, not just the
// range. It says what the number does rather than only what it must be.
const COVERAGE_PERCENT_MESSAGE =
  'Coverage percent must be a number from 0 to 100. Over 100 makes the '
  + 'estimated insurance exceed the charge, so the billing panel shows the '
  + 'patient in credit while the ageing report shows nothing owed; a negative '
  + 'value bills the patient for more than the charge; and a value that is not '
  + 'a number is read as zero per cent, so the patient is billed in full for a '
  + 'procedure their plan covers. Estimates are locked onto a charge when it is '
  + 'created and never recomputed, so a wrong rule keeps its effect on every '
  + 'charge written while it was in place.';

function coverageRuleProblem(record) {
  const r = record || {};
  const payer = String(r.payer == null ? '' : r.payer).trim();
  if (!payer) {
    return 'A coverage rule needs the payer name it applies to. Without one it '
         + 'can never match a patient, so it would sit in the rules table '
         + 'looking like configured coverage while every estimate ignored it.';
  }
  const procedure = String(r.procedure_type_id == null ? '' : r.procedure_type_id).trim();
  if (!procedure) {
    return 'A coverage rule needs the procedure type it applies to. Without one '
         + 'it can never match, so it would sit in the rules table looking like '
         + 'configured coverage while every estimate ignored it.';
  }
  if (typeof r.coverage_percent !== 'number' && typeof r.coverage_percent !== 'string') {
    return COVERAGE_PERCENT_MESSAGE;
  }
  const pct = Number(r.coverage_percent);
  if (!Number.isFinite(pct) || pct < 0 || pct > 100) {
    return COVERAGE_PERCENT_MESSAGE;
  }
  return null;
}

module.exports = {
  paymentProblem, chargeProblem, coverageRuleProblem,
  isPositiveMoney, isNonNegativeMoney,
};
