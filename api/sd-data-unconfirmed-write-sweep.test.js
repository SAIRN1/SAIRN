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
      // A branch may POST to an RPC before it PATCHes -- rf_invoices `issue`
      // calls the sequential invoice-number allocator first, and answering that
      // with the PATCH fixture made the branch refuse 502 before the line under
      // test was ever reached. Only set for sites that need it.
      if (method === 'POST' && opts.rpcBody !== undefined) {
        return { ok: true, status: 200, json: async () => opts.rpcBody };
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
    missIs: 404, unknownIs: 502 },

  // ── FOUR MORE, FOUND 2026-09-21 AND INVISIBLE TO THE OLD PREDICATE ──────
  // Same defect, different spelling of the read: `await r.json()` with no
  // catch. The predicate above now walks the PATCH instead of the read, so it
  // would find them; these arms drive the refusals it cannot see.
  { name: 'sd_quote_requests promote/decline (:2634)',
    app: 'stonedesk', role: 'owner',
    read: [{ request_id: 'QR-1', status: 'new', data: { id: 'QR-1' } }],
    body: { action: 'write', resource: 'sd_quote_requests',
            payload: { id: 'QR-1', status: 'promoted' } },
    missIs: 409, missCode: 'QUOTE_REQUEST_RACE', unknownIs: 502 },
  { name: 'rf_schedule set_status (:8064) -- it echoed the requested status back',
    app: 'sairnroofing', role: 'owner',
    read: [{ schedule_id: 'SC-1', data: { id: 'SC-1', job_id: 'J-1', crew_day: '2026-09-21' } }],
    body: { action: 'set_status', resource: 'rf_schedule',
            payload: { schedule_id: 'SC-1', status: 'done' } },
    missIs: 409, missCode: 'SCHEDULE_RACE', unknownIs: 502 },
  { name: 'rf_invoices issue (:7500) -- a MISS spends an invoice number',
    app: 'sairnroofing', role: 'owner',
    rpc: [{ invoice_number: 'INV-0007', invoice_seq: 7 }],
    // status lives on the ROW, not inside data -- the branch reads
    // found.row.status, and a row without it short-circuits as already_issued
    // before the PATCH is ever sent.
    read: [{ invoice_id: 'IV-1', status: 'draft', data: { id: 'IV-1', lines: [], payments: [] } }],
    body: { action: 'issue', resource: 'rf_invoices',
            payload: { invoice_id: 'IV-1', issue_date: '2026-09-21' } },
    missIs: 409, missCode: 'INVOICE_ISSUE_RACE', unknownIs: 502 },
  { name: 'rf_invoices add_payment (:7536)',
    app: 'sairnroofing', role: 'owner',
    read: [{ invoice_id: 'IV-1', status: 'issued', data: { id: 'IV-1', lines: [], payments: [] } }],
    body: { action: 'add_payment', resource: 'rf_invoices',
            payload: { invoice_id: 'IV-1',
                       payment: { payment_id: 'PMT-1', amount: 100,
                                  received_on: '2026-09-21', method: 'check' } } },
    missIs: 409, missCode: 'INVOICE_PAYMENT_RACE', unknownIs: 502 }
];

// ── THE PREDICATE, AND IT IS THE HALF THAT KEEPS THIS TRUE ────────────────
// Re-derived from the source on every run rather than pinned to a count. A
// number would go stale the first time a site is legitimately added or
// removed; this asks the question instead.
// ── WIDENED 2026-09-21, AND THE CONDITION THAT WENT WAS THE SYMPTOM ──────
// The first version keyed on `.json().catch(` -- which is how the four
// original sites happened to be WRITTEN, not what made them wrong. What makes
// the defect is: a representation PATCH, a result whose row count is never
// checked, and a 200 that reports success anyway. A site reading the body with
// a bare `await r.json()` has the identical defect and was skipped before the
// other conditions ever ran.
//
// FOUR SUCH SITES WERE LIVE IN THIS FILE while this guard reported it clean:
//   :2634  sd_quote_requests promote/decline -- the body was read and NEVER
//          consulted; the 200 carried an object assembled locally.
//   :7500  rf_invoices issue -- answered ok:true with invoice_number,
//          invoice_seq and issue_date echoed, on a PATCH that matched nothing,
//          after the sequential allocator had already SPENT that number.
//   :7536  rf_invoices add_payment -- ok:true, data null, summary null.
//   :8064  rf_schedule set_status -- echoed back the STATUS THE CALLER SENT.
// All four are repaired; the predicate now walks the PATCH rather than the
// spelling of the read, so it would have found them.
//
// ── AND THE POST EXCLUSION NOW ANCHORS ON THE CALL, NOT ON A LINE COUNT ──
// It used to scan twelve lines backwards for `method: 'POST'`, so an unguarded
// representation-PATCH twelve lines below an unrelated POST was silently
// excluded -- a window that reads across a branch boundary, which is the
// mistake tools/cross_tenant_isolation_scope.py's _block_after() records. It
// hid nothing when measured, and it failed in the dangerous direction. The
// method is now read from the SAME fetch() options block as the PATCH.
// TAKES THE SOURCE AS AN ARGUMENT so the non-vacuity arm below can drive THIS
// function against fixtures instead of retyping its conditions. The first
// version of that arm DID retype them -- and when this predicate was widened
// on 2026-09-21 the arm went on testing the OLD logic, passing, and proving
// nothing about the code it exists to check. A control that is a copy of its
// subject stops being a control the moment the subject changes.
function unguardedIn(source) {
  const lines = source.replace(/\r\n/g, '\n').split('\n');
  const out = [];
  lines.forEach(function (l, idx) {
    if (!/method:\s*'PATCH'/.test(l)) return;
    // The Prefer header sits in the same options object as the method, within
    // a line or two either side -- not twelve lines back.
    const optsBlock = lines.slice(Math.max(0, idx - 3), idx + 4).join('\n');
    if (!/return=representation/.test(optsBlock)) return;   // not a representation write
    // Everything the handler does with the answer, before the next branch.
    const after = lines.slice(idx, idx + 30).join('\n');
    if (/wroteRow\(/.test(after)) return;                                  // guarded, the platform way
    if (/!\w+\.length|\.length\s*===\s*0|\.length\s*<\s*1/.test(after)) return;  // guarded by hand
    if (!/res\.status\(200\)\.json\(/.test(after)) return;               // never reports success
    out.push(idx + 1);
  });
  return out;
}
function unguardedSites() {
  return unguardedIn(fs.readFileSync(path.join(__dirname, 'sd-data.js'), 'utf8'));
}

(async function () {
  console.log('api/sd-data.js -- no representation-PATCH reports an unconfirmed write');

  for (const site of SITES) {
    section(site.name);
    APP_ID = site.app;

    await test('a PATCH that MATCHED answers 200 ok:true', async () => {
      const m = mock({ rpcBody: site.rpc, readRows: site.read, patchBody: [{ data: {} }] });
      const h = load(m.fn);
      const res = mockRes();
      await h(req(site.body, site.app, site.role), res);
      assert.strictEqual(res.statusCode, 200,
        'a real write must still succeed -- the fix must not break the true '
        + 'positive. Got ' + res.statusCode + ' ' + JSON.stringify(res.body));
      assert.strictEqual(res.body.ok, true, JSON.stringify(res.body));
    });

    await test('a PATCH that matched ZERO rows answers ' + site.missIs + ', not ok:true', async () => {
      const m = mock({ rpcBody: site.rpc, readRows: site.read, patchBody: [] });
      const h = load(m.fn);
      const res = mockRes();
      await h(req(site.body, site.app, site.role), res);
      assert.notStrictEqual(res.body && res.body.ok, true,
        'a write that matched NOTHING was reported as done: '
        + JSON.stringify(res.body));
      assert.strictEqual(res.statusCode, site.missIs, JSON.stringify(res.body));
      // missCode, not a hardcoded NOT_FOUND. The four sites added 2026-09-21
      // answer 409 with a named race code, because each of them READ the row
      // moments before the PATCH -- so a zero-row match is the row moving, not
      // the row having never been there. Same call the slab reservation makes.
      assert.strictEqual(res.body.error.code, site.missCode || 'NOT_FOUND', JSON.stringify(res.body));
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
      const m = mock({ rpcBody: site.rpc, readRows: site.read, patchBody: { data: {} } });
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
      const m = mock({ rpcBody: site.rpc, readRows: site.read, patchThrows: true });
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

  await test('the predicate is not vacuous -- the REAL one, driven both directions', async () => {
    // A NEGATIVE CONTROL ON THE PREDICATE ITSELF, and it calls the real
    // unguardedIn(). A checker that matches nothing passes its own subject
    // trivially, which is how a guard stops guarding without anyone noticing.
    const patch = [
      "const w = await fetch(rest('t?license_hash=eq.' + enc(licHash)), {",
      "  method: 'PATCH',",
      "  headers: Object.assign({}, headers, { Prefer: 'return=representation' }),",
      "  body: JSON.stringify({ data: marked })",
      "});"
    ];
    const withCatch = patch.concat([
      "const wRows = await w.json().catch(function () { return null; });",
      "if (!w.ok) return upstream(res, wRows);",
      "res.status(200).json({ ok: true, data: marked });"
    ]).join('\n');
    // THE SHAPE THE OLD PREDICATE COULD NOT SEE. Four live sites read the body
    // this way; the catch was how the first four happened to be written, not
    // what made them wrong.
    const bareJson = patch.concat([
      "const rows = await w.json();",
      "if (!w.ok) return upstream(res, rows);",
      "const saved = Array.isArray(rows) && rows[0];",
      "res.status(200).json({ ok: true, status: saved ? saved.status : status });"
    ]).join('\n');
    const guardedByHelper = patch.concat([
      "const rows = await w.json().catch(function () { return null; });",
      "if (!w.ok) return upstream(res, rows);",
      "const says = wroteRow(rows);",
      "if (says === 'MISSED') { res.status(409).json({ error: { code: 'RACE' } }); return; }",
      "res.status(200).json({ ok: true, data: rows[0] });"
    ]).join('\n');
    const guardedByHand = patch.concat([
      "const rows = await w.json();",
      "if (!w.ok) return upstream(res, rows);",
      "if (!Array.isArray(rows) || !rows.length) { res.status(409).json({ error: {} }); return; }",
      "res.status(200).json({ ok: true, data: rows[0] });"
    ]).join('\n');
    const upsert = [
      "const w = await fetch(rest('t?on_conflict=license_hash,id'), {",
      "  method: 'POST',",
      "  headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),",
      "  body: JSON.stringify({ data: marked })",
      "});",
      "const rows = await w.json();",
      "if (!w.ok) return upstream(res, rows);",
      "res.status(200).json({ ok: true, data: rows[0] });"
    ].join('\n');

    assert.strictEqual(unguardedIn(withCatch).length, 1,
      'the predicate no longer finds the shape the original four were written in');
    assert.strictEqual(unguardedIn(bareJson).length, 1,
      'the predicate still cannot see a body read WITHOUT a catch -- the four sites '
      + 'repaired on 2026-09-21 would be invisible to it again');
    assert.strictEqual(unguardedIn(guardedByHelper).length, 0,
      'a site guarded by wroteRow() is reported, so the empty result above means nothing');
    assert.strictEqual(unguardedIn(guardedByHand).length, 0,
      'a site guarded by a hand-written row-count check is reported');
    assert.strictEqual(unguardedIn(upsert).length, 0,
      'an UPSERT is reported -- POST is a different shape and is excluded on purpose');
  });

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
