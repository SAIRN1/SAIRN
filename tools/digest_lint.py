#!/usr/bin/env python
# OWNER: cc
# written 2026-10-13, batch b5, queue item 6
"""A digest is 30 LINES or fewer and carries all six fields. Nothing else.

    python tools/digest_lint.py SAIRN-digest-cc-b5.txt
    python tools/digest_lint.py --fixtures      # the criteria lock

Exit 0 clean, 1 findings, 2 COULD NOT RUN.

── WHY, AND IT IS MEASURED ─────────────────────────────────────────────────
cc's b4 digest was 15,412 bytes. A digest that long is a second report, and the
thing it was for -- one screen a coordinating session can act on -- stops
existing the moment it does not fit on one.

── THE CEILING IS 30 LINES. THE 150-WORD RULE IS RETIRED, 2026-10-20. ──────
MICHAEL'S DECISION: ONE STANDARD, 30 lines, everywhere. It replaces the
150-word ceiling this tool enforced from 2026-10-13, and the retirement is
RECORDED HERE rather than done quietly, because a ceiling that silently
changes is worse than either number.

WHY 150 WORDS HAD TO GO, measured on 2026-10-20 over the newest digest of each
of the four build agents: hank b23 30 lines / 356 words, fourth b38 13 / 541,
cody b26 239 / 2011, cc b27 11 / 596. NOT ONE MET 150 WORDS, and three of the
four were well inside 30 lines. A ceiling nobody has met in months is not a
standard -- it is a line in a tool that every run reports and nobody acts on,
which is the shape this platform calls a check that has stopped testing
anything. Two ceilings disagreeing is worse still: every digest passed one and
failed the other, so neither could be read as a verdict.

AND LINES ARE THE RIGHT UNIT FOR WHAT THE RULE IS FOR. The rule exists so a
digest fits on one screen a coordinating session can act on. A screen is
measured in LINES. 596 words across 11 lines fits; 356 words across 30 lines
fits; 2011 words across 239 lines does not. The word count was a proxy for the
thing, and the thing is directly measurable.

`tools/drive_upload_verify.py --max-lines` enforces the same 30 at the moment
of upload, so the number now lives in two tools that agree instead of two that
did not.

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

── THE LINE COUNT IS DEFINED, NOT ASSUMED ──────────────────────────────────
`splitlines()` over the WHOLE file, field labels included, so A FINAL LINE WITH
NO TRAILING NEWLINE COUNTS. `wc -l` counts newlines and reports one FEWER for
that file; the two differ by exactly one at the boundary, which is the only
place a cap is ever argued about, so the tool says which it used.
`drive_upload_verify.py` counts the same way, deliberately -- two tools with
the same number and different definitions would be the old problem wearing a
new unit.

THE WORD COUNT IS STILL REPORTED AND NO LONGER A FINDING. It is printed beside
the line count because it is free and occasionally tells you something -- a
15-line digest of 2,000 words is a wall of text inside the cap -- but it
cannot fail a digest any more. A number that is informative and a number that
gates are different jobs, and conflating them is what produced two ceilings.
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

CRITERIA_VERSION = '2026-10-20.1'   # 150 words -> 30 lines
MAX_LINES = 30

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
    """Whitespace-separated tokens. REPORTED, never a finding -- see the
    header. Kept because it is free and a wall of text inside the line cap is
    worth seeing."""
    return [w for w in re.split(r'\s+', text) if w]


def lines(text):
    """`splitlines()`, so a final line with no trailing newline COUNTS and
    `wc -l` may report one fewer. Same definition as
    drive_upload_verify.count_lines(), on purpose -- two tools with the same
    number and different definitions would be the old problem in a new unit."""
    return text.splitlines()


def lint(text):
    """-> list of finding strings. Empty means clean."""
    out = []
    n = len(lines(text))
    if n > MAX_LINES:
        out.append('%d lines, and the ceiling is %d -- over by %d. A digest '
                   'that does not fit on one screen is a second report, which '
                   'is the thing it exists instead of. (Counted with '
                   'splitlines, so a final line with no newline counts and '
                   '`wc -l` may say %d.) The content belongs in the report, '
                   'which has no cap for exactly that reason.'
                   % (n, MAX_LINES, n - MAX_LINES, max(0, n - 1)))
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

# `_GOOD` is 6 lines, so padding to EXACTLY MAX_LINES needs MAX_LINES-6 more.
# Derived rather than written out: a hardcoded pad would stop being a boundary
# fixture the day MAX_LINES moved, which is the staleness this repo keeps
# paying for one level up.
_PAD = '\n'.join(['pad'] * (MAX_LINES - 6)) + '\n'

FIXTURES = (
    ('a short digest with all six fields', _GOOD, 0),
    ('one missing field', _GOOD.replace('UNVERIFIED: the live deploy.\n', ''), 1),
    ('a field named only INSIDE a sentence, never as a label',
     _GOOD.replace('UNVERIFIED: the live deploy.\n',
                   'and the UNVERIFIED part was the deploy.\n'), 1),
    ('over the LINE ceiling', _GOOD + _PAD + 'one too many\n', 1),
    ('over the ceiling AND missing a field',
     _GOOD.replace('NEXT: release the claim.\n', '') + _PAD + 'over\n', 1),
    ('EXACTLY at the ceiling is CLEAN -- the boundary is <=, not <',
     _GOOD + _PAD, 0),
    # ── THE RETIREMENT, AS A FIXTURE IN BOTH DIRECTIONS ─────────────────────
    # These two arms are the only MECHANICAL record that the 150-word rule is
    # gone. The first would have failed before 2026-10-20 and must now pass;
    # the second proves the line cap is what bites in its place. A retirement
    # recorded only in prose is a retirement that comes back.
    ('FAR over 150 WORDS but inside 30 lines is CLEAN -- the word ceiling is '
     'RETIRED', _GOOD + ('filler ' * 600) + '\n', 0),
    ('...and the converse: 30 short lines plus one IS a finding, so the line '
     'cap is what bites now', _GOOD + _PAD + 'x\n', 1),
    # A final line with NO trailing newline still counts -- the one place the
    # definition is ever argued about.
    ('a 31st line with NO trailing newline still counts',
     _GOOD + _PAD + 'no newline here', 1),
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
        print('  %s %-76s lines=%-4d words=%-5d findings=%d'
              % (mark, name, len(lines(text)), len(words(text)), len(got)))
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
        print('\n%s -- %d line(s), %d word(s)   [cap is %d LINES; the word '
              'count is REPORTED and is NOT a finding]'
              % (p, len(lines(text)), len(words(text)), MAX_LINES))
        if not findings:
            print('  CLEAN: %d lines or fewer, all six fields present.'
                  % MAX_LINES)
            print('  NOT a statement that the digest is CORRECT. This counts '
                  'lines and finds labels.')
            continue
        for f in findings:
            print('  ! %s' % f)
        if rc == EXIT_CLEAN:
            rc = EXIT_FINDING
    return rc


if __name__ == '__main__':
    sys.exit(main())
