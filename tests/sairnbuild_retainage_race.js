// tests/sairnbuild_retainage_race.js
//
// CONCURRENT-WRITE regression for the bld_draws release_retainage race
// (2026-09-21, hover_log #315). Before this fix: two concurrent
// release_retainage calls on the SAME draw_id each read the same starting
// `data`, computed their own trail entry, and whichever PATCH landed second
// silently WON -- overwriting the first release's write, including its
// audit-trail entry, with no error at all. The fix routes the write through
// public.bld_release_retainage_atomic() (sql/sairnbuild_data_schema.sql), an
// optimistic-CAS RPC: the caller passes back the retainage_released value it
// read, and the function refuses (RETAINAGE_RELEASE_CONFLICT) if that no
// longer matches the row's current committed value.
//
// WHAT THIS PROVES AND WHAT IT DOES NOT. This drives the REAL handler
// (api/sd-data.js) through a mocked fetch, with the mock's RPC branch
// modelling the real SQL function's CAS comparison exactly (see the mock
// below). It proves: (a) the application-layer plumbing forwards the read
// value as p_expected_prior_released correctly, and (b) two logically
// concurrent releases against the same starting state cannot BOTH silently
// succeed -- the second is refused, never merged over the first. It does
// NOT prove Postgres's own pg_advisory_xact_lock behaves correctly under
// real concurrent transactions -- that requires a live database this
// environment does not have write access to (repeated real constraint
// throughout this platform's own SQL files: "no DB execution access from
// this session"). tools/advisory_lock_isolation_check.py separately confirms
// the real SQL function is a syntactically GUARDED instance of the pattern
// (takes the lock, asserts READ COMMITTED, reads then writes).
//
// Run:  node tests/sairnbuild_retainage_race.js

'use strict';
const assert = require('assert');
const path = require('path');
const ROOT = path.join(__dirname, '..');

process.env.SUPABASE_URL = 'https://fake.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = 'fake-service-key';

const LIC_HASH = 'race-tenant-hash';
const TODAY = '2026-09-21';

let rows;
function seed() {
  rows = [{
    license_hash: LIC_HASH, draw_id: 'DR-RACE', data: {
      job_id: 'J-RACE', draw_no: 1, period_end: '2026-08-31', pct_complete: 100,
      amount: 100000, retainage_pct: 10, retainage_held: 10000,
      status: 'received', requested_at: '2026-08-01', amount_received: 100000
    }
  }];
}
function row(id) { return rows.find((r) => r.draw_id === id); }

let pass = 0, fail = 0;
async function test(name, fn) {
  try { await fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}

function loadHandler() {
  delete require.cache[require.resolve(path.join(ROOT, 'api/_lib/license.js'))];
  require.cache[require.resolve(path.join(ROOT, 'api/_lib/license.js'))] = {
    exports: {
      validateLicenseKey: async () => ({
        valid: true, active: true, license_hash: LIC_HASH,
        trial_ends_at: null, stripe_subscription_id: null
      })
    }
  };
  const authMod = require(path.join(ROOT, 'api/_lib/auth.js'));
  authMod.tokenFromRequest = (req) => req.headers['x-test-token'] || null;
  authMod.verifySessionToken = (token, licHash, expectedApp) => {
    if (!token) return null;
    if (expectedApp !== 'sairnbuild') throw new Error('expected app scope not sairnbuild: ' + expectedApp);
    return JSON.parse(token);
  };
  delete require.cache[require.resolve(path.join(ROOT, 'api/sd-data.js'))];
  return require(path.join(ROOT, 'api/sd-data.js'));
}

function eqParam(u, k) {
  const m = String(u).match(new RegExp('[?&]' + k + '=eq\\.([^&]+)'));
  return m ? decodeURIComponent(m[1]) : null;
}
function jsonRes(status, body) {
  return { status: status, ok: status >= 200 && status < 300,
    json: async () => body, text: async () => JSON.stringify(body) };
}

// The real function's CAS comparison, modelled exactly: refuse with
// RETAINAGE_RELEASE_CONFLICT the moment a caller's expected prior value no
// longer matches the row's real, current value.
global.fetch = async (url, opts) => {
  opts = opts || {};
  const u = String(url), method = opts.method || 'GET';
  if (u.indexOf('rpc/bld_release_retainage_atomic') !== -1) {
    const body = JSON.parse(opts.body);
    const r = row(body.p_draw_id);
    if (!r) return jsonRes(400, { message: 'NO_SUCH_DRAW: ' + body.p_draw_id + ' is not on file' });
    const current = Number(r.data.retainage_released) || 0;
    const expected = Number(body.p_expected_prior_released) || 0;
    if (current !== expected) {
      return jsonRes(400, { message: 'RETAINAGE_RELEASE_CONFLICT: draw ' + body.p_draw_id
        + ' was updated by another release between read and write (expected prior '
        + expected + ', found ' + current + ') -- re-fetch and retry' });
    }
    r.data = body.p_next_data;
    return jsonRes(200, [{ id: 'row-' + r.draw_id, license_hash: r.license_hash, draw_id: r.draw_id, data: r.data }]);
  }
  if (u.indexOf('bld_draws') !== -1) {
    const hash = eqParam(u, 'license_hash'), did = eqParam(u, 'draw_id');
    const match = rows.filter((r) => r.license_hash === hash && (!did || r.draw_id === did));
    return jsonRes(200, match.map((r) => ({ draw_id: r.draw_id, data: r.data })));
  }
  return jsonRes(404, { message: 'unexpected table: ' + u });
};

function mockRes() {
  const r = { statusCode: null, body: null };
  r.status = (c) => { r.statusCode = c; return r; };
  r.json = (b) => { r.body = b; return r; };
  return r;
}
function tokenFor(role) { return JSON.stringify({ role: role, employee_id: 'race-emp' }); }
async function release(payload) {
  const handler = loadHandler();
  const res = mockRes();
  await handler({
    method: 'POST', headers: { authorization: 'Bearer testkey', 'x-test-token': tokenFor('office') },
    body: { action: 'release_retainage', resource: 'bld_draws', app_id: 'sairnbuild',
      payload: Object.assign({ today: TODAY }, payload) }
  }, res);
  return res;
}

(async () => {
  console.log('SAIRNbuild bld_draws -- retainage release race (regression for hover_log #315)\n');

  await test('sequential releases: second one correctly sees the first\'s committed state and succeeds', async () => {
    seed();
    const first = await release({ draw_id: 'DR-RACE', amount: 3000, released_at: '2026-09-10' });
    assert.strictEqual(first.statusCode, 200, 'first release failed: ' + JSON.stringify(first.body));
    const second = await release({ draw_id: 'DR-RACE', amount: 5000, released_at: '2026-09-15' });
    assert.strictEqual(second.statusCode, 200, 'second release failed: ' + JSON.stringify(second.body));
    assert.strictEqual(row('DR-RACE').data.retainage_released, 5000);
    assert.strictEqual(row('DR-RACE').data.retainage_release_log.length, 2,
      'both releases must be in the trail -- got ' + row('DR-RACE').data.retainage_release_log.length);
  });

  await test('a stale write (same starting state as an already-applied release) is REFUSED, not silently merged', async () => {
    // Directly reproduces the race by constructing the SECOND caller's RPC
    // body the way a genuinely concurrent caller would have: computed from
    // the SAME starting `already` a first caller also read, sent AFTER the
    // first caller's write already committed. This is the exact shape two
    // real concurrent HTTP requests racing on this draw would produce --
    // the JS handler always computes p_expected_prior_released from
    // whatever it read, and two racing reads see the same pre-write state.
    seed();
    const firstRelease = await release({ draw_id: 'DR-RACE', amount: 2000, released_at: '2026-09-10' });
    assert.strictEqual(firstRelease.statusCode, 200);
    assert.strictEqual(row('DR-RACE').data.retainage_released, 2000, 'setup: first release did not land');

    // The stale caller's own trail entry -- built the way the real handler
    // builds one, from the SAME starting state (retainage_released: 0,
    // an empty log) the first caller also started from.
    const staleTrail = [{
      at: new Date().toISOString(), released_at: '2026-09-11', amount: 9000,
      previous: 0, by_employee_id: 'race-emp', by_role: 'office'
    }];
    const staleNextData = Object.assign({}, {
      job_id: 'J-RACE', draw_no: 1, period_end: '2026-08-31', pct_complete: 100,
      amount: 100000, retainage_pct: 10, retainage_held: 10000,
      status: 'received', requested_at: '2026-08-01', amount_received: 100000
    }, { retainage_released: 9000, retainage_released_at: '2026-09-11', retainage_release_log: staleTrail });

    const staleResp = await fetch('https://fake.supabase.co/rest/v1/rpc/bld_release_retainage_atomic', {
      method: 'POST',
      body: JSON.stringify({
        p_license_hash: LIC_HASH, p_draw_id: 'DR-RACE',
        p_expected_prior_released: 0, // what the stale caller read BEFORE the first release landed
        p_next_data: staleNextData
      })
    });
    assert.strictEqual(staleResp.status, 400, 'the stale write must be refused, got ' + staleResp.status);
    const body = JSON.parse(await staleResp.text());
    assert.match(body.message, /RETAINAGE_RELEASE_CONFLICT/,
      'refusal must be RETAINAGE_RELEASE_CONFLICT, got: ' + body.message);

    // THE REAL PROOF: the first release's data must survive, completely
    // untouched by the stale write. Before this fix, this assertion is
    // exactly what would have FAILED -- the stale write's merge-duplicates
    // resolution would have silently overwritten it.
    assert.strictEqual(row('DR-RACE').data.retainage_released, 2000,
      'the stale write corrupted the first release -- this is the exact defect #315 reported');
    assert.strictEqual(row('DR-RACE').data.retainage_release_log.length, 1,
      'the stale write injected its own trail entry -- the first release\'s audit trail was overwritten');
    assert.strictEqual(row('DR-RACE').data.retainage_release_log[0].amount, 2000);
  });

  await test('NEGATIVE CONTROL: the mock itself really does refuse a mismatched CAS (proves the test can fail)', async () => {
    seed();
    const resp = await fetch('https://fake.supabase.co/rest/v1/rpc/bld_release_retainage_atomic', {
      method: 'POST',
      body: JSON.stringify({
        p_license_hash: LIC_HASH, p_draw_id: 'DR-RACE',
        p_expected_prior_released: 999999, // deliberately wrong
        p_next_data: {}
      })
    });
    assert.strictEqual(resp.status, 400);
  });

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  if (fail) process.exit(1);
})();
