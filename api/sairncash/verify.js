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

const stripeConfig = require('../_lib/stripe-config');

module.exports = async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') { res.status(204).end(); return; }
  if (req.method !== 'POST') { res.status(405).end(); return; }

  // ONE PLACE ANSWERS "IS STRIPE CONFIGURED" (2026-09-14, item 94). The
  // requirement list lives in api/_lib/stripe-config.js; five files used to
  // re-derive it and three disagreed. `ready` means THE VARIABLES ARE PRESENT
  // and never that Stripe works -- on 2026-09-14 the key was present and an
  // expired sk_test_ one.
  const cfg = stripeConfig.status('verify');
  if (!cfg.ready) {
    console.error(cfg.logMessage);
    res.status(500).json({ error: cfg.clientMessage });
    return;
  }
  if (cfg.warnings.length) console.error(cfg.logMessage);
  const stripeKey = process.env.STRIPE_SECRET_KEY;

  try {
    const sessionId = req.body && req.body.sessionId;
    const subscriptionId = req.body && req.body.subscriptionId;
    if (!sessionId && !subscriptionId) {
      res.status(400).json({ error: 'Missing sessionId or subscriptionId' });
      return;
    }

    const Stripe = require('stripe');
    // apiVersion PINNED (2026-09-15). Without it this inherits whatever the
    // installed SDK happens to default to, so bumping `"stripe": "^17.4.0"`
    // would move the WIRE FORMAT on a live payments path as a side effect of a
    // dependency change -- two changes, one of them not in the diff.
    // api/_lib/stripe-api-version.js carries the value and the upgrade order.
    const { STRIPE_API_VERSION } = require('../_lib/stripe-api-version');
    const stripe = new Stripe(stripeKey, { apiVersion: STRIPE_API_VERSION });

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
    // ══ THE MINT ON THIS BRANCH NOW REQUIRES A SECOND IDENTIFIER, 2026-10-11 ══
    // WHAT WAS WRONG. api/_lib/firebase-admin.js:66-69 states the precondition
    // for minting in its own words: the uid "can be trusted by RTDB rules as
    // exactly the customer this request already proved ownership of via a real
    // trial/license check higher up the call stack". This branch did no such
    // check. An unauthenticated POST carrying nothing but a `subscriptionId`
    // came back with a Firebase custom token for that subscription's customer
    // -- a real auth credential for somebody else's SAIRNcash data, minted off
    // one bearer string. Reported by hover2 (seq681); reproducing artifact
    // .claude/skills/sairn-hover-auditor/tools-hover2/
    // sairncash_verify_token_mint_repro.py, exit 1 before this change.
    //
    // WHAT THIS IS AND IS NOT, because overstating it would be worse than the
    // gap. SAIRNcash HAS NO LOGIN. There is no password, no session and no
    // identity to check against -- a guest Stripe checkout is the whole
    // enrolment. So this cannot become real authentication, and it is not
    // claimed to be. What it does is make the implicit assumption EXPLICIT and
    // ENFORCED: a caller must now present BOTH the subscription id AND the
    // Stripe customer id, and the customer id is checked against what Stripe
    // returns for that subscription rather than taken as given. A leaked
    // subscriptionId alone no longer mints anything.
    //
    // IT BREAKS NO WORKING CLIENT, and that was READ rather than assumed.
    // initFirebase() at sairncash.html:484 already refuses to sync unless the
    // stored record holds BOTH customerId and firebaseToken. So every user who
    // has working sync today necessarily has customerId stored and will send
    // it; a record without customerId was already getting
    // "Sync unavailable -- no verified customer yet" and loses nothing.
    //
    // THE REFUSAL IS NAMED, NOT SILENT. Verification itself still succeeds --
    // that is this endpoint's stated purpose and a withheld token must not cost
    // a paying customer the app -- but the response says WHY the token is
    // absent instead of returning a bare null that is indistinguishable from a
    // Firebase outage. The outage case keeps returning null with no reason,
    // which is how the two stay distinguishable.
    //
    // THE sessionId BRANCH ABOVE IS DELIBERATELY NOT CHANGED, and the reason is
    // structural rather than an oversight: that branch IS the checkout return,
    // and it is where the client FIRST LEARNS its customerId. Requiring the
    // value as a precondition for issuing it is impossible. Its bearer string
    // is also a Checkout Session id that Stripe has just handed to the
    // purchaser in a redirect, rather than one sitting in localStorage across
    // every later page load. That asymmetry is recorded here because the next
    // reader will otherwise see one branch checked and one not and assume the
    // sweep was incomplete.
    const claimedCustomerId = req.body && req.body.customerId;
    let firebaseToken = null;
    let firebaseTokenWithheld = null;
    if (typeof claimedCustomerId !== 'string' || !claimedCustomerId) {
      firebaseTokenWithheld = 'CUSTOMER_ID_NOT_SUPPLIED';
    } else if (!customerId || String(claimedCustomerId) !== String(customerId)) {
      // MISMATCH AND ABSENCE ARE DIFFERENT FACTS and get different codes. An
      // absent id is an old or stale client; a mismatched one is a caller
      // asking for a token that is not theirs, and conflating the two would
      // hide the second inside the first.
      firebaseTokenWithheld = 'CUSTOMER_ID_MISMATCH';
    } else {
      firebaseToken = await mintFirebaseToken(customerId);
    }
    res.status(200).json({
      valid: true,
      email: customer.email || '',
      name: customer.name || '',
      plan: 'SAIRNcash Pro',
      price: '$9.99/month',
      subscriptionId: sub.id,
      customerId: customerId,
      // firebaseToken (2026-08-19) -- see mintFirebaseToken() above, and the
      // ownership precondition block directly above this response.
      firebaseToken: firebaseToken,
      firebaseTokenWithheld: firebaseTokenWithheld,
      expiresAt: sub.current_period_end
        ? new Date(sub.current_period_end * 1000).toISOString()
        : null
    });
  } catch (err) {
    // DO NOT RETURN err.message TO THE CALLER (fixed 2026-09-01).
    // Stripe's own error text is descriptive by design, and this endpoint is
    // unauthenticated -- an anonymous POST with any string as subscriptionId
    // was enough to get back
    //   "Expired API Key provided: sk_test_****...wz9bU6"
    // which discloses that a key exists, that it is a TEST key, its prefix and
    // its last six characters, to anyone who asks. That is how the stale key in
    // this project's environment was discovered, by a probe rather than by a
    // log. Upstream detail goes to the server log, where it belongs; the client
    // gets a fixed string it cannot mine.
    console.error('SAIRNcash Stripe verify error:', err.message);
    res.status(500).json({ error: 'Could not verify the subscription' });
  }
};
