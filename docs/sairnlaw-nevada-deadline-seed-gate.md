# Nevada — deadline-seed source-availability gate

**Run 2026-08-27. Verdict: PASS, and it is the strongest gate result so far.
Nevada is the SECOND state to answer the weekend-coverage check at step one,
the FIRST whose holiday list is fully derivable with the observation shift in
the SAME statute, and the source prints its own amendment cut-off date on page
one. It also passes the specific check that caught West Virginia — its
Rule 5(b)(2) lettering and Rule 6(d)'s parentheticals agree. Seed it.**

Nevada (~3.2M), the largest state with neither a seed nor a gate document after
Utah and Iowa. Rules of court are the **Nevada Rules of Civil Procedure**,
adopted by the Supreme Court of Nevada and substantially restyled on the
federal model effective 1 March 2019.

---

## 1. Sources — the best currency statement of any state gated

```
leg.state.nv.us/courtrules/NRCP.html   200, 524,109 B, real HTML
leg.state.nv.us/NRS/NRS-236.html       200,  63,386 B, real HTML
```

Free, official, plain `curl` — **no user-agent, no `Accept` header, no PDF
extraction, no browser.** Rules and statutes from the same publisher, like
Minnesota.

**The header answers the currency question outright**, which no other gated
source has done:

> Nevada Rules of Civil Procedure **[Rev. 4/15/2026 …--2025]** … ADOPTED BY THE
> SUPREME COURT OF NEVADA … Effective January 1, 1953 and **Including
> Amendments Through October 31, 2025**

A revision stamp *and* an explicit amendment cut-off. Contrast the three source
traps found the previous day: Utah's `legacy` hostname that was current anyway,
Utah's 200-with-an-error-body, and Iowa's dated URL that returns the same bytes
for every date including future ones. **Nevada simply tells you.**

## 2. THE WEEKEND-COVERAGE STANDING CHECK — step one, like Utah

**NRCP 6(a)(1)(C)**, verbatim:

> include the last day of the period, but **if the last day is a Saturday,
> Sunday, or legal holiday**, the period continues to run until the end of the
> next day that is not a Saturday, Sunday, or legal holiday.

Both weekend days named in the rollover clause itself. `isWeekend()` is correct
on the rule's own words; no holiday statute is consulted for the weekend
question and there is no statewide-coverage sub-question.

**The seven answers now on record:**

| State | Answer |
|---|---|
| Louisiana | rolls only on a "legal holiday"; the statute covers neither day everywhere → **LATE → BLOCKED** |
| Oklahoma | 25 O.S. § 82.1(A) opens "Each Saturday, Sunday", statewide → safe, via the statute |
| Oregon | ORCP 10 A names "a Saturday or a legal holiday, including Sunday" → safe, via the rule |
| Connecticut | keys purely on clerk's-office closure; no holiday list exists → **premise fails** |
| Utah | URCP 6(a)(1)(C) names both days → **safe at step 1** |
| Iowa | **splits by deadline type** — sentence one rolls Sunday only → **BLOCKED** |
| **Nevada** | **NRCP 6(a)(1)(C) names both days → safe at step 1** |

## 3. Counting — days are days, backward is real

**NRCP 6(a)(1)(B)**: *"count every day, **including intermediate Saturdays,
Sundays, and legal holidays**"* — the 2009-federal rule, stated affirmatively.
`short_period_exclusion_days` must be **ABSENT, not zero**.

**NRCP 6(a)(5)**: the "next day" is found by *"continuing to count forward when
the period is measured after an event and **backward when measured before an
event**"* — a real backward citation, like Utah and Minnesota, unlike the blank
NJ/NC/WA/MA/MO/WI carry.

**NRCP 6(a)(3)**: the clerk's-office **inaccessibility** limb is **ADDITIONAL
to** the Saturday/Sunday/holiday rollover, not a replacement for it — Minnesota's
6.01(a)(4) shape, **not** Wisconsin's. Omitting it can only report EARLY.

**NRCP 6(a)(4)(A)**: for electronic filing the last day ends at **11:59 p.m.**
in the court's local time. A filing cutoff, not a deadline shift — it does not
change the date this engine reports.

**NOT MODELLABLE: NRCP 6(a)(2)** states periods in hours with its own
hour-granular rollover. No hours unit exists in this engine.

## 4. The holiday list is FULLY DERIVABLE — and carries three traps

**NRCP 6(a)(6)**: *"'Legal holiday' means any day set aside as a legal holiday
by **NRS 236.015**."* A clean single pointer — no list inside the rule to
reconcile against the statute, which is what made Utah's Juneteenth question
messy.

**NRS 236.015(1)**, the complete list: New Year's Day (Jan 1); MLK (third Monday
in January); Washington's Birthday (third Monday in February); Memorial Day
(last Monday in May); **Juneteenth Day (June 19)**; Independence Day (July 4);
Labor Day (first Monday in September); **Nevada Day — "October 31 but is to be
observed on the last Friday in October"**; Veterans Day (Nov 11); Thanksgiving
(fourth Thursday in November); **Family Day — "Friday following the fourth
Thursday in November"**; Christmas (Dec 25); plus any presidentially appointed
day of public fast or thanksgiving.

**NRS 236.015(3)**, the observation shift:

> If **January 1, June 19, July 4, November 11 or December 25** falls upon a:
> (a) **Sunday, the Monday following** must be observed as a legal holiday.
> (b) **Saturday, the Friday preceding** must be observed as a legal holiday.

A **both-ways shift enumerated to exactly the five fixed-date holidays** —
Minnesota's shape. It is complete in practice: every other listed day is defined
by a weekday rule and can never land on a weekend. **Nevada is therefore
derive-not-ingest, with both halves in one statute** — a better position than
Utah, whose rule held the list while the statute held the shift.

### The three traps

1. **THERE IS NO COLUMBUS DAY.** NRS 236.025 puts Columbus Day under *PERIODS OF
   OBSERVANCE*, **not** under *HOLIDAYS*. Utah and West Virginia both make it a
   legal holiday, and the federal calendar has it. **Encoding it here would roll
   a deadline off a day that is a normal business day in Nevada — LATE.** Same
   for Indigenous Peoples Day (236.037), Cesar Chavez Day (236.027) and
   Nevada's two dozen other observance sections.
2. **JUNETEENTH IS JUNE 19, NOT THE THIRD MONDAY.** Utah's URCP 6(a)(6)(E) uses
   the third Monday. **In 2026 the two states are four days apart** — Nevada
   2026-06-19, Utah 2026-06-15. Two jurisdictions gated a day apart, opposite
   answers on the same holiday.
3. **TWO DAYS NO OTHER SEEDED STATE HAS: Nevada Day** (last Friday in October)
   and **Family Day** (the Friday after Thanksgiving). Missing either reports
   EARLY, which is safe — but Family Day in particular is the kind of day an
   analogy-driven calendar drops, since most states treat the day after
   Thanksgiving as an ordinary business day.

**Derived 2026 calendar — 12 days**, computed from the statute rather than
transcribed:

```
2026-01-01  New Year's Day            2026-09-07  Labor Day
2026-01-19  Martin Luther King, Jr.   2026-10-30  Nevada Day (last Friday)
2026-02-16  Washington's Birthday     2026-11-11  Veterans Day
2026-05-25  Memorial Day              2026-11-26  Thanksgiving Day
2026-06-19  Juneteenth Day            2026-11-27  Family Day
2026-07-03  Independence Day  <- Sat 4 Jul, shifted to the preceding Friday
2026-12-25  Christmas Day
```

**Year-boundary spill, same as Utah:** 1 January **2028** falls on a Saturday,
so it is observed **2027-12-31** and belongs in the 2027 calendar. A 2027
calendar built only from 2027's holidays is missing it.

**Ad hoc, EARLY, not encodable:** presidentially appointed days of public fast
or thanksgiving. Note the odd carve-out in the same sentence — *"except for any
Presidential appointment of the fourth Monday in October as Veterans Day"* — a
historical artefact with no current effect, since NRS 236.015 fixes Veterans Day
at November 11.

## 5. THE WEST VIRGINIA TRAP — checked, and Nevada does NOT have it

West Virginia's Rule 6(e) points at Rule 5(b)(2)**(F)** while labelling it
"(other means consented to)", which is the text of **(G)** — the pointer and the
parenthetical name different subparagraphs, and the two readings give opposite
answers on consented electronic service. That defect was found by reading
Rule 5. **The same read was run here, because Nevada's 6(d) is worded
identically.**

**Nevada's NRCP 5(b)(2) lettering, read directly:**

| | |
|---|---|
| (A) | handing it to the person |
| (B) | leaving it at the office / dwelling |
| **(C)** | **mailing it** — "in which event service is complete upon mailing" |
| **(D)** | **leaving it with the court clerk** if the person has no known address |
| (E) | the court's electronic filing system, or other **electronic** means consented to in writing |
| **(F)** | **delivering it by any other means that the person consented to in writing** |

**NRCP 6(d)** points at *"Rule 5(b)(2)(C) (mail), (D) (leaving with the clerk),
or (F) (other means consented to)"*. **Every pointer matches its parenthetical
exactly.** Nevada's (E) is the electronic subparagraph and (F) is
other-consented-means, which is the federal arrangement. **No ambiguity, nothing
to refuse.** Recorded as a checked negative rather than an unexamined one.

**The consequence is the same as West Virginia's and New York's, though:
ELECTRONIC SERVICE UNDER (E) TAKES NO EXTENSION**, because 6(d) does not list
it. That is the available mistake in Nevada practice — e-service feels like it
should behave like mail and does not.

## 6. The service extension — the federal triple, +3

**NRCP 6(d)**, verbatim:

> When a party may or must act within a specified time after being served and
> service is made under Rule 5(b)(2)(C) (mail), (D) (leaving with the clerk), or
> (F) (other means consented to), **3 days are added** after the period would
> otherwise expire under Rule 6(a).

**"Added after the period would otherwise expire"** — the federal
after-expiry order, so a second rollover runs, not the period-lengthening shape
Texas, New York and Georgia use. Same as `frcp_6d`.

**No exclusivity condition** — Utah's problem does not appear here. `applies_when`
is the plain `['mail', 'left_with_clerk', 'other_consented_means']` triple.

**Two service-completion facts worth recording but not modelling.** 5(b)(2)(C):
mail service *"is complete upon mailing"* — so no completion shift is needed and
a standard here would be dormant, exactly as in Utah. 5(b)(2)(E): electronic
service is complete on submission *"but is **not effective** if the serving
party learns that it did not reach the person to be served"* — a negative
condition the engine cannot see, which would push the period's start later and
therefore makes the engine's date EARLY. Safe, disclosable.

## 7. What is seedable — a full, ordinary row set

**NRCP 12(a)(1)** — the answer deadlines:
- **(A)(i) 21 days** after being served with the summons and complaint;
- **(A)(ii)** on a timely **waiver of service** under Rule 4.1, **60 days** after
  the request for a waiver was sent, or **90 days** if sent **outside the United
  States** — the federal shape, and the same in-/out-of-country split Virginia
  has;
- **(B) 21 days** to answer a counterclaim or crossclaim;
- **(C) 21 days** to reply to an answer, running from service of **an order to
  reply** — a court-action trigger, and the sentence adds *"unless the order
  specifies a different time"*.

**NRCP 12(a)(2) — the government row, and it is a `later_of`:** the State, its
public entities and political subdivisions, and their officers and employees
must answer *"within **45 days** after service on the party, **or if required
service on the Attorney General, whichever date of service is later**."* Two
trigger dates sharing **one** count — which is the engine's existing
`resolve: later_of` shape exactly, not the `resolve_periods` shape Georgia
needed. A clean fit.

**Discovery is uniform at 30 days**, read rule by rule rather than assumed from
the first: **NRCP 33(b)(2)** (*"must serve its answers and any objections within
30 days after being served with the interrogatories"*), **34(b)(2)(A)** (*"must
respond in writing within 30 days after being served"*), and **36(a)(3)** (*"A
matter is admitted unless, within 30 days after being served…"*).

**NO DEFENDANT FLOOR ON ANY DISCOVERY RULE.** Searched for *"may not seek
discovery"*, *"before the parties have conferred"* and *"not be served before"*:
**zero hits each**. Unlike Ohio, Indiana, Georgia, Massachusetts, Minnesota,
Missouri, North Carolina and Virginia, Nevada's discovery periods run purely
from service of the request. Reported as a searched-for absence.

**NRCP 16.1(j)(1)** — the **early case conference: 45 days after service of an
answer.** A real, ordinary, caller-suppliable deadline and an unusual one to
have available.

All three discovery rules and 12(a)(1)(C) carry *"a shorter or longer time may
be stipulated to under Rule 29 or be ordered by the court"* — a stipulation or
order the engine cannot see, the ordinary caveat.

## 8. Deliberately not seedable

**NRCP 15(a)(3)** — a response to an amended pleading is due *"within the time
remaining to respond to the original pleading **or within 14 days after service
of the amended pleading, whichever is later**."* One limb is a **COMPUTED
period** — the time remaining on a deadline this engine would have to derive
from a trigger it was never given. That is the Maryland chained-floor shape, and
the same reason two federal and two state appellate rules were left out. **Do
not seed it as a plain 14-day row**: whenever time remains on the original, the
true deadline is later and the row would report EARLY — safe, but it would be
answering a question nobody asked.

## 9. What was NOT determined

- **NRCP 4 and 4.1** (service of the summons; waiver mechanics), so what date a
  caller supplies for the 12(a)(1)(A) triggers — and what "the request for a
  waiver was sent" means precisely — is not yet sourced.
- **Rule 4.2(c)(3)(E)**, named in 12(a)(1) as an override, was not read.
- **NRCP 12(a)(3)**, named as an override on the government row, was not read.
- Whether **NEFCR 9** electronic service interacts with 6(d) in any way the rule
  text does not show.
- Appellate rules (NRAP) were not opened.
- **NRS 293.560 and 293C.527**, the election-related carve-outs in
  NRS 236.015(2), were not read. They govern office closure rather than the
  holiday list, so they most likely do not bear on the calendar — but that is an
  inference, not a reading.

## 10. Verdict

**PASS, and the recommendation is to seed.** Free official rules and statutes
from one publisher on a bare `curl`; a source that states its own amendment
cut-off; a rollover clause naming both weekend days; days-are-days with no
short-period exclusion; backward counting expressly defined; a holiday list and
its observation shift in the same statute, fully derivable; a real answer
deadline; uniform 30-day discovery with no floor; and the federal +3 extension
with no exclusivity condition.

**Three things to get right when seeding, all traps of analogy rather than of
law:** no Columbus Day; Juneteenth on **June 19**, not the third Monday; and
**Nevada Day and Family Day**, which no other seeded state has. Build the
calendar with a generator that asserts them, and carry the 2028→2027-12-31 spill
if the range is ever extended past 2026.
