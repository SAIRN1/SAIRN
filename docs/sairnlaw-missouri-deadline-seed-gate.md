# Missouri — deadline-seed source-availability gate

**Run 2026-08-26. Verdict: PASS — with one required engine addition and one
disclosure. Missouri is seedable; it is not seedable *today* without building
something new.**

Missouri (~6.2M) is the largest unseeded state after Tennessee failed. It has
the **best statute access of any jurisdiction gated so far**, and it needs a
service mechanism this engine has never had.

---

## 1. Sources — PASS, and the statute side is the best seen yet

**Rules.** The Missouri Supreme Court Rules are published free and in full by
the Missouri courts at `courts.mo.gov`, in the Clerk Handbooks database. Each
rule prints its own `Publication / Adopted Date` **and** `Revised / Effective
Date`, so `effective_from` would be real per row — Virginia's and
Massachusetts' situation, not New Jersey's blanket date.

Read verbatim during this gate: **44.01, 43.01, 103.08**.

| Rule | Adopted | Revised / effective |
|---|---|---|
| 44.01 Time | 1972-02-01 | **2025-01-01** (amended 2024-05-01) |
| 43.01 Service | 1972-02-01 | 2018-07-01 |
| 103.08 E-filing service | 2011-09-01 | 2020-07-01 |

**Access, and a real quirk worth recording:** `courts.mo.gov/page.jsp?id=…` is
behind a **Cloudflare bot challenge** that neither `curl` nor headless
Playwright clears (it returns the "Performing security verification" interstitial
indefinitely). But the underlying **`ClerkHandbooksP2RulesOnly.nsf/…` document
URLs are NOT challenged** and return full text to an ordinary Playwright
context. Every rule above was read that way. *A 403 or a challenge page on
`page.jsp` does not mean the rule is unavailable — reach it by its `.nsf`
document URL instead.* Same category of lesson as mass.gov and tncourts.gov,
third distinct mechanism.

**Statutes — the strongest of any state gated.** `revisor.mo.gov` is the
**official Missouri Revisor of Statutes**, free, and returns **HTTP 200 to plain
`curl`** with no challenge, no terms gate and no publisher redirect. It also
prints **per-section version history with effective dates**, so a section's
currency is checkable on its face. RSMo 9.010 was read directly this way and
shows `effective 28 Aug 2022` with prior versions listed back to 1959.

This is the exact opposite of Tennessee, which failed *because* its statute sat
behind a publisher's terms-acceptance gate.

## 2. The holiday basis — a Kentucky-shaped gap that is NOT a Kentucky-shaped risk

Rule 44.01(a) rolls the last day off "a Saturday, Sunday or a **legal holiday**"
and **names no statute**. Missouri's holiday statute, **RSMo 9.010, is titled
"Public holidays"** and never uses the phrase "legal holiday".

**That is the identical lexical gap that helped kill Kentucky** — KRS 2.110 is
titled "Public holidays", never says "legal holiday", and Kentucky was refused
partly on it. So the gap was checked the same way, and **it comes out the
opposite way here.**

Kentucky failed because its statutory list **diverged dangerously** from what
courts actually do: KRS 2.110 lists four days Kentucky courts do *not* close for
and **omits Thanksgiving**, so encoding it rolls deadlines **LATE**.

Missouri does not have that problem. **RSMo 9.010's thirteen days match the
State of Missouri's own published 2026 holiday schedule day for day**, verified
against the **Missouri Office of Administration** (`oa.mo.gov/commissioner/state-holidays`),
including both Missouri-specific days:

| RSMo 9.010 | OA 2026 schedule |
|---|---|
| January 1 | New Year's Day — Thu Jan 1 |
| third Monday of January | MLK — Mon Jan 19 |
| **twelfth day of February** | **Lincoln's Birthday — Thu Feb 12** |
| third Monday in February | Washington's Birthday — Mon Feb 16 |
| **eighth day of May** | **Truman Day — Fri May 8** |
| last Monday in May | Memorial Day — Mon May 25 |
| nineteenth day of June | Juneteenth — Fri Jun 19 |
| fourth day of July | *Independence Day (observed) — **Fri Jul 3*** |
| first Monday in September | Labor Day — Mon Sep 7 |
| second Monday in October | Columbus Day — Mon Oct 12 |
| eleventh day of November | Veterans Day — Wed Nov 11 |
| fourth Thursday in November | Thanksgiving — Thu Nov 26 |
| twenty-fifth of December | Christmas — Fri Dec 25 |

There is **no day in 9.010 that Missouri state government stays open for**, and
Thanksgiving is present. So encoding 9.010 cannot roll a deadline LATE on any
listed day. The "public" vs "legal" wording gap remains an unresolved question
of law, but **both candidate readings converge on the same thirteen days**,
which is what makes it safe where Kentucky's was not.

**Add it to the bundled lawyer's question as a new category:** *a rule that says
"legal holiday" and points at nothing, where the obvious statute is titled
something else but converges in practice.* That is a materially different
situation from Texas and Arizona (converge unknown) and from Kentucky
(diverges dangerously), and the bundle should say so.

### The one real divergence, and it fails EARLY

**RSMo 9.010's shift is SUNDAY-ONLY** — *"when any of such holidays falls upon
Sunday, the Monday next following shall be considered the holiday."* It says
**nothing about Saturday**, exactly like Massachusetts' Cl. 18 and unlike
Virginia and West Virginia.

But the OA schedule lists **"Independence Day (observed) — Friday, July 3"** for
2026, because 4 July 2026 is a Saturday. **The administration observes a Friday
substitute the statute does not create.**

Direction analysis, which decides the treatment:

- **Encode the statute only** (Sat 4 July 2026 is the holiday; no Friday entry):
  a deadline landing Fri 3 July does not roll. If the courthouse is in fact
  closed that Friday, the true deadline is later → **EARLY. Safe.**
- **Encode the observed Friday**: if Rule 44.01's "legal holiday" means the
  statute, we would roll a deadline that should not roll → **LATE. Unsafe.**

**So: encode RSMo 9.010 verbatim with the Sunday-only shift, and DISCLOSE that
administratively observed substitute days are not modelled.** Same
`JURISDICTION_COVERAGE` pattern and same direction test as Virginia's
§ 1-210(F) and Massachusetts' Suffolk County gap.

**Do NOT add a Saturday shift by analogy to Virginia or West Virginia** — this
is the second state in a row where that would be wrong, and in Massachusetts the
generator's own assertion caught it. Write the shift from Missouri's own words.

## 3. THE ENGINE ADDITION MISSOURI REQUIRES — a completion rule that moves the TRIGGER DATE

This is the finding that makes Missouri more than another seed, and it was found
**only because the Tennessee gate produced the standing habit of checking the
service rule before trusting a time rule.** Applying that habit here changed the
answer again — and in a third distinct way.

**Rule 44.01(d), verbatim:**

> Whenever a party has the right or is required to do some act or take some
> proceedings within a prescribed period after the service of a notice or other
> paper upon the party and the notice or paper **is served by mail, three days
> shall be added to the prescribed period.**

Read alone, that is mail-only, +3, period-lengthening. But:

**Rule 43.01(d), verbatim:**

> Personal service on attorneys and self-represented parties and service by
> leaving a copy at the attorney's office is complete upon delivery.
>
> Service by mail is complete upon mailing.
>
> **Service by facsimile transmission or electronic mail is complete upon
> transmission, except that a transmission made on a Saturday, Sunday, or legal
> holiday, or after 5:00 p.m. shall be complete on the next day that is not a
> Saturday, Sunday, or legal holiday.**

**Rule 103.08(a), verbatim:**

> Service shall be made to registered users through the electronic filing system
> and to all others as provided in Rule 43.01(c). Service by the electronic
> filing system is complete upon transmission except that, **for the purposes of
> calculating the time for filing a response, a transmission made on a Saturday,
> Sunday, or legal holiday, or after 5:00 p.m., shall be considered complete on
> the next day that is not a Saturday, Sunday, or a legal holiday.**

### Why this is a new mechanism and not Virginia's

The engine already accepts `service_time` — built for **Va. Sup. Ct. R. 1:7**,
where a 5:00 p.m. cutoff decides **how many days are ADDED** (0 or 1). Missouri's
5:00 p.m. cutoff decides **WHEN SERVICE IS COMPLETE**, which moves the **trigger
date** the whole period runs from. Same clock, different target:

| | Virginia R. 1:7 | **Missouri R. 43.01(d) / 103.08** |
|---|---|---|
| What the 5 p.m. cutoff changes | the **amount added** (0 vs 1 day) | **the trigger date itself** |
| Applies to | manual delivery, fax, email, same-day commercial | fax, email, e-filing service |
| Also shifts for weekends/holidays? | no | **yes — Sat/Sun/legal holiday also push completion forward** |
| Days added | 0 or 1, per method | **none** — electronic service gets no added days in Missouri |

So in Missouri: **mail → +3 days and no completion shift; fax / email / e-filing
→ no added days, but the trigger date may move forward to the next non-weekend,
non-holiday day.** A fax sent 17:30 on Friday before a Monday holiday is complete
**Tuesday**, and the whole period runs from Tuesday.

**Three states, three different answers on electronic service — none inheritable:**

- **Massachusetts** R. 6(d): +3 days for electronic service, stated in the time
  rule itself.
- **Tennessee** R. 6.05 + 5.02(2)(c)/(3)(e): time rule says mail only, but the
  service rule **deems** email and e-service to be mail → +3 days.
- **Missouri** R. 44.01(d) + 43.01(d)/103.08: time rule says mail only and the
  service rule does **not** deem — it instead moves **when service is complete**.
  → **+0 days, shifted trigger.**

Reading any one of those three time rules alone gives a wrong answer for the
other two. The habit generalises: **for every jurisdiction, read the service
rule before concluding what the time rule reaches.**

### What has to be built

A trigger-date completion adjustment, applied *before* the base period is
computed:

1. A new optional input describing service completion — the engine has
   `service_time` already; what is missing is a **per-jurisdiction completion
   standard** that consumes it to adjust `trigger_date` rather than the amount.
2. It must roll forward off Saturdays, Sundays **and legal holidays**, i.e. reuse
   `rollOff` against the same jurisdiction calendar.
3. It must **refuse rather than guess** when the method is one of the
   completion-governed ones and `service_time` is absent — the same call already
   made for Virginia, and for the same reason: defaulting to "before 5 p.m."
   runs EARLY and defaulting to "after" runs LATE, and the rule allows both.
   Reuse the existing `refused_missing_context` state.

This is a real addition but a bounded one, and it is the natural companion to
the `amount(method, ctx)` work Virginia already forced. **It must exist before
any Missouri row that carries electronic service is seeded** — otherwise those
rows silently compute from an unshifted trigger, and *that error runs EARLY on a
late-day transmission but the period start is simply wrong*, which is the kind of
quiet wrongness this engine exists to avoid.

## 4. Other banked findings, read verbatim

- **Short-period exclusion is "less than seven days"** (Rule 44.01(a)), so
  `short_period_exclusion_days: 7` — matching NJ, NC, WA, MA and WV appellate,
  and **not** Tennessee's or Arizona's eleven. Read, not carried.
- **Rule 44.01(c) sets five days' notice for motions** and one day for opposing
  affidavits — both **under seven**, so they are the rows that would actually
  exercise the exclusion. Worth seeding early for that reason.
- **Rule 44.01(b) names the rules whose time may NOT be enlarged** — 52.13,
  72.01, 73.01, 75.01, 78.04, 81.04, 81.07, 84.035 — a ready-made list of
  jurisdictional deadlines that must never carry an enlargement note.
- **Rule 44.01(d) is period-lengthening** ("added to the prescribed period"), so
  `add_to_period_then_roll`, like NJ, NC, WA, NY, VA, MA — not the federal
  after-expiry order.
- **RSMo 9.010 contains two days no other seeded jurisdiction has**: **Lincoln's
  Birthday (12 February)** and **Truman Day (8 May)**. Truman Day in particular
  has no federal or multi-state parallel. These are the days a Missouri live
  verification should use to prove the calendar is actually being read — the
  same role Patriots' Day played for Massachusetts.
- **RSMo 9.010 also carries an oddity to record, not encode**: *"There shall be
  no holiday for state employees on the fourth Monday of October."* It concerns
  state employees, not the holiday list, and the second Monday in October
  (Columbus Day) is the listed day.
- **Rule 43.01(c) permits service by facsimile and by electronic mail on both
  attorneys and parties**, so Missouri's fax and email limbs are real service
  methods and not edge cases.

## 5. What is NOT yet done

This is a **gate**, not a seed. Still required before any row:

- Verbatim read of the answer period (Rule 55.25) and the discovery periods
  (Rules 57.01 interrogatories, 58.01 production, 59.01 admissions), including
  whether Missouri grants a defendant floor on any of them. **Reachable — use
  the `.nsf` document URLs, not `page.jsp`.**
- Build the completion-rule mechanism in §3, with its own tests, before seeding
  any electronically-served row.
- Decide the disclosure text for administratively observed substitute days.
- Confirm whether the Missouri **Judiciary** publishes its own holiday schedule
  distinct from the executive OA list. It does not change the basis — Rule
  44.01 rolls off "a legal holiday", not "a day the courthouse is closed", which
  is the **opposite of North Carolina** — but it is worth having as corroboration.

## 6. Verdict

**PASS.** Sources are free, official, complete and permitted, with the best
statute access of any state gated so far and real per-rule currency. The
holiday-basis gap is Kentucky-shaped in wording but converges in substance, so
it is safe where Kentucky's was fatal. The one genuine divergence — the
administratively observed substitute day — fails EARLY and is disclosable on the
established pattern.

**Not seedable today**, because Rule 43.01(d) and Rule 103.08 require a
trigger-date completion mechanism the engine does not have. That is a build, not
a blocker, and the Tennessee-derived habit of reading the service rule first is
what surfaced it before any row was written rather than after.
