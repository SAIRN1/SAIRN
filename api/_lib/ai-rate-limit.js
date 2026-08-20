// api/_lib/ai-rate-limit.js
// ---------------------------------------------------------------------------
// Persistent, Supabase-backed per-app_id daily rate limiter for AI calls.
//
// Replaces the in-memory `demoCallCounts` counter in api/claude.js, which that
// file's own header has always disclosed as unreliable: it lives in a single
// serverless instance's memory, resets on cold start, and is not shared across
// concurrent invocations, so it "does NOT reliably cap usage or cost across
// real traffic." The 2026-08-20 firewall audit (layer 22) confirmed that is
// still the case. Same Supabase sliding-window pattern already proven in
// api/_lib/courtlistener.js.
//
// ── SHIPS IN OBSERVE MODE ON PURPOSE ──
// 10 of 11 live SAIRN apps send is_demo:true. Because the old counter kept
// resetting, a 200/day limit has effectively never been enforced against real
// traffic on any of them. Turning real enforcement on blind would risk a
// platform-wide outage on a threshold nobody has measured. So by default this
// RECORDS every call and REPORTS when a limit would have been exceeded,
// without blocking. Flip it deliberately once the real numbers are known:
//     SAIRN_AI_RATE_LIMIT_MODE=enforce
//     SAIRN_AI_DAILY_LIMIT=200          (optional, default 200)
//
// ── FAILS OPEN, ON PURPOSE ──
// If Supabase is unreachable or the table is missing, this allows the call.
// A logging/counting outage must never take down every AI feature on the
// platform -- the same best-effort reasoning api/_lib/audit.js documents for
// audit writes. A blocked-by-accident real user is a worse outcome than an
// uncounted call.
//
// REQUIRES env: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
// REQUIRES sql/sairn_ai_rate_limit_schema.sql to have been run.
// ---------------------------------------------------------------------------

const TABLE = 'sairn_ai_rate_limit_log';
const DEFAULT_DAILY_LIMIT = 200;
const WINDOW_SECONDS = 24 * 60 * 60;

function dailyLimit() {
  const raw = Number(process.env.SAIRN_AI_DAILY_LIMIT);
  return Number.isFinite(raw) && raw > 0 ? raw : DEFAULT_DAILY_LIMIT;
}

function isEnforcing() {
  return String(process.env.SAIRN_AI_RATE_LIMIT_MODE || '').toLowerCase() === 'enforce';
}

// Returns { allowed, limited, count, limit, mode, counted }
//   allowed  — whether the caller should proceed (false only in enforce mode)
//   limited  — whether the limit WAS exceeded, regardless of mode
//   counted  — whether this call was actually recorded (false = infra problem)
// Never throws.
async function checkAiRateLimit(appId) {
  const limit = dailyLimit();
  const mode = isEnforcing() ? 'enforce' : 'observe';
  const base = { limited: false, count: null, limit: limit, mode: mode, counted: false, allowed: true };

  const SUPABASE_URL = process.env.SUPABASE_URL;
  const SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!SUPABASE_URL || !SERVICE_KEY || !appId) return base;

  const headers = {
    apikey: SERVICE_KEY,
    Authorization: 'Bearer ' + SERVICE_KEY,
    'Content-Type': 'application/json'
  };
  const rest = (path) => SUPABASE_URL.replace(/\/+$/, '') + '/rest/v1/' + path;
  const since = new Date(Date.now() - WINDOW_SECONDS * 1000).toISOString();

  try {
    // Count first, then record. Counting before recording means the Nth call
    // sees N-1 prior calls, so a limit of 200 permits exactly 200 calls.
    const r = await fetch(
      rest(TABLE + '?app_id=eq.' + encodeURIComponent(appId) +
           '&requested_at=gte.' + encodeURIComponent(since) + '&select=id'),
      { headers: Object.assign({}, headers, { Prefer: 'count=exact' }) }
    );
    if (!r.ok) {
      // Table missing / permission problem / outage -- fail open, but make it
      // loud in logs so a silently-disabled limiter is discoverable.
      console.error('ai rate limit: count failed (failing open), HTTP', r.status);
      return base;
    }
    const rows = await r.json();
    const count = Array.isArray(rows) ? rows.length : 0;
    const limited = count >= limit;

    // Record this call even when limited, so observe-mode data reflects real
    // demand rather than being clipped at the threshold.
    const w = await fetch(rest(TABLE), {
      method: 'POST',
      headers: Object.assign({}, headers, { Prefer: 'return=minimal' }),
      body: JSON.stringify({ app_id: appId })
    });
    const counted = w.ok;
    if (!counted) console.error('ai rate limit: insert failed, HTTP', w.status);

    if (limited) {
      console.error('ai rate limit ' + (mode === 'enforce' ? 'EXCEEDED (blocking)' : 'would have blocked (observe mode)') +
        ' app_id=' + appId + ' count=' + count + ' limit=' + limit);
    }

    return {
      allowed: mode === 'enforce' ? !limited : true,
      limited: limited,
      count: count,
      limit: limit,
      mode: mode,
      counted: counted
    };
  } catch (e) {
    console.error('ai rate limit: check errored (failing open):', e && e.message);
    return base;
  }
}

module.exports = { checkAiRateLimit, dailyLimit, isEnforcing };
