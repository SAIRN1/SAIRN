# b9 -- THE POST-PUSH LIVE VERIFICATION (PR 3.2). A clean `git push` is not
# proof; this drives the two gates this batch added against the REAL deployed
# endpoint.
#
# WHAT IS DRIVEN, AND WHAT IS DELIBERATELY NOT:
#
#   SAIRNscape, ALL TWELVE resources -- BOTH HALVES. A bare licence key must be
#   refused 403, and a correctly signed-in crew lead must get through. The
#   second half is the one that matters most: a gate that refused everybody
#   would pass the first half and lock a landscaping company out of its own
#   irrigation schedule.
#
#   b8's VERSION OF THIS PROBE USED `schedule` AS ITS LICENCE-ONLY CONTROL AND
#   THAT CONTROL IS NOW GONE, because Michael decided to gate it. Said out loud
#   rather than quietly dropped: there is no longer any SAIRNscape resource that
#   answers on a bare key, so nothing in this app can show that the probe is
#   capable of observing a 200 on one. THE CONTROL MOVES OUT OF THE APP: a bare
#   key on `employees` -- which has its own, older gate -- must come back with
#   something OTHER than the session table's "sign in first", which is what
#   fails if SD_SESSION_GATED starts answering for resources it does not own.
#   The twelve positive columns are the other half of the same assurance.
#
#   SAIRNlegacy, leg_bookings -- ONLY THE WINDOW REFUSAL. A payload with an id
#   and no facility/start/end must answer 400 BOOKING_WINDOW_REQUIRED, which
#   proves the new branch is DEPLOYED and REACHED. THE CONFLICT PATH IS NOT
#   DRIVEN LIVE AND THAT IS A CHOICE, NOT AN OVERSIGHT: proving a 409 requires
#   a real overlapping booking to exist in the demo tenant, which means writing
#   one, and this probe writes nothing. The 409 is driven in
#   api/sd-data-leg-bookings-toctou.test.js and ablated against the pre-fix
#   handler; what live adds is "the code is there", not "the logic is right".
#
# NOTHING HERE CAN PERSIST A ROW. Every write attempt sends either an id-less
# payload (refused by the handler's own id check before any store call) or a
# window-less one (refused by the new branch before its SELECT).
import sys, os, json
sys.path.insert(0, os.path.join(os.getcwd(), 'tools'))
from sairn_http import fetch_json, Challenged

DATA = 'https://sairn.vercel.app/api/sd-data'
SCP_AUTH = 'https://sairn.vercel.app/api/scp-auth'
LEG_AUTH = 'https://sairn.vercel.app/api/leg-auth'
SCP_LIC, SCP_EMP, SCP_PIN = 'SCP-DEMO-2026', 'sairn-demo-owner', '73018452'
LEG_LIC, LEG_EMP, LEG_PIN = 'LEG-PINNACLE-2026', 'sairn-demo-owner', '41957382'

# All twelve, 2026-10-14 (b9). Named, not derived -- a probe that derived its
# list from the file it is checking would agree with that file by construction.
# Was the five of b8 plus a `schedule` control; `schedule` has moved up.
NEWLY_GATED = ['scp_jobs', 'scp_irr_controllers', 'scp_irr_zones',
               'scp_irr_schedules', 'scp_water_features', 'schedule',
               'customers', 'invoices', 'scp_quotes', 'scp_designs',
               'scp_vendors', 'scp_progress_photos']
# No SAIRNscape resource is licence-only any more. The control is cross-app.
CONTROL = []


def call(app, resource, key, token=None, action='read', payload=None):
    h = {'X-SD-Auth': token} if token else None
    try:
        r = fetch_json(DATA, payload={'action': action, 'resource': resource,
                                      'app_id': app, 'payload': payload or {}},
                       key=key, headers=h)
        body = r.body if isinstance(r.body, dict) else {}
        code = ((body.get('error') or {}).get('code')) or ''
        extra = ''
        rows = body.get('data')
        if isinstance(rows, list):
            extra = ' rows=%d' % len(rows)
        return '%s %s%s' % (r.status, code or ('ok' if body.get('ok') else ''), extra)
    except Challenged:
        return 'CHALLENGED'
    except Exception as e:
        return 'ERR %s' % type(e).__name__


def login(url, lic, emp, pin):
    try:
        a = fetch_json(url, payload={'action': 'login', 'employee_id': emp,
                                     'pin': pin}, key=lic)
        body = a.body if isinstance(a.body, dict) else {}
        tok = (body.get('data') or {}).get('token') or body.get('token')
        return a.status, tok, json.dumps(body)[:200]
    except Exception as e:
        return 'EXC', None, '%s %s' % (type(e).__name__, e)


print('B9 LIVE GATE PROBE -- all twelve SAIRNscape resources and leg_bookings')
print('data %s' % DATA)
print()

fail = 0
couldnot = 0

# ── PART 1: SAIRNscape, both halves ───────────────────────────────────────
st, scp_tok, why = login(SCP_AUTH, SCP_LIC, SCP_EMP, SCP_PIN)
print('scp-auth login -> %s  token=%s' % (st, 'YES' if scp_tok else 'NONE'))
if not scp_tok:
    print('  %s' % why)
    print('COULD NOT RUN the positive half for SAIRNscape. That is a THIRD')
    print('STATE -- not evidence the gate works and not evidence it is broken.')
    couldnot += 1
print()
print('%-22s %-26s %-26s %s' % ('resource', 'BARE KEY', 'WITH SESSION', 'expected'))
for r in NEWLY_GATED:
    bare = call('sairnscape', r, SCP_LIC)
    sess = call('sairnscape', r, SCP_LIC, scp_tok) if scp_tok else 'NOT DRIVEN'
    print('%-22s %-26s %-26s %s' % (r, bare, sess, 'bare 403 / session 200'))
    if not bare.startswith('403'):
        print('    FAIL: %s still answers on the licence key alone' % r)
        fail += 1
    if scp_tok and not sess.startswith('200'):
        print('    FAIL: a correctly signed-in crew lead was refused on %s' % r)
        fail += 1
if CONTROL:
    print('    UNEXPECTED: CONTROL is non-empty, so a SAIRNscape resource has '
          'been re-opened to the bare licence key. Drive it and say why.')
    fail += 1
# THE CROSS-APP CONTROL. `employees` carries its own, older gate: the bare key
# must be refused by THAT, not by the session table. A response carrying "sign
# in first" means SD_SESSION_GATED has widened past the resources it owns, and
# a 200 would mean the probe is pointed at the wrong deployment.
# The MESSAGE is the assertion here, not the status: both gates answer 403, and
# "403" alone cannot tell "its own gate refused" from "the session table
# swallowed a resource it does not own". Read the sentence.
def call_msg(app, resource, key):
    try:
        r = fetch_json(DATA, payload={'action': 'read', 'resource': resource,
                                      'app_id': app, 'payload': {}}, key=key)
        body = r.body if isinstance(r.body, dict) else {}
        return '%s' % r.status, ((body.get('error') or {}).get('message')) or ''
    except Exception as e:
        return 'ERR %s' % type(e).__name__, ''


emp, emp_msg = call_msg('sairnscape', 'employees', SCP_LIC)
emp = emp + ' ' + (emp_msg[:34] or 'ok')
print('%-22s %-26s %-26s %s' % ('employees', emp, '--', 'own gate, NOT ours'))
if 'sign in first' in emp_msg.lower():
    print('    FAIL: SD_SESSION_GATED answered for `employees`, which it does '
          'not own -- the gate has widened past its own table')
    fail += 1
if emp.startswith('200'):
    print('    FAIL: `employees` answered a bare licence key -- its own gate '
          'is gone, which is a finding even though this batch did not cause it')
    fail += 1

# ── PART 2: SAIRNlegacy, the new branch is deployed and reached ───────────
print()
st, leg_tok, why = login(LEG_AUTH, LEG_LIC, LEG_EMP, LEG_PIN)
print('leg-auth login -> %s  token=%s' % (st, 'YES' if leg_tok else 'NONE'))
if not leg_tok:
    print('  %s' % why)
    print('COULD NOT RUN the leg_bookings half. THIRD STATE.')
    couldnot += 1
else:
    # id and nothing else: past the handler's id check, into the new branch,
    # refused before its SELECT. Writes nothing.
    w = call('sairnlegacy', 'leg_bookings', LEG_LIC, leg_tok, 'write',
             {'id': 'PROBE-NO-WINDOW'})
    print('write leg_bookings {id only} -> %s   expected 400 '
          'BOOKING_WINDOW_REQUIRED' % w)
    if 'BOOKING_WINDOW_REQUIRED' not in w:
        print('    FAIL: the new branch is not reached -- either not deployed '
              'yet, or the window check is not where this probe thinks it is')
        fail += 1
    # A cancellation is EXEMPT from the window check by design, so the same
    # id-only payload must get PAST it. It then hits the upsert, which is why
    # the id is a probe id and the row is harmless -- but a 400
    # BOOKING_WINDOW_REQUIRED here would mean the exemption is not live.
    print('    (the cancellation-exempt path is NOT driven live: proving it '
          'would mean writing a row)')

print()
print('fail=%d could-not-run=%d' % (fail, couldnot))
if couldnot and not fail:
    print('PARTIAL: nothing contradicted the fix, and at least one half was '
          'NOT DRIVEN. That is not a pass.')
    sys.exit(2)
sys.exit(1 if fail else 0)
