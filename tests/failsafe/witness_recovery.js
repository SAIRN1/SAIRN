// tests/failsafe/witness_recovery.js
//
// Run:  node tests/failsafe/witness_recovery.js
//
// ITEM 83b -- RECOVERY ROUND-TRIP, applied to the witnessing lock (item 19).
//
// A fail-safe default that fires is a system in its SAFE state. That is not the
// same as a system that is working, and the difference is never tested: every
// arm anywhere on this platform stops at "it refused". Nothing walks the
// documented recovery and proves the thing goes back to doing its job.
//
// ── THE DOCUMENTED RECOVERY, QUOTED FROM THE LOCK ITSELF ───────────────────
// api/sv-witness.js says, twice, what to do after the safe state fires:
//
//   "a lost token is re-requested, which costs one confirmation rather than
//    leaving a readable table of live signatures"
//   "the token is burned and the record must be confirmed again -- which is
//    the direction to fail in"
//
// So the recovery is: confirm the record again, and write. This file runs that
// and asserts it actually returns the system to normal.
//
// ── WHAT "WITHIN THE WINDOW" MEANS HERE, stated rather than assumed ────────
// There is no separate recovery SLA written down, so inventing a number would
// be fabricating the standard. What the lock DOES commit to is observable and
// is what the arms below use:
//
//   * recovery costs exactly ONE new confirmation, not a cascade;
//   * it is available immediately -- no cool-off, no lockout counter;
//   * the replacement confirmation is valid for TOKEN_TTL_MS, so the window to
//     complete the write after recovering is the lock's own stated 10 minutes;
//   * and recovery must NOT widen what may be written.
//
// That last one is the arm worth having. A recovery path that lets a DIFFERENT
// record through is worse than no recovery: it turns an interruption into an
// opportunity, on an append-only controlled-substance register where a wrong
// row can never be taken back.
//
// ── HONEST SCOPE ───────────────────────────────────────────────────────────
// The recovery is driven at requireWitness() against the kit's in-memory table.
// Re-confirming is modelled by issuing a fresh token row bound to the SAME
// content hash, computed with the module's own contentHash() -- which is what
// the `request` action stores. It does not drive the HTTP handler, so it proves
// the LOCK recovers and not that the endpoint's auth path does. Named here
// rather than left for a reader to discover.

'use strict';
const assert = require('assert');
const crypto = require('crypto');
const path = require('path');
const W = require(path.join(__dirname, '..', '..', 'api', 'sv-witness.js'));
const K = require('./failsafekit.js');

let pass = 0, fail = 0;
const queue = [];
function t(name, fn) { queue.push([name, fn]); }
function section(s) { queue.push([s, null]); }

const PAYLOAD = { id: 'c1', drug: 'ketamine', qty: 2, vet: 'dr-a' };
const OTHER = { id: 'c1', drug: 'ketamine', qty: 20, vet: 'dr-a' };

function hash(tok) { return crypto.createHash('sha256').update(tok).digest('hex'); }

function tokenRow(tok, payload, extra) {
  return Object.assign({
    id: 'row-' + tok,
    license_hash: 'L1',
    token_hash: hash(tok),
    content_hash: W.contentHash('sv_controlled', payload),
    witness_employee_id: 'e1',
    countersign_employee_id: null,
    spent_at: null,
    expires_at: new Date(Date.now() + W.TOKEN_TTL_MS).toISOString(),
  }, extra || {});
}

function ctx(tok, payload) {
  return {
    resource: 'sv_controlled', payload: payload || PAYLOAD, licHash: 'L1',
    rest: (p) => 'https://db/rest/v1/' + p,
    headers: {}, token: tok,
  };
}

section('A. the safe state really fires, or there is nothing to recover from');

t('an interrupted transition leaves the write unmade', async () => {
  const world = K.restWorld({ tokens: [tokenRow('t1', PAYLOAD)], interruptAfter: 1 });
  const r = await K.attempt(() => W.requireWitness(ctx('t1')));
  assert.strictEqual(r.outcome, 'interrupted');
  assert.strictEqual(world.tokens[0].spent_at, null);
});

t('a BURNED token refuses -- the state recovery has to start from', async () => {
  const world = K.restWorld({ tokens: [tokenRow('t1', PAYLOAD, { spent_at: new Date().toISOString() })] });
  const r = await K.attempt(() => W.requireWitness(ctx('t1')));
  assert.strictEqual(r.outcome, 'refused');
  assert.strictEqual(r.refusal.body.error.code, 'WITNESS_ALREADY_SPENT');
  assert.strictEqual(world.applied.length, 0);
});

section('B. THE ROUND TRIP -- confirm again, and the write goes through');

t('one fresh confirmation restores normal operation', async () => {
  const burned = tokenRow('t1', PAYLOAD, { spent_at: new Date().toISOString() });
  const fresh = tokenRow('t2', PAYLOAD);
  const world = K.restWorld({ tokens: [burned, fresh] });
  const r = await K.attempt(() => W.requireWitness(ctx('t2')));
  assert.strictEqual(r.outcome, 'proceed', JSON.stringify(r.refusal));
  assert.ok(world.tokens[1].spent_at, 'the replacement was not spent');
});

t('and it costs exactly ONE confirmation -- no cascade, no cool-off', async () => {
  const burned = tokenRow('t1', PAYLOAD, { spent_at: new Date().toISOString() });
  const fresh = tokenRow('t2', PAYLOAD);
  const world = K.restWorld({ tokens: [burned, fresh] });
  await K.attempt(() => W.requireWitness(ctx('t2')));
  const issued = world.applied.filter((a) => a.op === 'issue').length;
  const spends = world.applied.filter((a) => a.op === 'spend').length;
  assert.strictEqual(spends, 1, 'recovery spent ' + spends + ' confirmations');
  assert.strictEqual(issued, 0, 'the lock issued a confirmation by itself');
});

t('recovery is available IMMEDIATELY -- the burn is not a lockout', async () => {
  // A fail-safe that fires and then refuses to be reset is an outage wearing a
  // safety label. Asserted because "it stopped" would pass without it.
  const burned = tokenRow('t1', PAYLOAD, { spent_at: new Date().toISOString() });
  const fresh = tokenRow('t2', PAYLOAD);
  K.restWorld({ tokens: [burned, fresh] });
  const started = Date.now();
  const r = await K.attempt(() => W.requireWitness(ctx('t2')));
  assert.strictEqual(r.outcome, 'proceed');
  assert.ok(Date.now() - started < 1000, 'recovery was not immediate');
});

t('the replacement is valid for the lock\'s own stated window', async () => {
  // Not a number typed here: TOKEN_TTL_MS is imported, so if the lock changes
  // its window this arm follows it instead of contradicting it.
  //
  // AND THIS ARM IS NOT EXPIRY COVERAGE, which is why section B2 below exists.
  // It measures a SUBTRACTION -- expires_at minus now -- and both ends come off
  // the same `Date.now()` the builder used, so it agrees with itself whatever
  // TOKEN_TTL_MS is. It was the arm that made expiry LOOK tested while a
  // mutation disabling the expiry check survived both suites entirely.
  const fresh = tokenRow('t2', PAYLOAD);
  const ttl = new Date(fresh.expires_at).getTime() - Date.now();
  assert.ok(ttl > W.TOKEN_TTL_MS - 5000 && ttl <= W.TOKEN_TTL_MS,
    'the replacement window is ' + ttl + 'ms, not TOKEN_TTL_MS');
});

section('B2. REAL WALL-CLOCK EXPIRY -- the clock moves, the row does not');

// WHAT THE FIRST TWO PASSES BOTH MISSED, AND THEY MISSED IT DIFFERENTLY.
// Pass one measured the remaining TTL (the arm directly above) -- a
// subtraction, not a behaviour. Pass two, by an independent reviewer, drove a
// BACKDATED ROW (`expires_at: Date.now() - 1000`) and proved the comparison
// exists. Neither drives the transition that actually happens in production: a
// token the lock itself issued as VALID becoming refused because time passed.
//
// The flaw common to both is that the test did the same arithmetic as the code.
// The lock mints `Date.now() + TOKEN_TTL_MS`; a test that adds or subtracts
// against `Date.now()` is checking its own sum. If TOKEN_TTL_MS were 0,
// negative, or in seconds instead of milliseconds, EVERY arm in both suites
// still passed -- because a backdated row is still refused and a measured
// window still matches the constant that produced it.
//
// So these arms change ONE thing: the clock the lock reads, via
// K.withClockAt/withClockAdvanced. The token row is built once, at T0, and
// never touched again. The mechanism (move time) is structurally different
// from the assertion (was it refused), which is what makes it independent
// rather than a third offset.

t('a token issued VALID is ALLOWED at the instant it was issued', async () => {
  // The control, and it carries more weight than a usual one: if TOKEN_TTL_MS
  // were zero or negative this arm FAILS, which no backdated-row arm can
  // detect. It is the only thing in either suite that would notice a
  // misconfigured window.
  const t0 = Date.now();
  const row = await K.withClockAt(t0, () => tokenRow('tx', PAYLOAD));
  const world = K.restWorld({ tokens: [row] });
  const r = await K.withClockAt(t0, () => K.attempt(() => W.requireWitness(ctx('tx', PAYLOAD))));
  assert.notStrictEqual(r.outcome, 'refused',
    'a freshly issued token was refused at T0 -- TOKEN_TTL_MS may be <= 0');
  assert.ok(world.applied.length > 0, 'the spend did not land at T0');
});

t('...and the SAME UNTOUCHED ROW is refused once the clock passes its expiry',
  async () => {
    const t0 = Date.now();
    const row = await K.withClockAt(t0, () => tokenRow('ty', PAYLOAD));
    const before = JSON.stringify(row);
    const world = K.restWorld({ tokens: [row] });
    const r = await K.withClockAdvanced(t0, W.TOKEN_TTL_MS + 1000,
      () => K.attempt(() => W.requireWitness(ctx('ty', PAYLOAD))));
    assert.strictEqual(r.outcome, 'refused',
      'time passed the expiry and the token still spent');
    assert.strictEqual(world.applied.length, 0,
      'an expired token reached the spend -- the write landed');
    // THE ROW WAS NEVER EDITED. Asserted rather than assumed, because the
    // whole claim of this section is that only the clock moved.
    assert.strictEqual(JSON.stringify(
      Object.assign({}, row, { spent_at: null })), before.replace(/"spent_at":"[^"]*"/, '"spent_at":null'),
      'the row was mutated, so this is not a pure clock test');
  });

t('the boundary is where TOKEN_TTL_MS says it is, from BOTH sides', async () => {
  // One millisecond before the window closes it must still work; one after, it
  // must not. Two arms on one line of the lock, so a comparison flipped from
  // <= to < , or a window silently halved, is caught rather than inferred.
  const t0 = Date.now();

  const rowIn = await K.withClockAt(t0, () => tokenRow('tz1', PAYLOAD));
  const wIn = K.restWorld({ tokens: [rowIn] });
  const rIn = await K.withClockAdvanced(t0, W.TOKEN_TTL_MS - 1,
    () => K.attempt(() => W.requireWitness(ctx('tz1', PAYLOAD))));
  assert.notStrictEqual(rIn.outcome, 'refused',
    'refused 1ms INSIDE the stated window -- the window is shorter than TOKEN_TTL_MS');
  assert.ok(wIn.applied.length > 0, 'the spend did not land just inside the window');

  const rowOut = await K.withClockAt(t0, () => tokenRow('tz2', PAYLOAD));
  const wOut = K.restWorld({ tokens: [rowOut] });
  const rOut = await K.withClockAdvanced(t0, W.TOKEN_TTL_MS + 1,
    () => K.attempt(() => W.requireWitness(ctx('tz2', PAYLOAD))));
  assert.strictEqual(rOut.outcome, 'refused',
    'allowed 1ms OUTSIDE the stated window -- the window is longer than TOKEN_TTL_MS');
  assert.strictEqual(wOut.applied.length, 0, 'the spend landed outside the window');
});

t('an expired token is refused BEFORE the compare-and-set, not by losing it',
  async () => {
    // The distinction that matters on an append-only controlled-substance
    // register: refusing because the CAS found no unspent row is a DIFFERENT
    // fact from refusing because the token is out of date, and only the second
    // is a fail-safe. If expiry were ever removed, an expired-but-unspent
    // token would sail through the CAS and write -- so this asserts no PATCH
    // was attempted at all, rather than merely that the outcome was refused.
    const t0 = Date.now();
    const row = await K.withClockAt(t0, () => tokenRow('tw', PAYLOAD));
    const world = K.restWorld({ tokens: [row] });
    await K.withClockAdvanced(t0, W.TOKEN_TTL_MS + 60000,
      () => K.attempt(() => W.requireWitness(ctx('tw', PAYLOAD))));
    const patches = world.calls.filter((c) => c.method === 'PATCH');
    assert.strictEqual(patches.length, 0,
      'the lock attempted a spend on an expired token (' + patches.length +
      ' PATCH call(s)) -- expiry is being enforced by the CAS rather than by the guard');
  });

section('C. RECOVERY MUST NOT WIDEN WHAT MAY BE WRITTEN');

t('a replacement confirmed for a DIFFERENT record is refused', async () => {
  // The arm worth having. If an interruption could be used to swap the record,
  // the lock would be turning a fault into an opportunity -- on an append-only
  // register where the wrong row stands forever.
  const fresh = tokenRow('t2', OTHER);
  const world = K.restWorld({ tokens: [fresh] });
  const r = await K.attempt(() => W.requireWitness(ctx('t2', PAYLOAD)));
  assert.strictEqual(r.outcome, 'refused');
  assert.strictEqual(r.refusal.body.error.code, 'WITNESS_CONTENT_MISMATCH');
  assert.strictEqual(world.tokens[0].spent_at, null,
    'a mismatched confirmation was burned, which costs the operator a second one');
});

t('the OLD burned token stays refused after recovery', async () => {
  const burned = tokenRow('t1', PAYLOAD, { spent_at: new Date().toISOString() });
  const fresh = tokenRow('t2', PAYLOAD);
  K.restWorld({ tokens: [burned, fresh] });
  await K.attempt(() => W.requireWitness(ctx('t2')));
  const r = await K.attempt(() => W.requireWitness(ctx('t1')));
  assert.strictEqual(r.outcome, 'refused');
  assert.strictEqual(r.refusal.body.error.code, 'WITNESS_ALREADY_SPENT');
});

t('recovery does not bypass the two-person policy', async () => {
  const fresh = tokenRow('t2', PAYLOAD);
  K.restWorld({ tokens: [fresh], policy: { require_two_person: true } });
  const r = await K.attempt(() => W.requireWitness(ctx('t2')));
  assert.strictEqual(r.outcome, 'refused');
  assert.strictEqual(r.refusal.body.error.code, 'COUNTERSIGN_REQUIRED');
});

t('...and with the countersignature present it proceeds', async () => {
  const fresh = tokenRow('t2', PAYLOAD, { countersign_employee_id: 'e2' });
  const world = K.restWorld({ tokens: [fresh], policy: { require_two_person: true } });
  const r = await K.attempt(() => W.requireWitness(ctx('t2')));
  assert.strictEqual(r.outcome, 'proceed', JSON.stringify(r.refusal));
  assert.ok(world.tokens[0].spent_at);
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
  console.log('\n' + (fail ? fail + ' ARM(S) FAILED' : 'ALL ' + pass + ' RECOVERY ARMS PASS'));
  process.exit(fail ? 1 : 0);
})();
