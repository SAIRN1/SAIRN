// api/sd-data-sen-caregiver-pii-scope.test.js
//
// REQUIREMENT: a SAIRNsenior session outside management cannot read a
//   caregiver's BACKGROUND-CHECK DATE, STATE-ISSUED CAREGIVER ID or free-text
//   HR NOTES through sen_caregivers/read -- and still gets everything
//   scheduling and coordination actually need.
//
// Run:  node api/sd-data-sen-caregiver-pii-scope.test.js
//
// ── THE DEFECT THIS HOLDS (hover2 seq 965, high, found 2026-10-06) ─────────
// sen_caregivers/read verified a session and then returned `data` whole, every
// row on the licence, to ANY authenticated sairnsenior role. The branch's own
// comment justified the lighter gate with "Employment/certification data, not
// client PHI" -- true, and the wrong comparison: it is EMPLOYEE PII, and three
// of its fields serve no scheduling purpose at all.
//
// ── WHY THE ARMS ARE SHAPED AROUND TWO LISTS AND NOT ONE ──────────────────
// A redaction suite that only asserts "the secret is gone" passes just as well
// against a branch that returns an empty object, and an empty roster breaks
// this app in a way the access-control arm cannot see: senIsScheduler() reads
// the roster agency-wide, certDaysUntil() computes from cpr_expiry, and visits
// join on employee_id. So every arm below asserts BOTH halves -- the three
// fields are absent AND the nine the app needs survived. That is the pairing
// docs/2026-09-13-cross-domain-disciplines.md asks for: a check whose pass
// condition can be met by breaking the feature is not a check.
//
// ── THE FIELD LIST IS TAKEN FROM THE WRITE SITE, NOT FROM THE BRANCH ──────
// sairnsenior.html saveCaregiver() (:2681) is the only thing that puts a
// caregiver row in the table, so it is the authority on what a row contains.
// Reading the list off the READ branch would make this suite agree with the
// handler by construction and prove nothing about coverage.
//
// ── WHAT THIS DOES NOT DO ─────────────────────────────────────────────────
// It does not test the DATABASE, it does not test the write gate (management
// only -- a separate question), and it does not test the CLIENT. The roster
// table's "Restricted" cell in sairnsenior.html matters for a different
// reason -- a blank compliance column reads as "no check on file" -- and is
// not asserted here because this file drives the handler, not the page.
//
// IT ALSO DOES NOT TEST THE TENANT BOUNDARY. license_hash scoping on this
// resource is api/sd-data-cross-tenant-dispatchers.test.js's job; the mock
// below honours eq. clauses so a dropped filter would be visible, but no arm
// here asserts on it and this file must not be read as covering it.

'use strict';

process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET
  || ['sen', 'caregiver', 'pii', 'fixture'].join('-');
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://test.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'test-key';

const assert = require('assert');
const { signSessionToken, ROLES_BY_APP } = require('./_lib/auth');

const HASH = 'sen-tenant-hash';
const APP = 'sairnsenior';

// The three fields the redaction removes, and the nine that must survive it.
// HR_FIELDS is what the handler strips; KEPT_FIELDS is every other key
// saveCaregiver() stores. Together they are the whole record, which is what
// makes the "nothing else was dropped" arm possible.
const HR_FIELDS = ['bgcheck_date', 'state_caregiver_id', 'notes'];
const KEPT_FIELDS = ['id', 'name', 'phone', 'cpr_expiry', 'status',
                     'aide_type', 'program', 'employee_id', 'branch_id'];
// Membership of the tier that keeps the HR half. Written out rather than
// imported from the handler: a suite that reads the handler's own constant
// cannot fail when that constant is widened, which is the change this file
// exists to notice.
const HR_ROLES = ['owner', 'billing'];

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

// ── THE MOCK ──────────────────────────────────────────────────────────────
// Filters seeded rows by every `<col>=eq.<value>` clause and honours
// `select=`, the way PostgREST does and the way the branch under test asks.
// Every way it is unfaithful runs in the safe direction: an unrecognised
// clause is not applied, so it returns MORE rows than the real thing would
// and an assertion fails louder. The negative control at the bottom drives
// the select= half rather than asserting it.
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
        return [{ license_hash: forHash || HASH, employee_id: 'emp-1',
                  role: 'owner', active: true }]; } };
    }
    if (opts && opts.method === 'POST') {
      const sent = JSON.parse(opts.body);
      return { ok: true, status: 200, json: async function () { return [sent]; } };
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

// Fresh per call, with the REAL api/_lib/auth: the role arrives inside a
// signed token and a stub there would answer part of the question this file
// asks.
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

function mockReq(body, employeeId, role) {
  return {
    method: 'POST',
    headers: {
      authorization: 'Bearer KEY-FOR-' + HASH,
      'x-sd-auth': signSessionToken({ app: APP, employee_id: employeeId,
                                      role: role, license_hash: HASH })
    },
    body: body
  };
}

async function readAs(role, rows) {
  const calls = [];
  const h = loadHandler(postgrestMock(rows, calls));
  const res = mockRes();
  await h(mockReq({ action: 'read', resource: 'sen_caregivers' }, 'emp-1', role), res);
  return { res: res, calls: calls };
}

// A row in the shape the SELECT asks for, carrying EVERY field
// saveCaregiver() stores so an over-broad response has something to leak.
function caregiverRow(id) {
  return {
    license_hash: HASH, app_id: APP, caregiver_id: id,
    data: {
      name: 'Dana Okonkwo', phone: '330-555-0147', cpr_expiry: '2027-03-01',
      bgcheck_date: '2026-02-14', status: 'active', notes: 'disclosed a prior'
        + ' conviction at interview; cleared by the agency',
      aide_type: 'STNA', program: 'PASSPORT',
      state_caregiver_id: 'OH-STNA-884213',
      employee_id: 'emp-7', branch_id: 'BR-2'
    },
    updated_at: '2026-09-01T00:00:00.000Z'
  };
}

const UNREACHED = [];
function reached(res, what) {
  if (res.statusCode !== 200) {
    UNREACHED.push([what, res.statusCode,
                    (res.body && res.body.error && res.body.error.code) || '']);
    assert.fail('UNREACHED: ' + what + ' answered ' + res.statusCode + ' '
      + JSON.stringify(res.body) + ' -- this arm never reached the redaction, so '
      + 'it proves nothing. Fix the fixture, do not relax the assertion.');
  }
}
function firstItem(res) {
  return ((res.body && res.body.data) || [])[0] || {};
}

(async function () {
  console.log('sen_caregivers READ -- employee-PII field scope (hover2 seq 965)');

  section('THE NON-MANAGEMENT TIERS -- every role sairnsenior has that is not '
    + 'owner or billing');

  const nonHr = (ROLES_BY_APP[APP] || []).filter(function (r) {
    return HR_ROLES.indexOf(r) === -1;
  });

  await test('sairnsenior actually HAS roles outside the HR tier -- otherwise '
    + 'every arm below is vacuous', async () => {
      assert.ok(nonHr.length > 0,
        'ROLES_BY_APP.' + APP + ' is ' + JSON.stringify(ROLES_BY_APP[APP])
        + ', so there is no role outside ' + JSON.stringify(HR_ROLES) + ' to '
        + 'test with and this whole suite would pass by having nothing to do.');
    });

  for (const role of nonHr) {
    await test('[' + role + '] the three HR fields are ABSENT -- not empty, '
      + 'absent', async () => {
        const { res } = await readAs(role, [caregiverRow('CG-1')]);
        reached(res, 'the ' + role + ' read');
        const item = firstItem(res);
        const leaked = HR_FIELDS.filter(function (f) { return f in item; });
        assert.deepStrictEqual(leaked, [],
          role + ' was handed ' + JSON.stringify(leaked) + '. A background-check '
          + 'date, a state caregiver ID and free-text HR notes about a colleague '
          + 'are not scheduling facts, and this role can neither write nor need '
          + 'them. Full item: ' + JSON.stringify(item));
      });

    await test('[' + role + '] ...and the nine fields the app needs SURVIVED, '
      + 'so the arm above cannot be satisfied by returning nothing', async () => {
        const { res } = await readAs(role, [caregiverRow('CG-1')]);
        reached(res, 'the ' + role + ' read');
        const item = firstItem(res);
        const missing = KEPT_FIELDS.filter(function (f) { return !(f in item); });
        assert.deepStrictEqual(missing, [],
          role + ' lost ' + JSON.stringify(missing) + '. senIsScheduler() reads '
          + 'this roster agency-wide, certDaysUntil() computes from cpr_expiry and '
          + 'visits join on employee_id -- stripping those breaks the feature the '
          + 'lighter gate exists to serve. Full item: ' + JSON.stringify(item));
      });

    await test('[' + role + '] ...and the response SAYS it was redacted, '
      + 'because a missing field and an empty one are the same thing to a '
      + 'caller that cannot ask', async () => {
        const { res } = await readAs(role, [caregiverRow('CG-1')]);
        reached(res, 'the ' + role + ' read');
        assert.strictEqual(res.body.hr_fields_visible, false,
          'hr_fields_visible came back ' + JSON.stringify(res.body.hr_fields_visible)
          + '. Undeclared redaction is how a blank background-check column gets '
          + 'read as "no check on file" on a compliance field.');
      });
  }

  section('THE MANAGEMENT TIER -- the negative half: the redaction must not '
    + 'apply to everyone, or it is a flat refusal wearing a field list');

  for (const role of HR_ROLES) {
    await test('[' + role + '] sees the whole record, all twelve fields',
      async () => {
        const { res } = await readAs(role, [caregiverRow('CG-1')]);
        reached(res, 'the ' + role + ' read');
        const item = firstItem(res);
        const missing = HR_FIELDS.concat(KEPT_FIELDS)
          .filter(function (f) { return !(f in item); });
        assert.deepStrictEqual(missing, [],
          role + ' is inside the HR tier and lost ' + JSON.stringify(missing)
          + '. If management cannot read these back, the redaction is a wipe: the '
          + 'write path sends whole records, so nobody could ever restore them.');
      });

    await test('[' + role + '] ...and the response says so', async () => {
      const { res } = await readAs(role, [caregiverRow('CG-1')]);
      reached(res, 'the ' + role + ' read');
      assert.strictEqual(res.body.hr_fields_visible, true,
        'hr_fields_visible came back ' + JSON.stringify(res.body.hr_fields_visible)
        + ' for a role that CAN see the fields.');
    });
  }

  section('ROUND-TRIP WIPE -- the check alf_facility\'s comment says has to be '
    + 'done for every field-level redaction');

  await test('a non-HR role cannot WRITE sen_caregivers, which is the only '
    + 'reason the redaction cannot erase the three fields', async () => {
      const role = nonHr[0];
      const calls = [];
      const h = loadHandler(postgrestMock([caregiverRow('CG-1')], calls));
      const res = mockRes();
      await h(mockReq({ action: 'write', resource: 'sen_caregivers',
                        payload: { id: 'CG-1', name: 'Dana Okonkwo' } },
                      'emp-1', role), res);
      assert.strictEqual(res.statusCode, 403,
        role + ' got ' + res.statusCode + ' ' + JSON.stringify(res.body)
        + ' on a write. THE REDACTION\'S SAFETY DEPENDS ON THIS: this client reads '
        + 'whole records and writes them back, so a role holding a stripped copy '
        + 'that may also save it would erase the background-check date for the '
        + 'whole agency. If the write gate is ever widened past the read tier, '
        + 'the redaction must change with it.');
      assert.ok(!calls.some(function (c) { return c.opts && c.opts.method === 'POST'; }),
        'the refusal still issued a POST, so the row was written before the gate '
        + 'answered: ' + JSON.stringify(calls.map(function (c) { return c.url; })));
    });

  section('NEGATIVE CONTROLS -- the fixture and the mock, driven rather than '
    + 'asserted');

  await test('the seeded row really CARRIES all three HR fields, so the '
    + 'absence arms are measuring a removal and not an empty fixture',
    async () => {
      const seeded = caregiverRow('CG-1').data;
      const absent = HR_FIELDS.filter(function (f) { return !(f in seeded); });
      assert.deepStrictEqual(absent, [],
        'the fixture itself is missing ' + JSON.stringify(absent) + '. Every '
        + '"absent" arm above would then pass against a handler that redacts '
        + 'nothing at all.');
    });

  await test('the mock honours select= -- so "the handler built the response '
    + 'from caregiver_id,data" is a real claim', async () => {
      const f = postgrestMock([caregiverRow('CG-1')], []);
      const projected = await (await f('https://x/rest/v1/sen_caregivers'
        + '?license_hash=eq.' + HASH + '&select=caregiver_id,data')).json();
      assert.deepStrictEqual(Object.keys(projected[0]).sort(),
        ['caregiver_id', 'data'],
        'the mock ignored select= and returned '
        + JSON.stringify(Object.keys(projected[0])) + '.');
    });

  await test('no session at all is 401, not a redacted 200 -- the gate this '
    + 'branch already had is still there', async () => {
      const calls = [];
      const h = loadHandler(postgrestMock([caregiverRow('CG-1')], calls));
      const res = mockRes();
      await h({ method: 'POST',
                headers: { authorization: 'Bearer KEY-FOR-' + HASH },
                body: { action: 'read', resource: 'sen_caregivers' } }, res);
      assert.strictEqual(res.statusCode, 401,
        'an unauthenticated read answered ' + res.statusCode + ' '
        + JSON.stringify(res.body) + '. Adding a field redaction must not have '
        + 'turned the session refusal into a partial answer.');
    });

  // ══ ADDED 2026-10-13 BY THE REVIEWER OF THIS FIX, NOT ITS AUTHOR ═════════
  // Discharging the Tier A obligation on seq965 meant grepping every render
  // and every read of the three HR fields rather than reading the branch the
  // finding named. That found THREE more places, two of them defects:
  //
  //   sairnsenior.html:5722   the COMPLIANCE panel's "Background Check"
  //                           column, ungated -- every row read "no check on
  //                           file" for any role outside owner/billing, on the
  //                           one column a state surveyor asks about. FIXED.
  //   sairnsenior.html:5745   exportCsv('caregivers'), ungated -- a CSV
  //                           asserting the agency holds no background checks,
  //                           with nothing on the file to say otherwise. FIXED
  //                           by dropping the COLUMN, not blanking the cell.
  //   api/sd-data.js:6746     the EVV-readiness branch loads the UNREDACTED
  //                           blob under a WIDER role set. NOT a defect today
  //                           and pinned below so it cannot become one.
  //
  // The two client fixes are pinned by source assertion rather than by driving
  // the page: this suite has no DOM. That limit is stated rather than implied,
  // and a source assertion is still the thing that fails if somebody deletes
  // the guard -- which is the regression being guarded.
  section('THE OTHER THREE PLACES THE HR FIELDS ARE REACHED (reviewer, 2026-10-13)');

  await test('the EVV-readiness branch reads sen_caregivers under a WIDER role '
    + 'set than the redaction tier, and its engine emits no HR VALUE -- only '
    + 'presence. If summarize() ever echoes one, this arm is what fails',
    function () {
      const fs = require('fs');
      const ev = fs.readFileSync(require.resolve('./_lib/sen-evv-readiness.js'), 'utf8');
      // The engine may TEST a field; it must never put one in its output. Its
      // only output channels are miss() and warn(), both of which take fixed
      // label/reason strings, plus the `out` object built at the top of
      // checkVisit.
      const emits = ev.match(/(?:reason|label|value|detail)\s*:\s*[^,\n]*caregiver\.\w+/g) || [];
      assert.deepStrictEqual(emits, [],
        'the readiness engine puts a caregiver field VALUE into its output: '
        + emits.join(' | ') + '. That output goes to SEN_READINESS_ROLES '
        + '(owner, billing, coordinator, scheduler), which is WIDER than the '
        + 'redaction tier (owner, billing), so it would route around the '
        + 'redaction this whole suite exists to hold.');
      // ...and the arm is not vacuous: the engine really does reference the
      // fields, so a regex that matched nothing would prove nothing.
      assert.ok(/caregiver\.state_caregiver_id/.test(ev),
        'the readiness engine no longer references state_caregiver_id at all, '
        + 'so the arm above passed over nothing. Re-point it at whatever reads '
        + 'the caregiver row now.');
    });

  await test('sairnsenior.html renders the background-check column behind '
    + 'senIsManagement() in ALL THREE places, not just the roster', function () {
      const fs = require('fs');
      const path = require('path');
      const html = fs.readFileSync(
        path.join(__dirname, '..', 'sairnsenior.html'), 'utf8');
      const renders = html.match(/fdate\(c\.bgcheck_date\)/g) || [];
      assert.ok(renders.length >= 2,
        'expected at least the roster and the compliance panel to render '
        + 'bgcheck_date, found ' + renders.length + '. A zero here would make '
        + 'this arm vacuous rather than satisfied.');
      // Every render must sit on the TRUE side of a management ternary. Checked
      // by requiring the guarded form and forbidding a bare one.
      // THE VARIABLE NAME DIFFERS PER SITE AND THE FIRST DRAFT OF THIS ARM
      // MISSED ONE BECAUSE OF IT: the roster uses `isMgmt`, the compliance
      // panel `cpIsMgmt`, and a pattern anchored on `IsMgmt` with a capital I
      // matched only the second. It reported 1 of 2 and the "failure" was this
      // regex, not the page. Matched case-correctly on any local whose name
      // ends in `sMgmt` rather than on one spelling.
      const guarded = html.match(/[A-Za-z]*[Ii]sMgmt\s*\?\s*fdate\(c\.bgcheck_date\)/g) || [];
      assert.strictEqual(guarded.length, renders.length,
        guarded.length + ' of ' + renders.length + ' bgcheck_date renders are '
        + 'behind a management ternary. An UNGUARDED render does not leak the '
        + 'value -- the server already stripped it -- it renders the ABSENCE as '
        + 'a fact, on a compliance column. That is the defect, not a cosmetic '
        + 'one.');
    });

  await test('...and the caregivers CSV export DROPS the column rather than '
    + 'exporting an empty one, because a file leaves the building', function () {
      const fs = require('fs');
      const path = require('path');
      const html = fs.readFileSync(
        path.join(__dirname, '..', 'sairnsenior.html'), 'utf8');
      const m = html.match(/else if\s*\(type==='caregivers'\)\s*\{([\s\S]{0,900}?)\n  \}/);
      assert.ok(m, "the exportCsv caregivers branch could not be located, so "
        + 'this arm checked NOTHING -- a third state, not a pass');
      const body = m[1];
      assert.ok(/senIsManagement\(\)/.test(body),
        'exportCsv(\'caregivers\') does not consult senIsManagement(), so a '
        + 'non-management export writes a Background Check column that is '
        + 'empty for every caregiver: a document asserting no checks are on '
        + 'file. The claims branch in the same function already gates; this '
        + 'one must too.');
      assert.ok(/\[\s*'Name'\s*,\s*'Phone'\s*,\s*'CPR Expiry'\s*,\s*'Status'\s*\]/.test(body),
        'the non-management header row still carries Background Check. The '
        + 'column has to be ABSENT, not blank -- a blank cell is a claim, a '
        + 'missing column is a visibly shorter file.');
    });

  if (UNREACHED.length) {
    console.log('\nUNREACHED -- arms that never got to the redaction:');
    UNREACHED.forEach(function (u) { console.log('  %s -> %s %s', u[0], u[1], u[2]); });
    console.log('These are NOT scope failures and NOT passes.');
  }

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
