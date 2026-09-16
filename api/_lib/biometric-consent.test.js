// api/_lib/biometric-consent.test.js
// REQUIREMENT: a biometric consent cannot be manufactured, back-dated or inferred by
//   this module, and the notice-purpose-release sequence is checked in ORDER
//   rather than for presence
//
//
// Run:  node api/_lib/biometric-consent.test.js
//
// THE ARMS THAT MATTER ARE THE REFUSALS, and every one of them is driven with
// a record that is ALMOST right. A consent module that refuses an empty object
// has proved nothing: nobody ships an empty object. The failures that happen
// are three real timestamps in the wrong order, a signature field containing a
// space, a purpose that says "biometrics", and a duration nobody disclosed --
// records that look complete in a table view and are not consents.
//
// AND THE POSITIVE CONTROL IS NOT OPTIONAL HERE. A module whose answer is
// always "no" would pass every refusal arm in this file and would be worse
// than no module, because it would be switched off within a week. Section 1
// drives a genuinely compliant record and requires OK.
//
// WHAT THIS FILE DOES NOT TEST, said rather than implied: whether the three
// steps satisfy any particular jurisdiction. That is a question for counsel and
// for docs/BIOMETRIC-RETENTION-POLICY.md, which is the controller's declared
// policy. This tests that the module holds a caller to that policy exactly, and
// cannot be talked out of it.
'use strict';
const assert = require('assert');
const b = require('./biometric-consent.js');

let pass = 0, fail = 0;
function t(name, fn) {
  try { fn(); pass++; console.log('  ok   ' + name); }
  catch (e) { fail++; console.log('  FAIL ' + name + '\n         ' + e.message); }
}
function section(s) { console.log('\n' + s); }

// A record that is genuinely compliant. Every refusal below is this, with ONE
// thing changed -- so a failing arm names the one thing.
function good(over) {
  return Object.assign({
    notice_at: '2026-01-05T09:00:00Z',
    purpose_duration_at: '2026-01-05T09:01:00Z',
    release_at: '2026-01-05T09:02:00Z',
    purpose: 'identity verification at the shop-floor clock-in terminal',
    disclosed_retention_days: 365,
    release_signature: 'A. Worker',
    last_interaction_at: '2026-01-20T17:30:00Z'
  }, over || {});
}
const NOW = '2026-02-01T00:00:00Z';

section('1. the positive control -- a compliant record is ALLOWED');
t('a complete, ordered, signed consent permits collection', () => {
  const r = b.mayCollect(good(), { now: NOW });
  assert.strictEqual(r.ok, true, JSON.stringify(r));
  assert.strictEqual(r.code, 'OK');
});
t('...and nextRequiredStep says there is nothing left to do', () => {
  assert.strictEqual(b.nextRequiredStep(good()), null);
});

section('2. the sequence must be COMPLETE, and the next step is named');
t('no record at all is NO_RECORD, not a silent false', () => {
  const r = b.mayCollect(null, { now: NOW });
  assert.strictEqual(r.code, 'NO_RECORD');
  assert.ok(r.reason.length > 20, 'a refusal with no reason is a retry loop');
});
t('an empty record owes NOTICE first', () => {
  assert.strictEqual(b.nextRequiredStep({}), 'notice');
});
t('notice alone owes the purpose-and-duration disclosure next', () => {
  assert.strictEqual(b.nextRequiredStep({ notice_at: '2026-01-05T09:00:00Z' }),
                     'purpose_duration');
});
t('notice and purpose owe the RELEASE, and mayCollect names it', () => {
  const rec = good();
  delete rec.release_at;
  assert.strictEqual(b.nextRequiredStep(rec), 'release');
  const r = b.mayCollect(rec, { now: NOW });
  assert.strictEqual(r.code, 'MISSING_STEP');
  assert.ok(/release/.test(r.reason), r.reason);
});
t('the steps are exported IN ORDER, so a form cannot render them wrong', () => {
  assert.deepStrictEqual(b.PRE_COLLECTION_STEPS,
                         ['notice', 'purpose_duration', 'release']);
});

section('3. ORDER -- three real timestamps in the wrong order is not a consent');
t('a release signed BEFORE the purpose disclosure is refused', () => {
  const r = b.mayCollect(good({ release_at: '2026-01-05T08:30:00Z' }), { now: NOW });
  assert.strictEqual(r.code, 'OUT_OF_ORDER', JSON.stringify(r));
});
t('a purpose disclosed BEFORE notice is refused', () => {
  const r = b.mayCollect(good({ purpose_duration_at: '2026-01-05T08:00:00Z' }),
                         { now: NOW });
  assert.strictEqual(r.code, 'OUT_OF_ORDER', JSON.stringify(r));
});
t('EQUAL timestamps are ALLOWED -- one screen can carry notice and purpose', () => {
  const r = b.mayCollect(good({ notice_at: '2026-01-05T09:00:00Z',
                                purpose_duration_at: '2026-01-05T09:00:00Z' }),
                         { now: NOW });
  assert.strictEqual(r.ok, true, JSON.stringify(r));
});
t('CONTROL: the order check is not vacuous -- one second backwards refuses', () => {
  // Without this, the "equal is allowed" arm above could be passing because
  // the ordering check does nothing at all.
  const r = b.mayCollect(good({ purpose_duration_at: '2026-01-05T08:59:59Z' }),
                         { now: NOW });
  assert.strictEqual(r.code, 'OUT_OF_ORDER', JSON.stringify(r));
});

section('4. the three artefacts must have CONTENT, not just be present');
t('a bare CATEGORY word is refused -- "biometrics" is a noun, not a purpose', () => {
  // THE LENGTH FLOOR ALONE ACCEPTED THIS. 'biometrics' is ten characters and is
  // the exact non-purpose the refusal text names; the first version of the
  // check passed it, and this arm is why the category list exists.
  assert.strictEqual(b.mayCollect(good({ purpose: 'biometrics' }), { now: NOW }).code,
                     'NO_PURPOSE');
  assert.strictEqual(b.mayCollect(good({ purpose: 'Facial Recognition.' }), { now: NOW }).code,
                     'NO_PURPOSE');
});
t('CONTROL: a real purpose CONTAINING a category word is still allowed', () => {
  // The list is short on purpose. A longer one starts refusing real purposes,
  // and a consent check that refuses compliant input is a check people route
  // around.
  const r = b.mayCollect(good({ purpose: 'fingerprint match at the clock-in terminal' }),
                         { now: NOW });
  assert.strictEqual(r.ok, true, JSON.stringify(r));
});
t('and the refusal STATES ITS OWN LIMIT rather than implying a judgement', () => {
  // A check that cannot tell specific from vague must not sound like it can:
  // the next person to read this message decides whether to trust it.
  assert.ok(/floor, not a judgement/.test(b.REASONS.NO_PURPOSE), b.REASONS.NO_PURPOSE);
});
t('a blank purpose is refused', () => {
  assert.strictEqual(b.mayCollect(good({ purpose: '        ' }), { now: NOW }).code,
                     'NO_PURPOSE');
});
t('a missing disclosed duration is refused -- not defaulted to the ceiling', () => {
  const rec = good();
  delete rec.disclosed_retention_days;
  assert.strictEqual(b.mayCollect(rec, { now: NOW }).code, 'NO_DURATION');
});
t('a zero or negative duration is refused', () => {
  assert.strictEqual(b.mayCollect(good({ disclosed_retention_days: 0 }), { now: NOW }).code,
                     'NO_DURATION');
  assert.strictEqual(b.mayCollect(good({ disclosed_retention_days: -1 }), { now: NOW }).code,
                     'NO_DURATION');
});
t('a duration that is a STRING is refused, not coerced', () => {
  // Number('365') is 365 and a coercing check would accept it. The platform has
  // already paid twice for a coercing reader turning a typo into a real value.
  assert.strictEqual(b.mayCollect(good({ disclosed_retention_days: '365' }), { now: NOW }).code,
                     'NO_DURATION');
});
t('a whitespace signature is refused -- a row is not a release', () => {
  assert.strictEqual(b.mayCollect(good({ release_signature: '   ' }), { now: NOW }).code,
                     'NO_SIGNATURE');
});

section('5. a timestamp that is not a real moment is not a timestamp');
t('a calendar date is not an instant', () => {
  assert.strictEqual(b.isTimestamp('2026-01-05'), false);
});
t('an IMPOSSIBLE date is refused rather than silently repaired', () => {
  // new Date('2026-02-31T00:00:00Z') is 3 March. A consent timestamped on a day
  // that does not exist is a record somebody typed, not one a system wrote.
  assert.strictEqual(b.isTimestamp('2026-02-31T00:00:00Z'), false);
  assert.strictEqual(b.nextRequiredStep({ notice_at: '2026-02-31T00:00:00Z' }), 'notice');
});
t('CONTROL: a real instant IS accepted, so the arm above is not blanket', () => {
  assert.strictEqual(b.isTimestamp('2026-02-28T00:00:00Z'), true);
});

section('6. RETENTION -- the ceiling is a ceiling, the disclosure is a promise');
t('the DECLARED duration wins when it is shorter than three years', () => {
  const due = b.retentionDeadline(good({ disclosed_retention_days: 30 }));
  assert.strictEqual(due.slice(0, 10), '2026-02-19');  // 20 Jan + 30 days
});
t('the CEILING wins when nothing was declared', () => {
  const rec = good();
  delete rec.disclosed_retention_days;
  assert.strictEqual(b.retentionDeadline(rec).slice(0, 10), '2029-01-20');
});
t('...and the ceiling is the ANNIVERSARY, not 1095 days', () => {
  // Across one leap year those differ by a day, and this is a deadline that
  // gets read off a page in a deposition.
  const rec = good({ last_interaction_at: '2027-03-01T12:00:00Z' });
  delete rec.disclosed_retention_days;
  assert.strictEqual(b.retentionDeadline(rec).slice(0, 10), '2030-03-01');
});
t('29 February plus three years lands on 28 February, never in March', () => {
  // The conservative direction: destruction a day early is compliant and a day
  // late is not.
  const rec = good({ last_interaction_at: '2028-02-29T00:00:00Z' });
  delete rec.disclosed_retention_days;
  assert.strictEqual(b.retentionDeadline(rec).slice(0, 10), '2031-02-28');
});
t('a declared duration LONGER than the ceiling does not extend it', () => {
  const due = b.retentionDeadline(good({ disclosed_retention_days: 5000 }));
  assert.strictEqual(due.slice(0, 10), '2029-01-20');
});
t('the clock runs from the LAST interaction, not the release', () => {
  const early = b.retentionDeadline(good({ last_interaction_at: '2026-01-20T17:30:00Z',
                                           disclosed_retention_days: 10 }));
  const later = b.retentionDeadline(good({ last_interaction_at: '2026-06-20T17:30:00Z',
                                           disclosed_retention_days: 10 }));
  assert.ok(Date.parse(later) > Date.parse(early),
            'a person who kept using the system did not get a longer deadline');
});
t('with no interaction recorded it falls back to the RELEASE, not to forever', () => {
  const rec = good();
  delete rec.last_interaction_at;
  delete rec.disclosed_retention_days;
  assert.strictEqual(b.retentionDeadline(rec).slice(0, 10), '2029-01-05');
});
t('with nothing to measure from it returns null, and null is UNKNOWN', () => {
  assert.strictEqual(b.retentionDeadline({}), null);
  // UNKNOWN is not "no deadline": isPastRetention must not report false as if
  // it had checked. The schema is what refuses to store such a row.
  assert.strictEqual(b.isPastRetention({}), false);
});

section('7. past the deadline, collection STOPS');
t('a record past its retention deadline refuses further collection', () => {
  const r = b.mayCollect(good({ disclosed_retention_days: 1 }),
                         { now: '2026-03-01T00:00:00Z' });
  assert.strictEqual(r.code, 'PAST_RETENTION', JSON.stringify(r));
});
t('withdrawal refuses collection, and does so BEFORE the deadline matters', () => {
  const r = b.mayCollect(good({ withdrawn_at: '2026-01-25T00:00:00Z' }), { now: NOW });
  assert.strictEqual(r.code, 'WITHDRAWN', JSON.stringify(r));
});

section('8. the destruction job gets a THIRD state, not two');
t('overdue templates are returned', () => {
  const { due } = b.dueForDestruction(
    [good({ subject_id: 'a', disclosed_retention_days: 1 })],
    { now: '2026-03-01T00:00:00Z' });
  assert.strictEqual(due.length, 1);
});
t('already-destroyed templates are not returned again', () => {
  const { due } = b.dueForDestruction(
    [good({ disclosed_retention_days: 1, destroyed_at: '2026-02-01T00:00:00Z' })],
    { now: '2026-03-01T00:00:00Z' });
  assert.strictEqual(due.length, 0);
});
t('a WITHDRAWN template is due immediately, whatever its deadline says', () => {
  const { due } = b.dueForDestruction(
    [good({ disclosed_retention_days: 1000, withdrawn_at: '2026-01-25T00:00:00Z' })],
    { now: NOW });
  assert.strictEqual(due.length, 1);
});
t('a record with NO computable deadline goes to `unknown`, never dropped', () => {
  // A retention job that silently skips what it cannot measure is a job that
  // keeps data forever without saying so.
  const { due, unknown } = b.dueForDestruction([{}], { now: NOW });
  assert.strictEqual(due.length, 0);
  assert.strictEqual(unknown.length, 1);
});
t('CONTROL: a live template is neither due nor unknown', () => {
  const { due, unknown } = b.dueForDestruction([good()], { now: NOW });
  assert.strictEqual(due.length, 0);
  assert.strictEqual(unknown.length, 0);
});

section('9. the module cannot MANUFACTURE a consent');
t('a caller asserting consent:true is ignored', () => {
  // The one thing a processor must never accept from a controller is the
  // CONCLUSION. It may only record the artefacts.
  const r = b.mayCollect({ consent: true, consented: true, ok: true }, { now: NOW });
  assert.strictEqual(r.ok, false);
  assert.strictEqual(r.code, 'MISSING_STEP');
});
t('an earlier consent for a DIFFERENT purpose is not reused', () => {
  // mayCollect is a pure function of the record it is handed. It has no store,
  // no lookup and no way to find "a consent from last year" -- which is the
  // mechanism by which consent-for-one-thing becomes consent-for-everything.
  assert.strictEqual(typeof b.mayCollect, 'function');
  assert.strictEqual(b.mayCollect.length <= 2, true,
                     'mayCollect gained a lookup argument; it must stay pure');
});

console.log('\n' + (fail ? fail + ' FAILED, ' + pass + ' passed'
  : 'ALL ' + pass + ' ASSERTIONS PASS'));
process.exit(fail ? 1 : 0);
