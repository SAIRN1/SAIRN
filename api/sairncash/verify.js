// api/sairncash/verify.js
// Verifies a SAIRNcash subscription two ways:
//   1. sessionId -- right after Stripe Checkout returns (original path,
//      ported from ~/Downloads/SAIRNtype_PRO (1)/sairntype_stripe/api/verify.js).
//   2. subscriptionId -- real per-load re-verification added 2026-08-10 to
//      close the audit-found gap where the client's isSubscribed() never
//      re-checked the real Stripe state after the initial checkout return,
//      making a forged localStorage.sairncash_sub grant permanent free
//      access. Both branches return the same shape so the client's
//      saveSub(data) works unchanged either way.
//
// REQUIRES env: STRIPE_SECRET_KEY.
// REQUIRES env (2026-08-19, real-auth fix): SAIRNCASH_FIREBASE_SERVICE_ACCOUNT
// -- see api/_lib/firebase-admin.js's header. Same best-effort degrade as
// trial-verify.js: a firebaseToken mint failure never fails subscription
// verification itself, that's this endpoint's real purpose.

const { mintCustomToken } = require('../_lib/firebase-admin.js');

async function mintFirebaseToken(customerId) {
  if (!customerId) return null;
  try {
    return await mintCustomToken(customerId);
  } catch (e) {
    console.error('SAIRNcash verify: mintCustomToken failed:', e.message);
    return null;
  }
}

module.exports = async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') { res.status(204).end(); return; }
  if (req.method !== 'POST') { res.status(405).end(); return; }

  const stripeKey = process.env.STRIPE_SECRET_KEY;
  if (!stripeKey) { res.status(500).json({ error: 'Not configured' }); return; }

  try {
    const sessionId = req.body && req.body.sessionId;
    const subscriptionId = req.body && req.body.subscriptionId;
    if (!sessionId && !subscriptionId) {
      res.status(400).json({ error: 'Missing sessionId or subscriptionId' });
      return;
    }

    const Stripe = require('stripe');
    const stripe = new Stripe(stripeKey);

    if (sessionId) {
      const session = await stripe.checkout.sessions.retrieve(sessionId, {
        expand: ['subscription', 'customer']
      });
      if (session.payment_status !== 'paid' && session.status !== 'complete') {
        res.status(402).json({ error: 'Payment not complete' });
        return;
      }
      const contact = session.customer_details || {};
      const sub = session.subscription;
      const customerObj = session.customer;
      const customerId = typeof customerObj === 'string' ? customerObj : (customerObj && customerObj.id);
      res.status(200).json({
        valid: true,
        email: contact.email || '',
        name: contact.name || '',
        plan: 'SAIRNcash Pro',
        price: '$9.99/month',
        subscriptionId: typeof sub === 'string' ? sub : (sub && sub.id),
        // Real customer.id (not the transient checkout session id) -- the
        // stable identifier every Firebase sync path is scoped by
        // (2026-08-10, closes the global-shared-path data-isolation bug
        // found while designing the tax/retirement estimator: this ID
        // survives a plan change or resubscribe, subscriptionId doesn't).
        customerId: customerId,
        // firebaseToken (2026-08-19) -- see mintFirebaseToken() above.
        firebaseToken: await mintFirebaseToken(customerId),
        expiresAt: sub && sub.current_period_end
          ? new Date(sub.current_period_end * 1000).toISOString()
          : null
      });
      return;
    }

    // Real per-load re-verification path -- looks the subscription up
    // directly by ID rather than trusting anything the client claims
    // beyond which ID to check.
    const sub = await stripe.subscriptions.retrieve(subscriptionId, {
      expand: ['customer']
    });
    const active = sub.status === 'active' || sub.status === 'trialing';
    if (!active) {
      res.status(200).json({ valid: false });
      return;
    }
    const customer = sub.customer && typeof sub.customer === 'object' ? sub.customer : {};
    const customerId = customer.id || (typeof sub.customer === 'string' ? sub.customer : undefined);
    res.status(200).json({
      valid: true,
      email: customer.email || '',
      name: customer.name || '',
      plan: 'SAIRNcash Pro',
      price: '$9.99/month',
      subscriptionId: sub.id,
      customerId: customerId,
      // firebaseToken (2026-08-19) -- see mintFirebaseToken() above.
      firebaseToken: await mintFirebaseToken(customerId),
      expiresAt: sub.current_period_end
        ? new Date(sub.current_period_end * 1000).toISOString()
        : null
    });
  } catch (err) {
    console.error('SAIRNcash Stripe verify error:', err.message);
    res.status(500).json({ error: err.message });
  }
};
