"""tests/run_all_tests_hook_gate_probe.py -- the report-only suite hook runs
after a PUSH, and after nothing else.

    python tests/run_all_tests_hook_gate_probe.py

WHY THIS EXISTS, and it is not hypothetical. `tools/run_all_tests.py --hook`
was wired as a PostToolUse hook on 2026-09-08 believing this entry in
`.claude/settings.json` restricted it to pushes:

    { "command": "python tools/run_all_tests.py --hook",
      "if": "Bash(git push*)" }          <-- NOT A REAL FIELD

A Claude Code hook entry has no `if`. The only gate it carries is `matcher`,
which matches the TOOL NAME -- so `matcher: "Bash"` means *every Bash tool
call*, and the unknown key was ignored in silence. The hook itself then read
the payload and discarded it under a comment saying "nothing here needs it".

What that cost, measured on 2026-09-09 rather than reasoned about: ten
concurrent copies of the whole suite in one clone inside four minutes, on a
single push; twenty-seven live processes by the time it was caught, some of
them from a second clone. The suite contains push-gate and seam probes that
make REAL commits on `main` and mutate tracked files before resetting -- so an
ordinary `git push origin main` raced one and published `PROBE clean endpoint
change` to origin/main, the branch Vercel deploys.

The lesson is bigger than the field name: A HOOK THAT LOOKS GATED IN CONFIG IS
UNGATED UNTIL THE HOOK ITSELF CHECKS. Its sibling, `tools/deploy_verify_notify.py`,
had the gate in the code the whole time (`if "git push" not in cmd`) and never
misfired once. Two hooks, same config block, one wrong belief between them.

This probe drives the REAL module and then the REAL binary. Sections 1-5 call
`hook_main()` with recorders in place of the suite, so "did it run?" is an
assertion and not a guess about timing. Section 6 runs the file itself as a
subprocess, because a fix verified only through an import is not verified for
the thing that actually executes. Section 7 reads `.claude/settings.json` and
fails if any hook entry carries an `if` again.
"""
import io
import json
import os
import subprocess
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import run_all_tests as rt              # noqa: E402

fails = 0


def check(label, actual, expected):
    global fails
    if actual == expected:
        print('  ok    %s' % label)
        return True
    fails += 1
    print('FAIL  %s\n        expected %r\n        actual   %r' % (label, expected, actual))
    return False


def ran(stdin_text):
    """Call hook_main with the suite -- and the suite lock -- replaced.

    Returns (suite_was_run, exit_code, stdout_text, lock_was_touched).

    THE LOCK IS STUBBED ON PURPOSE, and getting this wrong made this probe
    flake once already. `hook_main` also declines when another run of the suite
    holds `acquire_lock()`, which is a different, real mechanism added the same
    day. Leaving it live meant every "a push DOES run it" case failed whenever
    a genuine suite run happened to be in flight -- a red probe reporting the
    wrong defect. This probe tests the PAYLOAD gate; the lock has its own.
    Stubbing it also lets us assert the ordering below: the gate must decide
    before the lock is ever touched, or a `git status` would still be reaching
    into shared state on every keystroke.
    """
    seen = {'run': False, 'lock': False}
    saved = (rt.discover, rt._run, rt.acquire_lock, rt.release_lock,
             sys.stdin, sys.stdout)
    rt.discover = lambda: ([], [], [])
    rt._run = lambda js, py, quiet: (seen.__setitem__('run', True), ([], []))[1]
    rt.acquire_lock = lambda: (seen.__setitem__('lock', True), True)[1]
    rt.release_lock = lambda: None
    sys.stdin = io.StringIO(stdin_text)
    sys.stdout = io.StringIO()
    try:
        code = rt.hook_main()
        out = sys.stdout.getvalue()
    finally:
        (rt.discover, rt._run, rt.acquire_lock, rt.release_lock,
         sys.stdin, sys.stdout) = saved
    return seen['run'], code, out, seen['lock']


def payload(cmd):
    return json.dumps({'hook_event_name': 'PostToolUse', 'tool_name': 'Bash',
                       'tool_input': {'command': cmd}})


print('1. a non-push Bash command must not start the suite')
# These are ordinary calls a session makes constantly. Each one used to launch
# the entire suite, including the probes that commit to main.
for cmd in ('git status --porcelain',
            'git log --oneline -5',
            'python tools/sairn_claim.py list',
            'node --check stonedesk.html',
            'git pushd-is-not-a-thing',
            'git status && git commit -m "wip"'):
    was_run, code, out, locked = ran(payload(cmd))
    check('%-46s does not run the suite' % ('`%s`' % cmd[:44]), was_run, False)
    check('%-46s exits 0, says nothing, never takes the lock' % '',
          (code, out, locked), (0, '', False))

print('1b. A MENTION IS NOT A PUSH -- the case that tripped the first fix')
# The first version of this gate matched `\bgit\s+push\b` anywhere in the text,
# accepting stray mentions as cheap. The very next commit tripped it: this
# repo's commit messages quote the words, and `git commit -F -` with a heredoc
# saying "an ordinary `git push origin main` raced one of the probes" launched
# the whole suite mid-commit. Observed, not imagined -- these are the real
# shapes from that message.
for cmd in ('git commit -F - <<MSG\nan ordinary `git push origin main` raced one\nMSG',
            'echo "remember to git push after this"',
            'grep -rn "git push" docs/'):
    was_run, code, out, locked = ran(payload(cmd))
    check('a MENTION does not run the suite: %s' % cmd.splitlines()[0][:40],
          (was_run, locked), (False, False))

print('1c. NAMED FALSE NEGATIVES -- a silent gap, said out loud')
# A push wrapped in another command is not matched, and gets no report. Same
# blind spot deploy_verify_notify.py already documents for pushes driven from
# Python. Asserted so it stays a decision on the record rather than a surprise
# to whoever next wonders why a push produced no suite run.
for cmd in ('sudo git push origin main', 'xargs git push', 'time git push origin main'):
    check('%-34s is NOT seen as a push (accepted gap)' % ('`%s`' % cmd),
          ran(payload(cmd))[0], False)

print('2. a real push must still run it -- the gate must not be a mute button')
for cmd in ('git push origin main',
            'git push origin HEAD:main',
            'SAIRN_SEED_GATE=off git push origin main',
            'git fetch origin -q && git push origin main',
            'git add -A; git commit -m wip; git push',
            'git rebase origin/main 2>&1 | tail -5 && git push origin main 2>&1 | tail -5'):
    was_run, code, _, locked = ran(payload(cmd))
    check('%-46s runs the suite, having taken the lock' % ('`%s`' % cmd[:44]),
          (was_run, code, locked), (True, 0, True))

print('3. a payload with no command at all is treated as not-a-push')
check('empty tool_input does not run the suite',
      ran(json.dumps({'tool_name': 'Bash', 'tool_input': {}}))[0], False)
check('no tool_input key does not run the suite',
      ran(json.dumps({'tool_name': 'Bash'}))[0], False)

print('4. an UNREADABLE payload fails OPEN and runs -- a decision, not an accident')
# Report-only tooling in this repo fails open on its own errors (the same
# standard as the push-gate hooks), and `python tools/run_all_tests.py --hook`
# typed by hand has no payload at all. Both land here. Stated explicitly so it
# is a choice on the record: if a future payload shape stops parsing, this hook
# goes back to running on every Bash call, and this line is where to look.
check('no stdin at all runs the suite', ran('')[0], True)
check('malformed stdin runs the suite', ran('not json')[0], True)

print('4b. A DENIED PUSH IS NOT A PUSH')
# PostToolUse fires whether or not the command succeeded. The command gate
# above was necessary and not sufficient: every push the PRE-tool push gate
# refused still launched the whole suite, which then commits fixtures on
# `main` and dirties the tree -- so the denial that was meant to protect the
# branch is what dirtied it, and the next attempt raced the probe commit and
# was denied again. Observed 2026-09-10: two concurrent runs at 09:28 and
# 09:32 with no successful push between them.
def with_response(cmd, success):
    return json.dumps({'hook_event_name': 'PostToolUse', 'tool_name': 'Bash',
                       'tool_input': {'command': cmd},
                       'tool_response': {'success': success, 'stdout': '', 'stderr': ''}})


check('a push whose tool_response says success=false does not run the suite',
      ran(with_response('git push origin main', False))[0], False)
check('a push whose tool_response says success=true DOES run it',
      ran(with_response('git push origin main', True))[0], True)
check('a push with no tool_response at all still runs it (fail-open)',
      ran(payload('git push origin main'))[0], True)
check('and a non-push with success=true is still not a push',
      ran(with_response('git status', True))[0], False)

print('5. the gate reads the command, not the tool name')
# A non-Bash tool cannot have pushed anything. Nothing else in the payload
# should be able to satisfy the gate.
check('a Write payload does not run the suite',
      ran(json.dumps({'tool_name': 'Write',
                      'tool_input': {'file_path': 'git push notes.md'}}))[0], False)

print('6. the BINARY itself, because an import is not what runs unattended')
# The half the 2026-09-04 hook fix missed: `tools/sairn_claim_hook.py` kept its
# own copy of a defect that had been fixed in the tool a human invokes. So this
# executes the real file the way settings.json does.
t0 = time.time()
p = subprocess.run([sys.executable, os.path.join(REPO, 'tools', 'run_all_tests.py'),
                    '--hook'],
                   input=payload('git status'), capture_output=True, text=True,
                   cwd=REPO, timeout=120)
elapsed = time.time() - t0
check('the binary exits 0 on a non-push payload', p.returncode, 0)
check('the binary prints nothing on a non-push payload', p.stdout.strip(), '')
# The suite is minutes of work; returning in seconds is proof it did not start.
check('the binary returns without running the suite (< 20s)', elapsed < 20, True)

print('6b. THE SECOND COPY -- report_only_checks.py carries the same two gates')
# tools/sairn_claim_hook.py taught this on 2026-09-04: a fix verified on the
# copy a human invokes is not verified for the one that runs unattended. Both
# of these are PostToolUse Bash hooks in the same settings block.
_roc = io.open(os.path.join(REPO, 'tools', 'report_only_checks.py'), encoding='utf-8').read()
check('it imports the same push matcher rather than keeping its own',
      'pushes(' in _roc, True)
check('it declines a denied push too',
      "get('success') is False" in _roc, True)

print('7. `.claude/settings.json` must not carry an `if` on a hook again')
# The field that never existed. It read as a gate to three sessions.
cfg = json.load(io.open(os.path.join(REPO, '.claude', 'settings.json'), encoding='utf-8'))
stray = []
for event, groups in (cfg.get('hooks') or {}).items():
    for group in groups:
        for entry in (group.get('hooks') or []):
            for key in entry:
                if key not in ('type', 'command', 'timeout', 'statusMessage',
                               'async', 'asyncRewake'):
                    stray.append('%s: %s -> %r' % (event, entry.get('command', '?'), key))
check('no unrecognised keys on any hook entry', stray, [])

print()
if fails:
    print('%d FAILED' % fails)
    sys.exit(1)
print('ALL PASS -- the suite hook runs on a push and on nothing else.')
