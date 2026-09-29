#!/usr/bin/env python
"""sabotage_closed_system_check.py -- verify, don't assume, that a sabotage
test ran in a closed system: this session, alone, for the whole window.
Built 2026-09-16, the day tools/session_lock_check.py's liveness fix
(a744ceb5) landed and made this checkable for real.

WHY THIS EXISTS. Every sabotage/mutation control this role runs (plant a
defect, confirm the checker catches it, restore, confirm clean) has quietly
assumed no OTHER session touched the same file in the same clone during the
plant-run-restore window. If one had, the "before" and "after" states being
diffed would not be solely this test's doing, and a clean restore-confirmation
could be hiding a real collision rather than proving the sabotage tool works.
This was unverifiable until 2026-09-16: session_lock_check.py's OWN liveness
fix is what makes "who genuinely held this clone, when" a real, checkable
question rather than an assumption -- using the fix to verify the role that
built and deep-passed it is the correct, immediate use of newly-landed
infrastructure, not a coincidence.

WHAT THIS DOES NOT CLOSE, DISCLOSED PLAINLY, SAME DISCIPLINE AS EVERY OTHER
BOUNDARY IN THIS ROLE'S OWN TOOLING. owner_state() answers "does THIS clone's
lock show a different live session" -- it says nothing about a different
CLONE (Hank/CC/Cody/Fourth's own directories) independently touching the SAME
file this sabotage test plants into, which is a real, different, and already-
named-elsewhere risk (the claim system's own subject-collision problem, not
this checker's). This closes the SAME-CLONE, SAME-SESSION-IDENTITY case only
-- the literal shape of the 2026-09-15 incident this fix itself responds to.

Run as a wrapper around any sabotage test:
    python sabotage_closed_system_check.py -- <command to run> [args...]
Exit 0 only if the system was confirmed closed AND the wrapped command
exited 0. Any other outcome -- not closed, could not determine, or the
wrapped command itself failed -- is a non-zero exit with the reason stated,
never silently folded into a pass.
"""

import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = r'C:\Users\marsh\Documents\SAIRN-hover'


def _load_session_lock_check():
    sys.path.insert(0, os.path.join(REPO, 'tools'))
    import session_lock_check as s
    return s


def claim_ownership(s):
    """Same real refusal boundary as cmd_start()/cmd_guard() already use in
    production -- refuse ONLY on a CONFIRMED live different session (ALIVE).
    SELF, DEAD, and UNKNOWN all proceed to (re)write this session's own
    identity, exactly as cmd_start() already does; reinventing a stricter
    rule here would make this tool refuse on an ordinary stale or pre-fix-
    format lock that represents no real competing session at all, which is
    not the same claim as 'the system is not closed'."""
    name = s.clone_name()
    path = s.lock_path(name)
    info = s.read_lock(path) if os.path.exists(path) else None
    if info is not None and not s.is_stale(path):
        state, why = s.owner_state(info)
        if state == s.ALIVE:
            return None, info, why  # refuse -- a real, live, different session
    s.write_lock(path, s.lock_payload())
    return s.read_lock(path), None, None


def read_current(s):
    """Read-only -- does NOT write. Used for the post-test check, so a
    genuine change during the window is visible rather than overwritten."""
    name = s.clone_name()
    path = s.lock_path(name)
    return s.read_lock(path) if os.path.exists(path) else None, s.is_stale(path)


def main():
    if '--' not in sys.argv:
        print('usage: sabotage_closed_system_check.py -- <command> [args...]')
        return 2
    cmd = sys.argv[sys.argv.index('--') + 1:]
    if not cmd:
        print('COULD NOT RUN -- no command given after --')
        return 2

    s = _load_session_lock_check()

    info_before, refused_info, refused_why = claim_ownership(s)
    report = {'clone': s.clone_name()}

    if info_before is None:
        report['verdict'] = 'REFUSED -- did not run the wrapped command'
        report['reason'] = (
            'A different session is CONFIRMED live in this clone right now (%s). '
            'Running a sabotage test under that state means the before/after diff '
            'it produces cannot be trusted to be this test\'s doing alone.'
            % refused_why)
        report['live_owner_info'] = refused_info
        print(json.dumps(report, indent=2))
        return 3

    report['identity_claimed_before'] = info_before

    result = subprocess.run(cmd, cwd=REPO)
    report['wrapped_command'] = cmd
    report['wrapped_exit_code'] = result.returncode

    info_after, was_stale_after = read_current(s)
    report['identity_seen_after'] = info_after
    report['lock_was_stale_after'] = was_stale_after

    identity_unchanged = (
        info_after is not None
        and info_after.get('claude_pid') == info_before.get('claude_pid')
        and info_after.get('claude_start') == info_before.get('claude_start')
    )
    report['identity_unchanged_across_the_window'] = identity_unchanged
    report['CLOSED_SYSTEM_CONFIRMED'] = identity_unchanged
    print(json.dumps(report, indent=2))

    if not identity_unchanged:
        return 4
    return 0 if result.returncode == 0 else result.returncode


if __name__ == '__main__':
    sys.exit(main())
