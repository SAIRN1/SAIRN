"""A RELEASED claim must not be invisible to `check`.

    python tests/claims/run_released_visibility_probe.py

WHY THIS EXISTS, and it is two real near-misses on one day rather than a
hypothetical. `sairn_claim.py check` reported CLEAR on work another session had
FINISHED minutes earlier, twice on 2026-09-10 and in both directions:

  * cody claimed `sairnbiz-sb-incidents-kpi-with-no-write-path` 57 seconds
    after that work was pushed and the claim released. Released at 13:21:22
    after being claimed at 13:20:25 -- the whole episode lasted under a minute
    because cody read `git log`, not because this tool said anything.
  * hank had a claim written for the local-only wrapper false-clean and was
    reading `_server_calling_functions()` when the fix turned up already there,
    authored by cc hours earlier. Again found by reading history.

THE GAP IS STRUCTURAL, NOT A BUG. An ACTIVE claim blocks. An EXPIRED one is
reported, with a note saying it may mean the work was done. The SUCCESSFUL
case -- a claim released the moment the work landed -- was the one state the
tool said nothing about at all. **The better a session behaves, the less its
finished work warns anybody.**

IT REPORTS, IT DOES NOT BLOCK, and that is deliberate: follow-on work on a
subject somebody just finished is normal and common, and this tool's own rule
is that it flags for a human read rather than deciding. What it must not do is
stay silent. The arms below therefore weight the SILENCE side -- every case
that should produce a note is asserted, and the return code is asserted to stay
0 so a note can never become a block by accident.

Function-level, with synthetic claims. Nothing writes to .claude/claims, for
the reason the matcher probe states: `list` and `check` read that directory, so
a probe that disturbed it could destroy a real uncommitted claim.
"""
import importlib.util
import io
import os
import subprocess
import sys
import time

REPO = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True).stdout.strip()
spec = importlib.util.spec_from_file_location(
    'sairnclaim', os.path.join(REPO, 'tools', 'sairn_claim.py'))
claim = importlib.util.module_from_spec(spec)
spec.loader.exec_module(claim)

fails = 0


def check(label, actual, expected):
    global fails
    if actual == expected:
        print('  ok    %s' % label)
        return True
    fails += 1
    print('FAIL  %s\n        expected %r\n        actual   %r' % (label, expected, actual))
    return False


def iso_ago(hours):
    """An ISO-Z stamp `hours` in the past, in the same shape release() writes."""
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(time.time() - hours * 3600))


def released(session, subject, task, hours):
    return {'session': session, 'subject': subject, 'task': task,
            'status': 'released', 'released_at': iso_ago(hours),
            'claimed_at_epoch': time.time() - (hours + 1) * 3600}


def capture(claims, me, subj, task):
    buf = io.StringIO()
    real = sys.stdout
    sys.stdout = buf
    try:
        claim._report_recent_releases(claims, me, subj, task)
    finally:
        sys.stdout = real
    return buf.getvalue()


# ═══════════════════════════════════════════════════════════════════════════
print('1. released_hours_ago reads what release() writes')

check('a release 2 hours ago reads as ~2h',
      round(claim.released_hours_ago(released('cc', 's', 't', 2)) or -1), 2)
check('a release just now reads as ~0h',
      round(claim.released_hours_ago(released('cc', 's', 't', 0)) or -1), 0)
check('an ACTIVE claim has no release age',
      claim.released_hours_ago({'status': 'active', 'subject': 's'}), None)
check('a released claim with no timestamp is None, not a crash',
      claim.released_hours_ago({'status': 'released', 'subject': 's'}), None)
check('an unparseable timestamp is None, not a crash',
      claim.released_hours_ago({'status': 'released', 'released_at': 'last tuesday'}), None)

# The tool runs on every claim, check and list, in four clones. A parse failure
# here must degrade to saying nothing rather than taking the claim tool down.
check('a released_at of the wrong TYPE is survivable',
      claim.released_hours_ago({'status': 'released', 'released_at': 12345}), None)

# ═══════════════════════════════════════════════════════════════════════════
print('\n2. THE TWO REAL NEAR-MISSES now produce a note')

# cody's real claim string, and the task hank had just finished and released.
sairnbiz = [released('cody', 'sairnbiz-sb-incidents-kpi-with-no-write-path', '', 0.02)]
out = capture(sairnbiz, 'hank', 'sairnbiz', 'sb_incidents safety kpi with no write path')
check('the SAIRNbiz case is named', 'sairnbiz-sb-incidents-kpi-with-no-write-path' in out, True)
check('and it names WHO finished it', 'cody' in out, True)
check('and it says how long ago', 'finished 0.0h ago' in out, True)

localonly = [released('cc', 'local_only_collection_check.py', 'wrapper own signature', 3)]
out = capture(localonly, 'hank', 'tool-wrapper-heuristic-false-clean',
              'local_only_collection_check.py excuses one-line saveX wrappers')
check('the local-only checker case is named', 'local_only_collection_check.py' in out, True)

# ═══════════════════════════════════════════════════════════════════════════
print('\n3. it stays quiet when it should')

check('my OWN released claim is not reported back at me',
      capture([released('hank', 'sairnbiz-osha', 'x', 1)], 'hank', 'sairnbiz', 'osha'), '')
check('an unrelated subject produces nothing',
      capture([released('cc', 'sairnlaw-holiday-calendar', 'x', 1)],
              'hank', 'stonedesk-drawing-tool', 'chamfer snap'), '')
check('a release OLDER than the window is not reported',
      capture([released('cc', 'sairnbiz-sb-incidents', 'x', claim.RECENT_RELEASE_HOURS + 1)],
              'hank', 'sairnbiz', 'sb_incidents'), '')
check('an ACTIVE claim is not reported here -- that is the blocking path',
      capture([{'session': 'cc', 'subject': 'sairnbiz', 'task': 'sb_incidents',
                'status': 'active', 'claimed_at_epoch': time.time()}],
              'hank', 'sairnbiz', 'sb_incidents'), '')
check('a release in the FUTURE (clock skew) is ignored rather than shown as negative',
      capture([released('cc', 'sairnbiz-sb-incidents', 'x', -5)],
              'hank', 'sairnbiz', 'sb_incidents'), '')

# ═══════════════════════════════════════════════════════════════════════════
print('\n4. IT MUST NEVER BLOCK -- a note that becomes a gate is a different tool')

out = capture(sairnbiz, 'hank', 'sairnbiz', 'sb_incidents safety kpi')
check('the note says it is not blocking', 'Not blocking' in out, True)
check('the note tells the reader what to actually do', 'READ THE COMMIT' in out, True)
check('and it does not use the word that stops a session', 'DO NOT start this' in out, False)

# The whole `check` path must still exit 0 on a CLEAR-with-a-note. Driven
# through the real CLI so a wiring mistake in cmd_check cannot hide behind a
# function-level pass -- the lesson tools/sairn_claim_hook.py taught on
# 2026-09-04, where the fix reached the copy a human invokes and missed the one
# that runs unattended.
r = subprocess.run([sys.executable, os.path.join(REPO, 'tools', 'sairn_claim.py'),
                    'check', 'zz-probe-subject-that-matches-nothing'],
                   capture_output=True, text=True, cwd=REPO)
check('the real CLI still exits 0 on a clear check', r.returncode, 0)
check('and still prints CLEAR', 'CLEAR' in r.stdout, True)

print()
if fails:
    print('%d FAILED' % fails)
    sys.exit(1)
print('ALL PASS -- a released claim is no longer invisible, and still does not block.')
