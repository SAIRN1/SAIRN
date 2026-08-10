# SAIRNlegacy AI Tool-Calling Foundation + get_cases Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give SAIRNlegacy's `sendAI()` (`sairnlegacy.html:1512`) real function-calling access to the real case roster, via one proof tool (`get_cases`), while replacing the existing captured-index `aiHist` splice fix (`sairnlegacy.html:1520-1526`) with the object-identity version *from the start* — not as a follow-up, since the captured-index approach's exact failure mode was just found and fixed live on SAIRNdesign's structurally identical chat.

**Architecture:** `LEG_TOOLS`/`legRegisterTool`/`legExecuteTool` — same registry shape as every other non-real-auth app's dispatcher (no `sensitive` parameter, no real auth exists — `prole` comes from a client-side PIN match). `sendAI()`'s existing fetch gains a `tools` field. If a `tool_use` block comes back, the follow-up fetch is built from this request's own local turn data (not the shared, possibly-mutated `aiHist`), and on success the full 3-entry tool-use exchange is spliced into `aiHist` as one atomic group at `aiHist.indexOf(myUserTurn)+1` — an object-identity lookup, not a captured index, so a concurrent exchange's insertions landing first can't leave the splice position stale.

**Tech Stack:** Vanilla JS (`sairnlegacy.html`, no framework). Verified the same way every prior rollout was: `tools/checkblocks.py` / `tools/div_balance_check.py` on the file, a temporary `node:assert` scratch harness for pure logic, plus a real live-interaction test against the deployed app.

## Global Constraints

- Read-only tool only — `get_cases` may not create, modify, or delete any record. (Spec §2)
- No new persistence — reads `cases()` (`sairnlegacy.html:1377`) directly. (Spec §2)
- `get_cases` returns `{decedent_name, case_number, status, assigned_director, service_type, service_date}` only — `id`, `decedent_dob`, `decedent_dod`, `family_contact_name`, `family_contact_phone`, `family_contact_email`, `notes` all excluded. The family-contact and dob/dod exclusions are a deliberate domain-sensitivity call (grieving families), confirmed with the user — not the same exclusion set as prior roster tools (`get_customers`, `get_clients`). (Spec §1, §4)
- No `sensitive`/role parameter anywhere in this dispatcher — no real auth backend exists. (Spec §1, §3)
- **Concurrency fix is object-identity-based from the very first implementation, not a captured index.** `var myUserTurn={role:'user',content:q}; aiHist.push(myUserTurn);` and splice at `aiHist.indexOf(myUserTurn)+1`, for both the no-tool-use single-entry case and the tool-use 3-entry atomic-group case. This is the baseline implementation here, not a hardening step added later. (Spec §0, §1, §3)
- `generateObituary()` (`sairnlegacy.html:2438`) is not touched — already real, correct, dual-guarded. (Spec §2)
- No changes to `api/claude.js` — `sanitizeTools()` already passes custom tools through for `sairnlegacy`. (Spec §2)
- `python tools/checkblocks.py sairnlegacy.html` and `python tools/div_balance_check.py sairnlegacy.html` must stay clean (0 failed / PASS) after every change.
- Before push: full Guardian v2 check on `sairnlegacy.html`. After push: live-verify against `sairn.vercel.app/sairnlegacy` directly, not assumed from a clean push (project Push Protocol).

---

### Task 1: `sairnlegacy.html` — tool registry, dispatcher, and the `get_cases` tool

**Files:**
- Modify: `sairnlegacy.html` (insert immediately before `function clrAI(){...}` at `sairnlegacy.html:1510`, i.e. right after the `// ── AI ASSISTANT ──` comment)

**Interfaces:**
- Consumes: `cases()` (`sairnlegacy.html:1377`, existing).
- Produces: `LEG_TOOLS` (object, tool name → `{definition, run}` — no `sensitive` field), `legExecuteTool(name, input)` → `{ok: true, result: any} | {ok: false, error: string}` — used by Task 2.

- [ ] **Step 1: Write the implementation**

Insert immediately after the `// ── AI ASSISTANT ──...` comment (`sairnlegacy.html:1509`), before `function clrAI(){...}`:

```js
// AI tool-calling dispatcher (2026-08-10) -- ports the mechanism proven
// live on every other SAIRN app. Registry of read-only tools sendAI()
// may request via Claude's tool-use. Every tool is:
//   - read-only (never creates/modifies/deletes anything)
//   - wrapped so a thrown error or unexpected data shape becomes an honest
//     {ok:false} result, never a crash or a silently wrong answer
// No sensitivity/role-gate concept here -- SAIRNlegacy has no real,
// server-verified auth (prole comes from a client-side PIN match), same
// reasoning already applied to every prior non-real-auth dispatcher.
// See docs/superpowers/specs/2026-08-10-sairnlegacy-ai-tool-calling-design.md
var LEG_TOOLS = {};

function legRegisterTool(name, description, inputSchema, run) {
  LEG_TOOLS[name] = {
    definition: { name: name, description: description, input_schema: inputSchema },
    run: run
  };
}

function legExecuteTool(name, input) {
  var tool = LEG_TOOLS[name];
  if (!tool) return { ok: false, error: 'No tool named "' + name + '" exists.' };
  try {
    return { ok: true, result: tool.run(input || {}) };
  } catch (e) {
    return { ok: false, error: 'Could not retrieve that data right now.' };
  }
}

legRegisterTool(
  'get_cases',
  'Look up the current case roster: decedent name, case number, status, assigned director, service type, and service date. Does NOT include family contact information (name, phone, or email), decedent birth/death dates, or case notes -- none of that is available to this tool.',
  { type: 'object', properties: {}, required: [] },
  function (input) {
    // input intentionally unused -- this tool takes no real arguments, but
    // accepts one for interface consistency with legExecuteTool(name, input),
    // matching every prior tool's convention.
    return cases().map(function (c) {
      return {
        decedent_name: c.decedent_name,
        case_number: c.case_number,
        status: c.status,
        assigned_director: c.assigned_director,
        service_type: c.service_type,
        service_date: c.service_date
      };
    });
  }
);
```

- [ ] **Step 2: Syntax-check the modified script block**

Run: `python tools/checkblocks.py sairnlegacy.html`
Expected: same `TOTAL_BLOCKS` as the pre-change baseline (run it once before this edit if you don't already know the number), `FAILED_BLOCKS:0`.

Run: `python tools/div_balance_check.py sairnlegacy.html`
Expected: `RESULT:PASS`.

- [ ] **Step 3: Behavioral verification with a temporary Node harness**

Both the dispatcher and the tool's `run()` have no DOM dependency. Create a scratch file (not committed — delete after this step):

```js
// scratch verification, delete after running
var assert = require('assert');

var LEG_TOOLS = {};
function legRegisterTool(name, description, inputSchema, run) {
  LEG_TOOLS[name] = { definition: { name: name, description: description, input_schema: inputSchema }, run: run };
}
function legExecuteTool(name, input) {
  var tool = LEG_TOOLS[name];
  if (!tool) return { ok: false, error: 'No tool named "' + name + '" exists.' };
  try { return { ok: true, result: tool.run(input || {}) }; } catch (e) { return { ok: false, error: 'Could not retrieve that data right now.' }; }
}

// -- dispatcher checks --
legRegisterTool('ping', 'test tool', {type:'object'}, function () { return 'pong'; });
legRegisterTool('broken', 'test throwing tool', {type:'object'}, function () { throw new Error('boom'); });
assert.deepStrictEqual(legExecuteTool('ping', {}), { ok: true, result: 'pong' });
assert.deepStrictEqual(legExecuteTool('nonexistent', {}), { ok: false, error: 'No tool named "nonexistent" exists.' });
assert.strictEqual(legExecuteTool('broken', {}).ok, false);
console.log('legExecuteTool: all 3 checks passed');

// -- get_cases tool check, stubbing cases() --
function cases() {
  return [
    { id: 'CS-1', decedent_name: 'Robert Halloway', case_number: 'FH-2026-001', decedent_dob: '1948-03-11', decedent_dod: '2026-08-04',
      family_contact_name: 'Diane Halloway', family_contact_phone: '(440) 555-0110', family_contact_email: 'diane.halloway@example.com',
      assigned_director: 'Maria Chen', status: 'Arrangement', service_type: 'Burial', service_date: '2026-08-10', notes: '' },
    { id: 'CS-2', decedent_name: 'Eleanor Voss', case_number: 'FH-2026-002', decedent_dob: '1955-11-02', decedent_dod: '2026-08-06',
      family_contact_name: 'Mark Voss', family_contact_phone: '(440) 555-0121', family_contact_email: 'mark.voss@example.com',
      assigned_director: 'James Okoye', status: 'First Call', service_type: '', service_date: '', notes: 'Family requested callback this evening' }
  ];
}

legRegisterTool('get_cases', 'x', { type: 'object' }, function (input) {
  return cases().map(function (c) {
    return { decedent_name: c.decedent_name, case_number: c.case_number, status: c.status, assigned_director: c.assigned_director, service_type: c.service_type, service_date: c.service_date };
  });
});

var out = LEG_TOOLS.get_cases.run({});
assert.strictEqual(out.length, 2);
assert.strictEqual(out[0].decedent_name, 'Robert Halloway');
assert.strictEqual(out[1].assigned_director, 'James Okoye');
assert.strictEqual(out[0].id, undefined, 'id must never appear in get_cases output');
assert.strictEqual(out[0].decedent_dob, undefined, 'decedent_dob must never appear in get_cases output');
assert.strictEqual(out[0].decedent_dod, undefined, 'decedent_dod must never appear in get_cases output');
assert.strictEqual(out[0].family_contact_name, undefined, 'family_contact_name must never appear in get_cases output');
assert.strictEqual(out[0].family_contact_phone, undefined, 'family_contact_phone must never appear in get_cases output');
assert.strictEqual(out[0].family_contact_email, undefined, 'family_contact_email must never appear in get_cases output');
assert.strictEqual(out[1].notes, undefined, 'notes must never appear in get_cases output');
console.log('get_cases tool: all 7 checks passed');
```

Run: `node <scratch-file>.js`
Expected: `legExecuteTool: all 3 checks passed` then `get_cases tool: all 7 checks passed`. Delete the scratch file afterward.

- [ ] **Step 4: Commit**

```bash
git add sairnlegacy.html
git commit -m "feat: SAIRNlegacy -- tool-calling dispatcher + get_cases proof tool

Ports the mechanism proven live on every other SAIRN app, minus the
sensitivity/role-gate concept -- SAIRNlegacy has no real, server-
verified auth (prole comes from a client-side PIN match), same
reasoning already applied to every prior non-real-auth dispatcher.
LEG_TOOLS/legRegisterTool/legExecuteTool plus one read-only tool,
get_cases (decedent_name/case_number/status/assigned_director/
service_type/service_date). id/decedent_dob/decedent_dod/family
contact fields/notes deliberately excluded -- grieving-family data
sensitivity, confirmed with the user, not the same exclusion set as
prior roster tools. sendAI() doesn't call any of this yet -- verified
standalone via a Node harness."
```

---

### Task 2: `sairnlegacy.html` — `sendAI()` tool-use round-trip, object-identity splice fix from the start

**Files:**
- Modify: `sairnlegacy.html:1512-1543` (`sendAI()`)

**Interfaces:**
- Consumes: `legExecuteTool(name, input)` (Task 1), `LEG_TOOLS` (Task 1, read via `Object.keys(LEG_TOOLS).map(k => LEG_TOOLS[k].definition)`), `PROXY`, `APP_ID`, `legAiError(data)`, `H(s)`, `aiHist` (all existing, unmodified).
- Produces: no new exports — `sendAI()` keeps its existing signature and call site (`askAI(q)`, `sairnlegacy.html:1511`).

- [ ] **Step 1: Write the implementation**

Replace `sendAI()` (`sairnlegacy.html:1512-1543`) with:

```js
async function sendAI(){
  var inp=$('ainp'),q=(inp.value||'').trim();
  if(!q)return;
  inp.value='';
  var chat=$('achat');
  if(chat.querySelector('div[style*="text-align:center"]'))chat.innerHTML='';
  chat.innerHTML+='<div class="amu">'+H(q)+'</div>';
  chat.scrollTop=chat.scrollHeight;
  // 2026-08-10: object-identity splice fix, ported from the start rather
  // than discovered live -- the prior captured-index approach
  // (var myUserIdx=aiHist.length) goes stale once a concurrent exchange's
  // insertions land first and shift the array, which this tool-use
  // round-trip's longer duration makes far more likely to manifest
  // (found and fixed on SAIRNdesign's structurally identical chat,
  // docs/superpowers/specs/2026-08-10-sairndesign-ai-tool-calling-design.md).
  // Recording the turn object itself and looking up its live index at
  // splice time keeps aiHist correctly ordered regardless of resolve
  // order or how many other exchanges have inserted ahead of it.
  var myUserTurn={role:'user',content:q};
  aiHist.push(myUserTurn);
  var thinking=document.createElement('div');thinking.className='ama';thinking.textContent='Thinking...';chat.appendChild(thinking);
  chat.scrollTop=chat.scrollHeight;
  var toolDefs=Object.keys(LEG_TOOLS).map(function(k){return LEG_TOOLS[k].definition;});
  try{
    var res=await fetch(PROXY,{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({app_id:APP_ID,is_demo:true,max_tokens:500,
        system:'You are an operations assistant for a funeral home (case intake, family communication, documents, merchandise, and permit workflow). Be concise, practical, and compassionate in tone -- families reading drafted messages are grieving. Never provide your own estimate, guess, or general-knowledge substitute for any fact a tool would have provided -- if a tool errors, is denied, or a question calls for data you have not actually retrieved via a tool this turn, say so plainly and stop.',
        messages:aiHist.map(function(m){return {role:m.role,content:m.content};}),
        tools:toolDefs})});
    var data=await res.json();
    var aiErr=legAiError(data);
    if(aiErr){thinking.textContent=aiErr;chat.scrollTop=chat.scrollHeight;return;}
    var blocks=(data&&data.content)||[];
    var toolUse=blocks.filter(function(b){return b.type==='tool_use';})[0];
    if(!toolUse){
      var text=(blocks[0]&&blocks[0].text)||'No response text returned.';
      thinking.textContent=text;
      aiHist.splice(aiHist.indexOf(myUserTurn)+1,0,{role:'assistant',content:text});
      chat.scrollTop=chat.scrollHeight;
      return;
    }
    var outcome=legExecuteTool(toolUse.name,toolUse.input);
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
        system:'You are an operations assistant for a funeral home (case intake, family communication, documents, merchandise, and permit workflow). Be concise, practical, and compassionate in tone -- families reading drafted messages are grieving. Never provide your own estimate, guess, or general-knowledge substitute for any fact a tool would have provided -- if a tool errors, is denied, or a question calls for data you have not actually retrieved via a tool this turn, say so plainly and stop.',
        messages:followUpMessages})});
    var data2=await res2.json();
    var aiErr2=legAiError(data2);
    if(aiErr2){thinking.textContent=aiErr2;chat.scrollTop=chat.scrollHeight;return;}
    var finalText=(data2.content&&data2.content[0]&&data2.content[0].text)||'No response text returned.';
    thinking.textContent=finalText;
    // Atomic 3-entry splice at the turn object's live index -- preserves
    // correct ordering for a multi-entry exchange the same way the
    // single-entry case above does, rather than three separate splices
    // that would each need to account for prior insertions shifting
    // indices.
    aiHist.splice(aiHist.indexOf(myUserTurn)+1,0,
      {role:'assistant',content:blocks},
      {role:'user',content:[{type:'tool_result',tool_use_id:toolUse.id,content:toolResultContent}]},
      {role:'assistant',content:finalText}
    );
  }catch(e){thinking.textContent='Could not connect to Claude. Check your connection and try again.';}
  chat.scrollTop=chat.scrollHeight;
}
```

Note: the system-prompt string is duplicated verbatim between the first and second `fetch` calls (both need the anti-fabrication instruction, since Claude's own tool description has no influence on the second call, matching every prior rollout's finding on this exact point). This is intentional duplication, not an oversight.

- [ ] **Step 2: Syntax-check the modified script block**

Run: `python tools/checkblocks.py sairnlegacy.html`
Expected: same `TOTAL_BLOCKS` as Task 1's result, `FAILED_BLOCKS:0`.

Run: `python tools/div_balance_check.py sairnlegacy.html`
Expected: `RESULT:PASS`.

- [ ] **Step 3: Live interaction test — no-tool path unaffected**

Open the app (locally or via the deployed pre-push injection technique used on prior rollouts), ask a question unrelated to any tool ("what's a compassionate way to phrase a first-call callback message"). Confirm: exactly one "Thinking..." bubble appears and is replaced by one real answer, no console errors.

- [ ] **Step 4: Commit**

```bash
git add sairnlegacy.html
git commit -m "feat: SAIRNlegacy -- sendAI() tool-use round-trip for get_cases

Sends LEG_TOOLS' definitions on the existing fetch, executes a
requested tool via legExecuteTool() (error-safe), sends the result
back via a second fetch (built from this request's own local turn
data, not the shared aiHist) for a final grounded answer. Replaces
the prior captured-index aiHist splice with an object-identity
approach (aiHist.indexOf(myUserTurn)+1) from this first
implementation -- not a follow-up fix -- since the captured-index
version's exact failure mode was just found and fixed live on
SAIRNdesign's structurally identical chat."
```

---

### Task 3: End-to-end verification, push, live-verify

**Files:** none modified — verification only.

- [ ] **Step 1: Full local re-check of the changed file**

```bash
python tools/checkblocks.py sairnlegacy.html
python tools/div_balance_check.py sairnlegacy.html
```

Expected: both checks show 0 failures / PASS.

- [ ] **Step 2: Guardian v2 pass**

Run the full `sairn-guardian-v2` check (Check 0 + numbered checks) against `sairnlegacy.html` before push, per the project's standing Push Protocol.

- [ ] **Step 3: Real interaction test — case roster questions**

With the app running against real seeded data, ask the AI a case question ("which cases are open," "who is assigned to the Halloway case," "what's the status of Eleanor Voss's case"). Confirm the answer contains real decedent names/case numbers/statuses/directors from `leg_cases` — not a generic non-answer — and confirm no family contact info or decedent dates ever appear in the answer, even when not explicitly asked to exclude them.

- [ ] **Step 4: No-regression test on the obituary generator**

Run `generateObituary()` on a real case and confirm it still produces a correct, real-data-grounded draft exactly as before — untouched code, but it shares the same proxy and app_id, so a live spot-check is warranted.

- [ ] **Step 5: Concurrency test (object-identity fix, verified from the start)**

Send two questions back-to-back before the first resolves — one that triggers `get_cases` (longer round-trip) and one that doesn't. Inspect `aiHist` afterward: confirm it contains a correctly alternating role sequence with no corruption, regardless of which response arrived first, and that both answers rendered under their own correct message bubble. This is the exact scenario that broke SAIRNdesign's captured-index approach, so it must be verified here as a pass, not assumed safe from code review alone.

- [ ] **Step 6: `sanitizeTools()` regression check for this app_id specifically**

```bash
curl -s -X POST https://sairn.vercel.app/api/claude \
  -H 'Content-Type: application/json' \
  -d '{"app_id":"sairnlegacy","is_demo":true,"max_tokens":50,"system":"test","messages":[{"role":"user","content":"say hi"}],"tools":[{"name":"get_cases","description":"x","input_schema":{"type":"object","properties":{}}}]}'
```

Expected: HTTP 200 with a real Anthropic response shape (`content` array present), not a 400.

- [ ] **Step 7: Push**

```bash
git push origin main
```

- [ ] **Step 8: Live-verify**

```bash
curl -s https://sairn.vercel.app/sairnlegacy | grep -c "legExecuteTool"
```

Expected: non-zero. Then repeat Steps 3-5's tests against the **live** URL, not just a local/injected copy — per the project's standing rule that a clean push is not proof the live app reflects the change.

- [ ] **Step 9: Update the spec's status line**

Edit `docs/superpowers/specs/2026-08-10-sairnlegacy-ai-tool-calling-design.md`'s `**Status:**` line to note the foundation and `get_cases` are implemented and live-verified, with the date. Commit this doc-only change separately.
