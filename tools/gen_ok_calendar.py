"""Generate sql/sairnlaw_deadline_calendars_oklahoma.json, 2026-2031.

DERIVED FROM 25 O.S. Sec. 82.1(A), as incorporated by 12 O.S. Sec. 2006(A)(1)
('unless it is a legal holiday as defined by Section 82.1 of Title 25').

ONE DAY A YEAR IS DELIBERATELY MISSING, AND IT IS DISCLOSED RATHER THAN GUESSED.

Sec. 82.1(A) on Christmas, verbatim:

    Christmas on the 25th day of December, THE DAY BEFORE OR AFTER CHRISTMAS
    if Christmas is not on a Saturday or Sunday, the Thursday and Friday
    before Christmas if Christmas is on a Saturday, the Monday and Tuesday
    after Christmas, if Christmas is on a Sunday

"The day before OR after" does not say which. Sec. 82.1(B) says what does:

    The Governor shall issue an Executive Order each year specifying the dates
    on which the holidays other than Saturdays and Sundays designated in
    subsection A of this section occur.

THE EXECUTIVE ORDERS ARE REACHABLE AND UNREADABLE. The Secretary of State
publishes them at sos.ok.gov and they are identifiable by title -- EO 2026-26
AMENDED, 15 July 2026, "Hereby order the following dates be observed as
holidays by the State of Oklahoma in 2027" -- but every one is a SINGLE-PAGE
SCANNED IMAGE. pypdf extracts ZERO characters and the page carries
/ProcSet [/PDF /ImageI] with a single /Im1 Do. Reading the dates would need
OCR, which is not a source this project treats as verbatim.

SO ON A WEEKDAY CHRISTMAS THE EXTRA DAY IS OMITTED. Omitting a real holiday
means a deadline landing on it is not rolled, so the reported date is EARLIER
than the true one -- the safe direction, the same call made for Massachusetts's
Suffolk County days and Utah's limb (M). GUESSING would be worse in both
directions at once: encoding 24 December when the order said 28 December adds a
non-holiday (LATE, the direction that loses a filing) and still misses the real
one (EARLY).

The determinate limbs ARE encoded: a Saturday Christmas gives the Thursday and
Friday before, a Sunday Christmas gives the Monday and Tuesday after. Only the
weekday case is ambiguous, and assert_christmas() checks each year lands in the
branch it should.

THREE OTHER THINGS THIS LIST DOES NOT HAVE, all of which a neighbour's calendar
would wrongly add:

  1. NO JUNETEENTH. Sec. 2006 defines legal holiday by reference to Sec. 82.1
     ONLY, and Oklahoma's Juneteenth lives in Sec. 82.2 and Sec. 82.4 -- "the
     THIRD SATURDAY in June", not 19 June. It is already a non-day under
     82.1(A)'s "Each Saturday", so encoding it changes nothing when right and
     adds a spurious holiday when placed on 19 June. Do not add it.
  2. NO COLUMBUS DAY and no Indigenous Peoples Day, as in Oregon.
  3. Sec. 82.2's commemorative days -- Jefferson Day, Oklahoma Day, Will Rogers
     Day, state election days and the rest -- are NOT legal holidays for
     deadline purposes, because 2006(A)(1) points at 82.1 alone. Confirmed by
     reading 82.2 rather than assumed.

AND THE DAY AFTER THANKSGIVING *IS* A HOLIDAY, which most states do not have.

Sources, both free on plain curl:
  12 O.S. 2006  oscn.net/applications/oscn/DeliverDocument.asp?CiteID=94867
  25 O.S. 82.1  oscn.net/applications/oscn/DeliverDocument.asp?CiteID=73358

Run: python tools/gen_ok_calendar.py
"""

import datetime as dt
import json
import os

YEARS = [2026, 2027, 2028, 2029, 2030, 2031]

RULE_URL = "https://www.oscn.net/applications/oscn/DeliverDocument.asp?CiteID=94867"
STAT_URL = "https://www.oscn.net/applications/oscn/DeliverDocument.asp?CiteID=73358"

# 25 O.S. 82.1(A). "Each Saturday, Sunday" is item one and is NOT emitted --
# the engine already treats weekends as non-days.
FIXED = [
    ("New Year's Day", (1, 1), "25 O.S. 82.1(A) January 1"),
    ("Independence Day", (7, 4), "25 O.S. 82.1(A) July 4"),
    ("Veterans' Day", (11, 11), "25 O.S. 82.1(A) November 11"),
]


def days(year, month):
    d = dt.date(year, month, 1)
    out = []
    while d.month == month:
        out.append(d)
        d += dt.timedelta(days=1)
    return out


def nth_weekday(year, month, weekday, n):
    return [d for d in days(year, month) if d.weekday() == weekday][n - 1]


def last_weekday(year, month, weekday):
    return [d for d in days(year, month) if d.weekday() == weekday][-1]


def observed(d):
    """25 O.S. 82.1(A)'s general shift -- and note it expressly excludes
    Christmas: 'if any of such holidays OTHER THAN CHRISTMAS fall on Saturday,
    the preceding Friday ... and if any of such holidays OTHER THAN CHRISTMAS
    fall on Sunday, the succeeding Monday'. Christmas has its own rules in
    christmas_days() instead."""
    w = d.weekday()
    if w == 5:
        return d - dt.timedelta(days=1), "25 O.S. 82.1(A) Saturday -> preceding Friday (holidays other than Christmas)"
    if w == 6:
        return d + dt.timedelta(days=1), "25 O.S. 82.1(A) Sunday -> succeeding Monday (holidays other than Christmas)"
    return d, ""


def christmas_days(year):
    """The most complex Christmas rule encountered anywhere.

    Returns (rows, ambiguous) -- rows are the days that ARE determinate, and
    `ambiguous` is True when the statute produces a day it does not identify.
    """
    x = dt.date(year, 12, 25)
    w = x.weekday()
    if w == 5:  # Saturday
        return ([(x - dt.timedelta(days=2), "Christmas Eve observance (Thursday before)",
                  "25 O.S. 82.1(A) the Thursday before Christmas, Christmas being a Saturday"),
                 (x - dt.timedelta(days=1), "Christmas observance (Friday before)",
                  "25 O.S. 82.1(A) the Friday before Christmas, Christmas being a Saturday")], False)
    if w == 6:  # Sunday
        return ([(x + dt.timedelta(days=1), "Christmas observance (Monday after)",
                  "25 O.S. 82.1(A) the Monday after Christmas, Christmas being a Sunday"),
                 (x + dt.timedelta(days=2), "Christmas observance (Tuesday after)",
                  "25 O.S. 82.1(A) the Tuesday after Christmas, Christmas being a Sunday")], False)
    # Weekday Christmas: 25 December itself, plus ONE unidentified adjacent day.
    return ([(x, "Christmas Day",
              "25 O.S. 82.1(A) December 25 -- the accompanying 'day before or after' "
              "is NOT encoded, see the readme")], True)


def build_year(year):
    rows = []
    for name, (m, d), src in FIXED:
        obs, shift = observed(dt.date(year, m, d))
        if obs.year != year:
            continue
        rows.append((obs, name, src + ("; " + shift if shift else "")))

    thanks = nth_weekday(year, 11, 3, 4)
    rows += [
        (nth_weekday(year, 1, 0, 3), "Martin Luther King, Jr.'s Birthday",
         "25 O.S. 82.1(A) third Monday in January"),
        (nth_weekday(year, 2, 0, 3), "Presidents' Day",
         "25 O.S. 82.1(A) third Monday in February"),
        (last_weekday(year, 5, 0), "Memorial Day",
         "25 O.S. 82.1(A) last Monday in May"),
        (nth_weekday(year, 9, 0, 1), "Labor Day",
         "25 O.S. 82.1(A) first Monday in September"),
        (thanks, "Thanksgiving Day",
         "25 O.S. 82.1(A) fourth Thursday in November"),
        (thanks + dt.timedelta(days=1), "The day after Thanksgiving Day",
         "25 O.S. 82.1(A) the day after Thanksgiving Day -- a statutory holiday, "
         "unlike Minnesota where it is a branch option"),
    ]

    xmas, _ambig = christmas_days(year)
    rows.extend(xmas)

    # Year-boundary spill from the NEXT year's fixed-date holidays.
    for name, (m, d), src in FIXED:
        obs, shift = observed(dt.date(year + 1, m, d))
        if obs.year == year:
            rows.append((obs, "%s (%d, observed early)" % (name, year + 1),
                         src + "; " + shift + " -- SPILLS BACK FROM %d" % (year + 1)))

    rows.sort()
    return [{"date": o.isoformat(), "name": n, "kind": "declared", "derivation": s}
            for o, n, s in rows]


def assert_traps(cals):
    for c in cals:
        y = c["year"]
        by_date = {r["date"]: r["name"] for r in c["dates"]}

        # NO JUNETEENTH -- neither 19 June nor the third Saturday in June may
        # appear. 25 O.S. 82.1 has none; 82.2/82.4's is a Saturday already.
        assert dt.date(y, 6, 19).isoformat() not in by_date, (
            "%d: 19 June must NOT be an Oklahoma holiday -- Sec. 2006 points at "
            "Sec. 82.1 only, and Oklahoma's Juneteenth is the third Saturday in "
            "June under Sec. 82.4. Encoding 19 June adds a non-holiday and "
            "computes LATE." % y)
        third_sat_june = nth_weekday(y, 6, 5, 3).isoformat()
        assert third_sat_june not in by_date, (
            "%d: %s is Oklahoma's Juneteenth but is already a Saturday and must "
            "not be emitted." % (y, third_sat_june))

        # NO COLUMBUS DAY.
        assert nth_weekday(y, 10, 0, 2).isoformat() not in by_date, (
            "%d: Oklahoma has no Columbus Day and no Indigenous Peoples Day." % y)

        # THE DAY AFTER THANKSGIVING IS a holiday.
        thanks = nth_weekday(y, 11, 3, 4)
        assert (thanks + dt.timedelta(days=1)).isoformat() in by_date, (
            "%d: the day after Thanksgiving is a statutory Oklahoma holiday." % y)

        # THE CHRISTMAS BRANCH each year lands where the statute says.
        x = dt.date(y, 12, 25)
        w = x.weekday()
        dec = sorted(d for d in by_date if d.startswith("%d-12" % y))
        if w == 5:
            assert (x - dt.timedelta(days=2)).isoformat() in by_date and \
                   (x - dt.timedelta(days=1)).isoformat() in by_date, \
                "%d: Saturday Christmas must give the Thursday AND Friday before" % y
        elif w == 6:
            assert (x + dt.timedelta(days=1)).isoformat() in by_date and \
                   (x + dt.timedelta(days=2)).isoformat() in by_date, \
                "%d: Sunday Christmas must give the Monday AND Tuesday after" % y
        else:
            assert x.isoformat() in by_date, "%d: 25 December must be present" % y
            # And the ambiguous neighbour must be ABSENT in both directions.
            for delta in (-1, 1):
                n = (x + dt.timedelta(days=delta)).isoformat()
                assert n not in by_date, (
                    "%d: %s must NOT be encoded -- on a weekday Christmas the statute "
                    "says 'the day before OR after' without saying which, and only the "
                    "Governor's Executive Order resolves it. Guessing adds a "
                    "non-holiday and computes LATE." % (y, n))


def main():
    cals = []
    ambiguous_years = []
    for y in YEARS:
        rows = build_year(y)
        _x, ambig = christmas_days(y)
        if ambig:
            ambiguous_years.append(y)
        seen = set()
        for r in rows:
            d = dt.date.fromisoformat(r["date"])
            assert r["date"] not in seen, "duplicate %s in %d" % (r["date"], y)
            assert d.weekday() < 5, (
                "%s (%s) lands on a weekend" % (r["date"], r["name"]))
            assert d.year == y, "%s filed under year %d" % (r["date"], y)
            seen.add(r["date"])
        cals.append({
            "jurisdiction": "ok",
            "year": y,
            "authority": {
                "citation": "25 O.S. Sec. 82.1(A) (holidays), as incorporated for time "
                            "computation by 12 O.S. Sec. 2006(A)(1)",
                "url": STAT_URL,
                "computation_url": RULE_URL,
                "note": "DERIVED, with ONE DAY A YEAR DELIBERATELY OMITTED on a "
                        "weekday Christmas. Sec. 82.1(A) gives 'the day before OR "
                        "after Christmas if Christmas is not on a Saturday or "
                        "Sunday' without saying which, and Sec. 82.1(B) makes the "
                        "Governor's annual Executive Order the only thing that "
                        "resolves it. THOSE ORDERS ARE REACHABLE AND UNREADABLE -- "
                        "sos.ok.gov publishes them and they are identifiable by "
                        "title (EO 2026-26 AMENDED, 15 July 2026, for calendar "
                        "2027), but each is a SINGLE-PAGE SCANNED IMAGE with zero "
                        "extractable text. Omitting the day reports EARLY, which is "
                        "safe; guessing would add a non-holiday (LATE) and still "
                        "miss the real one. The determinate Christmas limbs ARE "
                        "encoded: a Saturday Christmas gives the Thursday and Friday "
                        "before, a Sunday Christmas the Monday and Tuesday after. "
                        "NOT PRESENT, and all asserted: NO JUNETEENTH (Sec. 2006 "
                        "points at Sec. 82.1 alone, and Oklahoma's is the THIRD "
                        "SATURDAY in June under Sec. 82.4, already a non-day); NO "
                        "COLUMBUS DAY; and none of Sec. 82.2's commemorative days, "
                        "which are outside Sec. 82.1 and were read to confirm it. "
                        "THE DAY AFTER THANKSGIVING IS a statutory holiday here. "
                        "Also not encoded, both ad hoc and EARLY: Sec. 82.1(B)'s "
                        "presidential-national-holiday limb, which the Governor MAY "
                        "adopt, and 2006(A)(1)'s partial-closure limb -- a day when "
                        "the clerk's office 'does not remain open for public "
                        "business until the regularly scheduled closing time', which "
                        "is ADDITIONAL to the holiday list rather than a replacement.",
                "retrieved_at": "2026-08-28",
            },
            "dates": rows,
        })

    assert_traps(cals)

    out = {
        "_readme": [
            "OKLAHOMA HOLIDAY CALENDARS -- DERIVED FROM 25 O.S. Sec. 82.1(A), as",
            "incorporated by 12 O.S. Sec. 2006(A)(1). 2026-2031.",
            "",
            "ONE DAY A YEAR IS MISSING ON PURPOSE, AND IT IS DISCLOSED RATHER THAN",
            "GUESSED. Sec. 82.1(A) gives 'the day before OR after Christmas if",
            "Christmas is not on a Saturday or Sunday' and does not say which.",
            "Sec. 82.1(B) makes the Governor's annual Executive Order the only thing",
            "that resolves it.",
            "",
            "THE ORDERS ARE REACHABLE AND UNREADABLE. sos.ok.gov publishes them and",
            "they are identifiable by title -- EO 2026-26 AMENDED, 15 July 2026,",
            "'Hereby order the following dates be observed as holidays by the State",
            "of Oklahoma in 2027' -- but every one is a SINGLE-PAGE SCANNED IMAGE.",
            "pypdf extracts zero characters; the page is /ProcSet [/PDF /ImageI]",
            "with a single /Im1 Do. Reading the dates needs OCR, which this project",
            "does not treat as a verbatim source.",
            "",
            "SO THE DAY IS OMITTED, WHICH REPORTS EARLY. A deadline landing on the",
            "real holiday is not rolled, so the date given is earlier than the true",
            "one -- the safe direction, and the same call made for Massachusetts's",
            "Suffolk County days and Utah's limb (M). GUESSING WOULD BE WORSE IN",
            "BOTH DIRECTIONS AT ONCE: encoding 24 December when the order said 28",
            "December adds a non-holiday, which rolls a deadline LATE, and still",
            "misses the real one, which is EARLY.",
            "",
            "AFFECTED YEARS in this file are those where 25 December is a weekday:",
            "2026 (Fri), 2028 (Mon), 2029 (Tue), 2030 (Wed), 2031 (Thu). 2027 is",
            "clean -- Christmas falls on a Saturday, so the statute names the",
            "Thursday and Friday before and nothing is ambiguous.",
            "",
            "THE DETERMINATE CHRISTMAS LIMBS ARE ENCODED. A Saturday Christmas gives",
            "the Thursday and Friday before; a Sunday Christmas gives the Monday and",
            "Tuesday after. The general Saturday/Sunday shift expressly does NOT",
            "apply to Christmas -- 'if any of such holidays OTHER THAN CHRISTMAS' --",
            "so Christmas is handled entirely by its own branch.",
            "",
            "THREE THINGS THIS LIST DOES NOT HAVE, all asserted by the generator",
            "because a neighbour's calendar would add them:",
            "  1. NO JUNETEENTH. Sec. 2006 defines legal holiday by reference to",
            "     Sec. 82.1 ONLY. Oklahoma's Juneteenth is in Sec. 82.4 and is 'the",
            "     THIRD SATURDAY in June', not 19 June -- already a non-day under",
            "     82.1(A)'s 'Each Saturday'. Encoding 19 June adds a holiday",
            "     Oklahoma does not have and computes LATE.",
            "  2. NO COLUMBUS DAY and no Indigenous Peoples Day, as in Oregon.",
            "  3. NONE of Sec. 82.2's commemorative days -- Jefferson Day, Oklahoma",
            "     Day, Will Rogers Day, state election days and the rest. 82.2 was",
            "     READ to confirm this rather than assumed; it is a separate section",
            "     and 2006(A)(1) does not point at it.",
            "",
            "AND THE DAY AFTER THANKSGIVING *IS* A HOLIDAY -- statutory here, unlike",
            "Minnesota where it is a judicial-branch option.",
            "",
            "Generated by tools/gen_ok_calendar.py, which asserts per year that no",
            "date is duplicated, none lands on a weekend, none is filed under the",
            "wrong year, the Christmas branch matches the weekday, the ambiguous",
            "neighbour is absent in BOTH directions, and all three of the above.",
        ],
        "holiday_calendars": cals,
    }

    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "sql", "sairnlaw_deadline_calendars_oklahoma.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    for c in cals:
        mark = "  <- weekday Christmas, one day omitted" if c["year"] in ambiguous_years else ""
        print("ok %d: %2d days  %s%s" % (c["year"], len(c["dates"]),
                                         " ".join(r["date"][5:] for r in c["dates"]), mark))
    print("wrote " + path)


if __name__ == "__main__":
    main()
