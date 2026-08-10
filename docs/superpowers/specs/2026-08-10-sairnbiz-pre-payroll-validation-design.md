# SAIRNbiz — Pre-Payroll Validation

**Status:** Implementation complete and live-verified 2026-08-10 against
`sairn.vercel.app/sairnbiz` (post-push, commit `100c166`, pushed to
`origin/main`). All three specified live tests passed against the
confirmed-deployed version: **(1) missing-rate blocking test** — an
active employee's rate set to `0` produced the CRITICAL banner and the
"Cannot run payroll" toast (the success toast did not fire); restoring
the rate and re-running produced the normal "Payroll calculated" toast
and cleared the banner. **(2) recently-started warning test** — an
active employee's start date set to 3 days ago produced the WARNING
banner while the normal "Payroll calculated" success toast still fired
(non-blocking), confirmed live. **(3) AI tool test** — asking the AI
Assistant "Check payroll for any issues before I run it" as owner
triggered a real `get_payroll_anomalies` tool call returning
`{critical_count:0,warning_count:0,findings:[]}` against live seed
data, and the assistant's reply accurately reflected that real "no
issues found" result rather than generic advice; the same question
asked as a non-owner (`manager`) role returned the tool error `This
data is restricted to the owner role.`, correctly relayed by the
assistant as a restricted-access message. All temporarily-modified
seed data (`E008` Kevin Walsh's `rate` and `start`) was restored to its
original value and independently re-verified byte-for-byte against the
original record after testing. This is item 3 of the 6-item AI-native
roadmap for SAIRNbiz, building on the tool-calling foundation (item 1)
and financial tools (item 2, `get_payroll_summary`/`get_pl_summary`,
both live).

## 1. Problem

`runPayroll()` (`sairnbiz.html:1503`) is currently a no-op toast — it
checks nothing before "running." This app has already shipped one real,
silent payroll-math bug in production (`0fa5fc6`, "Fix rPay() Benefits
Cost / Total Labor Cost 8x inflation" — a real, working calculation,
mathematically wrong, nothing about it looked broken). This spec adds
real, deterministic checks that run before payroll "runs," so a wrong
number gets caught before anyone trusts it, not after.

## 2. Scope corrections made during brainstorming (both real, both deferred)

- **No "vs. last cycle" comparison.** SAIRNbiz persists zero payroll-run
  history anywhere — `runPayroll()` does nothing real, and "YTD Payroll"
  (`py-ytd`) is a fabricated `gross×13` extrapolation, not a sum of
  actual historical runs (already disclosed to the AI as such, item 2's
  final fix wave). There is nothing to compare "this cycle" against.
  Building real payroll-run snapshot persistence is a legitimate,
  separate feature — logged to `SAIRN-BACKLOG.md`, not built here.
- **No benefits-assumption-vs-real-enrollment check.** Originally
  proposed (rPay()'s flat `$520/active-employee` vs. real
  `e.ben.cost`), but `e.ben` is read in three places (`sairnbiz.html:1615-1619`)
  and **written nowhere in the file** — no benefits-enrollment save
  function exists at all. Real enrolled cost is always `$0` today, so
  this check would fire as a "mismatch" on every single run, forever —
  permanent noise, not a signal. The underlying gap (the Benefits
  panel's own KPIs are themselves always zero, for the same reason) is
  real, separate, and bigger than this spec — also logged to
  `SAIRN-BACKLOG.md`.

## 3. The two checks this spec actually builds

### CRITICAL — missing or zero pay rate

Any **active** employee (`status==='Active'`, same filter `rPay()`
already uses) with no `rate` or `rate<=0`. This is what "a missing tax
field" actually maps to: there is no per-employee tax field in this
app's data model at all (no W-4/SSN/filing-status field exists) — `rate`
is the one real required input every downstream tax figure (`gross`,
federal/state withholding, FICA, net) depends on. A missing/zero rate
doesn't produce an error; it silently computes `$0` everywhere for that
employee, the same "looks fine, isn't" shape as the 8x bug.

**Blocks `runPayroll()`.** This is a hard block with no override: the
function returns early, the "Payroll calculated" toast never fires, and
there is no acknowledge-and-proceed affordance (no confirm dialog, no
"override" button) anywhere in the shipped UI. The only way to
"proceed" is to fix the underlying data — correct the missing/zero
rate — and click Run Payroll again. An acknowledge-and-override
affordance was considered during the final review of this feature and
deliberately not built: simpler and safer than an override nobody
asked for, and consistent with the check existing to catch a silent
wrong number, not to be waved past.

### WARNING — recently-started employee

Any active employee whose `start` date falls within the last 14 days.
14 days, not an arbitrary number: the Payroll panel's own subtitle
already states "Bi-weekly" (`sairnbiz.html:514`), and `type==='Full
Time'` computes `80` hours (2 weeks) per period — 14 days is "may not
have been included in a prior cycle," derived from the app's own real
cadence, not guessed.

**Does not block.** Shown, not gated — a new employee is often
expected, not wrong; the point is visibility before running payroll for
someone the person clicking the button might not be thinking about, not
prevention.

## 4. Architecture

**`checkPayrollAnomalies()`** — new, pure, standalone function, added
near `rPay()` but not modifying it. Reads `ld('sb_emps',[])` directly.
Unlike items 1-2's tools, this has **no `rPay()` dependency and no DOM
read-back** — the checks operate on raw employee records (`rate`,
`start`), not on `rPay()`'s rendered KPI output, so there is no "cold
call" risk class here at all. Returns an array of finding objects:
`{severity:'critical'|'warning', employee, message}`.

**Surfacing (both, per the confirmed design):**
- **UI banner.** `runPayroll()` (`sairnbiz.html:1503`) calls
  `checkPayrollAnomalies()` first. A new `<div id="payroll-anomaly-banner">`
  (new markup, inserted after the Payroll panel's header row,
  `sairnbiz.html:515` — no existing markup touched) renders the
  findings. Any CRITICAL finding: banner shows, the existing "Payroll
  calculated" toast does **not** fire, function returns early. Only
  WARNING findings: banner shows, toast still fires as today. No
  findings: banner clears/hides, behavior identical to today.
- **AI tool, `get_payroll_anomalies`.** `sensitive:true` (owner-only,
  same gate as the other financial tools — this is payroll-adjacent
  data). No arguments. `run()` calls `checkPayrollAnomalies()` directly
  and returns `{critical_count, warning_count, findings}`. Lets the
  assistant explain findings in plain language on request — "deterministic
  checks flag, AI explains," same principle as the AI Budget Early
  Warning feature and everything else built on this foundation.

**No changes to `rPay()`, `genReport()`, `sbExecuteTool()`, or
`callAI()`** — purely additive, same discipline as item 2.

## 5. Testing

- **The 8x-bug-shaped test (primary):** seed a scenario that would have
  looked exactly like the real historical bug — this spec can't detect
  that specific bug (it's fixed, and there's no history to compare
  against), but confirm the missing-rate check fires correctly for the
  shape of defect that class of bug represents: a real, plausible-looking,
  silently-wrong-because-of-missing-input number.
- **Missing-rate blocking test:** an active employee with `rate:0` (or
  missing) → confirm the banner shows CRITICAL, the toast does NOT fire,
  and after fixing the rate, running again succeeds normally.
- **Recently-started warning test:** an active employee with `start`
  within 14 days → confirm WARNING banner, toast still fires.
- **Clean-run test:** no anomalies → confirm behavior is identical to
  today (toast fires, no banner shown).
- **AI tool test:** ask the assistant to check payroll before running it;
  confirm the answer reflects real findings, not generic advice — and,
  separately, confirm a non-owner role gets the restricted-access
  message, not a number.
- Standard structural checks (`checkblocks.py`, `div_balance_check.py`)
  after every `sairnbiz.html` change.
