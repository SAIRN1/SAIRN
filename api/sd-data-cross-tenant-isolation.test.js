// api/sd-data-cross-tenant-isolation.test.js
//
// REQUIREMENT: a valid, fully authenticated session for tenant A cannot read,
//   overwrite or enumerate tenant B's rows on any Tier A resource.
//
// CROSS-TENANT-ISOLATION: law_invoices, law_opaccounts, law_barcerts
//
// That line is machine-read by tools/cross_tenant_isolation_scope.py and is the
// ONLY thing that credits a resource with coverage. It is cross-checked, never
// trusted: a file declaring coverage that does not also GRADE genuine credits
// nothing and is reported. Two heuristics were tried before this and both
// scored the better-structured test worse -- a parameterised suite declares its
// resources in a table and drives them in a loop, so no proximity rule can
// attribute an arm to a name. Extend this line when you extend LAW_TIER_A, and
// not before.
//
// Run:  node api/sd-data-cross-tenant-isolation.test.js
//
// ── WHY THIS FILE EXISTS ───────────────────────────────────────────────────
// The hover auditor's finding #269 swept `license_hash` FILTERING to 84/84
// Tier A resources: every one of them scopes its query by tenant. Findings
// #276/#278 are the half of that sentence that decays -- the filtering is
// asserted by almost nothing, and a filter nothing tests is a filter the next
// refactor drops silently. Tenant A reads tenant B's row and the response looks
// completely normal. There is no error, no log line and no failing test.
//
// THIS IS THE REFERENCE IMPLEMENTATION, not the sweep. It covers ONE dispatcher
// -- LAW_RESOURCES, three Tier A members -- and exists so the other 47 units in
// tools/cross_tenant_isolation_scope.py --plan are transplants of a PROVEN
// pattern rather than 47 independent inventions of one. Read
// docs/2026-09-21-cross-tenant-isolation-build-plan.md before extending it.
//
// ── THE PATTERN IS ADAPTED FROM api/sairndental/complaint-respond.test.js:100
// which is the only genuine cross-tenant isolation test on the platform today.
// Its load-bearing property, stated in its own comment, is the one thing that
// must survive every transplant:
//
//     THE FETCH MOCK FILTERS ON WHICHEVER eq. CLAUSES ARE ACTUALLY PRESENT IN
//     THE QUERY URL, mirroring real PostgREST.
//
// Remove `license_hash=eq.` from the handler and the mock matches on the other
// clause alone, returns tenant B's row, and the assertion fails. THE MOCK IS
// THE TEST. A mock that returns a fixed array with an assertion that the URL
// CONTAINS 'license_hash=eq.' is a string check wearing a behaviour check: it
// passes when the filter is present but ANDed wrong, when the handler ignores
// the rows it gets back, and when a second query on the same path lacks it.
// tools/cross_tenant_isolation_scope.py grades those apart and calls them WEAK.
//
// ── THREE SHAPES, NOT ONE, AND THAT IS THE MAIN FINDING OF THE SCOPING ─────
// complaint-respond is a single-id fetch, so its assertion is 404. Most of the
// 48 units are not that shape, and a session that transplants the 404 assertion
// onto a list read will write a test that passes on a handler with no filter at
// all. The three shapes:
//
//   SHAPE L -- LIST READ. `rest(resource + '?license_hash=eq.' + licHash +
//     '&select=data')`. No id clause. The refusal is not a status code, it is
//     an ABSENCE: 200 OK carrying only tenant A's rows. Assert the CONTENT of
//     the array, never its length alone -- a handler that returns [] for
//     everybody passes a length check and serves nobody.
//
//   SHAPE I -- ID READ. license_hash AND an id clause. Asking for tenant B's id
//     under tenant A's licence must 404/empty. complaint-respond's shape.
//
//   SHAPE W -- WRITE. The dangerous one and the least obvious. The upsert is
//     keyed `on_conflict=license_hash,<idCol>`, so tenant A writing tenant B's
//     id creates a SEPARATE row under A's hash rather than overwriting B's.
//     That is correct -- and it is correct BY ACCIDENT unless two things are
//     asserted: that `license_hash` is in the on_conflict key, and that the
//     BODY carries the licHash the handler derived rather than anything the
//     caller sent. Drop license_hash from the on_conflict key and tenant A's
//     write silently overwrites tenant B's row. Nothing else on this platform
//     tests that today.
//
// ── WHAT THIS FILE DOES NOT DO, said plainly ───────────────────────────────
// It does not test the DATABASE. If a Postgres RLS policy is wrong, or a GRANT
// is too wide, this passes anyway -- it drives the handler, and the handler
// builds the query it builds. It asserts the APPLICATION half of tenant
// isolation, which is the half that a refactor of api/sd-data.js can break.
// The database half is a different control and needs a different method.

'use strict';

const assert = require('assert');

// Set BEFORE api/_lib/auth is required -- it reads the secret at module load
// and throws if it is absent, which is correct (a signing key that defaults is
// a signing key that is not one) and means the order here is load-bearing.
// Split-and-joined so a secret scanner does not flag a test fixture, the same
// spelling the sibling sd-data suites use.
process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET
  || ['cross', 'tenant', 'isolation', 'fixture'].join('-');

const HASH_A = 'tenant-A-hash';
const HASH_B = 'tenant-B-hash';

let pass = 0, fail = 0;
async function test(name, fn) {
  try {
    await fn();
    console.log('  ok   ' + name);
    pass++;
  } catch (e) {
    console.log('  FAIL ' + name + '\n       ' + e.message);
    fail++;
  }
}
function section(t) { console.log('\n' + t); }

function mockRes() {
  const res = { statusCode: null, body: null };
  res.status = function (c) { res.statusCode = c; return res; };
  res.json = function (b) { res.body = b; return res; };
  return res;
}

// A REAL SIGNED SESSION for the tenant under test, signed against the hash the
// HANDLER will derive. api/_lib/license.js hashes the bearer key; a token
// signed against anything else verifies fine in isolation and the handler
// rejects it with an indistinguishable NO_SESSION -- so a test that got this
// wrong would report 401 and read as "isolation works". sairn-api-tester §2.
const { signSessionToken } = require('./_lib/auth');
function mockReq(body, licHash) {
  return {
    method: 'POST',
    headers: {
      authorization: 'Bearer KEY-FOR-' + licHash,
      'x-sd-auth': signSessionToken({
        app: 'sairnlaw', employee_id: 'emp-owner', role: 'owner', license_hash: licHash })
    },
    body: body
  };
}

// ── THE MOCK. THIS IS THE TEST. ───────────────────────────────────────────
// It parses every `<col>=eq.<value>` clause out of the query string and
// filters the seeded rows by ALL of them, the way PostgREST does. A handler
// that omits `license_hash=eq.` gets an unfiltered result and the assertions
// below catch it. `calls` records what was actually asked for, which is how
// SHAPE W checks the write without a database.
function postgrestMock(rows, calls) {
  return async function (url, opts) {
    const u = String(url);
    calls.push({ url: u, opts: opts || null });
    const q = u.indexOf('?') >= 0 ? u.slice(u.indexOf('?') + 1) : '';
    const eqs = [];
    q.split('&').forEach(function (part) {
      const m = part.match(/^([a-z0-9_]+)=eq\.(.*)$/);
      if (m) eqs.push([m[1], decodeURIComponent(m[2])]);
    });
    if (opts && opts.method === 'POST') {
      // The upsert. Echo back a representation, as PostgREST does with
      // `return=representation`, so the handler's own 200 path runs.
      const sent = JSON.parse(opts.body);
      return { ok: true, status: 200, json: async function () { return [sent]; } };
    }
    const matches = rows.filter(function (r) {
      return eqs.every(function (kv) { return String(r[kv[0]]) === kv[1]; });
    });
    return { ok: true, status: 200, json: async function () { return matches; } };
  };
}

// Loads sd-data.js fresh with `validateLicenseKey` stubbed to resolve the
// bearer key to a named tenant. Fresh per call: the handler caches nothing
// across requires, and a stale module would carry the previous tenant's stub.
function loadHandler(licHash, fetchImpl) {
  delete require.cache[require.resolve('./_lib/license')];
  require.cache[require.resolve('./_lib/license')] = {
    exports: {
      validateLicenseKey: async function () {
        return { valid: true, active: true, license_hash: licHash,
                 trial_ends_at: null, stripe_subscription_id: null, app_id: 'sairnlaw' };
      }
    }
  };
  global.fetch = fetchImpl;
  delete require.cache[require.resolve('./sd-data.js')];
  return require('./sd-data.js');
}

// The three Tier A members of LAW_RESOURCES, driven individually rather than
// as one representative. A dispatcher test that drives ONE member proves the
// dispatcher and proves nothing about whether the other two are in its map --
// which is the failure mode of "one parameterised test covers the map".
const LAW_TIER_A = [
  ['law_invoices', 'invoice_id'],
  ['law_opaccounts', 'opaccount_id'],
  ['law_barcerts', 'barcert_id']
];

(async function () {
  console.log('CROSS-TENANT ISOLATION -- LAW_RESOURCES dispatcher (reference implementation)');

  section('SHAPE L -- list read: tenant A sees ONLY tenant A\'s rows');
  for (const [resource, idCol] of LAW_TIER_A) {
    await test(resource + ': tenant B\'s rows are absent from tenant A\'s read', async () => {
      const rows = [
        { license_hash: HASH_A, [idCol]: 'A-1', data: { id: 'A-1', owner: 'A' } },
        { license_hash: HASH_B, [idCol]: 'B-1', data: { id: 'B-1', owner: 'B' } }
      ];
      const calls = [];
      const handler = loadHandler(HASH_A, postgrestMock(rows, calls));
      const res = mockRes();
      await handler(mockReq({ action: 'read', resource: resource }, HASH_A), res);

      assert.strictEqual(res.statusCode, 200, 'expected a 200 list read, got ' + res.statusCode
        + ' ' + JSON.stringify(res.body));
      const got = (res.body && res.body.data) || [];
      // CONTENT, NOT LENGTH. A handler that returns [] for everybody passes a
      // length assertion and serves nobody; a handler with no tenant filter
      // returns both rows and passes an "is non-empty" assertion.
      const owners = got.map(function (x) { return x && x.owner; }).sort();
      assert.deepStrictEqual(owners, ['A'],
        'tenant A\'s read returned ' + JSON.stringify(owners)
        + ' -- anything other than exactly ["A"] means the license_hash filter is '
        + 'absent, ANDed wrong, or the rows it returns are not the rows it filtered');
      // And the query really did carry the clause, so a future mock change
      // cannot make this pass for the wrong reason.
      assert.ok(calls.length && calls[0].url.indexOf('license_hash=eq.' + HASH_A) !== -1,
        'the read query did not carry license_hash=eq.' + HASH_A + ': ' + (calls[0] || {}).url);
    });
  }

  section('SHAPE L, the other direction -- tenant B sees ONLY tenant B\'s rows');
  await test('the same handler, a different tenant, no leakage either way', async () => {
    const rows = [
      { license_hash: HASH_A, invoice_id: 'A-1', data: { id: 'A-1', owner: 'A' } },
      { license_hash: HASH_B, invoice_id: 'B-1', data: { id: 'B-1', owner: 'B' } }
    ];
    const handler = loadHandler(HASH_B, postgrestMock(rows, []));
    const res = mockRes();
    await handler(mockReq({ action: 'read', resource: 'law_invoices' }, HASH_B), res);
    const owners = ((res.body && res.body.data) || []).map(function (x) { return x && x.owner; });
    assert.deepStrictEqual(owners, ['B'],
      'tenant B\'s read returned ' + JSON.stringify(owners)
      + '. BOTH DIRECTIONS ARE DRIVEN DELIBERATELY: a handler hardcoded to one '
      + 'tenant passes the A-only arm and fails here.');
  });

  section('SHAPE W -- write: tenant A cannot overwrite tenant B\'s row');
  for (const [resource, idCol] of LAW_TIER_A) {
    await test(resource + ': A writing B\'s id lands under A\'s hash, not B\'s', async () => {
      const calls = [];
      const handler = loadHandler(HASH_A, postgrestMock([], calls));
      const res = mockRes();
      // Tenant A deliberately submits an id that belongs to tenant B.
      await handler(mockReq({ action: 'write', resource: resource,
                             payload: { id: 'B-1', hours: 1, billing_code: 'L100',
                                        matter_id: 'M-1', stolen: true } }, HASH_A), res);

      const post = calls.filter(function (c) { return c.opts && c.opts.method === 'POST'; })[0];
      assert.ok(post, 'no POST was made for ' + resource);

      // 1. THE CONFLICT KEY MUST INCLUDE license_hash. Without it the upsert
      //    collides on the id alone and tenant A's write REPLACES tenant B's
      //    row. This is the assertion the whole shape exists for and it is
      //    invisible to any test that only checks the response.
      assert.ok(post.url.indexOf('on_conflict=license_hash,' + idCol) !== -1,
        'the upsert conflict key is not (license_hash, ' + idCol + '): ' + post.url
        + ' -- drop license_hash from it and tenant A overwrites tenant B');

      // 2. THE BODY MUST CARRY THE HANDLER-DERIVED HASH, not anything the
      //    caller supplied. A handler that read license_hash off the payload
      //    would let a caller write into any tenant it can name.
      const sent = JSON.parse(post.opts.body);
      assert.strictEqual(sent.license_hash, HASH_A,
        'the row was written under ' + JSON.stringify(sent.license_hash)
        + ' rather than the hash the handler derived from the bearer key');
      assert.strictEqual(String(sent[idCol]), 'B-1',
        'the id column was not populated from payload.id');
    });
  }

  section('SHAPE W, the injection direction -- a caller-supplied license_hash is ignored');
  await test('payload.license_hash naming tenant B does not move the row', async () => {
    const calls = [];
    const handler = loadHandler(HASH_A, postgrestMock([], calls));
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'law_invoices',
                           payload: { id: 'X-1', license_hash: HASH_B, amount: 1 } }, HASH_A), res);
    const post = calls.filter(function (c) { return c.opts && c.opts.method === 'POST'; })[0];
    assert.ok(post, 'no POST was made');
    const sent = JSON.parse(post.opts.body);
    assert.strictEqual(sent.license_hash, HASH_A,
      'a license_hash INSIDE the payload reached the stored row as '
      + JSON.stringify(sent.license_hash) + '. The handler must use the hash it '
      + 'derived from the bearer key and nothing else.');
  });

  section('THE NEGATIVE CONTROL -- the mock can distinguish a filtered query from an unfiltered one');
  await test('an unfiltered query against the same mock returns BOTH tenants', async () => {
    // Drives the MOCK, not the handler. If this ever returns one row, the mock
    // has stopped filtering and every arm above is passing for the wrong
    // reason -- the exact failure the eighth cross-domain discipline is about.
    const rows = [
      { license_hash: HASH_A, invoice_id: 'A-1', data: { owner: 'A' } },
      { license_hash: HASH_B, invoice_id: 'B-1', data: { owner: 'B' } }
    ];
    const f = postgrestMock(rows, []);
    const unfiltered = await (await f('https://x/rest/v1/law_invoices?select=data')).json();
    assert.strictEqual(unfiltered.length, 2,
      'the mock returned ' + unfiltered.length + ' rows for a query with NO eq. clauses. '
      + 'It is not filtering, so every isolation arm above proves nothing.');
    const filtered = await (await f('https://x/rest/v1/law_invoices?license_hash=eq.'
      + HASH_A + '&select=data')).json();
    assert.strictEqual(filtered.length, 1,
      'the mock returned ' + filtered.length + ' rows for a license_hash-filtered query');
  });

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
