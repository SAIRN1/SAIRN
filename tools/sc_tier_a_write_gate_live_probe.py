"""Exercise SAIRNcode's Tier A billing WRITE gate -- ALLOW and DENY -- against
the LIVE endpoint.

WHY THIS EXISTS. The gate shipped on 2026-09-14 and was verified two ways that
are both real and neither of which is live: tests/sairncode_gates.js drives the
REAL handler in-process (102 arms) and tests/sairncode_gates_mutation_control.js
proves those arms refuse 25 planted defects. What neither can prove is that the
DEPLOYED function behaves the same way, and CLAUDE.md's push protocol is explicit
that a clean push is not proof. The client half WAS live-verified by fetching the
deployed page; the server half sits BELOW the licence check, so it cannot be
reached without a real licence and a real session.

Same shape and the same reasoning as tools/rf_claim_gate_live_probe.py, which was
written after a green 11/11 run had SKIPPED the two arms that mattered.

── THE THREE STATES THIS REPORTS, AND THEY ARE NOT TWO ─────────────────────────
  VERIFIED     the gate allowed and refused exactly as designed, live
  UNVERIFIED   credentials are absent, or the licence is unknown to the platform
               because sql/demo_owner_credentials_2026-09-03.sql has never been
               run -- exit 2, and NOT reported as a gate failure
  FAILED       the live endpoint disagreed with the design -- exit 1

Folding UNVERIFIED into either of the others is the defect this platform keeps
finding (PR 1.11): "could not tell" is a third state and is never "fine".

── WHAT IT CREATES, AND WHAT IT CLEANS UP ──────────────────────────────────────
Everything is labelled ZZ-GATE-* so a later reader can see at a glance what it is
and why:

  * two credentials -- zz-gate-coder (role coder) and zz-gate-auditor (auditor),
    because the DENY-by-ROLE path needs a real subject and a no-session refusal
    only proves the session half
  * up to three data rows -- ZZ-GATE-CLAIM in sc_claims, ZZ-GATE-COMP in
    sc_compliance, and ZZ-GATE-CODED in sc_coded_items. The third is the
    coder's own UNGATED resource, written by the control arm that makes the
    six refusals a split rather than a lockout. It said "two" until
    2026-09-15 because the control arm was added after this paragraph was
    written and nothing re-reads a docstring; the row it leaves behind is a
    SUCCESSFUL write, so it is the one row here that a reader would find in
    real data.

UNLIKE the roofing probe, this one CAN clean up: SAIRNcode declares a `delete`
verb on all 28 resources and an admin session may use it, so the rows are deleted
and both credentials are DEACTIVATED (never orphaned active). Cleanup is reported
per item and a failure to clean up is a FINDING, not a silent exit -- a probe that
leaves live credentials behind is worse than one that never ran.

CREDENTIALS COME FROM THE ENVIRONMENT, NEVER THIS FILE:

    SC_LICENSE   the licence key            (e.g. the demo licence)
    SC_EMP       an admin employee_id
    SC_PIN       that admin's PIN

docs/2026-09-03-demo-credentials.md records SAIRNcode's demo row. Note its own
warning: none of those PINs work until the SQL in that document has been run, and
that is Michael's action, not this probe's.

Run:  SC_LICENSE=... SC_EMP=... SC_PIN=... python tools/sc_tier_a_write_gate_live_probe.py
"""

import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import sairn_http                                                # noqa: E402


def soft_delete_only():
    """The Tier A names that may be hidden and never destroyed, READ FROM THE
    REGISTRY by running it. Not typed here: a copy of that list in a probe is
    the drift api/_resources exists to prevent, and it would go stale silently
    the first time a resource is added -- the probe would then hard-delete a
    Tier A record while reporting a clean run, which is the worst possible
    direction for this particular tool to be wrong in."""
    src = ('process.stdout.write(JSON.stringify('
           'require("./api/_resources/sairncode").tierASoftDeleteOnly||[]));')
    try:
        r = subprocess.run(['node', '-e', src], cwd=ROOT,
                           capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.SubprocessError) as e:
        return None, '%s: %s' % (type(e).__name__, e)
    if r.returncode != 0:
        return None, (r.stderr or '')[:300]
    try:
        names = json.loads(r.stdout)
    except ValueError as e:
        return None, str(e)
    return (names, None) if names else (None, 'the registry returned an empty list')

AUTH = 'https://sairn.vercel.app/api/sc-auth'
DATA = 'https://sairn.vercel.app/api/sd-data'

LICENSE = os.environ.get('SC_LICENSE', '')
EMP = os.environ.get('SC_EMP', '')
PIN = os.environ.get('SC_PIN', '')

CODER_ID = 'zz-gate-coder'
AUDITOR_ID = 'zz-gate-auditor'
CODER_PIN = os.environ.get('SC_CODER_PIN', '')
AUDITOR_PIN = os.environ.get('SC_AUDITOR_PIN', '')

CLAIM_ROW = 'ZZ-GATE-CLAIM'
COMP_ROW = 'ZZ-GATE-COMP'
CODED_ROW = 'ZZ-GATE-CODED'

fails = []
notes = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name + ('' if cond else '\n         ' + detail))
    if not cond:
        fails.append(name)


def unverified(why):
    print('\nUNVERIFIED -- the gate was NOT exercised, and this is not a pass.')
    print('  ' + why)
    print('\n  This is the THIRD state, reported as itself. The in-process suite')
    print('  (tests/sairncode_gates.js, 102 arms) and its mutation control (25')
    print('  planted defects, all caught) still stand; what is missing is proof')
    print('  that the DEPLOYED function behaves the same way.')
    sys.exit(2)


def post(url, payload, key=None, token=None):
    """Returns (status, body_or_None). Never collapses a transport failure into
    a status code -- sairn_http raises Challenged/OSError and the caller decides."""
    headers = {}
    if token:
        headers['X-SD-Auth'] = token
    r = sairn_http.fetch_json(url, payload=payload, key=key, headers=headers, timeout=60)
    return r.status, r.body


def main():
    print('SAIRNcode -- the Tier A billing write gate, against the LIVE endpoint\n')

    # FAIL CLOSED IF THE REGISTRY CANNOT BE READ (PR 1.11). Guessing the verb
    # would mean sending a destroying 'delete' at a Tier A record on a live
    # tenant, so "could not tell" is UNVERIFIED and never a default.
    soft_only, why = soft_delete_only()
    if soft_only is None:
        unverified('could not read tierASoftDeleteOnly from '
                   'api/_resources/sairncode.js, so the cleanup verb for each '
                   'resource is unknown: %s' % why)

    if not LICENSE or not EMP or not PIN:
        unverified('SC_LICENSE, SC_EMP and SC_PIN are not all set in the '
                   'environment. See docs/2026-09-03-demo-credentials.md for the '
                   'SAIRNcode row -- and note its warning that those PINs do not '
                   'work until sql/demo_owner_credentials_2026-09-03.sql has been '
                   'run in Supabase, which is Michael\'s action.')

    # ── 0. SIGN IN AS ADMIN ───────────────────────────────────────────────────
    try:
        st, body = post(AUTH, {'action': 'login', 'employee_id': EMP, 'pin': PIN},
                        key=LICENSE)
    except sairn_http.Challenged as e:
        unverified('Vercel bot mitigation challenged the request: %s' % e)
    except Exception as e:                                       # noqa: BLE001
        unverified('could not reach %s: %s: %s' % (AUTH, type(e).__name__, e))

    code = (body or {}).get('error', {}).get('code', '') if isinstance(body, dict) else ''
    if st == 401 and code in ('INVALID_LICENSE', 'UNKNOWN_LICENSE'):
        unverified('the platform does not know licence %r (401 %s). That is the '
                   'documented state before sql/demo_owner_credentials_2026-09-03'
                   '.sql is run -- it is NOT a gate failure.' % (LICENSE, code))
    if st != 200 or not isinstance(body, dict) or not body.get('token'):
        unverified('login did not return a token (HTTP %s): %s'
                   % (st, json.dumps(body)[:200]))
    admin = body['token']
    print('  ok   signed in as %s, role %s' % (EMP, body.get('role')))
    if body.get('role') != 'admin':
        unverified('SC_EMP is role %r, not admin. This probe provisions the DENY '
                   'subjects and cleans up after itself, and both need admin.'
                   % body.get('role'))

    # ── 1. NO SESSION IS 401, ON EVERY TIER A RESOURCE ───────────────────────
    # The half that needs no extra credential, and the one the gate was built
    # for: these accepted a write from the licence key alone until 2026-09-14.
    #
    # THIS WAS A HAND-WRITTEN LIST OF SIX WHILE THE REGISTER SAID SEVEN -- the
    # defect this probe exists to catch, surviving inside the probe itself.
    # sc_denial_events was missing here for the same reason it was missing from
    # SC_TIER_A_WRITE_GATED, and the consequence here was worse than the
    # handler's: "all six refuse" was TRUE and covered six of seven, so a green
    # run was evidence about a population nobody had checked was the right one.
    # A verification tool reporting clean over the wrong denominator is the one
    # failure mode it must not have.
    #
    # Found 2026-09-15 by tools/pinned_list_drift_check.py, written that day to
    # sweep for exactly this shape after it had been found twice by hand -- and
    # this line was the first row it printed.
    #
    # DERIVED FROM THE REGISTRY NOW, like the cleanup verbs below.
    SIX = sorted(soft_only)
    print('\n1. a write with the LICENCE KEY ALONE is refused on all %d Tier A '
          'resources' % len(SIX))
    for res in SIX:
        st, body = post(DATA, {'action': 'write', 'resource': res, 'app_id': 'sairncode',
                               'payload': {'id': 'ZZ-GATE-NOSESSION'}}, key=LICENSE)
        c = (body or {}).get('error', {}).get('code', '') if isinstance(body, dict) else ''
        check('%-22s no session -> %s %s' % (res, st, c),
              st == 401 and c == 'NO_SESSION', json.dumps(body)[:160])

    # ── 2. READS ARE UNTOUCHED ───────────────────────────────────────────────
    # The other half of the decision, and the half a role gate most easily
    # breaks by accident.
    print('\n2. and a READ with the licence key alone still works on all %d' % len(SIX))
    for res in SIX:
        st, body = post(DATA, {'action': 'read', 'resource': res,
                               'app_id': 'sairncode', 'payload': {}}, key=LICENSE)
        check('%-22s read -> %s' % (res, st), st == 200, json.dumps(body)[:160])

    # ── 3. THE ALLOW PATH ────────────────────────────────────────────────────
    # Without this every arm above would pass on a deployment that refused
    # everything, which is a worse outage than the gap the gate closed.
    print('\n3. CONTROL: an admin session DOES write')
    st, body = post(DATA, {'action': 'write', 'resource': 'sc_claims',
                           'app_id': 'sairncode',
                           'payload': {'id': CLAIM_ROW, 'claimId': CLAIM_ROW,
                                       'patient': 'ZZ GATE PROBE', 'amount': 1,
                                       'status': 'Draft'}},
                    key=LICENSE, token=admin)
    check('admin write sc_claims -> %s' % st, st == 200, json.dumps(body)[:200])

    # ── 4. DENY BY ROLE ──────────────────────────────────────────────────────
    # A no-session refusal proves the SESSION half only. The role half needs a
    # real signed-in subject whose role is not on the list.
    print('\n4. DENY BY ROLE -- provisioning real subjects')
    if not CODER_PIN or not AUDITOR_PIN:
        notes.append('SC_CODER_PIN / SC_AUDITOR_PIN not set, so sections 4 and 5 '
                     'were SKIPPED -- the role half of the gate is UNVERIFIED live. '
                     'Set both to 6-8 digit values and re-run; this probe '
                     'provisions and then deactivates the accounts itself.')
        print('  SKIPPED -- SC_CODER_PIN and SC_AUDITOR_PIN are not set. Reported, '
              'never silently passed.')
    else:
        for emp, role, pin in ((CODER_ID, 'coder', CODER_PIN),
                               (AUDITOR_ID, 'auditor', AUDITOR_PIN)):
            st, body = post(AUTH, {'action': 'setup', 'employee_id': emp, 'pin': pin,
                                   'role': role, 'display_name': 'ZZ GATE ' + role},
                            key=LICENSE, token=admin)
            check('provisioned %s as %s -> %s' % (emp, role, st), st == 200,
                  json.dumps(body)[:200])

        tokens = {}
        for emp, pin in ((CODER_ID, CODER_PIN), (AUDITOR_ID, AUDITOR_PIN)):
            st, body = post(AUTH, {'action': 'login', 'employee_id': emp, 'pin': pin},
                            key=LICENSE)
            tokens[emp] = (body or {}).get('token') if isinstance(body, dict) else None
            check('signed in as %s -> %s' % (emp, st),
                  st == 200 and tokens[emp], json.dumps(body)[:200])

        if tokens.get(CODER_ID):
            for res in SIX:
                st, body = post(DATA, {'action': 'write', 'resource': res,
                                       'app_id': 'sairncode',
                                       'payload': {'id': 'ZZ-GATE-CODER'}},
                                key=LICENSE, token=tokens[CODER_ID])
                c = (body or {}).get('error', {}).get('code', '') if isinstance(body, dict) else ''
                check('coder write %-22s -> %s %s' % (res, st, c),
                      st == 403 and c == 'FORBIDDEN', json.dumps(body)[:160])
            # The coder's OWN resource is ungated, which is what makes the six
            # above a split rather than a lockout.
            st, body = post(DATA, {'action': 'write', 'resource': 'sc_coded_items',
                                   'app_id': 'sairncode',
                                   'payload': {'id': CODED_ROW}},
                            key=LICENSE, token=tokens[CODER_ID])
            check('CONTROL: coder write sc_coded_items -> %s (its own resource, '
                  'ungated)' % st, st == 200, json.dumps(body)[:200])

        # ── 5. THE ONE PER-RESOURCE OVERRIDE ─────────────────────────────────
        if tokens.get(AUDITOR_ID):
            print('\n5. the auditor override -- sc_compliance only')
            st, body = post(DATA, {'action': 'write', 'resource': 'sc_compliance',
                                   'app_id': 'sairncode',
                                   'payload': {'id': COMP_ROW, 'finding': 'ZZ GATE PROBE'}},
                            key=LICENSE, token=tokens[AUDITOR_ID])
            check('auditor write sc_compliance -> %s' % st, st == 200,
                  json.dumps(body)[:200])
            for res in [r for r in SIX if r != 'sc_compliance']:
                st, body = post(DATA, {'action': 'write', 'resource': res,
                                       'app_id': 'sairncode',
                                       'payload': {'id': 'ZZ-GATE-AUD'}},
                                key=LICENSE, token=tokens[AUDITOR_ID])
                c = (body or {}).get('error', {}).get('code', '') if isinstance(body, dict) else ''
                check('CONTROL: auditor write %-22s -> %s %s (the override is an '
                      'EXCEPTION)' % (res, st, c),
                      st == 403 and c == 'FORBIDDEN', json.dumps(body)[:160])

    # ── 5b. A TIER A RECORD CANNOT BE DESTROYED (2026-09-15, item 97) ────────
    # The write gate above proves WHO may change these records. This proves what
    # can be done to them at all: an admin -- the role that COULD hard-delete
    # every sc_* resource until today -- is refused the destroying verb on a
    # Tier A record by the deployed function.
    #
    # ANY REFUSAL COUNTS AND 200 IS THE ONLY FAILURE. Two different guards can
    # answer: checkEnvelope rejects the verb because the registry no longer
    # grants it, and the handler's own SOFT_DELETE_ONLY branch answers if the
    # two lists ever disagree. Asserting one specific status would make this arm
    # fail when the OTHER correct guard fires first.
    print('\n5b. a Tier A record cannot be destroyed, only hidden')
    st, body = post(DATA, {'action': 'delete', 'resource': 'sc_claims',
                           'app_id': 'sairncode', 'payload': {'id': CLAIM_ROW}},
                    key=LICENSE, token=admin)
    c = (body or {}).get('error', {}).get('code', '') if isinstance(body, dict) else ''
    check('admin hard-delete on sc_claims is REFUSED -> %s %s' % (st, c),
          st != 200, 'the row was destroyed: ' + json.dumps(body)[:200])
    st, body = post(DATA, {'action': 'delete', 'resource': 'sc_coded_items',
                           'app_id': 'sairncode', 'payload': {'id': CODED_ROW}},
                    key=LICENSE, token=admin)
    check('CONTROL: admin hard-delete on sc_coded_items still works -> %s' % st,
          st == 200,
          'the refusal is blanket rather than Tier A only: ' + json.dumps(body)[:200])

    # ── 6. CLEAN UP, AND REPORT IT ───────────────────────────────────────────
    # A failure to clean up is a FINDING. A probe that leaves live credentials
    # active is worse than one that never ran.
    print('\n6. cleanup')
    # sc_coded_items is here because the section-4 control arm WRITES it and
    # succeeds. The other two rows are deleted unconditionally even when the
    # section that writes them was skipped -- a delete of an absent id answers
    # 200 -- so this one follows the same shape rather than adding a branch.
    #
    # THE VERB DIFFERS BY RESOURCE NOW, AND THE PROBE IS WHY IT HAD TO (item 97,
    # 2026-09-15). sc_claims and sc_compliance are Tier A and no longer accept a
    # destroying 'delete'; sc_coded_items is not Tier A and still does. THE VERB
    # IS DERIVED FROM THE REGISTRY, NOT TYPED HERE -- a fourth copy of the
    # seven-name list in a probe is precisely the drift api/_resources exists to
    # prevent, and this probe's own cleanup loop has already gone stale once by
    # naming resources by hand.
    #
    # AND SOFT-DELETED ROWS DO NOT VANISH, so the read-back that follows checks
    # the row is EXCLUDED FROM READS rather than gone. A probe asserting absence
    # from the table would now fail against a correct implementation.
    for res, row in (('sc_claims', CLAIM_ROW), ('sc_compliance', COMP_ROW),
                     ('sc_coded_items', CODED_ROW)):
        verb = 'soft_delete' if res in soft_only else 'delete'
        st, body = post(DATA, {'action': verb, 'resource': res,
                               'app_id': 'sairncode', 'payload': {'id': row}},
                        key=LICENSE, token=admin)
        check('%s %s from %s -> %s' % (verb, row, res, st), st == 200,
              json.dumps(body)[:200])
        st, body = post(DATA, {'action': 'read', 'resource': res,
                               'app_id': 'sairncode'}, key=LICENSE, token=admin)
        rows = (body or {}).get('data') or []
        left = [x for x in rows if isinstance(x, dict) and x.get('id') == row]
        check('...and %s no longer appears in a read of %s' % (row, res),
              st == 200 and not left, json.dumps(left)[:200])
    if CODER_PIN and AUDITOR_PIN:
        for emp in (CODER_ID, AUDITOR_ID):
            st, body = post(AUTH, {'action': 'set_active', 'employee_id': emp,
                                   'active': False,
                                   'reason': 'ZZ-GATE live probe subject, '
                                             'deactivated by the probe that made it'},
                            key=LICENSE, token=admin)
            check('deactivated %s -> %s' % (emp, st), st == 200,
                  json.dumps(body)[:200])

    print()
    for note in notes:
        print('NOTE: ' + note)
    if fails:
        print('\n%d ARM(S) FAILED -- the LIVE endpoint disagrees with the design:'
              % len(fails))
        for f in fails:
            print('  - ' + f)
        # ── CHECK THIS BEFORE DEBUGGING THE GATE (2026-09-14) ─────────────────
        # The FIRST real failing run of this probe was not a gate defect: the
        # auditor override for sc_compliance was committed locally and NOT PUSHED,
        # so the deployed function was the previous build and answered "Only admin
        # or biller". The probe was right and its verdict was right FOR THE
        # DEPLOYMENT -- but a reader could easily spend an hour on the handler
        # instead. Naming it here costs one paragraph and is exactly the kind of
        # note this repo keeps paying for the absence of.
        print('\n  FIRST, CHECK WHETHER THE DEPLOYMENT IS BEHIND THIS CLONE:')
        print('    git fetch origin && git log --oneline origin/main..HEAD')
        print('  A refusal naming a NARROWER role list than the code in front of')
        print('  you is the signature of an unpushed or not-yet-deployed change,')
        print('  not of a gate that disagrees with itself.')
        return 1
    if notes:
        print('\nPARTIALLY VERIFIED -- every arm that ran passed, and the skipped '
              'ones are named above.')
        return 2
    print('LIVE-VERIFIED -- the gate allowed and refused exactly as designed.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
