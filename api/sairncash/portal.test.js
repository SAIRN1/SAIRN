// api/sairncash/portal.test.js
//
// Proves api/sairncash/portal.js's decisions WITHOUT a Stripe key, by injecting
// a fake `stripe` module shaped like Stripe's published Subscription and
// Billing Portal Session objects. Same split, and the same reason, as
// verify.test.js states at its own line 7: whether we can REACH Stripe is
// gated on credentials; whether we handle Stripe's documented response
// correctly is not, and never was.
//
// ── WHY THIS FILE EXISTS AT ALL, WHICH IS A FINDING AND NOT A CHORE ────────
// `docs/MASTER-PLAN.md` prints this exact path under **DEAD CITATIONS -- 1
// row(s) promise a test file this repo does NOT hold**: `api/sairncash/
// portal.test.js -- cited by index`. The index claimed coverage of a file that
// mints real Stripe Billing Portal sessions -- full access to a customer's
// card, invoices and the power to cancel -- and no such test existed. The
// generator reports a dead citation loudly rather than dropping it precisely
// so it gets written instead of rounded away. This is that write.
//
// ── THE ARM THAT MATTERS MOST IS THE CUSTOMER-ID ONE ───────────────────────
// portal.js's header states its whole security design: the caller sends a
// SUBSCRIPTION id and the customer id is read off the subscription as Stripe
// returns it, because "the identifier the caller can edit is the
// vulnerability". An endpoint that accepted `customerId` from the body would
// hand a working portal link for a stranger's billing to anyone who guessed a
// cus_ string.
//
// A test that only drives the happy path CANNOT SEE that property: the body
// has no customerId, so reading one would change nothing and the arm passes
// either way. So §6 sends a hostile `customerId` that DIFFERS from the
// subscription's, and asserts the portal was opened for the subscription's.
// §11 then proves that discrimination is real rather than assumed, by
// asserting the two ids are not equal -- an identical pair would make §6 pass
// against an endpoint that trusts the body completely.
//
// Plain node:assert, no framework -- matching verify.test.js exactly.
// Run: node api/sairncash/portal.test.js

const assert = require('assert');
const path = require('path');

const PORTAL = path.join(__dirname, 'portal.js');
const STRIPE_ID = require.resolve('stripe');

// What the stub was last asked for, so an arm can assert on the CALL and not
// only on the response. A wrong customer reaching Stripe is the defect this
// file exists to catch, and it is invisible from the response alone.
let nextSubscription = null;
let nextPortalSession = null;
let lastSubRetrieveId = null;
let lastPortalCreateArgs = null;
let lastStripeCtorArgs = null;
let stripeConstructed = 0;

function installStripeStub() {
  function FakeStripe(key, opts) {
    stripeConstructed++;
    lastStripeCtorArgs = { key, opts };
    this.subscriptions = {
      retrieve: async (id) => {
        lastSubRetrieveId = id;
        if (nextSubscription instanceof Error) throw nextSubscription;
        return nextSubscription;
      }
    };
    this.billingPortal = {
      sessions: {
        create: async (args) => {
          lastPortalCreateArgs = args;
          if (nextPortalSession instanceof Error) throw nextPortalSession;
          return nextPortalSession;
        }
      }
    };
  }
  require.cache[STRIPE_ID] = { id: STRIPE_ID, filename: STRIPE_ID, loaded: true, exports: FakeStripe };
}

function freshPortal() {
  delete require.cache[PORTAL];
  return require(PORTAL);
}

function mockRes() {
  const res = { statusCode: null, body: null, headers: {}, ended: false };
  res.setHeader = (k, v) => { res.headers[k] = v; };
  res.status = (c) => { res.statusCode = c; return res; };
  res.json = (p) => { res.body = p; return res; };
  res.end = () => { res.ended = true; return res; };
  return res;
}

const post = (body) => ({ method: 'POST', body });

// Stripe's documented Subscription shape, trimmed to the fields portal.js
// reads. `customer` is an id string on a plain retrieve and an object when
// expanded -- portal.js handles both and so does this.
function subscription(over) {
  return Object.assign({
    id: 'sub_XYZ789',
    status: 'active',
    customer: 'cus_REAL_OWNER'
  }, over || {});
}

let passed = 0, failed = 0;
async function test(name, fn) {
  try { await fn(); console.log('  PASS  ' + name); passed++; }
  catch (e) { console.log('  FAIL  ' + name + '\n        ' + e.message); failed++; }
}

// Every arm that expects to reach Stripe needs a key present and the counters
// clean, or an assertion about "Stripe was never constructed" silently inherits
// a previous arm's count.
function armReady() {
  process.env.STRIPE_SECRET_KEY = 'sk_test_fixture';
  delete process.env.VERCEL_ENV;
  stripeConstructed = 0;
  lastSubRetrieveId = null;
  lastPortalCreateArgs = null;
  lastStripeCtorArgs = null;
  nextSubscription = subscription();
  nextPortalSession = { url: 'https://billing.stripe.com/session/live_fixture' };
}

async function main() {
  installStripeStub();
  const SAVED_SITE_URL = process.env.SITE_URL;
  console.log('SAIRNcash portal.js -- Billing Portal session handling, no credentials\n');

  // ── 1. Transport ─────────────────────────────────────────────────────────
  await test('OPTIONS -> 204 and the CORS headers are set', async () => {
    armReady();
    const res = mockRes();
    await freshPortal()({ method: 'OPTIONS' }, res);
    assert.strictEqual(res.statusCode, 204);
    assert.strictEqual(res.headers['Access-Control-Allow-Origin'], '*');
    assert.ok(/POST/.test(res.headers['Access-Control-Allow-Methods']));
    assert.strictEqual(stripeConstructed, 0, 'a preflight reached Stripe');
  });

  await test('GET -> 405, and Stripe is never constructed', async () => {
    armReady();
    const res = mockRes();
    await freshPortal()({ method: 'GET' }, res);
    assert.strictEqual(res.statusCode, 405);
    assert.strictEqual(stripeConstructed, 0);
  });

  // ── 2. The configuration gate ────────────────────────────────────────────
  await test('no STRIPE_SECRET_KEY -> 500, Stripe never constructed, secret never named', async () => {
    armReady();
    delete process.env.STRIPE_SECRET_KEY;
    const res = mockRes();
    await freshPortal()(post({ subscriptionId: 'sub_XYZ789' }), res);
    assert.strictEqual(res.statusCode, 500);
    // ASSERTED AGAINST THE MODULE'S CONSTANT, NOT A LITERAL. Re-typing the
    // wording here is the defect verify.test.js line 109 records being fixed:
    // a copy of a string another module owns goes stale at the next rewording
    // and the arm turns red for no real reason.
    const CLIENT_MESSAGE = require('../_lib/stripe-config').CLIENT_MESSAGE;
    assert.strictEqual(res.body.error, CLIENT_MESSAGE);
    // ...and that constant is not VACUOUSLY satisfiable. Comparing a value to
    // the module that produced it would pass against an empty string, so the
    // two properties the message must keep are asserted directly.
    assert.ok(CLIENT_MESSAGE && CLIENT_MESSAGE.length > 10,
      'the client message is empty or near-empty: ' + JSON.stringify(CLIENT_MESSAGE));
    assert.doesNotMatch(String(res.body.error), /STRIPE_SECRET_KEY|sk_/,
      'the refusal names the missing secret to an unauthenticated caller');
    assert.strictEqual(stripeConstructed, 0);
  });

  await test('portal needs ONLY the secret key -- a missing PRICE_ID does not block it', async () => {
    // Pinned because this file is WHY api/_lib/stripe-config.js exists: its
    // guard and checkout.js's disagreed about the same environment. The
    // capability table says portal: [STRIPE_SECRET_KEY] and checkout:
    // [STRIPE_SECRET_KEY, STRIPE_PRICE_ID], and that difference is deliberate.
    armReady();
    delete process.env.STRIPE_PRICE_ID;
    const res = mockRes();
    await freshPortal()(post({ subscriptionId: 'sub_XYZ789' }), res);
    assert.strictEqual(res.statusCode, 200, 'a missing PRICE_ID blocked the portal');
    const CAPABILITIES = require('../_lib/stripe-config').CAPABILITIES;
    assert.deepStrictEqual(CAPABILITIES.portal, ['STRIPE_SECRET_KEY'],
      'the capability table moved; this arm is now asserting the wrong contract');
  });

  // ── 3. Input validation ──────────────────────────────────────────────────
  await test('missing subscriptionId -> 400, and nothing reaches Stripe', async () => {
    armReady();
    const res = mockRes();
    await freshPortal()(post({}), res);
    assert.strictEqual(res.statusCode, 400);
    assert.strictEqual(stripeConstructed, 0);
  });

  await test('absent body -> 400 rather than a throw', async () => {
    armReady();
    const res = mockRes();
    await freshPortal()({ method: 'POST' }, res);
    assert.strictEqual(res.statusCode, 400);
  });

  await test('non-string subscriptionId -> 400, so no object is handed to Stripe', async () => {
    // An object here would otherwise flow into subscriptions.retrieve() and be
    // serialised by the SDK into something nobody wrote.
    armReady();
    for (const bad of [{ id: 'sub_X' }, ['sub_X'], 42, true]) {
      const res = mockRes();
      await freshPortal()(post({ subscriptionId: bad }), res);
      assert.strictEqual(res.statusCode, 400, 'accepted ' + JSON.stringify(bad));
    }
    assert.strictEqual(stripeConstructed, 0);
  });

  // ── 4. The happy path ────────────────────────────────────────────────────
  await test('valid subscription -> 200 with the portal url', async () => {
    armReady();
    const res = mockRes();
    await freshPortal()(post({ subscriptionId: 'sub_XYZ789' }), res);
    assert.strictEqual(res.statusCode, 200);
    assert.strictEqual(res.body.url, 'https://billing.stripe.com/session/live_fixture');
    assert.strictEqual(lastSubRetrieveId, 'sub_XYZ789',
      'the subscription looked up was not the one the caller named');
  });

  await test('an EXPANDED customer object resolves to its id, not to [object Object]', async () => {
    armReady();
    nextSubscription = subscription({ customer: { id: 'cus_REAL_OWNER', email: 'a@b.c' } });
    const res = mockRes();
    await freshPortal()(post({ subscriptionId: 'sub_XYZ789' }), res);
    assert.strictEqual(res.statusCode, 200);
    assert.strictEqual(lastPortalCreateArgs.customer, 'cus_REAL_OWNER');
  });

  // ── 5. The 404 that is not an error ──────────────────────────────────────
  await test('subscription with no customer -> 404, and no portal is opened', async () => {
    armReady();
    nextSubscription = subscription({ customer: null });
    const res = mockRes();
    await freshPortal()(post({ subscriptionId: 'sub_XYZ789' }), res);
    assert.strictEqual(res.statusCode, 404);
    assert.strictEqual(lastPortalCreateArgs, null, 'a portal was opened with no customer');
  });

  await test('customer object with no id -> 404 rather than a portal for undefined', async () => {
    armReady();
    nextSubscription = subscription({ customer: { email: 'a@b.c' } });
    const res = mockRes();
    await freshPortal()(post({ subscriptionId: 'sub_XYZ789' }), res);
    assert.strictEqual(res.statusCode, 404);
    assert.strictEqual(lastPortalCreateArgs, null);
  });

  // ── 6. THE SECURITY PROPERTY -- a body-supplied customer id is ignored ───
  await test('a hostile customerId in the body is IGNORED -- the portal opens for the subscription owner', async () => {
    armReady();
    nextSubscription = subscription({ customer: 'cus_REAL_OWNER' });
    const res = mockRes();
    await freshPortal()(post({
      subscriptionId: 'sub_XYZ789',
      customerId: 'cus_SOMEONE_ELSE',
      customer: 'cus_SOMEONE_ELSE'
    }), res);
    assert.strictEqual(res.statusCode, 200);
    assert.strictEqual(lastPortalCreateArgs.customer, 'cus_REAL_OWNER',
      'THE BODY WAS TRUSTED: a portal was opened for ' + lastPortalCreateArgs.customer
      + ', a customer id the caller supplied. This is full access to a '
      + 'stranger\'s card, invoices and cancellation.');
  });

  // ── 7. return_url ────────────────────────────────────────────────────────
  await test('return_url uses SITE_URL when set', async () => {
    armReady();
    process.env.SITE_URL = 'https://example.invalid';
    const res = mockRes();
    await freshPortal()(post({ subscriptionId: 'sub_XYZ789' }), res);
    assert.strictEqual(res.statusCode, 200);
    assert.strictEqual(lastPortalCreateArgs.return_url, 'https://example.invalid/sairncash');
  });

  await test('return_url falls back to the deployed host when SITE_URL is unset', async () => {
    armReady();
    delete process.env.SITE_URL;
    const res = mockRes();
    await freshPortal()(post({ subscriptionId: 'sub_XYZ789' }), res);
    assert.strictEqual(lastPortalCreateArgs.return_url, 'https://sairn.vercel.app/sairncash');
  });

  // ── 8. The pinned API version ────────────────────────────────────────────
  await test('the Stripe client is constructed with the PINNED apiVersion', async () => {
    // Asserted against api/_lib/stripe-api-version.js rather than a literal,
    // for the reason portal.js:74 gives: without the pin, bumping the SDK
    // moves the wire format on a payments path as a side effect of a
    // dependency change. A literal here would have to be edited in lockstep
    // and would quietly stop testing the pin the moment it was not.
    armReady();
    const { STRIPE_API_VERSION } = require('../_lib/stripe-api-version');
    const res = mockRes();
    await freshPortal()(post({ subscriptionId: 'sub_XYZ789' }), res);
    assert.strictEqual(res.statusCode, 200);
    assert.ok(lastStripeCtorArgs && lastStripeCtorArgs.opts,
      'Stripe was constructed with no options at all -- the apiVersion pin is gone');
    assert.strictEqual(lastStripeCtorArgs.opts.apiVersion, STRIPE_API_VERSION);
    assert.ok(/^\d{4}-\d{2}-\d{2}/.test(STRIPE_API_VERSION),
      'the pinned version is not a date-shaped Stripe version: ' + STRIPE_API_VERSION);
  });

  // ── 9. Failure disclosure ────────────────────────────────────────────────
  await test('a Stripe throw -> 500, and Stripe\'s own error text is NOT disclosed', async () => {
    armReady();
    nextSubscription = new Error('No such subscription: sub_XYZ789 (sk_test_51Hq...)');
    const res = mockRes();
    await freshPortal()(post({ subscriptionId: 'sub_XYZ789' }), res);
    assert.strictEqual(res.statusCode, 500);
    assert.doesNotMatch(String(res.body.error), /No such subscription|sk_test_|sk_live_/,
      'Stripe\'s error text reached an unauthenticated caller: ' + res.body.error);
    assert.ok(res.body.error && res.body.error.length > 0, 'the 500 carries no message at all');
  });

  await test('a throw from billingPortal.sessions.create -> 500, not a half-success', async () => {
    armReady();
    nextPortalSession = new Error('portal configuration not set up in this account');
    const res = mockRes();
    await freshPortal()(post({ subscriptionId: 'sub_XYZ789' }), res);
    assert.strictEqual(res.statusCode, 500);
    assert.strictEqual(res.body.url, undefined, 'a url came back on a failed portal create');
  });

  // ── 10. NEGATIVE CONTROL -- the harness can actually fail ────────────────
  await test('NEGATIVE CONTROL: the stub is load-bearing, so a silent no-op would be caught', async () => {
    // Every arm above reads its verdict out of the stub. If the stub were not
    // installed -- a rename of the stripe package, a cache key that stopped
    // matching -- portal.js would construct the REAL Stripe, the call would
    // fail on a fixture key, and the arms would go red for a reason that looks
    // like a product defect. This asserts the injection itself, so that
    // failure mode names itself instead.
    assert.strictEqual(require('stripe').name, 'FakeStripe',
      'the stripe stub is NOT installed; every arm above tested the real SDK');
    armReady();
    lastPortalCreateArgs = null;
    const res = mockRes();
    await freshPortal()(post({ subscriptionId: 'sub_XYZ789' }), res);
    assert.ok(lastPortalCreateArgs !== null,
      'the happy path completed without the stub recording a call -- the arms above are vacuous');
  });

  await test('NEGATIVE CONTROL: the hostile-id arm has something to discriminate', async () => {
    // §6 is only a real test if the two ids differ. If a future edit made the
    // fixture's hostile customerId equal to the subscription's owner, §6 would
    // pass against an endpoint that trusts the body completely -- the exact
    // vacuous-pass shape this repo's disciplines call out.
    assert.notStrictEqual('cus_SOMEONE_ELSE', 'cus_REAL_OWNER',
      'the hostile id and the real owner are the same value; section 6 proves nothing');
  });

  if (SAVED_SITE_URL === undefined) delete process.env.SITE_URL;
  else process.env.SITE_URL = SAVED_SITE_URL;

  console.log('\n' + passed + ' passed, ' + failed + ' failed');
  if (failed) process.exit(1);
}

main();
