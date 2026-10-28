#!/usr/bin/env python
"""The control for tools/sairn_dead_function_sweep.py -- BOTH directions.

    python tests/run_sairn_dead_function_sweep_probe.py

Exit 0 all arms pass, 1 any arm fails.

The arm this exists for is M20 (2026-10-28): a file whose comment stripping
blanked past the 25% size guard printed a WARNING, then printed `clean`, went
into TOTAL_*, and the run exited 0. Planted here as a fixture whose comment
mass is over the guard; it must come back UNTRUSTED, out of the totals, exit 2.
The control is a clean fixture with one dead function: exit 0 and that
function named, so the arm above is not satisfied by a tool that refuses all.
"""
import os
import subprocess
import sys
import tempfile

CONTROLS_FOR = ['tools/sairn_dead_function_sweep.py']

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(REPO, 'tools', 'sairn_dead_function_sweep.py')

bad = 0


def arm(label, cond, detail=''):
    global bad
    print(('  ok   ' if cond else '  FAIL ') + label
          + ('' if cond else '\n         %s' % str(detail)[-400:]))
    if not cond:
        bad += 1


def run(*paths):
    p = subprocess.run([sys.executable, TOOL] + list(paths), cwd=REPO,
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace')
    return p.returncode, p.stdout + p.stderr


def main():
    print('SAIRN DEAD FUNCTION SWEEP -- probe')
    d = tempfile.mkdtemp(prefix='dfs-probe-')
    runaway = os.path.join(d, 'runaway.html')
    clean = os.path.join(d, 'clean.html')
    # Over half the file is one block comment: past the guard by construction.
    with open(runaway, 'w', encoding='utf-8') as fh:
        fh.write('<script>\n/* %s */\nfunction used(){}\nused();\n'
                 'function deadOne(){}\n</script>\n' % ('x' * 2000))
    with open(clean, 'w', encoding='utf-8') as fh:
        fh.write('<script>\nfunction used(){}\nused();\n'
                 'function deadOne(){}\n</script>\n')
    try:
        rc, out = run(runaway)
        arm('a file blanked past the 25% guard exits 2 COULD NOT RUN, not 0',
            rc == 2, (rc, out))
        arm('...is printed UNTRUSTED rather than `clean`',
            'UNTRUSTED' in out and 'clean   ' not in out, out)
        arm('...and is left OUT of the totals (TOTAL_FUNCTIONS:0, not 2)',
            'TOTAL_FUNCTIONS:0' in out, out)

        rc, out = run(clean, runaway)
        arm('mixed with a clean file: still exit 2, and the clean file\'s '
            'counts are the only ones totalled',
            rc == 2 and 'TOTAL_FUNCTIONS:2' in out and 'TOTAL_DEAD:1' in out,
            (rc, out))

        rc, out = run(clean)
        arm('NEGATIVE / CONTROL: a clean file exits 0 and names its one dead '
            'function, so the arms above are not a tool that refuses everything',
            rc == 0 and 'deadOne' in out and 'TOTAL_DEAD:1' in out
            and 'UNTRUSTED' not in out, (rc, out))
    finally:
        for f in (runaway, clean):
            if os.path.exists(f):
                os.unlink(f)
        os.rmdir(d)
    print('  %s' % ('ALL ARMS PASS' if not bad else '%d ARM(S) FAILED' % bad))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
