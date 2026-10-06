#!/usr/bin/env python
"""hover2_exit_capture.py -- this role's OWN exit-code recorder, independent
of tools/capture_exit.py (cody's -- a build-agent tool). Built because the
STANDING instruction and item 14 both named an exit-code recorder this role
had been using all batch without ever having built it: every "EXIT N ..."
cited earlier in this batch came from cody's tool, a dependency this role's
own rule (never run or depend on a build-agent tool for the sweep/finding
method) had already been violating without being caught until now.

GOALS:
  - Run a command and write ITS real exit code to a file, so a reader never
    has to trust a harness's own completion status (the Rule E shape:
    "a harness completion status is never an exit code").
  - Read that file back and exit with the SAME code, so a chain of shell
    commands (pipes, &&/||) cannot launder the real verdict into something
    else -- the exact hook warning that has fired on this role's own
    commands repeatedly this session.
  - A third state for a status file that is ABSENT, still being written,
    or unreadable -- never folded into "0 i.e. clean".

NON-GOALS:
  - Not a general process supervisor. No retries, no timeout/backoff, no
    stderr-phrase classification (that question belongs to a DIFFERENT
    tool, hover2_claim_reexecute.py, built a prior batch for a different
    purpose -- classifying WHY a subprocess failed. This tool only
    records WHAT code it returned).
  - Not an attempt to match cody's tool feature-for-feature (its own
    17-arm --fixtures suite, its ambient-credential proof, etc.). Minimum
    viable recorder for this role's own use, nothing shared or copied.
  - Does not call, import, or shell out to tools/capture_exit.py anywhere.

ALTERNATIVES CONSIDERED:
  1. Inline `cmd; echo $?` in each Bash call -- rejected: this IS the
     failure mode the PreToolUse hook has flagged on this role's own
     commands multiple times this session (a pipe or chain reports the
     LAST command's status, not the one being judged).
  2. Capture $? immediately after a bare command with no file -- rejected:
     survives one bash call but not a backgrounded command or a second
     tool reading the result later; a file is the only thing a SEPARATE
     --read invocation can check.
  3. Reuse tools/capture_exit.py as a caller (adopt, don't edit) -- this is
     what every build agent on this platform has done with it, and what
     this role itself was doing all batch. REJECTED HERE SPECIFICALLY
     because the explicit instruction this batch is "do not run or depend
     on any build-agent tool" for this role's own method -- an exit-code
     recorder every finding's evidence rests on is squarely inside that
     rule, not an exception to it the way read-only evidence-gathering
     over hank's gate_parity_check.py output was explicitly carved out to
     be in item 2.

CROSS-CUTTING CONCERNS:
  - Windows host: subprocess.run(cmd, shell=True) invokes cmd.exe here, not
    bash -- Rule H's own finding. That rule was about classifying a
    FAILURE'S WORDING; this tool never inspects stdout/stderr content, only
    the integer returncode subprocess.run() reports, which is the real
    exit status on either shell. Not the same hazard.
  - Status file path is always caller-supplied (same convention as cody's
    tool) so this role controls where it lands; never defaults to a
    platform-wide location.
  - Atomic write (temp file + os.replace) so a concurrent --read can never
    observe a half-written record.

Usage:
  python hover2_exit_capture.py --status PATH -- CMD [ARGS...]
  python hover2_exit_capture.py --read PATH
  python hover2_exit_capture.py --selftest
"""
import argparse
import os
import subprocess
import sys
import tempfile
import time


def write_status(path, code, cmd):
    ts = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    line = 'EXIT %d %s %s\n' % (code, ts, ' '.join(cmd))
    d = os.path.dirname(os.path.abspath(path)) or '.'
    fd, tmp = tempfile.mkstemp(dir=d, prefix='.hover2exit-')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(line)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def do_run(status_path, cmd):
    proc = subprocess.run(cmd)
    write_status(status_path, proc.returncode, cmd)
    return proc.returncode


def do_read(path):
    if not os.path.isfile(path):
        print('ABSENT: %s does not exist' % path)
        return 2
    try:
        with open(path, encoding='utf-8') as f:
            content = f.read().strip()
    except OSError as e:
        print('UNREADABLE: %s (%s)' % (path, e))
        return 2
    if not content.startswith('EXIT '):
        print('UNREADABLE: %s does not start with EXIT' % path)
        return 2
    print(content)
    try:
        code = int(content.split()[1])
    except (IndexError, ValueError):
        print('UNREADABLE: could not parse exit code from %r' % content)
        return 2
    return code


def main():
    argv = sys.argv[1:]
    if argv and argv[0] == '--selftest':
        sys.exit(selftest())
    if argv and argv[0] == '--read':
        if len(argv) < 2:
            print('usage: --read PATH')
            sys.exit(2)
        sys.exit(do_read(argv[1]))
    if argv and argv[0] == '--status':
        if len(argv) < 2:
            print('usage: --status PATH -- CMD [ARGS...]')
            sys.exit(2)
        status_path = argv[1]
        rest = argv[2:]
        if rest and rest[0] == '--':
            rest = rest[1:]
        if not rest:
            print('usage: --status PATH -- CMD [ARGS...]')
            sys.exit(2)
        sys.exit(do_run(status_path, rest))
    print(__doc__.strip().splitlines()[-4:])
    sys.exit(2)


def selftest():
    d = tempfile.mkdtemp()
    status0 = os.path.join(d, 'status0.txt')
    status7 = os.path.join(d, 'statusN.txt')
    missing = os.path.join(d, 'nope.txt')

    code0 = do_run(status0, [sys.executable, '-c', 'import sys; sys.exit(0)'])
    code7 = do_run(status7, [sys.executable, '-c', 'import sys; sys.exit(7)'])

    read0 = do_read(status0)
    read7 = do_read(status7)
    read_missing = do_read(missing)

    ok = (code0 == 0 and code7 == 7 and
          read0 == 0 and read7 == 7 and read_missing == 2)
    print('SELFTEST %s: known-0 run=%d read=%d; known-7 run=%d read=%d; missing read=%d (expect 2)' %
          ('PASS' if ok else 'FAIL', code0, read0, code7, read7, read_missing))
    return 0 if ok else 1


if __name__ == '__main__':
    main()
