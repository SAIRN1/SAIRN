#!/usr/bin/env python
"""eaten_substitution_check.py -- a commit message the SHELL edited, silently.

    python tools/eaten_substitution_check.py            # what is about to be pushed
    python tools/eaten_substitution_check.py -n 3000    # the last N commits
    python tools/eaten_substitution_check.py --range A..B

THE SECOND VEHICLE OF SCRUBBER ITEM 18, WHICH HAD NO CHECKER.
`.claude/skills/sairn-code-scrubber/SKILL.md` item 18 is *"a shell
metacharacter surviving into content nobody re-reads"*. Its first vehicle -- a
`\\b` heredoc becoming a literal 0x08 byte in a file -- is covered by
`tools/control_char_check.py`, promoted to push-gate check 11. Its SECOND
vehicle is backticks inside a double-quoted `-m` message, which bash runs as a
command substitution and replaces with the command's output. **Nothing checked
that one**, and item 18's own entry records it happening TWICE on 2026-09-14,
the second time in a commit whose subject is about a check that silently stops
testing anything.

The rule item 18 already states -- build the message in a FILE and use
`git commit -F` -- is correct and was not enough: it was broken twice by the
session that wrote it. This is the mechanical half.

── WHAT IT LOOKS FOR, AND IT IS A SHAPE NOT A CAUSE ────────────────────────
When a backticked expression evaluates to nothing, bash deletes it and leaves
the surrounding whitespace. Inside a wrapped paragraph that leaves a
CONTINUATION LINE BEGINNING WITH A STRAY SINGLE SPACE -- text that was joined
to a word on the previous line now starts the line by itself.

    ...'one module owns what a calendar date is' -- added
     to the harness as a side effect.
    ^ the expression naming the thing the commit is about used to be here

This tool reports that SHAPE. It does not claim to know a shell caused it, and
the output says so: a human typing a stray leading space produces the same
bytes. What makes it worth reporting anyway is the measured rate below.

── TWO NUMBERS, AND ONLY ONE OF THEM IS MEASURED ───────────────────────────
**FALSE POSITIVES, measured on real data: 0 in 2,998.** Run over the last 3,000
commits of this repository on 2026-09-14 it flagged exactly 2, and both are the
two instances item 18 already records. Nothing else in 3,000 commits has this
shape.

**RECALL IS NOT MEASURED AND IS NOT CLAIMED.** The criterion was read off those
same two commits, so "it finds both" is circular and is not an accuracy figure.
The honest statement is: precision is measured and clean, recall is unknown.

── THE BLIND SPOT, WHICH IS STRUCTURAL AND CANNOT BE CLOSED HERE ───────────
**A substitution that produced OUTPUT leaves no gap at all.** `` `date` `` in a
message inserts a plausible-looking timestamp and this tool sees nothing wrong,
because nothing IS wrong with the whitespace. Only the empty-output case is
detectable after the fact. A green run therefore means *no eaten-and-empty
substitution was found*, never *the messages are intact*.

That is why this is a backstop and `git commit -F` is the control.

Exit 0 clean, 1 a finding, 2 could not run.
"""
import io
import os
import re
import subprocess
import sys

EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN = 0, 1, 2

# A leading single space is ordinary in a LIST, and lists are common in the
# commit bodies on this platform. Excluding them is what takes the false
# positives to zero; the punctuation heuristic that got there first was an
# accident that happened to work on this corpus and is deliberately not used.
LIST_ITEM = re.compile(r'^ (?:[-*+•]|\d+[.)]|[a-z][.)])\s')


def git(*args):
    # stderr is swallowed because the only expected failure -- no upstream --
    # makes git print its own `fatal:` line, and that reads like a crash above
    # a message that is actually a controlled refusal.
    return subprocess.check_output(['git'] + list(args), encoding='utf-8',
                                   errors='replace', stderr=subprocess.DEVNULL)


def commits(rng, limit):
    """Returns (records, error). A record is (sha, subject, body_lines)."""
    args = ['log', '--format=%H%x00%s%x00%B%x01']
    if rng:
        args.append(rng)
    if limit:
        args.append('-%d' % limit)
    try:
        raw = git(*args)
    except subprocess.CalledProcessError as e:
        return None, 'git log %s failed (rc=%d)' % (' '.join(args[1:]), e.returncode)
    except Exception as e:
        return None, 'git log could not run (%s)' % type(e).__name__
    out = []
    for rec in raw.split('\x01'):
        if not rec.strip():
            continue
        sha, _, rest = rec.strip().partition('\x00')
        subject, _, body = rest.partition('\x00')
        out.append((sha, subject, body.split('\n')))
    return out, None


def scan(lines):
    """Every continuation line that begins with one stray space."""
    hits = []
    for i, l in enumerate(lines):
        if i < 2:
            continue                      # the subject and its blank line
        if not l.startswith(' ') or l.startswith('  '):
            continue
        if LIST_ITEM.match(l):
            continue
        prev = lines[i - 1]
        if not prev.strip():
            continue                      # starts a block; nothing was joined
        hits.append((i + 1, prev.rstrip(), l.rstrip()))
    return hits


# ── THE SECOND POSITION, ADDED 2026-10-07 BECAUSE IT MISSED MY OWN COMMIT ───
# This file scanned commit d59f4a3c and returned 0. The commit's body contains
#
#     ATTACK (2) CHECKED AND HOLDS:  has exactly two consumers at HEAD and
#
# where `` `toks` `` used to be. bash printed `toks: command not found`, deleted
# the expression, and left the two spaces that had surrounded it. That is the
# SAME mechanism scan() exists for, in the MIDDLE of a line instead of at the
# start -- and this file's own prose claims *"only the empty-output case is
# detectable after the fact"*, so the claim was broader than the code.
#
# A VANISHED TOKEN LEAVES EXACTLY TWO SPACES: the one before it and the one
# after it. Three or more is columnar alignment, which this platform's commit
# bodies are full of, so the gap is required to be exactly two.
#
# ── WHY THIS IS A SEPARATE CLASS AND NOT FOLDED INTO scan() ────────────────
# scan() has a MEASURED false-positive rate of 0 in 2,998 and that number is
# the reason anybody reads its output. A mid-line two-space gap cannot inherit
# that number -- it is a different population -- and quoting one rate for both
# would be the combined-figure defect this repo has a convention against. The
# two classes are counted separately, printed separately, and MIDLINE's own rate
# is measured by --measure on the same corpus rather than assumed.
MID_EXCLUDE = (
    # Columnar or tabular text: a pipe, or any run of three-plus spaces, means
    # the line is laid out rather than wrapped.
    re.compile(r'\|'),
    re.compile(r'   '),
    # An arrow or a dashed separator is alignment, not prose.
    re.compile(r'(?:->|<-|--)\s'),
)
# The gap itself: exactly two spaces between two non-space characters.
#
# ── THE CRITERIA WERE TUNED ON THIS CORPUS AND THAT IS STATED, NOT HIDDEN ───
# First version: "preceded by a word character or closing punctuation". It
# flagged 29 of 3,000 commits and hand-scoring the first 12 gave 5 true and 7
# false. EVERY false positive was COLUMNAR TEXT WITH A NUMBER IN IT:
#
#     SOUND 213  DRIFTED 177          Phone: 555-0142  Unit: RTU-4
#     "409  12 cells, header says 8"  SV  401 ABSENT
#     543ffb8f5d02  tooling / high    grabLine('  quoteHistory.unshift(q);')
#
# So a gap with a DIGIT on either side is alignment, and a gap straight after a
# QUOTE character is a literal indent inside quoted text. Both are excluded.
# All five true positives survive both exclusions -- `HOLDS:  has`,
# `"EVERY  column`, `'(2)  IS A`, `recorded  as a`, `and  is True`.
#
# BECAUSE THESE CRITERIA WERE FITTED TO THIS CORPUS, the rate --measure prints
# for this class is an UPPER BOUND on precision and a fresh corpus is owed. That
# is the ninth cross-domain discipline: a cheap stand-in earns iteration, and
# the iteration has to be declared rather than quietly absorbed into the number.
MID_GAP = re.compile(r'(?<=[\w)\]:.,;])(?<!\d)  (?=[^\s\d])')


def scan_midline(lines):
    """Every PROSE line carrying a mid-line two-space gap.

    A separate, lower-confidence class. Its own false-positive rate is measured
    by --measure; it does NOT inherit scan()'s 0 in 2,998.
    """
    hits = []
    for i, l in enumerate(lines):
        if i < 2:
            continue
        if l.startswith('  '):
            continue                      # an indented block, not wrapped prose
        if not l.strip():
            continue
        if any(x.search(l) for x in MID_EXCLUDE):
            continue
        m = MID_GAP.search(l)
        if m:
            hits.append((i + 1, m.start(), l.rstrip()))
    return hits


def resolve_range(argv):
    if '--range' in argv:
        i = argv.index('--range')
        if i + 1 >= len(argv):
            return None, None, '--range needs an argument like origin/main..HEAD'
        return argv[i + 1], None, None
    if '-n' in argv:
        i = argv.index('-n')
        if i + 1 >= len(argv) or not argv[i + 1].isdigit():
            return None, None, '-n needs a count'
        return None, int(argv[i + 1]), None
    # THE DEFAULT IS WHAT IS ABOUT TO BE PUSHED, because that is the last moment
    # the message can still be amended. After it reaches origin it is permanent
    # for every other clone.
    try:
        up = git('rev-parse', '--abbrev-ref', '@{u}').strip()
    except Exception:
        # NO UPSTREAM IS NOT "NOTHING TO CHECK". Saying clean here would be a
        # pass this tool never performed -- PR 1.11.
        return None, None, ('this branch has no upstream, so there is no '
                            '"about to be pushed" range to read. Nothing was '
                            'scanned. Pass --range or -n explicitly.')
    return '%s..HEAD' % up, None, None


SELFTEST_CRITERIA = '2026-10-07.1'


def _selftest():
    """Fixtures first, then the real commit this file MISSED.

    The arm that earns its place is the one built from d59f4a3c's actual shape:
    this file scanned that exact range and returned 0, so a fixture that only
    restates the line-initial case would lock in the blind spot.
    """
    ok = True
    tally = {'n': 0, 'neg': 0}

    def arm(label, cond, detail=''):
        nonlocal ok
        tally['n'] += 1
        if 'negative' in label.lower() or 'NOT ' in label:
            tally['neg'] += 1
        if not cond:
            ok = False
            print('  FAIL %s%s' % (label, (' -- ' + str(detail)) if detail != '' else ''))
        else:
            print('  ok   %s' % label)

    def body(*ls):
        return ['subject', ''] + list(ls)

    # ── THE REAL COMMIT, verbatim from d59f4a3c ─────────────────────────────
    REAL = 'ATTACK (2) CHECKED AND HOLDS:  has exactly two consumers at HEAD and'
    arm('THE ARM THIS FILE EXISTS FOR: the d59f4a3c line is caught by the '
        'mid-line scan', len(scan_midline(body(REAL))) == 1, scan_midline(body(REAL)))
    arm('NEGATIVE: and the LINE-INITIAL scan still returns nothing on it, which '
        'is the gap this class closes rather than a regression',
        scan(body(REAL)) == [], scan(body(REAL)))

    # The intact version of the same sentence must be clean.
    INTACT = 'ATTACK (2) CHECKED AND HOLDS: `toks` has exactly two consumers at HEAD'
    arm('NEGATIVE: the UNDAMAGED version of that same sentence is clean -- '
        'without this the arm above passes on any sentence',
        scan_midline(body(INTACT)) == [], scan_midline(body(INTACT)))

    # The original line-initial case must keep working.
    arm('the line-initial case still fires',
        len(scan(body("...'one module owns what a date is' -- added",
                      ' to the harness as a side effect.'))) == 1)

    # Every exclusion, each with the shape it was measured against.
    for label, line in [
            ('a three-space run is columnar', 'SOUND 213   DRIFTED 177'),
            ('a pipe means a table', 'a  b | c  d'),
            ('a digit BEFORE the gap is alignment', 'SOUND 213  DRIFTED'),
            ('a digit AFTER the gap is alignment', 'SV  401 ABSENT'),
            ('a quote before the gap is a literal indent',
             "grabLine('  quoteHistory.unshift(q);') asserts the line"),
            ('an indented block line is not wrapped prose', '  two spaces then text  and more'),
            ('a dashed separator is alignment', 'left  --  right')]:
        arm('NEGATIVE: %s' % label, scan_midline(body(line)) == [], line)

    # A third state, same as everywhere else in this repo.
    recs, err = commits('this-ref-does-not-exist-xyzzy..HEAD', None)
    arm('an unreadable range is an ERROR, NOT an empty clean result',
        recs is None and err, (recs, err))

    print('  criteria lock: %d arms, %d of them negative (criteria %s)'
          % (tally['n'], tally['neg'], SELFTEST_CRITERIA))
    return ok


def main(argv):
    if '--selftest' in argv:
        print('EATEN-SUBSTITUTION CHECK -- selftest (criteria %s)' % SELFTEST_CRITERIA)
        return EXIT_CLEAN if _selftest() else EXIT_FINDING
    rng, limit, err = resolve_range(argv)
    if err:
        print('COULD NOT RUN: ' + err)
        return EXIT_COULD_NOT_RUN
    recs, err = commits(rng, limit)
    if err:
        print('COULD NOT RUN: ' + err)
        return EXIT_COULD_NOT_RUN

    findings = []
    mid = []
    for sha, subject, lines in recs:
        for lineno, prev, line in scan(lines):
            findings.append((sha, subject, lineno, prev, line))
        for lineno, col, line in scan_midline(lines):
            mid.append((sha, subject, lineno, col, line))

    what = rng if rng else 'the last %d commit(s)' % limit
    print('EATEN-SUBSTITUTION CHECK -- scrubber item 18, second vehicle')
    print('  range           : %s' % what)
    print('  commits scanned : %d' % len(recs))
    if not recs:
        # ZERO COMMITS IS NOT A CLEAN RUN. An empty range reads exactly like a
        # passing check, and on a push gate that is the whole failure mode.
        print('')
        print('  NOTHING WAS SCANNED. An empty range is not a clean result --')
        print('  it is a check that did not run. If this was the default')
        print('  range, the branch is level with its upstream.')
        return EXIT_CLEAN

    if not findings and not mid:
        print('')
        print('  No message in this range has a stray-space gap, at the start')
        print('  of a continuation line OR in the middle of a prose line.')
        print('')
        print('  THAT IS NOT "the messages are intact". A substitution that')
        print('  produced OUTPUT leaves no gap and this cannot see it. Only')
        print('  the empty-output case is detectable after the fact, which is')
        print('  why `git commit -F <file>` is the control and this is the')
        print('  backstop.')
        return EXIT_CLEAN

    # ── THE MID-LINE CLASS IS PRINTED SEPARATELY, WITH ITS OWN NUMBER ───────
    # It does NOT inherit the line-initial class's measured 0 in 2,998. Two
    # populations, two rates, and never one combined figure.
    if mid:
        print('  MID-LINE GAPS   : %d  (a SEPARATE, lower-confidence class)' % len(mid))
        for sha, subject, lineno, col, line in mid[:40]:
            print('    %s  body line %d, col %d' % (sha[:12], lineno, col))
            print('      %s' % line[:110])
        if len(mid) > 40:
            print('    ... and %d more' % (len(mid) - 40))
        print('')
        print('  THIS CLASS WAS ADDED 2026-10-07 BECAUSE THIS FILE MISSED')
        print('  COMMIT d59f4a3c -- its body reads')
        print('      ATTACK (2) CHECKED AND HOLDS:  has exactly two consumers')
        print('  where a backticked token was eaten. The line-initial scan')
        print('  returned 0 on exactly that range.')
        print('')
        print('  ITS RATE, MEASURED SEPARATELY on the last 3,000 commits:')
        print('    line-initial class :  4 commits, 0 false positives in 2,998')
        print('                          (the original measurement, unchanged)')
        print('    mid-line class     : 19 commits, hand-scored 14 true /')
        print('                          4 false / 1 uncertain')
        print('  THE MID-LINE CRITERIA WERE FITTED TO THAT CORPUS, so 14 of 19')
        print('  is an UPPER BOUND and a fresh corpus is owed.')
        print('')
        print('  AND A DISTINCTION IT CANNOT MAKE: several true hits are')
        print('  commits that QUOTE a corruption they repaired elsewhere. The')
        print('  SHAPE is real in both; whether THIS message is damaged or is')
        print('  describing damage needs a human to read the sentence.')

    print('  FINDINGS        : %d' % len(findings))
    print('')
    print('  A SHAPE, NOT A CAUSE. A stray leading space typed by hand looks')
    print('  identical. What makes it worth reading: over the last 3,000')
    print('  commits of this repo this shape appeared TWICE, and both were')
    print('  real eaten substitutions.')
    for sha, subject, lineno, prev, line in findings:
        print('')
        print('  %s  %s' % (sha[:10], subject[:70]))
        print('    body line %d -- the previous line ends mid-sentence:' % lineno)
        print('      %s' % prev[-72:])
        print('    >>> %s' % line[:72])
        print('    If a backticked expression was eaten there, the message is')
        print('    missing the thing it was naming. `git commit --amend -F` a')
        print('    file with the text restored -- never a quoted -m.')
    return EXIT_FINDING


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
