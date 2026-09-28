#!/usr/bin/env python3
"""PreToolUse shim: run the conflict pre-flight ONLY while an operation is in
progress, because the full pass costs 7 seconds and a Bash hook fires on every
command.

    python tools/conflict_marker_preflight_hook.py      # wired; reads nothing

Exit 0 always. This is a WARNING channel, not a gate -- see below.

── WHY A SHIM AND NOT THE TOOL ITSELF ─────────────────────────────────────
`tools/conflict_marker_preflight.py` is the real check and it is EXCELLENT: its
check A delegates markers to `conflict_marker_check.py` rather than
reimplementing them, check B is a structural parse, and check C is the one that
catches the shape with NO markers at all -- a blind `--ours`/`--theirs` that
resolves cleanly, parses cleanly, passes the push gate, and silently discards
another session's work.

MEASURED 2026-09-28: 7.10 seconds over 2,670 paths. That is the right cost for
the moment it is built for and the wrong cost for every other moment. A
PreToolUse hook on Bash fires on EVERY command, and `.githooks/pre-commit`
already records the consequence in its own words: "a pre-commit hook that costs
real time on every commit is one somebody eventually turns off." Seven seconds
per Bash call would be turned off within the hour, and a check that is switched
off checks nothing.

THE TOOL IS NOT EDITED TO ADD THE EARLY EXIT, and that is a claim boundary
rather than a design preference: `tools/conflict_marker_preflight.py` is named
in fourth's active claim (they are adding an ORIG_HEAD..HEAD post-operation
mode to it). Reaching into a file another session holds to add a guard is the
thing PR 4.3 exists to stop, so the guard lives beside it.

Same shape as `tools/hover_self_health_shim.py`, which is the standing
precedent for "a hook that is a deliberate no-op except in the one state it is
for".

── THE CHEAP TEST COMES FIRST, DELIBERATELY ───────────────────────────────
Four filesystem stats against `.git/`. No subprocess, no import of the pre-flight
module, no repo walk. In the overwhelmingly common case this costs less than a
millisecond and returns.

── IT WARNS AND DOES NOT DENY, AND THAT IS A DECISION ─────────────────────
A mid-rebase state is a NORMAL state -- `git status`, `git diff`, `git add` of a
resolved file are all things a person legitimately runs there. Denying Bash
during a rebase would make the tool that helps you finish a rebase unusable
inside one, which is the failure mode where somebody disables the hook and
loses check C entirely.

So: exit 0 always, and print. The push gate still refuses a marker at the end.
What this adds is the pre-flight being SEEN at the moment it is cheap to act on,
which is the whole argument for the tool existing separately from the gate.

NON-ZERO FROM THE PRE-FLIGHT IS REPORTED, NEVER SWALLOWED. Exit 1 (found
something) and exit 2 (could not run) are printed with their own text and kept
apart -- folding "could not run" into silence is the defect this platform names
most often (PR 1.11).
"""
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(REPO, 'tools', 'conflict_marker_preflight.py')


def git_dir():
    """The real .git directory, or None. Resolved rather than assumed: a
    worktree's .git is a FILE pointing elsewhere, and the probes in this repo
    build throwaway worktrees constantly."""
    try:
        r = subprocess.run(['git', '-C', REPO, 'rev-parse', '--git-dir'],
                           capture_output=True, text=True, encoding='utf-8',
                           errors='replace', timeout=10)
    except Exception:
        return None
    if r.returncode != 0:
        return None
    d = (r.stdout or '').strip()
    if not d:
        return None
    return d if os.path.isabs(d) else os.path.join(REPO, d)


def operation_in_progress(gd):
    """Which operation, or None. The four markers git actually writes."""
    if not gd:
        return None
    for d in ('rebase-merge', 'rebase-apply'):
        if os.path.isdir(os.path.join(gd, d)):
            return 'rebase'
    for f, kind in (('MERGE_HEAD', 'merge'),
                    ('CHERRY_PICK_HEAD', 'cherry-pick'),
                    ('REVERT_HEAD', 'revert')):
        if os.path.isfile(os.path.join(gd, f)):
            return kind
    return None


def main():
    gd = git_dir()
    if gd is None:
        # COULD NOT TELL is not silence. It is one line, because a hook that
        # printed a paragraph on every Bash call in a non-repo directory would
        # itself become noise.
        print('conflict pre-flight: could not resolve the git directory, so it '
              'is NOT known whether an operation is in progress. Nothing was '
              'checked.', file=sys.stderr)
        return 0
    op = operation_in_progress(gd)
    if op is None:
        return 0
    if not os.path.isfile(TOOL):
        print('conflict pre-flight: a %s is in progress and '
              'tools/conflict_marker_preflight.py is MISSING, so the '
              'pre-flight did NOT run. This is not a clean state, it is an '
              'unchecked one.' % op, file=sys.stderr)
        return 0
    try:
        r = subprocess.run([sys.executable, TOOL], cwd=REPO, capture_output=True,
                           text=True, encoding='utf-8', errors='replace',
                           timeout=180)
    except Exception as exc:
        print('conflict pre-flight: a %s is in progress and the pre-flight '
              'could not be launched (%s). NOTHING WAS CHECKED.'
              % (op, type(exc).__name__), file=sys.stderr)
        return 0
    if r.returncode == 0:
        print('conflict pre-flight (%s in progress): CLEAN.' % op, file=sys.stderr)
        return 0
    head = '=' * 70
    if r.returncode == 2:
        print('%s\nCONFLICT PRE-FLIGHT COULD NOT RUN during a %s -- that is a '
              'THIRD STATE and not a pass. Nothing below was verified.\n%s'
              % (head, op, head), file=sys.stderr)
    else:
        print('%s\nCONFLICT PRE-FLIGHT FOUND SOMETHING during a %s. This is the '
              'cheap moment to fix it: nothing has been rewritten yet, the\n'
              'conflict is still in front of you, and `git reset` costs '
              'nothing. After `%s --continue` it is in a commit.\n%s'
              % (head, op, op, head), file=sys.stderr)
    out = (r.stdout or '') + (r.stderr or '')
    for line in out.splitlines()[-40:]:
        print('  ' + line, file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
