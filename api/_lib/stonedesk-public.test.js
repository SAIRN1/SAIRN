// api/_lib/stonedesk-public.test.js
// Run: node api/_lib/stonedesk-public.test.js
//
// StoneDesk's public, unauthenticated storefront: the slab and remnant catalog
// and the quote-request form. Nobody signs in to reach any of it.
//
// This is the SIBLING of api/_lib/dental-public.test.js. SAIRNdental's copy of
// these helpers was fixed on 2026-09-03; this file had been written from the
// same template the same week and carried the same defects, which is the whole
// reason to look. api/stonedesk-public.test.js already covers the pure
// decidable rules (what may leave the building); this covers what happens when
// the DATABASE ANSWERS BADLY, which needs a mocked fetch and so lives apart.
//
// ══ THE THREE SILENT FAILURES THIS HOLDS CLOSED ═══════════════════════════
//
//   1. resolveShopSlug() did `if (!r.ok) return null`, and the caller renders
//      null as 404 "No published catalog at this address". So a revoked
//      service_role key, an unreachable database or a missing GRANT told a
//      customer that the shop whose link they had just followed did not exist
//      -- no error, no 502, no log line.
//
//      The header on the lib explains, correctly, that an unknown slug and an
//      unpublished shop deliberately give the SAME answer so nobody can
//      enumerate shops. That covers two states a visitor may not tell apart.
//      It never covered a third state where the server could not ask at all,
//      and that one was quietly folded in with them.
//
//   2. checkAndIncrementRateLimit() read the counter with
//      `existing.ok ? await existing.json() : []`, so an unreachable store read
//      as count 0 and allowed everything.
//
//   3. The increment was `await fetch(...)` with NO .ok CHECK AT ALL. A failed
//      write meant the counter never rose, so the read kept returning 0 and the
//      limit could never re-engage for that window. This is the worst of the
//      three: the read succeeds, so nothing anywhere looks wrong.
//
// Together, 2 and 3 meant the limiter guarding 5 quote requests per hour --
// an unauthenticated WRITE into a shop's lead table, reachable by anyone who
// knows a public slug -- could be entirely absent while reporting nothing.
//
// ══ AND A FOURTH, FOUND HERE RATHER THAN INHERITED ════════════════════════
//
//   4. The catalog's remnant fetch was `if (rr.ok) { ... }` with no else, which
//      was written to tolerate ONE failure -- a shop that has not run the
//      sd_remnants migration -- and silently tolerated every other one too. A
//      401, a missing GRANT or a 500 rendered the storefront with the remnant
//      section simply gone: a published, for-sale inventory absent, with
//      nothing said to the visitor and nothing logged for the shop.

'use strict';
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const Module = require('module');

const LIB = path.join(__dirname, 'stonedesk-public.js');
const HANDLER = path.join(__dirname, '..', 'stonedesk-public.js');

let passed = 0;
async function test(name, fn) {
  try { await fn(); passed++; console.log('  ok - ' + name); }
  catch (e) { console.error('  FAIL - ' + name + '\n    ' + e.message); process.exitCode = 1; }
}

function res(status, json) {
  return { ok: status >= 200 && status < 300, status: status, json: async () => json };
}

function load(fetchImpl) {
  process.env.SUPABASE_URL = 'https://test.supabase.co';
  process.env.SUPABASE_SERVICE_ROLE_KEY = 'test-key';
  global.fetch = fetchImpl;
  delete require.cache[require.resolve(LIB)];
  return require(LIB);
}

function loadHandler(fetchImpl) {
  process.env.SUPABASE_URL = 'https://test.supabase.co';
  process.env.SUPABASE_SERVICE_ROLE_KEY = 'test-key';
  global.fetch = fetchImpl;
  delete require.cache[require.resolve(LIB)];
  delete require.cache[require.resolve(HANDLER)];
  return require(HANDLER);
}

const REQ_HEADERS = { 'x-forwarded-for': '203.0.113.9' };

function mkReq(body) {
  return { method: 'POST', headers: REQ_HEADERS, socket: {}, body: body };
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

// A fetch router keyed on the table in the URL, so a test says what each table
// answers and nothing depends on call order.
function router(spec) {
  return async function (url, init) {
    const method = (init && init.method) || 'GET';
    const u = String(url);
    const key = ['sd_public_rate_limits', 'sd_public_shop', 'sd_slabs', 'sd_remnants', 'sd_quote_requests']
      .find(function (t) { return u.indexOf(t) !== -1; });
    const entry = spec[key === 'sd_public_rate_limits' && method === 'POST' ? 'rate_write' : key];
    if (typeof entry === 'function') return entry(u, init);
    if (entry === undefined) throw new Error('test fetch router has no answer for ' + key + ' (' + method + ')');
    return entry;
  };
}

// The happy-path answers a test overrides one of.
function baseSpec() {
  return {
    sd_public_rate_limits: res(200, [{ count: 1 }]),
    rate_write: res(201, {}),
    sd_public_shop: res(200, [{ license_hash: 'hash-1', shop_slug: 'main-street-stone', data: { shop_name: 'Main Street Stone' } }]),
    sd_slabs: res(200, [{ data: { id: 'S1', material: 'granite', published: true } }]),
    sd_remnants: res(200, []),
    sd_quote_requests: res(201, {})
  };
}

async function main() {
  console.log('api/_lib/stonedesk-public.js -- a dead store is never an unknown shop, and never an open door');

  // ── 1. resolveShopSlug ──────────────────────────────────────────────────
  await test('a real published slug resolves to its license hash', async () => {
    const lib = load(async () => res(200, [{ license_hash: 'hash-1', shop_slug: 'main-street-stone', data: { shop_name: 'Main Street Stone' } }]));
    const shop = await lib.resolveShopSlug('main-street-stone');
    assert.strictEqual(shop.licenseHash, 'hash-1');
    assert.strictEqual(shop.slug, 'main-street-stone');
    assert.strictEqual(shop.data.shop_name, 'Main Street Stone');
  });

  await test('a genuine miss is still null, so a wrong link is still a 404', async () => {
    const lib = load(async () => res(200, []));
    assert.strictEqual(await lib.resolveShopSlug('no-such-shop'), null);
  });

  await test('an unpublished shop is still null -- the enumeration defence is unchanged', async () => {
    // published=eq.true is in the query string, so the store returns no rows.
    // Asserted explicitly because the fix below deliberately did NOT touch it.
    const lib = load(async (url) => {
      assert.match(String(url), /published=eq\.true/);
      return res(200, []);
    });
    assert.strictEqual(await lib.resolveShopSlug('quiet-shop'), null);
  });

  await test('an empty slug is null without touching the database', async () => {
    let called = false;
    const lib = load(async () => { called = true; return res(200, []); });
    assert.strictEqual(await lib.resolveShopSlug(''), null);
    assert.strictEqual(called, false);
  });

  await test('a row with no license_hash is null rather than a shop with an undefined hash', async () => {
    const lib = load(async () => res(200, [{ shop_slug: 'main-street-stone' }]));
    assert.strictEqual(await lib.resolveShopSlug('main-street-stone'), null);
  });

  for (const status of [401, 403, 404, 500, 503]) {
    await test('HTTP ' + status + ' from the store THROWS -- it must not read as an unclaimed slug', async () => {
      const lib = load(async () => res(status, { message: 'nope' }));
      await assert.rejects(() => lib.resolveShopSlug('main-street-stone'), (e) => {
        assert.strictEqual(e.code, 'UPSTREAM');
        assert.match(e.message, /slug lookup failed/);
        return true;
      });
    });
  }

  // ── 2 + 3. the rate limiter ─────────────────────────────────────────────
  await test('under the limit: allowed, counted, and the increment is written', async () => {
    const calls = [];
    const lib = load(async (url, init) => {
      calls.push((init && init.method) || 'GET');
      return ((init && init.method) === 'POST') ? res(201, {}) : res(200, [{ count: 2 }]);
    });
    const r = await lib.checkAndIncrementRateLimit(mkReq({}), 10, 120, 'catalog');
    assert.deepStrictEqual({ allowed: r.allowed, count: r.count }, { allowed: true, count: 3 });
    assert.deepStrictEqual(calls, ['GET', 'POST']);
  });

  await test('over the limit: refused as LIMITED, and no increment is written', async () => {
    const calls = [];
    const lib = load(async (url, init) => {
      calls.push((init && init.method) || 'GET');
      return res(200, [{ count: 5 }]);
    });
    const r = await lib.checkAndIncrementRateLimit(mkReq({}), 60, 5, 'quote');
    assert.strictEqual(r.allowed, false);
    assert.strictEqual(r.limited, true, 'a real limit must be distinguishable from an outage');
    assert.ok(!r.unavailable);
    assert.deepStrictEqual(calls, ['GET'], 'a refused request still wrote to the counter');
  });

  // Defect 2.
  for (const status of [401, 403, 500, 503]) {
    await test('counter READ fails (HTTP ' + status + ') -> UNAVAILABLE, not allowed', async () => {
      const lib = load(async () => res(status, { message: 'nope' }));
      const r = await lib.checkAndIncrementRateLimit(mkReq({}), 60, 5, 'quote');
      assert.strictEqual(r.allowed, false, 'an unreachable counter allowed the request');
      assert.strictEqual(r.unavailable, true);
      assert.ok(!r.limited, 'an outage must not be reported as a rate limit');
    });
  }

  await test('counter read THROWS -> UNAVAILABLE rather than an unhandled error', async () => {
    const lib = load(async () => { throw new Error('ECONNRESET'); });
    const r = await lib.checkAndIncrementRateLimit(mkReq({}), 60, 5, 'quote');
    assert.deepStrictEqual({ allowed: r.allowed, unavailable: r.unavailable }, { allowed: false, unavailable: true });
  });

  await test('counter read returns something that is not an array -> UNAVAILABLE, not count 0', async () => {
    const lib = load(async () => res(200, { unexpected: true }));
    const r = await lib.checkAndIncrementRateLimit(mkReq({}), 60, 5, 'quote');
    assert.strictEqual(r.unavailable, true);
  });

  // Defect 3 -- the one that had no check at all.
  for (const status of [401, 403, 409, 500]) {
    await test('counter INCREMENT fails (HTTP ' + status + ') -> UNAVAILABLE, not a silent allow', async () => {
      const lib = load(async (url, init) =>
        ((init && init.method) === 'POST') ? res(status, { message: 'nope' }) : res(200, [{ count: 0 }]));
      const r = await lib.checkAndIncrementRateLimit(mkReq({}), 60, 5, 'quote');
      assert.strictEqual(r.allowed, false,
        'an uncounted request was allowed -- the limit can never engage while the write keeps failing');
      assert.strictEqual(r.unavailable, true);
    });
  }

  await test('counter increment THROWS -> UNAVAILABLE', async () => {
    const lib = load(async (url, init) => {
      if ((init && init.method) === 'POST') throw new Error('ETIMEDOUT');
      return res(200, [{ count: 0 }]);
    });
    const r = await lib.checkAndIncrementRateLimit(mkReq({}), 60, 5, 'quote');
    assert.strictEqual(r.unavailable, true);
  });

  await test('a first-ever request for an IP starts at 1, not at NaN or 0', async () => {
    const lib = load(async (url, init) => ((init && init.method) === 'POST') ? res(201, {}) : res(200, []));
    const r = await lib.checkAndIncrementRateLimit(mkReq({}), 10, 120, 'catalog');
    assert.deepStrictEqual({ allowed: r.allowed, count: r.count }, { allowed: true, count: 1 });
  });

  // ── 4. the handler, driven end to end ───────────────────────────────────
  // Behavioural, not a source grep: the endpoint is called and its real answer
  // is read back.
  await test('a healthy catalog request answers 200 with the published slabs', async () => {
    const h = loadHandler(router(baseSpec()));
    const r = mkRes();
    await h(mkReq({ action: 'catalog', slug: 'main-street-stone' }), r);
    assert.strictEqual(r.out.code, 200);
    assert.strictEqual(r.out.body.count, 1);
  });

  await test('an unknown slug is a 404 -- unchanged, and that is the point', async () => {
    const spec = baseSpec();
    spec.sd_public_shop = res(200, []);
    const h = loadHandler(router(spec));
    const r = mkRes();
    await h(mkReq({ action: 'catalog', slug: 'no-such-shop' }), r);
    assert.strictEqual(r.out.code, 404);
    assert.strictEqual(r.out.body.error.code, 'NOT_FOUND');
  });

  for (const status of [401, 500, 503]) {
    await test('a shop lookup that fails with HTTP ' + status + ' answers 502, NOT 404', async () => {
      const spec = baseSpec();
      spec.sd_public_shop = res(status, { message: 'nope' });
      const h = loadHandler(router(spec));
      const r = mkRes();
      await h(mkReq({ action: 'catalog', slug: 'main-street-stone' }), r);
      assert.strictEqual(r.out.code, 502,
        'a dead store told the customer the shop does not exist');
      assert.notStrictEqual(r.out.body.error && r.out.body.error.code, 'NOT_FOUND');
    });
  }

  await test('an unavailable rate-limit store answers 503 UNAVAILABLE, and never reaches the shop lookup', async () => {
    const spec = baseSpec();
    spec.sd_public_rate_limits = res(500, { message: 'nope' });
    let lookedUp = false;
    spec.sd_public_shop = function () { lookedUp = true; return res(200, []); };
    const h = loadHandler(router(spec));
    const r = mkRes();
    await h(mkReq({ action: 'quote_request', slug: 'main-street-stone', request: { name: 'A', phone: '1' } }), r);
    assert.strictEqual(r.out.code, 503);
    assert.strictEqual(r.out.body.error.code, 'UNAVAILABLE');
    assert.strictEqual(lookedUp, false, 'a refused request still hit the database');
  });

  await test('a GENUINE limit still answers 429 RATE_LIMITED -- the 503 did not swallow it', async () => {
    const spec = baseSpec();
    spec.sd_public_rate_limits = res(200, [{ count: 5 }]);
    const h = loadHandler(router(spec));
    const r = mkRes();
    await h(mkReq({ action: 'quote_request', slug: 'main-street-stone', request: { name: 'A', phone: '1' } }), r);
    assert.strictEqual(r.out.code, 429);
    assert.strictEqual(r.out.body.error.code, 'RATE_LIMITED');
  });

  await test('a failed counter INCREMENT refuses the quote write rather than letting it through uncounted', async () => {
    const spec = baseSpec();
    spec.sd_public_rate_limits = res(200, [{ count: 0 }]);
    spec.rate_write = res(500, { message: 'nope' });
    let wrote = false;
    spec.sd_quote_requests = function () { wrote = true; return res(201, {}); };
    const h = loadHandler(router(spec));
    const r = mkRes();
    await h(mkReq({ action: 'quote_request', slug: 'main-street-stone', request: { name: 'A', phone: '1' } }), r);
    assert.strictEqual(r.out.code, 503);
    assert.strictEqual(wrote, false, 'an uncounted lead was written into the shop table');
  });

  // ── 5. defect 4, the remnant fetch ──────────────────────────────────────
  await test('a shop without the sd_remnants migration (404) still gets its slab catalog', async () => {
    const spec = baseSpec();
    spec.sd_remnants = res(404, { message: 'Could not find the table' });
    const h = loadHandler(router(spec));
    const r = mkRes();
    await h(mkReq({ action: 'catalog', slug: 'main-street-stone' }), r);
    assert.strictEqual(r.out.code, 200, 'a missing migration took the whole storefront down');
    assert.strictEqual(r.out.body.remnant_count, 0);
    assert.strictEqual(r.out.body.count, 1);
  });

  for (const status of [401, 403, 500]) {
    await test('a remnant read failing with HTTP ' + status + ' answers 502, not a silently empty section', async () => {
      const spec = baseSpec();
      spec.sd_remnants = res(status, { message: 'nope' });
      const h = loadHandler(router(spec));
      const r = mkRes();
      await h(mkReq({ action: 'catalog', slug: 'main-street-stone' }), r);
      assert.strictEqual(r.out.code, 502,
        'a for-sale remnant inventory vanished from the storefront with no error');
    });
  }

  await test('published available remnants reach the catalog; reserved and unpublished ones do not', async () => {
    const spec = baseSpec();
    spec.sd_remnants = res(200, [
      { data: { id: 'R1', stone: 'Carrara', published: true, status: 'Available' } },
      { data: { id: 'R2', stone: 'Calacatta', published: true, status: 'Reserved' } },
      { data: { id: 'R3', stone: 'Statuario', status: 'Available' } }
    ]);
    const h = loadHandler(router(spec));
    const r = mkRes();
    await h(mkReq({ action: 'catalog', slug: 'main-street-stone' }), r);
    assert.strictEqual(r.out.body.remnant_count, 1);
    assert.strictEqual(r.out.body.remnants[0].id, 'R1');
  });

  // ── 6. THE MUTATION TEST ────────────────────────────────────────────────
  // The two refusal branches in the handler are order-dependent: an unreachable
  // counter also reports allowed:false, so if `!rl.allowed` is read first an
  // outage renders as "too many requests" and the 503 becomes unreachable code.
  //
  // Asserting the order by reading indexOf() in the source would pass against a
  // file where the branches were correct but the states were not, and would
  // fail against a correct rewrite that used a switch. So instead: BUILD THE
  // BROKEN VERSION AND PROVE IT IS BROKEN. The mutant is compiled in memory
  // with the real file's path, so its relative require still resolves and
  // nothing is written to disk.
  await test('MUTANT: swapping the two branches really does turn an outage into a 429', async () => {
    const src = fs.readFileSync(HANDLER, 'utf8');
    // \r?\n throughout: this repo's working trees still hold CRLF on files git
    // has not rewritten since .gitattributes went repo-wide, and a \n-only
    // pattern silently fails to match on exactly those.
    const SWAP = /( *if \(rl\.unavailable\) \{[\s\S]*?\r?\n *\}\r?\n)( *if \(!rl\.allowed\) \{[\s\S]*?\r?\n *\}\r?\n)/;
    assert.match(src, SWAP, 'the two refusal branches are no longer adjacent -- this mutation test has stopped testing anything and must be rewritten, not deleted');
    const mutated = src.replace(SWAP, '$2$1');
    assert.notStrictEqual(mutated, src, 'the mutation did not change the source');

    process.env.SUPABASE_URL = 'https://test.supabase.co';
    process.env.SUPABASE_SERVICE_ROLE_KEY = 'test-key';
    const spec = baseSpec();
    spec.sd_public_rate_limits = res(500, { message: 'nope' });
    global.fetch = router(spec);
    delete require.cache[require.resolve(LIB)];

    const m = new Module(HANDLER, null);
    m.filename = HANDLER;
    m.paths = Module._nodeModulePaths(path.dirname(HANDLER));
    m._compile(mutated, HANDLER);

    const r = mkRes();
    await m.exports(mkReq({ action: 'catalog', slug: 'main-street-stone' }), r);
    assert.strictEqual(r.out.code, 429,
      'the mutant did NOT answer 429 -- either the branch order stopped mattering or this test is asserting nothing');
    assert.strictEqual(r.out.body.error.code, 'RATE_LIMITED');

    // And the real file, same input, gives the right answer. Both halves are
    // needed: the mutant proves the ordering is load-bearing, this proves the
    // shipped file has it the right way round.
    const real = loadHandler(router(spec));
    const r2 = mkRes();
    await real(mkReq({ action: 'catalog', slug: 'main-street-stone' }), r2);
    assert.strictEqual(r2.out.code, 503);
    assert.strictEqual(r2.out.body.error.code, 'UNAVAILABLE');
  });

  console.log('\n' + passed + ' assertions passed' + (process.exitCode ? ', see failures above' : ''));
}

main();
