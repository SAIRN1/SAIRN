#!/usr/bin/env python3
# tools/session_lock_check.py
# SAIRN session-lock check -- warns loudly if another live session already
# claims this clone directory. Built 2026-08-24 after two Claude Code
# sessions independently worked the identical task the same night with no
# way for either to know the other existed.
#
# Design, approved before building (see SAIRN-ACTIVE-WORK-cc.md, 2026-08-24):
#   - Lock files live OUTSIDE every git clone (~/SAIRN-SESSION-LOCKS), so
#     they never enter git history and are visible to any clone on this
#     machine without a push/pull.
#   - Staleness is TIME-BASED ONLY (lock file mtime vs a threshold), never
#     PID-liveness -- cross-shell PID checks are exactly the fragility a
#     "dead simple" tool should not take on. A 'heartbeat' call on every
#     user prompt keeps a genuinely active session's lock fresh; without
#     one for STALE_SECONDS, the lock is treated as abandoned and silently
#     reclaimed, no warning.
#   - Detects same-clone concurrent sessions ONLY. Does NOT detect two
#     different clones independently converging on the same external task
#     -- that is a harder, task-registry-shaped problem and out of scope.
#
# NO SessionEnd/clean-exit deletion, found DURING BUILD to be worse than not
# having it: every hook firing is a brand-new short-lived `python` process,
# so os.getpid() is different on every single invocation -- 'start',
# 'heartbeat' and an 'end' would each see a different PID, with no stable
# identity across a session's whole lifetime available to this script. The
# original design treated PID as an ownership check to avoid one session's
# exit handler deleting a DIFFERENT, still-active session's lock; without a
# stable identity that check cannot work, and deleting unconditionally on
# every exit would be actively wrong (a first session ending would erase a
# second, still-running session's lock). Simpler and safe: no exit hook at
# all. The 2-hour staleness timeout is the sole cleanup mechanism, exactly
# the fallback already described when this was proposed -- not a downgrade,
# the plan always said the timeout alone had to be sufficient on its own.
#
# Wired via .claude/settings.json hooks (SessionStart / UserPromptSubmit),
# invoked from the global C:/Users/marsh/tools/ copy the same way the
# platform's other hook scripts already are.
#
# Usage: python session_lock_check.py {start|heartbeat}

import json
import os
import sys
import time
import uuid

STALE_SECONDS = 2 * 60 * 60  # 2 hours, confirmed with Michael 2026-08-24
LOCK_DIR = os.path.join(os.path.expanduser('~'), 'SAIRN-SESSION-LOCKS')


def clone_name():
    # Documents\SAIRN-hank -> hank, Documents\SAIRN-cc -> cc, etc. A clone
    # that doesn't follow the SAIRN-<name> convention just uses its own
    # folder name -- no hardcoded list of the four, so a fifth/ad-hoc clone
    # still gets a real, distinct lock rather than erroring or colliding
    # with an unrelated directory.
    base = os.path.basename(os.getcwd())
    if base.upper().startswith('SAIRN-'):
        name = base[len('SAIRN-'):]
    else:
        name = base
    return (name or 'unknown').lower()


def lock_path(name):
    return os.path.join(LOCK_DIR, name + '.lock')


def read_lock(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def write_lock(path, data):
    os.makedirs(LOCK_DIR, exist_ok=True)
    tmp = path + '.tmp-' + uuid.uuid4().hex[:8]
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f)
    os.replace(tmp, path)  # atomic on the same filesystem


def is_stale(path):
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        return True
    return (time.time() - mtime) > STALE_SECONDS


def emit_context(event_name, text):
    # Same shape as the platform's existing PreCompact hook -- suppressOutput
    # so the raw JSON never shows in the transcript, additionalContext
    # carries the message plus an explicit instruction, since that pattern
    # is already proven to reach the assistant reliably in this codebase.
    print(json.dumps({
        'hookSpecificOutput': {
            'hookEventName': event_name,
            'additionalContext': text
        },
        'suppressOutput': True
    }))


def cmd_start():
    name = clone_name()
    path = lock_path(name)

    if os.path.exists(path) and not is_stale(path):
        info = read_lock(path) or {}
        age_min = int((time.time() - os.path.getmtime(path)) / 60)
        task = info.get('task') or ''
        warning = (
            "SESSION LOCK WARNING: another session already claims the '%s' clone "
            "(PID %s, started %s, last active %sm ago%s). If that session is "
            "still open in another window, this new one is about to duplicate "
            "its work -- surface this to Michael immediately, before doing "
            "anything else, and let him decide whether to proceed. This is a "
            "heads-up only; nothing is blocked. Note: this check only catches "
            "two sessions in the SAME clone directory -- it cannot see a "
            "different clone working the same task."
        ) % (name, info.get('pid', '?'), info.get('started', '?'), age_min,
             (', task: ' + task) if task else '')
        emit_context('SessionStart', warning)

    write_lock(path, {
        'pid': os.getpid(),
        'started': time.strftime('%Y-%m-%dT%H:%M:%S'),
        'task': ''
    })


def cmd_heartbeat():
    # Unconditional touch, on purpose -- see the header note on why a PID-
    # based ownership check can't work across separate hook-invoked
    # processes. In the normal case (one session in this clone) this simply
    # keeps that session's own lock fresh. In the collision case (two
    # sessions in the same clone, which already triggered a warning at the
    # second one's startup), either session's prompts keep the single shared
    # lock file looking active -- which is the correct answer to "is anyone
    # still working here," even though the file can no longer say precisely
    # which of the two.
    path = lock_path(clone_name())
    if os.path.exists(path):
        try:
            os.utime(path, None)
        except OSError:
            pass


if __name__ == '__main__':
    action = sys.argv[1] if len(sys.argv) > 1 else 'start'
    if action == 'start':
        cmd_start()
    elif action == 'heartbeat':
        cmd_heartbeat()
