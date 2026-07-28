"""
PreToolUse hook for Bash. Reads the hook payload on stdin (the same
mechanism redaction_check.py uses -- confirmed working all session) and
blocks (permissionDecision: deny) any command matching git push.*master.

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
"""
import sys, re, json


def main():
    payload = json.load(sys.stdin)
    tool_input = payload.get('tool_input', {}) or {}
    cmd = tool_input.get('command', '') or ''

    if re.search(r'git push.*master', cmd):
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
