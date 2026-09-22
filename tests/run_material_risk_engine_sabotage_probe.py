"""Negative control for tests/material_risk_engine.js.

    python tests/run_material_risk_engine_sabotage_probe.py

Exit 0  every planted defect was refused by the suite
Exit 1  one was not -- the suite does not bite where it says it does
Exit 3  COULD NOT RUN -- never folded into either of the other two

── THE MUTATIONS ARE THE SIMPLIFICATIONS, not arbitrary damage ──────────────
[0072] is an engine whose whole value is the things it REFUSES to say. Every
guard in it looks removable to someone reading it cold, and removing any one
of them leaves a function that still returns plausible percentages:

  1 the two-remake floor    -- "why wouldn't one remake count?"
  2 the four-job floor      -- "we're throwing away data"
  3 name normalisation      -- "just match the first few characters"
  4 the unmatched report    -- "it's an empty list most of the time"
  5 the no-material skip    -- "a customer is a job either way"
  6 the health-score wiring -- the engine keeps working and nothing reads it

1, 2, 3 and 5 all make the engine MORE WILLING TO ANSWER, which is the
direction that matters: every one of them produces a confident number off
evidence that does not support it, and a shop acts on a red flag. 4 makes it
quieter -- a material whose remakes match no job disappears, and a silent zero
reads exactly like a clean shop. 6 is [0040] in miniature and only a
source-text arm can see it.

STAGED: stonedesk.html, because the engine is not committed yet and the
worktree is at HEAD.
"""
# REQUIREMENT: [0072]'s refusals are proven to bite -- the evidence floors, the
#   name matching, the unmatched report and the call-site wiring -- because
#   every one of them looks like a removable simplification from inside
#
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sabotage_harness import run_probe                          # noqa: E402

SUITE = os.path.join('tests', 'material_risk_engine.js')
APP = 'stonedesk.html'

MUTATIONS = [
    # 1. One remake against four jobs is a 25% rate. Without this floor it
    #    outranks a material with six remakes against sixty.
    ('the two-remake floor is removed', APP,
     "    if (remakes >= SD_MATRISK_MIN_REMAKES) {\n",
     "    if (true) {\n"),

    # 2. The job floor is the difference between a rate and an anecdote, and
    #    it is the same 4 computePricingInsight() already chose.
    ('the four-job floor is removed', APP,
     "    if (jobs < SD_MATRISK_MIN_JOBS) {\n",
     "    if (false) {\n"),

    # 3. THE ONE A REASONABLE PERSON WOULD WRITE. Prefix matching looks like
    #    tolerance for typos and silently merges Quartz into Quartzite --
    #    the single distinction a fabricator most needs kept apart.
    ('material names are matched on a prefix', APP,
     r"function sdMatKey(s) { return String(s || '').trim().toLowerCase().replace(/\s+/g, ' '); }" + "\n",
     r"function sdMatKey(s) { return String(s || '').trim().toLowerCase().replace(/\s+/g, ' ').slice(0, 6); }" + "\n"),

    # 4. The quiet one. Remakes against a material no job carries vanish, and
    #    what is left reads as a shop with nothing wrong.
    ('the unmatched-material report is emptied', APP,
     "  var unmatched = Object.keys(rmBy).filter(function (k) { return !jobsBy[k]; }).map(function (k) {\n",
     "  var unmatched = [].filter(function (k) { return !jobsBy[k]; }).map(function (k) {\n"),

    # 5. A customer with no material recorded becomes a denominator entry under
    #    the empty-string key, diluting every rate and flattering the baseline.
    ('customers with no material enter the denominator', APP,
     "    var k = sdMatKey(c && c.material);\n    if (!k) return;\n",
     "    var k = sdMatKey(c && c.material);\n"),

    # 6. The engine keeps working perfectly and the score stops reading it.
    ('the health score stops reading the verdict', APP,
     "  if(matRisk&&matRisk.level==='red')score-=20;\n",
     "  if(false)score-=20;\n"),
]

if __name__ == '__main__':
    sys.exit(run_probe(
        SUITE, MUTATIONS, stage=(APP,),
        title='negative control: [0072] must keep refusing to answer where the '
              'evidence does not support one'))
