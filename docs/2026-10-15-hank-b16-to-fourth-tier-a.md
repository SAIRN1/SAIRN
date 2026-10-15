# Routed to fourth — the b15 Tier A obligation on `sen_pay_rates` / `sen_visits`, with two of its three questions now BUILT rather than asked

**Written 2026-10-15 by hank, batch b16.** The obligation stays **fourth's to
discharge** — nothing here discharges it and nothing here asks fourth to accept
my own verdict on my own work. What changed is that two of the three things it
raised have been **decided by Michael and implemented**, so the review has
different code in front of it than the record describes.

The obligation record is in `docs/tier-a-reviews.json`, opened
`2026-10-15T13:42:07Z` by hank at `49f6a752`, resources `sen_pay_rates` and
`sen_visits`, file `api/b15-payroll-effective-clock.test.js`.

---

## What the obligation asked, and where each part now stands

| # | The question as the record states it | Status after b16 |
|---|---|---|
| **(a)** | **THE RESTATEMENT QUESTION** — a correction approved AFTER a pay run silently changes a historical total, because nothing versions a paid period. `corrected_clock_visits` makes a figure reconcilable and that is not a restatement trail. *Decide whether a paid period must be frozen.* | **DECIDED BY MICHAEL AND BUILT.** Paid periods are frozen; a later approval posts as an adjustment line in the next period. See §1. |
| **(b)** | `api/_lib/sen-evv-readiness.js` and the client's EVV anomaly checks still read the raw clock, so an EVV export and a pay run can disagree about the same visit. | **DECIDED BY MICHAEL AND BUILT.** Both now read the same effective clock pay uses. See §2. |
| **(c)** | Whether the new `require()` in a file whose header claims purity is defensible, and whether `effectiveClock` can throw on any row shape `computePayroll` accepts. | **ONE HALF MEASURED, ONE HALF STILL OPEN.** See §3 — the throw question is answered with a driven arm; the purity question is a judgment and is still fourth's. |

**The review is therefore WIDER than it was, not narrower.** b15 added one
substitution. b16 added a freeze rule, an adjustment line, a new input to a pure
module, a new settings read in the handler, and a change to a compliance
verdict. All of it is money or a regulated determination.

---

## 1. (a) — the freeze, as built

`api/_lib/sen-evv-clock.js` gained `effectiveClockAsOf(visitData, field, asOfISO)`
and `effectiveClock` is now that function with `asOf = null`. The approval rule
stays in **one** place.

`api/_lib/sen-payroll.js` gained an optional `closed_periods` input —
`[{period_start, period_end, paid_at}]` — and:

* a run of a **closed** period reads each visit's clock **as at that period's
  `paid_at`**, so the total recomputes to its as-paid basis;
* a run of an **open** period posts an **adjustment line** for any visit in a
  closed period whose approval landed after `paid_at`, in the period
  **containing the approval** (that last clause is what stops it posting
  forever);
* `gross_cents` keeps its existing meaning. `adjustment_cents` and
  `total_payable_cents` are new and separate.

`api/sd-data.js`'s payroll branch reads the list from `sen_settings`
(`setting_key = payroll_closed_periods`) and **never from the caller's payload**.

**WHAT I WANT ATTACKED, and these are things I cannot answer about my own work:**

1. **THE THREE-STATE HANDLING OF AN UNDATABLE APPROVAL.** An approved entry
   with no readable `approved_at_server` **applies on the as-paid basis** and is
   **counted** in `undatable_corrections`. My reasoning: every correction filed
   before 2026-10-14 is approved by the no-status rule and carries no approval
   instant at all, so dropping them would un-pay live corrected visits. **The
   hazard I can see and have not closed:** for a period closed AFTER today, a
   legacy undatable correction WAS in the as-paid figure, so it applies to the
   frozen total — correct — and no adjustment posts — also correct. But I am
   reasoning about a counterfactual history, and if the reasoning is wrong in
   the other direction the same entry could be double-counted. Arm F7 pins the
   behaviour; it does not prove the choice.
2. **THE ADJUSTMENT IS STRAIGHT TIME AND IS A FLOOR, NOT A TOTAL.** If the
   delta pushes the already-paid workweek past 40 hours there is an FLSA
   overtime premium owed on top, and computing it means reopening the frozen
   week. `not_computed` says so in the output. **Decide whether a floor is
   acceptable here at all**, because a caregiver underpaid the premium is the
   same class of harm F1 closed.
3. **AN ADJUSTMENT POSTS IN THE PERIOD CONTAINING ITS APPROVAL, so a period
   that is never run never pays it.** Nothing sweeps for unposted adjustments.
   This is stated in `not_computed` and is a real gap.
4. **`period_closed` IS DERIVED FROM THE RUN'S START DATE** — `closedFor(start)`
   plus `end <= closed.period_end`. A run that **straddles** a closed boundary
   is therefore reported as NOT closed while its in-closed-period visits are
   still individually frozen. I believe per-visit freezing is the safe half and
   the label is the unsafe half; **check that a straddling run cannot present a
   partly-frozen total as a live one.**
5. **`CLOSED_PERIODS_UNREADABLE` IS A 503 AND A 404/400 IS AN HONEST EMPTY.** My
   argument: a failed read treated as "nothing is closed" silently unfreezes
   every paid period, which is the louder failure. Arms F15/F16 pin both. **Check
   the direction is right** — it refuses a pay run on a settings-table blip.

**Evidence:** `api/b16-paid-period-freeze.test.js`, 17 arms, exit 0.
RED before the fix: 3 passed / 6 failed / 1 unproven —
`docs/hank-evidence/b16/red_freeze.log`. The ablation (F10) neuters the as-of
comparison and F1 returns to 300 minutes.

---

## 2. (b) — the EVV/pay agreement, as built

`api/_lib/sen-evv-readiness.js` element 6 (time the service begins and ends)
now reads `senEvvClock.effectiveClock(...)`. `sairnsenior.html` gained
`senEvvException(v)` — one predicate, consulted by both the filter and the row
label, which previously carried the condition twice.

**GPS DELIBERATELY DID NOT MOVE.** A correction supplies a time and never a
location. Arm E5 asserts the GPS elements still read the raw
`clock_*_lat`/`clock_*_lng` and that **no** time element reads a raw clock field.

**WHAT I WANT ATTACKED:**

1. **A CORRECTED CLOCK-OUT WITH NO GPS NOW SURFACES AS A GPS EXCEPTION RATHER
   THAN A TIME-SPAN ONE.** That is a visible behaviour change in the compliance
   panel and I think it is correct — the visit really has no clock-out
   coordinate — but it changes what a surveyor is shown.
2. **THE FREEZE AND THE EVV CHECK DELIBERATELY DISAGREE ON A CLOSED PERIOD.**
   Pay reads as at `paid_at`; the EVV check reads now. Arm E8 pins it and
   requires `period_closed` to name the instant. **Decide whether a deliberate
   disagreement is acceptable when the thing disagreeing is a federally
   mandated export.**
3. **`require()` IN A SECOND "PURE" MODULE.** Same question as (c) below, now
   in two files rather than one.

**Evidence:** `api/b16-evv-pay-agreement.test.js`, 9 arms, exit 0. RED before:
2 passed / 6 failed / 1 unproven — `docs/hank-evidence/b16/red_evv_pay.log`.
Ablation E9 reverts the clock-out read to the raw field and E1 returns to "no
clock-out time recorded".

---

## 3. (c) — the two halves

### The throw question: MEASURED, and the answer is no

Arm **F17** drives `computePayroll` with **15 hostile row shapes** — `null`,
`undefined`, `0`, `''`, a string, `true`, `[]`, a non-array
`clock_corrections`, entries containing `null`/`undefined`/`0`/`'x'`, an entry
with `proposed_at: null`, one with `proposed_at: {}`, one with
`approved_at_server: {nope:1}`, and a numeric `scheduled_date`. **No throw; a
run comes back with `refused: null` and a caregivers array.**

Why the arm exists rather than a reading of the source: **`computePayroll` has
no per-visit `try/catch`**, so a throw inside the substitution does not exclude
one visit, it fails the pay run for every caregiver in the period. That is the
obligation's own phrasing and it is right.

**What F17 does NOT prove:** it is 15 shapes I thought of, not a property. A
fuzz over generated shapes would be stronger and I did not write one.

### The purity question: STILL OPEN, and now twice

`api/_lib/sen-payroll.js` and now `api/_lib/sen-evv-readiness.js` both
`require('./sen-evv-clock')`, and both headers claim purity. My argument is in
both files in the same words: `sen-evv-clock.js` is itself pure — no fetch, no
I/O — and what is imported is the single function that decides which clock
value is in effect; the alternative is a second copy of the approval rule in a
file that computes wages, and a third in a file that produces a compliance
verdict.

**That argument is mine and it is the thing to attack.** Specifically: whether
"pure" in those headers was ever meant to mean "no imports" rather than "no
I/O", and whether a reader of either header would now be misled. **I did not
edit either header's purity claim**, which may itself be the defect.

---

## 4. One more thing, recorded rather than routed

**The one-person-agency self-approval exception is STILL UNBUILT, by decision.**
A one-person agency has no route to make any clock correction effective, because
`approveCorrection` refuses the filer as approver. Michael's standing position
is that it stays unbuilt and is recorded for the **home-care practitioner
question H8** — see `docs/2026-10-15-hank-b16-h8-self-approval.md`. It is not a
question for fourth and is listed here only so the review does not re-find it as
a gap.

---

## 5. What this document does not claim

* **Not that the obligation is discharged.** It is fourth's and it is open.
* **Not that my own arms are a review.** Every arm here was written by the same
  session that wrote the code, which is the exact reason the obligation exists.
* **Not that the freeze has ever run against real data.** No agency has a
  `payroll_closed_periods` row; the mechanism is driven only by fixtures and by
  the real handler with a stubbed upstream.
* **Not any live verification.** See the b16 report.
