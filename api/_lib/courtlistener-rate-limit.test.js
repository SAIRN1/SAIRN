// api/_lib/courtlistener-rate-limit.test.js
//
// Run:  node api/_lib/courtlistener-rate-limit.test.js
//
// Three defects, all in the same feature, each of which made the other two
// pointless:
//
//   1. checkAndLogRateLimit() counted and then inserted in separate HTTP
//      calls. N concurrent callers all read the same counts, all pass, all
//      insert. At a ceiling of 4/minute that takes two callers, not fifty.
//   2. All four token-gated functions called it and DISCARDED THE VERDICT.
//      The limiter computed {limited: true} and the next line called
//      CourtListener anyway. No caller in api/ read the return value either.
//   3. legal-citator.js turned a FAILED budget read into `budget = null`, and
//      `if (budget && ...)` then fell through to the upstream call -- an
//      unreachable counter meant "spend freely".
//
// The budget belongs to a third party, the token is shared by every SAIRNlaw
// firm, and the penalty is CourtListener throttling or revoking it for
// everyone. So unlike api/_lib/ai-rate-limit.js -- which fails OPEN on
// purpose, because a counting outage must not take down every AI feature --
// this one must fail CLOSED. A test asserts that difference, because the two
// files are similar enough to be copied.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const Module = require('module');

const ROOT = path.join(__dirname, '..', '..');
const SRC = path.join(__dirname, 'courtlistener.js');
const src = fs.readFileSync(SRC, 'utf8');

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
async function atest(name, fn) {
  try { await fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('--- ' + t + ' ---'); }

// ── Load the module with a fake fetch, so nothing leaves the machine ───────
function load(fetchImpl) {
  process.env.SUPABASE_URL = 'https://example.invalid';
  process.env.SUPABASE_SERVICE_ROLE_KEY = 'fake-service-role-for-tests';
  process.env.COURTLISTENER_API_TOKEN = 'fake-cl-token-for-tests';
  const prevFetch = global.fetch;
  global.fetch = fetchImpl;
  delete require.cache[require.resolve(SRC)];
  const mod = require(SRC);
  return { mod, restore: () => { global.fetch = prevFetch; } };
}

function jsonRes(status, body) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status: status,
    json: () => Promise.resolve(body),
    text: () => Promise.resolve(JSON.stringify(body)),
  });
}

(async function () {

// ---------------------------------------------------------------------------
section('the atomic path is used, and its verdict is the answer');

await atest('a permitted RPC result allows the call and consumes one unit', async () => {
  const calls = [];
  const { mod, restore } = load((url, opts) => {
    calls.push(String(url));
    if (String(url).indexOf('rpc/cl_rate_limit_consume') !== -1) {
      return jsonRes(200, { limited: false, minute: 1, hour: 3, day: 9 });
    }
    return jsonRes(200, {});
  });
  try {
    const v = await mod.checkAndLogRateLimit();
    assert.deepStrictEqual(v, { limited: false });
    assert.strictEqual(calls.filter((c) => c.indexOf('rpc/') !== -1).length, 1,
      'the RPC was not called exactly once');
    assert.strictEqual(calls.filter((c) => c.indexOf('cl_rate_limit_log?') !== -1).length, 0,
      'the racy count query ran even though the RPC answered');
  } finally { restore(); }
});

await atest('a limited RPC result reports WHICH window, not just "no"', async () => {
  const { mod, restore } = load(() => jsonRes(200, { limited: true, window: 'minute', max: 4, prior_count: 4 }));
  try {
    const v = await mod.checkAndLogRateLimit();
    assert.strictEqual(v.limited, true);
    assert.strictEqual(v.window, 'minute');
    assert.strictEqual(v.max, 4);
  } finally { restore(); }
});

// ---------------------------------------------------------------------------
section('IT FAILS CLOSED -- the opposite of ai-rate-limit.js, on purpose');

await atest('an RPC 500 THROWS rather than allowing the call', async () => {
  const { mod, restore } = load(() => jsonRes(500, { message: 'boom' }));
  try {
    await assert.rejects(() => mod.checkAndLogRateLimit(), /HTTP 500/);
  } finally { restore(); }
});

await atest('an unusable RPC body THROWS rather than being read as "fine"', async () => {
  const { mod, restore } = load(() => jsonRes(200, { error: 'app_id required' }));
  try {
    await assert.rejects(() => mod.checkAndLogRateLimit(), /unusable body/);
  } finally { restore(); }
});

await atest('a failed COUNT on the legacy path still throws', async () => {
  const { mod, restore } = load((url) => {
    if (String(url).indexOf('rpc/') !== -1) return jsonRes(404, {});   // not migrated
    return jsonRes(503, {});                                          // count fails
  });
  try {
    await assert.rejects(() => mod.checkAndLogRateLimit(), /rate limit check failed/);
  } finally { restore(); }
});

await atest('ONLY a 404 falls back -- a 403 must not look like "not migrated"', async () => {
  // A permission error and a missing function are entirely different states.
  // Treating both as "fall back" would silently reinstate the racy path the
  // day someone narrows the EXECUTE grant.
  const { mod, restore } = load((url) => {
    if (String(url).indexOf('rpc/') !== -1) return jsonRes(403, { message: 'permission denied' });
    throw new Error('the legacy path must not have been reached');
  });
  try {
    await assert.rejects(() => mod.checkAndLogRateLimit(), /HTTP 403/);
  } finally { restore(); }
});

await atest('the legacy path runs on a 404, and says so out loud', async () => {
  const warned = [];
  const prevWarn = console.warn;
  console.warn = (...a) => warned.push(a.join(' '));
  const { mod, restore } = load((url) => {
    if (String(url).indexOf('rpc/') !== -1) return jsonRes(404, {});
    if (String(url).indexOf('cl_rate_limit_log?') !== -1) return jsonRes(200, []);
    return jsonRes(200, {});
  });
  try {
    const v = await mod.checkAndLogRateLimit();
    assert.deepStrictEqual(v, { limited: false });
    assert.ok(warned.some((w) => /RACY/.test(w)),
      'the racy fallback ran silently: ' + JSON.stringify(warned));
    assert.ok(warned.some((w) => /cl_rate_limit_consume_fn/.test(w)),
      'the warning does not name the migration to run');
  } finally { restore(); console.warn = prevWarn; }
});

// ---------------------------------------------------------------------------
section('THE VERDICT IS ACTED ON -- it used to be discarded');

await atest('a token-gated call REFUSES when limited, with status 429', async () => {
  let upstream = 0;
  const { mod, restore } = load((url) => {
    if (String(url).indexOf('rpc/') !== -1) {
      return jsonRes(200, { limited: true, window: 'minute', max: 4 });
    }
    upstream++;
    return jsonRes(200, { results: [] });
  });
  try {
    await assert.rejects(() => mod.clCitingOpinions(123), (e) => {
      assert.strictEqual(e.status, 429, 'the refusal does not carry status 429');
      assert.strictEqual(e.code, 'CL_RATE_LIMITED');
      assert.match(e.message, /minute/);
      return true;
    });
    assert.strictEqual(upstream, 0,
      'CourtListener was called anyway -- the verdict is still being discarded');
  } finally { restore(); }
});

await atest('...and all four token-gated functions do it, not just one', async () => {
  for (const [fn, arg] of [['clCitingOpinions', 1], ['clOpinionText', 1],
                           ['clCluster', 1], ['clCitationLookup', 'x']]) {
    let upstream = 0;
    const { mod, restore } = load((url) => {
      if (String(url).indexOf('rpc/') !== -1) return jsonRes(200, { limited: true, window: 'day', max: 115 });
      upstream++;
      return jsonRes(200, {});
    });
    try {
      await assert.rejects(() => mod[fn](arg), (e) => e.status === 429);
      assert.strictEqual(upstream, 0, fn + ' called CourtListener while limited');
    } finally { restore(); }
  }
});

await atest('a PERMITTED call still reaches CourtListener', async () => {
  // The mirror of the arm above. A limiter that refuses everything would pass
  // every deny test and be just as broken.
  let upstream = 0;
  const { mod, restore } = load((url) => {
    if (String(url).indexOf('rpc/') !== -1) return jsonRes(200, { limited: false, minute: 0 });
    upstream++;
    return jsonRes(200, { results: ['ok'] });
  });
  try {
    const data = await mod.clCitingOpinions(123);
    assert.deepStrictEqual(data, { results: ['ok'] });
    assert.strictEqual(upstream, 1);
  } finally { restore(); }
});

// ---------------------------------------------------------------------------
section('source-level guards on the decisions that have no runtime signal');

test('no token-gated function discards the verdict again', () => {
  const code = src.replace(/\/\/[^\n]*/g, '');
  const bare = code.match(/^\s*await checkAndLogRateLimit\(\);\s*$/gm) || [];
  assert.deepStrictEqual(bare, [],
    'a call site is back to discarding the rate-limit verdict');
});

test('the SQL function writes a row ONLY when the call is permitted', () => {
  // The AI limiter inserts unconditionally so observe-mode data reflects real
  // demand. Doing that here would consume budget for a refused call that never
  // reached CourtListener, and the limiter would over-tighten under load.
  const sql = fs.readFileSync(
    path.join(ROOT, 'sql', 'cl_rate_limit_consume_fn_2026-09-04.sql'), 'utf8')
    .replace(/--[^\n]*/g, '');
  const iInsert = sql.indexOf('insert into public.cl_rate_limit_log');
  const iLastReturn = sql.lastIndexOf("'limited', true");
  assert.ok(iInsert > 0 && iLastReturn > 0, 'could not locate both points');
  assert.ok(iLastReturn < iInsert,
    'the insert is not after every limited-return -- a refused call would consume budget');
});

test('all three windows are counted inside the same lock', () => {
  const sql = fs.readFileSync(
    path.join(ROOT, 'sql', 'cl_rate_limit_consume_fn_2026-09-04.sql'), 'utf8')
    .replace(/--[^\n]*/g, '');
  const iLock = sql.indexOf('pg_advisory_xact_lock');
  const counts = [...sql.matchAll(/select count\(\*\) into/g)].map((m) => m.index);
  assert.strictEqual(counts.length, 3, 'expected three window counts, found ' + counts.length);
  counts.forEach((i) => assert.ok(i > iLock, 'a count happens before the lock is taken'));
  assert.ok(sql.indexOf('insert into public.cl_rate_limit_log') > iLock,
    'the insert happens before the lock is taken');
});

test('the lock key is ONE constant, not per-tenant', () => {
  // One token means one budget means one lock. A per-firm key would let two
  // firms pass the same window at once and reintroduce the bug.
  const sql = fs.readFileSync(
    path.join(ROOT, 'sql', 'cl_rate_limit_consume_fn_2026-09-04.sql'), 'utf8');
  assert.match(sql, /pg_advisory_xact_lock\(hashtext\('cl_rate_limit:shared'\)\)/);
});

test('legal-citator no longer treats an unreadable budget as room to spend', () => {
  const cit = fs.readFileSync(path.join(ROOT, 'api', 'legal-citator.js'), 'utf8');
  const code = cit.replace(/\/\/[^\n]*/g, '');
  assert.ok(!/catch \(e\) \{ budget = null; \}/.test(code),
    'the fail-open catch is back');
  assert.match(code, /budgetReadFailed/,
    'a failed budget read is not distinguished from a healthy one');
  const iFlag = code.indexOf('if (budgetReadFailed)');
  const iSpend = code.indexOf('cl.clCitationLookup');
  assert.ok(iFlag > 0 && iFlag < iSpend,
    'the failure branch is not checked before the upstream call');
});

test('the two limiters disagree about failing open, and the file says why', () => {
  // ai-rate-limit.js allows on failure; this one refuses. The comment is the
  // only thing stopping a future reader from "harmonising" them.
  const ai = fs.readFileSync(path.join(ROOT, 'api', '_lib', 'ai-rate-limit.js'), 'utf8');
  assert.match(ai, /FAILS OPEN, ON PURPOSE/,
    'ai-rate-limit.js no longer documents its fail-open choice');
  assert.match(src, /WHY THIS FAILS CLOSED/,
    'courtlistener.js no longer documents that it is the opposite');
});

console.log('\n' + (fail === 0
  ? 'ALL ' + pass + ' COURTLISTENER RATE-LIMIT ASSERTIONS PASS'
  : pass + ' passed, ' + fail + ' FAILED'));
process.exit(fail === 0 ? 0 : 1);

})();
