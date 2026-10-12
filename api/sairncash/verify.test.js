// api/sairncash/verify.test.js
// REQUIREMENT: every decision verify.js makes about a Stripe Checkout Session
//   or Subscription is correct without credentials -- an unpaid, cancelled or
//   past_due subscription answers valid:false rather than an error code, and a
//   server with no STRIPE_SECRET_KEY refuses without naming the secret
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
    // ASSERTED AGAINST THE MODULE'S CONSTANT, NOT A LITERAL (2026-09-15).
    // This line read `'Not configured'` and had been RED since 3b115e8a, the
    // item-94 change that made api/_lib/stripe-config.js the one owner of "is
    // Stripe configured" and moved the wording to CLIENT_MESSAGE. A copy of a
    // string another module owns is exactly what that refactor existed to
    // remove, so re-typing the NEW wording here would reintroduce the same
    // defect with a fresher value. Importing it means the next rewording
    // cannot make this stale.
    const CLIENT_MESSAGE = require('../_lib/stripe-config').CLIENT_MESSAGE;
    assert.strictEqual(res.body.error, CLIENT_MESSAGE);
    // ...and the constant is not VACUOUSLY satisfiable. Asserting a value
    // against the module that produced it would pass if that module started
    // returning an empty string, so the two properties the message has to
    // keep are asserted directly: it says something, and it never names the
    // variable whose absence caused it.
    assert.ok(CLIENT_MESSAGE && CLIENT_MESSAGE.length > 10,
      'the client message is empty or near-empty: ' + JSON.stringify(CLIENT_MESSAGE));
    assert.doesNotMatch(String(res.body.error), /STRIPE_SECRET_KEY|sk_/,
      'the refusal names the missing secret to an unauthenticated caller');
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

  // ── THE FIREBASE MINT NEEDS A SECOND IDENTIFIER (2026-10-11) ─────────────
  // THE DEFECT: an unauthenticated POST carrying nothing but a subscriptionId
  // came back with a Firebase CUSTOM AUTH TOKEN for that subscription's
  // customer. api/_lib/firebase-admin.js:66-69 states the precondition for
  // minting in its own words -- the uid must be "the customer this request
  // already proved ownership of via a real trial/license check higher up the
  // call stack" -- and this branch did no such check. Reported by hover2
  // (seq681); reproducing artifact
  // .claude/skills/sairn-hover-auditor/tools-hover2/
  // sairncash_verify_token_mint_repro.py.
  //
  // WHAT THESE ARMS DO AND DO NOT PROVE. They prove the MINT DECISION, which is
  // the whole of the change: who gets a token, who does not, and whether the
  // reason is stated. They do NOT prove the token is cryptographically sound --
  // api/_lib/firebase-mint.test.js drives the real mintCustomToken for that.
  // The three outcomes are asserted separately rather than as one
  // "token is present" check, because a single arm would pass while absence and
  // mismatch were silently collapsed into one code.
  //
  // THE MINT IS STUBBED BY ABSENCE, NOT BY A FAKE. There is no
  // SAIRNCASH_FIREBASE_SERVICE_ACCOUNT in this process, so mintCustomToken
  // throws, verify.js's own try/catch returns null, and firebaseToken is null
  // on the HAPPY path too. That means a "token is null" assertion CANNOT
  // distinguish withheld from failed-to-mint -- which is exactly why
  // firebaseTokenWithheld exists and is what these arms assert instead. Stated
  // because an arm that looked at the token alone would be vacuous here and
  // would still have printed PASS.

  await test('subscriptionId with NO customerId -> verified, but the mint is '
    + 'withheld with CUSTOMER_ID_NOT_SUPPLIED named', async () => {
    nextSubscription = subscription();
    const res = mockRes();
    await freshVerify()(post({ subscriptionId: 'sub_XYZ789' }), res);
    assert.strictEqual(res.statusCode, 200);
    assert.strictEqual(res.body.valid, true,
      'verification itself must still succeed -- a withheld sync credential '
      + 'must not cost a paying customer the app');
    assert.strictEqual(res.body.firebaseToken, null);
    assert.strictEqual(res.body.firebaseTokenWithheld, 'CUSTOMER_ID_NOT_SUPPLIED',
      'a bare null is indistinguishable from a Firebase outage; the reason is '
      + 'the thing that makes the refusal readable');
  });

  await test('subscriptionId with the WRONG customerId -> withheld, and the '
    + 'code says MISMATCH rather than NOT_SUPPLIED', async () => {
    nextSubscription = subscription();
    const res = mockRes();
    await freshVerify()(post({
      subscriptionId: 'sub_XYZ789', customerId: 'cus_SOMEBODY_ELSE'
    }), res);
    assert.strictEqual(res.body.valid, true);
    assert.strictEqual(res.body.firebaseToken, null);
    assert.strictEqual(res.body.firebaseTokenWithheld, 'CUSTOMER_ID_MISMATCH',
      'absence and mismatch are different facts -- an absent id is a stale '
      + 'client, a mismatched one is a caller asking for a token that is not '
      + 'theirs, and collapsing them hides the second inside the first');
  });

  await test('subscriptionId with the RIGHT customerId -> the mint is ATTEMPTED '
    + '(nothing withheld), and the real customerId is still returned', async () => {
    nextSubscription = subscription();
    const res = mockRes();
    await freshVerify()(post({
      subscriptionId: 'sub_XYZ789', customerId: 'cus_ABC123'
    }), res);
    assert.strictEqual(res.body.valid, true);
    assert.strictEqual(res.body.firebaseTokenWithheld, null,
      'the matching case must not be withheld -- if this is non-null the gate '
      + 'is refusing the legitimate client and sync is dead for everyone');
    assert.strictEqual(res.body.customerId, 'cus_ABC123');
  });

  await test('the claimed customerId is NEVER echoed in place of the real one '
    + '-- a mismatch must not teach the caller anything', async () => {
    nextSubscription = subscription();
    const res = mockRes();
    await freshVerify()(post({
      subscriptionId: 'sub_XYZ789', customerId: 'cus_SOMEBODY_ELSE'
    }), res);
    assert.strictEqual(res.body.customerId, 'cus_ABC123',
      'the response must carry what STRIPE says, not what the caller claimed');
    assert.notStrictEqual(res.body.customerId, 'cus_SOMEBODY_ELSE');
  });

  await test('a non-string customerId is refused as ABSENT, not coerced -- '
    + 'true, 1 and {} must not satisfy the check', async () => {
    for (const bad of [true, 1, {}, [], null]) {
      nextSubscription = subscription();
      const res = mockRes();
      await freshVerify()(post({ subscriptionId: 'sub_XYZ789', customerId: bad }), res);
      assert.strictEqual(res.body.firebaseTokenWithheld, 'CUSTOMER_ID_NOT_SUPPLIED',
        'customerId ' + JSON.stringify(bad) + ' was not treated as absent');
    }
  });

  await test('an INACTIVE subscription never reaches the mint decision at all '
    + '-- valid:false carries no firebase fields to read', async () => {
    nextSubscription = subscription({ status: 'canceled' });
    const res = mockRes();
    await freshVerify()(post({
      subscriptionId: 'sub_XYZ789', customerId: 'cus_ABC123'
    }), res);
    assert.strictEqual(res.body.valid, false);
    assert.strictEqual(res.body.firebaseToken, undefined,
      'the valid:false response grew a firebase field -- the early return is '
      + 'the thing that keeps a cancelled subscription away from the mint');
  });

  console.log('\n' + passed + ' passed, ' + failed + ' failed');
  if (failed) process.exit(1);
}

main();
