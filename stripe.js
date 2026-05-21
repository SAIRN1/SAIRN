// ═══════════════════════════════════════════════════════════════════
//  SAIRN Technologies — /api/webhooks/stripe
//  Syncs every Stripe event → Supabase subscriptions table
//  Michael L. Dibert · HONEY COMB Platform · 2026
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
    return res.status(400).json({ error: `Signature failed: ${err.message}` });
  }

  try {
    switch (event.type) {

      case 'checkout.session.completed': {
        const session = event.data.object;
        if (session.mode !== 'subscription') break;
        const stripeSub = await stripe.subscriptions.retrieve(session.subscription);
        const priceId   = stripeSub.items.data[0]?.price?.id;
        const appId     = PRICE_MAP[priceId];
        if (!appId) break;
        const email  = session.customer_details?.email;
        const userId = await getUserIdByEmail(email);
        if (!userId) break;
        await upsertSub(userId, appId, session.customer, session.subscription, priceId, stripeSub);
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
        const { data: existing } = await supabase.from('subscriptions').select('user_id').eq('stripe_subscription_id', subId).maybeSingle();
        if (existing?.user_id) await upsertSub(existing.user_id, appId, stripeSub.customer, subId, priceId, stripeSub);
        break;
      }

      case 'customer.subscription.deleted': {
        await supabase.from('subscriptions').update({ status: 'canceled', updated_at: new Date().toISOString() }).eq('stripe_subscription_id', event.data.object.id);
        break;
      }

      case 'invoice.payment_failed': {
        if (event.data.object.subscription) {
          await supabase.from('subscriptions').update({ status: 'past_due', updated_at: new Date().toISOString() }).eq('stripe_subscription_id', event.data.object.subscription);
        }
        break;
      }
    }
    return res.status(200).json({ received: true });
  } catch (err) {
    console.error('[Stripe Webhook]', err.message);
    return res.status(500).json({ error: 'Webhook error' });
  }
}

async function getUserIdByEmail(email) {
  if (!email) return null;
  const { data } = await supabase.from('profiles').select('id').eq('email', email.toLowerCase()).maybeSingle();
  return data?.id || null;
}

async function upsertSub(userId, appId, customerId, subId, priceId, stripeSub) {
  await supabase.from('subscriptions').upsert({
    user_id: userId, app_id: appId,
    stripe_customer_id: customerId,
    stripe_subscription_id: subId,
    stripe_price_id: priceId,
    status: stripeSub.status,
    current_period_start: new Date(stripeSub.current_period_start * 1000).toISOString(),
    current_period_end:   new Date(stripeSub.current_period_end   * 1000).toISOString(),
    cancel_at_period_end: stripeSub.cancel_at_period_end,
    updated_at: new Date().toISOString()
  }, { onConflict: 'user_id,app_id' });
}
