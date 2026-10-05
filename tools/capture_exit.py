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

CRITERIA_VERSION = '2026-10-05.1'

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


def run(status_path, argv, cwd=None):
    """Run argv, record the real status, return it. Never raises on child failure."""
    shown = ' '.join(argv)
    _write(status_path, '%s %d %s %s' % (RUNNING, os.getpid(), _now(), shown))
    try:
        proc = subprocess.Popen(argv, cwd=cwd)
    except OSError as exc:
        _write(status_path, '%s %s %s %s' % (COULD_NOT_RUN, exc.__class__.__name__, _now(), shown))
        return None
    code = proc.wait()
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

    def arm(label, cond, detail=''):
        nonlocal ok
        if not cond:
            ok = False
        print('  %-4s %s%s' % ('ok' if cond else 'FAIL', label, (' -- ' + detail) if detail else ''))

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
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print('  criteria lock: 12 arms, 4 of them negative (criteria %s)' % CRITERIA_VERSION)
    return ok


def main():
    ap = argparse.ArgumentParser(
        description='run a command and write ITS real exit status to a file')
    ap.add_argument('--status', help='path the real status is written to')
    ap.add_argument('--fixtures', action='store_true',
                    help='run the self-check alone and stop')
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
        print('%s %s %s' % (state, '' if code is None else code, rest).strip())
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

    code = run(a.status, argv)
    if code is None:
        print('capture_exit: COULD NOT RUN -- see %s' % a.status, file=sys.stderr)
        return 2
    return code


if __name__ == '__main__':
    sys.exit(main())
