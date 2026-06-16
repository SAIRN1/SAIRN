// ================================================================
// SAIRNbiz QuickBooks Online Integration -- api/quickbooks.js
// OAuth 2.0 authorization code flow per Intuit's spec. Tokens stored
// per-shop in Supabase (qb_connections), never in the frontend.
// Requires env vars: QB_CLIENT_ID, QB_CLIENT_SECRET, QB_REDIRECT_URI
// (set these once an Intuit Developer app is registered -- see setup notes
// at the bottom of this file). Until those exist, every route here
// returns 503 "not_configured" rather than crashing.
// Michael L. Dibert -- SAIRN Technologies -- 2026
// ================================================================

import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
);

const QB_ENV = process.env.QB_ENVIRONMENT === 'production' ? 'production' : 'sandbox';
const QB_AUTH_BASE  = 'https://appcenter.intuit.com/connect/oauth2';
const QB_TOKEN_URL  = 'https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer';
const QB_API_BASE   = QB_ENV === 'production'
  ? 'https://quickbooks.api.intuit.com/v3/company'
  : 'https://sandbox-quickbooks.api.intuit.com/v3/company';

function isConfigured() {
  return !!(process.env.QB_CLIENT_ID && process.env.QB_CLIENT_SECRET && process.env.QB_REDIRECT_URI);
}

function setCors(res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
}

async function refreshIfNeeded(conn) {
  // QuickBooks access tokens expire in ~1hr; refresh tokens last ~100 days.
  const expired = !conn.access_token_expires_at || new Date(conn.access_token_expires_at) <= new Date();
  if (!expired) return conn;

  const basic = Buffer.from(`${process.env.QB_CLIENT_ID}:${process.env.QB_CLIENT_SECRET}`).toString('base64');
  const resp = await fetch(QB_TOKEN_URL, {
    method: 'POST',
    headers: {
      'Authorization': `Basic ${basic}`,
      'Content-Type': 'application/x-www-form-urlencoded',
      'Accept': 'application/json'
    },
    body: new URLSearchParams({ grant_type: 'refresh_token', refresh_token: conn.refresh_token })
  });
  if (!resp.ok) throw new Error('qb_refresh_failed: ' + resp.status);
  const tok = await resp.json();

  const updated = {
    access_token: tok.access_token,
    refresh_token: tok.refresh_token,
    access_token_expires_at: new Date(Date.now() + (tok.expires_in - 60) * 1000).toISOString(),
    updated_at: new Date().toISOString()
  };
  await supabase.from('qb_connections').update(updated).eq('shop_id', conn.shop_id);
  return { ...conn, ...updated };
}

export default async function handler(req, res) {
  setCors(res);
  if (req.method === 'OPTIONS') return res.status(200).end();

  if (!isConfigured()) {
    return res.status(503).json({
      error: 'not_configured',
      message: 'QuickBooks integration is not yet activated. Requires QB_CLIENT_ID, QB_CLIENT_SECRET, QB_REDIRECT_URI from an Intuit Developer app.'
    });
  }

  const { action } = req.query;

  // ── STEP 1: start the OAuth flow -- frontend redirects the user here ──
  if (req.method === 'GET' && action === 'connect') {
    const { shop_id } = req.query;
    if (!shop_id) return res.status(400).json({ error: 'shop_id required' });

    const state = Buffer.from(JSON.stringify({ shop_id, nonce: Date.now() })).toString('base64url');
    const params = new URLSearchParams({
      client_id: process.env.QB_CLIENT_ID,
      redirect_uri: process.env.QB_REDIRECT_URI,
      response_type: 'code',
      scope: 'com.intuit.quickbooks.accounting',
      state
    });
    return res.redirect(302, `${QB_AUTH_BASE}?${params.toString()}`);
  }

  // ── STEP 2: Intuit redirects back here with an auth code ──
  if (req.method === 'GET' && action === 'callback') {
    const { code, state, realmId, error: oauthError } = req.query;
    if (oauthError) return res.status(400).json({ error: 'oauth_denied', detail: oauthError });
    if (!code || !state || !realmId) return res.status(400).json({ error: 'missing_callback_params' });

    let shopId;
    try {
      shopId = JSON.parse(Buffer.from(state, 'base64url').toString()).shop_id;
    } catch (e) {
      return res.status(400).json({ error: 'invalid_state' });
    }

    const basic = Buffer.from(`${process.env.QB_CLIENT_ID}:${process.env.QB_CLIENT_SECRET}`).toString('base64');
    const tokenResp = await fetch(QB_TOKEN_URL, {
      method: 'POST',
      headers: {
        'Authorization': `Basic ${basic}`,
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json'
      },
      body: new URLSearchParams({
        grant_type: 'authorization_code',
        code,
        redirect_uri: process.env.QB_REDIRECT_URI
      })
    });

    if (!tokenResp.ok) {
      const errText = await tokenResp.text();
      return res.status(502).json({ error: 'token_exchange_failed', detail: errText });
    }
    const tok = await tokenResp.json();

    await supabase.from('qb_connections').upsert({
      shop_id: shopId,
      realm_id: realmId,
      access_token: tok.access_token,
      refresh_token: tok.refresh_token,
      access_token_expires_at: new Date(Date.now() + (tok.expires_in - 60) * 1000).toISOString(),
      environment: QB_ENV,
      connected_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    }, { onConflict: 'shop_id' });

    // Redirect back into the app with a success flag the frontend can check
    return res.redirect(302, `https://sairn.vercel.app/sairnbiz.html?qb_connected=1`);
  }

  // ── Sync: pull a resource (customers, employees, invoices, journal entries) ──
  if (req.method === 'GET' && action === 'sync') {
    const { shop_id, resource } = req.query;
    if (!shop_id || !resource) return res.status(400).json({ error: 'shop_id and resource required' });

    const ALLOWED_RESOURCES = new Set(['Customer', 'Employee', 'Invoice', 'JournalEntry', 'Vendor', 'Bill']);
    if (!ALLOWED_RESOURCES.has(resource)) {
      return res.status(400).json({ error: 'invalid_resource', allowed: Array.from(ALLOWED_RESOURCES) });
    }

    const { data: conn } = await supabase.from('qb_connections').select('*').eq('shop_id', shop_id).maybeSingle();
    if (!conn) return res.status(404).json({ error: 'not_connected' });

    let live;
    try {
      live = await refreshIfNeeded(conn);
    } catch (e) {
      return res.status(401).json({ error: 'reauth_required', detail: e.message });
    }

    const query = encodeURIComponent(`select * from ${resource} maxresults 100`);
    const qbResp = await fetch(`${QB_API_BASE}/${live.realm_id}/query?query=${query}`, {
      headers: { 'Authorization': `Bearer ${live.access_token}`, 'Accept': 'application/json' }
    });

    if (!qbResp.ok) {
      const errText = await qbResp.text();
      return res.status(qbResp.status).json({ error: 'qb_api_error', detail: errText });
    }
    const data = await qbResp.json();
    return res.status(200).json({ ok: true, resource, data: data.QueryResponse || {} });
  }

  // ── Disconnect ──
  if (req.method === 'POST' && action === 'disconnect') {
    const { shop_id } = req.body || {};
    if (!shop_id) return res.status(400).json({ error: 'shop_id required' });
    await supabase.from('qb_connections').delete().eq('shop_id', shop_id);
    return res.status(200).json({ ok: true });
  }

  // ── Status check (frontend uses this to decide whether to show "Connect" or "Connected") ──
  if (req.method === 'GET' && action === 'status') {
    const { shop_id } = req.query;
    if (!shop_id) return res.status(400).json({ error: 'shop_id required' });
    const { data: conn } = await supabase.from('qb_connections').select('shop_id, connected_at, environment').eq('shop_id', shop_id).maybeSingle();
    return res.status(200).json({ connected: !!conn, connected_at: conn?.connected_at || null, environment: conn?.environment || null });
  }

  return res.status(400).json({ error: 'unknown_action' });
}

// ================================================================
// ONE-TIME SETUP (only Michael can do this -- account-level, not code):
// 1. https://developer.intuit.com -> sign in -> Create an app -> QuickBooks Online and Payments
// 2. App dashboard -> Keys & OAuth -> copy Client ID and Client Secret (sandbox first)
// 3. Add Redirect URI: https://sairn.vercel.app/api/quickbooks?action=callback
// 4. Vercel env vars: QB_CLIENT_ID, QB_CLIENT_SECRET, QB_REDIRECT_URI
//    (= https://sairn.vercel.app/api/quickbooks?action=callback), QB_ENVIRONMENT=sandbox
// 5. Run db/schema_quickbooks.sql in Supabase
// 6. Test: visit /api/quickbooks?action=connect&shop_id=test123 -- should redirect to Intuit login
// 7. When ready for real customers: Intuit app review -> production keys -> QB_ENVIRONMENT=production
// ================================================================
