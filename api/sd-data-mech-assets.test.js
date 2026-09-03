// api/sd-data-mech-assets.test.js
// Run: node api/sd-data-mech-assets.test.js
//
// SAIRNmechanical's site asset registry endpoint -- capability #2 on the
// 2026-08-27 research list. The engine's logic lives in
// api/_lib/mech-assets.test.js; what is asserted here is the boundary.
//
// The assertion that carries the most weight is the charge one. Number('') is
// 0 in JavaScript, so an empty charge field coerced through Number() becomes a
// measured zero -- and a unit nobody has ever weighed gets reported as BELOW
// the 40 CFR 82.157 threshold. That is a compliance claim with no evidence,
// and this endpoint stores NULL instead.

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
    body: { action: action, resource: 'mech_site_assets', payload: payload || {} }
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
        return opts.noSession ? null : { employee_id: opts.employeeId || 'tech-3', role: opts.role || 'tech' };
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
  asset_id: 'AST-1', customer_name: 'Ruiz Foods', site_name: 'Plant 1',
  asset_type: 'chiller', make: 'Trane', model: 'CVHE', serial_no: 'X1',
  refrigerant_type: 'r134a', refrigerant_charge_lb: 900
};

async function main() {
  console.log('api/sd-data.js -- mech_site_assets: upsert, session-gated, unknown charge is never zero');
  process.env.SUPABASE_URL = 'https://test.supabase.co';
  process.env.SUPABASE_SERVICE_ROLE_KEY = 'test-key';

  await test('the resource is registered', () => {
    assert.ok(require('./_resources').RESOURCES['mech_site_assets']);
  });

  await test('no session -> 401, and never touches the database', async () => {
    const { handler, calls } = loadHandler({ noSession: true, refuseNetwork: true });
    const res = mockRes();
    await handler(mockReq('read'), res);
    assert.strictEqual(res.statusCode, 401);
    assert.strictEqual(calls.length, 0);
  });

  await test('A TECHNICIAN CAN WRITE -- recording the unit in front of them is the workflow', async () => {
    // Deliberately unlike mech_credentials, which is management-only because
    // nobody should record their own licence. That reasoning does not transfer
    // to describing a machine, and copying it would block the primary use.
    const { handler } = loadHandler({ role: 'tech' });
    const res = mockRes();
    await handler(mockReq('write', GOOD), res);
    assert.strictEqual(res.statusCode, 200);
  });

  // ---- the charge, which is the whole point ------------------------------
  for (const empty of ['', '   ', null, undefined]) {
    await test('an empty charge (' + JSON.stringify(empty) + ') is stored as NULL, never 0', async () => {
      const { handler, calls } = loadHandler({});
      const p = Object.assign({}, GOOD, { refrigerant_charge_lb: empty });
      await handler(mockReq('write', p), mockRes());
      const sent = JSON.parse(calls.find(c => c.method === 'POST').body);
      assert.strictEqual(sent.refrigerant_charge_lb, null,
        'an un-weighed unit was stored as a measured ' + sent.refrigerant_charge_lb);
    });
  }

  await test('a real zero IS stored as zero -- somebody measured it', async () => {
    const { handler, calls } = loadHandler({});
    await handler(mockReq('write', Object.assign({}, GOOD, { refrigerant_charge_lb: 0 })), mockRes());
    const sent = JSON.parse(calls.find(c => c.method === 'POST').body);
    assert.strictEqual(sent.refrigerant_charge_lb, 0);
  });

  await test('a nonsense charge is REFUSED, and the message says not to type 0', async () => {
    const { handler } = loadHandler({});
    const res = mockRes();
    await handler(mockReq('write', Object.assign({}, GOOD, { refrigerant_charge_lb: 'about 40' })), res);
    assert.strictEqual(res.statusCode, 400);
    assert.strictEqual(res.body.error.code, 'BAD_CHARGE');
    assert.match(res.body.error.message, /Do not enter 0 to mean unknown/);
  });

  await test('a negative charge is refused', async () => {
    const { handler } = loadHandler({});
    const res = mockRes();
    await handler(mockReq('write', Object.assign({}, GOOD, { refrigerant_charge_lb: -3 })), res);
    assert.strictEqual(res.body.error.code, 'BAD_CHARGE');
  });

  // ---- warranty: three states, not two ----------------------------------
  await test('an unstated warranty is stored as NULL, not false', async () => {
    // false means "checked, and it is out". null means nobody checked. They
    // must not render the same, so they must not store the same.
    const { handler, calls } = loadHandler({});
    await handler(mockReq('write', GOOD), mockRes());
    const sent = JSON.parse(calls.find(c => c.method === 'POST').body);
    assert.strictEqual(sent.has_warranty, null);
  });

  await test('has_warranty:true without a date is refused', async () => {
    const { handler } = loadHandler({});
    const res = mockRes();
    await handler(mockReq('write', Object.assign({}, GOOD, { has_warranty: true })), res);
    assert.strictEqual(res.body.error.code, 'NO_WARRANTY_DATE');
  });

  // ---- validation -------------------------------------------------------
  await test('an unknown asset type is refused, naming the allowed ones', async () => {
    const { handler } = loadHandler({});
    const res = mockRes();
    await handler(mockReq('write', Object.assign({}, GOOD, { asset_type: 'spaceship' })), res);
    assert.strictEqual(res.body.error.code, 'UNKNOWN_ASSET_TYPE');
    assert.match(res.body.error.message, /chiller/);
  });

  await test('an unknown refrigerant is refused, but an absent one is fine', async () => {
    const { handler } = loadHandler({});
    const bad = mockRes();
    await handler(mockReq('write', Object.assign({}, GOOD, { refrigerant_type: 'r999' })), bad);
    assert.strictEqual(bad.body.error.code, 'UNKNOWN_REFRIGERANT');
    const ok = mockRes();
    const p = Object.assign({}, GOOD); delete p.refrigerant_type; delete p.refrigerant_charge_lb;
    await handler(mockReq('write', p), ok);
    assert.strictEqual(ok.statusCode, 200);
  });

  await test('an asset with no customer is refused', async () => {
    const { handler } = loadHandler({});
    const res = mockRes();
    await handler(mockReq('write', Object.assign({}, GOOD, { customer_name: '  ' })), res);
    assert.strictEqual(res.body.error.code, 'NO_CUSTOMER');
  });

  // ---- upsert, unlike credentials ---------------------------------------
  await test('THIS ONE UPSERTS -- an asset is a description, not evidence', async () => {
    // The opposite of mech_credentials, deliberately: a serial gets corrected
    // and a unit gets relocated, and forcing a new row per typo would make
    // "which row is the unit" ambiguous.
    const { handler, calls } = loadHandler({});
    await handler(mockReq('write', GOOD), mockRes());
    const post = calls.find(c => c.method === 'POST');
    assert.match(String(post.headers.Prefer || ''), /merge-duplicates/);
    assert.match(post.url, /on_conflict=license_hash,asset_id/);
  });

  await test('recorded_by and license_hash come from the server, not the body', async () => {
    const { handler, calls } = loadHandler({ employeeId: 'tech-real' });
    await handler(mockReq('write', Object.assign({}, GOOD, { recorded_by: 'forged', license_hash: 'someone-else' })), mockRes());
    const sent = JSON.parse(calls.find(c => c.method === 'POST').body);
    assert.strictEqual(sent.recorded_by, 'tech-real');
    assert.strictEqual(sent.license_hash, 'test-hash');
  });

  await test('status is constrained to active/retired, never free text', async () => {
    const { handler, calls } = loadHandler({});
    await handler(mockReq('write', Object.assign({}, GOOD, { status: 'exploded' })), mockRes());
    const sent = JSON.parse(calls.find(c => c.method === 'POST').body);
    assert.strictEqual(sent.status, 'active');
  });

  // ---- read --------------------------------------------------------------
  await test('read returns the board, with the threshold it used', async () => {
    const { handler } = loadHandler({
      rows: [
        { asset_id: 'A1', customer_name: 'C', asset_type: 'chiller', refrigerant_type: 'r22', refrigerant_charge_lb: 90 },
        { asset_id: 'A2', customer_name: 'C', asset_type: 'rtu', refrigerant_type: 'r410a' }
      ]
    });
    const res = mockRes();
    await handler(mockReq('read', { today: '2026-09-02' }), res);
    assert.strictEqual(res.statusCode, 200);
    assert.strictEqual(res.body.board.refrigerant.at_or_above, 1);
    assert.strictEqual(res.body.board.refrigerant.unknown_charge, 1);
    assert.strictEqual(res.body.board.threshold_lb, 50);
    assert.strictEqual(res.body.board.citation, '40 CFR 82.157');
  });

  await test('un-run migration: READ is provisioned:false, WRITE is 503 naming the file', async () => {
    const r1 = mockRes();
    await loadHandler({ readStatus: 404 }).handler(mockReq('read'), r1);
    assert.strictEqual(r1.body.provisioned, false);
    const r2 = mockRes();
    await loadHandler({ writeStatus: 404 }).handler(mockReq('write', GOOD), r2);
    assert.strictEqual(r2.statusCode, 503);
    assert.match(r2.body.error.message, /mech_site_assets_schema\.sql/);
  });

  console.log('\n' + (process.exitCode ? 'FAILURES ABOVE' : 'ALL ' + passed + ' MECH-ASSET-ENDPOINT ASSERTIONS PASS'));
}

main();
