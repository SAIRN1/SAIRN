// api/sd-data-dental-provider-scope.test.js
// Plain node:assert tests. Run: node api/sd-data-dental-provider-scope.test.js
//
// Covers the SAIRNdental provider-scoped patient read added 2026-08-27:
//   - owner and frontdesk keep practice-wide visibility;
//   - a LINKED provider sees only patients they have an appointment with;
//   - an UNLINKED provider sees NOTHING, and is told why, with a fix path;
//   - the provider registry is owner-only to WRITE, because once it carries
//     linked_employee_id it IS the access-control table for all of the above.
//
// The link is `linked_employee_id` on the dnt_providers data blob. There is no
// migration behind it -- dnt_providers is (license_hash, provider_id, data
// jsonb) -- which is exactly why this was buildable without touching Supabase.
//
// WHAT THESE TESTS ARE REALLY GUARDING. The failure mode that made this whole
// feature dangerous is not "a provider sees too much"; it is "a provider sees
// an empty list and believes the practice has no patients." A permission check
// that returns 200 [] is indistinguishable from an empty practice. So every
// refusal below is asserted to be a 403 with a NAMED code, never a quiet empty
// success, and the unlinked message is asserted to actually point somewhere.

const assert = require('assert');
const { signSessionToken } = require('./_lib/auth');

const LIC_HASH = 'test-hash';

function mockRes() {
  var res = { statusCode: null, body: null };
  res.status = function (code) { res.statusCode = code; return res; };
  res.json = function (payload) { res.body = payload; return res; };
  return res;
}
function mockReq(body, token) {
  var headers = { authorization: 'Bearer GOOD-KEY' };
  if (token) headers['x-sd-auth'] = token;
  return { method: 'POST', headers: headers, body: body };
}
function tokenFor(role, employeeId) {
  return signSessionToken({ app: 'sairndental', employee_id: employeeId || ('emp-' + role), role: role, license_hash: LIC_HASH });
}

// A routing fetch stub. Each entry is [substring, rowsOrStatus]. Recording every
// URL lets a test assert WHERE the filter ran -- in the database or in JS --
// which matters for dnt_appointments, whose rows can be ~1.26 MB each.
function routedFetch(routes, seen) {
  return async function (url) {
    if (seen) seen.push(String(url));
    for (const [needle, rows] of routes) {
      if (String(url).indexOf(needle) !== -1) {
        if (typeof rows === 'number') return { ok: false, status: rows, json: async () => ({ message: 'stub' }) };
        return { ok: true, status: 200, json: async () => rows };
      }
    }
    return { ok: true, status: 200, json: async () => [] };
  };
}
function loadHandler(fetchImpl) {
  delete require.cache[require.resolve('./_lib/license')];
  require.cache[require.resolve('./_lib/license')] = {
    exports: {
      validateLicenseKey: async function () {
        return { valid: true, active: true, license_hash: LIC_HASH, trial_ends_at: null, stripe_subscription_id: null };
      }
    }
  };
  global.fetch = fetchImpl;
  delete require.cache[require.resolve('./sd-data.js')];
  return require('./sd-data.js');
}

// One linked provider (PV-1 -> emp-provider), one unlinked provider row.
const PROVIDER_ROWS = [
  { provider_id: 'PV-1', data: { id: 'PV-1', name: 'Dr Linked', linked_employee_id: 'emp-provider' } },
  { provider_id: 'PV-2', data: { id: 'PV-2', name: 'Dr Unlinked' } }
];
const APPOINTMENT_ROWS_PV1 = [
  { data: { id: 'AP-1', patient_id: 'PT-1', provider_id: 'PV-1' } },
  { data: { id: 'AP-2', patient_id: 'PT-2', provider_id: 'PV-1' } }
];
const PATIENT_ROWS = [
  { data: { id: 'PT-1', name: 'Alice' } },
  { data: { id: 'PT-2', name: 'Bob' } },
  { data: { id: 'PT-3', name: 'Carol -- not this provider\'s patient' } }
];

let passed = 0, total = 0;
async function test(name, fn) {
  total++;
  try { await fn(); passed++; console.log('  ok - ' + name); }
  catch (err) { console.error('  FAIL - ' + name); console.error('    ' + err.message); process.exitCode = 1; }
}

async function main() {
  console.log('api/sd-data.js -- SAIRNdental provider-scoped patient read');

  process.env.SUPABASE_URL = 'https://test.supabase.co';
  process.env.SUPABASE_SERVICE_ROLE_KEY = 'test-key';
  process.env.SD_AUTH_SECRET = ['dental', 'provider', 'scope', 'fixture'].join('-');

  await test('LINKED provider reading dnt_patients -> only their own patients', async () => {
    const handler = loadHandler(routedFetch([
      ['dnt_providers?', PROVIDER_ROWS],
      ['dnt_appointments?', APPOINTMENT_ROWS_PV1],
      ['dnt_patients?', PATIENT_ROWS]
    ]));
    const res = mockRes();
    await handler(mockReq({ action: 'read', resource: 'dnt_patients' }, tokenFor('provider', 'emp-provider')), res);
    assert.strictEqual(res.statusCode, 200);
    assert.deepStrictEqual(res.body.data.map((p) => p.id), ['PT-1', 'PT-2'], 'PT-3 must not be visible');
  });

  await test('UNLINKED provider reading dnt_patients -> 403 PROVIDER_NOT_LINKED, never an empty 200', async () => {
    const handler = loadHandler(routedFetch([['dnt_providers?', PROVIDER_ROWS]]));
    const res = mockRes();
    await handler(mockReq({ action: 'read', resource: 'dnt_patients' }, tokenFor('provider', 'emp-nobody')), res);
    assert.strictEqual(res.statusCode, 403);
    assert.strictEqual(res.body.error.code, 'PROVIDER_NOT_LINKED');
    assert.ok(!('data' in res.body), 'a refusal must never carry a data array');
  });

  await test('the unlinked message actually names where the fix happens', async () => {
    const handler = loadHandler(routedFetch([['dnt_providers?', PROVIDER_ROWS]]));
    const res = mockRes();
    await handler(mockReq({ action: 'read', resource: 'dnt_patients' }, tokenFor('provider', 'emp-nobody')), res);
    const m = res.body.error.message;
    assert.ok(/Providers panel/i.test(m), 'message must point at the Providers panel, not just say "denied": ' + m);
    assert.ok(/owner/i.test(m), 'message must say who can fix it: ' + m);
  });

  await test('owner reading dnt_patients -> practice-wide, no provider lookup at all', async () => {
    const seen = [];
    const handler = loadHandler(routedFetch([['dnt_patients?', PATIENT_ROWS]], seen));
    const res = mockRes();
    await handler(mockReq({ action: 'read', resource: 'dnt_patients' }, tokenFor('owner')), res);
    assert.strictEqual(res.statusCode, 200);
    assert.strictEqual(res.body.data.length, 3);
    assert.ok(!seen.some((u) => u.indexOf('dnt_providers?') !== -1), 'owner read must not pay for a link lookup');
  });

  await test('frontdesk reading dnt_patients -> practice-wide (they book and check in anyone)', async () => {
    const handler = loadHandler(routedFetch([['dnt_patients?', PATIENT_ROWS]]));
    const res = mockRes();
    await handler(mockReq({ action: 'read', resource: 'dnt_patients' }, tokenFor('frontdesk')), res);
    assert.strictEqual(res.statusCode, 200);
    assert.strictEqual(res.body.data.length, 3);
  });

  await test('dnt_referrals is patient-scoped too (it carries patient_id and a clinical reason)', async () => {
    const handler = loadHandler(routedFetch([
      ['dnt_providers?', PROVIDER_ROWS],
      ['dnt_appointments?', APPOINTMENT_ROWS_PV1],
      ['dnt_referrals?', [
        { data: { id: 'RF-1', patient_id: 'PT-1' } },
        { data: { id: 'RF-9', patient_id: 'PT-3' } }
      ]]
    ]));
    const res = mockRes();
    await handler(mockReq({ action: 'read', resource: 'dnt_referrals' }, tokenFor('provider', 'emp-provider')), res);
    assert.strictEqual(res.statusCode, 200);
    assert.deepStrictEqual(res.body.data.map((r) => r.id), ['RF-1']);
  });

  await test('LINKED provider reading dnt_appointments -> filtered IN THE DATABASE, not in JS', async () => {
    const seen = [];
    const handler = loadHandler(routedFetch([
      ['dnt_providers?', PROVIDER_ROWS],
      ['dnt_appointments?', APPOINTMENT_ROWS_PV1]
    ], seen));
    const res = mockRes();
    await handler(mockReq({ action: 'read', resource: 'dnt_appointments' }, tokenFor('provider', 'emp-provider')), res);
    assert.strictEqual(res.statusCode, 200);
    const apptUrl = seen.filter((u) => u.indexOf('dnt_appointments?') !== -1).pop();
    assert.ok(/provider_id=eq\.PV-1/.test(apptUrl),
      'appointment rows can be ~1.26MB each -- the filter must be in the query, not after it. URL was: ' + apptUrl);
  });

  await test('UNLINKED provider reading dnt_appointments -> 403 PROVIDER_NOT_LINKED', async () => {
    const handler = loadHandler(routedFetch([['dnt_providers?', PROVIDER_ROWS]]));
    const res = mockRes();
    await handler(mockReq({ action: 'read', resource: 'dnt_appointments' }, tokenFor('provider', 'emp-nobody')), res);
    assert.strictEqual(res.statusCode, 403);
    assert.strictEqual(res.body.error.code, 'PROVIDER_NOT_LINKED');
  });

  await test('unprovisioned provider registry -> honest provisioned:false, NOT a 403 blaming the user', async () => {
    const handler = loadHandler(routedFetch([['dnt_providers?', 404]]));
    const res = mockRes();
    await handler(mockReq({ action: 'read', resource: 'dnt_patients' }, tokenFor('provider', 'emp-provider')), res);
    assert.strictEqual(res.statusCode, 200);
    assert.strictEqual(res.body.provisioned, false);
    assert.deepStrictEqual(res.body.data, []);
  });

  // --- provider registry write gate ---
  await test('provider writing dnt_providers -> 403 ROLE_NOT_PERMITTED (it is the access-control table)', async () => {
    const handler = loadHandler(routedFetch([]));
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'dnt_providers', payload: { id: 'PV-9', name: 'Self Added' } }, tokenFor('provider')), res);
    assert.strictEqual(res.statusCode, 403);
    assert.strictEqual(res.body.error.code, 'ROLE_NOT_PERMITTED');
  });

  await test('frontdesk writing dnt_providers -> 403 as well (owner-only, not management-ish)', async () => {
    const handler = loadHandler(routedFetch([]));
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'dnt_providers', payload: { id: 'PV-9', name: 'Self Added' } }, tokenFor('frontdesk')), res);
    assert.strictEqual(res.statusCode, 403);
  });

  await test('owner writing dnt_providers -> allowed', async () => {
    const handler = loadHandler(routedFetch([['dnt_providers?', [{ data: { id: 'PV-9' } }]]]));
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'dnt_providers', payload: { id: 'PV-9', name: 'New Provider' } }, tokenFor('owner')), res);
    assert.strictEqual(res.statusCode, 200);
    assert.strictEqual(res.body.ok, true);
  });

  await test('linking a login already linked to another provider -> 409 EMPLOYEE_ALREADY_LINKED', async () => {
    const handler = loadHandler(routedFetch([['dnt_providers?', PROVIDER_ROWS]]));
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'dnt_providers', payload: { id: 'PV-2', name: 'Dr Unlinked', linked_employee_id: 'emp-provider' } }, tokenFor('owner')), res);
    assert.strictEqual(res.statusCode, 409);
    assert.strictEqual(res.body.error.code, 'EMPLOYEE_ALREADY_LINKED');
  });

  await test('re-saving the SAME provider with its OWN existing link is not a clash', async () => {
    const handler = loadHandler(routedFetch([['dnt_providers?', PROVIDER_ROWS]]));
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'dnt_providers', payload: { id: 'PV-1', name: 'Dr Linked Renamed', linked_employee_id: 'emp-provider' } }, tokenFor('owner')), res);
    assert.strictEqual(res.statusCode, 200, 'editing a provider must not collide with itself -- got ' + JSON.stringify(res.body));
  });

  // ── THE UNLINKED-REFERRAL QUEUE (2026-09-11) ────────────────────────────
  // Michael's call after the gap was measured and filed: do NOT require the
  // link, make the unlinked ones findable. An unlinked referral used to be
  // filtered out for every scoped role -- the front desk saw it, the clinician
  // who had to act on it did not, and nothing said so. It failed closed, so
  // nothing leaked; the cost ran the other way, and a referral nobody can see
  // is a patient who does not get seen.
  //
  // THE THREE ARMS THAT MATTER ARE THE SECOND AND THIRD. Making unlinked rows
  // visible is easy; not widening anything else is the part worth pinning.
  await test('an UNLINKED referral is visible to a scoped provider, not invisible to everyone', async () => {
    const handler = loadHandler(routedFetch([
      ['dnt_providers?', PROVIDER_ROWS],
      ['dnt_appointments?', APPOINTMENT_ROWS_PV1],
      ['dnt_referrals?', [
        { data: { id: 'RF-1', patient_id: 'PT-1' } },            // my patient
        { data: { id: 'RF-2', patient_id: '' } },                 // unlinked
        { data: { id: 'RF-3' } },                                 // no key at all
        { data: { id: 'RF-4', patient_id: '   ' } },              // whitespace
      ]],
    ]));
    const res = mockRes();
    await handler(mockReq({ action: 'read', resource: 'dnt_referrals' }, tokenFor('provider', 'emp-provider')), res);
    assert.strictEqual(res.statusCode, 200);
    assert.deepStrictEqual(res.body.data.map((r) => r.id).sort(),
      ['RF-1', 'RF-2', 'RF-3', 'RF-4'],
      'an unlinked referral is still hidden from the clinician who must act on it');
  });

  await test('AND IT DID NOT WIDEN ANYTHING: another provider\'s patient is still hidden', async () => {
    const handler = loadHandler(routedFetch([
      ['dnt_providers?', PROVIDER_ROWS],
      ['dnt_appointments?', APPOINTMENT_ROWS_PV1],
      ['dnt_referrals?', [
        { data: { id: 'RF-1', patient_id: 'PT-1' } },
        { data: { id: 'RF-9', patient_id: 'PT-3' } },   // somebody else's patient
        { data: { id: 'RF-2', patient_id: '' } },
      ]],
    ]));
    const res = mockRes();
    await handler(mockReq({ action: 'read', resource: 'dnt_referrals' }, tokenFor('provider', 'emp-provider')), res);
    assert.strictEqual(res.statusCode, 200);
    assert.ok(res.body.data.every((r) => r.id !== 'RF-9'),
      'a LINKED referral for another provider\'s patient leaked: ' + JSON.stringify(res.body.data));
    assert.deepStrictEqual(res.body.data.map((r) => r.id).sort(), ['RF-1', 'RF-2']);
  });

  // THE SCOPING OF THE CHANGE ITSELF. An unlinked REFERRAL belongs to no
  // patient yet, so it cannot be somebody else's patient -- which is exactly
  // why it is safe there and nowhere else. dnt_patients is keyed on 'id', and
  // a row with an empty key must STILL be filtered out, or the same one-line
  // relaxation would make unlinked patient records practice-wide.
  await test('dnt_patients is NOT widened -- an empty scope key there is still filtered out', async () => {
    const handler = loadHandler(routedFetch([
      ['dnt_providers?', PROVIDER_ROWS],
      ['dnt_appointments?', APPOINTMENT_ROWS_PV1],
      ['dnt_patients?', [
        { data: { id: 'PT-1', name: 'Alice' } },
        { data: { id: '', name: 'Orphan row' } },
        { data: { name: 'No id at all' } },
      ]],
    ]));
    const res = mockRes();
    await handler(mockReq({ action: 'read', resource: 'dnt_patients' }, tokenFor('provider', 'emp-provider')), res);
    assert.strictEqual(res.statusCode, 200);
    assert.deepStrictEqual(res.body.data.map((r) => r.name), ['Alice'],
      'the unlinked-visible relaxation leaked onto dnt_patients');
  });

  // ── THE EMPTY-STRING COLLISION (2026-09-11) ─────────────────────────────
  // An UNLINKED provider row carries `linked_employee_id: ''` --
  // saveProviderEdit() stores `$('pv-edit-login').value || ''`. dntLinkedProvider()
  // matches on `x.data.linked_employee_id === session.employee_id`, so a
  // session whose employee_id were the empty string would match the FIRST
  // unlinked provider by `'' === ''` and inherit its patient list.
  //
  // IT WAS NOT REACHABLE, AND THAT IS WHY THIS TEST EXISTS RATHER THAN A
  // BUG REPORT. api/dnt-auth.js refuses an empty employee_id on bootstrap and
  // the signin path takes it from the stored row -- but that bound lives in a
  // different file for a different reason, and nothing in the scoping code
  // depended on it deliberately. An incidental bound is not a control. The
  // guard is now in dntLinkedProvider() and this arm holds it.
  //
  // The token is signed DIRECTLY rather than through tokenFor(), because that
  // helper falls back to 'emp-' + role on a falsy id and so cannot express the
  // case under test.
  await test('an EMPTY session employee_id matches no provider, not the first unlinked one', async () => {
    const emptyIdToken = signSessionToken({
      app: 'sairndental', employee_id: '', role: 'provider', license_hash: LIC_HASH,
    });
    const rowsWithEmptyLink = [
      { provider_id: 'PV-1', data: { id: 'PV-1', name: 'Dr Linked', linked_employee_id: 'emp-provider' } },
      // exactly what an unlinked row looks like on disk
      { provider_id: 'PV-2', data: { id: 'PV-2', name: 'Dr Unlinked', linked_employee_id: '' } },
    ];
    const handler = loadHandler(routedFetch([
      ['dnt_providers?', rowsWithEmptyLink],
      ['dnt_appointments?', APPOINTMENT_ROWS_PV1],
      ['dnt_patients?', PATIENT_ROWS],
    ]));
    const res = mockRes();
    await handler(mockReq({ action: 'read', resource: 'dnt_patients' }, emptyIdToken), res);
    assert.strictEqual(res.statusCode, 403,
      'an empty employee_id inherited a scope instead of being refused -- got '
      + res.statusCode + ' ' + JSON.stringify(res.body));
    assert.strictEqual(res.body.error.code, 'PROVIDER_NOT_LINKED');
  });

  // CONTROL: the same rows, a REAL employee_id, still resolve normally. Without
  // this the arm above would pass on a guard that refused everybody.
  await test('CONTROL: a real employee_id still links against the same rows', async () => {
    const rowsWithEmptyLink = [
      { provider_id: 'PV-1', data: { id: 'PV-1', name: 'Dr Linked', linked_employee_id: 'emp-provider' } },
      { provider_id: 'PV-2', data: { id: 'PV-2', name: 'Dr Unlinked', linked_employee_id: '' } },
    ];
    const handler = loadHandler(routedFetch([
      ['dnt_providers?', rowsWithEmptyLink],
      ['dnt_appointments?', APPOINTMENT_ROWS_PV1],
      ['dnt_patients?', PATIENT_ROWS],
    ]));
    const res = mockRes();
    await handler(mockReq({ action: 'read', resource: 'dnt_patients' }, tokenFor('provider')), res);
    assert.strictEqual(res.statusCode, 200, JSON.stringify(res.body));
    assert.ok(Array.isArray(res.body.data) && res.body.data.length > 0,
      'the linked provider lost their patient list -- the guard is too wide');
  });

  console.log('\n' + passed + '/' + total + ' passed');
  if (passed !== total) process.exitCode = 1;
}

main();
