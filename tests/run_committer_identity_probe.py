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

── HERMETIC, SO THE VERDICT IS NOT ABOUT WHOSE MACHINE THIS IS ───────────────
Every git command and tool invocation against the throwaway clone runs with
GIT_CONFIG_GLOBAL and GIT_CONFIG_SYSTEM pointed at an empty file. git MERGES
system, global and local, so without that an operator's ambient identity
decides what the arms measure. Section B0 drives both directions: a hostile
global identity DOES reach the checker, and under the isolation it does not.

SECTION A IS THE ONE EXCEPTION AND IT IS DELIBERATE -- its job is to report
what THIS clone will really commit as, ambient config included. Section F
asserts the local override layer is byte-identical before and after, which is
a DELTA; whether a local override exists at all is the operator's business and
this probe neither changes nor judges it.

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

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REL = 'tools/committer_identity_check.py'
FAIL = []


def ok(name, cond, detail=''):
    print('  %s %s%s' % ('PASS ' if cond else 'FAIL ', name,
                         '' if cond else '\n        ' + str(detail)[:400]))
    if not cond:
        FAIL.append(name)


def git(cwd, *args, **kw):
    return subprocess.run(['git', '-C', cwd] + list(args), capture_output=True,
                          text=True, encoding='utf-8', errors='replace',
                          env=kw.get('env'))


def run(cwd, *args, **kw):
    env = dict(kw.get('env') or os.environ, PYTHONIOENCODING='utf-8')
    r = subprocess.run([sys.executable, os.path.join(cwd, REL.replace('/', os.sep))]
                       + list(args), capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=cwd,
                       env=env)
    return r.returncode, (r.stdout or '') + (r.stderr or '')


# ── HERMETIC: THE ARMS DO NOT READ WHOEVER'S MACHINE THIS IS (2026-10-14) ────
# WHAT WENT WRONG. Section F asked whether this clone has ANY local
# `user.email`, in the absolute. This clone has one -- `fx@example.invalid`,
# set deliberately and not by any probe -- so the arm failed, and the failure
# was reported as the probe's verdict on a thing the probe had no business
# deciding. Worse, the suggested repairs were both wrong: unsetting a
# committer identity is not a test's call to make, and loosening the arm
# would have retired the only check that the probe cleans up after itself.
#
# THE ARM WAS ASKING THE WRONG QUESTION, not asking it too strictly. Its name
# is "no local override was LEFT BEHIND" -- a BEFORE/AFTER property of this
# RUN. Absolute emptiness is a property of the operator's clone. One of those
# this file can assert; the other it cannot, and conflating them makes a
# correct run red on one machine and green on another.
#
# AND THE SAME CONFLATION REACHES THE OTHER ARMS FROM THE OTHER DIRECTION.
# Sections B-E set LOCAL config in a throwaway clone, but git MERGES system,
# global and local -- so an operator whose GLOBAL identity happened to be a
# known throwaway would have section B ("an ordinary identity is CLEAN")
# refuse, and an operator with no global identity at all reaches different
# code in the checker than one with. Neither is a fact about the subject.
#
# So every git command and every tool invocation against the THROWAWAY clone
# runs with GIT_CONFIG_GLOBAL and GIT_CONFIG_SYSTEM pointed at an empty file.
# Local config -- which the arms set themselves, deliberately -- still applies,
# because that is the layer the defect lived in.
#
# SECTION A IS DELIBERATELY *NOT* ISOLATED, and that is the one exception. Its
# job is to report what THIS clone will really commit as, ambient config
# included; isolating it would have it answer about a machine that does not
# exist. It is also read-only, and section F proves that.
def isolated_env(empty_cfg):
    return dict(os.environ,
                GIT_CONFIG_GLOBAL=empty_cfg,
                GIT_CONFIG_SYSTEM=empty_cfg,
                GIT_CONFIG_NOSYSTEM='1')


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
# CAPTURED, NOT JUDGED. Section F compares this against the same read after
# every arm has run. What it holds is none of this probe's business; whether
# this probe CHANGED it is entirely its business.
local_before = (git(REPO, 'config', '--local', '--get', 'user.name').stdout.strip(),
                git(REPO, 'config', '--local', '--get', 'user.email').stdout.strip())
print('    this clone commits as %s <%s>%s'
      % (before[0], before[1],
         '  (from LOCAL config, which overrides global)' if local_before[1]
         else '  (no local override; inherited)'))
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

    # The empty config the isolated arms read instead of this machine's.
    EMPTY_CFG = os.path.join(TMP, 'empty.gitconfig')
    io.open(EMPTY_CFG, 'w', encoding='utf-8', newline='\n').write('')
    ISO = isolated_env(EMPTY_CFG)

    print('\nB0. CONTROL -- the isolation is real, and the hostile fixture is live')
    # TWO ARMS, BOTH DIRECTIONS, and neither alone is worth anything.
    #
    # The throwaway clone has NO local user identity yet, so whatever git reads
    # at this moment comes from GLOBAL or SYSTEM. A hostile global file carrying
    # a KNOWN throwaway identity is written and handed to the checker: it must
    # REFUSE, which proves ambient config can reach the subject at all. Without
    # this arm "isolation works" is satisfied by a fixture that was inert.
    #
    # Then the same clone, same state, under the probe's own isolation: the
    # checker must NOT see it. That is the arm that fails if somebody deletes
    # isolated_env() or stops passing ISO -- which is the whole point, because
    # the symptom of missing isolation is a pass or fail that depends on whose
    # machine it is, and that is invisible from one green run.
    HOSTILE_CFG = os.path.join(TMP, 'hostile.gitconfig')
    io.open(HOSTILE_CFG, 'w', encoding='utf-8', newline='\n').write(
        '[user]\n\tname = probe\n\temail = probe' + '@local\n')
    hostile = dict(os.environ, GIT_CONFIG_GLOBAL=HOSTILE_CFG,
                   GIT_CONFIG_SYSTEM=EMPTY_CFG)
    rc_h, out_h = run(CLONE, env=hostile)
    ok('a THROWAWAY identity in ambient GLOBAL config really does reach the '
       'checker -- so the fixture below is not inert',
       rc_h == 1 and 'COMPROMISED' in out_h, 'exit=%d\n%s' % (rc_h, out_h[-400:]))
    rc_i, out_i = run(CLONE, env=ISO)
    ok('...and under this probe\'s ISOLATION the same clone is CLEAN -- ambient '
       'global/system config cannot change any verdict below',
       rc_i == 0 and 'COMPROMISED' not in out_i,
       'exit=%d\n%s' % (rc_i, out_i[-400:]))

    print('\nB. CONTROL -- a clone with an ordinary identity PASSES')
    # Without this, every arm below is "the tool fails on anything".
    git(CLONE, 'config', 'user.name', CLEAN_NAME, env=ISO)
    git(CLONE, 'config', 'user.email', CLEAN_EMAIL, env=ISO)
    rc, out = run(CLONE, env=ISO)
    ok('an ordinary identity is CLEAN', rc == 0, 'exit=%d\n%s' % (rc, out[-300:]))

    print('\nC. THE DEFECT -- the probes\' own identity in LOCAL config is REFUSED')
    git(CLONE, 'config', 'user.name', 'probe', env=ISO)
    git(CLONE, 'config', 'user.email', 'probe@local', env=ISO)
    rc, out = run(CLONE, env=ISO)
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
    git(CLONE, 'config', 'user.name', CLEAN_NAME, env=ISO)
    newprobe = os.path.join(CLONE, 'tests', 'zz_identity_fixture_probe.py')
    io.open(newprobe, 'w', encoding='utf-8', newline='\n').write(
        "git('config', 'user.email', '" + ARG_FIXTURE + "')\n")
    git(CLONE, 'config', 'user.email', ARG_FIXTURE, env=ISO)
    rc, out = run(CLONE, env=ISO)
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
    git(CLONE, 'config', 'user.email', DASHC_FIXTURE, env=ISO)
    rc, out = run(CLONE, env=ISO)
    ok('the `-c user.email=x` spelling is picked up too',
       rc == 1 and DASHC_FIXTURE in out.split('COMPROMISED')[-1],
       'exit=%d\n%s' % (rc, out[-400:]))
    os.remove(newprobe)

    print('\nE. THE HISTORY COUNT IS REPORTED AND NEVER FAILED ON')
    git(CLONE, 'config', 'user.name', CLEAN_NAME, env=ISO)
    git(CLONE, 'config', 'user.email', CLEAN_EMAIL, env=ISO)
    rc, out = run(CLONE, env=ISO)
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
    # ── BEFORE/AFTER, NOT ABSOLUTE EMPTINESS (repaired 2026-10-14) ───────────
    # This arm read `--local --get user.email == ''`. It is named "no local
    # override was LEFT BEHIND" and it was testing "no local override EXISTS",
    # which is a fact about whoever's clone this is. This clone carries
    # `fx@example.invalid` in local config, set deliberately and by no probe, so
    # the arm failed and reported a correct run as a defect -- an ENVIRONMENT
    # PRECONDITION wearing the costume of a finding. The arm immediately above
    # it passing was the evidence the probe had not written it.
    #
    # Both repairs it suggested were wrong. Unsetting a committer identity is
    # not a test's decision -- the identity is the operator's, and a suite that
    # quietly rewrites it is the 2026-09-10 defect with better manners. And
    # dropping the arm would retire the only check that this probe cleans up
    # after itself.
    #
    # The property is a DELTA, so it is asserted as one. The local layer is
    # named separately from the merged one because the merged read above would
    # stay equal if a probe wrote a local override identical to the inherited
    # value -- which is exactly the shape that hid for three days.
    local_after = (git(REPO, 'config', '--local', '--get', 'user.name').stdout.strip(),
                   git(REPO, 'config', '--local', '--get', 'user.email').stdout.strip())
    ok('the LOCAL override layer is byte-identical to before this run -- nothing '
       'was added, changed or unset here',
       local_after == local_before,
       'local before=%r after=%r' % (local_before, local_after))
    # REPORTED, NEVER ASSERTED. What the operator's local config holds is their
    # call; this line exists so a reader knows which identity the commits from
    # this clone will carry without having to go and look.
    if local_before[1]:
        print('    NOTE this clone has a LOCAL identity: %s <%s>. That is the '
              'operator\'s' % (local_before[0], local_before[1]))
        print('    decision and this probe neither changes it nor judges it. '
              'Section A asserts')
        print('    it is not a known THROWAWAY identity, which is the thing '
              'that would matter.')
    ok('the throwaway clone is gone', not os.path.isdir(TMP))

print('\n%d failure(s)' % len(FAIL))
for f in FAIL:
    print('  - ' + f)
sys.exit(1 if FAIL else 0)
