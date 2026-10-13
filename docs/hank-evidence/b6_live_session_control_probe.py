# b6 item 1 -- the half b5 could not drive: A VALID SESSION GETTING THROUGH.
#
# b5's probe proved a BARE LICENCE KEY is refused 403 on eleven gated
# resources, with four ungated siblings answering 200 on the same key as the
# control. That answers "is the 403 the gate". It does NOT answer "does a
# correctly signed-in caller get through", and a gate that refuses everybody is
# indistinguishable from one that works until somebody drives the positive
# half. b5 recorded that gap; this closes it for SAIRNscape.
#
# SAIRNfreedom IS NOT DRIVEN AND THE REASON IS RECORDED RATHER THAN GUESSED:
# docs/2026-09-03-demo-credentials.md has a row for every app with a demo
# employee credential and HAS NO SAIRNfreedom ROW. There is no SF-PINNACLE-2026
# PIN in this repo, so the session half cannot be driven for the five sf_
# resources. Searched: grep over *.md/*.sql/*.txt for SF-PINNACLE-2026 returns
# the licence seed and the open-work index, neither of which carries a PIN.
#
# NOTHING HERE CAN PERSIST A ROW. Every write attempt sends an ID-LESS payload,
# so the handler's own "payload.id is required" refuses before any store call
# even if a gate were absent entirely.
import sys, os, json
sys.path.insert(0, os.path.join(os.getcwd(), 'tools'))
from sairn_http import fetch_json, Challenged

DATA = 'https://sairn.vercel.app/api/sd-data'
AUTH = 'https://sairn.vercel.app/api/scp-auth'
LIC = 'SCP-DEMO-2026'
EMP, PIN = 'sairn-demo-owner', '73018452'

# The six SAIRNscape resources gated by SD_SESSION_GATED, plus two that are
# deliberately ungated (UNGATED_REST) as the negative control.
GATED = ['scp_designs', 'scp_quotes', 'invoices', 'scp_vendors',
         'scp_progress_photos', 'customers']
UNGATED = ['scp_jobs', 'scp_irr_zones']


def call(action, resource, key, token=None):
    h = {'X-SD-Auth': token} if token else None
    try:
        r = fetch_json(DATA, payload={'action': action, 'resource': resource,
                                      'app_id': 'sairnscape', 'payload': {}},
                       key=key, headers=h)
        body = r.body if isinstance(r.body, dict) else {}
        code = ((body.get('error') or {}).get('code')) or ''
        rows = body.get('data')
        extra = ''
        if isinstance(rows, list):
            extra = ' rows=%d' % len(rows)
        if 'provisioned' in body:
            extra += ' provisioned=%s' % body.get('provisioned')
        return '%s %s%s' % (r.status, code or ('ok' if body.get('ok') else ''), extra)
    except Challenged:
        return 'CHALLENGED'
    except Exception as e:
        return 'ERR %s' % type(e).__name__


print('LIVE SESSION CONTROL -- SAIRNscape, b6 item 1')
print('data  %s' % DATA)
print('auth  %s' % AUTH)
print()

# ── STEP 1: MINT A REAL SESSION ───────────────────────────────────────────
tok = None
try:
    a = fetch_json(AUTH, payload={'action': 'login', 'employee_id': EMP, 'pin': PIN},
                   key=LIC)
    body = a.body if isinstance(a.body, dict) else {}
    tok = (body.get('data') or {}).get('token') or body.get('token')
    role = (body.get('data') or {}).get('role') or body.get('role')
    print('login -> %s  token=%s  role=%s'
          % (a.status, 'YES len=%d' % len(tok) if tok else 'NONE', role))
    if not tok:
        print('  body: %s' % json.dumps(body)[:300])
except Exception as e:
    print('login -> EXC %s %s' % (type(e).__name__, e))

if not tok:
    print()
    print('COULD NOT RUN: no session token, so the positive half was NOT driven.')
    print('That is a third state. It is not evidence the gate is broken and it')
    print('is not evidence it works.')
    sys.exit(2)

print()
print('%-22s %-28s %-28s' % ('resource', 'BARE KEY (no session)', 'WITH SESSION'))
rows = []
for r in GATED + UNGATED:
    bare = call('read', r, LIC)
    sess = call('read', r, LIC, tok)
    gated = r in GATED
    print('%-22s %-28s %-28s %s' % (r, bare, sess, 'GATED' if gated else 'ungated'))
    rows.append((r, gated, bare, sess))

# ── STEP 2: AND A WRITE, ID-LESS, WITH THE SESSION ────────────────────────
# The point is that it reaches the HANDLER BODY rather than the gate: a 400
# "payload.id is required" proves the session passed the gate and the id check
# refused, which is a stronger statement than a 200 on a read.
print()
w = call('write', 'scp_designs', LIC, tok)
print('write scp_designs WITH SESSION, id-less payload -> %s' % w)
print('  a 400 here is the HANDLER refusing, not the gate -- which is what')
print('  proves the session got through. Nothing is stored by an id-less write.')

print()
bad = []
for r, gated, bare, sess in rows:
    if gated:
        if not bare.startswith('403'):
            bad.append((r, 'gated but a BARE KEY was not refused: ' + bare))
        if sess.startswith('403') or sess.startswith('401'):
            bad.append((r, 'gated and a VALID SESSION was refused: ' + sess))
    else:
        if bare.startswith('403'):
            bad.append((r, 'ungated control refused a bare key: ' + bare))
if bad:
    print('FINDINGS (%d):' % len(bad))
    for b in bad:
        print('  !', b[0], '--', b[1])
else:
    print('BOTH HALVES HOLD: every gated resource refused the bare key 403 and')
    print('ANSWERED a valid session; every ungated control answered the bare key.')
    print('The 403 is the gate, and the gate opens for a real sign-in.')
sys.exit(1 if bad else 0)
