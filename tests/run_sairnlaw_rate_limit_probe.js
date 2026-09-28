// tests/run_sairnlaw_rate_limit_probe.js
// REQUIREMENT: the two SAIRNlaw rate limiters REFUSE rather than allow when
//   the window cannot be read, because the limit is a promise to somebody
//   else's server and a permissive answer from a call that did not complete is
//   a request we actually send
//
//
// Run:  node tests/run_sairnlaw_rate_limit_probe.js
//
// CONTROLS_FOR = ['_lib/wex.js', '_lib/intl-caselaw.js']
//
// ITEM 78's COUNT-THEN-INSERT RACE, SWEPT TO THE TWO RATE LIMITERS THAT NEVER
// GOT IT. Four limiters exist on this platform; the AI one and CourtListener
// were fixed with an advisory-lock RPC and these two were left reading the
// window in one HTTP call and inserting in another.
//
// ── THE ARM THAT MATTERS IS THE FAIL-OPEN ONE ──────────────────────────────
// Every fallback path here has to answer "I could not tell" as REFUSE, never as
// "go ahead". These limits are a promise to somebody else's server -- Cornell
// LII publishes `Crawl-delay: 10` -- so a permissive answer from a call that
// did not complete is a request we actually send. Section D drives every way
// the RPC can fail to answer and asserts the racy path took over, which still
// honours the window, rather than the wrapper returning not-limited.
//
// The RPC is stubbed. This proves the CLIENT's decisions; that Postgres really
// serialises pg_advisory_xact_lock is proved by the SQL file's own concurrency
// query and is not claimed here.

'use strict';
// THE DECLARATION EXISTED ONLY AS A COMMENT (fixed 2026-09-16). Line 10 carries
// `CONTROLS_FOR` in prose, and tools/checker_control_check.py strips comments
// before reading it -- deliberately, because counting prose as a declaration is
// the over-crediting failure that tool was built to end. So this file declared
// nothing and both its subjects scored as though no control existed. Its three
// sibling JS controls all carry BOTH forms: the comment for a reader, the const
// for the parser. This is the const.
const CONTROLS_FOR = ['_lib/wex.js', '_lib/intl-caselaw.js'];
const assert = require('assert');
const path = require('path');

const REPO = path.dirname(__dirname);
const WEX = require(path.join(REPO, 'api', '_lib', 'wex.js'));
const INTL = require(path.join(REPO, 'api', '_lib', 'intl-caselaw.js'));

let pass = 0, fail = 0;
function ok(name, cond, detail) {
  console.log('  ' + (cond ? 'PASS ' : 'FAIL ') + name +
              (cond ? '' : '\n        ' + String(detail).slice(0, 400)));
  if (cond) pass++; else fail++;
}

// A world where the RPC answers however the test says, and the RACY path's
// two calls (a GET for the window, a POST for the row) answer from `rows`.
function world(opts) {
  const o = opts || {};
  const calls = [];
  global.fetch = async (url, init) => {
    const u = String(url), m = (init && init.method) || 'GET';
    calls.push({ url: u, method: m, body: init && init.body });
    if (u.indexOf('/rpc/') !== -1) {
      if (o.rpcThrows) throw new Error('ECONNRESET');
      if (o.rpcStatus && o.rpcStatus !== 200) {
        return { ok: false, status: o.rpcStatus, json: async () => o.rpcBody || {} };
      }
      return { ok: true, status: 200, json: async () => o.rpcBody };
    }
    if (m === 'POST') return { ok: true, status: 201, json: async () => ({}) };
    if (o.racyStatus) {
      return { ok: false, status: o.racyStatus, json: async () => ([]) };
    }
    return { ok: true, status: 200, json: async () => (o.rows || []) };
  };
  return calls;
}

process.env.SUPABASE_URL = 'https://db.example.invalid';
process.env.SUPABASE_SERVICE_ROLE_KEY = 'service-key';

console.log('sairnlaw rate limiters -- the atomic path, and every way it can not answer');

// ── A. the atomic path answers, and says so ────────────────────────────────
console.log('\n--- A. the RPC answers ---');
(async () => {
  let calls = world({ rpcBody: { limited: false, prior_count: 0, max: 1 } });
  let g = await WEX.checkCrawlDelay();
  ok('A1 wex: under the limit proceeds', g.delayed === false, JSON.stringify(g));
  ok('A2 ...and reports racy:false, so which path answered is in the RESULT '
    + 'rather than inferred', g.racy === false, JSON.stringify(g));
  ok('A3 ...and it really used the RPC, not the two-call path',
    calls.filter((c) => c.url.indexOf('/rpc/') !== -1).length === 1
    && calls.length === 1, JSON.stringify(calls.map((c) => c.url)));

  calls = world({ rpcBody: { limited: true, prior_count: 1, max: 1 } });
  g = await WEX.checkCrawlDelay();
  ok('A4 wex: at the limit delays, and carries the retry-after',
    g.delayed === true && g.retryAfterSeconds === WEX.WEX_CRAWL_DELAY_SECONDS,
    JSON.stringify(g));
  ok('A5 ...with no second call: the RPC decided and recorded in one round trip',
    calls.length === 1, JSON.stringify(calls.map((c) => c.method + ' ' + c.url)));

  world({ rpcBody: { limited: false } });
  let l = await INTL.checkLimit('fcl_rate_limit_log', 60, 5);
  ok('A6 intl: under the limit proceeds, racy:false',
    l.limited === false && l.racy === false, JSON.stringify(l));
  world({ rpcBody: { limited: true } });
  l = await INTL.checkLimit('fcl_rate_limit_log', 60, 5);
  ok('A7 intl: at the limit is limited, and still reports max and window',
    l.limited === true && l.max === 5 && l.seconds === 60, JSON.stringify(l));

  // ── B. the RPC is passed what the caller asked for ──────────────────────
  console.log('\n--- B. the parameters reach the function ---');
  calls = world({ rpcBody: { limited: false } });
  await INTL.checkLimit('fcl_rate_limit_log', 60, 5);
  const body = JSON.parse(calls[0].body);
  ok('B1 the TABLE is passed, so one function serves every ledger',
    body.p_table === 'fcl_rate_limit_log', JSON.stringify(body));
  ok('B2 ...and the window and max are the CALLER\'s, not baked in',
    body.p_window_seconds === 60 && body.p_max === 5, JSON.stringify(body));
  calls = world({ rpcBody: { limited: false } });
  await WEX.checkCrawlDelay();
  const wbody = JSON.parse(calls[0].body);
  ok('B3 wex asks for max 1 over its published crawl-delay -- a DIFFERENT '
    + 'shape from an N-per-day cap, which is why the max is a parameter',
    wbody.p_max === 1
    && wbody.p_window_seconds === WEX.WEX_CRAWL_DELAY_SECONDS,
    JSON.stringify(wbody));

  // ── C. the fallback is reachable and still honours the window ───────────
  console.log('\n--- C. no RPC yet: exactly today\'s behaviour ---');
  calls = world({ rpcStatus: 404, rows: [] });
  g = await WEX.checkCrawlDelay();
  ok('C1 a 404 falls back to the two-call path', g.racy === true, JSON.stringify(g));
  ok('C2 ...and the fallback really ran: a GET for the window and a POST',
    calls.filter((c) => c.method === 'GET').length >= 1
    && calls.filter((c) => c.method === 'POST' && c.url.indexOf('/rpc/') === -1).length === 1,
    JSON.stringify(calls.map((c) => c.method + ' ' + c.url)));
  calls = world({ rpcStatus: 404, rows: [{ id: 1 }] });
  g = await WEX.checkCrawlDelay();
  ok('C3 ...and the fallback still DELAYS when the window is occupied',
    g.delayed === true && g.racy === true, JSON.stringify(g));

  // ── C4/C5: THE FALLBACK'S OWN READ FAILING (added 2026-09-27) ───────────
  // `opts.racyStatus` has existed in this harness since it was written and
  // NOTHING EVER PASSED IT. Found by tools/ghost_field_read_scan.py: `racyStatus`
  // is read in a gate and is not written, keyed or quoted anywhere in the repo.
  //
  // IT IS THE ONE CASE THIS FILE'S OWN STANDARD DEMANDS AND NEVER DROVE.
  // Section D covers every way the RPC can fail. This is the layer below: the
  // RPC is gone (404) AND the fallback's own GET for the window fails. The
  // header says "Every fallback path here has to answer 'I could not tell' as
  // REFUSE, never as go-ahead" -- and a fail-open here is a request actually
  // sent to somebody else's server in violation of a published crawl-delay,
  // which is the concrete harm the whole limiter exists to prevent.
  console.log('\n--- C4/C5. the RPC is gone AND the fallback read fails ---');
  //
  // WHAT IT ACTUALLY DOES, MEASURED: it THROWS. `checkCrawlDelayRacy` answers a
  // 404/400 with a structured `{delayed:true, notProvisioned:true}` -- because
  // "a migration has not been run" is actionable and "the network is flaky" is
  // not, which is its own comment -- and then answers every OTHER non-ok status
  // with `throw new Error('wex crawl-delay check failed: HTTP ' + status)`.
  //
  // THE SAFETY PROPERTY HOLDS END TO END and that was traced rather than
  // assumed: `wexLookup` does not catch it, and api/legal-reference.js's outer
  // catch turns it into 502 "Upstream connection error — try again" with the
  // error logged. So NO REQUEST REACHES CORNELL. Fail-closed, which is the one
  // thing that matters here.
  //
  // THE ARM THEREFORE ASSERTS "NEVER PROCEEDS", not "returns delayed:true" --
  // a throw is a refusal, and demanding a particular shape would fail a
  // correct implementation. The first version of this arm demanded
  // `r.delayed === true` and killed the probe with an uncaught rejection.
  //
  // FLAGGED, NOT FIXED HERE: the throw escapes the `{ok:false, code:...}`
  // vocabulary every other branch of api/_lib/wex.js maintains, so the caller
  // cannot tell a crawl-delay bookkeeping failure from any other upstream
  // error. Giving it a code is a behaviour change in a file this change does
  // not otherwise touch.
  for (const st of [500, 503, 403]) {
    world({ rpcStatus: 404, racyStatus: st, rows: [] });
    let proceeded = null, threw = null;
    try {
      const r = await WEX.checkCrawlDelay();
      proceeded = r.delayed === false;
    } catch (e) {
      threw = e && e.message;
    }
    ok('C4 fallback GET ' + st + ' -> NEVER proceeds. It refuses or throws; a '
      + '`delayed:false` here is a request actually sent to somebody else\'s '
      + 'server in breach of a published Crawl-delay',
      proceeded !== true,
      'proceeded=' + proceeded + ' threw=' + threw);
    ok('C4b ...and the refusal NAMES the status, so the log says which failure '
      + 'it was rather than "something went wrong"',
      threw === null || /HTTP ' + st + '|HTTP ' + st/.test(String(threw))
        || String(threw).indexOf(String(st)) !== -1,
      'threw=' + threw);
  }
  // THE PAIRED POSITIVE. Without it, C4 proves only that something always
  // delays once racyStatus is set.
  world({ rpcStatus: 404, rows: [] });
  const readable = await WEX.checkCrawlDelay();
  ok('C5 CONTROL: the same fallback with a READABLE empty window proceeds, so '
    + 'C4 is about the read failing and not about the fallback refusing always',
    readable.delayed === false, JSON.stringify(readable));

  // ── D. THE FAIL-OPEN ARMS. Could-not-tell is never "go ahead". ──────────
  console.log('\n--- D. every way the RPC can fail to answer ---');
  const cases = [
    ['the RPC throws', { rpcThrows: true, rows: [{ id: 1 }] }],
    ['the RPC 500s', { rpcStatus: 500, rows: [{ id: 1 }] }],
    ['the RPC 404s', { rpcStatus: 404, rows: [{ id: 1 }] }],
    ['the RPC answers an ALLOWLIST REFUSAL with no `limited` field',
     { rpcBody: { error: 'unknown ledger: pg_authid' }, rows: [{ id: 1 }] }],
    ['the RPC answers null', { rpcBody: null, rows: [{ id: 1 }] }],
  ];
  for (const [label, opts] of cases) {
    world(opts);
    const r = await WEX.checkCrawlDelay();
    ok('D  ' + label + ' -> the window is still honoured, NOT "go ahead"',
      r.delayed === true,
      'returned ' + JSON.stringify(r) + ' -- a permissive answer here is a '
      + 'request actually sent to somebody else\'s server');
  }
  // THE PAIRED POSITIVE, or D proves only that something always delays.
  world({ rpcThrows: true, rows: [] });
  const open = await WEX.checkCrawlDelay();
  ok('D6 CONTROL: the same failures with an EMPTY window still proceed -- the '
    + 'fallback is not a blanket refusal', open.delayed === false,
    JSON.stringify(open));

  // ── E. the SQL carries the preconditions the pattern needs ─────────────
  console.log('\n--- E. the pattern travelled with its preconditions ---');
  const sql = require('fs').readFileSync(
    path.join(REPO, 'sql', 'sairnlaw_rate_limit_consume_fn_2026-09-14.sql'), 'utf8');
  ok('E1 the table name is ALLOWLISTED, not just quoted -- quote_ident is safe '
    + 'against injection and would still let a caller consume any table',
    /p_table not in \('wex_rate_limit_log', 'fcl_rate_limit_log'\)/.test(sql), '');
  ok('E2 it takes the advisory lock PER LEDGER, so wex and fcl never block '
    + 'each other', /pg_advisory_xact_lock\(hashtext\('sairnlaw_rl:' \|\| p_table\)\)/.test(sql), '');
  ok('E3 the READ COMMITTED precondition travelled from the AI function rather '
    + 'than waiting to be rediscovered here',
    /current_setting\('transaction_isolation'\)/.test(sql)
    && /invalid_transaction_state/.test(sql), '');
  ok('E4 a refused call does NOT write a row -- recording it would extend the '
    + 'very crawl-delay window it was refused by',
    /NOT RECORDED WHEN REFUSED/.test(sql), '');
  ok('E5 ...and that difference from the AI limiter is stated, not silent',
    /differs from the AI limiter on/.test(sql.replace(/\n\s*--\s*/g, ' ')), '');
  ok('E6 the file carries a control for the allowlist REFUSING, not only for it '
    + 'permitting', /sairnlaw_rate_limit_consume\('pg_authid'/.test(sql), '');

  console.log('');
  if (fail) {
    console.log('sairnlaw_rate_limit: ' + fail + ' ARM(S) FAILED');
    process.exit(1);
  }
  console.log('sairnlaw_rate_limit: all ' + pass + ' arms pass');
})();
