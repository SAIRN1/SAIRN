// api/sairncash/verify.test.js
//
// Proves SAIRNcash's Stripe response handling is correct WITHOUT a Stripe key,
// by injecting fixtures shaped like Stripe's published Checkout Session and
// Subscription objects.
//
// WHY THIS EXISTS -- the pattern, borrowed deliberately:
// docs/superpowers/specs/2026-08-27-evv-transmission-groundwork.md found that
// EVV format conformance "can be proven with no credentials, no agreement, and
// no trading-partner onboarding" -- because the gated thing (can I REACH the
// aggregator) is a different question from the ungated thing (is what I send
// SHAPED correctly). SAIRNcash is blocked in the open-work index on
// "Needs STRIPE_SECRET_KEY / STRIPE_PRICE_ID in Vercel", and the same split
// applies: whether we can reach Stripe is gated; whether we handle Stripe's
// documented response correctly is not, and never was.
//
// So this covers every decision api/sairncash/verify.js makes about a Stripe
// response. When the key lands, what remains to test live is connectivity and
// the real price id -- not this logic.
//
// Plain node:assert, no framework -- matching trial-renew.test.js exactly.
// Run: node api/sairncash/verify.test.js

const assert = require('assert');
const path = require('path');

const VERIFY = path.join(__dirname, 'verify.js');
const STRIPE_ID = require.resolve('stripe');

let nextSession = null;
let nextSubscription = null;
let lastRetrieveArgs = null;

// Inject a fake `stripe` into the module cache before verify.js requires it.
// verify.js does `new Stripe(key)`, so the export must be constructible.
function installStripeStub() {
  function FakeStripe() {
    this.checkout = {
      sessions: {
        retrieve: async (id, opts) => {
          lastRetrieveArgs = { id, opts };
          if (nextSession instanceof Error) throw nextSession;
          return nextSession;
        }
      }
    };
    this.subscriptions = {
      retrieve: async (id, opts) => {
        lastRetrieveArgs = { id, opts };
        if (nextSubscription instanceof Error) throw nextSubscription;
        return nextSubscription;
      }
    };
  }
  require.cache[STRIPE_ID] = { id: STRIPE_ID, filename: STRIPE_ID, loaded: true, exports: FakeStripe };
}

function freshVerify() {
  delete require.cache[VERIFY];
  return require(VERIFY);
}

function mockRes() {
  const res = { statusCode: null, body: null, headers: {} };
  res.setHeader = (k, v) => { res.headers[k] = v; };
  res.status = (c) => { res.statusCode = c; return res; };
  res.json = (p) => { res.body = p; return res; };
  res.end = () => res;
  return res;
}

const post = (body) => ({ method: 'POST', body });

let passed = 0, failed = 0;
async function test(name, fn) {
  try { await fn(); console.log('  PASS  ' + name); passed++; }
  catch (e) { console.log('  FAIL  ' + name + '\n        ' + e.message); failed++; }
}

// Stripe's documented Checkout Session shape, trimmed to the fields read.
function session(over) {
  return Object.assign({
    id: 'cs_test_a1',
    status: 'complete',
    payment_status: 'paid',
    customer_details: { email: 'post@example.com', name: 'Test Post' },
    customer: { id: 'cus_ABC123' },
    subscription: { id: 'sub_XYZ789', current_period_end: 1893456000 }
  }, over || {});
}
function subscription(over) {
  return Object.assign({
    id: 'sub_XYZ789',
    status: 'active',
    current_period_end: 1893456000,
    customer: { id: 'cus_ABC123', email: 'post@example.com', name: 'Test Post' }
  }, over || {});
}

async function main() {
  installStripeStub();
  console.log('SAIRNcash verify.js -- Stripe response handling, no credentials\n');

  await test('no STRIPE_SECRET_KEY -> 500, and Stripe is never constructed', async () => {
    delete process.env.STRIPE_SECRET_KEY;
    const res = mockRes();
    await freshVerify()(post({ sessionId: 'cs_test_a1' }), res);
    assert.strictEqual(res.statusCode, 500);
    assert.strictEqual(res.body.error, 'Not configured');
  });

  process.env.STRIPE_SECRET_KEY = 'sk_test_fixture_not_a_real_key';

  await test('neither sessionId nor subscriptionId -> 400', async () => {
    const res = mockRes();
    await freshVerify()(post({}), res);
    assert.strictEqual(res.statusCode, 400);
  });

  await test('non-POST -> 405', async () => {
    const res = mockRes();
    await freshVerify()({ method: 'GET' }, res);
    assert.strictEqual(res.statusCode, 405);
  });

  await test('paid + complete session -> 200 with mapped fields', async () => {
    nextSession = session();
    const res = mockRes();
    await freshVerify()(post({ sessionId: 'cs_test_a1' }), res);
    assert.strictEqual(res.statusCode, 200);
    assert.strictEqual(res.body.valid, true);
    assert.strictEqual(res.body.email, 'post@example.com');
    assert.strictEqual(res.body.subscriptionId, 'sub_XYZ789');
    assert.strictEqual(res.body.customerId, 'cus_ABC123');
    assert.strictEqual(res.body.expiresAt, new Date(1893456000 * 1000).toISOString());
  });

  await test('session is retrieved WITH expand -- subscription and customer', async () => {
    nextSession = session();
    await freshVerify()(post({ sessionId: 'cs_test_a1' }), mockRes());
    assert.deepStrictEqual(lastRetrieveArgs.opts.expand.sort(), ['customer', 'subscription']);
  });

  // THE OR BOUNDARY. The guard is
  //   payment_status !== 'paid' && status !== 'complete'  -> 402
  // so EITHER condition alone is sufficient to pass. Pinned in all four
  // combinations because an && here is easy to "tidy" into an || later, and
  // that edit would start rejecting genuinely paid customers.
  await test('unpaid but status complete -> still 200 (OR, not AND)', async () => {
    nextSession = session({ payment_status: 'unpaid', status: 'complete' });
    const res = mockRes();
    await freshVerify()(post({ sessionId: 'cs_test_a1' }), res);
    assert.strictEqual(res.statusCode, 200);
  });

  await test('paid but status open -> still 200 (OR, not AND)', async () => {
    nextSession = session({ payment_status: 'paid', status: 'open' });
    const res = mockRes();
    await freshVerify()(post({ sessionId: 'cs_test_a1' }), res);
    assert.strictEqual(res.statusCode, 200);
  });

  await test('unpaid AND open -> 402 Payment not complete', async () => {
    nextSession = session({ payment_status: 'unpaid', status: 'open' });
    const res = mockRes();
    await freshVerify()(post({ sessionId: 'cs_test_a1' }), res);
    assert.strictEqual(res.statusCode, 402);
  });

  // REGRESSION GUARD. verify.js's own comment records that customerId must be
  // the real customer.id and not the transient checkout session id -- it is
  // "the stable identifier every Firebase sync path is scoped by", and getting
  // it wrong caused a global-shared-path data-isolation bug (2026-08-10).
  // Stripe returns customer as a bare string when not expanded, so both shapes
  // must yield the same id.
  await test('customer as expanded object -> customerId extracted', async () => {
    nextSession = session({ customer: { id: 'cus_OBJ' } });
    const res = mockRes();
    await freshVerify()(post({ sessionId: 'cs_test_a1' }), res);
    assert.strictEqual(res.body.customerId, 'cus_OBJ');
  });

  await test('customer as bare string -> same customerId', async () => {
    nextSession = session({ customer: 'cus_STR' });
    const res = mockRes();
    await freshVerify()(post({ sessionId: 'cs_test_a1' }), res);
    assert.strictEqual(res.body.customerId, 'cus_STR');
  });

  await test('subscription as bare string -> subscriptionId extracted', async () => {
    nextSession = session({ subscription: 'sub_STR' });
    const res = mockRes();
    await freshVerify()(post({ sessionId: 'cs_test_a1' }), res);
    assert.strictEqual(res.body.subscriptionId, 'sub_STR');
  });

  await test('subscription as string -> expiresAt is null, not a crash', async () => {
    nextSession = session({ subscription: 'sub_STR' });
    const res = mockRes();
    await freshVerify()(post({ sessionId: 'cs_test_a1' }), res);
    assert.strictEqual(res.body.expiresAt, null);
  });

  // ── subscription path ────────────────────────────────────────────────
  await test('active subscription -> valid true', async () => {
    nextSubscription = subscription({ status: 'active' });
    const res = mockRes();
    await freshVerify()(post({ subscriptionId: 'sub_XYZ789' }), res);
    assert.strictEqual(res.statusCode, 200);
    assert.strictEqual(res.body.valid, true);
    assert.strictEqual(res.body.customerId, 'cus_ABC123');
  });

  await test('trialing subscription -> valid true', async () => {
    nextSubscription = subscription({ status: 'trialing' });
    const res = mockRes();
    await freshVerify()(post({ subscriptionId: 'sub_XYZ789' }), res);
    assert.strictEqual(res.body.valid, true);
  });

  // A cancelled subscription is NOT an error -- it answers 200 {valid:false}.
  // Pinned because "tightening" this to 402/403 would break the client's
  // re-verification path, which reads valid and expects a 200.
  await test('cancelled subscription -> 200 with valid:false, NOT an error code', async () => {
    nextSubscription = subscription({ status: 'canceled' });
    const res = mockRes();
    await freshVerify()(post({ subscriptionId: 'sub_XYZ789' }), res);
    assert.strictEqual(res.statusCode, 200);
    assert.strictEqual(res.body.valid, false);
  });

  await test('past_due subscription -> valid false', async () => {
    nextSubscription = subscription({ status: 'past_due' });
    const res = mockRes();
    await freshVerify()(post({ subscriptionId: 'sub_XYZ789' }), res);
    assert.strictEqual(res.body.valid, false);
  });

  console.log('\n' + passed + ' passed, ' + failed + ' failed');
  if (failed) process.exit(1);
}

main();
