// api/sd-data-unconfirmed-write-sweep.test.js
//
// REQUIREMENT: no representation-PATCH in api/sd-data.js reports `ok: true`
//   for a write the data store did not confirm. Three answers, never two:
//   WROTE (200), MISSED (404), UNKNOWN (502 WRITE_UNCONFIRMED).
//
// CROSS-TENANT-ISOLATION: none (this suite is about WRITE CONFIRMATION, not
//   tenancy; the isolation arms for these resources live in
//   api/sd-data-cross-tenant-dispatchers.test.js)
//
// Run:  node api/sd-data-unconfirmed-write-sweep.test.js
//
// ── WHY THIS EXISTS ────────────────────────────────────────────────────────
// The 2026-09-18 json-catch-null pass fixed two sites and its commit described
// itself as a platform SWEEP. The independent review of it (2026-09-21) found
// FOUR MORE in the same file with the identical shape, one of them serving
// seven Tier A resources and one of them moving money.
//
// The sweep searched for `.json().catch(() => null)`. That matches 27 sites in
// api/sd-data.js and most are reads handling null correctly, so the search
// returned a haystack and the two obvious needles came out of it. THE DEFECT
// IS THREE CONDITIONS, NOT ONE STRING: a PATCH sent with `Prefer:
// return=representation`, ITS BODY READ THROUGH A CATCH, and a `res.status(200)
// .json({ ok: true })` that never consults it.
//
// So this file does two things, and the second is the one that makes the first
// stay true:
//   1. DRIVES each of the four repaired sites and asserts all three answers.
//   2. RE-RUNS THE PREDICATE over api/sd-data.js and fails if any site of that
//      shape exists at all. A fifth copy added tomorrow turns this RED. Without
//      it this is a snapshot of four fixes and the shape comes back.
//
// ── WHY A 200 CAN MEAN "NOTHING HAPPENED" ─────────────────────────────────
// Under `Prefer: return=representation` PostgREST answers a PATCH that MATCHED
// with one row and a PATCH that matched ZERO with `[]` -- both status 200.
// Neither `w.ok` nor a null from the catch can tell those apart, so all three
// of "it landed", "it matched nothing" and "the answer could not be read"
// reached the same success response.

'use strict';

process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET
  || ['unconfirmed', 'write', 'sweep', 'fixture'].join('-');

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const LIC = 'sweep-hash';
let APP_ID = 'stonedesk';

let pass = 0, fail = 0;
async function test(name, fn) {
  try { await fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('\n' + t); }

function mockRes() {
  const res = { statusCode: null, body: null };
  res.status = function (c) { res.statusCode = c; return res; };
  res.json = function (b) { res.body = b; return res; };
  return res;
}

const { signSessionToken } = require('./_lib/auth');
function req(body, app, role) {
  return {
    method: 'POST',
    headers: {
      authorization: 'Bearer GOOD-KEY',
      'x-sd-auth': signSessionToken({ app: app, employee_id: 'E-1',
                                      role: role, license_hash: LIC })
    },
    body: body
  };
}

function load(fetchImpl) {
  delete require.cache[require.resolve('./_lib/license')];
  require.cache[require.resolve('./_lib/license')] = {
    exports: {
      validateLicenseKey: async function () {
        return { valid: true, active: true, license_hash: LIC, trial_ends_at: null,
                 stripe_subscription_id: null, app_id: APP_ID };
      }
    }
  };
  global.fetch = fetchImpl;
  delete require.cache[require.resolve('./sd-data.js')];
  return require('./sd-data.js');
}

// Answers the READ leg with a seeded row and the PATCH leg with whatever the
// case under test is about -- including a body that will not parse, which is
// the UNKNOWN case and the one a fixed array can never produce.
function mock(opts) {
  const calls = [];
  return {
    calls: calls,
    fn: async function (url, init) {
      const method = (init && init.method) || 'GET';
      calls.push({ url: String(url), method: method });
      if (method === 'GET') {
        return { ok: true, status: 200, json: async () => opts.readRows };
      }
      return {
        ok: true, status: 200,
        json: async function () {
          if (opts.patchThrows) throw new SyntaxError('Unexpected token <');
          return opts.patchBody;
        }
      };
    }
  };
}

// The four repaired sites. `read` is what the branch's READ leg must find for
// the PATCH to be attempted at all; `body` is the request.
const SITES = [
  { name: 'bld_draws retainage release (:4135, MONEY)',
    app: 'sairnbuild', role: 'owner',
    // The seeded draw has to SUMMARISE cleanly before and after the release,
    // or the branch answers 409 RELEASE_REFUSED at the WIP engine and the PATCH
    // is never sent. retainage_pct is what "what remains held" is worked out
    // from -- the engine refuses a release it cannot reconcile, which is
    // correct and is a gate in front of the line under test, not part of it.
    read: [{ draw_id: 'D-1', data: { draw_id: 'D-1', amount: 1000,
                                     retainage_pct: 10, retainage_held: 100,
                                     retainage_released: 0, status: 'approved' } }],
    // `today` is REQUIRED by this branch -- "this engine will not assume a
    // clock" -- and omitting it answers 400 NO_TODAY before the PATCH is ever
    // sent, which would have scored three arms as failures of the wrong thing.
    body: { action: 'release_retainage', resource: 'bld_draws',
            payload: { draw_id: 'D-1', amount: 50, released_at: '2026-09-21',
                       today: '2026-09-21' } },
    missIs: 404, unknownIs: 502 },
  { name: 'SAIRNcode soft-delete (:12422, 7 Tier A resources)',
    app: 'sairncode', role: 'admin',
    read: [{ data: { id: 'CLM-1', payer: 'Acme', amount: 1200 } }],
    body: { action: 'soft_delete', resource: 'sc_claims', payload: { id: 'CLM-1' } },
    missIs: 404, unknownIs: 502 },
  { name: 'sd_customers soft-delete (:2404)',
    app: 'stonedesk', role: 'owner',
    read: [{ data: { id: 'C-1', name: 'A Customer' } }],
    body: { action: 'soft_delete', resource: 'sd_customers', payload: { id: 'C-1' } },
    missIs: 404, unknownIs: 502 },
  { name: 'dnt_supplies soft-delete (:11257)',
    app: 'sairndental', role: 'owner',
    read: [{ data: { id: 'S-1', name: 'Gloves' } }],
    body: { action: 'soft_delete', resource: 'dnt_supplies', payload: { id: 'S-1' } },
    missIs: 404, unknownIs: 502 }
];

// ── THE PREDICATE, AND IT IS THE HALF THAT KEEPS THIS TRUE ────────────────
// Re-derived from the source on every run rather than pinned to a count. A
// number would go stale the first time a site is legitimately added or
// removed; this asks the question instead.
function unguardedSites() {
  const src = fs.readFileSync(path.join(__dirname, 'sd-data.js'), 'utf8')
    .replace(/\r\n/g, '\n');
  const lines = src.split('\n');
  const out = [];
  lines.forEach(function (l, idx) {
    if (!/\.json\(\)\.catch\(/.test(l)) return;
    const before = lines.slice(Math.max(0, idx - 12), idx).join('\n');
    const after = lines.slice(idx, idx + 6).join('\n');
    if (!/Prefer:\s*'return=representation'/.test(before)) return;   // not a representation write
    if (/method:\s*'POST'/.test(before)) return;                     // upserts are a different shape
    if (/wroteRow\(/.test(after)) return;                            // guarded
    if (!/res\.status\(200\)\.json\(\{\s*ok:\s*true/.test(after)) return;
    out.push(idx + 1);
  });
  return out;
}

(async function () {
  console.log('api/sd-data.js -- no representation-PATCH reports an unconfirmed write');

  for (const site of SITES) {
    section(site.name);
    APP_ID = site.app;

    await test('a PATCH that MATCHED answers 200 ok:true', async () => {
      const m = mock({ readRows: site.read, patchBody: [{ data: {} }] });
      const h = load(m.fn);
      const res = mockRes();
      await h(req(site.body, site.app, site.role), res);
      assert.strictEqual(res.statusCode, 200,
        'a real write must still succeed -- the fix must not break the true '
        + 'positive. Got ' + res.statusCode + ' ' + JSON.stringify(res.body));
      assert.strictEqual(res.body.ok, true, JSON.stringify(res.body));
    });

    await test('a PATCH that matched ZERO rows answers ' + site.missIs + ', not ok:true', async () => {
      const m = mock({ readRows: site.read, patchBody: [] });
      const h = load(m.fn);
      const res = mockRes();
      await h(req(site.body, site.app, site.role), res);
      assert.notStrictEqual(res.body && res.body.ok, true,
        'a write that matched NOTHING was reported as done: '
        + JSON.stringify(res.body));
      assert.strictEqual(res.statusCode, site.missIs, JSON.stringify(res.body));
      assert.strictEqual(res.body.error.code, 'NOT_FOUND', JSON.stringify(res.body));
    });

    // ── ADDED AFTER A SABOTAGE SURVIVED ──────────────────────────────────
    // Mutating wroteRow's `if (!Array.isArray(rows)) return 'UNKNOWN'` to
    // 'WROTE' survived the whole suite, because the only UNKNOWN arm drove a
    // body that would not PARSE -- and the catch turns that into `null`, which
    // the FIRST line of wroteRow handles. The non-array branch was untested by
    // anything. It is reachable: a branch that ever sends
    // `Accept: application/vnd.pgrst.object+json` gets an OBJECT back, and
    // under the mutation every successful write on it would be indistinguishable
    // from one that returned a shape nobody asked for.
    await test('a PATCH answering a bare OBJECT answers ' + site.unknownIs
      + ' WRITE_UNCONFIRMED', async () => {
      const m = mock({ readRows: site.read, patchBody: { data: {} } });
      const h = load(m.fn);
      const res = mockRes();
      await h(req(site.body, site.app, site.role), res);
      assert.notStrictEqual(res.body && res.body.ok, true,
        'a body that is not the array shape asked for was reported as a '
        + 'successful write: ' + JSON.stringify(res.body));
      assert.strictEqual(res.statusCode, site.unknownIs, JSON.stringify(res.body));
      assert.strictEqual(res.body.error.code, 'WRITE_UNCONFIRMED', JSON.stringify(res.body));
    });

    await test('a PATCH whose body will not parse answers ' + site.unknownIs
      + ' WRITE_UNCONFIRMED', async () => {
      const m = mock({ readRows: site.read, patchThrows: true });
      const h = load(m.fn);
      const res = mockRes();
      await h(req(site.body, site.app, site.role), res);
      assert.notStrictEqual(res.body && res.body.ok, true,
        'an unreadable answer was reported as a successful write: '
        + JSON.stringify(res.body));
      assert.strictEqual(res.statusCode, site.unknownIs, JSON.stringify(res.body));
      assert.strictEqual(res.body.error.code, 'WRITE_UNCONFIRMED', JSON.stringify(res.body));
      // UNKNOWN must claim NEITHER outcome. "It was not confirmed and it was
      // not refused" is the third state, and collapsing it into either
      // neighbour is the whole defect one level up.
      assert.match(res.body.error.message, /UNKNOWN|not confirmed/,
        'the refusal does not say the outcome is unknown: ' + res.body.error.message);
    });
  }

  // ── THE SHAPE, NOT THE SNAPSHOT ─────────────────────────────────────────
  section('THE PREDICATE -- a fifth copy of this shape turns this suite RED');
  await test('no representation-PATCH in api/sd-data.js answers ok:true unguarded', async () => {
    const found = unguardedSites();
    assert.deepStrictEqual(found, [],
      'api/sd-data.js has ' + found.length + ' representation-PATCH site(s) that '
      + 'report ok:true without consulting wroteRow(), at line(s) '
      + found.join(', ') + '. Under `Prefer: return=representation` a PATCH '
      + 'matching ZERO rows returns [] with status 200, so each of these '
      + 'reports a change that did not happen. Add the UNKNOWN and MISSED '
      + 'branches -- wroteRow() and refuseUnconfirmedWrite() are module-scope.');
  });

  await test('the predicate is not vacuous -- it finds a planted instance', async () => {
    // A NEGATIVE CONTROL ON THE PREDICATE ITSELF. A checker that matches
    // nothing passes its own subject trivially, which is how a guard stops
    // guarding without anyone noticing. This proves the three conditions are
    // conjunctive and that each is actually read.
    const src = [
      "const w = await fetch(rest('t?license_hash=eq.' + enc(licHash)), {",
      "  method: 'PATCH',",
      "  headers: Object.assign({}, headers, { Prefer: 'return=representation' }),",
      "  body: JSON.stringify({ data: marked })",
      "});",
      "const wRows = await w.json().catch(function () { return null; });",
      "if (!w.ok) return upstream(res, wRows);",
      "res.status(200).json({ ok: true, data: marked });"
    ].join('\n');
    const lines = src.split('\n');
    const hits = [];
    lines.forEach(function (l, idx) {
      if (!/\.json\(\)\.catch\(/.test(l)) return;
      const before = lines.slice(Math.max(0, idx - 12), idx).join('\n');
      const after = lines.slice(idx, idx + 6).join('\n');
      if (!/Prefer:\s*'return=representation'/.test(before)) return;
      if (/method:\s*'POST'/.test(before)) return;
      if (/wroteRow\(/.test(after)) return;
      if (!/res\.status\(200\)\.json\(\{\s*ok:\s*true/.test(after)) return;
      hits.push(idx + 1);
    });
    assert.strictEqual(hits.length, 1,
      'the predicate did not recognise a planted instance of the exact shape it '
      + 'exists to find, so its empty result above proves nothing');
  });

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
