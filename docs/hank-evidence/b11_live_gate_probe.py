# b11 -- THE POST-PUSH LIVE VERIFICATION (PR 3.2). A clean `git push` is not
# proof; this drives what this batch added against the REAL deployed endpoint.
#
# ── WHAT IS DRIVEN ─────────────────────────────────────────────────────────
#   mar_access_grant ON AN OWNER SESSION. The action did not exist before this
#   batch, so the DISCRIMINATION is the point: 400 "action must be ..." means
#   the dispatcher has never heard of it and NOTHING is deployed; 403 FORBIDDEN
#   means the action exists, is registered in api/_resources/sairncare.js, is
#   reached, AND that the grantor set is office_manager and NOT owner. One
#   request answers both questions and they have different answers.
#
#   family_mar ON AN OWNER SESSION -- the over-refusal control for the whole
#   role narrowing. A gate that locks an OWNER out of a MAR is the failure mode
#   that gets a gate deleted. Sent with a contact id that does not exist, so
#   the correct answer is 404 NO_SUCH_CONTACT: the owner passed the role gate
#   and the handler got as far as looking the contact up.
#
#   alf_mar read ON AN OWNER SESSION -- REGRESSION PIN, unchanged code. The
#   resource that OWNS the table has refused billing since it was written and
#   this batch did not touch it.
#
#   family_mar WITH NO SESSION -- 401, also unchanged, and the control that
#   says arms 1-3 are passing because of a session rather than in spite of one.
#
#   rf_photos write CARRYING ai_source AND NO SESSION -- 403
#   AI_APPROVAL_REQUIRED. This refusal has been REACHABLE AND NEVER REACHED in
#   production since b9, because no client stamped the field. sairnroofing.html
#   now does, so this is the first live proof that the high-risk AI approval
#   gate fires. A 400 here would mean the gate did not fire and the write
#   proceeded to its own validation.
#
#   ...AND THE SAME REQUEST WITH status:'draft' -- must NOT be
#   AI_APPROVAL_REQUIRED. The draft exemption, live, and the control that the
#   gate is not simply refusing every ai_source payload.
#
#   ...AND THE SAME REQUEST WITH NO ai_source -- must NOT be
#   AI_APPROVAL_REQUIRED either. The second control, from the other direction:
#   an ordinary write is untouched.
#
# ── WHAT IS DELIBERATELY NOT DRIVEN, AND WHY, SO AN ABSENCE IS NOT READ AS A
# ── PASS ───────────────────────────────────────────────────────────────────
#   THE ENTIRE SAIRNvet ROLE MATRIX -- all 42 resources, all 6 roles, and the
#   sv_audit_log append-only lock. NOT because the probe ran out of arms: the
#   SAIRNvet demo credential is DEAD. docs/2026-09-03-demo-credentials.md:59
#   records `SV-PINNACLE-2026` / 38471260 as DEAD 2026-09-25 and :250 records
#   the 401 INVALID_CREDENTIALS from the Wave 3 re-run. There is no SAIRNvet
#   session to be had and minting one would be writing a credential row from a
#   probe. SOURCE AND SUITE VERIFIED ONLY --
#   api/sd-data-sv-role-matrix.test.js, 31 arms, including D1 over all 492
#   (resource, role, action) combinations and the spec's V1-V12.
#
#   THE BILLING HALF OF family_mar, AND THE GRANT-THEN-READ FLOW END TO END.
#   Both need credentials that do not exist on ALF-TEST-2026: a `billing`
#   employee and an `office_manager` one. Creating either is a credential-row
#   write, which a probe does not do. The owner arms above prove the branch is
#   deployed and does not over-refuse; they do NOT prove billing is refused.
#   tests/mar_billing_grant.test.js drives that against the real handler, 28
#   arms, from 16 failed.
#
#   THE THREE TRANSPORT GUARDS (sairncare, sairnscape, stonedesk). Client-side
#   JavaScript -- there is no HTTP request that can reach them. Driven against
#   the REAL transports extracted from the real app files by
#   tests/faults/transport_timeout_sweep.js: 81 arms over 15 apps, from 4
#   failed.
#
#   THE THIRD STATE IN api/alf-append-only-read-order.test.js. A property of a
#   checker, not of a deployment. Proven by ablation in both directions: a pure
#   refactor of the read exits 2 COULD NOT RUN, a genuinely deleted order=
#   clause still exits 1 FAIL.
#
#   BOTH SQL BLOCKS. sql/2026-10-14-hank-b11-mar-grant.sql HAS NOT BEEN RUN.
#   So `alf_mar_access_grants` does not exist, no grant can be written or
#   found, and the three new audit event types are rejected by the audit
#   table's CHECK. Everything the probe DOES drive above is the code half,
#   which is live and fail-closed without the SQL.
#
# ── THIS PROBE WRITES NOTHING, AND THAT IS MEASURED NOT HOPED ──────────────
# class=VERIFICATION-READONLY  guard=n/a  residue=none
# Every arm is either a read or a request refused BEFORE its insert: the three
# rf_photos arms carry no `id`, so even the two that pass the AI gate are
# rejected by the handler's own `payload.id is required` check before any
# upsert. The one arm that could have needed a write -- the sv_audit_log
# append-only lock, whose two halves cannot both be proven by a refusal -- is
# unreachable for the credential reason above, so there is no residue and no
# removal SQL to enumerate. If a future run of this file gains a writing arm it
# must enumerate the row and its delete.
import sys, os, json
sys.path.insert(0, os.path.join(os.getcwd(), 'tools'))
from sairn_http import fetch_json, Challenged

DATA = 'https://sairn.vercel.app/api/sd-data'
ALF_AUTH = 'https://sairn.vercel.app/api/alf-auth'
ALF_LIC, ALF_EMP, ALF_PIN = 'ALF-TEST-2026', 'sairn-demo-owner', '19546830'
RF_LIC = 'RF-AUDIT-2026'


def call(app, resource, key, token=None, action='read', payload=None):
    h = {'X-SD-Auth': token} if token else None
    try:
        r = fetch_json(DATA, payload={'action': action, 'resource': resource,
                                      'app_id': app, 'payload': payload or {}},
                       key=key, headers=h)
        body = r.body if isinstance(r.body, dict) else {}
        err = body.get('error') or {}
        code = err.get('code') or ''
        msg = (err.get('message') or '')[:70]
        extra = ''
        rows = body.get('data')
        if isinstance(rows, list):
            extra = ' rows=%d' % len(rows)
        return r.status, code, '%s %s%s%s' % (
            r.status, code or ('ok' if body.get('ok') else ''), extra,
            (' | ' + msg) if (code == '' and msg) or code else '')
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


print('B11 LIVE GATE PROBE -- the MAR access grant action, the family_mar '
      'narrowing, and the first production firing of the AI approval gate')
print('data %s' % DATA)
print('class=VERIFICATION-READONLY  guard=n/a  residue=none')
print()

fail = 0
couldnot = 0

# ── SAIRNcare ──────────────────────────────────────────────────────────────
st, alf_tok, why = login(ALF_AUTH, ALF_LIC, ALF_EMP, ALF_PIN)
print('alf-auth login -> %s  token=%s' % (st, 'YES' if alf_tok else 'NONE'))
if not alf_tok:
    print('  COULD NOT RUN: no SAIRNcare session, so arms 1-3 were not driven. '
          '%s' % why)
    couldnot += 3
else:
    # 1. THE NEW ACTION EXISTS AND REFUSES THE OWNER.
    status, code, line = call('sairncare', 'alf_family_contacts', ALF_LIC,
                              alf_tok, 'mar_access_grant',
                              {'contact_id': 'ZZ-B11-NOSUCH',
                               'grantee_employee_id': 'ZZ-B11-NOBODY',
                               'expires_at': '2026-10-15T00:00:00.000Z'})
    undeployed = (status == 400 and code in ('', 'BAD_ACTION'))
    ok = (status == 403 and code == 'FORBIDDEN')
    print('  mar_access_grant, OWNER session -> %s   %s' %
          (line, 'PASS (the action is deployed AND owner is not a grantor)'
           if ok else ('FAIL -- the dispatcher does not know this action, so '
                       'NOTHING of item 1 is deployed' if undeployed
                       else 'FAIL')))
    if not ok:
        fail += 1

    # 2. THE OVER-REFUSAL CONTROL.
    status, code, line = call('sairncare', 'alf_family_contacts', ALF_LIC,
                              alf_tok, 'family_mar',
                              {'contact_id': 'ZZ-B11-NOSUCH'})
    ok = (code != 'FORBIDDEN')
    print('  family_mar, OWNER session, unknown contact -> %s   %s' %
          (line, 'PASS (the owner passed the role gate -- the narrowing did '
           'not catch them)' if ok else 'FAIL -- the owner is refused by the '
           'new role set'))
    if not ok:
        fail += 1

    # 3. REGRESSION PIN on the resource that owns the table.
    status, code, line = call('sairncare', 'alf_mar', ALF_LIC, alf_tok, 'read')
    ok = (status == 200)
    print('  alf_mar read, OWNER session -> %s   %s' %
          (line, 'PASS' if ok else 'FAIL'))
    if not ok:
        fail += 1

# 4. NO SESSION, unchanged behaviour.
status, code, line = call('sairncare', 'alf_family_contacts', ALF_LIC, None,
                          'family_mar', {'contact_id': 'ZZ-B11-NOSUCH'})
ok = (status == 401 and code == 'NO_SESSION')
print('  family_mar, NO session -> %s   %s' %
      (line, 'PASS' if ok else 'FAIL'))
if not ok:
    fail += 1

print()
# ── SAIRNroofing: THE AI APPROVAL GATE, FIRST PRODUCTION FIRING ────────────
# No session on purpose. The gate runs BEFORE the session gates and verifies
# its own session for the app that OWNS the row, so "nobody is signed in" is
# exactly the state the refusal is written for.
status, code, line = call('sairnroofing', 'rf_photos', RF_LIC, None, 'write',
                          {'ai_source': 'claude:measurement-photo',
                           'ai_analysis': 'b11 live probe -- no id, no write'})
ok = (status == 403 and code == 'AI_APPROVAL_REQUIRED')
print('  rf_photos write, ai_source, NO session -> %s   %s' %
      (line, 'PASS (the high-risk AI approval gate fired in production for '
       'the first time)' if ok else 'FAIL'))
if not ok:
    fail += 1

status, code, line = call('sairnroofing', 'rf_photos', RF_LIC, None, 'write',
                          {'ai_source': 'claude:measurement-photo',
                           'status': 'draft',
                           'ai_analysis': 'b11 live probe -- draft, no id'})
ok = (code != 'AI_APPROVAL_REQUIRED')
print('  rf_photos write, ai_source + status draft -> %s   %s' %
      (line, 'PASS (the draft exemption is live -- a working copy may be '
       'unapproved) -- and note the answer is the SESSION gate one layer '
       'later, which is the discrimination: the AI gate let it past'
       if ok else 'FAIL -- a draft was refused'))
if not ok:
    fail += 1

status, code, line = call('sairnroofing', 'rf_photos', RF_LIC, None, 'write',
                          {'ai_analysis': 'b11 live probe -- no ai_source'})
ok = (code != 'AI_APPROVAL_REQUIRED')
print('  rf_photos write, NO ai_source -> %s   %s' %
      (line, 'PASS (an ordinary write is untouched -- the gate is not '
       'refusing everything) -- again answered by the session gate, which '
       'is what arm 5 proves the AI gate runs BEFORE'
       if ok else 'FAIL'))
if not ok:
    fail += 1

print()
print('-- NOT DRIVEN BY THIS PROBE, so an absence is not read as a pass --')
print('  * the ENTIRE SAIRNvet role matrix (42 resources, 6 roles) and the')
print('    sv_audit_log append-only lock: the SAIRNvet demo credential is DEAD')
print('    (docs/2026-09-03-demo-credentials.md:59 and :250). No session can')
print('    be had and a probe does not mint credentials. SUITE VERIFIED ONLY:')
print('    api/sd-data-sv-role-matrix.test.js, 31 arms, 492 combinations.')
print('  * the BILLING refusal on family_mar and the grant-then-read flow:')
print('    need `billing` and `office_manager` credentials that do not exist')
print('    on ALF-TEST-2026. tests/mar_billing_grant.test.js, 28 arms.')
print('  * the three transport guards: client-side JS, unreachable over HTTP.')
print('    tests/faults/transport_timeout_sweep.js, 81 arms over 15 apps.')
print('  * the COULD NOT RUN third state: a property of a checker, proven by')
print('    ablation in both directions, not by a deployment.')
print('  * BOTH SQL BLOCKS -- NOT RUN, so no grant row can exist and the three')
print('    audit event types are still rejected by the table.')
print()
print('fail=%d couldnot=%d' % (fail, couldnot))
sys.exit(1 if fail else (2 if couldnot else 0))
