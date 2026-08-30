# Alabama — deadline-seed source-availability gate

**SEEDED 2026-08-30 -- 11 rules, calendar 2026. Loaded to LAW-PINNACLE-2026 and
live-verified 16/16.** All four "get this right" items in the verdict were
encoded and asserted: the FEDERAL after-expiry service order (asserted against
the date period-lengthening would have given), the ELEVEN-day exclusion, the
three-source holiday union, and Thanksgiving taken from the federal limb
because Sec. 1-3-8(a)(12) gives no date.

**Sec. 1-3-8(f)(1) IS NOT RESOLVED.** The office-may-stay-open provision, whose
direction is LATE, is disclosed in JURISDICTION_COVERAGE.al rather than modelled
-- it is discretionary, per-office and published nowhere machine-readable. This
gate said it should go to the bundled holiday question rather than be waved
through, and it is still there, now alongside the sharper Wisconsin form of the
same question: a statutory holiday list is not the same fact as whether the
courthouse was open.

**Run 2026-08-26. Verdict: PASS — the most recently amended rule of any state
gated, a self-contained holiday definition that does NOT depend on the statute
for its list, and the FIRST state seeded in a long run that uses the FEDERAL
after-expiry service order.**

Alabama (~5.1M) is the next unseeded state after South Carolina.

---

## 1. Sources — PASS, both official and free

| What | URL | Method |
|---|---|---|
| Ala. R. Civ. P. 6, 12, 33, 34, 36 | `judicial.alabama.gov/docs/library/rules/cv<N>.pdf` | **curl 200, native PDFs** |
| Ala. Code § 1-3-8 | `alison.legislature.state.al.us/code-of-alabama` → Title 1 → Ch. 3 → § 1-3-8 | browser (JS drill-down) |

The Alabama Judicial System publishes **each rule as its own official PDF**, and
they are real text PDFs (pypdf-extractable), not scans. The Legislature
publishes the Code on its own site.

**Two access notes.** The rules index at `/library/rules` is a **404**; the
working path is `/library/rulesofcourt` → `/library/CivilProcedure`, which then
links each rule's PDF. And the Code site is a JavaScript drill-down — Title →
Chapter → Section — so plain `curl` on a guessed section URL fails
(`legislature.state.al.us/aliswww/...` returned a connection error). A real
browser walks it fine.

**Currency is per-rule, printed on each PDF, and Rule 6 is startlingly fresh:**

| Rule | Amendment line, verbatim |
|---|---|
| **6** | `[Amended eff. 10-1-95; Amended eff.8-1-2004; Amended eff. 10-24-2008; Amended eff, 11-28-2012; **Amended 3-26-2026, effective 4-9-2026.**]` |
| 12 | `[Amended 10-14-76, eff. 1-16-77; … Amended 11-28-2012.]` |
| 33 | `[… Amended 11-4-2009, eff. 2-1-2010.]` |
| 34 | `[… Amended eff. 11-18-2009.]` |
| 36 | `[Amended eff. 10-1-95.]` |

**Rule 6 was amended effective 9 April 2026 — four months ago.** That is the
most recent rule text encountered in any gate, and it is a reminder that a
snapshot taken even a year ago would have been stale on the single most
load-bearing rule in the state.

## 2. Rule 6 — verbatim, and the holiday definition is SELF-CONTAINED

> **(a) Computing Time.** The following rules apply in computing any time period
> specified in these rules, in a court order, or in any statute that does not
> specify a method of computing time:
> **(1) Day of the Act, Event, or Default Excluded.** Exclude the day of the act,
> event, or default that begins the period.
> **(2) Exclusion from Brief Periods.** Exclude intermediate Saturdays, Sundays,
> and legal holidays **when the period is less than 11 days**.
> **(3) Last Day.** Include the last day of the period unless it is a Saturday,
> Sunday, or legal holiday, or — if the act to be done is filing a paper in court
> — **a day on which weather or other conditions make the clerk's office
> inaccessible**.
> **(4) "Legal Holiday" Defined.** As used in this rule and Rule 77(c), "legal
> holiday" includes:
> **(A)** the day set aside by statute for observing New Year's Day, Martin
> Luther King Jr.'s Birthday, President's Day, Memorial Day, **Juneteenth**,
> Independence Day, Labor Day, **Columbus Day**, Veterans' Day, Thanksgiving Day,
> or Christmas Day; **or**
> **(B)** any other day declared a holiday by the President or Congress **or as
> prescribed by § 1-3-8, Ala. Code 1975**.

**THE RULE NAMES ITS OWN ELEVEN DAYS.** This is a shape no seeded state has.
Everywhere else the rule either points at a statute (WA, MA, MO, WI, MN, TN) or
points at nothing (TX, AZ, KY). Alabama's rule **enumerates eleven holidays in
its own text** and uses the statute only for *the dates on which they are
observed* plus a catch-all in (B).

That matters because **§ 1-3-8 contains days the rule does NOT name** — see §4.
The (A) list is the primary source and (B) is the residue, not the other way
round.

**The Committee Comment states the union expressly:**

> This rule is virtually identical to Federal Rule 6. **The net effect is the
> inclusion of all holidays whether state or federal** within the definition of a
> legal holiday.
>
> Under § 1-1-4, Code of Alabama, **Saturdays are not treated as holidays. This
> Rule will include Saturdays** and hence § 1-1-4, Code of Alabama, will not be
> applicable in that respect.

So Alabama, like South Carolina, needs a **state ∪ federal** union — and here the
rule says so itself rather than leaving it to be inferred. The second paragraph
is also worth keeping: **the rule expressly overrides a statute** on Saturdays.

**Other fields:**
- **Short-period exclusion at ELEVEN days** — "less than 11 days", so the field
  is **11**, matching Tennessee, Arizona and Wisconsin, and not the 7 of NJ, NC,
  WA, MA, MO and SC, nor Minnesota's absence.
- **A weather/inaccessibility limb** in (a)(3), and — as in Minnesota — it is
  **additional to** the Saturday/Sunday/holiday rollover rather than a
  replacement, so omitting it reports **EARLY**. Safe, disclosable.
- **No backward provision.** Backward stays blank.

## 3. THE SERVICE ORDER IS FEDERAL — and this is the trap

> **(d) Additional Time After Certain Kinds of Service.** When a party may or
> must act within a specified time after being served and service is made under
> Rule 5(b)(2)(C) (by mail) or (E) (through the court's electronic-filing
> system), **3 days are added AFTER THE PERIOD WOULD OTHERWISE EXPIRE under Rule
> 6(a)**.

**"After the period would otherwise expire" is the FEDERAL after-expiry
ordering** (`roll_then_add_then_roll`) — roll the base period first, then add
three, then roll again. **Nearly every state seeded in this run is
period-lengthening** (NJ, NC, WA, NY, VA, MA, MO, MN, and SC): they add the days
*to the prescribed period* and roll once at the end.

The two orders give different dates whenever the unrolled last day falls on a
weekend or holiday. Copying the recent neighbours' sequence into Alabama would
be wrong, and the error is not consistently in the safe direction — it depends
on where the base period lands. **Read from Rule 6(d)'s own words, which say it
plainly.**

**Electronic-filing-system service DOES get the three days**, enumerated
alongside mail in the rule itself. That is the Massachusetts pattern — the time
rule granting it directly — and the seventh distinct answer on electronic
service across the states gated:

| State | Electronic service | Order |
|---|---|---|
| Massachusetts | +3, in the time rule | period-lengthening |
| Tennessee | service rule **deems** it mail → +3 | period-lengthening |
| Missouri | +0, **trigger date moves** | n/a |
| Maryland | +0, expressly negated | n/a |
| Wisconsin | +1 if 5 p.m.–midnight | period-lengthening |
| Minnesota | +1 if after 5 p.m. (negative condition) | period-lengthening |
| South Carolina | **unresolved** on sources read | period-lengthening |
| **Alabama** | **+3, in the time rule** | **FEDERAL after-expiry** |

## 4. § 1-3-8 — the statute, and why the rule's own list matters

**Ala. Code § 1-3-8(a)**, verbatim:

> (1) New Year's Day, January 1. (2) **Martin Luther King, Jr.'s birthday and
> Robert E. Lee's birthday**, the third Monday in January. (3) **George
> Washington's birthday and Thomas Jefferson's birthday**, the third Monday in
> February. (4) **Confederate Memorial Day, the fourth Monday in April.**
> (5) Memorial Day, the last Monday in May. (6) **Jefferson Davis' birthday, the
> first Monday in June.** (7) Juneteenth, June 19. (8) The Fourth of July, July 4.
> (9) Labor Day, the first Monday in September. (10) **Columbus Day, Fraternal
> Day, and American Indian Heritage Day**, the second Monday in October.
> (11) Veterans' Day, November 11. (12) **Thanksgiving Day, as designated by the
> Governor.** (13) Christmas Day, December 25.
>
> **(b) If any holiday falls on Sunday, the following day is the holiday. If any
> holiday falls on Saturday, the preceding day is the holiday.**

Findings that must not be got wrong:

- **§ 1-3-8 has THIRTEEN entries; Rule 6(a)(4)(A) names ELEVEN.** The statute
  adds **Confederate Memorial Day (fourth Monday in April)** and **Jefferson
  Davis' birthday (first Monday in June)** — neither named in the rule. But Rule
  6(a)(4)(B) sweeps in "any other day … as prescribed by § 1-3-8", so **both are
  legal holidays for deadline purposes anyway**. The two-limb structure means
  the answer is the union, not the rule's shorter list. Encoding only the eleven
  would compute **EARLY** on those two days.
- **THANKSGIVING HAS NO STATUTORY DATE.** § 1-3-8(a)(12) says "Thanksgiving Day,
  **as designated by the Governor**" — so unlike every other state seeded, the
  date is not derivable from the statute. It is the fourth Thursday in November
  in practice (and reaches Alabama independently through Rule 6(a)(4)(A)'s named
  list and (B)'s President/Congress limb, since it is a federal holiday), but a
  generator cannot derive it from § 1-3-8 alone. **This needs recording, not
  assuming.**
- **The shift is BOTH WAYS and unconditional** — § 1-3-8(b) applies to "any
  holiday", with no enumerated subset (contrast Minnesota's five named days) and
  no "for the purposes aforesaid" caveat (contrast South Carolina's § 53-5-30).
  It is the cleanest shift provision encountered. **It will produce year-boundary
  spills**, so the generator must compute a wider span than it emits — the thing
  the Minnesota generator's own assertion caught.
- **A COUNTY-SCOPED HOLIDAY:** § 1-3-8(e)(1) — **"Mardi Gras shall be deemed a
  holiday in Baldwin and Mobile Counties, and all state offices shall be closed
  in those counties on Mardi Gras."** Same shape as Massachusetts' Suffolk
  County. A jurisdiction+year calendar cannot express it; omitting runs **EARLY**
  in those two counties and is correct everywhere else, so it is the established
  safe treatment plus a coverage disclosure. Note Mardi Gras is a movable feast
  tied to Easter, so it is derivable but not trivially.
- **§ 1-3-8(f)(1) lets a state office stay OPEN on a state holiday** on 60 days'
  written notice. Discretionary and unknowable; if a court did so and the engine
  rolls anyway, that runs **LATE**. Small, but it is the one item here whose
  direction is not obviously safe and it should go to the bundled holiday
  question rather than be waved through.

## 5. Periods, read verbatim

- **Rule 12(a)** — answer **30 days** after service of the summons and complaint
  (except service by publication, where a different time is prescribed);
  cross-claim answer **30 days**; reply to a counterclaim **30 days** after
  service of the answer, or **30 days** after service of the order if a reply is
  ordered. Motion limbs: **10 days** after **notice of the court's action** if
  denied/postponed, **10 days** after **service** of the more definite
  statement. (Note the same notice-vs-service split Missouri and Massachusetts
  have, which decides whether the extension applies to each limb.)
- **Rules 33, 34 and 36** — all **30 days**, all with a **45-day defendant
  floor** running from service of the summons and complaint. **No outlier**,
  unlike Missouri's 45/45/60, and every floor runs from a **caller-supplied**
  date, so Alabama does not hit the Maryland chained-floor gap. Rule 36 is
  self-executing: *"The matter is admitted unless, within thirty (30) days…"*
- **Rule 6(c)** — motion and notice of hearing at least **5 days** before the
  hearing; opposing affidavit at least **1 day** before. Both far under 11, so
  they are the rows that would actually exercise the exclusion.
- **Rule 6(dc)** — a district-court carve-out: **Rule 6(a)(2) does not apply** to
  periods in **unlawful-detainer or eviction** actions. A domain-scoped
  disapplication of the exclusion, which no seeded jurisdiction has. Not
  relevant to a civil-litigation batch, but it must not be lost if landlord/
  tenant is ever seeded.

## 6. Verdict

**PASS.** Sources free and official from both branches, native text PDFs, real
per-rule currency, and a rule amended four months ago.

**Nothing is blocked.** Four things to get right during seeding, each of which
would be wrong if inherited from a neighbour:

1. **The service order is FEDERAL after-expiry**, not period-lengthening —
   against the run of the last eight states.
2. **The exclusion is ELEVEN days**, not seven.
3. **The holiday answer is the union of the rule's own eleven, § 1-3-8's
   thirteen, and the federal list** — the rule names its own days, which no other
   seeded state does, and the statute adds two the rule omits.
4. **Thanksgiving has no statutory date** ("as designated by the Governor") and
   must be sourced from the federal limb rather than derived from § 1-3-8.

Plus two disclosures: **Mardi Gras in Baldwin and Mobile Counties** (EARLY,
established treatment), and the weather/inaccessibility limb (EARLY). And one
item for the bundled holiday question: **§ 1-3-8(f)(1)'s office-may-stay-open
provision, whose direction is LATE.**
