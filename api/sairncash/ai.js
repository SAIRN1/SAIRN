// api/sairncash/ai.js
// ---------------------------------------------------------------------------
// SAIRNcash's OWN authenticated AI path. Verifies a real paying subscription
// (or a live trial) SERVER-SIDE, then calls Anthropic in-process.
//
// ── WHY THIS FILE EXISTS (2026-09-05) ──────────────────────────────────────
// api/claude.js is getting a licence-key requirement, because it accepted
// requests with no credential at all and spent this platform's Anthropic key
// on them. Fifteen apps hold a SAIRN licence key and can simply send it.
//
// SAIRNCASH HAS NO LICENCE KEY AND NEVER DID. It is a consumer product: a user
// is a device id (sairncash_did) plus a Stripe subscription (sairncash_sub) or
// a trial token (sairncash_trial). Minting a SAIRN licence per subscriber
// would drag the B2B licence system into a consumer app it was not built for.
//
// So SAIRNcash moves OFF the shared proxy and onto this. That is not merely a
// compatibility patch -- IT CLOSES A REAL GAP OF ITS OWN. SAIRNcash's three AI
// call sites send is_demo:false, which until 2026-09-05 skipped every cost
// control on the shared proxy, and nothing anywhere checked that an AI caller
// was actually a subscriber. This endpoint is the first server-side
// paying-subscriber check SAIRNcash's AI has ever had.
//
// ── NOT A NEW PATTERN ──────────────────────────────────────────────────────
// api/law-auth.js:596 and api/sc-ai.js:259 already do exactly this: import
// callAnthropic() from api/claude.js and call it in-process after their own
// auth, rather than making a second HTTP hop back through that endpoint. Same
// shape here, so there is one place that talks to Anthropic and one place that
// caps max_tokens.
//
// ── WHAT IT DELIBERATELY DOES NOT DO ───────────────────────────────────────
// It does not trust anything the client says about its own status. The client
// sends an IDENTIFIER -- a subscriptionId or a trialToken -- and this file
// looks it up. localStorage.sairncash_sub is forgeable, and this app's own
// 2026-08-10 fix exists precisely because it used to be trusted. That lesson
// is not re-broken here.
//
// REQUIRES env: ANTHROPIC_API_KEY, STRIPE_SECRET_KEY,
//               SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY (trial path only).
// ---------------------------------------------------------------------------

const { callAnthropic } = require('../claude.js');

const APP_ID = 'sairncash';

async function subscriptionActive(subscriptionId) {
  const stripeKey = process.env.STRIPE_SECRET_KEY;
  if (!stripeKey) return { ok: false, reason: 'CONFIG' };
  try {
    const Stripe = require('stripe');
    const stripe = new Stripe(stripeKey);
    const sub = await stripe.subscriptions.retrieve(subscriptionId);
    return { ok: sub.status === 'active' || sub.status === 'trialing' };
  } catch (err) {
    // Stripe's own error text is descriptive by design and this endpoint is
    // reachable by anyone. api/sairncash/verify.js records the real incident
    // where returning err.message disclosed the API key's type and last six
    // characters to an anonymous probe. Detail goes to the log only.
    console.error('SAIRNcash ai: Stripe lookup failed:', err.message);
    // A SUBSCRIPTION THAT DOES NOT EXIST IS NOT AN OUTAGE, and the first
    // version of this file conflated them. Found by live-probing production
    // rather than by reading: a junk subscriptionId returned
    // 503 VERIFY_UNAVAILABLE with the message "this is not a problem with your
    // account" -- which is false, tells the caller to retry forever, and hides
    // a real invalid credential behind an infrastructure excuse.
    //
    // Stripe answers a missing object with an invalid-request error and a 4xx.
    // Those are the caller's problem and get the 401. Anything else -- a
    // network failure, a 5xx, an auth failure on OUR key -- is genuinely ours
    // and keeps the fail-closed 503. Both still spend nothing.
    const stripeStatus = Number(err && err.statusCode);
    const missing = (err && err.code === 'resource_missing')
      || (err && err.type === 'StripeInvalidRequestError')
      || (stripeStatus >= 400 && stripeStatus < 500 && stripeStatus !== 401 && stripeStatus !== 429);
    return { ok: false, reason: missing ? undefined : 'UPSTREAM' };
  }
}

async function trialActive(trialToken) {
  const url = process.env.SUPABASE_URL;
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !key) return { ok: false, reason: 'CONFIG' };
  try {
    const r = await fetch(url + '/rest/v1/sairncash_trial?trial_token=eq.'
      + encodeURIComponent(trialToken) + '&select=status,expires_at&limit=1',
      { headers: { apikey: key, Authorization: 'Bearer ' + key } });
    if (!r.ok) return { ok: false, reason: 'UPSTREAM' };
    const rows = await r.json();
    const row = Array.isArray(rows) && rows[0];
    if (!row) return { ok: false };
    if (String(row.status || '').toLowerCase() !== 'active') return { ok: false };
    // An expired trial is not an active one. Compared here rather than trusted
    // from `status`, because nothing sweeps that column on a schedule -- a row
    // can read `active` for as long as nobody looks at it.
    if (row.expires_at && new Date(row.expires_at).getTime() < Date.now()) {
      return { ok: false };
    }
    return { ok: true };
  } catch (err) {
    console.error('SAIRNcash ai: trial lookup failed:', err.message);
    return { ok: false, reason: 'UPSTREAM' };
  }
}

module.exports = async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') { res.status(204).end(); return; }
  if (req.method !== 'POST') {
    res.status(405).json({ error: { message: 'Method not allowed — POST only' } });
    return;
  }

  let body = req.body;
  if (typeof body === 'string') {
    try { body = JSON.parse(body); } catch (e) {
      res.status(400).json({ error: { message: 'Invalid JSON body' } });
      return;
    }
  }
  body = body || {};

  const subscriptionId = typeof body.subscriptionId === 'string' ? body.subscriptionId.trim() : '';
  const trialToken = typeof body.trialToken === 'string' ? body.trialToken.trim() : '';
  if (!subscriptionId && !trialToken) {
    res.status(401).json({ error: { code: 'NO_SUBSCRIPTION',
      message: 'A SAIRNcash subscription or an active trial is required.' } });
    return;
  }

  // THE SUBSCRIPTION IS CHECKED BEFORE THE BODY IS VALIDATED, deliberately.
  // This is the ordering lesson from api/sd-data.js and api/sd-sub-data.js: a
  // caller holding no credential must not be able to tell a malformed request
  // from a well-formed one, or learn what this endpoint expects, by which
  // refusal comes back. The 405 above stays first because it says nothing
  // about what exists.
  let auth = { ok: false };
  if (subscriptionId) auth = await subscriptionActive(subscriptionId);
  if (!auth.ok && auth.reason !== 'UPSTREAM' && auth.reason !== 'CONFIG' && trialToken) {
    auth = await trialActive(trialToken);
  }

  if (!auth.ok) {
    if (auth.reason === 'CONFIG') {
      console.error('SAIRNcash ai: STRIPE_SECRET_KEY / Supabase env not set');
      res.status(500).json({ error: { message: 'Server configuration error — contact support' } });
      return;
    }
    if (auth.reason === 'UPSTREAM') {
      // FAILS CLOSED, and that is a DIFFERENT call from the shared proxy's
      // fail-open licence check -- on purpose, so the divergence is a decision
      // rather than an inconsistency. There, failing open protects a paying
      // B2B customer whose licence store is unreachable, and the licence key
      // is not the only thing gating spend. Here the identifier is the ONLY
      // thing between a caller and the API key, so failing open would hand
      // free Anthropic spend to anyone sending a nonsense subscriptionId
      // during a Stripe outage. A consumer app losing its assistant for the
      // length of an outage is the cheaper failure, and it SAYS so rather
      // than pretending the account is at fault.
      res.status(503).json({ error: { code: 'VERIFY_UNAVAILABLE',
        message: 'Your subscription could not be verified just now, so the assistant is paused. This is not a problem with your account — please try again shortly.' } });
      return;
    }
    res.status(401).json({ error: { code: 'NO_SUBSCRIPTION',
      message: 'A SAIRNcash subscription or an active trial is required.' } });
    return;
  }

  if (!Array.isArray(body.messages) || body.messages.length === 0) {
    res.status(400).json({ error: { message: 'messages array is required' } });
    return;
  }

  // max_tokens is NOT capped here. callAnthropic() owns that ceiling, and
  // duplicating it would create a second number that can drift from the first
  // -- which is the shape this platform keeps finding in its own docs.
  const result = await callAnthropic({
    system: body.system,
    messages: body.messages,
    max_tokens: body.max_tokens,
    tools: body.tools
  });
  if (!result.ok) {
    res.status(result.status).json({ error: result.error });
    return;
  }
  res.status(200).json(result.data);
};

module.exports.APP_ID = APP_ID;
module.exports.subscriptionActive = subscriptionActive;
module.exports.trialActive = trialActive;
