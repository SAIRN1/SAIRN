"""
PostToolUse hook for Bash, filtered (via the hooks-config "if" field) to
git push commands only. Runs async so it never blocks the pushing turn.

After a push, hashes the just-pushed stonedesk.html at HEAD and compares
it against a fresh curl of the live sairn.vercel.app/stonedesk content,
waiting ~60s first to give a normal deploy time to land. This is a
NOTIFY-ONLY check -- it never commits or pushes anything itself. On a
mismatch it exits 2 (asyncRewake) so a live Claude turn sees the finding
and decides what to do, same as the manual live-verify step already
required by CLAUDE.md's Push Protocol, just automated instead of relying
on someone remembering to run it. Never autonomous-writes to main --
that was an explicit user decision (2026-07-29), not an oversight.

Fails open on any error (network hiccup, missing git, etc.) -- same
standard as the other hooks in this file (git_push_master_guard.py,
redaction_check.py): never let a hook bug block or falsely alarm on a
legitimate push.
"""
import sys, json, subprocess, hashlib, time, urllib.request

LIVE_URL = "https://sairn.vercel.app/stonedesk"
WAIT_SECONDS = 60
FETCH_TIMEOUT = 20


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main():
    payload = json.load(sys.stdin)
    tool_input = payload.get("tool_input", {}) or {}
    cmd = tool_input.get("command", "") or ""
    tool_response = payload.get("tool_response", {}) or {}

    if "git push" not in cmd:
        sys.exit(0)
    # Only check a push that actually succeeded -- a failed push has
    # nothing new to verify against.
    if tool_response and tool_response.get("success") is False:
        sys.exit(0)

    try:
        local_bytes = subprocess.check_output(
            ["git", "show", "HEAD:stonedesk.html"], timeout=15
        )
    except Exception:
        sys.exit(0)  # can't establish what "just pushed" means -- fail open
    local_hash = sha256(local_bytes)

    time.sleep(WAIT_SECONDS)

    try:
        req = urllib.request.Request(
            LIVE_URL, headers={"Cache-Control": "no-cache", "Pragma": "no-cache"}
        )
        with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT) as resp:
            remote_bytes = resp.read()
    except Exception as e:
        # Network hiccup on our end -- not evidence of a real deploy
        # problem, so stay silent rather than false-alarm.
        sys.exit(0)

    remote_hash = sha256(remote_bytes)

    if remote_hash == local_hash:
        sys.exit(0)  # deploy matched -- nothing to report

    print(json.dumps({
        "systemMessage": "Deploy check: sairn.vercel.app/stonedesk still doesn't match the just-pushed commit ~60s after push. Possible stuck Vercel webhook.",
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": (
                "Automated post-push deploy check failed: sairn.vercel.app/stonedesk's "
                "content hash does not match HEAD:stonedesk.html roughly 60 seconds after "
                "the last git push to main. This does not mean the push failed -- git log/"
                "status should still show it committed and pushed. It means the live site "
                "has not picked it up yet, same symptom as the earlier stuck-webhook "
                "incident this session. Recommend: (1) push a trivial re-trigger commit, "
                "same fix that worked last time, or (2) if that doesn't resolve it, flag "
                "to the user that Vercel's Git integration may need checking directly in "
                "the dashboard (Settings > Git) -- not something checkable from here."
            ),
        },
    }))
    sys.exit(2)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Fail open -- never let a hook bug block or falsely alarm.
        sys.exit(0)
