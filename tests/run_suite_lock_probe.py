"""The control for the 2026-09-09 probe-restore failure. Run:

    python tests/run_suite_lock_probe.py

WHAT WENT WRONG, because the fix is unreadable without it. Probes under tests/
mutate a real tracked file and restore the bytes THEY read at their own start,
in a finally. Alone that is correct. In parallel it is not:

    run A snapshots the clean file, mutates it
    run B snapshots THE MUTATED FILE as its "original"
    run A restores clean
    run B restores the mutation -- and it stays on disk

Nothing serialised those runs. `tools/run_all_tests.py --hook` fires on every
`git push`, async, and on 2026-09-09 THREE concurrent `--hook` runs were alive
in one tree at 09:05:38, 09:06:06 and 09:06:21, plus two copies of
tests/seam_check/run_probe.py started in the same second. That is how
sairnvet.html repeatedly lost the corrupt-store guard from ebf2823e overnight,
and how tools/reachability_exemptions.json kept a zzDefinitelyNotAFinding entry
with no run of live_mode_probe having failed.

THE `finally` WAS NEVER THE DEFECT. Both runs restored exactly what they read.
"Make it restore reliably" cannot fix a wrong baseline -- so the fix is a lock
so there is only one run to snapshot against, plus a per-probe refusal to
snapshot a file that is already dirty, which is the half the lock cannot see
(a process KILLED before its finally leaves residue no lock notices). A
stranded `run_delegation_probe` mutation to api/sd-data.js was found on disk
during this work, with the probe already gone: the kill case is not theoretical.

ALL SEVEN MUTATING PROBES ARE DRIVEN, not the two named in the incident. The
repo's own standing lesson is that a fix verified on one copy is not verified
if a second copy runs unattended -- so arm E dirties each probe's real target
and requires each to skip.

IT NEVER WRITES THIS REPO. Arms E and F run in a throwaway `git worktree`
(~2s, shared object store), which is what makes it safe to dirty
stonedesk.html and sairndental.html at all. Arms A-D touch no tracked file.

ARM F IS SYNTHETIC ON PURPOSE. It stands in for the pre-fix probe with a
twelve-line read-inject-restore rather than checking the old file out of HEAD:
a probe pinned to what HEAD happens to contain rots the moment the fix lands,
which is the exact failure live_mode_probe's own header records.
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True).stdout.strip()
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import run_all_tests as rat                              # noqa: E402

EXEMPTIONS = 'tools/reachability_exemptions.json'

# probe -> the real tracked file it snapshots and restores.
GUARDED = [
    ('tests/suite_control_backfill_probe.py', 'sairnvet.html'),
    ('tests/reachability/live_mode_probe.py', EXEMPTIONS),
    ('tests/seam_check/run_probe.py', 'api/legal-deadlines.js'),
    ('tests/seam_check/run_delegation_probe.py', 'api/sd-data.js'),
    ('tests/seam_check/run_or_default_probe.py', 'api/sairndental/public-book.js'),
    ('tests/sairndental_write_failure_probe.py', 'sairndental.html'),
    ('tests/sd_timesheet_pay_est_probe.py', 'stonedesk.html'),
]

R = {}


def check(label, actual, expected):
    R[label] = (actual == expected, actual, expected)


def git(cwd, *a):
    return subprocess.run(['git'] + list(a), cwd=cwd, capture_output=True, text=True)


# ---- A. the lock is exclusive, and releasing it makes it available ----
rat.release_lock()                          # start from a known state
check('A1 first acquire succeeds', rat.acquire_lock(), True)
check('A2 second acquire is refused', rat.acquire_lock(), False)
rat.release_lock()
check('A3 acquire succeeds again after release', rat.acquire_lock(), True)

# ---- B. an abandoned lock is stolen, so a killed run cannot block forever ----
# Age-based, because os.kill(pid, 0) on Windows does not test liveness -- it
# calls TerminateProcess. The ceiling sits well above the 400s hook timeout; a
# killed run costs one skipped cycle, not a permanent block.
old = time.time() - rat.LOCK_MAX_AGE - 60
os.utime(rat.LOCK, (old, old))
check('B1 a stale lock is stolen', rat.acquire_lock(), True)
os.utime(rat.LOCK, None)
check('B2 a fresh lock is not stolen', rat.acquire_lock(), False)

# ---- C. the lock does not live in the working tree ----
# An untracked lockfile inside REPO shows as `??` and makes every
# clean-tree-dependent probe skip -- trading this bug for a cascade. Asserts
# the LOCKFILE is absent from git status, not that the tree is clean: `== ''`
# was the first version and it went red the moment this probe was written,
# because the fix it tests was uncommitted at the time.
check('C1 lockfile is outside the repo',
      os.path.abspath(rat.LOCK).startswith(os.path.abspath(ROOT) + os.sep), False)
check('C2 the lockfile never appears in git status',
      os.path.basename(rat.LOCK) in git(ROOT, 'status', '--porcelain').stdout, False)

# ---- D. a real second run declines rather than corrupting the first ----
# The lock is still held here, so this must come back SKIPPED without having
# executed a single test file.
r = subprocess.run([sys.executable, 'tools/run_all_tests.py'], cwd=ROOT,
                   capture_output=True, text=True, timeout=180)
out = (r.stdout or '') + (r.stderr or '')
check('D1 a concurrent manual run exits 3', r.returncode, 3)
check('D2 and says SKIPPED', out.startswith('SKIPPED'), True)
check('D3 and ran nothing', 'RAN:' in out, False)
rat.release_lock()

# ---- E/F: every mutating probe, in a throwaway worktree ----
TREE_BEFORE = git(ROOT, 'status', '--porcelain').stdout
wt = os.path.join(tempfile.gettempdir(), 'sairn-lock-probe-wt-%d' % os.getpid())
add = git(ROOT, 'worktree', 'add', '-q', '--detach', wt, 'HEAD')
check('E0 the throwaway worktree was created', add.returncode, 0)
try:
    # The worktree is checked out at HEAD, which does not carry uncommitted
    # guards. Copy the ON-DISK probes in, so this tests the files as they
    # actually are -- before the commit and after it alike.
    for probe, _ in GUARDED:
        dest = os.path.join(wt, probe.replace('/', os.sep))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copy2(os.path.join(ROOT, probe.replace('/', os.sep)), dest)
    # NOT `== ''`. The copies above are themselves uncommitted edits before the
    # fix lands, so the worktree legitimately shows them as modified -- the
    # first version asserted a clean worktree and went red for that reason
    # alone, which says nothing about any guard. The claim worth making is that
    # arm E leaves NOTHING BEHIND beyond those copies.
    WT_BASE = git(wt, 'status', '--porcelain').stdout
    check('E0b the worktree holds only the probe copies',
          [l[3:] for l in WT_BASE.splitlines()],
          sorted(p for p, _ in GUARDED if
                 git(wt, 'status', '--porcelain', '--', p).stdout.strip()))

    for probe, target in GUARDED:
        tgt = os.path.join(wt, target.replace('/', os.sep))
        name = probe.split('/')[-1][:-3]

        # A trailing newline: a real git-modified state that leaves .js, .html
        # and .json all still valid, so nothing goes red for the wrong reason.
        with io.open(tgt, 'a', encoding='utf-8', newline='') as fh:
            fh.write('\n')
        assert git(wt, 'status', '--porcelain', '--', target).stdout.strip(), target
        stamp = time.time() - 10000
        os.utime(tgt, (stamp, stamp))

        p = subprocess.run([sys.executable, probe], cwd=wt,
                           capture_output=True, text=True, timeout=900)
        pout = (p.stdout or '') + (p.stderr or '')
        check('E %-34s skips on a dirty target' % name, p.returncode, 3)
        check('E %-34s says SKIPPED' % name, 'SKIPPED' in pout, True)
        # The one that matters: a probe that ran and "restored" would have
        # written the file, adopting the modification as the new baseline.
        check('E %-34s wrote nothing' % name,
              abs(os.path.getmtime(tgt) - stamp) < 2, True)

        git(wt, 'checkout', '--', target)

    check('E9 arm E left nothing behind', git(wt, 'status', '--porcelain').stdout, WT_BASE)

    # ---- F. the pre-fix shape, driven in the other direction ----
    # Twelve lines standing in for every probe written before 2026-09-09: read
    # the bytes, mutate, restore in a finally, no baseline check. It must NOT
    # skip and it must WRITE -- that write is the bake-in, and the file it
    # hands back still carries the modification nobody put there deliberately
    # while the probe reports a clean run.
    ex = os.path.join(wt, EXEMPTIONS.replace('/', os.sep))
    with io.open(ex, 'a', encoding='utf-8', newline='') as fh:
        fh.write('\n')
    dirty_bytes = open(ex, 'rb').read()
    stamp = time.time() - 10000
    os.utime(ex, (stamp, stamp))

    def prefix_shape():
        original = open(ex, 'rb').read()            # <-- already dirty
        try:
            open(ex, 'ab').write(b'\n')
        finally:
            open(ex, 'wb').write(original)
        return 0

    check('F1 the pre-fix shape does not skip', prefix_shape(), 0)
    check('F2 and it wrote the file', abs(os.path.getmtime(ex) - stamp) > 2, True)
    check('F3 handing the modification back as the new baseline',
          open(ex, 'rb').read(), dirty_bytes)
    check('F4 so git still calls it modified, silently',
          git(wt, 'status', '--porcelain', '--', EXEMPTIONS).stdout.strip() != '', True)
finally:
    git(ROOT, 'worktree', 'remove', '--force', wt)
    git(ROOT, 'worktree', 'prune')
    rat.release_lock()

check('Z1 the worktree was cleaned up', os.path.exists(wt), False)
# Not `== ''`: this probe must be runnable from a tree that already has
# uncommitted work. The claim is that it changed NOTHING, so compare against
# what the tree looked like before arm E, byte for byte.
check('Z2 and this repo is exactly as it was',
      git(ROOT, 'status', '--porcelain').stdout, TREE_BEFORE)

for k in sorted(R):
    ok, actual, expected = R[k]
    print('  %-6s %s' % ('ok' if ok else 'FAIL', k))
    if not ok:
        print('         expected %r, got %r' % (expected, actual))
bad = [k for k in R if not R[k][0]]
print()
print('suite-lock: %d checks, %d failed' % (len(R), len(bad)))
sys.exit(1 if bad else 0)
