"""Is the hover auditor's independent-validation checkpoint overdue, asked from
OUTSIDE the hover clone -- because a check only that role can see cannot
escalate to anybody.

    python tools/hover_eqa_escalation.py
    python tools/hover_eqa_escalation.py --json

Exit 0 every checkpoint is current, 1 at least one is overdue, 2 COULD NOT TELL.

── WHY THIS EXISTS, AND IT IS THE ONE PLATFORM-SCOPE ITEM OF FIVE ────────────
hover1's full self-assessment (its own log, entry 408) named five gaps in its
own tooling and proposed five fixes. FOUR of them are changes to files that live
inside `~/.claude/projects/<hover clone>/hover-audit-log/` -- the SHA_TOKEN
width in hover_coverage_ledger.py, the missing third register in
hover_duplicate_finding_check.py, SLSA-style grading of the coverage ledger, and
the cited-vs-checked WARM distinction. Those are the auditor's own territory and
a build agent editing them is the separation problem running the other way
(CLAUDE.md; docs/2026-09-15-hover-auditor-separation-enforcement.md). They are
left for hover to build, exactly as proposal #6 was decided.

THE FIFTH IS DIFFERENT IN KIND AND THAT IS WHY IT IS HERE. Gap 5 is *nobody
independently checks hover's own findings*, and its concrete instance was
hover's EQA checkpoint reporting overdue for sixteen process passes against a
cadence of three -- with the tool that says so running ONLY inside the hover
clone. `tools/hover_self_health_shim.py` is deliberately a silent no-op in a
build clone, which is right for a self-check and wrong for an escalation: the
one party who must not be the sole reader of "hover has not been independently
validated" is hover.

A ROLE CANNOT SATISFY ITS OWN INDEPENDENCE CHECKPOINT BY DEFINITION, so the
report has to reach somewhere else. This is that somewhere else.

── WHAT IT DOES NOT DO ──────────────────────────────────────────────────────
IT DOES NOT RUN hover's grader. It reads the LOG -- a data file -- and computes
the answer from the rule independently. Two reasons, and the second is the one
that matters: executing another role's code from a build clone blurs the
boundary this whole mechanism exists to keep, and a second implementation that
can DISAGREE is worth more than a second copy that cannot. If this and hover's
own number ever differ, that disagreement is itself the finding.

IT WRITES NOTHING, anywhere. Not into the hover clones, not into the log, not a
state file. Read-only by construction.

── THE THIRD STATE IS THE WHOLE POINT HERE ──────────────────────────────────
No hover clone found, an unreadable log, or a log with no checkpoint field at
all are COULD NOT TELL and exit 2. An escalation that reports "current" because
it could not find the thing it was escalating is the failure it exists to
prevent.
"""
import argparse
import io
import json
import os
import sys

EXIT_CLEAN, EXIT_OVERDUE, EXIT_COULD_NOT_RUN = 0, 1, 2

# The cadence hover's own tooling states: an independent validation is due every
# N process passes. Kept here as a NUMBER WITH ITS SOURCE NAMED rather than read
# out of hover's code, because reading their constant would make this a copy of
# their answer instead of a second opinion -- and if they change it, the two
# disagreeing is information rather than a bug.
EQA_CADENCE = 3
CADENCE_SOURCE = ("hover_self_health.py's own `eqa_cadence` field, read once on "
                  "2026-09-22 and hard-coded here on purpose -- see the module "
                  "docstring")


def hover_logs():
    """Every hover self-log on this machine: [(session, path)]."""
    base = os.path.join(os.path.expanduser('~'), '.claude', 'projects')
    if not os.path.isdir(base):
        return []
    out = []
    for name in sorted(os.listdir(base)):
        p = os.path.join(base, name, 'hover-audit-log', 'hover-audit-log.jsonl')
        if os.path.isfile(p):
            out.append((name.rsplit('-', 1)[-1] or name, p))
    return out


def assess(path):
    """(verdict, detail) for one log, computed from the entries.

    verdict is 'current', 'overdue' or 'unknown'.
    """
    try:
        rows = [json.loads(l) for l in io.open(path, encoding='utf-8') if l.strip()]
    except (OSError, ValueError) as e:
        return 'unknown', 'the log could not be read or parsed: %s' % e
    if not rows:
        return 'unknown', 'the log is empty'
    if not any('eqa_checkpoint' in r for r in rows):
        # NOT "current". A log with no checkpoint field is one this tool cannot
        # speak about, and saying so is the difference between an escalation and
        # a rubber stamp.
        return 'unknown', ('no entry carries an `eqa_checkpoint` field, so this '
                           'tool cannot tell whether a checkpoint has ever '
                           'happened')
    last_cp = None
    for r in rows:
        if r.get('eqa_checkpoint'):
            last_cp = r.get('seq')
    if last_cp is None:
        return 'overdue', ('the field exists on %d entries and NO entry has ever '
                           'set it true -- an independent validation has never '
                           'been recorded' % len(rows))
    since = sum(1 for r in rows
                if r.get('process_pass') and (r.get('seq') or 0) > last_cp)
    if since >= EQA_CADENCE:
        return 'overdue', ('%d process pass(es) since the checkpoint at entry %s, '
                           'against a cadence of %d'
                           % (since, last_cp, EQA_CADENCE))
    return 'current', ('%d process pass(es) since the checkpoint at entry %s, '
                       'cadence %d' % (since, last_cp, EQA_CADENCE))


def main(argv=None):
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument('--json', action='store_true')
    args = ap.parse_args(argv)

    logs = hover_logs()
    results = [{'session': s, 'path': p, 'verdict': v, 'detail': d}
               for s, p in logs for v, d in [assess(p)]]

    if args.json:
        print(json.dumps({'cadence': EQA_CADENCE, 'cadence_source': CADENCE_SOURCE,
                          'results': results}, indent=1))
    else:
        print("HOVER INDEPENDENT-VALIDATION CHECKPOINT -- asked from OUTSIDE the "
              "auditor's clone")
        print('=' * 72)
        print('')
        if not logs:
            print('  COULD NOT TELL: no hover self-log found under')
            print('  ~/.claude/projects/*/hover-audit-log/.')
            print('')
            print('  That is NOT "no hover instance needs validating". It is this')
            print('  tool being unable to look, and it is reported as such.')
        for r in results:
            mark = {'current': 'ok        ', 'overdue': 'OVERDUE   ',
                    'unknown': 'COULD NOT '}[r['verdict']]
            print('  %s %-34s %s' % (mark, r['session'], r['detail']))
        print('')
        print('  Cadence %d, from %s.' % (EQA_CADENCE, CADENCE_SOURCE))
        print('  This tool READS the log and computes the answer itself; it does')
        print('  not run the auditor\'s own grader. If its number and hover\'s')
        print('  ever disagree, THAT is the finding -- a second implementation is')
        print('  worth more than a second copy.')
        print('')
        print('  It writes nothing, anywhere.')

    if not results:
        return EXIT_COULD_NOT_RUN
    if any(r['verdict'] == 'overdue' for r in results):
        return EXIT_OVERDUE
    if any(r['verdict'] == 'unknown' for r in results):
        return EXIT_COULD_NOT_RUN
    return EXIT_CLEAN


if __name__ == '__main__':
    sys.exit(main())
