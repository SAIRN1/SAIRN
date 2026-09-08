// api/claude-cost-controls.test.js
//
// Run:  node api/claude-cost-controls.test.js
//
// THE INTERIM FIX to the open-Anthropic-proxy finding of 2026-09-05. Two
// defects, both on the endpoint that spends this platform's own API key and
// that requires no credential at all to call:
//
//   1. max_tokens was passed to Anthropic UNMODIFIED. Verified live before
//      fixing, with deliberately minimal spend: a request carrying no
//      Authorization header and max_tokens 64000 returned HTTP 200 and a real
//      completion.
//   2. THE RATE LIMITER LIVED INSIDE `if (is_demo)`, AND is_demo COMES FROM
//      THE REQUEST BODY. The one persistent, cross-instance cost control could
//      be switched off by the caller. A control a client can opt out of is not
//      a control.
//
// WHAT THIS SUITE DELIBERATELY DOES NOT CLAIM: neither fix closes the finding.
// The endpoint still requires no credential -- that is the separate, breaking,
// 17-app change. And the limiter ships in OBSERVE mode, so moving it out
// refuses nothing TODAY; what it does is make the control reachable on every
// path so that enforcement, when switched on, cannot be bypassed. Asserting
// otherwise would be the "green suite certifies the bug" shape.

'use strict';
const assert = require('assert');
const fs = require('fs');
const path = require('path');

let pass = 0, fail = 0;
const run = [];
function t(name, fn) { run.push([name, fn]); }
function section(s) { run.push([s, null]); }

const LIMITER = require.resolve('./_lib/ai-rate-limit');

// The handler destructures checkAiRateLimit at module load, so the stub has to
// be in the require cache BEFORE the handler is required.
let limiterCalls = [];
let limiterAnswer = { allowed: true, rowId: 'row-1', degraded: false };
require.cache[LIMITER] = {
  id: LIMITER, filename: LIMITER, loaded: true,
  exports: {
    checkAiRateLimit: async (appId) => { limiterCalls.push(appId); return limiterAnswer; },
    recordAiUsage: async () => {},
  },
};

// The licence lookup is stubbed for the same reason the limiter is: on a
// developer machine SUPABASE_URL is unset, so the real one throws CONFIG and
// every auth state would collapse to `error`. A suite written against that
// would pass whether the auth logic is right or not -- the trap
// api/sd-sub-data-auth-ordering.test.js recorded.
const LICENCE = require.resolve('./_lib/license');
let licenceAnswer = { valid: true, active: true, license_hash: 'h' };
let licenceThrows = false;
require.cache[LICENCE] = {
  id: LICENCE, filename: LICENCE, loaded: true,
  exports: {
    validateLicenseKey: async () => {
      if (licenceThrows) { const e = new Error('upstream'); e.code = 'UPSTREAM'; throw e; }
      return licenceAnswer;
    },
  },
};

process.env.ANTHROPIC_API_KEY = process.env.ANTHROPIC_API_KEY || 'test-key';
process.env.SAIRN_CLAUDE_AUTH_MODE = 'observe';

delete require.cache[require.resolve('./claude.js')];
const handler = require('./claude.js');

// Anthropic itself is stubbed: this suite must never make a real paid call,
// and the body it captures is the thing under test.
let sentBody = null;
let anthropicStatus = 200;
global.fetch = async function (url, opts) {
  sentBody = JSON.parse(opts.body);
  return {
    ok: anthropicStatus === 200,
    status: anthropicStatus,
    json: async () => ({ content: [{ type: 'text', text: 'ok' }], usage: { input_tokens: 1, output_tokens: 1 } }),
  };
};

function mockRes() {
  const res = { _s: 0, _j: null };
  res.status = function (c) { res._s = c; return res; };
  res.json = function (o) { res._j = o; return res; };
  res.setHeader = function () { return res; };
  return res;
}

async function callWithAuth(body, key) {
  sentBody = null;
  limiterCalls = [];
  const headers = key ? { authorization: 'Bearer ' + key } : {};
  const res = mockRes();
  await handler({ method: 'POST', headers, body }, res);
  return { status: res._s, body: res._j, sent: sentBody, limiterCalls: limiterCalls.slice() };
}

async function call(body) { return callWithAuth(body, null); }

const MSG = [{ role: 'user', content: 'hi' }];

section('--- 1. max_tokens is capped, and capped where every path goes through ---');

t('a request for 64000 tokens reaches Anthropic clamped to the ceiling', async () => {
  const r = await call({ app_id: 'stonedesk', is_demo: true, messages: MSG, max_tokens: 64000 });
  assert.strictEqual(r.status, 200, JSON.stringify(r.body));
  assert.strictEqual(r.sent.max_tokens, handler.MAX_TOKENS_CEILING);
});

t('CLAMPED, NOT REFUSED -- an over-large request still gets an answer', async () => {
  const r = await call({ app_id: 'stonedesk', is_demo: true, messages: MSG, max_tokens: 999999 });
  assert.strictEqual(r.status, 200);
  assert.ok(r.body && r.body.content, 'the caller was refused rather than clamped');
});

t('the ceiling is ABOVE every real request on the platform, so nothing legitimate '
  + 'is refused -- 2000 is the largest any app sends and sd-agent uses 4096', () => {
  assert.ok(handler.MAX_TOKENS_CEILING >= 4096,
    'the ceiling dropped below sd-agent\'s own MAX_TOKENS -- a real feature would be truncated');
});

t('a normal request is untouched -- the cap must not rewrite ordinary traffic', async () => {
  const r = await call({ app_id: 'stonedesk', is_demo: true, messages: MSG, max_tokens: 1500 });
  assert.strictEqual(r.sent.max_tokens, 1500);
});

t('an ABSENT max_tokens still defaults to 1000, unchanged behaviour', async () => {
  const r = await call({ app_id: 'stonedesk', is_demo: true, messages: MSG });
  assert.strictEqual(r.sent.max_tokens, 1000);
});

t('a BOOLEAN max_tokens does not become a one-token ceiling', async () => {
  // Number(true) is 1. The first version of cappedMaxTokens() coerced without a
  // type check and returned 1, which would have truncated a real answer to
  // nothing. Found by probing the function, not by reading it -- and it is the
  // same trap api/_lib/dental-ledger.js's isPositiveMoney() already documents.
  const r = await call({ app_id: 'stonedesk', is_demo: true, messages: MSG, max_tokens: true });
  assert.strictEqual(r.sent.max_tokens, 1000);
});

t('a single-element ARRAY max_tokens does not coerce either -- Number([5]) is 5', async () => {
  const r = await call({ app_id: 'stonedesk', is_demo: true, messages: MSG, max_tokens: [5] });
  assert.strictEqual(r.sent.max_tokens, 1000);
});

t('a nonsense value falls back to the DEFAULT, never to the ceiling -- garbage in '
  + 'must not buy the largest generation available', () => {
  assert.strictEqual(handler.cappedMaxTokens(Infinity), 1000);
  assert.strictEqual(handler.cappedMaxTokens(NaN), 1000);
  assert.strictEqual(handler.cappedMaxTokens({ valueOf: () => 99999 }), 1000);
});

t('THE CAP IS IN callAnthropic, NOT ONLY THE HTTP HANDLER -- api/law-auth.js and '
  + 'api/sc-ai.js both pass a client-supplied max_tokens through it', async () => {
  // Asserted through the exported function the way those two files call it,
  // not through the HTTP path, because that is the copy that would otherwise
  // have been left uncapped.
  sentBody = null;
  const out = await handler.callAnthropic({ messages: MSG, max_tokens: 64000 });
  assert.ok(out.ok, JSON.stringify(out));
  assert.strictEqual(sentBody.max_tokens, handler.MAX_TOKENS_CEILING);
});

section('--- 2. the limiter runs for EVERY request, not only is_demo ones ---');

t('is_demo:false -- the bypass -- still consults the limiter', async () => {
  const r = await call({ app_id: 'stonedesk', is_demo: false, messages: MSG });
  assert.deepStrictEqual(r.limiterCalls, ['stonedesk'],
    'the limiter was skipped for a caller that simply said is_demo:false');
});

t('is_demo ABSENT ENTIRELY still consults the limiter', async () => {
  const r = await call({ app_id: 'stonedesk', messages: MSG });
  assert.deepStrictEqual(r.limiterCalls, ['stonedesk']);
});

t('is_demo:true still consults it too -- the move must not have lost the original path', async () => {
  const r = await call({ app_id: 'stonedesk', is_demo: true, messages: MSG });
  assert.deepStrictEqual(r.limiterCalls, ['stonedesk']);
});

t('a REFUSED demo call keeps the exact {error:"demo_limit"} contract 17 apps parse', async () => {
  limiterAnswer = { allowed: false };
  const r = await call({ app_id: 'stonedesk', is_demo: true, messages: MSG });
  limiterAnswer = { allowed: true, rowId: 'row-1', degraded: false };
  assert.strictEqual(r.status, 200, 'the demo contract is a 200 with an error field');
  assert.strictEqual(r.body.error, 'demo_limit');
});

t('a REFUSED non-demo call gets a real 429, not a false "demo_limit"', async () => {
  // SAIRNcash is the one path that legitimately sends is_demo:false, gated
  // upstream by a real Stripe subscription. Telling a paying subscriber they
  // hit a demo limit would be false.
  limiterAnswer = { allowed: false };
  const r = await call({ app_id: 'sairncash', is_demo: false, messages: MSG });
  limiterAnswer = { allowed: true, rowId: 'row-1', degraded: false };
  assert.strictEqual(r.status, 429);
  assert.strictEqual(r.body.error.code, 'AI_RATE_LIMIT');
  assert.ok(String(r.body.error.message).indexOf('demo') === -1,
    'a paying caller was told about a demo limit');
});

t('a refused call never reaches Anthropic', async () => {
  limiterAnswer = { allowed: false };
  const r = await call({ app_id: 'stonedesk', is_demo: true, messages: MSG });
  limiterAnswer = { allowed: true, rowId: 'row-1', degraded: false };
  assert.strictEqual(r.sent, null, 'a refused request still spent money');
});

t('the limiter still FAILS OPEN and still reports that it degraded', async () => {
  limiterAnswer = { allowed: true, rowId: 'row-2', degraded: true, degraded_reason: 'probe' };
  const r = await call({ app_id: 'stonedesk', is_demo: true, messages: MSG });
  limiterAnswer = { allowed: true, rowId: 'row-1', degraded: false };
  assert.strictEqual(r.status, 200);
  assert.strictEqual(r.body.rate_limit_degraded, true);
  assert.strictEqual(r.body.rate_limit_degraded_reason, 'probe');
});

section('--- 3. what is NOT fixed, asserted as-is so it cannot be mistaken for closed ---');

t('IN OBSERVE MODE AN UNAUTHENTICATED CALL IS STILL ALLOWED. Asserted as it IS, '
  + 'not as it should be -- Phase 1 must not refuse anything, and when '
  + 'SAIRN_CLAUDE_AUTH_MODE=enforce is set this behaviour changes deliberately '
  + 'rather than surprising someone', async () => {
  const r = await call({ app_id: 'stonedesk', is_demo: false, messages: MSG });
  assert.strictEqual(r.status, 200,
    'observe mode refused an unauthenticated call -- that is Phase 4 behaviour '
    + 'arriving early, and it would break every live app');
});

t('this suite UPDATED rather than being deleted when the Authorization read '
  + 'landed -- the previous version asserted there was none, and it went red on '
  + 'the very commit that added it, which is the point of an as-is assertion', () => {
  const src = fs.readFileSync(path.join(__dirname, 'claude.js'), 'utf8');
  assert.ok(src.indexOf("req.headers['authorization']") !== -1,
    'the Phase 1 auth read disappeared');
  assert.ok(src.indexOf('SAIRN_CLAUDE_AUTH_MODE') !== -1,
    'the mode flag disappeared -- enforcement must stay revertible without a deploy');
});

section('--- 4. Phase 1: observe, and record absent vs invalid as different things ---');

t('ENFORCE MODE REFUSES an unauthenticated call with 401 NO_LICENSE', async () => {
  process.env.SAIRN_CLAUDE_AUTH_MODE = 'enforce';
  const r = await call({ app_id: 'stonedesk', is_demo: true, messages: MSG });
  process.env.SAIRN_CLAUDE_AUTH_MODE = 'observe';
  assert.strictEqual(r.status, 401, JSON.stringify(r.body));
  assert.strictEqual(r.body.error.code, 'NO_LICENSE');
  assert.strictEqual(r.sent, null, 'a refused request still reached Anthropic');
});

t('enforce mode ALLOWS a valid, active licence', async () => {
  licenceAnswer = { valid: true, active: true, license_hash: 'h' };
  process.env.SAIRN_CLAUDE_AUTH_MODE = 'enforce';
  const r = await callWithAuth({ app_id: 'stonedesk', is_demo: true, messages: MSG }, 'real-key');
  process.env.SAIRN_CLAUDE_AUTH_MODE = 'observe';
  assert.strictEqual(r.status, 200, JSON.stringify(r.body));
});

t('enforce mode FAILS OPEN when the licence store is unreachable -- refusing on '
  + 'our own outage would punish the customer for it', async () => {
  licenceThrows = true;
  process.env.SAIRN_CLAUDE_AUTH_MODE = 'enforce';
  const r = await callWithAuth({ app_id: 'stonedesk', is_demo: true, messages: MSG }, 'real-key');
  process.env.SAIRN_CLAUDE_AUTH_MODE = 'observe';
  licenceThrows = false;
  assert.strictEqual(r.status, 200, 'an upstream failure took the AI down: ' + JSON.stringify(r.body));
});

t('an INACTIVE licence is not treated as absent -- the states are distinguished '
  + 'because they need different answers', async () => {
  licenceAnswer = { valid: true, active: false, license_hash: 'h' };
  process.env.SAIRN_CLAUDE_AUTH_MODE = 'enforce';
  const r = await callWithAuth({ app_id: 'stonedesk', is_demo: true, messages: MSG }, 'real-key');
  process.env.SAIRN_CLAUDE_AUTH_MODE = 'observe';
  licenceAnswer = { valid: true, active: true, license_hash: 'h' };
  // Recorded as `inactive`, and deliberately NOT refused by the enforce branch,
  // which lists only absent and invalid. An inactive licence is a billing
  // state, and cutting off AI is not this endpoint's call to make -- the app's
  // own licence gate already handles it. Asserted so the choice is visible.
  assert.strictEqual(r.status, 200, JSON.stringify(r.body));
});

(async function () {
  for (const [name, fn] of run) {
    if (!fn) { console.log(name); continue; }
    try { await fn(); console.log('  ok   ' + name); pass++; }
    catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
  }
  console.log('\n' + (fail ? 'FAILED  ' : 'ok  ') +
    'claude cost controls: ' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
