"""The copied court weight must never travel without its as-of date.

    python tests/run_citator_freshness_probe.py

WHAT THIS ASSERTS, AND WHAT IT CANNOT. api/legal-citator.js has no test harness
-- it is network-heavy and its copy path is DORMANT (`const citingCourtId =
null;`), so there is no behaviour to drive. The requirement here is structural:
two fields must be written together, and the cache upsert must set the column
whose DEFAULT only applies on INSERT.

So these are source assertions, which the scrubber's item 16 rightly treats as
suspect. Two things keep them honest: every match runs against COMMENT-STRIPPED
source, so a sentence describing the rule cannot satisfy it; and each arm has a
control that removes the real line and checks the arm goes red.
"""
# REQUIREMENT: a citation the citator reports as current was checked against a source
#   within the stated window, so staleness cannot read as currency
#
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, 'tools'))
os.chdir(REPO)

import jscomments   # noqa: E402

SRC = 'api/legal-citator.js'
PASS, FAIL = [], []


def check(name, cond, detail=''):
    (PASS if cond else FAIL).append(name)
    print(('  ok   ' if cond else '  FAIL ') + name
          + (('\n        ' + str(detail)[:240]) if (detail and not cond) else ''))


def code(text=None):
    if text is None:
        text = io.open(SRC, encoding='utf-8', errors='replace').read()
    return jscomments.strip_comments(text)


def writes_both(c):
    return ('court_hierarchy_weight:' in c) and ('court_hierarchy_weight_as_of:' in c)


def upsert_stamps(c):
    """Does the cl_court_cache UPSERT statement carry last_refreshed_at?

    A non-greedy match to the first `})` stopped short of the field, because the
    body object is long and contains nested braces -- and arm 3d then passed
    VACUOUSLY, agreeing that the sabotaged file also lacked it. Caught because
    2a was red at the same time. The window is now the statement itself: from
    the anchor to the next `await fetch(` or the end of the file.
    """
    i = c.find("rest('cl_court_cache')")
    if i < 0:
        return False
    j = c.find('await fetch(', i + 10)
    stmt = c[i:j if j > 0 else len(c)]
    return 'last_refreshed_at' in stmt


real = io.open(SRC, encoding='utf-8', errors='replace').read()
c = code(real)

print('--- 1. the copy and its stamp are written together ---')
check('1a  court_hierarchy_weight is written at all', 'court_hierarchy_weight:' in c)
check('1b  ...and court_hierarchy_weight_as_of beside it -- a copy with no '
      'as-of date cannot be told from a current value', writes_both(c))
check('1c  the stamp is read from the SOURCE row, not set to now() -- stamping '
      'an unknown copy with the current time asserts a freshness nobody '
      'measured', 'last_refreshed_at' in c and 'courtWeightAsOf' in c)

print('\n--- 2. the cache upsert sets last_refreshed_at explicitly ---')
check('2a  the cl_court_cache upsert carries last_refreshed_at', upsert_stamps(c),
      'a DEFAULT applies only on INSERT; merge-duplicates UPDATEs an existing '
      'row and would keep the FIRST fetch time forever')

print('\n--- 3. CONTROLS: each arm must go red when its line is removed ---')
sab1 = real.replace('court_hierarchy_weight_as_of: courtWeightAsOf,', '')
check('3a  CONTROL APPLIED: the stamp line really was removed', sab1 != real)
check('3b  ...and arm 1b then FAILS', not writes_both(code(sab1)))

sab2 = re.sub(r",\s*last_refreshed_at: refreshedAt", '', real, count=1)
check('3c  CONTROL APPLIED: the upsert stamp really was removed', sab2 != real)
check('3d  ...and arm 2a then FAILS', not upsert_stamps(code(sab2)))

print('\n--- 4. comments alone must not satisfy any arm ---')
prose = ('// court_hierarchy_weight: and court_hierarchy_weight_as_of: and\n'
         '// last_refreshed_at are all discussed right here in this comment\n'
         'var x = 1;\n')
check('4a  a file that only TALKS about the fields satisfies nothing -- the '
      'scrubber item 16 shape', not writes_both(code(prose)))

print('\n--- 5. the file is unchanged by this probe ---')
check('5a  nothing was written to disk',
      io.open(SRC, encoding='utf-8', errors='replace').read() == real)

print('\n%d passed, %d failed' % (len(PASS), len(FAIL)))
sys.exit(1 if FAIL else 0)
