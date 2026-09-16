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

// SV_HTML lets a negative control point this suite at a MUTATED COPY in a temp
// directory instead of patching the tracked file and restoring it afterwards.
// Same convention tests/sairnvet_seed_never_syncs.js took from SB_HTML rather
// than a second one being invented. Unset -- every ordinary run, including CI
// -- this is exactly what it was.
const HTML = process.env.SV_HTML || path.join(__dirname, '..', 'sairnvet.html');
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
// One whole `var NAME = ...;` statement, lifted verbatim. THROWS rather than
// returning '' when the prefix stops matching: a missing declaration would make
// every arm below fail with a ReferenceError from inside a catch, which reads as
// a defect in the app rather than as this file's anchor having rotted. That
// exact confusion is what left the boot-gate arm red further down.
function decl(prefix) {
  const i = src.indexOf(prefix);
  if (i < 0) throw new Error('declaration anchor no longer matches: ' + prefix);
  const j = src.indexOf(';', i);
  if (j < 0) throw new Error('unterminated declaration: ' + prefix);
  return src.slice(i, j + 1);
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
    // ── THE HARNESS MUST CARRY WHAT THE SLICED FUNCTIONS CALL (2026-09-10) ──
    // getControlledLog() was wrapped in svSeedStore() by the seed-leak sweep,
    // and this sandbox did not include it, so every test in this file died on
    // `ReferenceError: svSeedStore is not defined` before asserting anything.
    //
    // TAKEN FROM THE FILE, NOT STUBBED. A stub returning `saver(rows)` would
    // pass and would silently stop testing the suppression: the real one sets
    // svSyncSuppressed and clears it in a finally, and that is precisely the
    // behaviour a seeding test should be exercising. Same reason st() is
    // sliced rather than faked.
    //
    // svSyncSuppressed is declared here because the sandbox has no module
    // scope to hoist it from -- svSeedStore reads and writes it, and without a
    // binding the first assignment would throw in strict-mode-adjacent Function
    // bodies and leak to the global otherwise.
    'var _svKeyVerified = {};\nvar _svUnreadable = {};\nvar svSyncSuppressed = false;\n' +
    // ── THE AUDIT CAP'S CONSTANTS AND HELPERS, TAKEN FROM THE FILE ─────────
    // Hand-writing `var SV_AUDIT_CAP = 500;` here would make this sandbox a
    // SECOND declaration of the cap, and the arms below would then keep passing
    // against a number the app had moved away from. Five suites in this repo
    // have already broken on a hand-written mirror of a declaration going
    // stale; this one is read out of sairnvet.html every run.
    decl('var SV_AUDIT_KEY = ') + '\n' +
    decl('var SV_AUDIT_CAP = ') + '\n' +
    decl('var SV_AUDIT_BACKED_KEY = ') + '\n' +
    fn('function svAuditCanonical(v){') + '\n' +
    fn('function svAuditContentId(entry){') + '\n' +
    fn('function svAuditBackedSet(){') + '\n' +
    fn('function svAuditMarkBacked(id){') + '\n' +
    fn('function svSeedStore(saver, rows){') + '\n' +
    fn('function st(key,data){') + '\n' +
    fn('function svIntegrityScan(){') + '\n' +
    fn('function svBlockForCorruptStore(keys){') + '\n' +
    fn('function logDoseAudit(entry){') + '\n' +
    fn('function getControlledLog(){') + '\n' +
    fn('function saveControlledLog(list){') + '\n' +
    fn('function renderControlled(){') + '\n' +
    fn('function onDoseVetSignoff(){') + '\n' +
    'return { svAuditContentId: svAuditContentId, svAuditMarkBacked: svAuditMarkBacked,' +
    '         svAuditBackedSet: svAuditBackedSet,' +
    '         logDoseAudit: logDoseAudit, renderControlled: renderControlled,' +
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
  // ── THIS ARM WAS RED AND THE ANCHOR HAD ROTTED, NOT THE APP (2026-09-14) ──
  // It searched for `renderWhiteboard();` AFTER the gate. Every one of the four
  // such calls sits between lines 2741 and 3031, inside panel functions, far
  // ABOVE the gate at 9271 -- so indexOf returned -1, `gate < -1` was false, and
  // the arm had been failing against a correct file. The direct boot render it
  // was written for is gone: the boot path is now svRestoreSession() ->
  // svEnterApp(), and the line where the render used to be is a COMMENT saying
  // "svEnterApp() painted every panel".
  //
  // AN ANCHOR THAT IS NOT FOUND MUST SAY SO, which is the half that was missing
  // and the reason this read as an ordering failure for however long it sat
  // there. tests/dnt_vendor_write_confirmation_probe.py already records the
  // same lesson as ANCHOR-0: -1 is a could-not-tell, and folding it into a
  // comparison turns it into a confident wrong answer about the app.
  const firstEntry = src.indexOf('if(svRestoreSession()){', gate > 0 ? gate : 0);
  check('the boot gate exists', gate > 0, true);
  check('the setupPinPad anchor still matches', pin !== -1, true);
  check('the boot-entry anchor still matches', firstEntry !== -1, true);
  check('and runs before setupPinPad()', gate < pin, true);
  check('and before the boot path that paints the panels', gate < firstEntry, true);
  check('and the boot really is inside its else, not merely after it',
    /svBlockForCorruptStore\(_svCorruptAtBoot\);\s*\}else\{/.test(src), true);
}

// ── THE CAP MAY NOT EVICT WHAT HAS NO SECOND COPY (2026-09-14) ─────────────
// The defect: a flat 500-entry cap keeping the NEWEST, and entries written
// before 2026-09-09 with no id that svSyncCollection() therefore never backed
// up. The two compound -- the cap evicts OLDEST first and the un-backed-up
// entries ARE the oldest -- so the entries that existed in exactly one place
// were precisely the ones the next 500 writes pushed out.
//
// ARM 4 IS THE CONTROL AND IT IS THE WHOLE POINT: 600 entries with NONE
// confirmed must stay 600. The old code dropped 100 of them, so that arm fails
// against the previous version of the function by construction. An arm that
// only proved eviction WORKS would have passed against the defect.
function auditWith(entries, backed) {
  const w = build();
  w.store.data.sv_audit_log = JSON.stringify(entries);
  if (backed) w.store.data.sv_audit_backed = JSON.stringify(backed);
  return w;
}
function legacy(n, tag) {
  const out = [];
  for (let i = 0; i < n; i++) out.push({ type: (tag || 'dose_calc'), seq: i, timestamp: 't' + i });
  return out;
}

{
  // 1. a derived id, and the same entry derives the SAME id every time
  const w = build();
  const e = { type: 'dose_calc', seq: 1, timestamp: 't1' };
  w.api.logDoseAudit({ type: 'fresh' });
  const a = w.api.svAuditContentId(e), b = w.api.svAuditContentId({ timestamp: 't1', seq: 1, type: 'dose_calc' });
  check('the derived id is deterministic across key order', a, b);
  check('and it is self-labelling as computed-later', a.slice(0, 2), 'ac');
  check('two DIFFERENT entries do not collide',
    w.api.svAuditContentId({ a: 1 }) === w.api.svAuditContentId({ a: 2 }), false);
  // The id must not depend on an id already present, or re-deriving changes it.
  check('an existing id is excluded from the derivation',
    w.api.svAuditContentId({ a: 1, id: 'x' }), w.api.svAuditContentId({ a: 1 }));
}
{
  // 2. legacy entries acquire ids on the next write, content untouched
  const w = auditWith(legacy(3));
  check('a fresh entry is written', w.api.logDoseAudit({ type: 'dose_calc' }), true);
  const log = JSON.parse(w.store.data.sv_audit_log);
  check('every entry now has an id', log.every((r) => !!r.id), true);
  check('the legacy ones are marked as derived', log.slice(0, 3).every((r) => r.id.slice(0, 2) === 'ac'), true);
  check('the new one is marked as issued at the time', log[3].id.slice(0, 2), 'au');
  check('and NOTHING recorded in a legacy entry changed',
    JSON.stringify(log.slice(0, 3).map((r) => ({ type: r.type, seq: r.seq, timestamp: r.timestamp }))),
    JSON.stringify(legacy(3)));
  check('and the user is told, on screen, not in the console',
    w.toasts.filter((t) => /historical audit entr/.test(t.m)).length, 1);
}
{
  // 3. it is one-shot: nothing is re-derived on the next write
  const w = auditWith(legacy(3));
  w.api.logDoseAudit({ type: 'dose_calc' });
  const second = build();
  second.store.data.sv_audit_log = w.store.data.sv_audit_log;
  second.api.logDoseAudit({ type: 'dose_calc' });
  check('the derived-id notice does not repeat',
    second.toasts.filter((t) => /historical audit entr/.test(t.m)).length, 0);
}
{
  // 4. THE CONTROL. Over the cap, nothing confirmed -> NOTHING is discarded.
  const w = auditWith(legacy(600));
  w.api.logDoseAudit({ type: 'dose_calc' });
  const log = JSON.parse(w.store.data.sv_audit_log);
  check('an unconfirmed entry is NEVER evicted, even far over the cap', log.length, 601);
  check('and the practice is told, on screen', w.toasts.filter((t) => /over its local limit/.test(t.m)).length, 1);
  check('the notice says nothing was discarded',
    /Nothing was discarded/.test(w.toasts.filter((t) => /over its local limit/.test(t.m))[0].m), true);
}
{
  // 5. confirmed entries DO get evicted, oldest first -- or the cap is dead
  const rows = legacy(600).map((r) => Object.assign({}, r, { id: 'seed' + r.seq }));
  const w = auditWith(rows, rows.map((r) => r.id));
  w.api.logDoseAudit({ type: 'dose_calc' });
  const log = JSON.parse(w.store.data.sv_audit_log);
  check('with every entry confirmed the cap holds', log.length, 500);
  check('and it dropped the OLDEST', log[0].id, 'seed101');
  check('and kept the newest', log[log.length - 1].id.slice(0, 2), 'au');
}
{
  // 6. it STOPS at the first unconfirmed rather than stepping over it
  const rows = legacy(600).map((r) => Object.assign({}, r, { id: 'seed' + r.seq }));
  const w = auditWith(rows, rows.slice(0, 10).map((r) => r.id));
  w.api.logDoseAudit({ type: 'dose_calc' });
  const log = JSON.parse(w.store.data.sv_audit_log);
  check('only the confirmed run at the head is dropped', log.length, 591);
  check('and it stopped at the first unconfirmed one', log[0].id, 'seed10');
}
{
  // 7. an unreadable confirmation set answers NO, never YES
  const rows = legacy(600).map((r) => Object.assign({}, r, { id: 'seed' + r.seq }));
  const w = auditWith(rows);
  w.store.data.sv_audit_backed = '{not json';
  w.api.logDoseAudit({ type: 'dose_calc' });
  check('a could-not-tell on "is it backed up" evicts nothing',
    JSON.parse(w.store.data.sv_audit_log).length, 601);
}
{
  // 8. the confirmation set stays bounded by the trail itself
  const w = auditWith([{ id: 'live1', type: 'x' }], ['live1', 'gone1', 'gone2']);
  w.api.svAuditMarkBacked('live1');
  check('ids no longer in the trail are pruned from the confirmation set',
    JSON.stringify(JSON.parse(w.store.data.sv_audit_backed).sort()), JSON.stringify(['live1']));
  check('a refusal, a timeout and a rejection all leave it unmarked -- '
    + 'svPushOne resolves null for each and only a truthy answer marks',
    /if\(res\) svAuditMarkBacked\(_id\);/.test(src), true);
}

console.log((fail ? 'FAILED' : 'ok') + '  sairnvet-audit-and-controlled: ' +
  pass + ' passed, ' + fail + ' failed');
if (fail) process.exit(1);
