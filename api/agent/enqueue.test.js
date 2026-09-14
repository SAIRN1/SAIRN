// api/agent/enqueue.test.js
// Run: node api/agent/enqueue.test.js
//
// ITEM 6. This insert had no key, no unique constraint and no read-before-write,
// so a retry after a lost response queued a SECOND command and api/agent/poll.js
// handed it to the agent to execute again. WHAT IS DUPLICATED HERE IS AN
// ARBITRARY OPERATION, not a log line -- which is why this was the sharpest of
// the thirty unguarded writes triaged on 2026-09-14.
//
// THE ARM THAT MATTERS: a retry carrying the same key must come back with the
// ORIGINAL command_id. A fix that returned a NEW id would look like it worked
// -- the caller gets a 200 and an id -- while the agent ran the operation
// twice, which is the failure in full.
//
// AND THE PAIRED NEGATIVE: a caller that sends NO key must behave exactly as it
// did before, duplicate-on-retry included. This endpoint has live pilot
// callers; a fix that required a key would break them to prevent a failure they
// may never hit.

const assert = require('assert');
const handler = require('./enqueue.js');

let passed = 0, failed = 0;
async function test(name, fn) {
  try { await fn(); passed++; console.log('  ok   - ' + name); }
  catch (err) { failed++; console.error('  FAIL - ' + name + '\n         ' + err.message); }
}

function mockRes() {
  const res = { statusCode: null, body: null };
  res.status = (c) => { res.statusCode = c; return res; };
  res.json = (p) => { res.body = p; return res; };
  return res;
}

const AGENT = '11111111-2222-3333-4444-555555555555';
const KEY = 'enqueue-retry-2026-09-14-abcdef';
const req = (body) => ({ method: 'POST', headers: {}, body });

// A world holding one agent, and (optionally) one command already queued under
// KEY. Answered from the URL rather than a fixed script, so an arm says what
// the database CONTAINS rather than which call number it is.
function world(opts) {
  const o = opts || {};
  const calls = [];
  global.fetch = async (url, init) => {
    const u = String(url), m = (init && init.method) || 'GET';
    calls.push({ url: u, method: m, body: init && init.body });
    if (u.indexOf('sairn_agents') !== -1) {
      return { ok: true, status: 200,
        json: async () => [{ id: AGENT, status: 'active', plan_status: 'paid', trial_ends_at: null }] };
    }
    if (m === 'POST') {
      if (o.unknownColumn) {
        return { ok: false, status: 400,
          json: async () => ({ message: 'column "idempotency_key" does not exist' }) };
      }
      const hasKey = /idempotency_key/.test(String(init && init.body));
      if (o.alreadyQueued && hasKey) {
        return { ok: false, status: 409,
          json: async () => ({ code: '23505', message: 'duplicate key value' }) };
      }
      return { ok: true, status: 201, json: async () => [{ id: 'NEW-COMMAND-ID' }] };
    }
    // The read-back. Honest: it answers only when filtered on the real key.
    if (o.lookupFails) {
      return { ok: false, status: 500, json: async () => ({}) };
    }
    const km = /idempotency_key=eq\.([^&]+)/.exec(u);
    const rows = (km && decodeURIComponent(km[1]) === KEY)
      ? [{ id: 'ORIGINAL-COMMAND-ID' }] : [];
    return { ok: true, status: 200, json: async () => rows };
  };
  return calls;
}

async function main() {
  process.env.SUPABASE_URL = 'https://db.example.invalid';
  process.env.SUPABASE_SERVICE_ROLE_KEY = 'service-key';
  console.log('api/agent/enqueue.js -- a retry must not queue the command twice');

  console.log('\nA. the key is validated, not quietly ignored');
  await test('a short key is REFUSED', async () => {
    world();
    const res = mockRes();
    await handler(req({ agent_id: AGENT, operation: 'op', idempotency_key: 'tiny' }), res);
    assert.strictEqual(res.statusCode, 400);
    assert.strictEqual(res.body.error.code, 'BAD_IDEMPOTENCY_KEY');
  });

  console.log('\nB. the column appears only when asked for');
  await test('no key: the insert body carries NO idempotency_key', async () => {
    const calls = world();
    const res = mockRes();
    await handler(req({ agent_id: AGENT, operation: 'op' }), res);
    assert.strictEqual(res.statusCode, 200, JSON.stringify(res.body));
    const post = calls.filter((c) => c.method === 'POST')[0];
    assert.ok(post.body.indexOf('idempotency_key') === -1,
      'sending the column before the migration has run would 400 EVERY enqueue');
  });
  await test('with a key: it is sent as-is, unhashed', async () => {
    const calls = world();
    const res = mockRes();
    await handler(req({ agent_id: AGENT, operation: 'op', idempotency_key: KEY }), res);
    assert.strictEqual(res.statusCode, 200, JSON.stringify(res.body));
    assert.ok(calls.filter((c) => c.method === 'POST')[0].body.indexOf(KEY) !== -1);
  });

  console.log('\nC. THE ARM THAT MATTERS: a retry gets the ORIGINAL id');
  await test('same key again -> the ORIGINAL command_id, not a new one', async () => {
    world({ alreadyQueued: true });
    const res = mockRes();
    await handler(req({ agent_id: AGENT, operation: 'op', idempotency_key: KEY }), res);
    assert.strictEqual(res.statusCode, 200, JSON.stringify(res.body));
    assert.strictEqual(res.body.command_id, 'ORIGINAL-COMMAND-ID',
      'a NEW id here means the agent will run the operation twice, which is the '
      + 'whole defect -- and the caller would see a 200 and never know');
    assert.strictEqual(res.body.retried, true);
  });
  await test('THE PAIRED NEGATIVE: no key still queues a second command, '
    + 'unchanged for existing callers', async () => {
    world({ alreadyQueued: true });
    const res = mockRes();
    await handler(req({ agent_id: AGENT, operation: 'op' }), res);
    assert.strictEqual(res.statusCode, 200, JSON.stringify(res.body));
    assert.strictEqual(res.body.command_id, 'NEW-COMMAND-ID');
    assert.ok(!res.body.retried);
  });

  console.log('\nD. could-not-tell never reads as "not queued"');
  await test('a failed read-back says the command IS queued and not to re-key',
    async () => {
      world({ alreadyQueued: true, lookupFails: true });
      const res = mockRes();
      await handler(req({ agent_id: AGENT, operation: 'op', idempotency_key: KEY }), res);
      assert.strictEqual(res.statusCode, 502, JSON.stringify(res.body));
      assert.strictEqual(res.body.error.code, 'ALREADY_QUEUED_LOOKUP_FAILED');
      assert.ok(/Do NOT retry with a new key/.test(res.body.error.message),
        'a caller told only "try again" would re-key and queue it twice, which '
        + 'is the exact failure this endpoint is being fixed for');
    });
  await test('a MISSING COLUMN is NOT_PROVISIONED and names the migration',
    async () => {
      world({ unknownColumn: true });
      const res = mockRes();
      await handler(req({ agent_id: AGENT, operation: 'op', idempotency_key: KEY }), res);
      assert.strictEqual(res.statusCode, 503, JSON.stringify(res.body));
      assert.ok(/sairn_agent_commands_idempotency_2026-09-14\.sql/.test(
        res.body.error.message));
    });

  console.log('\n' + passed + ' passed, ' + failed + ' failed');
  if (failed) process.exitCode = 1;
}

main();
