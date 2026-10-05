#!/usr/bin/env python
"""Control for tools/push_retry.py -- its USAGE path must not crash.

# REQUIREMENT: `python tools/push_retry.py` with no arguments prints usage and
#   exits WITHOUT a traceback, on a console whose encoding cannot represent the
#   docstring's box-drawing characters.

WHY THIS ARM EXISTS AND WHY IT IS NOT COSMETIC. Found 2026-10-05: the no-args
path falls through to `print(__doc__.strip())`, the docstring carries U+2500,
and on Windows the console is cp1252 -- which has no mapping for it. So:

    UnicodeEncodeError: 'charmap' codec can't encode characters in
    position 143-144: character maps to <undefined>

This is the tool whose whole purpose is to stop a lost push race from amending
one session's work onto another session's commit. The first thing a session
reaching for it does is run it to see how it works, and it answered with a
traceback; the only way past was reading the source for `--loop --attempts`.
A safety tool that cannot explain itself is a safety tool nobody uses.

THE ENCODING IS FORCED, NOT INHERITED. Running the tool and seeing it pass
proves nothing on a machine where the ambient encoding already happens to be
utf-8 -- the arm would be green for a reason that has nothing to do with the
fix. So arm A2 runs it with PYTHONIOENCODING=cp1252 explicitly, which is the
condition that produced the crash. Without that this control could pass on a
broken tool, which is the failure mode it is built to refuse.

AND IT IS SCOPED. This file does NOT run the retry loop: that fetches, rebases
and pushes against a shared branch, and a control that pushes is a control that
has side effects on four other clones. Only the paths that are safe to drive
with no repository consequences are driven here, and that limit is stated
rather than left for a reader to infer from what is missing.

Run:  python tests/run_push_retry_probe.py
"""
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(REPO, 'tools', 'push_retry.py')

CRITERIA_VERSION = '2026-10-05.1'

_pass = _fail = 0


def ok(n):
    global _pass
    _pass += 1
    sys.stdout.write('  ok   %s\n' % n)


def bad(n, why):
    global _fail
    _fail += 1
    sys.stdout.write('  FAIL %s\n       %s\n' % (n, str(why)[:600]))


def run(args, encoding=None):
    env = dict(os.environ)
    if encoding:
        env['PYTHONIOENCODING'] = encoding
    else:
        env.pop('PYTHONIOENCODING', None)
    r = subprocess.run([sys.executable, TOOL] + list(args), cwd=REPO, env=env,
                       capture_output=True, timeout=180)
    # BYTES, decoded permissively HERE rather than by subprocess, so a mangled
    # byte in the tool's output cannot be mistaken for a crash in the tool.
    out = (r.stdout or b'').decode('utf-8', 'replace') + \
          (r.stderr or b'').decode('utf-8', 'replace')
    return r.returncode, out


def main():
    if not os.path.isfile(TOOL):
        sys.stderr.write('COULD NOT RUN: tools/push_retry.py is absent. This '
                         'control tested nothing, which is not a pass.\n')
        return 2
    sys.stdout.write('PUSH RETRY CONTROL -- criteria %s\n' % CRITERIA_VERSION)

    sys.stdout.write('\nA. THE USAGE PATH MUST NOT CRASH\n')

    code, out = run([])
    if code == 0 and 'Traceback' not in out:
        ok('A1. no arguments: exits 0 with no traceback')
    else:
        bad('A1. the no-args usage path must not crash',
            'exit=%s\n%s' % (code, out[-500:]))

    # THE ARM THAT MATTERS. cp1252 is the condition that produced the crash; a
    # green A1 on a utf-8 console says nothing about the fix.
    code, out = run([], encoding='cp1252')
    if code == 0 and 'UnicodeEncodeError' not in out and 'Traceback' not in out:
        ok('A2. KNOWN-BAD CONDITION FORCED: with PYTHONIOENCODING=cp1252 -- '
           'the Windows console default, and exactly what crashed it -- it '
           'still exits 0 with no UnicodeEncodeError. Without this arm A1 '
           'could pass on an unfixed tool merely because the ambient encoding '
           'happened to be utf-8')
    else:
        bad('A2. usage must survive a cp1252 stdout',
            'exit=%s\n%s' % (code, out[-600:]))

    if 'REFUSES TO AMEND' in out:
        ok('A3. ...and the usage TEXT actually arrives -- exit 0 with empty '
           'output would satisfy A2 while telling the reader nothing, which is '
           'the same silence one step over')
    else:
        bad('A3. the usage text must be printed, not just not-crash',
            out[-400:])

    sys.stdout.write('\nB. THE GUARD STILL ANSWERS, AND ON stderr\n')

    # --check prints its refusal REASONS to stderr. A guard whose refusal
    # cannot be encoded fails open at the moment it is trying to stop something,
    # so stderr is reconfigured too and this drives that path under cp1252.
    code, out = run(['--check'], encoding='cp1252')
    if 'Traceback' not in out and code in (0, 3):
        ok('B1. `--check` under cp1252 returns a real verdict (exit %d: 0 safe '
           '/ 3 refused) with no traceback. Its refusal reasons print to '
           'stderr, so stderr needed the same treatment as stdout -- a guard '
           'that cannot print WHY it refused is one that gets ignored' % code)
    else:
        bad('B1. --check must answer under cp1252',
            'exit=%s\n%s' % (code, out[-600:]))

    if ('AMEND IS SAFE' in out) or ('AMEND IS REFUSED' in out):
        ok('B2. ...and it says which, in words, rather than only in the exit '
           'code')
    else:
        bad('B2. --check must state its verdict in words', out[-400:])

    sys.stdout.write('\nC. THE SOURCE-LEVEL GUARD, so a future edit cannot '
                     'undo this quietly\n')

    import io as _io
    src = _io.open(TOOL, encoding='utf-8').read()
    has_non_ascii = any(ord(c) > 127 for c in src)
    has_reconf = 'sys.stdout.reconfigure' in src
    if has_non_ascii and has_reconf:
        ok('C1. the file still carries non-ASCII AND still reconfigures '
           'stdout. Pinned as a PAIR deliberately: the fix is not "remove the '
           'box rules" -- every tool here uses them, so stripping them would '
           'fix one file and leave the pattern')
    elif not has_non_ascii:
        bad('C1. the docstring was ASCII-ed instead of the stream being fixed',
            'that fixes this file and leaves the pattern in the other ~236')
    else:
        bad('C1. sys.stdout.reconfigure has been removed', 'the crash returns')

    if 'sys.stderr.reconfigure' in src:
        ok('C2. and stderr too -- see B1')
    else:
        bad('C2. stderr must be reconfigured as well',
            'refusal reasons print there')

    sys.stdout.write('\n%d passed, %d failed\n' % (_pass, _fail))
    return 1 if _fail else 0


if __name__ == '__main__':
    sys.exit(main())
