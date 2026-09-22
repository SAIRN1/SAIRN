"""Negative control for tests/run_body_file_roundtrip_probe.py's WIRING arms.

    python tests/run_body_file_wiring_sabotage_probe.py

Exit 0  every planted defect was refused by the suite
Exit 1  one was not -- the suite does not bite where it says it does
Exit 3  COULD NOT RUN -- never folded into either of the other two

── WHY THIS EXISTS, AND IT IS NOT "the roundtrip probe needed a control" ────
The roundtrip probe was CORRECT on 2026-09-22 and still could not see the
defect that matters. Every arm it carried tested `body_from_file_or` in
isolation, so it proved the helper decodes, strips and refuses exactly right
-- and proved nothing at all about whether `--open` or `--discharge` ever
CALLS it. MEASURED before the arms were written, not argued: with the single
line `why = body_from_file_or(argv, why)` deleted from main()'s --open branch,
the roundtrip probe exited 0 with ZERO failures, while
`--open --body-file <path>` recorded the literal string `--body-file` as the
whole "what changed and why" -- eleven characters, non-empty, so the gate
reported success and opened an obligation containing nothing.

That is the same shape the defect register already carries for
`_discharge()`'s docstring at `85464d4088f3`: a control that is right about
the thing it looks at, beside a caller that does not use it. A correct helper
nothing calls is indistinguishable from a correct helper everything calls,
from inside a unit test.

SO THE FOUR MUTATIONS ARE ABOUT THE SEAM, not about the helper. Each removes
one JOIN between main() and body_from_file_or and leaves the helper perfect:

  1 --open stops calling it       -> the flag name is stored as the record
  2 --discharge stops calling it  -> the file is read and then ignored
  3 the flag stops being stripped -> '--body-file' and a temp path are joined
                                     into the verdict prose as ordinary words
  4 a missing file returns ''     -> the refusal stops being COULD NOT TELL,
                                     which is 1.11 exactly: could-not-run
                                     folded into a quieter answer

Mutation 4 is the one worth reading twice. It does not break the round trip
and it does not break the wiring; it changes a REFUSAL into an empty string,
and an empty string is what the gate would store as a completed review.
"""
# REQUIREMENT: --body-file is proven WIRED INTO main(), not merely implemented,
#   because a helper that decodes perfectly and is never called stores the name
#   of the flag as the review body and reports success
#
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sabotage_harness import run_probe                          # noqa: E402

SUITE = os.path.join('tests', 'run_body_file_roundtrip_probe.py')
TOOL = os.path.join('tools', 'tier_a_review_gate.py')

MUTATIONS = [
    # 1. THE ONE THAT WAS MEASURED. Nothing else changes: the helper is intact,
    #    the flag is still accepted, and `why` falls back to argv[i + 1] --
    #    which, when --body-file is the next word, IS the string '--body-file'.
    ('--open stops calling body_from_file_or', TOOL,
     "            why = body_from_file_or(argv, why)\n",
     "            pass  # SABOTAGE: --open no longer reads --body-file\n"),

    # 2. THE MIRROR ON THE OTHER COMMAND. `file_body = None` sends --discharge
    #    down the positional branch, so a verdict written to a file is silently
    #    replaced by whatever words happened to follow the author on the line.
    ('--discharge stops calling body_from_file_or', TOOL,
     "            file_body = body_from_file_or(argv, None)\n",
     "            file_body = None  # SABOTAGE: --discharge ignores the file\n"),

    # 3. THE FLAG IS READ AND THEN LEFT IN argv. --discharge joins its trailing
    #    words into the verdict, so the review would be stored carrying the
    #    flag and an absolute temp path nobody else on the platform can open.
    ('--discharge stops stripping the flag out of the prose', TOOL,
     "        if '--body-file' in argv:\n"
     "            k = argv.index('--body-file')\n"
     "            argv = argv[:k] + argv[k + 2:]\n",
     "        pass  # SABOTAGE: the flag and its path stay in the verdict\n"),

    # 4. COULD-NOT-TELL BECOMES "". The body is absent either way; the
    #    difference is whether the tool says so or records a blank review and
    #    exits as though it had one. PR 1.11, at the smallest possible scale.
    ('an absent body stops being COULD NOT TELL', TOOL,
     "        raise CouldNotTell('--body-file %r does not exist. Nothing was '\n"
     "                           'recorded -- an absent body is not an empty one.'\n"
     "                           % path)\n",
     "        return ''  # SABOTAGE: an absent body becomes an empty review\n"),
]

if __name__ == '__main__':
    sys.exit(run_probe(
        SUITE, MUTATIONS,
        title='negative control: the roundtrip probe must refuse a --body-file '
              'that is implemented and not WIRED IN'))
