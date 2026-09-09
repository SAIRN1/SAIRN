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
(a process KILLED before its finally leaves residue no lock notices).

WHY THE ARMS BELOW ARE SYNTHETIC WHERE THEY ARE. Arm G stands in for the
pre-fix probe with a twelve-line read-inject-restore rather than checking out
the real old file from HEAD. A probe pinned to what HEAD happens to contain
rots the moment the fix lands -- the exact failure live_mode_probe's own header
records and was rewritten to avoid. The stand-in cannot be fixed out from under
this file.

NO APP FILE IS EVER TOUCHED. The only tracked file written here is
tools/reachability_exemptions.json, saved as bytes up front, restored in a
finally, and verified byte-identical by sha256 at the end.
"""
import hashlib
import io
import os
import subprocess
import sys
import time

ROOT = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True).stdout.strip()
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, os.path.join(ROOT, 'tests'))
import run_all_tests as rat                              # noqa: E402
import suite_control_backfill_probe as backfill          # noqa: E402

EXEMPTIONS = 'tools/reachability_exemptions.json'
EX_ABS = os.path.join(ROOT, EXEMPTIONS)
LIVE_PROBE = 'tests/reachability/live_mode_probe.py'

R = {}


def check(label, actual, expected):
    R[label] = (actual == expected, actual, expected)


def porcelain(path):
    return subprocess.run(['git', 'status', '--porcelain', '--', path], cwd=ROOT,
                          capture_output=True, text=True).stdout.strip()


# A dirty file that is still valid JSON, so nothing downstream fails for the
# wrong reason -- an arm that goes red on a parse error proves nothing about
# the guard.
def make_dirty():
    body = io.open(EX_ABS, encoding='utf-8').read()
    io.open(EX_ABS, 'w', encoding='utf-8', newline='').write(
        body.replace('"exemptions": [',
                     '"exemptions": [\n    {"file": "zz_probe_only.html", '
                     '"code": "R3", "name": "zzLockProbeFixture", '
                     '"added": "probe", "reason": "probe fixture"},', 1))


ORIGINAL = open(EX_ABS, 'rb').read()
BEFORE = hashlib.sha256(ORIGINAL).hexdigest()
try:
    # ---- A. the lock is exclusive, and releasing it makes it available ----
    rat.release_lock()                      # start from a known state
    check('A1 first acquire succeeds', rat.acquire_lock(), True)
    check('A2 second acquire is refused', rat.acquire_lock(), False)
    rat.release_lock()
    check('A3 acquire succeeds again after release', rat.acquire_lock(), True)

    # ---- B. an abandoned lock is stolen, so a killed run cannot block forever
    # Age-based, because os.kill(pid, 0) on Windows does not test liveness --
    # it calls TerminateProcess. The ceiling sits well above the 400s hook
    # timeout; a killed run costs one skipped cycle, not a permanent block.
    old = time.time() - rat.LOCK_MAX_AGE - 60
    os.utime(rat.LOCK, (old, old))
    check('B1 a stale lock is stolen', rat.acquire_lock(), True)
    os.utime(rat.LOCK, None)
    check('B2 a fresh lock is not stolen', rat.acquire_lock(), False)

    # ---- C. the lock does not live in the working tree ----
    # An untracked lockfile inside REPO shows as `??` and makes every
    # clean-tree-dependent probe skip -- trading this bug for a cascade.
    check('C1 lockfile is outside the repo',
          os.path.abspath(rat.LOCK).startswith(os.path.abspath(ROOT) + os.sep), False)
    # Asserts the LOCKFILE is absent from git status, not that the tree is
    # clean. `== ''` was the first version and it went red the moment this
    # probe was written, because the fix it tests was uncommitted at the time
    # -- an assertion about the whole tree dressed up as one about the lock.
    check('C2 the lockfile never appears in git status',
          os.path.basename(rat.LOCK) in subprocess.run(
              ['git', 'status', '--porcelain'], cwd=ROOT,
              capture_output=True, text=True).stdout, False)

    # ---- D. a real second run declines rather than corrupting the first ----
    # The lock is still held here, so this must come back SKIPPED without
    # having executed a single test file.
    r = subprocess.run([sys.executable, 'tools/run_all_tests.py'], cwd=ROOT,
                       capture_output=True, text=True, timeout=120)
    out = (r.stdout or '') + (r.stderr or '')
    check('D1 a concurrent manual run exits 3', r.returncode, 3)
    check('D2 and says SKIPPED', out.startswith('SKIPPED'), True)
    check('D3 and ran nothing', 'RAN:' in out, False)
    rat.release_lock()

    # ---- E. the backfill probe refuses to snapshot a dirty target ----
    # Retargeted at the exemptions file rather than one of its five real app
    # files, so this arm exercises the guard without ever writing sairnvet.html
    # or sairndental.html. Only the pre-snapshot branch is reached.
    make_dirty()
    check('E0 the fixture really is dirty in git', porcelain(EXEMPTIONS) != '', True)
    saved = backfill.SUITES
    try:
        backfill.SUITES = [('tests/run_suite_lock_probe.py', EXEMPTIONS, [])]
        check('E1 a dirty target makes the backfill probe skip', backfill.main(), 3)
    finally:
        backfill.SUITES = saved

    # ---- F. live_mode_probe refuses the same way, as a real subprocess ----
    stamp = time.time() - 10000
    os.utime(EX_ABS, (stamp, stamp))
    r = subprocess.run([sys.executable, LIVE_PROBE], cwd=ROOT,
                       capture_output=True, text=True, timeout=300)
    out = (r.stdout or '') + (r.stderr or '')
    check('F1 live_mode_probe exits 3 on a dirty exemptions file', r.returncode, 3)
    check('F2 and says nothing was verified', 'SKIPPED' in out, True)
    check('F3 and does not claim LIVE MODE VERIFIED', 'LIVE MODE VERIFIED' in out, False)
    check('F4 and did not write the file at all',
          abs(os.path.getmtime(EX_ABS) - stamp) < 2, True)

    # ---- G. the pre-fix shape, driven in the other direction ----
    # Twelve lines standing in for every probe written before 2026-09-09: read
    # the bytes, inject, restore in a finally, no baseline check. It must NOT
    # skip, and it must WRITE -- which is the bake-in. The file it hands back
    # still contains the fixture nobody put there deliberately, and it would
    # have reported a clean run.
    def prefix_shape():
        original = open(EX_ABS, 'rb').read()          # <-- already dirty
        try:
            open(EX_ABS, 'ab').write(b'\n')
        finally:
            open(EX_ABS, 'wb').write(original)
        return 0

    os.utime(EX_ABS, (stamp, stamp))
    check('G1 the pre-fix shape does not skip', prefix_shape(), 0)
    check('G2 and it wrote the file', abs(os.path.getmtime(EX_ABS) - stamp) > 2, True)
    check('G3 baking the fixture in as the new baseline',
          'zzLockProbeFixture' in io.open(EX_ABS, encoding='utf-8').read(), True)
finally:
    open(EX_ABS, 'wb').write(ORIGINAL)
    rat.release_lock()

after = hashlib.sha256(open(EX_ABS, 'rb').read()).hexdigest()
restored = after == BEFORE

for k in sorted(R):
    ok, actual, expected = R[k]
    print('  %-6s %s' % ('ok' if ok else 'FAIL', k))
    if not ok:
        print('         expected %r, got %r' % (expected, actual))
print()
print('%-38s %s  %s' % (EXEMPTIONS + ' restored:', restored, BEFORE[:16]))
bad = [k for k in R if not R[k][0]]
print('suite-lock: %d checks, %d failed' % (len(R), len(bad)))
sys.exit(0 if (not bad and restored) else 1)
