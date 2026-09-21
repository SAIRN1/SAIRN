"""Exercise SAIRNlaw's billing_code normalisation against the LIVE endpoint.

WHY THIS EXISTS. The trim fix (8ed8b14d, 2026-09-21) was verified two ways that
are both real and neither of which is live: api/_lib/law-timeentry.test.js
drives the real handler in-process (26 arms) and
tests/run_law_timeentry_trim_sabotage_probe.py proves those arms refuse seven
planted defects. CLAUDE.md's push protocol is explicit that a clean `git push`
is not proof, and the session that shipped it recorded the live half as
UNVERIFIED because the gate sits below a SAIRNlaw employee session it did not
have. docs/2026-09-03-demo-credentials.md has one; this closes that gap.

── WHAT IT PROVES, AND THE SHARP ARM IS THE SECOND ────────────────────────────
  1. a padded code round-trips TRIMMED -- '  L100  ' is stored as 'L100'
  2. a code that is OVER the length bound only because of padding is stored
     WITHIN it. 30 spaces + 'L100' is 34 characters; MAX_BILLING_CODE_CHARS is
     32 and is checked against the TRIMMED value, so before the fix the gate
     judged 4 and wrote 34 -- a value it would have refused had it been asked
     about the thing being written. This is the arm that distinguishes the fix
     from a cosmetic trim.
  3. the read-back is the DATABASE's copy, not the write's echo. The echo is
     asserted too, but a probe that only read the response would pass against
     a server that normalised its reply and stored the raw string.

── THE THREE STATES, AND THEY ARE NOT TWO ─────────────────────────────────────
  VERIFIED     the deployed endpoint stored the trimmed value on both arms
  UNVERIFIED   credentials absent, the licence or PIN is not live, the tables
               are not provisioned, or Vercel served a bot challenge -- exit 2,
               and NOT reported as a failure of the fix
  FAILED       the stored value is not the judged value -- exit 1

── WHAT IT LEAVES BEHIND, STATED BECAUSE IT CANNOT BE CLEANED UP ──────────────
SAIRNlaw declares NO delete verb: api/sd-data.js serves LAW_RESOURCES for
'read' and 'write' only. So this probe cannot remove what it writes, and
pretending otherwise would be worse than saying so.

It writes exactly ONE row -- timeentry_id `ZZ-TRIM-PROBE` in law_timeentries,
under the DEMO licence only -- and reuses that one id for every arm, so the
count does not grow with the number of runs. The final upsert leaves the row
carrying a description that says what it is and that it is safe to delete. It
is a no-charge entry (`billable: false`), which is both honest and the reason
it needs no rate or hours: those gates apply to billable work.

CREDENTIALS COME FROM THE ENVIRONMENT, NEVER THIS FILE:

    LAW_LICENSE   the licence key      (demo row: LAW-PINNACLE-2026)
    LAW_EMP       an employee_id       (demo row: sairn-demo-owner)
    LAW_PIN       that employee's PIN

Run:  LAW_LICENSE=... LAW_EMP=... LAW_PIN=... python tools/law_billing_code_trim_live_probe.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sairn_http                                                  # noqa: E402

DATA = 'https://sairn.vercel.app/api/sd-data'
AUTH = 'https://sairn.vercel.app/api/law-auth'
RESOURCE = 'law_timeentries'
ROW_ID = 'ZZ-TRIM-PROBE'

# Read out of the module rather than retyped, so a change to the bound cannot
# leave this probe asserting against a number the server no longer uses.
try:
    sys.path.insert(0, os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'api', '_lib'))
    MAXLEN = None
    import re as _re
    _lib = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        'api', '_lib', 'law-timeentry.js')
    _m = _re.search(r'MAX_BILLING_CODE_CHARS\s*=\s*(\d+)',
                    open(_lib, encoding='utf-8').read())
    MAXLEN = int(_m.group(1)) if _m else None
except (OSError, ValueError):
    MAXLEN = None


def call(payload, key, token=None):
    headers = {'X-SD-Auth': token} if token else None
    return sairn_http.fetch_json(DATA, payload=payload, key=key, headers=headers)


def read_row(key, token):
    st, body = call({'action': 'read', 'resource': RESOURCE}, key, token)
    if st != 200 or not isinstance(body, dict) or not body.get('ok'):
        return None, (st, body)
    for row in (body.get('data') or []):
        if isinstance(row, dict) and row.get('id') == ROW_ID:
            return row, None
    return None, (st, 'the row was written and did not come back')


def main():
    key = os.environ.get('LAW_LICENSE', '').strip()
    emp = os.environ.get('LAW_EMP', '').strip()
    pin = os.environ.get('LAW_PIN', '').strip()
    if not (key and emp and pin):
        print('UNVERIFIED -- LAW_LICENSE, LAW_EMP and LAW_PIN must all be set.')
        print('The normalisation sits BELOW SAIRNlaw\'s session gate, so it')
        print('cannot be reached without a real licence AND a real session.')
        print('  docs/2026-09-03-demo-credentials.md carries the demo row.')
        return 2
    if MAXLEN is None:
        print('UNVERIFIED -- MAX_BILLING_CODE_CHARS could not be read out of')
        print('api/_lib/law-timeentry.js, so the length arm has no bound to')
        print('assert against and is NOT being skipped quietly.')
        return 2

    print('SAIRNlaw billing_code normalisation -- LIVE')
    print('  endpoint %s' % DATA)
    print('  licence  %s...%s   employee %s' % (key[:4], key[-4:], emp))
    print('  MAX_BILLING_CODE_CHARS read from the module: %d\n' % MAXLEN)

    try:
        st, body = sairn_http.fetch_json(
            AUTH, payload={'action': 'login', 'employee_id': emp, 'pin': pin},
            key=key)
    except sairn_http.Challenged as c:
        print('  UNVERIFIED  the login was challenged (%s)' % c)
        return 2
    token = body.get('token') if isinstance(body, dict) else None
    if st != 200 or not token:
        print('  UNVERIFIED  login -> %s %s' % (st, json.dumps(body)[:180]))
        print('              The PIN or licence is not live. Nothing below could')
        print('              reach the normalisation, so this is not a failure')
        print('              of the fix.')
        return 2
    print('  ok          signed in as %s' % emp)

    failures, unverified = [], []

    # A no-charge entry: billable false, so the rate and hours gates -- which
    # are a different fix -- do not stand between this probe and its subject.
    def entry(code, note):
        return {'id': ROW_ID, 'matter_id': 'ZZ-PROBE', 'attorney': emp,
                'date': '2026-09-21', 'hours': 0, 'rate': 0, 'billable': False,
                'invoiced': False, 'billing_code': code, 'description': note}

    padded_long = ' ' * (MAXLEN - 2) + 'L100'
    arms = (
        ('a padded code round-trips TRIMMED', '  L100  ', 'L100'),
        ('a code over the bound ONLY because of padding (%d chars -> %d)'
         % (len(padded_long), 4), padded_long, 'L100'),
    )
    for label, sent, want in arms:
        try:
            st, body = call({'action': 'write', 'resource': RESOURCE,
                             'payload': entry(sent, 'ZZ live trim probe')},
                            key, token)
        except sairn_http.Challenged as c:
            unverified.append('%s -- challenged (%s)' % (label, c))
            print('  UNVERIFIED  %s' % label)
            continue
        if st == 503:
            print('  UNVERIFIED  %s -> 503 NOT_PROVISIONED; the SAIRNlaw extended'
                  ' tables are not set up' % label)
            return 2
        if st != 200:
            failures.append('%s -> %s %s' % (label, st, json.dumps(body)[:160]))
            print('  FAILED      %s -> %s, the write was refused' % (label, st))
            continue
        echoed = ((body.get('data') or {}).get('billing_code')
                  if isinstance(body, dict) else None)
        row, err = read_row(key, token)
        if row is None:
            unverified.append('%s -- could not read the row back: %s' % (label, err))
            print('  UNVERIFIED  %s -- the row did not read back' % label)
            continue
        stored = row.get('billing_code')
        if stored == want and echoed == want:
            print('  ok          %-58s sent %r, stored %r'
                  % (label, sent, stored))
        else:
            failures.append('%s: sent %r, STORED %r, echoed %r, wanted %r'
                            % (label, sent, stored, echoed, want))
            print('  FAILED      %-58s sent %r, STORED %r, echoed %r'
                  % (label, sent, stored, echoed))
        if isinstance(stored, str) and len(stored) > MAXLEN:
            failures.append('%s: the STORED value is %d characters, over the %d '
                            'the gate enforces' % (label, len(stored), MAXLEN))

    # The control: a code with nothing to trim must come back byte-identical,
    # so the two arms above are a NORMALISATION rather than a value the server
    # rewrites on every write.
    try:
        st, _b = call({'action': 'write', 'resource': RESOURCE,
                       'payload': entry('A101', 'ZZ live trim probe -- control')},
                      key, token)
        row, err = read_row(key, token)
        if row is None:
            unverified.append('control -- could not read the row back: %s' % err)
            print('  UNVERIFIED  CONTROL -- the row did not read back')
        elif row.get('billing_code') == 'A101':
            print('  ok          CONTROL a code with nothing to trim is unchanged')
        else:
            failures.append('CONTROL: sent %r, stored %r' % ('A101', row.get('billing_code')))
            print('  FAILED      CONTROL sent \'A101\', stored %r' % row.get('billing_code'))
    except sairn_http.Challenged as c:
        unverified.append('control -- challenged (%s)' % c)

    # Leave the one row it cannot delete describing itself.
    call({'action': 'write', 'resource': RESOURCE,
          'payload': entry('A101',
                           'ZZ live trim probe row -- written by '
                           'tools/law_billing_code_trim_live_probe.py to verify '
                           'billing_code normalisation on the deployed endpoint. '
                           'SAIRNlaw has no delete verb so it cannot remove '
                           'itself. Safe to delete.')}, key, token)

    print('')
    if failures:
        print('FAILED -- %d arm(s):' % len(failures))
        for f in failures:
            print('  ! %s' % f)
        return 1
    if unverified:
        print('UNVERIFIED -- %d arm(s) could not be driven, and that is NOT a pass:'
              % len(unverified))
        for u in unverified:
            print('  ? %s' % u)
        return 2
    print('VERIFIED -- the deployed endpoint stores the billing code it JUDGED,')
    print('including where padding alone put the raw value over the length bound,')
    print('and a code with nothing to trim is written through unchanged.')
    print('')
    print('ONE ROW LEFT BEHIND, by design and disclosed: %s in %s under the'
          % (ROW_ID, RESOURCE))
    print('demo licence. SAIRNlaw declares no delete verb, so this probe cannot')
    print('remove it; the row says so in its own description.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
