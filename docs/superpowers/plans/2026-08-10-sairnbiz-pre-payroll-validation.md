# SAIRNbiz Pre-Payroll Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Before "Run Payroll" does anything (even the no-op toast it does today), flag real problems: an active employee with no pay rate (would silently compute as `$0`, the same shape as the real 8x-inflation bug this app already shipped once), and an active employee who started within the last 14 days (may not have been in a prior cycle). Missing-rate blocks the run; recently-started warns without blocking.

**Architecture:** `checkPayrollAnomalies()` — a new, pure function reading `ld('sb_emps',[])` directly, no `rPay()` dependency, no DOM read-back, fully Node-testable in isolation. Two consumers: (1) `runPayroll()` calls it and renders a new banner on the Payroll panel, blocking on CRITICAL; (2) a new AI tool, `get_payroll_anomalies`, lets the assistant explain findings on request. No changes to `rPay()`, `genReport()`, `sbExecuteTool()`, or `callAI()`.

**Tech Stack:** Vanilla JS (`sairnbiz.html`), same `SB_TOOLS` dispatcher items 1-2 built.

## Global Constraints

- `checkPayrollAnomalies()` filters to `status==='Active'` employees only — same scope `rPay()` already uses. (Spec §3)
- CRITICAL = missing or `<=0` `rate`. WARNING = `start` within the last 14 days (relative to real "now," not a fixed date). (Spec §3)
- CRITICAL findings **block** `runPayroll()`'s existing toast until acknowledged; WARNING findings show but never block. (Spec §4)
- The AI tool is `sensitive:true` (owner-only, same gate as `get_payroll_summary`/`get_pl_summary`). (Spec §4)
- No changes to `rPay()`, `genReport()`, `sbExecuteTool()`, or `callAI()` — purely additive. (Spec §4)
- No benefits-assumption check, no "vs. last cycle" check — both explicitly out of scope (Spec §2), logged to `SAIRN-BACKLOG.md` already.
- Every modified script block must pass `python tools/checkblocks.py sairnbiz.html` (`FAILED_BLOCKS:0`) and `python tools/div_balance_check.py sairnbiz.html` (`PASS`).
- Before push: Guardian v2 pass. After push: live-verify against `sairn.vercel.app`, per the project's standing Push Protocol.

---

### Task 1: `sairnbiz.html` — `checkPayrollAnomalies()`

**Files:**
- Modify: `sairnbiz.html` (insert immediately before `function rPay(){` — currently at line 1472; confirm this line number is still accurate before inserting)

**Interfaces:**
- Consumes: `ld(k,d)` (existing).
- Produces: `checkPayrollAnomalies()` — returns an array of `{severity:'critical'|'warning', employee:'First Last', message:'...'}` objects. Used by Task 2 (UI banner) and Task 3 (AI tool).

- [ ] **Step 1: Write the implementation**

Insert immediately before `function rPay(){` (`sairnbiz.html:1472`):

```js
// Pre-payroll validation (2026-08-10) -- deterministic checks that run
// BEFORE payroll "runs," so a wrong number gets caught before anyone
// trusts it, not after. This app has already shipped one real, silent
// payroll-math bug in production (0fa5fc6, the rPay() Benefits Cost 8x
// inflation) -- a real calculation, mathematically wrong, nothing about
// it looked broken. These checks exist so the next wrong number doesn't
// ship silently either.
//
// Pure function, no rPay() dependency, no DOM read-back -- unlike
// get_payroll_summary/get_pl_summary, these checks read raw employee
// records directly, so there is no "cold call" risk class here at all.
// See docs/superpowers/specs/2026-08-10-sairnbiz-pre-payroll-validation-design.md
function checkPayrollAnomalies() {
  var findings = [];
  var emps = ld('sb_emps', []).filter(function (e) { return e.status === 'Active'; });
  var now = Date.now();
  var FOURTEEN_DAYS_MS = 14 * 86400000;
  emps.forEach(function (e) {
    var name = (e.fn || '') + ' ' + (e.ln || '');
    if (!e.rate || e.rate <= 0) {
      findings.push({
        severity: 'critical',
        employee: name,
        message: name + ' has no pay rate set (or it is $0) -- payroll for this employee will silently compute as $0 across every figure.'
      });
    }
    if (e.start) {
      var startMs = new Date(e.start + 'T00:00:00').getTime();
      if (!isNaN(startMs) && (now - startMs) >= 0 && (now - startMs) < FOURTEEN_DAYS_MS) {
        findings.push({
          severity: 'warning',
          employee: name,
          message: name + ' started within the last 14 days -- may not have been included in a prior payroll cycle.'
        });
      }
    }
  });
  return findings;
}
```

- [ ] **Step 2: Syntax-check the modified script block**

Run: `python tools/checkblocks.py sairnbiz.html`
Expected: `TOTAL_BLOCKS:2` / `FAILED_BLOCKS:0`.

Run: `python tools/div_balance_check.py sairnbiz.html`
Expected: `RESULT:PASS`.

- [ ] **Step 3: Behavioral verification with a temporary Node harness**

The function has no DOM dependency, so its real logic can be tested directly by stubbing `ld` and `Date.now`. Scratch file (not committed):

```js
var assert = require('assert');

function makeCheckPayrollAnomalies(STORE, nowMs) {
  function ld(k, d) { return STORE[k] !== undefined ? STORE[k] : d; }
  return function checkPayrollAnomalies() {
    var findings = [];
    var emps = ld('sb_emps', []).filter(function (e) { return e.status === 'Active'; });
    var now = nowMs;
    var FOURTEEN_DAYS_MS = 14 * 86400000;
    emps.forEach(function (e) {
      var name = (e.fn || '') + ' ' + (e.ln || '');
      if (!e.rate || e.rate <= 0) {
        findings.push({ severity: 'critical', employee: name, message: name + ' has no pay rate set (or it is $0) -- payroll for this employee will silently compute as $0 across every figure.' });
      }
      if (e.start) {
        var startMs = new Date(e.start + 'T00:00:00').getTime();
        if (!isNaN(startMs) && (now - startMs) >= 0 && (now - startMs) < FOURTEEN_DAYS_MS) {
          findings.push({ severity: 'warning', employee: name, message: name + ' started within the last 14 days -- may not have been included in a prior payroll cycle.' });
        }
      }
    });
    return findings;
  };
}

var NOW = new Date('2026-08-10T12:00:00').getTime();

// Case 1: clean roster, no findings
var check1 = makeCheckPayrollAnomalies({ sb_emps: [
  { fn: 'Jane', ln: 'Doe', status: 'Active', rate: 28, start: '2024-01-15' }
]}, NOW);
assert.deepStrictEqual(check1(), []);

// Case 2: missing rate -> critical
var check2 = makeCheckPayrollAnomalies({ sb_emps: [
  { fn: 'Sam', ln: 'Lee', status: 'Active', rate: 0, start: '2024-01-15' }
]}, NOW);
var r2 = check2();
assert.strictEqual(r2.length, 1);
assert.strictEqual(r2[0].severity, 'critical');

// Case 3: recently started -> warning
var check3 = makeCheckPayrollAnomalies({ sb_emps: [
  { fn: 'Alex', ln: 'Kim', status: 'Active', rate: 25, start: '2026-08-05' }
]}, NOW);
var r3 = check3();
assert.strictEqual(r3.length, 1);
assert.strictEqual(r3[0].severity, 'warning');

// Case 4: started exactly 14 days ago -> NOT flagged (boundary, exclusive)
var check4 = makeCheckPayrollAnomalies({ sb_emps: [
  { fn: 'Old', ln: 'Timer', status: 'Active', rate: 25, start: '2026-07-27' }
]}, NOW);
assert.deepStrictEqual(check4(), []);

// Case 5: inactive employee with $0 rate -> NOT flagged (only Active checked)
var check5 = makeCheckPayrollAnomalies({ sb_emps: [
  { fn: 'Former', ln: 'Employee', status: 'Terminated', rate: 0, start: '2020-01-01' }
]}, NOW);
assert.deepStrictEqual(check5(), []);

// Case 6: both critical and warning on the same employee
var check6 = makeCheckPayrollAnomalies({ sb_emps: [
  { fn: 'New', ln: 'Hire', status: 'Active', rate: null, start: '2026-08-08' }
]}, NOW);
var r6 = check6();
assert.strictEqual(r6.length, 2);
assert.ok(r6.some(function(f){return f.severity==='critical';}));
assert.ok(r6.some(function(f){return f.severity==='warning';}));

console.log('checkPayrollAnomalies: all 6 cases passed');
```

Run: `node <scratch-file>.js`
Expected: `checkPayrollAnomalies: all 6 cases passed`. Delete the scratch file afterward.

- [ ] **Step 4: Commit**

```bash
git add sairnbiz.html
git commit -m "feat: SAIRNbiz -- checkPayrollAnomalies() (missing-rate + recent-hire checks)

Pure function, no rPay() dependency, no DOM read-back -- reads raw
sb_emps directly. CRITICAL: active employee with no/zero rate (silent
\$0 payroll, same shape as the real 8x-inflation bug already shipped
once). WARNING: active employee started within 14 days (matches the
panel's own bi-weekly cadence). Not yet wired to anything -- Tasks 2/3
consume it."
```

---

### Task 2: `sairnbiz.html` — `runPayroll()` rewire + banner UI

**Files:**
- Modify: `sairnbiz.html:515` (insert banner container after the Payroll panel header row), `sairnbiz.html:1503` (`runPayroll()`)

**Interfaces:**
- Consumes: `checkPayrollAnomalies()` (Task 1), `$(s)`, `H(s)` (existing HTML-escape helper — confirm it exists by grepping `function H(`), `toast(m,d)` (existing).

- [ ] **Step 1: Add the banner container**

Insert immediately after the Payroll panel's header row (`sairnbiz.html:515`, ends `</div></div>`), before the `.krow` KPI row:

```html
<div id="payroll-anomaly-banner"></div>
```

- [ ] **Step 2: Write the render + rewire implementation**

Replace `function runPayroll(){toast('Payroll calculated - no real payment was sent. Process through your bank or payroll provider.',4000);}` (`sairnbiz.html:1503`) with:

```js
function renderPayrollAnomalyBanner(findings) {
  var el = $('payroll-anomaly-banner');
  if (!el) return;
  if (!findings.length) { el.innerHTML = ''; return; }
  var criticals = findings.filter(function (f) { return f.severity === 'critical'; });
  var warnings = findings.filter(function (f) { return f.severity === 'warning'; });
  var html = '';
  if (criticals.length) {
    html += '<div style="background:rgba(239,68,68,0.08);border:1px solid var(--danger);border-radius:8px;padding:12px 14px;margin-bottom:10px;">' +
      '<div style="font-weight:700;color:var(--danger);margin-bottom:6px;">Cannot run payroll -- ' + criticals.length + ' issue(s) must be fixed first</div>' +
      criticals.map(function (f) { return '<div style="font-size:13px;color:var(--text);margin-top:2px;">' + H(f.message) + '</div>'; }).join('') +
      '</div>';
  }
  if (warnings.length) {
    html += '<div style="background:rgba(245,158,11,0.08);border:1px solid var(--warn);border-radius:8px;padding:12px 14px;margin-bottom:10px;">' +
      '<div style="font-weight:700;color:var(--warn);margin-bottom:6px;">' + warnings.length + ' item(s) worth a look</div>' +
      warnings.map(function (f) { return '<div style="font-size:13px;color:var(--text);margin-top:2px;">' + H(f.message) + '</div>'; }).join('') +
      '</div>';
  }
  el.innerHTML = html;
}
function runPayroll() {
  var findings = checkPayrollAnomalies();
  renderPayrollAnomalyBanner(findings);
  var hasCritical = findings.some(function (f) { return f.severity === 'critical'; });
  if (hasCritical) {
    toast('Cannot run payroll -- fix the flagged issue(s) first', 5000);
    return;
  }
  toast('Payroll calculated - no real payment was sent. Process through your bank or payroll provider.', 4000);
}
```

- [ ] **Step 3: Syntax-check**

Run: `python tools/checkblocks.py sairnbiz.html`
Expected: `TOTAL_BLOCKS:2` / `FAILED_BLOCKS:0`.

Run: `python tools/div_balance_check.py sairnbiz.html`
Expected: `RESULT:PASS` (the new `<div id="payroll-anomaly-banner"></div>` is self-closing on one line — confirm it doesn't shift the balance count unexpectedly; if `DIFF` is nonzero, the div wasn't written as a matched open/close pair).

- [ ] **Step 4: Live interaction test (local or live, whichever is available)**

Three scenarios, each via the real "Run Payroll" button:
1. Clean roster (no missing rates, no employees started in the last 14 days) → banner stays empty, toast fires as before.
2. Temporarily set an active employee's `rate` to `0` (via the Employee edit modal or a direct console `st()` call) → banner shows the CRITICAL box, toast does NOT fire. Fix the rate, click again → toast fires normally.
3. Temporarily set an active employee's `start` to within the last 14 days → banner shows the WARNING box, toast still fires.

- [ ] **Step 5: Commit**

```bash
git add sairnbiz.html
git commit -m "feat: SAIRNbiz -- runPayroll() blocks on missing-rate, warns on recent hires

New payroll-anomaly-banner container on the Payroll panel. runPayroll()
now calls checkPayrollAnomalies() first: any CRITICAL finding blocks the
existing toast until fixed; WARNING findings show but don't block. No
changes to rPay()."
```

---

### Task 3: `sairnbiz.html` — `get_payroll_anomalies` AI tool

**Files:**
- Modify: `sairnbiz.html` (insert immediately after `get_pl_summary`'s registration, which currently ends at line 1027 with `);` — confirm this line is still accurate)

**Interfaces:**
- Consumes: `checkPayrollAnomalies()` (Task 1), `sbRegisterTool(...)` (existing, from item 1).

- [ ] **Step 1: Write the implementation**

Insert after `get_pl_summary`'s closing `);` (`sairnbiz.html:1027`):

```js
sbRegisterTool(
  'get_payroll_anomalies',
  'Check for problems before payroll runs: any active employee with a missing or $0 pay rate (payroll would silently compute as $0 for them), and any active employee who started within the last 14 days (may not have been in a prior payroll cycle). Returns real findings, never guesses.',
  { type: 'object', properties: {}, required: [] },
  true,
  function (input) {
    var findings = checkPayrollAnomalies();
    return {
      critical_count: findings.filter(function (f) { return f.severity === 'critical'; }).length,
      warning_count: findings.filter(function (f) { return f.severity === 'warning'; }).length,
      findings: findings
    };
  }
);
```

- [ ] **Step 2: Syntax-check**

Run: `python tools/checkblocks.py sairnbiz.html`
Expected: `TOTAL_BLOCKS:2` / `FAILED_BLOCKS:0`.

Run: `python tools/div_balance_check.py sairnbiz.html`
Expected: `RESULT:PASS`.

- [ ] **Step 3: Behavioral verification**

`sbRegisterTool`'s registration itself has no DOM dependency; `checkPayrollAnomalies()` was already verified in Task 1. Confirm registration only: `grep -n "sbRegisterTool" sairnbiz.html` should show `get_payroll_anomalies` registered exactly once, with `true` as the 4th argument (sensitive).

- [ ] **Step 4: Commit**

```bash
git add sairnbiz.html
git commit -m "feat: SAIRNbiz -- get_payroll_anomalies AI tool

Owner-gated. Wraps checkPayrollAnomalies() (Task 1) for the AI assistant
-- deterministic checks flag, AI explains in plain language on request.
No new logic, pure registration."
```

---

### Task 4: End-to-end verification, push, live-verify

**Files:** none modified — verification only.

- [ ] **Step 1: Full local re-check**

```bash
python tools/checkblocks.py sairnbiz.html
python tools/div_balance_check.py sairnbiz.html
```

Expected: both clean.

- [ ] **Step 2: Guardian v2 pass**

Run the relevant `sairn-guardian-v2` checks against the changed sections of `sairnbiz.html` before push.

- [ ] **Step 3: Missing-rate blocking test (primary, live)**

Against the LIVE deployed app: as owner, temporarily set an active employee's rate to `0`, click Run Payroll, confirm the CRITICAL banner shows and the toast does NOT fire. Fix the rate, click again, confirm normal behavior resumes. Restore any seed data changed during this test.

- [ ] **Step 4: Recently-started warning test (live)**

Temporarily set an active employee's start date to within the last 14 days, click Run Payroll, confirm the WARNING banner shows AND the toast still fires (non-blocking). Restore the original start date afterward.

- [ ] **Step 5: AI tool test (live)**

Ask the AI Assistant to check payroll for issues before running it; confirm the answer reflects real findings (or a real "no issues found," whichever is true for the live seed data at test time), not generic advice. Verify a non-owner role gets the restricted-access message for this tool too.

- [ ] **Step 6: Push**

```bash
git push origin main
```

- [ ] **Step 7: Live-verify**

```bash
curl -s https://sairn.vercel.app/sairnbiz | grep -c "checkPayrollAnomalies"
curl -s https://sairn.vercel.app/sairnbiz | grep -c "get_payroll_anomalies"
curl -s https://sairn.vercel.app/sairnbiz | grep -c "payroll-anomaly-banner"
```

Expected: all three non-zero. Repeat Steps 3-4's tests against this confirmed-deployed live version specifically, per the project's standing rule that a clean push is not proof the live app reflects the change.

- [ ] **Step 8: Update the spec's status line**

Edit `docs/superpowers/specs/2026-08-10-sairnbiz-pre-payroll-validation-design.md`'s `**Status:**` line to note implementation complete and live-verified, naming which specific tests passed live (not "tests passed" generically). Commit this doc-only change separately, push it.
