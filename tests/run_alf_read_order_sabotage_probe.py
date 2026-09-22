"""api/alf-append-only-read-order.test.js must REFUSE, not merely agree.

Run: python tests/run_alf_read_order_sabotage_probe.py

# REQUIREMENT: the arm guarding the six SAIRNcare append-only trail reads must
#   go RED when any one of them loses its order= clause, when a trail is
#   ordered by the wrong column, when the direction is flipped away from the
#   renderers, when the clause survives only as prose in a comment, when the
#   read is restructured out of the arm's sight, and when a SEVENTH trail is
#   added upstream with no ordering declared -- because an unordered read is
#   invisible in every other way this repo checks

THE DEFECT THIS ARM GUARDS WAS FOUND BY READING, NOT BY A TEST, and the two
existing SAIRNcare suites could not have found it: both
tests/sairncare/test-alf-mar.js and tests/sairncare/test-alf-signals.js assert
the read URL with an UNANCHORED regex that stops at `...data`, so they matched
before the fix and match after it. A suite that passes identically either side
of a change is not evidence about that change, which is the whole reason this
probe exists rather than "the tests are green".

SEVEN MUTATIONS. Three of them are the ones that read as correct:

  * MUTATION 2 removes the clause from alf_op_audits -- one of the THREE trails
    the handoff that commissioned this work never named. If the arm were the
    three-table version it would be green here while three reads sat unordered,
    which is precisely the "all-clear over reads it never looked at" shape.

  * MUTATION 4 flips alf_mar from desc to asc. Nothing errors, every other arm
    passes, and the only symptom is that same-day MAR entries tie-break against
    the direction the renderer is showing them in -- the defect restored at half
    strength, which is harder to see than restoring it whole.

  * MUTATION 6 deletes the clause from the code and writes it into a comment
    immediately above. Any check that greps the raw file for `order=` scores
    this as fixed. The arm strips comment lines before scanning for exactly this
    reason and the mutation is here to prove the stripping actually runs.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sabotage_harness import run_probe                      # noqa: E402

SUITE = os.path.join('api', 'alf-append-only-read-order.test.js')
SRC = os.path.join('api', 'sd-data.js')
SIBLING = os.path.join('api', 'alf-append-only-fail-closed.test.js')

MAR_READ = ("      const r = await fetch(rest('alf_mar?license_hash=eq.' + enc(licHash) "
            "+ '&select=entry_id,resident_id,assigned_employee_id,entry_type,data"
            "&order=created_at.desc'), { headers });")

MUTATIONS = [
    ("1. THE ORIGINAL DEFECT RESTORED on the worst of the six: alf_claim_routes "
     "loses its order= clause. prRenderRecorded has no client-side sort at all, "
     "so the server order IS the display order and there is none",
     SRC,
     ("rest('alf_claim_routes?license_hash=eq.' + enc(licHash) + "
      "'&select=entry_id,resident_id,service_month,data,decided_by,created_at"
      "&order=created_at.desc')"),
     ("rest('alf_claim_routes?license_hash=eq.' + enc(licHash) + "
      "'&select=entry_id,resident_id,service_month,data,decided_by,created_at')")),

    ("2. READS AS OUT OF SCOPE: alf_op_audits loses its clause -- a trail the "
     "commissioning handoff never named. A three-table arm passes this mutation "
     "and reports the class clean",
     SRC,
     ("rest('alf_op_audits?license_hash=eq.' + enc(licHash) + "
      "'&select=entry_id,record_type,observed_on,passed,data,recorded_by,"
      "reviewed_by,reviewed_at,created_at&order=created_at.desc')"),
     ("rest('alf_op_audits?license_hash=eq.' + enc(licHash) + "
      "'&select=entry_id,record_type,observed_on,passed,data,recorded_by,"
      "reviewed_by,reviewed_at,created_at')")),

    ("3. READS AS A TIDY-UP: alf_signals is ordered by created_at like its five "
     "siblings instead of recorded_at, silently sorting a monitoring log by when "
     "the row was WRITTEN rather than when the signal OCCURRED",
     SRC,
     "'&select=entry_id,resident_id,signal_type,data,recorded_at&order=recorded_at.desc'",
     "'&select=entry_id,resident_id,signal_type,data,recorded_at&order=created_at.desc'"),

    ("4. HALF THE DEFECT, WHICH IS HARDER TO SEE THAN ALL OF IT: alf_mar flips "
     "to asc, so same-day entries tie-break oldest-first underneath a renderer "
     "that is sorting them newest-first",
     SRC,
     "'&select=entry_id,resident_id,assigned_employee_id,entry_type,data&order=created_at.desc'",
     "'&select=entry_id,resident_id,assigned_employee_id,entry_type,data&order=created_at.asc'"),

    ("5. THE FIX IS STILL THERE BUT THE ARM CAN NO LONGER SEE IT: the alf_mar "
     "read is hoisted into a local, so the arm finds ZERO list reads for that "
     "table. A sweep over a read it never found is not a pass and must say so",
     SRC,
     MAR_READ,
     ("      const marSel = 'alf_mar?license_hash=eq.' + enc(licHash) "
      "+ '&select=entry_id,resident_id,assigned_employee_id,entry_type,data"
      "&order=created_at.desc';\n"
      "      const r = await fetch(rest(marSel), { headers });")),

    ("6. THE CLAUSE SURVIVES AS PROSE ONLY: alf_mar's order= is deleted from the "
     "code and written into a comment directly above it. Any check that greps "
     "the raw file scores this as fixed",
     SRC,
     MAR_READ,
     ("      // ordered &order=created_at.desc -- see the header above\n"
      "      const r = await fetch(rest('alf_mar?license_hash=eq.' + enc(licHash) "
      "+ '&select=entry_id,resident_id,assigned_employee_id,entry_type,data'), "
      "{ headers });")),

    ("7. A SEVENTH TRAIL APPEARS UPSTREAM with no ordering declared. The arm "
     "takes its table list from the sibling ON PURPOSE so this cannot be missed; "
     "a hand-typed local copy would be green here",
     SIBLING,
     "const TABLES = ['alf_mar', 'alf_incidents', 'alf_signals',\n"
     "                'alf_claim_routes', 'alf_staff_credentials', 'alf_op_audits'];",
     "const TABLES = ['alf_mar', 'alf_incidents', 'alf_signals',\n"
     "                'alf_claim_routes', 'alf_staff_credentials', 'alf_op_audits',\n"
     "                'alf_care_notes'];"),
]

if __name__ == '__main__':
    sys.exit(run_probe(
        SUITE, MUTATIONS,
        title=('api/alf-append-only-read-order.test.js must refuse an unordered, '
               'mis-ordered, prose-only or invisible trail read'),
        # sd-data.js carries the fix and is NOT committed yet; the worktree is at
        # HEAD, so without this the baseline measures the OLD unordered reads
        # against the NEW arm, goes red, and no mutation below would mean
        # anything. The sibling is NOT staged -- it is unmodified in this clone,
        # so HEAD's copy is the right one and mutation 7 edits that.
        stage=(SRC,)))
