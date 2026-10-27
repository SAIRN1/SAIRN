#!/usr/bin/env python3
# OWNER: cc
"""SAIRNlegacy -- PRESENCE PASSED AS PROOF stress test (cremation chain, billing, price list).

    python tools/sairnlegacy_presence_stress.py           # every scenario, the routing table, the record specs
    python tools/sairnlegacy_presence_stress.py --json
    python tools/sairnlegacy_presence_stress.py --ablate  # also run the named ablation

Exit 0 no false positive shown; 1 at least one; 2 COULD NOT RUN (the plan fails
tools/presence_proof.py's checklist, node missing, a function not found exactly
once, a CONTROL failing, or a FAIL that routes to no owner).

SCOPE -- what is REAL and what is STUBBED:
  L1 cremation write: REAL api/sd-data.js handler with the REAL MODE_ALWAYS
     countersignature lock (api/_lib/countersign.js) and a REAL signed session
     token. STUBBED: the licence; Supabase (a valid, unspent, second-person
     token row whose content hash is computed by the real contentHash() over
     the exact payload; an active employee row; the write records what would
     be stored). The b18 suite's own harness shape.
  L2 invoice write: the same REAL handler, role owner, leg_invoices.
  L3 statement of goods and services: REAL legPriceOf() and
     legComposeStatement() from sairnlegacy.html in a vm.
Nothing in the app is edited. Findings are ROUTED (checklist item ROUTE),
each with a ready-to-file record tagged [launch-wave:sairnlegacy]; this tool
writes nothing to the register.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import presence_proof as PP                                         # noqa: E402

CRITERIA_VERSION = '2026-10-27.1'
WAVE_APP = 'sairnlegacy'
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

AUTH_ALL = {'authorization_on_file': True, 'id_verified': True, 'waiting_period_observed': True,
            'witness_present': True}
AUTH_NONE = {k: False for k in AUTH_ALL}
INPUTS = {
    'L1c': {'t': 'crem', 'p': dict({'id': 'CR-9', 'case_id': 'CS-1', 'status': 'Completed'}, **AUTH_ALL)},
    'L1a': {'t': 'crem', 'p': dict({'id': 'CR-9', 'case_id': 'CS-1', 'status': 'Completed'}, **AUTH_NONE)},
    'L1b': {'t': 'crem', 'p': {'id': 'CR-9', 'case_id': 'CS-1', 'status': 'Completed'}},
    'L2c': {'t': 'inv', 'p': {'id': 'IV-1', 'case_id': 'CS-1', 'line_items': [{'label': 'Basic', 'amount': 5000}],
                              'payments': [{'amount': 5000, 'source': 'Cash'}], 'status': 'Paid'}},
    'L2a': {'t': 'inv', 'p': {'id': 'IV-1', 'case_id': 'CS-1', 'line_items': [{'label': 'Basic', 'amount': 5000}],
                              'payments': [], 'status': 'Paid'}},
    'L3c': {'t': 'stmt', 'in': {'offered': [{'id': 's1', 'label': 'Basic services', 'price': 5000}],
                                'selections': {'s1': 'selected'}}},
    'L3e': {'t': 'stmt', 'in': {'offered': [{'id': 's1', 'label': 'Basic services', 'price': ''}],
                                'selections': {'s1': 'selected'}}},
    'L3a': {'t': 'stmt', 'in': {'offered': [{'id': 's1', 'label': 'Basic services', 'price': 0}],
                                'selections': {'s1': 'selected'}}},
    'L3b': {'t': 'stmt', 'in': {'offered': [{'id': 'a', 'label': 'Casket', 'price': 5000},
                                            {'id': 'b', 'label': 'Adjustment', 'price': -5000}],
                                'selections': {'a': 'selected', 'b': 'selected'}}},
}
stored = lambda o: bool(o.get('stored'))                            # noqa: E731
printable = lambda o: o.get('printable') is True                   # noqa: E731
SCENARIOS = [
    PP.Scenario('L1c', 'filed with its countersignature', 'a cremation authorisation with every '
                'statutory check recorded, countersigned by a second qualified person', '', stored,
                expect_claim=True),
    PP.Scenario('L1a', 'filed with its countersignature', 'status Completed with authorization_on_file, '
                'id_verified, waiting_period_observed and witness_present ALL false',
                'the record is filed with its countersignature as Completed although every authorisation '
                'check is recorded false -- the lock checks the token, never the record',
                lambda o: stored(o) and (o.get('row') or {}).get('status') == 'Completed',
                site='api/_lib/countersign.js:247'),
    PP.Scenario('L1b', 'filed with its countersignature', 'status Completed with NO authorisation '
                'fields at all', 'the record is filed with its countersignature as Completed with no '
                'authorisation field present', lambda o: stored(o), site='api/sd-data.js:17528'),
    PP.Scenario('L2c', 'Paid', 'a $5,000 invoice with a $5,000 payment', '', stored, expect_claim=True),
    PP.Scenario('L2a', 'Paid', 'a $5,000 invoice with NO payment; the client sent status "Paid"',
                'the server stores status Paid on a $5,000 invoice with no payment, and the list badges it '
                'Paid and drops it from the open count', lambda o: stored(o)
                and (o.get('row') or {}).get('status') == 'Paid', site='api/sd-data.js:17552'),
    PP.Scenario('L3c', 'printable', 'every selected line has a real price', '',
                lambda o: printable(o) and o.get('total') == 5000, expect_claim=True),
    PP.Scenario('L3e', 'printable', 'the price field is BLANK -- no price is on file',
                'the statement is printable with a blank price', printable, site='sairnlegacy.html:3798'),
    PP.Scenario('L3a', 'printable', 'a $0 price, which is what saveGplServicePrice stores for a blank input',
                'the statement is printable at a $0 price, so any payment then marks the invoice Paid',
                printable, site='sairnlegacy.html:3748'),
    PP.Scenario('L3b', 'printable', 'a +$5,000 casket and a -$5,000 "adjustment" on the price list',
                'the statement is printable with a total of $0, offset by a negative price line',
                lambda o: printable(o) and o.get('total') == 0, site='sairnlegacy.html:3798'),
]
ABLATION = ("Compile legPriceOf with its blank-input guard removed: L3e must turn PASS -> FAIL "
            "(run with --ablate).")
SEVERITY = {'L1a': 'high', 'L1b': 'high', 'L2a': 'high', 'L3a': 'moderate', 'L3b': 'moderate', 'L3e': 'moderate'}

HARNESS = r"""
const fs = require('fs'), path = require('path'), vm = require('vm'), Module = require('module');
const REPO = process.argv[2], INPUTS = JSON.parse(process.argv[3]), ABLATE = process.argv[4] === '1';
const API = path.join(REPO, 'api');
// Fixture values only, built by join so no literal reads as a credential (the b18 suite's shape).
process.env.SD_AUTH_SECRET = ['cc', 'b58', 'presence', 'fixture'].join('-');
process.env.SUPABASE_URL = 'https://sb.invalid';
process.env.SUPABASE_SERVICE_ROLE_KEY = ['stress', 'fixture'].join('-');
const HASH = 'b58-leg-hash';
const { signSessionToken } = require(path.join(API, '_lib', 'auth'));
const cs = require(path.join(API, '_lib', 'countersign'));
const licP = require.resolve(path.join(API, '_lib', 'license'));
const lm = new Module(licP); lm.filename = licP; lm.loaded = true;
lm.exports = { validateLicenseKey: async () => ({ valid: true, active: true, license_hash: HASH,
  trial_ends_at: null, stripe_subscription_id: null, app_id: 'sairnlegacy' }) };
require.cache[licP] = lm;
let tokenRow = null, posted = [];
global.fetch = async (url, init) => {
  const u = String(url), method = (init && init.method) || 'GET';
  if (/_countersign_tokens/.test(u)) {
    if (method === 'PATCH') return { ok: true, status: 200, json: async () => (tokenRow ? [{ id: 'tok-1' }] : []) };
    return { ok: true, status: 200, json: async () => (tokenRow ? [tokenRow] : []) };
  }
  if (/_employee_auth/.test(u)) {
    const m = u.match(/employee_id=eq\.([^&]+)/); const who = m ? decodeURIComponent(m[1]) : 'emp-1';
    return { ok: true, status: 200, json: async () => [{ license_hash: HASH, employee_id: who, role: 'owner', active: true }] };
  }
  if (method === 'POST') { const b = JSON.parse(init.body); posted.push({ url: u, body: b });
    return { ok: true, status: 200, json: async () => [b] }; }
  return { ok: true, status: 200, json: async () => [] };
};
const handler = require(path.join(API, 'sd-data.js'));
async function write(resource, payload, role, withToken) {
  posted = [];
  tokenRow = withToken ? { id: 'tok-1', resource, content_hash: cs.contentHash(resource, payload),
    prepared_by: 'emp-1', prepared_role: 'director', countersign_employee_id: 'emp-2', countersign_role: 'director',
    countersigned_at: new Date(Date.now() - 60000).toISOString(), spent_at: null, spent_on_resource: null,
    expires_at: new Date(Date.now() + 300000).toISOString() } : null;
  let status = 0, body = null;
  const res = { status(s) { status = s; return this; }, json(b) { body = b; return this; }, setHeader() {}, end() {} };
  const headers = { authorization: 'Bearer KEY-' + HASH,
    'x-sd-auth': signSessionToken({ app: 'sairnlegacy', employee_id: 'emp-1', role, license_hash: HASH }) };
  if (withToken) headers['x-leg-countersign'] = 'cs-token-placeholder';
  await handler({ method: 'POST', headers, body: { action: 'write', resource, payload } }, res);
  const w = posted.filter((p) => p.url.indexOf(resource) !== -1).pop();
  const rowv = w ? (Array.isArray(w.body) ? w.body[0] : w.body) : null;
  const blob = rowv && (rowv.data || rowv.payload || rowv.record || rowv);
  return { http: status, stored: status >= 200 && status < 300 && !!w, row: blob, err: body && body.error ? body.error.code : null };
}
const HTML = fs.readFileSync(path.join(REPO, 'sairnlegacy.html'), 'utf8');
function once(sig) { const i = HTML.indexOf(sig); if (i < 0 || HTML.indexOf(sig, i + 1) !== -1) throw new Error('NOT EXACTLY ONCE: ' + sig); return i; }
function topFn(sig) { const at = once(sig); return HTML.slice(at, HTML.indexOf(String.fromCharCode(10) + '}', at) + 2); }
let STMT = ['var LEG_SELECTED=', 'function legProblem(code,severity,detail){'].map((s) => { const at = once(s); return HTML.slice(at, HTML.indexOf(String.fromCharCode(10), at)); }).join(String.fromCharCode(10))
  + String.fromCharCode(10) + topFn('function legPriceOf(v){') + String.fromCharCode(10) + topFn('function legComposeStatement(input){');
if (ABLATE) { const g = "if(v===undefined||v===null||v==='')return null;"; if (STMT.indexOf(g) < 0) throw new Error('ablation anchor gone'); STMT = STMT.replace(g, ''); }
function stmt(input) {
  const ctx = { Number, isFinite, Array, Object, String, Math, JSON }; vm.createContext(ctx);
  vm.runInContext(STMT, ctx);
  const r = ctx.legComposeStatement(input);
  return { printable: r.printable, total: r.total, problems: (r.problems || []).map((p) => p.code) };
}
(async () => {
  const out = {};
  for (const [id, inp] of Object.entries(INPUTS)) {
    try {
      if (inp.t === 'crem') out[id] = await write('leg_cremations', inp.p, 'director', true);
      else if (inp.t === 'inv') out[id] = await write('leg_invoices', inp.p, 'owner', false);
      else out[id] = stmt(inp.in);
    } catch (e) { out[id] = { crash: String(e && e.message || e).slice(0, 200) }; }
  }
  process.stdout.write(JSON.stringify({ ok: true, out }));
})().catch((e) => process.stdout.write(JSON.stringify({ ok: false, err: String(e && e.stack || e) })));
"""


def drive(ablate=False):
    node = shutil.which('node')
    if not node:
        return None, 'node is not on PATH'
    d = tempfile.mkdtemp(prefix='leg-presence-')
    h = os.path.join(d, 'harness.js')
    with open(h, 'w', encoding='utf-8') as fh:
        fh.write(HARNESS)
    r = subprocess.run([node, h, REPO, json.dumps(INPUTS), '1' if ablate else '0'], capture_output=True,
                       text=True, encoding='utf-8', errors='replace', timeout=300, cwd=REPO)
    try:
        res = json.loads(r.stdout or '{}')
    except ValueError:
        return None, 'unreadable harness output: %s' % (r.stderr or r.stdout)[-400:]
    if not res.get('ok'):
        return None, res.get('err') or (r.stderr or '')[-400:]
    return res['out'], ''


def main(argv):
    as_json = '--json' in argv
    PP.require_plan(SCENARIOS, ABLATION, __doc__, wave_app=WAVE_APP)
    out, err = drive()
    if out is None:
        print('COULD NOT RUN: %s' % err)
        return 2
    rows, specs = [], []
    for s in SCENARIOS:
        v, why = PP.verdict(s, out.get(s.sid, {'crash': 'no observation'}))
        rows.append({'id': s.sid, 'claim': s.claim, 'truth': s.truth, 'verdict': v, 'reason': why,
                     'input': INPUTS[s.sid], 'observed': out.get(s.sid)})
        if v == 'FAIL':
            specs.append(dict(PP.record_spec(s, WAVE_APP, REPO, SEVERITY.get(s.sid, 'moderate')), id=s.sid))
    abl = None
    if '--ablate' in argv:
        o2, e2 = drive(ablate=True)
        z = [s for s in SCENARIOS if s.sid == 'L3e'][0]
        abl = {'ran': o2 is not None, 'err': e2, 'before': [r['verdict'] for r in rows if r['id'] == 'L3e'][0],
               'after': PP.verdict(z, o2['L3e'])[0] if o2 else None}
    verdicts = [r['verdict'] for r in rows]
    code = 2 if 'CONTROL-FAIL' in verdicts else (1 if 'FAIL' in verdicts else 0)
    if any(x['owner'] is None for x in specs):
        code = 2
    if abl is not None and not (abl['ran'] and abl['before'] == 'PASS' and abl['after'] == 'FAIL'):
        code = 2
    if as_json:
        print(json.dumps({'criteria': CRITERIA_VERSION, 'wave_app': WAVE_APP, 'rows': rows, 'record_specs': specs,
                          'ablation': abl, 'exit': code}, indent=1))
        return code
    print('SAIRNLEGACY PRESENCE STRESS -- criteria %s; plan accepted by tools/presence_proof.py; launch-wave %s'
          % (CRITERIA_VERSION, WAVE_APP))
    for r in rows:
        obs = dict(r['observed'] or {})
        if isinstance(obs.get('row'), dict):
            obs['row'] = {k: obs['row'].get(k) for k in ('status', 'authorization_on_file', 'payments') if k in obs['row']}
        print('')
        print('%-12s %s  claim %r' % (r['verdict'], r['id'], r['claim']))
        print('   truth    : %s' % r['truth'])
        print('   observed : %s' % json.dumps(obs)[:260])
        print('   reason   : %s' % r['reason'])
    print('')
    print('ROUTING + READY-TO-FILE RECORDS (owner files each against the FIX commit; nothing is registered here):')
    for x in specs:
        print('  %-6s %s %s' % (x['owner'], x['id'], x['site']))
        print('         defect_register.py --add --commit <fix> %s' % ' '.join(
            a if a.startswith('--') else json.dumps(a) for a in x['args']))
    if abl is not None:
        print('')
        print('ABLATION (%s): L3e %s -> %s%s' % (ABLATION, abl['before'], abl['after'],
                                                '' if abl['ran'] else ' -- COULD NOT RUN: ' + abl['err']))
    print('%d scenarios: %d PASS, %d FAIL, controls %s' % (
        len(rows), verdicts.count('PASS'), verdicts.count('FAIL'),
        'FAILED' if 'CONTROL-FAIL' in verdicts else 'OK'))
    return code


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
