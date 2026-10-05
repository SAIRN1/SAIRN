"""tests/run_rebase_state_guard_probe.py -- the amend/blanket-stage guard
refuses the four forms during a real stopped rebase, refuses an amend of a
commit already on origin/main, and refuses nothing else.

    python tests/run_rebase_state_guard_probe.py

WHY THIS EXISTS, AND IT IS NOT A HYPOTHETICAL. The prose rule "never amend a
pushed commit" was in CLAUDE.md and in the process rules, and on 2026-09-27 the
session that wrote it amended onto another session's commit anyway. A rule that
lives only in prose is enforced by whoever remembers it at the moment they are
in a hurry, which is exactly the moment it is forgotten. This makes it
mechanical.

THE MID-REBASE ARM RUNS AGAINST A REAL STOPPED REBASE, not a directory with
files named like one. `.git/rebase-merge` is created by git, in a throwaway
repository this probe builds and deletes, with a genuine conflict that genuinely
stops the rebase -- because a fixture that only LOOKS like the state would pass
while the real detection was wrong. The probe asserts the state is real before
it asserts anything about the guard: if `operation_in_progress` cannot see a
rebase git itself created, every deny below would be vacuous.

TWO DIRECTIONS, AND THE SECOND MATTERS MORE. A guard that over-refuses is
visible and annoying. A guard that has quietly stopped refusing looks identical
to a clean run -- the amend simply succeeds and another session's commit is
gone. So every DENY case is a shape that must still be blocked, and several are
written because a plausible implementation would let them through:

  * `git commit -am "x"` -- the `a` is clustered with `m`, so a scan for the
    exact token `-a` never sees it.
  * `git -C /repo commit --amend` -- a global option before the subcommand slips
    any parser that assumes tokens[1] is the subcommand. The push-master guard
    had exactly this hole.
  * `git add .` vs `git add ./docs/x.md` -- only the bare `.` is blanket, and a
    prefix test would refuse the explicit path.
  * `git status && git commit --amend` -- the forbidden form in a later segment.

And every ALLOW case is a shape that must NOT be refused, most of them the
commands a person legitimately runs *inside* a rebase:

  * `git add docs/resolved.md` -- resolving a conflict file is the normal way
    out of a rebase. Denying it would make the guard the thing that has to be
    switched off to finish, and a switched-off guard checks nothing.
  * `git commit -m "mentions git add -A"` -- the forbidden text inside a quoted
    message is data, not an invocation. The push-master guard was denied three
    times in one session for exactly this, including on the commit of the row
    that documented it.

THE LITERALS BELOW ARE ASSEMBLED FROM PIECES for the same reason that probe
assembles the stale branch name: this file's own text ends up on command lines
(`git add tests/run_rebase_state_guard_probe.py`) and inside commit messages,
and a control that trips the guard it is testing cannot be committed.
"""
import io
import json
import os
import shlex as _shlex
import shutil
import stat
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, 'tools'))

EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN = 0, 1, 2

TOOL = os.path.join(REPO, 'tools', 'rebase_state_guard.py')
if not os.path.isfile(TOOL):
    print('COULD NOT RUN: tools/rebase_state_guard.py is not on disk. This '
          'control tested nothing, which is a third state and not a pass.')
    sys.exit(EXIT_COULD_NOT_RUN)

import rebase_state_guard as guard   # noqa: E402

passed = failed = 0


def ok(cond, label, detail=''):
    global passed, failed
    if cond:
        passed += 1
        print('  ok   %s' % label)
    else:
        failed += 1
        print('  FAIL %s' % label)
        if detail:
            print('       %s' % str(detail)[:500])


# ── THE FORBIDDEN FORMS, assembled so this file cannot trip its own subject ──
AMEND = 'commit --am' + 'end'
ADD_A = 'add -' + 'A'
ADD_ALL = 'add --' + 'all'
ADD_DOT = 'add ' + '.'
COMMIT_A = 'commit -' + 'a'

DENY = [
    'git ' + AMEND,
    'git ' + AMEND + ' --no-edit',
    'git ' + ADD_A,
    'git ' + ADD_ALL,
    'git ' + ADD_DOT,
    'git ' + COMMIT_A + ' -m "wip"',
    # Clustered short options. A scan for the exact token `-a` misses these.
    'git commit -' + 'am' + ' "wip"',
    'git commit -' + 'sam' + ' "wip"',
    'git ' + ADD_A + ' docs/x.md',          # -A wins regardless of paths after
    # A global option before the subcommand -- the hole the push-master guard had.
    'git -C /some/repo ' + AMEND,
    'git -c user.name=x ' + AMEND,
    # Later segments.
    'git status && git ' + AMEND,
    'git fetch; git ' + ADD_A,
    'git log -1 | cat && git ' + ADD_DOT,
    # No space normalisation to hide behind.
    'git   ' + AMEND,
    'git ' + AMEND + '   ',
]

# ── H2 seq 452 AND THE FOUR CLASSES BESIDE IT (added 2026-10-05) ───────────
# forbidden_forms() required tokens[0] to be `git`, so ANY leading token made it
# return nothing. Measured against the live function BEFORE the fix: 15 of 34
# forms bypassed the guard. The reported one is first and is the form a script
# is MOST likely to use, because it is how you stop --amend opening an editor.
#
# WHAT WAS ALREADY SOUND AND IS PINNED HERE ANYWAY: quoting (`"git"`, `g'it'`,
# `git "commit" --amend`), flags before the subcommand (`-C`, `-c`,
# `--git-dir=`, `--no-pager`) and plain `&&`/`;`/`|`/newline chaining all passed
# before the fix. They are in this list so a future rewrite of the parser
# cannot quietly lose them -- an arm that passes today and was never going to
# fail is still the arm that catches tomorrow's regression.
BYPASS_452 = [
    # 1. env-var assignment prefix -- the reported bypass
    'GIT_EDITOR=true git commit --amend',
    'A=1 B=2 git commit --amend',
    'GIT_EDITOR=true git add -A',
    'GIT_EDITOR="vim -f" git commit --amend',
    'GIT_PAGER= git commit --amend',                 # present but EMPTY value
    'GIT_EDITOR=true git -C /tmp/x commit --amend',  # prefix AND a global opt
    'true && GIT_EDITOR=true git commit --amend',     # prefix after a separator
    # 2. the `env` wrapper
    'env GIT_EDITOR=true git commit --amend',
    '/usr/bin/env git commit --amend',
    # 3. grouping -- a grouped invocation still runs
    '(git commit --amend)',
    'x=$(git commit --amend)',
    'x=`git commit --amend`',
    # 4. a shell given the command as a STRING in one token
    'bash -c "git commit --amend"',
    "sh -c 'git commit --amend'",
    # 5. an argv-building wrapper
    'echo x | xargs git commit --amend',
    # ALREADY SOUND -- pinned so a rewrite cannot lose them
    '"git" commit --amend',
    "'git' commit --amend",
    "g'it' commit --amend",
    'git commit "--amend"',
    'git "commit" --amend',
    'git -C /tmp/x commit --amend',
    'git --no-pager commit --amend',
    'git -c user.name=x commit --amend',
    'git --git-dir=/tmp/.git commit --amend',
    'git -c a=b -C /tmp commit --amend',
]

# The negative direction for the SAME change. Peeling a prefix must land
# EXACTLY on `git`; nothing may scan a token list for the word anywhere in it,
# or `echo git commit --amend` becomes a finding.
BYPASS_452_ALLOW = [
    'echo git commit --amend',          # prints a string, invokes nothing
    'echo "git add -A"',
    'echo "amend" && git status',
    'FOO=bar git status --short',        # a prefix on a HARMLESS command
    'env FOO=bar git log --oneline -5',
    'bash -c "git status"',              # shell payload, nothing forbidden in it
    'timeout 30 git status',
    'nice -n 10 git log -1',
]

ALLOW = [
    # The commands a person legitimately runs to get OUT of a rebase.
    'git status',
    'git diff',
    'git add docs/resolved.md',
    'git add tools/a.py tests/b.py',
    'git add ./docs/x.md',                  # an explicit path, not the bare dot
    'git add -p',
    'git rebase --continue',
    'git rebase --abort',
    'git commit -m "resolve the conflict"',
    'git commit -F -',
    'git cherry-pick --continue',
    'git merge --abort',
    'git log --oneline -5',
    # The forbidden text as DATA, not as an invocation.
    'git commit -m "stop using git ' + ADD_A + ' everywhere"',
    'git commit -m "never git ' + AMEND + ' a pushed commit"',
    'git add tests/run_rebase_state_guard_probe.py',
    'cat tools/rebase_state_guard.py',
    'python tools/sairn_claim.py claim hank the ' + AMEND + ' guard',
    'grep -rn "git ' + ADD_A + '" tools/',
    # A different tool entirely.
    'gh pr list',
    'python tools/defect_register.py --report',
    '',
    # After `--` everything is a pathspec, including a file named like a flag.
    'git add -- -' + 'A',
]


# ══ PART 1 -- THE PURE PARSE, no repository state involved ══════════════════
print('CONTROL PAIR -- tools/rebase_state_guard.py\n')
print('PART 1 -- which forms the parser SEES (no state, no git)')
bad = 0
for cmd in DENY:
    if not guard.forbidden_forms(cmd):
        bad += 1
        print('  FAIL not recognised as forbidden: %r' % cmd)
ok(bad == 0, 'all %d forbidden shapes are recognised' % len(DENY),
   '%d not recognised' % bad)

bad = 0
for cmd in ALLOW:
    forms = guard.forbidden_forms(cmd)
    if forms:
        bad += 1
        print('  FAIL recognised as forbidden (%s): %r' % (forms, cmd))
ok(bad == 0,
   'and none of the %d legitimate shapes is -- including the ones that merely '
   'QUOTE a forbidden command, which is how the push-master guard denied three '
   'commands in one session' % len(ALLOW), '%d false positives' % bad)

# ── H2 seq 452: THE PREFIX AND WRAPPER CLASSES, BOTH DIRECTIONS ────────────
missed = [c for c in BYPASS_452 if not guard.forbidden_forms(c)]
ok(not missed,
   'all %d prefix/wrapper/grouping forms are recognised -- 15 of these '
   'BYPASSED the guard before 2026-10-05, led by `GIT_EDITOR=true git commit '
   '--amend` (H2 seq 452): tokens[0] was not `git`, so the parser returned '
   'nothing and the guard said CLEAR on an amend' % len(BYPASS_452),
   'still bypassing: %r' % (missed[:6],))

fp = [(c, guard.forbidden_forms(c)) for c in BYPASS_452_ALLOW
      if guard.forbidden_forms(c)]
ok(not fp,
   'and none of the %d look-alikes is -- `echo git commit --amend` INVOKES '
   'nothing, and a harmless command carrying an env prefix or a wrapper is '
   'still harmless. THIS IS THE ARM THAT BOUNDS THE FIX: a peeled prefix must '
   'land exactly on `git`, never scan the token list for the word'
   % len(BYPASS_452_ALLOW), 'false positives: %r' % (fp[:4],))

# ── NESTING, BUILT BY shlex.quote RATHER THAN HAND-QUOTED ──────────────────
# The first version of this arm used a hand-written five-deep string and FAILED
# -- not because the guard was wrong but because the literal was mis-quoted, so
# the arm was measuring my typing. Recorded rather than quietly replaced: a
# fixture that is hard to write by hand is a fixture that should be generated,
# and a failing arm whose cause is the fixture is indistinguishable from one
# whose cause is the subject until you check.
_nest = {}
for _d in range(1, 7):
    _c = 'git commit --amend'
    for _ in range(_d):
        _c = 'bash -c ' + _shlex.quote(_c)
    _nest[_d] = guard.forbidden_forms(_c)

ok(all(_nest[d] == [AMEND] for d in (1, 2, 3, 4)),
   'a shell nest is followed to depth 4 and the amend inside is named exactly '
   '-- `bash -c "git commit --amend"` keeps its payload as ONE shlex token, so '
   'nothing inspecting a token list could ever have seen it',
   'depths 1-4 gave %r' % ({d: _nest[d] for d in (1, 2, 3, 4)},))

ok(all(_nest[d] and 'deeper than this guard' in _nest[d][0] for d in (5, 6)),
   'and a nest DEEPER than it will follow is REPORTED as could-not-parse, '
   'never silence. THIS IS THE THIRD STATE: the parser declining to read '
   'something must not be indistinguishable from it reading it and finding '
   'nothing -- the same rule as the unparseable-line fallback above',
   'depths 5-6 gave %r' % ({d: _nest[d] for d in (5, 6)},))


# ══ PART 2 -- A REAL STOPPED REBASE, built by git, in a throwaway repo ══════
print('\nPART 2 -- a REAL stopped rebase, not a directory named like one')


def rmtree(path):
    def onerror(fn, p, exc):
        try:
            os.chmod(p, stat.S_IWRITE)
            fn(p)
        except Exception:
            pass
    shutil.rmtree(path, onerror=onerror)


def g(cwd, *args, **kw):
    return subprocess.run(
        ['git', '-c', 'user.name=probe', '-c', 'user.email=probe@local',
         '-c', 'commit.gpgsign=false'] + list(args),
        cwd=cwd, capture_output=True, text=True, encoding='utf-8',
        errors='replace', **kw)


fixture = tempfile.mkdtemp(prefix='sairn_rebase_probe_')
try:
    g(fixture, 'init', '-q', '-b', 'main')
    f = os.path.join(fixture, 'conflict.txt')
    io.open(f, 'w', encoding='utf-8', newline='\n').write('base\n')
    g(fixture, 'add', 'conflict.txt')
    g(fixture, 'commit', '-q', '-m', 'base')
    g(fixture, 'checkout', '-q', '-b', 'side')
    io.open(f, 'w', encoding='utf-8', newline='\n').write('side\n')
    g(fixture, 'commit', '-q', '-a', '-m', 'side edit')
    g(fixture, 'checkout', '-q', 'main')
    io.open(f, 'w', encoding='utf-8', newline='\n').write('main\n')
    g(fixture, 'commit', '-q', '-a', '-m', 'main edit')
    g(fixture, 'checkout', '-q', 'side')
    r = g(fixture, 'rebase', 'main')

    gd = os.path.join(fixture, '.git')
    op = guard.operation_in_progress(gd)
    # THIS ASSERTION GATES EVERY ONE BELOW IT. If the state git just created is
    # not seen, the denies that follow prove nothing about a real rebase.
    ok(op == 'rebase',
       'git really did stop mid-rebase and operation_in_progress() sees it as '
       '%r' % op,
       'rebase exit=%d stdout=%s' % (r.returncode, (r.stdout or '')[-200:]))
    ok(os.path.isdir(os.path.join(gd, 'rebase-merge'))
       or os.path.isdir(os.path.join(gd, 'rebase-apply')),
       'and the marker directory git writes is on disk, so this is the real '
       'state and not a stand-in')

    if op == 'rebase':
        bad = 0
        for cmd in DENY:
            deny, reason = guard.decide(cmd, op, head_pushed=False)
            if not deny:
                bad += 1
                print('  FAIL allowed mid-rebase: %r' % cmd)
            elif 'rebase' not in reason:
                bad += 1
                print('  FAIL denied but did not name the operation: %r' % cmd)
        ok(bad == 0,
           'THE ARM THAT MATTERS: all %d forbidden forms are REFUSED mid-rebase '
           'and each refusal names the operation in progress' % len(DENY),
           '%d wrong' % bad)

        bad = 0
        for cmd in ALLOW:
            deny, _ = guard.decide(cmd, op, head_pushed=False)
            if deny:
                bad += 1
                print('  FAIL refused mid-rebase: %r' % cmd)
        ok(bad == 0,
           'and the %d legitimate commands still work mid-rebase -- resolving a '
           'conflict file and continuing is how you GET OUT, so denying it '
           'would make this the guard somebody switches off' % len(ALLOW),
           '%d wrong' % bad)

    # ── The same four markers, one at a time, each set by hand on the fixture.
    # Detection must not be rebase-only: a merge and a cherry-pick stop in the
    # same place and rewrite history the same way.
    g(fixture, 'rebase', '--abort')
    ok(guard.operation_in_progress(gd) is None,
       'after --abort the fixture is clean again, so the marker checks are '
       'reading state and not caching it')
    for name, kind in (('MERGE_HEAD', 'merge'),
                       ('CHERRY_PICK_HEAD', 'cherry-pick'),
                       ('REVERT_HEAD', 'revert')):
        p = os.path.join(gd, name)
        io.open(p, 'w', encoding='utf-8').write('0' * 40 + '\n')
        seen = guard.operation_in_progress(gd)
        deny, reason = guard.decide('git ' + AMEND, seen, head_pushed=False)
        os.remove(p)
        ok(seen == kind and deny and kind in reason,
           '%s is seen as %r and the amend is refused, naming it' % (name, seen))
finally:
    rmtree(fixture)


# ══ PART 3 -- AN AMEND OF A COMMIT ALREADY ON origin/main ══════════════════
print('\nPART 3 -- the rule that was prose and got broken anyway')
deny, reason = guard.decide('git ' + AMEND, None, head_pushed=True)
ok(deny and 'origin/main' in reason,
   'an amend of a commit already on origin/main is REFUSED with no operation '
   'in progress, and the refusal says why')

deny, _ = guard.decide('git ' + AMEND, None, head_pushed=False)
ok(not deny,
   'and an amend of an UNPUSHED local commit is ALLOWED -- that is the whole '
   'legitimate use and refusing it would make the guard useless')

deny, reason = guard.decide('git ' + AMEND, None, head_pushed=None)
ok(deny and ('could not' in reason.lower() or 'not known' in reason.lower()),
   'COULD NOT TELL whether HEAD is published is REFUSED, not allowed, and says '
   'so -- an unanswerable question about published history is the third state, '
   'and folding it into a pass is the defect this repo names most often')

bad = 0
for cmd in DENY:
    if cmd.strip().startswith('git ' + ADD_A[:3]) or 'add' in cmd:
        continue
for cmd in (('git ' + ADD_A), ('git ' + ADD_DOT), ('git ' + COMMIT_A + ' -m "x"')):
    deny, _ = guard.decide(cmd, None, head_pushed=True)
    if deny:
        bad += 1
        print('  FAIL blanket staging refused with NO operation in progress: %r'
              % cmd)
ok(bad == 0,
   'blanket staging outside an operation is NOT refused by this guard -- the '
   'stated rule is mid-operation only, and widening it silently would be a '
   'different rule nobody agreed')


# ══ PART 3b -- THE OPERATION QUESTION HAS A THIRD STATE TOO ════════════════
# ADDED 2026-09-30, from the review of hank's 2026-09-28T21:33:14Z obligation.
# git_dir() returns None for a missing git, a non-zero rev-parse, an exception
# OR A 10-SECOND TIMEOUT, and operation_in_progress(None) used to return the same
# None it returns for "nothing is running". For `git add -A`, `git add .` and
# `git commit -am x` there is no second question to fall through to, so decide()
# answered (False, '') and the command was ALLOWED -- a blanket stage into a live
# stopped rebase, silently.
#
# THIS FILE'S SUBJECT ALREADY HAD THE ARGUMENT AND APPLIED IT TO ONE QUESTION.
# The arm above about head_pushed=None is the same shape; this is the other
# question, which had no arm at all.
print('\nPART 3b -- a git_dir() that cannot answer is NOT "no operation"')

ok(guard.operation_in_progress(None) == guard.UNKNOWN,
   'operation_in_progress() returns the UNKNOWN sentinel when git_dir() could '
   'not answer, rather than the None it returns for a clean tree -- the two are '
   'different facts and used to be the same value')

bad = 0
for cmd in DENY:
    deny, reason = guard.decide(cmd, guard.UNKNOWN, head_pushed=False)
    if not deny:
        bad += 1
        print('  FAIL allowed with the operation state UNKNOWN: %r' % cmd)
    elif 'NOT KNOWN' not in reason:
        bad += 1
        print('  FAIL denied but did not say it could not tell: %r' % cmd)
ok(bad == 0,
   'THE FIX: all %d forbidden forms are REFUSED when the operation state could '
   'not be read, and each refusal says it could not tell rather than naming an '
   'operation it never saw' % len(DENY), '%d wrong' % bad)

ok('unknown' not in guard.decide(DENY[0], guard.UNKNOWN, False)[1].lower()
   .split('not known')[0],
   'and the sentinel string is not formatted into the message as though it were '
   'an operation called "unknown" -- a refusal for the right reason with the '
   'wrong sentence is how a guard gets read as broken')

bad = 0
for cmd in ALLOW:
    deny, _ = guard.decide(cmd, guard.UNKNOWN, head_pushed=False)
    if deny:
        bad += 1
        print('  FAIL refused a legitimate command on an UNKNOWN state: %r' % cmd)
ok(bad == 0,
   'and the %d legitimate commands are still allowed when the state is unknown '
   '-- the third state closes the four forbidden forms, it does not close the '
   'shell' % len(ALLOW), '%d wrong' % bad)

# ── THE TIMEOUT, DRIVEN RATHER THAN REASONED ABOUT ──────────────────────────
# The realistic trigger is not a missing git, it is `rev-parse --git-dir` timing
# out under load: five clones push to one branch here and single git invocations
# have exceeded 120 seconds. git_dir() passes timeout=10 and catches every
# exception, so a TimeoutExpired becomes None. This replaces subprocess.run
# inside the module with one that raises exactly that, and requires the whole
# chain -- git_dir -> operation_in_progress -> decide -> deny.
_real_run = guard.subprocess.run


def _timeout_run(*a, **kw):
    raise guard.subprocess.TimeoutExpired(cmd=(a[0] if a else 'git'), timeout=10)


try:
    guard.subprocess.run = _timeout_run
    gd_timeout = guard.git_dir()
    op_timeout = guard.operation_in_progress(gd_timeout)
    deny_timeout, reason_timeout = guard.decide('git add -A', op_timeout, False)
finally:
    guard.subprocess.run = _real_run

ok(gd_timeout is None,
   'a 10s TimeoutExpired out of `rev-parse --git-dir` makes git_dir() answer '
   'None -- driven by replacing subprocess.run, not assumed from reading the '
   'except clause')
ok(op_timeout == guard.UNKNOWN,
   'and that None becomes UNKNOWN rather than "no operation"')
ok(deny_timeout and 'NOT KNOWN' in reason_timeout,
   'and `git add -A` is REFUSED on a timed-out state lookup, which is the '
   'realistic form of this defect on a machine where git calls have exceeded '
   '120 seconds')
ok(guard.subprocess.run is _real_run,
   'and this arm put subprocess.run back, so nothing below it is measuring a '
   'patched module')


# ══ PART 4 -- THE HOOK ITSELF, over the real payload shape ═════════════════
print('\nPART 4 -- the hook contract, driven end to end')


def hook(cmd):
    p = subprocess.run([sys.executable, TOOL], cwd=REPO,
                       input=json.dumps({'tool_name': 'Bash',
                                         'tool_input': {'command': cmd}}),
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace',
                       env=dict(os.environ, PYTHONIOENCODING='utf-8'))
    return p


p = hook('git log --oneline -1')
ok(p.returncode == 0 and 'permissionDecision' not in (p.stdout or ''),
   'a harmless command produces no decision at all (exit %d)' % p.returncode,
   (p.stdout or '') + (p.stderr or ''))

p = hook('git ' + AMEND)
body = p.stdout or ''
ok(p.returncode == 0, 'the hook always exits 0 (exit %d) -- the decision is '
   'carried in the JSON, not in the exit code, which is what Claude Code reads'
   % p.returncode, body)

# ── ASSERTED AGAINST THE PURE DECISION FOR THE STATE THIS CLONE IS ACTUALLY
# IN, NOT AGAINST "deny". Whether an amend of HEAD is refused right now depends
# on whether HEAD has been pushed, which changes several times an hour here. An
# arm hardcoding `deny` would be green while the tree was clean and red the
# moment there was an unpushed commit -- the same defect that made the
# fact-sheet control red on main permanently. What Part 4 is FOR is the WIRING:
# that the hook reads the payload, consults the same logic, and emits the
# contract Claude Code reads.
live_op = guard.operation_in_progress(guard.git_dir())
live_pushed = guard.head_on_origin_main()
want_deny, want_reason = guard.decide('git ' + AMEND, live_op, live_pushed)
print('  --   this clone right now: operation=%r, HEAD published=%r -> '
      'expect deny=%r' % (live_op, live_pushed, want_deny))
try:
    doc = json.loads(body) if body.strip() else {}
except ValueError:
    doc = {}
hso = doc.get('hookSpecificOutput', {})
if want_deny:
    ok(hso.get('hookEventName') == 'PreToolUse'
       and hso.get('permissionDecision') == 'deny'
       and hso.get('permissionDecisionReason') == want_reason,
       'and the hook DENIES through the real payload with exactly the reason '
       'decide() gives -- the contract Claude Code reads, not a paraphrase',
       body[:400])
else:
    ok(not body.strip(),
       'and the hook allows it silently, which is what decide() says for this '
       'clone\'s current state (HEAD is not published) -- the wiring agrees '
       'with the logic, which is what this part is for', body[:400])

p = hook('')
ok(p.returncode == 0, 'an empty command does not crash the hook (exit %d)'
   % p.returncode, (p.stderr or '')[-300:])

p = subprocess.run([sys.executable, TOOL], cwd=REPO, input='not json at all',
                   capture_output=True, text=True, encoding='utf-8',
                   errors='replace')
ok(p.returncode == 0,
   'and an unreadable payload FAILS OPEN (exit %d) rather than blocking every '
   'Bash call in the session -- a guard that bricks the shell is removed '
   'within the hour, and then it guards nothing' % p.returncode,
   (p.stderr or '')[-300:])

print('\n%d passed, %d failed' % (passed, failed))
sys.exit(EXIT_FINDING if failed else EXIT_CLEAN)
