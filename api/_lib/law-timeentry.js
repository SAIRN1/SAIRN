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

const NO_CODE_MESSAGE =
  'A time entry needs a UTBMS billing code. This record is what invoices and '
  + 'the LEDES export are built from, so an hour stored without one cannot be '
  + 'billed under client guidelines that require a code -- and nothing '
  + 'downstream reports it: it renders as a normal billable hour with an empty '
  + 'column. Pick a code in the Log Time modal and save again.';

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
  return null;
}

module.exports = {
  timeEntryProblem,
  MAX_BILLING_CODE_CHARS,
  NO_CODE_MESSAGE,
};
