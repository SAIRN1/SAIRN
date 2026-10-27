#!/usr/bin/env python3
# OWNER: cc
"""StoneDesk money / legal / compliance -- PRESENCE PASSED AS PROOF stress test.

    python tools/stonedesk_presence_stress.py           # every scenario, printed
    python tools/stonedesk_presence_stress.py --json
    python tools/stonedesk_presence_stress.py --ablate  # also run the named ablation

Exit 0 no false positive shown; 1 at least one; 2 COULD NOT RUN (the plan
fails tools/presence_proof.py's checklist, node is missing, a function is not
found exactly once, or a CONTROL fails).

SCOPE -- what is REAL and what is STUBBED, per target:
  T1 sd_approvals write: REAL api/sd-data.js handler, the `write` action.
     STUBBED: the licence, the session token, the employee-auth lookup (an
     active row) and the Supabase write (records what would be stored).
  T2 subcontractor compliance pill: REAL complianceStatus() text from
     api/sd-sub-data.js and REAL subxCompliancePill() from stonedesk.html, run
     together in a vm, as the roster renders them.
  T3 safety compliance score: REAL safetyUpdateKPIs() from stonedesk.html in
     a vm. sdSafetyData is the scenario; document is a stub that records what
     each tile was set to.
  T4 silica monitoring tiles: REAL stonedesk.html markup, read statically.
Nothing in the app is edited. Each scenario's FAIL MEANS is written down
before it is driven, and the plan is refused if any is missing.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import presence_proof as PP                                         # noqa: E402

CRITERIA_VERSION = '2026-10-27.1'
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PNG_1PX = ('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk'
           '+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==')
GOOD = {'approval_id': 'APPR-STRESS-1', 'client_name': 'Ruiz kitchen', 'quote_num': 'Q-118',
        'signed_date': '2026-10-27', 'total_amount': 12400, 'deposit_amount': 6200,
        'signature_png': PNG_1PX}


def _a(**chg):
    d = dict(GOOD)
    d.update(chg)
    return d


# Every scenario's input, keyed by id, handed to the node harness.
INPUTS = {
    'T1c': {'t': 'approvals', 'payload': GOOD},
    'T1a': {'t': 'approvals', 'payload': _a(signature_png=None)},
    'T1b': {'t': 'approvals', 'payload': _a(signature_png='data:image/png;base64,AAAA')},
    'T1d': {'t': 'approvals', 'payload': _a(deposit_status='paid')},
    'T1z': {'t': 'approvals', 'payload': _a(total_amount=0, deposit_amount=0)},
    'T2c': {'t': 'pill', 'row': {'coi_expiry': '2027-06-01', 'licence_expiry': '2027-06-01', 'w9_on_file': True}},
    'T2a': {'t': 'pill', 'row': {'coi_expiry': '2027-06-01', 'licence_expiry': None, 'w9_on_file': False}},
    'T2b': {'t': 'pill', 'row': {'coi_expiry': None, 'licence_expiry': '2027-06-01', 'w9_on_file': True}},
    'T3c': {'t': 'safety', 'data': {'training': [{'type': 'silica_annual', 'date': '2026-09-01', 'expiry': '2027-09-01'}],
                                    'incidents': [], 'inspections': [], 'ecp': {'owner': 'Dana Ortiz'}}},
    'T3a': {'t': 'safety', 'data': {'training': [], 'incidents': [], 'inspections': [], 'ecp': {}}},
    'T3b': {'t': 'safety', 'data': {'training': [{'type': 'silica_annual', 'date': '2019-01-01', 'expiry': ''}],
                                    'incidents': [], 'inspections': [], 'ecp': {'owner': 'Dana Ortiz'}}},
    'T4a': {'t': 'silica'},
}

stored = lambda o: bool(o.get('stored'))                            # noqa: E731
GREEN = '#15803d'
SCENARIOS = [
    PP.Scenario('T1c', 'Signed', 'a priced, deposited approval with a real PNG signature',
                '', stored, expect_claim=True),
    PP.Scenario('T1a', 'Signed', 'the record carries NO signature image at all',
                'the server stores it as a signed approval (listed "Signed <date>") with signature_png null',
                stored),
    PP.Scenario('T1b', 'Signed', "the signature is 'AAAA', which is not an image",
                'the server stores it as a signed approval with an undecodable signature', stored),
    PP.Scenario('T1d', 'paid', 'no payment exists anywhere; the client simply sent deposit_status "paid"',
                'the server stores deposit_status "paid" and the approvals list displays it verbatim (paid with no payment)',
                lambda o: o.get('stored') and (o.get('row') or {}).get('deposit_status') == 'paid'),
    PP.Scenario('T1z', 'Signed', 'a $0 approval, which the branch exists to refuse',
                'the server stores a Signed $0 approval', stored),
    PP.Scenario('T2c', 'COMPLIANT', 'COI and licence both valid, W-9 on file', '',
                lambda o: 'COMPLIANT' in (o.get('html') or '') and 'NOT TRACKED' not in o['html'],
                expect_claim=True),
    PP.Scenario('T2a', 'COMPLIANT', 'NO licence on record and NO W-9 -- only an insurance date',
                'the roster shows a green COMPLIANT for a sub with no licence and no W-9',
                lambda o: '>COMPLIANT<' in (o.get('html') or '')),
    PP.Scenario('T2b', 'COMPLIANT', 'NO certificate of insurance on record -- only a licence date',
                'the roster shows a green COMPLIANT for an uninsured sub',
                lambda o: '>COMPLIANT<' in (o.get('html') or '')),
    PP.Scenario('T3c', '100%', 'current silica training, an exposure-control-plan owner, nothing overdue',
                '', lambda o: o.get('kpi4') == '100%' and o.get('kpi4_color') == GREEN, expect_claim=True),
    PP.Scenario('T3a', 'green', 'an EMPTY safety record: no training, no ECP owner, no inspections, nothing logged',
                'the compliance score shows green (80% or more) for a shop with nothing on file',
                lambda o: o.get('kpi4_color') == GREEN),
    PP.Scenario('T3b', 'green', 'the only silica training is from 2019 with NO expiry recorded',
                'the compliance score shows green 100% on 2019 training whose expiry was never entered',
                lambda o: o.get('kpi4_color') == GREEN and o.get('kpi4') == '100%'),
    PP.Scenario('T4a', 'Dry Cut Violations', 'no exposure data is read anywhere -- the tile values are markup',
                'the OSHA 1926.1153 panel shows "0 Dry Cut Violations", "12" wet-cut days and "8 Air Samples" '
                'as literals no code ever sets', lambda o: bool(o.get('literal_tiles'))),
]
ABLATION = ("Compile api/sd-data.js with the `total <= 0` refusal removed: T1z must turn PASS -> FAIL "
            "(run with --ablate).")

HARNESS = r"""
const fs = require('fs'), path = require('path'), vm = require('vm'), Module = require('module');
const REPO = process.argv[2], INPUTS = JSON.parse(process.argv[3]), ABLATE = process.argv[4] === '1';
const API = path.join(REPO, 'api');
const HTML = fs.readFileSync(path.join(REPO, 'stonedesk.html'), 'utf8');
function once(src, sig, what) {
  const i = src.indexOf(sig);
  if (i < 0 || src.indexOf(sig, i + 1) !== -1) throw new Error('NOT EXACTLY ONCE in ' + what + ': ' + sig);
  return i;
}
function grabFn(src, sig, what) {
  const start = once(src, sig, what);
  let i = src.indexOf('{', start + sig.length - 1), depth = 0, q = null;
  for (; i < src.length; i++) {
    const c = src[i], p = src[i - 1];
    if (q) { if (c === q && p !== '\\') q = null; continue; }
    if (c === '"' || c === "'" || c === '`') { q = c; continue; }
    if (c === '/' && src[i + 1] === '/') { i = src.indexOf('\n', i); continue; }
    if (c === '/' && src[i + 1] === '*') { i = src.indexOf('*/', i) + 1; continue; }
    if (c === '{') depth++;
    else if (c === '}') { depth--; if (!depth) return src.slice(start, i + 1); }
  }
  throw new Error('UNTERMINATED: ' + sig);
}
function stub(rel, exp) {
  const p = require.resolve(path.join(API, rel));
  const m = new Module(p); m.filename = p; m.loaded = true; m.exports = exp; require.cache[p] = m;
}
// ── T1: the real sd-data.js handler ──
let handler = null, lastWrite = null;
function loadSdData() {
  stub('_lib/license', { validateLicenseKey: async () => ({ valid: true, active: true, license_hash: 'LH-STRESS',
                                                             app_id: 'stonedesk', trial_ends_at: null }) });
  const realAuth = require(path.join(API, '_lib', 'auth'));
  stub('_lib/auth', Object.assign({}, realAuth, { tokenFromRequest: () => 'tok',
    verifySessionToken: () => ({ employee_id: 'emp-7', role: 'sales' }) }));
  global.fetch = async (url, init) => {
    const method = (init && init.method) || 'GET';
    if (method === 'GET') {
      const rows = /employee_auth|_employee_auth/.test(String(url)) ? [{ employee_id: 'emp-7', active: true, role: 'sales' }] : [];
      return { ok: true, status: 200, json: async () => rows };
    }
    lastWrite = init && init.body ? JSON.parse(init.body) : null;
    return { ok: true, status: 201, json: async () => [Array.isArray(lastWrite) ? lastWrite[0] : lastWrite] };
  };
  process.env.SUPABASE_URL = 'https://sb.invalid'; process.env.SUPABASE_SERVICE_ROLE_KEY = 'stress';
  const p = path.join(API, 'sd-data.js');
  let src = fs.readFileSync(p, 'utf8');
  if (ABLATE) {
    const anchor = "if (!isFinite(total) || total <= 0) {";
    once(src, anchor, 'sd-data.js');
    src = src.replace(anchor, 'if (!isFinite(total)) {');
  }
  const m = new Module(p, module); m.filename = p; m.paths = Module._nodeModulePaths(API);
  m._compile(src, p);
  handler = m.exports;
}
async function approvals(payload) {
  if (!handler) loadSdData();
  lastWrite = null;
  let status = 0, body = null;
  const res = { status(s) { status = s; return this; }, json(b) { body = b; return this; }, setHeader() {}, end() {} };
  await handler({ method: 'POST', headers: { authorization: 'Bearer SD-STRESS', 'x-sd-auth': 'tok' },
                  body: { action: 'write', resource: 'sd_approvals', payload } }, res);
  const row = Array.isArray(lastWrite) ? lastWrite[0] : lastWrite;
  return { http: status, stored: status >= 200 && status < 300 && !!row, row,
           err: body && body.error ? body.error.code : null };
}
// ── T2: complianceStatus (server text) + subxCompliancePill (client) ──
const SUB = fs.readFileSync(path.join(API, 'sd-sub-data.js'), 'utf8');
const pillCtx = { escHtml: null, _subxCompliance: true, EXPIRING_SOON_DAYS: 30, Date, String };
vm.createContext(pillCtx);
vm.runInContext("const EXPIRING_SOON_DAYS = 30;\n" + grabFn(SUB, 'function complianceStatus(row, todayISO) {', 'sd-sub-data.js'), pillCtx);
vm.runInContext(HTML.slice(once(HTML, 'function escHtml(s){', 'stonedesk.html'), HTML.indexOf('\n', once(HTML, 'function escHtml(s){', 'stonedesk.html'))), pillCtx);
vm.runInContext('var _subxCompliance = true;\n' + grabFn(HTML, 'function subxCompliancePill(s){', 'stonedesk.html'), pillCtx);
function pill(row) {
  const c = pillCtx.complianceStatus(row, '2026-10-27');
  return { compliance: c, html: pillCtx.subxCompliancePill({ compliance: c }) };
}
// ── T3: safetyUpdateKPIs ──
const SAFE = grabFn(HTML, 'function safetyUpdateKPIs() {', 'stonedesk.html');
function safety(data) {
  const els = {};
  const doc = { getElementById: (id) => (els[id] = els[id] || { textContent: '', style: {}, innerHTML: '' }) };
  const ctx = { document: doc, sdSafetyData: data, Date, Math, console };
  vm.createContext(ctx);
  vm.runInContext(SAFE + '\nsafetyUpdateKPIs();', ctx);
  const k = els['safe-kpi4'] || {};
  return { kpi4: String(k.textContent), kpi4_color: k.style.color, kpi1: String((els['safe-kpi1'] || {}).textContent) };
}
// ── T4: the silica tiles, statically ──
function silica() {
  const at = once(HTML, 'Silica Exposure Monitoring (OSHA 1926.1153)', 'stonedesk.html');
  const block = HTML.slice(at, HTML.indexOf('PPE Checklist', at));
  const tiles = [...block.matchAll(/<div style="font-size:20px;font-weight:800;color:var\(--brand2\)"( id="[^"]+")?>([^<]*)<\/div><div[^>]*>([^<]*)</g)];
  const literal = tiles.filter((t) => !t[1]).map((t) => t[2] + ' ' + t[3]);
  return { literal_tiles: literal, tiles: tiles.length };
}
(async () => {
  const out = {};
  for (const [id, inp] of Object.entries(INPUTS)) {
    try {
      if (inp.t === 'approvals') out[id] = await approvals(inp.payload);
      else if (inp.t === 'pill') out[id] = pill(inp.row);
      else if (inp.t === 'safety') out[id] = safety(inp.data);
      else out[id] = silica();
    } catch (e) { out[id] = { crash: String(e && e.message || e).slice(0, 200) }; }
  }
  process.stdout.write(JSON.stringify({ ok: true, out }));
})().catch((e) => process.stdout.write(JSON.stringify({ ok: false, err: String(e && e.stack || e) })));
"""


def drive(ablate=False):
    node = shutil.which('node')
    if not node:
        return None, 'node is not on PATH'
    d = tempfile.mkdtemp(prefix='sd-presence-')
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
    PP.require_plan(SCENARIOS, ABLATION, __doc__)
    out, err = drive()
    if out is None:
        print('COULD NOT RUN: %s' % err)
        return 2
    rows = []
    for s in SCENARIOS:
        v, why = PP.verdict(s, out.get(s.sid, {'crash': 'no observation'}))
        rows.append({'id': s.sid, 'claim': s.claim, 'truth': s.truth, 'verdict': v, 'reason': why,
                     'input': INPUTS[s.sid], 'observed': out.get(s.sid)})
    abl = None
    if '--ablate' in argv:
        o2, e2 = drive(ablate=True)
        z = [s for s in SCENARIOS if s.sid == 'T1z'][0]
        abl = {'ran': o2 is not None, 'err': e2,
               'before': [r['verdict'] for r in rows if r['id'] == 'T1z'][0],
               'after': PP.verdict(z, o2['T1z'])[0] if o2 else None}
    verdicts = [r['verdict'] for r in rows]
    code = 2 if 'CONTROL-FAIL' in verdicts else (1 if 'FAIL' in verdicts else 0)
    if abl is not None and not (abl['ran'] and abl['before'] == 'PASS' and abl['after'] == 'FAIL'):
        code = 2
    if as_json:
        print(json.dumps({'criteria': CRITERIA_VERSION, 'rows': rows, 'ablation': abl, 'exit': code}, indent=1))
        return code
    print('STONEDESK PRESENCE STRESS -- criteria %s; plan accepted by tools/presence_proof.py' % CRITERIA_VERSION)
    for r in rows:
        print('')
        print('%-12s %s  claim %r' % (r['verdict'], r['id'], r['claim']))
        print('   truth    : %s' % r['truth'])
        print('   input    : %s' % json.dumps(r['input'])[:300])
        obs = dict(r['observed'] or {})
        obs.pop('row', None)
        if 'html' in obs:
            obs['html'] = re.sub(r'<[^>]+>', '', obs['html'])
        print('   observed : %s' % json.dumps(obs)[:300])
        print('   reason   : %s' % r['reason'])
    print('')
    if abl is not None:
        print('ABLATION (%s): T1z %s -> %s%s' % (ABLATION, abl['before'], abl['after'],
                                                '' if abl['ran'] else ' -- COULD NOT RUN: ' + abl['err']))
    print('%d scenarios: %d PASS, %d FAIL, controls %s'
          % (len(rows), verdicts.count('PASS'), verdicts.count('FAIL'),
             'FAILED' if 'CONTROL-FAIL' in verdicts else 'OK'))
    return code


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
