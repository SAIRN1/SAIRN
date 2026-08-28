import Stripe from 'stripe';

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY);

const ALLOWED_ORIGINS = [
  'https://sairn.vercel.app',
  'https://stonedesk.io',
  'https://fabricor-production.up.railway.app',
  'http://localhost:3000',
  'http://localhost:5173'
];

const BASE_URL = 'https://sairn.vercel.app';

function setCors(res, origin) {
  const o = ALLOWED_ORIGINS.includes(origin) ? origin : BASE_URL;
  res.setHeader('Access-Control-Allow-Origin', o);
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
}

export default async function handler(req, res) {
  const origin = req.headers.origin || '';
  setCors(res, origin);
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  try {
    const { priceId, planName, appId, shopName } = req.body;

    if (!priceId) {
      return res.status(400).json({ error: 'Price ID required' });
    }

    const session = await stripe.checkout.sessions.create({
      mode: 'subscription',
      payment_method_types: ['card'],
      line_items: [{ price: priceId, quantity: 1 }],
      success_url: `${BASE_URL}/SAIRNnexus.html?success=true`,
      cancel_url:  `${BASE_URL}/SAIRNnexus.html?canceled=true`,
      metadata: {
        planName:  planName  || null,
        appId:     appId     || null,
        app_id:    appId     || null,
        shopName:  shopName  || null,
        shop_name: shopName  || null,
      },
      allow_promotion_codes: true,
      subscription_data: {
        trial_period_days: 14,
      },
    });

    return res.status(200).json({ url: session.url });
  } catch (e) {
    console.error('Stripe checkout error:', e);
    return res.status(500).json({ error: e.message });
  }
}
