"""Every vertical on this platform must carry a criticality tier.

    python tools/criticality_tier_check.py            # report, exit 1 on drift
    python tools/criticality_tier_check.py --quiet    # exit code only

WHY THIS EXISTS. `docs/CRITICALITY-TIERS.md` states, for each vertical, the WORST
CONSEQUENCE of it being wrong -- and cites something already recorded in this
repo as the evidence. It is the third of the three standing disciplines for
vertical work, alongside the SOUP register and the traceability matrix.

A register maintained by remembering goes stale, and this repo has that written
down in more places than anyone would like: the Guardian App File Map was wrong
seven times, the skill counts drifted three ways inside one file, and the
cleanup files' NOT RUN labels were wrong on at least six. So the register is
DERIVED-CHECKED rather than trusted.

IT REPORTS AND NEVER REWRITES, deliberately, and this is the whole design.
The tier and the sentence explaining it are a JUDGEMENT. A tool that
regenerated this file would delete exactly the part that matters and leave a
table that looks authoritative because it is machine-produced. Same reasoning
as tools/soup_register_check.py and tools/sairn_app_map_check.py.

WHAT IT CAN AND CANNOT SEE, said plainly because a checker that overstates its
reach is worse than none:

  IT CAN SEE        a vertical on disk with no row; a row naming a file that is
                    gone; a row with no tier; a tier outside the A/B/C/UNTIERED
                    vocabulary; an UNTIERED row that does not say what would
                    settle it; a row with an empty evidence cell.

  IT CANNOT SEE     whether a tier is RIGHT. Nothing mechanical can. That is
                    what the evidence column is for, and why every cell names a
                    source a reader can go and check instead of trusting this.
"""
import io
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTER = os.path.join(REPO, 'docs', 'CRITICALITY-TIERS.md')

# NOT A VERTICAL, and named here rather than filtered silently. piac.html is a
# 138 KB saved copy of an Indiana Department of Health 404 page, untracked at the
# repo root since 2026-08-28, with its own open-work row. A checker that quietly
# skipped it would hide the fact that something non-app is sitting in the app
# directory -- so the exclusion is declared, with its reason, and reported.
NOT_A_VERTICAL = {
    'piac.html': 'a saved 404 page, untracked since 2026-08-28; it has its own '
                 'open-work row and is not a product',
}

VALID_TIERS = ('A', 'B', 'C', 'UNTIERED')


def verticals_on_disk():
    """Root *.html files. The app IS the file on this platform -- see
    sairn-software-architect: single HTML file, inline CSS/JS, one per app."""
    return sorted(f for f in os.listdir(REPO)
                  if f.endswith('.html') and os.path.isfile(os.path.join(REPO, f)))


def cells(line):
    """Split a markdown row, honouring an escaped pipe as CONTENT.

    Not cosmetic: this repo has a standing rule about it. A cell whose prose
    contains a pipe -- a regex alternation, a `||` in a code span -- adds
    separators nobody intended, and splitting naively reads the wrong column.
    """
    out, cur, i, bs = [], '', 0, chr(92)
    while i < len(line):
        if line[i] == bs and i + 1 < len(line) and line[i + 1] == '|':
            cur += '|'
            i += 2
            continue
        if line[i] == '|':
            out.append(cur.strip())
            cur = ''
            i += 1
            continue
        cur += line[i]
        i += 1
    out.append(cur.strip())
    return [c for c in out[1:-1]] if len(out) >= 2 else []


def register_rows():
    """(file, tier, consequence, evidence) for each row of the register table.

    Anchored on a row whose FIRST cell is a backticked .html name, so the tier
    LEGEND table above it -- which has the same column count -- cannot be read
    as register rows. Counting columns alone would have swallowed it.
    """
    try:
        src = io.open(REGISTER, encoding='utf-8').read()
    except IOError:
        return None
    rows = []
    for line in src.split('\n'):
        if not line.startswith('|'):
            continue
        c = cells(line)
        if len(c) != 4:
            continue
        m = re.match(r'^`([\w.-]+\.html)`$', c[0])
        if not m:
            continue
        rows.append((m.group(1), re.sub(r'[*`]', '', c[1]).strip(), c[2], c[3]))
    return rows


def main(argv):
    quiet = '--quiet' in argv
    problems = []
    notes = []

    rows = register_rows()
    if rows is None:
        print('docs/CRITICALITY-TIERS.md is missing or unreadable -- that is the '
              'finding, not a reason to pass.')
        return 1

    listed = {r[0] for r in rows}
    on_disk = set(verticals_on_disk())

    for f in sorted(on_disk - listed):
        if f in NOT_A_VERTICAL:
            notes.append('EXCLUDED   %s -- %s' % (f, NOT_A_VERTICAL[f]))
            continue
        problems.append('NO TIER    %s is on disk and has no row. A vertical with no '
                        'stated worst case is one nobody has decided about.' % f)

    for f in sorted(listed - on_disk):
        problems.append('GONE       %s has a row and is not on disk. Either it was '
                        'removed and the row should go, or it moved and the row is '
                        'now pointing at nothing.' % f)

    for f in sorted(listed & on_disk):
        if f in NOT_A_VERTICAL:
            problems.append('EXCLUDED-BUT-LISTED  %s is declared not-a-vertical and '
                            'also has a row. One of the two is wrong.' % f)

    for f, tier, consequence, evidence in rows:
        if tier not in VALID_TIERS:
            problems.append('BAD TIER   %s has tier %r, which is not one of %s'
                            % (f, tier, '/'.join(VALID_TIERS)))
        if not consequence:
            problems.append('NO WORST CASE  %s states no consequence' % f)
        if not evidence:
            problems.append('NO EVIDENCE    %s states a tier with nothing to check it '
                            'against -- that is a label, not a tier.' % f)
        # AN UNTIERED ROW MUST SAY WHAT WOULD SETTLE IT. Otherwise "UNTIERED" is
        # just a permanent shrug, and the point of writing an open question down
        # is that somebody can close it.
        if tier == 'UNTIERED' and 'ettles' not in evidence:
            problems.append('OPEN WITH NO EXIT  %s is UNTIERED and does not say what '
                            'would settle it.' % f)

    if not quiet:
        for n in notes:
            print(n)
        for p in problems:
            print(p)
        print('')
        print('VERTICALS_ON_DISK:%d' % len(on_disk))
        print('ROWS_IN_REGISTER:%d' % len(rows))
        print('TIER_A:%d' % sum(1 for r in rows if r[1] == 'A'))
        print('UNTIERED:%d' % sum(1 for r in rows if r[1] == 'UNTIERED'))
        print('PROBLEMS:%d' % len(problems))
        if not problems:
            print('')
            print('NOTE: this says every vertical HAS a tier with evidence attached. '
                  'It does not say the tier is right -- nothing mechanical can. Read '
                  'the evidence column against its source.')
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
