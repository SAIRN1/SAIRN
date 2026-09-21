"""Exercise SAIRNlegacy's LEG_RESOURCES session gate against the LIVE endpoint.

WHY THIS EXISTS. The gate shipped on 2026-09-21 and was verified two ways that
are both real and neither of which is live: api/sd-data-leg-session-gate.test.js
drives the REAL handler in-process (20 arms) and
tests/run_leg_session_gate_sabotage_probe.py proves those arms refuse six planted
defects. CLAUDE.md's push protocol is explicit that a clean `git push` is not
proof, and the thing being proved here is that a licence key ALONE no longer
reads a funeral home's death records on the deployment a customer actually hits.

Same shape and the same reasoning as tools/sc_tier_a_write_gate_live_probe.py.

── THE THREE STATES THIS REPORTS, AND THEY ARE NOT TWO ─────────────────────────
  VERIFIED     the deployed endpoint refused the licence-key-only caller on both
               verbs, with the gate's own NO_SESSION code -- exit 0
  UNVERIFIED   the licence row is absent (sql/sairnlegacy_license_seed.sql has
               never been run), or Vercel served a bot challenge, or the
               deployment has not caught up -- exit 2, and NOT reported as a
               gate failure
  FAILED       the live endpoint answered 200, or refused for some OTHER reason,
               which would mean the gate is not what is doing the refusing
               -- exit 1

Folding UNVERIFIED into either of the others is the defect this platform keeps
finding (PR 1.11): "could not tell" is a third state and is never "fine".

── WHY A NON-GATE REFUSAL IS A FAILURE AND NOT A PASS ──────────────────────────
A 401 INVALID_LICENSE also refuses the request, and a probe that asserted only
"not 200" would go green against a deployment where the gate does not exist and
the demo licence merely expired. The error CODE is asserted, so the refusal has
to be the one the gate emits.

── AND THE CONTROL ARM, WHICH IS THE HALF THAT MAKES IT A SPLIT ────────────────
A resource OUTSIDE LEG_RESOURCES is read with the same licence and the same
absent session. If that is refused too, the endpoint is simply down or the
licence is dead, and the six refusals above are a lockout rather than a gate.
That arm answering differently is what makes this a measurement.

NO CREDENTIALS ARE WRITTEN AND NOTHING IS CREATED. Every arm is a REFUSED
request plus one read of an ungated resource, so there is nothing to clean up.

The licence key comes from the environment, never this file:

    LEG_LICENSE   the SAIRNlegacy licence key (sql/sairnlegacy_license_seed.sql
                  seeds LEG-PINNACLE-2026 as the demo row)

Run:  LEG_LICENSE=... python tools/leg_session_gate_live_probe.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sairn_http                                                  # noqa: E402

URL = 'https://sairn.vercel.app/api/sd-data'
PAGE = 'https://sairn.vercel.app/sairnlegacy'

# The two that carry the whole argument: the death record and the document that
# says which human remains were in whose hands, and when.
GATED = ('leg_deathrecords', 'leg_custodylog')
# Outside LEG_RESOURCES but INSIDE what this licence may name. The endpoint
# whitelists resources per app and answers 400 for anything else, so a
# cross-app control (sd_customers was the first try) is refused for the wrong
# reason and proves nothing about the gate. It also has to be a resource that
# is genuinely UNGATED -- `profile`, `memory`, `employees`, `slabs` and
# `employee_profile` all answer 403 FORBIDDEN without a session, which would
# make the control indistinguishable from the thing under test.
# `shared_knowledge` is reached by the same handler, with the same licence, and
# answers 200 on a licence alone by design.
UNGATED = 'shared_knowledge'


def err_code(body):
    if isinstance(body, dict):
        e = body.get('error')
        if isinstance(e, dict):
            return e.get('code') or ''
        # A string error is a shape this endpoint also emits; returning '' for
        # it would read as "no code" rather than "a different shape".
        if isinstance(e, str):
            return e
    return ''


def call(resource, action, key):
    payload = {'action': action, 'resource': resource}
    if action == 'write':
        # A write needs a row. ZZ-LIVE-PROBE is never stored -- the whole point
        # is that the request is refused before the query -- but a payload the
        # handler would reject for its SHAPE would refuse for the wrong reason.
        payload['data'] = {'id': 'ZZ-LIVE-PROBE', 'note': 'refused before write'}
    return sairn_http.fetch_json(URL, payload=payload, key=key)


def main():
    key = os.environ.get('LEG_LICENSE', '').strip()
    if not key:
        print('UNVERIFIED -- LEG_LICENSE is not set. The gate sits BELOW the')
        print('licence check, so it cannot be reached without a real licence.')
        print('  LEG_LICENSE=... python tools/leg_session_gate_live_probe.py')
        return 2

    print('SAIRNlegacy LEG_RESOURCES session gate -- LIVE')
    print('  endpoint %s' % URL)
    print('  licence  %s...%s (%d chars)' % (key[:4], key[-4:], len(key)))
    print('  NO X-SD-Auth header is sent on any arm below.\n')

    failures, unverified = [], []

    # ── the control arm runs FIRST, because if it fails every verdict below is
    # about the deployment rather than about the gate ──────────────────────────
    try:
        st, body = call(UNGATED, 'read', key)
    except sairn_http.Challenged as c:
        print('  UNVERIFIED  Vercel served a bot challenge (%s)' % c)
        return 2
    code = err_code(body)
    if st == 200:
        print('  ok          CONTROL %s read -> 200, so the licence is live and'
              ' the endpoint answers' % UNGATED)
    elif code in ('INVALID_LICENSE', 'LICENSE_INACTIVE'):
        print('  UNVERIFIED  CONTROL %s read -> %s %s. The licence row is absent'
              ' or inactive,' % (UNGATED, st, code))
        print('              so nothing below would reach the gate. Run'
              ' sql/sairnlegacy_license_seed.sql.')
        return 2
    else:
        print('  UNVERIFIED  CONTROL %s read -> %s %s. The ungated branch is not'
              ' answering,' % (UNGATED, st, code))
        print('              so a refusal on the gated ones would not be'
              ' attributable to the gate.')
        return 2

    # ── the gate itself, both verbs, licence key and nothing else ─────────────
    for resource in GATED:
        for action in ('read', 'write'):
            label = '%s %s' % (resource, action)
            try:
                st, body = call(resource, action, key)
            except sairn_http.Challenged as c:
                unverified.append('%s -- challenged (%s)' % (label, c))
                print('  UNVERIFIED  %-28s bot challenge' % label)
                continue
            code = err_code(body)
            if st == 401 and code == 'NO_SESSION':
                print('  ok          %-28s -> 401 NO_SESSION' % label)
            elif st == 200:
                failures.append('%s -> 200 -- THE GATE IS NOT LIVE. %s'
                                % (label, json.dumps(body)[:200]))
                print('  FAILED      %-28s -> 200, the licence key alone was'
                      ' enough' % label)
            else:
                failures.append('%s -> %s %s -- refused, but NOT by the gate'
                                % (label, st, code or '(no code)'))
                print('  FAILED      %-28s -> %s %s, refused for a reason that'
                      ' is not the gate' % (label, st, code or '(no code)'))

    # ── and the client half, which is what makes the gate survivable ──────────
    try:
        st, raw = sairn_http.fetch(PAGE, no_cache=True)
        page = raw.decode('utf-8', 'replace')
        if "if(legSession&&legSession.token)h['X-SD-Auth']=legSession.token;" in page:
            print("\n  ok          the deployed page attaches X-SD-Auth"
                  " unconditionally")
        elif "X-SD-Auth" in page:
            failures.append('the deployed page still guards X-SD-Auth behind a '
                            'caller flag -- the gate is an outage on the 56 '
                            'call sites that pass none')
            print('\n  FAILED      the deployed page has X-SD-Auth but not'
                  ' unconditionally')
        else:
            unverified.append('the deployed page does not contain X-SD-Auth at '
                              'all -- the deployment has probably not caught up')
            print('\n  UNVERIFIED  the deployed page has no X-SD-Auth; the'
                  ' deployment may not have caught up')
    except sairn_http.Challenged as c:
        unverified.append('the page was challenged (%s)' % c)
        print('\n  UNVERIFIED  the page was challenged (%s)' % c)

    print('')
    if failures:
        print('FAILED -- %d arm(s):' % len(failures))
        for f in failures:
            print('  ! %s' % f)
        return 1
    if unverified:
        print('UNVERIFIED -- %d arm(s) could not be driven, and that is NOT a'
              ' pass:' % len(unverified))
        for u in unverified:
            print('  ? %s' % u)
        return 2
    print('VERIFIED -- the deployed endpoint refuses a licence-key-only caller'
          ' on both verbs')
    print('of both resources with the gate\'s own NO_SESSION code, while the'
          ' ungated control')
    print('arm still answers 200. The gate is live.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
