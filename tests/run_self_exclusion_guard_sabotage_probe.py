"""tests/run_cross_tenant_scope_probe.py must REFUSE a broken SELF_EXCLUDED.

Run: python tests/run_self_exclusion_guard_sabotage_probe.py

# REQUIREMENT: the control on the cross-tenant grader must go RED when the
#   grader's self-exclusion list stops excluding -- when an entry is renamed
#   out of existence, when it is spelled in a form the scan never emits, when
#   the loop stops consulting the list, when the skip swallows everything, and
#   when a NEW file whose subject is the grader is not listed

WHAT WAS OPEN. SELF_EXCLUDED exists because the grader was counting its OWN
fixture bodies as platform coverage -- two of three reported GENUINEs were one
real file and the grader's own control. The fix was a tuple of string literals
naming other files, and NOTHING guarded it. A string literal pointing at
another file is the exact shape this platform records as "nothing announces the
day a check stops testing anything": rename either file and the exclusion
silently excludes nothing, while the report keeps PRINTING both names as
excluded -- a claim that the exclusion happened, over one that did not.

── THE COMPLETENESS ARM IS THE ONE THAT FOUND SOMETHING ───────────────────
Arms 1-4 below guard the list against decay. Arm 5 guards it against being
INCOMPLETE, which a literal cannot answer about itself, and it is the only one
that needed no sabotage to earn its place: on its first run it named
tests/cross_tenant_dispatchers_review_probe.py, a third file that imports the
grader, quotes the reference suite's CROSS-TENANT-ISOLATION line in its prose,
and was being credited with law_invoices, law_opaccounts and law_barcerts "on
the declaration alone".

── AND ARM 4 IS WHY ARM 3 IS NOT ENOUGH ───────────────────────────────────
A skip that skipped EVERY file would satisfy "the excluded file is not cited".
The control asserts the citation list is non-empty for the same resource, so a
guard that passes by matching nothing is refused rather than counted.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sabotage_harness import run_probe                           # noqa: E402

SUITE = os.path.join('tests', 'run_cross_tenant_scope_probe.py')
TOOL = os.path.join('tools', 'cross_tenant_isolation_scope.py')

MUTATIONS = [
    ("1. AN ENTRY NAMES A FILE THAT DOES NOT EXIST -- the rename shape, in "
     "which the report still prints the name as excluded and the exclusion "
     "excludes nothing",
     TOOL,
     "    'tests/run_cross_tenant_scope_probe.py',",
     "    'tests/run_cross_tenant_scope_probe_OLD.py',"),

    ("2. AN ENTRY IS SPELLED IN A FORM THE SCAN NEVER EMITS -- the file is on "
     "disk and `os.path.isfile` would call it healthy, but all_files() yields "
     "forward slashes and no './' prefix, so it matches nothing",
     TOOL,
     "    'tests/cross_tenant_scope_grader_review_probe.py',\n"
     "    # THE THIRD, AND IT WAS FOUND BY A GUARD RATHER THAN BY A READER",
     "    './tests/cross_tenant_scope_grader_review_probe.py',\n"
     "    # THE THIRD, AND IT WAS FOUND BY A GUARD RATHER THAN BY A READER"),

    ("3. THE LOOP STOPS CONSULTING THE LIST -- the tuple is intact, both "
     "list-shape arms stay green, and the grader is counting itself again",
     TOOL,
     "        if rel in SELF_EXCLUDED:\n            continue",
     "        if rel in ():\n            continue"),

    ("4. THE SKIP SWALLOWS EVERYTHING -- no excluded file is cited, which is "
     "exactly what a working exclusion looks like from the excluded file's "
     "side, and no file is cited at all",
     TOOL,
     "        if rel in SELF_EXCLUDED:\n            continue",
     "        if True:\n            continue"),

    ("5. A FILE WHOSE SUBJECT IS THE GRADER IS DROPPED FROM THE LIST -- the "
     "completeness question, which the two string literals cannot answer "
     "about themselves",
     TOOL,
     # ── RE-AIMED 2026-09-22, AND IT WAS STALE BEFORE TODAY ───
     # This anchored on the entry PLUS the tuple's closing paren, which only
     # matches while that entry is LAST. Two entries were appended after it on
     # 2026-09-21 and a third on 2026-09-22, so the anchor had ALREADY gone to
     # ANCHOR-0 -- and nobody could see it, because the importer arm was failing
     # and this probe stops at a red baseline before it checks a single anchor.
     # Fixing the baseline is what surfaced it. That is the real cost of a red
     # control: it hides the state of the controls behind it, not just the
     # mutations it was going to run.
     #
     # Anchored on the entry LINE alone now, so appending to the tuple does not
     # move it. A comment naming the same file cannot collide: comment lines
     # start with '#', not four spaces and a quote.
     "    'tests/cross_tenant_dispatchers_review_probe.py',\n",
     ""),
]

sys.exit(run_probe(
    SUITE, MUTATIONS,
    title="SAIRN: the cross-tenant grader's self-exclusion list must be "
          'present, SPELLED as the scan spells it, actually consulted, not '
          'swallowing everything, and COMPLETE',
    stage=(TOOL,),
))
