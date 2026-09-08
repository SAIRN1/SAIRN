// api/claude.js
// Shared Claude proxy for all SAIRN apps (StoneDesk, SAIRNbiz, SAIRNcode, SAIRNvet, and any future app).
// Every app's frontend calls this via PROXY = 'https://sairn.vercel.app/api/claude' — never api.anthropic.com directly.
//
// Request body (from frontend callClaude()): { app_id, is_demo, system, messages, max_tokens }
// Response shape matches the real Anthropic Messages API response so the frontend's existing
// `data.content[0].text` parsing works unchanged: { content: [{ type: "text", text: "..." }], ... }
// On error: { error: "demo_limit" } or { error: { message: "..." } } — frontend already checks both shapes.
//
// REQUIRES: ANTHROPIC_API_KEY set as a Vercel environment variable (Project Settings > Environment
// Variables). Never hardcode the key here — Guardian check 22 blocks any push with a hardcoded key.
//
// KNOWN LIMITATION (flagged, not hidden): demo_limit checking below is a best-effort, in-memory,
// per-instance counter. Serverless functions can run as multiple concurrent instances and reset on
// cold start, so this does NOT reliably cap usage or cost across real traffic. Before this proxy is
// exposed to real demo/customer traffic at scale, replace this with a persistent counter (Vercel KV
// or the Supabase project already used elsewhere in SAIRN) keyed by app_id + day.
//
// CORRECTED 2026-07-26: KNOWN_APP_IDS was missing 9 of 13 live apps (SAIRNscape, SAIRNbuild,
// SAIRNlaw, SAIRNdesign, SAIRNcare, SAIRNfuneral, SAIRNmechanical, SAIRNhr, SAIRNacc) — those apps'
// AI features were returning a 400 "unrecognized app_id" error against this proxy. Cross-referenced
// against sairn-guardian-v2's App File Map (the platform's own source of truth for which apps exist)
// rather than guessing. Guardian's Check 3 now also verifies an app_id exists in THIS list, not just
// that the app's own frontend code includes an app_id — the two are different checks, and only the
// first one was covered before.
//
// Accepts image content blocks in `messages` unmodified — this proxy has always forwarded `messages`
// straight through to the Anthropic API without inspecting shape, so vision (base64 image + text in a
// message) works with zero changes here once an app's frontend sends it in the standard API format.

const { checkAiRateLimit, recordAiUsage } = require('./_lib/ai-rate-limit');
// Phase 1 of the licence-key requirement -- see the block in the handler.
const { validateLicenseKey } = require('./_lib/license');

const KNOWN_APP_IDS = [
  'stonedesk', 'sairnbiz', 'sairnscape', 'sairncode', 'sairnbuild',
  'sairnlaw', 'sairndesign', 'sairncare', 'sairnvet', 'sairnfuneral',
  'sairnmechanical', 'sairnhr', 'sairnacc', 'sairngrounds', 'sairnlegacy',
  // SAIRNcash (2026-08-10) -- pivot from SAIRNtype. Its own callClaude()
  // calls this shared proxy directly (is_demo:false, gated upstream by
  // its own real Stripe subscription check) rather than a duplicate
  // per-app pass-through -- SAIRNtype's original api/claude.js had no
  // app_id allowlist, no rate limiting, and read the wrong env var name
  // (`mykey`); not ported.
  'sairncash',
  // SAIRNdental (2026-08-10) -- for the insurance-card capture flow
  // (docs/superpowers/specs/2026-08-10-sairndental-design.md §1) and
  // any future AI use. Standard license-key-gated B2B app, is_demo
  // used the same way every other non-SAIRNcash app on this platform
  // already does.
  'sairndental',
  // SAIRNsenior (2026-08-20) -- MISSED at build time despite having a real
  // AI Assistant panel calling this proxy with app_id:'sairnsenior' since
  // Phase 1 (3157ac9): every call has been 400ing with "unrecognized
  // app_id" and failing silently into the chat's generic "AI request
  // failed" message. Found while wiring the agentic ops-attention tool --
  // same missing-from-allowlist bug class as the 2026-07-26 correction
  // above, caught live via a direct curl against this proxy before
  // assuming the existing chat worked.
  'sairnsenior',
  // SAIRNfreedom (2026-08-31) -- added at Phase 1 BUILD TIME, not retrofitted
  // after a live 400, which is the standing gap this list has hit twice
  // (the 2026-07-26 nine-app correction and SAIRNsenior above, whose every
  // AI call had been 400ing silently since Phase 1). Phase 1 makes no AI
  // calls yet; the entry is here so the first one that ships cannot fail
  // quietly. NOTE for whoever wires that assistant: spec 0d requires it to
  // REFUSE VA claim-strategy questions in its system prompt -- a refusal,
  // not a disclaimer.
  'sairnfreedom',
  // SAIRNroofing (2026-08-24) -- added at Phase 1 build time, not
  // retrofitted after a live 400, per the standing gap this list has hit
  // twice before (2026-07-26, 2026-08-20). See
  // docs/superpowers/specs/2026-08-24-sairnroofing-v1-scope.md sec.3.
  'sairnroofing'
];

// Server tools a frontend is allowed to request. Server-executed tool TYPES
// are whitelisted by exact type string (not passed through unchecked)
// because this endpoint has no other auth beyond a client-supplied app_id --
// an unrestricted server-tool passthrough would let any caller run billed
// actions (web search) against our Anthropic key. max_uses is also
// server-capped below regardless of what the client sends.
//
// CUSTOM (client-executed) tools are a different risk category, added
// 2026-08-09: Anthropic never executes them -- the model only returns a
// tool_use request naming the tool + arguments, and the calling app decides
// locally whether and how to run it. No cost or external call happens from
// the tool definition alone, so these pass through unmodified rather than
// being type-whitelisted like server tools. A tool counts as "custom" if it
// has no `type` field, or an explicit `type: 'custom'` -- both are valid
// Anthropic custom-tool shapes.
const ALLOWED_SERVER_TOOL_TYPES = ['web_search_20250305'];
const MAX_TOOL_USES_CEILING = 5;

// ── max_tokens IS NOW CAPPED SERVER-SIDE (2026-09-05) ─────────────────────
// It was not, and the comment above -- which says "max_uses is also
// server-capped" -- is about tool USES and was never about tokens.
// callAnthropic() passed `max_tokens || 1000` straight through to Anthropic,
// so any caller could ask for an arbitrarily large generation on this
// platform's own API key. VERIFIED LIVE before fixing, with deliberately
// minimal spend: a request carrying NO Authorization header at all and
// max_tokens 64000 returned HTTP 200 and a real completion.
//
// 4096 is above every real request on the platform, measured rather than
// guessed: the largest max_tokens any app's client sends is 2000, and
// api/sd-agent.js -- the most demanding AI path here, a tool-using agent
// loop -- sets its own MAX_TOKENS to 4096. So nothing legitimate is refused,
// and the ceiling is not silently below somebody's working feature.
//
// CLAMPED, NOT REFUSED. A 400 here would break a caller that is asking for
// something reasonable-but-large; clamping gives it a shorter answer, which
// is the behaviour Anthropic's own max_tokens already has when a model stops
// early. Nothing about the response shape changes.
const MAX_TOKENS_CEILING = 4096;
const DEFAULT_MAX_TOKENS = 1000;

// IN callAnthropic(), NOT in the HTTP handler, and that placement is the
// whole point. THREE paths reach Anthropic through this module: this file's
// own handler, api/law-auth.js:596 and api/sc-ai.js:259 -- and the latter two
// both pass a CLIENT-SUPPLIED `body.max_tokens` through. Capping only the
// HTTP handler would fix the copy that is easiest to see and leave two others
// uncapped, which is this repo's own standing lesson about fixing the copy a
// human invokes and missing the one that runs elsewhere.
// TYPE-CHECKED BEFORE COERCING, and the first version of this function was
// not. `Number(true)` is 1 and `Number([5])` is 5, so a bare Number() test
// accepted a boolean and a single-element array -- `max_tokens: true` came out
// as a ONE-token ceiling and would have truncated a real answer to nothing.
// Found by probing the function rather than by reading it. This is verbatim
// the trap api/_lib/dental-ledger.js's isPositiveMoney() already documents on
// this platform; the lesson existed and I repeated the bug anyway, which is
// why it is written here too rather than only there.
//
// A non-finite or nonsensical value falls back to the DEFAULT rather than to
// the ceiling: garbage in should not buy the largest generation available.
function cappedMaxTokens(requested) {
  if (typeof requested !== 'number' && typeof requested !== 'string') {
    return DEFAULT_MAX_TOKENS;
  }
  const n = Number(requested);
  if (!Number.isFinite(n) || n <= 0) return DEFAULT_MAX_TOKENS;
  return Math.min(Math.floor(n), MAX_TOKENS_CEILING);
}

function sanitizeTools(tools) {
  if (!Array.isArray(tools)) return undefined;
  const clean = tools
    .filter((t) => t && (t.type === undefined || t.type === 'custom' || ALLOWED_SERVER_TOOL_TYPES.includes(t.type)))
    .map((t) => {
      if (t.type === undefined || t.type === 'custom') return t;
      const out = { type: t.type, name: t.name || 'web_search' };
      const requested = Number(t.max_uses) || MAX_TOOL_USES_CEILING;
      out.max_uses = Math.max(1, Math.min(requested, MAX_TOOL_USES_CEILING));
      return out;
    });
  return clean.length ? clean : undefined;
}

// Best-effort only — see limitation note above. Resets on cold start / differs per instance.
const demoCallCounts = {};
const DEMO_DAILY_LIMIT = 200;

function getDemoKey(appId) {
  const day = new Date().toISOString().slice(0, 10);
  return appId + '|' + day;
}

// Extracted (2026-08-13, SAIRNlaw AI Chain of Custody server-side capture) so
// api/law-auth.js's ai_generate action can call the real Anthropic API
// in-process -- one real server round trip that also writes the audit log,
// not a second HTTP hop back through this same endpoint. Returns a plain
// result object, never throws, so every caller (this file's own HTTP
// handler below, and api/law-auth.js) handles success/failure the same way.
async function callAnthropic({ system, messages, max_tokens, tools }) {
  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) {
    // Server misconfiguration — do not leak details to the client, but make it loud in logs.
    console.error('ANTHROPIC_API_KEY is not set in environment variables');
    return { ok: false, status: 500, error: { message: 'Server configuration error — contact support' } };
  }
  try {
    const anthropicRes = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': apiKey,
        'anthropic-version': '2023-06-01'
      },
      body: JSON.stringify({
        model: 'claude-sonnet-4-6',
        max_tokens: cappedMaxTokens(max_tokens),
        system: system || undefined,
        messages: messages,
        tools: sanitizeTools(tools)
      })
    });

    const data = await anthropicRes.json();

    if (!anthropicRes.ok) {
      const message = (data && data.error && data.error.message) ? data.error.message : ('Anthropic API error ' + anthropicRes.status);
      return { ok: false, status: anthropicRes.status, error: { message } };
    }

    return { ok: true, status: 200, data };
  } catch (err) {
    console.error('api/claude proxy error:', err);
    return { ok: false, status: 502, error: { message: 'Upstream connection error — try again' } };
  }
}

async function claudeProxyHandler(req, res) {
  if (req.method !== 'POST') {
    res.status(405).json({ error: { message: 'Method not allowed — POST only' } });
    return;
  }

  // ── THE BODY IS PARSED HERE BUT NOT REFUSED HERE (2026-09-05) ───────────
  // This file gained a licence check the same day, and putting it below the
  // envelope gate reintroduced, in the one endpoint that spends money, exactly
  // the shape just removed from twenty-nine others: an unauthenticated caller
  // could tell malformed JSON from a missing body from a bad licence by which
  // refusal came back. tools/preauth_oracle_check.py caught it, and it was MY
  // Phase 1 placement that put it there.
  //
  // It cannot simply move below the auth block, because that block's whole
  // purpose is a per-app_id log line and app_id lives in the body. So the
  // parse happens first and the REFUSAL is deferred: nothing is answered until
  // the caller is known.
  let body = req.body;
  let envelopeProblem = null;
  if (typeof body === 'string') {
    try { body = JSON.parse(body); } catch (e) { envelopeProblem = 'Invalid JSON body'; }
  }
  if (!envelopeProblem && (!body || typeof body !== 'object')) {
    envelopeProblem = 'Missing request body';
  }
  // Never let a bad body throw before the auth block reads app_id off it.
  if (!body || typeof body !== 'object') body = {};

  // ── PHASE 1 OF THE LICENCE-KEY REQUIREMENT (2026-09-05) ──────────────────
  // This endpoint requires no credential. That is the finding of 2026-09-05,
  // confirmed live: a request with no Authorization header returned 200 and a
  // real completion on this platform's own Anthropic key.
  //
  // THE FIX IS BREAKING -- roughly 134 call sites across 16 apps send no auth
  // header today -- so it ships in the shape this platform already uses for
  // SAIRN_AI_RATE_LIMIT_MODE: OBSERVE FIRST, MEASURE, THEN ENFORCE, behind an
  // env flag that can be reverted in seconds without a deploy.
  //
  // IN OBSERVE MODE NOTHING IS REFUSED. The point of this block is the log
  // line: it is what tells us, per app_id, whether the clients have actually
  // caught up. Phase 4's gate is that measurement -- NOT a checklist of files
  // edited, because the call site nobody found is exactly what a file
  // checklist cannot see. See docs/2026-09-05-claude-proxy-auth-rollout.md.
  //
  // `absent` and `invalid` are recorded as DIFFERENT states on purpose. Absent
  // means a client that never sends one -- possibly a surface with no licence
  // to send, which needs a different answer than a bug. Invalid means it tried
  // and the key is wrong. Collapsing them would hide the case that changes the
  // plan.
  const claudeAuthMode = String(process.env.SAIRN_CLAUDE_AUTH_MODE || 'observe')
    .trim().toLowerCase();
  const claudeAuthz = req.headers['authorization'] || '';
  const claudeLicenceKey = claudeAuthz.startsWith('Bearer ')
    ? claudeAuthz.slice(7).trim() : null;
  let authState = 'absent';
  if (claudeLicenceKey) {
    try {
      const lic = await validateLicenseKey(claudeLicenceKey);
      authState = lic.valid ? (lic.active ? 'valid' : 'inactive') : 'invalid';
    } catch (err) {
      // FAILS OPEN, and says so. An unreachable licence store must not take
      // down every AI feature on the platform -- the same standard every other
      // gate here holds. In enforce mode this is the one path that still
      // allows, because refusing on OUR outage punishes the customer for it.
      authState = 'error';
      console.error('api/claude auth check failed (allowing): ' + err.message);
    }
  }
  console.log('api/claude auth_observe app_id=' + (body.app_id || '(none)') +
    ' state=' + authState + ' mode=' + claudeAuthMode);
  if (claudeAuthMode === 'enforce' && (authState === 'absent' || authState === 'invalid')) {
    res.status(401).json({ error: { code: 'NO_LICENSE',
      message: 'A valid license key is required. Send it as Authorization: Bearer <key>.' } });
    return;
  }

  // THE DEFERRED ENVELOPE REFUSAL, answered only now that the caller is known.
  // In observe mode this is the same 400 as before and nothing has changed for
  // any live app; in enforce mode an unauthenticated caller has already been
  // refused above and never reaches it, which is the whole point.
  if (envelopeProblem) {
    res.status(400).json({ error: { message: envelopeProblem } });
    return;
  }

  const { app_id, is_demo, system, messages, max_tokens, tools } = body;
  // The rate-limit log row this request creates, if any. Declared here so the
  // usage recorder below can see it after the is_demo block has closed.
  let usageRowId = null;
  let rateLimitDegraded = false;
  let rateLimitDegradedReason = null;

  if (!app_id || !KNOWN_APP_IDS.includes(app_id)) {
    res.status(400).json({ error: { message: 'Missing or unrecognized app_id' } });
    return;
  }
  if (!messages || !Array.isArray(messages) || messages.length === 0) {
    res.status(400).json({ error: { message: 'messages array is required' } });
    return;
  }

  if (is_demo) {
    // In-memory pre-check, kept deliberately, and kept INSIDE the is_demo
    // branch on purpose while the real limiter below moved out. Two reasons:
    // it is per-instance and documented unreliable, so it was never the
    // control that mattered; and its refusal shape is `{error:'demo_limit'}`,
    // which is the demo contract 17 apps parse. Returning that to a paying
    // SAIRNcash call -- the one path that legitimately sends is_demo:false --
    // would be a wrong and confusing message about a real subscription.
    const key = getDemoKey(app_id);
    demoCallCounts[key] = (demoCallCounts[key] || 0) + 1;
    if (demoCallCounts[key] > DEMO_DAILY_LIMIT) {
      res.status(200).json({ error: 'demo_limit' });
      return;
    }
  }

  // ── THE REAL LIMITER NOW RUNS FOR EVERY REQUEST (2026-09-05) ─────────────
  // It used to sit inside `if (is_demo)`, and `is_demo` COMES FROM THE REQUEST
  // BODY. So the one persistent, cross-instance cost control on this endpoint
  // could be switched off by the caller: send is_demo:false and both limiters
  // were skipped entirely, straight through to Anthropic on this platform's
  // own API key. A control a client can opt out of is not a control.
  //
  // BE CLEAR ABOUT WHAT THIS DOES AND DOES NOT DO TODAY. The limiter ships in
  // OBSERVE mode (SAIRN_AI_RATE_LIMIT_MODE), so `allowed` is currently always
  // true and it fails open besides -- it is a COST control, not a security
  // control, and that stays. Moving it here does not refuse anything today.
  // What it does is make the control REACHABLE on every path, so that when
  // enforcement is switched on it cannot be bypassed by a flag the caller
  // sets. Without this, flipping to enforce would have capped honest demo
  // traffic while leaving anyone who sends is_demo:false completely uncapped
  // -- the limit would have looked real and protected nothing.
  //
  // IT ALSO CLOSES THE FILE'S OWN "HONEST SCOPE" GAP further down: usageRowId
  // only ever existed on the demo path, so a non-demo call was absent from the
  // usage table entirely rather than present with null tokens. Now every call
  // that gets a row gets its cost recorded.
  const rl = await checkAiRateLimit(app_id);
  if (!rl.allowed) {
    // The demo contract is preserved exactly for demo callers. A non-demo
    // caller gets a real 429 instead, because telling a paying subscriber they
    // hit a "demo limit" would be false.
    if (is_demo) {
      res.status(200).json({ error: 'demo_limit' });
    } else {
      res.status(429).json({ error: { code: 'AI_RATE_LIMIT',
        message: 'This app has reached its AI request limit for today. Try again tomorrow.' } });
    }
    return;
  }
  usageRowId = rl.rowId;
  // The limiter fails OPEN by design -- it is a cost control, not a security
  // control -- but until 2026-09-04 it did so silently, so an unreachable
  // counter and a healthy one produced identical responses. `degraded` says
  // the allow was the ABSENCE of a decision rather than one. Recorded on the
  // response the same way api/sc-ai.js reports `audited`.
  rateLimitDegraded = !!rl.degraded;
  rateLimitDegradedReason = rl.degraded_reason || null;
  if (rateLimitDegraded) {
    console.error('api/claude: AI rate limit NOT ENFORCED for app_id=' + app_id +
      ' (' + rateLimitDegradedReason + ') -- request allowed');
  }

  const result = await callAnthropic({ system, messages, max_tokens, tools });
  if (!result.ok) {
    res.status(result.status).json({ error: result.error });
    return;
  }
  // Added to result.data IN PLACE rather than to a copy, deliberately. Two
  // guarantees downstream are asserted against this exact source shape:
  // api/_lib/ai-usage.test.js checks that `res.status(200).json(result.data);`
  // appears BEFORE `recordAiUsage(usageRowId`, which is how the platform
  // guarantees a statistic can never delay a customer's reply. Responding with
  // a different object would have quietly broken that check, and the two extra
  // keys do not affect result.data.usage, which is all the recorder reads.
  if (rateLimitDegraded && result.data && typeof result.data === 'object') {
    result.data.rate_limit_degraded = true;
    result.data.rate_limit_degraded_reason = rateLimitDegradedReason || 'unknown';
  }
  res.status(200).json(result.data);

  // ── RECORD WHAT THIS ACTUALLY COST (2026-09-02) ───────────────────────────
  // Anthropic returns `usage: { input_tokens, output_tokens }` on every
  // successful call, and this proxy has forwarded it to the client since the
  // day it was written WITHOUT EVER READING IT. So the platform had no record
  // of how big any AI request was, which is why StoneDesk's [0039] token
  // budget had to ship as a labelled guess -- there was nothing to measure.
  //
  // AFTER res.json(), and deliberately NOT awaited: this is a statistic, and a
  // statistic must never be able to delay or fail a reply. recordAiUsage()
  // swallows everything, including the 404 it returns until
  // sql/sairn_ai_usage_columns_2026-09-02.sql is run.
  //
  // HONEST SCOPE: usageRowId only exists when is_demo was true, because that
  // is the only path that writes a log row. Ten of eleven live apps send
  // is_demo:true, so this covers most traffic and not all of it -- a non-demo
  // call is absent from the table entirely rather than present with null
  // tokens. Do not read this table as total platform AI volume.
  if (usageRowId != null && result.data && result.data.usage) {
    try { void recordAiUsage(usageRowId, result.data.usage); } catch (e) {}
  }
}

claudeProxyHandler.sanitizeTools = sanitizeTools;
claudeProxyHandler.callAnthropic = callAnthropic;
claudeProxyHandler.getDemoKey = getDemoKey;
claudeProxyHandler.demoCallCounts = demoCallCounts;
claudeProxyHandler.DEMO_DAILY_LIMIT = DEMO_DAILY_LIMIT;
claudeProxyHandler.cappedMaxTokens = cappedMaxTokens;
claudeProxyHandler.MAX_TOKENS_CEILING = MAX_TOKENS_CEILING;
module.exports = claudeProxyHandler;
