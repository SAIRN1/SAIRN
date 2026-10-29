# SAIRNlaw — South Dakota deadline seed gate

**Run 2026-10-29, hank b64, fourth in Michael's J1 order.**

**Verdict: PASS.**
- The rule names its holiday statute, so the referent is express.
- Every reading not compelled by the text resolves EARLY.
- The coverage disclosure is `direction: 'early'`.

## 1. Sources — read verbatim on 2026-10-29
These come from the South Dakota Legislature's official codified-law service, `https://sdlegislature.gov/api/Statutes/<section>.html`.
South Dakota's civil rules ARE statutes, codified as SDCL 15-6-x.

| section | what it supplies |
|---|---|
| SDCL 15-6-6(a) | computation (last amended by Sup. Ct. Rule 18-14, eff. July 1, 2018) |
| SDCL 15-6-6(e) | mail extension |
| SDCL 1-5-1, 1-5-1.1, 1-5-1.2 | legal holidays and their shifts |
| SDCL 15-6-12(a), 15-6-33(a), 15-6-34(b), 15-6-36(a), 15-6-59(b) | periods |
| SDCL 15-26A-6 | the time to appeal |

## 2. Computation — SDCL 15-6-6(a)
> "The last day of the period so computed shall be included, unless it is a Saturday, a Sunday or a legal holiday or,
> when the act to be done is the filing of a paper in court, a day on which weather or other conditions have made the
> office of the clerk of court inaccessible … **When the period of time prescribed or allowed is less than eleven
> days, intermediate Saturdays, Sundays, and legal holidays shall be excluded in the computation.** As used in this
> rule, 'legal holiday' includes those holidays listed in § 1-5-1."

- **The mechanism is Ohio's, but with ELEVEN.** That is `impl: 'ohio_civ_r_6a'`, `short_period_exclusion_days: 11`.
  It is the old federal threshold, and the first seeded state to use it. A 7 copied from Alaska, Missouri or
  Massachusetts would count a 10-day SD period as calendar days and run EARLY. That is safe, but wrong.
- **The clerk-inaccessible limb** is not modelled. That is EARLY.
- **Electronic service completed after 11:59 p.m.** "shall be deemed to be made on the following weekday". The
  trigger date the caller supplies may therefore be a day early. That is EARLY.
- **SDCL 15-26A-6** (appeal) is a statute, and 6(a) governs "any period of time prescribed … by any applicable
  statute". So the appeal row uses the same standard.

## 3. Holidays — SDCL 1-5-1, EXPRESS
**The list:** Sunday; 1 January; MLK Day (third Monday in January); the third Monday in February; Memorial Day;
**Juneteenth (19 June)**; 4 July; Labor Day; **Native Americans' Day (second Monday in October)**; 11 November;
Thanksgiving; 25 December; "every day appointed by the President … or by the Governor … for a public fast,
thanksgiving, or holiday".

**Shifts, verbatim:** "If the first day of January, the nineteenth day of June, the fourth day of July, the eleventh
day of November, or the twenty-fifth day of December falls upon a Sunday, the Monday following is a legal holiday and
shall be so observed; and if any such day falls upon a Saturday, the preceding Friday is a legal holiday and shall be
so observed."

- **Both shifts are encoded.** They are general, not scoped to employees.
- They cover FIVE days, which is one more than North Dakota, because Juneteenth is included.
- **Proclamation days are not encoded.** That is EARLY.

## 4. Mail — SDCL 15-6-6(e)
> "… and the notice or paper is served by mail, three days shall be added to the prescribed period. Service by
> facsimile or electronic mail transmission shall not be deemed service by mail."

- **The extension applies to MAIL only.** It is added to the period, so `add_to_period_then_roll`.
- **THE UNDER-ELEVEN QUESTION IS AVOIDED, NOT ANSWERED.** Whether the 11-day threshold is tested before or after the
  3 days is not stated, unlike Alaska's "not counting any period for mailing". The two readings give different dates.
  **So no seeded row with a base count under 11 carries the extension.** The only such row (59(b), 10 days) takes no
  mail days for the separate reason in §5. Every extended row has a base of 20 or 30, where the threshold cannot bite
  on either reading.

## 5. Seeded (8 rows)
| row | days | extension |
|---|---|---|
| 15-6-12(a) answer to complaint | 30 after service of the complaint | none: process (EARLY) |
| 15-6-12(a) answer to cross-claim | 20 | mail +3 |
| 15-6-12(a) reply to counterclaim | 20 after service of the answer | mail +3 |
| 15-6-33(a) interrogatories | 30 | mail +3 |
| 15-6-34(b) production | 30 | mail +3 |
| 15-6-36(a) admissions | 30 | mail +3 |
| 15-6-59(b) new trial | **10, so under 11: intermediate weekends and holidays excluded** | none (EARLY): "after notice of entry", same reading as AK and ND |
| 15-26A-6 notice of appeal | 30 after written notice of entry is given | none (EARLY); the same lawyer's question |

**Not seeded, each EARLY-safe:**
- the defendant's 45-day floor in 33, 34 and 36;
- the 10-day post-motion limbs of 12(a);
- the ordered reply.

The dispatch said "12 rules". The text supports these 8 without guessing a limb.

## 6. Calendar
2026–2031, derived from 1-5-1 with both shifts and computed by day of week. For example:
- Saturday 4 July 2026 makes **Friday 3 July 2026** the holiday.
- Saturday 19 June 2027 makes **Friday 18 June 2027** the holiday.
