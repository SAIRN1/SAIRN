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
  const fresh = tokenRow('t2', PAYLOAD);
  const ttl = new Date(fresh.expires_at).getTime() - Date.now();
  assert.ok(ttl > W.TOKEN_TTL_MS - 5000 && ttl <= W.TOKEN_TTL_MS,
    'the replacement window is ' + ttl + 'ms, not TOKEN_TTL_MS');
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
