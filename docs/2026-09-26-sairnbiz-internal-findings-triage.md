# SAIRNbiz — the four internal findings beyond the 1099 bug, extracted and prioritised

**2026-09-26 (Cody). Triage only. `sairnbiz.html` is NOT touched — `cc-queue12`
holds it.**

**HEADLINE: F1 is already fixed by cc and fixed in the right shape. Of the four
remaining, F4 is the one to do first — it is the fabricated-KPI class, shown to
every licence, and it includes a workers'-compensation status the app cannot
know. And cloud's F2 is right about a blocker being gone while the app's own
on-screen disclosure still says it is there — a stale sentence is holding a
feature back with a reason that stopped being true on 2026-09-15.**

Every figure below re-measured against `sairnbiz.html` at `1be35856`, not copied
from the cloud report. Source:
`docs/cloud-research/sairnbiz-external-competitive-gap-audit-2026-09-26.md` §0.3,
on `origin/claude/wizardly-ride-wtun13` (PR #18, unmerged).

---

## 0. F1 — CONFIRMED FIXED, and worth recording because it is the pattern

Cloud's F1: the "1099 Required" tile counted a vendor as required at **$600**
when OBBBA raised the threshold to **$2,000** for payments after 2025-12-31,
CPI-indexed from 2027. Direction: over-counting, so vendors paid $600–$1,999.99
in 2026 were labelled as requiring a form they do not.

**At `1be35856` the app carries `sb1099Threshold` — "$600 before 2026, $2,000 from
2026" (`sairnbiz.html:3809`).** Keyed to the **payment date**, not swapped for a
new constant, which is exactly the fix shape the research supported and exactly
what the 2026-09-03 audit's row A1 asked for: *compliance thresholds must be
dated and configurable, never a constant.* 2025 payments stay at $600.

Recorded so nobody re-opens it, and named as the template the other three should
follow where a statute is involved.

---

## 1. PRIORITY 1 — F4: the Benefits panel shows invented figures to every licence

**All six strings still present at `1be35856`, one occurrence each, in markup:**
`Medical Mutual`, `Fidelity`, `284,000`, `5.2%`, `BWC Ohio`, `1.5 days/month`.

Four cards at `sairnbiz.html:684-710` — Health, 401(k), Dental & Vision, Other
Benefits — every value a literal, no script targeting them. Only the `$520`
employer-cost line carries a "default" disclosure.

**Why this is first rather than F2, which involves more money.** Three reasons,
and the third is the one that decides it:

1. **It is the fabricated-KPI class**, which this platform treats as its worst
   category — and two of the values are the *hardest* kind: *"Employee Contrib.
   Avg 5.2%"* and *"Plan Assets (est.) $284,000"* both **look computed**. An
   invented plan name reads as sample data; an invented average reads as a
   measurement. StoneDesk's Vein Match KPIs were zeroed to `'--'` for precisely
   this distinction.
2. **Every licence sees the same numbers.** This is not a stale demo tenant; it
   is static markup, so a customer in Arizona is shown *"Workers Comp — Active ·
   BWC Ohio"*. **BWC is the Ohio Bureau of Workers' Compensation.** That is a
   compliance statement about a specific state's programme, asserted to every
   customer regardless of where they operate, on a screen about their benefits.
3. **The fix is the cheapest of the four and needs nobody's permission.** It is
   deletion or disclosure — the same treatment the safety-incidents tile and the
   timesheet hours already got in this app, both of which have a precedent
   comment to copy. No new rule, no external data, no statute to date.

**Scope note for whoever takes it:** the app has done this exact fix twice
already (`rTrain`, and the timesheet-hours pass whose comment says *"while
nothing writes the hours, the app says so instead of showing a number"*). Follow
that, not a fresh design.

---

## 2. PRIORITY 2 — F2: overtime is weekly-only, and a STALE DISCLOSURE is holding the fix back

**Verified at `1be35856`:** `daily overtime`, `double time`, `seventh`, `over 8`
and `1.5x` all return **zero** occurrences. The app computes overtime above 40
hours per week and nothing else. California (daily over 8, double time over 12,
seventh-day), Alaska (daily over 8), Nevada (daily over 8 under 1.5× minimum
wage) and Colorado (over 12 in a day) all have daily triggers, so the panel
**undercounts** in those states — the direction that costs an employer money and
attracts a claim.

Cloud's liability lens is the part to carry into any pitch: software
overtime/regular-rate and rounding logic produced employer class settlements and
then employers suing the vendor — ***DrinkPAK v. Paylocity*** and ***Nor-Cal
Moving v. Paylocity***.

### 2.1 THE CORRECTION THIS TRIAGE ADDS, and it is a one-line unblock

Cloud says: *"The 09-03 audit said phantom-wage detection was blocked because
timesheet hours came from a hardcoded array. **That blocker is gone:** timesheets
are now store-backed."*

**Cloud is right, and the app's own screen still says the opposite.**
`sairnbiz.html:1036`, under the Settings panel's *"Overtime Threshold
(hrs/week)"* input:

> *"Recorded, not yet used. The Timesheets panel still applies a fixed 40 — and
> **its hours are demo figures, not a real store**, so wiring this would make
> that look more authoritative than it is."*

That sentence was true when it was written and stopped being true on
**2026-09-15**. Measured: hours come from **`sb_ts` keyed by employee ID**;
`saveTimesheet()` is a real writer with an active-employee guard re-checked on
the write path; an employee with no record renders `--` and is **excluded** from
all three figures rather than defaulted to a full week; and the fix's own comment
records why the position-indexing version was dangerous — *"Set E003 to Inactive
and E004 moves to index 2, inheriting E003's 43-hour week."*

**So the stated reason for not wiring the configurable threshold no longer
exists.** Two consequences, and they are different sizes:

- **Small and immediate:** the disclosure is now wrong on screen, and it is the
  justification a future session will read and believe. Correcting that sentence
  is a one-line change and it unblocks the threshold.
- **Large and genuinely a build:** multi-state daily/double-time/seventh-day
  rules, and separately the payroll run's gross reading **scheduled** hours
  rather than recorded ones, so **recorded overtime reaches no payroll figure at
  all.** That second half is the one with money in it and it is not a
  configuration change.

**Do the one-line correction and the threshold wiring first; scope the multi-state
rules separately.** They are being treated as one item and they are not one item.

**Boundary note, not a defect:** from tax year 2026 any product supplying W-2
data must separate the FLSA overtime premium (box 12 code TT). SAIRNbiz supplies
no W-2 data.

---

## 3. PRIORITY 3 — F3: Employee FICA omits the Additional Medicare Tax, silently

**Verified at `1be35856`: `Additional Medicare`, `200,000` and `200000` all
return zero.** (There are 20 hits for `0.9` and none of them is this.)

Employers must withhold an extra **0.9%** on wages over **$200,000** in a
calendar year, and that threshold is **not indexed**. So the "Employee FICA"
figure understates for anyone past it.

**Why third rather than second:** exposure is genuinely low across SAIRN's
verticals — a shop foreman at $28.50/hour is nowhere near $200,000 — and the
error is in the *safe* direction for the employee while being wrong for the
employer's withholding obligation. **But it is an undisclosed error in a computed
figure, which is the class this platform treats as worst**, and it runs *opposite*
to the wage-base overstatement the app **does** disclose. That asymmetry is the
finding: one omission is disclosed and its mirror image is not.

**The fix is small and has two acceptable shapes**, and the app already uses both
elsewhere: compute it, or disclose the omission next to the figure. **Do not do
neither.**

---

## 4. PRIORITY 4 — F5: "free" is claimed in an AI prompt and nowhere in a contract

**Verified: `included free` appears exactly once across the platform, in
`stonedesk.html`'s AI system prompt.**

The FTC's Guide Concerning Use of the Word "Free" (16 CFR 251) asks that the
conditions of a "free" offer tied to a purchase be set out clearly and
conspicuously, at the outset and in close conjunction with the offer.

**Lowest priority of the four, for reasons worth stating rather than just
ranking:** it is one string, in a prompt rather than on a screen or in an
agreement; there is no SAIRNbiz agreement for it to contradict; and the remedy is
a **wording decision**, not a build. Cloud records the adjacent-industry
suggestion and explicitly does **not** adopt it — *say the module is included in
every subscription at no additional charge, and state its calculation-only scope
next to the claim* — and that is the right posture: it is Michael's sentence to
write, not a session's.

**It is also not SAIRNbiz's file**, which is worth noticing: the finding surfaced
in a SAIRNbiz audit and the string is in StoneDesk. Whoever takes it should not
go looking in `sairnbiz.html`.

---

## 5. Summary

| # | Finding | State at `1be35856` | Priority | Shape of the work |
|---|---|---|---|---|
| **F1** | 1099 threshold $600 → $2,000 | **FIXED** — `sb1099Threshold`, date-keyed | — | done, and it is the template |
| **F4** | Benefits panel invented figures | **open**, 6 strings present | **1** | deletion or disclosure; two in-app precedents |
| **F2** | weekly-only overtime + payroll gross ignores recorded hours | **open**, and its blocker is gone while the screen still claims it | **2** | split: a one-line disclosure correction, then a real multi-state build |
| **F3** | Additional Medicare Tax omitted | **open**, zero references | **3** | compute it or disclose it; small either way |
| **F5** | "free" in an AI prompt | **open**, one string, in `stonedesk.html` | **4** | a wording decision for Michael |

## 6. What this triage did NOT do

- **It did not touch `sairnbiz.html`.** `cc-queue12` holds that file and F1 is
  already theirs; a second session editing it is the write conflict the claim
  record exists to prevent.
- **It did not verify one external claim.** OBBBA, the 0.9% threshold, the four
  states' daily-overtime rules, 16 CFR 251 and both *Paylocity* cases are
  cloud's, inherited under cloud's own snippet-only caveat — its §0.1 records
  that `WebFetch` was `EGRESS_BLOCKED` for essentially every domain and that its
  search budget ran out during this very pass. **Nothing here is quotable to a
  customer without a primary read.**
- **It did not re-derive the rest of the audit.** §0.3 is five findings out of a
  1,492-line document; the competitive, pricing, market-scale and
  employment-law lenses are untouched here.
- **It did not measure how wrong F2 actually is.** "Undercounts in four states"
  is a statement about the rules, not about this app's data. Nobody has taken a
  real roster and computed the difference.

## 7. Decay

Counts are greps at `1be35856` against a file another session is actively
editing. **F1 moved from open to fixed between the cloud report being written and
this triage being written** — hours, not days — so re-measure before acting on
any row here.
