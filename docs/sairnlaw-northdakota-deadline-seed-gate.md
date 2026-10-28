# SAIRNlaw — North Dakota deadline seed gate

**Run 2026-10-28, hank b63, second in Michael's J1 order (AK, ND, RI, SD, VT, WY, DC).**

**Verdict: PASS.**
- The rule names its own holiday statute, so the referent is express.
- Every reading not compelled by the text resolves EARLY.
- The coverage disclosure is `direction: 'early'`.

## 1. Sources — read verbatim on 2026-10-28
| source | URL | effective |
|---|---|---|
| N.D.R.Civ.P. 6 | https://www.ndcourts.gov/legal-resources/rules/ndrcivp/6 | 3/1/2018 |
| N.D.R.Civ.P. 12, 33, 34, 36, 59 | https://www.ndcourts.gov/legal-resources/rules/ndrcivp/12 (and /33, /34, /36, /59) | 12: 3/1/2011 |
| N.D.R.Ct. 3.2 (motions) | https://www.ndcourts.gov/legal-resources/rules/ndrct/3-2 | 3/1/2025 |
| N.D.R.App.P. 4 | https://www.ndcourts.gov/legal-resources/rules/ndrappp/4 | **9/1/2026** |
| N.D.R.App.P. 26 | https://www.ndcourts.gov/legal-resources/rules/ndrappp/26 | 10/1/2018 |
| N.D.C.C. ch. 1-03 | https://ndlegis.gov/cencode/t01c03.pdf | — |

These are the official publications of the North Dakota Supreme Court and the Legislative Assembly. They are free.

## 2. Computation — N.D.R.Civ.P. 6(a), the modern federal form
> "(A) exclude the day of the event that triggers the period; (B) count every day, including intermediate Saturdays,
> Sundays, and legal holidays; and (C) include the last day of the period, but if the last day is a Saturday, Sunday,
> or legal holiday, the period continues to run until the end of the next day that is not a Saturday, Sunday, or
> legal holiday."

- This is `impl: 'frcp_6a'`, with no short-period exclusion.
- The Explanatory Note says so expressly: "Under the amended rule, intermediate weekends and holidays are counted
  regardless of the length of the specified period" (effective March 1, 2011).
- **N.D.R.App.P. 26(a)** is the same text and gets its own standard.
- **6(a)(3), inaccessibility of the clerk's office**, is an extra rollover the calendar cannot see. It is disclosed
  EARLY, the same as Utah's identical limb.

## 3. The holiday referent is EXPRESS — Rule 6(a)(6)
> "'legal holiday' means a day set aside as a holiday under N.D.C.C. §§ 1-03-01, 1-03-02 and 1-03-02.1."

App. R. 26(a)(6) uses the same words.

**N.D.C.C. 1-03-01, verbatim list:**
- every Sunday;
- 1 January;
- the third Monday of January (Martin Luther King Day);
- the third Monday in February;
- **"The Friday next preceding Easter Sunday and commonly known as Good Friday"**;
- the last Monday in May;
- 4 July;
- the first Monday in September;
- 11 November;
- the fourth Thursday in November;
- 25 December;
- "Every day appointed by the President of the United States or by the governor of this state for a public holiday."

**The shifts. Both directions are named by the rule, so BOTH are encoded:**
- **1-03-02:** "If the first day of January, the fourth day of July, the eleventh day of November, or the twenty-fifth
  day of December falls upon a Sunday, the Monday following shall be the holiday."
- **1-03-02.1:** "If any of the holidays enumerated in section 1-03-02 fall on a Saturday, the Friday immediately
  before shall be the holiday."
- These are four days only. MLK, Presidents', Memorial and Labor Days are always Mondays.
- Unlike Alaska's AS 44.12.025, the Saturday shift here is not scoped to state employees, and Rule 6(a)(6) cites it
  by number.
- In 2026: Friday 3 July is a legal holiday. In 2027: Friday 24 December, and Friday 31 December for Saturday
  1 January 2028.

**Deliberately absent, each EARLY:**
- **Juneteenth.** It is not in 1-03-01. It was created by Congress, not "appointed by the President", so (12) does
  not plainly reach it.
- **Columbus Day.** It is not listed.
- **The Christmas Eve noon closure (1-03-01.1).** It closes offices for half a day. It does not make a holiday.
- **Proclamation days ((12)).** They cannot be derived.

## 4. Service extension — two different rules, both AFTER-EXPIRY
- **N.D.R.Civ.P. 6(e)(1):** "Whenever a party must or may act within a prescribed period after service and service is
  made by mail or third-party commercial carrier under Rule 5, three days are added after the prescribed period would
  otherwise expire under N.D.R.Civ.P. 6(a)."
  - That is `roll_then_add_then_roll`, the federal order.
  - It applies to mail and third-party commercial carrier only.
- **6(e)(2):** "If service is made by mail or third-party commercial carrier under Rule 4, the prescribed period
  begins running upon delivery."
  - The answer row takes NO days. Its trigger date IS the delivery date.
- **N.D.R.App.P. 26(c):** "When a party may or must act within a specified time after being served, three days must
  be added after the period would otherwise expire, unless the document is delivered on the date of service stated
  in the proof of service. … a document that is served electronically is treated as delivered on the date of
  service."
  - The appeal runs "from service of notice of entry", which is squarely "after being served". **The appeal row
    takes the 3 days for mail and commercial carrier.**
  - Unlike Alaska, the trigger here is SERVICE, not the clerk's distribution, so there is no reading to make.

## 5. Seeded (9 rows)
| row | period | trigger | extension |
|---|---|---|---|
| Civ.R. 12(a)(1)(A) answer to complaint | 21 | served with summons and complaint | none (6(e)(2)) |
| Civ.R. 12(a)(1)(B) answer to counterclaim / crossclaim | 21 | served with the pleading | 6(e) |
| Civ.R. 33(b)(2) interrogatories | 30 | served | 6(e) |
| Civ.R. 34(b)(2)(A) production | 30 | served | 6(e) |
| Civ.R. 36(a)(3) admissions | 30 | served | 6(e) |
| Ct.R. 3.2(a)(2) answer brief | 14 | service of the brief | 6(e) |
| Ct.R. 3.2(a)(2) reply brief | 7 | service of the answer brief | 6(e) |
| Civ.R. 59(c)(2) new trial (other grounds) | 60 | notice of entry of judgment | none, by reading (EARLY) |
| App.R. 4(a)(1) notice of appeal | 60 | service of notice of entry | App.R. 26(c) |

**Not seeded, each EARLY-safe:**
- **The defendant's 45-day floor in Rules 33, 34 and 36.** Each runs from service of the summons, and the 30-day row
  is earlier-or-equal.
- **Rule 59(c)(1)**, six months.
- **The 12(a)(1)(C) ordered reply.**
- **The App.R. 4(a)(2) 14-day cross-appeal limb.**
- **Rule 59(c) takes no mail days.** "After notice of entry" may reach a mailed notice, but adding days a rule may
  not give is the LATE direction. It belongs in the bundled lawyer's question.

## 6. Calendar
2026–2031, derived from 1-03-01, -02 and -02.1. Good Friday is computed from Easter (the anonymous Gregorian
algorithm) and checked against 3 April 2026.

## 7. Not done here
District-court local rules. Small claims.
