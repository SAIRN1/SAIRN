#!/usr/bin/env python3
"""tools/alf_facility_role_gate_live_probe.py -- does the DEPLOYED alf_facility
write gate actually refuse a non-management role?

    ALF_LICENSE=... ALF_EMP=... ALF_PIN=... \
      python tools/alf_facility_role_gate_live_probe.py

  0 VERIFIED    the deployed gate refused the excluded role AND allowed management
  1 FAILED      the deployed endpoint disagreed with the design
  2 UNVERIFIED  credentials absent, or the licence is unknown to the platform

UNVERIFIED IS NOT A PASS AND IS NOT A FAILURE (PR §1.11). Folding it into either
is the defect this platform keeps finding.

── WHY THIS EXISTS AND WHY THE OTHER PROOFS ARE NOT IT ─────────────────────
The gate is verified three ways already, and none of them is live:

  * api/sd-data-alf-isolation.test.js drives the REAL handler in-process --
    four non-management roles each refused 403 FORBIDDEN, each asserting nothing
    was upserted, plus a management control arm and an ordering arm;
  * ABLATION proved those arms bite: deleting the gate from api/sd-data.js is
    CAUGHT by that suite, where before the arms existed it was SILENT across
    403 suites;
  * the gate is present at api/sd-data.js:10450 on origin/main, which is what
    deploys.

CLAUDE.md's push protocol is explicit that none of that is proof of the DEPLOYED
function: "a clean `git push` is not proof."

── WHAT WAS ALREADY MEASURED LIVE, 2026-09-27, AND WHY IT STOPS SHORT ──────
Against https://sairn.vercel.app/api/sd-data, real requests, browser UA:

    no Authorization header        -> 401 {"code":"NO_LICENSE"}
    bogus bearer licence           -> 401 {"code":"INVALID_LICENSE"}
    bogus licence + bogus token    -> 401 {"code":"INVALID_LICENSE"}

So the endpoint is live and refuses before anything else. **THAT IS NOT THE ROLE
GATE.** The role check sits BELOW the licence check and below the session check,
so it is UNREACHABLE without a real licence and a real employee session. A 401 is
evidence about the licence gate and says nothing whatsoever about whether a
caregiver can rewrite the facility profile.

That is the whole reason this file exists rather than a line in a report claiming
the gate was live-verified.

── WHAT MAKES THIS GATE WORTH A LIVE PROBE AT ALL ──────────────────────────
The write carries `licensing_state`, and the compliance rules engine selects a
state's rule set from it. A caregiver flipping OH to WV does not corrupt a
cosmetic field -- it changes which staffing and training law the facility is
measured against. The gate is the only thing between those.

── THE ROLES IT DRIVES, AND ONE OF THEM IS A REAL FINDING ──────────────────
ALF_MANAGEMENT_ROLES is roleSet({ owner: true, billing: true }).

`caregiver` is offered in BOTH of sairncare.html's role dropdowns and appears in
NO roleSet({...}) in api/sd-data.js. It is therefore absent from the role-gate
tool's universe and can never be counted as an excluded role. An arm driving it
still refuses -- the lookup is falsy -- but it buys no measured coverage, so this
probe drives `nursing` and `med_aide` (both declared) FIRST and reports a
caregiver result separately rather than leaning on it.

── WHAT IT WRITES AND WHAT IT CLEANS UP ────────────────────────────────────
NOTHING, on the refusal arms -- a refused write is the point. The management
CONTROL arm does write, because refusals that refuse everybody are not a gate;
it writes to the facility id given in ALF_FACILITY_ID (default ZZ-GATE-FAC) and
restores the profile it read first. A control arm that cannot be distinguished
from a lockout is the defect tools/rf_claim_gate_live_probe.py was written after.

IT DOES NOT PROVISION CREDENTIALS. The SAIRNcode probe creates and deactivates
its own; doing that here would mean writing employee rows into a live SAIRNcare
licence to test a read-only property of a gate, and the roles needed already
exist on any real roster. Absent PINs are UNVERIFIED, not a skipped section that
manufactures a pass -- which is a defect that file records finding in itself.
"""
import json
import os
import sys
import urllib.error

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))

import sairn_http as H  # noqa: E402

BASE = os.environ.get('ALF_BASE', 'https://sairn.vercel.app')
DATA = BASE + '/api/sd-data'
AUTH = BASE + '/api/alf-auth'

LICENSE = os.environ.get('ALF_LICENSE', '')
FACILITY = os.environ.get('ALF_FACILITY_ID', 'ZZ-GATE-FAC')

# (role, employee id env, pin env). Declared roles first -- see the header.
EXCLUDED = [('nursing', 'ALF_NURSING_EMP', 'ALF_NURSING_PIN'),
            ('med_aide', 'ALF_MEDAIDE_EMP', 'ALF_MEDAIDE_PIN'),
            ('caregiver', 'ALF_CAREGIVER_EMP', 'ALF_CAREGIVER_PIN')]
MANAGEMENT = ('owner', 'ALF_EMP', 'ALF_PIN')

FINDINGS = []
UNVERIFIED = []


def post(url, body, token=None):
    hdrs = {'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + LICENSE}
    if token:
        hdrs['X-Session-Token'] = token
    try:
        r = H.fetch(url, method='POST', data=json.dumps(body).encode(),
                    headers=H.with_browser_ua(hdrs))
        raw = r if isinstance(r, (bytes, str)) else getattr(r, 'body', r)
        if isinstance(raw, bytes):
            raw = raw.decode('utf-8', 'replace')
        try:
            return 200, json.loads(raw)
        except Exception:
            return 200, {'_raw': str(raw)[:400]}
    except urllib.error.HTTPError as e:
        txt = e.read().decode('utf-8', 'replace')
        try:
            return e.code, json.loads(txt)
        except ValueError:
            return e.code, {'_raw': txt[:400]}
    except Exception as exc:                                     # noqa: BLE001
        # A TRANSPORT FAILURE IS NOT A GATE FAILURE. Third state.
        return None, {'_transport': '%s: %s' % (type(exc).__name__, exc)}


def login(role, emp_env, pin_env):
    emp, pin = os.environ.get(emp_env, ''), os.environ.get(pin_env, '')
    if not emp or not pin:
        UNVERIFIED.append('%s: %s / %s are not set, so the %s arm DID NOT RUN'
                          % (role, emp_env, pin_env, role))
        return None
    code, body = post(AUTH, {'action': 'login', 'employee_id': emp, 'pin': pin})
    if code != 200 or not isinstance(body, dict) or not body.get('token'):
        UNVERIFIED.append('%s: login returned %s %s -- no session, so the arm '
                          'DID NOT RUN and this is NOT a gate result'
                          % (role, code, json.dumps(body)[:160]))
        return None
    return body['token']


def main():
    print('ALF_FACILITY WRITE-GATE LIVE PROBE -- %s' % DATA)
    print('')

    if not LICENSE:
        sys.stderr.write(
            'UNVERIFIED -- ALF_LICENSE is not set, so NOTHING was driven.\n'
            'The role gate sits BELOW the licence check and below the session '
            'check, so it is unreachable without a real licence and a real '
            'employee session. Measured 2026-09-27: an unauthenticated write to '
            'alf_facility returns 401 NO_LICENSE and a bogus licence returns 401 '
            'INVALID_LICENSE -- real live evidence about the LICENCE gate, and no '
            'evidence at all about the ROLE gate.\n'
            'This is the THIRD STATE. It is NOT "the gate is fine".\n')
        return 2

    # ── PRE-FLIGHT: is the licence even known to the platform? ──────────────
    code, body = post(AUTH, {'action': 'check_license'})
    if code != 200:
        sys.stderr.write('UNVERIFIED -- check_license returned %s %s. The licence '
                         'is unknown to the deployed platform, so no arm below '
                         'could have run. NOT a gate failure.\n'
                         % (code, json.dumps(body)[:200]))
        return 2
    print('licence accepted by the deployed platform.')
    print('')

    # ── THE REFUSAL ARMS ────────────────────────────────────────────────────
    print('EXCLUDED ROLES -- each must be refused 403 FORBIDDEN:')
    ran = 0
    for role, emp_env, pin_env in EXCLUDED:
        token = login(role, emp_env, pin_env)
        if not token:
            print('  ....  %-10s DID NOT RUN' % role)
            continue
        ran += 1
        code, resp = post(DATA, {
            'action': 'write', 'resource': 'alf_facility',
            'payload': {'id': FACILITY, 'licensing_state': 'WV'}}, token)
        got = (resp or {}).get('error', {}).get('code')
        if code is None:
            UNVERIFIED.append('%s: transport failure -- %s'
                              % (role, resp.get('_transport')))
            print('  ....  %-10s COULD NOT TELL (transport)' % role)
        elif code == 403 and got == 'FORBIDDEN':
            print('  ok    %-10s 403 FORBIDDEN' % role)
        else:
            FINDINGS.append(
                '%s got %s %s writing alf_facility with licensing_state=WV -- the '
                'DEPLOYED gate did not refuse a non-management role, and the '
                'compliance engine trusts that field'
                % (role, code, json.dumps(resp)[:200]))
            print('  FAIL  %-10s %s %s' % (role, code, json.dumps(resp)[:120]))

    # ── THE CONTROL: refusing everybody is not a gate ───────────────────────
    print('')
    print('CONTROL -- management must still be ALLOWED:')
    role, emp_env, pin_env = MANAGEMENT
    token = login(role, emp_env, pin_env)
    if not token:
        UNVERIFIED.append(
            'the MANAGEMENT control arm did not run, so even if every refusal '
            'above passed, this run cannot tell a working gate from a total '
            'lockout. That distinction is the point of the control.')
        print('  ....  %-10s DID NOT RUN' % role)
    else:
        code, resp = post(DATA, {'action': 'read', 'resource': 'alf_facility'}, token)
        before = None
        if code == 200 and isinstance(resp, dict):
            for row in (resp.get('data') or []):
                if str(row.get('id')) == FACILITY:
                    before = row
        code, resp = post(DATA, {
            'action': 'write', 'resource': 'alf_facility',
            'payload': dict(before or {'id': FACILITY}, id=FACILITY)}, token)
        if code == 200:
            print('  ok    %-10s allowed (control passes; the refusals above are '
                  'a split, not a lockout)' % role)
        else:
            FINDINGS.append(
                'the MANAGEMENT control arm got %s %s -- the deployed gate is '
                'refusing management too, which is a lockout rather than a gate'
                % (code, json.dumps(resp)[:200]))
            print('  FAIL  %-10s %s %s' % (role, code, json.dumps(resp)[:120]))

    print('')
    if FINDINGS:
        print('FAILED -- the DEPLOYED endpoint disagreed with the design:')
        for f in FINDINGS:
            print('  * %s' % f)
        return 1
    if UNVERIFIED or ran == 0:
        print('UNVERIFIED -- the third state, and NOT a pass:')
        for u in UNVERIFIED:
            print('  * %s' % u)
        print('')
        print('%d of %d excluded-role arms ran. Nothing here says the gate is '
              'broken; it says this run did not establish that it works.'
              % (ran, len(EXCLUDED)))
        return 2
    print('VERIFIED -- the deployed gate refused every excluded role that ran and')
    print('allowed management. In-process arms, ablation and source agreed; now the')
    print('deployment does too.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
