"""
PostToolUse hook for Write|Edit. Reads the hook payload on stdin (the
proven-working mechanism -- see git_push_master_guard.py and
redaction_check.py) and, for any edited .html file, previews each inline
<script> block's opening tag. Purely informational -- PostToolUse cannot
block anything, and this never raises even on a totally unexpected
payload shape.

Root cause of why the previous version never did anything: it relied on
a $CLAUDE_TOOL_INPUT_FILE_PATH environment variable substituted into a
bash `if [[ "$CLAUDE_TOOL_INPUT_FILE_PATH" == *.html ]]` check. Same
family of bug as the PreToolUse Bash-guard hook fixed earlier this
session -- switched to stdin for the same reason.
"""
import sys, re, json


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


if __name__ == '__main__':
    try:
        main()
    except Exception:
        # Informational only -- never let this hook error visibly.
        pass
