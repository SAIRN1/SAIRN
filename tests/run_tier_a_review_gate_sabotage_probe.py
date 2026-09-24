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
     # ANCHOR UPDATED 2026-09-24: 5e8cf3fb widened the partial set to the rule
     # channel, and this arm sat on the OLD spelling reporting ANCHOR-0 -- a
     # probe arm testing nothing while looking armed.
     "    partial = sorted((set(hits) & covered) | (set(rule_hits) & covered_rules))\n    if partial:",
     "    partial = sorted((set(hits) & covered) | (set(rule_hits) & covered_rules))\n    if False:"),

    ("4. THE ONE THAT READS AS CORRECT: the blocking list names every resource "
     "the change touched rather than the uncovered ones, so the heading and "
     "both halves are still right and only the list is wrong",
     GATE,
     "    for name in uncovered:\n        lines.append('  %-22s %s'",
     "    for name in sorted(hits):\n        lines.append('  %-22s %s'"),

    # ── OWNERSHIP, ADDED 2026-09-21 WITH THE STAMP ITSELF ─────────────────
    # Four obligations were double-reviewed in one day. Section 6 of the
    # suite proves the stamp closes that; these prove the arms would NOTICE
    # the stamp coming undone. Every mutation is a plausible tidy-up --
    # a check disabled, a filter dropped, a sort simplified -- rather than
    # nonsense, because a mutation nobody would ever make tests nothing.

    ('5. THE OWNER CHECK IS REMOVED AND THE SELF-REVIEW CHECK IS LEFT -- which is exactly what the file looked like yesterday, so it reads as the original rather than as damage',
     GATE,
     "    owner = rec.get('reviewer_owner')\n    if (owner and reviewer and reviewer != owner",
     "    owner = rec.get('reviewer_owner')\n    if (False and owner and reviewer and reviewer != owner"),

    ('6. THE STAMP STOPS BEING APPLIED AT --open -- every new obligation is born UNOWNED, so the queue silently returns to first-come while every existing owned record still looks right',
     GATE,
     '    owner, owner_note = assign_owner(author, data)',
     "    owner, owner_note = None, 'assignment disabled'"),

    ('7. AN AUTHOR CAN BE ASSIGNED ITS OWN OBLIGATION -- the exclusion in assign_owner goes, so the stamp still happens and still looks like one, and the record becomes unreviewable by the only session holding it',
     GATE,
     '    candidates = [n for n in roster if n != author]',
     '    candidates = list(roster)'),

    ('8. THE ROSTER STOPS FAILING CLOSED -- an unreadable .claude/claims/ returns an empty list instead of None, so assign_owner sees a roster with nobody on it and every record is quietly born unowned',
     GATE,
     '    except OSError:\n        return None',
     '    except OSError:\n        return []'),

    ("9. THE HOVER AUDITOR BECOMES ELIGIBLE -- one filter removed, and the audit role starts receiving the build agents' review queue",
     GATE,
     # ANCHOR MOVED 2026-09-24: the literal `n != HOVER_SESSION` compare was
     # itself the defect (H2 seq #205 -- hover2 was one claim file away from
     # the reviewer pool) and is a role predicate now.
     '    names = [n for n in names if not is_hover_session(n)]',
     '    names = list(names)'),

    ('10. TAKEOVER LOSES ITS TIME GATE -- anybody may take any owned obligation immediately, which is the original race with a flag on it, and it still RECORDS a handover so the record looks MORE honest than it is',
     GATE,
     '        if age <= OWNER_STALE_HOURS:',
     '        if False:'),

    ('11. THE TAKEOVER STOPS NAMING WHO -- the handover still happens and the verdict still lands, so nothing downstream looks wrong; only the evidence that an assignment failed disappears',
     GATE,
     "            'from': owner, 'by': session,",
     "            'from': None, 'by': None,"),

    ('12. ASSIGNMENT STOPS BEING LEAST-LOADED and becomes alphabetical -- it looks like a simplification, keeps every other property (deterministic, never the author) and quietly piles the whole queue on whoever sorts first',
     GATE,
     '    best = min(candidates, key=lambda n: (load[n], n))',
     '    best = min(candidates)'),

    ('13. THE ATOMIC SAVE GOES BACK TO A DIRECT WRITE -- the mode that produced two concatenated JSON documents and failed every push on the platform closed until somebody repaired the file by hand',
     GATE,
     '        os.replace(tmp, REVIEWS)',
     '        pass  # os.replace removed'),
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
