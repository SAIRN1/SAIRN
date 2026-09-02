"""Prove the CHECK-constraint comparison catches the defect it was built for.

THE DEFECT IT EXISTS FOR, replanted here exactly: SAIRNdental's
dnt_appointments enforced `octet_length(data::text) <= 65536` in production
while sql/sairndental_data_schema.sql had been raised to 1291059 and a
migration sat written-but-unrun. Nothing on the platform could see it.

A checker that has only ever returned clean is unproven, so every outcome is
exercised: a match, a drift, an absent constraint, an absent table, and a
snapshot with no constraint data at all. The last two must report
COULD-NOT-CHECK rather than clean -- "the checker said nothing" and "the
checker could not look" must never be the same output.
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))), 'tools'))
import sairn_sql_preflight as P  # noqa: E402

R = {}

# The real declared constraint, read from the repo rather than retyped.
declared_all = P.declared_constraints()
dnt = declared_all.get('dnt_appointments', {})
R['reads_the_real_declared_constraint'] = ('dntap_data_size' in dnt
                                           and '1291059' in dnt['dntap_data_size'])


def snap(constraints):
    fd, path = tempfile.mkstemp(suffix='.json')
    with os.fdopen(fd, 'w', encoding='utf-8') as fh:
        json.dump({'_generated_at': 'probe', '_constraints': constraints,
                   'dnt_appointments': ['id', 'data']}, fh)
    return path


def run(constraints, declared=None):
    p = snap(constraints)
    try:
        return P.constraint_findings(declared or {'dnt_appointments': dnt},
                                     P.load_live_constraints(p))
    finally:
        os.remove(p)


# 1. MATCH -- Postgres's own rendering, with the parens it adds. Must be clean.
f, u = run({'dnt_appointments': {
    'dntap_data_size': 'CHECK ((octet_length((data)::text) <= 1291059))'}})
R['postgres_rendering_is_not_drift'] = (f == [] and u == [])

# 2. THE REAL DEFECT -- live still at the old 64 KiB ceiling.
f, u = run({'dnt_appointments': {
    'dntap_data_size': 'CHECK ((octet_length((data)::text) <= 65536))'}})
R['catches_the_dental_drift'] = (len(f) == 1 and f[0][0] == 'CONSTRAINT_DRIFT'
                                 and '65536' in f[0][3] and '1291059' in f[0][3])

# 3. Constraint absent from the live table entirely.
f, u = run({'dnt_appointments': {}})
R['catches_a_missing_constraint'] = (len(f) == 1 and f[0][0] == 'MISSING_CONSTRAINT')

# 4. Table absent from the snapshot -- unchecked, NOT clean.
f, u = run({'some_other_table': {'x': 'CHECK (true)'}})
R['absent_table_is_unchecked_not_clean'] = (f == [] and len(u) == 1
                                            and 'could not be compared' in u[0])

# 5. Snapshot with no _constraints key at all -- unchecked, NOT clean.
fd, path = tempfile.mkstemp(suffix='.json')
with os.fdopen(fd, 'w', encoding='utf-8') as fh:
    json.dump({'_generated_at': 'probe', 'dnt_appointments': ['id', 'data']}, fh)
f, u = P.constraint_findings({'dnt_appointments': dnt}, P.load_live_constraints(path))
os.remove(path)
R['no_constraint_data_is_unchecked_not_clean'] = (f == [] and len(u) == 1
                                                  and 're-run' in u[0])

# 6. Underscore metadata keys must not be loaded as tables. This was a real
#    latent bug: load_live() skipped only '_generated_at', so the two
#    _anon_*_baseline keys already in the live snapshot were parsed as tables.
fd, path = tempfile.mkstemp(suffix='.json')
with os.fdopen(fd, 'w', encoding='utf-8') as fh:
    json.dump({'_generated_at': 'probe', '_anon_grant_baseline_2026_08_26': ['a'],
               '_constraints': {}, 'real_table': ['id']}, fh)
schema, _ = P.load_live(path)
os.remove(path)
R['metadata_keys_are_not_tables'] = (set(schema) == {'real_table'})

for k, v in R.items():
    print('%-40s %s' % (k, v))
print()
ok = all(R.values())
print('CONSTRAINT CHECK VERIFIED:', ok)
sys.exit(0 if ok else 1)
