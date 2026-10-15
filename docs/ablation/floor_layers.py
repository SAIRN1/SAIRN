"""Ablation record for cc b12's three test-file-floor layers.

THE ARMS LIVE IN cody's tests/run_all_tests_floor_probe.py, which cc does not
write. So the ablation is driven from outside: remove ONE layer from
tools/run_all_tests.py, run cody's probe as a subprocess, record whether it
goes red, restore, and confirm it goes green again.

RESTORE IS IN A finally AND VERIFIED BY HASH. A script that edits a tracked
tool and dies halfway leaves the repo subtly wrong, which is worse than having
no ablation record.
"""
import hashlib
import io
import os
import subprocess
import sys

REPO = r'C:\Users\marsh\Documents\SAIRN-cc'
TOOL = os.path.join(REPO, 'tools', 'run_all_tests.py')
PROBE = os.path.join('tests', 'run_all_tests_floor_probe.py')
# ── THE FLOOR FILE IS SNAPSHOTTED TOO, AND THAT IS NOT TIDINESS ───────────
# The first two runs of this harness removed the tracked-intersection layer,
# the ratchet then counted the floor probe's five UNTRACKED fixture files, and
# it wrote a floor of 812 and then 813 against a real 808 -- the
# 807-against-802 incident of b12 reproducing on demand, which is the finding.
# But the harness restored only the TOOL and left the FLOOR FILE poisoned, so
# cody's probe failed on the NEXT run for a reason that had nothing to do with
# the code under test, and the third layer's verdict changed between runs.
# AN ABLATION THAT LEAVES ITS SUBJECT'S STATE BEHIND HAS CONTAMINATED EVERY
# MEASUREMENT AFTER IT.
FLOOR = os.path.join(REPO, 'docs', 'test-file-floor.json')

# Each layer: a name, what it is, and a (find, replace) that REMOVES it.
LAYERS = [
    ('ratchet',
     'the floor is read from docs/test-file-floor.json and ratchets upward, '
     'instead of being a hand-maintained literal that sat at 370 against a '
     'real 802',
     "MIN_TEST_FILES = _read_floor()[0]",
     "MIN_TEST_FILES = _MIN_TEST_FILES_FLOOR"),
    ('tracked-intersection',
     'the ratchet rises only as far as the DISCOVERED list intersected with '
     '`git ls-files`, so an untracked probe fixture cannot push the floor '
     'above the tree',
     "    count = min(count, tracked)",
     "    count = count"),
    ('silence-breaking',
     '`behind` is part of the hook\'s early-return condition, so a clean tree '
     'whose floor has gone stale still produces output',
     "    if not failures and not skipped and not retried and not shrunk \\\n"
     "            and not behind:",
     "    if not failures and not skipped and not retried and not shrunk:"),
]


def run_probe():
    p = subprocess.run([sys.executable, PROBE], cwd=REPO,
                       capture_output=True, text=True,
                       encoding='utf-8', errors='replace', timeout=900)
    tail = (p.stdout or '') + (p.stderr or '')
    last = [l for l in tail.splitlines() if l.strip()][-1:] or ['(no output)']
    return p.returncode, last[0][:140]


def main():
    bad_restore = False
    original = io.open(TOOL, encoding='utf-8', newline='').read()
    floor0 = io.open(FLOOR, encoding='utf-8', newline='').read()
    h0 = hashlib.sha256(original.encode('utf-8')).hexdigest()
    print('tools/run_all_tests.py sha256 before: %s' % h0[:16])
    print('')
    rc, line = run_probe()
    print('BASELINE  cody probe exit %d -- %s' % (rc, line))
    if rc != 0:
        print('ABLATION NOT RUN -- the baseline is not green, so nothing below')
        print('could be attributed to the removed layer.')
        return 2
    print('')
    naked = []
    try:
        for name, what, find, repl in LAYERS:
            if original.count(find) != 1:
                print('%-22s COULD NOT ABLATE -- the anchor matched %d times, '
                      'not 1. Reported rather than guessed.'
                      % (name, original.count(find)))
                naked.append(name + ' (unablatable)')
                continue
            io.open(TOOL, 'w', encoding='utf-8', newline='\n').write(
                original.replace(find, repl))
            arc, aline = run_probe()
            io.open(TOOL, 'w', encoding='utf-8', newline='\n').write(original)
            # RESTORED PER LAYER, not once at the end: a layer that moves the
            # floor would otherwise contaminate every layer measured after it.
            io.open(FLOOR, 'w', encoding='utf-8', newline='\n').write(floor0)
            verdict = 'FAILS (load-bearing)' if arc != 0 else \
                      'STILL GREEN -- UNPROVEN'
            if arc == 0:
                naked.append(name)
            print('%-22s probe exit %d  %s' % (name, arc, verdict))
            print('    %s' % what)
            print('    %s' % aline)
    finally:
        io.open(TOOL, 'w', encoding='utf-8', newline='\n').write(original)
        io.open(FLOOR, 'w', encoding='utf-8', newline='\n').write(floor0)
        h1 = hashlib.sha256(
            io.open(TOOL, encoding='utf-8', newline='').read().encode('utf-8')
        ).hexdigest()
        print('')
        print('RESTORED  sha256 after: %s  %s'
              % (h1[:16], 'IDENTICAL' if h1 == h0 else 'MISMATCH -- CHECK IT'))
        bad_restore = h1 != h0
    if bad_restore:
        return 2
    rc2, line2 = run_probe()
    print('AFTER RESTORE  cody probe exit %d -- %s' % (rc2, line2))
    if rc2 != 0:
        return 2
    print('')
    if naked:
        print('%d LAYER(S) UNPROVEN: %s' % (len(naked), ', '.join(naked)))
        return 1
    print('every layer is load-bearing against cody\'s arms.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
