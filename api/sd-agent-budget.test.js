// api/sd-agent-budget.test.js
// Plain node:assert tests. Run: node api/sd-agent-budget.test.js
//
// THE MOST EXPENSIVE AI ENDPOINT ON THE PLATFORM HAD NO BUDGET.
//
// api/claude.js and api/sc-ai.js both consume the shared daily limiter. This
// one did not -- and ONE request here drives up to MAX_ITERATIONS model calls,
// so it is the endpoint where an unbounded caller costs the most.
//
// AND THE UNIT IS PER MODEL CALL, NOT PER REQUEST, which is the half most
// likely to be "simplified" later. Charging one unit for a request that can
// cost ten is an accounting error that makes the budget meaningless exactly
// where it matters most: the limiter would report a healthy day while this
// endpoint spent ten times its share.
//
// WHAT IS DELIBERATELY NOT ASSERTED: that the limit is the RIGHT number. The
// daily figure is shared platform-wide and is a cost decision, not a code one.
// What is asserted is that this endpoint participates in it at all, per call,
// and that a refusal returns the work already done rather than a truncated
// success.

'use strict';
const assert = require('assert');

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

// `calls` counts how many times the limiter was consulted, which is the whole
// point: one per model call, not one per request.
function loadHandler(opts) {
  const o = opts || {};
  const state = { limiterCalls: 0, modelCalls: 0 };

  delete require.cache[require.resolve('./_lib/ai-rate-limit')];
  require.cache[require.resolve('./_lib/ai-rate-limit')] = {
    exports: {
      checkAiRateLimit: async function () {
        state.limiterCalls++;
        const allow = o.allowFirst === undefined ? true
          : state.limiterCalls <= o.allowFirst;
        return { allowed: allow, degraded: !!o.degraded, rowId: null };
      },
      recordAiUsage: async function () {}
    }
  };
  delete require.cache[require.resolve('./_lib/sd-store')];
  require.cache[require.resolve('./_lib/sd-store')] = {
    exports: {
      validateAndGate: async function () {
        return { valid: true, active: true, license_hash: 'agent-test-hash' };
      },
      writeSlab: async function () { return { id: 'S1' }; }
    }
  };

  // Every model call asks for a tool, so the loop would run to MAX_ITERATIONS
  // unless something else stops it. That is the condition the budget exists for.
  global.fetch = async function (url) {
    if (String(url).indexOf('api.anthropic.com') !== -1) {
      state.modelCalls++;
      // `endTurn` makes the loop TERMINATE NORMALLY. Without it every run ends
      // at MAX_ITERATIONS, which is how the degraded arm below first passed
      // without testing anything: it accepted a MAX_ITERATIONS error as
      // evidence, and that error is what an all-allowed run always produces.
      if (o.endTurn) {
        return {
          ok: true, status: 200,
          json: async () => ({ stop_reason: 'end_turn',
                               content: [{ type: 'text', text: 'done' }] })
        };
      }
      return {
        ok: true, status: 200,
        json: async () => ({
          stop_reason: 'tool_use',
          content: [{ type: 'tool_use', id: 't' + state.modelCalls,
                      name: 'list_slabs', input: {} }]
        })
      };
    }
    return { ok: true, status: 200, json: async () => [] };
  };

  delete require.cache[require.resolve('./sd-agent.js')];
  return { handler: require('./sd-agent.js'), state: state };
}

(async () => {
  console.log('api/sd-agent.js -- the agent loop participates in the daily AI budget');

  process.env.SUPABASE_URL = 'https://test.supabase.co';
  process.env.SUPABASE_SERVICE_ROLE_KEY = 'test-key';
  process.env.ANTHROPIC_API_KEY = ['agent', 'budget', 'fixture'].join('-');

  await test('the limiter is consulted ONCE PER MODEL CALL, not once per request',
    async () => {
      const { handler, state } = loadHandler({});
      const res = mockRes();
      await handler(mockReq({ message: 'hello' }), res);
      assert.ok(state.modelCalls > 1,
        'the fixture must drive more than one model call or this proves nothing; got '
        + state.modelCalls);
      assert.strictEqual(state.limiterCalls, state.modelCalls,
        'limiter consulted ' + state.limiterCalls + ' times for '
        + state.modelCalls + ' model calls -- one unit for a ten-call request is '
        + 'an accounting error that makes the budget meaningless here');
    });

  await test('a refusal STOPS the loop -- no further model call is made',
    async () => {
      const { handler, state } = loadHandler({ allowFirst: 2 });
      const res = mockRes();
      await handler(mockReq({ message: 'hello' }), res);
      assert.strictEqual(state.modelCalls, 2,
        'expected the loop to stop after 2 allowed calls, got ' + state.modelCalls);
    });

  await test('...and answers 429 AI_RATE_LIMIT rather than a truncated success',
    async () => {
      const { handler } = loadHandler({ allowFirst: 1 });
      const res = mockRes();
      await handler(mockReq({ message: 'hello' }), res);
      assert.strictEqual(res.statusCode, 429, 'got ' + res.statusCode);
      assert.strictEqual(res.body.error.code, 'AI_RATE_LIMIT');
      assert.ok(!res.body.ok, 'a refusal must not carry ok:true');
    });

  await test('...and returns the conversation so far, so the work is not lost',
    async () => {
      const { handler } = loadHandler({ allowFirst: 2 });
      const res = mockRes();
      await handler(mockReq({ message: 'hello' }), res);
      assert.ok(Array.isArray(res.body.conversation),
        'the partial conversation must come back');
      assert.ok(res.body.conversation.length > 1,
        'a partial answer with nothing in it is a truncated success by another name');
      assert.strictEqual(res.body.completed_calls, 2,
        'the caller has to be able to see how much was done');
    });

  await test('a REFUSAL ON THE FIRST CALL costs no model call at all',
    async () => {
      const { handler, state } = loadHandler({ allowFirst: 0 });
      const res = mockRes();
      await handler(mockReq({ message: 'hello' }), res);
      assert.strictEqual(state.modelCalls, 0,
        'the budget must be checked BEFORE the call, not after; got '
        + state.modelCalls);
      assert.strictEqual(res.statusCode, 429);
    });

  // THIS ARM WAS VACUOUS ON ITS FIRST WRITING and the sabotage control caught
  // it: it accepted EITHER rate_limit_degraded OR a MAX_ITERATIONS error, and
  // an all-allowed run always ends at MAX_ITERATIONS, so the second branch
  // satisfied it every time and the flag was never checked. An `||` in an
  // assertion is an escape hatch, and the branch that always holds is the one
  // it will take.
  await test('DEGRADED is surfaced, not swallowed -- an allow that is the '
    + 'absence of a decision says so', async () => {
      const { handler, state } = loadHandler({ degraded: true, endTurn: true });
      const res = mockRes();
      await handler(mockReq({ message: 'hello' }), res);
      assert.strictEqual(state.modelCalls, 1,
        'the run must FINISH normally or this arm is testing the error path');
      assert.strictEqual(res.statusCode, 200, 'got ' + res.statusCode);
      assert.strictEqual(res.body.rate_limit_degraded, true,
        'degraded must reach the caller: ' + JSON.stringify(res.body).slice(0, 200));
    });

  await test('...and a HEALTHY limiter reports degraded FALSE, so the flag '
    + 'discriminates', async () => {
      const { handler } = loadHandler({ degraded: false, endTurn: true });
      const res = mockRes();
      await handler(mockReq({ message: 'hello' }), res);
      assert.strictEqual(res.body.rate_limit_degraded, false);
    });

  console.log('\n' + passed + '/' + total + ' passed');
  process.exit(passed === total ? 0 : 1);
})();
