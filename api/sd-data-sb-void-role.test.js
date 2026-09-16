// api/sd-data-sb-void-role.test.js
// REQUIREMENT: voiding or un-voiding a SAIRNbiz purchase order or receipt is
//   refused SERVER-SIDE to any role but Owner and Manager, because the client
//   constant that used to hold that decision was a button and not a control --
//   the endpoint's own gate is a SESSION gate, so a signed-in employee of any
//   role could POST a voided row straight past it
//
// Run:  node api/sd-data-sb-void-role.test.js
//
// ── WHY THIS EXISTS ────────────────────────────────────────────────────────
// Michael's 2026-09-14 decision: Admin/Manager may void. SAIRNbiz has no
// `admin`, so it is owner and manager. It shipped as `SB_VOID_ROLES` in
// sairnbiz.html and nowhere else, and the row recording it said so plainly --
// "a signed-in employee of any role can still POST a voided row directly".
// Excluding a role from the button did not stop that role voiding; it stopped
// them clicking. This suite is about the half that makes the decision true.
//
// ── THE SESSION GATE IS NOT WIDENED, AND THAT IS ASSERTED ─────────────────
// Raising a PO and logging a receipt stay ordinary work for any signed-in
// employee -- the block's own comment argues that, and breaking it would be a
// bigger change than the one decided. Only the VOID TRANSITION is privileged.
// Section 3 drives the ordinary write on a staff session and requires it
// through, so a future widening of the gate fails here rather than silently
// locking staff out of their own work.
//
// ── BOTH DIRECTIONS, AND THE SECOND IS THE ONE A ONE-WAY LOCK MISSES ──────
// The write is a blind upsert of the whole payload, so without reading the
// stored row a staff account could UN-VOID by posting the same id with the
// status removed. A void anybody can undo is not a void. Section 4 is that
// direction.
//
// ── AND THE COULD-NOT-TELL PATH IS A REFUSAL ──────────────────────────────
// If the stored row cannot be read, whether this write clears a void is
// UNKNOWN, and allowing it would be the gate quietly not running (PR 1.11).
// Section 5 drives a failing read and requires 503 VOID_STATE_UNREADABLE with
// nothing written. Section 6 separates that from the NOT-PROVISIONED case,
// which is not an error and must not become one.

'use strict';
const assert = require('assert');

function mockRes() {
  const res = { statusCode: null, body: null };
  res.status = function (c) { res.statusCode = c; return res; };
  res.json = function (b) { res.body = b; return res; };
  return res;
}

function mockReq(resource, payload) {
  return {
    method: 'POST',
    headers: { authorization: 'Bearer SB-TEST-KEY' },
    body: { action: 'write', resource: resource, payload: payload }
  };
}

// A PostgREST stand-in that HONOURS THE id FILTER, for the same reason
// sd-data-slab-reserve.test.js's does: a stub that answers whatever it likes
// cannot tell a gate that reads the stored row from one that does not.
function stubBackend(opts) {
  opts = opts || {};
  const calls = [];
  global.fetch = async (url, init) => {
    const u = String(url);
    const method = (init && init.method) || 'GET';
    calls.push({ url: u, method: method });
    if (method === 'GET') {
      if (opts.readStatus === 404 || opts.readStatus === 400) {
        return { ok: false, status: opts.readStatus, json: async () => ({}) };
      }
      if (opts.readStatus && opts.readStatus >= 500) {
        return { ok: false, status: opts.readStatus, json: async () => ({ message: 'upstream down' }) };
      }
      const wanted = decodeURIComponent(u).match(/(?:po_id|recv_id|ap_id)=eq\.([^&]*)/);
      const row = opts.stored && wanted && String(opts.stored.id) === wanted[1]
        ? [{ data: opts.stored }] : [];
      return { ok: true, status: 200, json: async () => row };
    }
    if (method === 'POST') {
      if (opts.writeStatus === 404 || opts.writeStatus === 400) {
        return { ok: false, status: opts.writeStatus, json: async () => ({}) };
      }
      return { ok: true, status: 200, json: async () => [{ data: JSON.parse(init.body).data }] };
    }
    throw new Error('unexpected method ' + method);
  };
  return calls;
}

function loadHandler(opts) {
  opts = opts || {};
  delete require.cache[require.resolve('./_lib/license')];
  require.cache[require.resolve('./_lib/license')] = {
    exports: {
      validateLicenseKey: async function () {
        return { valid: true, active: true, license_hash: 'test-hash', trial_ends_at: null, stripe_subscription_id: null };
      }
    }
  };
  // Object.assign over the REAL module on purpose: ROLES_BY_APP has to be the
  // shipped list, because the handler filters its void-role constant against
  // it and a hand-written copy here could not catch a role that stops existing.
  const realAuth = require('./_lib/auth');
  delete require.cache[require.resolve('./_lib/auth')];
  require.cache[require.resolve('./_lib/auth')] = {
    exports: Object.assign({}, realAuth, {
      tokenFromRequest: function () { return 'tok'; },
      verifySessionToken: function () {
        return opts.noSession ? null : { employee_id: 'emp-1', role: opts.role || 'staff', app: 'sairnbiz' };
      }
    })
  };
  delete require.cache[require.resolve('./sd-data.js')];
  return require('./sd-data.js');
}

const VOID_ROW = { id: 'PO-1', vendor: 'Stone World', amt: 1200, status: 'Void', void_reason: 'raised twice' };
const OPEN_ROW = { id: 'PO-1', vendor: 'Stone World', amt: 1200 };

let passed = 0;
async function test(name, fn) {
  try { await fn(); passed++; console.log('  ok   ' + name); }
  catch (e) { console.error('  FAIL ' + name + '\n       ' + e.message); process.exitCode = 1; }
}

async function main() {
  console.log('api/sd-data.js -- sb_po/sb_recv: voiding is a role act, server-side\n');
  process.env.SUPABASE_URL = 'https://test.supabase.co';
  process.env.SUPABASE_SERVICE_ROLE_KEY = 'test-key';

  console.log('1. SETTING a void');
  for (const role of ['staff', 'accounting', 'hr']) {
    await test(role + ' cannot void a purchase order -> 403, and nothing is written', async () => {
      const calls = stubBackend({});
      const res = mockRes();
      await loadHandler({ role: role })(mockReq('sb_po', VOID_ROW), res);
      assert.strictEqual(res.statusCode, 403, 'expected 403, got ' + res.statusCode);
      assert.strictEqual(res.body.error.code, 'VOID_ROLE_REQUIRED');
      assert.ok(/Voiding/.test(res.body.error.message), 'the refusal names the direction');
      assert.strictEqual(calls.filter((c) => c.method === 'POST').length, 0,
        'a refused void must not reach the table');
    });
  }
  // `accounting` is the role the whole open question is about, and it is
  // refused today by the decision as written. If that decision changes, THIS
  // arm is where it changes, rather than one constant moving unnoticed.
  await test('...and accounting is refused by the DECISION, not by an accident', async () => {
    const res = mockRes();
    stubBackend({});
    await loadHandler({ role: 'accounting' })(mockReq('sb_recv', { id: 'R-1', status: 'Void' }), res);
    assert.strictEqual(res.statusCode, 403);
    assert.ok(/receipt/.test(res.body.error.message), 'the refusal names the document');
  });

  for (const role of ['owner', 'manager']) {
    await test(role + ' CAN void, and it reaches the table', async () => {
      const calls = stubBackend({});
      const res = mockRes();
      await loadHandler({ role: role })(mockReq('sb_po', VOID_ROW), res);
      assert.strictEqual(res.statusCode, 200, 'expected 200, got ' + res.statusCode
        + ' ' + JSON.stringify(res.body));
      assert.strictEqual(calls.filter((c) => c.method === 'POST').length, 1);
    });
  }

  await test('setting a void costs NO extra read -- only the clear direction needs one', async () => {
    const calls = stubBackend({});
    const res = mockRes();
    await loadHandler({ role: 'owner' })(mockReq('sb_po', VOID_ROW), res);
    assert.strictEqual(res.statusCode, 200);
    assert.strictEqual(calls.filter((c) => c.method === 'GET').length, 0,
      'a void-setting write should not re-read the stored row');
  });

  console.log('\n2. the resource scope');
  await test('sb_ap is NOT voidable and is untouched -- staff writes it with a status', async () => {
    const calls = stubBackend({});
    const res = mockRes();
    await loadHandler({ role: 'staff' })(mockReq('sb_ap', { id: 'AP-1', status: 'Void' }), res);
    assert.strictEqual(res.statusCode, 200, 'the gate must be scoped to sb_po and sb_recv');
    assert.strictEqual(calls.filter((c) => c.method === 'GET').length, 0);
  });

  console.log('\n3. the SESSION gate is not widened');
  await test('staff CAN write an ordinary, unvoided purchase order', async () => {
    const calls = stubBackend({ stored: OPEN_ROW });
    const res = mockRes();
    await loadHandler({ role: 'staff' })(mockReq('sb_po', OPEN_ROW), res);
    assert.strictEqual(res.statusCode, 200, 'raising a PO is ordinary work; got ' + res.statusCode
      + ' ' + JSON.stringify(res.body));
    assert.strictEqual(calls.filter((c) => c.method === 'POST').length, 1);
  });
  await test('staff CAN write a purchase order that does not exist yet', async () => {
    const res = mockRes();
    stubBackend({ stored: null });
    await loadHandler({ role: 'staff' })(mockReq('sb_po', { id: 'PO-NEW', vendor: 'Atlas' }), res);
    assert.strictEqual(res.statusCode, 200);
  });
  await test('no session is still 401, not 403 -- the existing gate is intact', async () => {
    const res = mockRes();
    stubBackend({});
    await loadHandler({ noSession: true })(mockReq('sb_po', VOID_ROW), res);
    assert.strictEqual(res.statusCode, 401);
    assert.strictEqual(res.body.error.code, 'NO_SESSION');
  });

  console.log('\n4. CLEARING a void -- the direction a one-way lock misses');
  await test('staff cannot UN-VOID by posting the row without its status', async () => {
    const calls = stubBackend({ stored: VOID_ROW });
    const res = mockRes();
    await loadHandler({ role: 'staff' })(mockReq('sb_po', OPEN_ROW), res);
    assert.strictEqual(res.statusCode, 403, 'expected 403, got ' + res.statusCode);
    assert.strictEqual(res.body.error.code, 'VOID_ROLE_REQUIRED');
    assert.ok(/Un-voiding/.test(res.body.error.message), 'the refusal names the direction');
    assert.strictEqual(calls.filter((c) => c.method === 'POST').length, 0);
  });
  await test('...and the stored row really was read to find that out', async () => {
    const calls = stubBackend({ stored: VOID_ROW });
    const res = mockRes();
    await loadHandler({ role: 'staff' })(mockReq('sb_po', OPEN_ROW), res);
    assert.strictEqual(res.statusCode, 403);
    const gets = calls.filter((c) => c.method === 'GET');
    assert.strictEqual(gets.length, 1, 'expected exactly one stored-state read');
    assert.ok(/po_id=eq\.PO-1/.test(decodeURIComponent(gets[0].url)),
      'the read must be filtered to this row, not the whole table');
  });
  await test('owner CAN un-void', async () => {
    const res = mockRes();
    stubBackend({ stored: VOID_ROW });
    await loadHandler({ role: 'owner' })(mockReq('sb_po', OPEN_ROW), res);
    assert.strictEqual(res.statusCode, 200, 'got ' + res.statusCode + ' ' + JSON.stringify(res.body));
  });
  // THE LABEL ON THIS ARM WAS WRONG BEFORE IT WAS CHECKED. It read "a void
  // REWRITTEN as a void is not a transition -- staff may correct the reason",
  // and the assertion under it required 403. The assertion is right and the
  // label was describing a design that was not built: an incoming Void is
  // treated as a void-SETTING write whatever was stored, so rewriting the
  // reason stays privileged. Corrected rather than left, because an arm whose
  // label contradicts its assertion is the same defect as one that names the
  // wrong cause -- the next reader believes the sentence.
  await test('rewriting a void row -- still Void -- stays privileged, reason edits included', async () => {
    const res = mockRes();
    stubBackend({ stored: VOID_ROW });
    await loadHandler({ role: 'staff' })(
      mockReq('sb_po', Object.assign({}, VOID_ROW, { void_reason: 'typo fixed' })), res);
    assert.strictEqual(res.statusCode, 403,
      'a still-void write is a void-SETTING write by this gate and stays privileged');
  });

  console.log('\n5. COULD NOT TELL is a refusal, not a pass');
  await test('an unreadable stored row refuses with VOID_STATE_UNREADABLE', async () => {
    const calls = stubBackend({ stored: VOID_ROW, readStatus: 500 });
    const res = mockRes();
    await loadHandler({ role: 'staff' })(mockReq('sb_po', OPEN_ROW), res);
    assert.strictEqual(res.statusCode, 503, 'expected 503, got ' + res.statusCode);
    assert.strictEqual(res.body.error.code, 'VOID_STATE_UNREADABLE');
    assert.strictEqual(calls.filter((c) => c.method === 'POST').length, 0,
      'a write whose void state is unknown must not land');
  });
  await test('...and it says the write was refused rather than allowed', async () => {
    const res = mockRes();
    stubBackend({ readStatus: 503 });
    await loadHandler({ role: 'staff' })(mockReq('sb_recv', { id: 'R-1' }), res);
    assert.strictEqual(res.body.error.code, 'VOID_STATE_UNREADABLE');
    assert.ok(/refused rather than allowed/i.test(res.body.error.message));
  });

  console.log('\n6. NOT PROVISIONED is not an error and must not become one');
  await test('a 404 on the stored read means no row, so the write proceeds and answers NOT_PROVISIONED', async () => {
    const res = mockRes();
    stubBackend({ readStatus: 404, writeStatus: 404 });
    await loadHandler({ role: 'staff' })(mockReq('sb_po', OPEN_ROW), res);
    assert.strictEqual(res.statusCode, 503);
    assert.strictEqual(res.body.error.code, 'NOT_PROVISIONED',
      'an unmigrated table must not read as a void-state failure');
  });

  console.log('\n' + passed + ' assertion(s) passed');
}

main();
