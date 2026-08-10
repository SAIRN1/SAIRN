# SAIRNlaw AI Tool-Calling Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give SAIRNlaw's general AI chat (`sendAI()`, `sairnlaw.html:1406`) real function-calling access to the firm's own matter data, starting with one proof tool (`get_matters`), porting the exact mechanism already proven live in SAIRNbiz (`docs/superpowers/specs/2026-08-09-sairnbiz-ai-tool-calling-design.md`).

**Architecture:** Multi-turn tool-calling through the existing shared proxy (`api/claude.js`), which already allows custom client tools through for every `app_id` — no proxy change needed for this app. On the client, `sendAI()` sends a `tools` array; if Claude responds with a `tool_use` block, a new dispatcher (`lawExecuteTool()`) looks it up, checks role-sensitivity, executes the matching local getter, and sends a `tool_result` back for the final answer — one round-trip, not an open-ended tool loop. `LAW_FIRM_DATA_RULE` (`sairnlaw.html:1403`), which currently tells the model it has no real firm data at all, gets a precise field-level edit so it stops contradicting the new `get_matters` access while staying accurate about what's still not tooled (deadlines, trust, billing).

**Tech Stack:** Vanilla JS (`sairnlaw.html`, no framework), existing `sairn.vercel.app/api/claude` proxy (unmodified by this plan). Verified the way every other `sairnlaw.html`/`sairnbiz.html` change in this project is verified — `node --check` / `python tools/checkblocks.py` / `python tools/div_balance_check.py` on the file, a temporary `node:assert` scratch harness for pure-function logic (no browser test runner exists in this repo), plus a real live-interaction test against the deployed app.

## Global Constraints

- Read-only tool only — `get_matters` may not create, modify, or delete any record. (Spec §2)
- No new persistence — reads live from `ld('law_matters', [])` via the existing `matters()`/`clientLabel()` helpers. (Spec §2)
- v1 ships exactly one tool, `get_matters`, excluding `notes` (free text) and all date/trust/billing fields. (Spec §4)
- Single round-trip only: the follow-up call after a `tool_result` does not re-send `tools` and does not expect another `tool_use`. (Spec §3)
- No change to `api/claude.js` — `sanitizeTools()` already passes custom tools through for `sairnlaw`. (Spec §2)
- `runAiDraft()` (`sairnlaw.html:2218`) is untouched — only `sendAI()` changes. (Spec §2)
- `LAW_FIRM_DATA_RULE` gets a precise field-level edit (matters now accessible, deadlines/trust/billing still not) — not a blanket removal. (Spec §3)
- Every modified script block in `sairnlaw.html` must pass `node --check` before commit (project standing rule, `CLAUDE.md`).
- `python tools/checkblocks.py sairnlaw.html` and `python tools/div_balance_check.py sairnlaw.html` must stay clean (0 failed / PASS) after every change.
- Before push: full Guardian v2 check on `sairnlaw.html`. After push: live-verify against `sairn.vercel.app/sairnlaw` directly, not assumed from a clean push (project Push Protocol).
- `sendAI()` already holds its "Thinking..." placeholder by direct DOM-node reference (`thinking`, `sairnlaw.html:1415`), not a DOM query — the tool round-trip must keep updating this same node, not regress to querying for "the last `.ama`." (Spec §3)

---

### Task 1: `sairnlaw.html` — tool registry and dispatcher

**Files:**
- Modify: `sairnlaw.html` (insert immediately after `LAW_FIRM_DATA_RULE`'s definition, `sairnlaw.html:1403`, before `clrAI()` at `sairnlaw.html:1404`)

**Interfaces:**
- Consumes: `prole` (`sairnlaw.html:990`) — existing global holding the logged-in role string.
- Produces: `LAW_TOOLS` (object, tool name → `{definition, sensitive, run}`), `lawExecuteTool(name, role, input)` → `{ok: true, result: any} | {ok: false, error: string}` — used by Task 3.

- [ ] **Step 1: Write the implementation**

Insert immediately after the `LAW_FIRM_DATA_RULE` line (`sairnlaw.html:1403`), before `function clrAI(){...}`:

```js
// AI tool-calling dispatcher (2026-08-10) -- ports the mechanism proven
// live in SAIRNbiz (see docs/superpowers/specs/2026-08-09-sairnbiz-ai-
// tool-calling-design.md). Registry of read-only tools sendAI() may
// request via Claude's tool-use. Every tool is:
//   - read-only (never creates/modifies/deletes anything)
//   - wrapped so a thrown error or unexpected data shape becomes an honest
//     {ok:false} result, never a crash or a silently wrong answer
//   - checked against the CALLING role before running, if marked sensitive
// See docs/superpowers/specs/2026-08-10-sairnlaw-ai-tool-calling-design.md
var LAW_TOOLS = {};

function lawRegisterTool(name, description, inputSchema, sensitive, run) {
  LAW_TOOLS[name] = {
    definition: { name: name, description: description, input_schema: inputSchema },
    sensitive: !!sensitive,
    run: run
  };
}

// run() MUST be synchronous -- the try/catch below only catches thrown
// errors. An async run() returning a rejected Promise would NOT be
// caught and would silently report {ok:true, result:<pending Promise>}.
// (Same documented constraint as SAIRNbiz's sbExecuteTool.)
function lawExecuteTool(name, role, input) {
  var tool = LAW_TOOLS[name];
  if (!tool) return { ok: false, error: 'No tool named "' + name + '" exists.' };
  if (tool.sensitive && role !== 'owner') {
    return { ok: false, error: 'This data is restricted to the owner role.' };
  }
  try {
    return { ok: true, result: tool.run(input || {}) };
  } catch (e) {
    return { ok: false, error: 'Could not retrieve that data right now.' };
  }
}
```

- [ ] **Step 2: Syntax-check the modified script block**

Run: `node --check sairnlaw.html` will fail (this is an HTML file, not pure JS) — use the project's real check instead:

Run: `python tools/checkblocks.py sairnlaw.html`
Expected: same `TOTAL_BLOCKS` / `FAILED_BLOCKS:0` as the pre-change baseline — run `python tools/checkblocks.py sairnlaw.html` once before this edit if the baseline isn't already known, so a regression is distinguishable from a pre-existing failure.

Run: `python tools/div_balance_check.py sairnlaw.html`
Expected: `RESULT:PASS`.

- [ ] **Step 3: Behavioral verification with a temporary Node harness**

The dispatcher has no DOM dependency, so its real logic (not just syntax) can be checked with plain `node:assert` by stubbing nothing but the dispatcher itself. Create a scratch file (not committed — delete after this step):

```js
// scratch verification, delete after running
var LAW_TOOLS = {};
function lawRegisterTool(name, description, inputSchema, sensitive, run) {
  LAW_TOOLS[name] = { definition: { name: name, description: description, input_schema: inputSchema }, sensitive: !!sensitive, run: run };
}
function lawExecuteTool(name, role, input) {
  var tool = LAW_TOOLS[name];
  if (!tool) return { ok: false, error: 'No tool named "' + name + '" exists.' };
  if (tool.sensitive && role !== 'owner') return { ok: false, error: 'This data is restricted to the owner role.' };
  try { return { ok: true, result: tool.run(input || {}) }; } catch (e) { return { ok: false, error: 'Could not retrieve that data right now.' }; }
}

var assert = require('assert');

lawRegisterTool('ping', 'test tool', {type:'object'}, false, function () { return 'pong'; });
lawRegisterTool('secret', 'test sensitive tool', {type:'object'}, true, function () { return 'classified'; });
lawRegisterTool('broken', 'test throwing tool', {type:'object'}, false, function () { throw new Error('boom'); });

assert.deepStrictEqual(lawExecuteTool('ping', 'associate', {}), { ok: true, result: 'pong' });
assert.deepStrictEqual(lawExecuteTool('nonexistent', 'owner', {}), { ok: false, error: 'No tool named "nonexistent" exists.' });
assert.deepStrictEqual(lawExecuteTool('secret', 'associate', {}), { ok: false, error: 'This data is restricted to the owner role.' });
assert.deepStrictEqual(lawExecuteTool('secret', 'owner', {}), { ok: true, result: 'classified' });
assert.strictEqual(lawExecuteTool('broken', 'owner', {}).ok, false);

console.log('lawExecuteTool: all 5 checks passed');
```

Run: `node <scratch-file>.js`
Expected: `lawExecuteTool: all 5 checks passed`. Delete the scratch file afterward.

- [ ] **Step 4: Commit**

```bash
git add sairnlaw.html
git commit -m "feat: SAIRNlaw -- tool-calling dispatcher (LAW_TOOLS/lawExecuteTool)

Ports the mechanism proven live in SAIRNbiz. Registry + role-gated,
error-safe execution for read-only AI tools. No real tools registered
yet (Task 2) and sendAI() doesn't call this yet (Task 3) -- this is the
isolated mechanism, verified standalone."
```

---

### Task 2: `sairnlaw.html` — the `get_matters` tool

**Files:**
- Modify: `sairnlaw.html` (immediately after the `LAW_TOOLS`/`lawExecuteTool` block from Task 1)

**Interfaces:**
- Consumes: `lawRegisterTool(name, description, inputSchema, sensitive, run)` (Task 1), `matters()` (`sairnlaw.html:1278`, returns `ld('law_matters', [])`), `clientLabel(id)` (`sairnlaw.html:1288`, resolves a client id to its real name).
- Produces: nothing new consumed elsewhere — this is the leaf registration.

- [ ] **Step 1: Write the implementation**

Insert after the `lawExecuteTool` function from Task 1:

```js
lawRegisterTool(
  'get_matters',
  'Look up the firm\'s current matters: matter number, matter name, client name, practice area, status, responsible attorney, and opposing parties. Does NOT include deadlines, trust account balances, invoices, time entries, or matter notes -- those are not available to this tool.',
  { type: 'object', properties: {}, required: [] },
  false,
  function (input) {
    // input intentionally unused -- this tool takes no real arguments, but
    // accepts one for interface consistency with lawExecuteTool(name, role,
    // input), matching SAIRNbiz's get_employees convention.
    return matters().map(function (m) {
      return {
        matter_number: m.matter_number,
        matter_name: m.matter_name,
        client: clientLabel(m.client_id),
        practice_area: m.practice_area,
        status: m.status,
        responsible_attorney: m.responsible_attorney,
        opposing_parties: m.opposing_parties || []
      };
    });
  }
);
```

- [ ] **Step 2: Syntax-check**

Run: `python tools/checkblocks.py sairnlaw.html`
Expected: same `TOTAL_BLOCKS` as Task 1's result, `FAILED_BLOCKS:0`.

Run: `python tools/div_balance_check.py sairnlaw.html`
Expected: `RESULT:PASS`.

- [ ] **Step 3: Behavioral verification with a temporary Node harness**

Same technique as Task 1 Step 3 — the `run` function only touches `matters()`/`clientLabel()`, no DOM. Scratch file (not committed):

```js
var assert = require('assert');
var LAW_MATTERS = [
  { id: 'MT-1', matter_number: '2026-0001', client_id: 'CL-1', matter_name: 'Ostrander Estate Planning', practice_area: 'Estate Planning', status: 'Open', responsible_attorney: 'J. Ortiz', opposing_parties: [], notes: 'confidential family detail' },
  { id: 'MT-2', matter_number: '2026-0002', client_id: 'CL-2', matter_name: 'Delacroix v. Reyes Supply Co.', practice_area: 'Commercial Litigation', status: 'Open', responsible_attorney: 'S. Whitfield', opposing_parties: ['Reyes Supply Co.', 'Marcus Reyes'], notes: 'settlement strategy notes' }
];
var LAW_CLIENTS = [
  { id: 'CL-1', name: 'Margaret Ostrander' },
  { id: 'CL-2', name: 'Delacroix Manufacturing LLC' }
];
function matters() { return LAW_MATTERS; }
function clientLabel(id) { var c = LAW_CLIENTS.find(function (x) { return x.id === id; }); return c ? c.name : '(unknown client)'; }

var LAW_TOOLS = {};
function lawRegisterTool(name, description, inputSchema, sensitive, run) { LAW_TOOLS[name] = { definition: { name: name, description: description, input_schema: inputSchema }, sensitive: !!sensitive, run: run }; }

lawRegisterTool('get_matters', 'x', { type: 'object' }, false, function (input) {
  return matters().map(function (m) {
    return { matter_number: m.matter_number, matter_name: m.matter_name, client: clientLabel(m.client_id), practice_area: m.practice_area, status: m.status, responsible_attorney: m.responsible_attorney, opposing_parties: m.opposing_parties || [] };
  });
});

var out = LAW_TOOLS.get_matters.run({});
assert.strictEqual(out.length, 2);
assert.strictEqual(out[0].client, 'Margaret Ostrander', 'client_id must be resolved to a real name');
assert.strictEqual(out[1].opposing_parties.length, 2);
assert.strictEqual(out[0].notes, undefined, 'notes must never appear in get_matters output');
assert.strictEqual(out[0].matter_number, '2026-0001');

console.log('get_matters tool: all checks passed');
```

Run: `node <scratch-file>.js`
Expected: `get_matters tool: all checks passed`. Delete the scratch file afterward.

- [ ] **Step 4: Commit**

```bash
git add sairnlaw.html
git commit -m "feat: SAIRNlaw -- register get_matters as the v1 proof tool

Read-only matter lookup (number/name/client/practice area/status/
responsible attorney/opposing parties). notes and all date/trust/
billing fields deliberately excluded -- deadlines and trust-accounting
tools are later spec work, not this one's."
```

---

### Task 3: `sairnlaw.html` — rewire `sendAI()` for the tool-use round-trip

**Files:**
- Modify: `sairnlaw.html:1406-1452` (`sendAI()`)

**Interfaces:**
- Consumes: `lawExecuteTool(name, role, input)` (Task 1), `LAW_TOOLS` (Task 1, read via `Object.keys(LAW_TOOLS).map(k => LAW_TOOLS[k].definition)`), `PROXY`, `APP_ID`, `prole`, `aiHist`, `H()`, `$()`, `lawAiError()` (all existing globals/helpers used by the current `sendAI()`).
- Produces: no new exports — `sendAI()` keeps its existing signature and call sites (`askAI(q)`, `sairnlaw.html:1405`, and the chat input's own submit handler).

- [ ] **Step 1: Write the implementation**

Replace `sendAI()` (`sairnlaw.html:1406-1452`) with:

```js
async function sendAI(){
  var inp=$('ainp'),q=(inp.value||'').trim();
  if(!q)return;
  inp.value='';
  var chat=$('achat');
  if(chat.querySelector('div[style*="text-align:center"]'))chat.innerHTML='';
  chat.innerHTML+='<div class="amu">'+H(q)+'</div>';
  chat.scrollTop=chat.scrollHeight;
  aiHist.push({role:'user',content:q});
  var thinking=document.createElement('div');thinking.className='ama';thinking.textContent='Thinking...';chat.appendChild(thinking);
  chat.scrollTop=chat.scrollHeight;
  var toolDefs=Object.keys(LAW_TOOLS).map(function(k){return LAW_TOOLS[k].definition;});
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
  }catch(e){thinking.textContent='Could not connect to Claude. Check your connection and try again.';}
  chat.scrollTop=chat.scrollHeight;
}
```

Note: `aiHist.push({role:'assistant',content:q})` bug-check — the original code pushes the *user* message before the fetch and only pushes the assistant reply in the no-tool-use path; the tool-use path above pushes the assistant's tool-use turn (`blocks`) and the tool result before pushing the final text reply, mirroring SAIRNbiz's history-ordering requirement exactly (assistant tool-use turn must precede the user tool-result turn).

- [ ] **Step 2: Syntax-check the modified script block**

Run: `python tools/checkblocks.py sairnlaw.html`
Expected: same `TOTAL_BLOCKS` as Task 2's result, `FAILED_BLOCKS:0`.

Run: `python tools/div_balance_check.py sairnlaw.html`
Expected: `RESULT:PASS`.

- [ ] **Step 3: Live interaction test — no-tool path unaffected**

Open `sairnlaw.html` locally (or via the project's existing local-serve method), log in, ask the AI Assistant a question unrelated to any tool ("what should go in a demand letter" or similar). Confirm: exactly one "Thinking..." bubble appears and is replaced by one real answer, no console errors.

- [ ] **Step 4: Commit**

```bash
git add sairnlaw.html
git commit -m "feat: SAIRNlaw -- sendAI() supports the tool-use round-trip

Sends LAW_TOOLS' definitions, executes a requested tool via
lawExecuteTool() (role-gated, error-safe), sends the result back for a
final grounded answer. Anti-fabrication instruction added at both the
system-prompt level and next to the tool_result itself, matching the
platform-wide fix already live in SAIRNbiz."
```

---

### Task 4: `sairnlaw.html` — edit `LAW_FIRM_DATA_RULE` for the new access

**Files:**
- Modify: `sairnlaw.html:1403` (`LAW_FIRM_DATA_RULE`)

**Interfaces:**
- Consumes: none new.
- Produces: `LAW_FIRM_DATA_RULE` (existing global string, referenced by Task 3's `sys` construction) — same variable name, edited content.

- [ ] **Step 1: Write the implementation**

Replace `LAW_FIRM_DATA_RULE`'s definition (`sairnlaw.html:1403`) with:

```js
var LAW_FIRM_DATA_RULE='CRITICAL RULE: you now have tool-based access to this firm\'s current MATTERS (matter number, matter name, client name, practice area, status, responsible attorney, opposing parties) -- use the get_matters tool for any question about that data rather than guessing. You do NOT have access to this firm\'s deadlines, trust account balances, invoices, time entries, matter notes, or billing records -- none of that real data is available through any tool or included anywhere in this conversation. If asked something that depends on that still-unavailable data (e.g. "What is the trust balance on the Ostrander matter?", "Which deadlines are overdue?", "How much has this client been billed?"), you MUST say plainly that you do not have access to it and direct the user to the relevant panel (Trust Accounting, Deadlines, Billing) to look it up -- never guess, estimate, or invent a specific figure, date, or fact about that data. You may still help with general drafting, explaining concepts, and non-firm-specific questions.';
```

- [ ] **Step 2: Syntax-check**

Run: `python tools/checkblocks.py sairnlaw.html`
Expected: same `TOTAL_BLOCKS` as Task 3's result, `FAILED_BLOCKS:0`.

- [ ] **Step 3: Refusal-preserved live test**

With the app running locally, ask a deadline or trust-balance question ("what's overdue," "what's the trust balance on the Ostrander matter"). Confirm the model still refuses and redirects to the relevant panel — proving this edit didn't over-grant access it doesn't actually have. Then ask a matters question ("what matters do we have open," "who's the responsible attorney on the Delacroix matter") and confirm it now answers with real data instead of refusing.

- [ ] **Step 4: Commit**

```bash
git add sairnlaw.html
git commit -m "fix: SAIRNlaw -- LAW_FIRM_DATA_RULE reflects real get_matters access

Precise field-level edit, not a blanket removal: matters data is now
tool-accessible and the refusal for it is lifted; deadlines/trust/
billing remain genuinely unavailable and the refusal for those stays
exactly as strict as before."
```

---

### Task 5: End-to-end verification, push, live-verify

**Files:** none modified — verification only.

- [ ] **Step 1: Full local re-check of the changed file**

```bash
python tools/checkblocks.py sairnlaw.html
python tools/div_balance_check.py sairnlaw.html
```

Expected: both checks show 0 failures / PASS.

- [ ] **Step 2: Guardian v2 pass**

Run the full `sairn-guardian-v2` check (Check 0 + numbered checks) against `sairnlaw.html` before push, per the project's standing Push Protocol — not "syntax passed" alone.

- [ ] **Step 3: Real interaction test — matters question**

With the app running against real seeded data, ask the AI Assistant a matters question ("what matters are open," "who's the responsible attorney on the Delacroix matter," "list our current matters"). Confirm the answer contains real matter numbers/names/attorneys from `law_matters` — not the old "I don't have access" refusal.

- [ ] **Step 4: Refusal-preserved test**

Ask a deadline or trust-balance question ("what's overdue this week," "what's the trust balance on the Ostrander matter"). Confirm the model still refuses and redirects to the relevant panel — this is the regression check for Task 4's edit.

- [ ] **Step 5: Concurrency test**

Send two questions back-to-back before the first resolves — one that triggers `get_matters` and one that doesn't (e.g. "what matters are open" then immediately "what should go in a standard engagement letter"). Confirm both answers land under their own message bubble, no stuck "Thinking...", no misattributed answer. Live-test standard, not code review alone — this is the same bug class SAIRNbiz's rollout caught and fixed in sibling apps.

- [ ] **Step 6: Role-gate smoke check**

`get_matters` isn't sensitive, so this doesn't exercise the gate through the UI. Confirm the gate mechanism itself directly: open the browser console on the live app and run `lawExecuteTool('get_matters', 'owner', {})` and, temporarily, `LAW_TOOLS.get_matters.sensitive = true; lawExecuteTool('get_matters', 'associate', {});` — expect the second call to return `{ok:false, error:'This data is restricted to the owner role.'}`. Reload the page afterward (the temporary mutation is not persisted).

- [ ] **Step 7: `sanitizeTools()` regression check for this app_id specifically**

```bash
curl -s -X POST https://sairn.vercel.app/api/claude \
  -H 'Content-Type: application/json' \
  -d '{"app_id":"sairnlaw","is_demo":true,"max_tokens":50,"system":"test","messages":[{"role":"user","content":"say hi"}],"tools":[{"name":"get_matters","description":"x","input_schema":{"type":"object","properties":{}}}]}'
```

Expected: HTTP 200 with a real Anthropic response shape (`content` array present), not a 400 — confirms `sanitizeTools()` passes a `sairnlaw`-originated custom tool through unmodified against the real live proxy, not merely assumed from SAIRNbiz's own verification of the same shared function.

- [ ] **Step 8: Push**

```bash
git push origin main
```

- [ ] **Step 9: Live-verify**

```bash
curl -s https://sairn.vercel.app/sairnlaw | grep -c "lawExecuteTool"
```

Expected: non-zero (confirms the deployed file includes the new dispatcher). Then repeat Steps 3-4's real interaction tests against the **live** URL, not just a local copy — per the project's standing rule that a clean push is not proof the live app reflects the change.

- [ ] **Step 10: Update the spec's status line**

Edit `docs/superpowers/specs/2026-08-10-sairnlaw-ai-tool-calling-design.md`'s `**Status:**` line to note the foundation is implemented and live-verified, with the date. Commit this doc-only change separately.
