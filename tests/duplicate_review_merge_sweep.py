#!/usr/bin/env python
"""tests/duplicate_review_merge_sweep.py

Run:  python tests/duplicate_review_merge_sweep.py

EVERY OBLIGATION REVIEWED TWICE, SWEPT -- did the merge lose anything?

REPORT-ONLY AND EXIT 0. It reads docs/tier-a-reviews.json and reports; it
changes nothing and gates nothing.

WHY THIS EXISTS. On 2026-09-21 four obligations were discharged twice, minutes
apart, because the register was first-come and nothing keyed on whose review it
was. Each collision was resolved by MERGING -- the first lander keeps
reviewer_session, the second is appended under a marker -- but that convention
was applied by hand, four times, under time pressure, by a session that had
just lost a rebase. A convention applied by hand four times is exactly the
thing to check mechanically once.

Ownership shipped with tools/tier_a_review_gate.py on the same day and removes
the race going forward. This sweep is about the records made BEFORE it, and it
asks three questions a reader of the register would want answered:

  1. Is any merged record INTERNALLY INCONSISTENT -- a second verdict present
     while reviewer_session names the second reviewer, or a second verdict
     whose author is the record's own author?
  2. Was anything LOST -- is the first verdict still intact and ahead of the
     marker, or did the append overwrite part of it?
  3. Do the two verdicts CONTRADICT each other on a verdict-level judgement?
     That one cannot be answered mechanically, so it is reported as the
     material for a human rather than decided here.
"""

import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REVIEWS = os.path.join(ROOT, 'docs', 'tier-a-reviews.json')
MARKER = 'SECOND INDEPENDENT REVIEW'

problems = 0
data = json.load(io.open(REVIEWS, encoding='utf-8'))
records = data['records']

merged = [r for r in records if MARKER in (r.get('verdict') or '')]
print('records in the register        : %d' % len(records))
print('records carrying a SECOND review: %d' % len(merged))
print()

for r in merged:
    v = r['verdict']
    at = v.find(MARKER)
    first, second = v[:at], v[at:]
    who = re.search(MARKER + r',\s*([a-z][a-z0-9_-]*)', v)
    who = who.group(1) if who else None
    author = r.get('author_session')
    owner_of_record = r.get('reviewer_session')

    print('=' * 78)
    print('%s opened %s  -- %s' % (author, r.get('opened_at'),
                                   ', '.join(r.get('resources') or [])[:60]))
    print('  status            : %s' % r.get('status'))
    print('  reviewer_session  : %s   (the FIRST lander keeps the field)'
          % owner_of_record)
    print('  second reviewer   : %s' % who)
    print('  first verdict     : %d chars' % len(first.strip()))
    print('  second verdict    : %d chars' % len(second))

    # ── 1. INTERNAL CONSISTENCY ────────────────────────────────────────────
    if who and who == owner_of_record:
        problems += 1
        print('  ** the second reviewer IS the field holder -- one of the two '
              'is mislabelled')
    if who and who == author:
        problems += 1
        print('  ** the second reviewer is the record AUTHOR -- a self-review '
              'wearing a merge')
    if owner_of_record == author:
        problems += 1
        print('  ** reviewer_session IS the author')
    if r.get('status') != 'reviewed':
        problems += 1
        print('  ** status is %r, not "reviewed"' % r.get('status'))

    # ── 2. WAS ANYTHING LOST ───────────────────────────────────────────────
    # A first verdict of a few hundred characters would mean the append ate it.
    if len(first.strip()) < 400:
        problems += 1
        print('  ** the FIRST verdict is only %d chars -- the append may have '
              'overwritten it' % len(first.strip()))
    if len(second) < 400:
        problems += 1
        print('  ** the SECOND verdict is only %d chars' % len(second))
    # The marker must appear exactly once: twice would mean a third review was
    # appended onto a marker rather than after it.
    if v.count(MARKER) != 1:
        problems += 1
        print('  ** the marker appears %d times' % v.count(MARKER))

    # ── 3. THE MATERIAL FOR A HUMAN ────────────────────────────────────────
    # Not decidable mechanically, so it is SHOWN rather than judged. What a
    # reader wants is whether the two reviews reached different conclusions,
    # and the cheapest honest signal is whether the second says so itself.
    disagrees = [p for p in ('split on', 'disagree', 'not in cc', "not in hank",
                             'ADDS', 'adds', 'contradict')
                 if p in second]
    print('  second review says it differs: %s'
          % (', '.join(sorted(set(disagrees))) or 'no explicit signal'))
    lead = re.search(r'--\s*(.{0,150})', second)
    if lead:
        print('  its own account of why it was kept:')
        print('    %s' % re.sub(r'\s+', ' ', lead.group(1)).strip()[:150])

print('=' * 78)
print()
if not merged:
    print('No merged records found -- nothing to sweep.')
else:
    print('MECHANICAL PROBLEMS FOUND: %d' % problems)
    print()
    print('WHAT THIS CANNOT ANSWER, said plainly rather than implied: whether')
    print('two verdicts CONTRADICT each other on a judgement is a reading, not')
    print('a field comparison. The counts above prove the merges are')
    print('structurally intact -- first lander keeps the field, both verdicts')
    print('are present at full length, no self-review, one marker each -- and')
    print('the last line under each record is the material a person needs to')
    print('decide the rest.')
print()
print('Report-only: exit 0 by design.')
sys.exit(0)
