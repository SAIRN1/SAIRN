# New Mexico — deadline-seed source-availability gate

**Run 2026-08-30. Verdict: PASS, and SEEDED the same day — 15 rules, calendar
2026 with eleven dates. Loaded to `LAW-PINNACLE-2026` and live-verified 37/37;
the licence now holds 31 jurisdictions and 352 rules, and
`tools/sairn_load_state_check.py` reports 352/352 and 138/138 with 0 missing,
0 stale, 0 extra.**

**The headline is a deletion, and it is the kind that computes LATE.** Supreme
Court Order No. S-1-RCR-2023-00046, approved 1 November 2024 and effective for
all cases pending or filed on or after **31 December 2024**, **struck "electronic
transmission," from Rule 1-006(C) NMRA.** Mail, facsimile and deposit at a
court-facility attorney location still carry three added days. **E-service and
e-filing now carry none.** Nearly every secondary source — including the first
page of search results for this rule — still quotes the pre-2024 list.

New Mexico (~2.1M) was chosen as the largest unseeded state without an existing
gate document, after Mississippi closed earlier the same day.

---

## 1. Sources — PASS, but not where a gate would look first

| What | URL | Result |
|---|---|---|
| **NMRA Rule Set 1 — Rules of Civil Procedure for the District Courts** | `nmonesource.com/nmos/nmra/en/5687/1/document.do` | **200, `application/pdf`, 5,668,940 B, 1,072 pages** |
| Rule 1-006 approved-amendment redline | `supremecourt.nmcourts.gov/wp-content/uploads/sites/2/2024/11/Rule-1-006-NMRA.pdf` | 200, 156,094 B |
| 2026 Judicial Branch holiday memorandum | `firstdistrict.nmcourts.gov/wp-content/uploads/sites/20/2026/01/2026-NMJB-Holiday-Schedule-11-19-25.pdf` | 200, 159,086 B |
| NMOneSource navigation | `nmonesource.com/nmos/nmra/en/nav.do` and `/nmos/nmr/en/nav.do` | **404 `application/json`** |
| `govt.westlaw.com/nmrules/…` | any path | 200 but a 6,088-byte JS shell |

**THE OFFICIAL PUBLISHER IS FREE AND THE OFFICIAL SITE IS NOT SCRAPEABLE, AND
BOTH HALVES OF THAT MATTER.** NMOneSource.com is the New Mexico Compilation
Commission's portal — "Official Legal Publisher of State of New Mexico", stated
on the page — and it is free, with Login and Sign up both optional. It is also a
Lexum Decisia/Qweri single-page application: its navigation endpoints return
**404 JSON** to `curl`, and every URL pattern guessed from search results
(`/nmos/nmr/en/nav.do`, `/w/nmos/Rule-Set-1-NMRA*.pdf`) 404s as well. Driving the
site once in a browser produced the one URL that matters, and **that URL is a
plain PDF on an ordinary `curl` with no gate, no sign-in and no click-through.**
This is the opposite of Colorado: the JavaScript was an obstacle, not a wall.

**THE SUPREME COURT SITE IS AN AMENDMENT ARCHIVE, NOT A RULE SET.** Its WordPress
media API lists per-rule PDFs — but only for rules **recently amended**, so Rules
1-012, 1-036 and 1-056 are not there at all. A gate that stopped at
`supremecourt.nmcourts.gov` would have concluded that three of the six rules it
needed did not exist.

### BOTH TEXTS WERE READ FOR RULE 1-006, AND NEITHER WOULD HAVE DONE ALONE

New Mexico's approved-amendment PDFs are **redlines**: bracketed text is deleted,
added text follows it. The 1 November 2024 Rule 1-006 PDF reads, in Paragraph C:

> service is made by mail, facsimile, **[electronic transmission,]** or by deposit
> at a location designated for an attorney at a court facility

and, in Paragraph (A)(7)(a):

> Labor Day, **[Columbus Day]**Indigenous Peoples Day, Veterans' Day

The second is self-verifying — deleting "Columbus Day" and adding "Indigenous
Peoples Day" is the only reading — which is what establishes the convention for
the first. But **a redline is not the operative text**, so the clean compilation
was read too, and Rule 1-006(C) there now reads "by mail, facsimile, or by
deposit at a location designated for an attorney at a court facility". Confirmed
in both directions: the redline shows that something was *removed*, which the
clean text alone could never show, and the clean text shows that the removal is
*in force*, which the redline alone could not.

### Currency

Effective dates are printed per rule in a bracket, and they are unusually spread
out — **seven distinct values across fifteen rows**, from a 1979 amendment to one
that took effect eight months ago.

| Rule | Bracket | effective_from |
|---|---|---|
| 1-006 (computation) | `… Supreme Court Order No. S-1-RCR-2023-00046, effective … on or after December 31, 2024.` | 2024-12-31 |
| 1-012 (answers) | `[As amended, effective August 1, 1989.]` | 1989-08-01 |
| 1-033 (interrogatories) | `… Order No. 09-8300-007, effective May 15, 2009.` | 2009-05-15 |
| 1-034 (production) | `… Order No. 21-8300-024, effective … on or after December 31, 2021.` | 2021-12-31 |
| 1-036 (admissions) | *(none — see below)* | **1980-01-01, a convention** |
| 1-055 (default) | `… Order No. S-1-RCR-2025-00174, effective … on or after December 31, 2025.` | **2025-12-31** |
| 1-056 (summary judgment) | `[As amended, effective August 1, 1989.]` | 1989-08-01 |
| 1-059 (new trial) | `… Order No. 13-8300-032, effective … on or after December 31, 2013.` | 2013-12-31 |
| 1-068 (offer of settlement) | `[As amended, effective August 1, 2003.]` | 2003-08-01 |

**ONE DATE IS A CONVENTION AND IS LABELLED AS ONE.** Rule 1-036 carries no
amendment bracket at all; its annotations refer three times to a "1979
amendment" with no date. It takes **1980-01-01** — the 1 January following the
last amending act, the same deliberately conservative rule Wisconsin needed. The
direction matters: too late merely refuses, too early answers for years when the
rule may have read differently.

**A ROW WAS DROPPED FOR WANT OF A DATE.** Rule 1-027(A)(2)'s twenty-day notice of
a petition to perpetuate testimony was drafted into this seed and then removed:
it has **no bracket and no amendment year mentioned anywhere in the rule**, so
there was no defensible `effective_from` and no honest convention to reach for.
Rule 1-068(A)'s ten-day acceptance window, which does carry a date, took its
place.

---

## 2. Computation — eleven, not the ten the rule prints

**Rule 1-006(A)(2)(a)**: *"When the period is stated in days but the number of
days is **ten (10) days or less** … exclude intermediate Saturdays, Sundays, and
legal holidays."*

Ten-or-less is `< 11`, and the engine field is a strict less-than, so the
threshold is **11**. New Mexico is the **third** jurisdiction where the rule's own
number and the field's number differ, after Texas ("five days or less" → 6) and
Maryland ("seven days or less" → 8) — and the one where getting it wrong is most
visible, because the two Rule 1-012(A) rows are **exactly ten days**.

**The running tally, now wide enough that copying is indefensible:** 7 for NJ,
NC, WA, MA, MO, SC, Ohio, Indiana, Florida and Mississippi; 8 for Maryland; **11
for Tennessee, Arizona, Wisconsin, Alabama and now New Mexico**; 14 for Arkansas;
6 for Texas; and none at all for Minnesota, Utah, Nevada and Kansas.

### (A)(6) IS AN EXPRESS DIRECTION RULE, AND IT IS WHY A SHORT BACKWARD ROW IS SAFE HERE

> **(6) "Next day" defined.** The "next day" is determined by continuing to count
> **forward** when the period is measured after an event and **backward** when
> measured before an event.

Only Fla. R. Gen. Prac. & Jud. Admin. 2.514(a)(5) says the same among the states
seeded. **The contrast with Mississippi, closed hours earlier the same day, is
exact:** Miss. R. Civ. P. 6(a) is silent on direction *and* its calendar is a
deliberately under-inclusive intersection, so every backward row there had to be
dropped — including a ten-day one. New Mexico states the direction and its
calendar is the judiciary's own complete list, so **Rule 1-055(B)'s three-day
notice of an application for default judgment is seeded**: short, backward, and
the exact shape Mississippi refused.

### One carve-out the engine cannot see

**Rule 1-006(A)(2)(b)**: *"This subparagraph shall not apply to any statutory
notice that is required to be given prior to the filing of an action."* The
committee commentary gives the Uniform Owner-Resident Relations Act's three-day
notice to pay rent as the example. No such notice is seeded, **and none may be
seeded on this standard** — it would be excluded when the rule says to count
straight through. Recorded in the standard's own comment so the next person meets
it before writing the row.

---

## 3. Service — federal order, spelled out in full, and one method removed

**Rule 1-006(C) NMRA**, as amended effective 31 December 2024, verbatim and
complete:

> When a party may or must act within a specified time after service and service
> is made by **mail, facsimile, or by deposit at a location designated for an
> attorney at a court facility** under Rule 1-005(C)(1)(e) NMRA, three (3) days
> are **added after the period would otherwise expire** under Paragraph A.
> **Intermediate Saturdays, Sundays, and legal holidays are included in counting
> these added three (3) days.** If the third day is a Saturday, Sunday, or legal
> holiday, the last day to act is the next day that is not a Saturday, Sunday, or
> legal holiday.

Three things.

- **THE ORDER IS FEDERAL after-expiry**, and New Mexico is the **only seeded
  jurisdiction whose text states the whole sequence** rather than leaving the
  second roll to be inferred. It even settles the question every other state
  leaves open: the three added days count **straight through** weekends and
  holidays *even when the base period excluded them*. One rule, two opposite
  counting modes, applied in sequence — and the seed's test pins it at
  `2026-12-02 → 2026-12-07`.
- **FACSIMILE SURVIVED AND ELECTRONIC TRANSMISSION DID NOT.** Rule 1-005(C)(1)(b)
  makes *"sending a copy by facsimile or electronic transmission"* **one sub-limb**
  of what "delivering a copy" means — the two are siblings in the service rule —
  and the time rule now reaches only one of them. That asymmetry is the rule's,
  not a transcription error, and it must not be tidied away.
- **NO CARVE-OUT FOR SERVICE OF PROCESS, SO ONE WAS READ RATHER THAN QUOTED.**
  Mississippi and Arkansas say expressly that their extension does not reach a
  response to a summons; New Mexico, like Wisconsin, says nothing. Three
  structural points resolve it: Rule 1-005(A) governs *"every pleading subsequent
  to the original complaint"*; original process is Rule 1-004; and Rule 1-006(C)
  defines its own third method by cross-reference **into** Rule 1-005(C)(1)(e). So
  the answer row carries no `service_extension` field at all. Withholding reports
  EARLY; granting it on a mailed summons would report LATE.

---

## 4. The calendar — the statutory test itself, and one date no rule produces

**Rule 1-006(A)(7)**: *"'Legal holiday' means the day that the following are
observed **by the judiciary**: (a) New Year's Day, Martin Luther King Jr.'s
Birthday, **Presidents' Day (traditionally observed on the day after
Thanksgiving)**, Memorial Day, Juneteenth, Independence Day, Labor Day,
Indigenous Peoples Day, Veterans' Day, Thanksgiving Day, or Christmas Day; and
(b) any other day observed as a holiday by the judiciary."*

New Mexico's district courts are **state administered** and the Chief Justice
publishes **one schedule for the whole branch**, so that schedule *is* the rule's
referent rather than a proxy for it. **This is the Kansas shape, not the Wisconsin
or Mississippi one** — in both of those the rollover keys on something a county
may lawfully vary, which is why their calendars are defensive intersections and
this one is complete for the year it covers.

Transcribed from the memorandum of **Chief Justice David K. Thomson, dated 19
November 2025**, and every printed weekday re-checked:

| Date | Day | Holiday |
|---|---|---|
| 2026-01-01 | Thu | New Year's Day |
| 2026-01-19 | Mon | Martin Luther King Jr. Day |
| 2026-05-25 | Mon | Memorial Day |
| 2026-06-19 | Fri | Juneteenth |
| **2026-07-03** | **Fri** | **Independence Day (observed)** — 4 July is a Saturday |
| 2026-09-07 | Mon | Labor Day |
| 2026-10-12 | Mon | Indigenous Peoples' Day |
| 2026-11-11 | Wed | Veterans Day |
| 2026-11-26 | Thu | Thanksgiving Day |
| **2026-11-27** | **Fri** | **Presidents' Day** |
| 2026-12-25 | Fri | Christmas Day |

**PRESIDENTS' DAY IS IN NOVEMBER.** New Mexico observes it on the day after
Thanksgiving, and the rule itself says so in a parenthetical. **No other calendar
in this platform moves a holiday to the far side of the year.** A generated
third-Monday-in-February date would be wrong twice at once: it would add
16 February, which the judiciary does not observe, and drop 27 November, which it
does. Both halves are asserted — a ten-day period from 16 November skips *both*
26 and 27 November, and a ten-day period spanning 16 February does not skip it.

**2027 IS REFUSED RATHER THAN DERIVED, and the temptation here is unusually
specific.** The 2026 memorandum announces exactly one 2027 date — New Year's Day
on Friday 1 January 2027. Opening a 2027 calendar on that single entry would let
2027 deadlines compute against a year missing ten of its eleven days, which reads
as an answer rather than the refusal it should be. A test asserts the calendar
holds `['2026']` and nothing else.

**What is not modelled, and it is always EARLY:** Rule 1-006(A)(4) extends a
**filing** deadline whenever *"the court is closed or is unavailable for filing at
any time that the court is regularly open"* — the committee commentary names
weather and technological problems, and says a person relying on it "should be
prepared to demonstrate or affirm" the closure. Per-court, unknowable in advance,
and a **separate limb** from the holiday list rather than part of it. Also not
modelled: Rule 1-006(A)(3)'s hours arithmetic (no seeded row is stated in hours),
and Rule 1-006(A)(5)'s split cut-off — **midnight for electronic filing, closing
time for everything else** — which this engine cannot express because it returns
a date rather than a moment.

---

## 5. Two elections and one floor — the same split as Mississippi

| Rule | Wording | Shape |
|---|---|---|
| 1-033(C)(3) | "a defendant **may** serve answers or objections within forty-five (45) days" | election → plain 30-day row |
| 1-034(B) | "a defendant **may** serve a response within forty-five (45) days" | election → plain 30-day row |
| 1-036(A) | "a defendant **shall not be required** to serve answers or objections **before the expiration of** forty-five (45) days" | **floor** → `resolve_periods: later_of` |

Arkansas made all three floors; Kansas made all three elections; New Mexico joins
**Mississippi and South Carolina** in making admissions alone mandatory — and it
is the self-executing one, where *"the matter is admitted unless …"*.

---

## 6. What was seeded, and what was deliberately left out

**Fifteen rules.** Answer to the summons and complaint (30); answer to a
cross-claim (30); reply to a counterclaim (30, **from service of the answer**);
court-ordered reply (30); responsive pleading after a Rule 1-012 motion is denied
(10, **from the court's action**); responsive pleading after a more definite
statement (10, **from service**); interrogatory answers (30); production response
(30); admissions (later-of 30 / 45); summary-judgment opposing memorandum (15);
summary-judgment reply memorandum (15); motion for a new trial (30 from entry);
motion to alter, amend or reconsider (30 from entry); default-judgment notice
(**3 backward**); acceptance of an offer of settlement (10).

**Two pairs exist specifically because the rule distinguishes them and a reader
would not:**

- The two ten-day Rule 1-012 rows differ on **both** their trigger (*"the court's
  action"* vs *"service of the more definite statement"*) **and** on whether the
  three-day extension reaches them. Mississippi's analogue runs from *notice* of
  the court's action; a caller who supplies a notice date here computes LATE.
- The reply to a counterclaim runs from **service of the answer**, where
  Mississippi's runs from service of the counterclaim. In the ordinary case the
  counterclaim is *in* the answer and the dates coincide — which is exactly why
  the difference is easy to miss.

**THIRTY, NOT TEN, ON THE POST-JUDGMENT MOTIONS, and the commentary says the old
number out loud:** *"With the exception of Rule 1-060 NMRA, the time limit **had
been** ten (10) days."* The 2013 amendment moved every post-judgment motion to
thirty. A ten-day figure carried from an older source would report **twenty days
early** — and Rule 1-006(B)(2) forbids the court to enlarge any of them.

**Deliberately not seeded, each for a stated reason:**

- **Rule 1-027(A)(2)'s twenty-day notice** — no printed effective date anywhere in
  the rule; see §1.
- **Rule 1-068(A)'s "at any time more than ten (10) days before the trial
  begins"** — a boundary expressed as a strict inequality, not a period.
  Converting "more than ten" into a backward eleven-day count would be a reading,
  not a quotation.
- **Rule 1-068(A)'s 120-day claimant waiting period** — runs from "the filing of a
  responsive pleading", a filing date the engine is not given.
- **Rule 1-056(D)(1)** — "within a reasonable time prior to the date of trial" is
  a standard, not a period.
- **Rule 1-034(B)'s production itself** — the request must "specify a reasonable
  time, place, and manner", set by the parties' own papers.
- **Rule 1-012(A)'s "unless a different time is fixed by order of the court"** and
  Rule 1-033's "shorter or longer time … agreed to in writing by the parties" —
  caller-supplied facts, recorded in each row's own note.
- **Rule 12-201 NMRA's appeal clock**, which the Rule 1-059 rows tolls. Appellate
  rules are out of this seed's domain, and the 1-059(E) row says so in its note so
  nobody infers an appeal date from it.

---

## 7. Verdict

**PASS, and seeded.** The complete current rules are free, official, dated and
reachable by a plain request once the right URL is known. The holiday definition
points at a single branch-wide schedule that the Chief Justice publishes, so the
calendar is the statutory test rather than a proxy for it, and it is complete for
2026. Every gap disclosed runs EARLY. The one reading made rather than quoted —
that Rule 1-006(C) does not reach service of process — was resolved in the
direction that reports early.

**The finding to carry forward is the deletion.** If anything in this
jurisdiction is ever re-derived from a secondary source, it will grant three days
for electronic service, and that is three days late on every e-served deadline in
New Mexico.

### Live verification, 37/37 on `LAW-PINNACLE-2026`

**Pass 1** — all 15 rows return a real date.

**Pass 2** — the arithmetic, and it is built around the two things that would go
wrong silently:

- **The threshold, proved by an inversion.** A **ten**-day period from Monday
  16 November 2026 returns **2026-12-02**; a **fifteen**-day period from the same
  trigger returns **2026-12-01**. The longer period lands *earlier*, which only
  happens if the exclusion really fires at ten and really does not at fifteen.
- **Presidents' Day in November, probed in both directions.** The ten-day period
  above skips **both** 26 and 27 November. A 30-day period landing on Friday
  27 November rolls to Monday **2026-11-30**. And a ten-day period spanning
  16 February returns **2026-02-23** — it does *not* skip the third Monday in
  February, which a generated calendar would have added.
- **Short and backward.** The three-day default-judgment notice from a hearing on
  16 November returns **2026-11-10**, having counted back over Veterans Day. That
  is the shape Mississippi had to refuse hours earlier.
- **The service deletion, four ways.** Mail → **2026-12-07**; facsimile →
  **2026-12-07**; **electronic → 2026-12-02**; **e-filing service provider →
  2026-12-02**. The mailed date also proves both halves of Rule 1-006(C)'s own
  sentence at once: the base period had already excluded two holidays, the three
  added days counted straight through to Saturday 5 December, and the result then
  rolled to Monday the 7th.
- **The second roll is conditional, not automatic.** A fifteen-day period served
  by mail returns **2026-12-04**, a Friday, with no further roll.
- **The process reading, both ways.** A mailed summons adds nothing to the answer
  (**2026-12-16** with and without `service_method`), while a mailed cross-claim
  takes the three days (**2026-12-21**).
- **The two ten-day rows differ.** The post-motion row returns **2026-12-02** with
  `service_method: mail` supplied and ignored, because it runs from the court's
  action rather than from service.
- **Refusals.** 2027 → `NOT_PROVISIONED`. Rule 1-055 on 2025-12-20 →
  `NO_RULE_IN_FORCE`. Rule 1-034 on 2021-12-20 → `NO_RULE_IN_FORCE`. Partial
  admissions triggers → `INCOMPLETE_TRIGGERS`.
- **A control on the neighbour.** Mississippi, loaded hours earlier, still returns
  nothing for facsimile and three days for mail on the same shape of request —
  so New Mexico's facsimile limb did not leak across.
