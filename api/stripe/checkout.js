import Stripe from 'stripe';

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY);

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const { priceId, planName } = req.body;

    if (!priceId) {
      return res.status(400).json({ error: 'Price ID required' });
    }

    const session = await stripe.checkout.sessions.create({
      mode: 'subscription',
      payment_method_types: ['card'],
      line_items: [{ price: priceId, quantity: 1 }],
      success_url: `${req.headers.origin || 'https://sairn.vercel.app'}/SAIRNnexus.html?success=true`,
      cancel_url: `${req.headers.origin || 'https://sairn.vercel.app'}/SAIRNnexus.html?canceled=true`,
      metadata: { planName },
      allow_promotion_codes: true,
      subscription_data: {
        trial_period_days: 14,
      },
    });

    res.json({ url: session.url });
  } catch (e) {
    console.error('Stripe checkout error:', e);
    res.status(500).json({ error: e.message });
  }
}
