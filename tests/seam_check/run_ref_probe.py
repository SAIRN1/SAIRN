"""Probe --ref, the flag that stops a background probe from denying a real push.

THE INCIDENT (2026-09-08). tools/run_all_tests.py --hook verifies a suite by
BREAKING the code and watching the suite notice -- it reverts a fix, runs the
suite, restores it. While that is in flight, tracked files on disk are nobody's
code. The push gate shelled out to tools/sairn_seam_check.py with no revision,
so the gate read the tree mid-mutation and DENIED THREE LEGITIMATE PUSHES over
a field called `zz_probe_field` that exists in neither HEAD nor origin. The
seam check was right about the bytes it was handed. The bytes were residue.

Confirmed again while writing this probe: after the runner fleet finished, the
working tree still held `return true; return e.name==='QuotaExceededError'` in
sairnvet.html and an untracked reachability fixture. The residue is real and it
outlives the run that made it, so "just wait for the runner" is not the fix.

FOUR ARMS, because "the gate stopped denying" is not evidence it started
reading the right thing:

  1. THE FALSE DENIAL IS REAL -- a probe-shaped mutation on disk makes the
     working-tree run exit 1. Without this arm, arm 2 could pass because the
     tool sees nothing at all.
  2. --ref HEAD IS BLIND TO IT -- same mutated tree, exit 0, because `git show`
     cannot see a working-tree write.
  3. THE DEFAULT IS STILL THE WORKING TREE -- run by hand, mid-edit, what you
     want checked is what you just typed. --ref is for the gate, not for people.
  4. AN UNREADABLE REVISION EXITS 4, NOT 2 -- exit 2 means "could not tell" and
     the push gate lets a 2 through with a note. A revision the tool cannot read
     has checked nothing, and must not borrow the code that means it merely
     could not parse a seam. Arm 4b asserts the gate denies on that code rather
     than falling off the end of its if-chain, which is how an unknown exit code
     used to be allowed silently.

Run: python tests/seam_check/run_ref_probe.py
"""
import io
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TOOL = os.path.join(REPO, 'tools', 'sairn_seam_check.py')
HOOK = os.path.join(REPO, 'tools', 'sairn_push_gate_hook.py')
LIB = os.path.join(REPO, 'api', '_lib', 'dental-guardian.js')


def run(*extra):
    p = subprocess.run([sys.executable, TOOL] + list(extra),
                       capture_output=True, text=True, cwd=REPO)
    return p.returncode, (p.stdout or '') + (p.stderr or '')


def counts(out):
    m = re.search(r'(\d+) clean, (\d+) not-forwarded, (\d+) could-not-tell', out)
    return m.group(0) if m else '(unreadable)'


results = {}

base_code, base_out = run()
results['baseline_clean'] = base_code == 0
results['baseline_counts'] = counts(base_out)

# The mutation must be committed-clean first, or arm 2 proves nothing: if the
# file already differed from HEAD, --ref would be reading a different program
# for reasons unrelated to the fix.
_st = subprocess.run(['git', 'status', '--porcelain', '--', LIB],
                     capture_output=True, text=True, cwd=REPO)
results['fixture_matches_head'] = (_st.stdout or '').strip() == ''

lib_orig = io.open(LIB, 'rb').read()
try:
    marker = b"  if (!isMinorDob(r.dob)) return null;"
    assert marker in lib_orig, 'probe fixture invalid -- guardianProblem changed shape'
    # Shaped like what the runner actually leaves behind: a field the engine
    # reads and no endpoint forwards, present on disk and in no commit.
    io.open(LIB, 'wb').write(
        lib_orig.replace(marker, b"  if (r.zz_probe_field) return 'probe';\n" + marker, 1))

    # ── ARM 1: the false denial reproduces ────────────────────────────────
    c1, o1 = run()
    results['arm1_worktree_denies'] = (c1 == 1 and 'zz_probe_field' in o1)

    # ── ARM 2: --ref HEAD does not see the mutation ───────────────────────
    c2, o2 = run('--ref', 'HEAD')
    results['arm2_ref_is_blind'] = (c2 == 0 and 'zz_probe_field' not in o2)
    results['arm2_matches_baseline'] = counts(o2) == counts(base_out)
finally:
    io.open(LIB, 'wb').write(lib_orig)

results['source_restored'] = io.open(LIB, 'rb').read() == lib_orig

# ── ARM 3: the default did not move ───────────────────────────────────────
c3, o3 = run()
results['arm3_default_is_worktree'] = (c3 == 0 and counts(o3) == counts(base_out))

# ── ARM 4: an unreadable revision is not a could-not-tell ─────────────────
c4a, o4a = run('--ref', 'zz-no-such-revision')
results['arm4_bad_ref_exits_4'] = c4a == 4
results['arm4_bad_ref_says_why'] = 'zz-no-such-revision' in o4a
c4b, _o4b = run('--ref')
results['arm4_missing_value_exits_4'] = c4b == 4

# ── ARM 4b: the gate denies on a code it does not recognise ───────────────
# Static, deliberately. Driving the whole hook needs a scratch repo and a
# clean tree; what changed here is one branch, and its absence was the bug.
hook_src = io.open(HOOK, encoding='utf-8', errors='replace').read()
results['arm4b_gate_passes_ref'] = "seam, '--ref', tip" in hook_src
results['arm4b_gate_denies_unknown_code'] = 's.returncode not in (0, 1, 2)' in hook_src

print('--- results ---')
bad = 0
for k in sorted(results):
    v = results[k]
    if isinstance(v, bool):
        print('  %-30s %s' % (k, v))
        if not v:
            bad += 1
    else:
        print('  %-30s %s' % (k, v))

print('')
if bad:
    print('%d ARM(S) FAILED' % bad)
else:
    print('ALL ARMS PASS')
sys.exit(1 if bad else 0)
