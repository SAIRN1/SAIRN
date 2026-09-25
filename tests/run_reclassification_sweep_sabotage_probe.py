"""Negative control for tests/run_reclassification_sweep_probe.py.

    python tests/run_reclassification_sweep_sabotage_probe.py

Exit 0  every planted defect was refused by the suite
Exit 1  one was not -- the suite does not bite where it says it does
Exit 3  COULD NOT RUN -- never folded into either of the other two

── FIVE FAIL-OPENS FED ONE ZERO, AND EACH ONE IS PLANTED BACK ──────────────
tools/reclassification_sweep.py printed
`TALLY: {'DEEM': 0, 'ROLE': 0, 'PERMIT': 0}` from every directory it was ever
run in, having read either the wrong files or none. Five separate silences
produced that one sentence, and the fix removed all five in one pass -- which
is exactly the situation where a control matters, because four-of-five leaves
the same sentence on screen and nothing says which one came back.

So each mutation restores ONE of them:

  1 the corpus stops being anchored   -- the answer depends on the cwd again
  2 zero files stops being a refusal  -- a tally over nothing
  3 an unreadable document returns '' -- swept as containing no match
  4 the missing-pypdf case goes quiet -- the library, not the document
  5 a whitespace capture is no-match  -- a failed extraction reads as clean

NOT ONE OF THEM MAKES THE TOOL FAIL. Every single one makes it answer
confidently about statutes it did not read, which is the only failure mode
that matters for a tool whose output is evidence behind a compliance
position.

ANCHORS CARRY NO LINE ENDINGS. This clone's working tree is CRLF -- the
.gitattributes rule is not retroactive and `git status` stays clean
throughout -- so an anchor ending in `\\n` matches nothing here and would make
every arm report ANCHOR-0 rather than a finding. Substring anchors with no
newline match either spelling.

STAGED: the tool and its suite, neither of which is committed when this first
runs.
"""
# REQUIREMENT: the reclassification sweep keeps reading its real corpus and
#   keeps refusing every document it cannot read, because a zero in every
#   bucket reads as "no state deems these workers employees"
#
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sabotage_harness import run_probe                          # noqa: E402

SUITE = os.path.join('tests', 'run_reclassification_sweep_probe.py')
TOOL = os.path.join('tools', 'reclassification_sweep.py')

MUTATIONS = [
    # 1. THE ORIGINAL DEFECT, restored in one line. The walk still happens --
    #    it just starts from wherever the caller stood, which is how a tool
    #    ends up sweeping 22 app HTML files and calling it a statute corpus.
    ('the corpus stops being anchored to the repository', TOOL,
     "root = sys.argv[1] if len(sys.argv) > 1 else CORPUS",
     "root = sys.argv[1] if len(sys.argv) > 1 else '.'"),

    # 2. The sentence itself. Nothing else changes; the tool simply prints a
    #    tally after reading nothing, which is indistinguishable from a real
    #    sweep that found nothing.
    ('zero files stops being a refusal', TOOL,
     "if not files:",
     "if False:"),

    # 3. THE SHAPE THIS FILE IS NAMED FOR. A document that cannot be read
    #    becomes a document with no match -- and the exit code stays 0.
    # ── REWRITTEN 2026-09-25: THE ORIGINAL MUTANT DID NOT PARSE ────────────
    # It replaced the `raise` line only and left its continuation line -- the
    # `% (path, type(e).__name__, e))` -- dangling at the old indent, so the
    # tool died on `unexpected indent` and the suite went red about SYNTAX,
    # not about an unreadable .docx reading as empty. Scored CAUGHT until the
    # harness's 2026-09-25 parse check. The rewrite replaces the whole raise
    # statement, which is the defect as somebody would actually write it.
    ('an unreadable .docx goes back to reading as empty', TOOL,
     "            raise Unreadable('%s could not be read as a .docx (%s: %s)'\n"
     "                             % (path, type(e).__name__, e))",
     "            return ''  # SABOTAGE: unreadable reads as empty"),

    # 4. The library, not the document. Absent pypdf means EVERY PDF in the
    #    corpus is swept as clean, which is the widest of the five.
    ('a missing pypdf stops being reported', TOOL,
     "        except ImportError:",
     "        except ImportError:\n            return ''  # SABOTAGE\n        except SystemExit:"),

    # 5. A capture that extracted to whitespace -- a failed PDF-to-text, a
    #    truncated download that still cleared the size floor -- read as a
    #    statute containing none of the phrases.
    ('a whitespace-only capture goes back to counting as no-match', TOOL,
     "    if not t.strip():",
     "    if False:"),
]

if __name__ == '__main__':
    sys.exit(run_probe(
        SUITE, MUTATIONS, stage=(TOOL, SUITE),
        title='negative control: the reclassification sweep must keep refusing '
              'what it did not read'))
