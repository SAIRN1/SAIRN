# South Carolina — deadline-seed source-availability gate

**Run 2026-08-26. Verdict: PASS on sources — but with the FIRST holiday
definition requiring a STATE-plus-FEDERAL union, and one unresolved question
about electronic service that must ship as a safe default, not a guess.**

South Carolina (~5.4M) is the next unseeded state after Minnesota.

---

## 1. Sources — PASS, both free on plain `curl`

| What | URL | Method |
|---|---|---|
| SCRCP Rule 6 | `sccourts.org/resources/judicial-community/court-rules/civil/rule-6/` | **curl 200** |
| S.C. Code §§ 53-5-10, 53-5-30 | `scstatehouse.gov/code/t53c005.php` | **curl 200** |
| 2022 e-mail service order | `sccourts.org/whatsnew/displaywhatsnew.cfm?indexID=2698` | **curl 200** |

Both the Judicial Branch and the Legislature publish free, officially, with no
paywall, challenge or terms gate. The Rules carry per-rule drafting Notes and
dated amendment notes (e.g. "Note to 1986 Amendment").

**One access trap worth recording.** The obvious-looking URL
`sccourts.org/courtReg/displayRule.cfm?ruleID=6.0&ruleType=RCP` returns **HTTP
200 and 458 KB** — but the body is a **navigation index of every rule in every
body of rules**, not Rule 6, and it contains none of the words "Computation",
"intermediate Saturdays" or "shall not be included". A 200 with a large payload
is not proof you fetched the thing you asked for. The working path is
`/resources/judicial-community/court-rules/civil/rule-6/`.

## 2. A CORRECTION ON THE RECORD, before anything is built on it

A web search returned, as Rule 6(e):

> "Service by e-mail will be treated the same as service by U.S. Mail for
> purposes of determining the time to respond; therefore, five days shall be
> added to the prescribed period to respond from the date of transmission…"

**That sentence is not in Rule 6(e).** The actual rule, read verbatim from
sccourts.org, is:

> **(e) Additional Time After Service by Mail or Upon Statutory Agent.**
> Whenever a party has the right or is required to do some act or take some
> proceedings within a prescribed period after the service of a notice or other
> paper upon him and the notice or paper is served upon him **by mail or upon a
> person designated by statute to accept service, five days shall be added** to
> the prescribed period.

No e-mail language at all. I then read the **2022 Supreme Court order "RE:
Service by E-Mail in the Trial Courts"** (Appellate Case No. 2022-000029, dated
6 May 2022, signed by all five justices) end to end. It has paragraphs (a)
through (f) — purpose, e-mail as an additional method, service on lawyers,
service by and on self-represented litigants, requirements, and proof of service
— **and no time-extension provision whatsoever.**

**So on the two sources I actually read, whether South Carolina's five-day mail
extension reaches e-mail service is UNRESOLVED.** It may well live in a later
order or amendment I did not find. What I will not do is assert it from a search
summary.

**Direction, which decides the default:** if e-mail *does* collect the five days
and the engine omits them, the computed date is **EARLY** — safe. If it does
*not* and the engine adds them, the date is **LATE** — the direction that misses
a filing. **So the safe default is to extend for mail only and disclose the open
question**, and that is what a seed must do until someone resolves it.

This is the Tennessee lesson in a third form. There, a time rule reading
"by mail" was *widened* by a deeming provision in the service rule. Here a
search result claims the same widening, and the primary sources do not support
it. **Same instinct — check the service materials — opposite outcome.**

## 3. Rule 6(a) — verbatim, and the first STATE-plus-FEDERAL union

> **(a) Computation.** In computing any period of time prescribed or allowed by
> these rules, by order of court, or by any applicable statute, the day of the
> act, event, or default after which the designated period of time begins to run
> is not to be included. The last day of the period so computed is to be
> included, unless it is a Saturday, Sunday **or a State or Federal holiday**, in
> which event the period runs until the end of the next day which is neither a
> Saturday, Sunday nor such holiday. **When the period of time prescribed or
> allowed is less than seven days**, intermediate Saturdays, Sundays and holidays
> shall be excluded in the computation. **A half holiday shall be considered as
> other days and not as a holiday.**

Four fields fall out, and one of them is new:

- **THE HOLIDAY BASIS IS A UNION OF THE STATE LIST AND THE FEDERAL LIST.** "a
  State **or** Federal holiday". Every jurisdiction seeded so far keys on one
  list, or on two *state* lists (Wisconsin's 230.35(4)(a) ∪ 995.20). **South
  Carolina is the first to require the federal list as a co-equal source**, and
  it matters concretely: **Juneteenth is a federal holiday and is NOT in S.C.
  Code § 53-5-10**, and neither is **Columbus Day**. Encoding only the state
  list would miss both and compute **EARLY**; that is safe but wrong, and the
  union is not optional.
- **Short-period exclusion at seven** — "less than seven days", so the field is
  **7**, matching NJ, NC, WA, MA, MO and WV appellate, and not TN/AZ/WI's 11 or
  Minnesota's absence.
- **"A half holiday shall be considered as other days and not as a holiday"** —
  an express carve-out with no analogue in any seeded state. Nothing in
  § 53-5-10 is currently a half holiday, so it is inert today, but it must not
  be quietly dropped: it is the rule pre-emptively refusing a category.
- **No backward provision.** Rule 6(a) addresses only a period that "begins to
  run" after an act. Backward stays blank, like NJ, NC, WA, MA, MO and WI.

## 4. FIVE days for mail — and the rule says why

Rule 6(e) adds **five** days, not three. The drafting Note is explicit:

> This Rule 6(e) is the same as the Federal Rule except that **the additional
> time to take an act after service is by mail is increased from 3 to 5 days.**

**Every other seeded state adds three** (except California's and New York's
per-method tables). A three-day extension copied from a neighbour would compute
**two days EARLY** on every mailed South Carolina period. It also reaches
**service upon a statutory agent**, which no other seeded rule does.

Sequence: "five days shall be added to the prescribed period" → period-
lengthening (`add_to_period_then_roll`), like NJ, NC, WA, NY, VA, MA, MO and MN.

## 5. The holiday list — long, distinctive, and shifted both ways with a caveat

**S.C. Code § 53-5-10**, verbatim:

> The first day of January—New Year's Day, the third Monday of January—Martin
> Luther King, Jr. Day, the third Monday in February—George Washington's
> birthday/President's Day, **the tenth day of May—Confederate Memorial Day**,
> the last Monday of May—National Memorial Day, the fourth day of July—
> Independence Day, the first Monday in September—Labor Day, the eleventh day of
> November—Veterans Day, **National Thanksgiving Day and the day after**, and
> **the twenty-fourth, twenty-fifth, and twenty-sixth days of December** in each
> year are legal holidays.

Distinctive items, none of which appears in any seeded state:

- **Confederate Memorial Day, 10 May** — a fixed-date state holiday.
- **The day after Thanksgiving**, in the statute itself — where Minnesota leaves
  it to a branch option and Virginia derives it separately.
- **A THREE-DAY Christmas block: 24, 25 and 26 December.** No other seeded
  jurisdiction has three consecutive statutory Christmas days.

**§ 53-5-30** supplies the shift, both ways:

> Whenever any of the legal holidays mentioned in Section 53-5-10 shall fall upon
> Sunday the Monday next following shall be deemed a public holiday and whenever
> any of the holidays mentioned in such section shall fall upon Saturday the
> Friday next preceding shall be deemed a public holiday **for all of the
> purposes aforesaid**.

**Two caveats that must not be glossed:**

1. **"for all of the purposes aforesaid"** — § 53-5-30 is captioned "…effect on
   presentment of bills, notes, and checks", and its second sentence is entirely
   about negotiable instruments. Whether "the purposes aforesaid" reaches **court
   deadlines** is genuinely arguable on the text. This is a smaller cousin of the
   Maryland problem, where Rule 1-202(l) cites the holiday *list* but not the
   *shift*.
2. **§ 53-5-30 shifts only "the holidays mentioned in Section 53-5-10"** — i.e.
   the **state** list. The **federal** holidays that Rule 6(a) independently
   counts have their own observance rules (5 U.S.C. § 6103). So a South Carolina
   calendar may need **two different shift rules for two halves of one union**,
   which no seeded generator does.

Both are questions for the same lawyer's read, and both belong with the bundled
holiday question rather than as new categories.

## 6. Other periods read

- **Rule 6(d)** — a written motion and notice of hearing served **not later than
  ten days** before the hearing; opposing affidavits **not later than two days**
  before. **The two-day period is under seven**, so it is the row that would
  actually exercise the exclusion, and the natural first row to seed for that
  reason.
- **Rule 6(b)** names the rules whose time may not be extended — 50(b), 52(b),
  59, 60(b) — plus: **"The time for filing notice of intent to appeal is
  jurisdictional and may not be extended by consent or order."** A ready-made
  list of rows that must never carry an enlargement note.

**Not read:** the answer period (Rule 12) and the discovery response periods
(Rules 33, 34, 36). They are on the same host and the same URL pattern, so this
is effort remaining, not a source problem.

## 7. Verdict

**PASS on sources.** Free, official, `curl`-reachable from both the Judicial
Branch and the Legislature, with drafting and amendment notes.

**Three things to settle during seeding, none blocking:**

1. **Build the state ∪ federal holiday union** — the first time this is needed.
   Missing Juneteenth and Columbus Day would compute EARLY.
2. **Extend for mail only, at FIVE days, and disclose the e-mail question** as
   unresolved on the sources read. Do not carry a three-day extension from any
   neighbour, and do not add an e-mail extension on the strength of a search
   result.
3. **Record the two § 53-5-30 caveats** — the "purposes aforesaid" scope
   question and the fact that the shift by its terms reaches only the state half
   of the union — and send both to the bundled holiday question.

Remaining effort: read Rules 12, 33, 34 and 36.
