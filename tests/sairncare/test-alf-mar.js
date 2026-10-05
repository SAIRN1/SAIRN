// REQUIREMENT: the MAR is reachable by clinical roles only, and a med_aide may
//   LOG an administration for a resident assigned to them while never creating
//   a medication order, a reconciliation or an assessment refusal -- those are
//   clinical decisions and logging a dose is not
//
// Isolated test of the alf_mar MAR gate in api/sd-data.js. Runs the REAL
// handler (not a reimplementation) with mocked auth/license/fetch.
'use strict';
const path = require('path');
const ROOT = path.join(__dirname, '..', '..');

process.env.SUPABASE_URL = 'https://fake.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = 'fake-service-key';

const licenseMod = require(path.join(ROOT, 'api/_lib/license.js'));
licenseMod.validateLicenseKey = async () => ({
  valid: true, active: true, license_hash: 'HASH1', stripe_subscription_id: 'sub_1', trial_ends_at: null
});

const authMod = require(path.join(ROOT, 'api/_lib/auth.js'));
authMod.tokenFromRequest = (req) => req.headers['x-test-token'] || null;
authMod.verifySessionToken = (token, licHash, expectedApp) => {
  if (!token) return null;
  // ── AN ABSENT expectedApp IS LEGITIMATE; A WRONG ONE IS STILL FATAL ──────
  // This stub threw on ANY expectedApp other than 'sairncare', INCLUDING
  // `undefined`, and that is what made this file 0 passed / 20 failed from
  // c8b5e5b1 until now -- the whole MAR gate, unverified, for over a week.
  //
  // THE STUB WAS STRICTER THAN THE FUNCTION IT STANDS IN FOR, which is the
  // defect. `api/_lib/auth.js:604` is `if (expectedApp && payload.app !==
  // expectedApp) return null;` -- the third argument is OPTIONAL and omitting
  // it asserts nothing about the app while still checking the signature, the
  // `typ` (so a pre-auth token cannot pass), the role-in-app, the expiry and
  // the licence binding. `api/sd-data.js:1387`'s active-credential PRE-GATE
  // omits it DELIBERATELY: the only use for the app at that point is choosing
  // which `*_employee_auth` table to ask, and re-deriving each of 132
  // branches' expected app at the entry point would be a second copy of a
  // fact spread over the whole file.
  //
  // SO THE REFUSAL THIS STUB MODELLED COULD NEVER HAPPEN IN PRODUCTION. Every
  // arm below reported 502 "Upstream connection error" -- the handler catching
  // the stub's own throw -- and a suite failing on its own mock is not
  // evidence about the subject.
  //
  // THE GUARD IS KEPT AND IS THE POINT. A branch gate that quietly DROPPED its
  // app scope, or passed the wrong app, is still fatal here, because that is a
  // real defect and this stub was written to catch it. Only the absent case is
  // admitted. Shape copied from the two suites that were already green under
  // the same pre-gate -- `api/_lib/dnt-rollup-endpoint.test.js:49` and
  // `api/_lib/law-trust-reconcile-endpoint.test.js` -- rather than invented.
  if (expectedApp === undefined) return JSON.parse(token);
  if (expectedApp !== 'sairncare') throw new Error('expected app scope not sairncare: ' + expectedApp);
  return JSON.parse(token);
};

// Fixture: RES-1 assigned to MA-1, RES-2 assigned to MA-2, and RES-3 assigned
// to NOBODY. The unassigned case is not decoration -- it is the real state of a
// resident between staffing changes, and it is the only fixture under which the
// write path's "never trust a client-supplied assigned_employee_id" rule can be
// observed at all. With every resident assigned, a gate that fell back to the
// client's value would look identical to one that did not
// (tests/sairncare_fault_probe.py arm 7 found exactly that).
const RESIDENTS = { 'RES-1': 'MA-1', 'RES-2': 'MA-2', 'RES-3': null };
let MAR_ROWS = []; // {entry_id, resident_id, assigned_employee_id, entry_type, data}

// ── THE WITNESS LOCK'S STORE (added 2026-10-05) ───────────────────────────
// A controlled-substance `count` is gated by api/sairncare-witness.js as of
// 2026-09-30: the write is refused unless a SECOND person has confirmed that
// exact record on the server. This suite predates the lock, so its count arm
// asserted 200 for a count carrying only a CLIENT-SUPPLIED `witness_id` --
// which is precisely what the lock exists to refuse. Left as it was, that arm
// would have pressured somebody into weakening a controlled-substance control
// to make a suite green.
//
// SO THE FIXTURE SATISFIES THE LOCK RATHER THAN THE ARM BEING DOWNGRADED, the
// way api/sd-data-alf-mar-actor-identity.test.js already does. The arm goes on
// testing what it was written to test -- med_aide scope-of-practice on a count
// -- and a NEW arm beside it drives the refusal, so this suite can also tell
// if the lock is ever removed.
//
// THE content_hash IS COMPUTED BY THE REAL FUNCTION, imported rather than
// re-implemented. A hand-rolled canonical form here would bind the arm to a
// hash the endpoint does not actually use, and it would pass.
const alfWitness = require(path.join(ROOT, 'api/sairncare-witness.js'));
// A DIFFERENT person from any caller below. A self-witnessed count is refused,
// so the witness cannot be MA-1 -- that is the lock working, not a fixture
// convenience.
const WITNESS_EMP = 'EMP-NUR-WITNESS';
// `payload` null means NO confirmation exists on the server, which is the
// default state and the one the refusal arm runs in.
const witnessState = { payload: null, spent: false };

global.fetch = async (url, opts) => {
  opts = opts || {};
  const method = opts.method || 'GET';

  // alf_clients assignment lookup (for the write path's live look-up)
  const clientLookup = url.match(/alf_clients\?license_hash=eq\.[^&]+&client_id=eq\.([^&]+)&select=assigned_employee_id/);
  if (method === 'GET' && clientLookup) {
    const id = decodeURIComponent(clientLookup[1]);
    const assignee = RESIDENTS[id];
    return { ok: true, status: 200, json: async () => (assignee !== undefined ? [{ assigned_employee_id: assignee }] : []) };
  }

  // ── requireWitness RE-READS THE ATTESTER AT WRITE TIME -- the settling step
  // -- so this must answer for the WITNESS as well as the caller. A mock that
  // knew only the caller would fail every count arm with
  // WITNESS_NO_LONGER_ACTIVE, and that failure would look like the gate
  // working. Same trap the sibling suite's comment names.
  if (/_employee_auth\?/.test(url)) {
    const m = url.match(/employee_id=eq\.([^&]+)/);
    const forId = m ? decodeURIComponent(m[1]) : null;
    if (forId === WITNESS_EMP) {
      return { ok: true, status: 200, json: async () => [{ license_hash: 'HASH1', employee_id: WITNESS_EMP, role: 'nursing', active: true }] };
    }
    return { ok: true, status: 200, json: async () => [{ license_hash: 'HASH1', employee_id: forId, role: 'med_aide', active: true }] };
  }

  // No per-facility witness policy row: the module's defaults apply.
  if (/sairncare_witness_policy/.test(url)) {
    return { ok: true, status: 200, json: async () => [] };
  }

  if (/sairncare_witness_tokens/.test(url)) {
    // Spending the confirmation. A second PATCH finds nothing, which is how the
    // real store makes a confirmation single-use.
    if (method === 'PATCH') {
      if (witnessState.spent) return { ok: true, status: 200, json: async () => [] };
      witnessState.spent = true;
      return { ok: true, status: 200, json: async () => [{ id: 'tok-1' }] };
    }
    if (!witnessState.payload) return { ok: true, status: 200, json: async () => [] };
    return { ok: true, status: 200, json: async () => [{
      id: 'tok-1',
      content_hash: alfWitness.contentHash('alf_mar', witnessState.payload),
      witness_employee_id: WITNESS_EMP,
      countersign_employee_id: null,
      spent_at: witnessState.spent ? '2026-10-05T00:00:00Z' : null,
      expires_at: new Date(Date.now() + 600000).toISOString()
    }] };
  }

  // alf_mar facility-wide read
  if (method === 'GET' && /alf_mar\?license_hash=eq\.[^&]+&select=entry_id,resident_id,assigned_employee_id,entry_type,data/.test(url)) {
    return { ok: true, status: 200, json: async () => MAR_ROWS.map((r) => ({ entry_id: r.entry_id, resident_id: r.resident_id, assigned_employee_id: r.assigned_employee_id, entry_type: r.entry_type, data: r.data })) };
  }

  // alf_mar atomic check-and-insert RPC (2026-09-21 fix for hover_log #314).
  // Simulates public.alf_check_and_insert_mar_entry()'s real behaviour: an
  // append-only entry_type reusing an existing entry_id raises
  // ALREADY_RECORDED (surfaced by PostgREST as a 400 carrying that string in
  // the message, same as every other raised plpgsql exception on this
  // platform -- see how the disbursement RPC's 400 body is parsed);
  // medication_order upserts in place.
  if (method === 'POST' && /\/rpc\/alf_check_and_insert_mar_entry$/.test(url)) {
    const body = JSON.parse(opts.body);
    const entryId = body.p_entry_id;
    const idx = MAR_ROWS.findIndex((r) => r.entry_id === entryId);
    if (idx !== -1 && body.p_entry_type !== 'medication_order') {
      return {
        ok: false, status: 400,
        text: async () => JSON.stringify({ message: 'ALREADY_RECORDED: entry ' + entryId + ' has already been recorded and cannot be overwritten' })
      };
    }
    const row = {
      id: 'mar-row-' + entryId, entry_id: entryId, resident_id: body.p_resident_id,
      assigned_employee_id: body.p_assigned_employee_id, entry_type: body.p_entry_type, data: body.p_data
    };
    if (idx === -1) MAR_ROWS.push(row); else MAR_ROWS[idx] = row;
    return { ok: true, status: 200, json: async () => [row] };
  }

  throw new Error('Unmocked fetch: ' + method + ' ' + url);
};

delete require.cache[require.resolve(path.join(ROOT, 'api/sd-data.js'))];
const handler = require(path.join(ROOT, 'api/sd-data.js'));

function fakeRes() {
  const r = { statusCode: null, body: null };
  r.status = (c) => { r.statusCode = c; return r; };
  r.json = (b) => { r.body = b; return r; };
  return r;
}
async function call(role, employeeId, action, payload, witnessToken) {
  const headers = { authorization: 'Bearer testkey', 'x-test-token': JSON.stringify({ role, employee_id: employeeId }) };
  // Only set when an arm is presenting a server-minted confirmation. Absent on
  // every other arm, so no arm accidentally inherits a witnessed state.
  if (witnessToken) headers['x-alf-witness'] = witnessToken;
  const req = { method: 'POST', headers: headers, body: { action, resource: 'alf_mar', payload } };
  const res = fakeRes();
  await handler(req, res);
  return res;
}

let pass = 0, fail = 0;
async function check(name, fn) {
  try { await fn(); pass++; console.log('PASS ' + name); }
  catch (e) { fail++; console.log('FAIL ' + name + ' -- ' + e.message); }
}
function assertEq(actual, expected, msg) {
  if (JSON.stringify(actual) !== JSON.stringify(expected)) {
    throw new Error((msg || 'mismatch') + ': expected ' + JSON.stringify(expected) + ' got ' + JSON.stringify(actual));
  }
}

(async () => {
  await check('billing has zero MAR access: read is 403', async () => {
    const res = await call('billing', 'EMP-BILL', 'read', null);
    assertEq(res.statusCode, 403);
  });
  await check('caregiver has zero MAR access: write is 403', async () => {
    const res = await call('caregiver', 'CG-1', 'write', { id: 'X1', resident_id: 'RES-1', entry_type: 'administration' });
    assertEq(res.statusCode, 403);
  });
  await check('activities has zero MAR access: read is 403', async () => {
    const res = await call('activities', 'EMP-ACT', 'read', null);
    assertEq(res.statusCode, 403);
  });

  await check('owner can create a medication_order for any resident', async () => {
    const res = await call('owner', 'EMP-OWN', 'write', { id: 'MED-1', resident_id: 'RES-1', entry_type: 'medication_order', name: 'Metformin', dose: '500mg' });
    assertEq(res.statusCode, 200);
  });
  await check('nursing can create a reconciliation entry', async () => {
    const res = await call('nursing', 'EMP-NUR', 'write', { id: 'REC-1', resident_id: 'RES-1', entry_type: 'reconciliation', type: 'admission', summary: 'no discrepancies' });
    assertEq(res.statusCode, 200);
  });
  await check('nursing can create an assessment_refusal entry', async () => {
    const res = await call('nursing', 'EMP-NUR', 'write', { id: 'REF-1', resident_id: 'RES-1', entry_type: 'assessment_refusal', legal_rep_notified: true });
    assertEq(res.statusCode, 200);
  });

  await check('med_aide CANNOT create a medication_order (clinical-decision type)', async () => {
    const res = await call('med_aide', 'MA-1', 'write', { id: 'MED-2', resident_id: 'RES-1', entry_type: 'medication_order', name: 'Lisinopril' });
    assertEq(res.statusCode, 403);
  });
  await check('med_aide CANNOT create a reconciliation entry', async () => {
    const res = await call('med_aide', 'MA-1', 'write', { id: 'REC-2', resident_id: 'RES-1', entry_type: 'reconciliation' });
    assertEq(res.statusCode, 403);
  });
  await check('med_aide CANNOT create an assessment_refusal entry', async () => {
    const res = await call('med_aide', 'MA-1', 'write', { id: 'REF-2', resident_id: 'RES-1', entry_type: 'assessment_refusal' });
    assertEq(res.statusCode, 403);
  });

  await check('med_aide CAN log administration for their own-assigned resident (RES-1)', async () => {
    const res = await call('med_aide', 'MA-1', 'write', { id: 'ADM-1', resident_id: 'RES-1', entry_type: 'administration', medication_id: 'MED-1', status: 'given' });
    assertEq(res.statusCode, 200);
  });
  await check('med_aide CANNOT log administration for a resident assigned to someone else (RES-2)', async () => {
    const res = await call('med_aide', 'MA-1', 'write', { id: 'ADM-2', resident_id: 'RES-2', entry_type: 'administration', medication_id: 'MED-1', status: 'given' });
    assertEq(res.statusCode, 403);
  });
  // ── THE COUNT IS WITNESS-LOCKED. Two arms, and the refusal comes first so a
  // future reader sees the control before the happy path (added 2026-10-05).
  await check('a controlled-substance count with only a CLIENT-SUPPLIED witness_id is REFUSED -- 403 WITNESS_REQUIRED', async () => {
    // witnessState.payload is null: nothing is confirmed on the server. A
    // `witness_id` in the payload names a second person and PROVES nothing --
    // the caller typed it. This is the arm the old version of this file
    // asserted 200 for.
    const res = await call('med_aide', 'MA-1', 'write', { id: 'CNT-0', resident_id: 'RES-1', entry_type: 'count', medication_id: 'MED-1', witness_id: 'EMP-NUR', count_value: 30 });
    assertEq(res.statusCode, 403);
    assertEq(res.body.error.code, 'WITNESS_REQUIRED');
    // AND NOTHING WAS STORED. A refusal that still files the row is the worse
    // failure, and on an append-only MAR with no delete verb it is permanent.
    assertEq(MAR_ROWS.some((r) => r.entry_id === 'CNT-0'), false);
  });
  await check('med_aide CAN log a controlled-substance count for their own-assigned resident, WITH a server-recorded second signature', async () => {
    const payload = { id: 'CNT-1', resident_id: 'RES-1', entry_type: 'count', medication_id: 'MED-1', witness_id: WITNESS_EMP, count_value: 30 };
    // The confirmation covers THIS EXACT RECORD -- the store hashes the same
    // payload with the module's own contentHash, so changing any field after
    // confirming invalidates it. That binding is the lock, not the header.
    witnessState.payload = payload;
    witnessState.spent = false;
    const res = await call('med_aide', 'MA-1', 'write', payload, 'confirmation-token-1');
    assertEq(res.statusCode, 200);
    witnessState.payload = null;
  });

  await check('append-only integrity: reusing an administration id is 409, not silently overwritten', async () => {
    const res = await call('med_aide', 'MA-1', 'write', { id: 'ADM-1', resident_id: 'RES-1', entry_type: 'administration', status: 'refused' });
    assertEq(res.statusCode, 409);
    assertEq(res.body.error.code, 'ALREADY_RECORDED');
  });
  await check('medication_order IS editable in place (same id, no 409)', async () => {
    const res = await call('owner', 'EMP-OWN', 'write', { id: 'MED-1', resident_id: 'RES-1', entry_type: 'medication_order', name: 'Metformin', dose: '1000mg', discontinued: false });
    assertEq(res.statusCode, 200);
  });

  await check('an UNRECOGNISED entry_type is refused (400) and nothing is stored', async () => {
    // A typo'd entry_type stored silently is a MAR row no panel filters on and
    // no report counts -- present in the table, absent from the record. The
    // whitelist could be disabled with no suite noticing until this arm existed.
    const before = MAR_ROWS.length;
    const res = await call('owner', 'EMP-OWN', 'write', { id: 'BAD-1', resident_id: 'RES-1', entry_type: 'administrtion', status: 'given' });
    assertEq(res.statusCode, 400);
    assertEq(MAR_ROWS.length, before, 'a rejected entry_type must not reach the table');
  });

  await check('an UNASSIGNED resident cannot be claimed by a med_aide who supplies their own id in the payload', async () => {
    // The write path looks the assignment up live and says so in a comment.
    // This is the only arm that can tell that apart from trusting the caller:
    // RES-3 has no assignee, so a fallback to payload.assigned_employee_id
    // would let MA-1 assign the resident to themselves mid-write.
    const res = await call('med_aide', 'MA-1', 'write', { id: 'ADM-3', resident_id: 'RES-3', entry_type: 'administration', assigned_employee_id: 'MA-1', status: 'given' });
    assertEq(res.statusCode, 403);
  });

  await check('unknown resident_id is 400', async () => {
    const res = await call('owner', 'EMP-OWN', 'write', { id: 'ADM-99', resident_id: 'RES-NOPE', entry_type: 'administration' });
    assertEq(res.statusCode, 400);
  });

  await check('owner read sees ALL entry types across all residents (facility-wide)', async () => {
    const res = await call('owner', 'EMP-OWN', 'read', null);
    assertEq(res.statusCode, 200);
    const types = res.body.data.map((d) => d.entry_type).sort();
    assertEq(types.indexOf('medication_order') !== -1, true);
    assertEq(types.indexOf('reconciliation') !== -1, true);
    assertEq(types.indexOf('assessment_refusal') !== -1, true);
    assertEq(types.indexOf('administration') !== -1, true);
    assertEq(types.indexOf('count') !== -1, true);
  });
  await check('med_aide read is scoped to their own-assigned resident only', async () => {
    const res = await call('med_aide', 'MA-1', 'read', null);
    const residentIds = res.body.data.map((d) => d.resident_id);
    assertEq(residentIds.every((id) => id === 'RES-1'), true, 'every entry must belong to RES-1');
  });
  await check('a different med_aide (MA-2, RES-2 assignee, zero entries yet) sees nothing', async () => {
    const res = await call('med_aide', 'MA-2', 'read', null);
    assertEq(res.body.data.length, 0);
  });

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
