"""Does `rt_routes` ANSWER A REAL REQUEST on the deployment a customer hits?

Run:  SD_LICENSE=SD-AUDIT-2026 SD_OWNER_PIN=... python tests/rt_routes_live_probe.py

── WHY THIS EXISTS, AND IT IS THE ONE THING b27 COULD NOT SAY ──────────────────
b27 landed the `rt_routes` / `rt_stops` handler branch in api/sd-data.js, found
the feature STILL DEAD behind a fourth gate (`isVisibleTo`), fixed that, and
proved all of it with 63 in-process arms. Its own handoff §6.8 then said the
honest thing: **"Nothing establishes that rt_routes answers a real request
against a real Supabase."** In-process arms drive the real handler with a real
dispatcher and a stubbed `fetch`; they cannot tell a landed branch from a
deployed one, and CLAUDE.md's push protocol is explicit that a clean `git push`
is not proof.

── THE THREE STATES, AND THEY ARE NOT TWO ──────────────────────────────────────
  VERIFIED     every arm answered as the deployed branch's OWN code must -- exit 0
  UNVERIFIED   the licence row is absent, the PIN is not live, Vercel served a
               bot challenge, or the `rt_routes` table was never created
               (`provisioned: false`) -- exit 2, and NOT reported as a failure
  FAILED       an arm answered something the branch cannot produce -- exit 1

Folding UNVERIFIED into either of the others is the defect this platform keeps
re-finding (PR 1.11): "could not tell" is a third state and is never "fine".

── WHY EACH ARM ASSERTS A MESSAGE THE BRANCH ALONE CAN EMIT ────────────────────
"not 500" would pass against a deployment where this branch does not exist: the
dispatcher's fallthrough also answers 400. So A3 and A5 assert strings written
INSIDE the branch -- `route_date is required as YYYY-MM-DD` comes from
`RT.validateRouteKey`, and `action must be read, upsert, reorder or optimize for
rt_routes` is the branch's terminal line. Only the deployed branch can say
either. That is the difference between proving reachability and proving a refusal
happened for some unrelated reason.

── AND A4 IS THE ARM THAT ACTUALLY COMPUTES SOMETHING ──────────────────────────
A read of an absent row proves the dispatcher, the session gate and the table.
It does not prove the routing PRIMITIVE runs. A4 posts `optimize` with ONE stop,
which `api/_lib/routes.js:373` answers `basis: 'unavailable', reason:
'too-few-stops'` -- a real computed answer out of the deployed module.

**ONE stop is chosen on purpose and not for brevity.** `optimize` WRITES an
`rt_routes` row whenever `basis !== 'unavailable'`, and the branch has **no
delete verb**, so a write here is residue only Michael can remove with SQL.
`stops.length < 2` short-circuits before `driveMatrix` is ever called, so the
no-write outcome does not depend on whether a maps key happens to be set in the
deployment's environment. A 2-stop probe with coordinates would be a better
exercise of the optimiser and would leave a row behind; this is the trade, made
deliberately.

NOTHING IS WRITTEN AND THERE IS NOTHING TO CLEAN UP. Every arm is a read, a
refusal, or a computation that short-circuits before its write. A4b re-reads the
key afterwards and FAILS if a row appeared, so "nothing was written" is asserted
rather than intended.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, 'tools'))
import sairn_http                                                    # noqa: E402
from audit_licence import require_audit_licence                      # noqa: E402

# ── THE CLASS, AND THE AUDITOR WAS RIGHT TO REFUSE THE FIRST SPELLING ──────
# This said `LIVE_PROBE_CLASS = 'read-only'`, which is honest prose and is NOT
# one of the three values tools/live_probe_residue_audit.py accepts, so the
# pre-commit gate refused the commit: *"sends a WRITE action (write) to the live
# platform and declares no LIVE_PROBE_CLASS."*
#
# IT IS RIGHT TWICE OVER. The auditor matches `'action': 'write'` in source, and
# arm A5 posts exactly that -- deliberately, because `write` is the only
# globally-legal verb that is not an rt_routes verb and therefore the only input
# that reaches the branch's terminal refusal. A source scan cannot tell a write
# that is SENT from a write that is ASSERTED TO BE REFUSED, and it should not
# guess: "this request is refused" is a fact the author knows and nothing else
# reliably does. VERIFICATION is the class, and the residue line below says in
# full why the write leaves nothing.
LIVE_PROBE_CLASS = 'VERIFICATION'
LIVE_PROBE_RESIDUE = 'none -- the one `write` action (arm A5) is ASSERTED to be refused 400 by the branch, not sent to succeed; every other arm is a read, a licence-only refusal, or an optimize call that short-circuits at routes.js:373 before its write. A4b re-reads the probe key afterwards and FAILS if a row appeared, so the absence is measured rather than argued.'

DATA = 'https://sairn.vercel.app/api/sd-data'
AUTH = 'https://sairn.vercel.app/api/sd-auth'
EMPLOYEE = 'sairn-demo-owner'

# A key no real route can collide with, and a date far outside any shop's
# working window. Used only by reads -- nothing is inserted under it.
PROBE_ASSIGNEE = 'rt-live-probe-b28-no-such-employee'
PROBE_DATE = '2031-01-02'

CRITERIA_VERSION = '2026-10-20.1'


def post(url, key, body, token=None):
    h = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + key}
    if token:
        h['X-SD-Auth'] = token
    try:
        r = sairn_http.fetch(url, method='POST',
                             data=json.dumps(body).encode(), headers=h)
        status, raw = r.status, r.body
    except sairn_http.Challenged as e:
        return None, {'_challenged': str(e)}
    except Exception as e:                                           # noqa: BLE001
        status = getattr(e, 'code', None)
        try:
            raw = e.read()
        except Exception:                                            # noqa: BLE001
            return status, {'_transport': '%s: %s' % (type(e).__name__, e)}
    if isinstance(raw, bytes):
        raw = raw.decode('utf-8', 'replace')
    try:
        return status, json.loads(raw)
    except Exception:                                                # noqa: BLE001
        return status, {'_raw': raw[:300]}


def code_of(body):
    if isinstance(body, dict):
        e = body.get('error')
        if isinstance(e, dict):
            return str(e.get('code') or '')
    return ''


def message_of(body):
    if isinstance(body, dict):
        e = body.get('error')
        if isinstance(e, dict):
            return str(e.get('message') or '')
        if isinstance(e, str):
            return e
    return ''


def unreadable(body):
    """Transport trouble, not an answer. Its own state, never a failure."""
    if not isinstance(body, dict):
        return 'reply was not an object: %s' % str(body)[:80]
    if '_challenged' in body:
        return 'Vercel bot challenge: %s' % body['_challenged'][:80]
    if '_transport' in body:
        return body['_transport'][:120]
    if '_raw' in body:
        return 'reply was not JSON: %s' % body['_raw'][:120]
    return None


def key_payload(**over):
    p = {'app_id': 'stonedesk', 'assignee_id': PROBE_ASSIGNEE,
         'route_date': PROBE_DATE}
    p.update(over)
    return p


def main():
    key = require_audit_licence(
        os.environ.get('SD_LICENSE', '').strip(),
        tool=__file__,
        writes='nothing -- read-only, see LIVE_PROBE_RESIDUE')
    pin = os.environ.get('SD_OWNER_PIN', '').strip()
    if not pin:
        sys.stderr.write(
            'UNVERIFIED: SD_OWNER_PIN is not set, so no employee session could '
            'be obtained and NOT ONE ARM RAN. rt_routes requires a session on '
            'every verb by design, so there is no reduced read-only mode to '
            'fall back to.\n')
        return 2

    st, b = post(AUTH, key, {'action': 'login', 'employee_id': EMPLOYEE,
                             'pin': pin})
    bad = unreadable(b)
    if bad:
        sys.stderr.write('UNVERIFIED: sign-in at /api/sd-auth was '
                         'UNREADABLE -- %s\n' % bad)
        return 2
    token = b.get('token') if isinstance(b, dict) else None
    if not token:
        sys.stderr.write(
            'UNVERIFIED: sign-in at /api/sd-auth answered %s %s and returned no '
            'token, so NOT ONE ARM RAN. The licence row or the credential for '
            '%s is not live -- run sql/stonedesk_audit_license_seed.sql and the '
            'bootstrap it documents.\n'
            % (st, json.dumps(b)[:160], EMPLOYEE))
        return 2

    fails, lines = [], []

    def record(name, ok, detail):
        lines.append('%-4s %s -- %s' % ('PASS' if ok else 'FAIL', name, detail))
        if not ok:
            fails.append(name)

    # ── A1. A REAL AUTHENTICATED READ ───────────────────────────────────────
    st, b = post(DATA, key, {'action': 'read', 'resource': 'rt_routes',
                             'app_id': 'stonedesk',
                             'payload': key_payload()}, token)
    bad = unreadable(b)
    if bad:
        sys.stderr.write('UNVERIFIED: A1 was UNREADABLE -- %s\n' % bad)
        return 2
    if st == 200 and b.get('ok') and b.get('provisioned') is False:
        sys.stderr.write(
            'UNVERIFIED: the deployed branch answered A1 with provisioned=false, '
            'which is its own way of saying the rt_routes table does not exist '
            'on this deployment. sql/rt_routes_schema.sql has not been run. '
            'THE BRANCH IS REACHABLE -- that much is proved -- and the feature '
            'cannot be exercised, so the remaining arms were NOT run rather '
            'than reported green against a table that is absent.\n')
        return 2
    a1_ok = (st == 200 and b.get('ok') is True
             and b.get('provisioned') is True and b.get('data') is None)
    record('A1 authenticated read of an absent route -> 200 ok '
           'provisioned=true data=null', a1_ok,
           '%s %s' % (st, json.dumps(b)[:160]))

    # ── A2. THE SESSION GATE, WITH NO TOKEN ─────────────────────────────────
    st, b = post(DATA, key, {'action': 'read', 'resource': 'rt_routes',
                             'app_id': 'stonedesk',
                             'payload': key_payload()})
    bad = unreadable(b)
    if bad:
        record('A2 licence alone is refused', False, 'UNREADABLE -- %s' % bad)
    else:
        record('A2 licence alone -> 403 FORBIDDEN "A valid employee session '
               'is required"',
               st == 403 and code_of(b) == 'FORBIDDEN'
               and 'employee session' in message_of(b),
               '%s %s' % (st, json.dumps(b)[:160]))

    # ── A3. THE BRANCH'S OWN VALIDATOR ──────────────────────────────────────
    st, b = post(DATA, key, {'action': 'read', 'resource': 'rt_routes',
                             'app_id': 'stonedesk',
                             'payload': key_payload(route_date='02/01/2031')},
                 token)
    bad = unreadable(b)
    if bad:
        record('A3 RT.validateRouteKey runs in the deployment', False,
               'UNREADABLE -- %s' % bad)
    else:
        record('A3 a non-ISO route_date -> 400 with validateRouteKey\'s OWN '
               'message', st == 400
               and 'route_date is required as YYYY-MM-DD' in message_of(b),
               '%s %s' % (st, json.dumps(b)[:160]))

    # ── A4. THE ROUTING PRIMITIVE COMPUTES ──────────────────────────────────
    st, b = post(DATA, key, {
        'action': 'optimize', 'resource': 'rt_routes', 'app_id': 'stonedesk',
        'payload': key_payload(stops=[{'address': '1 Probe Way'}])}, token)
    bad = unreadable(b)
    if bad:
        record('A4 the deployed routing module computes', False,
               'UNREADABLE -- %s' % bad)
    else:
        record('A4 optimize with one stop -> 200 basis=unavailable '
               'reason=too-few-stops',
               st == 200 and b.get('ok') is True
               and b.get('basis') == 'unavailable'
               and b.get('reason') == 'too-few-stops',
               '%s %s' % (st, json.dumps(b)[:160]))

    # ── A4b. AND IT WROTE NOTHING ───────────────────────────────────────────
    st, b = post(DATA, key, {'action': 'read', 'resource': 'rt_routes',
                             'app_id': 'stonedesk',
                             'payload': key_payload()}, token)
    bad = unreadable(b)
    if bad:
        record('A4b nothing was written', False, 'UNREADABLE -- %s' % bad)
    else:
        record('A4b the probe key is STILL absent after A4 -- asserted, not '
               'assumed', st == 200 and b.get('data') is None,
               '%s %s' % (st, json.dumps(b)[:160]))

    # ── A5. THE BRANCH'S TERMINAL LINE ──────────────────────────────────────
    # `write` AND NOT A MADE-UP VERB, and the first spelling of this arm got it
    # wrong in a way worth keeping written down. `frobnicate` never reaches the
    # branch: api/sd-data.js whitelists the ACTION at the top of the handler and
    # answers "action must be 'read' or 'write' or 'upsert' or 'reorder' or
    # 'optimize'" long before any `resource ===` test runs. So the arm asserting
    # the branch's terminal line was reading the DISPATCHER's refusal and would
    # have gone red against a perfectly deployed branch. `write` is globally
    # legal and is not one of the four verbs rt_routes implements, so it is the
    # only input that falls through the branch to its last line.
    st, b = post(DATA, key, {'action': 'write', 'resource': 'rt_routes',
                             'app_id': 'stonedesk',
                             'payload': key_payload()}, token)
    bad = unreadable(b)
    if bad:
        record('A5 the branch owns the fall-through refusal', False,
               'UNREADABLE -- %s' % bad)
    else:
        record('A5 action=write (globally legal, not an rt_routes verb) -> 400 '
               'with the BRANCH\'s OWN terminal message', st == 400
               and 'action must be read, upsert, reorder or optimize for '
                   'rt_routes' in message_of(b),
               '%s %s' % (st, json.dumps(b)[:160]))

    print('rt_routes LIVE PROBE -- %s' % DATA)
    print('  licence %s, employee %s, criteria %s'
          % (key, EMPLOYEE, CRITERIA_VERSION))
    for ln in lines:
        print('  ' + ln)
    if fails:
        print('\nFAILED -- %d of %d arm(s): %s'
              % (len(fails), len(lines), ', '.join(fails)))
        return 1
    print('\nVERIFIED -- %d arms. rt_routes answers a real authenticated '
          'request end to end on the live deployment, refuses a licence-only '
          'one, and its own validator and terminal line are the code answering.'
          % len(lines))
    return 0


if __name__ == '__main__':
    sys.exit(main())
