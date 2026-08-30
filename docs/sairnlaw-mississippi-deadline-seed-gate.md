# Mississippi — deadline-seed source-availability gate

**Run 2026-08-30. Verdict: PASS on the rules, SPLIT on the code, and SEEDED the
same day — 11 rules, all forward, calendar 2026 with TWO dates. Loaded to
`LAW-PINNACLE-2026` and live-verified 35/35; the licence now holds 30
jurisdictions and 337 rules, and `tools/sairn_load_state_check.py` reports
337/337 and 137/137 with 0 missing, 0 stale, 0 extra.**

**Mississippi is the mirror image of Colorado.** Colorado's statutes are free and
its *rules* sit behind a LexisNexis click-through. Mississippi's *rules* are free,
official and complete — the Supreme Court serves the whole MRCP as one 988,557-byte
PDF with the advisory committee notes attached, no gate, no sign-in — while the
Mississippi Code is the thing behind Lexis: courts.ms.gov's own "MS Code" link goes
to `lexisnexis.com/hottopics/mscode/`, which redirects to `advance.lexis.com`, the
same publisher and the same container that stopped Colorado.

That split turned out not to block the gate, for a specific reason: **the only
thing the Code is needed for is the holiday definition, and the judicial branch
restates it itself.** The State Library page publishes the ten court holidays and
every closure notice cites `Miss. Code Ann. § 3-3-7(1)` by name. Justia's mirror
was used to read the section's full text and is labelled as unofficial wherever it
is relied on.

Mississippi (~2.9M) was chosen as the largest unseeded state without an existing
gate document, after re-confirming that no gate-passed jurisdiction remained
unseeded — Alabama, Arkansas, Wisconsin, Maryland and Kansas are all done, and
Arizona, Colorado, Iowa, Kentucky, Louisiana and Tennessee are all BLOCKED, GATED
or FAILED.

---

## 1. Sources

| What | URL | Result |
|---|---|---|
| Mississippi Rules of Civil Procedure (current) | `courts.ms.gov/research/rules/msrulesofcourt/2026-07-01 Rules of Civil Procedure…pdf` | **200, `application/pdf`, 988,557 B**, real text |
| Rules index | `courts.ms.gov/research/rules/rules.php` | 200 |
| Court holiday list | `courts.ms.gov/research/statelibrary/holidays.php` | 200, ten holidays, rule-based |
| 2026 closure notices (six of them) | `courts.ms.gov/news/2026/2026*HolidayClosureNotice.pdf` | 200 each, real PDFs |
| Miss. Code Ann. § 3-3-7 | `lexisnexis.com/hottopics/mscode/` → `advance.lexis.com/container?…` | **the Colorado blocker** |
| Miss. Code Ann. § 3-3-7, § 25-1-99 (unofficial) | `law.justia.com/codes/mississippi/…` | 200, full text |

### THE URL IS A TRAP FOR A SCRAPER, AND IT IS THE SAME TRAP AS COLORADO'S

`rules.php` contains **two** links captioned "Mississippi Rules of Civil
Procedure":

```html
<!--<tr><td …><a href="msrulesofcourt/2026-06-18 Rules of Civil Procedure …pdf" …>Mississippi Rules of Civil Procedure</a></td></tr>-->
      <tr><td …><a href="msrulesofcourt/2026-07-01 Rules of Civil Procedure …pdf" …>Mississippi Rules of Civil Procedure</a></td></tr>
```

The first is **inside an HTML comment** and the file behind it **no longer exists**
— requesting it returns **HTTP 200 with 17,429 bytes of HTML**, not a PDF. That is
byte-for-byte the same soft-404 shape the Colorado gate recorded for
`Updated_Full_set_of_CRCP_and_Water_Rules.pdf`, and `curl` reports it as success
both times. A scraper taking the first regex match on this page silently reads
nothing. Every quote in the seed is from the 2026-07-01 file, and a test asserts
no row cites the 2026-06-18 one.

### Currency

Effective dates are printed per rule in a bracket at the end of the rule text, and
**two of the five rules seeded carry no bracket at all**, which means unamended
since adoption. The PDF states the adoption date on its own title page: *"Adopted
Effective January 1, 1982."*

| Rule | Bracket | effective_from |
|---|---|---|
| 6 (computation) | `[Amended effective March 1, 1989; … June 24, 1992; … July 1, 2008.]` | 2008-07-01 |
| 12 (answers) | *(none)* | **1982-01-01** |
| 33 (interrogatories) | `[Amended effective April 13, 2000; October 11, 2021.]` | 2021-10-11 |
| 34 (production) | `[Amended effective July 1, 2013 …; amended effective October 7, 2021.]` | 2021-10-07 |
| 36 (admissions) | *(none)* | **1982-01-01** |
| 59 (new trial / alter or amend) | `[Amended effective July 1, 1997.]` | 1997-07-01 |

Rules 33 and 34 were amended **four days apart** by two separate orders, which is
why they carry different dates rather than one shared "October 2021".

**The MRCP Revision Project is not a currency risk.** The Rules Committee page
still on the site is a 2015 call for comments with a closing date of 31 December
2015 and a list of the proposals received. There is no pending restyled MRCP.

---

## 2. THE FINDING IS THE CALENDAR, AND IT IS TWO DAYS LONG

This is the strongest county-variance case seen in any state so far, and unlike
Wisconsin's it is written into the statute rather than inferred from a schedule.

**Three provisions have to agree before a day can go in the calendar.**

**(1) Miss. R. Civ. P. 6(a)** — the roll trigger is a UNION of two tests, and the
second one is the Wisconsin hazard:

> The last day of the period so computed shall be included, unless it is a
> Saturday, a Sunday, or a legal holiday, **as defined by statute**, **or any
> other day when the courthouse or the clerk's office is in fact closed, whether
> with or without legal authority** …

**(2) Miss. Code Ann. § 3-3-7** supplies that definition — and immediately takes
it back:

> **(1) Except as otherwise provided in subsection (2) of this section**, the
> following are declared to be legal holidays … *(ten days)*
>
> **(2)** In lieu of any one (1) legal holiday provided for in subsection (1),
> **with the exception of the third Monday in January** (Robert E. Lee's and
> Martin Luther King, Jr.'s birthday) **and the eleventh day of November**
> (Armistice or Veterans' Day), the governing authorities of **any municipality or
> county** may declare, by order spread upon its minutes, **Mardi Gras Day or any
> one (1) other day during the year**, to be a legal holiday.

**(3) Miss. Code Ann. § 25-1-99** then makes closure mandatory — but only for the
days that are still § 3-3-7 holidays in that county:

> the courthouse **shall be closed** on all state holidays as set forth in Section
> 3-3-7, and when any state holiday … falls on a Saturday, the courthouse **may**
> be closed on the Friday immediately preceding such Saturday and when such holiday
> falls on a Sunday, the courthouse **may** be closed on the Monday immediately
> succeeding such Sunday.

Note which words are mandatory and which are permissive. Closure on a § 3-3-7
holiday: **shall**. The Friday-before and Monday-after observances: **may**, county
by county.

### IT IS NOT THEORETICAL — A REAL COUNTY HAS DONE IT

**Jackson County publishes a ten-item holiday schedule** at
`co.jackson.ms.us/171/Holiday-Schedule`. It lists **Good Friday**, which appears
nowhere in § 3-3-7, and it **omits the last Monday in April** (Confederate
Memorial Day), which § 3-3-7(1) declares. Ten items in, ten items out: **a
one-for-one § 3-3-7(2) substitution, on the record, in a real Gulf Coast county.**

A statewide calendar carrying **2026-04-27** would roll a Jackson County deadline
off a day that courthouse was **open**, and report **LATER** than Rule 6(a) allows.
That is the direction that loses a filing.

### THE CALENDAR IS THEREFORE THE STATUTORY INTERSECTION

Only two days survive all three provisions in all 82 counties — the two § 3-3-7(2)
expressly refuses to let a county trade away:

| Date | Day | Why it is safe |
|---|---|---|
| **2026-01-19** | Monday | Third Monday in January. § 3-3-7(2) forbids substitution; § 25-1-99 compels closure. Confirmed by the Supreme Court's notice posted 9 January 2026. |
| **2026-11-11** | Wednesday | 11 November, fixed date. Same two protections. No 2026 notice existed as of 2026-08-30 (the 2025 one was posted 21 October), so this rests on the statute and the prior-year notice. |

**Deliberately absent, every one of them EARLY:** New Year's Day, Washington's
Birthday, Confederate Memorial Day, National Memorial Day and Jefferson Davis's
birthday, Independence Day, Labor Day, Thanksgiving, Christmas — all substitutable
under § 3-3-7(2). Also absent: **Friday 3 July 2026**, which the Supreme Court
itself observed (4 July 2026 is a Saturday) but which § 25-1-99 makes optional per
county; the Governor's customary extra Thanksgiving-Friday, Christmas-Eve and
New-Year's-Eve days, which § 25-1-99 leaves to each board of supervisors; any
county's own adopted Mardi Gras or substitute day; and any weather or emergency
closure under Rule 6(a)'s "in fact closed" limb.

**The Sunday shift is mandatory and is dormant, not missing.** § 3-3-7(1) and Rule
6(a) both say a legal holiday falling on a Sunday makes the next day a legal
holiday. No § 3-3-7 holiday falls on a Sunday in 2026.

### WHY THIS IS THE WISCONSIN DESIGN AND NOT THE KANSAS ONE

Kansas keys its rollover on a day "observed as a holiday by order of the Kansas
supreme court" — a statewide legal fact — so the published list **is** the test
there, and a district court opening its doors does not change it. Mississippi keys
on a statutory definition **each county may lawfully alter**, plus actual closure.
The list is not the test, exactly as in Wisconsin.

One difference is worth stating in Mississippi's favour: Wisconsin's three-day
intersection was found by reading a 72-county closure matrix and could go stale
when a county changes its practice. Mississippi's two-day intersection is written
into **the statute's own exception clause**. That is stronger evidence, not weaker.

### THE APPELLATE CLOSURE NOTICES ARE EVIDENCE, NOT THE CALENDAR

Mississippi does not publish an annual judicial holiday schedule. It publishes
**one PDF per holiday**, for the Carroll Gartin Justice Building in Jackson — the
Supreme Court, the Court of Appeals and the AOC — not the 82 county courthouses
where the circuit and chancery clerks sit. As of 2026-08-30 exactly six exist for
2026 (MLK/Lee, Washington's Birthday, last Monday in April, Memorial Day/Jeff
Davis, Independence Day, Labor Day) and **none for Armistice Day, Thanksgiving or
Christmas**; the 2025 equivalents were posted 21 October, 4 November and 2
December. So the notices could not have supplied a full year even if they governed
the counties.

They are cited anyway, for two things they prove:

- **Independence Day 2026 is observed Friday, 3 July** at the Gartin building —
  the § 25-1-99 permissive Friday-before, which no rule text would have produced,
  since Rule 6(a) and § 3-3-7(1) both shift only from a **Sunday**.
- **Thanksgiving and Christmas are two-day closures** there (Thu 27 + Fri 28
  November 2025; Thu 25 + Fri 26 December 2025, and 1 + 2 January 2026), by
  gubernatorial proclamation — the discretionary days § 25-1-99 leaves to each
  county.

---

## 3. Service — period-lengthening, mail only, and an EXPRESS Rule 4 carve-out

**Miss. R. Civ. P. 6(e)**, verbatim and complete:

> Whenever a party has the right or is required to do some act or take some
> proceedings within a prescribed period after the service of a notice or other
> paper upon him and the notice or paper is served upon him **by mail, three days
> shall be added to the prescribed period**. **This subdivision does not apply to
> responses to service of summons under Rule 4.**

Three findings, and all three cut differently from the states seeded just before.

- **"ADDED TO THE PRESCRIBED PERIOD"** → period-lengthening, not the federal
  after-expiry order Kansas and Alabama use. The two diverge whenever the
  unextended last day lands on a weekend or holiday, and the seed's test pins the
  difference at two days on a base period landing on Saturday 7 November 2026.
- **MAIL AND NOTHING ELSE, AND MISSISSIPPI HAS HAD E-SERVICE SINCE 1989.** Rule
  5(b)(1) expressly permits service "by transmitting it to him by electronic
  means", by leaving it with the clerk, and by transmitting it to the clerk
  electronically; Rule 5(b)(2) routes service through the Mississippi Electronic
  Court System wherever a court has adopted it by local rule. **Rule 6(e) was
  never widened to reach any of them.** This is the ninth distinct answer on
  electronic service across the states gated. Kansas at least extends for leaving
  with the clerk; Mississippi does not even do that.
- **THE RULE 4 CARVE-OUT IS EXPRESS**, not inferred from the Rule 4 / Rule 5 split
  the way it is federally. The answer row therefore declares **no**
  `service_extension` field at all, so a caller who passes `service_method: "mail"`
  cannot collect three days the rule forbids — asserted as arithmetic rather than
  left to a convention.

---

## 4. Computation — seven, in both directions, and one constraint it forces

**Miss. R. Civ. P. 6(a)**: *"When the period of time prescribed or allowed is **less
than seven days**, intermediate Saturdays, Sundays, and legal holidays shall be
excluded in the computation."*

Seven, strict less-than, and **the rule draws no distinction between forward and
backward periods** — unlike Md. Rule 1-203(b), which expressly counts backward
periods including intervening weekends and holidays. So the exclusion applies both
ways.

**The running tally across seeded states, now wide enough that copying is
indefensible:** 7 for NJ, NC, WA, MA, MO, SC, Ohio, Indiana, Florida **and now
Mississippi**; 8 for Maryland ("seven days or less"); 11 for Tennessee, Arizona,
Wisconsin and Alabama; 14 for Arkansas; 6 for Texas ("five days or less"); and
**none at all** for Minnesota, Utah, Nevada and Kansas.

### THE ONE WAY MISSISSIPPI COULD COMPUTE LATE, AND HOW IT IS CLOSED

An under-inclusive calendar is safe **only while the count runs forward**. Counting
backward it inverts, in *both* mechanisms:

| | forward | backward |
|---|---|---|
| **last-day rollover** | omitted holiday → the date does not roll on → **EARLIER** ✔ | omitted holiday → the date does not roll *back* → **lands closer to the trigger, LATER than the true last date to act** ✘ |
| **short-period exclusion** | excludes fewer days → **EARLIER** ✔ | excludes fewer days → **lands closer to the trigger, LATER** ✘ |

The whole right-hand column is the risk, and it is closed **by construction, not by
luck**: **no Mississippi row is seeded backward at all.**

- **Rule 6(d)**'s "not later than **five** days before the time fixed for the
  hearing" and its "not later than **one** day before the hearing" for opposing
  affidavits — omitted.
- **Rule 56(c)**'s "The motion shall be served at least **ten** days before the time
  fixed for the hearing" — **also omitted, and this one is worth recording because
  the first draft of this seed kept it.** The reasoning was that ten clears the
  seven-day threshold so the exclusion never fires, which is true of the exclusion
  and irrelevant to the rollover. A hearing on **Thursday 7 May 2026** counts back
  to **Monday 27 April**, Confederate Memorial Day — a day this calendar omits
  precisely because § 3-3-7(2) lets a county trade it away. In a county that still
  observes it the true last day is **Friday 24 April**, three days earlier than the
  engine would have said. Correct in Jackson County, late everywhere else.

**A longer period does not rescue a backward row here. Only a complete
county-level calendar would.** The constraint is asserted over the seed file itself
in `api/_lib/deadline-mississippi.test.js`, not left to a reviewer, and it is
repeated in the engine comment on `ms_r_civ_p_6` so that the next person adding a
Mississippi row meets it before they write one.

---

## 5. Two elections and one floor, inside a single rule set

Mississippi's three discovery periods do **not** agree with each other, and the
deciding words are in the rules:

| Rule | Wording | Shape |
|---|---|---|
| 33(b)(3) | "a defendant **may** serve answers or objections within forty-five days after service of the summons and complaint" | **election** → plain 30-day row |
| 34(b)(ii)(A) | "a defendant **may** serve a response within forty-five days after service of the summons and complaint" | **election** → plain 30-day row |
| 36(a) | "a defendant **shall not be required** to serve answers or objections **before the expiration of** forty-five days after service of the summons" | **floor** → `resolve_periods: later_of` |

Arkansas made all three floors ("must … whichever is longer"); Kansas made all
three elections; **Mississippi is split, and joins South Carolina in making
admissions the mandatory one.** Encoding an election as a floor reports a date the
rule does not guarantee; encoding a floor as an election reports EARLY. The three
had to be read one at a time.

Note also that Rule 36(a)'s floor runs from "service of the **summons**", where
Rules 33 and 34 both say "the **summons and complaint**". The limb is named for
the rule's own words.

**The stakes are highest on the one that is a floor.** A missed Rule 36 date is not
a sanctions question — "The matter is admitted unless …" — and Rule 36(b) makes an
admission conclusively established unless the court permits withdrawal.

---

## 6. What was seeded, and what was deliberately left out

**Eleven rules, every one forward.** Answer to the summons and complaint (30);
answer to a cross-claim (30); plaintiff's answer to a counterclaim (30);
court-ordered reply (30); responsive pleading after a Rule 12 motion is denied or
postponed (10, from **notice**); responsive pleading after a more definite
statement (10, from **service**); interrogatory answers (30); production response
(30); admissions (later-of 30 / 45); motion for a new trial (10 from **entry of
judgment**); motion to alter or amend the judgment (10 from entry).

Rule 12(a) uses **one number for all four of its pleading periods**, which is
unusual enough to state: many states shorten the reply. And thirty is not twenty,
which is what most of Mississippi's neighbours use for the answer.

**The two Rule 59 rows are the only ones the court cannot enlarge.** Rule 6(b) names
them in its own prohibition — *"it may not extend the time for taking any action
under Rules 50(b), 52(b), 59(b), 59(d), 59(e), 60(b), and 60(c)"* — so no
stipulation or order rescues a caller who computed them wrong. Neither takes the
Rule 6(e) three days, because entry of judgment is not service of a paper.

**Deliberately not seeded, each for a stated reason:**

- **Rule 6(d)'s five-day motion notice and one-day opposing affidavit, and Rule
  56(c)'s ten-day motion service** — all backward; see §4.
- **Rule 50(b) JNOV** — ten days, but from *two alternative triggers* depending on
  whether a verdict was returned ("after entry of judgment in accordance with a
  verdict" / "within ten days after the jury has been discharged"). Which one
  applies is a fact the engine cannot determine from a single date. Left out rather
  than guessed.
- **Rule 34(b)(ii)(B) production itself** — "no later than the time for inspection
  specified in the request or another reasonable time specified in the response":
  a date set by the parties' own papers, not by the rule.
- **Rule 56(c)'s opposing affidavits** — "prior to the day of the hearing" is a
  boundary, not a period.
- **Rule 12(a)'s "or within such time as is directed pursuant to Rule 4"** and its
  once-only ten-day stipulated extension — both caller-supplied facts the engine
  cannot see, recorded in the row's own note.
- **Rule 12(a)'s "unless the order otherwise directs"** on the court-ordered reply
  — same.
- **M.R.A.P. 4's appeal clock**, which a timely Rule 59 motion tolls. That is an
  appellate rule and is out of this seed's domain; the Rule 59(e) row says so in
  its own note so nobody infers an appeal date from it.

---

## 7. Verdict

**PASS, and seeded.** The rules are free, official, complete and dated. The
statutory holiday definition is behind Lexis but is restated by the judicial branch
and corroborated by its own closure notices, so nothing in the seed rests on the
Lexis container. The calendar is deliberately two days long, every omission runs
EARLY, and the single shape that could run LATE is excluded from the seed by a
constraint the test file enforces.

**Before relying on a Mississippi date that falls on or near any holiday other than
the third Monday in January or 11 November, check that county courthouse's own
schedule.** That instruction rides on every successful Mississippi computation via
`JURISDICTION_COVERAGE.ms`.

### Live verification, 35/35 on `LAW-PINNACLE-2026`

Two passes, because "every rule returns a date" and "the calendar is actually read"
are different claims and only the second fails quietly.

**Pass 1** — all 11 rows return a real date.

**Pass 2** — the arithmetic, and it is mostly **negative** probes, because a
Mississippi calendar copied from § 3-3-7 would pass every positive one:

- The two days that ARE carried roll: a 30-day answer landing on **2026-11-11**
  goes to the 12th, and one landing on **2026-01-19** goes to the 20th.
- **Seven days that a statutory calendar would have carried do NOT roll** —
  2026-02-16, 2026-04-27, 2026-05-25, **2026-07-03**, 2026-09-07, 2026-11-26 and
  2026-12-25 each come back unchanged.
- Mailed interrogatories give **2026-11-10**, where the federal after-expiry order
  would give 2026-11-12 — two days apart on the same facts.
- The same row served **electronically** and **left with the clerk** each give
  2026-11-09, i.e. nothing added. Kansas would have extended the second.
- A **mailed summons** adds nothing to the answer (2026-11-09), while a **mailed
  cross-claim** does take the three days (2026-11-10). That pair is the Rule 4
  carve-out, proved in both directions.
- The admissions later-of returns 2026-11-04 when the 45-day floor governs and
  2026-11-02 when the plain 30 days does, and refuses `INCOMPLETE_TRIGGERS` on
  partial input.
- 2027 refuses `NOT_PROVISIONED`; a Rule 34 trigger on 2021-10-05 refuses
  `NO_RULE_IN_FORCE`.
- The coverage disclosure comes back over the wire with `complete:false`,
  `direction:"early"`, and names both § 3-3-7(2) and Jackson County.

**One defect was found by the load-state gate and fixed, not hidden.** The first
load stored all 11 rows with a server-stamped `authority.retrieved_at`, because the
seed rows omitted the field; `tools/sairn_load_state_check.py` reported all 11 as
STALE against the repo on a hash the endpoint and the tool compute identically. The
dates were correct throughout — the drift was provenance, not arithmetic — but a
licence that does not match its own seed file is exactly the state that gate exists
to catch. `retrieved_at: "2026-08-30"` was added to every row, the seed was
reloaded, and the gate now reports a clean match.
