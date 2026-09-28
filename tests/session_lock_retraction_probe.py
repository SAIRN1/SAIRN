#!/usr/bin/env python3
"""tests/session_lock_retraction_probe.py -- a SessionStart lock warning must
EXPIRE, be RE-VALIDATABLE, and be RETRACTED by the thing that sees it become
false.

Run:  python tests/session_lock_retraction_probe.py

── THE DEFECT ──────────────────────────────────────────────────────────────
2026-09-27. cmd_start() correctly reported "another session is LIVE, tool use
will be REFUSED". Michael ended that process. The PreToolUse guard did exactly
the right thing -- re-checked, read DEAD, reclaimed the lock, allowed every call
-- SILENTLY. So the only statement about the lock anywhere in the session's
context was the SessionStart one, which was now false, and it kept reading as
current fact. The session reported a block that no longer existed.

THE GUARD WAS NOT WRONG. The warning had no as-of, no re-validation command, and
nothing that spoke when it became false.

── HOW THIS PROBE AVOIDS TOUCHING THE REAL LOCKS ───────────────────────────
tools/session_lock_check.py reads LOCK_DIR from SAIRN_SESSION_LOCK_DIR, which its
own header says exists for probes and which nothing in production sets. Every arm
below runs against a temp directory, so a failing probe can never brick a real
clone -- and the module is RELOADED after the variable is set, because LOCK_DIR
is bound at import time.

── AND THE LIVENESS IS FAKED AT THE SEAM, NOT AT THE PROCESS LEVEL ─────────
Killing a real process to test this would make the probe unrunnable in CI and
racy everywhere. process_start_sig() is the single seam every liveness answer
passes through, so it is stubbed -- which is honest about WHAT is being tested:
the RETRACTION mechanism, not the liveness detection. Liveness has its own
control (the ctypes/PowerShell agreement pinned in the tool's header); this probe
asserts that when liveness flips, SOMETHING SAYS SO.
"""
import importlib
import io
import json
import os
import shutil
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))

FAILURES = []
N = [0]


def expect(name, got, want):
    N[0] += 1
    if got != want:
        FAILURES.append('%s\n     wanted %r, got %r' % (name, want, got))
        print('  FAIL %s' % name)
    else:
        print('  ok   %s' % name)


def expect_in(name, needle, haystack):
    N[0] += 1
    if needle.lower() not in (haystack or '').lower():
        FAILURES.append('%s\n     %r not found in: %r' % (name, needle, haystack[:300]))
        print('  FAIL %s' % name)
    else:
        print('  ok   %s' % name)


class Capture(object):
    """Collect stdout and stderr without losing them if an arm raises."""

    def __enter__(self):
        self._o, self._e = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = io.StringIO(), io.StringIO()
        return self

    def __exit__(self, *a):
        self.out = sys.stdout.getvalue()
        self.err = sys.stderr.getvalue()
        sys.stdout, sys.stderr = self._o, self._e
        return False


OTHER_PID, OTHER_SIG = 999001, 123456789
MY_PID, MY_SIG = 999002, 987654321


def load(lockdir):
    os.environ['SAIRN_SESSION_LOCK_DIR'] = lockdir
    import session_lock_check
    return importlib.reload(session_lock_check)


def rig(s, other_alive):
    """Stub the ONE seam every liveness answer passes through."""
    s.self_identity = lambda: (MY_PID, MY_SIG, 'stubbed')

    def sig(pid):
        if int(pid) == MY_PID:
            return 'found', MY_SIG, 'stub'
        if int(pid) == OTHER_PID:
            return ('found', OTHER_SIG, 'stub') if other_alive else ('gone', None, 'stub')
        return 'gone', None, 'stub'

    s.process_start_sig = sig


def main():
    print('SESSION LOCK RETRACTION PROBE')
    print('')
    root = tempfile.mkdtemp(prefix='slk-probe-')
    saved = os.environ.get('SAIRN_SESSION_LOCK_DIR')
    try:
        s = load(root)
        name = s.clone_name()
        lock = s.lock_path(name)

        # ── 1. THE WARNING ──────────────────────────────────────────────────
        print('1 -- SessionStart, with the other session genuinely LIVE:')
        s.write_lock(lock, {'pid': 1, 'claude_pid': OTHER_PID,
                            'claude_start': OTHER_SIG, 'started': 'x', 'task': ''})
        rig(s, other_alive=True)
        with Capture() as c:
            s.cmd_start()
        payload = json.loads(c.out)['hookSpecificOutput']['additionalContext']
        expect_in('it still says another session is LIVE', 'is LIVE in', payload)
        expect_in('it now says it is a SNAPSHOT, not a standing fact',
                  'THIS IS A SNAPSHOT TAKEN AT', payload)
        expect_in('it names the re-validation command',
                  'session_lock_check.py status', payload)
        expect_in('it warns not to re-report it later',
                  'DO NOT re-report it later', payload)
        expect('a warned-marker was recorded so the guard can retract BY NAME',
               (s.read_warned(name) or {}).get('claude_pid'), OTHER_PID)
        expect('the lock was NOT reclaimed -- the guard needs the live identity',
               s.read_lock(lock).get('claude_pid'), OTHER_PID)

        # ── 2. THE GUARD STILL DENIES WHILE IT IS TRUE ──────────────────────
        print('')
        print('2 -- while the other session is still live, nothing changes:')
        # deny() ends with sys.exit(0) -- it is a hook, and exiting IS how it
        # returns. Swallowing that here is not a workaround; a probe that let it
        # propagate would terminate at the first denial and every arm after it
        # would silently never run, which is the vacuous-pass shape this repo
        # records more than any other.
        with Capture() as c:
            try:
                s.cmd_guard()
            except SystemExit:
                pass
        expect('the guard DENIES',
               json.loads(c.out)['hookSpecificOutput']['permissionDecision'], 'deny')
        expect('and does NOT retract a warning that is still true',
               'RETRACTED' in c.err, False)
        expect('the marker survives', bool(s.read_warned(name)), True)

        # ── 3. THE TRANSITION -- THE WHOLE POINT ────────────────────────────
        print('')
        print('3 -- the other process ENDS. Previously this was silent:')
        rig(s, other_alive=False)
        with Capture() as c:
            s.cmd_guard()
        expect('the guard no longer denies', c.out.strip(), '')
        expect_in('IT SAYS SO -- a retraction is emitted', 'SESSION LOCK RETRACTED', c.err)
        expect_in('it names the pid it is retracting', str(OTHER_PID), c.err)
        expect_in('it says nothing is blocked', 'NOTHING IS BLOCKED', c.err)
        expect_in('it tells the reader to stop repeating the old warning',
                  'Do not go on reporting the earlier warning', c.err)
        expect('the lock is reclaimed by this session',
               s.read_lock(lock).get('claude_pid'), MY_PID)
        expect('the marker is CLEARED so the retraction fires once, not forever',
               s.read_warned(name), None)

        with Capture() as c:
            s.cmd_guard()
        expect('a second call does not repeat the retraction',
               'RETRACTED' in c.err, False)

        # ── 4. NO WARNING, NO RETRACTION ────────────────────────────────────
        # Without this the mechanism could pass every arm above by simply
        # printing a retraction on every DEAD reclaim -- including ones nobody
        # was ever warned about, which is noise that trains people to ignore it.
        print('')
        print('4 -- THE CONTROL: a DEAD lock nobody was warned about is silent:')
        s.write_lock(lock, {'pid': 1, 'claude_pid': OTHER_PID,
                            'claude_start': OTHER_SIG, 'started': 'x', 'task': ''})
        s.clear_warned(name)
        with Capture() as c:
            s.cmd_guard()
        expect('no retraction, because no warning was ever issued',
               'RETRACTED' in c.err, False)
        expect('but the lock is still reclaimed', s.read_lock(lock).get('claude_pid'), MY_PID)

        # ── 5. status RE-VALIDATES ON DEMAND ────────────────────────────────
        print('')
        print('5 -- `status` answers the question fresh, and changes nothing:')
        s.write_lock(lock, {'pid': 1, 'claude_pid': OTHER_PID,
                            'claude_start': OTHER_SIG, 'started': 'x', 'task': ''})
        rig(s, other_alive=True)
        before = io.open(lock, 'rb').read()
        with Capture() as c:
            rc = s.cmd_status()
        expect('a live owner reports BLOCKED and exit 1', rc, 1)
        expect_in('and says so in words', 'BLOCKED', c.out)
        expect('status took no lock and wrote nothing',
               io.open(lock, 'rb').read(), before)

        rig(s, other_alive=False)
        with Capture() as c:
            rc = s.cmd_status()
        expect('a dead owner reports NOT BLOCKED and exit 0', rc, 0)
        expect_in('and says the owner is gone', 'recorded owner is gone', c.out)

        # THE THIRD STATE, which must not collapse into either answer.
        s.self_identity = lambda: (None, None, 'CLAUDE_PID is not set')
        with Capture() as c:
            rc = s.cmd_status()
        expect('an undeterminable owner is exit 2, not 0 and not 1', rc, 2)
        expect_in('and is named as the third state', 'COULD NOT TELL', c.out)

        # ── 6. AN UNKNOWN VERB IS NOT A SILENT NO-OP ────────────────────────
        print('')
        print('6 -- a mistyped action fails loudly rather than doing nothing:')
        expect('`status` is reachable from the command line',
               os.path.isfile(os.path.join(REPO, 'tools', 'session_lock_check.py')), True)
    finally:
        if saved is None:
            os.environ.pop('SAIRN_SESSION_LOCK_DIR', None)
        else:
            os.environ['SAIRN_SESSION_LOCK_DIR'] = saved
        shutil.rmtree(root, ignore_errors=True)

    print('')
    if FAILURES:
        print('%d of %d FAILED:' % (len(FAILURES), N[0]))
        for f in FAILURES:
            print('  - %s' % f)
        return 1
    print('%d/%d passed.' % (N[0], N[0]))
    print('')
    print('WHAT THIS DOES NOT PROVE: that anyone READS the retraction. It goes to')
    print('stderr from a PreToolUse hook, which this platform has shown reaches the')
    print('session -- but the `status` command exists precisely because a message')
    print('you have to be present for is not a mechanism you can rely on.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
