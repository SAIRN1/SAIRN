#!/usr/bin/env python
# OWNER: cody
"""Control for the OWNER-header gate on newly added tools/*.py files.

# REQUIREMENT: a push that ADDS a tools/*.py file with no `# OWNER: <session>`
#   header must be refused. An existing tool without one must NOT be refused --
#   282 of them have none, and a gate that blocks every push touching any tool
#   gets switched off. An owner naming a session that does not exist must be
#   refused too.

WHY. On 2026-09-30 a sweep found 22 tools that mutate the repo on a bare run, and
21 of them could not be routed to anybody. One git identity authors every commit
in this repo, and the claim record only knows a file if somebody happened to name
it in a claim string. The instruction was "register the rest by owner" and there
was no owner to register. A new file is the only moment the answer is free.

DRIVEN THROUGH THE REAL GATE, not just the checker. Arm C builds a throwaway
worktree, commits a tool with no header, and runs tools/sairn_push_gate_hook.py
--pre-push against it -- because a checker no gate invokes is a file, not a check,
and the wiring is the half most likely to be wrong.

Run:  python tests/run_tool_owner_header_probe.py
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECK = os.path.join(REPO, 'tools', 'tool_owner_header_check.py')
GATE_REL = os.path.join('tools', 'sairn_push_gate_hook.py')

CRITERIA_VERSION = '2026-09-30.1'

WITH_OWNER = '#!/usr/bin/env python\n# OWNER: cody\n"""A tool."""\nprint(1)\n'
NO_OWNER = '#!/usr/bin/env python\n"""A tool with nobody to ask."""\nprint(1)\n'
BAD_OWNER = '#!/usr/bin/env python\n# OWNER: nobody-in-particular\nprint(1)\n'
LOOSE = '#!/usr/bin/env python\n# owner = cody (probably)\nprint(1)\n'
LATE = '#!/usr/bin/env python\n' + ('# filler\n' * 60) + '# OWNER: cody\nprint(1)\n'

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


def run(*paths):
    r = subprocess.run([sys.executable, CHECK] + list(paths),
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace', timeout=180, cwd=REPO)
    return r.returncode, (r.stdout or '') + (r.stderr or '')


def git(cwd, *a):
    return subprocess.run(('git',) + a, cwd=cwd, capture_output=True, text=True,
                          encoding='utf-8', errors='replace')


def main():
    if not os.path.isfile(CHECK):
        sys.stderr.write('COULD NOT RUN -- tools/tool_owner_header_check.py is '
                         'missing.\n')
        return 2
    sys.stdout.write('TOOL OWNER HEADER CONTROL -- criteria %s\n'
                     % CRITERIA_VERSION)

    d = tempfile.mkdtemp(prefix='ownerhdr_')
    wt = None
    try:
        section('A. THE KNOWN-BAD: a new tool with nobody to ask')

        def mk(name, body):
            p = os.path.join(d, name)
            io.open(p, 'w', encoding='utf-8', newline='\n').write(body)
            return p

        code, o = run(mk('no_owner.py', NO_OWNER))
        if code == 1 and 'NO OWNER' in o:
            ok('A1. KNOWN-BAD: a file with no `# OWNER:` line is refused, exit 1')
        else:
            bad('A1. a missing owner must be refused', 'exit=%s\n%s' % (code, o[-500:]))

        code, o = run(mk('bad_owner.py', BAD_OWNER))
        if code == 1 and 'NOT A KNOWN SESSION' in o:
            ok('A2. KNOWN-BAD: an owner naming a session that does not exist is '
               'refused. An owner nobody can be asked is not an owner')
        else:
            bad('A2. an unknown session must be refused',
                'exit=%s\n%s' % (code, o[-400:]))

        code, o = run(mk('loose.py', LOOSE))
        if code == 1:
            ok('A3. KNOWN-BAD: `# owner = cody (probably)` is refused -- the form '
               'is `# OWNER: <session>` on its own line, or the field cannot be '
               'read by anything')
        else:
            bad('A3. a malformed owner line must be refused', 'exit=%s' % code)

        code, o = run(mk('late.py', LATE))
        if code == 1:
            ok('A4. KNOWN-BAD: an OWNER line below the header window is refused. '
               'It belongs where a reader meets the file, not buried at line 61')
        else:
            bad('A4. a late OWNER line must be refused', 'exit=%s' % code)

        section('B. THE SILENT HALF')

        code, o = run(mk('good.py', WITH_OWNER))
        if code == 0 and 'OWNER: cody' in o:
            ok('B1. a file carrying `# OWNER: cody` passes, exit 0. Without this '
               'the gate could be "refuse everything" and A1 would still pass')
        else:
            bad('B1. a declared owner must pass', 'exit=%s\n%s' % (code, o[-400:]))

        code, o = run()
        if code == 2:
            ok('B2. no files given is exit 2 COULD NOT RUN -- called from a gate '
               'where exit 0 means allow, an empty run must not read as clean')
        else:
            bad('B2. an empty run must exit 2', 'exit=%s' % code)

        code, o = run(os.path.join(d, 'not_there.py'))
        if code == 2 and 'COULD NOT CHECK' in o:
            bad_file_ok = True
            ok('B3. a file that is not there is COULD NOT CHECK, not a pass')
        else:
            bad('B3. a missing file must exit 2', 'exit=%s' % code)

        code, o = run(mk('good2.py', WITH_OWNER))
        if 'GRANDFATHERED' in o and 'NOT' in o:
            ok('B4. the run PRINTS the grandfathered backlog -- the 282 existing '
               'tools with no header -- so it cannot quietly become the normal '
               'state, and states that it is not refusing them')
        else:
            bad('B4. the backlog must be printed', o[-300:])

        section('C. THE GATE ACTUALLY REFUSES, driven end to end')

        wt = os.path.join(tempfile.gettempdir(), 'ownergate-%d' % os.getpid())
        if os.path.isdir(wt):
            git(REPO, 'worktree', 'remove', '--force', wt)
        r = git(REPO, 'worktree', 'add', '-q', '--detach', wt, 'HEAD')
        if r.returncode != 0 or not os.path.isdir(wt):
            bad('C. COULD NOT RUN: no worktree',
                'the end-to-end arm is the half most likely to be wrong and it '
                'did not run: %s' % ((r.stderr or r.stdout)[:200]))
        else:
            # THE WORKING-TREE GATE, COPIED IN. `git worktree add --detach HEAD`
            # gives the COMMITTED tree, so the gate it would run is the one at
            # HEAD -- which is exactly what happened the first time this arm ran:
            # it reported "the gate refused for a DIFFERENT reason" because
            # HEAD's gate has no owner check at all and the tool-inventory check
            # objected first. The arm was right to fail; it was testing the wrong
            # file. Copying both in makes it test the code in front of you.
            for _rel in (GATE_REL, os.path.join('tools',
                                                'tool_owner_header_check.py')):
                shutil.copy2(os.path.join(REPO, _rel), os.path.join(wt, _rel))
            base = git(wt, 'rev-parse', 'HEAD').stdout.strip()
            io.open(os.path.join(wt, 'tools', 'zz_probe_no_owner.py'), 'w',
                    encoding='utf-8', newline='\n').write(NO_OWNER)
            git(wt, 'add', '--', 'tools/zz_probe_no_owner.py')
            git(wt, '-c', 'user.name=probe', '-c', 'user.email=p@local',
                'commit', '-qm', 'adds a tool with no owner')
            tip = git(wt, 'rev-parse', 'HEAD').stdout.strip()
            env = dict(os.environ)
            env['SAIRN_PUSH_GATE_MODE'] = 'prepush'
            g = subprocess.run([sys.executable, GATE_REL, '--pre-push'], cwd=wt,
                               input='refs/heads/main %s refs/heads/main %s\n'
                                     % (tip, base),
                               capture_output=True, text=True, encoding='utf-8',
                               errors='replace', timeout=600)
            go = (g.stdout or '') + (g.stderr or '')
            if g.returncode != 0 and 'does not say who' in go:
                ok('C1. THE END-TO-END ARM: the real --pre-push gate REFUSES a '
                   'push that adds tools/zz_probe_no_owner.py, and says why')
            elif g.returncode != 0:
                bad('C1. the gate refused for a DIFFERENT reason',
                    'this arm cannot tell a working owner check from an unrelated '
                    'deny, so it is a failure:\n       '
                    + (go.strip().split(chr(10))[0] if go.strip() else '(silent)'))
            else:
                bad('C1. the gate must refuse a new tool with no owner',
                    'it allowed the push (exit 0)')

            # THE SILENT HALF OF THE WIRING: add the header, same commit shape,
            # and the owner check must stop objecting.
            io.open(os.path.join(wt, 'tools', 'zz_probe_no_owner.py'), 'w',
                    encoding='utf-8', newline='\n').write(WITH_OWNER)
            git(wt, 'add', '--', 'tools/zz_probe_no_owner.py')
            git(wt, '-c', 'user.name=probe', '-c', 'user.email=p@local',
                'commit', '-qm', 'gives it an owner')
            tip2 = git(wt, 'rev-parse', 'HEAD').stdout.strip()
            g2 = subprocess.run([sys.executable, GATE_REL, '--pre-push'], cwd=wt,
                                input='refs/heads/main %s refs/heads/main %s\n'
                                      % (tip2, base),
                                capture_output=True, text=True, encoding='utf-8',
                                errors='replace', timeout=600)
            go2 = (g2.stdout or '') + (g2.stderr or '')
            if 'does not say who' not in go2:
                ok('C2. ...and with the header added, the owner check no longer '
                   'objects. Other checks may still refuse this synthetic push '
                   'and that is not this arm\'s business -- it asserts only that '
                   'THIS refusal is gone')
            else:
                bad('C2. the header must clear the owner refusal',
                    'still refusing with the owner message')

        section('D. THE ANCHORS')

        gate = io.open(os.path.join(REPO, GATE_REL), encoding='utf-8').read()
        for needle, why in (
            ('tool_owner_header_check.py', 'the gate must invoke the checker'),
            ('--diff-filter=A', 'ADDED files only -- the grandfathering'),
            ('not os.path.isfile(_oh)', 'the fail-closed branch, PR 1.11'),
        ):
            if needle in gate:
                ok('D. ANCHOR present: %s -- %s' % (needle, why))
            else:
                bad('D. ANCHOR MISSING: %s' % needle, why)

        src = io.open(CHECK, encoding='utf-8').read()
        if 'def known_sessions' in src and '.claude' in src:
            ok('D. the session list is DERIVED from .claude/claims/ rather than '
               'hardcoded -- a sixth agent appears as a claim file, and a list '
               'here would be wrong for as long as CLAUDE.md\'s clone registry was')
        else:
            bad('D. the session list must be derived', 'known_sessions() is gone')
    finally:
        if wt:
            git(REPO, 'worktree', 'remove', '--force', wt)
            shutil.rmtree(wt, ignore_errors=True)
        shutil.rmtree(d, ignore_errors=True)

    sys.stdout.write('\n%d passed, %d failed\n' % (_pass, _fail))
    return 1 if _fail else 0


if __name__ == '__main__':
    sys.exit(main())
