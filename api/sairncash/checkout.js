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

module.exports = async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') { res.status(204).end(); return; }
  if (req.method !== 'POST') { res.status(405).end(); return; }

  const stripeKey = process.env.STRIPE_SECRET_KEY;
  const priceId = process.env.STRIPE_PRICE_ID;
  const siteUrl = process.env.SITE_URL || 'https://sairn.vercel.app';

  if (!stripeKey || !priceId) {
    res.status(500).json({ error: 'Stripe not configured' });
    return;
  }

  try {
    const email = (req.body && req.body.email) || undefined;

    const Stripe = require('stripe');
    const stripe = new Stripe(stripeKey);

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
