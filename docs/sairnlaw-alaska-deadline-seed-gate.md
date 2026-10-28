# SAIRNlaw — Alaska deadline seed gate

**Run 2026-10-28, hank b63, on Michael's J1 decision ("gate and seed AK").**

**Verdict: PASS, with stated readings.**
- Every reading that is not compelled by the text resolves to the EARLY side.
- No row can report a date later than the one the rule gives.
- The coverage disclosure is `direction: 'early'`.

## 1. Sources — what was read, and how
Every quoted passage below was read verbatim from the official text, downloaded on 2026-10-28. Nothing is from
memory or a secondary source.

| source | URL | what it supplies |
|---|---|---|
| Alaska Rules of Civil Procedure (PDF, 1,884,897 bytes) | https://courts.alaska.gov/rules/docs/civ.pdf | Civil Rules 6, 12, 33, 34, 36, 59, 77 |
| Alaska Rules of Appellate Procedure (PDF, 854,707 bytes) | https://courts.alaska.gov/rules/docs/app.pdf | Appellate Rules 204, 502 |
| AS 44.12.010–.025 (print view) | https://www.akleg.gov/basis/statutes.asp?media=print&secStart=44.12.010&secEnd=44.12.030 | the legal-holiday list and the two shift rules |

Authority: the Alaska Court System publishes the rules, and the Alaska Legislature publishes the statutes. Both are
free, official, and current. The PDFs were text-extracted with `pdftotext`.

## 2. Computation — Civil Rule 6(a), verbatim
> "In computing any period of time prescribed or allowed by these rules, by order of court, or by any applicable
> statute, the day of the act, event, or default from which the designated period of time begins to run is not to be
> included. The last day of the period is to be included, unless it is a Saturday, a Sunday, or a legal holiday, in
> which event the period runs until the end of the next day which is not a Saturday, Sunday, or legal holiday. When
> the period of time prescribed or allowed is less than seven days, not counting any period for mailing added under
> subsection (c) of this rule, intermediate Saturdays, Sundays, and legal holidays shall be excluded in the
> computation. A half holiday shall be considered as other days and not as a holiday."

- **The mechanism is Ohio's, so `impl: 'ohio_civ_r_6a'` with `short_period_exclusion_days: 7`.** That means: exclude
  the trigger day; roll the last day off a weekend or holiday; and for periods under 7 days, exclude intermediate
  weekends and holidays. Missouri and Massachusetts already map this way.
- **"not counting any period for mailing added under (c)" is express.** The under-7 test is made on the BASE count.
  That is what the engine does: `countValue < short_period_exclusion_days` is evaluated before any extension.
- **A half holiday is an ordinary day.** The engine has no half-holidays, so it already treats one this way.
- **THE COURT-CLOSURE LIMB IS NOT IN FORCE, AND THE PDF MAKES IT LOOK AS IF IT WERE.**
  - The text extraction places "Any day the court is closed for a full weekday or partial weekday will be considered a
    'legal holiday' for the purposes of time computation" right beside Rule 6.
  - Read against the page layout (PDF page 28–29), that sentence is the tail of the Note quoting **SCO 1875 (Amended)**.
    The rule's own history line says SCO 1875 was **rescinded by SCO 1995 effective November 29, 2022**.
  - Current 6(a) has no closed-court limb. A court closure that is not a legal holiday does NOT roll a deadline. It is
    not modelled.
- **Appellate Rule 502(a)** carries the same text, with "intermediate Saturdays, Sundays and holidays". It gets its own
  standard, so that the appellate row cites its own rule.

## 3. The holiday referent — AS 44.12.010
Rule 6(a) says "legal holiday" and names no statute. **AS 44.12.010 is TITLED "Legal holidays" and opens "The
following days are legal holidays".** That is the exact phrase, which is a closer link than Missouri's convergence.

The statute's list, verbatim (a)(1)–(14):
- New Year's Day;
- MLK, Jr.'s Birthday (3rd Monday of January) "as provided in (b)";
- Presidents' Day (3rd Monday in February);
- **Seward's Day (last Monday of March)**;
- Memorial Day;
- **Juneteenth Day (19 June)**;
- Independence Day;
- Labor Day;
- **Alaska Day (18 October)**;
- Veterans' Day;
- Thanksgiving Day;
- Christmas Day;
- every Sunday;
- every day designated by proclamation of the President or the governor.

### Three readings, each resolved to the EARLY side and disclosed
1. **MLK Day is NOT encoded.**
   - (a)(2) lists it "as provided in (b)". (b) begins "For employment purposes, Martin Luther King, Jr.'s Birthday is a
     legal holiday for state employees who …", and conditions it on collective-bargaining terms.
   - The cross-reference makes MLK's legal-holiday status conditional on (b). (b) speaks only of employment. Whether
     MLK Day is a "legal holiday" for computing a court deadline is therefore a genuine question of law.
   - Encoding it would roll a deadline off MLK Day to Tuesday. If that reading is wrong, the date is a day LATE.
     Omitting it can only be a day EARLY. **Omitted, and disclosed.**
2. **The Saturday→Friday shift (AS 44.12.025) is NOT encoded.**
   - Verbatim: "If a holiday listed in AS 44.12.010 falls on a Saturday, the Saturday and the preceding Friday are both
     legal holidays **for officers and employees of the state**."
   - The limb is scoped to state personnel, not to time computation. In 2026, Friday 3 July must NOT roll.
   - This is the same treatment as Hawaii's HRS § 8-2 and Missouri's Sunday-only shift.
3. **Proclamation days ((a)(14)) are not derivable and are not encoded.** That is the EARLY direction.

### One shift IS encoded: the Sunday→Monday shift (AS 44.12.020)
- Verbatim: "If a holiday listed in AS 44.12.010, except AS 44.12.010(a)(13), falls on a Sunday, Sunday and the
  following Monday are both legal holidays."
- It is unscoped. It is a statutory legal holiday, so it is encoded. In 2026, Alaska Day falls on Sunday 18 October,
  so **Monday 19 October 2026 is a legal holiday**.
- Every Sunday-shift date in 2026–2031 is derived by day-of-week, not assumed.

### Standing gate check: weekend coverage
Saturday and Sunday are both named in 6(a). Sunday is also a legal holiday under (a)(13). There is no gap.

## 4. Service extension — Civil Rule 6(c), verbatim
> "Whenever a party has the right or is required to act within a prescribed period after the service or distribution
> of a document, other than documents served under Civil Rule 4(h), and the document is served or distributed by
> non-electronic mail, three calendar days shall be added to the prescribed period. However, no additional time shall
> be added if a court order specifies a particular calendar date by which an act must occur."

- **The extension applies to MAIL, and only non-electronic mail.** Electronic service earns nothing.
- **"added to the prescribed period" means the days lengthen the period**, with one rollover at the end. That is
  `add_to_period_then_roll`, the same as Missouri 44.01(d) and Massachusetts 6(d).
- **Civil Rule 4(h) is "Service of Process by Mail".** So the answer to a summons and complaint never takes the 3 days.
- **The distribution-triggered rows carry NO extension, by reading (EARLY):**
  - These are Civil Rule 59(b) and Appellate Rule 204(a)(1). Both run "from the date shown in the clerk's certificate
    of distribution". 6(c), and Appellate Rule 502(c), reach "distribution" by mail, so 3 days may well be added.
  - But 6(b) forbids enlarging 59(b), and an appeal filed late is lost.
  - Adding days the rule may not give is the LATE direction on the two deadlines where lateness is least recoverable.
    The rows omit the extension, and the disclosure says so. **This belongs in the bundled lawyer's question.**

## 5. What is seeded (12 rows) — every count read from the text above
| row | period | trigger | extension |
|---|---|---|---|
| Civ. R. 12(a) answer to complaint | 20 days | service of summons and complaint | none (4(h)) |
| Civ. R. 12(a) answer to cross-claim | 20 | service of the cross-claim | mail +3 |
| Civ. R. 12(a) reply to counterclaim | 20 | service of the answer | mail +3 |
| Civ. R. 12(a) state answer | 40 | service upon the attorney general | none (process) |
| Civ. R. 33(a)(3) interrogatory answers | 30 | service of the interrogatories | mail +3 |
| Civ. R. 34(b) production response | 30 | service of the request | mail +3 |
| Civ. R. 36(a) admissions response | 30 | service of the request | mail +3 |
| Civ. R. 77(c)(2) opposition to a motion | 10 | service of the motion | mail +3 |
| Civ. R. 77(c)(2)(B) opposition to a dispositive motion | 15 | service of the motion | mail +3 |
| Civ. R. 77(d) reply | **5 (under 7: intermediate weekends and holidays excluded)** | service of the opposition | mail +3 |
| Civ. R. 59(b) motion for new trial | 10 | date in the clerk's certificate of distribution | none (§4) |
| App. R. 204(a)(1) notice of appeal | 30 | date in the clerk's certificate of distribution | none (§4) |

**Limbs NOT seeded, each EARLY-safe:**
- **Rule 77(c)(2)(A), pre-answer motions.** The true deadline is the later of 10 days or the answer date. The plain
  10-day row is earlier-or-equal.
- **Rule 77(c)(2)(B), where the plaintiff is the movant.** The later of 15 days or the answer date. The 15-day row is
  earlier-or-equal.
- **Rule 77(c)(2)(C).** Rules carrying their own response times, which are not seeded.
- **Every "shorter or longer time may be directed by the court".** That is an order the engine cannot see.

`effective_from` is **2022-11-29** on every row. That is the last amendment to Civil Rule 6 in its own history line
(SCO 1995), which is the text read. Each rule's own amendment history was NOT traced. A matter triggered before
2022-11-29 should have the then-current text confirmed by hand.

## 6. Calendar
- 2026–2031, derived from AS 44.12.010 and .020 by date arithmetic.
- 11 encoded holidays per year, plus a Monday wherever one falls on a Sunday.
- MLK Day, the Saturday→Friday days and proclamation days are omitted (§3).
- Every entry carries its `derivation`.

## 7. NOT done in this gate
- **Live load.** The seed reaches a licence only through `legal-deadlines` `add_rule` / `add_holidays`. That needs a
  signed-in owner or attorney session (`RULE_AUTHORING_ROLES`), which hank does not hold. The files and the engine are
  shipped; loading them onto a licence is Michael's step.
- **District court (small claims) rules** were not read.
