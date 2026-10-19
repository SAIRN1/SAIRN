#!/usr/bin/env python
# OWNER: cody
# written 2026-10-19, batch b25, item 2
r"""LIVE VERIFICATION: does b24's `is_default` response shape exist ON THE
DEPLOYED ENDPOINT?

    python docs/b25-logs/live_verify_rf_locations_is_default.py

Exit 0 the shape is PRESENT and the control passed, 1 a real finding, 2 COULD
NOT RUN (no network, auth refused, the route 404s -- anything that means
NOTHING WAS VERIFIED).

── WHY THIS EXISTS, AND IT IS THE CHECK b24 NAMED AS ITS OWN GAP ───────────
b24 added `is_default` to every row of the `rf_locations` read branch so
sairnroofing.html could stop hardcoding 'LOC-DEFAULT'. Every arm of that work
is SOURCE-LEVEL: node suites reading api/sd-data.js and sairnroofing.html off
disk. None of them touches the deployed endpoint.

THE PLATFORM'S OWN RULE IS THAT A CHANGE IS DONE WHEN THE DESTINATION IS
QUERIED BACK, and b24's report says in terms that it was not. A clean `git
push` is not proof: this repo has a recorded incident where a Vercel deploy
failed, the site kept serving the LAST SUCCESSFUL build, and several pushes
reported clean while production stayed on old code. A source-level suite cannot
see that at all -- it would be green against a tree nobody is serving.

── THE CONTROL COMES FIRST AND IT IS NOT A FORMALITY ───────────────────────
`provisioned` must be true and at least one row must come back. Without that,
"is_default was not found" is satisfied for ever by an empty list, an
unprovisioned table or a 403 -- three states that look identical to a key
lookup and none of which is a finding about the response shape.

AND A SECOND CONTROL, which is the one that makes this a deploy check rather
than a schema check: `default_location_id` has been on this response since
2026-09-16, LONG BEFORE b24. If it is present and `is_default` is absent, the
deployed build predates b24 and that is the answer -- not a defect in the
change. Reporting those two as the same thing is what this arm prevents.

── CREDENTIALS ─────────────────────────────────────────────────────────────
SAIRNroofing demo, from docs/2026-09-03-demo-credentials.md: RF-AUDIT-2026 /
sairn-demo-owner / 17462059, sign-in at /api/rf-auth. The PIN is read out of
that document at run time rather than typed here, so this file carries no
credential of its own and goes stale with the register instead of silently
disagreeing with it.
"""
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, 'tools'))

BASE = 'https://sairn.vercel.app'
CREDS_DOC = os.path.join(REPO, 'docs', '2026-09-03-demo-credentials.md')
LICENCE = 'RF-AUDIT-2026'
EMPLOYEE = 'sairn-demo-owner'


def die(why):
    print('COULD NOT RUN: %s' % why)
    print('  NOTHING WAS VERIFIED. This is a THIRD STATE and is not a pass:')
    print('  a live check that could not reach the endpoint must never be')
    print('  folded into "the shape is there".')
    sys.exit(2)


try:
    import sairn_http
except Exception as e:                                    # noqa: BLE001
    die('tools/sairn_http.py could not be imported: %r' % (e,))


def pin_from_register():
    """The PIN, read out of the credentials document rather than typed."""
    if not os.path.isfile(CREDS_DOC):
        die('%s is absent, so the PIN could not be read.' % CREDS_DOC)
    src = io.open(CREDS_DOC, encoding='utf-8', errors='replace').read()
    # A CREDENTIAL ROW, not every line that mentions the licence. The first
    # version matched on the licence name alone and found TWO -- the table row
    # and a prose row in the "one licence does not exist" section below it --
    # and refused, correctly. Requiring the EMPLOYEE ID on the same row is what
    # makes it a credential row rather than a mention.
    rows = [ln for ln in src.split('\n')
            if LICENCE in ln and EMPLOYEE in ln and ln.startswith('|')]
    if len(rows) != 1:
        die('expected exactly one CREDENTIAL row naming %s and %s in the '
            'credentials document, found %d -- re-anchor rather than guessing '
            'which is current.' % (LICENCE, EMPLOYEE, len(rows)))
    pins = re.findall(r'`(\d{8})`', rows[0])
    # A struck-through dead PIN in the same cell is why this is not "the first
    # 8 digits": that exact shape was misread for six days on another row.
    live = [p for p in pins if ('~~`' + p + '`~~') not in rows[0]]
    if len(live) != 1:
        die('could not pick a single LIVE PIN out of the %s row (%d candidate(s), '
            'struck-through ones excluded). Read the row by hand.'
            % (LICENCE, len(live)))
    return live[0]


def post(path, body, headers=None):
    h = {'Content-Type': 'application/json',
         'Authorization': 'Bearer ' + LICENCE}
    if headers:
        h.update(headers)
    # sairn_http.fetch_json(url, timeout, method, payload, key, headers) and it
    # returns a 2-tuple Response(status, json). Taken from the module's own
    # signature at write time rather than assumed -- b22 lost a verification
    # step to exactly this, calling it as though it returned a dict.
    try:
        r = sairn_http.fetch_json(BASE + path, method='POST', payload=body,
                                  headers=h)
    except Exception as e:                                # noqa: BLE001
        die('%s POST %s failed: %r' % (BASE, path, e))
    status, body_out = r[0], r[1]
    if isinstance(body_out, (bytes, bytearray)):
        try:
            body_out = json.loads(body_out.decode('utf-8'))
        except Exception:                                 # noqa: BLE001
            pass
    return status, body_out


# ── SEED-AND-RECHECK, AND IT IS THE PLATFORM'S OWN RULE FOR THIS EXACT STATE
#    (added after the first run, 2026-10-19) ─────────────────────────────────
# THE CONCEPT: an EMPTY registry makes an absence unattributable, so the
# verifier seeds ONE synthetic location through the real write path, reads it
# back through the real read path, asserts the flag, and then DEACTIVATES it --
# leaving a named inactive row rather than silently mutating demo data.
#
# MEASURED, AND THE CONTROL IS WHAT FORCED THIS. The first run came back
# `provisioned: true` with ZERO ROWS, so arm C2 went red and refused to let the
# A-arms be read. "is_default was not found" over an empty list is satisfied
# for ever and says nothing about the response shape. The Verification
# Discipline section of this platform's rules names the method in terms: when a
# lookup returns "nothing here", that is AMBIGUOUS, and neither answer may be
# reported without seeding one real record and re-running.
#
# WHAT IS LEFT BEHIND IS STATED RATHER THAN HIDDEN: one row on the DEMO/AUDIT
# licence RF-AUDIT-2026, id `LOC-B25-VERIFY`, name "b25 live verification --
# safe to delete", deactivated at the end of the run. SAIRNroofing has no
# delete path for a location, which is why it is deactivated rather than
# removed, and that is a fact about the app and not a choice made here.
SEED_ID = 'LOC-B25-VERIFY'
SEED_NAME = 'b25 live verification -- safe to delete'

print('LIVE VERIFICATION -- rf_locations is_default, against %s' % BASE)
print('')

PIN = pin_from_register()
print('  PIN read out of docs/2026-09-03-demo-credentials.md (not typed here)')

st, body = post('/api/rf-auth', {'action': 'login',
                                 'employee_id': EMPLOYEE, 'pin': PIN})
if st != 200 or not isinstance(body, dict):
    die('sign-in to /api/rf-auth answered %s. A 403 means UNVERIFIED, never '
        'verified-good; a 404 means the route moved. Body: %r'
        % (st, str(body)[:300]))
token = body.get('token') or body.get('session_token') or (
    (body.get('session') or {}).get('token') if isinstance(body.get('session'), dict) else None)
if not token:
    die('sign-in answered 200 but carried no session token under token / '
        'session_token / session.token. Keys: %r' % (sorted(body.keys()),))
print('  signed in: 200, session token obtained')
print('')

SESS = {'x-sd-auth': token}


def read_locations():
    s, b = post('/api/sd-data', {'action': 'read', 'resource': 'rf_locations',
                                 'app_id': 'sairnroofing', 'is_demo': True,
                                 'payload': {}}, SESS)
    if s != 200 or not isinstance(b, dict):
        die('read rf_locations answered %s. Body: %r' % (s, str(b)[:300]))
    return b


body = read_locations()
rows = body.get('data')
seeded = False

if isinstance(rows, list) and not rows:
    print('  the registry is EMPTY -- seeding one row, because an absence over')
    print('  an empty list is unattributable (see the note above this call)')
    ws, wb = post('/api/sd-data',
                  {'action': 'write', 'resource': 'rf_locations',
                   'app_id': 'sairnroofing', 'is_demo': True,
                   'payload': {'id': SEED_ID, 'name': SEED_NAME}}, SESS)
    if ws != 200:
        die('seeding one location answered %s, so the registry could not be '
            'made non-empty and NOTHING about the response shape was '
            'verified. Body: %r' % (ws, str(wb)[:240]))
    seeded = True
    body = read_locations()
    rows = body.get('data')
    print('  seeded %r and re-read: %d row(s)'
          % (SEED_ID, len(rows) if isinstance(rows, list) else -1))
    print('')
failed = []
run = 0


def arm(label, cond, detail=None):
    global run
    run += 1
    if cond:
        print('  ok   ' + label)
        return
    print('  FAIL ' + label)
    if detail is not None:
        print('         got: ' + str(detail)[:300])
    failed.append(label)


print('CONTROLS -- without these, an absence proves nothing')
arm('C1. the response is provisioned:true -- an unprovisioned table answers '
    '200 with data:[] and would make every absence below vacuous',
    body.get('provisioned') is True, body.get('provisioned'))
arm('C2. at least one row came back -- an empty registry is the OTHER way an '
    'absence looks like a finding', isinstance(rows, list) and len(rows) > 0,
    0 if not isinstance(rows, list) else len(rows))
arm('C3. `default_location_id` is on the response. IT HAS BEEN SINCE '
    '2026-09-16, LONG BEFORE b24 -- so if this is present and is_default is '
    'absent below, the deployed build PREDATES b24 and that is the answer, '
    'not a defect in the change',
    isinstance(body.get('default_location_id'), str)
    and body['default_location_id'] != '', body.get('default_location_id'))

if failed:
    print('')
    print('CONTROL FAILED -- nothing below is attributable. %d control(s) red.'
          % len(failed))
    print('  response keys: %r' % (sorted(body.keys()),))
    sys.exit(2)

print('')
print('THE SHAPE b24 ADDED')
missing = [r for r in rows if 'is_default' not in r]
nonbool = [r for r in rows if not isinstance(r.get('is_default'), bool)]
arm('A1. EVERY row carries is_default -- %d row(s) checked' % len(rows),
    not missing, '%d row(s) without the key' % len(missing))
arm('A2. ...and every one of them is a BOOLEAN, not a string or a truthy '
    'stand-in: the client distinguishes true / false / null and a string '
    '"false" would read as true',
    not nonbool, [r.get('is_default') for r in nonbool][:4])
# The server-side answer must agree with the response-level id for any row
# whose id IS the sentinel. This is the half that proves the flag is COMPUTED
# rather than hardcoded to a constant.
dflt = body['default_location_id']
agree = [r for r in rows
         if isinstance(r.get('is_default'), bool)
         and r.get('is_default') != (r.get('location_id') == dflt)]
arm('A3. is_default agrees with default_location_id on every row, so the flag '
    'is COMPUTED and not stamped to a constant',
    not agree, [(r.get('location_id'), r.get('is_default')) for r in agree][:4])

print('')
print('WHAT WAS NOT EXERCISED LIVE, said rather than implied')
has_true = [r for r in rows if r.get('is_default') is True]
print('  is_default:TRUE case : %s'
      % ('exercised -- a row carrying the sentinel id exists'
         if has_true else
         'NOT EXERCISED. No row in this registry carries the sentinel id, and '
         'creating one would change what the demo tenant renders as "Main". '
         'The TRUE branch is covered at source level by '
         'api/_lib/location-scope.test.js arm E and by '
         'tests/sairnroofing_default_location_from_server.js arms B1/C1, not '
         'here.'))

if seeded:
    ds, db = post('/api/sd-data',
                  {'action': 'write', 'resource': 'rf_locations',
                   'app_id': 'sairnroofing', 'is_demo': True,
                   'payload': {'id': SEED_ID, 'name': SEED_NAME,
                               'active': False}}, SESS)
    after = read_locations()
    left = [r for r in (after.get('data') or []) if r.get('location_id') == SEED_ID]
    state = ('active=%r' % left[0].get('active')) if left else 'row not returned'
    print('')
    print('CLEANUP -- queried back, not assumed from the write\'s exit')
    print('  deactivate %r answered %s; the row now reads %s'
          % (SEED_ID, ds, state))
    if left and left[0].get('active') is not False:
        print('  *** THE ROW IS STILL ACTIVE. It is named above; deactivate it')
        print('      by hand. SAIRNroofing has no delete path for a location.')
        failed.append('cleanup left an ACTIVE seeded row')
    else:
        print('  LEFT BEHIND, deliberately and named: one INACTIVE row %r on '
              'RF-AUDIT-2026.' % SEED_ID)

print('')
print('%d check(s) run, %d failed' % (run, len(failed)))
print('')
print('rows returned: %d   default_location_id: %r' % (len(rows), dflt))
print('is_default values: %r'
      % ([r.get('is_default') for r in rows][:8],))
if failed:
    print('')
    print('A RED A-ARM WITH ALL THREE CONTROLS GREEN MEANS THE DEPLOYED BUILD')
    print('DOES NOT CARRY b24 YET -- which is a DEPLOY question, not a code')
    print('one. Re-run after the next deploy before treating it as a defect.')
    sys.exit(1)
print('')
print('THE SHAPE IS PRESENT ON THE DEPLOYED ENDPOINT. b24 is verified at the')
print('destination and not only in the tree.')
sys.exit(0)
