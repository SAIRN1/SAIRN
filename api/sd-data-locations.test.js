// api/sd-data-locations.test.js
// Run: node api/sd-data-locations.test.js
//
// StoneDesk GAP 7 -- the 'locations' endpoint boundary. The roll-up itself is
// covered by tests/stonedesk_locations.js; this file is about who may do what.
//
// ══ WHY THIS EXISTS ═══════════════════════════════════════════════════════
// The GAP 7 branch shipped describing itself as carrying "the same
// licence-scoped gate as 'slabs' and 'remnants'". `slabs` is in
// SD_SESSION_GATED and therefore was never licence-scoped, so the comparison
// was wrong in the direction that mattered: `locations` had NO employee
// session requirement at all. Anyone holding the licence key could rename or
// close a yard.
//
// That is not a small hole, because the write is an UPSERT on
// (license_hash, location_id). Renaming a yard silently relabels every slab
// ever attributed to it, on every screen, with no record that anything
// changed -- and closing one does the same to its entire history.
//
// READ STAYS OPEN TO EVERY EMPLOYEE. A templater has to know which yard a slab
// is in to go and find it, and gating the read to management would break the
// primary use of the feature. Reading a yard and CHANGING one are different
// acts and are gated differently, on purpose.

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
    headers: { authorization: 'Bearer SD-TEST-KEY', 'x-sd-auth': 'tok' },
    body: { action: action, resource: 'locations', payload: payload === undefined ? {} : payload }
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
        return opts.noSession ? null : { employee_id: opts.employeeId || 'emp-1', role: opts.role || 'owner' };
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

const GOOD = { id: 'LOC1', name: 'Westlake Main', address: '1 Stone Way', active: true };

async function main() {
  console.log("api/sd-data.js -- 'locations': session-gated, read open to staff, write management-only");
  process.env.SUPABASE_URL = 'https://test.supabase.co';
  process.env.SUPABASE_SERVICE_ROLE_KEY = 'test-key';

  await test('the resource is registered', () => {
    // A working resource missing from the registry silently 400s -- the exact
    // way employee_profile failed. Asserted rather than assumed.
    assert.ok(require('./_resources').RESOURCES['locations']);
  });

  // ---- the hole this file was written for ---------------------------------
  await test('NO SESSION -> refused on READ, and never touches the database', async () => {
    const { handler, calls } = loadHandler({ noSession: true, refuseNetwork: true });
    const res = mockRes();
    await handler(mockReq('read', null), res);
    assert.strictEqual(res.statusCode, 403);
    assert.strictEqual(calls.length, 0);
  });

  await test('NO SESSION -> refused on WRITE. A licence key alone could rename a yard before this', async () => {
    const { handler, calls } = loadHandler({ noSession: true, refuseNetwork: true });
    const res = mockRes();
    await handler(mockReq('write', GOOD), res);
    assert.strictEqual(res.statusCode, 403);
    assert.strictEqual(calls.length, 0);
  });

  // ---- who may read --------------------------------------------------------
  for (const role of ['tech', 'sales', 'installer', 'fabricator', 'admin', 'owner']) {
    await test('a ' + role + ' CAN read the yards -- finding a slab requires knowing its site', async () => {
      const { handler } = loadHandler({ role: role });
      const res = mockRes();
      await handler(mockReq('read', null), res);
      assert.strictEqual(res.statusCode, 200);
    });
  }

  // ---- who may write -------------------------------------------------------
  for (const role of ['tech', 'sales', 'installer', 'fabricator']) {
    await test('a ' + role + ' CANNOT add, rename or close a yard', async () => {
      const { handler, calls } = loadHandler({ role: role });
      const res = mockRes();
      await handler(mockReq('write', GOOD), res);
      assert.strictEqual(res.statusCode, 403);
      assert.strictEqual(res.body.error.code, 'FORBIDDEN');
      // Refused BEFORE the database, not after.
      assert.strictEqual(calls.filter(c => c.method === 'POST').length, 0,
        'a refused write still reached the database');
    });
  }
  for (const role of ['owner', 'admin']) {
    await test('an ' + role + ' can write', async () => {
      const { handler } = loadHandler({ role: role });
      const res = mockRes();
      await handler(mockReq('write', GOOD), res);
      assert.strictEqual(res.statusCode, 200);
    });
  }

  await test('a rename by a non-manager is refused -- an upsert relabels every slab pointing at the yard', async () => {
    const { handler, calls } = loadHandler({ role: 'sales' });
    await handler(mockReq('write', { id: 'LOC1', name: 'Renamed By Sales' }), mockRes());
    assert.strictEqual(calls.filter(c => c.method === 'POST').length, 0);
  });

  await test('closing a yard is refused for a non-manager too', async () => {
    const { handler, calls } = loadHandler({ role: 'tech' });
    await handler(mockReq('write', Object.assign({}, GOOD, { active: false })), mockRes());
    assert.strictEqual(calls.filter(c => c.method === 'POST').length, 0);
  });

  // ---- the existing refusals, held so the gate above cannot mask them ------
  for (const blank of ['', '   ', null, undefined]) {
    await test('a yard named ' + JSON.stringify(blank) + ' is REFUSED, not defaulted', async () => {
      const { handler, calls } = loadHandler({});
      const res = mockRes();
      await handler(mockReq('write', Object.assign({}, GOOD, { name: blank })), res);
      assert.strictEqual(res.statusCode, 400);
      assert.strictEqual(res.body.error.code, 'INVALID_LOCATION');
      assert.strictEqual(calls.filter(c => c.method === 'POST').length, 0);
    });
  }
  await test('a missing id is refused', async () => {
    const { handler } = loadHandler({});
    const res = mockRes();
    await handler(mockReq('write', { name: 'No id' }), res);
    assert.strictEqual(res.statusCode, 400);
  });

  // ---- what is actually stored --------------------------------------------
  await test('it upserts on (license_hash, location_id) -- a yard is correctable', async () => {
    const { handler, calls } = loadHandler({});
    await handler(mockReq('write', GOOD), mockRes());
    const post = calls.find(c => c.method === 'POST');
    assert.match(post.url, /on_conflict=license_hash,location_id/);
    assert.match(String(post.headers.Prefer), /merge-duplicates/);
  });

  await test('license_hash comes from the validated licence, never from the body', async () => {
    const { handler, calls } = loadHandler({});
    await handler(mockReq('write', Object.assign({}, GOOD, { license_hash: 'somebody-elses-hash' })), mockRes());
    const sent = JSON.parse(calls.find(c => c.method === 'POST').body);
    assert.strictEqual(sent.license_hash, 'test-hash');
  });

  await test('no DELETE is ever issued -- a closed yard keeps its history', async () => {
    const { handler, calls } = loadHandler({});
    await handler(mockReq('write', Object.assign({}, GOOD, { active: false })), mockRes());
    assert.strictEqual(calls.filter(c => c.method === 'DELETE').length, 0);
  });

  await test('this branch never touches sd_slabs -- attribution lives in the slab, not here', async () => {
    const { handler, calls } = loadHandler({});
    await handler(mockReq('write', GOOD), mockRes());
    assert.ok(calls.every(c => !/sd_slabs/.test(c.url)),
      'the yard registry reached into the slab table');
  });

  // ---- not provisioned -----------------------------------------------------
  await test('an unrun migration reads as an empty list, not an error', async () => {
    const { handler } = loadHandler({ readStatus: 404 });
    const res = mockRes();
    await handler(mockReq('read', null), res);
    assert.strictEqual(res.statusCode, 200);
    assert.deepStrictEqual(res.body.data, []);
    assert.strictEqual(res.body.provisioned, false);
  });

  await test('but an unrun migration on WRITE is a 503 naming the file, not a cheerful 200', async () => {
    // A write has genuinely failed to do the thing asked. A 200 with nothing
    // stored is how a feature looks fine and persists nothing.
    const { handler } = loadHandler({ writeStatus: 404 });
    const res = mockRes();
    await handler(mockReq('write', GOOD), res);
    assert.strictEqual(res.statusCode, 503);
    assert.strictEqual(res.body.error.code, 'NOT_PROVISIONED');
    assert.match(res.body.error.message, /stonedesk_locations_schema\.sql/);
  });

  console.log('\n' + passed + ' assertions passed');
}

main();
