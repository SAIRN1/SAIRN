#!/usr/bin/env python
"""A digest is 150 words or fewer and carries all six fields. Nothing else.

    python tools/digest_lint.py SAIRN-digest-cc-b5.txt
    python tools/digest_lint.py --fixtures      # the criteria lock

Exit 0 clean, 1 findings, 2 COULD NOT RUN.

── WHY, AND IT IS MEASURED ─────────────────────────────────────────────────
cc's b4 digest was 15,412 bytes. A digest that long is a second report, and the
thing it was for -- one screen a coordinating session can act on -- stops
existing the moment it does not fit on one. Michael named the number: 150
words, six fields, run before upload.

THE SIX FIELDS ARE THE SCHEMA AND THEY ARE NOT NEGOTIABLE HERE. Each exists
because a digest that omitted it cost somebody a read of the full report:

  STATUS           did the batch land, and where is HEAD
  DECISION-NEEDED  what only Michael can answer. "none" is a real answer and
                   must be written, because an ABSENT field and "nothing is
                   blocked" are different facts
  CHANGED          what moved, with the commit
  EVIDENCE-path    where to look. A digest that asserts without a path is a
                   claim, and this platform's whole discipline is that a claim
                   is not a fact until somebody can re-run it
  UNVERIFIED       what was NOT proven. The field exists so "everything
                   passed" cannot be written by omission
  NEXT             the next action, so the next session does not re-derive it

── WHAT THIS DOES NOT CHECK, SAID OUT LOUD ─────────────────────────────────
Whether the content is TRUE. It counts words and looks for six labels. A digest
that passes this lint can still be wrong about every figure in it, and a
session that reads a green lint as a verified digest has made the same mistake
this repo keeps recording -- a check that passed is not a subject that is
correct.

── THE WORD COUNT IS DEFINED, NOT ASSUMED ──────────────────────────────────
Whitespace-separated tokens over the WHOLE file, field labels included. Two
alternatives were considered and rejected: excluding the labels (a session
would pad the labels), and counting only prose lines (the definition of a prose
line is a second thing to argue about). The crude definition is the one nobody
can game accidentally, and 150 is generous under it.
"""
import io
import os
import re
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)
try:
    from checker_kit import EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN
except Exception:                                                # noqa: BLE001
    EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN = 0, 1, 2

CRITERIA_VERSION = '2026-10-13.1'
MAX_WORDS = 150

# Matched at a line start, case-insensitively, with or without a trailing
# colon. A field is a LABEL somebody wrote on purpose -- not a word that
# happens to appear in a sentence -- which is why the anchor is the line start
# and not a substring search. `STATUS` inside "the STATUS of the gate" must not
# satisfy the schema.
FIELDS = ('STATUS', 'DECISION-NEEDED', 'CHANGED', 'EVIDENCE-path',
          'UNVERIFIED', 'NEXT')


def field_re(name):
    return re.compile(r'(?mi)^\s*%s\s*:?' % re.escape(name))


def words(text):
    return [w for w in re.split(r'\s+', text) if w]


def lint(text):
    """-> list of finding strings. Empty means clean."""
    out = []
    n = len(words(text))
    if n > MAX_WORDS:
        out.append('%d words, and the ceiling is %d. A digest that does not '
                   'fit on one screen is a second report, which is the thing '
                   'it exists instead of.' % (n, MAX_WORDS))
    missing = [f for f in FIELDS if not field_re(f).search(text)]
    if missing:
        out.append('missing field(s): %s. Each must appear as a LABEL at the '
                   'start of a line. "none" is a real value and must be '
                   'written -- an absent field and "nothing to report" are '
                   'different facts.' % ', '.join(missing))
    return out


# ── THE CRITERIA LOCK ───────────────────────────────────────────────────────
# Locked against synthetic fixtures before the tool is pointed at a real
# digest, per the first cross-domain discipline. Both directions: a digest that
# must pass and five that must each fail for ONE named reason, so a change that
# breaks one rule cannot hide behind another.
_GOOD = """STATUS: landed at abc1234, ahead 0 behind 0.
DECISION-NEEDED: none.
CHANGED: one gate, one probe.
EVIDENCE-path: docs/x.md
UNVERIFIED: the live deploy.
NEXT: release the claim.
"""

FIXTURES = (
    ('a short digest with all six fields', _GOOD, 0),
    ('one missing field', _GOOD.replace('UNVERIFIED: the live deploy.\n', ''), 1),
    ('a field named only INSIDE a sentence, never as a label',
     _GOOD.replace('UNVERIFIED: the live deploy.\n',
                   'and the UNVERIFIED part was the deploy.\n'), 1),
    ('over the word ceiling', _GOOD + ('filler ' * (MAX_WORDS + 10)), 1),
    ('over the ceiling AND missing a field',
     _GOOD.replace('NEXT: release the claim.\n', '')
     + ('filler ' * (MAX_WORDS + 10)), 1),
    ('exactly at the ceiling is CLEAN -- the boundary is <=, not <',
     'STATUS: x\nDECISION-NEEDED: x\nCHANGED: x\nEVIDENCE-path: x\n'
     'UNVERIFIED: x\nNEXT: x\n' + ('w ' * (MAX_WORDS - 12)), 0),
)


def run_fixtures():
    bad = 0
    print('DIGEST LINT -- criteria lock %s' % CRITERIA_VERSION)
    for name, text, want_findings in FIXTURES:
        got = lint(text)
        hit = 1 if got else 0
        mark = 'ok  ' if hit == want_findings else 'FAIL'
        if hit != want_findings:
            bad += 1
        print('  %s %-62s words=%d findings=%d'
              % (mark, name, len(words(text)), len(got)))
        if hit != want_findings:
            for g in got:
                print('         got: %s' % g[:120])
    print('  %d/%d fixtures classify correctly' % (len(FIXTURES) - bad,
                                                   len(FIXTURES)))
    return EXIT_FINDING if bad else EXIT_CLEAN


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if '--fixtures' in argv:
        return run_fixtures()
    paths = [a for a in argv if not a.startswith('-')]
    if not paths:
        print('COULD NOT RUN: no digest given. Nothing was checked.')
        print('usage: python tools/digest_lint.py <digest.txt> [...]')
        print('       python tools/digest_lint.py --fixtures')
        return EXIT_COULD_NOT_RUN

    # THE LOCK RUNS FIRST, EVERY TIME. A lint whose own criteria are broken
    # reports a pass it never performed, and that is cheaper to catch here than
    # in the digest somebody then uploads.
    if run_fixtures() != EXIT_CLEAN:
        print('\nCOULD NOT RUN: the criteria lock itself failed, so no verdict '
              'about a real digest is trustworthy. Nothing was checked.')
        return EXIT_COULD_NOT_RUN

    rc = EXIT_CLEAN
    for p in paths:
        if not os.path.isfile(p):
            print('\nCOULD NOT RUN: %s does not exist.' % p)
            rc = EXIT_COULD_NOT_RUN
            continue
        text = io.open(p, encoding='utf-8', errors='replace').read()
        findings = lint(text)
        print('\n%s -- %d word(s)' % (p, len(words(text))))
        if not findings:
            print('  CLEAN: %d words or fewer, all six fields present.'
                  % MAX_WORDS)
            print('  NOT a statement that the digest is CORRECT. This counts '
                  'words and finds labels.')
            continue
        for f in findings:
            print('  ! %s' % f)
        if rc == EXIT_CLEAN:
            rc = EXIT_FINDING
    return rc


if __name__ == '__main__':
    sys.exit(main())
