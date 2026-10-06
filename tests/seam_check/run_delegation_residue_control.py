"""CONTROL for the 2026-10-06 residue guard in run_delegation_probe.py.

The guard is three layers -- a `finally` via the plant() context manager, an
atexit net, and a sentinel file that survives a kill -- and a guard nobody has
watched fire is a guard whose behaviour nobody knows. Every arm here PLANTS the
failure and requires the guard to catch it; the last two require the OTHER
direction, because a guard that always reports residue is as useless as one
that never does.

CONTROLS_FOR = ['tests/seam_check/run_delegation_probe.py']

Run:  python tests/seam_check/run_delegation_residue_control.py

Exit 0 every arm held, 1 an arm failed, 3 SKIPPED because a precondition was
not met -- which is not a pass.
"""
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROBE = os.path.join(REPO, 'tests', 'seam_check', 'run_delegation_probe.py')
EP = 'api/sd-data.js'
LIB = 'api/_lib/subcontractor-compliance.js'

passed = 0
failed = []


def arm(name, cond, detail=''):
    global passed
    if cond:
        passed += 1
        print('  ok   ' + name)
    else:
        failed.append(name)
        print('  FAIL ' + name + ('  ' + detail if detail else ''))


def clean(path):
    r = subprocess.run(['git', 'status', '--porcelain', '--', path],
                       cwd=REPO, capture_output=True, text=True)
    return r.stdout.strip() == ''


# ── PRECONDITION. The targets must be clean, or "restored" below would mean
# "handed back somebody else's edit", which is the same confusion the probe
# itself exits 3 for.
_dirty = [p for p in (EP, LIB) if not clean(p)]
if _dirty:
    print('SKIPPED: %s already modified, so this control cannot tell a restore '
          'from a pre-existing edit. Nothing about the guard was verified.'
          % ', '.join(_dirty))
    sys.exit(3)

# Import the probe WITHOUT running it. Its module body runs the whole probe, so
# the import has to stop at the point the guard is defined -- which it does,
# because `--check-residue` exits before the arms. Passing that flag is the
# supported entry point and is used here deliberately rather than exec'ing a
# slice of the file.
spec = importlib.util.spec_from_file_location('delegation_probe', PROBE)
mod = importlib.util.module_from_spec(spec)
_argv = sys.argv[:]
sys.argv = [PROBE, '--check-residue']
try:
    spec.loader.exec_module(mod)
    _import_exit = 0
except SystemExit as e:
    _import_exit = e.code if isinstance(e.code, int) else 0
finally:
    sys.argv = _argv

print('CONTROL -- the residue guard in run_delegation_probe.py\n')

arm('0. --check-residue on a clean tree exits 0 and claims nothing else',
    _import_exit == 0, 'exited %r' % _import_exit)

# ── ARM 1: AN EXCEPTION INSIDE A PLANT STILL RESTORES ──────────────────────
# This is the shape that left api/sd-data.js sabotaged on 2026-10-06: the
# original code ran write(), then tool(), then `git checkout --` in a straight
# line, so anything that raised in between kept the plant.
src = open(os.path.join(REPO, EP), encoding='utf-8').read()
planted_was_seen = False
try:
    with mod.plant(EP, src.replace(', warn_days: gateWarn }', ' }', 1)):
        planted_was_seen = not clean(EP)
        raise RuntimeError('deliberate failure inside the plant')
except RuntimeError:
    pass
arm('1a. the plant really did modify the file (the arm is not vacuous)',
    planted_was_seen)
arm('1b. an EXCEPTION inside the plant still restores the file', clean(EP),
    'api/sd-data.js is still modified after the exception')

# ── ARM 2: THE SENTINEL IS REMOVED ON THE NORMAL PATH ─────────────────────
arm('2. the sentinel is gone after a plant unwinds',
    not os.path.exists(mod.SENTINEL),
    'left behind at ' + os.path.relpath(mod.SENTINEL, REPO))

# ── ARM 3: A SENTINEL LEFT BY A KILLED RUN IS REPORTED, NOT IGNORED ───────
# The kill itself cannot be simulated from inside a process, so what is tested
# is the EVIDENCE a kill leaves: the sentinel, with the paths in it.
with open(mod.SENTINEL, 'w', encoding='utf-8') as fh:
    fh.write(EP + '\n' + LIB + '\n')
rc = subprocess.run([sys.executable, PROBE, '--check-residue'],
                    cwd=REPO, capture_output=True, text=True,
                    encoding='utf-8', errors='replace')
arm('3a. --check-residue EXITS 1 when a sentinel is present',
    rc.returncode == 1, 'exit was %d' % rc.returncode)
arm('3b. ...and NAMES both files rather than just counting them',
    EP in rc.stdout and LIB in rc.stdout, rc.stdout[:160])
arm('3c. ...and prints the command that restores them',
    'git checkout --' in rc.stdout, rc.stdout[:160])
# ── 3d IS THE ARM THAT CAUGHT A DEFECT IN THE FIX ITSELF ──────────────────
# The first version of the guard registered its atexit net at MODULE SCOPE, so
# this very subprocess -- which only ASKS whether a run died -- deleted the
# sentinel on its way out. A second ask would have reported "no sentinel" with
# both files still sabotaged: a detector erasing its own evidence. The net is
# registered on the first real plant now.
arm('3d. ...and does NOT delete the sentinel it just reported',
    os.path.exists(mod.SENTINEL),
    'asking whether a run died removed the evidence that it had')
if os.path.exists(mod.SENTINEL):
    os.remove(mod.SENTINEL)

# ── ARM 4: THE OTHER DIRECTION. With no sentinel it must say so and exit 0.
rc2 = subprocess.run([sys.executable, PROBE, '--check-residue'],
                     cwd=REPO, capture_output=True, text=True,
                     encoding='utf-8', errors='replace')
arm('4. with no sentinel it exits 0 -- the check is not one that always fires',
    rc2.returncode == 0 and 'no sentinel' in rc2.stdout,
    'exit %d: %s' % (rc2.returncode, rc2.stdout[:120]))

# ── ARM 5: ABLATION. Without the guard, the same exception LEAVES the plant.
# Proves the guard is load-bearing rather than decoration, on a throwaway copy
# so nothing in the repo is touched.
tmp = tempfile.mkdtemp(prefix='delegation-ablation-')
try:
    target = os.path.join(tmp, 'sd-data.js')
    shutil.copyfile(os.path.join(REPO, EP), target)
    before = open(target, encoding='utf-8').read()
    try:
        # The PRE-FIX shape: write, then work, then restore -- no finally.
        with open(target, 'w', encoding='utf-8') as fh:
            fh.write(before.replace(', warn_days: gateWarn }', ' }', 1))
        raise RuntimeError('the same deliberate failure, without the guard')
        # (unreachable restore, which is the point)
    except RuntimeError:
        pass
    after = open(target, encoding='utf-8').read()
    arm('5. ABLATION: the same exception WITHOUT the guard leaves the plant',
        after != before,
        'the ablated copy was unchanged, so arm 1b proves nothing')
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print('\n%d passed, %d failed' % (passed, len(failed)))
if failed:
    print('FAILED: %s' % ', '.join(failed))
sys.exit(1 if failed else 0)
