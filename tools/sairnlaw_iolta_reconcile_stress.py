#!/usr/bin/env python3
# OWNER: cc
"""SAIRNlaw IOLTA reconciliation stress test -- forced bank / trust-ledger / client mismatches.

    python tools/sairnlaw_iolta_reconcile_stress.py            # every scenario, printed
    python tools/sairnlaw_iolta_reconcile_stress.py --json
    python tools/sairnlaw_iolta_reconcile_stress.py --fixtures # criteria lock only

Exit 0 every forced discrepancy is surfaced; 1 at least one reconciles as
"Reconciled" with nothing flagged; 2 COULD NOT RUN (node missing, the module
or the label table not found, or a CONTROL failing).

REAL: api/_lib/law-trust-reconcile.js reconcileTrustLedger(), required as-is,
which is what api/sd-data.js's law_trust_reconcile read calls. REAL:
sairnlaw.html's LAW_RECON_STATUS label table, read from the file, and the
dashboard rule that paints a Trust Alert for a NEGATIVE client
(sairnlaw.html, the `negative_clients` branch). Nothing is stubbed; the
scenarios are data.

THE PASS RULE (CRITERIA_VERSION): a forced discrepancy is SURFACED when the
status is anything other than AGREES, or when it is AGREES and a negative
client is flagged (the dashboard paints a Trust Alert for that). It is
SILENTLY RECONCILED, a FAIL, when the status is AGREES, the label the user
sees is "Reconciled", and no client is negative. A control (correct books)
must come back AGREES, or nothing here has been tested.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

CRITERIA_VERSION = '2026-10-23.1'
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def D(i, c, a, d, **x):
    return dict(id=i, client_id=c, type='Deposit', amount=a, date=d, **x)


def W(i, c, a, d, **x):
    return dict(id=i, client_id=c, type='Disbursement', amount=a, date=d, **x)


# Correct books: A deposits 1000, B deposits 500, A is paid out 200. Trust
# ledger 1300.00; bank 1300.00 on 2026-09-30; every item has cleared.
BASE = [D('T1', 'CL-A', 1000, '2026-09-01', cleared_on='2026-09-02'),
        D('T2', 'CL-B', 500, '2026-09-03', cleared_on='2026-09-04'),
        W('T3', 'CL-A', 200, '2026-09-10', cleared_on='2026-09-11')]
STMT = [{'statement_date': '2026-09-30', 'bank_balance': 1300}]


def with_rows(rows, stmt=STMT, device=130000):
    return {'rows': rows, 'statements': stmt, 'clientTotalCents': device}


def replace(rows, idx, **chg):
    out = [dict(r) for r in rows]
    out[idx].update(chg)
    return out


SCENARIOS = [
    ('C0', 'control', 'correct books, every leg agrees', with_rows(BASE)),
    ('M1', 'bank', 'the bank is ONE CENT short (1299.99)',
     with_rows(BASE, [{'statement_date': '2026-09-30', 'bank_balance': 1299.99}])),
    ('M2', 'bank', 'the bank holds $500 the ledger never recorded',
     with_rows(BASE, [{'statement_date': '2026-09-30', 'bank_balance': 1800}])),
    ('M3', 'client', "the device's client-ledger total is one cent off the server's",
     with_rows(BASE, device=129999)),
    ('M4', 'ledger', 'a $200 disbursement keyed as a DEPOSIT (trust ledger overstated by $400)',
     with_rows(replace(BASE, 2, type='Deposit'), device=170000)),
    ('M5', 'concealment', 'a $40 TRUST SHORTFALL parked as a "deposit in transit" dated 91 days '
     'before the statement. Client B is credited 540; only 1300 is in the bank against 1340 owed',
     with_rows(BASE + [D('T9', 'CL-B', 40, '2026-07-01', cleared=False)], device=134000)),
    ('M6', 'client', "A's $200 disbursement charged to B's ledger, totals unchanged (A shows "
     "1000 not 800; B shows 300 not 500)",
     with_rows(replace(BASE, 2, client_id='CL-B'))),
    ('M7', 'client', "a $600 disbursement for A charged to B, driving B NEGATIVE (-100)",
     with_rows([BASE[0], BASE[1], W('T3', 'CL-B', 600, '2026-09-10', cleared_on='2026-09-11')],
               [{'statement_date': '2026-09-30', 'bank_balance': 900}], device=90000)),
    ('M8', 'ledger', "an unreadable amount on one row ('12O0' with a letter O)",
     with_rows(replace(BASE, 0, amount='12O0'))),
    ('M9', 'ledger', 'one row with no date', with_rows(replace(BASE, 1, date=''))),
]

HARNESS = r"""
const fs = require('fs'), path = require('path'), vm = require('vm');
const REPO = process.argv[2];
const S = JSON.parse(process.argv[3]);
const R = require(path.join(REPO, 'api', '_lib', 'law-trust-reconcile.js'));
const HTML = fs.readFileSync(path.join(REPO, 'sairnlaw.html'), 'utf8');
const m = HTML.match(/var LAW_RECON_STATUS=\{[\s\S]*?\n\};/);
if (!m || HTML.indexOf('var LAW_RECON_STATUS=') !== HTML.lastIndexOf('var LAW_RECON_STATUS=')) {
  process.stdout.write(JSON.stringify({ ok: false, err: 'LAW_RECON_STATUS not found exactly once' })); process.exit(0);
}
const ctx = {}; vm.createContext(ctx); vm.runInContext(m[0] + '; this.T = LAW_RECON_STATUS;', ctx);
const negRule = /negative_clients&&d\.negative_clients\.length\)paint\(\[\{t:'A client trust ledger is NEGATIVE/.test(HTML);
const rows = S.map(([id, kind, why, input]) => {
  const out = R.reconcileTrustLedger(input);
  const meta = ctx.T[out.status];
  return { id, kind, why, status: out.status, label: meta ? meta.label : null,
           legs_disagreeing: out.legs_disagreeing, legs_compared: out.legs_compared,
           negative_clients: out.negative_clients,
           clients: (out.clients || []).map((c) => [c.client_id, c.cents]),
           bank: out.legs && out.legs.bank_vs_ledger
             ? { agrees: out.legs.bank_vs_ledger.agrees, expected: out.legs.bank_vs_ledger.expected_bank_cents,
                 outstanding: out.legs.bank_vs_ledger.outstanding_cents } : null };
});
process.stdout.write(JSON.stringify({ ok: true, negative_rule_present: negRule, rows }));
"""


def classify(row, negative_rule_present=True):
    if row['kind'] == 'control':
        return ('CONTROL-OK', 'correct books reconcile') if row['status'] == 'AGREES' \
            else ('CONTROL-FAIL', 'correct books came back %s' % row['status'])
    if row['status'] != 'AGREES':
        return 'PASS', 'surfaced as %s (%s)%s' % (
            row['status'], row['label'],
            ', disagreeing: ' + ', '.join(row['legs_disagreeing']) if row.get('legs_disagreeing') else '')
    if row.get('negative_clients') and negative_rule_present:
        return 'PASS', ('status AGREES, but client(s) %s are NEGATIVE and the dashboard paints a '
                        'Trust Alert' % ', '.join(row['negative_clients']))
    return 'FAIL', ('SILENTLY RECONCILED: status AGREES, the user sees "%s", and nothing is flagged'
                    % row['label'])


FIXTURES = [
    ({'kind': 'bank', 'status': 'DISAGREES', 'label': 'Discrepancy', 'legs_disagreeing': ['bank_vs_ledger']},
     'PASS', 'DISAGREES is surfaced'),
    ({'kind': 'bank', 'status': 'PARTIAL', 'label': 'Partly reconciled'}, 'PASS',
     'PARTIAL is not a pass-as-reconciled'),
    ({'kind': 'client', 'status': 'AGREES', 'label': 'Reconciled', 'negative_clients': []}, 'FAIL',
     'AGREES over a forced discrepancy with nothing flagged is the failure'),
    ({'kind': 'client', 'status': 'AGREES', 'label': 'Reconciled', 'negative_clients': ['CL-B']}, 'PASS',
     'a negative client is flagged loudly even under AGREES'),
    ({'kind': 'control', 'status': 'AGREES'}, 'CONTROL-OK', 'control agrees'),
    ({'kind': 'control', 'status': 'DISAGREES'}, 'CONTROL-FAIL', 'a control that disagrees breaks the harness'),
]


def run_fixtures():
    return ['EXPECTED %s, got %s -- %s' % (w, classify(r)[0], why)
            for r, w, why in FIXTURES if classify(r)[0] != w]


def main(argv):
    as_json = '--json' in argv
    bad = run_fixtures()
    if bad:
        print('CRITERIA LOCK FAILED -- nothing real was judged:')
        for b in bad:
            print('  ! ' + b)
        return 2
    if not as_json:
        print('SAIRNLAW IOLTA RECONCILE STRESS -- criteria lock %s: %d/%d fixtures classify correctly'
              % (CRITERIA_VERSION, len(FIXTURES), len(FIXTURES)))
    if '--fixtures' in argv:
        return 0
    node = shutil.which('node')
    if not node:
        print('COULD NOT RUN: node is not on PATH.')
        return 2
    d = tempfile.mkdtemp(prefix='iolta-stress-')
    h = os.path.join(d, 'harness.js')
    with open(h, 'w', encoding='utf-8') as fh:
        fh.write(HARNESS)
    try:
        r = subprocess.run([node, h, REPO, json.dumps(SCENARIOS)], capture_output=True, text=True,
                           encoding='utf-8', errors='replace', timeout=120, cwd=REPO)
        out = json.loads(r.stdout or '{}')
    except Exception as e:                                       # noqa: BLE001
        print('COULD NOT RUN: %s: %s' % (type(e).__name__, e))
        return 2
    if not out.get('ok'):
        print('COULD NOT RUN: %s' % (out.get('err') or (r.stderr or '')[-400:]))
        return 2
    verdicts = []
    for row in out['rows']:
        row['verdict'], row['reason'] = classify(row, out['negative_rule_present'])
        verdicts.append(row['verdict'])
    code = 2 if 'CONTROL-FAIL' in verdicts else (1 if 'FAIL' in verdicts else 0)
    if as_json:
        print(json.dumps({'criteria': CRITERIA_VERSION, 'rows': out['rows'],
                          'scenarios': SCENARIOS, 'exit': code}, indent=1))
        return code
    print('REAL: api/_lib/law-trust-reconcile.js + sairnlaw.html LAW_RECON_STATUS '
          '(negative-client alert rule present: %s)' % out['negative_rule_present'])
    for row, (_i, _k, _w, inp) in zip(out['rows'], SCENARIOS):
        print('')
        print('%-12s %s  [%s] %s' % (row['verdict'], row['id'], row['kind'], row['why']))
        print('   rows     : %s' % json.dumps(inp['rows']))
        print('   bank     : %s | device total cents: %s' % (json.dumps(inp['statements']), inp['clientTotalCents']))
        print('   result   : status %s, label "%s", legs compared %s, disagreeing %s, clients %s, '
              'negative %s, bank leg %s'
              % (row['status'], row['label'], row['legs_compared'], row['legs_disagreeing'],
                 row['clients'], row['negative_clients'], row['bank']))
        print('   reason   : %s' % row['reason'])
    print('')
    print('%d scenarios: %d PASS, %d FAIL, controls %s'
          % (len(verdicts), verdicts.count('PASS'), verdicts.count('FAIL'),
             'FAILED' if 'CONTROL-FAIL' in verdicts else 'OK'))
    if code == 2:
        print('COULD NOT RUN: a control failed.')
    return code


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
