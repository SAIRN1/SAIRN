"""tests/sairnvet_controlled_export.js must REFUSE, not merely agree.

Run: python tests/sairnvet_controlled_export_probe.py

TIER A, AND IT WAS ONE OF 37 UNCONTROLLED TIER A SUITES. Measured 2026-09-18
with `python tools/suite_control_triage.py`: 166 suites, 58 with a negative
control, 108 without, and 37 of those 108 name a Tier A resource. This closes
one of the 37. `sv_controlled` is a Class A, DEA-relevant record and
svExportControlled() is the only way it leaves the app as a file.

── WHY THIS SUITE SPECIFICALLY NEEDED A CONTROL, AND IT IS NOT A HYPOTHETICAL ─
This suite was RED for seventeen hours and nobody noticed. The 2026-09-17 CSV
formula-injection sweep (885fd0b9) made svExportControlled() call svCsvCell(),
and the suite extracts svExportControlled BY SIGNATURE into a VM sandbox that
did not contain the guard -- so from that commit it ran 3 passed / 19 FAILED
with `svCsvCell is not defined`. Driven both ways to establish that rather
than infer it: 22/22 green against sairnvet.html at 885fd0b9^, 3/22 at HEAD.

A suite going RED is the LOUD failure and it still went unread for most of a
day. The quiet one is what this file is for: every mutation below leaves the
function running and the file downloading, and changes only what is INSIDE it.

── WHAT IS PLANTED, AND WHY EACH ONE LOOKS FINE IN REVIEW ──────────────────
  * the per-drug quantity column stops reaching the file -- the export still
    writes a row per drug, with the drug, the schedule and the note, and the
    one number a DEA inspection is counting is gone;
  * the unit warning leaves the preamble. The KPI directly above this table
    recorded a real defect where millilitres were added to milligrams and
    printed as a controlled-substance balance, so the line saying DO NOT SUM
    is load-bearing and its absence is invisible in a diff of the data rows;
  * the not-tamper-evident disclosure leaves the preamble, which makes the
    file read as more than it is -- the whole risk on a DEA record;
  * the row COUNT is computed from the content selector instead of the body
    selector, so it silently includes the header row and the file overstates
    how many drugs are on the register by exactly one;
  * the CSV guard is dropped from the DATA rows only. The preamble still goes
    through svCsvCell, so the file still looks quoted and the helper is still
    called -- and a drug name or transaction note beginning with = is a live
    formula again. This is the mutation that would survive a reading.
"""
# REQUIREMENT: tests/sairnvet_controlled_export.js must go RED when the
#   controlled-substance export quietly stops carrying the per-drug quantity,
#   the do-not-sum unit warning, the not-tamper-evident disclosure, an honest
#   row count, or the CSV formula guard on its data rows -- each of which
#   leaves the function running and the file downloading, so a green suite
#   over any of them is a DEA-relevant record that reads as more than it is
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sabotage_harness import run_probe                           # noqa: E402

SUITE = os.path.join('tests', 'sairnvet_controlled_export.js')
VET = 'sairnvet.html'

# ── THE ANCHOR HAS TO REACH THE DOWNLOAD LINE, AND THAT IS NOT VERBOSITY ────
# svExportDoseAudit() and svExportControlled() share their row loop BYTE FOR
# BYTE -- eight identical lines. A mutation anchored on the loop alone matched
# TWICE, and the harness refused it as ANCHOR-2 rather than mutating the wrong
# function, which is the whole reason it counts. The first line that differs is
# `a.download`, so the anchor runs from the loop to there. It is brittle to a
# reflow of those eight lines and that is the SAFE brittleness: a stale anchor
# here fails LOUD as ANCHOR-0, where a str.replace that silently matches
# nothing would leave the arm running against an unmodified file and passing.
ROW_LOOP = (
    "    row.querySelectorAll('th,td').forEach(function(cell){ "
    "rowData.push(q(cell.textContent)); });\n"
    "    csv += rowData.join(',') + '\\n';\n"
    "  });\n"
    "  var blob = new Blob([csv], {type:'text/csv'});\n"
    "  var url = URL.createObjectURL(blob);\n"
    "  var a = document.createElement('a');\n"
    "  a.href = url;\n"
    "  a.download = 'controlled-substance-register.csv';")


def row_loop_with(replacement_loop_line):
    """The same unique span with only its first line replaced."""
    return replacement_loop_line + ROW_LOOP[ROW_LOOP.index('\n'):]


MUTATIONS = [
    ("1. the ON HAND quantity never reaches the file -- every other column "
     "still does, and the file still downloads",
     VET,
     ROW_LOOP,
     row_loop_with("    row.querySelectorAll('th,td').forEach(function(cell,i){ "
                   "rowData.push(i===2?q(''):q(cell.textContent)); });")),

    ("2. the DO-NOT-SUM unit warning leaves the preamble -- the column the KPI "
     "above this table already got wrong once is now unlabelled",
     VET,
     "    [q('ON HAND IS PER-DRUG, IN THAT DRUG’S OWN UNIT. Do not sum the column: '",
     "    [q('ON HAND IS PER-DRUG. '"),

    ("3. the NOT TAMPER-EVIDENT disclosure leaves the preamble, so the file "
     "reads as more than it is",
     VET,
     "    [q('THIS RECORD IS NOT APPEND-ONLY AND IS NOT TAMPER-EVIDENT. Rows are '",
     "    [q('THIS RECORD IS MAINTAINED IN THE APP. Rows are '"),

    ("4. the row count is taken from the CONTENT selector, so it silently "
     "includes the header and the register overstates its own size by one",
     VET,
     "  try { rowCount = Math.max(0, table.querySelectorAll('tbody tr').length); } catch(e){}",
     "  try { rowCount = Math.max(0, table.querySelectorAll('tr').length); } catch(e){}"),

    ("5. THE ONE THAT WOULD SURVIVE A READING: the CSV guard is dropped from "
     "the DATA rows only. The preamble still calls svCsvCell, so the file is "
     "still quoted and the helper is still there -- and a drug name or note "
     "beginning with = is a live formula again",
     VET,
     ROW_LOOP,
     row_loop_with("    row.querySelectorAll('th,td').forEach(function(cell){ "
                   "rowData.push('\"' + String(cell.textContent) + '\"'); });")),

    # ── 6 AND 7 GUARD THE DISCLOSURE ITSELF, added 2026-09-21 ────────────
    # Both keep the file syntactically valid and the guard itself running.
    # That is the point: the defect being planted is not "the apostrophe
    # stopped happening", it is "the apostrophe still happens and the file
    # stopped saying so", which is the state this export was in until today
    # and which no reader could detect from the file.
    ("6. THE DISCLOSURE STOPS NAMING THE APOSTROPHE -- the guard still runs, "
     "the preamble still has a line about it, and the one word a downstream "
     "parser would search for is gone",
     VET,
     "       + 'plain number is prefixed with an apostrophe, so a spreadsheet cannot '",
     "       + 'plain number is prefixed with a marker, so a spreadsheet cannot '"),

    ("7. THE DISCLOSURE SAYS IT HAPPENS AND STOPS SAYING WHAT TO DO -- a "
     "reader learns a transformation exists and not that they must strip it "
     "before parsing, which is the half that changes anybody's code",
     VET,
     "       + 'on screen; software reading this file does not, and must strip a '\n"
     "       + 'leading apostrophe before parsing a value.')],",
     "       + 'on screen; software reading this file does not.')],"),
]

if __name__ == '__main__':
    sys.exit(run_probe(
        SUITE, MUTATIONS,
        title='SAIRNvet controlled-substance export -- the suite must refuse '
              'an export that has quietly stopped carrying the quantity, the '
              'disclosures, or the guard',
        # sairnvet.html IS STAGED TOO, added 2026-09-21. The worktree is at
        # HEAD, so an uncommitted change to the EXPORTER is not in it -- and
        # the disclosure arms this suite gained assert on preamble text that
        # lives in the exporter. Without this the baseline went red for a
        # reason that has nothing to do with any mutation, which is exactly
        # the case the harness's `stage` argument documents.
        stage=(SUITE, VET)))
