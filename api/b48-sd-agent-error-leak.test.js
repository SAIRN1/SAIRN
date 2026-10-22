// api/b48-sd-agent-error-leak.test.js
// Plain node:assert tests. Run: node api/b48-sd-agent-error-leak.test.js
//
// HOVER H1 #1684: api/sd-agent.js's last catch relayed err.message to the
// caller. On that path err.message is either Anthropic's own error text
// (callClaude throws UPSTREAM with data.error.message) or an internal
// exception, and neither is the caller's to read.
//
// THE ABLATION ARM RUNS THE OLD LINE. A leak arm that cannot fail on the code
// it was written against proves nothing, so arm X rebuilds the handler with
// the pre-b48 line swapped back in and requires arm A's check to catch it.

'use strict';
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const Module = require('module');

const SECRET_UPSTREAM = 'UPSTREAM-DETAIL-' + 'b48-must-not-leak';
const SECRET_INTERNAL = 'INTERNAL-DETAIL-' + 'b48-must-not-leak';
const GENERIC = 'Upstream connection error — try again';
const NEW_LINE = "res.status(err.status || 502).json({ error: { message: 'Upstream connection error — try again' } });";
const OLD_LINE = "res.status(err.status || 502).json({ error: { message: err.message || 'Upstream connection error — try again' } });";

let passed = 0, total = 0;
async function test(name, fn) {
  total++;
  try { await fn(); passed++; console.log('  ok - ' + name); }
  catch (e) { console.log('  FAIL - ' + name + '\n        ' + e.message); }
}

function mockRes() {
  const res = { statusCode: null, body: null };
  res.status = function (c) { res.statusCode = c; return res; };
  res.json = function (b) { res.body = b; return res; };
  return res;
}
function mockReq(body) {
  return { method: 'POST', headers: { authorization: 'Bearer GOOD-KEY' }, body: body };
}

// `mode` 'upstream': Anthropic answers 400 with a message. 'throw': fetch
// itself throws. `source` replaces the handler's text (the ablation).
function loadHandler(mode, source) {
  delete require.cache[require.resolve('./_lib/ai-rate-limit')];
  require.cache[require.resolve('./_lib/ai-rate-limit')] = {
    exports: {
      checkAiRateLimit: async function () { return { allowed: true, degraded: false, rowId: null }; },
      recordAiUsage: async function () {}
    }
  };
  delete require.cache[require.resolve('./_lib/sd-store')];
  require.cache[require.resolve('./_lib/sd-store')] = {
    exports: {
      validateAndGate: async function () {
        return { valid: true, active: true, license_hash: 'b48-test-hash' };
      },
      writeSlab: async function () { return { id: 'S1' }; }
    }
  };
  global.fetch = async function (url) {
    if (String(url).indexOf('api.anthropic.com') !== -1) {
      if (mode === 'throw') throw new Error(SECRET_INTERNAL);
      return { ok: false, status: 400,
               json: async () => ({ error: { type: 'invalid_request_error', message: SECRET_UPSTREAM } }) };
    }
    return { ok: true, status: 200, json: async () => [] };
  };
  const file = require.resolve('./sd-agent.js');
  delete require.cache[file];
  if (!source) return require(file);
  const m = new Module(file, module);
  m.filename = file;
  m.paths = Module._nodeModulePaths(path.dirname(file));
  m._compile(source, file);
  return m.exports;
}

async function drive(handler) {
  const res = mockRes();
  const realErr = console.error;
  console.error = function () {};
  try { await handler(mockReq({ message: 'hello' }), res); }
  finally { console.error = realErr; }
  return res;
}

function assertNoLeak(res, secret) {
  const body = JSON.stringify(res.body);
  assert.ok(body.indexOf(secret) === -1, 'response relays the error text: ' + body.slice(0, 200));
  assert.strictEqual(res.body.error.message, GENERIC, 'expected the fixed sentence, got ' + body.slice(0, 200));
}

(async () => {
  console.log('api/sd-agent.js -- the last catch never relays err.message (hover H1 #1684)');

  process.env.SUPABASE_URL = 'https://test.supabase.co';
  process.env.SUPABASE_SERVICE_ROLE_KEY = 'test-key';
  process.env.ANTHROPIC_API_KEY = ['b48', 'leak', 'fixture'].join('-');

  await test('A. Anthropic refuses with a message -> its status, the fixed sentence, no upstream text', async () => {
    const res = await drive(loadHandler('upstream'));
    assert.strictEqual(res.statusCode, 400);
    assertNoLeak(res, SECRET_UPSTREAM);
  });

  await test('B. the fetch itself throws -> 502, the fixed sentence, no exception text', async () => {
    const res = await drive(loadHandler('throw'));
    assert.strictEqual(res.statusCode, 502);
    assertNoLeak(res, SECRET_INTERNAL);
  });

  await test('X. ABLATION: with the pre-b48 line restored, arm A\'s check FAILS', async () => {
    const src = fs.readFileSync(path.join(__dirname, 'sd-agent.js'), 'utf8');
    assert.strictEqual(src.split(NEW_LINE).length - 1, 1,
      'the fixed line must occur exactly once or this ablation mutates nothing');
    const res = await drive(loadHandler('upstream', src.replace(NEW_LINE, OLD_LINE)));
    assert.throws(() => assertNoLeak(res, SECRET_UPSTREAM),
      'the old line relayed nothing, so arm A would pass on the defect it guards');
  });

  console.log('\n' + passed + '/' + total + ' passed');
  process.exit(passed === total ? 0 : 1);
})();
