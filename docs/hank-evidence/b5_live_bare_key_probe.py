# Live bare-key verification, b5 item 3. READ-ONLY INTENT.
# Every WRITE attempt uses an id-less payload so that if the gate were absent
# the handler's own "payload.id is required" 400 refuses BEFORE any store call.
# Nothing can persist from this probe even on a total gate failure.
import sys, os, json
sys.path.insert(0, os.path.join(os.getcwd(), 'tools'))
from sairn_http import fetch_json, Challenged

URL = 'https://sairn.vercel.app/api/sd-data'
CASES = [
    # (licence, app_id, resource, GATED?)
    ('SF-PINNACLE-2026', 'sairnfreedom', 'sf_officers',   True),
    ('SF-PINNACLE-2026', 'sairnfreedom', 'sf_sessions',   True),
    ('SF-PINNACLE-2026', 'sairnfreedom', 'sf_shifts',     True),
    ('SF-PINNACLE-2026', 'sairnfreedom', 'sf_tickets',    True),
    ('SF-PINNACLE-2026', 'sairnfreedom', 'sf_rentals',    True),
    # CONTROLS on the same key: Tier A but deliberately UNGATED. A 200 here is
    # what makes a 403 above the GATE rather than a bad key or a dead endpoint.
    ('SF-PINNACLE-2026', 'sairnfreedom', 'sf_events',     False),
    ('SF-PINNACLE-2026', 'sairnfreedom', 'sf_products',   False),
    ('SCP-DEMO-2026',    'sairnscape',   'scp_designs',   True),
    ('SCP-DEMO-2026',    'sairnscape',   'scp_quotes',    True),
    ('SCP-DEMO-2026',    'sairnscape',   'invoices',      True),
    ('SCP-DEMO-2026',    'sairnscape',   'scp_vendors',   True),
    ('SCP-DEMO-2026',    'sairnscape',   'scp_progress_photos', True),
    ('SCP-DEMO-2026',    'sairnscape',   'customers',     True),
    # CONTROLS on the scp key: in UNGATED_REST by design.
    ('SCP-DEMO-2026',    'sairnscape',   'scp_jobs',      False),
    ('SCP-DEMO-2026',    'sairnscape',   'scp_irr_zones', False),
]
print('LIVE BARE-KEY VERIFICATION -- no X-SD-Auth header on any call below')
print('endpoint %s' % URL)
print()
print('%-18s %-22s %-6s %-26s %-26s' % ('licence','resource','gated','read','write(id-less)'))
rows=[]
for lic, app, res, gated in CASES:
    out=[]
    for action in ('read','write'):
        try:
            r = fetch_json(URL, payload={'action':action,'resource':res,
                                         'app_id':app,'payload':{}}, key=lic)
            body=r.body if isinstance(r.body,dict) else {}
            code=((body.get('error') or {}).get('code')) or ''
            out.append('%s %s' % (r.status, code or ('ok' if body.get('ok') else '')))
        except Challenged as e:
            out.append('CHALLENGED')
        except Exception as e:
            out.append('ERR %s' % type(e).__name__)
    print('%-18s %-22s %-6s %-26s %-26s' % (lic,res,'YES' if gated else 'no',out[0],out[1]))
    rows.append((lic,res,gated,out[0],out[1]))
print()
# VERDICT
bad=[]
for lic,res,gated,rd,wr in rows:
    if gated:
        if not (rd.startswith('403') and wr.startswith('403')): bad.append((lic,res,rd,wr,'GATED but not 403 on both'))
    else:
        if rd.startswith('403'): bad.append((lic,res,rd,wr,'UNGATED control answered 403 -- key or endpoint, not the gate'))
if bad:
    print('FINDINGS (%d):'%len(bad))
    for b in bad: print('  !',b)
else:
    print('ALL AS EXPECTED: every gated resource refused 403 on both verbs with a bare key, and every ungated control did not.')
sys.exit(1 if bad else 0)
