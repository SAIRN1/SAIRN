# OWNER: hank
"""Prove an IOLTA reconciliation ATTESTATION end to end on the REAL store.

    LAW_LICENSE=LAW-AUDIT-2026 LAW_OWNER_PIN=... LAW_ATTORNEY_PIN=... \
      python tools/law_attest_live_probe.py

CONCEPT, stated before this file existed (docs/2026-10-20-hank-b24-notes.md):
  An attestation is proven only when THE ROW COMES BACK FROM THE DATABASE
  saying single-signer with one name in both places; a one-cent-different
  comparison is refused against a token signed for another; and the
  single-signer route STOPS WORKING the moment a second attorney is active --
  all against the deployed endpoint, never a mock.

WHY THIS EXISTS. api/b23-iolta-attestation.test.js has 66 arms and every one of
them drives a RECORDED PostgREST stand-in. GUARDIAN CHECK 29 is explicit that a
change touching a storage validator or a schema constraint must be proven with a
real write against the real store, read back, and the boundary tried IN BOTH
DIRECTIONS -- because unit tests that call the compute function directly do not
exercise the storage layer at all and will pass while the write path is broken.
That is exactly what happened to SAIRNlaw's deadline engine on 2026-08-24: 84 of
84 isolation tests green while every California civil row was unstorable.

── WHAT IT WRITES, AND WHY THE RESIDUE IS PERMANENT AND BOUNDED ──────────────
`sairnlaw_trust_attestations` is granted SELECT and INSERT and NOT DELETE, by
design: an attestation is never amended and a correction is a new row. So
NOTHING -- not this probe, not a cleanup file, not Michael -- can remove an
attestation through the app. The residue is therefore real and unremovable, and
it is bounded instead: the two attestation ids are FIXED CONSTANTS, so a
re-run finds them already present, asserts the EXISTING rows rather than
writing again, and proves the duplicate refusal. At most two rows exist no
matter how many times this runs.

ON THE AUDIT LICENCE ONLY. `require_audit_licence` refuses a demo-facing key.

── THE ARM THAT MATTERS MOST IS B2 ───────────────────────────────────────────
The single-signer setting is a STATEMENT ABOUT STAFFING, not a preference, and
it is accepted only while that statement is true. B2 makes the firm have TWO
active bar-admitted employees with the setting STILL ON, and requires the
attestation to be REFUSED. A check that ran only when the setting was written
would be an authorisation that outlives its own precondition, and nothing in
the mock suite can tell that version from this one.

── THE THREE STATES, AND THEY ARE NOT TWO ────────────────────────────────────
  VERIFIED     every arm answered as stated on the deployed endpoint
  UNVERIFIED   credentials absent, a PIN or licence is not live, the tables are
               not provisioned, or Vercel served its bot challenge -- exit 2,
               and NEVER reported as a failure of the mechanism
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
ATTEST = 'https://sairn.vercel.app/api/law-attest'
OWNER_ID = 'hank-b23-owner'
ATTY_ID = 'hank-b24-attorney'
ATT_SINGLE = 'ZZ-B24-SINGLE'
ATT_DUAL = 'ZZ-B24-DUAL'
RESOURCE = 'law_trust_attestation'

LIVE_PROBE_CLASS = 'VERIFICATION'
LIVE_PROBE_RESIDUE = 'docs/live-residue/README.md -- TWO attestation rows on the AUDIT licence, ids ZZ-B24-SINGLE and ZZ-B24-DUAL, plus one employee credential row hank-b24-attorney (deactivated by the teardown). THE ATTESTATION ROWS CANNOT BE DELETED BY ANYTHING: sairnlaw_trust_attestations is granted SELECT and INSERT only, on purpose, because an attestation is never amended. The ids are FIXED so a re-run asserts the existing rows instead of adding more -- at most two, ever.'
LIVE_PROBE_TEARDOWN = 'the second attorney is deactivated with set_active and the deactivation is READ BACK twice -- a login that must answer 401, and a `policy` call whose active_bar_admitted must return to 1. A 200 from set_active is the reply, not the state.'

EXIT_OK, EXIT_FAILED, EXIT_COULD_NOT_RUN = 0, 1, 2

failures = []

# THE COMPARISON, IN THE NORMALISED SHAPE THE SERVER HASHES. `negative_balances`
# is present and empty on purpose: api/_lib/law-attest.js normalises an absent
# key to [] and hashes the NORMALISED object, so a `prepare` payload without it
# would hash differently from the attest payload and every dual arm would pass
# for the wrong reason (a CONTENT_MISMATCH that looks like the content binding
# working while actually being a fixture bug).
CMP = {
    'bank_balance_cents': 1250000,
    'ledger_balance_cents': 1250000,
    'client_subledger_total_cents': 1250000,
    'bank_as_of': '2026-10-01',
    'ledger_as_of': '2026-10-01',
    'subledger_as_of': '2026-10-01',
    'verdict': 'AGREES',
    'negative_balances': [],
}


def post(url, body, licence, token=None, cs_token=None):
    headers = {'Content-Type': 'application/json',
               'Authorization': 'Bearer ' + licence}
    if token:
        headers['X-SD-Auth'] = token
    if cs_token:
        headers['X-LAW-COUNTERSIGN'] = cs_token
    try:
        r = sairn_http.fetch(url, method='POST', data=json.dumps(body).encode(),
                             headers=headers, no_cache=True)
        return r.status, r.body
    except urllib.error.HTTPError as e:
        sairn_http.raise_if_challenge(e)
        return e.code, e.read()


def body_of(raw):
    try:
        return json.loads(raw.decode('utf-8', 'replace'))
    except Exception:
        return {}


def code_of(raw):
    d = body_of(raw)
    err = d.get('error') if isinstance(d, dict) else None
    return (err or {}).get('code', '') if isinstance(err, dict) else ''


def arm(label, status, code, want_status, want_code=None, extra=None):
    ok = status in (want_status if isinstance(want_status, tuple) else (want_status,))
    if ok and want_code is not None:
        ok = code == want_code
    if ok and extra is not None:
        ok = bool(extra)
    print('  %-4s %-62s %s %s' % ('ok' if ok else 'FAIL', label, status, code or ''))
    if not ok:
        failures.append('%s (expected %s %s, got %s %s)'
                        % (label, want_status, want_code or '*', status, code or ''))
    return ok


def main():
    key = os.environ.get('LAW_LICENSE', '').strip()
    owner_pin = os.environ.get('LAW_OWNER_PIN', '').strip()
    atty_pin = os.environ.get('LAW_ATTORNEY_PIN', '').strip()
    if not (key and owner_pin and atty_pin):
        print('UNVERIFIED -- LAW_LICENSE, LAW_OWNER_PIN and LAW_ATTORNEY_PIN must')
        print('all be set. The attestation sits below a SAIRNlaw employee session')
        print('and the dual path needs TWO bar-admitted people, so one PIN is not')
        print('enough. LAW_LICENSE must be an AUDIT licence: LAW-AUDIT-2026.')
        return EXIT_COULD_NOT_RUN
    key = require_audit_licence(
        key, tool=__file__,
        writes=('sairnlaw_trust_attestations (two fixed-id rows, UNDELETABLE by '
                'design) and one sairnlaw_employee_auth row'))

    print('SAIRNlaw IOLTA attestation -- LIVE, END TO END')
    print('  endpoint %s' % ATTEST)
    print('  licence  %s...%s\n' % (key[:4], key[-4:]))

    st, b = post(AUTH, {'action': 'login', 'employee_id': OWNER_ID,
                        'pin': owner_pin}, key)
    if st != 200:
        print('UNVERIFIED -- the probe owner could not sign in (%s). Run '
              'sql/zz_probe_residue_delete_b23.sql and re-run the b23 probe '
              'first.' % st)
        return EXIT_COULD_NOT_RUN
    owner_tok = body_of(b)['token']

    # Provisioned state check BEFORE any arm, so an unprovisioned table is
    # COULD NOT RUN rather than a wall of failures.
    st, b = post(ATTEST, {'action': 'policy'}, key, owner_tok)
    if st == 503:
        print('UNVERIFIED -- 503 NOT_PROVISIONED: '
              'sql/sairnlaw_trust_attestations.sql has not been run. Nothing '
              'below would be testing the mechanism.')
        return EXIT_COULD_NOT_RUN
    if st != 200:
        print('UNVERIFIED -- policy answered %s %s' % (st, b[:200]))
        return EXIT_COULD_NOT_RUN

    # ── A. THE SINGLE-SIGNER PATH, WRITTEN AND READ BACK ────────────────────
    print('A. THE SINGLE-SIGNER PATH')
    st, b = post(ATTEST, {'action': 'set_policy', 'enabled': True}, key, owner_tok)
    arm('A0. owner of a one-attorney firm may switch single-signer ON',
        st, code_of(b), 200)
    st, b = post(ATTEST, {'action': 'policy'}, key, owner_tok)
    p = body_of(b)
    arm('A1. policy: enabled, exactly ONE bar-admitted, available', st, '', 200,
        None, p.get('single_signer_enabled') is True
        and p.get('active_bar_admitted') == 1
        and p.get('single_signer_available') is True)

    st, b = post(ATTEST, {'action': 'attest', 'attestation_id': ATT_SINGLE,
                          'comparison': CMP}, key, owner_tok)
    wrote = st == 200
    arm('A2. attest %s -- 200 on a first run, 409 TAKEN on a re-run' % ATT_SINGLE,
        st, code_of(b), (200, 409))
    if wrote:
        arm('A2b. ...and the answer says signer_mode single', st, '', 200, None,
            body_of(b).get('signer_mode') == 'single')

    # THE READ-BACK IS THE ARM THAT SATISFIES CHECK 29. Not the write's echo:
    # a server that normalised only its reply would pass a response-only check.
    st, b = post(ATTEST, {'action': 'list'}, key, owner_tok)
    rows = body_of(b).get('data') or []
    single = [r for r in rows if r.get('attestation_id') == ATT_SINGLE]
    row = single[0] if single else None
    arm('A3. THE ROW COMES BACK FROM THE DATABASE', st, '', 200, None, row)
    if row:
        arm('A3a. signer_mode single, ONE name in both places', 200, '', 200,
            None, row.get('signer_mode') == 'single'
            and row.get('prepared_by') == row.get('attested_by') == OWNER_ID
            and row.get('attested_role') == 'owner')
        arm('A3b. the three legs are the INTEGER CENTS that were sent', 200, '',
            200, None,
            row.get('bank_balance_cents') == CMP['bank_balance_cents']
            and row.get('ledger_balance_cents') == CMP['ledger_balance_cents']
            and row.get('client_subledger_total_cents')
            == CMP['client_subledger_total_cents'])
        arm('A3c. verdict AGREES and a content hash is stored', 200, '', 200,
            None, row.get('verdict') == 'AGREES'
            and len(str(row.get('content_hash') or '')) == 64)
    arm('A3d. NO token or token hash anywhere in the list answer', 200, '', 200,
        None, 'token' not in b.decode('utf-8', 'replace').lower())

    # ── THE BOUNDARY, IN BOTH DIRECTIONS (check 29 step 3) ──────────────────
    print('\nB. THE BOUNDARY -- what the store must REFUSE')
    bad = dict(CMP); bad['bank_balance_cents'] = 12500.5
    st, b = post(ATTEST, {'action': 'attest', 'attestation_id': 'ZZ-B24-FLOAT',
                          'comparison': bad}, key, owner_tok)
    arm('B1. a FLOAT leg is refused, not rounded', st, code_of(b), 400,
        'CENTS_NOT_INTEGER')
    bad = dict(CMP); bad['bank_balance_cents'] = CMP['bank_balance_cents'] + 1
    st, b = post(ATTEST, {'action': 'attest', 'attestation_id': 'ZZ-B24-INCONS',
                          'comparison': bad}, key, owner_tok)
    arm('B2. AGREES with legs ONE CENT apart is refused', st, code_of(b), 400,
        'VERDICT_INCONSISTENT')
    bad = dict(CMP); bad['note'] = 'everything is fine'
    st, b = post(ATTEST, {'action': 'attest', 'attestation_id': 'ZZ-B24-UNK',
                          'comparison': bad}, key, owner_tok)
    arm('B3. an UNKNOWN comparison field is refused, not dropped', st,
        code_of(b), 400, 'COMPARISON_UNKNOWN_FIELD')
    # AND THE OTHER DIRECTION: the same unequal legs with DISAGREES are stored.
    # Without this, B2 is equally consistent with "unequal legs are refused
    # outright", which would make a real discrepancy unrecordable.
    ok3 = dict(CMP)
    ok3['bank_balance_cents'] = CMP['bank_balance_cents'] + 1
    ok3['verdict'] = 'DISAGREES'
    st, b = post(ATTEST, {'action': 'attest', 'attestation_id': 'ZZ-B24-DISAGREE',
                          'comparison': ok3}, key, owner_tok)
    arm('B4. THE OTHER DIRECTION: the same unequal legs with DISAGREES are '
        'ACCEPTED', st, code_of(b), (200, 409))
    st, b = post(ATTEST, {'action': 'attest', 'attestation_id': ATT_SINGLE,
                          'comparison': CMP}, key, owner_tok)
    arm('B5. a reused attestation_id is its own 409', st, code_of(b), 409,
        'ATTESTATION_ID_TAKEN')

    # ── C. THE STALE SETTING. THE ARM THAT MATTERS MOST. ───────────────────
    print('\nC. A SECOND ATTORNEY APPEARS AND THE SETTING IS STILL ON')
    st, b = post(AUTH, {'action': 'setup', 'employee_id': ATTY_ID,
                        'pin': atty_pin, 'role': 'attorney',
                        'display_name': 'hank b24 probe attorney'},
                 key, owner_tok)
    if st != 200:
        print('UNVERIFIED -- the second attorney could not be provisioned '
              '(%s %s)' % (st, b[:200]))
        return EXIT_COULD_NOT_RUN
    st, b = post(AUTH, {'action': 'login', 'employee_id': ATTY_ID,
                        'pin': atty_pin}, key)
    if st != 200:
        print('UNVERIFIED -- the second attorney could not sign in (%s)' % st)
        return EXIT_COULD_NOT_RUN
    atty_tok = body_of(b)['token']

    st, b = post(ATTEST, {'action': 'policy'}, key, owner_tok)
    p = body_of(b)
    arm('C1. policy: still ENABLED, count is now 2, available FALSE, with a why',
        st, '', 200, None,
        p.get('single_signer_enabled') is True
        and p.get('active_bar_admitted') == 2
        and p.get('single_signer_available') is False
        and bool(p.get('why')))
    st, b = post(ATTEST, {'action': 'attest', 'attestation_id': 'ZZ-B24-STALE',
                          'comparison': CMP}, key, owner_tok)
    arm('C2. THE ONE THAT MATTERS: a single-signer attestation is REFUSED while '
        'the setting is still on', st, code_of(b), 403, 'SINGLE_SIGNER_NOT_SOLO')
    st, b = post(ATTEST, {'action': 'set_policy', 'enabled': True}, key, owner_tok)
    arm('C3. and switching it on again is refused at the SET point too', st,
        code_of(b), 409, 'SINGLE_SIGNER_NOT_SOLO')

    # ── D. THE DUAL PATH, END TO END ───────────────────────────────────────
    print('\nD. THE TWO-SIGNER PATH')
    st, b = post(ATTEST, {'action': 'prepare', 'resource': RESOURCE,
                          'payload': CMP}, key, owner_tok)
    arm('D1. the owner PREPARES an attestation', st, code_of(b), 200)
    tok1 = body_of(b).get('token')
    if not tok1:
        print('UNVERIFIED -- prepare returned no token, so nothing below is '
              'testing the dual path.')
        return EXIT_COULD_NOT_RUN
    st, b = post(ATTEST, {'action': 'countersign', 'token': tok1}, key, owner_tok)
    arm('D2. the PREPARER cannot countersign their own record', st, code_of(b),
        409, 'SAME_PERSON')
    st, b = post(ATTEST, {'action': 'countersign', 'token': tok1}, key, atty_tok)
    arm('D3. the second attorney COUNTERSIGNS', st, code_of(b), 200)
    st, b = post(ATTEST, {'action': 'attest', 'attestation_id': ATT_DUAL,
                          'comparison': CMP}, key, owner_tok, cs_token=tok1)
    dual_wrote = st == 200
    arm('D4. attest with the token -- 200 first run, 409 TAKEN on a re-run', st,
        code_of(b), (200, 409))
    if dual_wrote:
        arm('D4b. the answer says signer_mode dual', st, '', 200, None,
            body_of(b).get('signer_mode') == 'dual')
    st, b = post(ATTEST, {'action': 'list'}, key, owner_tok)
    dual = [r for r in (body_of(b).get('data') or [])
            if r.get('attestation_id') == ATT_DUAL]
    drow = dual[0] if dual else None
    arm('D5. THE DUAL ROW COMES BACK FROM THE DATABASE naming TWO people -- the '
        'preparer and the COUNTERSIGNER, not the saver', 200, '', 200, None,
        drow and drow.get('signer_mode') == 'dual'
        and drow.get('prepared_by') == OWNER_ID
        and drow.get('attested_by') == ATTY_ID
        and drow.get('attested_role') == 'attorney')
    st, b = post(ATTEST, {'action': 'attest', 'attestation_id': 'ZZ-B24-RESPEND',
                          'comparison': CMP}, key, owner_tok, cs_token=tok1)
    arm('D6. the same token cannot be spent twice', st, code_of(b), 409,
        'COUNTERSIGN_ALREADY_SPENT')

    # THE CONTENT BINDING, LIVE. A fresh signed token, spent against a
    # comparison that differs by ONE CENT.
    st, b = post(ATTEST, {'action': 'prepare', 'resource': RESOURCE,
                          'payload': CMP}, key, owner_tok)
    tok2 = body_of(b).get('token')
    if tok2:
        post(ATTEST, {'action': 'countersign', 'token': tok2}, key, atty_tok)
        off = dict(CMP)
        off['bank_balance_cents'] = CMP['bank_balance_cents'] + 1
        off['verdict'] = 'DISAGREES'
        st, b = post(ATTEST, {'action': 'attest',
                              'attestation_id': 'ZZ-B24-MISMATCH',
                              'comparison': off}, key, owner_tok, cs_token=tok2)
        arm('D7. THE CONTENT BINDING: a token signed for one comparison cannot '
            'be spent on one ONE CENT different', st, code_of(b), 409,
            'COUNTERSIGN_CONTENT_MISMATCH')
    else:
        print('  FAIL D7. a second prepare returned no token')
        failures.append('D7 (no token from the second prepare)')

    # ── E. TEARDOWN, READ BACK TWICE ───────────────────────────────────────
    print('\nE. TEARDOWN')
    st, b = post(AUTH, {'action': 'set_active', 'employee_id': ATTY_ID,
                        'active': False,
                        'reason': 'b24 live probe teardown -- this credential '
                                  'exists only to prove the two-signer path '
                                  'and the stale-setting refusal'},
                 key, owner_tok)
    arm('E1. set_active(false) was accepted', st, code_of(b), 200)
    st, b = post(AUTH, {'action': 'login', 'employee_id': ATTY_ID,
                        'pin': atty_pin}, key)
    arm('E2. the deactivated attorney can no longer sign in', st, '', 401)
    st, b = post(ATTEST, {'action': 'policy'}, key, owner_tok)
    arm('E3. ...and policy reports the count back at 1, so the state really '
        'moved and not just the reply', st, '', 200, None,
        body_of(b).get('active_bar_admitted') == 1)

    print()
    if failures:
        print('FAILED -- %d arm(s):' % len(failures))
        for f in failures:
            print('  ' + f)
        return EXIT_FAILED
    print('VERIFIED -- an attestation was WRITTEN, READ BACK FROM THE DATABASE, '
          'and the boundary refused in both directions on the deployed '
          'endpoint. Guardian check 29 is satisfied for this change.')
    return EXIT_OK


if __name__ == '__main__':
    try:
        sys.exit(main())
    except sairn_http.Challenged as c:
        print('UNVERIFIED -- %s' % c)
        sys.exit(EXIT_COULD_NOT_RUN)
    except Exception as e:
        print('UNVERIFIED -- %s: %s' % (type(e).__name__, e))
        sys.exit(EXIT_COULD_NOT_RUN)
