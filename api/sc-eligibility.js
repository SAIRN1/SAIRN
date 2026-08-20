// api/sc-eligibility.js
// ---------------------------------------------------------------------------
// SAIRNcode real-time eligibility verification (X12 270/271) proxy.
//
// Calls Stedi -- the practice's OWN Stedi account, using the API key they
// stored through api/sc-credentials.js. SAIRN never holds a clearinghouse
// account on their behalf (see that file's header for the BAA reasoning).
//
// LIVE-RESEARCHED API SHAPES (2026-08-20, from Stedi's own docs -- not
// guessed, and not answered from training data, which predates them):
//   Eligibility check:
//     POST https://healthcare.us.stedi.com/2024-04-01/change/medicalnetwork/eligibility/v3
//     Required body: tradingPartnerServiceId, provider, subscriber
//     (encounter optional but effectively needed for a useful answer).
//     Response: benefitsInformation[], planStatus[], planDateInformation,
//     benefitsRelatedEntities, errors[].
//   Payer search:
//     GET https://healthcare.us.stedi.com/2024-04-01/payers/search?query=...
//     Response: items[] (each with payer + matches), nextPageToken, stats.
//   Auth for both: the raw API key in the Authorization header (NOT a
//   "Bearer " prefix -- Stedi takes the key directly).
//
// ANTI-FABRICATION CONTRACT, the whole point of this endpoint:
//   - If no credential is configured -> 503 NOT_CONFIGURED. Never a
//     simulated or sample result.
//   - If Stedi or the payer returns an error -> that REAL error text is
//     surfaced. Never swallowed, never replaced with a friendly "not
//     covered", never retried into a different-looking answer.
//   - This endpoint does not interpret coverage. It passes back what the
//     payer actually said, and the client renders only fields that are
//     genuinely present (see sairncode.html's renderEligibilityResult).
//     A missing field is shown as "payer returned no data", never as $0,
//     never as "covered".
//
// Two actions, both POST, license key via Authorization: Bearer, employee
// session token via X-SD-Auth:
//
//   action: 'check'        { payerId, provider:{...}, subscriber:{...}, encounter:{...} }
//   action: 'search_payer' { query }
//
// Any authenticated SAIRNcode role may run a check -- verifying a patient's
// coverage is core coder/biller work, not an admin-only action. Only storing
// the credential itself is admin-gated (api/sc-credentials.js).
//
// REQUIRES env: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, SD_AUTH_SECRET
// REQUIRES sql/sairncode_credentials_schema.sql to have been run.
// ---------------------------------------------------------------------------

const { validateLicenseKey } = require('./_lib/license');
const { verifySessionToken, tokenFromRequest, decryptSecret } = require('./_lib/auth');

const APP = 'sairncode';
const CREDENTIAL_TABLE = 'sc_credentials';
const CREDENTIAL_ID = 'default';

const STEDI_BASE = 'https://healthcare.us.stedi.com/2024-04-01';
const STEDI_ELIGIBILITY_URL = STEDI_BASE + '/change/medicalnetwork/eligibility/v3';
const STEDI_PAYER_SEARCH_URL = STEDI_BASE + '/payers/search';

// Stedi's own documented ceiling for the search query parameter.
const MAX_QUERY_LENGTH = 200;

// A real eligibility round trip goes browser -> here -> Stedi -> payer ->
// back. Payers are the slow link and some are genuinely slow; this ceiling
// exists so a hung payer surfaces as an honest timeout rather than leaving
// the caller waiting on a serverless function until the platform kills it.
const OUTBOUND_TIMEOUT_MS = 30000;

function upstream(res, detail) {
  console.error('sc-eligibility upstream error:', detail);
  res.status(502).json({ error: { message: 'Data store error — try again' } });
}

async function fetchWithTimeout(url, options) {
  const controller = new AbortController();
  const timer = setTimeout(function () { controller.abort(); }, OUTBOUND_TIMEOUT_MS);
  try {
    return await fetch(url, Object.assign({}, options, { signal: controller.signal }));
  } finally {
    clearTimeout(timer);
  }
}

module.exports = async (req, res) => {
  if (req.method !== 'POST') {
    res.status(405).json({ error: { message: 'Method not allowed — POST only' } });
    return;
  }

  const authz = req.headers['authorization'] || '';
  const licenseKey = authz.startsWith('Bearer ') ? authz.slice(7).trim() : null;
  if (!licenseKey) {
    res.status(401).json({ error: { code: 'NO_LICENSE', message: 'Missing bearer license key' } });
    return;
  }

  let body = req.body;
  if (typeof body === 'string') {
    try { body = JSON.parse(body); } catch (e) {
      res.status(400).json({ error: { message: 'Invalid JSON body' } });
      return;
    }
  }
  const action = body && body.action;
  if (['check', 'search_payer'].indexOf(action) === -1) {
    res.status(400).json({ error: { message: "action must be 'check' or 'search_payer'" } });
    return;
  }

  const SUPABASE_URL = process.env.SUPABASE_URL;
  const SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!SUPABASE_URL || !SERVICE_KEY || !process.env.SD_AUTH_SECRET) {
    console.error('sc-eligibility: SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY / SD_AUTH_SECRET not set');
    res.status(500).json({ error: { message: 'Server configuration error — contact support' } });
    return;
  }

  let lic;
  try {
    lic = await validateLicenseKey(licenseKey);
  } catch (err) {
    if (err.code === 'CONFIG') { res.status(500).json({ error: { message: 'Server configuration error — contact support' } }); return; }
    res.status(502).json({ error: { message: 'Upstream connection error — try again' } });
    return;
  }
  if (!lic.valid) { res.status(401).json({ error: { code: 'INVALID_LICENSE', message: 'Unknown license key' } }); return; }
  if (!lic.active) { res.status(403).json({ error: { code: 'LICENSE_INACTIVE', message: 'This license is not active' } }); return; }

  const licHash = lic.license_hash;
  const caller = verifySessionToken(tokenFromRequest(req), licHash, APP);
  if (!caller) {
    res.status(401).json({ error: { code: 'NO_SESSION', message: 'A valid employee session is required' } });
    return;
  }

  const headers = { apikey: SERVICE_KEY, Authorization: 'Bearer ' + SERVICE_KEY, 'Content-Type': 'application/json' };
  const rest = (path) => SUPABASE_URL + '/rest/v1/' + path;
  const enc = encodeURIComponent;

  // ── Load + decrypt the practice's own Stedi key ──
  // The ONLY place a decrypted credential exists is this local variable, for
  // the duration of one outbound call. It is never logged, never returned to
  // the client, and never written anywhere.
  let stediKey;
  try {
    const credR = await fetchWithTimeout(rest(CREDENTIAL_TABLE + '?license_hash=eq.' + enc(licHash) + '&credential_id=eq.' + enc(CREDENTIAL_ID) + '&select=data'), { headers });
    if (credR.status === 404 || credR.status === 400) {
      res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Credential storage is not set up yet -- run sql/sairncode_credentials_schema.sql in Supabase first.' } });
      return;
    }
    const credRows = await credR.json();
    if (!credR.ok) return upstream(res, credRows);
    const stored = (Array.isArray(credRows) && credRows[0] && credRows[0].data) || {};
    const rec = stored.stedi;
    if (!rec || !rec.enc) {
      res.status(503).json({
        error: {
          code: 'NOT_CONFIGURED',
          message: 'No Stedi API key is configured for this practice yet. A Compliance Admin can add one in Settings — create a free account at stedi.com, generate an API key, and paste it there. Eligibility checks (270/271) are billed at $0 by Stedi, but the account must be your practice’s own.'
        }
      });
      return;
    }
    stediKey = decryptSecret(rec.enc);
    if (!stediKey) {
      // Ciphertext present but undecryptable -- almost always SD_AUTH_SECRET
      // having changed since the credential was stored. Say that plainly
      // rather than reporting it as a Stedi or payer failure.
      console.error('sc-eligibility: stored Stedi credential failed to decrypt (SD_AUTH_SECRET rotated?)');
      res.status(503).json({ error: { code: 'CREDENTIAL_UNREADABLE', message: 'The stored Stedi API key could not be decrypted. It most likely needs to be re-entered by a Compliance Admin in Settings.' } });
      return;
    }
  } catch (err) {
    console.error('sc-eligibility credential load error:', err && err.message);
    res.status(502).json({ error: { message: 'Could not load service credentials — try again' } });
    return;
  }

  // ── Payer search ──
  if (action === 'search_payer') {
    const query = String((body.query || '')).trim();
    if (!query) { res.status(400).json({ error: { message: 'query is required' } }); return; }
    if (query.length > MAX_QUERY_LENGTH) { res.status(400).json({ error: { message: 'query exceeds ' + MAX_QUERY_LENGTH + ' characters' } }); return; }
    try {
      const r = await fetchWithTimeout(STEDI_PAYER_SEARCH_URL + '?query=' + enc(query) + '&eligibilityCheck=SUPPORTED&pageSize=10', {
        method: 'GET',
        headers: { Authorization: stediKey }
      });
      const data = await r.json().catch(function () { return null; });
      if (!r.ok) {
        // Surface Stedi's real message. Never substitute a generic
        // "no payers found" for what was actually an auth or quota error.
        res.status(502).json({ error: { code: 'STEDI_ERROR', message: 'Stedi payer search failed (HTTP ' + r.status + ')', detail: data || null } });
        return;
      }
      res.status(200).json({ ok: true, items: (data && data.items) || [], stats: (data && data.stats) || null });
    } catch (err) {
      const aborted = err && err.name === 'AbortError';
      console.error('sc-eligibility payer search error:', err && err.message);
      res.status(504).json({ error: { code: aborted ? 'TIMEOUT' : 'NETWORK', message: aborted ? 'Stedi payer search timed out' : 'Could not reach Stedi' } });
    }
    return;
  }

  // ── Real-time eligibility check (270/271) ──
  const payerId = String((body.payerId || '')).trim();
  const provider = body.provider || {};
  const subscriber = body.subscriber || {};
  const encounter = body.encounter || {};

  // Validate against Stedi's own documented minimums rather than sending a
  // request we already know is malformed and reporting the payer's rejection
  // as though it were a coverage answer.
  if (!payerId) { res.status(400).json({ error: { message: 'payerId (tradingPartnerServiceId) is required' } }); return; }
  if (!provider.npi && !provider.organizationName && !(provider.firstName && provider.lastName)) {
    res.status(400).json({ error: { message: 'provider requires an npi, an organizationName, or both firstName and lastName' } });
    return;
  }
  if (!subscriber.memberId && !subscriber.dateOfBirth && !subscriber.lastName) {
    res.status(400).json({ error: { message: 'subscriber requires at least one of memberId, dateOfBirth, or lastName' } });
    return;
  }

  const stediBody = {
    tradingPartnerServiceId: payerId,
    provider: provider,
    subscriber: subscriber
  };
  if (encounter && Object.keys(encounter).length) stediBody.encounter = encounter;

  try {
    const r = await fetchWithTimeout(STEDI_ELIGIBILITY_URL, {
      method: 'POST',
      headers: { Authorization: stediKey, 'Content-Type': 'application/json' },
      body: JSON.stringify(stediBody)
    });
    const data = await r.json().catch(function () { return null; });

    if (!r.ok) {
      res.status(502).json({
        error: {
          code: 'STEDI_ERROR',
          message: 'Eligibility check failed (HTTP ' + r.status + ')',
          detail: data || null
        }
      });
      return;
    }

    // A 200 from Stedi can still carry payer-level errors in errors[]. Pass
    // them through untouched -- the client shows them verbatim rather than
    // rendering a coverage answer that was never actually given.
    res.status(200).json({
      ok: true,
      benefitsInformation: (data && data.benefitsInformation) || null,
      planStatus: (data && data.planStatus) || null,
      planDateInformation: (data && data.planDateInformation) || null,
      benefitsRelatedEntities: (data && data.benefitsRelatedEntities) || null,
      subscriber: (data && data.subscriber) || null,
      errors: (data && data.errors) || null
    });
  } catch (err) {
    const aborted = err && err.name === 'AbortError';
    console.error('sc-eligibility check error:', err && err.message);
    res.status(504).json({
      error: {
        code: aborted ? 'TIMEOUT' : 'NETWORK',
        message: aborted
          ? 'The eligibility check timed out waiting for the payer. It was NOT completed — do not treat this as a coverage answer.'
          : 'Could not reach Stedi. The eligibility check was NOT completed.'
      }
    });
  }
};
