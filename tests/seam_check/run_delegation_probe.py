"""Prove the one-level delegation-following added 2026-09-02 actually works,
propagates, and stops where it says it stops.

WHY THIS EXISTS. Before that change the tool reported CANNOT TELL on
subcontractor-compliance.js's canAssign(), which hands its whole input to
evaluateSubcontractor() and never reads a field itself. That verdict was
accurate and blind, and it was hiding a real unforwarded field: the moment the
tool could see through the delegation it found `warn_days` missing at the call
site. A feature that finds a bug once and is never tested again is a feature
that quietly stops working.

THREE ARMS, because the failure modes are different:
  1. IT SEES  -- plant the real gap (drop warn_days at the canAssign call site)
                 and the tool must name it. Proves the delegated dependency set
                 is live, not decorative.
  2. IT REFUSES -- make the delegate unreadable and the tool must report CANNOT
                 TELL rather than clean. Inheriting a delegate's blindness as a
                 pass would be the vacuous pass this tool exists to refuse --
                 the dnt-location.js lesson, one call deeper.
  3. IT STOPS -- one level means one level. A two-deep chain must NOT resolve.

Restores with targeted `git checkout --`, never a reset, and asserts each
restore actually happened. (A `--hard` on a dirty tree destroyed six edits
during an earlier probe on 2026-09-01; that is why this is the house style.)
"""
# REQUIREMENT: the seam check follows a delegated call exactly one level, names
#   the unforwarded field it finds there, and reports CANNOT TELL rather than
#   clean when the delegate is unreadable -- inheriting a delegate's blindness
#   as a pass is the vacuous pass it exists to refuse
#
import atexit
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EP = 'api/sd-data.js'
LIB = 'api/_lib/subcontractor-compliance.js'

# ── THE RESTORE WAS NOT UNCONDITIONAL AND IT LEFT SABOTAGE IN A LIVE FILE ──
# MEASURED 2026-10-06 (fourth), during a whole-tree run: this probe left
# api/sd-data.js missing `warn_days: gateWarn` at the canAssign call site AND
# api/_lib/subcontractor-compliance.js carrying ARM 2's planted signature --
# which does not parse, because it adds `const input = {...}` above the
# original `input = input || {}`. Attributed by digesting a watch-list after
# every suite, not by reading.
#
# The restore below was `write(...) ... tool() ... git checkout --`, in a
# straight line with no `finally`. Everything between the plant and the
# checkout is exposure: `tool()` raising, an `assert` in a later fixture
# guard, a KeyboardInterrupt, or the runner's per-suite ceiling killing the
# process. Any of those leaves a live API file sabotaged, and the next suites
# in the same run then measure a tree this one broke -- which is exactly what
# happened: tests/seam_check/run_probe.py exits 1 on the sabotaged tree and 0
# on the restored one.
#
# THREE LAYERS, because a `finally` alone does not survive a kill:
#   1. plant() is a context manager -- the checkout runs in a `finally`;
#   2. an atexit net restores anything still dirty on any ordinary exit;
#   3. a SENTINEL file written before the first plant and removed after the
#      last one, so a run that died leaves evidence a later session can find.
#      `--check-residue` reads it and says what to restore.
#
# A SENTINEL IS NOT A FIX AND IS NOT CLAIMED AS ONE. It converts a silent
# corrupted tree into a loud one. The kill itself is not preventable from
# inside the process.
SENTINEL = os.path.join(REPO, '.git', 'seam-delegation-probe.planting')
_PLANTED = []
_NET = [False]      # has the atexit net been registered? See plant.__enter__.


def _restore_all():
    """Last-resort restore. Runs on any ordinary exit, including an exception."""
    for p in list(_PLANTED):
        subprocess.run(['git', 'checkout', '--', p], cwd=REPO, capture_output=True)
    _PLANTED[:] = []
    try:
        if os.path.exists(SENTINEL):
            os.remove(SENTINEL)
    except OSError:
        pass


class plant(object):
    """Write a sabotaged copy of `path`, and restore it whatever happens."""

    def __init__(self, path, text):
        self.path = path
        self.text = text

    def __enter__(self):
        # ── THE NET IS REGISTERED HERE, NOT AT IMPORT, AND THAT IS A FIX ───
        # It was `atexit.register(_restore_all)` at module scope, and the
        # control caught it on its first run: `--check-residue` imports this
        # module, so merely ASKING whether a run died DELETED the sentinel it
        # had just reported. A second ask would have said "no sentinel" while
        # the files were still sabotaged -- a detector erasing its own
        # evidence, which is worse than no detector. Registering on the first
        # real plant means the net exists exactly when there is something to
        # unwind.
        if not _NET[0]:
            atexit.register(_restore_all)
            _NET[0] = True
        with open(SENTINEL, 'a', encoding='utf-8') as fh:
            fh.write(self.path + '\n')
        _PLANTED.append(self.path)
        with open(os.path.join(REPO, self.path), 'w', encoding='utf-8') as fh:
            fh.write(self.text)
        return self

    def __exit__(self, *exc):
        subprocess.run(['git', 'checkout', '--', self.path], cwd=REPO,
                       capture_output=True)
        if self.path in _PLANTED:
            _PLANTED.remove(self.path)
        if not _PLANTED:
            try:
                os.remove(SENTINEL)
            except OSError:
                pass
        return False       # never swallow the exception



def check_residue():
    """-> exit code. Did a previous run die with a plant still on disk?"""
    if not os.path.exists(SENTINEL):
        print('no sentinel: no run of this probe died mid-plant.')
        return 0
    try:
        with open(SENTINEL, encoding='utf-8') as fh:
            paths = sorted(set(l.strip() for l in fh if l.strip()))
    except OSError as e:
        print('COULD NOT READ the sentinel (%s). That is not a clean result.' % e)
        return 2
    print('A RUN OF THIS PROBE DIED WITH A PLANT ON DISK.')
    print('These files may still carry deliberately broken code:')
    for p in paths:
        print('    %s' % p)
    print('Restore them and remove the sentinel:')
    print('    git checkout -- %s' % ' '.join(paths))
    print('    rm %s' % SENTINEL)
    return 1


if '--check-residue' in sys.argv:
    sys.exit(check_residue())


def run(*a):
    return subprocess.run(list(a), cwd=REPO, capture_output=True, text=True, encoding='utf-8', errors='replace')


def tool():
    r = run(sys.executable, 'tools/sairn_seam_check.py')
    return r.returncode, r.stdout


def clean(path):
    return run('git', 'status', '--porcelain', '--', path).stdout.strip() == ''


def write(path, text):
    with open(os.path.join(REPO, path), 'w', encoding='utf-8') as fh:
        fh.write(text)


def read(path):
    with open(os.path.join(REPO, path), encoding='utf-8') as fh:
        return fh.read()


# ── A DIRTY TARGET IS A SKIP, NOT A FAILURE (2026-09-09) ────────────────────
# Was a bare `assert`, which exits 1 and reads as "the seam check is broken"
# when nothing about it has been examined -- the signal defect already fixed in
# check4_probe. It is a precondition: this probe restores the bytes it read at
# its own start, so an already-modified target means it would hand the
# modification back as the original. Exit 3 = SKIPPED, which the runner reports
# apart from both pass and fail.
_dirty = [p for p in (EP, LIB) if not clean(p)]
if _dirty:
    print('SKIPPED: already modified, so the bytes this probe would snapshot as')
    print('"original" are not the original and restoring them would bake the')
    print('modification in. Nothing about the seam check was verified: %s'
          % ', '.join(_dirty))
    sys.exit(3)

base_rc, base_out = tool()


# ── THE BASELINE ANCHOR WAS WRONG IN TWO WAYS, FIXED 2026-10-06 ───────────
# It read `base_out.strip().splitlines()[-1]` and required
# `'0 could-not-tell' in base_tail`. Both halves had stopped meaning what they
# said, and the probe has been exiting 1 on a platform where its own subject
# is fine:
#
#   1. WRONG LINE. tools/sairn_seam_check.py now closes with a three-line
#      explanation ("COULD NOT TELL IS NOT A PASS..."), so the last line is
#      `api/_lib/deadline-endpoint-inputs.test.js.` and the summary sits three
#      lines above it. A tail index is an anchor that moves whenever anybody
#      adds a closing sentence -- discipline 8, instrument drift.
#   2. WRONG PROPERTY. "0 could-not-tell" is a claim about the WHOLE PLATFORM;
#      the sentence printed beside it says "canAssign resolves at baseline".
#      Those are different assertions and the platform figure is 19 today,
#      every one of them a different seam. A probe about canAssign must judge
#      canAssign.
#
# So the summary is found by PATTERN, not by position, and the baseline
# question is asked about the one seam this probe is for. A missing summary is
# a THIRD STATE -- the tool's output shape changed -- not a failing baseline.
_SUMMARY = re.compile(r'^\s*(\d+) clean, (\d+) not-forwarded, (\d+) could-not-tell\s*$')
_sum_lines = [l for l in base_out.splitlines() if _SUMMARY.match(l)]
base_tail = _sum_lines[-1].strip() if _sum_lines else ''
if not _sum_lines:
    print('COULD NOT RUN: tools/sairn_seam_check.py printed no '
          '"N clean, N not-forwarded, N could-not-tell" summary line, so this '
          'probe cannot read its baseline. Its output shape changed; nothing '
          'about the delegation was verified.')
    sys.exit(3)
print('BASELINE exit', base_rc, '|', base_tail)
# canAssign must RESOLVE at baseline -- it must appear, and not in a row this
# tool could not read. Asked about the subject, not about the platform total.
_ca = [l.strip() for l in base_out.splitlines() if 'canAssign' in l]
baseline_resolves = bool(_ca) and not any('CANNOT TELL' in l for l in _ca)
print('  canAssign resolves at baseline:', baseline_resolves,
      '->', (_ca[0][:100] if _ca else 'canAssign appears in NO seam row at all'))

results = {}

# ── ARM 1: the delegated dependency set is live ────────────────────────────
src = read(EP)
# EXACTLY ONCE, NOT MERELY PRESENT (2026-09-10) -- see the note on
# anchor_once() in tests/push_gate/check7_probe.py. `in` catches an anchor that
# has GONE and misses one that has become AMBIGUOUS, and .replace(..., 1) then
# plants in whichever came first. An anchor is a string match against code
# somebody else keeps editing, so going ambiguous is how it ages.
_n = src.count(', warn_days: gateWarn }')
assert _n == 1, ('fixture invalid: the canAssign anchor matches %d places in %s, '
                 'not 1 -- widen it rather than letting replace() pick' % (_n, EP))
with plant(EP, src.replace(', warn_days: gateWarn }', ' }', 1)):
    rc, out = tool()
    named = [l.strip() for l in out.splitlines() if 'warn_days' in l]
    results['arm1_sees'] = (rc == 1 and any('warn_days' in l for l in named)
                            and 'canAssign' in out)
    print('\nARM 1 -- gap behind the delegation, exit', rc)
    for l in named[:3]:
        print('   ', l)
assert clean(EP), 'ARM 1 restore failed'

# ── ARM 2: an unreadable delegate PROPAGATES, it does not pass ─────────────
lib = read(LIB)
_n2 = lib.count('function evaluateSubcontractor(input) {')
assert _n2 == 1, ('fixture invalid: the delegate signature matches %d places in %s, '
                  'not 1 -- moved, or duplicated; either way this arm would be '
                  'planting somewhere nobody chose' % (_n2, LIB))
with plant(LIB, lib.replace('function evaluateSubcontractor(input) {',
                            'function evaluateSubcontractor({ subcontractor, today, warn_days, required }) {\n  const input = { subcontractor, today, warn_days, required };', 1)):
    rc2, out2 = tool()
    ct = [l.strip() for l in out2.splitlines() if 'CANNOT TELL' in l and 'canAssign' in l]
    results['arm2_propagates'] = bool(ct)
    print('\nARM 2 -- delegate made unreadable, exit', rc2)
    for l in ct[:2]:
        print('   ', l)
    if not ct:
        print('    (no CANNOT TELL row mentioning canAssign -- the tool inherited the '
              'delegate\'s blindness as a pass, which is the bug this arm exists for)')
assert clean(LIB), 'ARM 2 restore failed'

# ── ARM 3: one level means one level ───────────────────────────────────────
# Called directly rather than through a planted file: the assertion is about
# the function's bound, and a synthetic source makes that unambiguous.
sys.path.insert(0, os.path.join(REPO, 'tools'))
import importlib.util
spec = importlib.util.spec_from_file_location(
    'seamchk', os.path.join(REPO, 'tools', 'sairn_seam_check.py'))
seamchk = importlib.util.module_from_spec(spec)
spec.loader.exec_module(seamchk)

ONE_DEEP = """
function inner(input) { return input.alpha + input.beta; }
function outer(input) { return inner(input); }
"""
TWO_DEEP = """
function deepest(input) { return input.gamma; }
function middle(input) { return deepest(input); }
function top(input) { return middle(input); }
"""
r1, p1 = seamchk.engine_reads(ONE_DEEP, 'outer')
r2, p2 = seamchk.engine_reads(TWO_DEEP, 'top')
one_level_followed = (r1 == {'alpha', 'beta'} and not p1)
two_levels_refused = (not r2) and bool(p2)
results['arm3_stops'] = one_level_followed and two_levels_refused
print('\nARM 3 -- one level followed:', one_level_followed, '->', sorted(r1), p1 or '')
print('        two levels refused :', two_levels_refused, '->', sorted(r2), (p2 or '')[:90])

post_rc, post_out = tool()
# Same pattern anchor as the baseline, for the same reason: comparing the last
# LINE compares whatever explanation the tool currently closes with, which is
# not what "restored" means.
_post_sum = [l for l in post_out.splitlines() if _SUMMARY.match(l)]
post_tail = _post_sum[-1].strip() if _post_sum else '(no summary line)'
restored_baseline = (post_rc == base_rc and bool(_post_sum) and post_tail == base_tail)

# ── ARM 4: NO PLANTED BYTE SURVIVES THIS PROBE (added 2026-10-06) ──────────
# `restored_baseline` above compares the seam check's own OUTPUT before and
# after, which is a proxy: the tool could report the same tail on a file that
# still differs, and on 2026-10-06 the residue was found by digesting the
# files, not by reading that line. This arm asks git directly, names every
# file it found dirty, and checks the sentinel is gone -- a sentinel left
# behind means a plant was recorded and never unwound even if the working
# tree happens to look clean.
_dirty_now = [p for p in (EP, LIB) if not clean(p)]
results['arm4_no_residue'] = (not _dirty_now) and not os.path.exists(SENTINEL)
print('\nARM 4 -- nothing planted survives this probe:', results['arm4_no_residue'])
if _dirty_now:
    print('    STILL MODIFIED AFTER THE RUN: %s' % ', '.join(_dirty_now))
    print('    These are live API files and one of the plants does not parse.')
    print('    Restore with: git checkout -- %s' % ' '.join(_dirty_now))
if os.path.exists(SENTINEL):
    print('    THE SENTINEL IS STILL PRESENT (%s) -- a plant was recorded and'
          % os.path.relpath(SENTINEL, REPO))
    print('    never unwound. Run --check-residue for what to restore.')

print('\n--- results ---')
for k, v in results.items():
    print('  %-18s %s' % (k, v))
print('  %-18s %s (%s)' % ('restored_baseline', restored_baseline, post_tail))
sys.exit(0 if all(results.values()) and restored_baseline and baseline_resolves else 1)
