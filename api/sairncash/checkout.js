// api/sairncash/checkout.js
// Creates a real Stripe Checkout Session for a SAIRNcash Pro subscription.
// Ported from ~/Downloads/SAIRNtype_PRO (1)/sairntype_stripe/api/checkout.js
// (confirmed genuine, correct Stripe integration during the 2026-08-10
// SAIRNcash pivot audit) -- converted from ESM `export default` to this
// repo's CommonJS convention (package.json has no "type":"module", every
// other api/*.js file here uses module.exports).
//
// REQUIRES env: STRIPE_SECRET_KEY, STRIPE_PRICE_ID (SAIRNcash's own Stripe
// price -- not yet confirmed provisioned in this Vercel project as of
// 2026-08-10; see docs/superpowers/plans/2026-08-10-sairncash-pivot-foundation.md
// Task 1 Step 1). SITE_URL optional, defaults to https://sairn.vercel.app.

const stripeConfig = require('../_lib/stripe-config');

module.exports = async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') { res.status(204).end(); return; }
  if (req.method !== 'POST') { res.status(405).end(); return; }

  const stripeKey = process.env.STRIPE_SECRET_KEY;
  const priceId = process.env.STRIPE_PRICE_ID;
  const siteUrl = process.env.SITE_URL || 'https://sairn.vercel.app';

  // ── ONE PLACE ANSWERS "IS STRIPE CONFIGURED" (2026-09-14, item 94) ──────
  // This condition used to live here, and it answered "Stripe not configured"
  // when STRIPE_PRICE_ID was missing while the KEY was set the whole time.
  // That message was then read as evidence about the key by three separate
  // readers -- the SOUP register, a comment in ai.js, and a comment in
  // sairncash.html -- and none of them could see the disagreement, because no
  // file held the whole answer. The requirement list now lives in
  // api/_lib/stripe-config.js and nowhere else.
  //
  // THE LOG NAMES THE VARIABLE AND THE RESPONSE DOES NOT. This endpoint is
  // unauthenticated, so telling a caller which variable is missing tells them
  // about the deployment; and a per-endpoint message is exactly what invited
  // readers to infer a cause last time.
  const cfg = stripeConfig.status('checkout');
  if (!cfg.ready) {
    console.error(cfg.logMessage);
    res.status(500).json({ error: cfg.clientMessage });
    return;
  }
  if (cfg.warnings.length) console.error(cfg.logMessage);

  try {
    const email = (req.body && req.body.email) || undefined;

    const Stripe = require('stripe');
    // apiVersion PINNED (2026-09-15). Without it this inherits whatever the
    // installed SDK happens to default to, so bumping `"stripe": "^17.4.0"`
    // would move the WIRE FORMAT on a live payments path as a side effect of a
    // dependency change -- two changes, one of them not in the diff.
    // api/_lib/stripe-api-version.js carries the value and the upgrade order.
    const { STRIPE_API_VERSION } = require('../_lib/stripe-api-version');
    const stripe = new Stripe(stripeKey, { apiVersion: STRIPE_API_VERSION });

    const session = await stripe.checkout.sessions.create({
      mode: 'subscription',
      payment_method_types: ['card'],
      line_items: [{ price: priceId, quantity: 1 }],
      customer_email: email,
      success_url: siteUrl + '/sairncash?session_id={CHECKOUT_SESSION_ID}',
      cancel_url: siteUrl + '/sairncash?cancelled=true',
      subscription_data: { metadata: { product: 'SAIRNcash Pro' } },
      metadata: { product: 'SAIRNcash Pro' },
      allow_promotion_codes: true
    });

    res.status(200).json({ url: session.url, sessionId: session.id });
  } catch (err) {
    // Same disclosure fix as verify.js (2026-09-01) -- Stripe's error text is
    // descriptive by design and this endpoint is unauthenticated. This is the
    // one that matters most once a real key is live, because it is the endpoint
    // a stranger can reach with an unlimited number of tries.
    // Error SHAPE deliberately unchanged: sairncash.html reads
    // `data.error || 'Could not start checkout'` and expects a string, not the
    // {error:{message}} envelope the natively-built trial endpoints use.
    console.error('SAIRNcash Stripe checkout error:', err.message);
    res.status(500).json({ error: 'Could not start checkout' });
  }
};
