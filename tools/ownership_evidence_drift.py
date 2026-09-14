#!/usr/bin/env python
"""ownership_evidence_drift.py -- how much of `public` the ownership evidence
does not cover.

    python tools/ownership_evidence_drift.py
    python tools/ownership_evidence_drift.py --json

── THE QUESTION THIS ANSWERS, AND THE ONE IT DOES NOT ─────────────────────
It does NOT tell you who owns anything. That needs a live database and no clone
has credentials for one.

It tells you how far the last OWNERSHIP MEASUREMENT has drifted from the
population it was a measurement of -- which is the question "can the accepted
risk be closed out" actually turns on.

── WHY IT EXISTS ──────────────────────────────────────────────────────────
`supabase_admin`'s default ACL grants `anon` and `authenticated` full CRUD on
tables it creates. That is carried in docs/SAIRN-OPEN-WORK-INDEX.md as an
ACCEPTED RISK, MONITORED, and it is accepted on exactly one piece of evidence:
on 2026-08-26 ownership across `public` was measured at 100% `postgres` --
251 tables, zero `supabase_admin`-owned objects. The entry is real and has
never fired.

**THE ROW NAMES ITS OWN RE-CHECK TRIGGER AND NOTHING EVALUATES IT:** *"RE-CHECK
THIS THE MOMENT ANY OBJECT IN public IS CREATED BY ANYTHING OTHER THAN THE SQL
EDITOR RUNNING AS postgres."* It even names the monitor -- one SELECT -- and
nothing runs it. A tool that exists is not a mechanism; a tool that RUNS is.

So this measures the one thing a clone CAN measure: the gap between the
population that was inspected and the population that exists.

── WHAT A GREEN RUN WOULD AND WOULD NOT MEAN ──────────────────────────────
Zero drift would mean no table has been added since the evidence was taken. It
would still not mean the evidence is current: a table could be DROPPED and
RECREATED by `supabase_admin` with no change in the count at all. The count is
a lower bound on what is unobserved, never a proof that nothing is.

Exit 0 when the drift is zero, 1 when it is not, 2 when it could not run.
"""
import io
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASELINE = os.path.join(REPO, 'tools', 'ownership_evidence_drift.json')
SNAPSHOT = os.path.join(REPO, 'db', 'schema_snapshot.json')
CHECK_SQL = 'sql/supabase_admin_default_acl_check_2026-08-26.sql'
EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN = 0, 1, 2


def load_baseline():
    try:
        d = json.loads(io.open(BASELINE, encoding='utf-8').read())
    except Exception as e:
        return None, '%s: %s' % (type(e).__name__, e)
    ms = d.get('measurements')
    if not isinstance(ms, list) or not ms:
        return None, 'no measurements recorded -- that is a broken file, not a ' \
                     'platform nobody has ever measured'
    # The most recent by date. Sorted rather than "the last element", because an
    # entry appended in the wrong place would otherwise silently become the
    # baseline and UNDERSTATE the drift -- the direction that makes stale
    # evidence look current.
    return sorted(ms, key=lambda m: m.get('measured_at', '')) [-1], None


def load_snapshot():
    try:
        d = json.loads(io.open(SNAPSHOT, encoding='utf-8').read())
    except Exception as e:
        return None, None, '%s: %s' % (type(e).__name__, e)
    tables = [k for k in d if not k.startswith('_')]
    if not tables:
        # A ZERO HERE IS A BROKEN READER, NOT AN EMPTY DATABASE, and reporting
        # zero drift off it would be the most reassuring possible wrong answer.
        return None, None, 'the snapshot parsed to ZERO tables -- that is a ' \
                           'broken reader, not an empty schema'
    return len(tables), d.get('_generated_at'), None


def main(argv):
    base, err = load_baseline()
    if err:
        print('COULD NOT RUN: ' + err)
        return EXIT_COULD_NOT_RUN
    now, captured, err = load_snapshot()
    if err:
        print('COULD NOT RUN: ' + err)
        return EXIT_COULD_NOT_RUN

    then = base.get('tables_in_public')
    if not isinstance(then, int):
        print('COULD NOT RUN: the latest measurement records no tables_in_public')
        return EXIT_COULD_NOT_RUN
    drift = now - then
    pct = (drift * 100.0 / then) if then else 0.0

    if '--json' in argv:
        print(json.dumps({
            'measured_at': base.get('measured_at'),
            'tables_when_measured': then,
            'tables_now': now,
            'unobserved': drift,
            'unobserved_pct': round(pct, 1),
            'snapshot_captured': captured,
        }, indent=2))
        return EXIT_CLEAN if drift <= 0 else EXIT_FINDING

    print('OWNERSHIP EVIDENCE DRIFT -- schema public')
    print('  last MEASURED     : %s  by %s' % (base.get('measured_at'),
                                               base.get('by', '(unrecorded)')))
    print('  tables then       : %d  (100%% postgres, 0 supabase_admin-owned)'
          % then)
    print('  tables now        : %d  (db/schema_snapshot.json, captured %s)'
          % (now, captured))
    print('  UNOBSERVED        : %d tables, %.0f%% growth since the evidence'
          % (drift, pct))
    print('')
    if drift <= 0:
        print('  No table has been added since the ownership evidence was taken.')
        print('  THAT IS NOT THE SAME AS THE EVIDENCE BEING CURRENT: a table can')
        print('  be dropped and recreated by another role with no change in the')
        print('  count. This is a lower bound on what is unobserved, never a')
        print('  proof that nothing is.')
        return EXIT_CLEAN

    print('  THE ACCEPTED RISK CANNOT BE CLOSED OUT ON THIS EVIDENCE.')
    print('  docs/SAIRN-OPEN-WORK-INDEX.md carries supabase_admin\'s default ACL')
    print('  as ACCEPTED RISK, MONITORED, and names its own re-check trigger:')
    print('    "RE-CHECK THIS THE MOMENT ANY OBJECT IN public IS CREATED BY')
    print('     ANYTHING OTHER THAN THE SQL EDITOR RUNNING AS postgres."')
    print('  %d tables have been created since anybody looked, and nothing has'
          % drift)
    print('  evaluated that trigger against a single one of them.')
    print('')
    print('  THIS IS NOT A CLAIM THAT THE ACL HAS FIRED. It almost certainly has')
    print('  not -- every migration on this platform goes through the SQL editor')
    print('  as postgres. It is a statement that nobody has checked, which is a')
    print('  different thing from a clean result and must not read as one.')
    print('')
    print('  AND %d IS ITSELF A LOWER BOUND. A table dropped and recreated by'
          % drift)
    print('  another role changes the count by nothing at all, so this number')
    print('  can only understate what is unobserved, never overstate it.')
    print('')
    print('  TO CLOSE IT: run Section 1 of')
    print('    %s' % CHECK_SQL)
    print('  as postgres -- read-only, one SELECT -- and add the numbers to')
    print('  tools/ownership_evidence_drift.json. A single non-postgres row is')
    print('  the whole alarm.')
    return EXIT_FINDING


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
