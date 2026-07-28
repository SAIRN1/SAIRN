"""
PostToolUse hook for Write|Edit. Reads the hook payload on stdin (the
proven-working mechanism -- see git_push_master_guard.py and
redaction_check.py) and, for any edited .html file: previews each inline
<script> block's opening tag, then runs duplicate_global_check.py and
missing_dom_target_check.py against the same file and prints their
output ONLY if either finds something (silent on a clean pass, so normal
edits stay quiet). Purely informational -- PostToolUse cannot block
anything, and this never raises even on a totally unexpected payload
shape or if either sub-check itself errors.

Root cause of why the previous version never did anything: it relied on
a $CLAUDE_TOOL_INPUT_FILE_PATH environment variable substituted into a
bash `if [[ "$CLAUDE_TOOL_INPUT_FILE_PATH" == *.html ]]` check. Same
family of bug as the PreToolUse Bash-guard hook fixed earlier this
session -- switched to stdin for the same reason.

The two sub-checks were built the same session this hook wiring was
added and were NOT actually wired in until this revision -- confirmed by
checking .claude/settings.json directly rather than assuming a prior
description was accurate.
"""
import sys, re, json, os, subprocess


def main():
    payload = json.load(sys.stdin)
    tool_input = payload.get('tool_input', {}) or {}
    file_path = tool_input.get('file_path', '') or ''

    if not file_path.lower().endswith('.html'):
        return

    try:
        with open(file_path, encoding='utf-8', errors='replace') as f:
            content = f.read()
    except OSError:
        return

    pattern = re.compile(r'<script(?![^>]*\bsrc=)[^>]*>')
    matches = [m.group(0)[:50] for m in pattern.finditer(content)]

    print('--- auto script-block preview on edited HTML ---')
    print(len(matches))

    tools_dir = os.path.dirname(os.path.abspath(__file__))
    for script_name, label in (
        ('duplicate_global_check.py', 'DUPLICATE GLOBAL CHECK'),
        ('missing_dom_target_check.py', 'MISSING DOM TARGET CHECK'),
    ):
        script_path = os.path.join(tools_dir, script_name)
        try:
            result = subprocess.run(
                [sys.executable, script_path, file_path],
                capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=20,
            )
            if result.returncode != 0:
                # Capped, not the full dump: missing_dom_target_check.py
                # in particular has a large pre-existing backlog (~470
                # findings as of this session) that would otherwise print
                # in full on every single .html edit, drowning out any
                # NEW orphan this specific edit introduced and bloating
                # context on every future edit. First 3 lines (the two
                # summary counts + one detail line) plus a truncation
                # note is enough to notice something changed without the
                # full-backlog noise.
                out_lines = result.stdout.splitlines()
                print('--- %s: FOUND ISSUES (showing first 3 of %d output lines) ---' % (label, len(out_lines)))
                print('\n'.join(out_lines[:3]))
                if len(out_lines) > 3:
                    print('... (%d more lines -- run `python tools/%s %s` directly for the full list)'
                          % (len(out_lines) - 3, script_name, file_path))
        except Exception:
            pass  # never let a sub-check failure block or error this hook


if __name__ == '__main__':
    try:
        main()
    except Exception:
        # Informational only -- never let this hook error visibly.
        pass
