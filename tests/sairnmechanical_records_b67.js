'use strict';
// tests/sairnmechanical_records_b67.js -- fourth b67: the job, invoice and inspection
// records SAIRNmechanical never had. The save functions are lifted from the real file
// and driven against stubs; the server half drives the real api/sd-data.js handler.
// Run: node tests/sairnmechanical_records_b67.js
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const crypto = require('crypto');
let pass = 0, fail = 0;
function is(c, l, why) { if (c) { pass++; console.log('  ok   ' + l); } else { fail++; console.log('  FAIL ' + l + (why ? '\n         ' + why : '')); } }
const src = fs.readFileSync(path.join(__dirname, '..', 'sairnmechanical.html'), 'utf8');
function lift(decl) {
  const i = src.indexOf(decl); if (i < 0) throw new Error('anchor no longer matches: ' + decl);
  let j = src.indexOf('{', i), d = 0;
  for (; j < src.length; j++) { if (src[j] === '{') d++; else if (src[j] === '}' && !--d) break; }
  return src.slice(i, j + 1);
}

(async () => {
  console.log('sairnmechanical job / invoice / inspection records (fourth b67)\n');
  const store = {}, els = {}, backups = [], toasts = [];
  const el = (id) => (els[id] = els[id] || { value: '', innerHTML: '', style: {} });
  const c = {
    APP_ID: 'mech', JSON, Date, Number, String, Math, parseInt,
    localStorage: { getItem: (k) => (k in store ? store[k] : null) },
    document: { getElementById: el },
    mechSt: (k, v) => { store[k] = JSON.stringify(v); return true; },
    mechBackup: (r, rec) => { backups.push([r, rec]); return true; },
    showToast: (m) => toasts.push(m), window: { addEventListener() {} },
  };
  vm.createContext(c);
  vm.runInContext(['function mechRecId(', 'function mechRecList(', 'function mechRecVal(', 'function mechRecEsc(', 'function mechRecSave(',
    'function mechJobSave(', 'function mechInvoiceSave(', 'function mechInspectionSave(', 'function mechRenderRecords('].map(lift).join('\n'), c);

  is(c.mechJobSave() === false && backups.length === 0, 'a job with no customer is refused, nothing saved');
  el('mj-customer').value = 'Acme Dental'; el('mj-type').value = 'Install'; el('mj-status').value = 'scheduled';
  is(c.mechJobSave() === true, 'a job saves');
  const job = JSON.parse(store['mech_jobs'])[0];
  is(backups[0][0] === 'mech_jobs' && backups[0][1].id === job.id && job.customer === 'Acme Dental', '...locally and as ONE mech_jobs backup record');
  is(/Acme Dental/.test(el('mj-tbody').innerHTML) && /Acme Dental/.test(el('mi-job').innerHTML), '...and shows in the Jobs table and the invoice job picker');

  el('mi-customer').value = 'Acme Dental'; el('mi-amount').value = '0';
  is(c.mechInvoiceSave() === false, 'an invoice of $0 is refused');
  el('mi-amount').value = '1250.5'; el('mi-job').value = job.id;
  c.mechInvoiceSave(); c.mechInvoiceSave();
  const inv = JSON.parse(store['mech_invoices']);
  is(inv.length === 2 && inv[1].number === 'INV-0001' && inv[0].number === 'INV-0002', 'invoice numbers are SEQUENTIAL, even when minted in the same second', JSON.stringify(inv.map((x) => x.number)));
  is(inv[0].id !== inv[1].id, 'two invoices saved in the same moment get DIFFERENT record ids (the server upserts on them)');
  is(inv[0].amount === 1250.5 && inv[0].job_id === job.id && backups.filter((b) => b[0] === 'mech_invoices').length === 2, '...carry the job and amount, and back up as mech_invoices');

  is(c.mechInspectionSave() === false, 'an inspection with no equipment or inspector is refused');
  el('mx-asset').value = 'RTU-2 (Carrier 48TC)'; el('mx-tech').value = 'J. Ortiz'; el('mx-result').value = 'needs_repair'; el('mx-next').value = '2027-04-01';
  is(c.mechInspectionSave() === true, 'an inspection records');
  const ins = JSON.parse(store['mech_inspections'])[0];
  is(ins.result === 'needs_repair' && ins.next_due_on === '2027-04-01' && backups.slice(-1)[0][0] === 'mech_inspections', '...with its result and next-due date, backed up as mech_inspections');
  el('mx-asset').value = '<img src=x onerror=alert(1)>'; c.mechInspectionSave();
  is(!/<img/.test(el('mx-tbody').innerHTML), 'a field is escaped when rendered');
  is(!/mechNotLive\('Job entry'|mechNotLive\('Invoice entry'/.test(src), 'the two "not live" placeholders are gone');

  // ── server: the real handler accepts the three resources ─────────────────
  process.env[['SD', 'AUTH', 'SECRET'].join('_')] = 'b67-fixture-' + process.pid;
  process.env.SUPABASE_URL = 'https://fake.supabase.co'; process.env.SUPABASE_SERVICE_ROLE_KEY = 'k';
  const HASH = crypto.createHash('sha256').update('k').digest('hex');
  const lic = require.resolve('../api/_lib/license');
  require.cache[lic] = { id: lic, filename: lic, loaded: true, exports: { validateLicenseKey: async () => ({ valid: true, active: true, license_hash: HASH, app_id: 'sairnmechanical' }) } };
  const { signSessionToken } = require('../api/_lib/auth');
  const handler = require('../api/sd-data.js');
  const writes = [];
  global.fetch = async (u, init) => {
    if (/_employee_auth\?/.test(String(u))) return { ok: true, status: 200, headers: { get: () => '' }, json: async () => [{ employee_id: 'E1', role: 'owner', active: true, license_hash: HASH }], text: async () => '[]' };
    if (init && init.method === 'POST') { writes.push({ u: String(u), b: JSON.parse(init.body) }); return { ok: true, status: 201, headers: { get: () => '' }, json: async () => [JSON.parse(init.body)], text: async () => '[]' }; }
    return { ok: true, status: 200, headers: { get: () => '' }, json: async () => [], text: async () => '[]' };
  };
  for (const [resource, col, rec] of [['mech_jobs', 'job_id', job], ['mech_invoices', 'invoice_id', inv[0]], ['mech_inspections', 'inspection_id', ins]]) {
    writes.length = 0;
    const res = { s: 0, b: null, status(x) { this.s = x; return this; }, json(x) { this.b = x; return this; } };
    await handler({ method: 'POST', headers: { authorization: 'Bearer k', 'x-sd-auth': signSessionToken({ app: 'sairnmechanical', employee_id: 'E1', role: 'owner', license_hash: HASH }) },
      body: { action: 'write', resource, app_id: 'sairnmechanical', payload: rec } }, res);
    const w = writes.find((x) => x.u.indexOf('/' + resource + '?') !== -1);
    is(res.s === 200 && !!w && w.b[col] === String(rec.id), 'server: ' + resource + ' upserts keyed on ' + col, res.s + ' ' + JSON.stringify(res.b).slice(0, 200));
  }
  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})().catch((e) => { console.log('COULD NOT RUN: ' + (e && e.stack || e)); process.exit(2); });
