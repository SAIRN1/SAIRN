// api/_lib/ai-usage.test.js
//
// Run: node api/_lib/ai-usage.test.js
//
// Anthropic returns `usage: { input_tokens, output_tokens }` on every
// successful call, and api/claude.js forwarded it to the client from the day it
// was written WITHOUT EVER READING IT. sairn_ai_rate_limit_log stored only
// (app_id, requested_at). So this platform had NO record of how large any AI
// request was -- which is why StoneDesk's [0039] token budget shipped as a
// labelled guess: [0039] was held a day for production sizing data that was
// never being collected and never would have appeared.
//
// These assertions cover the two properties that make the fix safe rather than
// merely present:
//   1. the measurement attaches to THE ROW THIS CALL CREATED, never to
//      whichever row is newest -- under concurrency that would file one app's
//      token count against another app's request;
//   2. it can never delay, alter or fail a reply. Every failure path -- no
//      migration, no client, no row, a refused RPC, a thrown fetch -- ends in a
//      quiet false.
//
// Plain node:assert, matching ai-rate-limit.test.js.

const assert = require('assert');

const realFetch = global.fetch;
const realEnv = Object.assign({}, process.env);

let passed = 0;
async function test(name, fn) {
  try { await fn(); passed++; console.log('  ok - ' + name); }
  catch (e) { console.error('  FAIL - ' + name + '\n    ' + e.message); process.exitCode = 1; }
}

function freshLib() {
  process.env.SUPABASE_URL = 'https://test.supabase.co';
  process.env.SUPABASE_SERVICE_ROLE_KEY = 'test-key';
  delete require.cache[require.resolve('./ai-rate-limit')];
  return require('./ai-rate-limit');
}

// Swallow the library's own console.error so a deliberate failure path does not
// look like a broken test run. Returns what was logged, so "quiet" can itself
// be asserted rather than assumed.
function captureErrors(fn) {
  const real = console.error;
  const lines = [];
  console.error = function () { lines.push(Array.prototype.join.call(arguments, ' ')); };
  return Promise.resolve(fn()).then(
    v => { console.error = real; return { value: v, lines: lines }; },
    e => { console.error = real; throw e; }
  );
}

async function main() {
  console.log('api/_lib/ai-rate-limit.js -- recordAiUsage + row_id plumbing');

  // ---- the recorder refuses rather than guessing -------------------------
  await test('no row id -> false, and never calls the network', async () => {
    const lib = freshLib();
    global.fetch = async () => { throw new Error('must not be called'); };
    assert.strictEqual(await lib.recordAiUsage(null, { input_tokens: 1, output_tokens: 1 }), false);
    assert.strictEqual(await lib.recordAiUsage(undefined, { input_tokens: 1, output_tokens: 1 }), false);
  });

  await test('no usage block -> false, and never calls the network', async () => {
    const lib = freshLib();
    global.fetch = async () => { throw new Error('must not be called'); };
    assert.strictEqual(await lib.recordAiUsage(7, null), false);
    assert.strictEqual(await lib.recordAiUsage(7, {}), false);
  });

  await test('non-numeric tokens -> false, never stored as 0', async () => {
    const lib = freshLib();
    global.fetch = async () => { throw new Error('must not be called'); };
    assert.strictEqual(await lib.recordAiUsage(7, { input_tokens: 'lots', output_tokens: 2 }), false);
    assert.strictEqual(await lib.recordAiUsage(7, { input_tokens: 5 }), false);
  });

  // ---- the happy path ----------------------------------------------------
  await test('sends the row id and both counts to the record RPC', async () => {
    const lib = freshLib();
    let seenUrl = null, seenBody = null;
    global.fetch = async (url, init) => {
      seenUrl = String(url); seenBody = JSON.parse(init.body);
      return { ok: true, status: 200, json: async () => true };
    };
    const ok = await lib.recordAiUsage(4242, { input_tokens: 1234, output_tokens: 567 });
    assert.strictEqual(ok, true);
    assert.ok(seenUrl.includes('/rpc/sairn_ai_record_usage'), 'wrong endpoint: ' + seenUrl);
    assert.deepStrictEqual(seenBody, { p_row_id: 4242, p_input_tokens: 1234, p_output_tokens: 567 });
  });

  await test('an RPC that returns false is reported as false, not as success', async () => {
    const lib = freshLib();
    global.fetch = async () => ({ ok: true, status: 200, json: async () => false });
    assert.strictEqual(await lib.recordAiUsage(1, { input_tokens: 1, output_tokens: 1 }), false);
  });

  // ---- every failure is quiet and harmless -------------------------------
  await test('migration not run (404) -> false, and stays QUIET about it', async () => {
    const lib = freshLib();
    global.fetch = async () => ({ ok: false, status: 404, json: async () => ({}) });
    const r = await captureErrors(() => lib.recordAiUsage(1, { input_tokens: 1, output_tokens: 1 }));
    assert.strictEqual(r.value, false);
    assert.strictEqual(r.lines.length, 0, 'a not-yet-run migration logged an error every call');
  });

  await test('a real HTTP failure -> false, and DOES say so', async () => {
    const lib = freshLib();
    global.fetch = async () => ({ ok: false, status: 500, json: async () => ({}) });
    const r = await captureErrors(() => lib.recordAiUsage(1, { input_tokens: 1, output_tokens: 1 }));
    assert.strictEqual(r.value, false);
    assert.ok(r.lines.some(l => /record failed/.test(l)), 'a 500 was swallowed silently');
  });

  await test('a thrown fetch -> false, never propagates', async () => {
    const lib = freshLib();
    global.fetch = async () => { throw new Error('network down'); };
    const r = await captureErrors(() => lib.recordAiUsage(1, { input_tokens: 1, output_tokens: 1 }));
    assert.strictEqual(r.value, false);
  });

  await test('no Supabase config -> false, never throws', async () => {
    delete require.cache[require.resolve('./ai-rate-limit')];
    delete process.env.SUPABASE_URL;
    delete process.env.SUPABASE_SERVICE_ROLE_KEY;
    const lib = require('./ai-rate-limit');
    assert.strictEqual(await lib.recordAiUsage(1, { input_tokens: 1, output_tokens: 1 }), false);
  });

  // ---- the row id has to survive the limiter to be useful ----------------
  await test('the atomic path surfaces the row_id the RPC inserted', async () => {
    const lib = freshLib();
    global.fetch = async () => ({
      ok: true, status: 200,
      json: async () => ({ prior_count: 3, limited: false, limit: 200, row_id: 991 })
    });
    const rl = await lib.checkAiRateLimit('stonedesk');
    assert.strictEqual(rl.rowId, 991);
  });

  await test('an older RPC with no row_id yields null, not NaN or 0', async () => {
    const lib = freshLib();
    global.fetch = async () => ({
      ok: true, status: 200,
      json: async () => ({ prior_count: 3, limited: false, limit: 200 })
    });
    const rl = await lib.checkAiRateLimit('stonedesk');
    assert.strictEqual(rl.rowId, null,
      'a pre-migration RPC produced a row id that does not exist');
  });

  await test('the racy fallback asks for the id back instead of guessing it', async () => {
    const lib = freshLib();
    let insertUrl = null, insertPrefer = null;
    global.fetch = async (url, init) => {
      const u = String(url);
      if (u.includes('/rpc/')) return { ok: false, status: 404, json: async () => ({}) };
      if (init && init.method === 'POST') {
        insertUrl = u; insertPrefer = init.headers.Prefer;
        return { ok: true, status: 201, json: async () => [{ id: 555 }] };
      }
      return { ok: true, status: 200, headers: { get: () => '*/7' }, json: async () => [] };
    };
    const r = await captureErrors(() => lib.checkAiRateLimit('stonedesk'));
    assert.strictEqual(r.value.rowId, 555);
    assert.ok(/select=id/.test(insertUrl), 'the insert did not request the id: ' + insertUrl);
    assert.ok(/return=representation/.test(insertPrefer), 'Prefer was: ' + insertPrefer);
  });

  await test('a failing-open check reports rowId null rather than omitting it', async () => {
    const lib = freshLib();
    global.fetch = async () => { throw new Error('network down'); };
    const r = await captureErrors(() => lib.checkAiRateLimit('stonedesk'));
    assert.strictEqual(r.value.rowId, null);
    assert.strictEqual(r.value.allowed, true, 'a counting outage blocked an AI call');
  });

  // ---- and the proxy wires it up in the only safe order ------------------
  await test('claude.js records AFTER responding, and does not await it', () => {
    const fs = require('fs');
    const src = fs.readFileSync(require.resolve('../claude.js'), 'utf8');
    const respondAt = src.indexOf('res.status(200).json(result.data);');
    const recordAt = src.indexOf('recordAiUsage(usageRowId');
    assert.ok(respondAt > 0 && recordAt > respondAt,
      'the usage write happens before or instead of the reply');
    assert.ok(/void recordAiUsage\(/.test(src),
      'the usage write is awaited -- a statistic must not be able to delay a reply');
  });

  await test('claude.js only records when a log row actually exists', () => {
    const fs = require('fs');
    const src = fs.readFileSync(require.resolve('../claude.js'), 'utf8');
    assert.match(src, /if \(usageRowId != null && result\.data && result\.data\.usage\)/);
  });

  global.fetch = realFetch;
  process.env = realEnv;
  console.log('\n' + (process.exitCode ? 'FAILURES ABOVE' : 'ALL ' + passed + ' AI-USAGE ASSERTIONS PASS'));
}

main();
