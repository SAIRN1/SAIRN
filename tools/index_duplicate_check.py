"""Are two rows of the open-work index about the same thing?

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

Usage:
    python tools/index_duplicate_check.py
    python tools/index_duplicate_check.py --json

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


def rows():
    out = []
    for n, line in enumerate(io.open(INDEX, encoding='utf-8'), 1):
        if not line.startswith('|'):
            continue
        cells = line.rstrip('\n').split('|')
        if len(cells) < 5:
            continue
        app, item = cells[1].strip(), cells[2].strip()
        if app in ('App', '---') or set(app) <= set('- '):
            continue
        norm = normalise(item)
        if len(norm) < 25:
            continue                          # too short to compare meaningfully
        out.append({'line': n, 'app': app, 'item': item, 'norm': norm,
                    'status': cells[3].strip() if len(cells) > 3 else ''})
    return out


def main(argv):
    if not os.path.exists(INDEX):
        print('%s is missing. NOT a pass -- nothing was checked.' % INDEX)
        return 2
    rs = rows()
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
        print('\n  NOTE: numbers are stripped before comparing, on purpose -- a count'
              ' that has')
        print('  moved is the commonest way one subject becomes two rows. This does NOT'
              ' check')
        print('  whether a unique row\'s own number is stale; see the module docstring.')

    return 1 if undeclared else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
