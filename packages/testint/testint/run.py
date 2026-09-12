r"""Run every testint check and report in one voice.

    python -m testint.run --config testint.config.json
    python -m testint.run --config testint.config.json --only comment_quote
    python -m testint.run --self-test

Exit codes, and the distinctions are the whole point:

    0   every check ran and found nothing
    1   at least one check found something
    2   at least one check COULD NOT READ part of its subject
    3   at least one check COULD NOT RUN at all

**2 and 3 are never folded into 0.** "We could not check it" and "it is fine"
are the two answers this suite exists to keep apart, and a runner that collapses
them undoes every check underneath it.

── WHY A RUNNER AT ALL ───────────────────────────────────────────────────────
Three scripts in a directory is not a mechanism. In the codebase this package
came from, an inventory of the tooling found **43 of 99 tools invoked by nothing
at all** -- every one of them written in response to a real incident, committed,
and never pointed at the codebase again. A tool that exists is not a mechanism;
a tool that runs is. This is the smallest thing that makes the other three run.

── WHAT IT DELIBERATELY DOES NOT DO ──────────────────────────────────────────
It does not aggregate findings into a score. A count across three different
questions is a number nobody can act on, and the moment a number exists somebody
drives it to zero by the cheapest available route -- which for a checker is
switching it off. Each check reports its own finding in its own words; this
prints them in order and returns the worst exit code.
"""
import sys

from . import check_comment_quote, check_determinism, check_mutation_anchor

CHECKS = [
    ('comment_quote',
     'does an assertion match the target COMMENTS instead of its code',
     check_comment_quote.main),
    ('mutation_anchor',
     'does every mutation control still match its target exactly once',
     check_mutation_anchor.main),
    ('determinism',
     'does each checker give the same answer twice on the same input',
     check_determinism.main),
]


def main(argv):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:                                    # noqa: BLE001
        pass

    if '--self-test' in argv:
        # Only the determinism check has a self-test: it is the only one whose
        # CLEAN result is otherwise indistinguishable from a broken sweep. The
        # other two report what they could not read, which is the same property
        # arrived at a different way.
        return check_determinism.main(['--self-test'])

    only = None
    if '--only' in argv:
        only = argv[argv.index('--only') + 1]
    passthrough = [a for a in argv if a not in ('--only', only)]

    worst = 0
    ran, results = 0, []
    for name, question, fn in CHECKS:
        if only and name != only:
            continue
        print('=' * 72)
        print('%s -- %s' % (name.upper().replace('_', ' '), question))
        print('=' * 72)
        rc = fn(list(passthrough))
        results.append((name, rc))
        ran += 1
        # 3 (could not run) is the loudest, then 2 (could not read), then 1.
        worst = max(worst, rc) if rc != 3 else 3
        if 3 in (rc, worst):
            worst = 3
        print('')

    if not ran:
        print('NOTHING RAN. --only %r matched no check. Known: %s'
              % (only, ', '.join(n for n, _, _ in CHECKS)))
        return 3

    print('=' * 72)
    print('SUMMARY')
    for name, rc in results:
        word = {0: 'clean', 1: 'FINDINGS', 2: 'COULD NOT READ part of its subject',
                3: 'COULD NOT RUN'}.get(rc, 'exit %d' % rc)
        print('  %-18s %s' % (name, word))
    print('')
    if worst == 0:
        print('All %d check(s) ran and found nothing.' % ran)
        print('A clean determinism result only means something if the method can '
              'see the defect:')
        print('    python -m testint.run --self-test')
    elif worst == 3:
        print('At least one check COULD NOT RUN. That is not a pass -- read the '
              'reason above.')
    elif worst == 2:
        print('At least one check could not read part of its subject. The part it '
              'could not read')
        print('is not covered, and a clean line above does not cover it.')
    else:
        print('Findings above. Each is a place where something that looks like a '
              'check may not be one.')
    return worst


def cli():
    """Console entry point: `testint` after a pip install.

    A separate function because `pyproject.toml`'s [project.scripts] needs a
    callable taking no arguments, and `main()` takes argv so the tests can drive
    it without touching sys.argv.
    """
    sys.exit(main(sys.argv[1:]))


if __name__ == '__main__':
    cli()
