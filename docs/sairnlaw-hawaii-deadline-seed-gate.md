# Hawaiʻi — deadline-seed source-availability gate

**Run 2026-08-31. Verdict: PASS, and SEEDED the same day — 11 rules, calendar
2026 with thirteen dates. Loaded to `LAW-PINNACLE-2026` and live-verified 33/33;
the licence now holds 34 jurisdictions and 384 rules, and
`tools/sairn_load_state_check.py` reports 0 missing, 0 stale, 0 extra.**

**Two headline findings.**

**TWO DAYS FOR MAILED SERVICE, NOT THREE.** Haw. R. Civ. P. 6(e): *"2 days shall
be added to the prescribed period."* Hawaiʻi is the **only seeded jurisdiction
that says two**. Every FRCP-family state adds three, South Carolina and New
Jersey add five, California and New York use per-method tables. An `add: 3`
copied from any neighbour over-counts by a day on every mailed Hawaiʻi deadline —
the direction that reports LATE.

**FOUR HOLIDAYS THAT EXIST ON NO OTHER CALENDAR IN THIS PLATFORM** — Prince Jonah
Kūhiō Kalanianaʻole Day, King Kamehameha I Day, Statehood Day, and **Good
Friday**, the only computed-from-Easter date in the whole engine.

Hawaiʻi (~1.4M) was chosen as the largest unseeded state without an existing gate
document, after Nebraska closed the previous day.

---

## 1. Sources — PASS

| What | URL | Result |
|---|---|---|
| **Hawaiʻi Rules of Civil Procedure, complete** | `courts.state.hi.us/wp-content/uploads/2024/09/hrcp_ada.htm` | **200, 1,363,985 B, whole rule set as one HTML document** |
| HRS § 8-1 (holidays designated) | `capitol.hawaii.gov/hrscurrent/…/HRS_0008-0001.htm` | 200 |
| HRS § 8-2 (weekend observance) | `…/HRS_0008-0002.htm` | 200 |
| HRS § 1-29 (computation of time) | `…/HRS_0001-0029.htm` | 200 |
| `courts.state.hi.us/docs/court_rules/rules/hrcp.htm` | — | 404 |
| Justia HRS § 8-1 | — | **403** |

Free, official, no gate. The Judiciary serves the entire HRCP as one plain HTML
document and the Legislature serves each statute section as its own page.

**THE UPLOAD PATH IS MISLEADING AND IS WORTH RECORDING.** The rule set lives under
`/wp-content/uploads/**2024/09**/` — yet its own text records amendments
*"effective July 1, 2026"*. The file is maintained in place, so **the date in the
path says nothing about currency**. A gate that inferred staleness from the URL
would have rejected a current document; one that inferred currency from it would
be trusting a directory name.

### Currency

| Rule | Amendment note | effective_from |
|---|---|---|
| 6 (computation) | *…amended July 9, 2025, effective January 1, 2026; corrected December 19, 2025; further amended May 21, 2026, effective July 1, 2026* | n/a (standard) |
| 12 (pleadings) | *…further amended December 7, 1999, effective January 1, 2000* | 2000-01-01 |
| 33, 34 (discovery) | *…further amended August 29, 2014, effective January 1, 2015* | 2015-01-01 |
| 36 (admissions) | *…amended July 9, 2025, **effective January 1, 2026**; further corrected December 19, 2025* | **2026-01-01** |
| 59 (new trial) | *…further amended December 7, 1999, effective January 1, 2000* | 2000-01-01 |

**Rule 6 was amended twice in the last year and Rule 36 once.** The text encoded
is the current one. **What those amendments changed was NOT determined** — the
document carries an amendment history and no redline, and guessing would be worse
than recording the gap. That is stated in the coverage entry rather than left
implicit.

---

## 2. Computation — an EXPRESS referent, which is what Idaho's was not

**Haw. R. Civ. P. 6(a)**, closing sentence:

> As used in these rules, **"holiday" shall mean any day designated as such
> pursuant to section 8-1 of the Hawaiʻi Revised Statutes.**

One section, named by number. **The contrast with Idaho, seeded the day before,
is exact**: there I.R.C.P. 2.2 said "legal holiday" and stopped, nothing in the
civil or appellate rules defined it, and three published lists disagreed. Hawaiʻi
removes the question in a sentence.

**Threshold is SEVEN**, a strict less-than: *"When the period of time prescribed
or allowed is **less than 7 days**, intermediate Saturdays, Sundays and holidays
shall be excluded."*

**Note the bare word.** Rule 6(a) rolls off *"a Saturday, a Sunday or **a
holiday**"* — never "legal holiday" — which is why the definitional sentence at
the end of the paragraph is load-bearing rather than decorative.

### No direction rule, so no backward row is seeded

Rule 6(a) rolls to *"the **next** day"* and says nothing about a period measured
before an event — the Mississippi, Idaho and Nebraska shape, not New Mexico's.

**Hawaiʻi has the longest motion-notice period of any seeded jurisdiction and it
is not seeded.** Rule 6(d) requires a written motion and notice of hearing to be
served **not less than 18 days** before the hearing, and opposing affidavits **not
less than 8 days** before. Both clear the seven-day exclusion threshold, so the
short-period rule is *not* the obstacle here — the missing direction rule is, on
its own.

---

## 3. Service — two days, mail only, and it has the notice limb

**Haw. R. Civ. P. 6(e)**, verbatim and complete:

> Whenever a party has the right or is required to do some act or take some
> proceedings within a prescribed period after the service of a **notice or other
> paper** upon the party and the notice or paper is served upon the party **by
> mail, 2 days shall be added to the prescribed period.**

- **TWO DAYS.** The only two on the platform. Asserted twice: once as a field
  (`add: 2` on every row, and no row carrying 3) and once as a **date** — base
  Friday 20 March 2026 plus two is Sunday the 22nd, rolled to **Monday the 23rd**,
  where three days would have given Tuesday the 24th.
- **MAIL ONLY** — no electronic limb, no commercial carrier, nothing else.
- **"ADDED TO THE PRESCRIBED PERIOD"** → period-lengthening, not the federal
  after-expiry order.

### THE NOTICE LIMB — a third answer to a question two states already split on

Four seeded jurisdictions run the post-Rule-12-motion period from **"notice of the
court's action"**:

| | the time rule reaches | that row takes |
|---|---|---|
| Mississippi | 6(e): *"the service of a **notice** or other paper"* | +3 |
| **Hawaiʻi** | 6(e): *"the service of a **notice** or other paper"* | **+2** |
| Idaho | 2.2(c): *"after **service**"* | nothing |
| Nebraska | § 6-1106(c): *"after **being served**"* | nothing |

**The answer is decided every time by the TIME rule, never by the pleading rule** —
and it is now three different answers on identical trigger words. All four are
asserted live in the same run.

**No row triggered by service of process carries it.** Original process is served
under Rule 4, not as a Rule 5 paper. Withholding reports EARLY.

---

## 4. The calendar — four unique holidays, three deliberate omissions

**HRS § 8-1** designates fifteen entries; thirteen are fixed or derivable for
2026 and are seeded.

| Date | Day | Holiday |
|---|---|---|
| 2026-01-01 | Thu | New Year's Day |
| 2026-01-19 | Mon | Dr. Martin Luther King, Jr., Day |
| 2026-02-16 | Mon | Presidents' Day |
| **2026-03-26** | **Thu** | **Prince Jonah Kūhiō Kalanianaʻole Day** |
| **2026-04-03** | **Fri** | **Good Friday** — *"the Friday preceding Easter Sunday"* |
| 2026-05-25 | Mon | Memorial Day |
| **2026-06-11** | **Thu** | **King Kamehameha I Day** |
| 2026-07-04 | Sat | Independence Day |
| **2026-08-21** | **Fri** | **Statehood Day** — *"the third Friday in August"*, a floating date |
| 2026-09-07 | Mon | Labor Day |
| 2026-11-11 | Wed | Veterans' Day |
| 2026-11-26 | Thu | Thanksgiving Day |
| 2026-12-25 | Fri | Christmas Day |

**GOOD FRIDAY IS THE ONLY COMPUTED-FROM-EASTER DATE IN THE WHOLE ENGINE.** § 8-1
says *"the Friday preceding Easter Sunday"*, so it is derived from the computus
rather than read off a schedule: Easter 2026 is Sunday 5 April, so Good Friday is
3 April. It is also the only religious observance any seeded state makes a legal
holiday, and the statute's own case note records that the provision survived an
Establishment Clause challenge — **932 F.2d 765**.

**And three that its neighbours have and Hawaiʻi does not:** no Juneteenth, no
Columbus or Indigenous Peoples' Day, no day after Thanksgiving. **Nebraska
enumerates all three.** A calendar copied from Nebraska would add three days
Hawaiʻi does not have and miss four it does.

### OMISSION 1 — the § 8-2 weekend shift, and it is a reading

**HRS § 8-2** provides that a state holiday falling on Sunday is observed the
following Monday and one falling on **Saturday is observed the preceding Friday**.
It is not carried.

**Why.** Rule 6(a) incorporates **section 8-1 by number**, and a § 8-2 day is
designated pursuant to § 8-2. **Idaho and Nebraska both carry their shifts because
in those states the shift clause sits in the SAME section the rule points at** —
Idaho Code § 73-108 and Neb. Rev. Stat. § 25-2221 each contain their own. Hawaiʻi's
does not.

Both readings are respectable, so the direction decides: omitting reports EARLIER,
carrying would roll a deadline off a possibly-countable day and report LATER.

**IN 2026 THIS AFFECTS EXACTLY ONE DATE.** 4 July is a Saturday, so § 8-2 would
make **Friday 3 July 2026** an observed holiday, and this calendar does not carry
it. No other § 8-1 holiday falls on a weekend in 2026. **A practitioner will treat
that Friday as a court holiday** — the coverage entry says so and names the date.
The negative is probed live, alongside Idaho and Nebraska rolling their own
3 July.

### OMISSION 2 — the general election day

§ 8-1 designates *"all election days, except primary and special election days,
**in the county wherein the election is held**"* — **county-scoped by its own
words**, and requiring a second statute to fix the date. Neither was resolved on a
primary source here, so the day is **omitted rather than computed**. A Hawaiʻi
deadline landing on a general election day needs checking by hand.

### OMISSION 3 — the proclamation limb

*"Any day designated by proclamation by the President of the United States or by
the governor as a holiday."* The open limb every jurisdiction has and none can
model.

All three omissions run **EARLY**.

**2026 only.** Twelve of the thirteen would generate mechanically and Good Friday
from the computus — which is precisely why a later year is refused. Generating
would hide the § 8-2, election-day and proclamation questions behind a confident
answer.

---

## 5. Two elections and one floor

| Rule | Wording | Shape |
|---|---|---|
| 33(b)(3) | a defendant **may** serve answers or objections within 45 days | election → plain 30 |
| 34(b) | a defendant **may** serve a response within 45 days | election → plain 30 |
| 36(a) | a defendant **shall not be required** to serve **before the expiration of** 45 days | **floor** → `later_of` |

Hawaiʻi joins Mississippi, New Mexico and South Carolina. Rule 36 is
self-executing — *"The matter is admitted unless…"* — which is where reading the
wrong shape costs most.

**And contrast Nebraska, seeded the day before**, whose § 6-333(b)(2) says *"may"*
**and** *"whichever is longer"* in one sentence: there the comparative governs and
the same word produces a floor. The word alone does not settle it; the sentence
does.

---

## 6. What was seeded, and what was deliberately left out

**Eleven rules, every one forward.** Answer to the summons and complaint (20);
answer to a cross-claim (20); reply to a counterclaim (20, **from service of the
answer**); reply when ordered (20); responsive pleading after a Rule 12 motion is
denied (10, from **notice**); responsive pleading after a more definite statement
(10, from **service**); interrogatory answers (30); production response (30);
admissions (later-of 30 / 45); motion for a new trial (10 from entry); motion to
alter or amend (10 from entry).

**Twenty days, the pre-2009 federal number**, kept when the FRCP moved to
twenty-one — and Hawaiʻi uses the same figure for all four Rule 12(a) periods, as
Mississippi does with thirty.

**Rule 6(b)'s non-extendable list reaches into another rule set**, which no other
seeded jurisdiction's Rule 6 does: *"it may not extend the time for taking any
action under Rules 50(b), 52(b), 59(b), (d) and (e) and 60(b) of these rules **and
Rule 4(a) of the Hawaiʻi Rules of Appellate Procedure**."*

**Deliberately not seeded:**

- **Every backward row** — Rule 6(d)'s 18-day motion notice and 8-day opposing
  affidavits; see §2.
- **Rule 12(a)(1)'s Rule 4(c) carve-out** — *"except when service is made under
  Rule 4(c) and a different time is prescribed in an order of court"*: a period
  set by the order itself.
- **Rule 34's production itself** — a time set by the parties' own papers.
- **HRAP Rule 4(a)**, which Rule 6(b) freezes but which belongs to the appellate
  rules.

---

## 7. Verdict

**PASS, and seeded.** The whole rule set is one free official HTML document, the
holiday referent is named by section number in the rule's own text, and the
statute is equally free. Every gap disclosed runs EARLY, and the one interpretive
call — the § 8-2 shift — is stated as a reading with the single affected 2026 date
named.

**Two things to carry forward.** *Two days, not three* — the single most
copy-prone number in this jurisdiction. And the URL path date: a document under
`/uploads/2024/09/` recording amendments effective July 2026 is a reminder that
**a path is not a publication date**.

### Live verification, 33/33 on `LAW-PINNACLE-2026`

- **Two days proved as a date**: mailed → **2026-03-23**, and *not* the 24th that
  three days would have produced. Idaho and Nebraska still add three on their own
  facts in the same run.
- **All four unique holidays roll**: Prince Kūhiō → 2026-03-27, Good Friday →
  **2026-04-06** (through the weekend to Easter Monday), King Kamehameha →
  2026-06-12, Statehood Day → 2026-08-24.
- **Both omissions probed as negatives**, each against a jurisdiction that does the
  opposite: Friday 3 July does **not** roll in Hawaiʻi (2026-07-03) while Idaho and
  Nebraska both roll to 2026-07-06; Juneteenth does **not** roll in Hawaiʻi
  (2026-06-19) while Nebraska rolls to 2026-06-22.
- **The notice limb across four states in one run**: Hawaiʻi 2026-03-20 → 2026-03-23
  mailed; Idaho and Nebraska unchanged on the same trigger.
- **The later-of** returns 2026-04-15 when the floor governs and 2026-04-09 when it
  does not; partial triggers refuse.
- **Refusals**: 2027 → `NOT_PROVISIONED`; admissions before 1 January 2026 →
  `NO_RULE_IN_FORCE`.
- The coverage disclosure rides on the answer with `complete:false`,
  `direction:"early"`, naming § 8-2 and Friday 3 July 2026 by date.
