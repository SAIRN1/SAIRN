// tests/run_rate_limit_race_probe.js
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
  ok('D5 and it says the racy path is the one DEPLOYED, with the reason',
    /never been run/.test(normal.out), normal.out);
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

console.log('');
if (fail) {
  console.log('rate_limit_race_model: ' + fail + ' ARM(S) FAILED');
  process.exit(1);
}
console.log('rate_limit_race_model: all ' + pass + ' arms pass');
