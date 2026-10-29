# SAIRNlaw — Rhode Island deadline seed: GATED, NOT SEEDED

**Run 2026-10-28, hank b63, third in Michael's J1 order.**

**Verdict: NOT SEEDABLE TODAY. The computation and the rules pass; the HOLIDAY REFERENT does not.** This is the same
shape that refused Kentucky. Nothing was loaded, and no engine entry was added.

## What PASSES (read verbatim on 2026-10-28)
Source: https://courts.ri.gov/Courts/superiorcourt/Documents/SuperiorCourtRulesOfCivilProcedure.pdf
(510,148 bytes, footer "February 2024").

- **Super. R. Civ. P. 6(a):**
  > "The last day of the period is to be included, unless it is a Saturday, Sunday, or a legal holiday, in which event
  > the period runs until the end of the next day which is neither a Saturday, Sunday, nor a holiday."

  There is no short-period exclusion, so this is the `frcp_6a` shape.
- **6(d):**
  > "Whenever a party has the right or is required to do some act or take some proceedings within a prescribed period
  > after the service of a notice or other paper upon the party, and the notice or paper is served upon the party
  > electronically or by mail, one (1) day shall be added to the prescribed period."
  - It is **ONE day**, and it covers **ELECTRONIC** service as well. That is unlike any of the 41 seeded jurisdictions
    checked so far, and it must not be copied from a neighbour.
  - "Added to the prescribed period" means `add_to_period_then_roll`.

## What BLOCKS
1. **Rule 6(a) says "legal holiday" and names no statute.** R.I. Gen. Laws § 25-1-1 is headed "General holidays
   enumerated" and ends "shall be holidays". This is the Kentucky/Missouri lexical gap. Missouri passed by CONVERGENCE
   with an official published schedule. **No official Rhode Island Judiciary holiday schedule could be found** on
   courts.ri.gov (two searches, 2026-10-28). Without one, convergence cannot be checked, only assumed.
2. **The weekend shifts in § 25-1-1 are scoped to employees.** For New Year's, Juneteenth, July 4, Veterans' and
   Christmas: "in the event that day is a Saturday or Sunday, then **state employees will celebrate** the holiday on the
   following Monday".
   - A separate general clause gives a Sunday→Monday shift: "when either of the above days falls on the first day of
     the week, then the day following it".
   - Whether a Saturday holiday's following Monday rolls a court deadline is a reading. Encoding it is the LATE
     direction.
3. **The incorporation clause is open-ended.** "any other days as the governor or general assembly of this state or the
   president or the Congress of the United States shall appoint as holidays for any purpose".
   - That plausibly takes in the whole federal list (5 U.S.C. § 6103), including **Thanksgiving, which § 25-1-1 does not
     itself name**.
   - It also takes in ad-hoc gubernatorial days, which cannot be derived.
4. **Election day.** "the Tuesday next after the first Monday in November in each year in which a general election of
   state officers is held". The general officers are elected in 2026 and 2030. Whether a legislative-only year (2028)
   counts is a reading.
5. **Two RI-only days, Victory Day (second Monday of August) and RI Independence Day (4 May),** are in the statute.
   Whether the courts close on them could not be confirmed against a court source.

## What would unblock it
Either an official Rhode Island Judiciary holiday or closure list to converge against, or Michael's / counsel's
direction on readings 2–4. **The direction to prefer, if forced:** encode only the days § 25-1-1 names directly, plus the
general Sunday→Monday shift. Omit the employee-only Monday shifts, 2028 election day and appointed days. Every one of
those omissions is EARLY. Thanksgiving is the hard case: omitting it is EARLY, but a Thanksgiving deadline the courts
are closed for would read a day short.

## b64 (2026-10-29): official referent searched for again — NOT FOUND, so still not seeded
Michael's b64 item 4 was to source the official referent, seed, and document the source here. Tried:
- **courts.ri.gov:**
  - `/PublicResources/holidays/Pages/default.aspx` returned 404.
  - `/Pages/holidays.aspx` returned 404.
  - The Superior Court rules PDF (above) carries no holiday list.
- **State HR:**
  - `admin.ri.gov/holidays` returned **403**.
  - `hr.ri.gov/holidays` and `ri.gov/holidays/` returned 404.
- **Two web searches** returned only third-party calendars (publicholidays.com, officeholidays.com and similar). One
  utility schedule was also found: RI Resource Recovery's 2026 PDF, which lists Victory Day as 10 August 2026. None of
  these is a permitted source for a gate.

Also found: **2026 House bill H 7781** (webserver.rilegislature.gov/BillText26/HouseText26/H7781.htm) carries
§ 25-1-1 text. Its enactment status was not confirmed. If it changes § 25-1-1, a seed built on today's text could go
stale on day one, which is one more reason not to guess.

**Still blocked, for the same reasons.** The single most useful unblock is the Rhode Island Judiciary's own annual
holiday or closure notice. The 403 on admin.ri.gov may be a bot block, so a human may get through where this fetch
did not.

## Next in the J1 order
South Dakota, then Vermont, Wyoming and DC. None was started in b63.

## b65 (2026-10-29): SEEDED on Michael's direction, on the EARLY-side reading above
Michael's b65 instruction was to seed RI from the Superior Court Rules PDF (Rule 6).

**Rule 6 was never the blocker.** It names no holiday statute, so the holiday list is still a reading of § 25-1-1. It
is encoded exactly as "the direction to prefer, if forced" says, and disclosed in `JURISDICTION_COVERAGE.ri`.

**Encoded:**
- every day § 25-1-1 names, including 4 May, Victory Day, Columbus Day and Juneteenth;
- the GENERAL Sunday→Monday shift;
- **Thanksgiving**, because the President proclaims it and Congress made it a holiday (5 U.S.C. § 6103). The
  incorporation clause reaches both, so this is no longer the "hard case";
- general election day in 2026 and 2030, the years general officers are elected.

**Omitted, each EARLY:**
- the employee-only Monday after a SATURDAY holiday;
- 2028 election day;
- governor- or Assembly-appointed days.

**Computation and rules:** `ri_rcp_6a` (the federal count) and `ri_rcp_6d` (+1 day, mail OR electronic). The 8 rows
are read verbatim from the February 2024 PDF: Rules 12(a), 33, 34, 36, 59(b) and 59(e).
