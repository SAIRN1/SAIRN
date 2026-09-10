"""Probe tools/schema_provisioning_check.py -- and mostly its FAILURE paths.

WHY THE FAILURE PATHS ARE THE POINT. This checker's whole job is to catch a
partially-run migration, and on the night it was written BOTH migrations it
could reach were complete: SAIRNfreedom 35/35, SAIRNvet 41/41. A checker that
has only ever returned clean is a checker whose behaviour nobody knows -- the
bar tools/discarded_verdict_check.py set and the reason its own probe plants a
defect. There is no live half-migrated app to point this at, so the MISSING,
REFUSED and CHALLENGED paths are driven with stubbed responses instead, and the
stub is honest about being one.

THE THREE ANSWERS THAT ARE NOT A PASS, each asserted separately, because
collapsing them is exactly how a partial migration reads as an empty database:
  MISSING     -- 200 ok:true provisioned:FALSE. The table is not there. This is
                 the finding; the endpoint answers it deliberately so that an
                 un-migrated table is distinguishable from an empty one.
  REFUSED     -- a 4xx. The check did not run for that resource.
  CHALLENGED  -- Vercel bot mitigation. UNVERIFIED, which is not verified-good.

Run: python tests/schema_provisioning_probe.py
"""
import io
import json
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import sairn_http  # noqa: E402
import schema_provisioning_check as C  # noqa: E402

TOOL = os.path.join(REPO, 'tools', 'schema_provisioning_check.py')
results = {}


class FakeResp(object):
    def __init__(self, status, body):
        self.status = status
        self.body = body.encode('utf-8')


# ── ARM 1: the schema file is the source of truth, not the registry ────────
# Reading the registry against itself would prove nothing about the migration.
tables = C.declared_tables(os.path.join(REPO, 'sql', 'sairnfreedom_data_schema.sql'))
results['arm1_reads_35_from_the_schema'] = len(tables) == 35
results['arm1_names_are_tables_not_prose'] = all(t.startswith('sf_') for t in tables)
vet = C.declared_tables(os.path.join(REPO, 'sql', 'sairnvet_data_schema.sql'))
results['arm1_reads_41_for_sairnvet'] = len(vet) == 41

# ── ARM 2: the registry is read with comments stripped ────────────────────
# These files carry long prose; an earlier checker cleared a resource on a word
# in a sentence, and that lesson is one file over.
reg = C.registered('sairnfreedom')
results['arm2_registry_has_35'] = len(reg) == 35
results['arm2_no_prose_words'] = not (reg & {'the', 'and', 'record', 'server'})

# ── ARM 3 (CONTROL): provisioned:false is MISSING, and it is not a pass ───
# The live run cannot produce this -- both migrations are complete -- so it is
# driven with a stub. Without this arm the tool has never once said "missing".
real_fetch = sairn_http.fetch
try:
    sairn_http.fetch = lambda *a, **k: FakeResp(
        200, json.dumps({'ok': True, 'data': [], 'provisioned': False}))
    state, _ = C.probe('sf_members', 'ZZ-KEY', 'sairnfreedom')
    results['arm3_provisioned_false_is_MISSING'] = state == 'MISSING'

    sairn_http.fetch = lambda *a, **k: FakeResp(
        200, json.dumps({'ok': True, 'data': [], 'provisioned': True}))
    state, _ = C.probe('sf_members', 'ZZ-KEY', 'sairnfreedom')
    results['arm3_provisioned_true_is_PROVISIONED'] = state == 'PROVISIONED'

    # ── ARM 4 (CONTROL): a refusal is not a missing table and not a pass ──
    sairn_http.fetch = lambda *a, **k: FakeResp(
        401, json.dumps({'error': {'code': 'INVALID_LICENSE'}}))
    state, detail = C.probe('sf_members', 'ZZ-KEY', 'sairnfreedom')
    results['arm4_401_is_REFUSED_not_missing'] = state == 'REFUSED'
    results['arm4_refusal_names_the_code'] = 'INVALID_LICENSE' in detail

    def _challenge(*a, **k):
        # Constructed with the REAL signature (url, status). My first version
        # passed one string, the constructor raised TypeError, and the tool
        # classified it as UNREADABLE -- so the arm failed on the stub rather
        # than on the code. A control that cannot build the exception it is
        # testing is testing the control.
        raise sairn_http.Challenged(C.URL, 403)
    sairn_http.fetch = _challenge
    state, _ = C.probe('sf_members', 'ZZ-KEY', 'sairnfreedom')
    results['arm4_challenge_is_its_own_state'] = state == 'CHALLENGED'
finally:
    sairn_http.fetch = real_fetch
results['arm4_fetch_restored'] = sairn_http.fetch is real_fetch

# ── ARM 5: no key is exit 2 and says nothing was checked ──────────────────
env = dict(os.environ)
env.pop('SAIRN_LICENSE_KEY', None)
p = subprocess.run([sys.executable, TOOL, '--app', 'sairnfreedom',
                    '--schema', 'sql/sairnfreedom_data_schema.sql'],
                   capture_output=True, text=True, cwd=REPO, env=env)
results['arm5_no_key_exits_2'] = p.returncode == 2
results['arm5_no_key_says_not_a_pass'] = 'not a pass' in (p.stderr or '').lower()

# ── ARM 6: neither --app nor --schema is guessed from the other ───────────
# Schema filenames genuinely differ in shape (sairnvet_data_schema.sql,
# sairndental_vendor_schema.sql), so a guess would check the wrong file.
p = subprocess.run([sys.executable, TOOL, '--app', 'sairnfreedom', '--key', 'ZZ'],
                   capture_output=True, text=True, cwd=REPO, env=env)
results['arm6_missing_schema_exits_3'] = p.returncode == 3
p = subprocess.run([sys.executable, TOOL, '--app', 'zz_not_an_app', '--key', 'ZZ',
                    '--schema', 'sql/sairnfreedom_data_schema.sql'],
                   capture_output=True, text=True, cwd=REPO, env=env)
results['arm6_unknown_app_exits_3'] = p.returncode == 3

# ── ARM 7: it is READ ONLY, and that is checked rather than promised ──────
# Nothing here may leave a row behind: api/sd-data.js has no delete path outside
# the sc_* family and sf_* declares no soft_delete, so a probe write would be
# permanent in a licence this has no way to clean up.
src = io.open(TOOL, encoding='utf-8', errors='replace').read()
results['arm7_only_read_actions'] = "'action': 'read'" in src and "'write'" not in src
results['arm7_no_soft_delete'] = 'soft_delete' not in src.split('"""', 2)[2]

print('--- results ---')
bad = 0
for k in sorted(results):
    v = results[k]
    print('  %-42s %s' % (k, v))
    if isinstance(v, bool) and not v:
        bad += 1

print('')
print('%d ARM(S) FAILED' % bad if bad else 'ALL ARMS PASS')
sys.exit(1 if bad else 0)
