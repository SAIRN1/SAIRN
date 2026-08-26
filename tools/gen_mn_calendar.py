"""Generate the Minnesota holiday calendar from Minn. Stat. 645.44 subd. 5.

Every day is DERIVED from the statute's own words, quoted in the readme of the
file this writes. Nothing here is copied from a published court schedule.

HOW THE STATUTE REACHES A COURT DEADLINE -- BY EXPRESS CROSS-REFERENCE, WITH A
SECOND LIMB THAT MATTERS. Minn. R. Civ. P. 6.01(d), verbatim:

  "As used in this rule and in Rule 77 (c), 'legal holiday' includes any holiday
   designated in Minnesota Statutes, section 645.44, subdivision 5, as a holiday
   for the state or any statewide branch of government AND ANY DAY THAT THE U.S.
   MAIL DOES NOT OPERATE."

Two limbs, and the second one is not decoration -- it decides one of the two
days the statute leaves optional. See INDIGENOUS PEOPLES DAY below.

THE SHIFT IS BOTH WAYS BUT ENUMERATED TO FIVE NAMED DAYS, which is the most
precise wording of any state seeded. Verbatim: "provided, when New Year's Day,
January 1; or Juneteenth, June 19; or Independence Day, July 4; or Veterans Day,
November 11; or Christmas Day, December 25; falls on Sunday, the following day
shall be a holiday and, provided, when [the same five] falls on Saturday, the
preceding day shall be a holiday."

APPLY IT TO THOSE FIVE ONLY. The other six days are nth-weekday rules that
cannot land on a weekend, so a blanket both-ways shift would be harmless there
by accident rather than by design -- but writing it as a blanket rule invites
the next reader to carry it somewhere it IS wrong. Massachusetts, Missouri and
Wisconsin are all Sunday-only; Virginia and West Virginia are both-ways for
every fixed date. Minnesota is both-ways for an enumerated five. Read per state.

THE TWO OPTIONAL DAYS, AND WHY ONLY ONE IS A PROBLEM. 645.44 subd. 5(a) ends:

  "However, for the executive branch of the state of Minnesota, 'holiday' also
   includes the Friday after Thanksgiving but does not include Indigenous
   Peoples Day. Other branches of state government and political subdivisions
   shall have the option of determining whether Indigenous Peoples Day and the
   Friday after Thanksgiving shall be holidays."

So the JUDICIAL branch may or may not observe either day. That is the same shape
as Wisconsin's clerk-closure question -- except that here Rule 6.01(d)'s second
limb resolves half of it and the other half has a safe default:

  INDIGENOUS PEOPLES DAY (2nd Monday in October) -- ENCODED. It is the federal
  Columbus Day, on which the U.S. mail does not operate, so Rule 6.01(d)'s
  second limb makes it a legal holiday INDEPENDENTLY of whether the judiciary
  exercised its 645.44 option. THIS IS A READING OF THE RULE, NOT A QUOTED
  HOLDING, and it is recorded as such here and in the coverage disclosure. If it
  is wrong, the error direction is LATE, which is why it is the one inference in
  this file worth a lawyer's confirmation.

  FRIDAY AFTER THANKSGIVING -- NOT ENCODED. The U.S. mail DOES operate that day,
  so the postal limb does not reach it, and it depends entirely on the judicial
  branch's option. Omitting it can only ever report EARLY, which is safe, so the
  default is available and taken. Wisconsin had no such safe default.

INDIGENOUS PEOPLES DAY REPLACED COLUMBUS DAY here, as Frances Xavier Cabrini Day
did in Colorado -- 645.44 subd. 5(c) even directs that agreements citing
"Columbus Day" be amended to cite "Indigenous Peoples Day". Same date, different
name. The name is not the point; whether the day counts is.

Usage:  python tools/gen_mn_calendar.py
"""
import json
from datetime import date, timedelta

MON, TUE, WED, THU, FRI, SAT, SUN = range(7)

# The five days 645.44 subd. 5(a) names for the both-ways shift, and ONLY those.
SHIFTABLE = {(1, 1), (6, 19), (7, 4), (11, 11), (12, 25)}


def nth_weekday(year, month, weekday, n):
    d = date(year, month, 1)
    d += timedelta(days=(weekday - d.weekday()) % 7)
    return d + timedelta(days=7 * (n - 1))


def last_weekday(year, month, weekday):
    d = date(year, month + 1, 1) - timedelta(days=1) if month < 12 else date(year, 12, 31)
    d -= timedelta(days=(d.weekday() - weekday) % 7)
    return d


def enumerated_shift(d):
    """645.44 subd. 5(a): Sunday -> the following day; Saturday -> the preceding
    day. Applied ONLY to the five days the statute names."""
    if (d.month, d.day) not in SHIFTABLE:
        return d
    if d.weekday() == SUN:
        return d + timedelta(days=1)
    if d.weekday() == SAT:
        return d - timedelta(days=1)
    return d


def holidays_for(year):
    """(observed, name, derivation) for the eleven statutory days."""
    out = []

    for m, day, name in [
        (1, 1, "New Year's Day"),
        (6, 19, "Juneteenth"),
        (7, 4, "Independence Day"),
        (11, 11, "Veterans Day"),
        (12, 25, "Christmas Day"),
    ]:
        actual = date(year, m, day)
        obs = enumerated_shift(actual)
        deriv = "Minn. Stat. 645.44 subd. 5(a) fixed date %04d-%02d-%02d" % (year, m, day)
        if obs != actual:
            deriv += (" fell on a %s; 645.44 subd. 5(a) names this day in its shift proviso, so the %s "
                      "%s day is the holiday"
                      % (actual.strftime('%A'),
                         'following' if obs > actual else 'preceding',
                         'next' if obs > actual else ''))
            deriv = deriv.replace('  ', ' ')
        out.append((obs, name, deriv))

    out.append((nth_weekday(year, 1, MON, 3), "Martin Luther King's Birthday",
                "Minn. Stat. 645.44 subd. 5(a) third Monday in January"))
    out.append((nth_weekday(year, 2, MON, 3), "Washington's and Lincoln's Birthday",
                "Minn. Stat. 645.44 subd. 5(a) third Monday in February"))
    out.append((last_weekday(year, 5, MON), "Memorial Day",
                "Minn. Stat. 645.44 subd. 5(a) last Monday in May"))
    out.append((nth_weekday(year, 9, MON, 1), "Labor Day",
                "Minn. Stat. 645.44 subd. 5(a) first Monday in September"))
    # THE ONE INFERENCE IN THIS FILE. See the module docstring.
    out.append((nth_weekday(year, 10, MON, 2), "Indigenous Peoples Day",
                "Minn. Stat. 645.44 subd. 5(a) second Monday in October. The judicial branch has the "
                "OPTION whether to observe it, but Minn. R. Civ. P. 6.01(d) independently counts \"any "
                "day that the U.S. mail does not operate\", and this is the federal Columbus Day on "
                "which mail does not run -- so it is encoded on the postal limb rather than on the "
                "branch option. A READING, not a quoted holding; see JURISDICTION_COVERAGE"))
    out.append((nth_weekday(year, 11, THU, 4), "Thanksgiving Day",
                "Minn. Stat. 645.44 subd. 5(a) fourth Thursday in November"))
    return out


# A BOTH-WAYS SHIFT SPILLS ACROSS THE YEAR BOUNDARY, AND THE GENERATOR'S OWN
# ASSERTION CAUGHT IT. This loop originally ran over EMIT alone and asserted
# `obs.year == y`, carried over from the Massachusetts and Missouri generators.
# It fired on 2027-12-31: 1 January 2028 is a SATURDAY, and 645.44 subd. 5(a)
# names New Year's Day in its shift proviso, so the holiday is the PRECEDING
# day -- Friday 31 December 2027, which belongs in the 2027 calendar.
#
# The assertion was right to exist and wrong to be copied. Massachusetts and
# Missouri shift Sundays ONLY, so their holidays can only ever move FORWARD and
# can never leave their own year; asserting it there is correct. Minnesota,
# Virginia and West Virginia all shift both ways, so all three must compute a
# WIDER SPAN than they emit and bucket by the OBSERVED date. Third time a
# carried-over assertion has been the thing that was wrong rather than the data.
SPAN = range(2025, 2033)
EMIT = range(2026, 2032)

buckets = {y: [] for y in EMIT}
for y in SPAN:
    for obs, name, deriv in holidays_for(y):
        if obs.year in buckets:
            buckets[obs.year].append((obs, name, deriv))

calendars = []
for y in EMIT:
    rows = []
    seen = set()
    for obs, name, deriv in sorted(buckets[y], key=lambda r: r[0]):
        iso = obs.isoformat()
        assert iso not in seen, "duplicate %s in %d" % (iso, y)
        seen.add(iso)
        # The enumerated shift moves the five named days OFF both weekend days,
        # and an nth-weekday day cannot land on one, so nothing may be a weekend
        # date here. This differs from Massachusetts and Missouri, where a
        # Saturday entry is CORRECT because their statutes shift only Sundays --
        # do not carry this assertion to a Sunday-only state, and do not carry
        # theirs to here.
        assert obs.weekday() < SAT, \
            "%s in %d is a weekend day -- 645.44's enumerated both-ways shift did not apply" % (iso, y)
        # NOT an `obs.year == y` assertion -- see the SPAN comment above. Rows
        # are bucketed BY the observed year, so this holds by construction and
        # a 31 December entry for the following year's New Year's Day is
        # correct, not a defect.
        assert obs.year == y, "%s bucketed under %d -- bucketing is broken" % (iso, y)
        rows.append({"date": iso, "name": name, "kind": "declared", "derivation": deriv})

    calendars.append({
        "jurisdiction": "mn",
        "year": y,
        "authority": {
            "citation": "Minn. Stat. 645.44 subd. 5 (holidays), as expressly incorporated for time "
                        "computation by Minn. R. Civ. P. 6.01(d)",
            "url": "https://www.revisor.mn.gov/statutes/cite/645.44",
            "computation_url": "https://www.revisor.mn.gov/court_rules/cp/id/6/",
            "note": (
                "EVERY DATE HERE IS DERIVED FROM THE STATUTE, not copied from any published court "
                "schedule. "
                "THE LINK IS EXPRESS AND HAS TWO LIMBS: Minn. R. Civ. P. 6.01(d) counts \"any holiday "
                "designated in Minnesota Statutes, section 645.44, subdivision 5, as a holiday for the "
                "state or any statewide branch of government AND ANY DAY THAT THE U.S. MAIL DOES NOT "
                "OPERATE.\" The second limb is load-bearing -- see Indigenous Peoples Day. "
                "THE SHIFT IS BOTH WAYS BUT ENUMERATED TO FIVE NAMED DAYS (New Year's Day, Juneteenth, "
                "Independence Day, Veterans Day, Christmas Day): Sunday -> the following day, Saturday "
                "-> the preceding day. It is applied to those five ONLY. Massachusetts, Missouri and "
                "Wisconsin shift Sundays only; Virginia and West Virginia shift every fixed date both "
                "ways. Minnesota is neither -- read per state, never carried. "
                "INDIGENOUS PEOPLES DAY (second Monday in October) IS ENCODED ON THE POSTAL LIMB. "
                "645.44 subd. 5(a) gives the judicial branch the OPTION whether to observe it, but it "
                "is the federal Columbus Day, on which the U.S. mail does not operate, so R. 6.01(d)'s "
                "second limb reaches it regardless of that option. THAT IS A READING OF THE RULE, NOT A "
                "QUOTED HOLDING, and if it is wrong the error runs LATE -- it is the one inference in "
                "this calendar worth a lawyer's confirmation. It replaced Columbus Day; 645.44 subd. "
                "5(c) directs agreements citing \"Columbus Day\" to be amended to cite \"Indigenous "
                "Peoples Day\". "
                "WHAT IS DELIBERATELY ABSENT: (1) THE FRIDAY AFTER THANKSGIVING, which the same "
                "subdivision also leaves to the judicial branch's option and which the postal limb does "
                "NOT reach, because the U.S. mail operates that day. Omitting it can only ever report "
                "EARLY, so the safe default is taken. (2) One-off days on which the U.S. mail does not "
                "operate for reasons other than a federal holiday -- unknowable in advance, EARLY. "
                "(3) Days the Court Administrator's office is inaccessible under R. 6.01(a)(4), which "
                "is an ADDITIONAL limb on top of this list rather than a replacement for it, and is "
                "therefore also EARLY. See JURISDICTION_COVERAGE in api/_lib/deadline-engine.js."
            ),
            "retrieved_at": "2026-08-26",
        },
        "dates": rows,
    })

doc = {
    "_readme": [
        "MINNESOTA HOLIDAY CALENDARS -- DERIVED FROM Minn. Stat. 645.44 subd. 5,",
        "2026-2031.",
        "",
        "Coverage is SIX YEARS because the list is fixed by STATUTE in derivable",
        "terms -- five fixed dates and six weekday rules -- rather than by an annual",
        "court order (New Jersey) or a published administrative schedule (North",
        "Carolina). Nothing needs re-issuing for it to be computed.",
        "",
        "Generated by tools/gen_mn_calendar.py, which asserts per year that no date",
        "is duplicated, none falls on a weekend, and none is filed under the wrong",
        "year.",
        "",
        "== THE DEFINITION HAS TWO LIMBS AND THE SECOND ONE MATTERS =============",
        "R. 6.01(d) counts 645.44 subd. 5 holidays AND \"any day that the U.S. mail",
        "does not operate\". That second limb is what puts INDIGENOUS PEOPLES DAY in",
        "this calendar even though the judicial branch merely has the OPTION to",
        "observe it under the statute -- it is the federal Columbus Day and mail",
        "does not run. THAT IS A READING, NOT A QUOTED HOLDING, and it is the one",
        "inference here whose error direction is LATE. Flagged for a lawyer.",
        "",
        "== THE SHIFT IS BOTH WAYS BUT ONLY FOR FIVE NAMED DAYS =================",
        "New Year's Day, Juneteenth, Independence Day, Veterans Day, Christmas Day.",
        "Sunday -> following day; Saturday -> preceding day. Do NOT generalise it.",
        "MA, MO and WI shift Sundays only. VA and WV shift every fixed date both",
        "ways. Minnesota is a third pattern.",
        "",
        "== THE FRIDAY AFTER THANKSGIVING IS NOT HERE, DELIBERATELY =============",
        "Same optional status as Indigenous Peoples Day, but the postal limb does",
        "NOT reach it because mail operates. Omitting runs EARLY, which is safe, so",
        "the safe default is taken. Confirm against the Judiciary's own published",
        "schedule before relying on a date that lands there.",
    ],
    "holiday_calendars": calendars,
}

out = "sql/sairnlaw_deadline_calendars_minnesota.json"
with open(out, "w", encoding="utf-8") as f:
    json.dump(doc, f, indent=1, ensure_ascii=False)
    f.write("\n")

for c in calendars:
    print(c["year"], len(c["dates"]), "dates")
print("wrote", out)
