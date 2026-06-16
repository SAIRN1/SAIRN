// ================================================================
// SAIRNbiz Accounting/Payroll Integrations -- api/accounting.js
// Merged QuickBooks + Gusto into one file (was api/quickbooks.js +
// api/gusto.js separately) to stay under Vercel Hobby's 12 Serverless
// Function limit. Same logic as before, routed by ?provider=.
// Michael L. Dibert -- SAIRN Technologies -- 2026
// ================================================================

import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
);

function setCors(res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
}

// ================================================================
// QUICKBOOKS
// ================================================================
const QB_ENV = process.env.QB_ENVIRONMENT === 'production' ? 'production' : 'sandbox';
const QB_AUTH_BASE  = 'https://appcenter.intuit.com/connect/oauth2';
const QB_TOKEN_URL  = 'https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer';
const QB_API_BASE   = QB_ENV === 'production'
  ? 'https://quickbooks.api.intuit.com/v3/company'
  : 'https://sandbox-quickbooks.api.intuit.com/v3/company';

function qbConfigured() {
  return !!(process.env.QB_CLIENT_ID && process.env.QB_CLIENT_SECRET && process.env.QB_REDIRECT_URI);
}

async function qbRefreshIfNeeded(conn) {
  const expired = !conn.access_token_expires_at || new Date(conn.access_token_expires_at) <= new Date();
  if (!expired) return conn;

  const basic = Buffer.from(`${process.env.QB_CLIENT_ID}:${process.env.QB_CLIENT_SECRET}`).toString('base64');
  const resp = await fetch(QB_TOKEN_URL, {
    method: 'POST',
    headers: { 'Authorization': `Basic ${basic}`, 'Content-Type': 'application/x-www-form-urlencoded', 'Accept': 'application/json' },
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

async function handleQuickBooks(req, res, action) {
  if (!qbConfigured()) {
    return res.status(503).json({ error: 'not_configured', message: 'QuickBooks integration is not yet activated. Requires QB_CLIENT_ID, QB_CLIENT_SECRET, QB_REDIRECT_URI.' });
  }

  if (req.method === 'GET' && action === 'connect') {
    const { shop_id } = req.query;
    if (!shop_id) return res.status(400).json({ error: 'shop_id required' });
    const state = Buffer.from(JSON.stringify({ shop_id, nonce: Date.now() })).toString('base64url');
    const params = new URLSearchParams({
      client_id: process.env.QB_CLIENT_ID, redirect_uri: process.env.QB_REDIRECT_URI,
      response_type: 'code', scope: 'com.intuit.quickbooks.accounting', state
    });
    return res.redirect(302, `${QB_AUTH_BASE}?${params.toString()}`);
  }

  if (req.method === 'GET' && action === 'callback') {
    const { code, state, realmId, error: oauthError } = req.query;
    if (oauthError) return res.status(400).json({ error: 'oauth_denied', detail: oauthError });
    if (!code || !state || !realmId) return res.status(400).json({ error: 'missing_callback_params' });

    let shopId;
    try { shopId = JSON.parse(Buffer.from(state, 'base64url').toString()).shop_id; }
    catch (e) { return res.status(400).json({ error: 'invalid_state' }); }

    const basic = Buffer.from(`${process.env.QB_CLIENT_ID}:${process.env.QB_CLIENT_SECRET}`).toString('base64');
    const tokenResp = await fetch(QB_TOKEN_URL, {
      method: 'POST',
      headers: { 'Authorization': `Basic ${basic}`, 'Content-Type': 'application/x-www-form-urlencoded', 'Accept': 'application/json' },
      body: new URLSearchParams({ grant_type: 'authorization_code', code, redirect_uri: process.env.QB_REDIRECT_URI })
    });
    if (!tokenResp.ok) return res.status(502).json({ error: 'token_exchange_failed', detail: await tokenResp.text() });
    const tok = await tokenResp.json();

    await supabase.from('qb_connections').upsert({
      shop_id: shopId, realm_id: realmId, access_token: tok.access_token, refresh_token: tok.refresh_token,
      access_token_expires_at: new Date(Date.now() + (tok.expires_in - 60) * 1000).toISOString(),
      environment: QB_ENV, connected_at: new Date().toISOString(), updated_at: new Date().toISOString()
    }, { onConflict: 'shop_id' });

    return res.redirect(302, `https://sairn.vercel.app/sairnbiz.html?qb_connected=1`);
  }

  if (req.method === 'GET' && action === 'sync') {
    const { shop_id, resource } = req.query;
    if (!shop_id || !resource) return res.status(400).json({ error: 'shop_id and resource required' });
    const ALLOWED = new Set(['Customer', 'Employee', 'Invoice', 'JournalEntry', 'Vendor', 'Bill']);
    if (!ALLOWED.has(resource)) return res.status(400).json({ error: 'invalid_resource', allowed: Array.from(ALLOWED) });

    const { data: conn } = await supabase.from('qb_connections').select('*').eq('shop_id', shop_id).maybeSingle();
    if (!conn) return res.status(404).json({ error: 'not_connected' });

    let live;
    try { live = await qbRefreshIfNeeded(conn); }
    catch (e) { return res.status(401).json({ error: 'reauth_required', detail: e.message }); }

    const query = encodeURIComponent(`select * from ${resource} maxresults 100`);
    const qbResp = await fetch(`${QB_API_BASE}/${live.realm_id}/query?query=${query}`, {
      headers: { 'Authorization': `Bearer ${live.access_token}`, 'Accept': 'application/json' }
    });
    if (!qbResp.ok) return res.status(qbResp.status).json({ error: 'qb_api_error', detail: await qbResp.text() });
    const data = await qbResp.json();
    return res.status(200).json({ ok: true, resource, data: data.QueryResponse || {} });
  }

  if (req.method === 'POST' && action === 'disconnect') {
    const { shop_id } = req.body || {};
    if (!shop_id) return res.status(400).json({ error: 'shop_id required' });
    await supabase.from('qb_connections').delete().eq('shop_id', shop_id);
    return res.status(200).json({ ok: true });
  }

  if (req.method === 'GET' && action === 'status') {
    const { shop_id } = req.query;
    if (!shop_id) return res.status(400).json({ error: 'shop_id required' });
    const { data: conn } = await supabase.from('qb_connections').select('shop_id, connected_at, environment').eq('shop_id', shop_id).maybeSingle();
    return res.status(200).json({ connected: !!conn, connected_at: conn?.connected_at || null, environment: conn?.environment || null });
  }

  return res.status(400).json({ error: 'unknown_action' });
}

// ================================================================
// GUSTO
// ================================================================
const GUSTO_ENV = process.env.GUSTO_ENVIRONMENT === 'production' ? 'production' : 'demo';
const GUSTO_AUTH_BASE = GUSTO_ENV === 'production' ? 'https://api.gusto.com/oauth/authorize' : 'https://api.gusto-demo.com/oauth/authorize';
const GUSTO_TOKEN_URL = GUSTO_ENV === 'production' ? 'https://api.gusto.com/oauth/token' : 'https://api.gusto-demo.com/oauth/token';
const GUSTO_API_BASE  = GUSTO_ENV === 'production' ? 'https://api.gusto.com/v1' : 'https://api.gusto-demo.com/v1';

function gustoConfigured() {
  return !!(process.env.GUSTO_CLIENT_ID && process.env.GUSTO_CLIENT_SECRET && process.env.GUSTO_REDIRECT_URI);
}

async function gustoRefreshIfNeeded(conn) {
  const expired = !conn.access_token_expires_at || new Date(conn.access_token_expires_at) <= new Date();
  if (!expired) return conn;

  const resp = await fetch(GUSTO_TOKEN_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      client_id: process.env.GUSTO_CLIENT_ID, client_secret: process.env.GUSTO_CLIENT_SECRET,
      redirect_uri: process.env.GUSTO_REDIRECT_URI, refresh_token: conn.refresh_token, grant_type: 'refresh_token'
    })
  });
  if (!resp.ok) throw new Error('gusto_refresh_failed: ' + resp.status);
  const tok = await resp.json();

  const updated = {
    access_token: tok.access_token, refresh_token: tok.refresh_token,
    access_token_expires_at: new Date(Date.now() + (tok.expires_in - 60) * 1000).toISOString(),
    updated_at: new Date().toISOString()
  };
  await supabase.from('gusto_connections').update(updated).eq('shop_id', conn.shop_id);
  return { ...conn, ...updated };
}

async function handleGusto(req, res, action) {
  if (!gustoConfigured()) {
    return res.status(503).json({ error: 'not_configured', message: 'Gusto integration is not yet activated. Requires GUSTO_CLIENT_ID, GUSTO_CLIENT_SECRET, GUSTO_REDIRECT_URI. Production payroll additionally requires Gusto Production Pre-Approval.' });
  }

  if (req.method === 'GET' && action === 'connect') {
    const { shop_id } = req.query;
    if (!shop_id) return res.status(400).json({ error: 'shop_id required' });
    const state = Buffer.from(JSON.stringify({ shop_id, nonce: Date.now() })).toString('base64url');
    const params = new URLSearchParams({ client_id: process.env.GUSTO_CLIENT_ID, redirect_uri: process.env.GUSTO_REDIRECT_URI, response_type: 'code', state });
    return res.redirect(302, `${GUSTO_AUTH_BASE}?${params.toString()}`);
  }

  if (req.method === 'GET' && action === 'callback') {
    const { code, state, error: oauthError } = req.query;
    if (oauthError) return res.status(400).json({ error: 'oauth_denied', detail: oauthError });
    if (!code || !state) return res.status(400).json({ error: 'missing_callback_params' });

    let shopId;
    try { shopId = JSON.parse(Buffer.from(state, 'base64url').toString()).shop_id; }
    catch (e) { return res.status(400).json({ error: 'invalid_state' }); }

    const tokenResp = await fetch(GUSTO_TOKEN_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        client_id: process.env.GUSTO_CLIENT_ID, client_secret: process.env.GUSTO_CLIENT_SECRET,
        redirect_uri: process.env.GUSTO_REDIRECT_URI, code, grant_type: 'authorization_code'
      })
    });
    if (!tokenResp.ok) return res.status(502).json({ error: 'token_exchange_failed', detail: await tokenResp.text() });
    const tok = await tokenResp.json();

    const meResp = await fetch(`${GUSTO_API_BASE}/me`, { headers: { 'Authorization': `Bearer ${tok.access_token}` } });
    const me = meResp.ok ? await meResp.json() : {};
    const companyUuid = me?.roles?.payroll_admin?.companies?.[0]?.uuid || null;

    await supabase.from('gusto_connections').upsert({
      shop_id: shopId, company_uuid: companyUuid, access_token: tok.access_token, refresh_token: tok.refresh_token,
      access_token_expires_at: new Date(Date.now() + (tok.expires_in - 60) * 1000).toISOString(),
      environment: GUSTO_ENV, connected_at: new Date().toISOString(), updated_at: new Date().toISOString()
    }, { onConflict: 'shop_id' });

    return res.redirect(302, `https://sairn.vercel.app/sairnbiz.html?gusto_connected=1`);
  }

  if (req.method === 'GET' && action === 'sync') {
    const { shop_id, resource } = req.query;
    if (!shop_id || !resource) return res.status(400).json({ error: 'shop_id and resource required' });
    const ALLOWED = new Set(['employees', 'payrolls', 'pay_schedules']);
    if (!ALLOWED.has(resource)) return res.status(400).json({ error: 'invalid_resource', allowed: Array.from(ALLOWED) });

    const { data: conn } = await supabase.from('gusto_connections').select('*').eq('shop_id', shop_id).maybeSingle();
    if (!conn) return res.status(404).json({ error: 'not_connected' });
    if (!conn.company_uuid) return res.status(409).json({ error: 'no_company_uuid_on_record' });

    let live;
    try { live = await gustoRefreshIfNeeded(conn); }
    catch (e) { return res.status(401).json({ error: 'reauth_required', detail: e.message }); }

    const gResp = await fetch(`${GUSTO_API_BASE}/companies/${live.company_uuid}/${resource}`, { headers: { 'Authorization': `Bearer ${live.access_token}` } });
    if (!gResp.ok) return res.status(gResp.status).json({ error: 'gusto_api_error', detail: await gResp.text() });
    const data = await gResp.json();
    return res.status(200).json({ ok: true, resource, data });
  }

  if (req.method === 'POST' && action === 'disconnect') {
    const { shop_id } = req.body || {};
    if (!shop_id) return res.status(400).json({ error: 'shop_id required' });
    await supabase.from('gusto_connections').delete().eq('shop_id', shop_id);
    return res.status(200).json({ ok: true });
  }

  if (req.method === 'GET' && action === 'status') {
    const { shop_id } = req.query;
    if (!shop_id) return res.status(400).json({ error: 'shop_id required' });
    const { data: conn } = await supabase.from('gusto_connections').select('shop_id, connected_at, environment').eq('shop_id', shop_id).maybeSingle();
    return res.status(200).json({ connected: !!conn, connected_at: conn?.connected_at || null, environment: conn?.environment || null });
  }

  return res.status(400).json({ error: 'unknown_action' });
}

// ================================================================
// ENTRY POINT
// ================================================================
export default async function handler(req, res) {
  setCors(res);
  if (req.method === 'OPTIONS') return res.status(200).end();

  const { provider, action } = req.query;
  if (provider === 'quickbooks') return handleQuickBooks(req, res, action);
  if (provider === 'gusto') return handleGusto(req, res, action);
  return res.status(400).json({ error: 'invalid_provider', allowed: ['quickbooks', 'gusto'] });
}

// ================================================================
// SETUP NOTES
// QuickBooks redirect URI: https://sairn.vercel.app/api/accounting?provider=quickbooks&action=callback
// Gusto redirect URI:      https://sairn.vercel.app/api/accounting?provider=gusto&action=callback
// (update these in Intuit Developer / Gusto Developer Portal app settings,
// and update QB_REDIRECT_URI / GUSTO_REDIRECT_URI env vars to match)
// ================================================================
