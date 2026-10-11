# -*- coding: utf-8 -*-
"""WHICH TOOL SETS core.bare = true?

cody's batch-24 claim says "The WRITER of core.bare is still unidentified."
My item-6 bare sweep REPRODUCED it in the live clone, which bounds the window
to those 62 programs run in that order. This finds the one.

A THROWAWAY CLONE, NOT A WORKTREE, and the distinction is the whole point: a
linked worktree SHARES the common .git/config, so a tool that corrupts it
corrupts the real clone too. That is how the live clone got hit in the first
place.

Runs each of the 62 in order, reads `core.bare` after each, and STOPS at the
first one that flips it to true -- naming it, and leaving the clone in place so
the flip can be re-driven by hand.
"""
import io
import json
import os
import subprocess
import sys

SRC = r'C:\Users\marsh\Documents\SAIRN-hank'
CLONE = sys.argv[1]
ORDER = sys.argv[2]


def git(args, cwd):
    return subprocess.run(['git'] + args, cwd=cwd, capture_output=True,
                          text=True)


def bare_of(cwd):
    p = git(['config', '--get', 'core.bare'], cwd)
    return (p.stdout or '').strip()


if not os.path.isdir(CLONE):
    r = subprocess.run(['git', 'clone', '--no-hardlinks', '-q', SRC, CLONE],
                       capture_output=True, text=True)
    print('clone exit=%d %s' % (r.returncode, (r.stderr or '')[:200]), flush=True)

start = bare_of(CLONE)
print('core.bare at the start of the clone: %r' % start, flush=True)
if start != 'false':
    print('THE CLONE DID NOT START AT false -- stopping, this cannot measure '
          'anything.')
    sys.exit(2)

names = [x['tool'] for x in json.load(io.open(ORDER, encoding='utf-8'))]
print('driving %d program(s) in the recorded order\n' % len(names), flush=True)

for n in names:
    p = os.path.join(CLONE, 'tools', n)
    if not os.path.isfile(p):
        print('%-40s ABSENT' % n, flush=True)
        continue
    try:
        r = subprocess.run([sys.executable, '-u', os.path.join('tools', n)],
                           cwd=CLONE, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, timeout=180)
        code = r.returncode
    except subprocess.TimeoutExpired:
        code = 'TIMEOUT180'
    now = bare_of(CLONE)
    flag = '' if now == 'false' else '   <<<< core.bare = %r' % now
    print('%-40s exit=%-10s bare=%-6s%s' % (n, code, now, flag), flush=True)
    if now != 'false':
        print('\nFOUND IT: tools/%s flipped core.bare to %r.' % (n, now))
        print('The clone is left at %s so the flip can be re-driven by hand.'
              % CLONE)
        sys.exit(1)

print('\nNOT REPRODUCED in this clone across all %d. That is a finding of its '
      'own and NOT an all-clear: the live-clone flip really happened, so\n'
      'something about THIS environment differs -- a linked worktree present,\n'
      'an env var, or a tool that only writes under a condition not met here.'
      % len(names))
