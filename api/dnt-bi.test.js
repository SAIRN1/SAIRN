// api/dnt-bi.test.js
// Endpoint suite for SAIRNdental B5 -- the open BI / data-warehouse feed.
//
// Run:  node --test api/dnt-bi.test.js
//
// api/_lib/dental-bi.test.js proves the RULES are right. This file proves the
// endpoint actually applies them, which is a different claim and the one that
// has failed before on this platform: a correct gate function that some code
// path never calls is worth nothing, and reads as safe in review.
//
// Supabase is stubbed by URL. The stub also RECORDS every request, so the tests
// can assert not just what came back but what was asked for -- that is the only
// way to prove a provider's appointment read was narrowed in the database
// rather than after it.
//
// Every value below is a placeholder built by concatenation, not a real
// credential; nothing in this file is or resembles a secret.

'use strict';
const test = require('node:test');
const assert = require('node:assert');

// ── STUBS, INSTALLED BEFORE api/dnt-bi.js IS LOADED ────────────────────────
const licPath = require.resolve('./_lib/license.js');
const authPath = require.resolve('./_lib/auth.js');
const realAuth = require(authPath);

let SESSION = null;   // what verifySessionToken returns
let LICENSE = null;

require.cache[licPath] = {
  id: licPath, filename: licPath, loaded: true, exports: {
    validateLicenseKey: async () => LICENSE
  }
};
require.cache[authPath] = {
  id: authPath, filename: authPath, loaded: true, exports: Object.assign({}, realAuth, {
    verifySessionToken: () => SESSION,
    tokenFromRequest: (req) => req.headers['x-sd-auth'] || null
  })
};

const PLACEHOLDER = 'stub-' + 'placeholder';
[
  ['SUPABASE_URL', 'https://stub.supabase.co'],
  ['SUPABASE_SERVICE_ROLE_KEY', PLACEHOLDER],
  ['SD_AUTH_SECRET', PLACEHOLDER],
  ['DENTAL_BI_KEY', PLACEHOLDER]
].forEach(function (pair) { process.env[pair[0]] = pair[1]; });

const bi = require('./_lib/dental-bi');
const handler = require('./dnt-bi.js');

// ── THE SUPABASE STUB ──────────────────────────────────────────────────────
let TABLES = {};
let REQUESTS = [];
const realFetch = global.fetch;

function tableOf(url) {
  const m = /\/rest\/v1\/([a-z0-9_]+)/i.exec(url);
  return m ? m[1] : null;
}
function paramsOf(url) {
  const q = url.indexOf('?');
  return q === -1 ? new URLSearchParams() : new URLSearchParams(url.slice(q + 1));
}

// Minimal PostgREST filter support: eq., is.null, and the implicit AND.
function matches(row, params) {
  let ok = true;
  params.forEach(function (v, k) {
    if (k === 'select' || k === 'order' || k === 'limit') return;
    if (v === 'is.null') { if (row[k] != null) ok = false; return; }
    if (v.indexOf('eq.') === 0) {
      const want = decodeURIComponent(v.slice(3));
      const got = row[k];
      const gotS = typeof got === 'boolean' ? String(got) : String(got == null ? '' : got);
      if (gotS !== want) ok = false;
    }
  });
  return ok;
}

global.fetch = async function (url, opts) {
  opts = opts || {};
  const method = opts.method || 'GET';
  const table = tableOf(String(url));
  REQUESTS.push({ url: String(url), method: method, table: table, body: opts.body ? JSON.parse(opts.body) : null });

  const spec = TABLES[table];
  if (!spec) {
    // A table nobody set up in this test = a table that does not exist in the
    // deployment. Shaped like PostgREST's real answer, not an empty array.
    return { ok: false, status: 404, json: async () => ({ code: 'PGRST205', message: 'Could not find the table' }) };
  }
  if (spec.error) return { ok: false, status: spec.status || 500, json: async () => ({ message: 'boom' }) };

  if (method === 'POST') {
    const row = Object.assign({ id: 'row-' + (spec.rows.length + 1) }, JSON.parse(opts.body));
    spec.rows.push(row);
    return { ok: true, status: 201, json: async () => [row] };
  }
  if (method === 'PATCH') {
    const p = paramsOf(String(url));
    const patch = JSON.parse(opts.body);
    const hit = spec.rows.filter(function (r) { return matches(r, p); });
    hit.forEach(function (r) { Object.assign(r, patch); });
    return { ok: true, status: 200, json: async () => hit };
  }
  const p = paramsOf(String(url));
  const hit = spec.rows.filter(function (r) { return matches(r, p); });
  return { ok: true, status: 200, json: async () => hit.map(function (r) { return project(r, p.get('select')); }) };
};

// PostgREST honours ?select=. The stub must too, or "list never returns a token
// hash" would pass on a stub that returns whole rows while the endpoint relies
// on the column list to keep the hash in the database. That was the first
// version of this file and the assertion was worthless.
function project(row, select) {
  if (!select) return row;
  const out = {};
  select.split(',').map(function (s) { return s.trim(); }).forEach(function (c) {
    if (c && c in row) out[c] = row[c];
  });
  return out;
}

// ── REQUEST / RESPONSE DOUBLES ─────────────────────────────────────────────
function mkRes() {
  const r = { statusCode: null, body: null };
  r.status = function (c) { r.statusCode = c; return r; };
  r.json = function (b) { r.body = b; return r; };
  return r;
}
async function GET(query, headers) {
  const res = mkRes();
  await handler({ method: 'GET', query: query || {}, headers: headers || {} }, res);
  return res;
}
async function POST(body, headers) {
  const res = mkRes();
  await handler({ method: 'POST', body: body, query: {}, headers: headers || {} }, res);
  return res;
}

const LIC_HASH = 'LIC-HASH-1';
const GOOD_TOKEN = 'dntbi_' + 'a'.repeat(64);
const GOOD_HASH = bi.hashToken(GOOD_TOKEN);
// Header values the management door reads. Both are stand-ins; the license and
// session stubs above decide the outcome, not these strings.
const MGMT_HEADERS = { authorization: 'Bearer ' + 'placeholder-license', 'x-sd-auth': 'placeholder-session' };
const OWNER_SESSION = { employee_id: 'emp-owner', role: 'owner', app: 'sairndental' };

// A practice: one owner, one linked provider, one unlinked provider.
function seed(opts) {
  opts = opts || {};
  REQUESTS = [];
  TABLES = {
    sairndental_bi_tokens: { rows: [Object.assign({
      id: 'TOK-1', license_hash: LIC_HASH, app_id: 'sairndental', token_hash: GOOD_HASH,
      label: 'Owner Power BI', employee_id: 'emp-owner', include_identifiers: false,
      created_by: 'emp-owner', revoked_at: null, last_used_at: null, use_count: 0
    }, opts.token || {})] },
    sairndental_employee_auth: { rows: [
      { license_hash: LIC_HASH, employee_id: 'emp-owner', role: 'owner', active: true },
      { license_hash: LIC_HASH, employee_id: 'emp-doc', role: 'provider', active: true },
      { license_hash: LIC_HASH, employee_id: 'emp-hyg', role: 'provider', active: true },
      { license_hash: LIC_HASH, employee_id: 'emp-gone', role: 'owner', active: false }
    ] },
    dnt_providers: { rows: [
      { license_hash: LIC_HASH, provider_id: 'PV-1', data: { id: 'PV-1', name: 'Dr Vance', role: 'Dentist', linked_employee_id: 'emp-doc', active: true, created_at: '2026-08-01' } },
      { license_hash: LIC_HASH, provider_id: 'PV-2', data: { id: 'PV-2', name: 'Dr Okafor', role: 'Dentist', active: true, created_at: '2026-08-01' } }
    ] },
    dnt_patients: { rows: [
      { license_hash: LIC_HASH, data: { id: 'PT-1', name: 'Jane Roe', dob: '1990-04-02', phone: '555-0100', insurance_payer: 'Delta', created_at: '2026-08-02' } },
      { license_hash: LIC_HASH, data: { id: 'PT-2', name: 'Sam Poe', dob: '1985-01-15', phone: '555-0199', insurance_payer: 'Aetna', created_at: '2026-08-03' } }
    ] },
    dnt_appointments: { rows: [
      { license_hash: LIC_HASH, provider_id: 'PV-1', data: { id: 'AP-1', patient_id: 'PT-1', provider_id: 'PV-1', start_time: '2026-09-03T14:00:00.000Z', status: 'Confirmed' } },
      { license_hash: LIC_HASH, provider_id: 'PV-2', data: { id: 'AP-2', patient_id: 'PT-2', provider_id: 'PV-2', start_time: '2026-09-03T15:00:00.000Z', status: 'Confirmed' } }
    ] },
    dnt_charges: { rows: [
      { license_hash: LIC_HASH, data: { id: 'CH-1', patient_id: 'PT-1', amount: 240, date: '2026-09-02' } }
    ] },
    dnt_recall_outreach: { rows: [
      { license_hash: LIC_HASH, data: { id: 'RC-1', patient_id: 'PT-1', on: '2026-09-01', channel: 'phone', outcome: 'booked' } },
      { license_hash: LIC_HASH, data: { id: 'RC-2', patient_id: 'PT-2', on: '2026-09-01', channel: 'sms', outcome: 'no answer' } }
    ] }
  };
  SESSION = null;
  LICENSE = { valid: true, active: true, license_hash: LIC_HASH, app_id: 'sairndental' };
}

// ── 1. THE FEED DOOR ───────────────────────────────────────────────────────

test('no token at all is refused', async () => {
  seed();
  const r = await GET({ dataset: 'patients' });
  assert.strictEqual(r.statusCode, 401);
  assert.strictEqual(r.body.error.code, 'NO_TOKEN');
});

test('an unknown token and a REVOKED token get the identical answer', async () => {
  seed();
  const unknown = await GET({ dataset: 'patients', token: 'dntbi_' + 'f'.repeat(64) });
  seed({ token: { revoked_at: '2026-09-01T00:00:00.000Z' } });
  const revoked = await GET({ dataset: 'patients', token: GOOD_TOKEN });
  // Telling them apart would confirm to the holder of a revoked token that it
  // was real once.
  assert.strictEqual(unknown.statusCode, 401);
  assert.strictEqual(revoked.statusCode, 401);
  assert.deepStrictEqual(unknown.body, revoked.body);
});

test('the token is accepted in an Authorization header, not only in the URL', async () => {
  seed();
  const r = await GET({ dataset: 'patients' }, { authorization: 'Bearer ' + GOOD_TOKEN });
  assert.strictEqual(r.statusCode, 200);
  assert.strictEqual(r.body.dataset, 'patients');
});

test('a license key does not authenticate the feed', async () => {
  // The two doors are disjoint on purpose: a BI token lives in a shared BI
  // workspace, and a license key must never be interchangeable with it.
  seed();
  const r = await GET({ dataset: 'patients' }, { authorization: 'Bearer ' + 'a-real-license-key-shape' });
  assert.strictEqual(r.statusCode, 401);
  assert.strictEqual(r.body.error.code, 'INVALID_TOKEN');
});

test('the feed is GET-only -- it cannot be made to write', async () => {
  seed();
  const res = mkRes();
  await handler({ method: 'DELETE', query: {}, headers: {} }, res);
  assert.strictEqual(res.statusCode, 405);
});

test('an unprovisioned deployment says so instead of returning nothing', async () => {
  seed();
  delete TABLES.sairndental_bi_tokens;
  const r = await GET({ dataset: 'patients', token: GOOD_TOKEN });
  assert.strictEqual(r.statusCode, 503);
  assert.strictEqual(r.body.error.code, 'NOT_PROVISIONED');
  assert.match(r.body.error.message, /sairndental_bi_tokens_schema\.sql/);
});

// ── 2. THE LIVE ROLE RE-READ ───────────────────────────────────────────────

test('a token whose employee has been DEACTIVATED stops working', async () => {
  // The reason the role is not snapshotted into the token row.
  seed({ token: { employee_id: 'emp-gone' } });
  const r = await GET({ dataset: 'patients', token: GOOD_TOKEN });
  assert.strictEqual(r.statusCode, 403);
  assert.strictEqual(r.body.error.code, 'EMPLOYEE_INACTIVE');
});

test('a token whose employee row is GONE stops working', async () => {
  seed({ token: { employee_id: 'emp-never-existed' } });
  const r = await GET({ dataset: 'patients', token: GOOD_TOKEN });
  assert.strictEqual(r.statusCode, 403);
  assert.strictEqual(r.body.error.code, 'EMPLOYEE_INACTIVE');
});

test('a DEMOTED employee loses the financial datasets at the next poll', async () => {
  seed();
  const before = await GET({ dataset: 'charges', token: GOOD_TOKEN });
  assert.strictEqual(before.statusCode, 200);
  // Same token, same row -- the owner is demoted to provider in the auth table.
  TABLES.sairndental_employee_auth.rows[0].role = 'provider';
  const after = await GET({ dataset: 'charges', token: GOOD_TOKEN });
  assert.strictEqual(after.statusCode, 403);
  assert.strictEqual(after.body.error.code, 'ROLE_NOT_PERMITTED');
});

// ── 3. THE FINANCIAL TIER IS ENFORCED, AND REFUSES RATHER THAN EMPTIES ─────

test('a provider asking for charges gets 403, NOT an empty 200', async () => {
  // An empty 200 renders as a real zero in a dashboard -- a fabricated figure
  // produced by a permission check. Same reasoning as api/sd-data.js:8168.
  seed({ token: { employee_id: 'emp-doc' } });
  const r = await GET({ dataset: 'charges', token: GOOD_TOKEN });
  assert.strictEqual(r.statusCode, 403);
  assert.strictEqual(r.body.error.code, 'ROLE_NOT_PERMITTED');
  assert.ok(!r.body.rows, 'rows came back with the refusal');
});

test('a provider reaches the non-financial datasets normally', async () => {
  seed({ token: { employee_id: 'emp-doc' } });
  const r = await GET({ dataset: 'appointments', token: GOOD_TOKEN });
  assert.strictEqual(r.statusCode, 200);
});

test('the catalog a provider gets lists no financial dataset', async () => {
  seed({ token: { employee_id: 'emp-doc' } });
  const r = await GET({ dataset: '_catalog', token: GOOD_TOKEN });
  assert.strictEqual(r.statusCode, 200);
  assert.strictEqual(r.body.role, 'provider');
  r.body.datasets.forEach(function (d) { assert.strictEqual(d.contains_financial_data, false); });
});

test('an unknown dataset is a 404 that names the catalog', async () => {
  seed();
  const r = await GET({ dataset: 'revenue_by_moon_phase', token: GOOD_TOKEN });
  assert.strictEqual(r.statusCode, 404);
  assert.match(r.body.error.message, /_catalog/);
});

// ── 4. PROVIDER SCOPE IS ENFORCED, AND IN THE RIGHT PLACE ─────────────────

test('a provider appointment read is narrowed IN THE DATABASE', async () => {
  seed({ token: { employee_id: 'emp-doc' } });
  const r = await GET({ dataset: 'appointments', token: GOOD_TOKEN });
  assert.strictEqual(r.statusCode, 200);
  assert.deepStrictEqual(r.body.rows.map(function (x) { return x.appointment_id; }), ['AP-1']);
  // The claim that matters: the other provider's row was never fetched. An
  // appointment blob can carry ~1.26 MB of patient photos.
  const read = REQUESTS.filter(function (q) { return q.table === 'dnt_appointments' && q.method === 'GET'; })[0];
  assert.match(read.url, /provider_id=eq\.PV-1/);
});

test('an owner appointment read is NOT narrowed', async () => {
  seed();
  const r = await GET({ dataset: 'appointments', token: GOOD_TOKEN });
  assert.deepStrictEqual(r.body.rows.map(function (x) { return x.appointment_id; }).sort(), ['AP-1', 'AP-2']);
  const read = REQUESTS.filter(function (q) { return q.table === 'dnt_appointments' && q.method === 'GET'; })[0];
  assert.ok(!/provider_id=eq/.test(read.url));
});

test('a provider sees only their own patients on a patient-scoped dataset', async () => {
  seed({ token: { employee_id: 'emp-doc' } });
  const r = await GET({ dataset: 'recall_outreach', token: GOOD_TOKEN });
  assert.strictEqual(r.statusCode, 200);
  // PV-1 treats PT-1 only. RC-2 is PT-2's and must not appear.
  assert.deepStrictEqual(r.body.rows.map(function (x) { return x.outreach_id; }), ['RC-1']);
  assert.strictEqual(r.body.total, 1, 'the total counted rows the caller may not see');
});

test('a provider sees only their own patients in the patients dataset', async () => {
  seed({ token: { employee_id: 'emp-doc' } });
  const r = await GET({ dataset: 'patients', token: GOOD_TOKEN });
  assert.strictEqual(r.body.rows.length, 1);
  assert.strictEqual(r.body.rows[0].patient_key, bi.patientKey(LIC_HASH, 'PT-1', PLACEHOLDER));
});

test('an UNLINKED provider sees nothing and is told why', async () => {
  // See-nothing, not see-everything -- and not a silent empty list either.
  seed({ token: { employee_id: 'emp-hyg' } });
  const r = await GET({ dataset: 'patients', token: GOOD_TOKEN });
  assert.strictEqual(r.statusCode, 403);
  assert.strictEqual(r.body.error.code, 'PROVIDER_NOT_LINKED');
  assert.match(r.body.error.message, /link that login/i);
});

test('an unlinked provider cannot reach appointments either', async () => {
  seed({ token: { employee_id: 'emp-hyg' } });
  const r = await GET({ dataset: 'appointments', token: GOOD_TOKEN });
  assert.strictEqual(r.statusCode, 403);
  assert.strictEqual(r.body.error.code, 'PROVIDER_NOT_LINKED');
});

// ── 5. IDENTIFIERS ─────────────────────────────────────────────────────────

test('an owner default feed carries no patient names', async () => {
  seed();
  const r = await GET({ dataset: 'patients', token: GOOD_TOKEN });
  assert.strictEqual(r.body.identifiers_included, false);
  const s = JSON.stringify(r.body);
  assert.strictEqual(s.indexOf('Jane Roe'), -1, 'a patient name reached the feed');
  assert.strictEqual(s.indexOf('555-0100'), -1, 'a phone number reached the feed');
  assert.strictEqual(s.indexOf('1990-04-02'), -1, 'a date of birth reached the feed');
  // And the pseudonym is there, so the analyst can still join.
  assert.ok(r.body.rows[0].patient_key);
});

test('the declared columns match the rows -- no phantom identifier columns', async () => {
  seed();
  const r = await GET({ dataset: 'patients', token: GOOD_TOKEN });
  const declared = r.body.columns.map(function (c) { return c.name; }).sort();
  assert.deepStrictEqual(Object.keys(r.body.rows[0]).sort(), declared);
  assert.ok(declared.indexOf('name') === -1);
});

test('a token minted WITH identifiers carries them', async () => {
  seed({ token: { include_identifiers: true } });
  const r = await GET({ dataset: 'patients', token: GOOD_TOKEN });
  assert.strictEqual(r.body.identifiers_included, true);
  assert.ok(r.body.rows.some(function (x) { return x.name === 'Jane Roe'; }));
});

// ── 6. PAGING AND THE ENVELOPE ─────────────────────────────────────────────

test('the envelope reports a total and an honest has_more', async () => {
  seed();
  const first = await GET({ dataset: 'recall_outreach', token: GOOD_TOKEN, limit: '1', offset: '0' });
  assert.strictEqual(first.body.total, 2);
  assert.strictEqual(first.body.rows.length, 1);
  assert.strictEqual(first.body.has_more, true);
  const second = await GET({ dataset: 'recall_outreach', token: GOOD_TOKEN, limit: '1', offset: '1' });
  assert.strictEqual(second.body.has_more, false);
  assert.notStrictEqual(second.body.rows[0].outreach_id, first.body.rows[0].outreach_id);
});

test('a dataset whose table does not exist reports provisioned:false, not zero rows', async () => {
  seed();
  delete TABLES.dnt_recall_outreach;
  const r = await GET({ dataset: 'recall_outreach', token: GOOD_TOKEN });
  assert.strictEqual(r.statusCode, 200);
  assert.strictEqual(r.body.provisioned, false);
  assert.deepStrictEqual(r.body.rows, []);
});

test('a successful poll stamps last_used_at on the token row', async () => {
  seed();
  await GET({ dataset: 'patients', token: GOOD_TOKEN });
  await new Promise(function (r) { setImmediate(r); });   // the stamp is fire-and-forget
  const row = TABLES.sairndental_bi_tokens.rows[0];
  assert.ok(row.last_used_at, 'the poll was not recorded');
  assert.strictEqual(row.use_count, 1);
});

// ── 7. TOKEN MANAGEMENT ────────────────────────────────────────────────────

test('minting needs a staff session, not just a license key', async () => {
  seed();
  SESSION = null;
  const r = await POST({ action: 'mint', employee_id: 'emp-owner' }, MGMT_HEADERS);
  assert.strictEqual(r.statusCode, 401);
  assert.strictEqual(r.body.error.code, 'NO_SESSION');
});

test('a front-desk session cannot mint a feed -- owner only', async () => {
  seed();
  SESSION = { employee_id: 'emp-fd', role: 'frontdesk', app: 'sairndental' };
  const r = await POST({ action: 'mint', employee_id: 'emp-owner' }, MGMT_HEADERS);
  assert.strictEqual(r.statusCode, 403);
  assert.strictEqual(r.body.error.code, 'ROLE_NOT_PERMITTED');
});

test('a provider session cannot mint a feed for themselves', async () => {
  seed();
  SESSION = { employee_id: 'emp-doc', role: 'provider', app: 'sairndental' };
  const r = await POST({ action: 'mint', employee_id: 'emp-doc' }, MGMT_HEADERS);
  assert.strictEqual(r.statusCode, 403);
});

test('the minted token is returned ONCE, and only its hash is stored', async () => {
  seed();
  SESSION = OWNER_SESSION;
  const r = await POST({ action: 'mint', employee_id: 'emp-doc', label: 'Hygiene dashboard' }, MGMT_HEADERS);
  assert.strictEqual(r.statusCode, 200);
  assert.match(r.body.token, /^dntbi_[0-9a-f]{64}$/);
  assert.strictEqual(r.body.shown_once, true);

  const stored = TABLES.sairndental_bi_tokens.rows.filter(function (x) { return x.label === 'Hygiene dashboard'; })[0];
  assert.ok(stored, 'nothing was stored');
  assert.strictEqual(stored.token_hash, bi.hashToken(r.body.token));
  // The token itself must be nowhere in the row.
  assert.strictEqual(JSON.stringify(stored).indexOf(r.body.token), -1, 'the raw token was stored');
});

test('a minted token immediately works, with the named employee scope', async () => {
  seed();
  SESSION = OWNER_SESSION;
  const m = await POST({ action: 'mint', employee_id: 'emp-doc' }, MGMT_HEADERS);
  const r = await GET({ dataset: 'appointments', token: m.body.token });
  assert.strictEqual(r.statusCode, 200);
  assert.strictEqual(r.body.role, 'provider');
  assert.deepStrictEqual(r.body.rows.map(function (x) { return x.appointment_id; }), ['AP-1']);
  // And it cannot reach money, because emp-doc cannot.
  const money = await GET({ dataset: 'charges', token: m.body.token });
  assert.strictEqual(money.statusCode, 403);
});

test('a feed cannot be minted for a deactivated login', async () => {
  seed();
  SESSION = OWNER_SESSION;
  const r = await POST({ action: 'mint', employee_id: 'emp-gone' }, MGMT_HEADERS);
  assert.strictEqual(r.statusCode, 404);
  assert.strictEqual(r.body.error.code, 'EMPLOYEE_NOT_FOUND');
});

test('include_identifiers must be exactly true to be stored as true', async () => {
  seed();
  SESSION = OWNER_SESSION;
  const r = await POST({ action: 'mint', employee_id: 'emp-owner', include_identifiers: 'yes' }, MGMT_HEADERS);
  assert.strictEqual(r.body.include_identifiers, false);
});

test('list never returns a token hash', async () => {
  seed();
  SESSION = OWNER_SESSION;
  const r = await POST({ action: 'list' }, MGMT_HEADERS);
  assert.strictEqual(r.statusCode, 200);
  assert.ok(r.body.tokens.length >= 1);
  r.body.tokens.forEach(function (t) {
    assert.ok(!('token_hash' in t), 'a token hash was listed');
    assert.ok(!('token' in t));
  });
  const q = REQUESTS.filter(function (x) { return x.table === 'sairndental_bi_tokens' && x.method === 'GET'; }).pop();
  assert.strictEqual(q.url.indexOf('token_hash'), -1, 'token_hash was selected from the database');
});

test('revoking closes the feed at the next poll', async () => {
  seed();
  const before = await GET({ dataset: 'patients', token: GOOD_TOKEN });
  assert.strictEqual(before.statusCode, 200);
  SESSION = OWNER_SESSION;
  const rev = await POST({ action: 'revoke', id: 'TOK-1' }, MGMT_HEADERS);
  assert.strictEqual(rev.statusCode, 200);
  const after = await GET({ dataset: 'patients', token: GOOD_TOKEN });
  assert.strictEqual(after.statusCode, 401);
});

test('revoking the same token twice reports NOT_FOUND, not a second success', async () => {
  seed();
  SESSION = OWNER_SESSION;
  await POST({ action: 'revoke', id: 'TOK-1' }, MGMT_HEADERS);
  const again = await POST({ action: 'revoke', id: 'TOK-1' }, MGMT_HEADERS);
  assert.strictEqual(again.statusCode, 404);
});

test('one practice cannot revoke another practice token', async () => {
  seed();
  SESSION = OWNER_SESSION;
  LICENSE = { valid: true, active: true, license_hash: 'SOME-OTHER-PRACTICE', app_id: 'sairndental' };
  const r = await POST({ action: 'revoke', id: 'TOK-1' }, MGMT_HEADERS);
  assert.strictEqual(r.statusCode, 404);
  assert.strictEqual(TABLES.sairndental_bi_tokens.rows[0].revoked_at, null, 'the token was revoked across practices');
});

test('an inactive license reaches neither door', async () => {
  seed();
  SESSION = OWNER_SESSION;
  LICENSE = { valid: true, active: false, license_hash: LIC_HASH };
  const r = await POST({ action: 'list' }, MGMT_HEADERS);
  assert.strictEqual(r.statusCode, 403);
  assert.strictEqual(r.body.error.code, 'LICENSE_INACTIVE');
});

test('a feed keeps polling after the licence lapses -- the documented limitation', async () => {
  // Asserted so the gap is a KNOWN, tested property rather than something a
  // future reader discovers and mistakes for a bug they just introduced. The
  // feed cannot check licence status: a token stores only license_hash, and
  // license_keys has no license_hash column to look one up by. See the
  // endpoint header. Not a cross-tenant hole -- every read is still filtered by
  // this practice's own hash -- but a practice that stops paying keeps its own
  // feed until the token is revoked.
  seed();
  LICENSE = { valid: true, active: false, license_hash: LIC_HASH };
  const r = await GET({ dataset: 'patients', token: GOOD_TOKEN });
  assert.strictEqual(r.statusCode, 200, 'behaviour changed -- if this is now a refusal, delete the limitation note in the header');
  // And it is still only this practice's data.
  assert.strictEqual(r.body.rows.length, 2);
  const read = REQUESTS.filter(function (q) { return q.table === 'dnt_patients'; })[0];
  assert.match(read.url, /license_hash=eq\.LIC-HASH-1/);
});

test('minting, unlike polling, DOES require an active licence', async () => {
  seed();
  SESSION = OWNER_SESSION;
  LICENSE = { valid: true, active: false, license_hash: LIC_HASH };
  const r = await POST({ action: 'mint', employee_id: 'emp-owner' }, MGMT_HEADERS);
  assert.strictEqual(r.statusCode, 403);
  assert.strictEqual(r.body.error.code, 'LICENSE_INACTIVE');
});

test('an unknown action is refused rather than treated as a read', async () => {
  seed();
  SESSION = OWNER_SESSION;
  const r = await POST({ action: 'drop_everything' }, MGMT_HEADERS);
  assert.strictEqual(r.statusCode, 400);
});

test.after(function () { global.fetch = realFetch; });
