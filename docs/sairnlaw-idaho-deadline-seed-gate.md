# Idaho — deadline-seed source-availability gate

**Run 2026-08-30. Verdict: PASS, and SEEDED the same day — 11 rules, calendar
2026 with eleven dates. Loaded to `LAW-PINNACLE-2026` and live-verified 30/30;
the licence now holds 32 jurisdictions and 363 rules, and
`tools/sairn_load_state_check.py` reports 363/363 and 139/139 with 0 missing,
0 stale, 0 extra.**

**The finding is that Idaho publishes three holiday lists that do not agree, and
the one the rule points at is the one nobody publishes as a calendar.**
I.R.C.P. 2.2 says "legal holiday" and never defines it. Idaho Code § 73-108 is
the referent. It has **no Juneteenth**, which the Secretary of State's published
State Holidays page does have; and it makes **Friday 3 July 2026 a holiday by
mandatory statute**, which that same page does not show. A calendar copied from
the executive branch would be wrong in both directions at once.

Idaho (~2.0M) was chosen as the largest unseeded state without an existing gate
document, after New Mexico closed earlier the same day.

---

## 1. Sources — PASS

| What | URL | Result |
|---|---|---|
| **Idaho Rules of Civil Procedure, complete** | `isc.idaho.gov/rules-procedure/ircp` | **200, 1,445,212 B, 104 rules, server-rendered HTML** |
| Idaho Code § 73-108 (holidays enumerated) | `legislature.idaho.gov/statutesrules/idstat/Title73/T73CH1/SECT73-108/` | 200 |
| Idaho Code § 73-109 (computation of time) | `…/SECT73-109/` | 200 |
| Idaho Code § 67-5302 (definitions, incl. "Holiday") | `…/Title67/T67CH53/SECT67-5302/` | 200 |
| Secretary of State, State Holidays | `sos.idaho.gov/state-holidays/` | 200 |
| Idaho Supreme Court release | `isc.idaho.gov/news-article/idaho-courts-to-be-open-july-2` | 200 |
| `isc.idaho.gov/rules/`, `isc.idaho.gov/ircp/` | — | **404** |
| `isc.idaho.gov/printpdf/2281` (from search results) | — | **404** |

**THE SITE IS A SINGLE-PAGE APP AND THE RULES ARE STILL THERE.** `isc.idaho.gov`
is a Nuxt application; its obvious rule paths 404 and the homepage carries
nothing but `/_nuxt/*.js`. But `/rules-procedure/ircp` returns the **entire
I.R.C.P. server-rendered** — 104 rules in 1.4 MB of HTML on a plain `curl`, no
gate, no sign-in, no click-through. Completeness was checked rather than assumed:
104 `Idaho Rules of Civil Procedure Rule N.` headings extracted, and every rule
this seed needs found among them.

That is the third JavaScript-fronted official publisher in three states, and the
third different answer. **Colorado is a wall** (a CAPTCHA behind a
terms-acceptance). **New Mexico was an obstacle** (one browser pass produced a
plain PDF URL). **Idaho is not even an obstacle** — the server already renders
everything; only the guessed URLs were wrong.

### Currency

Idaho **restyled its civil rules in 2016**, and effective dates cluster
accordingly. Each rule carries its own parenthetical.

| Rule | Note | effective_from |
|---|---|---|
| 2.2 (computation) | `Adopted March 1, 2016, effective July 1, 2016; amended September 9, 2016` | 2016-09-09 |
| 12 (pleadings) | `… amended April 25, 2018, effective July 1, 2018` | **2018-07-01** |
| 33, 34, 36, 56, 59 | `Adopted March 1, 2016, effective July 1, 2016` | 2016-07-01 |
| 55 (default) | `… amended September 9, 2016` | 2016-09-09 |

**THE RULE NUMBER IS ITSELF A CURRENCY TRAP.** The 2016 restyling moved
computation of time **from Rule 6 to Rule 2.2**. A citation to "Idaho Rule 6" has
pointed at nothing since 1 July 2016, and Rule 6 is now an unrelated rule. Every
other seeded jurisdiction keeps computation at 6 or in a statute; Idaho is the
only one that moved it.

---

## 2. Computation — no exclusion at all, and no direction rule

**I.R.C.P. 2.2(a)(1)**: *"(B) **count every day, including intermediate
Saturdays, Sundays, and legal holidays**; and (C) include the last day of the
period, but if the last day is a Saturday, Sunday, or legal holiday, the period
continues to run until the end of the next day that is not a Saturday, Sunday, or
legal holiday."*

**No short-period exclusion.** Idaho took the 2009 federal restyling wholesale
and joins **Minnesota, Utah, Nevada and Kansas** in having none at all.

**It matters more here than the tally suggests.** Four seeded Idaho rows are
**fourteen days** — the two Rule 12(a)(2) rows and both Rule 59 post-judgment
rows. Under Alabama's or Wisconsin's threshold of 11 they would still count
straight through, so a careless copy from those states would produce the right
answer for the wrong reason. Under **Arkansas's 14** they would be excluded, and
the answer would be wrong. The test asserts the field is `undefined`, not merely
small.

### NO DIRECTION RULE, SO NO BACKWARD ROW IS SEEDED

2.2(a)(1)(C) rolls to *"the **next** day"* and says nothing about a period
measured **before** an event. That is the **Mississippi** shape, not the New
Mexico one — N.M. Rule 1-006(A)(6) settles direction in terms, and Mississippi's
silence plus an under-inclusive calendar is exactly why every Mississippi
backward row was dropped this morning.

**Idaho has backward rows worth having, and none is seeded:**

- **Rule 55(a)(1)** — three days' written notice of the application for **entry of
  default**, if the party has appeared. Unusual: most states require notice only
  before default **judgment**.
- **Rule 55(b)(2)** — written notice at least three days before the
  default-judgment **hearing**.
- **Rule 56(b)(2)** — motion and supporting documents served at least **28** days
  before the hearing, answering brief at least **14**, reply at least **7**.
- **Rule 56(b)(1)** — the motion itself filed at least **90 days before trial**,
  or within 7 days of the order setting trial, whichever is later.

The reason they are omitted is §4: one annually-recurring date is genuinely
contested, and on a backward count an omitted holiday leaves the date **closer to
the trigger** — later than the rule allows.

---

## 3. Service — one sentence, and four words fewer than Mississippi

**I.R.C.P. 2.2(c)**, verbatim and complete:

> **Additional Time After Service by Mail.** When a party may or must act within a
> specified time after service and service is made **by mail, 3 days are added to
> the specified time**.

Three things.

- **"ADDED TO THE SPECIFIED TIME"** → period-lengthening, not the federal
  after-expiry order.
- **MAIL AND NOTHING ELSE — and here that is not a leftover.** Mississippi's
  mail-only rule dates from 1982 and simply was never widened. **Idaho wrote this
  sentence from scratch in 2016**, when electronic service was already routine
  across the profession, and still reached only mail. E-mail, the iCourt e-filing
  system, facsimile and hand delivery all get zero.
- **IT SAYS "AFTER SERVICE", NOT "AFTER SERVICE OF A NOTICE OR OTHER PAPER".**

### THE FOUR WORDS, AND THE ROW THEY DECIDE

Both Idaho and Mississippi run the post-Rule-12-motion period from **notice of
the court's action**:

| | rule text on the extension | that row takes |
|---|---|---|
| Mississippi | 6(e): "after **the service of a notice** or other paper" | **+3 on mailed notice** |
| Idaho | 2.2(c): "after **service**" | **nothing** |

Copying Mississippi's treatment into Idaho reports **three days late**. And
Idaho's own sibling row — Rule 12(a)(2)(B), which runs from *"after the more
definite statement **is served**"* — **does** take the three days. Same rule, same
paragraph, same fourteen days, opposite answers, decided by which verb the
subparagraph uses. Both are seeded separately for that reason and the pair is
asserted live.

**No row triggered by service of process carries the extension.** There is no
express Rule 4 carve-out — the Wisconsin and New Mexico position, resolved the
same way. I.R.C.P. 5(a)(1)(B) reaches *"a pleading filed after the original
complaint"*; original process is Rule 4. Withholding reports EARLY.

---

## 4. The calendar — three lists, and the statute is the one that governs

### The chain, because the rule does not state it

I.R.C.P. 2.2 says "legal holiday" and stops. **Nothing in the Idaho Rules of Civil
Procedure or the Idaho Appellate Rules defines it** — checked, not assumed.
**Idaho Code § 73-108** ("Holidays enumerated") is the referent, and **§
67-5302(15)(a)** confirms the chain in terms: *"'Holiday' means any day so
designated by the president of the United States or the governor of this state
for a public fast, thanksgiving or holiday. **Holidays are enumerated in section
73-108, Idaho Code.**"* § 73-109 independently uses the same referent for
statutory computation.

### List 1 — Idaho Code § 73-108, which governs

> Every Sunday; January 1; Third Monday in January (Martin Luther King,
> Jr.-Idaho Human Rights Day); Third Monday in February (Washington's Birthday);
> Last Monday in May; July 4; First Monday in September; **Second Monday in
> October (Columbus Day)**; November 11; Fourth Thursday in November; December
> 25; **every day appointed by the President of the United States, or by the
> governor of this state**, for a public fast, thanksgiving, or holiday.
>
> **Any legal holiday that falls on Saturday, the preceding Friday shall be a
> holiday** and any legal holiday enumerated herein other than Sunday that falls
> on Sunday, the following Monday shall be a holiday.

Both shifts are **mandatory statute**, not a published observance — unlike
Mississippi, where § 25-1-99 makes the Friday-before permissive per county.

### List 2 — the Secretary of State's State Holidays page

Carries **Juneteenth, Friday 19 June 2026**, which § 73-108 does not enumerate.
Prints **Independence Day as Saturday 4 July** with nothing on the Friday — i.e.
it does **not** apply § 73-108's mandatory Saturday shift.

### List 3 — what the courts actually do

The Idaho Supreme Court published a 2026 release headed **"Idaho Courts to be
Open July 2 & 6"**, keeping courts open as essential services on days other parts
of state government close. Meanwhile at least one county trial court publishes a
2026 schedule that **does** close for Juneteenth.

**Court closure, state-employee holiday and legal holiday are three different
sets in Idaho, and only the third governs Rule 2.2.**

### The eleven dates seeded, and the two that carry the finding

| Date | Day | Source |
|---|---|---|
| 2026-01-01 | Thu | § 73-108, January 1 |
| 2026-01-19 | Mon | 3rd Monday January — named for **both** MLK and Idaho Human Rights Day in the statute |
| 2026-02-16 | Mon | 3rd Monday February — the statute says **Washington's Birthday**; the SOS page says Presidents' Day |
| 2026-05-25 | Mon | Last Monday May |
| **2026-07-03** | **Fri** | **Derived from the mandatory Saturday shift. The SOS list does not show it.** |
| 2026-07-04 | Sat | § 73-108, July 4 — carried because the shift adds the Friday without unmaking the Saturday |
| 2026-09-07 | Mon | 1st Monday September |
| 2026-10-12 | Mon | 2nd Monday October — **Columbus Day is enumerated in Idaho**, unlike Oregon |
| 2026-11-11 | Wed | November 11 |
| 2026-11-26 | Thu | 4th Thursday November — **the day after is not a statutory holiday here**, unlike Kansas, South Carolina, Wisconsin and Maryland |
| 2026-12-25 | Fri | December 25 |

**JUNETEENTH IS DELIBERATELY ABSENT, AND IT IS THE ONE CONTESTED DATE.** Its only
route in is § 73-108's open limb for days *"appointed by the President … or by the
governor"* — a proclamation this engine cannot read. Omitting it means a forward
deadline landing on 19 June is reported as due that day when the true one may roll
to the 22nd: **earlier, and safe**. Adding it would roll a deadline off a possibly
fully-countable day: **later, and not**. The same reasoning omits every other
ad-hoc presidential or gubernatorial day.

**"Every Sunday" is also a statutory holiday** and is deliberately not enumerated
as 52 dates — Rule 2.2(a)(1)(C) already excludes Sundays by name.

**The Sunday→Monday limb is mandatory and dormant in 2026**: no § 73-108 holiday
falls on a Sunday this year.

**2027 is refused rather than derived, and here the temptation is the opposite of
New Mexico's.** § 73-108 is a rule-based list that *would* generate 2027
mechanically — and that is exactly why it is refused. Generating a year would
hide both open questions (the ad-hoc limb and Juneteenth) behind a confident
answer.

**Also not modelled, and always EARLY:** Rule 2.2(a)(2) extends the time for
**filing** whenever *"the clerk's office is inaccessible"* — per-court, unknowable
in advance, and a **separate limb** from the holiday list rather than part of it.

---

## 5. No defendant floor anywhere — a first

| Rule | Text | Shape |
|---|---|---|
| 33(b)(2) | "within 30 days after being served with the interrogatories" | flat 30 |
| 34(b)(2)(A) | "must respond in writing within 30 days after being served" | flat 30 |
| 36(a)(4) | "A matter is admitted unless, within 30 days after being served …" | flat 30, **self-executing** |

**The string "45 days" does not appear anywhere in the Idaho Rules of Civil
Procedure.** Not a floor, not an election, nothing.

That makes Idaho **the first seeded state outside the federal seed itself where
no discovery row is a `resolve_periods`**, and the reason is an absence rather
than a reading. The neighbours all have something: Arkansas a mandatory floor on
all three, Kansas an election on all three, Mississippi and New Mexico two
elections and one floor, North Carolina 45/45/60, Massachusetts none/45/45.

**The stakes are concentrated in Rule 36.** It is self-executing and Rule 36(b)
makes an admission conclusively established unless the court permits withdrawal.
A row carrying a 45-day floor read across from any neighbour would tell an Idaho
defendant the matter is not yet admitted **when it already is** — the worst
failure this engine can produce.

---

## 6. What was seeded, and what was deliberately left out

**Eleven rules, every one forward.** Answer to the summons and complaint (21);
answer to a counterclaim **or** crossclaim (21, one rule for both); reply after an
order to reply (21); responsive pleading after a Rule 12 motion is denied (14,
from **notice**); responsive pleading after a more definite statement (14, from
**service**); interrogatory answers (30); production response (30); admissions
(30); motion for a new trial (14 from entry); motion to alter or amend (14 from
entry); opposing affidavits on a new-trial motion (14 from service).

**Rule 2.2(b) is unusually generous and then unusually strict.** (b)(2) lets the
**parties** extend time by written stipulation, filed before or after expiry —
broader than most states. (b)(3) then freezes six rules absolutely: *"A court must
not extend the time to act under Rules 50(b), 52(b), 59(b), (d), and (e), and
60(b)."* Rule 59(c)'s opposing-affidavit period is **not** on that list and grants
its own extension of up to 21 further days, which is why it is seeded beside the
two frozen rows rather than folded into them.

**One quote is left unrepaired on purpose.** Rule 12(a)(1)(C) as published reads
*"a party must serve a reply to an answer **21 days after** being served with an
order to reply"*, where its federal source reads *"within 21 days"*. Read
literally it names a day rather than a period. The seed records the quote exactly
as published and says so in the row's note, so a reader can see the discrepancy
rather than trust a silent correction.

**Deliberately not seeded, each for a stated reason:**

- **Every backward row** — Rules 55(a)(1), 55(b)(2), 56(b)(1) and 56(b)(2); see
  §2.
- **Rule 34's production itself** — a date set by the parties' own papers.
- **Rule 12(a)(1)'s "unless another time is specified by rule or statute"** and
  12(a)(2)'s "unless the court sets a different time" — caller-supplied facts,
  recorded in each row's note.
- **The Idaho Appellate Rules' appeal clock**, which the Rule 59 rows toll. A
  separate rule set, out of this seed's domain.

---

## 7. Verdict

**PASS, and seeded.** The complete current rules are free, official, dated and
server-rendered on a plain request. The holiday referent is a statute, reached
through a chain the Idaho Code states explicitly, and the calendar is derived from
its own words with every date checked by weekday. Every omission runs EARLY, and
the one direction that could run LATE — a backward count over the contested date —
is closed by not seeding a backward row at all.

**The finding to carry forward is that Idaho's three lists disagree in both
directions.** A calendar taken from the Secretary of State adds a day the statute
does not have and drops a day the statute requires, and each error points the
opposite way.

### Live verification, 30/30 on `LAW-PINNACLE-2026`

**Pass 1** — all 11 rows return a real date.

**Pass 2** — the arithmetic, built around the calendar disagreements and the
four-word divergence:

- **Every day counts.** A 21-day period from Monday 16 November 2026 returns
  **2026-12-07**, having counted Thanksgiving as an ordinary intermediate day.
- **The statutory Saturday shift bites, and it moves the answer three days.** A
  21-day period from 12 June lands on Friday 3 July — a holiday only because 4
  July is a Saturday — and rolls through the weekend to **Monday 2026-07-06**. A
  calendar copied from the Secretary of State's list would have answered 3 July.
- **Juneteenth does not roll.** A period landing on Friday 19 June returns
  **2026-06-19** unchanged. That is the contested date, omitted on purpose.
- **Columbus Day does roll** (→ **2026-10-13**), and **the day after Thanksgiving
  does not** (→ **2026-11-27**). Two negative probes a copied calendar fails in
  opposite directions.
- **The four words, proved across two live jurisdictions on the same trigger
  name.** Idaho's `notice_of_court_action_denying_or_postponing_motion` returns
  **2026-11-30 with and without `service_method: mail`**. Mississippi's returns
  **2026-11-26** plain and **2026-11-30** mailed. Same trigger, same platform,
  opposite answers — because Miss. R. Civ. P. 6(e) has a notice limb and
  I.R.C.P. 2.2(c) does not.
- **Mail only.** Mailed interrogatories → **2026-12-21** (base 16 December, plus
  three calendar days to Saturday the 19th, rolled to Monday the 21st).
  Electronic → **2026-12-16**. Facsimile → **2026-12-16**, while New Mexico's
  facsimile limb still returns **2026-11-12** on its own facts, so Idaho's
  narrower list did not leak.
- **Process vs paper.** A mailed summons adds nothing (**2026-12-07**); a mailed
  counterclaim pleading takes the three days (**2026-12-10**).
- **The frozen pair.** Rules 59(b) and 59(e) return **2026-11-30** even with
  `mail` supplied; Rule 59(c), the one Rule 2.2(b)(3) does not freeze and the only
  one running from service, returns **2026-12-03**.
- **The absent floor, proved against a neighbour.** Idaho's admissions row on a
  request served 1 October returns **2026-11-02**; New Mexico's later-of on
  comparable facts returns **2026-11-04**. The fifteen days Idaho does not give
  are visible in the difference.
- **Refusals.** 2027 → `NOT_PROVISIONED`. Rule 12 on 2018-06-01 →
  `NO_RULE_IN_FORCE`. Rule 33 on 2016-06-01 → `NO_RULE_IN_FORCE`.
- The coverage disclosure comes back over the wire with `complete:false`,
  `direction:"early"`, naming § 73-108, Juneteenth and the backward-row decision.
