r"""Are two rows of the open-work index about the same thing?

WHY. docs/SAIRN-OPEN-WORK-INDEX.md is the file every session reads to choose
work, and four sessions in four clones append to it. On 2026-09-11 it carried
TWO rows for one subject: "56 TIER A resources have no removal path" and "53
TIER A resources have no removal path (was 56)". Both open, both unassigned,
both citing the same command. The tool itself answers 53 -- verified by running
it, not by trusting either row -- so a session reading the first one would have
taken a stale count as current and, worse, could have picked up work another row
already records as underway.

THAT IS THE CLAIMS PROBLEM AT THE DOCUMENT LEVEL. tools/sairn_claim.py stops two
sessions doing the same work; nothing stopped the index describing the same work
twice. A duplicate row is not untidy, it is a second answer to "what needs
doing", and the reader has no way to tell which one is current.

WHAT IT DOES. Normalises each row's ITEM cell -- markup, entities, digits and
dates removed -- and reports pairs that are near-identical. Digits are dropped
on purpose: "56 TIER A resources" and "53 TIER A resources" are the same subject
with a moving count, and a comparison that kept the numbers would have missed
the exact case that prompted this.

REPORT ONLY, AND A MATCH IS A QUESTION, NOT A VERDICT. Two rows can legitimately
share a subject -- a finding and its follow-up, the same defect in two apps. Those
are declared in ACCEPTED below with a reason each, the same two-list discipline
as every other checker here: an exclusion is a decision with a reason beside it,
never a silence.

WHAT IT CANNOT SEE, said here rather than discovered later:
  * two rows about one subject written in genuinely different words. This is a
    similarity check, not a semantic one;
  * a row whose stated NUMBER has gone stale while its subject is unique. That
    needs re-running the tool each row cites and comparing, which is a different
    and much more expensive tool -- deliberately not attempted here rather than
    half-done;
  * rows in any other document.

A ROW THIS TOOL CANNOT PARSE IS NOT A ROW IT CLEARED (cc b17, 2026-10-19).
`rows()` did `line.split('|')`, which cuts a cell at an ESCAPED pipe as
readily as at a real delimiter -- and `\|` is the only way to put a pipe
inside a cell, so the rows using it are exactly the ones about `||` operators
and shell pipelines. MEASURED on the live index before the fix: 855 table
rows, **41 of them split into the wrong number of columns**, of which the APP
cell was wrong on 0, the STATUS cell on 2, and the ITEM cell on ONE --
line 645, whose item came out as the seven characters ``**`(x \`` and was
then dropped by the `len(norm) < 25` guard. **One row of the index was
invisible to this check and nothing said so.** The split is pipe-aware now,
and every row dropped for any reason is COUNTED in the output, because a
silent exclusion is the failure this tool exists to prevent one document
layer up.

Usage:
    python tools/index_duplicate_check.py
    python tools/index_duplicate_check.py --json
    python tools/index_duplicate_check.py --fixtures   # the criteria lock

Exit 0 clean, 1 when an undeclared near-duplicate pair exists, 2 when the index
could not be read -- which is not a pass.
"""
import difflib
import io
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(REPO, 'docs', 'SAIRN-OPEN-WORK-INDEX.md')
THRESHOLD = 0.92
CRITERIA_VERSION = '2026-10-19.1'

# Declared pairs, each with a reason. Keyed on the normalised item text of both
# rows so a reworded row stops matching the exception and is reported again.
ACCEPTED = {}


def normalise(cell):
    t = cell
    t = re.sub(r'&[a-z]+;', ' ', t)          # &mdash; &amp; and friends
    t = re.sub(r'<[^>]+>', ' ', t)           # <br>, <sup>
    t = re.sub(r'[*~`_]', '', t)             # markdown emphasis and strikethrough
    t = re.sub(r'\d{4}-\d{2}-\d{2}', ' ', t)  # dates
    t = re.sub(r'\d+', ' ', t)               # ANY number -- see the docstring
    t = re.sub(r'[^a-z ]', ' ', t.lower())
    return ' '.join(t.split())


BS = chr(92)


def split_cells(line):
    """Split a table row on UNESCAPED pipes, and unescape the rest.

    `line.split('|')` cannot tell a delimiter from `\\|`, which is the only
    way markdown lets a pipe into a cell -- so the rows it mis-split were
    precisely the rows about `||` operators. See the module docstring for the
    measured before-and-after.
    """
    cells, cur, i = [], [], 0
    s = line.rstrip('\n')
    while i < len(s):
        if s[i] == BS and i + 1 < len(s) and s[i + 1] == '|':
            cur.append('|')                   # an escaped pipe is CONTENT
            i += 2
            continue
        if s[i] == '|':
            cells.append(''.join(cur))
            cur = []
            i += 1
            continue
        cur.append(s[i])
        i += 1
    cells.append(''.join(cur))
    return cells


def rows(skipped=None):
    """The comparable rows. `skipped` collects what was left out and WHY --
    passed in rather than printed here so the caller reports it."""
    out = []
    for n, line in enumerate(io.open(INDEX, encoding='utf-8'), 1):
        if not line.startswith('|'):
            continue
        cells = split_cells(line)
        if len(cells) < 5:
            if skipped is not None:
                skipped.append((n, 'fewer than 5 columns (%d)' % len(cells)))
            continue
        app, item = cells[1].strip(), cells[2].strip()
        if app in ('App', '---') or set(app) <= set('- '):
            continue                          # header or rule, not a row
        norm = normalise(item)
        if len(norm) < 25:
            # NOT SILENT ANY MORE. Line 645 landed here with a 7-character
            # item because the naive split cut it at an escaped pipe, and the
            # row vanished from the comparison with no output at all.
            if skipped is not None:
                skipped.append((n, 'item normalises to %d character(s), under '
                                   'the 25 needed to compare: %r'
                                % (len(norm), item[:60])))
            continue
        out.append({'line': n, 'app': app, 'item': item, 'norm': norm,
                    'status': cells[3].strip() if len(cells) > 3 else ''})
    return out


# ── THE CRITERIA LOCK, BOTH DIRECTIONS ─────────────────────────────────────
def run_fixtures():
    print('INDEX DUPLICATE CHECK -- criteria lock %s' % CRITERIA_VERSION)
    bad = total = 0

    def check(name, got, want):
        nonlocal bad, total
        total += 1
        ok = (got == want)
        if not ok:
            bad += 1
        print('  %s %-62s got %r' % ('ok  ' if ok else 'FAIL', name, got))

    check('a plain row splits into its real columns',
          len(split_cells('| a | b | c |')), 5)
    check('...and the cell contents survive',
          [c.strip() for c in split_cells('| a | b | c |')],
          ['', 'a', 'b', 'c', ''])
    esc = '| a | x ' + BS + '| y | c |'
    check('AN ESCAPED PIPE IS CONTENT, not a delimiter -- the defect',
          len(split_cells(esc)), 5)
    check('...and it is UNESCAPED in the cell, so the backslash does not reach '
          'the comparison', split_cells(esc)[2].strip(), 'x | y')
    check('ABLATION: the naive split reads that same row as SIX columns, which '
          'is how one row went missing', len(esc.split('|')), 6)
    check('ABLATION CONTROL: the naive split is RIGHT about a row with no '
          'escaped pipe -- it only ever failed on the escaped ones',
          len('| a | b | c |'.split('|')), 5)
    dbl = '| a | `(x ' + BS + '|' + BS + '| 0)` is wrong | c |'
    check('two escaped pipes in one cell stay in one cell',
          len(split_cells(dbl)), 5)
    check('...and render as the operator the row is about',
          '(x || 0)' in split_cells(dbl)[2], True)
    check('a trailing backslash is not treated as an escape, and does not '
          'crash', len(split_cells('| a | b ' + BS)), 3)
    check('a cell that is ONLY an escaped pipe is one non-empty cell',
          split_cells('| ' + BS + '| |')[1].strip(), '|')

    # ── THE REAL ROW, PINNED (cc b18 item 3) ──────────────────────────────
    # Every fixture above is synthetic, which is right -- they keep meaning the
    # same thing when the index changes. But the defect had ONE live instance,
    # index line 645, and a synthetic fixture cannot prove THAT row parses. So
    # its opening is pinned here verbatim: if the split ever regresses, this arm
    # names the row a reader can go and look at instead of an invented one.
    REAL_645 = ('| **Platform** | **`(x ' + BS + '|' + BS + '| 0)`** in a '
                'numeric fold CONCATENATES a string instead of adding it** '
                '&mdash; made mechanical | **BUILT** | cc | - | - | - |')
    cells = split_cells(REAL_645)
    check('THE REAL ROW: index line 645 parses into its 7 columns plus two '
          'edges', len(cells), 9)
    check('...and its ITEM cell is the whole item, not the seven characters '
          'the naive split left (`**`(x ' + BS + '`)',
          cells[2].strip().startswith('**`(x || 0)`** in a numeric fold'), True)
    check('ABLATION on the real row: the naive split reads it as ELEVEN '
          'cells, which is how its item became 7 characters and the row '
          'vanished from the comparison', len(REAL_645.split('|')), 11)
    check('...and the naive split\'s item cell really is that short, measured '
          'rather than asserted',
          len(REAL_645.split('|')[2].strip()) < 12, True)

    print('  %d/%d fixtures classify correctly' % (total - bad, total))
    return 1 if bad else 0


def main(argv):
    if '--fixtures' in argv or '--selftest' in argv:
        return run_fixtures()
    if not os.path.exists(INDEX):
        print('%s is missing. NOT a pass -- nothing was checked.' % INDEX)
        return 2
    # THE LOCK FIRST: a parser whose own criteria are broken reports a clean
    # index it never read correctly, which is the defect this batch fixed.
    if run_fixtures() != 0:
        print('')
        print('COULD NOT RUN: the criteria lock failed, so no verdict about '
              'the index is trustworthy.')
        return 2
    print('')
    skipped = []
    rs = rows(skipped)
    pairs = []
    for i in range(len(rs)):
        for j in range(i + 1, len(rs)):
            a, b = rs[i], rs[j]
            if a['app'] != b['app']:
                continue                      # same subject, different app is normal
            ratio = difflib.SequenceMatcher(None, a['norm'], b['norm']).ratio()
            if ratio < THRESHOLD:
                continue
            key = tuple(sorted((a['norm'], b['norm'])))
            pairs.append({'a_line': a['line'], 'b_line': b['line'], 'app': a['app'],
                          'ratio': round(ratio, 3), 'declared': key in ACCEPTED,
                          'a_item': a['item'][:110], 'b_item': b['item'][:110],
                          'a_status': a['status'][:70], 'b_status': b['status'][:70]})

    undeclared = [p for p in pairs if not p['declared']]

    if '--json' in argv:
        print(json.dumps(pairs, indent=1))
    else:
        print('INDEX DUPLICATE CHECK -- report only, nothing was written')
        print('  rows compared            : %d' % len(rs))
        print('  rows NOT compared        : %d  (listed below -- a row this '
              'tool skipped is NOT a row it cleared)' % len(skipped))
        print('  near-duplicate pairs     : %d  (same app, >= %.2f similar with '
              'numbers removed)' % (len(pairs), THRESHOLD))
        print('  UNDECLARED               : %d' % len(undeclared))
        for p in undeclared:
            print('\n  %s -- lines %d and %d, similarity %.3f'
                  % (p['app'], p['a_line'], p['b_line'], p['ratio']))
            print('      %d: %s' % (p['a_line'], p['a_item']))
            print('         status: %s' % p['a_status'])
            print('      %d: %s' % (p['b_line'], p['b_item']))
            print('         status: %s' % p['b_status'])
            print('      Two rows, one subject. A reader has no way to tell which is'
                  ' current.')
        if skipped:
            print('\n  ROWS NOT COMPARED, each with its reason:')
            for n, why in skipped:
                print('      line %-5d %s' % (n, why))
        print('\n  NOTE: numbers are stripped before comparing, on purpose -- a count'
              ' that has')
        print('  moved is the commonest way one subject becomes two rows. This does NOT'
              ' check')
        print('  whether a unique row\'s own number is stale; see the module docstring.')

    return 1 if undeclared else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
