// api/sd-data-alf-mar-actor-identity.test.js
//
// REQUIREMENT: on an alf_mar entry, the field naming WHO DID IT is set from the
//   verified session and is never accepted from the caller.
//
// Run:  node api/sd-data-alf-mar-actor-identity.test.js
//
// ── THE DEFECT THIS PINS ──────────────────────────────────────────────────
// alf_mar's write builds its blob with
//
//     storedBlob(payload, ['id','resident_id','entry_type',
//                          'assigned_employee_id','created_at'])
//
// and storedBlob is a DENY-LIST: it copies the payload and deletes only the keys
// named. `reviewed_by` on that same blob is stamped server-side three lines
// later. `administered_by` was not -- it was whatever the request said.
//
// sairncare.html sends `administered_by: alfSession.employee_id`, so the honest
// client always sends its own id. That is a property of the client, and the
// client is the thing an attacker replaces. ANY AUTHENTICATED EMPLOYEE COULD
// RECORD A MEDICATION ADMINISTRATION AGAINST ANOTHER EMPLOYEE'S NAME.
//
// ── AND IT WAS NOT ONE FIELD, IT WAS FOUR ─────────────────────────────────
// Reading all four MAR writers in sairncare.html, every entry type carries its
// own actor key and all four are `(alfSession&&alfSession.employee_id)||''`:
//
//     administration        administered_by
//     count                 counted_by
//     reconciliation        reconciled_by
//     assessment_refusal    documented_by
//
// Fixing only the one that was reported would have left three identical holes
// on the same resource, which is why the server now owns a MAP rather than a
// field.
//
// ── WHAT IS DELIBERATELY NOT CHANGED HERE ─────────────────────────────────
// `witness_id` on a controlled-substance count names a SECOND person who is BY
// DEFINITION not the caller, so it cannot be stamped from the session and is
// still caller-supplied. That SAIRNcare has no server-side witness verification
// at all -- SAIRNvet has one, api/sv-witness.js, with a witness token -- is a
// real and separate finding, registered rather than folded in here. An arm below
// pins that witness_id SURVIVES, so this change cannot be mistaken for having
// addressed it.
//
// ── THE ARMS ASSERT BOTH HOPS ─────────────────────────────────────────────
// Every write arm checks the RPC body that goes to PostgREST *and* the JSON the
// client receives back. On 2026-09-28 alf_incidents shipped with a correct
// column and a read mapper that spread the blob over it, and nine green arms
// asserting only the outbound request could not see it.

'use strict';

process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET
  || ['alf', 'mar', 'actor', 'fixture'].join('-');
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://test.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'test-key';

const assert = require('assert');
const { signSessionToken } = require('./_lib/auth');

const HASH = 'alf-mar-actor-hash';
const APP = 'sairncare';
const ME = 'emp-nurse-1';
const VICTIM = 'emp-someone-else';
const RESIDENT = 'res-1';

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

// Same contract as the sibling alf_ suites: eq-clauses applied, `select=`
// honoured, routing by table so one fixture set cannot leak across resources,
// and every unfaithfulness in the direction that returns MORE rows and fails
// the content assertion louder.
//
// THE RPC IS ANSWERED LIKE THE REAL FUNCTION, not like a table insert.
// alf_check_and_insert_mar_entry returns a ROW SHAPE -- entry_id, resident_id,
// entry_type, assigned_employee_id, data -- and the handler maps that row to the
// response. A mock that echoed the POST body back would be handing the handler a
// shape it never receives, and the return-hop arms would be testing the mock.
function postgrestMock(role, calls) {
  return async function (url, opts) {
    const u = String(url);
    calls.push({ url: u, opts: opts || null });
    const q = u.indexOf('?') >= 0 ? u.slice(u.indexOf('?') + 1) : '';
    const eqs = [];
    q.split('&').forEach(function (part) {
      const m = part.match(/^([a-z0-9_]+)=eq\.(.*)$/);
      if (m) eqs.push([m[1], decodeURIComponent(m[2])]);
    });
    if (/_employee_auth\?/.test(u)) {
      return { ok: true, status: 200, json: async function () {
        return [{ license_hash: HASH, employee_id: ME, role: role, active: true }]; } };
    }
    if (/rpc\/alf_check_and_insert_mar_entry/.test(u)) {
      const sent = JSON.parse(opts.body);
      const row = { entry_id: sent.p_entry_id, resident_id: sent.p_resident_id,
                    entry_type: sent.p_entry_type,
                    assigned_employee_id: sent.p_assigned_employee_id,
                    data: sent.p_data, created_at: '2026-09-29T00:00:00Z' };
      return { ok: true, status: 200,
               text: async function () { return JSON.stringify([row]); },
               json: async function () { return [row]; } };
    }
    if (/alf_clients\?/.test(u)) {
      const forId = (eqs.filter(function (kv) { return kv[0] === 'client_id'; })[0] || [])[1];
      if (forId && forId !== RESIDENT) {
        return { ok: true, status: 200, json: async function () { return []; } };
      }
      return { ok: true, status: 200, json: async function () {
        return [{ license_hash: HASH, client_id: RESIDENT,
                  assigned_employee_id: ME, data: { name: 'A Resident' } }]; } };
    }
    if (opts && opts.method === 'POST') {
      const sent = JSON.parse(opts.body);
      return { ok: true, status: 200, text: async function () { return opts.body; },
               json: async function () { return [sent]; } };
    }
    return { ok: true, status: 200, json: async function () { return []; } };
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

async function write(role, payload) {
  const calls = [];
  const h = loadHandler(postgrestMock(role, calls));
  const res = mockRes();
  await h({
    method: 'POST',
    headers: {
      authorization: 'Bearer KEY-FOR-' + HASH,
      'x-sd-auth': signSessionToken({ app: APP, employee_id: ME,
                                      role: role, license_hash: HASH })
    },
    body: { action: 'write', resource: 'alf_mar', app_id: APP, payload: payload }
  }, res);
  const rpc = calls.filter(function (c) {
    return /rpc\/alf_check_and_insert_mar_entry/.test(c.url);
  })[0];
  return {
    res: res,
    stored: rpc ? JSON.parse(rpc.opts.body).p_data : null,
    got: res.body && res.body.data
  };
}

// entry_type -> the key that names who performed it, as the four UI writers in
// sairncare.html actually send them.
const ACTORS = [
  ['administration', 'administered_by', { medication_id: 'M1', date: '2026-09-29',
                                          time: '08:00', status: 'given' }],
  ['count', 'counted_by', { medication_id: 'M1', date: '2026-09-29',
                            count_value: 12, witness_id: 'emp-witness-2' }],
  ['reconciliation', 'reconciled_by', { type: 'monthly', date: '2026-09-29',
                                        summary: 'all counts agree' }],
  ['assessment_refusal', 'documented_by', { date: '2026-09-29',
                                            notes: 'resident declined' }]
];

(async () => {

section('1. THE ACTOR IS THE SESSION, on every entry type that has one');

for (const [entryType, actorKey, extra] of ACTORS) {
  await test(entryType + ': ' + actorKey + ' comes from the session, not the payload',
    async () => {
      const r = await write('nursing', Object.assign(
        { id: 'E-' + entryType, resident_id: RESIDENT, entry_type: entryType }, extra));
      assert.strictEqual(r.res.statusCode, 200,
        'write refused: ' + JSON.stringify(r.res.body));
      assert.ok(r.stored, 'no RPC call was made');
      assert.strictEqual(r.stored[actorKey], ME,
        actorKey + ' stored as ' + JSON.stringify(r.stored[actorKey]));
    });

  await test(entryType + ': a FORGED ' + actorKey + ' is ignored, both hops',
    async () => {
      const payload = Object.assign(
        { id: 'F-' + entryType, resident_id: RESIDENT, entry_type: entryType },
        extra, {});
      payload[actorKey] = VICTIM;
      const r = await write('nursing', payload);
      assert.strictEqual(r.res.statusCode, 200,
        'write refused: ' + JSON.stringify(r.res.body));
      // OUTBOUND -- what reaches the database
      assert.strictEqual(r.stored[actorKey], ME,
        'STORED ' + actorKey + ' = ' + JSON.stringify(r.stored[actorKey])
        + ' -- the caller named somebody else and the server believed it');
      // RETURN HOP -- what the client is told. A correct column with a blob
      // spread over it reads correct in the database and wrong in every
      // response, which is exactly how the alf_incidents defect survived nine
      // green arms on 2026-09-28.
      assert.strictEqual(r.got && r.got[actorKey], ME,
        'RESPONSE ' + actorKey + ' = ' + JSON.stringify(r.got && r.got[actorKey]));
    });
}

section('2. NO ENTRY TYPE MAY CARRY ANOTHER TYPE\'S ACTOR KEY');

await test('a count cannot smuggle an administered_by onto the MAR', async () => {
  // Without this the fix could stamp the RIGHT key and still let the caller
  // write the other three, and the MAR would carry a forged administration
  // attribution on a row that is not an administration.
  const r = await write('nursing', {
    id: 'X-1', resident_id: RESIDENT, entry_type: 'count',
    medication_id: 'M1', count_value: 3, witness_id: 'emp-witness-2',
    administered_by: VICTIM, reconciled_by: VICTIM, documented_by: VICTIM
  });
  assert.strictEqual(r.res.statusCode, 200, JSON.stringify(r.res.body));
  assert.strictEqual(r.stored.counted_by, ME, 'counted_by not stamped');
  ['administered_by', 'reconciled_by', 'documented_by'].forEach((k) => {
    assert.ok(!(k in r.stored),
      k + ' survived on a count entry as ' + JSON.stringify(r.stored[k]));
  });
});

section('3. WHAT MUST STILL WORK -- the controls');

await test('ordinary clinical fields are untouched', async () => {
  // A strip that took the whole payload would pass every arm above and destroy
  // the record. status, notes and refusal_reason are the MAR.
  const r = await write('nursing', {
    id: 'K-1', resident_id: RESIDENT, entry_type: 'administration',
    medication_id: 'M1', date: '2026-09-29', time: '08:00', status: 'refused',
    refusal_reason: 'resident asleep', notes: 'will retry at 10:00',
    administered_by: VICTIM
  });
  assert.strictEqual(r.stored.status, 'refused');
  assert.strictEqual(r.stored.refusal_reason, 'resident asleep');
  assert.strictEqual(r.stored.notes, 'will retry at 10:00');
  assert.strictEqual(r.stored.medication_id, 'M1');
});

await test('witness_id SURVIVES -- it names a second person, not the caller',
  async () => {
    // Deliberate, and pinned so this change is not mistaken for having closed
    // the witness question. SAIRNcare has NO server-side witness verification;
    // SAIRNvet has one (api/sv-witness.js). Registered separately.
    const r = await write('nursing', {
      id: 'W-1', resident_id: RESIDENT, entry_type: 'count',
      medication_id: 'M1', count_value: 5, witness_id: 'emp-witness-2'
    });
    assert.strictEqual(r.stored.witness_id, 'emp-witness-2',
      'witness_id was stripped -- a controlled-substance count lost its second '
      + 'signature entirely, which is worse than the forgeable one');
    assert.strictEqual(r.stored.counted_by, ME);
  });

await test('reviewed_by is still stamped on a pharmacy-order acceptance',
  async () => {
    // The field that was ALREADY correct. If the new map displaced it, the
    // regression would be invisible to every arm above.
    const r = await write('nursing', {
      id: 'P-1', resident_id: RESIDENT, entry_type: 'medication_order',
      pharmacy_status: 'accepted', medication_id: 'M1',
      reviewed_by: VICTIM
    });
    assert.strictEqual(r.res.statusCode, 200, JSON.stringify(r.res.body));
    assert.strictEqual(r.stored.reviewed_by, ME,
      'reviewed_by = ' + JSON.stringify(r.stored.reviewed_by));
    assert.ok(r.stored.reviewed_at, 'reviewed_at was not stamped');
  });

await test('NEGATIVE CONTROL: the harness can SEE a caller-supplied field',
  async () => {
    // Without this, a handler that dropped the entire payload would satisfy
    // every "forged value is gone" arm above and this suite would be green
    // against a broken endpoint.
    const r = await write('nursing', {
      id: 'N-1', resident_id: RESIDENT, entry_type: 'administration',
      medication_id: 'M1', status: 'given', zz_probe_marker: 'CARRIED-THROUGH'
    });
    assert.strictEqual(r.stored.zz_probe_marker, 'CARRIED-THROUGH',
      'the mock is not carrying payload fields through at all, so the arms '
      + 'above prove nothing about stripping');
  });

console.log('\n' + (fail === 0
  ? 'ALL ' + pass + ' alf_mar ACTOR-IDENTITY ASSERTIONS PASS'
  : pass + ' passed, ' + fail + ' FAILED'));
process.exit(fail === 0 ? 0 : 1);

})();
