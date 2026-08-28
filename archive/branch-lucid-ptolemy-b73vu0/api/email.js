// ================================================================
// SAIRN Email Proxy -- api/email.js (v1)
// Provider: Resend (resend.com) -- no domain verification required
// Env var:  RESEND_API_KEY (set in Vercel dashboard)
// Handles:  pay stubs, invoices, client emails, any SAIRN app mail
// Michael L. Dibert -- SAIRN Technologies -- 2026
// ================================================================

const RESEND_API = 'https://api.resend.com/emails';

// Allowed sender domains -- update when custom domain verified
// Until then, Resend provides onboarding@resend.dev for testing
const VERIFIED_FROM = process.env.RESEND_FROM_EMAIL || 'onboarding@resend.dev';

// Allowed app sources
const ALLOWED_APPS = new Set([
  'sairnbiz', 'stonedesk', 'fabricor', 'sairnbuild', 'sairnscape',
  'sairnlaw', 'sairncode', 'sairndesign', 'sairnvet', 'sairnvetglobal',
  'sairncare', 'sairnfuneral', 'sairnmechanical', 'sairntrade',
  'sairnhr', 'sairnacc'
]);

// Rate limit: max 20 emails per IP per day (abuse prevention)
const emailCalls = new Map();
function checkEmailRate(req) {
  const ip = (req.headers['x-forwarded-for'] || '').split(',')[0].trim() || 'unknown';
  const key = ip + '_' + new Date().toISOString().slice(0, 10);
  const count = emailCalls.get(key) || 0;
  if (count >= 20) return false;
  emailCalls.set(key, count + 1);
  // Clean old keys every 500 calls
  if (emailCalls.size > 500) {
    const today = new Date().toISOString().slice(0, 10);
    for (const [k] of emailCalls) {
      if (!k.includes(today)) emailCalls.delete(k);
    }
  }
  return true;
}

// Build plain-text fallback from HTML
function htmlToText(html) {
  return html
    .replace(/<style[^>]*>[\s\S]*?<\/style>/gi, '')
    .replace(/<[^>]+>/g, ' ')
    .replace(/\s{2,}/g, ' ')
    .trim()
    .slice(0, 2000);
}

// Validate email address (basic)
function isValidEmail(email) {
  return typeof email === 'string' && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim());
}

export default async function handler(req, res) {
  // CORS
  res.setHeader('Access-Control-Allow-Origin', req.headers.origin || '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  // Check Resend key configured
  const RESEND_KEY = process.env.RESEND_API_KEY;
  if (!RESEND_KEY) {
    return res.status(503).json({
      error: 'Email service not configured. Add RESEND_API_KEY to Vercel environment variables.',
      setup_url: 'https://vercel.com/dashboard -> Your Project -> Settings -> Environment Variables'
    });
  }

  // Rate limit
  if (!checkEmailRate(req)) {
    return res.status(429).json({ error: 'Email rate limit reached (20/day). Try again tomorrow.' });
  }

  let body;
  try {
    body = typeof req.body === 'string' ? JSON.parse(req.body) : req.body;
  } catch (e) {
    return res.status(400).json({ error: 'Invalid JSON body' });
  }

  const {
    app_id,
    to,           // string or array of strings
    subject,      // required
    html,         // HTML body (preferred)
    text,         // plain text fallback (auto-generated if omitted)
    from_name,    // display name, e.g. "StoneDesk"
    reply_to,     // optional reply-to address
    email_type,   // 'paystub' | 'invoice' | 'estimate' | 'general' | 'alert'
  } = body || {};

  // Validate app_id
  if (!app_id || !ALLOWED_APPS.has(app_id)) {
    return res.status(400).json({ error: 'Invalid or missing app_id' });
  }

  // Validate recipients
  const recipients = Array.isArray(to) ? to : [to];
  if (!recipients.length || recipients.some(e => !isValidEmail(e))) {
    return res.status(400).json({ error: 'Invalid or missing recipient email address(es)' });
  }
  if (recipients.length > 10) {
    return res.status(400).json({ error: 'Max 10 recipients per call' });
  }

  // Validate subject
  if (!subject || typeof subject !== 'string' || subject.trim().length < 2) {
    return res.status(400).json({ error: 'Missing or invalid subject' });
  }

  // Validate body
  if (!html && !text) {
    return res.status(400).json({ error: 'Must provide html or text body' });
  }

  // Build from address
  const appDisplayNames = {
    sairnbiz: 'SAIRNbiz', stonedesk: 'StoneDesk', fabricor: 'StoneDesk',
    sairnbuild: 'SAIRNbuild', sairnscape: 'SAIRNscape', sairnlaw: 'SAIRNlaw',
    sairncode: 'SAIRNcode', sairndesign: 'SAIRNdesign', sairnvet: 'SAIRNvet',
    sairnvetglobal: 'SAIRNvetGlobal', sairncare: 'SAIRNcare',
    sairnfuneral: 'SAIRNfuneral', sairnmechanical: 'SAIRNmechanical',
    sairnhr: 'SAIRNhr', sairnacc: 'SAIRNacc'
  };
  const displayName = from_name || appDisplayNames[app_id] || 'SAIRN';
  const fromAddress = `${displayName} <${VERIFIED_FROM}>`;

  // Build Resend payload
  const resendPayload = {
    from: fromAddress,
    to: recipients,
    subject: subject.trim(),
    html: html || `<pre style="font-family:monospace">${text}</pre>`,
    text: text || htmlToText(html || ''),
  };

  if (reply_to && isValidEmail(reply_to)) {
    resendPayload.reply_to = reply_to;
  }

  // Send via Resend
  try {
    const response = await fetch(RESEND_API, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${RESEND_KEY}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(resendPayload),
    });

    const result = await response.json();

    if (!response.ok) {
      console.error('Resend error:', result);
      return res.status(response.status).json({
        error: 'Email delivery failed',
        detail: result.message || result.error || 'Unknown Resend error',
        resend_status: response.status
      });
    }

    // Success
    return res.status(200).json({
      success: true,
      message_id: result.id,
      to: recipients,
      app_id,
      email_type: email_type || 'general',
      sent_at: new Date().toISOString()
    });

  } catch (err) {
    console.error('SAIRN email proxy error:', err);
    return res.status(500).json({
      error: 'Email service error',
      detail: err.message
    });
  }
}
