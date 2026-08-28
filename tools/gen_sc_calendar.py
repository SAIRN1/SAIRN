"""Generate sql/sairnlaw_deadline_calendars_southcarolina.json, 2026-2031.

THE FIRST STATE-PLUS-FEDERAL UNION IN THIS PLATFORM.

SCRCP 6(a) rolls the last day "unless it is a Saturday, Sunday OR A STATE OR
FEDERAL HOLIDAY". Every jurisdiction seeded before this keys on ONE list, or on
two *state* lists (Wisconsin). South Carolina needs the federal list as a
co-equal source, and it matters concretely: JUNETEENTH AND COLUMBUS DAY ARE
FEDERAL HOLIDAYS AND ARE NOT IN S.C. Code Sec. 53-5-10. Encoding only the state
list would miss both and report EARLY -- safe, but wrong, and the union is not
optional.

THE THREE-DAY CHRISTMAS BLOCK COLLIDES UNDER THE SHIFT, IN HALF THE YEARS.
Sec. 53-5-10 makes 24, 25 AND 26 December legal holidays -- no other seeded
jurisdiction has three consecutive statutory Christmas days -- and Sec. 53-5-30
shifts each of them both ways. Two of the three then land on the same observed
date in 2026, 2027 and 2028. The generator DEDUPLICATES rather than emitting a
duplicate or dropping a real day, and assert_christmas_block() checks each year.

2027 is the year worth looking at: 24 December is a Friday and stays, 25
December is a Saturday and its observance merges BACKWARD onto the 24th, and 26
December is a Sunday and moves FORWARD to Monday the 27th. Observed set
{12-24, 12-27} -- Christmas Day itself is not an emitted date at all.

TWO CAVEATS ON Sec. 53-5-30 THAT THIS FILE CANNOT RESOLVE, both recorded for the
bundled holiday question rather than guessed at:

  1. "FOR ALL OF THE PURPOSES AFORESAID". Sec. 53-5-30 is captioned "...effect
     on presentment of bills, notes, and checks" and its second sentence is
     entirely about negotiable instruments. Whether "the purposes aforesaid"
     reaches COURT DEADLINES is arguable on the text. This generator applies the
     shift, because not applying it would drop real observed holidays and report
     EARLY on a day the courts are shut -- but it is an assumption, not a
     reading.
  2. Sec. 53-5-30 SHIFTS ONLY "the holidays mentioned in Section 53-5-10" --
     the STATE half. The federal half has its own observance rule, 5 U.S.C.
     Sec. 6103(b). CHECKED: both are Saturday -> preceding Friday and Sunday ->
     following Monday, so they agree and one function serves both. Recorded as a
     checked negative rather than an unexamined assumption, because if they ever
     diverge this file needs two shift rules for two halves of one union.

Sources, both free on plain curl:
  SCRCP 6      sccourts.org/resources/judicial-community/court-rules/civil/rule-6/
  Sec. 53-5-10 scstatehouse.gov/code/t53c005.php

ACCESS TRAP, recorded so it is not rediscovered: the obvious-looking
sccourts.org/courtReg/displayRule.cfm?ruleID=6.0&ruleType=RCP returns HTTP 200
and 458 KB -- and the body is a navigation index of every rule in every body of
rules, containing none of "Computation", "intermediate Saturdays" or "shall not
be included". A 200 with a large payload is not proof you fetched what you asked
for.

Run: python tools/gen_sc_calendar.py
"""

import datetime as dt
import json
import os

YEARS = [2026, 2027, 2028, 2029, 2030, 2031]

RULE_URL = "https://www.sccourts.org/resources/judicial-community/court-rules/civil/rule-6/"
STAT_URL = "https://www.scstatehouse.gov/code/t53c005.php"

# S.C. Code 53-5-10 -- fixed dates. Note THREE consecutive December days.
STATE_FIXED = [
    ("New Year's Day", (1, 1), "S.C. Code 53-5-10 the first day of January"),
    ("Confederate Memorial Day", (5, 10), "S.C. Code 53-5-10 the tenth day of May -- a fixed-date STATE holiday no other seeded jurisdiction has"),
    ("Independence Day", (7, 4), "S.C. Code 53-5-10 the fourth day of July"),
    ("Veterans Day", (11, 11), "S.C. Code 53-5-10 the eleventh day of November"),
    ("Christmas Eve", (12, 24), "S.C. Code 53-5-10 the twenty-fourth day of December"),
    ("Christmas Day", (12, 25), "S.C. Code 53-5-10 the twenty-fifth day of December"),
    ("Day after Christmas", (12, 26), "S.C. Code 53-5-10 the twenty-sixth day of December"),
]

# 5 U.S.C. 6103 -- the federal holidays NOT in 53-5-10. Every other federal day
# is already in the state list.
FEDERAL_FIXED = [
    ("Juneteenth National Independence Day", (6, 19),
     "5 U.S.C. 6103(a) June 19 -- FEDERAL ONLY, absent from S.C. Code 53-5-10, and reached "
     "because SCRCP 6(a) counts 'a State OR Federal holiday'"),
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


def shift(d):
    """S.C. Code 53-5-30 for the state half; 5 U.S.C. 6103(b) for the federal
    half. CHECKED to be identical -- Saturday to the preceding Friday, Sunday to
    the following Monday -- so one function serves both. See the module
    docstring for why that check matters."""
    w = d.weekday()
    if w == 6:
        return d + dt.timedelta(days=1), "S.C. Code 53-5-30 / 5 U.S.C. 6103(b) Sunday -> the Monday next following"
    if w == 5:
        return d - dt.timedelta(days=1), "S.C. Code 53-5-30 / 5 U.S.C. 6103(b) Saturday -> the Friday next preceding"
    return d, ""


def weekday_rule_days(year):
    thanks = nth_weekday(year, 11, 3, 4)
    return [
        (nth_weekday(year, 1, 0, 3), "Martin Luther King, Jr. Day",
         "S.C. Code 53-5-10 the third Monday of January"),
        (nth_weekday(year, 2, 0, 3), "George Washington's Birthday / Presidents' Day",
         "S.C. Code 53-5-10 the third Monday in February"),
        (last_weekday(year, 5, 0), "National Memorial Day",
         "S.C. Code 53-5-10 the last Monday of May"),
        (nth_weekday(year, 9, 0, 1), "Labor Day",
         "S.C. Code 53-5-10 the first Monday in September"),
        (nth_weekday(year, 10, 0, 2), "Columbus Day",
         "5 U.S.C. 6103(a) the second Monday in October -- FEDERAL ONLY, absent from "
         "S.C. Code 53-5-10, reached because SCRCP 6(a) counts a State OR Federal holiday"),
        (thanks, "National Thanksgiving Day",
         "S.C. Code 53-5-10 National Thanksgiving Day"),
        (thanks + dt.timedelta(days=1), "Day after Thanksgiving",
         "S.C. Code 53-5-10 'and the day after' -- in the STATUTE itself, where Minnesota "
         "leaves it to a branch option"),
    ]


def build_year(year):
    rows = {}

    def add(d, name, src):
        """DEDUPLICATE. The three-day Christmas block collides under the shift
        in half the years -- two statutory days landing on one observed date --
        and a duplicate would be rejected by the loader while dropping one
        would lose a real holiday. First writer wins and the derivation records
        the merge."""
        key = d.isoformat()
        if key in rows:
            rows[key]["derivation"] += " || ALSO observed here: " + name + " (" + src + ")"
            return
        rows[key] = {"date": key, "name": name, "kind": "declared", "derivation": src}

    for name, (m, d), src in STATE_FIXED + FEDERAL_FIXED:
        obs, sh = shift(dt.date(year, m, d))
        if obs.year != year:
            continue
        add(obs, name, src + ("; " + sh if sh else ""))
    for d, name, src in weekday_rule_days(year):
        add(d, name, src)

    # SPILL: a fixed-date holiday in the next year observed in this one.
    for name, (m, d), src in STATE_FIXED + FEDERAL_FIXED:
        obs, sh = shift(dt.date(year + 1, m, d))
        if obs.year == year:
            add(obs, "%s (%d, observed early)" % (name, year + 1),
                src + "; " + sh + " -- SPILLS BACK FROM %d" % (year + 1))

    return [rows[k] for k in sorted(rows)]


def assert_traps(cals):
    for c in cals:
        y = c["year"]
        by_date = {r["date"]: r["name"] for r in c["dates"]}

        # THE UNION IS NOT OPTIONAL. Both federal-only days must be present.
        june, _ = shift(dt.date(y, 6, 19))
        assert june.isoformat() in by_date, (
            "%d: JUNETEENTH (%s) is missing. It is a FEDERAL holiday and is NOT in "
            "S.C. Code 53-5-10, but SCRCP 6(a) counts 'a State OR Federal holiday'. "
            "Omitting it reports EARLY." % (y, june))
        columbus = nth_weekday(y, 10, 0, 2).isoformat()
        assert columbus in by_date, (
            "%d: COLUMBUS DAY (%s) is missing -- federal-only, same reasoning as "
            "Juneteenth. South Carolina is NOT Oregon or Oklahoma here." % (y, columbus))

        # THE TWO STATE-ONLY DAYS no other seeded jurisdiction has.
        cmd, _ = shift(dt.date(y, 5, 10))
        assert cmd.isoformat() in by_date, (
            "%d: Confederate Memorial Day (10 May, observed %s) is missing." % (y, cmd))
        thanks = nth_weekday(y, 11, 3, 4)
        assert (thanks + dt.timedelta(days=1)).isoformat() in by_date, (
            "%d: the day after Thanksgiving is in the STATUTE here." % y)

        # THE CHRISTMAS BLOCK: every one of the three statutory days must be
        # accounted for -- either as its own observed date or merged into
        # another -- and no observed date may be duplicated.
        observed = {shift(dt.date(y, 12, d))[0].isoformat() for d in (24, 25, 26)}
        for o in observed:
            assert o in by_date, (
                "%d: %s is an observed December holiday and is missing -- the "
                "three-day block must not lose a day to deduplication." % (y, o))
        assert len(c["dates"]) == len(set(r["date"] for r in c["dates"])), \
            "%d: duplicate observed dates emitted" % y


def main():
    cals = []
    collided = []
    for y in YEARS:
        rows = build_year(y)
        observed = {shift(dt.date(y, 12, d))[0] for d in (24, 25, 26)}
        if len(observed) < 3:
            collided.append(y)
        for r in rows:
            d = dt.date.fromisoformat(r["date"])
            assert d.weekday() < 5, "%s (%s) lands on a weekend" % (r["date"], r["name"])
            assert d.year == y, "%s filed under year %d" % (r["date"], y)
        cals.append({
            "jurisdiction": "sc",
            "year": y,
            "authority": {
                "citation": "S.C. Code Sec. 53-5-10 (state holidays) UNION 5 U.S.C. Sec. 6103 "
                            "(federal holidays), as required by S.C. R. Civ. P. 6(a)'s "
                            "\"a State or Federal holiday\", with the observance shift in "
                            "S.C. Code Sec. 53-5-30",
                "url": STAT_URL,
                "computation_url": RULE_URL,
                "note": "THE FIRST STATE-PLUS-FEDERAL UNION IN THIS PLATFORM. SCRCP "
                        "6(a) rolls on 'a Saturday, Sunday OR A STATE OR FEDERAL "
                        "holiday', so the federal list is a CO-EQUAL SOURCE rather "
                        "than a fallback. JUNETEENTH AND COLUMBUS DAY ARE FEDERAL "
                        "ONLY -- neither is in S.C. Code 53-5-10 -- and omitting "
                        "either reports EARLY. Both are asserted by the generator. "
                        "THE THREE-DAY CHRISTMAS BLOCK (24, 25 AND 26 December, "
                        "unique among seeded jurisdictions) COLLIDES under the "
                        "53-5-30 shift in 2026, 2027 and 2028, where two statutory "
                        "days land on one observed date; the generator deduplicates "
                        "and records the merge in the derivation rather than "
                        "emitting a duplicate or dropping a day. In 2027 CHRISTMAS "
                        "DAY ITSELF IS NOT AN EMITTED DATE: 25 December is a "
                        "Saturday, so its observance merges backward onto the 24th, "
                        "and 26 December moves forward to Monday the 27th. TWO "
                        "CAVEATS THIS FILE CANNOT RESOLVE, both sent to the bundled "
                        "holiday question: (1) 53-5-30 is captioned 'effect on "
                        "presentment of bills, notes, and checks' and shifts 'for "
                        "all of the purposes aforesaid', so whether it reaches COURT "
                        "deadlines is arguable -- the shift is APPLIED here because "
                        "not applying it would report EARLY on days the courts are "
                        "shut, but that is an assumption; (2) 53-5-30 by its terms "
                        "shifts only the STATE half, and the federal half has "
                        "5 U.S.C. 6103(b) -- CHECKED to be identical both ways, so "
                        "one rule serves both, recorded as a checked negative in "
                        "case they ever diverge. Also not encoded: SCRCP 6(a)'s "
                        "'A half holiday shall be considered as other days and not "
                        "as a holiday' -- inert today because nothing in 53-5-10 is "
                        "a half holiday, but it is the rule pre-emptively refusing a "
                        "category and must not be quietly dropped.",
                "retrieved_at": "2026-08-28",
            },
            "dates": rows,
        })

    assert_traps(cals)

    out = {
        "_readme": [
            "SOUTH CAROLINA HOLIDAY CALENDARS -- S.C. Code Sec. 53-5-10 UNION",
            "5 U.S.C. Sec. 6103, shifted by Sec. 53-5-30. 2026-2031.",
            "",
            "THE FIRST STATE-PLUS-FEDERAL UNION IN THIS PLATFORM. SCRCP 6(a) rolls",
            "the last day 'unless it is a Saturday, Sunday OR A STATE OR FEDERAL",
            "holiday'. Every jurisdiction seeded before this keys on one list, or on",
            "two STATE lists (Wisconsin). Here the federal list is a co-equal source.",
            "",
            "IT MATTERS CONCRETELY: JUNETEENTH AND COLUMBUS DAY ARE FEDERAL HOLIDAYS",
            "AND ARE NOT IN Sec. 53-5-10. A calendar built from the state statute",
            "alone would miss both and report EARLY. Both are asserted.",
            "",
            "THE THREE-DAY CHRISTMAS BLOCK -- 24, 25 AND 26 December, which no other",
            "seeded jurisdiction has -- COLLIDES UNDER THE SHIFT IN HALF THE YEARS.",
            "Sec. 53-5-30 moves each of the three both ways, and two of them land on",
            "one observed date in 2026, 2027 and 2028. The generator DEDUPLICATES,",
            "recording the merge in the derivation, rather than emitting a duplicate",
            "(which the loader rejects) or dropping a day (which loses a holiday).",
            "",
            "2027 IS THE YEAR WORTH LOOKING AT. 24 December is a Friday and stays; 25",
            "December is a Saturday, so its observance merges BACKWARD onto the 24th;",
            "26 December is a Sunday and moves FORWARD to Monday the 27th. The",
            "observed set is {12-24, 12-27} and CHRISTMAS DAY ITSELF IS NOT AN",
            "EMITTED DATE.",
            "",
            "TWO CAVEATS ON Sec. 53-5-30, both recorded rather than resolved:",
            "  1. It is captioned 'effect on presentment of bills, notes, and checks'",
            "     and shifts 'for all of the purposes aforesaid'; its second sentence",
            "     is entirely about negotiable instruments. Whether that reaches",
            "     COURT deadlines is arguable on the text. THE SHIFT IS APPLIED HERE,",
            "     because not applying it would report EARLY on days the courts are",
            "     actually shut -- but it is an assumption, not a reading, and it",
            "     belongs with the bundled holiday question.",
            "  2. It shifts only 'the holidays mentioned in Section 53-5-10' -- the",
            "     STATE half. The federal half has 5 U.S.C. Sec. 6103(b). CHECKED:",
            "     both are Saturday -> preceding Friday and Sunday -> following",
            "     Monday, so one function serves both. Recorded as a CHECKED",
            "     NEGATIVE, because if they ever diverge this file needs two shift",
            "     rules for two halves of one union -- which no seeded generator has.",
            "",
            "TWO STATE-ONLY DAYS no other seeded jurisdiction has: CONFEDERATE",
            "MEMORIAL DAY (10 May, a fixed date) and THE DAY AFTER THANKSGIVING, in",
            "the statute itself where Minnesota leaves it to a branch option.",
            "",
            "NOT ENCODED: SCRCP 6(a)'s 'A half holiday shall be considered as other",
            "days and not as a holiday'. Inert today -- nothing in Sec. 53-5-10 is a",
            "half holiday -- but it is the rule pre-emptively refusing a category and",
            "is recorded rather than dropped.",
            "",
            "Generated by tools/gen_sc_calendar.py, which asserts per year that no",
            "date lands on a weekend or in the wrong year, that no observed date is",
            "duplicated, that every one of the three statutory December days is",
            "accounted for, and that Juneteenth, Columbus Day, Confederate Memorial",
            "Day and the day after Thanksgiving are all present.",
        ],
        "holiday_calendars": cals,
    }

    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "sql", "sairnlaw_deadline_calendars_southcarolina.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    for c in cals:
        mark = "  <- Christmas block collides" if c["year"] in collided else ""
        print("sc %d: %2d days  %s%s" % (c["year"], len(c["dates"]),
                                         " ".join(r["date"][5:] for r in c["dates"]), mark))
    print("wrote " + path)


if __name__ == "__main__":
    main()
