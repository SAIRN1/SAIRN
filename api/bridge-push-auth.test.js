// api/bridge-push-auth.test.js
//
// Run:  node api/bridge-push-auth.test.js
//
// REQUIREMENT: api/bridge.js's `push` writes only the row the caller's LICENCE
// proves it owns, and never a row named in the request body.
//
// ── WHY THIS EXISTS ────────────────────────────────────────────────────────
// Until 2026-09-17 `push` took `shopId` from the BODY with no Authorization
// header of any kind, and stonedesk.html's `sdShopId()` is
// `return sdLicenseKey()` -- so `bridge_data.shop_id` was the customer's RAW
// LICENCE KEY and anyone could overwrite any shop's row by naming it. The read
// side (`?action=pull`) had the mirror defect and was removed the same day; it
// had no callers, which is the only reason removal was the right answer there
// and is not the right answer here.
//
// THE FILE'S OWN HEADER HAD ALREADY NAMED THE LIMIT AND LOST IT: "NOT fine for
// personal or financial data". StoneDesk's crSendToBridge pushes expense
// invoices carrying payee, amount, memo and a GL account. A rule that names its
// own boundary and is not enforced does not hold the boundary.
//
// Every arm drives the real exported handler. The licence module is stubbed for
// the reason api/claude-cost-controls.test.js states: on a developer machine
// SUPABASE_URL is unset, so a suite written against the real one would pass
// whether the auth logic is right or wrong.

'use strict';
const assert = require('assert');
const path = require('path');

const LICENCE = require.resolve('./_lib/license');
let licenceAnswer = { valid: true, active: true, license_hash: 'hash-of-shop-a' };
let licenceThrows = false;
let licenceSeen = [];
require.cache[LICENCE] = {
  id: LICENCE, filename: LICENCE, loaded: true,
  exports: {
    validateLicenseKey: async (k) => {
      licenceSeen.push(k);
      if (licenceThrows) throw new Error('licence store unreachable');
      return licenceAnswer;
    },
  },
};

process.env.SUPABASE_URL = 'https://example.invalid';
process.env.SUPABASE_SERVICE_ROLE_KEY = 'service-role-for-the-test';

const handler = require('./bridge.js');

// The upsert the handler makes, captured rather than sent.
let upserts = [];
const realFetch = global.fetch;
global.fetch = async (url, opts) => {
  upserts.push({ url: String(url), body: opts && opts.body });
  return { ok: true, status: 200, json: async () => ([{ shop_id: 'x' }]),
           text: async () => '[]' };
};

function mockRes() {
  const r = { _s: 0, _j: null };
  r.status = (s) => { r._s = s; return r; };
  r.json = (j) => { r._j = j; return r; };
  return r;
}

async function push(body, authHeader) {
  upserts = [];
  licenceSeen = [];
  const headers = authHeader ? { authorization: authHeader } : {};
  const res = mockRes();
  await handler({ method: 'POST', url: '/api/bridge?action=push', headers, body }, res);
  return { status: res._s, body: res._j, upserts: upserts.slice(),
           licenceSeen: licenceSeen.slice() };
}

let pass = 0, fail = 0;
function t(name, fn) {
  return fn().then(() => { console.log('  ok   ' + name); pass++; })
    .catch((e) => { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; });
}

const PAYLOAD = { shopId: 'SD-SOMEBODY-ELSES-LICENCE', invoices: [{ id: 'i1', amount: 10 }] };

(async () => {
  console.log('api/bridge.js -- push authorization');

  await t('NO Authorization header is refused, and nothing is written', async () => {
    const r = await push(PAYLOAD, null);
    assert.strictEqual(r.status, 401, JSON.stringify(r.body));
    assert.strictEqual(r.body.error.code, 'NO_LICENCE');
    assert.strictEqual(r.upserts.length, 0, 'an unauthenticated push still wrote');
  });

  await t('THE ROW IS KEYED ON license_hash, NOT on the body shopId', async () => {
    // The arm this file exists for. `shopId` in the body names somebody else's
    // licence; the write must land on the caller's own hash.
    const r = await push(PAYLOAD, 'Bearer SD-MY-OWN-LICENCE');
    assert.strictEqual(r.status, 200, JSON.stringify(r.body));
    assert.strictEqual(r.upserts.length, 1);
    const sent = JSON.parse(r.upserts[0].body);
    const row = Array.isArray(sent) ? sent[0] : sent;
    assert.strictEqual(row.shop_id, 'hash-of-shop-a',
      'the write was keyed on a value the caller supplied: ' + row.shop_id);
    assert.ok(!JSON.stringify(sent).includes('SD-SOMEBODY-ELSES-LICENCE'),
      'the body shopId reached the row');
  });

  await t('...and the RAW LICENCE KEY never reaches the row either', async () => {
    const r = await push(PAYLOAD, 'Bearer SD-MY-OWN-LICENCE');
    assert.ok(!JSON.stringify(r.upserts).includes('SD-MY-OWN-LICENCE'),
      'the raw licence key was stored, which is the defect the read side had');
  });

  await t('the licence that gets validated is the one from the header', async () => {
    const r = await push(PAYLOAD, 'Bearer SD-MY-OWN-LICENCE');
    assert.deepStrictEqual(r.licenceSeen, ['SD-MY-OWN-LICENCE'], r.licenceSeen);
  });

  await t('an INVALID licence is refused', async () => {
    const prev = licenceAnswer;
    licenceAnswer = { valid: false, active: false, license_hash: null };
    try {
      const r = await push(PAYLOAD, 'Bearer SD-NOT-A-LICENCE');
      assert.strictEqual(r.status, 403, JSON.stringify(r.body));
      assert.strictEqual(r.upserts.length, 0);
    } finally { licenceAnswer = prev; }
  });

  await t('A WRITE PATH FAILS CLOSED when the licence store is unreachable',
    async () => {
      // Deliberately the opposite of the read-side convention elsewhere on this
      // platform. Allowing an unverified WRITE because the licence store
      // blinked lets the outage do the thing the gate exists to prevent.
      licenceThrows = true;
      try {
        const r = await push(PAYLOAD, 'Bearer SD-MY-OWN-LICENCE');
        assert.strictEqual(r.status, 503, JSON.stringify(r.body));
        assert.strictEqual(r.body.error.code, 'LICENCE_UNCHECKED');
        assert.strictEqual(r.upserts.length, 0, 'it wrote anyway');
      } finally { licenceThrows = false; }
    });

  await t('TEETH -- a VALID licence with a working store does write, so the '
    + 'refusals above are not just "this endpoint never writes"', async () => {
      const r = await push(PAYLOAD, 'Bearer SD-MY-OWN-LICENCE');
      assert.strictEqual(r.status, 200, JSON.stringify(r.body));
      assert.strictEqual(r.upserts.length, 1);
    });

  await t('the READ SIDE IS STILL GONE -- a GET answers 405 and reads nothing',
    async () => {
      upserts = [];
      const res = mockRes();
      await handler({ method: 'GET', url: '/api/bridge?action=pull&shopId=x',
                      headers: {}, body: null }, res);
      assert.strictEqual(res._s, 405, JSON.stringify(res._j));
      assert.strictEqual(res._j.error.code, 'NO_READ_SIDE');
    });

  await t('proxy_get is UNTOUCHED by this -- it needs no licence and is the '
    + 'only action with real live callers', async () => {
      // sairnbuild's FRED fetch and stonedesk's map calls go through it. If
      // requiring a licence had leaked into this path they would all break.
      upserts = [];
      const res = mockRes();
      await handler({ method: 'POST', url: '/api/bridge', headers: {},
                      body: { data_type: 'proxy_get',
                              payload: { url: 'https://api.stlouisfed.org/x' } } }, res);
      assert.notStrictEqual(res._s, 401, 'proxy_get now demands a licence');
    });

  global.fetch = realFetch;
  console.log('\nbridge push auth: ' + pass + ' passed, ' + fail + ' failed');
  if (fail) process.exit(1);
})();
