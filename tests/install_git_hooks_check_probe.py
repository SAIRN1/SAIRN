"""`install_git_hooks.py --check` must answer about GIT, not about the file.

Run: python tests/install_git_hooks_check_probe.py

.githooks/pre-push IS THE ONLY THING THAT GATES A PUSH MADE BY SUBPROCESS. The
Claude Code PreToolUse hook keys on Bash command text and tools/sairn_claim.py
pushes from Python, so the hook is the whole protection for that path. .git/ is
not versioned, so it is opt-in per clone.

--check HAS BEEN WIDENED TWICE, AND THIS PROBE EXISTS BECAUSE OF THE FIRST TIME.
It originally compared core.hooksPath and stopped, so on 2026-09-01 -- when all
four clones held a CRLF copy that git was skipping silently, and two of them had
core.hooksPath set -- it would have printed OK on a hook that had NEVER ONCE
EXECUTED. The byte check and the wrapper execution were added then.

EVERY ONE OF THOSE IS STILL A STATEMENT ABOUT THE FILE. hooksPath can be right,
the bytes can be LF, and `sh <file>` can exit 0, while git still does not run it
-- a wrong file name, a permission bit, an interpreter git resolves differently
from the shell the checker happens to be running under. `sh <file>` never
consults the shebang at all, which runs_cleanly() says about itself.

So --check now FIRES THE HOOK THROUGH GIT: a throwaway repo, core.hooksPath
pointed at this clone's .githooks, and a dry-run push to a throwaway bare repo.
The hook resolves ROOT from the scratch repo and cannot find the tools there, so
it exits 1 and git refuses -- push refused means it fired, push succeeded means
git never ran it.

THE ARM THAT MATTERS IS 3. It builds the state every earlier version of --check
was blind to: hooksPath set to a directory named `.githooks` that contains NO
pre-push. The tracked file is still present, still LF, still executable on its
own -- so the path check passes, the byte check passes, and the wrapper runs.
Only firing it through git can tell.

Nothing here touches this clone: every case runs in a throwaway clone with its
own config, and the only pushes are dry-runs to bare repos in temp directories.
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile

REPO = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True, encoding='utf-8',
                      errors='replace').stdout.strip()
TOOL = 'tools/install_git_hooks.py'

FAILURES = []
TEMPS = []


def arm(name, ok, detail=''):
    print(('  ok   ' if ok else '  FAIL ') + name)
    if not ok:
        print('         ' + str(detail)[:400])
        FAILURES.append(name)
    return bool(ok)


# ── THE THIRD STATE, ADDED 2026-09-23 ────────────────────────────────────────
# Arm 4 sabotages the installed hook with `b.replace(b'\n', b'\r\n')` and then
# requires --check to refuse it as CRLF. NOTHING CHECKED THAT THE SABOTAGE
# APPLIED, and this is the one arm where a no-op is invisible rather than loud:
# if the installed hook ever arrives ALREADY CRLF, or with no newline in it at
# all, the replace changes nothing -- and --check still refuses, still says
# CRLF, and arm 4 still passes. It would be reporting that the byte check
# survives a mutation that was never made.
#
# That is the same shape as the defect this whole probe exists for: an answer
# about the wrong thing, wearing a green tick. So a mutation that did not land
# is a COULD-NOT-RUN and exits 3 -- never folded into the pass, and not folded
# into FAILURES either, because nothing about the tool under test is broken.
CANNOT = []


def cannot(why):
    print('  CANNOT ' + why)
    CANNOT.append(why)


def clone():
    tmp = tempfile.mkdtemp(prefix='sairn-hookchk-')
    TEMPS.append(tmp)
    dst = os.path.join(tmp, 'clone')
    r = subprocess.run(['git', 'clone', '-q', '--depth', '1', '--no-hardlinks',
                        REPO, dst], capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    if r.returncode != 0:
        print('COULD NOT RUN: clone failed: ' + (r.stderr or '')[:200])
        sys.exit(3)
    for a in (['config', 'user.email', 'probe@example.invalid'],
              ['config', 'user.name', 'probe']):
        subprocess.run(['git', '-C', dst] + a, capture_output=True)
    # ── THE WORKING COPY IS STAGED IN, AND THE FIRST RUN OF THIS PROBE PROVED
    # ── WHY (2026-09-16) ──────────────────────────────────────────────────────
    # A clone is at COMMITTED HEAD, so without this the probe tests the tool as
    # it was PUSHED while its author is editing the working copy. The first run
    # reported two failures whose real cause was that the clone held the OLD
    # --check -- it printed the old success line, which the arms correctly did
    # not recognise.
    #
    # That is the defect recorded as f4397982 in the defect register, which this
    # same session had back-filled contributing factors for an hour earlier.
    # Reproduced by hand, immediately, which is the argument for the harness
    # carrying it rather than each probe remembering.
    shutil.copy(os.path.join(REPO, TOOL), os.path.join(dst, TOOL))
    return dst


def check(dst):
    r = subprocess.run([sys.executable, os.path.join(dst, TOOL), '--check'],
                       cwd=dst, capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    return r.returncode, (r.stdout or '') + (r.stderr or '')


def main():
    try:
        print('install_git_hooks --check -- it must answer about GIT, not the file\n')

        # 1. INSTALLED PROPERLY -> 0, and it says git fires it.
        d = clone()
        subprocess.run([sys.executable, os.path.join(d, TOOL)], cwd=d,
                       capture_output=True)
        rc, out = check(d)
        arm('a properly installed clone passes, and SAYS git fires the hook',
            rc == 0 and 'GIT ITSELF FIRES IT' in out, 'exit %d\n%s' % (rc, out[-400:]))

        # 2. NOT INSTALLED AT ALL -> 1.
        d = clone()
        rc, out = check(d)
        arm('a clone with no core.hooksPath is refused', rc == 1,
            'exit %d\n%s' % (rc, out[-300:]))
        arm('...and it names core.hooksPath as the reason',
            'core.hooksPath' in out, out[-300:])

        # 3. THE ARM THAT MATTERS. Every file-level check passes and git still
        #    does not run the hook.
        d = clone()
        subprocess.run([sys.executable, os.path.join(d, TOOL)], cwd=d,
                       capture_output=True)
        decoy = os.path.join(d, 'decoy', '.githooks')
        os.makedirs(decoy)
        io.open(os.path.join(decoy, 'README'), 'w').write('no pre-push here\n')
        subprocess.run(['git', '-C', d, 'config', 'core.hooksPath',
                        decoy.replace('\\', '/')], capture_output=True)
        rc, out = check(d)
        tracked = os.path.join(d, '.githooks', 'pre-push')
        arm('the tracked hook is still present and LF, so every FILE-level '
            'check still passes',
            os.path.isfile(tracked) and b'\r\n' not in io.open(tracked, 'rb').read(),
            tracked)
        arm('...and hooksPath still ENDS IN .githooks, so the path check passes too',
            'core.hooksPath is' not in out, out[-300:])
        arm('BUT GIT DOES NOT RUN IT, and --check refuses -- the state every '
            'earlier version of this flag was blind to',
            rc == 1 and 'did NOT run' in out, 'exit %d\n%s' % (rc, out[-400:]))

        # 4. CRLF -> refused, and for the right reason. The byte check owns
        #    this one; keeping it here proves the new arm did not replace it.
        d = clone()
        subprocess.run([sys.executable, os.path.join(d, TOOL)], cwd=d,
                       capture_output=True)
        hp = os.path.join(d, '.githooks', 'pre-push')
        b = io.open(hp, 'rb').read()
        lf = b'\n'
        if lf not in b:
            cannot('the installed hook carries no LF at all, so the CRLF '
                   'mutation below is a NO-OP and arm 4 would pass without '
                   'having exercised the byte check. Could-not-run, not a pass.')
        crlf = b.replace(lf, b'\r\n')
        if crlf == b:
            cannot('the CRLF mutation changed nothing -- the installed hook is '
                   'already CRLF, so --check refusing it proves nothing about '
                   'this arm. Could-not-run, not a pass.')
        io.open(hp, 'wb').write(crlf)
        rc, out = check(d)
        arm('a CRLF hook is still refused, and still named as CRLF -- the byte '
            'check was not replaced by the fire test',
            rc == 1 and 'CRLF' in out, 'exit %d\n%s' % (rc, out[-400:]))

        # 5. CONTROL: --check REPAIRS NOTHING. A report-only checker that
        #    rewrote a tracked file would be worse than a weak one.
        after = io.open(hp, 'rb').read()
        arm('CONTROL: --check did not repair the CRLF it complained about',
            b'\r\n' in after, 'the checker rewrote a tracked file')

        # 6. CONTROL: it did not touch THIS clone's config.
        rc2, cur, _ = (lambda r: (r.returncode, r.stdout.strip(), r.stderr))(
            subprocess.run(['git', '-C', REPO, 'config', '--get', 'core.hooksPath'],
                           capture_output=True, text=True, encoding='utf-8'))
        arm('CONTROL: this clone still points at .githooks -- the probe changed '
            'nothing here', rc2 == 0 and cur.endswith('.githooks'), cur)
    finally:
        for t in TEMPS:
            shutil.rmtree(t, ignore_errors=True)

    print('')
    if CANNOT:
        print('%d ARM(S) COULD NOT BE DRIVEN -- see CANNOT above. Exit 3: not a '
              'pass, and not a failure of the tool under test.' % len(CANNOT))
        return 3
    if FAILURES:
        print('%d ARM(S) FAILED' % len(FAILURES))
        return 1
    print('ALL ARMS PASS -- --check answers about git, and still answers about '
          'the file.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
