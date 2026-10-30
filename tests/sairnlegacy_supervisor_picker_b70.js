// tests/sairnlegacy_supervisor_picker_b70.js
//
// REQUIREMENT: an apprentice staging a cremation record names the licensed
//   director supervising it, and that name travels IN the staged record as
//   `authorized_by_supervisor` -- the field api/leg-countersign.js requires
//   (api/b69-leg-f3-supervisor.test.js P4/P8, S1-S3). Without it every
//   apprentice prepare is refused 403 SUPERVISOR_REQUIRED.
//
// Run:  node tests/sairnlegacy_supervisor_picker_b70.js [path-to-sairnlegacy.html]
//
// WRITTEN BEFORE THE FIX and run against the unfixed page: arms 1-5 failed.
// Arm 6 is the CONTROL: a director stages exactly as before, with no field.

'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const FILE = process.argv[2] || path.resolve(__dirname, '..', 'sairnlegacy.html');
const html = fs.readFileSync(FILE, 'utf8').replace(/\r\n/g, '\n');

let pass = 0, fail = 0;
function test(name, fn) {
  return Promise.resolve().then(fn).then(
    () => { console.log('  ok   ' + name); pass++; },
    (e) => { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; });
}
function grab(sig) {
  const at = html.indexOf(sig);
  assert.ok(at !== -1, 'not found: ' + sig);
  let i = html.indexOf('{', at), depth = 0;
  for (; i < html.length; i++) {
    if (html[i] === '{') depth++;
    else if (html[i] === '}' && --depth === 0) return html.slice(at, i + 1);
  }
  throw new Error('unterminated: ' + sig);
}

// A DOM of plain objects and a captured prepare call: saveCremation is RUN.
function harness(role, supValue) {
  const els = {
    crcase: { value: 'CS-1' }, crname: { value: 'Pinnacle' }, crsched: { value: '' },
    crstatus: { value: 'Scheduled' }, crauth: { checked: true }, cridcheck: { checked: true },
    crwait: { checked: true }, crwitness: { checked: false }, crdisposition: { value: 'Return to Family' },
    crdispositiondetails: { value: '' }, crsupervisor: { value: supValue || '' },
    crsupervisorrow: { style: {} }, cremationmodal: { classList: { add() {}, remove() {} } }
  };
  const sent = [], toasts = [];
  const ctx = vm.createContext({
    console, Date, JSON, String, Object,
    $: (id) => els[id] || null,
    legSession: { role: role, employee_id: 'emp-me', token: 't' },
    legCremationStaging: false, ceid: null,
    cremations: () => [], newId: () => 'CR-1', legLocalToday: () => '2026-10-30',
    toast: (m) => toasts.push(m),
    legCs: async (action, p) => { sent.push({ action, p }); return { ok: true, data: { token: 'tok', expires_at: '' } }; },
    legCsPending: () => [], legCsSave() {}, closeCremationModal() {}, rCremation() {}
  });
  for (const sig of ['function legCrSupervisorShow(', 'function legCrSupervisorFor(', 'async function saveCremation(']) {
    try { vm.runInContext(grab(sig), ctx); } catch (e) { if (!/legCrSupervisor/.test(sig)) throw e; }
  }
  return { ctx, els, sent, toasts };
}

(async () => {
  console.log('SAIRNLEGACY -- an apprentice names the supervising director in the staged record');
  await test('1. the cremation modal has a supervisor input', () => {
    assert.ok(/id="crsupervisor"/.test(html), 'no #crsupervisor input');
  });
  await test('2. an apprentice with a director named -> the prepare payload carries authorized_by_supervisor', async () => {
    const h = harness('apprentice', ' DIR-01 ');
    await h.ctx.saveCremation();
    assert.strictEqual(h.sent.length, 1, 'no prepare was sent: ' + h.toasts.join(' | '));
    assert.strictEqual(h.sent[0].p.payload.authorized_by_supervisor, 'DIR-01');
  });
  await test('3. an apprentice with NO director named -> nothing is staged, and the toast says why', async () => {
    const h = harness('apprentice', '');
    await h.ctx.saveCremation();
    assert.strictEqual(h.sent.length, 0, 'a prepare was sent without a supervisor');
    assert.ok(/supervis/i.test(h.toasts.join(' ')), h.toasts.join(' | '));
  });
  await test('4. an apprentice naming THEMSELF -> nothing is staged', async () => {
    const h = harness('apprentice', 'emp-me');
    await h.ctx.saveCremation();
    assert.strictEqual(h.sent.length, 0);
  });
  await test('5. the field is shown to an apprentice and hidden from a director', () => {
    const a = harness('apprentice'); a.ctx.legCrSupervisorShow('');
    const d = harness('director'); d.ctx.legCrSupervisorShow('');
    assert.strictEqual(a.els.crsupervisorrow.style.display, '');
    assert.strictEqual(d.els.crsupervisorrow.style.display, 'none');
  });
  await test('6. CONTROL: a director stages as before -- no supervisor field in the payload', async () => {
    const h = harness('director', 'ignored');
    await h.ctx.saveCremation();
    assert.strictEqual(h.sent.length, 1);
    assert.ok(!('authorized_by_supervisor' in h.sent[0].p.payload));
  });
  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
