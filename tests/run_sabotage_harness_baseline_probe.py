"""THE CONTROL ON THE HARNESS ITSELF: a red baseline must be COULD NOT RUN, and
must never be reported with the same exit code as a mutation that was missed.

    python tests/run_sabotage_harness_baseline_probe.py

── THE INCIDENT THIS EXISTS FOR (2026-09-29) ───────────────────────────────
tests/run_self_exclusion_guard_sabotage_probe.py was RED AT ITS OWN BASELINE.
Its subject suite failed before anything was planted, so every mutation below it
was measured against an already-broken suite and meant nothing. The harness
noticed, printed "The baseline is red, so no mutation below would mean anything.
Stopping." -- and then RETURNED 1.

**1 IS THE CODE FOR "A PLANTED DEFECT WAS NOT REFUSED".** So a run that verified
nothing and a run that found a real hole in the subject are indistinguishable to
anything reading the exit code, which is every gate, every script and every
session that checks `rc != 0` without reading the output. "Could not run" is a
THIRD STATE and folding it into a finding is the same defect as folding it into a
pass -- PR 1.11, in the direction people forget.

THE HARNESS IS OTHERWISE RIGHT AND THAT IS THE POINT. It already refuses to plant
anything on a red baseline; the gate exists and works. What was wrong was the one
number it answered with.

── WHAT THIS DRIVES, AND WHY IT NEEDS A FIXTURE ────────────────────────────
sabotage_harness builds a git worktree at HEAD and copies the subject suite into
it, so the subject must be a TRACKED file. tests/fixtures/baseline_gate_fixture.py
exists for that and nothing else: green by default, red on demand via an
environment variable, with one mutable anchor so the harness's own
planted-defect-was-refused verdict is meaningful on it.

BOTH DIRECTIONS, because one alone proves nothing:
  * GREEN baseline  -> the harness runs normally and reports 0
  * RED baseline    -> COULD NOT RUN, and NOT the missed-mutation code
"""
import io
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tests'))

HARNESS = os.path.join(REPO, 'tests', 'sabotage_harness.py')
FIXTURE_REL = os.path.join('tests', 'fixtures', 'baseline_gate_fixture.py')
DRIVER_REL = os.path.join('tests', 'fixtures', '_baseline_gate_driver.py')

EXIT_CLEAN = 0
EXIT_FINDING = 1
EXIT_COULD_NOT_RUN = 2

passed = failed = 0


def check(name, cond, detail=''):
    global passed, failed
    print(('  ok   ' if cond else '  FAIL ') + name)
    if not cond:
        failed += 1
        if detail:
            print('         ' + str(detail).replace('\n', '\n         ')[:600])
    else:
        passed += 1


print('the sabotage harness: a RED BASELINE is COULD NOT RUN, not a finding\n')

for p in (HARNESS, os.path.join(REPO, FIXTURE_REL)):
    if not os.path.isfile(p):
        print('COULD NOT RUN: %s is missing. Nothing below was checked, and this '
              'is not a pass.' % p)
        sys.exit(EXIT_COULD_NOT_RUN)

# ── THE DRIVER IS WRITTEN, RUN AND REMOVED ──────────────────────────────────
# run_probe() prints and returns; it is not importable-and-callable twice in one
# process without its worktree bookkeeping colliding, so each colour gets its own
# subprocess. The driver is a tracked-path temp file because the harness resolves
# paths relative to the repository.
DRIVER = (
    "import os, sys\n"
    "sys.path.insert(0, os.path.join(%r, 'tests'))\n"
    "from sabotage_harness import run_probe\n"
    "MUTATIONS = [(%r, 'ANCHOR = ', 'ANCHOR_REMOVED_BY_THE_CONTROL = ')]\n"
    "sys.exit(run_probe(%r, MUTATIONS, title='harness baseline fixture'))\n"
    % (REPO, FIXTURE_REL.replace('\\', '/'), FIXTURE_REL.replace('\\', '/')))

driver_abs = os.path.join(REPO, DRIVER_REL)
io.open(driver_abs, 'w', encoding='utf-8', newline='\n').write(DRIVER)


def drive(red):
    env = dict(os.environ, PYTHONIOENCODING='utf-8')
    if red:
        env['SAIRN_HARNESS_FIXTURE_RED'] = '1'
    else:
        env.pop('SAIRN_HARNESS_FIXTURE_RED', None)
    r = subprocess.run([sys.executable, driver_abs], cwd=REPO, env=env,
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace')
    return r.returncode, (r.stdout or '') + (r.stderr or '')


try:
    # ── 1. THE GREEN DIRECTION, FIRST, OR THE RED ARM PROVES NOTHING ────────
    # If the harness cannot get a clean run out of this fixture at all, then a
    # COULD-NOT-RUN on the red arm is not evidence about the baseline gate -- it
    # is evidence the fixture is broken.
    rc_green, out_green = drive(red=False)
    check('1. GREEN baseline: the harness runs the fixture, plants its mutation '
          'and reports CLEAN (exit %d)' % rc_green,
          rc_green == EXIT_CLEAN, out_green[-700:])
    check('1b. ...and it really did reach the baseline arm, so arm 2 is comparing '
          'two runs of the same thing',
          'before anything is planted' in out_green, out_green[-400:])

    # ── 2. THE DEFECT ───────────────────────────────────────────────────────
    rc_red, out_red = drive(red=True)
    check('2. RED baseline: the harness STOPS and says so',
          'baseline is red' in out_red, out_red[-500:])
    check('2b. THE DEFECT: a red baseline exits COULD NOT RUN (%d), NOT the '
          'missed-mutation code (%d). Got %d'
          % (EXIT_COULD_NOT_RUN, EXIT_FINDING, rc_red),
          rc_red == EXIT_COULD_NOT_RUN,
          'A red baseline answering %d is indistinguishable from "a planted '
          'defect was not refused" to every caller that reads only the exit '
          'code.\n' % rc_red + out_red[-500:])
    check('2c. ...and it reports NO caught/missed verdict about the subject, '
          'because it never planted anything',
          not re.search(r'\bCAUGHT\b|\bMISSED\b|was REFUSED|were refused',
                        out_red),
          out_red[-500:])

    # ── 3. THE TWO CODES ARE NOT THE SAME CODE ──────────────────────────────
    # Stated as its own arm rather than left implied by arms 1 and 2: if a later
    # edit made CLEAN and COULD-NOT-RUN equal, both arms above could still pass
    # while the distinction this file exists for was gone.
    check('3. CLEAN and COULD NOT RUN are different codes (%d vs %d)'
          % (rc_green, rc_red), rc_green != rc_red,
          'the harness answers the same number for "verified" and "could not '
          'verify"')
finally:
    try:
        os.remove(driver_abs)
    except OSError:
        pass
    check('4. this run left nothing behind -- the driver it wrote is gone',
          not os.path.isfile(driver_abs), driver_abs)

print('\n%d passed, %d failed' % (passed, failed))
sys.exit(EXIT_FINDING if failed else EXIT_CLEAN)
