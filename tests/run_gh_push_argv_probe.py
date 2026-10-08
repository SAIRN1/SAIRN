#!/usr/bin/env python
# OWNER: cc
"""A bare run of a tool that PUSHES must REFUSE, not crash -- and push nothing.

    python tests/run_gh_push_argv_probe.py

Exit 0 all arms pass, 1 an arm failed, 2 COULD NOT RUN.

THE DEFECT, MEASURED 2026-10-07 BEFORE THE FIX. `commit_message = sys.argv[1]` was
the FIRST statement in tools/gh_push.py's main(), so a bare run raised

    IndexError: list index out of range   at tools/gh_push.py:182

THIS TOOL PUSHES TO GITHUB OVER THE REST API. The crash happened to occur before
the first network write, so nothing was sent -- `git ls-remote origin` captured
before and after a bare run was BYTE-IDENTICAL at 63 refs. But that outcome was
luck, not design: nothing in the code said the ordering mattered, and any later edit
that moved one line above it would have turned a typo-shaped mistake into a push of
HEAD with a traceback for a commit message.

So the guard is not "stop a crash". It is to make the safe outcome DELIBERATE and
to keep it that way, and to deliver COULD NOT RUN (exit 2) rather than a finding
(exit 1) for a missing argument.

WHY THIS PROBE NEVER RUNS THE TOOL WITH ARGUMENTS. A single real invocation would
attempt an actual push to SAIRN1/SAIRN. Every arm here drives ONLY the refusal
paths, in a subprocess, and asserts the remote is untouched by comparing
`git ls-remote origin` before and after. There is no arm for the success path and
that is a deliberate limit, not an oversight -- see below.

WHAT THIS PROBE CANNOT SEE, stated rather than discovered later:
  * THE PUSH PATH ITSELF. Nothing here proves a real push works, or that the gate
    is invoked before the first blob upload. That needs a real push and belongs to
    a human doing one deliberately.
  * whether the ordering inside main() still puts the gate before the network. The
    guard makes a BARE run safe; it says nothing about argument-bearing runs.
  * a network failure mid-push. Out of scope entirely.
"""
import io
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(ROOT, 'tools', 'gh_push.py')

if not os.path.isfile(TOOL):
    print('COULD NOT RUN -- %s is absent. This probe is about that file and '
          'reports nothing without it.' % TOOL)
    sys.exit(2)


def ls_remote():
    """The remote's refs, or None if it could not be read.

    A COULD-NOT-READ is NOT treated as 'unchanged': if the remote cannot be
    reached, this probe cannot prove anything about whether it changed, and
    saying so is the point.
    """
    p = subprocess.run(['git', 'ls-remote', 'origin'], cwd=ROOT,
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace')
    return p.stdout if p.returncode == 0 else None


def run(args):
    p = subprocess.run([sys.executable, TOOL] + args, cwd=ROOT,
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace')
    return p.returncode, (p.stdout or '') + (p.stderr or '')


before = ls_remote()
if before is None:
    print('COULD NOT RUN -- `git ls-remote origin` failed, so the "pushed '
          'nothing" arms cannot be evidence. Not reporting clean on an '
          'unreadable remote.')
    sys.exit(2)

arms = []

# ── ARM 1: a BARE run refuses with 2 and says COULD NOT RUN ────────────────
rc, out = run([])
arms.append(('a BARE run exits 2, not 1 and not a traceback',
             rc, 2))
arms.append(('...and says COULD NOT RUN rather than printing a stack',
             ('COULD NOT RUN' in out, 'Traceback' in out, 'IndexError' in out),
             (True, False, False)))
arms.append(('...and states that nothing was sent',
             'Nothing was sent' in out, True))
arms.append(('...and prints the usage so the reader knows what was missing',
             'python tools/gh_push.py' in out, True))

# ── ARM 2: AN EMPTY MESSAGE IS THE SAME REFUSAL ────────────────────────────
# This is the arm that matters more than the bare run. `gh_push.py ""` PASSES a
# len(sys.argv) guard and would have committed with no subject at all -- which is
# worse than a crash, because it succeeds.
rc, out = run([''])
arms.append(('an EMPTY commit message is refused too, with 2',
             (rc, 'COULD NOT RUN' in out), (2, True)))

# ── ARM 3: a whitespace-only message is also refused ───────────────────────
rc, out = run(['   '])
arms.append(('a WHITESPACE-ONLY message is refused',
             (rc, 'COULD NOT RUN' in out), (2, True)))

# ── ARM 4: THE REMOTE IS UNTOUCHED BY ALL OF THE ABOVE ────────────────────
after = ls_remote()
arms.append(('the remote is readable after the refusals (so the comparison '
             'below means something)', after is not None, True))
arms.append(('THE REMOTE IS BYTE-IDENTICAL after every refusal -- nothing was '
             'pushed', after == before, True))

# ── ARM 5: the refusal reaches the SHELL, not just the screen ─────────────
# A verdict computed and not delivered is this repo's most-paid-for defect:
# gen_ma_seed.py printed DRIFTED while exiting 0. `main()` alone discards its
# return value, so this asserts the entry point forwards it.
src = io.open(TOOL, encoding='utf-8', errors='replace').read()
arms.append(('the entry point FORWARDS main()\'s return value to sys.exit',
             'sys.exit(main()' in src, True))

passed = 0
for name, got, want in arms:
    ok = got == want
    passed += ok
    print('  %-4s %s' % ('PASS' if ok else 'FAIL', name))
    if not ok:
        print('       wanted %r' % (want,))
        print('       got    %r' % (got,))
print('gh_push argv probe: %d/%d arm(s) pass  (remote refs seen: %d)'
      % (passed, len(arms), len([l for l in before.split(chr(10)) if l.strip()])))
sys.exit(0 if passed == len(arms) else 1)
