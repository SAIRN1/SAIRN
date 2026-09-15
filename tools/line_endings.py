"""line_endings.py -- the three DIFFERENT jobs CRLF-vs-LF work splits into.

    python tools/line_endings.py <path> [<path2>]   # describe, or compare two
    python tools/line_endings.py --selftest

── WHY THIS IS A RECOMBINATION AND NOT A NEW HELPER ─────────────────────────
Fifty-two files in this repo handle line endings independently. That is not
duplication to be tidied away -- most of them are doing it CORRECTLY, and they
had already converged on the right primitive for the job they each have. What
they had NOT done is notice that there are THREE jobs, and that the recurring
false alarm lives in the one job almost nobody writes down.

  1. ROUND-TRIP a file      -- read, change something, write back, and do NOT
                               flip the endings underneath somebody
  2. COMPARE two copies     -- is this the same CONTENT, when one copy came
                               through a different checkout?
  3. FLIP on purpose        -- a metamorphic transform that must not change a
                               tool's verdict

── JOB 1 IS ALREADY SOLVED, AND THE PLATFORM IS RIGHT ───────────────────────
`io.open(path, encoding='utf-8', newline='')` on BOTH the read and the write is
the correct primitive and ~50 files use it. `newline=''` disables universal-
newline translation, so what is read is what is on disk and what is written is
what you hand it. The failure mode it prevents is real and expensive: Python's
DEFAULT text mode translates on read and writes `\\n`, so a read-modify-write of
a CRLF file SILENTLY REWRITES EVERY LINE. That produces a diff nobody can review
and can hide a real change inside thousands of lines of noise -- which is why
CLAUDE.md warns that `sed -i` is unsafe in this repo, and why one session
abandoned a Python read/write approach mid-pass after it flattened a shared
file.

`tools/guard_ablation.py` is worth reading as the subtle case: it writes
`'\\n'.join(mutated)` under `newline=''`, which preserves CRLF only because the
split was on `'\\n'` and each line kept its own `\\r`. Correct, and correct for a
reason that is easy to break.

── JOB 2 IS WHERE THE RECURRING DEFECT LIVES ────────────────────────────────
A byte comparison between two checkouts of the same file reports DIFFERENT when
nothing differs but the endings. On this platform that has produced false
"files differ" alarms repeatedly -- four times in a single session on
2026-09-03, and CLAUDE.md now carries the rule in its own voice: *"A
CRLF-vs-LF difference is not drift -- compare after `tr -d '\\r'` before
reporting one."* The skill files say the same about the user store being CRLF
and the repo LF.

**THE FIX IS NOT "NORMALISE BEFORE COMPARING". It is that the comparison has
THREE ANSWERS AND EVERYBODY WROTE TWO.** `tr -d '\\r'` then compare collapses
*identical* and *differs only in line endings* into one result, which is right
for "is this content the same" and WRONG the moment somebody needs to know
whether a file was rewritten -- a mixed-ending file, a checkout that flipped, a
tool that flattened something. `compare()` below returns which of the three it
is, so a caller can say "same content" without losing the fact that the bytes
moved.

── JOB 3 IS RARE AND ALREADY CORRECT ────────────────────────────────────────
`tools/metamorphic_check.py:161` flips endings deliberately, to prove a checker's
verdict does not depend on them. It is the only file here that SHOULD change
endings, and `flip()` is its logic, kept identical.

── WHAT THIS DOES NOT DO ────────────────────────────────────────────────────
It does not migrate the 52 files. Most are correct, a mass edit across probes
that mutate tracked files is a poor trade, and `git diff` noise on 52 files is
exactly the reviewability problem this module is about. It is here so the NEXT
one is not a fifty-third independent implementation, and so job 2 has an obvious
right answer to reach for.
"""
import io
import os
import sys

CRLF = '\r\n'
LF = '\n'


def read_preserving(path):
    """Job 1, read half. What is on disk, byte for byte, as text."""
    with io.open(path, encoding='utf-8', errors='replace', newline='') as fh:
        return fh.read()


def write_preserving(path, text):
    """Job 1, write half. Writes exactly what it is given.

    It does NOT choose an ending for you, deliberately: a helper that guessed
    would be the translation bug wearing a friendlier name. Pair it with
    read_preserving and the endings survive; hand it text you built yourself and
    you own what you built.
    """
    with io.open(path, 'w', encoding='utf-8', newline='') as fh:
        fh.write(text)
    return len(text)


def normalise(text):
    """Every ending to LF. For COMPARISON ONLY -- never write this back to a
    file whose endings you did not intend to change."""
    return text.replace(CRLF, LF).replace('\r', LF)


def describe(text):
    """counts, so a report can say WHICH kind rather than that something is
    'wrong'. `mixed` is a real state and the one most likely to surprise."""
    crlf = text.count(CRLF)
    lone_lf = text.count(LF) - crlf
    lone_cr = text.count('\r') - crlf
    return {'crlf': crlf, 'lf': lone_lf, 'cr': lone_cr,
            'mixed': (crlf > 0 and lone_lf > 0),
            'style': 'CRLF' if crlf and not lone_lf
                     else 'LF' if lone_lf and not crlf
                     else 'MIXED' if crlf and lone_lf
                     else 'NONE'}


def compare(a, b):
    """THE THREE-STATE ANSWER. Returns one of:

        'IDENTICAL'     -- byte for byte
        'ENDINGS_ONLY'  -- same content, different line endings. NOT DRIFT
        'DIFFERS'       -- genuinely different content

    Two states is what produces the false alarm, and it produces it in the
    direction that wastes the most time: a real investigation into a difference
    that is a checkout artefact. Three states costs one extra branch at the call
    site and removes the whole class.
    """
    if a == b:
        return 'IDENTICAL'
    if normalise(a) == normalise(b):
        return 'ENDINGS_ONLY'
    return 'DIFFERS'


def same_content(a, b):
    """True when the CONTENT matches, whatever the endings. Use when the answer
    genuinely is binary -- but prefer compare() when a human will read the
    result, because 'they differ' and 'they differ only in line endings' are
    different sentences to put in front of somebody at 3am."""
    return compare(a, b) != 'DIFFERS'


def flip(src):
    """Job 3. Whichever ending the text has, give it the other one.

    Kept identical to tools/metamorphic_check.py's transform rather than
    rewritten: that one is correct and is under test, and a second subtly
    different implementation of a deliberate corruption is the last thing this
    module should introduce.
    """
    lf = src.replace(CRLF, LF)
    return lf if CRLF in src else lf.replace(LF, CRLF)


def compare_files(p1, p2):
    return compare(read_preserving(p1), read_preserving(p2))


def _selftest():
    ok = True

    def check(name, cond, detail=''):
        nonlocal ok
        print(('  ok   ' if cond else '  FAIL ') + name + ('' if cond else '  ' + str(detail)))
        if not cond:
            ok = False

    lf, crlf = 'a\nb\nc\n', 'a\r\nb\r\nc\r\n'

    print('1. compare has THREE answers, which is the whole point')
    check('identical bytes -> IDENTICAL', compare(lf, lf) == 'IDENTICAL')
    check('same content, different endings -> ENDINGS_ONLY',
          compare(lf, crlf) == 'ENDINGS_ONLY', compare(lf, crlf))
    check('real difference -> DIFFERS', compare(lf, 'a\nB\nc\n') == 'DIFFERS')
    check('a real difference is NOT masked by normalising',
          compare('a\r\nb\r\n', 'a\nc\n') == 'DIFFERS',
          'the normalise step must not hide content changes')

    print('\n2. same_content is the binary view, and agrees with compare')
    check('LF vs CRLF is the same content', same_content(lf, crlf))
    check('different text is not', not same_content(lf, 'x\n'))

    print('\n3. describe names the style, including MIXED')
    check('pure LF', describe(lf)['style'] == 'LF', describe(lf))
    check('pure CRLF', describe(crlf)['style'] == 'CRLF', describe(crlf))
    check('mixed is its own answer, not one of the two',
          describe('a\r\nb\n')['style'] == 'MIXED', describe('a\r\nb\n'))
    check('...and mixed is flagged', describe('a\r\nb\n')['mixed'] is True)
    check('no line endings at all is NONE, not LF',
          describe('abc')['style'] == 'NONE', describe('abc'))

    print('\n4. flip really flips, in both directions')
    check('LF -> CRLF', flip(lf) == crlf, repr(flip(lf)))
    check('CRLF -> LF', flip(crlf) == lf, repr(flip(crlf)))
    check('flip changes the bytes but never the content',
          compare(lf, flip(lf)) == 'ENDINGS_ONLY')

    print('\n5. round-trip does not rewrite the file -- the job-1 failure mode')
    import tempfile
    d = tempfile.mkdtemp(prefix='line-endings-selftest-')
    p = os.path.join(d, 'f.txt')
    io.open(p, 'w', encoding='utf-8', newline='').write(crlf)
    back = read_preserving(p)
    check('a CRLF file reads back as CRLF', back == crlf, repr(back))
    write_preserving(p, back)
    check('...and writing it back leaves it byte-identical',
          read_preserving(p) == crlf)
    # The control: the DEFAULT text mode is what silently flattens it.
    with io.open(p, encoding='utf-8') as fh:
        translated = fh.read()
    check('CONTROL: default text mode really does translate, so this module is '
          'solving a real problem', translated == lf, repr(translated))
    try:
        os.remove(p)
        os.rmdir(d)
    except OSError:
        pass

    print('')
    print('  all arms pass' if ok else '  ARMS FAILED -- do not trust this module')
    return 0 if ok else 2


def main(argv):
    if '--selftest' in argv:
        return _selftest()
    args = [a for a in argv if not a.startswith('-')]
    if len(args) == 2:
        v = compare_files(args[0], args[1])
        print('%s' % v)
        if v == 'ENDINGS_ONLY':
            print('  NOT DRIFT. The content is identical; only the line endings '
                  'differ.\n  CLAUDE.md: "A CRLF-vs-LF difference is not drift."')
        return 0
    if len(args) == 1:
        d = describe(read_preserving(args[0]))
        print('%s  crlf=%d lf=%d lone_cr=%d' % (d['style'], d['crlf'], d['lf'], d['cr']))
        return 0
    print(__doc__.strip().split('\n')[2])
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
