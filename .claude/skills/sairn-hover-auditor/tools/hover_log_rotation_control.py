#!/usr/bin/env python
"""Sabotage control for hover_log.py's rotation interlock. Built 2026-09-16.

WHY THIS FILE EXISTS. The gate it tests was built to fix a real, measured
defect -- 20 adjacent same-target repeats, rising from 11.6% to 34.1% of
transitions. A gate that has never been shown to REFUSE is not a gate; it is a
function that has only ever been observed returning None. Every check below
states its expectation as a literal BEFORE the call, and roughly half expect a
REFUSAL, so a gate stuck permanently open fails this suite loudly rather than
passing it silently.

Two properties are checked and are NOT the same claim, named separately:
  (1) the gate returns the right VERDICT for a given prior-log shape, and
  (2) on a refusal, NOTHING IS APPENDED -- a gate that refuses in its message
      while still writing the row would pass (1) and be useless.

Run: python hover_log_rotation_control.py
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone

import hover_log

HERE = os.path.dirname(os.path.abspath(__file__))


def ts_ago(seconds):
    return (datetime.now(timezone.utc) - timedelta(seconds=seconds)).strftime('%Y-%m-%dT%H:%M:%SZ')


def row(seq, etype, target, ts, prev_hash='x' * 64):
    e = {
        'seq': seq, 'ts': ts, 'type': etype, 'target': target,
        'summary': 'fixture', 'severity': '', 'ref': '', 'vector': '',
        'retrospective': False, 'prev_hash': prev_hash,
    }
    e['hash'] = hover_log.digest_of(prev_hash, e)
    return e


# ── (1) VERDICT CONTROL ──────────────────────────────────────────────────────
# (label, prior rows, new etype, new target, reason, EXPECTED_REFUSAL)
VERDICT_CASES = [
    ('different target -> allowed',
     [row(1, 'check', 'hank', ts_ago(600))], 'check', 'cc', '', False),

    ('SAME target, no reason -> REFUSED',
     [row(1, 'check', 'hank', ts_ago(600))], 'check', 'hank', '', True),

    ('same target WITH a declared reason -> allowed',
     [row(1, 'check', 'hank', ts_ago(600))], 'check', 'hank', 're-verifying the fix I just flagged', False),

    ('check->finding same target within 2s -> allowed, no reason needed',
     [row(1, 'check', 'hank', ts_ago(1))], 'finding', 'hank', '', False),

    ('check->finding same target after 600s -> REFUSED (two picks, not one review)',
     [row(1, 'check', 'hank', ts_ago(600))], 'finding', 'hank', '', True),

    ('finding->check same target at 0s (reversed order) -> REFUSED',
     [row(1, 'finding', 'hank', ts_ago(0))], 'check', 'hank', '', True),

    ('target self repeated -> allowed (self is outside the rotation)',
     [row(1, 'finding', 'self', ts_ago(600))], 'finding', 'self', '', False),

    ("type note on the same target -> allowed (not a rotation decision)",
     [row(1, 'check', 'hank', ts_ago(600))], 'note', 'hank', '', False),

    ('LOOPHOLE CONTROL: a self entry between two hank checks must NOT unlock it',
     [row(1, 'check', 'hank', ts_ago(900)), row(2, 'finding', 'self', ts_ago(600))],
     'check', 'hank', '', True),

    ('LOOPHOLE CONTROL: a note between two hank checks must NOT unlock it',
     [row(1, 'check', 'hank', ts_ago(900)), row(2, 'note', 'hank', ts_ago(600))],
     'check', 'hank', '', True),

    ('FAIL CLOSED: unparseable prev timestamp on a check->finding -> REFUSED',
     [row(1, 'check', 'hank', 'not-a-timestamp')], 'finding', 'hank', '', True),

    ('empty log -> allowed (nothing to repeat)',
     [], 'check', 'hank', '', False),

    ('whitespace-only reason does not count as declared -> REFUSED',
     [row(1, 'check', 'hank', ts_ago(600))], 'check', 'hank', '   ', True),
]


def run_verdict_control():
    failures = []
    for label, prior, etype, target, reason, expect_refusal in VERDICT_CASES:
        err = hover_log.rotation_gate(prior, etype, target, reason)
        got_refusal = err is not None
        if got_refusal != expect_refusal:
            failures.append('%s -- expected refusal=%s, got %s' % (label, expect_refusal, got_refusal))
    return len(VERDICT_CASES), failures


# ── (2) NOTHING-IS-APPENDED CONTROL ──────────────────────────────────────────
def run_append_control():
    """Drives the REAL CLI against a throwaway log. A gate that refuses in its
    message while still writing the row would pass the verdict control above
    and still be worthless, so this is checked separately rather than assumed.
    """
    failures = []
    tmp = tempfile.mkdtemp(prefix='hover-gate-control-')
    try:
        log = os.path.join(tmp, 'hover-audit-log.jsonl')
        env = dict(os.environ, PYTHONIOENCODING='utf-8')

        def cli(args):
            code = (
                'import sys; sys.path.insert(0,%r); import hover_log; '
                'hover_log.LOG_PATH=%r; sys.exit(hover_log.cmd_add(sys.argv[1:]))'
                % (HERE, log)
            )
            return subprocess.run([sys.executable, '-c', code] + args,
                                  capture_output=True, text=True, env=env, encoding='utf-8')

        def lines():
            return sum(1 for l in open(log, encoding='utf-8')) if os.path.isfile(log) else 0

        r = cli(['--type', 'check', '--target', 'hank', '--summary', 'first'])
        if lines() != 1:
            failures.append('first entry did not append (rc=%s, out=%r)' % (r.returncode, r.stdout))

        before = lines()
        r = cli(['--type', 'check', '--target', 'hank', '--summary', 'repeat, no reason'])
        if r.returncode == 0:
            failures.append('REFUSAL EXPECTED but exit code was 0')
        if 'ROTATION GATE: REFUSED' not in (r.stdout or ''):
            failures.append('refusal message missing from stdout: %r' % (r.stdout or '')[:120])
        if lines() != before:
            failures.append('GATE WROTE THE ROW ANYWAY -- refused in message, appended in fact')

        r = cli(['--type', 'check', '--target', 'hank', '--summary', 'repeat, declared',
                 '--same-target-reason', 're-verifying the fix I just flagged'])
        if r.returncode != 0 or lines() != before + 1:
            failures.append('declared repeat was not accepted (rc=%s)' % r.returncode)
        else:
            last = json.loads(open(log, encoding='utf-8').read().strip().split('\n')[-1])
            if last.get('same_target_reason') != 're-verifying the fix I just flagged':
                failures.append('declared reason was not STORED in the entry: %r'
                                % last.get('same_target_reason'))

        vcode = ('import sys; sys.path.insert(0,%r); import hover_log; '
                 'hover_log.LOG_PATH=%r; sys.exit(hover_log.cmd_verify([]))' % (HERE, log))
        r = subprocess.run([sys.executable, '-c', vcode], capture_output=True, text=True,
                           env=env, encoding='utf-8')
        if 'VERIFIED' not in (r.stdout or ''):
            failures.append('chain did not verify after gated writes: %r' % (r.stdout or '')[:160])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return failures


def main():
    n, vfail = run_verdict_control()
    afail = run_append_control()
    print('VERDICT CONTROL: %d cases, %d failed' % (n, len(vfail)))
    for f in vfail:
        print('   FAIL', f)
    print('APPEND CONTROL: %d failed' % len(afail))
    for f in afail:
        print('   FAIL', f)
    ok = not vfail and not afail
    print('\n%s' % ('ALL ROTATION-GATE CONTROLS PASS' if ok else 'ROTATION-GATE CONTROLS FAILED'))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
