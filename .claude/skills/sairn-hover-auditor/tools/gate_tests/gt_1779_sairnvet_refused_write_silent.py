#!/usr/bin/env python
"""gate test for H1 finding #1779 (b107). The CLAIM it asserts, so that exit 0 means the claim held and the
finding SURVIVES the kill attempt: in sairnvet.html svPushOne(), a controlled-register write that the server
refuses AFTER a witness token was granted produces NO on-screen notice -- the only showToast in the function
sits inside the branch that tests r===null together with witnessWhy (set only when the TOKEN REQUEST failed),
and the generic r===null branch only calls refused(), which console.warns.

Exit 0 = the claim holds (finding survives). Exit 1 = it does not (killed: a toast reaches the refused-write
path). Exit 2 = could not run (file or function missing). It READS the file as data and executes none of it.

usage: python gt_1779_sairnvet_refused_write_silent.py REV [PATH_OVERRIDE]
  REV           a git rev in the SAIRN-hover clone; the file is read with `git show REV:sairnvet.html`
  PATH_OVERRIDE a file to read instead (used by the control that plants a toast in the wrong branch)
"""
import os
import re
import subprocess
import sys

REPO = os.path.expanduser('~/Documents/SAIRN-hover')


def load(rev, override):
    if override:
        return open(override, encoding='utf-8', errors='replace').read()
    r = subprocess.run(['git', '-C', REPO, 'show', '%s:sairnvet.html' % rev], capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    if r.returncode != 0:
        print('COULD NOT RUN: git show %s:sairnvet.html failed: %s' % (rev, r.stderr.strip()[:100]))
        sys.exit(2)
    return r.stdout


def main(argv):
    if not argv:
        print('COULD NOT RUN: no rev given')
        return 2
    src = load(argv[0], argv[1] if len(argv) > 1 else None)
    a = src.find('function svPushOne(')
    if a < 0:
        print('COULD NOT RUN: svPushOne not found')
        return 2
    m = re.search(r'\n(?:async\s+)?function\s+\w+\s*\(', src[a + 10:])
    fn = src[a:a + 10 + (m.start() if m else len(src))]
    toasts = [x.start() for x in re.finditer(r'showToast\s*\(', fn)]
    gate = re.search(r'if\s*\(\s*r\s*===\s*null\s*&&\s*witnessWhy\s*\)\s*\{', fn)
    generic = re.search(r'if\s*\(\s*r\s*===\s*null\s*\)\s*return\s+refused\(', fn)
    print('svPushOne: %d showToast call(s); witnessWhy branch %s; generic refused branch %s'
          % (len(toasts), 'found' if gate else 'MISSING', 'found' if generic else 'MISSING'))
    if not gate or not generic:
        print('COULD NOT RUN: the branches this claim is about are not in the function shape expected')
        return 2
    # the end of the witnessWhy block is the first 'return refused(' after it
    end_gate = fn.find('return refused(', gate.end())
    in_gate = [t for t in toasts if gate.end() <= t <= end_gate]
    outside = [t for t in toasts if t not in in_gate]
    # is any toast reachable on the generic refused-write path? Anything between the generic test and its return.
    generic_toast = [t for t in toasts if generic.start() <= t <= generic.end() + 80]
    print('toasts inside the witnessWhy branch: %d; toasts elsewhere in the function: %d; toast on the generic '
          'refused-write branch: %d' % (len(in_gate), len(outside), len(generic_toast)))
    if generic_toast or outside:
        print('CLAIM DOES NOT HOLD: a toast can reach the refused-write path')
        return 1
    print('CLAIM HOLDS: the only toast is inside the witnessWhy branch; the generic refused-write branch only '
          'calls refused(), which console.warns')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
