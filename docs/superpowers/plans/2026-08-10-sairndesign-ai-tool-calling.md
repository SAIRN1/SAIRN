# SAIRNdesign AI Tool-Calling Foundation + get_clients Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give SAIRNdesign's `sendAI()` (`sairndesign.html:1212`) real function-calling access to the real client roster, via one proof tool (`get_clients`), while extending — not replacing — the existing splice-based `aiHist` reordering fix (`sairndesign.html:1220-1230`).

**Architecture:** `SDN_TOOLS`/`sdnRegisterTool`/`sdnExecuteTool` — same registry shape as SAIRNvet's/SAIRNcode's/SAIRNbuild's (no `sensitive` parameter, no real auth exists). `sendAI()`'s existing fetch gains a `tools` field. If a `tool_use` block comes back, the follow-up fetch is built from this request's own local turn data (not the shared, possibly-mutated `aiHist`) — matching every prior rollout's pattern — and on success, the full 3-entry tool-use exchange is spliced into `aiHist` as one atomic group at the same `myUserIdx+1` position the existing fix already uses for its single-entry case.

**Tech Stack:** Vanilla JS (`sairndesign.html`, no framework). Verified the same way every prior rollout was: `tools/checkblocks.py` / `tools/div_balance_check.py` on the file, a temporary `node:assert` scratch harness for pure logic, plus a real live-interaction test against the deployed app.

## Global Constraints

- Read-only tool only — `get_clients` may not create, modify, or delete any record. (Spec §2)
- No new persistence — reads `clients()` (`sairndesign.html:1077`) directly. (Spec §2)
- `get_clients` returns `{name, company, phone, email, address, status}` only — `id`, `notes` excluded. (Spec §4)
- No `sensitive`/role parameter anywhere in this dispatcher — no real auth backend exists. (Spec §1, §3)
- **No new concurrency mechanism** — the existing `myUserIdx`-splice fix is extended, not replaced. The follow-up (second) fetch's `messages` are built from this request's own local turn data, never re-read from the shared `aiHist` (which may be mutated by other concurrent requests by then). The final splice inserts all 3 new entries as one atomic `aiHist.splice(myUserIdx+1, 0, entry1, entry2, entry3)` call, not three separate splices. (Spec §1, §3)
- The Spec Sheet compliance-review feature (`sairndesign.html:1378`) is not touched. (Spec §2)
- No changes to `api/claude.js`. (Spec §2)
- `python tools/checkblocks.py sairndesign.html` and `python tools/div_balance_check.py sairndesign.html` must stay clean (0 failed / PASS) after every change.
- Before push: full Guardian v2 check on `sairndesign.html`. After push: live-verify against `sairn.vercel.app/sairndesign` directly, not assumed from a clean push (project Push Protocol).

---

### Task 1: `sairndesign.html` — tool registry, dispatcher, and the `get_clients` tool

**Files:**
- Modify: `sairndesign.html` (insert immediately after `// ── AI ASSISTANT (generic) ──...` and `var aiHist=[];` at `sairndesign.html:1208-1209`, before `function clrAI(){...}`)

**Interfaces:**
- Consumes: `clients()` (`sairndesign.html:1077`, existing).
- Produces: `SDN_TOOLS` (object, tool name → `{definition, run}` — no `sensitive` field), `sdnExecuteTool(name, input)` → `{ok: true, result: any} | {ok: false, error: string}` — used by Task 2.

- [ ] **Step 1: Write the implementation**

Insert immediately after `var aiHist=[];` (`sairndesign.html:1209`), before `function clrAI(){...}`:

```js
// AI tool-calling dispatcher (2026-08-10) -- ports the mechanism proven
// live on every other SAIRN app. Registry of read-only tools sendAI()
// may request via Claude's tool-use. Every tool is:
//   - read-only (never creates/modifies/deletes anything)
//   - wrapped so a thrown error or unexpected data shape becomes an honest
//     {ok:false} result, never a crash or a silently wrong answer
// No sensitivity/role-gate concept here -- SAIRNdesign has no real,
// server-verified auth (prole comes from a client-side PIN match), same
// reasoning already applied to SAIRNvet's/SAIRNcode's/SAIRNbuild's
// dispatchers.
// See docs/superpowers/specs/2026-08-10-sairndesign-ai-tool-calling-design.md
var SDN_TOOLS = {};

function sdnRegisterTool(name, description, inputSchema, run) {
  SDN_TOOLS[name] = {
    definition: { name: name, description: description, input_schema: inputSchema },
    run: run
  };
}

function sdnExecuteTool(name, input) {
  var tool = SDN_TOOLS[name];
  if (!tool) return { ok: false, error: 'No tool named "' + name + '" exists.' };
  try {
    return { ok: true, result: tool.run(input || {}) };
  } catch (e) {
    return { ok: false, error: 'Could not retrieve that data right now.' };
  }
}

sdnRegisterTool(
  'get_clients',
  'Look up the current client roster: name, company, phone, email, address, and status. Does NOT include project, spec-item, vendor, contract, invoice, proposal, team, or schedule data -- those are not available to this tool.',
  { type: 'object', properties: {}, required: [] },
  function (input) {
    // input intentionally unused -- this tool takes no real arguments, but
    // accepts one for interface consistency with sdnExecuteTool(name, input),
    // matching every prior tool's convention.
    return clients().map(function (c) {
      return {
        name: c.name,
        company: c.company,
        phone: c.phone,
        email: c.email,
        address: c.address,
        status: c.status
      };
    });
  }
);
```

- [ ] **Step 2: Syntax-check the modified script block**

Run: `python tools/checkblocks.py sairndesign.html`
Expected: same `TOTAL_BLOCKS` as the pre-change baseline (run it once before this edit if you don't already know the number), `FAILED_BLOCKS:0`.

Run: `python tools/div_balance_check.py sairndesign.html`
Expected: `RESULT:PASS`.

- [ ] **Step 3: Behavioral verification with a temporary Node harness**

Both the dispatcher and the tool's `run()` have no DOM dependency. Create a scratch file (not committed — delete after this step):

```js
// scratch verification, delete after running
var assert = require('assert');

var SDN_TOOLS = {};
function sdnRegisterTool(name, description, inputSchema, run) {
  SDN_TOOLS[name] = { definition: { name: name, description: description, input_schema: inputSchema }, run: run };
}
function sdnExecuteTool(name, input) {
  var tool = SDN_TOOLS[name];
  if (!tool) return { ok: false, error: 'No tool named "' + name + '" exists.' };
  try { return { ok: true, result: tool.run(input || {}) }; } catch (e) { return { ok: false, error: 'Could not retrieve that data right now.' }; }
}

// -- dispatcher checks --
sdnRegisterTool('ping', 'test tool', {type:'object'}, function () { return 'pong'; });
sdnRegisterTool('broken', 'test throwing tool', {type:'object'}, function () { throw new Error('boom'); });
assert.deepStrictEqual(sdnExecuteTool('ping', {}), { ok: true, result: 'pong' });
assert.deepStrictEqual(sdnExecuteTool('nonexistent', {}), { ok: false, error: 'No tool named "nonexistent" exists.' });
assert.strictEqual(sdnExecuteTool('broken', {}).ok, false);
console.log('sdnExecuteTool: all 3 checks passed');

// -- get_clients tool check, stubbing clients() --
function clients() {
  return [
    { id: 'CL-1', name: 'Sarah Whitfield', company: '', phone: '(440) 555-0142', email: 'sarah.whitfield@example.com', address: '315 Moore Rd, Avon Lake OH', status: 'Active', notes: 'Referred by Hartley project' },
    { id: 'CL-2', name: 'Marcus Delgado', company: 'Delgado Property Group', phone: '(440) 555-0188', email: 'marcus@delgadopg.com', address: '88 Lake Rd, Rocky River OH', status: 'Active', notes: 'Multi-unit, repeat client' }
  ];
}

sdnRegisterTool('get_clients', 'x', { type: 'object' }, function (input) {
  return clients().map(function (c) {
    return { name: c.name, company: c.company, phone: c.phone, email: c.email, address: c.address, status: c.status };
  });
});

var out = SDN_TOOLS.get_clients.run({});
assert.strictEqual(out.length, 2);
assert.strictEqual(out[0].name, 'Sarah Whitfield');
assert.strictEqual(out[1].company, 'Delgado Property Group');
assert.strictEqual(out[0].id, undefined, 'id must never appear in get_clients output');
assert.strictEqual(out[0].notes, undefined, 'notes must never appear in get_clients output');
console.log('get_clients tool: all 4 checks passed');
```

Run: `node <scratch-file>.js`
Expected: `sdnExecuteTool: all 3 checks passed` then `get_clients tool: all 4 checks passed`. Delete the scratch file afterward.

- [ ] **Step 4: Commit**

```bash
git add sairndesign.html
git commit -m "feat: SAIRNdesign -- tool-calling dispatcher + get_clients proof tool

Ports the mechanism proven live on every other SAIRN app, minus the
sensitivity/role-gate concept -- SAIRNdesign has no real, server-
verified auth (prole comes from a client-side PIN match), same
reasoning already applied to SAIRNvet's/SAIRNcode's/SAIRNbuild's
dispatchers. SDN_TOOLS/sdnRegisterTool/sdnExecuteTool plus one
read-only tool, get_clients (name/company/phone/email/address/status).
id/notes deliberately excluded. sendAI() doesn't call any of this yet
-- verified standalone via a Node harness."
```

---

### Task 2: `sairndesign.html` — `sendAI()` tool-use round-trip, preserving the splice-reordering fix

**Files:**
- Modify: `sairndesign.html:1212-1247` (`sendAI()`)

**Interfaces:**
- Consumes: `sdnExecuteTool(name, input)` (Task 1), `SDN_TOOLS` (Task 1, read via `Object.keys(SDN_TOOLS).map(k => SDN_TOOLS[k].definition)`), `PROXY`, `APP_ID`, `sdnAiError(data)`, `H(s)`, `aiHist` (all existing, unmodified).
- Produces: no new exports — `sendAI()` keeps its existing signature and call site (`askAI(q)`, `sairndesign.html:1211`).

- [ ] **Step 1: Write the implementation**

Replace `sendAI()` (`sairndesign.html:1212-1247`) with:

```js
async function sendAI(){
  var inp=$('ainp'),q=(inp.value||'').trim();
  if(!q)return;
  inp.value='';
  var chat=$('achat');
  if(chat.querySelector('div[style*="text-align:center"]'))chat.innerHTML='';
  chat.innerHTML+='<div class="amu">'+H(q)+'</div>';
  chat.scrollTop=chat.scrollHeight;
  // FIXED 2026-08-09: see the original comment history for why this
  // splices at a recorded index rather than pushing to the end -- that
  // reasoning is unchanged. The tool-use path below extends it to splice
  // a 3-entry group atomically instead of a single assistant entry.
  var myUserIdx=aiHist.length;
  aiHist.push({role:'user',content:q});
  var thinking=document.createElement('div');thinking.className='ama';thinking.textContent='Thinking...';chat.appendChild(thinking);
  chat.scrollTop=chat.scrollHeight;
  var toolDefs=Object.keys(SDN_TOOLS).map(function(k){return SDN_TOOLS[k].definition;});
  try{
    var res=await fetch(PROXY,{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({app_id:APP_ID,is_demo:true,max_tokens:500,
        system:'You are a studio operations assistant for an interior design business (trade markup, client proposals, vendor management, project scheduling). Be concise and practical. Never provide your own estimate, guess, or general-knowledge substitute for any fact a tool would have provided -- if a tool errors, is denied, or a question calls for data you have not actually retrieved via a tool this turn, say so plainly and stop.',
        messages:aiHist.map(function(m){return {role:m.role,content:m.content};}),
        tools:toolDefs})});
    var data=await res.json();
    var aiErr=sdnAiError(data);
    if(aiErr){thinking.textContent=aiErr;chat.scrollTop=chat.scrollHeight;return;}
    var blocks=(data&&data.content)||[];
    var toolUse=blocks.filter(function(b){return b.type==='tool_use';})[0];
    if(!toolUse){
      var text=(blocks[0]&&blocks[0].text)||'No response text returned.';
      thinking.textContent=text;
      aiHist.splice(myUserIdx+1,0,{role:'assistant',content:text});
      chat.scrollTop=chat.scrollHeight;
      return;
    }
    var outcome=sdnExecuteTool(toolUse.name,toolUse.input);
    // Belt-and-suspenders, same pattern proven on every prior rollout:
    // reinforce the anti-fabrication instruction right next to the
    // trigger, in the same turn as the denial/error itself.
    var toolResultContent=outcome.ok?JSON.stringify(outcome.result):('Error: '+outcome.error+' Do not estimate or substitute your own figures for this -- state the restriction/error plainly and stop.');
    // Built from this request's OWN local turn data, not re-read from the
    // shared aiHist -- aiHist may have been mutated by other concurrent
    // requests by the time this follow-up fires, matching every prior
    // rollout's pattern of using local turn state for the follow-up call.
    var followUpMessages=[
      {role:'user',content:q},
      {role:'assistant',content:blocks},
      {role:'user',content:[{type:'tool_result',tool_use_id:toolUse.id,content:toolResultContent}]}
    ];
    var res2=await fetch(PROXY,{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({app_id:APP_ID,is_demo:true,max_tokens:500,
        system:'You are a studio operations assistant for an interior design business (trade markup, client proposals, vendor management, project scheduling). Be concise and practical. Never provide your own estimate, guess, or general-knowledge substitute for any fact a tool would have provided -- if a tool errors, is denied, or a question calls for data you have not actually retrieved via a tool this turn, say so plainly and stop.',
        messages:followUpMessages})});
    var data2=await res2.json();
    var aiErr2=sdnAiError(data2);
    if(aiErr2){thinking.textContent=aiErr2;chat.scrollTop=chat.scrollHeight;return;}
    var finalText=(data2.content&&data2.content[0]&&data2.content[0].text)||'No response text returned.';
    thinking.textContent=finalText;
    // Atomic 3-entry splice at the same recorded index the single-entry
    // case uses -- preserves the existing fix's exact "insert relative to
    // this request's own recorded position" behavior for a multi-entry
    // exchange, rather than three separate splices that would each need
    // to account for the prior insertions shifting indices.
    aiHist.splice(myUserIdx+1,0,
      {role:'assistant',content:blocks},
      {role:'user',content:[{type:'tool_result',tool_use_id:toolUse.id,content:toolResultContent}]},
      {role:'assistant',content:finalText}
    );
  }catch(e){thinking.textContent='Could not connect to Claude. Check your connection and try again.';}
  chat.scrollTop=chat.scrollHeight;
}
```

Note: the system-prompt string is duplicated verbatim between the first and second `fetch` calls (both need the anti-fabrication instruction, since Claude's own tool description has no influence on the second call, matching every prior rollout's finding on this exact point). This is intentional duplication, not an oversight — the alternative (a shared local variable) would work equally well and either is acceptable; the plan above inlines it to keep both call sites' bodies fully visible without requiring the reader to trace a variable back to its definition.

- [ ] **Step 2: Syntax-check the modified script block**

Run: `python tools/checkblocks.py sairndesign.html`
Expected: same `TOTAL_BLOCKS` as Task 1's result, `FAILED_BLOCKS:0`.

Run: `python tools/div_balance_check.py sairndesign.html`
Expected: `RESULT:PASS`.

- [ ] **Step 3: Live interaction test — no-tool path unaffected**

Open the app (locally or via the deployed pre-push injection technique used on prior rollouts), ask a question unrelated to any tool ("what's a fair trade markup on custom drapery"). Confirm: exactly one "Thinking..." bubble appears and is replaced by one real answer, no console errors.

- [ ] **Step 4: Commit**

```bash
git add sairndesign.html
git commit -m "feat: SAIRNdesign -- sendAI() tool-use round-trip for get_clients

Sends SDN_TOOLS' definitions on the existing fetch, executes a
requested tool via sdnExecuteTool() (error-safe), sends the result
back via a second fetch (built from this request's own local turn
data, not the shared aiHist) for a final grounded answer. Preserves
the existing 2026-08-09 splice-based aiHist reordering fix: the
tool-use exchange's 3 new entries are spliced in as one atomic group
at the same myUserIdx+1 position the single-entry case already uses,
rather than introducing a different ordering mechanism."
```

---

### Task 3: End-to-end verification, push, live-verify

**Files:** none modified — verification only.

- [ ] **Step 1: Full local re-check of the changed file**

```bash
python tools/checkblocks.py sairndesign.html
python tools/div_balance_check.py sairndesign.html
```

Expected: both checks show 0 failures / PASS.

- [ ] **Step 2: Guardian v2 pass**

Run the full `sairn-guardian-v2` check (Check 0 + numbered checks) against `sairndesign.html` before push, per the project's standing Push Protocol.

- [ ] **Step 3: Real interaction test — client roster question**

With the app running against real seeded data, ask the AI a client question ("who are our clients," "what's Marcus Delgado's company," "which clients are leads vs active"). Confirm the answer contains real names/companies/statuses from `sdn_clients` — not a generic non-answer.

- [ ] **Step 4: No-regression test on the Spec Sheet compliance feature**

Run the Spec Sheet compliance check on a real project and confirm it still produces correct deterministic-findings-plus-AI-review output exactly as before — untouched code, but it shares the same proxy and app_id, so a live spot-check is warranted.

- [ ] **Step 5: Concurrency test (extending the existing fix, not replacing it)**

Send two questions back-to-back before the first resolves — one that triggers `get_clients` and one that doesn't. Inspect `aiHist` afterward: confirm it contains a correctly alternating role sequence with no corruption, regardless of which response arrived first, and that both answers rendered under their own correct message bubble. This is the direct regression test for the concurrency behavior this plan is required to preserve.

- [ ] **Step 6: `sanitizeTools()` regression check for this app_id specifically**

```bash
curl -s -X POST https://sairn.vercel.app/api/claude \
  -H 'Content-Type: application/json' \
  -d '{"app_id":"sairndesign","is_demo":true,"max_tokens":50,"system":"test","messages":[{"role":"user","content":"say hi"}],"tools":[{"name":"get_clients","description":"x","input_schema":{"type":"object","properties":{}}}]}'
```

Expected: HTTP 200 with a real Anthropic response shape (`content` array present), not a 400.

- [ ] **Step 7: Push**

```bash
git push origin main
```

- [ ] **Step 8: Live-verify**

```bash
curl -s https://sairn.vercel.app/sairndesign | grep -c "sdnExecuteTool"
```

Expected: non-zero. Then repeat Steps 3-5's tests against the **live** URL, not just a local/injected copy — per the project's standing rule that a clean push is not proof the live app reflects the change.

- [ ] **Step 9: Update the spec's status line**

Edit `docs/superpowers/specs/2026-08-10-sairndesign-ai-tool-calling-design.md`'s `**Status:**` line to note the foundation and `get_clients` are implemented and live-verified, with the date. Commit this doc-only change separately.
