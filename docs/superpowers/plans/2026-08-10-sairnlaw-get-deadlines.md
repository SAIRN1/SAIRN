# SAIRNlaw get_deadlines Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `get_deadlines` as the second tool on SAIRNlaw's already-shipped AI tool-calling foundation (`LAW_TOOLS`/`lawRegisterTool`/`lawExecuteTool`, live at `sairn.vercel.app/sairnlaw`), so the AI assistant can answer real deadline questions ("what's overdue," "what's coming up") instead of refusing, per `docs/superpowers/specs/2026-08-10-sairnlaw-get-deadlines-design.md`.

**Architecture:** One new `lawRegisterTool('get_deadlines', ...)` call reusing the existing dispatcher unchanged, plus a field-level edit to `LAW_FIRM_DATA_RULE`. No changes to `sendAI()`, `api/claude.js`, or the `lawAiBusy` concurrency guard — all already generic across any number of registered tools. Urgency (`"Overdue"` / `"Due soon"` / `"Upcoming"`) is computed by a new pure function, `computeDeadlineUrgency(dueDate, today, weekAheadMs)`, reusing `rDash()`'s own existing thresholds verbatim rather than a new scheme.

**Tech Stack:** Vanilla JS (`sairnlaw.html`, no framework). Verified the same way `get_matters` was: `tools/checkblocks.py` / `tools/div_balance_check.py` on the file, a temporary `node:assert` scratch harness for the pure function and the tool's `run()`, plus a real live-interaction test against the deployed app.

## Global Constraints

- Read-only tool only — `get_deadlines` may not create, modify, or delete any record. (Spec §3)
- No new persistence — reads live from `ld('law_deadlines', [])` via the existing `deadlines()` helper. (Spec §3)
- `status:'Pending'` only — `Complete` deadlines are excluded entirely, not merely labeled. (Spec §2)
- No type-based severity weighting — `type` stays in the output as plain data; urgency is purely date-driven. (Spec §2)
- Urgency thresholds reuse `rDash()`'s own existing convention verbatim: Overdue = `status==='Pending' && due_date < lawLocalToday()` (string comparison); Due soon = `due_date` within `Date.now()+7*24*60*60*1000` via `new Date(due_date+'T00:00:00').getTime()<=weekAheadMs`; anything else is Upcoming. Not a redesigned scheme. (Spec §2, §4)
- Non-sensitive — same trust level as `get_matters`; no new role-gating introduced. (Spec §2)
- No optional filter arguments in this pass — input is `{}`, matching `get_matters`'s v1 shape. (Spec §3)
- `notes`, `end_time`, and `created_at` excluded from the tool's output. (Spec §5)
- `LAW_FIRM_DATA_RULE` gets a precise field-level edit (deadlines now accessible, trust/billing/invoices/time-entries still not) — not a blanket rewrite. (Spec §6)
- Every modified script block in `sairnlaw.html` must pass `node --check`-equivalent structural checks before commit (project standing rule, `CLAUDE.md`).
- `python tools/checkblocks.py sairnlaw.html` and `python tools/div_balance_check.py sairnlaw.html` must stay clean (0 failed / PASS) after every change.
- Before push: full Guardian v2 check on `sairnlaw.html`. After push: live-verify against `sairn.vercel.app/sairnlaw` directly, not assumed from a clean push (project Push Protocol).

---

### Task 1: `sairnlaw.html` — `computeDeadlineUrgency()` and the `get_deadlines` tool

**Files:**
- Modify: `sairnlaw.html` (insert immediately after the `get_matters` `lawRegisterTool(...)` block's closing `);` at `sairnlaw.html:1484`, before `function clrAI(){...}` at `sairnlaw.html:1486`)

**Interfaces:**
- Consumes: `lawRegisterTool(name, description, inputSchema, sensitive, run)` (already exists, `sairnlaw.html:1438`), `deadlines()` (`sairnlaw.html:1297`, returns `ld('law_deadlines', [])`), `matterLabel(id)` (`sairnlaw.html:1304`, resolves a matter id to its real number+name), `lawLocalToday()` (`sairnlaw.html:959`, returns a `'YYYY-MM-DD'` string).
- Produces: `computeDeadlineUrgency(dueDate, today, weekAheadMs)` → `"Overdue" | "Due soon" | "Upcoming"` (module-level function, no globals touched) — used by `get_deadlines`'s `run()` and by Task 1's own test. `LAW_TOOLS.get_deadlines` — used by Task 2.

- [ ] **Step 1: Write the implementation**

Insert after the `get_matters` block's closing `);` (`sairnlaw.html:1484`):

```js
// Pure function -- takes already-known values as arguments, not global
// lookups, so it's fully Node-testable with no ld()/DOM stubbing needed.
// Reuses rDash()'s own existing urgency thresholds verbatim (see rDash(),
// sairnlaw.html:1575 area) rather than inventing a new scheme -- Overdue
// and Due-soon must mean the same thing here as they do on the dashboard.
function computeDeadlineUrgency(dueDate, today, weekAheadMs) {
  if (dueDate < today) return 'Overdue';
  if (new Date(dueDate + 'T00:00:00').getTime() <= weekAheadMs) return 'Due soon';
  return 'Upcoming';
}

lawRegisterTool(
  'get_deadlines',
  'Look up the firm\'s current PENDING deadlines only (completed deadlines are not included): matter, deadline type, title, due date, due time, and location. Each deadline includes an "urgency" field computed live from its due date -- "Overdue", "Due soon" (within 7 days), or "Upcoming" -- never from a stored status label. Does NOT include trust account balances, invoices, time entries, billing records, or deadline notes -- those are not available to this tool.',
  { type: 'object', properties: {}, required: [] },
  false,
  function (input) {
    // input intentionally unused -- this tool takes no real arguments, but
    // accepts one for interface consistency with lawExecuteTool(name, role,
    // input), matching get_matters' and SAIRNbiz's get_employees convention.
    var today = lawLocalToday();
    var weekAheadMs = Date.now() + 7 * 24 * 60 * 60 * 1000;
    return deadlines()
      .filter(function (d) { return d.status === 'Pending'; })
      .map(function (d) {
        return {
          matter: matterLabel(d.matter_id),
          type: d.type,
          title: d.title,
          due_date: d.due_date,
          due_time: d.due_time,
          location: d.location,
          urgency: computeDeadlineUrgency(d.due_date, today, weekAheadMs)
        };
      });
  }
);
```

- [ ] **Step 2: Syntax-check the modified script block**

Run: `python tools/checkblocks.py sairnlaw.html`
Expected: same `TOTAL_BLOCKS` as the current baseline (run it once before this edit if you don't already know the number), `FAILED_BLOCKS:0`.

Run: `python tools/div_balance_check.py sairnlaw.html`
Expected: `RESULT:PASS`.

- [ ] **Step 3: Behavioral verification with a temporary Node harness**

Both `computeDeadlineUrgency()` and the tool's `run()` have no DOM dependency. Create a scratch file (not committed — delete after this step):

```js
// scratch verification, delete after running
var assert = require('assert');

function computeDeadlineUrgency(dueDate, today, weekAheadMs) {
  if (dueDate < today) return 'Overdue';
  if (new Date(dueDate + 'T00:00:00').getTime() <= weekAheadMs) return 'Due soon';
  return 'Upcoming';
}

// -- pure function checks --
var today = '2026-08-10';
var weekAheadMs = new Date('2026-08-17T00:00:00').getTime();
assert.strictEqual(computeDeadlineUrgency('2026-08-05', today, weekAheadMs), 'Overdue');
assert.strictEqual(computeDeadlineUrgency('2026-08-10', today, weekAheadMs), 'Due soon', 'due today is not overdue, and is within the week-ahead window');
assert.strictEqual(computeDeadlineUrgency('2026-08-17', today, weekAheadMs), 'Due soon', 'exactly at the 7-day boundary matches rDash()\'s own <= comparison');
assert.strictEqual(computeDeadlineUrgency('2026-08-18', today, weekAheadMs), 'Upcoming');
console.log('computeDeadlineUrgency: all 4 checks passed');

// -- tool run() checks, stubbing deadlines()/matterLabel()/lawLocalToday() --
var LAW_DEADLINES = [
  { id: 'DL-1', matter_id: 'MT-2', type: 'Filing Deadline', title: 'Answer to Complaint due', due_date: '2026-08-05', due_time: '', end_time: '', status: 'Pending', location: '', notes: 'privileged strategy note', created_at: '2026-08-01' },
  { id: 'DL-2', matter_id: 'MT-1', type: 'Hearing', title: 'Status conference', due_date: '2026-08-12', due_time: '09:00', end_time: '10:00', status: 'Pending', location: 'Courtroom 4B', notes: '', created_at: '2026-08-01' },
  { id: 'DL-3', matter_id: 'MT-2', type: 'Court Deadline', title: 'Already handled', due_date: '2026-07-01', due_time: '', end_time: '', status: 'Complete', location: '', notes: '', created_at: '2026-06-01' }
];
var LAW_MATTERS = [
  { id: 'MT-1', matter_number: '2026-0001', matter_name: 'Ostrander Estate Planning' },
  { id: 'MT-2', matter_number: '2026-0002', matter_name: 'Delacroix v. Reyes Supply Co.' }
];
function deadlines() { return LAW_DEADLINES; }
function matterLabel(id) { var m = LAW_MATTERS.find(function (x) { return x.id === id; }); return m ? (m.matter_number + ' -- ' + m.matter_name) : '(unknown matter)'; }
function lawLocalToday() { return '2026-08-10'; }

var LAW_TOOLS = {};
function lawRegisterTool(name, description, inputSchema, sensitive, run) { LAW_TOOLS[name] = { definition: { name: name, description: description, input_schema: inputSchema }, sensitive: !!sensitive, run: run }; }

lawRegisterTool('get_deadlines', 'x', { type: 'object' }, false, function (input) {
  var today = lawLocalToday();
  var weekAheadMs = Date.now() + 7 * 24 * 60 * 60 * 1000; // note: real Date.now(), only urgency VALUES checked below via the matter/status/notes assertions, not exact tier boundaries (those are covered above)
  return deadlines().filter(function (d) { return d.status === 'Pending'; }).map(function (d) {
    return { matter: matterLabel(d.matter_id), type: d.type, title: d.title, due_date: d.due_date, due_time: d.due_time, location: d.location, urgency: computeDeadlineUrgency(d.due_date, today, weekAheadMs) };
  });
});

var out = LAW_TOOLS.get_deadlines.run({});
assert.strictEqual(out.length, 2, 'Complete deadline (DL-3) must be excluded');
assert.strictEqual(out[0].matter, '2026-0002 -- Delacroix v. Reyes Supply Co.', 'matter_id must be resolved to a real label');
assert.strictEqual(out[1].location, 'Courtroom 4B');
assert.strictEqual(out[0].notes, undefined, 'notes must never appear in get_deadlines output');
assert.strictEqual(out[0].end_time, undefined, 'end_time must never appear in get_deadlines output');
console.log('get_deadlines tool: all 4 checks passed');
```

Run: `node <scratch-file>.js`
Expected: `computeDeadlineUrgency: all 4 checks passed` then `get_deadlines tool: all 4 checks passed`. Delete the scratch file afterward.

- [ ] **Step 4: Commit**

```bash
git add sairnlaw.html
git commit -m "feat: SAIRNlaw -- register get_deadlines as the second AI tool

Read-only deadline lookup (matter/type/title/due date/due time/
location/urgency), Pending status only. urgency is computed live from
the due date via computeDeadlineUrgency(), reusing rDash()'s own
existing Overdue/Due-soon/Upcoming thresholds verbatim rather than a
new scheme. notes, end_time, and created_at deliberately excluded.
LAW_FIRM_DATA_RULE not yet updated (next commit) -- sendAI() doesn't
call this yet either (dispatcher/sendAI already generic, no change
needed there)."
```

---

### Task 2: `sairnlaw.html` — edit `LAW_FIRM_DATA_RULE` for the new access

**Files:**
- Modify: `sairnlaw.html:1426` (`LAW_FIRM_DATA_RULE`)

**Interfaces:**
- Consumes: none new.
- Produces: `LAW_FIRM_DATA_RULE` (existing global string, already referenced by `sendAI()`'s `sys` construction) — same variable name, edited content.

- [ ] **Step 1: Write the implementation**

Replace `LAW_FIRM_DATA_RULE`'s definition (`sairnlaw.html:1426`) with:

```js
var LAW_FIRM_DATA_RULE='CRITICAL RULE: you now have tool-based access to this firm\'s current MATTERS (matter number, matter name, client name, practice area, status, responsible attorney, opposing parties) via get_matters, and this firm\'s current PENDING deadlines (matter, deadline type, title, due date, due time, location, and a live-computed urgency) via get_deadlines -- use the matching tool for either topic rather than guessing, and never state a deadline\'s urgency, status, or existence without having actually called get_deadlines this turn. You do NOT have access to this firm\'s trust account balances, invoices, time entries, matter notes, deadline notes, or billing records -- none of that real data is available through any tool or included anywhere in this conversation. If asked something that depends on that still-unavailable data (e.g. "What is the trust balance on the Ostrander matter?", "How much has this client been billed?"), you MUST say plainly that you do not have access to it and direct the user to the relevant panel (Trust Accounting, Billing) to look it up -- never guess, estimate, or invent a specific figure or fact about that data. You may still help with general drafting, explaining concepts, and non-firm-specific questions.';
```

- [ ] **Step 2: Syntax-check**

Run: `python tools/checkblocks.py sairnlaw.html`
Expected: same `TOTAL_BLOCKS` as Task 1's result, `FAILED_BLOCKS:0`.

Run: `python tools/div_balance_check.py sairnlaw.html`
Expected: `RESULT:PASS`.

- [ ] **Step 3: Refusal-preserved local sanity check**

This step is a code-reading check, not a live test (Task 3 does the real live testing) — re-read the edited string and confirm it: (a) grants access to matters and deadlines specifically, (b) explicitly still refuses trust/invoices/time-entries/billing/notes, (c) does not accidentally drop the "never guess" instruction that was present in the prior version.

- [ ] **Step 4: Commit**

```bash
git add sairnlaw.html
git commit -m "fix: SAIRNlaw -- LAW_FIRM_DATA_RULE reflects real get_deadlines access

Precise field-level edit, not a blanket rewrite: deadlines are now
tool-accessible (Pending only, live urgency) and the refusal for them
is lifted; trust/invoices/time-entries/billing/notes remain genuinely
unavailable and the refusal for those stays exactly as strict as
before."
```

---

### Task 3: End-to-end verification, push, live-verify

**Files:** none modified — verification only.

- [ ] **Step 1: Full local re-check of the changed file**

```bash
python tools/checkblocks.py sairnlaw.html
python tools/div_balance_check.py sairnlaw.html
```

Expected: both checks show 0 failures / PASS.

- [ ] **Step 2: Guardian v2 pass**

Run the full `sairn-guardian-v2` check (Check 0 + numbered checks) against `sairnlaw.html` before push, per the project's standing Push Protocol. Diff against the last known-clean baseline (post-`get_matters` push) to confirm no new findings were introduced by this change specifically — the two pre-existing findings noted during the `get_matters` rollout (a duplicate `tr-explain-result` id, and `nav_panel_check.py`'s sidebar-button convention mismatch) are still out of scope for this task; confirm they're unchanged, not newly caused.

- [ ] **Step 3: Real interaction test — deadlines question**

With the app running against real seeded data (or a browser-console login bypass via `lawEnterApp({token:'test-token', role:'owner', employee_id:'test-owner'})`, same technique used for `get_matters`), ask the AI Assistant a deadlines question ("what deadlines are coming up," "is anything overdue," "what's the status of the Answer to Complaint deadline"). Confirm the answer contains real matter names, titles, due dates, and urgency from `law_deadlines` — not the old "I don't have access" refusal, and not a completed deadline.

- [ ] **Step 4: Refusal-preserved test**

Ask a trust-balance or billing question ("what's the trust balance on the Ostrander matter," "how much has this client been billed"). Confirm the model still refuses and redirects to the relevant panel — this is the regression check for Task 2's edit, proving deadline access didn't loosen the refusal for still-unavailable data.

- [ ] **Step 5: Consistency-with-dashboard spot check**

With the same real seeded data, compare `get_deadlines`'s Overdue/Due-soon counts (ask the assistant "how many deadlines are overdue" and "how many are due soon") against `rDash()`'s own dashboard numbers (`k-deadlines` element, and the overdue count in the dashboard's attention card) at the same moment. They should agree — both now use the same thresholds. A mismatch means the port diverged from `rDash()`'s actual logic somewhere and must be fixed before proceeding.

- [ ] **Step 6: Concurrency regression check**

Send two questions back-to-back before the first resolves — one that triggers `get_deadlines` and one that doesn't (e.g. "what's overdue" then immediately "what should go in a standard engagement letter"). Confirm exactly one bubble is created for the accepted call and the second send is rejected with the "please wait" toast, same as the `get_matters`-era fix — this is the first real chance to confirm `lawAiBusy` generalizes past the single-tool case it was originally fixed and verified against.

- [ ] **Step 7: Role-gate mechanism check (not exercised through the UI)**

`get_deadlines` isn't sensitive, so nothing in the UI naturally exercises the gate for it. Confirm the mechanism itself directly, same technique as the `get_matters` rollout: `lawExecuteTool('get_deadlines', 'owner', {})` should return `{ok:true, ...}`; temporarily setting `LAW_TOOLS.get_deadlines.sensitive = true` then calling `lawExecuteTool('get_deadlines', 'associate', {})` should return `{ok:false, error:'This data is restricted to the owner role.'}`. Reload the page afterward (the mutation is not persisted).

- [ ] **Step 8: Push**

```bash
git push origin main
```

- [ ] **Step 9: Live-verify**

```bash
curl -s https://sairn.vercel.app/sairnlaw | grep -c "get_deadlines"
```

Expected: non-zero (confirms the deployed file includes the new tool registration). Then repeat Steps 3-6's tests against the **live** URL, not just a local copy — per the project's standing rule that a clean push is not proof the live app reflects the change.

- [ ] **Step 10: Update the spec's status line**

Edit `docs/superpowers/specs/2026-08-10-sairnlaw-get-deadlines-design.md`'s `**Status:**` line to note the tool is implemented and live-verified, with the date, and record the dashboard-consistency spot-check result. Commit this doc-only change separately.
