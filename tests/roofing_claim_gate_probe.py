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

    # ARMS 5 AND 6 WERE RE-ANCHORED 2026-09-24, not rewritten. seesAllRows's
    # body changed from `MANAGEMENT_ROLES[session.role] || ...` to
    # `hasRole(MANAGEMENT_ROLES, session.role) || ...` when the role maps were
    # given a null prototype. The old anchors would have stopped matching, and a
    # mutation whose anchor no longer matches is a control that silently stops
    # testing -- the exact staleness shape these probes exist to catch. The
    # defect each arm plants is unchanged.
    ("5. the role set WIDENS to every management role plus broad read plus "
     "anyone else the table grows -- the duplication this file exists to end, "
     "reintroduced in one line",
     AUTH,
     "  return hasRole(MANAGEMENT_ROLES, session.role) || hasRole(BROAD_READ_ROLES, session.role);",
     "  return !!session.role;"),

    ("6. the broad-READ roles stop counting, so a manager who should see "
     "everything is refused -- the opposite failure, and a gate that only "
     "over-refuses is still a broken gate",
     AUTH,
     "  return hasRole(MANAGEMENT_ROLES, session.role) || hasRole(BROAD_READ_ROLES, session.role);",
     "  return hasRole(MANAGEMENT_ROLES, session.role);"),

    ("7. ownsRow stops being EXPORTED under that name, so the single source "
     "quietly becomes seven again",
     AUTH,
     "module.exports.ownsRow = ownsRow;",
     "module.exports.ownsRowHelper = ownsRow;"),

    # ── ARMS 8 AND 9 PLANT THE TWO DEFECTS FIXED 2026-09-24 (H2 d3fbda32) ──
    # Both were LATENT, each held inert by unrelated code elsewhere, so neither
    # would have shown up in any behavioural arm above. They are planted here
    # because a fix whose control has never refused anything is indistinguish-
    # able from a fix that does nothing.
    ("8. the role maps go back to a NORMAL prototype -- seesAllRows still "
     "refuses an inherited name via hasOwnProperty, but the ~40 sites in "
     "api/sd-data.js that index MANAGEMENT_ROLES/BROAD_READ_ROLES DIRECTLY all "
     "start reading 'constructor' as a role again, and nothing at those sites "
     "changed",
     AUTH,
     "  const m = Object.create(null);",
     "  const m = {};"),

    ("9. the rf_claims WRITE stops stripping the caller's own "
     "assigned_employee_id from the stored blob, so the row carries a claimed "
     "assignee beside the authorised one -- invisible today only because the "
     "read branch's Object.assign happens to overlay the real column last",
     os.path.join('api', 'sd-data.js'),
     "      delete dataBlob.assigned_employee_id;\n",
     ""),
]

if __name__ == '__main__':
    sys.exit(run_probe(
        SUITE, MUTATIONS,
        # Both files are staged because arms 8 and 9 and the suite arms that
        # match them landed in the same change as the fix. The worktree is at
        # HEAD, so without this the baseline measures the OLD source against a
        # suite that expects the new one and goes red for the wrong reason.
        stage=(AUTH, os.path.join('api', 'sd-data.js')),
        title='SAIRNroofing claim gate -- the suite must refuse a predicate '
              'that has stopped being the same answer'))
