#!/usr/bin/env python3
"""tools/claim_activity_check.py must not call an EXPIRED claim an ACTIVE one.

    python tests/run_claim_activity_probe.py

Exit 0 all arms pass, 1 an arm failed, 2 COULD NOT RUN.

── THE DEFECT THESE ARMS EXIST FOR ────────────────────────────────────────
`active_claims()` selected on `c.get('status') == 'active'` -- the RAW field
in the claim file. That field is only half the answer. `sairn_claim.py`'s own
`is_active()` also applies the four-hour staleness rule (and a liveness check
on the owning process where the registry stamped one), and says so at its own
call site: "Uses is_active(), not the raw status field: an EXPIRED claim is
one this..." The sibling tool makes the distinction; this one did not.

MEASURED ON THE LIVE CLAIM FILES THE DAY IT WAS FIXED: 13 records carry
`status: active` and `is_active()` is true for TWO. So eleven of thirteen were
being described as "active NNh and NO commit has touched its declared files"
when they had expired hours or days earlier and were blocking nobody --
`sairn_claim.py check` already ignores them. Every finding the tool produced
that day was of that shape, which makes it a false-finding generator: the
report was non-empty, plausible, and pointed at nothing anybody could act on
in the way the sentence implied.

EXPIRED-BUT-UNRELEASED IS A REAL STATE AND IS NOT DELETED HERE. It is clutter
worth clearing and `sairn_claim.py` already names it as a third answer. What
it must not be is folded into the one that means "a session is holding this
right now and has stopped working" -- those call for different actions by
different people, which is the whole of PR 1.11 one domain over.

── HOW THE FIXTURES DRIVE IT ──────────────────────────────────────────────
SAIRN_CLAIM_DIR points the tool at a constructed claim directory instead of
the live one, the same affordance `SAIRN_TIER_REGISTER` gives
criticality_tier_check.py and for the same reason: the real directory changes
under the test and cannot be made to hold a known shape.

The declared paths are deliberately absent from git history, so
`touched_since` answers False rather than None -- a genuinely quiet file set,
which is the input the finding is about.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(REPO, 'tools', 'claim_activity_check.py')

fails = []


def check(name, ok, detail=''):
    print('  %s %s' % ('ok  ' if ok else 'FAIL', name))
    if not ok:
        print('       ' + str(detail)[:400])
        fails.append(name)


def claim(cid, session, age_hours, files_text):
    return {
        'id': cid, 'session': session, 'subject': cid,
        'claimed_at': time.strftime('%Y-%m-%dT%H:%M:%SZ',
                                    time.gmtime(time.time() - age_hours * 3600)),
        'claimed_at_epoch': time.time() - age_hours * 3600,
        'status': 'active', 'released_at': None, 'files': None,
        'task': 'fixture work FILES: ' + files_text,
    }


def write_dir(claims_by_session):
    d = tempfile.mkdtemp(prefix='claimprobe-')
    for session, claims in claims_by_session.items():
        io.open(os.path.join(d, session + '.json'), 'w', encoding='utf-8').write(
            json.dumps({'session': session, 'claims': claims}, indent=1))
    return d


def run(tool, claim_dir, *extra):
    env = dict(os.environ)
    env['SAIRN_CLAIM_DIR'] = claim_dir
    env['PYTHONIOENCODING'] = 'utf-8'
    r = subprocess.run([sys.executable, tool, '--json'] + list(extra),
                       cwd=REPO, capture_output=True, text=True,
                       encoding='utf-8', errors='replace', env=env, timeout=180)
    try:
        return r.returncode, json.loads(r.stdout or '{}'), r.stderr
    except ValueError:
        return r.returncode, None, (r.stdout or '') + (r.stderr or '')


QUIET = 'docs/zzz-claim-probe-never-committed-a.md docs/zzz-claim-probe-never-committed-b.md'

print('claim_activity_check -- an EXPIRED claim is not an ACTIVE one')

# ── 0. THE FIXTURE AFFORDANCE ITSELF ───────────────────────────────────────
# Without this the arms below would silently run against the LIVE claim
# directory and pass or fail on whatever three other sessions happen to hold,
# which is a probe measuring the weather.
both = write_dir({'alpha': [claim('alpha-live', 'alpha', 0.1, QUIET)],
                  'beta': [claim('beta-old', 'beta', 100.0, QUIET)]})
rc, js, err = run(TOOL, both, '--hours', '0')
check('0. SAIRN_CLAIM_DIR points the tool at a constructed directory -- '
      'without it every arm here is measuring the live claim files',
      js is not None and isinstance(js.get('rows'), list)
      and {r.get('id') for r in js['rows']} <= {'alpha-live', 'beta-old'},
      'rc=%s out=%s err=%s' % (rc, js, err))

if js is None:
    print('\nCOULD NOT RUN -- the tool did not produce JSON.')
    sys.exit(2)

rows = {r.get('id'): r for r in js.get('rows', [])}

# ── 1. THE LIVE CLAIM IS STILL FOUND ───────────────────────────────────────
# The fix must not be a narrower reader that reports nothing. This is the
# paired positive.
check('1. a LIVE claim with quiet declared files is still reported NO ACTIVITY '
      '-- the fix is not a reader that sees less',
      rows.get('alpha-live', {}).get('state') == 'NO ACTIVITY',
      'got %r' % (rows.get('alpha-live'),))

# ── 2. THE EXPIRED CLAIM IS A DIFFERENT STATE ──────────────────────────────
check('2. an EXPIRED-but-unreleased claim is NOT reported as NO ACTIVITY',
      rows.get('beta-old', {}).get('state') != 'NO ACTIVITY',
      'the 100h claim was described as active with quiet files: %r'
      % (rows.get('beta-old'),))
check('3. ...it is reported under its OWN state, not dropped -- clutter worth '
      'clearing is still worth saying',
      rows.get('beta-old', {}).get('state') == 'EXPIRED',
      'got %r' % (rows.get('beta-old'),))
check('4. ...and its reason says it blocks nobody, so the reader knows which '
      'action this calls for',
      'block' in (rows.get('beta-old', {}).get('why') or '').lower(),
      'why=%r' % (rows.get('beta-old', {}).get('why'),))

# ── 5. THE EXIT CODE FOLLOWS THE LIVE FINDINGS ONLY ────────────────────────
# A repo carrying eleven ancient unreleased claims would otherwise exit 1
# forever, which is a check that only ever says one thing.
only_old = write_dir({'beta': [claim('beta-old', 'beta', 100.0, QUIET)]})
rc_old, js_old, err_old = run(TOOL, only_old, '--hours', '0')
check('5. EXPIRED rows alone do not set the exit code -- a repo full of ancient '
      'unreleased claims must not leave this check red forever',
      rc_old == 0, 'rc=%s rows=%s err=%s'
      % (rc_old, js_old and js_old.get('rows'), err_old))
check('6. ...but the EXPIRED row is still in the report',
      js_old is not None
      and any(r.get('id') == 'beta-old' for r in js_old.get('rows', [])),
      'rows=%s' % (js_old and js_old.get('rows'),))

only_live = write_dir({'alpha': [claim('alpha-live', 'alpha', 0.1, QUIET)]})
rc_live, js_live, _e = run(TOOL, only_live, '--hours', '0')
check('7. a LIVE finding DOES set the exit code',
      rc_live == 1, 'rc=%s rows=%s' % (rc_live, js_live and js_live.get('rows')))

# ── 8. THE KNOWN-BAD CONTROL ───────────────────────────────────────────────
# Arms 2-4 would pass against a tool that reported nothing at all, and arm 1
# would pass against one that reported everything as NO ACTIVITY. Neither can
# pass against BOTH halves at once -- but a control that puts the defect back
# is the only thing that proves these arms see it rather than merely agreeing
# with today's output.
src = io.open(TOOL, encoding='utf-8').read()
MARK = "live = _claim_is_active(c)"
# THE ABLATED COPY LIVES IN tests/, NOT IN A TEMP DIRECTORY, and that is not
# tidiness. The tool derives REPO from its own __file__ and runs `git log` in
# it; from a temp directory REPO is wrong, git refuses, and every row comes
# back COULD NOT TELL -- which is a control that fails for a reason that has
# nothing to do with the defect it is planting. tests/ is one level under the
# repo root, exactly like tools/, so REPO resolves correctly. Removed in the
# `finally` below, and arm 10 asserts the clone is clean afterwards.
bad_tool = os.path.join(REPO, 'tests', '_ablated_claim_activity_probe_tmp.py')
if MARK not in src:
    check('8. KNOWN-BAD CONTROL: the ablation anchor is present in the tool',
          False,
          'expected %r in tools/claim_activity_check.py. The liveness call was '
          'renamed or removed, so this control CANNOT plant the defect and arms '
          '1-7 are unguarded. Re-derive the anchor; do not delete this arm.'
          % MARK)
else:
    try:
        io.open(bad_tool, 'w', encoding='utf-8').write(
            src.replace(MARK, "live = True  # ABLATED: the raw-status rule"))
        rc_b, js_b, err_b = run(bad_tool, both, '--hours', '0')
        bad_rows = {r.get('id'): r for r in (js_b or {}).get('rows', [])}
        check('8. KNOWN-BAD CONTROL: with the liveness check ablated to the '
              'raw-status rule, the 100h claim is reported NO ACTIVITY again -- '
              'so arms 2-4 are reading the fix and not agreeing with an empty '
              'report',
              bad_rows.get('beta-old', {}).get('state') == 'NO ACTIVITY',
              'the ablated tool did NOT reproduce the defect, so the arms above '
              'prove nothing: rc=%s rows=%r err=%s'
              % (rc_b, bad_rows, (err_b or '')[:300]))
        check('8b. ...and the ablated copy still finds the LIVE one, so arm 8 '
              'is planting the defect rather than breaking the tool',
              bad_rows.get('alpha-live', {}).get('state') == 'NO ACTIVITY',
              'got %r' % (bad_rows.get('alpha-live'),))
    finally:
        if os.path.exists(bad_tool):
            os.remove(bad_tool)

# ── 9. FAIL CLOSED WHEN THE LIVENESS RULE CANNOT BE IMPORTED ───────────────
# PR 1.11. Falling back to the raw status field would be the defect restored
# under a different name, and it would report a pass it never performed.
no_sibling = tempfile.mkdtemp(prefix='claimprobe-nosib-')
lone = os.path.join(no_sibling, 'claim_activity_check.py')
io.open(lone, 'w', encoding='utf-8').write(src)
rc_n, js_n, err_n = run(lone, both, '--hours', '0')
check('9. FAILS CLOSED when sairn_claim.py cannot be imported -- exit 2 and a '
      'sentence, never a fallback to the raw status field',
      rc_n == 2 and 'sairn_claim' in (err_n or ''),
      'rc=%s stderr=%s' % (rc_n, (err_n or '')[:300]))

# ── 10. THIS PROBE LEFT NOTHING BEHIND ─────────────────────────────────────
# Arm 8 writes a file into tests/. A probe that can leave a mutated repo is
# worse than no probe, and the one thing nobody checks after a green run is
# whether the clone is still clean.
check('10. the ablated copy was removed -- this probe leaves the clone clean',
      not os.path.exists(bad_tool),
      '%s survived the run and would be committed by the next `git add -A`'
      % bad_tool)

for d in (both, only_old, only_live, no_sibling):
    shutil.rmtree(d, ignore_errors=True)

print('\n%s  run_claim_activity_probe: %d failed'
      % ('FAILED' if fails else 'ok', len(fails)))
sys.exit(1 if fails else 0)
