"""
PostToolUse hook for Bash, filtered (via the hooks-config "if" field) to
git push commands only. Runs async so it never blocks the pushing turn.

After a push, waits ~60s for a normal deploy to land, then fetches and
compares origin/main:stonedesk.html against a fresh fetch of the live
sairn.vercel.app/stonedesk content, made through tools/sairn_http so it is
not answered with Vercel's bot-mitigation challenge (see that module).

BASELINE CORRECTED 2026-09-01: it used to compare against local HEAD, which
is the wrong question in a four-clone repo and false-alarmed three times in
one night. Vercel deploys origin/main; HEAD can be ahead of it, behind it, or
a different sha entirely after a rebase. The fetch happens AFTER the wait so
that a push from another clone during those 60 seconds moves the baseline
rather than registering as drift.

KNOWN SCOPE LIMIT, stated rather than implied: this checks stonedesk.html
only, and it is a PostToolUse hook keyed on the Bash command text containing
"git push" -- so a push driven from Python (tools/sairn_claim.py) never
triggers it, the same blind spot the pre-push gate was moved off in task 1.
This is a
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
import os, sys, json, subprocess, hashlib, time

# Imported by path rather than by package: this file is invoked as a hook
# from an arbitrary cwd, so a bare `import sairn_http` would depend on where
# Claude happened to be standing.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sairn_http  # noqa: E402

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

    # ── ONLY CHECK A PUSH THAT ACTUALLY SHIPPED THIS FILE -- added 2026-09-02
    # after this hook false-alarmed on a push that contained no HTML at all.
    #
    # It fired on a commit touching sql/, tools/ and tests/ only, then reported
    # that sairn.vercel.app/stonedesk did not match origin/main -- which was
    # true at that instant for an entirely unrelated reason: ANOTHER clone had
    # just pushed a real stonedesk.html change and Vercel had not finished
    # deploying it. Sixty seconds later live and origin/main agreed exactly.
    #
    # So the alarm was real drift belonging to someone else's in-flight deploy,
    # attributed to a push that could not possibly have caused it. Checking a
    # file the push never touched can only ever produce that: either a
    # coincidence or a false alarm, never evidence about this push.
    #
    # WHAT THE RANGE ACTUALLY MEANS, stated because it is an approximation and
    # not the literal question. `origin/main@{1}..origin/main` is "what arrived
    # on origin since this clone last looked", which contains this push and may
    # also contain another clone's commits fetched in the same window. It is
    # therefore WIDER than "what I just pushed" -- so it can only ever suppress
    # a check that could not possibly concern stonedesk.html, never suppress one
    # that could. That asymmetry is the whole reason it is safe.
    #
    # Fails OPEN (checks anyway) if the file list cannot be determined, because
    # the alternative is silently skipping a real verification.
    try:
        changed = subprocess.check_output(
            ["git", "log", "origin/main@{1}..origin/main", "--name-only", "--pretty=format:"],
            timeout=15, stderr=subprocess.DEVNULL
        ).decode("utf-8", "replace")
        if changed.strip() and "stonedesk.html" not in changed:
            sys.exit(0)
    except Exception:
        pass

    # ── WAIT FIRST, THEN ESTABLISH THE BASELINE. Order matters -- see below.
    time.sleep(WAIT_SECONDS)

    # ── COMPARE AGAINST origin/main, NOT LOCAL HEAD -- corrected 2026-09-01 ──
    # This hook used to hash `HEAD:stonedesk.html`. That is the wrong question
    # in a four-clone repo, and it false-alarmed three separate times in one
    # night before anyone worked out why:
    #
    #   * HEAD can be AHEAD of the remote (a local commit not pushed, or a push
    #     that touched a different file), so live legitimately differs.
    #   * HEAD can be BEHIND, because another clone pushed while this one sat
    #     idle. Live then correctly serves THEIR commit and this hook called it
    #     a stuck webhook.
    #   * After a rebase, HEAD is a different sha than the one actually sent.
    #
    # Vercel deploys whatever is on origin/main. So origin/main is the only
    # baseline that answers the question being asked -- "has the deploy caught
    # up with the remote" -- and it is fetched AFTER the wait, not before, so a
    # push landing from another clone during those 60 seconds moves the
    # baseline with it rather than being reported as drift.
    #
    # (Task 1 got the equivalent fix from the other direction: a git pre-push
    # hook is handed the remote's real sha on stdin. That mechanism is not
    # available here -- this is a PostToolUse hook and no pre-push stdin
    # exists -- so the same correctness is reached by fetching.)
    try:
        subprocess.run(["git", "fetch", "origin", "--quiet"], timeout=30,
                       capture_output=True)
        base_bytes = subprocess.check_output(
            ["git", "show", "origin/main:stonedesk.html"], timeout=15
        )
    except Exception:
        # Cannot establish what the remote actually holds. Silent rather than
        # alarming: the whole point of this change is to stop crying wolf, and
        # a notify-only hook that guesses is worse than one that says nothing.
        sys.exit(0)
    base_hash = sha256(base_bytes)

    # ── THE FETCH, AND THE SILENT SKIP THAT USED TO HIDE ITS OWN ABSENCE ──
    # CORRECTED 2026-09-02. This used to be a bare urllib call whose `except`
    # ran `sys.exit(0)` on ANY failure, described as "network hiccup -- stay
    # silent rather than false-alarm."
    #
    # That reasoning is right for a hiccup and wrong for everything else, and on
    # 2026-09-02 it cost the whole check. Four sessions live-verifying with curl
    # and urllib tripped Vercel's bot mitigation, which answers an
    # automated-looking User-Agent with 403 + `X-Vercel-Mitigated: challenge`.
    # Every push that night got a deploy check that DID NOT RUN and SAID
    # NOTHING -- indistinguishable, from the outside, from a clean pass. A
    # verification that quietly stops verifying is worse than none, because it
    # is trusted.
    #
    # Two changes. The request now goes out browser-shaped via tools/sairn_http
    # (measured: default UA 403, browser UA 200, same second, same URL). And a
    # CHALLENGE is now reported rather than swallowed -- it is not a deploy
    # problem, but "I could not look" is a different answer from "I looked and
    # it was fine", and only one of them may be silent.
    try:
        _, remote_bytes = sairn_http.fetch(LIVE_URL, timeout=FETCH_TIMEOUT, no_cache=True)
    except sairn_http.Challenged as c:
        print(json.dumps({
            "systemMessage": "Deploy check could NOT RUN: Vercel served its bot-mitigation challenge. This is not a failed deploy -- and it is not a pass either.",
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": (
                    "The post-push deploy check was unable to fetch " + LIVE_URL +
                    " because Vercel answered with its bot-mitigation challenge "
                    "(" + str(c.status) + ", X-Vercel-Mitigated: challenge). "
                    "REAL BROWSERS ARE UNAFFECTED and deployment protection is off "
                    "for this project -- this is Vercel judging the CLIENT, not an "
                    "outage and not a settings change. THE DEPLOY IS UNVERIFIED, "
                    "which is not the same as verified-good. To check it properly "
                    "from this turn, use mcp__claude_ai_Vercel__web_fetch_vercel_url "
                    "on the same URL; it authenticates past the challenge. Reported "
                    "rather than skipped because a check that silently stops "
                    "running is the failure this hook was rewritten to remove."
                ),
            },
        }))
        sys.exit(2)
    except Exception:
        # A genuine network hiccup on our end really is not evidence of a deploy
        # problem, and this path stays quiet on purpose. It is now narrow: the
        # one failure mode that used to hide here has its own branch above.
        sys.exit(0)

    remote_hash = sha256(remote_bytes)

    if remote_hash == base_hash:
        sys.exit(0)  # live matches the remote -- nothing to report

    # Live disagrees with origin/main. Say whether THIS clone is also out of
    # step, because the two situations need opposite responses and the old
    # message could not tell them apart.
    try:
        head_bytes = subprocess.check_output(
            ["git", "show", "HEAD:stonedesk.html"], timeout=15
        )
        clone_in_step = (sha256(head_bytes) == base_hash)
    except Exception:
        clone_in_step = None
    clone_note = {
        True:  "This clone's HEAD matches origin/main, so the difference is on the deploy side.",
        False: "NOTE: this clone's HEAD does NOT match origin/main either -- fetch/rebase before "
               "reading anything into the live comparison.",
        None:  "Could not determine whether this clone is in step with origin/main.",
    }[clone_in_step]

    print(json.dumps({
        "systemMessage": "Deploy check: sairn.vercel.app/stonedesk still doesn't match the just-pushed commit ~60s after push. Possible stuck Vercel webhook.",
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": (
                "Automated post-push deploy check: sairn.vercel.app/stonedesk's content "
                "hash does not match origin/main:stonedesk.html roughly 60 seconds after "
                "the last push. " + clone_note + " This does not mean the push failed -- "
                "git log/status should still show it committed and pushed. It means the "
                "live site has not picked up what the REMOTE holds, same symptom as the "
                "earlier stuck-webhook incident. Recommend: (1) push a trivial re-trigger "
                "commit, same fix that worked last time, or (2) if that doesn't resolve "
                "it, flag to the user that Vercel's Git integration may need checking "
                "directly in the dashboard (Settings > Git) -- not something checkable "
                "from here. Baseline is origin/main, fetched AFTER the 60s wait, so a "
                "push from another clone during the wait is not reported as drift."
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
