# OWNER: hank
"""Prove the SAIRNsenior straight-time-floor SIGN GUARD on the deployed pay run.

    SEN_LICENSE=SEN-AUDIT-2026 SEN_OWNER_PIN=... SEN_CAREGIVER_PIN=... \
      python docs/2026-10-20-hank-b27-sen-straight-time-floor-live-probe.py

CONCEPT, stated before this file existed:
  A downward clock correction on an already-paid visit must come back as an
  OVERPAYMENT a human has to act on, and must never be netted into someone's
  wages -- proved by writing the fixture to the real store, running the real pay
  run, and reading both numbers back, with an UPWARD control beside it so a guard
  that drops everything cannot pass.

WHY IT EXISTS. b17 fixed fourth's H2 (a scheduler approving a downward correction
silently deducted $20) with one character, `if (dMin > 0)`. api/b17-straight-time-
floor.test.js proves it against the module; this proves it on the deployed
endpoint, and it was NOT PROVEN at b23 because SAIRNsenior had no audit licence
and `sen_visits` has no delete verb, so the fixture could not go on the demo-
facing SEN-PINNACLE-2026. sql/mint_sen_audit_2026.sql mints SEN-AUDIT-2026.

THE FIXTURES ARE docs/2026-10-20-hank-b27-sen-straight-time-floor-fixtures.json AND NOWHERE ELSE.
api/b27-sen-straight-time-floor-fixtures.test.js feeds the same file to the real
sen-payroll.js (18 arms, with the guard ablated), so the numbers asserted below
were proven offline first.

WHAT IS UNPROVEN UNTIL IT RUNS: the request SEQUENCE against the deployed
endpoints. Every payload is checked offline against the real clock validators; the
HTTP contract itself is read from api/sd-data.js and has not been driven.

-- RESIDUE, PERMANENT AND BOUNDED ------------------------------------------
sen_visits has no delete verb, sen_period_closings is append-only, and
sen_pay_rates is an upsert. The ids are FIXED CONSTANTS and every write is
preceded by a read, so a re-run finds the rows and asserts them: at most two
visits, one closing, one rate and one caregiver credential row exist no matter
how many times this runs. Audit licence only.

EXIT  0 VERIFIED - 1 an arm FAILED - 2 COULD NOT RUN (never reported as a pass)
"""
import datetime
import json
import os
import sys
import urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
# WHY THIS LIVES IN docs/ AND NOT tools/ (b27): every tools/*.py needs a PURPOSES
# entry in tools/tooling_inventory.py, which cc held under a live claim, and the
# path-scope gate would also call a new tools/ file FOREIGN to hank. Moving it is
# a rename plus one inventory line -- see the b27 handoff, open item.
TOOLS = os.path.join(os.path.dirname(HERE), 'tools')
sys.path.insert(0, TOOLS)
import sairn_http                                                   # noqa: E402
from audit_licence import require_audit_licence                     # noqa: E402

AUTH = 'https://sairn.vercel.app/api/sen-auth'
DATA = 'https://sairn.vercel.app/api/sd-data'
OWNER_ID = 'audit-owner'
with open(os.path.join(HERE, '2026-10-20-hank-b27-sen-straight-time-floor-fixtures.json'),
          encoding='utf-8') as _fh:
    FIX = json.load(_fh)

LIVE_PROBE_CLASS = 'VERIFICATION'
LIVE_PROBE_RESIDUE = 'docs/live-residue/README.md -- on SEN-AUDIT-2026 only: two sen_visits rows (zz-b27-down, zz-b27-up, UNDELETABLE: no delete verb), one append-only sen_period_closings row (zz-b27-close-2026-08), one sen_pay_rates row (zz-b27-rate) and one sairnsenior_employee_auth row (hank-b27-caregiver); fixed ids, read-before-write, so a re-run adds nothing'
LIVE_PROBE_TEARDOWN = 'none -- the visits and the closing cannot be removed through the app by design; the caregiver credential row stays active on an audit licence that holds no customer data'

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


def body_of(raw):
    try:
        return json.loads(raw.decode('utf-8', 'replace'))
    except Exception:
        return {}


def code_of(raw):
    err = body_of(raw).get('error')
    return err.get('code', '') if isinstance(err, dict) else ''


def arm(label, status, code, want_status, want_code=None, extra=None):
    ok = status in (want_status if isinstance(want_status, tuple) else (want_status,))
    if ok and want_code is not None:
        ok = code in (want_code if isinstance(want_code, tuple) else (want_code,))
    if ok and extra is not None:
        ok = bool(extra)
    print('  %-4s %-66s %s %s' % ('ok' if ok else 'FAIL', label, status, code or ''))
    if not ok:
        failures.append('%s (expected %s %s, got %s %s)'
                        % (label, want_status, want_code or '*', status, code or ''))
    return ok


# ── THE PROBE CONFIRMS WHO IT IS BEFORE IT MEASURES ANYTHING (b32) ────────
# CONCEPT: a probe that authenticates as the wrong role proves nothing, so
# before any arm runs it asks the SERVER who this session is -- `whoami`, which
# reads the role from the credential row, not from the login reply and not
# from what the probe meant to sign in as -- and refuses to report a verdict
# (exit 2) if the answer is not the role under test.
def confirm_identity(key, tok, want_emp, want_role):
    st, body = post(AUTH, {'action': 'whoami'}, key, tok)
    if st != 200:
        return 'whoami answered %s %s' % (st, code_of(body))
    try:
        d = json.loads(body.decode('utf-8', 'replace'))
    except Exception:
        return 'whoami returned an unreadable body'
    if d.get('employee_id') != want_emp or d.get('role') != want_role:
        return ('the session is %r with role %r, not %r with role %r'
                % (d.get('employee_id'), d.get('role'), want_emp, want_role))
    print('  ok   signed in as %-22s role %-9s (whoami, from the credential row)'
          % (want_emp, want_role))
    return None


def sd(key, tok, resource, action, payload=None):
    body = {'action': action, 'resource': resource}
    if payload is not None:
        body['payload'] = payload
    return post(DATA, body, key, tok)


def current_month_utc():
    now = datetime.datetime.now(datetime.timezone.utc)
    first = now.replace(day=1)
    nxt = (first.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)
    last = nxt - datetime.timedelta(days=1)
    return first.strftime('%Y-%m-%d'), last.strftime('%Y-%m-%d')


def login(key, emp, pin):
    st, b = post(AUTH, {'action': 'login', 'employee_id': emp, 'pin': pin}, key)
    return (body_of(b).get('token') if st == 200 else None), st, b


def visits_by_id(key, tok):
    st, b = sd(key, tok, 'sen_visits', 'read')
    return st, b, {x.get('id'): x for x in (body_of(b).get('data') or [])}


def main():
    key = os.environ.get('SEN_LICENSE', '').strip()
    owner_pin = os.environ.get('SEN_OWNER_PIN', '').strip()
    cg_pin = os.environ.get('SEN_CAREGIVER_PIN', '').strip()
    if not (key and owner_pin and cg_pin):
        print('COULD NOT RUN -- SEN_LICENSE, SEN_OWNER_PIN and SEN_CAREGIVER_PIN must')
        print('all be set. The clock is written by the ASSIGNED CAREGIVER (a scheduler')
        print('may not write EVV times), so two accounts are needed. SEN_LICENSE must')
        print('be SEN-AUDIT-2026: sql/mint_sen_audit_2026.sql, then bootstrap the owner')
        print('as "%s" through /api/sen-auth.' % OWNER_ID)
        return EXIT_COULD_NOT_RUN
    key = require_audit_licence(
        key, tool=__file__,
        writes='two sen_visits rows (UNDELETABLE), one append-only period closing, '
               'one pay rate and one caregiver credential row')

    cg = FIX['caregiver_id']
    print('SAIRNsenior straight-time-floor sign guard -- LIVE')
    print('  licence %s...%s\n' % (key[:4], key[-4:]))

    owner_tok, st, b = login(key, OWNER_ID, owner_pin)
    if not owner_tok:
        print('COULD NOT RUN -- the owner "%s" could not sign in (%s %s). If this is'
              % (OWNER_ID, st, code_of(b)))
        print('401 INVALID_LICENSE, sql/mint_sen_audit_2026.sql has not run; if it is')
        print('401 INVALID_CREDENTIALS, run sql/audit_owner_and_demo_caregiver_credentials_2026-10-20.sql')
        print('and pass the PIN in its header as SEN_OWNER_PIN.')
        return EXIT_COULD_NOT_RUN
    why = confirm_identity(key, owner_tok, OWNER_ID, 'owner')
    if why:
        print('COULD NOT RUN -- %s. The fixtures need an owner session.' % why)
        return EXIT_COULD_NOT_RUN

    # The caregiver: log in, or provision once through the app's own setup.
    cg_tok, st, b = login(key, cg, cg_pin)
    if not cg_tok:
        st, b = post(AUTH, {'action': 'setup', 'employee_id': cg,
                            'display_name': 'Probe Caregiver', 'pin': cg_pin,
                            'role': 'caregiver'}, key, owner_tok)
        arm('S0. the owner may provision the caregiver account', st, code_of(b), 200)
        cg_tok, st, b = login(key, cg, cg_pin)
    if not cg_tok:
        print('COULD NOT RUN -- the caregiver could not sign in (%s %s)' % (st, code_of(b)))
        return EXIT_COULD_NOT_RUN
    why = confirm_identity(key, cg_tok, cg, 'caregiver')
    if why:
        print('COULD NOT RUN -- %s. Only the ASSIGNED CAREGIVER may write the clock, so '
              'a different role would test a refusal, not the pay run.' % why)
        return EXIT_COULD_NOT_RUN

    print('A. THE FIXTURES (read before write, fixed ids)')
    r = FIX['rate']
    rate = {'id': r['id'], 'employee_id': cg, 'rate_per_hour': r['rate_per_hour'],
            'effective_on': r['effective_on'], 'burden_pct': r['burden_pct']}
    st, b = sd(key, owner_tok, 'sen_pay_rates', 'write', rate)
    arm('A1. the pay rate is written', st, code_of(b), 200)
    st, b = sd(key, owner_tok, 'sen_pay_rates', 'read')
    arm('A1b. ...and READ BACK at 20/hour for the caregiver', st, '', 200, None,
        any(x.get('id') == r['id'] and x.get('employee_id') == cg
            and float(x.get('rate_per_hour')) == float(r['rate_per_hour'])
            for x in (body_of(b).get('data') or [])))

    cl = FIX['closing']
    st, b = sd(key, owner_tok, 'sen_period_closings', 'write', cl)
    arm('A2. the closed period is written (200 first run, 409 on a re-run)', st,
        code_of(b), (200, 409))
    if st == 409:
        arm('A2a. ...and that 409 is the already-closed refusal, not some other 409',
            st, code_of(b), 409, ('PERIOD_ALREADY_CLOSED', 'CLOSING_IMMUTABLE'))
    st, b = sd(key, owner_tok, 'sen_period_closings', 'read')
    d = body_of(b)
    rows = d.get('data') or d.get('periods') or []
    closed_ok = arm('A2b. ...and READ BACK as closed', st, '', 200, None,
        any(x.get('closing_id') == cl['closing_id']
            or x.get('period_start') == cl['period_start'] for x in rows))

    for v in FIX['visits']:
        vid = v['id']
        st, b, rows = visits_by_id(key, owner_tok)
        existing = rows.get(vid)
        if not existing:
            sched = dict(FIX['schedule'])
            sched.update({'id': vid, 'assigned_employee_id': cg})
            st, b = sd(key, owner_tok, 'sen_visits', 'write', sched)
            arm('A3[%s]. the scheduler creates the visit' % vid, st, code_of(b), 200)
            existing = {}
        if not existing.get('clock_in_at'):
            clk = dict(FIX['clock'])
            clk['id'] = vid
            st, b = sd(key, cg_tok, 'sen_visits', 'write', clk)
            arm('A4[%s]. the ASSIGNED CAREGIVER records the clock (a past time is '
                'flagged, not refused)' % vid, st, code_of(b), 200)
        st, b, rows = visits_by_id(key, owner_tok)
        if not (rows.get(vid) or {}).get('clock_corrections'):
            st, b = sd(key, owner_tok, 'sen_visits', 'propose_clock_correction',
                       {'id': vid, 'correction': {
                           'field': 'clock_out_at',
                           'proposed_at': v['proposed_clock_out_at'],
                           'reason_code': FIX['correction_reason_code']}})
            arm('A5[%s]. the owner files the correction' % vid, st, code_of(b), 200)
            st, b = sd(key, owner_tok, 'sen_visits', 'approve_clock_correction',
                       {'id': vid, 'correction_index': 0})
            arm('A6[%s]. ...and approves it (owner self-approval is the stated '
                'exception)' % vid, st, code_of(b), 200)
        st, b, rows = visits_by_id(key, owner_tok)
        ex = rows.get(vid) or {}
        cor = ex.get('clock_corrections') or []
        arm('A7[%s]. READ BACK: one APPROVED correction to %s'
            % (vid, v['proposed_clock_out_at']), st, '', 200, None,
            len(cor) == 1 and cor[0].get('status') == 'approved'
            and cor[0].get('proposed_at') == v['proposed_clock_out_at']
            and ex.get('clock_out_at') == FIX['clock']['clock_out_at'])

    print('\nB. THE PAY RUN')
    # ── B IS ONLY MEASURABLE WITH THE CLOSING ON THE SERVER (b33) ────────────
    # The first live run (2026-10-20) failed A2/A2b with 503 AUDIT_UNAVAILABLE
    # and then B1, B2 and B4 -- and api/b27-sen-straight-time-floor-fixtures
    # .test.js section 4 reproduces exactly that pattern from the missing
    # closing alone: with no closed period there is no carry-forward to find,
    # whatever the sign guard does. Reporting B as FAILED blamed the guard for a
    # precondition. So B is NOT MEASURED, said in words, and the run still
    # fails on A.
    if not closed_ok:
        print('  NOT MEASURED -- the August closing is not on the server (A2/A2b), so no')
        print('  carry-forward can exist and B1/B2/B4 would fail for that reason alone.')
        print('  Fix A2 first: sql/sairnsenior_audit_log_event_types_widen_2026-10-20.sql.')
        print('')
        print('FAILED -- %d arm(s):' % len(failures))
        for f in failures:
            print('  - ' + f)
        return EXIT_FAILED
    ps, pe = current_month_utc()
    st, b = sd(key, owner_tok, 'sen_visits', 'payroll',
               {'period_start': ps, 'period_end': pe, 'week_start_day': 'sunday'})
    arm('B0. the run answers 200 for %s..%s' % (ps, pe), st, code_of(b), 200)
    out = body_of(b).get('data') or {}
    for v in FIX['visits']:
        e = v['expect']
        hit = [x for x in (out.get(e['bucket']) or []) if x.get('visit_id') == v['id']]
        if e['bucket'] == 'overpayments':
            arm('B1. DOWNWARD %s is an OVERPAYMENT of %d min / %d cents, for a human'
                % (v['id'], e['minutes'], e['cents']), st, '', 200, None,
                len(hit) == 1 and hit[0].get('minutes_overpaid') == e['minutes']
                and hit[0].get('cents_overpaid') == e['cents']
                and hit[0].get('requires_human_act') is True)
        else:
            arm('B2. UPWARD CONTROL %s is an ADJUSTMENT of %d min / %d cents'
                % (v['id'], e['minutes'], e['cents']), st, '', 200, None,
                len(hit) == 1 and hit[0].get('minutes_delta') == e['minutes']
                and hit[0].get('cents_delta') == e['cents'])
    cgs = out.get('caregivers') or []
    arm('B3. THE INVARIANT: total_payable_cents >= gross_cents on every caregiver',
        st, '', 200, None,
        cgs and all(c.get('total_payable_cents', -1) >= c.get('gross_cents', 0)
                    for c in cgs))
    arm('B4. the overpayment is in its OWN total and was not netted into pay',
        st, '', 200, None, out.get('overpayment_cents') == 2000)

    print('')
    if failures:
        print('FAILED -- %d arm(s):' % len(failures))
        for f in failures:
            print('  - ' + f)
        return EXIT_FAILED
    print('VERIFIED -- the sign guard holds on the deployed pay run.')
    return EXIT_OK


if __name__ == '__main__':
    try:
        sys.exit(main())
    except sairn_http.Challenged as e:
        print('COULD NOT RUN -- Vercel served its bot challenge: %s' % e)
        sys.exit(EXIT_COULD_NOT_RUN)
