"""run_push_timeout_guard_probe.py -- does tools/push_timeout_guard.py actually refuse a timed push?

    python tests/run_push_timeout_guard_probe.py

Exit: 0 all passed - 1 an arm FAILED - 2 COULD NOT RUN - 3 not applicable here (no `timeout` binary)

Drives the REAL process chain, not a synthetic one: `timeout 60 git -c alias...`
runs the guard as git -> sh -> python, which is exactly how git runs a pre-push
hook. No push happens anywhere in this probe -- the point of the guard is that
a timed push must never start, so it is not started here either.

Each refusal arm has a control that makes it fail on purpose: the same chain
with the killer list emptied must PASS, or the arm was not testing the list.
"""
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
GUARD = os.path.join(REPO, 'tools', 'push_timeout_guard.py')
PY = sys.executable

if not os.path.isfile(GUARD):
    print('COULD NOT RUN: %s is missing' % GUARD)
    sys.exit(2)
TIMEOUT_BIN = shutil.which('timeout')
if not TIMEOUT_BIN:
    print('NOT APPLICABLE: no `timeout` binary on PATH, so the shape this guards cannot occur here')
    sys.exit(3)

bad = total = 0


def arm(name, ok, detail=''):
    global bad, total
    total += 1
    if ok:
        print('  PASS  ' + name)
    else:
        bad += 1
        print('  FAIL  ' + name + ('\n        ' + detail[:400] if detail else ''))


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=REPO)
    return r.returncode, (r.stdout or '') + (r.stderr or '')


def hook_chain(guard_path, timed):
    """The guard run the way git runs a hook: git -> sh -> python. Optionally under timeout."""
    alias = 'alias.ptg=!"%s" "%s" --pre-push' % (PY.replace('\\', '/'), guard_path.replace('\\', '/'))
    cmd = ['git', '-c', alias, 'ptg']
    return run(([TIMEOUT_BIN, '60'] if timed else []) + cmd)


print('PUSH TIMEOUT GUARD PROBE')
rc, out = run([PY, GUARD, '--fixtures'])
arm('the criteria classify all their own fixtures (exit 0)', rc == 0, out)

rc, out = hook_chain(GUARD, timed=False)
arm('A. hook chain, NO timeout: allowed (exit 0, no REFUSED)', rc == 0 and 'REFUSED' not in out, out)

rc, out = hook_chain(GUARD, timed=True)
arm('B. hook chain UNDER timeout: REFUSED (exit 1) and the timeout is named',
    rc == 1 and 'REFUSED (push_timeout_guard)' in out and 'timeout' in out.lower(), 'rc=%d %s' % (rc, out))

rc, out = run([TIMEOUT_BIN, '60', PY, GUARD, '--pre-push'])
arm('C. the guard directly under timeout: REFUSED (exit 1)', rc == 1 and 'REFUSED' in out, 'rc=%d %s' % (rc, out))

# CONTROL: the same chain, with the killer list emptied. If B still refused,
# B was never testing the list -- it would be refusing for some other reason.
tmp = tempfile.mkdtemp(prefix='ptg_ctl_')
try:
    src = open(GUARD, encoding='utf-8').read()
    anchor = "KILLERS = {'timeout', 'timeout.exe', 'gtimeout'}"
    if src.count(anchor) != 1:
        arm('CONTROL anchor found exactly once', False, 'found %d time(s)' % src.count(anchor))
    else:
        ctl = os.path.join(tmp, 'push_timeout_guard.py')
        open(ctl, 'w', encoding='utf-8').write(src.replace(anchor, 'KILLERS = set()'))
        rc, out = hook_chain(ctl, timed=True)
        arm('CONTROL: killer list emptied -> the SAME timed chain is allowed (so B tested the list)',
            rc == 0 and 'REFUSED' not in out, 'rc=%d %s' % (rc, out))
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# The static layer, on the real file it was written for and on that file's
# pre-fix shape: tools/push_retry.py pushed through a 120 s git() helper.
sys.path.insert(0, os.path.join(REPO, 'tools'))
import push_timeout_guard as G                                   # noqa: E402
pr = open(os.path.join(REPO, 'tools', 'push_retry.py'), encoding='utf-8').read()
arm('D. tools/push_retry.py as it stands: no timed push', G.scan_python(pr) == [], repr(G.scan_python(pr)))
fixed = "git('push', 'origin', 'main', timeout=None)"
if pr.count(fixed) != 1:
    arm('D-CONTROL anchor found exactly once', False, 'found %d time(s)' % pr.count(fixed))
else:
    hits = G.scan_python(pr.replace(fixed, "git('push', 'origin', 'main')"))
    arm('D-CONTROL: the pre-fix push (no timeout=None) IS flagged', len(hits) == 1, repr(hits))

# The tooling layer ON THE PUSH PATH, in a throwaway repo -- never by planting a
# timed push in THIS tree, which would be a mutant in a tracked file, the very
# hazard this guard exists for.
tmp = tempfile.mkdtemp(prefix='ptg_repo_')
try:
    def g(*a):
        return subprocess.run(['git', '-C', tmp] + list(a), capture_output=True, text=True)
    g('init', '-q')
    os.makedirs(os.path.join(tmp, 'tools'))
    shutil.copy(GUARD, os.path.join(tmp, 'tools', 'push_timeout_guard.py'))
    tool = os.path.join(tmp, 'tools', 'pusher.py')
    open(tool, 'w').write("import subprocess\nsubprocess.run(['git', 'push', 'origin', 'main'], timeout=60)\n")
    g('add', '-A')
    r = subprocess.run([PY, os.path.join(tmp, 'tools', 'push_timeout_guard.py'), '--pre-push'],
                       capture_output=True, text=True, cwd=tmp)
    arm('E. --pre-push in a repo whose tool pushes with timeout=: REFUSED and the file named',
        r.returncode == 1 and 'tools/pusher.py' in (r.stderr or ''), 'rc=%d %s' % (r.returncode, r.stderr))
    open(tool, 'w').write("import subprocess\nsubprocess.run(['git', 'push', 'origin', 'main'])\n")
    r = subprocess.run([PY, os.path.join(tmp, 'tools', 'push_timeout_guard.py'), '--pre-push'],
                       capture_output=True, text=True, cwd=tmp)
    arm('E-CONTROL: the same repo with the timeout removed is allowed', r.returncode == 0,
        'rc=%d %s' % (r.returncode, r.stderr))
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print('\n%d of %d passed, %d failed' % (total - bad, total, bad))
sys.exit(1 if bad else 0)
