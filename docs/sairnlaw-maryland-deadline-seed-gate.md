# Maryland — deadline-seed source-availability gate

**Run 2026-08-26. Verdict: PASS, with named build work and TWO DECISIONS that
are not mine to make.**

Maryland (~6.2M) is the next unseeded state after Missouri. Source availability
is a clean pass. It fails nothing — but it carries a wrong-source trap that
runs LATE, two mechanics the engine lacks, a holiday list that **cannot be
derived**, and one genuine ambiguity that must ship disclosed rather than
guessed.

---

## 1. Sources — PASS, and `curl` works

| What | URL | Method |
|---|---|---|
| Maryland Rules, full text | `govt.westlaw.com/mdc/Browse/Index` → Maryland Rules | **plain curl 200** |
| Rule 1-203 document | `govt.westlaw.com/mdc/Document/N417C58309CEA11DB9BCF9DAC28345A2A?viewType=FullText` | curl 200, full text |
| Maryland Code (statutes) | `mgaleg.maryland.gov/mgawebsite/Laws/StatuteText?article=gsp&section=9-201` | plain urllib 200 |
| **Court holiday calendar** | `mdcourts.gov/administration/holidays` (+ `/holidaysYYYY` archives) | curl 200 |
| Rules Orders (authoritative) | `mdcourts.gov/rules/ruleschanges` — 76 free PDFs | curl 200 |

**On the Westlaw host, and why this is NOT Tennessee.** The full text sits on
`govt.westlaw.com/mdc` — but as the government slice hosted for the
**Judiciary's own Thurgood Marshall State Law Library** (named in the page
footer). Verified: **no sign-in form, no click-through, no terms acceptance, no
paywall on document pages.** Tennessee failed because its state courts pointed
at a Lexis edition that now requires clicking "I agree" before content renders.
Maryland's loads on a plain `curl`. Different fact, different verdict.

`dsd.maryland.gov/Pages/Maryland-Rules.aspx` is a **404** — the Division of
State Documents does not publish the Rules. Dead lead, recorded so nobody
re-chases it.

`WebFetch` fails on `mdcourts.gov` ("unable to verify domain is safe") while
`curl` and Playwright both succeed — a **fourth** distinct access quirk after
mass.gov, tncourts.gov and courts.mo.gov.

## 2. Currency — real per rule, with one disclosed lag

Every rule carries its own credits block. Verbatim, Rule 1-203:

> `[Adopted April 6, 1984, eff. July 1, 1984. Amended June 28, 1988, eff. July 1,
> 1988; July 16, 1992; Dec. 10, 1996, eff. Jan. 1, 1997; April 8, 1997, eff.
> July 1, 1997; May 9, 2000, eff. July 1, 2000; Nov. 12, 2003, eff. Jan. 1,
> 2004; March 2, 2015, eff. July 1, 2015.]`
> `Current with amendments received through June 1, 2026.`

Proposed `effective_from` per rule: **1-203 → 2015-07-01**, 1-202 → 2025-01-01,
1-321 → 2025-01-01, 20-205 → 2026-07-01, 2-321 → 2016-01-01, 2-421 and
2-424 → 2008-01-01, 2-422 → 2017-04-01.

**The lag, and how it was closed rather than assumed away.** The free slice is
current through amendments *received* 1 June 2026, and Rule 2-422 shows
`Effective: [See Text Amendments] to September 30, 2026` with the successor text
not exposed. Traced to the **228th Rules Order dated 4 June 2026**, amending
2-422 effective **1 October 2026**; the order PDF was pulled and read, and the
amendment only restructures 2-422(c)'s response format. **The 30-day/15-day
deadline language is untouched — deadline-neutral.**

The durable lesson: **for currency verification the Rules Orders PDFs move
first, not the Westlaw slice.** They are free and independent of it, which
means Maryland's currency can be checked without relying on the publisher at
all.

## 3. THE WRONG-SOURCE TRAP — it fails LATE

The intuitive path for a Maryland time rule is **Gen. Provisions § 1-302**
(computation) + **§ 1-111** ("legal holiday"). **Both are wrong for court
deadlines, and wrong in both directions at once:**

- **GP § 1-302(b)(1)** rolls the last day only if `it is a Sunday or legal
  holiday` — **no Saturday roll**. Using it reports **EARLY**.
- **GP § 1-111** adds **Good Friday, Lincoln's Birthday (12 Feb), Maryland Day
  (25 Mar) and Defenders' Day (12 Sep)** — four days that are **not** court
  holidays. Using it reports **LATE**.
- GP § 1-111(b) also shifts **Sunday-only**, contradicting the both-directions
  shift the courts actually apply.

Rule 1-203's own committee note settles it: *"This section supersedes Code,
General Provisions Article, § 1-302 to the extent of any inconsistency."*

**The correct chain is Rule 1-203 → Rule 1-202(l) → State Personnel & Pensions
§ 9-201.** Rule 1-202(l) verbatim: *"'Holiday' means an 'employee holiday' set
forth in Code, State Personnel and Pensions Article, § 9-201."*

This is the same class of hazard as Kentucky's KRS 2.110 and Missouri's RSMo
9.010 question, and it is the **third** time the obvious statute has been the
wrong one. It belongs in the bundled lawyer's question as its own category:
*a state with TWO plausible holiday statutes, where the general one is wrong.*

## 4. A FOURTH electronic-service pattern

Maryland matches none of the three now implemented.

**Rule 20-205 committee note, verbatim:**

> **Rule 1-203 (c), which adds three days to certain prescribed periods after
> service by mail, does not apply when service is made by the MDEC system.**

**Rule 20-202, in full:**

> The MDEC system shall record the date and time an electronically filed
> submission is received by the MDEC system. Subject to Rules 20-201(i) and
> 20-203, the date recorded shall be the effective date of filing and shall
> serve as the docket date of the submission filed.

| State | Electronic service |
|---|---|
| Massachusetts | +3 days, granted in the time rule itself |
| Tennessee | time rule says mail-only, but the service rule **deems** it mail → +3 |
| Missouri | +0 days, and the **trigger date moves** on a 5 p.m./weekend cutoff |
| **Maryland** | **+0 days, no cutoff, trigger is the MDEC-recorded date** |

So Maryland needs **neither** mechanism for e-service — the simplest of the
four, but only knowable by reading Title 20. The 3-day mail extension survives
solely for the 20-205(d)(2) residue: non-registered users, registered users who
have not entered an appearance, and tangible paper items.

**MDEC is statewide** as of 2024-05-06, so there is no county variance — checked
because Rule 20-102 is written county-by-county. Self-represented litigants are
still not required to e-file, so the mail branch stays live for them.

**Reported as unresolved, not inferred:** Rule 20-202's cross-reference to
"Rule 20-201(i)" is **stale** — current (i) is "Electronic File Names", not a
timing provision. So a cutoff hour cannot be positively ruled out; it may have
lived in a re-lettered subsection. The State Court Administrator's MDEC policies
and procedures, which Rule 20-201(c) makes binding on filers, were **not**
checked and could carry an operational cutoff invisible in the Rules.

## 5. The holiday list CANNOT be derived — it must be ingested per year

**SPP § 9-201** lists fourteen items, including `(11) the Friday after
Thanksgiving Day, for American Indian Heritage Day`, `(13) each statewide
general election day in this State`, and `(14) each other day that the
President of the United States or the Governor designates for general cessation
of business`.

Three independent reasons a generator cannot produce this list:

1. **§ 9-201(14) is arbitrary.** Real example from the Judiciary's own archive:
   `Sunday, December 25, 2022 (Observed Friday, December 23 and Monday,
   December 26, 2022)` — **two observed days for one holiday.**
2. **§ 9-201(13) fires only in even years** and the date must be looked up.
3. **MLK, Memorial and Columbus each carry** "unless the United States Congress
   designates another day", a live substitution.

So Maryland joins **New Jersey** and **North Carolina** as ingest-not-derive,
and the target is `mdcourts.gov/administration/holidays` with `/holidaysYYYY`
archives — plain HTML that `curl` reads.

**The weekend shift is BOTH WAYS** — the first such state in three. SPP § 9-204:
Saturday → the immediately preceding Friday; Sunday → the immediately following
Monday. **Do not carry Massachusetts' or Missouri's Sunday-only shift here.**

**A doctrinal gap, flagged not papered over:** Rule 1-202(l) cites only § 9-201
(the list), **not** § 9-204 (the shift), and § 9-202 confines that subtitle to
*"all employees of all units in the Executive Branch"* — which excludes the
Judiciary. The shift is therefore not, on its face, incorporated into the Rules'
definition. It was resolved against the **Judiciary's own published practice**
(six verbatim archived calendar entries showing both directions applied), which
is what the engine should follow — but no rule or case closing the gap was
found. Since the list is ingested rather than derived, this is mostly moot in
practice; it matters if anyone ever tries to compute the calendar.

**No county-scoped holidays** — one statewide list, unlike Massachusetts'
Suffolk County. What *is* locally variable is court **closures** (weather,
emergencies), published per-court at `mdcourts.gov/administration/closingsdelays`.

## 6. Build items

1. **A ≤7-day intermediate-day exclusion, expressed as "seven days or less".**
   Verbatim: *"if the period of time allowed is seven days or less, intermediate
   Saturdays, Sundays, and holidays are not counted."* The engine's
   `short_period_exclusion_days` is compared with a **strict less-than**, so
   Maryland's value is **8, not 7** — exactly the trap the engine's own comment
   already documents for Texas ("five days or less" → 6). Needs a boundary test
   at exactly 7 days.
2. **Backward counting is NOT the mirror of forward.** Rule 1-203(b) counts
   *all* days prior *"including intervening Saturdays, Sundays, and holidays"* —
   the exclusion in (a) deliberately does **not** apply — and the latest day
   rolls **backward** to *"the first preceding day which is not a Saturday,
   Sunday, or holiday."* An engine reusing forward logic for backward periods is
   wrong on every short backward Maryland period. Maryland would be the first
   jurisdiction here needing a per-direction exclusion flag.
3. **Rule 1-203(a)(2) is a second, non-holiday roll trigger** — *"the act to be
   done is the filing of a paper in court and the office of the clerk of that
   court on the last day of the period is not open, or is closed for a part of
   the day."* Independent of any holiday list; captures weather and partial-day
   closures. Not knowable in advance → **coverage disclosure, EARLY direction**,
   same treatment as Virginia's § 1-210(F).

## 7. DECISION ONE — the ≤7-day / mail-extension interaction

**Ship as a disclosed ambiguity. Do not guess.**

Rule 1-203(c) adds three days **"to the prescribed period"**. So a mailed 7-day
period arguably becomes a 10-day period — which is *"more than seven days"* —
which would **flip intermediate Saturdays, Sundays and holidays from excluded to
counted**, changing the date.

Two live readings:

- **(A)** "the period of time allowed" in (a) means the period *after* the
  mail extension → exclusion is lost → **earlier** date.
- **(B)** "the period of time allowed" means the underlying rule's period (7) →
  exclusion survives, and the 3 days are appended → **later** date.

**No committee note, no cross reference, and no controlling authority was
found.** The readings diverge on any mailed period of **4–7 days**.

This is not a direction-of-error question that can be resolved by picking the
safe side, because the two readings differ by which is safe depending on the
period. It must be **disclosed on every affected row** and, if a mailed short
period is ever seeded, the engine should **refuse** rather than pick — the same
call already made for West Virginia's contested Rule 6(e), which returns
`refused_contested_standard` rather than resolving a rule against itself.

## 8. DECISION TWO — a discovery floor that CHAINS OFF A COMPUTED DATE

**This is an engine gap, not a Maryland quirk, and it has the highest stakes of
anything in this gate.**

All three Maryland discovery rules use an identical two-limb floor. Rule 2-424(b)
verbatim:

> Each matter of which an admission is requested shall be **deemed admitted**
> unless, **within 30 days after service of the request or within 15 days after
> the date on which that party's initial pleading or motion is required,
> whichever is later**, the party to whom the request is directed serves a
> response…

2-421(b) (interrogatories) and 2-422(c) (production) carry the same construction.

**Why this is different from every later-of row already seeded.** Ohio, Georgia,
New Jersey, North Carolina, Washington, Virginia, Massachusetts and Missouri all
have a defendant floor measured from a **date the caller supplies** — service of
the complaint, an appearance, service of process. Maryland's second limb runs
from *"the date on which that party's initial pleading or motion is **required**"*
— **which is itself the output of another rule.**

And it is not a static offset. Rule 2-321 makes the answer date **30, 60 or 90
days** depending on how and where the defendant was served, and **Rule 2-321(c)**
extends it further, *"without special order to 15 days after entry of the court's
order"* on a Rule 2-322 preliminary motion or a remand.

So the floor for a Maryland-resident defendant is 30 + 15 = **45 days**; for a
60-day defendant **75**; for a 90-day defendant **105**; and after a Rule 2-322
motion it is 15 days after a ruling the engine cannot see.

**`resolve_periods` cannot express this.** Its limbs each take an *event* and a
*count*; neither limb can be "the result of computing rule X". Nothing seeded
today handles a trigger that depends on another rule's outcome.

**The stakes make this the wrong place to improvise.** Rule 2-424 is
self-executing — miss it and facts are **deemed admitted**. A floor guessed
short computes **EARLY on the one rule where an early date silently forfeits the
case on the merits.** That is the most dangerous single shape encountered in any
gate so far, and it is why this gets its own index row rather than a line in the
Maryland write-up.

**Three options, none chosen here:**

1. **Caller supplies the computed date.** Name the limb event
   `date_initial_pleading_is_required` and make the caller compute it from Rule
   2-321 first. Honest and buildable today; the risk is that a caller who
   supplies the wrong branch (30 vs 60 vs 90) produces a floor that is EARLY.
2. **Build rule chaining** — let a limb name another rule and have the engine
   compute it. The correct answer, and much the largest.
3. **Refuse the defendant limb entirely** and seed only the plain 30-day row
   with a disclosure that a defendant's true deadline may be later. Safe (EARLY
   direction), least useful.

## 9. What was NOT determined

- Whether SPP § 9-204's shift is legally incorporated into Rule 1-202(l)
  (practice established; doctrine not closed).
- Whether any MDEC cutoff hour exists — Rules 20-201/202/203 and 1-322 checked,
  none found, but Rule 20-202's cross-reference is stale and the binding State
  Court Administrator policies were not read.
- The other 19 rules amended by the 228th Rules Order were not audited for
  deadline impact; only 2-422 was.
- **District Court (Title 3) equivalents** — Rules 3-307, 3-421 etc. were not
  read. Title 3 has parallel but not necessarily identical periods, and the
  228th Order amends 3-325 and 3-421. A separate pass if District Court is ever
  seeded.
- Whether individual circuit courts publish local holiday closures beyond the
  statewide list.

## 10. Verdict

**PASS.** Sources are free, official, complete, permitted, `curl`-reachable, and
carry real per-rule currency plus an independent currency channel (the Rules
Orders PDFs) that does not depend on the publisher.

**Not seedable today.** It needs the "seven days or less" threshold expressed as
8, a backward mode with the exclusion off, and a decision on the chained
discovery floor. Two of those are small; the third is DECISION TWO above and is
the reason this state should not be seeded piecemeal — seeding the plain
discovery rows while leaving the defendant floor unmodelled is defensible only
if the disclosure is explicit that a defendant's real deadline is later.
