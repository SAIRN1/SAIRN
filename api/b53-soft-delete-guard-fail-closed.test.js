// hank b53 -- a soft-delete guard that cannot read its subject has not checked
// it. The two resurrection guards (sd_customers, and SAIRNcode's soft-delete-
// only Tier A resources) wrapped their 409 in `if (pre.ok)`, so a 4xx/5xx
// pre-read or an unparsable body fell through to the wholesale upsert -- the
// resurrection each guard exists to stop. Michael's b53 decision: refuse.
//
// Drives the real api/sd-data.js handler. Section M removes each new refusal
// and requires its arm to go red.
//
// Run: node api/b53-soft-delete-guard-fail-closed.test.js    Exit 0 pass, 1 fail

'use strict';
process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET || ['soft', 'delete', 'b53', 'fixture'].join('-');
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://test.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'test-key';
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const Module = require('module');
const { signSessionToken } = require('./_lib/auth');

const SD_FILE = path.join(__dirname, 'sd-data.js');
const SD_SRC = fs.readFileSync(SD_FILE, 'utf8');
const HASH = 'b53-hash';

function load(src, app) {
  const lic = require.resolve('./_lib/license');
  delete require.cache[lic];
  require.cache[lic] = { id: lic, filename: lic, loaded: true, exports: {
    validateLicenseKey: async function () {
      return { valid: true, active: true, license_hash: HASH, trial_ends_at: null,
               stripe_subscription_id: null, app_id: app };
    } } };
  const m = new Module(SD_FILE, module);
  m.filename = SD_FILE;
  m.paths = Module._nodeModulePaths(__dirname);
  m._compile(src || SD_SRC, SD_FILE);
  return m.exports;
}

// pre() answers the guard's pre-read of the target table; writes are recorded.
async function drive(src, app, role, resource, pre) {
  const h = load(src, app);
  const writes = [];
  const prev = global.fetch;
  global.fetch = async function (url, o) {
    const u = String(url);
    const method = (o && o.method) || 'GET';
    if (/_employee_auth\?/.test(u)) {
      return { ok: true, status: 200, json: async () => [{ license_hash: HASH, employee_id: 'emp-1', role: role, active: true }] };
    }
    if (method !== 'GET') {
      if (u.indexOf(resource + '?on_conflict') !== -1) {
        writes.push(u);
        const b = JSON.parse(o.body);
        return { ok: true, status: 201, text: async () => '', json: async () => [Array.isArray(b) ? b[0] : b] };
      }
      return { ok: true, status: 201, text: async () => '', json: async () => [] };
    }
    if (u.indexOf(resource + '?') !== -1 && /select=data&limit=1/.test(u)) return pre();
    return { ok: true, status: 200, text: async () => '[]', json: async () => [] };
  };
  const res = { statusCode: null, body: null, setHeader: function () { return res; },
                status: function (c) { res.statusCode = c; return res; },
                json: function (b) { res.body = b; return res; } };
  try {
    await h({ method: 'POST', headers: { authorization: 'Bearer KEY',
      'x-sd-auth': signSessionToken({ app: app, employee_id: 'emp-1', role: role, license_hash: HASH }) },
      body: { action: 'write', resource: resource, payload: { id: 'X-1', name: 'b53 probe' } } }, res);
  } finally { global.fetch = prev; }
  return { res: res, writes: writes };
}
const code = (r) => ((r.body || {}).error || {}).code;
const rows = (r) => () => ({ ok: true, status: 200, text: async () => JSON.stringify(r), json: async () => r });
const status = (s) => () => ({ ok: false, status: s, text: async () => '{"message":"x"}', json: async () => ({ message: 'x' }) });
const unparsable = () => ({ ok: true, status: 200, text: async () => '<html>', json: async () => { throw new SyntaxError('Unexpected token <'); } });

const TARGETS = [
  { tag: 'C', app: 'stonedesk', role: 'owner', resource: 'sd_customers' },
  { tag: 'S', app: 'sairncode', role: 'admin', resource: 'sc_claims' },
];

async function armUnreadable(t, src) {
  for (const [label, pre] of [['HTTP 500', status(500)], ['HTTP 403', status(403)], ['unparsable', unparsable],
                              ['non-list', rows({ message: 'x' })]]) {
    const r = await drive(src, t.app, t.role, t.resource, pre);
    assert.deepStrictEqual([r.res.statusCode, code(r.res), r.writes.length], [502, 'UNREADABLE_PRIOR', 0],
      t.resource + ' ' + label + ': ' + JSON.stringify(r.res.body));
  }
}
async function armControls(t, src) {
  const del = await drive(src, t.app, t.role, t.resource, rows([{ data: { _deleted_at: '2026-10-01T00:00:00Z' } }]));
  assert.deepStrictEqual([del.res.statusCode, code(del.res), del.writes.length], [409, 'DELETED', 0], 'deleted: ' + JSON.stringify(del.res.body));
  const live = await drive(src, t.app, t.role, t.resource, rows([{ data: { name: 'old' } }]));
  assert.deepStrictEqual([live.res.statusCode, live.writes.length], [200, 1], 'live row: ' + JSON.stringify(live.res.body));
  const none = await drive(src, t.app, t.role, t.resource, rows([]));
  assert.deepStrictEqual([none.res.statusCode, none.writes.length], [200, 1], 'no row: ' + JSON.stringify(none.res.body));
  const np = await drive(src, t.app, t.role, t.resource, status(404));
  assert.notStrictEqual(code(np.res), 'UNREADABLE_PRIOR', '404 (not provisioned) must fall through to the write');
}

function mutate(from, to) {
  const n = SD_SRC.split(from).length - 1;
  if (n !== 1) throw new Error('mutant anchor found ' + n + ' times: ' + from.slice(0, 70));
  return SD_SRC.replace(from, to);
}
async function mustFail(arm, src, name) {
  try { await arm(src); } catch (e) {
    if (e instanceof assert.AssertionError) return;
    throw new Error(name + ': non-assertion error, the mutant proves nothing: ' + e.message);
  }
  throw new Error(name + ' survived');
}

let pass = 0, fail = 0;
async function test(name, fn) {
  try { await fn(); pass++; console.log('  ok   ' + name); }
  catch (e) { fail++; console.log('  FAIL ' + name + '\n       ' + String(e.message).slice(0, 300)); }
}

(async function () {
  console.log('b53 -- soft-delete guards refuse when they cannot read');
  for (const t of TARGETS) {
    await test(t.tag + '1. ' + t.resource + ': a 500 / 403 / unparsable / non-list pre-read -> 502 UNREADABLE_PRIOR, nothing written', () => armUnreadable(t));
    await test(t.tag + '2. ' + t.resource + ' controls: deleted -> 409; live row and no row -> written; 404 -> not this refusal', () => armControls(t));
  }
  console.log('M. mutants');
  await test('M1. sd_customers !ok refusal removed -> C1 red', () => mustFail((s) => armUnreadable(TARGETS[0], s),
    mutate("if (!rcur.ok && rcur.status !== 404 && rcur.status !== 400) {", 'if (false) {'), 'customers !ok'));
  await test('M2. sd_customers non-list refusal removed -> C1 red', () => mustFail((s) => armUnreadable(TARGETS[0], s),
    mutate('if (!Array.isArray(rrows)) {', 'if (false) {'), 'customers non-list'));
  await test('M3. SAIRNcode !ok refusal removed -> S1 red', () => mustFail((s) => armUnreadable(TARGETS[1], s),
    mutate("if (!scur.ok && scur.status !== 404 && scur.status !== 400) {", 'if (false) {'), 'sc !ok'));
  await test('M4. SAIRNcode non-list refusal removed -> S1 red', () => mustFail((s) => armUnreadable(TARGETS[1], s),
    mutate('if (!Array.isArray(srows)) {', 'if (false) {'), 'sc non-list'));
  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
