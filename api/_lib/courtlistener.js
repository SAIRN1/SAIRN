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
// ── THE ATOMIC PATH (2026-09-04) ───────────────────────────────────────────
// One RPC. The three window counts and the insert happen together inside one
// transaction under an advisory lock -- see
// sql/cl_rate_limit_consume_fn_2026-09-04.sql, which also records why the lock
// key is a single constant rather than per-tenant.
//
// Returns null ONLY when the migration has not been run (404). Every other
// failure throws, because this limiter fails CLOSED -- see the block comment
// on checkAndLogRateLimit().
const CONSUME_RPC = 'cl_rate_limit_consume';

async function consumeAtomic() {
  const { headers, rest } = sbClient();
  const r = await fetch(rest('rpc/' + CONSUME_RPC), {
    method: 'POST',
    headers: headers,
    body: JSON.stringify({
      p_minute_max: CL_LIMITS.minute.max,
      p_hour_max: CL_LIMITS.hour.max,
      p_day_max: CL_LIMITS.day.max
    })
  });
  // 404 = the function does not exist yet. That is the only condition under
  // which the legacy path is allowed to run, and it is checked narrowly so a
  // 500 or a permission error can never be mistaken for "not migrated yet".
  if (r.status === 404) return null;
  if (!r.ok) throw new Error('rate limit RPC failed: HTTP ' + r.status);
  const body = await r.json().catch(() => null);
  if (!body || typeof body !== 'object' || body.error) {
    throw new Error('rate limit RPC returned an unusable body: ' + JSON.stringify(body).slice(0, 200));
  }
  return body.limited === true
    ? { limited: true, window: body.window, max: body.max }
    : { limited: false };
}

// ── WHY THIS FAILS CLOSED, WHERE THE AI LIMITER DELIBERATELY FAILS OPEN ────
// api/_lib/ai-rate-limit.js allows the call when its counter is unreachable:
// a counting outage must not take down every AI feature on the platform. That
// is the right trade there and the WRONG one here, and the difference is worth
// stating because the two files otherwise look alike enough to copy.
//
// This limiter guards a THIRD PARTY's documented allowance on a token shared
// by every SAIRNlaw firm (see api/courtlistener.js's header). If the count
// cannot be read, the honest state is "I do not know whether we are within
// CourtListener's limit", and the safe answer to that is to refuse one
// request -- not to spend an unknown amount of a shared budget whose penalty
// is CourtListener throttling or revoking the token for everyone.
//
// So the existing throw-on-failed-count behaviour is PRESERVED, not replaced.
//
// ── THE LEGACY PATH IS STILL RACY AND IS NOW NARROWLY SCOPED ──
// It runs only until the migration is applied (RPC 404), and it says so on
// every call rather than being a silent property of the deployment. It counted
// and then inserted in separate HTTP calls, so N concurrent callers all read
// the same counts, all pass, and all insert. At a ceiling of 4 per minute that
// takes two callers, not fifty.
async function checkAndLogRateLimit() {
  const atomic = await consumeAtomic();
  if (atomic) return atomic;

  console.warn('courtlistener rate limit: atomic RPC not present (run '
    + 'sql/cl_rate_limit_consume_fn_2026-09-04.sql) -- using the RACY '
    + 'count-then-insert path; concurrent callers can exceed the shared budget');

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
// and requires COURTLISTENER_API_TOKEN.
//
// ── THESE NOW REFUSE, AND UNTIL 2026-09-04 THEY DID NOT ───────────────────
// This comment used to read: "these functions log one request each but do not
// themselves refuse to run over budget, since the batch-level decision belongs
// to the orchestration layer, not this low-level client."
//
// That was a coherent design and it was not what the code did. All four
// functions called `await checkAndLogRateLimit()` and DISCARDED THE RESULT,
// and no caller anywhere in api/ read that return value either — grepped, not
// assumed. So the limiter computed {limited: true, window: 'minute'} and the
// very next line called CourtListener anyway. The only thing actually standing
// between SAIRNlaw and a third party's ceiling was remainingBudget() in the
// orchestration layer: a SEPARATE read, taken before the work starts, with an
// arbitrarily wide gap before the call it is meant to authorise.
//
// Nothing about that is visible from the outside. The limiter ran, the log row
// was written, the budget looked accounted for, and the refusal was thrown
// away — the shape sairn-silent-failure-sweep exists to catch.
//
// Now the verdict is honoured here, with `status = 429` so api/courtlistener.js's
// existing `if (err.status)` handler surfaces it unchanged. The orchestration
// layer's own pre-flight check is kept: it decides how big a batch to attempt,
// which is a genuinely different question from whether THIS call may proceed.
function tokenHeaders() {
  const token = process.env.COURTLISTENER_API_TOKEN;
  if (!token) { const e = new Error('COURTLISTENER_API_TOKEN not configured'); e.code = 'NOT_CONFIGURED'; throw e; }
  return { Authorization: 'Token ' + token };
}

// Consume one unit of budget, or refuse. The single place the verdict is
// acted on, so there is one spelling of the refusal rather than four.
async function spendBudgetOrRefuse() {
  const v = await checkAndLogRateLimit();
  if (v && v.limited) {
    const e = new Error('CourtListener request budget for this ' + v.window +
      ' is exhausted (shared across all SAIRNlaw firms) — try again shortly.');
    e.status = 429;
    e.code = 'CL_RATE_LIMITED';
    e.window = v.window;
    throw e;
  }
}
async function clCitingOpinions(citedOpinionId) {
  await spendBudgetOrRefuse();
  const params = new URLSearchParams({ cited_opinion: String(citedOpinionId) });
  const r = await fetch(CL_BASE + '/opinions-cited/?' + params.toString(), { headers: tokenHeaders() });
  const data = await r.json();
  if (!r.ok) { const e = new Error('CourtListener opinions-cited error: ' + JSON.stringify(data).slice(0, 300)); e.status = r.status; throw e; }
  return data;
}
async function clOpinionText(opinionId) {
  await spendBudgetOrRefuse();
  const r = await fetch(CL_BASE + '/opinions/' + encodeURIComponent(opinionId) + '/', { headers: tokenHeaders() });
  const data = await r.json();
  if (!r.ok) { const e = new Error('CourtListener opinion error: ' + JSON.stringify(data).slice(0, 300)); e.status = r.status; throw e; }
  return data;
}
async function clCluster(clusterId) {
  await spendBudgetOrRefuse();
  const r = await fetch(CL_BASE + '/clusters/' + encodeURIComponent(clusterId) + '/', { headers: tokenHeaders() });
  const data = await r.json();
  if (!r.ok) { const e = new Error('CourtListener cluster error: ' + JSON.stringify(data).slice(0, 300)); e.status = r.status; throw e; }
  return data;
}
async function clCitationLookup(text) {
  await spendBudgetOrRefuse();
  const r = await fetch(CL_BASE + '/citation-lookup/', { method: 'POST', headers: Object.assign({ 'Content-Type': 'application/json' }, tokenHeaders()), body: JSON.stringify({ text }) });
  const data = await r.json();
  if (!r.ok) { const e = new Error('CourtListener citation-lookup error: ' + JSON.stringify(data).slice(0, 300)); e.status = r.status; throw e; }
  return data;
}

module.exports = {
  sbClient, checkAndLogRateLimit, remainingBudget,
  clSearch, clCourt, clCitingOpinions, clOpinionText, clCluster, clCitationLookup
};
