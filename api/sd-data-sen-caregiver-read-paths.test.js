// api/sd-data-sen-caregiver-read-paths.test.js
//
// REQUIREMENT: NO response from api/sd-data.js carries a caregiver's
//   background-check date, state-issued caregiver ID or free-text HR notes to a
//   caller outside owner/billing -- on ANY path that reads sen_caregivers, not
//   just the one that was fixed.
//
// Run:  node api/sd-data-sen-caregiver-read-paths.test.js
//
// ── WHY THIS EXISTS SEPARATELY FROM THE SCOPE SUITE (batch b5 item 5) ─────
// api/sd-data-sen-caregiver-pii-scope.test.js proves the REDACTION on
// `sen_caregivers/read` is correct and complete. It says nothing at all about
// whether some OTHER branch reads the same table and returns the same fields,
// which is the question that actually matters once a field is declared
// sensitive: a redaction on one path is a redaction on one path.
//
// AND THERE IS A SECOND PATH. `sen_visits/readiness` fetches
// sen_caregivers?select=caregiver_id,data and builds a caregiversById map from
// the WHOLE blob. It was not found by reading the fix; it was found by grepping
// for every `fetch(rest('sen_caregivers` in the file, which is the only method
// that can answer "every path".
//
// ── THE PATH COUNT IS DERIVED AND ASSERTED, WHICH IS THE WHOLE POINT ──────
// The arm below counts the sen_caregivers FETCH SITES in api/sd-data.js and
// fails if the number changes. That is deliberately brittle: a third read path
// added later is exactly the event this file exists to catch, and a suite that
// silently covered 2 of 3 would report clean while the new path leaked. If the
// count changes, do not raise the number -- add an arm for the new path.
//
// ── WHAT "SAFE" MEANS PER PATH, BECAUSE IT IS NOT THE SAME ANSWER ─────────
//   sen_caregivers/read     REDACTS. Returns rows, so the three fields are
//                           removed for anyone outside owner/billing and the
//                           response declares it with hr_fields_visible.
//   sen_visits/readiness    CONSUMES WITHOUT EMITTING. It reads
//                           caregiver.name and caregiver.state_caregiver_id to
//                           decide whether each is PRESENT, and returns only
//                           miss-reasons built from string literals. So it must
//                           NOT be redacted at the fetch -- redacting there
//                           would make every visit report a missing state
//                           caregiver ID -- and it must never echo a value.
//                           Those are two different claims and both are armed.
//
// ── WHAT THIS DOES NOT DO ─────────────────────────────────────────────────
// It does not test the DATABASE, makes no live request, and does not cover the
// CLIENT. sairnsenior.html's own roster rendering is asserted nowhere here; the
// b4 commit added a Restricted badge there and a click-through has never been
// run. It also does not cover sen_clients, which is a different resource with a
// different gate.

'use strict';

process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET
  || ['sen', 'caregiver', 'paths', 'fixture'].join('-');
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://test.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'test-key';

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const { signSessionToken, ROLES_BY_APP } = require('./_lib/auth');

const HASH = 'sen-tenant-hash';
const APP = 'sairnsenior';

// The three fields. Values are DISTINCTIVE STRINGS, not realistic ones, so a
// leak anywhere in a response body is findable by substring regardless of what
// shape it arrives in -- a nested object, a joined string, an error message.
const SECRETS = Object.freeze({
  bgcheck_date: '2026-02-14-ZZBGCHECKZZ',
  state_caregiver_id: 'OH-STNA-ZZSTATEIDZZ',
  notes: 'ZZHRNOTESZZ disclosed a prior conviction at interview'
});
const KEPT = ['id', 'name', 'phone', 'cpr_expiry', 'status',
              'aide_type', 'program', 'employee_id', 'branch_id'];
const HR_ROLES = ['owner', 'billing'];

let pass = 0, fail = 0;
const FAILED = [];
async function test(name, fn) {
  try { await fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; FAILED.push(name); }
}
function section(t) { console.log('\n' + t); }

function mockRes() {
  const res = { statusCode: null, body: null };
  res.status = function (c) { res.statusCode = c; return res; };
  res.json = function (b) { res.body = b; return res; };
  return res;
}

function caregiverRow(id, employeeId) {
  return {
    license_hash: HASH, app_id: APP, caregiver_id: id,
    data: Object.assign({
      name: 'Dana Okonkwo', phone: '330-555-0147', cpr_expiry: '2027-03-01',
      status: 'active', aide_type: 'STNA', program: 'PASSPORT',
      employee_id: employeeId || 'emp-7', branch_id: 'BR-2'
    }, SECRETS)
  };
}
function visitRow(id, employeeId) {
  return {
    license_hash: HASH, app_id: APP, visit_id: id,
    assigned_employee_id: employeeId || 'emp-7',
    data: { client_id: 'CL-1', assigned_employee_id: employeeId || 'emp-7',
            scheduled_date: '2026-10-01', status: 'completed',
            clock_in_at: '2026-10-01T13:00:00Z', clock_out_at: '2026-10-01T15:00:00Z' }
  };
}
function clientRow(id) {
  return { license_hash: HASH, app_id: APP, client_id: id,
           data: { name: 'A Client', member_id: 'M-1' } };
}

// Serves whichever table the URL names. Honours select= so the handler receives
// the column list it actually asked for.
function pgMock(tables, calls) {
  return async function (url, opts) {
    const u = String(url);
    calls.push({ url: u, method: (opts && opts.method) || 'GET' });
    const q = u.indexOf('?') >= 0 ? u.slice(u.indexOf('?') + 1) : '';
    let select = null;
    const eqs = [];
    q.split('&').forEach(function (part) {
      const m = part.match(/^([a-z0-9_]+)=eq\.(.*)$/);
      if (m) { eqs.push([m[1], decodeURIComponent(m[2])]); return; }
      const s = part.match(/^select=(.*)$/);
      if (s) select = decodeURIComponent(s[1]).split(',').map((x) => x.trim());
    });
    if (/_employee_auth\?/.test(u)) {
      const forHash = (eqs.filter((kv) => kv[0] === 'license_hash')[0] || [])[1];
      return { ok: true, status: 200, json: async () => [
        { license_hash: forHash || HASH, employee_id: 'emp-1', role: 'owner', active: true }] };
    }
    if (opts && opts.method === 'POST') {
      return { ok: true, status: 200, json: async () => [JSON.parse(opts.body)] };
    }
    const tbl = (u.split('/rest/v1/')[1] || u).split('?')[0];
    const rows = (tables[tbl] || []).filter(
      (r) => eqs.every((kv) => String(r[kv[0]]) === kv[1]));
    const projected = rows.map((r) => {
      if (!select || select.indexOf('*') !== -1) return r;
      const out = {};
      select.forEach((c) => { if (c in r) out[c] = r[c]; });
      return out;
    });
    return { ok: true, status: 200, json: async () => projected };
  };
}

function loadHandler(fetchImpl) {
  delete require.cache[require.resolve('./_lib/license')];
  require.cache[require.resolve('./_lib/license')] = {
    exports: {
      validateLicenseKey: async () => ({
        valid: true, active: true, license_hash: HASH,
        trial_ends_at: null, stripe_subscription_id: null, app_id: APP })
    }
  };
  global.fetch = fetchImpl;
  delete require.cache[require.resolve('./sd-data.js')];
  return require('./sd-data.js');
}

async function callAs(role, body, tables) {
  const calls = [];
  const h = loadHandler(pgMock(tables || {}, calls));
  const res = mockRes();
  await h({
    method: 'POST',
    headers: {
      authorization: 'Bearer KEY-FOR-' + HASH,
      'x-sd-auth': signSessionToken({ app: APP, employee_id: 'emp-1', role, license_hash: HASH })
    },
    body
  }, res);
  return { res, calls };
}

// THE LEAK TEST ITSELF: serialise the WHOLE response and look for the marker
// strings. Asserting on a named field only catches a leak that arrives in the
// shape you predicted; a substring sweep catches one nested inside an error
// message, a joined label or a field nobody thought of.
function leaksIn(body) {
  const blob = JSON.stringify(body === undefined ? null : body);
  return Object.keys(SECRETS).filter((k) => blob.indexOf(SECRETS[k]) !== -1);
}

(async function () {
  console.log('sen_caregivers -- EVERY read path, field-level PII redaction (b5 item 5)');

  const SRC = fs.readFileSync(path.join(__dirname, 'sd-data.js'), 'utf8');
  // COUNTS READ SITES, NOT ALL FETCH SITES, AND THE FIRST VERSION DID NOT.
  // `fetch(rest('sen_caregivers?` also matches the WRITE upsert at :6400
  // (`?on_conflict=`), so the arm reported 3 and read as "an undiscovered third
  // read path". A read is the one that asks for columns: `select=`. Recorded
  // rather than just corrected, because a count that is wrong in the ALARMING
  // direction is the lucky case -- the same regex one character looser would
  // have been wrong in the reassuring one.
  // `[^\n]*` and NOT `[^)]*`: the URL is built by concatenation and contains
  // `enc(licHash)`, so a close-paren appears before `select=` and the first
  // corrected regex matched ZERO. Bounded to the same LINE instead, which both
  // read sites are. The arm went red both times rather than quietly matching
  // the wrong thing, which is the only reason this was cheap to find.
  const FETCH_SITES = (SRC.match(/fetch\(rest\('sen_caregivers\?[^\n]*select=/g) || []).length;
  const nonHr = (ROLES_BY_APP[APP] || []).filter((r) => HR_ROLES.indexOf(r) === -1);

  section('A. THE PATH INVENTORY, DERIVED FROM THE SOURCE');

  await test('api/sd-data.js reads sen_caregivers from EXACTLY 2 places, and '
    + 'this arm fails if a third is added', () => {
      assert.strictEqual(FETCH_SITES, 2,
        'found ' + FETCH_SITES + ' sen_caregivers fetch site(s). If a path was '
        + 'ADDED, do not raise this number -- add an arm for it below. A suite '
        + 'that silently covers 2 of 3 reports clean while the new path leaks. '
        + 'If a path was REMOVED, the arm for it below is now dead and should go '
        + 'with it.');
    });

  await test('...and there is at least one role outside owner/billing to test '
    + 'with, so every arm below is not vacuous', () => {
      assert.ok(nonHr.length > 0,
        'ROLES_BY_APP.' + APP + ' is ' + JSON.stringify(ROLES_BY_APP[APP]));
    });

  await test('...and the fixture really CARRIES all three secrets, so an '
    + '"absent" result is a removal and not an empty fixture', () => {
      const d = caregiverRow('CG-1').data;
      const missing = Object.keys(SECRETS).filter((k) => d[k] !== SECRETS[k]);
      assert.deepStrictEqual(missing, [], 'fixture is missing ' + JSON.stringify(missing));
    });

  section('B. PATH 1 -- sen_caregivers/read. REDACTS.');

  for (const role of nonHr) {
    await test('[' + role + '] no marker string appears ANYWHERE in the '
      + 'serialised response', async () => {
        const { res } = await callAs(role, { action: 'read', resource: 'sen_caregivers' },
          { sen_caregivers: [caregiverRow('CG-1'), caregiverRow('CG-2', 'emp-8')] });
        assert.strictEqual(res.statusCode, 200,
          'answered ' + res.statusCode + ' ' + JSON.stringify(res.body));
        const leaked = leaksIn(res.body);
        assert.deepStrictEqual(leaked, [],
          role + ' received ' + JSON.stringify(leaked) + '. Body: '
          + JSON.stringify(res.body).slice(0, 400));
      });

    await test('[' + role + '] ...and the nine fields the app needs survived, '
      + 'on EVERY row and not just the first', async () => {
        const { res } = await callAs(role, { action: 'read', resource: 'sen_caregivers' },
          { sen_caregivers: [caregiverRow('CG-1'), caregiverRow('CG-2', 'emp-8')] });
        const rows = (res.body && res.body.data) || [];
        assert.strictEqual(rows.length, 2, 'expected 2 rows, got ' + rows.length);
        rows.forEach((item, i) => {
          const missing = KEPT.filter((f) => !(f in item));
          assert.deepStrictEqual(missing, [],
            'row ' + i + ' lost ' + JSON.stringify(missing)
            + '. An empty roster breaks senIsScheduler, certDaysUntil and the '
            + 'visit join -- which the leak arm above cannot see.');
        });
      });
  }

  for (const role of HR_ROLES) {
    await test('[' + role + '] NEGATIVE HALF: all three markers ARE returned, '
      + 'so the redaction is scoped and not a blanket wipe', async () => {
        const { res } = await callAs(role, { action: 'read', resource: 'sen_caregivers' },
          { sen_caregivers: [caregiverRow('CG-1')] });
        const leaked = leaksIn(res.body).sort();
        assert.deepStrictEqual(leaked, Object.keys(SECRETS).sort(),
          role + ' is inside the HR tier and received only '
          + JSON.stringify(leaked) + '. If management cannot read these back the '
          + 'redaction is a wipe: the write path sends whole records, so nobody '
          + 'could ever restore them.');
      });
  }

  section('C. PATH 2 -- sen_visits/readiness. CONSUMES WITHOUT EMITTING.');

  // ── THE JOIN KEY, AND THE FIRST FIXTURE GOT IT WRONG ──────────────────
  // readiness builds `caregiversById` keyed on `caregiver_id` and looks up
  // `caregivers[visit.assigned_employee_id]`. So for the lookup to resolve at
  // all, the caregiver ROW ID must equal the visit's assigned_employee_id.
  // With `caregiver_id: 'CG-1'` against `assigned_employee_id: 'emp-7'` every
  // visit reported "a caregiver record that could not be found" and the
  // state-caregiver-ID branch was never reached -- so the no-leak arms were
  // passing against a path that had consumed nothing. That is the
  // check-that-tests-nothing shape, caught by the arm written to catch it.
  const CG_KEY = 'emp-7';
  const READINESS_TABLES = {
    sen_visits: [visitRow('V-1', CG_KEY)],
    sen_clients: [clientRow('CL-1')],
    sen_caregivers: [caregiverRow(CG_KEY, CG_KEY)],
    sen_settings: [{ license_hash: HASH, app_id: APP, setting_key: 'evv_config',
                     data: { state: 'OH' } }]
  };

  for (const role of nonHr.concat(HR_ROLES)) {
    await test('[' + role + '] readiness returns NO marker string -- it reads '
      + 'the blob and emits only miss-reasons', async () => {
        const { res } = await callAs(role,
          { action: 'readiness', resource: 'sen_visits' }, READINESS_TABLES);
        if (res.statusCode !== 200) {
          assert.deepStrictEqual(leaksIn(res.body), [],
            'readiness answered ' + res.statusCode + ' AND the refusal body '
            + 'carries a marker: ' + JSON.stringify(res.body).slice(0, 300));
          return; // a refusal with no leak is an acceptable outcome for this arm
        }
        const leaked = leaksIn(res.body);
        assert.deepStrictEqual(leaked, [],
          role + ' received ' + JSON.stringify(leaked)
          + ' through the readiness report. Body: '
          + JSON.stringify(res.body).slice(0, 400));
      });
  }

  await test('...and readiness STILL FETCHES the unredacted blob, which is '
    + 'correct and is the arm that stops somebody "fixing" it', async () => {
      // THE TRAP THIS ARM GUARDS: redacting at the FETCH would make every visit
      // report a missing state caregiver ID, because checkVisit() reads
      // caregiver.state_caregiver_id to decide whether one is on file. The
      // right boundary for this path is the RESPONSE, and the response emits
      // only literals. Asserting the fetch is unredacted makes that explicit
      // instead of leaving it as an accident of where the code happens to be.
      const { calls } = await callAs('owner',
        { action: 'readiness', resource: 'sen_visits' }, READINESS_TABLES);
      const cg = calls.filter((c) => /sen_caregivers\?/.test(c.url));
      assert.ok(cg.length >= 1,
        'readiness did not fetch sen_caregivers at all -- either the path moved '
        + 'or the fixture no longer reaches it: '
        + JSON.stringify(calls.map((c) => c.url)));
      assert.ok(cg.every((c) => /select=caregiver_id,data/.test(c.url)),
        'the readiness fetch no longer asks for the whole data blob: '
        + JSON.stringify(cg.map((c) => c.url)) + '. If this was a deliberate '
        + 'narrowing, re-check that the state-caregiver-ID element still '
        + 'reports correctly rather than reporting every visit as missing it.');
    });

  await test('...and a caregiver WITH a state ID is reported as not-missing '
    + 'while one WITHOUT it is -- so the field is really being read, and the '
    + 'no-leak arms above are not passing because nothing was consumed',
    async () => {
      const withId = await callAs('owner',
        { action: 'readiness', resource: 'sen_visits' }, READINESS_TABLES);
      const bare = caregiverRow(CG_KEY, CG_KEY);
      delete bare.data.state_caregiver_id;
      const without = await callAs('owner',
        { action: 'readiness', resource: 'sen_visits' },
        Object.assign({}, READINESS_TABLES, { sen_caregivers: [bare] }));
      const says = (r) => JSON.stringify((r.res.body) || {}).indexOf('state caregiver ID') !== -1;
      assert.ok(!says(withId) && says(without),
        'the readiness report did not change when state_caregiver_id was '
        + 'removed (with: ' + says(withId) + ', without: ' + says(without)
        + '). If it never reads the field, the no-leak arms prove nothing '
        + 'about a path that consumes it.');
    });

  section('D. THE WRITE PATH, because the redaction depends on it');

  await test('a non-HR role cannot WRITE sen_caregivers -- the only reason the '
    + 'redaction cannot erase the three fields on a round trip', async () => {
      const { res, calls } = await callAs(nonHr[0],
        { action: 'write', resource: 'sen_caregivers',
          payload: { id: 'CG-1', name: 'Dana Okonkwo' } },
        { sen_caregivers: [caregiverRow('CG-1')] });
      assert.strictEqual(res.statusCode, 403,
        nonHr[0] + ' got ' + res.statusCode + ' ' + JSON.stringify(res.body));
      assert.ok(!calls.some((c) => c.method === 'POST'),
        'the refusal still POSTed: ' + JSON.stringify(calls.map((c) => c.url)));
    });

  if (FAILED.length) {
    console.log('\n' + FAILED.length + ' ARM(S) FAILED:');
    FAILED.forEach((f) => console.log('  - ' + f));
  }
  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
