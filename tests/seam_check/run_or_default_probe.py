"""Probe the or-default alias form the seam check learned on 2026-09-04.

    const r = record || {};   ... r.dob, r.guardian

api/_lib/dental-guardian.js is written that way, and the tool reported
CANNOT TELL on it the moment that file landed -- a standing note on every push,
which is the noise class that gets scrolled past until a real finding hides in
it.

THREE ARMS, because "it stopped saying CANNOT TELL" is not on its own evidence
that it started saying something TRUE:

  1. the real seam is now READ, and reports the inputs it actually depends on
  2. a planted not-forwarded input through that same alias is CAUGHT -- proving
     the change made the tool see, not merely fall silent
  3. the tree is restored and the baseline is unchanged

Run: python tests/seam_check/run_or_default_probe.py
"""
import io
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TOOL = os.path.join(REPO, 'tools', 'sairn_seam_check.py')
LIB = os.path.join(REPO, 'api', '_lib', 'dental-guardian.js')
EP = os.path.join(REPO, 'api', 'sairndental', 'public-book.js')


def run():
    p = subprocess.run([sys.executable, TOOL], capture_output=True, text=True, cwd=REPO)
    return p.returncode, (p.stdout or '') + (p.stderr or '')


def line_for(out, needle):
    for ln in out.splitlines():
        if needle in ln:
            return ln.strip()
    return ''


results = {}

# ── ARM 1: the seam is read at all ────────────────────────────────────────
code, out = run()
seam = line_for(out, 'dental-guardian.js')
results['arm1_seam_is_read'] = seam.startswith('OK') and 'inputs' in seam
results['arm1_no_could_not_tell'] = 'could-not-tell' in out and re.search(r'0 could-not-tell', out) is not None
baseline = re.search(r'(\d+) clean, (\d+) not-forwarded, (\d+) could-not-tell', out)
results['arm1_line'] = seam

# ── ARM 2: a planted defect through that alias is CAUGHT ──────────────────
# guardianProblem reads r.dob through the or-default alias. Teach it to read a
# second field the endpoint does not forward; the tool must now say so.
lib_orig = io.open(LIB, 'rb').read()
ep_orig = io.open(EP, 'rb').read()
try:
    marker = b"  if (!isMinorDob(r.dob)) return null;"
    assert marker in lib_orig, 'probe fixture invalid -- guardianProblem changed shape'
    planted = lib_orig.replace(
        marker,
        b"  if (r.zz_probe_field) return 'probe';\n" + marker, 1)
    io.open(LIB, 'wb').write(planted)
    code2, out2 = run()
    seam2 = line_for(out2, 'dental-guardian.js')
    results['arm2_planted_is_caught'] = ('NOT FORWARDED' in out2 and 'zz_probe_field' in out2)
    results['arm2_exit_nonzero'] = code2 != 0
finally:
    io.open(LIB, 'wb').write(lib_orig)
    io.open(EP, 'wb').write(ep_orig)

# ── ARM 3: restored, and the baseline is what it was ──────────────────────
code3, out3 = run()
after = re.search(r'(\d+) clean, (\d+) not-forwarded, (\d+) could-not-tell', out3)
results['arm3_restored_clean'] = (baseline is not None and after is not None
                                  and baseline.groups() == after.groups())
results['arm3_exit_zero'] = code3 == 0
results['arm3_counts'] = after.group(0) if after else '(unreadable)'
results['sources_restored'] = (io.open(LIB, 'rb').read() == lib_orig
                               and io.open(EP, 'rb').read() == ep_orig)

print('--- results ---')
bad = 0
for k in sorted(results):
    v = results[k]
    if isinstance(v, bool):
        print('  %-26s %s' % (k, v))
        if not v:
            bad += 1
    else:
        print('  %-26s %s' % (k, v))
print('\n%s' % ('ALL ARMS PASS' if not bad else '%d ARM(S) FAILED' % bad))
sys.exit(1 if bad else 0)
