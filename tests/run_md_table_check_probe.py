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

# The real document must be clean, since that is the file this exists for.
check('the live open-work index passes',
      len(mt.scan('docs/SAIRN-OPEN-WORK-INDEX.md')), 0)

print(('FAILED  ' if fails else 'ok  ') +
      'md-table-check: %d cases, %d failed' % (len(CASES) + 8, fails))
sys.exit(1 if fails else 0)
