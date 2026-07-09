// api/agent/stripe-webhook.js
// Automatically flips an agent from trial to paid the moment Stripe confirms
// a real payment — closes the gap flagged in scripts/mark-agent-paid.js
// ("no Stripe webhook wired up yet").
//
// SIGNATURE VERIFICATION is implemented directly with Node's built-in `crypto`
// module rather than the `stripe` npm package — this repo has no package.json
// / npm dependencies today, and Stripe's signature scheme is a simple,
// well-documented HMAC-SHA256 check that doesn't need a full SDK just for this.
//
// RAW BODY — IMPORTANT VERCEL-SPECIFIC NOTE: Stripe's signature is computed
// over the exact raw request bytes. The usual Next.js fix for this
// (`export const config = { api: { bodyParser: false } }`) does NOT work here
// — this repo uses plain Vercel serverless functions with no framework, and
// that config export is only honored inside Next.js API routes. Confirmed via
// Vercel's own community discussions (vercel/vercel#5213, #4524) that plain
// serverless functions never see that config at all. The fix that DOES work
// for a plain function like this one: read the raw stream directly via
// `req.on('data'/'end')` and never touch `req.body` (accessing `req.body`
// is what triggers Vercel's automatic JSON parsing in the first place).
// That's exactly what this file does below — do not "simplify" this to use
// req.body, it will break signature verification silently.
//
// SETUP (Stripe dashboard):
//   1. Developers > Webhooks > Add endpoint
//   2. URL: https://sairn.vercel.app/api/agent/stripe-webhook
//   3. Events to send: checkout.session.completed, customer.subscription.updated,
//      customer.subscription.deleted
//   4. Copy the "Signing secret" (whsec_...) into Vercel env var STRIPE_WEBHOOK_SECRET
//
// LINKING A PAYMENT TO AN AGENT: whoever creates the Stripe Checkout Session or
// Subscription for a customer must set client_reference_id (or
// metadata.agent_id) to that customer's sairn_agents.id. This file reads
// EITHER field, preferring metadata.agent_id if both are present. Creating
// that checkout session is NOT built here — this file only handles the
// receiving side of a payment that's already been set up to reference an
// agent_id. If nothing sets that reference, this webhook has nothing to act on
// and will log a warning and no-op — it will not silently mark the wrong agent.
//
// REQUIRES: STRIPE_WEBHOOK_SECRET, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY as
// Vercel env vars. Never hardcode any of these — Guardian check 22 blocks any
// push with a hardcoded key.

const crypto = require('crypto');

module.exports = async (req, res) => {
  if (req.method !== 'POST') {
    res.status(405).json({ error: { message: 'Method not allowed — POST only' } });
    return;
  }

  const WEBHOOK_SECRET = process.env.STRIPE_WEBHOOK_SECRET;
  const SUPABASE_URL = process.env.SUPABASE_URL;
  const SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!WEBHOOK_SECRET || !SUPABASE_URL || !SERVICE_KEY) {
    console.error('STRIPE_WEBHOOK_SECRET / SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set in environment variables');
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

  const sigHeader = req.headers['stripe-signature'];
  if (!sigHeader || !verifyStripeSignature(rawBody, sigHeader, WEBHOOK_SECRET)) {
    console.error('stripe-webhook: signature verification failed');
    res.status(400).json({ error: { message: 'Invalid Stripe signature' } });
    return;
  }

  let event;
  try {
    event = JSON.parse(rawBody);
  } catch (err) {
    res.status(400).json({ error: { message: 'Invalid JSON payload' } });
    return;
  }

  try {
    await handleEvent(event, SUPABASE_URL, SERVICE_KEY);
    res.status(200).json({ received: true });
  } catch (err) {
    // Signature was valid, so this IS a genuine Stripe event — but something
    // downstream (e.g. a transient Supabase error) failed. Log loudly and
    // still return 200 so Stripe doesn't hammer retries forever on an event
    // type we may not even act on; the log is the thing to actually watch.
    console.error('stripe-webhook handling error:', err);
    res.status(200).json({ received: true, warning: 'handled with errors, see server logs' });
  }
};

function readRawBody(req) {
  return new Promise((resolve, reject) => {
    let data = '';
    req.on('data', (chunk) => { data += chunk; });
    req.on('end', () => resolve(data));
    req.on('error', reject);
  });
}

function verifyStripeSignature(rawBody, sigHeader, secret) {
  const parts = {};
  sigHeader.split(',').forEach((kv) => {
    const idx = kv.indexOf('=');
    if (idx > -1) parts[kv.slice(0, idx)] = kv.slice(idx + 1);
  });
  const timestamp = parts.t;
  const v1 = parts.v1;
  if (!timestamp || !v1) return false;

  // Replay protection — reject anything claiming to be older than 5 minutes.
  const ageSeconds = Math.abs(Date.now() / 1000 - Number(timestamp));
  if (!Number.isFinite(ageSeconds) || ageSeconds > 300) return false;

  const signedPayload = timestamp + '.' + rawBody;
  const expected = crypto.createHmac('sha256', secret).update(signedPayload).digest('hex');

  const expectedBuf = Buffer.from(expected, 'utf8');
  const givenBuf = Buffer.from(v1, 'utf8');
  if (expectedBuf.length !== givenBuf.length) return false;
  return crypto.timingSafeEqual(expectedBuf, givenBuf);
}

async function handleEvent(event, SUPABASE_URL, SERVICE_KEY) {
  const headers = { apikey: SERVICE_KEY, Authorization: 'Bearer ' + SERVICE_KEY, 'Content-Type': 'application/json' };

  if (event.type === 'checkout.session.completed') {
    const session = event.data.object;
    const agentId = (session.metadata && session.metadata.agent_id) || session.client_reference_id;
    if (!agentId) {
      console.warn('checkout.session.completed had no agent_id in metadata or client_reference_id — nothing to update.');
      return;
    }
    await setPlanStatus(SUPABASE_URL, headers, agentId, 'paid');
    return;
  }

  if (event.type === 'customer.subscription.updated') {
    const sub = event.data.object;
    const agentId = sub.metadata && sub.metadata.agent_id;
    if (!agentId) return;
    if (sub.status === 'active' || sub.status === 'trialing') {
      await setPlanStatus(SUPABASE_URL, headers, agentId, 'paid');
    } else if (sub.status === 'canceled' || sub.status === 'unpaid' || sub.status === 'past_due') {
      await setPlanStatus(SUPABASE_URL, headers, agentId, 'canceled');
    }
    return;
  }

  if (event.type === 'customer.subscription.deleted') {
    const sub = event.data.object;
    const agentId = sub.metadata && sub.metadata.agent_id;
    if (!agentId) return;
    await setPlanStatus(SUPABASE_URL, headers, agentId, 'canceled');
    return;
  }

  // Any other event type is intentionally ignored — not an error, just not
  // one this endpoint acts on.
}

async function setPlanStatus(SUPABASE_URL, headers, agentId, planStatus) {
  const res = await fetch(SUPABASE_URL + '/rest/v1/sairn_agents?id=eq.' + agentId, {
    method: 'PATCH',
    headers: { ...headers, Prefer: 'return=minimal' },
    body: JSON.stringify({ plan_status: planStatus })
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error('Failed to set plan_status for agent ' + agentId + ': ' + text);
  }
  console.log('Agent ' + agentId + ' plan_status set to "' + planStatus + '" via Stripe webhook.');
}
