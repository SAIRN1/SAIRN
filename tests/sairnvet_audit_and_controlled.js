// tests/sairnvet_audit_and_controlled.js
//
// Run:  node tests/sairnvet_audit_and_controlled.js
//
// SAIRNvet's audit trail and its controlled-substance KPIs, driven verbatim
// from sairnvet.html.
//
// THREE DEFECTS, all found in the 2026-09-04 silent-failure sweep, all of the
// same family: a real function doing real work and the screen saying something
// that is not what happened.
//
//   1. logDoseAudit() has always returned true/false and ALL SEVENTEEN call
//      sites ignored it. st() returns false on a full or unavailable store, so
//      a lost audit row was completely invisible. Two of those call sites are
//      clinical sign-offs whose toast asserts the row exists:
//      onDoseVetSignoff() said "Confirmed — recorded for this patient" and
//      onSoapSignoff() said "Confirmed for this patient", either of which
//      could be printed over a write that never happened.
//
//   2. onSoapSignoff() also ignored saveSoapNotes(). A failed write leaves the
//      note UNREVIEWED in storage while the toast says it was confirmed --
//      and renderSoap() re-reads storage, so the screen and the message
//      actively disagreed.
//
//   3. The Schedule II "On Hand" KPI was one reduce over d.onHand printed as
//      "N units". Fentanyl is seeded in mL and logControlledUse() creates any
//      newly-logged drug with unit '', so the first mg-dosed Schedule II drug
//      logged made this add millilitres to milligrams and present the result
//      as a controlled-substance balance. Alongside it, "Discrepancies This
//      Month" counted every negative balance ever -- nothing in this panel is
//      filtered by date, because the rows carry no date field at all.
//
// The functions are lifted out of the real file rather than reimplemented.

'use strict';
const fs = require('fs');
const path = require('path');

const HTML = path.join(__dirname, '..', 'sairnvet.html');
const src = fs.readFileSync(HTML, 'utf8');

let pass = 0, fail = 0;
function check(name, actual, expected) {
  const a = JSON.stringify(actual), e = JSON.stringify(expected);
  if (a === e) { pass++; return; }
  fail++;
  console.log('FAIL  ' + name + '\n        expected ' + e + '\n        actual   ' + a);
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
  if (i < 0) throw new Error('not found: ' + decl);
  return balanced(i);
}

// A store that can be told to refuse writes, which is the whole point: st()
// returning false is the trigger every assertion below turns on.
function makeStore(refuseWrites) {
  const data = {};
  const store = {
    getItem: (k) => (k in data ? data[k] : null),
    setItem: (k, v) => { if (refuseWrites) throw new Error('QuotaExceededError'); data[k] = v; },
    key: (i) => Object.keys(data)[i],
    get length() { return Object.keys(data).length; }
  };
  return { data, store };
}

// Minimal DOM: renderControlled touches exactly two ids plus createElement.
function makeDom(fields) {
  const els = {
    'controlled-tbody': { innerHTML: '', appendChild(tr) { this.innerHTML += tr.innerHTML; } },
    'controlled-kpis': { innerHTML: '' }
  };
  Object.keys(fields || {}).forEach((id) => { els[id] = { value: fields[id], checked: fields[id] === true, textContent: fields[id] }; });
  const body = { innerHTML: '' };
  return {
    els,
    body,
    document: {
      body,
      title: '',
      getElementById: (id) => els[id] || null,
      createElement: () => ({ innerHTML: '' })
    }
  };
}

function build(opts) {
  opts = opts || {};
  const s = makeStore(opts.refuseWrites);
  const dom = makeDom(opts.fields);
  const toasts = [];
  const api = new Function(
    'localStorage', 'document', 'showToast', 'console',
    fn('function escHtml(s){') + '\n' +
    'var _svKeyVerified = {};\nvar _svUnreadable = {};\n' +
    fn('function st(key,data){') + '\n' +
    fn('function svIntegrityScan(){') + '\n' +
    fn('function svBlockForCorruptStore(keys){') + '\n' +
    fn('function logDoseAudit(entry){') + '\n' +
    fn('function getControlledLog(){') + '\n' +
    fn('function saveControlledLog(list){') + '\n' +
    fn('function renderControlled(){') + '\n' +
    fn('function onDoseVetSignoff(){') + '\n' +
    'return { logDoseAudit: logDoseAudit, renderControlled: renderControlled,' +
    '         onDoseVetSignoff: onDoseVetSignoff, getControlledLog: getControlledLog,' +
    '         st: st, scan: svIntegrityScan, block: svBlockForCorruptStore };'
  )(s.store, dom.document, (m, t, d) => toasts.push({ m: String(m), t: t }), { warn() {}, error() {} });
  return { api, toasts, store: s, dom };
}

// ── logDoseAudit says what happened ────────────────────────────────────────
{
  const w = build();
  check('a successful audit write returns true',
    w.api.logDoseAudit({ type: 'dose_calc' }), true);
  check('and says nothing to the user', w.toasts.length, 0);
  check('and the row is actually stored',
    JSON.parse(w.store.data.sv_audit_log).length, 1);
}
{
  const w = build({ refuseWrites: true });
  check('a refused audit write returns false',
    w.api.logDoseAudit({ type: 'dose_calc' }), false);
  check('and SAYS SO -- this is the whole defect', w.toasts.length, 1);
  check('naming the audit log, not just "error"',
    /audit log/.test(w.toasts[0].m), true);
  check('as an error, not a success', w.toasts[0].t, 'error');
}
// A corrupt log must not be replaced by an empty one. Losing an unreadable
// audit trail is worse than refusing to append to it.
{
  const w = build();
  w.store.data.sv_audit_log = '{not json';
  check('a corrupt audit log makes the write fail',
    w.api.logDoseAudit({ type: 'dose_calc' }), false);
  check('and it is left exactly as it was, not reset',
    w.store.data.sv_audit_log, '{not json');
}

// ── the dose sign-off no longer claims a record that does not exist ────────
{
  const w = build({ fields: { 'dose-vet-accepted': true, 'calc-drug': 'Ketamine' } });
  w.api.onDoseVetSignoff();
  check('a successful sign-off confirms', w.toasts.map((x) => x.t), ['success']);
}
{
  const w = build({ refuseWrites: true, fields: { 'dose-vet-accepted': true, 'calc-drug': 'Ketamine' } });
  w.api.onDoseVetSignoff();
  check('a failed sign-off does NOT say "recorded for this patient"',
    w.toasts.filter((x) => /recorded for this patient/.test(x.m)).length, 0);
  check('the operator is told the opposite instead', w.toasts.map((x) => x.t), ['error']);
}

// ── Schedule II on-hand is not added across units ──────────────────────────
{
  const w = build();
  // mL and mg in the same schedule -- reachable the moment anyone logs a
  // second Schedule II drug, because logControlledUse() stores unit '' for a
  // drug it has not seen before.
  w.store.data.sv_controlled = JSON.stringify([
    { drug: 'Fentanyl 50mcg/mL', schedule: 'II', onHand: 96, unit: 'mL', lastTransaction: '', witness: 'Tech Reyes' },
    { drug: 'Pentobarbital', schedule: 'II', onHand: 1200, unit: 'mg', lastTransaction: '', witness: 'Tech Reyes' }
  ]);
  w.api.renderControlled();
  const kpi = w.dom.els['controlled-kpis'].innerHTML;
  check('mL and mg are reported separately',
    /96 mL/.test(kpi) && /1200 mg/.test(kpi), true);
  check('and 1296 -- the meaningless sum -- appears nowhere',
    /1296/.test(kpi), false);
}
{
  const w = build();
  w.store.data.sv_controlled = JSON.stringify([
    { drug: 'New Drug', schedule: 'II', onHand: -5, unit: '', lastTransaction: '', witness: '' }
  ]);
  w.api.renderControlled();
  const kpi = w.dom.els['controlled-kpis'].innerHTML;
  check('a missing unit is named as missing, not silently treated as a unit',
    /unspecified unit/.test(kpi), true);
  check('the negative-balance count is still reported', /-5/.test(kpi), true);
}
// The label claimed a date filter this panel does not have and cannot have --
// the rows carry no transaction date, only free text.
{
  const w = build();
  w.store.data.sv_controlled = JSON.stringify([]);
  w.api.renderControlled();
  const kpi = w.dom.els['controlled-kpis'].innerHTML;
  check('the KPI no longer claims to be scoped to this month',
    /This Month/.test(kpi), false);
  check('and says what it actually counts',
    /Negative Balances \(all time\)/.test(kpi), true);
}

// ── the unreadable-store guard: never re-seed over a corrupt value ─────────
//
// The shape being closed: every get*() here does
//     try { if(stored) return JSON.parse(stored); } catch(e){}
//     var seed = [...]; saveX(seed); return seed;
// so a parse throw silently REPLACED the value with demo rows. For
// sv_controlled that is a DEA Schedule II-IV register overwritten by three
// sample drugs and shown as the real one.
{
  const w = build();
  w.store.data.sv_controlled = '{not json';
  // getControlledLog() still falls through to its seed -- that path is inside
  // 39 getters and is not what this guard changes. What it changes is that
  // the seed can no longer be WRITTEN over the unreadable value.
  w.api.getControlledLog();
  check('the unreadable DEA log is still byte-for-byte intact',
    w.store.data.sv_controlled, '{not json');
  check('and the app has blocked rather than carried on',
    /refused to open/.test(w.dom.body.innerHTML), true);
  check('naming the affected key so it can be recovered',
    /sv_controlled/.test(w.dom.body.innerHTML), true);
  check('and saying plainly that nothing was deleted',
    /Nothing has been deleted or overwritten/.test(w.dom.body.innerHTML), true);
  check('with NO one-click wipe offered -- that is what destroys the record',
    /clear|delete|reset/i.test(w.dom.body.innerHTML.replace(/Do not clear this browser[^<]*/, '')
      .replace(/deleted or overwritten/, '')), false);
}
{
  const w = build();
  w.store.data.sv_controlled = '{not json';
  check('a direct write to the corrupt key is REFUSED',
    w.api.st('sv_controlled', [{ drug: 'X' }]), false);
  check('and the corrupt value survives the refusal',
    w.store.data.sv_controlled, '{not json');
  check('a second write is refused too, not just the first',
    w.api.st('sv_controlled', [{ drug: 'Y' }]), false);
}
{
  const w = build();
  w.store.data.sv_patients = JSON.stringify([{ id: 'P-1' }]);
  check('a readable key writes normally', w.api.st('sv_patients', [{ id: 'P-2' }]), true);
  check('and the new value is what is stored',
    JSON.parse(w.store.data.sv_patients), [{ id: 'P-2' }]);
}
// The scan must not fire on values this app legitimately stores as bare
// numbers or strings -- all of which are valid JSON. A false positive here
// would refuse to open a perfectly healthy clinic.
{
  const w = build();
  Object.assign(w.store.data, {
    sv_trial_start: '1788525956000',        // String(startMs)
    sv_speciesref_lookups: '7',             // String(n+1)
    sv_analytics_scans: '12',               // String(n+1)
    sv_role: '"Doctor"',                    // svStore -> JSON.stringify(string)
    sv_patients: '[]',
    unrelated_other_app_key: 'not json at all'
  });
  check('a healthy store scans clean', w.api.scan(), []);
  w.store.data.sv_boarding = '[{"id":';
  check('and a genuinely corrupt sv_ key is found', w.api.scan(), ['sv_boarding']);
}

// The gate is top-level boot code, so it cannot be driven the way the
// functions above can. Its ORDER is the thing that matters and is asserted
// directly: once a render*() has run, its get*() has already returned seed
// data and the demo rows are on screen -- blocking after that is too late.
{
  const gate = src.indexOf('var _svCorruptAtBoot = svIntegrityScan();');
  const pin = src.indexOf('setupPinPad();', gate > 0 ? gate : 0);
  const firstRender = src.indexOf('renderWhiteboard();', gate > 0 ? gate : 0);
  check('the boot gate exists', gate > 0, true);
  check('and runs before setupPinPad()', gate < pin, true);
  check('and before the first render', gate < firstRender, true);
  check('and the boot really is inside its else, not merely after it',
    /svBlockForCorruptStore\(_svCorruptAtBoot\);\s*\}else\{/.test(src), true);
}

console.log((fail ? 'FAILED' : 'ok') + '  sairnvet-audit-and-controlled: ' +
  pass + ' passed, ' + fail + ' failed');
if (fail) process.exit(1);
