#!/usr/bin/env python3
"""SAIRNlaw citator adversarial stress test -- fabricated and altered citations.

    python tools/sairnlaw_citator_stress.py            # run the corpus, print every row
    python tools/sairnlaw_citator_stress.py --json     # machine-readable
    python tools/sairnlaw_citator_stress.py --fixtures # criteria lock only

Exit 0 every corpus item is rejected or flagged; 1 at least one is presented
as real or is not shown at all; 2 COULD NOT RUN (node missing, a function not
found in its file, or a CONTROL failing -- a harness whose control fails has
tested nothing, PR 1.11).

WHAT IS REAL AND WHAT IS A FIXTURE, stated rather than implied:
  REAL   api/legal-citator.js's handler, `verify` action, required as-is.
  REAL   sairnlaw.html's mtExtractCitations, MT_CITE_PATTERNS,
         mtVerifyCitations and lawCiteGuard, extracted by signature and run in
         a vm, with citatorFetch wired straight to that handler.
  FIXTURE  what CourtListener answers. The upstream is stubbed, with one
         declared answer per citation (UPSTREAM below). This tests what the
         app DOES with each answer. It does not test what CourtListener knows,
         and a citation listed here as fabricated is fabricated BY
         CONSTRUCTION of the fixture. Several are the real fabrications from
         Mata v. Avianca (S.D.N.Y. 2023), so that the shape is the one that
         ended in sanctions.
  STUB   license, session, audit and the cl_case_cache table (an empty
         cache, so that every citation reaches the upstream).

THE PASS RULE (CRITERIA_VERSION): an item passes only if no layer presents it
as real. On the client, it must also be SHOWN, flagged in the guard box. A
citation the extractor never sees is not checked and not shown, so it reaches
the user silently. That is a FAIL, not a pass, because "never silently cited
as real" is the requirement.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

CRITERIA_VERSION = '2026-10-23.1'
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BRADY = {'id': 106, 'case_name': 'Brady v. Maryland', 'court': 'scotus',
         'date_filed': '1963-05-13', 'absolute_url': '/opinion/106/brady-v-maryland/'}
ROE = {'id': 108713, 'case_name': 'Roe v. Wade', 'court': 'scotus',
       'date_filed': '1973-01-22', 'absolute_url': '/opinion/108713/roe-v-wade/'}
MIRANDA = {'id': 107252, 'case_name': 'Miranda v. Arizona', 'court': 'scotus',
           'date_filed': '1966-06-13', 'absolute_url': '/opinion/107252/miranda-v-arizona/'}
BROWN = {'id': 105221, 'case_name': 'Brown v. Board of Education', 'court': 'scotus',
         'date_filed': '1954-05-17', 'absolute_url': '/opinion/105221/brown-v-board/'}

# The fixture upstream, keyed by the REPORTER CITATION TEXT that CourtListener's
# /citation-lookup/ would find in the submitted text. A citation that is not a
# key is one the upstream does not mention at all.
UPSTREAM = {
    '373 U.S. 83': (200, [BRADY]),
    '410 U.S. 113': (200, [ROE]),
    '384 U.S. 436': (200, [MIRANDA]),
    '347 U.S. 483': (200, [BROWN]),
    '347 U.S. 484': (404, []),
    '925 F.3d 1339': (404, []),
    '905 F. Supp. 2d 121': (404, []),
    '47 U.S. 483': (404, []),
    '999 U.S. 9999': (404, []),
}

# kind: F fabricated, A real but altered, X key-matching collision,
# C control (must come back VERIFIED or the harness proves nothing).
# layer: 'client' = drafted text through lawCiteGuard, end to end; 'api' = a
# direct verify call with this exact citation string (the API accepts free
# text).
CORPUS = [
    ('F1', 'F', 'client', 'Varghese v. China Southern Airlines Co., 925 F.3d 1339 (11th Cir. 2019)',
     'a real Mata v. Avianca fabrication, in reporter form'),
    ('F2', 'F', 'client', 'Petersen v. Iran Air, 905 F. Supp. 2d 121 (D.D.C. 2012)',
     'a Mata fabrication, F. Supp. 2d form'),
    ('F3', 'F', 'client', 'Shaboon v. Egyptair, 2013 IL App (1st) 111279-U',
     'a Mata fabrication in a PUBLIC-DOMAIN citation form, with no reporter'),
    ('F4', 'F', 'client', 'Martinez v. Delta Airlines, Inc., 2019 WL 4639462 (Tex. App. 2019)',
     'a Mata fabrication in WESTLAW form'),
    ('F5', 'F', 'client', 'Durden v. KLM Royal Dutch Airlines',
     'a Mata case NAME cited with no citation at all'),
    ('F6', 'F', 'client', 'Holloway v. Tranquil Systems, 999 U.S. 9999 (2031)',
     'an impossible volume, page and year'),
    ('A1', 'A', 'client', 'Brady v. Maryland, 373 U.S. 83 (9th Cir. 1963)',
     'a real citation with the WRONG COURT'),
    ('A2', 'A', 'client', 'Roe v. Smith, 410 U.S. 113 (1973)',
     'a real reporter citation with the WRONG CASE NAME'),
    ('A3', 'A', 'client', 'Miranda v. Arizona, 384 U.S. 436 (1966) (holding that a warrantless '
     'search of a parked car is always permitted)',
     'a real citation with an INVENTED HOLDING'),
    ('A4', 'A', 'client', 'Brown v. Board of Education, 347 U.S. 484 (1954)',
     'a real case with an off-by-one PAGE'),
    ('A5', 'F', 'client', 'SEVENTH:Varghese v. China Southern Airlines Co., 925 F.3d 1339 (11th Cir. 2019)',
     'a fabrication placed SEVENTH, after six real citations in the same draft'),
    ('X1', 'X', 'api', ['47 U.S. 483', 'Brown v. Board of Education, 347 U.S. 483 (1954)'],
     'a fabricated citation that is a SUBSTRING of a real one, sent before it in one batch'),
    ('C1', 'C', 'client', 'Brady v. Maryland, 373 U.S. 83 (1963)',
     'CONTROL: a correct citation must come back verified'),
]

HARNESS = r"""
const fs = require('fs'), path = require('path'), vm = require('vm'), Module = require('module');
const REPO = process.argv[2];
const UPSTREAM = JSON.parse(process.argv[3]);
const CORPUS = JSON.parse(process.argv[4]);
const API = path.join(REPO, 'api');
function stub(rel, exp) {
  const p = require.resolve(path.join(API, rel));
  const m = new Module(p); m.filename = p; m.loaded = true; m.exports = exp;
  require.cache[p] = m;
}
const RX = /\b\d{1,4}\s+(?:U\.?\s?S\.?|S\.\s?Ct\.|F\.\s?(?:2d|3d|4th|Supp\.?(?:\s?2d|\s?3d)?)|[A-Z][a-z]?\.(?:\s?(?:2d|3d))?)\s+\d{1,4}\b/g;
let upstreamCalls = 0;
stub('_lib/license', { validateLicenseKey: async () => ({ valid: true, active: true, app_id: 'sairnlaw', license_hash: 'LH-STRESS' }) });
stub('_lib/auth', { tokenFromRequest: () => null, verifySessionToken: () => null });
stub('_lib/audit', { writeAuditLog: async () => ({}) });
stub('_lib/courtlistener', {
  sbClient: () => ({ rest: (q) => 'https://sb.invalid/rest/v1/' + q, headers: {} }),
  remainingBudget: async () => ({ minute: 5, hour: 50, day: 125 }),
  clCitationLookup: async (text) => {
    upstreamCalls++;
    const out = [];
    RX.lastIndex = 0; let m;
    while ((m = RX.exec(text)) !== null) {
      const c = m[0].replace(/\s+/g, ' ').trim();
      if (UPSTREAM[c]) out.push({ citation: c, status: UPSTREAM[c][0], clusters: UPSTREAM[c][1] });
    }
    return out;
  },
});
global.fetch = async (url, init) => {
  if (String(url).indexOf('cl_case_cache') !== -1 && (!init || !init.method || init.method === 'GET'))
    return { ok: true, status: 200, json: async () => [] };
  return { ok: true, status: 201, json: async () => ({}) };
};
process.env.COURTLISTENER_API_TOKEN = 'stress-fixture';
process.env.SUPABASE_URL = 'https://sb.invalid';
process.env.SUPABASE_SERVICE_ROLE_KEY = 'stress-fixture';
const handler = require(path.join(API, 'legal-citator.js'));
async function verify(citations) {
  let status = 0, body = null;
  const res = { status(s) { status = s; return this; }, json(b) { body = b; return this; },
                setHeader() {}, end() {} };
  await handler({ method: 'POST', headers: { authorization: 'Bearer LIC-STRESS' },
                  body: { action: 'verify', citations } }, res);
  return { status, body };
}
// ── client functions, extracted by signature from sairnlaw.html ──
const HTML = fs.readFileSync(path.join(REPO, 'sairnlaw.html'), 'utf8');
function grabFn(sig) {
  const start = HTML.indexOf(sig);
  if (start < 0) throw new Error('NOT FOUND: ' + sig);
  if (HTML.indexOf(sig, start + 1) !== -1) throw new Error('FOUND TWICE: ' + sig);
  let i = HTML.indexOf('{', start + sig.length - 1), depth = 0, q = null;
  for (; i < HTML.length; i++) {
    const c = HTML[i], p = HTML[i - 1];
    if (q) { if (c === q && p !== '\\') q = null; continue; }
    if (c === '"' || c === "'" || c === '`') { q = c; continue; }
    if (c === '/' && HTML[i + 1] === '/') { i = HTML.indexOf('\n', i); continue; }
    if (c === '/' && HTML[i + 1] === '*') { i = HTML.indexOf('*/', i) + 1; continue; }
    if (c === '{') depth++;
    else if (c === '}') { depth--; if (!depth) return HTML.slice(start, i + 1); }
  }
  throw new Error('UNTERMINATED: ' + sig);
}
function grabLine(sig) {
  const s = HTML.indexOf(sig);
  if (s < 0 || HTML.indexOf(sig, s + 1) !== -1) throw new Error('NOT EXACTLY ONCE: ' + sig);
  return HTML.slice(s, HTML.indexOf('\n', s));
}
function grabArray(sig) {
  const s = HTML.indexOf(sig);
  if (s < 0 || HTML.indexOf(sig, s + 1) !== -1) throw new Error('NOT EXACTLY ONCE: ' + sig);
  return HTML.slice(s, HTML.indexOf('\n];', s) + 3);
}
const ctx = { console, Promise, String, JSON };
ctx.citatorFetch = async (action, payload) => (await verify(payload.citations)).body;
ctx.document = { createElement: () => ({ style: {}, innerHTML: '', className: '', parentNode: null }) };
vm.createContext(ctx);
vm.runInContext(grabLine('function H(s){'), ctx);
vm.runInContext(grabArray('var MT_CITE_PATTERNS = ['), ctx);
for (const sig of ['function mtExtractCitations(text) {', 'function mtVerifyCitations(cites) {',
                   'function lawCiteGuard(text, host, label) {']) vm.runInContext(grabFn(sig), ctx);
async function guard(text) {
  const host = { kids: [], querySelector: () => null,
                 appendChild(b) { b.parentNode = host; host.kids.push(b); } };
  const n = ctx.lawCiteGuard(text, host, 'AI draft');
  for (let k = 0; k < 20; k++) await new Promise((r) => setImmediate(r));
  return { extracted: n, html: host.kids.length ? host.kids[0].innerHTML : '' };
}
(async () => {
  const rows = [];
  for (const [id, kind, layer, input, why] of CORPUS) {
    const row = { id, kind, layer, input, why };
    if (layer === 'api') {
      const r = await verify(input);
      row.http = r.status; row.results = (r.body && r.body.results) || [];
    } else {
      let text = input, target = input;
      if (input.startsWith('SEVENTH:')) {
        target = input.slice(8);
        // Six DISTINCT real reporter citations first, so the fabrication is
        // the seventh extracted.
        text = ['Brady v. Maryland, 373 U.S. 83', 'Roe v. Wade, 410 U.S. 113',
                'Miranda v. Arizona, 384 U.S. 436', 'Brown v. Board, 347 U.S. 483',
                'Gideon v. Wainwright, 372 U.S. 335', 'Mapp v. Ohio, 367 U.S. 643',
                target].join('. ') + '.';
      }
      const extracted = ctx.mtExtractCitations(target);
      const g = await guard('The court should rule for us. See ' + text + '.');
      row.extracted = extracted;
      row.guard_html = g.html;
      row.results = extracted.length ? (await verify(extracted)).body.results : [];
    }
    rows.push(row);
  }
  process.stdout.write(JSON.stringify({ ok: true, upstream_calls: upstreamCalls, rows }));
})().catch((e) => { process.stdout.write(JSON.stringify({ ok: false, err: String(e && e.stack || e) })); });
"""


def classify(row):
    """-> (verdict, reason). verdict in PASS / FAIL / CONTROL-OK / CONTROL-FAIL."""
    states = [r.get('state') for r in row.get('results') or []]
    kind = row['kind']
    if kind == 'C':
        if states and all(s == 'verified' for s in states):
            return 'CONTROL-OK', 'a correct citation is verified'
        return 'CONTROL-FAIL', 'a correct citation was NOT verified (%s)' % states
    if kind == 'X':
        bad = [r for r in row.get('results') or []
               if r.get('state') == 'verified' and r.get('citation') == row['input'][0]]
        if bad:
            return 'FAIL', ('the FABRICATED %r came back verified as %r' %
                            (row['input'][0], bad[0].get('case_name')))
        return 'PASS', 'the fabricated citation is not verified'
    if row['layer'] == 'client':
        if not row.get('extracted'):
            return 'FAIL', ('NOT EXTRACTED: the guard never sees it, so it is neither '
                            'checked nor shown -- it reaches the user silently')
        target = row['extracted'][-1]
        shown = ('<code>%s</code>' % target) in (row.get('guard_html') or '')
        if not shown:
            return 'FAIL', ('extracted as %r but NOT SHOWN in the guard box -- '
                            'dropped silently' % target)
    if 'verified' in states:
        r = [x for x in row['results'] if x.get('state') == 'verified'][0]
        return 'FAIL', ('presented as REAL: verified as %r. The citator checks that '
                        'a case exists at this reporter cite, not that the name, '
                        'court or holding is right' % r.get('case_name'))
    return 'PASS', 'flagged: %s' % ', '.join(sorted(set(states)))


FIXTURES = [
    ({'kind': 'F', 'layer': 'client', 'extracted': [], 'results': []}, 'FAIL',
     'an unextracted fabrication is a FAIL, never a pass'),
    ({'kind': 'F', 'layer': 'client', 'extracted': ['9 U.S. 9'], 'guard_html': '<code>9 U.S. 9</code> NOT FOUND',
      'results': [{'citation': '9 U.S. 9', 'state': 'not_found'}]}, 'PASS', 'a shown not_found passes'),
    ({'kind': 'F', 'layer': 'client', 'extracted': ['9 U.S. 9'], 'guard_html': '',
      'results': [{'citation': '9 U.S. 9', 'state': 'not_found'}]}, 'FAIL',
     'a not_found the guard never SHOWS still fails'),
    ({'kind': 'A', 'layer': 'client', 'extracted': ['1 U.S. 1'], 'guard_html': '<code>1 U.S. 1</code>',
      'results': [{'citation': '1 U.S. 1', 'state': 'verified', 'case_name': 'X'}]}, 'FAIL',
     'an altered citation that verifies fails'),
    ({'kind': 'A', 'layer': 'client', 'extracted': ['1 U.S. 1'], 'guard_html': '<code>1 U.S. 1</code>',
      'results': [{'citation': '1 U.S. 1', 'state': 'unavailable'}]}, 'PASS',
     'unavailable is a flag, not a pass-as-real'),
    ({'kind': 'C', 'layer': 'client', 'results': [{'state': 'verified'}]}, 'CONTROL-OK', 'control verified'),
    ({'kind': 'C', 'layer': 'client', 'results': [{'state': 'not_found'}]}, 'CONTROL-FAIL',
     'a control that does not verify is a harness failure'),
    ({'kind': 'X', 'layer': 'api', 'input': ['47 U.S. 483', 'B'],
      'results': [{'citation': '47 U.S. 483', 'state': 'verified', 'case_name': 'Brown'}]}, 'FAIL',
     'a fabricated substring verified as the real case fails'),
    ({'kind': 'X', 'layer': 'api', 'input': ['47 U.S. 483', 'B'],
      'results': [{'citation': '47 U.S. 483', 'state': 'not_found'}]}, 'PASS', 'collision handled'),
]


def run_fixtures():
    bad = []
    for row, want, why in FIXTURES:
        got = classify(row)[0]
        if got != want:
            bad.append('EXPECTED %s, got %s -- %s' % (want, got, why))
    return bad


def main(argv):
    as_json = '--json' in argv
    bad = run_fixtures()
    if bad:
        print('CRITERIA LOCK FAILED -- nothing real was judged:')
        for b in bad:
            print('  ! ' + b)
        return 2
    if not as_json:
        print('SAIRNLAW CITATOR STRESS -- criteria lock %s: %d/%d fixtures classify correctly'
              % (CRITERIA_VERSION, len(FIXTURES), len(FIXTURES)))
    if '--fixtures' in argv:
        return 0
    node = shutil.which('node')
    if not node:
        print('COULD NOT RUN: node is not on PATH, so the real handler and client code were not driven.')
        return 2
    d = tempfile.mkdtemp(prefix='citator-stress-')
    h = os.path.join(d, 'harness.js')
    with open(h, 'w', encoding='utf-8') as fh:
        fh.write(HARNESS)
    upstream = {k: [v[0], v[1]] for k, v in UPSTREAM.items()}
    try:
        r = subprocess.run([node, h, REPO, json.dumps(upstream), json.dumps(CORPUS)],
                           capture_output=True, text=True, encoding='utf-8',
                           errors='replace', timeout=300, cwd=REPO)
        out = json.loads(r.stdout or '{}')
    except Exception as e:                                       # noqa: BLE001
        print('COULD NOT RUN: the harness failed (%s: %s)' % (type(e).__name__, e))
        return 2
    if not out.get('ok'):
        print('COULD NOT RUN: %s' % (out.get('err') or r.stderr[-400:]))
        return 2
    rows = out['rows']
    verdicts = []
    for row in rows:
        v, why = classify(row)
        row['verdict'], row['reason'] = v, why
        verdicts.append(v)
    if as_json:
        print(json.dumps({'criteria': CRITERIA_VERSION, 'rows': rows,
                          'exit': 2 if 'CONTROL-FAIL' in verdicts else (1 if 'FAIL' in verdicts else 0)},
                         indent=1))
    else:
        print('REAL: api/legal-citator.js verify + sairnlaw.html lawCiteGuard path. FIXTURE: the '
              'CourtListener answers (UPSTREAM in this file).')
        for row in rows:
            inp = row['input'] if isinstance(row['input'], str) else ' || '.join(row['input'])
            print('')
            print('%-12s %s  [%s, %s layer]' % (row['verdict'], row['id'], row['kind'], row['layer']))
            print('   input   : %s' % inp)
            print('   why     : %s' % row['why'])
            if row['layer'] == 'client':
                print('   extracted: %s' % (row.get('extracted') or '(none)'))
            print('   states  : %s' % [(x.get('citation'), x.get('state'), x.get('case_name'))
                                       for x in row.get('results') or []])
            print('   reason  : %s' % row['reason'])
        n_fail = verdicts.count('FAIL')
        print('')
        print('upstream calls made: %d' % out.get('upstream_calls', 0))
        print('%d corpus items: %d PASS, %d FAIL, controls %s'
              % (len(rows), verdicts.count('PASS'), n_fail,
                 'OK' if 'CONTROL-FAIL' not in verdicts else 'FAILED'))
    if 'CONTROL-FAIL' in verdicts:
        if not as_json:
            print('COULD NOT RUN: a control failed, so a FAIL or PASS above means nothing.')
        return 2
    return 1 if 'FAIL' in verdicts else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
