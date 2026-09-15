// api/_lib/resilience.js
// ---------------------------------------------------------------------------
// TIMEOUT, BULKHEAD and CIRCUIT BREAKER for this platform's outbound calls.
//
// The pattern is the standard one and is not invented here: Netflix Hystrix
// (now maintenance-mode), Resilience4j, and Polly all implement the same three
// states -- CLOSED (calls pass), OPEN (calls fail immediately instead of
// waiting on a dependency that is already known to be failing), HALF_OPEN (a
// small number of probes decide whether to trust it again) -- alongside a
// bulkhead that caps how much of a caller's resource any one dependency may
// consume. No effectiveness figure is quoted here. One was offered while this
// was being scoped and it could not be traced to a primary source, and an
// unsourced statistic in a header is the fabricated-KPI shape this codebase
// keeps removing.
//
// ══ READ THIS BEFORE USING THE BREAKER. IT IS NOT THE INTERESTING PART. ══
//
// THE THREE MECHANISMS DO NOT SURVIVE THIS RUNTIME EQUALLY, and treating them
// as one feature is how a decorative gate ships.
//
//   TIMEOUT    fully effective. Local to one call. Needs no shared state.
//   BULKHEAD   fully effective, AND CORRECT AS PER-INSTANCE -- the resource it
//              protects (this instance's sockets, event loop, memory) IS
//              per-instance. A shared bulkhead would be the wrong object.
//   BREAKER    needs state SHARED ACROSS INSTANCES, and on Vercel it does not
//              have any unless it is given some.
//
// WHY, AND IT IS MEASURED IN THIS REPO RATHER THAN REASONED ABOUT.
// api/_lib/anon-rate-limit.js shipped a per-instance counter with a threshold.
// Live, 2026-09-05: 40 concurrent requests against a limit of 20 produced 40
// refusals-for-other-reasons and NOT ONE trip. The logs showed a dozen
// instances each counting the same subject from 1. Its own header states the
// conclusion: "HORIZONTAL SCALE-OUT DEFEATS A PER-INSTANCE COUNTER, AND WORSE
// THAN THAT, IT DEFEATS IT IN PROPORTION TO THE ATTACK."
//
// A CLASSIC IN-PROCESS CIRCUIT BREAKER IS EXACTLY THAT SHAPE -- a per-instance
// failure counter with a threshold. Hystrix, Resilience4j and Polly all hold
// breaker state in process memory, which is right for a long-lived JVM or
// .NET host serving many requests, and is the wrong assumption here. Worse, the
// failure mode aligns with the incident: a dependency degrading under load is
// when Vercel adds instances, so each one counts from zero and the threshold is
// approached most slowly at exactly the moment the breaker is supposed to trip.
//
// So this module takes a STORE. `sharedStore` keeps breaker state in Postgres
// and is the real thing. `instanceStore` keeps it in memory, is honest about
// being approximate, and REFUSES to enforce -- it can observe and report, and
// that is all a per-instance counter has ever been able to do here.
//
// THE CIRCULARITY, STATED RATHER THAN DISCOVERED LATER: the shared store lives
// in Supabase, so it cannot be used to break on Supabase itself. Asking a
// database whether the database is reachable returns the answer you already
// have. A Supabase breaker is therefore instance-backed and observe-only, by
// construction and not by oversight. The TIMEOUT and the BULKHEAD are what
// actually protect a caller from a slow Supabase, and both work fine.
//
// ── WHAT THIS DOES NOT DO ──────────────────────────────────────────────────
// It does not retry. A breaker and a retry policy interact badly if either is
// added without the other in mind -- retries multiply load on a dependency that
// is already failing, which is the cascade this is meant to stop -- and this
// platform has no shared retry helper today. Adding one is a separate decision.
// ---------------------------------------------------------------------------

'use strict';

// ── TIMEOUT ────────────────────────────────────────────────────────────────
// Generalised from api/sc-eligibility.js, which on 2026-09-15 was the ONLY one
// of 684 non-test `fetch(` call sites in api/ carrying any timeout at all. Its
// comment is the argument for all of them: a ceiling "exists so a hung payer
// surfaces as an honest timeout rather than leaving the caller waiting on a
// serverless function until the platform kills it."
//
// WITHOUT A TIMEOUT THERE IS NOTHING FOR A BREAKER TO COUNT. A hung call does
// not fail; it waits. The breaker's failure threshold is never reached because
// no failure is ever recorded -- the call is still in flight when the platform
// kills the whole invocation. So this is the load-bearing half, and it is also
// the half that needs no infrastructure.
const DEFAULT_TIMEOUT_MS = 10000;

class TimeoutError extends Error {
  constructor(ms, label) {
    super('timed out after ' + ms + 'ms' + (label ? ' calling ' + label : ''));
    this.name = 'TimeoutError';
    this.code = 'DEPENDENCY_TIMEOUT';
    this.timeoutMs = ms;
    this.dependency = label || null;
  }
}
class CircuitOpenError extends Error {
  constructor(label, until) {
    super(label + ' is failing; the circuit is open. Not retried — this would '
          + 'have waited and then failed anyway.');
    this.name = 'CircuitOpenError';
    this.code = 'DEPENDENCY_CIRCUIT_OPEN';
    this.dependency = label;
    this.retryAfterMs = until;
  }
}
class BulkheadFullError extends Error {
  constructor(label, limit) {
    super(label + ' already has ' + limit + ' calls in flight from this '
          + 'instance; refusing rather than queueing.');
    this.name = 'BulkheadFullError';
    this.code = 'DEPENDENCY_BULKHEAD_FULL';
    this.dependency = label;
    this.limit = limit;
  }
}

// `fetchImpl` is injectable so a test drives this without a network, and so a
// caller can layer these in any order. Returns whatever fetchImpl returns.
async function withTimeout(fetchImpl, url, options, ms, label) {
  const limit = typeof ms === 'number' && ms > 0 ? ms : DEFAULT_TIMEOUT_MS;
  const controller = new AbortController();
  // A caller's own signal must still work. Chaining rather than replacing:
  // silently dropping an incoming signal would break cancellation somewhere
  // else and look like this module working.
  const incoming = options && options.signal;
  if (incoming) {
    if (incoming.aborted) controller.abort();
    else incoming.addEventListener('abort', () => controller.abort(), { once: true });
  }
  let timedOut = false;
  const timer = setTimeout(() => { timedOut = true; controller.abort(); }, limit);
  try {
    return await fetchImpl(url, Object.assign({}, options, { signal: controller.signal }));
  } catch (err) {
    // An abort from OUR timer is a timeout; an abort from the caller's signal
    // is a cancellation and is not this dependency's fault. Reporting a
    // cancellation as a dependency failure would feed the breaker's counter
    // with the caller's own behaviour.
    if (timedOut) throw new TimeoutError(limit, label);
    throw err;
  } finally {
    clearTimeout(timer);
  }
}

// ── BULKHEAD ───────────────────────────────────────────────────────────────
// Per-instance, and that is CORRECT here rather than a compromise: the thing
// being partitioned is this instance's own concurrency. One dependency going
// slow must not consume every socket and every bit of event-loop attention the
// instance has, leaving calls to three healthy dependencies queued behind it.
//
// IT REFUSES RATHER THAN QUEUES. A queue converts "too many calls" into
// "everything is slow", which is the failure this exists to prevent wearing a
// politer face. Refusing immediately is the whole point of the pattern.
function createBulkhead(label, limit) {
  const max = typeof limit === 'number' && limit > 0 ? limit : 6;
  let inFlight = 0;
  return {
    label: label,
    limit: max,
    inFlight: () => inFlight,
    async run(fn) {
      if (inFlight >= max) throw new BulkheadFullError(label, max);
      inFlight += 1;
      try { return await fn(); } finally { inFlight -= 1; }
    }
  };
}

// ── THE BREAKER'S STATE STORES ─────────────────────────────────────────────
// A store answers two questions and records one fact:
//   read(key)            -> { state, failures, openedAt, halfOpenProbes }
//   onResult(key, ok)    -> the same, updated
// `shared` marks whether the answer is platform-wide or one instance's guess.
// It is returned to the caller on every decision, so a log line can never be
// mistaken for the other kind -- the convention ai-rate-limit.js uses when it
// reports 'enforce-racy' rather than 'enforce'.

function instanceStore() {
  const mem = new Map();
  function slot(key) {
    if (!mem.has(key)) mem.set(key, { state: 'CLOSED', failures: 0, openedAt: 0, probes: 0 });
    return mem.get(key);
  }
  return {
    shared: false,
    // NAMED, NOT IMPLIED. The one thing this store must never do is let a
    // caller enforce on it -- see the header, and see anon-rate-limit.js for
    // what enforcing on a per-instance counter actually did in production.
    canEnforce: false,
    async read(key) { return Object.assign({}, slot(key)); },
    async write(key, next) { mem.set(key, Object.assign({}, next)); return next; },
    reset() { mem.clear(); }
  };
}

// Postgres-backed, one RPC per decision, on the pattern api/_lib/ai-rate-limit.js
// proved: a single call taking an advisory lock so the read and the write cannot
// interleave across concurrent invocations. Requires
// sql/sairn_circuit_breaker_schema.sql.
function sharedStore(client, rpcName) {
  const RPC = rpcName || 'sairn_circuit_breaker_step';
  return {
    shared: true,
    canEnforce: true,
    async step(key, outcome, cfg) {
      const r = await client.fetch(client.rest('rpc/' + RPC), {
        method: 'POST',
        headers: client.headers,
        body: JSON.stringify({
          p_key: key,
          p_outcome: outcome,               // 'success' | 'failure' | 'probe'
          p_threshold: cfg.threshold,
          p_open_ms: cfg.openMs,
          p_half_open_probes: cfg.halfOpenProbes
        })
      });
      if (!r.ok) {
        const detail = await r.json().catch(() => null);
        const e = new Error('breaker store unavailable');
        e.detail = detail;
        throw e;
      }
      const row = await r.json();
      return Array.isArray(row) ? row[0] : row;
    }
  };
}

// ── THE BREAKER ────────────────────────────────────────────────────────────
// MODE DEFAULTS TO 'observe', DELIBERATELY, AND THAT IS THIS PLATFORM'S OWN
// PROMOTION PATH rather than timidity: checks 5 and 7 in the push gate both
// shipped report-only and were promoted once their false-alarm shape was known
// to be quiet. A breaker that opens wrongly takes a working dependency offline
// for its whole open window, which is a self-inflicted outage. Observe first,
// read what it WOULD have done, then enforce.
//
// WHAT COUNTS AS A FAILURE IS NARROW, AND THIS IS THE DECISION MOST BREAKERS
// GET WRONG. A 4xx is the CALLER being wrong -- a bad payload, a missing
// licence, a refused write. Counting those trips the breaker on a bug in our
// own request and takes the dependency away from everybody else. Only a
// transport error, a timeout, or a 5xx/429 from the dependency counts.
function isDependencyFailure(resOrErr) {
  if (resOrErr instanceof TimeoutError) return true;
  if (resOrErr instanceof CircuitOpenError) return false;   // not a new failure
  if (resOrErr instanceof BulkheadFullError) return false;  // our own saturation
  if (resOrErr instanceof Error) return true;               // transport/DNS/socket
  const s = resOrErr && typeof resOrErr.status === 'number' ? resOrErr.status : 0;
  return s >= 500 || s === 429;
}

const DEFAULTS = { threshold: 5, openMs: 30000, halfOpenProbes: 2, mode: 'observe' };

function createBreaker(label, opts) {
  const cfg = Object.assign({}, DEFAULTS, opts || {});
  const store = cfg.store || instanceStore();
  const enforcing = cfg.mode === 'enforce';
  // FAIL LOUDLY RATHER THAN QUIETLY DOWNGRADE. A caller asking to enforce on a
  // store that cannot enforce has a wrong mental model of what is protecting
  // them, and silently running in observe mode would leave them believing in a
  // breaker that never trips. This is the one configuration this module
  // refuses outright.
  if (enforcing && store.canEnforce === false) {
    throw new Error(
      'resilience: refusing to enforce breaker "' + label + '" on a per-instance '
      + 'store. Horizontal scale-out defeats a per-instance threshold in '
      + 'proportion to load -- measured on this platform 2026-09-05, see '
      + 'api/_lib/anon-rate-limit.js. Use sharedStore(), or run mode:"observe".');
  }

  async function currentState(key) {
    if (store.shared) return null;                // shared store decides in-RPC
    return store.read(key);
  }

  return {
    label: label,
    mode: cfg.mode,
    shared: !!store.shared,
    store: store,
    isDependencyFailure: isDependencyFailure,

    // Returns { allowed, state, shared, mode, wouldHaveRefused }.
    // `wouldHaveRefused` is what makes observe mode worth running: it says what
    // enforcement WOULD have done, so the decision to promote is made on
    // evidence rather than on the pattern's reputation.
    async beforeCall(key) {
      const k = key || label;
      if (store.shared) {
        const row = await store.step(k, 'probe', cfg);
        const open = row && row.state === 'OPEN';
        return {
          allowed: enforcing ? !open : true,
          state: row ? row.state : 'UNKNOWN',
          shared: true, mode: cfg.mode, wouldHaveRefused: !!open
        };
      }
      const s = await currentState(k);
      let open = s.state === 'OPEN';
      if (open && Date.now() - s.openedAt >= cfg.openMs) {
        // The OPEN window has elapsed: let a bounded number of probes through.
        s.state = 'HALF_OPEN'; s.probes = 0;
        await store.write(k, s);
        open = false;
      }
      if (s.state === 'HALF_OPEN') {
        if (s.probes >= cfg.halfOpenProbes) {
          return { allowed: enforcing ? false : true, state: 'HALF_OPEN',
                   shared: false, mode: cfg.mode, wouldHaveRefused: true };
        }
        s.probes += 1;
        await store.write(k, s);
      }
      return { allowed: enforcing ? !open : true, state: s.state,
               shared: false, mode: cfg.mode, wouldHaveRefused: open };
    },

    async afterCall(key, outcome) {
      const k = key || label;
      const failed = outcome === 'failure';
      if (store.shared) {
        const row = await store.step(k, failed ? 'failure' : 'success', cfg);
        return { state: row ? row.state : 'UNKNOWN', shared: true };
      }
      const s = await store.read(k);
      if (!failed) {
        // A success in HALF_OPEN closes it. A success in CLOSED clears the
        // count -- consecutive failures are the signal, not lifetime failures,
        // or a long-lived key would eventually trip on noise.
        await store.write(k, { state: 'CLOSED', failures: 0, openedAt: 0, probes: 0 });
        return { state: 'CLOSED', shared: false };
      }
      const failures = s.failures + 1;
      if (s.state === 'HALF_OPEN' || failures >= cfg.threshold) {
        await store.write(k, { state: 'OPEN', failures: failures,
                               openedAt: Date.now(), probes: 0 });
        return { state: 'OPEN', shared: false };
      }
      await store.write(k, { state: s.state, failures: failures,
                             openedAt: s.openedAt, probes: s.probes });
      return { state: s.state, shared: false };
    }
  };
}

// ── THE THREE COMPOSED, WHICH IS THE ONLY WAY THEY ARE USEFUL ──────────────
// Order matters and is not arbitrary:
//   1. BREAKER first  -- if it is open, spend nothing at all, not even a slot.
//   2. BULKHEAD next  -- refuse before occupying a socket.
//   3. TIMEOUT last   -- bound the call that actually goes out.
// A bulkhead outside the breaker would let an open circuit still consume slots;
// a timeout outside the bulkhead would bound the wait for a slot rather than
// the call, which is a different and much less useful guarantee.
async function guardedFetch(guard, url, options) {
  const { breaker, bulkhead, timeoutMs, fetchImpl, key } = guard;
  const label = (breaker && breaker.label) || (bulkhead && bulkhead.label) || 'dependency';
  const impl = fetchImpl || fetch;

  let decision = { allowed: true, state: 'NO_BREAKER', shared: false, mode: 'none',
                   wouldHaveRefused: false };
  if (breaker) {
    decision = await breaker.beforeCall(key);
    if (!decision.allowed) throw new CircuitOpenError(label, guard.openMs || 30000);
  }

  const call = async () => {
    try {
      const res = await withTimeout(impl, url, options, timeoutMs, label);
      if (breaker) {
        await breaker.afterCall(key, isDependencyFailure(res) ? 'failure' : 'success');
      }
      return { res: res, decision: decision };
    } catch (err) {
      if (breaker && isDependencyFailure(err)) await breaker.afterCall(key, 'failure');
      throw err;
    }
  };
  return bulkhead ? bulkhead.run(call) : call();
}

module.exports = {
  withTimeout,
  createBulkhead,
  createBreaker,
  instanceStore,
  sharedStore,
  guardedFetch,
  isDependencyFailure,
  TimeoutError,
  CircuitOpenError,
  BulkheadFullError,
  DEFAULT_TIMEOUT_MS,
  DEFAULTS
};
