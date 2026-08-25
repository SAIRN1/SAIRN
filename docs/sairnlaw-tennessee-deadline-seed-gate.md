# Tennessee — deadline-seed source-availability gate

**Run 2026-08-25. Verdict: FAILED — Tennessee is not seedable, and this is a
decision made, not a decision pending.**

> **Verdict upgraded from "gated out, awaiting a decision" to FAILED on
> 2026-08-25**, on Michael's direction after he found the Administrative Office
> of the Courts' own Code page. See §2A for that page's verbatim text and for a
> correction to how it was first characterised — the AOC's warning is real and
> decisive, but it does not say what it was first reported to say, and the
> distinction changes which reason does the work.

Tennessee (~7.1M) is the largest unseeded state. Its **rules pass the gate
outright**. It fails on the **holiday statute its own rule expressly requires** —
an ACCESS failure rather than a definitional one, which is why so much usable
work survives it (§5) even though the state itself is refused.

---

## 1. The rules — PASS, cleanly

The complete Tennessee Rules of Civil Procedure are published free, in full, by
the **Administrative Office of the Courts** at `tncourts.gov`. No Westlaw or
Lexis redirect anywhere in the rules path. Each rule prints its own amendment
history with effective dates, e.g. Rule 6.01: *"[As amended by order entered
January 21, 1988, effective August 1, 1988; ... and by order entered December
21, 2010, effective July 1, 2011.]"* — so `effective_from` would be real per
row, as in Virginia and Massachusetts.

Read verbatim during this gate: **5.02, 6.01, 6.05, 12.01, 33.01, 34.02, 36.01**,
plus the Advisory Commission Comments to Rule 6.

**Access:** `tncourts.gov` serves a JavaScript anti-bot challenge to plain
`curl` (the response body is an obfuscated JS computation, not the page). A real
browser gets HTTP 200 and full text. Same *condition* as Massachusetts and North
Carolina, different mechanism, already-solved either way.

## 2. The blocker — Tenn. Code Ann. § 15-1-101 is not reachable in a current, official, free form

Rule 6.01 does not define "legal holiday" itself. It **expressly delegates**:

> The last day of the period so computed shall be included unless it is a
> Saturday, a Sunday, or **a legal holiday as defined in Tenn. Code Ann.
> § 15-1-101** …

That express cross-reference is normally the *good* shape (it is what makes
Washington and Massachusetts clean). Here it makes the statute load-bearing —
no statute, no calendar, and no calendar means every Tennessee row refuses.

What was tried, and what happened:

| Route | Result |
|---|---|
| `lexisnexis.com/hottopics/tncode` — **the link the Tennessee General Assembly's own site gives for the Code** | **HTTP 403** (CloudFront) to `curl` *and* to a real browser |
| `advance.lexis.com` container deep link | HTTP 200 but renders **"Page Unavailable"** |
| `capitol.tn.gov` — searched for an in-house Code | No Code link found; the site carries bills, chapters and journals, not the codified text |
| Open-data republication (`unicourt.github.io` / `archive.org` `gov.tn.tca`) | **HTTP 200, full text — but the newest release is `release76.2021.05.21`** |
| Justia / FindLaw | Reachable, but **unofficial secondary republications** |

### The open snapshot is provably stale on exactly the list we need

The 2021 snapshot's § 15-1-101 lists: January 1; third Monday in January (MLK);
third Monday in February (Washington Day); last Monday in May (Memorial);
July 4; first Monday in September (Labor Day); second Monday in October
(Columbus Day); November 11 (Veterans'); fourth Thursday in November
(Thanksgiving); December 25; and Good Friday.

**It does not contain Juneteenth.** § 15-1-101 was amended to add "June 19,
known as Juneteenth" by **2023 Tenn. Acts ch. 337, effective 2023-05-05**
(SB269/SB1829 lineage). So the only free full text reachable is demonstrably
two years and at least one substantive amendment behind — on the holiday list
itself.

Reconstructing the current section from the 2021 base plus every public chapter
since is exactly the **Arizona** method, and it was failed there for a reason
that applies unchanged: *a reconstruction cannot prove its own completeness,
and a missed amendment yields wrong dates with no refusal.*

## 2A. The AOC's own Code page — verbatim, and a correction to how it was first read

Found by Michael 2026-08-25 and then read directly from
`https://www.tncourts.gov/Tennessee%20Code` through a real browser. The page is
titled **"Tennessee Code - Lexis Law Link"** and says, in full:

> At the bottom of this page is a link to the LEXIS Law Publishing Web Site.
> **The site is not operated by, nor is it under the control of, The Tennessee
> Administrative Office of the Courts.**
>
> This link is provided solely as a service, and any inquires regarding the
> usage of, or problems with, the LEXIS Law Publishing query tools should be
> directed by LEXIS Law Publishing Customer Service.
>
> **Please note that Lexis has changed its free version of the Tennessee Code.
> Before you can view the content, you must click a button that says you agree
> to its terms and conditions.**

**CORRECTION, STATED PLAINLY BECAUSE THE DIFFERENCE MATTERS.** This finding was
first relayed as the state courts "flagging the free edition as unreliable" —
i.e. a warning about the *integrity of the content*. **The page does not say
that.** It says two narrower things: the AOC does not operate or control the
site, and Lexis has changed its free edition so that content is now behind a
**click-through terms-and-conditions acceptance**. Nothing on the page
characterises the text as inaccurate or untrustworthy.

The verdict is unchanged, and arguably rests on firmer ground once the page is
read literally rather than as a reliability warning:

1. **There is now an explicit terms-acceptance gate.** Viewing the Code requires
   affirmatively clicking a button agreeing to LexisNexis's terms. **An agent
   cannot click that on anyone's behalf.** This project has already declined to
   route around exactly this kind of gate — the BAILII/AustLII reasoning, and
   CanLII's suit against Caseway AI. That is a bright line and it is reached
   before any question of content quality arises.
2. **The state's own courts disclaim the source.** "not operated by, nor …
   under the control of" the AOC is the AOC declining to vouch for the only free
   access point it can offer for a statute its own Rule 6.01 makes load-bearing.
3. The stale-snapshot and dangerous-direction findings below stand on their own
   and are independent of both.

**How this differs from Arizona, precisely.** Arizona's problem was
*completeness*: a free, complete, official base text that provably lagged, with
the maintained version behind a paywall — a staleness question, and the
free-government-edition terms were later cleared. Tennessee's problem is
*access permission at the front door*: the current text is not merely stale but
sits behind a terms gate this project will not click through, and the state
courts expressly disclaim the host. That is closer to **Kentucky** — refused on
source availability — than to Arizona, though the mechanism differs: Kentucky
had no free base text at all, Tennessee has one it may not pass the gate to.

### And the error direction is NOT uniformly safe, which rules out shipping it with a disclosure

- **Missing Juneteenth** → a deadline landing on 19 June would not roll →
  reports **EARLY**. Safe.
- **Election days** → § 15-1-101 makes "all days set apart by law for holding
  county, state, or national elections" legal holidays *on its face*. But its
  own Compiler's Notes record that **Acts 1984, ch. 979 §§ 2–3 empowered the
  governor to DELETE legal holidays**, and that *"[t]he governor chose the
  election day holiday for the August and November elections."* If those are
  deleted and this engine encodes them, Tennessee deadlines roll **LATE** —
  the direction that misses a filing. Resolving it needs the current text
  *and* the governor's designations.
- **"All days appointed by the governor or by the president … as days of
  fasting or thanksgiving"** → ad hoc, never knowable in advance → EARLY,
  disclosable (same shape as Va. Code § 1-210(F)).

Because one of the three runs LATE, this cannot be shipped as a Virginia- or
Massachusetts-style disclosure. That is the whole verdict.

## 3. How this differs from Arizona and from Kentucky

| | Kentucky | Arizona | **Tennessee** |
|---|---|---|---|
| Rules free & complete? | **No** — one link, to Westlaw | Base yes (2017 restyled), maintained text no | **Yes, free, official, maintained** |
| Holiday basis | Undefined; KRS 2.110 fails **LATE** | Rule says "legal holiday", names no statute | **Expressly defined** by § 15-1-101 |
| What blocks it | Two blockers, one fatal by itself | Unprovable reconstruction | **One blocker: current statute unreachable** |

Tennessee is the *narrowest* block of the three. The law is clear and the rules
are excellent; only a current authoritative copy of one statute is missing.

## 4. Why no decision is pending — and what would have to change

An earlier draft of this document left two questions open for Michael: whether
the LexisNexis free Tennessee Code edition was acceptable on the same reasoning
that cleared Westlaw's government edition for Arizona, and whether the URL was
reachable at all. **Both are now answered, and the answer is no on the first,
which is dispositive.**

- **The terms question is not a judgement call about publisher policy — there
  is a literal click-through gate.** The AOC's page states that content cannot
  be viewed until you "click a button that says you agree to its terms and
  conditions." Clearing Westlaw's *free government edition* for Arizona was a
  decision about reading a page that simply loads. This is a decision about
  affirmatively accepting a contract on a user's behalf, which is not the same
  act and is not covered by that earlier decision.
- **The reachability question is moot.** `lexisnexis.com/hottopics/tncode`
  returns HTTP 403 (CloudFront) to `curl` and to a real browser alike, and
  `advance.lexis.com` renders "Page Unavailable". Even setting the terms gate
  aside, nothing loads.

**What would change the verdict** (none of which is work this project can do
unilaterally):

1. Tennessee publishing the Code in a free, official form that is not behind a
   terms acceptance — as Virginia, Massachusetts, Washington and North Carolina
   all do for their statutes.
2. A human obtaining § 15-1-101 through the gate and supplying the verbatim
   current text, together with the governor's standing designations under Acts
   1984 ch. 979 for the election-day holidays.
3. A decision, made explicitly and by a person, that accepting those terms is
   acceptable for this use.

Route 2 is the realistic one and it is small: **a single statute section plus
one designation list**. Everything else Tennessee needs is already read and
recorded in §5 below. Tennessee is refused today, not abandoned.

## 5. Banked verbatim — reusable whether or not Tennessee is ever seeded

All read directly from `tncourts.gov`, 2026-08-25.

- **THE SHORT-PERIOD EXCLUSION IS ELEVEN DAYS, NOT SEVEN.** Rule 6.01: *"When
  the period of time prescribed or allowed is less than eleven (11) days,
  intermediate Saturdays, Sundays, and legal holidays shall be excluded."*
  Every other state seeded that has one uses 7 (NJ, NC, WA, MA, WV appellate);
  Arizona is the only other 11. **Encoding 7 by analogy would be wrong on every
  Tennessee period of 7–10 days.** The Advisory Commission Comment gives the
  reasoning: *"When the time allowed is so short, the party limited by the time
  should not be further handicapped…"*

- **THE ADVISORY COMMISSION COMMENT [2011] ANSWERS THE BUNDLED HOLIDAY QUESTION
  FOR TENNESSEE, AND IS THE CLEANEST STATEMENT OF IT FOUND IN ANY STATE SO FAR:**
  > "Rule 6.01 is amended to define 'legal holiday' by reference to statute,
  > Tenn. Code Ann. § 15-1-101. The status of a day as a legal holiday is
  > statutory; thus, for the purpose of filing papers in court, **it does not
  > depend on whether the clerk's office is open for business.** For example,
  > state offices might be open on Columbus Day, pursuant to the governor's
  > authority under Tenn. Code Ann. § 4-4-105(a)(3) to substitute the day after
  > Thanksgiving for the Columbus Day holiday; in such circumstances, however,
  > Columbus Day is still a 'legal holiday' for purposes of computing time
  > periods under the rule."

  This is the **exact inverse of North Carolina**, whose Rule 6(a) keys on
  whether "the courthouse is closed for transactions". It also means the
  **Tennessee state-employee holiday schedule (§ 4-4-105) is the WRONG source**
  and the comment says so in terms — a trap this project has already walked into
  once, in reverse, in North Carolina.

- **RULE 6.05 READS MAIL-ONLY AND THAT READING IS WRONG.** Rule 6.05 itself:
  *"…served upon such party by mail three (3) days shall be added to the
  prescribed period."* But **Rule 5.02(2)(c)**: *"A document transmitted by
  email shall be treated as a document that was mailed for purposes of
  computation of time under Rule 6."* And **Rule 5.02(3)(e)**: *"A document
  that is E-served shall be treated as a document that was mailed for purposes
  of computation of time under Rule 6."* So email and e-service **do** get the
  three days — by a deeming provision in the SERVICE rule, not the time rule.
  Reading Rule 6.05 alone produces a wrong, EARLY answer. **Facsimile has no
  such deeming provision** (Rule 5.02(1) permits fax service but never deems it
  mail), so fax gets nothing. Tennessee reaches Massachusetts' outcome by a
  completely different route — worth a standing habit: *check the service rule
  for deeming provisions before concluding a time rule is mail-only.*

- **Rule 6.05 sequence:** "added to the prescribed period" → period-lengthening
  (`add_to_period_then_roll`), like NJ, NC, WA, NY, VA and MA; not the federal
  after-expiry order.

- **Rule 12.01, verbatim:** answer **30 days** after service of the summons and
  complaint; answer to a cross-claim **30 days**; reply to a counterclaim
  **30 days** after service of the answer, *or* 30 days after service of the
  order if a reply is ordered. A Rule 12 motion alters these: **15 days** after
  notice of the court's action if denied or postponed, **15 days** after service
  of the more definite statement if granted. (15 ≥ 11, so no exclusion applies
  to those limbs — the 11-day threshold only bites on shorter periods.)

- **Rules 33.01, 34.02 and 36.01 are 30 days with a 45-day defendant floor —
  ALL THREE.** *"within 30 days after the service of the interrogatories, except
  that a defendant may serve answers or objections within 45 days after service
  of the summons and complaint upon that defendant"*, and the same construction
  in 34.02 and 36.01. So Tennessee needs a `later_of` row on **every** discovery
  device — unlike Massachusetts, which has one on two of three (R. 33 grants no
  floor there). 36.01 is self-executing: *"The matter is admitted unless…"*

- **§ 15-1-101's weekend shift runs BOTH WAYS** — *"when any one (1) of these
  days falls on Sunday, then the following Monday shall be substituted; and when
  any of these days falls on Saturday, then the preceding Friday shall be
  substituted"* — like Virginia and West Virginia, and unlike Massachusetts'
  Sunday-only shift. (From the 2021 snapshot; the shift sentence is long-standing
  and not what the 2023 amendment touched, but it still needs confirming against
  a current text before use.)

- **Good Friday is a Tennessee legal holiday**, as in New Jersey.

- **Rule 6.04 fixes five days' notice for motions**, per the Advisory Commission
  Comment — a period **under 11 days**, so it would be the row that actually
  exercises the 11-day exclusion. Worth seeding first if Tennessee ever clears,
  because it is the one that would catch a mis-set threshold.

## 6. Verdict

**FAILED. Not seedable, and not pending a decision.**

The rules pass the gate — free, complete, official, maintained, with real
per-rule currency. Everything needed to seed Tennessee is read and banked in §5.

It fails on the statute Rule 6.01 makes load-bearing. The only free access point
the state's own courts can offer is a host they expressly disclaim control over,
whose content now sits behind a **click-through terms acceptance an agent must
not click**, and which returns 403 in any case. The only free full text actually
reachable is a 2021 snapshot that provably predates a 2023 amendment to the
holiday list. And one of the three gaps in that stale text — election-day
holidays, which § 15-1-101 grants on its face while its own Compiler's Notes
record the governor deleting them — runs **LATE**, which forecloses shipping it
behind a Virginia-style disclosure.

**Refused for a related but distinct reason from Kentucky.** Kentucky has no
permitted primary source *and* a holiday basis that fails late. Tennessee has a
permitted, excellent primary source for its *rules*, and a front-door access
barrier on the one *statute* those rules require. Both end in refusal; the
mechanisms are different and should not be collapsed when either is revisited.

Banked, not abandoned — see §5, and the standing-habit finding about deeming
provisions in service rules, which is the most reusable thing this gate produced.
