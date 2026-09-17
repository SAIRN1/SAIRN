# Ohio — deadline-seed source-availability gate

**Run 2026-09-17 (Fourth).** Verdict at §10.

**Why Ohio and not the next-largest unseeded state.** Every unseeded state was
compared on ONE criterion that is a fact about this repo rather than about the
state: whether the engine already carries its computation standard. Ohio is the
only one where the answer is yes and the standard is *already exercised in
production* — `ohio_civ_r_6a` has been a first-class entry in
`COMPUTATION_STANDARDS` since before this gate, and **Massachusetts
(`ma_rcp_6a`) and Missouri (`mo_rule_44_01_a`) both run on it today**
(`api/_lib/deadline-engine.js:499,1325,1367`). So Ohio is the one unseeded
jurisdiction whose engine work is zero and whose mechanism has live test
coverage under two other states' suites before a single Ohio row exists.

Indiana and Michigan standards also exist (`indiana_tr_6a`, and MCR 1.108 mapped
to `frcp_6a`) but neither is reached by any seeded jurisdiction, so their
implementations have never been exercised. That is a weaker position than
Ohio's, not an equal one, and it is the reason those two are not this pick.

**AND THE ENGINE ENTRY WAS RE-VERIFIED AGAINST SOURCE RATHER THAN TRUSTED.**
It would be circular to gate Ohio on a standard named "ohio" without reading
whether it matches Ohio. `short_period_exclusion_days: 7` is compared with a
STRICT less-than at the call site (`countValue < std.short_period_exclusion_days`,
noted at `deadline-engine.js:719-720`), and Civ.R. 6(A) says *"less than seven
days"*. Those agree. This is the same habit the Indiana entry records in its own
comment — a shared threshold is not evidence of a shared rule.

---

## 1. Sources — PASS, and the civil rules are the freshest text of any state gated

| Source | Location | Terms | Currency |
|---|---|---|---|
| Ohio Rules of Civil Procedure | `supremecourt.ohio.gov/docs/LegalResources/Rules/civil/CivilProcedure.pdf` | none — direct PDF, no click-through, no account | **Rule 6 amended July 1, 2026** |
| Ohio Revised Code (holidays, computation) | `codes.ohio.gov/ohio-revised-code/section-1.14` | none — official state site | effective **September 30, 2021** (H.B. 110, 134th G.A.) |
| Supreme Court of Ohio filing-holiday page | `supremecourt.ohio.gov/opinions-cases/office/holiday-filing-rule/` | none | lists 2026 and 2027 observances |

**Retrieved, not cited from a secondary source.** The rules PDF was downloaded
and read: 28,565,669 bytes, 895 pages, `sha256 643aa2c16fa7057e…`. Rule 6 and
Rule 5(B)(2) below are quoted from that file, not from a rules aggregator. Four
aggregator copies of Civ.R. 6 were visible in search results and **none was
used** — the Tennessee gate's finding is that a neighbour's text carried across
is how a seed gets corrupted, and an aggregator is the same problem one step
further out.

**No click-through anywhere.** This is the cleanest access position since
Nevada, and it is the point on which Tennessee, Arizona, Kentucky and Colorado
all failed or stalled.

---

## 2. THE WEEKEND-COVERAGE STANDING CHECK (row 400) — step one

Civ.R. 6(A), verbatim:

> "The last day of the period so computed shall be included, **unless it is a
> Saturday, a Sunday, or a legal holiday**, in which event the period runs until
> the end of the next day which is not a Saturday, a Sunday, or a legal holiday."

| State | Answer |
| --- | --- |
| Louisiana | rolls only on a "legal holiday"; covers neither day everywhere — **LATE, BLOCKED** |
| Connecticut | keys purely on clerk's-office closure; no holiday list — **premise fails** |
| Iowa | **splits by deadline type** — **BLOCKED** |
| Nevada | NRCP 6(a)(1)(C) names both days — safe at step 1 |
| **Ohio** | **Civ.R. 6(A) names both days, in the rule itself — SAFE AT STEP 1** |

**BUT STEP ONE IS NOT THE WHOLE ANSWER HERE, AND OHIO IS THE FIRST STATE WHERE
IT IS NOT.** Ohio has a *second* computation provision, and it disagrees.

**R.C. 1.14**, verbatim:

> "The time within which an act is required by law to be done shall be computed
> by excluding the first and including the last day; except that, **when the
> last day falls on Sunday or a legal holiday**, the act may be done on the next
> succeeding day that is not Sunday or a legal holiday."

**Saturday does not appear in R.C. 1.14 anywhere** — confirmed by reading the
section, not inferred from its summary. So Ohio has a rule that rolls Saturday
and a statute that does not, and *which one governs depends on where the period
came from.*

**WHY THIS IS A DISCLOSURE AND NOT A BLOCKER, stated so the reasoning can be
argued with rather than taken on trust.** Three things converge:

1. **Civ.R. 6(A) claims statutory periods by its own terms** — it applies to a
   period prescribed "by these rules, by the local rules of any court, by order
   of court, **or by any applicable statute**." Inside a civil action it is the
   operative provision.
2. **R.C. 1.14's own office-closed sentence lands on the same day anyway.** If
   the last day is a Saturday and the clerk is closed, the act "may be performed
   on the next succeeding day that is not a Sunday or a legal holiday" — Monday.
   The two provisions reach Monday by different routes.
3. **The disagreement therefore has no reachable input inside this engine's
   scope** (civil litigation deadlines with a court clerk as the filing office).

**WHAT IS NOT CLAIMED:** that Civ.R. 6(A) enlarges a substantive limitations
period. Ohio Const. art. IV §5(B) bars a procedural rule from abridging a
substantive right, and whether a statute of limitations expiring on a Saturday
is governed by Civ.R. 6(A) or by R.C. 1.14 **is a lawyer's question and is not
answered here.** It goes in the bundled question of row 394 alongside the
Illinois and Kentucky holiday questions, not into a rule row.

---

## 3. Counting — the short-period exclusion, and it is already built

> "When the period of time prescribed or allowed is **less than seven days**,
> intermediate Saturdays, Sundays, and legal holidays shall be excluded in the
> computation."

Strict less-than, threshold seven. Already `short_period_exclusion_days: 7` on
`ohio_civ_r_6a`. **Nothing to build.**

---

## 4. The holiday list — derivable, with ONE discretionary limb and ONE partial day

R.C. 1.14 enumerates (A)–(L). Eleven are formula-derivable with no published
list: New Year's (1 Jan), Martin Luther King (3rd Mon Jan), Washington-Lincoln
(3rd Mon Feb), Memorial (per 5 U.S.C. 6103), Juneteenth (19 Jun), Independence
(4 Jul), Labor (1st Mon Sep), Columbus (2nd Mon Oct), Veterans' (11 Nov),
Thanksgiving (4th Thu Nov), Christmas (25 Dec).

**TRAP 1 — (L) is DISCRETIONARY.** A day "appointed and recommended by the
governor" or by the president. No readable signal, not derivable, and this is
the Alabama shape. **Direction is EARLY and therefore disclosed, not refused:**
an unforeseen holiday makes the true deadline *later*, so an engine that does
not know about it returns a date **before** the real one. Filing early is safe.

**TRAP 2 — THE HOLIDAY'S OWN WEEKEND SHIFT IS ASYMMETRIC, AND THE TWO
AUTHORITIES DISAGREE IN THE DANGEROUS DIRECTION.**

- **R.C. 1.14**: if a designated holiday falls on **Sunday**, the next
  succeeding day is a legal holiday. **There is no Saturday clause.**
- **Supreme Court of Ohio, Rules of Practice 3.03(A)(3)** (its filing-holiday
  page): "If a holiday falls on a Saturday, the holiday shall be observed on the
  immediately preceding Friday. If a holiday falls on a Sunday, the holiday shall
  be observed on the immediately ensuing Monday."

So for a July 4 that falls on a Saturday: the preceding Friday is a holiday for
**Supreme Court of Ohio filings** and, on the statute's plain text, an ordinary
business day everywhere else.

**THE MODELLING DECISION FOLLOWS FROM THE DIRECTION AND IS MADE HERE:** the
Ohio calendar **must NOT apply a Saturday-to-Friday observance shift.** If it
did and the statute governs, the engine would treat Friday as a holiday, roll
the deadline to Monday, and **compute LATE** — a filing made on the engine's
date would be out of time. Omitting the shift fails the other way: where the
Supreme Court's practice rule does govern, the engine returns Friday when the
true date is Monday, which is early. **Early is the only acceptable error
here,** and this is the same call the Georgia frozen-calendar row records for
the same reason.

The Sunday-to-Monday shift **is** modelled — both authorities agree on it.

**TRAP 3 — ELECTION DAY IS A PARTIAL-DAY HOLIDAY AND IS NOT IN R.C. 1.14.**
R.C. 5.20 makes the first Tuesday after the first Monday in November a legal
holiday **only between 12:00 noon and 5:30 p.m. eastern time**. It is not one of
R.C. 1.14's lettered items. A whole-day calendar cannot express "holiday for
five and a half hours", and this engine has no field for it. **Election Day is
NOT marked a holiday in the Ohio calendar, and that is disclosed rather than
silently decided** — marking it would roll deadlines forward a day on a
half-day basis and could compute LATE.

**R.C. 5.23 was read and is irrelevant** — it is the schools-commemoration
section (Lincoln's birthday, Washington's birthday, Memorial Day, Veterans' Day
"shall be commemorated in the schools") and creates no filing holiday. Recorded
because its number sits beside 5.20 and a future reader will otherwise re-check
it.

---

## 5. THE WEST VIRGINIA TRAP — checked, and Ohio does NOT have it

West Virginia's R. Civ. P. 6(e) points at a subparagraph that contradicts its
own parenthetical. Ohio's equivalent was checked the same way — by reading the
pointer AND the target, not the pointer alone.

Civ.R. 6(D) extends time for service "by mail or commercial carrier service
**under Civ.R. 5(B)(2)(c) or (d)**". Civ.R. 5(B)(2), verbatim:

| | |
| --- | --- |
| (a) | Handing it to the person |
| (b) | Leaving it at the office / dwelling |
| **(c)** | **Mailing it** to the last known address by United States mail — "service is complete upon mailing" |
| **(d)** | **Delivering it to a commercial carrier service** for delivery within three calendar days — "complete upon delivery to the carrier" |
| (e) | Leaving it with the clerk of court if the person has no known address |
| (f) | Electronic means — "complete upon transmission, but is not effective if the serving party learns that it did not reach the person served" |

**(c) is mail. (d) is commercial carrier. The pointer and the parenthetical
agree exactly.** No trap.

---

## 6. The service extension — +3, mail and carrier only, and it ANSWERS ROW 412

Civ.R. 6(D), verbatim:

> "Whenever a party has the right or is required to do some act or take some
> proceedings within a prescribed period after the service of a notice or other
> document upon that party and the notice or paper is served upon that party by
> mail or commercial carrier service under Civ.R. 5(B)(2)(c) or (d), **three
> days shall be added** to the prescribed period. **This division does not apply
> to responses to service of summons under Civ.R. 4 through Civ.R. 4.6.**"

Three facts, each load-bearing for a seed row:

1. **+3 days, mail and commercial carrier only.** Electronic service under
   (B)(2)(f) gets nothing — Ohio reached the same place as the 2016 federal
   amendment. Personal service, office/dwelling and clerk-deposit get nothing.
2. **NO EXTENSION ON THE ANSWER TO A COMPLAINT, SAID IN THE RULE ITSELF.** This
   is the exact question open-work row 412 raises against the `us-federal` seed,
   where the answer-to-complaint row attaches an FRCP 6(d) extension for service
   of *process* and would compute **three days late** if that is wrong. **Ohio
   does not leave it to inference** — the last sentence excludes Civ.R. 4
   through 4.6 in terms. The Ohio answer-to-complaint row therefore carries **no
   `service_extension`**, and that is a quotation rather than a judgment call.
   **This does not resolve row 412**, which is about the federal rule; it
   removes any temptation to carry the federal shape across to Ohio.
3. **Rule 6 has no division (E).** Confirmed by reading to the end of the rule:
   it runs (A) through (D) and then the effective-date line. The old Civ.R. 6(E)
   was re-lettered to 6(D) in the July 1, 2012 amendment, and the staff note in
   the PDF says so. **Anything citing "Ohio Civ.R. 6(E)" for the three-day rule
   is citing a rule that has not existed for fourteen years** — recorded because
   several secondary sources still do.

**Sequencing (row 440).** Two of three states checked did not follow the federal
order. Ohio's +3 is expressed as added "to the prescribed period", i.e. the
extension is applied to the period **before** the Civ.R. 6(A) weekend/holiday
rollover — the federal order. **Stated as a reading of one sentence, not as a
verified Ohio holding**, and it goes in the seed `_readme` as such.

---

## 7. What is seedable

An ordinary full row set: computation standard `ohio_civ_r_6a` (built),
holiday calendar from R.C. 1.14 minus the two traps at §4, motion-response rows
straight from Civ.R. 6(C) (14 days for a motion, **28 days for summary
judgment**, 7 days for a movant's reply — all quotable verbatim), the Civ.R.
6(D) service extension on the rows that take one, and no engine change of any
kind.

---

## 8. What was NOT determined — the appellate side

**The Ohio Rules of Appellate Procedure were not read.** App.R. 4 (time for
appeal) and App.R. 14 (computation and the appellate service extension) live in
a different PDF that was not downloaded, and **every appellate row is therefore
out of scope for this gate.** Named rather than estimated: three states in this
series had an appellate rule that differed from the civil one, and assuming
App.R. 14 mirrors Civ.R. 6(D) is exactly the carry-across the Tennessee gate
warns about. A seed may ship trial-court rows with no appellate rows; it may not
ship appellate rows on this document.

Also undetermined: whether Civ.R. 6(A) or R.C. 1.14 governs a substantive
limitations period expiring on a Saturday (§2), and whether any county's local
rules narrow Civ.R. 6(C)'s response periods — local rules are expressly
contemplated by Civ.R. 6(A) and this engine has no per-county layer.

---

## 9. Verdict

**GATE PASSED.** Sources are official, free of terms, and the civil rules text
is current to 1 July 2026. The weekend-coverage standing check is safe at step
one. The West Virginia trap is absent. The engine needs no change. Three traps
are identified, and **each one's direction was determined before deciding what
to do about it** — (L) discretionary and the Saturday-observance omission both
fail EARLY by construction, and Election Day is excluded for the same reason.

**Seeding may proceed for trial-court rows.** Appellate rows are blocked on
§8 and need the appellate rules read first.
