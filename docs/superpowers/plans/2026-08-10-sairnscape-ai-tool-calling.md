# SAIRNscape AI Tool-Calling Foundation + get_customers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give SAIRNscape's general AI chat (`scpCallAI()`, `sairnscape.html:2672`) real function-calling access to the company's own customer roster, via one proof tool (`get_customers`), porting the mechanism already proven live in SAIRNbiz/SAIRNlaw/SAIRNvet — and, as a required part of the same rollout, fixing a real pre-existing concurrency bug: `scpAiHist` is a shared, persistent, multi-turn history array with zero guard of any kind, the same architecture shape that caused SAIRNlaw's live-observed corruption bug before `lawAiBusy` was added there.

**Architecture:** `SCP_TOOLS`/`scpRegisterTool`/`scpExecuteTool` — same registry shape as SAIRNbiz's `SB_TOOLS`/SAIRNlaw's `LAW_TOOLS`, **including** the `sensitive`/role parameter (unlike SAIRNvet) since SAIRNscape has real, server-verified roles already in active use elsewhere in this file. `scpAiBusy` (new) guards `scpSendAI()`/`scpCallAI()` exactly like `lawAiBusy` guards SAIRNlaw's `sendAI()`. `scpCallAI()` is rewired for a tool-use round-trip, kept in its existing `.then()`-chain style (not converted to `async`/`await` — no orthogonal style change).

**Tech Stack:** Vanilla JS (`sairnscape.html`, no framework). Verified the same way `get_matters`/`get_deadlines`/`get_patients` were: `tools/checkblocks.py` / `tools/div_balance_check.py` on the file, a temporary `node:assert` scratch harness for pure logic, plus a real live-interaction test against the deployed app.

## Global Constraints

- Read-only tool only — `get_customers` may not create, modify, or delete any record. (Spec §2)
- No new persistence — reads live from `scpLd('scp_customers', [])`. (Spec §2)
- `get_customers` returns `{name, service, recurring, phone, email, address}` only — `id` and `notes` excluded. (Spec §4)
- `get_customers` is non-sensitive (`sensitive:false`), but the dispatcher itself supports a `sensitive`/role parameter (unlike SAIRNvet's dispatcher, which omits it). (Spec §1, §4)
- `scpExecuteTool`'s role check is `sensitive && role !== 'owner'` — the exact same single-role check as `sbExecuteTool`/`lawExecuteTool`. This is **not** SAIRNscape's own separate `SCP_QC_AUTHORITY_ROLES` multi-role concept (`sairnscape.html:2228`) — that gate belongs to a different feature (QC sign-off) and is not inherited here. (Spec §3)
- `role` for `scpExecuteTool` calls comes from the existing `scpCurrentRole()` helper (`sairnscape.html:2218`), read on-demand — not cached into a new global variable. (Spec §3)
- The pre-existing concurrency bug (unguarded shared `scpAiHist`) must be fixed as part of this rollout, not deferred — `scpAiBusy`, same shape as `lawAiBusy`: `scpSendAI()` rejects a second send with a toast while busy; `scpCallAI()` sets it `true` at start, clears it on every exit path. (Spec §0, §1, §3)
- `scpUploadProgressPhoto()` (`sairnscape.html:2292`) and `api/claude.js` are not touched. (Spec §2)
- `python tools/checkblocks.py sairnscape.html` and `python tools/div_balance_check.py sairnscape.html` must stay clean (0 failed / PASS) after every change.
- Before push: full Guardian v2 check on `sairnscape.html`. After push: live-verify against `sairn.vercel.app/sairnscape` directly, not assumed from a clean push (project Push Protocol).

---

### Task 1: `sairnscape.html` — tool registry, dispatcher, and the `get_customers` tool

**Files:**
- Modify: `sairnscape.html` (insert immediately after the globals line `var scpCid=null,scpJid=null,scpQid=null,scpSid=null,scpIid=null,scpAiHist=[];` at `sairnscape.html:1650`, before `function scpLd(k,d){...}` at `sairnscape.html:1654`)

**Interfaces:**
- Consumes: `scpLd(k, d)` (`sairnscape.html:1654`, existing localStorage getter).
- Produces: `SCP_TOOLS` (object, tool name → `{definition, sensitive, run}`), `scpExecuteTool(name, role, input)` → `{ok: true, result: any} | {ok: false, error: string}`, `scpAiBusy` (boolean, initialized `false`) — all used by Task 2.

- [ ] **Step 1: Write the implementation**

Insert immediately after `var scpCid=null,scpJid=null,scpQid=null,scpSid=null,scpIid=null,scpAiHist=[];` (`sairnscape.html:1650`):

```js
// AI tool-calling dispatcher (2026-08-10) -- ports the mechanism proven
// live in SAIRNbiz/SAIRNlaw/SAIRNvet. Registry of read-only tools
// scpCallAI() may request via Claude's tool-use. Every tool is:
//   - read-only (never creates/modifies/deletes anything)
//   - wrapped so a thrown error or unexpected data shape becomes an honest
//     {ok:false} result, never a crash or a silently wrong answer
//   - checked against the CALLING role before running, if marked sensitive
//     (same single-role check as SAIRNbiz's sbExecuteTool/SAIRNlaw's
//     lawExecuteTool -- NOT this file's own separate
//     SCP_QC_AUTHORITY_ROLES multi-role concept, a different feature)
// See docs/superpowers/specs/2026-08-10-sairnscape-ai-tool-calling-design.md
var SCP_TOOLS = {};

function scpRegisterTool(name, description, inputSchema, sensitive, run) {
  SCP_TOOLS[name] = {
    definition: { name: name, description: description, input_schema: inputSchema },
    sensitive: !!sensitive,
    run: run
  };
}

function scpExecuteTool(name, role, input) {
  var tool = SCP_TOOLS[name];
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
// discovered live: scpAiHist is a shared, persistent, multi-turn history
// array (same shape as SAIRNlaw's aiHist) that had ZERO guard before this
// change. Two concurrent scpCallAI() calls would both read/write the same
// array, corrupting each other's context -- the exact bug class already
// found and fixed live in SAIRNlaw. Same fix shape as lawAiBusy: block a
// second send outright rather than trying to make concurrent shared-
// history calls safe.
var scpAiBusy = false;

scpRegisterTool(
  'get_customers',
  'Look up the company\'s current customer roster: name, service, whether it\'s recurring, phone, email, and address. Does NOT include job history, schedule, invoices, quotes, or customer notes -- those are not available to this tool.',
  { type: 'object', properties: {}, required: [] },
  false,
  function (input) {
    // input intentionally unused -- this tool takes no real arguments, but
    // accepts one for interface consistency with scpExecuteTool(name, role,
    // input), matching get_matters'/get_patients' convention.
    return scpLd('scp_customers', []).map(function (c) {
      return {
        name: c.name,
        service: c.service,
        recurring: c.recurring,
        phone: c.phone,
        email: c.email,
        address: c.address
      };
    });
  }
);
```

- [ ] **Step 2: Syntax-check the modified script block**

Run: `python tools/checkblocks.py sairnscape.html`
Expected: same `TOTAL_BLOCKS` as the pre-change baseline (run it once before this edit if you don't already know the number), `FAILED_BLOCKS:0`.

Run: `python tools/div_balance_check.py sairnscape.html`
Expected: `RESULT:PASS`.

- [ ] **Step 3: Behavioral verification with a temporary Node harness**

Both the dispatcher and the tool's `run()` have no DOM dependency. Create a scratch file (not committed — delete after this step):

```js
// scratch verification, delete after running
var assert = require('assert');

var SCP_TOOLS = {};
function scpRegisterTool(name, description, inputSchema, sensitive, run) {
  SCP_TOOLS[name] = { definition: { name: name, description: description, input_schema: inputSchema }, sensitive: !!sensitive, run: run };
}
function scpExecuteTool(name, role, input) {
  var tool = SCP_TOOLS[name];
  if (!tool) return { ok: false, error: 'No tool named "' + name + '" exists.' };
  if (tool.sensitive && role !== 'owner') return { ok: false, error: 'This data is restricted to the owner role.' };
  try { return { ok: true, result: tool.run(input || {}) }; } catch (e) { return { ok: false, error: 'Could not retrieve that data right now.' }; }
}

// -- dispatcher + role-gate checks --
scpRegisterTool('ping', 'test tool', {type:'object'}, false, function () { return 'pong'; });
scpRegisterTool('secret', 'test sensitive tool', {type:'object'}, true, function () { return 'classified'; });
scpRegisterTool('broken', 'test throwing tool', {type:'object'}, false, function () { throw new Error('boom'); });

assert.deepStrictEqual(scpExecuteTool('ping', 'office', {}), { ok: true, result: 'pong' });
assert.deepStrictEqual(scpExecuteTool('nonexistent', 'owner', {}), { ok: false, error: 'No tool named "nonexistent" exists.' });
assert.deepStrictEqual(scpExecuteTool('secret', 'crew_lead', {}), { ok: false, error: 'This data is restricted to the owner role.' });
assert.deepStrictEqual(scpExecuteTool('secret', 'office', {}), { ok: false, error: 'This data is restricted to the owner role.' });
assert.deepStrictEqual(scpExecuteTool('secret', 'owner', {}), { ok: true, result: 'classified' });
assert.strictEqual(scpExecuteTool('broken', 'owner', {}).ok, false);
console.log('scpExecuteTool: all 6 checks passed');

// -- get_customers tool check, stubbing scpLd() --
var SCP_CUSTOMERS = [
  { id: 'C-001', name: 'Diane Ferraro', service: 'Weekly mowing + edge', recurring: true, phone: '(440) 555-0140', email: 'dferraro@example.com', address: '12 Birchwood Ln, Avon OH', notes: '' },
  { id: 'C-002', name: 'Marcus Webb', service: 'Seasonal cleanup', recurring: false, phone: '(440) 555-0141', email: 'mwebb@example.com', address: '88 Elmwood Ave, Avon Lake OH', notes: 'Prefers Friday visits' }
];
function scpLd(k, d) { return k === 'scp_customers' ? SCP_CUSTOMERS : d; }

scpRegisterTool('get_customers', 'x', { type: 'object' }, false, function (input) {
  return scpLd('scp_customers', []).map(function (c) {
    return { name: c.name, service: c.service, recurring: c.recurring, phone: c.phone, email: c.email, address: c.address };
  });
});

var out = SCP_TOOLS.get_customers.run({});
assert.strictEqual(out.length, 2);
assert.strictEqual(out[0].name, 'Diane Ferraro');
assert.strictEqual(out[1].recurring, false);
assert.strictEqual(out[0].id, undefined, 'id must never appear in get_customers output');
assert.strictEqual(out[1].notes, undefined, 'notes must never appear in get_customers output');
console.log('get_customers tool: all 4 checks passed');
```

Run: `node <scratch-file>.js`
Expected: `scpExecuteTool: all 6 checks passed` then `get_customers tool: all 4 checks passed`. Delete the scratch file afterward.

- [ ] **Step 4: Commit**

```bash
git add sairnscape.html
git commit -m "feat: SAIRNscape -- tool-calling dispatcher + get_customers proof tool

Ports the mechanism proven live in SAIRNbiz/SAIRNlaw/SAIRNvet, WITH the
sensitive/role-gate parameter (unlike SAIRNvet) since SAIRNscape has
real, server-verified roles already in active use elsewhere in this
file (SCP_QC_AUTHORITY_ROLES). SCP_TOOLS/scpRegisterTool/scpExecuteTool
plus one read-only tool, get_customers (name/service/recurring/phone/
email/address). id and notes deliberately excluded. Also adds scpAiBusy
(unused until Task 2) -- the concurrency guard scpCallAI()'s shared
scpAiHist array has never had. scpCallAI() doesn't call any of this yet
-- verified standalone via a Node harness."
```

---

### Task 2: `sairnscape.html` — `scpCallAI()` tool-use round-trip + `scpAiBusy` guard

**Files:**
- Modify: `sairnscape.html:2668-2690` (`scpSendAI()`, `scpCallAI()`)

**Interfaces:**
- Consumes: `scpExecuteTool(name, role, input)` (Task 1), `SCP_TOOLS` (Task 1, read via `Object.keys(SCP_TOOLS).map(k => SCP_TOOLS[k].definition)`), `scpAiBusy` (Task 1), `scpCurrentRole()` (`sairnscape.html:2218`, existing), `scpToast(m, d)` (`sairnscape.html:1658`, existing), `scpAddMsg(t, role)` (`sairnscape.html:2671`, existing, already returns its DOM node), `SCP_PROXY`, `SCP_APP_ID`, `scpAiHist`, `buildScpSharedCompanyContext()`/`recordScpSharedTopics(msg)` (`sairnscape.html:2704`/`2700`, existing, untouched).
- Produces: no new exports — `scpSendAI()`/`scpCallAI(msg)` keep their existing signatures and call sites (`scpAskAI(q)`, `sairnscape.html:2669`).

- [ ] **Step 1: Write the implementation**

Replace `scpSendAI()` (`sairnscape.html:2668`) with:

```js
function scpSendAI(){if(scpAiBusy){scpToast('Please wait for the current response first');return;}var inp=scp$('scp-ainp');var m=(inp.value||'').trim();if(!m)return;inp.value='';scpAddMsg(m,'u');scpCallAI(m);}
```

Replace `scpCallAI(msg)` (`sairnscape.html:2672-2690`) with:

```js
function scpCallAI(msg){
  scpAiBusy=true;
  var custs=scpLd('scp_customers',[]);
  var ctx='You are the AI business assistant for SAIRNscape, used by a residential/small-commercial landscaping company with '+custs.length+' active customers. Be concise, practical, and landscaping-industry-specific. No fluff. Never provide your own estimate, guess, or general-knowledge substitute for any fact a tool would have provided -- if a tool errors, is denied, or a question calls for data you have not actually retrieved via a tool this turn, say so plainly and stop.';
  var sharedCtx=buildScpSharedCompanyContext();
  if(sharedCtx)ctx+='\n\n'+sharedCtx;
  recordScpSharedTopics(msg);
  scpAiHist.push({role:'user',content:msg});
  var toolDefs=Object.keys(SCP_TOOLS).map(function(k){return SCP_TOOLS[k].definition;});
  // One placeholder spans the whole exchange, including the extra
  // tool-result round-trip -- same placeholder-by-reference pattern
  // already in this function, preserved unchanged (it already does the
  // right thing per its own original comment; only scpAiHist was
  // unguarded, not this placeholder).
  var thinkingEl=scpAddMsg('Thinking...','a');
  function finish(replyText){
    scpAiBusy=false;
    if(thinkingEl&&thinkingEl.parentNode)thinkingEl.remove();
    scpAiHist.push({role:'assistant',content:replyText});
    scpAddMsg(replyText,'a');
  }
  fetch(SCP_PROXY,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({model:'claude-sonnet-4-6',max_tokens:1000,app_id:SCP_APP_ID,is_demo:true,system:ctx,messages:scpAiHist.slice(-10),tools:toolDefs})})
  .then(function(r){return r.json();}).then(function(d){
    var blocks=(d&&d.content)||[];
    var toolUse=blocks.filter(function(b){return b.type==='tool_use';})[0];
    if(!toolUse){
      var rep=(blocks[0]&&blocks[0].text)||'No response.';
      finish(rep);
      return;
    }
    var outcome=scpExecuteTool(toolUse.name,scpCurrentRole(),toolUse.input);
    // Belt-and-suspenders, same pattern proven in SAIRNbiz/SAIRNlaw/
    // SAIRNvet: reinforce the anti-fabrication instruction right next to
    // the trigger, in the same turn as the denial/error itself.
    var toolResultContent=outcome.ok?JSON.stringify(outcome.result):('Error: '+outcome.error+' Do not estimate or substitute your own figures for this -- state the restriction/error plainly and stop.');
    // Claude requires the assistant turn that requested the tool to be
    // present in history before the tool_result turn that answers it.
    scpAiHist.push({role:'assistant',content:blocks});
    scpAiHist.push({role:'user',content:[{type:'tool_result',tool_use_id:toolUse.id,content:toolResultContent}]});
    fetch(SCP_PROXY,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({model:'claude-sonnet-4-6',max_tokens:1000,app_id:SCP_APP_ID,is_demo:true,system:ctx,messages:scpAiHist.slice(-10)})})
    .then(function(r2){return r2.json();}).then(function(d2){
      var rep2=(d2.content&&d2.content[0]&&d2.content[0].text)||'No response.';
      finish(rep2);
    }).catch(function(){
      finish('Could not reach Claude for the final answer. Connection error.');
    });
  }).catch(function(){
    scpAiBusy=false;
    if(thinkingEl&&thinkingEl.parentNode)thinkingEl.remove();
    scpAddMsg('Connection error.','a');
  });
}
```

Note: the second `fetch` call omits `tools` entirely (single round-trip only, matching every other rollout's contract — the follow-up call never expects another `tool_use`).

- [ ] **Step 2: Syntax-check the modified script block**

Run: `python tools/checkblocks.py sairnscape.html`
Expected: same `TOTAL_BLOCKS` as Task 1's result, `FAILED_BLOCKS:0`.

Run: `python tools/div_balance_check.py sairnscape.html`
Expected: `RESULT:PASS`.

- [ ] **Step 3: Live interaction test — no-tool path unaffected**

Open the app (locally or via the deployed pre-push injection technique used on prior rollouts), log in, ask the AI assistant a question unrelated to any tool ("what's a fair markup on mulch" or similar). Confirm: exactly one "Thinking..." bubble appears and is replaced by one real answer, no console errors.

- [ ] **Step 4: Commit**

```bash
git add sairnscape.html
git commit -m "feat: SAIRNscape -- scpCallAI() tool-use round-trip + scpAiBusy guard

Sends SCP_TOOLS' definitions, executes a requested tool via
scpExecuteTool() (role-gated, error-safe), sends the result back for a
final grounded answer. Fixes the real pre-existing concurrency gap:
scpAiHist (shared, multi-turn) had zero guard before this change --
scpAiBusy now blocks a second send outright while one is in flight,
same shape as SAIRNlaw's lawAiBusy fix. scpSendAI() rejects a busy
second send with a toast before it touches scpAiHist at all."
```

---

### Task 3: End-to-end verification, push, live-verify

**Files:** none modified — verification only.

- [ ] **Step 1: Full local re-check of the changed file**

```bash
python tools/checkblocks.py sairnscape.html
python tools/div_balance_check.py sairnscape.html
```

Expected: both checks show 0 failures / PASS.

- [ ] **Step 2: Guardian v2 pass**

Run the full `sairn-guardian-v2` check (Check 0 + numbered checks) against `sairnscape.html` before push, per the project's standing Push Protocol.

- [ ] **Step 3: Real interaction test — customer roster question**

With the app running against real seeded data, ask the AI assistant a customer question ("what customers do we have," "what service does Diane Ferraro have," "does Marcus Webb have a recurring service"). Confirm the answer contains real names/services/contact info from `scp_customers` — not a generic non-answer.

- [ ] **Step 4: Concurrency test (the load-bearing one for this rollout)**

Send two questions back-to-back before the first resolves. Confirm: the second send is rejected with the "Please wait for the current response first" toast before it touches `scpAiHist`, exactly one message-bubble pair results from the first question, and inspecting `scpAiHist` afterward shows a clean, correctly-ordered sequence (no interleaved or duplicated turns) for that one exchange. This is the direct regression test for the concurrency bug this rollout fixes — do not skip it or treat it as optional.

- [ ] **Step 5: Role-gate mechanism check (not exercised through the UI)**

`get_customers` isn't sensitive, so nothing in the UI naturally exercises the gate for it. Confirm the mechanism itself directly: open the browser console on the live app and run `scpExecuteTool('get_customers', 'owner', {})` (should succeed) and, temporarily, `SCP_TOOLS.get_customers.sensitive = true; scpExecuteTool('get_customers', 'crew_lead', {})` and `scpExecuteTool('get_customers', 'office', {})` (both should return `{ok:false, error:'This data is restricted to the owner role.'}`); then `scpExecuteTool('get_customers', 'owner', {})` again (should still succeed). Reload the page afterward (the temporary mutation is not persisted).

- [ ] **Step 6: `sanitizeTools()` regression check for this app_id specifically**

```bash
curl -s -X POST https://sairn.vercel.app/api/claude \
  -H 'Content-Type: application/json' \
  -d '{"app_id":"sairnscape","is_demo":true,"max_tokens":50,"system":"test","messages":[{"role":"user","content":"say hi"}],"tools":[{"name":"get_customers","description":"x","input_schema":{"type":"object","properties":{}}}]}'
```

Expected: HTTP 200 with a real Anthropic response shape (`content` array present), not a 400.

- [ ] **Step 7: Push**

```bash
git push origin main
```

- [ ] **Step 8: Live-verify**

```bash
curl -s https://sairn.vercel.app/sairnscape | grep -c "scpExecuteTool"
```

Expected: non-zero. Then repeat Steps 3-5's tests against the **live** URL, not just a local/injected copy — per the project's standing rule that a clean push is not proof the live app reflects the change.

- [ ] **Step 9: Update the spec's status line**

Edit `docs/superpowers/specs/2026-08-10-sairnscape-ai-tool-calling-design.md`'s `**Status:**` line to note the foundation, `get_customers`, and the concurrency fix are implemented and live-verified, with the date. Commit this doc-only change separately.
