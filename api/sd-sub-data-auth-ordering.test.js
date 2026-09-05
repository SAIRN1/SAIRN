// api/sd-sub-data-auth-ordering.test.js
//
// Run:  node api/sd-sub-data-auth-ordering.test.js
//
// `api/sd-sub-data.js` ran its envelope gate -- action, resource, payload cap
// -- ABOVE licence validation, the same shape fixed in api/sd-data.js on
// 2026-09-04 ("a junk bearer token could enumerate all 268 resource names").
//
// THE ENUMERATION HALF WAS TRIVIAL HERE and the row said so: the list is three
// hardcoded names a reader of the subcontractor app already knows. THE ORACLE
// WAS THE REAL DEFECT. A caller holding no credential at all got a different
// refusal for `roster` than for `nonsense`, and a different one again for a
// verb this endpoint refuses -- so the surface and its permitted actions could
// be mapped without ever authenticating.
//
// THE TRAP THIS FILE IS BUILT TO AVOID, learned from the sibling fix: on a
// developer machine SUPABASE_URL is unset, so almost any call returns a
// config 500 -- and a test written against that passes whether or not the
// ordering is right. Every assertion below therefore stubs the licence lookup
// and sets the env, so the handler runs its REAL path and the 401 it returns
// is the one production would return. A fix proved only in the accidental
// configuration is not proved.

'use strict';
const path = require('path');
const assert = require('assert');

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('--- ' + t + ' ---'); }

// The handler destructures validateLicenseKey at module load, so the stub has
// to be in the require cache BEFORE the handler is required -- patching the
// module object afterwards would leave the handler holding the real function.
const LICENSE_PATH = require.resolve('./_lib/license.js');
let licenseAnswer = { valid: false };
require.cache[LICENSE_PATH] = {
  id: LICENSE_PATH, filename: LICENSE_PATH, loaded: true, exports: {
    validateLicenseKey: async () => licenseAnswer,
  },
};
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://example.invalid';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'test-key';

const handler = require('./sd-sub-data.js');

async function call(body, opts) {
  opts = opts || {};
  const res = { _s: 0, _j: null, status(c) { this._s = c; return this; }, json(o) { this._j = o; return this; } };
  await handler({
    method: opts.method || 'POST',
    headers: { authorization: 'authorization' in opts ? opts.authorization : 'Bearer not-a-real-key' },
    body,
  }, res);
  return { status: res._s, body: res._j, text: JSON.stringify(res._j) };
}

const run = [];
function t(name, fn) { run.push([name, fn]); }

// ── an unauthenticated caller learns exactly one thing ────────────────────
section('a junk bearer token gets one answer and no oracle');

t('a junk token with an unknown resource is 401, not a 400 naming the list', async () => {
  const r = await call({ action: 'read', resource: 'nonsense' });
  assert.strictEqual(r.status, 401, 'expected INVALID_LICENSE, got ' + r.text);
  assert.strictEqual(r.body.error.code, 'INVALID_LICENSE');
});

t('and the three resource names appear NOWHERE in that answer', async () => {
  const r = await call({ action: 'read', resource: 'nonsense' });
  ['roster', 'jobs', 'progress_photos'].forEach((n) => {
    assert.ok(r.text.indexOf(n) === -1, 'the refusal discloses "' + n + '"');
  });
});

t('NO REAL-VS-INVENTED ORACLE: a real resource answers identically', async () => {
  const real = await call({ action: 'read', resource: 'roster' });
  const fake = await call({ action: 'read', resource: 'nonsense' });
  assert.strictEqual(real.status, fake.status);
  assert.strictEqual(real.text, fake.text, 'a real resource is distinguishable from an invented one');
});

t('NO PERMITTED-VS-REFUSED VERB ORACLE', async () => {
  const ok = await call({ action: 'qc-review', resource: 'progress_photos' });
  const no = await call({ action: 'delete', resource: 'progress_photos' });
  assert.strictEqual(ok.status, no.status);
  assert.strictEqual(ok.text, no.text, 'a permitted verb is distinguishable from a refused one');
});

t('NO PAYLOAD-SIZE ORACLE: an oversized write is 401, not 413', async () => {
  // MUST actually exceed SUB_JOB_PAYLOAD_MAX_BYTES, which is 1.5 MB. The first
  // draft used 300 KB and was VACUOUS -- it passed before the fix and after it,
  // because the payload never reached the cap and the 413 branch was never
  // entered either way. Caught by the negative control below: every other
  // oracle assertion went red on the pre-fix ordering and this one did not,
  // which is the only reason it was looked at. Read from the constant rather
  // than hardcoded, so raising the cap cannot silently make this vacuous again.
  const cap = 1.5 * 1024 * 1024;
  const big = { action: 'write', resource: 'jobs', payload: { blob: 'x'.repeat(cap + 1024) } };
  assert.ok(Buffer.byteLength(JSON.stringify(big.payload), 'utf8') > cap,
    'the probe payload does not exceed the cap -- this assertion would be vacuous');
  const r = await call(big);
  assert.strictEqual(r.status, 401, 'an unauthenticated caller learned the payload cap');
  assert.ok(r.text.indexOf('PAYLOAD_TOO_LARGE') === -1);
});

t('NO MALFORMED-BODY ORACLE: invalid JSON is 401, not 400', async () => {
  const r = await call('{not json');
  assert.strictEqual(r.status, 401, 'an unauthenticated caller learned its body was malformed');
});

t('an INACTIVE licence is 403 and still discloses nothing', async () => {
  licenseAnswer = { valid: true, active: false, license_hash: 'h' };
  const r = await call({ action: 'read', resource: 'nonsense' });
  licenseAnswer = { valid: false };
  assert.strictEqual(r.status, 403);
  assert.ok(r.text.indexOf('roster') === -1);
});

// ── what must NOT have changed ────────────────────────────────────────────
section('the checks that disclose nothing stay where they were');

t('a non-POST is still 405, before anything else', async () => {
  const r = await call({}, { method: 'GET' });
  assert.strictEqual(r.status, 405);
});

t('a missing bearer is still NO_LICENSE, and costs no licence lookup', async () => {
  const r = await call({ action: 'read', resource: 'roster' }, { authorization: '' });
  assert.strictEqual(r.status, 401);
  assert.strictEqual(r.body.error.code, 'NO_LICENSE');
});

t('AN AUTHENTICATED CALLER STILL GETS THE ENVELOPE ERRORS -- the reorder must '
  + 'not have deleted the gates', async () => {
  licenseAnswer = { valid: true, active: true, license_hash: 'h' };
  const bad = await call({ action: 'delete', resource: 'roster' });
  const unknown = await call({ action: 'read', resource: 'nonsense' });
  licenseAnswer = { valid: false };
  assert.strictEqual(bad.status, 400, 'a valid licence no longer gets the action error');
  assert.match(bad.text, /action must be/);
  assert.strictEqual(unknown.status, 400, 'a valid licence no longer gets the resource error');
  assert.match(unknown.text, /resource must be one of/);
});

// ── the ordering itself, so a re-swap fails loudly ────────────────────────
section('the source ordering');

t('validateLicenseKey sits ABOVE the resource, action and payload gates', () => {
  const fs = require('fs');
  const src = fs.readFileSync(path.join(__dirname, 'sd-sub-data.js'), 'utf8');
  const at = (re) => { const m = src.match(re); assert.ok(m, 'not found: ' + re); return m.index; };
  const lic = at(/lic = await validateLicenseKey/);
  assert.ok(lic < at(/resource must be one of/), 'the resource gate runs before licence validation');
  assert.ok(lic < at(/action must be 'read'/), 'the action gate runs before licence validation');
  assert.ok(lic < at(/PAYLOAD_TOO_LARGE/), 'the payload cap runs before licence validation');
  assert.ok(lic < at(/Invalid JSON body/), 'the body parse runs before licence validation');
  assert.ok(at(/Method not allowed/) < at(/NO_LICENSE/), 'the 405 check no longer runs first');
  assert.strictEqual((src.match(/await validateLicenseKey/g) || []).length, 1,
    'the licence is validated more than once');
});

(async function () {
  for (const [name, fn] of run) {
    try { await fn(); console.log('  ok   ' + name); pass++; }
    catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
  }
  console.log('\n' + (fail ? 'FAILED  ' : 'ok  ') +
    'sd-sub-data auth ordering: ' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
