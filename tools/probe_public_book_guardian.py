"""Live probe of the guardian refusal, against an UNKNOWN slug on purpose.

The guardian check runs before resolveSlug, so a minor with no guardian must be
refused 400 GUARDIAN_REQUIRED and never reach the 404. Using a slug that cannot
exist means nothing is written to any real practice at any point.
"""
import json
import os
import sys
import urllib.request
import urllib.error

sys.path.insert(0, os.path.join(r"C:\Users\marsh\Documents\SAIRN-hank", 'tools'))
import sairn_http  # noqa: E402

URL = 'https://sairn.vercel.app/api/sairndental/public-book'


def post(body):
    h = dict(sairn_http.DEFAULT_HEADERS)
    h['Content-Type'] = 'application/json'
    req = urllib.request.Request(URL, data=json.dumps(body).encode(), method='POST', headers=h)
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            return r.status, json.loads(r.read().decode('utf-8', 'replace'))
    except urllib.error.HTTPError as e:
        raw = e.read().decode('utf-8', 'replace')
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {'_raw': raw[:240]}
    except Exception as e:
        return 'ERR', {'_exc': '%s: %s' % (type(e).__name__, e)}


base = {"slug": "__probe_no_such_practice__", "provider_id": "x",
        "procedure_type_id": "y", "start_time": "2026-10-01T15:00:00Z"}
minor = dict(base, patient={"name": "P", "dob": "2015-01-01", "phone": "5555555555"})
withg = dict(base, patient={"name": "P", "dob": "2015-01-01", "phone": "5555555555"},
             guardian={"name": "A Parent", "phone": "5555555556"})
adult = dict(base, patient={"name": "P", "dob": "1980-01-01", "phone": "5555555555"})
nameonly = dict(base, patient={"name": "P", "dob": "2015-01-01", "phone": "5555555555"},
                guardian={"name": "A Parent"})

checks = []


def code(r):
    return (r[1].get('error') or {}).get('code') if isinstance(r[1], dict) else None


r = post(minor)
checks.append(('minor, NO guardian -> 400 GUARDIAN_REQUIRED', r[0] == 400 and code(r) == 'GUARDIAN_REQUIRED', r))
r = post(nameonly)
checks.append(('minor, guardian NAME but no contact -> 400', r[0] == 400 and code(r) == 'GUARDIAN_REQUIRED', r))
r = post(withg)
checks.append(('minor WITH guardian -> gets past the check (404 unknown slug)', r[0] == 404 and code(r) == 'UNKNOWN_SLUG', r))
r = post(adult)
checks.append(('adult, no guardian -> gets past the check (404 unknown slug)', r[0] == 404 and code(r) == 'UNKNOWN_SLUG', r))

bad = 0
for name, ok, res in checks:
    print(('  OK   ' if ok else '  FAIL ') + name + '  -> ' + str(res[0]) + ' ' + str(code(res)))
    if not ok:
        bad += 1
        print('        ' + json.dumps(res[1])[:220])
print('\n%d/%d live checks passed' % (len(checks) - bad, len(checks)))
sys.exit(1 if bad else 0)
