#!/usr/bin/env python
# OWNER: cody
"""Did the 2026-10-05 missing-table runbook actually work? Asks the endpoint.

    python tools/gate1_verify.py                 # all six apps
    python tools/gate1_verify.py --app sairnsenior
    python tools/gate1_verify.py --fixtures      # the criteria lock, alone

Exit 0 every expected table present, 1 one or more still missing, 2 COULD NOT
RUN. REPORT ONLY -- every request is action:'read' and nothing is written.

── WHY A TOOL AND NOT JUST THE CONFIRM QUERY ───────────────────────────────
`sql/zz_confirm_2026-10-05_missing_tables.sql` asks POSTGRES whether the tables
exist. That is necessary and it is not the same question as whether THE APP CAN
REACH THEM. A CREATE that lands while its GRANT block does not leaves a table
`information_schema` reports happily and `api/sd-data.js` answers 503
NOT_PROVISIONED on -- the identical answer to a table that was never created.

So the confirm query and this tool are two different instruments on purpose, and
the runbook says to run BOTH. The query sees the catalogue; this sees what a
signed-in employee sees.

── IT SIGNS IN, BECAUSE A LICENCE KEY ANSWERS 37% OF THE QUESTION ──────────
Measured 2026-10-05 over every app with a demo key: with a licence key alone,
216 of 402 declared tables were REFUSED because the resource sits behind the
employee session gate, so the answer was unobtainable for more than half. Four
of the six apps below have session-gated tables in this set. The PINs are in
docs/2026-09-03-demo-credentials.md, which is the same document the keys come
from.

A FAILED SIGN-IN IS EXIT 2 AND NEVER A FALLBACK to an unauthenticated run: the
unauthenticated REFUSED list has the same shape as a real result and would be
indistinguishable from one.

── WHAT IT DOES NOT ESTABLISH, said here rather than discovered later ──────
  * THAT A WRITE SUCCEEDS. Every request is a read. A table can exist, be
    reachable, and still reject a write on a column mismatch.
  * THAT THE TABLE'S SHAPE IS RIGHT. Existence is not shape.
  * ANYTHING ABOUT A CUSTOMER LICENCE. Six demo licences are read. A customer
    tenant is a different database row set and nothing here touches one.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sairn_http                                               # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = 'https://sairn.vercel.app/api/sd-data'
CONTROLLED_BY = ['tests/run_gate1_verify_probe.py']
CRITERIA_VERSION = '2026-10-05.1'

# app -> (licence key, PIN, auth endpoint name, {table: resource})
#
# THE RESOURCE IS NOT THE TABLE AND THAT IS THE WHOLE TRAP THIS MAP EXISTS FOR.
# api/sd-data.js dispatches on the RESOURCE name, and SAIRNgrounds and
# SAIRNscape deliberately map one to the other -- resource `properties` reaches
# table `grd_properties`. Asking for a table name that is not a resource gets a
# 400 "Unsupported action/resource combination", which reads like a finding and
# is not one. Written out per table rather than derived by stripping a prefix,
# because a stripped prefix is a guess and this file is read by somebody
# checking whether a migration worked.
TARGETS = {
    'stonedesk': ('SD-AUDIT-2026', '31840627', 'sd-auth', {
        'sd_locations': 'locations',
        'sd_approvals': 'sd_approvals',
        'sd_supplier_lead_times': 'supplier_lead_times',
    }),
    'sairngrounds': ('GRD-DEMO-2026', '27593016', 'grd-auth', {
        'grd_rounds': 'grd_rounds',
        'grd_cart_orders': 'grd_cart_orders',
    }),
    'sairndental': ('DNT-PINNACLE-2026', '25741609', 'dnt-auth', {
        'dnt_gfe': 'dnt_gfe',
        'dnt_recall_outreach': 'dnt_recall_outreach',
        'dnt_txplans': 'dnt_txplans',
    }),
    'sairnmechanical': ('MECH-PINNACLE-2026', '58203764', 'mech-auth', {
        'mech_credentials': 'mech_credentials',
    }),
    'sairnsenior': ('SEN-PINNACLE-2026', '90128473', 'sen-auth', {
        'sen_applicants': 'sen_applicants',
        'sen_authorizations': 'sen_authorizations',
        'sen_branches': 'sen_branches',
        'sen_franchise_agreements': 'sen_franchise_agreements',
        'sen_payer_contracts': 'sen_payer_contracts',
        'sen_referrals': 'sen_referrals',
        'sen_referral_sources': 'sen_referral_sources',
        'sen_training_records': 'sen_training_records',
        'sen_training_rules': 'sen_training_rules',
    }),
    'sairnroofing': ('RF-AUDIT-2026', '17462059', 'rf-auth', {
        'rf_entities': 'rf_entities',
        'rf_bonding': 'rf_bonding',
        'rf_prequal_documents': 'rf_prequal_documents',
        'rf_job_hazard_assessments': 'rf_job_hazard_assessments',
        'rf_safety_equipment': 'rf_safety_equipment',
        'rf_supplier_documents': 'rf_supplier_documents',
        'rf_job_warranties': 'rf_job_warranties',
        'rf_warranty_tiers': 'rf_warranty_tiers',
    }),
}

EXPECTED_TOTAL = 26


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
    except Exception as e:                                      # noqa: BLE001
        status = getattr(e, 'code', None)
        try:
            raw = e.read()
        except Exception:                                       # noqa: BLE001
            return status, {'_transport': '%s: %s' % (type(e).__name__, e)}
    if isinstance(raw, bytes):
        raw = raw.decode('utf-8', 'replace')
    try:
        return status, json.loads(raw)
    except Exception:                                           # noqa: BLE001
        return status, {'_raw': raw[:200]}


def classify(status, body):
    """(verdict, detail). Four verdicts and they are NOT three.

    PRESENT / MISSING are answers. REFUSED and UNREADABLE are the third state:
    the question was not answered, and folding either into MISSING would invite
    a re-run of a migration that is already there (PR 1.11).
    """
    if not isinstance(body, dict):
        return 'UNREADABLE', str(body)[:80]
    if '_challenged' in body:
        return 'UNREADABLE', 'Vercel bot challenge'
    if '_transport' in body:
        return 'UNREADABLE', body['_transport']
    if status == 200 and body.get('ok'):
        return ('PRESENT' if body.get('provisioned') else 'MISSING'), ''
    err = body.get('error') or {}
    return 'REFUSED', '%s %s' % (status, err.get('code') or err.get('message')
                                 or '')


def run(only=None):
    rows, could_not = [], []
    for app, (key, pin, auth, tables) in sorted(TARGETS.items()):
        if only and app != only:
            continue
        url = DATA.rsplit('/api/', 1)[0] + '/api/' + auth
        st, b = post(url, key, {'action': 'login',
                                'employee_id': 'sairn-demo-owner', 'pin': pin})
        tok = b.get('token') if isinstance(b, dict) else None
        if not tok:
            could_not.append('%s: sign-in at /api/%s returned %s %s -- the %d '
                             'table(s) for this app WERE NOT CHECKED'
                             % (app, auth, st, json.dumps(b)[:120],
                                len(tables)))
            continue
        for table, resource in sorted(tables.items()):
            st2, b2 = post(DATA, key, {'action': 'read', 'resource': resource,
                                       'app_id': app, 'payload': {}}, tok)
            verdict, detail = classify(st2, b2)
            rows.append((app, table, resource, verdict, detail))
    return rows, could_not


def run_fixtures(verbose=True):
    """The criteria lock: classify() on hand-built endpoint answers."""
    bad = []
    CASES = [
        ('a provisioned read WITH rows', 200,
         {'ok': True, 'provisioned': True, 'data': [{'id': 'x'}]}, 'PRESENT'),
        # THE TRAP THIS ARM EXISTS FOR, and it is the one a human gets wrong
        # reading the app: an EMPTY table is PRESENT. "No rows" and "no table"
        # are the same screen to a user and different facts to a migration
        # check, and every one of the 26 will be empty the moment it is created.
        ('an EMPTY provisioned table is PRESENT, not MISSING -- all 26 will '
         'read empty the moment they exist', 200,
         {'ok': True, 'provisioned': True, 'data': []}, 'PRESENT'),
        ('provisioned false', 200, {'ok': True, 'provisioned': False,
                                    'data': []}, 'MISSING'),
        ('a session refusal is NOT missing', 403,
         {'error': {'code': 'FORBIDDEN'}}, 'REFUSED'),
        ('an unsupported combination is NOT missing either', 400,
         {'error': {'code': 'BAD_REQUEST'}}, 'REFUSED'),
        ('a bot challenge is UNREADABLE, never a verdict', None,
         {'_challenged': 'x'}, 'UNREADABLE'),
        ('a transport failure is UNREADABLE', None,
         {'_transport': 'x'}, 'UNREADABLE'),
    ]
    for name, st, body, want in CASES:
        got, _d = classify(st, body)
        ok = got == want
        if not ok:
            bad.append((name, want, got))
        if verbose:
            print('  %s %-14s %s' % ('ok  ' if ok else 'FAIL', got, name))
    # THE COUNT IS DERIVED FROM THE MAP, NOT TYPED TWICE.
    total = sum(len(v[3]) for v in TARGETS.values())
    ok = total == EXPECTED_TOTAL
    if not ok:
        bad.append(('the target map holds EXPECTED_TOTAL tables',
                    EXPECTED_TOTAL, total))
    if verbose:
        print('  %s the target map holds %d tables (EXPECTED_TOTAL %d)'
              % ('ok  ' if ok else 'FAIL', total, EXPECTED_TOTAL))
    return bad


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--app')
    ap.add_argument('--fixtures', action='store_true')
    ap.add_argument('--json', action='store_true')
    args = ap.parse_args(argv)

    print('GATE 1 RUNBOOK VERIFY -- READ ONLY (criteria %s)' % CRITERIA_VERSION)
    bad = run_fixtures(verbose=args.fixtures)
    if bad:
        print('  !! THE CRITERIA FAILED THEIR OWN FIXTURES. NOTHING WAS ASKED.')
        for row in bad:
            print('     %s -- wanted %r, got %r' % row)
        return 2
    print('  criteria lock: %d verdict fixtures + the derived table count'
          % 7)
    if args.fixtures:
        return 0

    if args.app and args.app not in TARGETS:
        print('No such app %r. Known: %s'
              % (args.app, ', '.join(sorted(TARGETS))))
        return 2

    rows, could_not = run(args.app)
    if args.json:
        print(json.dumps({'rows': rows, 'could_not_check': could_not},
                         indent=1))
        return 1 if any(r[3] != 'PRESENT' for r in rows) or could_not else 0

    present = [r for r in rows if r[3] == 'PRESENT']
    missing = [r for r in rows if r[3] == 'MISSING']
    other = [r for r in rows if r[3] not in ('PRESENT', 'MISSING')]
    print('')
    for app, table, resource, verdict, detail in rows:
        mark = {'PRESENT': 'ok  ', 'MISSING': 'MISS', }.get(verdict, '?   ')
        print('  %s %-16s %-26s %-12s %s'
              % (mark, app, table, verdict, detail))
    print('\n  PRESENT : %d' % len(present))
    print('  MISSING : %d' % len(missing))
    if other:
        print('  NOT ANSWERED : %d -- NOT a pass and NOT a missing table'
              % len(other))
    if could_not:
        print('\nCOULD NOT CHECK -- this is NOT a pass:')
        for c in could_not:
            print('  ? %s' % c)
    asked = len(rows)
    print('\n  asked about %d of %d expected tables' % (asked, EXPECTED_TOTAL))
    if asked < EXPECTED_TOTAL and not args.app:
        print('  FEWER THAN EXPECTED WERE ASKED ABOUT, so the counts above are '
              'a FLOOR.\n  A sign-in failure above is the usual reason.')
    if missing:
        print('\nSTILL MISSING -- re-paste the schema file for each and re-run '
              'the matching\nsection of sql/zz_confirm_2026-10-05_missing_tables.sql:')
        for app, table, _r, _v, _d in missing:
            print('  - %s / %s' % (app, table))
    if could_not or other:
        return 2 if not missing else 1
    return 1 if missing else 0


if __name__ == '__main__':
    sys.exit(main())
