// api/sairncash/stripe-webhook.test.js
//
// Proves SAIRNcash's webhook is correct WITHOUT a Stripe account, following the
// same split verify.test.js sets out: whether we can REACH Stripe is gated;
// whether we handle what Stripe sends is not, and never was.
//
// SIGNATURE VERIFICATION IS EXERCISED FOR REAL HERE, not simulated. The
// signatures below are generated with a fake secret and fed to the Stripe SDK's
// own webhooks.constructEvent -- the same call the endpoint makes. So the
// tamper, wrong-secret and replay cases are genuine rejections by the library,
// not a re-implementation agreeing with itself. What remains untestable until a
// key lands is connectivity and Stripe's real event shapes; the fixtures here
// follow Stripe's published object shapes.
//
// Firebase is stubbed through the require cache so handleEvent's reads and
// writes are observable without a database.
//
// Plain node:assert, no framework -- matching verify.test.js and
// trial-renew.test.js exactly.
// Run: node api/sairncash/stripe-webhook.test.js
// (requires `npm install` -- package.json already declares stripe ^17.4.0)

const assert = require('assert');
const crypto = require('crypto');
const path = require('path');

// ---- stub the Firebase layer BEFORE the webhook requires it ---------------
const fbPath = require.resolve(path.join(__dirname, '../_lib/firebase-admin.js'));
const writes = [];
let stored = {};
require.cache[fbPath] = {
  id: fbPath,
  filename: fbPath,
  loaded: true,
  exports: {
    mintCustomToken: async () => 'stub',
    rtdbUpdate: async (p, v) => {
      writes.push({ path: p, value: v });
      stored[p] = Object.assign({}, stored[p], v);
    },
    rtdbGet: async (p) => {
      const parent = p.replace(/\/lastEventAt$/, '');
      return stored[parent] ? stored[parent].lastEventAt : null;
    }
  }
};

const hook = require('./stripe-webhook.js');
const Stripe = require('stripe');
const stripe = new Stripe('sk_test_dummy_never_used_for_a_signature_check');

const SECRET = 'whsec_' + 'x'.repeat(32);
function sign(body, secret, ts) {
  const t0 = ts || Math.floor(Date.now() / 1000);
  const sig = crypto.createHmac('sha256', secret).update(t0 + '.' + body).digest('hex');
  return 't=' + t0 + ',v1=' + sig;
}
function construct(body, header, secret) {
  try { return { ok: true, event: stripe.webhooks.constructEvent(body, header, secret) }; }
  catch (e) { return { ok: false, msg: e.message }; }
}
const ev = (type, obj, id, created) => ({
  id: id || 'evt_x', type, created: created || 2000, data: { object: obj }
});

// ---- signature verification ----------------------------------------------
const body = JSON.stringify(ev('invoice.payment_succeeded', { customer: 'cus_A' }, 'evt_1', 1000));

assert.strictEqual(construct(body, sign(body, SECRET), SECRET).ok, true,
  'a correctly signed payload must verify');

assert.strictEqual(construct(body.replace('cus_A', 'cus_B'), sign(body, SECRET), SECRET).ok, false,
  'a payload altered after signing must be rejected');

assert.strictEqual(construct(body, sign(body, 'whsec_' + 'y'.repeat(32)), SECRET).ok, false,
  'a signature made with a different secret must be rejected -- this is what stops anyone POSTing a fake cancellation');

assert.strictEqual(construct(body, '', SECRET).ok, false, 'a missing signature header must be rejected');
assert.strictEqual(construct(body, 't=1,v1=zzz', SECRET).ok, false, 'a malformed header must be rejected');

const stale = construct(body, sign(body, SECRET, Math.floor(Date.now() / 1000) - 4000), SECRET);
assert.strictEqual(stale.ok, false, 'a replayed old timestamp must be rejected');
assert.ok(/timestamp/i.test(stale.msg), 'the replay rejection should name the timestamp, not the signature');

// ---- identifiers come off the verified payload, never the caller ----------
assert.strictEqual(hook.customerIdFrom({ customer: 'cus_1' }), 'cus_1');
assert.strictEqual(hook.customerIdFrom({ customer: { id: 'cus_2' } }), 'cus_2', 'expanded customer object');
assert.strictEqual(hook.customerIdFrom({}), null);
assert.strictEqual(hook.customerIdFrom(null), null);
assert.strictEqual(hook.subscriptionIdFrom(ev('customer.subscription.updated', { id: 'sub_9' })), 'sub_9');
assert.strictEqual(hook.subscriptionIdFrom(ev('checkout.session.completed', { subscription: 'sub_7' })), 'sub_7');
assert.strictEqual(hook.subscriptionIdFrom(ev('invoice.payment_failed', { subscription: { id: 'sub_8' } })), 'sub_8');

// ---- the advisory mirror, per event type ---------------------------------
let m = hook.mirrorFor(ev('checkout.session.completed', { customer: 'cus_1', subscription: 'sub_1' }));
assert.deepStrictEqual(
  [m.customerId, m.patch.status, m.patch.paymentFailed, m.patch.subscriptionId],
  ['cus_1', 'active', false, 'sub_1']);

m = hook.mirrorFor(ev('customer.subscription.updated',
  { id: 'sub_1', customer: 'cus_1', status: 'active', current_period_end: 123, cancel_at_period_end: false }));
assert.deepStrictEqual([m.patch.status, m.patch.paymentFailed, m.patch.currentPeriodEnd], ['active', false, 123]);

for (const dunning of ['past_due', 'unpaid']) {
  m = hook.mirrorFor(ev('customer.subscription.updated', { id: 'sub_1', customer: 'cus_1', status: dunning }));
  assert.strictEqual(m.patch.paymentFailed, true, dunning + ' is a dunning state');
}

m = hook.mirrorFor(ev('customer.subscription.updated',
  { id: 'sub_1', customer: 'cus_1', status: 'active', cancel_at_period_end: true }));
assert.deepStrictEqual([m.patch.status, m.patch.cancelAtPeriodEnd], ['active', true],
  'cancel-at-period-end is carried without changing status');

m = hook.mirrorFor(ev('customer.subscription.deleted', { id: 'sub_1', customer: 'cus_1' }));
assert.deepStrictEqual([m.patch.status, m.patch.cancelAtPeriodEnd], ['canceled', false]);

m = hook.mirrorFor(ev('invoice.payment_failed', { customer: 'cus_1', attempt_count: 2 }));
assert.deepStrictEqual([m.patch.paymentFailed, m.patch.failedAttempts], [true, 2]);
assert.strictEqual(m.patch.status, undefined,
  'a failed invoice must NOT assert a subscription status -- Stripe decides when that becomes past_due');

m = hook.mirrorFor(ev('invoice.payment_succeeded', { customer: 'cus_1' }));
assert.deepStrictEqual([m.patch.paymentFailed, m.patch.failedAttempts], [false, 0]);

assert.strictEqual(hook.mirrorFor(ev('invoice.payment_failed', {})), null,
  'an event with no customer has no write target');
assert.strictEqual(hook.HANDLED.length, 5);

// ---- idempotency and ordering --------------------------------------------
(async () => {
  writes.length = 0; stored = {};

  await hook.handleEvent(ev('customer.subscription.updated',
    { id: 'sub_1', customer: 'cus_1', status: 'active' }, 'evt_100', 1000));
  assert.ok(writes.some(w => w.path === 'sairncash/customers/cus_1/billingEvents/evt_100'),
    'the audit entry is keyed by the Stripe event id');
  assert.ok(writes.some(w => w.path === 'sairncash/customers/cus_1/billing'), 'the mirror is written');

  const auditBefore = writes.filter(w => w.path.includes('/billingEvents/')).length;
  await hook.handleEvent(ev('customer.subscription.updated',
    { id: 'sub_1', customer: 'cus_1', status: 'active' }, 'evt_100', 1000));
  const auditKeys = new Set(writes.filter(w => w.path.includes('/billingEvents/')).map(w => w.path));
  assert.strictEqual(auditKeys.size, 1,
    'a Stripe retry overwrites the same audit key rather than appending a duplicate');
  assert.ok(writes.filter(w => w.path.includes('/billingEvents/')).length > auditBefore,
    'and the retry really was processed, not short-circuited');

  writes.length = 0;
  await hook.handleEvent(ev('customer.subscription.deleted', { id: 'sub_1', customer: 'cus_1' }, 'evt_101', 2000));
  assert.strictEqual(writes.find(w => w.path === 'sairncash/customers/cus_1/billing').value.status, 'canceled',
    'a newer event advances the mirror');

  writes.length = 0;
  await hook.handleEvent(ev('customer.subscription.updated',
    { id: 'sub_1', customer: 'cus_1', status: 'active' }, 'evt_099', 500));
  assert.ok(!writes.some(w => w.path === 'sairncash/customers/cus_1/billing'),
    'a stale out-of-order event must not resurrect a cancelled customer');
  assert.ok(writes.some(w => w.path === 'sairncash/customers/cus_1/billingEvents/evt_099'),
    'but late delivery is still worth recording in the audit trail');
  assert.strictEqual(stored['sairncash/customers/cus_1/billing'].status, 'canceled',
    'the stored status is unchanged');

  writes.length = 0;
  await hook.handleEvent(ev('invoice.payment_failed', {}, 'evt_102', 3000));
  assert.strictEqual(writes.length, 0, 'an event with no customer writes nothing anywhere');

  console.log('api/sairncash/stripe-webhook.test.js: all assertions passed');
})();
