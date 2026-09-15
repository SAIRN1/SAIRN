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
// ══ READ THIS BEFORE FLIPPING enforce: IT IS ALSO A TENANCY DECISION ══════
//
// Until 2026-09-15 the paragraph above was the only warning at this switch, and
// it is about the RACE. It is not the only thing that changes.
//
// This limiter counts per `app_id`. Every customer of one app therefore shares
// ONE daily ceiling, so the moment `enforce` is on, one practice, firm or shop
// exhausting the app's 200 locks out EVERY OTHER CUSTOMER OF THAT APP for the
// rest of the day. Nothing at this switch used to say so, and nothing in this
// file's history ever asked whether that was wanted --
// docs/2026-09-15-item93-shared-backend-tenancy-scoping.md measured it and
// found that the `app_id` key was inherited from the table shape rather than
// chosen. A real fairness question had been answered by a column name.
//
// MICHAEL DECIDED IT 2026-09-15: each client gets its own SUB-BUDGET inside the
// existing per-app ceiling. Not a second limiter and not a bigger ceiling.
//
//   THE GUARANTEE: once an app is past its contention floor, no single tenant
//   may hold more than its share of the daily ceiling, so the remainder stays
//   reachable by every other tenant of that app.
//
//     SAIRN_AI_TENANT_SHARE=100         (optional; default half the app limit)
//     SAIRN_AI_CONTENTION_FLOOR=100     (optional; default half the app limit)
//
// THE CAP BINDS ONLY UNDER CONTENTION, and that is the design rather than a
// softening of it. Ten of the fourteen apps with seeded licences have exactly
// ONE tenant; a hard per-tenant cap would take capacity away from somebody
// contending with nobody, to protect tenants who do not exist. Below the floor
// nobody is capped at all.
//
// A CALL WITH NO TENANT IS NOT REFUSED AND IS NOT INVISIBLE. SAIRN_CLAUDE_AUTH_MODE
// is `observe` in production, so much real traffic arrives with no licence and
// therefore no tenant identity. Those calls count against the APP exactly as
// before, are never sub-budgeted, and come back `tenant_scoped:false` -- so
// observe-mode data now shows how much traffic is currently unattributable.
// That number is the real precondition for enforcement and did not exist
// before. Requires sql/sairn_ai_tenant_subbudget_2026-09-15.sql.
//
// NOT CHANGED BY THIS, and deliberately: api/_lib/courtlistener.js stays global.
// Its SQL states the reason -- one upstream token, so one budget, so one lock --
// and that reasoning is correct. This decision is about a budget WE own.
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

// ── THE SUB-BUDGET KNOBS (2026-09-15) ────────────────────────────────────
// Both default to HALF the app ceiling, which is the property in the header
// stated as a number: past the floor a tenant may hold at most half, so at
// least half stays reachable by everybody else.
//
// An UNPARSEABLE value falls back to the default rather than to zero. A zero
// share would cap every tenant at nothing the moment the floor is crossed --
// the shape this platform keeps writing down, where a setting that means
// "unreadable" behaves as "disabled" or, worse, as "maximally strict".
function tenantShare(limit) {
  const raw = Number(process.env.SAIRN_AI_TENANT_SHARE);
  return Number.isFinite(raw) && raw > 0 ? Math.floor(raw) : Math.max(1, Math.floor(limit / 2));
}
function contentionFloor(limit) {
  const raw = Number(process.env.SAIRN_AI_CONTENTION_FLOOR);
  return Number.isFinite(raw) && raw > 0 ? Math.floor(raw) : Math.max(1, Math.floor(limit / 2));
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
// TENANT ARGUMENTS ARE SENT ONCE AND THEN REMEMBERED (2026-09-15).
// The deployed database may still hold the 3-argument function, in which case
// PostgREST answers 404 for the 6-argument call. Retrying every request would
// double the round trips on an un-migrated deployment forever, so the first
// 404 sets this for the life of the process and later calls go straight to the
// old shape. Module-level rather than global: a cold start re-probes, which is
// what makes the flag self-healing after the migration runs.
let tenantArgsUnsupported = false;

async function consumeAtomic(client, appId, limit, tenantKey) {
  const args = { p_app_id: appId, p_limit: limit, p_window_seconds: WINDOW_SECONDS };
  const wantTenant = !!tenantKey && !tenantArgsUnsupported;
  if (wantTenant) {
    args.p_tenant_key = tenantKey;
    args.p_tenant_limit = tenantShare(limit);
    args.p_contention_floor = contentionFloor(limit);
  }
  let r = await fetch(client.rest('rpc/' + RPC), {
    method: 'POST',
    headers: client.headers,
    body: JSON.stringify(args)
  });
  // A 404 on the SIX-argument shape means the sub-budget migration has not run;
  // the three-argument function may still be there and is still correct, just
  // not tenant-aware. Fall back to it ONCE rather than dropping all the way to
  // the racy path, which would lose atomicity for a reason that has nothing to
  // do with atomicity.
  if (!r.ok && r.status === 404 && wantTenant) {
    tenantArgsUnsupported = true;
    console.error('ai rate limit: the tenant sub-budget RPC is absent -- run '
      + 'sql/sairn_ai_tenant_subbudget_2026-09-15.sql. Counting per APP only; '
      + 'one tenant can still exhaust the whole app ceiling.');
    r = await fetch(client.rest('rpc/' + RPC), {
      method: 'POST',
      headers: client.headers,
      body: JSON.stringify({ p_app_id: appId, p_limit: limit, p_window_seconds: WINDOW_SECONDS })
    });
  }
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
    // Absent from the 3-arg function's answer, which is why these read as
    // "not sub-budgeted" rather than as zero -- an un-migrated deployment has
    // no tenant counts, and reporting 0 would look like a tenant who has made
    // no calls instead of a question nobody asked.
    limitedBy: (body.limited_by == null ? null : String(body.limited_by)),
    tenantScoped: body.tenant_scoped === true,
    tenantCount: (body.tenant_prior_count == null ? null : Number(body.tenant_prior_count)),
    tenantLimit: (body.tenant_limit == null ? null : Number(body.tenant_limit)),
    counted: true,
    // Added 2026-09-02 with sql/sairn_ai_usage_columns_2026-09-02.sql. Null
    // until that migration is run -- the older RPC simply does not return the
    // key, and the usage recorder treats null as "nothing to attach to".
    rowId: (body.row_id == null ? null : Number(body.row_id))
  };
}

// THE OLD PATH, KEPT ONLY UNTIL THE MIGRATION IS RUN. Still racy by
// construction -- two uncoordinated calls -- and says so in the mode it
// reports.
// THE RACY PATH IS NOT TENANT-AWARE, AND THAT IS REPORTED RATHER THAN HIDDEN.
// Making it so would need a second count and a second insert with nothing
// coordinating them -- more round trips to produce a sub-budget that is
// approximate in exactly the way the atomic fix exists to remove. It counts per
// APP as it always has, and returns tenantScoped:false so a caller can tell the
// difference between "this tenant is within its share" and "nobody looked".
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

  // return=representation rather than minimal, so the inserted id comes back
  // and a usage measurement can be attached to THIS row rather than to
  // whichever row happened to be newest -- guessing the row under concurrency
  // would put one app's token count on another app's request.
  const w = await fetch(client.rest(TABLE + '?select=id'), {
    method: 'POST',
    headers: Object.assign({}, client.headers, { Prefer: 'return=representation' }),
    body: JSON.stringify({ app_id: appId })
  });
  if (!w.ok) console.error('ai rate limit: insert failed, HTTP', w.status);
  let rowId = null;
  try {
    const wRows = w.ok ? await w.json() : null;
    if (Array.isArray(wRows) && wRows[0] && wRows[0].id != null) rowId = Number(wRows[0].id);
  } catch (e) { rowId = null; }

  return { count: exact, limited: exact >= limit, counted: w.ok, rowId: rowId,
           limitedBy: exact >= limit ? 'app' : null,
           tenantScoped: false, tenantCount: null, tenantLimit: null };
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
// tenantKey (2026-09-15) is the caller's `license_hash` -- NEVER the raw licence
// key, which is a bearer secret and must not sit in a log table. Optional: a
// call with no licence is counted against the app and never sub-budgeted, and
// says so in `tenant_scoped`.
async function checkAiRateLimit(appId, tenantKey) {
  const limit = dailyLimit();
  const enforcing = isEnforcing();
  // FAILING OPEN IS THE RIGHT CALL AND IT STAYS. This is a COST control, not a
  // security control -- blocking every AI request in a practice because a
  // counter table is unreachable is worse for the customer than letting the
  // calls through. What was wrong was that it failed open SILENTLY: the only
  // signal was a console.error nobody has open, so an unreachable counter and
  // a healthy one produced byte-identical responses.
  //
  // `degraded` is now part of the answer. It means "this allow is not a
  // decision, it is the absence of one" -- callers surface it the same way
  // api/sc-ai.js already surfaces audited:false rather than implying a log
  // record exists when it does not. Added 2026-09-04.
  const base = {
    limited: false, count: null, limit: limit,
    mode: enforcing ? 'enforce' : 'observe',
    counted: false, allowed: true, atomic: false, rowId: null,
    limited_by: null, tenant_scoped: false, tenant_count: null, tenant_limit: null,
    degraded: true, degraded_reason: 'unknown'
  };

  const client = sb();
  if (!client || !appId) {
    // No Supabase client configured, or no app id to count against. Nothing was
    // counted and nothing could have been.
    console.error('ai rate limit: NOT ENFORCED -- ' +
      (!client ? 'no storage client configured' : 'no app_id supplied') +
      ' (failing open, degraded)');
    return Object.assign({}, base, {
      degraded_reason: !client ? 'no_storage_client' : 'no_app_id'
    });
  }

  try {
    let atomic = true;
    let res = await consumeAtomic(client, appId, limit, tenantKey);
    if (!res) { atomic = false; res = await consumeRacy(client, appId, limit); }
    if (!res) {
      // Both the atomic and the racy path failed to produce a count. The call
      // is allowed, and the caller is told the allow was uncounted.
      console.error('ai rate limit: NOT ENFORCED -- counter unreadable for app_id=' +
        appId + ' (failing open, degraded)');
      return Object.assign({}, base, { degraded_reason: 'counter_unavailable' });
    }

    const mode = (enforcing ? 'enforce' : 'observe') + (atomic ? '' : '-racy');

    if (res.limited) {
      // WHICH limit is in the log line, because "this customer has used its
      // share" and "the whole app is out" are different incidents and lead to
      // different phone calls.
      console.error('ai rate limit ' +
        (enforcing ? 'EXCEEDED (blocking)' : 'would have blocked (observe mode)') +
        ' app_id=' + appId + ' by=' + (res.limitedBy || 'app') +
        ' count=' + res.count + ' limit=' + limit +
        (res.tenantScoped ? ' tenant_count=' + res.tenantCount + ' tenant_limit=' + res.tenantLimit : '') +
        ' atomic=' + atomic);
    }

    return {
      allowed: enforcing ? !res.limited : true,
      limited: res.limited,
      count: res.count,
      limit: limit,
      mode: mode,
      counted: res.counted,
      atomic: atomic,
      // WHICH ceiling stopped it: 'app', 'tenant', or null when nothing did.
      limited_by: res.limitedBy || (res.limited ? 'app' : null),
      // false means this call was NOT sub-budgeted -- no licence on the
      // request, or the migration is not run. Counting those is the whole
      // point: it measures how much traffic is unattributable today, which is
      // the precondition for turning enforcement on.
      tenant_scoped: res.tenantScoped === true,
      tenant_count: (res.tenantCount == null ? null : res.tenantCount),
      tenant_limit: (res.tenantLimit == null ? null : res.tenantLimit),
      // A real count happened, so this allow (or block) IS a decision.
      degraded: false,
      degraded_reason: null,
      // The log row this call created. api/claude.js fills its token columns
      // in after Anthropic answers; null means there is nothing to fill.
      rowId: (res.rowId == null ? null : res.rowId)
    };
  } catch (e) {
    console.error('ai rate limit: NOT ENFORCED -- check errored (failing open, degraded):', e && e.message);
    return Object.assign({}, base, { degraded_reason: 'check_errored' });
  }
}

// Fill in what a call actually cost, on the row checkAiRateLimit() just
// created. Added 2026-09-02: Anthropic returns a `usage` block on every
// successful call and api/claude.js forwarded it to the client without ever
// reading it, so this platform had NO record of how big any AI request was --
// which is why StoneDesk's [0039] token budget is a labelled guess rather than
// a measured number.
//
// A MEASUREMENT, NEVER A CONTROL. Called after the reply is already on its way
// back, never awaited by the response path, and every failure mode -- no
// migration, no client, no row, a refused RPC -- ends in a quiet false. An AI
// feature must not break because a statistic could not be written. Requires
// sql/sairn_ai_usage_columns_2026-09-02.sql; before that runs, the RPC 404s
// and this returns false forever, which is the correct inert state.
async function recordAiUsage(rowId, usage) {
  const client = sb();
  if (!client || rowId == null || !usage) return false;
  const inTok = Number(usage.input_tokens);
  const outTok = Number(usage.output_tokens);
  if (!Number.isFinite(inTok) || !Number.isFinite(outTok)) return false;
  try {
    const r = await fetch(client.rest('rpc/sairn_ai_record_usage'), {
      method: 'POST',
      headers: client.headers,
      body: JSON.stringify({ p_row_id: rowId, p_input_tokens: inTok, p_output_tokens: outTok })
    });
    if (!r.ok) {
      // 404 = migration not run yet. Expected and quiet, same convention as
      // consumeAtomic above; anything else is worth a line in the log.
      if (r.status !== 404) console.error('ai usage: record failed, HTTP', r.status);
      return false;
    }
    return (await r.json().catch(() => false)) === true;
  } catch (e) {
    console.error('ai usage: record errored (ignored):', e && e.message);
    return false;
  }
}

module.exports = { checkAiRateLimit, recordAiUsage, dailyLimit, isEnforcing, tenantShare, contentionFloor, exactCountFrom, consumeAtomic, consumeRacy };
