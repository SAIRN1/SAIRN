// api/sd-data-mech-insurance.test.js
// REQUIREMENT: an empty coverage limit is stored as NULL rather than coerced
//   through Number() into a limit of ZERO, because a limit nobody read off the
//   certificate would otherwise fail every requirement for a reason nobody
//   typed -- and people learn to ignore a board that cries wolf
//
// Run: node api/sd-data-mech-insurance.test.js
//
// SAIRNmechanical's BUSINESS insurance / COI endpoint. The engine's logic lives
// in api/_lib/mech-insurance.test.js; what is asserted here is the boundary,
// plus the one thing an engine test can never see: IS IT WIRED.
//
// THAT LAST ONE IS NOT DECORATIVE. This app has the failure on record: the
// `eligibility` action, its engine, its registry entry and ten test arms all
// existed on 2026-09-17, and sairnmechanical.html never sent the action -- the
// string appeared exactly once in the file and it was a sentence claiming the
// feature. So the columns-are-fetched and action-is-reachable arms are here by
// name.

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
    headers: { authorization: 'Bearer MECH-TEST-KEY', 'x-sd-auth': 'tok' },
    body: { action: action, resource: 'mech_insurance_policies', payload: payload || {} }
  };
}

let passed = 0;
async function test(name, fn) {
  try { await fn(); passed++; console.log('  ok - ' + name); }
  catch (e) { console.error('  FAIL - ' + name + '\n    ' + e.message); process.exitCode = 1; }
}

function loadHandler(opts) {
  opts = opts || {};
  const calls = [];
  delete require.cache[require.resolve('./_lib/license')];
  require.cache[require.resolve('./_lib/license')] = {
    exports: {
      validateLicenseKey: async function () {
        return { valid: true, active: true, license_hash: 'test-hash', trial_ends_at: null, stripe_subscription_id: null };
      }
    }
  };
  const realAuth = require('./_lib/auth');
  delete require.cache[require.resolve('./_lib/auth')];
  require.cache[require.resolve('./_lib/auth')] = {
    exports: Object.assign({}, realAuth, {
      tokenFromRequest: function () { return 'tok'; },
      verifySessionToken: function () {
        return opts.noSession ? null : { employee_id: opts.employeeId || 'owner-1', role: opts.role || 'owner' };
      }
    })
  };
  global.fetch = async function (url, init) {
    const method = (init && init.method) || 'GET';
    calls.push({ url: String(url), method: method, headers: (init && init.headers) || {}, body: init && init.body });
    if (method === 'GET') {
      const st = opts.readStatus || 200;
      return { ok: st === 200, status: st, json: async () => (st === 200 ? (opts.rows || []) : {}) };
    }
    const st = opts.writeStatus || 201;
    return { ok: st < 300, status: st, json: async () => (st < 300 ? [JSON.parse(init.body)] : {}) };
  };
  delete require.cache[require.resolve('./sd-data.js')];
  return { handler: require('./sd-data.js'), calls: calls };
}

const TODAY = '2026-09-25';
const GOOD = {
  policy_key: 'GL-2026', kind: 'general_liability', carrier: 'Acme Mutual',
  policy_no: 'GL-1', effective_on: '2026-01-01', expires_on: '2027-01-01',
  each_occurrence: 1000000, aggregate_limit: 2000000
};
const ROW = {
  policy_key: 'GL-2026', kind: 'general_liability', carrier: 'Acme Mutual',
  policy_no: 'GL-1', effective_on: '2026-01-01', expires_on: '2027-01-01',
  each_occurrence: 1000000, aggregate_limit: 2000000,
  additional_insured: true, waiver_of_subrogation: null,
  primary_noncontributory: null, per_project_aggregate: null
};

async function main() {
  console.log('SAIRNmechanical business insurance endpoint\n');

  await test('IS IT WIRED: every column the engine reads is in the SELECT list', async () => {
    const { handler, calls } = loadHandler({ rows: [] });
    await handler(mockReq('read', { today: TODAY }), mockRes());
    const url = calls.find(c => c.method === 'GET').url;
    ['each_occurrence', 'aggregate_limit', 'expires_on', 'additional_insured',
     'waiver_of_subrogation', 'primary_noncontributory', 'per_project_aggregate']
      .forEach(function (c) {
        assert.ok(url.indexOf(c) !== -1,
          c + ' is not fetched -- the comparison would report unknown for every requirement forever');
      });
  });

  await test('read computes the board from the engine rather than returning bare rows', async () => {
    const { handler } = loadHandler({ rows: [ROW] });
    const res = mockRes();
    await handler(mockReq('read', { today: TODAY }), res);
    assert.strictEqual(res.body.board.counts.current, 1);
    assert.strictEqual(res.body.board.rows[0].each_occurrence, 1000000);
  });

  await test('read will not assume a clock -- no today is a 400, never now()', async () => {
    const res = mockRes();
    await loadHandler({ rows: [ROW] }).handler(mockReq('read', {}), res);
    assert.strictEqual(res.statusCode, 400);
    assert.strictEqual(res.body.error.code, 'NO_TODAY');
  });

  await test('an unprovisioned registry fails CLOSED -- provisioned:false, not an empty board', async () => {
    const res = mockRes();
    await loadHandler({ readStatus: 404 }).handler(mockReq('read', { today: TODAY }), res);
    assert.strictEqual(res.body.provisioned, false);
    assert.ok(!res.body.board, 'a board was computed for a registry that does not exist');
  });

  await test('no session is 401 on every action', async () => {
    for (const a of ['read', 'write', 'readiness']) {
      const res = mockRes();
      await loadHandler({ noSession: true }).handler(mockReq(a, { today: TODAY }), res);
      assert.strictEqual(res.statusCode, 401, a + ' did not refuse');
    }
  });

  await test('WRITE IS MANAGEMENT ONLY -- a coverage limit is a number an owner will be shown', async () => {
    const res = mockRes();
    await loadHandler({ role: 'tech' }).handler(mockReq('write', GOOD), res);
    assert.strictEqual(res.statusCode, 403);
    assert.strictEqual(res.body.error.code, 'NOT_PERMITTED');
  });

  await test('...and READ is not -- a dispatcher must be able to see the position', async () => {
    const res = mockRes();
    await loadHandler({ role: 'tech', rows: [ROW] }).handler(mockReq('read', { today: TODAY }), res);
    assert.strictEqual(res.body.ok, true);
  });

  await test('THE ARM THAT MATTERS: an empty limit is stored as NULL, never as 0', async () => {
    for (const v of ['', null, undefined]) {
      const p = Object.assign({}, GOOD);
      if (v === undefined) delete p.each_occurrence; else p.each_occurrence = v;
      const { handler, calls } = loadHandler({});
      await handler(mockReq('write', p), mockRes());
      const sent = JSON.parse(calls.find(c => c.method === 'POST').body);
      assert.strictEqual(sent.each_occurrence, null,
        'an unread limit was stored as ' + JSON.stringify(sent.each_occurrence));
    }
  });

  await test('...and a limit that is present but not a number is REFUSED, not dropped to null', async () => {
    for (const v of ['lots', -1, 'NaN']) {
      const res = mockRes();
      await loadHandler({}).handler(mockReq('write', Object.assign({}, GOOD, { each_occurrence: v })), res);
      assert.strictEqual(res.statusCode, 400, 'accepted ' + JSON.stringify(v));
      assert.strictEqual(res.body.error.code, 'BAD_LIMIT');
    }
  });

  await test('an explicit ZERO is accepted and stored as zero -- it is a real limit, and the refusal above must not swallow it', async () => {
    const { handler, calls } = loadHandler({});
    await handler(mockReq('write', Object.assign({}, GOOD, { each_occurrence: 0 })), mockRes());
    const sent = JSON.parse(calls.find(c => c.method === 'POST').body);
    assert.strictEqual(sent.each_occurrence, 0);
  });

  await test('the four endorsements are TRI-STATE: a non-boolean is refused, never coerced', async () => {
    for (const f of ['additional_insured', 'waiver_of_subrogation',
                     'primary_noncontributory', 'per_project_aggregate']) {
      for (const v of ['false', 'true', 'yes', 1]) {
        const res = mockRes();
        const p = Object.assign({}, GOOD); p[f] = v;
        await loadHandler({}).handler(mockReq('write', p), res);
        assert.strictEqual(res.statusCode, 400, f + ' accepted ' + JSON.stringify(v));
        assert.strictEqual(res.body.error.code, 'BAD_ENDORSEMENT_FLAG');
      }
    }
  });

  await test('...and unstated endorsements are stored as null, never as false', async () => {
    const { handler, calls } = loadHandler({});
    await handler(mockReq('write', GOOD), mockRes());
    const sent = JSON.parse(calls.find(c => c.method === 'POST').body);
    ['additional_insured', 'waiver_of_subrogation', 'primary_noncontributory',
     'per_project_aggregate'].forEach(function (f) {
      assert.strictEqual(sent[f], null, f + ' was stored as ' + JSON.stringify(sent[f]));
    });
  });

  await test('an unknown coverage kind is refused rather than creating a silent bucket', async () => {
    const res = mockRes();
    await loadHandler({}).handler(mockReq('write', Object.assign({}, GOOD, { kind: 'cyber' })), res);
    assert.strictEqual(res.statusCode, 400);
    assert.strictEqual(res.body.error.code, 'BAD_KIND');
  });

  await test('a malformed policy date is REFUSED, not silently dropped -- a dropped expiry reads as a policy with no expiry', async () => {
    for (const f of ['effective_on', 'expires_on']) {
      const res = mockRes();
      const p = Object.assign({}, GOOD); p[f] = '01/01/2027';
      await loadHandler({}).handler(mockReq('write', p), res);
      assert.strictEqual(res.statusCode, 400, f + ' accepted a slash date');
      assert.strictEqual(res.body.error.code, 'BAD_POLICY_DATE');
    }
  });

  await test('a policy with no key is refused -- the key is what makes a renewal a new row', async () => {
    const p = Object.assign({}, GOOD); delete p.policy_key;
    const res = mockRes();
    await loadHandler({}).handler(mockReq('write', p), res);
    assert.strictEqual(res.body.error.code, 'NO_POLICY_KEY');
  });

  await test('the write is an UPSERT on (license_hash, policy_key), so a correction merges and a renewal is a new key', async () => {
    const { handler, calls } = loadHandler({});
    await handler(mockReq('write', GOOD), mockRes());
    const post = calls.find(c => c.method === 'POST');
    assert.ok(post.url.indexOf('on_conflict=license_hash,policy_key') !== -1, post.url);
    assert.ok(String(post.headers.Prefer || '').indexOf('merge-duplicates') !== -1);
  });

  await test('READINESS is reachable, and the requirements it answers are the CALLER\'S', async () => {
    const { handler } = loadHandler({ rows: [ROW] });
    const res = mockRes();
    await handler(mockReq('readiness', { today: TODAY, requirements: [
      { kind: 'general_liability', each_occurrence: 1000000, endorsements: ['additional_insured'] }
    ] }), res);
    assert.strictEqual(res.body.readiness.lines[0].met, true,
      res.body.readiness.lines[0].reasons.join('; '));
  });

  await test('readiness with NO requirements REFUSES rather than inventing a standard packet', async () => {
    const res = mockRes();
    await loadHandler({ rows: [ROW] }).handler(mockReq('readiness', { today: TODAY }), res);
    assert.strictEqual(res.statusCode, 400);
    assert.strictEqual(res.body.error.code, 'NO_REQUIREMENTS');
  });

  await test('readiness reports NOT MET against a limit the certificate does not carry, and names the shortfall', async () => {
    const { handler } = loadHandler({ rows: [ROW] });
    const res = mockRes();
    await handler(mockReq('readiness', { today: TODAY, requirements: [
      { kind: 'general_liability', each_occurrence: 5000000 }
    ] }), res);
    const line = res.body.readiness.lines[0];
    assert.strictEqual(line.met, false);
    assert.ok(/5000000|5,000,000/.test(line.reasons.join(' ')), line.reasons.join(' '));
  });

  await test('an endorsement nobody recorded is NOT carried, through the endpoint as well as the engine', async () => {
    const { handler } = loadHandler({ rows: [ROW] });
    const res = mockRes();
    await handler(mockReq('readiness', { today: TODAY, requirements: [
      { kind: 'general_liability', endorsements: ['waiver_of_subrogation'] }
    ] }), res);
    assert.strictEqual(res.body.readiness.lines[0].met, false);
    assert.ok(/unknown is not carried/.test(res.body.readiness.lines[0].reasons.join(' ')));
  });

  await test('the endpoint never invents a today for readiness either', async () => {
    const res = mockRes();
    await loadHandler({ rows: [ROW] }).handler(mockReq('readiness', { requirements: [{ kind: 'general_liability' }] }), res);
    assert.strictEqual(res.body.error.code, 'NO_TODAY');
  });

  console.log('\n' + (process.exitCode
    ? 'FAILURES ABOVE'
    : 'ALL ' + passed + ' MECH-INSURANCE-ENDPOINT ASSERTIONS PASS'));
}

main();
