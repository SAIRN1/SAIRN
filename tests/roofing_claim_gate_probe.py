"""tests/roofing_claim_gate_single_source.js must REFUSE, not merely agree.

Run: python tests/roofing_claim_gate_probe.py

TIER A. `rf_claims` and `rf_claim_photos` are insurance claim records and the
photographic evidence supporting them. The gate this suite guards was
hand-written at SEVEN branches of `api/sd-data.js` before being replaced by one
predicate, and `api/rf-auth.js`'s own header names duplicated role logic as
SAIRNsenior's root cause.

Measured 2026-09-16: 14 of 152 suites on this platform have a negative control.

WHAT THIS SUITE CLAIMS TO DO, AND WHAT IS PLANTED AGAINST IT. It proves
`ownsRow()` answers IDENTICALLY to the expression it replaced, and asserts the
hand-written form has not come back. So every mutation below breaks the
substitution in a way a reader would have to hold seven branches in their head
to notice:

  * the row check drops the assignee comparison, so any authenticated roofer
    acts on any claim;
  * the broad-read roles leak into the WRITE path through seesAllRows;
  * a missing row (`rows[0]` on an empty PostgREST result) starts returning
    true -- the gate opens precisely when the record it is about does not
    exist;
  * the null-session guard goes, which is the one that turns an auth failure
    into an authorisation pass;
  * the predicate reads the CALLER'S PAYLOAD instead of the stored row, which
    is the whole point of the gate and is invisible at every call site.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sabotage_harness import run_probe                           # noqa: E402

SUITE = os.path.join('tests', 'roofing_claim_gate_single_source.js')
AUTH = os.path.join('api', 'rf-auth.js')

MUTATIONS = [
    ("1. the ASSIGNEE comparison goes -- any authenticated roofer acts on any "
     "claim, and every one of the seven call sites still reads correctly",
     AUTH,
     "  return !!(row && row.assigned_employee_id === session.employee_id);",
     "  return !!row;"),

    ("2. a MISSING ROW starts returning true -- the gate opens exactly when the "
     "record it is about does not exist, which is what PostgREST hands back on "
     "an empty result",
     AUTH,
     "function ownsRow(session, row) {\n  if (!session) return false;",
     "function ownsRow(session, row) {\n  if (!session) return false;\n"
     "  if (!row) return true;"),

    ("3. the NULL-SESSION guard goes -- an auth failure becomes an "
     "authorisation pass",
     AUTH,
     "function ownsRow(session, row) {\n  if (!session) return false;\n  if "
     "(seesAllRows(session)) return true;",
     "function ownsRow(session, row) {\n  if (seesAllRows(session)) return true;"),

    # MUTANT 4 WAS EQUIVALENT AND IS REPLACED, not deleted. The first version
    # swapped `if (!session) return false;` for `session = session || {};` and
    # reported the suite SILENT -- but the two are identical for every input,
    # because MANAGEMENT_ROLES[undefined] is already falsy. That is an
    # EQUIVALENT MUTANT, not a coverage gap, and calling it a gap would have
    # been a fabricated finding against a suite that was right.
    #
    # It still earned an arm. seesAllRows is EXPORTED and api/sd-data.js:5656
    # calls it DIRECTLY, while every arm in the suite drove ownsRow(), which
    # refuses a null session at its own guard and never reaches it. The
    # replacement below changes real behaviour.
    ("4. a MISSING SESSION starts SEEING ALL ROWS -- and seesAllRows is called "
     "directly at api/sd-data.js:5656 on the claim-photo read path, so this is "
     "not reachable only through ownsRow's own guard",
     AUTH,
     "function seesAllRows(session) {\n  if (!session) return false;",
     "function seesAllRows(session) {\n  if (!session) return true;"),

    ("5. the role set WIDENS to every management role plus broad read plus "
     "anyone else the table grows -- the duplication this file exists to end, "
     "reintroduced in one line",
     AUTH,
     "  return !!(MANAGEMENT_ROLES[session.role] || BROAD_READ_ROLES[session.role]);",
     "  return !!session.role;"),

    ("6. the broad-READ roles stop counting, so a manager who should see "
     "everything is refused -- the opposite failure, and a gate that only "
     "over-refuses is still a broken gate",
     AUTH,
     "  return !!(MANAGEMENT_ROLES[session.role] || BROAD_READ_ROLES[session.role]);",
     "  return !!MANAGEMENT_ROLES[session.role];"),

    ("7. ownsRow stops being EXPORTED under that name, so the single source "
     "quietly becomes seven again",
     AUTH,
     "module.exports.ownsRow = ownsRow;",
     "module.exports.ownsRowHelper = ownsRow;"),
]

if __name__ == '__main__':
    sys.exit(run_probe(
        SUITE, MUTATIONS,
        title='SAIRNroofing claim gate -- the suite must refuse a predicate '
              'that has stopped being the same answer'))
