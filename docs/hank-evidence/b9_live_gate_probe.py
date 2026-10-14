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
# ── THIS PROBE WRITES ONE ROW, AND b8's VERSION OF THIS HEADER SAID IT WROTE
# ── NONE. CORRECTED RATHER THAN QUIETLY LEFT. ────────────────────────────────
# guard=yes  residue=docs/live-residue/README.md -- ONE upserted mech_quotes
# row, id ZZ-AI-PROBE-CONTROL, on the AUDIT LICENCE MECH-PINNACLE-2026 only.
# The id is FIXED, not generated, so re-runs overwrite rather than accumulate.
#
# WHY IT HAS TO WRITE. The AI-approval arm asserts that a payload carrying
# `ai_source` is REFUSED with no session. On its own that arm is satisfied by a
# gate that refuses EVERY mech_quotes write -- which would break every existing
# SAIRNmechanical user and is the over-refusal this change must not cause. The
# only way to tell those apart live is to send the same request WITHOUT
# `ai_source` and watch it succeed, and succeeding means a row.
#
# EVERY OTHER WRITE ATTEMPT HERE STILL PERSISTS NOTHING: the leg_bookings one
# is window-less and refused before its SELECT, and the AI-sourced one is
# refused before any upstream call at all.
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


print('B9 LIVE GATE PROBE -- twelve SAIRNscape resources, the AI safeguards '
      'and leg_bookings')
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

# ── PART 1b: THE AI SAFEGUARDS, BOTH HALVES, b9 ──────────────────────────
# WHAT THIS CAN AND CANNOT SHOW, said before the numbers. The approval gate
# fires only on a payload carrying `ai_source`, so a live 403 here proves the
# gate is DEPLOYED AND REACHED on a resource that is otherwise licence-only --
# which is the half a unit test cannot give. It does not prove any production
# client sends the field; none does yet, and that is in the handoff.
#
# IT WRITES NOTHING. The refusal happens before any upstream call, so no
# mech_quotes row is created on the audit licence even if the gate were absent
# -- in which case the handler's own payload check refuses the id-less write.
MECH_LIC = 'MECH-PINNACLE-2026'
print()
ai_bare = call('sairnmechanical', 'mech_quotes', MECH_LIC, None, 'write',
               {'id': 'ZZ-AI-PROBE', 'text': 'x', 'ai_source': 'claude:probe'})
print('mech_quotes write {ai_source, no session} -> %-34s expected 403 '
      'AI_APPROVAL_REQUIRED' % ai_bare)
if 'AI_APPROVAL_REQUIRED' not in ai_bare:
    print('    FAIL: the AI approval gate is not reached -- either not '
          'deployed yet, or mech_quotes is no longer in the high-risk table')
    fail += 1

# THE PAIRED NEGATIVE: the SAME resource, the SAME absent session, WITHOUT the
# ai_source field, must still save. Without this the arm above is satisfied by a
# gate that refuses every mech_quotes write, which would break every existing
# SAIRNmechanical user and is the over-refusal this fix must not cause.
ai_none = call('sairnmechanical', 'mech_quotes', MECH_LIC, None, 'write',
               {'id': 'ZZ-AI-PROBE-CONTROL', 'text': 'x'})
print('mech_quotes write {no ai_source, no session} -> %-31s expected 200 '
      '(THE OVER-REFUSAL CONTROL)' % ai_none)
if not ai_none.startswith('200'):
    print('    FAIL: an ordinary quote no longer saves -- the AI gate has '
          'widened onto every write of this resource')
    fail += 1
else:
    print('    NOTE: that control WROTE one mech_quotes row, id '
          'ZZ-AI-PROBE-CONTROL, on the audit licence MECH-PINNACLE-2026. It is '
          'an upsert on a fixed id, so re-runs overwrite rather than '
          'accumulate. This is the one write in this probe and it is declared '
          'rather than hidden.')

# THE NOTICE ENDPOINT, deployed and correctly refusing. The SQL has not been
# run, so 503 AI_NOTICE_NOT_PROVISIONED is the CORRECT answer and a 200 would
# be the finding -- it would mean the endpoint answered a question it cannot
# answer. 401 is also correct and means the same thing one step earlier.
try:
    r = fetch_json('https://sairn.vercel.app/api/ai-notice',
                   payload={'action': 'state', 'app_id': 'sairnfreedom'},
                   key='SF-PINNACLE-2026')
    body = r.body if isinstance(r.body, dict) else {}
    code = ((body.get('error') or {}).get('code')) or ('ok' if body.get('ok') else '')
    notice = '%s %s' % (r.status, code)
except Exception as e:
    notice = 'ERR %s' % type(e).__name__
print('ai-notice state {no session} -> %-42s expected 401 NO_SESSION or 503 '
      'AI_NOTICE_NOT_PROVISIONED' % notice)
if not (notice.startswith('401') or notice.startswith('503')):
    print('    FAIL: api/ai-notice.js answered something other than a refusal '
          'with no session -- %s' % notice)
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
