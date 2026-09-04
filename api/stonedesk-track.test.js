// api/stonedesk-track.test.js
// Run: node api/stonedesk-track.test.js
//
// The PUBLIC half of StoneDesk's order-tracking endpoint -- the `view` action,
// reached with a token and nothing else: no session, no license key. A customer
// following a link the shop sent them.
//
// ══ WHY THIS FILE EXISTS (2026-09-03) ═════════════════════════════════════
// It had no tests at all, and it carried the same silent-null defect being
// closed in api/_lib/stonedesk-public.js the same day -- in THREE reads rather
// than one, and with worse wording than the catalog's, because two of the three
// accuse the customer:
//
//   1. sd_order_links was read with only 404/400 special-cased. A 401 from a
//      revoked service_role key, a missing GRANT or a 500 fell through to
//      `await lr.json()`, which parsed the error body into a non-array, which
//      became `link = null`, which answered 404 "This tracking link is not
//      valid. Ask the shop for a new one." The shop would then have issued a
//      new link that failed exactly the same way.
//
//   2. sd_customers was read with `cr.ok ? await cr.json() : []`, so the same
//      outage told a customer holding a valid, active link that their job was
//      "no longer on file" -- a sentence with a real-world meaning, said to
//      somebody whose countertop is in fabrication.
//
//   3. sd_public_shop was read the same way. That one is STILL non-fatal and
//      deliberately so -- the stage is what the customer came for and a shop
//      may legitimately have no published profile -- but it is now logged, so
//      a failing read is no longer indistinguishable from an empty one.
//
// The revocation and enumeration defences are asserted here too, because the
// fix above adds branches directly beside them and they must not move: a
// revoked link and a guessed one still answer identically.

'use strict';
const assert = require('assert');
const path = require('path');

const HANDLER = path.join(__dirname, 'stonedesk-track.js');
const TOKEN = 'a'.repeat(64);

let passed = 0;
async function test(name, fn) {
  try { await fn(); passed++; console.log('  ok - ' + name); }
  catch (e) { console.error('  FAIL - ' + name + '\n    ' + e.message); process.exitCode = 1; }
}

function res(status, json) {
  return { ok: status >= 200 && status < 300, status: status, json: async () => json };
}
function mkReq(body) {
  return { method: 'POST', headers: {}, socket: {}, body: body };
}
function mkRes() {
  const out = { code: null, body: null };
  const r = {
    setHeader: function () { return r; },
    status: function (c) { out.code = c; return r; },
    json: function (b) { out.body = b; return r; },
    end: function () { return r; },
    out: out
  };
  return r;
}

function router(spec) {
  return async function (url, init) {
    const u = String(url);
    const key = ['sd_order_links', 'sd_customers', 'sd_public_shop']
      .find(function (t) { return u.indexOf(t) !== -1; });
    // The access-log PATCH is fire-and-forget on the same table as the read;
    // it must never be the thing that decides the answer.
    if (key === 'sd_order_links' && init && init.method === 'PATCH') return res(204, null);
    const entry = spec[key];
    if (typeof entry === 'function') return entry(u, init);
    if (entry === undefined) throw new Error('test fetch router has no answer for ' + key);
    return entry;
  };
}

function baseSpec() {
  return {
    sd_order_links: res(200, [{ id: 'L1', license_hash: 'hash-1', job_id: 'C-9', label: 'Kitchen', active: true }]),
    sd_customers: res(200, [{ data: { name: 'A. Customer', project: 'Kitchen', material: 'Quartzite', status: 'fabricating' } }]),
    sd_public_shop: res(200, [{ data: { shop_name: 'Main Street Stone', phone: '555-0100' } }])
  };
}

function loadHandler(fetchImpl) {
  process.env.SUPABASE_URL = 'https://test.supabase.co';
  process.env.SUPABASE_SERVICE_ROLE_KEY = 'test-key';
  global.fetch = fetchImpl;
  delete require.cache[require.resolve(HANDLER)];
  return require(HANDLER);
}

async function view(spec, token) {
  const h = loadHandler(router(spec));
  const r = mkRes();
  await h(mkReq({ action: 'view', token: token === undefined ? TOKEN : token }), r);
  return r.out;
}

async function main() {
  console.log('api/stonedesk-track.js -- a dead store is never a bad link, and never a deleted job');

  // ── the happy path ──────────────────────────────────────────────────────
  await test('a valid active token returns the stage and the shop contact', async () => {
    const o = await view(baseSpec());
    assert.strictEqual(o.code, 200);
    assert.strictEqual(o.body.stage, 'fabricating');
    assert.strictEqual(o.body.stage_known, true);
    assert.strictEqual(o.body.shop.phone, '555-0100');
  });

  await test('an unrecognised stage is reported as unrecognised, never given an invented label', async () => {
    const spec = baseSpec();
    spec.sd_customers = res(200, [{ data: { name: 'A', status: 'polishing' } }]);
    const o = await view(spec);
    assert.strictEqual(o.body.stage, 'polishing');
    assert.strictEqual(o.body.stage_known, false);
    assert.strictEqual(o.body.stage_text, '');
  });

  await test('the quote amount and internal notes never leave the building', async () => {
    const spec = baseSpec();
    spec.sd_customers = res(200, [{ data: {
      name: 'A', project: 'Kitchen', status: 'quoted',
      quote_amount: 8400, notes: 'chased twice', referral_source: 'Houzz', satisfaction: 3
    } }]);
    const o = await view(spec);
    assert.deepStrictEqual(Object.keys(o.body).sort(),
      ['customer_name', 'material', 'ok', 'project', 'shop', 'stage', 'stage_known', 'stage_text']);
  });

  // ── the defences that must not move ─────────────────────────────────────
  await test('a malformed token is refused without touching the database', async () => {
    let called = false;
    const h = loadHandler(async () => { called = true; return res(200, []); });
    const r = mkRes();
    await h(mkReq({ action: 'view', token: 'not-a-token' }), r);
    assert.strictEqual(r.out.code, 404);
    assert.strictEqual(called, false);
  });

  await test('a revoked link and a token that never existed answer identically', async () => {
    const revoked = baseSpec();
    revoked.sd_order_links = res(200, [{ id: 'L1', license_hash: 'hash-1', job_id: 'C-9', active: false }]);
    const missing = baseSpec();
    missing.sd_order_links = res(200, []);
    const a = await view(revoked);
    const b = await view(missing);
    assert.deepStrictEqual([a.code, a.body], [b.code, b.body],
      'a revoked link is distinguishable from a guess');
    assert.strictEqual(a.code, 404);
  });

  await test('a shop that has not run the migration says so, and does not accuse the customer', async () => {
    for (const status of [404, 400]) {
      const spec = baseSpec();
      spec.sd_order_links = res(status, { message: 'Could not find the table' });
      const o = await view(spec);
      assert.strictEqual(o.code, 503, 'HTTP ' + status);
      assert.strictEqual(o.body.error.code, 'NOT_PROVISIONED');
    }
  });

  // ── defect 1 ────────────────────────────────────────────────────────────
  for (const status of [401, 403, 500, 503]) {
    await test('link read fails (HTTP ' + status + ') -> 502 UPSTREAM, NOT "your link is not valid"', async () => {
      const spec = baseSpec();
      spec.sd_order_links = res(status, { message: 'JWT expired' });
      const o = await view(spec);
      assert.strictEqual(o.code, 502, 'a dead store told the customer their link was invalid');
      assert.strictEqual(o.body.error.code, 'UPSTREAM');
    });
  }

  await test('link read returns a non-array on a 200 -> 502, not a silent "no such token"', async () => {
    const spec = baseSpec();
    spec.sd_order_links = res(200, { message: 'something unexpected' });
    const o = await view(spec);
    assert.strictEqual(o.code, 502);
    assert.strictEqual(o.body.error.code, 'UPSTREAM');
  });

  // ── defect 2 ────────────────────────────────────────────────────────────
  for (const status of [401, 403, 500]) {
    await test('customer read fails (HTTP ' + status + ') -> 502, NOT "that job is no longer on file"', async () => {
      const spec = baseSpec();
      spec.sd_customers = res(status, { message: 'nope' });
      const o = await view(spec);
      assert.strictEqual(o.code, 502,
        'a customer with a job in fabrication was told it had been deleted');
      assert.strictEqual(o.body.error.code, 'UPSTREAM');
    });
  }

  await test('a job that really is gone is STILL a 404 -- the fix did not swallow the real case', async () => {
    const spec = baseSpec();
    spec.sd_customers = res(200, []);
    const o = await view(spec);
    assert.strictEqual(o.code, 404);
    assert.strictEqual(o.body.error.code, 'NOT_FOUND');
  });

  // ── defect 3, deliberately still non-fatal ──────────────────────────────
  await test('a failed shop-profile read still shows the customer their stage', async () => {
    const spec = baseSpec();
    spec.sd_public_shop = res(500, { message: 'nope' });
    const o = await view(spec);
    assert.strictEqual(o.code, 200,
      'a decorative field took the whole status page down');
    assert.strictEqual(o.body.stage, 'fabricating');
    assert.deepStrictEqual(o.body.shop, { name: '', phone: '' });
  });

  await test('a shop with no published profile is indistinguishable from one, by design', async () => {
    const spec = baseSpec();
    spec.sd_public_shop = res(200, []);
    const o = await view(spec);
    assert.strictEqual(o.code, 200);
    assert.deepStrictEqual(o.body.shop, { name: '', phone: '' });
  });

  // ── the access log must never decide the answer ─────────────────────────
  await test('a failed access-log write does not deny a customer their status', async () => {
    const spec = baseSpec();
    const h = loadHandler(async function (url, init) {
      if (String(url).indexOf('sd_order_links') !== -1 && init && init.method === 'PATCH') {
        throw new Error('EHOSTUNREACH');
      }
      return router(spec)(url, init);
    });
    const r = mkRes();
    await h(mkReq({ action: 'view', token: TOKEN }), r);
    assert.strictEqual(r.out.code, 200);
  });

  // ── the private actions still need a session ────────────────────────────
  await test('create, revoke and list all refuse an anonymous caller', async () => {
    for (const action of ['create', 'revoke', 'list']) {
      const h = loadHandler(router(baseSpec()));
      const r = mkRes();
      await h(mkReq({ action: action }), r);
      assert.strictEqual(r.out.code, 401, action + ' did not require a license key');
      assert.strictEqual(r.out.body.error.code, 'NO_LICENSE');
    }
  });

  console.log('\n' + passed + ' assertions passed' + (process.exitCode ? ', see failures above' : ''));
}

main();
