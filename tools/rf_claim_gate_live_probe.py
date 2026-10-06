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

# ── THE WORKTREE ROOT, ASKED OF GIT AND THEN CHECKED (2026-10-06) ──────────
# This line hardcoded the absolute path of one clone, so running this probe
# from any other clone imported THAT clone's tools. Nothing would have failed;
# the answer would have been about the wrong tree.
#
# `git rev-parse --show-toplevel` IS THE SOURCE, per instruction -- and it is
# ANCHORED AND VERIFIED, because unanchored it is a trap in this repository
# specifically: the HOME directory is itself a git repository, so discovery
# walks UP from any directory beneath it and SUCCEEDS with exit 0 about the
# wrong repo. tools/git_discovery_anchoring_check.py exists for that hazard and
# it has already produced a fail-open in another tool's probe.
#
# So: anchor with `-C <this file's own directory>`, then CHECK the answer
# actually contains this file. If git is absent, fails, or answers about a tree
# this file is not in, fall back to the __file__ root and SAY SO on stderr --
# a silent fallback would be the same defect one level down.
def _repo_root():
    here = os.path.dirname(os.path.abspath(__file__))
    fallback = os.path.dirname(here)
    try:
        import subprocess
        p = subprocess.run(['git', '-C', here, 'rev-parse', '--show-toplevel'],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if p.returncode == 0:
            root = p.stdout.decode('utf-8', 'replace').strip()
            if root and os.path.isfile(os.path.join(root, 'tools',
                                                    os.path.basename(__file__))):
                return root
            sys.stderr.write(
                'worktree root: git answered %r, which does not contain this '
                'file -- falling back to the path derived from __file__\n'
                % root)
        else:
            sys.stderr.write('worktree root: git rev-parse exited %d -- '
                             'falling back to __file__\n' % p.returncode)
    except Exception as _e:                                      # noqa: BLE001
        sys.stderr.write('worktree root: git rev-parse unavailable (%s) -- '
                         'falling back to __file__\n' % type(_e).__name__)
    return fallback


sys.path.insert(0, os.path.join(_repo_root(), 'tools'))
import sairn_http  # noqa: E402

AUTH = 'https://sairn.vercel.app/api/rf-auth'
DATA = 'https://sairn.vercel.app/api/sd-data'
# ── LIVE-PROBE CLASS AND RESIDUE, DECLARED (2026-09-28) ─────────────────────
# VERIFICATION, and it was already doing the right thing: RF_LICENSE defaults to
# RF-AUDIT-2026, the dedicated audit licence minted on 2026-09-02 precisely so
# roofing verification stopped writing to the customer licence. This declaration
# records that rather than leaving it as a default somebody could change.
LIVE_PROBE_CLASS = 'VERIFICATION'
LIVE_PROBE_RESIDUE = 'none -- `setup` upserts one narrow-role credential on the audit licence, overwritten by the next run; no customer licence is touched'

LICENSE = os.environ.get('RF_LICENSE', 'RF-AUDIT-2026')
# The default is already the audit licence; the guard is what stops an
# override from quietly pointing it at RF-PINNACLE-2026.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from audit_licence import require_audit_licence
LICENSE = require_audit_licence(LICENSE, tool=__file__,
                                writes='a narrow-role credential via setup')
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
