// ═══════════════════════════════════════════════════════════════════
//  SAIRN Technologies — /api/webhooks/stripe  (v2 — Hardened)
//  ✓ Retry queue for failed events  ✓ Idempotency checks
//  ✓ Free trial activation  ✓ Referral crediting
//  Michael L. Dibert · SAIRN Technologies · 2026
// ═══════════════════════════════════════════════════════════════════

import Stripe from 'stripe';
import { createClient } from '@supabase/supabase-js';

const stripe   = new Stripe(process.env.STRIPE_SECRET_KEY);
const supabase = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_ROLE_KEY);

const PRICE_MAP = {
  'price_1TXX2xPAZMGVs7fEFeEZXUMu': 'sairntype',
  'price_1TYkzNPAZMGVs7fEBwtr2DNO': 'lingual',
  'price_1TYlEuPAZMGVs7fE08F60j7B': 'health',
  'price_1TYlEzPAZMGVs7fEWGHKcfot': 'money',
  'price_1TYlF4PAZMGVs7fEZVPqfl1L': 'legal',
  'price_1TYlFAPAZMGVs7fEWwLutuMV': 'study',
  'price_1TYkz7PAZMGVs7fEFSoi6api': 'roam',
  'price_1TYlFFPAZMGVs7fE7zeWHKzE': 'senior',
};

export const config = { api: { bodyParser: false } };

export default async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).end();

  const raw = await new Promise((resolve, reject) => {
    const chunks = [];
    req.on('data', c => chunks.push(c));
    req.on('end',  () => resolve(Buffer.concat(chunks)));
    req.on('error', reject);
  });

  let event;
  try {
    event = stripe.webhooks.constructEvent(raw, req.headers['stripe-signature'], process.env.STRIPE_WEBHOOK_SECRET);
  } catch (err) {
    console.error('[Stripe Webhook] Signature failed:', err.message);
    return res.status(400).json({ error: `Webhook signature failed: ${err.message}` });
  }

  // Idempotency: skip already-processed events
  const { data: processed } = await supabase
    .from('webhook_events').select('id').eq('stripe_event_id', event.id).maybeSingle();
  if (processed) return res.status(200).json({ received: true, skipped: 'duplicate' });

  // Log event immediately
  await supabase.from('webhook_events').insert({
    stripe_event_id: event.id, event_type: event.type, status: 'processing',
    payload: JSON.stringify(event.data.object).slice(0, 10000)
  }).catch(() => {});

  try {
    await handleEvent(event);

    // Mark success
    await supabase.from('webhook_events').update({ status: 'completed', processed_at: new Date().toISOString() })
      .eq('stripe_event_id', event.id);

    return res.status(200).json({ received: true });

  } catch (err) {
    console.error('[Stripe Webhook] Handler error:', err.message);

    // Mark failed — allows retry visibility
    await supabase.from('webhook_events').update({
      status: 'failed', error_message: err.message, processed_at: new Date().toISOString()
    }).eq('stripe_event_id', event.id);

    // Return 200 to prevent Stripe from retrying events we've logged
    // (we handle retries ourselves via the failed events table)
    return res.status(200).json({ received: true, error: err.message });
  }
}

async function handleEvent(event) {
  switch (event.type) {

    case 'checkout.session.completed': {
      const session = event.data.object;
      if (session.mode !== 'subscription') break;
      const stripeSub = await stripe.subscriptions.retrieve(session.subscription);
      const priceId   = stripeSub.items.data[0]?.price?.id;
      const appId     = PRICE_MAP[priceId];
      if (!appId) { console.warn('[Stripe] Unknown price ID:', priceId); break; }
      const email  = session.customer_details?.email;
      const userId = await getUserId(email);
      if (!userId) { console.warn('[Stripe] No user for email:', email); break; }
      await upsertSub(userId, appId, session.customer, session.subscription, priceId, stripeSub);

      // Activate pending referral
      await activateReferral(userId, appId);

      // Send welcome email trigger (fire-and-forget)
      triggerWelcome(userId, appId, email).catch(() => {});
      break;
    }

    case 'customer.subscription.trial_will_end': {
      // 3 days before trial ends — send reminder
      const sub = event.data.object;
      const { data: record } = await supabase.from('subscriptions')
        .select('user_id, app_id').eq('stripe_subscription_id', sub.id).maybeSingle();
      if (record) {
        await supabase.from('notification_queue').insert({
          user_id: record.user_id, app_id: record.app_id,
          type: 'trial_ending', scheduled_for: new Date().toISOString()
        }).catch(() => {});
      }
      break;
    }

    case 'customer.subscription.updated':
    case 'invoice.payment_succeeded': {
      const subId = event.data.object.subscription || event.data.object.id;
      if (!subId) break;
      const stripeSub = await stripe.subscriptions.retrieve(subId);
      const priceId   = stripeSub.items.data[0]?.price?.id;
      const appId     = PRICE_MAP[priceId];
      if (!appId) break;
      const { data: rec } = await supabase.from('subscriptions')
        .select('user_id').eq('stripe_subscription_id', subId).maybeSingle();
      if (rec?.user_id) await upsertSub(rec.user_id, appId, stripeSub.customer, subId, priceId, stripeSub);
      break;
    }

    case 'customer.subscription.deleted': {
      await supabase.from('subscriptions')
        .update({ status: 'canceled', updated_at: new Date().toISOString() })
        .eq('stripe_subscription_id', event.data.object.id);
      break;
    }

    case 'invoice.payment_failed': {
      const invoice = event.data.object;
      if (invoice.subscription) {
        await supabase.from('subscriptions')
          .update({ status: 'past_due', updated_at: new Date().toISOString() })
          .eq('stripe_subscription_id', invoice.subscription);
      }
      break;
    }
  }
}

async function getUserId(email) {
  if (!email) return null;
  const { data } = await supabase.from('profiles').select('id').eq('email', email.toLowerCase()).maybeSingle();
  return data?.id || null;
}

async function upsertSub(userId, appId, customerId, subId, priceId, stripeSub) {
  await supabase.from('subscriptions').upsert({
    user_id: userId, app_id: appId,
    stripe_customer_id: customerId, stripe_subscription_id: subId, stripe_price_id: priceId,
    status: stripeSub.status,
    trial_end: stripeSub.trial_end ? new Date(stripeSub.trial_end * 1000).toISOString() : null,
    current_period_start: new Date(stripeSub.current_period_start * 1000).toISOString(),
    current_period_end:   new Date(stripeSub.current_period_end   * 1000).toISOString(),
    cancel_at_period_end: stripeSub.cancel_at_period_end,
    updated_at: new Date().toISOString()
  }, { onConflict: 'user_id,app_id' });
}

async function activateReferral(userId, appId) {
  const { data: referral } = await supabase.from('referrals')
    .select('id, referrer_id').eq('referred_user_id', userId).eq('status', 'pending').maybeSingle();
  if (!referral) return;
  await supabase.from('referrals').update({ status: 'credited', credited_at: new Date().toISOString() }).eq('id', referral.id);
  await supabase.rpc('credit_referral', { p_user_id: referral.referrer_id, p_app_id: appId }).catch(() => {});
}

async function triggerWelcome(userId, appId, email) {
  await supabase.from('notification_queue').insert({
    user_id: userId, app_id: appId, email,
    type: 'welcome', scheduled_for: new Date().toISOString()
  });
}
