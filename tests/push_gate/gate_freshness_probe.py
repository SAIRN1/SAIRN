"""Control for push-gate check 10 -- the gate that ran may not be the gate that exists.

    python tests/push_gate/gate_freshness_probe.py

WHY CHECK 10 EXISTS, and it is not hypothetical. Check 8 -- "a PROBE fixture
commit must not reach origin" -- landed at 10:08 on 2026-09-10. At 13:24, THREE
HOURS LATER, `8fa974f9 "PROBE clean api change"` became the tip of origin/main
anyway, putting api/_lib/zz_probe_clean.js into the production tree.

Check 8 was not broken. Driven directly with a PROBE commit in range it fires
and exits 1 -- measured, not assumed, and the first measurement said otherwise
because it read `${PIPESTATUS[0]}` of `printf | python | tail`, which is
printf's exit code. The gate was right and the instrument was wrong.

The real mechanism: the hook runs
`$(git rev-parse --show-toplevel)/tools/sairn_push_gate_hook.py`, the WORKING
TREE copy. A session running since before 10:08 that has not synced executes
the pre-check-8 gate, which contains no check 8 at all. Four clones and long
sessions make that window hours wide, and IT APPLIES TO EVERY CHECK IN THE
FILE.

RUNS IN THROWAWAY WORKTREES. It never writes this clone and never pushes.
"""
import io
import os
import subprocess
import sys
import tempfile

REPO = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True).stdout.strip()
REL = 'tools/sairn_push_gate_hook.py'
R = {}


def check(label, actual, expected):
    R[label] = (actual == expected, actual, expected)


def git(cwd, *a):
    return subprocess.run(['git'] + list(a), cwd=cwd, capture_output=True, text=True)


def run_gate(wt):
    """Drive the pre-push hook the way git does, and return (exit, output).

    stdin is `<local ref> <local sha> <remote ref> <remote sha>`; the range the
    gate inspects is remote..local.
    """
    tip = git(wt, 'rev-parse', 'HEAD').stdout.strip()
    base = git(wt, 'rev-parse', 'origin/main').stdout.strip()
    payload = 'refs/heads/main %s refs/heads/main %s\n' % (tip, base)
    p = subprocess.run([sys.executable, os.path.join(wt, REL.replace('/', os.sep)),
                        '--pre-push'],
                       input=payload, cwd=wt, capture_output=True, text=True,
                       timeout=600)
    return p.returncode, (p.stdout or '') + (p.stderr or '')


TREE_BEFORE = git(REPO, 'status', '--porcelain').stdout
wt = os.path.join(tempfile.gettempdir(), 'gate-fresh-probe-%d' % os.getpid())
add = git(REPO, 'worktree', 'add', '-q', '--detach', wt, 'origin/main')
check('A0 the throwaway worktree was created', add.returncode, 0)
# THE WORKTREE IS AT origin/main, WHICH MAY NOT CARRY THE GATE BEING TESTED.
# The first version of this probe forgot that and drove the OLD gate, so the
# arms for check 10 came back saying it does not exist -- a probe passing on
# the absence of the thing it tests. Copy the ON-DISK gate in, so this tests
# the file as it actually is, before the commit and after it alike.
import shutil                                                    # noqa: E402
shutil.copy2(os.path.join(REPO, REL.replace('/', os.sep)),
             os.path.join(wt, REL.replace('/', os.sep)))
# ...AND THEN MAKE THAT THE BASELINE. Copying the gate in is not enough: check
# 10 compares the file against `origin/main:<path>`, so a gate that is newer
# than origin -- which it always is while the fix is uncommitted -- makes the
# "in-sync" and "CRLF-only" arms fire and look like failures of the check.
# The second version of this probe hit exactly that and the arms were right to
# go red; the SETUP was wrong. Committing the copied gate and pointing this
# worktree's origin/main at it makes "in sync" true BY CONSTRUCTION, so the
# arms test the check instead of testing whether I have pushed yet.
git(wt, 'add', REL)
git(wt, '-c', 'user.email=probe@sairn', '-c', 'user.name=probe',
    'commit', '-q', '-m', 'probe: baseline gate')
_baseline = git(wt, 'rev-parse', 'HEAD').stdout.strip()
git(wt, 'update-ref', 'refs/remotes/origin/main', _baseline)
try:
    # ── A. a gate identical to origin's says nothing ────────────────────────
    rc, out = run_gate(wt)
    check('A1 an in-sync gate is silent about freshness',
          'Gate-freshness' in out, False)

    # ── B. a gate that differs from origin's NOTICES ────────────────────────
    # Any real edit will do; the check compares content, not a version string.
    path = os.path.join(wt, REL.replace('/', os.sep))
    original = io.open(path, 'rb').read()
    io.open(path, 'wb').write(original + b"\n# probe: a local edit to this gate\n")
    rc, out = run_gate(wt)
    check('B1 a modified gate produces the notice',
          'Gate-freshness (check 10) NOTICE' in out, True)
    check('B2 and it does NOT block -- report-only', rc, 0)
    check('B3 and it says a clean pass is not a full one',
          'do not read a clean pass as a full one' in out, True)
    io.open(path, 'wb').write(original)

    # ── C. A CRLF-ONLY DIFFERENCE IS NOT DRIFT ──────────────────────────────
    # This repo has produced four separate false "files differ" alarms from
    # line endings alone. A freshness notice that fires on every push in a CRLF
    # clone is worth less than no notice: it would be the notice nobody reads,
    # on the check whose entire job is to be believed.
    io.open(path, 'wb').write(original.replace(b'\n', b'\r\n'))
    rc, out = run_gate(wt)
    check('C1 a CRLF-only difference does not fire', 'Gate-freshness' in out, False)
    io.open(path, 'wb').write(original)

    # ── D. it fails OPEN and SILENT, never taking a push down with it ───────
    # A check about the gate's own freshness must not be the thing that blocks
    # a legitimate push. Simulated by making the comparison impossible: with no
    # origin/main to read, `git show` fails and the check must vanish.
    git(wt, 'update-ref', '-d', 'refs/remotes/origin/main')
    tip = git(wt, 'rev-parse', 'HEAD').stdout.strip()
    p = subprocess.run([sys.executable, path, '--pre-push'],
                       input='refs/heads/main %s refs/heads/main %s\n' % (tip, tip),
                       cwd=wt, capture_output=True, text=True, timeout=600)
    check('D1 with no origin/main to compare, it stays quiet',
          'Gate-freshness' in ((p.stdout or '') + (p.stderr or '')), False)
    check('D2 and does not block', p.returncode, 0)

    # ── E. THE THING IT EXISTS FOR: check 8 still bites ─────────────────────
    # Check 10 reports that the gate may be old. That is only worth anything
    # while the checks it is vouching for actually work, so this drives check 8
    # in the same harness -- the exact scenario of 2026-09-10.
    git(wt, 'fetch', '-q', 'origin')
    io.open(os.path.join(wt, 'api', '_lib', 'zz_gatefresh_probe.js'), 'w',
            encoding='utf-8').write('// probe fixture\nmodule.exports = {};\n')
    git(wt, 'add', 'api/_lib/zz_gatefresh_probe.js')
    git(wt, '-c', 'user.email=probe@sairn', '-c', 'user.name=probe',
        'commit', '-q', '-m', 'PROBE clean api change')
    rc, out = run_gate(wt)
    check('E1 check 8 still BLOCKS a PROBE fixture commit', rc, 1)
    check('E2 and names it', 'PROBE fixture commit' in out, True)
finally:
    git(REPO, 'worktree', 'remove', '--force', wt)
    git(REPO, 'worktree', 'prune')

check('Z1 the worktree was cleaned up', os.path.exists(wt), False)
# NOT `== ''`. This probe must be runnable from a tree that already has
# uncommitted work -- it was written against exactly such a tree. The claim is
# that it changed NOTHING, so compare with what was there before it ran.
check('Z2 and this clone is exactly as it was',
      git(REPO, 'status', '--porcelain').stdout, TREE_BEFORE)

for k in sorted(R):
    ok, actual, expected = R[k]
    print('  %-6s %s' % ('ok' if ok else 'FAIL', k))
    if not ok:
        print('         expected %r, got %r' % (expected, actual))
bad = [k for k in R if not R[k][0]]
print()
print('gate-freshness: %d checks, %d failed' % (len(R), len(bad)))
sys.exit(1 if bad else 0)
