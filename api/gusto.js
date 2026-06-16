// ================================================================
// SAIRNbiz Gusto Integration -- api/gusto.js
// OAuth 2.0 per Gusto's spec. Tokens stored per-shop in Supabase
// (gusto_connections), never in the frontend.
//
// IMPORTANT: Gusto requires Production Pre-Approval from their Partnerships
// team before this can touch real customer payroll data -- that approval
// is a business/account step, not something built in code. Until
// GUSTO_CLIENT_ID/SECRET exist (sandbox is available immediately after
// Developer Portal signup, no approval needed for testing), every route
// returns 503 rather than crashing. Production access needs the approval.
// Michael L. Dibert -- SAIRN Technologies -- 2026
// ================================================================

import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
);

const GUSTO_ENV = process.env.GUSTO_ENVIRONMENT === 'production' ? 'production' : 'demo';
const GUSTO_AUTH_BASE  = GUSTO_ENV === 'production'
  ? 'https://api.gusto.com/oauth/authorize'
  : 'https://api.gusto-demo.com/oauth/authorize';
const GUSTO_TOKEN_URL  = GUSTO_ENV === 'production'
  ? 'https://api.gusto.com/oauth/token'
  : 'https://api.gusto-demo.com/oauth/token';
const GUSTO_API_BASE   = GUSTO_ENV === 'production'
  ? 'https://api.gusto.com/v1'
  : 'https://api.gusto-demo.com/v1';

function isConfigured() {
  return !!(process.env.GUSTO_CLIENT_ID && process.env.GUSTO_CLIENT_SECRET && process.env.GUSTO_REDIRECT_URI);
}

function setCors(res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
}

async function refreshIfNeeded(conn) {
  const expired = !conn.access_token_expires_at || new Date(conn.access_token_expires_at) <= new Date();
  if (!expired) return conn;

  const resp = await fetch(GUSTO_TOKEN_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      client_id: process.env.GUSTO_CLIENT_ID,
      client_secret: process.env.GUSTO_CLIENT_SECRET,
      redirect_uri: process.env.GUSTO_REDIRECT_URI,
      refresh_token: conn.refresh_token,
      grant_type: 'refresh_token'
    })
  });
  if (!resp.ok) throw new Error('gusto_refresh_failed: ' + resp.status);
  const tok = await resp.json();

  const updated = {
    access_token: tok.access_token,
    refresh_token: tok.refresh_token,
    access_token_expires_at: new Date(Date.now() + (tok.expires_in - 60) * 1000).toISOString(),
    updated_at: new Date().toISOString()
  };
  await supabase.from('gusto_connections').update(updated).eq('shop_id', conn.shop_id);
  return { ...conn, ...updated };
}

export default async function handler(req, res) {
  setCors(res);
  if (req.method === 'OPTIONS') return res.status(200).end();

  if (!isConfigured()) {
    return res.status(503).json({
      error: 'not_configured',
      message: 'Gusto integration is not yet activated. Requires GUSTO_CLIENT_ID, GUSTO_CLIENT_SECRET, GUSTO_REDIRECT_URI from a Gusto Developer Portal app. Production payroll access additionally requires Gusto Production Pre-Approval -- sandbox/demo works without it.'
    });
  }

  const { action } = req.query;

  // ── STEP 1: start the OAuth flow ──
  if (req.method === 'GET' && action === 'connect') {
    const { shop_id } = req.query;
    if (!shop_id) return res.status(400).json({ error: 'shop_id required' });

    const state = Buffer.from(JSON.stringify({ shop_id, nonce: Date.now() })).toString('base64url');
    const params = new URLSearchParams({
      client_id: process.env.GUSTO_CLIENT_ID,
      redirect_uri: process.env.GUSTO_REDIRECT_URI,
      response_type: 'code',
      state
    });
    return res.redirect(302, `${GUSTO_AUTH_BASE}?${params.toString()}`);
  }

  // ── STEP 2: Gusto redirects back here with an auth code ──
  if (req.method === 'GET' && action === 'callback') {
    const { code, state, error: oauthError } = req.query;
    if (oauthError) return res.status(400).json({ error: 'oauth_denied', detail: oauthError });
    if (!code || !state) return res.status(400).json({ error: 'missing_callback_params' });

    let shopId;
    try {
      shopId = JSON.parse(Buffer.from(state, 'base64url').toString()).shop_id;
    } catch (e) {
      return res.status(400).json({ error: 'invalid_state' });
    }

    const tokenResp = await fetch(GUSTO_TOKEN_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        client_id: process.env.GUSTO_CLIENT_ID,
        client_secret: process.env.GUSTO_CLIENT_SECRET,
        redirect_uri: process.env.GUSTO_REDIRECT_URI,
        code,
        grant_type: 'authorization_code'
      })
    });

    if (!tokenResp.ok) {
      const errText = await tokenResp.text();
      return res.status(502).json({ error: 'token_exchange_failed', detail: errText });
    }
    const tok = await tokenResp.json();

    // Gusto's company UUID is fetched from the /v1/me endpoint after auth
    const meResp = await fetch(`${GUSTO_API_BASE}/me`, {
      headers: { 'Authorization': `Bearer ${tok.access_token}` }
    });
    const me = meResp.ok ? await meResp.json() : {};
    const companyUuid = me?.roles?.payroll_admin?.companies?.[0]?.uuid || null;

    await supabase.from('gusto_connections').upsert({
      shop_id: shopId,
      company_uuid: companyUuid,
      access_token: tok.access_token,
      refresh_token: tok.refresh_token,
      access_token_expires_at: new Date(Date.now() + (tok.expires_in - 60) * 1000).toISOString(),
      environment: GUSTO_ENV,
      connected_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    }, { onConflict: 'shop_id' });

    return res.redirect(302, `https://sairn.vercel.app/sairnbiz.html?gusto_connected=1`);
  }

  // ── Sync: pull employees or payrolls ──
  if (req.method === 'GET' && action === 'sync') {
    const { shop_id, resource } = req.query;
    if (!shop_id || !resource) return res.status(400).json({ error: 'shop_id and resource required' });

    const ALLOWED_RESOURCES = new Set(['employees', 'payrolls', 'pay_schedules']);
    if (!ALLOWED_RESOURCES.has(resource)) {
      return res.status(400).json({ error: 'invalid_resource', allowed: Array.from(ALLOWED_RESOURCES) });
    }

    const { data: conn } = await supabase.from('gusto_connections').select('*').eq('shop_id', shop_id).maybeSingle();
    if (!conn) return res.status(404).json({ error: 'not_connected' });
    if (!conn.company_uuid) return res.status(409).json({ error: 'no_company_uuid_on_record' });

    let live;
    try {
      live = await refreshIfNeeded(conn);
    } catch (e) {
      return res.status(401).json({ error: 'reauth_required', detail: e.message });
    }

    const gResp = await fetch(`${GUSTO_API_BASE}/companies/${live.company_uuid}/${resource}`, {
      headers: { 'Authorization': `Bearer ${live.access_token}` }
    });

    if (!gResp.ok) {
      const errText = await gResp.text();
      return res.status(gResp.status).json({ error: 'gusto_api_error', detail: errText });
    }
    const data = await gResp.json();
    return res.status(200).json({ ok: true, resource, data });
  }

  // ── Disconnect ──
  if (req.method === 'POST' && action === 'disconnect') {
    const { shop_id } = req.body || {};
    if (!shop_id) return res.status(400).json({ error: 'shop_id required' });
    await supabase.from('gusto_connections').delete().eq('shop_id', shop_id);
    return res.status(200).json({ ok: true });
  }

  // ── Status check ──
  if (req.method === 'GET' && action === 'status') {
    const { shop_id } = req.query;
    if (!shop_id) return res.status(400).json({ error: 'shop_id required' });
    const { data: conn } = await supabase.from('gusto_connections').select('shop_id, connected_at, environment').eq('shop_id', shop_id).maybeSingle();
    return res.status(200).json({ connected: !!conn, connected_at: conn?.connected_at || null, environment: conn?.environment || null });
  }

  return res.status(400).json({ error: 'unknown_action' });
}

// ================================================================
// ONE-TIME SETUP (only Michael can do this -- account-level, not code):
// 1. https://dev.gusto.com -> sign up for a Developer Portal account
// 2. Create an app -> copy Client ID and Client Secret (works against
//    api.gusto-demo.com immediately, no approval needed for demo/testing)
// 3. Add Redirect URI: https://sairn.vercel.app/api/gusto?action=callback
// 4. Vercel env vars: GUSTO_CLIENT_ID, GUSTO_CLIENT_SECRET, GUSTO_REDIRECT_URI
//    (= https://sairn.vercel.app/api/gusto?action=callback), GUSTO_ENVIRONMENT=demo
// 5. Run db/schema_gusto.sql in Supabase
// 6. Test against demo: visit /api/gusto?action=connect&shop_id=test123
// 7. BEFORE any real customer payroll: submit Gusto's Production Pre-Approval
//    application (https://dev.gusto.com -> Partnerships). This is a business
//    review, not a code task -- start it early, it gates production access.
//    Once approved: production keys -> GUSTO_ENVIRONMENT=production
// ================================================================
