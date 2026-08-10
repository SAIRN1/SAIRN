# SAIRNgrounds AI Tool-Calling Foundation + get_properties Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give SAIRNgrounds' general AI chat (`callAI()`, `sairngrounds.html:3543`) real function-calling access to the company's own property roster, via one proof tool (`get_properties`), porting the mechanism already proven live in SAIRNbiz/SAIRNlaw/SAIRNvet/SAIRNscape — and, as a required part of the same rollout, fixing a real pre-existing concurrency bug: `aiHist` is a shared, persistent, multi-turn history array with zero guard of any kind, the exact same architecture shape that caused SAIRNlaw's live-observed corruption bug and that was already found and fixed in SAIRNscape.

**Architecture:** `GRD_TOOLS`/`grdRegisterTool`/`grdExecuteTool` — same registry shape as SAIRNscape's `SCP_TOOLS`, including the `sensitive`/role parameter (real, server-verified roles already gate two other features in this file). `grdAiBusy` (new) guards `sendAI()`/`callAI()` exactly like `scpAiBusy` guards SAIRNscape's `scpCallAI()`. `callAI()` is rewired for a tool-use round-trip, kept in its existing `.then()`-chain style (no orthogonal style change).

**Tech Stack:** Vanilla JS (`sairngrounds.html`, no framework). Verified the same way every prior rollout was: `tools/checkblocks.py` / `tools/div_balance_check.py` on the file, a temporary `node:assert` scratch harness for pure logic, plus a real live-interaction test against the deployed app.

## Global Constraints

- Read-only tool only — `get_properties` may not create, modify, or delete any record. (Spec §2)
- No new persistence — reads live from `ld('grd_properties', [])`. (Spec §2)
- `get_properties` returns `{name, type, contact, phone, email, acreage, address, status}` only — `id` and `notes` excluded. (Spec §4)
- `get_properties` is non-sensitive (`sensitive:false`), but the dispatcher itself supports a `sensitive`/role parameter. (Spec §1, §4)
- `grdExecuteTool`'s role check is `sensitive && role !== 'owner'` — the exact same single-role check as every prior rollout. This is **not** SAIRNgrounds' own separate `GRD_QC_AUTHORITY_ROLES`/`MSB_VOID_AUTHORITY_ROLES` multi-role concepts (`sairngrounds.html:1950`, `3026`) — those gates belong to different features and are not inherited here. (Spec §3)
- `role` for `grdExecuteTool` calls comes from the existing `grdCurrentRole()` helper (`sairngrounds.html:1942`), read on-demand — not cached into a new global variable. (Spec §3)
- The pre-existing concurrency bug (unguarded shared `aiHist`) must be fixed as part of this rollout, not deferred — `grdAiBusy`, same shape as `scpAiBusy`/`lawAiBusy`: `sendAI()` rejects a second send with a toast while busy; `callAI()` sets it `true` at start, clears it on every exit path. (Spec §0, §1, §3)
- `grdUploadProgressPhoto()`, `genEcosystemReport()`, `dcAnalyze()`, the bar-inventory scanners, and `api/claude.js` are not touched. (Spec §2)
- `python tools/checkblocks.py sairngrounds.html` and `python tools/div_balance_check.py sairngrounds.html` must stay clean (0 failed / PASS) after every change.
- Before push: full Guardian v2 check on `sairngrounds.html`. After push: live-verify against `sairn.vercel.app/sairngrounds` directly, not assumed from a clean push (project Push Protocol).

---

### Task 1: `sairngrounds.html` — tool registry, dispatcher, and the `get_properties` tool

**Files:**
- Modify: `sairngrounds.html` (insert immediately after the globals line `var zid=null,jid=null,qid=null,pid=null,aiHist=[];` at `sairngrounds.html:1111`, before `function ld(k,d){...}` at `sairngrounds.html:1115`)

**Interfaces:**
- Consumes: `ld(k, d)` (`sairngrounds.html:1115`, existing localStorage getter).
- Produces: `GRD_TOOLS` (object, tool name → `{definition, sensitive, run}`), `grdExecuteTool(name, role, input)` → `{ok: true, result: any} | {ok: false, error: string}`, `grdAiBusy` (boolean, initialized `false`) — all used by Task 2.

- [ ] **Step 1: Write the implementation**

Insert immediately after `var zid=null,jid=null,qid=null,pid=null,aiHist=[];` (`sairngrounds.html:1111`):

```js
// AI tool-calling dispatcher (2026-08-10) -- ports the mechanism proven
// live in SAIRNbiz/SAIRNlaw/SAIRNvet/SAIRNscape. Registry of read-only
// tools callAI() may request via Claude's tool-use. Every tool is:
//   - read-only (never creates/modifies/deletes anything)
//   - wrapped so a thrown error or unexpected data shape becomes an honest
//     {ok:false} result, never a crash or a silently wrong answer
//   - checked against the CALLING role before running, if marked sensitive
//     (same single-role check as SAIRNbiz's sbExecuteTool/SAIRNlaw's
//     lawExecuteTool/SAIRNscape's scpExecuteTool -- NOT this file's own
//     separate GRD_QC_AUTHORITY_ROLES/MSB_VOID_AUTHORITY_ROLES multi-role
//     concepts, different features)
// See docs/superpowers/specs/2026-08-10-sairngrounds-ai-tool-calling-design.md
var GRD_TOOLS = {};

function grdRegisterTool(name, description, inputSchema, sensitive, run) {
  GRD_TOOLS[name] = {
    definition: { name: name, description: description, input_schema: inputSchema },
    sensitive: !!sensitive,
    run: run
  };
}

function grdExecuteTool(name, role, input) {
  var tool = GRD_TOOLS[name];
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

// Concurrency guard (2026-08-10) -- found necessary during design, not
// discovered live: aiHist is a shared, persistent, multi-turn history
// array (same shape as SAIRNlaw's aiHist/SAIRNscape's scpAiHist) that had
// ZERO guard before this change. Two concurrent callAI() calls would both
// read/write the same array, corrupting each other's context -- the exact
// bug class already found and fixed live in SAIRNlaw and SAIRNscape. Same
// fix shape: block a second send outright rather than trying to make
// concurrent shared-history calls safe.
var grdAiBusy = false;

grdRegisterTool(
  'get_properties',
  'Look up the company\'s current property roster: name, type, contact, phone, email, acreage, address, and status. Does NOT include job history, schedule, invoices, quotes, or property notes -- those are not available to this tool.',
  { type: 'object', properties: {}, required: [] },
  false,
  function (input) {
    // input intentionally unused -- this tool takes no real arguments, but
    // accepts one for interface consistency with grdExecuteTool(name, role,
    // input), matching get_customers'/get_matters' convention.
    return ld('grd_properties', []).map(function (p) {
      return {
        name: p.name,
        type: p.type,
        contact: p.contact,
        phone: p.phone,
        email: p.email,
        acreage: p.acreage,
        address: p.address,
        status: p.status
      };
    });
  }
);
```

- [ ] **Step 2: Syntax-check the modified script block**

Run: `python tools/checkblocks.py sairngrounds.html`
Expected: same `TOTAL_BLOCKS` as the pre-change baseline (run it once before this edit if you don't already know the number), `FAILED_BLOCKS:0`.

Run: `python tools/div_balance_check.py sairngrounds.html`
Expected: `RESULT:PASS`.

- [ ] **Step 3: Behavioral verification with a temporary Node harness**

Both the dispatcher and the tool's `run()` have no DOM dependency. Create a scratch file (not committed — delete after this step):

```js
// scratch verification, delete after running
var assert = require('assert');

var GRD_TOOLS = {};
function grdRegisterTool(name, description, inputSchema, sensitive, run) {
  GRD_TOOLS[name] = { definition: { name: name, description: description, input_schema: inputSchema }, sensitive: !!sensitive, run: run };
}
function grdExecuteTool(name, role, input) {
  var tool = GRD_TOOLS[name];
  if (!tool) return { ok: false, error: 'No tool named "' + name + '" exists.' };
  if (tool.sensitive && role !== 'owner') return { ok: false, error: 'This data is restricted to the owner role.' };
  try { return { ok: true, result: tool.run(input || {}) }; } catch (e) { return { ok: false, error: 'Could not retrieve that data right now.' }; }
}

// -- dispatcher + role-gate checks --
grdRegisterTool('ping', 'test tool', {type:'object'}, false, function () { return 'pong'; });
grdRegisterTool('secret', 'test sensitive tool', {type:'object'}, true, function () { return 'classified'; });
grdRegisterTool('broken', 'test throwing tool', {type:'object'}, false, function () { throw new Error('boom'); });

assert.deepStrictEqual(grdExecuteTool('ping', 'manager', {}), { ok: true, result: 'pong' });
assert.deepStrictEqual(grdExecuteTool('nonexistent', 'owner', {}), { ok: false, error: 'No tool named "nonexistent" exists.' });
assert.deepStrictEqual(grdExecuteTool('secret', 'superintendent', {}), { ok: false, error: 'This data is restricted to the owner role.' });
assert.deepStrictEqual(grdExecuteTool('secret', 'manager', {}), { ok: false, error: 'This data is restricted to the owner role.' });
assert.deepStrictEqual(grdExecuteTool('secret', 'owner', {}), { ok: true, result: 'classified' });
assert.strictEqual(grdExecuteTool('broken', 'owner', {}).ok, false);
console.log('grdExecuteTool: all 6 checks passed');

// -- get_properties tool check, stubbing ld() --
var GRD_PROPERTIES = [
  { id: 'P-001', name: 'Fairview Golf Club', type: 'golf', contact: 'Jane Reynolds', phone: '(440) 555-0120', email: 'jane@fairview.example', acreage: 145, address: '4200 Fairway Dr, Westlake OH', status: 'Active', notes: '18-hole championship course' },
  { id: 'P-002', name: 'Rocky River Estates HOA', type: 'hoa', contact: 'Tom Baird', phone: '(440) 555-0121', email: 'tbaird@rrehoa.example', acreage: 22, address: '110 Estates Blvd, Rocky River OH', status: 'Active', notes: 'Common areas + entrance beds' }
];
function ld(k, d) { return k === 'grd_properties' ? GRD_PROPERTIES : d; }

grdRegisterTool('get_properties', 'x', { type: 'object' }, false, function (input) {
  return ld('grd_properties', []).map(function (p) {
    return { name: p.name, type: p.type, contact: p.contact, phone: p.phone, email: p.email, acreage: p.acreage, address: p.address, status: p.status };
  });
});

var out = GRD_TOOLS.get_properties.run({});
assert.strictEqual(out.length, 2);
assert.strictEqual(out[0].name, 'Fairview Golf Club');
assert.strictEqual(out[1].type, 'hoa');
assert.strictEqual(out[0].id, undefined, 'id must never appear in get_properties output');
assert.strictEqual(out[1].notes, undefined, 'notes must never appear in get_properties output');
console.log('get_properties tool: all 4 checks passed');
```

Run: `node <scratch-file>.js`
Expected: `grdExecuteTool: all 6 checks passed` then `get_properties tool: all 4 checks passed`. Delete the scratch file afterward.

- [ ] **Step 4: Commit**

```bash
git add sairngrounds.html
git commit -m "feat: SAIRNgrounds -- tool-calling dispatcher + get_properties proof tool

Ports the mechanism proven live in SAIRNbiz/SAIRNlaw/SAIRNvet/SAIRNscape,
WITH the sensitive/role-gate parameter since SAIRNgrounds has real,
server-verified roles already in active use for two other features
(GRD_QC_AUTHORITY_ROLES, MSB_VOID_AUTHORITY_ROLES). GRD_TOOLS/
grdRegisterTool/grdExecuteTool plus one read-only tool, get_properties
(name/type/contact/phone/email/acreage/address/status). id and notes
deliberately excluded. Also adds grdAiBusy (unused until Task 2) -- the
concurrency guard callAI()'s shared aiHist array has never had.
callAI() doesn't call any of this yet -- verified standalone via a Node
harness."
```

---

### Task 2: `sairngrounds.html` — `callAI()` tool-use round-trip + `grdAiBusy` guard

**Files:**
- Modify: `sairngrounds.html:3539-3563` (`sendAI()`, `callAI()`)

**Interfaces:**
- Consumes: `grdExecuteTool(name, role, input)` (Task 1), `GRD_TOOLS` (Task 1, read via `Object.keys(GRD_TOOLS).map(k => GRD_TOOLS[k].definition)`), `grdAiBusy` (Task 1), `grdCurrentRole()` (`sairngrounds.html:1942`, existing), `toast(m, d)` (`sairngrounds.html:1119`, existing), `addMsg(t, role)` (`sairngrounds.html:3542`, existing, already returns its DOM node), `PROXY`, `APP_ID`, `aiHist`, `buildGrdSharedCompanyContext()`/`recordGrdSharedTopics(msg)` (`sairngrounds.html:3581`/`3577`, existing, untouched).
- Produces: no new exports — `sendAI()`/`callAI(msg)` keep their existing signatures and call sites (`askAI(q)`, `sairngrounds.html:3540`).

- [ ] **Step 1: Write the implementation**

Replace `sendAI()` (`sairngrounds.html:3539`) with:

```js
function sendAI(){if(grdAiBusy){toast('Please wait for the current response first');return;}var inp=$('ainp');var m=(inp.value||'').trim();if(!m)return;inp.value='';addMsg(m,'u');callAI(m);}
```

Replace `callAI(msg)` (`sairngrounds.html:3543-3563`) with:

```js
function callAI(msg){
  grdAiBusy=true;
  var props=ld('grd_properties',[]);
  var ctx='You are the AI grounds operations assistant for SAIRNgrounds, used by a golf course / HOA / commercial grounds operator managing '+props.length+' properties. Be concise, practical, and turf/landscaping-industry-specific. No fluff. Never provide your own estimate, guess, or general-knowledge substitute for any fact a tool would have provided -- if a tool errors, is denied, or a question calls for data you have not actually retrieved via a tool this turn, say so plainly and stop.';
  var sharedCtx=buildGrdSharedCompanyContext();
  if(sharedCtx)ctx+='\n\n'+sharedCtx;
  recordGrdSharedTopics(msg);
  aiHist.push({role:'user',content:msg});
  var toolDefs=Object.keys(GRD_TOOLS).map(function(k){return GRD_TOOLS[k].definition;});
  // Reference this call's OWN placeholder node directly (not "the last .ama in
  // the DOM") -- if a second question is sent before this one's fetch resolves,
  // two Thinking placeholders coexist, and "remove the last one" removes
  // whichever request finishes first's own bubble regardless of which call it
  // belongs to, permanently orphaning the other and misattributing the answer.
  var thinkingEl=addMsg('Thinking...','a');
  function finish(replyText){
    grdAiBusy=false;
    if(thinkingEl&&thinkingEl.parentNode)thinkingEl.remove();
    aiHist.push({role:'assistant',content:replyText});
    addMsg(replyText,'a');
  }
  fetch(PROXY,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({model:'claude-sonnet-4-6',max_tokens:1000,app_id:APP_ID,is_demo:true,system:ctx,messages:aiHist.slice(-10),tools:toolDefs})})
  .then(function(r){return r.json();}).then(function(d){
    var blocks=(d&&d.content)||[];
    var toolUse=blocks.filter(function(b){return b.type==='tool_use';})[0];
    if(!toolUse){
      var rep=(blocks[0]&&blocks[0].text)||'No response.';
      finish(rep);
      return;
    }
    var outcome=grdExecuteTool(toolUse.name,grdCurrentRole(),toolUse.input);
    // Belt-and-suspenders, same pattern proven in SAIRNbiz/SAIRNlaw/
    // SAIRNvet/SAIRNscape: reinforce the anti-fabrication instruction
    // right next to the trigger, in the same turn as the denial/error.
    var toolResultContent=outcome.ok?JSON.stringify(outcome.result):('Error: '+outcome.error+' Do not estimate or substitute your own figures for this -- state the restriction/error plainly and stop.');
    // Claude requires the assistant turn that requested the tool to be
    // present in history before the tool_result turn that answers it.
    aiHist.push({role:'assistant',content:blocks});
    aiHist.push({role:'user',content:[{type:'tool_result',tool_use_id:toolUse.id,content:toolResultContent}]});
    fetch(PROXY,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({model:'claude-sonnet-4-6',max_tokens:1000,app_id:APP_ID,is_demo:true,system:ctx,messages:aiHist.slice(-10)})})
    .then(function(r2){return r2.json();}).then(function(d2){
      var rep2=(d2.content&&d2.content[0]&&d2.content[0].text)||'No response.';
      finish(rep2);
    }).catch(function(){
      finish('Could not reach Claude for the final answer. Connection error.');
    });
  }).catch(function(){
    grdAiBusy=false;
    if(thinkingEl&&thinkingEl.parentNode)thinkingEl.remove();
    addMsg('Connection error.','a');
  });
}
```

Note: the second `fetch` call omits `tools` entirely (single round-trip only, matching every other rollout's contract — the follow-up call never expects another `tool_use`).

- [ ] **Step 2: Syntax-check the modified script block**

Run: `python tools/checkblocks.py sairngrounds.html`
Expected: same `TOTAL_BLOCKS` as Task 1's result, `FAILED_BLOCKS:0`.

Run: `python tools/div_balance_check.py sairngrounds.html`
Expected: `RESULT:PASS`.

- [ ] **Step 3: Live interaction test — no-tool path unaffected**

Open the app (locally or via the deployed pre-push injection technique used on prior rollouts), log in, ask the AI assistant a question unrelated to any tool ("what's a good aerification schedule for cool-season turf" or similar). Confirm: exactly one "Thinking..." bubble appears and is replaced by one real answer, no console errors.

- [ ] **Step 4: Commit**

```bash
git add sairngrounds.html
git commit -m "feat: SAIRNgrounds -- callAI() tool-use round-trip + grdAiBusy guard

Sends GRD_TOOLS' definitions, executes a requested tool via
grdExecuteTool() (role-gated, error-safe), sends the result back for a
final grounded answer. Fixes the real pre-existing concurrency gap:
aiHist (shared, multi-turn) had zero guard before this change --
grdAiBusy now blocks a second send outright while one is in flight,
same shape as SAIRNscape's/SAIRNlaw's fix. sendAI() rejects a busy
second send with a toast before it touches aiHist at all."
```

---

### Task 3: End-to-end verification, push, live-verify

**Files:** none modified — verification only.

- [ ] **Step 1: Full local re-check of the changed file**

```bash
python tools/checkblocks.py sairngrounds.html
python tools/div_balance_check.py sairngrounds.html
```

Expected: both checks show 0 failures / PASS.

- [ ] **Step 2: Guardian v2 pass**

Run the full `sairn-guardian-v2` check (Check 0 + numbered checks) against `sairngrounds.html` before push, per the project's standing Push Protocol.

- [ ] **Step 3: Real interaction test — property roster question**

With the app running against real seeded data, ask the AI assistant a property question ("what properties do we manage," "what type is Fairview Golf Club," "what's the status of Lakeshore Corporate Park"). Confirm the answer contains real names/types/contact info from `grd_properties` — not a generic non-answer.

- [ ] **Step 4: Concurrency test (the load-bearing one for this rollout)**

Send two questions back-to-back before the first resolves. Confirm: the second send is rejected with the "Please wait for the current response first" toast before it touches `aiHist`, exactly one message-bubble pair results from the first question, and inspecting `aiHist` afterward shows a clean, correctly-ordered sequence (no interleaved or duplicated turns) for that one exchange. This is the direct regression test for the concurrency bug this rollout fixes — do not skip it or treat it as optional.

- [ ] **Step 5: Role-gate mechanism check (not exercised through the UI)**

`get_properties` isn't sensitive, so nothing in the UI naturally exercises the gate for it. Confirm the mechanism itself directly: open the browser console on the live app and run `grdExecuteTool('get_properties', 'owner', {})` (should succeed) and, temporarily, `GRD_TOOLS.get_properties.sensitive = true; grdExecuteTool('get_properties', 'superintendent', {})` and `grdExecuteTool('get_properties', 'manager', {})` (both should return `{ok:false, error:'This data is restricted to the owner role.'}`); then `grdExecuteTool('get_properties', 'owner', {})` again (should still succeed). Reload the page afterward (the temporary mutation is not persisted).

- [ ] **Step 6: `sanitizeTools()` regression check for this app_id specifically**

```bash
curl -s -X POST https://sairn.vercel.app/api/claude \
  -H 'Content-Type: application/json' \
  -d '{"app_id":"sairngrounds","is_demo":true,"max_tokens":50,"system":"test","messages":[{"role":"user","content":"say hi"}],"tools":[{"name":"get_properties","description":"x","input_schema":{"type":"object","properties":{}}}]}'
```

Expected: HTTP 200 with a real Anthropic response shape (`content` array present), not a 400.

- [ ] **Step 7: Push**

```bash
git push origin main
```

- [ ] **Step 8: Live-verify**

```bash
curl -s https://sairn.vercel.app/sairngrounds | grep -c "grdExecuteTool"
```

Expected: non-zero. Then repeat Steps 3-5's tests against the **live** URL, not just a local/injected copy — per the project's standing rule that a clean push is not proof the live app reflects the change.

- [ ] **Step 9: Update the spec's status line**

Edit `docs/superpowers/specs/2026-08-10-sairngrounds-ai-tool-calling-design.md`'s `**Status:**` line to note the foundation, `get_properties`, and the concurrency fix are implemented and live-verified, with the date. Commit this doc-only change separately.
