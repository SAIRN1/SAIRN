// api/sd-data-mech-credentials.test.js
// Run: node api/sd-data-mech-credentials.test.js
//
// SAIRNmechanical's FIRST data resource. Until 2026-09-02 the app had complete
// per-employee auth (api/mech-auth.js) and no data layer at all -- no registry
// module, and `sairnmechanical` appeared zero times in api/sd-data.js.
//
// The engine's logic is covered in api/_lib/mech-credentials.test.js. What is
// asserted here is the boundary: who may read, who may write, what the endpoint
// refuses to store, and that a renewal cannot overwrite the record it renews.

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
    body: { action: action, resource: 'mech_credentials', payload: payload || {} }
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
        return opts.noSession ? null : { employee_id: opts.employeeId || 'mgr-1', role: opts.role || 'owner' };
      }
    })
  };
  global.fetch = async function (url, init) {
    const method = (init && init.method) || 'GET';
    calls.push({ url: String(url), method: method, headers: (init && init.headers) || {}, body: init && init.body });
    if (opts.refuseNetwork) throw new Error('a refused request reached the database');
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

const GOOD = {
  credential_id: 'CRED-1', technician_id: 'tech-7', record_type: 'epa_608',
  epa_section: 'universal', has_expiry: false, issued_on: '2021-03-01', issuer: 'ESCO'
};

async function main() {
  console.log('api/sd-data.js -- mech_credentials: append-only, session-gated, management-write');
  process.env.SUPABASE_URL = 'https://test.supabase.co';
  process.env.SUPABASE_SERVICE_ROLE_KEY = 'test-key';

  await test('the resource is registered -- an unregistered one 400s with the list', async () => {
    const reg = require('./_resources');
    assert.ok(reg.RESOURCES['mech_credentials'], 'mech_credentials is not registered');
    assert.deepStrictEqual(reg.EXTRA_ACTIONS['mech_credentials'], ['eligibility']);
  });

  await test('no session -> 401 on read, and never touches the database', async () => {
    const { handler, calls } = loadHandler({ noSession: true, refuseNetwork: true });
    const res = mockRes();
    await handler(mockReq('read'), res);
    assert.strictEqual(res.statusCode, 401);
    assert.strictEqual(calls.length, 0);
  });

  await test('a technician CAN read the board -- a dispatcher must see it', async () => {
    const { handler } = loadHandler({ role: 'tech', rows: [] });
    const res = mockRes();
    await handler(mockReq('read'), res);
    assert.strictEqual(res.statusCode, 200);
    assert.strictEqual(res.body.board.ok, true);
  });

  await test('a technician CANNOT write -- nobody records their own licence', async () => {
    const { handler, calls } = loadHandler({ role: 'tech' });
    const res = mockRes();
    await handler(mockReq('write', GOOD), res);
    assert.strictEqual(res.statusCode, 403);
    assert.match(res.body.error.message, /Owner or Manager/);
    assert.strictEqual(calls.filter(c => c.method === 'POST').length, 0);
  });

  for (const role of ['owner', 'admin']) {
    await test(role + ' can write', async () => {
      const { handler } = loadHandler({ role: role });
      const res = mockRes();
      await handler(mockReq('write', GOOD), res);
      assert.strictEqual(res.statusCode, 200);
    });
  }

  // ---- what it refuses to store -----------------------------------------
  await test('EPA 608 with NO SECTION is refused -- the section is the answer', async () => {
    // Type I/II/III are different equipment. A sectionless EPA record could not
    // answer the only question it exists to answer.
    const { handler } = loadHandler({});
    const res = mockRes();
    await handler(mockReq('write', Object.assign({}, GOOD, { epa_section: null })), res);
    assert.strictEqual(res.statusCode, 400);
    assert.strictEqual(res.body.error.code, 'NO_EPA_SECTION');
  });

  await test('an invented section is refused', async () => {
    const { handler } = loadHandler({});
    const res = mockRes();
    await handler(mockReq('write', Object.assign({}, GOOD, { epa_section: 'type_iv' })), res);
    assert.strictEqual(res.body.error.code, 'NO_EPA_SECTION');
  });

  await test('has_expiry MUST BE STATED -- it is never defaulted', async () => {
    // EPA 608 is for life (40 CFR 82.161); NATE renews on two years. Guessing
    // either way would be the app making a claim about a legal document.
    const p = Object.assign({}, GOOD); delete p.has_expiry;
    const { handler } = loadHandler({});
    const res = mockRes();
    await handler(mockReq('write', p), res);
    assert.strictEqual(res.statusCode, 400);
    assert.strictEqual(res.body.error.code, 'NO_EXPIRY_STATED');
  });

  await test('has_expiry:true without a date is refused', async () => {
    const { handler } = loadHandler({});
    const res = mockRes();
    await handler(mockReq('write', Object.assign({}, GOOD, { record_type: 'nate', epa_section: null, has_expiry: true })), res);
    assert.strictEqual(res.body.error.code, 'NO_EXPIRY_DATE');
  });

  await test('an unknown record type is refused, naming the allowed ones', async () => {
    const { handler } = loadHandler({});
    const res = mockRes();
    await handler(mockReq('write', Object.assign({}, GOOD, { record_type: 'vibes' })), res);
    assert.strictEqual(res.body.error.code, 'UNKNOWN_RECORD_TYPE');
    assert.match(res.body.error.message, /epa_608/);
  });

  await test('a credential with no technician is refused', async () => {
    const { handler } = loadHandler({});
    const res = mockRes();
    await handler(mockReq('write', Object.assign({}, GOOD, { technician_id: '  ' })), res);
    assert.strictEqual(res.body.error.code, 'NO_TECHNICIAN');
  });

  // ---- append-only --------------------------------------------------------
  await test('THE INSERT IS PLAIN -- an upsert would let a licence be edited', async () => {
    const { handler, calls } = loadHandler({});
    await handler(mockReq('write', GOOD), mockRes());
    const post = calls.find(c => c.method === 'POST');
    assert.ok(!/merge-duplicates/.test(String(post.headers.Prefer || '')));
    assert.ok(!/on_conflict/.test(post.url));
  });

  await test('a duplicate credential_id -> 409 that says a renewal is a NEW record', async () => {
    const { handler } = loadHandler({ writeStatus: 409 });
    const res = mockRes();
    await handler(mockReq('write', GOOD), res);
    assert.strictEqual(res.statusCode, 409);
    assert.match(res.body.error.message, /renewal is a NEW record/);
  });

  await test('recorded_by comes from the session, never the body', async () => {
    const { handler, calls } = loadHandler({ employeeId: 'mgr-real' });
    await handler(mockReq('write', Object.assign({}, GOOD, { recorded_by: 'mgr-forged' })), mockRes());
    const sent = JSON.parse(calls.find(c => c.method === 'POST').body);
    assert.strictEqual(sent.recorded_by, 'mgr-real');
    assert.strictEqual(sent.license_hash, 'test-hash');
  });

  await test('expires_on is dropped when has_expiry is false, not stored alongside it', async () => {
    const { handler, calls } = loadHandler({});
    await handler(mockReq('write', Object.assign({}, GOOD, { expires_on: '2030-01-01' })), mockRes());
    const sent = JSON.parse(calls.find(c => c.method === 'POST').body);
    assert.strictEqual(sent.expires_on, null, 'a lifetime credential was stored with an expiry date');
  });

  // ---- eligibility --------------------------------------------------------
  await test('eligibility with no requirements -> 400, not "anyone may go"', async () => {
    const { handler } = loadHandler({ rows: [] });
    const res = mockRes();
    await handler(mockReq('eligibility', { requirements: [] }), res);
    assert.strictEqual(res.statusCode, 400);
    assert.strictEqual(res.body.error.code, 'NO_REQUIREMENTS');
  });

  await test('eligibility WRITES NOTHING -- it is a question, not a record', async () => {
    const { handler, calls } = loadHandler({
      rows: [{ technician_id: 't1', record_type: 'epa_608', epa_section: 'universal', has_expiry: false }]
    });
    const res = mockRes();
    await handler(mockReq('eligibility', { requirements: [{ record_type: 'epa_608', epa_section: 'type_ii' }], today: '2026-09-02' }), res);
    assert.strictEqual(res.statusCode, 200);
    assert.deepStrictEqual(res.body.eligibility.eligible, ['t1']);
    assert.strictEqual(calls.filter(c => c.method !== 'GET').length, 0, 'asking who may be dispatched wrote something');
  });

  // ---- provisioning -------------------------------------------------------
  await test('un-run migration: READ is 200 provisioned:false, WRITE is 503 naming the file', async () => {
    const r1 = mockRes();
    await loadHandler({ readStatus: 404 }).handler(mockReq('read'), r1);
    assert.strictEqual(r1.statusCode, 200);
    assert.strictEqual(r1.body.provisioned, false);

    const r2 = mockRes();
    await loadHandler({ writeStatus: 404 }).handler(mockReq('write', GOOD), r2);
    assert.strictEqual(r2.statusCode, 503);
    assert.match(r2.body.error.message, /mech_credentials_schema\.sql/);
  });

  console.log('\n' + (process.exitCode ? 'FAILURES ABOVE' : 'ALL ' + passed + ' MECH-ENDPOINT ASSERTIONS PASS'));
}

main();
