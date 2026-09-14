// api/_lib/stripe-config.js
// The ONE place that answers "is Stripe configured for X".
//
// ── WHY THIS EXISTS, AND IT IS NOT TIDINESS ──────────────────────────────
// Five files read Stripe's env vars independently and three of them answered
// the same question differently. On 2026-09-14 that cost real time and produced
// two wrong entries in standing documents:
//
//   checkout.js   if (!stripeKey || !priceId) -> "Stripe not configured"
//   portal.js     if (!stripeKey)             -> "Not configured"
//   verify.js     if (!stripeKey)             -> "Not configured"
//   ai.js         if (!stripeKey)             -> reason 'CONFIG'
//   stripe-webhook.js  if (!secret || !stripeKey) -> console.error, 400
//
// checkout.js was answering "Stripe not configured" because STRIPE_PRICE_ID was
// missing. THE KEY WAS SET THE WHOLE TIME. That message was then read as
// evidence about the KEY by three separate readers: docs/SOUP-REGISTER.md
// recorded the key as unconfigured and the blast radius as zero; a comment in
// ai.js recorded "production's Stripe key does not work"; and a comment in
// sairncash.html says the 500 happens "because STRIPE_SECRET_KEY". One
// ambiguous string, four places that believed it, and nobody could see the
// disagreement because no file held the whole answer.
//
// THAT IS THE INFORMATION-LEAKAGE SHAPE EXACTLY: "what counts as configured"
// was not a fact any module owned, it was a condition each caller re-derived,
// so the callers could disagree and nothing could notice.
//
// ── WHAT IS HIDDEN BEHIND THIS INTERFACE ─────────────────────────────────
// Which env vars each capability needs, what counts as present, and what a
// caller may safely say out loud. A caller asks about a CAPABILITY and never
// about a variable.
//
// ── THE CLIENT MESSAGE AND THE LOG MESSAGE ARE DIFFERENT ON PURPOSE ──────
// Every one of these endpoints is unauthenticated, so naming the missing
// variable in the response would tell any caller about the deployment. The
// client message is therefore generic AND IDENTICAL across capabilities --
// deliberately, because the old per-file strings were what invited readers to
// infer a specific cause. The log message names the variable, because that is
// where somebody debugging is actually looking.
//
// ── AND THE STATE IT CANNOT SEE, SAID HERE RATHER THAN DISCOVERED ────────
// PRESENT IS NOT WORKING. Production's STRIPE_SECRET_KEY on 2026-09-14 was set,
// and was an EXPIRED sk_test_ key: every call died at Stripe with "Expired API
// Key provided". No env-var check can know that -- it needs a real API call --
// so `ready: true` from this module means THE VARIABLES ARE PRESENT and nothing
// more. A caller that treats it as "Stripe works" has made the same mistake
// this module was built to stop. `warnings` carries the one hint that IS
// visible without a call: a test key in a production deployment.

'use strict';

// One row per capability. The requirement list is the thing that used to be
// re-derived per file; it lives here now and nowhere else.
const CAPABILITIES = {
  checkout: ['STRIPE_SECRET_KEY', 'STRIPE_PRICE_ID'],
  portal: ['STRIPE_SECRET_KEY'],
  verify: ['STRIPE_SECRET_KEY'],
  ai: ['STRIPE_SECRET_KEY'],
  'webhook:sairncash': ['SAIRNCASH_STRIPE_WEBHOOK_SECRET', 'STRIPE_SECRET_KEY'],
  'webhook:agent': ['STRIPE_WEBHOOK_SECRET'],
};

// Said once, here, so no endpoint invents its own phrasing and no reader can
// infer a cause from it.
const CLIENT_MESSAGE = 'Payments are not configured on this server';

function present(name, env) {
  const v = env[name];
  return typeof v === 'string' && v.trim() !== '';
}

function warnings(env) {
  const out = [];
  const key = env.STRIPE_SECRET_KEY;
  // A test key in a production deployment. This is the ONLY unhealthy state
  // visible without calling Stripe, and it is worth surfacing because it looks
  // exactly like a healthy one to every `if (!stripeKey)` check on the platform.
  if (typeof key === 'string' && key.indexOf('sk_test_') === 0
      && String(env.VERCEL_ENV || '').toLowerCase() === 'production') {
    out.push('STRIPE_SECRET_KEY is a TEST key (sk_test_) in a PRODUCTION '
             + 'deployment -- present, and every live call will fail');
  }
  return out;
}

/**
 * status(capability) -> {
 *   ready        every required variable is PRESENT. NOT "Stripe works".
 *   missing      the required variables that are absent, for logging only.
 *   warnings     states that are present-but-wrong, for logging only.
 *   clientMessage  safe to return to an unauthenticated caller.
 *   logMessage     names the variables; never send this to a client.
 * }
 * An unknown capability THROWS rather than returning not-ready: a typo that
 * silently reports "not configured" would take a working endpoint off the air
 * and look like a deployment problem.
 */
function status(capability, env) {
  env = env || process.env;
  const need = CAPABILITIES[capability];
  if (!need) {
    throw new Error('stripe-config: unknown capability ' + JSON.stringify(capability)
      + '. Known: ' + Object.keys(CAPABILITIES).join(', '));
  }
  const missing = need.filter((n) => !present(n, env));
  const warn = warnings(env);
  return {
    ready: missing.length === 0,
    missing: missing,
    warnings: warn,
    clientMessage: CLIENT_MESSAGE,
    logMessage: 'stripe ' + capability + ': '
      + (missing.length ? 'not set -- ' + missing.join(', ') : 'all variables present')
      + (warn.length ? ' | ' + warn.join(' | ') : ''),
  };
}

module.exports = { status, CAPABILITIES, CLIENT_MESSAGE };
