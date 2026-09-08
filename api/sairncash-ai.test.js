// api/sairncash-ai.test.js
//
// Run:  node api/sairncash-ai.test.js
//
// api/sairncash/ai.js is SAIRNcash's own authenticated AI path, built because
// the shared proxy is getting a licence-key requirement and SAIRNcash has no
// licence key at all -- it is a consumer app identified by a Stripe
// subscription or a trial token.
//
// THE THING THIS SUITE EXISTS TO HOLD is that the credential is checked
// SERVER-SIDE and BEFORE anything is spent. Until 2026-09-05 SAIRNcash's AI
// had no subscriber check anywhere, and it sent is_demo:false, which skipped
// every cost control the shared proxy had.

'use strict';
const assert = require('assert');

let pass = 0, fail = 0;
const run = [];
function t(name, fn) { run.push([name, fn]); }
function section(s) { run.push([s, null]); }

// ── stubs, installed before the handler is required ────────────────────────
let anthropicCalls = [];
const CLAUDE = require.resolve('./claude.js');
require.cache[CLAUDE] = {
  id: CLAUDE, filename: CLAUDE, loaded: true,
  exports: Object.assign(async function () {}, {
    callAnthropic: async (args) => {
      anthropicCalls.push(args);
      return { ok: true, status: 200, data: { content: [{ type: 'text', text: 'ok' }] } };
    },
  }),
};

let stripeStatus = 'active';
let stripeThrows = false;
const STRIPE = require.resolve('stripe');
require.cache[STRIPE] = {
  id: STRIPE, filename: STRIPE, loaded: true,
  exports: function Stripe() {
    return {
      subscriptions: {
        retrieve: async () => {
          if (stripeThrows) throw new Error('Expired API Key provided: sk_test_xxx');
          return { status: stripeStatus };
        },
      },
    };
  },
};

process.env.STRIPE_SECRET_KEY = 'sk_test_stub';
process.env.SUPABASE_URL = 'https://example.invalid';
process.env.SUPABASE_SERVICE_ROLE_KEY = 'stub';

// Supabase trial lookup
let trialRow = null;
let trialHttpOk = true;
global.fetch = async function () {
  return { ok: trialHttpOk, status: trialHttpOk ? 200 : 500,
           json: async () => (trialRow ? [trialRow] : []) };
};

const handler = require('./sairncash/ai.js');

function mockRes() {
  const res = { _s: 0, _j: null };
  res.status = function (c) { res._s = c; return res; };
  res.json = function (o) { res._j = o; return res; };
  res.end = function () { return res; };
  res.setHeader = function () { return res; };
  return res;
}

async function call(body, method) {
  anthropicCalls = [];
  const res = mockRes();
  await handler({ method: method || 'POST', headers: {}, body }, res);
  return { status: res._s, body: res._j, spent: anthropicCalls.length };
}

const MSG = [{ role: 'user', content: 'hi' }];

section('--- no credential means no spend ---');

t('no subscriptionId and no trialToken -> 401, and Anthropic is never called', async () => {
  const r = await call({ messages: MSG });
  assert.strictEqual(r.status, 401, JSON.stringify(r.body));
  assert.strictEqual(r.body.error.code, 'NO_SUBSCRIPTION');
  assert.strictEqual(r.spent, 0, 'a request with no credential still spent money');
});

t('THE CREDENTIAL IS CHECKED BEFORE THE BODY -- a caller with no credential '
  + 'cannot learn what this endpoint expects from which refusal comes back', async () => {
  // Same ordering lesson as api/sd-data.js and api/sd-sub-data.js. Without a
  // messages array AND without a credential, the answer must be the 401, not
  // the 400 that would tell an anonymous caller the shape of a valid request.
  const r = await call({});
  assert.strictEqual(r.status, 401);
  assert.strictEqual(r.body.error.code, 'NO_SUBSCRIPTION');
});

t('a non-POST is refused first of all', async () => {
  const r = await call({}, 'GET');
  assert.strictEqual(r.status, 405);
  assert.strictEqual(r.spent, 0);
});

section('--- the subscription is looked up, never believed ---');

t('an ACTIVE subscription is allowed', async () => {
  stripeStatus = 'active';
  const r = await call({ subscriptionId: 'sub_1', messages: MSG });
  assert.strictEqual(r.status, 200, JSON.stringify(r.body));
  assert.strictEqual(r.spent, 1);
});

t('a TRIALING subscription is allowed -- Stripe\'s own trial state counts', async () => {
  stripeStatus = 'trialing';
  const r = await call({ subscriptionId: 'sub_1', messages: MSG });
  stripeStatus = 'active';
  assert.strictEqual(r.status, 200);
});

t('a CANCELED subscription is refused, and nothing is spent', async () => {
  stripeStatus = 'canceled';
  const r = await call({ subscriptionId: 'sub_1', messages: MSG });
  stripeStatus = 'active';
  assert.strictEqual(r.status, 401);
  assert.strictEqual(r.spent, 0);
});

t('an UNPAID subscription is refused', async () => {
  stripeStatus = 'unpaid';
  const r = await call({ subscriptionId: 'sub_1', messages: MSG });
  stripeStatus = 'active';
  assert.strictEqual(r.status, 401);
});

section('--- FAILS CLOSED on an upstream failure, and that is the opposite of '
      + 'the shared proxy on purpose ---');

t('a Stripe outage returns 503 and spends nothing', async () => {
  // api/claude.js fails OPEN on an unreachable licence store, because there the
  // licence is not the only thing gating spend and a paying B2B customer should
  // not lose AI over our outage. HERE the identifier is the only thing between
  // a caller and the API key, so failing open would hand free Anthropic spend
  // to anyone sending a nonsense subscriptionId during an outage.
  stripeThrows = true;
  const r = await call({ subscriptionId: 'sub_1', messages: MSG });
  stripeThrows = false;
  assert.strictEqual(r.status, 503, JSON.stringify(r.body));
  assert.strictEqual(r.body.error.code, 'VERIFY_UNAVAILABLE');
  assert.strictEqual(r.spent, 0);
});

t('the outage message does NOT blame the customer\'s account', async () => {
  stripeThrows = true;
  const r = await call({ subscriptionId: 'sub_1', messages: MSG });
  stripeThrows = false;
  assert.match(r.body.error.message, /not a problem with your account/i);
});

t('Stripe\'s own error text never reaches the caller', async () => {
  // api/sairncash/verify.js records the real incident: returning err.message
  // disclosed that an API key existed, that it was a TEST key, and its last six
  // characters, to an anonymous probe.
  stripeThrows = true;
  const r = await call({ subscriptionId: 'sub_1', messages: MSG });
  stripeThrows = false;
  assert.strictEqual(JSON.stringify(r.body).indexOf('sk_test'), -1,
    'the Stripe key prefix leaked to the caller');
});

t('an upstream Stripe failure does NOT silently fall through to the trial path', async () => {
  // A caller holding a real trial token and a junk subscriptionId must not be
  // able to turn a Stripe outage into a free pass -- but more importantly, an
  // outage must not be reported as "no subscription", which would send a paying
  // customer to the signup screen.
  stripeThrows = true;
  trialRow = { status: 'active', expires_at: new Date(Date.now() + 86400000).toISOString() };
  const r = await call({ subscriptionId: 'sub_1', trialToken: 'tok', messages: MSG });
  stripeThrows = false; trialRow = null;
  assert.strictEqual(r.status, 503, 'an outage was reported as something else: ' + JSON.stringify(r.body));
});

section('--- the trial path ---');

t('an ACTIVE, unexpired trial is allowed', async () => {
  trialRow = { status: 'active', expires_at: new Date(Date.now() + 86400000).toISOString() };
  const r = await call({ trialToken: 'tok', messages: MSG });
  trialRow = null;
  assert.strictEqual(r.status, 200, JSON.stringify(r.body));
});

t('an EXPIRED trial is refused even though its row still says active -- nothing '
  + 'sweeps that column on a schedule', async () => {
  trialRow = { status: 'active', expires_at: new Date(Date.now() - 1000).toISOString() };
  const r = await call({ trialToken: 'tok', messages: MSG });
  trialRow = null;
  assert.strictEqual(r.status, 401);
  assert.strictEqual(r.spent, 0);
});

t('a trial row with a non-active status is refused', async () => {
  trialRow = { status: 'revoked', expires_at: new Date(Date.now() + 86400000).toISOString() };
  const r = await call({ trialToken: 'tok', messages: MSG });
  trialRow = null;
  assert.strictEqual(r.status, 401);
});

t('an unknown trial token is refused', async () => {
  trialRow = null;
  const r = await call({ trialToken: 'nope', messages: MSG });
  assert.strictEqual(r.status, 401);
});

section('--- the body is validated only after the credential clears ---');

t('an authenticated caller with no messages array gets the 400', async () => {
  stripeStatus = 'active';
  const r = await call({ subscriptionId: 'sub_1' });
  assert.strictEqual(r.status, 400);
  assert.match(r.body.error.message, /messages array is required/);
  assert.strictEqual(r.spent, 0);
});

t('max_tokens is NOT capped here -- callAnthropic owns the one ceiling, so a '
  + 'second number cannot drift from the first', async () => {
  stripeStatus = 'active';
  await call({ subscriptionId: 'sub_1', messages: MSG, max_tokens: 64000 });
  assert.strictEqual(anthropicCalls[0].max_tokens, 64000,
    'this file started capping too -- there must be exactly one ceiling');
});

(async function () {
  for (const [name, fn] of run) {
    if (!fn) { console.log(name); continue; }
    try { await fn(); console.log('  ok   ' + name); pass++; }
    catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
  }
  console.log('\n' + (fail ? 'FAILED  ' : 'ok  ') +
    'sairncash ai: ' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
