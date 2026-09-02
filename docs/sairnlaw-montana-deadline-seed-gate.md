# Montana — deadline-seed source-availability gate

**Verdict: PASS. Ready to seed, with five disclosures and one scoping decision
that is mine and can be overruled.** Gated 2026-09-02 (Hank). No rows are
seeded by this document; it is the gate that precedes the seed, in the same
shape as every other state's gate doc in this directory.

**Why Montana over the seven other never-gated states** (Alaska, Maine, North
Dakota, Rhode Island, South Dakota, Vermont, Wyoming): it was named as the next
jurisdiction in the standing queue rather than chosen here. What the gate found
is that it is a good choice for a reason nobody could have known in advance —
its rules are the post-2009 federal text almost verbatim, which makes the four
places it *departs* from the federal text the entire risk surface, and every one
of those four is load-bearing.

---

## 1. Sources — PASS, and the retrieval is as clean as Delaware's

| What | Where | Result |
|---|---|---|
| M.R.Civ.P. Rules 4, 5, 6, 12, 33, 34, 36, 59 | `mca.legmt.gov/bills/mca/title_0250/chapter_0200/...` | **200** on every section, plain browser header, first attempt |
| Justice & City Court R. Civ. P. 6 | `mca.legmt.gov/bills/mca/title_0250/chapter_0230/part_0010/section_0060/...` | **200** |
| Legal holidays, MCA § 1-1-216 | `mca.legmt.gov/bills/mca/title_0010/chapter_0010/part_0020/section_0160/...` | **200** |
| General election date, MCA § 13-1-104 | `mca.legmt.gov/bills/mca/title_0130/chapter_0010/part_0010/section_0040/...` | **200** |
| MCA § 1-1-216 as it stood in **2011** and in **2023** | `mca.legmt.gov/bills/2011/...` and `mca.legmt.gov/bills/2024/...` | **200** — see §4, this is what dated the Presidents' Day question |

**Everything is in one place, and that is unusual.** Montana codifies its Rules
of Civil Procedure *inside the statute code* — MCA Title 25 ch. 20 — so the
rules, the holiday statute and the election statute all come from the same
authenticated source with the same URL scheme and the same per-section
`History:` line. No court website, no PDF, no click-through, no CAPTCHA.
Contrast New Hampshire, where no effective date is published anywhere, and
Colorado and Tennessee, which are gated out entirely behind terms acceptance.

**Every rule carries a per-section amendment history**, e.g. Rule 59: `En. Sup.
Ct. Ord. No. AF 07-0157, April 26, 2011, eff. Oct. 1, 2011; amd. Sup. Ct. Ord.
No. AF 07-0157, December 14, 2016, eff. July 1, 2017.` That is the
Hawaii/Idaho/Nebraska/New Mexico/Delaware position.

**One honest limit on that:** the history is published **per rule, not per
subsection**. Rule 59 was amended as a whole in 2016 and only part of it plainly
changed, but the source does not say which part, so all three seeded Rule 59
rows carry `2017-07-01`. That is what the source supports. It is stated in the
seed rather than refined by guess.

---

## 2. The computation standard — `mt_rcp_6a`

M.R.Civ.P. 6(a), on the operative limbs, verbatim:

> **(a) Computing Time.** The following rules apply in computing any time period
> specified in these rules, or court order, or in any statute that does not
> specify a method of computing time.
> **(1) Period Stated in Days or a Longer Unit.** … (A) exclude the day of the
> event that triggers the period; (B) **count every day, including intermediate
> Saturdays, Sundays, and legal holidays**; and (C) include the last day of the
> period, but **if the last day is a Saturday, Sunday, or legal holiday**, the
> period continues to run until the end of the next day that is not a Saturday,
> Sunday, or legal holiday.
> **(3) Inaccessibility of the Clerk's Office.** Unless the court orders
> otherwise, if the clerk's office is inaccessible: (A) on the last day for
> filing under Rule 6(a)(1), then the time for filing is **extended** to the
> first accessible day …
> **(5) "Next Day" Defined.** The "next day" is determined by continuing to
> count **forward** when the period is measured after an event and **backward**
> when measured before an event.

### 2.1 NO SHORT-PERIOD EXCLUSION, AND THE ABSENCE IS THE MOST LOAD-BEARING FACT IN THIS SEED

Rule 6(a)(1)(B) counts **every day**. Montana has no threshold at all — not
Ohio's and Indiana's 7, not Arkansas's 14, not Alabama's, Wisconsin's and
**Delaware's 11**.

Five of the fifteen seeded rows are shorter than 15 days: three 14-day rows, one
14-day backward row and one 7-day backward row. Under an 11 or a 14 every one of
them would exclude intermediate weekends and land **later**, and late is the
direction that loses a filing. Worked and asserted in the suite: a 14-day period
from Monday 1 June 2026 is **Monday 15 June**; counting business days only gives
**Friday 19 June**, four days apart.

**This is the trap that Delaware sets for Montana specifically**, because
Delaware is the most recently gated state, its Rule 6(a) is also headed 6(a),
and it *does* carry an 11.

### 2.2 The rule names both weekend days itself

"if the last day is a Saturday, Sunday, or legal holiday" — so the engine's
`[Sat, Sun]` default is correct and **no `weekend_days` declaration belongs
here.** Checked deliberately, because **MCA § 1-1-216(1)(a) makes each SUNDAY a
statutory legal holiday and never lists Saturday at all.** That is Louisiana's
shape, and the exact inverse of Delaware's (where Saturdays are statutory and
Sunday is not listed). It changes nothing, for the same reason it changed
nothing in Delaware: Rule 6(a)(1)(C) does not defer the weekend question to the
statute the way La. C.C.P. art. 5059(A) does.

### 2.3 Backward periods are addressed EXPRESSLY, which Delaware's rule is not

Rule 6(a)(5) supplies the sentence Delaware's Superior Court Rule 6(a) lacks. So
Montana can carry backward rows where Delaware deliberately carried none, and
two are seeded — Rule 6(c)(1)'s 14-day motion notice and Rule 6(c)(2)'s 7-day
opposing affidavit.

### DISCLOSURE 1 — the clerk's-office inaccessibility limb is not modelled

Rule 6(a)(3) **extends** the time for filing to the first accessible day when
the clerk's office is inaccessible. This engine has no field for a given court's
closures and cannot acquire one from a statute.

**Direction: SAFE.** The limb is **additional** to the weekend/holiday test
rather than a replacement for it — the Minnesota and Utah shape — so omitting an
inaccessible day returns the earlier, unrolled date. Contrast **Wisconsin**,
where the closure test *replaces* the holiday test inside the same sentence and
the omission could not be made safe.

### DISCLOSURE 2 — Rule 6(a)(4)'s closing time is not a date question and is still a gap

"the last day ends … for electronic filing, at midnight in the court's time
zone; and **for filing by other means, when the clerk's office is scheduled to
close**." This engine computes a **date** and expresses no time of day, so a
paper filing made after the counter closes on the correct date is late by a rule
this seed cannot express. Disclosed rather than silently ignored.

---

## 3. The holiday definition — and it is NOT a plain incorporation of § 1-1-216

This is the most interesting thing in the Montana gate and it has no analogue in
any seeded state. Rule 6(a)(6), verbatim:

> **(6) "Legal Holiday" Defined.** "Legal holiday" means:
> **(A)** the day set aside **by statute for observing** New Year's Day, Martin
> Luther King, Jr. Day, **Lincoln's and Washington's Birthdays**, Memorial Day,
> Independence Day, Labor Day, Columbus Day, Veterans' Day, Thanksgiving Day,
> Christmas Day, or **state general election day**;
> **(B)** any day declared a holiday by the President of the United States or by
> the Governor of this state; and
> **(C)** **for periods that are measured after an event**, any other day
> declared a holiday by the state.

**THE SET IS GENUINELY WIDER FORWARD THAN BACKWARD.** Limb (C) applies only to
forward periods, by its own words. No other seeded jurisdiction has a
direction-dependent holiday definition. The engine already has the mechanism for
it (`kind: 'state'` is skipped on non-forward directions) and **Montana does not
need it**, because every 2026 date in the calendar is reached in both
directions — see §4.

### 3.1 MCA § 1-1-216, and what it does and does not contain

> (1) … (a) each Sunday; (b) New Year's Day, January 1; (c) Martin Luther King
> Jr. Day, the third Monday in January; **(d) Presidents' Day, the third Monday
> in February**; (e) Memorial Day, the last Monday in May; (f) Independence Day,
> July 4; (g) Labor Day, the first Monday in September; **(h) Indigenous
> Peoples' Day and Columbus Day, the second Monday in October**; (i) Veterans'
> Day, November 11; (j) Thanksgiving Day, the fourth Thursday in November; (k)
> Christmas Day, December 25; **(l) state general election day.**
>
> (2)(a) If any of the holidays in subsections (1)(b) through (1)(l) fall on a
> **Sunday**, the Monday following is a holiday. **(b) If any of the holidays in
> subsections (1)(b) through (1)(l) fall on a Saturday, the Friday preceding is
> a holiday.** (c) All other days are business days.

**NOT PRESENT, and each is in some neighbour's list:** no day after
Thanksgiving (Delaware and Nebraska have one), no Good Friday (Delaware and
Hawaii do), **no Juneteenth at all**. A calendar copied from any of them reports
**LATE**.

### 3.2 The Saturday shift IS carried, and it is a citation

§ 1-1-216(2)(b) was added by **Ch. 131, L. 2013** — verified by fetching the
2023 edition of the section, which already contains it, against the 2011 edition,
which contains only a Sunday limb. It has therefore been in force for every year
this platform computes.

**Rule 6(a)(6)(A) reaches "the day set aside by statute FOR OBSERVING" the named
holidays** — an observance reference, not a date reference — so the shifted day
is inside it. **4 July 2026 is a Saturday, so FRIDAY 3 JULY 2026 is a Montana
legal holiday and the calendar carries it.**

Montana therefore joins the two-thirds of seeded states that observe that
Friday. The reasons still differ per state and a neighbour's answer is still
never evidence: an explicit shift clause inside the cited section (Idaho,
Nebraska), inside the cited *chapter* (Delaware, Maryland), a shift clause that
fell **outside** the reference (Hawaii), no Saturday limb at all (New
Hampshire) — and now Montana, where the reference is to the day set aside **for
observing** rather than to a section or a chapter.

### 3.3 The state general election day IS carried, and Montana needs no reach at all

Rule 6(a)(6)(A) names **"state general election day"** in the rule's own list.
§ 1-1-216(1)(l) uses **the same three words**. § 13-1-104(1) fixes it: "A
general election must be held throughout the state on the **first Tuesday after
the first Monday in November**." The first Monday in November 2026 is Monday the
2nd, so the day is **Tuesday 3 November 2026**, verified by weekday.

**This is a shorter reach than any equivalent so far.** Delaware's needed the
state constitution; New Hampshire's was **omitted** because RSA 288:1 names a
"biennial election" that ch. 652 never defines. Here three provisions use one
term.

2026 is an **even-numbered** year, which § 13-1-104(2) makes the year in which
federal officers, legislators, state officers, district judges and county
officers are elected, so a state general election unambiguously occurs.

### DISCLOSURE 3 — limb (B) and limb (C) are open-ended

"any day declared a holiday by the President … or by the Governor" and, forward
only, "any other day declared a holiday by the state". Underivable, the same
shape as Idaho Code § 73-108 and HRS § 8-1's proclamation limbs. Disclose; do
not attempt to enumerate.

---

## 4. The one real interpretive question: Presidents' Day

**Rule 6(a)(6)(A) names "Lincoln's and Washington's Birthdays". The statute no
longer uses those words.**

This is not an old drafting mismatch. It is **fourteen months old**, and it was
found by pulling two prior editions of the section rather than by reading the
current one:

| Edition | § 1-1-216(1)(d) |
|---|---|
| **2011** (when the rule was adopted, eff. 1 Oct 2011) | "**Lincoln's and Washington's Birthdays**, the third Monday in February" |
| **2023** | "**Lincoln's and Washington's Birthdays**, the third Monday in February" |
| **2025** (current) | "**Presidents' Day**, the third Monday in February" |

**Ch. 561, L. 2025 (SB 224)** — the Indigenous Peoples' Day bill — renamed that
entry and **moved nothing**. The rule's list was not conformed. So the rule now
names a holiday by a name the statute has stopped using, for a day that has not
changed.

**It is carried in both directions, and each direction has its own reason.**

- **Forward: certain, twice over.** On any ordinary reading the third Monday in
  February is still "the day set aside by statute for observing" those
  birthdays. Independently, **limb (C)** reaches "any other day declared a
  holiday by the state" for periods measured after an event, and § 1-1-216(1)(d)
  plainly is such a declaration. Limb (C) closes the question outright.
- **Backward: limb (C) is unavailable by its own terms**, so only the (A)
  reading carries it — and **carrying is the SAFE direction there.** A backward
  period that fails to roll off a holiday reports a date **LATER** than the true
  one, which is the direction that loses the filing. Omitting would be the
  unsafe choice, which is the opposite of the usual calculus and is why this
  needed working out rather than pattern-matching.

For 2026 that day is **Monday 16 February**. Asserted in the suite in both
directions.

**Indigenous Peoples' Day raises no equivalent question**: the rule names
"Columbus Day" and the statutory entry still contains those words verbatim, and
the 2025 amendment added a name to an existing day rather than creating one.

---

## 5. Periods available to seed — all quoted from the read

| Rule | Period | Note |
|---|---|---|
| 12(a)(1)(A) | Answer **21 days** after service of the summons and complaint | Carve-out in the rule itself for Rule 4(c)(2)(C) statutory exceptions |
| 12(a)(1)(B) | Answer to a counterclaim or crossclaim **21 days** | Same count, different extension treatment — see §5.1 |
| 12(a)(1)(C) | Reply to an answer **21 days** after service of an order to reply | "unless the order specifies a different time" |
| 12(a)(2) | State/agency/official-capacity answer **42 days** after service on the attorney general | **Not the federal 60** |
| 12(a)(3) | Individual-capacity officer **42 days** after the **later of** two services | `resolve: later_of` — one count, two start dates |
| 12(a)(4)(A) | Responsive pleading **14 days** after notice of the court's action on a Rule 12 motion | |
| 12(a)(4)(B) | Responsive pleading **14 days** after a more definite statement is served | |
| 33(b)(2) | Interrogatory answers **30 days**; defendant **may** serve within 45 — an **election** | |
| 34(b)(2)(A) | Production response **30 days**; same **election** | |
| 36(a)(3) | Admissions — **"shall not be required to serve … before the expiration of 45 days"**, a **FLOOR** | Self-executing |
| 59(b) | New trial **28 days** after entry of judgment | **Non-extendable** under 6(b)(2) |
| 59(c) | Opposing affidavits **14 days** after being served | |
| 59(e) | Alter or amend **28 days** after entry of judgment | **Non-extendable** |
| 6(c)(1) | Motion and notice of hearing **at least 14 days BEFORE** the hearing | Backward |
| 6(c)(2) | Opposing affidavit **at least 7 days BEFORE** the hearing | Backward; **carves out Rule 59(c)** |

### 5.1 Rule 6(d) — the pre-2016 federal set, and it is NOT `frcp_6d`

> "When a party may or must act within a specified time after service and
> service is made under **Rule 5(b)(2)(C), (D), or (E), or (F)**, 3 days are
> added **after the period would otherwise expire under Rule 6(a)**."

**Federal Rule 6(d) dropped subparagraph (E) — electronic service — in 2016.
Montana's still carries it.** So a Montana party served by e-mail with written
consent gets three days and a federal one does not. Reusing `frcp_6d` here would
silently drop three days from every consented electronic service. Asserted in the
suite as a direct disagreement between the two standards on the same method.

Read from **Rule 5(b)(2)** itself rather than assumed from the federal
numbering: (C) mailing, (D) leaving with the court clerk where the person has no
known address, (E) electronic means with written consent, (F) any other means
consented to in writing. (A) handing it to the person and (B) leaving it at an
office or dwelling are **not** in the list.

**Not an exclusivity rule** — no "only" or "exclusively", so no
`requires_exclusive`, checked deliberately against the Utah and Florida shape.
**Sequencing is `roll_then_add_then_roll`** on the rule's own words ("after the
period would otherwise expire").

**What it does not reach: service of the summons and complaint.** Rule 6(d) is
gated on service "made under Rule 5(b)(2)"; process goes out under Rule 4. **That
is a citation rather than a reading**, which is why the Montana answer row
carries no extension and needs no open-question note — contrast **Delaware**,
where Rule 6(e) says only "after being served" and the same question is still
open on this platform.

### 5.2 Rules 33, 34 and 36 — the OPPOSITE split from Delaware

All three were read in full. None was inferred from the other two.

- **33(b)(2) and 34(b)(2)(A):** "a defendant **MAY** serve … within 45 days
  after service of the summons and complaint" — an **election** between two
  limbs with two different triggers. Seeded as the 30-day limb, which reports
  EARLIER and is safe.
- **36(a)(3):** "a defendant **shall not be required to serve** answers or
  objections **before the expiration of 45 days**" — a **FLOOR**, seeded as a
  `resolve_periods: later_of`.

**Delaware is the mirror image**: election on 33 and 34, and **nothing at all**
on 36. Montana joins Mississippi, New Mexico, South Carolina and Hawai'i in
making admissions the mandatory one. Getting this backwards on a **self-executing**
rule would tell a Montana defendant a matter is still open fifteen days after it
was admitted.

### DISCLOSURE 4 — the Rule 36 row deliberately carries no service extension

The 30-day limb runs from service of the **request** (Rule 5 — Rule 6(d) reaches
it). The 45-day limb runs from service of the **summons and complaint** (Rule 4 —
it does not). This engine applies a service extension **per row, not per limb**,
so carrying it would add three days whenever the floor governs — which is exactly
the common case for a defendant served with requests early in the action — and
would report **LATE**. Omitting reports EARLY for a mail-served party whose
30-day limb governs. Safe direction taken, disclosed in the row.

Note that **Hawai'i's equivalent row does carry its extension.** Whether Haw. R.
Civ. P. 6(e) is gated on a service subsection the way Mont. R. Civ. P. 6(d)
expressly is was **not read here**, and that row is not changed on the strength
of this one. Filed as a question rather than acted on.

### DISCLOSURE 5 — the Rule 12(a)(4)(A) row carries no extension either

Its period runs from **notice of the court's action**, which is not stated to be
Rule 5 service of a paper by a party. Carrying three days the rule may not
authorise reports LATE; omitting reports EARLY. Safe direction taken.

### 5.3 A decision that is available and was not taken

Rule 6(b)(2) forbids the court to extend the time under Rules 50(b) and (d),
52(b), **59(b), (d) and (e)**, and 60(b) — no good cause, no excusable neglect.
That is an argument for setting the two Rule 59 rows' `trigger_document` guard to
**`refuse`** rather than `warn`.

**They are set to `warn`**, matching Delaware's identical entry-of-judgment
new-trial row and the platform's civil/appellate convention. Changing the
convention for two rows is a judgment call above this gate. It is recorded here
and in the row's own note so it is a decision rather than an oversight.

---

## 6. SCOPING DECISION, MINE, STATED SO IT CAN BE OVERRULED

**Seed DISTRICT COURT ONLY as jurisdiction `mt`, and say so in the label, the
coverage entry, the readme and every row's note.**

**The Montana Justice and City Court Rules of Civil Procedure, MCA Title 25
ch. 23, contain their own Rule 6.** Same number, same title of the same code,
different computation:

| | M.R.Civ.P. 6 (District Court) | Just. & City Ct. R. Civ. P. 6 |
|---|---|---|
| "Legal holiday" | defined in 6(a)(6), three limbs, one of them forward-only | **not defined at all** — nothing narrows § 1-1-216 |
| Clerk inaccessibility | 6(a)(3), a separate additional limb | **none** |
| Backward periods | 6(a)(5), expressly | **not addressed** |
| Hours | 6(a)(2), a full unit with its own rollover | **none** |
| Service extension | Rule 5(b)(2)(C),(D),(E),(F) — mail, clerk, consented electronic, other consented | **mail only** |
| Extension sequencing | "3 days are added **after the period would otherwise expire**" — roll, add, roll | "3 days **must be added to the prescribed period**" — add, roll once |

**The sequencing row alone moves real dates**, and this platform has already
measured that difference on FRCP vs CPLR: three days apart on a worked example,
with the federal order producing the **later** of the two.

**Also not read and not seeded:** the Justice and City Court answer, discovery
and new-trial periods (ch. 23); the **Montana Uniform District Court Rules**
(ch. 19), whose Rule 2 carries its own motion briefing schedule; and the
**Montana Rules of Appellate Procedure** (ch. 21). No appellate row is seeded, so
no Montana row is in the `refuse` trigger-document class.

---

## 7. Verdict

**PASS — seed District Court, with the five disclosures in §2, §3 and §5 written
into `JURISDICTION_COVERAGE.mt` before any row is loaded.** Every remaining
omission runs EARLY. The one interpretive question, Presidents' Day, is closed
outright for forward periods by Rule 6(a)(6)(C) and resolved in the safe
direction for backward ones.

**The single highest-value finding is the ABSENCE in §2.1.** Every other state
gated in the last week carries a short-period exclusion threshold and Montana
carries none; the seed would have been wrong on a third of its rows if the
neighbour's number had been assumed rather than the rule read.
