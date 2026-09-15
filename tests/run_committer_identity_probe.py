"""tests/run_committer_identity_probe.py

Run:  python tests/run_committer_identity_probe.py

CONTROLS_FOR = tools/committer_identity_check.py

── WHY THE SUBJECT EXISTS ────────────────────────────────────────────────────
131 commits reached origin/main authored and committed as `probe <probe@local>`
between 2026-09-10 and 2026-09-13, including an app's entire per-employee auth
endpoint. One clone had the probes' throwaway identity written into its LOCAL
git config instead of passed per-invocation. Nothing on the platform reads the
committing identity, so nothing said anything for three days.

── WHY A THROWAWAY CLONE AND NOT A WORKTREE ──────────────────────────────────
`user.name`/`user.email` are REPOSITORY config and `git worktree` shares
`.git/config` with the clone that made it. Breaking the identity in a worktree
would mis-attribute this clone's own commits for as long as the probe ran --
which is the defect, performed. Every arm runs in a separate `git clone`, and
the last section asserts this clone's identity is exactly as it was.

── THE TOOL IS COPIED IN, DELIBERATELY ───────────────────────────────────────
It resolves its subject from its own `__file__`, so it must live inside the
clone under test. `git clone` carries committed HEAD, which is the tool as it
stood BEFORE any uncommitted change -- the githook probe was written that way by
mistake and reported four false failures. Copying this clone's file in means the
arms exercise the tool as it actually is.
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile

CONTROLS_FOR = ['committer_identity_check.py']

REPO = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True, encoding='utf-8', errors='replace').stdout.strip()
REL = 'tools/committer_identity_check.py'
FAIL = []


def ok(name, cond, detail=''):
    print('  %s %s%s' % ('PASS ' if cond else 'FAIL ', name,
                         '' if cond else '\n        ' + str(detail)[:400]))
    if not cond:
        FAIL.append(name)


def git(cwd, *args):
    return subprocess.run(['git', '-C', cwd] + list(args), capture_output=True, text=True, encoding='utf-8', errors='replace')


def run(cwd, *args):
    r = subprocess.run([sys.executable, os.path.join(cwd, REL.replace('/', os.sep))]
                       + list(args), capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=cwd,
                       env=dict(os.environ, PYTHONIOENCODING='utf-8'))
    return r.returncode, (r.stdout or '') + (r.stderr or '')


def rmtree(path):
    def onerror(fn, p, _exc):
        try:
            os.chmod(p, 0o700)
            fn(p)
        except Exception:
            pass
    shutil.rmtree(path, onerror=onerror)


# THE CONTROL IDENTITY IS ASSEMBLED AT RUN TIME, AND THAT IS NOT A FLOURISH.
# The checker derives its throwaway list by scanning tests/ for
# `'user.email', '<value>'` pairs. The moment THIS file was committed, a fresh
# clone carried it -- and the control arms' own clean identity, written as a
# literal pair right here, became a 'throwaway identity' the checker refused.
# Two arms that assert an ordinary identity PASSES went red within a minute of
# the commit landing. The probe had poisoned the list it was testing.
#
# Splitting the value so no source line contains the pair keeps the control
# honest without weakening the checker: a real probe writing a real throwaway
# identity still gets caught, because a real probe writes it as a literal.
CLEAN_NAME = 'A' + ' Person'
CLEAN_EMAIL = 'a.person' + '@' + 'example.com'
# THE TWO FIXTURE VALUES ARE ASSEMBLED FOR A DIFFERENT REASON, and it is the
# one that let a mutation survive twice. To make the checker see a value this
# probe has to SET it with `git config user.email <value>` -- and that line,
# in this file, is itself an ARGUMENT-form pair the checker scans. So the
# `-c` arm was passing on the checker finding the value HERE rather than in
# the fixture, and deleting the `-c` branch changed nothing. Assembling the
# value means its only literal appearance is inside the generated fixture, in
# the spelling under test.
ARG_FIXTURE = 'brand.new' + '.fixture@invalid'
DASHC_FIXTURE = 'dash.c' + '.fixture@invalid'

print('\nA. this clone answers, and answering is read-only')
before = (git(REPO, 'config', '--get', 'user.name').stdout.strip(),
          git(REPO, 'config', '--get', 'user.email').stdout.strip())
rc, out = run(REPO)
ok('this clone is CLEAN', rc == 0, 'exit=%d\n%s' % (rc, out[-300:]))
ok('...and it names the identity it will commit as',
   before[1] in out, out[-300:])
ok('...and it reports the already-affected history without failing on it',
   'history, NOT rewritten' in out, out[-300:])

TMP = tempfile.mkdtemp(prefix='identity-probe-')
CLONE = os.path.join(TMP, 'clone')
try:
    c = subprocess.run(['git', 'clone', '--local', '--quiet', REPO, CLONE],
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    ok('a throwaway clone was made', os.path.isdir(os.path.join(CLONE, 'tools')),
       c.stderr[-300:])
    shutil.copy2(os.path.join(REPO, REL.replace('/', os.sep)),
                 os.path.join(CLONE, REL.replace('/', os.sep)))
    # AND THIS FILE TOO, for the same reason and one more. The checker DERIVES
    # its list by scanning tests/, and a fresh clone carries the COMMITTED copy
    # of this probe -- so without this the arms below are measured against the
    # previous version of themselves, and an edit made here cannot be verified
    # until after it is committed. That is how the literal control identity went
    # unnoticed: it was correct in the working tree and wrong in the clone.
    shutil.copy2(os.path.abspath(__file__),
                 os.path.join(CLONE, 'tests', os.path.basename(__file__)))

    print('\nB. CONTROL -- a clone with an ordinary identity PASSES')
    # Without this, every arm below is "the tool fails on anything".
    git(CLONE, 'config', 'user.name', CLEAN_NAME)
    git(CLONE, 'config', 'user.email', CLEAN_EMAIL)
    rc, out = run(CLONE)
    ok('an ordinary identity is CLEAN', rc == 0, 'exit=%d\n%s' % (rc, out[-300:]))

    print('\nC. THE DEFECT -- the probes\' own identity in LOCAL config is REFUSED')
    git(CLONE, 'config', 'user.name', 'probe')
    git(CLONE, 'config', 'user.email', 'probe@local')
    rc, out = run(CLONE)
    ok('the tool refuses', rc == 1, 'exit=%d\n%s' % (rc, out[-400:]))
    ok('...and says COMPROMISED rather than a soft note',
       'COMPROMISED' in out, out[-400:])
    ok('...and names the value it matched', 'probe@local' in out, out[-400:])
    ok('...and names a probe that uses it, so the reader can check the claim',
       'tests/push_gate/' in out, out[-400:])
    ok('...and gives the --local unset, which is where it persists',
       '--local --unset user.email' in out, out[-400:])

    print('\nD. THE LIST IS DERIVED, NOT HARDCODED')
    # A hardcoded list goes stale the first time somebody writes a new probe --
    # the failure the app map and the tooling inventory were both rewritten for.
    # THE NAME IS RESET FIRST, AND THAT IS NOT TIDINESS. Section C left
    # user.name='probe', which is itself a known identity -- so the first
    # version of these two arms refused for the NAME and passed while proving
    # nothing about the email under test. The `-c` mutation SURVIVED because
    # of exactly that. Only the value under test may be able to trigger.
    git(CLONE, 'config', 'user.name', CLEAN_NAME)
    newprobe = os.path.join(CLONE, 'tests', 'zz_identity_fixture_probe.py')
    io.open(newprobe, 'w', encoding='utf-8', newline='\n').write(
        "git('config', 'user.email', '" + ARG_FIXTURE + "')\n")
    git(CLONE, 'config', 'user.email', ARG_FIXTURE)
    rc, out = run(CLONE)
    ok('an identity introduced by a NEW probe is picked up with no edit here',
       rc == 1 and ARG_FIXTURE in out.split('COMPROMISED')[-1],
       'exit=%d\n%s' % (rc, out[-400:]))
    ok('...and the source file is named',
       'zz_identity_fixture_probe.py' in out, out[-400:])
    os.remove(newprobe)

    # BOTH SPELLINGS, and this arm exists because its absence let a mutation
    # SURVIVE. The first version of section D only wrote an ARGUMENT-form
    # fixture, so deleting the `-c user.email=x` branch from the scanner changed
    # nothing here -- while every push-gate probe in this repo uses exactly that
    # form. An untested branch of a checker is a branch that can be deleted.
    io.open(newprobe, 'w', encoding='utf-8', newline='\n').write(
        "git(wt, '-c', 'user.email=" + DASHC_FIXTURE + "', 'commit')\n")
    git(CLONE, 'config', 'user.email', DASHC_FIXTURE)
    rc, out = run(CLONE)
    ok('the `-c user.email=x` spelling is picked up too',
       rc == 1 and DASHC_FIXTURE in out.split('COMPROMISED')[-1],
       'exit=%d\n%s' % (rc, out[-400:]))
    os.remove(newprobe)

    print('\nE. THE HISTORY COUNT IS REPORTED AND NEVER FAILED ON')
    git(CLONE, 'config', 'user.name', CLEAN_NAME)
    git(CLONE, 'config', 'user.email', CLEAN_EMAIL)
    rc, out = run(CLONE)
    ok('a clone whose HISTORY carries the identity still passes once its config '
       'is fixed', rc == 0, 'exit=%d\n%s' % (rc, out[-300:]))
    ok('...and the count is still printed, so it is not forgotten',
       'history, NOT rewritten' in out, out[-300:])
finally:
    rmtree(TMP)
    print('\nF. this clone was never touched')
    after = (git(REPO, 'config', '--get', 'user.name').stdout.strip(),
             git(REPO, 'config', '--get', 'user.email').stdout.strip())
    ok('the identity is unchanged in THIS clone', after == before,
       'before=%r after=%r' % (before, after))
    ok('and no local override was left behind',
       git(REPO, 'config', '--local', '--get', 'user.email').stdout.strip() == '',
       git(REPO, 'config', '--local', '--get', 'user.email').stdout.strip())
    ok('the throwaway clone is gone', not os.path.isdir(TMP))

print('\n%d failure(s)' % len(FAIL))
for f in FAIL:
    print('  - ' + f)
sys.exit(1 if FAIL else 0)
