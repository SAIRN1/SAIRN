// tests/run_rate_limit_race_probe.js
// REQUIREMENT: the race model violates the cap when requests overlap AND holds
//   when only one is in flight -- either half alone is satisfied by a model
//   that always returns the same verdict -- and its exhaustive enumeration is
//   checked against independently computed schedule counts
//
//
// Run:  node tests/run_rate_limit_race_probe.js
//
// The control pair for tools/rate_limit_race_model.js -- item 78, second target.
//
// CONTROLS_FOR = ['rate_limit_race_model.js']
//
// A MODEL THAT ALWAYS REPORTS A VIOLATION IS NOT A MODEL, IT IS A SLOGAN. The
// arms below are built around that: the racy path must violate the cap when
// requests overlap AND must NOT violate it when only one request is in flight,
// and the locked path must hold in both. Either half alone is satisfied by
// something useless -- one that always says "violated" passes the first, one
// that always says "holds" passes the second.
//
// THE ENUMERATION IS ALSO CHECKED AGAINST ITS OWN ARITHMETIC. "Exhaustive" is a
// claim, and a recursion that silently stopped early would still print a
// confident worst case. The schedule counts below are computed independently --
// (2n)!/2^n for the racy path, n! for the locked one -- so a truncated walk
// fails rather than reporting a smaller worst case as good news.

'use strict';
const assert = require('assert');
const path = require('path');
const { execFileSync } = require('child_process');

const CONTROLS_FOR = ['rate_limit_race_model.js'];
const REPO = path.dirname(__dirname);
const M = require(path.join(REPO, 'tools', 'rate_limit_race_model.js'));

let pass = 0, fail = 0;
function ok(name, cond, detail) {
  console.log('  ' + (cond ? 'PASS ' : 'FAIL ') + name +
              (cond ? '' : '\n        ' + String(detail).slice(0, 500)));
  if (cond) pass++; else fail++;
}
const fact = (n) => (n <= 1 ? 1 : n * fact(n - 1));

console.log('rate_limit_race_model -- the control pair');

// ── A. the violation, and the pair that stops it being a slogan ───────────
console.log('\n--- A. the racy path ---');
{
  const r = M.enumerateRacy(3, 2);
  ok('A1 three requests against a limit of two records THREE', r.worst === 3, 'worst=' + r.worst);
  ok('A2 and it EXHIBITS the schedule rather than asserting one exists',
    Array.isArray(r.witness) && r.witness.length === 6, JSON.stringify(r.witness));
  ok('A3 the witness is well formed -- every request reads before it decides', (() => {
    const seenRead = {};
    for (const s of r.witness) {
      const m = /^([RWX])(\d+)/.exec(s);
      if (!m) return false;
      if (m[1] === 'R') seenRead[m[2]] = true;
      else if (!seenRead[m[2]]) return false;
    }
    return true;
  })(), JSON.stringify(r.witness));
  ok('A4 THE PAIR: with ONE request in flight the cap is NOT violated',
    M.enumerateRacy(1, 2).worst <= 2, 'a single request overshot');
  ok('A5 ...and two requests at a limit of two do not overshoot either -- the '
    + 'race needs a request to read BEFORE another writes',
    M.enumerateRacy(2, 2).worst <= 2, 'worst=' + M.enumerateRacy(2, 2).worst);
  ok('A6 but two requests at a limit of ONE do',
    M.enumerateRacy(2, 1).worst === 2, 'worst=' + M.enumerateRacy(2, 1).worst);
}

// ── B. the locked path holds everywhere ───────────────────────────────────
console.log('\n--- B. the locked path ---');
{
  let bad = null;
  for (let n = 1; n <= 5 && !bad; n++) {
    for (let lim = 1; lim <= 4 && !bad; lim++) {
      const w = M.enumerateLocked(n, lim).worst;
      if (w > lim) bad = 'n=' + n + ' limit=' + lim + ' worst=' + w;
    }
  }
  ok('B1 the cap holds in EVERY schedule, across twenty (n, limit) pairs',
    bad === null, bad);
  ok('B2 and it still records up to the limit -- it is a cap, not a block',
    M.enumerateLocked(5, 3).worst === 3, 'worst=' + M.enumerateLocked(5, 3).worst);
}

// ── C. "exhaustive" is checked against arithmetic, not trusted ────────────
console.log('\n--- C. the enumeration really is exhaustive ---');
{
  // Racy: 2n steps, each request's write after its read -> (2n)! / 2^n.
  for (const n of [2, 3, 4]) {
    const expect = fact(2 * n) / Math.pow(2, n);
    ok('C' + n + ' n=' + n + ' enumerates ' + expect + ' schedules',
      M.enumerateRacy(n, 2).schedules === expect,
      'got ' + M.enumerateRacy(n, 2).schedules + ', expected ' + expect);
  }
  ok('C5 locked enumerates n! orderings', M.enumerateLocked(4, 2).schedules === fact(4),
    'got ' + M.enumerateLocked(4, 2).schedules);
}

// ── D. the tool refuses a bound it cannot honour ──────────────────────────
console.log('\n--- D. the stated bound ---');
{
  const run = (args) => {
    try {
      return { code: 0, out: execFileSync(process.execPath,
        [path.join(REPO, 'tools', 'rate_limit_race_model.js')].concat(args), { encoding: 'utf8' }) };
    } catch (e) { return { code: e.status, out: (e.stdout || '') + (e.stderr || '') }; }
  };
  const tooBig = run(['--requests', '9']);
  ok('D1 it refuses a request count past its stated bound', tooBig.code === 2, 'rc=' + tooBig.code);
  ok('D2 and says why a bound nobody states makes "exhaustive" a sampled claim',
    /sampled/.test(tooBig.out), tooBig.out);
  const normal = run([]);
  ok('D3 the default run exits 0 -- model and spec agree', normal.code === 0, normal.out);
  ok('D4 it names the spec it is modelling',
    /docs\/spec\/RateLimitConsume\.tla/.test(normal.out), normal.out);
  // D5 USED TO ASSERT THE OPPOSITE, and it was holding an overclaim in place.
  // It required the output to say the RPC "has never been run" -- a claim
  // sourced from db/schema_snapshot.json, which carries TABLES ONLY and has
  // never held a function. A zero there is NOT CAPTURED, not NOT RUN. The arm
  // now requires the tool to DECLINE to say which path is deployed, because
  // from a clone with no service-role key it genuinely cannot know.
  ok('D5 it refuses to claim which path is deployed, and says why',
    /not knowable from this repo/.test(normal.out)
    && /Read the mode the endpoint returns/.test(normal.out), normal.out);
  ok('D5b ...and no longer asserts the RPC was never run',
    !/never been run/.test(normal.out),
    'the unsupportable claim is back in the output');
  ok('D6 it distinguishes racy from unbounded -- a different claim',
    /Racy is not the same as unbounded/.test(normal.out), normal.out);
}

// ── E. the model still describes the code it claims to ────────────────────
console.log('\n--- E. the model and the code have not drifted ---');
{
  const src = require('fs').readFileSync(
    path.join(REPO, 'api', '_lib', 'ai-rate-limit.js'), 'utf8');
  ok('E1 the fallback is still described as racy in the code itself',
    /observe-racy|enforce-racy/.test(src), 'the mode strings are gone');
  ok('E2 the atomic RPC is still the named fix',
    /sairn_ai_rate_limit_consume/.test(src), 'the RPC name moved');
  ok('E3 and the code still warns against enforcing while the fallback is live',
    /DO NOT switch SAIRN_AI_RATE_LIMIT_MODE=enforce/.test(src),
    'the warning is gone -- the model is describing a system that changed');
}

// ── F. the precondition the locked model was silently resting on ──────────
// enumerateLocked() collapses each request into ONE step because "the lock
// means no other request can observe the count in between". That is true of
// the write and true of the read ONLY under read committed. F exists so the
// assumption is demonstrated rather than assumed -- and so that an enumerator
// which quietly stopped demonstrating it fails loudly instead of looking like
// a proof.
console.log('\n--- F. read committed is load-bearing, and now says so ---');
{
  const stale = M.enumerateLockedStaleSnapshot(3, 2);
  ok('F1 a snapshot taken before the lock BREAKS the cap',
    stale.worst > 2, 'worst=' + stale.worst + ' -- this enumerator is meant to violate');
  ok('F2 ...and it exhibits the schedule rather than asserting one exists',
    Array.isArray(stale.witness) && stale.witness.length > 0, JSON.stringify(stale));
  ok('F3 ...in which the LOCK is acquired on every run step -- the lock is not '
    + 'what failed',
    stale.witness.filter((s) => /^L\d/.test(s)).length === 3,
    JSON.stringify(stale.witness));
  ok('F4 ...and two different requests count the SAME prior value',
    (() => {
      const counts = stale.witness.filter((s) => /^L\d/.test(s))
        .map((s) => (s.match(/counts (\d+)/) || [])[1]);
      return new Set(counts).size < counts.length;
    })(), JSON.stringify(stale.witness));

  // THE PAIRED POSITIVE. A model that violated no matter what would pass F1
  // and prove nothing -- the same enumerator with the snapshot taken AT the
  // lock is enumerateLocked(), and that one must hold.
  ok('F5 the same requests through the fresh-snapshot model do NOT break it',
    M.enumerateLocked(3, 2).worst <= 2, 'the locked path stopped holding');

  ok('F6 one request cannot race itself, under either model',
    M.enumerateLockedStaleSnapshot(1, 2).worst <= 2
    && M.enumerateRacy(1, 2).worst <= 2, 'a single request violated the cap');

  const out = execFileSync(process.execPath,
    [path.join(REPO, 'tools', 'rate_limit_race_model.js')], { encoding: 'utf8' });
  ok('F7 the tool reports the stale-snapshot result rather than hiding it',
    /SNAPSHOT TAKEN BEFORE THE LOCK/.test(out), out.slice(0, 400));
  ok('F8 ...and says the lock is working throughout that trace',
    /LOCK IS WORKING IN EVERY STEP/.test(out), out.slice(-800));

  const sql = require('fs').readFileSync(
    path.join(REPO, 'sql', 'sairn_ai_rate_limit_consume_fn.sql'), 'utf8');
  ok('F9 the SQL function REFUSES outside read committed rather than assuming it',
    /current_setting\('transaction_isolation'\)/.test(sql)
    && /raise exception/.test(sql), 'the guard is not in the function');
  ok('F10 ...and raises rather than returning an error object a caller would read '
    + 'as an answer',
    !/return jsonb_build_object\('error', 'transaction/.test(sql)
    && /invalid_transaction_state/.test(sql), 'the refusal became a return value');
  ok('F11 the file tells the operator how to watch the guard REFUSE',
    /set transaction isolation level repeatable read/.test(sql),
    'there is no way to see this guard fire, so nobody will know if it stops');

  const tla = require('fs').readFileSync(
    path.join(REPO, 'docs', 'spec', 'RateLimitConsume.tla'), 'utf8');
  ok('F12 the spec carries the stale-snapshot behaviour too, not just the model',
    /StaleSnapshotSpec\s*==/.test(tla) && /StaleSnapshotRun\(r\)\s*==/.test(tla),
    'the spec and the model have drifted apart again');
}

console.log('');
if (fail) {
  console.log('rate_limit_race_model: ' + fail + ' ARM(S) FAILED');
  process.exit(1);
}
console.log('rate_limit_race_model: all ' + pass + ' arms pass');
