// ================================================================
// SAIRN Stripe Webhook Handler -- api/webhooks/stripe.js
// Verifies stripe-signature, generates + stores license keys,
// activates/deactivates orgs in Supabase, sends welcome email.
//
// Events handled:
//   checkout.session.completed     -> generate key, activate org, email
//   customer.subscription.deleted  -> cancel key, deactivate org
//
// Env vars required:
//   STRIPE_SECRET_KEY
//   STRIPE_WEBHOOK_SECRET
//   SUPABASE_URL
//   SUPABASE_SERVICE_ROLE_KEY
//   RESEND_API_KEY
//   RESEND_FROM_EMAIL
//
// Stripe webhook URL:
//   https://sairn.vercel.app/api/webhooks/stripe
// ================================================================

import Stripe from 'stripe';
import { createClient } from '@supabase/supabase-js';
import { randomBytes }  from 'crypto';

// Vercel: disable body parser so raw bytes reach constructEvent()
export const config = { api: { bodyParser: false } };

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY);

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
);

// ----------------------------------------------------------------
// License key generation
// Format: {APP_PREFIX}_{YEAR}_{10 random hex chars, uppercase}
// Example: SD_2026_A3F9C2B1E4
// Matches the SAIRN_KEYS env var format (underscores, no hyphens).
// ----------------------------------------------------------------
const APP_PREFIXES = {
  stonedesk:       'SD',
  sairnbiz:        'SBZ',
  sairnbuild:      'SBD',
  sairnlaw:        'SLW',
  sairnscape:      'SSC',
  sairndesign:     'SDG',
  sairncode:       'SCO',
  sairncare:       'SCR',
  sairnvet:        'SVT',
  sairnfuneral:    'SFN',
  sairnmechanical: 'SMC',
};

function generateLicenseKey(appId) {
  const prefix = APP_PREFIXES[appId] || 'SRN';
  const year   = new Date().getFullYear();
  const rand   = randomBytes(5).toString('hex').toUpperCase(); // 10 chars
  return `${prefix}_${year}_${rand}`;
}

// ----------------------------------------------------------------
// Store license key in Supabase.
// On conflict (same stripe_customer_id + app_id) update in place
// so re-subscriptions don't create orphaned rows.
// ----------------------------------------------------------------
async function storeLicenseKey({ key, appId, shopName, email, stripeCustomerId, subscriptionId, plan }) {
  const { data, error } = await supabase
    .from('license_keys')
    .upsert(
      {
        key,
        app_id:                 appId,
        shop_name:              shopName  || null,
        customer_email:         email     || null,
        stripe_customer_id:     stripeCustomerId,
        stripe_subscription_id: subscriptionId,
        plan:                   plan      || 'b2b_starter',
        status:                 'active',
      },
      { onConflict: 'key' }
    )
    .select()
    .single();

  if (error) console.error('[stripe webhook] storeLicenseKey error:', error.message);
  return data;
}

// ----------------------------------------------------------------
// Cancel the license key tied to a Stripe customer/subscription.
// ----------------------------------------------------------------
async function cancelLicenseKey({ stripeCustomerId, subscriptionId }) {
  let query = supabase
    .from('license_keys')
    .update({ status: 'cancelled' });

  if (stripeCustomerId) {
    query = query.eq('stripe_customer_id', stripeCustomerId);
  } else if (subscriptionId) {
    query = query.eq('stripe_subscription_id', subscriptionId);
  } else {
    return;
  }

  const { error } = await query;
  if (error) console.error('[stripe webhook] cancelLicenseKey error:', error.message);
}

// ----------------------------------------------------------------
// Activate org in Supabase (organizations table).
// ----------------------------------------------------------------
async function activateOrg({ stripeCustomerId, subscriptionId, email, shopName, planName }) {
  let { data: org } = await supabase
    .from('organizations')
    .select('id, name, contact_email')
    .eq('stripe_customer', stripeCustomerId)
    .maybeSingle();

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
// Deactivate org in Supabase.
// ----------------------------------------------------------------
async function deactivateOrg({ stripeCustomerId, subscriptionId }) {
  let query = supabase
    .from('organizations')
    .update({ status: 'cancelled', stripe_subscription: null, updated_at: new Date().toISOString() });

  if (stripeCustomerId)  query = query.eq('stripe_customer', stripeCustomerId);
  else if (subscriptionId) query = query.eq('stripe_subscription', subscriptionId);
  else return;

  await query;
}

// ----------------------------------------------------------------
// Send welcome email with the license key via Resend.
// ----------------------------------------------------------------
async function sendWelcomeEmail({ to, shopName, planName, appName, appId, licenseKey }) {
  const resendKey = process.env.RESEND_API_KEY;
  const from      = process.env.RESEND_FROM_EMAIL || 'onboarding@resend.dev';
  if (!resendKey || !to) return;

  const displayApp  = appName || appId || 'SAIRN';
  const displayPlan = planName || 'B2B';
  const displayShop = shopName || to;

  const html = `
    <div style="font-family:system-ui,sans-serif;max-width:580px;margin:0 auto;background:#ffffff;padding:40px 32px;border-radius:12px;border:1px solid #e2e8f0;">
      <div style="font-size:26px;font-weight:900;color:#0f172a;margin-bottom:4px;">Welcome to SAIRN</div>
      <div style="font-size:14px;color:#64748b;margin-bottom:28px;">Your subscription is active. Here is everything you need to get started.</div>

      <table style="width:100%;border-collapse:collapse;margin-bottom:28px;">
        <tr>
          <td style="padding:10px 0;border-bottom:1px solid #e2e8f0;color:#64748b;font-size:13px;width:140px;">Business</td>
          <td style="padding:10px 0;border-bottom:1px solid #e2e8f0;font-weight:600;font-size:13px;">${displayShop}</td>
        </tr>
        <tr>
          <td style="padding:10px 0;border-bottom:1px solid #e2e8f0;color:#64748b;font-size:13px;">App</td>
          <td style="padding:10px 0;border-bottom:1px solid #e2e8f0;font-weight:600;font-size:13px;">${displayApp} + SAIRNbiz (included)</td>
        </tr>
        <tr>
          <td style="padding:10px 0;color:#64748b;font-size:13px;">Plan</td>
          <td style="padding:10px 0;font-weight:600;font-size:13px;">${displayPlan}</td>
        </tr>
      </table>

      <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;padding:20px 24px;margin-bottom:28px;">
        <div style="font-size:11px;font-weight:700;color:#15803d;letter-spacing:0.8px;text-transform:uppercase;margin-bottom:8px;">Your License Key</div>
        <div style="font-family:monospace;font-size:20px;font-weight:700;color:#0f172a;letter-spacing:2px;">${licenseKey}</div>
        <div style="font-size:12px;color:#64748b;margin-top:8px;">Enter this key in the app to unlock unlimited AI access.</div>
      </div>

      <div style="background:#f8fafc;border-radius:8px;padding:16px 20px;margin-bottom:28px;">
        <div style="font-size:12px;font-weight:700;color:#475569;margin-bottom:8px;">How to activate</div>
        <ol style="font-size:13px;color:#475569;margin:0;padding-left:18px;line-height:1.8;">
          <li>Open your app at <a href="https://sairn.vercel.app" style="color:#0f172a;">sairn.vercel.app</a></li>
          <li>Click the AI button or Formula Editor</li>
          <li>Paste your license key when prompted</li>
        </ol>
      </div>

      <a href="https://sairn.vercel.app" style="display:inline-block;background:#0f172a;color:#ffffff;text-decoration:none;padding:12px 28px;border-radius:8px;font-weight:600;font-size:14px;">Open your app</a>

      <div style="margin-top:32px;padding-top:20px;border-top:1px solid #e2e8f0;font-size:12px;color:#94a3b8;">
        Keep this email -- your license key is not stored anywhere else accessible to you.<br>
        Questions? Email <a href="mailto:michael@sairn.com" style="color:#64748b;">michael@sairn.com</a>
      </div>
    </div>
  `;

  const text = [
    `Welcome to SAIRN!`,
    ``,
    `Business: ${displayShop}`,
    `App: ${displayApp} + SAIRNbiz (included)`,
    `Plan: ${displayPlan}`,
    ``,
    `Your License Key: ${licenseKey}`,
    ``,
    `Enter this key in the app's AI button or Formula Editor to unlock unlimited access.`,
    ``,
    `Open your app: https://sairn.vercel.app`,
    ``,
    `Questions? Email michael@sairn.com`,
  ].join('\n');

  const result = await fetch('https://api.resend.com/emails', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${resendKey}`,
      'Content-Type':  'application/json',
    },
    body: JSON.stringify({
      from:    `SAIRN <${from}>`,
      to:      [to],
      subject: `Your SAIRN license key for ${displayApp}`,
      html,
      text,
    }),
  });

  if (!result.ok) {
    const err = await result.json().catch(() => ({}));
    console.error('[stripe webhook] Resend error:', err);
  }
}

// ----------------------------------------------------------------
// Raw body reader (required for Stripe signature verification)
// ----------------------------------------------------------------
function getRawBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    req.on('data', chunk => chunks.push(chunk));
    req.on('end',  ()    => resolve(Buffer.concat(chunks)));
    req.on('error', reject);
  });
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

  let rawBody;
  try {
    rawBody = await getRawBody(req);
  } catch {
    return res.status(400).json({ error: 'Could not read request body' });
  }

  let event;
  try {
    event = stripe.webhooks.constructEvent(rawBody, sig, secret);
  } catch (err) {
    console.error('[stripe webhook] signature verification failed:', err.message);
    return res.status(400).json({ error: `Webhook signature invalid: ${err.message}` });
  }

  try {
    // ---- checkout.session.completed --------------------------------
    if (event.type === 'checkout.session.completed') {
      const session = event.data.object;

      if (session.mode !== 'subscription') {
        return res.status(200).json({ received: true, skipped: 'non-subscription checkout' });
      }

      const stripeCustomerId = session.customer;
      const subscriptionId   = session.subscription;
      const email            = session.customer_details?.email || session.customer_email;
      const shopName         = session.metadata?.shopName  || session.metadata?.shop_name  || null;
      const planName         = session.metadata?.planName  || session.metadata?.plan_name  || null;
      const appId            = session.metadata?.appId     || session.metadata?.app_id     || 'sairn';
      const appName          = session.metadata?.appName   || session.metadata?.app_name   || null;

      // Generate and persist the license key
      const licenseKey = generateLicenseKey(appId);

      const [keyRow, org] = await Promise.all([
        storeLicenseKey({
          key:             licenseKey,
          appId,
          shopName,
          email,
          stripeCustomerId,
          subscriptionId,
          plan:            planName,
        }),
        activateOrg({ stripeCustomerId, subscriptionId, email, shopName, planName }),
      ]);

      await sendWelcomeEmail({
        to:         email,
        shopName:   shopName || org?.name,
        planName,
        appName,
        appId,
        licenseKey,
      });

      console.log('[stripe webhook] checkout.session.completed -- key:', licenseKey, 'org:', org?.id);
      return res.status(200).json({ received: true, license_key: licenseKey, org_id: org?.id });
    }

    // ---- customer.subscription.deleted -----------------------------
    if (event.type === 'customer.subscription.deleted') {
      const sub = event.data.object;

      await Promise.all([
        cancelLicenseKey({ stripeCustomerId: sub.customer, subscriptionId: sub.id }),
        deactivateOrg({ stripeCustomerId: sub.customer, subscriptionId: sub.id }),
      ]);

      console.log('[stripe webhook] subscription.deleted -- customer:', sub.customer);
      return res.status(200).json({ received: true });
    }

    return res.status(200).json({ received: true, event: event.type });

  } catch (err) {
    console.error('[stripe webhook] handler error:', err.message);
    // 200 so Stripe does not retry -- error is logged for manual review
    return res.status(200).json({ received: true, error: err.message });
  }
}
