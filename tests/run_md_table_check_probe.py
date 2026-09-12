"""tests/run_md_table_check_probe.py -- the table checker finds what it claims
to find, and refuses what it cannot safely repair.

    python tests/run_md_table_check_probe.py

A checker that reports OK is only worth having if it can be shown to report
NOT-OK. This drives the real `tools/md_table_check.py` against throwaway
fixtures written to a temp directory -- never into the repo -- covering the
cases that actually occur in `docs/SAIRN-OPEN-WORK-INDEX.md`:

  * a pipe inside prose (`Write|Edit`), the shape found on the redaction row;
  * a `||` inside a code span, the shape found on the SAIRNroofing row;
  * an already-escaped `\\|`, which must NOT be reported -- if it were, the
    fix for the first two cases would look like a new defect;
  * SEVERAL TABLES OF DIFFERENT WIDTHS in one file, because that document has
    three and a fixed expectation would be wrong twice;
  * a row that is too NARROW, which must be reported like any other.

THIS PROBE ALREADY EARNED ITS KEEP ONCE. The checker shipped with a `--fix`
that escaped surplus pipes automatically. Given `| A | a Write|Edit hook | C |`
it kept `Write|Edit` as a separator and escaped the REAL one before `C`,
merging two genuine columns -- the exact corruption the tool exists to prevent,
committed by the tool. The case below is what caught it, and `--fix` was
removed rather than patched: which pipe the author meant as a separator is a
question about intent, and the two real occurrences were repaired by reading
them.
"""
import io
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
import md_table_check as mt          # noqa: E402

HEADER = '| App | Item | Owner |\n|---|---|---|\n'

CASES = [
    # (name, body rows, expected number of problems)
    ('a clean 3-column table', ['| A | B | C |'], 0),
    ('a pipe in prose is caught', ['| A | a Write|Edit hook | C |'], 1),
    ('a || in a code span is caught', ['| A | `if (!x || y)` | C |'], 1),
    ('an ALREADY-ESCAPED pipe is not a problem',
     ['| A | a Write\\|Edit hook | C |'], 0),
    ('two escaped pipes are still not a problem',
     ['| A | `if (!x \\|\\| y)` | C |'], 0),
    ('a row with a missing separator is caught', ['| A | B |'], 1),
    ('several bad rows are all reported',
     ['| A | a|b | C |', '| D | E |', '| F | G | H |'], 2),
]

fails = 0
tmp = tempfile.mkdtemp(prefix='mdtable-')


def write(name, text):
    p = os.path.join(tmp, name)
    with io.open(p, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(text)
    return p


def check(label, actual, expected):
    global fails
    if actual == expected:
        return True
    fails += 1
    print('FAIL  %s\n        expected %r\n        actual   %r' % (label, expected, actual))
    return False


for i, (name, rows, want) in enumerate(CASES):
    path = write('case%d.md' % i, HEADER + '\n'.join(rows) + '\n')
    check(name, len(mt.scan(path)), want)

# Different widths in one file, which is the real document's shape.
multi = write('multi.md',
              '| A | B | C |\n|---|---|---|\n| 1 | 2 | 3 |\n\n'
              '| X | Y |\n|---|---|\n| 1 | 2 |\n\n'
              '| P | Q | R | S |\n|---|---|---|---|\n| 1 | 2 | 3 | 4 |\n')
check('three tables of three widths, all consistent, all pass',
      len(mt.scan(multi)), 0)

multi_bad = write('multi_bad.md',
                  '| A | B | C |\n|---|---|---|\n| 1 | 2 | 3 |\n\n'
                  '| X | Y |\n|---|---|\n| 1 | 2 | 3 |\n')
probs = mt.scan(multi_bad)
check('a row that is wrong for ITS OWN table is caught', len(probs), 1)
check('and it is reported against that table\'s width, not the first one\'s',
      (probs[0][1], probs[0][2]) if probs else None, (5, 4))

# The checker REPORTS and never writes. This is the case that caught the
# removed --fix corrupting a row, kept as the reason the tool is read-only.
readonly = HEADER + '| A | a Write|Edit hook | C |\n'
ro = write('readonly.md', readonly)
mt.main([ro])
with io.open(ro, encoding='utf-8') as fh:
    check('running the checker leaves the file byte-for-byte alone',
          fh.read(), readonly)
check('and it still reports the row', len(mt.scan(ro)), 1)
check('the tool exposes no repair entry point at all',
      hasattr(mt, 'fix_row'), False)

# ── WHAT THE CHECKER CANNOT SEE MUST BE REPORTED, NOT PASSED OVER ──────────
# Added 2026-09-12. blocks() ends a table at the first line not starting with
# `|`, so ANY interruption severs every row after it -- they stay in the file,
# stay read by humans, and stop being checked. On the real index three
# unresolved conflict markers had been on origin/main since 2026-09-11, and
# this checker examined 110 of 346 rows and printed OK. These arms plant both
# shapes on fixtures and demand they be seen, because a checker that finds
# nothing is indistinguishable from one that looks at nothing.

conflict = write('conflict.md',
                 HEADER + '| A | B | C |\n'
                 '<<<<<<< HEAD\n| D | E | F |\n=======\n| G | H | I |\n'
                 '>>>>>>> abc1234 (some commit)\n| J | K | L |\n')
orph = mt.orphans(conflict)
check('all three conflict markers are reported',
      sorted(k for _, k, _ in orph if k == 'conflict'),
      ['conflict'] * 3)
check('and the rows the markers severed are reported as orphans, not silently dropped',
      len([1 for _, k, _ in orph if k == 'orphan']), 3)
check('the severed rows are genuinely invisible to scan() -- which is the point',
      len(mt.scan(conflict)), 0)
check('coverage says so out loud rather than claiming a clean pass',
      mt.coverage(conflict), (2, 5))

# A row split across two lines by a newline inside a code span: the second
# half does not start with `|`, so it ends the table exactly like a marker.
split = write('split.md',
              HEADER + "| A | `newline='\n' here` | C |\n| D | E | F |\n")
check('a row split by an embedded newline leaves an orphan behind',
      len([1 for _, k, _ in mt.orphans(split) if k == 'orphan']), 1)

# THE CONTROL THAT MATTERS. Without it, an orphan reporter that flagged every
# row would pass every arm above.
clean = write('clean.md', HEADER + '| A | B | C |\n| D | E | F |\n')
check('CONTROL: a clean table has no orphans and no conflicts',
      mt.orphans(clean), [])
check('CONTROL: and it reports full coverage, header included',
      mt.coverage(clean), (3, 3))

# A `|` inside a fenced code block is NOT a table row. This is the false
# positive that would make the new reporting unusable if it existed.
check('a pipe line outside any table in ordinary prose is reported once',
      len(mt.orphans(write('prose.md', 'text\n| stray |\nmore text\n'))), 1)

# The real document must be clean, since that is the file this exists for --
# and "clean" now means every row was READ, not merely that the read ones
# passed.
check('the live open-work index passes',
      len(mt.scan('docs/SAIRN-OPEN-WORK-INDEX.md')), 0)
check('the live open-work index has nothing this checker cannot read',
      mt.orphans('docs/SAIRN-OPEN-WORK-INDEX.md'), [])
_checked, _looks = mt.coverage('docs/SAIRN-OPEN-WORK-INDEX.md')
check('and every row in it is actually checked', _checked, _looks)

print(('FAILED  ' if fails else 'ok  ') +
      'md-table-check: %d cases, %d failed' % (len(CASES) + 18, fails))
sys.exit(1 if fails else 0)
