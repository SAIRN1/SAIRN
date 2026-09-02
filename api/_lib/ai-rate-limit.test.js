// api/_lib/ai-rate-limit.test.js
//
// Proves the limiter is atomic under CONCURRENCY, not just correct
// sequentially -- the whole point of the 2026-09-02 fix.
//
// The Supabase side is simulated by a fake fetch backed by an in-memory log,
// with a deliberate delay between the count and the insert so concurrent
// callers genuinely interleave. That is what makes the old path fail here: the
// race is real in the code shape, and a simulation with no delay would hide it.
//
// The atomic path's guarantee is delegated to Postgres (pg_advisory_xact_lock),
// so what is proved HERE is that the client makes ONE call and trusts the
// server's verdict, and that a fake serialised backend then yields distinct
// counts. The lock itself is verified in the SQL file's own comment block, on
// a real database, and cannot be proved from JavaScript.
//
// Plain node:assert, no framework -- matching verify.test.js and
// stripe-webhook.test.js exactly.
// Run: node api/_lib/ai-rate-limit.test.js

const assert = require('assert');

const realFetch = global.fetch;
const realEnv = Object.assign({}, process.env);

function makeBackend(opts) {
  opts = opts || {};
  const log = [];                 // { app_id }
  const state = { rpcAvailable: !!opts.rpcAvailable, calls: 0, inserts: 0, counts: 0 };
  const gap = opts.gapMs || 0;    // delay between count and insert on the racy path
  let lock = Promise.resolve();   // serialises the atomic path, like the advisory lock

  global.fetch = async (url, init) => {
    state.calls++;
    const u = String(url);

    if (u.includes('/rpc/sairn_ai_rate_limit_consume')) {
      if (!state.rpcAvailable) return { ok: false, status: 404, json: async () => ({}) };
      const body = JSON.parse(init.body);
      // The real guarantee is the advisory lock; this chain is its stand-in.
      let release;
      const prev = lock;
      lock = new Promise(r => { release = r; });
      await prev;
      try {
        const prior = log.filter(x => x.app_id === body.p_app_id).length;
        if (gap) await new Promise(r => setTimeout(r, gap));
        log.push({ app_id: body.p_app_id });
        state.counts++; state.inserts++;
        return { ok: true, status: 200, json: async () => ({
          prior_count: prior, limited: prior >= body.p_limit, limit: body.p_limit
        }) };
      } finally { release(); }
    }

    if (init && init.method === 'POST') {           // racy insert
      const body = JSON.parse(init.body);
      if (gap) await new Promise(r => setTimeout(r, gap));
      log.push({ app_id: body.app_id });
      state.inserts++;
      return { ok: true, status: 201, json: async () => ({}) };
    }

    // racy count
    const app = decodeURIComponent((u.match(/app_id=eq\.([^&]+)/) || [])[1] || '');
    const n = log.filter(x => x.app_id === app).length;
    state.counts++;
    if (gap) await new Promise(r => setTimeout(r, gap));
    return {
      ok: true, status: 200,
      headers: { get: (h) => (h.toLowerCase() === 'content-range' ? '*/' + n : null) },
      json: async () => []
    };
  };
  return { log, state };
}

function load() {
  delete require.cache[require.resolve('./ai-rate-limit.js')];
  return require('./ai-rate-limit.js');
}

(async () => {
  process.env.SUPABASE_URL = 'https://example.supabase.co';
  process.env.SUPABASE_SERVICE_ROLE_KEY = 'test-key';
  process.env.SAIRN_AI_DAILY_LIMIT = '5';
  delete process.env.SAIRN_AI_RATE_LIMIT_MODE;      // observe

  // ---- exact-count parsing, the bug fixed on the way past ----------------
  const { exactCountFrom } = load();
  assert.strictEqual(exactCountFrom({ headers: { get: () => '0-24/1234' } }), 1234,
    'a ranged Content-Range yields the total, not the page size');
  assert.strictEqual(exactCountFrom({ headers: { get: () => '*/7' } }), 7);
  assert.strictEqual(exactCountFrom({ headers: { get: () => '0-24/*' } }), null,
    'an unknown total must be null, not 0 -- 0 would read as "no calls yet"');
  assert.strictEqual(exactCountFrom({ headers: { get: () => null } }), null);
  assert.strictEqual(exactCountFrom({}), null);

  // ---- THE RACE, demonstrated on the fallback path ----------------------
  {
    const be = makeBackend({ rpcAvailable: false, gapMs: 15 });
    const { checkAiRateLimit } = load();
    const results = await Promise.all(
      Array.from({ length: 10 }, () => checkAiRateLimit('raceapp'))
    );
    const counts = results.map(r => r.count);
    assert.ok(results.every(r => r.atomic === false), 'the fallback must report atomic:false');
    assert.ok(results.every(r => r.mode === 'observe-racy'),
      'and must say -racy in its mode so the race is visible, not silent');
    // Every one of the ten read the same count, because none of the inserts
    // had landed yet. This is the defect, reproduced.
    assert.strictEqual(new Set(counts).size, 1,
      'ten concurrent racy callers all read the SAME count -- this is the bug');
    assert.strictEqual(counts[0], 0);
    assert.strictEqual(be.log.length, 10, 'yet all ten were recorded');
    // ...and with a limit of 5, none of them was flagged as limited.
    assert.ok(results.every(r => r.limited === false),
      'so a limit of 5 did not fire on the 6th through 10th call');
  }

  // ---- THE FIX: the same ten calls through the atomic RPC ---------------
  {
    const be = makeBackend({ rpcAvailable: true, gapMs: 15 });
    const { checkAiRateLimit } = load();
    const results = await Promise.all(
      Array.from({ length: 10 }, () => checkAiRateLimit('atomicapp'))
    );
    const counts = results.map(r => r.count).sort((a, b) => a - b);
    assert.ok(results.every(r => r.atomic === true), 'the atomic path reports atomic:true');
    assert.ok(results.every(r => r.mode === 'observe'), 'and drops the -racy suffix');
    assert.deepStrictEqual(counts, [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
      'every concurrent caller sees a DISTINCT prior count -- no two agree');
    assert.strictEqual(be.log.length, 10);
    assert.strictEqual(results.filter(r => r.limited).length, 5,
      'with a limit of 5, exactly the 6th through 10th are flagged as limited');
    assert.strictEqual(be.state.calls, 10,
      'and it is ONE round trip per call, not two -- faster as well as correct');
  }

  // ---- enforce mode actually blocks, and only past the limit ------------
  {
    process.env.SAIRN_AI_RATE_LIMIT_MODE = 'enforce';
    const be = makeBackend({ rpcAvailable: true, gapMs: 5 });
    const { checkAiRateLimit } = load();
    const results = await Promise.all(
      Array.from({ length: 8 }, () => checkAiRateLimit('enforceapp'))
    );
    const allowed = results.filter(r => r.allowed).length;
    assert.strictEqual(allowed, 5,
      'a limit of 5 permits exactly 5 concurrent calls under enforcement');
    assert.ok(results.every(r => r.mode === 'enforce'));
    assert.strictEqual(be.log.length, 8,
      'and blocked calls are still recorded, so observe data is not clipped');
    delete process.env.SAIRN_AI_RATE_LIMIT_MODE;
  }

  // ---- fail open, every way it can fail --------------------------------
  {
    global.fetch = async () => { throw new Error('network down'); };
    const { checkAiRateLimit } = load();
    const r = await checkAiRateLimit('anyapp');
    assert.strictEqual(r.allowed, true, 'a network outage must never block an AI feature');
    assert.strictEqual(r.counted, false);
    assert.strictEqual(r.atomic, false);
  }
  {
    global.fetch = async (u) => (String(u).includes('/rpc/')
      ? { ok: false, status: 404, json: async () => ({}) }
      : { ok: false, status: 500, json: async () => ({}) });
    const { checkAiRateLimit } = load();
    const r = await checkAiRateLimit('anyapp');
    assert.strictEqual(r.allowed, true, 'a missing table fails open too');
    assert.strictEqual(r.counted, false);
  }
  {
    // RPC present but returning something unusable -> fall back, do not crash
    global.fetch = async (u, init) => {
      if (String(u).includes('/rpc/')) return { ok: true, status: 200, json: async () => ({ error: 'boom' }) };
      if (init && init.method === 'POST') return { ok: true, status: 201, json: async () => ({}) };
      return { ok: true, status: 200, headers: { get: () => '*/3' }, json: async () => [] };
    };
    const { checkAiRateLimit } = load();
    const r = await checkAiRateLimit('anyapp');
    assert.strictEqual(r.atomic, false, 'an unusable RPC body falls back rather than throwing');
    assert.strictEqual(r.count, 3);
  }
  {
    // No app id at all -- no counting, no blocking
    const { checkAiRateLimit } = load();
    const r = await checkAiRateLimit('');
    assert.strictEqual(r.allowed, true);
    assert.strictEqual(r.counted, false);
  }

  global.fetch = realFetch;
  process.env = realEnv;
  console.log('api/_lib/ai-rate-limit.test.js: all assertions passed');
})().catch((e) => { console.error(e); process.exit(1); });
