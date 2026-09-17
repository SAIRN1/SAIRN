# Michigan — deadline-seed source-availability gate

**Run 2026-09-17 (Fourth).** Verdict at §9.

**Picked on the same criterion as Ohio, applied honestly to what was left.** Of
the unseeded states, only two have a computation standard already in the engine:
Indiana (`indiana_tr_6a`) and Michigan (`michigan_mcr_1108`). Ohio was chosen
because its standard was already *exercised in production*. By that same test
**Michigan wins and Indiana does not**: `michigan_mcr_1108` maps to the
`frcp_6a` IMPLEMENTATION, which **34 computation standards on this platform
already run on**, while `indiana_tr_6a` has its own implementation that no
seeded jurisdiction reaches and that has therefore never executed against a real
rule set. Same criterion, opposite answers, and the reason is stated so the next
picker does not have to re-derive it.

---

## 1. Sources — PASS, and the rules text is the freshest yet gated

| Source | Location | Terms | Currency |
|---|---|---|---|
| Michigan Court Rules of 1985 | `courts.michigan.gov/…/michigan-court-rules.pdf` | none — direct PDF, no click-through, no account | **updated 31 July 2026**; chapter footers read "Chapter Updated September 1, 2026" |
| MCL 435.101 (legal holidays, Act 124 of 1865) | `legislature.mi.gov/Laws/MCL?objectName=mcl-435-101` | none — official state site | last amended **2023 PA 54, imd. eff. 12 July 2023** |

**Retrieved and hashed, not cited from an aggregator.** The rules PDF was
downloaded and read: **9,897,972 bytes, `sha256 31ed59fbef8d2f17…`, 875 pages.**
Every rule quoted below comes from that file. Several rule-aggregator copies of
MCR 1.108 were visible in search and **none was used** — same discipline as the
Ohio gate, for the reason the Tennessee gate recorded.

---

## 2. THE WEEKEND-COVERAGE STANDING CHECK (row 400) — safe, and by the widest clause yet

MCR 1.108(1), verbatim:

> "The day of the act, event, or default after which the designated period of
> time begins to run is not included. The last day of the period is included,
> **unless it is a Saturday, Sunday, legal holiday, or day on which the court is
> closed pursuant to court order**; in that event the period runs until the end
> of the next day that is not a Saturday, Sunday, legal holiday, or day on which
> the court is closed pursuant to court order."

| State | Answer |
| --- | --- |
| Louisiana | rolls only on a "legal holiday" — **LATE, BLOCKED** |
| Iowa | **splits by deadline type** — **BLOCKED** |
| Ohio | Civ.R. 6(A) names both; R.C. 1.14 names only Sunday — safe, with a disclosure |
| **Michigan** | **names both days AND court-ordered closures — safe at step 1, and the widest of the set** |

---

## 3. Counting — and the engine already agrees with the rule's own examples

**NO SHORT-PERIOD EXCLUSION.** MCR 1.108 has no analogue of the federal or Ohio
"less than N days, exclude intermediate weekends" clause. The engine's entry
already records this as verified; it is re-verified here against the text.

**MCR 1.108(2), weeks:** "the last day of the period is the same day of the week
as the day on which the period began."

**MCR 1.108(3), months and years** — and this is the part worth quoting, because
**the rule supplies its own test cases**:

> "If what would otherwise be the final month does not include that day, the
> last day of the period is the last day of that month. For example, **'2 months'
> after January 31 is March 31, and '3 months' after January 31 is April 30.**"

**DRIVEN, NOT READ.** `api/_lib/deadline-engine.js`'s `addMonths` was executed
against both of the rule's own examples:

```
2 months after 2026-01-31 -> 2026-03-31    rule says 2026-03-31    MATCH
3 months after 2026-01-31 -> 2026-04-30    rule says 2026-04-30    MATCH
```

and `addDays('2026-01-31', 14)` lands on the same weekday it started on, which
is MCR 1.108(2). **The engine work for Michigan is zero and this is the
strongest evidence for that claim any gate in this series has had** — the rule
wrote the test cases and the engine passes them.

---

## 4. The holiday list — FULLY DERIVABLE, and the cleanest of any state gated

MCL 435.101 names twelve days, every one computable with no published list:

| Fixed date | Nth weekday |
|---|---|
| 1 Jan · **12 Feb (Lincoln's Birthday)** · 19 Jun · 4 Jul · 11 Nov · 25 Dec | 3rd Mon Jan · 3rd Mon Feb · last Mon May · 1st Mon Sep · 2nd Mon Oct · 4th Thu Nov |

**THERE IS NO GOVERNOR-OR-PRESIDENT LIMB.** Ohio has one (R.C. 1.14(L)),
Alabama has one, and both had to be disclosed as undetectable. **Michigan has
none**, so the statutory list is closed and derivable in full. That is the
cleanest holiday position in this series.

### Three traps, each with its direction determined first

**TRAP 1 — 12 FEBRUARY IS A MICHIGAN LEGAL HOLIDAY AND IS NOT A FEDERAL ONE.**
Lincoln's Birthday. A calendar generated from a federal holiday list — the
obvious shortcut, and the one the Georgia row records going wrong — silently
omits it, and a deadline landing on 12 February would be computed a day or more
**LATE**. Fixed date, trivially derivable, and the single most likely way to get
Michigan wrong.

**TRAP 2 — THE SUNDAY SHIFT IS ENUMERATED, NOT GENERAL.** MCL 435.101 shifts to
the next Monday only when **1 Jan, 12 Feb, 19 Jun, 4 Jul, 11 Nov or 25 Dec**
falls on a Sunday. **That enumeration was checked for completeness rather than
trusted: those six ARE exactly the six fixed-date holidays**, and an nth-weekday
holiday can never fall on a Sunday, so the rule is complete as written. Had one
fixed-date holiday been missing from that list it would have been a silent
one-day error every few years.

**AND THERE IS NO SATURDAY SHIFT AT ALL** — no counterpart to Ohio's
S.Ct.Prac.R. 3.03(A)(3) moving a Saturday holiday to the preceding Friday.
Here that is **inert rather than dangerous**, because MCR 1.108(1) rolls every
Saturday on its own terms: a deadline landing on a Saturday-falling holiday
rolls to Monday through the Saturday clause regardless. Ohio's equivalent had to
be modelled as an omission; Michigan's converges.

**TRAP 3 — THE SATURDAY HALF-HOLIDAY.** MCL 435.101 makes every Saturday from
noon to midnight a half-holiday. A whole-day calendar cannot express that, which
is the Ohio Election Day shape — **but again it is inert**, because MCR 1.108
rolls all of Saturday anyway. Named so nobody models it and thereby invents a
half-day.

---

## 5. THE SERVICE EXTENSION — THERE ISN'T ONE, AND THAT IS THE FINDING

**Michigan's court rules contain NO added-time-for-mail rule.** Searched the
875-page text for every spelling — "3 days added", "additional 3 days", "days
are added", "served by mail … add" — and the only hit is MCR 2.506 on **subpoena
witness fees**, which is unrelated. There is no FRCP 6(d), no Ohio Civ.R. 6(D),
no NRCP-style +3.

What Michigan has instead, MCR 2.107(C)(3):

> "Mailing a copy under this rule means enclosing it in a sealed envelope with
> first class postage fully prepaid … and depositing the envelope and its
> contents in the United States mail. **Service by mail is complete at the time
> of mailing.**"

**DO NOT CONFUSE THIS WITH MCR 2.108(A)(2).** That rule gives a defendant **28
days** rather than 21 when the summons and complaint are served outside Michigan
or by registered mail. That is a **different period for a different manner of
service**, not an extension added to a period — so it is its own rule row with
its own trigger, and it must NOT be encoded as a `service_extension`. Getting
that wrong would add three days to a period that already accounts for the
manner of service, and compute **LATE**.

**EVERY MICHIGAN ROW THEREFORE CARRIES NO `service_extension`**, as a
quotation from an absence that was searched for, not an assumption. This is a
direct contribution to the standing extension sweep (row 413).

**THE WEST VIRGINIA TRAP IS NOT APPLICABLE HERE, and that is said precisely
rather than reported as "absent".** That trap is a service-extension rule whose
subparagraph pointer contradicts its own parenthetical. Michigan has no
service-extension rule, so there is no pointer to check — a different answer
from "checked and clean", and recording it as the latter would overstate what
was done.

---

## 6. What is seedable

An ordinary full row set: computation standard `michigan_mcr_1108` (built, and
running on the platform's most-exercised implementation), a fully derivable
holiday calendar from MCL 435.101, answer periods straight from MCR 2.108(A)
(21 days in-state; 28 days outside Michigan or by registered mail; 28 days after
publication or posting; 21 days for a cross-claim, counterclaim or reply), and
**no service extension on any row**. No engine change of any kind.

---

## 7. What was NOT determined

**The Michigan Court Rules of Appellate Procedure (Chapter 7) were not read.**
MCR 7.204 (time for appeal) and MCR 7.208 are in the same PDF and were simply
not examined in this pass, so **every appellate row is out of scope** — the same
bound the Ohio gate set, for the same reason: assuming the appellate chapter
mirrors the civil one is precisely the carry-across the Tennessee gate warns
about, and "it was in the file I already had" is not a reason to believe it.

Also undetermined: whether any circuit's **local** rules narrow MCR 2.108's
periods; and the practical reach of MCR 1.108(1)'s "**day on which the court is
closed pursuant to court order**" limb. That limb is per-court and discretionary
with no readable signal — the Ohio R.C. 1.14(L) shape — and its direction is
**EARLY**: a closure the engine does not know about makes the true deadline
later, so the engine's answer is before the real one. Disclosed, not refused.

---

## 8. Verdict

**GATE PASSED.** Sources official, free of terms, and current to 31 July 2026.
The weekend standing check is safe by the widest clause in the series. The
holiday list is fully derivable with no discretionary limb — a first. The engine
reproduces the rule's own worked examples. Three traps identified, each with its
direction determined before deciding what to do, and two of the three turn out
inert because MCR 1.108 rolls Saturday on its own terms.

**The one that is not inert is Lincoln's Birthday**, and it is the whole reason
this state cannot be seeded from a federal holiday calendar.

**Seeding may proceed for trial-court rows.** Appellate rows are blocked on §7.
