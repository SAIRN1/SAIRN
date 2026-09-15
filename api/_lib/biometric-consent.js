// api/_lib/biometric-consent.js
// ---------------------------------------------------------------------------
// ONE MODULE OWNS "MAY THIS APP COLLECT A BIOMETRIC IDENTIFIER FROM THIS
// PERSON, AND WHEN MUST IT BE DESTROYED."
//
// Built once, cross-app, on the same reasoning as the WebAuthn rollout: every
// future biometric feature inherits the legal machinery instead of doing its
// own scramble. A per-app implementation of this is a per-app chance to get a
// statutory sequence wrong, and the sequence is the part with the case law
// behind it.
//
// ── WHO IS WHO, AND THIS IS THE LOAD-BEARING FACT ──────────────────────────
// SAIRN IS THE PROCESSOR. THE SAIRN CUSTOMER IS THE CONTROLLER.
//
// The customer -- the shop, the practice, the agency -- decides to collect, and
// the consent duty is THEIRS. SAIRN provides the mechanism, records what they
// did, and refuses to collect when they have not done it. That division is not
// a disclaimer: it changes what this module is allowed to do. It NEVER
// generates a consent, never back-dates one, never infers one from an earlier
// interaction, and never lets a caller assert "consent: true" as a flag. It
// only records the three artefacts the controller produced, in order, and
// answers a yes/no about what they add up to.
//
// A module that could manufacture consent is a module that would, the first
// time somebody hit a deadline.
//
// ── THE THREE-PART PRE-COLLECTION SEQUENCE, IN THAT ORDER ──────────────────
//   1. NOTICE               the person is TOLD a biometric identifier will be
//                           collected or stored
//   2. PURPOSE AND DURATION the specific purpose, and the LENGTH OF TERM for
//                           which it will be collected, stored and used
//   3. SIGNED RELEASE       a written release executed by the person
//
// ORDER IS A REQUIREMENT AND NOT A CONVENTION. A release signed before the
// person was told what they were signing about is not a release; a purpose
// disclosed after the signature is not a disclosure. `mayCollect` therefore
// checks the ORDER of the timestamps, not merely that three fields are
// non-null -- three present fields in the wrong order is the exact shape of a
// form somebody assembled afterwards.
//
// EQUAL TIMESTAMPS ARE ALLOWED. One screen can legitimately present notice and
// purpose together, and second-resolution clocks make two real steps look
// simultaneous. Strictly-increasing would refuse a compliant flow for a
// reason that is about clock resolution rather than about consent.
//
// ── RETENTION: THREE YEARS IS A CEILING, NOT A DEFAULT ─────────────────────
// Destruction is due at the EARLIER of:
//   * the purpose being satisfied, as the controller declared it, and
//   * three years after the person's last interaction with the controller.
//
// `retentionDeadline` returns the earlier. A controller that declares a
// shorter duration is held to the shorter one -- the ceiling does not extend
// anything, and a module that quietly relaxed a customer's own stated
// retention to the statutory maximum would be turning their promise into our
// default.
//
// THE CEILING IS ALSO ENFORCED IN THE SCHEMA, and that is deliberate
// belt-and-braces. sql/biometric_consent_schema.sql computes `destroy_by` as a
// GENERATED column and CHECKs that it is never more than three years past the
// last interaction, so a bug in this file, or a write that bypasses it
// entirely, still cannot store a template with an unbounded life. Application
// code is where a rule is applied; the schema is where it cannot be skipped.
//
// ── TWO TABLES, AND SPLITTING THEM IS THE POINT ────────────────────────────
// `biometric_consent`  the RECORD that the three steps happened. RETAINED --
//                      it is the evidence of compliance, and destroying it
//                      destroys the proof that collection was lawful.
// `biometric_template` the identifier ITSELF. DESTROYED on schedule.
//
// Conflating them produces one of two failures and there is no third option:
// keep everything and blow the retention limit, or delete everything and have
// no evidence you ever had consent. Nothing in this module lets a caller treat
// the two as one record.
//
// ── WHAT THIS MODULE DOES NOT DO ───────────────────────────────────────────
//   * It does not decide whether a feature NEEDS a biometric identifier. That
//     is a product question and usually the answer is no -- api/sd-webauthn.js
//     exists precisely because a passkey gets the same outcome with no
//     biometric data ever leaving the device, and its header says so.
//   * It does not perform destruction. It answers WHEN, and the schema and the
//     destruction job act on that answer.
//   * It does not know any jurisdiction's law. The three-step sequence and the
//     three-year ceiling are the CONTROLLER'S declared policy, written down in
//     docs/BIOMETRIC-RETENTION-POLICY.md; this module holds them to it. A
//     stricter jurisdiction is a stricter policy, not a code change.
'use strict';

const cal = require('./calendar-date.js');

// The ordered sequence. Exported so a caller renders the steps in the order
// the rule requires rather than in whatever order a form happens to lay out.
const PRE_COLLECTION_STEPS = ['notice', 'purpose_duration', 'release'];

// The timestamp field each step records.
const STEP_FIELD = {
  notice: 'notice_at',
  purpose_duration: 'purpose_duration_at',
  release: 'release_at'
};

// Three years, as days, in the module that owns calendar arithmetic. Not
// `3 * 365`: that is wrong by one day across a leap year, and a retention
// deadline that is a day late is the one day that matters.
const RETENTION_MAX_YEARS = 3;

// Bare category words. Naming what the data IS is not naming what it is FOR.
// Kept short deliberately: a long list would start refusing real purposes that
// happen to contain one of these words, and this check is a floor rather than
// a judgement.
const NON_PURPOSES = new Set([
  'biometrics', 'biometric', 'biometric data', 'biometric identifier',
  'fingerprint', 'fingerprints', 'face scan', 'facial scan', 'face data',
  'facial recognition', 'retina scan', 'iris scan', 'voiceprint', 'handprint',
  'identification', 'verification', 'security', 'compliance'
]);

const REASONS = {
  NO_RECORD: 'No consent record exists for this person. The three-part '
    + 'sequence has not been started.',
  OUT_OF_ORDER: 'The consent steps are recorded out of order. Notice must '
    + 'come before the purpose-and-duration disclosure, and both before the '
    + 'signed release -- a release signed before the person was told what it '
    + 'was about is not a release.',
  MISSING_STEP: 'The sequence is incomplete.',
  NO_PURPOSE: 'The purpose field does not state a purpose. Naming the '
    + 'CATEGORY -- "biometrics", "fingerprint", "face scan" -- says what the '
    + 'data IS, not what it is used FOR, and a person cannot consent to a '
    + 'noun. NOTE THE LIMIT: this check is a floor, not a judgement. It '
    + 'refuses an empty field and the bare category words that have actually '
    + 'been typed here; it CANNOT tell a specific purpose from a vague one, '
    + 'and no code can. That reading belongs to the controller, and the '
    + 'policy document is where the standard lives.',
  NO_DURATION: 'No retention duration was disclosed to the person before they '
    + 'signed.',
  NO_SIGNATURE: 'The release carries no signature. A release row with no '
    + 'signature is a row, not a release.',
  WITHDRAWN: 'Consent was withdrawn. Collection must stop and any stored '
    + 'template is due for destruction.',
  PAST_RETENTION: 'The retention deadline has passed. Nothing further may be '
    + 'collected against this consent, and the stored template is overdue for '
    + 'destruction.'
};

function isTs(v) {
  // An ISO instant, not a calendar date: these are moments, and two steps on
  // one screen are minutes apart, not days.
  return typeof v === 'string'
    && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$/.test(v)
    && !isNaN(Date.parse(v))
    // Reject a rolled-over impossible date the way calendar-date does: Date
    // silently repairs 2026-02-31 into 2026-03-03, and a consent timestamped on
    // a day that does not exist is a record somebody typed rather than one a
    // system wrote.
    && cal.isCalendarDate(v.slice(0, 10));
}

/**
 * The next step this person still owes, or null when the sequence is complete.
 * Returns the FIRST incomplete step in order -- a caller that asks for the
 * next step and gets `release` knows the first two are done, which is the only
 * safe way to render a sequential form.
 */
function nextRequiredStep(record) {
  const r = record || {};
  for (const step of PRE_COLLECTION_STEPS) {
    if (!isTs(r[STEP_FIELD[step]])) return step;
  }
  return null;
}

/**
 * May a biometric identifier be collected from this person right now?
 *
 * Returns { ok, reason, code }. NEVER a bare boolean: a refusal that cannot
 * say why becomes a caller that retries, and on this path a caller that
 * retries is a caller that collects.
 */
function mayCollect(record, opts) {
  const now = (opts && opts.now) || new Date().toISOString();
  const r = record || null;
  if (!r) return { ok: false, code: 'NO_RECORD', reason: REASONS.NO_RECORD };

  const missing = nextRequiredStep(r);
  if (missing) {
    return { ok: false, code: 'MISSING_STEP',
             reason: REASONS.MISSING_STEP + ' Next required: ' + missing + '.' };
  }
  // ORDER, not merely presence. Equal is allowed -- see the header.
  const seq = PRE_COLLECTION_STEPS.map((s) => Date.parse(r[STEP_FIELD[s]]));
  for (let i = 1; i < seq.length; i++) {
    if (seq[i] < seq[i - 1]) {
      return { ok: false, code: 'OUT_OF_ORDER', reason: REASONS.OUT_OF_ORDER };
    }
  }
  // A FLOOR, AND THE HEADER SAYS SO RATHER THAN IMPLYING MORE. The length
  // test alone accepted 'biometrics' -- ten characters, and the exact
  // non-purpose the refusal text names. A category word is what the data IS;
  // a purpose is what it is used FOR, and a person cannot consent to a noun.
  // The list is short on purpose: it holds the words that have actually been
  // typed into this field, not a vocabulary somebody imagined.
  const purpose = String(r.purpose || '').trim().toLowerCase().replace(/[.\s]+$/, '');
  if (!purpose || purpose.length < 8 || NON_PURPOSES.has(purpose)) {
    return { ok: false, code: 'NO_PURPOSE', reason: REASONS.NO_PURPOSE };
  }
  if (!Number.isInteger(r.disclosed_retention_days) || r.disclosed_retention_days <= 0) {
    return { ok: false, code: 'NO_DURATION', reason: REASONS.NO_DURATION };
  }
  if (!r.release_signature || !String(r.release_signature).trim()) {
    return { ok: false, code: 'NO_SIGNATURE', reason: REASONS.NO_SIGNATURE };
  }
  if (r.withdrawn_at) {
    return { ok: false, code: 'WITHDRAWN', reason: REASONS.WITHDRAWN };
  }
  const due = retentionDeadline(r);
  if (due && Date.parse(now) >= Date.parse(due)) {
    return { ok: false, code: 'PAST_RETENTION', reason: REASONS.PAST_RETENTION };
  }
  return { ok: true, code: 'OK', reason: '' };
}

/**
 * When the stored template must be destroyed: the EARLIER of the controller's
 * own disclosed duration and the three-year ceiling, both measured from the
 * last interaction.
 *
 * Returns null when there is nothing to measure from -- and null means
 * UNKNOWN, never "no deadline". Callers must treat a null as a refusal to
 * store, which is what the schema does by making the column NOT NULL.
 */
function retentionDeadline(record) {
  const r = record || {};
  const last = isTs(r.last_interaction_at) ? r.last_interaction_at
    : (isTs(r.release_at) ? r.release_at : null);
  if (!last) return null;
  const day = r.last_interaction_at && isTs(r.last_interaction_at)
    ? r.last_interaction_at.slice(0, 10) : last.slice(0, 10);
  const ceilingDay = cal.addDays(day, yearsToDays(day, RETENTION_MAX_YEARS));
  const ceiling = ceilingDay + last.slice(10);
  if (!Number.isInteger(r.disclosed_retention_days) || r.disclosed_retention_days <= 0) {
    return ceiling;
  }
  const declaredDay = cal.addDays(day, r.disclosed_retention_days);
  const declared = declaredDay + last.slice(10);
  return Date.parse(declared) < Date.parse(ceiling) ? declared : ceiling;
}

/**
 * Days from `fromDay` to the same calendar day N years later, so the ceiling
 * lands on the anniversary rather than 1095 days later. Across one leap year
 * those differ by a day, and this deadline is the kind that gets read off a
 * page in a deposition.
 */
function yearsToDays(fromDay, years) {
  const y = Number(fromDay.slice(0, 4)) + years;
  const target = String(y) + fromDay.slice(4);
  // 29 February plus three years is not a date. Land on 28 February rather
  // than rolling into March, which is the conservative direction: destruction
  // a day early is compliant and a day late is not.
  const safe = cal.isCalendarDate(target) ? target : (String(y) + '-02-28');
  return cal.daysBetween(fromDay, safe);
}

function isPastRetention(record, opts) {
  const now = (opts && opts.now) || new Date().toISOString();
  const due = retentionDeadline(record);
  if (!due) return false;   // UNKNOWN is not overdue; it is unstorable.
  return Date.parse(now) >= Date.parse(due);
}

/**
 * Templates due for destruction. The destruction job's whole input.
 * A record with no computable deadline is returned in `unknown` rather than
 * silently skipped -- "could not tell" is the third state and a retention job
 * that drops it is a job that keeps data forever without saying so.
 */
function dueForDestruction(records, opts) {
  const now = (opts && opts.now) || new Date().toISOString();
  const due = [];
  const unknown = [];
  for (const r of records || []) {
    if (r && r.destroyed_at) continue;
    const d = retentionDeadline(r);
    if (!d) { unknown.push(r); continue; }
    if (Date.parse(now) >= Date.parse(d) || (r && r.withdrawn_at)) due.push(r);
  }
  return { due, unknown };
}

module.exports = {
  PRE_COLLECTION_STEPS,
  STEP_FIELD,
  RETENTION_MAX_YEARS,
  REASONS,
  nextRequiredStep,
  mayCollect,
  retentionDeadline,
  isPastRetention,
  dueForDestruction,
  // Exported for the suite and for any caller validating input before storing.
  isTimestamp: isTs
};
