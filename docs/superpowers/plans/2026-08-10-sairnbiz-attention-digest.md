# SAIRNbiz Cross-Domain Attention Digest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `rDash()`'s stale-status-based `#d-actions` widget with one computed directly from real dates across budget, AP, training, and performance data, and expose the same computation as a new owner-gated AI tool — the first feature that genuinely reasons across HR and Accounting data in one place.

**Architecture:** `checkAttentionItems()` — a new, pure function (no DOM, no dependency on `rBud()`/`rAP()`/`rTrain()`/`rPerf()`), reading all four domains directly via `ld()`, returning a severity-then-domain-sorted findings array. Two consumers: `rDash()`'s `#d-actions` block (only that block — the KPI tiles, department chart, revenue trend, and activity feed are untouched) and a new AI tool, `get_attention_digest`.

**Tech Stack:** Vanilla JS (`sairnbiz.html`), same `SB_TOOLS` dispatcher items 1-3 built.

## Global Constraints

- All urgency determinations are computed from real date fields (`due`, `exp`) — never from the `status` field on `sb_ap`/`sb_train`/`sb_perf` records, all three of which are confirmed stale/never-recomputed. (Spec §1, §3)
- Budget threshold matches `rBud()`'s own existing values exactly: `>90%` CRITICAL, `>75%` WARNING (same operators). AP/performance "nearing" = 14 days. Training "nearing" = 30 days. (Spec §3)
- Findings are sorted severity-first (all CRITICAL, then all WARNING), and within each severity tier, ordered by domain: Budget → AP → Training → Performance. (Spec §4)
- `get_attention_digest` is `sensitive:true` (owner-only, same gate as the other financial/HR-sensitive tools). No arguments. (Spec §4)
- No changes to `rPay()`, `rBud()`, `rAP()`, `rTrain()`, `rPerf()`, `genReport()`, `sbExecuteTool()`, or `callAI()`. In `rDash()`, only the `#d-actions`-producing block (`sairnbiz.html:1354-1361`) is touched — the rest of the function is untouched.
- Every modified script block must pass `python tools/checkblocks.py sairnbiz.html` (`FAILED_BLOCKS:0`) and `python tools/div_balance_check.py sairnbiz.html` (`PASS`).
- Before push: Guardian v2 pass. After push: live-verify against `sairn.vercel.app`, per the project's standing Push Protocol.

---

### Task 1: `sairnbiz.html` — `checkAttentionItems()`

**Files:**
- Modify: `sairnbiz.html` (insert immediately before `function rDash(){` — currently at line 1329; confirm this line number is still accurate before inserting)

**Interfaces:**
- Consumes: `ld(k,d)`, `fmt(n)` (existing — both already defined earlier in the file at the point of use, since these are hoisted top-level function declarations).
- Produces: `checkAttentionItems()` — returns an array of `{severity:'critical'|'warning', domain:'budget'|'ap'|'training'|'performance', subject, message}` objects, pre-sorted (severity-first, then domain order). Used by Task 2 (`rDash()`) and Task 3 (AI tool).

- [ ] **Step 1: Write the implementation**

Insert immediately before `function rDash(){` (`sairnbiz.html:1329`):

```js
// Cross-domain attention digest (2026-08-10) -- synthesizes budget
// overages, AP bills nearing/past due, expiring certs, and overdue
// performance reviews into one prioritized list. Pure function, no DOM,
// no dependency on rBud()/rAP()/rTrain()/rPerf() -- reads sb_bud/sb_ap/
// sb_train/sb_perf directly.
//
// IMPORTANT: urgency is computed from the real date fields (due/exp),
// NEVER from the stored `status` field on sb_ap/sb_train/sb_perf --
// all three are confirmed stale and never recomputed after creation
// (no edit path exists for sb_train at all; the AP "Pay" button is a
// no-op toast; sb_perf status is chosen once at creation and never
// auto-flips to overdue). Trusting those labels would silently miss
// real problems -- the entire reason this function exists.
// See docs/superpowers/specs/2026-08-10-sairnbiz-attention-digest-design.md
function checkAttentionItems() {
  var findings = [];
  var now = Date.now();
  var FOURTEEN_DAYS_MS = 14 * 86400000;
  var THIRTY_DAYS_MS = 30 * 86400000;

  ld('sb_bud', []).forEach(function (b) {
    var u = b.annual > 0 ? Math.round(b.actual / b.annual * 100) : 0;
    if (u > 90) {
      findings.push({ severity: 'critical', domain: 'budget', subject: b.cat, message: b.cat + ' is over budget: ' + u + '% of annual (' + fmt(b.actual) + ' of ' + fmt(b.annual) + ').' });
    } else if (u > 75) {
      findings.push({ severity: 'warning', domain: 'budget', subject: b.cat, message: b.cat + ' is at ' + u + '% of annual budget -- worth watching.' });
    }
  });

  ld('sb_ap', []).forEach(function (bill) {
    if (bill.status === 'Paid' || !bill.due) return;
    var dueMs = new Date(bill.due + 'T00:00:00').getTime();
    if (isNaN(dueMs)) return;
    if (dueMs < now) {
      findings.push({ severity: 'critical', domain: 'ap', subject: bill.vendor, message: bill.vendor + ' bill (' + fmt(bill.bal) + ') is past due (' + bill.due + ').' });
    } else if (dueMs - now < FOURTEEN_DAYS_MS) {
      findings.push({ severity: 'warning', domain: 'ap', subject: bill.vendor, message: bill.vendor + ' bill (' + fmt(bill.bal) + ') is due within 14 days (' + bill.due + ').' });
    }
  });

  ld('sb_train', []).forEach(function (t) {
    if (!t.exp) return;
    var expMs = new Date(t.exp + 'T00:00:00').getTime();
    if (isNaN(expMs)) return;
    if (expMs < now) {
      findings.push({ severity: 'critical', domain: 'training', subject: t.emp, message: t.emp + '\'s ' + t.cert + ' certification expired (' + t.exp + ').' });
    } else if (expMs - now < THIRTY_DAYS_MS) {
      findings.push({ severity: 'warning', domain: 'training', subject: t.emp, message: t.emp + '\'s ' + t.cert + ' certification expires within 30 days (' + t.exp + ').' });
    }
  });

  ld('sb_perf', []).forEach(function (p) {
    if (p.status === 'Completed' || !p.due) return;
    var dueMs = new Date(p.due + 'T00:00:00').getTime();
    if (isNaN(dueMs)) return;
    if (dueMs < now) {
      findings.push({ severity: 'critical', domain: 'performance', subject: p.emp, message: p.emp + '\'s ' + p.type + ' is overdue (was due ' + p.due + ').' });
    } else if (dueMs - now < FOURTEEN_DAYS_MS) {
      findings.push({ severity: 'warning', domain: 'performance', subject: p.emp, message: p.emp + '\'s ' + p.type + ' is due within 14 days (' + p.due + ').' });
    }
  });

  var DOMAIN_ORDER = { budget: 0, ap: 1, training: 2, performance: 3 };
  findings.sort(function (a, b) {
    if (a.severity !== b.severity) return a.severity === 'critical' ? -1 : 1;
    return DOMAIN_ORDER[a.domain] - DOMAIN_ORDER[b.domain];
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

No DOM dependency, so real logic can be tested directly. Scratch file (not committed):

```js
var assert = require('assert');

function makeCheckAttentionItems(STORE, nowMs) {
  function ld(k, d) { return STORE[k] !== undefined ? STORE[k] : d; }
  function fmt(n) { return '$' + Number(n || 0).toLocaleString('en-US'); }
  return function checkAttentionItems() {
    var findings = [];
    var now = nowMs;
    var FOURTEEN_DAYS_MS = 14 * 86400000;
    var THIRTY_DAYS_MS = 30 * 86400000;
    ld('sb_bud', []).forEach(function (b) {
      var u = b.annual > 0 ? Math.round(b.actual / b.annual * 100) : 0;
      if (u > 90) findings.push({ severity: 'critical', domain: 'budget', subject: b.cat, message: b.cat + ' is over budget: ' + u + '% of annual (' + fmt(b.actual) + ' of ' + fmt(b.annual) + ').' });
      else if (u > 75) findings.push({ severity: 'warning', domain: 'budget', subject: b.cat, message: b.cat + ' is at ' + u + '% of annual budget -- worth watching.' });
    });
    ld('sb_ap', []).forEach(function (bill) {
      if (bill.status === 'Paid' || !bill.due) return;
      var dueMs = new Date(bill.due + 'T00:00:00').getTime();
      if (isNaN(dueMs)) return;
      if (dueMs < now) findings.push({ severity: 'critical', domain: 'ap', subject: bill.vendor, message: bill.vendor + ' bill (' + fmt(bill.bal) + ') is past due (' + bill.due + ').' });
      else if (dueMs - now < FOURTEEN_DAYS_MS) findings.push({ severity: 'warning', domain: 'ap', subject: bill.vendor, message: bill.vendor + ' bill (' + fmt(bill.bal) + ') is due within 14 days (' + bill.due + ').' });
    });
    ld('sb_train', []).forEach(function (t) {
      if (!t.exp) return;
      var expMs = new Date(t.exp + 'T00:00:00').getTime();
      if (isNaN(expMs)) return;
      if (expMs < now) findings.push({ severity: 'critical', domain: 'training', subject: t.emp, message: t.emp + '\'s ' + t.cert + ' certification expired (' + t.exp + ').' });
      else if (expMs - now < THIRTY_DAYS_MS) findings.push({ severity: 'warning', domain: 'training', subject: t.emp, message: t.emp + '\'s ' + t.cert + ' certification expires within 30 days (' + t.exp + ').' });
    });
    ld('sb_perf', []).forEach(function (p) {
      if (p.status === 'Completed' || !p.due) return;
      var dueMs = new Date(p.due + 'T00:00:00').getTime();
      if (isNaN(dueMs)) return;
      if (dueMs < now) findings.push({ severity: 'critical', domain: 'performance', subject: p.emp, message: p.emp + '\'s ' + p.type + ' is overdue (was due ' + p.due + ').' });
      else if (dueMs - now < FOURTEEN_DAYS_MS) findings.push({ severity: 'warning', domain: 'performance', subject: p.emp, message: p.emp + '\'s ' + p.type + ' is due within 14 days (' + p.due + ').' });
    });
    var DOMAIN_ORDER = { budget: 0, ap: 1, training: 2, performance: 3 };
    findings.sort(function (a, b) { if (a.severity !== b.severity) return a.severity === 'critical' ? -1 : 1; return DOMAIN_ORDER[a.domain] - DOMAIN_ORDER[b.domain]; });
    return findings;
  };
}

var NOW = new Date('2026-08-10T12:00:00').getTime();

// Case 1: clean state, no findings
var c1 = makeCheckAttentionItems({}, NOW);
assert.deepStrictEqual(c1(), []);

// Case 2: budget boundaries -- 90% not flagged, 91% critical, 75% not flagged, 76% warning
var c2 = makeCheckAttentionItems({ sb_bud: [
  { cat: 'A', annual: 100, actual: 90 },
  { cat: 'B', annual: 100, actual: 91 },
  { cat: 'C', annual: 100, actual: 75 },
  { cat: 'D', annual: 100, actual: 76 }
]}, NOW);
var r2 = c2();
assert.strictEqual(r2.length, 2);
assert.ok(r2.some(function(f){return f.subject==='B'&&f.severity==='critical';}));
assert.ok(r2.some(function(f){return f.subject==='D'&&f.severity==='warning';}));

// Case 3: stale-status independence -- status says fine, real date says critical
var c3 = makeCheckAttentionItems({
  sb_ap: [{ vendor: 'V1', bal: 500, status: 'Open', due: '2026-01-01' }],
  sb_train: [{ emp: 'E1', cert: 'CPR', status: 'Active', exp: '2026-01-01' }],
  sb_perf: [{ emp: 'E2', type: 'Annual', status: 'Scheduled', due: '2026-01-01' }]
}, NOW);
var r3 = c3();
assert.strictEqual(r3.length, 3);
assert.ok(r3.every(function(f){return f.severity==='critical';}));

// Case 4: Paid AP bill excluded even if overdue by date
var c4 = makeCheckAttentionItems({ sb_ap: [{ vendor: 'V2', bal: 0, status: 'Paid', due: '2026-01-01' }] }, NOW);
assert.deepStrictEqual(c4(), []);

// Case 5: Completed review excluded even if overdue by date
var c5 = makeCheckAttentionItems({ sb_perf: [{ emp: 'E3', type: 'Annual', status: 'Completed', due: '2026-01-01' }] }, NOW);
assert.deepStrictEqual(c5(), []);

// Case 6: sort order -- critical (any domain) before warning (any domain), domain order within tier
var c6 = makeCheckAttentionItems({
  sb_perf: [{ emp: 'PerfWarn', type: 'Annual', status: 'Scheduled', due: '2026-08-15' }],
  sb_bud: [{ cat: 'BudCrit', annual: 100, actual: 95 }]
}, NOW);
var r6 = c6();
assert.strictEqual(r6.length, 2);
assert.strictEqual(r6[0].domain, 'budget');
assert.strictEqual(r6[0].severity, 'critical');
assert.strictEqual(r6[1].domain, 'performance');
assert.strictEqual(r6[1].severity, 'warning');

console.log('checkAttentionItems: all 6 cases passed');
```

Run: `node <scratch-file>.js`
Expected: `checkAttentionItems: all 6 cases passed`. Delete the scratch file afterward.

- [ ] **Step 4: Commit**

```bash
git add sairnbiz.html
git commit -m "feat: SAIRNbiz -- checkAttentionItems() (budget/AP/training/performance)

Pure function, no DOM/rBud()/rAP()/rTrain()/rPerf() dependency -- reads
all four domains directly. Urgency computed from real date fields
(due/exp), never from the stale status labels on sb_ap/sb_train/sb_perf
(all three confirmed never-recomputed after creation). Severity-then-
domain sorted. Not yet wired to anything -- Tasks 2/3 consume it."
```

---

### Task 2: `sairnbiz.html` — `rDash()`'s `#d-actions` rewire

**Files:**
- Modify: `sairnbiz.html:1354-1361` (the `actions` array construction and `#d-actions` render inside `rDash()` — confirm these line numbers are still accurate; do not touch any other part of `rDash()`)

**Interfaces:**
- Consumes: `checkAttentionItems()` (Task 1), `H(s)` (existing HTML-escape helper).

- [ ] **Step 1: Write the implementation**

**Decided explicitly, not left to the implementer:** the old widget also
included two items outside this spec's four domains — overdue AR
invoices and an open-hiring-position count. The spec's scope is
budget/AP/training/performance only; it never said to remove AR/hiring
visibility. Preserve both exactly as they rendered before, appended
after the new `checkAttentionItems()` findings — do not drop them and
do not ask; this is settled.

Replace the block from `var actions=[];` through
`$('d-actions').innerHTML=actions.length?actions.map(...` (currently
`sairnbiz.html:1354-1361`) with:

```js
  var attn = checkAttentionItems();
  var legacyActions = [];
  invs.filter(function (i) { return i.status === 'Overdue'; }).forEach(function (i) { legacyActions.push({ t: H(i.id) + ' overdue - ' + fmt(i.amt - (i.paid || 0)) + ' ' + H(i.cust), b: 'Overdue', c: 'br' }); });
  if (h.length) legacyActions.push({ t: h.length + ' open hiring position' + (h.length === 1 ? '' : 's') + ' active', b: 'Hiring', c: 'bb' });
  var attnHtml = attn.map(function (f) {
    var badgeClass = f.severity === 'critical' ? 'br' : 'bw';
    var badgeLabel = f.severity === 'critical' ? 'Critical' : 'Watch';
    return '<div class="srow"><span class="slbl">' + H(f.message) + '</span><span class="badge ' + badgeClass + '">' + badgeLabel + '</span></div>';
  }).join('');
  var legacyHtml = legacyActions.map(function (a) { return '<div class="srow"><span class="slbl">' + a.t + '</span><span class="badge ' + a.c + '">' + a.b + '</span></div>'; }).join('');
  $('d-actions').innerHTML = (attnHtml + legacyHtml) || '<div style="color:var(--muted);text-align:center;padding:12px;">Nothing needs attention</div>';
```

This fully replaces the old AP/training/performance filtering (`bills.filter(status==='Overdue')`, `tr.filter(status==='Expiring Soon')`, the `duePf` block) — none of that stale-status logic remains, since `checkAttentionItems()` now owns those three domains. AR-overdue and hiring-count logic is preserved verbatim (same `invs`/`h` vars, same `{t,b,c}` shape, same badge classes), just renamed to `legacyActions` and rendered after the new findings. `bills`/`tr`/`pf` (the local vars destructured at the top of `rDash()`) may become partially or fully unused by this specific block afterward — that's fine and expected (they're still used elsewhere in `rDash()`, e.g. the activity feed); do not remove them from the destructure, that's out of scope.

- [ ] **Step 2: Syntax-check**

Run: `python tools/checkblocks.py sairnbiz.html`
Expected: `TOTAL_BLOCKS:2` / `FAILED_BLOCKS:0`.

Run: `python tools/div_balance_check.py sairnbiz.html`
Expected: `RESULT:PASS`.

- [ ] **Step 3: Live interaction test**

Against a local or live instance: view the Dashboard with clean seed data → confirm `#d-actions` shows the same information as before (AR overdue, hiring count) plus nothing new (assuming clean budget/AP/training/performance data). Temporarily create a stale-status-mismatch scenario (e.g. an AP bill with `status:'Open'` but a past `due` date) → confirm it now appears in `#d-actions` as Critical, where the OLD code would have missed it (since old code checked `status==='Overdue'`, not the real date). Restore any modified seed data afterward.

- [ ] **Step 4: Commit**

```bash
git add sairnbiz.html
git commit -m "feat: SAIRNbiz -- rDash() #d-actions now uses checkAttentionItems()

Replaces stale-status-based budget/AP/training/performance checks with
real-date-computed ones. AR-overdue and open-hiring-count items
(outside this feature's four domains) preserved unchanged alongside the
new findings. No other part of rDash() touched."
```

---

### Task 3: `sairnbiz.html` — `get_attention_digest` AI tool

**Files:**
- Modify: `sairnbiz.html` (insert immediately after `get_payroll_anomalies`'s closing `);`, currently at line 1043 — confirm still accurate)

**Interfaces:**
- Consumes: `checkAttentionItems()` (Task 1), `sbRegisterTool(...)` (existing).

- [ ] **Step 1: Write the implementation**

Insert after `get_payroll_anomalies`'s closing `);` (`sairnbiz.html:1043`):

```js
sbRegisterTool(
  'get_attention_digest',
  'Get a prioritized list of everything across the business that needs attention right now: budget categories over 90% (critical) or 75-90% (warning) of annual spend, AP bills past due (critical) or due within 14 days (warning), employee certifications expired (critical) or expiring within 30 days (warning), and performance reviews overdue (critical) or due within 14 days (warning). Findings are computed from real dates, not from stored status labels. Synthesize across domains in your answer when more than one is present -- do not just list one domain and ignore the others.',
  { type: 'object', properties: {}, required: [] },
  true,
  function (input) {
    var findings = checkAttentionItems();
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

No new logic (Task 1 already verified `checkAttentionItems()`). Confirm registration only: `grep -n "sbRegisterTool" sairnbiz.html` shows `get_attention_digest` registered exactly once, with `true` as the 4th argument.

- [ ] **Step 4: Commit**

```bash
git add sairnbiz.html
git commit -m "feat: SAIRNbiz -- get_attention_digest AI tool

Owner-gated. Wraps checkAttentionItems() (Task 1) for the AI assistant
-- the flagship capability: synthesizing budget, AP, training, and
performance findings into one answer. No new logic, pure registration."
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

Run the relevant `sairn-guardian-v2` checks against the changed sections of `sairnbiz.html`.

- [ ] **Step 3: Stale-label independence test (primary, live)**

Against the LIVE deployed app: temporarily create at least one real stale-status-mismatch record (e.g. an AP bill with `status:'Open'` but a `due` date in the past, or a training cert with `status:'Active'` but `exp` in the past). Confirm `#d-actions` on the Dashboard now flags it as Critical — the specific thing the old code could never do. Restore the modified seed data afterward.

- [ ] **Step 4: Multi-domain synthesis test (live)**

With more than one domain having a real finding (natural seed data or temporarily arranged), ask the AI Assistant something like "what needs my attention across the business right now" — confirm the answer synthesizes findings from more than one domain in one coherent response, not a single-domain answer. Verify a non-owner role gets the restricted-access message for `get_attention_digest`.

- [ ] **Step 5: Clean-state and AR/hiring-preservation test (live)**

With no anomalies in the four new domains, confirm `#d-actions` still shows AR-overdue and open-hiring-position items exactly as before (or "Nothing needs attention" if genuinely nothing applies across all six signal types).

- [ ] **Step 6: Push**

```bash
git push origin main
```

- [ ] **Step 7: Live-verify**

```bash
curl -s https://sairn.vercel.app/sairnbiz | grep -c "checkAttentionItems"
curl -s https://sairn.vercel.app/sairnbiz | grep -c "get_attention_digest"
```

Expected: both non-zero. Repeat Steps 3-4's tests against this confirmed-deployed version specifically.

- [ ] **Step 8: Update the spec's status line**

Edit `docs/superpowers/specs/2026-08-10-sairnbiz-attention-digest-design.md`'s `**Status:**` line to note implementation complete and live-verified, naming which specific tests passed live (stale-label independence test, multi-domain synthesis test) — not "tests passed" generically. Commit this doc-only change separately, push it.
