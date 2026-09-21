// api/sd-data-law-trusttx-clearance.test.js
// REQUIREMENT: a clearance recorded against a DISBURSEMENT must either be
//   stored or be refused -- it must never come back ok:true over a write the
//   data store never performed, because an uncleared CHEQUE is a disbursement
//   and it is the commonest outstanding item in a trust reconciliation
//
// Run:  node api/sd-data-law-trusttx-clearance.test.js
//
// ── THE DEFECT, AND WHY IT IS INVISIBLE FROM EITHER END ALONE ─────────────
// api/sd-data.js routes every law_trusttx write with type 'Disbursement' and
// status not 'Voided' to rpc/law_check_and_insert_disbursement. That RPC takes
// NINE NAMED PARAMETERS -- licence, id, matter, client, amount, method,
// reference, description, date -- and none of them is a clearance field. Its
// body builds `data` with jsonb_build_object over ten fixed keys, and when the
// id already exists for the same client it takes the retry-idempotency branch
// (sql/sairnlaw_trusttx_functions.sql, `if v_existing_found then v_row :=
// v_existing;`) and RETURNS THE STORED ROW WITHOUT WRITING.
//
// So the round trip is a confirmed no-op: 200 {ok:true, data: row.data}, and
// sairnlaw.html's sdnData() returns a truthy d.data, and lawSetClearance()
// says "Marked cleared". Nothing was stored. Reading only the client, the
// write succeeded; reading only the SQL, the function is correct for what it
// is for. It is the SEAM that is wrong, which is why this file drives it.
//
// ── WHAT IS DRIVEN HERE, AND WHAT IS NOT ──────────────────────────────────
// Section 1 asserts a fact about api/sd-data.js ALONE and needs no model of
// the database: the request the handler sends carries no clearance field. That
// one cannot be wrong about Postgres because it never mentions it.
//
// Section 2 stubs the RPC to behave the way the SQL above says it behaves on
// an existing id, and asserts what the CALLER is told. That arm is only as
// good as the model, and the model is quoted in the comment beside it.
//
// Section 3 is the contrast that makes it a seam rather than a rule: a DEPOSIT
// takes the plain upsert two lines below, which sends `data: payload`, so the
// identical clearance is stored. Same app, same resource, same field, opposite
// outcome, decided by `type`.
'use strict';
const assert = require('assert');
// Set BEFORE _lib/auth is required: it reads the secret at load time and
// throws on an absent one, which is the right behaviour and means a fixture
// has to supply one first. Same line and same reasoning as
// api/sd-data-law-trusttx-session.test.js.
process.env.SD_AUTH_SECRET = ['law', 'trusttx', 'clearance', 'fixture'].join('-');
const { signSessionToken } = require('./_lib/auth.js');

const LIC_HASH = 'law-clearance-hash';
let passed = 0, total = 0;
async function test(name, fn) {
  total++;
  try { await fn(); passed++; console.log('  ok - ' + name); }
  catch (e) { console.log('  FAIL - ' + name + '\n        ' + e.message); }
}
function section(s) { console.log('\n' + s); }

function mockRes() {
  const res = { statusCode: null, body: null };
  res.status = function (c) { res.statusCode = c; return res; };
  res.json = function (b) { res.body = b; return res; };
  return res;
}
function mockReq(body) {
  return {
    method: 'POST',
    headers: {
      authorization: 'Bearer GOOD-KEY',
      'x-sd-auth': signSessionToken({
        app: 'sairnlaw', employee_id: 'emp-owner', role: 'owner', license_hash: LIC_HASH,
      }),
    },
    body,
  };
}
function loadHandler(fetchImpl) {
  delete require.cache[require.resolve('./_lib/license')];
  require.cache[require.resolve('./_lib/license')] = {
    exports: {
      validateLicenseKey: async () => ({
        valid: true, active: true, license_hash: LIC_HASH,
        trial_ends_at: null, stripe_subscription_id: null,
      }),
    },
  };
  global.fetch = fetchImpl;
  delete require.cache[require.resolve('./sd-data.js')];
  return require('./sd-data.js');
}

// THE STORED ROW, as the database really holds it: a cheque written on the
// 14th, posted, and carrying NO clearance because nothing has ever put one
// there.
const STORED = {
  id: 'T-CHQ', matter_id: 'M1', client_id: 'C1', type: 'Disbursement',
  amount: 40, date: '2026-09-14', status: 'Posted', created_at: '2026-09-14',
};
// What lawSetClearance() sends: the whole record with the clearance applied.
const MARKED = Object.assign({}, STORED, {
  cleared_on: '2026-09-20', cleared: true, cleared_at: '2026-09-21T12:00:00.000Z',
});

// A REST stub that answers the credential lookup and records every call, and
// models the RPC's EXISTING-ID branch: it returns the stored row untouched,
// which is what `if v_existing_found then v_row := v_existing;` does.
function restStub(calls, opts) {
  const o = opts || {};
  return async function (url, init) {
    const u = String(url);
    calls.push({ url: u, body: init && init.body ? JSON.parse(init.body) : null,
                 method: (init && init.method) || 'GET' });
    if (u.indexOf('sairnlaw_employee_auth') !== -1) {
      return { ok: true, status: 200, json: async () => [{ active: true }] };
    }
    if (u.indexOf('rpc/law_check_and_insert_disbursement') !== -1) {
      // The existing-id path. Returns the STORED row, having written nothing.
      return { ok: true, status: 200, json: async () => [{ data: o.rpcData || STORED }] };
    }
    if (u.indexOf('law_trusttx') !== -1) {
      // The plain upsert path echoes back what it was given, as PostgREST does
      // under Prefer: return=representation.
      const sent = init && init.body ? JSON.parse(init.body) : {};
      return { ok: true, status: 200, json: async () => [{ data: sent.data || {} }] };
    }
    return { ok: true, status: 200, json: async () => [] };
  };
}

async function write(payload, opts) {
  const calls = [];
  const handler = loadHandler(restStub(calls, opts));
  const res = mockRes();
  await handler(mockReq({ action: 'write', resource: 'law_trusttx', app_id: 'sairnlaw', payload }), res);
  return { res, calls };
}

(async () => {
  console.log('api/sd-data.js -- a clearance on a DISBURSEMENT (attorney trust money)');

  section('1. the request itself: what the handler sends the database');

  await test('a Disbursement write goes to the RPC, not to the plain upsert', async () => {
    const { calls } = await write(MARKED);
    const rpc = calls.find((c) => c.url.indexOf('rpc/law_check_and_insert_disbursement') !== -1);
    assert.ok(rpc, 'the disbursement did not reach the balance-checking RPC');
  });

  await test('THE DEFECT: the RPC call carries NO clearance field at all', async () => {
    // A fact about api/sd-data.js on its own. Whatever the database does with
    // the nine parameters, a field that is not in the request cannot be stored
    // by it.
    const { calls } = await write(MARKED);
    const rpc = calls.find((c) => c.url.indexOf('rpc/law_check_and_insert_disbursement') !== -1);
    const sent = Object.keys(rpc.body || {});
    ['cleared_on', 'cleared', 'cleared_at'].forEach((k) => {
      assert.ok(!sent.some((p) => p.indexOf(k) !== -1),
        'expected no clearance parameter, found one of: ' + sent.join(', '));
    });
  });

  section('2. what the CALLER is told, with the RPC behaving as its SQL says');

  await test('THE FALSE SUCCESS IS REFUSED: a clearance the store did not take is not ok:true', async () => {
    // `if v_existing_found then v_row := v_existing;` returns the stored row
    // having written nothing, so the response carries no clearance. Answering
    // ok:true over that is the platform's oldest refusal: a confirmation for a
    // write that did not happen, on attorney client trust money.
    const { res } = await write(MARKED);
    assert.notStrictEqual(res.statusCode, 200,
      'the caller was told the clearance was saved and it was not');
    assert.strictEqual(res.body && res.body.error && res.body.error.code, 'CLEARANCE_NOT_STORED',
      JSON.stringify(res.body));
  });

  await test('...and the refusal SAYS WHAT IS WRONG rather than blaming the network', async () => {
    const { res } = await write(MARKED);
    const m = (res.body && res.body.error && res.body.error.message) || '';
    assert.match(m, /Nothing was saved/, m);
    assert.match(m, /disbursement/i, m);
  });

  await test('MARKING IT OUTSTANDING IS REFUSED TOO, and that is the case the feature is FOR', async () => {
    // The shape lawSetClearance() sends for "outstanding": `cleared:false` and
    // a stamp, with `cleared_on` DELETED. Two keys, not three, and one of them
    // is falsy -- so a guard written with `payload[k]` truthiness, or one that
    // waits for all three keys, lets exactly this through. An uncleared cheque
    // marked outstanding is the commonest outstanding item there is.
    const out = Object.assign({}, STORED, { cleared: false, cleared_at: '2026-09-21T12:00:00.000Z' });
    const { res } = await write(out);
    assert.strictEqual(res.body && res.body.error && res.body.error.code, 'CLEARANCE_NOT_STORED',
      JSON.stringify(res.body));
    // ── THE MESSAGE MUST NAME `cleared`, AND THAT IS NOT PEDANTRY ──────────
    // The first version of this arm asserted only that the refusal FIRED, and
    // the negative control planted `payload[k]` in place of
    // `payload[k] !== undefined` -- the two forms differ on exactly one value,
    // `false` -- and the arm STAYED GREEN. It stayed green for the wrong
    // reason: `cleared_at` is truthy, so the refusal still happened, naming
    // one field instead of two. The outcome was right and the finding was
    // wrong, which is the shape that survives review.
    //
    // A client that does not stamp -- or a future one that stops -- would send
    // `cleared:false` alone, every key would read falsy, and the whole
    // outstanding case would walk through. So the assertion is on WHICH FIELDS
    // the refusal names, not on whether it fired.
    //
    // AND THE SECOND VERSION OF THIS ARM WAS ALSO WRONG, which is why the
    // refusal now carries a `fields` array. It asserted `/\bcleared\b/` over
    // the MESSAGE -- and the message ends "whether a cheque has cleared the
    // bank", so the regex matched that prose and the arm stayed green with the
    // defect planted. The control caught it both times; reading the message
    // did not. An assertion over a sentence cannot tell the sentence's subject
    // from its wording.
    assert.deepStrictEqual((res.body.error.fields || []).slice().sort(),
      ['cleared', 'cleared_at'],
      'the refusal named ' + JSON.stringify(res.body.error.fields)
      + ' -- the FLAG is how an outstanding cheque is recorded and it is missing');
  });

  await test('a Disbursement with NO clearance is untouched by this -- it still succeeds', async () => {
    // The guard must be about the clearance, not about disbursements. Posting
    // a new cheque is the normal path and it goes through unchanged.
    const { res } = await write(STORED);
    assert.strictEqual(res.statusCode, 200, JSON.stringify(res.body));
    assert.strictEqual(res.body.ok, true);
  });

  await test('and it stops complaining the moment the store DOES carry the clearance', async () => {
    // THE CHECK RETIRES ITSELF. It compares what was asked for against what
    // came back, so when the RPC is taught to carry these fields the refusal
    // stops firing with no second change and nothing to remember.
    const { res } = await write(MARKED, { rpcData: MARKED });
    assert.strictEqual(res.statusCode, 200, JSON.stringify(res.body));
    assert.strictEqual(res.body.data.cleared_on, '2026-09-20');
  });

  section('3. the contrast that makes it a SEAM: a Deposit stores it fine');

  await test('a DEPOSIT in transit takes the plain upsert and keeps its clearance', async () => {
    const dep = Object.assign({}, MARKED, { id: 'T-DEP', type: 'Deposit' });
    const { res, calls } = await write(dep);
    assert.strictEqual(res.statusCode, 200, JSON.stringify(res.body));
    const up = calls.find((c) => c.url.indexOf('law_trusttx?on_conflict') !== -1);
    assert.ok(up, 'the deposit did not take the upsert path');
    assert.strictEqual(up.body.data.cleared_on, '2026-09-20',
      'the upsert path dropped the clearance too -- then this is not a seam, it is a rule');
    assert.strictEqual(res.body.data.cleared_on, '2026-09-20');
  });

  await test('a VOIDED disbursement also takes the non-RPC path, so it is unaffected', async () => {
    const voided = Object.assign({}, MARKED, { id: 'T-VOID', status: 'Voided' });
    const { calls } = await write(voided);
    assert.ok(!calls.some((c) => c.url.indexOf('rpc/law_check_and_insert_disbursement') !== -1),
      'a voided disbursement reached the balance RPC');
  });

  console.log('\n' + passed + '/' + total + ' passed');
  process.exit(passed === total ? 0 : 1);
})();
