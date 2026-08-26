"""Generate the Missouri holiday calendar from RSMo 9.010.

Every day is DERIVED from the statute's own words, quoted in the readme of the
file this writes. Nothing here is copied from a published court or agency
schedule -- the agency schedule is used only as CORROBORATION, never as a
source, for the reason set out below.

HOW A HOLIDAY STATUTE REACHES A MISSOURI COURT DEADLINE, AND THE HONEST
CAVEAT. Mo. R. Civ. P. 44.01(a) rolls the last day off "a Saturday, Sunday or a
legal holiday" and NAMES NO STATUTE. RSMo 9.010 is titled "Public holidays" and
never uses the phrase "legal holiday". That is the identical lexical gap that
helped refuse Kentucky, so it was checked the same way -- and it comes out the
opposite way here:

  KENTUCKY   KRS 2.110 lists four days its courts do NOT close for and OMITS
             Thanksgiving, so encoding it rolls deadlines LATE. Fatal.
  MISSOURI   RSMo 9.010's thirteen days match the State of Missouri's own
             published holiday schedule DAY FOR DAY (checked against the
             Office of Administration's 2026 list, oa.mo.gov), Thanksgiving
             included, and there is no listed day the state stays open for.

So both candidate readings of "legal holiday" converge on the same thirteen
days, and encoding 9.010 cannot roll a deadline LATE on any of them. The
wording gap remains a real question of law and belongs in the bundled lawyer's
question; it is not a safety problem.

THE SHIFT IS SUNDAY-ONLY. Verbatim: "and when any of such holidays falls upon
Sunday, the Monday next following shall be considered the holiday." The statute
says NOTHING about Saturday. Massachusetts is the same and Virginia and West
Virginia are not -- a both-ways shift carried across from either would invent a
Friday holiday Missouri does not have, and that error runs LATE. This is the
SECOND state in a row where that mistake was available; in Massachusetts the
generator's own assertion caught it. Because the shift only ever moves a day
FORWARD, no holiday can spill into the previous calendar year.

WHAT IS DELIBERATELY NOT ENCODED: administratively OBSERVED substitute days.
The state observes "Independence Day (observed) -- Friday, July 3" in 2026
because 4 July 2026 is a Saturday, but 9.010 creates no such substitute. If
Rule 44.01's "legal holiday" means the statute, encoding the observed Friday
would roll a deadline that should not roll -- LATE. Omitting it means a
deadline landing on that Friday does not roll when the courthouse may in fact
be shut -- EARLY, and safe. Disclosed via JURISDICTION_COVERAGE rather than
encoded.

Usage:  python tools/gen_mo_calendar.py
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


def sunday_shift(d):
    """RSMo 9.010: "when any of such holidays falls upon Sunday, the Monday next
    following shall be considered the holiday." SUNDAY ONLY. A Saturday holiday
    is NOT moved -- and it needs no moving, because Rule 44.01(a) already rolls
    off a Saturday in its own right."""
    return d + timedelta(days=1) if d.weekday() == SUN else d


def holidays_for(year):
    """(observed_date, name, derivation) for the thirteen statutory days."""
    out = []

    # The eight FIXED-DATE days named in RSMo 9.010, subject to the Sunday shift.
    for m, day, name in [
        (1, 1, "New Year's Day"),
        # LINCOLN DAY. RSMo 9.020 names 12 February "Lincoln Day". No other
        # jurisdiction seeded in this engine has it -- and note that Kentucky's
        # KRS 2.110 also lists Lincoln's Birthday, where it is one of the days
        # its COURTS DO NOT CLOSE FOR. Missouri's courts do. Same day, opposite
        # consequence, which is exactly why holiday lists are never carried
        # between states.
        (2, 12, "Lincoln Day"),
        # TRUMAN DAY. Missouri-specific; no federal or multi-state parallel.
        (5, 8, "Truman Day"),
        (6, 19, "Juneteenth"),
        (7, 4, "Independence Day"),
        (11, 11, "Veterans Day"),
        (12, 25, "Christmas Day"),
    ]:
        actual = date(year, m, day)
        obs = sunday_shift(actual)
        deriv = "RSMo 9.010 fixed date %04d-%02d-%02d" % (year, m, day)
        if obs != actual:
            deriv += (" fell on a Sunday, observed the Monday next following under 9.010's "
                      "\"when any of such holidays falls upon Sunday, the Monday next following "
                      "shall be considered the holiday\"")
        out.append((obs, name, deriv))

    # The nth-weekday days. Never shifted -- they cannot fall on a Sunday.
    out.append((nth_weekday(year, 1, MON, 3), "Martin Luther King, Jr. Day",
                "RSMo 9.010 third Monday of January"))
    out.append((nth_weekday(year, 2, MON, 3), "Washington's Birthday",
                "RSMo 9.010 third Monday in February"))
    out.append((last_weekday(year, 5, MON), "Memorial Day",
                "RSMo 9.010 last Monday in May"))
    out.append((nth_weekday(year, 9, MON, 1), "Labor Day",
                "RSMo 9.010 first Monday in September"))
    # COLUMBUS DAY IS A MISSOURI PUBLIC HOLIDAY. North Carolina excludes it (its
    # Rule 6(a) keys on courthouse closure and its courts do not close) and
    # Washington excludes it (RCW 1.16.050(7)); New Jersey, Virginia and
    # Massachusetts all count it. Read per state, never carried.
    out.append((nth_weekday(year, 10, MON, 2), "Columbus Day",
                "RSMo 9.010 second Monday in October"))
    out.append((nth_weekday(year, 11, THU, 4), "Thanksgiving Day",
                "RSMo 9.010 fourth Thursday in November"))
    return out


EMIT = range(2026, 2032)

calendars = []
for y in EMIT:
    rows = []
    seen = set()
    for obs, name, deriv in sorted(holidays_for(y), key=lambda r: r[0]):
        iso = obs.isoformat()
        assert iso not in seen, "duplicate %s in %d" % (iso, y)
        seen.add(iso)
        # A SATURDAY ENTRY IS CORRECT HERE. 9.010 shifts only Sundays, so a
        # fixed-date holiday falling on a Saturday stays there -- the same
        # property Massachusetts has, and the reason the Virginia/West Virginia
        # both-ways assertion must NOT be copied in. What must never appear is a
        # SUNDAY: the fixed dates are shifted off Sunday by the statute itself
        # and an nth-weekday day cannot land on one, so a Sunday here would mean
        # the shift silently stopped working.
        assert obs.weekday() != SUN, \
            "%s in %d is a SUNDAY -- 9.010's Sunday shift did not apply" % (iso, y)
        assert obs.year == y, "%s filed under %d" % (iso, y)
        rows.append({"date": iso, "name": name, "kind": "declared", "derivation": deriv})

    calendars.append({
        "jurisdiction": "mo",
        "year": y,
        "authority": {
            "citation": "RSMo 9.010 (public holidays), as the list supplying \"legal holiday\" for "
                        "time computation under Mo. R. Civ. P. 44.01(a)",
            "url": "https://revisor.mo.gov/main/OneSection.aspx?section=9.010",
            "computation_url": "https://www.courts.mo.gov/courts/ClerkHandbooksP2RulesOnly.nsf/0/59231e1c136ceb1086256ca60052133a?OpenDocument=",
            "corroboration_url": "https://oa.mo.gov/commissioner/state-holidays",
            "note": (
                "EVERY DATE HERE IS DERIVED FROM THE STATUTE, not copied from any published schedule. "
                "THE LINK IS BY CONVERGENCE, NOT BY EXPRESS CROSS-REFERENCE, AND THAT IS DISCLOSED "
                "RATHER THAN GLOSSED: Mo. R. Civ. P. 44.01(a) says \"legal holiday\" and names no "
                "statute, while RSMo 9.010 is titled \"Public holidays\" and never says \"legal "
                "holiday\". That is the same lexical gap that helped refuse Kentucky -- but Kentucky's "
                "KRS 2.110 lists four days its courts do NOT close for and omits Thanksgiving, so "
                "encoding it fails LATE, whereas RSMo 9.010's thirteen days match Missouri's own "
                "published state holiday schedule day for day (corroborated against the Office of "
                "Administration's 2026 list) with Thanksgiving present and no listed day the state "
                "stays open for. Both readings converge, so encoding this list cannot roll a deadline "
                "LATE. The wording gap is a real question of law and belongs in the bundled lawyer's "
                "question; it is not a safety problem. "
                "THE SHIFT IS SUNDAY-ONLY, verbatim: \"when any of such holidays falls upon Sunday, "
                "the Monday next following shall be considered the holiday.\" 9.010 says NOTHING about "
                "Saturday, so a Saturday holiday is NOT moved to the preceding Friday -- the same as "
                "Massachusetts and the opposite of Virginia and West Virginia. Carrying a both-ways "
                "shift across would invent a Friday holiday and roll deadlines LATE. "
                "TWO DAYS NO OTHER SEEDED JURISDICTION HAS: LINCOLN DAY (12 February, named by RSMo "
                "9.020) and TRUMAN DAY (8 May), the latter with no federal or multi-state parallel. "
                "Note that Kentucky's KRS 2.110 ALSO lists Lincoln's Birthday -- there as a day its "
                "courts do NOT close for. Same day, opposite consequence. "
                "COLUMBUS DAY IS COUNTED HERE, as in New Jersey, Virginia and Massachusetts, and "
                "unlike North Carolina and Washington, which exclude it for two different reasons. "
                "WHAT IS DELIBERATELY ABSENT: administratively OBSERVED substitute days. The state "
                "observes Friday 3 July 2026 for a Saturday 4 July, but 9.010 creates no such "
                "substitute; encoding it would roll a deadline LATE if the statute governs, while "
                "omitting it can only run EARLY. Also absent: RSMo 9.010's \"no holiday for state "
                "employees on the fourth Monday of October\" sentence, which concerns state employees "
                "and not the holiday list. See JURISDICTION_COVERAGE in api/_lib/deadline-engine.js."
            ),
            "retrieved_at": "2026-08-26",
        },
        "dates": rows,
    })

doc = {
    "_readme": [
        "MISSOURI HOLIDAY CALENDARS -- DERIVED FROM RSMo 9.010, 2026-2031.",
        "",
        "Coverage is SIX YEARS because Missouri's list is fixed by STATUTE in",
        "derivable terms -- seven fixed dates and six weekday rules -- rather than",
        "by an annual court order (New Jersey) or an administrative schedule",
        "(North Carolina). Nothing needs re-issuing for it to be computed.",
        "",
        "Generated by tools/gen_mo_calendar.py, which asserts per year that no",
        "date is duplicated, no date is a SUNDAY, and no date is filed under the",
        "wrong year.",
        "",
        "== THE LINK IS BY CONVERGENCE, NOT BY CROSS-REFERENCE ==================",
        "Rule 44.01(a) says \"legal holiday\" and points at nothing; RSMo 9.010 is",
        "titled \"Public holidays\". Kentucky was refused partly on that same gap.",
        "The difference is direction: Kentucky's statute diverges from what its",
        "courts do and fails LATE; Missouri's matches the state's own schedule day",
        "for day, so both readings converge and encoding it is safe. The wording",
        "gap still belongs in the bundled lawyer's question.",
        "",
        "== THE SHIFT IS SUNDAY-ONLY ===========================================",
        "\"when any of such holidays falls upon Sunday, the Monday next following",
        "shall be considered the holiday.\" No Saturday shift exists. Do NOT add",
        "one by analogy to Virginia or West Virginia -- that invents a Friday",
        "holiday and rolls deadlines LATE. Second state running where this was",
        "available to get wrong; in Massachusetts the generator's own assertion",
        "caught it.",
        "",
        "== TWO DAYS TO READ TWICE =============================================",
        "LINCOLN DAY (12 February) and TRUMAN DAY (8 May). Truman Day has no",
        "federal or multi-state parallel. Kentucky's KRS 2.110 also lists",
        "Lincoln's Birthday -- there as a day its courts do NOT close for. Same",
        "day, opposite consequence, in two neighbouring states.",
        "",
        "== OBSERVED SUBSTITUTE DAYS ARE NOT IN THIS CALENDAR ===================",
        "The state observes Friday 3 July 2026 for a Saturday 4 July. The statute",
        "creates no such substitute. Encoding it would roll LATE; omitting it can",
        "only run EARLY. Disclosed on every Missouri result instead.",
    ],
    "holiday_calendars": calendars,
}

out = "sql/sairnlaw_deadline_calendars_missouri.json"
with open(out, "w", encoding="utf-8") as f:
    json.dump(doc, f, indent=1, ensure_ascii=False)
    f.write("\n")

for c in calendars:
    print(c["year"], len(c["dates"]), "dates")
print("wrote", out)
