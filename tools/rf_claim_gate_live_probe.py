"""Exercise the SAIRNroofing claim gate's ALLOW and DENY paths against the live
endpoint, on the RF-AUDIT-2026 audit licence.

WHY THIS EXISTS SEPARATELY FROM rf_roundtrip.py. That script passed 11/11 and
SKIPPED the two arms that matter most: RF-AUDIT-2026 has zero claims, so
"read the photos of a real claim" and "reconcile a real claim" never ran, and
the gate's ALLOW path was never exercised at all. A green run that skipped the
substantive half is the exact shape this codebase keeps getting caught by, so
this creates the fixture instead of reporting around its absence.

WHAT IT CREATES, on the AUDIT licence only, all clearly labelled ZZ-GATE-*:
  * one rf_jobs row      ZZ-GATE-JOB
  * one rf_claims row    ZZ-GATE-CLAIM
  * one narrow-role employee, so the DENY path has a real subject
Nothing is deleted afterwards: the platform has no reachable delete path for
these resources (its own open row). The names are chosen so a later reader can
see at a glance what they are and why.

Credentials come from the environment, never this file.
"""
import json
import os
import sys
import urllib.request
import urllib.error

sys.path.insert(0, os.path.join(r"C:\Users\marsh\Documents\SAIRN-hank", 'tools'))
import sairn_http  # noqa: E402

AUTH = 'https://sairn.vercel.app/api/rf-auth'
DATA = 'https://sairn.vercel.app/api/sd-data'
LICENSE = os.environ.get('RF_LICENSE', 'RF-AUDIT-2026')
EMP = os.environ.get('RF_EMP', '')
SECRET = os.environ.get('RF_PIN', '')
NARROW_ID = 'zz-gate-foreman'
NARROW_SECRET = os.environ.get('RF_NARROW_PIN', '')

if not EMP or not SECRET or not NARROW_SECRET:
    print('Set RF_EMP, RF_PIN and RF_NARROW_PIN in the environment.')
    sys.exit(2)

JOB = 'ZZ-GATE-JOB'
CLAIM = 'ZZ-GATE-CLAIM'


def post(url, body, session=None):
    headers = dict(sairn_http.DEFAULT_HEADERS)
    headers['Content-Type'] = 'application/json'
    headers['Authorization'] = 'Bearer ' + LICENSE
    if session:
        headers['X-SD-Auth'] = session
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method='POST', headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            return r.status, json.loads(r.read().decode('utf-8', 'replace'))
    except urllib.error.HTTPError as e:
        raw = e.read().decode('utf-8', 'replace')
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {'_raw': raw[:400]}
    except Exception as e:
        return 'ERR', {'_exc': '%s: %s' % (type(e).__name__, e)}


def data(action, resource, payload, session):
    return post(DATA, {'action': action, 'resource': resource,
                       'app_id': 'sairnroofing', 'payload': payload}, session=session)


results = []


def step(name, status, body, ok):
    results.append((name, status, ok))
    print('  %s %-56s -> %s' % ('OK  ' if ok else 'FAIL', name, status))
    if not ok or os.environ.get('RF_VERBOSE'):
        print('        ' + json.dumps(body)[:340])


st, b = post(AUTH, {'action': 'login', 'employee_id': EMP, 'pin': SECRET})
if not (st == 200 and b.get('token')):
    print('owner login failed:', st, json.dumps(b)[:300])
    sys.exit(1)
OWNER = b['token']
print('signed in as %s (role=%s) on %s\n' % (b.get('employee_id'), b.get('role'), LICENSE))

print('FIXTURE -- create a job and a claim so the ALLOW path has something to allow')
st, b = data('write', 'rf_jobs', {
    'id': JOB, 'customer_name': 'ZZ Gate Probe', 'address': '1 Probe Way',
    'status': 'lead'}, OWNER)
step('rf_jobs write ' + JOB, st, b, st == 200)

st, b = data('write', 'rf_claims', {
    'id': CLAIM, 'job_id': JOB, 'carrier': 'ZZ Probe Mutual',
    'claim_number': 'ZZ-GATE-0001', 'status': 'loss_reported',
    'assigned_employee_id': None}, OWNER)
step('rf_claims write ' + CLAIM, st, b, st == 200)

print('\nALLOW -- an owner sees everything, assigned or not')
st, b = data('read', 'rf_claims', {}, OWNER)
ids = [c.get('claim_id') for c in (b.get('data') or [])] if isinstance(b, dict) else []
step('owner rf_claims read includes the probe claim', st, b, CLAIM in ids)

st, b = data('read', 'rf_claim_photos', {'claim_id': CLAIM}, OWNER)
step('owner photos read on a REAL claim (was skipped before)', st, b, st == 200)

st, b = data('reconcile', 'rf_claims', {'claim_id': CLAIM}, OWNER)
step('owner reconcile on a REAL claim (was skipped before)', st, b, st == 200)

st, b = data('assess', 'rf_claims', {'claim_id': CLAIM}, OWNER)
step('owner assess on a REAL claim', st, b, st in (200, 400))

print('\nDENY -- a narrow role that is not the assignee')
st, b = post(AUTH, {'action': 'setup', 'employee_id': NARROW_ID, 'pin': NARROW_SECRET,
                    'role': 'foreman', 'name': 'ZZ Gate Probe Foreman'}, session=OWNER)
step('provision a foreman for the deny path', st, b, st in (200, 409))

st, b = post(AUTH, {'action': 'login', 'employee_id': NARROW_ID, 'pin': NARROW_SECRET})
narrow_ok = st == 200 and isinstance(b, dict) and b.get('token')
step('foreman login', st, b, bool(narrow_ok))
if narrow_ok:
    NARROW = b['token']
    print('        role=%s' % b.get('role'))

    st, b = data('read', 'rf_claims', {}, NARROW)
    nids = [c.get('claim_id') for c in (b.get('data') or [])] if isinstance(b, dict) else []
    step('foreman rf_claims read EXCLUDES the unassigned claim', st, b,
         st == 200 and CLAIM not in nids)

    st, b = data('read', 'rf_claim_photos', {'claim_id': CLAIM}, NARROW)
    step('foreman photos read on it -> 403 FORBIDDEN', st, b,
         st == 403 and (b.get('error') or {}).get('code') == 'FORBIDDEN')

    st, b = data('reconcile', 'rf_claims', {'claim_id': CLAIM}, NARROW)
    step('foreman reconcile on it -> 403 FORBIDDEN', st, b,
         st == 403 and (b.get('error') or {}).get('code') == 'FORBIDDEN')

    st, b = data('write', 'rf_claims', {
        'id': CLAIM, 'job_id': JOB, 'carrier': 'ZZ Probe Mutual',
        'claim_number': 'ZZ-GATE-0001'}, NARROW)
    step('foreman WRITE to an unassigned claim -> 403 (the 7th spelling)', st, b,
         st == 403 and (b.get('error') or {}).get('code') == 'FORBIDDEN')

    print('\nALLOW -- assign it to the foreman, then the same calls must pass')
    st, b = data('write', 'rf_claims', {
        'id': CLAIM, 'job_id': JOB, 'carrier': 'ZZ Probe Mutual',
        'claim_number': 'ZZ-GATE-0001', 'assigned_employee_id': NARROW_ID}, OWNER)
    step('owner assigns the claim to the foreman', st, b, st == 200)

    st, b = data('read', 'rf_claims', {}, NARROW)
    nids = [c.get('claim_id') for c in (b.get('data') or [])] if isinstance(b, dict) else []
    step('foreman rf_claims read NOW includes it', st, b, st == 200 and CLAIM in nids)

    st, b = data('read', 'rf_claim_photos', {'claim_id': CLAIM}, NARROW)
    step('foreman photos read NOW allowed', st, b, st == 200)

    st, b = data('reconcile', 'rf_claims', {'claim_id': CLAIM}, NARROW)
    step('foreman reconcile NOW allowed', st, b, st == 200)

bad = [r for r in results if not r[2]]
print('\n%d/%d checks passed' % (len(results) - len(bad), len(results)))
for n, s, _ in bad:
    print('  FAILED: %s (%s)' % (n, s))
sys.exit(1 if bad else 0)
