// api/sc-credentials.js
// ---------------------------------------------------------------------------
// SAIRNcode "bring your own credential" management endpoint.
//
// Stores a practice's OWN third-party service credentials (currently: their
// Stedi clearinghouse API key) encrypted at rest, scoped to their license.
// Used by api/sc-eligibility.js, and later by the prior-auth and code-data-
// licensing integrations -- one credential layer, three consumers.
//
// THE LOAD-BEARING RULE OF THIS FILE: a stored secret is NEVER returned to
// any client, for any role, by any action. 'status' returns presence
// metadata plus a last-4 fingerprint and nothing else -- not the plaintext,
// not the ciphertext. If a future action needs to return a secret, that is a
// design error, not a missing feature: the only code that should ever see a
// decrypted value is a server-side proxy making one outbound call with it
// (see api/sc-eligibility.js's loadServiceKey).
//
// WHY BYO RATHER THAN ONE SHARED SAIRN ACCOUNT (decided 2026-08-20): a
// 270/271 eligibility request carries real patient identifiers. A single
// SAIRN-owned clearinghouse account would make SAIRN the business associate
// for every practice's PHI traffic. Each practice using its own account
// keeps that relationship, and its BAA, between the practice and the
// clearinghouse -- where it already exists today.
//
// Note this is genuinely NEW infrastructure, not a pattern already in use
// here: verified 2026-08-20, every other third-party key on this platform
// (COURTLISTENER_API_TOKEN included, despite often being described as
// bring-your-own) is a single platform-wide Vercel env var.
//
// Three actions, all POST, license key via Authorization: Bearer, employee
// session token via X-SD-Auth:
//
//   action: 'status'  {}
//     Which credentials are configured. Metadata only, never a secret.
//     Any authenticated SAIRNcode role -- a coder needs to know whether
//     eligibility is available before trying to use it.
//
//   action: 'set'     { service, value }
//     Encrypts and stores. ADMIN ONLY.
//
//   action: 'clear'   { service }
//     Removes a stored credential. ADMIN ONLY.
//
// REQUIRES env: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, SD_AUTH_SECRET
// REQUIRES sql/sairncode_credentials_schema.sql to have been run.
// ---------------------------------------------------------------------------

const { validateLicenseKey } = require('./_lib/license');
const { verifySessionToken, tokenFromRequest, encryptSecret } = require('./_lib/auth');

const APP = 'sairncode';
const TABLE = 'sc_credentials';
const CREDENTIAL_ID = 'default';

// Services a practice may store a credential for. An explicit allowlist so a
// caller cannot write arbitrary keys into the blob -- same discipline as
// api/claude.js's server-tool type allowlist.
const ALLOWED_SERVICES = { stedi: true };

// Max plaintext length accepted for any single credential. Real API keys are
// well under this; the cap stops a caller from using this table as general
// storage and keeps the encrypted row inside the 64KB CHECK constraint.
const MAX_CREDENTIAL_LENGTH = 4096;

function upstream(res, detail) {
  console.error('sc-credentials upstream error:', detail);
  res.status(502).json({ error: { message: 'Data store error — try again' } });
}

// Presence metadata only. Deliberately returns a last-4 fingerprint (enough
// for an admin to confirm WHICH key is stored without revealing it) and the
// timestamp -- never the value, never the ciphertext, for any role.
function publicStatus(data) {
  const out = {};
  Object.keys(ALLOWED_SERVICES).forEach(function (svc) {
    const rec = data && data[svc];
    out[svc] = rec && rec.enc
      ? { configured: true, last4: rec.last4 || null, updated_at: rec.updated_at || null }
      : { configured: false, last4: null, updated_at: null };
  });
  return out;
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
  if (['status', 'set', 'clear'].indexOf(action) === -1) {
    res.status(400).json({ error: { message: "action must be 'status', 'set', or 'clear'" } });
    return;
  }

  const SUPABASE_URL = process.env.SUPABASE_URL;
  const SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!SUPABASE_URL || !SERVICE_KEY || !process.env.SD_AUTH_SECRET) {
    console.error('sc-credentials: SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY / SD_AUTH_SECRET not set');
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

  // Real per-employee session required for every action -- a valid license
  // key alone is not enough to read or write credential state. expectedApp
  // pins the token to SAIRNcode so a token minted by another SAIRN app on
  // the same license cannot be replayed here (Check 28 discipline).
  const caller = verifySessionToken(tokenFromRequest(req), licHash, APP);
  if (!caller) {
    res.status(401).json({ error: { code: 'NO_SESSION', message: 'A valid employee session is required' } });
    return;
  }

  const headers = { apikey: SERVICE_KEY, Authorization: 'Bearer ' + SERVICE_KEY, 'Content-Type': 'application/json' };
  const rest = (path) => SUPABASE_URL + '/rest/v1/' + path;
  const enc = encodeURIComponent;

  try {
    const readR = await fetch(rest(TABLE + '?license_hash=eq.' + enc(licHash) + '&credential_id=eq.' + enc(CREDENTIAL_ID) + '&select=data'), { headers });
    if (readR.status === 404 || readR.status === 400) {
      res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Credential storage is not set up yet -- run sql/sairncode_credentials_schema.sql in Supabase first.' } });
      return;
    }
    const readRows = await readR.json();
    if (!readR.ok) return upstream(res, readRows);
    const current = (Array.isArray(readRows) && readRows[0] && readRows[0].data) || {};

    if (action === 'status') {
      res.status(200).json({ ok: true, credentials: publicStatus(current) });
      return;
    }

    // ── set / clear: admin only, re-verified server-side ──
    // Matches the SC_RESOURCES delete gate in api/sd-data.js -- the client's
    // own role check is a UI convenience, never the real boundary.
    if (caller.role !== 'admin') {
      res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only Compliance Admin can change service credentials' } });
      return;
    }

    const service = String((body.service || '')).trim().toLowerCase();
    if (!ALLOWED_SERVICES[service]) {
      res.status(400).json({ error: { message: 'service must be one of: ' + Object.keys(ALLOWED_SERVICES).join(', ') } });
      return;
    }

    const next = Object.assign({}, current);

    if (action === 'set') {
      const value = String(body.value == null ? '' : body.value).trim();
      if (!value) { res.status(400).json({ error: { message: 'value is required' } }); return; }
      if (value.length > MAX_CREDENTIAL_LENGTH) {
        res.status(400).json({ error: { message: 'value exceeds ' + MAX_CREDENTIAL_LENGTH + ' characters' } });
        return;
      }
      next[service] = {
        enc: encryptSecret(value),
        last4: value.slice(-4),
        updated_at: new Date().toISOString(),
        updated_by: caller.employee_id
      };
    } else {
      delete next[service];
    }

    const writeR = await fetch(rest(TABLE + '?on_conflict=license_hash,credential_id'), {
      method: 'POST',
      headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
      body: JSON.stringify({
        license_hash: licHash,
        app_id: APP,
        credential_id: CREDENTIAL_ID,
        data: next,
        updated_at: new Date().toISOString()
      })
    });
    if (writeR.status === 404 || writeR.status === 400) {
      res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Credential storage is not set up yet -- run sql/sairncode_credentials_schema.sql in Supabase first.' } });
      return;
    }
    const writeRows = await writeR.json();
    if (!writeR.ok) return upstream(res, writeRows);

    // Deliberately re-derives from `next` rather than echoing the stored row
    // -- publicStatus is the only shape that ever leaves this endpoint.
    res.status(200).json({ ok: true, credentials: publicStatus(next) });
  } catch (err) {
    console.error('sc-credentials error:', err && err.message);
    res.status(500).json({ error: { message: 'Unexpected server error' } });
  }
};
