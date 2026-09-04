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

module.exports = { paymentProblem, isPositiveMoney };
