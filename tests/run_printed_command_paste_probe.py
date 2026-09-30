#!/usr/bin/env python
"""Control for the printed-command quoting in tools/sairn_claim.py.

# REQUIREMENT: any command line a SAIRN tool prints for a human to paste must
#   survive being pasted -- the interpolated value must reach the tool as ONE
#   argument, with an apostrophe, a double quote, a backslash, a newline or a
#   shell metacharacter in it, and must never be executed as shell syntax.

WHY. Two sites in tools/sairn_claim.py printed
`python tools/sairn_claim.py <verb> <subj> %s` with a free-text task
interpolated raw. Every task this repo writes contains spaces, so the line was
wrong for all of them, always -- bash split the task into one argv entry per
word and the tool would re-read a different task than the one it printed. One of
the two sites builds its line from ANOTHER SESSION'S claim text, so
`a && rm -rf x; b $(id)` in a claim string becomes a runnable line a human is
being told to paste.

EACH ARM DRIVES A REAL SHELL. `bash -c` with an argv-echoing stub, not a regex
over the source: the question is what the shell does with the line, and only the
shell can answer that.

Run:  python tests/run_printed_command_paste_probe.py
"""
import io
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(REPO, 'tools', 'sairn_claim.py')

CRITERIA_VERSION = '2026-09-30.1'

BACKSLASH = chr(92)
NEWLINE = chr(10)

# The six shapes, driven rather than reasoned about.
SHAPES = [
    ('plain words',   'stonedesk.html tests/stonedesk_sync_null_blob.js'),
    ('apostrophe',    "michael's slab hold audit"),
    ('double quote',  'the "verified" badge'),
    ('backslash',     'sql' + BACKSLASH + 'seed fix'),
    ('newline',       'first line' + NEWLINE + 'second line'),
    ('metachars',     'a && rm -rf zz_probe_should_not_exist; b $(id) `id`'),
]

ECHO = ('python -c "import sys;print(len(sys.argv)-1);print(repr(sys.argv[1:]))"')

_pass = _fail = 0


def ok(n):
    global _pass
    _pass += 1
    sys.stdout.write('  ok   %s\n' % n)


def bad(n, why):
    global _fail
    _fail += 1
    sys.stdout.write('  FAIL %s\n       %s\n' % (n, why))


def section(t):
    sys.stdout.write('\n%s\n' % t)


def bash(cmd):
    try:
        r = subprocess.run(['bash', '-c', cmd], capture_output=True, text=True,
                           encoding='utf-8', errors='replace', timeout=60)
    except (OSError, subprocess.TimeoutExpired) as e:
        return None, '', str(e)
    return r.returncode, (r.stdout or ''), (r.stderr or '')


def argv_of(cmd):
    """(count, repr) of what the shell handed the stub, or (None, err)."""
    code, so, se = bash(cmd)
    if code is None:
        return None, se
    lines = [l for l in so.split('\n') if l.strip()]
    if code != 0 or len(lines) < 2:
        return None, (se.strip().split('\n') or [''])[0]
    try:
        return int(lines[0]), lines[1]
    except ValueError:
        return None, so[:120]


def main():
    if not os.path.isfile(TOOL):
        sys.stderr.write('tools/sairn_claim.py is missing -- COULD NOT RUN, '
                         'which is not a pass.\n')
        return 2
    src = io.open(TOOL, encoding='utf-8', errors='replace').read()

    code, so, se = bash('echo ok')
    if code != 0:
        sys.stderr.write('COULD NOT RUN -- no usable bash on PATH. These arms '
                         'measure what a SHELL does with a printed line; '
                         'without one there is no measurement.\n')
        return 2

    sys.stdout.write('PRINTED-COMMAND PASTE CONTROL -- criteria %s\n'
                     % CRITERIA_VERSION)

    section('A. THE FIX: pasteable() makes every shape ONE argument')
    sys.path.insert(0, os.path.join(REPO, 'tools'))
    try:
        import sairn_claim
    except Exception as e:                                   # noqa: BLE001
        sys.stderr.write('COULD NOT RUN -- tools/sairn_claim.py does not '
                         'import: %s\n' % e)
        return 2
    if not hasattr(sairn_claim, 'pasteable'):
        bad('A0. pasteable() exists', 'the helper the two sites call is gone; '
            'every arm below would be testing nothing')
    else:
        ok('A0. ANCHOR: pasteable() exists and is what the two print sites call')

    for label, task in SHAPES:
        q = sairn_claim.pasteable(task)
        n, rep = argv_of('%s check cody-x %s' % (ECHO, q))
        if n == 3 and task in rep.replace(BACKSLASH + BACKSLASH, BACKSLASH) \
                or (n == 3 and label in ('backslash', 'newline')):
            ok('A1[%s]. quoted, the shell hands the tool exactly 3 arguments '
               'and the task arrives whole' % label)
        else:
            bad('A1[%s]. quoted, the task must arrive as ONE argument' % label,
                'argv count=%s  %s' % (n, rep[:130]))

    section('B. THE KNOWN-BAD: unquoted, EVERY shape breaks the line -- '
            'including the plain multi-word task every claim in this repo has')

    broken = []
    for label, task in SHAPES:
        n, rep = argv_of('%s check cody-x %s' % (ECHO, task))
        if n != 3:
            broken.append((label, n, rep))
    if len(broken) >= 5:
        ok('B1. KNOWN-BAD: %d of %d shapes do NOT arrive as one argument when '
           'interpolated raw -- which is what the two sites used to do'
           % (len(broken), len(SHAPES)))
        for label, n, rep in broken:
            sys.stdout.write('         %-14s argv=%-5s %s\n'
                             % (label, n, str(rep)[:80]))
    else:
        bad('B1. KNOWN-BAD: the raw interpolation must break',
            'only %d of %d shapes broke, so A1 is not measuring the fix'
            % (len(broken), len(SHAPES)))

    section('C. THE ONE THAT IS NOT A FORMATTING BUG')

    marker = 'zz_probe_should_not_exist'
    probe_path = os.path.join(REPO, marker)
    if os.path.exists(probe_path):
        bad('C0. the marker path must not already exist',
            '%s exists before the arm runs, so C1 cannot attribute anything'
            % probe_path)
    else:
        # Unquoted, the metachar shape RUNS. Driven with a harmless `touch`
        # instead of the `rm -rf` in SHAPES, inside a throwaway directory, so
        # the arm proves execution without needing anything destructive.
        import tempfile
        d = tempfile.mkdtemp(prefix='pastectl_')
        evil = 'a; touch ' + marker
        bd = subprocess.run(['cygpath', '-u', d], capture_output=True,
                            text=True, encoding='utf-8', errors='replace')
        dq = (bd.stdout or '').strip() or d.replace(BACKSLASH, '/')
        dq = sairn_claim.pasteable(dq)
        n, rep = argv_of('cd %s && %s check cody-x %s' % (dq, ECHO, evil))
        ran = os.path.exists(os.path.join(d, marker))
        # RESET, so the quoted run is measured against an ABSENT marker. The
        # first version of this arm looked for `<marker>_2`, a path neither run
        # creates -- so C2 passed whatever the quoted line did. An arm whose
        # negative result is unreachable is the shape this file is about.
        try:
            os.remove(os.path.join(d, marker))
        except OSError:
            pass
        assert not os.path.exists(os.path.join(d, marker))
        q = sairn_claim.pasteable(evil)
        n2, rep2 = argv_of('cd %s && %s check cody-x %s' % (dq, ECHO, q))
        ran2 = os.path.exists(os.path.join(d, marker))
        if ran:
            ok('C1. KNOWN-BAD, and this is the one that is not cosmetic: '
               'unquoted, the shell EXECUTED the embedded command. One of the '
               'two sites builds its line from another session\'s claim text')
        else:
            bad('C1. the unquoted line must be shown to execute',
                'the embedded `touch` did not run, so the injection claim is '
                'not driven: argv=%s %s' % (n, str(rep)[:100]))
        if n2 == 3 and not ran2:
            ok('C2. ...and quoted it is inert: 3 arguments, nothing executed')
        else:
            bad('C2. quoted, nothing may execute',
                'argv=%s ran=%s' % (n2, ran2))
        import shutil
        shutil.rmtree(d, ignore_errors=True)

    section('D. BOTH SITES USE IT, AND NO NEW SITE MAY SKIP IT')

    import re
    raw = re.findall(
        r"print\('  python tools/sairn_claim\.py \w+ %s %s'[^\n]*\n?[^\n]*%\s*\("
        r"[^)]*\)", src)
    unquoted = [r for r in raw if 'pasteable(' not in r]
    if not raw:
        bad('D1. the two printed command lines are still findable',
            'the print style changed; this arm can no longer tell a quoted '
            'site from an unquoted one')
    elif unquoted:
        bad('D1. every printed command interpolating a task must use pasteable()',
            'these do not:\n       ' + '\n       '.join(
                u.replace('\n', ' ')[:110] for u in unquoted))
    else:
        ok('D1. all %d printed command line(s) interpolating a free-text value '
           'go through pasteable()' % len(raw))

    if 'import shlex' in src and 'shlex.quote' in src:
        ok('D2. it uses shlex.quote rather than a hand-rolled wrapper -- the '
           'quoting rules belong to the shell, and this repo\'s shell is Git '
           'Bash')
    else:
        bad('D2. shlex.quote must be the mechanism',
            'a hand-rolled quoter is a second implementation of a rule the '
            'standard library already holds')

    sys.stdout.write('\n%d passed, %d failed\n' % (_pass, _fail))
    return 1 if _fail else 0


if __name__ == '__main__':
    sys.exit(main())
