# Arkansas — deadline-seed source-availability gate

**AMENDED 2026-08-29: SEEDED -- 13 rules, calendar 2026 ONLY. Read Sec. 1c,
which is the section that matters now. The original verdict below is kept
unedited, because the reasoning that produced the block is what made the
eventual route findable -- Sec. 1b named this channel as the third of three
things that would clear it.**

**Run 2026-08-27. Verdict: RULES PASS with a real currency date and no
structural blocker — but the HOLIDAY STATUTE could not be reached on any
primary source, so the calendar is blocked and the state is not seedable today.
That is a source gap, not a structural one, and it is the only thing in the way.
Arkansas also settles, in its own rule text, the Rule 4 / Rule 5 question that
had to be inferred to fix two federal rows the same day.**

Arkansas (~3.1M), the largest state with neither a seed nor a gate document
after Utah, Iowa and Nevada. Rules of court are the **Arkansas Rules of Civil
Procedure**, adopted by the Supreme Court of Arkansas.

---

## 1. Sources — the rules PASS, the statute does NOT

### The rules: reachable, official, and they state their own currency

```
opinions.arcourts.gov/ark/cr/en/16712/1/document.do   200, 1,311,020 B, 195pp PDF
```

Real text, not a scan. **Its first line is the currency statement:**

> Rules of Civil Procedure **(current through June 4, 2026)**

and the collection index prints the same date per rule set — *"Arkansas Rules of
Civil Procedure - **06/04/2026**"*, alongside Evidence 06/04/2026, Appellate
Procedure—Civil 06/04/2026, Appellate—Criminal 12/15/2025. Per-collection
currency, which only Nevada has matched.

**GETTING THERE IS NOT OBVIOUS AND IS WORTH RECORDING.** Arkansas serves its
rules from a **Lexum/Decisia portal**, and every intuitive path is a dead end:

| tried | result |
|---|---|
| `arcourts.gov/rules`, `/court-rules`, `/rules-and-administrative-orders` | **404** |
| `arkansasjudiciary.gov`, `courts.arkansas.gov` | **DNS does not resolve** |
| `opinions.arcourts.gov/ark/courtrules/en/nav.do` | 404 |
| `opinions.arcourts.gov/ark/en/nav.do` | 200, but the rule links are **JS-loaded and absent from the HTML** |

The working route is `?iframe=true`, which returns the server-rendered list:
`/ark/en/nav.do?iframe=true` → reveals `/ark/cr/en/nav_date.do` → with
`?iframe=true` → the collection listing with per-rule-set IDs and dates →
`/ark/cr/en/16712/1/document.do` is the ARCP PDF. **A browser user-agent is
required throughout.**

### The statute: NO PRIMARY SOURCE FOUND, and this is the blocker

Rule 6(a) defines "legal holiday" by pointing outward (§4), so the calendar
cannot be built without **Ark. Code Ann. § 1-5-101**. It was not obtainable:

- **`arkleg.state.ar.us` returns HTTP 200 and a 42-byte 1×1 GIF** for the
  statute's `FTPDocument` path. Not an error page, not a redirect — a
  transparent placeholder image, `content-type: image/gif`.
- `law.justia.com` serves the section (200) but is a **secondary source**, and
  it disclaims itself in terms: *"These codes may not be the most recent
  version … We make no warranties … Please check official sources."*
- Lexis `advance.lexis.com` returns a container shell, not text.

**THIS IS THE FOURTH DISTINCT SHAPE OF "200 THAT IS NOT CONTENT" IN THREE DAYS**
— after Utah's 200-with-an-error-page-body, Iowa's dated URL returning identical
bytes for every date including future ones, and njcourts.gov's anti-bot
interstitial at 200. **A 1×1 GIF is the most easily missed of the four:** a
scripted fetch checking only status and non-zero length passes it.

**The §4 analysis below is therefore built on Justia and is explicitly NOT
primary-sourced.** It is recorded so the work is not repeated, not so it can be
seeded from.

## 1a. UPDATE 2026-08-27 — two official sources found, and the block is NARROWED, NOT CLEARED

Michael supplied two leads after the first pass. Both paid off, neither is the
statute, and **Arkansas stays gated.** What changed is what is left to find.

### The GIF is a path problem, not a domain problem — confirmed

`arkleg.state.ar.us` **does** serve documents through `/Home/FTPDocument`. Acts
come back as real PDFs. It is the **ACA** that is not published there, under any
path shape tried, and **pre-2017 Acts** are not either:

| `/ACTS/<biennium>/Public/ACT1.pdf` | result |
|---|---|
| 2001R, 2005R, 2011R, 2015R | **200, 42-byte 1×1 GIF** |
| 2017R, 2019R, 2021R, 2023R, 2025R | **200, real PDF (150–235 KB)** |

So the GIF is a *"not published at this path"* placeholder with a clean cut-off
at **2017**. Separately, `/Home/ArkansasCode`, `/ACA` and the code search all
return **HTTP 500**, and the site's own **Arkansas Law** portal links to Acts,
Bills and the administrative-rules site but **NOT to the Code** — consistent
with Arkansas licensing the ACA to a commercial publisher rather than serving
it. **The Arkansas Code does not appear to be published free by the State.**

### PRIMARY SOURCE 1 — Act 561 of 2017 (arkleg, official publisher)

`/Home/FTPDocument?path=/ACTS/2017R/Public/ACT561.pdf` — 191,122 B, 4pp, real
text. **SECTION 4** amends the very subsection in question:

> SECTION 4. Arkansas Code § 1-5-101(a)(2), concerning official state holidays,
> is amended to read as follows: (2) Dr. Martin Luther King, Jr.'s Birthday
> ~~and Robert E. Lee's Birthday~~ — the third Monday in January;

(The PDF's header states *"Stricken language would be deleted from and
underlined language would be added to present law"*; the strike does not survive
text extraction, so the deleted words are marked here by hand.) **SECTION 5**
moves Robert E. Lee Day to § 1-5-106 — gubernatorial-proclamation memorial days,
**second Saturday in October** — which is **NOT an official holiday** and must
not enter a calendar.

**This confirms from primary law that (a)(2) is MLK only.** It does not give the
rest of § 1-5-101.

### PRIMARY SOURCE 2 — the Treasurer of State's holiday sheet

`media.ark.org/artreasury/holidays_2025.pdf` — 585,660 B, on the State's own
CDN. Headed **"2025 State Holidays — Legal holidays by authority of Act 304 of
2001 and Amended by Act 561 of 2017."** Those two citations match Justia's
history line exactly, and the sheet enumerates **ten** dated days: New Year's;
MLK; **George Washington's Birthday and Daisy Gatson Bates Day**; Memorial;
Independence; Labor; Veterans; Thanksgiving; **Christmas Eve, December 24**;
Christmas.

**It corroborates §4's list on every dated day, from an official state source,
and it independently confirms Christmas Eve** — the entry no other seeded state
has. It also **omits "an employee's birthday"**, which supports reading that
limb as personal leave rather than a calendar holiday.

Only `holidays_2025.pdf` exists; 2026 and 2027 both **403**.

### WHAT IS STILL MISSING, AND WHY IT STILL BLOCKS

**§ 1-5-101(b) — THE OBSERVATION SHIFT — IS STILL UNSOURCED FROM PRIMARY.**
Justia alone has *"A holiday falling on a Saturday will be observed on the
preceding Friday. A holiday falling on a Sunday will be observed on the
succeeding Monday."* The Treasury sheet cannot corroborate it: **no fixed-date
Arkansas holiday fell on a weekend in 2025** — 1 January was a Wednesday, 4 July
a Friday, 11 November a Tuesday, 24 and 25 December a Wednesday and Thursday.
The sheet never had to apply the shift, so it demonstrates nothing about it.

That is the load-bearing piece, not a detail. The shift is what makes the
Christmas Eve / Christmas pair behave, and they straddle a weekend in **2027**
(24th Friday, 25th Saturday) and **2028** (24th Sunday, 25th Monday) — inside
any calendar range that would be generated.

Also still open: **whether any act after 2017 amended § 1-5-101.** Every
biennium from 2017R is fetchable, but arkleg's act search is JS-driven and
returns nothing in static HTML, so the amendment history could not be swept.
Justia's history line stops at 2017, and Justia is the source being checked.

### Verdict on the update

**Two official Arkansas sources now corroborate the holiday LIST, and one
confirms from primary law the only subsection amended this century.** That is
real progress: the remaining gap is no longer "find the statute" but
**"source § 1-5-101(b)'s observation shift, and confirm nothing amended the
section after 2017."**

It is still a block. A calendar built now would take its most delicate mechanic
— the both-ways weekend shift, in the years where Christmas Eve and Christmas
straddle a weekend — from a secondary source that disclaims itself, and would be
**wrong in whichever direction the shift actually runs**.

## 1b. UPDATE 2026-08-28 — one of the two questions is CLOSED; the other is not, and its cost is now known

### CLOSED: nothing amended § 1-5-101 after 2017

Michael checked Justia's 2024 code page, which carries the full amendment chain
back to 1943, and it ends at **Acts 2017, No. 561, § 4** — the act read from
primary in §1a. That matches, and the question is closed.

**What is being relied on there is worth naming precisely, because it is not the
same thing this gate refused to rely on elsewhere.** A publisher's *history
line* is a mechanical citation list, and it is the part of a secondary source
least likely to be wrong; the *substantive text* is the part that gets subtly
mis-rendered. This gate declined the second and accepts the first, and that
distinction is deliberate rather than a softening of the standard.

**A primary confirmation was attempted and is not cheaply available.** arkleg
serves Acts from 2017R onward, so a sweep of 2019R–2025R for `1-5-101` would
settle it from primary — but that is roughly a thousand PDFs per session, and
the per-session index that would collapse it is not published: every
`CodeSectionsAmended` path tried returns the same **42-byte 1×1 GIF**, and the
`/Acts/CodeSectionsAmended` page is JS-driven with nothing in static HTML.

### STILL OPEN: § 1-5-101(b), the observation shift

Michael also searched for the subsection (b) text and found:

- **Justia across multiple years, FindLaw, USLegal and the Encyclopedia of
  Arkansas** — all quoting the **identical** language.
- **One genuine primary hit on `codeofarrules.arkansas.gov`** — a banking rule
  that *cites* § 1-5-101 without *containing* it. Same category this gate
  already ruled out: a citation is not the text.

**Four independent secondary sources agreeing does not make a primary source**,
and the block stands. But it changes what the residual risk actually is: the
realistic failure is no longer "the language is wrong" — four publishers do not
independently invent the same sentence — it is "the language is stale relative
to an amendment nobody indexed", and §1a plus the closed question above make
that unlikely too.

**So the honest position is: high confidence, no primary source, and the gate
does not seed on confidence.** That is the same standard applied to Iowa, whose
currency could not be established and which stays blocked, and to Connecticut,
whose calendar basis is unresolved.

### What would actually clear it

In descending order of likely cost:

1. **The print or LexisNexis ACA** — Arkansas licenses its Code, so this is
   probably the only route to the codified text, and it is not a free one.
2. **The act that enacted or last amended subsection (b).** The chain runs 1943
   No. 211 → … → 2001 No. 304 → 2017 No. 561. Act 561 amended only (a)(2), so
   (b) predates it — and **arkleg serves nothing before 2017R**, which puts Act
   304 of 2001 and everything earlier out of reach on that host. A different
   official archive of pre-2017 Arkansas session laws would settle it.
3. **A court or agency document that QUOTES (b) rather than citing § 1-5-101.**
   The Treasurer's sheet was the near miss — it applies the rule without stating
   it, and 2025 happens to be a year where it never had to.

**Until one of those lands, Arkansas stays gated.** Everything else about the
state is ready: §§ 2–6 are unchanged and the seeding plan in §8 stands.


## 1c. UPDATE 2026-08-29 — THE BLOCK IS CLEARED, BY A CHANNEL THIS GATE NAMED AND HAD NOT TRIED

**Verdict amended: SEEDED, 13 rules, calendar 2026 ONLY.**

§1b listed three things that would clear this, in descending cost. The third was:

> **A court or agency document that QUOTES (b) rather than citing § 1-5-101.**
> The Treasurer's sheet was the near miss — it applies the rule without stating
> it, and 2025 happens to be a year where it never had to.

That is exactly what landed, on a host this gate never tried. Every earlier
attempt went to `media.ark.org/artreasury/`, where 2026 and 2027 both **403**.
The **SECRETARY OF STATE** publishes the same sheet:

```
https://www.sos.arkansas.gov/uploads/holidays_2026.pdf   200, 204,182 B, 1 page
https://www.sos.arkansas.gov/uploads/holidays_2027.pdf   404
https://www.sos.arkansas.gov/uploads/holidays_2028.pdf   404
```

Real text via pypdf, headed verbatim:

> **2026 State Holidays. Legal holidays by authority of Act 304 of 2001 and
> Amended by Act 561 of 2017.**

### It confirms §4, including both traps

The list is exactly what §4 had only from Justia — and the two things that make
Arkansas dangerous to guess at are both present and both correct:

- **CHRISTMAS EVE IS THERE**, `December 24 . . . Christmas Eve`. A calendar built
  from the federal list alone omits it.
- **JUNETEENTH AND COLUMBUS DAY ARE NOT.** Neither appears on the state sheet, so
  a calendar built from the state statute alone omits two days and computes
  **EARLY**. The union ARCP 6(a) requires is confirmed as mandatory rather than
  assumed.
- **"an employee's birthday" does not appear as a date**, as §4 predicted it
  could not.

### And it SHOWS subsection (b) operating, in the one 2026 instance where it fires

> `July 4 . . . Independence Day` **`(Observed on Friday, July 3, 2026)`**

4 July 2026 is a Saturday. That is the Saturday-to-preceding-Friday limb, applied
by the State's own publisher, for the exact year being encoded.

### WHAT IS STILL TRUE, and why the seed is capped at 2026

**§ 1-5-101(b) has still never been read on a primary source.** Nothing here
changes that, and the honest reason the seed can exist anyway is narrower than
"the block cleared":

> **The calendar is TRANSCRIBED, not DERIVED.** A holiday calendar in this engine
> is an enumerated list of dates, not a shift rule. Every 2026 date now comes off
> a primary state publication, so no unread statute is relied on. The gate blocked
> a *generated* calendar spanning years; it does not block a *transcribed* one for
> a year the State itself has published.

Two consequences, both recorded in the seed files:

1. **2027+ REFUSES `NOT_PROVISIONED`** rather than being derived. Adding a year
   means fetching that year's SoS sheet, not extending a rule. Same shape as
   Utah's 2026 cap, and the safe direction. Verified live.
2. **The Sunday limb is untested and unused.** No 2026 Arkansas holiday falls on
   a Sunday, so the half of (b) that four secondary publishers agree on and no
   primary source states never fires in what was seeded.

**If the ACA text of (b) is ever read from primary, that does not merely confirm
this — it is what would allow a GENERATED calendar and lift the 2026 cap.** The
three routes in §1b stand unchanged for that purpose.

### What was seeded

13 rules, all read verbatim from the court's own PDF (`opinions.arcourts.gov`,
1,311,020 B, 195pp, *"current through June 4, 2026"*), all live-verified on
`LAW-PINNACLE-2026`: **20/20 live assertions passed.**

**PER-RULE EFFECTIVE DATES, and this was nearly got wrong.** The first draft used
the collection's currency date, 2026-06-04, for every row — and every Rule 12 row
then refused `NO_RULE_IN_FORCE` for any trigger before June 2026, against rules
that were in fact in force. Each rule's own HISTORY line gives the real answer:
Rules 6, 33, 34 and 36 were *"amended and effective June 4, 2026"*; **Rule 12's
current text has been in force since *"amended June 21, 2018, effective January 1,
2019"***. A currency date and an effective date are different things, and the
engine — which computes against the law as it stood at the TRIGGER date — makes
the difference visible immediately.

§§ 2–7 are unchanged and still describe what was built.

## 2. THE WEEKEND-COVERAGE STANDING CHECK — step one

**ARCP Rule 6(a)**, verbatim on the operative part:

> The last day of the period so computed shall be included, **unless it is a
> Saturday, Sunday, legal holiday, or other day when the clerk's office is
> closed**, in which event the period runs until the end of **the next day that
> the clerk's office is open**.

Both weekend days named in the rollover clause. `isWeekend()` is correct on the
rule's own words.

**The eight answers now on record:**

| State | Answer |
|---|---|
| Louisiana | rolls only on a "legal holiday"; the statute covers neither day everywhere → **LATE → BLOCKED** |
| Oklahoma | 25 O.S. § 82.1(A) opens "Each Saturday, Sunday", statewide → safe, via the statute |
| Oregon | ORCP 10 A names "a Saturday or a legal holiday, including Sunday" → safe, via the rule |
| Connecticut | keys purely on clerk's-office closure; no holiday list exists → **premise fails** |
| Utah | URCP 6(a)(1)(C) names both days → safe at step 1 |
| Iowa | **splits by deadline type** — sentence one rolls Sunday only → **BLOCKED** |
| Nevada | NRCP 6(a)(1)(C) names both days → safe at step 1 |
| **Arkansas** | **Rule 6(a) names both days → safe at step 1** |

**The clerk's-office limb here is ADDITIONAL to the named days, not a
replacement for them** — Minnesota's shape, not Wisconsin's or Connecticut's.
Note it appears **twice**, though: as a rollover *trigger* ("or other day when
the clerk's office is closed") and as the rollover *target* ("the next day that
the clerk's office is open"). Both omissions run **EARLY**: an unmodelled
closure means the true deadline is later than the computed one. Safe, and
disclosable rather than blocking. The 2003 amendment note says this limb was
added to codify *Honeycutt v. Fanning*, 349 Ark. 324, 78 S.W.3d 96 (2002).

## 3. THE SHORT-PERIOD EXCLUSION IS FOURTEEN DAYS — a new number

> When the period of time prescribed or allowed is **less than fourteen (14)
> days**, intermediate Saturdays, Sundays, or legal holidays shall be excluded
> in the computation.

**Fourteen.** Six seeded states use **7** (NJ/NC/WA/MA/MO and Ohio/Indiana);
three use **11** (TN/AZ/WI); Minnesota, Utah and Nevada have **none at all**.
**Arkansas is the longest threshold in the platform**, and every seeded row
shorter than 14 days is affected by it. Copying any neighbour's number is wrong
in a direction that depends on which one — 7 would compute **EARLY** on periods
of 7–13 days, and no exclusion at all would compute EARLY on everything under 14.

Arkansas also **did not follow the federal 2009 amendment** that abolished the
exclusion entirely. The Reporter's Notes show the reverse trajectory: a 1986
amendment moved it to 11 days "consistently with the federal rule", and it has
since gone to 14 while the federal rule went to zero. **Do not reason from FRCP
6(a) here even though the Reporter's Notes call Rule 6 "practically identical to
FRCP 6".**

## 4. The holiday definition — a UNION of two lists, and one limb is not a date

Arkansas **deliberately declines to list its holidays in the rule.** Rule 6(a):

> As used in this rule and Rule 77(c), "legal holiday" means those days
> designated as a holiday by **the President or Congress of the United States
> OR designated by the laws of this State**.

and the Reporter's Notes say why: *"Section (a) has been changed somewhat by
omitting a recitation of specific legal holidays … It is redundant to list
specifically the holidays and then add … 'any other day appointed as a holiday
by the President o[r] the Congress' or by the State."*

**So the calendar is the UNION of the federal list and the state list** — the
first seeded jurisdiction that would need both. **Everything below is from
Justia and is not primary-sourced (§1).**

**Ark. Code Ann. § 1-5-101(a)** as Justia has it: New Year's Day (Jan 1); MLK
(third Monday in January); **George Washington's Birthday and Daisy Gatson Bates
Day** (third Monday in February); Memorial Day (last Monday in May);
Independence Day (July 4); Labor Day (first Monday in September); Veterans Day
(Nov 11); Thanksgiving (fourth Thursday in November); **CHRISTMAS EVE —
DECEMBER 24**; Christmas Day (Dec 25); and **"an employee's birthday — an
employee is granted one (1) holiday to observe his or her birthday."**

Three things follow, and each is a trap:

1. **CHRISTMAS EVE IS A HOLIDAY.** No seeded state has 24 December. It is also
   **adjacent to Christmas**, which makes the observation shift interact: when
   25 December falls on a Sunday it is observed Monday the 26th while the 24th
   (a Saturday) is observed Friday the 23rd — **two holidays on either side of a
   weekend that is itself two more non-days**. Any generator must be asserted
   against that year, not assumed through it.
2. **THE STATE LIST HAS NO JUNETEENTH AND NO COLUMBUS DAY — BUT THE UNION DOES**,
   because both are federal. A calendar built from the state statute alone would
   omit two days and compute **EARLY**; one built from the federal list alone
   would omit Christmas Eve. **Neither list on its own is correct.**
3. **"AN EMPLOYEE'S BIRTHDAY" IS NOT A CALENDAR DATE AT ALL.** It is a floating
   personal-leave day for state employees. Whether it is a "legal holiday"
   reaching court deadlines is doubtful — the subsection is about state
   employees' paid leave — but Rule 6(a) incorporates *"those days … designated
   by the laws of this State"* wholesale and does not filter. Unmodellable
   either way, and omitting it runs **EARLY**.

**The observation shifts agree, which is the one piece of luck here.**
§ 1-5-101(b): *"A holiday falling on a Saturday will be observed on the
preceding Friday. A holiday falling on a Sunday will be observed on the
succeeding Monday."* Both-ways, and **general rather than enumerated** — unlike
Nevada's and Utah's, which name the fixed dates they reach. 5 U.S.C. § 6103(b)
shifts the federal days the same way, so the union does not need two rules.

## 5. Rule 6(d) — THREE BUSINESS DAYS, e-service INCLUDED, and an EXPRESS answer carve-out

**ARCP Rule 6(d)**, verbatim:

> Whenever a party has the right or is required to do some act or take some
> proceedings within a prescribed period after the service of a notice or other
> paper upon him and the notice or paper is served upon him **by mail,
> commercial delivery company, or electronic transmission, including e-mail or
> service through the court's electronic filing system pursuant to Rule
> 5(b)(2), three (3) BUSINESS DAYS shall be added** to the prescribed period.
> **Provided, however, that this subdivision shall not extend the time in which
> the defendant must file an answer or pre-answer motion when service of the
> summons and complaint is by mail or commercial delivery company in accordance
> with Rule 4.**

Three separate things here, and all three cut against analogy:

**BUSINESS DAYS, NOT CALENDAR DAYS.** Every seeded extension adds calendar days
except California's two-court-day limbs and New York's one-business-day
overnight limb. Arkansas's whole extension is in business days. **The engine
already supports this** — `addUnit === 'business_days'` shares the court-day
branch, and `ny_cplr_2103b` already uses it — so this needs no engine change,
only care not to write `calendar_days` out of habit.

**ELECTRONIC SERVICE IS INCLUDED, EXPRESSLY.** E-mail and service through the
court's e-filing system both extend. That is the **opposite** of Nevada, West
Virginia, New York and the federal rule, where e-service is deliberately outside
the extension, and the opposite of Missouri, which handles it by a completion
rule instead. An allowlist copied from any of them would **under-count** and
compute EARLY.

**AND THE ANSWER CARVE-OUT IS EXPRESS.** This is the finding worth carrying
beyond Arkansas. Two federal rows were corrected on 2026-08-27 because FRCP 6(d)
reaches only service "under Rule 5(b)(2)" while a summons goes out under Rule 4
— a reading that had to be **inferred** from the cross-reference, and had been
got wrong. **Arkansas says it outright**, in a proviso, naming Rule 4. It is
direct textual confirmation that the reading applied to the federal rows is the
one a drafting court reaches when it bothers to say so.

Note the carve-out is **narrower than the federal position**: it excludes the
answer only where the summons was served *by mail or commercial delivery
company*. Whether an answer following some other Rule 4 method takes the three
days is not settled by the proviso, and would need reading before any answer row
carried an extension.

## 6. What is seedable — and one shape the engine already has

**Rule 12(a)(1)** carries **four** periods in one paragraph:

- **30 days** after service of summons and complaint;
- **30 days** from the date of **first publication or posting of the warning
  order** for a defendant served under Rule 4(g)(3) or (4);
- **60 days** for **a defendant incarcerated in any jail, penitentiary, or other
  correctional facility in this state** — a party-status period no seeded state
  has, and one the engine has no field for, so it must be its own trigger;
- **30 days** to answer or reply to a cross-claim or counterclaim.

Plus 12(a)(2)'s motion-tolling limbs, the Nevada/Utah shape.

**ALL THREE DISCOVERY RULES CARRY THE SAME DEFENDANT FLOOR, WITH THE SAME
NUMBERS** — which is itself unusual and worth stating, because Missouri gives
45/45/60, North Carolina 45/45/60, Minnesota 45/45/none and Massachusetts
none/45/45:

- **Rule 33**: *"within 30 days after the service of the interrogatories, except
  that a defendant must serve answers or objections within 30 days after the
  service of the interrogatories upon him **or within 45 days after the summons
  and complaint have been served** upon him, **whichever is longer**."*
- **Rule 34**: identical wording for the written response.
- **Rule 36**: *"a defendant shall have 30 days after service of the request or
  45 days after he has been served with the summons and complaint to answer,
  **whichever time is longer**."*

**That is `resolve_periods: later_of` with DIFFERENT COUNTS PER LIMB** — the
shape built after Georgia's O.C.G.A. 9-11-36(a)(2) shipped fifteen days early,
and Arkansas would be its third real user after Georgia and Minnesota. Both
limbs run from caller-supplied dates, so Arkansas does **not** hit the Maryland
chained-floor problem.

**Rule 6(c)** adds three more ordinary rows: a motion and notice of hearing
served **not later than 20 days before** the hearing (backward), a response
**within 10 days** after service of the motion, and a reply **within 5 days**
after service of the response. **Both the 10 and the 5 fall under the 14-day
short-period exclusion**, which makes §3 load-bearing rather than academic — and
the 20-day backward row would be the platform's first backward row outside the
federal seed.

## 7. What was NOT determined

- **Ark. Code Ann. § 1-5-101 on a primary source.** The blocker. Everything in
  §4 is from a self-disclaiming secondary source.
- **Whether the federal-list limb is read as the statutory federal holidays
  (5 U.S.C. § 6103) or only as ad hoc presidential proclamations.** The rule
  says "designated as a holiday by the President or Congress", which reads as
  the former, but it was not confirmed against Arkansas authority.
- **Whether "an employee's birthday" is a legal holiday for Rule 6 purposes.**
  Almost certainly not in substance; certainly not modellable.
- **Rule 4** (service of the summons, warning orders, and the Rule 4(g)(3)/(4)
  publication limbs), so what date a caller supplies for the Rule 12 triggers is
  not sourced.
- **Rule 5(b)(2)**, referenced by 6(d) for e-filing service.
- **Rule 77(c)**, which shares Rule 6(a)'s holiday definition and governs when
  the clerk's office is open.
- Appellate rules, which are a separate collection with their own currency date.

## 8. Verdict

**NOT SEEDABLE TODAY, AND THE ONLY THING IN THE WAY IS ONE STATUTE.**

The rules are official, current to a stated date, free, text-extractable and
structurally unremarkable: the weekend question answers itself at step one, the
clerk's-office limbs are additional rather than substitutive, the extension is
expressible with mechanisms the engine already has, the discovery floors fit a
shape already built, and the one question that has bitten this platform twice —
whether a service extension reaches an answer deadline — Arkansas answers in its
own text.

**What blocks it is that Rule 6(a) defines "legal holiday" by pointing at
Ark. Code Ann. § 1-5-101, and that statute is not available on any primary
source found.** `arkleg.state.ar.us` answers the request with a 1×1 GIF at
HTTP 200. Until it is read from an official source, a Arkansas calendar would be
derived from Justia, and the union-of-two-lists structure in §4 — with Christmas
Eve on one side and Juneteenth and Columbus Day on the other — is exactly the
kind of thing a secondary source gets subtly wrong.

**To close:** find § 1-5-101 on an official Arkansas source. If it confirms §4,
Arkansas seeds straightforwardly, with **14** as the short-period threshold,
**three business days** including e-service, no extension on the answer row, and
a `resolve_periods` floor on all three discovery rules.
