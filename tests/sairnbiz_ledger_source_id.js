// tests/sairnbiz_ledger_source_id.js
//
// Run:  node tests/sairnbiz_ledger_source_id.js
//
// SAIRNbiz's expense and bill postings, driven verbatim from sairnbiz.html.
//
// THE DEFECT. `saveExp()` built `exId='EX-'+String(Date.now()).slice(-6)`
// purely to fill `source_id` on the journal entry and NEVER wrote it onto the
// expense record. So every expense entry in the general ledger pointed at a
// string that matched nothing in `sb_exps`, and no entry could be traced back
// to the expense it came from. Every other posting in the file already used
// the record's own id (`r.id`, `pr.id`, `b.id`) -- this one was the odd one
// out, and it was odd in the direction that breaks an audit trail.
//
// `saveBill()` had the same shape one function down, which is why it is fixed
// and tested here rather than left for a follow-up. Its `blId` fell back to a
// minted 'BILL-...' whenever the invoice number was blank, and that string was
// never written onto the bill -- while the `bill_paid` entry for the SAME bill
// uses `b.id`, the real id `sbNormalizeBills()` assigns on the next render.
// Two entries for one bill, two different source ids, neither linkable to the
// other.
//
// WHY THE ID IS MINTED AT CREATION AND NOT LEFT TO sbEnsureIds(). That helper
// also mints an 'EX' id, but it runs inside the backup hook, behind a licence
// check and two availability flags (`sbSyncPaused`, `sbBackupUnavailable`).
// On an unlicensed or offline device it never runs -- and offline is exactly
// when the local ledger is the only copy. Asserted below by driving the real
// saveExp() with no licence in storage at all.

'use strict';
const fs = require('fs');
const path = require('path');

const HTML = path.join(__dirname, '..', 'sairnbiz.html');
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

// A store with no licence key in it, on purpose -- see the header.
function makeStore() {
  const data = {};
  return {
    data,
    store: {
      getItem: (k) => (k in data ? data[k] : null),
      setItem: (k, v) => { data[k] = v; }
    }
  };
}

// Fields the two modals read. Everything else is a stub whose only job is to
// not throw, so the two functions under test run their real bodies.
function build(fields, frozenNow) {
  const s = makeStore();
  const posted = [];
  const toasts = [];
  const els = {};
  Object.keys(fields).forEach((id) => { els[id] = { value: fields[id] }; });
  const FrozenDate = function () {};
  FrozenDate.now = () => frozenNow;

  const api = new Function(
    'localStorage', 'console', '$', 'toast', 'fmt', 'sbLocalToday',
    'closeExpModal', 'rExps', 'rDash', 'rPay', 'closeBillModal', 'rAP',
    'sbGlPost', 'SB_GL_EXPENSE_ACCOUNTS', 'Date',
    'var _sbSaveFailed={};\n' +
    fn('function st(k,v){') + '\n' +
    fn('function ld(k,d){') + '\n' +
    fn('function saveExp(){') + '\n' +
    fn('function saveBill(){') + '\n' +
    'return { saveExp: saveExp, saveBill: saveBill, ld: ld };'
  )(
    s.store, { warn: () => {} },
    (id) => els[id] || { value: '' },
    (m) => toasts.push(String(m)),
    (n) => '$' + n,
    () => '2026-09-04',
    () => {}, () => {}, () => {}, () => {}, () => {}, () => {},
    (entry) => posted.push(entry),
    { Materials: '5020', Tools: '5030' },
    FrozenDate
  );
  return { api, store: s, posted, toasts };
}

const EXP_FIELDS = {
  exdesc: 'Skil saw blades', examt: '240', exdate: '2026-09-04',
  excat: 'Materials', exvendor: 'Acme Supply', exded: 'Yes',
  exreceipt: 'r-1', exstatus: 'Paid'
};
const BILL_FIELDS = {
  blvendor: 'Acme Supply', blamt: '1200', blinv: '', bldate: '2026-09-04',
  bldue: '2026-10-04', blstatus: 'Open'
};

// ── an expense entry now points at a record that exists ───────────────────
{
  const w = build(EXP_FIELDS, 1788500000000);
  w.api.saveExp();
  const exps = w.api.ld('sb_exps', []);
  check('the expense was recorded', exps.length, 1);
  check('and it carries an id', typeof exps[0].id, 'string');
  check('exactly one journal entry was posted', w.posted.length, 1);
  check('and its source_id IS that record id -- not a parallel string',
    w.posted[0].source_id, exps[0].id);
  check('so the entry can be traced back by lookup',
    exps.filter((e) => e.id === w.posted[0].source_id).length, 1);
  check('the id uses the same scheme sbEnsureIds would have used',
    /^EX[0-9a-z]+-\d+$/.test(exps[0].id), true);
  check('the old orphan format is gone', /^EX-\d{6}$/.test(exps[0].id), false);
}

// ── the offline case, which is the reason it is minted at creation ────────
// There is no licence key in this store, so the backup hook returns before
// sbEnsureIds() and could not have supplied the id.
{
  const w = build(EXP_FIELDS, 1788500000000);
  w.api.saveExp();
  check('no licence is present, so the backup path cannot have run',
    w.api.ld('sb_lic', null), null);
  check('and the record still has its id', !!w.api.ld('sb_exps', [])[0].id, true);
}

// ── two saves in the same millisecond must not share an id ────────────────
{
  const w = build(EXP_FIELDS, 1788500000000);
  w.api.saveExp();
  w.api.saveExp();
  const exps = w.api.ld('sb_exps', []);
  check('both expenses were recorded', exps.length, 2);
  check('with different ids despite an identical clock',
    exps[0].id === exps[1].id, false);
  check('and each journal entry names its own',
    [w.posted[0].source_id, w.posted[1].source_id], [exps[0].id, exps[1].id]);
}

// ── an unmapped category still records, and still gets an id ──────────────
// The refusal to post to a nearby account is deliberate and stays; what must
// not happen is the record losing its identity because the posting was
// skipped.
{
  const w = build(Object.assign({}, EXP_FIELDS, { excat: 'Not A Mapped Category' }), 1788500000000);
  w.api.saveExp();
  const exps = w.api.ld('sb_exps', []);
  check('nothing was posted to the ledger', w.posted.length, 0);
  check('the operator was told why', /NOT posted to the ledger/.test(w.toasts.join(' ')), true);
  check('and the expense still has an id for when it is corrected',
    /^EX[0-9a-z]+-\d+$/.test(exps[0].id), true);
}

// ── a bill and its payment now name the same record ───────────────────────
{
  const w = build(BILL_FIELDS, 1788500000000);
  w.api.saveBill();
  const bills = w.api.ld('sb_ap', []);
  check('the bill was recorded', bills.length, 1);
  check('with no invoice number typed -- the case that used to orphan it',
    bills[0].inv, '');
  check('it carries an id in sbNormalizeBills\' own format',
    /^AP[0-9a-z]+-\d+$/.test(bills[0].id), true);
  check('the bill_received entry names that id',
    w.posted[0].source_id, bills[0].id);
  check('which is the SAME id the bill_paid path uses (b.id), so the two '
    + 'entries for one bill are linkable',
    /source_app:'sairnbiz',source_kind:'bill_paid',source_id:b\.id/.test(src), true);
  check('the minted BILL- string that was stored nowhere is gone',
    /'BILL-'\+String\(Date\.now\(\)\)/.test(src), false);
}

// ── an invoice number no longer decides the ledger key ────────────────────
// It stays on the record as the human handle. It is not the key, because it
// is optional and two vendors can issue the same one.
{
  const w = build(Object.assign({}, BILL_FIELDS, { blinv: 'INV-778' }), 1788500000000);
  w.api.saveBill();
  const bills = w.api.ld('sb_ap', []);
  check('the invoice number is kept on the record', bills[0].inv, 'INV-778');
  check('but the ledger keys on the record id, not on it',
    [w.posted[0].source_id === bills[0].id, w.posted[0].source_id === 'INV-778'],
    [true, false]);
}

console.log((fail ? 'FAILED' : 'ok') + '  sairnbiz-ledger-source-id: ' +
  pass + ' passed, ' + fail + ' failed');
if (fail) process.exit(1);
