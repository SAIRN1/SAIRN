// api/sd-data-dental-provider-scope.test.js
// REQUIREMENT: an UNLINKED provider sees no patients and is told why with a
//   fix path, a linked one sees only patients they have an appointment with,
//   and the provider registry is owner-only to WRITE -- once it carries
//   linked_employee_id it IS the access-control table for all of that
//
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
// ACTIVE-CREDENTIAL PRE-GATE (2026-09-26): api/sd-data.js now re-checks the
// caller's employee row on EVERY request carrying a token. This suite's fetch
// stub answers generic rows with no `active` field, which is a state a real
// deployment cannot be in, so the wrapper answers that one read and passes
// everything else through. See tests/lib/active_credential_stub.js.
const { wrapFetch: wrapActiveCred } = require('../tests/lib/active_credential_stub');

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
  global.fetch = wrapActiveCred(fetchImpl);
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

  // ── THE COULD-NOT-TELL PATH, ADDED 2026-09-17 ─────────────────────────
  // FOUND BY THE NEGATIVE CONTROL, NOT BY REVIEW. Replacing the 502 refusal
  // with `dntScopeIds = null` left this suite GREEN: with no scope ids the
  // filter below is skipped entirely and the scoped provider reads the WHOLE
  // practice's patients. Every arm here drove a lookup that SUCCEEDED, so the
  // one branch where the patient list is UNKNOWN was never entered -- the same
  // shape as an arm that asserts a refusal and never asserts what happens when
  // the refusal cannot be decided.
  //
  // A FAILED LOOKUP IS NOT AN EMPTY LOOKUP. dntPatientIdsForProvider returns
  // null on a bad response and `{}` on a real provider with no appointments;
  // folding the first into the second would read as "no patients" and quietly
  // hand back everyone instead.
  await test('a FAILED patient-scope lookup refuses 502 -- it never falls through to an unfiltered read', async () => {
    const seen = [];
    const handler = loadHandler(routedFetch([
      ['dnt_providers?', PROVIDER_ROWS],
      ['dnt_appointments?', 500],          // the scope lookup cannot answer
      ['dnt_patients?', PATIENT_ROWS]
    ], seen));
    const res = mockRes();
    await handler(mockReq({ action: 'read', resource: 'dnt_patients' }, tokenFor('provider', 'emp-provider')), res);
    assert.strictEqual(res.statusCode, 502, 'a scope that could not be determined must refuse');
    assert.strictEqual(res.body.error.code, 'SCOPE_LOOKUP_FAILED');
    assert.ok(!('data' in res.body), 'a refusal must never carry a data array');
    // AND IT STOPPED BEFORE READING PHI. Refusing after the patient table has
    // already been fetched would still be a refusal and would still have put
    // every patient row in memory on a request that was not entitled to them.
    assert.ok(!seen.some((u) => u.indexOf('dnt_patients?') !== -1),
      'the patient table was read despite the scope being unknown: ' + seen.join(' | '));
  });

  await test('...and a provider with NO appointments is an EMPTY list, not a failure', async () => {
    // The other half of the pair. `{}` and null are different answers and the
    // code distinguishes them; without this arm, "refuse when the lookup
    // fails" could be satisfied by refusing whenever it returns nothing --
    // which would lock out every newly-linked provider on their first day.
    const handler = loadHandler(routedFetch([
      ['dnt_providers?', PROVIDER_ROWS],
      ['dnt_appointments?', []],
      ['dnt_patients?', PATIENT_ROWS]
    ]));
    const res = mockRes();
    await handler(mockReq({ action: 'read', resource: 'dnt_patients' }, tokenFor('provider', 'emp-provider')), res);
    assert.strictEqual(res.statusCode, 200);
    assert.deepStrictEqual(res.body.data, [], 'no appointments means no patients, not every patient');
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

  // ══ PROVIDER OWNERSHIP ON **WRITE**, 2026-10-11 ════════════════════════════
  // Everything above this line drives the READ. The write beside it had no role
  // check and no ownership check at all: a `provider` session could rewrite any
  // appointment in the practice, including one belonging to a provider whose
  // appointments it is forbidden to even read. That asymmetry is what these arms
  // pin, and the reason they live in THIS file is that the rule they enforce is
  // the same rule the read above already had.
  //
  // Reproducing artifact: dnt_appointments_write_gate_repro.py, exit 1
  // REPRODUCES at 263f736f -> exit 0 CLEAN. That tool answers a SOURCE question
  // ("is there a role check in the block"); these arms answer the behavioural
  // one, which is the half it cannot.
  //
  // ONE ROLE IS AFFECTED: api/_lib/auth.js:155 gives sairndental
  // ['owner', 'frontdesk', 'provider'] and the broad-read set is
  // {owner, frontdesk}, so the complement is `provider` alone. Both exempt roles
  // are driven below anyway -- a gate that locked out the front desk would be a
  // worse bug than the one being fixed.
  section_write();

  // Routes the THREE distinct dnt_appointments URLs this path touches, in the
  // order routedFetch matches them (first substring wins, so the two specific
  // ones must precede the generic read filter):
  //   on_conflict=          the upsert itself
  //   appointment_id=eq.    the NEW existing-row ownership lookup
  //   dnt_appointments?     the read-branch filter
  // `seen` is what proves a refusal happened BEFORE the upsert rather than after
  // it -- a 403 with the row already written would satisfy a status-code
  // assertion and still be the bug.
  function writeRoutes(existingRow, opts) {
    const o = opts || {};
    return [
      ['on_conflict=', o.upsert || [{ data: { id: 'AP-9' } }]],
      ['appointment_id=eq.', o.lookupStatus || (existingRow ? [existingRow] : [])],
      ['dnt_providers?', o.providerRows || PROVIDER_ROWS],
      ['dnt_appointments?', APPOINTMENT_ROWS_PV1],
    ];
  }
  function postedUpsert(seen) {
    return seen.filter((u) => u.indexOf('on_conflict=') !== -1).length;
  }
  const APPT = { id: 'AP-9', patient_id: 'PT-1', start_time: '2026-10-12T09:00:00Z' };

  await test('provider writing an appointment for THEIR OWN provider -> allowed '
    + '(a gate is a split, not a lockout)', async () => {
    const seen = [];
    const handler = loadHandler(routedFetch(writeRoutes(null), seen));
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'dnt_appointments',
      payload: Object.assign({}, APPT, { provider_id: 'PV-1' }) }, tokenFor('provider')), res);
    assert.strictEqual(res.statusCode, 200, 'the linked provider lost their own '
      + 'write: ' + res.statusCode + ' ' + JSON.stringify(res.body));
    assert.strictEqual(postedUpsert(seen), 1, 'the upsert did not run');
  });

  await test('provider writing an appointment labelled with ANOTHER provider -> '
    + '403 NOT_YOUR_APPOINTMENT, and nothing is written', async () => {
    const seen = [];
    const handler = loadHandler(routedFetch(writeRoutes(null), seen));
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'dnt_appointments',
      payload: Object.assign({}, APPT, { provider_id: 'PV-2' }) }, tokenFor('provider')), res);
    assert.strictEqual(res.statusCode, 403, JSON.stringify(res.body));
    assert.strictEqual(res.body.error.code, 'NOT_YOUR_APPOINTMENT');
    assert.strictEqual(postedUpsert(seen), 0,
      'REFUSED AFTER WRITING. The status code is right and the row is already in '
      + 'the table, which is the whole bug wearing a 403.');
  });

  await test('THE TAKEOVER: provider writing their OWN provider_id onto an '
    + 'appointment the SERVER says belongs to PV-2 -> 403, and nothing is written',
  async () => {
    // THE ARM THAT MATTERS, and the reason a payload-only check is not a fix.
    // This is an upsert on (license_hash, appointment_id). A check that only
    // compared payload.provider_id to the caller's own id would PASS this
    // request -- the payload is honestly labelled PV-1 -- and PV-1 would walk
    // off with PV-2's appointment. The decision has to be made against the row
    // already on the server, which is the same pattern scp_progress_photos'
    // self-QC refusal uses.
    const seen = [];
    const handler = loadHandler(routedFetch(writeRoutes({ provider_id: 'PV-2' }), seen));
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'dnt_appointments',
      payload: Object.assign({}, APPT, { provider_id: 'PV-1' }) }, tokenFor('provider')), res);
    assert.strictEqual(res.statusCode, 403, JSON.stringify(res.body));
    assert.strictEqual(res.body.error.code, 'NOT_YOUR_APPOINTMENT');
    assert.strictEqual(postedUpsert(seen), 0, 'the takeover was written anyway');
  });

  await test('CONTROL FOR THE TAKEOVER ARM: the same request, with the existing '
    + 'row already PV-1, is allowed', async () => {
    // Without this, the arm above would pass on a guard that refused every write
    // that had an existing row at all.
    const seen = [];
    const handler = loadHandler(routedFetch(writeRoutes({ provider_id: 'PV-1' }), seen));
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'dnt_appointments',
      payload: Object.assign({}, APPT, { provider_id: 'PV-1' }) }, tokenFor('provider')), res);
    assert.strictEqual(res.statusCode, 200, JSON.stringify(res.body));
    assert.strictEqual(postedUpsert(seen), 1);
  });

  await test('provider writing an appointment with NO provider_id -> 403, not '
    + 'waved through as unassigned', async () => {
    // The column is nullable and `payload.provider_id || null` is written, so an
    // unassigned appointment is a real state. It is not one a provider-scoped
    // caller may create: the row it produces is one they could not read back.
    const seen = [];
    const handler = loadHandler(routedFetch(writeRoutes(null), seen));
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'dnt_appointments',
      payload: Object.assign({}, APPT) }, tokenFor('provider')), res);
    assert.strictEqual(res.statusCode, 403, JSON.stringify(res.body));
    assert.strictEqual(res.body.error.code, 'NOT_YOUR_APPOINTMENT');
    assert.strictEqual(postedUpsert(seen), 0);
  });

  await test('UNLINKED provider writing -> 403 PROVIDER_NOT_LINKED, and the '
    + 'message says where the fix happens', async () => {
    const seen = [];
    const handler = loadHandler(routedFetch(writeRoutes(null), seen));
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'dnt_appointments',
      payload: Object.assign({}, APPT, { provider_id: 'PV-2' }) },
      tokenFor('provider', 'emp-nobody')), res);
    assert.strictEqual(res.statusCode, 403, JSON.stringify(res.body));
    assert.strictEqual(res.body.error.code, 'PROVIDER_NOT_LINKED');
    assert.ok(/Providers panel/i.test(res.body.error.message),
      'the message must point at the fix, not just refuse: ' + res.body.error.message);
    assert.strictEqual(postedUpsert(seen), 0);
  });

  await test('an UNPROVISIONED provider registry on WRITE -> 503 NOT_PROVISIONED, '
    + 'NEVER an empty success', async () => {
    // The READ above can honestly answer provisioned:false with an empty list.
    // A WRITE cannot: an empty-success write is the silent failure this platform
    // refuses -- the caller is told it saved and nothing is in the table.
    const seen = [];
    const handler = loadHandler(routedFetch([
      ['on_conflict=', [{ data: { id: 'AP-9' } }]],
      ['dnt_providers?', 404],
      ['dnt_appointments?', APPOINTMENT_ROWS_PV1],
    ], seen));
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'dnt_appointments',
      payload: Object.assign({}, APPT, { provider_id: 'PV-1' }) }, tokenFor('provider')), res);
    assert.strictEqual(res.statusCode, 503, JSON.stringify(res.body));
    assert.strictEqual(res.body.error.code, 'NOT_PROVISIONED');
    assert.ok(/sairndental_availability_booking_schema\.sql/.test(res.body.error.message),
      'a 503 with no SQL to run is a dead end: ' + res.body.error.message);
    assert.strictEqual(postedUpsert(seen), 0);
  });

  await test('a FAILED existing-row lookup refuses 502 SCOPE_LOOKUP_FAILED -- it '
    + 'never falls through to the unrestricted write', async () => {
    // PR 1.11 inside one branch: "could not tell who this belongs to" is a third
    // state, and folding it into the allow path is how the whole gate becomes
    // optional under load. A 500 from the lookup must not become a 200 write.
    const seen = [];
    const handler = loadHandler(routedFetch([
      ['on_conflict=', [{ data: { id: 'AP-9' } }]],
      ['appointment_id=eq.', 500],
      ['dnt_providers?', PROVIDER_ROWS],
      ['dnt_appointments?', APPOINTMENT_ROWS_PV1],
    ], seen));
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'dnt_appointments',
      payload: Object.assign({}, APPT, { provider_id: 'PV-1' }) }, tokenFor('provider')), res);
    assert.strictEqual(res.statusCode, 502, JSON.stringify(res.body));
    assert.strictEqual(res.body.error.code, 'SCOPE_LOOKUP_FAILED');
    assert.strictEqual(postedUpsert(seen), 0,
      'the write ran anyway after the ownership lookup failed');
  });

  await test('OWNER writing any appointment -> allowed, with NO provider lookup '
    + 'at all', async () => {
    const seen = [];
    const handler = loadHandler(routedFetch(writeRoutes({ provider_id: 'PV-2' }), seen));
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'dnt_appointments',
      payload: Object.assign({}, APPT, { provider_id: 'PV-2' }) }, tokenFor('owner')), res);
    assert.strictEqual(res.statusCode, 200, JSON.stringify(res.body));
    assert.deepStrictEqual(seen.filter((u) => u.indexOf('dnt_providers?') !== -1), [],
      'the owner path did a provider lookup it does not need -- that is a '
      + 'round-trip per write and a second place the rule can drift');
    assert.deepStrictEqual(seen.filter((u) => u.indexOf('appointment_id=eq.') !== -1), [],
      'the owner path did the ownership lookup too');
  });

  await test('FRONTDESK writing any appointment -> allowed (they book and check '
    + 'in anyone, which is why the read exempts them)', async () => {
    const seen = [];
    const handler = loadHandler(routedFetch(writeRoutes({ provider_id: 'PV-2' }), seen));
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'dnt_appointments',
      payload: Object.assign({}, APPT, { provider_id: 'PV-2' }) }, tokenFor('frontdesk')), res);
    assert.strictEqual(res.statusCode, 200, JSON.stringify(res.body));
    assert.strictEqual(postedUpsert(seen), 1);
  });

  await test('NO SESSION at all still refuses before any of this -- the dntGate '
    + 'was not displaced by the ownership check', async () => {
    const seen = [];
    const handler = loadHandler(routedFetch(writeRoutes(null), seen));
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'dnt_appointments',
      payload: Object.assign({}, APPT, { provider_id: 'PV-1' }) }), res);
    // 401 NO_SESSION, not 403. The distinction is dntGate's and is worth
    // pinning: 401 is "you are not signed in", 403 is "you are signed in and
    // this is not yours". Collapsing them would make the ownership refusals
    // above indistinguishable from an expired token at the call site.
    assert.strictEqual(res.statusCode, 401, JSON.stringify(res.body));
    assert.strictEqual(res.body.error.code, 'NO_SESSION');
    assert.strictEqual(postedUpsert(seen), 0);
  });

  console.log('\n' + passed + '/' + total + ' passed');
  if (passed !== total) process.exitCode = 1;
}

function section_write() {
  console.log('\napi/sd-data.js -- SAIRNdental dnt_appointments WRITE: provider '
    + 'ownership, which the read had and the write did not');
}

main();
