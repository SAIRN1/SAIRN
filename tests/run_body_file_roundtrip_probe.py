"""Does a free-text body survive from disk to the record, byte for byte?

    python tests/run_body_file_roundtrip_probe.py

Exit 0  every metacharacter shape survives, and every unusable body is
        refused as COULD NOT TELL rather than stored as empty
Exit 1  a body was altered, or an unusable one was accepted
Exit 2  COULD NOT RUN -- never folded into either of the other two

── WHAT THIS IS ACTUALLY ABOUT, BECAUSE THE OBVIOUS READING IS WRONG ───────
This is NOT a shell-injection control on tools/tier_a_review_gate.py. That
tool was AUDITED on 2026-09-22 and has no injection path: every subprocess
call in it passes an argument LIST with no `shell=`, so nothing in a body can
mean anything by the time it reaches argv. The same is true of
tools/sairn_claim.py. Saying so plainly matters -- a control whose stated
subject is a vulnerability that does not exist teaches the next reader to
look in the wrong place.

THE TEXT DIES IN THE CALLER'S SHELL, BEFORE argv EXISTS. Reproduced rather
than assumed, on 2026-09-22:

    "the anchor is `echo SUBSTITUTED` in the file"
        -> 'the anchor is SUBSTITUTED in the file'   (37 bytes; 12 gone)

    "$(cat <<EOF ... $(echo INJECTED) ... EOF)"      [UNQUOTED delimiter]
        -> the substitution RUNS and splices its output into the body

    A 221-byte verdict carrying backticks, $(...), ${HOME} and $USER
        -> arrived as 140 bytes with $USER silently EMPTY and ${HOME}
           replaced by a path

Every one of those reports success. The shell did as instructed, the tool
stored what it was handed, and nobody re-reads a verdict they just wrote.

SO THE FIX REMOVES THE NEED FOR COMMAND SUBSTITUTION rather than sanitising
anything: `--body-file <path>`. A path is a short argument with no
metacharacters, and the body never passes through a shell at all. This probe
guards THAT -- the round trip -- plus the refusals, because a body-file that
silently became the empty string would store a tick as a review.
"""

import importlib.util
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(ROOT, 'tools', 'tier_a_review_gate.py')

CONTROLS_FOR = ['tier_a_review_gate.py']

# Every shape that was observed to be eaten, plus the two that expand silently
# to nothing -- which is the worst of them, because a removal leaves no trace.
HOSTILE = (
    'The guard is `senServerWinsMerge` and the anchor is `check11_probe.py`.\n'
    'Cost: $(git rev-parse HEAD) must stay literal, and so must ${HOME}.\n'
    '$USER expands to EMPTY in a shell, which is the shape that leaves no\n'
    'trace at all -- a word simply missing from a sentence that still reads.\n'
    'Nested: $(echo `echo inner`) and a lone backslash \\ and a quote " here.\n'
)

FAILS = []


def arm(label, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + label
          + ('' if cond else '\n         ' + str(detail)[:300]))
    if not cond:
        FAILS.append(label)


def main():
    if not os.path.isfile(TOOL):
        print('COULD NOT RUN -- %s is not in this clone.' % TOOL)
        return 2
    spec = importlib.util.spec_from_file_location('tg_probe', TOOL)
    tg = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(tg)
    except Exception as e:
        print('COULD NOT RUN -- %s did not import: %s' % (TOOL, e))
        return 2
    if not hasattr(tg, 'body_from_file_or'):
        print('COULD NOT RUN -- body_from_file_or is gone. That is not a pass: '
              'the round trip this probe guards no longer exists.')
        return 2

    tmp = tempfile.mkdtemp(prefix='bodyfile-')
    good = os.path.join(tmp, 'body.txt')
    with open(good, 'w', encoding='utf-8', newline='') as fh:
        fh.write(HOSTILE)

    print('THE ROUND TRIP')
    got = tg.body_from_file_or(['--open', '--body-file', good], 'FALLBACK')
    arm('the body returns byte-for-byte, stripped of surrounding blank space only',
        got == HOSTILE.strip(),
        'len(returned)=%d len(expected)=%d' % (len(got), len(HOSTILE.strip())))

    # NAMED INDIVIDUALLY rather than covered by the equality above. If the
    # equality arm is ever loosened, these still say which shape was lost --
    # and the failure message is the whole value of a control like this.
    for shape in ('`senServerWinsMerge`', '$(git rev-parse HEAD)', '${HOME}',
                  '$USER', '$(echo `echo inner`)', '\\', '"'):
        arm('survives literally: %r' % shape, shape in got,
            'the shell ate it, or something between here and the record did')

    print('\nTHE REFUSALS -- an unusable body is COULD NOT TELL, never ""')

    def refuses(label, argv, path_note=''):
        try:
            tg.body_from_file_or(argv, None)
            arm(label, False, 'ACCEPTED it' + path_note)
        except tg.CouldNotTell:
            arm(label, True)
        except Exception as e:
            arm(label, False, 'raised %s instead of CouldNotTell' % type(e).__name__)

    refuses('a path that does not exist',
            ['--open', '--body-file', good + '.nope'])
    refuses('--body-file with no path at all', ['--open', '--body-file'])

    empty = os.path.join(tmp, 'empty.txt')
    with open(empty, 'w', encoding='utf-8') as fh:
        fh.write('   \n\n  ')
    refuses('a file containing only whitespace', ['--open', '--body-file', empty])

    # NOT UTF-8. A lossy decode would store a body that LOOKS fine and is not
    # the author's, which is the same silent-corruption family the flag exists
    # to close -- so it has to refuse rather than decode with errors='replace'.
    latin = os.path.join(tmp, 'latin.txt')
    with open(latin, 'wb') as fh:
        fh.write('a verdict about résumé handling'.encode('latin-1'))
    refuses('a file that is not UTF-8', ['--open', '--body-file', latin])

    print('\nTHE OLD PATH IS UNTOUCHED')
    arm('with no --body-file, the positional body is returned unchanged',
        tg.body_from_file_or(['--open', 'a plain sentence'], 'a plain sentence')
        == 'a plain sentence')
    arm('...and None stays None, so a caller can tell "not given" from ""',
        tg.body_from_file_or(['--discharge', 'cody'], None) is None)

    print('\n%d failure(s)' % len(FAILS))
    for f in FAILS:
        print('  - ' + f)
    return 1 if FAILS else 0


if __name__ == '__main__':
    sys.exit(main())
