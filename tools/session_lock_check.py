#!/usr/bin/env python3
# tools/session_lock_check.py
# SAIRN session-lock check -- warns when another session claims this clone, and
# REFUSES TOOL USE when that other session is confirmed to still be running.
# Built 2026-08-24 after two Claude Code sessions independently worked the
# identical task the same night with no way for either to know the other
# existed.
#
# Design, approved before building (see SAIRN-ACTIVE-WORK-cc.md, 2026-08-24):
#   - Lock files live OUTSIDE every git clone (~/SAIRN-SESSION-LOCKS), so
#     they never enter git history and are visible to any clone on this
#     machine without a push/pull. UNCHANGED, still correct.
#   - Detects same-clone concurrent sessions ONLY. Does NOT detect two
#     different clones independently converging on the same external task
#     -- that is a harder, task-registry-shaped problem and out of scope.
#     UNCHANGED.
#   - Staleness was TIME-BASED ONLY. That half is now a FALLBACK rather than
#     the whole answer; see below. The 2-hour timeout is unchanged and is
#     still the sole answer whenever liveness cannot be determined.
#
# ── WHAT CHANGED 2026-09-16, AND WHY THE ORIGINAL REASONING WAS RIGHT AT THE
# ── TIME IT WAS WRITTEN
#
# The original header argued that PID liveness was unavailable to this script,
# and the argument was sound: every hook firing is a brand-new short-lived
# `python` process, so os.getpid() differs on every single invocation and there
# was no stable identity across a session's lifetime to check. The same fact
# rules out a kernel flock(): flock ties a lock's lifetime to an open file
# descriptor held by one continuously-running process, and this script has no
# continuously-running process to hold one.
#
# What was missing was not a technique, it was an identity. `CLAUDE_PID` is in
# the environment of every hook invocation and names the Claude Code CLI process
# itself -- stable for the whole session, inherited by every hook. Measured
# 2026-09-16: present, e.g. 27280, in both SessionStart and PreToolUse hooks.
# That is the stable identity the 2026-08-24 design correctly said it did not
# have.
#
# A BARE PID-ALIVE CHECK WOULD BE A BUG, not a fix: pids are recycled, so a
# dead session's pid now belonging to some unrelated process would read as
# "still working here" and lock the clone out for ever. The lock therefore
# stores the owner's PROCESS START TIME alongside its pid, and liveness means
# BOTH match. Three independent open-source projects have shipped the recycled-
# pid version of this bug; the start-time comparison is the whole defence.
#
# ── AND THE HALF THAT ACTUALLY FAILED: A WARNING NOBODY HAS TO OBEY
#
# The SessionStart warning below did not malfunction. It fired, correctly, and
# twice on 2026-09-15 a session read it and carried on anyway. BEING IGNORABLE
# IS WHAT FAILED. SessionStart hooks cannot deny -- only PreToolUse carries
# `permissionDecision: "deny"` (tools/sairn_push_gate_hook.py:290-305 is the
# working precedent in this same codebase). So `guard` is a PreToolUse hook on
# Write|Edit|Bash that genuinely refuses, and the SessionStart warning stays as
# the first heads-up rather than as the enforcement.
#
# ── COULD-NOT-DETERMINE IS A THIRD STATE (PR §1.11)
#
# owner_state() returns one of SELF / ALIVE / DEAD / UNKNOWN and never folds
# UNKNOWN into either end. UNKNOWN -- CLAUDE_PID unset, a lock written before
# this change, a start-time query that errors -- falls back to exactly the
# pre-2026-09-16 behaviour: time-based staleness only, advisory, nothing
# blocked. It is never treated as DEAD (which would hand the clone to a second
# session while the first is still typing) and never as ALIVE (which would
# brick a session over an unreadable process handle).
#
# Wired via .claude/settings.json hooks (SessionStart / UserPromptSubmit /
# PreToolUse). The copy at C:/Users/marsh/tools/session_lock_check.py is
# ORPHANED -- no clone's settings.json references it, and as of 2026-09-16 it
# is still the pre-2026-09-11 version with the cwd bug. Do not revive it.
#
# Usage: python session_lock_check.py {start|heartbeat|guard}

import json
import os
import subprocess
import sys
import time
import uuid

STALE_SECONDS = 2 * 60 * 60  # 2 hours, confirmed with Michael 2026-08-24
# Overridable for probes ONLY -- tests/session_lock_liveness_probe.py drives a
# copy of this file against a temp directory so it can never touch the real
# locks. Nothing in production sets it.
LOCK_DIR = os.environ.get(
    'SAIRN_SESSION_LOCK_DIR',
    os.path.join(os.path.expanduser('~'), 'SAIRN-SESSION-LOCKS'))

SELF = 'self'
ALIVE = 'alive'
DEAD = 'dead'
UNKNOWN = 'unknown'

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
ERROR_INVALID_PARAMETER = 87  # what OpenProcess returns for a pid that is gone


def clone_name():
    # Documents\SAIRN-hank -> hank, Documents\SAIRN-cc -> cc, etc. A clone
    # that doesn't follow the SAIRN-<name> convention just uses its own
    # folder name -- no hardcoded list of the four, so a fifth/ad-hoc clone
    # still gets a real, distinct lock rather than erroring or colliding
    # with an unrelated directory.
    #
    # ── FROM THIS FILE'S OWN LOCATION, NOT THE WORKING DIRECTORY (2026-09-11)
    # It read os.path.basename(os.getcwd()), and this runs as a SessionStart
    # and UserPromptSubmit hook, which inherit whatever directory the session's
    # Bash tool is sitting in. Measured: from `tools/` it returned 'tools' and
    # from `docs/` it returned 'docs'.
    #
    # THAT IS THE WORST POSSIBLE FAILURE FOR THIS PARTICULAR FUNCTION, because
    # EVERY clone has a `tools/` and a `docs/`. The lock is per-clone by name,
    # so a drifted cwd does not merely mislabel the session -- it makes four
    # separate clones all claim the SAME lock and report each other as a
    # duplicate session in the one directory where they are guaranteed to
    # collide. Silent, and exactly backwards from what the lock is for.
    #
    # The repo root is a fact about where this file lives; the cwd is not.
    base = os.path.basename(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
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


# ── READING A PROCESS'S START TIME ──────────────────────────────────────────
# Two structurally different methods, and that is deliberate (cross-domain
# discipline 6): they share no mechanism, so a failure in one does not silently
# become a wrong answer from the other. ctypes is primary because it costs
# ~20us; PowerShell costs ~600ms and would tax every single tool call.
#
# THEY RETURN THE SAME NUMBER, VERIFIED 2026-09-16 against CLAUDE_PID 27280:
# both 134340359245483744. That is only true because the PowerShell arm calls
# .ToFileTime() -- .Ticks on the same DateTime returns 639251447245483744, a
# different epoch, and a lock written under one arm would then read as
# "recycled pid" under the other. If either arm is ever changed, re-verify that
# equality; a signature is only useful while both writers agree on it.

def _start_sig_ctypes(pid):
    """(state, detail) where state is found | gone | unknown."""
    import ctypes
    from ctypes import wintypes

    k = ctypes.WinDLL('kernel32', use_last_error=True)
    k.OpenProcess.restype = wintypes.HANDLE
    k.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    k.GetProcessTimes.restype = wintypes.BOOL
    k.GetProcessTimes.argtypes = ([wintypes.HANDLE] +
                                  [ctypes.POINTER(wintypes.FILETIME)] * 4)

    handle = k.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, int(pid))
    if not handle:
        err = ctypes.get_last_error()
        if err == ERROR_INVALID_PARAMETER:
            return 'gone', None
        # ACCESS_DENIED (5) and anything else is NOT evidence of death -- a
        # process we may not query is still a process.
        return 'unknown', 'OpenProcess error %d' % err
    try:
        created, exited, kern, user = (wintypes.FILETIME() for _ in range(4))
        if not k.GetProcessTimes(handle, ctypes.byref(created),
                                 ctypes.byref(exited), ctypes.byref(kern),
                                 ctypes.byref(user)):
            return 'unknown', 'GetProcessTimes error %d' % ctypes.get_last_error()
        if (exited.dwHighDateTime << 32) | exited.dwLowDateTime:
            # Windows keeps a pid queryable while ANY handle on it is still
            # open, so OpenProcess succeeding is not proof of life. A non-zero
            # exit time is the only thing that separates a running process from
            # one its parent has not reaped.
            return 'gone', None
        return 'found', (created.dwHighDateTime << 32) | created.dwLowDateTime
    finally:
        k.CloseHandle(handle)


def _start_sig_powershell(pid):
    """(state, detail) where state is found | gone | unknown."""
    try:
        out = subprocess.run(
            ['powershell.exe', '-NoProfile', '-NonInteractive', '-Command',
             '(Get-Process -Id %d -ErrorAction Stop).StartTime.ToFileTime()'
             % int(pid)],
            capture_output=True, text=True, timeout=15)
    except Exception as exc:
        return 'unknown', 'powershell did not run: %s' % exc
    text = (out.stdout or '').strip()
    if out.returncode == 0 and text.isdigit():
        return 'found', int(text)
    if 'Cannot find a process' in (out.stderr or ''):
        return 'gone', None
    return 'unknown', 'powershell rc=%s' % out.returncode


def process_start_sig(pid):
    """(state, detail, how). state is found | gone | unknown; on found, detail
    is the start-time signature."""
    if os.name != 'nt':
        return 'unknown', 'start-time liveness is Windows-only here', 'none'
    try:
        state, detail = _start_sig_ctypes(pid)
    except Exception as exc:
        state, detail = 'unknown', 'ctypes path failed: %s' % exc
    if state != 'unknown':
        return state, detail, 'ctypes'
    state, detail = _start_sig_powershell(pid)
    return state, detail, 'powershell'


def self_identity():
    """(claude_pid, start_sig, why) for THIS session. Either may be None."""
    raw = (os.environ.get('CLAUDE_PID') or '').strip()
    if not raw.isdigit():
        return None, None, 'CLAUDE_PID is not set in this hook environment'
    pid = int(raw)
    state, detail, how = process_start_sig(pid)
    if state != 'found':
        return pid, None, ('own start time unreadable (%s, via %s)'
                           % (detail, how))
    return pid, detail, 'via ' + how


def owner_state(info):
    """(state, why) for whoever wrote this lock. Never guesses: UNKNOWN is a
    real answer and is handled by the callers as 'fall back to staleness'."""
    lock_pid = info.get('claude_pid')
    lock_sig = info.get('claude_start')
    if not lock_pid or not lock_sig:
        return UNKNOWN, ('lock carries no claude_pid/claude_start -- written '
                         'before liveness tracking existed')

    my_pid, my_sig, why = self_identity()
    if my_pid is None:
        return UNKNOWN, why

    if int(lock_pid) == my_pid:
        if my_sig is None:
            return UNKNOWN, why
        if str(lock_sig) == str(my_sig):
            return SELF, 'this session owns the lock (CLAUDE_PID %d)' % my_pid
        return DEAD, ('CLAUDE_PID %d is live but started at a different time '
                      'than the lock records -- the pid was recycled and the '
                      'lock owner is gone' % my_pid)

    state, detail, how = process_start_sig(int(lock_pid))
    if state == 'gone':
        return DEAD, 'CLAUDE_PID %s no longer exists' % lock_pid
    if state == 'unknown':
        return UNKNOWN, ('could not read the start time of CLAUDE_PID %s: %s '
                         '(via %s)' % (lock_pid, detail, how))
    if str(detail) == str(lock_sig):
        return ALIVE, ('CLAUDE_PID %s is running and started exactly when the '
                       'lock says' % lock_pid)
    return DEAD, ('CLAUDE_PID %s exists but started at a different time than '
                  'the lock records -- the pid was recycled and the lock owner '
                  'is gone' % lock_pid)


def lock_payload(task=''):
    my_pid, my_sig, _ = self_identity()
    return {
        # The hook's own pid. Diagnostics only -- it is a different number on
        # every invocation and must never be used for liveness.
        'pid': os.getpid(),
        'claude_pid': my_pid,
        'claude_start': my_sig,
        'started': time.strftime('%Y-%m-%dT%H:%M:%S'),
        'task': task,
    }


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


def deny(reason):
    # Same shape as tools/sairn_push_gate_hook.py's deny(), which is already
    # wired and working on this platform.
    print(json.dumps({
        'hookSpecificOutput': {
            'hookEventName': 'PreToolUse',
            'permissionDecision': 'deny',
            'permissionDecisionReason': reason,
        }
    }))
    sys.exit(0)


def _describe(name, info, path):
    age_min = 0
    try:
        age_min = int((time.time() - os.path.getmtime(path)) / 60)
    except OSError:
        pass
    task = info.get('task') or ''
    return ("the '%s' clone (CLAUDE_PID %s, started %s, last active %sm ago%s)"
            % (name, info.get('claude_pid') or info.get('pid') or '?',
               info.get('started', '?'), age_min,
               (', task: ' + task) if task else ''))


def cmd_start():
    name = clone_name()
    path = lock_path(name)
    info = read_lock(path) if os.path.exists(path) else None

    if info is not None and not is_stale(path):
        state, why = owner_state(info)

        if state == ALIVE:
            emit_context('SessionStart', (
                "SESSION LOCK: another session is LIVE in %s. %s -- this is a "
                "confirmed running process, not a stale lock. Tool use in this "
                "session will be REFUSED by the PreToolUse guard until that "
                "session exits. Surface this to Michael now and let him decide "
                "which session continues. Note: this check only catches two "
                "sessions in the SAME clone directory -- it cannot see a "
                "different clone working the same task."
            ) % (_describe(name, info, path), why))
            # DO NOT reclaim. The guard needs the LIVE owner's identity in the
            # lock file; overwriting it here would make every later check read
            # 'self' and the deny would never fire. This is the whole reason
            # the warning was previously toothless in a different way.
            return

        if state == UNKNOWN:
            emit_context('SessionStart', (
                "SESSION LOCK WARNING: another session already claims %s. "
                "LIVENESS COULD NOT BE DETERMINED (%s), so this falls back to "
                "the %dh staleness rule only -- the other session may or may "
                "not still be running, and nothing will be blocked. If it is "
                "still open in another window, this new one is about to "
                "duplicate its work -- surface this to Michael immediately, "
                "before doing anything else. Note: this check only catches two "
                "sessions in the SAME clone directory -- it cannot see a "
                "different clone working the same task."
            ) % (_describe(name, info, path), why, STALE_SECONDS // 3600))
        # DEAD or SELF: no warning. A confirmed-dead owner is reclaimed
        # immediately rather than waiting out the 2 hours.

    write_lock(path, lock_payload())


def cmd_guard():
    """PreToolUse. The enforcement the SessionStart warning could never be."""
    name = clone_name()
    path = lock_path(name)
    info = read_lock(path) if os.path.exists(path) else None

    if info is None or is_stale(path):
        write_lock(path, lock_payload())
        return

    state, why = owner_state(info)

    if state == ALIVE:
        deny(
            "SESSION LOCK: tool use refused. Another Claude Code session is "
            "running RIGHT NOW in %s.\n\n"
            "Liveness was confirmed against that process's real start time "
            "(%s), not inferred from the clock -- this is not a stale-lock "
            "false alarm, and a recycled pid would have read as dead.\n\n"
            "Two sessions in one clone overwrite each other's edits and "
            "duplicate each other's work. Close one of them, or ask Michael "
            "which should continue.\n\n"
            "Nothing needs to be cleaned up if that session ends: the next "
            "tool call re-checks the process and reclaims the lock "
            "automatically. Lock file: %s"
            % (_describe(name, info, path), why, path))

    if state == DEAD:
        write_lock(path, lock_payload())
        return

    if state == UNKNOWN:
        # PR §1.11's third state. Not a pass and not a block -- the
        # pre-2026-09-16 behaviour, said out loud instead of silently assumed.
        sys.stderr.write(
            'session-lock: could not determine whether the lock holder is '
            'still running (%s); falling back to the %dh staleness rule. '
            'Nothing blocked.\n' % (why, STALE_SECONDS // 3600))
        return

    # SELF: the common case, and it costs one file read plus one ~20us
    # OpenProcess. Nothing to do.


def cmd_heartbeat():
    # Unconditional touch, on purpose. In the normal case (one session in this
    # clone) it keeps that session's own lock fresh. In the collision case the
    # second session is being denied tool use anyway, and either session's
    # prompts keeping the single lock file looking active is still the correct
    # answer to "is anyone working here".
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
    elif action == 'guard':
        cmd_guard()
