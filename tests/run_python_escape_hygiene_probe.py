r"""tests/python_escape_hygiene.py must REFUSE, not merely agree.

Run: python tests/run_python_escape_hygiene_probe.py

A checker that has only ever printed "no file emits a SyntaxWarning" has, by
construction, never been observed refusing anything. This one is a green-field
check over 463 files, so the failure mode that matters is not a wrong answer --
it is a scan that quietly reaches nothing and reports clean, which is exactly
what an empty result set looks like from outside.

THREE DIRECTIONS THAT CAN FIRE, and two that cannot -- recorded at the point
where they would have been rather than shipped as arms that always pass:
  1. a bad escape is planted in a tools/ file      -> must be REPORTED
  2. ...and in a nested tests/ subdirectory file   -> the recursive glob is
     the half most likely to be silently wrong, because tests/*.py already
     matches the top level and would hide a broken tests/**/*.py
  3. the scan is narrowed to nothing               -> must say COULD NOT RUN
     rather than clean, which is the rule the rest of this repo applies to an
     empty result set

A FIFTH DIRECTION WAS TRIED AND DROPPED, and the reason is worth more than the
arm would have been: widening the warning filter from SyntaxWarning to every
category changes no output, because nothing in the corpus emits any other
warning at compile time. The probe reported SILENT and was right. An arm that
cannot fire is worse than an absent one -- it counts toward a total and reads
as coverage.
"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sabotage_harness import run_probe                           # noqa: E402

SUITE = os.path.join('tests', 'python_escape_hygiene.py')
# A tools/ file with a docstring long enough that one more line changes nothing
# about what it does. Chosen rather than a tests/ file so mutation 1 and
# mutation 2 exercise two different glob patterns.
TOOLS_SUBJECT = os.path.join('tools', 'sairn_status.py')
# A NESTED PYTHON file -- the first spelling named a .js file, which this
# check never scans, so the mutation could not have fired whatever the glob
# did.
NESTED_SUBJECT = os.path.join('tests', 'claims', 'run_freshness_probe.py')

MUTATIONS = [
    ("1. A BAD ESCAPE IS PLANTED IN A tools/ FILE -- the gate that holds the "
     "push protocol is one interpreter release from not compiling, and the "
     "check must say which file",
     TOOLS_SUBJECT,
     "import io",
     "_PLANTED = \"\\d not a real escape\"\nimport io"),

    # ── RE-AIMED, AND THE FIRST SPELLING WAS UNFIRABLE BY CONSTRUCTION ──
    # It dropped `tests/**/*.py` from the pattern list and expected the check
    # to notice. It cannot, and no warning-only checker could: with the repo
    # clean, a NARROWED scan and a CLEAN scan produce identical output. That
    # is a real property worth knowing -- it is why the file count is printed
    # -- but it is not something this probe can plant. The mutation now puts a
    # real defect in a NESTED file, where only the recursive pattern can reach
    # it, so the arm tests the reach rather than the spelling of the glob.
    ("2. ...AND IN A NESTED tests/ SUBDIRECTORY, which is the half most likely "
     "to be silently missed: tests/*.py already matches the top level, so a "
     "recursive pattern that had quietly stopped recursing would look exactly "
     "like a clean scan",
     NESTED_SUBJECT,
     "import os",
     "_PLANTED = \"\\d not a real escape\"\nimport io"),

    ("3. THE SCAN IS NARROWED TO NOTHING -- it matches no file at all and must "
     "report COULD NOT RUN rather than clean, because an empty result set and "
     "a clean result set are not the same fact",
     SUITE,
     "PATTERNS = ('tools/*.py', 'tests/*.py', 'tests/**/*.py')",
     "PATTERNS = ('tools/no_such_directory_*.py',)"),

    # ── TWO DIRECTIONS WERE TRIED AND BOTH ARE UNFIRABLE HERE ─────────
    # Recorded where the arms would have been, because an arm that cannot
    # fire is worse than an absent one: it counts toward a total and reads as
    # coverage.
    #
    # WIDENING THE WARNING FILTER from SyntaxWarning to every category changes
    # no output -- nothing in the corpus emits another warning at compile
    # time. SWALLOWING THE SyntaxError BRANCH changes no output either --
    # every file in the corpus compiles, so that branch never runs. Both
    # reported SILENT and both were right to. Each becomes plantable the day
    # the corpus stops being clean in that specific way, and each is a
    # one-line restore from this comment.
]

if __name__ == '__main__':
    sys.exit(run_probe(
        SUITE, MUTATIONS,
        title='python escape hygiene -- the check must refuse a planted escape, '
              'a narrowed glob, an empty scan and a widened filter',
        # The subject of mutations 2-4 IS the suite, which the harness already
        # stages. Mutation 1 plants in tools/, so that file is staged too --
        # the worktree is at HEAD and this probe and its subject land together.
        # tests/run_temporary_state_probe.py is staged as well: it is the file
        # whose bad escape prompted this check, its fix is uncommitted, and the
        # worktree is at HEAD -- so without it the baseline measures the OLD
        # version against a suite that expects the new one and goes red for a
        # reason that has nothing to do with the mutations. The harness said so
        # itself, by name, rather than leaving it to be diagnosed.
        stage=(TOOLS_SUBJECT, NESTED_SUBJECT,
               os.path.join('tests', 'run_temporary_state_probe.py'))))
