"""Do the two SAIRNmechanical panels actually READ AND WRITE the real tables?

    python tools/mech_panels_live_check.py --static   # no network, no writes
    python tools/mech_panels_live_check.py            # the live half too

Exit 0 verified, 1 an arm failed, 2 could not run at all. Three states, never two.

LIVE end-to-end verification of the two SAIRNmechanical panels against the
REAL tables, now that both schema files have been run.

Item 6's wording is the point: not that the columns exist, but that the panels
READ AND WRITE. So this drives the same endpoint, the same actions and the same
payload shapes the panels send -- taken from sairnmechanical.html's mechAssetAdd()
and mechInsAdd() -- rather than a convenient minimal body.

NOT bare curl: tools/sairn_http.py, so a Vercel challenge RAISES instead of being
read as a 200.

── WHAT IT WRITES, AND WHY IT CANNOT CLEAN UP AFTER ITSELF ────────────────────
Both tables grant `select, insert, update` and NO DELETE, by design -- "a lapsed
policy is part of the coverage history somebody may have to answer for", "an asset
that has been serviced is referenced by history that must not orphan". So a
verification row cannot be removed, and pretending otherwise would be the
load_deadline_seed mistake (a dummy POSTed to test an endpoint that implements no
delete, and the dummy stayed).

What it does instead is use the lifecycle the tables were designed with: the row
is written, read back, UPDATED, re-read, then updated to `retired` / `superseded`
with a note naming it as a verification row. The ids carry a per-run timestamp so
a re-run never collides with the previous run's row -- the ZZ-GATE lesson from
tools/sc_tier_a_write_gate_live_probe.py.

── THE ASSET TYPE IS DERIVED, NOT TYPED, AND THE FIRST RUN IS WHY ─────────────
The first version sent 'rooftop_unit' and the endpoint refused it 400
UNKNOWN_ASSET_TYPE -- correctly: the vocabulary is `rtu`. The app was right and
the fixture was wrong, which is the cheap direction for that mistake and only
cheap because the endpoint validates rather than storing it through. It is taken
from api/_lib/mech-assets.js's own ASSET_TYPES now, so a vocabulary change cannot
make this probe fail on a correct app.

── THE ASSERTION THAT MATTERS IS THE NULLS ───────────────────────────────────
Both schemas are built around unrecorded-is-not-zero: refrigerant_charge_lb,
hfc_gwp_over_53, site_state, gwp_over_150, each_occurrence, aggregate_limit,
expires_on and the four endorsements are all NULLABLE WITH NO DEFAULT, and each
file's VERIFY block says what a default would assert. Column metadata proves the
DDL; only a round trip proves the APP preserves them. So the probe writes a row
with those fields deliberately unstated and asserts they come back null -- not 0,
not false.
"""
import io
import json
import os
import re
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import sairn_http                                                   # noqa: E402

# The demo licence from docs/2026-09-03-demo-credentials.md. Overridable, because
# a live check pinned to one licence is a check nobody can point at a customer's.
KEY = os.environ.get('MECH_LICENSE_KEY', 'MECH-PINNACLE-2026')
EMP = os.environ.get('MECH_EMP', 'sairn-demo-owner')
PIN = os.environ.get('MECH_PIN', '58203764')
AUTH = 'https://sairn.vercel.app/api/mech-auth'
DATA = 'https://sairn.vercel.app/api/sd-data'

STAMP = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())
ASSET_ID = 'ZZ-LIVEVERIFY-' + STAMP
POLICY_KEY = 'ZZ-LIVEVERIFY-' + STAMP

fails = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name
          + ('' if cond else '\n         ' + str(detail)[:500]))
    if not cond:
        fails.append(name)


def post(url, body, token=None):
    headers = {'X-SD-Auth': token} if token else None
    r = sairn_http.fetch_json(url, timeout=90, method='POST', payload=body,
                              key=KEY, headers=headers)
    return r.status, r.body


def data(action, resource, payload, token):
    return post(DATA, {'action': action, 'resource': resource,
                       'payload': payload}, token)


_ml = io.open(os.path.join(REPO, 'api', '_lib', 'mech-assets.js'),
              encoding='utf-8').read()
_blk = _ml[_ml.index('const ASSET_TYPES = {'):]
_blk = _blk[:_blk.index('};')]
ASSET_TYPES = re.findall(r'^\s*([a-z_]+): true', _blk, re.M)
assert ASSET_TYPES, 'could not read ASSET_TYPES out of api/_lib/mech-assets.js'
ASSET_TYPE = ASSET_TYPES[0]

# AND THE PANEL'S OWN DROPDOWN HAS TO OFFER THAT SAME VOCABULARY. A select
# offering a value the endpoint refuses would hand every user the 400 this probe
# handed itself, and nothing else compares the two lists.
_h = io.open(os.path.join(REPO, 'sairnmechanical.html'), encoding='utf-8').read()
_seg = _h[_h.index('id="ma-type"'):][:1600]
PANEL_TYPES = [v for v in re.findall(r'<option value="([a-z_]*)"', _seg) if v]

STATIC_ONLY = '--static' in sys.argv

print('SAIRNmechanical -- do the two panels actually READ AND WRITE the real tables')
print('run id %s%s\n' % (STAMP, '  [--static: no network, no writes]'
                        if STATIC_ONLY else ''))

# ── THE STATIC ARM RUNS EVERYWHERE AND WRITES NOTHING ──────────────────────
# It needs no licence, and it is the one that would have caught a real
# user-facing defect rather than a probe's own fixture: a dropdown offering a
# value the endpoint refuses. Runnable in a clone with no credentials, which is
# most of them.
check('the Equipment panel\'s asset-type dropdown offers EXACTLY the vocabulary '
      'api/_lib/mech-assets.js accepts -- an option the endpoint refuses would '
      'hand every user a 400 UNKNOWN_ASSET_TYPE, and nothing else compares the '
      'two lists',
      sorted(PANEL_TYPES) == sorted(ASSET_TYPES),
      'panel: %s\n         lib:   %s' % (sorted(PANEL_TYPES), sorted(ASSET_TYPES)))

if STATIC_ONLY:
    print('\n%d arm(s) failed' % len(fails))
    # NOT a pass for the panels. `--static` answers one question and says so:
    # the first version of this flag did not gate anything at all and ran the
    # whole live half while printing "no writes", which is the unreachable-branch
    # shape this session spent the afternoon sweeping for -- committed by the
    # sweep's own author, inside the hour.
    print('STATIC ONLY -- the live read/write half was NOT run. That is a '
          'COULD-NOT-TELL about the panels, not a pass. Re-run without --static '
          'against a real licence for that.')
    sys.exit(1 if fails else 0)

st, body = post(AUTH, {'action': 'login', 'employee_id': EMP, 'pin': PIN})
token = (body or {}).get('token')
if st != 200 or not token:
    sys.stderr.write('COULD NOT RUN: sign-in failed (%s) %s\n'
                     % (st, json.dumps(body)[:300]))
    sys.exit(2)
print('signed in as %s (%s)\n' % (EMP, (body or {}).get('role')))

# ══ 1. mech_site_assets ═════════════════════════════════════════════════════
print('1. mech_site_assets -- the Equipment panel\'s own payload shape')

st, b = data('read', 'mech_site_assets', {}, token)
check('read answers 200 and the table is PROVISIONED -- provisioned:false would '
      'mean the panel is showing an honest empty state over a missing table',
      st == 200 and (b or {}).get('provisioned') is not False,
      (st, json.dumps(b)[:300]))
print('       %d asset(s) on the licence before this run'
      % len((b or {}).get('data') or []))

asset = {
    'asset_id': ASSET_ID,
    'customer_name': 'ZZ Live Verify (hank ' + STAMP + ')',
    'site_name': 'verification row -- retired at the end of this run',
    'site_address': None,
    'asset_type': ASSET_TYPE,
    'make': None, 'model': None, 'serial_no': None,
    'location_on_site': None, 'installed_on': None,
    'has_warranty': None, 'warranty_expires_on': None,
    'refrigerant_type': None,
    'refrigerant_charge_lb': None,
    'hfc_gwp_over_53': None,
    'site_state': None,
    'gwp_over_150': None,
    'leak_detected_on': None,
    'leak_repair_verified_on': None
}
st, b = data('write', 'mech_site_assets', asset, token)
check('write answers 200 ok:true', st == 200 and (b or {}).get('ok') is True,
      (st, json.dumps(b)[:400]))

st, b = data('read', 'mech_site_assets', {}, token)
rows = (b or {}).get('data') or []
mine = [r for r in rows if r.get('asset_id') == ASSET_ID or r.get('id') == ASSET_ID]
check('the written row READS BACK on the next read -- one round trip, not two '
      'assertions about the same request', len(mine) == 1,
      'found %d; ids seen: %s'
      % (len(mine), [r.get('asset_id') or r.get('id') for r in rows][:8]))

if mine:
    row = mine[0]
    NULLABLE = ['refrigerant_charge_lb', 'hfc_gwp_over_53', 'site_state',
                'gwp_over_150', 'leak_detected_on', 'leak_repair_verified_on']
    bad = dict((k, row.get(k)) for k in NULLABLE if row.get(k) is not None)
    check('THE ARM THAT MATTERS: every unstated three-state column comes back '
          'NULL, not 0 and not false -- a defaulted charge reports an unweighed '
          'unit as below a federal threshold, and a defaulted gwp_over_150 '
          'clears it under a state programme that may reach it',
          not bad, bad)

    st, b = data('write', 'mech_site_assets',
                 dict(asset, make='ZZ-UPDATED', refrigerant_charge_lb='55.5',
                      site_state='CA', gwp_over_150=True), token)
    check('UPDATE through the same upsert answers 200 ok:true',
          st == 200 and (b or {}).get('ok') is True, (st, json.dumps(b)[:300]))
    st, b = data('read', 'mech_site_assets', {}, token)
    again = [r for r in ((b or {}).get('data') or [])
             if r.get('asset_id') == ASSET_ID or r.get('id') == ASSET_ID]
    check('the UPDATE landed and did not create a second row -- the unique '
          '(license_hash, asset_id) is what makes the panel\'s re-entry an edit '
          'rather than a duplicate', len(again) == 1, 'found %d' % len(again))
    if again:
        got = again[0]
        check('...and the updated values are the ones read back (make, charge, '
              'site_state, gwp_over_150)',
              got.get('make') == 'ZZ-UPDATED'
              and str(got.get('refrigerant_charge_lb')) in ('55.5', '55.50')
              and got.get('site_state') == 'CA'
              and got.get('gwp_over_150') is True,
              dict((k, got.get(k)) for k in
                   ('make', 'refrigerant_charge_lb', 'site_state', 'gwp_over_150')))

    st, b = data('write', 'mech_site_assets',
                 dict(asset, make='ZZ-UPDATED', status='retired',
                      notes='live verification row, hank ' + STAMP
                           + ' -- this table grants no DELETE by design, so it is '
                             'retired rather than removed'), token)
    check('and it is left RETIRED rather than deleted -- this table grants no '
          'DELETE on purpose, so retiring is the recoverable end state',
          st == 200 and (b or {}).get('ok') is True, (st, json.dumps(b)[:300]))

# ══ 2. mech_insurance_policies ══════════════════════════════════════════════
print('\n2. mech_insurance_policies -- the Insurance/COI panel')

st, b = data('read', 'mech_insurance_policies', {'today': '2026-09-26'}, token)
check('read answers 200 and the table is PROVISIONED',
      st == 200 and (b or {}).get('provisioned') is not False,
      (st, json.dumps(b)[:300]))

policy = {
    'policy_key': POLICY_KEY,
    'kind': 'general_liability',
    'carrier': 'ZZ Live Verify (hank ' + STAMP + ')',
    'policy_no': None,
    'effective_on': '2026-01-01',
    'expires_on': None,
    'each_occurrence': None,
    'aggregate_limit': None,
    'certificate_holder': None,
    'additional_insured': None,
    'waiver_of_subrogation': None,
    'primary_noncontributory': None,
    'per_project_aggregate': None
}
st, b = data('write', 'mech_insurance_policies', policy, token)
check('write answers 200 ok:true', st == 200 and (b or {}).get('ok') is True,
      (st, json.dumps(b)[:400]))

st, b = data('read', 'mech_insurance_policies', {'today': '2026-09-26'}, token)
prows = (b or {}).get('data') or []
pmine = [r for r in prows if r.get('policy_id') == POLICY_KEY
         or r.get('policy_key') == POLICY_KEY]
check('the written policy READS BACK', len(pmine) == 1,
      'found %d; keys seen: %s'
      % (len(pmine),
         [r.get('policy_id') or r.get('policy_key') for r in prows][:8]))

if pmine:
    prow = pmine[0]
    check('THE ARM THAT MATTERS: an unrecorded expiry does NOT read as current. '
          'A certificate holder asking for proof of current cover is asking a '
          'question this record cannot answer',
          'no_expiry' in json.dumps(prow).lower() or prow.get('expires_on') is None,
          json.dumps(prow)[:400])
    check('...and an unrecorded limit is NOT zero and NOT satisfied',
          prow.get('each_occurrence') in (None, '')
          or 'unknown' in json.dumps(prow).lower(),
          json.dumps(prow)[:400])

    st, b = data('write', 'mech_insurance_policies',
                 dict(policy, each_occurrence='2000000.00',
                      aggregate_limit='4000000.00', expires_on='2027-01-01',
                      additional_insured=True), token)
    check('UPDATE answers 200 ok:true', st == 200 and (b or {}).get('ok') is True,
          (st, json.dumps(b)[:300]))
    st, b = data('read', 'mech_insurance_policies', {'today': '2026-09-26'}, token)
    pagain = [r for r in ((b or {}).get('data') or [])
              if r.get('policy_id') == POLICY_KEY or r.get('policy_key') == POLICY_KEY]
    check('the UPDATE landed and did not create a second row', len(pagain) == 1,
          'found %d' % len(pagain))
    if pagain:
        check('...and the recorded limits and endorsement read back',
              json.dumps(pagain[0]).find('2000000') != -1
              and pagain[0].get('additional_insured') is True,
              json.dumps(pagain[0])[:400])

    st, b = data('readiness', 'mech_insurance_policies',
                 {'today': '2026-09-26',
                  'requirements': [{'kind': 'general_liability',
                                    'each_occurrence': 1000000,
                                    'endorsements': ['additional_insured']}]}, token)
    check('the readiness action answers 200 -- the panel\'s Check button drives '
          'this and nothing in the client re-derives the comparison',
          st == 200, (st, json.dumps(b)[:400]))

    st, b = data('write', 'mech_insurance_policies',
                 dict(policy, status='superseded',
                      notes='live verification row, hank ' + STAMP
                           + ' -- no DELETE grant by design, so superseded'), token)
    check('and it is left SUPERSEDED rather than deleted',
          st == 200 and (b or {}).get('ok') is True, (st, json.dumps(b)[:300]))

print('\n%d arm(s) failed' % len(fails))
print('LIVE VERDICT: ' + ('VERIFIED -- both panels read AND write the real tables'
                          if not fails else 'FAILED'))
print('ROWS LEFT ON THE LICENCE: asset %s (retired), policy %s (superseded). '
      'Neither table grants DELETE, by design.' % (ASSET_ID, POLICY_KEY))
sys.exit(1 if fails else 0)
