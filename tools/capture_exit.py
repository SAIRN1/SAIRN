# OWNER: cody
"""tools/capture_exit.py -- run a command and write ITS real exit status to a
file, so a backgrounded run can be judged by the program's code instead of by
whatever ran last.

── THE DEFECT THIS EXISTS FOR, MEASURED 2026-10-05 ───────────────────────────
The repo's own advice for getting an attributable status is:

    python tools/some_check.py > /tmp/out 2>&1
    echo "EXIT=$?"

That advice is CORRECT and `tools/exit_status_attributable.py` is right to give
it. On a FOREGROUND run the `EXIT=` line is printed where it can be read.

IT STOPS BEING CORRECT THE MOMENT THE RUN IS BACKGROUNDED. The caller then
receives the status of the COMPOUND command, whose last element is the `echo` --
so it reports 0 regardless of what the program did. Both of these were reported
to me as "completed (exit code 0)" while the `EXIT=` line in the captured stdout
said otherwise:

    tools/metamorphic_check.py   notification 0   REAL 1  (one finding)
    tools/dead_rule_sweep.py     notification 0   REAL 2  (22 COULD NOT RUN)

Two not-green tools were one step from entering a standing document as green.
Nothing was hidden -- the real numbers were in the output the whole time. What
was wrong was the number that LOOKED AUTHORITATIVE.

── WHY A STATUS FILE AND NOT A BETTER HABIT ──────────────────────────────────
The backgrounding decision is made AFTER the command text is written, by
something other than the person writing it. So the same text is safe in one
context and misleading in the other, and no amount of care at writing time can
tell which context it will run in. A status written to a NAMED FILE by the
process that actually waited on the child does not depend on who reads it or
how it was launched.

── THE THIRD STATE IS THE WHOLE POINT, AND IT IS A FILE'S HARDEST PART ───────
A status file that does not exist yet and a status file saying `EXIT 0` are the
same bytes to a careless reader: nothing, then zero. That is the identical
failure one level down -- "could not tell" folded into "passed", PR §1.11.

So the file is written TWICE and never only once:

    RUNNING <pid> <iso-utc> <command>     written BEFORE the child starts
    EXIT <code> <iso-utc> <command>       written after the child is reaped
    COULD_NOT_RUN <reason> ...            written when the child never started
    SIGNAL <n> ... (as EXIT <128+n>)      a kill is an outcome, not a silence

A reader that finds `RUNNING` knows the answer is NOT YET KNOWN. A reader that
finds no file at all knows the wrapper itself never started. Neither can be
mistaken for success.

── WHAT IT DOES NOT DO ───────────────────────────────────────────────────────
It does not interpret the status. `EXIT 1` from a report-only checker means
"findings", `EXIT 2` on this platform usually means COULD NOT RUN, and this tool
knows nothing about either convention -- it records the number the child
returned and stops. Judging it stays with the person, the same division
`exit_status_attributable.py` draws.

It does not replace that tool either. That one reads command TEXT before the
run; this one records the OUTCOME of a run. Opposite ends.
"""

import argparse
import datetime
import io
import os
import shutil
import subprocess
import sys
import tempfile
import time

# .2 -- the CLI arms were added after --read raised on its first real use. The
# criteria really changed, so the stamp moves; a lock that grows without the
# version moving makes two different locks indistinguishable in a past report.
# .3 -- the optional --bound. cc's routed finding, 2026-10-06: with no bound
# this file recorded EXIT 0 for runs the live 600s hook ceiling would have
# killed. The criteria really changed, so the stamp moves.
CRITERIA_VERSION = '2026-10-07.3'

RUNNING = 'RUNNING'
EXIT = 'EXIT'
COULD_NOT_RUN = 'COULD_NOT_RUN'


def _now():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def _write(path, text):
    """Replace the status file atomically.

    A half-written status file is a third state nobody asked for, so the
    content is staged beside the target and moved over it.
    """
    d = os.path.dirname(os.path.abspath(path)) or '.'
    if not os.path.isdir(d):
        os.makedirs(d)
    fd, tmp = tempfile.mkstemp(dir=d, prefix='.capture_exit-')
    try:
        with io.open(fd, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(text if text.endswith('\n') else text + '\n')
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def read_status(path):
    """(state, code, rest) from a status file. code is None unless state is EXIT.

    A missing file is ('ABSENT', None, '') -- NOT an exit 0. An unparseable one
    is ('UNREADABLE', None, <the line>), also not an exit 0.
    """
    if not os.path.isfile(path):
        return ('ABSENT', None, '')
    line = io.open(path, encoding='utf-8').read().strip().split('\n')[0]
    parts = line.split(None, 1)
    if not parts:
        return ('UNREADABLE', None, line)
    state = parts[0]
    rest = parts[1] if len(parts) > 1 else ''
    if state == EXIT:
        bits = rest.split(None, 1)
        try:
            return (EXIT, int(bits[0]), bits[1] if len(bits) > 1 else '')
        except (ValueError, IndexError):
            return ('UNREADABLE', None, line)
    if state in (RUNNING, COULD_NOT_RUN):
        return (state, None, rest)
    return ('UNREADABLE', None, line)


# ── THE BOUND, AND WHY A TIMEOUT IS A COULD-NOT-RUN AND NOT A CODE ──────────
# ROUTED TO ME BY CC, 2026-10-06, docs/2026-10-06-cc-routed.md section 16, with
# a five-run artifact. `tools/report_only_checks.py --hook` is wired as an
# `async: true` PostToolUse hook with a 600s ceiling in .claude/settings.json.
# Measured in a detached worktree at f588ef02:
#
#     run 1  547.6s  91.3%  EXIT 0      run 4  679.9s  113.3%  EXIT 0
#     run 2  543.1s  90.5%  EXIT 0      run 5  712.4s  118.7%  EXIT 0
#     run 3  577.1s  96.2%  EXIT 0      mean 612.0s -- OVER the bound
#
# ALL FIVE RECORDED EXIT 0 AND TWO OF THEM THE LIVE HOOK WOULD HAVE KILLED.
# This file had no bound, so it waited as long as the child wanted and then
# wrote a code -- and a code is a VERDICT ABOUT THE PROGRAM. A run the ceiling
# would have killed has no verdict at all: a killed async hook reports nothing,
# which is indistinguishable from a sweep that found nothing. That is the
# fail-open this platform keeps paying for, arriving through a timeout instead
# of through an exception, and it is PR 1.11 one level down inside the very
# tool written to stop it.
#
# CC'S OWN RULE A NAMES THE SHAPE OF THE FIX: "the repair was not a better
# wrapper, it was no wrapper -- a cap enforced by the process that waited on the
# child cannot be shadowed by a PATH lookup." Her 26-run measurement was
# destroyed by `timeout 120` resolving to Windows `timeout.exe` and failing the
# CONTROL and the TEST identically. So the cap lives HERE, in the process that
# already waits, and not in a wrapper command that can be shadowed.
#
# BACKWARD COMPATIBLE BY CONSTRUCTION: `bound=None` is the default and the code
# path below is byte-for-byte the old one. A caller that passes no bound cannot
# tell this change happened.
#
# WHAT IT DOES NOT DO, stated rather than discovered: it kills the CHILD. A
# grandchild the child spawned and did not reap can outlive the kill, so
# `COULD_NOT_RUN TIMEOUT` means "the child did not finish in time", not "nothing
# is still running". Nothing here walks a process tree.
def run(status_path, argv, cwd=None, bound=None):
    """Run argv, record the real status, return it. Never raises on child failure.

    `bound` is seconds. On expiry the child is killed and the status file gets
    `COULD_NOT_RUN TIMEOUT_<bound>s` -- NOT an exit code, because a run that was
    killed produced no verdict about the program. Returns None, same as every
    other could-not-run, so `--read` exits 2 and never 0.
    """
    shown = ' '.join(argv)
    _write(status_path, '%s %d %s %s' % (RUNNING, os.getpid(), _now(), shown))
    try:
        proc = subprocess.Popen(argv, cwd=cwd)
    except OSError as exc:
        _write(status_path, '%s %s %s %s' % (COULD_NOT_RUN, exc.__class__.__name__, _now(), shown))
        return None
    if bound is None:
        code = proc.wait()
    else:
        try:
            code = proc.wait(timeout=bound)
        except subprocess.TimeoutExpired:
            # terminate first, then kill, then stop waiting. A tool that hangs
            # in its own cleanup must not hang the recorder too -- the status
            # file is the deliverable and it gets written either way.
            for _step in (proc.terminate, proc.kill):
                try:
                    _step()
                    proc.wait(timeout=5)
                    break
                except (subprocess.TimeoutExpired, OSError):
                    continue
            _write(status_path, '%s TIMEOUT_%gs %s %s'
                   % (COULD_NOT_RUN, bound, _now(), shown))
            return None
    # A signal death arrives as a negative code on POSIX. 128+n is the shell's
    # own convention and keeps the file's one number an exit status throughout.
    if code < 0:
        code = 128 - code
    _write(status_path, '%s %d %s %s' % (EXIT, code, _now(), shown))
    return code


# ── THE SELF-CHECK, AND ITS NEGATIVE HALF IS WHAT MAKES IT EVIDENCE ──────────
# "it wrote a status file" is satisfied by a wrapper that writes EXIT 0 always.
# So every positive arm is paired with the thing that must NOT hold, and the
# last two arms reproduce the trailing-element mechanism this tool exists for.

def _fixtures():
    tmp = tempfile.mkdtemp(prefix='capture_exit_fx_')
    ok = True

    # ── TWO DEFECTS IN THIS REPORTER, BOTH ALREADY FIXED ELSEWHERE BY ME ────
    # 1. THE COUNT WAS A LITERAL. The lock line said "17 arms, 6 negative, 5
    #    through the CLI" and nine arms were added below it in one sitting. The
    #    same literal was off by one in clone_health_check.py and right only by
    #    coincidence in ledger_append.py; both now derive it. A criteria lock
    #    quoting a number nothing computes is the staleness this repo keeps
    #    paying for, inside the lock that is supposed to be the evidence.
    # 2. THE DETAIL PRINTED ON SUCCESS. `ok A COMMAND THAT OUTLASTS THE BOUND
    #    ... -- returned None, file COULD_NOT_RUN/None` -- the pass and the
    #    failure message on one line, which is a clean line indistinguishable
    #    from a finding. ledger_append.py's reporter did exactly this on its
    #    first run and was corrected the same day; this one was not, because
    #    nothing looked at it.
    tally = {'n': 0, 'neg': 0, 'cli': 0}

    def arm(label, cond, detail=''):
        nonlocal ok
        tally['n'] += 1
        if 'negative' in label.lower() or 'NEVER' in label or 'never' in label:
            tally['neg'] += 1
        if 'CLI' in label or '--read' in label:
            tally['cli'] += 1
        if not cond:
            ok = False
            print('  FAIL %s%s' % (label, (' -- ' + str(detail)) if detail != '' else ''))
        else:
            print('  ok   %s' % label)

    try:
        sp = os.path.join(tmp, 'a.status')

        # ABSENT is not zero. The single hardest arm, and it runs first.
        state, code, _ = read_status(sp)
        arm('an ABSENT status file is ABSENT, never EXIT 0',
            state == 'ABSENT' and code is None, 'got %s/%r' % (state, code))

        code = run(sp, [sys.executable, '-c', 'pass'])
        state, filed, _ = read_status(sp)
        arm('a clean child records EXIT 0', code == 0 and state == EXIT and filed == 0,
            'returned %r, file %s/%r' % (code, state, filed))

        code = run(sp, [sys.executable, '-c', 'import sys; sys.exit(3)'])
        state, filed, _ = read_status(sp)
        arm('a failing child records ITS code, not 0',
            code == 3 and state == EXIT and filed == 3,
            'returned %r, file %s/%r' % (code, state, filed))
        arm('and the recorded code is NOT 0 -- the negative half',
            filed != 0, 'file said %r' % (filed,))

        code = run(sp, [sys.executable, '-c', 'import sys; sys.exit(2)'])
        state, filed, _ = read_status(sp)
        arm('exit 2 survives as 2 and is not flattened to 1',
            code == 2 and filed == 2, 'returned %r, file %r' % (code, filed))

        # A status file is REPLACED, not appended, or the second reader gets the
        # first run's answer.
        arm('the file holds ONE line after a re-run',
            len(io.open(sp, encoding='utf-8').read().strip().split('\n')) == 1)

        missing = os.path.join(tmp, 'no_such_program_xyz')
        code = run(sp, [missing])
        state, filed, _ = read_status(sp)
        arm('a child that never started is COULD_NOT_RUN, not an exit code',
            code is None and state == COULD_NOT_RUN,
            'returned %r, file %s' % (code, state))
        arm('and COULD_NOT_RUN carries no code at all -- the negative half',
            filed is None, 'file code %r' % (filed,))

        sp2 = os.path.join(tmp, 'b.status')
        _write(sp2, '%s 999 %s sleeping' % (RUNNING, _now()))
        state, filed, _ = read_status(sp2)
        arm('a RUNNING file is NOT YET KNOWN, never EXIT 0',
            state == RUNNING and filed is None, 'got %s/%r' % (state, filed))

        _write(sp2, 'garbage from somewhere else')
        state, filed, _ = read_status(sp2)
        arm('an UNREADABLE file is UNREADABLE, never EXIT 0',
            state == 'UNREADABLE' and filed is None, 'got %s/%r' % (state, filed))

        # ── THE TRAILING-ELEMENT MECHANISM, REPRODUCED WITHOUT A SHELL ───────
        # No shell is assumed, because the hazard is not shell-specific: the
        # status a caller receives is the LAST process's. Running a trivial
        # second process after a failing first one is exactly the `; echo $?`
        # shape, and it must come back 0 while the file still says 3.
        sp3 = os.path.join(tmp, 'c.status')
        real = run(sp3, [sys.executable, '-c', 'import sys; sys.exit(3)'])
        trailing = subprocess.call([sys.executable, '-c', 'print("EXIT=3")'])
        _, filed, _ = read_status(sp3)
        arm('the TRAILING element reports 0 -- the defect, reproduced',
            trailing == 0, 'trailing returned %r' % (trailing,))
        arm('while the status FILE still says 3 -- the fix, measured',
            real == 3 and filed == 3, 'file %r, wrapper %r' % (filed, real))

        # ── THE --read CLI, NOT read_status() ────────────────────────────────
        # Added after --read raised AttributeError on its FIRST REAL USE: a
        # `.strip()` inside the %-format parentheses bound to the tuple. Every
        # arm above passed, because every arm above called read_status()
        # directly and none of them went through the CLI that wraps it. A
        # strong lock over one half of a tool says nothing about the other half,
        # which is a sentence I wrote about a different tool the day before.
        def _cli(*args):
            r = subprocess.run([sys.executable, os.path.abspath(__file__)] + list(args),
                               capture_output=True, text=True, encoding='utf-8',
                               errors='replace')
            return r.returncode, (r.stdout or '') + (r.stderr or '')

        rc, out = _cli('--read', sp3)
        arm('--read EXITS WITH THE RECORDED CODE and does not traceback',
            rc == 3 and 'Traceback' not in out, 'rc=%r out=%r' % (rc, out[:160]))
        arm('...and prints the state it read', 'EXIT 3' in out, out[:160])

        rc, out = _cli('--read', os.path.join(tmp, 'does-not-exist.status'))
        arm('--read on an ABSENT file exits 2 COULD NOT RUN, NEVER 0 -- the '
            'negative half, and the only arm that would have caught a wrapper '
            'returning success for a file it never found',
            rc == 2 and 'ABSENT' in out, 'rc=%r out=%r' % (rc, out[:160]))

        rc, out = _cli('--read', sp2)          # left UNREADABLE above
        arm('--read on an UNREADABLE file exits 2, not 0 and not 1',
            rc == 2, 'rc=%r' % (rc,))

        rc, out = _cli('--status', os.path.join(tmp, 'z.status'))
        arm('a run with --status and NOTHING TO RUN is an argument error, not a '
            'silent success', rc != 0, 'rc=%r' % (rc,))

        # ── THE BOUND, DRIVEN WITH A COMMAND THAT REALLY OUTLASTS IT ────────
        # cc's finding, 2026-10-06: a run the live 600s hook ceiling would kill
        # recorded EXIT 0, because nothing here imposed a bound. The arm is a
        # child that sleeps 30s under a 1s bound -- a real overrun, not a
        # mocked one -- and the thing that must NOT appear is an exit code.
        spb = os.path.join(tmp, 'bound.status')
        _t0 = time.time()
        code = run(spb, [sys.executable, '-c', 'import time; time.sleep(30)'],
                   bound=1)
        _elapsed = time.time() - _t0
        state, filed, rest = read_status(spb)
        arm('A COMMAND THAT OUTLASTS THE BOUND IS COULD_NOT_RUN, NOT AN EXIT '
            'CODE -- cc\'s finding, driven',
            code is None and state == COULD_NOT_RUN,
            'returned %r, file %s/%r' % (code, state, filed))
        arm('...and the record NAMES the timeout and its bound, so a reader can '
            'tell it from a child that never started',
            'TIMEOUT_1s' in rest, 'rest=%r' % (rest,))
        arm('...and NO exit code is recorded at all -- the negative half, and '
            'the only arm that would catch a bound that reported 0 or 124',
            filed is None, 'file code %r' % (filed,))
        arm('...and the recorder RETURNED rather than waiting out the child, '
            'measured, so the bound is real and not decorative',
            _elapsed < 20, 'elapsed %.1fs for a 30s child under a 1s bound'
            % (_elapsed,))
        rc, out = _cli('--read', spb)
        arm('--read on a TIMEOUT record exits 2 COULD NOT RUN, never 0',
            rc == 2 and COULD_NOT_RUN in out, 'rc=%r out=%r' % (rc, out[:120]))

        # PAIRED POSITIVE: without it, every arm above passes on a bound that
        # fires unconditionally.
        spb2 = os.path.join(tmp, 'bound_ok.status')
        code = run(spb2, [sys.executable, '-c', 'pass'], bound=60)
        state, filed, _ = read_status(spb2)
        arm('PAIRED POSITIVE: a child that finishes INSIDE the bound still '
            'records its real EXIT 0',
            code == 0 and state == EXIT and filed == 0,
            'returned %r, file %s/%r' % (code, state, filed))
        code = run(spb2, [sys.executable, '-c', 'import sys; sys.exit(3)'], bound=60)
        _, filed, _ = read_status(spb2)
        arm('...and a failing child inside the bound still records 3, so the '
            'bound did not flatten the code',
            code == 3 and filed == 3, 'returned %r, file %r' % (code, filed))

        # BACKWARD COMPATIBILITY, asserted rather than assumed: no bound at all
        # must behave exactly as before.
        spb3 = os.path.join(tmp, 'nobound.status')
        code = run(spb3, [sys.executable, '-c', 'import sys; sys.exit(7)'])
        _, filed, _ = read_status(spb3)
        arm('BACKWARD COMPATIBLE: with no bound the old path is taken and the '
            'real code is recorded', code == 7 and filed == 7,
            'returned %r, file %r' % (code, filed))
        rc, out = _cli('--status', os.path.join(tmp, 'cli_b.status'),
                       '--bound', '1', '--',
                       sys.executable, '-c', 'import time; time.sleep(30)')
        arm('and the --bound CLI exits 2 on a timeout rather than a code, '
            'through the CLI and not just the function',
            rc == 2, 'rc=%r out=%r' % (rc, out[:160]))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print('  criteria lock: %d arms, %d of them negative, and %d through the CLI '
          'rather than the function (criteria %s)'
          % (tally['n'], tally['neg'], tally['cli'], CRITERIA_VERSION))
    return ok


def main():
    ap = argparse.ArgumentParser(
        description='run a command and write ITS real exit status to a file')
    ap.add_argument('--status', help='path the real status is written to')
    ap.add_argument('--fixtures', action='store_true',
                    help='run the self-check alone and stop')
    ap.add_argument('--bound', type=float, metavar='SECONDS',
                    help='kill the child after SECONDS and record COULD_NOT_RUN '
                         'TIMEOUT -- never an exit code, because a killed run '
                         'produced no verdict. Omit for the old unbounded wait')
    ap.add_argument('--read', metavar='FILE',
                    help='print a status file and EXIT WITH ITS CODE; '
                         'ABSENT/RUNNING/UNREADABLE exit 2 (COULD NOT RUN), never 0')
    ap.add_argument('cmd', nargs=argparse.REMAINDER,
                    help='-- then the command to run')
    a = ap.parse_args()

    if a.fixtures:
        print('CAPTURE EXIT -- self-check (criteria %s)' % CRITERIA_VERSION)
        return 0 if _fixtures() else 1

    if a.read:
        state, code, rest = read_status(a.read)
        # The .strip() used to sit INSIDE the %-format parentheses, so it bound
        # to the tuple and raised AttributeError on the first real use of
        # --read. The arms below did not catch it because they tested
        # read_status() and never the CLI around it: A STRONG LOCK OVER ONE HALF
        # OF A TOOL SAYS NOTHING ABOUT THE OTHER HALF.
        print(('%s %s %s' % (state, '' if code is None else code, rest)).strip())
        if state == EXIT:
            return code
        # NOT 0. "I cannot tell you the status" is the third state and folding
        # it into success is the defect this file was written against.
        print('  NOT a verdict about the program -- the status is not yet known',
              file=sys.stderr)
        return 2

    argv = [x for x in a.cmd if x != '--'] if a.cmd and a.cmd[0] == '--' else a.cmd
    if not argv:
        ap.error('nothing to run: pass --fixtures, --read FILE, or -- <command>')
    if not a.status:
        ap.error('--status is required: a status file nobody can name is a status '
                 'nobody will read')

    code = run(a.status, argv, bound=a.bound)
    if code is None:
        print('capture_exit: COULD NOT RUN -- see %s' % a.status, file=sys.stderr)
        return 2
    return code


if __name__ == '__main__':
    sys.exit(main())
