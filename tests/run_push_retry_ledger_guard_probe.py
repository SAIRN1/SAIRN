#!/usr/bin/env python
# REQUIREMENT: tools/push_retry.py must REFUSE to push when a rebase it performed
#   shrank an append-only ledger -- a Tier A review obligation was written,
#   committed, and then silently deleted by a fetch/rebase/push loop resolving a
#   conflict with `--ours`, which during a rebase takes the UPSTREAM side
#
# Run: python tests/run_push_retry_ledger_guard_probe.py
#
# ── WHY COUNTS AND NOT EQUALITY ───────────────────────────────────────────
# Five clones push to one branch, so a ledger GROWING across a rebase is the
# normal case -- another session appended. Requiring the counts to match would
# refuse every ordinary push and the guard would be switched off within a day.
# Only a FALL is a finding.
#
# ── WHY A FILE THAT CANNOT BE READ IS OMITTED, NOT ZERO ───────────────────
# Recording an unreadable ledger as 0 would make it look like a catastrophic
# drop on the next comparison, and would make a REAL drop indistinguishable
# from a parse error. It is left out of the comparison and reported separately,
# so "not watched" never reads as "watched and fine".

import io
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, 'tools'))

import push_retry as P  # noqa: E402

PASS, FAIL = [], []


def check(name, cond, detail=''):
    (PASS if cond else FAIL).append(name)
    print(('  ok   ' if cond else '  FAIL ') + name
          + (('\n       ' + detail) if not cond and detail else ''))


def section(t):
    print('\n' + t)


print('push_retry ledger guard -- a rebase must not silently eat a record\n')

section('A. accumulated_losses() -- the decision, on fixtures')
check('A1. a ledger that SHRANK is reported',
      P.accumulated_losses({'a.json': 10}, {'a.json': 9}) == [('a.json', 10, 9)])
check('A2. a ledger that GREW is NOT reported -- another clone appending is '
      'the normal case', P.accumulated_losses({'a.json': 10}, {'a.json': 12}) == [])
check('A3. an unchanged ledger is not reported',
      P.accumulated_losses({'a.json': 10}, {'a.json': 10}) == [])
check('A4. a ledger absent from AFTER is not guessed at -- it is simply not '
      'compared', P.accumulated_losses({'a.json': 10}, {}) == [])
check('A5. several losses are all reported, not just the first',
      len(P.accumulated_losses({'a': 5, 'b': 5, 'c': 5}, {'a': 4, 'b': 5, 'c': 1})) == 2)
check('A6. THE REAL CASE: one record gone out of 229, which is what the '
      'incident looked like',
      P.accumulated_losses({'docs/tier-a-reviews.json': 229},
                           {'docs/tier-a-reviews.json': 228})
      == [('docs/tier-a-reviews.json', 229, 228)])

section('B. accumulated_counts() against real files')
counts, unreadable = P.accumulated_counts()
print('   watching %d ledger(s); %d unreadable' % (len(counts), len(unreadable)))
check('B1. the watch list resolves to real files in this clone',
      len(counts) >= 5, 'only %d resolved: %r' % (len(counts), sorted(counts)))
check('B2. the ledger the incident happened to is watched',
      'docs/tier-a-reviews.json' in counts,
      'watched: %r' % sorted(counts))
check('B3. the defect register is watched', 'docs/defect-density-register.json' in counts)
check('B4. this session\'s own claim file is watched',
      '.claude/claims/fourth.json' in counts)
check('B5. every count is a positive integer -- a 0 here would mean the key '
      'was found but empty, which no live ledger is',
      all(isinstance(v, int) and v > 0 for v in counts.values()),
      repr(counts))

section('C. the unreadable path is a THIRD STATE, not a zero')
tmp = tempfile.mkdtemp(prefix='ledgerguard-')
try:
    # Point the module at a throwaway repo holding one broken and one good
    # ledger, and confirm the broken one is omitted rather than counted as 0.
    real_repo, real_acc = P.REPO, P.ACCUMULATED
    os.makedirs(os.path.join(tmp, 'docs'))
    io.open(os.path.join(tmp, 'docs', 'good.json'), 'w', encoding='utf-8').write(
        json.dumps({'records': [1, 2, 3]}))
    io.open(os.path.join(tmp, 'docs', 'broken.json'), 'w', encoding='utf-8').write(
        '{ this is not json')
    io.open(os.path.join(tmp, 'docs', 'wrongshape.json'), 'w', encoding='utf-8').write(
        json.dumps({'records': 'not-a-list'}))
    P.REPO = tmp
    P.ACCUMULATED = [('docs/good.json', 'records'),
                     ('docs/broken.json', 'records'),
                     ('docs/wrongshape.json', 'records'),
                     ('docs/absent.json', 'records')]
    c, u = P.accumulated_counts()
    check('C1. the readable ledger is counted', c.get('docs/good.json') == 3, repr(c))
    check('C2. UNPARSEABLE is reported, and is NOT counted as 0',
          'docs/good.json' in c and 'docs/broken.json' not in c
          and any('broken.json' in x for x in u), 'counts=%r unreadable=%r' % (c, u))
    check('C3. a key holding a NON-LIST is reported, not counted',
          'docs/wrongshape.json' not in c
          and any('wrongshape.json' in x for x in u), repr(u))
    check('C4. a file that simply does not exist is silent -- absent is not '
          'an error', not any('absent.json' in x for x in u), repr(u))
    check('C5. CONTROL: an unreadable ledger cannot produce a false LOSS, '
          'because it never enters either side of the comparison',
          P.accumulated_losses(c, c) == [])
finally:
    P.REPO, P.ACCUMULATED = real_repo, real_acc
    shutil.rmtree(tmp, ignore_errors=True)

section('D. the watch list is honest about itself')
missing = [rel for rel, _k in P.ACCUMULATED
           if not os.path.isfile(os.path.join(REPO, rel))]
print('   %d of %d entries have no file in this clone: %s'
      % (len(missing), len(P.ACCUMULATED), ', '.join(missing) or 'none'))
check('D1. the list is not mostly dead names -- a watch list of paths that do '
      'not exist is a guard watching nothing',
      len(missing) <= len(P.ACCUMULATED) // 3,
      '%d of %d missing: %r' % (len(missing), len(P.ACCUMULATED), missing))
check('D2. GENERATED and ACCUMULATED do not overlap -- a generated document '
      'is SAFE to resolve with --ours and these are the opposite, so a file '
      'in both lists would get contradictory advice',
      not (set(d for d, _ in P.GENERATED) & set(p for p, _ in P.ACCUMULATED)))

print('\n%d passed, %d failed' % (len(PASS), len(FAIL)))
sys.exit(1 if FAIL else 0)
