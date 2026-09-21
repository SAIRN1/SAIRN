# Maine — deadline-seed source-availability gate

**Run 2026-09-18 (Fourth).** Verdict at §6: **PASSED, with one finding that
decides the calendar and one dangling cross-reference that has been dangling
since 1974.** Maine is the best source position in this series since Ohio, and
the one real ambiguity **has a safe side**, which is what separates it from
Pennsylvania.

> **SEEDED 2026-09-21 (Fourth). §7 at the foot of this file is the record of
> what was built, what the gate got right, and the THREE things it did not
> have** — including the resolution of §5's UNVERIFIED prediction, which turned
> out to be the wrong question rather than a wrong answer. **Read §7 before
> relying on §5's build list**: two of its items changed on contact with the
> code. Nothing in §1–§6 is retracted; both PDF hashes were re-verified on
> 2026-09-21 and both matched.

**Why Maine.** The population-against-source-access criterion, continued from
the Pennsylvania gate. The states above Maine by population are all already
gated and all blocked or failed — Arizona (Westlaw), Colorado (rules behind an
"I Agree"), Tennessee (holiday statute behind a Lexis terms gate), Kentucky (no
definable "legal holiday"), Louisiana (Saturdays are holidays in *some parishes
only*), Iowa (split rollover + currency). **Maine (~1.40M) is the largest
unseeded state with no gate on it**, and it is small — that is stated plainly
rather than dressed up: this is the point in the series where the remaining
states are small, and the value of each additional one is falling.

---

## 1. Sources — the strongest position since Ohio

| Source | Location | Terms | Currency | Verified |
|---|---|---|---|---|
| M.R. Civ. P. 6 (per-rule, with Advisory Committee's Notes) | `courts.maine.gov/rules/text/MRCivPPlus/RULE%206.pdf` | none | — | **HTTP 200, 100,386 bytes, sha256 `8875d50ab9126df1c77a95919a9c31a04a7c3c04888bf57326532b55061283c7`** |
| Maine Rules of Civil Procedure, consolidated | `courts.maine.gov/rules/text/mr_civ_p_only_2026-06-01.pdf` | none | **"Last reviewed and edited May 14, 2026 / Includes amendments effective June 1, 2026"** | HTTP 200, 1,326,535 bytes, sha256 `263f9b45c296db9ad9f3dbafabefcd6106373baedddce38e326ecde5387584d0` |
| 4 M.R.S. §1051, *Legal holidays* | `legislature.maine.gov/statutes/4/title4sec1051-1.html` | none | page states "Data for this page extracted on 10/20/2025" | HTTP 200 |
| 1 M.R.S. §71(12), rules of construction | `legislature.maine.gov/statutes/1/title1sec71.html` | none | page states extracted 1/05/2026 | HTTP 200 |
| Court Holidays Observed (Judicial Branch) | `courts.maine.gov/courts/schedules/holidays.html` | none | 2026 and 2027 both published | HTTP 200 |

**ACCESS PASSES OUTRIGHT.** Plain fetch, HTTP 200, no paywall, no challenge, no
click-through. The rules index carries a bare `Copyright © 2026 / All rights
reserved` notice and **nothing resembling a terms acceptance** — the thing that
failed Tennessee and half of Colorado.

**THE RULE TEXT WAS DOWNLOADED AND HASHED, WHICH PENNSYLVANIA AND INDIANA WERE
NOT.** That is a source grade back up to Ohio's and Michigan's level. It was
also fetched **twice by two different routes** — once through the agent's
fetcher, once by a direct `urllib` request — and **both produced the identical
sha256 above**, which is what makes "this is the judiciary's own file" a checked
statement rather than a described one.

**AND THE RULE TEXT WAS CROSS-CHECKED AGAINST A SECOND DOCUMENT.** Rule 6(a) in
the per-rule PDF and Rule 6(a) in the June 2026 consolidated PDF are the same
text. Two documents, published separately, agreeing — not one document read
twice.

---

## 2. The rule, verbatim

M.R. Civ. P. 6(a), complete:

> "**(a) Computation.** In computing any period of time prescribed or allowed by
> these rules, by order of court, or by any applicable statute, the day of the
> act, event, or default after which the designated period of time begins to run
> is not to be included. The last day of the period so computed is to be
> included, unless it is a Saturday, a Sunday, or a legal holiday, in which event
> the period runs until the end of the next day which is not a Saturday, a
> Sunday, or a holiday. When the period of time prescribed or allowed is less
> than 7 days, intermediate Saturdays, Sundays and legal holidays shall be
> excluded in the computation.
>
> For the purpose of this subdivision legal holidays shall include days on which
> the Chief Justice of the Superior Court or Chief Judge of the District Court
> pursuant to Rule 77(c) specifically orders the clerk's office closed."

M.R. Civ. P. 6(c), complete:

> "**(c) Additional Time After Service by Mail.** Whenever a party has the right
> or is required to do some act or take some proceedings within a prescribed
> period after the service of a notice or other paper upon the party and the
> notice or paper is served upon the party by mail, 3 days shall be added to the
> prescribed period."

**PENNSYLVANIA'S BLOCKER DOES NOT EXIST HERE.** Maine says *"the period runs
until the end of the next day which is not a Saturday, a Sunday, or a holiday"*
— explicitly, in the operative sentence. There is no omit-versus-roll question
to send to counsel.

**ONE STANDARD COVERS BOTH RULE-MADE AND STATUTE-MADE DEADLINES, AND THAT IS
UNUSUAL.** 1 M.R.S. §71(12), verbatim in the operative part: a statutory period
"involved in or related to the commencement, prosecution or defense of any civil
… action or other judicial proceeding … **is governed by and computed under Rule
6(a) of the Maine Rules of Civil Procedure as amended from time to time**".
California needed **two** standards for exactly this split (`ca_ccp_12_12a` for
statutes, `ca_crc_1_10` for rules). **Maine's legislature pointed its own
statutes at the court rule**, so one standard is correct here — and it is
correct because a statute says so, not because the arithmetic happens to match.

---

## 3. THE FINDING THAT DECIDES THE CALENDAR: two holiday lists, and they diverge
   in the DANGEROUS direction

Maine publishes **two** sets of days and they are not the same set.

**(A) THE STATUTE.** 4 M.R.S. §1051 names twelve: annual Thanksgiving, New
Year's Day, Martin Luther King, Jr., Day (3rd Mon Jan), Washington's Birthday
(3rd Mon Feb), **Patriot's Day (3rd Mon Apr — Maine and Massachusetts only)**,
Memorial Day (last Mon May), Juneteenth (Jun 19), the 4th of July, Labor Day
(1st Mon Sep), Indigenous Peoples Day (2nd Mon Oct), Veterans Day (Nov 11),
Christmas Day. Its only observance rule: *"When any one of the holidays named in
this section falls on **Sunday**, the Monday following must be observed as a
holiday."*

**(B) THE JUDICIAL BRANCH'S PUBLISHED COURT HOLIDAYS**, whose own note reads
*"Holidays that fall on Saturday are observed on the preceding Friday; holidays
that fall on Sunday are observed on the following Monday."*

**DERIVED FROM §1051 AND CHECKED BY DAY OF WEEK AGAINST THE PUBLISHED LIST — and
every statutory day matched**, which is the cross-check, not a coincidence to be
noted afterwards. The divergence is exactly this:

| Year | Day | In §1051? | On the court list? |
|---|---|---|---|
| 2026 | **Thanksgiving Friday, 2026-11-27** | **No** | Yes |
| 2026 | **Independence observed Fri 2026-07-03** (Jul 4 is a Saturday) | **No** — §1051 covers Sunday only | Yes |
| 2027 | **Thanksgiving Friday, 2027-11-26** | **No** | Yes |
| 2027 | **Juneteenth observed Fri 2027-06-18** (Jun 19 is a Saturday) | **No** | Yes |
| 2027 | **Christmas observed Fri 2027-12-24** (Dec 25 is a Saturday) | **No** | Yes |
| 2027 | Independence observed Mon 2027-07-05 (Jul 4 is a Sunday) | **Yes** — the Sunday limb | Yes |

**§1051 HAS NO SATURDAY LIMB AT ALL.** It carries Sunday→Monday and stops. The
Judicial Branch's Saturday→Friday observance has no statutory source on this
page, and **that is three of the five divergent days**.

**WHY THE DIRECTION MATTERS MORE THAN THE COUNT.** Encoding the *bigger* list
when the *smaller* one is the legal test makes the engine roll a deadline off a
day that is not a holiday — Friday 2026-11-27 becomes Monday 2026-11-30, and a
date that is LATE is how a filing is missed. Encoding the *smaller* list when
the bigger one is right reports EARLY, and filing early is safe.

**AND BOTH LIMBS OF RULE 6(a) FAIL THE SAME WAY, WHICH IS WHY THIS IS SAFE AND
MARYLAND WAS NOT.** Checked in both directions rather than assumed from the
rollover alone:

* *Rollover:* a missing holiday means no roll → **earlier**.
* *Short-period exclusion (<7 days):* a missing holiday is one fewer intermediate
  day excluded → the count finishes sooner → **earlier**.

There is therefore a genuinely safe encoding, which Maryland's ≤7-day/mail
interaction did not have. **SEED THE STATUTORY TWELVE, NOT THE PUBLISHED
SCHEDULE**, and disclose the divergence — the Wisconsin resolution, reached from
Maine's own rule text rather than carried across.

---

## 4. THE DANGLING CROSS-REFERENCE, AND IT HAS BEEN DANGLING SINCE 1974

This is the finding worth banking even if Maine is never seeded.

Rule 6(a)'s second paragraph makes closure days into legal holidays when
ordered by *"the Chief Justice of the **Superior** Court or Chief Judge of the
**District** Court pursuant to Rule 77(c)"*.

**RULE 77(c) GIVES THOSE TWO OFFICERS NO SUCH POWER.** Verbatim: *"The clerk's
office … shall be open on all days except Saturdays, Sundays, legal holidays,
and such other days as the **Chief Justice of the Supreme Judicial Court** may
designate."*

**Rule 6's own 1974 Advisory Committee's Note says the amendment was made
"simultaneously with the amendment of Rule 77(c) placing in the hands of the
Chief Justice of the Supreme Judicial Court the fixing of days on which the
clerks' offices will be closed."** So the note and the rule text disagreed **on
the day they were adopted**, and the operative text has named the wrong officers
for fifty-one years.

**THIS IS THE FOURTH MOVED-CITATION TRAP IN FOUR CONSECUTIVE STATES** — Ohio
Civ.R. 6(E) re-lettered to 6(D) in 2012, Indiana's mail extension at T.R. 6(G)
still cited as 6(E), Pa.R.Civ.P. 106 rescinded outright, now this. The first
three were *secondary sources* citing a stale number. **This one is the rule
itself**, which is a harder version of the same defect and the reason the
standing check is "read the current rule set" rather than "distrust search
results".

**TWO READINGS, AND THEY MOVE REAL DATES:**

* **A — the names are a stale label** for whoever fixes closure days under
  77(c), i.e. the Chief Justice of the SJC. The published court-holiday list is
  then the Rule 6 holiday set, Thanksgiving Friday counts, and the bigger list
  is right.
* **B — the rule means what it says.** No Superior Court Chief Justice or
  District Court Chief Judge order exists to point at, so the limb is a dead
  letter and only §1051's twelve days count.

**IT DOES NOT BLOCK, BECAUSE §3'S SAFE SIDE COVERS IT.** Encoding the statutory
twelve is correct under reading B and EARLY under reading A. **It is a
disclosure, not a refusal** — and it belongs in the same bundled lawyer's
question as Illinois, Kentucky, Texas, West Virginia and now Pennsylvania.

---

## 5. What the seed would need, and the one prediction that is NOT verified

**A NEW ENGINE STANDARD, `me_mr_civ_p_6`:**

* `short_period_exclusion_days: 7` — *"less than 7 days"*, read from Maine's own
  text. **Ohio, Indiana and Florida also use 7 and that is not why this is 7.**
  The standing lesson from Ohio/Indiana/Michigan is that a shared threshold is
  a coincidence of drafting, and it is restated here because Maine's wording is
  *near-identical* to Ohio's, which is the most tempting case yet.
* **PREDICTED to map to the `ohio_civ_r_6a` implementation. NOT VERIFIED, and
  this is flagged rather than assumed** — Florida was predicted to be
  "data-only, no engine change" on exactly this reasoning and the prediction was
  wrong in the dangerous direction. The prediction is carried forward as
  UNVERIFIED and must be checked against the Ohio implementation's actual
  behaviour before a row is written.
* Suffixes: `base_period_suffix '(a)'`, `rollover_suffix_forward '(a)'` —
  Maine's subdivisions are real and citable, unlike Ohio's and Indiana's
  unlettered paragraphs. `months_years_suffix` **BLANK: Rule 6 does not address
  months or years at all.** `rollover_suffix_backward` **BLANK, and this is a
  hard bound, not a formality** — see below.
* Service extension: **3 days, MAIL ONLY**, per 6(c).

**BACKWARD-COUNTED ROWS ARE OUT OF SCOPE FOR MAINE AND THE REASON IS NOT THE
USUAL ONE.** Michigan, Pennsylvania and Illinois leave backward blank because
their rules are silent, and silence there is merely a citation problem. **For
Maine it is a safety problem**: when counting BACKWARD, an omitted holiday moves
the computed date LATER, so the under-inclusive calendar chosen in §3 —
deliberately safe forward — is **unsafe backward**. A Maine backward row would
invert the one property this whole gate rests on. Do not seed one.

---

## 6. Verdict

**PASSED.** Sources are official, free, ungated, current to 1 June 2026, and
hashed. The rule is explicit where Pennsylvania was silent. One statute points
Maine's own statutory deadlines at the same court rule, so a single standard is
correct rather than convenient.

**Two things are disclosed rather than resolved**, and both have a safe side:
the statutory-versus-published holiday divergence (§3) and the fifty-one-year
dangling cross-reference in Rule 6(a) (§4). Encoding the statutory twelve is
correct under one reading and EARLY under the other.

**NOT DETERMINED, stated rather than implied:**

* **Whether electronic service gets the 3 days.** M.R. Civ. P. 5(b) says
  Electronic Service *"shall have the same legal effect as the service of an
  original paper document"* — which does not say whether that paper document was
  *mailed*, and 6(c) adds days only for mail. **Tennessee is the warning here in
  reverse**: its Rule 5.02 expressly deems an emailed document "mailed for
  purposes of computation of time under Rule 6", and reading 6.05 alone gave a
  wrong EARLY answer. Maine has **no such deeming sentence**. So encode mail
  only, never electronic — that fails EARLY if the reading is wrong.
* **The Maine Rules of Unified Criminal Procedure Rule 45(a)**, which 1 M.R.S.
  §71(12) names for criminal matters. Not read. Criminal rows are out of scope,
  the same bound as every state in this series.
* **The Maine Rules of Appellate Procedure.** Not read; appellate rows out of
  scope.
* **Administrative weeks.** The Judicial Branch closes clerk's windows 8am–noon
  during three weeks a year (2026: Mar 30–Apr 3, Jul 27–31, Oct 19–23). A
  **partial-day** closure is not a day the office is "closed" under 77(c) and is
  not modelled. Recorded because Maryland's Rule 1-203(a)(2) *does* reach a
  clerk's office "closed for a part of the day", and somebody will ask whether
  Maine's is the same thing. It is not, on this text.
* **Years beyond 2027.** The published court list stops there; §1051 is
  derivable indefinitely, but a year not seeded must REFUSE rather than be
  derived silently — the New Jersey rule.

**THE SEED ITSELF WAS NOT BUILT IN THIS PASS.** This is the gate. The rule rows,
the 2026–2027 calendars and the engine standard are the next unit of work, and
the §5 prediction must be verified rather than assumed on the way in.

---

## 7. THE SEED, BUILT 2026-09-21 — and the three things this gate did not have

**§6 said "THE SEED ITSELF WAS NOT BUILT IN THIS PASS." It is built now.** This
section is appended rather than replacing anything above: the gate's reasoning is
what made the build cheap, and a gate rewritten after the fact stops being
evidence of what was known when.

### 7.1 Sources re-verified, not trusted

Both PDFs were downloaded again on 2026-09-21, three days after the gate, by a
plain `urllib` request:

| File | Bytes | sha256 | Matches §1? |
|---|---|---|---|
| `RULE 6.pdf` | 100,386 | `8875d50a…1283c7` | **yes** |
| `mr_civ_p_only_2026-06-01.pdf` | 1,326,535 | `263f9b45…7584d0` | **yes** |

4 M.R.S. §1051, 1 M.R.S. §71(12) and the Court Holidays Observed page were
re-fetched and re-read; every quotation in §2, §3 and §4 was confirmed word for
word, including Rule 77(c)'s "Chief Justice of the **Supreme Judicial** Court"
and Rule 6's 1974 Advisory Note.

### 7.2 What was built

* **`COMPUTATION_STANDARDS.me_mr_civ_p_6`** — `short_period_exclusion_days: 7`,
  `base_period_suffix` and `rollover_suffix_forward` both `(a)`,
  `months_years_suffix` and `rollover_suffix_backward` both blank.
* **`SERVICE_EXTENSION_STANDARDS.me_mr_civ_p_6_c`** — 3 days, **mail only**,
  `sequence: 'add_to_period_then_roll'`.
* **`JURISDICTION_COVERAGE.me`** — `direction: 'early'`, carrying §3's calendar
  divergence, §4's dangling cross-reference, the Thanksgiving-designation
  problem, and the 2023 trigger change.
* **`sql/sairnlaw_deadline_calendars_maine.json`** — the statutory twelve for
  2026 (11 dated entries) and 2027 (10). A statutory holiday falling on a
  weekend is **omitted rather than shifted**, because Rule 6(a) excludes
  Saturdays and Sundays by name; only §1051's Sunday→Monday limb produces an
  observed day, and in these two years it fires exactly once (Monday
  2027-07-05).
* **`sql/sairnlaw_deadline_seed_maine.json`** — 14 forward rows: Rule 12(a)'s
  five periods, the two 10-day post-motion periods, Rules 33 and 34 at 30 days,
  Rule 36 as a `later_of` **floor**, Rule 30(b)(5) at 5 days, and the three
  Rule 59 periods.
* **`api/legal-deadlines.js`** — `me: 'Maine'`, in the same commit as the seed.
* **`api/_lib/deadline-maine.test.js`** — 102 arms. **Sabotage-verified against
  20 deliberate defects, all 20 caught, control passing on the unmutated copy.**

### 7.3 §5's UNVERIFIED PREDICTION IS RESOLVED, AND IT WAS THE WRONG QUESTION

§5 predicted Maine would "map to the `ohio_civ_r_6a` implementation" and refused
to assume it, because Florida had been predicted "data-only" on the same
reasoning and was wrong in the dangerous direction. That caution was right and
the answer is not the one either side of the prediction expected:

**`impl` IS READ BY NOTHING IN THE ENGINE.** Every occurrence in
`api/_lib/deadline-engine.js` is a property definition or a comment; the only
readers of `std.impl` anywhere in the repository are test files asserting the
declaration. Behaviour comes entirely from the declared properties —
`short_period_exclusion_days`, `shifted_start`, `weekend_days` and the suffixes.

So there was never an implementation to map onto. **Verified by MUTATION rather
than by reading**, because reading only shows that nothing *appears* to use it:
the test replaces `impl` with `there-is-no-such-implementation` and asserts the
computed date does not move.

### 7.4 THREE THINGS THIS GATE DID NOT HAVE

**(a) A SUPERSEDED RULE TEXT IS SERVED AT A GUESSABLE URL WITH HTTP 200.** The
gate found Rule 6 at
`courts.maine.gov/rules/text/MRCivPPlus/RULE%206.pdf` and that file is current.
The same pattern **also returns 200 for `RULE%2012.pdf`, `RULE%2033.pdf`,
`RULE%2034.pdf` and `RULE%2036.pdf` — and those are DIFFERENT DOCUMENTS from the
`mr_civ_p_NN_plus_2023-11-15.pdf` files the civil-rules index actually links.**
The undated Rule 12 copy is **23 years stale**: its latest Advisory Committee's
Note is 1 May 2000 and its Rule 12(a) reads "within 20 days after the service of
the summons and complaint upon that defendant".

The current text, in both the index-linked per-rule PDF and the June 2026
consolidated book, reads "within 20 days after the service of the summons,
**complaint, and notice regarding Electronic Service** upon that defendant".

**THE COUNT DID NOT CHANGE. THE TRIGGER DID.** A seed built from the guessable
URL would have carried the right number of days and the wrong starting event,
and nothing would have said so — the date would simply have run from whenever
the complaint was served. This is the same family as the four moved-citation
traps §4 records, one level out: not a stale citation inside a document, but a
**stale document at a live address**. Every row's `effective_from` is therefore
taken from the effective date each document states on its own face —
**2023-11-15** for the rules the e-service amendment touched, **2014-11-01** for
the Rule 59 rows — and a matter triggered earlier is REFUSED.

**(b) THE UNDER-7-DAY EXCLUSION AND THE MAIL EXTENSION INTERACT, AND THE
ENGINE'S ORDER IS THE LATER OF TWO READINGS.** Found by driving the rows, not by
reading them. Rule 30(b)(5) gives 5 days, the only Maine period short enough to
reach 6(a)'s exclusion. Rule 6(c) **lengthens the period** rather than adding
days after it expires. Five plus three is eight.

* **Reading A**, which is what this engine computes: the exclusion applies to the
  5 days Rule 30(b)(5) prescribes, and 6(c)'s days are added to the result. From
  a Monday 2026-06-15 trigger: **2026-06-26**.
* **Reading B**: 6(c) makes the prescribed period 8, so 6(a)'s "less than 7
  days" test is no longer met and the count runs straight through: **2026-06-23**.

Maine's text settles neither, and **Reading A is the later**. Every other
disclosed gap in this seed fails EARLY, so rather than ship the one that fails
LATE on a period whose consequence is losing the right to object to inspection,
**the extension is not attached to that row**. It computes the unextended date,
which is at or before both readings, and **a mailed Rule 30(b)(5) objection is
declared not-computed**. Attaching the extension afterwards is a one-line change
once counsel answers.

**(c) MAIL-ONLY IS A POSITIVE READING, NOT A SHORTER LIST.** §6 reached "encode
mail only, never electronic" from the ABSENCE of a Tennessee-style deeming
sentence. Reading Rule 5(b) in full gives a stronger basis: 5(b)(2) offers three
routes in one sentence — "by **Electronic Service** to the last known electronic
mail address … or, if no electronic mail address is known, **mailing** it to the
last known regular mail address, or, if neither is known, by **leaving it with
the clerk** of the court" — and 6(c) picks out the middle one by name. So Maine's
own service rule distinguishes all three inside a single provision. That also
settles a question §5 did not ask: **leaving it with the clerk gets no days
either**, where `frcp_6d` extends for it. Carrying the federal allowlist across
would have added three days to two methods Maine does not extend, and added days
are the LATE direction.

One more thing read and found not to matter: Rule 5(b) says "Service by regular
mail is complete upon mailing", so Maine needs **no**
`SERVICE_COMPLETION_STANDARDS` entry. Missouri needed one because its rule moves
the completion date instead of adding days.

### 7.5 One more thing the gate's §3 did not name: Thanksgiving has no date

§3 lists "annual Thanksgiving" among §1051's twelve. Read again for the calendar,
the statute says **"any day designated for the annual Thanksgiving"** — a
designation, not the fourth Thursday. So its date comes from an annual
proclamation this engine cannot read. It is encoded as the fourth Thursday and
that derivation was **checked against the published court list for both seeded
years** rather than assumed. It is also the sharpest reason a year beyond 2027 is
REFUSED rather than generated: eleven of the twelve days would generate
mechanically, and a generated year would hide this one behind a confident answer.

### 7.6 What is still not seeded, restated because §6's list has changed

Unchanged and still out of scope: **criminal** (M.R.U. Crim. P. 45(a), not read),
**appellate** (M.R. App. P., not read), **backward-counted rows** (the
under-inclusive calendar is safe forward and unsafe backward — a hard bound, not
a formality), **administrative-week part-day closures** (not a 77(c) closed day
on this text), and **years beyond 2027** (REFUSED rather than derived).

Newly on the bundled lawyer's question, alongside §4's cross-reference: whether
Rule 6(c) reaches a summons and complaint served by mail under Rule 4 (omitted,
which reports EARLY), and the §7.4(b) exclusion-versus-extension order.
