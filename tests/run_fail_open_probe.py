#!/usr/bin/env python3
"""tests/run_fail_open_probe.py -- take each hook's dependency away and watch it
REFUSE, not pass.

Run:  python tests/run_fail_open_probe.py

── WHY A CONTROL PER FIX AND NOT ONE FOR THE SET ─────────────────────────
The three hooks were fixed three DIFFERENT ways, because `|| exit 0` meant a
different thing in each:

  prepare-commit-msg  a missing checker must REFUSE the commit (exit non-zero).
  pre-commit          a missing CHECKER must refuse; a missing SCOPE MARKER must
                      still exit 0, because the gate genuinely does not apply in
                      a build clone. One arm each, in both directions.
  post-rewrite        must NOT fail the rebase -- git ignores its status and it
                      runs after the fact -- but must SAY SO LOUDLY. The arm
                      asserts exit 0 AND a message on stderr, which is the only
                      arm here where a zero exit is the correct answer.

A single "hooks fail closed" assertion would have been wrong for two of the
three, and demanding a refusal from pre-commit's scope test would have broken
every commit in four clones.

── REAL HOOK FILES, RUN AS SHELL ─────────────────────────────────────────
Each hook is copied into a sandbox with a real git repository and executed by
`sh`, because the defect lived in shell control flow -- `||`, `exec`, and what
exit 0 means to git. Reading the file would have proved nothing about any of
those.
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOKS = os.path.join(REPO, '.githooks')

FAILURES = []
N = [0]


def expect(name, got, want):
    N[0] += 1
    if got != want:
        FAILURES.append('%s -- wanted %r, got %r' % (name, want, got))
        print('  FAIL %s' % name)
    else:
        print('  ok   %s' % name)


def sh_available():
    return shutil.which('sh') is not None


def sandbox(hook, with_tools=(), marker=False):
    """A real repo with the hook installed and only the named tools present."""
    root = tempfile.mkdtemp(prefix='failopen-')
    subprocess.run(['git', 'init', '-q', '-b', 'main'], cwd=root,
                   capture_output=True)
    subprocess.run(['git', 'config', 'user.email', 'p@e.invalid'], cwd=root,
                   capture_output=True)
    subprocess.run(['git', 'config', 'user.name', 'probe'], cwd=root,
                   capture_output=True)
    os.makedirs(os.path.join(root, 'tools'), exist_ok=True)
    os.makedirs(os.path.join(root, '.githooks'), exist_ok=True)
    shutil.copy(os.path.join(HOOKS, hook), os.path.join(root, '.githooks', hook))
    for t in with_tools:
        # A stub that succeeds. The question is whether the HOOK reaches it.
        io.open(os.path.join(root, 'tools', t), 'w', encoding='utf-8',
                newline='\n').write('import sys\nsys.exit(0)\n')
    if marker:
        gd = subprocess.run(['git', 'rev-parse', '--git-dir'], cwd=root,
                            capture_output=True).stdout.decode().strip()
        io.open(os.path.join(root, gd, 'sairn-hover-auditor-clone'), 'w').write('x')
    return root


def stage(root, rel, body):
    """Write a file in the sandbox and `git add` it, so the hook's
    `git diff --cached` actually sees something."""
    full = os.path.join(root, rel.replace('/', os.sep))
    os.makedirs(os.path.dirname(full), exist_ok=True)
    io.open(full, 'w', encoding='utf-8', newline=chr(10)).write(body)
    subprocess.run(['git', 'add', rel], cwd=root, capture_output=True)


def run_hook(root, hook):
    r = subprocess.run(['sh', os.path.join(root, '.githooks', hook)],
                       cwd=root, capture_output=True, timeout=120)
    return r.returncode, (r.stdout + r.stderr).decode('utf-8', 'replace')


def main():
    if not sh_available():
        sys.stderr.write('COULD NOT RUN -- no `sh` on PATH, so no hook was '
                         'executed. This is NOT a pass.\n')
        return 2
    print('FAIL-OPEN PROBE -- remove the dependency, the hook must not pass')

    # ── prepare-commit-msg ───────────────────────────────────────────────
    print('')
    print('1. prepare-commit-msg: a MISSING CHECKER must refuse the commit')
    for missing, present in (
            ('staged_credential_check.py', ['staged_conflict_marker_check.py']),
            ('staged_conflict_marker_check.py', ['staged_credential_check.py'])):
        root = sandbox('prepare-commit-msg', with_tools=present)
        try:
            rc, out = run_hook(root, 'prepare-commit-msg')
            expect('  without %-34s -> refuses' % missing, rc != 0, True)
            expect('    ... and NAMES the missing file', missing in out, True)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    root = sandbox('prepare-commit-msg',
                   with_tools=['staged_conflict_marker_check.py',
                               'staged_credential_check.py'])
    try:
        rc, _ = run_hook(root, 'prepare-commit-msg')
        expect('  THE CONTROL: with both present it allows the commit', rc, 0)
    finally:
        shutil.rmtree(root, ignore_errors=True)

    # ── pre-commit, both directions ──────────────────────────────────────
    print('')
    print('2. pre-commit: SCOPE absent must PASS, DEPENDENCY absent must REFUSE')
    root = sandbox('pre-commit', with_tools=[], marker=False)
    try:
        rc, _ = run_hook(root, 'pre-commit')
        expect('  no auditor marker (a build clone) -> exit 0, gate not applicable',
               rc, 0)
    finally:
        shutil.rmtree(root, ignore_errors=True)

    root = sandbox('pre-commit', with_tools=[], marker=True)
    try:
        rc, out = run_hook(root, 'pre-commit')
        expect('  marker PRESENT but the gate tool missing -> refuses', rc != 0, True)
        expect('    ... and names hover_auditor_scope_gate.py',
               'hover_auditor_scope_gate.py' in out, True)
    finally:
        shutil.rmtree(root, ignore_errors=True)

    root = sandbox('pre-commit', with_tools=['hover_auditor_scope_gate.py'],
                   marker=True)
    try:
        rc, _ = run_hook(root, 'pre-commit')
        expect('  THE CONTROL: marker AND tool present -> runs and allows', rc, 0)
    finally:
        shutil.rmtree(root, ignore_errors=True)

    # ── pre-commit, the LIVE-PROBE OBLIGATION block (2026-09-29) ─────────
    # Four directions, and the first two are the ones that keep it usable: a
    # block that fires on every commit is a block somebody turns off. The host
    # string is assembled at runtime -- a literal here would make this fixture a
    # finding in the audit's own scan of tests/.
    print('')
    print('2b. pre-commit: the live-probe obligations, scoped to the commit')
    HOST = 'sairn' + '.vercel.' + 'app'
    NL = chr(10)
    PROBE_SRC = (('import json' + NL +
                  'ENDPOINT = "https://%s/api/sd-data"' + NL +
                  'def go():' + NL +
                  '    return json.dumps({"action": "write"})' + NL) % HOST)
    ORDINARY_SRC = 'def f():' + NL + '    return 1' + NL

    root = sandbox('pre-commit', with_tools=[], marker=False)
    try:
        rc, out = run_hook(root, 'pre-commit')
        expect('  NOTHING staged -> exit 0, the block never runs', rc, 0)
    finally:
        shutil.rmtree(root, ignore_errors=True)

    root = sandbox('pre-commit', with_tools=[], marker=False)
    try:
        stage(root, 'tools/zz_ordinary.py', ORDINARY_SRC)
        rc, out = run_hook(root, 'pre-commit')
        expect('  a staged tools/ file that does NOT address the platform -> '
               'exit 0', rc, 0)
    finally:
        shutil.rmtree(root, ignore_errors=True)

    root = sandbox('pre-commit', with_tools=[], marker=False)
    try:
        stage(root, 'tools/zz_live_probe.py', PROBE_SRC)
        rc, out = run_hook(root, 'pre-commit')
        expect('  a staged file that DOES address it, audit tool ABSENT -> '
               'refuses', rc != 0, True)
        expect('    ... and names live_probe_residue_audit.py',
               'live_probe_residue_audit.py' in out, True)
    finally:
        shutil.rmtree(root, ignore_errors=True)

    root = sandbox('pre-commit', with_tools=['live_probe_residue_audit.py'],
                   marker=False)
    try:
        stage(root, 'tools/zz_live_probe.py', PROBE_SRC)
        rc, out = run_hook(root, 'pre-commit')
        expect('  THE CONTROL: audit tool present and CLEAN -> runs and allows',
               rc, 0)
    finally:
        shutil.rmtree(root, ignore_errors=True)

    root = sandbox('pre-commit', with_tools=[], marker=False)
    try:
        # A stub that FINDS something. Without this arm the block could reach
        # the audit, ignore its verdict, and every arm above would still pass.
        io.open(os.path.join(root, 'tools', 'live_probe_residue_audit.py'), 'w',
                encoding='utf-8', newline=NL).write('import sys' + NL + 'sys.exit(1)' + NL)
        stage(root, 'tools/zz_live_probe.py', PROBE_SRC)
        rc, out = run_hook(root, 'pre-commit')
        expect('  audit present and REPORTING A FINDING -> the hook refuses',
               rc != 0, True)
    finally:
        shutil.rmtree(root, ignore_errors=True)

    root = sandbox('pre-commit', with_tools=[], marker=False)
    try:
        # COULD NOT RUN is exit 2 from the audit and must also stop the commit
        # -- PR 1.11, the two are printed differently and folded into neither.
        io.open(os.path.join(root, 'tools', 'live_probe_residue_audit.py'), 'w',
                encoding='utf-8', newline=NL).write('import sys' + NL + 'sys.exit(2)' + NL)
        stage(root, 'tools/zz_live_probe.py', PROBE_SRC)
        rc, out = run_hook(root, 'pre-commit')
        expect('  audit exiting 2 COULD NOT RUN -> the hook also refuses',
               rc != 0, True)
    finally:
        shutil.rmtree(root, ignore_errors=True)

    # ── post-rewrite: the one where exit 0 is correct ────────────────────
    print('')
    print('3. post-rewrite: must NOT fail the rebase, but must SAY SO')
    root = sandbox('post-rewrite', with_tools=[])
    try:
        rc, out = run_hook(root, 'post-rewrite')
        expect('  missing register tool -> still exit 0 (git ignores it anyway)',
               rc, 0)
        expect('    ... but WARNS on stderr, which is the control here',
               'NOT be' in out or 'NOT re-seated' in out or 'MISSING' in out, True)
        expect('    ... and names the recovery command',
               '--reseat' in out or 'defect_register.py' in out, True)
    finally:
        shutil.rmtree(root, ignore_errors=True)

    # ── 4. THE SCANNER ITSELF, AGAINST A DECOY ──────────────────────────
    # Sections 1-3 drive the HOOKS. Nothing drove the SCANNER's counting, and
    # that is how it came to count its own docstring six times and publish two
    # wrong figures (21, then 16; the real number is 30). A count is the easiest
    # output to believe and the hardest to falsify by reading.
    #
    # EVERY FIXTURE HERE IS ASSEMBLED AT RUNTIME. Writing a literal
    # `except: pass` into this file would make the probe a finding in the very
    # scan it is testing -- the same self-match, one level out.
    print('')
    print('4. THE SCANNER, fed a known-bad decoy and its prose twin')
    import tempfile as _tf
    import shutil as _sh
    sys.path.insert(0, os.path.join(REPO, 'tools'))
    import fail_open_scan as S

    _EXC = 'except'
    _PASS = 'pass'
    REAL = (
        'import os\n'
        'def load(p):\n'
        '    try:\n'
        '        return open(p).read()\n'
        '    %s Exception:\n'
        '        %s\n' % (_EXC, _PASS))
    PROSE = (
        '"""A checker.\n'
        '\n'
        'It looks for `%s: %s` and for `|| exit 0`, which are the shapes that\n'
        'make a gate report success when it could not run.\n'
        '"""\n'
        'import os\n'
        'def load(p):\n'
        '    return open(p).read()\n' % (_EXC, _PASS))

    d = _tf.mkdtemp(prefix='failopen-decoy-')
    saved_repo, saved_dirs = S.REPO, S.SCAN_DIRS
    try:
        os.makedirs(os.path.join(d, 'tools'))
        io.open(os.path.join(d, 'tools', 'real_defect.py'), 'w',
                encoding='utf-8', newline='\n').write(REAL)
        io.open(os.path.join(d, 'tools', 'prose_only.py'), 'w',
                encoding='utf-8', newline='\n').write(PROSE)
        S.REPO, S.SCAN_DIRS = d, ('tools',)
        res = S.scan()
        real = res.get('tools/real_defect.py', [])
        prose = res.get('tools/prose_only.py', [])
        expect('  a REAL bare-except-pass in executable code is CAUGHT',
               [h['shape'] for h in real], ['bare-except-pass'])
        expect('  the SAME text inside a docstring is NOT counted',
               prose, [])

        # A file that will not tokenise must be COULD NOT TELL, never scanned
        # raw -- a raw fallback would reinstate the self-match it just fixed.
        io.open(os.path.join(d, 'tools', 'broken.py'), 'w',
                encoding='utf-8', newline='\n').write('def f(:\n    ' + _PASS + '\n')
        raised = False
        try:
            S.scan()
        except S.CouldNotTell:
            raised = True
        expect('  an untokenisable file is COULD NOT TELL, not scanned raw',
               raised, True)
    finally:
        S.REPO, S.SCAN_DIRS = saved_repo, saved_dirs
        _sh.rmtree(d, ignore_errors=True)

    print('')
    if FAILURES:
        print('%d of %d FAILED:' % (len(FAILURES), N[0]))
        for f in FAILURES:
            print('  - %s' % f)
        return 1
    print('%d/%d passed.' % (N[0], N[0]))
    print('')
    print('WHAT THIS DOES NOT PROVE: that the checkers these hooks call are')
    print('correct. Every tool here is a stub that exits 0 -- the question asked')
    print('is only whether the HOOK reaches it or silently decides it does not')
    print('have to. Each checker has its own control.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
