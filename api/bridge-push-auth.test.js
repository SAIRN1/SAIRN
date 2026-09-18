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
    // COLUMN RENAMED shop_id -> license_hash by
    // sql/bridge_data_rekey_2026-09-18.sql. Both spellings are asserted: the
    // new one must carry the hash, and the OLD one must be GONE. Without the
    // second half this arm would pass on a handler writing both, which is the
    // half-applied rename that leaves a column holding a secret behind.
    assert.strictEqual(row.license_hash, 'hash-of-shop-a',
      'the write was keyed on a value the caller supplied: ' + row.license_hash);
    assert.strictEqual(row.shop_id, undefined,
      'the old shop_id column is still being written -- the rename is half applied');
    assert.ok(!JSON.stringify(sent).includes('SD-SOMEBODY-ELSES-LICENCE'),
      'the body shopId reached the row');
    // THE UPSERT TARGET MUST BE RENAMED WITH THE COLUMN, and nothing asserted
    // it until 2026-09-18 -- a mutation that left `on_conflict=shop_id` behind
    // came back SILENT. It is not cosmetic: on_conflict naming a column the
    // table no longer has makes PostgREST refuse every push, and naming the
    // wrong existing one would INSERT a second row per shop instead of merging.
    assert.match(r.upserts[0].url, /on_conflict=license_hash(&|$)/,
      'the upsert conflict target was not renamed with the column: ' + r.upserts[0].url);
    assert.ok(!/on_conflict=shop_id/.test(r.upserts[0].url),
      'the old conflict target survives');
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


  // == proxy_get: THE UNTRUSTED PARSE IS ISOLATED BEFORE IT IS TRUSTED =====
  // The platform's most exposed untrusted-input path: any caller, no licence,
  // a third-party body parsed into the app. The allowlist bounds WHO answers,
  // not what they say or how long they take.
  const RESIL = require('./_lib/resilience.js');

  function withUpstream(impl, fn) {
    const saved = global.fetch;
    global.fetch = impl;
    return fn().finally(function () { global.fetch = saved; });
  }

  async function proxy() {
    const res = mockRes();
    await handler({ method: 'POST', url: '/api/bridge', headers: {},
                    body: { data_type: 'proxy_get',
                            payload: { url: 'https://api.stlouisfed.org/series' } } }, res);
    return { status: res._s, body: res._j };
  }

  function upstreamOf(text, headers) {
    const h = headers || {};
    return async function () {
      return {
        ok: true, status: 200,
        headers: { get: function (k) { return h[String(k).toLowerCase()] || null; } },
        text: async function () { return text; },
        body: null
      };
    };
  }

  await t('proxy_get: a NORMAL upstream body still works -- the bounds are not '
    + 'a refusal of everything', async () => {
      await withUpstream(upstreamOf('{"observations":[1,2,3]}'), async () => {
        const r = await proxy();
        assert.strictEqual(r.status, 200, JSON.stringify(r.body));
        assert.deepStrictEqual(r.body.result.observations, [1, 2, 3]);
      });
    });

  await t('proxy_get: an OVERSIZE body is REFUSED, not truncated', async () => {
      // Truncation is the dangerous option: a cut-off JSON body either fails to
      // parse or parses as a valid SMALLER structure, which is silently wrong.
      const huge = 'x'.repeat(3 * 1024 * 1024);
      await withUpstream(upstreamOf(huge), async () => {
        const r = await proxy();
        assert.strictEqual(r.status, 502, JSON.stringify(r.body));
        assert.strictEqual(r.body.error.code, 'UPSTREAM_TOO_LARGE');
      });
    });

  await t('proxy_get: a LYING content-length does not get past the reader',
    async () => {
      // The header is a claim by the same party whose body is in question.
      const huge = 'x'.repeat(3 * 1024 * 1024);
      await withUpstream(upstreamOf(huge, { 'content-length': '10' }), async () => {
        const r = await proxy();
        assert.strictEqual(r.body.error.code, 'UPSTREAM_TOO_LARGE',
          'a small declared length let an enormous body through');
      });
    });

  await t('proxy_get: an honest oversize content-length is refused BEFORE the '
    + 'body is read at all', async () => {
      let read = false;
      await withUpstream(async function () {
        return {
          ok: true, status: 200,
          headers: { get: function (k) {
            return String(k).toLowerCase() === 'content-length'
              ? String(9 * 1024 * 1024) : null;
          } },
          text: async function () { read = true; return 'x'; },
          body: null
        };
      }, async () => {
        const r = await proxy();
        assert.strictEqual(r.body.error.code, 'UPSTREAM_TOO_LARGE');
        assert.strictEqual(read, false, 'the body was read despite the declaration');
      });
    });

  await t('proxy_get: TEETH -- the guard really is in the path, so the arms '
    + 'above are not passing on a code path nobody uses', async () => {
      // ORDERED BEFORE THE HANG ARM ON PURPOSE, and that order was chosen
      // after a sabotage proved it mattered: removing the guard made the
      // hanging-upstream arm STALL, so the suite never reached this one and
      // reported no failure at all. A hang that masks a failure is worse than
      // the failure. This arm is cheap, it does not touch the network, and it
      // goes red immediately if the wiring is gone.
      const src = require('fs').readFileSync(
        require('path').join(__dirname, 'bridge.js'), 'utf8');
      assert.ok(src.indexOf('RESIL.guardedFetch(') !== -1,
        'proxy_get no longer goes through the guard');
      assert.ok(src.indexOf("createBulkhead('bridge:proxy_get'") !== -1,
        'the bulkhead is gone');
      assert.ok(RESIL.TimeoutError && RESIL.BulkheadFullError,
        'resilience no longer exports the refusals bridge.js catches');
    });


  function streamingUpstream(totalBytes, chunk) {
    // EXERCISES THE READER PATH. The fakes above hand back `text()` with a null
    // body, which takes readCapped's non-stream branch -- so the per-chunk cap
    // and the refuse-rather-than-truncate rule were both untested until a
    // sabotage removed them and killed nothing.
    const size = chunk || 64 * 1024;
    let sent = 0;
    return async function () {
      return {
        ok: true, status: 200,
        headers: { get: function () { return null; } },
        text: async function () { throw new Error('text() must not be used when a body exists'); },
        body: {
          getReader: function () {
            return {
              read: async function () {
                if (sent >= totalBytes) return { done: true, value: undefined };
                const n = Math.min(size, totalBytes - sent);
                sent += n;
                return { done: false, value: new Uint8Array(n) };
              },
              cancel: async function () { sent = totalBytes; }
            };
          }
        }
      };
    };
  }

  await t('proxy_get: a STREAMED oversize body is refused mid-read, with no '
    + 'content-length to warn us', async () => {
      await withUpstream(streamingUpstream(3 * 1024 * 1024), async () => {
        const r = await proxy();
        assert.strictEqual(r.status, 502, JSON.stringify(r.body));
        assert.strictEqual(r.body.error.code, 'UPSTREAM_TOO_LARGE',
          'the streaming reader let an oversize body through');
      });
    });

  await t('proxy_get: ...and it REFUSES rather than truncating -- a cut-off '
    + 'body parses as a valid smaller structure', async () => {
      await withUpstream(streamingUpstream(3 * 1024 * 1024), async () => {
        const r = await proxy();
        assert.notStrictEqual(r.status, 200,
          'an oversize stream was truncated and returned as a 200, which is '
          + 'silently wrong rather than loudly refused');
      });
    });

  await t('proxy_get: a STREAMED body UNDER the cap still comes through', () =>
    withUpstream(streamingUpstream(1024), async () => {
      const r = await proxy();
      assert.strictEqual(r.status, 200, JSON.stringify(r.body));
    }));

  await t('proxy_get: a HANGING upstream times out instead of holding the '
    + 'function to the platform limit', async () => {
      // THE FAKE HONOURS THE ABORT SIGNAL, and it has to. withTimeout() aborts a
      // controller and relies on the fetch implementation to reject on it --
      // real fetch does. A fake that ignored the signal would HANG rather than
      // fail, which is a test that proves nothing and looks like a pass.
      await withUpstream(function (u, opts) {
        return new Promise(function (_resolve, reject) {
          const sig = opts && opts.signal;
          if (sig) {
            if (sig.aborted) return reject(Object.assign(new Error('aborted'), { name: 'AbortError' }));
            sig.addEventListener('abort', function () {
              reject(Object.assign(new Error('aborted'), { name: 'AbortError' }));
            }, { once: true });
          }
        });
      }, async () => {
        const r = await proxy();
        assert.strictEqual(r.status, 504, JSON.stringify(r.body));
        assert.strictEqual(r.body.error.code, 'UPSTREAM_TIMEOUT');
      });
    });

  global.fetch = realFetch;
  console.log('\nbridge push auth: ' + pass + ' passed, ' + fail + ' failed');
  if (fail) process.exit(1);
})();
