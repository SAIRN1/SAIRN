// api/_lib/law-timeentry.js
//
// THE SERVER GATE ON A BILLABLE HOUR'S UTBMS CODE.
//
// ── THE GAP THIS CLOSES, AND THE APP FILE ALREADY DESCRIBED IT ─────────────
// sairnlaw.html's own comment above LAW_BILLING_CODES says it plainly:
//
//     "saveTime() has no billing-code validation, so it wrote billing_code:''
//      into law_timeentries AND SYNCED IT: a billable hour with no UTBMS code,
//      silently, on the exact record invoices and LEDES export are built from."
//
// ── AND THE LEDES EXPORT IN THAT SENTENCE DOES NOT EXIST (corrected 2026-09-21)
// Quoted above as it was written, because that is what the app said; but this
// module then repeated the claim in its OWN voice, twice, including in the
// refusal a firm reads on screen. Measured: sairnlaw.html has six occurrences
// of "LEDES" and NO export function of any kind -- no exporter, no
// downloadObjectURL, no CSV writer, nothing. Five of the six are the published
// UTBMS/LEDES STANDARD, which does exist and which those lines are right to
// cite; the sixth is a FEATURE OF THIS APP that was never built.
//
// THE GATE IS JUSTIFIED BY INVOICES ALONE AND DOES NOT NEED THE SECOND
// CONSUMER. What it cannot do is stand on one that is not there: a header
// naming a downstream artefact nobody can find sends the next reader looking
// for it, and a user-facing refusal naming it tells a firm their data feeds an
// export they do not have. The absence is now a TRACKED GAP -- see the
// SAIRNlaw LEDES row in docs/SAIRN-OPEN-WORK-INDEX.md -- rather than a
// premise. Found as FINDING 5 of the independent review of this module.
//
// That was fixed on 2026-09-09 by making the code list a CONSTANT, so the
// <select> can no longer render empty. THAT CLOSED THE CAUSE AND NOT THE GATE.
// saveTime() still writes `billing_code:$('ttcode').value` with no check, and
// until now the server accepted whatever arrived -- `billing_code` appeared in
// NO validator anywhere in api/, measured: zero hits across api/sd-data.js and
// api/_lib/*.js. A client-side fix that depends on one <select> staying
// populated is not a gate; it is the absence of one, working.
//
// ── WHAT IT REFUSES, AND IT IS DELIBERATELY NARROW ─────────────────────────
// Presence and shape. A missing, non-string, or blank-after-trim code is
// refused, because an hour recorded with no code is not a partially-good row:
// it is a row that cannot be put on an invoice governed by client billing
// guidelines, and nothing downstream will say so.
//
// ── AND IT IS NOT A MEMBERSHIP CHECK. THAT IS THE DECISION, NOT AN OMISSION ─
// The obvious next step is to check the code against the 27 in
// LAW_BILLING_CODES. It is refused for two reasons and the first is decisive:
//
//   1. THAT LIST IS FLAGGED UNVERIFIED BY THE APP ITSELF -- "entered from
//      memory of the published UTBMS Litigation set, to be verified against the
//      official UTBMS/LEDES list before real billing." Encoding a
//      possibly-wrong list as a REFUSAL points the error in the dangerous
//      direction: a firm types a genuine UTBMS code that the list happens to
//      have wrong or to be missing, and the server rejects real work. A gate
//      should fail toward accepting a valid code, never toward refusing one.
//   2. It would be a SECOND COPY of a vocabulary that lives in the app file,
//      free to drift from the reader it is protecting -- the same argument
//      dental-ledger.js makes when it exports DAY_NAMES so there is one list
//      and not two.
//
// So the server answers the question it can answer from the payload alone, and
// says here that it is not answering the other one.
//
// ── NOT ADDED, AND NAMED RATHER THAN LEFT SILENT ──────────────────────────
// saveTime() also validates `matter_id` (required) and `hours` (> 0) in the
// browser, and the server checks NEITHER. Those are the same shape as this gap
// and they are real; they are out of scope here because this change was asked
// for as the billing-code fix, and widening it silently would make the diff
// stop matching its own reason. Recorded so the next reader knows the absence
// was seen.
'use strict';

// A generous ceiling rather than a format. UTBMS codes in the shipped list are
// four characters (L100, A101, E101), but the published standard has grown
// before and this module has already refused to assert what the valid set is --
// so it bounds the field instead of describing it. What this stops is a pasted
// paragraph or a whole document landing in a column an invoice prints.
const MAX_BILLING_CODE_CHARS = 32;

// The LEDES export was removed from this sentence on 2026-09-21: this app has
// no exporter, so the refusal a firm reads was naming a feature they do not
// have. Invoices alone carry the reason and are the thing actually built from
// these rows.
const NO_CODE_MESSAGE =
  'A time entry needs a UTBMS billing code. This record is what invoices are '
  + 'built from, so an hour stored without one cannot be '
  + 'billed under client guidelines that require a code -- and nothing '
  + 'downstream reports it: it renders as a normal billable hour with an empty '
  + 'column. Pick a code in the Log Time modal and save again.';

const NO_RATE_MESSAGE =
  'A BILLABLE hour needs an hourly rate above zero. The invoice total is '
  + 'hours x rate, so an hour stored at rate 0 adds $0.00 to the bill while '
  + 'showing in the billing table as an ordinary billable hour -- the work is '
  + 'recorded, the fee is not, and nothing downstream says so. Enter the rate '
  + 'in the Log Time modal, or untick Billable if this hour is no-charge.';

function timeEntryProblem(record) {
  const r = record || {};
  if (typeof r.billing_code !== 'string') {
    // Not folded in with the blank case. `undefined` means a caller that never
    // set the field -- a new write path, an import, a partial payload -- and
    // saying so is what tells the next person WHICH of the two happened.
    return NO_CODE_MESSAGE
      + ' (no billing_code was sent at all; it was ' + typeof r.billing_code + ')';
  }
  const code = r.billing_code.trim();
  if (!code) {
    return NO_CODE_MESSAGE
      + ' (billing_code arrived empty, which is what an unpopulated code list '
      + 'used to produce)';
  }
  if (code.length > MAX_BILLING_CODE_CHARS) {
    return 'billing_code is ' + code.length + ' characters. A UTBMS code is a '
      + 'short identifier and the limit here is ' + MAX_BILLING_CODE_CHARS
      + '; a value this long is a pasted description rather than a code, and it '
      + 'would print into an invoice column as if it were one.';
  }
  // ── A BILLABLE HOUR AT RATE ZERO IS THE SAME DEFECT ONE FIELD OVER ───────
  // Added 2026-09-21 by cc, from FINDING 3 of the independent review of this
  // module (obligation 2026-09-18T23:44:59Z). The review that opened it named
  // matter_id and hours as the two fields left to the client; there were
  // THREE, and the third is the one with the money on it.
  //
  // saveTime() checked matter_id (required) and hours (> 0) and then wrote
  // `rate: Number($('ttrate').value)||0` -- a blank or unparseable rate became
  // ZERO, silently, with no complaint at either end. saveInvoice() computes
  // the invoice total as hours * rate, so such an hour contributes $0.00 and
  // renders in the billing table as an ordinary billable hour. It is the
  // codeless-hour defect exactly, and arguably worse: a codeless hour at least
  // shows '--' in the code column, while a zero-rate hour shows a number.
  //
  // ONLY WHEN THE ENTRY IS BILLABLE, and that is the whole scope of it. A
  // no-charge entry legitimately carries rate 0 -- that is what no-charge
  // MEANS -- and refusing it would refuse real work. `billable` is read the
  // same way every reader in sairnlaw.html reads it (`t.billable && ...`), so
  // an ABSENT billable field is no-charge here too, and the module does not
  // invent a stricter meaning than the app's own.
  //
  // THE TYPE IS REQUIRED, NOT COERCED, and that is a deliberate difference
  // from how this module treats billing_code. There the refusal to assert a
  // vocabulary was right because the valid SET is unverified; a numeric rate
  // has no such uncertainty, the app itself always sends a Number, and
  // accepting the string '350' would store a string in a column an invoice
  // multiplies -- the validate-one-thing/store-another seam this module was
  // criticised for in FINDING 1 of the same review. A caller sending a string
  // is told exactly what to send instead.
  //
  // NOT ADDED, AND NAMED RATHER THAN LEFT SILENT: `hours` is still unchecked
  // at the server, and hours 0 produces the identical $0.00 line. It is the
  // same defect and it is deliberately NOT bundled here, because the scope
  // asked for was the rate. Recorded in docs/SAIRN-OPEN-WORK-INDEX.md so the
  // absence is a tracked gap rather than an oversight.
  if (r.billable) {
    if (typeof r.rate !== 'number' || !isFinite(r.rate)) {
      return NO_RATE_MESSAGE + ' (rate arrived as ' + typeof r.rate
        + (typeof r.rate === 'string' ? ' -- send a number, not a string' : '')
        + ', so nothing could be multiplied by it)';
    }
    if (r.rate <= 0) {
      return NO_RATE_MESSAGE + ' (rate arrived as ' + r.rate
        + '. If this hour is genuinely not being charged for, untick Billable '
        + 'rather than leaving the rate blank -- a no-charge entry is allowed '
        + 'to have no rate, and it says so on the invoice.)';
    }
  }
  return null;
}

module.exports = {
  timeEntryProblem,
  MAX_BILLING_CODE_CHARS,
  NO_CODE_MESSAGE,
  NO_RATE_MESSAGE,
};
