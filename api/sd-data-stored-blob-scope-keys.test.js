// api/sd-data-stored-blob-scope-keys.test.js
//
// REQUIREMENT: on every api/sd-data.js write branch converted to
//   api/_lib/blob.js's storedBlob(), a payload that carries a scope key
//   (license_hash, app_id, p_license_hash) or a MAPPED COLUMN key must not get
//   that key into the stored `data` blob -- and must still get everything else
//   through untouched.
//
// Run:  node api/sd-data-stored-blob-scope-keys.test.js
//
// ── WHY THIS FILE EXISTS, AND IT IS AN ABLATION RESULT, NOT A HUNCH ───────
// Six branches were converted to storedBlob() on 2026-09-26 (sdn_clients,
// sen_clients, the SEN_REFERRAL_RESOURCES pair, sen_claims, rf_jobs,
// rf_claim_photos). Before writing a line of this file, the module was
// SABOTAGED -- `NEVER_STORED` emptied to `[]` -- and the existing suites were
// run against it:
//
//   api/sd-data-cross-tenant-ownbranch.test.js    76 passed, 0 failed
//   api/sd-data-sdn-session-gate.test.js          40 passed, 0 failed
//   api/sd-data-bespoke-branch-isolation.test.js  36 passed, 2 FAILED
//   api/sd-data-alf-isolation.test.js             19 passed, 3 FAILED
//
// The five arms that went red all belong to the SIX BRANCHES CONVERTED IN
// SEPTEMBER (law_matters, rf_proposals, alf_mar, alf_incidents, alf_clients) --
// every one of them named in a `BLOB_CLEAN` table in its own suite. NOT ONE
// arm anywhere covered the six converted today: the conversion would have been
// landed, believed, and held by nothing. That is the gap this file closes, and
// it is the reason the ablation ran first rather than last.
//
// ── WHAT EACH ARM ASSERTS, AND THE THIRD ONE IS THE POINT ────────────────
// (1) no scope key reached `data`            -- the universal rule
// (2) no MAPPED COLUMN key reached `data`    -- this branch's own column list
// (3) an ordinary payload field SURVIVED     -- the strip is not over-broad
//
// (3) exists because the failure mode of a blob strip is symmetric and only
// one half is loud. A missing strip leaks a lying field; an over-broad strip
// DELETES A CUSTOMER'S DATA, silently, on every save. `storedBlob(payload,
// [...])` makes the second easy to cause by typing one extra name into a list,
// so every branch here proves a field came through.
//
// ── THE COLUMN LISTS BELOW ARE NOT COPIES OF THE HANDLER'S ───────────────
// Each is derived from THAT BRANCH'S READ, which is where a shadow actually
// happens, and the two differ in three of the six:
//
//   sdn_clients        read spreads the blob LAST over {id, assigned_employee_id}
//   sen_clients        same shape, its own read, checked separately
//   sen_referrals      blob LAST over {id} only -- idCol is mapped TO id, so a
//                      payload `referral_id` shadows nothing and is NOT stripped
//   sen_claims         blob LAST over {id} only, same reasoning for claim_id
//   rf_jobs            blob LAST over FOUR columns; the handler deletes SIX
//                      keys and the other two (estimate, measurement_correction)
//                      are trust discards, not column mappings
//   rf_claim_photos    THE COLUMNS ARE SPREAD LAST -- this read cannot be
//                      shadowed at all, so its column list is just {id} and
//                      what the conversion buys is the scope-key strip alone
//
// A suite that asserted one column list six times would be green and would be
// proving the wrong thing on four of the six.
//
// ── AND IT WAS DRIVEN RED FOUR WAYS BEFORE BEING BELIEVED ────────────────
// api/_lib/blob.js mutated, this suite run against each, module restored
// (31 passed, 0 failed on the real module):
//
//   M1  NEVER_STORED = []                    24 passed,  7 FAILED
//   M2  columnKeys ignored                   25 passed,  6 FAILED
//   M3  the blob returned empty              25 passed,  6 FAILED
//   M4  only the FIRST scope key stripped    25 passed,  6 FAILED
//
// M1's first result was 30 passed, 1 FAILED -- see REQUIRED_STRIPPED below for
// what that caught and why the arms no longer read their own requirement from
// the thing they are testing.

'use strict';

process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET
  || ['stored', 'blob', 'scope', 'fixture'].join('-');
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://test.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'test-key';

const assert = require('assert');
const { signSessionToken } = require('./_lib/auth');

const HASH_A = 'tenant-A-hash';
const HASH_B = 'tenant-B-hash';

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

// Same mock shape as api/sd-data-bespoke-branch-isolation.test.js: it filters
// seeded rows by every `<col>=eq.<v>` clause and honours `select=`. Unfaithful
// only in the safe direction -- an unrecognised clause is not applied, so it
// returns MORE rows than PostgREST would and an assertion fails louder.
function postgrestMock(rows, calls) {
  return async function (url, opts) {
    const u = String(url);
    calls.push({ url: u, opts: opts || null });
    const q = u.indexOf('?') >= 0 ? u.slice(u.indexOf('?') + 1) : '';
    const eqs = [];
    let select = null;
    q.split('&').forEach(function (part) {
      const m = part.match(/^([a-z0-9_]+)=eq\.(.*)$/);
      if (m) { eqs.push([m[1], decodeURIComponent(m[2])]); return; }
      const s = part.match(/^select=(.*)$/);
      if (s) select = decodeURIComponent(s[1]).split(',').map(function (x) { return x.trim(); });
    });
    if (/_employee_auth\?/.test(u)) {
      const forHash = (eqs.filter(function (kv) { return kv[0] === 'license_hash'; })[0] || [])[1];
      return { ok: true, status: 200, json: async function () {
        return [{ license_hash: forHash || HASH_A, employee_id: 'emp-1',
                  role: 'owner', active: true }]; } };
    }
    if (opts && opts.method === 'POST') {
      const sent = JSON.parse(opts.body);
      return { ok: true, status: 200, text: async function () { return opts.body; },
               json: async function () { return [sent]; } };
    }
    if (opts && opts.method === 'PATCH') {
      return { ok: true, status: 200, json: async function () { return [{ data: {} }]; } };
    }
    const matches = rows.filter(function (r) {
      return eqs.every(function (kv) { return String(r[kv[0]]) === kv[1]; });
    }).map(function (r) {
      if (!select || select.indexOf('*') !== -1) return r;
      const out = {};
      select.forEach(function (c) { if (c in r) out[c] = r[c]; });
      return out;
    });
    return { ok: true, status: 200, json: async function () { return matches; } };
  };
}

function loadHandler(licHash, app, fetchImpl) {
  delete require.cache[require.resolve('./_lib/license')];
  require.cache[require.resolve('./_lib/license')] = {
    exports: {
      validateLicenseKey: async function () {
        return { valid: true, active: true, license_hash: licHash,
                 trial_ends_at: null, stripe_subscription_id: null, app_id: app };
      }
    }
  };
  global.fetch = fetchImpl;
  delete require.cache[require.resolve('./sd-data.js')];
  return require('./sd-data.js');
}

function mockReq(body, licHash, app, role) {
  return {
    method: 'POST',
    headers: {
      authorization: 'Bearer KEY-FOR-' + licHash,
      'x-sd-auth': signSessionToken({ app: app, employee_id: 'emp-1',
                                      role: role, license_hash: licHash })
    },
    body: body
  };
}

function firstPost(calls) {
  return calls.filter(function (c) { return c.opts && c.opts.method === 'POST'; })[0];
}

// ── THE UNITS ─────────────────────────────────────────────────────────────
// [label, app, role, resource, columns-that-must-be-stripped, extra payload,
//  seed rows the branch needs before it will write at all]
//
// `survivor` is the ordinary field every arm proves came THROUGH. It is a
// different name per branch so a cross-wired fixture cannot pass by accident.
const UNITS = [
  { label: 'sdn_clients', app: 'sairndesign', role: 'owner',
    resource: 'sdn_clients',
    columns: ['id', 'assigned_employee_id'],
    payload: { id: 'C-1', assigned_employee_id: 'emp-1', notes: 'sdn-survives' },
    survivor: ['notes', 'sdn-survives'], rows: [] },

  { label: 'sen_clients', app: 'sairnsenior', role: 'owner',
    resource: 'sen_clients',
    columns: ['id', 'assigned_employee_id'],
    payload: { id: 'C-1', assigned_employee_id: 'emp-1', care_plan: 'sen-survives' },
    survivor: ['care_plan', 'sen-survives'], rows: [] },

  // The SEN_REFERRAL_RESOURCES generic pair -- one branch, five resources.
  // `referral_id` is in the payload ON PURPOSE and must SURVIVE: the read maps
  // the id column to `id`, so a payload copy under its own name shadows
  // nothing, and stripping it would delete real data.
  { label: 'sen_referrals (SEN_REFERRAL_RESOURCES)', app: 'sairnsenior',
    role: 'owner', resource: 'sen_referrals',
    columns: ['id'],
    payload: { id: 'R-1', referral_id: 'R-1', source: 'ref-survives' },
    survivor: ['source', 'ref-survives'],
    mustSurvive: ['referral_id'], rows: [] },

  { label: 'sen_claims', app: 'sairnsenior', role: 'owner',
    resource: 'sen_claims',
    columns: ['id'],
    payload: { id: 'CL-1', claim_id: 'CL-1', amount: 'claim-survives' },
    survivor: ['amount', 'claim-survives'],
    mustSurvive: ['claim_id'], rows: [] },

  // rf_jobs: FOUR mapped columns. `estimate` and `measurement_correction` are
  // deliberately NOT asserted as stripped -- they are trust discards the
  // handler still removes by hand, and asserting them here would state that
  // rf_jobs has columns it does not have.
  { label: 'rf_jobs', app: 'sairnroofing', role: 'owner',
    resource: 'rf_jobs',
    columns: ['id', 'job_class', 'assigned_employee_id', 'location_id'],
    payload: { id: 'J-1', job_class: 'commercial', assigned_employee_id: 'emp-1',
               location_id: 'LOC-1', customer_name: 'rf-survives' },
    survivor: ['customer_name', 'rf-survives'], rows: [] },

  // rf_claim_photos: append-only insert, and the read spreads COLUMNS last, so
  // the only thing this conversion buys is the scope-key strip. The column
  // list is `id` alone and the arm says so.
  { label: 'rf_claim_photos', app: 'sairnroofing', role: 'owner',
    resource: 'rf_claim_photos',
    columns: ['id'],
    payload: { id: 'P-1', claim_id: 'CLM-1', caption: 'photo-survives' },
    survivor: ['caption', 'photo-survives'],
    mustSurvive: ['claim_id'],
    rows: [{ license_hash: HASH_A, claim_id: 'CLM-1',
             assigned_employee_id: 'emp-1', data: {} }] }
];

// ── THE REQUIREMENT IS STATED HERE, NOT READ FROM THE SUBJECT ─────────────
// The first draft filtered over the module's own `NEVER_STORED`, and the
// sabotage run caught that immediately: emptying `NEVER_STORED` to `[]` left
// all six [scope] arms GREEN (30 passed, 1 failed) because an empty filter
// finds nothing to complain about, and only the control noticed. An arm whose
// assertion is supplied by the thing it is testing cannot fail when that thing
// is wrong -- the most-repeated defect shape on this platform, reproduced here
// on the way to avoiding it.
//
// So the three keys are WRITTEN DOWN as the requirement. The module's list is
// still read, and the control below asserts it is a SUPERSET: adding a fourth
// scope key to api/_lib/blob.js does not break this suite, removing one of
// these three turns six arms and the control red together.
const REQUIRED_STRIPPED = ['license_hash', 'app_id', 'p_license_hash'];
const { NEVER_STORED } = require('./_lib/blob');

(async function () {
  console.log('STORED BLOB -- scope keys and mapped columns never reach `data`');
  console.log('  scope keys REQUIRED stripped (stated here, not read from '
    + 'the subject): ' + JSON.stringify(REQUIRED_STRIPPED));
  console.log('  the module currently declares: ' + JSON.stringify(NEVER_STORED));

  for (const u of UNITS) {
    section(u.label + '  (' + u.app + ', role ' + u.role + ')');

    // ONE write per unit, three assertions off the same sent body: the arms are
    // about one request's content, and re-driving the branch three times would
    // make three chances for a fixture to diverge.
    const calls = [];
    const h = loadHandler(HASH_A, u.app, postgrestMock(u.rows, calls));
    const res = mockRes();
    const payload = Object.assign({}, u.payload, {
      license_hash: HASH_B, app_id: 'not-this-app', p_license_hash: HASH_B
    });
    await h(mockReq({ action: 'write', resource: u.resource, payload: payload },
                    HASH_A, u.app, u.role), res);
    const post = firstPost(calls);

    await test(u.label + ' [reached] the branch actually issued its write',
      async () => {
        assert.ok(post, 'UNREACHED: no POST was sent; the handler answered '
          + res.statusCode + ' ' + JSON.stringify(res.body)
          + ' -- every assertion below would pass vacuously on a request that '
          + 'never reached the blob. Fix the fixture, not the assertion.');
      });
    if (!post) { continue; }
    const sent = JSON.parse(post.opts.body);
    const blob = sent.data || {};

    await test(u.label + ' [scope] no scope key reached the stored blob',
      async () => {
        const leaked = REQUIRED_STRIPPED.filter(function (k) { return k in blob; });
        assert.deepStrictEqual(leaked, [],
          u.label + ' stored ' + JSON.stringify(leaked) + ' inside data: '
          + JSON.stringify(Object.keys(blob)) + '. A scope key inside the blob '
          + 'is echoed back on read as a field the row\'s real tenant column '
          + 'contradicts.');
      });

    await test(u.label + ' [columns] no MAPPED COLUMN key reached the blob',
      async () => {
        const leaked = u.columns.filter(function (k) { return k in blob; });
        assert.deepStrictEqual(leaked, [],
          u.label + ' stored mapped column(s) ' + JSON.stringify(leaked)
          + ' inside data. This branch\'s read spreads the blob AFTER the '
          + 'columns, so each one shadows the real value on every read.');
      });

    await test(u.label + ' [survives] an ordinary payload field came through',
      async () => {
        const [k, v] = u.survivor;
        assert.strictEqual(blob[k], v,
          u.label + ' did not store ' + k + ': ' + JSON.stringify(blob)
          + ' -- the strip is OVER-BROAD, which deletes a customer\'s data '
          + 'silently on every save and is the half of this failure nobody '
          + 'gets an error about.');
        (u.mustSurvive || []).forEach(function (extra) {
          assert.ok(extra in blob,
            u.label + ' stripped ' + extra + ', which is NOT a mapped column '
            + 'on this branch -- the read maps the id column to `id`, so a '
            + 'payload copy under its own name shadows nothing and is real '
            + 'data.');
        });
      });

    await test(u.label + ' [row] the row itself is written under tenant A',
      async () => {
        assert.strictEqual(sent.license_hash, HASH_A,
          'the row was written under ' + JSON.stringify(sent.license_hash)
          + ' rather than the hash the handler derived from the bearer key');
      });
  }

  // ── THE CONTROL: THIS SUITE MUST BE ABLE TO FAIL ─────────────────────────
  // NEVER_STORED is read from the module, so an empty list would make every
  // [scope] arm above assert nothing and pass. That is the exact shape this
  // platform keeps recording -- a check that stops checking and says nothing.
  section('CONTROL -- the guard on the guard');
  await test('the module still declares every key this suite requires',
    async () => {
      assert.ok(Array.isArray(NEVER_STORED),
        'NEVER_STORED is not a list: ' + JSON.stringify(NEVER_STORED));
      const missing = REQUIRED_STRIPPED.filter(function (k) {
        return NEVER_STORED.indexOf(k) === -1;
      });
      assert.deepStrictEqual(missing, [],
        'api/_lib/blob.js no longer declares ' + JSON.stringify(missing)
        + '. SUPERSET, not equality, on purpose: a FOURTH scope key added to '
        + 'the module must not turn this suite red, and one REMOVED from it '
        + 'must -- together with the six [scope] arms, which state the three '
        + 'keys themselves rather than reading them from the subject.');
    });

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
