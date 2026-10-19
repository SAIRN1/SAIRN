#!/usr/bin/env python
# OWNER: cody
# written 2026-10-19, batch b23, item 4
r"""SWEEP: which test files assert on SOURCE TEXT without stripping comments?

    python docs/b23-logs/green_but_worthless_sweep.py            # cody's files
    python docs/b23-logs/green_but_worthless_sweep.py --all       # every file
    python docs/b23-logs/green_but_worthless_sweep.py --json

Exit 0 no candidate found in scope, 1 candidates found, 2 COULD NOT RUN.

── THE SHAPE BEING SWEPT FOR, AND WHY A SWEEP RATHER THAN A READ ──────────
An assertion whose SUBJECT is the text of an application file -- `html`,
`src`, a function body sliced out of one -- and whose test is a substring or a
regex over that text WITHOUT first removing comments and string literals. Such
an assertion is satisfied by any prose that happens to contain the spelling,
including a comment explaining that the code used to do the thing being
asserted. It passes. It tests nothing. And nothing about reading it reveals
that, which is the whole reason this is a sweep and not a code review:

  b17   `key==='bld_bids'` satisfied by a COMMENT inside the function under
        test, which said the code "used to read" exactly that
  b27   a fourth argument satisfied by a BLOCK comment, after a repair that
        stripped only line comments
  b28   BLD_PENDING_TRACKED satisfied by a LINE comment (N1) and the retry
        guard by a BLOCK comment (N4) -- routed HIGH, fixed in b23
  b22   P5 in tests/sd_data_not_provisioned_misclass.js satisfied by hank's
        explanatory comment naming notProvisioned() after the call was
        reverted; and B6 in tests/sairnfreedom_tax_entity_facts.js satisfied
        by a CONSTANT's `note` field after the disclosure it checked was
        deleted. Both found by ablation, both in the same batch

── WHAT THIS TOOL DOES AND DOES NOT CLAIM ─────────────────────────────────
IT REPORTS CANDIDATES. It cannot tell a real hole from an assertion whose
subject genuinely IS the file's prose -- a doc-comment check, a disclosure
requirement, a licence header -- and several of those exist in this repo and
are correct. So every candidate needs a read, and a confirmed one needs an
ABLATION, which is the only thing that settles it. The counts below are a
work-list, never a defect count.

IT ALSO CANNOT SEE the inverse defect: an assertion that strips comments
correctly and still checks the wrong property. b22's B6 stripped nothing but
would not have been caught by this sweep either, because its subject was a
CONSTANT'S FIELD rather than a comment -- real executable data carrying prose.
That class is named here and NOT detected, because detecting it needs the
value flow, not the text.

OWNERSHIP IS DERIVED FROM COMMIT SUBJECTS, not from an OWNER header: 26 of
617 test files carry one, and every commit on this repo is authored by the
same git identity, so the session is only recoverable from what the commit
said about itself.
"""
import io
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
TESTS = os.path.join(REPO, 'tests')

# Reading an application/handler source file at all.
READS_SOURCE = re.compile(
    r"readFileSync\s*\([^)]*\.(?:html|js)['\"]?|"
    r"open\s*\([^)]*\.(?:html|js)['\"]|"
    r"\.read_text\s*\(|io\.open\s*\([^)]*\.(?:html|js)",
    re.I)

# A text assertion over a variable that plausibly holds that source.
TEXT_ASSERT = re.compile(
    r"\b(?:html|src|source|body|code|text|content|branch|slice|snippet|"
    r"[A-Z_]{3,})\s*\.\s*(?:indexOf|includes|match|search)\s*\(|"
    r"\.test\s*\(\s*(?:html|src|source|body|text|content|branch)\b|"
    r"\bin\s+(?:html|src|source|body|text|content|branch)\b")

# Any evidence the file removes comments before asserting.
STRIPS = re.compile(
    r"/\\\*|"                                   # JS: /\* in a regex literal
    r"replace\s*\(\s*/\\?/\\?/|"                # JS: replace(/\/\//
    r"strip_comments|stripComments|no_?comments|noComments|"
    r"code\s*\(|struct\s*\(|comment[_-]?strip",
    re.I)


def git(*args):
    r = subprocess.run(('git',) + args, cwd=REPO, capture_output=True,
                       text=True, encoding='utf-8', errors='replace')
    return r.stdout if r.returncode == 0 else ''


def attribution(rel):
    """Sessions named in the commit subjects that touched this file."""
    subjects = git('log', '--format=%s%n%b', '--', rel).lower()
    found = set()
    for s in ('cody', 'hank', 'fourth', 'cc', 'hover'):
        if re.search(r'\b' + s + r'\b', subjects):
            found.add(s)
    return found


def main():
    if not os.path.isdir(TESTS):
        print('COULD NOT RUN: %s is absent. Nothing was swept.' % TESTS)
        return 2
    everyone = '--all' in sys.argv
    as_json = '--json' in sys.argv

    names = sorted(f for f in os.listdir(TESTS)
                   if f.endswith('.js') or f.endswith('.py'))
    if not names:
        print('COULD NOT RUN: no test files found under tests/. Nothing was '
              'swept -- an empty sweep is not a clean one.')
        return 2

    scanned = 0
    candidates = []
    for f in names:
        p = os.path.join(TESTS, f)
        try:
            s = io.open(p, encoding='utf-8', errors='replace').read()
        except OSError:
            continue
        scanned += 1
        if not READS_SOURCE.search(s):
            continue
        hits = TEXT_ASSERT.findall(s)
        if not hits:
            continue
        if STRIPS.search(s):
            continue
        rel = 'tests/' + f
        who = attribution(rel)
        candidates.append({
            'file': rel,
            'text_assertions': len(hits),
            'sessions': sorted(who),
            'mine': 'cody' in who,
        })

    scope = [c for c in candidates if c['mine']] if not everyone else candidates

    if as_json:
        print(json.dumps({'scanned': scanned,
                          'candidates_all': len(candidates),
                          'candidates_in_scope': len(scope),
                          'rows': scope}, indent=2))
        return 1 if scope else 0

    print('GREEN-BUT-WORTHLESS SWEEP -- candidates, never a defect count')
    print('  test files scanned                     : %d' % scanned)
    print('  read an app source AND assert on its text,')
    print('  with NO comment stripping anywhere     : %d' % len(candidates))
    print('  ...of those, attributable to cody      : %d'
          % len([c for c in candidates if c['mine']]))
    print('')
    if not scope:
        print('  No candidate in scope.')
        print('')
        print('  THAT IS NOT "THE SUITES ARE SOUND". This sweep cannot see an')
        print('  assertion that strips comments and still checks the wrong')
        print('  property, and it cannot see b22\'s B6 class at all -- a')
        print('  CONSTANT\'S FIELD carrying prose is real executable data and')
        print('  looks like nothing to a text scanner. Only ablation settles')
        print('  any of this.')
        return 0

    print('  %-52s %5s  %s' % ('file', 'text?', 'sessions'))
    for c in sorted(scope, key=lambda x: -x['text_assertions']):
        print('  %-52s %5d  %s'
              % (c['file'], c['text_assertions'], ','.join(c['sessions'])))
    print('')
    print('  EACH NEEDS A READ, AND A CONFIRMED ONE NEEDS AN ABLATION. A')
    print('  candidate is not a finding: an assertion whose subject genuinely')
    print('  IS the file\'s prose -- a disclosure requirement, a doc-comment')
    print('  rule -- is correct as written and several exist in this repo.')
    return 1


if __name__ == '__main__':
    sys.exit(main())
