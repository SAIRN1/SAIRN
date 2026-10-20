// api/_lib/law-attest.js
// ---------------------------------------------------------------------------
// THE IOLTA RECONCILIATION ATTESTATION -- the POLICY and the CANONICAL RECORD.
// No I/O, no transport, no database. The route is api/law-attest.js; the
// design it implements is docs/2026-10-19-hank-b21-attestation-design.md.
//
// ── THE ONE-LINE CONCEPT, WHICH IS THE THING TO ATTACK FIRST ──────────────
// A completed three-way reconciliation becomes an ATTESTED record only when a
// bar-admitted person signs a hash of the exact comparison that was run; a
// firm that has EXACTLY ONE active owner/attorney may switch on a per-firm
// single-signer setting and attest alone, and every attestation taken that way
// is stored as signer_mode 'single' -- so the record never claims two people
// looked when one did.
//
// That is Michael's answer to the one question the design note could not close
// (§6). It is a HYBRID of its answers (2) and (3), and neither half stands
// alone: (2) on its own is the thing SAIRNlaw's own countersign schema already
// refused once -- "a legal requirement is not something a licensee turns off in
// Settings" -- and (3) on its own leaves a solo attorney with no route at all.
//
// ── SO THE SETTING IS NOT A PREFERENCE ────────────────────────────────────
// It is a STATEMENT ABOUT THE FIRM'S STAFFING, accepted only while that
// statement is true. Two enforcement points, and THE SECOND IS THE ONE THAT
// MATTERS:
//
//   1. at SET time   -- a firm with two bar-admitted employees cannot turn it on
//   2. at ATTEST time -- the count is re-derived on EVERY single-signer
//      attestation, so a firm that switched it on as a solo and later hired a
//      second attorney does not keep the route. A check that runs only at set
//      time is an authorisation that outlives its own precondition.
//
// AND THE COUNT FAILS CLOSED. `null` means the employee table could not be
// read, and the answer to could-not-tell on a record a bar auditor reads is
// REFUSAL -- never "one, so go ahead". That is why the count is a nullable
// number here rather than a boolean computed upstream: a boolean cannot carry
// the third state and would arrive as `false`, which reads as "not eligible"
// and is a different (and in this direction, luckier) answer than the truth.
//
// ── WHAT THIS DOES NOT WEAKEN ─────────────────────────────────────────────
// api/_lib/countersign.js states in its own header that it has no
// `require_two_person` policy table, no `set_policy` action, and NO
// SELF-SIGNATURE, EVER. None of the three is touched. The single-signer path
// does not go through the countersignature token at all -- it is a separate,
// named path, and the shared lock keeps refusing a self-signature exactly as
// before. A solo attestation is a DIFFERENT KIND OF RECORD, not the same
// record with a check switched off, and `signer_mode` is what carries that
// difference into the row.
//
// ── WHAT AN ATTESTATION DOES NOT CLAIM ────────────────────────────────────
// That the figures are RIGHT. It records that a qualified person looked and
// signed. The same sentence is in api/_lib/countersign.js's header for the
// same reason, and the design note's non-goal 1 makes it a requirement rather
// than a caveat: an attestation that reads as a correctness guarantee is the
// wrong-model-that-looks-like-compliance failure.
//
// ONE EXCEPTION, AND IT IS CONSISTENCY RATHER THAN CORRECTNESS. A record whose
// verdict is AGREES while its three legs hold three different numbers is a lie
// on its face, and it is the shape a fabricated verdict takes. That ONE
// condition is refused (`VERDICT_INCONSISTENT`). Nothing here checks whether
// the legs themselves are the right numbers, and nothing here could.
// ---------------------------------------------------------------------------

'use strict';

const lawRoles = require('./law-roles');

// The locked resource name, spelled ONCE. The route's profile, the token row's
// `resource` column, the content hash and the attestation row all have to agree
// about this string, and four copies of a literal is the drift that cost b18 a
// round of red arms.
const ATTEST_RESOURCE = 'law_trust_attestation';

// The settings key. Also spelled once, for the same reason.
const SETTING_KEY = 'trust_attestation_single_signer';

// The two signer modes. SPELLED, not a boolean, the same argument
// api/_lib/countersign.js makes for MODE_ALWAYS/MODE_PREPARED_ONLY: `dual` and
// `single` are two different claims about a record and a true/false would read
// as the same claim with opposite values. These strings are STORED, so a bar
// auditor reads them years later -- they are part of the record, not an
// implementation detail.
const SIGNER_MODE_DUAL = 'dual';
const SIGNER_MODE_SINGLE = 'single';

// The verdicts a three-way reconciliation can reach. CANNOT_RECONCILE is a
// real answer and not an error: a firm whose bank statement has not arrived
// has not failed to reconcile, it has not been able to, and collapsing that
// into DISAGREES would record a discrepancy that was never measured.
const VERDICTS = Object.freeze(['AGREES', 'DISAGREES', 'PARTIAL', 'CANNOT_RECONCILE']);

// The exact field set of a comparison. CLOSED, and unknown keys are REFUSED
// rather than dropped: the hash is computed over this object, so a key this
// module silently discarded would be a value the signer saw and the record
// does not carry -- a signature over something other than what was shown.
const COMPARISON_FIELDS = Object.freeze([
  'bank_balance_cents', 'ledger_balance_cents', 'client_subledger_total_cents',
  'bank_as_of', 'ledger_as_of', 'subledger_as_of',
  'verdict', 'negative_balances'
]);

const CENT_FIELDS = Object.freeze([
  'bank_balance_cents', 'ledger_balance_cents', 'client_subledger_total_cents'
]);
const DATE_FIELDS = Object.freeze(['bank_as_of', 'ledger_as_of', 'subledger_as_of']);

const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

function refuse(code, message) {
  return { refused: { code: code, message: message } };
}

/**
 * Normalise and validate the comparison that is about to be attested.
 *
 * Returns `{ comparison }` on acceptance -- a NEW object carrying exactly
 * COMPARISON_FIELDS, in no particular order (the hash sorts keys itself) --
 * or `{ refused: { code, message } }`.
 *
 * INTEGER CENTS, NEVER FLOATS, and a string is refused rather than coerced.
 * api/_lib/law-trust-reconcile.js already computes in cents and sairnlaw.html
 * already sends `client_total_cents`, so accepting 1234.00 here would let a
 * rounding difference manufacture the very discrepancy the record exists to
 * settle. `Number.isSafeInteger` is the test and not `Number.isInteger`,
 * because a balance beyond 2^53 cents has already lost precision before it
 * arrived and storing it would be recording a number nobody can reproduce.
 */
function normaliseComparison(input) {
  if (!input || typeof input !== 'object' || Array.isArray(input)) {
    return refuse('COMPARISON_REQUIRED',
      'The comparison that was run is required -- the three leg balances, '
      + 'their as-of dates and the verdict. Nothing was attested.');
  }
  const unknown = Object.keys(input).filter((k) => COMPARISON_FIELDS.indexOf(k) === -1);
  if (unknown.length) {
    return refuse('COMPARISON_UNKNOWN_FIELD',
      'The comparison carries fields this attestation does not store: '
      + unknown.join(', ') + '. They are REFUSED rather than dropped, because '
      + 'a value the signer saw and the record does not carry is a signature '
      + 'over something other than what was shown.');
  }
  const out = {};
  for (const f of CENT_FIELDS) {
    const v = input[f];
    if (typeof v !== 'number' || !Number.isSafeInteger(v)) {
      return refuse('CENTS_NOT_INTEGER',
        f + ' must be a whole number of CENTS as a number, not ' + typeof v
        + '. Trust balances are held in integer cents everywhere in this app; '
        + 'a float here could manufacture the discrepancy the reconciliation '
        + 'exists to settle.');
    }
    out[f] = v;
  }
  for (const f of DATE_FIELDS) {
    const v = input[f];
    if (typeof v !== 'string' || !DATE_RE.test(v)) {
      return refuse('AS_OF_DATE_REQUIRED',
        f + ' must be a YYYY-MM-DD date. A balance with no as-of date is not '
        + 'a leg of a reconciliation -- it is a number.');
    }
    out[f] = v;
  }
  if (VERDICTS.indexOf(input.verdict) === -1) {
    return refuse('VERDICT_UNKNOWN',
      'verdict must be one of: ' + VERDICTS.join(', ') + '.');
  }
  out.verdict = input.verdict;

  // The negative-balance list. An EMPTY ARRAY and an ABSENT key are the same
  // fact here -- "no client sub-ledger is negative" -- so absent normalises to
  // `[]` and the key always exists on the stored record. A consumer cannot
  // tell an absent key from a cannot-tell, and only one of those is honest.
  const neg = input.negative_balances === undefined || input.negative_balances === null
    ? [] : input.negative_balances;
  if (!Array.isArray(neg)) {
    return refuse('NEGATIVE_BALANCES_SHAPE',
      'negative_balances must be an array of { client_id, cents } with cents '
      + 'below zero, or absent if none.');
  }
  const cleanNeg = [];
  for (const row of neg) {
    if (!row || typeof row !== 'object' || Array.isArray(row)
        || typeof row.client_id !== 'string' || !row.client_id
        || typeof row.cents !== 'number' || !Number.isSafeInteger(row.cents)
        || row.cents >= 0) {
      return refuse('NEGATIVE_BALANCES_SHAPE',
        'Each negative_balances entry must be { client_id: string, cents: a '
        + 'whole number below zero }. A non-negative entry in this list is a '
        + 'contradiction, not a rounding question.');
    }
    cleanNeg.push({ client_id: row.client_id, cents: row.cents });
  }
  out.negative_balances = cleanNeg;

  // ── THE ONE CONSISTENCY REFUSAL (see the header) ────────────────────────
  // AGREES means the three legs hold the same number. If they do not, the
  // verdict contradicts the figures printed beside it on the same row, and a
  // bar auditor reading it back is misled by the record rather than by the
  // firm. This is NOT a correctness check: it says nothing about whether the
  // three numbers are the right ones.
  if (out.verdict === 'AGREES') {
    const legs = CENT_FIELDS.map((f) => out[f]);
    if (legs[0] !== legs[1] || legs[1] !== legs[2]) {
      return refuse('VERDICT_INCONSISTENT',
        'The verdict says AGREES and the three legs are ' + legs.join(' / ')
        + '. A record cannot attest agreement between figures that differ. '
        + 'Nothing was attested. (This checks the record against itself, not '
        + 'the figures against the bank.)');
    }
  }
  return { comparison: out };
}

/**
 * May this firm hold the single-signer setting ON?
 *
 * `activeBarAdmitted` is the count of CURRENTLY ACTIVE owner/attorney
 * employees, or `null` for "could not be read".
 *
 * Used at BOTH enforcement points -- set_policy and attest -- which is the
 * whole reason it is one function. Two spellings of "exactly one" would be two
 * places to get it wrong, and the set-time one is the copy nobody would
 * re-read.
 */
function singleSignerEligible(activeBarAdmitted) {
  if (activeBarAdmitted === null || activeBarAdmitted === undefined) {
    return refuse('ELIGIBILITY_UNKNOWN',
      'How many bar-admitted employees this firm has could not be read, so '
      + 'whether it may attest with a single signer is unknown. Nothing was '
      + 'changed and nothing was attested -- could-not-tell is not "one".');
  }
  if (typeof activeBarAdmitted !== 'number' || !Number.isInteger(activeBarAdmitted)
      || activeBarAdmitted < 0) {
    return refuse('ELIGIBILITY_UNKNOWN',
      'The count of bar-admitted employees was not a whole number, so '
      + 'eligibility is unknown. Nothing was changed.');
  }
  if (activeBarAdmitted === 1) return { eligible: true, count: 1 };
  if (activeBarAdmitted === 0) {
    return refuse('SINGLE_SIGNER_NO_ATTORNEY',
      'This firm has no active attorney or owner on its roster, so there is '
      + 'nobody who can attest a trust reconciliation at all -- with one '
      + 'signature or two.');
  }
  return refuse('SINGLE_SIGNER_NOT_SOLO',
    'This firm has ' + activeBarAdmitted + ' active bar-admitted employees, so '
    + 'a trust reconciliation is attested by one of them and countersigned by '
    + 'another. The single-signer setting is for a firm with exactly one, and '
    + 'it is refused here rather than ignored.');
}

/**
 * Which path is this attestation taking, if any?
 *
 *   { mode: 'dual' }    -- a countersignature token was presented; the shared
 *                          lock in api/_lib/countersign.js decides whether it
 *                          is good. THIS FUNCTION NEVER APPROVES A SIGNATURE.
 *   { mode: 'single' }  -- no token, the setting is on, and the firm has
 *                          exactly one active bar-admitted employee.
 *   { refused: {...} }  -- everything else.
 *
 * `callerRole` is the role read from the EMPLOYEE ROW, not from the session
 * token -- the route's `activeCaller()` does that, and the reason is in
 * api/_lib/countersign-endpoint.js: a session outlives a demotion.
 */
function decideAttestation(ctx) {
  const c = ctx || {};
  if (!lawRoles.LAW_BAR_ADMITTED_ROLES[c.callerRole]) {
    return refuse('NOT_BAR_ADMITTED',
      'Only an attorney or the firm owner can attest a trust reconciliation. '
      + 'Running the comparison is delegable; attesting to it is not -- the '
      + 'duty under Rule 1.15 is the lawyer\'s.');
  }
  // A TOKEN MEANS DUAL, WHETHER OR NOT THE SETTING IS ON. A solo firm that
  // hires a second attorney and prepares/countersigns properly is not pushed
  // back onto the single-signer route by a setting nobody turned off; and a
  // firm that is eligible for single-signer is not prevented from doing the
  // stronger thing. The record then says `dual`, which is the truth.
  if (c.hasToken) return { mode: SIGNER_MODE_DUAL };

  if (c.settingOn !== true) {
    return refuse('COUNTERSIGN_REQUIRED',
      'A trust reconciliation is attested by one bar-admitted person and '
      + 'countersigned by another. Prepare the attestation and have a second '
      + 'attorney sign it. (A firm with exactly one attorney can switch on '
      + 'single-signer attestation instead -- the record then says so.)');
  }
  const elig = singleSignerEligible(c.activeBarAdmitted);
  if (elig.refused) return elig;
  return { mode: SIGNER_MODE_SINGLE };
}

module.exports = {
  ATTEST_RESOURCE, SETTING_KEY,
  SIGNER_MODE_DUAL, SIGNER_MODE_SINGLE,
  VERDICTS, COMPARISON_FIELDS, CENT_FIELDS, DATE_FIELDS,
  normaliseComparison, singleSignerEligible, decideAttestation
};
