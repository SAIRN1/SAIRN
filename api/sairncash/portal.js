// api/sairncash/portal.js
// ---------------------------------------------------------------------------
// Creates a Stripe Billing Portal session so a SAIRNcash subscriber can update
// their card, see invoices, or cancel.
//
// WHAT IT REPLACES. sairncash.html's "manage subscription" was an alert()
// reading "Manage or cancel at stripe.com" -- which is not a place. There is no
// stripe.com page a customer can log into to find a subscription they bought as
// a guest; the Billing Portal is the actual mechanism, and without it the only
// route to cancelling was emailing support.
//
// THE CUSTOMER ID IS NOT TAKEN AT FACE VALUE, and that is the whole security
// design of this file. A Billing Portal session for a customer id is full
// access to that customer's billing -- card details on file, invoice history,
// the power to cancel. If this endpoint accepted a customer id from the request
// body and used it, anyone who guessed or observed a cus_... string would get a
// working portal link for a stranger's account.
//
// So the caller sends a SUBSCRIPTION id, and the customer id is read off the
// subscription as Stripe returns it. That is the same shape as verify.js's
// re-verification path ("looks the subscription up directly by ID rather than
// trusting anything the client claims beyond which ID to check") and the same
// principle as api/sen-portal.js on SAIRNsenior, whose header states it
// plainly: the identifier the caller can edit is the vulnerability.
//
// It is not a perfect gate -- possession of a subscription id still gets you a
// portal for that subscription, so a leaked sub_... is a real credential. It is
// materially better than accepting a customer id, and it matches what the
// client already holds. Tightening it further needs a server-side session, which
// SAIRNcash does not have; recorded here rather than left to be discovered.
//
// REQUIRES env: STRIPE_SECRET_KEY. SITE_URL optional, defaults to the same
// value checkout.js uses.
// ---------------------------------------------------------------------------

module.exports = async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') { res.status(204).end(); return; }
  if (req.method !== 'POST') { res.status(405).json({ error: 'POST only' }); return; }

  const stripeKey = process.env.STRIPE_SECRET_KEY;
  if (!stripeKey) { res.status(500).json({ error: 'Not configured' }); return; }

  const subscriptionId = req.body && req.body.subscriptionId;
  if (!subscriptionId || typeof subscriptionId !== 'string') {
    res.status(400).json({ error: 'Missing subscriptionId' });
    return;
  }

  try {
    const Stripe = require('stripe');
    const stripe = new Stripe(stripeKey);

    const sub = await stripe.subscriptions.retrieve(subscriptionId);
    const customerId = typeof sub.customer === 'string' ? sub.customer : (sub.customer && sub.customer.id);
    if (!customerId) {
      res.status(404).json({ error: 'No customer on that subscription' });
      return;
    }

    const session = await stripe.billingPortal.sessions.create({
      customer: customerId,
      return_url: (process.env.SITE_URL || 'https://sairn.vercel.app') + '/sairncash'
    });

    res.status(200).json({ url: session.url });
  } catch (err) {
    // Same disclosure rule as verify.js and checkout.js -- Stripe's error text
    // is descriptive by design and this endpoint is unauthenticated.
    console.error('SAIRNcash portal error:', err.message);
    res.status(500).json({ error: 'Could not open the billing portal' });
  }
};
