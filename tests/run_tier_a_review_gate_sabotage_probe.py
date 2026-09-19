"""tests/run_tier_a_review_gate_probe.py must REFUSE, not merely agree.

Run: python tests/run_tier_a_review_gate_sabotage_probe.py

# REQUIREMENT: the probe guarding check 13 must go RED when the gate's coverage
#   test widens back to an INTERSECTION, when the union of open obligations
#   reaches across sessions, or when a partially-recorded change stops saying
#   so -- because check 13 is the only thing standing between a Tier A change
#   and nobody knowing it went unreviewed, and a probe that cannot notice it
#   going soft is indistinguishable from one that always agrees

THE GATE HAD NO NEGATIVE CONTROL, which is why hover #270 survived in it.
`python tools/sabotage_control_check.py` lists no probe sabotaging
tools/tier_a_review_gate.py. Its probe is 102 arms and green, and green said
nothing about whether it would notice the coverage test widening -- which is
exactly what had happened: `set(hits) & set(record.resources)` cleared a whole
change on one resource in common, and every arm in that probe drove a
single-resource diff, so the difference between an intersection and a subset
was invisible to it.

── WHY THE WORKTREE SHAPE WORKS HERE ──────────────────────────────────────
run_tier_a_review_gate_probe.py resolves REPO from its own __file__ and does
`sys.path.insert(0, REPO/tools)`, so a copy of the probe running inside the
sabotage harness's throwaway worktree imports THAT worktree's gate. Nothing in
this clone is written; the harness asserts byte-identity and asks git.

── WHAT IS PLANTED ────────────────────────────────────────────────────────
  * the coverage test goes back to an INTERSECTION -- hover #270 itself,
    restored exactly, so one open obligation clears a change touching it and
    anything else;
  * the union of open obligations stops being scoped to THIS session, so
    another session's obligation fills my gap -- a gate satisfied by work
    nobody in this clone is accountable for;
  * a partially-recorded change stops SAYING it is partial, so the message
    reads as a change with nothing recorded and the session is told to
    re-record what is already on file;
  * the blocking list reports every resource the change touched instead of the
    uncovered ones, which reads as correct and sends the session to record
    obligations it already holds.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sabotage_harness import run_probe                           # noqa: E402

SUITE = os.path.join('tests', 'run_tier_a_review_gate_probe.py')
GATE = os.path.join('tools', 'tier_a_review_gate.py')

MUTATIONS = [
    ("1. HOVER #270 ITSELF, RESTORED -- the coverage test is an INTERSECTION "
     "again, so one open obligation clears a change touching it and anything "
     "else alongside it",
     GATE,
     "    uncovered = sorted(set(hits) - covered)",
     "    uncovered = [] if (set(hits) & covered) else sorted(set(hits) - covered)"),

    ("2. the union stops being scoped to THIS SESSION -- another session's "
     "open obligation fills my gap, and the gate is satisfied by work nobody "
     "in this clone is accountable for",
     GATE,
     "    mine = open_records(data, session)",
     "    mine = open_records(data)"),

    ("3. a PARTIALLY recorded change stops saying it is partial -- the message "
     "reads as a change with nothing on file and sends the session to "
     "re-record obligations it already holds",
     GATE,
     "    partial = sorted(set(hits) & covered)\n    if partial:",
     "    partial = sorted(set(hits) & covered)\n    if False:"),

    ("4. THE ONE THAT READS AS CORRECT: the blocking list names every resource "
     "the change touched rather than the uncovered ones, so the heading and "
     "both halves are still right and only the list is wrong",
     GATE,
     "    for name in uncovered:\n        lines.append('  %-22s %s'",
     "    for name in sorted(hits):\n        lines.append('  %-22s %s'"),
]

if __name__ == '__main__':
    sys.exit(run_probe(
        SUITE, MUTATIONS,
        title='check 13 coverage -- the probe must refuse a gate whose '
              'coverage test has widened back to an intersection',
        # BOTH the suite and the GATE are staged. The worktree is at HEAD,
        # so without the gate the probe would run its new #270 arms against
        # the OLD gate and the baseline would go red for a reason that has
        # nothing to do with any mutation -- which is what happened on the
        # first run here, and is the case the harness's own `stage` note
        # describes.
        stage=(SUITE, GATE),
        carry_identity=True))
