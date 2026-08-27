"""Generate sql/sairnlaw_deadline_calendars_utah.json.

ONE YEAR ONLY -- 2026 -- AND THAT IS THE POINT, NOT AN OVERSIGHT.

Utah Code 63G-1-301 is SUPERSEDED 1/1/2027. The successor version moves
Juneteenth out of subsection (1)(b)(ix) into (1)(a)(ii) and DELETES its bespoke
(2)(c)/(2)(d) Monday-shifting rules. URCP 6(a)(6)(E) describes Juneteenth as
"the third Monday of June", which this script verifies is EXACTLY equivalent to
the CURRENT statutory formula in every year 2024-2032 -- and which the 1/1/2027
amendment makes wrong in eight of the next nine years. 2027 alone is three days
apart: the rule's text gives 2027-06-21, the amended statute gives 2027-06-18.

That divergence fails in BOTH directions in the same year, and one of them is
LATE. So the calendar stops at 2026-12-31 and the engine's own missing-year
refusal (holidayFor -> known: false -> NOT_PROVISIONED) blocks every 2027+
Utah computation until a human decides which reading of Juneteenth governs.
DO NOT EXTEND THIS CALENDAR TO 2027 WITHOUT ANSWERING THAT QUESTION.

Sources, both free on a bare curl:
  URCP 6(a)(6)  legacy.utcourts.gov/rules/view.php?type=urcp&rule=6
  63G-1-301     le.utah.gov/xcode/Title63G/Chapter1/C63G-1-P3_1800010118000101.pdf

Run: python tools/gen_ut_calendar.py
"""

import datetime as dt
import json
import os

YEARS = [2026]  # see the module docstring before adding to this list

RULE_URL = "https://legacy.utcourts.gov/rules/view.php?type=urcp&rule=6"
STAT_URL = ("https://le.utah.gov/xcode/Title63G/Chapter1/"
            "C63G-1-P3_1800010118000101.pdf")


def nth_weekday(year, month, weekday, n):
    """n-th (1-based) `weekday` of `month`. Monday=0."""
    days = [d for d in _month_days(year, month) if d.weekday() == weekday]
    return days[n - 1]


def last_weekday(year, month, weekday):
    return [d for d in _month_days(year, month) if d.weekday() == weekday][-1]


def _month_days(year, month):
    d = dt.date(year, month, 1)
    out = []
    while d.month == month:
        out.append(d)
        d += dt.timedelta(days=1)
    return out


def observed_fixed(d):
    """63G-1-301(2)(a)/(b): the observation shift for a FIXED-DATE holiday.

    Saturday -> the PRECEDING Friday. Sunday -> the FOLLOWING Monday. This is a
    BOTH-WAYS shift, so it can move a holiday out of its own calendar year --
    New Year's Day 2028 falls on a Saturday and is observed 2027-12-31. Handled
    by spill_into() rather than ignored.
    """
    w = d.weekday()
    if w == 5:
        return d - dt.timedelta(days=1), "63G-1-301(2)(a) Saturday -> preceding Friday"
    if w == 6:
        return d + dt.timedelta(days=1), "63G-1-301(2)(b) Sunday -> following Monday"
    return d, ""


def juneteenth_current(year):
    """63G-1-301(1)(b)(ix) + (2)(c)/(2)(d), the version in force through 2026.

    June 19; if it falls Tue-Fri the PRECEDING Monday; if Sat/Sun the FOLLOWING
    Monday. Deliberately computed from the statute rather than from URCP
    6(a)(6)(E)'s "third Monday of June" shorthand, so that assert_equivalence()
    below is a real check and not a tautology.
    """
    d = dt.date(year, 6, 19)
    w = d.weekday()
    if 1 <= w <= 4:
        return d - dt.timedelta(days=w)
    if w in (5, 6):
        return d + dt.timedelta(days=7 - w)
    return d


def third_monday_june(year):
    return nth_weekday(year, 6, 0, 3)


def assert_equivalence():
    """URCP 6(a)(6)(E)'s shorthand vs the statute it describes, 2024-2032.

    They agree in every one of those years -- the rule's parenthetical is a
    correct restatement of current law, not a drafting error. Asserted rather
    than assumed, because the whole reason this calendar stops at 2026 is that
    the equivalence BREAKS on 1/1/2027, and a silent change to either formula
    would otherwise go unnoticed.
    """
    for y in range(2024, 2033):
        a, b = third_monday_june(y), juneteenth_current(y)
        assert a == b, (
            "URCP 6(a)(6)(E) 'third Monday of June' (%s) no longer matches "
            "63G-1-301 (%s) for %d -- re-read both before generating." % (a, b, y))


# URCP 6(a)(6) limbs (A)-(L). Limb (M) -- "any day designated by the Governor
# or Legislature" -- is ad hoc and NOT encodable; omitting it can only ever
# report a deadline EARLY. Good Friday and Easter Sunday are statutory holidays
# under 63G-1-301(1)(b)(iii)-(iv) but are NOT among 6(a)(6)'s limbs, and 6(a)(6)
# says "means" rather than "includes" -- so they are omitted too, which is
# likewise the EARLY direction. See the gate document, section 4.
FIXED = [
    ("New Year's Day", (1, 1), "URCP 6(a)(6)(A); 63G-1-301(1)(a)(i) January 1"),
    ("Independence Day", (7, 4), "URCP 6(a)(6)(F); 63G-1-301(1)(a)(ii) July 4"),
    ("Pioneer Day", (7, 24), "URCP 6(a)(6)(G); 63G-1-301(1)(a)(iii) July 24"),
    ("Veterans' Day", (11, 11), "URCP 6(a)(6)(J); 63G-1-301(1)(a)(iv) November 11"),
    ("Christmas", (12, 25), "URCP 6(a)(6)(L); 63G-1-301(1)(a)(v) December 25"),
]

WEEKDAY_RULES = [
    ("Dr. Martin Luther King, Jr. Day", lambda y: nth_weekday(y, 1, 0, 3),
     "URCP 6(a)(6)(B); 63G-1-301(1)(b)(i) third Monday of January"),
    ("Washington and Lincoln Day", lambda y: nth_weekday(y, 2, 0, 3),
     "URCP 6(a)(6)(C); 63G-1-301(1)(b)(ii) third Monday of February "
     "(the statute calls the same day Presidents' Day -- a naming divergence only)"),
    ("Memorial Day", lambda y: last_weekday(y, 5, 0),
     "URCP 6(a)(6)(D); 63G-1-301(1)(b)(v) last Monday of May"),
    ("Juneteenth National Freedom Day", juneteenth_current,
     "URCP 6(a)(6)(E) third Monday of June, verified equal to "
     "63G-1-301(1)(b)(ix) with (2)(c)/(2)(d) for this year"),
    ("Labor Day", lambda y: nth_weekday(y, 9, 0, 1),
     "URCP 6(a)(6)(H); 63G-1-301(1)(b)(vi) first Monday of September"),
    ("Columbus Day", lambda y: nth_weekday(y, 10, 0, 2),
     "URCP 6(a)(6)(I); 63G-1-301(1)(b)(vii) second Monday of October"),
    ("Thanksgiving Day", lambda y: nth_weekday(y, 11, 3, 4),
     "URCP 6(a)(6)(K); 63G-1-301(1)(b)(viii) fourth Thursday of November"),
]


def build_year(year):
    rows = []
    for name, (m, d), src in FIXED:
        obs, shift = observed_fixed(dt.date(year, m, d))
        rows.append((obs, name, src + ("; " + shift if shift else "")))
    for name, fn, src in WEEKDAY_RULES:
        rows.append((fn(year), name, src))

    # SPILL: a fixed-date holiday in the NEXT year can be observed in THIS one
    # (New Year's Day 2028 -> 2027-12-31). Checked rather than assumed; for 2026
    # it finds nothing, because 1 January 2027 is a Friday.
    for name, (m, d), src in FIXED:
        obs, shift = observed_fixed(dt.date(year + 1, m, d))
        if obs.year == year:
            rows.append((obs, name + " (%d, observed early)" % (year + 1),
                         src + "; " + shift + " -- SPILLS BACK FROM %d" % (year + 1)))

    rows.sort()
    return [{"date": o.isoformat(), "name": n, "kind": "declared", "derivation": s}
            for o, n, s in rows]


def main():
    assert_equivalence()
    cals = []
    for y in YEARS:
        dates = build_year(y)
        seen = set()
        for row in dates:
            d = dt.date.fromisoformat(row["date"])
            assert row["date"] not in seen, "duplicate date %s in %d" % (row["date"], y)
            assert d.weekday() < 5, (
                "%s (%s) lands on a weekend -- the observation shift is wrong"
                % (row["date"], row["name"]))
            assert d.year == y, "%s filed under year %d" % (row["date"], y)
            seen.add(row["date"])
        assert len(dates) == 12, "expected 12 observed days for %d, got %d" % (y, len(dates))
        cals.append({
            "jurisdiction": "ut",
            "year": y,
            "authority": {
                "citation": "Utah R. Civ. P. 6(a)(6) (the closed definition of "
                            "\"legal holiday\"), with the observation shift in "
                            "Utah Code 63G-1-301(2)",
                "url": RULE_URL,
                "statute_url": STAT_URL,
                "note": "EVERY DATE HERE IS DERIVED, not transcribed from a "
                        "published schedule -- Utah is the first jurisdiction "
                        "seeded whose holiday list lives INSIDE the rule of "
                        "procedure (URCP 6(a)(6), thirteen limbs, \"means\" not "
                        "\"includes\"), rather than in a statute the rule points "
                        "at or an administrative calendar the court issues. It "
                        "is NOT derivable from the rule ALONE: \"the day for "
                        "OBSERVING\" incorporates 63G-1-301(2)'s both-ways "
                        "Saturday->preceding-Friday / Sunday->following-Monday "
                        "shift. LIMB (M) (\"any day designated by the Governor or "
                        "Legislature\") and 63G-1-301(5) governor's proclamations "
                        "are ad hoc and NOT encoded; so are Good Friday and "
                        "Easter Sunday, which 63G-1-301 makes state holidays but "
                        "6(a)(6) omits. Every one of those omissions can only "
                        "report a deadline EARLY, never late. "
                        "2026 IS THE ONLY YEAR AND THAT IS DELIBERATE -- see "
                        "tools/gen_ut_calendar.py and the gate document.",
                "retrieved_at": "2026-08-27",
            },
            "dates": dates,
        })

    out = {
        "_readme": [
            "UTAH HOLIDAY CALENDARS -- DERIVED FROM URCP 6(a)(6) with the",
            "observation shift in Utah Code 63G-1-301(2). 2026 ONLY.",
            "",
            "ONE YEAR, DELIBERATELY. Every other seeded jurisdiction runs six",
            "years because its holiday list is stable in derivable terms. Utah's",
            "is too -- but 63G-1-301 is SUPERSEDED 1/1/2027, and the successor",
            "moves Juneteenth out of (1)(b)(ix) into (1)(a)(ii) and deletes its",
            "bespoke (2)(c)/(2)(d) Monday rules. URCP 6(a)(6)(E) still describes",
            "it as \"the third Monday of June\".",
            "",
            "That shorthand is EXACTLY RIGHT for the current statute in every",
            "year 2024-2032 -- gen_ut_calendar.py asserts it rather than assuming",
            "it -- and WRONG in eight of the next nine from 1/1/2027. 2027 alone",
            "is three days apart: the rule's text gives 2027-06-21, the amended",
            "statute gives 2027-06-18. Encoding 06-21 would roll a deadline off a",
            "day that is not a holiday, which is LATE -- the direction that loses",
            "a filing.",
            "",
            "So the calendar stops here and the engine's own missing-year refusal",
            "does the rest: holidayFor returns known:false for 2027, rollOff",
            "returns NOT_PROVISIONED, and no Utah date is computed past",
            "2026-12-31. DO NOT ADD 2027 UNTIL A HUMAN DECIDES WHETHER URCP",
            "6(a)(6)(E) MEANS ITS OWN TEXT OR THE STATUTE IT DESCRIBES.",
            "",
            "Generated by tools/gen_ut_calendar.py, which asserts per year that",
            "no date is duplicated, none lands on a weekend, none is filed under",
            "the wrong year, and that exactly 12 observed days are produced.",
        ],
        "holiday_calendars": cals,
    }

    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "sql", "sairnlaw_deadline_calendars_utah.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    for c in cals:
        print("%s %d: %d observed days" % (c["jurisdiction"], c["year"], len(c["dates"])))
        for d in c["dates"]:
            print("   %s  %s" % (d["date"], d["name"]))
    print("wrote " + path)


if __name__ == "__main__":
    main()
