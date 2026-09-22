"""Negative control for tests/seam_remake_derivation.js.

    python tests/run_seam_remake_derivation_sabotage_probe.py

Exit 0  every planted defect was refused by the suite
Exit 1  one was not -- the suite does not bite where it says it does
Exit 3  COULD NOT RUN -- never folded into either of the other two

── WHY THIS CONTROL AND NOT A REVIEW ───────────────────────────────────────
The defect being fixed is a CONSTANT that three tiles read as a measurement,
and the replacement is a derivation. That swap is easy to get right and easy
to have silently reverted -- `x.remake` is shorter than `seamHadRemake(x,rms)`
and reads as equivalent to anyone who has not been told why it is not.

So the mutations are the plausible regressions, not arbitrary damage. Each is
something a later session could write believing it was a simplification:

  1 drop the time-order guard   -- "any remake on this job counts"
  2 drop the name normalisation -- "the names are typed the same anyway"
  3 drop the blank-job guard    -- "an empty job is just another key"
  4 restore the $180 constant   -- the tile looked broken showing '--'
  5 restore the frozen flag     -- the insert "lost a field"

1, 2 and 3 all make the function MORE permissive, which is the direction that
matters: a remake attributed to the wrong analysis is a first-pass approval
figure that is wrong in the flattering direction, which is the direction
nobody checks. 4 and 5 are caught by source-text arms rather than behaviour,
because a call site can go back to reading the constant while every unit
assertion about the derivation still passes -- the same shape that kept the
[0040] trigger behind a dead element for three weeks.

STAGED: stonedesk.html, because the fix under test is not committed yet and
the worktree is at HEAD. Without it the baseline measures the OLD file
against the NEW suite and goes red for a reason that has nothing to do with
any mutation.
"""
# REQUIREMENT: the Seam AI remake derivation is proven to bite in the
#   permissive direction, because a remake attributed to the wrong analysis
#   flatters the first-pass approval tile and nobody checks a good number
#
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sabotage_harness import run_probe                          # noqa: E402

SUITE = os.path.join('tests', 'seam_remake_derivation.js')
APP = 'stonedesk.html'

MUTATIONS = [
    # 1. "A remake on this job is a remake on this job." It is not: the
    #    analysis is supposed to PREVENT the remake, so one logged beforehand
    #    says nothing about it.
    ('the time-order guard is dropped', APP,
     "      if(!on||!made||made>=on) return true;\n",
     "      return true;\n"),

    # 2. Both names are free text typed by different people on different days.
    #    Exact equality under-counts, and an under-count here raises the
    #    first-pass approval figure.
    ('job names stop being normalised', APP,
     r"  function seamKey(s){return String(s||'').trim().toLowerCase().replace(/\s+/g,' ');}" + "\n",
     "  function seamKey(s){return String(s||'');}\n"),

    # 3. Without this, seamKey('') === seamKey(undefined) and every blank-job
    #    analysis matches every blank-customer remake.
    ('the blank-job guard is dropped', APP,
     "    if(!job) return false;\n",
     "\n"),

    # 4. The tile showing '--' looks broken to someone who does not know the
    #    number behind it was invented. This is the revert that looks like a
    #    fix.
    ('the $180-per-analysis savings constant comes back', APP,
     "    document.getElementById('seam-savings').textContent='--';\n",
     "    document.getElementById('seam-savings').textContent='$'+(d.length*180).toLocaleString();\n"),

    # 5. The frozen field returns at an insert site. Every behavioural
    #    assertion above still passes -- only a source-text arm can see this.
    ('the frozen remake:false flag is written again', APP,
     "      d.push({job:job,mat:mat,loc:loc,date:sdLocalToday()});\n",
     "      d.push({job:job,mat:mat,loc:loc,date:sdLocalToday(),remake:false});\n"),
]

if __name__ == '__main__':
    sys.exit(run_probe(
        SUITE, MUTATIONS, stage=(APP,),
        title='negative control: the Seam AI remake figures must be derived, '
              'and must not drift back to a constant'))
