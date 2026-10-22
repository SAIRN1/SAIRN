// tests/sairnlegacy_countersign_ui.js
// Run: node tests/sairnlegacy_countersign_ui.js [path-to-sairnlegacy.html]
//
// fourth b56: the F3 countersignature UI (cody b49 O2 -- the deferred-write
// flow existed only as an API). A cremation record is STAGED with
// /api/leg-countersign `prepare`, a different director `countersign`s it with
// the one-time reference, and the preparer FILES exactly the staged record to
// sd-data carrying `countersign_token`. Nothing enters the local list before
// it is filed.
//
// The functions are EXTRACTED BY NAME from the shipped file and run in a vm
// with fetch stubbed; an extraction that fails exits 2 rather than testing a
// copy. Exit: 0 all passed - 1 an arm FAILED - 2 COULD NOT RUN

'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const FILE = process.argv[2] || path.join(__dirname, '..', 'sairnlegacy.html');
const html = fs.readFileSync(FILE, 'utf8').replace(/\r\n/g, '\n');
function grab(head) {
  const i = html.indexOf(head);
  if (i < 0 || html.indexOf(head, i + 1) !== -1) {
    console.log('COULD NOT RUN: "' + head.slice(0, 60) + '" found ' + (i < 0 ? 0 : 'more than one') + ' time(s) in ' + FILE);
    process.exit(2);
  }
  const end = html.indexOf('\n}\n', i);
  return html.slice(i, end + 2);
}
function grabLine(head) {
  const i = html.indexOf(head);
  if (i < 0 || html.indexOf(head, i + 1) !== -1) { console.log('COULD NOT RUN: "' + head + '"'); process.exit(2); }
  return html.slice(i, html.indexOf('\n', i));
}
let pass = 0, fail = 0;
function check(name, cond, detail) {
  if (cond) { pass++; console.log('  ok   ' + name); }
  else { fail++; console.log('  FAIL ' + name + (detail ? '\n       ' + String(detail).slice(0, 300) : '')); }
}

const SRC = [grab('function sdnData(action,resource,payload,withSession,extraBody){'),
  grab('async function saveCremation(){'), grabLine("var LEG_CS_API="), grabLine("var LEG_CS_KEY="),
  grab('function legCs(action,payload){'), grabLine('function legCsPending(){'), grabLine('function legCsSave(v){'),
  grabLine('var LEG_CS_STAGE='), grab('function legCsRender(){'), grab('async function legCsFile(i){'),
  grab('async function legCsSign(){')].join('\n');

function world(answers) {
  const calls = [], toasts = [], store = {}, els = {};
  const el = (id) => (els[id] = els[id] || { id, value: '', checked: false, textContent: '', innerHTML: '', classList: { add() {}, remove() {} } });
  const ctx = {
    calls, toasts, store, els, closed: 0, rendered: 0,
    console: { warn() {} }, JSON, Object, Array, Promise, Date, String,
    APP_ID: 'sairnlegacy', DATA_API: 'https://sairn.vercel.app/api/sd-data',
    legSession: { token: 'SESSION-TOKEN', role: 'apprentice', employee_id: 'b56-app' },
    legLastErr: {}, ceid: null,
    legLicenseKey: () => 'LEG-LIC', legFetchTimeoutSignal: () => undefined, legLocalToday: () => '2026-10-22',
    newId: () => 'CR-NEW', H: (x) => String(x == null ? '' : x).replace(/</g, '&lt;'), fdatetime: (x) => x,
    caseLabel: (id) => 'case ' + id, toast: (m) => toasts.push(m),
    legWriteFailText: (r, f) => (ctx.legLastErr[r] && ctx.legLastErr[r].message) || f,
    cremations: () => JSON.parse(store.leg_cremations || '[]'),
    st: (k, v) => { store[k] = JSON.stringify(v); return true; },
    closeCremationModal: () => { ctx.closed++; }, rCremation: () => { ctx.rendered++; },
    confirm: () => true, legMarkSynced: () => {}, legAdoptServerId: () => {},
    $: el,
    localStorage: { getItem: (k) => (k in store ? store[k] : null), setItem: (k, v) => { store[k] = String(v); } },
    fetch: (url, opts) => {
      const body = JSON.parse(opts.body); calls.push({ url, headers: opts.headers, body });
      const a = answers(url, body) || { status: 200, json: { ok: true } };
      return Promise.resolve({ ok: a.status < 300, status: a.status, json: () => Promise.resolve(a.json) });
    }
  };
  ['crcase', 'crname', 'crsched', 'crstatus', 'crauth', 'cridcheck', 'crwait', 'crwitness', 'crdisposition', 'crdispositiondetails'].forEach(el);
  els.crcase.value = 'CASE-1'; els.crname.value = 'Valley Crematory'; els.crstatus.value = 'Scheduled'; els.crdisposition.value = 'Return to Family';
  vm.createContext(ctx); vm.runInContext(SRC, ctx);
  return ctx;
}

(async () => {
  console.log('1. saving STAGES the record; nothing is written locally before it is filed');
  {
    const w = world((url, b) => (/leg-countersign/.test(url) && b.action === 'prepare' ? { status: 200, json: { ok: true, token: 'TOK<1>', expires_at: '2026-10-23T00:00:00Z' } } : null));
    await w.saveCremation();
    const prep = w.calls.find((c) => /leg-countersign/.test(c.url));
    check('U1. prepare is sent for leg_cremations with the record as payload', !!prep && prep.body.action === 'prepare' && prep.body.resource === 'leg_cremations' && prep.body.payload.case_id === 'CASE-1' && prep.body.payload.crematory_name === 'Valley Crematory', JSON.stringify(prep && prep.body));
    check('U2. ...with the licence as bearer and the employee session', !!prep && prep.headers.Authorization === 'Bearer LEG-LIC' && prep.headers['X-SD-Auth'] === 'SESSION-TOKEN');
    check('U3. no sd-data write and no local cremation row before filing', !w.calls.some((c) => /sd-data/.test(c.url)) && !('leg_cremations' in w.store), JSON.stringify(w.calls.map((c) => c.url)));
    const pend = JSON.parse(w.store.sairnlegacy_cs_pending || '[]');
    check('U4. the reference and the exact record are kept on this device as staged', pend.length === 1 && pend[0].token === 'TOK<1>' && pend[0].rec.case_id === 'CASE-1');
    check('U5. the person is told it is staged, NOT filed', w.toasts.some((t) => /NOT filed/.test(t)), w.toasts.join(' | '));
    w.els['cs-pending'] = { innerHTML: '' }; w.legCsRender();
    check('U6. the staged list escapes the reference (no markup from the server)', /TOK&lt;1>/.test(w.els['cs-pending'].innerHTML) && !/TOK<1>/.test(w.els['cs-pending'].innerHTML));
  }
  console.log('2. a refused prepare stages nothing and keeps the form open');
  {
    const w = world((url) => (/leg-countersign/.test(url) ? { status: 403, json: { error: { code: 'NOT_A_PREPARER', message: 'Only a licensed director, or an apprentice your home has authorised to prepare one, can stage a cremation authorisation for signature.' } } } : null));
    await w.saveCremation();
    check('R1. nothing staged, nothing written, the form stays open', !w.store.sairnlegacy_cs_pending && !('leg_cremations' in w.store) && w.closed === 0);
    check('R2. the server\'s own refusal is shown verbatim', w.toasts.some((t) => /apprentice your home has authorised/.test(t)), w.toasts.join(' | '));
  }
  console.log('3. filing sends the exact staged record with its countersign reference');
  {
    const w = world((url, b) => (/sd-data/.test(url) ? { status: 200, json: { ok: true, data: { id: 'CR-9' } } } : null));
    const rec = { id: 'CR-9', case_id: 'CASE-9', crematory_name: 'Hill' };
    w.store.sairnlegacy_cs_pending = JSON.stringify([{ token: 'TOK-9', rec, expires_at: 'x' }]);
    await w.legCsFile(0);
    const wr = w.calls.find((c) => /sd-data/.test(c.url));
    check('F1. sd-data write carries countersign_token and the same record', !!wr && wr.body.action === 'write' && wr.body.resource === 'leg_cremations' && wr.body.countersign_token === 'TOK-9' && JSON.stringify(wr.body.payload) === JSON.stringify(rec), JSON.stringify(wr && wr.body));
    check('F2. on success the record joins the local list and leaves the staged list', JSON.parse(w.store.leg_cremations || '[]').some((x) => x.id === 'CR-9') && JSON.parse(w.store.sairnlegacy_cs_pending).length === 0);
  }
  {
    const w = world((url) => (/sd-data/.test(url) ? { status: 403, json: { error: { code: 'COUNTERSIGN_REQUIRED', message: 'A cremation authorisation needs a second named, signing person before it can be filed.' } } } : null));
    w.store.sairnlegacy_cs_pending = JSON.stringify([{ token: 'TOK-9', rec: { id: 'CR-9', case_id: 'C' } }]);
    await w.legCsFile(0);
    check('F3. a refused filing keeps it staged and writes nothing locally', !('leg_cremations' in w.store) && JSON.parse(w.store.sairnlegacy_cs_pending).length === 1);
    check('F4. ...and says why, in the server\'s words', w.toasts.some((t) => /second named, signing person/.test(t)), w.toasts.join(' | '));
    const other = world(() => null);
    const plain = other.calls; await other.sdnData('read', 'leg_cases', {});
    check('F5. every other sdnData call sends no countersign_token', !('countersign_token' in plain[0].body));
  }
  console.log('4. countersigning');
  {
    const w = world((url, b) => (b.action === 'countersign' ? { status: 409, json: { error: { code: 'SAME_PERSON', message: 'The person who prepared a record cannot also countersign it.' } } } : null));
    w.els['cs-ref'] = { value: '  TOK-5 ' }; w.els['cs-result'] = { textContent: '' };
    await w.legCsSign();
    const c = w.calls[0];
    check('S1. countersign is sent with the trimmed reference', !!c && c.body.action === 'countersign' && c.body.token === 'TOK-5');
    check('S2. a refusal is shown in the server\'s words', /cannot also countersign/.test(w.els['cs-result'].textContent), w.els['cs-result'].textContent);
  }
  console.log('\n' + (fail ? 'FAILED' : 'ok') + '  sairnlegacy countersign UI: ' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})().catch((e) => { console.log('COULD NOT RUN: ' + e.stack); process.exit(2); });
