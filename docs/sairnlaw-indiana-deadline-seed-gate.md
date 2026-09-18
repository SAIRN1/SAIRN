# Indiana — deadline-seed source-availability gate

**Run 2026-09-18 (Fourth).** Verdict at §8: **PASS WITH CONDITIONS**, and the
conditions are load-bearing. This is the first state in this run that does not
pass cleanly.

**Why Indiana, and why it is the weakest of the three by the same criterion.**
Ohio and Michigan were picked because their computation standard was already in
the engine. Indiana is the **last** such state — and it is the weak one:
`indiana_tr_6a` has its own `impl`, reached by **no seeded jurisdiction**, so
unlike Ohio (exercised by MA and MO) and Michigan (mapped to the `frcp_6a`
implementation 34 standards run on) **its implementation has never executed
against a real rule set.** Gating it is therefore also the first exercise of
that code, and the gate has to carry that.

---

## 1. Sources — rules PASS on a primary source; the HOLIDAY STATUTE DOES NOT

| Source | Location | Terms | Currency |
|---|---|---|---|
| Ind. Trial Rule 6 | `rules.incourts.gov/Content/trial/rule6/current.htm` | none — official judiciary site | **effective 1 July 2026**, amendment order 9 June 2026 |
| IC 1-1-9-1 (legal holidays) | ⚠ **secondary** — `codes.findlaw.com` | none | current text, amendment date not established |

⚠ **THE HOLIDAY STATUTE WAS NOT READ ON A PRIMARY SOURCE AND THAT IS A REAL
DIFFERENCE FROM THE LAST TWO GATES.** Ohio's and Michigan's rule texts were
downloaded, hashed and quoted from the official PDF. Here `iga.in.gov` returned
a page this session could not extract and the official county PDF mirror 403'd,
so IC 1-1-9-1 below is from a legal publisher. **Everything in §4 that rests on
that text is therefore one grade weaker than the Ohio and Michigan equivalents
and must be re-read against iga.in.gov before any Indiana row is seeded.** It is
recorded here rather than quietly accepted, because "I could not reach the
primary source" and "I read the primary source" are different claims.

The **rules** half is primary and current: T.R. 6 as amended 9 June 2026,
effective 1 July 2026.

---

## 2. Counting — WIDER than Ohio's and the federal, exactly as the engine records

T.R. 6(A), from the judiciary's own page:

> The final day is included unless it falls on a Saturday, a Sunday, a legal
> holiday, **or a day the office is closed during regular hours**. "In any
> event, the period runs until the end of the next day that is not a Saturday, a
> Sunday, a legal holiday, or a day on which the office is closed."

> "When the period of time allowed is **less than seven days**, intermediate
> Saturdays, Sundays, legal holidays, **and days on which the office is closed**
> must be excluded from the computations."

**THE ENGINE'S OWN COMMENT WAS RIGHT AND IS NOW VERIFIED AGAINST SOURCE.**
`deadline-engine.js` records that Indiana and Ohio "only LOOK alike: both use a
seven-day threshold, but Indiana's exclusion set is strictly WIDER — the
office-closed limb has no Ohio or federal analog and is NOT modelled by this
engine, which has no field for a given clerk's office closures." Confirmed word
for word. **Weekend standing check (row 400): SAFE** — both days named.

---

## 3. The service extension — +3 for US mail, and the DIVISION LETTER HAS MOVED

> "Whenever a party has the right or is required to do some act or take some
> proceedings within a prescribed period after the service of a notice or other
> paper and the notice or paper is served by United States mail, **three days
> must be added** to the prescribed period."

**It is T.R. 6(G) on the current rule, not 6(E).** Secondary sources and older
practice material cite 6(E); the judiciary's current page puts it at (G).
Recorded because a seed row citing a division letter that has moved is the
Ohio Civ.R. 6(E) problem again — that citation had been dead fourteen years.

**United States mail only.** No commercial-carrier limb (Ohio has one), and no
electronic limb. **The West Virginia trap is checked and ABSENT**: the rule
names the service method in words rather than pointing at a subparagraph, so
there is no pointer that can contradict a parenthetical.

---

## 4. The holiday list — and this is where Indiana stops being like the others

IC 1-1-9-1 names **fourteen** legal holidays. Eleven are ordinary:
New Year's (1 Jan) · MLK (3rd Mon Jan) · **Lincoln (12 Feb)** · Washington
(3rd Mon Feb) · Memorial (last Mon May) · Independence (4 Jul) · Labor
(1st Mon Sep) · Columbus (2nd Mon Oct) · Veterans (11 Nov) · Thanksgiving
(4th Thu Nov) · Christmas (25 Dec).

**Lincoln's Birthday again** — Indiana has it, like Michigan, and the federal
calendar does not. A calendar copied from a federal list is wrong for both.

**AND BOTH SHIFTS ARE STATUTORY AND GENERAL:** a holiday other than Sunday
falling on Sunday is observed the following Monday; **a holiday falling on
Saturday is observed the PRECEDING FRIDAY.** Michigan had no Saturday shift and
Ohio's lived only in a Supreme Court practice rule. Indiana's is in the statute
and applies to all fourteen. Both must be modelled. *Omitting* the Saturday
shift errs EARLY on a forward count — the engine would return a Friday that is
really a holiday — so it is safe-direction, but it is plainly wrong and there is
no reason not to carry it.

### The two that are not ordinary

**GOOD FRIDAY — "a movable feast day".** Derivable only from the computus.
**This platform already has one**: the Hawaiʻi calendar derives Good Friday
rather than transcribing it (3 April 2026), and Hawaiʻi's coverage entry records
the reasoning. So Indiana does not need a new mechanism — it needs the existing
one pointed at a second state. **That is a real engine touch, however small, and
it is the reason this gate cannot claim the zero-engine-work position Ohio and
Michigan both had.**

**ELECTION DAY — "the day of any general, municipal, or primary election".
THIS IS THE BLOCKER, AND IT IS WIDER THAN ANY ELECTION LIMB ALREADY ON THE
PLATFORM.** Hawaiʻi's is "all election days, **except primary and special**
election days, in the county wherein the election is held" and is recorded there
as omitted-because-county-scoped. **Indiana's includes primary AND municipal
elections**, which are neither statewide nor annual nor formula-derivable: a
municipal primary in one city is a legal holiday under this section and cannot
be computed from any rule. There is no published statewide list of every
municipal and primary election date, and manufacturing one would be inventing
law.

**Direction, determined before deciding what to do:** an omitted holiday on a
FORWARD count of seven days or more makes the computed date EARLIER than the
true one, which is safe. It inverts on a BACKWARD count and inside the
sub-seven-day exclusion, where omitting an intermediate holiday lands the date
CLOSER to the trigger — i.e. LATER than the rule allows. That is the Mississippi
reasoning and it applies here unchanged.

---

## 5. What is seedable, and the conditions are not optional

**SEEDABLE:** forward-counted rows of **seven days or more**, with

* both statutory shifts modelled (Sunday→Monday, Saturday→preceding Friday);
* Good Friday derived from the existing computus;
* the eleven ordinary holidays generated;
* **Election Day omitted and DISCLOSED**, not guessed;
* the office-closed limb omitted and disclosed (no field for it, as with Ohio's
  and Utah's equivalents).

**NOT SEEDABLE, and these are refusals rather than gaps:**

* **any BACKWARD-counted row.** Every omission above reports LATE on a backward
  count.
* **any row shorter than seven days.** T.R. 6(A)'s exclusion set is wider than
  the engine models, and an omitted intermediate holiday shortens the period.

---

## 6. What was NOT determined

* **The primary text of IC 1-1-9-1** (§1). Re-read before seeding.
* **The Indiana Rules of Appellate Procedure** — not read at all, so every
  appellate row is out of scope, the same bound Ohio and Michigan set.
* **Whether `indiana_tr_6a`'s implementation is correct.** Its `impl` is
  unexercised by any seeded jurisdiction, so this gate establishes what the RULE
  says and not that the CODE agrees with it. Ohio's gate could drive Michigan's
  and Ohio's arithmetic against worked examples the rules supplied; T.R. 6
  supplies none. **The seed must begin by driving `indiana_tr_6a` against
  hand-computed dates, and that work is not done here.**

---

## 7. Verdict

**PASS WITH CONDITIONS.** Rules are primary, official, free of terms and current
to 1 July 2026. The weekend standing check is safe. The West Virginia trap is
absent. The counting rule is confirmed wider than the engine models, exactly as
the engine already said.

**But three things separate Indiana from Ohio and Michigan, and all three are
real:** the holiday statute was not read on a primary source; Election Day is
un-derivable and its limb is the widest on the platform; and the engine standard
has never executed. The first two are disclosures with a safe direction on
forward counts and refusals on backward ones. The third means this is the first
gate in the run that cannot say "the engine work is zero".

**Seeding may proceed only for forward rows of seven days or more**, and only
after IC 1-1-9-1 is re-read on `iga.in.gov`.

---

## 9. RE-READ 2026-09-18 — the Election Day limb is RESOLVED, and by a better source than the one I was chasing

**The primary statute still could not be read, and the failure is now measured
rather than asserted.** `iga.in.gov` serves a **691-byte JavaScript shell** for
every Indiana Code URL tried (2025 and 2026 title indexes, both identical,
`sha256 61d9d1265c82…`) — there is no statute text in the response at all.
`law.justia.com`'s section page 403s. The official county PDF mirror 403s.
`law.onecle.com` 404s. So IC 1-1-9-1's own words remain second-hand.

**BUT THE QUESTION THAT MATTERED WAS ANSWERABLE FROM A BETTER SOURCE, AND I WAS
CHASING THE WRONG DOCUMENT.** T.R. 6(A) rolls off a "legal holiday", and what a
court deadline actually turns on is which days the COURTS observe. The Indiana
Judicial Branch publishes exactly that, itself, at **`in.gov/courts/holidays/`**
— a primary, court-published source, and more on point than the general holiday
statute.

**IT PUBLISHES THE ELECTION DAYS.** For 2026: **Primary Election Day, 5 May**
and **General Election Day, 3 November**, named with their dates. It also
publishes **Good Friday, 3 April 2026**, and Lincoln's and Washington's
Birthdays.

### What that changes

**THE ELECTION DAY LIMB IS NOT A PERMANENT BLOCKER. IT IS INGESTED, NEVER
DERIVED** — which is the Maryland pattern this platform already runs: that
calendar is "taken from the Judiciary's own published list rather than
generated, and a year it does not cover is REFUSED rather than derived."
Indiana takes the same shape, and for the same reason: a day that depends on an
election schedule cannot be computed from a rule, and generating it would hide
that behind a confident answer.

**AND GOOD FRIDAY NEED NOT BE COMPUTED AT ALL** for a covered year — the
schedule states the date. The computus is still the right mechanism if the
calendar is ever extended past the published years, but it is not on the
critical path for seeding.

### The residual is now sharper, and it is the court's own sentence

> "County court and clerk's offices **may observe different hours and holidays
> than state offices**."

That is the Judicial Branch disclaiming its own list for the county courts where
almost every trial-level deadline is actually filed — the **Mississippi shape**,
in the publisher's own words, and this platform already refuses to seed a
statewide Mississippi calendar for exactly it. Two consequences:

* **A MUNICIPAL election is a legal holiday under IC 1-1-9-1 and is NOT on the
  state schedule**, which carries only the statewide primary and general. So the
  state list is INCOMPLETE for a county in a municipal election year, and the
  omission reports EARLY on a forward count — safe, and it must be disclosed.
* **A county may also observe a day the state list does NOT carry.** Same
  direction, same disclosure.

### The verdict is unchanged in force and better founded

Still **PASS WITH CONDITIONS**, still forward-only and seven days or more, still
no backward rows. What changes:

* Election Day moves from *"un-derivable, therefore disclosed"* to **"ingested
  per year from the Judicial Branch schedule, and a year that schedule does not
  cover is REFUSED"** — the Maryland rule, not a gap.
* The **county-divergence disclaimer replaces it as the sharpest residual**, and
  it is worse, because it is unbounded and comes from the publisher.
* **IC 1-1-9-1 is still second-hand** and the Saturday/Sunday shift sentences
  still rest on it. The shifts must be modelled, and the statute must be read
  first-hand before a seed lands — the state schedule says nothing about weekend
  observance, so it cannot substitute for the statute on that point.
