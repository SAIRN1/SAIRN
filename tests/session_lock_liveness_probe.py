#!/usr/bin/env python3
"""Does tools/session_lock_check.py's PreToolUse guard refuse the right session?

    python tests/session_lock_liveness_probe.py

── WHAT IT IS FOR ────────────────────────────────────────────────────────────
The guard added 2026-09-16 turns a lock file into a REFUSAL. That makes two new
ways to be wrong, opposite to each other and both expensive:

  * it refuses when it should not -- a session is locked out of its own clone
    because a dead session's pid was recycled by something unrelated. A bare
    pid-alive check has exactly this bug, and three open-source projects have
    shipped it. The only defence is the start-time comparison, so the recycled
    case is an arm here rather than a comment;
  * it allows when it should not -- which is the original 2026-09-15 failure
    (two live sessions in one clone) coming back silently.

── NO REAL LOCKS ARE TOUCHED ─────────────────────────────────────────────────
The tool is COPIED into a temp tree named SAIRN-probeclone, and the copy is
pointed at a temp lock directory via SAIRN_SESSION_LOCK_DIR. clone_name() reads
the copy's own path, so it claims 'probeclone' and can never collide with the
four real clones' locks. The copy is verified byte-identical to the real file
before anything runs -- a probe exercising a stale copy of its subject is the
instrument-drift failure (cross-domain discipline 8) and would report green for
a tool nobody had tested.

── THE LIVENESS FACTS ARE REAL, THE DEATH IS REAL, THE RECYCLING IS SYNTHETIC ─
Arms (a) and (b) use two genuinely running child processes. Arm (c1) kills one
and lets the tool discover that. Arm (c2) CANNOT be produced honestly -- waiting
for Windows to hand a specific pid to an unrelated process is not a test -- so
it is built by storing a live pid beside a start-time signature that is not its
own, which is bit-for-bit the state the recycled case produces and is the only
state the tool can actually read. That substitution is stated here rather than
left to be discovered.

── ARM (e) IS THE CONTROL THAT MAKES ARM (b) FAIL ────────────────────────────
Arm (b) passing proves a deny happened; it does not prove the LIVENESS VERDICT
caused it. Arm (e) neuters owner_state() to always answer UNKNOWN under
arm (b)'s exact conditions and asserts the deny disappears. Without it, a guard
that denied for some unrelated reason would look identical.

Exit 0 when every arm holds, 1 when one does not, 2 when the probe could not
set itself up -- which means nothing was tested.
"""
import contextlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REAL_TOOL = os.path.join(REPO, 'tools', 'session_lock_check.py')

failures = []
arms = 0


def check(label, ok, detail=''):
    global arms
    arms += 1
    print('  %-5s %s%s' % ('PASS' if ok else 'FAIL', label,
                           ('  -- ' + detail) if detail else ''))
    if not ok:
        failures.append(label)


def refuse(why):
    print('COULD NOT TEST: ' + why)
    print('Nothing was verified. This is not a pass.')
    sys.exit(2)


def run(tool, action, claude_pid, lock_dir):
    env = dict(os.environ)
    env['SAIRN_SESSION_LOCK_DIR'] = lock_dir
    if claude_pid is None:
        env.pop('CLAUDE_PID', None)
    else:
        env['CLAUDE_PID'] = str(claude_pid)
    return subprocess.run([sys.executable, tool, action],
                          capture_output=True, text=True, encoding='utf-8', errors='replace', env=env, timeout=60)


def decision(proc):
    """'deny' | 'context' | 'silent' -- what the hook actually told the host."""
    out = (proc.stdout or '').strip()
    if not out:
        return 'silent'
    try:
        payload = json.loads(out)
    except ValueError:
        return 'silent'
    spec = payload.get('hookSpecificOutput', {})
    if spec.get('permissionDecision') == 'deny':
        return 'deny'
    if spec.get('additionalContext'):
        return 'context'
    return 'silent'


def main():
    if not os.path.isfile(REAL_TOOL):
        refuse('tools/session_lock_check.py is not on disk at ' + REAL_TOOL)

    tmp = tempfile.mkdtemp(prefix='sairn-lockprobe-')
    children = []
    try:
        clone = os.path.join(tmp, 'SAIRN-probeclone', 'tools')
        os.makedirs(clone)
        tool = os.path.join(clone, 'session_lock_check.py')
        shutil.copyfile(REAL_TOOL, tool)
        with open(REAL_TOOL, 'rb') as f:
            original = f.read()
        with open(tool, 'rb') as f:
            copied = f.read()
        if copied != original:
            refuse('the copy under test is not byte-identical to the real tool')
        lock_dir = os.path.join(tmp, 'locks')
        lock_file = os.path.join(lock_dir, 'probeclone.lock')

        # Two genuinely running processes to stand in for two CLI sessions.
        for _ in range(2):
            children.append(subprocess.Popen(
                [sys.executable, '-c', 'import time; time.sleep(600)']))
        pid_a, pid_b = children[0].pid, children[1].pid
        if pid_a == pid_b:
            refuse('the two stand-in processes share a pid')

        # The module itself, for the arms that need to break a dependency.
        os.environ['SAIRN_SESSION_LOCK_DIR'] = lock_dir
        spec = importlib.util.spec_from_file_location('slc_under_test', tool)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if mod.LOCK_DIR != lock_dir:
            refuse('the module under test did not pick up the temp lock dir')
        if mod.clone_name() != 'probeclone':
            refuse('the module under test claims %r, not probeclone'
                   % mod.clone_name())

        state, sig_a, how = mod.process_start_sig(pid_a)
        if state != 'found':
            refuse('could not read a start time for a process this probe just '
                   'started (%s, via %s) -- liveness is untestable here'
                   % (sig_a, how))
        print('start-time source: %s; pid %d -> %s\n' % (how, pid_a, sig_a))

        # ── (a) same session: tool use proceeds ──────────────────────────────
        print('(a) one session, its own lock')
        run(tool, 'start', pid_a, lock_dir)
        info = json.load(open(lock_file, encoding='utf-8'))
        check('start records CLAUDE_PID, not the hook pid',
              info.get('claude_pid') == pid_a,
              'claude_pid=%s hook pid=%s' % (info.get('claude_pid'),
                                             info.get('pid')))
        check('start records the owner start-time signature',
              str(info.get('claude_start')) == str(sig_a),
              'lock says %s' % info.get('claude_start'))
        check('guard allows the session that owns the lock',
              decision(run(tool, 'guard', pid_a, lock_dir)) == 'silent')

        # ── (b) a second LIVE session in the same clone: refused ─────────────
        print('(b) a second live session in the same clone')
        second = run(tool, 'guard', pid_b, lock_dir)
        check('guard DENIES the second live session',
              decision(second) == 'deny')
        reason = json.loads(second.stdout or '{}').get(
            'hookSpecificOutput', {}).get('permissionDecisionReason', '')
        check('the refusal names the live pid and says it is not a stale lock',
              str(pid_a) in reason and 'stale' in reason.lower())
        start_second = run(tool, 'start', pid_b, lock_dir)
        check('SessionStart still warns the second session',
              decision(start_second) == 'context')
        still = json.load(open(lock_file, encoding='utf-8'))
        check('SessionStart does NOT steal a live owner\'s lock',
              still.get('claude_pid') == pid_a,
              'lock now names %s' % still.get('claude_pid'))

        # ── (c1) the owner really died ───────────────────────────────────────
        print('(c1) the lock owner crashed')
        children[0].kill()
        children[0].wait(timeout=30)
        dead = run(tool, 'guard', pid_b, lock_dir)
        check('guard does NOT refuse over a dead owner',
              decision(dead) != 'deny',
              'decision was %s' % decision(dead))
        reclaimed = json.load(open(lock_file, encoding='utf-8'))
        check('the dead owner\'s lock is reclaimed immediately',
              reclaimed.get('claude_pid') == pid_b,
              'lock now names %s' % reclaimed.get('claude_pid'))

        # ── (c2) the owner died and its pid was recycled ─────────────────────
        # pid_b is genuinely alive; the signature stored beside it is not its
        # own. That is exactly what a recycled pid looks like from here.
        print('(c2) the owner died and something unrelated took its pid')
        pid_c = children[1].pid  # alive, and about to be mislabelled
        wrong_sig = int(mod.process_start_sig(pid_c)[1]) + 1
        mod.write_lock(lock_file, {'pid': 1, 'claude_pid': pid_c,
                                   'claude_start': wrong_sig,
                                   'started': 'synthetic', 'task': ''})
        planted = json.load(open(lock_file, encoding='utf-8'))
        if planted.get('claude_start') != wrong_sig:
            refuse('the recycled-pid fixture did not land on disk')
        # A third process, so the caller is not the mislabelled pid itself.
        children.append(subprocess.Popen(
            [sys.executable, '-c', 'import time; time.sleep(600)']))
        pid_d = children[-1].pid
        recycled = run(tool, 'guard', pid_d, lock_dir)
        check('a recycled pid is NOT mistaken for a live session',
              decision(recycled) != 'deny',
              'decision was %s' % decision(recycled))
        check('and the stale lock is reclaimed',
              json.load(open(lock_file, encoding='utf-8')
                        ).get('claude_pid') == pid_d)

        # ── (d1) the liveness query itself fails ─────────────────────────────
        print('(d1) both start-time methods fail')
        mod.write_lock(lock_file, {'pid': 1, 'claude_pid': pid_c,
                                   'claude_start': mod.process_start_sig(pid_c)[1],
                                   'started': 'synthetic', 'task': ''})
        real_ctypes, real_ps = mod._start_sig_ctypes, mod._start_sig_powershell

        def blown(pid):
            raise OSError('probe: ctypes path deliberately broken')

        mod._start_sig_ctypes = blown
        mod._start_sig_powershell = lambda pid: ('unknown',
                                                 'probe: powershell broken')
        try:
            state, detail, how = mod.process_start_sig(pid_c)
            check('the sabotage applied -- start-time reads now fail',
                  state == 'unknown' and how == 'powershell',
                  'got %s via %s' % (state, how))
            os.environ['CLAUDE_PID'] = str(pid_d)
            verdict, why = mod.owner_state(
                json.load(open(lock_file, encoding='utf-8')))
            check('unknown liveness is UNKNOWN, never DEAD and never ALIVE',
                  verdict == mod.UNKNOWN, '%s: %s' % (verdict, why))
            out = io.StringIO()
            try:
                with contextlib.redirect_stdout(out):
                    mod.cmd_guard()
            except SystemExit:
                pass
            except Exception as exc:
                check('guard survives a failed liveness query', False,
                      '%s: %s' % (type(exc).__name__, exc))
            else:
                check('guard survives a failed liveness query', True)
            check('and falls back to staleness rather than refusing',
                  'deny' not in out.getvalue(),
                  out.getvalue().strip()[:80])
        finally:
            mod._start_sig_ctypes, mod._start_sig_powershell = real_ctypes, real_ps

        # ── (d2) no CLAUDE_PID at all ────────────────────────────────────────
        print('(d2) CLAUDE_PID is not in the environment')
        mod.write_lock(lock_file, {'pid': 1, 'claude_pid': pid_c,
                                   'claude_start': mod.process_start_sig(pid_c)[1],
                                   'started': 'synthetic', 'task': ''})
        blind = run(tool, 'guard', None, lock_dir)
        check('a session with no CLAUDE_PID is not refused',
              decision(blind) != 'deny', 'decision was %s' % decision(blind))
        check('and the hook still exits cleanly', blind.returncode == 0,
              'rc=%s %s' % (blind.returncode, (blind.stderr or '')[:80]))

        # ── (e) the control that makes (b) fail ──────────────────────────────
        print('(e) ablation: does the liveness verdict cause the refusal?')
        mod.write_lock(lock_file, {'pid': 1, 'claude_pid': pid_c,
                                   'claude_start': mod.process_start_sig(pid_c)[1],
                                   'started': 'synthetic', 'task': ''})
        os.environ['CLAUDE_PID'] = str(pid_d)
        out = io.StringIO()
        try:
            with contextlib.redirect_stdout(out):
                mod.cmd_guard()
        except SystemExit:
            pass
        before = 'deny' in out.getvalue()
        check('with liveness intact, that same state DOES refuse', before,
              'the ablation below proves nothing if this is False')
        real_owner_state = mod.owner_state
        mod.owner_state = lambda info: (mod.UNKNOWN, 'probe: ablated')
        try:
            if mod.owner_state({})[0] != mod.UNKNOWN:
                refuse('the ablation did not take effect')
            out = io.StringIO()
            try:
                with contextlib.redirect_stdout(out):
                    mod.cmd_guard()
            except SystemExit:
                pass
            check('ablating the liveness verdict removes the refusal',
                  'deny' not in out.getvalue())
        finally:
            mod.owner_state = real_owner_state
    finally:
        for child in children:
            try:
                child.kill()
                child.wait(timeout=10)
            except Exception:
                pass
        shutil.rmtree(tmp, ignore_errors=True)

    print('\n%d arms, %d failed' % (arms, len(failures)))
    for name in failures:
        print('  FAILED: ' + name)
    sys.exit(1 if failures else 0)


if __name__ == '__main__':
    main()
