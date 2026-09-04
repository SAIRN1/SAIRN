"""Live 3b/3c round trips for the SAIRNroofing claim gate, on RF-AUDIT-2026.

Step 1 verifies the credential rather than trusting it. Nothing after it runs
unless that step really returned a session token.

THE CREDENTIAL IS READ FROM THE ENVIRONMENT, NOT WRITTEN HERE. A first draft
had the PIN inline and the repo's redaction hook refused the write -- correctly.
A verification script is exactly the kind of file that gets kept and pasted, so
the secret stays out of it:

    RF_EMP=<employee id> RF_PIN=<pin> python rf_roundtrip.py

(The hook then refused a SECOND draft too, on the literal forged-token string
`not-a-real-token` -- 16+ chars assigned to something called `token`. That is a
false positive, and the fix here is to make the fake obviously fake rather than
to argue with the gate.)

READ-ONLY unless --write is passed. Nothing here deletes; the platform has no
reachable delete path for these resources, which is its own recorded row.
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
FORGED = 'fake-unsigned-session'
WRITE = '--write' in sys.argv

if not EMP or not SECRET:
    print('Set RF_EMP and RF_PIN in the environment. They are deliberately not in this file.')
    sys.exit(2)


def post(url, body, session=None, bearer=None):
    headers = dict(sairn_http.DEFAULT_HEADERS)
    headers['Content-Type'] = 'application/json'
    if bearer:
        headers['Authorization'] = 'Bearer ' + bearer
    if session:
        headers['X-SD-Auth'] = session  # api/_lib/auth.js:321 reads x-sd-auth, not a bearer
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


results = []


def step(name, status, body, ok):
    results.append((name, status, ok))
    print('  %s %-54s -> %s' % ('OK  ' if ok else 'FAIL', name, status))
    if not ok or os.environ.get('RF_VERBOSE'):
        print('        ' + json.dumps(body)[:320])


print('STEP 1 -- does the credential actually work?')
st, b = post(AUTH, {'action': 'check_license'}, bearer=LICENSE)
step('check_license %s' % LICENSE, st, b, st == 200)

st, b = post(AUTH, {'action': 'login', 'employee_id': EMP, 'pin': SECRET}, bearer=LICENSE)
ok = (st == 200 and isinstance(b, dict) and b.get('ok') and b.get('token'))
step('login as the demo owner', st, b, bool(ok))
if not ok:
    print('\nSTOPPED: the credential does not work, so nothing below would mean anything.')
    print(json.dumps(b)[:500])
    sys.exit(1)

SESSION = b['token']
print('        role=%s employee_id=%s' % (b.get('role'), b.get('employee_id')))

st, b = post(AUTH, {'action': 'whoami'}, session=SESSION, bearer=LICENSE)
step('whoami echoes the same identity', st, b,
     st == 200 and isinstance(b, dict) and b.get('employee_id') == EMP)

print('\nSTEP 2 -- 3b: rf_claims and rf_claim_photos read paths')
st, claims = post(DATA, {'action': 'read', 'resource': 'rf_claims', 'app_id': 'sairnroofing', 'payload': {}},
                  session=SESSION, bearer=LICENSE)
step('rf_claims read', st, claims, st == 200 and isinstance(claims, dict) and claims.get('ok'))
rows = (claims.get('data') or []) if isinstance(claims, dict) else []
print('        %d claim(s), provisioned=%s' % (len(rows), claims.get('provisioned') if isinstance(claims, dict) else '?'))
claim_id = rows[0]['claim_id'] if rows else None

st, b = post(DATA, {'action': 'read', 'resource': 'rf_claim_photos', 'app_id': 'sairnroofing',
                    'payload': {}}, session=SESSION, bearer=LICENSE)
step('photos read with NO claim_id -> 400', st, b, st == 400)

st, b = post(DATA, {'action': 'read', 'resource': 'rf_claim_photos', 'app_id': 'sairnroofing',
                    'payload': {'claim_id': 'ZZ-NO-SUCH-CLAIM'}}, session=SESSION, bearer=LICENSE)
step('photos read, unknown claim -> 200 empty (degrades, not 503)', st, b,
     st == 200 and isinstance(b, dict) and b.get('ok') and not (b.get('data') or []))

if claim_id:
    st, b = post(DATA, {'action': 'read', 'resource': 'rf_claim_photos', 'app_id': 'sairnroofing',
                        'payload': {'claim_id': claim_id}}, session=SESSION, bearer=LICENSE)
    step('photos read, real claim', st, b, st == 200)
else:
    print('  SKIP photos read on a real claim -- this licence has no claims')

print('\nSTEP 3 -- 3c: reconcile')
if claim_id:
    st, b = post(DATA, {'action': 'reconcile', 'resource': 'rf_claims', 'app_id': 'sairnroofing',
                        'payload': {'claim_id': claim_id}}, session=SESSION, bearer=LICENSE)
    step('reconcile a real claim', st, b, st == 200)
else:
    print('  SKIP reconcile on a real claim -- this licence has no claims')
st, b = post(DATA, {'action': 'reconcile', 'resource': 'rf_claims', 'app_id': 'sairnroofing',
                    'payload': {}}, session=SESSION, bearer=LICENSE)
step('reconcile with no claim_id -> 400', st, b, st == 400)
st, b = post(DATA, {'action': 'reconcile', 'resource': 'rf_claims', 'app_id': 'sairnroofing',
                    'payload': {'claim_id': 'ZZ-NO-SUCH-CLAIM'}}, session=SESSION, bearer=LICENSE)
step('reconcile unknown claim -> 404 NO_CLAIM or 200 unprovisioned', st, b, st in (200, 404))

print('\nSTEP 4 -- the gate refuses without a session, and refuses a forged one')
st, b = post(DATA, {'action': 'read', 'resource': 'rf_claims', 'app_id': 'sairnroofing', 'payload': {}},
             bearer=LICENSE)
step('rf_claims read with NO session -> 401', st, b, st == 401)
st, b = post(DATA, {'action': 'reconcile', 'resource': 'rf_claims', 'app_id': 'sairnroofing',
                    'payload': {'claim_id': 'x'}}, session=FORGED, bearer=LICENSE)
step('reconcile with a FORGED session -> 401', st, b, st == 401)
st, b = post(DATA, {'action': 'read', 'resource': 'rf_claim_photos', 'app_id': 'sairnroofing',
                    'payload': {'claim_id': 'x'}}, session=FORGED, bearer=LICENSE)
step('photos read with a FORGED session -> 401', st, b, st == 401)

if WRITE:
    print('\nSTEP 5 -- write paths')
    st, b = post(DATA, {'action': 'write', 'resource': 'rf_claim_photos', 'app_id': 'sairnroofing',
                        'payload': {'claim_id': 'ZZ-NO-SUCH-CLAIM'}}, session=SESSION, bearer=LICENSE)
    step('photo write against an unknown claim -> 400/404/503, never 200', st, b, st in (400, 404, 503))
else:
    print('\nSTEP 5 -- skipped (pass --write to exercise write paths)')

bad = [r for r in results if not r[2]]
print('\n%d/%d checks passed' % (len(results) - len(bad), len(results)))
for n, s, _ in bad:
    print('  FAILED: %s (%s)' % (n, s))
sys.exit(1 if bad else 0)
