# SAIRNlaw AI Chain of Custody — Server-Side Capture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move AI-interaction logging for all 5 real AI call sites in SAIRNlaw into the same server-side request path that calls Claude, so a response can never reach the rep without a genuine, server-written log entry already existing — closing both the capture gap (a second, unlinked client request that might never fire) and the fabrication risk (a still-open action that accepted an arbitrary client-supplied prompt/response pair).

**Architecture:** Extract `callAnthropic()` (plus the existing demo-rate-limit helpers) out of `api/claude.js` into exported functions, used unchanged by that file's existing HTTP handler (17 other apps, zero behavior change) and newly by a session-authenticated `ai_generate` action added to `api/law-auth.js`. That action calls Claude, and — only when the response is final user-facing text, never on an intermediate tool-use directive — writes the audit-log entry itself before returning the response; a failed write returns a real error instead of the AI text. The standalone `ai_log` action (Phase 1) is removed. All 5 client call sites switch from `fetch(PROXY, ...)` to this new action.

**Tech Stack:** Vercel serverless functions (Node, `api/*.js`), vanilla JS client (`sairnlaw.html`).

## Global Constraints

- **`api/claude.js`'s existing HTTP handler must remain byte-identical in behavior for its other 17 callers** — same `KNOWN_APP_IDS` gate, same demo-limit counting, same error shapes. Verified by re-running the existing `api/_lib/claude.test.js` (8 assertions on `sanitizeTools()`) unchanged, plus a live spot-check of one other app's AI feature.
- **The demo-rate-limit gate (`is_demo`, `DEMO_DAILY_LIMIT`, `getDemoKey`, `demoCallCounts`) must be preserved for SAIRNlaw's traffic, not silently dropped.** `sendAI()` and its siblings already send `is_demo:true` today — that's the existing cap on SAIRNlaw's own AI usage (200 calls/app/day), not a "this is a demo account" flag. Since `ai_generate` calls `callAnthropic()` directly rather than going through `claudeProxyHandler`'s existing gate, it must replicate the exact same check using the exact same shared counter (`demoCallCounts`, exported alongside `callAnthropic`) — not a second, independent counter that could double- or under-count against the same daily cap.
- **`ai_generate` only writes a log entry when Claude returns final text, never on a `tool_use`-only response.** A tool-use directive has produced nothing user-facing yet — logging it would double-log the same real exchange once its second leg completes, and doesn't match Phase 1's existing one-entry-per-exchange data model (`tools_used` is metadata on the one entry for the full exchange, not a separate entry per API call).
- **What gets logged as `prompt` is the real, per-function user-turn content actually sent to Claude for that specific call** — not the (constant, non-per-interaction) system prompt, and not sendAI()'s full running chat history (each turn already gets its own log entry with that turn's real content; earlier turns already have their own entries). Exact per-function definition:
  - `sendAI()`: `q` (the rep's typed question for this turn) — unchanged from Phase 1, this was never the under-informative part.
  - `runAiDraft()`: `'Matter context: '+context+'\n\nRequest: '+request` (the exact string already sent as the user message) — matter facts included, per the design spec's decision.
  - `reviewDocument()`: `'Please review this document:\n\n'+d.content_text` (the exact string already sent) — the real document text included.
  - `explainReconciliation()`: the exact real reconciliation-numbers string already constructed and sent.
- **`employee_id`/`role` on every log entry remain session-derived** (`caller.employee_id`/`caller.role`), never client-supplied — unchanged security posture from Phase 1.
- **Write failure blocks the response** — `ai_generate` must not return Claude's real text to the client on a failed audit-log write. Matches `LOG_WRITE_FAILED`'s existing 502 shape from Phase 1.
- `node --check` must pass on every touched `.js` file; whatever syntax-check tooling applies to `sairnlaw.html` (established in the prior plan: `python tools/checkblocks.py sairnlaw.html`) must show zero failures.
- Never bulk find-replace. Every edit below is a targeted, unique-context change.
- Real, DB-backed verification uses the already-provisioned `LAW-TEST-2026` test license (`sql/sairnlaw_test_license_seed.sql`, already run and live-verified this session) — not simulated.

---

## File Structure

| File | Responsibility for this feature |
|---|---|
| `api/claude.js` | Extract `callAnthropic()` + demo-limit helpers into exported functions; `claudeProxyHandler` becomes a thin wrapper calling them — behavior-identical for its 17 other callers. |
| `api/law-auth.js` | New `action: 'ai_generate'` (replaces `ai_log`'s role); `ai_log` removed entirely from `ACTIONS` and its handler. |
| `sairnlaw.html` | `sendAI()` (both legs), `explainReconciliation()`, `runAiDraft()`, `reviewDocument()` switch from `fetch(PROXY,...)` to `lawAuth('ai_generate',...)`; `lawLogAiInteraction()` and its two call sites removed. |

Line numbers below are as of this plan's base commit and will drift as earlier tasks land — every edit is anchored to unique surrounding code, not the raw number.

---

### Task 1: `api/claude.js` — extract `callAnthropic()` and the demo-limit helpers

**Files:**
- Modify: `api/claude.js`

**Interfaces:**
- Produces: `async function callAnthropic({system, messages, max_tokens, tools})` returning `{ok:true, status:200, data}` on success or `{ok:false, status, error:{message}}` on any failure (config error, non-ok Anthropic response, or network error) — never throws. Also exports `getDemoKey(appId)`, `demoCallCounts` (the shared in-memory counter object), `DEMO_DAILY_LIMIT` — all attached to `claudeProxyHandler` alongside the existing `sanitizeTools`, matching this file's own established export pattern (confirmed real via `api/_lib/claude.test.js`'s existing `const { sanitizeTools } = require('../claude.js');`).
- Consumed by: Task 2's `ai_generate` action.

- [ ] **Step 1: Extract `callAnthropic()` and update the handler to use it**

Find (the exact current file, from the handler's start through its Anthropic-calling block):

```js
async function claudeProxyHandler(req, res) {
  if (req.method !== 'POST') {
    res.status(405).json({ error: { message: 'Method not allowed — POST only' } });
    return;
  }

  let body = req.body;
  if (typeof body === 'string') {
    try { body = JSON.parse(body); } catch (e) {
      res.status(400).json({ error: { message: 'Invalid JSON body' } });
      return;
    }
  }
  if (!body || typeof body !== 'object') {
    res.status(400).json({ error: { message: 'Missing request body' } });
    return;
  }

  const { app_id, is_demo, system, messages, max_tokens, tools } = body;

  if (!app_id || !KNOWN_APP_IDS.includes(app_id)) {
    res.status(400).json({ error: { message: 'Missing or unrecognized app_id' } });
    return;
  }
  if (!messages || !Array.isArray(messages) || messages.length === 0) {
    res.status(400).json({ error: { message: 'messages array is required' } });
    return;
  }

  if (is_demo) {
    const key = getDemoKey(app_id);
    demoCallCounts[key] = (demoCallCounts[key] || 0) + 1;
    if (demoCallCounts[key] > DEMO_DAILY_LIMIT) {
      res.status(200).json({ error: 'demo_limit' });
      return;
    }
  }

  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) {
    // Server misconfiguration — do not leak details to the client, but make it loud in logs.
    console.error('ANTHROPIC_API_KEY is not set in environment variables');
    res.status(500).json({ error: { message: 'Server configuration error — contact support' } });
    return;
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
        max_tokens: max_tokens || 1000,
        system: system || undefined,
        messages: messages,
        tools: sanitizeTools(tools)
      })
    });

    const data = await anthropicRes.json();

    if (!anthropicRes.ok) {
      const message = (data && data.error && data.error.message) ? data.error.message : ('Anthropic API error ' + anthropicRes.status);
      res.status(anthropicRes.status).json({ error: { message } });
      return;
    }

    res.status(200).json(data);
  } catch (err) {
    console.error('api/claude proxy error:', err);
    res.status(502).json({ error: { message: 'Upstream connection error — try again' } });
  }
}

claudeProxyHandler.sanitizeTools = sanitizeTools;
module.exports = claudeProxyHandler;
```

Replace with:

```js
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
        max_tokens: max_tokens || 1000,
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

  let body = req.body;
  if (typeof body === 'string') {
    try { body = JSON.parse(body); } catch (e) {
      res.status(400).json({ error: { message: 'Invalid JSON body' } });
      return;
    }
  }
  if (!body || typeof body !== 'object') {
    res.status(400).json({ error: { message: 'Missing request body' } });
    return;
  }

  const { app_id, is_demo, system, messages, max_tokens, tools } = body;

  if (!app_id || !KNOWN_APP_IDS.includes(app_id)) {
    res.status(400).json({ error: { message: 'Missing or unrecognized app_id' } });
    return;
  }
  if (!messages || !Array.isArray(messages) || messages.length === 0) {
    res.status(400).json({ error: { message: 'messages array is required' } });
    return;
  }

  if (is_demo) {
    const key = getDemoKey(app_id);
    demoCallCounts[key] = (demoCallCounts[key] || 0) + 1;
    if (demoCallCounts[key] > DEMO_DAILY_LIMIT) {
      res.status(200).json({ error: 'demo_limit' });
      return;
    }
  }

  const result = await callAnthropic({ system, messages, max_tokens, tools });
  if (!result.ok) {
    res.status(result.status).json({ error: result.error });
    return;
  }
  res.status(200).json(result.data);
}

claudeProxyHandler.sanitizeTools = sanitizeTools;
claudeProxyHandler.callAnthropic = callAnthropic;
claudeProxyHandler.getDemoKey = getDemoKey;
claudeProxyHandler.demoCallCounts = demoCallCounts;
claudeProxyHandler.DEMO_DAILY_LIMIT = DEMO_DAILY_LIMIT;
module.exports = claudeProxyHandler;
```

- [ ] **Step 2: Run node --check**

Run: `node --check api/claude.js`
Expected: clean exit, no output.

- [ ] **Step 3: Re-run the existing test file — must still pass unchanged**

Run: `node api/_lib/claude.test.js`
Expected: `8 passed` (identical to the baseline — this refactor doesn't touch `sanitizeTools()`'s logic, only where it's called from).

- [ ] **Step 4: Manual verification (Node REPL or a small throwaway script)**

```js
const claude = require('./api/claude.js');
typeof claude.callAnthropic;      // -> 'function'
typeof claude.getDemoKey;         // -> 'function'
typeof claude.demoCallCounts;     // -> 'object'
typeof claude.DEMO_DAILY_LIMIT;   // -> 'number'
typeof claude.sanitizeTools;      // -> 'function' (unchanged, confirms nothing was lost)
```

Expected: matches every comment — all five are real exported functions/values on the module.

- [ ] **Step 5: Commit**

```bash
git add api/claude.js
git commit -m "feat: SAIRNlaw AI Chain of Custody -- extract callAnthropic() and demo-limit helpers from api/claude.js"
```

---

### Task 2: `api/law-auth.js` — `ai_generate` action, remove `ai_log`

**Files:**
- Modify: `api/law-auth.js` (requires ~L87; `ACTIONS` ~L104-109; the `ai_log` block ~L482-501)

**Interfaces:**
- Consumes: `callAnthropic`, `getDemoKey`, `demoCallCounts`, `DEMO_DAILY_LIMIT` (Task 1).
- Produces: `action: 'ai_generate'` (POST body: `{system, messages, max_tokens, tools (optional), matter_id}`, session required, any role) — consumed by Task 3/4's client call sites. `action: 'ai_log'` is REMOVED — no longer a valid action.

- [ ] **Step 1: Import the extracted functions**

Find (around line 87-97):

```js
const { validateLicenseKey } = require('./_lib/license');
const { writeAuditLog } = require('./_lib/audit');
const {
  hashPin, verifyPin, signSessionToken, verifySessionToken, tokenFromRequest,
  signPreAuthToken, verifyPreAuthToken,
  generateTotpSecret, verifyTotpCode, totpProvisioningUri,
  encryptSecret, decryptSecret,
  oidcConfigured, generatePkcePair, oidcDiscoverEndpoints, oidcAuthorizationUrl,
  oidcExchangeCode, oidcVerifyIdToken, signSsoState, verifySsoState,
  ROLES_BY_APP
} = require('./_lib/auth');
```

Replace with:

```js
const { validateLicenseKey } = require('./_lib/license');
const { writeAuditLog } = require('./_lib/audit');
const {
  hashPin, verifyPin, signSessionToken, verifySessionToken, tokenFromRequest,
  signPreAuthToken, verifyPreAuthToken,
  generateTotpSecret, verifyTotpCode, totpProvisioningUri,
  encryptSecret, decryptSecret,
  oidcConfigured, generatePkcePair, oidcDiscoverEndpoints, oidcAuthorizationUrl,
  oidcExchangeCode, oidcVerifyIdToken, signSsoState, verifySsoState,
  ROLES_BY_APP
} = require('./_lib/auth');
// AI Chain of Custody server-side capture (2026-08-13): callAnthropic() and
// the demo-limit helpers are the SAME functions/counter api/claude.js's own
// HTTP handler uses for every other app -- imported directly (an in-process
// function call, not a second HTTP round trip back through that endpoint),
// so SAIRNlaw's existing is_demo daily-call cap is preserved exactly, not
// silently dropped or double-counted against a second, independent counter.
const { callAnthropic, getDemoKey, demoCallCounts, DEMO_DAILY_LIMIT } = require('./claude.js');
```

- [ ] **Step 2: Update `ACTIONS` — remove `ai_log`, add `ai_generate`**

Find (around line 104-109):

```js
const ACTIONS = [
  'check_license', 'bootstrap', 'login', 'setup',
  'mfa_setup', 'mfa_enable', 'mfa_verify', 'mfa_reset',
  'sso_start', 'sso_callback', 'audit_read',
  'ai_log', 'ai_list', 'ai_review', 'ai_reject', 'ai_used_in_filing'
];
```

Replace with:

```js
const ACTIONS = [
  'check_license', 'bootstrap', 'login', 'setup',
  'mfa_setup', 'mfa_enable', 'mfa_verify', 'mfa_reset',
  'sso_start', 'sso_callback', 'audit_read',
  'ai_generate', 'ai_list', 'ai_review', 'ai_reject', 'ai_used_in_filing'
];
```

- [ ] **Step 3: Replace the `ai_log` handler with `ai_generate`**

Find (the full existing block, around line 482-501):

```js
    // ── AI CHAIN OF CUSTODY (2026-08-13) ────────────────────────────────
    // Extends sairnlaw_audit_log (see sql/sairnlaw_ai_chain_of_custody.sql)
    // rather than a new table -- the existing grant/revoke on that table
    // already makes every row here immutable at the database level.
    if (action === 'ai_log') {
      const caller = verifySessionToken(tokenFromRequest(req), licHash, APP);
      if (!caller) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in required' } }); return; }
      const prompt = String(body.prompt || '').slice(0, AI_PROMPT_RESPONSE_CAP);
      const response = String(body.response || '').slice(0, AI_PROMPT_RESPONSE_CAP);
      if (!prompt || !response) { res.status(400).json({ error: { message: 'prompt and response are both required' } }); return; }
      const matter_id = body.matter_id ? String(body.matter_id) : 'general';
      const tools_used = Array.isArray(body.tools_used) ? body.tools_used.map(String) : [];
      const logged = await audit('ai_interaction', { employee_id: caller.employee_id, role: caller.role, detail: { prompt, response, matter_id, tools_used } });
      if (!logged) {
        res.status(502).json({ error: { code: 'LOG_WRITE_FAILED', message: 'Could not write to the AI Chain of Custody log — try again' } });
        return;
      }
      res.status(200).json({ ok: true });
      return;
    }
```

Replace with:

```js
    // ── AI CHAIN OF CUSTODY -- SERVER-SIDE CAPTURE (2026-08-13) ─────────
    // Replaces ai_log. The old design let the client submit an arbitrary
    // prompt/response pair as a SEPARATE, unlinked request after the AI
    // answer had already rendered -- a real capture gap (the second
    // request might never fire) and a real fabrication gap (nothing tied
    // a logged pair to a real Claude call). This action calls Claude
    // itself and writes the log entry from the REAL response it just
    // received, BEFORE the client ever sees that text -- a response
    // literally cannot reach the rep without a genuine log entry already
    // existing. See docs/superpowers/specs/2026-08-13-sairnlaw-ai-chain-of-
    // custody-server-side-capture-design.md.
    if (action === 'ai_generate') {
      const caller = verifySessionToken(tokenFromRequest(req), licHash, APP);
      if (!caller) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in required' } }); return; }
      const messages = Array.isArray(body.messages) ? body.messages : null;
      if (!messages || !messages.length) { res.status(400).json({ error: { message: 'messages array is required' } }); return; }

      // Same is_demo daily-cap gate api/claude.js's own HTTP handler applies
      // to every other app -- same shared counter, same 200-ish daily limit,
      // preserved exactly rather than silently dropped for this path.
      const key = getDemoKey('sairnlaw');
      demoCallCounts[key] = (demoCallCounts[key] || 0) + 1;
      if (demoCallCounts[key] > DEMO_DAILY_LIMIT) {
        res.status(200).json({ error: 'demo_limit' });
        return;
      }

      const result = await callAnthropic({ system: body.system, messages: messages, max_tokens: body.max_tokens, tools: body.tools });
      if (!result.ok) {
        res.status(result.status).json({ error: result.error });
        return;
      }

      const blocks = (result.data && result.data.content) || [];
      const toolUse = blocks.filter(function (b) { return b.type === 'tool_use'; })[0];
      if (toolUse) {
        // Intermediate tool-use directive -- nothing user-facing yet, so
        // there is nothing real to log. The client executes the tool
        // locally (unchanged; tool data is law_* localStorage, not
        // server-accessible) and calls this same action again with the
        // tool result appended to `messages` for the second, final leg.
        res.status(200).json(result.data);
        return;
      }

      // Final text -- the only case a rep ever actually sees output.
      const responseText = (blocks[0] && blocks[0].text) || '';
      const prompt = String(body.prompt_for_log || '').slice(0, AI_PROMPT_RESPONSE_CAP);
      const response = responseText.slice(0, AI_PROMPT_RESPONSE_CAP);
      const matter_id = body.matter_id ? String(body.matter_id) : 'general';
      const tools_used = Array.isArray(body.tools_used) ? body.tools_used.map(String) : [];
      const logged = await audit('ai_interaction', { employee_id: caller.employee_id, role: caller.role, detail: { prompt, response, matter_id, tools_used } });
      if (!logged) {
        res.status(502).json({ error: { code: 'LOG_WRITE_FAILED', message: 'Could not write to the AI Chain of Custody log — the AI response was generated but is being withheld until this is logged. Try again.' } });
        return;
      }
      res.status(200).json(result.data);
      return;
    }
```

Note: `prompt_for_log` is a distinct field from `messages` — the caller sends the full `messages` array (what Claude actually needs) AND a separate `prompt_for_log` string (the real, per-function prompt content defined in this plan's Global Constraints) so the server logs exactly the intended per-function text without needing to re-derive it from `messages`' shape (which differs: a plain string for most calls, a `tool_result` content-block array for sendAI()'s second leg).

- [ ] **Step 4: Run node --check**

Run: `node --check api/law-auth.js`
Expected: clean exit, no output.

- [ ] **Step 5: Manual verification (real API, using `LAW-TEST-2026`)**

Using the same bootstrap/login flow already proven live this session (a fresh `bootstrap` call works if credentials from the earlier verification session are no longer available, or reuse the existing `coc-verify` session token if still valid):

```bash
curl -s -X POST https://sairn.vercel.app/api/law-auth -H "Content-Type: application/json" -H "Authorization: Bearer LAW-TEST-2026" -H "X-SD-Auth: <token>" \
  -d '{"action":"ai_generate","system":"You are a helpful assistant.","messages":[{"role":"user","content":"Say the word VERIFIED and nothing else."}],"max_tokens":50,"prompt_for_log":"Say the word VERIFIED and nothing else.","matter_id":"general","tools_used":[]}'
# Expected: 200, real Anthropic response shape ({content:[{type:'text',text:'VERIFIED'}], ...})

curl -s -X POST https://sairn.vercel.app/api/law-auth -H "Content-Type: application/json" -H "Authorization: Bearer LAW-TEST-2026" -H "X-SD-Auth: <token>" \
  -d '{"action":"ai_list","limit":5}'
# Expected: the new entry present, prompt/response matching what was sent, status:"unreviewed"

curl -s -X POST https://sairn.vercel.app/api/law-auth -H "Content-Type: application/json" -H "Authorization: Bearer LAW-TEST-2026" \
  -d '{"action":"ai_log","prompt":"x","response":"y"}'
# Expected: 400 "action must be one of: ..." -- ai_log is genuinely gone
```

- [ ] **Step 6: Commit**

```bash
git add api/law-auth.js
git commit -m "feat: SAIRNlaw AI Chain of Custody -- ai_generate (server-side capture), remove ai_log"
```

---

### Task 3: Client — `sendAI()` (both legs)

**Files:**
- Modify: `sairnlaw.html` (`lawLogAiInteraction()` + `sendAI()` ~L1554-1662)

**Interfaces:**
- Consumes: `action: 'ai_generate'` (Task 2), `lawAuth()` (existing).
- Removes: `lawLogAiInteraction()` — no longer needed, logging is server-side now.

- [ ] **Step 1: Remove `lawLogAiInteraction()`, update `sendAI()` to call `ai_generate`**

Find (the full current block, `lawLogAiInteraction()` through the end of `sendAI()`, around line 1554-1662):

```js
function askAI(q){$('ainp').value=q;sendAI();}
// AI Chain of Custody (2026-08-13): fire-and-forget from sendAI()'s point of
// view -- a logging failure must never block or hide the AI response the
// rep already received (same "best-effort" posture writeAuditLog() itself
// documents), but it IS surfaced honestly via toast, not silently
// swallowed, matching this platform's established saveOk-style discipline
// rather than an empty catch(e){}.
// matter (added 2026-08-13) is captured by the CALLER at send time, not
// re-read from the DOM here -- see sendAI()'s "sentMatter" capture. Reading
// $('aimatter').value at LOG time (after the AI round-trip, 5-15+ seconds
// later) let a rep change the matter dropdown mid-request and silently
// misattribute the interaction to the wrong matter, which is unacceptable
// for an evidentiary/audit record.
function lawLogAiInteraction(prompt,response,toolsUsed,matter){
  lawAuth('ai_log',{prompt:prompt,response:response,matter_id:matter||'general',tools_used:toolsUsed||[]},true)
    .then(function(r){ if(!r.ok) toast('AI interaction was not logged to the Chain of Custody record — ' + (r.msg||'try again')); })
    .catch(function(){ toast('AI interaction was not logged to the Chain of Custody record — network error'); });
}
async function sendAI(){
  var inp=$('ainp'),q=(inp.value||'').trim();
  if(!q)return;
  var matterSel=$('aimatter');
  if(matterSel && !matterSel.value){ toast('Select a matter (or "General") before sending — required for the AI Chain of Custody record'); return; }
  // Frozen at send time, not log time -- see lawLogAiInteraction()'s comment.
  var sentMatter=matterSel?matterSel.value:'general';
  if(lawAiBusy){toast('Please wait for the current response first');return;}
  lawAiBusy=true;
  inp.value='';
  var chat=$('achat');
  if(chat.querySelector('div[style*="text-align:center"]'))chat.innerHTML='';
  chat.innerHTML+='<div class="amu">'+H(q)+'</div>';
  chat.scrollTop=chat.scrollHeight;
  aiHist.push({role:'user',content:q});
  var thinking=document.createElement('div');thinking.className='ama';thinking.textContent='Thinking...';chat.appendChild(thinking);
  chat.scrollTop=chat.scrollHeight;
  var toolDefs=Object.keys(LAW_TOOLS).map(function(k){return LAW_TOOLS[k].definition;});
  // Citation-grounding instruction -- the actual enforcement mechanism
  // for this panel's promise, not a UI label. This does not make
  // hallucination structurally impossible (no system prompt can, for
  // any LLM) -- it's the same class of mitigation as a disclaimer
  // plus explicit refusal instruction, not a verification system. A
  // real citation-verification system (checking a generated citation
  // against an actual case-law database) is a materially larger
  // build -- out of scope for Phase 1, flagged here rather than
  // silently implied as solved.
  //
  // TIGHTENED 2026-08-08: live-testing the first version of this rule
  // found a real gap -- for a famous case (Miranda v. Arizona) the
  // model stated a specific citation string ("384 U.S. 436 (1966)")
  // prefaced with "high confidence" and followed by a verification
  // disclaimer, rather than withholding the citation itself. A busy
  // attorney could copy the citation and skip the disclaimer
  // underneath it. The rule now explicitly forbids outputting the
  // citable-reference-format string (volume/reporter/page/year, or a
  // statute section number) under any circumstances regardless of
  // confidence or fame -- narrative description of a case (holding,
  // parties, era, principle) is still allowed, only the citation
  // string itself is withheld.
  //
  // ADDED 2026-08-10: platform-wide anti-substitution instruction,
  // ported from SAIRNbiz's fix for the same fabrication class (a denied
  // or failed tool call getting followed by a self-invented figure
  // anyway). Placed at the end of system-prompt construction so it
  // carries into the SECOND proxy call below too -- that's the one that
  // renders the user-visible reply after a tool_result comes back, and
  // it sends no `tools` field at all, so a tool's own description has
  // zero influence on that turn.
  var sys='You are a legal practice operations assistant (NOT a substitute for legal research or legal advice). '+LAW_CITATION_RULE+' Non-legal-research topics (matter organization, scheduling, drafting non-legal-conclusion text, billing) are not subject to that citation restriction. '+LAW_FIRM_DATA_RULE+' Never provide your own estimate, guess, or general-knowledge substitute for any fact a tool would have provided -- if a tool errors, is denied, or a question calls for data you have not actually retrieved via a tool this turn, say so plainly and stop. This applies even to "rough" or "likely" answers.';
  try{
    var res=await fetch(PROXY,{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({app_id:APP_ID,is_demo:true,max_tokens:600,system:sys,
        messages:aiHist.map(function(m){return {role:m.role,content:m.content};}),
        tools:toolDefs})});
    var data=await res.json();
    var aiErr=lawAiError(data);
    if(aiErr){thinking.textContent=aiErr;chat.scrollTop=chat.scrollHeight;return;}
    var blocks=(data&&data.content)||[];
    var toolUse=blocks.filter(function(b){return b.type==='tool_use';})[0];
    if(!toolUse){
      var rep=(blocks[0]&&blocks[0].text)||'No response text returned.';
      thinking.textContent=rep;
      aiHist.push({role:'assistant',content:rep});
      lawLogAiInteraction(q,rep,[],sentMatter);
      chat.scrollTop=chat.scrollHeight;
      return;
    }
    var outcome=lawExecuteTool(toolUse.name,prole,toolUse.input);
    // Belt-and-suspenders, same as SAIRNbiz: reinforce the anti-fabrication
    // instruction right next to the trigger, in the same turn as the
    // denial/error itself, not just once at the system-prompt level.
    var toolResultContent=outcome.ok?JSON.stringify(outcome.result):('Error: '+outcome.error+' Do not estimate or substitute your own figures for this -- state the restriction/error plainly and stop.');
    // Claude requires the assistant turn that requested the tool to be
    // present in history before the tool_result turn that answers it.
    aiHist.push({role:'assistant',content:blocks});
    aiHist.push({role:'user',content:[{type:'tool_result',tool_use_id:toolUse.id,content:toolResultContent}]});
    var res2=await fetch(PROXY,{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({app_id:APP_ID,is_demo:true,max_tokens:600,system:sys,
        messages:aiHist.map(function(m){return {role:m.role,content:m.content};})})});
    var data2=await res2.json();
    var aiErr2=lawAiError(data2);
    if(aiErr2){thinking.textContent=aiErr2;chat.scrollTop=chat.scrollHeight;return;}
    var rep2=(data2.content&&data2.content[0]&&data2.content[0].text)||'No response text returned.';
    thinking.textContent=rep2;
    aiHist.push({role:'assistant',content:rep2});
    lawLogAiInteraction(q,rep2,[toolUse.name],sentMatter);
  }catch(e){thinking.textContent='Could not connect to Claude. Check your connection and try again.';}
  finally{lawAiBusy=false;}
  chat.scrollTop=chat.scrollHeight;
}
```

Replace with:

```js
function askAI(q){$('ainp').value=q;sendAI();}
async function sendAI(){
  var inp=$('ainp'),q=(inp.value||'').trim();
  if(!q)return;
  var matterSel=$('aimatter');
  if(matterSel && !matterSel.value){ toast('Select a matter (or "General") before sending — required for the AI Chain of Custody record'); return; }
  // Frozen at send time -- see docs/superpowers/specs/2026-08-13-sairnlaw-
  // ai-chain-of-custody-server-side-capture-design.md.
  var sentMatter=matterSel?matterSel.value:'general';
  if(lawAiBusy){toast('Please wait for the current response first');return;}
  lawAiBusy=true;
  inp.value='';
  var chat=$('achat');
  if(chat.querySelector('div[style*="text-align:center"]'))chat.innerHTML='';
  chat.innerHTML+='<div class="amu">'+H(q)+'</div>';
  chat.scrollTop=chat.scrollHeight;
  aiHist.push({role:'user',content:q});
  var thinking=document.createElement('div');thinking.className='ama';thinking.textContent='Thinking...';chat.appendChild(thinking);
  chat.scrollTop=chat.scrollHeight;
  var toolDefs=Object.keys(LAW_TOOLS).map(function(k){return LAW_TOOLS[k].definition;});
  // Citation-grounding instruction -- the actual enforcement mechanism
  // for this panel's promise, not a UI label. This does not make
  // hallucination structurally impossible (no system prompt can, for
  // any LLM) -- it's the same class of mitigation as a disclaimer
  // plus explicit refusal instruction, not a verification system. A
  // real citation-verification system (checking a generated citation
  // against an actual case-law database) is a materially larger
  // build -- out of scope for Phase 1, flagged here rather than
  // silently implied as solved.
  //
  // TIGHTENED 2026-08-08: live-testing the first version of this rule
  // found a real gap -- for a famous case (Miranda v. Arizona) the
  // model stated a specific citation string ("384 U.S. 436 (1966)")
  // prefaced with "high confidence" and followed by a verification
  // disclaimer, rather than withholding the citation itself. A busy
  // attorney could copy the citation and skip the disclaimer
  // underneath it. The rule now explicitly forbids outputting the
  // citable-reference-format string (volume/reporter/page/year, or a
  // statute section number) under any circumstances regardless of
  // confidence or fame -- narrative description of a case (holding,
  // parties, era, principle) is still allowed, only the citation
  // string itself is withheld.
  //
  // ADDED 2026-08-10: platform-wide anti-substitution instruction,
  // ported from SAIRNbiz's fix for the same fabrication class (a denied
  // or failed tool call getting followed by a self-invented figure
  // anyway). Placed at the end of system-prompt construction so it
  // carries into the SECOND proxy call below too -- that's the one that
  // renders the user-visible reply after a tool_result comes back, and
  // it sends no `tools` field at all, so a tool's own description has
  // zero influence on that turn.
  var sys='You are a legal practice operations assistant (NOT a substitute for legal research or legal advice). '+LAW_CITATION_RULE+' Non-legal-research topics (matter organization, scheduling, drafting non-legal-conclusion text, billing) are not subject to that citation restriction. '+LAW_FIRM_DATA_RULE+' Never provide your own estimate, guess, or general-knowledge substitute for any fact a tool would have provided -- if a tool errors, is denied, or a question calls for data you have not actually retrieved via a tool this turn, say so plainly and stop. This applies even to "rough" or "likely" answers.';
  try{
    // AI Chain of Custody -- server-side capture (2026-08-13): ai_generate
    // replaces a raw fetch(PROXY,...) -- one authenticated server round trip
    // that also logs the FINAL leg's real response before returning it, so
    // nothing user-facing can reach this chat unlogged. This first call
    // never returns final text on its own when a tool is used (see
    // ai_generate's own tool_use branch), so nothing here is logged yet.
    var r=await lawAuth('ai_generate',{system:sys,
      messages:aiHist.map(function(m){return {role:m.role,content:m.content};}),
      max_tokens:600,tools:toolDefs,prompt_for_log:q,matter_id:sentMatter,tools_used:[]},true);
    var data=r.data;
    var aiErr=lawAiError(data)||(!r.ok?(r.msg||'AI request failed'):null);
    if(aiErr){thinking.textContent=aiErr;chat.scrollTop=chat.scrollHeight;return;}
    var blocks=(data&&data.content)||[];
    var toolUse=blocks.filter(function(b){return b.type==='tool_use';})[0];
    if(!toolUse){
      var rep=(blocks[0]&&blocks[0].text)||'No response text returned.';
      thinking.textContent=rep;
      aiHist.push({role:'assistant',content:rep});
      chat.scrollTop=chat.scrollHeight;
      return;
    }
    var outcome=lawExecuteTool(toolUse.name,prole,toolUse.input);
    // Belt-and-suspenders, same as SAIRNbiz: reinforce the anti-fabrication
    // instruction right next to the trigger, in the same turn as the
    // denial/error itself, not just once at the system-prompt level.
    var toolResultContent=outcome.ok?JSON.stringify(outcome.result):('Error: '+outcome.error+' Do not estimate or substitute your own figures for this -- state the restriction/error plainly and stop.');
    // Claude requires the assistant turn that requested the tool to be
    // present in history before the tool_result turn that answers it.
    aiHist.push({role:'assistant',content:blocks});
    aiHist.push({role:'user',content:[{type:'tool_result',tool_use_id:toolUse.id,content:toolResultContent}]});
    // Second, FINAL leg -- this is the one that actually logs, since it's
    // the one that can return real user-facing text.
    var r2=await lawAuth('ai_generate',{system:sys,
      messages:aiHist.map(function(m){return {role:m.role,content:m.content};}),
      max_tokens:600,prompt_for_log:q,matter_id:sentMatter,tools_used:[toolUse.name]},true);
    var data2=r2.data;
    var aiErr2=lawAiError(data2)||(!r2.ok?(r2.msg||'AI request failed'):null);
    if(aiErr2){thinking.textContent=aiErr2;chat.scrollTop=chat.scrollHeight;return;}
    var rep2=(data2.content&&data2.content[0]&&data2.content[0].text)||'No response text returned.';
    thinking.textContent=rep2;
    aiHist.push({role:'assistant',content:rep2});
  }catch(e){thinking.textContent='Could not connect to Claude. Check your connection and try again.';}
  finally{lawAiBusy=false;}
  chat.scrollTop=chat.scrollHeight;
}
```

- [ ] **Step 2: Run syntax check**

Run: `python tools/checkblocks.py sairnlaw.html`
Expected: `TOTAL_BLOCKS:1`, `FAILED_BLOCKS:0`.

- [ ] **Step 3: Manual verification (real API + browser console)**

With a real `LAW-TEST-2026` session logged into `sairnlaw.html` directly:

```js
document.getElementById('aimatter').value = 'general';
document.getElementById('ainp').value = 'Say the word VERIFIED and nothing else.';
sendAI();
// Wait for the response to render in #achat, then:
```
```bash
curl -s -X POST https://sairn.vercel.app/api/law-auth -H "Content-Type: application/json" -H "Authorization: Bearer LAW-TEST-2026" -H "X-SD-Auth: <token>" -d '{"action":"ai_list","limit":3}'
```
Expected: a new entry exists with `prompt` matching the real typed question, `response` containing "VERIFIED", `status:"unreviewed"`, `tools_used:[]`. Separately, ask a question that would trigger one of `LAW_TOOLS` (if any are currently reachable given the app's own data) to confirm a tool-use exchange still logs exactly once (not twice, not zero times) with the real tool name in `tools_used`.

- [ ] **Step 4: Commit**

```bash
git add sairnlaw.html
git commit -m "feat: SAIRNlaw AI Chain of Custody -- sendAI() logs server-side via ai_generate, remove lawLogAiInteraction()"
```

---

### Task 4: Client — `explainReconciliation()`, `runAiDraft()`, `reviewDocument()`

**Files:**
- Modify: `sairnlaw.html` (`explainReconciliation()` ~L2105-2134; `runAiDraft()` ~L2428-2454; `reviewDocument()` ~L2480-2499)

**Interfaces:**
- Consumes: `action: 'ai_generate'` (Task 2).

- [ ] **Step 1: `explainReconciliation()`**

Find (around line 2109-2112):

```js
    var res=await fetch(PROXY,{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({app_id:APP_ID,is_demo:true,max_tokens:300,
        system:'You explain trust-accounting reconciliation discrepancies in plain language for a law firm. You are given real, already-computed numbers -- never recompute or second-guess them, never invent additional numbers, only explain what a mismatch of this shape typically means and what to check next (uncleared checks, timing differences, a missed entry).',
        messages:[{role:'user',content:'Trust ledger balance: '+fmt(r.ledgerBal)+'. Sum of client ledgers: '+fmt(r.clientSum)+'. Bank statement balance: '+(r.bankBal===null?'not yet entered':fmt(r.bankBal))+'. Ledger matches client-ledger sum: '+r.ledgerVsClient+'. Ledger matches bank statement: '+r.ledgerVsBank+'. Explain what this indicates and what to check.'}]})});
    var data=await res.json();
    var aiErr=lawAiError(data);
```

Replace with:

```js
    var trPrompt='Trust ledger balance: '+fmt(r.ledgerBal)+'. Sum of client ledgers: '+fmt(r.clientSum)+'. Bank statement balance: '+(r.bankBal===null?'not yet entered':fmt(r.bankBal))+'. Ledger matches client-ledger sum: '+r.ledgerVsClient+'. Ledger matches bank statement: '+r.ledgerVsBank+'. Explain what this indicates and what to check.';
    var rr=await lawAuth('ai_generate',{max_tokens:300,
      system:'You explain trust-accounting reconciliation discrepancies in plain language for a law firm. You are given real, already-computed numbers -- never recompute or second-guess them, never invent additional numbers, only explain what a mismatch of this shape typically means and what to check next (uncleared checks, timing differences, a missed entry).',
      messages:[{role:'user',content:trPrompt}],prompt_for_log:trPrompt,matter_id:'general',tools_used:[]},true);
    var data=rr.data;
    var aiErr=lawAiError(data)||(!rr.ok?(rr.msg||'AI request failed'):null);
```

- [ ] **Step 2: `runAiDraft()`**

Find (around line 2440-2446):

```js
    var res=await fetch(PROXY,{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({app_id:APP_ID,is_demo:true,max_tokens:1200,
        system:'You are a legal document drafting and review assistant for a law firm, working from the real matter data provided below. Draft or review documents professionally and precisely, using the matter facts given -- do not invent facts about the matter you were not given. '+LAW_CITATION_RULE+' Drafting document text itself (letters, contract language, motion structure) is expected and not restricted -- the restriction is specifically on inventing citation numbers, not on legal drafting generally.',
        messages:[{role:'user',content:'Matter context: '+context+'\n\nRequest: '+request}]})});
    var data=await res.json();
    if(myDraftSeq!==lawDraftSeq)return;
    var aiErr=lawAiError(data);
```

Replace with:

```js
    var draftPrompt='Matter context: '+context+'\n\nRequest: '+request;
    var rr=await lawAuth('ai_generate',{max_tokens:1200,
      system:'You are a legal document drafting and review assistant for a law firm, working from the real matter data provided below. Draft or review documents professionally and precisely, using the matter facts given -- do not invent facts about the matter you were not given. '+LAW_CITATION_RULE+' Drafting document text itself (letters, contract language, motion structure) is expected and not restricted -- the restriction is specifically on inventing citation numbers, not on legal drafting generally.',
      messages:[{role:'user',content:draftPrompt}],prompt_for_log:draftPrompt,matter_id:matterId,tools_used:[]},true);
    var data=rr.data;
    if(myDraftSeq!==lawDraftSeq)return;
    var aiErr=lawAiError(data)||(!rr.ok?(rr.msg||'AI request failed'):null);
```

- [ ] **Step 3: `reviewDocument()`**

Find (around line 2487-2493):

```js
    var res=await fetch(PROXY,{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({app_id:APP_ID,is_demo:true,max_tokens:800,
        system:'You are reviewing a legal document for a law firm. Give specific, actionable feedback (clarity, structure, missing elements, risk flags) -- do not rewrite the whole document unless asked. '+LAW_CITATION_RULE,
        messages:[{role:'user',content:'Please review this document:\n\n'+d.content_text}]})});
    var data=await res.json();
    if(myDraftSeq!==lawDraftSeq)return;
    var aiErr=lawAiError(data);
```

Replace with:

```js
    var reviewPrompt='Please review this document:\n\n'+d.content_text;
    var rr=await lawAuth('ai_generate',{max_tokens:800,
      system:'You are reviewing a legal document for a law firm. Give specific, actionable feedback (clarity, structure, missing elements, risk flags) -- do not rewrite the whole document unless asked. '+LAW_CITATION_RULE,
      messages:[{role:'user',content:reviewPrompt}],prompt_for_log:reviewPrompt,matter_id:d.matter_id||'general',tools_used:[]},true);
    var data=rr.data;
    if(myDraftSeq!==lawDraftSeq)return;
    var aiErr=lawAiError(data)||(!rr.ok?(rr.msg||'AI request failed'):null);
```

- [ ] **Step 4: Run syntax check**

Run: `python tools/checkblocks.py sairnlaw.html`
Expected: `TOTAL_BLOCKS:1`, `FAILED_BLOCKS:0`.

- [ ] **Step 5: Manual verification (real API + browser console)**

With a matter that has real data on `LAW-TEST-2026` (create one via the app's own Matters panel if none exists yet):

```js
// Trust reconciliation panel: click "Explain This Discrepancy (AI)" (or call explainReconciliation() directly)
// Drafting panel: select a matter, type a request, click Draft (or call runAiDraft() directly)
// Documents: pick a document with real text, click Review (or call reviewDocument(docId) directly)
```
After each, confirm via `ai_list` (same curl pattern as Task 2/3) that a new entry exists with the real matter/document-linked `matter_id`, the real full prompt content (matter context / document text included, not just the rep's short request), and `status:"unreviewed"`.

- [ ] **Step 6: Commit**

```bash
git add sairnlaw.html
git commit -m "feat: SAIRNlaw AI Chain of Custody -- explainReconciliation/runAiDraft/reviewDocument log server-side via ai_generate"
```

---

### Task 5: Full verification sweep, live-verify, and push

**Files:** none (verification only)

- [ ] **Step 1: Full local syntax sweep**

`node --check api/claude.js`, `node --check api/law-auth.js` — both clean. `node api/_lib/claude.test.js` — `8 passed`. `python tools/checkblocks.py sairnlaw.html` — `FAILED_BLOCKS:0`.

- [ ] **Step 2: Scoped Guardian checks**

Search: grep the diff for `console.log` — confirm none left in. Confirm no hardcoded secrets. Confirm every `verifySessionToken` call in the new/changed code uses the full 3-argument form with `APP`.

- [ ] **Step 3: Run the full Guardian review before commit/push**

Invoke the `sairn-guardian-v2` skill's full Check 0 + numbered checks against the diff, per CLAUDE.md's standing Push Protocol.

- [ ] **Step 4: Combined end-to-end manual verification (real API, `LAW-TEST-2026`)**

1. Confirm `ai_log` is genuinely gone: direct call returns 400 unrecognized-action.
2. Confirm write-failure blocking: temporarily make a log write fail (e.g. by testing against a `matter_id`/payload shape that would violate a real constraint, or by coordinating a brief, reverted change to the `event_type` check constraint) and confirm the client-visible result is a real error, never the AI's generated text.
3. Confirm all 5 call sites (sendAI() x2 legs, explainReconciliation, runAiDraft, reviewDocument) produce exactly one log entry per real exchange, with the correct real prompt/response/matter_id/tools_used each.
4. Confirm `runAiDraft()`'s existing "Save as Document" behavior (`saveDraftAsDocument()`, unrelated to this change) still works unaffected.
5. Live spot-check one OTHER app's AI feature (e.g. StoneDesk's own AI panel) to confirm `api/claude.js`'s HTTP handler is still byte-identical for its other 17 callers.

- [ ] **Step 5: Push**

```bash
git push origin main
```

- [ ] **Step 6: Live-verify against production**

Repeat Step 4's checks against `sairn.vercel.app/sairnlaw` and the live `api/claude.js`/`api/law-auth.js` endpoints directly. Confirm the deployed file hashes match the pushed commit (normalize line endings before comparing).

- [ ] **Step 7: Update `SAIRN-BACKLOG.md` and write the session handoff**

Mark the "client-reported capture, not proxy-observed" half of the existing "SAIRNlaw AI Chain of Custody: two honest gaps" backlog entry as resolved (the fabrication-risk half is also resolved via `ai_log`'s removal) — the "unvalidated matter linkage" half remains open (still blocked on `law_matters` becoming server-backed, unchanged by this plan). Use the `sairn-session-handoff` skill to write the next `SAIRNLAW-SESSION-N-HANDOFF.md` (Session 2).

---

## Self-Review Notes

- **Spec coverage:** the `api/claude.js` refactor (Task 1), `ai_generate`'s tool-use-branch/final-text-branch/write-blocks-response logic (Task 2), all 5 real call sites migrated with their own correct per-function `prompt_for_log` content (Tasks 3-4), and `ai_log`'s removal (Task 2) together cover every decision in the design spec's Scope section. The demo-rate-limit preservation (Global Constraints) closes a real gap found during planning that the spec itself didn't explicitly call out — disclosed here rather than silently handled.
- **Placeholder scan:** no TBD/TODO — every step shows real code matching the actual current file content (re-read immediately before writing this plan) or a real runnable check with a stated expected result.
- **Type/name consistency:** `callAnthropic`/`getDemoKey`/`demoCallCounts`/`DEMO_DAILY_LIMIT` (Task 1) are consumed with identical names in Task 2. `ai_generate`'s request shape (`system`, `messages`, `max_tokens`, `tools`, `matter_id`, `prompt_for_log`, `tools_used`) is identical across Task 2's handler and every one of Tasks 3-4's 5 call sites.
