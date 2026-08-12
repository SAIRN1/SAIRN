---
name: sairn-silent-failure-sweep
description: 'A dedicated check for the one pattern every genuinely catastrophic bug tonight shared: silent failure — something breaks, destroys data, or gets blocked, while showing no error, or worse, showing false success. Distinct from Guardian''s fabrication check (no function backing a number) — this is about real functions that fail without telling anyone. Trigger before calling any app "done," and specifically whenever a feature involves money, data persistence, or infrastructure (deployment, auth, API routing).'
---

# SAIRN Silent Failure Sweep

Every bug tonight that actually mattered — not just annoying, genuinely catastrophic — shared one property: **it looked fine while doing real damage.** Not a crash, not an error message, not even a hardcoded fake number. A real function, quietly failing, or a real infrastructure setting, quietly blocking, with nothing on screen to suggest anything was wrong.

## The real catastrophic bugs found tonight, and what they had in common

- **StoneDesk's reset IIFE**: wiped all business data on every page load. No error. Just gone.
- **NPS score data-clobber**: same shape — real data silently erased, no error.
- **SAIRNbiz's `saveEmp()`**: silently wiped an employee's benefits data on every edit. The save appeared to succeed.
- **SAIRNbiz's `runPayroll()`**: showed "Payroll approved — ACH transfers initiated" with zero actual payment processing behind it. A false success claim about *money moving*.
- **The 8x payroll inflation**: a real, working calculation — just mathematically wrong. Nothing about it looked broken.
- **The hardcoded "Synced" badge**: claimed sync succeeded regardless of whether it ever ran, sitting directly beside an honest field that told the truth.
- **The `invDelete()` collision**: a Delete button that showed a success confirmation while silently deleting nothing.
- **Vercel's SSO deployment protection**: blocked every single API request in production — found only because Michael personally opened the browser console. No amount of reading the app's source code could ever have caught this; it lived entirely outside the codebase, in infrastructure configuration.

**The common thread:** none of these threw a visible error. Several actively claimed success. One was invisible to code review entirely because it wasn't in the code.

## The sweep — ask these explicitly, don't wait to stumble onto them

1. **For every "save," "sync," "send," "submit," or "process" action: what does it show on failure, and does that path actually get exercised, or only ever tested on the happy path?** A save that always shows "Saved!" regardless of whether the write actually succeeded is a silent-failure bug waiting to be found the hard way.

2. **For every claim of money moving, data syncing, or an external system being contacted: is there a real network call/transaction behind that specific claim, or is the UI just assuming success?** (`runPayroll()`'s fake ACH message, the hardcoded "Synced" badge — both found this way.)

3. **For anything infrastructure-level (deployment settings, DNS, auth/SSO, environment variables, API gateway config): check it directly, not by reading application code.** No amount of `stonedesk.html` review would ever reveal a Vercel dashboard setting blocking every API call. This category of risk is invisible to every code-level tool built tonight — it needs a direct infrastructure check, done deliberately, not stumbled into.

4. **When two adjacent UI elements could contradict each other (a status badge next to a timestamp, a total next to a subtotal), do they actually agree, or could one be lying while the other tells the truth?** The hardcoded "Synced" badge sitting beside an honest "Last Sync: Never" field is the exact shape to watch for.

5. **Live-test the actual failure path, not just the success path.** Every silent-failure bug found tonight was found by triggering the real scenario (editing an employee, running payroll, checking the console after a page load) — never by reading the code alone.

## Displayed ≠ wired — a recurring, now-confirmed pattern (added 2026-08-12)

StoneDesk had this exact bug twice: drawing-tool cutout costs (sink/cooktop) computed correctly and displayed correctly in the drawing tool's own results panel, but never fed into calc()'s real quote total — a rep could draw $370 in cutouts and the quote showed $0 extra. Then the identical shape recurred with seam polished-edge cost. Both times: a real, correct calculation existed, rendered correctly in its own local display, and simply was never passed to the one function that owns the actual customer-facing total. Check this explicitly whenever a UI shows a dollar figure (or any computed value) in more than one place — confirm the "detail" display and the "total" display are reading the same live value, not two independently-computed numbers only one of which is real.

## Why this is separate from Guardian's Check 0b

Check 0b catches a number with *no function behind it at all* — a hardcoded literal masquerading as live data. This is different: a *real function*, genuinely running, that either fails without saying so, or succeeds at claiming something that never actually happened. Both are fabrication in the broad sense, but they need different detection methods — 0b is found by tracing whether a function exists; this is found by actually triggering the action and checking what happens on the failure path, and by checking infrastructure directly rather than trusting the code to reveal everything.
