# StoneDesk AI Tool-Calling Foundation + get_job_profitability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give StoneDesk's real, live chat widget (`sdAISend()`/`sendMsg()`, `stonedesk.html:3189-3221`) real function-calling access to real job-profitability data, via one proof tool (`get_job_profitability`), porting the mechanism already proven live in SAIRNbiz/SAIRNlaw/SAIRNvet/SAIRNscape/SAIRNgrounds — and, as a required part of the same rollout, fixing a real concurrency gap this chat has always had (`history` is shared, persistent, and completely unguarded).

**Architecture:** `SD_TOOLS`/`sdRegisterTool`/`sdExecuteTool` — same registry shape as every prior rollout, including the `sensitive`/role parameter (real, server-verified auth exists via `api/sd-auth.js`). A new, minimal `sdCurrentRole()` helper reads the real session role directly from `sessionStorage` (`sd_session_role`), since no existing global accessor exposes it. `sdAiBusy` guards the chat's two public entry points (`sdAISend()`/`sdAIQuick()`). `sendMsg()` gets its first-ever system prompt and a tool-use round-trip, kept inside its existing IIFE and `.then()`-chain style — no structural or stylistic changes beyond what's needed.

**Tech Stack:** Vanilla JS (`stonedesk.html`, no framework). **This file is ~2.0MB across 128 real `<script>` blocks** (confirmed via `tools/checkblocks.py`'s real HTML-parser-based extraction — never a `grep -c '<script'` count, per project `CLAUDE.md`). Verified the same way every prior rollout was, plus an extra structural guard specific to this file's size: every syntax-check step re-confirms `TOTAL_BLOCKS` stays exactly 128 (not just `FAILED_BLOCKS:0`) — an unexpected block-count change (e.g. an accidentally-closed `<script>` tag) is itself a signal something broke, even if no block individually fails `node --check`.

## Global Constraints

- Read-only tool only — `get_job_profitability` may not create, modify, or delete any record. (Spec §2)
- No new persistence — reads the existing in-memory `sdFinJobs` global directly (already loaded from `localStorage`'s `sd_fin_jobs` key at script-parse time, kept in sync by `finSaveJob()`/`finDeleteJob()`). (Spec §2, §4)
- `get_job_profitability` returns `{customer, quote, material, sqft, cogs, profit, margin, date}` only. (Spec §4)
- `get_job_profitability` is non-sensitive (`sensitive:false`), but the dispatcher itself supports a `sensitive`/role parameter. (Spec §1, §4)
- `sdExecuteTool`'s role check is `sensitive && role !== 'owner'` — the exact same single-role check as every prior rollout. This is **not** the same as this file's own separate `currentRole === 'owner' || currentRole === 'admin'` two-role check used elsewhere (`stonedesk.html:29714`) for a different feature — not inherited here. (Spec §3)
- `role` comes from a new `sdCurrentRole()` helper reading `sessionStorage.getItem('sd_session_role')` directly — not the auth module's internal `currentRole` variable, which isn't exposed outside its own scope and must not be touched. (Spec §0, §3)
- The pre-existing concurrency gap (unguarded shared `history`) must be fixed as part of this rollout, not deferred — `sdAiBusy`: `sdAISend()`/`sdAIQuick()` reject a second call with `notify()` while busy; `sendMsg()` sets it `true` at start, clears it on every exit path. (Spec §0, §1, §3)
- **The streaming chat override (`installStreamingHook()`) is completely untouched by this plan** — different, harder, explicitly out-of-scope integration. (Spec §2)
- **None of StoneDesk's other ~14 AI features are touched** (`scanDoc`, `sdRunEmailScan`, `getAIDrawingAdvice`, `fqAnalyze`/`fqGenQuote`, `finAIJobAdvice`, `finAskCFO`, etc.) — `finAIJobAdvice`/`finAskCFO` call `sdAIQuick()`, which this plan modifies, so they must be spot-checked for regressions, not assumed safe. (Spec §2, §5)
- `api/sd-auth.js` and `api/claude.js` are not touched. (Spec §2)
- `python tools/checkblocks.py stonedesk.html` must report `TOTAL_BLOCKS:128` and `FAILED_BLOCKS:0` after every change (both numbers checked, not just the failure count).
- `python tools/div_balance_check.py stonedesk.html` must report `RESULT:PASS` after every change.
- Before push: full Guardian v2 check on `stonedesk.html`. After push: live-verify against `sairn.vercel.app/stonedesk` directly — both steps of the Push Protocol, neither optional, and especially load-bearing on this specific file per the project's own standing fragility warnings.

---

### Task 1: `stonedesk.html` — tool registry, dispatcher, `sdCurrentRole()`, and the `get_job_profitability` tool

**Files:**
- Modify: `stonedesk.html` (insert immediately after `var history=[];` at `stonedesk.html:3173`, before `var counts={today:0,total:0};`, inside the existing chat-widget IIFE)

**Interfaces:**
- Consumes: nothing from earlier tasks (this is the first task); reads the existing global `sdFinJobs` array (`stonedesk.html:21644`) directly.
- Produces: `SD_TOOLS` (object, tool name → `{definition, sensitive, run}`), `sdExecuteTool(name, role, input)` → `{ok: true, result: any} | {ok: false, error: string}`, `sdCurrentRole()` → real session role string (or `''`), `sdAiBusy` (boolean, initialized `false`) — all used by Task 2. All of these live inside the chat widget's IIFE (module-private, not `window`-exposed, matching how `history`/`counts` are already scoped there).

- [ ] **Step 1: Write the implementation**

Insert immediately after `var history=[];` (`stonedesk.html:3173`), before `var counts={today:0,total:0};`:

```js
// AI tool-calling dispatcher (2026-08-10) -- ports the mechanism proven
// live in SAIRNbiz/SAIRNlaw/SAIRNvet/SAIRNscape/SAIRNgrounds. Registry
// of read-only tools sendMsg() may request via Claude's tool-use. Kept
// inside this IIFE (module-private, same as history/counts) since
// nothing outside this widget needs it. Every tool is:
//   - read-only (never creates/modifies/deletes anything)
//   - wrapped so a thrown error or unexpected data shape becomes an honest
//     {ok:false} result, never a crash or a silently wrong answer
//   - checked against the CALLING role before running, if marked sensitive
//     (same single-role check as every prior rollout's dispatcher -- NOT
//     this file's own separate `currentRole === 'owner' || currentRole
//     === 'admin'` two-role check used elsewhere for a different feature)
// See docs/superpowers/specs/2026-08-10-stonedesk-ai-tool-calling-design.md
var SD_TOOLS = {};

function sdRegisterTool(name, description, inputSchema, sensitive, run) {
  SD_TOOLS[name] = {
    definition: { name: name, description: description, input_schema: inputSchema },
    sensitive: !!sensitive,
    run: run
  };
}

// The real, server-verified session role. StoneDesk's auth module
// (api/sd-auth.js via a real per-employee login) stores this in
// sessionStorage as 'sd_session_role' (SD_ROLE_KEY, stonedesk.html:29284)
// -- the module's own internal `currentRole` variable is not exposed
// outside its own scope, so this reads the session value directly rather
// than reaching into or modifying that existing code.
function sdCurrentRole() {
  try { return sessionStorage.getItem('sd_session_role') || ''; } catch (e) { return ''; }
}

function sdExecuteTool(name, role, input) {
  var tool = SD_TOOLS[name];
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

// Concurrency guard (2026-08-10) -- history (declared just above) is
// shared, persistent, multi-turn, and had ZERO guard before this change
// -- the same latent bug class already found and fixed live in SAIRNlaw/
// SAIRNscape/SAIRNgrounds. Two concurrent sendMsg() calls would both
// read/write the same array, corrupting each other's context.
var sdAiBusy = false;

sdRegisterTool(
  'get_job_profitability',
  'Look up real per-job profitability records from the Job Financials tracker: customer, quoted price, material, square footage, cost of goods sold (COGS), profit, gross margin percent, and date. Does NOT include production/scheduling job records (a separate data domain), the Quote Builder's own quote records, or any other job-adjacent data.',
  { type: 'object', properties: {}, required: [] },
  false,
  function (input) {
    // input intentionally unused -- this tool takes no real arguments, but
    // accepts one for interface consistency with sdExecuteTool(name, role,
    // input), matching every prior tool's convention. Reads the existing
    // sdFinJobs global directly (stonedesk.html:21644) -- no new lookup
    // logic, no localStorage re-read.
    return sdFinJobs.map(function (j) {
      return {
        customer: j.customer,
        quote: j.quote,
        material: j.material,
        sqft: j.sqft,
        cogs: j.cogs,
        profit: j.profit,
        margin: j.margin,
        date: j.date
      };
    });
  }
);
```

- [ ] **Step 2: Syntax-check the modified script block**

Run: `python tools/checkblocks.py stonedesk.html`
Expected: `TOTAL_BLOCKS:128` (unchanged from baseline — this edit is inside an existing script block, it does not add or remove one), `FAILED_BLOCKS:0`.

Run: `python tools/div_balance_check.py stonedesk.html`
Expected: `RESULT:PASS`.

- [ ] **Step 3: Behavioral verification with a temporary Node harness**

Both the dispatcher and the tool's `run()` have no DOM dependency. Create a scratch file (not committed — delete after this step):

```js
// scratch verification, delete after running
var assert = require('assert');

var SD_TOOLS = {};
function sdRegisterTool(name, description, inputSchema, sensitive, run) {
  SD_TOOLS[name] = { definition: { name: name, description: description, input_schema: inputSchema }, sensitive: !!sensitive, run: run };
}
function sdExecuteTool(name, role, input) {
  var tool = SD_TOOLS[name];
  if (!tool) return { ok: false, error: 'No tool named "' + name + '" exists.' };
  if (tool.sensitive && role !== 'owner') return { ok: false, error: 'This data is restricted to the owner role.' };
  try { return { ok: true, result: tool.run(input || {}) }; } catch (e) { return { ok: false, error: 'Could not retrieve that data right now.' }; }
}

// -- dispatcher + role-gate checks --
sdRegisterTool('ping', 'test tool', {type:'object'}, false, function () { return 'pong'; });
sdRegisterTool('secret', 'test sensitive tool', {type:'object'}, true, function () { return 'classified'; });
sdRegisterTool('broken', 'test throwing tool', {type:'object'}, false, function () { throw new Error('boom'); });

assert.deepStrictEqual(sdExecuteTool('ping', 'employee', {}), { ok: true, result: 'pong' });
assert.deepStrictEqual(sdExecuteTool('nonexistent', 'owner', {}), { ok: false, error: 'No tool named "nonexistent" exists.' });
assert.deepStrictEqual(sdExecuteTool('secret', 'admin', {}), { ok: false, error: 'This data is restricted to the owner role.' });
assert.deepStrictEqual(sdExecuteTool('secret', 'employee', {}), { ok: false, error: 'This data is restricted to the owner role.' });
assert.deepStrictEqual(sdExecuteTool('secret', 'owner', {}), { ok: true, result: 'classified' });
assert.strictEqual(sdExecuteTool('broken', 'owner', {}).ok, false);
console.log('sdExecuteTool: all 6 checks passed');

// -- get_job_profitability tool check, stubbing sdFinJobs --
var sdFinJobs = [
  { id: 'FJ1', customer: 'Diane Ferraro', quote: 4200, sqft: 42, material: 'quartz', slab: 900, hours: 12, rate: 35, consumables: 80, install: 400, cogs: 1800, profit: 2400, margin: 57, date: '2026-08-01T00:00:00.000Z' },
  { id: 'FJ2', customer: 'Marcus Webb', quote: 3100, sqft: 30, material: 'granite', slab: 700, hours: 10, rate: 35, consumables: 60, install: 350, cogs: 1460, profit: 1640, margin: 53, date: '2026-08-05T00:00:00.000Z' }
];

sdRegisterTool('get_job_profitability', 'x', { type: 'object' }, false, function (input) {
  return sdFinJobs.map(function (j) {
    return { customer: j.customer, quote: j.quote, material: j.material, sqft: j.sqft, cogs: j.cogs, profit: j.profit, margin: j.margin, date: j.date };
  });
});

var out = SD_TOOLS.get_job_profitability.run({});
assert.strictEqual(out.length, 2);
assert.strictEqual(out[0].customer, 'Diane Ferraro');
assert.strictEqual(out[0].quote, 4200, 'quote must be included per spec §4 field list');
assert.strictEqual(out[1].margin, 53);
assert.strictEqual(out[0].id, undefined, 'id must never appear in get_job_profitability output');
assert.strictEqual(out[0].slab, undefined, 'internal cost-breakdown fields (slab/hours/rate/consumables/install) must not appear -- only the spec §4 field list');
console.log('get_job_profitability tool: all 5 checks passed');
```

Run: `node <scratch-file>.js`
Expected: `sdExecuteTool: all 6 checks passed` then `get_job_profitability tool: all 5 checks passed`. Delete the scratch file afterward.

- [ ] **Step 4: Commit**

```bash
git add stonedesk.html
git commit -m "feat: StoneDesk -- tool-calling dispatcher + get_job_profitability

Ports the mechanism proven live in SAIRNbiz/SAIRNlaw/SAIRNvet/SAIRNscape/
SAIRNgrounds, WITH the sensitive/role-gate parameter -- real server-
verified auth exists (api/sd-auth.js). Adds sdCurrentRole(), a new
minimal helper reading the real session role directly from
sessionStorage ('sd_session_role') rather than touching the auth
module's internal currentRole variable, which isn't exposed outside its
own scope. SD_TOOLS/sdRegisterTool/sdExecuteTool plus one read-only
tool, get_job_profitability (customer/quote/material/sqft/cogs/profit/margin/
date from the real sdFinJobs global). Also adds sdAiBusy (unused until
next commit) -- the concurrency guard this chat's shared history array
has never had. sendMsg() doesn't call any of this yet -- verified
standalone via a Node harness. TOTAL_BLOCKS stays 128, FAILED_BLOCKS 0."
```

---

### Task 2: `stonedesk.html` — `sendMsg()` tool-use round-trip + `sdAiBusy` guard

**Files:**
- Modify: `stonedesk.html:3189-3221` (`sendMsg()`, `sdAISend`, `sdAIQuick`)

**Interfaces:**
- Consumes: `sdExecuteTool(name, role, input)` (Task 1), `SD_TOOLS` (Task 1, read via `Object.keys(SD_TOOLS).map(k => SD_TOOLS[k].definition)`), `sdAiBusy` (Task 1), `sdCurrentRole()` (Task 1), `notify(msg, type)` (`stonedesk.html:1876`, existing global, confirmed in scope), `appendMsg(role, text)` (`stonedesk.html:3180`, existing, same IIFE), `history`/`counts` (existing, same IIFE).
- Produces: no new exports — `window.sdAISend`/`window.sdAIQuick` keep their existing signatures and call sites (6+ real callers via `sdAIQuick()`, including `finAIJobAdvice()`/`finAskCFO()`).

- [ ] **Step 1: Write the implementation**

Replace the block from `function sendMsg(msg){` through `window.sdAIQuick=function(q){...};` (`stonedesk.html:3189-3221`) with:

```js
  function sendMsg(msg){
    if(!msg.trim())return;
    sdAiBusy=true;
    appendMsg('user',msg);
    history.push({role:'user',content:msg});
    var typing=document.createElement('div');
    typing.id='ai-typing';
    typing.style.cssText='margin-bottom:10px;padding:12px;background:#f0fdf4;border-radius:10px;color:var(--muted);font-size:13px';
    typing.textContent='🤖 Thinking...';
    document.getElementById('ai-chat').appendChild(typing);
    document.getElementById('ai-chat').scrollTop=document.getElementById('ai-chat').scrollHeight;
    var toolDefs=Object.keys(SD_TOOLS).map(function(k){return SD_TOOLS[k].definition;});
    var sys='You are the AI assistant for StoneDesk, a stone fabrication shop management platform. Be concise, practical, and industry-specific. Never provide your own estimate, guess, or general-knowledge substitute for any fact a tool would have provided -- if a tool errors, is denied, or a question calls for data you have not actually retrieved via a tool this turn, say so plainly and stop.';
    function finish(reply){
      sdAiBusy=false;
      var t=document.getElementById('ai-typing');if(t)t.remove();
      appendMsg('assistant',reply);
      history.push({role:'assistant',content:reply});
      counts.today=(counts.today||0)+1;counts.total=(counts.total||0)+1;
      try{localStorage.setItem('sd_ai_counts',JSON.stringify(counts));}catch(e){}
      document.getElementById('ai-queries').textContent=counts.today;
      document.getElementById('ai-total').textContent=counts.total;
    }
    fetch('https://sairn.vercel.app/api/claude',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({app_id:'stonedesk',is_demo:true,system:sys,messages:history,tools:toolDefs})
    }).then(function(r){return r.json();}).then(function(r){
      var blocks=(r&&r.content)||[];
      var toolUse=blocks.filter(function(b){return b.type==='tool_use';})[0];
      if(!toolUse){
        var reply=(blocks[0]&&blocks[0].text?blocks[0].text:(r.completion||'Sorry, I could not get a response.'));
        finish(reply);
        return;
      }
      var outcome=sdExecuteTool(toolUse.name,sdCurrentRole(),toolUse.input);
      // Belt-and-suspenders, same pattern proven on every prior rollout:
      // reinforce the anti-fabrication instruction right next to the
      // trigger, in the same turn as the denial/error itself.
      var toolResultContent=outcome.ok?JSON.stringify(outcome.result):('Error: '+outcome.error+' Do not estimate or substitute your own figures for this -- state the restriction/error plainly and stop.');
      // Claude requires the assistant turn that requested the tool to be
      // present in history before the tool_result turn that answers it.
      history.push({role:'assistant',content:blocks});
      history.push({role:'user',content:[{type:'tool_result',tool_use_id:toolUse.id,content:toolResultContent}]});
      fetch('https://sairn.vercel.app/api/claude',{method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({app_id:'stonedesk',is_demo:true,system:sys,messages:history})
      }).then(function(r2){return r2.json();}).then(function(r2){
        var reply2=(r2.content&&r2.content[0]&&r2.content[0].text?r2.content[0].text:(r2.completion||'Sorry, I could not get a response.'));
        finish(reply2);
      }).catch(function(){
        finish('Could not reach Claude for the final answer. Connection error.');
      });
    }).catch(function(){
      sdAiBusy=false;
      var t=document.getElementById('ai-typing');if(t)t.remove();
      appendMsg('assistant','AI proxy unavailable. Please check your connection or try again.');
    });
  }
  window.sdAISend=function(){
    if(sdAiBusy){notify('Please wait for the current response first','warn');return;}
    var inp=document.getElementById('ai-input');
    sendMsg(inp.value);inp.value='';
  };
  window.sdAIQuick=function(q){
    if(sdAiBusy){notify('Please wait for the current response first','warn');return;}
    document.getElementById('ai-input').value=q;sdAISend();
  };
```

Note: `sdAIQuick()` also checks `sdAiBusy` directly (not just relying on the `sdAISend()` it calls) so the busy-rejection toast fires immediately rather than after an unnecessary DOM write to `#ai-input`. `app_id`/`is_demo` stay as the pre-existing hardcoded literals (`'stonedesk'`, `true`) — not changed, per the spec's scope.

- [ ] **Step 2: Syntax-check the modified script block**

Run: `python tools/checkblocks.py stonedesk.html`
Expected: `TOTAL_BLOCKS:128`, `FAILED_BLOCKS:0`.

Run: `python tools/div_balance_check.py stonedesk.html`
Expected: `RESULT:PASS`.

- [ ] **Step 3: Live interaction test — no-tool path and existing callers unaffected**

Open the app (locally or via the deployed pre-push injection technique used on prior rollouts), open the AI chat panel, ask a question unrelated to any tool ("what's a good waste factor for a waterfall island"). Confirm: exactly one "Thinking..." indicator appears and is replaced by one real answer, no console errors. Then trigger `finAIJobAdvice()` (Financials → add a job → "Margin Advice" button) and `finAskCFO()` and confirm both still produce real, on-topic answers through the now-tool-aware `sendMsg()` — these are real existing callers of `sdAIQuick()`, not hypothetical.

- [ ] **Step 4: Commit**

```bash
git add stonedesk.html
git commit -m "feat: StoneDesk -- sendMsg() tool-use round-trip + sdAiBusy guard

Adds StoneDesk's first-ever system prompt to this chat (previously
none existed) plus the tool-use round-trip: sends SD_TOOLS' definitions,
executes a requested tool via sdExecuteTool() (role-gated, error-safe),
sends the result back for a final grounded answer. Fixes the real
pre-existing concurrency gap: history (shared, multi-turn) had zero
guard before this change -- sdAiBusy now blocks a second send outright
via both public entry points (sdAISend/sdAIQuick) while one is in
flight, same shape as every prior rollout's fix. TOTAL_BLOCKS stays
128, FAILED_BLOCKS 0."
```

---

### Task 3: End-to-end verification, push, live-verify

**Files:** none modified — verification only.

- [ ] **Step 1: Full local re-check of the changed file**

```bash
python tools/checkblocks.py stonedesk.html
python tools/div_balance_check.py stonedesk.html
```

Expected: `TOTAL_BLOCKS:128`, `FAILED_BLOCKS:0`, `RESULT:PASS`.

- [ ] **Step 2: Guardian v2 pass**

Run the full `sairn-guardian-v2` check (Check 0 + numbered checks) against `stonedesk.html` before push, per the project's standing Push Protocol — this file in particular, given its size and the project's own repeated fragility warnings about it.

- [ ] **Step 3: Real interaction test — job profitability question**

With the app running against real data, ask the AI assistant a job-profitability question ("which jobs were most profitable," "what's my average margin across jobs," "how much profit on the [customer name] job"). Confirm the answer contains real customer names/margins/COGS from `sdFinJobs` — not a refusal or a generic answer.

- [ ] **Step 4: No-regression spot check on existing `sdAIQuick()` callers**

Exercise `finAIJobAdvice()` and `finAskCFO()` live and confirm both still produce real, on-topic answers exactly as before — these are the two real existing features most directly affected by this change (they call the now-rewired `sdAIQuick()`), not a hypothetical regression risk.

- [ ] **Step 5: Concurrency test (load-bearing)**

Send two questions back-to-back before the first resolves. Confirm: the second is rejected with the "Please wait for the current response first" toast (via `notify()`) before it touches `history`, exactly one exchange's worth of messages results from the first question, and inspecting `history` afterward shows a clean, correctly-ordered sequence (no interleaved or duplicated turns).

- [ ] **Step 6: Role-gate mechanism check (not exercised through the UI)**

`get_job_profitability` isn't sensitive, so nothing in the UI naturally exercises the gate for it. Confirm the mechanism itself directly: open the browser console on the live app and run `sdExecuteTool('get_job_profitability', 'owner', {})` (should succeed) and, temporarily, `SD_TOOLS.get_job_profitability.sensitive = true; sdExecuteTool('get_job_profitability', 'employee', {})` (should return `{ok:false, error:'This data is restricted to the owner role.'}`); then `sdExecuteTool('get_job_profitability', 'owner', {})` again (should still succeed). Reload the page afterward (the temporary mutation is not persisted).

- [ ] **Step 7: Streaming-path regression check**

Confirm `installStreamingHook()` and its override of `window.sendMessage` (if that code path is reachable/tested in this app) are completely unaffected — this plan never touches that function or `window.sendMessage`.

- [ ] **Step 8: `sanitizeTools()` regression check for this app_id specifically**

```bash
curl -s -X POST https://sairn.vercel.app/api/claude \
  -H 'Content-Type: application/json' \
  -d '{"app_id":"stonedesk","is_demo":true,"max_tokens":50,"system":"test","messages":[{"role":"user","content":"say hi"}],"tools":[{"name":"get_job_profitability","description":"x","input_schema":{"type":"object","properties":{}}}]}'
```

Expected: HTTP 200 with a real Anthropic response shape (`content` array present), not a 400.

- [ ] **Step 9: Push**

```bash
git push origin main
```

- [ ] **Step 10: Live-verify**

```bash
curl -s https://sairn.vercel.app/stonedesk | grep -c "sdExecuteTool"
```

Expected: non-zero. Then repeat Steps 3-5's tests against the **live** URL, not just a local/injected copy — per the project's standing rule that a clean push is not proof the live app reflects the change, weighted extra heavily on this specific file per project convention.

- [ ] **Step 11: Update the spec's status line**

Edit `docs/superpowers/specs/2026-08-10-stonedesk-ai-tool-calling-design.md`'s `**Status:**` line to note the foundation, `get_job_profitability`, and the concurrency fix are implemented and live-verified, with the date. Commit this doc-only change separately.
