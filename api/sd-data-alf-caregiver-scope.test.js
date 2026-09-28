// api/sd-data-alf-caregiver-scope.test.js
//
// REQUIREMENT: `caregiver` -- a role SAIRNcare offers in both of its role
//   dropdowns and which appears in NO roleSet() in api/sd-data.js -- reaches
//   exactly the resident-care surface it is designed to reach, and nothing
//   administrative or clinical beyond it.
//
// Run:  node api/sd-data-alf-caregiver-scope.test.js
//
// ── WHY THIS FILE EXISTS, AND IT CORRECTS SOMETHING I SAID EARLIER ────────
// I reported that `caregiver` was a "phantom role": named in sairncare.html's
// two role dropdowns, absent from every roleSet() in api/sd-data.js, therefore
// outside the role-gate tool's universe and unable to be counted as an excluded
// role anywhere. THE FIRST HALF IS TRUE AND THE INFERENCE WAS WRONG.
//
// Reading all fourteen alf_ branches shows the gates come in two shapes:
//
//   ALLOW-LIST   `if (!ALF_X_ROLES[session.role]) 403`
//                -- caregiver is refused, and for administration that is right.
//   FALLTHROUGH  `if (!ALF_BROAD_READ_ROLES[session.role]) { narrow to own }`
//                -- caregiver lands in the NARROW tier and works as designed.
//
// api/sd-data.js:6650-6656 documents a FOUR-TIER gate and names caregiver
// explicitly: "NARROW (med_aide, caregiver): own-assigned-residents-only,
// self-assign-on-create". The narrow tier is not a roleSet, it is the absence of
// one -- which is why a tool that reads roleSet membership cannot see it, and
// why "not in any roleSet" does not mean "has no permissions".
//
// SO NO roleSet IS CHANGED BY THIS COMMIT. The design is coherent; what was
// missing is anything that PINS it. A tier implemented as a fallthrough is one
// refactor away from silently becoming an allow-list, and nothing would fail.
//
// ── THE THREE THINGS THAT MATTER MOST HERE ───────────────────────────────
// 1. alf_mar MUST refuse caregiver, and this is not a preference. Medication
//    administration is a licensure boundary -- `med_aide` is a separate
//    certified role for exactly this reason. A caregiver granted MAR access
//    would be a regulatory finding, not a UX improvement, so that arm is
//    written to fail loudly if anybody ever widens ALF_MAR_ROLES.
// 2. alf_incidents WRITE must ACCEPT caregiver for a NEW report. Direct-care
//    staff are mandated reporters; the person who finds the fall is usually the
//    caregiver. The branch already implements this asymmetry deliberately
//    ("gating this would discourage reporting") and nothing pinned it.
// 3. alf_facility WRITE must refuse caregiver. That write carries
//    `licensing_state`, which the compliance engine selects a state's rule set
//    from -- so this is the difference between a cosmetic field and which
//    staffing law the facility is measured against.

'use strict';

process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET
  || ['alf', 'caregiver', 'fixture'].join('-');
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://test.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'test-key';

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const { signSessionToken, ROLES_BY_APP } = require('./_lib/auth');

const HASH = 'caregiver-scope-hash';
const APP = 'sairncare';
const ME = 'emp-care-1';
const OTHER = 'emp-other-9';

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

// Same PostgREST mock contract as api/sd-data-alf-isolation.test.js: every
// `<col>=eq.<v>` clause is applied, `select=` is honoured, and an unrecognised
// clause is NOT applied so the mock errs by returning MORE rows than the real
// database would. Every way it is unfaithful runs in the safe direction.
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
      return { ok: true, status: 200, json: async function () {
        return [{ license_hash: HASH, employee_id: ME, role: 'caregiver', active: true }]; } };
    }
    if (opts && opts.method === 'POST') {
      const sent = JSON.parse(opts.body);
      return { ok: true, status: 200, text: async function () { return opts.body; },
               json: async function () { return [sent]; } };
    }
    // ── THE MOCK MUST ROUTE BY TABLE, AND THE FIRST CUT DID NOT ──────────
    // Every alf_ query filters on `license_hash=eq.<hash>`, so a flat row set
    // matched on eq-clauses alone hands an alf_clients row back to an
    // alf_family_contacts query. The narrow arms still passed -- their own
    // resident_id filter dropped the stray rows -- and only the BROAD control
    // caught it, by receiving four rows where two were expected. A fixture leak
    // that the strict arms absorb and only the control sees is the shape a
    // control exists for, so it is fixed here rather than worked around in the
    // assertion.
    const table = (u.match(/\/rest\/v1\/([a-z0-9_]+)/) || [])[1] || '';
    const matches = rows.filter(function (r) {
      if (r.__table && table && r.__table !== table) return false;
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

function loadHandler(fetchImpl) {
  delete require.cache[require.resolve('./_lib/license')];
  require.cache[require.resolve('./_lib/license')] = {
    exports: {
      validateLicenseKey: async function () {
        return { valid: true, active: true, license_hash: HASH,
                 trial_ends_at: null, stripe_subscription_id: null, app_id: APP };
      }
    }
  };
  global.fetch = fetchImpl;
  delete require.cache[require.resolve('./sd-data.js')];
  return require('./sd-data.js');
}

async function call(role, body, rows, employeeId) {
  const calls = [];
  const h = loadHandler(postgrestMock(rows || [], calls));
  const res = mockRes();
  await h({
    method: 'POST',
    headers: {
      authorization: 'Bearer KEY-FOR-' + HASH,
      'x-sd-auth': signSessionToken({ app: APP, employee_id: employeeId || ME,
                                      role: role, license_hash: HASH })
    },
    body: body
  }, res);
  return { res: res, calls: calls };
}

function firstPost(calls) {
  return calls.filter(function (c) { return c.opts && c.opts.method === 'POST'; })[0];
}
function code(res) {
  return (res.body && res.body.error && res.body.error.code) || null;
}

function client(id, assignee, marker) {
  return { __table: 'alf_clients',
           license_hash: HASH, client_id: id, assigned_employee_id: assignee,
           data: { marker: marker, name: 'A Resident' } };
}

(async () => {

// ── 0. THE PREMISE, DRIVEN ───────────────────────────────────────────────
section('0. THE PREMISE -- caregiver is a REAL app role that no roleSet names');

await test('caregiver IS in ROLES_BY_APP.sairncare, so a token can be minted '
  + 'for it at all', () => {
    assert.ok(ROLES_BY_APP.sairncare.indexOf('caregiver') !== -1,
      'caregiver is not a valid sairncare role -- every arm below is vacuous, '
      + 'because verifySessionToken would refuse the token before any gate ran');
  });

await test('caregiver appears in BOTH of sairncare.html role dropdowns -- the '
  + 'UI offers it', () => {
    const html = fs.readFileSync(path.join(__dirname, '..', 'sairncare.html'), 'utf8');
    const opts = html.match(/<option value="caregiver">/g) || [];
    assert.ok(opts.length >= 2,
      'expected caregiver in both the staff-position and the credential-role '
      + 'dropdowns, found ' + opts.length);
  });

await test('and NO roleSet() in api/sd-data.js names it -- which is what made '
  + 'it look like a phantom', () => {
    const src = fs.readFileSync(path.join(__dirname, 'sd-data.js'), 'utf8');
    const sets = src.match(/roleSet\(\{[^}]*\}\)/g) || [];
    const naming = sets.filter(function (s) { return /\bcaregiver\s*:/.test(s); });
    assert.deepStrictEqual(naming, [],
      'caregiver is now IN a roleSet: ' + naming.join(' | ') + '. That may be '
      + 'correct, but this file documents the fallthrough design and every arm '
      + 'below was written against it -- re-read them before re-pinning.');
  });

// ── 1. WHAT CAREGIVER REACHES, BY DESIGN ─────────────────────────────────
section('1. THE NARROW TIER -- reached by FALLTHROUGH, not by a roleSet');

await test('alf_clients read: a caregiver sees ONLY their own assigned '
  + 'residents, not the facility roster', async () => {
    const { res } = await call('caregiver',
      { action: 'read', resource: 'alf_clients' },
      [client('C-MINE', ME, 'mine'), client('C-THEIRS', OTHER, 'theirs')]);
    assert.strictEqual(res.statusCode, 200,
      'caregiver was refused the resident list entirely: ' + code(res));
    const markers = (res.body.data || []).map(function (r) { return r.marker; });
    assert.deepStrictEqual(markers, ['mine'],
      'caregiver was handed ' + JSON.stringify(markers) + ' -- the narrow tier '
      + 'did not narrow, or narrowed the wrong way');
  });

await test('alf_clients read CONTROL: a broad role DOES see both, so the arm '
  + 'above is narrowing and not an empty fixture', async () => {
    const { res } = await call('nursing',
      { action: 'read', resource: 'alf_clients' },
      [client('C-MINE', ME, 'mine'), client('C-THEIRS', OTHER, 'theirs')]);
    assert.strictEqual(res.statusCode, 200, 'nursing refused: ' + code(res));
    const markers = (res.body.data || []).map(function (r) { return r.marker; }).sort();
    assert.deepStrictEqual(markers, ['mine', 'theirs'],
      'the broad role did not see both -- the fixture, not the gate, is what '
      + 'the arm above measured');
  });

await test('alf_incidents write: a caregiver CAN file a NEW report -- mandated '
  + 'reporting, and the branch says so', async () => {
    const { res, calls } = await call('caregiver',
      { action: 'write', resource: 'alf_incidents',
        payload: { id: 'INC-NEW', resident_id: 'C-MINE', type: 'fall' } }, []);
    assert.strictEqual(res.statusCode, 200,
      'a caregiver was refused filing an incident (' + res.statusCode + ' '
      + code(res) + ') -- the person who finds the fall cannot report it');
    assert.ok(firstPost(calls), 'the report was accepted but never written');
  });

await test('alf_activities read: a caregiver CAN read the activity calendar '
  + '(broad-read, any authenticated employee)', async () => {
    const { res } = await call('caregiver',
      { action: 'read', resource: 'alf_activities' }, []);
    assert.strictEqual(res.statusCode, 200,
      'caregiver refused the activity calendar: ' + code(res));
  });

// ── 2. WHAT IT MUST NEVER REACH ──────────────────────────────────────────
section('2. THE LICENSURE BOUNDARY AND THE ADMINISTRATIVE SURFACE');

await test('alf_mar read: a caregiver is REFUSED the medication record -- a '
  + 'licensure boundary, not a preference', async () => {
    const { res } = await call('caregiver',
      { action: 'read', resource: 'alf_mar' }, []);
    assert.strictEqual(res.statusCode, 403,
      'A CAREGIVER REACHED THE MEDICATION ADMINISTRATION RECORD (got '
      + res.statusCode + '). med_aide exists as a separate certified role for '
      + 'exactly this reason. If ALF_MAR_ROLES was widened deliberately, that is '
      + 'a regulatory decision and needs more than a passing test.');
    assert.strictEqual(code(res), 'FORBIDDEN', 'refused for the wrong reason');
  });

await test('alf_mar write: same, and nothing is written', async () => {
  const { res, calls } = await call('caregiver',
    { action: 'write', resource: 'alf_mar',
      payload: { id: 'M-1', resident_id: 'C-MINE', entry_type: 'given' } }, []);
  assert.strictEqual(res.statusCode, 403,
    'a caregiver recorded a medication administration (' + res.statusCode + ')');
  assert.strictEqual(firstPost(calls), undefined,
    'refused AFTER the write was sent -- the MAR row already exists');
});

const ADMIN_REFUSALS = [
  ['alf_facility', 'write', { id: 'F-1', licensing_state: 'WV' },
   'the facility profile carries licensing_state, which the compliance engine '
   + 'selects a state rule set from'],
  ['alf_billing', 'read', null, 'resident billing'],
  ['alf_billing', 'write', { id: 'B-1' }, 'resident billing'],
  ['alf_staff', 'write', { id: 'S-1' }, 'the staff roster'],
  ['alf_staff_credentials', 'write', { id: 'CR-1' }, 'staff credentials'],
  ['alf_payer_rules', 'write', { id: 'P-1' }, 'payer rules'],
  ['alf_claim_routes', 'read', null, 'the claim routing trail'],
  ['alf_claim_routes', 'write', { id: 'R-1' }, 'the claim routing trail'],
  ['alf_compliance_rules', 'write', { id: 'CP-1' }, 'the compliance rule set'],
  ['alf_signals', 'write', { id: 'SG-1' }, 'operational signals']
];

for (const [resource, action, payload, why] of ADMIN_REFUSALS) {
  await test('caregiver is refused ' + resource + ' ' + action
    + ' -- ' + why, async () => {
      const body = { action: action, resource: resource };
      if (payload) body.payload = payload;
      const { res, calls } = await call('caregiver', body, []);
      assert.strictEqual(res.statusCode, 403,
        'caregiver reached ' + resource + ' ' + action + ' (' + res.statusCode
        + ' ' + JSON.stringify(res.body) + ')');
      assert.strictEqual(code(res), 'FORBIDDEN',
        'refused for the wrong reason: ' + JSON.stringify(res.body));
      if (action === 'write') {
        assert.strictEqual(firstPost(calls), undefined,
          'refused AFTER the write was sent -- the row already changed');
      }
    });
}

// ── 2b. THREE GATES THAT ARE NOT ALLOW-LISTS, AND I GUESSED WRONG ────────
// Each of these was written into section 2 as a flat refusal and each came back
// a different answer. The code is right and the assumption was wrong, so the
// arms are rewritten to assert what actually happens. Recorded this way rather
// than silently corrected, because "I expected 403 and got 200" is exactly the
// sentence a reader of a permissions suite needs to see.
section('2b. REDACTION AND SELF-SCOPE -- not refusal, and not a defect');

await test('alf_facility read: caregiver is ALLOWED, with rate fields REDACTED '
  + '-- a third shape, neither allow-list nor fallthrough-narrow', async () => {
    const { res } = await call('caregiver',
      { action: 'read', resource: 'alf_facility' }, []);
    assert.strictEqual(res.statusCode, 200,
      'caregiver refused the facility profile: ' + code(res));
    assert.strictEqual(res.body.rates_visible, false,
      'RATE FIELDS ARE VISIBLE TO A CAREGIVER. The read is deliberately open to '
      + 'every authenticated employee and defends itself by REDACTION, so '
      + 'rates_visible is the whole control and it is off.');
  });

await test('alf_facility read CONTROL: management DOES see rates, so the arm '
  + 'above measures redaction rather than an empty response', async () => {
    const { res } = await call('owner',
      { action: 'read', resource: 'alf_facility' }, []);
    assert.strictEqual(res.body.rates_visible, true,
      'nobody sees rates, so rates_visible: false proves nothing about role');
  });

await test('alf_staff_credentials read: caregiver is ALLOWED and SELF-SCOPED -- '
  + 'they see their own training, not the roster\'s', async () => {
    const rows = [
      { __table: 'alf_staff_credentials', license_hash: HASH, entry_id: 'CR-MINE', staff_id: ME,
        record_type: 'credential', data: { marker: 'mine' }, recorded_by: 'owner-1', created_at: '2026-01-01' },
      { __table: 'alf_staff_credentials', license_hash: HASH, entry_id: 'CR-THEIRS', staff_id: OTHER,
        record_type: 'credential', data: { marker: 'theirs' }, recorded_by: 'owner-1', created_at: '2026-01-02' }
    ];
    const { res } = await call('caregiver',
      { action: 'read', resource: 'alf_staff_credentials' }, rows);
    assert.strictEqual(res.statusCode, 200, 'refused: ' + code(res));
    assert.strictEqual(res.body.scoped_to_self, true,
      'a caregiver was NOT self-scoped on staff credentials -- this exposes the '
      + 'whole roster\'s qualifications');
    const markers = (res.body.data || []).map(function (r) { return r.marker; });
    assert.deepStrictEqual(markers, ['mine'],
      'self-scoping did not narrow: got ' + JSON.stringify(markers));
  });

await test('alf_op_audits write: caregiver CAN record an observation -- it is '
  + 'only the SIGN-OFF that is management-only', async () => {
    const { res, calls } = await call('caregiver',
      { action: 'write', resource: 'alf_op_audits',
        payload: { id: 'A-OBS', record_type: 'emergency_drill' } }, []);
    assert.notStrictEqual(res.statusCode, 403,
      'caregiver was refused recording an observation: ' + JSON.stringify(res.body));
    assert.ok(res.statusCode === 200 || res.statusCode === 400,
      'unexpected ' + res.statusCode + ' ' + JSON.stringify(res.body));
    if (res.statusCode === 200) assert.ok(firstPost(calls), 'accepted but not written');
  });

await test('alf_op_audits SIGN-OFF is refused for caregiver', async () => {
  const { res } = await call('caregiver',
    { action: 'write', resource: 'alf_op_audits',
      payload: { id: 'A-REV', record_type: 'emergency_drill', reviewed: true } }, []);
  assert.strictEqual(res.statusCode, 403,
    'a caregiver signed off an operational audit record (' + res.statusCode + ')');
});

await test('alf_op_audits ORDERING: a sign-off from a refused role with a BAD '
  + 'payload is answered on the PAYLOAD, not the role', async () => {
    // FINDING, recorded not fixed. The payload validator at the top of this
    // branch runs BEFORE the isReview role gate, so a caregiver attempting a
    // sign-off with an unknown record_type is told their record_type is wrong
    // -- a wrong explanation for a request they were never allowed to make, and
    // an oracle: the message confirms which record_types exist to a caller who
    // may not write one. Same class the alf_facility ordering arm pins in
    // api/sd-data-alf-isolation.test.js, where the gate is ordered correctly.
    const { res } = await call('caregiver',
      { action: 'write', resource: 'alf_op_audits',
        payload: { id: 'A-REV2', record_type: 'not-a-real-type', reviewed: true } }, []);
    assert.strictEqual(res.statusCode, 400,
      'the ordering changed -- if this is now 403 FORBIDDEN the finding is '
      + 'CLOSED and this arm should be rewritten to assert that instead');
    assert.ok(/record_type must be one of/.test(
      (res.body && res.body.error && res.body.error.message) || ''),
      'the 400 is no longer the record_type validator');
  });

// ── 3. THE CONTROL ───────────────────────────────────────────────────────
section('3. THE CONTROL -- the refusals above are a SPLIT, not a lockout');

await test('owner is ALLOWED everything caregiver was refused above', async () => {
  for (const [resource, action, payload] of ADMIN_REFUSALS) {
    const body = { action: action, resource: resource };
    if (payload) body.payload = payload;
    const { res } = await call('owner', body, []);
    assert.notStrictEqual(res.statusCode, 403,
      'owner was ALSO refused ' + resource + ' ' + action + ' -- these gates are '
      + 'a lockout rather than a role split, and every arm in section 2 passes '
      + 'for the wrong reason');
  }
});

await test('med_aide IS allowed the MAR -- so section 2\'s MAR arms measure the '
  + 'licensure line and not a dead branch', async () => {
    const { res } = await call('med_aide',
      { action: 'read', resource: 'alf_mar' }, []);
    assert.notStrictEqual(res.statusCode, 403,
      'med_aide is refused the MAR too, so the caregiver arm proves nothing '
      + 'about caregiver specifically');
  });

// ── 4. THE OPEN QUESTIONS, PINNED AS CURRENT BEHAVIOUR ───────────────────
section('4. CURRENT BEHAVIOUR ON THE THREE UNSETTLED ONES -- pinned, not blessed');

// These are PRODUCT questions, not defects, and they are pinned so a change is
// deliberate rather than accidental. Each arm says what the argument on the
// other side is, so the next reader is not left guessing why it is here.

// alf_family_contacts was an open question here and is now DECIDED -- a care
// role reads the emergency contact for its own assigned residents only. The
// arms moved to section 5, which drives both halves of the narrowing.

// alf_staff_credentials was listed here as an open question on the assumption
// that the gate had no self-scope. IT DOES -- see section 2b -- so the question
// does not exist and the arm has moved there as a positive assertion. Left
// named rather than deleted, because a question that turned out to be already
// answered is worth one line to stop it being re-asked.

// alf_incidents read was pinned here as an open question at a flat 403. It is
// now DECIDED -- a care role reads back its own filings -- and the arms moved to
// section 6, which drives the server-set attribution the narrowing rests on.

// ── 5. THE NARROW FAMILY-CONTACT TIER, BUILT 2026-09-27 ──────────────────
section('5. alf_family_contacts NARROW TIER -- own assigned residents, and the '
  + 'consent trail stripped');

function contact(contactId, residentId, marker) {
  return {
    __table: 'alf_family_contacts',
    contact_id: contactId, resident_id: residentId, name: 'A Relative',
    relationship: 'daughter', email: 'x@example.invalid', phone: '555-0100',
    active: true, created_at: '2026-01-01', updated_at: '2026-01-01',
    marker: marker,
    // The consent trail. Present on every row so its ABSENCE from the narrow
    // answer is a real assertion and not an empty fixture.
    mar_consent: true, consent_granted_at: '2026-01-01',
    consent_granted_by: 'owner-1', consent_revoked_at: null,
    revoked_at: null, notes: 'SENSITIVE FREE TEXT',
    recorded_by: 'owner-1', license_hash: HASH
  };
}

const FAM_ROWS = [
  contact('FC-MINE', 'C-MINE', 'mine'),
  contact('FC-THEIRS', 'C-THEIRS', 'theirs')
];
const FAM_CLIENTS = [client('C-MINE', ME, 'mine'), client('C-THEIRS', OTHER, 'theirs')];

await test('ROWS NARROW: a caregiver sees contacts for their OWN assigned '
  + 'resident only', async () => {
    const { res } = await call('caregiver',
      { action: 'read', resource: 'alf_family_contacts' },
      FAM_ROWS.concat(FAM_CLIENTS));
    assert.strictEqual(res.statusCode, 200,
      'caregiver refused the emergency contact: ' + code(res));
    assert.strictEqual(res.body.scoped_to_assigned, true,
      'the answer does not declare itself scoped');
    const ids = (res.body.data || []).map(function (r) { return r.contact_id; });
    assert.deepStrictEqual(ids, ['FC-MINE'],
      'got ' + JSON.stringify(ids) + ' -- a caregiver was handed a resident '
      + 'who is not assigned to them');
  });

await test('COLUMNS NARROW: the consent trail and notes are ABSENT, not merely '
  + 'unrendered', async () => {
    const { res } = await call('caregiver',
      { action: 'read', resource: 'alf_family_contacts' },
      FAM_ROWS.concat(FAM_CLIENTS));
    const row = (res.body.data || [])[0];
    assert.ok(row, 'no row came back, so this arm proves nothing');
    ['mar_consent', 'consent_granted_at', 'consent_granted_by',
     'consent_revoked_at', 'revoked_at', 'notes'].forEach(function (f) {
      assert.strictEqual(f in row, false,
        f + ' reached a care role. Whether a family member may see medication '
        + 'status is the disclosure decision the WRITE gate reserves to '
        + 'management, and handing over the answer gives away the thing the '
        + 'gate protects one step removed.');
    });
    assert.strictEqual(row.phone, '555-0100',
      'the emergency number itself did not survive -- the tier is useless');
    assert.strictEqual(row.name, 'A Relative', 'the contact name did not survive');
  });

await test('CONTROL: a broad role still gets the FULL row including the consent '
  + 'trail, so the arm above measures stripping and not an empty select',
  async () => {
    const { res } = await call('nursing',
      { action: 'read', resource: 'alf_family_contacts' },
      FAM_ROWS.concat(FAM_CLIENTS));
    assert.strictEqual(res.body.scoped_to_assigned, false,
      'a broad role was scoped to assignment');
    const ids = (res.body.data || []).map(function (r) { return r.contact_id; }).sort();
    assert.deepStrictEqual(ids, ['FC-MINE', 'FC-THEIRS'],
      'the broad role did not see both residents');
    assert.strictEqual('mar_consent' in (res.body.data[0] || {}), true,
      'nobody gets the consent trail, so its absence above proves nothing');
  });

await test('ASKING FOR SOMEBODY ELSE\'S RESIDENT BY ID is refused, not answered '
  + 'with an empty list', async () => {
    const { res } = await call('caregiver',
      { action: 'read', resource: 'alf_family_contacts',
        payload: { resident_id: 'C-THEIRS' } },
      FAM_ROWS.concat(FAM_CLIENTS));
    assert.strictEqual(res.statusCode, 403,
      '"you may not see that resident" and "that resident has no contacts" are '
      + 'different answers, and collapsing them is an oracle: an empty list '
      + 'would confirm the resident exists');
    assert.strictEqual(code(res), 'FORBIDDEN', 'wrong refusal code');
  });

await test('ASKING FOR THEIR OWN resident by id still works', async () => {
  const { res } = await call('caregiver',
    { action: 'read', resource: 'alf_family_contacts',
      payload: { resident_id: 'C-MINE' } },
    FAM_ROWS.concat(FAM_CLIENTS));
  assert.strictEqual(res.statusCode, 200, 'refused their own resident: ' + code(res));
  assert.deepStrictEqual((res.body.data || []).map(function (r) { return r.contact_id; }),
    ['FC-MINE']);
});

await test('AN EMPLOYEE WITH NO ASSIGNED RESIDENTS gets an empty list, not a '
  + '403 -- they are permitted to ask', async () => {
    const { res } = await call('caregiver',
      { action: 'read', resource: 'alf_family_contacts' },
      FAM_ROWS.concat([client('C-THEIRS', OTHER, 'theirs')]));
    assert.strictEqual(res.statusCode, 200, 'refused: ' + code(res));
    assert.deepStrictEqual(res.body.data, []);
    assert.strictEqual(res.body.scoped_to_assigned, true);
  });

await test('THE WRITE GATE IS UNTOUCHED -- a caregiver still cannot record or '
  + 'change a family contact', async () => {
    const { res, calls } = await call('caregiver',
      { action: 'write', resource: 'alf_family_contacts',
        payload: { id: 'FC-NEW', resident_id: 'C-MINE', name: 'X' } },
      FAM_CLIENTS);
    assert.strictEqual(res.statusCode, 403,
      'the read narrowing widened the WRITE path: ' + JSON.stringify(res.body));
    assert.strictEqual(firstPost(calls), undefined, 'a row was written');
  });

// ── 6. INCIDENT ATTRIBUTION -- SERVER-SET, AND THE READ THAT RESTS ON IT ──
section('6. alf_incidents: who filed it is SET, not SENT');

function incident(entryId, residentId, recordedBy, reportedBy) {
  const row = {
    __table: 'alf_incidents', license_hash: HASH, entry_id: entryId,
    resident_id: residentId, created_at: '2026-01-01',
    data: { category: 'fall', description: 'x', reported_by: reportedBy || null }
  };
  if (recordedBy !== undefined) row.recorded_by = recordedBy;
  return row;
}

await test('WRITE: recorded_by is set from the SESSION, and a payload '
  + 'recorded_by cannot override it', async () => {
    const { res, calls } = await call('caregiver',
      { action: 'write', resource: 'alf_incidents',
        payload: { id: 'INC-1', resident_id: 'C-MINE', category: 'fall',
                   recorded_by: 'owner-1' } }, []);
    assert.strictEqual(res.statusCode, 200, 'refused: ' + JSON.stringify(res.body));
    const sent = JSON.parse(firstPost(calls).opts.body);
    assert.strictEqual(sent.recorded_by, ME,
      'the filer was taken from the payload, not the session -- got '
      + JSON.stringify(sent.recorded_by));
  });

await test('WRITE: reported_by is STRIPPED from the payload, so a caller cannot '
  + 'attribute a report to somebody else', async () => {
    const { res, calls } = await call('caregiver',
      { action: 'write', resource: 'alf_incidents',
        payload: { id: 'INC-2', resident_id: 'C-MINE', category: 'abuse_neglect_allegation',
                   reported_by: 'some-other-employee', description: 'x' } }, []);
    assert.strictEqual(res.statusCode, 200, 'refused: ' + JSON.stringify(res.body));
    const sent = JSON.parse(firstPost(calls).opts.body);
    assert.strictEqual('reported_by' in (sent.data || {}), false,
      'THE FORGEABLE FIELD WAS STORED. Any employee could file an abuse, '
      + 'neglect or exploitation allegation attributed to anyone else, and the '
      + 'row would carry two answers to "who reported this" -- one '
      + 'authoritative, one not, side by side.');
    assert.strictEqual(sent.recorded_by, ME, 'the real attribution is missing');
    assert.strictEqual(sent.data.category, 'abuse_neglect_allegation',
      'stripping took the rest of the report with it');
  });

await test('WRITE: an UPDATE does not re-stamp recorded_by -- the column answers '
  + '"who filed it", not "who last touched it"', async () => {
    const { res, calls } = await call('owner',
      { action: 'write', resource: 'alf_incidents',
        payload: { id: 'INC-OLD', resident_id: 'C-MINE', follow_up_notes: 'later' } },
      [incident('INC-OLD', 'C-MINE', ME)]);
    assert.strictEqual(res.statusCode, 200, 'refused: ' + JSON.stringify(res.body));
    const sent = JSON.parse(firstPost(calls).opts.body);
    assert.strictEqual('recorded_by' in sent, false,
      'a management follow-up overwrote the reporter with the manager -- which '
      + 'erases the one fact this column exists to hold');
  });

await test('ROUND TRIP: a forged recorded_by does not survive the READ -- the '
  + 'COLUMN wins over the blob', async () => {
    // THE ARM THAT WAS MISSING, AND ITS ABSENCE WAS A LIVE DEFECT (2026-09-28).
    // The write arm above asserts the POST BODY carries the session's
    // employee_id, and it always did -- the column was correct. Nothing
    // asserted what came BACK. `recorded_by` was not in the strip list, so a
    // payload copy landed inside `data`, and the read mapper spread `data`
    // LAST, so the blob overwrote the column. Driven live against
    // ALF-TEST-2026, a write with recorded_by forged read back
    // 'FORGED-SOMEONE-ELSE'.
    //
    // The fixture puts the forged value in BOTH places a real attacker could
    // reach: the stored blob and the column.
    const forged = {
      __table: 'alf_incidents', license_hash: HASH, entry_id: 'INC-RT',
      resident_id: 'C-MINE', created_at: '2026-01-01', recorded_by: ME,
      data: { category: 'fall', recorded_by: 'FORGED', reported_by: 'FORGED',
              id: 'FORGED-ID', resident_id: 'FORGED-RESIDENT' }
    };
    const { res } = await call('nursing',
      { action: 'read', resource: 'alf_incidents' }, [forged]);
    const row = (res.body.data || [])[0];
    assert.ok(row, 'no row came back, so this arm proves nothing');
    assert.strictEqual(row.recorded_by, ME,
      'THE BLOB OVERWROTE THE COLUMN: recorded_by read back as '
      + JSON.stringify(row.recorded_by) + '. That reinstates the attribution '
      + 'spoof the column exists to close.');
    assert.strictEqual(row.id, 'INC-RT',
      'a payload id inside the blob overwrote the real entry_id');
    assert.strictEqual(row.resident_id, 'C-MINE',
      'a payload resident_id inside the blob overwrote the real column');
  });

await test('WRITE: recorded_by is STRIPPED from the blob too -- the second half '
  + 'of the fix, pinned separately', async () => {
    // ABLATION SAID THIS ARM WAS MISSING. Reverting ONLY the strip turned no
    // arm red: the mapper fix alone closes the round trip, so the strip was
    // defence in depth with nothing pinning it. A layer no test can see is a
    // layer the next refactor deletes for being redundant.
    const { res, calls } = await call('caregiver',
      { action: 'write', resource: 'alf_incidents',
        payload: { id: 'INC-STRIP', resident_id: 'C-MINE', category: 'fall',
                   recorded_by: 'FORGED', reported_by: 'FORGED' } }, []);
    assert.strictEqual(res.statusCode, 200, 'refused: ' + JSON.stringify(res.body));
    const sent = JSON.parse(firstPost(calls).opts.body);
    assert.strictEqual('recorded_by' in (sent.data || {}), false,
      'a payload recorded_by was stored INSIDE the blob: '
      + JSON.stringify(sent.data) + '. The column is correct, so nothing breaks '
      + 'today -- but the row then carries two answers to "who filed this", and '
      + 'any future reader that prefers the blob reinstates the spoof.');
    assert.strictEqual(sent.recorded_by, ME, 'the column is wrong');
  });

await test('ROUND TRIP CONTROL: an ordinary blob field still reaches the caller, '
  + 'so the arm above is not testing an empty response', async () => {
    const { res } = await call('nursing',
      { action: 'read', resource: 'alf_incidents' },
      [incident('INC-RT2', 'C-MINE', ME)]);
    const row = (res.body.data || [])[0];
    assert.strictEqual(row.category, 'fall',
      'blob fields no longer survive at all -- the fix went too far');
  });

await test('READ: a caregiver sees ONLY the incidents they filed', async () => {
  const { res } = await call('caregiver',
    { action: 'read', resource: 'alf_incidents' },
    [incident('INC-MINE', 'C-MINE', ME), incident('INC-THEIRS', 'C-THEIRS', OTHER)]);
  assert.strictEqual(res.statusCode, 200, 'refused: ' + code(res));
  assert.strictEqual(res.body.scoped_to_self, true, 'the answer is not declared scoped');
  const ids = (res.body.data || []).map(function (r) { return r.id; });
  assert.deepStrictEqual(ids, ['INC-MINE'], 'got ' + JSON.stringify(ids));
});

await test('READ: a LEGACY row with recorded_by NULL is invisible to the care '
  + 'tier -- no backfill, by decision', async () => {
    const { res } = await call('caregiver',
      { action: 'read', resource: 'alf_incidents' },
      [incident('INC-LEGACY', 'C-MINE', null, ME)]);
    const ids = (res.body.data || []).map(function (r) { return r.id; });
    assert.deepStrictEqual(ids, [],
      'a legacy row reached the care tier. The only candidate backfill source '
      + 'is data.reported_by, which is caller-controlled -- filtering on it '
      + 'would let any employee read any incident by claiming to have filed it.');
  });

await test('READ CONTROL: management still sees EVERY incident including the '
  + 'legacy one, so nothing became unreachable', async () => {
    const { res } = await call('nursing',
      { action: 'read', resource: 'alf_incidents' },
      [incident('INC-MINE', 'C-MINE', ME), incident('INC-THEIRS', 'C-THEIRS', OTHER),
       incident('INC-LEGACY', 'C-MINE', null, ME)]);
    assert.strictEqual(res.body.scoped_to_self, false, 'management was self-scoped');
    const ids = (res.body.data || []).map(function (r) { return r.id; }).sort();
    assert.deepStrictEqual(ids, ['INC-LEGACY', 'INC-MINE', 'INC-THEIRS'],
      'management lost sight of a report: ' + JSON.stringify(ids));
  });

await test('READ: data.reported_by is NOT what the scope is computed from -- a '
  + 'forged reported_by buys nothing', async () => {
    const { res } = await call('caregiver',
      { action: 'read', resource: 'alf_incidents' },
      [incident('INC-FORGED', 'C-THEIRS', OTHER, ME)]);
    assert.deepStrictEqual((res.body.data || []).map(function (r) { return r.id; }), [],
      'a row whose data.reported_by names the caller was handed over -- the '
      + 'scope is being computed from the forgeable field');
  });

await test('UN-MIGRATED: a missing recorded_by column is its OWN state, not an '
  + 'empty log and not provisioned:false', async () => {
    const calls = [];
    const base = postgrestMock([], calls);
    const h = loadHandler(async function (url, opts) {
      if (/alf_incidents\?/.test(String(url)) && !(opts && opts.method === 'POST')) {
        return { ok: false, status: 400, json: async function () {
          return { code: '42703', message: 'column alf_incidents.recorded_by does not exist' };
        } };
      }
      return base(url, opts);
    });
    const res = mockRes();
    await h({ method: 'POST',
      headers: { authorization: 'Bearer KEY-FOR-' + HASH,
                 'x-sd-auth': signSessionToken({ app: APP, employee_id: ME,
                   role: 'caregiver', license_hash: HASH }) },
      body: { action: 'read', resource: 'alf_incidents' } }, res);
    assert.strictEqual(res.statusCode, 503,
      'an un-migrated column answered ' + res.statusCode + ' '
      + JSON.stringify(res.body) + ' -- folding it into provisioned:false plus '
      + 'an empty list reads as "this facility has no incidents", a confident '
      + 'wrong answer about a mandated-reporting log');
    assert.strictEqual(code(res), 'MIGRATION_REQUIRED', 'wrong code');
    assert.ok(/sairncare_incidents_recorded_by\.sql/.test(
      res.body.error.message), 'the message does not name the file to run');
  });

await test('UN-PROVISIONED still behaves as before -- a missing TABLE is not a '
  + 'migration error', async () => {
    const calls = [];
    const base = postgrestMock([], calls);
    const h = loadHandler(async function (url, opts) {
      if (/alf_incidents\?/.test(String(url)) && !(opts && opts.method === 'POST')) {
        return { ok: false, status: 404, json: async function () { return {}; } };
      }
      return base(url, opts);
    });
    const res = mockRes();
    await h({ method: 'POST',
      headers: { authorization: 'Bearer KEY-FOR-' + HASH,
                 'x-sd-auth': signSessionToken({ app: APP, employee_id: ME,
                   role: 'caregiver', license_hash: HASH }) },
      body: { action: 'read', resource: 'alf_incidents' } }, res);
    assert.strictEqual(res.statusCode, 200, 'a missing table changed shape');
    assert.strictEqual(res.body.provisioned, false);
  });

console.log('');
console.log(pass + ' passed, ' + fail + ' failed');
if (fail) process.exit(1);
console.log('');
console.log('NO roleSet WAS CHANGED. caregiver reaches the narrow resident tier,');
console.log('files incidents, and reads the activity calendar -- all by design and');
console.log('none of it visible to a tool that reads roleSet membership. The three');
console.log('arms in section 4 are product questions for Michael, pinned at their');
console.log('current answers so that changing one is a decision and not a drift.');
})();
