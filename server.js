// ================================================================
//  SAIRN Technologies — StoneDesk Railway Server
//  Express backend for fabricor-production.up.railway.app
//  Handles: Stripe webhook, health check
//  Michael L. Dibert · SAIRN Technologies · 2026
// ================================================================

import express from 'express';
import Stripe from 'stripe';
import { createClient } from '@supabase/supabase-js';

const app  = express();
const port = process.env.PORT || 3000;

const stripe   = new Stripe(process.env.STRIPE_SECRET_KEY);
const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
);

const PRICE_MAP = {
  'price_1TgEAbA6PfEDlvnaQBSzvNW5': 'stonedesk_starter',
  'price_1TgEBVA6PfEDlvnaN4ZbVE8r': 'stonedesk_pro',
  'price_1TgECGA6PfEDlvnaDzp5cyhG': 'stonedesk_enterprise',
};

// Health check
app.get('/', (req, res) => res.json({ status: 'ok', app: 'StoneDesk', version: '1.0' }));
app.get('/health', (req, res) => res.json({ status: 'ok' }));

// Stripe webhook -- raw body required for signature verification
app.post('/api/billing/webhook', express.raw({ type: 'application/json' }), async (req, res) => {
  const sig    = req.headers['stripe-signature'];
  const secret = process.env.STRIPE_WEBHOOK_SECRET;

  let event;
  try {
    event = stripe.webhooks.constructEvent(req.body, sig, secret);
  } catch (err) {
    console.error('[Webhook] Signature failed:', err.message);
    return res.status(400).json({ error: 'Signature verification failed' });
  }

  console.log('[Webhook] Event received:', event.type, event.id);

  // Idempotency check
  const { data: existing } = await supabase
    .from('webhook_events')
    .select('id')
    .eq('stripe_event_id', event.id)
    .maybeSingle();

  if (existing) {
    console.log('[Webhook] Duplicate event, skipping:', event.id);
    return res.status(200).json({ received: true, skipped: 'duplicate' });
  }

  // Log event
  await supabase.from('webhook_events').insert({
    stripe_event_id: event.id,
    event_type: event.type,
    status: 'processing',
    payload: JSON.stringify(event.data.object).slice(0, 10000)
  }).catch(() => {});

  try {
    await handleEvent(event);
    await supabase.from('webhook_events')
      .update({ status: 'completed', processed_at: new Date().toISOString() })
      .eq('stripe_event_id', event.id);

    return res.status(200).json({ received: true });

  } catch (err) {
    console.error('[Webhook] Handler error:', err.message);
    await supabase.from('webhook_events')
      .update({ status: 'failed', error_message: err.message, processed_at: new Date().toISOString() })
      .eq('stripe_event_id', event.id);

    return res.status(200).json({ received: true, error: err.message });
  }
});

async function handleEvent(event) {
  switch (event.type) {

    case 'checkout.session.completed': {
      const session = event.data.object;
      if (session.mode !== 'subscription') break;
      const sub     = await stripe.subscriptions.retrieve(session.subscription);
      const priceId = sub.items.data[0]?.price?.id;
      const plan    = PRICE_MAP[priceId];
      const email   = session.customer_details?.email;
      if (!plan || !email) break;
      const userId = await getUserId(email);
      if (!userId) break;
      await upsertSubscription(userId, plan, session.customer, session.subscription, priceId, sub);
      console.log('[Webhook] New subscription activated:', email, plan);
      break;
    }

    case 'customer.subscription.deleted': {
      await supabase.from('subscriptions')
        .update({ status: 'canceled', updated_at: new Date().toISOString() })
        .eq('stripe_subscription_id', event.data.object.id);
      console.log('[Webhook] Subscription canceled:', event.data.object.id);
      break;
    }

    case 'customer.subscription.updated': {
      const sub     = event.data.object;
      const priceId = sub.items.data[0]?.price?.id;
      const plan    = PRICE_MAP[priceId];
      if (!plan) break;
      await supabase.from('subscriptions')
        .update({ status: sub.status, updated_at: new Date().toISOString() })
        .eq('stripe_subscription_id', sub.id);
      break;
    }

    case 'invoice.payment_failed': {
      const invoice = event.data.object;
      if (invoice.subscription) {
        await supabase.from('subscriptions')
          .update({ status: 'past_due', updated_at: new Date().toISOString() })
          .eq('stripe_subscription_id', invoice.subscription);
        console.log('[Webhook] Payment failed, marked past_due:', invoice.subscription);
      }
      break;
    }
  }
}

async function getUserId(email) {
  if (!email) return null;
  const { data } = await supabase
    .from('profiles')
    .select('id')
    .eq('email', email.toLowerCase())
    .maybeSingle();
  return data?.id || null;
}

async function upsertSubscription(userId, plan, customerId, subId, priceId, sub) {
  await supabase.from('subscriptions').upsert({
    user_id:                  userId,
    app_id:                   plan,
    stripe_customer_id:       customerId,
    stripe_subscription_id:   subId,
    stripe_price_id:          priceId,
    status:                   sub.status,
    current_period_start:     new Date(sub.current_period_start * 1000).toISOString(),
    current_period_end:       new Date(sub.current_period_end   * 1000).toISOString(),
    cancel_at_period_end:     sub.cancel_at_period_end,
    updated_at:               new Date().toISOString()
  }, { onConflict: 'user_id,app_id' });
}

app.listen(port, () => {
  console.log('StoneDesk server running on port', port);
});
