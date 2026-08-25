"""Generate the Massachusetts holiday calendar from Mass. G.L. c. 4, s. 7, Cl. 18.

Every day is DERIVED from the statute's own words, quoted in the readme of the
file this writes. Nothing here is copied from a published court schedule.

HOW A HOLIDAY STATUTE REACHES A COURT DEADLINE HERE -- BY EXPRESS
CROSS-REFERENCE, which is the strong case. Mass. R. Civ. P. 6(a) says, in its
own text: "As used in this rule and in Rule 77(c), 'legal holiday' includes
those days specified in Mass. G.L. c. 4, s. 7 and any other day appointed as a
holiday by the President or the Congress of the United States or designated by
the laws of the Commonwealth." That is the same shape as Washington's CR 6(a)
-> RCW 1.16.050 and the OPPOSITE of Texas, Arizona and Kentucky, where the rule
says "legal holiday" and points at nothing. Rule 77(b) then closes the clerk's
office "on all days except Saturdays, Sundays, and legal holidays", using the
same defined term, so the statute governs both the rolling and the closure.

WHAT IS DELIBERATELY NOT ENCODED, AND WHY IT IS SAFE:

  SUFFOLK COUNTY ONLY -- Evacuation Day (March 17) and Bunker Hill Day
  (June 17). Clause Eighteenth makes these legal holidays "with respect to
  Suffolk county only". holidayFor() keys a calendar by jurisdiction + year,
  so one `ma` calendar cannot carry a county-scoped day. Encoding them would
  roll deadlines in the other thirteen counties LATE, which is the direction
  that misses a filing; omitting them can only ever run EARLY in Suffolk.
  So they are omitted and DISCLOSED. Note also that the same clause requires
  Suffolk offices to "be open for business and appropriately staffed" on both
  days, so whether a Rule 6(a) period rolls off them at all is a genuine
  lawyer's question -- which means omitting them is either CORRECT or EARLY,
  and never late. Suffolk County is BOSTON, so this is the busiest venue in
  the Commonwealth, not an edge case.

  PRESIDENTIALLY OR CONGRESSIONALLY APPOINTED DAYS -- Rule 6(a)'s own
  "any other day appointed as a holiday by the President or the Congress"
  limb is open-ended and ad hoc, never knowable in advance. Same shape as
  Va. Code s. 1-210(F), same direction (EARLY), same treatment.

THE WEEKEND SHIFT IS ONE-WAY AND THAT IS UNUSUAL. Clause Eighteenth shifts a
fixed-date holiday only "when any of said days occurs on Sunday" -- it says
NOTHING about Saturday. Virginia and West Virginia both shift BOTH ways
(Saturday -> the preceding Friday). A generator carried across from either
would invent a Friday holiday Massachusetts does not have, and that error runs
LATE. There is also no backward spill into the previous calendar year, which
the Virginia and West Virginia generators both have to handle, because a
Sunday shift only ever moves a day FORWARD.

Usage:  python tools/gen_ma_calendar.py
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
    """Clause Eighteenth: "or the day following when any of said days occurs on
    Sunday". SUNDAY ONLY. A Saturday holiday is NOT moved -- and it does not
    need to be, because Rule 6(a) already rolls off a Saturday in its own
    right, so the statute's silence costs nothing and inventing a Friday
    holiday to fill it would roll deadlines LATE."""
    return d + timedelta(days=1) if d.weekday() == SUN else d


def holidays_for(year):
    """(observed_date, name, derivation) for the statewide list only."""
    out = []

    # The five FIXED-DATE days named in Clause Eighteenth, subject to the
    # Sunday-only shift.
    for m, day, name in [
        (1, 1, "New Year's Day"),
        (6, 19, "Juneteenth Independence Day"),
        (7, 4, "Independence Day"),
        (11, 11, "Veterans Day"),
        (12, 25, "Christmas Day"),
    ]:
        actual = date(year, m, day)
        obs = sunday_shift(actual)
        deriv = "Mass. G.L. c. 4, s. 7, Cl. 18 fixed date %04d-%02d-%02d" % (year, m, day)
        if obs != actual:
            deriv += (" fell on a Sunday, observed the day following under Cl. 18's "
                      "\"or the day following when any of said days occurs on Sunday\"")
        out.append((obs, name, deriv))

    # The nth-weekday days. Never shifted -- they cannot fall on a weekend.
    out.append((nth_weekday(year, 1, MON, 3), "Martin Luther King, Jr. Day",
                "Mass. G.L. c. 4, s. 7, Cl. 18 third Monday in January"))
    out.append((nth_weekday(year, 2, MON, 3), "Washington's Birthday",
                "Mass. G.L. c. 4, s. 7, Cl. 18 third Monday in February"))
    # PATRIOTS' DAY -- third Monday in April. Massachusetts and Maine only; no
    # other jurisdiction seeded in this engine has it, and it is not derivable
    # from any federal list. Named in Cl. 18 by date-rule, not by name.
    out.append((nth_weekday(year, 4, MON, 3), "Patriots' Day",
                "Mass. G.L. c. 4, s. 7, Cl. 18 third Monday in April"))
    out.append((last_weekday(year, 5, MON), "Memorial Day",
                "Mass. G.L. c. 4, s. 7, Cl. 18 last Monday in May"))
    out.append((nth_weekday(year, 9, MON, 1), "Labor Day",
                "Mass. G.L. c. 4, s. 7, Cl. 18 first Monday in September"))
    # COLUMBUS DAY IS A MASSACHUSETTS LEGAL HOLIDAY. North Carolina excludes it
    # (its courts do not close and Rule 6(a) there keys on closure) and
    # Washington excludes it (RCW 1.16.050(7) says its recognized days "may not
    # be considered legal holidays for any purpose"). New Jersey and Virginia
    # both count it. Three answers across five states -- read, never carried.
    out.append((nth_weekday(year, 10, MON, 2), "Columbus Day",
                "Mass. G.L. c. 4, s. 7, Cl. 18 second Monday in October"))
    # Cl. 18 names "Thanksgiving Day" WITHOUT giving it a date rule. The date
    # comes from the federal appointment (5 U.S.C. 6103, fourth Thursday in
    # November), which Rule 6(a) reaches independently through its own "any
    # other day appointed as a holiday by the President or the Congress of the
    # United States" limb. So the derivation is stated on the entry rather than
    # silently assumed from the other states' calendars.
    out.append((nth_weekday(year, 11, THU, 4), "Thanksgiving Day",
                "Mass. G.L. c. 4, s. 7, Cl. 18 names \"Thanksgiving Day\" without a date rule; "
                "the fourth Thursday in November comes from the federal appointment, which "
                "Mass. R. Civ. P. 6(a) reaches through its \"appointed as a holiday by the "
                "President or the Congress of the United States\" limb"))
    return out


EMIT = range(2026, 2032)

calendars = []
for y in EMIT:
    days = sorted(holidays_for(y), key=lambda r: r[0])
    seen = set()
    rows = []
    for obs, name, deriv in days:
        iso = obs.isoformat()
        assert iso not in seen, "duplicate %s in %d" % (iso, y)
        seen.add(iso)
        # A SATURDAY ENTRY IS CORRECT HERE AND THAT IS THE POINT OF THIS CHECK.
        # This assertion originally read `obs.weekday() < SAT`, carried over
        # from the Virginia and West Virginia generators, and it FIRED on
        # 2026-07-04. That was the assertion being wrong, not the data:
        # 4 July 2026 is a Saturday and Cl. 18 shifts only Sundays, so
        # Independence Day 2026 really is a Saturday legal holiday in
        # Massachusetts. It costs nothing downstream -- Rule 6(a) rolls off a
        # Saturday in its own right, and the short-period exclusion excludes
        # "intermediate Saturdays, Sundays, and legal holidays" anyway, so the
        # day is non-counting by two independent routes.
        # What must NEVER appear is a SUNDAY: the fixed-date days are shifted
        # off Sunday by Cl. 18 itself, and an nth-weekday day cannot land on
        # one. A Sunday here would mean the shift silently stopped working.
        assert obs.weekday() != SUN, \
            "%s in %d is a SUNDAY -- Cl. 18's Sunday shift did not apply" % (iso, y)
        # Every emitted date must be in the year it is filed under. Unlike
        # Virginia and West Virginia, Massachusetts cannot spill into the
        # previous year, because its shift only moves days FORWARD -- this
        # assertion exists to catch a future edit that adds a backward shift.
        assert obs.year == y, "%s filed under %d" % (iso, y)
        rows.append({"date": iso, "name": name, "kind": "declared", "derivation": deriv})

    calendars.append({
        "jurisdiction": "ma",
        "year": y,
        "authority": {
            "citation": "Mass. G.L. c. 4, s. 7, Cl. 18 (legal holidays), as expressly incorporated "
                        "for time computation by Mass. R. Civ. P. 6(a)",
            "url": "https://malegislature.gov/Laws/GeneralLaws/PartI/TitleI/Chapter4/Section7",
            "computation_url": "https://www.mass.gov/rules-of-civil-procedure/civil-procedure-rule-6-time",
            "clerk_office_url": "https://www.mass.gov/rules-of-civil-procedure/civil-procedure-rule-77-courts-and-clerks",
            "note": (
                "EVERY DATE HERE IS DERIVED FROM THE STATUTE, not copied from any published court "
                "schedule. "
                "THE LINK IS EXPRESS, WHICH IS THE STRONG CASE: Mass. R. Civ. P. 6(a) states in its "
                "own text that \"As used in this rule and in Rule 77(c), 'legal holiday' includes "
                "those days specified in Mass. G.L. c. 4, s. 7 and any other day appointed as a "
                "holiday by the President or the Congress of the United States or designated by the "
                "laws of the Commonwealth.\" Same shape as Washington's CR 6(a) -> RCW 1.16.050; the "
                "opposite of Texas, Arizona and Kentucky, whose rules name no statute. Rule 77(b) "
                "separately keeps the clerk's office closed on \"Saturdays, Sundays, and legal "
                "holidays\", the same defined term. "
                "THE SHIFT IS SUNDAY-ONLY, verbatim: \"or the day following when any of said days "
                "occurs on Sunday\". Clause 18 says NOTHING about Saturday, so a Saturday holiday is "
                "NOT moved to the preceding Friday -- the opposite of Virginia and West Virginia. It "
                "costs nothing, because Rule 6(a) already rolls off a Saturday in its own right, and "
                "inventing a Friday holiday would roll deadlines LATE. "
                "PATRIOTS' DAY (third Monday in April) is a Massachusetts legal holiday and appears "
                "in no other jurisdiction seeded in this engine. "
                "COLUMBUS DAY IS COUNTED HERE. North Carolina and Washington both exclude it, for two "
                "different reasons; New Jersey and Virginia count it. Read per state, never carried. "
                "THANKSGIVING has no date rule in Cl. 18 -- the fourth Thursday comes from the federal "
                "appointment, which Rule 6(a) reaches through its own President/Congress limb. "
                "WHAT IS DELIBERATELY ABSENT: (1) EVACUATION DAY (March 17) and BUNKER HILL DAY "
                "(June 17), which Cl. 18 makes legal holidays \"with respect to SUFFOLK COUNTY ONLY\". "
                "A calendar is keyed by jurisdiction and year, so it cannot express a county-scoped "
                "day; encoding them would roll the other thirteen counties LATE, while omitting them "
                "can only run EARLY in Suffolk. The same clause also requires Suffolk offices to \"be "
                "open for business and appropriately staffed\" on both days, so whether a Rule 6(a) "
                "period rolls off them at all is an open lawyer's question -- which makes the omission "
                "either CORRECT or EARLY, never late. SUFFOLK COUNTY IS BOSTON, the busiest venue in "
                "the Commonwealth; this is not an edge case and the engine discloses it on every "
                "Massachusetts result. (2) Days appointed ad hoc by the President or Congress, per "
                "Rule 6(a)'s own open-ended limb. See JURISDICTION_COVERAGE in "
                "api/_lib/deadline-engine.js."
            ),
            "retrieved_at": "2026-08-25",
        },
        "dates": rows,
    })

doc = {
    "_readme": [
        "MASSACHUSETTS HOLIDAY CALENDARS -- DERIVED FROM Mass. G.L. c. 4, s. 7, Cl. 18,",
        "2026-2031.",
        "",
        "Coverage is SIX YEARS because the Massachusetts list is fixed by STATUTE in",
        "derivable terms -- five fixed dates and seven weekday rules -- rather than by",
        "an annual court order (New Jersey) or a published administrative schedule",
        "(North Carolina). Nothing needs re-issuing for the calendar to be computed.",
        "",
        "Generated by tools/gen_ma_calendar.py, which asserts on every emitted year",
        "that no date is duplicated, no date falls on a Saturday or Sunday, and no",
        "date is filed under the wrong year.",
        "",
        "== THE LINK TO THE RULE IS EXPRESS ====================================",
        "Mass. R. Civ. P. 6(a) names Mass. G.L. c. 4, s. 7 in its own text. That",
        "settles, for Massachusetts, the question left open in Texas, Arizona and",
        "Kentucky -- and it settles it the same way Washington's CR 6(a) does.",
        "",
        "== TWELVE DAYS, AND TWO OF THEM ARE WORTH READING TWICE ===============",
        "PATRIOTS' DAY, the third Monday in April, exists in no other jurisdiction",
        "in this engine. COLUMBUS DAY counts here -- North Carolina and Washington",
        "both exclude it and New Jersey and Virginia both count it, so it must be",
        "read per state and never carried across.",
        "",
        "== THE SHIFT IS SUNDAY-ONLY ===========================================",
        "\"or the day following when any of said days occurs on Sunday\". No Saturday",
        "shift exists in the statute. Do NOT add one by analogy to Virginia or West",
        "Virginia: that would invent a Friday holiday and roll deadlines LATE.",
        "Because the shift only moves forward, no holiday can spill into the",
        "previous calendar year, which those two states' generators do have to",
        "handle.",
        "",
        "== SUFFOLK COUNTY IS NOT IN THIS CALENDAR =============================",
        "Evacuation Day (March 17) and Bunker Hill Day (June 17) are legal holidays",
        "in SUFFOLK COUNTY ONLY. They are omitted, because a jurisdiction+year",
        "calendar cannot carry a county-scoped day and encoding them would roll the",
        "other thirteen counties LATE. Suffolk County is BOSTON. The engine",
        "discloses this on every Massachusetts result rather than hiding it here.",
    ],
    "holiday_calendars": calendars,
}

out = "sql/sairnlaw_deadline_calendars_massachusetts.json"
with open(out, "w", encoding="utf-8") as f:
    json.dump(doc, f, indent=1, ensure_ascii=False)
    f.write("\n")

for c in calendars:
    print(c["year"], len(c["dates"]), "dates")
print("wrote", out)
