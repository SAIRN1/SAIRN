#!/usr/bin/env python
"""Runs a command and reports ITS real exit code, captured directly by this
role's own subprocess call -- never a harness completion-status message,
never a status file written by a recorder this role did not build.

Own tool, own location. Built 2026-10-06 (H1, batch I, item 12). Design
logged (seq 984) before this file was written. tools/capture_exit.py is
cody's (per hank's own claim text this session: "tools/capture_exit.py is
ALSO CODY'S -- adopted as a CALLER, not edited") -- every exit code this
role cites from here forward is captured by THIS tool instead.

THREE STATES: a real 0, a real nonzero, or COULD_NOT_RUN (timeout / launch
failure) -- the third never folded into either of the first two.
"""
import subprocess
import sys

DEFAULT_TIMEOUT = 120

_NOT_FOUND_PHRASES = (
    'is not recognized as an internal or external command',
    'command not found',
)


def capture(command, cwd=None, timeout=DEFAULT_TIMEOUT):
    try:
        p = subprocess.run(command, shell=True, cwd=cwd, capture_output=True,
                            text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {'state': 'COULD_NOT_RUN', 'reason': 'timed out after %ds' % timeout}
    except OSError as e:
        return {'state': 'COULD_NOT_RUN', 'reason': 'process did not launch: %s' % e}
    output = (p.stdout or '') + (p.stderr or '')
    if any(phrase in output for phrase in _NOT_FOUND_PHRASES):
        return {'state': 'COULD_NOT_RUN', 'reason': 'shell reported command not found'}
    return {'state': 'EXIT', 'exit_code': p.returncode, 'stdout': p.stdout, 'stderr': p.stderr}


def _selftest():
    ok = 0
    r1 = capture('python -c "import sys; sys.exit(0)"')
    status1 = 'ok  ' if (r1['state'] == 'EXIT' and r1['exit_code'] == 0) else 'FAIL'
    if status1 == 'ok  ':
        ok += 1
    print('  %s known-0 command -> %r' % (status1, r1))

    r2 = capture('python -c "import sys; sys.exit(7)"')
    status2 = 'ok  ' if (r2['state'] == 'EXIT' and r2['exit_code'] == 7) else 'FAIL'
    if status2 == 'ok  ':
        ok += 1
    print('  %s known-7 command -> %r' % (status2, r2))

    r3 = capture('this_binary_does_not_exist_anywhere_xyz')
    status3 = 'ok  ' if r3['state'] == 'COULD_NOT_RUN' else 'FAIL'
    if status3 == 'ok  ':
        ok += 1
    print('  %s nonexistent command -> %s, never forced into a fake exit code' % (status3, r3['state']))

    # Regression fixture, 2026-10-07 (H1 batch O, item 5): the bug was in
    # main()'s OWN argv dispatch, not in capture() -- '--selftest' used to be
    # checked before '--run', so an argv list carrying BOTH (wrapping a
    # command that itself takes a --selftest flag) ran THIS wrapper's own
    # 3-fixture selftest instead of dispatching to --run. Calls main()
    # directly with the exact shape that reproduced it, and checks the
    # returned exit code is the WRAPPED command's real exit code (9), not
    # this wrapper's own selftest return value (0 or 1). 'exit(9)', not
    # 'import sys; sys.exit(9)' -- the join-with-spaces limitation already
    # documented on --run means a space/semicolon-bearing -c argument does
    # not survive re-quoting, confirmed by this fixture initially failing
    # for exactly that reason before being corrected to a space-free form.
    import io
    import contextlib
    test_argv = ['--run', sys.executable, '-c', 'exit(9)', '--selftest']
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc4 = main(test_argv)
    status4 = 'ok  ' if rc4 == 9 else 'FAIL'
    if status4 == 'ok  ':
        ok += 1
    print('  %s main() with --run ... --selftest in the SAME argv dispatches to --run (exit 9), not swallowed by this wrapper\'s own selftest -> got exit %r' % (status4, rc4))

    print('%d/4 fixture checks correct' % ok)
    return ok == 4


def main(argv):
    # ── '--run' CHECKED FIRST, 2026-10-07 (H1 batch O, item 5) ──────────────
    # Real bug, reproduced before this fix: `--selftest` used to be checked
    # BEFORE `--run`, so `hover_own_exit_capture.py --run python some_tool.py
    # --selftest` (wrapping a command that itself takes a --selftest flag)
    # silently ran THIS WRAPPER's own 3-fixture selftest instead of the
    # wrapped command -- `'--selftest' in argv` is true for the whole argv
    # list regardless of where it appears, so any wrapped command containing
    # that flag was swallowed. Checking '--run' first means its own
    # everything-after-this-flag command string is dispatched before the
    # bare 'is --selftest anywhere in argv' check ever runs; the wrapper's
    # own selftest now only fires when '--run' is genuinely absent.
    if '--run' in argv:
        i = argv.index('--run')
        # KNOWN LIMITATION, found on first real use: re-joining argv with
        # spaces loses any quoting the caller intended (a -c "..." Python
        # one-liner splits apart). Prefer `from hover_own_exit_capture import
        # capture` and call it directly with the real command string -- the
        # CLI form is for simple, unquoted commands only.
        cmd = ' '.join(argv[i + 1:])
        r = capture(cmd)
        if r['state'] == 'COULD_NOT_RUN':
            print('COULD NOT RUN: %s' % r['reason'])
            return 2
        print('EXIT %d' % r['exit_code'])
        if r['stdout']:
            sys.stdout.write(r['stdout'])
        if r['stderr']:
            sys.stderr.write(r['stderr'])
        return r['exit_code']
    if '--selftest' in argv:
        return 0 if _selftest() else 1
    print('usage: hover_own_exit_capture.py --selftest | --run COMMAND...')
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
