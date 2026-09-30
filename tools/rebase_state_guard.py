"""PreToolUse hook for Bash: history-rewriting commands are refused in the two
states where they destroy somebody else's work.

    python tools/rebase_state_guard.py      # wired; reads the payload on stdin

Exit is ALWAYS 0. The decision travels in the JSON body, which is what Claude
Code reads; a non-zero exit from a PreToolUse hook is a hook failure, not a
denial.

── WHY THIS IS MECHANICAL AND NOT A PARAGRAPH ──────────────────────────────
"Never amend a pushed commit" was already written down twice -- in CLAUDE.md and
in `docs/SAIRN-PROCESS-RULES.md` PR 2.4. On 2026-09-27 the session that wrote it
amended onto another session's commit anyway, mid-rebase, and the commit was
gone. A rule that lives only in prose is enforced by whoever remembers it at the
moment they are in a hurry, and that is precisely the moment nobody does. This
file is that rule with a gate under it.

── WHAT IT REFUSES ─────────────────────────────────────────────────────────
1. WHILE A REBASE, MERGE OR CHERRY-PICK IS IN PROGRESS -- all four of:
       git commit --amend
       git add -A   /   git add --all
       git add .
       git commit -a   (including clustered, e.g. -am)
   Mid-operation the index holds a half-finished state that git is going to
   reuse. `git add -A` there stages another session's conflicted hunks as
   though they were yours, and `--amend` rewrites the commit the operation is
   replaying onto. Both produce a clean-looking result that silently discards
   work, which is the worst available failure: nothing on screen says so.

2. ALWAYS -- `git commit --amend` when HEAD is already an ancestor of
   `refs/remotes/origin/main`, i.e. the commit has been published. Amending it
   rewrites history four other clones have already pulled.

── WHAT IT DELIBERATELY DOES NOT REFUSE, so no reader mistakes it for a miss ─
* BLANKET STAGING OUTSIDE AN OPERATION. `git add -A` on a clean tree is not
  refused here. That is a real discipline and it is a DIFFERENT rule with a
  different owner -- fourth's staging-discipline work replaces blanket staging
  inside this repo's own tooling and adds a staged-content credential check.
  Widening this guard to cover it silently would be a rule nobody agreed, and
  the two would then disagree about what the rule is.
* `git add -u`, `git add :/`, `git add *`. Each is blanket-ish and none is in
  the stated rule. Named here rather than quietly included.
* `git stash`, `git reset --hard`, `git rebase -i`, `git push --force`. All
  destructive, none in this rule. `--force` to `master` is already covered by
  `tools/git_push_master_guard.py`.
* A command that changes directory first. The operation state is read from THIS
  repository, the one the hook lives in. A `cd /other/repo && git commit
  --amend` is judged against this repo's state, which is the same boundary
  `tools/conflict_marker_preflight_hook.py` draws and for the same reason: the
  alternative is parsing shell semantics on the PreToolUse path.

── NO OVERRIDE, AND THAT IS THE DECISION ───────────────────────────────────
The push gate has `SAIRN_SEED_GATE=off` because a seed can legitimately be
ahead of live. There is no equivalent legitimate case here: if HEAD is
published, the fix is a new commit, and if an operation is in progress the fix
is to finish or abort it. An escape hatch with no stated reason "does not
produce honesty, it produces a field that means nothing" -- the defect
register's own words about `not-citable` -- and this rule already failed once as
an honour system.

── FAIL OPEN ON A HOOK BUG, FAIL CLOSED ON AN UNANSWERABLE QUESTION ────────
Two different failures and they get opposite treatment, deliberately.

A crash, an unreadable payload, a missing git: FAIL OPEN. A PreToolUse hook that
throws blocks every Bash call in the session, so a bug here would brick the
shell, be switched off within the hour, and then guard nothing. Same standard as
`redaction_check.py` and `git_push_master_guard.py`.

"Is HEAD published?" coming back UNKNOWN: FAIL CLOSED. That is not a hook bug,
it is the exact question the rule turns on, and answering "probably fine" about
rewriting published history is how the incident happened. The refusal says it
could not tell, so it reads as a third state rather than a verdict (PR 1.11).
"""
import json
import os
import posixpath
import re
import shlex
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Split on the raw string BEFORE shlex, exactly as git_push_master_guard.py
# does: shlex separates on whitespace only, so `git add -A;echo hi` comes back
# with `-A;echo` as one token and compares unequal to `-A`. That is a HOLE, not
# a false positive, and a hole is the one direction this guard must not move in.
SEPARATOR_RE = re.compile(r'&&|\|\||[;\n|&]')

# git's global options that take a SEPARATE value, so the subcommand after them
# is still found. `--git-dir=x` style carries its value inline and needs no
# entry. This is the hole the push-master guard had and it is closed here from
# the start rather than after an incident.
GIT_VALUE_OPTS = ('-C', '-c', '--git-dir', '--work-tree', '--namespace',
                  '--exec-path', '--super-prefix')

AMEND = 'commit --amend'
ADD_ALL = 'add -A / --all'
ADD_DOT = 'add .'
COMMIT_ALL = 'commit -a'

# The narrow fallback for a segment shlex cannot read. Deliberately anchored on
# `git` immediately followed by the subcommand and the flag, rather than the
# `.*` span that made the push-master guard deny its own commit message three
# times in one session.
UNPARSEABLE_RE = re.compile(
    r'\bgit\b(?:\s+-\S+)*\s+(?:commit\s+--amend\b|add\s+(?:-A\b|--all\b|\.(?:\s|$)))')


def _git_subcommand_args(tokens):
    """(subcommand, args) for a `git [global-opts] <sub> ...` invocation.

    (None, None) when this segment is not a git invocation at all.
    """
    if not tokens:
        return None, None
    head = posixpath.basename(tokens[0].replace('\\', '/')).lower()
    if head not in ('git', 'git.exe'):
        return None, None
    i = 1
    while i < len(tokens) and tokens[i].startswith('-'):
        opt = tokens[i]
        i += 1
        if opt in GIT_VALUE_OPTS and i < len(tokens):
            i += 1
    if i >= len(tokens):
        return None, None
    return tokens[i], tokens[i + 1:]


def _has_short_flag(args, letter):
    """A short option, whether alone (`-a`) or clustered (`-am`, `-sam`).

    A scan for the exact token is what misses `git commit -am "wip"`, which is
    how most people write it.
    """
    for a in args:
        if a == '--':
            return False
        if not a.startswith('-') or a.startswith('--'):
            continue
        if letter in a[1:]:
            return True
    return False


def _has_long_flag(args, name):
    for a in args:
        if a == '--':
            return False
        if a == name or a.startswith(name + '='):
            return True
    return False


def _stages_everything(args):
    """`git add` with a blanket target: -A, --all, or the bare dot.

    ONLY the bare `.`. `git add ./docs/x.md` is an explicit path and a prefix
    test would refuse it -- and then the guard would be in the way of the normal
    work of resolving a conflict, which is how a guard gets switched off.
    Everything after `--` is a pathspec, including a file named `-A`.
    """
    if _has_short_flag(args, 'A') or _has_long_flag(args, '--all'):
        return ADD_ALL
    seen_ddash = False
    for a in args:
        if a == '--':
            seen_ddash = True
            continue
        if not seen_ddash and a == '.':
            return ADD_DOT
    return None


def forbidden_forms(cmd):
    """Which forbidden forms this command line actually INVOKES.

    A form quoted inside a commit message is data, not an invocation, and is not
    returned -- shlex keeps a quoted message as one token so `-A` inside it is
    never a bare flag. That distinction is the whole reason this parses rather
    than greps: the push-master guard's `.*` version denied the very commit that
    documented it.
    """
    found = []
    for piece in SEPARATOR_RE.split(cmd or ''):
        if not piece.strip():
            continue
        try:
            tokens = shlex.split(piece, posix=True)
        except ValueError:
            # Unbalanced quotes, usually because the separator split landed
            # inside a quoted string. A parse failure must not become a hole.
            if UNPARSEABLE_RE.search(piece):
                found.append('an unparseable command line naming a forbidden '
                             'form')
            continue
        sub, args = _git_subcommand_args(tokens)
        if sub is None:
            continue
        if sub == 'commit':
            if _has_long_flag(args, '--amend'):
                found.append(AMEND)
            if _has_short_flag(args, 'a') or _has_long_flag(args, '--all'):
                found.append(COMMIT_ALL)
        elif sub == 'add':
            form = _stages_everything(args)
            if form:
                found.append(form)
    # Order-stable dedup: the message lists what it found and a repeat reads as
    # two separate problems.
    out = []
    for f in found:
        if f not in out:
            out.append(f)
    return out


def git_dir(repo=None):
    """The real .git directory, or None.

    RESOLVED rather than assumed. A worktree's `.git` is a FILE pointing
    elsewhere and this repo's probes build throwaway worktrees constantly, so
    `os.path.join(repo, '.git')` would be wrong in exactly the situation where a
    rebase is most likely to be running.
    """
    try:
        r = subprocess.run(['git', '-C', repo or REPO, 'rev-parse', '--git-dir'],
                           capture_output=True, text=True, encoding='utf-8',
                           errors='replace', timeout=10)
    except Exception:
        return None
    if r.returncode != 0:
        return None
    d = (r.stdout or '').strip()
    if not d:
        return None
    return d if os.path.isabs(d) else os.path.join(repo or REPO, d)


# ── THE THIRD STATE FOR THE *OPERATION* QUESTION (added 2026-09-30) ─────────
# `git_dir()` returns None for a missing git, a non-zero rev-parse, an exception
# OR A 10-SECOND TIMEOUT, and `operation_in_progress(None)` used to return the
# same None it returns for "nothing is running". For `git add -A`, `git add .`
# and `git commit -am x` there is no second question to fall through to, so
# decide() returned (False, '') and the command was ALLOWED -- a blanket stage
# into a live stopped rebase, silently, which is the 2026-09-27 incident this
# file was written for.
#
# FOUND BY REVIEW AND DRIVEN, NOT ARGUED: a real repository, a real conflicting
# rebase stopped on disk, all four forms correctly refused -- and then the same
# call with the op value a failed git_dir() produces came back deny=False for
# three of them.
#
# THE HEADER ALREADY DECIDED THIS. It says a hook bug fails OPEN and an
# unanswerable question fails CLOSED, and there are TWO questions. "Is HEAD
# published?" got the three-state treatment from the start; "is an operation in
# progress?" did not. Same paragraph, same argument, second question.
#
# THE TIMEOUT IS THE REALISTIC TRIGGER, not a missing git. Five clones push to
# one branch on this machine and single git invocations have exceeded 120
# seconds; a 10s timeout on `rev-parse --git-dir` under that load is ordinary,
# and it is most likely exactly when a rebase is stopped.
UNKNOWN = 'unknown'


def operation_in_progress(gd):
    """Which operation is stopped, None when none is, UNKNOWN when it cannot tell.

    THREE STATES, and the third is the fix. `gd` is None whenever git_dir()
    could not answer, and that is NOT evidence that no operation is running --
    it is the absence of evidence either way. Returning None there made a
    failed lookup indistinguishable from a clean tree.

    `revert` is included even though the stated rule names three: it stops in
    the same place, the same commands do the same damage there, and leaving it
    out would be a gap with no reason behind it.
    """
    if not gd:
        return UNKNOWN
    for d in ('rebase-merge', 'rebase-apply'):
        if os.path.isdir(os.path.join(gd, d)):
            return 'rebase'
    for f, kind in (('MERGE_HEAD', 'merge'),
                    ('CHERRY_PICK_HEAD', 'cherry-pick'),
                    ('REVERT_HEAD', 'revert')):
        if os.path.isfile(os.path.join(gd, f)):
            return kind
    return None


def head_on_origin_main(repo=None):
    """True if HEAD is already published, False if not, None if NOT KNOWN.

    Three states on purpose. `--is-ancestor` exits 0 for yes and 1 for no, and
    ANY other outcome -- no such ref, no git, a timeout -- is None rather than
    False. Reading "I could not check" as "not published" would allow exactly
    the rewrite this guard exists to stop.
    """
    try:
        r = subprocess.run(['git', '-C', repo or REPO, 'merge-base',
                            '--is-ancestor', 'HEAD', 'refs/remotes/origin/main'],
                           capture_output=True, text=True, encoding='utf-8',
                           errors='replace', timeout=15)
    except Exception:
        return None
    if r.returncode == 0:
        return True
    if r.returncode == 1:
        return False
    return None


def decide(cmd, op, head_pushed):
    """(deny, reason). Pure: every input is passed in, nothing is read here.

    That is what lets the control drive the mid-rebase arm against a REAL
    stopped rebase in a throwaway repository instead of against a directory
    with files named like one.
    """
    forms = forbidden_forms(cmd)
    if not forms:
        return False, ''

    # ── COULD NOT TELL WHETHER AN OPERATION IS RUNNING: REFUSE ──────────────
    # Checked BEFORE the `if op:` branch, because UNKNOWN is truthy and would
    # otherwise be formatted into the message as though it were an operation
    # named "unknown" -- a refusal for the right reason with the wrong sentence,
    # which is how a guard gets read as broken.
    if op == UNKNOWN:
        return True, (
            'Blocked: it is NOT KNOWN whether a rebase, merge, cherry-pick or '
            'revert is in progress, so this command was not judged -- it was '
            'refused.\n\n'
            'Reading the repository state failed: `git rev-parse --git-dir` did '
            'not answer, which on this machine is most often a TIMEOUT under '
            'load rather than a broken repository. That is a THIRD STATE, not a '
            'pass. Mid-operation %s stages another session\'s conflicted hunks '
            'as if they were yours, or rewrites the commit being replayed onto, '
            'and both succeed silently.\n\n'
            'Re-run the command -- a timeout usually clears. If it does not, '
            'check `git status` by hand and stage the files you have resolved by '
            'name: `git add <path>`.'
            % (' and '.join(forms)))

    if op:
        return True, (
            'Blocked: a %s is IN PROGRESS and this command uses %s.\n\n'
            'Mid-%s the index holds a half-finished state git is about to '
            'reuse. A blanket stage there commits another session\'s '
            'conflicted hunks as if they were yours, and --amend rewrites the '
            'commit being replayed onto. Both succeed silently and both lose '
            'work.\n\n'
            'Finish or abandon the operation first: `git %s --continue` or '
            '`git %s --abort`. To stage a file you have resolved, name it: '
            '`git add <path>`.'
            % (op, ' and '.join(forms), op, op, op))

    if AMEND in forms:
        if head_pushed is True:
            return True, (
                'Blocked: --amend would rewrite a commit that is ALREADY ON '
                'origin/main.\n\n'
                'HEAD is an ancestor of refs/remotes/origin/main, so four '
                'other clones have it. Amending it rewrites history they have '
                'pulled. This rule was prose in CLAUDE.md and PR 2.4 and was '
                'broken anyway on 2026-09-27, which is why it is a gate.\n\n'
                'Make a new commit instead.')
        if head_pushed is None:
            return True, (
                'Blocked: it is NOT KNOWN whether HEAD is already on '
                'origin/main, so this --amend was not judged -- it was '
                'refused.\n\n'
                '`git merge-base --is-ancestor HEAD refs/remotes/origin/main` '
                'did not answer. That is a THIRD STATE, not a pass: reading '
                '"could not check" as "not published" would allow the one '
                'rewrite this guard exists to stop.\n\n'
                'Run `git fetch origin` and try again, or make a new commit.')

    return False, ''


def main():
    payload = json.load(sys.stdin)
    cmd = (payload.get('tool_input', {}) or {}).get('command', '') or ''

    # THE CHEAP TEST FIRST. A Bash PreToolUse hook fires on every command, so
    # the common path must not spawn git. Nothing below runs unless the command
    # actually invokes one of the four forms.
    forms = forbidden_forms(cmd)
    if not forms:
        sys.exit(0)

    gd = git_dir()
    op = operation_in_progress(gd)
    head_pushed = head_on_origin_main() if (AMEND in forms and not op) else False

    deny, reason = decide(cmd, op, head_pushed)
    if deny:
        print(json.dumps({
            'hookSpecificOutput': {
                'hookEventName': 'PreToolUse',
                'permissionDecision': 'deny',
                'permissionDecisionReason': reason,
            }
        }))
    sys.exit(0)


if __name__ == '__main__':
    try:
        main()
    except Exception:
        # FAIL OPEN on a hook bug -- never let this block a legitimate command.
        # The opposite choice is made for an unanswerable question inside
        # decide(); see the header for why the two differ.
        sys.exit(0)
