# Arkansas — deadline-seed source-availability gate

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
