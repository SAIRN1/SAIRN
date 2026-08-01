// api/bridge.js
// ---------------------------------------------------------------------------
// SAIRN Bridge -- action-routed cross-app relay. Built 2026-07-31 to replace
// a URL every caller already assumed existed but never did (confirmed live
// 404 -- no api/bridge.js was ever committed; Guardian's "Bridge rule"
// pointed at a dead endpoint). Serves the two REAL, currently-live call
// shapes found in stonedesk.html and sairnbuild.html.
//
// Deliberately does NOT implement sairn-mobile-sync's documented
// event-envelope contract (app_id/event_type/source_device/timestamp/
// payload) -- nothing calls that shape today. That spec stays a known-
// unimplemented item for a separate conversation, not built speculatively
// here alongside two unrelated, already-live shapes.
//
// ACTION: proxy_get  (StoneDesk + SAIRNbuild Market Intelligence)
//   POST body: { source_app, target_app, data_type:'proxy_get', payload:{url} }
//   (no ?action= in the URL for this one -- both live callers signal it via
//   data_type in the body, so that's what's matched on.)
//   Relays a GET to an ALLOWLISTED external host only. This exists to dodge
//   FRED/homebuyer.com's missing CORS headers, not to hide a secret (FRED's
//   key is already public in the client HTML). An open URL relay would be an
//   SSRF vector, so the allowlist is a hard gate, not a suggestion -- any
//   other host is refused with 400.
//   Response: { ok:true, result: <parsed JSON, or {text:...} if not JSON> }
//
// ACTION: push  (StoneDesk's syncToSAIRNBridge + Field Map/Check-Register)
//   POST /api/bridge?action=push
//   Body: { shopId, jobs?, invoices?, employees? } -- exactly what the two
//   live callers already send. Neither sends an Authorization header, so
//   this does not require a license key -- adding that requirement would
//   just trade a 404 for a 401, not fix anything live.
//
//   UPSERTS one row into the pre-existing `bridge_data` table
//   (shop_id text primary key, data jsonb, updated_at timestamptz -- already
//   provisioned in Supabase, confirmed empty/unused by any code before this
//   change; NOT the `bridge_pushes` append-log table this file used
//   originally, which was scrapped 2026-08-01 in favor of reusing bridge_data
//   rather than standing up duplicate infra). {jobs,invoices,employees} is
//   stored together as the `data` blob, same shape convention as
//   api/sd-data.js's business_profiles.data. shop_id is the natural upsert
//   key (?on_conflict=shop_id, Prefer: resolution=merge-duplicates) -- each
//   live caller sends a full current-state snapshot on every call, not a
//   discrete event, so "latest wins" is the correct model here, not an
//   append-only log.
//   Response: { ok:true, written:1, shopId }
//
// ACTION: pull  (symmetric read side -- no live caller yet, added for
//   completeness since this was speced as a "push/pull" action)
//   GET /api/bridge?action=pull&shopId=X
//   Response: { ok:true, data: {jobs,invoices,employees,shop_id,updated_at} | null }
//
// REQUIRES env: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY (push/pull only --
// proxy_get needs neither).
// ---------------------------------------------------------------------------

const ALLOWED_PROXY_HOSTS = ['api.stlouisfed.org', 'homebuyer.com'];
const MAX_PUSH_BYTES = 64 * 1024; // matches api/sd-data.js's write cap

// req.query is populated by Vercel's Node runtime, but this endpoint has no
// prior usage in this codebase to confirm that against -- every existing
// api/*.js handler takes params from the body, not the query string. Parse
// req.url as a fallback so a real ?action=push/pull request never silently
// falls through to the wrong branch if req.query is ever unpopulated.
function getQueryParam(req, name) {
  if (req.query && req.query[name] !== undefined) return req.query[name];
  try {
    const u = new URL(req.url, 'https://sairn.vercel.app');
    return u.searchParams.get(name);
  } catch (e) { return null; }
}

module.exports = async (req, res) => {
  const action = getQueryParam(req, 'action');

  if (req.method === 'GET') {
    if (action === 'pull') return handlePull(req, res);
    res.status(405).json({ error: { message: 'GET only supports ?action=pull' } });
    return;
  }
  if (req.method !== 'POST') {
    res.status(405).json({ error: { message: 'Method not allowed' } });
    return;
  }

  let body = req.body;
  if (typeof body === 'string') {
    try { body = JSON.parse(body); } catch (e) { body = {}; }
  }
  body = body || {};

  // proxy_get is signaled via body.data_type, not ?action= -- match the
  // actual live callers rather than requiring them to change.
  if (action === 'proxy_get' || body.data_type === 'proxy_get') {
    return handleProxyGet(body, res);
  }
  return handlePush(body, res);
};

async function handleProxyGet(body, res) {
  const url = body.payload && body.payload.url;
  if (!url || typeof url !== 'string') {
    res.status(400).json({ error: { message: 'payload.url is required for proxy_get' } });
    return;
  }
  let parsed;
  try { parsed = new URL(url); } catch (e) {
    res.status(400).json({ error: { message: 'payload.url is not a valid URL' } });
    return;
  }
  if (parsed.protocol !== 'https:' || !ALLOWED_PROXY_HOSTS.includes(parsed.hostname)) {
    res.status(400).json({ error: { message: 'Host not allowed for proxy_get. Allowed: ' + ALLOWED_PROXY_HOSTS.join(', ') } });
    return;
  }
  try {
    const r = await fetch(parsed.toString(), { method: 'GET' });
    const text = await r.text();
    let data;
    try { data = JSON.parse(text); } catch (e) { data = { text: text }; }
    if (!r.ok) {
      res.status(502).json({ error: { message: 'Upstream (' + parsed.hostname + ') returned ' + r.status } });
      return;
    }
    res.status(200).json({ ok: true, result: data });
  } catch (err) {
    console.error('bridge proxy_get error:', err);
    res.status(502).json({ error: { message: 'Upstream connection error — try again' } });
  }
}

async function handlePush(body, res) {
  const shopId = body.shopId;
  if (!shopId) {
    res.status(400).json({ error: { message: 'shopId is required' } });
    return;
  }
  const data = {
    jobs: body.jobs || null,
    invoices: body.invoices || null,
    employees: body.employees || null
  };
  const bytes = Buffer.byteLength(JSON.stringify(data), 'utf8');
  if (bytes > MAX_PUSH_BYTES) {
    res.status(413).json({ error: { code: 'PAYLOAD_TOO_LARGE', message: 'Payload is ' + bytes + ' bytes; the limit is ' + MAX_PUSH_BYTES + ' (64KB)' } });
    return;
  }

  const SUPABASE_URL = process.env.SUPABASE_URL;
  const SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!SUPABASE_URL || !SERVICE_KEY) {
    console.error('SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set in environment variables');
    res.status(500).json({ error: { message: 'Server configuration error — contact support' } });
    return;
  }

  try {
    // Upsert on shop_id (its primary key) -- same merge-duplicates pattern
    // api/sd-data.js already uses for business_profiles. Each live caller
    // sends a full current-state snapshot every time, so "latest wins" here
    // is correct, not a data-loss shortcut.
    const r = await fetch(SUPABASE_URL + '/rest/v1/bridge_data?on_conflict=shop_id', {
      method: 'POST',
      headers: {
        apikey: SERVICE_KEY,
        Authorization: 'Bearer ' + SERVICE_KEY,
        'Content-Type': 'application/json',
        Prefer: 'resolution=merge-duplicates,return=representation'
      },
      body: JSON.stringify({ shop_id: String(shopId), data: data, updated_at: new Date().toISOString() })
    });
    const out = await r.json().catch(function () { return null; });
    if (!r.ok) {
      // bridge_data already exists in Supabase (confirmed 2026-08-01), so
      // this branch shouldn't fire in normal operation -- kept as a guard
      // in case the table is ever renamed/dropped, so that failure mode
      // stays self-diagnosing instead of a bare 502.
      const code = out && out.code;
      if (code === '42P01' || code === 'PGRST205') {
        res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'bridge_data table not found in Supabase — check the schema' } });
        return;
      }
      // 42501 = Postgres permission_denied. Hit live 2026-08-01 even with
      // the correct schema/query: service_role itself has no GRANT on
      // bridge_data (unusual -- Supabase normally auto-grants service_role
      // full access). Surfacing Postgres's own fix hint verbatim rather
      // than a generic 502 -- this is a Supabase-side GRANT, not something
      // fixable from this file.
      if (code === '42501') {
        res.status(503).json({ error: { code: 'PERMISSION_DENIED', message: (out && out.hint) || 'service_role lacks privileges on bridge_data — run the GRANT Postgres suggests in the Supabase SQL editor' } });
        return;
      }
      console.error('bridge push upstream error:', out);
      res.status(502).json({ error: { message: 'Data store error — try again' } });
      return;
    }
    const written = Array.isArray(out) ? out[0] : out;
    res.status(200).json({ ok: true, written: 1, shopId: written && written.shop_id });
  } catch (err) {
    console.error('bridge push error:', err);
    res.status(502).json({ error: { message: 'Upstream connection error — try again' } });
  }
}

async function handlePull(req, res) {
  const shopId = getQueryParam(req, 'shopId');
  if (!shopId) {
    res.status(400).json({ error: { message: 'shopId query param is required' } });
    return;
  }

  const SUPABASE_URL = process.env.SUPABASE_URL;
  const SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!SUPABASE_URL || !SERVICE_KEY) {
    console.error('SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set in environment variables');
    res.status(500).json({ error: { message: 'Server configuration error — contact support' } });
    return;
  }

  try {
    const url = SUPABASE_URL + '/rest/v1/bridge_data?shop_id=eq.' + encodeURIComponent(shopId) +
      '&select=shop_id,data,updated_at&limit=1';
    const r = await fetch(url, {
      headers: { apikey: SERVICE_KEY, Authorization: 'Bearer ' + SERVICE_KEY }
    });
    const rows = await r.json().catch(function () { return null; });
    if (!r.ok) {
      const code = rows && rows.code;
      if (code === '42P01' || code === 'PGRST205') {
        res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'bridge_data table not found in Supabase — check the schema' } });
        return;
      }
      if (code === '42501') {
        res.status(503).json({ error: { code: 'PERMISSION_DENIED', message: (rows && rows.hint) || 'service_role lacks privileges on bridge_data — run the GRANT Postgres suggests in the Supabase SQL editor' } });
        return;
      }
      console.error('bridge pull upstream error:', rows);
      res.status(502).json({ error: { message: 'Data store error — try again' } });
      return;
    }
    const row = Array.isArray(rows) && rows[0];
    res.status(200).json({
      ok: true,
      data: row ? Object.assign({}, row.data, { shop_id: row.shop_id, updated_at: row.updated_at }) : null
    });
  } catch (err) {
    console.error('bridge pull error:', err);
    res.status(502).json({ error: { message: 'Upstream connection error — try again' } });
  }
}
