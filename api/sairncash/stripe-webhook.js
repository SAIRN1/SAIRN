// api/sairncash/stripe-webhook.js
// ---------------------------------------------------------------------------
// Receives SAIRNcash subscription lifecycle events from Stripe.
//
// WHY THIS IS NOT api/agent/stripe-webhook.js WITH A DIFFERENT TABLE NAME.
// That file writes to Supabase `sairn_agents` and links a payment to an agent
// via metadata.agent_id. SAIRNcash has no Supabase subscription table at all --
// a paid customer's state lives in Stripe, and their DATA lives in Firebase
// RTDB under sairncash/customers/{customerId}/. Different store, different
// identifier, different lifecycle. It was read as a template, not reused.
//
// WHAT THIS IS AND IS NOT AUTHORITATIVE FOR -- the load-bearing decision here.
// api/sairncash/verify.js already re-checks the real Stripe subscription on
// every app load, and that remains THE authority for whether someone may use
// the product. This webhook writes an ADVISORY MIRROR, never a grant:
//
//   - It cannot turn a non-subscriber into a subscriber. Nothing reads this
//     node to decide access.
//   - Worst case if the RTDB rules are ever wrong, or if a replayed or
//     malformed event slips through, is a stale banner -- not free access.
//
// That ordering is deliberate. A webhook that granted entitlement would make
// the RTDB security rules (which live in the Firebase console, outside this
// repo and outside review here) part of the paywall. They are not, and should
// not become so.
//
// WHAT IT GENUINELY ADDS over polling:
//   1. Promptness -- a cancellation or a renewal is known now rather than at
//      the customer's next app load.
//   2. DUNNING, which polling cannot see at all. invoice.payment_failed is not
//      visible as "subscription inactive" until Stripe finally gives up, so a
//      customer whose card expired looks fully active right up until they are
//      cut off with no warning. That is the real gap this closes.
//   3. An audit trail of billing events, keyed by Stripe's own event id.
//
// RAW BODY -- THE VERCEL-SPECIFIC TRAP. Stripe's signature is computed over the
// exact raw request bytes. `export const config = { api: { bodyParser: false } }`
// does NOT work here: this repo uses plain Vercel serverless functions with no
// framework, and that export is only honoured inside Next.js API routes. The
// fix that does work is to read the stream directly and NEVER touch req.body --
// accessing req.body is itself what triggers Vercel's automatic JSON parsing.
// Do not "simplify" this to use req.body; it breaks verification silently.
// (Same finding as api/agent/stripe-webhook.js, independently re-confirmed.)
//
// SIGNATURE VERIFICATION USES THE STRIPE SDK, unlike the agent webhook, and the
// difference is not stylistic. That file hand-rolls HMAC-SHA256 and says why:
// "this repo has no package.json / npm dependencies today". THAT IS NO LONGER
// TRUE -- package.json now carries stripe ^17.4.0, added during the 2026-08-10
// SAIRNcash pivot. So the platform's own stated precedent applies instead, the
// one api/_lib/firebase-admin.js sets out: security-critical crypto goes
// through an audited library, not custom code.
//
// SETUP (Stripe dashboard), once a real account exists:
//   1. Developers > Webhooks > Add endpoint
//   2. URL: https://sairn.vercel.app/api/sairncash/stripe-webhook
//   3. Events: checkout.session.completed, customer.subscription.updated,
//      customer.subscription.deleted, invoice.payment_failed,
//      invoice.payment_succeeded
//   4. Copy the signing secret (whsec_...) into Vercel env var
//      SAIRNCASH_STRIPE_WEBHOOK_SECRET
//
// ENV NAME IS APP-PREFIXED ON PURPOSE. api/agent/stripe-webhook.js already owns
// the bare STRIPE_WEBHOOK_SECRET for a DIFFERENT Stripe endpoint with a
// DIFFERENT signing secret. Reusing that name would mean whichever product was
// configured last silently broke the other's signature checks -- exactly the
// collision api/sairncash/firebase-config.js was renamed to avoid.
//
// REQUIRES env: SAIRNCASH_STRIPE_WEBHOOK_SECRET,
//               SAIRNCASH_FIREBASE_SERVICE_ACCOUNT,
//               SAIRNCASH_FIREBASE_DATABASE_URL.
// ---------------------------------------------------------------------------

const { rtdbUpdate, rtdbGet } = require('../_lib/firebase-admin.js');

const HANDLED = [
  'checkout.session.completed',
  'customer.subscription.updated',
  'customer.subscription.deleted',
  'invoice.payment_failed',
  'invoice.payment_succeeded'
];

function readRawBody(req) {
  return new Promise((resolve, reject) => {
    let data = '';
    req.on('data', (chunk) => { data += chunk; });
    req.on('end', () => resolve(data));
    req.on('error', reject);
  });
}

// Stripe puts the customer id in a different place on each object shape. Never
// read it from anything the caller could choose -- it always comes off the
// verified event payload.
function customerIdFrom(obj) {
  if (!obj) return null;
  const c = obj.customer;
  if (typeof c === 'string') return c;
  if (c && typeof c === 'object' && c.id) return c.id;
  return null;
}

function subscriptionIdFrom(event) {
  const o = event.data && event.data.object;
  if (!o) return null;
  if (event.type.indexOf('customer.subscription') === 0) return o.id || null;
  const s = o.subscription;
  if (typeof s === 'string') return s;
  if (s && typeof s === 'object' && s.id) return s.id;
  return null;
}

// Maps an event onto the advisory mirror. Returns null for an event that
// carries no customer -- logged and skipped rather than written somewhere
// arbitrary.
function mirrorFor(event) {
  const o = (event.data && event.data.object) || {};
  const customerId = customerIdFrom(o);
  if (!customerId) return null;

  const patch = {
    lastEvent: event.type,
    lastEventId: event.id,
    // Stripe's own event timestamp, not ours -- see the ordering guard below.
    lastEventAt: event.created,
    updatedBy: 'stripe-webhook'
  };

  const subId = subscriptionIdFrom(event);
  if (subId) patch.subscriptionId = subId;

  if (event.type === 'checkout.session.completed') {
    patch.status = 'active';
    patch.paymentFailed = false;
  } else if (event.type === 'customer.subscription.updated') {
    patch.status = o.status || 'unknown';
    // past_due / unpaid mean Stripe is still retrying; both are dunning states.
    patch.paymentFailed = (o.status === 'past_due' || o.status === 'unpaid');
    if (o.current_period_end) patch.currentPeriodEnd = o.current_period_end;
    patch.cancelAtPeriodEnd = !!o.cancel_at_period_end;
  } else if (event.type === 'customer.subscription.deleted') {
    patch.status = 'canceled';
    patch.paymentFailed = false;
    patch.cancelAtPeriodEnd = false;
  } else if (event.type === 'invoice.payment_failed') {
    patch.paymentFailed = true;
    patch.failedAttempts = typeof o.attempt_count === 'number' ? o.attempt_count : null;
    // Deliberately does NOT set status. Stripe decides when a failed payment
    // becomes past_due or unpaid; asserting it here would put this file ahead
    // of the authority it is mirroring.
  } else if (event.type === 'invoice.payment_succeeded') {
    patch.paymentFailed = false;
    patch.failedAttempts = 0;
  }

  return { customerId, patch };
}

async function handleEvent(event) {
  const m = mirrorFor(event);
  if (!m) {
    console.warn('sairncash stripe-webhook: ' + event.type + ' (' + event.id + ') carries no customer id -- skipped, nothing written');
    return;
  }
  const base = 'sairncash/customers/' + m.customerId;

  // IDEMPOTENCY. Stripe retries, and retries are expected rather than
  // exceptional. Keying the audit entry by Stripe's own event id means a
  // replay overwrites the identical record instead of appending a duplicate.
  await rtdbUpdate(base + '/billingEvents/' + event.id, {
    type: event.type,
    created: event.created,
    receivedAt: Date.now()
  });

  // ORDERING GUARD. Stripe does not guarantee delivery order, and a retried
  // OLD event arriving after a newer one would otherwise roll the mirror
  // backwards -- showing a cancelled customer as active, or clearing a real
  // dunning flag. Compare against the stored event timestamp and skip a stale
  // write. The audit entry above is written either way, because "we received
  // this late" is itself worth having on record.
  let existingAt = null;
  try {
    existingAt = await rtdbGet(base + '/billing/lastEventAt');
  } catch (e) {
    // A read failure must not become a silent skip of the write -- fall
    // through and apply it, which is the same behaviour as no prior state.
    console.error('sairncash stripe-webhook: could not read prior billing state:', e.message);
  }
  if (typeof existingAt === 'number' && typeof m.patch.lastEventAt === 'number' && m.patch.lastEventAt < existingAt) {
    console.warn('sairncash stripe-webhook: ' + event.type + ' (' + event.id + ') is older than the stored state -- mirror left alone');
    return;
  }

  await rtdbUpdate(base + '/billing', m.patch);
}

module.exports = async (req, res) => {
  if (req.method !== 'POST') {
    res.status(405).json({ error: { message: 'Method not allowed — POST only' } });
    return;
  }

  const secret = process.env.SAIRNCASH_STRIPE_WEBHOOK_SECRET;
  const stripeKey = process.env.STRIPE_SECRET_KEY;
  if (!secret || !stripeKey) {
    console.error('SAIRNCASH_STRIPE_WEBHOOK_SECRET / STRIPE_SECRET_KEY not set in environment variables');
    res.status(500).json({ error: { message: 'Server configuration error — contact support' } });
    return;
  }

  let rawBody;
  try {
    rawBody = await readRawBody(req);
  } catch (err) {
    res.status(400).json({ error: { message: 'Could not read request body' } });
    return;
  }

  let event;
  try {
    const Stripe = require('stripe');
    const stripe = new Stripe(stripeKey);
    event = stripe.webhooks.constructEvent(rawBody, req.headers['stripe-signature'], secret);
  } catch (err) {
    // Covers a bad signature, a missing header, a replayed old timestamp and a
    // malformed payload alike. The detail goes to the log; the caller gets a
    // fixed string, same standard as verify.js and checkout.js.
    console.error('sairncash stripe-webhook: signature verification failed:', err.message);
    res.status(400).json({ error: { message: 'Invalid Stripe signature' } });
    return;
  }

  if (HANDLED.indexOf(event.type) === -1) {
    // Not an error. Stripe sends what the endpoint is subscribed to, and an
    // unhandled type is a no-op rather than a failure.
    res.status(200).json({ received: true, handled: false });
    return;
  }

  try {
    await handleEvent(event);
    res.status(200).json({ received: true, handled: true });
  } catch (err) {
    // The signature was valid, so this IS a genuine Stripe event; something
    // downstream failed. Return 200 so Stripe does not retry forever against a
    // problem retrying cannot fix, and make the log the thing to watch. This is
    // safe here in a way it would not be for an entitlement writer: the mirror
    // is advisory, so a lost write costs a stale banner, not lost access.
    console.error('sairncash stripe-webhook handling error:', err);
    res.status(200).json({ received: true, handled: false, warning: 'handled with errors, see server logs' });
  }
};

module.exports.handleEvent = handleEvent;
module.exports.mirrorFor = mirrorFor;
module.exports.customerIdFrom = customerIdFrom;
module.exports.subscriptionIdFrom = subscriptionIdFrom;
module.exports.HANDLED = HANDLED;
