# -*- coding: utf-8 -*-
"""ITEM 11 -- add `disable-model-invocation: true` to skills that cannot apply here.

A NARROW SET, AND THE NARROWNESS IS THE POINT. This flag changes what FIVE other
sessions see in their skill list, and `/skill-doctor` -- the thing that would give
the real per-skill cost -- is a client-side command a model turn cannot invoke. So
the set is limited to skills whose irrelevance is DOCUMENTED or CHECKABLE, not
guessed:

  design-taste-frontend   CLAUDE.md itself: "scoped to marketing sites and RARELY
                          APPLIES"
  ui-ux-pro-max           CLAUDE.md itself: "is a lookup table, NOT A COMPETITOR"
  domain-check            domain availability / WHOIS / RDAP lookups. No SAIRN app
                          registers or checks domains; nothing in the repo calls it.
  playwright-devops       Playwright CI workflow debugging. This platform drives
                          Playwright directly and sairn-visual-review owns that
                          use; there is no Playwright CI here.

EVERY OTHER CANDIDATE IS LEFT ALONE AND REPORTED INSTEAD. The 39 skills not named
in a CLAUDE.md include several that clearly matter (sairn-session-handoff,
sairn-master-orientation, sairn-silent-failure-sweep), so "not named" is NOT a
usage measurement and is not treated as one.

The flag is MERGED INTO EXISTING FRONTMATTER, never written over it, and a file
without frontmatter is REFUSED rather than given some.
"""
import io
import os
import shutil
import sys
import time

SK = os.path.join(os.path.expanduser('~'), '.claude', 'skills')
S = os.path.dirname(os.path.abspath(__file__))
TARGETS = [
    ('design-taste-frontend',
     'CLAUDE.md: scoped to marketing sites and rarely applies'),
    ('ui-ux-pro-max',
     'CLAUDE.md: a lookup table, not a competitor'),
    ('domain-check',
     'domain availability/WHOIS/RDAP; no SAIRN app does this and nothing in the '
     'repo calls it'),
    ('playwright-devops',
     'Playwright CI workflow debugging; this platform drives Playwright directly '
     'and sairn-visual-review owns that use'),
]

done = skipped = failed = 0
for name, why in TARGETS:
    p = os.path.join(SK, name, 'SKILL.md')
    if not os.path.isfile(p):
        print('%-26s ABSENT at %s -- not created, not guessed at' % (name, p))
        failed += 1
        continue
    raw = io.open(p, encoding='utf-8', errors='replace').read()
    if not raw.startswith('---'):
        print('%-26s REFUSED: no YAML frontmatter. Adding one would be '
              'inventing structure in somebody else\'s skill.' % name)
        failed += 1
        continue
    parts = raw.split('---', 2)
    if len(parts) < 3:
        print('%-26s REFUSED: frontmatter is not closed.' % name)
        failed += 1
        continue
    fm = parts[1]
    if 'disable-model-invocation' in fm:
        print('%-26s ALREADY SET -- no change' % name)
        skipped += 1
        continue
    bak = os.path.join(S, 'SKILL.%s.bak.%s'
                       % (name, time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())))
    shutil.copy(p, bak)
    new_fm = fm.rstrip('\n') + ('\ndisable-model-invocation: true'
                                '  # hank 2026-10-08: %s\n' % why)
    out = '---' + new_fm + '---' + parts[2]
    io.open(p, 'w', encoding='utf-8', newline='\n').write(out)
    back = io.open(p, encoding='utf-8', errors='replace').read()
    bparts = back.split('---', 2)
    okk = (back.startswith('---') and len(bparts) >= 3
           and 'disable-model-invocation: true' in bparts[1]
           and bparts[2] == parts[2])
    if not okk:
        shutil.copy(bak, p)
        print('%-26s FAILED verification -- restored from backup' % name)
        failed += 1
        continue
    print('%-26s SET (body byte-identical, backup %s)'
          % (name, os.path.basename(bak)))
    done += 1

print('')
print('SET %d   ALREADY %d   REFUSED/ABSENT %d   of %d targeted'
      % (done, skipped, failed, len(TARGETS)))
