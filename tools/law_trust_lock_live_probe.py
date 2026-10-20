# OWNER: hank
"""Prove SAIRNlaw's trust HARD-LOCK against the LIVE deployed endpoint.

    LAW_LICENSE=LAW-AUDIT-2026 LAW_OWNER_PIN=... LAW_PARALEGAL_PIN=... \
      python tools/law_trust_lock_live_probe.py

WHY THIS EXISTS (b23, 2026-10-19). The hard lock is the structure
`api/_lib/law-roles.js` consults FIRST -- `LAW_TRUST_LOCKED` -- and
fourth's b26 finding H1 was that it could be DELETED ENTIRELY with every suite
still green. b17 answered that with structural arms and b18 with 59 handler
arms, and both drive a MOCK. CLAUDE.md's push protocol is explicit that a clean
`git push` is not proof, and every previous batch recorded the live half of this
lock as UNVERIFIED because it sits below a SAIRNlaw employee session nothing had.

── THE FOUR ANSWERS, AND THE POINT IS THAT THEY ARE FOUR AND NOT ONE ─────────
A probe that only showed "a paralegal gets 403" would be satisfied by a broken
session, a dead licence, or an endpoint that refuses everything. These four
together are not:

  1. paralegal + law_trusttx       read   -> 403 FORBIDDEN       the hard lock
  2. paralegal + law_bankstatements r/w   -> 403 FORBIDDEN       no carve-out:
     the bank side is IMPORTED, nobody at the firm prepares one, and it is
     deliberately absent from LAW_TRUST_TWO_STAGE
  3. paralegal + law_trusttx       write  -> 403 COUNTERSIGN_REQUIRED
     NOT the same refusal. This is C2's two-stage carve-out, and a probe that
     accepted any 403 here could not tell the carve-out from the lock
  4. THE NEGATIVE CONTROLS -- paralegal + law_clients/law_timeentries read
     -> 200, and owner + both locked resources -> 200. Without these a 403
     everywhere is indistinguishable from the lock working

── WHAT IT WRITES, AND WHERE ─────────────────────────────────────────────────
A role refusal cannot be proved without a credential in that role, so this
provisions two employee rows -- an owner (via `bootstrap`, which only succeeds
on a licence with no credentials) and a paralegal (via `setup`). ON THE AUDIT
LICENCE ONLY: `require_audit_licence` refuses a demo-facing key outright rather
than writing to the licence a prospect is shown.

It DEACTIVATES the paralegal at the end and READS THAT BACK by attempting a
login, which must answer 401. Asserting the reply to `set_active` would be a
different claim from asserting the state.

── THE THREE STATES, AND THEY ARE NOT TWO ────────────────────────────────────
  VERIFIED     every arm above answered as stated on the deployed endpoint
  UNVERIFIED   credentials absent, a licence or PIN is not live, the tables are
               not provisioned, or Vercel served its bot challenge -- exit 2,
               and NOT reported as a failure of the lock
  FAILED       an arm answered something else -- exit 1
"""
import json
import os
import sys
import urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sairn_http                                                   # noqa: E402
from audit_licence import require_audit_licence                     # noqa: E402

AUTH = 'https://sairn.vercel.app/api/law-auth'
DATA = 'https://sairn.vercel.app/api/sd-data'
OWNER_ID = 'hank-b23-owner'
PARA_ID = 'hank-b23-paralegal'

LIVE_PROBE_CLASS = 'VERIFICATION'
LIVE_PROBE_RESIDUE = 'sql/zz_probe_residue_delete_b23.sql -- two employee credential rows on the AUDIT licence, hank-b23-owner and hank-b23-paralegal, reusing the same two ids every run so the count does not grow'
LIVE_PROBE_TEARDOWN = 'the paralegal is deactivated with set_active and the deactivation is READ BACK by attempting a login, which must answer 401 INVALID_CREDENTIALS. A 200 from set_active is the reply, not the state, and this probe asserts the state.'

EXIT_OK, EXIT_FAILED, EXIT_COULD_NOT_RUN = 0, 1, 2

failures = []


def post(url, body, licence, token=None):
    headers = {'Content-Type': 'application/json',
               'Authorization': 'Bearer ' + licence}
    if token:
        headers['X-SD-Auth'] = token
    try:
        r = sairn_http.fetch(url, method='POST', data=json.dumps(body).encode(),
                             headers=headers, no_cache=True)
        return r.status, r.body
    except urllib.error.HTTPError as e:
        sairn_http.raise_if_challenge(e)
        return e.code, e.read()


def code_of(raw):
    try:
        d = json.loads(raw.decode('utf-8', 'replace'))
    except Exception:
        return ''
    err = d.get('error') if isinstance(d, dict) else None
    return (err or {}).get('code', '') if isinstance(err, dict) else ''


def arm(label, got_status, got_code, want_status, want_code):
    """want_code of None means 'do not care about the code'."""
    ok = got_status == want_status and (want_code is None or got_code == want_code)
    print('  %-4s %-58s %s %s' % ('ok' if ok else 'FAIL', label,
                                  got_status, got_code or ''))
    if not ok:
        failures.append('%s (expected %s %s, got %s %s)'
                        % (label, want_status, want_code or '*',
                           got_status, got_code or ''))
    return ok


def main():
    key = os.environ.get('LAW_LICENSE', '').strip()
    owner_pin = os.environ.get('LAW_OWNER_PIN', '').strip()
    para_pin = os.environ.get('LAW_PARALEGAL_PIN', '').strip()
    if not (key and owner_pin and para_pin):
        print('UNVERIFIED -- LAW_LICENSE, LAW_OWNER_PIN and LAW_PARALEGAL_PIN')
        print('must all be set. The lock sits below a SAIRNlaw employee session,')
        print('so it cannot be reached without a real licence AND a real session.')
        print('  LAW_LICENSE must be an AUDIT licence: LAW-AUDIT-2026.')
        return EXIT_COULD_NOT_RUN
    key = require_audit_licence(
        key, tool=__file__,
        writes='sairnlaw_employee_auth (two probe credential rows, fixed ids)')

    print('SAIRNlaw trust hard-lock -- LIVE')
    print('  endpoint %s' % DATA)
    print('  licence  %s...%s\n' % (key[:4], key[-4:]))

    # ── PROVISION. bootstrap only succeeds on a licence with no credentials;
    # 409 ALREADY_PROVISIONED means a previous run made them, which is fine.
    st, body = post(AUTH, {'action': 'bootstrap', 'employee_id': OWNER_ID,
                           'pin': owner_pin,
                           'display_name': 'hank b23 probe owner'}, key)
    if st not in (200, 409):
        print('UNVERIFIED -- bootstrap answered %s %s' % (st, body[:200]))
        return EXIT_COULD_NOT_RUN
    st, body = post(AUTH, {'action': 'login', 'employee_id': OWNER_ID,
                           'pin': owner_pin}, key)
    if st != 200:
        print('UNVERIFIED -- the probe owner could not sign in (%s). The '
              'credential exists on a licence whose PIN is not this one; run '
              'sql/zz_probe_residue_delete_b23.sql and re-run.' % st)
        return EXIT_COULD_NOT_RUN
    owner_tok = json.loads(body)['token']

    st, body = post(AUTH, {'action': 'setup', 'employee_id': PARA_ID,
                           'pin': para_pin, 'role': 'paralegal',
                           'display_name': 'hank b23 probe paralegal'},
                    key, owner_tok)
    if st != 200:
        print('UNVERIFIED -- the paralegal credential could not be provisioned '
              '(%s %s)' % (st, body[:200]))
        return EXIT_COULD_NOT_RUN
    st, body = post(AUTH, {'action': 'login', 'employee_id': PARA_ID,
                           'pin': para_pin}, key)
    if st != 200:
        print('UNVERIFIED -- the paralegal could not sign in (%s)' % st)
        return EXIT_COULD_NOT_RUN
    para = json.loads(body)
    if para.get('role') != 'paralegal':
        print('UNVERIFIED -- the probe session is role %r, not paralegal, so '
              'nothing below would be measuring the lock.' % para.get('role'))
        return EXIT_COULD_NOT_RUN
    para_tok = para['token']

    print('A. THE HARD LOCK')
    for res in ('law_trusttx', 'law_bankstatements'):
        st, b = post(DATA, {'action': 'read', 'resource': res}, key, para_tok)
        arm('A%d. paralegal READ %s' % (1 if res == 'law_trusttx' else 2, res),
            st, code_of(b), 403, 'FORBIDDEN')
    st, b = post(DATA, {'action': 'write', 'resource': 'law_bankstatements',
                        'payload': {'id': 'ZZ-B23-PROBE'}}, key, para_tok)
    arm('A3. paralegal WRITE law_bankstatements (no carve-out)',
        st, code_of(b), 403, 'FORBIDDEN')

    print('\nB. C2\'s CARVE-OUT IS A DIFFERENT REFUSAL, NOT THE SAME 403')
    st, b = post(DATA, {'action': 'write', 'resource': 'law_trusttx',
                        'payload': {'id': 'ZZ-B23-PROBE', 'matter_id': 'M-1',
                                    'client_id': 'CL-1', 'type': 'Deposit',
                                    'amount': 1}}, key, para_tok)
    arm('B1. paralegal WRITE law_trusttx', st, code_of(b),
        403, 'COUNTERSIGN_REQUIRED')

    print('\nC. THE NEGATIVE CONTROLS -- without these a 403 everywhere looks '
          'like a lock')
    for res in ('law_clients', 'law_timeentries'):
        st, b = post(DATA, {'action': 'read', 'resource': res}, key, para_tok)
        arm('C%d. paralegal READ %s (allowed)'
            % (1 if res == 'law_clients' else 2, res), st, code_of(b), 200, None)
    for res in ('law_trusttx', 'law_bankstatements'):
        st, b = post(DATA, {'action': 'read', 'resource': res}, key, owner_tok)
        arm('C%d. OWNER READ %s (the lock is about the ROLE)'
            % (3 if res == 'law_trusttx' else 4, res), st, code_of(b), 200, None)
    st, b = post(DATA, {'action': 'read', 'resource': 'law_trusttx'}, key)
    arm('C5. NO SESSION READ law_trusttx (the session gate, not the lock)',
        st, code_of(b), 403, None)

    print('\nD. TEARDOWN, READ BACK')
    # `reason` IS REQUIRED WHEN DEACTIVATING -- api/_lib/employee-lifecycle.js
    # refuses 400 without one, and the first run of this probe got exactly that
    # 400, reported the teardown as having answered, and THEN FAILED D2 because
    # the credential was still live. Which is the read-back doing its job: a
    # probe that asserted only the set_active reply would have reported a clean
    # teardown and left a working paralegal sign-in on the audit licence.
    st, b = post(AUTH, {'action': 'set_active', 'employee_id': PARA_ID,
                        'active': False,
                        'reason': 'b23 live probe teardown -- this credential '
                                  'exists only to prove the trust hard-lock'},
                 key, owner_tok)
    arm('D1. set_active(false) was accepted', st, None, 200, None)
    st, b = post(AUTH, {'action': 'login', 'employee_id': PARA_ID,
                        'pin': para_pin}, key)
    arm('D2. the deactivated paralegal can no longer sign in', st, None, 401, None)

    print()
    if failures:
        print('FAILED -- %d arm(s):' % len(failures))
        for f in failures:
            print('  ' + f)
        return EXIT_FAILED
    print('VERIFIED -- the trust hard-lock, C2\'s carve-out and five negative '
          'controls all answered as stated on the deployed endpoint.')
    return EXIT_OK


if __name__ == '__main__':
    try:
        sys.exit(main())
    except sairn_http.Challenged as c:
        print('UNVERIFIED -- %s' % c)
        sys.exit(EXIT_COULD_NOT_RUN)
    except Exception as e:                        # transport, JSON, anything
        print('UNVERIFIED -- %s: %s' % (type(e).__name__, e))
        sys.exit(EXIT_COULD_NOT_RUN)
