"""Negative control for tests/run_defect_register_vocab_probe.py.

    python tests/run_defect_register_vocab_sabotage_probe.py

Exit 0  every planted defect was refused by the suite
Exit 1  one was not -- the suite does not bite where it says it does
Exit 3  COULD NOT RUN -- never folded into either of the other two

── THE MUTATIONS ARE THE ARGUMENTS SOMEBODY WILL MAKE ──────────────────────
Both changes under test are REFUSALS, and every refusal in a tool eventually
meets a session in a hurry with a good reason to remove it. These are the five
good reasons:

  1 "--app was fine as free text"        -- it drifted five times on one value
  2 "the note length is arbitrary"       -- it is the only thing a reader of an
                                            unverifiable pointer actually has
  3 "why can't an external cite an app"  -- because the per-app rate would gain
                                            a numerator with no denominator
  4 "resolve() can treat it like a sha"  -- then --check reports it as VERIFIED
                                            when nothing looked at it
  5 "zero lines looks like a bug"        -- a fabricated count deflates a
                                            defect rate with a number nobody
                                            measured

A SIXTH WAS WRITTEN, RAN SILENT AND IS KEPT AS A COMMENT below rather than
deleted: it removed a `continue` from cmd_reseat that could not fire. The
suite stayed green because the guard was already redundant, so the GUARD was
deleted rather than the arm weakened.

4 and 5 are the quiet ones. None of them makes the tool fail; each makes it
answer confidently about something it never checked, which is the defect class
this whole register exists to count.

STAGED: tools/defect_register.py and docs/defect-density-register.json,
because neither the code under test nor the register it validates is committed
when this first runs.
"""
# REQUIREMENT: the register's app vocabulary and its external-citation format
#   keep refusing what they cannot verify, because every one of those refusals
#   has a plausible argument for removing it
#
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sabotage_harness import run_probe                          # noqa: E402

SUITE = os.path.join('tests', 'run_defect_register_vocab_probe.py')
TOOL = os.path.join('tools', 'defect_register.py')
REG = os.path.join('docs', 'defect-density-register.json')

MUTATIONS = [
    # 1. Back to free text. The detector under --check still exists, so the
    #    tool does not fail -- it just goes back to catching the drift on the
    #    NEXT clone instead of at the keyboard that caused it.
    ('--app goes back to free text', TOOL,
     "    if app not in apps:\n",
     "    if False:\n"),

    # 2. A pointer this repo cannot check is worth exactly the sentence telling
    #    a reader where to go and look.
    ('the external note loses its length floor', TOOL,
     "        if len(str(ext_note).strip()) < 40:\n",
     "        if False:\n"),

    # 3. An external record against an app file is a defect counted against
    #    lines that are not in this repo.
    ('an external citation may name a real app file', TOOL,
     "        if app not in NON_APP_ENTITIES:\n",
     "        if False:\n"),

    # 4. THE QUIET ONE. Without the explicit branch the external cite falls
    #    through to rev-parse, fails, then to the subject index -- and --check
    #    reports it as a record pointing at nothing, or worse, re-seats it onto
    #    a local commit that happens to share a subject.
    ('resolve() stops recognising an external citation', TOOL,
     "        return rec['commit'], 'external'\n",
     "        pass\n"),

    # ── A SIXTH MUTATION WAS WRITTEN, RAN SILENT, AND IS RECORDED RATHER
    # ── THAN DELETED, because a dropped arm nobody mentions is the thing this
    # ── file is about.
    #
    # It planted the removal of `if how == 'external': continue` from
    # cmd_reseat and THE SUITE STAYED GREEN. That was not a hole in the suite:
    # the `continue` could not fire. With resolve() returning 'external', the
    # branches after it test `how == 'sha'` and `how in ('subject',
    # 'dangling')`, so the record already falls through untouched. A guard
    # indistinguishable from its own absence is PR 1.1, in the tool that
    # exists to count that shape -- so the `continue` was DELETED and the
    # reason written where it used to be.
    #
    # The hazard it was aimed at is still guarded, by mutation 4 above:
    # resolve() is the single place that knows what an external citation is,
    # and removing its branch takes this suite red.

    # 5. One line added, one removed -- small enough to look like a rounding
    #    detail and enough to put a defect into a rate it does not belong in.
    ('the external line counts are fabricated rather than zero', TOOL,
     "                'lines_added': 0, 'lines_removed': 0,\n",
     "                'lines_added': 1, 'lines_removed': 1,\n"),
]

if __name__ == '__main__':
    sys.exit(run_probe(
        SUITE, MUTATIONS, stage=(TOOL, REG),
        title='negative control: the register keeps refusing what it cannot '
              'verify, and keeps saying which pointers were never checked'))
