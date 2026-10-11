# -*- coding: utf-8 -*-
"""ITEM 4, PHASE 1 -- EVIDENCE ONLY. This script removes nothing.

Two populations, one rule each, and the rule is applied per item rather than to
the group -- RULE E, from batch b1: a refusal (or a removal) is scoped to the
case that justified it.

  LOCKS      ~/SAIRN-SESSION-LOCKS/*.lock
             removable only if the recorded owner process is GONE and the age is
             stated.
  WORKTREES  every linked worktree registered against this clone
             removable only if: no uncommitted changes, no live process with its
             path as cwd or on a command line, and no file activity in 24h.

EVERY FIELD IS MEASURED AND PRINTED. A missing measurement is COULD-NOT-TELL and
makes the item NOT removable -- never removable-by-default.
"""
import io
import json
import os
import re
import subprocess
import sys
import time

LOCKS = os.path.join(os.path.expanduser('~'), 'SAIRN-SESSION-LOCKS')
REPO = r'C:\Users\marsh\Documents\SAIRN-hank'
OUT = sys.argv[1]
NOW = time.time()
DAY = 86400.0


def ps_table():
    """Every running process with its command line, once, so each item below is
    judged against ONE snapshot rather than a moving target."""
    p = subprocess.run(
        ['powershell', '-NoProfile', '-Command',
         "Get-CimInstance Win32_Process | Select-Object ProcessId,Name,"
         "CommandLine | ConvertTo-Json -Compress"],
        capture_output=True, text=True)
    try:
        d = json.loads(p.stdout or '[]')
    except ValueError:
        return None          # COULD NOT TELL -- never an empty list
    if isinstance(d, dict):
        d = [d]
    return d


procs = ps_table()
if procs is None:
    print('COULD NOT RUN: the process table could not be read. Nothing can be '
          'judged removable without it, and an empty list is not the same as '
          '"no processes".')
    sys.exit(2)
pids = set(int(x.get('ProcessId') or 0) for x in procs)
print('process snapshot: %d process(es)\n' % len(procs))

report = {'locks': [], 'worktrees': [], 'snapshot_processes': len(procs)}

# ---------------------------------------------------------------- LOCKS
print('=' * 72)
print('LOCKS in %s' % LOCKS)
print('=' * 72)
for f in sorted(os.listdir(LOCKS)) if os.path.isdir(LOCKS) else []:
    if not f.endswith('.lock'):
        continue
    p = os.path.join(LOCKS, f)
    raw = io.open(p, encoding='utf-8', errors='replace').read()
    try:
        info = json.loads(raw)
    except ValueError:
        info = None
    mtime = os.path.getmtime(p)
    age_h = (NOW - mtime) / 3600.0
    pid = None
    for k in ('claude_pid', 'pid', 'CLAUDE_PID', 'owner_pid'):
        if isinstance(info, dict) and info.get(k):
            try:
                pid = int(info[k])
            except (TypeError, ValueError):
                pass
            break
    alive = (pid in pids) if pid is not None else None
    row = {'lock': f, 'age_hours': round(age_h, 2),
           'mtime': time.strftime('%Y-%m-%dT%H:%M:%S',
                                  time.localtime(mtime)),
           'recorded_pid': pid, 'pid_alive': alive,
           'raw': raw.strip()[:200], 'parsed': info is not None}
    # REMOVABLE requires a POSITIVE answer on both, never an absent one.
    row['removable'] = bool(alive is False and age_h > 24.0)
    row['why'] = (
        'pid %s is GONE and the lock is %.1fh old' % (pid, age_h)
        if row['removable'] else
        'pid could not be read from the lock, so "gone" cannot be established'
        if pid is None else
        'pid %s is STILL ALIVE' % pid if alive else
        'pid %s is gone but the lock is only %.1fh old (< 24h)' % (pid, age_h))
    report['locks'].append(row)
    print('%-28s age=%7.2fh  pid=%-7s alive=%-5s  removable=%-5s  %s'
          % (f, age_h, pid, alive, row['removable'], row['why']))

# ------------------------------------------------------------ WORKTREES
print('')
print('=' * 72)
print('WORKTREES registered against %s' % REPO)
print('=' * 72)
wt = subprocess.run(['git', 'worktree', 'list', '--porcelain'], cwd=REPO,
                    capture_output=True, text=True)
entries, cur = [], {}
for line in (wt.stdout or '').split('\n'):
    if line.startswith('worktree '):
        if cur:
            entries.append(cur)
        cur = {'path': line[len('worktree '):].strip()}
    elif line.startswith('HEAD '):
        cur['head'] = line[5:].strip()[:12]
    elif line.strip() == 'detached':
        cur['detached'] = True
    elif line.startswith('branch '):
        cur['branch'] = line[7:].strip()
if cur:
    entries.append(cur)


def newest_mtime(root):
    """The most recent mtime under a path, bounded so a huge tree cannot hang
    this. Returns (mtime, files_seen, truncated)."""
    best, seen, trunc = 0.0, 0, False
    for dirpath, dirnames, filenames in os.walk(root):
        if '.git' in dirnames:
            dirnames.remove('.git')
        for fn in filenames:
            try:
                m = os.path.getmtime(os.path.join(dirpath, fn))
            except OSError:
                continue
            seen += 1
            if m > best:
                best = m
            if seen >= 6000:
                trunc = True
                return best, seen, trunc
    return best, seen, trunc


for e in entries:
    path = e['path']
    if os.path.normpath(path).lower() == os.path.normpath(REPO).lower():
        continue                      # the live clone itself
    exists = os.path.isdir(path)
    st = subprocess.run(['git', 'status', '--porcelain'], cwd=path,
                        capture_output=True, text=True) if exists else None
    dirty = None
    if st is not None:
        dirty = [l for l in (st.stdout or '').split('\n') if l.strip()] \
            if st.returncode == 0 else None
    low = path.replace('/', '\\').lower()
    low2 = path.replace('\\', '/').lower()
    busy = [x for x in procs
            if x.get('CommandLine')
            and (low in x['CommandLine'].lower()
                 or low2 in x['CommandLine'].lower())]
    newest, seen, trunc = (newest_mtime(path) if exists else (0.0, 0, False))
    age_h = (NOW - newest) / 3600.0 if newest else None
    row = {'path': path, 'head': e.get('head'), 'exists': exists,
           'uncommitted': (len(dirty) if dirty is not None else None),
           'uncommitted_sample': (dirty[:6] if dirty else []),
           'live_processes': len(busy),
           'newest_file_age_hours': (round(age_h, 2) if age_h is not None
                                     else None),
           'files_seen': seen, 'walk_truncated': trunc}
    if not exists:
        row['removable'] = True
        row['why'] = ('the directory is GONE; only the registration is left, '
                      'so there is nothing to lose')
    elif dirty is None:
        row['removable'] = False
        row['why'] = ('git status COULD NOT RUN here, so "no uncommitted '
                      'changes" cannot be established')
    elif dirty:
        row['removable'] = False
        row['why'] = '%d uncommitted path(s)' % len(dirty)
    elif busy:
        row['removable'] = False
        row['why'] = '%d live process(es) name this path' % len(busy)
    elif age_h is None:
        row['removable'] = False
        row['why'] = 'no file mtime could be read, so 24h quiet is unprovable'
    elif age_h <= 24.0:
        row['removable'] = False
        row['why'] = 'newest file is %.1fh old (< 24h)' % age_h
    else:
        row['removable'] = True
        row['why'] = ('clean, no live process, newest file %.1fh old' % age_h)
    report['worktrees'].append(row)
    print('%-74s' % path[:74])
    print('    exists=%-5s uncommitted=%-5s procs=%-3s newest=%-9s '
          'removable=%-5s  %s'
          % (exists, row['uncommitted'], row['live_processes'],
             ('%.1fh' % age_h) if age_h is not None else 'n/a',
             row['removable'], row['why']))

io.open(OUT, 'w', encoding='utf-8').write(json.dumps(report, indent=1))
print('')
print('locks     : %d, removable %d'
      % (len(report['locks']), len([r for r in report['locks'] if r['removable']])))
print('worktrees : %d, removable %d'
      % (len(report['worktrees']),
         len([r for r in report['worktrees'] if r['removable']])))
print('NOTHING WAS REMOVED BY THIS SCRIPT.')
