"""Generate the Virginia holiday calendar from Va. Code 2.2-3300.

Every day is DERIVED from the statute's own words, quoted in the readme of the
file this writes. Nothing here is copied from a published court schedule.
"""
import json
from datetime import date, timedelta

MON, TUE, WED, THU, FRI, SAT, SUN = range(7)


def nth_weekday(year, month, weekday, n):
    d = date(year, month, 1)
    d += timedelta(days=(weekday - d.weekday()) % 7)
    return d + timedelta(days=7 * (n - 1))


def last_weekday(year, month, weekday):
    d = date(year, month + 1, 1) - timedelta(days=1) if month < 12 else date(year, 12, 31)
    d -= timedelta(days=(d.weekday() - weekday) % 7)
    return d


def shift(d):
    """2.2-3300: Saturday -> the Friday next preceding; Sunday -> the Monday
    next following. Applies only to the fixed-date holidays; an nth-weekday
    holiday can never land on a weekend."""
    if d.weekday() == SAT:
        return d - timedelta(days=1)
    if d.weekday() == SUN:
        return d + timedelta(days=1)
    return d


def holidays_for(year):
    """Returns (observed_date, name, derivation) for the statutory year."""
    out = []
    # Fixed-date days, subject to the weekend shift.
    for m, day, name in [
        (1, 1, "New Year's Day"),
        (6, 19, "Juneteenth"),
        (7, 4, "Independence Day"),
        (11, 11, "Veterans Day"),
        (12, 25, "Christmas Day"),
    ]:
        actual = date(year, m, day)
        obs = shift(actual)
        deriv = "Va. Code 2.2-3300 fixed date %04d-%02d-%02d" % (year, m, day)
        if obs != actual:
            deriv += " fell on a %s, observed the %s next %s under 2.2-3300's final sentence" % (
                actual.strftime('%A'),
                obs.strftime('%A'),
                'preceding' if obs < actual else 'following')
        out.append((obs, name, deriv))

    # Nth-weekday days. Never shifted -- they cannot fall on a weekend.
    out.append((nth_weekday(year, 1, MON, 3), "Martin Luther King, Jr., Day",
                "Va. Code 2.2-3300 third Monday in January"))
    out.append((nth_weekday(year, 2, MON, 3), "George Washington Day",
                "Va. Code 2.2-3300 third Monday in February"))
    out.append((last_weekday(year, 5, MON), "Memorial Day",
                "Va. Code 2.2-3300 last Monday in May"))
    out.append((nth_weekday(year, 9, MON, 1), "Labor Day",
                "Va. Code 2.2-3300 first Monday in September"))
    out.append((nth_weekday(year, 10, MON, 2), "Columbus Day and Yorktown Victory Day",
                "Va. Code 2.2-3300 second Monday in October"))
    # "The Tuesday following the first Monday in November" -- EVERY year, not
    # only even ones. Virginia elects its House of Delegates in odd years.
    out.append((nth_weekday(year, 11, MON, 1) + timedelta(days=1), "Election Day",
                "Va. Code 2.2-3300 the Tuesday following the first Monday in November"))
    thanks = nth_weekday(year, 11, THU, 4)
    out.append((thanks, "Thanksgiving Day",
                "Va. Code 2.2-3300 fourth Thursday in November"))
    out.append((thanks + timedelta(days=1), "Day after Thanksgiving",
                "Va. Code 2.2-3300 the Friday next following the fourth Thursday in November"))
    return out


# Compute a wider span than we emit, because a 1 January that falls on a
# Saturday is observed on 31 December of the PREVIOUS calendar year and would
# otherwise be silently dropped from that year's calendar.
SPAN = range(2025, 2033)
EMIT = range(2026, 2032)

buckets = {y: [] for y in EMIT}
for y in SPAN:
    for obs, name, deriv in holidays_for(y):
        if obs.year in buckets:
            buckets[obs.year].append({
                "date": obs.isoformat(),
                "name": name,
                # "declared" to match validateHolidayPayload's accepted enum
                # (federal / declared / state) and every sibling jurisdiction's
                # generator -- NOT "derived", which is not a valid kind and
                # would have made add_holidays reject this calendar outright.
                # Found by Guardian Check 29 (the storage-validator/engine
                # drift check written after the same class of bug shipped for
                # California's service extensions) before this was ever
                # submitted, not after.
                "kind": "declared",
                "derivation": deriv,
            })

calendars = []
for y in EMIT:
    days = sorted(buckets[y], key=lambda r: r["date"])
    seen = set()
    for d in days:
        assert d["date"] not in seen, "duplicate %s in %d" % (d["date"], y)
        seen.add(d["date"])
        assert date.fromisoformat(d["date"]).weekday() < SAT, \
            "%s in %d is a weekend day" % (d["date"], y)
    calendars.append({
        "jurisdiction": "va",
        "year": y,
        "authority": {
            "citation": "Va. Code 2.2-3300 (legal holidays), as reached for time computation by Va. Code 1-210(B) through Va. Code 17.1-207(A)",
            "url": "https://law.lis.virginia.gov/vacode/title2.2/chapter33/section2.2-3300/",
            "computation_url": "https://law.lis.virginia.gov/vacode/title1/chapter2.1/section1-210/",
            "closure_url": "https://law.lis.virginia.gov/vacode/title17.1/chapter2/section17.1-207/",
            "note": (
                "EVERY DATE HERE IS DERIVED FROM THE STATUTE, not copied from any published court "
                "schedule. Va. Code 2.2-3300 states each day either as a fixed calendar date or as an "
                "nth weekday, and its final sentence supplies the weekend shift verbatim: \"Whenever any "
                "of such days falls on Saturday, the Friday next preceding such day, or whenever any of "
                "such days falls on Sunday, the Monday next following such day ... shall be a legal "
                "holiday as to the transaction of all business.\" Each entry carries its own derivation. "
                "HOW A HOLIDAY STATUTE REACHES A COURT DEADLINE: Va. Code 1-210(B) rolls the last day off "
                "a \"legal holiday\" but names no statute, so the link is Va. Code 17.1-207(A), which "
                "requires every clerk's office to be kept open \"on every day except Saturday ... and "
                "Sunday, and the days provided for in 2.2-3300\". "
                "ELECTION DAY IS ANNUAL, NOT EVEN-YEAR. The statute says \"the Tuesday following the "
                "first Monday in November\" with no qualification, and Virginia elects its House of "
                "Delegates in odd years. Same trap as New Jersey. "
                "COLUMBUS DAY IS A VIRGINIA LEGAL HOLIDAY, unlike North Carolina (whose Rule 6(a) keys on "
                "actual courthouse closure and whose courts do not close) and unlike Washington (whose "
                "RCW 1.16.050(7) says its recognized days \"may not be considered legal holidays for any "
                "purpose\"). Virginia names it in 2.2-3300 and 17.1-207(A) mandates the closure. "
                "THE DAY AFTER THANKSGIVING IS IN THE STATUTE ITSELF -- \"The fourth Thursday in November "
                "and the Friday next following\" -- so it is derived, not an administrative addition of "
                "the kind North Carolina's Christmas and Thanksgiving blocks turned out to be. "
                "WHAT IS DELIBERATELY ABSENT: this calendar does NOT encode (1) days the Governor "
                "authorizes the closing of state government, which Va. Code 1-210(F) makes legal holidays; "
                "(2) days appointed by the Governor or the President, which 2.2-3300's own final sentence "
                "also makes legal holidays; or (3) the discretionary closures 17.1-207 permits a clerk -- "
                "locality-adopted holidays, Christmas Eve, and health-or-safety closures authorized by a "
                "chief or presiding judge. None is knowable in advance and the last is per-locality. "
                "Omitting them can only make a computed date EARLIER than the true deadline, never later, "
                "which is why the engine discloses the gap on every Virginia result instead of refusing. "
                "See JURISDICTION_COVERAGE in api/_lib/deadline-engine.js."
            ),
            "retrieved_at": "2026-08-25",
        },
        "dates": days,
    })

doc = {
    "_readme": [
        "VIRGINIA HOLIDAY CALENDARS -- DERIVED FROM Va. Code 2.2-3300, 2026-2031.",
        "",
        "Coverage is SIX YEARS, unlike New Jersey's one and North Carolina's two,",
        "because Virginia's holidays are fixed by STATUTE in derivable terms rather",
        "than by an annual court order (New Jersey) or a published administrative",
        "schedule (North Carolina). Nothing needs re-issuing for the calendar to be",
        "computed, so nothing has to be re-run each year.",
        "",
        "Generated by tools/gen_va_calendar.py, which asserts on every emitted year",
        "that no date is duplicated and no date falls on a Saturday or Sunday.",
        "",
        "READ THE PER-YEAR authority.note. It carries the verbatim weekend-shift",
        "sentence, the 1-210 -> 17.1-207 -> 2.2-3300 chain that makes a holiday",
        "statute reach a court deadline at all, and the list of closures that are",
        "deliberately NOT encoded because they are not knowable in advance.",
    ],
    "holiday_calendars": calendars,
}

out = "sql/sairnlaw_deadline_calendars_virginia.json"
with open(out, "w", encoding="utf-8") as f:
    json.dump(doc, f, indent=1, ensure_ascii=False)
    f.write("\n")

for c in calendars:
    print(c["year"], len(c["dates"]), "dates")
print("wrote", out)
