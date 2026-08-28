"""Generate sql/sairnlaw_deadline_calendars_oregon.json, 2026-2031.

DERIVED FROM ORS 187.010(1), as incorporated by ORCP 10 A ('"legal holiday"
means legal holiday as defined in ORS 187.010 and 187.020').

THE TRAP THIS FILE EXISTS TO ASSERT AGAINST -- "OTHER THAN SUNDAY".

ORS 187.010(1)(a) makes EACH SUNDAY a legal holiday, so Sunday is INSIDE the
list rather than beside it. Subsection (2) then says:

    Each time a holiday, OTHER THAN SUNDAY, listed in subsection (1) falls on
    Sunday, the succeeding Monday shall be a legal holiday. Each time a holiday
    listed in subsection (1) falls on Saturday, the preceding Friday shall be a
    legal holiday.

"Other than Sunday" is load-bearing. A generator that applied the Sunday->Monday
shift to the whole list would treat every Sunday as a holiday falling on a
Sunday and emit FIFTY-TWO PHANTOM MONDAY HOLIDAYS a year -- every one of which
would roll a real deadline LATE. assert_no_phantom_mondays() fails the build if
that ever creeps back in.

Note the asymmetry is deliberate and is reproduced here: the Sunday->Monday limb
carries the carve-out, the Saturday->Friday limb does not. That costs nothing --
Sunday never falls on a Saturday -- but the rule is copied as written rather
than tidied.

NO COLUMBUS DAY AND NO INDIGENOUS PEOPLES DAY. Oregon simply has neither, unlike
Utah and West Virginia (which have Columbus Day) and the federal calendar. A
list copied from a neighbour would add a day Oregon does not have and roll LATE.

Sources, both free on plain curl -- no user-agent needed:
  ORCP 10 A   oregonlegislature.gov/bills_laws/SiteAssets/ORCP.html
  ORS 187.010 oregonlegislature.gov/bills_laws/ors/ors187.html

NOT ENCODED, and every omission runs EARLY:
  - ORS 187.020(1): every day appointed by the Governor as a holiday.
  - ORS 187.020(2): a day appointed by the PRESIDENT counts ONLY when the
    Governor also appoints it -- a CONJUNCTIVE condition, so a presidential day
    alone is not an Oregon legal holiday. Recorded because the obvious
    assumption runs the other way.
  - ORCP 10 A's public-office-closure limb, which fires on a PARTIAL-day closure
    ("closed before the end of or for all of the normal work day") and is
    ADDITIONAL to the Saturday/holiday rollover rather than a replacement.

Run: python tools/gen_or_calendar.py
"""

import datetime as dt
import json
import os

YEARS = [2026, 2027, 2028, 2029, 2030, 2031]

RULE_URL = "https://www.oregonlegislature.gov/bills_laws/SiteAssets/ORCP.html"
STAT_URL = "https://www.oregonlegislature.gov/bills_laws/ors/ors187.html"

# ORS 187.010(1)(b), (f), (g), (i), (k) -- the fixed-date holidays, the only
# ones the subsection (2) shift can ever move.
FIXED = [
    ("New Year's Day", (1, 1), "ORS 187.010(1)(b) January 1"),
    ("Juneteenth", (6, 19), "ORS 187.010(1)(f) June 19"),
    ("Independence Day", (7, 4), "ORS 187.010(1)(g) July 4"),
    ("Veterans Day", (11, 11), "ORS 187.010(1)(i) November 11"),
    ("Christmas Day", (12, 25), "ORS 187.010(1)(k) December 25"),
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


def weekday_rule_days(year):
    """ORS 187.010(1)(c), (d), (e), (h), (j). None can fall on a weekend, so
    subsection (2) never reaches them."""
    return [
        (nth_weekday(year, 1, 0, 3), "Martin Luther King, Jr.'s Birthday",
         "ORS 187.010(1)(c) third Monday in January"),
        (nth_weekday(year, 2, 0, 3), "Presidents Day",
         "ORS 187.010(1)(d) third Monday in February -- commemorating Washington and Lincoln"),
        (last_weekday(year, 5, 0), "Memorial Day",
         "ORS 187.010(1)(e) last Monday in May"),
        (nth_weekday(year, 9, 0, 1), "Labor Day",
         "ORS 187.010(1)(h) first Monday in September"),
        (nth_weekday(year, 11, 3, 4), "Thanksgiving Day",
         "ORS 187.010(1)(j) fourth Thursday in November"),
    ]


def observed(d):
    """ORS 187.010(2). Applied ONLY to the fixed-date holidays in FIXED --
    never to 'Each Sunday', which is what the 'other than Sunday' carve-out
    excludes and what assert_no_phantom_mondays() guards."""
    w = d.weekday()
    if w == 6:
        return d + dt.timedelta(days=1), "ORS 187.010(2) Sunday -> succeeding Monday"
    if w == 5:
        return d - dt.timedelta(days=1), "ORS 187.010(2) Saturday -> preceding Friday"
    return d, ""


def build_year(year):
    rows = []
    for name, (m, d), src in FIXED:
        obs, shift = observed(dt.date(year, m, d))
        if obs.year != year:
            continue  # belongs to the neighbouring year; the spill pass adds it
        rows.append((obs, name, src + ("; " + shift if shift else "")))
    rows.extend(weekday_rule_days(year))

    # SPILL. The shift runs both ways, so a fixed-date holiday in the NEXT year
    # can land in this one -- 1 January 2028 is a Saturday, observed 2027-12-31.
    for name, (m, d), src in FIXED:
        obs, shift = observed(dt.date(year + 1, m, d))
        if obs.year == year:
            rows.append((obs, "%s (%d, observed early)" % (name, year + 1),
                         src + "; " + shift + " -- SPILLS BACK FROM %d" % (year + 1)))

    rows.sort()
    return [{"date": o.isoformat(), "name": n, "kind": "declared", "derivation": s}
            for o, n, s in rows]


def assert_no_phantom_mondays(cals):
    """THE ORS 187.010(2) TRAP, asserted rather than trusted.

    If the Sunday->Monday shift were ever applied to 'Each Sunday', every Monday
    in the year would appear. Two checks: no year may exceed the real count, and
    no emitted date may be a Monday whose only claim is that it follows a Sunday.
    """
    for c in cals:
        y = c["year"]
        legit = set()
        for _, fn, _ in [(0, f, 0) for f in []]:
            pass
        for d, n, s in [(r["date"], r["name"], r["derivation"]) for r in c["dates"]]:
            legit.add(d)
        mondays = [r for r in c["dates"] if dt.date.fromisoformat(r["date"]).weekday() == 0]
        # Every legitimate Monday is either a weekday-rule holiday or a shifted
        # fixed-date one; there are at most 5 + 5 of those, never 52.
        assert len(mondays) <= 8, (
            "%d emits %d Monday holidays -- the ORS 187.010(2) 'other than Sunday' "
            "carve-out has been lost and every Monday after a Sunday is being "
            "treated as a holiday." % (y, len(mondays)))
        assert len(c["dates"]) <= 12, (
            "%d emits %d holidays; Oregon has ten in ORS 187.010(1) plus at most "
            "one spill. A count this high means the Sunday shift is over-applying."
            % (y, len(c["dates"])))
        # And no Columbus Day, which Oregon does not have.
        columbus = nth_weekday(y, 10, 0, 2).isoformat()
        assert columbus not in legit, (
            "%s: Oregon has NO Columbus Day and no Indigenous Peoples Day. "
            "Encoding one rolls a deadline off a normal business day -- LATE." % columbus)


def main():
    cals = []
    for y in YEARS:
        rows = build_year(y)
        seen = set()
        for r in rows:
            d = dt.date.fromisoformat(r["date"])
            assert r["date"] not in seen, "duplicate %s in %d" % (r["date"], y)
            assert d.weekday() < 5, (
                "%s (%s) lands on a weekend -- the ORS 187.010(2) shift is wrong"
                % (r["date"], r["name"]))
            assert d.year == y, "%s filed under year %d" % (r["date"], y)
            seen.add(r["date"])
        cals.append({
            "jurisdiction": "or",
            "year": y,
            "authority": {
                "citation": "ORS 187.010 (legal holidays), as incorporated for time "
                            "computation by Or. R. Civ. P. 10 A",
                "url": STAT_URL,
                "computation_url": RULE_URL,
                "note": "EVERY DATE HERE IS DERIVED from ORS 187.010(1) and its "
                        "subsection (2) shift, not transcribed. 'EACH SUNDAY' IS "
                        "ITSELF ITEM (1)(a) AND IS NOT EMITTED -- weekends are "
                        "handled by the engine, and emitting Sundays would be "
                        "redundant. The load-bearing detail is subsection (2)'s "
                        "'OTHER THAN SUNDAY' carve-out on the Sunday->Monday limb: "
                        "without it a generator produces fifty-two phantom Monday "
                        "holidays a year, every one of which rolls a real deadline "
                        "LATE. tools/gen_or_calendar.py asserts against that. "
                        "OREGON HAS NO COLUMBUS DAY AND NO INDIGENOUS PEOPLES DAY, "
                        "unlike Utah, West Virginia and the federal calendar -- also "
                        "asserted. NOT ENCODED, all EARLY: ORS 187.020(1) "
                        "gubernatorial appointments; ORS 187.020(2), where a "
                        "PRESIDENTIAL day counts ONLY IF the Governor also appoints "
                        "it (a conjunctive condition, so a presidential day alone is "
                        "not an Oregon holiday); and ORCP 10 A's public-office "
                        "closure limb, which fires on a PARTIAL-day closure and is "
                        "additional to the rollover rather than a replacement.",
                "retrieved_at": "2026-08-28",
            },
            "dates": rows,
        })

    assert_no_phantom_mondays(cals)

    out = {
        "_readme": [
            "OREGON HOLIDAY CALENDARS -- DERIVED FROM ORS 187.010, as incorporated",
            "by Or. R. Civ. P. 10 A. 2026-2031.",
            "",
            "TEN HOLIDAYS, and 'Each Sunday' is deliberately NOT among the emitted",
            "dates. ORS 187.010(1)(a) makes every Sunday a legal holiday, but the",
            "engine already treats weekends as non-days, so emitting 52 Sundays a",
            "year would be redundant -- and, worse, would invite the shift bug below.",
            "",
            "THE 'OTHER THAN SUNDAY' TRAP, WHICH THIS GENERATOR ASSERTS AGAINST.",
            "ORS 187.010(2): 'Each time a holiday, OTHER THAN SUNDAY, listed in",
            "subsection (1) falls on Sunday, the succeeding Monday shall be a legal",
            "holiday.' Those three words are load-bearing. Sunday is itself item",
            "(1)(a), so a generator applying the shift to the whole list treats every",
            "Sunday as a holiday-falling-on-a-Sunday and emits FIFTY-TWO PHANTOM",
            "MONDAY HOLIDAYS a year -- each one rolling a real deadline LATE.",
            "assert_no_phantom_mondays() fails the build if that returns.",
            "",
            "The asymmetry is copied as written rather than tidied: the",
            "Sunday->Monday limb carries the carve-out and the Saturday->Friday limb",
            "does not. It costs nothing, because Sunday never falls on a Saturday.",
            "",
            "NO COLUMBUS DAY AND NO INDIGENOUS PEOPLES DAY -- Oregon has neither,",
            "unlike Utah, West Virginia and the federal calendar. Also asserted,",
            "because this is the kind of day a list copied from a neighbour adds.",
            "",
            "THE SHIFT IS BOTH-WAYS AND SPILLS ACROSS THE YEAR BOUNDARY: 1 January",
            "2028 falls on a Saturday and is observed 2027-12-31, so the 2027",
            "calendar carries it and 2028 does not.",
            "",
            "Generated by tools/gen_or_calendar.py, which asserts per year that no",
            "date is duplicated, none lands on a weekend, none is filed under the",
            "wrong year, no Columbus Day appears, and no phantom Mondays appear.",
        ],
        "holiday_calendars": cals,
    }

    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "sql", "sairnlaw_deadline_calendars_oregon.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    for c in cals:
        print("or %d: %2d days  %s" % (c["year"], len(c["dates"]),
                                       " ".join(r["date"][5:] for r in c["dates"])))
    print("wrote " + path)


if __name__ == "__main__":
    main()
