"""Generate sql/sairnlaw_deadline_calendars_nevada.json, 2026-2031.

SIX YEARS, unlike Utah's one. Utah is capped at 2026 because Utah Code
63G-1-301 is superseded 1/1/2027 and moves Juneteenth. Nevada has no such
pending change: NRS 236.015's amendment trail ends at "2023, 1463", the chapter
header stamps [Rev. 4/15/2026 --2025], and nothing in it is marked superseded.
Checked before choosing the range rather than assumed from Minnesota's.

NRCP 6(a)(6) is a clean single pointer -- '"Legal holiday" means any day set
aside as a legal holiday by NRS 236.015' -- so unlike Utah there is no in-rule
list to reconcile against the statute. NRS 236.015(1) holds the list and (3)
holds the observation shift. Both halves in one statute: Nevada is the cleanest
derive-not-ingest position of any seeded jurisdiction.

THREE TRAPS OF ANALOGY, asserted below rather than trusted:

  1. THERE IS NO COLUMBUS DAY. NRS 236.025 files it under PERIODS OF
     OBSERVANCE, not HOLIDAYS. Utah and West Virginia both make it a legal
     holiday and the federal calendar has it, so a calendar copied from a
     neighbour would roll a deadline off a normal Nevada business day -- LATE,
     the direction that loses a filing. Same for Indigenous Peoples Day
     (236.037) and Cesar Chavez Day (236.027).
  2. JUNETEENTH IS JUNE 19, A FIXED DATE -- not the third Monday. Utah's URCP
     6(a)(6)(E) uses the third Monday, and in 2026 the two states are FOUR DAYS
     APART: Nevada 2026-06-19, Utah 2026-06-15.
  3. NEVADA DAY (31 October, observed the last Friday in October) and FAMILY
     DAY (the Friday following the fourth Thursday in November). No other
     seeded state has either. Family Day is exactly what an analogy-driven
     calendar drops, since most states treat the day after Thanksgiving as an
     ordinary business day.

Sources, both free on a bare curl -- no user-agent, no Accept header:
  NRCP 6      leg.state.nv.us/courtrules/NRCP.html
  NRS 236.015 leg.state.nv.us/NRS/NRS-236.html

Run: python tools/gen_nv_calendar.py
"""

import datetime as dt
import json
import os

YEARS = [2026, 2027, 2028, 2029, 2030, 2031]

RULE_URL = "https://www.leg.state.nv.us/courtrules/NRCP.html"
STAT_URL = "https://www.leg.state.nv.us/NRS/NRS-236.html"

# NRS 236.015(3) enumerates the shift to EXACTLY these five dates. Every other
# listed holiday is defined by a weekday rule and can never fall on a weekend,
# so the enumeration is complete in practice -- but it is enumerated, not
# general, and a sixth fixed-date holiday added later would NOT inherit it.
SHIFTED = [
    ("New Year's Day", (1, 1), "NRS 236.015(1) January 1"),
    ("Juneteenth Day", (6, 19), "NRS 236.015(1) June 19 -- A FIXED DATE, not the third Monday"),
    ("Independence Day", (7, 4), "NRS 236.015(1) July 4"),
    ("Veterans Day", (11, 11), "NRS 236.015(1) November 11"),
    ("Christmas Day", (12, 25), "NRS 236.015(1) December 25"),
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
    """NRS 236.015(3): Sunday -> the following Monday; Saturday -> the
    PRECEDING Friday. A both-ways shift, so it can move a holiday out of its
    own calendar year -- 1 January 2028 is a Saturday and is observed
    2027-12-31. Handled by the spill pass in build_year(), not ignored."""
    w = d.weekday()
    if w == 6:
        return d + dt.timedelta(days=1), "NRS 236.015(3)(a) Sunday -> following Monday"
    if w == 5:
        return d - dt.timedelta(days=1), "NRS 236.015(3)(b) Saturday -> preceding Friday"
    return d, ""


def weekday_rule_days(year):
    thanksgiving = nth_weekday(year, 11, 3, 4)
    return [
        (nth_weekday(year, 1, 0, 3), "Martin Luther King, Jr. Day",
         "NRS 236.015(1) observed the third Monday in January"),
        (nth_weekday(year, 2, 0, 3), "Washington's Birthday",
         "NRS 236.015(1) observed the third Monday in February"),
        (last_weekday(year, 5, 0), "Memorial Day",
         "NRS 236.015(1) last Monday in May"),
        (nth_weekday(year, 9, 0, 1), "Labor Day",
         "NRS 236.015(1) first Monday in September"),
        (last_weekday(year, 10, 4), "Nevada Day",
         "NRS 236.015(1) October 31 but observed the LAST FRIDAY IN OCTOBER "
         "-- Nevada-specific, no other seeded state has it"),
        (thanksgiving, "Thanksgiving Day",
         "NRS 236.015(1) fourth Thursday in November"),
        (thanksgiving + dt.timedelta(days=1), "Family Day",
         "NRS 236.015(1) the Friday FOLLOWING the fourth Thursday in November "
         "-- Nevada-specific; most states treat this as an ordinary business day"),
    ]


def build_year(year):
    rows = []
    for name, (m, d), src in SHIFTED:
        obs, shift = observed(dt.date(year, m, d))
        if obs.year != year:
            continue  # belongs to the previous year's calendar; handled below
        rows.append((obs, name, src + ("; " + shift if shift else "")))
    rows.extend(weekday_rule_days(year))

    # SPILL: a fixed-date holiday in the NEXT year can be observed in THIS one.
    # 1 January 2028 falls on a Saturday -> observed 2027-12-31.
    for name, (m, d), src in SHIFTED:
        obs, shift = observed(dt.date(year + 1, m, d))
        if obs.year == year:
            rows.append((obs, "%s (%d, observed early)" % (name, year + 1),
                         src + "; " + shift + " -- SPILLS BACK FROM %d" % (year + 1)))

    rows.sort()
    return [{"date": o.isoformat(), "name": n, "kind": "declared", "derivation": s}
            for o, n, s in rows]


def assert_traps(cals):
    """The three traps of analogy, asserted rather than trusted. Each of these
    would be a silent wrong date if a future edit copied a neighbour's list."""
    for c in cals:
        y = c["year"]
        by_date = {r["date"]: r["name"] for r in c["dates"]}
        names = set(by_date.values())

        # 1. NO COLUMBUS DAY -- the only LATE-direction trap here.
        columbus = nth_weekday(y, 10, 0, 2).isoformat()
        assert columbus not in by_date, (
            "%s: Columbus Day (%s) must NOT be a Nevada holiday -- NRS 236.025 "
            "files it under PERIODS OF OBSERVANCE. Encoding it rolls a deadline "
            "off a normal business day, which is LATE." % (y, columbus))

        # 2. Juneteenth is the fixed date (as observed), never the third Monday
        #    unless the two genuinely coincide.
        june19 = observed(dt.date(y, 6, 19))[0].isoformat()
        third_mon = nth_weekday(y, 6, 0, 3).isoformat()
        assert by_date.get(june19) == "Juneteenth Day", (
            "%s: Juneteenth must sit on the observed 19 June (%s), not %s "
            "(Utah's third-Monday rule)." % (y, june19, third_mon))
        if third_mon != june19:
            assert third_mon not in by_date, (
                "%s: %s is Utah's Juneteenth, not Nevada's -- it must not appear."
                % (y, third_mon))

        # 3. The two Nevada-specific days are present.
        assert "Nevada Day" in names, "%s: Nevada Day missing" % y
        assert "Family Day" in names, "%s: Family Day missing" % y
        thanks = nth_weekday(y, 11, 3, 4)
        assert by_date.get((thanks + dt.timedelta(days=1)).isoformat()) == "Family Day", (
            "%s: Family Day must be the Friday after Thanksgiving" % y)


def main():
    cals = []
    for y in YEARS:
        rows = build_year(y)
        seen = set()
        for r in rows:
            d = dt.date.fromisoformat(r["date"])
            assert r["date"] not in seen, "duplicate %s in %d" % (r["date"], y)
            assert d.weekday() < 5, (
                "%s (%s) lands on a weekend -- the NRS 236.015(3) shift is wrong"
                % (r["date"], r["name"]))
            assert d.year == y, "%s filed under year %d" % (r["date"], y)
            seen.add(r["date"])
        cals.append({
            "jurisdiction": "nv",
            "year": y,
            "authority": {
                "citation": "NRS 236.015 (legal holidays and their observation), "
                            "as incorporated for time computation by Nev. R. Civ. P. 6(a)(6)",
                "url": STAT_URL,
                "computation_url": RULE_URL,
                "note": "EVERY DATE HERE IS DERIVED, not transcribed. NRCP "
                        "6(a)(6) is a clean single pointer -- \"'Legal holiday' "
                        "means any day set aside as a legal holiday by NRS "
                        "236.015\" -- so unlike Utah there is no in-rule list to "
                        "reconcile against the statute. NRS 236.015(1) holds the "
                        "list; (3) holds a BOTH-WAYS shift ENUMERATED to exactly "
                        "five fixed dates (Jan 1, Jun 19, Jul 4, Nov 11, Dec 25), "
                        "which is complete in practice because every other listed "
                        "day is a weekday rule. THREE TRAPS, asserted by the "
                        "generator: (1) THERE IS NO COLUMBUS DAY -- NRS 236.025 "
                        "files it under PERIODS OF OBSERVANCE, and encoding it "
                        "would roll a deadline off a normal business day, which "
                        "is LATE; (2) JUNETEENTH IS JUNE 19, not Utah's third "
                        "Monday -- the two states are four days apart in 2026; "
                        "(3) NEVADA DAY (last Friday in October) and FAMILY DAY "
                        "(the Friday after Thanksgiving) exist here and nowhere "
                        "else in this platform. NOT ENCODED, ad hoc and EARLY: "
                        "presidentially appointed days of public fast or "
                        "thanksgiving, and NRCP 6(a)(3)'s clerk-inaccessibility "
                        "limb, which is ADDITIONAL to the rollover rather than a "
                        "replacement for it.",
                "retrieved_at": "2026-08-27",
            },
            "dates": rows,
        })

    assert_traps(cals)

    out = {
        "_readme": [
            "NEVADA HOLIDAY CALENDARS -- DERIVED FROM NRS 236.015, as incorporated",
            "by Nev. R. Civ. P. 6(a)(6). 2026-2031.",
            "",
            "SIX YEARS, and the range was CHECKED rather than copied from",
            "Minnesota. Utah's calendar stops at 2026 because Utah Code 63G-1-301",
            "is superseded 1/1/2027 and moves Juneteenth. Nevada has no pending",
            "change: NRS 236.015's amendment trail ends at \"2023, 1463\", the",
            "chapter header stamps [Rev. 4/15/2026 --2025], and nothing in it is",
            "marked superseded.",
            "",
            "NEVADA IS THE CLEANEST DERIVE-NOT-INGEST POSITION IN THE PLATFORM.",
            "NRCP 6(a)(6) is a single pointer at the statute, so there is no",
            "in-rule list to reconcile -- which is exactly what made Utah's",
            "Juneteenth question messy. NRS 236.015(1) holds the list and (3)",
            "holds the observation shift.",
            "",
            "THE SHIFT IS BOTH-WAYS BUT ENUMERATED, to exactly five fixed dates:",
            "January 1, June 19, July 4, November 11 and December 25. Sunday ->",
            "the following Monday; Saturday -> the PRECEDING Friday. It is",
            "complete in practice because every other listed holiday is defined by",
            "a weekday rule and can never land on a weekend -- but it is an",
            "ENUMERATION, so a sixth fixed-date holiday added by a later",
            "legislature would NOT inherit it.",
            "",
            "IT SPILLS ACROSS THE YEAR BOUNDARY: 1 January 2028 is a Saturday, so",
            "it is observed 2027-12-31 and belongs in the 2027 calendar. A year",
            "built only from its own holidays would be missing it.",
            "",
            "THREE TRAPS OF ANALOGY, ASSERTED BY THE GENERATOR RATHER THAN TRUSTED",
            "-- assert_traps() fails the build if any of them regresses:",
            "  1. THERE IS NO COLUMBUS DAY. NRS 236.025 files it under PERIODS OF",
            "     OBSERVANCE, not HOLIDAYS. Utah and West Virginia both make it a",
            "     legal holiday and the federal calendar has it. This is the only",
            "     LATE-direction trap here: encoding it rolls a deadline off a day",
            "     that is a normal Nevada business day.",
            "  2. JUNETEENTH IS JUNE 19, A FIXED DATE. Utah uses the third Monday.",
            "     In 2026 the two states are FOUR DAYS APART -- NV 2026-06-19,",
            "     UT 2026-06-15 -- and the two were gated a day apart.",
            "  3. NEVADA DAY (31 October, observed the last Friday in October) and",
            "     FAMILY DAY (the Friday after Thanksgiving). No other seeded state",
            "     has either. Missing them reports EARLY, which is safe, but Family",
            "     Day is exactly what an analogy-driven calendar drops.",
            "",
            "Generated by tools/gen_nv_calendar.py, which asserts per year that no",
            "date is duplicated, none lands on a weekend, none is filed under the",
            "wrong year, and that all three traps above still hold.",
        ],
        "holiday_calendars": cals,
    }

    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "sql", "sairnlaw_deadline_calendars_nevada.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    for c in cals:
        print("nv %d: %d days  %s" % (c["year"], len(c["dates"]),
                                      " ".join(r["date"][5:] for r in c["dates"])))
    print("wrote " + path)


if __name__ == "__main__":
    main()
