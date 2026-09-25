"""Exercise SAIRNscape's two Tier A session gates against the LIVE endpoint.

WHY THIS EXISTS. The gate shipped on 2026-09-25 and was verified two ways that
are both real and neither of which is live: api/sd-data-scp-session-gate.test.js
drives the REAL handler in-process (18 arms) and three mutations of the gate
take it to 9/18, 11/18 and 16/18. CLAUDE.md's push protocol is explicit that a
clean `git push` is not proof, and the thing being proved here is that a licence
key ALONE no longer reads or writes a landscaping company's quotes and invoices
on the deployment a customer actually hits.

Same shape and the same reasoning as tools/leg_session_gate_live_probe.py,
which this is adapted from. THE ADAPTATION IS NOT A COPY AND THE DIFFERENCE
MATTERS: SAIRNlegacy's gate is bespoke and answers 401 NO_SESSION; SAIRNscape's
is the SHARED SD_SESSION_GATED table and answers 403 FORBIDDEN. A probe that
kept the borrowed code would assert the wrong code and report a working gate as
FAILED -- which is bug class 22, borrowed safety reasoning never re-verified
against the new context, and it is cheaper to name here than to debug live.

── THE THREE STATES THIS REPORTS, AND THEY ARE NOT TWO ─────────────────────────
  VERIFIED     the deployed endpoint refused the licence-key-only caller on both
               verbs of both resources, with the gate's own FORBIDDEN code
               -- exit 0
  UNVERIFIED   the licence row is absent (sql/demo_license_keys_seed.sql has
               never been run for SCP-DEMO-2026), or Vercel served a bot
               challenge, or the deployment has not caught up -- exit 2, and NOT
               reported as a gate failure
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
A SAIRNscape resource OUTSIDE the gate is read with the same licence and the
same absent session. If that is refused too, the endpoint is down or the licence
is dead, and the four refusals above are a lockout rather than a gate. That arm
answering differently is what makes this a measurement rather than an assertion.

`scp_vendors` is the control deliberately: it is one of the ten Tier B
SAIRNscape resources that stay licence-only by the Tier A stopping rule, it is
served by the same handler under the same licence, and it is the same resource
api/sd-data-scp-session-gate.test.js drives as its in-process disclosure arm --
so the live control and the unit control cannot drift apart.

NO CREDENTIALS ARE WRITTEN AND NOTHING IS CREATED. Every arm is a REFUSED
request plus one read of an ungated resource, so there is nothing to clean up.

The licence key comes from the environment, never this file:

    SCP_LICENSE   the SAIRNscape licence key (sql/demo_license_keys_seed.sql
                  seeds SCP-DEMO-2026 as the demo row)

Run:  SCP_LICENSE=... python tools/scp_session_gate_live_probe.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sairn_http                                                  # noqa: E402

URL = 'https://sairn.vercel.app/api/sd-data'
PAGE = 'https://sairn.vercel.app/sairnscape'

# The two Tier A rows: the money, and the priced quote it descends from.
#
# `invoices` IS SPELLED BARE ON PURPOSE. SAIRNscape claimed that name before the
# scp_ convention existed -- the storage table is scp_invoices and the RESOURCE
# the dispatch tests for is `invoices`. Probing 'scp_invoices' here would get a
# 400 for an unknown resource, which is a refusal, and a probe that accepted any
# refusal would report the gate live while testing a name that does not exist.
GATED = ('invoices', 'scp_quotes')

# Outside the gate and INSIDE what this licence may name. It has to be a
# SAIRNscape resource: the endpoint whitelists resources per app, so a cross-app
# control is refused for the wrong reason and proves nothing about the gate.
UNGATED = 'scp_vendors'

# What the SHARED gate emits. Asserted rather than "not 200" -- see the header.
GATE_STATUS = 403
GATE_CODE = 'FORBIDDEN'


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
        # A write needs a row that would pass the branch's OWN shape checks --
        # `invoices` refuses a payload with no id or customer_id with 400, and a
        # 400 here would be a refusal for the wrong reason. ZZ-LIVE-PROBE is
        # never stored: the whole point is that the request is refused by the
        # gate, which runs long before the query.
        payload['payload'] = {'id': 'ZZ-LIVE-PROBE', 'customer_id': 'ZZ-LIVE-PROBE'}
    return sairn_http.fetch_json(URL, payload=payload, key=key)


def main():
    key = os.environ.get('SCP_LICENSE', '').strip()
    if not key:
        print('UNVERIFIED -- SCP_LICENSE is not set. The gate sits BELOW the')
        print('licence check, so it cannot be reached without a real licence.')
        print('  SCP_LICENSE=... python tools/scp_session_gate_live_probe.py')
        return 2

    print('SAIRNscape Tier A session gate -- LIVE')
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
              ' sql/demo_license_keys_seed.sql.')
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
            if st == GATE_STATUS and code == GATE_CODE:
                print('  ok          %-28s -> %s %s' % (label, st, code))
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
    # A gate on the server with no header on the client is an outage, not a
    # control. Read off the DEPLOYED page, because the repo's copy says nothing
    # about what Vercel is serving.
    try:
        st, raw = sairn_http.fetch(PAGE, no_cache=True)
        page = raw.decode('utf-8', 'replace')
        if "sessionStorage.getItem(SCP_SESSION_KEY); if (tok) headers['X-SD-Auth'] = tok;" in page:
            print("\n  ok          the deployed page attaches X-SD-Auth on the"
                  " stored token alone")
        elif 'X-SD-Auth' in page:
            failures.append('the deployed page has X-SD-Auth but not in the '
                            'shape scpData ships -- re-read it before trusting '
                            'the gate, because a per-call flag here is an '
                            'outage on every call site that passes none')
            print('\n  FAILED      the deployed page has X-SD-Auth in an'
                  ' unexpected shape')
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
            print('  ' + f)
        return 1
    if unverified:
        print('UNVERIFIED -- %d arm(s) could not be driven:' % len(unverified))
        for u in unverified:
            print('  ' + u)
        print('COULD NOT TELL IS NOT A PASS.')
        return 2
    print('VERIFIED -- the deployed endpoint refuses both Tier A SAIRNscape')
    print('resources on read AND write to a caller holding only a licence key,')
    print('with the gate\'s own %s %s, while %s still answers 200.'
          % (GATE_STATUS, GATE_CODE, UNGATED))
    return 0


if __name__ == '__main__':
    sys.exit(main())
