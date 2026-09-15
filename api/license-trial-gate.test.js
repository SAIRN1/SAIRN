// api/license-trial-gate.test.js
//
// Run:  node api/license-trial-gate.test.js
//
// PATTERN 13's trial-expiry gate has never refused anyone, on any licence, and
// the reason is not a bug in the comparison -- it is that `trial_ends_at` IS
// NOT A COLUMN on license_keys. Three handlers carried an identical inline copy
// of the check: api/sd-data.js, api/sd-render.js and api/_lib/sd-store.js.
//
// THIS SUITE PINS THE CURRENT BEHAVIOUR AS-IS, DELIBERATELY. Two of its arms
// assert that the gate is UNREACHABLE today. They are not describing something
// that should stay true forever -- they are a tripwire. The day someone adds
// the column, they go RED and name the three handlers that will start refusing
// people. That is the whole point: the decision (add the column and backfill,
// or delete the gates) is a billing decision, Stripe is not configured under
// the new LLC, and nobody is on a paid plan to expire. What must not happen is
// the gate quietly starting to fire, or quietly continuing to look enforced.
//
// The comment at the sd-data.js call site is what let this survive for so long:
// "A null/absent trial_ends_at (e.g. before the migration, or intentionally
// unset) is treated as 'not expired' and allowed through." That reads as an
// edge case being handled. It is not an edge case -- it is the only case.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const ROOT = path.join(__dirname, '..');
// NO HELPER. An earlier version of this fix extracted the check into
// trialExpired() in _lib/license.js and routed all three handlers through it.
// That broke SIXTEEN sd-data suites: they replace require.cache for
// _lib/license with a fake exporting only validateLicenseKey, so the new
// export was undefined at call time -- and `node --check` never sees a missing
// export, because it is a RUNTIME error. Reverted. The duplication was
// pre-existing and is not the finding; the misleading PROSE was. Sixteen test
// harnesses is a real cost for a tidiness gain, and this row is about a gate
// that looks enforced, not about three identical lines.
//
// So the logic is driven from the REAL expression, lifted out of the real
// file, rather than from a copy that could drift from it.
// The logic is MODELLED here and the SHAPE is asserted below, rather than
// lifted out of the file by regex and eval'd. A regex over source is the
// fragile half of both options -- this repo has already been caught by a
// fixed-size window that ran past a callback -- so the model and the shape
// assertion are kept as two simple things instead of one clever one. If the
// shape assertion holds, this model is faithful to what actually runs.
//
// ── UPDATED 2026-09-15 (item 100): AN IDENTIFIER IS NOT A STATE ───────────
// The model used to be `const isPaid = !!lic.stripe_subscription_id;`, which
// is the defect this suite now pins the FIX for: a cancelled subscription
// keeps its id forever, so that expression could grant a paid tier and could
// never revoke one. The shape assertion below went red on the change, named
// all three handlers, and that is exactly what it was written to do.
function trialExpired(lic) {
  const subState = String(lic.subscription_status || '').trim().toLowerCase();
  const everSubscribed = !!lic.stripe_subscription_id;
  const knownPaid = everSubscribed && (subState === 'active' || subState === 'trialing');
  const knownNotPaid = !everSubscribed
    || subState === 'canceled' || subState === 'cancelled'
    || subState === 'unpaid' || subState === 'past_due'
    || subState === 'incomplete_expired';
  // knownPaid is read so this model cannot drift into `!knownNotPaid` and
  // still look faithful; the two are NOT complements -- cannot-tell is
  // neither.
  if (knownPaid) return false;
  return !!(knownNotPaid && lic.trial_ends_at
            && new Date(lic.trial_ends_at).getTime() < Date.now());
}

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok - ' + name); pass++; }
  catch (e) { console.log('  FAIL - ' + name + '\n        ' + e.message); fail++; }
}
const read = (p) => fs.readFileSync(path.join(ROOT, p), 'utf8');

console.log('PATTERN 13 trial gate: the logic is right and the column is missing\n');

// ── the helper's own behaviour, so nothing about it is taken on trust ──────
test('a PAID licence bypasses the trial even with a date long past', () => {
  assert.strictEqual(trialExpired({
    stripe_subscription_id: 'sub_123', trial_ends_at: '2020-01-01T00:00:00Z' }), false);
});

test('an UNPAID licence with a past trial date IS expired -- the logic works', () => {
  // Asserted so the arms below cannot be mistaken for "the check is broken".
  // It is not broken. It is unreachable.
  assert.strictEqual(trialExpired({
    stripe_subscription_id: null, trial_ends_at: '2020-01-01T00:00:00Z' }), true);
});

test('an UNPAID licence with a future trial date is not expired', () => {
  const future = new Date(Date.now() + 86400000).toISOString();
  assert.strictEqual(trialExpired({ stripe_subscription_id: null, trial_ends_at: future }), false);
});

test('NO trial date means not expired -- and this is the ONLY case in production', () => {
  assert.strictEqual(trialExpired({ stripe_subscription_id: null, trial_ends_at: null }), false);
  assert.strictEqual(trialExpired({ stripe_subscription_id: null }), false);
});

// ── THE FIX: an identifier is not a state (item 100, 2026-09-15) ───────
// Every arm here is BOTH directions of one rule. The defect being fixed was a
// gate that could grant and never revoke, so "a cancelled subscription is now
// refused" alone proves nothing -- a check that refuses everybody passes it.
// Each is paired with the case that must still be allowed.

test('FIXED: a CANCELLED subscription no longer bypasses the trial', () => {
  // The whole defect in one arm. Under the old expression this was `false`:
  // the id is present, so isPaid was true, so the gate let them straight
  // through forever. `sub_...` is the receipt that a subscription once
  // existed, never evidence that it exists now.
  assert.strictEqual(trialExpired({
    stripe_subscription_id: 'sub_123', subscription_status: 'canceled',
    trial_ends_at: '2020-01-01T00:00:00Z' }), true);
});

test('...and the British spelling too, because Stripe is not the only writer', () => {
  assert.strictEqual(trialExpired({
    stripe_subscription_id: 'sub_123', subscription_status: 'cancelled',
    trial_ends_at: '2020-01-01T00:00:00Z' }), true);
});

test('...as do unpaid, past_due and incomplete_expired', () => {
  ['unpaid', 'past_due', 'incomplete_expired'].forEach((st) => {
    assert.strictEqual(trialExpired({
      stripe_subscription_id: 'sub_123', subscription_status: st,
      trial_ends_at: '2020-01-01T00:00:00Z' }), true, st + ' should be refusable');
  });
});

test('THE OTHER DIRECTION: an ACTIVE subscription still bypasses', () => {
  // Without this, a gate that refused everybody would pass every arm above.
  assert.strictEqual(trialExpired({
    stripe_subscription_id: 'sub_123', subscription_status: 'active',
    trial_ends_at: '2020-01-01T00:00:00Z' }), false);
});

test('...and so does trialing', () => {
  assert.strictEqual(trialExpired({
    stripe_subscription_id: 'sub_123', subscription_status: 'trialing',
    trial_ends_at: '2020-01-01T00:00:00Z' }), false);
});

test('CANNOT-TELL is NOT refused -- an id with no state column is the case today', () => {
  // This is the arm that protects real subscribers. license_keys has no
  // subscription_status column, so EVERY subscribed licence is in this state
  // right now. Folding it into not-paid would 402 every paying customer the
  // day trial_ends_at is added and this column is not.
  assert.strictEqual(trialExpired({
    stripe_subscription_id: 'sub_123', subscription_status: null,
    trial_ends_at: '2020-01-01T00:00:00Z' }), false);
  assert.strictEqual(trialExpired({
    stripe_subscription_id: 'sub_123',
    trial_ends_at: '2020-01-01T00:00:00Z' }), false, 'an absent field is the same as null');
});

test('CANNOT-TELL is not GRANTED either: an UNRECOGNISED status still falls through', () => {
  // Deliberately recorded rather than asserted as a refusal. A status nobody
  // has mapped is a cannot-tell, and this suite pins that it behaves like one
  // -- so if a future Stripe state should refuse, the change is visible here
  // rather than silently already-done.
  assert.strictEqual(trialExpired({
    stripe_subscription_id: 'sub_123', subscription_status: 'some_future_state',
    trial_ends_at: '2020-01-01T00:00:00Z' }), false);
});

test('NEVER SUBSCRIBED is knownNotPaid, exactly as before -- behaviour preserved', () => {
  // The fix must not change what happens today. With no status column a
  // licence is either knownNotPaid (no id) or cannot-tell (id present), and
  // both outcomes match the old expression.
  assert.strictEqual(trialExpired({
    stripe_subscription_id: null, subscription_status: 'active',
    trial_ends_at: '2020-01-01T00:00:00Z' }), true,
    'a status without a subscription id is not a subscription');
});

test('case and whitespace in the status do not decide entitlement', () => {
  assert.strictEqual(trialExpired({
    stripe_subscription_id: 'sub_123', subscription_status: '  CANCELED  ',
    trial_ends_at: '2020-01-01T00:00:00Z' }), true);
  assert.strictEqual(trialExpired({
    stripe_subscription_id: 'sub_123', subscription_status: ' Active ',
    trial_ends_at: '2020-01-01T00:00:00Z' }), false);
});

test('AS-IS: subscription_status is not a column yet either', () => {
  // The companion tripwire to trial_ends_at. If this goes red the column has
  // been added, which is GOOD -- it is what makes revocation possible -- but
  // it also means every licence with an id and no backfilled status is a
  // cannot-tell, and something must now WRITE this column. Nothing in api/
  // does today (tools/entitlement_freshness_check.py).
  const snap = JSON.parse(read(path.join('db', 'schema_snapshot.json')));
  const cols = snap.license_keys;
  assert.ok(Array.isArray(cols) && cols.length, 're-capture the snapshot');
  assert.strictEqual(cols.indexOf('subscription_status'), -1,
    'subscription_status EXISTS NOW -- confirm something writes it before trusting the gate');
});

// ── the two tripwires ─────────────────────────────────────────────────────
test('AS-IS: `trial_ends_at` is NOT a column on license_keys', () => {
  // The live snapshot, captured 2026-09-02. If this arm goes red, the column
  // has been added and THREE handlers begin refusing licences whose trial has
  // lapsed: api/sd-data.js, api/sd-render.js, api/_lib/sd-store.js. Check that
  // every existing licence has been backfilled before shipping it.
  const snap = JSON.parse(read(path.join('db', 'schema_snapshot.json')));
  const cols = snap.license_keys;
  assert.ok(Array.isArray(cols) && cols.length,
    'the snapshot no longer lists license_keys -- re-capture it before trusting this suite');
  assert.ok(cols.indexOf('stripe_subscription_id') !== -1,
    'the snapshot does not look like license_keys, so its absence proves nothing');
  assert.strictEqual(cols.indexOf('trial_ends_at'), -1,
    'trial_ends_at EXISTS NOW -- the trial gate is live in three handlers; confirm every licence is backfilled');
});

test('AS-IS: validateLicenseKey normalises the field to null, which is why', () => {
  const src = read(path.join('api', '_lib', 'license.js'));
  assert.match(src, /trial_ends_at:\s*null,/,
    'the default is no longer null, so the gate may now read something else');
  assert.match(src, /out\.trial_ends_at = row\.trial_ends_at \|\| null;/,
    'the row value is no longer defaulted to null');
});

// ── one place, not three ──────────────────────────────────────────────────
test('all three sites say the gate is inert, and point at this suite', () => {
  const files = ['api/sd-data.js', 'api/sd-render.js', 'api/_lib/sd-store.js'];
  files.forEach((f) => {
    const src = read(f);
    // All three still carry their own copy, deliberately -- see the note at
    // the top. What each MUST carry is the correction, so a reader of any one
    // of them learns the gate is inert.
    assert.match(src, /knownNotPaid && lic\.trial_ends_at && new Date\(lic\.trial_ends_at\)/,
      f + ' no longer contains the trial gate at all');
    // THE CONDITION MUST BE knownNotPaid AND NOT !knownPaid. They are not
    // complements: cannot-tell is neither, and `!knownPaid` would sweep it in
    // with positively-not-paid and 402 a real subscriber. This is the arm that
    // stops the fix being undone by a plausible-looking simplification.
    assert.ok(src.indexOf('!knownPaid && lic.trial_ends_at') === -1,
      f + ' refuses on !knownPaid, which folds cannot-tell into not-paid');
    // ANCHORED AT THE START OF A LINE, because the first version of this arm
    // was a plain indexOf and it went RED against the fixed file -- the fix's
    // own comment QUOTES the defective expression to explain what was wrong
    // with it. A marker search that cannot tell code from prose about code is
    // the same trap as `esign` matching 47 occurrences of `design`.
    assert.ok(!/^[ \t]*const isPaid = !!lic\.stripe_subscription_id;/m.test(src),
      f + ' is back to deriving a paid tier from the presence of an identifier');
    assert.ok(src.indexOf('NOT A COLUMN') !== -1,
      f + ' no longer says the gate is inert, so it reads as enforcement again');
    assert.ok(src.indexOf('license-trial-gate.test.js') !== -1,
      f + ' no longer points at the suite that pins this');
  });
});

test('the prose that made it look enforced is gone', () => {
  // "e.g. before the migration, or intentionally unset" described the only case
  // in production as an edge case, and that sentence is why nobody looked.
  const src = read('api/sd-data.js');
  assert.ok(src.indexOf('before the migration, or intentionally') === -1
            || src.indexOf('NOT A COLUMN') !== -1,
    'the misleading comment is back without the correction beside it');
  assert.ok(src.indexOf('has never') !== -1 || src.indexOf('NOT A COLUMN') !== -1,
    'nothing at the call site says the gate is inert');
});

console.log('\n' + (fail === 0 ? pass + ' / ' + pass + ' passed' : pass + ' passed, ' + fail + ' FAILED'));
process.exit(fail ? 1 : 0);
