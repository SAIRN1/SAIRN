# -*- coding: utf-8 -*-
"""ITEM 3 -- split the 101 suite failures by OWNER.

SOURCE: scratchpad/i3.rerun.json, produced in batch 18 by re-running every
FAILing file ALONE on a tree restored with `reset --hard` + `clean -fd` before
each one, 240 s bound. 89 REAL, 8 CASCADE, 4 TIMEOUT.

OWNER IS DERIVED FROM TWO SOURCES AND EACH ROW SAYS WHICH ONE:

  map        docs/tool-owner-map.json, where the entry is not null
  claim      a session's claim has DECLARED the file in its FILES list, read
             out of every .claude/claims/*.json record ever written -- which is
             the only durable record of who has worked on a file
  UNOWNED    neither. 502 of the map's 680 ownerless entries are under tests/,
             so this is the common case and is reported as its own count rather
             than guessed at.

A GUESS IS NEVER WRITTEN. "UNOWNED" means nothing in either source names an
owner, not that nobody wrote it.
"""
import collections
import glob
import io
import json
import os
import sys

REPO = r'C:\Users\marsh\Documents\SAIRN-hank'
S = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1]

rows = json.load(io.open(os.path.join(S, 'i3.rerun.json'), encoding='utf-8'))

omap = json.load(io.open(os.path.join(REPO, 'docs', 'tool-owner-map.json'),
                         encoding='utf-8'))['tools']

# -- every file any claim has ever DECLARED, with who declared it.
declared = collections.defaultdict(set)
for p in sorted(glob.glob(os.path.join(REPO, '.claude', 'claims', '*.json'))):
    try:
        d = json.load(io.open(p, encoding='utf-8'))
    except ValueError:
        continue
    for c in d.get('claims', []):
        sess = c.get('session') or os.path.basename(p)[:-5]
        task = c.get('task') or ''
        i = task.find('FILES:')
        if i < 0:
            continue
        for tok in task[i + 6:].split():
            if '/' in tok and ('.' in tok):
                declared[tok].add(sess)


def cell(text):
    """One markdown table cell, safe by construction.

    A CARRIAGE RETURN INSIDE A CELL SPLITS THE ROW, and the first version of
    this table hit it: three tracebacks carried a bare \r from a subprocess
    captured on Windows. md_table_check reported "5 cells, header says 6" and
    then 62 ORPHAN rows downstream -- ONE broken row unparses everything after
    it, so the damage is nothing like proportional to the cause.

    Escaping the pipe was not enough, because the pipe was never the problem.
    So: every control character becomes a space, and a pipe becomes a SLASH
    rather than a backslash-escape -- escaping is parser-dependent and this
    repo's own md_table_check is the arbiter that has to be satisfied.
    """
    t = ''.join((' ' if ord(c) < 32 else c) for c in (text or ''))
    t = t.replace('|', '/')
    return ' '.join(t.split()) or '(no output)'


def owner_of(rel):
    e = omap.get(rel) or omap.get(os.path.basename(rel))
    if e and e.get('owner'):
        return e['owner'], 'map'
    if rel in declared:
        return '+'.join(sorted(declared[rel])), 'claim'
    return 'UNOWNED', '-'


for r in rows:
    r['owner'], r['basis'] = owner_of(r['file'])

real = [r for r in rows if r['verdict'] == 'REAL']
casc = [r for r in rows if r['verdict'] == 'CASCADE']
tmo = [r for r in rows if r['verdict'] == 'TIMEOUT']

L = []
w = L.append
w('# The 101 suite failures, split by owner — batch 19, 2026-10-08')
w('')
w('**SOURCE.** The clean-worktree run of `tools/run_all_tests.py` in batch 18 '
  '(`python -u`, captured **EXIT 1**): 757 files, 651 ok, **101 FAIL**, 5 '
  'SKIPPED, 2 NOT RUN. Every one of the 101 was then re-run **ALONE**, on a '
  'tree restored with `reset --hard` plus `clean -fd` **before each file**, at '
  'a 240 s bound.')
w('')
w('**WHY ALONE.** The suite dirties its own tree — its footer names five paths '
  'and says *"Results above may be CASCADE, not real."* The generators it runs '
  'regenerate documents, and every clean-tree probe after that point fails for '
  'a reason that is not its own. Running in a clean worktree does **not** fix '
  'that; only running each file by itself does.')
w('')
w('| verdict | count | meaning |')
w('|---|---:|---|')
w('| **REAL** | **%d** | non-zero ALONE, on a restored tree |' % len(real))
w('| **CASCADE** | **%d** | exit 0 alone — failed in the suite only because '
  'something earlier dirtied the tree |' % len(casc))
w('| **TIMEOUT** | **%d** | exceeded 240 s alone. A third state, folded into '
  'neither |' % len(tmo))
w('')
w('**OWNER IS DERIVED, NOT GUESSED.** `map` = a non-null entry in '
  '`docs/tool-owner-map.json`. `claim` = a session DECLARED the file in a '
  'claim\'s `FILES:` list, read out of every record in `.claude/claims/*.json`. '
  '**`UNOWNED` means neither source names anybody** — not that nobody wrote it. '
  '502 of the owner map\'s 680 ownerless entries are under `tests/`, so this is '
  'the common case and is counted rather than filled in.')
w('')

bo = collections.Counter(r['owner'] for r in real)
w('## REAL failures by owner (%d)' % len(real))
w('')
w('| owner | count |')
w('|---|---:|')
for o, n in bo.most_common():
    w('| %s | %d |' % (('**%s**' % o) if o != 'UNOWNED' else o, n))
w('')

for o, _n in bo.most_common():
    sel = [r for r in real if r['owner'] == o]
    w('### %s — %d REAL' % (o, len(sel)))
    w('')
    w('| suite | basis | exit | first failing assertion |')
    w('|---|---|---:|---|')
    for r in sorted(sel, key=lambda x: x['file']):
        first = cell(r['first'])
        w('| `%s` | %s | %s | %s |'
          % (r['file'], r['basis'], r['code'], first[:200] or '(no output)'))
    w('')

w('---')
w('')
w('## CASCADE — listed separately, and NOT counted as failures (%d)' % len(casc))
w('')
w('**These exit 0 alone.** Their suite verdict is an artefact of the tree being '
  'dirty by the time they ran.')
w('')
w('| suite | owner | basis | suite said | ALONE |')
w('|---|---|---|---|---|')
for r in sorted(casc, key=lambda x: x['file']):
    sl = cell(r.get('suite_line'))
    first = cell(r['first'])
    w('| `%s` | %s | %s | %s | **%s** |'
      % (r['file'], r['owner'], r['basis'], sl[:90] or '(nothing)',
         first[:90]))
w('')
w('**`tests/phi_cache_scoped_to_user.js` is the one to read twice.** Alone, on '
  'a restored tree, it is **72 passed / 0 failed**. Fourth\'s batch-16 item 4 '
  'took it on as *"basis NONE, no owner, blocks three register rows"*. Three '
  'register rows may be blocked on a green test.')
w('')
w('---')
w('')
w('## TIMEOUT at 240 s alone — a third state, classified as neither (%d)'
  % len(tmo))
w('')
w('**NOT counted as REAL and NOT counted as CASCADE.** Exceeding a bound is not '
  'evidence either way, and the bound was mine.')
w('')
w('| suite | owner | basis | suite said |')
w('|---|---|---|---|')
for r in sorted(tmo, key=lambda x: x['file']):
    sl = cell(r.get('suite_line'))
    w('| `%s` | %s | %s | %s |' % (r['file'], r['owner'], r['basis'],
                                   sl[:120] or '(nothing)'))
w('')
w('**NEXT STEP for these four:** re-run each with NO ceiling on a quiet box. A '
  'bound exceeded is a lower bound, not a number — the same discipline batch 18 '
  'applied to `dead_rule_sweep.py`.')
w('')
w('---')
w('')
w('## WHAT THIS TABLE DOES NOT CLAIM')
w('')
w('* **It does not claim the 89 are NEW.** They are real *alone*; many are '
  'long-standing and some are already in `docs/known-red-suites.json`. '
  '`known_red_check.py --from-run` against this same log reports **101 red, '
  'registry records 75, 30 RED AND NOT RECORDED** — that register is '
  '**fourth\'s** and is not touched here.')
w('* **It does not diagnose any of them.** The "first failing assertion" column '
  'is the first failure line each file printed when driven alone, quoted, not '
  'interpreted.')
w('* **`UNOWNED` is a gap in the record, not a verdict.** A file with no owner '
  'cannot be routed to anybody, which is the same problem '
  '`tools/va_rule_currency.py` had in batch b1.')

io.open(OUT, 'w', encoding='utf-8', newline='\n').write('\n'.join(L) + '\n')
print('wrote %s' % OUT)
print('REAL %d  CASCADE %d  TIMEOUT %d  = %d'
      % (len(real), len(casc), len(tmo), len(rows)))
print('REAL by owner: %s' % dict(bo))
