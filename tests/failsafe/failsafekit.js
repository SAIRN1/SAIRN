// tests/failsafe/failsafekit.js
//
// THE TWO QUESTIONS A FAIL-SAFE DEFAULT IS NEVER ASKED.
//
// This platform has a growing family of fail-safe defaults -- the witnessing
// lock, the cron watchdog, deny-by-default auth gates, the push gate's
// could-not-tell refusals. Every one of them is tested the same way: drive it
// into the unsafe condition and prove it refuses. That is necessary and it is
// not sufficient, because it only ever asks whether the transition FIRES.
//
// Two questions nothing here has asked:
//
//   ATOMICITY        the transition itself is several steps. Kill the process
//                    or drop the connection between any two of them and the
//                    system settles SOMEWHERE. Is every one of those resting
//                    places safe, or is one of them half-transitioned -- the
//                    guard consumed but the protection not applied, or the
//                    protection applied with the guard still reusable?
//
//   RECOVERY         a fail-safe default that fires is a system in its safe
//                    state, not a system that is working. Does the documented
//                    recovery actually return it to normal operation, and
//                    within the window somebody agreed to? "It stopped" and
//                    "it recovered" are different claims and only the first is
//                    ever tested.
//
// ── WHY A REAL STATE MACHINE AND NOT A SCRIPTED STUB ────────────────────────
// api/sv-witness.test.js answers its REST stub from a script: each URL matches
// a canned reply. That is right for "which refusal for which state" and it
// cannot answer either question above, because a scripted stub cannot tell you
// whether a WRITE LANDED -- it replays the same answer whether or not the
// mutation happened. Atomicity is entirely a question about what landed.
//
// So this kit keeps a real (tiny) table and applies PATCHes to it, including
// the `spent_at=is.null` compare-and-set, which is the one semantic the lock
// depends on. That is still not PostgREST and the arms say so.
//
// ── AN INTERRUPTION IS NOT AN ERROR RESPONSE ────────────────────────────────
// A 503 is the server answering. An interruption is the answer never arriving:
// the socket drops, the lambda is frozen, the process is killed. The two take
// different code paths -- one returns, one throws -- and only the first is
// usually tested. `interruptAfter(n)` throws, and `applyThenInterrupt(n)`
// applies the mutation server-side FIRST and then throws, which is the shape
// that actually loses data: the write landed and the caller will never know.

'use strict';

function clone(v) { return JSON.parse(JSON.stringify(v)); }

// A minimal PostgREST-shaped world with REAL rows.
//
//   tokens   an array of token rows, mutated by PATCH
//   policy   the witness policy row, or null for "could not read"
//
// opts.interruptAfter  throw on the Nth fetch call onwards (1-based), simulating
//                      a dropped connection or a killed process.
// opts.applyThenInterruptAfter  on that call, APPLY the mutation and then throw:
//                      the server did the work and the answer never arrived.
function restWorld(opts) {
  const o = opts || {};
  const state = {
    tokens: clone(o.tokens || []),
    policy: o.policy === undefined ? { require_two_person: false } : o.policy,
    calls: [],
    applied: [],
  };

  function matchTokenQuery(url) {
    const m = /token_hash=eq\.([^&]+)/.exec(url);
    const idm = /id=eq\.([^&]+)/.exec(url);
    if (idm) return state.tokens.filter((t) => String(t.id) === decodeURIComponent(idm[1]));
    if (m) return state.tokens.filter((t) => t.token_hash === decodeURIComponent(m[1]));
    return [];
  }

  global.fetch = async (url, init) => {
    const u = String(url);
    const method = (init && init.method) || 'GET';
    state.calls.push({ url: u, method });
    const n = state.calls.length;

    const interrupt = o.interruptAfter && n >= o.interruptAfter;
    const applyThen = o.applyThenInterruptAfter && n === o.applyThenInterruptAfter;

    if (interrupt && !applyThen) {
      const e = new Error('ECONNRESET: the connection dropped before an answer arrived');
      e.code = 'ECONNRESET';
      throw e;
    }

    // ── the policy table ──────────────────────────────────────────────────
    if (u.indexOf('witness_policy') !== -1) {
      if (state.policy === null) {
        return { ok: false, status: 503, json: async () => ({ message: 'unreachable' }) };
      }
      return { ok: true, status: 200, json: async () => [state.policy] };
    }

    // ── the token table ───────────────────────────────────────────────────
    if (u.indexOf('witness_tokens') !== -1) {
      if (method === 'PATCH') {
        const body = JSON.parse((init && init.body) || '{}');
        // THE COMPARE-AND-SET. `spent_at=is.null` in the URL means the update
        // must only apply to a token nobody has spent yet; the loser of a race
        // gets zero rows back. Modelled rather than mocked, because "did the
        // spend land" is the entire question this kit exists to answer.
        const casUnspent = u.indexOf('spent_at=is.null') !== -1;
        const rows = matchTokenQuery(u).filter((t) => (casUnspent ? !t.spent_at : true));
        rows.forEach((t) => { Object.assign(t, body); });
        if (rows.length) state.applied.push({ op: 'spend', ids: rows.map((r) => r.id) });
        if (applyThen) {
          const e = new Error('ECONNRESET: the spend was applied and the answer never arrived');
          e.code = 'ECONNRESET';
          throw e;
        }
        return { ok: true, status: 200, json: async () => clone(rows) };
      }
      if (method === 'POST') {
        const body = JSON.parse((init && init.body) || '{}');
        const row = Object.assign({ id: 'tok-row-' + (state.tokens.length + 1) }, body);
        state.tokens.push(row);
        state.applied.push({ op: 'issue', ids: [row.id] });
        if (applyThen) {
          const e = new Error('ECONNRESET: the token was issued and the answer never arrived');
          e.code = 'ECONNRESET';
          throw e;
        }
        return { ok: true, status: 200, json: async () => [clone(row)] };
      }
      return { ok: true, status: 200, json: async () => clone(matchTokenQuery(u)) };
    }

    return { ok: true, status: 200, json: async () => [] };
  };

  return state;
}

// Run one attempt and report WHAT HAPPENED rather than only what was returned.
// A thrown interruption is an outcome, not a test failure.
async function attempt(fn) {
  try {
    const refusal = await fn();
    return { outcome: refusal ? 'refused' : 'proceed', refusal: refusal || null };
  } catch (e) {
    return { outcome: 'interrupted', error: String((e && e.message) || e) };
  }
}

module.exports = { restWorld, attempt, clone };
