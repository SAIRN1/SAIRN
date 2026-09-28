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
  return { license_hash: HASH, client_id: id, assigned_employee_id: assignee,
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
      { license_hash: HASH, entry_id: 'CR-MINE', staff_id: ME,
        record_type: 'credential', data: { marker: 'mine' }, recorded_by: 'owner-1', created_at: '2026-01-01' },
      { license_hash: HASH, entry_id: 'CR-THEIRS', staff_id: OTHER,
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

await test('alf_family_contacts read: caregiver is refused. OPEN -- a caregiver '
  + 'caring for a resident arguably needs their emergency contact', async () => {
    const { res } = await call('caregiver',
      { action: 'read', resource: 'alf_family_contacts' }, []);
    assert.strictEqual(res.statusCode, 403,
      'this changed. If caregivers were granted family contacts, note that the '
      + 'gate has NO narrow tier -- it is facility-wide, so this grants every '
      + 'resident\'s contacts, not the assigned ones.');
  });

// alf_staff_credentials was listed here as an open question on the assumption
// that the gate had no self-scope. IT DOES -- see section 2b -- so the question
// does not exist and the arm has moved there as a positive assertion. Left
// named rather than deleted, because a question that turned out to be already
// answered is worth one line to stop it being re-asked.

await test('alf_incidents read: caregiver cannot read back the report they just '
  + 'filed. OPEN -- deliberate for EDIT, less obviously right for READ', async () => {
    const { res } = await call('caregiver',
      { action: 'read', resource: 'alf_incidents' }, []);
    assert.strictEqual(res.statusCode, 403,
      'this changed. The branch deliberately ends the filer\'s WRITE access once '
      + 'the report is saved; not being able to READ your own filed report is a '
      + 'different question and the comment does not address it.');
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
