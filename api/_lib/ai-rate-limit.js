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
// ── ATOMIC AS OF 2026-09-02, AND IT WAS NOT BEFORE ──
// This file used to count and record in TWO SEPARATE HTTP CALLS with nothing
// coordinating them. Vercel runs these functions concurrently, so N
// simultaneous requests all read the SAME count, all decide they are under the
// limit, and all insert -- 50 requests arriving at count 199 against a limit of
// 200 were ALL permitted. The limit was approximate, not enforced, and would
// have stayed approximate the moment enforce mode was switched on, which is
// worse than observe mode because it would then LOOK like a real cap.
//
// The fix is one RPC to public.sairn_ai_rate_limit_consume(), which takes a
// pg_advisory_xact_lock keyed on the app_id and does the count and the insert
// inside a single transaction. See sql/sairn_ai_rate_limit_consume_fn.sql for
// why an advisory lock rather than a row lock or a counter row. It is also one
// round trip instead of two, so it is faster as well as correct.
//
// ── THE OLD PATH IS KEPT AS A FALLBACK, AND IS STILL RACY ──
// The RPC does not exist until that migration is run. Until then this falls
// back to the original count-then-insert, which behaves exactly as it always
// has. The fallback reports mode 'observe-racy' / 'enforce-racy' so the race is
// visible in the returned value rather than being a silent property of the
// deployment, and so a reader of a log line can tell which path produced it.
// DO NOT switch SAIRN_AI_RATE_LIMIT_MODE=enforce while the fallback is live --
// enforcing an approximate limit is the worst of both worlds.
//
// One real counting bug was fixed in the fallback on the way past: it set
// `Prefer: count=exact` and then ignored it, using rows.length instead. That is
// the number of rows PostgREST chose to RETURN, which is subject to its
// max-rows setting -- so above that ceiling the count would silently stop
// growing and the limit could never trigger. It now reads the exact count from
// the Content-Range header and asks for zero rows back, which is also a great
// deal less data on every single AI call.
//
// ── SHIPS IN OBSERVE MODE ON PURPOSE ──
// 10 of 11 live SAIRN apps send is_demo:true. Because the old counter kept
// resetting, a 200/day limit has effectively never been enforced against real
// traffic on any of them. Turning real enforcement on blind would risk a
// platform-wide outage on a threshold nobody has measured. So by default this
// RECORDS every call and REPORTS when a limit would have been exceeded,
// without blocking. Flip it deliberately once the real numbers are known AND
// the RPC migration has been run:
//     SAIRN_AI_RATE_LIMIT_MODE=enforce
//     SAIRN_AI_DAILY_LIMIT=200          (optional, default 200)
//
// ── FAILS OPEN, ON PURPOSE ──
// If Supabase is unreachable or the table is missing, this allows the call.
// A logging/counting outage must never take down every AI feature on the
// platform -- the same best-effort reasoning api/_lib/audit.js documents for
// audit writes. A blocked-by-accident real user is a worse outcome than an
// uncounted call. Unchanged by the atomicity fix.
//
// REQUIRES env: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
// REQUIRES sql/sairn_ai_rate_limit_schema.sql to have been run.
// ATOMIC ONLY ONCE sql/sairn_ai_rate_limit_consume_fn.sql has been run.
// ---------------------------------------------------------------------------

const TABLE = 'sairn_ai_rate_limit_log';
const RPC = 'sairn_ai_rate_limit_consume';
const DEFAULT_DAILY_LIMIT = 200;
const WINDOW_SECONDS = 24 * 60 * 60;

function dailyLimit() {
  const raw = Number(process.env.SAIRN_AI_DAILY_LIMIT);
  return Number.isFinite(raw) && raw > 0 ? raw : DEFAULT_DAILY_LIMIT;
}

function isEnforcing() {
  return String(process.env.SAIRN_AI_RATE_LIMIT_MODE || '').toLowerCase() === 'enforce';
}

function sb() {
  const SUPABASE_URL = process.env.SUPABASE_URL;
  const SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!SUPABASE_URL || !SERVICE_KEY) return null;
  return {
    headers: {
      apikey: SERVICE_KEY,
      Authorization: 'Bearer ' + SERVICE_KEY,
      'Content-Type': 'application/json'
    },
    rest: (path) => SUPABASE_URL.replace(/\/+$/, '') + '/rest/v1/' + path
  };
}

// Exact row count from PostgREST's Content-Range header ("0-24/1234" or
// "*/1234"), NOT the length of the returned array. Returns null if absent.
function exactCountFrom(res) {
  const cr = res.headers && res.headers.get ? res.headers.get('content-range') : null;
  if (!cr) return null;
  const total = String(cr).split('/')[1];
  if (!total || total === '*') return null;
  const n = Number(total);
  return Number.isFinite(n) ? n : null;
}

// THE ATOMIC PATH. One call; the count and the insert happen together under an
// advisory lock held for the duration of the statement's transaction.
// Returns null when the RPC is unavailable, so the caller can fall back.
async function consumeAtomic(client, appId, limit) {
  const r = await fetch(client.rest('rpc/' + RPC), {
    method: 'POST',
    headers: client.headers,
    body: JSON.stringify({ p_app_id: appId, p_limit: limit, p_window_seconds: WINDOW_SECONDS })
  });
  if (!r.ok) {
    // 404 = migration not run yet, which is expected and quiet-ish; anything
    // else is a real problem worth shouting about.
    if (r.status === 404) return null;
    console.error('ai rate limit: atomic RPC failed, HTTP', r.status, '-- falling back to the racy path');
    return null;
  }
  const body = await r.json().catch(() => null);
  if (!body || typeof body !== 'object' || body.error) {
    console.error('ai rate limit: atomic RPC returned an unusable body -- falling back');
    return null;
  }
  return {
    count: Number(body.prior_count) || 0,
    limited: body.limited === true,
    counted: true
  };
}

// THE OLD PATH, KEPT ONLY UNTIL THE MIGRATION IS RUN. Still racy by
// construction -- two uncoordinated calls -- and says so in the mode it
// reports.
async function consumeRacy(client, appId, limit) {
  const since = new Date(Date.now() - WINDOW_SECONDS * 1000).toISOString();
  const r = await fetch(
    client.rest(TABLE + '?app_id=eq.' + encodeURIComponent(appId) +
                '&requested_at=gte.' + encodeURIComponent(since) + '&select=id&limit=1'),
    { headers: Object.assign({}, client.headers, { Prefer: 'count=exact' }) }
  );
  if (!r.ok) {
    console.error('ai rate limit: count failed (failing open), HTTP', r.status);
    return null;
  }
  await r.json().catch(() => null);
  const exact = exactCountFrom(r);
  if (exact === null) {
    console.error('ai rate limit: no exact count header (failing open)');
    return null;
  }

  const w = await fetch(client.rest(TABLE), {
    method: 'POST',
    headers: Object.assign({}, client.headers, { Prefer: 'return=minimal' }),
    body: JSON.stringify({ app_id: appId })
  });
  if (!w.ok) console.error('ai rate limit: insert failed, HTTP', w.status);

  return { count: exact, limited: exact >= limit, counted: w.ok };
}

// Returns { allowed, limited, count, limit, mode, counted, atomic }
//   allowed  — whether the caller should proceed (false only in enforce mode)
//   limited  — whether the limit WAS exceeded, regardless of mode
//   counted  — whether this call was actually recorded (false = infra problem)
//   atomic   — whether the count and the record happened as one operation.
//              false means the limit is APPROXIMATE under concurrency; it is
//              returned rather than hidden so a caller, a log line or a future
//              reader can tell the difference.
// Never throws.
async function checkAiRateLimit(appId) {
  const limit = dailyLimit();
  const enforcing = isEnforcing();
  const base = {
    limited: false, count: null, limit: limit,
    mode: enforcing ? 'enforce' : 'observe',
    counted: false, allowed: true, atomic: false
  };

  const client = sb();
  if (!client || !appId) return base;

  try {
    let atomic = true;
    let res = await consumeAtomic(client, appId, limit);
    if (!res) { atomic = false; res = await consumeRacy(client, appId, limit); }
    if (!res) return base;

    const mode = (enforcing ? 'enforce' : 'observe') + (atomic ? '' : '-racy');

    if (res.limited) {
      console.error('ai rate limit ' +
        (enforcing ? 'EXCEEDED (blocking)' : 'would have blocked (observe mode)') +
        ' app_id=' + appId + ' count=' + res.count + ' limit=' + limit +
        ' atomic=' + atomic);
    }

    return {
      allowed: enforcing ? !res.limited : true,
      limited: res.limited,
      count: res.count,
      limit: limit,
      mode: mode,
      counted: res.counted,
      atomic: atomic
    };
  } catch (e) {
    console.error('ai rate limit: check errored (failing open):', e && e.message);
    return base;
  }
}

module.exports = { checkAiRateLimit, dailyLimit, isEnforcing, exactCountFrom, consumeAtomic, consumeRacy };
