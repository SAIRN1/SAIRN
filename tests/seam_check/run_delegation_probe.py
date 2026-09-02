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
import os
import re
import subprocess
import sys

REPO = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True).stdout.strip()
EP = 'api/sd-data.js'
LIB = 'api/_lib/subcontractor-compliance.js'


def run(*a):
    return subprocess.run(list(a), cwd=REPO, capture_output=True, text=True)


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


for p in (EP, LIB):
    assert clean(p), '%s must be unmodified before the probe' % p

base_rc, base_out = tool()
base_tail = base_out.strip().splitlines()[-1]
print('BASELINE exit', base_rc, '|', base_tail)
baseline_resolves = 'could-not-tell' in base_tail and '0 could-not-tell' in base_tail
print('  canAssign resolves at baseline (0 could-not-tell):', baseline_resolves)

results = {}

# ── ARM 1: the delegated dependency set is live ────────────────────────────
src = read(EP)
assert 'warn_days: gateWarn' in src, \
    'fixture invalid: the canAssign call site does not forward warn_days today'
write(EP, src.replace(', warn_days: gateWarn }', ' }', 1))
rc, out = tool()
named = [l.strip() for l in out.splitlines() if 'warn_days' in l]
results['arm1_sees'] = (rc == 1 and any('warn_days' in l for l in named)
                        and 'canAssign' in out)
print('\nARM 1 -- gap behind the delegation, exit', rc)
for l in named[:3]:
    print('   ', l)
run('git', 'checkout', '--', EP)
assert clean(EP), 'ARM 1 restore failed'

# ── ARM 2: an unreadable delegate PROPAGATES, it does not pass ─────────────
lib = read(LIB)
assert 'function evaluateSubcontractor(input) {' in lib, 'fixture invalid: delegate signature moved'
write(LIB, lib.replace('function evaluateSubcontractor(input) {',
                       'function evaluateSubcontractor({ subcontractor, today, warn_days, required }) {\n  const input = { subcontractor, today, warn_days, required };', 1))
rc2, out2 = tool()
ct = [l.strip() for l in out2.splitlines() if 'CANNOT TELL' in l and 'canAssign' in l]
results['arm2_propagates'] = bool(ct)
print('\nARM 2 -- delegate made unreadable, exit', rc2)
for l in ct[:2]:
    print('   ', l)
if not ct:
    print('    (no CANNOT TELL row mentioning canAssign -- the tool inherited the '
          'delegate\'s blindness as a pass, which is the bug this arm exists for)')
run('git', 'checkout', '--', LIB)
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
post_tail = post_out.strip().splitlines()[-1]
restored_baseline = (post_rc == base_rc and post_tail == base_tail)

print('\n--- results ---')
for k, v in results.items():
    print('  %-18s %s' % (k, v))
print('  %-18s %s (%s)' % ('restored_baseline', restored_baseline, post_tail))
sys.exit(0 if all(results.values()) and restored_baseline and baseline_resolves else 1)
