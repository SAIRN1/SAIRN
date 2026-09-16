"""Control on tests/law_reconcile_role_vocab_check.py.

    python tests/law_reconcile_role_vocab_control.py

The checker's whole value is that it FINDS the 2026-09-16 defect. A checker that
exits 0 on the real tree proves nothing about that -- the tree is clean, so exit
0 is also what a checker that reads the wrong file, matches the wrong anchor, or
parses to an empty list would print. This runs it against SYNTHETIC copies of
the tree where the answer is known in both directions, and against the exact
pre-fix text.

The criteria are locked here BEFORE the real run, which is the standing
convention (docs/2026-09-13-cross-domain-disciplines.md): a check whose
threshold is chosen after seeing the data is a description of the data.
"""
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
CHECK = os.path.join(HERE, 'law_reconcile_role_vocab_check.py')

FAILURES = []


def arm(name, ok, detail=''):
    print(('  ok   ' if ok else '  FAIL ') + name)
    if not ok:
        print('         ' + str(detail))
        FAILURES.append(name)
    return ok


def fixture(gate_literal=None, roles_line=None):
    """A throwaway tree holding only the two files the checker reads."""
    tmp = tempfile.mkdtemp(prefix='lrrv_')
    for rel in ('api/sd-data.js', 'api/_lib/auth.js'):
        src = io.open(os.path.join(REPO, rel), encoding='utf-8').read()
        if rel == 'api/sd-data.js' and gate_literal is not None:
            src, n = re.subn(r'const\s+LAW_RECONCILE_ROLES\s*=\s*\{[^}]*\}\s*;',
                             gate_literal, src, count=1)
            assert n == 1, 'fixture did not rewrite the allow-list'
        if rel == 'api/_lib/auth.js' and roles_line is not None:
            src, n = re.subn(r"^\s*sairnlaw:\s*\[[^\]]*\],", roles_line, src,
                             count=1, flags=re.M)
            assert n == 1, 'fixture did not rewrite the vocabulary'
        d = os.path.join(tmp, os.path.dirname(rel))
        if not os.path.isdir(d):
            os.makedirs(d)
        io.open(os.path.join(tmp, rel), 'w', encoding='utf-8',
                newline='').write(src)
    # Under tests/, because the checker resolves REPO as its own parent's parent.
    os.makedirs(os.path.join(tmp, 'tests'))
    shutil.copy(CHECK, os.path.join(tmp, 'tests', 'check.py'))
    return tmp


def run(tmp):
    r = subprocess.run([sys.executable, os.path.join(tmp, 'tests', 'check.py')],
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace')
    return r.returncode, (r.stdout or '') + (r.stderr or '')


def main():
    temps = []
    try:
        print('CRITERIA LOCKED BEFORE THE REAL RUN')

        # 1. THE DEFECT ITSELF, byte-for-byte as it shipped.
        t = fixture('const LAW_RECONCILE_ROLES = { owner: true, admin: true };')
        temps.append(t)
        code, out = run(t)
        arm('the 2026-09-16 literal `{ owner, admin }` is FOUND, exit 1',
            code == 1, 'exit %d\n%s' % (code, out[-400:]))
        arm('...and the output names `admin`', 'admin' in out, out[-300:])

        # 2. THE CLEAN TREE. Must be a different answer from 1, or the checker
        #    is not reading anything.
        t = fixture()
        temps.append(t)
        code, out = run(t)
        arm('the tree as fixed passes, exit 0', code == 0,
            'exit %d\n%s' % (code, out[-400:]))

        # 3. A key that is real in ANOTHER app but not this one -- the actual
        #    mechanism of the defect, not just the one string that caused it.
        t = fixture('const LAW_RECONCILE_ROLES = { owner: true, biller: true };')
        temps.append(t)
        code, out = run(t)
        arm('a role real in SAIRNcode but not SAIRNlaw is FOUND, exit 1',
            code == 1 and 'biller' in out, 'exit %d\n%s' % (code, out[-400:]))

        # 4. The same key, once the app really does have it. The checker must
        #    be reading the VOCABULARY and not a list of blessed words.
        t = fixture('const LAW_RECONCILE_ROLES = { owner: true, biller: true };',
                    "  sairnlaw: ['owner', 'attorney', 'paralegal', 'biller'],")
        temps.append(t)
        code, out = run(t)
        arm('...and passes once ROLES_BY_APP.sairnlaw actually lists it',
            code == 0, 'exit %d\n%s' % (code, out[-400:]))

        # 5. ANCHOR GONE. The failure mode that makes every other arm a lie: a
        #    check that matches nothing reports a clean result.
        t = fixture('const LAW_RECONCILE_ROLES_RENAMED = { owner: true };')
        temps.append(t)
        code, out = run(t)
        arm('a RENAMED allow-list is exit 2, not a silent pass', code == 2,
            'exit %d\n%s' % (code, out[-400:]))

        # 6. An empty vocabulary must not manufacture a finding.
        t = fixture(None, "  sairnlaw: [],")
        temps.append(t)
        code, out = run(t)
        arm('an EMPTY ROLES_BY_APP entry is exit 2, not a fabricated finding',
            code == 2, 'exit %d\n%s' % (code, out[-400:]))

        print('')
        print('THE REAL TREE')
        r = subprocess.run([sys.executable, CHECK], cwd=REPO,
                           capture_output=True, text=True, encoding='utf-8',
                           errors='replace')
        out = (r.stdout or '') + (r.stderr or '')
        arm('api/sd-data.js LAW_RECONCILE_ROLES names only real SAIRNlaw roles',
            r.returncode == 0, 'exit %d\n%s' % (r.returncode, out[-500:]))
        print(out.strip())
    finally:
        for t in temps:
            shutil.rmtree(t, ignore_errors=True)

    print('')
    if FAILURES:
        print('FAILED: %d arm(s)' % len(FAILURES))
        return 1
    print('OK: the checker separates the shipped defect from the fixed tree, '
          'and fails CLOSED on a gone anchor and an empty vocabulary.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
