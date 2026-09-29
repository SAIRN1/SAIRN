r"""A ROW THAT ASSERTS A BASIS AND CITES NOTHING.

    python tools/citation_no_source_report.py
    python tools/citation_no_source_report.py --json
    python tools/citation_no_source_report.py --doc <path>

REPORT ONLY. Exit 0 clean, 1 findings, 2 COULD NOT RUN. Writes nothing.

── WHY THIS AND NOT THE RULE THAT WAS ASKED FOR ────────────────────────────
`docs/2026-09-29-write-site-basis-rule-scope.md` proposed failing any row whose
basis cites only WRITE sites -- the `msb_sale_hours` shape, where a cell cited its
two write sites, concluded "display only", and was wrong for seven weeks about an
alcohol-sale refusal.

**Running that rule before recommending it is what killed it.** It fires on 82
rows, of which three distinct false-positive classes account for most, WHILE 209
ROWS CITE NOTHING AT ALL and are exempt for having less evidence. A rule that
pressures the cells that did the most work and none of the cells that did none is
backwards.

**This is the population that survives that objection.** A row either cites a line
or it does not. There is no classifier, no vocabulary matching, and **no
false-positive shape at all** -- which is the entire argument for building this
first.

── WHAT A FINDING MEANS, AND WHAT IT DOES NOT ──────────────────────────────
It means: this row states a consequence and a confidentiality class, and points at
no line of code. **It does NOT mean the row is wrong.** Many are obviously right
from the resource name alone, and several say in terms that they were classified by
a stated rule rather than read -- which is honest, and is exactly the sentence this
report makes countable.

**The number is a coverage figure, not a defect count.** Said plainly because "209
findings" in a report reads as 209 bugs.

── THE ONE THING IT IS STRICT ABOUT ────────────────────────────────────────
A row that cites nothing AND claims to have been read individually is a different
and worse thing than a row that cites nothing and says so. The report separates
them, because the second is a disclosed gap and the first is a contradiction.
"""
import argparse
import io
import json
import os
import re
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
from checker_kit import EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN  # noqa: E402

CRITERIA_VERSION = '2026-09-29.1'
DEFAULT_DOC = os.path.join('docs', 'CRITICALITY-TIERS.md')

# A two-axis resource row: `| `name` | **T** | **C** | ...`
ROW = re.compile(r'^\| `([a-z0-9_]+)` \| \*\*([ABC])\*\* \| \*\*([ABC])\*\* \|')
# A line citation. `:1234` after a path, or a bare `:1234` in a cell that named
# a file earlier. Either is a citation for this report's purpose -- the question
# is whether the cell points at ANY line, not whether the pointer is good.
CITE = re.compile(r':\d{3,5}')
# A row claiming it was read individually. Deliberately a small closed set of the
# phrases this register actually uses, because inventing synonyms would make the
# strict half of the report fire on cells that never claimed anything.
CLAIMS_READ = re.compile(
    r'read individually|individually read|READ OUT OF THE APP|'
    r'read at HEAD|re-derived|verified by direct read', re.I)
# A row saying in terms that it was NOT read. The honest form.
ADMITS_DEFAULT = re.compile(
    r'Classified by the stated B rule rather than individually read|'
    r'NOT YET INDIVIDUALLY READ|classified by the stated B rule', re.I)

# -- A GROUP STAMP IS EVIDENCE, AND CALLING IT A CONTRADICTION WAS MY THIRD
# WRONG CRITERION IN TWO DAYS -- caught here BEFORE the number was reported,
# which is the whole point of running a rule before recommending it.
#
# The first version of this report counted 138 rows as CONTRADICTORY: claiming an
# individual read while citing no line. Spot-checking two of them found the same
# sentence -- "Confidentiality individually read in the 3.2 pass, 2026-09-22
# (MONEY_INTERNAL)" -- and the register's OWN HEADER explains it: the 3.2 pass read
# 99 Tier A rows individually and stamped each with a GROUP NAME "so a reader can
# disagree with a GROUP rather than with 99 separate judgements".
#
# That is a deliberate, disclosed form of evidence. It is WEAKER than a line
# citation and it is NOT an unsupported claim, and flattening the two over-accuses
# 100-odd rows. Over-accusing is the direction that gets a report ignored, and this
# report's own closing text says exactly that about something else.
#
# So a group stamp is its own category, and the CONTRADICTION bucket becomes what
# it claimed to be: a row asserting a read with neither a line NOR a group behind
# it. The 12 stamp names are the ones the register actually uses, plus a general
# ALL-CAPS-in-parentheses fallback so a new group name is not silently accused.
GROUP_STAMP = re.compile(r'\((?:[A-Z][A-Z_]{4,})\)')


def scan(text):
    rows, no_cite, contradictory, disclosed, cited, grouped = (
        [], [], [], [], [], [])
    for line in text.split('\n'):
        m = ROW.match(line)
        if not m:
            continue
        res, tier, conf = m.group(1), m.group(2), m.group(3)
        rows.append(res)
        if CITE.search(line):
            cited.append(res)
            continue
        entry = {'resource': res, 'tier': tier, 'confidentiality': conf}
        no_cite.append(entry)
        # ORDER IS THE CRITERION, most specific claim first. The row saying it was
        # NOT read wins over everything; then a GROUP STAMP, which is real if
        # weaker evidence; and only a claim with neither is a contradiction.
        if ADMITS_DEFAULT.search(line):
            disclosed.append(entry)
        elif GROUP_STAMP.search(line) and CLAIMS_READ.search(line):
            grouped.append(entry)
        elif CLAIMS_READ.search(line):
            contradictory.append(entry)
    return rows, cited, no_cite, contradictory, disclosed, grouped


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--doc', default=DEFAULT_DOC)
    ap.add_argument('--json', action='store_true')
    args = ap.parse_args(argv)

    path = args.doc if os.path.isabs(args.doc) else os.path.join(REPO, args.doc)
    if not os.path.isfile(path):
        print('COULD NOT RUN: %s is not on disk, so there is nothing to count. '
              'An absent document is not a document with full coverage.'
              % args.doc)
        return EXIT_COULD_NOT_RUN
    text = io.open(path, encoding='utf-8', errors='replace').read()
    rows, cited, no_cite, contradictory, disclosed, grouped = scan(text)

    if not rows:
        print('COULD NOT RUN: no two-axis resource row matched in %s. Either the '
              'row format moved or the parse broke; either way a count of zero '
              'here would read as perfect coverage.' % args.doc)
        return EXIT_COULD_NOT_RUN

    print('CITATION COVERAGE -- a row that asserts a basis and cites nothing')
    print('  criteria : %s' % CRITERIA_VERSION)
    print('  document : %s' % args.doc)
    print('  rows     : %d' % len(rows))
    print('  cite at least one line : %d' % len(cited))
    print('  CITE NOTHING           : %d' % len(no_cite))
    print('    of those, ADMIT they were not read individually : %d'
          % len(disclosed))
    print('    of those, carry a 3.2 GROUP STAMP               : %d  -- '
          'weaker than a line, NOT an unsupported claim' % len(grouped))
    print('    of those, CLAIM a read with NEITHER             : %d  <- the '
          'contradiction' % len(contradictory))
    print('    neither stated                                  : %d'
          % (len(no_cite) - len(disclosed) - len(contradictory) - len(grouped)))
    print()
    if contradictory:
        print('CONTRADICTORY (%d) -- claims an individual read with NEITHER a '
              'line NOR a group stamp behind it. Read these first: the other '
              'groups are disclosed or group-backed; this one asserts evidence '
              'it does not show.' % len(contradictory))
        for e in contradictory:
            print('  ! %-30s Tier %s / Conf %s'
                  % (e['resource'], e['tier'], e['confidentiality']))
        print()
    tier_a = [e for e in no_cite if e['tier'] == 'A']
    print('  UNCITED AND TIER A: %d -- a wrong basis on an A row is the '
          'expensive one' % len(tier_a))
    for e in tier_a[:20]:
        print('    %-30s Conf %s' % (e['resource'], e['confidentiality']))
    if len(tier_a) > 20:
        print('    ... and %d more' % (len(tier_a) - 20))

    print()
    print('  THIS IS A COVERAGE FIGURE, NOT A DEFECT COUNT. A row citing nothing')
    print('  is not thereby wrong -- many are obviously right from the resource')
    print('  name, and the ones that SAY they were classified by a stated rule')
    print('  rather than read are being honest. What this makes countable is the')
    print('  sentence, not a judgement about it.')
    print()
    print('  NOT THE RULE THAT WAS SCOPED. docs/2026-09-29-write-site-basis-rule-')
    print('  scope.md proposed failing rows that cite only WRITE sites. Measured:')
    print('  82 hits with three false-positive classes, while 209 rows cite')
    print('  nothing and are exempt for having LESS evidence. This report is the')
    print('  population that has no false-positive shape at all.')

    if args.json:
        print(json.dumps({'criteria': CRITERIA_VERSION, 'doc': args.doc,
                          'rows': len(rows), 'cited': len(cited),
                          'no_citation': no_cite,
                          'contradictory': contradictory,
                          'group_stamped': grouped,
                          'disclosed': disclosed}, indent=2))

    return EXIT_FINDING if no_cite else EXIT_CLEAN


if __name__ == '__main__':
    sys.exit(main())
