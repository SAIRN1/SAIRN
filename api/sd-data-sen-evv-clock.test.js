// api/sd-data-sen-evv-clock.test.js
// REQUIREMENT: a caregiver's clock time is CHECKED against the server that
//   receives it before it is stored, the claimed time is still what is stored,
//   and a correction is ADDITIVE.
//
// Run: node api/sd-data-sen-evv-clock.test.js
//
// ── WHY THIS SUITE EXISTS SEPARATELY FROM THE MODULE'S OWN 28 ARMS ─────────
// api/_lib/sen-evv-clock.js was written on 2026-09-26 with 28 arms and was
// UNREACHABLE: nothing called it, because api/sd-data.js was inside another
// session's claim. A pure module with a green suite and no caller is a rule
// nobody is subject to — and the defect it describes was live the whole time:
// vsClockIn/vsClockOut send `new Date().toISOString()` from the HANDSET and the
// server stored it verbatim.
//
// So these arms are about the SEAM. The module's arms prove the rules; these
// prove the endpoint applies them, stores what it should, and stores nothing it
// should not.
//
// ── THE ARM THAT MATTERS IS THAT THE CLAIMED TIME SURVIVES ────────────────
// "Use the server's clock" is the reflex and it destroys the offline path.
// sairnsenior replays queued clock events UNCHANGED, and its own comment says
// why: re-stamping on arrival produces an EVV record that is "precise, plausible
// and false". So the arm is not only that a bad time is refused — it is that a
// legitimate late one is KEPT, flagged, and not rewritten.

const assert = require('assert');

function mockRes() {
  var res = { statusCode: null, body: null };
  res.status = function (c) { res.statusCode = c; return res; };
  res.json = function (b) { res.body = b; return res; };
  return res;
}
function mockReq(action, payload) {
  return {
    method: 'POST',
    headers: { authorization: 'Bearer SEN-TEST-KEY', 'x-sd-auth': 'tok' },
    body: { action: action, resource: 'sen_visits', payload: payload || {} }
  };
}

let passed = 0;
async function test(name, fn) {
  try { await fn(); passed++; console.log('  ok - ' + name); }
  catch (e) { console.error('  FAIL - ' + name + '\n    ' + e.message); process.exitCode = 1; }
}

// The real module, so a vocabulary change breaks this suite rather than letting
// it pass against a shape the product does not have.
const CLOCK = require('./_lib/sen-evv-clock');

const CAREGIVER = 'cg-1';
function visitRow(data) {
  return [{ assigned_employee_id: CAREGIVER, data: data || {} }];
}

function loadHandler(opts) {
  opts = opts || {};
  const writes = [];
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
        return opts.noSession ? null
          : { employee_id: opts.employee_id || CAREGIVER,
              role: opts.role || 'caregiver' };
      }
    })
  };
  global.fetch = async function (url, init) {
    const u = String(url);
    const method = (init && init.method) || 'GET';
    if (method === 'POST') {
      writes.push(JSON.parse(init.body));
      return { ok: true, status: 200, json: async () => [{}] };
    }
    if (u.indexOf('sen_visits') !== -1) {
      const st = opts.readStatus || 200;
      return { ok: st === 200, status: st,
               json: async () => (opts.rows === undefined ? visitRow(opts.data) : opts.rows) };
    }
    return { ok: true, status: 200, json: async () => [] };
  };
  delete require.cache[require.resolve('./sd-data.js')];
  return { handler: require('./sd-data.js'), writes: writes };
}

const NOW_ISH = new Date().toISOString();
function minutesFromNow(m) {
  return new Date(Date.now() + m * 60000).toISOString();
}
function daysAgo(d) {
  return new Date(Date.now() - d * 86400000).toISOString();
}

async function main() {
  console.log('sen_visits EVV clock -- the seam between the endpoint and the '
    + 'module that was unreachable\n');

  await test('THE ARM THAT MATTERS: a legitimate clock-in is stored AS CLAIMED, '
    + 'not re-stamped with the server time -- re-stamping is what would make '
    + 'an offline replay precise, plausible and false',
    async () => {
      const { handler, writes } = loadHandler();
      const res = mockRes();
      const claimed = minutesFromNow(-3);
      await handler(mockReq('write', { id: 'V-1', clock_in_at: claimed }), res);
      assert.strictEqual(res.statusCode, 200, JSON.stringify(res.body));
      assert.strictEqual(writes.length, 1, 'expected one write');
      assert.strictEqual(writes[0].data.clock_in_at, claimed,
        'the stored clock time is not the one the caregiver sent');
    });

  await test('...and the server records its OWN observation beside it, which is '
    + 'the auditable fact an offline replay makes large and legitimate',
    async () => {
      const { handler, writes } = loadHandler();
      const res = mockRes();
      await handler(mockReq('write', { id: 'V-1', clock_in_at: minutesFromNow(-3) }), res);
      const d = writes[0].data;
      assert.ok(d.clock_in_received_at, 'no received_at stamp: ' + JSON.stringify(d));
      assert.strictEqual(typeof d.clock_in_skew_ms, 'number', JSON.stringify(d));
      assert.ok(d.clock_in_skew_ms < 0, 'a past claim should have negative skew');
    });

  await test('A TIME AHEAD OF THE SERVER IS REFUSED 400 with the module\'s own '
    + 'code -- a clock event cannot be stamped later than the moment it is '
    + 'received, so it is a wrong device clock or a forged value',
    async () => {
      const { handler, writes } = loadHandler();
      const res = mockRes();
      await handler(mockReq('write', { id: 'V-1', clock_in_at: minutesFromNow(30) }), res);
      assert.strictEqual(res.statusCode, 400, JSON.stringify(res.body));
      assert.strictEqual(res.body.error.code, 'CLOCK_IN_FUTURE');
      assert.strictEqual(writes.length, 0, 'a refused clock time was still written');
    });

  await test('AN UNREADABLE TIMESTAMP IS REFUSED, not stored -- an unreadable EVV '
    + 'time is not a time, and storing it produces a visit that looks verified',
    async () => {
      const { handler, writes } = loadHandler();
      const res = mockRes();
      await handler(mockReq('write', { id: 'V-1', clock_in_at: 'yesterday afternoon' }), res);
      assert.strictEqual(res.statusCode, 400, JSON.stringify(res.body));
      assert.strictEqual(res.body.error.code, 'CLOCK_UNPARSEABLE');
      assert.strictEqual(writes.length, 0);
    });

  await test('A CLOCK-OUT BEFORE ITS STORED CLOCK-IN IS REFUSED -- and the '
    + 'clock-in is only in the STORED row, so a payload-only comparison would '
    + 'never have seen it',
    async () => {
      const inAt = minutesFromNow(-60);
      const { handler, writes } = loadHandler({ data: { clock_in_at: inAt } });
      const res = mockRes();
      await handler(mockReq('write', { id: 'V-1', clock_out_at: minutesFromNow(-90) }), res);
      assert.strictEqual(res.statusCode, 400, JSON.stringify(res.body));
      assert.strictEqual(res.body.error.code, 'CLOCK_OUT_BEFORE_IN');
      assert.strictEqual(writes.length, 0);
    });

  await test('A LATE OFFLINE REPLAY IS STORED AND FLAGGED, never refused -- a '
    + 'past skew at any size is the offline path working, and the flag is '
    + 'STORED rather than only returned so an audit can find it later',
    async () => {
      const { handler, writes } = loadHandler();
      const res = mockRes();
      const claimed = daysAgo(30);
      await handler(mockReq('write', { id: 'V-1', clock_in_at: claimed }), res);
      assert.strictEqual(res.statusCode, 200, JSON.stringify(res.body));
      const d = writes[0].data;
      assert.strictEqual(d.clock_in_at, claimed, 'a late replay was rewritten');
      assert.ok(Array.isArray(d.clock_flags), 'no stored flag: ' + JSON.stringify(d));
      assert.ok(d.clock_flags.some((f) => f.code === 'LATE_REPLAY'),
        JSON.stringify(d.clock_flags));
    });

  await test('a NON-CLOCK write is untouched -- a scheduling edit goes through '
    + 'the same handler and must not gain stamps or flags',
    async () => {
      const { handler, writes } = loadHandler();
      const res = mockRes();
      await handler(mockReq('write', { id: 'V-1', services_notes: 'bathing, meds' }), res);
      assert.strictEqual(res.statusCode, 200, JSON.stringify(res.body));
      const d = writes[0].data;
      assert.strictEqual(d.services_notes, 'bathing, meds');
      assert.ok(!('clock_in_received_at' in d), JSON.stringify(d));
      assert.ok(!('clock_flags' in d), JSON.stringify(d));
    });

  await test('THE SCHEDULER GUARD IS UNCHANGED: a scheduler-tier caller still '
    + 'cannot set a clock field at all, so the new check did not open a door',
    async () => {
      const inAt = minutesFromNow(-60);
      const { handler, writes } = loadHandler({ role: 'owner', employee_id: 'boss',
                                                data: { clock_in_at: inAt } });
      const res = mockRes();
      await handler(mockReq('write', { id: 'V-1', clock_in_at: minutesFromNow(-5) }), res);
      assert.strictEqual(res.statusCode, 200, JSON.stringify(res.body));
      assert.strictEqual(writes[0].data.clock_in_at, inAt,
        'a scheduler forged a clock time');
    });

  // ══ THE CORRECTION PATH ══════════════════════════════════════════════════
  await test('A CORRECTION IS APPEND-ONLY: clock_in_at is UNCHANGED and an entry '
    + 'is appended, because a correction that overwrites destroys the evidence '
    + 'the record is',
    async () => {
      const original = minutesFromNow(-120);
      const { handler, writes } = loadHandler({ role: 'owner', employee_id: 'boss',
                                                data: { clock_in_at: original } });
      const res = mockRes();
      await handler(mockReq('propose_clock_correction', { id: 'V-1',
        correction: { field: 'clock_in_at', proposed_at: minutesFromNow(-110),
                      reason_code: Object.keys(CLOCK.CORRECTION_REASONS)[0] } }), res);
      assert.strictEqual(res.statusCode, 200, JSON.stringify(res.body));
      const d = writes[0].data;
      assert.strictEqual(d.clock_in_at, original,
        'the correction OVERWROTE the caregiver\'s recorded time');
      assert.strictEqual(d.clock_corrections.length, 1, JSON.stringify(d));
      assert.strictEqual(d.clock_corrections[0].original_at, original);
    });

  await test('...and the actor comes from the SESSION, never the payload -- a '
    + 'correction is attributed or it is not a correction',
    async () => {
      const { handler, writes } = loadHandler({ role: 'owner', employee_id: 'boss',
                                                data: { clock_in_at: minutesFromNow(-120) } });
      const res = mockRes();
      await handler(mockReq('propose_clock_correction', { id: 'V-1',
        correction: { field: 'clock_in_at', proposed_at: minutesFromNow(-110),
                      reason_code: Object.keys(CLOCK.CORRECTION_REASONS)[0],
                      proposed_by: 'somebody-else' } }), res);
      assert.strictEqual(writes[0].data.clock_corrections[0].proposed_by, 'boss',
        'the payload chose who filed the correction');
    });

  await test('A CAREGIVER CANNOT CORRECT THEIR OWN CLOCK -- correcting your own '
    + 'time with nobody else involved is the unverified self-assertion EVV '
    + 'exists to stop',
    async () => {
      const { handler, writes } = loadHandler({ role: 'caregiver',
                                                data: { clock_in_at: minutesFromNow(-120) } });
      const res = mockRes();
      await handler(mockReq('propose_clock_correction', { id: 'V-1',
        correction: { field: 'clock_in_at', proposed_at: minutesFromNow(-110),
                      reason_code: Object.keys(CLOCK.CORRECTION_REASONS)[0] } }), res);
      assert.strictEqual(res.statusCode, 403, JSON.stringify(res.body));
      assert.strictEqual(writes.length, 0);
    });

  await test('AN UNKNOWN REASON CODE IS REFUSED -- the closed vocabulary is the '
    + 'reason the categories can be counted at audit',
    async () => {
      const { handler, writes } = loadHandler({ role: 'owner', employee_id: 'boss',
                                                data: { clock_in_at: minutesFromNow(-120) } });
      const res = mockRes();
      await handler(mockReq('propose_clock_correction', { id: 'V-1',
        correction: { field: 'clock_in_at', proposed_at: minutesFromNow(-110),
                      reason_code: 'because' } }), res);
      assert.strictEqual(res.statusCode, 400, JSON.stringify(res.body));
      assert.strictEqual(res.body.error.code, 'BAD_REASON_CODE');
      assert.strictEqual(writes.length, 0);
    });

  await test('A CORRECTION CANNOT CREATE THE VISIT IT CORRECTS -- an upsert here '
    + 'would let a correction invent its own subject',
    async () => {
      const { handler, writes } = loadHandler({ role: 'owner', employee_id: 'boss',
                                                rows: [] });
      const res = mockRes();
      await handler(mockReq('propose_clock_correction', { id: 'V-NOPE',
        correction: { field: 'clock_in_at', proposed_at: minutesFromNow(-110),
                      reason_code: Object.keys(CLOCK.CORRECTION_REASONS)[0] } }), res);
      assert.strictEqual(res.statusCode, 404, JSON.stringify(res.body));
      assert.strictEqual(writes.length, 0);
    });

  await test('IS IT REACHABLE: propose_clock_correction is DECLARED in the '
    + 'resource registry, or the dispatcher answers 400 before this branch is '
    + 'ever entered -- which is how `tombstones` shipped unreachable',
    async () => {
      const reg = require('./_resources/sairnsenior.js');
      assert.ok((reg.extraActions.sen_visits || []).indexOf('propose_clock_correction') !== -1,
        'implemented and undeclared: ' + JSON.stringify(reg.extraActions.sen_visits));
    });

  // ══ THE READ ═════════════════════════════════════════════════════════════
  await test('A CORRECTED VISIT READS BACK WITH BOTH NUMBERS -- a screen showing '
    + 'only the corrected value has quietly become the overwrite this module '
    + 'exists to avoid',
    async () => {
      const original = minutesFromNow(-120);
      const proposed = minutesFromNow(-110);
      const { handler } = loadHandler({ role: 'owner', employee_id: 'boss',
        rows: [{ visit_id: 'V-1', assigned_employee_id: CAREGIVER,
                 data: { clock_in_at: original,
                         clock_corrections: [{ field: 'clock_in_at',
                                               original_at: original,
                                               proposed_at: proposed }] } }] });
      const res = mockRes();
      await handler(mockReq('read', {}), res);
      assert.strictEqual(res.statusCode, 200, JSON.stringify(res.body));
      const v = res.body.data[0];
      assert.strictEqual(v.clock_in_at, original, 'the raw field was replaced');
      assert.ok(v.effective_clock && v.effective_clock.clock_in_at, JSON.stringify(v));
      assert.strictEqual(v.effective_clock.clock_in_at.value, proposed);
      assert.strictEqual(v.effective_clock.clock_in_at.original_at, original);
      assert.strictEqual(v.effective_clock.clock_in_at.corrected, true);
    });

  await test('...and an UNCORRECTED visit gains no effective_clock key at all -- '
    + 'a key on every row whether or not it says anything is a key a reader '
    + 'stops reading',
    async () => {
      const { handler } = loadHandler({ role: 'owner', employee_id: 'boss',
        rows: [{ visit_id: 'V-2', assigned_employee_id: CAREGIVER,
                 data: { clock_in_at: minutesFromNow(-30) } }] });
      const res = mockRes();
      await handler(mockReq('read', {}), res);
      assert.ok(!('effective_clock' in res.body.data[0]),
        JSON.stringify(res.body.data[0]));
    });

  console.log('\n' + passed + ' assertion(s) passed');
  if (process.exitCode) console.log('SOME ASSERTIONS FAILED');
  else console.log('ALL SEN EVV-CLOCK SEAM ASSERTIONS PASS');
}

main();
