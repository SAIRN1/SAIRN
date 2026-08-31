#!/usr/bin/env python
"""Assert tools/sairn_sql_preflight.py still catches what it is meant to catch.

Run from the repo root:  python tests/sql_preflight/run_probe.py

Every case here corresponds to a defect the tool must find, or to a shape that
produced a FALSE POSITIVE in an earlier draft and must stay clean. The false
positives are the more valuable half: each one was found by hand-checking the
tool's own output against the repo, not by reading the tool, and each would have
been enough on its own to get the checker switched off after one use.

  caught wrongly, then fixed:
    `revoke ... from anon`            -> missing tables `anon`, `service_role`
    `on all tables in schema public`  -> a missing table called `schema`
    `grant execute on function ...`   -> a missing table called `function`
    multi-column ALTER TABLE          -> 4 real dnt_appointments columns called
                                         missing in a live dental app's seed
    `with declared(table_name) as`    -> a missing table called `declared`
    `x is distinct from y`            -> missing tables `tst`, `test_data`
    unqualified pg_class / pg_namespace
    `create temp table X as select`   -> 4 missing `_*_baseline_*` tables

  missed, then fixed:
    `a.last_login_at` where `a` is an alias -- the qualified-reference case went
    unchecked because the alias looked like a CTE name.
"""
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HERE = os.path.join('tests', 'sql_preflight')
TOOL = os.path.join('tools', 'sairn_sql_preflight.py')

SNAPSHOT = {
    "_generated_at": "2026-08-31 09:00:00.000000+00",
    "sairnmechanical_employee_auth": [
        "id", "license_hash", "employee_id", "display_name", "role", "pin_hash",
        "pin_salt", "active", "failed_attempts", "locked_until", "created_at", "updated_at"],
    "license_keys": ["id", "key", "status", "customer_email", "app_id", "plan",
                     "stripe_subscription_id"],
}

EXPECTED_DEFECTS = {
    'MISSING_COLUMN sairnmechanical_employee_auth.pin_plaintext',   # D1 insert column list
    'MISSING_COLUMN sairnmechanical_employee_auth.is_active',       # D3 update set
    'MISSING_COLUMN sairnmechanical_employee_auth.last_login_at',   # D4 alias-qualified ref
    'MISSING_TABLE sairnmechanical_employee_authz',                 # D2 table typo
}


def run(args):
    p = subprocess.run([sys.executable, TOOL] + args, cwd=ROOT,
                       capture_output=True, text=True)
    return p.returncode, p.stdout


def findings(out):
    got = set()
    for line in out.splitlines():
        line = line.strip()
        for kind in ('MISSING_COLUMN', 'MISSING_TABLE', 'UNDECLARED_TABLE'):
            if line.startswith(kind):
                got.add(' '.join(line.split()))
    return got


def main():
    fd, snap = tempfile.mkstemp(suffix='.json')
    os.close(fd)
    open(snap, 'w', encoding='utf-8').write(json.dumps(SNAPSHOT))
    defects = os.path.join(HERE, 'probe_defects.sql')
    control = os.path.join(HERE, 'probe_control.sql')
    failures = []

    code, out = run(['--live', snap, defects])
    got = findings(out)
    if got != EXPECTED_DEFECTS:
        failures.append('LIVE/defects findings mismatch\n  missed: %s\n  extra : %s'
                        % (sorted(EXPECTED_DEFECTS - got), sorted(got - EXPECTED_DEFECTS)))
    if code != 1:
        failures.append('LIVE/defects exit %d, expected 1' % code)

    code, out = run(['--live', snap, control])
    if findings(out):
        failures.append('LIVE/control should be clean, got: %s' % sorted(findings(out)))
    if code != 0:
        failures.append('LIVE/control exit %d, expected 0' % code)

    # DECLARED must never report 0 -- "could not tell" is not a pass.
    code, _ = run([control])
    if code != 2:
        failures.append('DECLARED/control exit %d, expected 2 (not-a-pass)' % code)

    for args, want in ((['--live', '/nope.json', control], 3),
                       ([], 3),
                       ([os.path.join('sql', 'does_not_exist.sql')], 3)):
        code, _ = run(args)
        if code != want:
            failures.append('args=%s exit %d, expected %d' % (args, code, want))

    os.remove(snap)
    if failures:
        print('FAIL')
        for f in failures:
            print('  ' + f)
        return 1
    print('PASS -- 4 defects caught, control clean, 7 exit codes correct')
    return 0


if __name__ == '__main__':
    sys.exit(main())
