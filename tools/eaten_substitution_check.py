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


def main(argv):
    rng, limit, err = resolve_range(argv)
    if err:
        print('COULD NOT RUN: ' + err)
        return EXIT_COULD_NOT_RUN
    recs, err = commits(rng, limit)
    if err:
        print('COULD NOT RUN: ' + err)
        return EXIT_COULD_NOT_RUN

    findings = []
    for sha, subject, lines in recs:
        for lineno, prev, line in scan(lines):
            findings.append((sha, subject, lineno, prev, line))

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

    if not findings:
        print('')
        print('  No message in this range has a paragraph continuation line')
        print('  beginning with a stray single space.')
        print('')
        print('  THAT IS NOT "the messages are intact". A substitution that')
        print('  produced OUTPUT leaves no gap and this cannot see it. Only')
        print('  the empty-output case is detectable after the fact, which is')
        print('  why `git commit -F <file>` is the control and this is the')
        print('  backstop.')
        return EXIT_CLEAN

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
