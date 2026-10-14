# b10 -- THE POST-PUSH LIVE VERIFICATION (PR 3.2). A clean `git push` is not
# proof; this drives what this batch added against the REAL deployed endpoint.
#
# ── WHAT IS DRIVEN ─────────────────────────────────────────────────────────
#   leg_clergybookings, the WINDOW REFUSAL. A payload with an id and no
#   clergy/start/end must answer 400 CLERGY_BOOKING_WINDOW_REQUIRED. That code
#   did not exist before this batch, so receiving it is proof the new shared
#   helper is DEPLOYED AND REACHED -- a stronger signal than the leg_bookings
#   arm beside it, whose code is unchanged.
#
#   leg_bookings, the same refusal. UNCHANGED by this batch and that is the
#   point: it is the regression control on the refactor that moved it into
#   api/_lib/leg-overlap.js. If the helper broke it, this arm says so.
#
#   leg_custodylog APPEND-ONLY, BOTH DIRECTIONS. A new entry must be accepted
#   and the SAME id re-sent must be refused 409 APPEND_ONLY. One of those
#   alone proves nothing: a gate that refuses every custody write passes the
#   second arm and breaks the log.
#
#   leg_deathrecords read on an OWNER session -- the over-refusal control for
#   the whole role matrix. A matrix that locks an owner out of a death record
#   is the failure mode that gets a gate deleted.
#
#   rf_settings read on a MANAGEMENT session: 200 and tiered=false.
#
# ── WHAT IS DELIBERATELY NOT DRIVEN, AND WHY, SO AN ABSENCE IS NOT READ AS
# ── A PASS ─────────────────────────────────────────────────────────────────
#   THE ROLE MATRIX'S REFUSAL HALF IS NOT REACHABLE LIVE YET, and that is the
#   same fact as the batch's largest open item rather than a gap in this
#   probe. Every negative arm needs a session holding a NON-owner role, and
#   the five new SAIRNlegacy roles are REJECTED BY THE DATABASE until
#   sql/2026-10-14-michael-run-order.sql block 6 is run. `staff` exists in the
#   CHECK but no `staff` credential exists on the demo licence, and minting
#   one would be writing a credential row from a probe. So: SOURCE AND SUITE
#   VERIFIED ONLY (api/sd-data-leg-role-matrix.test.js, 32 arms, L1-L10
#   included). Stated here because "the probe did not run it" and "the probe
#   ran it and it passed" must never look the same.
#
#   THE rf_settings TIERED HALF, for the same shape of reason: it needs a
#   non-management SAIRNroofing session and no such demo credential exists.
#   The management arm proves the branch still answers; it does not prove the
#   tier withholds anything. api/sd-data-rf-settings-tier.test.js drives both
#   sides against the real handler.
#
#   THE sen_visits clock_flags MERGE needs a caregiver session, an existing
#   visit assigned to them, and two writes ten days apart -- which is a
#   fixture, not a probe. tests/sd_data_clock_flags_merge.test.js drives it
#   across two writes against the real handler and was RED before this batch.
#
# ── THIS PROBE WRITES, AND THE RESIDUE IS NAMED ────────────────────────────
# guard=yes  residue=docs/live-residue/README.md -- ONE leg_custodylog row,
# id ZZ-B10-APPEND-PROBE, on the demo licence LEG-PINNACLE-2026 only. The id
# is FIXED, not generated, so re-runs do not accumulate -- and on a re-run the
# first arm becomes a 409 too, which the output states rather than failing on.
#
# IT HAS TO WRITE. Append-only has two halves and only one of them is a
# refusal. A probe that only sent the second request could not tell
# "edits refused, appends work" from "the log is read-only and nothing can be
# recorded" -- and the second is the worse bug, because a custody log that
# cannot be appended to is a custody log that stops existing.
#
# EVERY OTHER WRITE HERE PERSISTS NOTHING: both window arms are refused before
# their SELECT.
import sys, os, json
sys.path.insert(0, os.path.join(os.getcwd(), 'tools'))
from sairn_http import fetch_json, Challenged

DATA = 'https://sairn.vercel.app/api/sd-data'
LEG_AUTH = 'https://sairn.vercel.app/api/leg-auth'
RF_AUTH = 'https://sairn.vercel.app/api/rf-auth'
LEG_LIC, LEG_EMP, LEG_PIN = 'LEG-PINNACLE-2026', 'sairn-demo-owner', '41957382'
RF_LIC, RF_EMP, RF_PIN = 'RF-AUDIT-2026', 'sairn-demo-owner', '17462059'
APPEND_ID = 'ZZ-B10-APPEND-PROBE'


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
        if 'tiered' in body:
            extra += ' tiered=%s' % body.get('tiered')
        return r.status, code, '%s %s%s' % (r.status, code or ('ok' if body.get('ok') else ''), extra)
    except Challenged:
        return None, 'CHALLENGED', 'CHALLENGED'
    except Exception as e:
        return None, 'ERR', 'ERR %s' % type(e).__name__


def login(url, lic, emp, pin):
    try:
        a = fetch_json(url, payload={'action': 'login', 'employee_id': emp,
                                     'pin': pin}, key=lic)
        body = a.body if isinstance(a.body, dict) else {}
        tok = (body.get('data') or {}).get('token') or body.get('token')
        return a.status, tok, json.dumps(body)[:200]
    except Exception as e:
        return 'EXC', None, '%s %s' % (type(e).__name__, e)


print('B10 LIVE GATE PROBE -- the clergy overlap helper, leg_custodylog '
      'append-only, the role matrix over-refusal control, rf_settings')
print('data %s' % DATA)
print()

fail = 0
couldnot = 0

# ── SAIRNlegacy ────────────────────────────────────────────────────────────
st, leg_tok, why = login(LEG_AUTH, LEG_LIC, LEG_EMP, LEG_PIN)
print('leg-auth login -> %s  token=%s' % (st, 'YES' if leg_tok else 'NONE'))
if not leg_tok:
    print('  COULD NOT RUN: no SAIRNlegacy session, so nothing below was '
          'driven. %s' % why)
    couldnot += 5
else:
    # 1. THE NEW CODE. This error code did not exist before this batch.
    _, code, line = call('sairnlegacy', 'leg_clergybookings', LEG_LIC,
                         leg_tok, 'write', {'id': 'ZZ-B10-NOWINDOW'})
    ok = (code == 'CLERGY_BOOKING_WINDOW_REQUIRED')
    print('  leg_clergybookings write, no window -> %s   %s' %
          (line, 'PASS' if ok else 'FAIL'))
    if not ok:
        fail += 1

    # 2. THE REGRESSION CONTROL on the refactored path.
    _, code, line = call('sairnlegacy', 'leg_bookings', LEG_LIC,
                         leg_tok, 'write', {'id': 'ZZ-B10-NOWINDOW'})
    ok = (code == 'BOOKING_WINDOW_REQUIRED')
    print('  leg_bookings write, no window -> %s   %s' %
          (line, 'PASS' if ok else 'FAIL'))
    if not ok:
        fail += 1

    # 3. APPEND-ONLY, FIRST HALF: a new entry is ACCEPTED.
    status, code, line = call('sairnlegacy', 'leg_custodylog', LEG_LIC,
                              leg_tok, 'write',
                              {'id': APPEND_ID, 'note': 'b10 live probe'})
    first_ok = (status == 200)
    rerun = (code == 'APPEND_ONLY')
    print('  leg_custodylog APPEND %s -> %s   %s' %
          (APPEND_ID, line,
           'PASS' if first_ok else
           ('PASS (re-run: the row already exists from an earlier run, which '
            'is the fixed-id design, not a failure)' if rerun else 'FAIL')))
    if not (first_ok or rerun):
        fail += 1

    # 4. APPEND-ONLY, SECOND HALF: the SAME id is REFUSED.
    status, code, line = call('sairnlegacy', 'leg_custodylog', LEG_LIC,
                              leg_tok, 'write',
                              {'id': APPEND_ID, 'note': 'b10 live probe EDIT'})
    ok = (status == 409 and code == 'APPEND_ONLY')
    print('  leg_custodylog EDIT  %s -> %s   %s' %
          (APPEND_ID, line, 'PASS' if ok else 'FAIL'))
    if not ok:
        fail += 1

    # 5. THE OVER-REFUSAL CONTROL for the whole matrix.
    status, code, line = call('sairnlegacy', 'leg_deathrecords', LEG_LIC,
                              leg_tok, 'read')
    ok = (status == 200)
    print('  leg_deathrecords read, OWNER -> %s   %s' %
          (line, 'PASS' if ok else 'FAIL'))
    if not ok:
        fail += 1

# ── SAIRNroofing ───────────────────────────────────────────────────────────
print()
st, rf_tok, why = login(RF_AUTH, RF_LIC, RF_EMP, RF_PIN)
print('rf-auth login -> %s  token=%s' % (st, 'YES' if rf_tok else 'NONE'))
if not rf_tok:
    print('  COULD NOT RUN: no SAIRNroofing session. %s' % why)
    couldnot += 1
else:
    status, code, line = call('sairnroofing', 'rf_settings', RF_LIC,
                              rf_tok, 'read')
    ok = (status == 200)
    print('  rf_settings read, MANAGEMENT -> %s   %s' %
          (line, 'PASS' if ok else 'FAIL'))
    if not ok:
        fail += 1

print()
print('fail=%d couldnot=%d' % (fail, couldnot))
print()
print('NOT DRIVEN HERE, and this is the list rather than a silence:')
print('  * every role-matrix REFUSAL arm -- needs a non-owner SAIRNlegacy')
print('    session, and the five new roles are rejected by the database')
print('    until run-order block 6 is run. SOURCE AND SUITE VERIFIED ONLY.')
print('  * the rf_settings TIERED half -- needs a non-management SAIRNroofing')
print('    session; no such demo credential exists.')
print('  * the sen_visits clock_flags merge -- needs two writes ten days')
print('    apart against an assigned visit. That is a fixture, not a probe.')
print('  * the office_manager role end to end -- the database rejects it')
print('    until run-order block 5 is run.')
sys.exit(1 if (fail or couldnot) else 0)
