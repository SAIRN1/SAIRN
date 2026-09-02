// api/sd-data-approvals.test.js
// Plain node:assert tests. Run: node api/sd-data-approvals.test.js
//
// esigApprove() in stonedesk.html has always captured a REAL signature -- typed
// name, a canvas checked for being genuinely blank, the agreed total and the
// 50% deposit. It wrote all of it to localStorage['sd_approvals'] AND NOWHERE
// ELSE, read back from nowhere in the entire file. The document proving a
// customer agreed to a price lived in one browser and died with its cache.
//
// (That is also a correction to the 2026-09-02 competitive audit, whose GAP 5
// said StoneDesk could not get a customer to e-sign a quote. It could. The
// signature just had nowhere to go.)
//
// Two properties are load-bearing here and both are asserted below:
//   APPEND-ONLY -- a signed price must not be editable, so a duplicate id is a
//   409 and there is no update path at all; and
//   NO $0 APPROVALS -- with no quote loaded the estimate total rendered as an
//   em-dash, which parsed to zero, so a customer could sign a $0 agreement and
//   it saved without a word.

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
    body: { action: action, resource: 'sd_approvals', payload: payload }
  };
}

let passed = 0;
async function test(name, fn) {
  try { await fn(); passed++; console.log('  ok - ' + name); }
  catch (e) { console.error('  FAIL - ' + name + '\n    ' + e.message); process.exitCode = 1; }
}

// `upstream` is the PostgREST stand-in: `status` is what it answers a write
// with, `rows` what it answers a read with.
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
        return opts.noSession ? null : { employee_id: opts.employeeId || 'emp-7', role: opts.role || 'sales' };
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
    return { ok: st < 300, status: st, json: async () => (st < 300 ? [{ approval_id: JSON.parse(init.body).approval_id }] : {}) };
  };
  delete require.cache[require.resolve('./sd-data.js')];
  return { handler: require('./sd-data.js'), calls: calls };
}

const GOOD = {
  approval_id: 'APPR1788360000000',
  client_name: 'Ruiz kitchen',
  quote_num: 'Q-118',
  signed_date: '2026-09-02',
  total_amount: 12400,
  deposit_amount: 6200,
  signature_png: 'data:image/png;base64,AAAA'
};

async function main() {
  console.log('api/sd-data.js -- sd_approvals: append-only, session-gated, no $0 approvals');
  process.env.SUPABASE_URL = 'https://test.supabase.co';
  process.env.SUPABASE_SERVICE_ROLE_KEY = 'test-key';

  await test('no session -> 403 on write', async () => {
    const { handler } = loadHandler({ noSession: true });
    const res = mockRes();
    await handler(mockReq('write', GOOD), res);
    assert.strictEqual(res.statusCode, 403);
    assert.strictEqual(res.body.error.code, 'FORBIDDEN');
  });

  await test('no session -> 403 on read too', async () => {
    const { handler } = loadHandler({ noSession: true });
    const res = mockRes();
    await handler(mockReq('read', {}), res);
    assert.strictEqual(res.statusCode, 403);
  });

  // -- the $0 signature -----------------------------------------------------
  for (const bad of [0, -5, null, undefined, 'lots', NaN]) {
    await test('a total of ' + JSON.stringify(bad) + ' is refused -- nobody signs a priceless agreement', async () => {
      const { handler, calls } = loadHandler({});
      const res = mockRes();
      await handler(mockReq('write', Object.assign({}, GOOD, { total_amount: bad })), res);
      assert.strictEqual(res.statusCode, 400);
      assert.strictEqual(res.body.error.code, 'NO_TOTAL');
      assert.strictEqual(calls.filter(c => c.method === 'POST').length, 0, 'it wrote anyway');
    });
  }

  await test('a deposit larger than the total is refused', async () => {
    const { handler } = loadHandler({});
    const res = mockRes();
    await handler(mockReq('write', Object.assign({}, GOOD, { deposit_amount: 99999 })), res);
    assert.strictEqual(res.statusCode, 400);
    assert.strictEqual(res.body.error.code, 'BAD_DEPOSIT');
  });

  await test('a missing client name is refused', async () => {
    const { handler } = loadHandler({});
    const res = mockRes();
    await handler(mockReq('write', Object.assign({}, GOOD, { client_name: '  ' })), res);
    assert.strictEqual(res.statusCode, 400);
    assert.strictEqual(res.body.error.code, 'NO_CLIENT');
  });

  await test('a missing approval id is refused', async () => {
    const { handler } = loadHandler({});
    const res = mockRes();
    await handler(mockReq('write', Object.assign({}, GOOD, { approval_id: '' })), res);
    assert.strictEqual(res.statusCode, 400);
    assert.strictEqual(res.body.error.code, 'NO_APPROVAL_ID');
  });

  await test('an oversized signature is REFUSED by the uniform 64KB cap, not truncated', async () => {
    // Half a signature still looks like a signature. This handler already caps
    // EVERY write at 64KB near the top of the file, so a signature that does
    // not fit is refused there -- 413, before any database call.
    //
    // A first draft added a SECOND check here at 200KB. It could never fire,
    // because 200KB > 64KB, and this assertion is what found it: it expected
    // 400 and got 413. A cap that never fires is worse than none, because it
    // reads as protection.
    const { handler, calls } = loadHandler({});
    const res = mockRes();
    await handler(mockReq('write', Object.assign({}, GOOD, { signature_png: 'x'.repeat(70000) })), res);
    assert.strictEqual(res.statusCode, 413);
    assert.strictEqual(res.body.error.code, 'PAYLOAD_TOO_LARGE');
    assert.strictEqual(calls.filter(c => c.method === 'POST').length, 0, 'it wrote anyway');
  });

  await test('and no second, unreachable signature cap was left behind', async () => {
    const fs = require('fs');
    const src = fs.readFileSync(require.resolve('./sd-data.js'), 'utf8');
    assert.ok(!/SIGNATURE_TOO_LARGE/.test(src),
      'a dead second cap is back in api/sd-data.js');
  });

  await test('the client measures against the REAL 64KB budget before sending', async () => {
    const fs = require('fs');
    const path = require('path');
    const html = fs.readFileSync(path.join(__dirname, '..', 'stonedesk.html'), 'utf8');
    assert.match(html, /var SD_APPROVAL_MAX_BYTES = 64 \* 1024;/);
    assert.match(html, /Ask the customer to sign again with a simpler mark/);
  });

  await test('validation runs BEFORE the database, so it is identical un-provisioned', async () => {
    const { handler, calls } = loadHandler({ writeStatus: 404 });
    const res = mockRes();
    await handler(mockReq('write', Object.assign({}, GOOD, { total_amount: 0 })), res);
    assert.strictEqual(res.body.error.code, 'NO_TOTAL', 'a missing table masked a bad payload');
    assert.strictEqual(calls.filter(c => c.method === 'POST').length, 0);
  });

  // -- append-only ----------------------------------------------------------
  await test('a valid approval is written', async () => {
    const { handler } = loadHandler({});
    const res = mockRes();
    await handler(mockReq('write', GOOD), res);
    assert.strictEqual(res.statusCode, 200);
    assert.strictEqual(res.body.ok, true);
  });

  await test('THE INSERT IS PLAIN -- an upsert would make a signed price editable', async () => {
    const { handler, calls } = loadHandler({});
    await handler(mockReq('write', GOOD), mockRes());
    const post = calls.find(c => c.method === 'POST');
    assert.ok(post, 'no insert issued');
    assert.ok(!/merge-duplicates/.test(String(post.headers.Prefer || '')),
      'the insert was an upsert: ' + post.headers.Prefer);
    assert.ok(!/on_conflict/.test(post.url), 'the insert declared on_conflict: ' + post.url);
  });

  await test('a duplicate approval id -> 409, and says to sign a new one', async () => {
    const { handler } = loadHandler({ writeStatus: 409 });
    const res = mockRes();
    await handler(mockReq('write', GOOD), res);
    assert.strictEqual(res.statusCode, 409);
    assert.strictEqual(res.body.error.code, 'ALREADY_RECORDED');
    assert.match(res.body.error.message, /not editable/);
  });

  await test('signed_by comes from the SESSION, never from the body', async () => {
    // Who was present when a customer signed is not a field the client asserts.
    const { handler, calls } = loadHandler({ employeeId: 'emp-real' });
    await handler(mockReq('write', Object.assign({}, GOOD, { signed_by: 'emp-forged' })), mockRes());
    const sent = JSON.parse(calls.find(c => c.method === 'POST').body);
    assert.strictEqual(sent.signed_by, 'emp-real');
  });

  await test('license_hash is stamped server-side and cannot be sent in', async () => {
    const { handler, calls } = loadHandler({});
    await handler(mockReq('write', Object.assign({}, GOOD, { license_hash: 'someone-elses' })), mockRes());
    const sent = JSON.parse(calls.find(c => c.method === 'POST').body);
    assert.strictEqual(sent.license_hash, 'test-hash');
  });

  // -- provisioning ---------------------------------------------------------
  await test('un-run migration: a WRITE is a 503 naming the file, not a cheerful 200', async () => {
    const { handler } = loadHandler({ writeStatus: 404 });
    const res = mockRes();
    await handler(mockReq('write', GOOD), res);
    assert.strictEqual(res.statusCode, 503);
    assert.strictEqual(res.body.error.code, 'NOT_PROVISIONED');
    assert.match(res.body.error.message, /sd_approvals_schema\.sql/);
  });

  await test('un-run migration: a READ is 200 with provisioned:false', async () => {
    // A read genuinely has nothing to report; a write failed to do the thing.
    const { handler } = loadHandler({ readStatus: 404 });
    const res = mockRes();
    await handler(mockReq('read', {}), res);
    assert.strictEqual(res.statusCode, 200);
    assert.strictEqual(res.body.provisioned, false);
    assert.deepStrictEqual(res.body.data, []);
  });

  await test('a read returns the rows, newest first', async () => {
    const { handler, calls } = loadHandler({ rows: [{ approval_id: 'A2' }, { approval_id: 'A1' }] });
    const res = mockRes();
    await handler(mockReq('read', {}), res);
    assert.strictEqual(res.statusCode, 200);
    assert.strictEqual(res.body.data.length, 2);
    assert.ok(calls[0].url.includes('order=created_at.desc'), 'no ordering asked for: ' + calls[0].url);
  });

  console.log('\n' + (process.exitCode ? 'FAILURES ABOVE' : 'ALL ' + passed + ' APPROVAL ASSERTIONS PASS'));
}

main();
