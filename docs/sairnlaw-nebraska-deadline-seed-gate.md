# Nebraska — deadline-seed source-availability gate

**Run 2026-08-30. Verdict: PASS, and SEEDED the same day — 10 rules, calendar
2026 with fourteen dates. Loaded to `LAW-PINNACLE-2026` and live-verified 30/30;
the licence now holds 33 jurisdictions and 373 rules, and
`tools/sairn_load_state_check.py` reports 373/373 and 140/140 with 0 missing,
0 stale, 0 extra.**

**Two findings, and the first is unusual enough to lead with: a court named this
engine's exact ambiguity and amended its rule to settle it.** Comment [2] to
Neb. Ct. R. Pldg. § 6-1106 says the old mail-extension rule left it *"unclear
whether the 3 days were added to the time period itself or at the end of the time
period"*, and that the 2024 amendment reworded it to say **after the period would
otherwise expire**. That is the `add_to_period_then_roll` /
`roll_then_add_then_roll` distinction, identified as genuinely ambiguous by the
body that wrote the rule. Comment [3] then works an example, and the engine is
asserted against it.

**The second: the prior versions of both rule articles are still published,
correctly labelled, and one click away — and the 2025 amendments moved real
numbers.**

Nebraska (~2.0M) was chosen as the largest unseeded state without an existing
gate document, after Idaho closed earlier the same day.

---

## 1. Sources — PASS

| What | URL | Result |
|---|---|---|
| **Article 11 — Rules of Pleading (current)** | `nebraskajudicial.gov/book/export/html/9131` | **200, 83,044 B, 32 rule headings** |
| **Article 3 — Rules of Discovery (current)** | `nebraskajudicial.gov/book/export/html/9064` | **200, 186,527 B, 15 rule headings** |
| Article 11 — **prior version** | `…/book/export/html/24459` | **200, 51,678 B — a complete, live document** |
| Neb. Rev. Stat. § 25-2221 (computation + holidays) | `nebraskalegislature.gov/laws/statutes.php?statute=25-2221` | 200 |
| § 25-1144.01, § 25-1329 (post-judgment motions) | `…?statute=25-1144.01`, `…=25-1329` | 200 |
| `supremecourt.nebraska.gov/rules/pleading-civil-cases` | — | 404 |

Free, official, no gate, no sign-in. The judicial branch exposes a
`book/export/html/<id>` endpoint that returns a whole article as one document —
the cleanest bulk source of any state gated so far.

### THE TRAP HERE IS THE OPPOSITE OF MISSISSIPPI'S, AND MORE DANGEROUS

`nebraskajudicial.gov` lists, adjacent to each other:

- *Article 11: Nebraska Court Rules of Pleading in Civil Cases. **(Effective
  January 1, 2025.)***
- *Prior Version of Article 11 … **(Effective before January 1, 2025.)***

and the same pair for Article 3. **Both are real, complete, correctly labelled
documents.** Mississippi's superseded link was a dead soft-404 — requesting it
returned HTML and no PDF, so a scraper got nothing and a reader noticed. Here a
scraper gets a **complete and plausible rule set that is simply not the law**, and
the label is the only thing distinguishing them.

**The 2025 amendments moved real numbers.** Read from both documents side by side:

| Row | Prior (before 2025-01-01) | Current |
|---|---|---|
| Responsive pleading after a Rule 12 motion is denied | **20 days** | **21 days** |
| Responsive pleading after a more definite statement | **20 days** | **21 days** |
| Reply after an order to reply | **15 days** | **21 days** |
| Answer to summons and complaint | 30 days | 30 days |

A seed built from the prior page reports one day early on two rows and **six days
early** on a third. Early is the safe direction and it is still wrong. Every
seeded row carries the current number with `effective_from: 2025-01-01`, and a
pre-2025 trigger **refuses** rather than answering with a number that was not yet
law — asserted both locally and live.

### Currency

| Rule | Note | effective_from |
|---|---|---|
| § 6-1106 (time) | amended 13 Nov 2024, effective 1 Jan 2025 | 2025-01-01 |
| § 6-1112 (pleadings) | Article 11 effective 1 Jan 2025 | 2025-01-01 |
| §§ 6-333 / 6-334 / 6-336 (discovery) | Article 3 effective 1 Jan 2025 | 2025-01-01 |
| Neb. Rev. Stat. §§ 25-1144.01, 25-1329 | Laws 2000 LB 921; Laws 2004 LB 1207 — **no effective date printed** | **2005-01-01, a convention** |

**One date is a convention and is labelled as one.** The Legislature's pages print
a source history and no effective date. Both statutes take **1 January following
the last amending act**, the same conservative rule Wisconsin and New Mexico's
Rule 1-036 needed. Too late merely refuses; too early would answer for a period
when the section may have read differently.

**A dead section, recorded because a pre-2000 source would send you to it:**
Neb. Rev. Stat. **§ 25-1143**, the old new-trial section, was **repealed by Laws
2000, LB 921, § 38**. The Legislature's page for it now returns nothing but
*"Repealed."* The motion is now **§ 25-1144.01**.

---

## 2. Computation — a statute, and the rule says so in its first line

**Neb. Ct. R. Pldg. § 6-1106(a):** *"Neb. Rev. Stat. § 25-2221 governs the
computation of time periods."*

No chain to trace. Contrast Idaho, seeded hours earlier, where I.R.C.P. 2.2 said
"legal holiday" and stopped, and the referent had to be established through a
second statute's definition section.

**§ 25-2221**, first paragraph: *"the period of time … shall be computed by
excluding the day of the act, event, or default … The last day of the period so
computed shall be included unless it is a Saturday, a Sunday, or a day during
which the offices of courts of record may be legally closed **as provided in this
section**, in which event the period shall run until the end of the next day on
which the office will be open."*

**No short-period exclusion.** Sixth seeded jurisdiction with none, after
Minnesota, Utah, Nevada, Kansas and Idaho.

**No citation suffixes.** § 25-2221 is a single unsubdivided section — there is no
paragraph to cite past the number — so every suffix on the standard is empty
rather than guessed, and a test asserts that.

**No backward row is seeded.** The statute rolls to *"the **next** day on which
the office will be open"* and says nothing about a period measured before an
event — the Mississippi and Idaho shape, not New Mexico's. Nebraska's calendar is
materially more complete than Idaho's so the case is weaker here, but the
direction question has not been read out of any Nebraska text and is not being
guessed.

---

## 3. Service — the court settled it, in writing, and worked an example

**§ 6-1106(c)**, verbatim: *"When a party may or must act within a specified time
after being served and service is made under § 6-1105(b)(3)(C), 3 days are
**added after the period would otherwise expire**."*

### ★ COMMENT [2] IS THE FINDING

> The original version of the rule provided that 3 days were added to the
> applicable time period when a document was served by mail. **It was unclear
> whether the 3 days were added to the time period itself or at the end of the
> time period** as computed by § 25-2221. In 2024, the provision — which now
> appears in subpart (c) — was reworded to clarify that the 3 days are added
> after the period would otherwise expire.

Every other jurisdiction on this platform had to be *read* for this distinction,
and several were close calls. Nebraska's rules committee identified the same
ambiguity, said so, and amended the text to remove it. It also means **any
Nebraska mailed deadline computed against the pre-2025 wording may be a day out**,
which is a second reason the prior version being live matters.

### Comment [3] works an example, and the engine matches it

> answers to interrogatories are normally due 30 days after service … If the 30th
> day is a Saturday, the period would expire on Monday … Adding 3 days after the
> period would otherwise expire (Monday) extends the period to **Thursday**.

Interrogatories served Thursday 19 February 2026: +30 lands on Saturday 21 March,
expires **Monday 23 March**, and mailed service gives **Thursday 26 March**. Both
halves are asserted — the unmailed date proves the "expire on Monday" step — plus
a third assertion that period-lengthening's Tuesday 24 March is *not* what comes
back.

### Mail only, and the drafting is the sharpest on the platform

§ 6-1106(c) does not say "by mail". It cross-references **one lettered
subparagraph** — § 6-1105(b)(3)(C) — out of six sibling methods listed beside it:
(A) handing it to the person, (B) leaving it at an office or residence, **(C)
mailing**, (D) email, (E) a designated delivery service under Neb. Rev. Stat.
§ 25-505.01(1)(d), and (F) any other consented or court-authorised means.
Electronic service through the court-authorized service provider is a separate
limb again, § 6-1105(b)(2). **Five named alternatives get nothing, and the rule
picked one by letter.** Asserted live on email, designated delivery service and
e-filing.

**No row triggered by service of process carries it.** § 6-1105(a)(1)(A) reaches
*"a pleading filed after the original complaint"*; original process is not Rule 5
service. Withholding reports EARLY. Same reading as Wisconsin, Idaho and New
Mexico.

**And the notice/service split is the Idaho shape, not the Mississippi one.**
§ 6-1106(c) reaches a party who must act *"after **being served**"*, with no
notice limb, where Miss. R. Civ. P. 6(e) expressly reaches *"the service of a
**notice** or other paper"*. So Nebraska's post-motion row — triggered by "notice
of the court's action" — takes nothing, and its more-definite-statement sibling
takes three. Three states now run the same trigger words to two different
answers, decided by the time rule rather than the pleading rule.

---

## 4. The calendar — the statute carries its own list

**§ 25-2221 rolls off "a day during which the offices of courts of record may be
legally closed as provided in this section" — and enumerates them in the very
next sentence.** The rollover test and the holiday list are the same text. No
other seeded jurisdiction manages that: Kansas points at a supreme court order,
New Mexico at what the judiciary observes, Idaho at a statute in a different
title, Mississippi at a statute that lets counties amend it.

**Fourteen dates for 2026**, each derived from the statute's own words and checked
by weekday:

| Date | Day | Entry |
|---|---|---|
| 2026-01-01 | Thu | New Year's Day |
| 2026-01-19 | Mon | Birthday of Martin Luther King, Jr. |
| 2026-02-16 | Mon | President's Day |
| **2026-04-24** | **Fri** | **Arbor Day, the last Friday in April** |
| 2026-05-25 | Mon | Memorial Day |
| **2026-06-19** | **Fri** | **Juneteenth National Independence Day** |
| **2026-07-03** | **Fri** | Independence Day — derived from the mandatory Saturday shift |
| 2026-07-04 | Sat | Independence Day |
| 2026-09-07 | Mon | Labor Day |
| 2026-10-12 | Mon | **"Indigenous Peoples' Day and Columbus Day"** — one day, two names |
| 2026-11-11 | Wed | Veterans Day |
| 2026-11-26 | Thu | Thanksgiving Day |
| **2026-11-27** | **Fri** | **The day after Thanksgiving — enumerated in the statute** |
| 2026-12-25 | Fri | Christmas Day |

**ARBOR DAY EXISTS ON NO OTHER CALENDAR IN THIS PLATFORM.** Nebraska founded the
holiday in 1872 and is the only state to make it a nonjudicial day. It is a
**floating** date — the last Friday in April — so a copied calendar misses it
entirely and a hardcoded one gets it wrong every other year.

**THE CONTRAST WITH ITS NEIGHBOUR IS THREE DAYS WIDE.** Idaho Code § 73-108 has
**no Juneteenth** and **no day after Thanksgiving**, and nothing anywhere has
Arbor Day. Idaho and Nebraska were seeded within hours of each other and their
statutory lists disagree on three days. Both facts are asserted live, in both
directions, against both jurisdictions on the same platform.

**The day after Thanksgiving is enumerated in the statute**, not derived from an
administrative schedule — unlike Kansas, South Carolina, Wisconsin and Maryland,
which carry it from a published judicial calendar.

**Both shifts are mandatory statute in both directions**, so Friday 3 July 2026 is
**derived** rather than transcribed. The Sunday limb is dormant in 2026.

### The federal-override clause — unique, live, and dormant this year

> If the date designated by the state for observance of any legal holiday
> pursuant to this section, **except Veterans Day**, is different from the date of
> observance of such holiday pursuant to a **federal holiday schedule, the federal
> holiday schedule shall be observed.**

**No other seeded jurisdiction subordinates its own dates to the federal
calendar.** Every 2026 date was checked against the federal schedule and none
diverges, so the clause changes nothing this year. It is live law in a year where
they split, it is not modelled, and Veterans Day is expressly carved out of it and
therefore always takes the state date.

### What is not modelled, both EARLY

- *"days on which a **specifically designated court** is closed by order of the
  Chief Justice of the Supreme Court"* — per-court rather than statewide, the only
  place Nebraska resembles Wisconsin.
- *"all days declared by law or **proclamation of the Governor** to be holidays."*

**Note "may be closed", not "must".** The statute then designates these
*"nonjudicial days"*, and the rollover keys on that legal designation rather than
on whether a particular courthouse opened — the same reasoning that let Kansas use
its published list and stopped Wisconsin using its.

**2027 is refused rather than derived**, even though the statutory rules would
generate it mechanically — which is exactly why. Generating would hide the two
open limbs and the federal-override clause behind a confident answer.

---

## 5. All three discovery rules are `later_of`, and they say so themselves

| Rule | Wording | Shape |
|---|---|---|
| 6-333(b)(2) | a defending party **may** serve within 45 days after the summons or 30 after the interrogatories, **whichever is longer** | later_of |
| 6-334(b)(2)(A) | a defending party **must** respond within 45 days after the summons or 30 after the request, **whichever is longer** | later_of |
| 6-336(a)(4) | *A matter is admitted unless* … (A) within 30 days … (B) if a defending party, within 45 days after the summons or 30 after the request, **whichever is longer** | later_of, self-executing |

**The rule does its own resolving.** "Whichever is longer" is in the text, so no
reading was needed — and that matters because 6-333 also says **"may"**, which in
Kansas and in Mississippi's Rules 33 and 34 marks an *election* and produces a
plain 30-day row. Here "may" and "whichever is longer" sit in one sentence and the
comparative governs.

**Three rules, three different wordings, one destination** — and the neighbour
seeded hours earlier has **none of it**: `"45 days"` does not appear anywhere in
the Idaho Rules of Civil Procedure. Both are asserted live on the same facts:
Nebraska returns 2026-11-04, Idaho 2026-11-02.

---

## 6. What was seeded, and what was deliberately left out

**Ten rules, every one forward.** Answer to the summons and complaint (30); answer
to a counterclaim **or** cross-claim (30, one rule for both); reply after an order
to reply (21); responsive pleading after a Rule 12 motion is denied (21, from
**notice**); responsive pleading after a more definite statement (21, from
**service**); interrogatory answers, production response and admissions (all
later-of 30/45); motion for a new trial (10 from entry); motion to alter or amend
(10 from entry).

**The two post-judgment motions are frozen by the SOURCE of the deadline, not by a
list.** § 6-1106(b)(2): *"If the time to act is specified by **statute**, the court
must not extend the time except to the extent and under the conditions stated by
statute."* Most states freeze post-judgment motions by naming them; Nebraska
freezes these because they are statutory. Note also that § 6-1106(b)(2) is
unusually generous elsewhere — the **parties** may extend most times by written
stipulation.

**Deliberately not seeded, each for a stated reason:**

- **Every backward row** — see §2.
- **"or completion of service by publication"** in § 6-1112(a)(1)(A) — a different
  event with its own completion date, not a variant of personal service. A caller
  with a published summons needs a row that does not yet exist rather than this
  one.
- **§ 6-334(b)(2)(B)'s production itself** — a date set by the parties' own papers.
- **The deeming sentence** in both post-judgment statutes — a motion filed after
  the verdict but before entry is treated as filed on the day of entry. It makes an
  early motion valid; it does not change the deadline, so no row is needed.
- **The appeal clock**, Neb. Rev. Stat. § 25-1912.

---

## 7. Verdict

**PASS, and seeded.** The rules and the statutes are free, official and reachable
by plain request, with a bulk export endpoint that returns a whole article at
once. The computation rule names its own statute, and that statute carries its own
holiday list in the same sentence as its rollover test — the strongest source
position of any state gated so far.

**Two things to carry forward.** A rules committee has now stated, in a published
comment, that the after-expiry / period-lengthening distinction this engine
encodes was genuinely ambiguous and needed an amendment to settle — which is
external confirmation that the distinction is real and worth the care spent on it
in every other jurisdiction. And the prior rule versions are live, complete and
correctly labelled: the safest-looking kind of stale source, because nothing about
fetching it fails.

### Live verification, 30/30 on `LAW-PINNACLE-2026`

**Pass 1** — all 10 rows return a real date.

**Pass 2** — the arithmetic:

- **The court's own worked example reproduces exactly**: 2026-03-23 unmailed,
  **2026-03-26 mailed**, matching Comment [3]'s "extends the period to Thursday".
- **Arbor Day rolls** (→ 2026-04-27). **Juneteenth rolls in Nebraska**
  (→ 2026-06-22) and **does not roll in Idaho** (→ 2026-06-19) on the same
  platform. **The day after Thanksgiving rolls in Nebraska** (→ 2026-11-30) and
  **does not in Idaho** (→ 2026-11-27). Three cross-jurisdiction pairs, live.
- **The shifted Friday 3 July rolls to Monday the 6th**, and a 30-day period
  counts Thanksgiving and the day after as ordinary intermediate days.
- **Mail only**: a mailed counterclaim pleading takes three days (2026-12-21), a
  mailed summons takes none (2026-12-16), and **email, a designated delivery
  service and e-filing all return 2026-12-16** — nothing.
- **The notice/service split**: 2026-12-07 vs 2026-12-10 on rows one subparagraph
  apart.
- **The later-of against Idaho on identical facts**: Nebraska 2026-11-04, Idaho
  2026-11-02.
- **A pre-2025 trigger refuses** `NO_RULE_IN_FORCE` rather than answering with the
  superseded 20-day number. 2027 refuses `NOT_PROVISIONED`.
- The coverage disclosure comes back with `complete:false`, `direction:"early"`,
  naming Arbor Day and the federal-override clause.
