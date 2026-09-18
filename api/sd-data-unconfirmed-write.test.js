// api/sd-data-unconfirmed-write.test.js
// REQUIREMENT: a soft-delete is reported as done only when the data store hands
//   back the row it changed -- an unreadable answer and a zero-row match are
//   each their own refusal, never a success
//
// Run:  node api/sd-data-unconfirmed-write.test.js
//
// ── WHY THIS EXISTS ────────────────────────────────────────────────────────
// A platform sweep for the shape fixed in api/sc-credentials.js on 2026-09-18
// found the same one in the soft-delete paths here. Under
// `Prefer: return=representation` a PATCH that MATCHED returns one row and a
// PATCH that matched ZERO returns `[]` with status 200. These paths checked
// only `w.ok`, and `.json().catch(() => null)` turned an unparseable body into
// null, so all three of "it landed", "it matched nothing" and "the answer could
// not be read" reached `res.json({ ok: true })`.
//
// THE CONSEQUENCE IS A DELETION THAT DID NOT HAPPEN, which is the sentence in
// the other direction from the one this platform usually guards: the caller is
// told the record is gone and it is still there.
//
// TIER A COVERAGE IS THE REASON IT WAS FIXED RATHER THAN RECORDED. The generic
// SD_LOCAL_RESOURCES soft-delete serves SEVEN Tier A resources -- sd_invoices,
// sd_fin_jobs, sd_pricing_rules, sd_negotiated_prices, sd_order_history,
// stonedesk_quote_history and sd_aiquotes -- and sd_quote_requests has its own
// Tier A path beside it.

'use strict';
const assert = require('assert');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const licPath = require.resolve(path.join(ROOT, 'api/_lib/license.js'));
const authPath = require.resolve(path.join(ROOT, 'api/_lib/auth.js'));
const realAuth = require(authPath);

let LICENSE = null, SESSION = null;
require.cache[licPath] = { id: licPath, filename: licPath, loaded: true,
  exports: { validateLicenseKey: async () => LICENSE } };
require.cache[authPath] = { id: authPath, filename: authPath, loaded: true,
  exports: Object.assign({}, realAuth, {
    verifySessionToken: () => SESSION, tokenFromRequest: () => 'tok' }) };

const PH = 'stub-' + 'placeholder';
[['SUPABASE_URL', 'https://stub.supabase.co'],
 ['SUPABASE_SERVICE_ROLE_KEY', PH],
 ['SD_AUTH_SECRET', PH]].forEach((p) => { process.env[p[0]] = p[1]; });

// ── the stub. One stored row, and a PLAN for what the PATCH answers with. ──
let ROW = null;            // { data } or null
let PATCH_PLAN = null;     // 'unparseable' | 'empty' | 'notarray' | null
let PATCHES = 0;

function J(b, s) { return { ok: s >= 200 && s < 300, status: s, json: async () => b }; }
function BAD(s) { return { ok: s >= 200 && s < 300, status: s,
  json: async () => { throw new Error('unparseable'); } }; }

global.fetch = async (url, opts) => {
  opts = opts || {};
  const m = (opts.method || 'GET').toUpperCase();
  if (m === 'GET') return J(ROW ? [{ data: ROW.data }] : [], 200);
  if (m === 'PATCH') {
    PATCHES += 1;
    if (PATCH_PLAN === 'unparseable') return BAD(200);
    if (PATCH_PLAN === 'empty') return J([], 200);
    if (PATCH_PLAN === 'notarray') return J({ data: {} }, 200);
    ROW = { data: JSON.parse(opts.body).data };
    return J([{ data: ROW.data }], 200);
  }
  return J({}, 500);
};

const handler = require(path.join(ROOT, 'api/sd-data.js'));

function mkRes() {
  const o = { code: null, body: null };
  return { _out: o, setHeader() {}, status(c) { o.code = c; return this; },
           json(b) { o.body = b; return this; }, end() { return this; } };
}
async function call(resource, payload, appId) {
  const res = mkRes();
  await handler({ method: 'POST',
    headers: { 'x-sd-auth': 'tok', authorization: 'Bearer LIC' },
    body: { action: 'soft_delete', resource, payload, app_id: appId || 'stonedesk' } }, res);
  return res._out;
}
function reset(app) {
  ROW = { data: { id: 'R-1', note: 'still here' } };
  PATCH_PLAN = null; PATCHES = 0;
  LICENSE = { valid: true, active: true, license_hash: 'H1', app_id: app || 'stonedesk' };
  SESSION = { role: 'owner', employee_id: 'E-1' };
}

let pass = 0, fail = 0;
const t = (n, f) => Promise.resolve().then(f).then(
  () => { pass++; console.log('  ok   ' + n); },
  (e) => { fail++; console.log('  FAIL ' + n + '\n       ' + e.message); });

(async () => {

console.log('\n1. THE GENERIC SOFT-DELETE -- it serves SEVEN Tier A resources');

// sd_invoices is one of the seven. Picked deliberately: a deletion reported as
// done on an invoice that is still there is the worst reading of this defect.
for (const [name, plan, wantCode, wantErr] of [
  ['an UNPARSEABLE representation refuses, never ok', 'unparseable', 502, 'WRITE_UNCONFIRMED'],
  ['a NOT-AN-ARRAY representation refuses too', 'notarray', 502, 'WRITE_UNCONFIRMED'],
  ['a ZERO-ROW match is NOT FOUND, not a successful delete', 'empty', 404, 'NOT_FOUND'],
]) await t('sd_invoices: ' + name, async () => {
  reset();
  PATCH_PLAN = plan;
  const out = await call('sd_invoices', { id: 'R-1' });
  assert.notStrictEqual(out.body && out.body.ok, true,
    'a delete that did not happen was reported as done: ' + JSON.stringify(out.body));
  assert.strictEqual(out.code, wantCode, JSON.stringify(out.body));
  assert.strictEqual(out.body.error.code, wantErr);
  assert.strictEqual(ROW.data.note, 'still here', 'the stub row should be untouched');
  assert.strictEqual(PATCHES, 1, 'the write must still have been attempted once');
});

await t('sd_invoices: an ordinary soft-delete still succeeds', async () => {
  reset();
  const out = await call('sd_invoices', { id: 'R-1' });
  assert.strictEqual(out.code, 200, JSON.stringify(out.body));
  assert.strictEqual(out.body.ok, true);
  assert.ok(ROW.data._deleted_at, 'the row was not actually marked');
});

console.log('\n2. sd_quote_requests -- its own Tier A path, same three answers');

for (const [name, plan, wantCode, wantErr] of [
  ['an UNPARSEABLE representation refuses', 'unparseable', 502, 'WRITE_UNCONFIRMED'],
  ['a ZERO-ROW match is NOT FOUND', 'empty', 404, 'NOT_FOUND'],
]) await t('sd_quote_requests: ' + name, async () => {
  reset();
  PATCH_PLAN = plan;
  const out = await call('sd_quote_requests', { id: 'R-1' });
  assert.notStrictEqual(out.body && out.body.ok, true, JSON.stringify(out.body));
  assert.strictEqual(out.code, wantCode, JSON.stringify(out.body));
  assert.strictEqual(out.body.error.code, wantErr);
});

await t('sd_quote_requests: an ordinary soft-delete still succeeds', async () => {
  reset();
  const out = await call('sd_quote_requests', { id: 'R-1' });
  assert.strictEqual(out.code, 200, JSON.stringify(out.body));
  assert.strictEqual(out.body.ok, true);
});

console.log('\n3. THE DIRECTION THAT MUST NOT SOFTEN');

await t('an ALREADY-deleted row still short-circuits without a write', async () => {
  // This path answers 200 before any PATCH, and it must keep doing so -- the
  // new guards sit after the write and must not have moved in front of it.
  reset();
  ROW = { data: { id: 'R-1', _deleted_at: '2026-01-01T00:00:00.000Z' } };
  const out = await call('sd_invoices', { id: 'R-1' });
  assert.strictEqual(out.code, 200);
  assert.strictEqual(out.body.already_deleted, true);
  assert.strictEqual(PATCHES, 0, 'an already-deleted row must not be written again');
});

await t('a MISSING row is still 404 before any write', async () => {
  reset();
  ROW = null;
  const out = await call('sd_invoices', { id: 'R-1' });
  assert.strictEqual(out.code, 404);
  assert.strictEqual(PATCHES, 0);
});

console.log('\n' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
})();
