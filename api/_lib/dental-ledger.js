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

// The four values tp-status can emit. It is a <select> in the browser, so the
// app cannot produce a fifth -- and the generic write accepted any string.
// Kept as an object rather than an array so the lookup cannot be fooled by a
// prototype member: `TX_PLAN_STATUSES['constructor']` is undefined here and
// ['proposed',...].includes is fine too, but a bare {} literal would inherit
// one. Object.create(null) would also do; this matches how DNT_* gate maps are
// written in the handler.
const TX_PLAN_STATUSES = Object.assign(Object.create(null), {
  proposed: true, presented: true, accepted: true, declined: true,
});

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
// NO LONGER APPEND-ONLY, AND THIS PARAGRAPH IS CORRECTED RATHER THAN LEFT.
// It read: "APPEND-ONLY IN FACT ... sdnData('write','dnt_coverage_rules',...)
// appears exactly once, in addCoverageRule(), which only creates." That was
// true when written and stopped being true hours later, when the same session
// added an EDIT path -- saveCoverageRule() re-uses an existing rule's id so the
// upsert updates the row in place. The reasoning it supported still holds, for
// a different reason: an edit is refused only if the percent it is being
// changed TO is out of range, so a legacy rule with a bad percent is not locked
// in -- correcting it is exactly the operation the validator permits.
//
// DUPLICATE RULES ARE NOW REFUSED, in api/sd-data.js rather than here.
// lookupCoverage() uses .find(), so two matching rules meant the applied
// percentage was decided by ROW ORDER -- the same defect the dnt_providers
// branch refuses for linked_employee_id. It is not in this module because it
// needs a READ before the write and a 409, where everything here is a pure
// function of the payload; the handler owns it, and it excludes the row being
// edited by id so an edit does not clash with itself.
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

// ── dnt_denial, THE FOURTH OF THE FIFTEEN (2026-09-05) ────────────────────
// Chosen the same way the first three were: by measuring what a bad row does
// to a number a practice reads, not by which table sounds worst. Every rule
// below is one sairndental.html's own saveDenial() already refuses on. None is
// invented here.
//
// THE ONE THAT MADE IT NEXT IS THE DATE, and it is a different shape from the
// three money rules above -- it does not corrupt a total, it removes a WARNING.
// dnAppealWindow() returns { known, deadline, days }. Given a denied_on it
// cannot parse, dnAddDays() returns '' and dnDaysUntil('') returns null, so the
// row comes back known:true with days:null and the "closing within 14 days"
// filter -- `w.known && w.days !== null && w.days <= 14` -- silently excludes
// it. THE DENIAL DISAPPEARS FROM THE APPEAL-DEADLINE WARNING WHILE STILL
// LOOKING LIKE A DENIAL WITH A KNOWN WINDOW. An appeal window that passes
// unnoticed is money that cannot be recovered afterwards.
//
// AND A ROLLOVER DATE IS WORSE THAN AN UNPARSEABLE ONE, which is why the check
// round-trips instead of trusting `new Date()`. '2026-02-31T00:00:00' is not
// NaN in JavaScript -- it silently becomes 3 March -- so dnAddDays() would
// compute a real-looking appeal deadline counted from a day that never existed.
// A wrong deadline is more dangerous than a missing one, because nothing about
// it looks wrong.
const DENIAL_STAGES = {
  none: true, drafted: true, submitted: true,
  won: true, partial: true, lost: true, abandoned: true,
};

// A calendar date the appeal window can actually be counted from. The
// round-trip is the whole point: see the rollover note above.
function isCalendarDate(v) {
  if (typeof v !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(v)) return false;
  const d = new Date(v + 'T00:00:00');
  if (Number.isNaN(d.getTime())) return false;
  const back = d.getFullYear() + '-'
    + String(d.getMonth() + 1).padStart(2, '0') + '-'
    + String(d.getDate()).padStart(2, '0');
  return back === v;
}

function denialProblem(record) {
  const r = record || {};
  const patientId = String(r.patient_id == null ? '' : r.patient_id).trim();
  if (!patientId) {
    return 'This denial is not attached to a patient, so nothing can show it '
         + 'against the account it belongs to. Send patient_id with the denial.';
  }
  if (!isPositiveMoney(r.amount)) {
    return 'A denied amount must be a number greater than zero. dnAtStake() '
         + 'reads it through Number(x) || 0, so a value that is not a number '
         + 'becomes zero and the denial silently stops counting toward the '
         + 'amount at stake, and a negative one reduces that total below what '
         + 'the other denials really are.';
  }
  if (!isCalendarDate(r.denied_on)) {
    return 'A denial needs the date it was denied, as a real calendar date '
         + '(YYYY-MM-DD). The appeal window is counted from it, and a date that '
         + 'cannot be parsed drops the denial out of the "closing soon" warning '
         + 'while still appearing to have a known window -- so an appeal '
         + 'deadline passes with nothing on screen to say so.';
  }
  if (!DENIAL_STAGES[r.stage]) {
    return 'A denial stage must be one of: '
         + Object.keys(DENIAL_STAGES).join(', ')
         + '. Any other value is not in the app\'s decided-stage table, so the '
         + 'denial counts as still open forever -- it inflates the open count '
         + 'and the amount at stake, and it is never counted in the appeal '
         + 'success rate either way.';
  }
  // recovered is optional; zero is the ordinary value for a denial that
  // recovered nothing, so this is the non-negative test rather than positive.
  if (r.recovered !== undefined && r.recovered !== null && r.recovered !== '') {
    if (!isNonNegativeMoney(r.recovered)) {
      return 'The amount recovered must be a number of zero or more.';
    }
    if (Number(r.recovered) > Number(r.amount)) {
      return 'More was recovered than was denied. The denials panel prints '
           + '"recovered of denied" straight from these two fields, so this row '
           + 'would read as the practice having been paid more than the payer '
           + 'refused.';
    }
  }
  return null;
}

// NOT CHECKED HERE, and recorded so the absence is a decision rather than an
// oversight:
//   * THE APPEAL DATE ORDER -- submitted_on on or after denied_on, decided_on
//     on or after submitted_on. saveDenial() enforces all three, but they are
//     workflow rules about how an appeal proceeded, not rules about whether the
//     row can be added up. Enforcing them server-side would refuse a practice
//     correcting a historical record, which is the one time somebody genuinely
//     needs to write a shape the form would not produce today.
//   * A FUTURE denied_on. saveDenial() refuses it against the browser's local
//     today; this module has no way to know the practice's timezone, and
//     refusing against UTC would reject a denial entered on the correct local
//     day west of UTC in the evening. That is the UTC-midnight trap this
//     platform has already been bitten by.

// ── FIFTH RESOURCE: dnt_procedure_types ───────────────────────────────────
// The first one in this file that is NOT a ledger row, which is worth saying
// out loud rather than quietly widening the header: a procedure type is the
// practice's fee schedule and its CDT coding record. It lives here because it
// is the ROOT the four rows above compute from -- setChargeProcedure() seeds
// ch-add-amount from default_fee, tpItemMoney() seeds the plan item from it,
// and computeEstimatedInsurance() is handed it directly -- and because it
// needs isCalendarDate(), which already carries the rollover discipline the
// denial pass worked out. A second module would have copied that helper.
//
// IT IS THE HIGHEST-STAKES OF THE NINE THAT WERE LEFT, and the reason is a
// gate that is missing rather than a number that is wrong. dnt_procedure_types
// is NOT in DNT_FINANCIAL_RESOURCES and the write branch role-gates exactly one
// resource (dnt_providers), so ANY authenticated role -- provider, hygienist,
// assistant -- can write this practice's fee schedule, and until now the only
// thing checked was that payload.id was present.
//
// NO LEGACY-ROW COST, checked rather than assumed. sdnData('write',
// 'dnt_procedure_types', ...) appears exactly ONCE in sairndental.html, in
// addProcedureType(), which only creates. There is no edit path at all --
// removeProcedureType() is local-only and says so -- so nothing re-sends an
// existing row and nothing existing can be blocked by this. Same standing as
// dnt_payments, and the opposite of the guardian rule.
//
// ── THE RULES, EVERY ONE ALREADY REFUSED BY THE BROWSER ───────────────────
//
//   1. CODE AND DESCRIPTION. addProcedureType() refuses `!code || !desc`
//      outright. rProcedures() renders H(p.cdt_code) into the first column and
//      cdtStatusFor() falls back to the literal string 'this code' when it is
//      missing, so a code-less row is a blank cell in the fee schedule and an
//      unnamed code in every compliance message about it. The CDT code is also
//      what goes on the claim: a charge built from a procedure type with no
//      code is a charge nobody can bill.
//
//   2. THE EFFECTIVE WINDOW MUST BE A REAL CALENDAR DATE. The browser cannot
//      produce anything else -- pc-add-efffrom and pc-add-effto are
//      <input type="date">, which yields zero-padded ISO or nothing -- so this
//      enforces what the form already guarantees rather than inventing a rule.
//
//      AND IT MATTERS MORE THAN A TYPE CHECK USUALLY DOES, because
//      cdtStatusFor() compares these as STRINGS:
//          if (from && serviceDate < from)  -> 'future'
//          if (to   && serviceDate > to)    -> 'retired'
//      Lexicographic comparison is correct for zero-padded ISO and silently
//      wrong for anything else. '2026-1-5' is a date a human would read as
//      January; against it, a March service date compares '2026-03-01' <
//      '2026-1-5' -> TRUE, and the panel reports that the code "did not take
//      effect until 2026-1-5" for a service four months after it did. The
//      verdict is inverted, confidently, with a real-looking date in the
//      sentence.
//
//   3. THE WINDOW MUST NOT BE INVERTED. addProcedureType() refuses this in the
//      browser with its own reason recorded -- "an inverted window makes every
//      date-of-service check on this code meaningless in both directions" --
//      and re-measuring it here confirms something sharper than "meaningless":
//      with effective_to before effective_from, EVERY service date satisfies
//      one branch or the other, so cdtStatusFor() can never return 'ok'. The
//      code reads as not-yet-in-effect or retired forever, on every
//      appointment, which is a compliance check that has quietly stopped being
//      capable of passing.
//
//   4. A PRESENT default_fee MUST BE A NUMBER. addProcedureType() stores
//      `isNaN(fee) ? 0 : fee` from parseFloat, so the browser can only ever
//      store a number. A string fee reaches tpItemMoney() as
//      Number(proc.default_fee || 0) -- and 'abc' is truthy, so the || 0 never
//      fires and the plan total renders NaN. Checked only when SENT: absent is
//      a legitimate shape, because that same expression turns undefined into 0.
//
// ── DELIBERATELY NOT CHECKED, so each absence is a decision ────────────────
//   * A NEGATIVE default_fee. parseFloat('-50') is not NaN, so the browser
//     stores it and the practice may well mean it -- an adjustment or credit
//     code is a real thing. This module does not get to overrule the form.
//   * default_length_minutes and recall_months, for the same reason on sign,
//     and because a bad recall_months is inert: recallDueProcedures() filters
//     on Number(p.recall_months) > 0, so a negative or non-numeric value reads
//     as "we do not recall on this", which is the correct answer for most
//     codes anyway.
//   * cdt_version and superseded_by. Free text that nothing parses --
//     cdtMaintenance() counts editions by whatever string is there and
//     cdtStatusFor() prints superseded_by verbatim. Constraining them would be
//     inventing a vocabulary the practice never agreed to.
//   * THAT superseded_by NAMES A REAL CODE. That is a read before every write,
//     the same round trip this file already declines for "does the patient
//     exist".
//   * UNIQUENESS OF cdt_code. Not the coverage-rule shape, and that was
//     checked rather than assumed: every reader resolves a procedure by
//     `find(p => p.id === ...)`, never by code, so two rows sharing a CDT code
//     do not put the applied value at the mercy of row order the way two
//     matching coverage rules do.
function procedureTypeProblem(record) {
  const r = record || {};
  const code = String(r.cdt_code == null ? '' : r.cdt_code).trim();
  if (!code) {
    return 'A procedure type needs its CDT code. The fee schedule prints it as '
         + 'the first column, every compliance message about the code names it, '
         + 'and it is what goes on the claim -- a charge built from a procedure '
         + 'type with no code is a charge nobody can bill.';
  }
  const desc = String(r.description == null ? '' : r.description).trim();
  if (!desc) {
    return 'A procedure type needs a description. The picker renders it as '
         + '"code -- description", so without one the person choosing a '
         + 'procedure is picking from bare codes.';
  }
  const from = r.effective_from == null ? '' : String(r.effective_from);
  const to = r.effective_to == null ? '' : String(r.effective_to);
  if (from !== '' && !isCalendarDate(from)) {
    return 'The effective-from date must be a real calendar date (YYYY-MM-DD). '
         + 'cdtStatusFor() compares it against the date of service as a STRING, '
         + 'which is only correct for that exact zero-padded shape -- against '
         + 'anything else the in-effect check silently returns the wrong '
         + 'verdict rather than failing.';
  }
  if (to !== '' && !isCalendarDate(to)) {
    return 'The retirement date must be a real calendar date (YYYY-MM-DD), for '
         + 'the same reason as the effective-from date: the retired-code check '
         + 'is a string comparison against the date of service, and any other '
         + 'shape makes it answer confidently and wrongly.';
  }
  if (from !== '' && to !== '' && to < from) {
    return 'The retirement date is before the effective date. That window '
         + 'cannot be checked against any date of service -- every date is '
         + 'either before the start or after the end, so this code would report '
         + 'as not-yet-in-effect or retired on every appointment and could '
         + 'never come back "in effect".';
  }
  if (r.default_fee !== undefined && r.default_fee !== null && r.default_fee !== '') {
    if (typeof r.default_fee === 'boolean' || !Number.isFinite(Number(r.default_fee))) {
      return 'The default fee must be a number. A treatment-plan item seeded '
           + 'from this code reads it as Number(default_fee || 0), and a '
           + 'non-numeric value is truthy -- so the fallback never fires and '
           + 'the plan total renders NaN.';
    }
  }
  return null;
}

// ── SIXTH RESOURCE: dnt_txplans (2026-09-10) ──────────────────────────────
// A treatment plan is a PRICED PROPOSAL -- the money a patient is being asked
// to accept -- which is why the write branch already gates it behind
// DNT_FINANCIAL_ROLES and why the criticality register tiers it A. What was
// missing is the payload shape: every rule below is one `saveTxPlan()` already
// enforces in the BROWSER and nothing else, the same shape as the guardian
// rule and 45 CFR 149.610(c)(1).
//
// FIVE FAILURE SHAPES, EACH MEASURED AGAINST THE REAL READERS RATHER THAN
// REASONED ABOUT. Run in node against the actual expressions from
// sairndental.html:
//
//   1. A NON-ARRAY `items` TAKES THE WHOLE PANEL DOWN, not just its own row.
//      rTxPlans() maps over every plan and calls tpPlanTotals(), which does
//      `(plan.items||[]).forEach(...)`. Measured: items "abc", {a:1}, 42 and
//      true each throw `TypeError: forEach is not a function` -- and the throw
//      happens inside the .map() building the table body, so ONE bad row
//      renders no treatment plans at all. Every other shape here is a wrong
//      number; this one is a blank screen.
//
//   2. A NEGATIVE ITEM FEE REDUCES THE OPEN-VALUE KPI. tpItemMoney() is
//      `Number(item.fee)||0` and there is NO clamp anywhere in the plan path
//      -- not in tpPlanTotals(), not in rTxPlans()'s
//      `open.reduce((s,p) => s + tpPlanTotals(p).fee, 0)`. Measured: items
//      [100, -500] give an open value of -400. Same family as the negative
//      payment that opened this file, and unlike dnt_charges there is no
//      second view that floors at zero -- so nothing disagrees and nothing
//      flags it.
//
//   3. A NON-NUMERIC FEE CONTRIBUTES 0 WHILE THE ITEM STILL SHOWS. Measured:
//      [100, 'abc'] totals 100, and the row's "Items" cell still counts 2.
//      An item visible in the plan and absent from its total, on one screen --
//      the same shape as the charges case.
//
//   4. A STATUS OUTSIDE THE FOUR-VALUE VOCABULARY FALLS OUT OF BOTH KPIs.
//      rTxPlans() filters `status==='proposed'||status==='presented'` for open
//      and `accepted||declined` for decided. Measured on
//      ['Accepted','accepted','proposed','weird']: open=1, decided=1, and TWO
//      plans in neither. So the plan lists in the table, contributes to no
//      KPI, and is invisible to the case-acceptance rate. The browser can only
//      produce the four because tp-status is a <select>; this handler accepts
//      any string, and TP_STATUS_LABELS falls back to rendering it raw.
//
//   5. AN ACCEPTED PLAN WITH NO decided_on SITS IN THE ACCEPTANCE DENOMINATOR
//      WITH NO DECISION DATE. saveTxPlan() refuses exactly this and says why:
//      "it would sit in the case-acceptance denominator with an unknowable
//      one. Asked for rather than back-filled with today." The `decided`
//      filter is on STATUS ALONE, so server-side the row counts regardless.
//
// A LEGACY-ROW COST, AND UNLIKE dnt_payments AND dnt_charges IT IS REAL HERE.
// Re-checked for THIS resource rather than carried over: saveTxPlan() does
// `if (tpEditId) { list = list.map(x => x.id === tpEditId ? rec : x); }`, so
// plans are EDITED, not only created. An existing plan that predates a rule --
// an accepted one with no decided_on -- becomes unwritable until it is fixed.
//
// BUT THE COST IS BOUNDED, AND THAT WAS CHECKED RATHER THAN ASSUMED. There is
// no bulk re-upload path to walk old rows into this gate: `dnt_txplans`
// appears in `DNT_SYNC_RESOURCES`, but sairndental.html states at that map
// that "dntSyncFromServer() only READS", and the only
// `sdnData('write','dnt_txplans',...)` call in the app is saveTxPlan(). So the
// refusal reaches exactly one place -- a human editing that one plan, with a
// message naming what to fix -- and never a background sweep.
// Same trade-off the guardian rule took and flagged, and the same judgement:
// refusing loudly with a message that names the fix beats quietly persisting a
// shape the practice's own form forbids. Flagged rather than buried.
//
// ── WHAT IS DELIBERATELY NOT VALIDATED ────────────────────────────────────
//   * A FUTURE decided_on. saveTxPlan() refuses it against dntLocalToday();
//     this module has no way to know the practice's timezone, and refusing
//     against UTC would reject a plan decided on the correct local day west of
//     UTC in the evening. That is the UTC-midnight trap, and it is the same
//     call denialProblem() made above for denied_on -- not a fresh decision,
//     and recorded so nobody adds it thinking it was forgotten.
//   * provider_id. The modal sends `$('tp-provider').value`, which can be
//     empty, so requiring it would refuse a shape the form itself produces.
//   * item.phase. tpPhases() reads `Number(it.phase)||1`, so a bad phase
//     merges into phase 1 -- a mis-grouped item, not a wrong total.
//   * item.procedure_type_id. Absent, the item still totals from its own fee
//     and tpIsStarted() simply never matches it. Requiring it would block a
//     plan item the practice priced by hand.
function txPlanProblem(record) {
  const r = record || {};
  if (String(r.patient_id == null ? '' : r.patient_id).trim() === '') {
    return 'A treatment plan must name a patient. Without patient_id the plan '
         + 'renders as "(unknown patient)" and tpItemMoney() is handed an empty '
         + 'payer, so every item silently falls to uncovered and the insurance '
         + 'estimate reads 0 rather than unknown.';
  }
  if (String(r.title == null ? '' : r.title).trim() === '') {
    return 'A treatment plan needs a title -- a patient shown two untitled '
         + 'plans cannot tell them apart. This is the rule saveTxPlan() '
         + 'already refuses on.';
  }
  if (!Array.isArray(r.items)) {
    return 'items must be an array. tpPlanTotals() does '
         + '(plan.items||[]).forEach(...) inside the .map() that builds the '
         + 'table, so a non-array value throws there and NO treatment plans '
         + 'render at all -- one bad row blanks the whole panel.';
  }
  if (r.items.length === 0) {
    return 'A plan with no items is not a plan -- add at least one procedure. '
         + 'An empty accepted plan counts in the case-acceptance numerator '
         + 'while contributing nothing to open value.';
  }
  for (let i = 0; i < r.items.length; i += 1) {
    const it = r.items[i] || {};
    if (it.fee === undefined || it.fee === null || it.fee === '') continue;
    if (!isNonNegativeMoney(it.fee)) {
      return 'Item ' + (i + 1) + ' has fee ' + JSON.stringify(it.fee)
           + '. A plan item fee must be a number and cannot be negative: '
           + 'tpItemMoney() reads Number(item.fee)||0 with no clamp anywhere '
           + 'in the plan path, so a negative fee REDUCES the open treatment '
           + 'value, and a non-numeric one contributes 0 while the item still '
           + 'shows in the plan.';
    }
  }
  const status = String(r.status == null ? '' : r.status).trim();
  if (!TX_PLAN_STATUSES[status]) {
    return 'status must be one of proposed, presented, accepted or declined '
         + '(got ' + JSON.stringify(r.status) + '). rTxPlans() filters open on '
         + 'proposed/presented and decided on accepted/declined, so any other '
         + 'value puts the plan in NEITHER -- it lists in the table and '
         + 'contributes to no KPI, including the case-acceptance rate.';
  }
  if (status === 'accepted' || status === 'declined') {
    if (!isCalendarDate(r.decided_on)) {
      return 'An accepted or declined plan needs decided_on as a YYYY-MM-DD '
           + 'date, and it is not assumed to be today. The decided filter is '
           + 'on status alone, so without it the plan sits in the '
           + 'case-acceptance denominator with an unknowable decision date.';
    }
  } else if (r.decided_on !== undefined && r.decided_on !== null
             && String(r.decided_on).trim() !== '') {
    // saveTxPlan() stores '' for a plan that is not decided. A malformed value
    // carried on an undecided plan becomes the denominator problem above the
    // moment somebody marks it accepted, so it is refused now rather than
    // later.
    if (!isCalendarDate(r.decided_on)) {
      return 'decided_on must be empty or a YYYY-MM-DD date (got '
           + JSON.stringify(r.decided_on) + ').';
    }
  }
  return null;
}

module.exports = {
  paymentProblem, chargeProblem, coverageRuleProblem, denialProblem,
  procedureTypeProblem, txPlanProblem,
  isPositiveMoney, isNonNegativeMoney, isCalendarDate,
};
