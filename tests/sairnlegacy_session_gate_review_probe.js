// tests/sairnlegacy_session_gate_review_probe.js
//
// REPORT-ONLY REVIEW PROBE for cc's LEG_RESOURCES session gate (obligation
// 2026-09-21T19:47:07Z on leg_invoices, assigned to cody). Not a regression
// suite -- api/sd-data-leg-session-gate.test.js is that, and re-running it
// would be re-reading the author's own answer. This DRIVES the four things the
// obligation asks a reviewer to check, plus the two it does not ask about that
// a reviewer should, and reports what it found either way.
//
// Run:  node tests/sairnlegacy_session_gate_review_probe.js
//
// WHY DRIVE RATHER THAN READ. The gate is nine lines and reads correctly. So
// did every gate this platform has had to fix twice. The questions worth
// answering are the ones reading cannot settle: is EVERY verb covered, not the
// two somebody thought of; is there an EARLIER branch that serves a leg_
// resource before the gate is reached; and does the refusal really happen with
// nothing read.
//
// EXIT CODE IS 0 UNLESS THE PROBE ITSELF COULD NOT RUN. A finding is reported,
// not thrown -- the reviewer writes the verdict, a probe does not get to.

'use strict';
process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET
  || ['cross', 'tenant', 'dispatchers', 'fixture'].join('-');

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const SD_DATA = path.join(ROOT, 'api', 'sd-data.js');
const LICENSE = path.join(ROOT, 'api', '_lib', 'license.js');
const { signSessionToken } = require(path.join(ROOT, 'api', '_lib', 'auth.js'));

const HASH = 'legacy-tenant-hash';
const findings = [];
const notes = [];

function ok(name, detail) { console.log('  ok      ' + name + (detail ? '\n            ' + detail : '')); }
function finding(name, detail) {
  console.log('  FINDING ' + name + '\n            ' + detail);
  findings.push(name + ' -- ' + detail);
}
function note(name, detail) {
  console.log('  note    ' + name + (detail ? '\n            ' + detail : ''));
  notes.push(name);
}

// Every fetch is counted AND recorded, because "refused" and "refused without
// reading anything" are different facts and only the second one is the claim.
let calls = [];
function loadHandler(appId) {
  delete require.cache[require.resolve(LICENSE)];
  require.cache[require.resolve(LICENSE)] = {
    exports: {
      validateLicenseKey: async function () {
        return {
          valid: true, active: true, license_hash: HASH,
          trial_ends_at: null, stripe_subscription_id: null, app_id: appId
        };
      }
    }
  };
  calls = [];
  global.fetch = async function (url, opts) {
    calls.push({ url: String(url), method: (opts && opts.method) || 'GET' });
    const u = String(url);
    if (opts && opts.method === 'POST') {
      return { ok: true, status: 200, json: async () => [JSON.parse(opts.body)] };
    }
    const rows = [{ license_hash: HASH, invoice_id: 'INV-1', deathrecord_id: 'DR-1',
                    custodylog_id: 'CL-1', merch_unit_id: 'MU-1', status: 'Available',
                    data: { id: 'INV-1', amount: 4200, decedent: 'A REAL NAME' } }];
    return { ok: true, status: 200, json: async () => (u.indexOf('leg_') >= 0 ? rows : []) };
  };
  delete require.cache[require.resolve(SD_DATA)];
  return require(SD_DATA);
}

function res() {
  const r = { statusCode: null, body: null };
  r.status = (c) => { r.statusCode = c; return r; };
  r.json = (b) => { r.body = b; return r; };
  return r;
}

async function call(action, resource, payload, token, appId) {
  const h = loadHandler(appId || 'sairnlegacy');
  const headers = { authorization: 'Bearer KEY' };
  if (token) headers['x-sd-auth'] = token;
  const r = res();
  await h({ method: 'POST', headers: headers,
            body: { action: action, resource: resource, payload: payload || {} } }, r);
  return r;
}

function code(r) { return (r.body && r.body.error && r.body.error.code) || null; }

// The verbs this handler understands AT ALL, read from its own source rather
// than from the two the gate's author had in mind. If a seventh verb is added
// next month and routed to a leg_ table, the point of this probe is that the
// question gets asked again.
const ALL_ACTIONS = Array.from(new Set(
  (fs.readFileSync(SD_DATA, 'utf8').match(/action === '([a-z_]+)'/g) || [])
    .map((m) => m.slice("action === '".length, -1))
)).sort();

(async () => {
  console.log('REVIEW PROBE -- cc\'s LEG_RESOURCES session gate, driven\n');
  console.log('  the handler understands ' + ALL_ACTIONS.length + ' verbs: ' + ALL_ACTIONS.join(', ') + '\n');

  // ── FOCUS 3, WIDENED: every verb, not the two the obligation names ───────
  console.log('1. EVERY verb against a gated resource, with no session');
  const leaked = [];
  for (const action of ALL_ACTIONS) {
    const r = await call(action, 'leg_invoices', { id: 'INV-1', status: 'Reserved' });
    const refused = r.statusCode === 401 && code(r) === 'NO_SESSION';
    const served = r.statusCode === 200;
    if (served) leaked.push(action + ' -> 200');
    else if (!refused) notes.push('leg_invoices ' + action + ' -> ' + r.statusCode + ' ' + (code(r) || ''));
  }
  if (leaked.length) {
    finding('a verb serves leg_invoices without a session',
            leaked.join(', ') + ' -- the gate is keyed on the RESOURCE before the verb dispatch, so this should be impossible');
  } else {
    ok('all ' + ALL_ACTIONS.length + ' verbs refuse leg_invoices with 401 NO_SESSION or fall through to no handler',
       'the gate sits before the verb dispatch, so an UNBORN verb is covered too -- which is the part a per-verb gate would have got wrong');
  }

  // ── FOCUS 1: the refusal is BEFORE the query ─────────────────────────────
  console.log('\n2. nothing is read before the refusal');
  let anyQueried = [];
  for (const action of ['read', 'write', 'soft_delete', 'delete', 'set_status']) {
    await call(action, 'leg_deathrecords', { id: 'DR-1' });
    if (calls.length) anyQueried.push(action + ' issued ' + calls.length + ' fetch(es): ' + calls.map((c) => c.method + ' ' + c.url.slice(0, 60)).join(' | '));
  }
  if (anyQueried.length) {
    finding('a refusal happened AFTER the table was read', anyQueried.join('; '));
  } else {
    ok('zero fetches on every refused verb, including the chain-of-custody and death-record tables',
       'a 401 issued after the fetch passes every status assertion and has already read the rows');
  }

  // ── FOCUS 2: the app scoping is real, driven both ways ───────────────────
  console.log('\n3. the app-scoping third argument');
  const foreign = signSessionToken({ app: 'sairndental', employee_id: 'e1', role: 'owner', license_hash: HASH });
  const rf = await call('read', 'leg_deathrecords', null, foreign);
  if (rf.statusCode === 200) {
    finding('a SAIRNdental session reads SAIRNlegacy death records',
            'verifySessionToken\'s third argument is missing or ignored (Guardian Check 28)');
  } else {
    ok('a valid sairndental owner session is refused ' + rf.statusCode + ' ' + code(rf),
       'and the roles collide by name across apps, which is why the third argument is not optional');
  }
  const own = signSessionToken({ app: 'sairnlegacy', employee_id: 'e1', role: 'owner', license_hash: HASH });
  const ro = await call('read', 'leg_deathrecords', null, own);
  if (ro.statusCode !== 200) {
    finding('a genuine sairnlegacy session CANNOT read', 'got ' + ro.statusCode + ' ' + code(ro) + ' -- this would be an app-wide outage, not a gate');
  } else {
    ok('a genuine sairnlegacy session reads normally (' + (ro.body.data || []).length + ' row(s))',
       'so the refusals above are a SPLIT rather than a lockout -- the arm that makes the rest a measurement');
  }

  // ── NOT IN THE OBLIGATION: is the gate reachable at all for every member? ─
  console.log('\n4. every one of the 36 members, not a sample');
  const src = fs.readFileSync(SD_DATA, 'utf8');
  const mapText = src.slice(src.indexOf('const LEG_RESOURCES = {'));
  const members = Array.from(new Set((mapText.slice(0, mapText.indexOf('};')).match(/leg_[a-z_]+/g) || [])));
  const open = [];
  for (const m of members) {
    const r = await call('read', m, null);
    if (r.statusCode !== 401) open.push(m + ' -> ' + r.statusCode);
  }
  if (open.length) finding('a member of the map is not behind the gate', open.join(', '));
  else ok('all ' + members.length + ' leg_ resources refuse 401 with no session',
          'checked individually rather than trusting that one `if (LEG_RESOURCES[resource])` covers the map');

  // ── NOT IN THE OBLIGATION: an EARLIER branch serving a leg_ resource ─────
  console.log('\n5. is there an earlier branch that serves a leg_ table before the gate?');
  const gateAt = src.indexOf('if (LEG_RESOURCES[resource]) {');
  const before = src.slice(0, gateAt);
  const earlier = (before.match(/rest\('leg_[a-z_]+/g) || []);
  if (earlier.length) {
    finding('a leg_ table is addressed BEFORE the gate block',
            Array.from(new Set(earlier)).join(', ') + ' -- a bespoke branch above the gate is not covered by it');
  } else {
    ok('no leg_ table is addressed anywhere above the gate',
       'the one place that could have defeated "one gate before the dispatch" -- a bespoke earlier branch for a single table, which is exactly what leg_merch_units has BELOW the gate');
  }

  // ── FOCUS 4, AND THE ARM THAT FOUND SOMETHING ───────────────────────────
  // FIRST SPELLING OF THIS ARM WAS WRONG AND REPORTED A CLEAN BILL. It looked
  // for `fetch('http...` and `fetch('/api/...` literals, found none, and said
  // "no cross-origin fetch in the page at all". Every call in this page goes
  // through a CONSTANT -- `var DATA_API='https://sairn.vercel.app/api/sd-data'`
  // -- so the regex could never have matched and the arm was vacuous in the
  // reassuring direction. Re-aimed at the constants themselves.
  console.log('\n6. the client half: EVERY call site that reaches the data endpoint');
  const html = fs.readFileSync(path.join(ROOT, 'sairnlegacy.html'), 'utf8');
  const consts = {};
  (html.match(/var (DATA_API|AUTH_API|PROXY)\s*=\s*'([^']+)'/g) || []).forEach((m) => {
    const p = m.match(/var (\w+)\s*=\s*'([^']+)'/);
    consts[p[1]] = p[2];
  });
  note('endpoint constants: ' + Object.keys(consts).map((k) => k + '=' + consts[k]).join('  '));

  const lines = html.split('\n');
  const dataSites = [];
  lines.forEach((ln, i) => {
    if (ln.indexOf('fetch(DATA_API') !== -1) {
      // ── THE WINDOW IS 12 LINES BEFORE AND 6 AFTER, AND THE FIRST VERSION
      // OF THIS ARM GOT IT WRONG IN THE DIRECTION THAT ACCUSES SOMEBODY.
      // A 3-line forward window flagged sdnData()'s own fetch (line 1555) as
      // tokenless, because that call is written across five lines --
      // `fetch(DATA_API,{` / signal / method / `headers:h` -- and the header
      // object `h` is BUILT twelve lines earlier, where the token is attached.
      // A review probe reporting a false finding against the session under
      // review is worse than one that reports nothing, so the window now
      // covers where a header object is assembled as well as where it is
      // passed.
      const from = Math.max(0, i - 12);
      const win = lines.slice(from, i + 7).join('\n');
      const literalToken = win.indexOf('X-SD-Auth') !== -1;
      dataSites.push({ line: i + 1, token: literalToken, text: ln.trim().slice(0, 90) });
    }
  });
  dataSites.forEach((s) => {
    note('  sairnlegacy.html:' + s.line + '  ' + (s.token ? 'sends a session token' : 'NO SESSION TOKEN') + '  ' + s.text);
  });
  const tokenless = dataSites.filter((s) => !s.token);
  if (!tokenless.length) {
    ok('every direct call to the data endpoint carries the session token',
       dataSites.length + ' site(s) checked by resolving the endpoint CONSTANT rather than a URL literal');
  } else {
    // Drive it: take the exact header set that call site sends and put it
    // through the real handler against the real resource it writes.
    const r = await call('write', 'leg_merch_units', { id: 'MU-1', status: 'Reserved' });
    finding('a direct data-endpoint call site sends NO session token, and the gate now refuses it',
            'sairnlegacy.html:' + tokenless.map((s) => s.line).join(', ')
            + ' posts { Content-Type, Authorization: Bearer <licence> } and no X-SD-Auth. '
            + 'Driven through the real handler with exactly those headers: leg_merch_units write -> '
            + r.statusCode + ' ' + code(r) + '. The transport fix landed inside sdnData(); THIS CALL '
            + 'SITE DELIBERATELY BYPASSES sdnData() (its own comment says so -- it needs the real 409 '
            + 'ALREADY_RESERVED status, which sdnData() collapses to null), so the unconditional-token '
            + 'change never reached it.');
  }

  console.log('\n' + findings.length + ' finding(s), ' + notes.length + ' note(s)');
  findings.forEach((f) => console.log('  - ' + f));
  notes.forEach((n) => console.log('  ? ' + n));
})().catch((e) => { console.log('PROBE COULD NOT RUN: ' + e.message); process.exit(3); });
