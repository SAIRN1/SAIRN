'use strict';
// tests/sairnvet_witness_token_client.js -- fourth b64.
//
// Two defects the b63 worldwide audit found in sairnvet.html, and their fixes:
//   1. api/sd-data.js refuses every sv_controlled write without an X-SV-Witness
//      token, and the app never requested one. svPushOne() now asks
//      api/sv-witness.js for a token bound to the EXACT record it sends.
//   2. The SOAP record stored 60 characters of the complaint and no note.
//      generateSOAP() and scribeAcceptDraft() now store the note itself.
//
// The functions are lifted out of the real file and run against stubs. The
// content-hash arm uses the SERVER'S OWN contentHash(), so "the token was
// requested for the record that was written" is checked the way the server
// checks it, not by comparing two strings this test built.
//
// Run: node tests/sairnvet_witness_token_client.js
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const { contentHash } = require('../api/sv-witness.js');

const src = fs.readFileSync(path.join(__dirname, '..', 'sairnvet.html'), 'utf8');
let pass = 0, fail = 0;
function check(name, ok, detail) {
  if (ok) { pass++; console.log('  ok   ' + name); return; }
  fail++; console.log('  FAIL ' + name + (detail ? '\n         ' + detail : ''));
}
function balanced(start) {
  let i = src.indexOf('{', start), depth = 0;
  for (; i < src.length; i++) {
    if (src[i] === '{') depth++;
    else if (src[i] === '}') { depth--; if (!depth) return src.slice(start, i + 1); }
  }
  throw new Error('unbalanced from ' + start);
}
function fn(decl) {
  const i = src.indexOf(decl);
  if (i < 0) throw new Error('anchor no longer matches: ' + decl);
  return balanced(i);
}

// ── 1. THE WITNESS TOKEN ────────────────────────────────────────────────────
function pushHarness(witnessAnswer) {
  const calls = [], toasts = [];
  const ctx = {
    calls, toasts, console: { warn() {} },
    svLoad: (k) => (k === 'license' ? 'SV-TEST' : ''),
    svTok: () => 'session-tok',
    svFetchTimeoutSignal: () => undefined,
    showToast: (m) => toasts.push(String(m)),
    setTimeout: () => 0,
    fetch: (url, opts) => {
      const body = JSON.parse(opts.body);
      calls.push({ url, headers: opts.headers, body });
      if (/sv-witness/.test(url)) {
        return Promise.resolve({ ok: witnessAnswer.ok, status: witnessAnswer.status,
                                 json: () => Promise.resolve(witnessAnswer.body) });
      }
      return Promise.resolve({ ok: true, status: 200,
                               json: () => Promise.resolve({ ok: true, data: body.payload }) });
    },
  };
  vm.createContext(ctx);
  vm.runInContext([
    'var SV_PUSH_TIMEOUT={svPushTimeout:true};', 'var SV_PUSH_REJECTED={svPushRejected:true};',
    'var SV_PUSH_TIMEOUT_MS=15000;', "var SV_DATA_API='https://sairn.vercel.app/api/sd-data';",
    "var SV_WITNESS_API='https://sairn.vercel.app/api/sv-witness';",
    fn('function svWitnessRequest('), fn('function svData('), fn('function svPushOne('),
  ].join('\n'), ctx);
  return ctx;
}

(async () => {
  console.log('sairnvet witness token + SOAP body (fourth b64)\n');
  const rec = { drug: 'Hydromorphone', schedule: 'II', onHand: 7.5, unit: 'mL',
                lastTransaction: '2026-10-28 — 0.5mL used', witness: 'Dr B', id: 'Hydromorphone' };

  let c = pushHarness({ ok: true, status: 200, body: { ok: true, token: 'TOK-123' } });
  let r = await c.svPushOne('sv_controlled', rec, 'Hydromorphone');
  const w = c.calls[0], d = c.calls[1];
  check('sv_controlled asks sv-witness for a token FIRST', !!w && /sv-witness/.test(w.url) && w.body.action === 'request',
        JSON.stringify(c.calls.map((x) => x.url)));
  check('...as the signed-in session (X-SD-Auth), on the licence', !!w && w.headers['X-SD-Auth'] === 'session-tok'
        && w.headers['Authorization'] === 'Bearer SV-TEST');
  check('...then writes to sd-data carrying exactly that token', !!d && /sd-data/.test(d.url)
        && d.headers['X-SV-Witness'] === 'TOK-123', d && JSON.stringify(d.headers));
  check('THE SERVER\'S contentHash of the token request equals that of the write -- the token is spendable on this record',
        !!w && !!d && contentHash('sv_controlled', w.body.payload) === contentHash('sv_controlled', d.body.payload));
  check('...and the push resolves with the server\'s answer', !!r && r.drug === 'Hydromorphone');

  c = pushHarness({ ok: false, status: 403, body: { error: { code: 'NOT_A_PRESCRIBER' } } });
  r = await c.svPushOne('sv_controlled', rec, 'Hydromorphone');
  check('a refused token sends NO write at all', c.calls.length === 1 && !c.calls.some((x) => /sd-data/.test(x.url)),
        JSON.stringify(c.calls.map((x) => x.url)));
  check('...resolves null, so nothing reads it as backed up', r === null);
  check('...and SAYS so on screen, naming the refusal', c.toasts.some((t) => /device only/.test(t) && /NOT_A_PRESCRIBER/.test(t)),
        JSON.stringify(c.toasts));

  c = pushHarness({ ok: true, status: 200, body: { ok: true, token: 'X' } });
  const p = c.svPushOne('sv_patients', { id: 'p1', name: 'Bella' }, 'p1');
  check('CONTROL: any other collection is written SYNCHRONOUSLY, with no witness call',
        c.calls.length === 1 && /sd-data/.test(c.calls[0].url) && !c.calls[0].headers['X-SV-Witness'],
        JSON.stringify(c.calls.map((x) => x.url)));
  await p;

  // ── 2. THE SOAP NOTE IS STORED ─────────────────────────────────────────────
  const els = {};
  const el = (id) => (els[id] = els[id] || { value: '', textContent: '', checked: false, style: {} });
  el('soap-patient').value = 'Bella (canine)'; el('soap-subj').value = 'Vomiting x2 days, lethargic, no appetite since Monday';
  el('soap-obj').value = 'T 39.8, HR 120, mild dehydration'; el('userRole').textContent = 'Doctor';
  let saved = null;
  const s = {
    document: { getElementById: el }, console,
    showToast() {}, logDoseAudit() {}, renderSoap() {}, localToday: () => '2026-10-28',
    getSoapNotes: () => [], saveSoapNotes: (l) => { saved = l; return true; },
    callClaude: () => Promise.resolve('S: vomiting\nO: febrile\nA: 1. gastritis 2. pancreatitis\nP: bloods, fluids'),
    soapGenSeq: 0, soapPendingNote: null, Date, Promise,
  };
  vm.createContext(s);
  vm.runInContext(fn('function generateSOAP('), s);
  s.generateSOAP();
  await new Promise((res) => setImmediate(res));
  const n = saved && saved[0];
  check('generateSOAP stores the NOTE the vet reviewed, not 60 characters of the complaint',
        !!n && n.note === 'S: vomiting\nO: febrile\nA: 1. gastritis 2. pancreatitis\nP: bloods, fluids', JSON.stringify(n));
  check('...and the subjective and objective it was written from, in full',
        !!n && n.subjective === el('soap-subj').value && n.objective === el('soap-obj').value);
  check('...and is still a Draft until sign-off', !!n && n.status === 'Draft');

  saved = null;
  const sc = {
    console, showToast() {}, renderSoap() {}, scribeReset() {}, localToday: () => '2026-10-28',
    getSoapNotes: () => [], saveSoapNotes: (l) => { saved = l; return true; },
    scEl: (id) => el('sc:' + id), scConsent: { id: 'consent-1', patient: 'Bella' }, scPendingModel: 'm', window: {},
    Date,
  };
  el('sc:sc-draft').value = 'Full scribe draft: history, exam, assessment and plan, longer than sixty characters.';
  el('sc:soap-patient').value = 'Bella';
  vm.createContext(sc);
  vm.runInContext(fn('window.scribeAcceptDraft = function'), sc);
  sc.window.scribeAcceptDraft();
  const m = saved && saved[0];
  check('scribeAcceptDraft stores the accepted draft before clearing it from the screen',
        !!m && m.note === 'Full scribe draft: history, exam, assessment and plan, longer than sixty characters.',
        JSON.stringify(m));

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})().catch((e) => { console.log('COULD NOT RUN: ' + e.message); process.exit(2); });
