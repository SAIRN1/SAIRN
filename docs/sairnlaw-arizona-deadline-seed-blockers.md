# Arizona deadline seed — gate result, and what was established

**2026-08-25, Hank.** Arizona was gated alongside Washington. **Washington passed
and is seeded. Arizona did not pass, and is not seeded.** This file records the
gate result, the verbatim text that was obtained anyway, and the specific,
bounded work that would make Arizona buildable.

Arizona is a **near miss**, not a Kentucky-style dead end, and the difference
matters — read the "How this differs from Kentucky" section before deciding.

---

## The gate result

The gate asks one question: **are this state's civil rules published free and in
full, in their current form, by an official source?**

For Arizona the answer is **no, not in their current form.**

- `azcourts.gov/rules` — the Arizona Judicial Branch's own rules page — links out
  to **`azrules.westgroup.com`**, which redirects to `govt.westlaw.com/azrules`.
  The maintained, current compilation is Thomson Reuters'. This is the same
  structure that blocked Kentucky, and it was not scraped, for the same reason:
  a commercial publisher's terms were not read, and this platform has already
  declined to route around BAILII's and AustLII's prohibitions with better
  tooling.
- What azcourts.gov *does* host free is the **2017 restyled rules** as a
  119-page PDF, plus a 256-page copy on `rulesforum.azcourts.gov`. Both were
  downloaded and both are real, complete rule text. **Neither is dated as
  current, and both are petition/agenda attachments rather than a maintained
  compilation.**

**The snapshot is demonstrably stale for four of the six rules a seed needs.**
azcourts.gov also publishes a maintained, official, per-rule amendment list at
`azcourts.gov/rules/recent-amendments/rules-of-civil-procedure`, and it shows:

| Order | Rules touched | Effective |
|---|---|---|
| **R-17-0010** | "Rules 5.1, 8, 8.1, 11, 16, 26, 26.1, 26.2, 29, 30, **33-37**, 38.1, 45, and 84" | after the 2017 restyling |
| **R-20-0028** | **Rule 12**, "to require good faith consultation before filing certain Rule 12 motions" | 2021-01-01 |

So Rules 12, 33, 34 and 36 — the answer rule and all three discovery rules — have
been amended since the free snapshot was written. Rules 5 and 6 show no
post-restyling amendment on that list.

**And the amendment list itself stops at 2024.** Its most recent entries are
effective 2024-01-01. Secondary commentary refers to "2025 amendments to the
Arizona Rules of Civil Procedure", which this page does not appear to cover, so
even reconstruction from the list would carry an unknown 2025–2026 gap.

---

## How this differs from Kentucky — read before deciding

Kentucky had **no free base text at all**; there was nothing to build on. Arizona
has a complete free official base text and a maintained free official amendment
index. The gap is narrow and specific:

> apply R-17-0010 and R-20-0028 to the 2017 text for Rules 12 and 33–36, and
> close the 2025–2026 coverage gap in the amendment list.

Both orders are free on azcourts.gov. That is real work but it is bounded, and
unlike Kentucky it does not require anyone's permission.

**Why it was still failed rather than attempted:** reconstruction cannot prove
its own completeness. Confirming "no other order touched Rule 33" requires a
complete order list, and the list on hand demonstrably stops two years short. A
rule seeded from a reconstruction that missed an amendment would produce wrong
dates with no refusal — the failure mode this engine exists to prevent. The same
reasoning was applied to Kentucky and is applied here for consistency, not
because the two states are equally blocked.

### Options for unblocking, in order

1. **Read Westlaw's terms of use for the free state-government sites.** If they
   permit on-demand retrieval of a handful of named documents — as The National
   Archives' Open Justice Licence does for Find Case Law, which this platform
   already relies on — then fetching six rules is inside the permission and
   Arizona is immediately buildable. This is the same first step recommended for
   Kentucky and would resolve both states at once.
2. **Buy the book.** *Arizona Rules of Court* (Thomson West) read by a human is
   not a licensing question.
3. **Reconstruct, but only after closing the 2025–2026 gap** in the amendment
   list by another official route.

---

## What WAS established, verbatim, and is reusable

All from free official sources. If Arizona is unblocked, this is a head start.

### Arizona restyled its civil rules effective 2017-01-01

The 2017 amendments "restyle the ARCP in a manner similar to the 2007 restyling
of the" federal rules, and where an Arizona rule did not differ substantively
"these amendments adopt the restyled federal wording verbatim". Anything written
about Arizona civil procedure before 2017 should be re-read before use.

### Rule 6 — read verbatim, and it is NOT the federal shape

> **(a) Computing Time.** The following rules apply in computing any time period
> specified in these rules or in any local rule, court order, or statute:
> **(1) Day of the Event Excluded.** Exclude the day of the act, event, or
> default that begins the period.
> **(2) Exclusions if the Deadline Is Less Than 11 Days.** Exclude intermediate
> Saturdays, Sundays, and legal holidays if the period is less than 11 days.
> **(3) Last Day.** Include the last day of the period unless it is a Saturday,
> Sunday or legal holiday. When the last day is excluded, the period runs until
> the next day that is not a Saturday, Sunday or legal holiday.
> **(4) Next Day.** The "next day" is determined by continuing to count forward
> when the period is measured after an event and backward when measured before
> an event.

Three things to carry forward:

- **The short-period exclusion is ELEVEN days**, not the seven used by Ohio,
  Indiana, Georgia, North Carolina and Washington. Arizona kept a threshold the
  federal rules abolished in 2009, and set it higher than any state seeded so
  far. Encoding 7 here would be wrong on every Arizona period of 7–10 days.
- **(a)(4) defines the backward direction expressly**, like W. Va. R. Civ. P.
  6(a)(5) and Fla. 2.514(a)(5) and unlike North Carolina and Washington. Arizona
  backward rows would be seedable where theirs were not.
- Rule 6(a) says "legal holiday" and — on the text read — **does not name a
  statute**. That puts Arizona in the Texas/Kentucky category on the holiday
  question, and it should join the bundled lawyer's question rather than being
  resolved state-by-state. The candidate is A.R.S. § 1-301, which was **not**
  read for this note.

### Rule 6(c) — FIVE days, and the federal sequencing

> **(c) Additional Time After Service Under Rule 5(c)(2)(C), (D), or (E).** When
> a party may or must act within a specified time after service and service is
> made under Rule 5(c)(2)(C), (D), or (E), 5 calendar days are added after the
> specified period would otherwise expire under Rule 6(a). This rule does not
> apply to the clerk's distribution of notice of entry of judgment under Rule
> 58(e).

- **FIVE days, not three.** Only Florida's five (Fla. R. Gen. Prac. & Jud.
  Admin. 2.514(b)) matches; every other seeded state adds three, and California
  varies by method.
- **"after the specified period would otherwise expire"** — the *federal*
  after-expiry order, unlike Washington, North Carolina, New York and Georgia,
  which all lengthen the period. Six states, and the split is now roughly even;
  there is still no default.
- The Rule 58(e) carve-out is express and would need its own row-level note.
- **Which methods (C), (D) and (E) actually are was not read** — Rule 5(c)(2) was
  not retrieved. Note that Arizona has renumbered around here before
  (R-14-0003 amended "Rules 5(c)(2) and 6(e)"), and West Virginia's live defect
  is exactly an unrenumbered cross-reference of this kind. **Read 5(c)(2) against
  the current text before encoding any method, and check whether 6(c)'s pointers
  still match.**

### Sources

- 2017 restyled rules (free, official, undated):
  `https://www.azcourts.gov/DesktopModules/ActiveForums/viewer.aspx?portalid=0&moduleid=23621&attachmentid=3200`
- Second copy, 256pp:
  `https://rulesforum.azcourts.gov/DesktopModules/ActiveForums/viewer.aspx?portalid=4&moduleid=9811&attachmentid=3261`
- Maintained amendment index (free, official, ends 2024):
  `https://www.azcourts.gov/rules/recent-amendments/rules-of-civil-procedure`
- The Westlaw redirect the court's own rules page points at:
  `http://azrules.westgroup.com/` → `https://govt.westlaw.com/azrules/Index`

---

## Recommended next action

Bundle the Westlaw terms question for **Kentucky and Arizona together** — one
answer unblocks both, and both are otherwise ready to build. Add Arizona's
undefined "legal holiday" to the existing four-jurisdiction bundled lawyer's
question. Do not seed Arizona from the 2017 snapshot alone, and do not encode a
seven-day short-period exclusion by analogy to its neighbours.
