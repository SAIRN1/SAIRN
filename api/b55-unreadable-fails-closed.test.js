// hank b55 -- the six WRONG fail-opens from the b54 unparsable-2xx sweep, closed.
// The rule in every one: the store ANSWERED, the answer cannot be read, and so
// the protected thing is refused -- never treated as "no row", "empty", or a
// transport blip.
//
//   W1 _lib/auth.js credentialStillActive -> ACTIVE_CHECK_UNREADABLE; the sd-data
//      pre-gate and bridge.js refuse it 502.                       DRIVEN (unit)
//   W2 _lib/license.js lookup -> throws UPSTREAM + unparsable; claude.js refuses
//      LICENCE_UNREADABLE in every mode.                 DRIVEN (unit) + pin
//   W3 audit-checkpoint.js -- a non-list read throws, so verify cannot pass.  pin
//   W4 sairndental/public-complaint-submit.js -- duplicate check refuses 503. pin
//   W5 sairncash/trial-renew.js -- an unconfirmed renewal is 502.            pin
//   W6 sd-data.js derive_charges -- MAR / ADL / activity reads refuse 502.   pin
//
// Run: node api/b55-unreadable-fails-closed.test.js    Exit 0 pass, 1 fail

'use strict';
process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET || ['unreadable', 'b55', 'fixture'].join('-');
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://test.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'test-key';
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const Module = require('module');

const AUTH_FILE = path.join(__dirname, '_lib', 'auth.js');
const LIC_FILE = path.join(__dirname, '_lib', 'license.js');
function compile(file, src) {
  const m = new Module(file, module);
  m.filename = file;
  m.paths = Module._nodeModulePaths(path.dirname(file));
  m._compile(src, file);
  return m.exports;
}
const AUTH_SRC = fs.readFileSync(AUTH_FILE, 'utf8');
const LIC_SRC = fs.readFileSync(LIC_FILE, 'utf8');

const okBody = (v) => ({ ok: true, status: 200, json: async () => v, text: async () => JSON.stringify(v) });
const unparsable = () => ({ ok: true, status: 200, json: async () => { throw new SyntaxError('Unexpected token <'); }, text: async () => '<html>' });
async function withFetch(impl, fn) {
  const prev = global.fetch; global.fetch = impl;
  try { return await fn(); } finally { global.fetch = prev; }
}

const SESSION = { employee_id: 'E1', role: 'owner', app: 'stonedesk' };
const rest = (p) => 'https://test.supabase.co/rest/v1/' + p;
async function armW1(src) {
  const auth = compile(AUTH_FILE, src);
  for (const [label, resp] of [['unparsable', unparsable], ['non-list', () => okBody({ message: 'x' })]]) {
    const r = await withFetch(async () => resp(), () => auth.credentialStillActive(SESSION, 'LIC', rest, {}));
    assert.deepStrictEqual([r.ok, r.code], [false, 'ACTIVE_CHECK_UNREADABLE'], label + ': ' + JSON.stringify(r));
  }
}
async function armW1Controls(src) {
  const auth = compile(AUTH_FILE, src);
  const live = await withFetch(async () => okBody([{ active: true }]), () => auth.credentialStillActive(SESSION, 'LIC', rest, {}));
  assert.deepStrictEqual(live, { ok: true });
  const blip = await withFetch(async () => { throw new Error('ECONNRESET'); }, () => auth.credentialStillActive(SESSION, 'LIC', rest, {}));
  assert.strictEqual(blip.code, 'NO_ACTIVE_CHECK', 'a transport failure is still the third state, not a refusal');
  const off = await withFetch(async () => okBody([{ active: false }]), () => auth.credentialStillActive(SESSION, 'LIC', rest, {}));
  assert.strictEqual(off.code, 'CREDENTIAL_INACTIVE');
}

async function armW2(src) {
  const lic = compile(LIC_FILE, src);
  let err = null;
  await withFetch(async () => unparsable(), async () => {
    try { await lic.validateLicenseKey('ANY-KEY-2026'); } catch (e) { err = e; }
  });
  assert.ok(err, 'an unparsable licence body did not throw');
  assert.deepStrictEqual([err.code, err.unparsable], ['UPSTREAM', true]);
}

function pin(file, line) {
  const t = fs.readFileSync(path.join(__dirname, file), 'utf8');
  assert.strictEqual(t.split(line).length - 1, 1, file + ': expected exactly once: ' + line.slice(0, 80));
}

let pass = 0, fail = 0;
async function test(name, fn) {
  try { await fn(); pass++; console.log('  ok   ' + name); }
  catch (e) { fail++; console.log('  FAIL ' + name + '\n       ' + String(e.message).slice(0, 300)); }
}
async function mustFail(fn, name) {
  try { await fn(); } catch (e) {
    if (e instanceof assert.AssertionError) return;
    throw new Error(name + ': non-assertion error, the mutant proves nothing: ' + e.message);
  }
  throw new Error(name + ' survived');
}
function mutate(src, from, to) {
  const n = src.split(from).length - 1;
  if (n !== 1) throw new Error('mutant anchor found ' + n + ' times: ' + from.slice(0, 60));
  return src.replace(from, to);
}

(async function () {
  console.log('b55 -- an unreadable answer fails CLOSED');
  await test('W1a. credentialStillActive: an unparsable or non-list 2xx -> ACTIVE_CHECK_UNREADABLE', () => armW1(AUTH_SRC));
  await test('W1b. controls: active -> ok; a transport throw -> NO_ACTIVE_CHECK; active:false -> CREDENTIAL_INACTIVE', () => armW1Controls(AUTH_SRC));
  await test('W1c. both callers refuse ACTIVE_CHECK_UNREADABLE 502 (source pins)', () => {
    pin('sd-data.js', "if (!preActive.ok && preActive.code === 'ACTIVE_CHECK_UNREADABLE') {");
    pin('bridge.js', "if (!stillActive.ok && stillActive.code === 'ACTIVE_CHECK_UNREADABLE') {");
  });
  await test('W2a. license.js: an unparsable licence body throws UPSTREAM + unparsable (never "no licence")', () => armW2(LIC_SRC));
  await test('W2b. claude.js refuses LICENCE_UNREADABLE before the fail-open (source pin)', () =>
    pin('claude.js', "res.status(502).json({ error: { code: 'LICENCE_UNREADABLE',"));
  await test('W3. audit-checkpoint.js: all three readers throw on a non-list body (source pins)', () => {
    pin('audit-checkpoint.js', "if (!Array.isArray(body)) { const e = new Error('earliest read unreadable'); e.detail = body; throw e; }");
    const t = fs.readFileSync(path.join(__dirname, 'audit-checkpoint.js'), 'utf8');
    assert.strictEqual(t.split("new Error('checkpoint read unreadable')").length - 1, 2, 'lastCheckpoint + allCheckpoints guards');
  });
  await test('W4. public complaint duplicate check refuses an unreadable 2xx (source pin)', () =>
    pin(path.join('sairndental', 'public-complaint-submit.js'), "duplicate check unreadable -- refusing rather than filing unchecked"));
  await test('W5. trial-renew refuses an unconfirmed renewal (source pin)', () =>
    pin(path.join('sairncash', 'trial-renew.js'), "code: 'RENEWAL_UNCONFIRMED',"));
  await test('W6. derive_charges: MAR, ADL and activity reads refuse (source pins)', () => {
    for (const w of ['medication record (MAR)', 'resident record (ADL assessments)', 'activities log']) {
      const t = fs.readFileSync(path.join(__dirname, 'sd-data.js'), 'utf8');
      assert.strictEqual(t.split("'Could not read the " + w + ", so no charges were derived.'").length - 1, 2, w);
    }
  });
  console.log('M. mutants');
  await test('M1. credentialStillActive non-list guard removed -> W1a red', () => mustFail(() => armW1(mutate(AUTH_SRC,
    "  if (!Array.isArray(rows)) {\n    return { ok: false, code: 'ACTIVE_CHECK_UNREADABLE'", "  if (false) {\n    return { ok: false, code: 'ACTIVE_CHECK_UNREADABLE'")), 'W1'));
  await test('M2. license.js unparsable tag removed -> W2a red', () => mustFail(() => armW2(mutate(LIC_SRC,
    'e.unparsable = true;', 'e.unparsable = false;')), 'W2'));
  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
