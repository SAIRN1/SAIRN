"""
PreToolUse hook for Write|Edit. Reads the hook payload on stdin, scans the
content about to be written for credential-shaped strings, and blocks the
tool call (permissionDecision: deny) if any are found.

Wired in response to SESSION68 open item #1: a real GitHub PAT was involved
in a prior session and no check existed to catch that before a save. See
SAIRN-SESSION68-HANDOFF.md section 4.

Deliberately vendor-specific/high-confidence patterns first (near-zero false
positive rate), plus one guarded generic assignment pattern last. This repo
is full of throwaway check_*.js / temp_check_*.js files, so a noisy check
here would get worked around rather than respected -- keep it tight.
"""
import sys, re, json

VENDOR_PATTERNS = [
    ("github_pat", re.compile(r'\bgithub_pat_[A-Za-z0-9_]{22,}')),
    ("github_token", re.compile(r'\bgh[oprsu]_[A-Za-z0-9]{36,}')),
    ("aws_access_key_id", re.compile(r'\bAKIA[0-9A-Z]{16}\b')),
    ("anthropic_api_key", re.compile(r'\bsk-ant-[A-Za-z0-9\-_]{20,}')),
    ("openai_api_key", re.compile(r'\bsk-[A-Za-z0-9]{20,}\b')),
    ("stripe_live_key", re.compile(r'\b(sk|rk)_live_[0-9a-zA-Z]{24,}')),
    ("slack_token", re.compile(r'\bxox[baprs]-[A-Za-z0-9-]{10,}')),
    ("google_api_key", re.compile(r'\bAIza[0-9A-Za-z\-_]{35}\b')),
    ("private_key_block", re.compile(r'-----BEGIN (RSA |EC |OPENSSH |DSA |)?PRIVATE KEY-----')),
    ("jwt", re.compile(r'\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}')),
]

GENERIC_ASSIGNMENT = re.compile(
    r'(?i)(api[_-]?key|secret|token|password|passwd)\s*[:=]\s*["\']([A-Za-z0-9_\-/+=]{16,})["\']'
)

PLACEHOLDER_MARKERS = (
    'your_', 'replace_', 'changeme', 'change_me', 'example', 'placeholder',
    'xxxxxxxx', '<', 'todo', 'fixme', '00000000', 'test_key', 'fake',
)


def find_hits(text):
    hits = []
    for name, pattern in VENDOR_PATTERNS:
        m = pattern.search(text)
        if m:
            hits.append((name, m.group(0)[:12] + '...'))
    for m in GENERIC_ASSIGNMENT.finditer(text):
        value = m.group(2)
        if any(marker in value.lower() for marker in PLACEHOLDER_MARKERS):
            continue
        hits.append(('generic_credential_assignment', m.group(1) + '=' + value[:6] + '...'))
    return hits


def main():
    payload = json.load(sys.stdin)
    tool_name = payload.get('tool_name', '')
    tool_input = payload.get('tool_input', {}) or {}

    if tool_name == 'Write':
        text = tool_input.get('content', '') or ''
    elif tool_name == 'Edit':
        text = tool_input.get('new_string', '') or ''
    else:
        text = ''

    hits = find_hits(text)

    if hits:
        kinds = ', '.join(sorted(set(k for k, _ in hits)))
        reason = (
            f"Blocked: content matches credential-shaped pattern(s): {kinds}. "
            f"Remove or redact the secret before writing this file."
        )
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        }))
        sys.exit(0)

    sys.exit(0)


if __name__ == '__main__':
    try:
        main()
    except Exception:
        # Never let a hook bug block legitimate saves -- fail open.
        sys.exit(0)
