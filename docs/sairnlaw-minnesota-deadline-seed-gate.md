# Minnesota — deadline-seed source-availability gate

**Run 2026-08-26. Verdict: PASS — the cleanest gate yet. One official free
source carries BOTH the rules and the statutes, no new engine mechanism is
required, and every open item fails EARLY.**

Minnesota (~5.8M) is the next unseeded state after Colorado. It is the first
state gated where **nothing had to be worked around**.

---

## 1. Sources — one host, both bodies of law, plain `curl`

The **Minnesota Office of the Revisor of Statutes** publishes the Rules of Civil
Procedure *and* the statutes on the same official site, all **HTTP 200 to plain
`curl`**:

```
revisor.mn.gov/court_rules/cp/id/6/     200   Rule 6 (Time)
revisor.mn.gov/court_rules/cp/id/12/    200   Rule 12 (answer)
revisor.mn.gov/court_rules/cp/id/33/    200   Rule 33 (interrogatories)
revisor.mn.gov/court_rules/cp/id/34/    200   Rule 34 (production)
revisor.mn.gov/court_rules/cp/id/36/    200   Rule 36 (admissions)
revisor.mn.gov/statutes/cite/645.44     200   § 645.44 subd. 5 (holidays)
```

**This is the first state where the rules and the statutes come from the same
free official publisher.** Wisconsin was close (civil procedure *is* statutory
there, so one site covers it) but Minnesota publishes actual court rules as
rules, officially, free.

`mncourts.gov` returns **403** to plain fetches, but nothing is needed from it —
the Revisor has everything. Recorded only so a future session does not read that
403 as a blocker.

Per-rule amendment lines are printed, e.g. Rule 6.01 ends *"(Amended effective
January 1, 1997; amended effective July 1, 2007; amended effective September 1,
2012; amended effective January 1, 2020.)"* — so `effective_from` is real per
rule. Proposed: **6.01 → 2020-01-01**, **12.01 → 2020-01-01**.

## 2. Rule 6.01 — read verbatim, and it is the modern federal shape

> **(a)(1) Period Stated in Days or a Longer Unit of Time.** … (A) exclude the
> day of the event that triggers the period; (B) **count every day, including
> intermediate Saturdays, Sundays, and legal holidays**; and (C) include the
> last day of the period, but if the last day is a Saturday, Sunday, or legal
> holiday, the period continues to run until the end of the next day that is not
> a Saturday, Sunday, or legal holiday.
>
> **(a)(2) Periods Shorter than 7 Days.** **Only if expressly so provided by any
> other rule or statute**, a time period that is less than 7 days may exclude
> intermediate Saturdays, Sundays, and legal holidays.
>
> **(c) "Next Day" Defined.** The "next day" is determined by continuing to
> count forward when the period is measured after an event **and backward when
> measured before an event**.

Three things follow, each of which decides a field:

- **NO GENERAL SHORT-PERIOD EXCLUSION.** Minnesota adopted the 2009-federal
  "days are days" approach. `short_period_exclusion_days` must be **ABSENT**,
  like the federal standard — not 7, not 11. **And note the shape is different
  from every seeded state:** (a)(2) makes the exclusion an **opt-in that
  individual rules may grant**, not a standard-wide threshold. The engine's flag
  is standard-level, so if a Minnesota rule is ever seeded that *expressly*
  provides the exclusion, it cannot be expressed by the current field and would
  need a row-level mechanism. No such rule is in this batch.
- **BACKWARD IS DEFINED**, expressly, in (c) — "backward when measured before an
  event". So the backward suffix is real, like Virginia and unlike NJ, NC, WA,
  MA, MO and WI. No backward row is seeded in a first batch even so.
- **The rollover basis IS the holiday list** (Saturday, Sunday, or legal
  holiday) — *not* a courthouse-closure test. So Minnesota does **not** have
  Wisconsin's problem, where the rollover keys on clerk closure while the list
  governs only the exclusion.

### Two limbs the engine cannot express, both failing EARLY

- **(a)(3) Periods stated in HOURS** — "begin counting immediately on the
  occurrence of the event … count every hour". **The engine has no hours unit**
  (`calendar_days`, `business_days`, `months`, `years` only). No hours-based row
  is in this batch; if one is ever needed it is a real addition. Avoidable, not
  a blocker.
- **(a)(4) Inaccessibility of the Court Administrator's Office** — extends
  filing to the first accessible day. Unknowable in advance. **Crucially this is
  an ADDITIONAL limb on top of the Sat/Sun/holiday rollover, not a replacement
  for it**, so omitting it can only ever report **EARLY**. Disclosable, same
  treatment as Va. § 1-210(F).
- **(b) "Last Day" Defined** — ends 11:59 p.m. for e-filing, or when the Court
  Administrator's office closes otherwise. A time-of-day for the deadline
  itself; it does not change the **date**, which is all this engine reports.
  Worth a note, not a mechanism.

## 3. Service extension — a SIXTH pattern, and existing machinery covers it

> **6.01(e) Additional Time After Service by Mail or Service Late in Day.**
> Whenever a party has the right or is required to do some act … within a
> prescribed period after the service of a notice or other document upon the
> party, and the notice or document is served upon the party **by United States
> Mail, 3 days shall be added** to the prescribed period. **If service is made
> by any means other than United States Mail and accomplished after 5:00 p.m.
> local Minnesota time on the day of service, 1 additional day shall be added**
> to the prescribed period.

| State | Electronic / non-mail service |
|---|---|
| Massachusetts | +3 days, enumerated in the time rule |
| Tennessee | service rule **deems** it mail → +3 |
| Missouri | +0 days, **trigger date moves** on a 5 p.m./weekend cutoff |
| Maryland | +0 days, no cutoff |
| Wisconsin | +1 day if completed **between** 5 p.m. and midnight |
| **Minnesota** | **+1 day if after 5 p.m., for ANY means other than U.S. Mail** |

**It is Virginia's/Wisconsin's mechanism — an amount that varies by clock — so
`amount(method, ctx)` with `service_time` already covers it. No new mechanism.**

Two differences worth encoding carefully:

- **The non-mail limb is a NEGATIVE condition, not an allowlist.** It reaches
  "any means other than United States Mail" — so fax, e-mail, e-filing, personal
  delivery and anything else all fall in it. Every other state that has a clock
  rule enumerates the methods. A Minnesota `qualifies()` must not be an
  allowlist copied from a neighbour.
- **"after 5:00 p.m." — so 17:00 exactly is NOT after**, the same clean boundary
  Virginia has and **unlike Wisconsin's ambiguous "between 5 p.m. and
  midnight"**. And there is **no midnight ceiling**: the limb turns only on
  "after 5:00 p.m. … on the day of service".

## 4. The holiday definition — two limbs, and the second one resolves the hard part

> **6.01(d) Definition of Legal Holiday.** As used in this rule and in Rule
> 77(c), "legal holiday" includes any holiday designated in Minnesota Statutes,
> section 645.44, subdivision 5, **as a holiday for the state or any statewide
> branch of government** and **any day that the U.S. mail does not operate**.

**§ 645.44 subd. 5**, verbatim on the list and the shift:

> "Holiday" includes New Year's Day, January 1; Martin Luther King's Birthday,
> the third Monday in January; Washington's and Lincoln's Birthday, the third
> Monday in February; Memorial Day, the last Monday in May; **Juneteenth, June
> 19**; Independence Day, July 4; Labor Day, the first Monday in September;
> **Indigenous Peoples Day, the second Monday in October**; Veterans Day,
> November 11; Thanksgiving Day, the fourth Thursday in November; and Christmas
> Day, December 25; **provided, when New Year's Day … or Juneteenth … or
> Independence Day … or Veterans Day … or Christmas Day … falls on Sunday, the
> following day shall be a holiday and, provided, when [the same five] falls on
> Saturday, the preceding day shall be a holiday.**

**The shift is BOTH WAYS but ENUMERATED to five named days** — the most precise
wording of any state gated. It is correct as written, since the nth-weekday days
cannot land on a weekend anyway, but a generator must apply the shift **only to
those five**, not to every fixed-date day by analogy.

**INDIGENOUS PEOPLES DAY replaced Columbus Day** in Minnesota, as Frances Xavier
Cabrini Day did in Colorado. Same date (second Monday in October), different
name — and **the name is not the point; whether the day counts is**. See below.

### The branch-option problem, and why it resolves

The statute continues:

> However, for the **executive branch** of the state of Minnesota, "holiday"
> also includes the **Friday after Thanksgiving** but **does not include
> Indigenous Peoples Day**. **Other branches of state government and political
> subdivisions shall have the OPTION** of determining whether Indigenous Peoples
> Day and the Friday after Thanksgiving shall be holidays.

So two days are **optional for the judicial branch**, and Rule 6.01(d) pulls in
645.44 only "as a holiday for the state or any statewide branch of government".
That looks like Wisconsin's clerk-closure problem — but it is narrower, and
**Rule 6.01(d)'s SECOND limb resolves half of it**:

- **Indigenous Peoples Day (2nd Monday in October): IN, on the postal limb.**
  It is the federal Columbus Day holiday, so **the U.S. mail does not operate**
  — which independently makes it a legal holiday under 6.01(d) regardless of
  whether the judiciary exercised its 645.44 option. This is a reading, not a
  quoted holding, and is flagged as such; but it is the reading the rule's own
  second limb compels.
- **Friday after Thanksgiving: OUT by default.** U.S. mail **does** operate that
  day, so the postal limb does not reach it, and it depends entirely on whether
  the judicial branch opted in. **Omitting it reports EARLY**, which is safe, so
  the default is available and correct — unlike Wisconsin, where no safe default
  existed. Worth confirming against the Judiciary's published holiday schedule
  before seeding, but it does not block.

**The postal limb is also a small ongoing dependency**: "any day that the U.S.
mail does not operate" is not a fixed list. In practice it tracks the federal
holidays, all eleven of which map onto Minnesota's eleven, but a one-off postal
closure would be a day this engine does not know about — **EARLY, disclosable**.

## 5. Periods, read verbatim

- **Rule 12.01** — answer **21 days** after service of the summons; cross-claim
  answer **21 days**; reply to a counterclaim **21 days** after service of the
  answer, or 21 days after service of the order if a reply is ordered. A Rule 12
  motion alters these to **14 days** after service of notice of the court's
  action (denied/postponed) or **14 days** after service of the more definite
  statement. Note both motion limbs run from **SERVICE**, not from entry or
  notice-by-the-court — so unlike Missouri's, they should take the extension.
- **Rule 33.01(b)** — interrogatories: **30 days**, defendant floor **45 days**
  after service of summons and complaint.
- **Rule 34.02(c)(1)** — production: **30 days after the party is served (or
  deemed served pursuant to Rule 26.04(b))**. **NO defendant floor** — unlike
  interrogatories and admissions. Same asymmetry Massachusetts has (2 of 3), and
  it must not be filled in by analogy. The "or deemed served" cross-reference to
  Rule 26.04(b) needs its own read before seeding.
- **Rule 36.01** — admissions: **30 days**, defendant floor **45 days**, and
  **silence ADMITS** ("The matter is admitted unless within 30 days…").

All floors run from **service of the summons and complaint** — a caller-supplied
date — so Minnesota does **not** hit the Maryland chained-floor gap.

## 6. Verdict

**PASS, and it is the cleanest gate run so far.** One official free publisher
for both rules and statutes on plain `curl`; real per-rule effective dates; the
rollover keyed to the holiday list rather than to courthouse closure; backward
counting expressly defined; the service extension covered by machinery that
already exists; and every unmodelled item — office inaccessibility, the postal
limb, the Friday-after-Thanksgiving option — failing **EARLY**.

**No decision is pending and nothing is blocked.** The items to settle during
seeding rather than before it:

1. Confirm the Judiciary's treatment of the **Friday after Thanksgiving**
   against its published holiday schedule (default: omit, EARLY).
2. Read **Rule 26.04(b)** for what "deemed served" means in Rule 34.02.
3. Decide whether to seed the **no-defendant-floor** production row as a plain
   single-trigger row (it is), and record why it differs from its two siblings.
4. Record the hours limb of 6.01(a)(3) as a known unmodelled unit.
