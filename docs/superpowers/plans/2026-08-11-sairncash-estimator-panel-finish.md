# SAIRNcash Estimator Panel Finish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the already-existing profile inputs and results-display
skeleton in `sairncash.html`'s estimator view to the already-live tax-math
engine and Firebase profile path, per
`docs/superpowers/specs/2026-08-11-sairncash-estimator-panel-finish-design.md`.

**Architecture:** A new `profileCache` + `initProfileSync()` (mirrors the
existing `incomeCache`/`initFinanceSync()` pattern exactly), a new
`saveProfile()`/`populateProfileForm()` pair, a new `QUARTERLY_DEADLINES_2026`
constant, and a new `renderEstimator()` that reads `profileCache` +
`ytdNetProfit()` and calls the already-existing `calcQuarterlySetAside()`/
`calcRetirementEstimate()` to populate the results spans. No changes to
any already-implemented function from Tasks 0/1/2/4.

**Tech Stack:** No new dependencies — reuses `sairncash.html`'s existing
Firebase module (`window._fbProfileRef`, `window._fbOnValueRaw`,
`window._fbSetRaw`) and ES6 conventions already used throughout this file
(arrow functions, template literals — confirmed by reading
`initFinanceSync()`/`renderFinancePanel()`, this file's style differs
from SAIRNdental's ES5/var convention, match this file's own style, not
another app's).

## Global Constraints

- Every dollar/date figure comes from the already-existing, already-live
  `calcQuarterlySetAside()`/`calcRetirementEstimate()`/`ytdNetProfit()`
  functions or the new `QUARTERLY_DEADLINES_2026` table — this plan adds
  zero new math, only wiring (spec §1).
- Currency formatting matches this file's existing inline convention:
  `'$' + (Number(x)||0).toFixed(2)` (confirmed at `sairncash.html:791`,
  `795`) — no new `fmt()` helper introduced.
- `saveProfile()` guards on Firebase readiness exactly like
  `addIncomeEntry()` does (`sairncash.html:739`) — same toast text,
  same early-return-without-writing pattern.
- `QUARTERLY_DEADLINES_2026`'s 4 dates (verified against IRS.gov during
  design, spec §0): Apr 15 2026 (Q1), Jun 15 2026 (Q2), Sep 15 2026 (Q3),
  Jan 15 2027 (Q4) — use exactly these ISO dates, do not recompute or
  approximate.
- `resQuarterlyLabel` text: exactly `'Recommended quarterly set-aside'`
  when `hasFullBasis`, exactly `'Partial estimate (90% of this year
  only) -- add prior-year tax above for the full figure'` when not
  (spec §4).
- `python tools/checkblocks.py sairncash.html` / `div_balance_check.py`
  / `duplicate_global_check.py` clean after every change. Push Protocol:
  full local checks before push, real live-verify after.

---

### Task 1: Profile sync (`profileCache`, `initProfileSync`, `populateProfileForm`, `saveProfile`)

**Files:** Modify `sairncash.html`

**Interfaces:**
- Consumes: existing `window._fbProfileRef`, `window._fbOnValueRaw`,
  `window._fbSetRaw` (all already set up in `initFirebase()`,
  `sairncash.html:395-443`), existing `showToast()`.
- Produces: `profileCache` (object) — Task 2's `renderEstimator()` reads
  this exact variable. `saveProfile()` — the existing uncommitted "Save
  profile" button's `onclick="saveProfile()"` (already in the HTML)
  calls this exact function.

- [ ] **Step 1: Add `profileCache` and the sync/populate/save functions**

Insert immediately after `let incomeCache = [], deductionCache = [];`
(`sairncash.html:722`):

```js
let profileCache = {};

// Mirrors initFinanceSync()'s real-time-listener pattern exactly (line
// 724-736) -- a profile edit on one device reflects here live, same as
// income/deduction entries already do.
function initProfileSync() {
  if (!window._fbProfileRef || !window._fbOnValueRaw) return;
  window._fbOnValueRaw(window._fbProfileRef, snap => {
    profileCache = snap.val() || {};
    populateProfileForm();
    renderEstimator();
  });
}

function populateProfileForm() {
  const fs = document.getElementById('profFilingStatus');
  const pyt = document.getElementById('profPriorYearTax');
  const agi = document.getElementById('profAgiOver150k');
  const rv = document.getElementById('profRetirementVehicle');
  if (fs && profileCache.filing_status) fs.value = profileCache.filing_status;
  if (pyt) pyt.value = profileCache.prior_year_tax_liability || '';
  if (agi) agi.checked = !!profileCache.prior_year_agi_over_150k;
  if (rv && profileCache.retirement_vehicle) rv.value = profileCache.retirement_vehicle;
}

async function saveProfile() {
  if (!window._fbProfileRef || !window._fbSetRaw) { showToast('Sync not ready yet -- try again in a moment'); return; }
  const filing_status = document.getElementById('profFilingStatus').value;
  const prior_year_tax_liability = Number(document.getElementById('profPriorYearTax').value) || undefined;
  const prior_year_agi_over_150k = document.getElementById('profAgiOver150k').checked;
  const retirement_vehicle = document.getElementById('profRetirementVehicle').value;
  await window._fbSetRaw(window._fbProfileRef, { filing_status, prior_year_tax_liability, prior_year_agi_over_150k, retirement_vehicle });
  showToast('Profile saved');
}
```

(`renderEstimator()` is defined in Task 2 — `initProfileSync()` calling
it here is a forward reference that resolves correctly at runtime since
both are plain function declarations in the same script scope, same
pattern already used between `initFinanceSync()` and
`renderFinancePanel()`.)

- [ ] **Step 2: Call `initProfileSync()` alongside the existing `initFinanceSync()` call**

At `sairncash.html:570`:

```js
    if (window._initFirebaseSync) { await window._initFirebaseSync(); initFinanceSync(); initProfileSync(); }
```

- [ ] **Step 3: Syntax-check**

```
python tools/checkblocks.py sairncash.html
python tools/div_balance_check.py sairncash.html
python tools/duplicate_global_check.py sairncash.html
```

- [ ] **Step 4: Commit**

```bash
git add sairncash.html
git commit -m "feat: SAIRNcash -- profile sync (initProfileSync/populateProfileForm/saveProfile), mirrors existing income/deduction Firebase pattern"
```

---

### Task 2: `renderEstimator()` + quarterly deadline table

**Files:** Modify `sairncash.html`

**Interfaces:**
- Consumes: `profileCache` from Task 1, existing `ytdNetProfit()`,
  `calcQuarterlySetAside()`, `calcRetirementEstimate()`, `calcTotalTax()`
  (all already implemented, unchanged).
- Produces: `renderEstimator()` — Task 1's `initProfileSync()` (already
  wired in Task 1) and Task 3's view-switch hook both call this exact
  function.

- [ ] **Step 1: Add the deadline table and `renderEstimator()`**

Insert immediately after `function ytdNetProfit() { return sumIncome() - sumDeductions(); }`
(`sairncash.html:751`):

```js
// Verified against IRS.gov for tax year 2026 specifically -- each date
// individually checked against weekend/holiday shifts, none apply this
// year. Re-verify for any other tax year before reuse, same discipline
// as TAX_YEAR_2026.
const QUARTERLY_DEADLINES_2026 = [
  { label: 'Q1', date: '2026-04-15' },
  { label: 'Q2', date: '2026-06-15' },
  { label: 'Q3', date: '2026-09-15' },
  { label: 'Q4', date: '2027-01-15' }
];

function nextQuarterlyDeadline() {
  const now = new Date();
  for (const d of QUARTERLY_DEADLINES_2026) {
    const due = new Date(d.date + 'T23:59:59');
    if (due >= now) {
      const days = Math.ceil((due - now) / 86400000);
      return { label: d.label, dateStr: due.toLocaleDateString(), days };
    }
  }
  return null; // all 4 deadlines have passed -- fails safely, not thrown
}

function renderEstimator() {
  const ytd = ytdNetProfit();
  const filingStatus = profileCache.filing_status || 'single';
  const result = calcQuarterlySetAside(ytd, filingStatus, profileCache.prior_year_tax_liability, profileCache.prior_year_agi_over_150k);
  // calcRetirementEstimate's 2nd param must be the FULL SE tax (SS +
  // Medicare + Additional Medicare) -- calcTotalTax().seTax already
  // includes all three (sairncash.html:658-667, unchanged, already
  // live). calcSeTax() alone only returns ssAndMedicare, missing
  // Additional Medicare -- using that instead would understate the
  // half-SE-tax deduction for any high earner over the Additional
  // Medicare threshold, silently overstating their retirement room.
  const totalTaxResult = calcTotalTax(ytd, filingStatus, 0);
  const retirement = calcRetirementEstimate(ytd, totalTaxResult.seTax, profileCache.retirement_vehicle || 'none');

  const ytdEl = document.getElementById('resYtdNet');
  const annualEl = document.getElementById('resEstAnnual');
  const quarterlyEl = document.getElementById('resQuarterly');
  const quarterlyLabelEl = document.getElementById('resQuarterlyLabel');
  const deadlineEl = document.getElementById('resDeadline');
  const retirementEl = document.getElementById('resRetirement');
  const missingNoteEl = document.getElementById('profileMissingNote');

  if (ytdEl) ytdEl.textContent = '$' + ytd.toFixed(2);
  if (annualEl) annualEl.textContent = '$' + result.estAnnual.toFixed(2);
  if (quarterlyEl) quarterlyEl.textContent = '$' + result.quarterlyAmount.toFixed(2);
  if (quarterlyLabelEl) quarterlyLabelEl.textContent = result.hasFullBasis
    ? 'Recommended quarterly set-aside'
    : 'Partial estimate (90% of this year only) -- add prior-year tax above for the full figure';
  if (deadlineEl) {
    const next = nextQuarterlyDeadline();
    deadlineEl.textContent = next ? (next.dateStr + ' (' + next.days + ' days)') : 'N/A';
  }
  if (retirementEl) retirementEl.textContent = '$' + retirement.estimate.toFixed(2);
  if (missingNoteEl) missingNoteEl.style.display = result.hasFullBasis ? 'none' : '';
}
```

- [ ] **Step 2: Call `renderEstimator()` alongside the existing `renderFinancePanel()` calls in `initFinanceSync()`'s two listeners**

At `sairncash.html:726-730` (income listener):

```js
  window._fbOnValueRaw(window._fbIncomeRef, snap => {
    incomeCache = [];
    snap.forEach(c => { const v = c.val(); if (v) incomeCache.push(Object.assign({ key: c.key }, v)); });
    renderFinancePanel();
    renderEstimator();
  });
```

At `sairncash.html:731-735` (deduction listener):

```js
  window._fbOnValueRaw(window._fbDeductionsRef, snap => {
    deductionCache = [];
    snap.forEach(c => { const v = c.val(); if (v) deductionCache.push(Object.assign({ key: c.key }, v)); });
    renderFinancePanel();
    renderEstimator();
  });
```

- [ ] **Step 3: Syntax-check**

```
python tools/checkblocks.py sairncash.html
python tools/div_balance_check.py sairncash.html
python tools/duplicate_global_check.py sairncash.html
```

- [ ] **Step 4: Node harness verification of `nextQuarterlyDeadline()`'s date-selection logic (pure, no Firebase/DOM dependency for this one function)**

```
node -e "
const QUARTERLY_DEADLINES_2026 = [
  { label: 'Q1', date: '2026-04-15' },
  { label: 'Q2', date: '2026-06-15' },
  { label: 'Q3', date: '2026-09-15' },
  { label: 'Q4', date: '2027-01-15' }
];
function nextQuarterlyDeadline(nowOverride) {
  const now = nowOverride || new Date();
  for (const d of QUARTERLY_DEADLINES_2026) {
    const due = new Date(d.date + 'T23:59:59');
    if (due >= now) {
      const days = Math.ceil((due - now) / 86400000);
      return { label: d.label, dateStr: due.toLocaleDateString(), days };
    }
  }
  return null;
}
var assert = require('assert');
assert.strictEqual(nextQuarterlyDeadline(new Date('2026-04-01')).label, 'Q1');
assert.strictEqual(nextQuarterlyDeadline(new Date('2026-04-16')).label, 'Q2');
assert.strictEqual(nextQuarterlyDeadline(new Date('2026-09-16')).label, 'Q4');
assert.strictEqual(nextQuarterlyDeadline(new Date('2027-01-16')), null);
console.log('all 4 nextQuarterlyDeadline cases passed');
"
```

Expected: `all 4 nextQuarterlyDeadline cases passed`.

- [ ] **Step 5: Commit**

```bash
git add sairncash.html
git commit -m "feat: SAIRNcash -- renderEstimator() + quarterly deadline table, wired to income/deduction sync"
```

---

### Task 3: View-switch trigger + honest disclosure wiring

**Files:** Modify `sairncash.html`

**Interfaces:**
- Consumes: `renderEstimator()` from Task 2.
- Produces: no new functions — hooks into the existing `switchView()`.

- [ ] **Step 1: Call `renderEstimator()` when switching to the estimator view**

In `switchView(v)` (`sairncash.html:710-716`):

```js
function switchView(v) {
  document.querySelectorAll('.fin-view').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.view-tab').forEach(el => el.classList.remove('active'));
  document.getElementById('view-' + v).classList.add('active');
  document.getElementById('tab-' + v).classList.add('active');
  if (v === 'assistant') setTimeout(() => document.getElementById('inp').focus(), 50);
  if (v === 'estimator') renderEstimator();
}
```

- [ ] **Step 2: Syntax-check**

```
python tools/checkblocks.py sairncash.html
python tools/div_balance_check.py sairncash.html
```

- [ ] **Step 3: Manual verification (no automated browser/Firebase test harness for this file — matches this session's established convention for every other client-side change)**

Confirm `#profileMissingNote`'s initial `display:none` in the HTML
(already set in the uncommitted diff) is consistent with `renderEstimator()`
only ever setting it to `'none'` or `''` (never leaving a stale inline
style from before the first render) — read `renderEstimator()`'s code
to confirm this by inspection, since it can't be exercised without a
real Firebase-connected browser session.

- [ ] **Step 4: Commit**

```bash
git add sairncash.html
git commit -m "feat: SAIRNcash -- estimator view renders real data on switch, not just on sync events"
```

---

### Task 4: End-to-end verification, push, live-verify

- [ ] **Step 1:** Full local re-check: `checkblocks.py` /
  `div_balance_check.py` / `duplicate_global_check.py` on
  `sairncash.html`; confirm Task 2's Node verification still passes.
- [ ] **Step 2:** Push to `main`.
- [ ] **Step 3: Real regression test — genuinely live, not simulated.**
  Using a real (test-mode) Stripe-subscribed SAIRNcash account, open the
  Estimator view fresh. Confirm: `resYtdNet` shows `$0.00` (or real data
  if the test account has prior entries), `resQuarterlyLabel` shows the
  partial-estimate text (no profile saved yet), `resDeadline` shows a
  real, correct next-deadline date matching today's actual date against
  `QUARTERLY_DEADLINES_2026`.
- [ ] **Step 4:** Fill in and save a real profile (filing status, a
  prior-year tax liability figure, a retirement vehicle). Confirm:
  `resQuarterlyLabel` switches to "Recommended quarterly set-aside",
  `profileMissingNote` hides, `resQuarterly`/`resRetirement` show real
  computed numbers.
- [ ] **Step 5:** Hand-compute the expected `resQuarterly`/`resRetirement`
  values for the exact inputs entered in Step 4 using
  `calcQuarterlySetAside()`/`calcRetirementEstimate()`'s real formulas
  (already-verified functions per the parent plan's Task 1) — confirm
  the displayed numbers match exactly, proving the new wiring correctly
  connects to the existing math rather than silently diverging from it.
- [ ] **Step 6:** Add a real income entry through the existing Add
  Income form. Confirm `resYtdNet`/`resEstAnnual`/`resQuarterly` all
  update live, without switching views or reloading — the actual
  regression test for §0's "live recompute via existing listeners"
  decision.
- [ ] **Step 7 (two-device isolation, mirrors the parent plan's Task 0
  Step 4 methodology applied to profile specifically):** From a second
  browser/device signed into the same test account, confirm the saved
  profile from Step 4 appears correctly populated via
  `populateProfileForm()` — proving `initProfileSync()`'s listener
  genuinely syncs across devices, not just within one session.
- [ ] **Step 8:** Update
  `docs/superpowers/specs/2026-08-11-sairncash-estimator-panel-finish-design.md`'s
  status line with the real commit SHAs and confirmed-live date.

---

**Not started. Awaiting explicit go-ahead before any code in Tasks 1-4
is written**, per your instruction.
