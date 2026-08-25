"""Build sql/sairnlaw_deadline_calendars_newjersey.json from the real orders.

New Jersey does not publish a derivable holiday statute for its courts. Its
legal holidays are fixed by ORDER OF THE SUPREME COURT OF NEW JERSEY, one
COURT YEAR at a time, and a court year runs 1 JULY to 30 JUNE. So a CALENDAR
year is always assembled from TWO orders, and a calendar year is complete only
when BOTH of the orders covering it have issued.

THAT RULE IS ENFORCED BY THIS SCRIPT, NOT BY WHOEVER RUNS IT. Every order read
is entered below with the exact span it covers, and a calendar year is emitted
only if both its halves are covered by an entered order. A half-known year is
never written. The reason is in the file this replaces, and it is the whole
point: the engine refuses on a missing YEAR, not on a missing DAY, so a 2027
calendar holding only January-June would look COMPLETE to the engine and would
silently under-report every holiday in the second half of the year. Refusing
the whole year is honest; half-filling it is not.

ONLY DAYS THE ORDERS THEMSELVES CALL "Legal Holiday" ARE ENCODED. Each order
also designates "Court Recess" and "Statewide Judicial College" days, both
marked "(Emergent Matters Only)". N.J. Ct. R. 1:3-1 rolls a last day off "a
Saturday, Sunday or legal holiday" and says nothing about recesses, so encoding
those would roll deadlines LATER than the rule provides -- the direction that
misses a filing. They are listed below as EXCLUDED, with their designation, so
the exclusion is visible and auditable rather than an absence.

DO NOT DERIVE ANY OF THIS FROM N.J.S.A. 36:1-1. That statute is the wrong
source and is wrong in the LATE direction -- see the seed file's readme.

Sources, each read VERBATIM from the court's own PDF (not from a summary, and
not from the HTML notice page, which is a rendering of the order rather than
the order):
  2026-2027 order  n250725d.pdf  dated 2025-07-18, Chief Justice
  2027-2028 order  n260608a.pdf  dated 2026-06-01, /s/ Stuart Rabner, C.J.

Usage:  python tools/gen_nj_calendar.py
"""
import json
from datetime import date

RETRIEVED = "2026-08-25"

NOTICES = "https://www.njcourts.gov/notices/"
FILES = "https://www.njcourts.gov/sites/default/files/notices/"

# ── The orders, transcribed verbatim ──────────────────────────────────────
# `covers` is the court year the order's own operative language states. It is
# what decides whether a calendar year is complete -- it is NOT inferred from
# the dates that happen to appear in `holidays`.
#
# `holidays` carries ONLY the entries the order designates "Legal Holiday".
# `excluded` carries the entries it designates otherwise, kept so a reader can
# confirm nothing was dropped silently.
ORDERS = [
    {
        "court_year": "2025-2026",
        "covers": (date(2025, 7, 1), date(2026, 6, 30)),
        "url": "https://www.njcourts.gov/court-holidays-and-recesses-2025-2026",
        "pdf": FILES + "2024/07/n240705c.pdf",
        "dated": "2024-07-05",
        # Read on 2026-08-25 for the January-June 2026 half of calendar 2026.
        # The July-December 2025 half of this order is outside every calendar
        # year this file emits and is deliberately not transcribed.
        "holidays": [
            ("2026-01-01", "New Year's Day"),
            ("2026-01-19", "Martin Luther King's Birthday"),
            ("2026-02-16", "Washington's Birthday"),
            ("2026-04-03", "Good Friday"),
            ("2026-05-25", "Memorial Day"),
            ("2026-06-19", "Juneteenth Day (third Friday in June)"),
        ],
        "excluded": [],
    },
    {
        "court_year": "2026-2027",
        "covers": (date(2026, 7, 1), date(2027, 6, 30)),
        "url": NOTICES + "order-schedule-of-2026-2027-legal-holidays-and-court-recesses",
        "pdf": FILES + "2025/07/n250725d.pdf",
        "dated": "2025-07-18",
        "holidays": [
            ("2026-07-03", "Independence Day (observed; 4 July 2026 is a Saturday)"),
            ("2026-09-07", "Labor Day"),
            ("2026-10-12", "Columbus Day"),
            ("2026-11-03", "General Election Day"),
            ("2026-11-11", "Veterans' Day"),
            ("2026-11-26", "Thanksgiving Day"),
            ("2026-12-25", "Christmas Day"),
            ("2027-01-01", "New Year's Day"),
            ("2027-01-18", "Martin Luther King's Birthday"),
            ("2027-02-15", "Washington's Birthday"),
            ("2027-03-26", "Good Friday"),
            ("2027-05-31", "Memorial Day"),
            ("2027-06-18", "Juneteenth Day (third Friday in June)"),
        ],
        "excluded": [
            ("2026-11-23", "Statewide Judicial College (Emergent Matters Only)"),
            ("2026-11-24", "Statewide Judicial College (Emergent Matters Only)"),
            ("2026-11-25", "Statewide Judicial College (Emergent Matters Only)"),
            ("2026-12-28", "Court Recess (Emergent Matters Only)"),
            ("2026-12-29", "Court Recess (Emergent Matters Only)"),
            ("2026-12-30", "Court Recess (Emergent Matters Only)"),
            ("2026-12-31", "Court Recess (Emergent Matters Only)"),
        ],
    },
    {
        "court_year": "2027-2028",
        "covers": (date(2027, 7, 1), date(2028, 6, 30)),
        "url": NOTICES + "2027-2028-holiday-and-court-recess-order-july-1-2027-through-june-30-2028",
        "pdf": FILES + "2026/06/n260608a.pdf",
        "dated": "2026-06-01",
        "holidays": [
            ("2027-07-05", "Independence Day (observed; 4 July 2027 is a Sunday)"),
            ("2027-09-06", "Labor Day"),
            ("2027-10-11", "Columbus Day"),
            ("2027-11-02", "General Election Day"),
            ("2027-11-11", "Veterans' Day"),
            ("2027-11-25", "Thanksgiving Day"),
            ("2027-12-24", "Christmas Day (observed; 25 December 2027 is a Saturday)"),
            # THIS ONE SITS IN THE WRONG YEAR ON PURPOSE. The order designates
            # Friday 31 December 2027 a Legal Holiday because 1 January 2028
            # falls on a Saturday, so the observed New Year's Day for 2028 lands
            # in CALENDAR 2027 and belongs in the 2027 calendar. Same
            # year-boundary shape already flagged in West Virginia and Virginia.
            ("2027-12-31", "New Year's Day 2028 (observed; 1 January 2028 is a Saturday)"),
            ("2028-01-17", "Martin Luther King's Birthday"),
            ("2028-02-21", "Washington's Birthday"),
            ("2028-04-14", "Good Friday"),
            ("2028-05-29", "Memorial Day"),
            ("2028-06-16", "Juneteenth Day (third Friday in June)"),
        ],
        "excluded": [
            ("2027-11-22", "Statewide Judicial College (Emergent Matters Only)"),
            ("2027-11-23", "Statewide Judicial College (Emergent Matters Only)"),
            ("2027-11-24", "Statewide Judicial College (Emergent Matters Only)"),
            ("2027-12-27", "Court Recess (Emergent Matters Only)"),
            ("2027-12-28", "Court Recess (Emergent Matters Only)"),
            ("2027-12-29", "Court Recess (Emergent Matters Only)"),
            ("2027-12-30", "Court Recess (Emergent Matters Only)"),
        ],
    },
]


def covered(day):
    """The order covering `day`, or None if no order read covers it."""
    for o in ORDERS:
        if o["covers"][0] <= day <= o["covers"][1]:
            return o
    return None


def complete_years():
    """Calendar years where BOTH halves are covered by an order we have read.

    Checked on the court-year SPANS, not on which dates appear in `holidays` --
    an order with no holiday in some month still covers that month, and an
    order we have not read covers nothing even if we could guess its contents.
    """
    out = []
    span_lo = min(o["covers"][0] for o in ORDERS)
    span_hi = max(o["covers"][1] for o in ORDERS)
    for y in range(span_lo.year, span_hi.year + 1):
        first_half = covered(date(y, 1, 1))
        second_half = covered(date(y, 12, 31))
        if first_half and second_half:
            out.append((y, first_half, second_half))
    return out


years = complete_years()
emitted = {y for y, _, _ in years}

# Which years we hold SOME data for but deliberately refuse to emit. Reported
# out loud, because a silently missing year is indistinguishable from one
# nobody thought about.
partial = sorted({
    date.fromisoformat(d).year
    for o in ORDERS for d, _ in o["holidays"]
} - emitted)

calendars = []
for y, first_half, second_half in years:
    dates = []
    for o in ORDERS:
        for iso, name in o["holidays"]:
            if date.fromisoformat(iso).year == y:
                dates.append({"date": iso, "name": name, "kind": "declared"})
    dates.sort(key=lambda r: r["date"])

    seen = set()
    for d in dates:
        assert d["date"] not in seen, "duplicate %s in %d" % (d["date"], y)
        seen.add(d["date"])
        # A weekend entry would mean a misread order: these are OBSERVED dates
        # and the court never designates a Saturday or Sunday a legal holiday.
        assert date.fromisoformat(d["date"]).weekday() < 5, \
            "%s in %d falls on a weekend -- re-read the order" % (d["date"], y)
        # Nothing may be emitted that the orders designate as a recess.
        for o in ORDERS:
            for ex_iso, ex_kind in o["excluded"]:
                assert d["date"] != ex_iso, \
                    "%s is designated %s and must not be encoded" % (ex_iso, ex_kind)

    srcs = []
    for o in (first_half, second_half):
        if o not in srcs:
            srcs.append(o)

    calendars.append({
        "jurisdiction": "nj",
        "year": y,
        "authority": {
            "citation": "Orders of the Supreme Court of New Jersey scheduling legal holidays and "
                        "court recesses for the %s court year%s, as applied to time computation by "
                        "N.J. Ct. R. 1:3-1"
                        % (" and ".join(o["court_year"] for o in srcs),
                           "s" if len(srcs) > 1 else ""),
            "url": srcs[-1]["url"],
            "order_pdfs": [o["pdf"] for o in srcs],
            "prior_year_order_url": srcs[0]["url"] if len(srcs) > 1 else None,
            "computation_url": "https://www.njcourts.gov/attorneys/rules-of-court",
            "note": (
                "Assembled from %d Order%s of the Supreme Court of New Jersey, each read VERBATIM "
                "from the court's own PDF on %s: %s. New Jersey fixes its court legal holidays by "
                "ORDER, one court year at a time, and a court year runs 1 July to 30 June -- so a "
                "calendar year is always assembled from TWO orders and is emitted only when BOTH "
                "have issued. "
                "ONLY DAYS THE ORDERS THEMSELVES LABEL \"Legal Holiday\" ARE ENCODED. The same orders "
                "separately designate a Statewide Judicial College and a Court Recess, both "
                "\"Emergent Matters Only\"; R. 1:3-1 rolls off a \"legal holiday\" and says nothing "
                "about recesses, so encoding those would push deadlines LATE. Excluded for this "
                "year: %s. "
                "NOT DERIVED AND NOT DERIVABLE: Columbus Day IS a New Jersey legal holiday (North "
                "Carolina and Washington both exclude it); General Election Day is a legal holiday "
                "EVERY year, not even years only, because New Jersey elects its General Assembly "
                "annually; Juneteenth is \"the third Friday in June\" per N.J.S.A. 36:1-1(a), NOT "
                "19 June; and Good Friday moves. The observed-date shift is already applied by the "
                "order and is not computed here. "
                "DO NOT DERIVE THE MISSING YEARS FROM N.J.S.A. 36:1-1 -- that statute is the wrong "
                "source and is wrong in the LATE direction. See the seed readme."
                % (len(srcs), "s" if len(srcs) > 1 else "", RETRIEVED,
                   ", ".join("%s (dated %s)" % (o["court_year"], o["dated"]) for o in srcs),
                   ", ".join("%s %s" % (d, k) for o in srcs for d, k in o["excluded"]
                             if date.fromisoformat(d).year == y) or "none")
            ),
            "retrieved_at": RETRIEVED,
        },
        "dates": dates,
    })

doc = {
    "_readme": [
        "NEW JERSEY HOLIDAY CALENDARS -- READ FROM SUPREME COURT ORDERS, NOT DERIVED.",
        "",
        "Generated by tools/gen_nj_calendar.py. Years emitted: %s."
        % ", ".join(str(y) for y in sorted(emitted)),
        "",
        "== WHY THE COVERAGE IS WHAT IT IS =====================================",
        "New Jersey's court legal holidays are fixed by ORDER, one COURT YEAR at",
        "a time, and a court year runs 1 JULY to 30 JUNE. A CALENDAR year is",
        "therefore always assembled from TWO orders. This generator emits a",
        "calendar year ONLY when both covering orders have issued and been read.",
        "",
        "%s IS NOT EMITTED, and that is deliberate: its January-June half is known"
        % (", ".join(str(y) for y in partial) if partial else "(no partial year)"),
        "from the 2027-2028 order, but its July-December half belongs to a",
        "2028-2029 order that has not been issued. The engine refuses on a missing",
        "YEAR, not a missing DAY, so a half-filled year would look COMPLETE and",
        "would silently under-report every holiday in its second half. Refusing the",
        "whole year is the honest behaviour.",
        "",
        "RE-RUN THIS EVERY JULY, when the next court year's order issues: add the",
        "new order to ORDERS in the generator and the next calendar year starts",
        "emitting on its own. Nothing else needs changing.",
        "",
        "== WHAT IS DELIBERATELY EXCLUDED ======================================",
        "Each order designates some days \"Court Recess\" or \"Statewide Judicial",
        "College\", both \"Emergent Matters Only\". Those are NOT encoded: R. 1:3-1",
        "rolls a last day off \"a Saturday, Sunday or legal holiday\" and does not",
        "mention recesses, so encoding them would roll deadlines LATER than the",
        "rule provides. The courts are largely shut on those days and a",
        "practitioner will feel the difference; the rule still does not make them",
        "legal holidays. A deadline computed across them is EARLY, never late.",
        "The generator asserts that no excluded date is ever emitted.",
        "",
        "== ENTRIES THAT LOOK LIKE MISTAKES AND ARE NOT ========================",
        "COLUMBUS DAY is a New Jersey legal holiday. North Carolina and Washington",
        "both exclude it, for two different reasons. Do not carry those across.",
        "GENERAL ELECTION DAY is a legal holiday EVERY year -- New Jersey elects",
        "its General Assembly annually, unlike the even-year-only states.",
        "JUNETEENTH IS THE THIRD FRIDAY IN JUNE, not 19 June: 19 June 2026,",
        "18 June 2027, 16 June 2028. 2026 is the year the coincidence hides it.",
        "GOOD FRIDAY MOVES: 3 April 2026, 26 March 2027, 14 April 2028.",
        "FRIDAY 31 DECEMBER 2027 IS IN THE 2027 CALENDAR and is New Year's Day",
        "2028 observed, because 1 January 2028 is a Saturday. A year-boundary",
        "entry like this is easy to file under the wrong year; the generator",
        "buckets by the OBSERVED date, which is the date the rule rolls off.",
        "NO WEEKEND-SHIFT RULE IS APPLIED HERE -- the orders state observed dates",
        "directly. This is the opposite of West Virginia and Washington, where a",
        "statute states the shift and the calendar applies it.",
    ],
    "holiday_calendars": calendars,
}

out = "sql/sairnlaw_deadline_calendars_newjersey.json"
with open(out, "w", encoding="utf-8") as f:
    json.dump(doc, f, indent=1, ensure_ascii=False)
    f.write("\n")

for c in calendars:
    print("%d  %2d dates  (from %s)" % (c["year"], len(c["dates"]),
                                        c["authority"]["citation"].split("for the ")[1].split(" court year")[0]))
print("NOT emitted (half-known, refused on purpose):", partial or "none")
print("wrote", out)
