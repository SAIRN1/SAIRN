# OWNER: cc
"""tools/exit_status_attributable.py -- does the exit status this command
returns actually belong to the program you are about to judge?

── THE PATTERN THIS EXISTS FOR, MEASURED TWICE IN TWO DAYS ───────────────────
Both errors were the same shape: A STATUS READ OFF THE WRONG SUBJECT.

  1. 2026-10-04. I ran `python tools/md_table_check.py 2>&1 | tail -8` inside an
     `&&` chain, saw exit 2, and wrote "md_table_check.py EXITS 2 (COULD NOT
     RUN) while reporting 0 malformed rows" into the standing open-work index
     AND a commit message. THE TOOL EXITS 0 and has no code path that returns 2
     at all. The 2 belonged to the last element of the chain.

  2. 2026-10-05. After a push had already succeeded, a SUBSEQUENT no-op push
     printed "Blocked: this gate could not tell what is being pushed -- no ref
     lines on stdin". I read it as a refusal OF MY PUSH. `git rev-list
     --left-right --count origin/main...HEAD` answered `0 0`: there was nothing
     to send, so the hook was invoked with no refs.

The first cost a false accusation against a working checker in a standing
document. The second cost a wrong conclusion that I nearly acted on.

── WHY A CHECK IS POSSIBLE AT ALL, when "did you misread it" sounds subjective
The hazardous half is NOT subjective and needs no intent inference: **a shell
pipeline or an `&&` / `||` chain returns ONE status, and it is not the status of
the program you named.** That is decidable from the command text alone.

So this does not try to know what you believe. It answers one mechanical
question -- IS THE STATUS THIS COMMAND RETURNS ATTRIBUTABLE TO A SINGLE NAMED
PROGRAM -- and when the answer is no, it names which element the status will
actually come from and what to run instead.

── WHAT IT DOES NOT DO ────────────────────────────────────────────────────────
It does not say a pipeline is wrong. Piping into `tail` to keep output short is
correct and common, and the overwhelming majority of commands here do it. THE
OUTPUT IS A LIST TO READ, and the judgement -- am I about to quote this status
as a fact about that program -- stays with the person. A gate here would be
cleared by dropping the `| tail`, which makes output unreadable and buys
nothing.

It also cannot see the SECOND half of error 2: that a no-op push produces a
refusal-shaped message. Nothing in the command text says whether there is
anything to push. That half is named here and NOT claimed.

── FAILS CLOSED (PR 1.11) ─────────────────────────────────────────────────────
Exit 2 COULD NOT RUN -- never 0 -- when the command cannot be tokenised at all.
A linter that silently passed an unparseable command would be the same class of
defect it exists to find.

Exit 1 only with `--strict`. Default is report-only, exit 0.

CLI:
    python tools/exit_status_attributable.py 'python tools/x.py | tail -3'
    python tools/exit_status_attributable.py --stdin   < command.txt
    python tools/exit_status_attributable.py --selftest
"""
import re
import shlex
import sys

COULD_NOT_RUN = 2

# Separators after which the FINAL element owns the status. Split on raw text
# rather than shlex tokens: shlex splits on whitespace only, so `a;b` arrives as
# one token -- the same reason tools/git_push_master_guard.py splits on text.
SEPARATORS = re.compile(r'\|\||&&|;|\||\n')

# A pipeline whose last element is one of these is the classic "I read the
# filter's status" shape. Named so the message can be specific rather than
# generic.
FILTERS = ('tail', 'head', 'grep', 'sed', 'awk', 'cut', 'sort', 'uniq', 'wc',
           'tr', 'cat', 'tee', 'jq', 'xargs')


def elements(cmd):
    """The command text split into the pieces a shell would sequence."""
    return [p.strip() for p in SEPARATORS.split(cmd) if p.strip()]


def program(piece):
    """The program a single command piece invokes, best effort.

    Skips leading VAR=value assignments -- `SAIRN_SEED_GATE=off git push` runs
    git, not an assignment -- and skips `cd`, which is almost never the subject.
    """
    try:
        toks = shlex.split(piece, posix=True)
    except ValueError:
        toks = piece.split()
    for t in toks:
        if re.match(r'^[A-Za-z_][A-Za-z0-9_]*=', t):
            continue
        return t
    return ''


def analyse(cmd):
    """(attributable, owner, parts, note)."""
    if not cmd.strip():
        return None, '', [], 'empty command'
    parts = elements(cmd)
    if not parts:
        return None, '', [], 'nothing to analyse'
    if len(parts) == 1:
        return True, program(parts[0]), parts, ''
    owner = program(parts[-1])
    note = ''
    if owner in FILTERS:
        note = ('the status will come from `%s`, a text filter, which exits 0 '
                'for "I ran" and says NOTHING about the program before it'
                % owner)
    elif '&&' in cmd or '||' in cmd:
        note = ('an `&&` / `||` chain returns the status of whichever element '
                'ran LAST, which may not be the one you are judging')
    else:
        note = 'the status will come from the LAST element, `%s`' % owner
    return False, owner, parts, note


def selftest():
    """Both directions, and the two real commands that caused the errors."""
    ok = True

    def case(label, cmd, want_attributable):
        nonlocal ok
        att, owner, parts, note = analyse(cmd)
        good = (att is want_attributable)
        print('%s %-54s -> attributable=%s owner=%r'
              % ('ok  ' if good else 'FAIL', label, att, owner))
        if not good:
            ok = False

    # THE TWO REAL ONES, verbatim in shape.
    case('error 1: tool piped into tail inside an && chain',
         'node --check api/x.js && python tools/md_table_check.py 2>&1 | tail -8',
         False)
    case('error 2: git push piped through sed/grep/tail',
         'git push origin main 2>&1 | sed "s/^remote: //" | grep -v To | tail -4',
         False)
    # The safe shape the lesson produced.
    case('the fix: redirect, then read the status alone',
         'python tools/md_table_check.py > /tmp/out.txt 2>&1', True)
    # Controls in the other direction, so it is not simply "everything is bad".
    case('a bare command', 'python tools/fail_open_scan.py', True)
    case('a command with an env assignment is still attributable',
         'PYTHONIOENCODING=utf-8 python tools/x.py', True)
    case('a semicolon sequence is NOT attributable', 'echo a; echo b', False)

    # The owner must be NAMED, not merely "not attributable".
    _att, owner, _p, note = analyse('python tools/x.py 2>&1 | tail -3')
    if owner != 'tail' or 'text filter' not in note:
        print('FAIL the filter owner is not named in the note')
        ok = False
    else:
        print('ok   the owning element is NAMED (%r) and the note says why' % owner)

    # Fails closed on something it cannot tokenise.
    att, _o, _p, note = analyse('   ')
    if att is not None:
        print('FAIL an empty command should not be called attributable')
        ok = False
    else:
        print('ok   an empty command is a refusal, not a pass')
    return 0 if ok else 1


def main(argv):
    if '--selftest' in argv:
        return selftest()
    if '--stdin' in argv:
        cmd = sys.stdin.read()
    else:
        pos = [a for a in argv if not a.startswith('--')]
        if not pos:
            print(__doc__.strip().split('CLI:')[-1].strip())
            return COULD_NOT_RUN
        cmd = pos[0]

    att, owner, parts, note = analyse(cmd)
    if att is None:
        print('COULD NOT RUN -- this is not a pass.')
        print('  %s' % note)
        return COULD_NOT_RUN

    print('EXIT STATUS ATTRIBUTION')
    print('  elements: %d' % len(parts))
    for p in parts:
        print('    %s' % p[:140])
    print()
    if att:
        print('  ATTRIBUTABLE. The status belongs to `%s`, so quoting it as a '
              'fact about that program is sound.' % owner)
        return 0
    print('  NOT ATTRIBUTABLE -- %s.' % note)
    print()
    print('  So do NOT quote this exit code as a fact about any program you '
          'named earlier in the line. Measure the one you mean:')
    print('    <that program> > /tmp/out.txt 2>&1')
    print('    echo $?          # on its own line')
    print()
    print('  THIS IS A LIST TO READ, NOT A VERDICT. Piping into a filter to '
          'keep output short is correct and usual; the hazard is only in '
          'ATTRIBUTING the resulting status.')
    return 1 if '--strict' in argv else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
