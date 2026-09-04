// api/accounting.js
// SHARED read-only accounting connector endpoint.
//
// ── THE NAME IS DELIBERATELY REUSED, AND HERE IS WHY THAT IS SAFE ────────
// An api/accounting.js existed once. It was created 2026-06-16 on the
// lucid-ptolemy branch, was NEVER merged to main, is reachable only from the
// archive tag, and was never deployed -- /api/accounting returned 404 on
// 2026-09-02, which is how this was found. It is not being replaced or
// resurrected; the name was simply free. That file was keyed on shop_id
// (StoneDesk-shaped, not shared) and bundled Gusto payroll into the same
// function to fit a Vercel 12-function Hobby limit that no longer binds.
// It was read for the raw OAuth shape and nothing else.
//
// ── WHAT WORKS TODAY AND WHAT DOES NOT ───────────────────────────────────
// WORKS, and is tested: recording an explicit consent, revoking one, and
// reporting the true state of the connection and of the environment.
//
// DOES NOT WORK, and says so on every affected action: the OAuth leg. There
// is no Intuit application and no QB_CLIENT_ID / QB_CLIENT_SECRET /
// QB_REDIRECT_URI in any environment, so no authorisation URL can be produced
// and no code can be exchanged for a token.
//
// THE OAUTH ACTIONS RETURN 501 WITH THE REAL REASON. They do not return a
// fake URL, a stub token, or a success shape with empty data. The whole reason
// this rebuild exists is that a previous version of this feature was described
// as working when it was not, in three places at once, to customers. A
// simulated token exchange would be the same defect with better manners.
//
// ── THE THREE PROMISES ARE ENFORCED IN api/_lib/accounting-connector.js ──
// read-only, explicit opt-in per customer, never auto-connect. This file
// carries none of those rules itself: it fetches rows, calls the engine, and
// does what the engine says. Two implementations of "may this be read" would
// eventually disagree, and the one in the endpoint would be the one nobody
// tested.

'use strict';

const { validateLicenseKey } = require('./_lib/license');
const { verifySessionToken, tokenFromRequest } = require('./_lib/auth');
const connector = require('./_lib/accounting-connector');
const vault = require('./_lib/token-vault');

const IDENT_RE = /^[a-z0-9_-]+$/i;
const MAX_ID_LEN = 64;

// Which roles may see or change a customer's accounting connection. This is
// commercial and contractual information about the business itself, not
// operational data, so it sits at the same tier as programme standing and
// bonding limits rather than being visible to a crew member.
const MANAGEMENT_ROLES = { owner: true, admin: true };

function setCors(res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-SD-Auth');
}

function todayFrom(payload) {
  const t = payload && payload.today;
  return (typeof t === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(t)) ? t : null;
}

// The provider credentials, reported never returned. `configured` is the only
// thing that leaves this function -- an endpoint that echoed which secret was
// missing would be telling an unauthenticated caller about the environment.
function providerConfigured() {
  return !!(process.env.QB_CLIENT_ID && process.env.QB_CLIENT_SECRET && process.env.QB_REDIRECT_URI);
}

module.exports = async (req, res) => {
  setCors(res);
  if (req.method === 'OPTIONS') { res.status(204).end(); return; }
  if (req.method !== 'POST') { res.status(405).json({ error: { message: 'Method not allowed' } }); return; }

  const SUPABASE_URL = process.env.SUPABASE_URL;
  const SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!SUPABASE_URL || !SERVICE_KEY) {
    console.error('SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set');
    res.status(500).json({ error: { message: 'Server configuration error — contact support' } });
    return;
  }

  const body = req.body || {};
  const action = String(body.action || '');
  const appId = String(body.app_id || '');
  const payload = body.payload || {};

  if (!IDENT_RE.test(appId) || appId.length > MAX_ID_LEN) {
    res.status(400).json({ error: { message: 'app_id is required and must be a short identifier' } });
    return;
  }

  const licKey = (req.headers.authorization || '').replace(/^Bearer\s+/i, '').trim();
  const lic = await validateLicenseKey(licKey);
  if (!lic || !lic.valid) { res.status(401).json({ error: { code: 'INVALID_LICENSE', message: 'Unknown license key' } }); return; }
  if (!lic.active) { res.status(403).json({ error: { code: 'LICENSE_INACTIVE', message: 'This license is not active' } }); return; }
  const licHash = lic.license_hash;

  // The session is verified against the app the caller CLAIMS to be, so a
  // token minted for one app cannot be replayed at another through this shared
  // endpoint. Same rule every per-app data path already applies.
  const session = verifySessionToken(tokenFromRequest(req), licHash, appId);
  if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
  if (!MANAGEMENT_ROLES[session.role]) {
    res.status(403).json({ error: { code: 'FORBIDDEN', message: 'A connection to your accounting package is management-level information' } });
    return;
  }

  const headers = { apikey: SERVICE_KEY, Authorization: 'Bearer ' + SERVICE_KEY, 'Content-Type': 'application/json' };
  const rest = (p) => SUPABASE_URL + '/rest/v1/' + p;
  const enc = encodeURIComponent;
  const provider = String(payload.provider || 'quickbooks_online');
  if (connector.PROVIDERS.indexOf(provider) === -1) {
    res.status(400).json({ error: { code: 'BAD_PROVIDER', message: 'provider must be one of ' + connector.PROVIDERS.join(', ') } });
    return;
  }

  const today = todayFrom(payload);
  // Every dated answer needs the caller's date, for the reason every other
  // engine on this platform gives: a server clock answers a local-date question
  // in UTC and is wrong for several hours a day.
  const needsToday = ['status', 'consent', 'revoke', 'read'];
  if (needsToday.indexOf(action) !== -1 && !today) {
    res.status(400).json({ error: { code: 'NO_TODAY', message: 'payload.today (YYYY-MM-DD) is required' } });
    return;
  }

  // Reads the live consent (most recent un-revoked grant) and the connection.
  // Both may legitimately be absent; that is a state, not an error.
  async function loadState() {
    const cr = await fetch(rest('accounting_consents?license_hash=eq.' + enc(licHash) +
      '&provider=eq.' + enc(provider) +
      '&select=consent_id,provider,granted_by,granted_on,scopes,revoked_on,revoked_by&order=granted_on.desc'), { headers });
    if (cr.status === 404 || cr.status === 400) return { provisioned: false };
    // AN UNREADABLE CONSENT TABLE IS NOT AN ABSENT CONSENT (2026-09-04).
    // These fell back to [], so `live` became null and `status` reported the
    // customer as NOT CONSENTED and NOT CONNECTED -- a statement about a legal
    // artifact, made because a read failed. The 404/400 branch above already
    // distinguishes not-provisioned; unreadable needs its own answer rather
    // than borrowing "no consent".
    if (!cr.ok) return { unreadable: true, detail: 'accounting_consents HTTP ' + cr.status };
    const consents = await cr.json().catch(() => null);
    if (!Array.isArray(consents)) return { unreadable: true, detail: 'accounting_consents returned a non-array' };
    const live = consents.filter((c) => !c.revoked_on)[0] || null;
    const nr = await fetch(rest('accounting_connections?license_hash=eq.' + enc(licHash) +
      '&provider=eq.' + enc(provider) +
      '&select=provider,consent_id,realm_id,status,expires_on,last_read_at,last_error,refresh_token_enc&limit=1'), { headers });
    if (!nr.ok) return { unreadable: true, detail: 'accounting_connections HTTP ' + nr.status };
    const conns = await nr.json().catch(() => null);
    if (!Array.isArray(conns)) return { unreadable: true, detail: 'accounting_connections returned a non-array' };
    const conn = conns[0] || null;
    return { provisioned: true, consents: consents, live: live, conn: conn };
  }

  try {
    // ── STATUS ────────────────────────────────────────────────────────────
    // The honest picture, and the action a UI should lead with. It reports
    // three separate things that fail for different reasons and must not be
    // collapsed: is the schema there, is the environment configured, and has
    // this customer consented.
    if (action === 'status') {
      const st = await loadState();
      // `unreadable` must be checked BEFORE `provisioned`: an unreadable state
      // has no `provisioned` field, so falling through would report "the tables
      // are not set up" -- swapping one false reason for another.
      if (st.unreadable) {
        console.error('accounting: consent/connection state unreadable --', st.detail);
        res.status(502).json({ error: { code: 'STATE_UNREADABLE', message: 'Could not read the consent and connection records, so no connection status is being reported. This is not a statement that consent is absent.' } });
        return;
      }
      if (!st.provisioned) {
        res.status(200).json({ ok: true, provisioned: false,
          message: 'The accounting connector tables are not set up — run sql/accounting_connector_schema.sql in Supabase first.' });
        return;
      }
      const consentShape = st.live ? Object.assign({}, st.live, { scopes: Array.isArray(st.live.scopes) ? st.live.scopes : [] }) : null;
      const state = connector.connectionState({
        today: today,
        consent: consentShape,
        connection: st.conn ? {
          status: st.conn.status, realm_id: st.conn.realm_id, provider: st.conn.provider,
          expires_on: st.conn.expires_on,
          // The engine is told WHETHER a refresh token exists, never the token
          // itself. Ciphertext has no business leaving the database row.
          refresh_token_present: !!st.conn.refresh_token_enc
        } : null
      });
      const v = vault.vaultStatus();
      res.status(200).json({
        ok: true, provisioned: true, provider: provider,
        connection: state.ok ? state : null,
        connection_error: state.ok ? null : state.error,
        consent: consentShape ? {
          consent_id: consentShape.consent_id, granted_by: consentShape.granted_by,
          granted_on: consentShape.granted_on, scopes: consentShape.scopes
        } : null,
        consent_history: (st.consents || []).length,
        // Environment readiness, reported as three independent facts rather
        // than one "ready" boolean that hides which piece is missing.
        environment: {
          token_vault_usable: v.usable,
          token_vault_reason: v.usable ? null : v.reason,
          provider_credentials_configured: providerConfigured(),
          oauth_available: false,
          oauth_reason: providerConfigured()
            ? 'Credentials are present but the OAuth leg has never been exercised against Intuit and is not enabled.'
            : 'No Intuit application is registered: QB_CLIENT_ID, QB_CLIENT_SECRET and QB_REDIRECT_URI are not set.'
        },
        scopes_available: connector.SCOPES,
        readable_entities: connector.READABLE_ENTITIES
      });
      return;
    }

    // ── CONSENT ───────────────────────────────────────────────────────────
    // The only way a connection can ever come to exist. granted_by comes from
    // the VERIFIED session, never from the request body: a consent naming
    // whoever the caller typed is not evidence of anything.
    if (action === 'consent') {
      const consentId = String(payload.consent_id || '').trim();
      const scopes = Array.isArray(payload.scopes) ? payload.scopes : [];
      if (!consentId || !IDENT_RE.test(consentId) || consentId.length > MAX_ID_LEN) {
        res.status(400).json({ error: { message: 'payload.consent_id is required and must be a short identifier' } });
        return;
      }
      // Validated BEFORE anything is written, so an unusable consent never
      // reaches the table and cannot later be mistaken for a real grant.
      const check = connector.validateConsent({
        today: today,
        consent: { provider: provider, granted_by: session.employee_id, granted_on: today, scopes: scopes }
      });
      if (!check.ok) { res.status(400).json({ error: check.error }); return; }
      if (!check.usable) {
        res.status(400).json({ error: { code: 'INVALID_CONSENT', message: 'Not recorded: ' + check.reasons.join('; '), reasons: check.reasons } });
        return;
      }
      const w = await fetch(rest('accounting_consents?on_conflict=license_hash,consent_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({
          license_hash: licHash, consent_id: consentId, provider: provider,
          granted_by: session.employee_id, granted_on: today,
          scopes: check.scopes,
          consent_text: typeof payload.consent_text === 'string' ? payload.consent_text.slice(0, 16000) : null,
          ip: (req.headers['x-forwarded-for'] || '').split(',')[0].trim() || null,
          user_agent: String(req.headers['user-agent'] || '').slice(0, 512) || null,
          updated_at: new Date().toISOString()
        })
      });
      const saved = await w.json();
      if (!w.ok) {
        if (w.status === 404 || w.status === 400) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'The accounting connector tables are not set up — run sql/accounting_connector_schema.sql in Supabase first.' } }); return; }
        res.status(502).json({ error: { message: 'Data store rejected the consent' } });
        return;
      }
      // Recording consent does NOT connect anything, and the response says so
      // in the same breath rather than leaving a UI to imply otherwise.
      res.status(200).json({
        ok: true, data: Array.isArray(saved) ? saved[0] : saved,
        entities_this_permits: check.entities,
        connected: false,
        next: 'Consent recorded. Nothing is connected yet and no data has been read. The connection step is not available: ' +
          (providerConfigured() ? 'the OAuth leg has never been exercised against Intuit.' : 'no Intuit application is registered.')
      });
      return;
    }

    // ── REVOKE ────────────────────────────────────────────────────────────
    if (action === 'revoke') {
      const consentId = String(payload.consent_id || '').trim();
      if (!consentId) { res.status(400).json({ error: { message: 'payload.consent_id is required' } }); return; }
      const w = await fetch(rest('accounting_consents?license_hash=eq.' + enc(licHash) + '&consent_id=eq.' + enc(consentId)), {
        method: 'PATCH',
        headers: Object.assign({}, headers, { Prefer: 'return=representation' }),
        body: JSON.stringify({ revoked_on: today, revoked_by: session.employee_id, updated_at: new Date().toISOString() })
      });
      const saved = await w.json();
      if (!w.ok) { res.status(502).json({ error: { message: 'Data store rejected the revocation' } }); return; }
      if (!Array.isArray(saved) || !saved.length) { res.status(404).json({ error: { code: 'NO_CONSENT', message: 'No consent with that id on this licence' } }); return; }
      // The connection is marked revoked in the same breath. A token whose
      // consent is gone must not sit in a row still saying 'connected' --
      // the engine would refuse to use it, but the row would read as fine to
      // anybody looking at the table.
      await fetch(rest('accounting_connections?license_hash=eq.' + enc(licHash) + '&provider=eq.' + enc(provider)), {
        method: 'PATCH', headers: headers,
        body: JSON.stringify({ status: 'revoked', access_token_enc: null, refresh_token_enc: null, updated_at: new Date().toISOString() })
      });
      res.status(200).json({ ok: true, data: saved[0], tokens_discarded: true });
      return;
    }

    // ── READ ──────────────────────────────────────────────────────────────
    // The gate runs FIRST and in full, before anything about the provider is
    // considered. So a caller learns "you are not permitted to read that"
    // rather than "the integration is not configured", which are different
    // answers and only one of them is about them.
    if (action === 'read') {
      const st = await loadState();
      // `unreadable` must be checked BEFORE `provisioned`: an unreadable state
      // has no `provisioned` field, so falling through would report "the tables
      // are not set up" -- swapping one false reason for another.
      if (st.unreadable) {
        console.error('accounting: consent/connection state unreadable --', st.detail);
        res.status(502).json({ error: { code: 'STATE_UNREADABLE', message: 'Could not read the consent and connection records, so no connection status is being reported. This is not a statement that consent is absent.' } });
        return;
      }
      if (!st.provisioned) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'The accounting connector tables are not set up.' } }); return; }
      const gate = connector.authoriseRead({
        today: today,
        consent: st.live ? Object.assign({}, st.live, { scopes: Array.isArray(st.live.scopes) ? st.live.scopes : [] }) : null,
        entity: String(payload.entity || ''),
        method: String(payload.method || 'GET')
      });
      if (!gate.ok) { res.status(400).json({ error: gate.error }); return; }
      if (!gate.allowed) {
        res.status(403).json({ error: { code: 'NOT_PERMITTED', message: 'Refused: ' + gate.reasons.join('; '), reasons: gate.reasons } });
        return;
      }
      // Permitted, and STILL not possible. Reported as 501 with the real
      // reason rather than an empty success. An endpoint that returned
      // { ok: true, data: [] } here would be indistinguishable from a customer
      // whose books are empty, and that is the lie this rebuild exists to end.
      res.status(501).json({
        error: {
          code: 'OAUTH_NOT_AVAILABLE',
          message: 'This read is permitted by your consent, but no data can be fetched: ' +
            (providerConfigured()
              ? 'the OAuth leg has never been exercised against Intuit and is not enabled.'
              : 'no Intuit application is registered (QB_CLIENT_ID, QB_CLIENT_SECRET, QB_REDIRECT_URI are unset).'),
          permitted: true,
          entity: gate.entity
        }
      });
      return;
    }

    // ── THE OAUTH LEG ─────────────────────────────────────────────────────
    // Named explicitly so the 501 is about these actions rather than falling
    // into a generic "unknown action" that hides which part is missing.
    if (action === 'authorize_url' || action === 'callback' || action === 'refresh') {
      res.status(501).json({
        error: {
          code: 'OAUTH_NOT_IMPLEMENTED',
          message: 'The OAuth leg is not built and is not simulated. ' +
            (providerConfigured()
              ? 'Credentials are present, but no token exchange has ever been performed against Intuit.'
              : 'No Intuit application is registered: QB_CLIENT_ID, QB_CLIENT_SECRET and QB_REDIRECT_URI are unset.'),
          needs: providerConfigured() ? ['an exercised and verified token exchange'] : ['an Intuit application', 'QB_CLIENT_ID', 'QB_CLIENT_SECRET', 'QB_REDIRECT_URI']
        }
      });
      return;
    }

    res.status(400).json({ error: { message: 'Unknown action: ' + action } });
  } catch (e) {
    console.error('accounting endpoint error:', e && e.message);
    res.status(500).json({ error: { message: 'Server error — try again' } });
  }
};
