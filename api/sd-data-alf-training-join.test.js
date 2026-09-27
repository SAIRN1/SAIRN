// api/sd-data-alf-training-join.test.js
// REQUIREMENT: a per-staff training verdict is computed from the SERVER's own
//   append-only alf_staff_credentials records, in a window somebody DECLARED,
//   and never from a staff array the caller sent.
//
// Run: node api/sd-data-alf-training-join.test.js
//
// ── THE ARM THAT MATTERS IS THE FIRST ONE, AND IT WAS A LIVE HOLE ──────────
// Before this change the evaluate branch built its options as
// `Object.assign({}, payload, ...)`, so `payload.staff` went straight into
// evaluateTraining's per-staff branch. Anybody holding a SAIRNcare session could
// POST
//
//   {action:'evaluate', resource:'alf_compliance_rules', payload:{
//      state:'IN', requirement_type:'training',
//      staff:[{staff_id:'X', annual_hours_recorded:999, applies_to:[...]}]}}
//
// and be handed a training-compliance verdict computed entirely from numbers they
// chose, while the authoritative record sat unread one branch away.
//
// THE ENGINE'S BRANCH WAS CALLED DORMANT BECAUSE sairncare.html NEVER SENDS
// `staff`. That is a fact about the UI, not about the endpoint -- the API is the
// boundary, not the panel -- and it is the reason this arm is first.
//
// ── THE SECOND IS THE WINDOW, AND IT IS A REFUSAL ON PURPOSE ──────────────
// `annual_hours` has three defensible readings (rolling twelve months, calendar
// year, the facility's own training year) and they give different answers.
// docs/2026-09-26-sairncare-compliance-join-scoping.md's first unblock item is
// that somebody decides. Until then an undeclared window is refused, named, and
// whichever window IS used is reported on every finding.
//
// ── AND THE THIRD IS THAT AN ABSENT TABLE MUST NOT READ AS ZERO HOURS ─────
// An unprovisioned credentials table returning [] would make every staff member
// non-compliant -- a facility-wide false FAIL, which is a worse answer than none.

const assert = require('assert');

function mockRes() {
  var res = { statusCode: null, body: null };
  res.status = function (c) { res.statusCode = c; return res; };
  res.json = function (b) { res.body = b; return res; };
  return res;
}
function mockReq(payload) {
  return {
    method: 'POST',
    headers: { authorization: 'Bearer ALF-TEST-KEY', 'x-sd-auth': 'tok' },
    body: { action: 'evaluate', resource: 'alf_compliance_rules',
            payload: payload || {} }
  };
}

let passed = 0;
async function test(name, fn) {
  try { await fn(); passed++; console.log('  ok - ' + name); }
  catch (e) { console.error('  FAIL - ' + name + '\n    ' + e.message); process.exitCode = 1; }
}

// THE RULES ARE THE REAL SEEDED ONES, read out of the seed file rather than
// invented here. A hand-written fixture rule would let this suite pass against a
// vocabulary the product does not have -- which is the exact defect the WV rows
// caused in the engine.
const SEED = require('../sql/sairncare_compliance_seed.json');
const TRAINING = SEED.rules.filter((r) => r.requirement_type === 'training');
const WV = TRAINING.filter((r) => r.state === 'WV');
assert.ok(WV.length === 1, 'the seed no longer carries exactly one WV training rule');

function loadHandler(opts) {
  opts = opts || {};
  const calls = [];
  delete require.cache[require.resolve('./_lib/license')];
  require.cache[require.resolve('./_lib/license')] = {
    exports: {
      validateLicenseKey: async function () {
        return { valid: true, active: true, license_hash: 'test-hash',
                 trial_ends_at: null, stripe_subscription_id: null };
      }
    }
  };
  const realAuth = require('./_lib/auth');
  delete require.cache[require.resolve('./_lib/auth')];
  require.cache[require.resolve('./_lib/auth')] = {
    exports: Object.assign({}, realAuth, {
      tokenFromRequest: function () { return 'tok'; },
      verifySessionToken: function () {
        return opts.noSession ? null : { employee_id: 'emp-1', role: opts.role || 'owner' };
      }
    })
  };
  global.fetch = async function (url, init) {
    const u = String(url);
    calls.push({ url: u, method: (init && init.method) || 'GET' });
    const answer = (st, rows) => ({ ok: st === 200, status: st, json: async () => rows });
    if (u.indexOf('alf_compliance_rules') !== -1) {
      return answer(opts.rulesStatus || 200, opts.rules || WV);
    }
    if (u.indexOf('alf_staff_credentials') !== -1) {
      return answer(opts.credStatus || 200, opts.creds || []);
    }
    if (u.indexOf('alf_staff') !== -1) {
      return answer(opts.staffStatus || 200, opts.staff || []);
    }
    return answer(200, []);
  };
  delete require.cache[require.resolve('./sd-data.js')];
  return { handler: require('./sd-data.js'), calls: calls };
}

// One caregiver. WV's `all_staff` audience applies to every position with no
// mapping at all, which is why it is the audience that works.
const ROSTER = [{ staff_id: 'ST-1', data: { name: 'A. Caregiver', position: 'caregiver' } }];
function hours(n, category, on) {
  return [{ staff_id: 'ST-1', data: { hours: n, category: category || 'dementia',
                                      completed_on: on || '2026-06-01' } }];
}

async function main() {
  console.log('alf_compliance_rules evaluate -- the records join, and the two '
    + 'refusals in front of it\n');

  await test('THE ARM THAT MATTERS: a caller-supplied `staff` array is REFUSED '
    + '400, not evaluated -- it let the caller choose the compliance answer',
    async () => {
      const { handler } = loadHandler();
      const res = mockRes();
      await handler(mockReq({ state: 'WV', requirement_type: 'training',
        facility_class: WV[0].facility_class,
        staff: [{ staff_id: 'X', annual_hours_recorded: 999 }] }), res);
      assert.strictEqual(res.statusCode, 400, JSON.stringify(res.body));
      assert.strictEqual(res.body.error.code, 'STAFF_NOT_CALLER_SUPPLIED');
    });

  await test('...and the refusal says the record is on the SERVER, so a reader '
    + 'knows what to ask for instead',
    async () => {
      const { handler } = loadHandler();
      const res = mockRes();
      await handler(mockReq({ state: 'WV', requirement_type: 'training',
        facility_class: WV[0].facility_class, staff: [] }), res);
      assert.strictEqual(res.statusCode, 400);
      assert.ok(/include_staff/.test(res.body.error.message), res.body.error.message);
      // AN EMPTY ARRAY IS REFUSED TOO. `staff: []` is still the caller deciding
      // the input, and a check that only refused a NON-empty one would be
      // satisfied by the shape rather than the boundary.
    });

  await test('a request WITHOUT include_staff is unchanged -- every existing '
    + 'caller still gets exactly the requirements, and no roster is read',
    async () => {
      const { handler, calls } = loadHandler();
      const res = mockRes();
      await handler(mockReq({ state: 'WV', requirement_type: 'training',
        facility_class: WV[0].facility_class }), res);
      assert.strictEqual(res.statusCode, 200, JSON.stringify(res.body));
      assert.ok(!res.body.staff_findings, 'a per-staff finding appeared unasked');
      assert.ok(!calls.some((c) => c.url.indexOf('alf_staff?') !== -1),
        'the roster was read for a request that did not ask for staff');
    });

  await test('THE WINDOW IS DECIDED, NOT REFUSED (re-pinned 2026-09-27): '
    + 'include_staff with NO annual_window now ANSWERS, because picking one was '
    + 'Michael\'s decision to make and he made it -- rolling twelve months '
    + 'anchored to each staff member\'s hire date',
    async () => {
      const { handler } = loadHandler({ staff: ROSTER, creds: hours(3) });
      const res = mockRes();
      await handler(mockReq({ state: 'WV', requirement_type: 'training',
        facility_class: WV[0].facility_class, include_staff: true,
        on_date: '2026-09-27' }), res);
      assert.strictEqual(res.statusCode, 200, JSON.stringify(res.body));
      const f = (res.body.staff_findings || [])[0];
      assert.ok(f, 'no staff finding: ' + JSON.stringify(res.body).slice(0, 300));
      assert.strictEqual(f.hours_window, 'rolling_12_months_from_hire',
        JSON.stringify(f));
    });

  await test('...and an UNKNOWN window is STILL refused rather than falling back '
    + 'to the default -- a typo must not silently choose a reading, and the '
    + 'refusal names the default and every accepted value',
    async () => {
      const { handler } = loadHandler({ staff: ROSTER, creds: hours(3) });
      const res = mockRes();
      await handler(mockReq({ state: 'WV', requirement_type: 'training',
        facility_class: WV[0].facility_class, include_staff: true,
        annual_window: 'rolling_twelve_months' }), res);
      assert.strictEqual(res.statusCode, 400, JSON.stringify(res.body));
      assert.strictEqual(res.body.error.code, 'ANNUAL_WINDOW_UNKNOWN');
      ['rolling_12_months_from_hire', 'rolling_12_months', 'calendar_year',
       'facility_training_year'].forEach((w) => {
        assert.ok(res.body.error.message.indexOf(w) !== -1, 'window ' + w + ' not named');
      });
    });

  await test('THE ANCHOR IS NOT POPULATED YET AND THE ENDPOINT SAYS SO RATHER '
    + 'THAN GUESSING: alf_staff carries no hire date -- saveStaff() collects '
    + 'name, phone, position, cert_expiry, bgcheck_date, status and notes -- so '
    + 'a roster row with none comes back meets:null / NO_HIRE_DATE, never false',
    async () => {
      const { handler } = loadHandler({ staff: ROSTER, creds: hours(3) });
      const res = mockRes();
      await handler(mockReq({ state: 'WV', requirement_type: 'training',
        facility_class: WV[0].facility_class, include_staff: true,
        on_date: '2026-09-27' }), res);
      const f = res.body.staff_findings[0];
      assert.strictEqual(f.meets, null, JSON.stringify(f));
      assert.strictEqual(f.hours_window_error, 'NO_HIRE_DATE', JSON.stringify(f));
    });

  await test('...and ONE `hire_date` on the roster blob is all it takes -- '
    + 'alf_staff stores an open jsonb blob so no migration is involved, which '
    + 'is why the remaining gap is a UI field and not a schema change',
    async () => {
      const withHire = [{ staff_id: 'ST-1',
        data: { name: 'A. Caregiver', position: 'caregiver',
                hire_date: '2024-11-03' } }];
      const { handler } = loadHandler({ staff: withHire, creds: hours(3) });
      const res = mockRes();
      await handler(mockReq({ state: 'WV', requirement_type: 'training',
        facility_class: WV[0].facility_class, include_staff: true,
        on_date: '2026-09-27' }), res);
      const f = res.body.staff_findings[0];
      assert.strictEqual(f.meets, true, JSON.stringify(f));
      assert.strictEqual(f.hours_window_from, '2025-11-03', JSON.stringify(f));
      assert.strictEqual(f.hours_window_error, null, JSON.stringify(f));
    });

  await test('AN ABSENT CREDENTIALS TABLE IS 503, NOT ZERO HOURS -- reading [] '
    + 'would report every staff member non-compliant, which is a '
    + 'facility-wide false FAIL rather than a gap',
    async () => {
      const { handler } = loadHandler({ staff: ROSTER, credStatus: 404 });
      const res = mockRes();
      await handler(mockReq({ state: 'WV', requirement_type: 'training',
        facility_class: WV[0].facility_class, include_staff: true,
        annual_window: 'rolling_12_months' }), res);
      assert.strictEqual(res.statusCode, 503, JSON.stringify(res.body));
      assert.strictEqual(res.body.error.code, 'NOT_PROVISIONED');
    });

  await test('...and an absent ROSTER is 503 for the mirror reason -- "no staff" '
    + 'would report a facility with no obligations',
    async () => {
      const { handler } = loadHandler({ staffStatus: 404 });
      const res = mockRes();
      await handler(mockReq({ state: 'WV', requirement_type: 'training',
        facility_class: WV[0].facility_class, include_staff: true,
        annual_window: 'rolling_12_months' }), res);
      assert.strictEqual(res.statusCode, 503, JSON.stringify(res.body));
    });

  await test('THE JOIN: West Virginia now answers a real verdict for a '
    + 'caregiver -- the state the engine used to REFUSE outright',
    async () => {
      const { handler } = loadHandler({ staff: ROSTER, creds: hours(3) });
      const res = mockRes();
      await handler(mockReq({ state: 'WV', requirement_type: 'training',
        facility_class: WV[0].facility_class, include_staff: true,
        annual_window: 'rolling_12_months', on_date: '2026-09-26' }), res);
      assert.strictEqual(res.statusCode, 200, JSON.stringify(res.body));
      const f = (res.body.staff_findings || [])[0];
      assert.ok(f, 'no staff finding: ' + JSON.stringify(res.body).slice(0, 300));
      assert.strictEqual(f.staff_id, 'ST-1');
      assert.strictEqual(f.meets, true, JSON.stringify(f));
      assert.strictEqual(f.recorded_annual_hours, 3);
      // WV's all_staff row is 2 hours a year. 3 recorded clears it.
      assert.strictEqual(f.required_annual_hours, 2, JSON.stringify(f));
    });

  await test('...and it says the hours came from the SERVER RECORDS, so a verdict '
    + 'computed from a record can never be mistaken for one computed from a '
    + 'number a caller sent',
    async () => {
      const { handler } = loadHandler({ staff: ROSTER, creds: hours(3) });
      const res = mockRes();
      await handler(mockReq({ state: 'WV', requirement_type: 'training',
        facility_class: WV[0].facility_class, include_staff: true,
        annual_window: 'rolling_12_months', on_date: '2026-09-26' }), res);
      const f = res.body.staff_findings[0];
      assert.strictEqual(f.hours_source, 'server_records');
      assert.strictEqual(f.hours_window, 'rolling_12_months');
      assert.ok(f.hours_window_meaning, 'the window is reported but not explained');
    });

  await test('UNDER-trained is FALSE, and that is the arm that proves the pass '
    + 'is not the only answer it can give',
    async () => {
      const { handler } = loadHandler({ staff: ROSTER, creds: hours(1) });
      const res = mockRes();
      await handler(mockReq({ state: 'WV', requirement_type: 'training',
        facility_class: WV[0].facility_class, include_staff: true,
        annual_window: 'rolling_12_months', on_date: '2026-09-26' }), res);
      const f = res.body.staff_findings[0];
      assert.strictEqual(f.meets, false, JSON.stringify(f));
      assert.strictEqual(f.shortfall_hours, 1);
    });

  await test('HOURS OUTSIDE THE WINDOW DO NOT COUNT -- training from three years '
    + 'ago is not this year\'s training, and the window is the whole reason '
    + 'the endpoint refuses to guess it',
    async () => {
      const { handler } = loadHandler({ staff: ROSTER, creds: hours(9, 'dementia', '2023-01-01') });
      const res = mockRes();
      await handler(mockReq({ state: 'WV', requirement_type: 'training',
        facility_class: WV[0].facility_class, include_staff: true,
        annual_window: 'rolling_12_months', on_date: '2026-09-26' }), res);
      const f = res.body.staff_findings[0];
      assert.strictEqual(f.recorded_annual_hours, 0, JSON.stringify(f));
      assert.strictEqual(f.meets, false);
      assert.strictEqual(f.records_counted, 0);
    });

  await test('A RECORD WITH NO completed_on IS COUNTED AS SKIPPED AND SAID SO, '
    + 'not dropped -- hours nobody dated cannot be placed in a window, and '
    + 'silently ignoring them is how a shortfall appears from nowhere',
    async () => {
      const { handler } = loadHandler({ staff: ROSTER,
        creds: [{ staff_id: 'ST-1', data: { hours: 5, category: 'dementia' } }] });
      const res = mockRes();
      await handler(mockReq({ state: 'WV', requirement_type: 'training',
        facility_class: WV[0].facility_class, include_staff: true,
        annual_window: 'rolling_12_months', on_date: '2026-09-26' }), res);
      const f = res.body.staff_findings[0];
      assert.strictEqual(f.records_skipped_no_completed_on, 1, JSON.stringify(f));
      assert.strictEqual(f.recorded_annual_hours, 0);
    });

  await test('THE ADMINISTRATOR REQUIREMENT IS NAMED AS UNMAPPED, NOT DROPPED -- '
    + 'a requirement this code cannot attribute contributing zero is exactly '
    + 'how WV\'s two real rows became a confident pass the first time',
    async () => {
      const { handler } = loadHandler({ staff: ROSTER, creds: hours(3) });
      const res = mockRes();
      await handler(mockReq({ state: 'WV', requirement_type: 'training',
        facility_class: WV[0].facility_class, include_staff: true,
        annual_window: 'rolling_12_months', on_date: '2026-09-26' }), res);
      assert.ok(Array.isArray(res.body.unmapped_requirements),
        'no unmapped list: ' + JSON.stringify(res.body).slice(0, 300));
      assert.strictEqual(res.body.unmapped_requirements.length, 1);
      assert.ok(/administrator/.test(JSON.stringify(res.body.unmapped_requirements)));
      assert.ok(/never "compliant"/.test(res.body.unmapped_requirements_caveat || ''),
        res.body.unmapped_requirements_caveat);
    });

  await test('a session is still required -- the join did not open a door',
    async () => {
      const { handler } = loadHandler({ noSession: true });
      const res = mockRes();
      await handler(mockReq({ state: 'WV', requirement_type: 'training',
        include_staff: true, annual_window: 'rolling_12_months' }), res);
      assert.strictEqual(res.statusCode, 401, JSON.stringify(res.body));
    });

  console.log('\n' + passed + ' assertion(s) passed');
  if (process.exitCode) console.log('SOME ASSERTIONS FAILED');
  else console.log('ALL ALF TRAINING-JOIN ASSERTIONS PASS');
}

main();
