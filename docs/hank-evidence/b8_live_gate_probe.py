# b8 -- THE POST-PUSH LIVE VERIFICATION (PR 3.2). A clean `git push` is not
# proof; this drives the two gates this batch added against the REAL deployed
# endpoint.
#
# WHAT IS DRIVEN, AND WHAT IS DELIBERATELY NOT:
#
#   SAIRNscape, the five newly gated resources -- BOTH HALVES. A bare licence
#   key must be refused 403, and a correctly signed-in crew lead must get
#   through. The second half is the one that matters most: a gate that refused
#   everybody would pass the first half and lock a landscaping company out of
#   its own irrigation schedule. `schedule` is the NEGATIVE CONTROL and must
#   still answer 200 on the bare key -- it is the twelfth SAIRNscape resource,
#   outside Michael's decision, and the day it is gated by accident this probe
#   is where it shows.
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

# The five this batch gated. Named, not derived -- a probe that derived its
# list from the file it is checking would agree with that file by construction.
NEWLY_GATED = ['scp_jobs', 'scp_irr_controllers', 'scp_irr_zones',
               'scp_irr_schedules', 'scp_water_features']
# The twelfth resource, still licence-only, as the control.
CONTROL = ['schedule']


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


print('B8 LIVE GATE PROBE -- the five SAIRNscape resources and leg_bookings')
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
for r in CONTROL:
    bare = call('sairnscape', r, SCP_LIC)
    print('%-22s %-26s %-26s %s' % (r, bare, '--', 'bare 200 (CONTROL)'))
    if not bare.startswith('200'):
        print('    FAIL: the licence-only CONTROL %s no longer answers on the '
              'bare key -- the scope widened, deliberately or not' % r)
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
