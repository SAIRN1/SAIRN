# SAIRNcode AI Tool-Calling Foundation + get_providers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give SAIRNcode's chat (`sendChatMessage()`, `sairncode.html:2548`) real function-calling access to the real provider roster, via one proof tool (`get_providers`), porting the mechanism proven live on every prior rollout — the simplest port so far, since this chat is already single-shot and stateless (no shared history to guard) and no real auth exists (no sensitivity/role-gate needed).

**Architecture:** `SC_TOOLS`/`scRegisterTool`/`scExecuteTool` — same registry shape as SAIRNvet's, minus the `sensitive`/role parameter (no real auth backend exists here either). Unlike every other rollout, no new parallel fetch function is needed — the existing single `fetch(APP_CONFIG.proxy, ...)` call in `sendChatMessage()` simply gains a `tools` field and a tool-use branch. No busy-guard needed — nothing shared to corrupt.

**Tech Stack:** Vanilla JS (`sairncode.html`, no framework). Verified the same way every prior rollout was: `tools/checkblocks.py` / `tools/div_balance_check.py` on the file, a temporary `node:assert` scratch harness for pure logic, plus a real live-interaction test against the deployed app.

**Note — one small, deliberate addition beyond a literal reading of the spec:** the spec's §3 architecture doesn't spell out an anti-fabrication instruction, but every single prior rollout (SAIRNbiz, SAIRNlaw, SAIRNvet, SAIRNscape, SAIRNgrounds, StoneDesk) added one, at zero cost, as the belt-and-suspenders phrasing next to a `tool_result` error. This plan includes it for the same reason and to stay consistent with the now-established platform convention — flagged here explicitly rather than silently expanding scope.

## Global Constraints

- Read-only tool only — `get_providers` may not create, modify, or delete any record. (Spec §2)
- No new persistence — reads `getProviderEntries()` (`sairncode.html:2465`) directly. (Spec §2)
- `get_providers` returns `{name, specialty, license, cred, perf}` only — `id` excluded. (Spec §4)
- No `sensitive`/role parameter anywhere in this dispatcher — no real auth backend exists to enforce one. (Spec §1, §3)
- No concurrency guard — `sendChatMessage()` builds a fresh one-message request each call, nothing shared to corrupt. (Spec §1)
- Single round-trip only: the follow-up call after a `tool_result` does not re-send `tools` and does not expect another `tool_use`. (Spec §3)
- `SAIRNCODE_SYSTEM_PROMPT` (`sairncode.html:1481`) is reused as-is, unmodified. (Spec §3)
- No changes to `api/claude.js`. (Spec §2)
- `python tools/checkblocks.py sairncode.html` and `python tools/div_balance_check.py sairncode.html` must stay clean (0 failed / PASS) after every change.
- Before push: full Guardian v2 check on `sairncode.html`. After push: live-verify against `sairn.vercel.app/sairncode` directly, not assumed from a clean push (project Push Protocol).

---

### Task 1: `sairncode.html` — tool registry, dispatcher, and the `get_providers` tool

**Files:**
- Modify: `sairncode.html` (insert immediately before `async function sendChatMessage()` at `sairncode.html:2548`, after `saveProviderEntries()`'s closing `}` at `sairncode.html:2476`)

**Interfaces:**
- Consumes: `getProviderEntries()` (`sairncode.html:2465`, existing).
- Produces: `SC_TOOLS` (object, tool name → `{definition, run}` — no `sensitive` field), `scExecuteTool(name, input)` → `{ok: true, result: any} | {ok: false, error: string}` — used by Task 2.

- [ ] **Step 1: Write the implementation**

Insert after `saveProviderEntries()`'s closing `}` (`sairncode.html:2476`), before `async function sendChatMessage()`:

```js
        // AI tool-calling dispatcher (2026-08-10) -- ports the mechanism proven
        // live on every other SAIRN app. Registry of read-only tools
        // sendChatMessage() may request via Claude's tool-use. Every tool is:
        //   - read-only (never creates/modifies/deletes anything)
        //   - wrapped so a thrown error or unexpected data shape becomes an honest
        //     {ok:false} result, never a crash or a silently wrong answer
        // No sensitivity/role-gate concept here -- SAIRNcode has no real,
        // server-verified auth (sc_role comes from a client-side PIN pick),
        // same reasoning already applied to SAIRNvet's dispatcher.
        // See docs/superpowers/specs/2026-08-10-sairncode-ai-tool-calling-design.md
        var SC_TOOLS = {};

        function scRegisterTool(name, description, inputSchema, run) {
            SC_TOOLS[name] = {
                definition: { name: name, description: description, input_schema: inputSchema },
                run: run
            };
        }

        function scExecuteTool(name, input) {
            var tool = SC_TOOLS[name];
            if (!tool) return { ok: false, error: 'No tool named "' + name + '" exists.' };
            try {
                return { ok: true, result: tool.run(input || {}) };
            } catch (e) {
                return { ok: false, error: 'Could not retrieve that data right now.' };
            }
        }

        scRegisterTool(
            'get_providers',
            'Look up the current provider roster: name, specialty, license number, credentialing status, and performance score. Does NOT include A/R, denials, DRG, HCC, RAC, compliance, fraud, revenue, prebill, telehealth, or anesthesia data -- those are not available to this tool.',
            { type: 'object', properties: {}, required: [] },
            function (input) {
                // input intentionally unused -- this tool takes no real arguments, but
                // accepts one for interface consistency with scExecuteTool(name, input),
                // matching every prior tool's convention.
                return getProviderEntries().map(function (p) {
                    return {
                        name: p.name,
                        specialty: p.specialty,
                        license: p.license,
                        cred: p.cred,
                        perf: p.perf
                    };
                });
            }
        );
```

- [ ] **Step 2: Syntax-check the modified script block**

Run: `python tools/checkblocks.py sairncode.html`
Expected: same `TOTAL_BLOCKS` as the pre-change baseline (run it once before this edit if you don't already know the number), `FAILED_BLOCKS:0`.

Run: `python tools/div_balance_check.py sairncode.html`
Expected: `RESULT:PASS`.

- [ ] **Step 3: Behavioral verification with a temporary Node harness**

Both the dispatcher and the tool's `run()` have no DOM dependency. Create a scratch file (not committed — delete after this step):

```js
// scratch verification, delete after running
var assert = require('assert');

var SC_TOOLS = {};
function scRegisterTool(name, description, inputSchema, run) {
  SC_TOOLS[name] = { definition: { name: name, description: description, input_schema: inputSchema }, run: run };
}
function scExecuteTool(name, input) {
  var tool = SC_TOOLS[name];
  if (!tool) return { ok: false, error: 'No tool named "' + name + '" exists.' };
  try { return { ok: true, result: tool.run(input || {}) }; } catch (e) { return { ok: false, error: 'Could not retrieve that data right now.' }; }
}

// -- dispatcher checks --
scRegisterTool('ping', 'test tool', {type:'object'}, function () { return 'pong'; });
scRegisterTool('broken', 'test throwing tool', {type:'object'}, function () { throw new Error('boom'); });
assert.deepStrictEqual(scExecuteTool('ping', {}), { ok: true, result: 'pong' });
assert.deepStrictEqual(scExecuteTool('nonexistent', {}), { ok: false, error: 'No tool named "nonexistent" exists.' });
assert.strictEqual(scExecuteTool('broken', {}).ok, false);
console.log('scExecuteTool: all 3 checks passed');

// -- get_providers tool check, stubbing getProviderEntries() --
function getProviderEntries() {
  return [
    { id: 'pv1', name: 'Dr. Michael Chen', specialty: 'Internal Medicine', license: 'MD-2847291', cred: 'Yes', perf: 97.2 },
    { id: 'pv2', name: 'Dr. Sarah Martinez', specialty: 'Cardiology', license: 'MD-2947382', cred: 'Yes', perf: 98.1 }
  ];
}

scRegisterTool('get_providers', 'x', { type: 'object' }, function (input) {
  return getProviderEntries().map(function (p) {
    return { name: p.name, specialty: p.specialty, license: p.license, cred: p.cred, perf: p.perf };
  });
});

var out = SC_TOOLS.get_providers.run({});
assert.strictEqual(out.length, 2);
assert.strictEqual(out[0].name, 'Dr. Michael Chen');
assert.strictEqual(out[1].specialty, 'Cardiology');
assert.strictEqual(out[0].id, undefined, 'id must never appear in get_providers output');
console.log('get_providers tool: all 4 checks passed');
```

Run: `node <scratch-file>.js`
Expected: `scExecuteTool: all 3 checks passed` then `get_providers tool: all 4 checks passed`. Delete the scratch file afterward.

- [ ] **Step 4: Commit**

```bash
git add sairncode.html
git commit -m "feat: SAIRNcode -- tool-calling dispatcher + get_providers proof tool

Ports the mechanism proven live on every other SAIRN app, minus the
sensitivity/role-gate concept -- SAIRNcode has no real, server-verified
auth (sc_role comes from a client-side PIN pick), same reasoning
already applied to SAIRNvet's dispatcher. SC_TOOLS/scRegisterTool/
scExecuteTool plus one read-only tool, get_providers (name/specialty/
license/cred/perf). id deliberately excluded. sendChatMessage() doesn't
call any of this yet -- verified standalone via a Node harness."
```

---

### Task 2: `sairncode.html` — `sendChatMessage()` tool-use round-trip

**Files:**
- Modify: `sairncode.html:2548-2606` (`sendChatMessage()`)

**Interfaces:**
- Consumes: `scExecuteTool(name, input)` (Task 1), `SC_TOOLS` (Task 1, read via `Object.keys(SC_TOOLS).map(k => SC_TOOLS[k].definition)`), `APP_CONFIG` (`sairncode.html:1261`, existing), `SAIRNCODE_SYSTEM_PROMPT` (`sairncode.html:1481`, existing, unmodified), `buildScSharedCompanyContext()`/`recordScSharedTopics(message)` (existing, unmodified), `escHtml` (existing).
- Produces: no new exports — `sendChatMessage()` keeps its existing signature and call site (the chat input's submit handler).

- [ ] **Step 1: Write the implementation**

Replace `sendChatMessage()` (`sairncode.html:2548-2606`) with:

```js
        async function sendChatMessage() {
            const input = document.getElementById('chatInput');
            const chatHistoryEl = document.getElementById('chatHistory');
            if (!input || !chatHistoryEl) return;

            const message = input.value.trim();
            if (!message) return;

            input.value = '';

            const userMsg = document.createElement('div');
            userMsg.className = 'chat-message user';
            userMsg.innerHTML = `<div class="chat-bubble">${escHtml(message)}</div>`;
            chatHistoryEl.appendChild(userMsg);

            const loadingMsg = document.createElement('div');
            loadingMsg.className = 'chat-message assistant';
            loadingMsg.innerHTML = '<div class="chat-bubble"><div class="spinner"></div> Processing...</div>';
            chatHistoryEl.appendChild(loadingMsg);
            chatHistoryEl.scrollTop = chatHistoryEl.scrollHeight;

            function renderReply(text) {
                loadingMsg.remove();
                const assistantMsg = document.createElement('div');
                assistantMsg.className = 'chat-message assistant';
                assistantMsg.innerHTML = `<div class="chat-bubble">${escHtml(text)}</div>`;
                chatHistoryEl.appendChild(assistantMsg);
                chatHistoryEl.scrollTop = chatHistoryEl.scrollHeight;
            }

            function renderError(text) {
                loadingMsg.remove();
                const errorMsg = document.createElement('div');
                errorMsg.className = 'chat-message assistant';
                errorMsg.innerHTML = `<div class="chat-bubble error-box">${escHtml(text)}</div>`;
                chatHistoryEl.appendChild(errorMsg);
                chatHistoryEl.scrollTop = chatHistoryEl.scrollHeight;
            }

            try {
                const sharedCtx = (typeof buildScSharedCompanyContext === 'function') ? buildScSharedCompanyContext() : '';
                if (typeof recordScSharedTopics === 'function') recordScSharedTopics(message);
                // Belt-and-suspenders, same pattern proven on every prior rollout:
                // an explicit anti-fabrication instruction, not spelled out
                // verbatim in the design doc's architecture section but added
                // here for consistency with the platform-wide convention at
                // zero cost.
                const sys = SAIRNCODE_SYSTEM_PROMPT + (sharedCtx ? ('\n\n' + sharedCtx) : '') +
                    '\n\nNever provide your own estimate, guess, or general-knowledge substitute for any fact a tool would have provided -- if a tool errors, is denied, or a question calls for data you have not actually retrieved via a tool this turn, say so plainly and stop.';
                const toolDefs = Object.keys(SC_TOOLS).map(function (k) { return SC_TOOLS[k].definition; });
                const response = await fetch(APP_CONFIG.proxy, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        messages: [{ role: 'user', content: message }],
                        system: sys,
                        app_id: APP_CONFIG.app_id,
                        is_demo: APP_CONFIG.is_demo,
                        tools: toolDefs
                    })
                });

                if (!response.ok) {
                    renderError('Error: Unable to process request');
                    return;
                }

                const data = await response.json();
                const blocks = (data && data.content) || [];
                const toolUse = blocks.filter(function (b) { return b.type === 'tool_use'; })[0];

                if (!toolUse) {
                    renderReply((blocks[0] && blocks[0].text) || 'Response received');
                    return;
                }

                const outcome = scExecuteTool(toolUse.name, toolUse.input);
                const toolResultContent = outcome.ok
                    ? JSON.stringify(outcome.result)
                    : ('Error: ' + outcome.error + ' Do not estimate or substitute your own figures for this -- state the restriction/error plainly and stop.');

                const followUpMessages = [
                    { role: 'user', content: message },
                    { role: 'assistant', content: blocks },
                    { role: 'user', content: [{ type: 'tool_result', tool_use_id: toolUse.id, content: toolResultContent }] }
                ];

                const response2 = await fetch(APP_CONFIG.proxy, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        messages: followUpMessages,
                        system: sys,
                        app_id: APP_CONFIG.app_id,
                        is_demo: APP_CONFIG.is_demo
                    })
                });

                if (!response2.ok) {
                    renderError('Error: Unable to process request');
                    return;
                }

                const data2 = await response2.json();
                renderReply((data2.content && data2.content[0] && data2.content[0].text) || 'Response received');
            } catch (error) {
                renderError('Error: Connection failed');
            }
        }
```

Note: the local variable previously named `history` (a DOM element reference, `document.getElementById('chatHistory')`) is renamed to `chatHistoryEl` here purely to avoid any reader confusion with the message-array `history`/`aiHist` pattern used in every other app's rollout — it was never a shared or global variable, so this is a pure rename with zero behavioral change, not a scope fix.

- [ ] **Step 2: Syntax-check the modified script block**

Run: `python tools/checkblocks.py sairncode.html`
Expected: same `TOTAL_BLOCKS` as Task 1's result, `FAILED_BLOCKS:0`.

Run: `python tools/div_balance_check.py sairncode.html`
Expected: `RESULT:PASS`.

- [ ] **Step 3: Live interaction test — no-tool path unaffected**

Open the app locally (or via the deployed pre-push injection technique used on prior rollouts — note this file does not wrap chat state in an IIFE closure the way StoneDesk's did, so the usual injection technique should work here), log in (demo credentials: license `SC-PINNACLE-2026`, PIN `1234`), ask a generic medical-coding question unrelated to providers (e.g. "what modifier do I use for a bilateral procedure"). Confirm: exactly one "Processing..." spinner appears and is replaced by one real answer, no console errors, no tool invoked.

- [ ] **Step 4: Commit**

```bash
git add sairncode.html
git commit -m "feat: SAIRNcode -- sendChatMessage() supports the tool-use round-trip

Sends SC_TOOLS' definitions on the existing single fetch call, executes
a requested tool via scExecuteTool() (error-safe, no role check per
this app's design decision), sends the result back via a second fetch
for a final grounded answer. Anti-fabrication instruction added to the
system prompt for this turn only, matching the platform-wide
convention -- SAIRNCODE_SYSTEM_PROMPT itself is unmodified. No busy-
guard needed -- each call already builds a fresh, independent request."
```

---

### Task 3: End-to-end verification, push, live-verify

**Files:** none modified — verification only.

- [ ] **Step 1: Full local re-check of the changed file**

```bash
python tools/checkblocks.py sairncode.html
python tools/div_balance_check.py sairncode.html
```

Expected: both checks show 0 failures / PASS.

- [ ] **Step 2: Guardian v2 pass**

Run the full `sairn-guardian-v2` check (Check 0 + numbered checks) against `sairncode.html` before push, per the project's standing Push Protocol.

- [ ] **Step 3: Real interaction test — provider roster question**

With the app running against real seeded data, ask the AI a provider question ("who are our credentialed providers," "what's Dr. Chen's specialty," "list our providers and their performance scores"). Confirm the answer contains real names/specialties/credentialing status from `sc_providers` — not a generic non-answer.

- [ ] **Step 4: No-tool-use regression test**

Ask a generic medical-coding question unrelated to providers (e.g. "explain the difference between ICD-10 and CPT codes"). Confirm it still answers directly from the persona, exactly as before, with no tool invoked and no regression in response quality.

- [ ] **Step 5: `sanitizeTools()` regression check for this app_id specifically**

```bash
curl -s -X POST https://sairn.vercel.app/api/claude \
  -H 'Content-Type: application/json' \
  -d '{"app_id":"sairncode","is_demo":true,"max_tokens":50,"system":"test","messages":[{"role":"user","content":"say hi"}],"tools":[{"name":"get_providers","description":"x","input_schema":{"type":"object","properties":{}}}]}'
```

Expected: HTTP 200 with a real Anthropic response shape (`content` array present), not a 400.

- [ ] **Step 6: Push**

```bash
git push origin main
```

- [ ] **Step 7: Live-verify**

```bash
curl -s https://sairn.vercel.app/sairncode | grep -c "scExecuteTool"
```

Expected: non-zero. Then repeat Steps 3-4's tests against the **live** URL, not just a local copy — per the project's standing rule that a clean push is not proof the live app reflects the change.

- [ ] **Step 8: Update the spec's status line**

Edit `docs/superpowers/specs/2026-08-10-sairncode-ai-tool-calling-design.md`'s `**Status:**` line to note the foundation and `get_providers` are implemented and live-verified, with the date. Commit this doc-only change separately.
