# -*- coding: utf-8 -*-
"""ITEM 3 -- re-run each of the suite's FAILing files ALONE, in a FRESH clean
worktree, and classify REAL or CASCADE.

WHY ALONE AND WHY CLEAN. The suite's own footer says it DIRTIED ITS OWN TREE
(5 paths) and that "Results above may be CASCADE, not real: a modified tracked
file fails every clean-tree probe after it." So the suite is self-dirtying: the
generators it runs regenerate documents, and every clean-tree probe AFTER that
point fails for a reason that is not its own. The only way to tell the two
apart is to drive each file by itself against a tree nothing else has touched.

CLASSIFICATION, stated before the run so it cannot drift to fit the answer:
  REAL     exits non-zero ALONE, on a clean tree.
  CASCADE  exits 0 alone -- it failed in the suite only because something
           earlier dirtied the tree.
  TIMEOUT  exceeded the bound alone. NOT folded into either; a third state.
  ERROR    could not be driven at all.

THE TREE IS RESTORED BETWEEN EVERY FILE, because these probes dirty it too --
otherwise this run would manufacture the very cascade it is measuring.
"""
import io
import json
import os
import re
import subprocess
import sys
import time

WT = sys.argv[1]
SUITE_OUT = sys.argv[2]
OUT = sys.argv[3]
BOUND = 240

FAILS = []
for line in io.open(SUITE_OUT, encoding='utf-8', errors='replace'):
    m = re.match(r'^  FAIL (node|py)\s+(\S+)\s*(.*)$', line.rstrip('\n'))
    if m:
        FAILS.append({'kind': m.group(1), 'file': m.group(2),
                      'suite_line': m.group(3).strip()})
print('FAILing files read from the suite output: %d' % len(FAILS), flush=True)


def restore():
    subprocess.run(['git', 'reset', '-q', '--hard', 'HEAD'], cwd=WT,
                   capture_output=True)
    subprocess.run(['git', 'clean', '-qfd'], cwd=WT, capture_output=True)


def first_failing_line(out):
    """The FIRST line that looks like a failure, not the last. A tool's summary
    line names the count; the first failing line names the thing."""
    for ln in out.split('\n'):
        s = ln.strip()
        if not s:
            continue
        if re.match(r'^(FAIL|FAILED|\*\s*FAIL|!\s)', s) or ' FAIL ' in s \
           or s.startswith('  FAIL') or 'ARM(S) FAILED' in s \
           or re.match(r'^\s*(FAIL|NOT PROVEN|REFUSED|DENIED)\b', ln):
            return s[:220]
    for ln in out.split('\n'):
        if 'Traceback (most recent call last)' in ln:
            return 'TRACEBACK: ' + out.split('Traceback', 1)[1][:200].replace('\n', ' | ')
    tail = [l for l in out.strip().split('\n') if l.strip()]
    return (tail[-1].strip()[:220] if tail else '(no output)')


rows = []
for i, f in enumerate(FAILS, 1):
    restore()
    rel = f['file']
    p = os.path.join(WT, rel.replace('/', os.sep))
    if not os.path.isfile(p):
        rows.append(dict(f, code='ABSENT', secs=0.0, verdict='ERROR',
                         first='not on disk in the worktree'))
        print('%3d/%d %-58s ABSENT' % (i, len(FAILS), rel), flush=True)
        continue
    cmd = ([sys.executable, '-u', rel] if f['kind'] == 'py'
           else ['node', rel])
    t0 = time.time()
    try:
        r = subprocess.run(cmd, cwd=WT, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, timeout=BOUND)
        code = r.returncode
        out = r.stdout.decode('utf-8', 'replace')
    except subprocess.TimeoutExpired as e:
        code = 'TIMEOUT'
        out = (e.output or b'').decode('utf-8', 'replace')
    el = round(time.time() - t0, 1)
    if code == 'TIMEOUT':
        verdict = 'TIMEOUT'
    elif code == 0:
        verdict = 'CASCADE'
    else:
        verdict = 'REAL'
    rows.append(dict(f, code=code, secs=el, verdict=verdict,
                     first=first_failing_line(out)))
    print('%3d/%d %-58s %-8s %-8s %6.1fs' % (i, len(FAILS), rel, code,
                                             verdict, el), flush=True)
    io.open(OUT, 'w', encoding='utf-8').write(json.dumps(rows, indent=1))

restore()
io.open(OUT, 'w', encoding='utf-8').write(json.dumps(rows, indent=1))
import collections
c = collections.Counter(r['verdict'] for r in rows)
print('\nREAL %d  CASCADE %d  TIMEOUT %d  ERROR %d   (of %d)'
      % (c['REAL'], c['CASCADE'], c['TIMEOUT'], c['ERROR'], len(rows)))
print('bound was %ds per file, each driven ALONE with the tree restored first'
      % BOUND)
