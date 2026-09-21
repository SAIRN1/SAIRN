// api/_lib/sairnbuild-retainage-endpoint.test.js
//
// Run:  node api/_lib/sairnbuild-retainage-endpoint.test.js
//
// Round-trip tests for the `wip` and `release_retainage` actions on
// `bld_draws` in api/sd-data.js, through the REAL handler with a stubbed
// Supabase.
//
// ── WHAT THIS GUARDS ──────────────────────────────────────────────────────
// Competitive-gap audit B2 (docs/superpowers/specs/2026-09-03-...): SAIRNbuild
// held retainage on every draw and had NO PATH TO RELEASE IT. The audit's own
// sentence is "money can go in and never come out", and the Draw Requests
// board therefore showed a LIFETIME ACCRUAL under a label that reads as a
// current balance.
//
// The three things that can silently go wrong in the fix, and the sections
// that pin each:
//
//   1. THE ENGINE STOPS BEING THE ENGINE. api/_lib/wip-accounting.js owns
//      held / released / outstanding and owns the refusals. A future edit that
//      re-derives any of it locally would keep every arm green unless the
//      suite asserts the figures come out DIFFERENT from what the stored
//      columns say. Section 2 seeds a deliberately WRONG `retainage_held` on
//      every row for exactly that reason -- a branch reading the stored field
//      fails immediately.
//
//   2. A DRAW NOBODY PRICED GETS FOLDED IN AS ZERO. "Nothing is held" and
//      "nobody recorded what is held" are different facts, and averaging them
//      understates what a contractor is owed. Section 2 asserts the
//      uncomputable draw is EXCLUDED AND COUNTED.
//
//   3. THE RELEASE STOPS BEING AN EVENT. A release is a contractual moment
//      that gets disputed, so it must refuse to go backwards and must leave a
//      who/when/how-much trail. Section 4 pins both, including the
//      append-only-ness of the trail across two releases.
//
// ── THE NEGATIVE CONTROL IS EXTERNAL AND IS RECORDED IN THE WORK LOG ──────
// Run against the pre-fix tree (`git stash` of api/sd-data.js and
// api/_resources/sairnbuild.js), every arm that exercises either new action
// must fail at the action gate with "action must be 'read' or 'write'".
// A suite that is green on the code it was written to reject asserts nothing;
// measured both ways before this file was committed.

const assert = require('assert');

process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET || 'test-secret-for-bld-retainage';
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://stub.test';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'k';

const { signSessionToken } = require('./auth');
const { hashLicense } = require('./license');

// THE HASH IS DERIVED, NOT BORROWED. api/_lib/license.js hashes the BEARER
// KEY; a token signed against a literal license_hash verifies in isolation and
// is then rejected by the handler with an indistinguishable NO_SESSION.
const KEY = 'BLD-RETAINAGE-TEST-KEY';
const LIC_HASH = hashLicense(KEY);
const OTHER_TENANT_HASH = hashLicense('BLD-SOMEBODY-ELSE');

const TODAY = '2026-09-15';

let pass = 0, fail = 0;
async function test(name, fn) {
  try { await fn(); pass += 1; console.log('  ok   - ' + name); }
  catch (e) { fail += 1; console.log('  FAIL - ' + name + '\n         ' + (e && e.message)); }
}
function section(t) { console.log('\n' + t); }

function mockRes() {
  const res = { statusCode: null, body: null };
  res.status = function (c) { res.statusCode = c; return res; };
  res.json = function (p) { res.body = p; return res; };
  return res;
}
function tokenFor(role, app) {
  return signSessionToken({
    app: app || 'sairnbuild', employee_id: 'emp-' + role, role: role, license_hash: LIC_HASH
  });
}

// ── The stubbed store ─────────────────────────────────────────────────────
// `retainage_held` is seeded WRONG on purpose on every row. It is a real
// column on the real table (sairnbuild.html stores both pct and held, which
// the engine header calls out as the thing that can disagree the moment
// anyone edits one), so a branch that reads it instead of deriving from the
// percentage is not a hypothetical.
let rows = [];
let requests = [];
let provisioned = true;

function seed() {
  rows = [
    { license_hash: LIC_HASH, draw_id: 'DR-01', data: {
      job_id: 'J-2601', draw_no: 1, period_end: '2026-06-30', pct_complete: 35,
      amount: 45000, retainage_pct: 10, retainage_held: 999999,
      status: 'received', requested_at: '2026-07-01', amount_received: 40500,
      notes: 'first draw' } },
    { license_hash: LIC_HASH, draw_id: 'DR-02', data: {
      job_id: 'J-2602', draw_no: 2, period_end: '2026-07-31', pct_complete: 55,
      amount: 78000, retainage_pct: 10, retainage_held: 999999,
      status: 'requested', requested_at: '2026-08-01', amount_received: 0,
      notes: 'awaiting owner approval' } },
    // NOBODY PRICED THIS ONE. Not "nothing is held" -- unknown.
    { license_hash: LIC_HASH, draw_id: 'DR-03', data: {
      job_id: 'J-2603', draw_no: 1, period_end: '2026-08-31', pct_complete: 20,
      amount: 20000, status: 'draft', notes: 'no retainage recorded' } },
    // Another tenant's draw, same draw_id as one of ours on purpose.
    { license_hash: OTHER_TENANT_HASH, draw_id: 'DR-99', data: {
      job_id: 'J-9901', amount: 10000, retainage_pct: 10, status: 'received' } }
  ];
  requests = [];
  provisioned = true;
}
function row(id, hash) {
  return rows.filter((r) => r.draw_id === id && r.license_hash === (hash || LIC_HASH))[0];
}
function eqParam(u, k) {
  const m = String(u).match(new RegExp('[?&]' + k + '=eq\\.([^&]+)'));
  return m ? decodeURIComponent(m[1]) : null;
}
function jsonRes(status, body) {
  return Promise.resolve({
    status: status, ok: status >= 200 && status < 300,
    json: () => Promise.resolve(body),
    text: () => Promise.resolve(JSON.stringify(body))
  });
}

const FETCH = function (url, opts) {
  opts = opts || {};
  const u = String(url), method = opts.method || 'GET';
  requests.push({ url: u, method: method, body: opts.body ? JSON.parse(opts.body) : null });

  // bld_release_retainage_atomic RPC (2026-09-21 fix for hover_log #315).
  // Simulates the real Postgres function's optimistic-CAS behaviour: refuse
  // with RETAINAGE_RELEASE_CONFLICT if the row's current retainage_released
  // no longer matches what the caller read before computing its write (the
  // exact race this fix closes), refuse with NO_SUCH_DRAW if the row is
  // gone, else replace `data` wholesale -- same effect as the real
  // `set data = p_next_data` the function performs under its lock.
  if (u.indexOf('rpc/bld_release_retainage_atomic') !== -1) {
    if (!provisioned) return jsonRes(400, { message: 'relation "public.bld_draws" does not exist' });
    const body = JSON.parse(opts.body);
    const r = row(body.p_draw_id, body.p_license_hash);
    if (!r) return jsonRes(400, { message: 'NO_SUCH_DRAW: ' + body.p_draw_id + ' is not on file' });
    const current = Number(r.data && r.data.retainage_released) || 0;
    const expected = Number(body.p_expected_prior_released) || 0;
    if (current !== expected) {
      return jsonRes(400, { message: 'RETAINAGE_RELEASE_CONFLICT: draw ' + body.p_draw_id
        + ' was updated by another release between read and write (expected prior '
        + expected + ', found ' + current + ') -- re-fetch and retry' });
    }
    r.data = body.p_next_data;
    return jsonRes(200, [{ id: 'row-' + r.draw_id, license_hash: r.license_hash, draw_id: r.draw_id, data: r.data }]);
  }

  if (u.indexOf('bld_draws') === -1) return jsonRes(404, { message: 'unexpected table: ' + u });
  // An unprovisioned table is what PostgREST actually answers with.
  if (!provisioned) return jsonRes(404, { message: 'relation "public.bld_draws" does not exist' });

  const hash = eqParam(u, 'license_hash');
  const did = eqParam(u, 'draw_id');
  const match = rows.filter((r) => r.license_hash === hash && (!did || r.draw_id === did));

  if (method === 'PATCH') {
    const patch = JSON.parse(opts.body);
    match.forEach((r) => { Object.assign(r, patch); });
    return jsonRes(200, match);
  }
  return jsonRes(200, match.map((r) => ({ draw_id: r.draw_id, data: r.data })));
};

// A licence WITH a tenant, so the branch reaches its own logic rather than
// short-circuiting on the honest-empty path.
function loadHandler() {
  delete require.cache[require.resolve('./license')];
  require.cache[require.resolve('./license')] = {
    exports: {
      validateLicenseKey: async function () {
        return {
          valid: true, active: true, license_hash: LIC_HASH,
          customer_email: 'tenant@example.test',
          trial_ends_at: null, stripe_subscription_id: null
        };
      },
      hashLicense: hashLicense
    }
  };
  global.fetch = FETCH;
  delete require.cache[require.resolve('../sd-data.js')];
  return require('../sd-data.js');
}

async function call(action, payload, token) {
  const handler = loadHandler();
  const res = mockRes();
  const headers = { authorization: 'Bearer ' + KEY };
  if (token) headers['x-sd-auth'] = token;
  await handler({
    method: 'POST', headers: headers,
    body: { action: action, resource: 'bld_draws', app_id: 'sairnbuild', payload: payload }
  }, res);
  return res;
}
const wip = (payload, token) => call('wip', Object.assign({ today: TODAY }, payload || {}), token === undefined ? tokenFor('owner') : token);
const release = (payload, token) => call('release_retainage', Object.assign({ today: TODAY }, payload || {}), token === undefined ? tokenFor('owner') : token);
function summaryFor(body, id) { return body.data.filter((d) => d.draw_id === id)[0]; }

async function main() {
  console.log('SAIRNbuild bld_draws -- retainage can come back out (audit B2)');

  // ── 1. THE GATE ────────────────────────────────────────────────────────
  section('1. who may look at progress billing, and on what date');

  await test('no session token is refused as a session', async () => {
    seed();
    const res = await wip({}, null);
    assert.strictEqual(res.statusCode, 401, 'got ' + res.statusCode);
    assert.strictEqual(res.body.error.code, 'NO_SESSION');
  });

  await test('a REAL non-management role (pm) is refused the read', async () => {
    seed();
    const res = await wip({}, tokenFor('pm'));
    assert.strictEqual(res.statusCode, 403, 'got ' + res.statusCode);
    assert.strictEqual(res.body.error.code, 'FORBIDDEN');
    assert.strictEqual(requests.length, 0, 'the refusal still read the table');
  });

  await test('a non-management role is refused the WRITE too', async () => {
    seed();
    const res = await release({ draw_id: 'DR-01', amount: 100, released_at: TODAY }, tokenFor('pm'));
    assert.strictEqual(res.statusCode, 403);
    assert.strictEqual(requests.length, 0, 'a refused release still touched the table');
  });

  await test('office is management and gets in', async () => {
    seed();
    const res = await wip({}, tokenFor('office'));
    assert.strictEqual(res.statusCode, 200, 'got ' + res.statusCode);
  });

  await test("a VALID session for another app does not open this one", async () => {
    seed();
    const res = await wip({}, tokenFor('owner', 'sairnroofing'));
    assert.strictEqual(res.statusCode, 401, 'got ' + res.statusCode);
    assert.strictEqual(requests.length, 0);
  });

  await test('no `today` is refused -- the engine will not assume a clock', async () => {
    seed();
    const res = await call('wip', {}, tokenFor('owner'));
    assert.strictEqual(res.statusCode, 400, 'got ' + res.statusCode);
    assert.strictEqual(res.body.error.code, 'NO_TODAY');
  });

  await test("an IMPOSSIBLE `today` is refused, not silently repaired", async () => {
    seed();
    const res = await call('wip', { today: '2026-02-31' }, tokenFor('owner'));
    assert.strictEqual(res.statusCode, 400, "'2026-02-31' was accepted -- item 94, it becomes 2026-03-03");
    assert.strictEqual(res.body.error.code, 'NO_TODAY');
  });

  // ── 2. THE READ ────────────────────────────────────────────────────────
  section('2. the WIP read derives the figures and does not trust the row');

  await test('held comes from amount x pct, NOT from the stored retainage_held', async () => {
    seed();
    const res = await wip();
    assert.strictEqual(res.statusCode, 200, 'got ' + res.statusCode + ' ' + JSON.stringify(res.body));
    // Stored says 999999 on both priced rows; derived is 4500 + 7800.
    assert.strictEqual(res.body.totals.retainage_held, 12300,
      'got ' + res.body.totals.retainage_held + ' -- 999999 means the stored column was read');
    assert.strictEqual(summaryFor(res.body, 'DR-01').retainage_held, 4500);
    assert.strictEqual(summaryFor(res.body, 'DR-02').retainage_held, 7800);
  });

  await test('an UNPRICED draw is excluded and COUNTED, never folded in as zero', async () => {
    seed();
    const res = await wip();
    assert.strictEqual(res.body.totals.draws_counted, 2);
    assert.strictEqual(res.body.totals.draws_not_computable, 1,
      'the draw nobody priced was silently treated as a real zero');
    const d3 = summaryFor(res.body, 'DR-03');
    assert.strictEqual(d3.retainage_held, null);
    assert.ok(d3.problems.some((p) => /no retainage percentage/.test(p)),
      'the unpriced draw does not say why it could not be worked out');
  });

  await test('outstanding is held MINUS released, and starts equal to held', async () => {
    seed();
    const res = await wip();
    assert.strictEqual(res.body.totals.retainage_released, 0);
    assert.strictEqual(res.body.totals.retainage_outstanding, 12300);
  });

  await test('the read is READ-ONLY -- looking at a WIP position changes nothing', async () => {
    seed();
    await wip();
    const writes = requests.filter((r) => r.method !== 'GET');
    assert.strictEqual(writes.length, 0, 'the WIP read issued ' + writes.length + ' write(s)');
  });

  await test("another tenant's draw is not in this licence's book", async () => {
    seed();
    const res = await wip();
    assert.strictEqual(res.body.data.length, 3, 'got ' + res.body.data.length + ' draws');
    assert.ok(!summaryFor(res.body, 'DR-99'), "another tenant's draw came back");
  });

  await test('aged_days is FORWARDED to the engine, not quietly defaulted', async () => {
    seed();
    // DR-02 was requested 2026-08-01 and today is 2026-09-15 -- 45 days.
    const dflt = await wip();
    assert.strictEqual(summaryFor(dflt.body, 'DR-02').days_outstanding, 45);
    assert.strictEqual(summaryFor(dflt.body, 'DR-02').aged, true,
      '45 days outstanding is not aged against the 30-day default');
    const wide = await wip({ aged_days: 90 });
    assert.strictEqual(summaryFor(wide.body, 'DR-02').aged, false,
      'aged_days never reached the engine -- it took its own default and the answer still looked reasonable');
  });

  await test('an UNUSABLE aged_days is refused, not quietly turned into 30', async () => {
    seed();
    for (const bad of ['30', 30.5, -1, 400, NaN]) {
      const res = await wip({ aged_days: bad });
      assert.strictEqual(res.statusCode, 400, JSON.stringify(bad) + ' got ' + res.statusCode);
      assert.strictEqual(res.body.error.code, 'BAD_AGED_DAYS');
    }
    // null and absent both mean "nobody asked for a window", which is not the
    // same fact and must still work.
    assert.strictEqual((await wip({ aged_days: null })).statusCode, 200);
  });

  await test('an UNPROVISIONED table degrades honestly, it does not 500', async () => {
    seed();
    provisioned = false;
    const res = await wip();
    assert.strictEqual(res.statusCode, 200, 'got ' + res.statusCode);
    assert.strictEqual(res.body.provisioned, false);
    assert.deepStrictEqual(res.body.data, []);
    assert.strictEqual(res.body.totals, null,
      'an absent table reported a totals object, which reads as a real zero');
  });

  // ── 3. WHAT A RELEASE REFUSES ──────────────────────────────────────────
  section('3. a release that is not a record of anything is refused');

  await test('no draw_id', async () => {
    seed();
    const res = await release({ amount: 100, released_at: TODAY });
    assert.strictEqual(res.statusCode, 400);
  });

  await test('a zero or negative amount is not a release', async () => {
    seed();
    for (const amt of [0, -500, 'abc', null]) {
      const res = await release({ draw_id: 'DR-01', amount: amt, released_at: TODAY });
      assert.strictEqual(res.statusCode, 400, 'amount ' + JSON.stringify(amt) + ' got ' + res.statusCode);
      assert.strictEqual(res.body.error.code, 'BAD_AMOUNT');
    }
  });

  await test('no released_at -- a release with no date cannot be defended', async () => {
    seed();
    const res = await release({ draw_id: 'DR-01', amount: 100 });
    assert.strictEqual(res.statusCode, 400);
    assert.strictEqual(res.body.error.code, 'NO_RELEASE_DATE');
  });

  await test('an IMPOSSIBLE released_at is refused for the RIGHT reason', async () => {
    seed();
    const res = await release({ draw_id: 'DR-01', amount: 100, released_at: '2026-02-31' });
    assert.strictEqual(res.statusCode, 400, "'2026-02-31' was accepted as a release date");
    assert.strictEqual(res.body.error.code, 'NO_RELEASE_DATE',
      'refused, but blamed on something other than the date');
  });

  await test('a draw that is not on file is 404, not a silent no-op', async () => {
    seed();
    const res = await release({ draw_id: 'NOPE', amount: 100, released_at: TODAY });
    assert.strictEqual(res.statusCode, 404);
    assert.strictEqual(res.body.error.code, 'NO_SUCH_DRAW');
  });

  await test("another tenant's draw is not on file EITHER", async () => {
    seed();
    const res = await release({ draw_id: 'DR-99', amount: 100, released_at: TODAY });
    assert.strictEqual(res.statusCode, 404, 'got ' + res.statusCode);
    assert.strictEqual(row('DR-99', OTHER_TENANT_HASH).data.retainage_released, undefined,
      "another tenant's draw was written to");
  });

  await test('releasing MORE than was ever held is refused BY THE ENGINE', async () => {
    seed();
    const res = await release({ draw_id: 'DR-01', amount: 6000, released_at: TODAY });
    assert.strictEqual(res.statusCode, 409, 'got ' + res.statusCode);
    assert.strictEqual(res.body.error.code, 'RELEASE_REFUSED');
    assert.match(res.body.error.message, /more retainage released than was ever held/,
      'the refusal is not the engine\'s own sentence -- the rule has been re-spelled locally');
    assert.strictEqual(row('DR-01').data.retainage_released, undefined, 'the refused release still wrote');
  });

  await test('releasing against a draw nobody priced is refused', async () => {
    seed();
    const res = await release({ draw_id: 'DR-03', amount: 100, released_at: TODAY });
    assert.strictEqual(res.statusCode, 409, 'got ' + res.statusCode);
    assert.strictEqual(res.body.error.code, 'RELEASE_REFUSED');
    assert.match(res.body.error.message, /no usable retainage percentage/);
  });

  // ── 4. THE RELEASE ITSELF ──────────────────────────────────────────────
  section('4. a release is an EVENT, with a trail, and it only goes one way');

  await test('a good release lands and outstanding actually falls', async () => {
    seed();
    const res = await release({ draw_id: 'DR-01', amount: 4500, released_at: '2026-09-10' });
    assert.strictEqual(res.statusCode, 200, 'got ' + res.statusCode + ' ' + JSON.stringify(res.body));
    assert.strictEqual(res.body.summary.retainage_released, 4500);
    assert.strictEqual(res.body.summary.retainage_outstanding, 0);
    const after = await wip();
    assert.strictEqual(after.body.totals.retainage_released, 4500);
    assert.strictEqual(after.body.totals.retainage_outstanding, 7800,
      'the board still says the money is being withheld -- which is the whole bug');
    assert.strictEqual(after.body.totals.retainage_held, 12300,
      'GROSS held moved; it is a lifetime figure and must not');
  });

  await test('the trail records who, when, how much, and what it was before', async () => {
    seed();
    const res = await release({ draw_id: 'DR-01', amount: 4500, released_at: '2026-09-10' });
    const log = res.body.release_log;
    assert.strictEqual(log.length, 1);
    assert.strictEqual(log[0].amount, 4500);
    assert.strictEqual(log[0].released_at, '2026-09-10');
    assert.strictEqual(log[0].previous, 0);
    assert.strictEqual(log[0].by_employee_id, 'emp-owner');
    assert.strictEqual(log[0].by_role, 'owner');
    assert.ok(log[0].at, 'no server instant recorded');
  });

  await test('a SECOND, larger release APPENDS -- the trail is never rewritten', async () => {
    seed();
    await release({ draw_id: 'DR-02', amount: 3000, released_at: '2026-09-10' });
    const res = await release({ draw_id: 'DR-02', amount: 7800, released_at: '2026-09-12' });
    assert.strictEqual(res.statusCode, 200, 'got ' + res.statusCode + ' ' + JSON.stringify(res.body));
    const log = res.body.release_log;
    assert.strictEqual(log.length, 2, 'got ' + log.length + ' entries -- the first release was overwritten');
    assert.strictEqual(log[0].amount, 3000);
    assert.strictEqual(log[1].amount, 7800);
    assert.strictEqual(log[1].previous, 3000, 'the second entry does not say what it replaced');
    assert.strictEqual(res.body.summary.retainage_outstanding, 0);
  });

  await test('a release may NOT be reduced -- that is un-paying somebody', async () => {
    seed();
    await release({ draw_id: 'DR-02', amount: 5000, released_at: '2026-09-10' });
    const res = await release({ draw_id: 'DR-02', amount: 2000, released_at: '2026-09-12' });
    assert.strictEqual(res.statusCode, 409, 'got ' + res.statusCode);
    assert.strictEqual(res.body.error.code, 'RELEASE_WOULD_DECREASE');
    assert.strictEqual(row('DR-02').data.retainage_released, 5000, 'the reduction landed anyway');
    assert.strictEqual(row('DR-02').data.retainage_release_log.length, 1,
      'a refused release still appended to the trail');
  });

  await test('the write is READ-MODIFY-WRITE -- nothing the caller did not send is lost', async () => {
    seed();
    await release({ draw_id: 'DR-01', amount: 4500, released_at: '2026-09-10' });
    const d = row('DR-01').data;
    assert.strictEqual(d.notes, 'first draw', 'a field the caller never sent was dropped');
    assert.strictEqual(d.job_id, 'J-2601');
    assert.strictEqual(d.amount, 45000);
    assert.strictEqual(d.status, 'received');
    assert.strictEqual(d.retainage_released, 4500);
    assert.strictEqual(d.retainage_released_at, '2026-09-10');
  });

  await test('a release touches ONE draw and leaves the rest alone', async () => {
    seed();
    await release({ draw_id: 'DR-01', amount: 4500, released_at: '2026-09-10' });
    assert.strictEqual(row('DR-02').data.retainage_released, undefined);
    assert.strictEqual(row('DR-03').data.retainage_released, undefined);
    // A raw PATCH became a single scoped RPC call (2026-09-21, hover_log
    // #315 fix) -- the scoping now lives in the POST body's p_draw_id /
    // p_license_hash rather than a query string.
    const rpcCalls = requests.filter((r) => r.url.indexOf('rpc/bld_release_retainage_atomic') !== -1);
    assert.strictEqual(rpcCalls.length, 1, 'got ' + rpcCalls.length + ' retainage-release RPC calls for one release');
    assert.strictEqual(rpcCalls[0].body.p_draw_id, 'DR-01', 'the RPC call is not scoped to one draw');
    assert.ok(rpcCalls[0].body.p_license_hash, 'the RPC call is not scoped to one tenant');
  });

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail === 0 ? 0 : 1);
}

main();
