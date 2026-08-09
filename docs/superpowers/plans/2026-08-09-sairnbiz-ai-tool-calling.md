# SAIRNbiz AI Tool-Calling Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give SAIRNbiz's AI Assistant (`callAI()`, `sairnbiz.html:1488`) real function-calling access to the app's own data, starting with one proof tool (`get_employees`), so every later feature (payroll/P&L copilot, pre-payroll validation, cross-domain digest, hiring cost-impact, review narratives) can add a tool to the same mechanism instead of rebuilding it.

**Architecture:** Multi-turn tool-calling through the existing shared proxy (`api/claude.js`). The proxy's `sanitizeTools()` currently strips any tool that isn't Anthropic's server-executed `web_search_20250305`; it needs to allow custom (client-executed) tool definitions through unmodified, since those carry none of the cost/abuse risk the existing whitelist defends against. On the client, `callAI()` sends a `tools` array; if Claude responds with a `tool_use` block, a new dispatcher (`sbExecuteTool()`) looks it up, checks role-sensitivity, executes the matching local getter, and sends a `tool_result` back for the final answer — one round-trip, not an open-ended tool loop.

**Tech Stack:** Vanilla JS (`sairnbiz.html`, no framework), Node.js serverless function (`api/claude.js`, Vercel), Anthropic Messages API (`claude-sonnet-4-6`) via the existing `sairn.vercel.app/api/claude` proxy. Tests use this repo's existing zero-dependency `node:assert` convention (see `api/_lib/auth.test.js`) for the server-side change; the client-side change is verified the way every other `sairnbiz.html` change in this project is verified — `node --check` on the extracted script block, plus a real live-interaction test against the deployed app, not a browser test runner (none exists in this repo).

## Global Constraints

- Read-only tools only — no tool in this pass may create, modify, or delete any record. (Spec §2)
- No new persistence — tool results are computed live from existing `localStorage` via existing getters (`ld('sb_emps', [])`, etc.). (Spec §2)
- v1 ships exactly one tool, `get_employees`, excluding compensation fields even though it's non-sensitive data otherwise — payroll tools are a later spec's scope. (Spec §5)
- Single round-trip only: the follow-up call after a `tool_result` does not re-send `tools` and does not expect another `tool_use`. (Spec §4 step 3)
- No change to `KNOWN_APP_IDS` or the demo daily-call-limit logic in `api/claude.js`. (Spec §2)
- Every modified script block in `sairnbiz.html` must pass `node --check` before commit (project standing rule, `CLAUDE.md`).
- `python tools/checkblocks.py sairnbiz.html` and `python tools/div_balance_check.py sairnbiz.html` must stay clean (0 failed / PASS) after every `sairnbiz.html` change.
- Before push: full Guardian v2 check on changed files. After push: live-verify the specific change against `sairn.vercel.app` directly, not assumed from a clean push (project Push Protocol).
- One "Thinking..." placeholder spans the entire exchange including the tool round-trip, removed by the DOM-node reference `addMsg()` already returns — must not reintroduce the placeholder-by-DOM-position race fixed earlier this session in this function's siblings. (Spec §4)

---

### Task 1: `api/claude.js` — allow custom tools through `sanitizeTools()`

**Files:**
- Modify: `api/claude.js:37-56` (`ALLOWED_TOOL_TYPES`, `sanitizeTools`), `api/claude.js:67` (export the handler by name so `sanitizeTools` can be attached and required by the test)
- Create: `api/claude.test.js`

**Interfaces:**
- Produces: `sanitizeTools(tools)` — exported as a property on the module's default export (`require('./claude.js').sanitizeTools`), same shape/behavior as today for `web_search_20250305` entries, now also passes through entries shaped like `{name, description, input_schema}` (Anthropic custom-tool schema, no `type` field, or `type` omitted) unmodified.

- [ ] **Step 1: Write the failing test**

Create `api/claude.test.js`:

```js
// api/claude.test.js
// ---------------------------------------------------------------------------
// Plain node:assert tests — no test framework, matching api/'s existing
// zero-npm-dependency convention (see api/_lib/auth.test.js).
// Run: node api/claude.test.js
//
// WHY THIS EXISTS: sanitizeTools() is a security boundary (the file's own
// comment: "this endpoint has no other auth beyond a client-supplied
// app_id"). Confirms the existing web_search allowlist/cap behavior is
// unchanged, and that a custom client-executed tool (no cost/abuse risk —
// Anthropic never runs it, the browser does) now survives sanitization,
// before any app is wired to send one.
// ---------------------------------------------------------------------------

const assert = require('assert');
const { sanitizeTools } = require('./claude.js');

let passed = 0;
function test(name, fn) {
  try {
    fn();
    passed++;
    console.log('  ok - ' + name);
  } catch (err) {
    console.error('  FAIL - ' + name);
    console.error('    ' + err.message);
    process.exitCode = 1;
  }
}

console.log('api/claude.js sanitizeTools()');

test('non-array input returns undefined', () => {
  assert.strictEqual(sanitizeTools(null), undefined);
  assert.strictEqual(sanitizeTools('not an array'), undefined);
});

test('empty array returns undefined', () => {
  assert.strictEqual(sanitizeTools([]), undefined);
});

test('web_search_20250305 passes through with default name and capped max_uses', () => {
  const out = sanitizeTools([{ type: 'web_search_20250305' }]);
  assert.strictEqual(out.length, 1);
  assert.strictEqual(out[0].type, 'web_search_20250305');
  assert.strictEqual(out[0].name, 'web_search');
  assert.strictEqual(out[0].max_uses, 5);
});

test('web_search_20250305 max_uses is capped at 5 even if the client asks for more', () => {
  const out = sanitizeTools([{ type: 'web_search_20250305', max_uses: 999 }]);
  assert.strictEqual(out[0].max_uses, 5);
});

test('an unknown server-tool type is still stripped', () => {
  const out = sanitizeTools([{ type: 'some_future_billed_tool' }]);
  assert.strictEqual(out, undefined);
});

test('a custom client tool (no type field) passes through unmodified', () => {
  const customTool = {
    name: 'get_employees',
    description: 'Look up the current employee roster.',
    input_schema: { type: 'object', properties: {}, required: [] }
  };
  const out = sanitizeTools([customTool]);
  assert.strictEqual(out.length, 1);
  assert.deepStrictEqual(out[0], customTool);
});

test('a custom client tool with type:"custom" passes through unmodified', () => {
  const customTool = {
    type: 'custom',
    name: 'get_employees',
    description: 'Look up the current employee roster.',
    input_schema: { type: 'object', properties: {}, required: [] }
  };
  const out = sanitizeTools([customTool]);
  assert.strictEqual(out.length, 1);
  assert.deepStrictEqual(out[0], customTool);
});

test('a mix of one allowed server tool and one custom tool both survive', () => {
  const out = sanitizeTools([
    { type: 'web_search_20250305' },
    { name: 'get_employees', description: 'x', input_schema: { type: 'object' } }
  ]);
  assert.strictEqual(out.length, 2);
});

console.log(passed + ' passed');
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node api/claude.test.js`
Expected: `TypeError: (0 , _claude.sanitizeTools) is not a function` (or similar) — `sanitizeTools` is not exported yet, and even once it is, the custom-tool tests fail because `ALLOWED_TOOL_TYPES` doesn't recognize them.

- [ ] **Step 3: Implement — export `sanitizeTools` and allow custom tools**

In `api/claude.js`, replace the `ALLOWED_TOOL_TYPES` constant and `sanitizeTools` function (lines 42-56):

```js
// Server tools a frontend is allowed to request. Server-executed tool TYPES
// are whitelisted by exact type string (not passed through unchecked)
// because this endpoint has no other auth beyond a client-supplied app_id --
// an unrestricted server-tool passthrough would let any caller run billed
// actions (web search) against our Anthropic key. max_uses is also
// server-capped below regardless of what the client sends.
//
// CUSTOM (client-executed) tools are a different risk category, added
// 2026-08-09: Anthropic never executes them -- the model only returns a
// tool_use request naming the tool + arguments, and the calling app decides
// locally whether and how to run it. No cost or external call happens from
// the tool definition alone, so these pass through unmodified rather than
// being type-whitelisted like server tools. A tool counts as "custom" if it
// has no `type` field, or an explicit `type: 'custom'` -- both are valid
// Anthropic custom-tool shapes.
const ALLOWED_SERVER_TOOL_TYPES = ['web_search_20250305'];
const MAX_TOOL_USES_CEILING = 5;

function sanitizeTools(tools) {
  if (!Array.isArray(tools)) return undefined;
  const clean = tools
    .filter((t) => t && (t.type === undefined || t.type === 'custom' || ALLOWED_SERVER_TOOL_TYPES.includes(t.type)))
    .map((t) => {
      if (t.type === undefined || t.type === 'custom') return t;
      const out = { type: t.type, name: t.name || 'web_search' };
      const requested = Number(t.max_uses) || MAX_TOOL_USES_CEILING;
      out.max_uses = Math.max(1, Math.min(requested, MAX_TOOL_USES_CEILING));
      return out;
    });
  return clean.length ? clean : undefined;
}
```

Then change the handler from an anonymous export to a named one so `sanitizeTools` can be attached and the file stays requirable by the test. Replace `module.exports = async (req, res) => {` (line 67) with:

```js
async function claudeProxyHandler(req, res) {
```

...leave the entire function body (lines 68-142) unchanged...

...and replace the final closing `};` (line 143) with:

```js
}

claudeProxyHandler.sanitizeTools = sanitizeTools;
module.exports = claudeProxyHandler;
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node api/claude.test.js`
Expected: 8 `ok -` lines, `8 passed`, exit code 0.

- [ ] **Step 5: Verify no behavior change for Vercel routing**

Run: `node --check api/claude.js`
Expected: no output (valid syntax). `module.exports` is still a callable async function (Vercel invokes it the same way whether it's a named function or an anonymous arrow) — the only externally visible change is the added `.sanitizeTools` property, which Vercel's routing ignores.

- [ ] **Step 6: Commit**

```bash
git add api/claude.js api/claude.test.js
git commit -m "feat: api/claude.js -- allow custom client tools through sanitizeTools()

Server-executed tool TYPES stay whitelisted (web_search_20250305 only,
capped at 5 uses) for the cost/abuse reason already documented here.
Custom client-executed tools (no type, or type:'custom') now pass
through unmodified -- Anthropic never runs them, so they carry none of
that risk. Exported sanitizeTools for testing; added api/claude.test.js
following the api/_lib/auth.test.js zero-dependency node:assert pattern.
Enables SAIRNbiz's AI tool-calling foundation (see
docs/superpowers/specs/2026-08-09-sairnbiz-ai-tool-calling-design.md);
this is shared-proxy infrastructure, so every app gains the capability."
```

---

### Task 2: `sairnbiz.html` — tool registry and dispatcher

**Files:**
- Modify: `sairnbiz.html` (insert after the `ld()`/`st()` helpers, ~line 866; the `<script>` block containing lines 831-2000+, exact line to be confirmed at edit time since Task 1 doesn't touch this file)

**Interfaces:**
- Consumes: `ld(k, d)` (`sairnbiz.html:866`) — existing localStorage getter, `prole` (`sairnbiz.html:862`) — existing global holding the logged-in role string.
- Produces: `SB_TOOLS` (object, tool name → `{definition, sensitive, run}`), `sbExecuteTool(name, role)` → `{ok: true, result: any} | {ok: false, error: string}` — used by Task 3.

- [ ] **Step 1: Write the implementation**

Insert immediately after `function ld(k,d){...}` (`sairnbiz.html:866`):

```js
// AI tool-calling dispatcher (2026-08-09) -- registry of read-only tools
// callAI() may request via Claude's tool-use. Every tool is:
//   - read-only (never creates/modifies/deletes anything)
//   - wrapped so a thrown error or unexpected data shape becomes an honest
//     {ok:false} result, never a crash or a silently wrong answer
//   - checked against the CALLING role before running, if marked sensitive
// See docs/superpowers/specs/2026-08-09-sairnbiz-ai-tool-calling-design.md
var SB_TOOLS = {};

function sbRegisterTool(name, description, inputSchema, sensitive, run) {
  SB_TOOLS[name] = {
    definition: { name: name, description: description, input_schema: inputSchema },
    sensitive: !!sensitive,
    run: run
  };
}

// This is the first role-based access check anywhere in SAIRNbiz's client
// code -- prole is real (server-issued via SB_AUTH_API) but nothing has
// ever branched on it before now. New pattern, not an established one.
function sbExecuteTool(name, role) {
  var tool = SB_TOOLS[name];
  if (!tool) return { ok: false, error: 'No tool named "' + name + '" exists.' };
  if (tool.sensitive && role !== 'owner') {
    return { ok: false, error: 'This data is restricted to the owner role.' };
  }
  try {
    return { ok: true, result: tool.run() };
  } catch (e) {
    return { ok: false, error: 'Could not retrieve that data right now.' };
  }
}
```

- [ ] **Step 2: Syntax-check the modified script block**

Run: `python tools/checkblocks.py sairnbiz.html`
Expected: `TOTAL_BLOCKS:2` / `FAILED_BLOCKS:0` (unchanged from baseline — confirm no regression, not just that this block is new).

- [ ] **Step 3: Behavioral verification with a temporary Node harness**

The dispatcher has no DOM dependency, so its real logic (not just syntax) can be checked with plain `node:assert` by stubbing `ld`/`prole`. Create a scratch file (not committed — delete after this step, same as any other verification script per project convention):

```js
// scratch verification, delete after running
var prole, SB_TOOLS = {};
function sbRegisterTool(name, description, inputSchema, sensitive, run) {
  SB_TOOLS[name] = { definition: { name: name, description: description, input_schema: inputSchema }, sensitive: !!sensitive, run: run };
}
function sbExecuteTool(name, role) {
  var tool = SB_TOOLS[name];
  if (!tool) return { ok: false, error: 'No tool named "' + name + '" exists.' };
  if (tool.sensitive && role !== 'owner') return { ok: false, error: 'This data is restricted to the owner role.' };
  try { return { ok: true, result: tool.run() }; } catch (e) { return { ok: false, error: 'Could not retrieve that data right now.' }; }
}

var assert = require('assert');

sbRegisterTool('ping', 'test tool', {type:'object'}, false, function () { return 'pong'; });
sbRegisterTool('secret', 'test sensitive tool', {type:'object'}, true, function () { return 'classified'; });
sbRegisterTool('broken', 'test throwing tool', {type:'object'}, false, function () { throw new Error('boom'); });

assert.deepStrictEqual(sbExecuteTool('ping', 'employee'), { ok: true, result: 'pong' });
assert.deepStrictEqual(sbExecuteTool('nonexistent', 'owner'), { ok: false, error: 'No tool named "nonexistent" exists.' });
assert.deepStrictEqual(sbExecuteTool('secret', 'employee'), { ok: false, error: 'This data is restricted to the owner role.' });
assert.deepStrictEqual(sbExecuteTool('secret', 'manager'), { ok: false, error: 'This data is restricted to the owner role.' });
assert.deepStrictEqual(sbExecuteTool('secret', 'owner'), { ok: true, result: 'classified' });
assert.strictEqual(sbExecuteTool('broken', 'owner').ok, false);

console.log('sbExecuteTool: all 6 checks passed');
```

Run: `node <scratch-file>.js`
Expected: `sbExecuteTool: all 6 checks passed`. Delete the scratch file afterward.

- [ ] **Step 4: Commit**

```bash
git add sairnbiz.html
git commit -m "feat: SAIRNbiz -- tool-calling dispatcher (SB_TOOLS/sbExecuteTool)

Registry + role-gated, error-safe execution for read-only AI tools.
No real tools registered yet (Task 4) and callAI() doesn't call this
yet (Task 3) -- this is the isolated mechanism, verified standalone."
```

---

### Task 3: `sairnbiz.html` — rewire `callAI()` for the tool-use round-trip

**Files:**
- Modify: `sairnbiz.html:1488-1505` (`callAI()`)

**Interfaces:**
- Consumes: `sbExecuteTool(name, role)` (Task 2), `SB_TOOLS` (Task 2, read via `Object.keys(SB_TOOLS).map(k => SB_TOOLS[k].definition)` to build the `tools` array), `addMsg(t, role)` (`sairnbiz.html:1487`, already returns its DOM node), `PROXY`, `APP_ID`, `prole`, `aiHist` (all existing globals).
- Produces: no new exports — `callAI(msg)` keeps its existing signature and call sites (`sendAI()`, `sairnbiz.html:1484`).

- [ ] **Step 1: Write the implementation**

Replace `callAI()` (`sairnbiz.html:1488-1505`) with:

```js
function callAI(msg){
  var emps=ld('sb_emps',[]);
  var ctx='You are the AI business operations assistant for SAIRNbiz, used by Pinnacle Stone & Design in Westlake, OH. They have '+emps.length+' employees, operate a stone fabrication shop, and use SAIRNbiz for HR and accounting. Be concise, practical, and industry-specific. No fluff. If you use a tool and it returns an error or "not authorized," say so plainly instead of guessing an answer.';
  var sharedCtx=(typeof buildSbSharedCompanyContext==='function')?buildSbSharedCompanyContext():'';
  if(sharedCtx)ctx+='\n\n'+sharedCtx;
  if(typeof recordSbSharedTopics==='function')recordSbSharedTopics(msg);
  aiHist.push({role:'user',content:msg});
  var toolDefs=Object.keys(SB_TOOLS).map(function(k){return SB_TOOLS[k].definition;});
  // One placeholder spans the whole exchange, including the extra
  // tool-result round-trip -- same placeholder-by-reference fix already
  // applied to this function's siblings in sairngrounds.html/sairnscape.html
  // this session; must not regress to "remove the last .ama in the DOM".
  var thinkingEl=addMsg('Thinking...','a');
  function finish(replyText){
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
    var outcome=sbExecuteTool(toolUse.name,prole);
    var toolResultContent=outcome.ok?JSON.stringify(outcome.result):('Error: '+outcome.error);
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
    if(thinkingEl&&thinkingEl.parentNode)thinkingEl.remove();
    addMsg('Connection error.','a');
  });
}
```

- [ ] **Step 2: Syntax-check the modified script block**

Run: `python tools/checkblocks.py sairnbiz.html`
Expected: `TOTAL_BLOCKS:2` / `FAILED_BLOCKS:0`.

Run: `python tools/div_balance_check.py sairnbiz.html`
Expected: `RESULT:PASS`.

- [ ] **Step 3: Live interaction test (no real tool exists yet — verify the no-tool path is unaffected)**

Deploy is not yet pushed at this point in the plan (Task 5 handles push + live-verify for the whole feature). For this task, verify locally: open `sairnbiz.html` in a browser (or via the project's existing local-serve method), log in, ask the AI Assistant a question unrelated to any tool ("what's the best way to price a granite countertop job" or similar). Confirm: exactly one "Thinking..." bubble appears and is replaced by one real answer, no console errors, `tools:toolDefs` sent as `tools:[]` today (safe — `sanitizeTools([])` returns `undefined` per Task 1's test, so this is identical to today's no-`tools` behavior).

- [ ] **Step 4: Commit**

```bash
git add sairnbiz.html
git commit -m "feat: SAIRNbiz -- callAI() supports the tool-use round-trip

Sends SB_TOOLS' definitions, executes a requested tool via
sbExecuteTool() (role-gated, error-safe), sends the result back for a
final grounded answer. No real tools registered yet (Task 4) so this
is currently a no-op passthrough to today's behavior, verified live."
```

---

### Task 4: `sairnbiz.html` — the `get_employees` tool

**Files:**
- Modify: `sairnbiz.html` (immediately after the `SB_TOOLS`/`sbExecuteTool` block from Task 2)

**Interfaces:**
- Consumes: `sbRegisterTool(name, description, inputSchema, sensitive, run)` (Task 2), `ld('sb_emps', [])` (existing).
- Produces: nothing new consumed elsewhere — this is the leaf registration.

- [ ] **Step 1: Write the implementation**

Insert after the `sbExecuteTool` function from Task 2:

```js
sbRegisterTool(
  'get_employees',
  'Look up the current employee roster: name, role, department, employment type, start date, and status. Does NOT include pay rate or any compensation figures.',
  { type: 'object', properties: {}, required: [] },
  false,
  function () {
    return ld('sb_emps', []).map(function (e) {
      return { name: (e.fn || '') + ' ' + (e.ln || ''), role: e.role, dept: e.dept, type: e.type, start: e.start, status: e.status };
    });
  }
);
```

- [ ] **Step 2: Syntax-check**

Run: `python tools/checkblocks.py sairnbiz.html`
Expected: `TOTAL_BLOCKS:2` / `FAILED_BLOCKS:0`.

- [ ] **Step 3: Behavioral verification with a temporary Node harness**

Same technique as Task 2 Step 3 — the `run` function only touches `ld`, no DOM. Scratch file (not committed):

```js
var assert = require('assert');
var STORE = { sb_emps: JSON.stringify([
  { fn: 'Jane', ln: 'Doe', role: 'Fabricator', dept: 'Shop', type: 'Full Time', rate: 28, start: '2024-01-15', status: 'Active' },
  { fn: 'Sam', ln: 'Lee', role: 'Estimator', dept: 'Sales', type: 'Full Time', rate: 34, start: '2023-06-01', status: 'Active' }
])};
function ld(k, d) { return STORE[k] ? JSON.parse(STORE[k]) : d; }

var SB_TOOLS = {};
function sbRegisterTool(name, description, inputSchema, sensitive, run) { SB_TOOLS[name] = { definition: { name: name, description: description, input_schema: inputSchema }, sensitive: !!sensitive, run: run }; }

sbRegisterTool('get_employees', 'x', { type: 'object' }, false, function () {
  return ld('sb_emps', []).map(function (e) { return { name: (e.fn || '') + ' ' + (e.ln || ''), role: e.role, dept: e.dept, type: e.type, start: e.start, status: e.status }; });
});

var out = SB_TOOLS.get_employees.run();
assert.strictEqual(out.length, 2);
assert.strictEqual(out[0].name, 'Jane Doe');
assert.strictEqual(out[0].rate, undefined, 'rate must never appear in get_employees output');
assert.strictEqual(out[1].role, 'Estimator');

console.log('get_employees tool: all checks passed');
```

Run: `node <scratch-file>.js`
Expected: `get_employees tool: all checks passed`. Delete the scratch file afterward.

- [ ] **Step 4: Commit**

```bash
git add sairnbiz.html
git commit -m "feat: SAIRNbiz -- register get_employees as the v1 proof tool

Read-only roster lookup (name/role/dept/type/start/status), compensation
fields deliberately excluded even though this tool is non-sensitive --
payroll tools are a later spec's scope, not this one's."
```

---

### Task 5: End-to-end verification, push, live-verify

**Files:** none modified — verification only.

- [ ] **Step 1: Full local re-check of every changed file**

```bash
node --check api/claude.js
node api/claude.test.js
python tools/checkblocks.py sairnbiz.html
python tools/div_balance_check.py sairnbiz.html
```

Expected: `api/claude.test.js` shows `8 passed`; both Python checks show 0 failures / PASS.

- [ ] **Step 2: Guardian v2 pass on both changed files**

Run the full `sairn-guardian-v2` check (Check 0 + numbered checks) against `sairnbiz.html` and `api/claude.js` before push, per the project's standing Push Protocol — not "syntax passed" alone.

- [ ] **Step 3: Real interaction test — roster question**

With the app running against real seeded data, ask the AI Assistant a roster question ("who's on the team," "how many active employees do we have," "list the fabricators"). Confirm the answer contains real names/roles from `sb_emps` — not the old generic "we have N employees" response. This is the concrete proof the tool round-trip actually works, not just that it doesn't crash.

- [ ] **Step 4: Concurrency test**

Send two questions back-to-back before the first resolves — ideally one that triggers `get_employees` and one that doesn't (e.g. "who works here" then immediately "what's a fair markup on granite"). Confirm both answers land under their own message bubble, no stuck "Thinking...", no misattributed answer. This is the same live-test standard that caught the placeholder-by-DOM-position bug earlier this session in the sibling apps — code review alone is not sufficient here.

- [ ] **Step 5: Role-gate smoke check**

`get_employees` isn't sensitive, so this doesn't exercise the gate through the UI. Confirm the gate mechanism itself directly: open the browser console on the live app and run `sbExecuteTool('get_employees', 'owner')` and, temporarily, `SB_TOOLS.get_employees.sensitive = true; sbExecuteTool('get_employees', 'manager');` — expect the second call to return `{ok:false, error:'This data is restricted to the owner role.'}`. Reload the page afterward (the temporary mutation is not persisted).

- [ ] **Step 6: Push**

```bash
git push origin main
```

- [ ] **Step 7: Live-verify**

```bash
curl -s https://sairn.vercel.app/sairnbiz | grep -c "sbExecuteTool"
```

Expected: non-zero (confirms the deployed file includes the new dispatcher). Then repeat Step 3's real interaction test against the **live** URL, not just a local copy — per the project's standing rule that a clean push is not proof the live app reflects the change.

- [ ] **Step 8: Update the spec's status line**

Edit `docs/superpowers/specs/2026-08-09-sairnbiz-ai-tool-calling-design.md`'s `**Status:**` line to note the foundation is implemented and live-verified, with the date and confirming this unblocks item 2 (Payroll/P&L Copilot) as the next spec in the roadmap. Commit this doc-only change separately.
