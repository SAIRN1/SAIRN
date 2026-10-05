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

CRITERIA_VERSION = '2026-10-05.2'

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

    sys.stdout.write('\nD. THE LOOP CAN FIX THE FAILURE IT IS NAMED FOR\n')

    # ── WHY THESE ARE SOURCE-LEVEL ARMS ────────────────────────────────────
    # Driving cmd_loop() for real means fetch, rebase and PUSH against a branch
    # four other clones share. A control with side effects on other people's
    # work is not a control, so the two defects are pinned structurally: the
    # remedy must not be reachable only from the rebase branch, and the
    # refusal must not be printed from the tail. Stated rather than left as an
    # unexplained gap -- see the header.
    import inspect
    sys.path.insert(0, os.path.join(REPO, 'tools'))
    import push_retry as _pr

    loop_src = inspect.getsource(_pr.cmd_loop)

    if hasattr(_pr, '_regenerate_and_fold'):
        ok('D1. the regenerate-and-fold step is its OWN function. It used to '
           'live inside `if behind > 0:`, so with nothing to rebase the loop '
           'could not reach the remedy at all -- observed 2026-10-05 as six '
           'attempts, six identical "failed to push some refs" lines, and a '
           'push refused the whole time for three stale generated documents')
    else:
        bad('D1. the remedy must be callable from both paths',
            '_regenerate_and_fold is absent')

    # It must be called from the REFUSAL path, not only after a rebase. Counted,
    # because one call site is the old behaviour wearing a new name.
    n_calls = loop_src.count('_regenerate_and_fold()')
    if n_calls >= 2:
        ok('D2. ...and cmd_loop calls it from %d sites -- after a successful '
           'rebase AND after a push refusal. ONE call site would be the old '
           'behaviour with a new name, which is why this arm counts them'
           % n_calls)
    else:
        bad('D2. the remedy must be reached from the refusal path too',
            'only %d call site(s)' % n_calls)

    # MATCHED ON THE CODE FORM, NOT THE BARE STRING. The first version of this
    # arm checked `'tail[-6:]' not in loop_src` and FAILED -- on the comment I
    # had just written to explain that `tail[-6:]` was the old behaviour. A
    # source-level arm that greps for a token matches the prose documenting the
    # token, so it has to grep for something only the CODE can contain. Left in
    # rather than tidied: this is PR 1.2 (grep cannot tell code from text that
    # describes code) committed inside a control written the same hour.
    _code_lines = [l for l in loop_src.split('\n')
                   if not l.lstrip().startswith('#')]
    _code = '\n'.join(_code_lines)
    if 'tail[-6:]' not in _code and 'lines[:14]' in _code:
        ok('D3. the refusal is printed HEAD-ANCHORED. The push gate writes its '
           '`Blocked:` header and the fix command at the TOP and git\'s '
           'generic error at the BOTTOM, so `tail[-6:]` reliably printed the '
           'least informative six lines -- which is how six attempts produced '
           'six useless messages')
    else:
        bad('D3. the refusal must not be printed from the tail',
            'tail[-6:] still present, or the head slice is gone')

    if 'carrying a remedy' in loop_src:
        ok('D4. ...and when the output is longer than the head slice, the '
           'lines carrying a REMEDY are pulled out rather than dropped, so a '
           'truncation cannot hide the one line that says what to do')
    else:
        bad('D4. remedy-bearing lines must survive truncation', '')

    if 'git said nothing on either stream' in loop_src:
        ok('D5. a refusal with NO text on either stream is reported as itself '
           'rather than printed as an empty block -- a push that fails '
           'silently is not diagnosable, and saying so beats showing nothing')
    else:
        bad('D5. an empty refusal must be named', '')

    sys.stdout.write('\n%d passed, %d failed\n' % (_pass, _fail))
    return 1 if _fail else 0


if __name__ == '__main__':
    sys.exit(main())
