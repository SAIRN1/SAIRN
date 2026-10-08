"""Item 2: re-run each of the 86 failures ALONE on a CLEAN tree.

WHY A FRESH CLONE AND NOT THIS CLONE. The question is whether a failure was an
artifact of docs/report-only-reachability.json being modified mid-run. Re-running
here would answer it only if this clone is clean AND stays clean -- and the whole
finding is that probes dirty the tree. A `git clone --local` at the same commit
the suite ran (aa2f014d) is clean by construction, and each probe is run from it.

VERDICT RULE, fixed before the run so it cannot be fitted afterwards:
  REAL      -- fails alone on a clean tree at the same commit
  ARTIFACT  -- passes alone on a clean tree (the suite-run failure was not
               reproducible in isolation)
  COULD-NOT-RUN -- exits 2, or the runner could not launch it; never folded into
               either of the first two

A BOUND PER PROBE, because one hanging probe must not eat the batch: 420s. A
probe that hits it is recorded TIMEOUT and counted with COULD-NOT-RUN, never as
a pass.

Appends one TSV line per probe AS IT FINISHES -- the batch-24 lesson, paid for by
a watcher that wrote only at the end and lost 3h of data to a kill.
"""
import io
import os
import shutil
import subprocess
import sys
import time

SP = os.path.dirname(os.path.abspath(__file__))
REPO = r'C:\Users\marsh\Documents\SAIRN-cody'
SUITE_SHA = 'aa2f014dd21b088711944b5675104471c43b0502'
BOUND = 420
OUT = os.path.join(SP, 'i2_rerun.tsv')
WT = os.path.join(os.environ.get('TEMP', r'C:\Windows\Temp'),
                  'cody-b26-triage-clone')


def rm_ro(fn, path, _exc):
    try:
        os.chmod(path, 0o700)
        fn(path)
    except Exception:                                       # noqa: BLE001
        pass


def git(*a, **kw):
    return subprocess.run(['git'] + list(a), capture_output=True,
                          encoding='utf-8', errors='replace', **kw)


if os.path.isdir(WT):
    shutil.rmtree(WT, onerror=rm_ro)
r = git('clone', '--local', '--no-checkout', '--quiet', REPO, WT)
if r.returncode != 0:
    sys.exit('COULD NOT RUN: clone failed: %s' % r.stderr.strip()[:200])
r = git('checkout', '--detach', SUITE_SHA, cwd=WT)
if r.returncode != 0:
    sys.exit('COULD NOT RUN: checkout %s failed: %s' % (SUITE_SHA, r.stderr.strip()[:200]))
# session identity, so probes that ask who they are do not refuse
src = os.path.join(REPO, '.git', 'sairn-session')
if os.path.isfile(src):
    shutil.copy(src, os.path.join(WT, '.git', 'sairn-session'))

rows = [l.rstrip('\n').split('\t') for l in io.open(
    os.path.join(SP, 'i2_fails.tsv'), encoding='utf-8') if l.strip()]
out = io.open(OUT, 'w', encoding='utf-8', newline='\n')
out.write('kind\ttest\tverdict\trc\tseconds\tdirtied\tsuite_reason\n')
out.flush()

print('clean clone at %s -> %s' % (SUITE_SHA[:12], WT))
print('%d probe(s) to re-run, bound %ds each' % (len(rows), BOUND))

for i, row in enumerate(rows, 1):
    kind, test = row[0], row[1]
    reason = row[2] if len(row) > 2 else ''
    cmd = (['node', test] if kind == 'node' else [sys.executable, test])
    t0 = time.time()
    try:
        p = subprocess.run(cmd, cwd=WT, capture_output=True, encoding='utf-8',
                           errors='replace', timeout=BOUND)
        rc = p.returncode
        verdict = 'ARTIFACT' if rc == 0 else ('COULD-NOT-RUN' if rc == 2 else 'REAL')
    except subprocess.TimeoutExpired:
        rc, verdict = 'TIMEOUT', 'COULD-NOT-RUN'
    except Exception as e:                                  # noqa: BLE001
        rc, verdict = 'LAUNCH-FAIL:%s' % type(e).__name__, 'COULD-NOT-RUN'
    secs = time.time() - t0
    # did THIS probe dirty the clean clone? asked per probe, not once at the end
    st = git('status', '--porcelain', cwd=WT)
    dirtied = len([l for l in (st.stdout or '').splitlines() if l.strip()])
    if dirtied:
        git('checkout', '--', '.', cwd=WT)
        git('clean', '-qfd', cwd=WT)
    out.write('%s\t%s\t%s\t%s\t%.1f\t%d\t%s\n'
              % (kind, test, verdict, rc, secs, dirtied, reason[:120]))
    out.flush()
    print('%3d/%d  %-10s %-54s rc=%-7s %5.0fs dirty=%d'
          % (i, len(rows), verdict, test, rc, secs, dirtied))

out.close()
shutil.rmtree(WT, onerror=rm_ro)
print('DONE -> %s ; clone removed: %s' % (OUT, not os.path.isdir(WT)))
