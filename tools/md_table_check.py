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
    # Added 2026-09-12 with the primer/process split. Both carry a table every
    # session reads -- the clone-to-worklog mapping, and the three-tools-for-one
    # -lesson table -- and both sit in files where prose pipes are common.
    'CLAUDE.md',
    'docs/SAIRN-PROCESS-RULES.md',
    # ── ADDED 2026-10-05, AND THE REASON IS A DEFECT THIS LIST'S OWN NARROWNESS
    # ── LET THROUGH ────────────────────────────────────────────────────────────
    # On 2026-09-27 rows 355 and 356 of the open-work index were malformed by a
    # `|` inside a CODE SPAN, where neither `\|` nor `&#124;` can work because a
    # code span renders its contents literally. That was written up as a lesson
    # the same day.
    #
    # On 2026-10-05 the SAME DEFECT was committed again, by the session that
    # wrote the lesson, in `docs/CRITICALITY-TIERS.md` -- a cell went to 12
    # cells against a 6-cell header. IT WAS NOT CAUGHT BY THIS TOOL, because
    # this list did not contain that file; it was caught by a hand-rolled
    # one-off script, which then false-flagged three HEADER rows in an unrelated
    # document because it only updated its expected width on separator lines.
    #
    # SO THE LESSON DID NOT FAIL -- THE INSTRUMENT DID NOT READ THE FILE. A
    # discipline written in prose cannot prevent what nothing measures, and the
    # second-order cost is worse than the first: a session that finds this tool
    # blind to its file hand-rolls a WORSE checker, and then trusts it.
    #
    # Both additions were measured before being added -- 434 and 516 rows, zero
    # malformed, zero unreadable -- so neither arrives red. Deliberately still a
    # NAMED LIST and not a glob, for the reason stated above the list.
    'docs/CRITICALITY-TIERS.md',
    'docs/traceability-matrix.md',
    # ── ADDED 2026-10-05, LATER THE SAME DAY, AND THE OMISSION BELOW IS NOW
    # ── CLOSED RATHER THAN RE-ARGUED ─────────────────────────────────────────
    # It was left out hours earlier because it carried 11 genuinely malformed
    # rows and is GENERATED, so adding it would have parked this tool in a
    # state no document edit could clear. tools/tooling_inventory.py's cell
    # emitter is now fixed -- all three free-text sources route through
    # table_safe(), and the generator REFUSES TO WRITE a malformed table at
    # all -- so the file is clean (401/401, 0 malformed) and arrives green.
    'docs/TOOLING-INVENTORY.md',
]

# NOT ADDED, AND NAMED SO THE OMISSION IS A DECISION RATHER THAN AN OVERSIGHT.
# `docs/TOOLING-INVENTORY.md` carries 400 rows and **11 GENUINELY MALFORMED
# ROWS** at the time of writing, every one from a `|` inside a code span in a
# tool's PURPOSES text (`+ (x || 0)`, `[ -f tools/x.py ] || exit 0`). It is a
# GENERATED file, so the row cannot be repaired in place -- the fix belongs in
# `tools/tooling_inventory.py`'s cell emitter, which is a different change with
# a different owner. Adding the file here before that fix would put this tool
# permanently in a reporting state nobody can clear from the document itself,
# which is how a report-only check becomes noise. Recorded as an open-work row
# instead, with the eleven line numbers.
# Empty, and that is a RESULT rather than a default. Its one entry --
# docs/TOOLING-INVENTORY.md, 11 rows malformed by pipes inside code spans --
# was resolved the same day by fixing the generator rather than the rows, so
# the file moved into DEFAULT_FILES above. Kept as a named constant because the
# next deliberate omission should be recorded here rather than argued in a
# commit message, and because the probe asserts on it.
KNOWN_UNADDED = {}

# A pipe not preceded by a backslash. Markdown treats `\|` as literal content.
UNESCAPED = re.compile(r'(?<!\\)\|')
SEPARATOR = re.compile(r'^\s*\|?[\s:\-|]+\|[\s:\-|]*$')

# An unresolved VCS conflict marker at the start of a line. Added 2026-09-12,
# see ORPHAN ROWS below.
CONFLICT = re.compile(r'^(<{7}|={7}|>{7})(\s|$)')


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


def orphans(path):
    """Return (line_no, kind, text) for every line this checker CANNOT judge.

    ── WHY THIS EXISTS, AND WHY IT IS NOT AN AFTERTHOUGHT ──────────────────
    `blocks()` starts a table at a header+separator pair and ends it at the
    first line that does not start with `|`. That is correct markdown, and it
    means ANY interruption silently severs every row after it: the rows are
    still there, still read by a human, and no longer checked by anything.

    MEASURED on docs/SAIRN-OPEN-WORK-INDEX.md the day this was written: 350
    lines look like table rows, this checker was examining 110 of them, and it
    printed `OK`. THIRTY-ONE PERCENT COVERAGE, REPORTED AS A PASS. The cause
    was three unresolved `<<<<<<<`/`=======`/`>>>>>>>` markers committed to
    origin/main on 2026-09-11 -- after which no header+separator pair occurs
    again, so `blocks()` yields nothing for the remainder of the file.

    Second instance of that shape found the same night in a different tool
    (`gate_column_check.py`, reading 4% of its subject), which is why the
    disclosure is a first-class output here rather than a comment.

    So: a checker that cannot see part of its subject must SAY SO. See
    docs/SAIRN-PROCESS-RULES.md section 1.7 -- a scan that covered 31% and
    reports "clean" is a wrong answer, not a partial one.

    Two kinds, because they need different repairs:
      conflict  an unresolved VCS marker. Resolve it; both sides are real.
      orphan    a line starting with `|` that is inside no table. Usually a row
                split across two lines by a newline inside a code span, which
                also breaks rendering.
    """
    with io.open(_resolve(path), encoding='utf-8') as fh:
        lines = fh.read().split('\n')
    covered = set()
    for header, body in blocks(lines):
        covered.add(header)
        covered.update(body)
    out = []
    for i, line in enumerate(lines):
        if CONFLICT.match(line):
            out.append((i + 1, 'conflict', line))
        elif is_row(line) and i not in covered and not SEPARATOR.match(line):
            out.append((i + 1, 'orphan', line))
    return out


def coverage(path):
    """(rows_checked, rows_that_look_like_rows) -- the honest denominator."""
    with io.open(_resolve(path), encoding='utf-8') as fh:
        lines = fh.read().split('\n')
    # The header counts as checked -- it is what every body row is measured
    # against. Omitting it made a clean file report "4/5 rows checked", which
    # reads as an unread remainder that does not exist.
    checked = sum(1 + len(body) for _, body in blocks(lines))
    looks = sum(1 for l in lines if is_row(l) and not SEPARATOR.match(l))
    return checked, looks


def main(argv):
    files = [a for a in argv if not a.startswith('--')] or DEFAULT_FILES
    total = 0
    unseen = 0
    for path in files:
        bad = scan(path)
        for line_no, got, want, text in bad:
            print('%s:%d  %d cells, header says %d  %s'
                  % (path, line_no, got, want, text[:90]))
        orph = orphans(path)
        for line_no, kind, text in orph:
            print('%s:%d  %-8s %s' % (path, line_no, kind.upper(), text[:90]))
        checked, looks = coverage(path)
        total += len(bad)
        unseen += len(orph)
        if not bad and not orph:
            print('%s: OK  (%d/%d rows checked)' % (path, checked, looks))
        else:
            # Never print a bare pass beside an unread remainder.
            print('%s: %d malformed, %d unreadable  (%d/%d rows checked)'
                  % (path, len(bad), len(orph), checked, looks))
    print('TOTAL_MALFORMED_ROWS:%d' % total)
    print('TOTAL_UNCHECKABLE_LINES:%d' % unseen)
    return 1 if (total or unseen) else 0


if __name__ == '__main__':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.exit(main(sys.argv[1:]))
