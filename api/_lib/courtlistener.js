// api/_lib/courtlistener.js
// ---------------------------------------------------------------------------
// Shared CourtListener REST v4 client + real Supabase-backed rate limiter.
// Used by BOTH api/courtlistener.js (the direct search/browse proxy) and
// api/legal-citator.js (the classification orchestration layer), so the
// rate-limit accounting is correct across both call paths instead of each
// endpoint keeping its own (wrong) count. See api/courtlistener.js's own
// header comment for the live-researched API shapes/limits this is built
// against (not guessed) — not re-duplicated here.
//
// Files under api/_lib are NOT routed by Vercel (leading underscore) — this
// is an importable helper, not an endpoint, same convention as
// api/_lib/license.js and api/_lib/auth.js.
// ---------------------------------------------------------------------------

const CL_BASE = 'https://www.courtlistener.com/api/rest/v4';
const CL_LIMITS = { minute: { seconds: 60, max: 4 }, hour: { seconds: 3600, max: 45 }, day: { seconds: 86400, max: 115 } };

function sbClient() {
  const SUPABASE_URL = process.env.SUPABASE_URL;
  const SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!SUPABASE_URL || !SERVICE_KEY) {
    const e = new Error('SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set');
    e.code = 'CONFIG';
    throw e;
  }
  const headers = { apikey: SERVICE_KEY, Authorization: 'Bearer ' + SERVICE_KEY, 'Content-Type': 'application/json' };
  const rest = (path) => SUPABASE_URL + '/rest/v1/' + path;
  return { headers, rest };
}

// Real, Supabase-backed sliding-window check across all three of
// CourtListener's documented windows (minute/hour/day) — see
// api/courtlistener.js's header for why this can't be an in-memory
// counter (stateless serverless functions, shared token across every
// SAIRNlaw firm).
async function checkAndLogRateLimit() {
  const { headers, rest } = sbClient();
  const now = Date.now();
  for (const key of Object.keys(CL_LIMITS)) {
    const { seconds, max } = CL_LIMITS[key];
    const since = new Date(now - seconds * 1000).toISOString();
    const r = await fetch(rest('cl_rate_limit_log?requested_at=gte.' + encodeURIComponent(since) + '&select=id'), { headers });
    if (!r.ok) throw new Error('rate limit check failed: HTTP ' + r.status);
    const rows = await r.json();
    if (Array.isArray(rows) && rows.length >= max) return { limited: true, window: key, max };
  }
  await fetch(rest('cl_rate_limit_log'), { method: 'POST', headers: Object.assign({}, headers, { Prefer: 'return=minimal' }), body: JSON.stringify({}) });
  return { limited: false };
}

// How many rate-limit-consuming CourtListener calls remain available right
// now, per window — used by api/legal-citator.js to decide how big a batch
// of citing opinions it can safely process in one request, rather than
// firing calls until one happens to 429.
async function remainingBudget() {
  const { headers, rest } = sbClient();
  const now = Date.now();
  const remaining = {};
  for (const key of Object.keys(CL_LIMITS)) {
    const { seconds, max } = CL_LIMITS[key];
    const since = new Date(now - seconds * 1000).toISOString();
    const r = await fetch(rest('cl_rate_limit_log?requested_at=gte.' + encodeURIComponent(since) + '&select=id'), { headers });
    if (!r.ok) throw new Error('rate limit budget check failed: HTTP ' + r.status);
    const rows = await r.json();
    remaining[key] = Math.max(0, max - (Array.isArray(rows) ? rows.length : 0));
  }
  return remaining;
}

// Unauthenticated CourtListener calls (search, courts) — real, confirmed
// live 2026-08-08 to require no token and not be subject to the
// authenticated rate limit, so these deliberately do NOT go through the
// limiter above.
async function clSearch(q) {
  const params = new URLSearchParams({ q, type: 'o' });
  const r = await fetch(CL_BASE + '/search/?' + params.toString());
  const data = await r.json();
  if (!r.ok) { const e = new Error('CourtListener search error: ' + JSON.stringify(data).slice(0, 300)); e.status = r.status; throw e; }
  return data;
}
async function clCourt(courtId) {
  const params = new URLSearchParams({ id: courtId });
  const r = await fetch(CL_BASE + '/courts/?' + params.toString());
  const data = await r.json();
  if (!r.ok) { const e = new Error('CourtListener courts error: ' + JSON.stringify(data).slice(0, 300)); e.status = r.status; throw e; }
  return data;
}

// Token-gated calls — every one of these consumes real rate-limit budget
// and requires COURTLISTENER_API_TOKEN. Callers must check
// checkAndLogRateLimit()/remainingBudget() themselves before calling these
// in a loop (legal-citator.js does) — these functions log one request each
// but do not themselves refuse to run over budget, since the batch-level
// decision belongs to the orchestration layer, not this low-level client.
function tokenHeaders() {
  const token = process.env.COURTLISTENER_API_TOKEN;
  if (!token) { const e = new Error('COURTLISTENER_API_TOKEN not configured'); e.code = 'NOT_CONFIGURED'; throw e; }
  return { Authorization: 'Token ' + token };
}
async function clCitingOpinions(citedOpinionId) {
  await checkAndLogRateLimit();
  const params = new URLSearchParams({ cited_opinion: String(citedOpinionId) });
  const r = await fetch(CL_BASE + '/opinions-cited/?' + params.toString(), { headers: tokenHeaders() });
  const data = await r.json();
  if (!r.ok) { const e = new Error('CourtListener opinions-cited error: ' + JSON.stringify(data).slice(0, 300)); e.status = r.status; throw e; }
  return data;
}
async function clOpinionText(opinionId) {
  await checkAndLogRateLimit();
  const r = await fetch(CL_BASE + '/opinions/' + encodeURIComponent(opinionId) + '/', { headers: tokenHeaders() });
  const data = await r.json();
  if (!r.ok) { const e = new Error('CourtListener opinion error: ' + JSON.stringify(data).slice(0, 300)); e.status = r.status; throw e; }
  return data;
}
async function clCluster(clusterId) {
  await checkAndLogRateLimit();
  const r = await fetch(CL_BASE + '/clusters/' + encodeURIComponent(clusterId) + '/', { headers: tokenHeaders() });
  const data = await r.json();
  if (!r.ok) { const e = new Error('CourtListener cluster error: ' + JSON.stringify(data).slice(0, 300)); e.status = r.status; throw e; }
  return data;
}
async function clCitationLookup(text) {
  await checkAndLogRateLimit();
  const r = await fetch(CL_BASE + '/citation-lookup/', { method: 'POST', headers: Object.assign({ 'Content-Type': 'application/json' }, tokenHeaders()), body: JSON.stringify({ text }) });
  const data = await r.json();
  if (!r.ok) { const e = new Error('CourtListener citation-lookup error: ' + JSON.stringify(data).slice(0, 300)); e.status = r.status; throw e; }
  return data;
}

module.exports = {
  sbClient, checkAndLogRateLimit, remainingBudget,
  clSearch, clCourt, clCitingOpinions, clOpinionText, clCluster, clCitationLookup
};
