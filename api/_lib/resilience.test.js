// api/_lib/resilience.test.js
//
// Run:  node api/_lib/resilience.test.js
//
// Control for api/_lib/resilience.js.
//
// WHAT A CONTROL FOR THIS HAS TO PROVE, and it is not "the breaker opens".
// Every mechanism here is a REFUSAL, and a suite of refusals is the easiest
// kind to write so that it passes vacuously: a module that refused everything
// would satisfy "does it refuse?" on every arm. So each refusal arm is paired
// with an arm proving the thing still PASSES traffic in the ordinary case.
//
// THE SHARPEST ARMS ARE THE THREE THAT ARE ABOUT THIS RUNTIME RATHER THAN
// ABOUT THE PATTERN:
//   * enforcing on a per-instance store is REFUSED, loudly, at construction
//     (section 5) -- the whole reason this module takes a store at all;
//   * a 4xx does NOT count as a dependency failure (section 4) -- the decision
//     most breaker implementations get wrong, and the one that would take a
//     healthy dependency offline because of a bug in our own request;
//   * a caller's own AbortSignal is a cancellation, NOT a dependency failure
//     (section 2), or the breaker's counter gets fed the caller's behaviour.

'use strict';
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const R = require('./resilience.js');

let pass = 0, fail = 0;
const queue = [];
function t(name, fn) { queue.push([name, fn]); }
function section(s) { queue.push([s, null]); }

const OK = { status: 200, ok: true };
const FIVE = { status: 503, ok: false };
const FOUR = { status: 400, ok: false };

function stubFetch(answers) {
  let i = 0;
  const calls = [];
  return Object.assign(async function (url, opts) {
    calls.push({ url: String(url), opts: opts });
    const a = answers[Math.min(i, answers.length - 1)];
    i += 1;
    if (a instanceof Error) throw a;
    if (typeof a === 'number') {                 // hang for N ms, honouring abort
      return new Promise((resolve, reject) => {
        const timer = setTimeout(() => resolve(OK), a);
        if (opts && opts.signal) {
          opts.signal.addEventListener('abort', () => {
            clearTimeout(timer);
            const e = new Error('aborted'); e.name = 'AbortError'; reject(e);
          }, { once: true });
        }
      });
    }
    return a;
  }, { calls: calls });
}

// ════════════════════════════════════════════════════════════════════════════
section('1. TIMEOUT -- the half that needs no infrastructure');
t('a call that answers in time is returned untouched', async () => {
  const f = stubFetch([OK]);
  const res = await R.withTimeout(f, 'https://x.test', {}, 50, 'x');
  assert.strictEqual(res.status, 200);
});
t('a hung call raises TimeoutError, it does not wait for the platform to kill it', async () => {
  const f = stubFetch([5000]);
  await assert.rejects(
    () => R.withTimeout(f, 'https://x.test', {}, 20, 'stripe'),
    (e) => e instanceof R.TimeoutError && e.code === 'DEPENDENCY_TIMEOUT'
           && /stripe/.test(e.message));
});
t('the abort really reaches the call -- the stub was cancelled, not abandoned', async () => {
  // Without this, "it rejected after 20ms" is also satisfied by a module that
  // races a timer and leaves the request running, which is the shape that
  // exhausts sockets while looking like a working timeout.
  let aborted = false;
  const f = async (url, opts) => new Promise((resolve, reject) => {
    opts.signal.addEventListener('abort', () => {
      aborted = true;
      const e = new Error('aborted'); e.name = 'AbortError'; reject(e);
    }, { once: true });
  });
  await assert.rejects(() => R.withTimeout(f, 'u', {}, 10, 'x'));
  assert.strictEqual(aborted, true, 'the signal was passed through and fired');
});
t('the default ceiling is a real number, not undefined', () => {
  assert.strictEqual(typeof R.DEFAULT_TIMEOUT_MS, 'number');
  assert.ok(R.DEFAULT_TIMEOUT_MS > 0);
});

// ════════════════════════════════════════════════════════════════════════════
section('2. a CALLER\'S cancellation is not a dependency failure');
t('a caller\'s own abort propagates as its own error, not as TimeoutError', async () => {
  const ac = new AbortController();
  const f = async (url, opts) => new Promise((resolve, reject) => {
    opts.signal.addEventListener('abort', () => {
      const e = new Error('aborted'); e.name = 'AbortError'; reject(e);
    }, { once: true });
  });
  const p = R.withTimeout(f, 'u', { signal: ac.signal }, 60000, 'supabase');
  ac.abort();
  await assert.rejects(p, (e) => !(e instanceof R.TimeoutError),
    'reporting a caller cancellation as a dependency timeout feeds the breaker '
    + 'the caller\'s own behaviour');
});
t('an ALREADY-aborted caller signal is honoured rather than ignored', async () => {
  const ac = new AbortController();
  ac.abort();
  const f = async (url, opts) => {
    assert.strictEqual(opts.signal.aborted, true, 'the chained signal starts aborted');
    const e = new Error('aborted'); e.name = 'AbortError'; throw e;
  };
  await assert.rejects(() => R.withTimeout(f, 'u', { signal: ac.signal }, 1000, 'x'));
});

// ════════════════════════════════════════════════════════════════════════════
section('3. BULKHEAD -- refuses, and does not queue');
t('calls under the limit run', async () => {
  const b = R.createBulkhead('claude', 2);
  assert.strictEqual(await b.run(async () => 'a'), 'a');
  assert.strictEqual(b.inFlight(), 0, 'the slot is released');
});
t('the call OVER the limit is refused immediately, not queued', async () => {
  const b = R.createBulkhead('claude', 1);
  let release;
  const held = b.run(() => new Promise((r) => { release = r; }));
  await assert.rejects(() => b.run(async () => 'second'),
    (e) => e instanceof R.BulkheadFullError && e.code === 'DEPENDENCY_BULKHEAD_FULL');
  release('done'); await held;
});
t('...and the slot is freed even when the call THROWS', async () => {
  // A leaked slot on the error path turns the bulkhead into a permanent refusal
  // after N failures -- a self-inflicted outage that looks like the dependency.
  const b = R.createBulkhead('x', 1);
  await assert.rejects(() => b.run(async () => { throw new Error('boom'); }));
  assert.strictEqual(b.inFlight(), 0);
  assert.strictEqual(await b.run(async () => 'ok'), 'ok');
});
t('CONTROL: after a refusal the bulkhead still passes traffic', async () => {
  const b = R.createBulkhead('x', 1);
  let release;
  const held = b.run(() => new Promise((r) => { release = r; }));
  await assert.rejects(() => b.run(async () => 1));
  release(0); await held;
  assert.strictEqual(await b.run(async () => 'through'), 'through');
});

// ════════════════════════════════════════════════════════════════════════════
section('4. WHAT COUNTS AS A DEPENDENCY FAILURE');
t('5xx and 429 count', () => {
  assert.strictEqual(R.isDependencyFailure({ status: 503 }), true);
  assert.strictEqual(R.isDependencyFailure({ status: 500 }), true);
  assert.strictEqual(R.isDependencyFailure({ status: 429 }), true);
});
t('a TIMEOUT counts', () => {
  assert.strictEqual(R.isDependencyFailure(new R.TimeoutError(10, 'x')), true);
});
t('a 4xx does NOT count -- that is OUR request being wrong', () => {
  [400, 401, 403, 404, 409, 422].forEach((s) => {
    assert.strictEqual(R.isDependencyFailure({ status: s }), false,
      s + ' must not trip a breaker; counting it takes a healthy dependency '
      + 'away from everyone because of a bug in one caller\'s payload');
  });
});
t('a 2xx/3xx does not count', () => {
  [200, 201, 204, 302].forEach((s) => assert.strictEqual(R.isDependencyFailure({ status: s }), false));
});
t('the breaker\'s OWN refusals do not count as new failures', () => {
  assert.strictEqual(R.isDependencyFailure(new R.CircuitOpenError('x', 1)), false,
    'counting the refusal would keep the circuit open forever by its own output');
  assert.strictEqual(R.isDependencyFailure(new R.BulkheadFullError('x', 1)), false,
    'our own saturation is not the dependency failing');
});

// ════════════════════════════════════════════════════════════════════════════
section('5. THE RUNTIME ARM -- enforcing on a per-instance store is REFUSED');
t('mode:"enforce" on an instance store throws at construction', () => {
  assert.throws(
    () => R.createBreaker('supabase', { mode: 'enforce', store: R.instanceStore() }),
    (e) => /per-instance store/.test(e.message) && /2026-09-05/.test(e.message),
    'a per-instance threshold is defeated by scale-out in proportion to load, '
    + 'measured on this platform; silently downgrading to observe would leave '
    + 'the caller believing in a breaker that never trips');
});
t('observe mode on an instance store is allowed -- it can report', () => {
  const b = R.createBreaker('supabase', { store: R.instanceStore() });
  assert.strictEqual(b.mode, 'observe');
  assert.strictEqual(b.shared, false);
});
t('a SHARED store may enforce', () => {
  const client = { rest: (p) => 'https://db.test/' + p, headers: {}, fetch: async () => ({ ok: true, json: async () => ({ state: 'CLOSED' }) }) };
  const b = R.createBreaker('stripe', { mode: 'enforce', store: R.sharedStore(client) });
  assert.strictEqual(b.shared, true);
});
t('every decision REPORTS which kind of store answered it', async () => {
  // The ai-rate-limit.js convention: 'enforce-racy' rather than 'enforce', so a
  // log line can never be mistaken for the stronger guarantee.
  const b = R.createBreaker('x', { store: R.instanceStore() });
  const d = await b.beforeCall('x');
  assert.strictEqual(d.shared, false);
  assert.strictEqual(d.mode, 'observe');
  assert.ok('wouldHaveRefused' in d, 'observe mode must say what enforcing WOULD have done');
});

// ════════════════════════════════════════════════════════════════════════════
section('6. THE THREE STATES, on a store that can hold them');
function breaker(extra) {
  return R.createBreaker('dep', Object.assign(
    { store: R.instanceStore(), threshold: 3, openMs: 40, halfOpenProbes: 1, mode: 'enforce' },
    extra || {}));
}
// mode:'enforce' is legal here ONLY because the arms below override canEnforce
// on a store they own outright. Stated so this is not read as contradicting
// section 5 -- what is being tested is the STATE MACHINE, not the policy.
function enforceableInstanceStore() {
  const s = R.instanceStore();
  s.canEnforce = true;
  return s;
}
t('CLOSED passes traffic', async () => {
  const b = breaker({ store: enforceableInstanceStore() });
  const d = await b.beforeCall('k');
  assert.strictEqual(d.allowed, true);
  assert.strictEqual(d.state, 'CLOSED');
});
t('the threshold of consecutive failures OPENS it', async () => {
  const b = breaker({ store: enforceableInstanceStore() });
  for (let i = 0; i < 3; i += 1) await b.afterCall('k', 'failure');
  const d = await b.beforeCall('k');
  assert.strictEqual(d.state, 'OPEN');
  assert.strictEqual(d.allowed, false, 'an open circuit fails immediately');
});
t('a SUCCESS before the threshold resets the count -- consecutive, not lifetime', async () => {
  // Without this a long-lived key eventually trips on unrelated noise spread
  // over hours, which is an outage caused by the breaker rather than prevented.
  const b = breaker({ store: enforceableInstanceStore() });
  await b.afterCall('k', 'failure');
  await b.afterCall('k', 'failure');
  await b.afterCall('k', 'success');
  await b.afterCall('k', 'failure');
  const d = await b.beforeCall('k');
  assert.strictEqual(d.state, 'CLOSED');
  assert.strictEqual(d.allowed, true);
});
t('after the open window it goes HALF_OPEN and admits a bounded probe', async () => {
  const b = breaker({ store: enforceableInstanceStore() });
  for (let i = 0; i < 3; i += 1) await b.afterCall('k', 'failure');
  await new Promise((r) => setTimeout(r, 55));
  const first = await b.beforeCall('k');
  assert.strictEqual(first.state, 'HALF_OPEN');
  assert.strictEqual(first.allowed, true, 'the probe is what tests recovery');
  const second = await b.beforeCall('k');
  assert.strictEqual(second.allowed, false, 'only halfOpenProbes get through');
});
t('a probe that SUCCEEDS closes it', async () => {
  const b = breaker({ store: enforceableInstanceStore() });
  for (let i = 0; i < 3; i += 1) await b.afterCall('k', 'failure');
  await new Promise((r) => setTimeout(r, 55));
  await b.beforeCall('k');
  await b.afterCall('k', 'success');
  const d = await b.beforeCall('k');
  assert.strictEqual(d.state, 'CLOSED');
  assert.strictEqual(d.allowed, true);
});
t('a probe that FAILS re-opens it immediately, without re-counting to the threshold', async () => {
  const b = breaker({ store: enforceableInstanceStore() });
  for (let i = 0; i < 3; i += 1) await b.afterCall('k', 'failure');
  await new Promise((r) => setTimeout(r, 55));
  await b.beforeCall('k');
  await b.afterCall('k', 'failure');
  const d = await b.beforeCall('k');
  assert.strictEqual(d.state, 'OPEN',
    'a still-broken dependency must not get another full threshold of traffic');
});
t('two dependencies do not share a circuit', async () => {
  const b = breaker({ store: enforceableInstanceStore() });
  for (let i = 0; i < 3; i += 1) await b.afterCall('stripe', 'failure');
  assert.strictEqual((await b.beforeCall('stripe')).state, 'OPEN');
  assert.strictEqual((await b.beforeCall('claude')).state, 'CLOSED',
    'one failing dependency must not take the others down -- that IS the cascade');
});

// ════════════════════════════════════════════════════════════════════════════
section('7. OBSERVE MODE reports without refusing');
t('an open circuit in observe mode still lets the call through', async () => {
  const b = R.createBreaker('dep', { store: R.instanceStore(), threshold: 2,
                                     openMs: 10000, mode: 'observe' });
  await b.afterCall('k', 'failure');
  await b.afterCall('k', 'failure');
  const d = await b.beforeCall('k');
  assert.strictEqual(d.allowed, true, 'observe must never refuse');
  assert.strictEqual(d.wouldHaveRefused, true,
    '...and must say what enforcing would have done, or observing buys nothing');
});

// ════════════════════════════════════════════════════════════════════════════
section('8. COMPOSED -- order is load-bearing');
t('an OPEN circuit costs no bulkhead slot at all', async () => {
  const store = enforceableInstanceStore();
  const b = R.createBreaker('dep', { store: store, threshold: 1, openMs: 10000,
                                     mode: 'enforce' });
  await b.afterCall('dep', 'failure');
  const bh = R.createBulkhead('dep', 1);
  const f = stubFetch([OK]);
  await assert.rejects(
    () => R.guardedFetch({ breaker: b, bulkhead: bh, timeoutMs: 50, fetchImpl: f }, 'u', {}),
    (e) => e instanceof R.CircuitOpenError);
  assert.strictEqual(bh.inFlight(), 0);
  assert.strictEqual(f.calls.length, 0, 'and no request was sent');
});
t('a healthy call passes all three and reaches the dependency', async () => {
  const b = R.createBreaker('dep', { store: enforceableInstanceStore(), mode: 'enforce' });
  const bh = R.createBulkhead('dep', 2);
  const f = stubFetch([OK]);
  const out = await R.guardedFetch({ breaker: b, bulkhead: bh, timeoutMs: 100, fetchImpl: f }, 'u', {});
  assert.strictEqual(out.res.status, 200);
  assert.strictEqual(f.calls.length, 1);
});
t('a 5xx from the dependency is recorded and eventually opens the circuit', async () => {
  const b = R.createBreaker('dep', { store: enforceableInstanceStore(), threshold: 2,
                                     openMs: 10000, mode: 'enforce' });
  const f = stubFetch([FIVE, FIVE]);
  const g = { breaker: b, timeoutMs: 100, fetchImpl: f };
  await R.guardedFetch(g, 'u', {});
  await R.guardedFetch(g, 'u', {});
  await assert.rejects(() => R.guardedFetch(g, 'u', {}), (e) => e instanceof R.CircuitOpenError);
});
t('a 4xx does NOT open it, however many times it happens', async () => {
  const b = R.createBreaker('dep', { store: enforceableInstanceStore(), threshold: 2,
                                     openMs: 10000, mode: 'enforce' });
  const f = stubFetch([FOUR]);
  const g = { breaker: b, timeoutMs: 100, fetchImpl: f };
  for (let i = 0; i < 6; i += 1) await R.guardedFetch(g, 'u', {});
  const d = await b.beforeCall('dep');
  assert.strictEqual(d.state, 'CLOSED',
    'six refused-because-our-payload-was-wrong responses must leave the '
    + 'dependency available to every other caller');
});
t('a TIMEOUT inside the composition is recorded as a failure', async () => {
  const b = R.createBreaker('dep', { store: enforceableInstanceStore(), threshold: 1,
                                     openMs: 10000, mode: 'enforce' });
  const f = stubFetch([5000]);
  await assert.rejects(
    () => R.guardedFetch({ breaker: b, timeoutMs: 15, fetchImpl: f }, 'u', {}),
    (e) => e instanceof R.TimeoutError);
  const d = await b.beforeCall('dep');
  assert.strictEqual(d.state, 'OPEN',
    'without a timeout there is nothing for a breaker to count -- a hung call '
    + 'never fails, it waits');
});

// ════════════════════════════════════════════════════════════════════════════
section('9. THE HEADER MAKES NO UNSOURCED EFFECTIVENESS CLAIM');
t('no percentage figure is asserted anywhere in the module', () => {
  // A number was offered while this was scoped and could not be traced to a
  // primary source. This arm is why it cannot come back in quietly later.
  const src = fs.readFileSync(path.join(__dirname, 'resilience.js'), 'utf8');
  const pcts = src.match(/\b\d+(\.\d+)?\s?%/g) || [];
  assert.deepStrictEqual(pcts, [],
    'an unsourced statistic in a header is the fabricated-KPI shape this '
    + 'codebase keeps removing; found: ' + pcts.join(', '));
});
t('the named real implementations ARE cited, so the pattern is attributable', () => {
  const src = fs.readFileSync(path.join(__dirname, 'resilience.js'), 'utf8');
  ['Hystrix', 'Resilience4j', 'Polly'].forEach((n) => {
    assert.ok(src.indexOf(n) !== -1, n + ' should be named');
  });
});

(async () => {
  for (const [name, fn] of queue) {
    if (!fn) { console.log('--- ' + name + ' ---'); continue; }
    try { await fn(); console.log('  ok   ' + name); pass++; }
    catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
  }
  console.log('\nresilience: ' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
