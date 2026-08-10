# SAIRNvet AI Tool-Calling Foundation + get_patients Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give SAIRNvet's general AI chat (`askAI()`, `sairnvet.html:7036`) real function-calling access to the app's own patient roster, via one proof tool (`get_patients`), porting the mechanism already proven live in SAIRNbiz and SAIRNlaw — adapted for two real differences found during design (`docs/superpowers/specs/2026-08-10-sairnvet-ai-tool-calling-design.md`, §1): no sensitivity/role-gate concept (SAIRNvet's `role` is a self-selected dropdown, never server-verified), and a new `callClaudeWithTools()` function kept fully separate from the shared `callClaude()` helper used by 6 other AI features.

**Architecture:** `SV_TOOLS`/`svRegisterTool`/`svExecuteTool` — same registry shape as SAIRNbiz's `SB_TOOLS`/SAIRNlaw's `LAW_TOOLS`, minus the `sensitive`/role parameter. A new `callClaudeWithTools(system, messages, tools, maxTokens)` sends `tools` and returns raw content blocks (not pre-extracted text), used only by `askAI()`. `askAI()`'s existing `askAiSeq`/`myAskAiSeq` stale-response-discard guard is reused and extended to cover both fetches of a tool-use round-trip, rather than introducing a busy-guard/toast pattern this file doesn't otherwise use.

**Tech Stack:** Vanilla JS (`sairnvet.html`, no framework). Verified the same way `get_matters`/`get_deadlines` were: `tools/checkblocks.py` / `tools/div_balance_check.py` on the file, a temporary `node:assert` scratch harness for pure logic, plus a real live-interaction test against the deployed app.

## Global Constraints

- Read-only tool only — `get_patients` may not create, modify, or delete any record. (Spec §2)
- No new persistence — reads live from `getPatients()` (`sairnvet.html:3954`). (Spec §2)
- No sensitivity/role-gate concept anywhere in this dispatcher — `svRegisterTool(name, description, inputSchema, run)`, `svExecuteTool(name, input)`, no third/second parameter for it. (Spec §1, §3)
- `callClaude()` (`sairnvet.html:1904-1932`) and its 6 other callers (`calculateDoseAI`, `getProtocolFromClaude`, the SOAP-note generator, the species-reference generator, the revenue-recovery analytics function, `getZooProtocol`) must not be modified. `callClaudeWithTools()` is new and separate. (Spec §1, §3)
- `askAI()`'s existing dosing/diagnosis refusal ("do NOT provide a specific number or a single diagnosis here...") stays intact — this spec only adds patient-lookup capability alongside it, never loosens it. (Spec §3)
- Reuse the existing `askAiSeq`/`myAskAiSeq` guard, extended to both fetch callbacks in a tool-use exchange — do not introduce a new busy-guard/toast mechanism. (Spec §1)
- `get_patients` returns `{name, species, breed, owner, age, lastVisit, status, visitsThisYear}` only — `id`, `added`, and `chartComplete` excluded. (Spec §4)
- No changes to `api/claude.js` — `sanitizeTools()` already passes custom tools through for `sairnvet`. (Spec §2)
- `python tools/checkblocks.py sairnvet.html` and `python tools/div_balance_check.py sairnvet.html` must stay clean (0 failed / PASS) after every change.
- Before push: full Guardian v2 check on `sairnvet.html`. After push: live-verify against `sairn.vercel.app/sairnvet` directly, not assumed from a clean push (project Push Protocol).

---

### Task 1: `sairnvet.html` — tool registry, dispatcher, and the `get_patients` tool

**Files:**
- Modify: `sairnvet.html` (insert immediately after `getPatients()`/`savePatients()` at `sairnvet.html:3954-3974`, before `renderPatients()`)

**Interfaces:**
- Consumes: `getPatients()` (`sairnvet.html:3954`, returns an array of patient records from `localStorage`'s `sv_patients` key).
- Produces: `SV_TOOLS` (object, tool name → `{definition, run}` — no `sensitive` field), `svExecuteTool(name, input)` → `{ok: true, result: any} | {ok: false, error: string}` — used by Task 3.

- [ ] **Step 1: Write the implementation**

Insert after `savePatients()`'s closing `}` (`sairnvet.html:3974`), before `function renderPatients(){`:

```js
// AI tool-calling dispatcher (2026-08-10) -- ports the mechanism proven
// live in SAIRNbiz and SAIRNlaw, minus the sensitivity/role-gate concept:
// SAIRNvet's `role` is a self-selected dropdown at login
// (sairnvet.html:1981), never server-verified, so a "sensitive" flag
// here would restrict nothing a user couldn't bypass by picking a
// different option. See
// docs/superpowers/specs/2026-08-10-sairnvet-ai-tool-calling-design.md
var SV_TOOLS = {};

function svRegisterTool(name, description, inputSchema, run) {
  SV_TOOLS[name] = {
    definition: { name: name, description: description, input_schema: inputSchema },
    run: run
  };
}

function svExecuteTool(name, input) {
  var tool = SV_TOOLS[name];
  if (!tool) return { ok: false, error: 'No tool named "' + name + '" exists.' };
  try {
    return { ok: true, result: tool.run(input || {}) };
  } catch (e) {
    return { ok: false, error: 'Could not retrieve that data right now.' };
  }
}

svRegisterTool(
  'get_patients',
  'Look up the practice\'s current patient roster: name, species, breed, owner, age, last visit date, status, and visits this year. Does NOT include weight, vitals, lab results, or any medical/financial record -- those are not available to this tool.',
  { type: 'object', properties: {}, required: [] },
  function (input) {
    // input intentionally unused -- this tool takes no real arguments, but
    // accepts one for interface consistency with svExecuteTool(name, input),
    // matching get_matters'/get_employees' convention.
    return getPatients().map(function (p) {
      return {
        name: p.name,
        species: p.species,
        breed: p.breed,
        owner: p.owner,
        age: p.age,
        lastVisit: p.lastVisit,
        status: p.status,
        visitsThisYear: p.visitsThisYear
      };
    });
  }
);
```

- [ ] **Step 2: Syntax-check the modified script block**

Run: `python tools/checkblocks.py sairnvet.html`
Expected: same `TOTAL_BLOCKS` as the pre-change baseline (run it once before this edit if you don't already know the number), `FAILED_BLOCKS:0`.

Run: `python tools/div_balance_check.py sairnvet.html`
Expected: `RESULT:PASS`.

- [ ] **Step 3: Behavioral verification with a temporary Node harness**

Both the dispatcher and the tool's `run()` have no DOM dependency. Create a scratch file (not committed — delete after this step):

```js
// scratch verification, delete after running
var assert = require('assert');

var SV_TOOLS = {};
function svRegisterTool(name, description, inputSchema, run) {
  SV_TOOLS[name] = { definition: { name: name, description: description, input_schema: inputSchema }, run: run };
}
function svExecuteTool(name, input) {
  var tool = SV_TOOLS[name];
  if (!tool) return { ok: false, error: 'No tool named "' + name + '" exists.' };
  try { return { ok: true, result: tool.run(input || {}) }; } catch (e) { return { ok: false, error: 'Could not retrieve that data right now.' }; }
}

// -- dispatcher checks --
svRegisterTool('ping', 'test tool', {type:'object'}, function () { return 'pong'; });
svRegisterTool('broken', 'test throwing tool', {type:'object'}, function () { throw new Error('boom'); });
assert.deepStrictEqual(svExecuteTool('ping', {}), { ok: true, result: 'pong' });
assert.deepStrictEqual(svExecuteTool('nonexistent', {}), { ok: false, error: 'No tool named "nonexistent" exists.' });
assert.strictEqual(svExecuteTool('broken', {}).ok, false);
console.log('svExecuteTool: all 3 checks passed');

// -- get_patients tool check, stubbing getPatients() --
var SV_PATIENTS = [
  { id: 'pt1', name: 'Max', species: 'Canine', breed: 'Golden Retriever', owner: 'Smith, John', age: 5, lastVisit: '2026-07-05', status: 'Healthy', added: '2025-03-12', visitsThisYear: 3, chartComplete: true },
  { id: 'pt2', name: 'Whiskers', species: 'Feline', breed: 'Persian', owner: 'Doe, Jane', age: 8, lastVisit: '2026-07-04', status: 'Follow-up', added: '2023-11-02', visitsThisYear: 2, chartComplete: true }
];
function getPatients() { return SV_PATIENTS; }

svRegisterTool('get_patients', 'x', { type: 'object' }, function (input) {
  return getPatients().map(function (p) {
    return { name: p.name, species: p.species, breed: p.breed, owner: p.owner, age: p.age, lastVisit: p.lastVisit, status: p.status, visitsThisYear: p.visitsThisYear };
  });
});

var out = SV_TOOLS.get_patients.run({});
assert.strictEqual(out.length, 2);
assert.strictEqual(out[0].name, 'Max');
assert.strictEqual(out[1].species, 'Feline');
assert.strictEqual(out[0].id, undefined, 'id must never appear in get_patients output');
assert.strictEqual(out[0].added, undefined, 'added must never appear in get_patients output');
assert.strictEqual(out[0].chartComplete, undefined, 'chartComplete must never appear in get_patients output');
console.log('get_patients tool: all 5 checks passed');
```

Run: `node <scratch-file>.js`
Expected: `svExecuteTool: all 3 checks passed` then `get_patients tool: all 5 checks passed`. Delete the scratch file afterward.

- [ ] **Step 4: Commit**

```bash
git add sairnvet.html
git commit -m "feat: SAIRNvet -- tool-calling dispatcher + get_patients proof tool

Ports the mechanism proven live in SAIRNbiz/SAIRNlaw, minus the
sensitivity/role-gate concept -- SAIRNvet's role is a self-selected
dropdown, never server-verified, so a sensitive flag here would be
non-functional structure. SV_TOOLS/svRegisterTool/svExecuteTool plus
one read-only tool, get_patients (name/species/breed/owner/age/
lastVisit/status/visitsThisYear). id, added, and chartComplete
deliberately excluded. askAI() doesn't call this yet (later commits)
-- verified standalone via a Node harness."
```

---

### Task 2: `sairnvet.html` — `callClaudeWithTools()`, parallel to `callClaude()`

**Files:**
- Modify: `sairnvet.html` (insert immediately after `callClaude()`'s closing `}` at `sairnvet.html:1932`)

**Interfaces:**
- Consumes: `PROXY`, `APP_ID` (existing globals, already used by `callClaude()`), `showToast(message, type, duration)` (existing, already used by `callClaude()`).
- Produces: `callClaudeWithTools(system, messages, tools, maxTokens)` → `Promise<Array>` resolving to the raw `data.content` blocks array (not a plain string) — used by Task 3. Throws the same way `callClaude()` does on `demo_limit`/non-OK-status/connection errors, with its own toasts (duplicated deliberately, not shared, per the design's decision to keep `callClaude()` completely unmodified).

- [ ] **Step 1: Write the implementation**

Insert after `callClaude()`'s closing `}` (`sairnvet.html:1932`):

```js
// New, separate from callClaude() -- NOT a modification of it. callClaude()
// is used by 6 other AI features (dosing calculator, differential
// diagnosis, SOAP notes, species reference, revenue-recovery analytics,
// zoo protocol) and always assumes a plain-text reply; a tool_use-only
// response has no .text and would incorrectly hit callClaude()'s "Empty
// response" error path. This function sends `tools` and returns the raw
// content blocks array so the caller can inspect it for a tool_use block,
// leaving callClaude() and its 6 callers completely untouched.
async function callClaudeWithTools(system, messages, tools, maxTokens) {
  try {
    var res = await fetch(PROXY, {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({
        app_id:APP_ID, is_demo:true,
        system:system, messages:messages, tools:tools,
        max_tokens:maxTokens||1000
      })
    });
    var data = await res.json();
    if(data.error==='demo_limit'||(typeof data.error==='string'&&data.error.includes('limit'))){
      showToast('Demo limit reached. Email michael@sairn.com for license.','error',6000);
      throw new Error('demo_limit');
    }
    if(!res.ok){
      var em=(data.error&&data.error.message)?data.error.message:(typeof data.error==='string'?data.error:'Error '+res.status);
      showToast('Claude: '+em,'error',4000); throw new Error(em);
    }
    var blocks = (data.content) || [];
    if(!blocks.length){showToast('Empty response — try again.','error',3000);throw new Error('empty');}
    return blocks;
  } catch(e){
    if(e.message!=='demo_limit'&&e.message!=='empty') showToast('Connection error.','error',4000);
    throw e;
  }
}
```

- [ ] **Step 2: Syntax-check**

Run: `python tools/checkblocks.py sairnvet.html`
Expected: same `TOTAL_BLOCKS` as Task 1's result, `FAILED_BLOCKS:0`.

Run: `python tools/div_balance_check.py sairnvet.html`
Expected: `RESULT:PASS`.

- [ ] **Step 3: Confirm `callClaude()` itself is byte-for-byte unchanged**

```bash
git diff sairnvet.html | grep -A2 -B2 "^-.*callClaude\b" | grep -v callClaudeWithTools
```

Expected: no output showing a line removed from inside the original `callClaude()` function body (`sairnvet.html:1904-1932`) — only additions after it. This is the direct verification that the 6 existing callers are provably untouched, not just assumed so.

- [ ] **Step 4: Commit**

```bash
git add sairnvet.html
git commit -m "feat: SAIRNvet -- callClaudeWithTools(), separate from callClaude()

New function for tool-use exchanges, returning raw content blocks
instead of pre-extracted text. callClaude() and its 6 other callers
are completely unmodified -- zero risk to already-shipped dosing/
diagnosis/SOAP/reference/analytics/zoo features. Not called anywhere
yet (next commit rewires askAI() to use it)."
```

---

### Task 3: `sairnvet.html` — rewire `askAI()` for the tool-use round-trip

**Files:**
- Modify: `sairnvet.html:7035-7054` (`askAI()`)

**Interfaces:**
- Consumes: `svExecuteTool(name, input)` (Task 1), `SV_TOOLS` (Task 1, read via `Object.keys(SV_TOOLS).map(k => SV_TOOLS[k].definition)`), `callClaudeWithTools(system, messages, tools, maxTokens)` (Task 2), `buildSvSharedCompanyContext()` (`sairnvet.html:7630`, existing), `recordSvSharedTopics(text)` (`sairnvet.html:7609`, existing), `logDoseAudit(entry)` (`sairnvet.html:6355`, existing).
- Produces: no new exports — `askAI()` keeps its existing signature and call site (the "Ask AI" button's `onclick`).

- [ ] **Step 1: Write the implementation**

Replace `askAI()` (`sairnvet.html:7036-7054`) with:

```js
function askAI(){
  var q=document.getElementById('ai-question').value.trim();
  if(!q){showToast('Enter a question','error');return;}
  var toolDefs=Object.keys(SV_TOOLS).map(function(k){return SV_TOOLS[k].definition;});
  var system='You are a general veterinary knowledge assistant. Answer clearly and accurately. IMPORTANT: if the question asks for a specific numeric drug dose or asks you to diagnose a specific patient, do NOT provide a specific number or a single diagnosis here -- this tool is not connected to the verified drug/diagnosis database or the contraindication safety checks. Instead, tell the user to use the AI Dosing Calculator (for verified, bounds-checked doses) or the Diagnosis Library / Diagnosis Protocol Generator (for a grounded, ranked differential) so the safety checks actually run. You may still discuss general concepts, mechanisms, and reasoning freely, and you may look up real patient roster information (name, species, breed, owner, age, last visit, status) via the get_patients tool when asked -- never guess or invent a specific figure, date, or fact a tool would have provided.';
  var sharedCtx=(typeof buildSvSharedCompanyContext==='function')?buildSvSharedCompanyContext():'';
  if(sharedCtx) system+='\n\n'+sharedCtx;
  showToast('Asking Claude...','info');
  logDoseAudit({type:'ai_assistant_question', question:q.slice(0,200)});
  if(typeof recordSvSharedTopics==='function') recordSvSharedTopics(q);
  askAiSeq++;
  var myAskAiSeq=askAiSeq;
  callClaudeWithTools(system,[{role:'user',content:q}],toolDefs,1500).then(function(blocks){
    if(myAskAiSeq!==askAiSeq) return;
    var toolUse=blocks.filter(function(b){return b.type==='tool_use';})[0];
    if(!toolUse){
      var rep=(blocks[0]&&blocks[0].text)||'No response text returned.';
      document.getElementById('ai-result').style.display='block';
      document.getElementById('ai-result').textContent=rep;
      return;
    }
    var outcome=svExecuteTool(toolUse.name,toolUse.input);
    // Belt-and-suspenders, same pattern proven in SAIRNbiz/SAIRNlaw:
    // reinforce the anti-fabrication instruction right next to the
    // trigger, in the same turn as the denial/error itself.
    var toolResultContent=outcome.ok?JSON.stringify(outcome.result):('Error: '+outcome.error+' Do not estimate or substitute your own figures for this -- state the error plainly and stop.');
    var followUpMessages=[
      {role:'user',content:q},
      {role:'assistant',content:blocks},
      {role:'user',content:[{type:'tool_result',tool_use_id:toolUse.id,content:toolResultContent}]}
    ];
    callClaudeWithTools(system,followUpMessages,undefined,1500).then(function(blocks2){
      if(myAskAiSeq!==askAiSeq) return;
      var rep2=(blocks2[0]&&blocks2[0].text)||'No response text returned.';
      document.getElementById('ai-result').style.display='block';
      document.getElementById('ai-result').textContent=rep2;
    }).catch(function(e){});
  }).catch(function(e){});
}
```

Note: `tools:undefined` on the follow-up call — `JSON.stringify` omits an `undefined`-valued object property entirely, so the second request body has no `tools` field at all, matching the single-round-trip contract already used by SAIRNbiz/SAIRNlaw (the follow-up call never expects another `tool_use`).

- [ ] **Step 2: Syntax-check the modified script block**

Run: `python tools/checkblocks.py sairnvet.html`
Expected: same `TOTAL_BLOCKS` as Task 2's result, `FAILED_BLOCKS:0`.

Run: `python tools/div_balance_check.py sairnvet.html`
Expected: `RESULT:PASS`.

- [ ] **Step 3: Live interaction test — no-tool path unaffected**

Open `sairnvet.html` locally (or via the project's existing local-serve method), ask the general AI assistant a question unrelated to any tool ("what are common signs of hyperthyroidism in cats"). Confirm: the result area shows one real answer, no console errors, and the existing dosing/diagnosis refusal still works when tested directly (ask "what dose of amoxicillin for a 10kg dog" via this same general chat — confirm it still refuses and redirects to the Dosing Calculator, not a number).

- [ ] **Step 4: Commit**

```bash
git add sairnvet.html
git commit -m "feat: SAIRNvet -- askAI() supports the tool-use round-trip

Sends SV_TOOLS' definitions via the new callClaudeWithTools(), executes
a requested tool via svExecuteTool() (error-safe, no role check per
this app's design decision), sends the result back for a final grounded
answer via a second callClaudeWithTools() call with no tools field.
Existing dosing/diagnosis refusal instruction preserved unchanged.
Reuses the existing askAiSeq/myAskAiSeq stale-response guard, extended
to both fetch callbacks."
```

---

### Task 4: End-to-end verification, push, live-verify

**Files:** none modified — verification only.

- [ ] **Step 1: Full local re-check of the changed file**

```bash
python tools/checkblocks.py sairnvet.html
python tools/div_balance_check.py sairnvet.html
```

Expected: both checks show 0 failures / PASS.

- [ ] **Step 2: Guardian v2 pass**

Run the full `sairn-guardian-v2` check (Check 0 + numbered checks) against `sairnvet.html` before push, per the project's standing Push Protocol.

- [ ] **Step 3: Real interaction test — patient roster question**

With the app running against real seeded data, ask the general AI assistant a patient question ("do we have a patient named Max," "what species is Whiskers," "list our patients"). Confirm the answer contains real names/species/owners from `sv_patients` — not a generic non-answer.

- [ ] **Step 4: Refusal-preserved test**

Ask for a specific numeric dose or a single diagnosis via the same general chat ("what's the exact dose of amoxicillin for a 10kg dog," "what does my patient have"). Confirm it still refuses and redirects to the AI Dosing Calculator / Diagnosis Library — the regression check proving `get_patients`'s addition didn't loosen this existing, safety-critical refusal.

- [ ] **Step 5: No-regression spot check on `callClaude()`'s other callers**

Exercise at least two of the 6 untouched features directly (e.g., the AI Dosing Calculator and the Diagnosis Protocol Generator) and confirm they still work exactly as before — real, live calls, not just re-reading the code.

- [ ] **Step 6: Stale-response-guard test**

Send two `askAI()` questions back-to-back before the first resolves — one that triggers `get_patients` and one that doesn't. Confirm only the *later* question's answer ever renders in the result area (matching the existing `askAiSeq` convention), with no mixed or stuck state across the tool-use round-trip specifically.

- [ ] **Step 7: `sanitizeTools()` regression check for this app_id specifically**

```bash
curl -s -X POST https://sairn.vercel.app/api/claude \
  -H 'Content-Type: application/json' \
  -d '{"app_id":"sairnvet","is_demo":true,"max_tokens":50,"system":"test","messages":[{"role":"user","content":"say hi"}],"tools":[{"name":"get_patients","description":"x","input_schema":{"type":"object","properties":{}}}]}'
```

Expected: HTTP 200 with a real Anthropic response shape (`content` array present), not a 400.

- [ ] **Step 8: Push**

```bash
git push origin main
```

- [ ] **Step 9: Live-verify**

```bash
curl -s https://sairn.vercel.app/sairnvet | grep -c "svExecuteTool"
```

Expected: non-zero. Then repeat Steps 3-6's tests against the **live** URL, not just a local copy — per the project's standing rule that a clean push is not proof the live app reflects the change.

- [ ] **Step 10: Update the spec's status line**

Edit `docs/superpowers/specs/2026-08-10-sairnvet-ai-tool-calling-design.md`'s `**Status:**` line to note the foundation and `get_patients` are implemented and live-verified, with the date. Commit this doc-only change separately.
