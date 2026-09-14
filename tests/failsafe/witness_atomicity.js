// tests/failsafe/witness_atomicity.js
//
// Run:  node tests/failsafe/witness_atomicity.js
//
// ITEM 83a -- ATOMICITY, applied to the witnessing lock (item 19).
//
// The lock is PROVEN by control-pair testing: api/sv-witness.test.js drives
// every refusal and proves the lock still opens. Neither that file nor any
// other asks what happens when the transition is INTERRUPTED PART-WAY.
//
// ── THE TRANSITION IS NOT ONE STEP ─────────────────────────────────────────
// requireWitness() does, in order: read the token row, read the policy row,
// SPEND the token with a compare-and-set, and only then return null so the
// caller writes the controlled-substance record. Four network round trips
// before an irreversible write. Kill the process or drop the socket between
// any two of them and the system settles somewhere.
//
// ── THE ONE INVARIANT THAT MATTERS ─────────────────────────────────────────
//
//     requireWitness() returns null  ==>  the token is SPENT.
//
// Every other resting place is safe. Nothing happened: safe. The token burned
// and no record written: safe, and the file says so in its own words -- "the
// token is burned and the record must be confirmed again, which is the
// direction to fail in". Both spent and written: the success path.
//
// The unsafe one is the inverse: the caller is told to PROCEED while the token
// is still unspent. That is a reusable signature on a DEA-relevant append-only
// record, which is the exact defect the lock exists to prevent -- and no arm
// anywhere asserted it could not happen.
//
// ── THE SHAPE THAT ACTUALLY LOSES DATA ─────────────────────────────────────
// Section C is the one worth reading. A dropped connection AFTER the server
// applied the spend is not the same as a dropped connection before it: the
// mutation landed and the caller will never learn that it did. A retry then
// meets a spent token. The lock must treat that as a refusal rather than as a
// transient it can retry through.
//
// ── HONEST SCOPE ───────────────────────────────────────────────────────────
// Driven against the kit's in-memory table, not PostgREST. It models the
// `spent_at=is.null` compare-and-set because that is the semantic the lock
// rests on; it does not prove PostgREST implements it. Same limitation
// sv-witness.test.js names, restated here rather than inherited quietly.

'use strict';
const assert = require('assert');
const path = require('path');
const W = require(path.join(__dirname, '..', '..', 'api', 'sv-witness.js'));
const K = require('./failsafekit.js');

let pass = 0, fail = 0;
const queue = [];
function t(name, fn) { queue.push([name, fn]); }
function section(s) { queue.push([s, null]); }

const PAYLOAD = { id: 'c1', drug: 'ketamine', qty: 2, vet: 'dr-a' };
const FUTURE = new Date(Date.now() + 60000).toISOString();

function tokenRow(extra) {
  return Object.assign({
    id: 'row-1',
    license_hash: 'L1',
    token_hash: require('crypto').createHash('sha256').update('tok-good').digest('hex'),
    content_hash: W.contentHash('sv_controlled', PAYLOAD),
    witness_employee_id: 'e1',
    countersign_employee_id: null,
    spent_at: null,
    expires_at: FUTURE,
  }, extra || {});
}

function ctx(token) {
  return {
    resource: 'sv_controlled', payload: PAYLOAD, licHash: 'L1',
    rest: (p) => 'https://db/rest/v1/' + p,
    headers: {}, token: token === undefined ? 'tok-good' : token,
  };
}

// The lock hashes the token before querying; the kit stores rows keyed on that
// same hash, so the fixture has to use the module's own hashing rather than a
// second copy of it. Derived here from the module's observable behaviour.
function hashedRow() {
  const probe = K.restWorld({ tokens: [] });
  return probe;
}

section('A. the invariant, at EVERY interruption point in the transition');

// The transition is a handful of fetch calls. Rather than guess how many,
// measure it once and then interrupt at each one -- a count written down here
// would be a claim that goes stale the first time a round trip is added.
let TRANSITION_CALLS = 0;
t('the uninterrupted transition PROCEEDS, or every arm below is vacuous', async () => {
  const world = K.restWorld({ tokens: [tokenRow()] });
  const r = await K.attempt(() => W.requireWitness(ctx()));
  assert.strictEqual(r.outcome, 'proceed', JSON.stringify(r.refusal));
  assert.ok(world.tokens[0].spent_at, 'proceeded without spending the token');
  TRANSITION_CALLS = world.calls.length;
  assert.ok(TRANSITION_CALLS >= 2, 'measured ' + TRANSITION_CALLS + ' calls');
});

t('interrupting at every point never says PROCEED on an unspent token', async () => {
  const seen = [];
  for (let n = 1; n <= TRANSITION_CALLS + 1; n += 1) {
    const world = K.restWorld({ tokens: [tokenRow()], interruptAfter: n });
    const r = await K.attempt(() => W.requireWitness(ctx()));
    const spent = !!world.tokens[0].spent_at;
    seen.push(n + ':' + r.outcome + (spent ? '/spent' : '/unspent'));
    // THE INVARIANT. Proceed means the caller writes an irreversible record.
    assert.ok(!(r.outcome === 'proceed' && !spent),
      'interrupt after call ' + n + ' told the caller to PROCEED on an UNSPENT token '
      + '-- that signature is reusable and the record is append-only');
  }
  console.log('        observed: ' + seen.join('  '));
});

section('B. a half-transition is a REFUSAL or a THROW, never a quiet success');

t('an interruption is never reported as a completed witnessing', async () => {
  for (let n = 1; n <= TRANSITION_CALLS; n += 1) {
    const world = K.restWorld({ tokens: [tokenRow()], interruptAfter: n });
    const r = await K.attempt(() => W.requireWitness(ctx()));
    assert.ok(r.outcome !== 'proceed' || world.tokens[0].spent_at,
      'call ' + n + ' produced a silent success');
  }
});

t('and an interrupted attempt never leaves the token spent AND reports proceed '
  + 'without the caller knowing', async () => {
  // Stated as its own arm because the two halves fail differently: the one
  // above is about the invariant, this is about the caller's knowledge. A
  // throw reaches the caller; a null does not carry "by the way, I burned it".
  const world = K.restWorld({ tokens: [tokenRow()], interruptAfter: 1 });
  const r = await K.attempt(() => W.requireWitness(ctx()));
  assert.strictEqual(r.outcome, 'interrupted');
  assert.strictEqual(!!world.tokens[0].spent_at, false,
    'the token was burned by an attempt that never reached the spend');
});

section('C. the shape that loses data: the spend LANDED and the answer did not');

t('a spend applied server-side then interrupted does NOT proceed', async () => {
  // The dangerous asymmetry. The row is now spent and the caller is told
  // nothing; if the lock swallowed this it would either write unwitnessed or
  // retry onto a burned signature.
  const world = K.restWorld({
    tokens: [tokenRow()],
    applyThenInterruptAfter: 3,
  });
  const r = await K.attempt(() => W.requireWitness(ctx()));
  assert.notStrictEqual(r.outcome, 'proceed',
    'the caller was cleared to write on an answer that never arrived');
  assert.ok(world.applied.some((a) => a.op === 'spend'),
    'the fixture did not actually apply the spend -- this arm proves nothing');
  assert.ok(world.tokens[0].spent_at, 'the spend did not land in the fixture');
});

t('and the burned token is REFUSED on the retry, not silently reused', async () => {
  const spent = tokenRow({ spent_at: new Date().toISOString() });
  const world = K.restWorld({ tokens: [spent] });
  const r = await K.attempt(() => W.requireWitness(ctx()));
  assert.strictEqual(r.outcome, 'refused');
  assert.strictEqual(r.refusal.body.error.code, 'WITNESS_ALREADY_SPENT');
  assert.strictEqual(world.applied.length, 0, 'a spent token was written to again');
});

section('C2. THE RACE -- one signature, two requests, exactly one write');

// ADDED AFTER A MUTATION SURVIVED. Deleting `&spent_at=is.null` from the
// spend, and separately treating the zero-row CAS loser as a win, both left
// every arm green -- so the file proved the lock refuses a token that is
// ALREADY spent while proving nothing about two requests spending the SAME
// one. The lock's own comment calls that gap 'exactly wide enough for a
// double submit to write two controlled-substance rows on one signature',
// which is the defect it exists to prevent and was the one thing untested.
t('two concurrent writes on one confirmation: exactly ONE proceeds', async () => {
  const world = K.restWorld({ tokens: [tokenRow()] });
  const [a, b] = await Promise.all([
    K.attempt(() => W.requireWitness(ctx())),
    K.attempt(() => W.requireWitness(ctx())),
  ]);
  const proceeded = [a, b].filter((r) => r.outcome === 'proceed');
  assert.strictEqual(proceeded.length, 1,
    'both requests were cleared to write -- one signature, two irreversible rows');
  const spends = world.applied.filter((x) => x.op === 'spend' && x.ids.length);
  assert.strictEqual(spends.length, 1,
    'the confirmation was spent ' + spends.length + ' times');
});

t('...and the loser is told the confirmation was used, not given a 500', async () => {
  const world = K.restWorld({ tokens: [tokenRow()] });
  const [a, b] = await Promise.all([
    K.attempt(() => W.requireWitness(ctx())),
    K.attempt(() => W.requireWitness(ctx())),
  ]);
  const loser = [a, b].find((r) => r.outcome !== 'proceed');
  assert.ok(loser, 'nobody lost the race -- see the arm above');
  assert.strictEqual(loser.outcome, 'refused');
  assert.strictEqual(loser.refusal.body.error.code, 'WITNESS_ALREADY_SPENT');
  assert.strictEqual(loser.refusal.status, 409);
  assert.ok(world.tokens[0].spent_at, 'the winner did not spend it');
});

t('the spend really is a compare-and-set, asserted on the URL the lock sends',
  async () => {
  // The arms above can only observe the OUTCOME, and the kit is the thing
  // implementing the CAS -- so a lock that dropped `spent_at=is.null` would
  // still pass them against a fixture that happens to be safe. This reads the
  // request the lock actually issued. Against PostgREST that clause is the
  // whole guarantee; here it is at least PROVEN TO BE SENT.
  const world = K.restWorld({ tokens: [tokenRow()] });
  await K.attempt(() => W.requireWitness(ctx()));
  const patch = world.calls.filter((c) => c.method === 'PATCH');
  assert.strictEqual(patch.length, 1, 'expected exactly one spend');
  assert.ok(patch[0].url.indexOf('spent_at=is.null') !== -1,
    'the spend is not a compare-and-set: ' + patch[0].url);
});

section('D. CONTROLS -- the arms above are not "it refuses everything"');

t('an uninterrupted, unspent, in-date, content-matched token PROCEEDS', async () => {
  const world = K.restWorld({ tokens: [tokenRow()] });
  const r = await K.attempt(() => W.requireWitness(ctx()));
  assert.strictEqual(r.outcome, 'proceed');
  assert.ok(world.tokens[0].spent_at);
});

t('a policy that cannot be read REFUSES rather than assuming the weaker rule', async () => {
  const world = K.restWorld({ tokens: [tokenRow()], policy: null });
  const r = await K.attempt(() => W.requireWitness(ctx()));
  assert.strictEqual(r.outcome, 'refused');
  assert.strictEqual(r.refusal.body.error.code, 'WITNESS_CHECK_FAILED');
  assert.strictEqual(world.tokens[0].spent_at, null,
    'a token was burned by a check that never got as far as the spend');
});

t('an unlocked resource is not the lock\'s business at all', async () => {
  K.restWorld({ tokens: [] });
  const r = await K.attempt(() => W.requireWitness(
    Object.assign(ctx(), { resource: 'sv_patients' })));
  assert.strictEqual(r.outcome, 'proceed');
});

(async () => {
  for (const [name, fn] of queue) {
    if (!fn) { console.log('\n' + name); continue; }
    try {
      await fn();
      pass += 1;
      console.log('  ok   ' + name);
    } catch (e) {
      fail += 1;
      console.log('  FAIL ' + name + '\n       ' + String((e && e.message) || e).slice(0, 300));
    }
  }
  console.log('\n' + (fail ? fail + ' ARM(S) FAILED' : 'ALL ' + pass + ' ATOMICITY ARMS PASS'));
  process.exit(fail ? 1 : 0);
})();
