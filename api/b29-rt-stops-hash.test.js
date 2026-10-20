// api/b29-rt-stops-hash.test.js
//
// Run:  node api/b29-rt-stops-hash.test.js
//
// ── THE REQUIREMENT ─────────────────────────────────────────────────────────
// A stop belongs to a route, so the tenant a stop is filed under is a fact
// about the ROUTE and never a field the caller gets to state.
// `rt_stops.license_hash` must be derived SERVER-SIDE from the route row, and
// a client-supplied value must be impossible to land -- refused or overwritten,
// never honoured.
//
// This matters because cc's composite foreign key
// (sql/rt_stops_license_hash_composite_fk.sql) binds a stop to
// `(route_id, license_hash)` of its route. A mismatch the API allowed through
// would either be refused by that FK with an opaque error, or -- before the FK
// is applied -- land a stop under the wrong tenant. NO SQL IS RUN HERE: cc owns
// the migration, and this suite proves the API half holds with or without it.
//
// ── WHAT WAS ALREADY TRUE, AND WHY THAT IS NOT THE SAME AS PROVEN ──────────
// The insert has always written an EXPLICIT field list, so a `license_hash`
// inside a client stop object was never copied -- there is no spread for it to
// ride in on. But the value came from `licHash`, the LICENCE KEY, not from the
// route row. Those are the same number on every well-formed request and they
// are not the same FACT, and the gap between "the same today" and "the same by
// construction" is where a tenancy bug lives. b29 closed that and T3 is the arm
// that could not exist before.
//
// No database is touched. The real dispatcher runs against a recorded
// PostgREST stand-in, and every arm reads THE BODY THAT WAS POSTED rather than
// the handler's reply -- a 200 says the request was accepted, not what was
// written, and this suite is about what was written.
//
// Exit: 0 all arms passed · 1 an arm FAILED

'use strict';

process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET
  || ['b29', 'rt', 'stops', 'fixture'].join('-');
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://test.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'test-key';

const fs = require('fs');
const path = require('path');
const { signSessionToken } = require('./_lib/auth');

const HASH = 'b29-rt-hash';
const KEY = 'KEY-FOR-' + HASH;
const FOREIGN = 'SOMEBODY-ELSES-LICENCE-HASH';

let pass = 0, fail = 0;
const failed = [];
function ok(l) { pass++; console.log('  ok    ' + l); }
function bad(l, why) {
  fail++; failed.push(l.split('.')[0]);
  console.log('  FAIL  ' + l);
  if (why) console.log('        ' + String(why).slice(0, 700));
}
function is(cond, label, detail) { if (cond) ok(label); else bad(label, detail); }
function section(t) { console.log('\n' + t); }

function mockRes() {
  const res = { statusCode: null, body: null };
  res.status = function (c) { res.statusCode = c; return res; };
  res.json = function (b) { res.body = b; return res; };
  return res;
}
function eCode(res) { return (res.body && res.body.error && res.body.error.code) || ''; }
function eMsg(res) { return (res.body && res.body.error && res.body.error.message) || ''; }

// `opts.routeHash` is the license_hash the ROUTE ROW comes back carrying. It
// defaults to the licence's own, which is the only thing a correct PostgREST
// can return given an on_conflict key that includes license_hash -- so T3 has
// to force it, and forcing it is the point: the refusal must exist before the
// condition that triggers it ever does.
function pgMock(calls, opts) {
  opts = opts || {};
  const routeHash = Object.prototype.hasOwnProperty.call(opts, 'routeHash')
    ? opts.routeHash : HASH;
  return async function (url, init) {
    const u = String(url);
    const method = (init && init.method) || 'GET';
    let parsed = null;
    if (init && init.body) { try { parsed = JSON.parse(init.body); } catch (e) { parsed = null; } }
    calls.push({ url: u, method: method, body: parsed });
    if (/_employee_auth/.test(u)) {
      const m = u.match(/employee_id=eq\.([^&]+)/);
      return { ok: true, status: 200, json: async () => [
        { license_hash: HASH, employee_id: m ? decodeURIComponent(m[1]) : 'emp-1',
          role: 'owner', active: true }] };
    }
    if (/rt_routes/.test(u) && method === 'POST') {
      return { ok: true, status: 200, json: async () => [
        { id: 'ROUTE-1', license_hash: routeHash, app_id: 'stonedesk',
          assignee_id: 'EMP-1', route_date: '2031-01-02' }] };
    }
    if (/rt_stops/.test(u) && method === 'POST') {
      return { ok: true, status: 200,
               json: async () => (Array.isArray(parsed) ? parsed : [parsed]) };
    }
    if (/rt_routes/.test(u)) {
      return { ok: true, status: 200, json: async () => [
        { id: 'ROUTE-1', license_hash: routeHash }] };
    }
    return { ok: true, status: 200, json: async () => [] };
  };
}

function loadHandler(fetchImpl) {
  delete require.cache[require.resolve('./_lib/license')];
  require.cache[require.resolve('./_lib/license')] = {
    exports: {
      validateLicenseKey: async () => ({
        valid: true, active: true, license_hash: HASH,
        trial_ends_at: null, stripe_subscription_id: null, app_id: 'stonedesk' })
    }
  };
  global.fetch = fetchImpl;
  delete require.cache[require.resolve('./sd-data.js')];
  return require('./sd-data.js');
}

async function upsert(payload, opts) {
  const calls = [];
  const h = loadHandler(pgMock(calls, opts));
  const res = mockRes();
  await h({
    method: 'POST',
    headers: {
      authorization: 'Bearer ' + KEY,
      'x-sd-auth': signSessionToken({
        app: 'stonedesk', employee_id: 'emp-1', role: 'owner',
        license_hash: HASH })
    },
    body: { action: 'upsert', resource: 'rt_routes', payload: payload }
  }, res);
  return { res: res, calls: calls };
}

function key(over) {
  return Object.assign({
    app_id: 'stonedesk', assignee_id: 'EMP-1', route_date: '2031-01-02',
    stops: [{ address: '1 Probe Way' }, { address: '2 Probe Way' }]
  }, over || {});
}

// The rows that were actually POSTed to rt_stops, which is the only evidence
// about what was WRITTEN. A 200 says the request was accepted.
function insertedStops(calls) {
  const c = calls.filter((x) => /rt_stops/.test(x.url) && x.method === 'POST');
  if (!c.length) return null;
  const b = c[c.length - 1].body;
  return Array.isArray(b) ? b : [b];
}

(async function main() {
  section('T. rt_stops.license_hash IS THE ROUTE\'S, NEVER THE CALLER\'S');

  // T1. A client license_hash inside a STOP. The insert writes an explicit
  // field list, so this is dropped -- asserted on the posted body rather than
  // trusted, because "there is no spread" is a fact about today's source.
  {
    const { res, calls } = await upsert(key({
      stops: [{ address: '1 Probe Way', license_hash: FOREIGN },
              { address: '2 Probe Way', license_hash: FOREIGN }]
    }));
    const rows = insertedStops(calls);
    is(res.statusCode === 200 && rows && rows.length === 2
       && rows.every((r) => r.license_hash === HASH),
       'T1. a `license_hash` inside each STOP is OVERWRITTEN with the route\'s '
       + '-- the caller\'s value never lands',
       res.statusCode + ' ' + JSON.stringify(rows).slice(0, 200));
  }

  // T2. A client license_hash at the TOP of the payload, which is the likelier
  // mistake because that is where app_id and assignee_id legitimately live.
  {
    const { res, calls } = await upsert(key({ license_hash: FOREIGN }));
    const rows = insertedStops(calls);
    const routePost = calls.find((c) => /rt_routes/.test(c.url) && c.method === 'POST');
    is(res.statusCode === 200 && rows
       && rows.every((r) => r.license_hash === HASH)
       && routePost && routePost.body.license_hash === HASH,
       'T2. a top-level `license_hash` is ignored by BOTH writes -- the route '
       + 'upsert and the stop insert',
       res.statusCode + ' route=' + JSON.stringify(routePost && routePost.body)
         .slice(0, 120) + ' stops=' + JSON.stringify(rows).slice(0, 120));
  }

  // T3. THE ARM THAT COULD NOT EXIST BEFORE b29. The route row comes back
  // under a DIFFERENT licence. Before b29 the stops were filed under `licHash`
  // regardless, so a route belonging to someone else would have acquired stops
  // under this caller's tenant; now the request is refused and NOTHING is
  // written. Unreachable through a correct PostgREST -- which is precisely why
  // it must not be a silent fallback.
  {
    const { res, calls } = await upsert(key(), { routeHash: FOREIGN });
    const rows = insertedStops(calls);
    const deletes = calls.filter((c) => c.method === 'DELETE');
    is(res.statusCode === 409 && eCode(res) === 'ROUTE_TENANCY_MISMATCH'
       && rows === null && deletes.length === 0,
       'T3. a route row under ANOTHER licence -> 409 ROUTE_TENANCY_MISMATCH, '
       + 'with no stop insert AND no stop delete',
       res.statusCode + ' ' + eCode(res) + ' inserts='
         + JSON.stringify(rows) + ' deletes=' + deletes.length);
  }

  // T4. THE CONTROL. Without it T1-T3 prove a lockout rather than a rule.
  {
    const { res, calls } = await upsert(key());
    const rows = insertedStops(calls);
    is(res.statusCode === 200 && rows && rows.length === 2
       && rows[0].seq === 1 && rows[1].seq === 2
       && rows.every((r) => r.license_hash === HASH && r.route_id === 'ROUTE-1'),
       'T4. CONTROL: an ordinary upsert writes both stops, sequenced, under the '
       + 'route\'s id and hash',
       res.statusCode + ' ' + JSON.stringify(rows).slice(0, 220));
  }

  // T5. AND THE DELETE IS SCOPED BY THE ROUTE'S HASH TOO. The stop set is
  // REPLACED, so the delete runs before the insert; a delete scoped by the
  // caller's licence while the insert used the route's would be a split-brain
  // the arms above could not see.
  {
    const { calls } = await upsert(key());
    const del = calls.find((c) => c.method === 'DELETE' && /rt_stops/.test(c.url));
    is(del && /route_id=eq\.ROUTE-1/.test(del.url)
       && new RegExp('license_hash=eq\\.' + HASH).test(del.url),
       'T5. the REPLACE delete is bounded by BOTH the route id and the route\'s '
       + 'own hash',
       del ? del.url : '(no delete issued)');
  }

  section('S. THE STRUCTURAL ARM -- the value cannot come from the caller');

  // S1. THE SOURCE, because T1-T5 are about behaviour and a future edit could
  // reintroduce a spread that happens to pass them (a stop object whose only
  // extra key is one the explicit list also sets). This asserts the shape:
  // the inserted object sets `license_hash: routeHash` and the map callback
  // does not spread `s`.
  {
    const src = fs.readFileSync(path.join(__dirname, 'sd-data.js'), 'utf8');
    const i = src.indexOf('const toInsert = p.stops.map(');
    // ── BOUNDED BY THE STRUCTURE, NOT BY A CHARACTER COUNT ───────────────
    // This was a slice of six hundred characters from the anchor, and the
    // push gate refused it -- api/b16-slice-window-check.test.js arm S1, "NO
    // NEW fixed-width source window in an api/ test suite". THE DETECTOR
    // READS RAW SOURCE, so the old form is deliberately NOT quoted here: a
    // comment quoting it re-trips the arm, which is this clone's own
    // recorded lesson. The refusal is right: a window measured in characters
    // stops covering what it names the moment a comment is added inside it,
    // and then S1 here reports a clean field list because it read half of one.
    // Scanned to the terminator that closes the map call instead, so the
    // window is whatever the structure is.
    const term = i === -1 ? -1 : src.indexOf('}));', i);
    const block = (i === -1 || term === -1) ? '' : src.slice(i, term + 4);
    is(i !== -1
       && /license_hash: routeHash/.test(block)
       && !/\.\.\.s\b/.test(block)
       && !/Object\.assign\(\{\}, s\b/.test(block),
       'S1. the stop insert sets `license_hash: routeHash` and does NOT spread '
       + 'the client stop object',
       (i === -1 || term === -1)
         ? 'the toInsert map, or its closing `}));`, was not found -- re-aim '
           + 'this arm rather than widening it'
         : block.slice(0, 240));
  }

  // S2. AND THE MISMATCH REFUSAL IS NOT A FALLBACK. `routeHash || licHash`
  // would be one character shorter and would turn a tenancy inconsistency into
  // a write under the caller's own licence. This arm goes red if somebody
  // "simplifies" it that way, which no behaviour arm can see -- the condition
  // is unreachable through a correct PostgREST, so a fallback would never fire
  // in any test that did not force it.
  // AND IT READS COMMENT-STRIPPED SOURCE, because the first spelling did not
  // and went red on its own subject's comment: the fix in api/sd-data.js
  // EXPLAINS why there is no `routeHash || licHash` fallback, and the
  // explanation contains the string. A checker whose universe includes the
  // prose describing it is a shape this clone's auto-memory already records --
  // "my own comments trip my own scanners" -- and the right answer is to blank
  // comments, never to stop writing the reason down.
  {
    const { stripJs } = require('../tests/lib/strip_comments.js');
    const src = stripJs(
      fs.readFileSync(path.join(__dirname, 'sd-data.js'), 'utf8'));
    is(/const routeHash = routeRow\.license_hash;/.test(src)
       && !/routeHash \|\| licHash/.test(src)
       && /ROUTE_TENANCY_MISMATCH/.test(src),
       'S2. the route hash is taken WITHOUT a `|| licHash` fallback, and a '
       + 'mismatch has its own refusal code',
       'routeHash decl=' + /const routeHash = routeRow\.license_hash;/.test(src)
         + ' fallback=' + /routeHash \|\| licHash/.test(src));
  }

  console.log('\n' + (fail ? 'FAILED' : 'PASSED') + ' -- ' + pass + ' passed, '
    + fail + ' failed'
    + (fail ? '\nFAILING ARMS: ' + failed.join(', ') : ''));
  process.exit(fail ? 1 : 0);
})().catch((e) => {
  console.error('HARNESS ERROR -- no verdict was reached, which is NOT a pass');
  console.error(e);
  process.exit(1);
});
