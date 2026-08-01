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
//   Persists one row to Supabase `bridge_pushes`
//   (sql/bridge_schema.sql -- MUST be run once in the Supabase SQL editor
//   before this action will work; same manual-migration convention already
//   used by sql/agent_schema.sql). If the table doesn't exist yet, this
//   returns a clear 503 naming the migration file instead of a generic 500.
//   Response: { ok:true, written:1, id }
//
// ACTION: pull  (symmetric read side -- no live caller yet, added for
//   completeness since this was speced as a "push/pull" action)
//   GET /api/bridge?action=pull&shopId=X[&limit=20]
//   Response: { ok:true, data:[ {shop_id,jobs,invoices,employees,created_at}, ... ] }
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
  const row = {
    shop_id: String(shopId),
    jobs: body.jobs || null,
    invoices: body.invoices || null,
    employees: body.employees || null
  };
  const bytes = Buffer.byteLength(JSON.stringify(row), 'utf8');
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
    const r = await fetch(SUPABASE_URL + '/rest/v1/bridge_pushes', {
      method: 'POST',
      headers: {
        apikey: SERVICE_KEY,
        Authorization: 'Bearer ' + SERVICE_KEY,
        'Content-Type': 'application/json',
        Prefer: 'return=representation'
      },
      body: JSON.stringify(row)
    });
    const out = await r.json().catch(function () { return null; });
    if (!r.ok) {
      // 42P01 = raw Postgres "undefined_table". PGRST205 = PostgREST's own
      // "table not in schema cache" code, which is what a genuinely missing
      // table actually returns in practice (confirmed live 2026-07-31 —
      // 42P01 alone never matched, so this fell through to a misleading
      // generic 502 instead of the actionable message below). Check both.
      const code = out && out.code;
      if (code === '42P01' || code === 'PGRST205') {
        res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Bridge storage not yet provisioned — run sql/bridge_schema.sql in the Supabase SQL editor' } });
        return;
      }
      console.error('bridge push upstream error:', out);
      res.status(502).json({ error: { message: 'Data store error — try again' } });
      return;
    }
    const written = Array.isArray(out) ? out[0] : out;
    res.status(200).json({ ok: true, written: 1, id: written && written.id });
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
  const rawLimit = parseInt(getQueryParam(req, 'limit') || '20', 10);
  const limit = Math.min(Math.max(rawLimit || 20, 1), 100);

  const SUPABASE_URL = process.env.SUPABASE_URL;
  const SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!SUPABASE_URL || !SERVICE_KEY) {
    console.error('SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set in environment variables');
    res.status(500).json({ error: { message: 'Server configuration error — contact support' } });
    return;
  }

  try {
    const url = SUPABASE_URL + '/rest/v1/bridge_pushes?shop_id=eq.' + encodeURIComponent(shopId) +
      '&select=shop_id,jobs,invoices,employees,created_at&order=created_at.desc&limit=' + limit;
    const r = await fetch(url, {
      headers: { apikey: SERVICE_KEY, Authorization: 'Bearer ' + SERVICE_KEY }
    });
    const rows = await r.json().catch(function () { return null; });
    if (!r.ok) {
      const code = rows && rows.code;
      if (code === '42P01' || code === 'PGRST205') {
        res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Bridge storage not yet provisioned — run sql/bridge_schema.sql in the Supabase SQL editor' } });
        return;
      }
      console.error('bridge pull upstream error:', rows);
      res.status(502).json({ error: { message: 'Data store error — try again' } });
      return;
    }
    res.status(200).json({ ok: true, data: rows || [] });
  } catch (err) {
    console.error('bridge pull error:', err);
    res.status(502).json({ error: { message: 'Upstream connection error — try again' } });
  }
}
