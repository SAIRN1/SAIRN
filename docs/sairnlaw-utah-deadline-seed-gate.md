# Utah — deadline-seed source-availability gate

**Run 2026-08-27. Verdict: PASS, and it is the cleanest jurisdiction gated since
Minnesota. Utah is the FIRST state to pass the weekend-coverage check at STEP
ONE, and the first whose holiday list lives INSIDE the rule of procedure rather
than in a statute the rule points at. It carries ONE dated landmine: the holiday
statute is SUPERSEDED 1/1/2027 and the change moves Juneteenth, breaking the
rule's own shorthand for it in eight of the next nine years.**

Utah (~3.5M), the largest state with neither a seed nor a gate document. Rules
of court are the **Utah Rules of Civil Procedure**, adopted by the Utah Supreme
Court.

---

## 1. Sources — PASS on plain `curl`, but two traps sit on top of them

```
legacy.utcourts.gov/rules/view.php?type=urcp&rule=6    200, no headers needed
le.utah.gov/xcode/Title63G/Chapter1/C63G-1-P3_...pdf   200, real text PDF
```

Both free, both official, both on a bare `curl` with no user-agent and no
`Accept` header. Every rule page prints its own **`Effective:` date**, so
`effective_from` is a real per-rule value rather than a restyling fallback.

**TRAP 1 — the host named `legacy` IS the current one, and the banner saying
otherwise is self-referential.** Every rule page prints:

> Rule printed on August 27, 2026 at 3:22 am. **Go to
> https://www.utcourts.gov/rules for current rules.**

Follow that link and it **302s straight back to `legacy.utcourts.gov/rules`**
(`location: https://legacy.utcourts.gov/rules`, captured directly). The banner
tells you to go where you already are. Two independent confirmations that
`legacy` is live and maintained, not an archive:

| URCP | `Effective:` on `legacy` |
|---|---|
| 63 | **2/13/2026** |
| 58A | **12/9/2025** |
| 45 | **11/1/2025** |
| 26 | 5/7/2025 |
| 5 | 11/1/2024 |
| 6, 12 | 5/1/2024 |

A site carrying a rule effective **six months ago** is not stale. **Do not read
the hostname or the banner as a currency blocker** — that is this jurisdiction's
version of the `mass.gov` 403 and the `nccourts.gov` 403: a signal that looks
like a wall and is not one.

**TRAP 2 — and this one runs the DANGEROUS way. `legacy.utcourts.gov` returns
HTTP 200 with an error-page BODY for a rule that does not exist.**
`legacy.utcourts.gov/rules/urcp.html` returns **200, 11,211 bytes**, and the
body reads *"We couldn't find your page… There was an error viewing this rule."*
Every other source problem gated so far announced itself with a 403, a 404 or a
paywall. **Here a 200 is not proof the rule exists** — the body must be checked.
A scripted fetch that trusts the status code would silently seed nothing.

**`www.utcourts.gov` returns 406 to `curl`**, and neither a user-agent alone nor
an `Accept` header alone fixes it — both are needed together. Irrelevant in
practice, since `legacy` serves everything with no headers at all, but recorded
so a future session does not read that 406 as "site down".

## 2. THE WEEKEND-COVERAGE STANDING CHECK — Utah answers at STEP ONE

The standing check asks, in order: (1) does the rollover clause name Saturday
and Sunday expressly? **Utah's does, and the check stops there.**

**URCP 6(a)(1)(C)**, verbatim:

> include the last day of the period, but **if the last day is a Saturday,
> Sunday, or legal holiday**, the period continues to run until the end of the
> next day that is **not a Saturday, Sunday or legal holiday**.

`isWeekend()` is correct for Utah **on the rule's own words**. No holiday
statute needs to be consulted for the weekend question at all, and there is no
statewide-coverage sub-question to answer.

**The five answers now on record:**

| State | Answer |
|---|---|
| Louisiana | rolls only on a "legal holiday"; the statute does not cover both days everywhere → **LATE → BLOCKED** |
| Oklahoma | 25 O.S. § 82.1(A) opens "Each Saturday, Sunday", statewide → safe, via the statute |
| Oregon | ORCP 10 A names "a Saturday or a legal holiday, including Sunday" → safe, via the rule |
| Connecticut | keys purely on clerk's-office closure; no holiday list exists → **premise fails, the Wisconsin hazard** |
| **Utah** | **URCP 6(a)(1)(C) names both days in the rollover clause itself → safe at step 1** |

## 3. Counting — days are days, and backward is expressly defined

**URCP 6(a)(1)(A)–(B)**, verbatim:

> (A) exclude the day of the event that triggers the period; (B) **count every
> day, including intermediate Saturdays, Sundays, and legal holidays**

**NO short-period exclusion, stated affirmatively** — the 2009-federal "days are
days", like Minnesota and unlike the six seeded states that use 7 and the three
that use 11. `short_period_exclusion_days` must be **ABSENT, not zero**.
Copying 7 from a neighbour would push every short Utah deadline later than the
rule provides.

**URCP 6(a)(5)** defines backward counting outright:

> The "next day" is determined by continuing to count forward when the period is
> measured after an event and **backward when measured before an event**.

Real, like Minnesota's 6.01(c), unlike NJ/NC/WA/MA/MO/WI where the backward
suffix has to be left blank.

**NOT MODELLABLE: URCP 6(a)(2) states periods in HOURS**, with its own
hour-granular rollover. This engine has no hours unit. No hours row can be
seeded; that would be a real engine addition, not a config change.

## 4. THE HOLIDAY LIST IS INSIDE THE RULE — Utah is DERIVE, not INGEST

**URCP 6(a)(6)** carries its own closed definition — *"'Legal holiday' **means**
the day for observing"* — of thirteen limbs: New Year's Day; Dr. Martin Luther
King, Jr. Day; **Washington and Lincoln Day**; Memorial Day; **Juneteenth
National Freedom Day (as recognized by the Utah Legislature as the third Monday
of June)**; Independence Day; **Pioneer Day**; Labor Day; Columbus Day;
Veterans' Day; Thanksgiving Day; Christmas; and **(M) any day designated by the
Governor or Legislature as a legal holiday**.

That makes Utah **ingest-NOT-required** — the opposite of North Carolina, New
Jersey, Maryland, Oklahoma and Connecticut, all of which need an artifact the
court publishes separately. Two Utah-specific days to get right: **Pioneer Day,
24 July**, and **Washington and Lincoln Day** (the statute calls the same day
Presidents' Day — a naming divergence only, no date impact).

**It is not derivable from the rule ALONE, though.** The definition says *"the
day for **observing**"*, which points outward to the observation rule in
**Utah Code § 63G-1-301(2)**:

> (a) If a day described in Subsection (1)(a) falls on a **Saturday, the
> preceding Friday** is the legal holiday. (b) If a day described in Subsection
> (1)(a) falls on a **Sunday, the following Monday** is the legal holiday.

A **both-ways shift** on the five fixed-date holidays, like Minnesota's
enumerated shift — and it **spills across the year boundary** the same way.
Computed directly:

| | date | falls | observed |
|---|---|---|---|
| Independence 2026 | 2026-07-04 | Sat | **2026-07-03** |
| Independence 2027 | 2027-07-04 | Sun | **2027-07-05** |
| Pioneer Day 2027 | 2027-07-24 | Sat | **2027-07-23** |
| Christmas 2027 | 2027-12-25 | Sat | **2027-12-24** |
| New Year's **2028** | 2028-01-01 | Sat | **2027-12-31 ← SPILLS INTO THE 2027 CALENDAR** |

A Utah 2027 calendar that is built only from 2027's holidays is **missing
2027-12-31**, and a deadline landing there would be reported a day EARLY at
best. The 2028 list must be consulted to finish 2027.

**GOOD FRIDAY IS THE INTERESTING OMISSION.** § 63G-1-301(1)(b)(iii) makes
**Good Friday** a Utah legal holiday — a **weekday** — and URCP 6(a)(6)'s
thirteen limbs **do not list it**. Because 6(a)(6) says "means" rather than
"includes", the rule's list should control and Good Friday should NOT roll a
deadline. But limb **(M)** — "any day designated by the Governor **or
Legislature**" — could be read to sweep the statute back in, since the
Legislature designated Good Friday by statute; on that reading (M) makes the
other twelve limbs redundant, which is an argument against it. **Unresolved,
and it does not need resolving to seed:** omitting Good Friday can only report a
deadline **EARLY**, never late. Encoding it would be the risky choice.
(Easter Sunday and the statute's "every Sunday" are already non-days under
6(a)(1)(C), so neither matters.)

**Ad hoc and not knowable in advance, both EARLY:** limb (M) proper
(Governor/Legislature designations), and § 63G-1-301(5), which lets the governor
proclaim additional legal holidays for up to 60 days, renewable in 30-day
increments.

## 5. THE LANDMINE — the holiday statute is SUPERSEDED 1/1/2027, and it moves Juneteenth

The Utah Code PDF carries **both versions of § 63G-1-301 in one file**: the
current one, headed **`Superseded 1/1/2027`** (amended by Chapter 124, 2026
General Session), and its successor, headed **`Effective 1/1/2027`** (amended by
Chapter **126**, 2026 General Session). The section was amended **twice in the
2026 session**.

**What changes is Juneteenth, and only Juneteenth.** Today it sits in
§ 63G-1-301(1)(**b**)(ix) — "June 19" — with two shifting rules of its own that
apply to nothing else:

> (c) If June 19 falls on a **Tuesday, Wednesday, Thursday, or Friday, the
> preceding Monday** is the legal holiday. (d) If June 19 falls on **Saturday or
> Sunday, the following Monday** is the legal holiday.

From 1/1/2027 it moves to § 63G-1-301(1)(**a**)(ii) — an ordinary fixed-date
holiday under the plain (2)(a)/(2)(b) Saturday→Friday / Sunday→Monday shift —
and **(2)(c) and (2)(d) are deleted outright**.

**First, the good news: URCP 6(a)(6)(E)'s parenthetical is EXACTLY RIGHT for the
current statute.** "the third Monday of June" reproduces the (1)(b)(ix) + (2)(c)
+ (2)(d) formula in **every year 2024–2032**, verified by computation, not
assumed. The rule's shorthand is a correct restatement, not a drafting error.

**Then the landmine: the 1/1/2027 amendment breaks that equivalence in eight of
the next nine years.**

| year | June 19 | rule's "third Monday" | statute from 1/1/2027 | agree? |
|---|---|---|---|---|
| **2027** | Sat | **2027-06-21** | **2027-06-18** | **no — 3 days apart** |
| 2028 | Mon | 2028-06-19 | 2028-06-19 | yes |
| 2029 | Tue | 2029-06-18 | 2029-06-19 | no |
| 2030 | Wed | 2030-06-17 | 2030-06-19 | no |
| 2031 | Thu | 2031-06-16 | 2031-06-19 | no |
| 2032 | Sat | 2032-06-21 | 2032-06-18 | no |

**The question this raises is legal, not arithmetic:** URCP 6(a)(6)(E) defines
Juneteenth by a description ("the third Monday of June") that is expressly
premised on how *"the Utah Legislature"* recognises it. When the Legislature
stops recognising it that way, does the rule mean its own literal text, or its
stated basis? Nobody can compute the answer.

**AND IT FAILS IN BOTH DIRECTIONS IN THE SAME YEAR.** Take 2027: encoding
2027-06-21 as the holiday when the true date is 2027-06-18 means a deadline
landing on the 21st is rolled when it should not be — **LATE, the direction that
loses a filing** — while a deadline landing on the 18th is not rolled when it
should be — EARLY. **This is the one item in the Utah gate that can produce a
late date**, and unlike Connecticut's it has a hard calendar date attached to it.

**It does NOT block seeding.** It blocks the calendar's *range*. The engine
already refuses a year it has no calendar for (`holidayFor` → `known: false,
missingYear` → `NOT_PROVISIONED`), so **a Utah calendar loaded for 2026 only
refuses every 2027+ trigger automatically** — the same mechanical hold used for
Connecticut, scoped to a year boundary instead of a whole jurisdiction. Seed
Utah, cap the calendar at 2026-12-31, and resolve the Juneteenth question before
extending it.

## 6. Rule 6(c) — SEVEN days for mail, and a condition the engine cannot express

**URCP 6(c)**, verbatim:

> When a party may or must act within a specified time after service and service
> is made **exclusively by mail under Rule 5(b)(3)(C)(i)**, **7 days are added**
> after the period would otherwise expire under paragraph (a).

**Seven.** Every seeded jurisdiction adds three, except California's per-method
amounts. Copying a neighbour's 3 here would compute **four days EARLY** on every
mailed period.

**The condition is narrow and is NOT a plain method test.** Rule 5(b)(3)(C)
permits mail only *"if the party serving or being served with a document does
not have an electronic filing account or email."* So mail service under (C)(i)
already implies both are unavailable — meaning `applies_when: ['mail']` is
defensible on the face of it.

**But the word is "exclusively", and this engine has ONE `service_method`
field.** It cannot express "served by mail **and by nothing else**". If a caller
supplies `mail` for a party who was in fact served by mail *and* email, the
engine adds seven days and reports **LATE**. Seven days is a large overshoot,
and this is a real modelling hazard to settle before seeding, not after.

**URCP 5(b)(4)** also states a completion rule: *"Service by mail or electronic
means is **complete upon sending**."* Missouri's `service_completion` shape,
with no time-of-day condition attached.

## 7. What is seedable — the ordinary rows are clean

**URCP 12(a)(1)**, verbatim on the operative part:

> a defendant must file and serve an answer **within 21 days after the service
> of the summons and complaint within the state** and **within 30 days after
> service of the summons and complaint outside the state**. A party served with
> a crossclaim must file and serve an answer to the crossclaim within 21 days
> after service. The plaintiff must file and serve an answer to a counterclaim
> within 21 days after service of the counterclaim…

Utah **has a real answer deadline**, unlike Connecticut. The in-state/out-of-
state split is two rows with distinct trigger events, not a mechanism —
the same shape as a domain-scoped variant. Rule 12(a)(1)(A) and (B) add two
more ordinary rows: **14 days** after notice of the court's action on a denied
or postponed motion, and **14 days** after service of a more definite statement.

Discovery is uniform at **28 days**, read directly: **URCP 33** ("a written
response within 28 days after service of the interrogatories"), **URCP 34(b)(2)**
("must serve a written response within 28 days after service of the request")
and **URCP 36** ("The matter is admitted unless, within 28 days after service of
the request…"). None was read for a defendant floor.

`effective_from` values are real and per-rule: **6 → 2024-05-01**, **12 →
2024-05-01**, **33 → 2011-11-01**, **34 → 2017-05-01**, **36 → 2021-05-01**.

## 8. Not modelled, all EARLY, all disclosable

- **URCP 6(a)(3)** — clerk's-office **inaccessibility**. Critically, this is
  **ADDITIONAL to** the Saturday/Sunday/holiday rollover, not a replacement for
  it (Minnesota's 6.01(a)(4) shape, **not** Wisconsin's). Omitting it can only
  report EARLY.
- **URCP 6(d)** — for a party who is unrepresented **and** has no e-filing
  account, the period runs from the **service** date rather than the **filing**
  date. Keyed on party status, which this engine has no field for.
- **URCP 6(e)** — the inmate mailbox rule, and its own "calculated from the date
  the papers are received by the court" limb.
- Limb **(M)** and § 63G-1-301(5) governor's proclamations (see §4).
- **Good Friday**, on the (M)-sweeps-the-statute reading (see §4).

## 9. What was NOT determined

- **Whether URCP 6(a)(6)(M) sweeps the whole statutory list in**, which is what
  decides Good Friday. Safe to leave open; the safe answer is to omit.
- **Which reading of Juneteenth governs from 1/1/2027** — §5. The only
  late-direction item in this gate.
- **How to express Rule 6(c)'s "exclusively"** with one `service_method` field —
  §6. The second-most important item, and also late-direction.
- **URCP 34** was read for its response period only; no defendant-floor question
  was checked for any of 33, 34 or 36.
- **Rule 4** (process/service of the summons) was not read, so the trigger for
  the Rule 12 rows — what "service of the summons and complaint" completes on —
  is not yet sourced.
- Appellate rules, and the new **Rules of Business and Chancery Court
  Procedure**, were not looked at.

## 10. Verdict

**PASS.** Sources are free, official, current and plain-`curl`, with real
per-rule effective dates. The counting rule is unambiguous, the weekend question
answers itself at step one, backward counting is expressly defined, the holiday
list is inside the rule, and there is a real answer deadline to compute.

**Seed it, with the calendar capped at 2026-12-31.** Three things to settle,
in this order:

1. **Rule 6(c)'s "exclusively"** — LATE-direction, and it affects every mailed
   row. Settle before seeding any row that carries the extension.
2. **Juneteenth from 1/1/2027** — LATE-direction, but the year cap holds it
   mechanically. Settle before extending the calendar past 2026.
3. **Good Friday / limb (M)** — EARLY-direction only. Omit and disclose; it can
   wait.

Nothing here is a source problem, and nothing here is structural in the way
Connecticut's chain was.
