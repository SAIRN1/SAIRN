# SAIRNbuild AI Tool-Calling Foundation + get_jobs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give SAIRNbuild's `aiAsk()` (`sairnbuild.html:6410`) real function-calling access to the real job roster, via one proof tool (`get_jobs`), merged alongside the `web_search_20250305` server tool this chat already uses — without disturbing that tool's existing behavior or the chat's already-correct concurrency guard.

**Architecture:** `BLD_TOOLS`/`bldRegisterTool`/`bldExecuteTool` — same registry shape as SAIRNvet's/SAIRNcode's (no `sensitive` parameter, no real auth exists). `aiAsk()`'s `tools` array becomes `[web_search_definition].concat(toolDefs)`. A response's `content` array may contain a `text` block (with optional `.citations`, from web search), a custom `tool_use` block (from `get_jobs`), or both in principle — the rewire checks for a custom `tool_use` block specifically (distinct from Anthropic's own `server_tool_use`/`web_search_tool_result` block types) and, if present, does a second round-trip; otherwise renders exactly as today. The existing `aiAskSeq`/`myAiAskSeq` guard is checked again after the new second fetch, not replaced.

**Tech Stack:** Vanilla JS (`sairnbuild.html`, no framework). Verified the same way every prior rollout was: `tools/checkblocks.py` / `tools/div_balance_check.py` on the file, a temporary `node:assert` scratch harness for pure logic, plus a real live-interaction test against the deployed app.

## Global Constraints

- Read-only tool only — `get_jobs` may not create, modify, or delete any record. (Spec §2)
- No new persistence — reads `jobs()` (`sairnbuild.html:2473`) directly. (Spec §2)
- `get_jobs` returns `{address, client, value, stage, start, target, blocked}` only — `id`, `phone`, `permit`, `notes` excluded. (Spec §4)
- No `sensitive`/role parameter anywhere in this dispatcher — no real auth backend exists. (Spec §1, §3)
- No new concurrency guard — `aiAskSeq`/`myAiAskSeq` (`sairnbuild.html:6447-6448, 6457, 6481`) already exists and is extended to also guard the new second fetch, not replaced. (Spec §1, §3)
- The new custom tool definitions are **merged** into the existing `tools` array alongside `{type:'web_search_20250305',name:'web_search',max_uses:3}` — never sent as a separate request or a replacement array. (Spec §1, §3)
- The existing web-search text/citation extraction logic (`sairnbuild.html:6460-6471`) is preserved unchanged for the no-custom-tool-use path. (Spec §2)
- `fpAnalyze`, `claimGeneratePacket`, `costExplain`, `ssaAnalyze`, `disRespond`, `mktBriefing`, and `api/claude.js` are not touched. (Spec §2)
- `python tools/checkblocks.py sairnbuild.html` and `python tools/div_balance_check.py sairnbuild.html` must stay clean (0 failed / PASS) after every change.
- Before push: full Guardian v2 check on `sairnbuild.html`. After push: live-verify against `sairn.vercel.app/sairnbuild` directly, not assumed from a clean push (project Push Protocol).

---

### Task 1: `sairnbuild.html` — tool registry, dispatcher, and the `get_jobs` tool

**Files:**
- Modify: `sairnbuild.html` (insert immediately before `async function aiAsk()` at `sairnbuild.html:6410`)

**Interfaces:**
- Consumes: `jobs()` (`sairnbuild.html:2473`, existing).
- Produces: `BLD_TOOLS` (object, tool name → `{definition, run}` — no `sensitive` field), `bldExecuteTool(name, input)` → `{ok: true, result: any} | {ok: false, error: string}` — used by Task 2.

- [ ] **Step 1: Write the implementation**

Insert immediately before `async function aiAsk(){` (`sairnbuild.html:6410`):

```js
// AI tool-calling dispatcher (2026-08-10) -- ports the mechanism proven
// live on every other SAIRN app. Registry of read-only tools aiAsk()
// may request via Claude's tool-use, MERGED into the existing
// web_search_20250305 server tool this chat already sends -- not a
// replacement. Every tool is:
//   - read-only (never creates/modifies/deletes anything)
//   - wrapped so a thrown error or unexpected data shape becomes an honest
//     {ok:false} result, never a crash or a silently wrong answer
// No sensitivity/role-gate concept here -- SAIRNbuild has no real,
// server-verified auth (prole comes from a client-side PIN pick), same
// reasoning already applied to SAIRNvet's/SAIRNcode's dispatchers.
// See docs/superpowers/specs/2026-08-10-sairnbuild-ai-tool-calling-design.md
var BLD_TOOLS = {};

function bldRegisterTool(name, description, inputSchema, run) {
  BLD_TOOLS[name] = {
    definition: { name: name, description: description, input_schema: inputSchema },
    run: run
  };
}

function bldExecuteTool(name, input) {
  var tool = BLD_TOOLS[name];
  if (!tool) return { ok: false, error: 'No tool named "' + name + '" exists.' };
  try {
    return { ok: true, result: tool.run(input || {}) };
  } catch (e) {
    return { ok: false, error: 'Could not retrieve that data right now.' };
  }
}

bldRegisterTool(
  'get_jobs',
  'Look up the current job roster: address, client, contract value, stage, start date, target completion date, and a blocked-reason if the job is currently blocked. Does NOT include subcontractor, RFI, submittal, change-order, bid, or punch-list data -- those are not available to this tool.',
  { type: 'object', properties: {}, required: [] },
  function (input) {
    // input intentionally unused -- this tool takes no real arguments, but
    // accepts one for interface consistency with bldExecuteTool(name, input),
    // matching every prior tool's convention.
    return jobs().map(function (j) {
      return {
        address: j.address,
        client: j.client,
        value: j.value,
        stage: j.stage,
        start: j.start,
        target: j.target,
        blocked: j.blocked
      };
    });
  }
);
```

- [ ] **Step 2: Syntax-check the modified script block**

Run: `python tools/checkblocks.py sairnbuild.html`
Expected: same `TOTAL_BLOCKS` as the pre-change baseline (run it once before this edit if you don't already know the number), `FAILED_BLOCKS:0`.

Run: `python tools/div_balance_check.py sairnbuild.html`
Expected: `RESULT:PASS`.

- [ ] **Step 3: Behavioral verification with a temporary Node harness**

Both the dispatcher and the tool's `run()` have no DOM dependency. Create a scratch file (not committed — delete after this step):

```js
// scratch verification, delete after running
var assert = require('assert');

var BLD_TOOLS = {};
function bldRegisterTool(name, description, inputSchema, run) {
  BLD_TOOLS[name] = { definition: { name: name, description: description, input_schema: inputSchema }, run: run };
}
function bldExecuteTool(name, input) {
  var tool = BLD_TOOLS[name];
  if (!tool) return { ok: false, error: 'No tool named "' + name + '" exists.' };
  try { return { ok: true, result: tool.run(input || {}) }; } catch (e) { return { ok: false, error: 'Could not retrieve that data right now.' }; }
}

// -- dispatcher checks --
bldRegisterTool('ping', 'test tool', {type:'object'}, function () { return 'pong'; });
bldRegisterTool('broken', 'test throwing tool', {type:'object'}, function () { throw new Error('boom'); });
assert.deepStrictEqual(bldExecuteTool('ping', {}), { ok: true, result: 'pong' });
assert.deepStrictEqual(bldExecuteTool('nonexistent', {}), { ok: false, error: 'No tool named "nonexistent" exists.' });
assert.strictEqual(bldExecuteTool('broken', {}).ok, false);
console.log('bldExecuteTool: all 3 checks passed');

// -- get_jobs tool check, stubbing jobs() --
function jobs() {
  return [
    { id: 'J-2601', address: '1420 Center Ridge Rd, Westlake OH', client: 'Hartley Residence', phone: '(440) 555-0142', value: 186500, stage: 'in_progress', start: '2026-05-04', target: '2026-08-14', permit: 'WL-26-0412', blocked: '', notes: 'Full kitchen + primary bath remodel' },
    { id: 'J-2603', address: '315 Moore Rd, Avon Lake OH', client: 'Whitfield Residence', phone: '(440) 555-0315', value: 98750, stage: 'blocked', start: '2026-06-01', target: '2026-08-29', permit: 'AL-26-0117', blocked: 'Failed rough electrical - re-inspection 8/6', notes: 'Addition, 480 sqft' }
  ];
}

bldRegisterTool('get_jobs', 'x', { type: 'object' }, function (input) {
  return jobs().map(function (j) {
    return { address: j.address, client: j.client, value: j.value, stage: j.stage, start: j.start, target: j.target, blocked: j.blocked };
  });
});

var out = BLD_TOOLS.get_jobs.run({});
assert.strictEqual(out.length, 2);
assert.strictEqual(out[0].client, 'Hartley Residence');
assert.strictEqual(out[1].blocked, 'Failed rough electrical - re-inspection 8/6');
assert.strictEqual(out[0].id, undefined, 'id must never appear in get_jobs output');
assert.strictEqual(out[0].phone, undefined, 'phone must never appear in get_jobs output');
assert.strictEqual(out[0].permit, undefined, 'permit must never appear in get_jobs output');
assert.strictEqual(out[0].notes, undefined, 'notes must never appear in get_jobs output');
console.log('get_jobs tool: all 6 checks passed');
```

Run: `node <scratch-file>.js`
Expected: `bldExecuteTool: all 3 checks passed` then `get_jobs tool: all 6 checks passed`. Delete the scratch file afterward.

- [ ] **Step 4: Commit**

```bash
git add sairnbuild.html
git commit -m "feat: SAIRNbuild -- tool-calling dispatcher + get_jobs proof tool

Ports the mechanism proven live on every other SAIRN app, minus the
sensitivity/role-gate concept -- SAIRNbuild has no real, server-verified
auth (prole comes from a client-side PIN pick), same reasoning already
applied to SAIRNvet's/SAIRNcode's dispatchers. BLD_TOOLS/
bldRegisterTool/bldExecuteTool plus one read-only tool, get_jobs
(address/client/value/stage/start/target/blocked). id/phone/permit/
notes deliberately excluded. aiAsk() doesn't call any of this yet --
verified standalone via a Node harness."
```

---

### Task 2: `sairnbuild.html` — `aiAsk()` tool-use round-trip, merged with `web_search_20250305`

**Files:**
- Modify: `sairnbuild.html:6410-6484` (`aiAsk()`)

**Interfaces:**
- Consumes: `bldExecuteTool(name, input)` (Task 1), `BLD_TOOLS` (Task 1, read via `Object.keys(BLD_TOOLS).map(k => BLD_TOOLS[k].definition)`), `PROXY`, `APP_ID`, `bldAiError(data)`, `bldAiChat()`, `bldLocalToday()`, `recordBldSharedTopics(q)`, `rAiHistory()`, `SB_TRADE_SEQUENCE_KNOWLEDGE`, `SB_TRADE_TAXONOMY_KNOWLEDGE`, `buildBldSharedCompanyContext()` (all existing, unmodified), `aiAskSeq` (existing global counter).
- Produces: no new exports — `aiAsk()` keeps its existing signature and call site (the "Ask" button's `onclick`).

- [ ] **Step 1: Write the implementation**

Replace `aiAsk()` (`sairnbuild.html:6410-6484`) with:

```js
async function aiAsk(){
  var q=$('ai-question').value.trim();
  if(!q){toast('Enter a question first');return;}
  var jobId=$('ai-job').value;
  var j=jobId?jobs().find(function(x){return x.id===jobId;}):null;
  $('ai-answer-wrap').style.display='block';
  $('ai-answer').textContent='Thinking...';
  var sys='You are the SAIRNbuild AI Assistant for Pinnacle Industries LLC, a residential/'+
    'light-commercial general contractor in the Cleveland/Westlake OH area. Answer scope '+
    'questions, help draft contract language, give general building-code reference pointers, '+
    'answer questions about current building products, materials, pricing, availability, and '+
    'trends, and answer questions about which trades/subcontractors a project needs and how '+
    'to select or bundle them for efficiency -- all of these are in scope, do not decline a '+
    'question just because it asks about material trends, pricing, or trade/sub selection '+
    'rather than a specific job. '+
    (j?('Current job context: '+(j.client||j.address)+', stage '+j.stage+'. '):'')+
    'If a question touches build sequencing, scheduling order, or trade timing, use the '+
    'trade-sequence knowledge below to proactively flag any real violation even if the '+
    'question does not explicitly ask about it. '+
    'If a question touches which trades/subs a project needs, use the trade-taxonomy '+
    'knowledge below -- but only name a specific sub if the roster context below actually '+
    'lists one; otherwise speak in terms of trades, not invented company names. '+
    'If a question depends on current information -- specific products, materials, pricing, '+
    'availability, codes, or trends that could have changed since training -- you MUST use '+
    'the web search tool rather than answering from memory alone, so the trade-knowledge '+
    'base stays current without manual upkeep. You may also look up the real job roster '+
    '(address, client, value, stage, dates, and blocked-reason) via the get_jobs tool when a '+
    'question needs it -- never guess or invent a job\'s status or details. '+
    'Always end with a one-line reminder that code/legal answers must be verified with the '+
    'local building department or contract counsel before being relied on. Plain ASCII only, '+
    'no Unicode box characters. Keep it under 200 words.\n\n'+SB_TRADE_SEQUENCE_KNOWLEDGE+
    '\n\n'+SB_TRADE_TAXONOMY_KNOWLEDGE;
  var sharedCtx=(typeof buildBldSharedCompanyContext==='function')?buildBldSharedCompanyContext():'';
  if(sharedCtx) sys+='\n\n'+sharedCtx;
  var msgs=[{role:'user',content:q}];
  // Guard against out-of-order async responses -- same shape and same
  // consequence class as SAIRNbiz's/SAIRNvet's same-night fixes (misattributed
  // answers under concurrent questions), except here the misattributed answer
  // also gets permanently saved into bld_ai_chat history if not caught.
  aiAskSeq++;
  var myAiAskSeq=aiAskSeq;
  var toolDefs=Object.keys(BLD_TOOLS).map(function(k){return BLD_TOOLS[k].definition;});
  var toolsForRequest=[{type:'web_search_20250305',name:'web_search',max_uses:3}].concat(toolDefs);
  function saveAndRender(answer){
    $('ai-answer').textContent=answer;
    var list=bldAiChat();
    list.push({id:'AIQ-'+String(Date.now()).slice(-5),job_id:jobId,date:bldLocalToday(),question:q,answer:answer});
    st('bld_ai_chat',list);
    if(typeof recordBldSharedTopics==='function') recordBldSharedTopics(q);
    $('ai-question').value='';
    rAiHistory();
  }
  try{
    var res=await fetch(PROXY,{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({app_id:APP_ID,is_demo:true,system:sys,messages:msgs,
        tools:toolsForRequest})
    });
    if(!res.ok)throw new Error('Claude error '+res.status);
    var data=await res.json();
    if(myAiAskSeq!==aiAskSeq) return;
    var aiErr=bldAiError(data);
    if(aiErr){$('ai-answer').textContent=aiErr;return;}
    var content=data.content||[];
    // A custom tool_use block (get_jobs) is a distinct block type from
    // Anthropic's own server_tool_use/web_search_tool_result blocks used
    // by the web_search tool -- both can appear in the same content array
    // if the model used both in one turn, so this checks for a custom
    // tool_use specifically rather than assuming mutual exclusivity.
    var toolUse=content.filter(function(b){return b.type==='tool_use';})[0];
    if(toolUse){
      var outcome=bldExecuteTool(toolUse.name,toolUse.input);
      // Belt-and-suspenders, same pattern proven on every prior rollout:
      // reinforce the anti-fabrication instruction right next to the
      // trigger, in the same turn as the denial/error itself.
      var toolResultContent=outcome.ok?JSON.stringify(outcome.result):('Error: '+outcome.error+' Do not estimate or substitute your own figures for this -- state the restriction/error plainly and stop.');
      var followUpMessages=[
        {role:'user',content:q},
        {role:'assistant',content:content},
        {role:'user',content:[{type:'tool_result',tool_use_id:toolUse.id,content:toolResultContent}]}
      ];
      var res2=await fetch(PROXY,{
        method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({app_id:APP_ID,is_demo:true,system:sys,messages:followUpMessages})
      });
      if(!res2.ok)throw new Error('Claude error '+res2.status);
      var data2=await res2.json();
      if(myAiAskSeq!==aiAskSeq) return;
      var aiErr2=bldAiError(data2);
      if(aiErr2){$('ai-answer').textContent=aiErr2;return;}
      var answer2=(data2.content&&data2.content[0]&&data2.content[0].text)||'No response text returned.';
      saveAndRender(answer2);
      return;
    }
    // No custom tool_use -- existing web-search text/citation handling,
    // unchanged. A web-search turn returns text interleaved with
    // server_tool_use/web_search_tool_result blocks, not just content[0]
    // -- join every text block in order instead of assuming the old
    // single-block shape.
    var text=content.filter(function(b){return b.type==='text';}).map(function(b){return b.text;}).join('');
    var sources=[];
    content.forEach(function(b){
      if(b.type==='text'&&Array.isArray(b.citations)){
        b.citations.forEach(function(c){if(c.url&&sources.indexOf(c.url)===-1)sources.push(c.url);});
      }
    });
    if(sources.length) text+='\n\nSources:\n'+sources.map(function(u){return '- '+u;}).join('\n');
    var answer=text||'No response text returned.';
    saveAndRender(answer);
  }catch(e){
    if(myAiAskSeq!==aiAskSeq) return;
    $('ai-answer').textContent='Could not reach Claude. Check your connection and try again.';
  }
}
```

Note: `saveAndRender()` is a small new helper factoring out the persist-and-render steps duplicated between the tool-use path and the existing no-tool-use path — both call it with a final answer string; no behavior change from what the original code already did in the no-tool-use branch.

- [ ] **Step 2: Syntax-check the modified script block**

Run: `python tools/checkblocks.py sairnbuild.html`
Expected: same `TOTAL_BLOCKS` as Task 1's result, `FAILED_BLOCKS:0`.

Run: `python tools/div_balance_check.py sairnbuild.html`
Expected: `RESULT:PASS`.

- [ ] **Step 3: Live interaction test — existing web-search path unaffected**

Open the app (locally or via the deployed pre-push injection technique used on prior rollouts), ask a question that should trigger web search ("what's the current price trend for 2x4 lumber"). Confirm: the answer still includes real search-grounded content and a "Sources:" list exactly as before, with no `get_jobs` tool invoked for this question.

- [ ] **Step 4: Commit**

```bash
git add sairnbuild.html
git commit -m "feat: SAIRNbuild -- aiAsk() tool-use round-trip for get_jobs

Merges BLD_TOOLS' definitions into the existing tools array alongside
web_search_20250305 (not a replacement). Checks the response content
for a custom tool_use block (distinct from Anthropic's own
server_tool_use/web_search_tool_result block types, which can coexist
in the same turn) and, if present, executes via bldExecuteTool()
(error-safe) and does a second round-trip for the final answer. The
existing web-search text/citation extraction path is unchanged for
turns that don't use get_jobs. Extends the existing aiAskSeq guard to
also cover the new second fetch -- no new concurrency mechanism
introduced."
```

---

### Task 3: End-to-end verification, push, live-verify

**Files:** none modified — verification only.

- [ ] **Step 1: Full local re-check of the changed file**

```bash
python tools/checkblocks.py sairnbuild.html
python tools/div_balance_check.py sairnbuild.html
```

Expected: both checks show 0 failures / PASS.

- [ ] **Step 2: Guardian v2 pass**

Run the full `sairn-guardian-v2` check (Check 0 + numbered checks) against `sairnbuild.html` before push, per the project's standing Push Protocol.

- [ ] **Step 3: Real interaction test — job roster question**

With the app running against real seeded data, ask the AI a job question ("which jobs are blocked and why," "what's the value of the Hartley job," "list our jobs and their stages"). Confirm the answer contains real addresses/clients/values/blocked-reasons from `bld_jobs` — not a generic non-answer.

- [ ] **Step 4: No-regression test on the existing web-search tool**

Ask a question that should trigger web search ("what's the current price of 2x4 lumber," "any recent changes to residential electrical code"). Confirm it still works exactly as before — real search-grounded content, sources listed, no `get_jobs` invoked for a question that doesn't need it.

- [ ] **Step 5: Mixed-turn sanity check**

Ask a question that plausibly invites both ("Job Whitfield is blocked — is there anything about EU/US material sourcing I should search for while I wait on the re-inspection?"). Confirm the answer doesn't crash or silently drop either signal — at minimum, the `get_jobs`-sourced blocked-reason should appear if the model chose to use that tool; a search citation may or may not appear depending on the model's own judgment call, which is acceptable (this test verifies robustness, not a specific tool-choice outcome).

- [ ] **Step 6: Concurrency test (extending the existing guard)**

Send two questions back-to-back before the first resolves — one that triggers `get_jobs` and one that doesn't. Confirm only the *later* question's answer ever renders in the result area (matching the existing `aiAskSeq` convention), with no mixed or stuck state across the tool-use round-trip specifically.

- [ ] **Step 7: `sanitizeTools()` regression check for a mixed server-tool + custom-tool array, this app_id specifically**

```bash
curl -s -X POST https://sairn.vercel.app/api/claude \
  -H 'Content-Type: application/json' \
  -d '{"app_id":"sairnbuild","is_demo":true,"max_tokens":50,"system":"test","messages":[{"role":"user","content":"say hi"}],"tools":[{"type":"web_search_20250305","name":"web_search","max_uses":3},{"name":"get_jobs","description":"x","input_schema":{"type":"object","properties":{}}}]}'
```

Expected: HTTP 200 with a real Anthropic response shape (`content` array present), not a 400 — confirms `sanitizeTools()` passes both the server tool and the custom tool through together correctly for this app_id specifically.

- [ ] **Step 8: Push**

```bash
git push origin main
```

- [ ] **Step 9: Live-verify**

```bash
curl -s https://sairn.vercel.app/sairnbuild | grep -c "bldExecuteTool"
```

Expected: non-zero. Then repeat Steps 3-6's tests against the **live** URL, not just a local/injected copy — per the project's standing rule that a clean push is not proof the live app reflects the change.

- [ ] **Step 10: Update the spec's status line**

Edit `docs/superpowers/specs/2026-08-10-sairnbuild-ai-tool-calling-design.md`'s `**Status:**` line to note the foundation and `get_jobs` are implemented and live-verified, with the date. Commit this doc-only change separately.
