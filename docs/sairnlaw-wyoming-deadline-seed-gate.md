# SAIRNlaw — Wyoming deadline seed gate

**Run 2026-10-29, hank b65.**

**Verdict: PASS.** Every open reading resolves EARLY, and the coverage disclosure is `direction: 'early'`.

## Sources — read verbatim on 2026-10-29
- **Rules:** W.R.C.P., the compiled edition "Eff. 9-21-26", at
  https://www.wyocourts.gov/app/uploads/2025/01/WY-Rules-of-Civ.-Procedure-Eff.-9-21-26.pdf
  (1,223,362 bytes), linked from wyocourts.gov/court-rules/wyoming-rules-of-civil-procedure/.
- **Holidays:** W.S. 8-4-101, from the Wyoming Legislature's title PDF at https://wyoleg.gov/statutes/compress/title08.pdf.

## Computation — W.R.C.P. 6(a) (added February 2, 2017, effective March 1, 2017)
> "The last day of the period so computed shall be included, unless it is a Saturday, a Sunday, or a legal holiday, or,
> when the act to be done is the filing of a paper, a day on which weather or other conditions have made the office of
> the clerk of the court inaccessible … As used in this rule, 'legal holiday' includes any day officially recognized as
> a legal holiday in this state by designation of the legislature, appointment as a holiday by the governor or the chief
> justice of the Wyoming Supreme Court, or any day designated as such by local officials."

- This is the federal count (`frcp_6a`), with no short-period exclusion.
- **The referent is OPEN-ENDED.** Only the legislature's list (8-4-101) can be derived. Days appointed by the governor
  or the chief justice, and days set by local officials, are omitted. That is EARLY.
- The clerk-inaccessible limb is also omitted (EARLY).

## Holidays — W.S. 8-4-101
**The list:**
- New Year's Day;
- the third Monday in February;
- Memorial Day;
- 4 July;
- Labor Day;
- Veterans Day;
- Thanksgiving;
- Christmas;
- MLK / Wyoming Equality Day (the third Monday in January);
- presidential days declared by the governor (not derivable).

**There is NO Juneteenth and NO Columbus Day.**

**The shift is (b), Sunday only:** "If New Year's Day, Independence Day, Christmas Day or Veterans Day fall upon a
Sunday, the Monday following is a legal holiday." There is no Saturday shift, so Friday 3 July 2026 does not roll.

## Mail — W.R.C.P. 6(d)
> "served upon the party by mail or by delivery to the clerk for service, three days shall be added to the prescribed
> period, provided however, this rule shall not apply to service of process by registered or certified mail under Rule
> 4(r)."

- The methods are mail and `left_with_clerk`.
- The days are added to the period, so `add_to_period_then_roll`.
- The answer row takes no days, because it runs from process.

## Seeded (6 rows)
| row | period | extension |
|---|---|---|
| 12(a)(1)(A)(i) answer | 20 days | none |
| 12(a)(1)(A)(ii) answer, served outside Wyoming | 30 days | none |
| 33(b)(2) interrogatories | 30 days | +3 |
| 34(b)(2)(A) production | 30 days | +3 |
| 36(a)(3) admissions | 30 days | +3 |
| 59(b) new trial | 28 days after entry | none |

**NOT seeded: the 6(c)(2) motion response.** It ends at "at least three days prior to the hearing … or within 20 days
after service of the motion, **whichever is earlier**". A 20-day date alone could be LATE.
