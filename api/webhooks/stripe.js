// ================================================================
// SAIRN Stripe Webhook Handler -- api/webhooks/stripe.js
// Verifies stripe-signature, activates/deactivates licenses in
// Supabase, and sends welcome email via Resend on new subscriptions.
//
// Events handled:
//   checkout.session.completed     -> activate org + send welcome
//   customer.subscription.deleted  -> deactivate org
//
// Env vars required:
//   STRIPE_SECRET_KEY
//   STRIPE_WEBHOOK_SECRET
//   SUPABASE_URL
//   SUPABASE_SERVICE_ROLE_KEY
//   RESEND_API_KEY
//   RESEND_FROM_EMAIL
//
// Stripe webhook URL to register:
//   https://sairn.vercel.app/api/webhooks/stripe
// ================================================================

import Stripe from 'stripe';
import { createClient } from '@supabase/supabase-js';

// Vercel: must disable body parser so we can read the raw bytes
// that Stripe uses to compute the signature.
export const config = { api: { bodyParser: false } };

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY);

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
);

// ----------------------------------------------------------------
// Collect the raw request body as a Buffer.
// Vercel streams the body when bodyParser is disabled.
// ----------------------------------------------------------------
function getRawBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    req.on('data', chunk => chunks.push(chunk));
    req.on('end', () => resolve(Buffer.concat(chunks)));
    req.on('error', reject);
  });
}

// ----------------------------------------------------------------
// Welcome email via Resend (called directly -- no self-fetch to
// /api/email needed since we're already on the server).
// ----------------------------------------------------------------
async function sendWelcomeEmail({ to, shopName, planName, appName }) {
  const key  = process.env.RESEND_API_KEY;
  const from = process.env.RESEND_FROM_EMAIL || 'onboarding@resend.dev';
  if (!key || !to) return;

  const subject = `Welcome to ${appName || 'SAIRN'} -- you're all set`;
  const html = `
    <div style="font-family:system-ui,sans-serif;max-width:560px;margin:0 auto;background:#ffffff;padding:40px 32px;border-radius:12px;">
      <div style="font-size:28px;font-weight:900;color:#0f172a;margin-bottom:8px;">Welcome to SAIRN</div>
      <div style="font-size:15px;color:#475569;margin-bottom:24px;">Your subscription is active and your account is ready.</div>
      <table style="width:100%;border-collapse:collapse;margin-bottom:28px;">
        <tr>
          <td style="padding:10px 0;border-bottom:1px solid #e2e8f0;color:#64748b;font-size:13px;">Shop / Business</td>
          <td style="padding:10px 0;border-bottom:1px solid #e2e8f0;font-weight:600;font-size:13px;">${shopName || 'Your account'}</td>
        </tr>
        <tr>
          <td style="padding:10px 0;border-bottom:1px solid #e2e8f0;color:#64748b;font-size:13px;">Plan</td>
          <td style="padding:10px 0;border-bottom:1px solid #e2e8f0;font-weight:600;font-size:13px;">${planName || 'B2B'}</td>
        </tr>
        <tr>
          <td style="padding:10px 0;color:#64748b;font-size:13px;">App</td>
          <td style="padding:10px 0;font-weight:600;font-size:13px;">${appName || 'SAIRN Platform'} + SAIRNbiz (included)</td>
        </tr>
      </table>
      <a href="https://sairn.vercel.app" style="display:inline-block;background:#0f172a;color:#ffffff;text-decoration:none;padding:12px 28px;border-radius:8px;font-weight:600;font-size:14px;">Open your app</a>
      <div style="margin-top:32px;font-size:12px;color:#94a3b8;">
        Questions? Reply to this email or reach us at michael@sairn.com
      </div>
    </div>
  `;

  await fetch('https://api.resend.com/emails', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${key}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      from: `SAIRN <${from}>`,
      to: [to],
      subject,
      html,
      text: `Welcome to SAIRN. Your ${planName || 'B2B'} subscription for ${shopName || 'your account'} is active. Open your app at https://sairn.vercel.app`,
    }),
  });
}

// ----------------------------------------------------------------
// Activate org in Supabase: set status=active, store Stripe IDs.
// Looks up by stripe_customer first; falls back to contact_email.
// Upserts so a missing org row doesn't silently fail.
// ----------------------------------------------------------------
async function activateOrg({ stripeCustomerId, subscriptionId, email, shopName, planName }) {
  // Try to find existing org by Stripe customer ID
  let { data: org } = await supabase
    .from('organizations')
    .select('id, name, contact_email')
    .eq('stripe_customer', stripeCustomerId)
    .maybeSingle();

  // Fall back to email match
  if (!org && email) {
    ({ data: org } = await supabase
      .from('organizations')
      .select('id, name, contact_email')
      .eq('contact_email', email)
      .maybeSingle());
  }

  if (org) {
    await supabase
      .from('organizations')
      .update({
        status:              'active',
        stripe_customer:     stripeCustomerId,
        stripe_subscription: subscriptionId,
        plan:                planName || org.plan || 'b2b_starter',
        updated_at:          new Date().toISOString(),
      })
      .eq('id', org.id);
    return org;
  }

  // No existing org -- create one so billing is tracked even if
  // the shop hasn't been provisioned yet via the app.
  const { data: newOrg } = await supabase
    .from('organizations')
    .insert({
      name:                shopName || email || 'New SAIRN Customer',
      status:              'active',
      stripe_customer:     stripeCustomerId,
      stripe_subscription: subscriptionId,
      plan:                planName || 'b2b_starter',
      contact_email:       email || null,
    })
    .select('id, name, contact_email')
    .single();

  return newOrg;
}

// ----------------------------------------------------------------
// Deactivate org: set status=cancelled, clear subscription ID.
// ----------------------------------------------------------------
async function deactivateOrg({ stripeCustomerId, subscriptionId }) {
  // Match on customer ID first, then subscription ID as fallback
  let query = supabase
    .from('organizations')
    .update({
      status:              'cancelled',
      stripe_subscription: null,
      updated_at:          new Date().toISOString(),
    });

  if (stripeCustomerId) {
    query = query.eq('stripe_customer', stripeCustomerId);
  } else if (subscriptionId) {
    query = query.eq('stripe_subscription', subscriptionId);
  } else {
    return; // nothing to match on
  }

  await query;
}

// ----------------------------------------------------------------
// Main handler
// ----------------------------------------------------------------
export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const sig    = req.headers['stripe-signature'];
  const secret = process.env.STRIPE_WEBHOOK_SECRET;

  if (!sig)    return res.status(400).json({ error: 'Missing stripe-signature header' });
  if (!secret) return res.status(500).json({ error: 'STRIPE_WEBHOOK_SECRET not configured' });

  // Read raw body -- required for signature verification
  let rawBody;
  try {
    rawBody = await getRawBody(req);
  } catch (err) {
    return res.status(400).json({ error: 'Could not read request body' });
  }

  // Verify signature
  let event;
  try {
    event = stripe.webhooks.constructEvent(rawBody, sig, secret);
  } catch (err) {
    console.error('[stripe webhook] signature verification failed:', err.message);
    return res.status(400).json({ error: `Webhook signature invalid: ${err.message}` });
  }

  // ── EVENT DISPATCH ───────────────────────────────────────────

  try {
    if (event.type === 'checkout.session.completed') {
      const session = event.data.object;

      const stripeCustomerId = session.customer;
      const subscriptionId   = session.subscription;
      const email            = session.customer_details?.email || session.customer_email;
      const shopName         = session.metadata?.shopName  || session.metadata?.shop_name || null;
      const planName         = session.metadata?.planName  || session.metadata?.plan_name || null;
      const appName          = session.metadata?.appName   || session.metadata?.app_name  || null;

      // Only process subscription checkouts (not one-time payments)
      if (session.mode !== 'subscription') {
        return res.status(200).json({ received: true, skipped: 'non-subscription checkout' });
      }

      const org = await activateOrg({ stripeCustomerId, subscriptionId, email, shopName, planName });

      await sendWelcomeEmail({
        to:       email,
        shopName: shopName || org?.name,
        planName,
        appName,
      });

      console.log('[stripe webhook] checkout.session.completed -- org activated:', org?.id);
      return res.status(200).json({ received: true, org_id: org?.id });
    }

    if (event.type === 'customer.subscription.deleted') {
      const subscription = event.data.object;

      await deactivateOrg({
        stripeCustomerId: subscription.customer,
        subscriptionId:   subscription.id,
      });

      console.log('[stripe webhook] subscription.deleted -- org deactivated:', subscription.customer);
      return res.status(200).json({ received: true });
    }

    // All other events acknowledged but not acted on
    return res.status(200).json({ received: true, event: event.type });

  } catch (err) {
    console.error('[stripe webhook] handler error:', err.message);
    // Return 200 so Stripe does not retry -- log the error for manual review
    return res.status(200).json({ received: true, error: err.message });
  }
}
