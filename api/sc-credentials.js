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
    // `updated_at` is selected because it is the concurrency token for the
    // conditional write below -- see the lost-update note there. Reading it
    // costs nothing and the status path ignores it.
    const readR = await fetch(rest(TABLE + '?license_hash=eq.' + enc(licHash) + '&credential_id=eq.' + enc(CREDENTIAL_ID) + '&select=data,updated_at'), { headers });
    if (readR.status === 404 || readR.status === 400) {
      res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Credential storage is not set up yet -- run sql/sairncode_credentials_schema.sql in Supabase first.' } });
      return;
    }
    const readRows = await readR.json();
    if (!readR.ok) return upstream(res, readRows);
    const currentRow = (Array.isArray(readRows) && readRows[0]) || null;
    const current = (currentRow && currentRow.data) || {};

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
    let nextEntry = null;

    if (action === 'set') {
      const value = String(body.value == null ? '' : body.value).trim();
      if (!value) { res.status(400).json({ error: { message: 'value is required' } }); return; }
      if (value.length > MAX_CREDENTIAL_LENGTH) {
        res.status(400).json({ error: { message: 'value exceeds ' + MAX_CREDENTIAL_LENGTH + ' characters' } });
        return;
      }
      // Held in its own binding so the conflict retry can re-apply exactly
      // this change to a freshly-read blob instead of re-sending a stale merge.
      nextEntry = {
        enc: encryptSecret(value),
        last4: value.slice(-4),
        updated_at: new Date().toISOString(),
        updated_by: caller.employee_id
      };
      next[service] = nextEntry;
    } else {
      delete next[service];
    }

    // ── LOST UPDATE, FIXED 2026-09-04 ──────────────────────────────────────
    // Every service credential for the practice lives in ONE jsonb blob keyed
    // (license_hash, credential_id='default'). This handler read that blob,
    // changed one service inside it, and upserted the WHOLE THING back with
    // resolution=merge-duplicates, which replaces `data` wholesale.
    //
    // Two admins configuring DIFFERENT services in the same window both read
    // the same `current`; each wrote current + their own service; the second
    // write silently dropped the first's credential. No error, nothing in the
    // UI, and the missing key only surfaces later as an eligibility check that
    // reports NOT_CONFIGURED for a service somebody knows they set up.
    //
    // Fixed with optimistic concurrency rather than a schema change: the write
    // is now conditional on the `updated_at` we actually read. PostgREST
    // returns the affected rows, so ZERO rows back means somebody else wrote
    // in between -- the row is still there, our precondition simply no longer
    // holds.
    //
    // ONE AUTOMATIC RETRY, AND ONLY ONE, because a retry here is genuinely
    // safe rather than a way of hiding the race: we re-read the blob and
    // re-apply the SAME single-service change to it. If the other admin
    // touched a different service, both survive, which is the correct outcome.
    // If they touched the SAME service, last-write-wins was always the answer.
    // A second conflict is reported as 409 rather than retried forever.
    async function writeBlob(blob, expectedUpdatedAt) {
      const stamp = new Date().toISOString();
      if (expectedUpdatedAt) {
        // Conditional UPDATE. The updated_at filter is the precondition.
        return fetch(rest(TABLE +
          '?license_hash=eq.' + enc(licHash) +
          '&credential_id=eq.' + enc(CREDENTIAL_ID) +
          '&updated_at=eq.' + enc(expectedUpdatedAt)), {
          method: 'PATCH',
          headers: Object.assign({}, headers, { Prefer: 'return=representation' }),
          body: JSON.stringify({ data: blob, updated_at: stamp })
        });
      }
      // No row existed when we read. A plain INSERT rather than an upsert, so
      // that a concurrent first-write loses the insert race LOUDLY (unique
      // violation) instead of silently overwriting the row that just landed.
      return fetch(rest(TABLE), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'return=representation' }),
        body: JSON.stringify({
          license_hash: licHash,
          app_id: APP,
          credential_id: CREDENTIAL_ID,
          data: blob,
          updated_at: stamp
        })
      });
    }

    // Applies this request's single change to whatever blob it is handed, so
    // the retry re-applies the change rather than re-sending a stale merge.
    function applyChange(base) {
      const out = Object.assign({}, base || {});
      if (action === 'set') { out[service] = nextEntry; } else { delete out[service]; }
      return out;
    }

    let writeR = await writeBlob(next, currentRow && currentRow.updated_at);
    let writeRows = null;

    if (writeR.ok || writeR.status === 409) {
      const firstRows = writeR.status === 409 ? null : await writeR.json().catch(function () { return null; });
      const noRowsMatched = writeR.status === 409 ||
        (Array.isArray(firstRows) && firstRows.length === 0);
      if (noRowsMatched) {
        console.warn('sc-credentials: concurrent write detected on ' + service + ' -- re-reading and retrying once');
        const reR = await fetch(rest(TABLE + '?license_hash=eq.' + enc(licHash) + '&credential_id=eq.' + enc(CREDENTIAL_ID) + '&select=data,updated_at'), { headers });
        const reRows = reR.ok ? await reR.json().catch(function () { return null; }) : null;
        const reRow = (Array.isArray(reRows) && reRows[0]) || null;
        if (!reRow) {
          res.status(409).json({ error: { code: 'WRITE_CONFLICT', message: 'Another administrator changed service credentials while this change was being saved, and the record could not be re-read. Nothing was saved -- reopen the panel and try again.' } });
          return;
        }
        writeR = await writeBlob(applyChange(reRow.data), reRow.updated_at);
        const secondRows = writeR.ok ? await writeR.json().catch(function () { return null; }) : null;
        if (!writeR.ok || (Array.isArray(secondRows) && secondRows.length === 0)) {
          res.status(409).json({ error: { code: 'WRITE_CONFLICT', message: 'Another administrator is changing service credentials right now. Nothing was saved -- reopen the panel and try again.' } });
          return;
        }
        // The retry succeeded against a blob we re-read, so the response must
        // describe THAT blob, not the stale `next` computed from the first read.
        const savedRow = Array.isArray(secondRows) ? secondRows[0] : null;
        res.status(200).json({ ok: true, credentials: publicStatus((savedRow && savedRow.data) || applyChange(reRow.data)), retried: true });
        return;
      }
      writeRows = firstRows;
    }

    if (writeR.status === 404 || writeR.status === 400) {
      res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Credential storage is not set up yet -- run sql/sairncode_credentials_schema.sql in Supabase first.' } });
      return;
    }
    if (writeRows === null) writeRows = await writeR.json().catch(function () { return null; });
    if (!writeR.ok) return upstream(res, writeRows);

    // Deliberately re-derives from `next` rather than echoing the stored row
    // -- publicStatus is the only shape that ever leaves this endpoint.
    res.status(200).json({ ok: true, credentials: publicStatus(next) });
  } catch (err) {
    console.error('sc-credentials error:', err && err.message);
    res.status(500).json({ error: { message: 'Unexpected server error' } });
  }
};
