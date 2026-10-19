"""b18 live verification -- the deployed URLs, not the repo.

A clean `git push` is not proof. This drives the REAL deployed endpoints and
the REAL deployed HTML and reports three states per leg, never two:

  VERIFIED        the deployed thing answered, and the answer is the one b18
                  intends
  FAILED          it answered, and the answer is wrong
  COULD NOT RUN   it could not be reached, or the leg needs a credential or a
                  migration this probe does not have. NEVER folded into
                  VERIFIED -- a 403 means UNVERIFIED, not verified-good
                  (SAIRN-PROCESS-RULES PR 3.2).

WHAT THIS CANNOT CHECK, said up front so the count is not overread:
NEITHER SQL FILE HAS BEEN RUN. sql/sairnlegacy_countersign_schema.sql and
sql/sairnlaw_countersign_schema.sql are not in the live database, so every
countersignature token lookup answers 503 NOT_PROVISIONED in production today.
THAT IS A REFUSAL AND NOT A BYPASS -- the write is refused rather than filed
unsigned -- and arm A1 of api/b18-countersign-lock.test.js asserts exactly
that shape against the real dispatcher. But it means the HAPPY PATH of F1 and
C2 cannot be driven live by anybody until Michael runs them.

Run:  python docs/hank-evidence/b18_live_gate_probe.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'tools'))

try:
    import urllib.error
    from sairn_http import fetch as sairn_fetch
    HAVE_HTTP = True
except Exception as _e:                                  # pragma: no cover
    HAVE_HTTP = False
    IMPORT_WHY = str(_e)

BASE = 'https://sairn.vercel.app'

verified, failed, cannot = [], [], []


def ok(label, detail=''):
    verified.append(label)
    print('  VERIFIED       ' + label + (('  -- ' + detail) if detail else ''))


def bad(label, detail=''):
    failed.append(label)
    print('  FAILED         ' + label + (('  -- ' + detail) if detail else ''))


def no(label, why):
    cannot.append(label)
    print('  COULD NOT RUN  ' + label + '  -- ' + why)


def _call(method, path, body=None, headers=None):
    """(status, text). An HTTPError is a REAL ANSWER here -- a 401 and a 405
    are the two the probe is looking for -- so it is unwrapped rather than
    allowed to look like a transport failure."""
    h = {}
    if body is not None:
        h['Content-Type'] = 'application/json'
    if headers:
        h.update(headers)
    data = json.dumps(body).encode('utf-8') if body is not None else None
    try:
        st, raw = sairn_fetch(BASE + path, method=method, data=data, headers=h)
    except urllib.error.HTTPError as e:
        st, raw = e.code, (e.read() or b'')
    return st, (raw.decode('utf-8', 'replace') if isinstance(raw, bytes) else str(raw))


def post(path, body, headers=None):
    return _call('POST', path, body, headers)


def get(path):
    return _call('GET', path)


print(__doc__.strip().splitlines()[0])
print()

if not HAVE_HTTP:
    no('every leg', 'tools/sairn_http.py could not be imported: ' + IMPORT_WHY)
else:
    # ── 1. THE TWO NEW ENDPOINTS EXIST AND ARE ROUTED ──────────────────────
    # A 405 on GET is the RIGHT answer and is the cheapest proof the route is
    # deployed: it means the handler ran. A 404 means Vercel never built it.
    for name, path in (('leg-countersign', '/api/leg-countersign'),
                       ('law-countersign', '/api/law-countersign')):
        try:
            st, txt = get(path)
        except Exception as e:
            no(name + ' is routed', 'the request itself failed: ' + str(e)[:120])
            continue
        if st == 405:
            ok(name + ' is routed and answers 405 on GET',
               'the handler ran -- POST only, which is its first line')
        elif st == 404:
            bad(name + ' is routed', 'HTTP 404 -- Vercel did not build this route')
        else:
            no(name + ' is routed', 'HTTP ' + str(st) + ': ' + txt[:140])

    # ── 2. NO LICENCE = 401 NO_LICENSE, BEFORE ANYTHING ELSE ───────────────
    # This is the auth boundary the push gate refused b18's first draft for
    # not having in the route file. Driving it live is the point.
    for name, path in (('leg-countersign', '/api/leg-countersign'),
                       ('law-countersign', '/api/law-countersign')):
        try:
            st, txt = post(path, {'action': 'prepare'})
        except Exception as e:
            no(name + ' refuses a bearer-less POST', 'request failed: ' + str(e)[:120])
            continue
        if st == 401 and 'NO_LICENSE' in txt:
            ok(name + ' refuses a bearer-less POST 401 NO_LICENSE',
               'the boundary is in the route file and it RUNS')
        else:
            bad(name + ' refuses a bearer-less POST',
                'HTTP ' + str(st) + ': ' + txt[:140])

    # ── 3. AN UNKNOWN ACTION IS A 400 THAT NAMES THE ALLOWLIST ─────────────
    # Needs a licence, which this probe does not have. Stated rather than
    # attempted and reported as a pass.
    #
    # THE LABEL NO LONGER SPELLS THE LIST, FIXED 2026-10-19 (b20). It read
    # "naming prepare/countersign/status" and b20 added a FOURTH action,
    # `open`. The arm is COULD NOT RUN so nothing failed -- which is exactly
    # the shape worth catching: a label that quietly stopped describing the
    # thing, in a check whose own result could never contradict it. The
    # endpoint derives that message from its ACTIONS array, so the honest
    # label names the array rather than a snapshot of it.
    no('an unknown action is a 400 naming the endpoint\'s ACTIONS allowlist',
       'needs a valid licence key, which this probe deliberately does not '
       'carry. api/b18-countersign-lock.test.js arm K14 drives it against the '
       'real handler, and it asserts the MESSAGE SHAPE rather than the list, '
       'which is why adding `open` in b20 did not make it red')

    # ── 4. THE SQL IS NOT RUN, SO THE LOCKS ANSWER 503 ─────────────────────
    no('F1 leg_cremations happy path (prepare -> countersign -> write)',
       'sql/sairnlegacy_countersign_schema.sql HAS NOT BEEN RUN, so the token '
       'table does not exist and every lookup answers 503 NOT_PROVISIONED. '
       'Needs a signed session for TWO different licensed directors as well')
    no('C2 law_trusttx two-stage happy path',
       'sql/sairnlaw_countersign_schema.sql HAS NOT BEEN RUN. Needs a '
       'paralegal session AND a bar-admitted session on one licence')
    no('C1 bookkeeper credential creation',
       'the bookkeeper CHECK-constraint widening block at the bottom of '
       'sql/sairnlaw_employee_auth_schema.sql HAS NOT BEEN RUN, so Postgres '
       'refuses the role with 23514. The picker offers it and says so')

    # ── 5. THE CLIENT HALVES, WHICH NEED NO CREDENTIAL ─────────────────────
    # The deployed HTML is fetchable without auth, so these are the legs this
    # probe can actually prove. THREE OF THEM ARE ABSENCE CHECKS -- the only
    # way to verify a deletion deployed.
    try:
        st, html = get('/stonedesk.html')
        if st != 200:
            st, html = get('/stonedesk')
    except Exception as e:
        st, html = 0, ''
        no('every stonedesk client leg', 'could not fetch the page: ' + str(e)[:120])

    if st == 200 and html:
        CHECKS = [
            ('present', 'function setPending(on){',
             'the grant button reset is ONE function, called from all three exits'),
            ('present', "sdReadFailedNote('employee profiles')",
             'a FAILED profile read says so instead of "No profiles set yet."'),
            ('present', "sdAuthWasRefused('employee_profile')",
             'and a REFUSED read is a third message, not an absence'),
            ('present', 'Could not complete the save -- nothing was confirmed',
             'the profile save has a .catch and it reports'),
            ('absent', "errEl.textContent='Network error -- check your connection and try again'",
             'THE OLD WORDING IS GONE -- it reported a CREATED credential as a '
             'network failure. An absence check is the only way to verify a '
             'deletion deployed'),
            ('absent', "btn.textContent='Granting...';btn.disabled=true;",
             'the unguarded btn dereference is gone, replaced by setPending()'),
            ('absent', "listEl.innerHTML='<div style=\"color:var(--muted)\">No profiles set yet.</div>';return;}\n      var expLbl",
             'the three-state branch really is between the empty test and the '
             'render -- this exact adjacency no longer exists'),
        ]
        for kind, needle, why in CHECKS:
            found = needle in html
            label = ('PRESENT: ' if kind == 'present' else 'ABSENT: ') + needle[:58]
            if (kind == 'present') == found:
                ok(label, why)
            else:
                bad(label, why + '  [found=' + str(found) + ']')
    elif st:
        no('every stonedesk client leg', 'the page answered HTTP ' + str(st))

    # ── 6. sairnlaw.html's PICKER ──────────────────────────────────────────
    try:
        st, lhtml = get('/sairnlaw.html')
        if st != 200:
            st, lhtml = get('/sairnlaw')
    except Exception as e:
        st, lhtml = 0, ''
    if st == 200 and lhtml:
        if 'value="bookkeeper">Bookkeeper' in lhtml:
            ok('PRESENT: the sairnlaw provisioning picker offers Bookkeeper',
               'C1 is reachable from the UI -- and the comment beside it says '
               'the database will refuse it until the migration runs')
        else:
            bad('PRESENT: the sairnlaw picker offers Bookkeeper',
                'the deployed page does not carry the option')
    elif st:
        no('the sairnlaw picker', 'the page answered HTTP ' + str(st))

print()
print('  %d verified, %d failed, %d could not run'
      % (len(verified), len(failed), len(cannot)))
if failed:
    print('  FAILED: ' + '; '.join(failed))
if cannot:
    print('  COULD NOT RUN (these are NOT passes):')
    for c in cannot:
        print('    - ' + c)
sys.exit(1 if failed else 0)
