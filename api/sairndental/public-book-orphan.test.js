// api/sairndental/public-book-orphan.test.js
// Plain node:assert, matching api/'s zero-npm-dependency convention.
// Run: node api/sairndental/public-book-orphan.test.js
//
// THE DEFECT. The patient row was written BEFORE the appointment. Every
// booking that then failed left an ORPHAN PATIENT RECORD -- and the most
// common failure is the 409 slot race two people hit on purpose by clicking
// the same popular time.
//
// This is an ANONYMOUS, UNAUTHENTICATED endpoint, so anyone able to load the
// booking page could mint unbounded dnt_patients rows carrying name, date of
// birth, phone and email just by racing a slot. AND THE PRACTICE CANNOT DELETE
// THEM: dnt_patients has no delete grant (revoked platform-wide by
// sql/unused_delete_grant_revoke_2026-08-24.sql). Permanent PHI debris in a
// dental record system.
//
// Cleaning up afterwards was therefore never available as a fix -- there is no
// delete to roll back with. The order is reversed instead: claim the SLOT
// first, write the patient only once it is secured.
//
// AND THE SECOND DEFECT, which the open-work row did not name: the patient
// write was a bare `await fetch(...)` whose result was never checked. If it
// failed, patientId still pointed at a row that did not exist and the
// appointment was written referencing a PHANTOM PATIENT, reported as a clean
// 200. The appointment now also carries the caller's name and phone so it
// stays actionable, and the response says which happened.
//
// These assertions drive the real handler with a stubbed fetch. They record
// the ORDER of the writes, which is the whole property at issue.

const assert = require('assert');
const path = require('path');
const Module = require('module');

const LIB = path.join(__dirname, '..', '_lib', 'dental-public.js');

// Stub resolveSlug so no network or env is needed. Everything else in the
// handler is exercised for real.
const origLoad = Module._load;
Module._load = function (request, parent, isMain) {
  const resolved = (() => { try { return Module._resolveFilename(request, parent); } catch (e) { return request; } })();
  if (resolved === LIB) {
    const real = origLoad.apply(this, arguments);
    return Object.assign({}, real, {
      resolveSlug: async () => 'LICENSE-HASH-TEST',
      checkAndIncrementRateLimit: async () => ({ allowed: true, count: 1 })
    });
  }
  return origLoad.apply(this, arguments);
};
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://example.invalid';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'test-key';
const handler = require('./public-book.js');
Module._load = origLoad;

function mockRes() {
  const res = { statusCode: null, body: null };
  res.status = (c) => { res.statusCode = c; return res; };
  res.json = (p) => { res.body = p; return res; };
  res.setHeader = () => res;
  res.end = () => res;
  return res;
}
const REQ = () => ({
  method: 'POST', headers: {},
  body: {
    slug: 'test-practice',
    patient: { name: 'Jane Doe', dob: '1990-01-01', phone: '555-0100', email: 'j@example.com' },
    provider_id: 'PV-1', procedure_type_id: 'PC-1', start_time: '2026-08-13T14:00:00.000Z'
  }
});

// A fetch stub that records every write, in order, and lets a test decide what
// the appointment insert and the patient insert return.
function stubFetch(opts) {
  const calls = [];
  global.fetch = async (url, init) => {
    const u = String(url);
    const method = (init && init.method) || 'GET';
    if (method === 'POST') calls.push(u.split('?')[0].split('/').pop());
    const ok = (body, status) => ({
      ok: (status || 200) < 400, status: status || 200,
      json: async () => body, text: async () => JSON.stringify(body)
    });
    if (u.includes('dnt_procedure_types')) return ok([{ data: { default_length_minutes: 30 } }]);
    if (u.includes('dnt_providers')) return ok([{ data: { operatory_id: 'OP-1' } }]);
    if (u.includes('dnt_patients') && method === 'GET') return ok(opts.existingPatients || []);
    if (u.includes('dnt_patients') && method === 'POST') return ok({}, opts.patientStatus || 200);
    if (u.includes('dnt_appointments')) return ok(opts.apptBody || [{}], opts.apptStatus || 200);
    if (u.includes('dnt_settings')) return ok([]);
    return ok([]);
  };
  return calls;
}

let passed = 0;
async function test(name, fn) {
  try { await fn(); passed++; console.log('  ok - ' + name); }
  catch (err) { console.error('  FAIL - ' + name + '\n    ' + err.message); process.exitCode = 1; }
}

async function main() {
  console.log('api/sairndental/public-book.js -- no orphan patient, and no phantom one either');

  // ── THE ORPHAN, WHICH IS THE WHOLE POINT ──────────────────────────────
  await test('a 409 slot race writes NO patient row at all', async () => {
    const calls = stubFetch({ apptStatus: 409 });
    const res = mockRes();
    await handler(REQ(), res);
    assert.strictEqual(res.statusCode, 409, 'still reports the race as 409');
    assert.strictEqual(res.body.error.code, 'SLOT_TAKEN');
    assert.ok(!calls.includes('dnt_patients'),
      'a patient row was written on a failed booking -- that is the orphan: ' + JSON.stringify(calls));
  });

  await test('a 502 on the appointment insert writes NO patient row either', async () => {
    const calls = stubFetch({ apptStatus: 500 });
    const res = mockRes();
    await handler(REQ(), res);
    assert.strictEqual(res.statusCode, 502);
    assert.ok(!calls.includes('dnt_patients'), 'orphan on the non-race failure path: ' + JSON.stringify(calls));
  });

  // ── THE ORDER, asserted directly rather than inferred ─────────────────
  await test('on success the SLOT is claimed first and the patient written second',
    async () => {
      const calls = stubFetch({});
      const res = mockRes();
      await handler(REQ(), res);
      assert.strictEqual(res.statusCode, 200);
      const a = calls.indexOf('dnt_appointments'), p = calls.indexOf('dnt_patients');
      assert.ok(a >= 0 && p >= 0, 'both writes should happen: ' + JSON.stringify(calls));
      assert.ok(a < p, 'the patient was written BEFORE the slot was secured: ' + JSON.stringify(calls));
    });

  await test('an EXISTING patient is not rewritten at all', async () => {
    const calls = stubFetch({
      existingPatients: [{ patient_id: 'PT-EXISTING',
        data: { name: 'Jane Doe', dob: '1990-01-01', phone: '555-0100' } }]
    });
    const res = mockRes();
    await handler(REQ(), res);
    assert.strictEqual(res.statusCode, 200);
    assert.ok(!calls.includes('dnt_patients'), 'matched patient should need no write: ' + JSON.stringify(calls));
    assert.strictEqual(res.body.patient_record, 'saved');
  });

  // ── THE PHANTOM PATIENT: the unchecked write the open-work row missed ──
  await test('a failed patient write does NOT report a complete record', async () => {
    stubFetch({ patientStatus: 500 });
    const res = mockRes();
    await handler(REQ(), res);
    // The booking is real: the slot is taken. Telling the visitor it failed
    // would send them to book a second time into a slot they already hold.
    assert.strictEqual(res.statusCode, 200, 'the booking itself succeeded and must be reported as such');
    assert.strictEqual(res.body.ok, true);
    assert.strictEqual(res.body.patient_record, 'not_saved',
      'a phantom patient_id was reported as a complete success');
  });

  await test('and a successful one says so', async () => {
    stubFetch({});
    const res = mockRes();
    await handler(REQ(), res);
    assert.strictEqual(res.body.patient_record, 'saved');
  });

  // THE LOUD LOG IS THE ONLY SIGNAL OPS GETS. A visitor is deliberately told
  // the booking succeeded (it did), so if this line goes quiet the phantom
  // patient_id is invisible to everyone. Asserted behaviourally -- the first
  // version of this suite had no assertion at all here and a negative control
  // that wrapped the log in `if (false)` passed clean.
  await test('a phantom patient_id is logged loudly, naming both ids', async () => {
    stubFetch({ patientStatus: 500 });
    const seen = [];
    const orig = console.error;
    console.error = (...a) => { seen.push(a.map(String).join(' ')); };
    try { await handler(REQ(), mockRes()); } finally { console.error = orig; }
    const hit = seen.find((l) => /patient record was NOT/.test(l));
    assert.ok(hit, 'nothing was logged for a phantom patient_id: ' + JSON.stringify(seen));
    assert.ok(/AP-/.test(hit) && /PT-/.test(hit),
      'the log must name BOTH ids or it cannot be acted on: ' + hit);
  });

  // ── THE APPOINTMENT STAYS ACTIONABLE ON ITS OWN ───────────────────────
  await test('the appointment carries the caller name and phone, so a phantom patient_id is survivable',
    async () => {
      let apptBody = null;
      const origStub = stubFetch({});
      const inner = global.fetch;
      global.fetch = async (url, init) => {
        if (String(url).includes('dnt_appointments') && init && init.method === 'POST') {
          apptBody = JSON.parse(init.body);
        }
        return inner(url, init);
      };
      const res = mockRes();
      await handler(REQ(), res);
      assert.ok(apptBody, 'appointment insert should have happened');
      assert.strictEqual(apptBody.data.patient_name, 'Jane Doe');
      assert.strictEqual(apptBody.data.patient_phone, '555-0100');
      assert.ok(origStub.length >= 1);
    });

  // ── the source-level guarantee, so a reorder cannot silently come back ─
  await test('the patient insert appears AFTER the appointment insert in the source', async () => {
    const fs = require('fs');
    const src = fs.readFileSync(path.join(__dirname, 'public-book.js'), 'utf8');
    const code = src.split('\n').filter((l) => !/^\s*\/\//.test(l)).join('\n');
    const appt = code.indexOf("rest('dnt_appointments");
    const pat = code.indexOf("rest('dnt_patients?on_conflict");
    assert.ok(appt >= 0 && pat >= 0, 'both inserts should be present');
    assert.ok(appt < pat, 'the patient insert moved back above the appointment insert');
    assert.ok(/patientWritten = patientRes\.ok/.test(code), 'the patient write must be checked');
  });

  console.log(passed + ' passed');
}

main();
