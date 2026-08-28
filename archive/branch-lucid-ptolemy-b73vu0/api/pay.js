// ================================================================
// SAIRN Payment API — api/pay.js
// Card on file + Pay Now for all B2B apps
// Handles: setup intents, charge on file, payment links, webhooks
// Michael L. Dibert · SAIRN Technologies · 2026
// ================================================================

import Stripe from 'stripe';
import { createClient } from '@supabase/supabase-js';

const stripe   = new Stripe(process.env.STRIPE_SECRET_KEY);
const supabase = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_ROLE_KEY);

function setCors(res, req) {
  const origin = req.headers.origin || '';
  res.setHeader('Access-Control-Allow-Origin', origin || '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Shop-Id');
}

export default async function handler(req, res) {
  setCors(res, req);
  if (req.method === 'OPTIONS') return res.status(200).end();

  const { action } = req.query;

  try {

    // ── SETUP CARD ON FILE ──────────────────────────────────────
    // Called when adding a card for a customer
    // Returns a Stripe SetupIntent client_secret for the frontend

    if (action === 'setup_card') {
      const { customer_id, shop_id, customer_name, customer_email } = req.body;
      if (!customer_id || !shop_id) return res.status(400).json({ error: 'customer_id and shop_id required' });

      // Get or create Stripe customer
      const { data: customer } = await supabase
        .from('customers').select('stripe_customer_id, email').eq('id', customer_id).single();

      let stripeCustomerId = customer?.stripe_customer_id;
      if (!stripeCustomerId) {
        const sc = await stripe.customers.create({
          email: customer_email || customer?.email,
          name: customer_name,
          metadata: { sairn_customer_id: customer_id, shop_id }
        });
        stripeCustomerId = sc.id;
        await supabase.from('customers').update({ stripe_customer_id: stripeCustomerId }).eq('id', customer_id);
      }

      const setupIntent = await stripe.setupIntents.create({
        customer: stripeCustomerId,
        payment_method_types: ['card'],
        usage: 'off_session',
        metadata: { customer_id, shop_id }
      });

      return res.status(200).json({
        ok: true,
        client_secret: setupIntent.client_secret,
        stripe_customer_id: stripeCustomerId
      });
    }

    // ── SAVE CARD AFTER SETUP ───────────────────────────────────
    // After frontend confirms setup, save the payment method

    if (action === 'save_card') {
      const { customer_id, setup_intent_id } = req.body;
      if (!customer_id || !setup_intent_id) return res.status(400).json({ error: 'customer_id and setup_intent_id required' });

      const setupIntent = await stripe.setupIntents.retrieve(setup_intent_id);
      if (setupIntent.status !== 'succeeded') {
        return res.status(400).json({ error: 'Setup intent not succeeded' });
      }

      const pm = await stripe.paymentMethods.retrieve(setupIntent.payment_method);
      await supabase.from('customers').update({
        stripe_payment_method: setupIntent.payment_method,
        stripe_customer_id: setupIntent.customer
      }).eq('id', customer_id);

      return res.status(200).json({
        ok: true,
        card: {
          brand: pm.card.brand,
          last4: pm.card.last4,
          exp_month: pm.card.exp_month,
          exp_year: pm.card.exp_year
        }
      });
    }

    // ── CHARGE CARD ON FILE ─────────────────────────────────────
    // Charge the saved card for an invoice — one-click collection

    if (action === 'charge') {
      const { invoice_id, shop_id, amount_cents, description } = req.body;
      if (!invoice_id || !shop_id || !amount_cents) {
        return res.status(400).json({ error: 'invoice_id, shop_id, amount_cents required' });
      }

      // Get invoice + customer
      const { data: invoice } = await supabase.from('invoices')
        .select('*, customers(stripe_customer_id, stripe_payment_method, first_name, last_name, email)')
        .eq('id', invoice_id).eq('shop_id', shop_id).single();

      if (!invoice) return res.status(404).json({ error: 'Invoice not found' });

      const cust = invoice.customers;
      if (!cust?.stripe_customer_id || !cust?.stripe_payment_method) {
        return res.status(400).json({ error: 'No card on file for this customer', no_card: true });
      }

      // Create and confirm PaymentIntent
      const pi = await stripe.paymentIntents.create({
        amount: amount_cents,
        currency: 'usd',
        customer: cust.stripe_customer_id,
        payment_method: cust.stripe_payment_method,
        confirm: true,
        off_session: true,
        description: description || `Invoice ${invoice.invoice_number}`,
        metadata: { invoice_id, shop_id, invoice_number: invoice.invoice_number }
      });

      if (pi.status === 'succeeded') {
        // Update invoice + log payment
        await supabase.from('invoices').update({
          status: 'paid',
          amount_paid: invoice.total,
          paid_at: new Date().toISOString(),
          stripe_payment_intent_id: pi.id
        }).eq('id', invoice_id);

        await supabase.from('payments').insert({
          shop_id, invoice_id,
          customer_id: invoice.customer_id,
          amount: amount_cents / 100,
          method: 'card',
          stripe_payment_intent_id: pi.id,
          stripe_charge_id: pi.latest_charge,
          status: 'succeeded'
        });

        // Auto-post to GL
        await supabase.from('gl_entries').insert({
          shop_id, date: new Date().toISOString().slice(0,10),
          account_code: '1000', description: `Payment received - ${invoice.invoice_number}`,
          debit: amount_cents / 100, source_app: 'payment', source_id: invoice_id
        }).catch(() => {});

        return res.status(200).json({
          ok: true,
          status: 'paid',
          amount: amount_cents / 100,
          charge_id: pi.latest_charge
        });

      } else if (pi.status === 'requires_action') {
        return res.status(200).json({
          ok: false,
          status: 'requires_action',
          client_secret: pi.client_secret,
          message: 'Card requires authentication. Send payment link to customer.'
        });
      } else {
        return res.status(400).json({ error: `Payment status: ${pi.status}` });
      }
    }

    // ── PAYMENT LINK (customer self-pay) ────────────────────────
    // Generate a Stripe-hosted payment link to send to customer

    if (action === 'payment_link') {
      const { invoice_id, shop_id, success_url, cancel_url } = req.body;
      if (!invoice_id || !shop_id) return res.status(400).json({ error: 'invoice_id and shop_id required' });

      const { data: invoice } = await supabase.from('invoices')
        .select('*, customers(email, first_name, last_name, stripe_customer_id)')
        .eq('id', invoice_id).eq('shop_id', shop_id).single();

      if (!invoice) return res.status(404).json({ error: 'Invoice not found' });

      // Get shop info for success URL
      const { data: shop } = await supabase.from('shops').select('app_id, shop_name').eq('id', shop_id).single();
      const baseUrl = 'https://sairn.vercel.app';
      const appPage = `${baseUrl}/${shop?.app_id || 'sairntrade'}.html`;

      // Create price for this invoice amount
      const price = await stripe.prices.create({
        currency: 'usd',
        unit_amount: Math.round(invoice.total * 100),
        product_data: {
          name: `Invoice ${invoice.invoice_number} - ${shop?.shop_name || 'SAIRN'}`,
          metadata: { invoice_id, shop_id }
        }
      });

      // Create payment link
      const link = await stripe.paymentLinks.create({
        line_items: [{ price: price.id, quantity: 1 }],
        after_completion: {
          type: 'redirect',
          redirect: { url: success_url || `${appPage}?paid=${invoice_id}` }
        },
        metadata: { invoice_id, shop_id },
        customer_creation: 'if_required',
        ...(invoice.customers?.stripe_customer_id ? {
          // Pre-fill customer email
        } : {})
      });

      // Update invoice with payment link
      await supabase.from('invoices').update({
        status: 'sent',
        sent_at: new Date().toISOString()
      }).eq('id', invoice_id);

      return res.status(200).json({
        ok: true,
        payment_url: link.url,
        invoice_number: invoice.invoice_number,
        amount: invoice.total
      });
    }

    // ── CHECK CARD ON FILE ───────────────────────────────────────

    if (action === 'get_card') {
      const { customer_id } = req.query;
      if (!customer_id) return res.status(400).json({ error: 'customer_id required' });

      const { data: customer } = await supabase.from('customers')
        .select('stripe_customer_id, stripe_payment_method').eq('id', customer_id).single();

      if (!customer?.stripe_payment_method) {
        return res.status(200).json({ ok: true, has_card: false });
      }

      const pm = await stripe.paymentMethods.retrieve(customer.stripe_payment_method);
      return res.status(200).json({
        ok: true,
        has_card: true,
        card: {
          brand: pm.card.brand,
          last4: pm.card.last4,
          exp_month: pm.card.exp_month,
          exp_year: pm.card.exp_year
        }
      });
    }

    // ── B2B SUBSCRIPTION CHECKOUT ────────────────────────────────
    // For shops signing up for StoneDesk, SAIRNbuild, SAIRNtrade etc.

    if (action === 'b2b_checkout') {
      const { app_id, plan, shop_name, email, success_url, cancel_url } = req.body;
      if (!app_id || !plan || !email) return res.status(400).json({ error: 'app_id, plan, email required' });

      // B2B price map
      const PRICES = {
        stonedesk:   { starter: 'price_stonedesk_starter', pro: 'price_stonedesk_pro', enterprise: 'price_stonedesk_ent' },
        sairntrade:  { starter: 'price_sairntrade_starter', pro: 'price_sairntrade_pro', enterprise: 'price_sairntrade_ent' },
        sairnbuild:  { starter: 'price_sairnbuild_starter', pro: 'price_sairnbuild_pro', enterprise: 'price_sairnbuild_ent' },
        sairnscape:  { starter: 'price_sairnscape_starter', pro: 'price_sairnscape_pro', enterprise: 'price_sairnscape_ent' },
        sairnhr:     { starter: 'price_sairnhr_starter' },
        sairnacc:    { starter: 'price_sairnacc_starter' },
      };

      // For now use the existing StoneDesk prices or fall through to a generic one
      const priceId = PRICES[app_id]?.[plan] || process.env[`STRIPE_PRICE_${app_id.toUpperCase()}_${plan.toUpperCase()}`];

      if (!priceId) {
        // Create ad-hoc price for demo
        const PLAN_AMOUNTS = {
          starter: 14900, pro: 29900, enterprise: 49900
        };
        const price = await stripe.prices.create({
          currency: 'usd',
          unit_amount: PLAN_AMOUNTS[plan] || 14900,
          recurring: { interval: 'month' },
          product_data: {
            name: `${app_id} ${plan.charAt(0).toUpperCase()+plan.slice(1)}`,
          }
        });

        const session = await stripe.checkout.sessions.create({
          mode: 'subscription',
          payment_method_types: ['card'],
          line_items: [{ price: price.id, quantity: 1 }],
          customer_email: email,
          subscription_data: { trial_period_days: 14, metadata: { app_id, plan, shop_name } },
          success_url: success_url || `https://sairn.vercel.app/${app_id}.html?subscribed=true`,
          cancel_url: cancel_url || `https://sairn.vercel.app/${app_id}.html`,
          metadata: { app_id, plan, shop_name, email },
          allow_promotion_codes: true
        });
        return res.status(200).json({ ok: true, url: session.url });
      }

      const session = await stripe.checkout.sessions.create({
        mode: 'subscription',
        payment_method_types: ['card'],
        line_items: [{ price: priceId, quantity: 1 }],
        customer_email: email,
        subscription_data: { trial_period_days: 14 },
        success_url: success_url || `https://sairn.vercel.app/${app_id}.html?subscribed=true`,
        cancel_url: cancel_url || `https://sairn.vercel.app/${app_id}.html`,
        metadata: { app_id, plan, shop_name },
        allow_promotion_codes: true
      });

      return res.status(200).json({ ok: true, url: session.url });
    }

    // ── REFUND ───────────────────────────────────────────────────

    if (action === 'refund') {
      const { payment_intent_id, amount_cents, reason = 'requested_by_customer' } = req.body;
      if (!payment_intent_id) return res.status(400).json({ error: 'payment_intent_id required' });

      const refund = await stripe.refunds.create({
        payment_intent: payment_intent_id,
        ...(amount_cents ? { amount: amount_cents } : {}),
        reason
      });

      return res.status(200).json({ ok: true, refund_id: refund.id, status: refund.status });
    }

    return res.status(400).json({ error: `Unknown action: ${action}` });

  } catch (err) {
    console.error('[Pay API Error]', err.message);
    if (err.type === 'StripeCardError') {
      return res.status(402).json({ error: err.message, decline_code: err.decline_code });
    }
    return res.status(500).json({ error: err.message });
  }
}
