# Kansas — deadline-seed source-availability gate

**Run 2026-08-30. Verdict: PASS, and SEEDED the same day — 10 rules, calendar
2026, loaded to `LAW-PINNACLE-2026` and live-verified 14/14.**

**The best source position since Wisconsin, for a structural reason: Kansas puts
civil procedure in the STATUTE, not in court rules.** K.S.A. chapter 60 article
2 carries computation, answers, motions and all three discovery periods, and the
Kansas Office of Revisor of Statutes — the official publisher — serves every
section as free HTML on a plain request with no gate, no sign-in and no
click-through. There is no Westlaw or Lexis hop anywhere in this state, which is
what Tennessee lacked entirely and what Colorado still needs a decision about.

Kansas (~2.9M) was chosen as the largest unseeded state without an existing gate
document, after confirming no gate-passed jurisdiction remained unseeded.

---

## 1. Sources — PASS on both channels

| What | URL | Result |
|---|---|---|
| K.S.A. 60-206 (time) | `ksrevisor.gov/statutes/chapters/ch60/060_002_0006.html` | **200**, real text |
| K.S.A. 60-212 (answers) | `…/060_002_0012.html` | **200** |
| K.S.A. 60-233 / 234 / 236 (discovery) | `…/060_002_00{33,34,36}.html` | **200** |
| Court holiday schedule | `kscourts.gov/Footer/Holiday-Schedule` | **200**, 2025 and 2026 |

**One access note.** `kscourts.gov/About-the-Courts/Programs/Rules` returns
**403** on a plain request, but `kscourts.gov/Footer/Holiday-Schedule` and
`/Rules-Orders/Rules/Terms-of-Court-Holidays` both return 200 with an ordinary
browser user-agent. The 403 is path-specific, not host-wide — worth recording so
nobody concludes the judicial host is closed.

**Currency is printed per section**, immediately after the last session law:

| Section | Tail of the History line | Effective |
|---|---|---|
| 60-206 | `L. 2020, ch. 4, § 3; March 19` | **2020-03-19** |
| 60-212 | `L. 2010, ch. 135, § 79; July 1` | 2010-07-01 |
| 60-233 | `L. 2010, ch. 135, § 102; July 1` | 2010-07-01 |
| 60-234 | `L. 2017, ch. 75, § 7; July 1` | **2017-07-01** |
| 60-236 | `L. 2010, ch. 135, § 105; July 1` | 2010-07-01 |

**No convention was needed and none was invented.** Contrast Wisconsin, whose
statutes PDF gives a History line and no per-section date, forcing every row
there to carry a deliberately conservative "1 January following the last
amending act".

## 2. THE FINDING IS AN ABSENCE — there is no short-period exclusion

**K.S.A. 60-206(a)(1)**, verbatim:

> When the period is stated in days or a longer unit of time: (A) Exclude the
> day of the event that triggers the period; (B) **count every day, including
> intermediate Saturdays, Sundays and legal holidays**; and (C) include the last
> day of the period, but if the last day is a Saturday, Sunday or legal holiday,
> the period continues to run until the end of the next day that is not a
> Saturday, Sunday or legal holiday.

Kansas took the **2010 restyling** that abolished the exclusion federally
(`L. 2010, ch. 135` runs through all of these sections). It therefore joins
Minnesota, Utah and Nevada in having **none at all**.

**The running tally across seeded states, which is now wide enough that copying
is indefensible:** 7 for NJ, NC, WA, MA, MO, SC, Ohio and Indiana; **8** for
Maryland ("seven days or less"); **11** for Tennessee, Arizona, Wisconsin and
Alabama; **14** for Arkansas; **6** for Texas ("five days or less"); and **none**
for Minnesota, Utah, Nevada and now Kansas. Declaring any threshold on Kansas
would drop days the statute counts and report **LATER** than the true deadline.

The seed's test asserts `short_period_exclusion_days` is **undefined**, not
merely small, and pins it as arithmetic on the seven-day backward row — exactly
where a Maryland-style value would change the answer.

## 3. Service — federal order, and NO electronic limb

**K.S.A. 60-206(d)**, verbatim:

> When a party may or must act within a specified time after being served and
> service is made under K.S.A. 60-205(b)(2)(C) **(mail)**, or (D) **(leaving
> with the clerk)**, and amendments thereto, **three days are added after the
> period would otherwise expire** under subsection (a).

Two things, and both cut against the recent run of states:

- **THE ORDER IS FEDERAL after-expiry** — the same sequencing words as FRCP 6(d)
  and Ala. R. Civ. P. 6(d). Roll, add, roll again. Nearly every state seeded
  before Alabama is period-lengthening instead, and the two orders diverge
  whenever the unrolled last day lands on a weekend or holiday.
- **THERE IS NO ELECTRONIC LIMB.** Mail and leaving-with-the-clerk only. E-mail
  and the e-filing system get **nothing** — the federal position, and the
  opposite of Arkansas, Alabama and Massachusetts, all of which extend for
  electronic service. A `qualifies()` copied from any of those over-counts and
  reports **LATE**.

This is the eighth distinct answer on electronic service across the states
gated, and the second (after the federal seed itself) that is simply "no".

## 4. The holiday definition — four limbs, and the fourth is the one that governs

**K.S.A. 60-206(a)(6)**, verbatim:

> "Legal holiday" means any day declared a holiday by the president of the
> United States, the congress of the United States or the legislature of this
> state, **or any day observed as a holiday by order of the Kansas supreme
> court**. **A half holiday is considered as other days and not as a holiday.**

The calendar is that fourth limb — the Judicial Branch's own published schedule,
which lists 2025 and 2026 side by side. **Twelve dates for 2026**, including
**TWO days for Thanksgiving** (26 and 27 November, both printed) and
**Independence Day published as Friday 3 July**, since 4 July 2026 is a
Saturday. Nothing is derived from a shift rule; the schedule states the observed
date, the same transcription approach used for Arkansas and Maryland.

### WHY THIS IS NOT THE WISCONSIN PROBLEM

The Kansas schedule carries language that looks exactly like the Wisconsin
hazard:

> A court may defer observing a holiday if it will interfere with judicial
> proceedings in progress. At the discretion of the chief judge and with the
> approval of the judicial administrator, **a district court may remain open on
> any of these designated holidays.**

**It is not the same problem, and the difference is which fact the statute keys
on.** Wis. Stat. § 801.15(1)(b) rolls the last day unless it is *"a day the
clerk of courts office is closed"* — an actual-closure test — so a county
staying open destroys the list as a proxy, which is why Wisconsin's calendar had
to fall back to a three-day statewide intersection. **K.S.A. 60-206(a)(6) keys
on the day being OBSERVED BY ORDER OF THE SUPREME COURT**, a statewide legal
fact. A district court opening its doors does not stop the day being a legal
holiday for computation purposes. **The list IS the test here; in Wisconsin it
was not.**

## 5. Periods, read verbatim

- **60-212(a)(1)** — answer **21 days** after service of the summons and
  **petition** (Kansas's name for the complaint); **21 days** to answer a
  counterclaim or crossclaim; **21 days** to reply to an answer **after being
  served with an order to reply** — there is no reply unless the court orders
  one. Motion limbs: **14 days** after *notice of the court's action*, **14
  days** after *service* of a more definite statement.
- **60-206(c)** — motion and notice of hearing at least **7 days** before;
  opposing affidavit at least **1 day** before. Both backward, and both counted
  straight through weekends because there is no exclusion.
- **60-233(b)(2), 60-234(b)(2)(A), 60-236(a)(3)** — all **30 days**, and all
  three say a defendant **"MAY serve"** within 45 days after being served with
  process.

**KANSAS IS THE FIRST SEEDED JURISDICTION WHERE ALL THREE DISCOVERY PERIODS ARE
ELECTIONS.** Alabama and Wisconsin each make one of the three mandatory (*"shall
not be required to serve before"*), South Carolina makes its admissions rule
mandatory, and Kansas makes none of them so. All three are therefore plain
30-day rows and **no Kansas row is a `resolve_periods`** — asserted in the test
as a count of zero.

## 6. What was NOT determined, and what is NOT encoded

- **60-212(a)(1)(A)(ii), service by publication.** The answer is due *"within
  the time fixed in the notice, which must not be less than 41 days from the
  time the notice is first published"*. The engine cannot read a notice, and the
  41 days is a **floor on what the notice may lawfully say**, not the period —
  so encoding 41 would report the earliest date the notice could have set rather
  than the date it did.
- **60-205 itself** was fetched but not read end to end; only the (b)(2)(C) and
  (D) cross-references 60-206(d) depends on were checked.
- **60-206(b) extensions** are discretionary and not computable.
- **60-206(e)** lets the **chief justice extend or suspend these computation
  rules entirely** during an emergency, under K.S.A. 20-172. No engine can
  anticipate that; it is disclosed.
- **An ad hoc holiday declared by the President or Congress** after the annual
  schedule publishes is a legal holiday under the first two limbs of (a)(6) and
  is not in the calendar. Omitting it reports **EARLY** — safe, disclosed.

## 7. Verdict

**PASS, and seeded.** Free official statute text with printed per-section
effective dates, a free official statewide holiday schedule that is the exact
statutory limb the courts run on, no gated host anywhere, and no unresolved
question in the direction that loses a filing.

Live: **28 jurisdictions before Kansas, 29 after; 316 computing rules before,
326 after.** 929/929 deadline tests pass.
