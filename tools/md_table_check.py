"""tools/md_table_check.py -- a markdown table row must have the columns its
header says it has.

    python tools/md_table_check.py                       # the standing docs
    python tools/md_table_check.py docs/SOME-FILE.md ... # named files

IT REPORTS AND DOES NOT REPAIR, and that is a decision with a scar on it. The
first version carried a `--fix` that escaped surplus pipes automatically. Its
own probe caught it corrupting the row it was repairing: given

    | A | a Write|Edit hook | C |

it kept `Write|Edit` as a column separator and escaped the REAL separator
before `C`, merging two genuine columns into one. There is no reliable way to
tell from the text which pipe the author meant as a separator -- that is a
question about intent, and a fixer that answers it by heuristic silently
destroys a column in the file every session trusts to say who is doing what.
The two real occurrences found on 2026-09-04 were repaired by reading them and
escaping the right character by hand, which took a minute. `--fix` was removed
rather than improved.

WHY THIS EXISTS (2026-09-04). `docs/SAIRN-OPEN-WORK-INDEX.md` is this
platform's coordination surface: four sessions read it to choose work and edit
it to record outcomes. Rows are routinely updated by splitting the line on
`|`, replacing a cell by index, and joining it back.

That is safe only while every `|` in the row is a column separator. It is not.
A cell whose prose contains a pipe -- a hook matcher written `Write|Edit`, a
regex alternation, a code span holding a table -- adds separators the author
never intended, and then:

  * markdown renders the row with extra columns, so the LAST cells fall off
    the end of the table. On the two rows found today that meant the **Sz**
    column was gone and narrative text was rendered as if it were a column
    heading value;
  * an edit by cell index writes into the WRONG CELL. CC hit exactly this
    while updating a row, which is what prompted this tool. A status landed
    where an owner belonged, silently, in the file every session trusts to
    say who is doing what.

── WHAT IT CHECKS ────────────────────────────────────────────────────────
Per contiguous table block, not per file: this document contains several
tables with different column counts (the 7-column open-work table, a
3-column corrections table, a 4-column closed table), so a fixed expectation
would be wrong three ways. The header row defines the width and every body
row in that block must match it.

Escaped pipes (`\\|`) are counted as content, not separators, because that is
what markdown does with them.

── WHAT IT DELIBERATELY DOES NOT DO ──────────────────────────────────────
It does not check that a cell's CONTENT is sensible, that an owner exists, or
that a status is current -- those are `sairn-memory-curator` questions and no
parser can answer them. A file passing this check can still be entirely wrong;
it just cannot be structurally misread.
"""
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Files that carry tables every session reads. Extend deliberately; a wide
# default glob would drag in every doc that ever used a pipe in prose.
DEFAULT_FILES = [
    'docs/SAIRN-OPEN-WORK-INDEX.md',
]

# A pipe not preceded by a backslash. Markdown treats `\|` as literal content.
UNESCAPED = re.compile(r'(?<!\\)\|')
SEPARATOR = re.compile(r'^\s*\|?[\s:\-|]+\|[\s:\-|]*$')


def _resolve(path):
    """Repo-relative by default; absolute paths pass through so the probe can
    drive this against throwaway fixtures without writing them into the repo."""
    return path if os.path.isabs(path) else os.path.join(ROOT, path)


def cells(line):
    return UNESCAPED.split(line)


def is_row(line):
    return line.lstrip().startswith('|')


def blocks(lines):
    """Yield (header_index, [body_indices]) for each contiguous table."""
    i = 0
    while i < len(lines):
        if is_row(lines[i]) and i + 1 < len(lines) and SEPARATOR.match(lines[i + 1]) \
                and is_row(lines[i + 1]):
            header, body, j = i, [], i + 2
            while j < len(lines) and is_row(lines[j]):
                body.append(j)
                j += 1
            yield header, body
            i = j
        else:
            i += 1


def scan(path):
    """Return a list of (line_no, found, expected, text) problems."""
    with io.open(_resolve(path), encoding='utf-8') as fh:
        lines = fh.read().split('\n')
    bad = []
    for header, body in blocks(lines):
        width = len(cells(lines[header]))
        for j in body:
            got = len(cells(lines[j]))
            if got != width:
                bad.append((j + 1, got, width, lines[j]))
    return bad


def main(argv):
    files = [a for a in argv if not a.startswith('--')] or DEFAULT_FILES
    total = 0
    for path in files:
        bad = scan(path)
        for line_no, got, want, text in bad:
            print('%s:%d  %d cells, header says %d  %s'
                  % (path, line_no, got, want, text[:90]))
        total += len(bad)
        if not bad:
            print('%s: OK' % path)
    print('TOTAL_MALFORMED_ROWS:%d' % total)
    return 1 if total else 0


if __name__ == '__main__':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.exit(main(sys.argv[1:]))
