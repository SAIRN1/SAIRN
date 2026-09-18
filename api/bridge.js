// api/bridge.js
// ---------------------------------------------------------------------------
// ⚠ NAMING: THIS IS NOT "THE SAIRN DATA BRIDGE" MOST APPS MEAN.
// Two different things carry that name. The real cross-app data path is
// api/sd-data.js's shared resources (employees, shared_knowledge, ...) --
// license-scoped, session-gated, used by 10 apps, and genuinely read by
// them. That is what SAIRNsenior and SAIRNcare shipped as "SAIRN Data
// Bridge integration". THIS file is a separate, StoneDesk-only endpoint.
// Guardian v2's Check 2 named this one by mistake until 2026-08-24; see its
// corrected entry. Use api/sd-data.js for new cross-app data.
//
// STATE OF THIS FILE'S THREE ACTIONS, audited live 2026-08-24:
//   proxy_get -- healthy, in real use by StoneDesk + SAIRNbuild.
//   push      -- one live caller (StoneDesk crSendToBridge). Two other
//                callers were dead code and were deleted that day.
//   pull      -- REMOVED 2026-09-17. Zero callers across all 13 app files,
//                and "correct and harmless" was wrong on the second half: it
//                served one tenant's stored jobs, invoices and employees to
//                an unauthenticated GET keyed on a RAW LICENCE KEY. The
//                natural read side is still worth building one day, and when
//                it is it should key on license_hash and require a session.
// So bridge_data is, today, written and never read.
//
// push NOW REQUIRES A LICENCE, CORRECTED 2026-09-17. This block used to read
// "NO AUTHORIZATION ON push, deliberately: anyone can write to any shop_id.
// Fine for shop metadata a shop pushes about itself; NOT fine for personal or
// financial data." THE BOUND IT DESCRIBED HAD ALREADY BEEN CROSSED -- StoneDesk's
// crSendToBridge pushes expense invoices with payee, amount, memo and a GL
// account, which is financial data by any reading. A rule that names its own
// limit and is not enforced does not hold the limit; it records that somebody
// once knew where it was.
//
// It now takes Authorization: Bearer <licence key>, validates it, and keys the
// row on the resulting license_hash. The body's shopId is accepted and IGNORED.
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
// ACTION: pull -- REMOVED 2026-09-17. It had zero callers and it was an
//   UNAUTHENTICATED read: `shopId` came from the query string, no
//   Authorization header was required, and `bridge_data.shop_id` is the
//   customer's RAW LICENCE KEY (stonedesk.html: `sdShopId()` returns
//   `sdLicenseKey()`), where everywhere else on this platform a licence is
//   hashed before it reaches a table. Anyone holding a licence key -- a string
//   customers do not treat as a password -- could read that shop's jobs,
//   invoices and employees. A GET now answers 405 NO_READ_SIDE.
//
// REQUIRES env: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY (push only --
// proxy_get needs neither).
// ---------------------------------------------------------------------------

const { validateLicenseKey } = require('./_lib/license');
const RESIL = require('./_lib/resilience.js');

// LOOSE ON PURPOSE. Nothing has been measured about these upstreams' real
// latency or size, and a tight number chosen from nothing trips on ordinary
// traffic and teaches its readers the guard is noise.
const MAX_PROXY_BYTES = 2 * 1024 * 1024;   // 2MB
const PROXY_TIMEOUT_MS = 10000;
const PROXY_BULKHEAD = 8;

let _proxyGuard = null;
function proxyGuard() {
  if (!_proxyGuard) {
    _proxyGuard = {
      bulkhead: RESIL.createBulkhead('bridge:proxy_get', PROXY_BULKHEAD),
      timeoutMs: PROXY_TIMEOUT_MS,
      key: 'bridge:proxy_get'
    };
  }
  return _proxyGuard;
}

const ALLOWED_PROXY_HOSTS = ['api.stlouisfed.org', 'homebuyer.com'];
const MAX_PUSH_BYTES = 64 * 1024; // matches api/sd-data.js's write cap

// req.query is populated by Vercel's Node runtime, but this endpoint has no
// prior usage in this codebase to confirm that against -- every existing
// api/*.js handler takes params from the body, not the query string. Parse
// req.url as a fallback so a real ?action=push request never silently
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

  // ── THE READ SIDE IS GONE (2026-09-17) ────────────────────────────────
  // `?action=pull` had ZERO callers -- three separate comments across
  // stonedesk.html and sairncash.html say so independently -- and it was not
  // merely dead. It took a `shopId` from the QUERY STRING with NO
  // Authorization header of any kind and returned that shop's stored jobs,
  // invoices and employees.
  //
  // AND THE KEY IS THE CUSTOMER'S RAW LICENCE. `sdShopId()` in stonedesk.html
  // is `return sdLicenseKey() || 'stonedesk-demo'`, so `bridge_data.shop_id`
  // is the licence key in plaintext -- while everywhere else on this platform
  // a licence is hashed before it reaches a table. A licence key is typed into
  // the app, lives in localStorage, and is the kind of string that ends up in
  // a support ticket or a screenshot. So this was an UNAUTHENTICATED CROSS-
  // TENANT READ OF ONE SHOP'S FINANCIAL DATA, reachable by anyone holding a
  // string the customer does not treat as a password.
  //
  // Removed rather than authenticated: nothing consumes it, so there is no
  // behaviour to preserve, and the fastest correct fix for a read path with no
  // reader is to not have it. Recoverable from git history if a real consumer
  // is ever designed -- and it should be designed against license_hash.
  if (req.method === 'GET') {
    res.status(405).json({ error: { code: 'NO_READ_SIDE', message:
      'This endpoint has no read action. ?action=pull was removed 2026-09-17: '
      + 'it had no callers and served one tenant data to an unauthenticated '
      + 'GET keyed on a raw licence key.' } });
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
  return handlePush(body, res, req);
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
    // THE ALLOWLIST IS NO LONGER ECHOED TO AN UNAUTHENTICATED CALLER.
    // proxy_get deliberately requires no licence, so every message it returns
    // is pre-auth -- and until 2026-09-17 `push` had no auth either, so this
    // file had no authenticated surface for tools/preauth_oracle_check.py to
    // measure against. Adding one made this line visible as what it always
    // was: an unauthenticated enumeration of the allowlist.
    //
    // THE LIST IS PUBLIC ANYWAY -- this repository is public and the constant
    // is three lines up -- which is exactly the argument that would erode the
    // rule if it were accepted. It costs nothing to log it instead, so it is
    // logged instead.
    console.error('bridge proxy_get: host not allowed: ' + parsed.hostname
      + '. Allowed: ' + ALLOWED_PROXY_HOSTS.join(', '));
    res.status(400).json({ error: { message: 'Host not allowed for proxy_get' } });
    return;
  }
  // ── THE PARSE IS ISOLATED BEFORE IT IS TRUSTED (2026-09-17) ───────────
  // This is the platform's most exposed untrusted-input path: ANY caller can
  // reach it with no licence, it fetches a third party, and it parsed whatever
  // came back with `await r.text()` then `JSON.parse` -- unbounded in SIZE and
  // unbounded in TIME.
  //
  // THE ALLOWLIST IS NOT THE ISOLATION. It bounds WHO answers, not what they
  // say or how long they take. A slow or enormous response from an
  // allowlisted host is the same failure as a hostile one, and neither needs
  // the host to be compromised -- api.stlouisfed.org having a bad afternoon is
  // enough.
  //
  // THREE BOUNDS, and they are different failures:
  //   TIMEOUT   the function is not held until Vercel's own limit
  //   SIZE      the body cannot exhaust the instance's memory
  //   BULKHEAD  proxy_get cannot consume every socket this instance has, so a
  //             slow upstream does not starve the rest of the endpoint
  //
  // The bulkhead and timeout come from api/_lib/resilience.js rather than being
  // written here. NO BREAKER: the store lives in Supabase and would be a
  // per-instance counter otherwise, which this platform measured doing nothing
  // in 2026-09-05.
  const guard = proxyGuard();
  try {
    const out = await RESIL.guardedFetch(guard, parsed.toString(), { method: 'GET' });
    const r = out.res;
    // CHECKED BEFORE READING A BYTE, and again while reading: a content-length
    // is a claim by the same party whose body is in question, so it is worth
    // refusing early and worth not believing.
    const declared = Number(r.headers && r.headers.get && r.headers.get('content-length'));
    if (Number.isFinite(declared) && declared > MAX_PROXY_BYTES) {
      res.status(502).json({ error: { code: 'UPSTREAM_TOO_LARGE', message:
        'Upstream (' + parsed.hostname + ') declared ' + declared + ' bytes; the limit is '
        + MAX_PROXY_BYTES } });
      return;
    }
    let text;
    try {
      text = await readCapped(r, MAX_PROXY_BYTES);
    } catch (e) {
      if (e && e.code === 'TOO_LARGE') {
        res.status(502).json({ error: { code: 'UPSTREAM_TOO_LARGE', message:
          'Upstream (' + parsed.hostname + ') exceeded ' + MAX_PROXY_BYTES + ' bytes' } });
        return;
      }
      throw e;
    }
    if (!r.ok) {
      res.status(502).json({ error: { message: 'Upstream (' + parsed.hostname + ') returned ' + r.status } });
      return;
    }
    // PARSED ONLY AFTER IT IS BOUNDED. A parse is the step that turns bytes
    // into structure the rest of the app will act on, so every limit that
    // matters has to be applied on the near side of it.
    let data;
    try { data = JSON.parse(text); } catch (e) { data = { text: text }; }
    res.status(200).json({ ok: true, result: data });
  } catch (err) {
    if (err instanceof RESIL.TimeoutError) {
      console.error('bridge proxy_get: ' + parsed.hostname + ' timed out');
      res.status(504).json({ error: { code: 'UPSTREAM_TIMEOUT', message:
        'Upstream did not answer in time' } });
      return;
    }
    if (err instanceof RESIL.BulkheadFullError) {
      console.error('bridge proxy_get: bulkhead full, refusing rather than queueing');
      res.status(503).json({ error: { code: 'BUSY', message:
        'Too many upstream fetches in flight — try again' } });
      return;
    }
    console.error('bridge proxy_get error:', err);
    res.status(502).json({ error: { message: 'Upstream connection error — try again' } });
  }
}

// Reads at most `cap` bytes and REFUSES past it, rather than truncating. A
// truncated JSON body parses as garbage or, worse, as a valid smaller
// structure -- silently wrong is the outcome this whole file argues against.
async function readCapped(r, cap) {
  if (!r.body || typeof r.body.getReader !== 'function') {
    const t = await r.text();
    if (Buffer.byteLength(t, 'utf8') > cap) {
      const e = new Error('too large'); e.code = 'TOO_LARGE'; throw e;
    }
    return t;
  }
  const reader = r.body.getReader();
  const chunks = [];
  let total = 0;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    total += value.length;
    if (total > cap) {
      try { await reader.cancel(); } catch (e) { /* already closing */ }
      const err = new Error('too large'); err.code = 'TOO_LARGE'; throw err;
    }
    chunks.push(Buffer.from(value));
  }
  return Buffer.concat(chunks).toString('utf8');
}

// ── PUSH IS AUTHENTICATED AND KEYED ON license_hash (2026-09-17) ──────────
// It shared the read side's exact defect. `shopId` came from the BODY with no
// Authorization header, and stonedesk.html's `sdShopId()` is
// `return sdLicenseKey()` -- so `bridge_data.shop_id` was the customer's RAW
// LICENCE KEY, and anyone could overwrite any shop's row by naming it.
//
// TWO THINGS ARE FIXED AND THEY ARE SEPARATE. The endpoint now requires a
// Bearer licence -- the same header api/sd-data.js has always used, so this is
// the platform's existing convention rather than a new one -- and it keys the
// row on the validated `license_hash` instead of the raw key, which is what
// every other table on this platform already does.
//
// THE BODY'S `shopId` IS NO LONGER TRUSTED FOR ANYTHING. It is accepted and
// ignored: a caller cannot name a row, it gets the row its licence proves it
// owns. That is the same correction made to api/claude.js's `app_id` earlier
// today -- a scope key the caller supplies is not a scope key.
//
// EXISTING ROWS ARE ORPHANED BY THIS, DELIBERATELY AND HARMLESSLY. Nothing
// reads bridge_data (the read side was removed the same day), and the old rows
// are keyed by raw licence keys, which is precisely what should stop being
// stored. THEY ARE NOT DELETED HERE -- that is a database action, and it is
// named in the open-work row rather than done silently from an endpoint.
async function handlePush(body, res, req) {
  const auth = (req && req.headers && (req.headers.authorization
    || req.headers.Authorization)) || '';
  const licenceKey = String(auth).replace(/^Bearer\s+/i, '').trim();
  if (!licenceKey) {
    res.status(401).json({ error: { code: 'NO_LICENCE', message:
      'A licence is required: send Authorization: Bearer <licence key>. '
      + 'Until 2026-09-17 this endpoint accepted an unauthenticated write keyed '
      + 'on a shopId taken from the body.' } });
    return;
  }
  let lic;
  try {
    lic = await validateLicenseKey(licenceKey);
  } catch (err) {
    // FAILS CLOSED. A write path is not a read path: allowing an unverified
    // write because the licence store blinked would let the outage do the
    // thing the gate exists to prevent.
    console.error('bridge push: licence check failed:', err && err.message);
    res.status(503).json({ error: { code: 'LICENCE_UNCHECKED', message:
      'The licence could not be verified right now. Nothing was written.' } });
    return;
  }
  if (!lic || !lic.valid || !lic.license_hash) {
    res.status(403).json({ error: { code: 'BAD_LICENCE', message: 'That licence is not valid' } });
    return;
  }
  // ── THE COLUMN IS `license_hash` SINCE 2026-09-18 ────────────────────
  // sql/bridge_data_rekey_2026-09-18.sql renamed it and rehashed the legacy
  // rows in place. The name mattered: after the auth fix this column held a
  // hash under a name that said shop id, so the next reader had to read this
  // handler to find out what was in the table. Every other tenant-scoped
  // table on this platform calls it license_hash.
  //
  // THE RESPONSE FIELD STAYS `shopId`. It is the wire contract the two live
  // callers read, renaming it would break them for no benefit, and it is a
  // HASH either way -- the caller never sees a raw key back.
  const licenseHash = lic.license_hash;
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
    // Upsert on license_hash (its primary key) -- same merge-duplicates pattern
    // api/sd-data.js already uses for business_profiles. Each live caller
    // sends a full current-state snapshot every time, so "latest wins" here
    // is correct, not a data-loss shortcut.
    const r = await fetch(SUPABASE_URL + '/rest/v1/bridge_data?on_conflict=license_hash', {
      method: 'POST',
      headers: {
        apikey: SERVICE_KEY,
        Authorization: 'Bearer ' + SERVICE_KEY,
        'Content-Type': 'application/json',
        Prefer: 'resolution=merge-duplicates,return=representation'
      },
      body: JSON.stringify({ license_hash: String(licenseHash), data: data, updated_at: new Date().toISOString() })
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
    res.status(200).json({ ok: true, written: 1, shopId: written && written.license_hash });
  } catch (err) {
    console.error('bridge push error:', err);
    res.status(502).json({ error: { message: 'Upstream connection error — try again' } });
  }
}

