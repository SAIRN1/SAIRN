#!/usr/bin/env python
"""wait_for.py -- wait for a condition, and STOP when the thing you are waiting
on has died.

    python tools/wait_for.py --file <path> --pid <n> [--timeout 3600]
    python tools/wait_for.py --grep "ALL .* PASS" --file <path> --pid <n>
    python tools/wait_for.py --pid <n>                    # just outlive it

WHY THIS EXISTS, AND IT IS A MEASURED COST RATHER THAN A TIDINESS ARGUMENT.
On 2026-09-25 a waiter was armed as an inline shell loop:

    until [ "$(tail -c 200 <file> | grep -c 'ASSERTIONS PASS|ARM(S) FAILED')" -gt 0 ]
    do sleep 15; done

Three minutes later the process producing that file was KILLED -- deliberately,
because its spy had gone blind and it was running a 590-file suite by mistake.
The sentinel string could then never appear. **The waiter polled every fifteen
seconds for FOURTEEN HOURS** and was still going when somebody asked what was
running. It held no lock and cost no real CPU; what it cost was a process list
nobody could read and a status report that had to start by explaining it.

THE BUG IS NOT THE SLEEP. It is that the loop's exit condition mentioned only
SUCCESS. A watcher whose only terminal state is the happy path cannot tell
"still working" from "dead", and those are the two answers that matter.

SAME SHAPE AS A RULE THIS PLATFORM ALREADY WROTE DOWN. The Monitor guidance in
this repo says: *if this process crashed right now, would my filter emit
anything?* -- and the ablation monitor on the same day got it right, checking
both the output file and the PID. This file is that pattern made reusable so it
does not depend on remembering.

── EVERY EXIT IS NAMED, AND "GONE" IS NOT "DONE" ──────────────────────────────
    0  CONDITION MET      the file appeared / matched while the process lived
    3  WATCHED PID GONE   it exited without the condition ever being met. NOT a
                          success. The caller must treat this as "the work did
                          not finish", which is the whole point.
    4  TIMEOUT            neither happened inside the deadline
    2  COULD NOT RUN      bad arguments, unreadable file -- never folded into 0

A watcher that exited 0 when its subject died would be worse than the loop it
replaces: it would report success for work that never happened.
"""
import argparse
import io
import os
import re
import subprocess
import sys
import time

EXIT_MET = 0
EXIT_COULD_NOT_RUN = 2
EXIT_PID_GONE = 3
EXIT_TIMEOUT = 4


def pid_alive(pid):
    """True / False / None, and None is a THIRD ANSWER that must not read as dead.

    An unreadable process table is not a dead process. Returning False there
    would make this tool report PID GONE for a subject that is running, which
    is the same class of lie as reporting success for one that died.
    """
    if os.name == 'nt':
        r = subprocess.run(['tasklist', '/FI', 'PID eq %d' % pid, '/NH', '/FO', 'CSV'],
                           capture_output=True, text=True, encoding='utf-8',
                           errors='replace')
        if r.returncode != 0:
            return None
        return ('"%d"' % pid) in (r.stdout or '')
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True          # exists, not ours
    except OSError:
        return None


def condition_met(path, pattern):
    if path is None:
        return False
    if not os.path.isfile(path):
        return False
    if pattern is None:
        return os.path.getsize(path) > 0
    try:
        with io.open(path, encoding='utf-8', errors='replace') as fh:
            return re.search(pattern, fh.read()) is not None
    except OSError:
        return False


def main(argv):
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument('--file')
    ap.add_argument('--grep')
    ap.add_argument('--pid', type=int)
    ap.add_argument('--interval', type=float, default=15.0)
    ap.add_argument('--timeout', type=float, default=3600.0)
    a = ap.parse_args(argv)

    if a.file is None and a.pid is None:
        sys.stderr.write('COULD NOT RUN: give --file, --pid, or both. With '
                         'neither there is nothing to wait for.\n')
        return EXIT_COULD_NOT_RUN
    if a.grep and a.file is None:
        sys.stderr.write('COULD NOT RUN: --grep needs --file to search.\n')
        return EXIT_COULD_NOT_RUN
    if a.grep:
        try:
            re.compile(a.grep)
        except re.error as e:
            sys.stderr.write('COULD NOT RUN: --grep is not a valid regex: %s\n' % e)
            return EXIT_COULD_NOT_RUN

    # ── THE CONDITION IS CHECKED FIRST, BEFORE ANY LIVENESS TEST ────────────
    # A process can finish between being launched and this tool starting. If the
    # PID check ran first it would report PID GONE for work that COMPLETED, and
    # a false "did not finish" is as misleading as a false success.
    if condition_met(a.file, a.grep):
        print('CONDITION MET immediately: %s' % (a.grep or 'file is non-empty'))
        return EXIT_MET

    deadline = time.time() + a.timeout
    unknown_streak = 0
    while time.time() < deadline:
        if condition_met(a.file, a.grep):
            print('CONDITION MET: %s' % (a.grep or 'file is non-empty'))
            return EXIT_MET
        if a.pid is not None:
            alive = pid_alive(a.pid)
            if alive is False:
                # RE-CHECK THE CONDITION ONCE MORE. The subject may have written
                # its last line and exited between the two checks above; calling
                # that PID GONE would discard a completed run.
                if condition_met(a.file, a.grep):
                    print('CONDITION MET (on the subject\'s final write): %s'
                          % (a.grep or 'file is non-empty'))
                    return EXIT_MET
                sys.stderr.write(
                    'WATCHED PID GONE: pid %d has exited and the condition was '
                    'never met.\nThis is NOT a success -- the work did not '
                    'finish. %s\n'
                    % (a.pid, ('file %r %s' % (a.file, 'is absent'
                       if a.file and not os.path.isfile(a.file) else 'never matched'))
                       if a.file else 'No output file was being watched.'))
                return EXIT_PID_GONE
            if alive is None:
                # COULD NOT TELL is not dead. Counted and reported rather than
                # guessed, so a broken process table shows up as itself.
                unknown_streak += 1
                if unknown_streak in (4, 40):
                    sys.stderr.write('NOTE: the process table has been '
                                     'unreadable for %d checks; liveness is '
                                     'UNKNOWN, not dead. Still waiting.\n'
                                     % unknown_streak)
            else:
                unknown_streak = 0
        time.sleep(a.interval)

    sys.stderr.write('TIMEOUT after %.0fs: the condition was never met%s. NOT a '
                     'success.\n' % (a.timeout,
                                     '' if a.pid is None
                                     else ' and pid %d is %s' % (
                                         a.pid, {True: 'still alive',
                                                 False: 'gone',
                                                 None: 'of unknown state'}[pid_alive(a.pid)])))
    return EXIT_TIMEOUT


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
