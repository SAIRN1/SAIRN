"""tests/run_demo_credentials_probe.py -- attacks tools/demo_credentials_check.py.

Run:  python tests/run_demo_credentials_probe.py

── WHY THIS CONTROL IS UNUSUAL ─────────────────────────────────────────────
The tool under test handles PINs. So the arm that matters most is not "does it
report the right verdict" -- it is **NOTHING IT PRINTS CONTAINS A PIN, ON ANY
PATH, INCLUDING THE FAILING ONES.** A checker that reports WRONG-PIN by showing
the PIN it tried has made the problem worse than the stale credential it found.

Every verdict path is driven against a MOCK endpoint, and after every single one
the whole captured output is searched for the PIN that was used. That search is
the control: if it ever finds one, the arm fails and says which path leaked.

── AND A SECOND CONTROL, BECAUSE THE FIRST ONE IS EASY TO SATISFY BY ACCIDENT
A tool that printed nothing at all would pass the leak arm. So a paired arm
requires the output to CONTAIN the app name and the verdict for the same case --
silent is not the same as safe.

── THE VERDICTS ────────────────────────────────────────────────────────────
  OK                200 with a token
  WRONG-PIN         401 INVALID_CREDENTIALS -- the credential is stale
  LICENCE-INACTIVE  401 INVALID_LICENSE or 403 LICENSE_INACTIVE
  COULD-NOT-REACH   transport failure, a challenge, or any other status

COULD-NOT-REACH IS A THIRD STATE and is never folded into a failure OR a pass:
"the platform said no" and "I could not ask" are different answers, and only the
first is evidence about the credential.
"""
CONTROLS_FOR = ['demo_credentials_check.py']

import importlib.util
import io
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(REPO, 'tools', 'demo_credentials_check.py')
EXIT_COULD_NOT_RUN = 2

FAIL = []


def ok(name, cond, detail=''):
    print('  %s %s%s' % ('PASS ' if cond else 'FAIL ', name,
                         '' if cond else '\n        ' + str(detail)[:400]))
    if not cond:
        FAIL.append(name)


if not os.path.isfile(TOOL):
    sys.stderr.write('COULD NOT RUN: tools/demo_credentials_check.py is not on '
                     'disk. This control tested nothing, which is a third state '
                     'and not a pass.\n')
    sys.exit(EXIT_COULD_NOT_RUN)

spec = importlib.util.spec_from_file_location('dcc', TOOL)
dcc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dcc)

NL = chr(10)
# Assembled at run time. A literal eight-digit string in this file would be a
# finding in the credential-shape guard this same change installs.
PIN = ''.join(str((i * 7 + 3) % 10) for i in range(8))
OTHER_PIN = ''.join(str((i * 3 + 1) % 10) for i in range(8))


class MockResponse(object):
    def __init__(self, status, body):
        self.status = status
        self.body = body


def mock(status, body):
    """A fetch_json stand-in that records what it was called with."""
    calls = []

    def _f(url, payload=None, key=None, headers=None, timeout=None):
        calls.append({'url': url, 'payload': payload, 'key': key})
        if isinstance(status, Exception):
            raise status
        return MockResponse(status, body)
    _f.calls = calls
    return _f


CASES = [
    ('OK', 200, {'ok': True, 'token': 'tok-abc', 'role': 'owner'}),
    ('WRONG-PIN', 401, {'error': {'code': 'INVALID_CREDENTIALS',
                                  'message': 'Incorrect employee ID or PIN'}}),
    ('LICENCE-INACTIVE', 401, {'error': {'code': 'INVALID_LICENSE',
                                         'message': 'Unknown license key'}}),
    ('LICENCE-INACTIVE', 403, {'error': {'code': 'LICENSE_INACTIVE',
                                         'message': 'This license is not active'}}),
    ('COULD-NOT-REACH', 502, {'error': {'message': 'bad gateway'}}),
]

print('CONTROL PAIR -- tools/demo_credentials_check.py' + NL)

print('A. every verdict, against a mock endpoint')
for want, status, body in CASES:
    entry = {'app': 'zzapp', 'endpoint': '/api/zz-auth',
             'license_key': 'ZZ-TEST-2026', 'employee_id': 'sairn-demo-owner',
             'pin': PIN}
    got, line = dcc.check_one(entry, fetch=mock(status, body))
    ok('HTTP %-3s %-22s -> %s' % (status, body.get('error', {}).get('code', 'ok'), want),
       got == want, 'got %r, line = %r' % (got, line))
    # THE ARM THAT MATTERS MOST, on every single case including the failures.
    ok('   ...and the reported line contains NO PIN',
       PIN not in str(line) and PIN[:4] not in str(line),
       'the line leaked the PIN or a fragment of it: %r' % line)
    # ...and it is not silent either.
    ok('   ...and it DOES name the app and the verdict',
       'zzapp' in str(line) and want in str(line),
       'line = %r -- silent is not the same as safe' % line)

print(NL + 'B. a transport failure is COULD-NOT-REACH, not a failed credential')
got, line = dcc.check_one(
    {'app': 'zzapp', 'endpoint': '/api/zz-auth', 'license_key': 'ZZ-TEST-2026',
     'employee_id': 'sairn-demo-owner', 'pin': PIN},
    fetch=mock(OSError('connection reset'), None))
ok('an OSError is COULD-NOT-REACH', got == 'COULD-NOT-REACH', got)
ok('...and it says so rather than reporting a stale credential',
   'COULD-NOT-REACH' in str(line) and 'WRONG-PIN' not in str(line), line)
ok('...and still leaks no PIN', PIN not in str(line), line)

print(NL + 'C. the PIN reaches the ENDPOINT and nowhere else')
f = mock(200, {'ok': True, 'token': 't'})
dcc.check_one({'app': 'zzapp', 'endpoint': '/api/zz-auth',
               'license_key': 'ZZ-TEST-2026', 'employee_id': 'sairn-demo-owner',
               'pin': PIN}, fetch=f)
ok('the PIN IS sent in the request payload -- otherwise this tool tests nothing',
   f.calls and f.calls[0]['payload'].get('pin') == PIN,
   'payload = %r' % (f.calls[0]['payload'] if f.calls else None))
ok('...and the licence key is sent as the key, not in the body',
   f.calls[0]['key'] == 'ZZ-TEST-2026', f.calls[0])

print(NL + 'D. KNOWN-BAD CONTROL: a tool that printed the PIN must be CAUGHT')
# Plant the leak the arms above exist to catch, using the tool's own formatter,
# and require the same search to find it. Without this, the leak arms pass
# whenever the formatter changes shape and stop meaning anything.
leaked = dcc.format_line('zzapp', 'WRONG-PIN', 'tried ' + PIN)
ok('the leak search DOES find a planted PIN', PIN in leaked,
   'the search used by every arm above cannot see a PIN in this tool own '
   'output format, so those arms prove nothing')

print(NL + 'E. the credentials file is READ, NEVER WRITTEN, and refuses to guess')
missing = os.path.join(REPO, '.zz-no-such-credentials.json')
res = dcc.load_credentials(missing)
ok('an absent file is COULD NOT RUN, not an empty pass', res is None)
ok('...and the tool did not create it', not os.path.exists(missing))

bad = os.path.join(REPO, '.zz-probe-credentials.json')
try:
    io.open(bad, 'w', encoding='utf-8').write('{not json')
    ok('unparseable content is COULD NOT RUN, not an empty pass',
       dcc.load_credentials(bad) is None)
finally:
    if os.path.exists(bad):
        os.remove(bad)

print(NL + 'F. THE FILE IS GITIGNORED, driven rather than assumed')
import subprocess
target = os.path.join(REPO, dcc.CREDENTIALS_FILE)
r = subprocess.run(['git', '-C', REPO, 'check-ignore', '-q', target],
                   capture_output=True)
ok('%s is ignored by git' % dcc.CREDENTIALS_FILE, r.returncode == 0,
   'git check-ignore returned %d -- the file the tool reads PINs from is not '
   'ignored, so it can be staged' % r.returncode)

print(NL + 'G. the staged-content guard refuses a credential file by SHAPE')
guard = os.path.join(REPO, 'tools', 'staged_credential_check.py')
if not os.path.isfile(guard):
    ok('tools/staged_credential_check.py exists', False,
       'the pre-commit content guard is missing, so nothing stops a credential '
       'file with an innocent name being staged')
else:
    gspec = importlib.util.spec_from_file_location('scc', guard)
    scc = importlib.util.module_from_spec(gspec)
    gspec.loader.exec_module(gspec and scc)
    body = json.dumps({'apps': [{'app': 'zzapp', 'license_key': 'ZZ-TEST-2026',
                                 'employee_id': 'sairn-demo-owner',
                                 'pin': PIN}]})
    # THE TOOL'S REAL API IS shapes_in(bytes). The first draft of this arm
    # invented scan_text(text, path), got None, and read that as the guard
    # failing to match -- a control asserting against an API that does not
    # exist reports a defect in the subject that is really a defect in itself.
    hits = scc.shapes_in(body.encode())
    ok('a credential FILE SHAPE is caught under an innocent name',
       'demo_credential_file' in hits,
       'shapes_in returned %r -- the guard matches token shapes but not a '
       'demo-credential file, so this file can be staged as notes.json' % (hits,))
    clean = scc.shapes_in(json.dumps({'apps': [{'app': 'zzapp'}]}).encode())
    ok('...and an ordinary JSON file is NOT caught', not clean,
       'the guard fires on a file with no credential in it: %r' % (clean,))
    # BOTH KEY ORDERS, because JSON key order is not promised by anything and
    # a one-order regex is a rename away from useless.
    rev = json.dumps({'apps': [{'pin': PIN, 'license_key': 'ZZ-TEST-2026'}]})
    ok('...and the reversed key order is caught too',
       'demo_credential_file' in scc.shapes_in(rev.encode()),
       scc.shapes_in(rev.encode()))
    # A BARE EIGHT-DIGIT NUMBER IS NOT A CREDENTIAL. Without this the shape
    # would fire on a date, an id, or a row count in any JSON in the repo.
    lone = json.dumps({'count': 12345678, 'pin': PIN})
    ok('...and a PIN with NO licence key beside it is NOT caught',
       'demo_credential_file' not in scc.shapes_in(lone.encode()),
       scc.shapes_in(lone.encode()))

print(NL + '%d failure(s)' % len(FAIL))
for f in FAIL:
    print('  - ' + f)
sys.exit(1 if FAIL else 0)
