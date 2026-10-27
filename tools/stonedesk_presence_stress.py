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
    # ── b57: e-signature approval ──
    'E0': {'t': 'esig', 'name': 'Ruiz kitchen', 'quoteOut': 'Q-118', 'lastCalc': {'total': 12400},
           'canvas': [0, 0, 0, 255] * 4, 'customers': [{'id': 'C9', 'name': 'Ruiz kitchen'}]},
    'E1': {'t': 'esig', 'name': 'Ruiz kitchen', 'quoteOut': 'Q-118', 'lastCalc': {'total': 12400},
           'canvas': None, 'customers': [{'id': 'C9', 'name': 'Ruiz kitchen'}]},
    'E2': {'t': 'esig', 'name': 'Ruiz kitchen', 'quoteOut': 'Q-118', 'lastCalc': {'total': 12400},
           'canvas': [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0], 'customers': [{'id': 'C9', 'name': 'Ruiz kitchen'}]},
    'E3': {'t': 'esig', 'name': 'Ruiz kitchen', 'quoteOut': 'Q-200', 'estTotal': '$9,800', 'lastCalc': {'total': 3000},
           'canvas': [0, 0, 0, 255] * 4, 'customers': [{'id': 'C9', 'name': 'Ruiz kitchen'}]},
    'E4': {'t': 'esig', 'name': 'Maria Lopez', 'quoteOut': 'Q-118', 'lastCalc': {'total': 12400},
           'canvas': [0, 0, 0, 255] * 4,
           'customers': [{'id': 'C1', 'name': 'Maria Lopez'}, {'id': 'C2', 'name': 'maria lopez'}]},
    # ── b57: invoice Paid ──
    'I0': {'t': 'inv', 'mode': 'save', 'f': {'inv2-cust': 'Ruiz kitchen', 'inv2-amount': '5000', 'inv2-deposit': '5000',
                                              'inv2-method': 'Check', 'inv2-check-num': '1234'}},
    'I1': {'t': 'inv', 'mode': 'save', 'f': {'inv2-cust': 'Ruiz kitchen', 'inv2-amount': '5000', 'inv2-deposit': '6000',
                                              'inv2-method': 'Check', 'inv2-check-num': '1234'}},
    'I2': {'t': 'inv', 'mode': 'markpaid', 'storeOk': False},
    'I3': {'t': 'inv', 'mode': 'chain', 'estTotal': '$12,400', 'f': {'inv2-deposit': '6200', 'inv2-method': 'Card'}},
    # ── b57: margin ──
    'M0': {'t': 'margin', 'fn': 'calc', 'f': {'fj-quote': '10000', 'fj-slab': '3000', 'fj-hours': '10', 'fj-rate': '35',
                                               'fj-consumables': '200', 'fj-install': '500'}},
    'M1': {'t': 'margin', 'fn': 'calc', 'f': {'fj-quote': '10000', 'fj-slab': '', 'fj-hours': '10', 'fj-rate': '35',
                                               'fj-consumables': '200', 'fj-install': '500'}},
    'M2': {'t': 'margin', 'fn': 'kpis', 'quotes': [{'total': '$12,400'}, {'total': '$3,000'}]},
    'M3': {'t': 'margin', 'fn': 'kpis', 'quotes': [{'total': 12400}]},
    # ── b57: tax ──
    'X0': {'t': 'tax', 'fn': 'render', 'entries': [{'tax': 100, 'date': '2026-03-01'}], 'ap': []},
    'X1': {'t': 'tax', 'fn': 'render', 'entries': [{'tax': 100, 'date': '2026-03-01'}, {'tax': 900, 'date': '2024-05-01'}],
           'ap': []},
    'X2': {'t': 'tax', 'fn': 'add', 'f': {'tax-state': 'TX', 'tax-taxable': '1000', 'tax-rate': '825'}},
    'X3': {'t': 'tax', 'fn': 'render', 'entries': [], 'ap': [{'vendor': 'Joe Install LLC', 'amt': 5000}]},
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
                'as literals no code ever sets', lambda o: bool(o.get('literal_tiles')),
                site='stonedesk.html:10809'),
    # ── b57: esigApprove ──
    PP.Scenario('E0', 'Project Approved!', 'a drawn signature on the current quote, one matching customer', '',
                lambda o: o.get('approved') and (o.get('approval') or {}).get('totalAmt') == 12400, expect_claim=True),
    PP.Scenario('E1', 'Project Approved!', 'the signature pad is NOT ON THE PAGE, so nothing was signed',
                'the app shows Project Approved! and stores an approval whose signature is an empty string',
                lambda o: o.get('approved'), site='stonedesk.html:41700'),
    PP.Scenario('E2', 'Project Approved!', 'the pad holds ONE pixel at 1/255 alpha -- a stray touch, not a signature',
                'the app shows Project Approved! on a single near-transparent pixel',
                lambda o: o.get('approved'), site='stonedesk.html:41701'),
    PP.Scenario('E3', 'Project Approved!', 'the screen shows quote Q-200 at $9,800; lastCalc still holds a $3,000 total',
                'the app shows Project Approved! and records Q-200 at $3,000 -- one quote\'s number, another\'s price',
                lambda o: o.get('approved') and (o.get('approval') or {}).get('quoteNum') == 'Q-200'
                and (o.get('approval') or {}).get('totalAmt') == 3000, site='stonedesk.html:41717'),
    PP.Scenario('E4', 'Project Approved!', 'two customers are named Maria Lopez; nothing says which one signed',
                'the app shows Project Approved! and marks the FIRST same-named customer approved, with no choice offered',
                lambda o: o.get('approved') and sum(1 for c in o.get('customers') or [] if c[1] == 'approved') == 1,
                site='stonedesk.html:41785'),
    # ── b57: invoice Paid ──
    PP.Scenario('I0', 'Paid', '$5,000 invoice, $5,000 cheque recorded', '',
                lambda o: o.get('status') == 'Paid' and o.get('balance') == 0, expect_claim=True),
    PP.Scenario('I1', 'Paid', 'a $6,000 cheque against a $5,000 invoice: the customer is owed a $1,000 credit',
                'the invoice shows Paid with a $0 balance and nothing records the $1,000 overpayment',
                lambda o: o.get('status') == 'Paid' and o.get('balance') == 0
                and not any(k for k in (o.get('keys') or []) if 'credit' in k or 'over' in k),
                site='stonedesk.html:12123'),
    PP.Scenario('I2', 'marked as Paid', 'the store write FAILED, so the Paid status is lost on reload',
                'the app says "Invoice marked as Paid" although the save returned false',
                lambda o: any('marked as Paid' in n for n in o.get('notes') or []) and o.get('stored') is False,
                site='stonedesk.html:12157'),
    PP.Scenario('I3', 'Paid', 'a 50% DEPOSIT REQUEST invoice built from the quote; the customer has paid nothing',
                'the deposit-request invoice saves as Paid with a $6,200 payment recorded, from a deposit field left over',
                lambda o: o.get('status') == 'Paid', site='stonedesk.html:41945'),
    # ── b57: margin ──
    PP.Scenario('M0', '60%', 'all costs entered: quote 10,000, COGS 4,050', '',
                lambda o: o.get('margin') == '60%' and o.get('color') == '#16a34a', expect_claim=True),
    PP.Scenario('M1', 'green', 'the SLAB COST is blank -- the largest cost of the job is unknown',
                'the job margin shows green (40% or more) with the slab cost blank, read as $0',
                lambda o: o.get('color') == '#16a34a', site='stonedesk.html:28624'),
    PP.Scenario('M2', '65%', 'no cost has been recorded for any job',
                'the Financial margin KPI shows 65% computed from a hardcoded 35% material ratio, for any revenue',
                lambda o: o.get('kpi_margin') == '65%', site='stonedesk.html:28608'),
    PP.Scenario('M3', 'margin', 'a saved quote stores its total as a NUMBER (12400)',
                'the margin KPI never renders, a TypeError on q.total.replace, once one quote has a numeric total',
                lambda o: o.get('kpi_margin') == '65%', site='stonedesk.html:28607'),
    # ── b57: tax ──
    PP.Scenario('X0', '$100', 'one sales-tax entry this year, $100', '',
                lambda o: o.get('ytd') == '$100', expect_claim=True),
    PP.Scenario('X1', 'YTD', 'a $900 entry is from 2024, not this year',
                'the Sales tax YTD figure includes the 2024 entry ($1,000, not $100)',
                lambda o: o.get('ytd') == '$1,000', site='stonedesk.html:43341'),
    PP.Scenario('X2', 'Logged', 'a rate of 825 is 825%, a typo for 8.25',
                'the entry is Logged at 825% (tax $8,250 on $1,000) with no refusal',
                lambda o: (o.get('last') or {}).get('rate') == 825, site='stonedesk.html:43323'),
    PP.Scenario('X3', '0', '$5,000 was paid to an installer LLC; nobody checked whether a 1099 is due',
                'the 1099 tile shows 0 as a literal, whatever the payables say',
                lambda o: o.get('t1099') == '0', site='stonedesk.html:43343'),
]
SITES = {'T1a': 'api/sd-data.js:3862', 'T1b': 'api/sd-data.js:3862', 'T1d': 'api/sd-data.js:3859',
         'T1z': 'api/sd-data.js:3827', 'T2a': 'api/sd-sub-data.js:67', 'T2b': 'api/sd-sub-data.js:67',
         'T3a': 'stonedesk.html:28004', 'T3b': 'stonedesk.html:28007'}
for _s in SCENARIOS:
    if _s.sid in SITES:
        _s.site = SITES[_s.sid]
# T2 is a pair: the server status and the pill that renders it. Both owners are told.
ALSO_ROUTE = {'T2a': 'stonedesk.html:36608', 'T2b': 'stonedesk.html:36608'}
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
// ── shared stub DOM: every id resolves, `f` seeds values ──
function dom(f, missing) {
  const els = {};
  const get = (id) => {
    if ((missing || []).indexOf(id) !== -1) return null;
    if (!els[id]) els[id] = { id, value: (f && id in f) ? String(f[id]) : '', textContent: (f && id in f) ? String(f[id]) : '',
                              innerHTML: '', style: {}, scrollIntoView() {}, classList: { add() {}, remove() {} } };
    return els[id];
  };
  return { els, doc: { getElementById: get, querySelector: () => null, querySelectorAll: () => [] } };
}
function lsStub(seed) {
  const store = Object.assign({}, seed || {});
  return { getItem: (k) => (k in store ? store[k] : null), setItem: (k, v) => { store[k] = String(v); }, removeItem: (k) => { delete store[k]; } };
}
const BASE = { Date, Math, JSON, console, String, Number, isFinite, parseFloat, Array, Object, setTimeout: () => 0 };
const ESC_AT = once(HTML, 'function escHtml(s){', 'stonedesk.html');
const ESC = HTML.slice(ESC_AT, HTML.indexOf(String.fromCharCode(10), ESC_AT));
// The real one-line escapers the rendered markup calls, loaded from the file, never re-typed.
const ONE_LINE = (sig) => { const at = once(HTML, sig, 'stonedesk.html'); return HTML.slice(at, HTML.indexOf(String.fromCharCode(10), at)); };
const ESCAPERS = [ONE_LINE('function escHtml(s){'), (() => { const at = once(HTML, 'function jsStr(v){', 'stonedesk.html'); return HTML.slice(at, HTML.indexOf(String.fromCharCode(10) + '}', at) + 2); })(),
                  ONE_LINE('function escAttrJs(v){')].join(String.fromCharCode(10));
function mkctx(ctx) { vm.createContext(ctx); vm.runInContext(ESCAPERS, ctx); return ctx; }
// ── T5: esigApprove ──
const ESIG = grabFn(HTML, 'function esigApprove(){', 'stonedesk.html');
function esig(o) {
  const d = dom({ 'esig-name': o.name, 'esig-date': '2026-10-27', 'est-quote-out': o.quoteOut, 'est-total': o.estTotal || '' },
                o.canvas ? [] : ['esig-canvas']);
  if (o.canvas) d.els['esig-canvas'] = { width: o.canvas.length / 4, height: 1,
    getContext: () => ({ getImageData: () => ({ data: o.canvas }) }), toDataURL: () => 'data:image/png;base64,SIG' };
  const toasts = [];
  const ctx = Object.assign({}, BASE, { document: d.doc, localStorage: lsStub(), sdLocalToday: () => '2026-10-27',
    showToast: (m) => toasts.push(String(m)), lastCalc: o.lastCalc, _sdApprovals: [],
    sdApprovalsSaveLocal: () => true, sdApprovalsRender: () => {}, sdApprovalSync: () => {},
    sdCustomers: o.customers, saveSD3Data: () => {} });
  mkctx(ctx);
  vm.runInContext(ESIG + '\nesigApprove();', ctx);
  const a = ctx._sdApprovals[0] || null;
  return { approved: /Project Approved!/.test(d.els['est-esig-block'] ? d.els['est-esig-block'].innerHTML : ''),
           approval: a ? { quoteNum: a.quoteNum, totalAmt: a.totalAmt, sig: a.sigDataUrl } : null,
           customers: (ctx.sdCustomers || []).map((c) => [c.id, c.status || null]), toasts };
}
// ── T6: invoices ──
const INVFN = ['function invSave() {', 'function invMarkPaid(id) {', 'function esigCreateInvoice(clientName){']
  .map((s) => grabFn(HTML, s, 'stonedesk.html')).join('\n');
function inv(o) {
  const d = dom(Object.assign({ 'est-total': o.estTotal || '', 'est-quote-out': 'Q-118' }, o.f || {}));
  const notes = [];
  let stored = null;
  const ctx = Object.assign({}, BASE, { document: d.doc, notify: (m) => notes.push(String(m)), showToast: (m) => notes.push(String(m)),
    sd_invoices: o.mode === 'markpaid' ? [{ id: 'I1', num: 'INV-1', amount: 5000, balance: 5000, status: 'Unpaid', payments: [] }] : [],
    invSaveStore: () => (stored = o.storeOk !== false), invGenNum: () => 'INV-1001', invUpdateKPIs: () => {}, invRender: () => {},
    sdLocalToday: () => '2026-10-27', sbNav: () => {} });
  mkctx(ctx);
  vm.runInContext(INVFN, ctx);
  if (o.mode === 'save') ctx.invSave();
  else if (o.mode === 'chain') { ctx.esigCreateInvoice('Ruiz kitchen'); ctx.invSave(); }
  else ctx.invMarkPaid('I1');
  const i = ctx.sd_invoices[0] || {};
  return { status: i.status, balance: i.balance, amount: i.amount, deposit: i.deposit, payments: i.payments,
           keys: Object.keys(i).map((k) => k.toLowerCase()), notes, stored };
}
// ── T7: margin ──
const MARGIN = ['function finUpdateKPIs(){', 'function finCalcMargin(){'].map((s) => grabFn(HTML, s, 'stonedesk.html')).join('\n');
function margin(o) {
  const d = dom(o.f || {});
  const ctx = Object.assign({}, BASE, { document: d.doc,
    localStorage: lsStub({ stonedesk_quote_history: JSON.stringify(o.quotes || []) }) });
  mkctx(ctx);
  vm.runInContext(MARGIN, ctx);
  if (o.fn === 'calc') { ctx.finCalcMargin(); const m = d.els['fj-live-margin'] || {}; return { margin: m.textContent, color: m.style.color }; }
  ctx.finUpdateKPIs();
  return { kpi_margin: (d.els['fin-kpi-margin'] || {}).textContent };
}
// ── T8: tax ──
const TAX = ['function taxAddEntry(){', 'function taxRender(){'].map((s) => grabFn(HTML, s, 'stonedesk.html')).join('\n');
function tax(o) {
  const d = dom(o.f || {});
  const ctx = Object.assign({}, BASE, { document: d.doc, taxEntries: o.entries || [], sd_invoices: [],
    localStorage: lsStub({ sd_ap: JSON.stringify(o.ap || []) }), sdStore: () => true, showToast: () => {},
    sdLocalToday: () => '2026-10-27', sdFmt: (n) => '$' + Math.round(n).toLocaleString('en-US'), confirm: () => true });
  mkctx(ctx);
  vm.runInContext(TAX, ctx);
  if (o.fn === 'add') { ctx.taxRender = () => {}; ctx.taxAddEntry(); return { last: ctx.taxEntries[ctx.taxEntries.length - 1] || null }; }
  ctx.taxRender();
  return { ytd: (d.els['tax-ytd'] || {}).textContent, t1099: (d.els['tax-1099'] || {}).textContent };
}
(async () => {
  const out = {};
  for (const [id, inp] of Object.entries(INPUTS)) {
    try {
      if (inp.t === 'approvals') out[id] = await approvals(inp.payload);
      else if (inp.t === 'pill') out[id] = pill(inp.row);
      else if (inp.t === 'safety') out[id] = safety(inp.data);
      else if (inp.t === 'esig') out[id] = esig(inp);
      else if (inp.t === 'inv') out[id] = inv(inp);
      else if (inp.t === 'margin') out[id] = margin(inp);
      else if (inp.t === 'tax') out[id] = tax(inp);
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
    # ── ROUTE, NEVER SELF-REGISTER (checklist item ROUTE, cc b57) ──────────
    # Every FAIL goes to the owner of its SITE, read from the path manifest.
    # This tool writes NOTHING to docs/defect-density-register.json; a finding
    # in a file cc owns would be the only one cc may file, and it is marked.
    routes = []
    for r in rows:
        if r['verdict'] != 'FAIL':
            continue
        s = [x for x in SCENARIOS if x.sid == r['id']][0]
        for site in [s.site] + ([ALSO_ROUTE[s.sid]] if s.sid in ALSO_ROUTE else []):
            owner = PP.route(site, REPO)
            routes.append({'id': r['id'], 'site': site, 'owner': owner,
                           'self_register': PP.may_self_register(site, 'cc', REPO)})
    for r in rows:
        r['routes'] = [x for x in routes if x['id'] == r['id']]
    verdicts = [r['verdict'] for r in rows]
    code = 2 if 'CONTROL-FAIL' in verdicts else (1 if 'FAIL' in verdicts else 0)
    if any(x['owner'] is None for x in routes):
        code = 2                       # a FAIL nobody owns cannot be routed
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
    print('ROUTING (owner from %s; nothing here is self-registered):' % PP.MANIFEST)
    by_owner = {}
    for x in routes:
        by_owner.setdefault(x['owner'] or 'UNOWNED', []).append('%s %s%s' % (
            x['id'], x['site'], ' [cc may register]' if x['self_register'] else ''))
    for owner in sorted(by_owner):
        print('  %-7s %s' % (owner, '; '.join(by_owner[owner])))
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
