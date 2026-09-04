"""
PreToolUse hook for Bash. Reads the hook payload on stdin (the same
mechanism redaction_check.py uses -- confirmed working all session) and
blocks (permissionDecision: deny) a command that pushes to the stale
`master` branch. Repo default is `main` -- see CLAUDE.md.

Root cause of the original "PreToolUse:Bash hook error" traceback:
the old version of this hook relied on a $CLAUDE_TOOL_INPUT environment
variable substituted into `echo "$CLAUDE_TOOL_INPUT" | python -c "..."`.
Empirically confirmed (2026-07-28) that an empty/unset variable piped into
json.load(sys.stdin) throws an uncaught JSONDecodeError -- exactly the
traceback symptom -- and there is no confirmed evidence Claude Code
actually populates that env var for hooks (the sibling PostToolUse hook's
identically-shaped $CLAUDE_TOOL_INPUT_FILE_PATH reference never visibly
fired all session despite dozens of .html edits, consistent with it also
being unset). Switched to reading stdin directly, the one mechanism
already proven to work, and wrapped in try/except to fail open -- same
standard as redaction_check.py: never let a hook bug block or crash-
visibly on a legitimate command.

── THE FALSE POSITIVE THIS FILE USED TO HAVE (fixed 2026-09-04) ───────────
The test was one line:

    re.search(r'git push.*master', cmd)

`.*` spans the WHOLE command string, so the word `master` anywhere after a
push invocation tripped it -- in an unrelated argument, a path, or a commit
message. Reproduced three times by accident rather than theorised (found
2026-09-04 by Hank while pipe-testing the repointed hooks):

  * a diagnostic that pushed to `HEAD:main` and separately named the file
    `git_push_master_guard.py` was DENIED, the only occurrence of the word
    being this script's own filename;
  * the command that first tried to ADD the open-work row for it was denied,
    because the row text quotes both halves of the pattern;
  * the COMMIT of that row was denied too, because the commit message did.

The direction always mattered and still does: this guard could only ever be
talked into REFUSING something harmless, never into ALLOWING a push to the
stale branch. That is why it was left alone rather than patched inside an
unrelated change, and it is the property the rewrite below has to keep.

── WHAT IT MATCHES NOW: THE DESTINATION REF, NOT THE LINE ─────────────────
The command is split on shell separators, each segment is checked for a
`git ... push` invocation, and only the DESTINATION half of that
invocation's refspecs is compared against `master`. Same parsing idea as
sairn_push_gate_hook.pushed_tip(), which reads the SOURCE half of the same
refspec for the same reason.

Denied (each verified in tests/run_push_master_guard_probe.py):

    git push origin master
    git push origin HEAD:master
    git push -u origin master
    git push --force origin +HEAD:master
    git push origin refs/heads/master
    git push origin :master              # deleting it is still touching it
    git push origin --delete master
    git -C /some/repo push origin master # `git -C` slipped the old regex too
    git push origin main && git push origin master   # second segment

Allowed (each of these was DENIED before):

    git push origin main && cat tools/git_push_master_guard.py
    git push origin HEAD:main -o "note mentioning master"
    git add docs/master-plan.md && git push origin main
    git push origin master-of-none:main   # a branch merely NAMED like it
    git push origin archive/master        # a different branch entirely

DELIBERATE BOUNDARIES, so a later reader does not mistake them for misses:

  * A bare `git push` with no refspec is NOT inspected. Resolving it means
    asking git which branch is checked out and what its upstream is, i.e. a
    subprocess on the PreToolUse path. The repo default is `main` and every
    clone tracks it, so the realistic exposure is small; closing it is a
    separate change with its own cost, not a silent extra in this one.
  * The SOURCE half is not checked. `git push origin master:main` is allowed.
    This guard's stated job, in its own denial message, is pushes TO master.
    Widening it to the source is a different rule and needs its own decision.
  * `archive/master` and similar are allowed on purpose: only `master`, or a
    fully-qualified `refs/heads/master`, is the stale branch.

── WHY THE UNPARSEABLE CASE FALLS BACK TO THE OLD BLUNT TEST ──────────────
shlex raises on unbalanced quotes. Falling through to "allow" there would
convert a parse failure into a hole, which is the one direction this guard
must never move in. So a command shlex cannot read is checked with the old
substring rule instead -- over-refusing a pathological command line is the
outcome this file has always been willing to have.
"""
import sys, re, json, shlex, posixpath

# Split on the raw string BEFORE shlex, not on shlex's token list: shlex only
# separates on whitespace, so `git push origin master;echo hi` would come back
# as the single token `master;echo` and compare unequal to `master`. That is a
# HOLE rather than a false positive, i.e. the one direction this guard is not
# allowed to move in, so the separator split has to happen on the text.
SEPARATOR_RE = re.compile(r'&&|\|\||[;\n|&]')

# git's own global options, before the subcommand. Only the ones that take a
# SEPARATE value need naming; `--git-dir=x` style carries its value inline.
GIT_VALUE_OPTS = ('-C', '-c', '--git-dir', '--work-tree', '--namespace',
                  '--exec-path', '--super-prefix')

# `git push` options that consume the NEXT argument, which must therefore not
# be mistaken for a refspec. DELIBERATELY SHORT. `--force-with-lease` and
# `--force-if-includes` are NOT here: they take an optional value with `=`, so
# listing them would make this skip the following token -- and in
# `git push --force-with-lease origin master` that token is the remote, which
# would leave `master` unread and the push ALLOWED. An over-long list here
# opens holes; an over-short one only risks reading an option value as a ref,
# which over-refuses.
PUSH_VALUE_OPTS = ('-o', '--push-option', '--repo')


def _push_args(tokens):
    """Args of a `git [global-opts] push` invocation in this segment, or None."""
    if not tokens:
        return None
    head = posixpath.basename(tokens[0].replace('\\', '/')).lower()
    if head not in ('git', 'git.exe'):
        return None
    i = 1
    while i < len(tokens) and tokens[i].startswith('-'):
        opt = tokens[i]
        i += 1
        if opt in GIT_VALUE_OPTS and i < len(tokens):
            i += 1
    if i < len(tokens) and tokens[i] == 'push':
        return tokens[i + 1:]
    return None


def _destination_refs(args):
    """The refs a push would WRITE TO. Empty when the command names none."""
    positional, i = [], 0
    while i < len(args):
        a = args[i]
        if a == '--':
            positional.extend(args[i + 1:])
            break
        if a.startswith('-'):
            if a in PUSH_VALUE_OPTS:
                i += 1
            i += 1
            continue
        positional.append(a)
        i += 1
    # First positional is the remote; a lone argument is a remote, not a ref --
    # the same reading pushed_tip() uses.
    specs = positional[1:] if positional else []
    dsts = []
    for spec in specs:
        spec = spec.lstrip('+')
        # `src:dst` writes to dst; `:dst` deletes dst; a bare ref writes to the
        # ref of that name (and is also what `--delete <ref>` names).
        dsts.append(spec.split(':', 1)[1] if ':' in spec else spec)
    return dsts


def _is_master(ref):
    r = ref.strip()
    for prefix in ('refs/heads/', 'refs/remotes/origin/'):
        if r.startswith(prefix):
            r = r[len(prefix):]
    return r == 'master'


def targets_master(cmd):
    """True when this command line pushes to the stale `master` branch."""
    for piece in SEPARATOR_RE.split(cmd or ''):
        if not piece.strip():
            continue
        try:
            tokens = shlex.split(piece, posix=True)
        except ValueError:
            # Unbalanced quotes -- usually because the separator split landed
            # inside a quoted string. See the header: a parse failure must not
            # become a hole, so this piece gets the old blunt substring test.
            if re.search(r'\bgit\b.*\bpush\b.*\bmaster\b', piece, re.S):
                return True
            continue
        args = _push_args(tokens)
        if args is None:
            continue
        if any(_is_master(d) for d in _destination_refs(args)):
            return True
    return False


def main():
    payload = json.load(sys.stdin)
    tool_input = payload.get('tool_input', {}) or {}
    cmd = tool_input.get('command', '') or ''

    if targets_master(cmd):
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": "Blocked: this command pushes to the stale 'master' branch. Repo default is 'main' -- see CLAUDE.md.",
            }
        }))
        sys.exit(0)

    sys.exit(0)


if __name__ == '__main__':
    try:
        main()
    except Exception:
        # Fail open -- never let a hook bug block a legitimate command.
        sys.exit(0)
