// api/network.js
// ---------------------------------------------------------------------------
// SAIRN Intelligence Network -- cross-tenant anonymized-pattern aggregation.
// Built 2026-08-01 to replace a URL StoneDesk's client code has assumed
// existed since June 16 2026 (stonedesk.html:21898-21930) but was never
// committed -- confirmed live 404 (X-Vercel-Error: NOT_FOUND, no CORS
// headers at all, which is what actually produced the localhost:8806 CORS
// error report). Same class of gap as api/bridge.js.
//
// Check 0e (searched before building): probed 8 plausible existing table
// names via the project's public anon key. None matched this purpose.
// Two unrelated-sounding tables surfaced via PostgREST's error hints --
// webhook_events, demo_calls -- neither inspected or reused: no safe
// service-role access to confirm their actual schema/purpose from this
// session, and guessing wrong risks writing into someone else's system.
// Flagged here for a human to check; this migration builds new instead.
//
// DEAD-CODE FINDING (report this, don't silently fix or silently ignore):
// the only POST call site, sendNetworkInsight() (stonedesk.html:21921), is
// only ever invoked from inside window.sendMessage's DOMContentLoaded
// monkey-patch (stonedesk.html:21945), which reads document.getElementById
// ('userInput') -- an id that does not exist anywhere in current markup
// (confirmed via grep). That patched function no-ops on its very first
// line, every time, for every caller. sendNetworkInsight() therefore never
// actually fires in real usage today -- this is the SAME dead #userInput/
// sendMessage() legacy chat path already flagged elsewhere in this file
// (see stonedesk.html:17322 etc.), just not previously connected to this
// endpoint's absence. The GET call (loadNetworkIntelligence(), called
// unconditionally from the outer DOMContentLoaded listener) DOES fire for
// real on every page load -- its result is just never surfaced anywhere,
// since its only consumer is the same dead code path. Building the real
// server endpoint here regardless: it's correct infrastructure either way,
// and a future session reconnecting the live sdAISend() chat to it is a
// small, separate wiring change, not a reason to leave the server side
// broken too.
//
// ── GET /api/network?app=X ──────────────────────────────────────────────
// Returns aggregate, anonymized insight strings computed from real recent
// signals for that app_id (cross-SHOP, same app_id -- matches the client
// comment "anonymized patterns from other stonedesk installs", not
// cross-app). Only surfaces a pattern once at least MIN_OCCURRENCES
// distinct signals share it within the lookback window -- a floor, not
// just a formatting choice: single-digit counts could point back at one
// shop, which defeats the point of "anonymized". With a brand-new,
// currently-empty table this returns an honestly empty list, not
// fabricated insights -- exactly what Check 0b requires.
// Response: { ok:true, insights: string[] }
//
// ── POST /api/network ────────────────────────────────────────────────────
// Body: { app, type, pattern, score? }. The client comment promises "the
// server re-validates and rejects anything that looks like a price, name,
// or PII" -- implemented here structurally, not by trying to regex-scrub
// free text: type/pattern must match a short identifier pattern
// ([a-z0-9_]{1,64}) with no spaces, so free-text PII/prices/names cannot be
// stored in the first place, not just filtered after the fact.
// Response: { ok:true }
//
// CORS: Access-Control-Allow-Origin:* on both methods. Unlike api/bridge.js
// (push/pull touch real per-shop data) or api/sd-data.js (license-gated),
// this endpoint only ever stores/returns anonymized aggregate counts with
// no per-tenant identity and no auth token sent by any caller -- there is
// nothing here a permissive origin policy would expose that the data
// itself doesn't already exclude by construction.
//
// REQUIRES env: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY.
// ---------------------------------------------------------------------------

const IDENT_RE = /^[a-z0-9_]{1,64}$/i;
const MIN_OCCURRENCES = 3;
const LOOKBACK_DAYS = 30;
const MAX_APP_LEN = 64;

function setCors(res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
}

module.exports = async (req, res) => {
  setCors(res);
  if (req.method === 'OPTIONS') { res.status(204).end(); return; }

  if (req.method === 'GET') return handleGet(req, res);
  if (req.method === 'POST') return handlePost(req, res);
  res.status(405).json({ error: { message: 'Method not allowed' } });
};

async function handleGet(req, res) {
  const app = (req.query && req.query.app) || null;
  if (!app || typeof app !== 'string' || !IDENT_RE.test(app) || app.length > MAX_APP_LEN) {
    res.status(400).json({ error: { message: 'app query param is required and must be a short identifier' } });
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
    const since = new Date(Date.now() - LOOKBACK_DAYS * 24 * 60 * 60 * 1000).toISOString();
    const url = SUPABASE_URL + '/rest/v1/network_insights?app=eq.' + encodeURIComponent(app) +
      '&created_at=gte.' + encodeURIComponent(since) +
      '&select=type,pattern&limit=2000';
    const r = await fetch(url, {
      headers: { apikey: SERVICE_KEY, Authorization: 'Bearer ' + SERVICE_KEY }
    });
    const rows = await r.json().catch(function () { return null; });
    if (!r.ok) {
      const code = rows && rows.code;
      if (code === '42P01' || code === 'PGRST205') {
        res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'network_insights table not found — run sql/network_schema.sql in the Supabase SQL editor' } });
        return;
      }
      // 42501 = Postgres permission_denied -- same class of gap already
      // hit on bridge_data (2026-08-01): the table exists but service_role
      // has no GRANT on it. Surface Postgres's own fix hint verbatim.
      if (code === '42501') {
        res.status(503).json({ error: { code: 'PERMISSION_DENIED', message: (rows && rows.hint) || 'service_role lacks privileges on network_insights — run the GRANT Postgres suggests in the Supabase SQL editor' } });
        return;
      }
      console.error('network GET upstream error:', rows);
      res.status(502).json({ error: { message: 'Data store error — try again' } });
      return;
    }

    const counts = {};
    (rows || []).forEach(function (row) {
      const key = row.type + '|' + row.pattern;
      counts[key] = (counts[key] || 0) + 1;
    });

    const insights = Object.keys(counts)
      .filter(function (key) { return counts[key] >= MIN_OCCURRENCES; })
      .sort(function (a, b) { return counts[b] - counts[a]; })
      .slice(0, 5)
      .map(function (key) {
        var parts = key.split('|');
        return counts[key] + ' recent ' + app + ' sessions logged "' + parts[1] + '" (' + parts[0] + ') in the last ' + LOOKBACK_DAYS + ' days.';
      });

    res.status(200).json({ ok: true, insights: insights });
  } catch (err) {
    console.error('network GET error:', err);
    res.status(502).json({ error: { message: 'Upstream connection error — try again' } });
  }
}

async function handlePost(req, res) {
  let body = req.body;
  if (typeof body === 'string') {
    try { body = JSON.parse(body); } catch (e) { body = {}; }
  }
  body = body || {};

  const app = body.app, type = body.type, pattern = body.pattern;
  const score = typeof body.score === 'number' ? body.score : null;

  // Structural PII/price/name gate: only short bare identifiers are
  // accepted at all, in any of the three string fields -- this is what the
  // client's own comment promises ("the server re-validates and rejects
  // anything that looks like a price, name, or PII regardless"). No free
  // text is ever accepted, so there is no PII/price/name shape it could
  // take that would pass.
  if (!app || !IDENT_RE.test(app) || app.length > MAX_APP_LEN) {
    res.status(400).json({ error: { message: 'app must be a short identifier' } });
    return;
  }
  if (!type || !IDENT_RE.test(type)) {
    res.status(400).json({ error: { message: 'type must be a short identifier (letters/digits/underscore only)' } });
    return;
  }
  if (!pattern || !IDENT_RE.test(pattern)) {
    res.status(400).json({ error: { message: 'pattern must be a short identifier (letters/digits/underscore only) — free text is rejected, not scrubbed' } });
    return;
  }
  if (score !== null && (score < 0 || score > 1)) {
    res.status(400).json({ error: { message: 'score must be between 0 and 1' } });
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
    const r = await fetch(SUPABASE_URL + '/rest/v1/network_insights', {
      method: 'POST',
      headers: {
        apikey: SERVICE_KEY,
        Authorization: 'Bearer ' + SERVICE_KEY,
        'Content-Type': 'application/json',
        Prefer: 'return=minimal'
      },
      body: JSON.stringify({ app: app, type: type, pattern: pattern, score: score })
    });
    if (!r.ok) {
      const out = await r.json().catch(function () { return null; });
      const code = out && out.code;
      if (code === '42P01' || code === 'PGRST205') {
        res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'network_insights table not found — run sql/network_schema.sql in the Supabase SQL editor' } });
        return;
      }
      if (code === '42501') {
        res.status(503).json({ error: { code: 'PERMISSION_DENIED', message: (out && out.hint) || 'service_role lacks privileges on network_insights — run the GRANT Postgres suggests in the Supabase SQL editor' } });
        return;
      }
      console.error('network POST upstream error:', out);
      res.status(502).json({ error: { message: 'Data store error — try again' } });
      return;
    }
    res.status(200).json({ ok: true });
  } catch (err) {
    console.error('network POST error:', err);
    res.status(502).json({ error: { message: 'Upstream connection error — try again' } });
  }
}
