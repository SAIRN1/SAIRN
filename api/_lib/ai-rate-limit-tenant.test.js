// api/_lib/ai-rate-limit-tenant.test.js
//
// Run:  node api/_lib/ai-rate-limit-tenant.test.js
//
// THE PER-TENANT SUB-BUDGET, on the client half.
//
// ── WHAT THIS GUARDS ──────────────────────────────────────────────────────
// docs/2026-09-15-item93-shared-backend-tenancy-scoping.md found that this
// limiter keyed on `app_id` and that the key had been inherited from the table
// shape rather than chosen -- so "should two customers of one app share a daily
// quota?" had been answered by a column name. Michael decided it on 2026-09-15:
// each client gets a sub-budget inside the existing per-app ceiling.
//
// The SQL half is where the arithmetic lives (sql/sairn_ai_tenant_subbudget_
// 2026-09-15.sql, and its own header carries three verification queries to run
// against a real database). What is asserted HERE is everything the client is
// responsible for and could get wrong silently:
//
//   * the tenant key REACHES the RPC, and is the license_hash rather than the
//     raw licence key -- a bearer secret in a log table is the one mistake
//     this feature could make that is worse than the problem it solves;
//   * a call with NO tenant is not refused and is not silently treated as
//     sub-budgeted;
//   * an un-migrated database degrades to the 3-argument function ONCE rather
//     than on every request, and never all the way to the racy path;
//   * `limited_by` distinguishes an app ceiling from a tenant share, because
//     those are different incidents in front of a customer;
//   * the knobs fall back to their defaults on an unreadable value, never to
//     zero -- a zero share would cap every tenant at nothing.

'use strict';

const assert = require('assert');

process.env.SUPABASE_URL = 'https://stub.test';
process.env.SUPABASE_SERVICE_ROLE_KEY = 'k';
delete process.env.SAIRN_AI_RATE_LIMIT_MODE;
delete process.env.SAIRN_AI_DAILY_LIMIT;
delete process.env.SAIRN_AI_TENANT_SHARE;
delete process.env.SAIRN_AI_CONTENTION_FLOOR;

let pass = 0, fail = 0;
async function test(name, fn) {
  try { await fn(); pass++; console.log('  ok   - ' + name); }
  catch (e) { fail++; console.log('  FAIL - ' + name + '\n         ' + e.message); }
}
function section(t) { console.log('\n--- ' + t + ' ---'); }

// A fresh module each time, because the "remember the 404" flag is
// module-level by design and a test that inherited it from the previous case
// would be asserting the wrong thing.
function load(handler) {
  delete require.cache[require.resolve('./ai-rate-limit')];
  global.fetch = handler;
  return require('./ai-rate-limit');
}

// The RPC double. Records every call so an arm can assert WHAT was sent, which
// is the only way "the licence key never reaches the table" is checkable.
function rpcStub(opts) {
  opts = opts || {};
  const calls = [];
  const fn = (url, init) => {
    const u = String(url);
    const body = init && init.body ? JSON.parse(init.body) : null;
    calls.push({ url: u, body: body, method: (init && init.method) || 'GET' });
    if (u.indexOf('rpc/sairn_ai_rate_limit_consume') !== -1) {
      const sixArg = body && body.p_tenant_key !== undefined;
      if (sixArg && opts.tenantRpcMissing) {
        return Promise.resolve({ ok: false, status: 404, json: () => Promise.resolve({}) });
      }
      return Promise.resolve({
        ok: true, status: 200,
        json: () => Promise.resolve(Object.assign({
          prior_count: 0, limited: false, limit: body.p_limit,
          tenant_scoped: !!sixArg,
          tenant_prior_count: sixArg ? 0 : null,
          tenant_limit: sixArg ? body.p_tenant_limit : null,
          limited_by: null, row_id: 1
        }, opts.reply || {}))
      });
    }
    // The racy fallback's count + insert.
    return Promise.resolve({
      ok: true, status: 200,
      headers: { get: () => '*/0' },
      json: () => Promise.resolve([{ id: 7 }])
    });
  };
  fn.calls = calls;
  return fn;
}

const HASH = 'a'.repeat(64);          // a license_hash shape
const RAW_KEY = 'DNT-PINNACLE-2026';  // the bearer secret that must never appear

(async () => {
  console.log('ai-rate-limit -- the per-tenant sub-budget');

  section('the tenant key reaches the RPC, and it is the HASH');

  await test('a tenant-scoped call sends p_tenant_key plus both bounds', async () => {
    const f = rpcStub();
    const m = load(f);
    const r = await m.checkAiRateLimit('sairndental', HASH);
    const rpc = f.calls.filter((c) => c.url.indexOf('rpc/') !== -1)[0];
    assert.ok(rpc, 'no RPC call was made at all');
    assert.strictEqual(rpc.body.p_tenant_key, HASH);
    assert.strictEqual(rpc.body.p_tenant_limit, 100, 'default share is half of 200');
    assert.strictEqual(rpc.body.p_contention_floor, 100, 'default floor is half of 200');
    assert.strictEqual(r.tenant_scoped, true);
  });

  await test('THE RAW LICENCE KEY NEVER APPEARS IN ANYTHING SENT', async () => {
    // The caller passes a hash; this asserts the module adds nothing else. If a
    // future edit passed the key through instead, it lands in a log table that
    // is not a credential store and is read by anybody with database access.
    const f = rpcStub();
    const m = load(f);
    await m.checkAiRateLimit('sairndental', HASH);
    const sent = JSON.stringify(f.calls);
    assert.strictEqual(sent.indexOf(RAW_KEY), -1,
      'a raw licence key reached the rate-limit call');
    assert.ok(sent.indexOf(HASH) !== -1,
      'the hash did NOT reach the call, so the assertion above proves nothing');
  });

  section('a call with no tenant is allowed, counted, and says it was not scoped');

  await test('no tenant key -> the 3-arg shape, and tenant_scoped is false', async () => {
    const f = rpcStub();
    const m = load(f);
    const r = await m.checkAiRateLimit('stonedesk');
    const rpc = f.calls.filter((c) => c.url.indexOf('rpc/') !== -1)[0];
    assert.strictEqual(rpc.body.p_tenant_key, undefined,
      'a tenant argument was sent for a call that has no tenant');
    assert.strictEqual(r.tenant_scoped, false);
    assert.strictEqual(r.allowed, true, 'an unattributable call was refused');
    assert.strictEqual(r.degraded, false, 'a counted call was reported as degraded');
  });

  section('an un-migrated database degrades once, not forever, and not to racy');

  await test('a 404 on the 6-arg shape retries the 3-arg one and still counts', async () => {
    const f = rpcStub({ tenantRpcMissing: true });
    const m = load(f);
    const r = await m.checkAiRateLimit('sairndental', HASH);
    const rpcs = f.calls.filter((c) => c.url.indexOf('rpc/') !== -1);
    assert.strictEqual(rpcs.length, 2, 'expected the 6-arg attempt then the 3-arg retry');
    assert.strictEqual(rpcs[1].body.p_tenant_key, undefined);
    assert.strictEqual(r.atomic, true,
      'it fell through to the RACY path, losing atomicity for a reason that has '
      + 'nothing to do with atomicity');
    assert.strictEqual(r.tenant_scoped, false);
  });

  await test('...and the SECOND call does not retry -- the 404 is remembered', async () => {
    const f = rpcStub({ tenantRpcMissing: true });
    const m = load(f);
    await m.checkAiRateLimit('sairndental', HASH);
    const firstCount = f.calls.filter((c) => c.url.indexOf('rpc/') !== -1).length;
    await m.checkAiRateLimit('sairndental', HASH);
    const total = f.calls.filter((c) => c.url.indexOf('rpc/') !== -1).length;
    assert.strictEqual(firstCount, 2);
    assert.strictEqual(total, 3,
      'the second call probed again -- that doubles the round trips on every '
      + 'request of an un-migrated deployment, forever');
  });

  section('which ceiling stopped it is part of the answer');

  await test('a TENANT limit reports limited_by tenant, not app', async () => {
    const f = rpcStub({ reply: { limited: true, limited_by: 'tenant', prior_count: 120, tenant_prior_count: 100, tenant_limit: 100 } });
    const m = load(f);
    const r = await m.checkAiRateLimit('sairndental', HASH);
    assert.strictEqual(r.limited, true);
    assert.strictEqual(r.limited_by, 'tenant');
    assert.strictEqual(r.tenant_count, 100);
    assert.strictEqual(r.allowed, true, 'observe mode must still allow');
  });

  await test('an APP limit still reports limited_by app', async () => {
    const f = rpcStub({ reply: { limited: true, limited_by: 'app', prior_count: 200 } });
    const m = load(f);
    const r = await m.checkAiRateLimit('sairndental', HASH);
    assert.strictEqual(r.limited_by, 'app');
  });

  await test('enforce mode blocks on a TENANT limit too', async () => {
    process.env.SAIRN_AI_RATE_LIMIT_MODE = 'enforce';
    const f = rpcStub({ reply: { limited: true, limited_by: 'tenant' } });
    const m = load(f);
    const r = await m.checkAiRateLimit('sairndental', HASH);
    assert.strictEqual(r.allowed, false,
      'a tenant over its share was allowed through in enforce mode');
    delete process.env.SAIRN_AI_RATE_LIMIT_MODE;
  });

  section('the knobs fall back to the default, never to zero');

  await test('an unreadable share falls back to half the ceiling', async () => {
    const m = load(rpcStub());
    for (const bad of ['', 'abc', '-5', '0']) {
      process.env.SAIRN_AI_TENANT_SHARE = bad;
      assert.strictEqual(m.tenantShare(200), 100,
        JSON.stringify(bad) + ' produced ' + m.tenantShare(200)
        + ' -- a zero or negative share caps every tenant at nothing');
    }
    delete process.env.SAIRN_AI_TENANT_SHARE;
  });

  await test('a REAL value is honoured, so the arm above is not vacuous', async () => {
    const m = load(rpcStub());
    process.env.SAIRN_AI_TENANT_SHARE = '25';
    assert.strictEqual(m.tenantShare(200), 25);
    process.env.SAIRN_AI_CONTENTION_FLOOR = '150';
    assert.strictEqual(m.contentionFloor(200), 150);
    delete process.env.SAIRN_AI_TENANT_SHARE;
    delete process.env.SAIRN_AI_CONTENTION_FLOOR;
  });

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail === 0 ? 0 : 1);
})();
