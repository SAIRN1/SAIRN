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
    // Counts the attester-active lookups the lock makes. A harness that answers
    // a question nobody asked would hide the check being deleted; an arm can
    // assert this is non-zero to prove it is still being asked.
    employeeQueries: 0,
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

    // ── the employee table ────────────────────────────────────────────────
    // Item 101, 2026-09-14. requireWitness() now re-reads the attester's
    // active status at SPEND time, so this world has to be able to answer it.
    // `employees` defaults to "everyone named is active", because the arms in
    // this file are about INTERRUPTION and a revoked witness would make every
    // one of them refuse for an unrelated reason. Set it explicitly to test the
    // revoked case -- api/sv-witness.test.js section 5b does exactly that.
    //
    // THE DEFAULT IS THE PERMISSIVE ONE ON PURPOSE AND THAT IS A RISK WORTH
    // NAMING: a harness that silently answers "active" to a question the code
    // did not ask would hide the check being removed. The arm that protects
    // against it is the uninterrupted-transition one -- if the lock stopped
    // asking, `employeeQueries` below would be zero and that is asserted.
    if (u.indexOf('employee_auth') !== -1 || u.indexOf('_employees') !== -1) {
      state.employeeQueries += 1;
      const m = /employee_id=eq\.([^&]+)/.exec(u);
      const who = m ? decodeURIComponent(m[1]) : null;
      const revoked = o.revoked || [];
      if (o.employeeLookupFails) {
        return { ok: false, status: 500, json: async () => ({ message: 'employee lookup failed' }) };
      }
      if (who && revoked.indexOf(who) !== -1) {
        return { ok: true, status: 200, json: async () => [] };
      }
      return { ok: true, status: 200, json: async () => [{ employee_id: who }] };
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

// ── THE CLOCK SEAM: MOVE TIME, DO NOT RECOMPUTE AN OFFSET ─────────────────
// WHY THIS EXISTS, and it is the second thing an independent reviewer found
// about item 83. The first pass tested expiry by BACKDATING A ROW --
// `expires_at: new Date(Date.now() - 1000)`. That proves the comparison
// exists. It cannot prove the property that actually matters operationally:
// that a token which WAS valid when the lock issued it becomes refused once
// real time passes it.
//
// The gap is that the test and the code were doing the same arithmetic. The
// lock mints `Date.now() + TOKEN_TTL_MS` (api/sv-witness.js:261) and the old
// recovery arm MEASURED the remaining TTL against `Date.now()` -- so both ends
// came off the same computation and would AGREE WHILE BOTH WERE WRONG. If
// TOKEN_TTL_MS were zero, negative, or in the wrong unit, a
// measure-the-remaining-window arm still passes: it is checking the
// subtraction, not the behaviour. That is disciplines item 8's vacuum-failure
// case -- agreement is not corroboration when both ends come off the same bus.
//
// So this does not compute a different offset. It ADVANCES THE CLOCK THE LOCK
// READS and leaves the token row untouched, which makes the token's own
// `expires_at` -- whatever produced it -- the thing under test. The mechanism
// is structurally different from the assertion, which is what convention 6
// means by independence.
//
// Only Date.now is moved, and Date itself is left alone: the lock reads
// `new Date(row.expires_at).getTime()` to parse a STORED string, and a Date
// constructor that lied about parsing would break the parse rather than the
// comparison, testing the wrong thing again.
// IT MUST AWAIT, AND THE FIRST VERSION DID NOT -- caught by its own arms going
// red against a lock that is correct. A synchronous try/finally around an ASYNC
// fn restores Date.now the moment fn returns its PROMISE, which is before the
// lock has read the clock even once. So every clock-advanced arm ran against
// the real wall clock, the token was still inside its window, and the spend
// proceeded: three arms failed and would have been reported as a fail-safe
// defect in production code.
//
// That is worth keeping rather than quietly fixing. A seam that silently stops
// applying is the same shape as an anchor that stops matching -- and here it
// failed LOUDLY only because the arms assert a refusal. Written as
// "expect no findings" it would have gone green for ever while controlling
// nothing.
async function withClockAt(atMs, fn) {
  const realNow = Date.now;
  Date.now = function () { return atMs; };
  try {
    return await fn();
  } finally {
    Date.now = realNow;
  }
}

// Advance from a captured instant rather than from "now at call time", so a
// caller can pin T0 once and step forward from it deterministically. A test
// that re-read the clock between steps would reintroduce the shared-arithmetic
// problem through the back door.
async function withClockAdvanced(fromMs, deltaMs, fn) {
  return withClockAt(fromMs + deltaMs, fn);
}

module.exports = { restWorld, attempt, clone, withClockAt, withClockAdvanced };
