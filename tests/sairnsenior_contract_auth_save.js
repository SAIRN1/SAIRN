// tests/sairnsenior_contract_auth_save.js
// Run: node tests/sairnsenior_contract_auth_save.js
//
// cody b35/b36 routed defect 8. CONCEPT: a write the server REFUSED is
// withdrawn from the device and named, so a contract or authorisation the
// server rejected never prices or authorises a claim; a write that got NO
// answer, or hit a table that is not set up, stays on the device and the toast
// says which -- never "the connection" when the server answered. A claim's
// pricing and authorisation message survive a failed save, and a claim with no
// contract still says something about authorisation.
//
//   (a) savePayerContract / saveAuthorization stored locally first and, on ANY
//       failure, said "server sync failed, try again with a connection" while
//       the local row kept pricing claims (payerContracts) and authorising
//       them (azResolve).
//   (b) generateClaim said nothing about authorisation when no contract
//       resolved, and a failed claim write replaced the whole message with the
//       device-only line.
//
// The functions are EXTRACTED BY NAME from the shipped sairnsenior.html and run
// in a vm; an extraction that fails REFUSES (exit 2) rather than testing a copy.
//
// Exit: 0 all passed - 1 an arm FAILED - 2 COULD NOT RUN

'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const FILE = process.argv[2] || path.join(__dirname, '..', 'sairnsenior.html');
const html = fs.readFileSync(FILE, 'utf8');
function grab(head, optional) {
  const i = html.indexOf(head);
  if (i < 0 && optional) return '';
  if (i < 0 || html.indexOf(head, i + 1) !== -1) {
    console.log('COULD NOT RUN: "' + head + '" found ' + (i < 0 ? 0 : 'more than one') + ' time(s) in ' + FILE);
    process.exit(2);
  }
  return html.slice(i, html.indexOf('\n}\n', i) + 2);
}
const SRC = [
  grab('function senLastErrText(resource){', false).split('\n')[0],
  grab('function senLastErrCode(resource){', false).split('\n')[0],
  grab('function senWriteFail(resource){', true),
  grab('async function savePayerContract(){'),
  grab('async function saveAuthorization(){'),
  // cody b70: generateClaim now holds on its own flag, declared beside it.
  (html.match(/var senClaimGenerating\s*=\s*false;/) || [''])[0],
  grab('async function generateClaim(visitId){'),
  grab('function readyToBillVisits(){'),
  grab('var SEN_SWEEP_ROW_CAP=').split('\n')[0],
  grab('async function senSweepLocalDrafts(serverRows){'),
].join('\n');

let pass = 0, fail = 0;
function check(name, cond, detail) {
  if (cond) { pass++; console.log('  ok   ' + name); }
  else { fail++; console.log('  FAIL ' + name + (detail ? '\n       ' + String(detail).slice(0, 300) : '')); }
}

const CONTRACT_FORM = { 'pc-rate': '30', 'pc-effective': '2026-01-01', 'pc-term': '', 'pc-state': 'OH', 'pc-payer': 'Medicaid',
  'pc-plan': 'Plan', 'pc-auth': 'true', 'pc-auth-note': '' };
const AUTH_FORM = { 'az-client': 'C1', 'az-number': 'A-77', 'az-units': '40', 'az-start': '2026-01-01', 'az-end': '2026-12-31',
  'az-code': 'T1019', 'az-basis': '15', 'az-active': 'true', 'az-notes': '' };

// outcome: 'ok' | {code, message} (server answered, refused) | 'network' (no answer)
function make(outcome, opts) {
  opts = opts || {};
  const store = Object.assign({ sen_payer_contracts: [], sen_authorizations: [], sen_claims: [],
    sen_clients: [{ id: 'C1', name: 'Ann', payer: 'Medicaid' }], sen_visits: [{ id: 'V1', client_id: 'C1', scheduled_date: '2026-03-02', status: 'completed' }] }, opts.store || {});
  const form = Object.assign({}, CONTRACT_FORM, AUTH_FORM, opts.form || {});
  const toasts = [];
  const ctx = {
    JSON, Object, Array, String, Number, Math, Boolean, isFinite,
    $: (id) => ({ value: form[id] !== undefined ? form[id] : '', checked: false, style: {} }),
    toast: (m) => toasts.push(String(m)),
    ld: (k, d) => (store[k] !== undefined ? JSON.parse(JSON.stringify(store[k])) : d),
    st: (k, v) => { store[k] = JSON.parse(JSON.stringify(v)); return true; },
    payerContracts: () => ctx.ld('sen_payer_contracts', []),
    authorizations: () => ctx.ld('sen_authorizations', []),
    clients: () => ctx.ld('sen_clients', []), visits: () => ctx.ld('sen_visits', []), claims: () => ctx.ld('sen_claims', []),
    newId: (p) => p + '-NEW', senLocalToday: () => '2026-10-21',
    closePcModal() {}, pcPaint() {}, closeAzModal() {}, azPaint() {},
    renderReadyToBill() {}, renderClaimsTable() {}, blRenderKpis() {},
    visitHours: () => 2, visitClockReversed: () => false, pcStateForClient: () => 'OH',
    pcResolveRate: () => opts.rate || { status: 'no_contract', reason: 'No contract for this payer on the service date.' },
    azResolve: () => opts.auth || { status: 'none', reason: 'no authorisation on file covers the service date.' },
    azBurnDown: () => ({ remaining: 10 }), fmt: (n) => '$' + n,
    pcEditId: opts.pcEditId || null, azEditId: opts.azEditId || null,
    senLastErr: Object.assign({}, opts.staleErr || {}),
    writes: 0,
    senData: (action, resource) => {
      if (action === 'write') ctx.writes++;
      if (outcome === 'ok') { delete ctx.senLastErr[resource]; return Promise.resolve({ ok: true }); }
      if (outcome === 'network') return Promise.resolve(null);
      ctx.senLastErr[resource] = { code: outcome.code, message: outcome.message };
      return Promise.resolve(null);
    },
  };
  vm.createContext(ctx);
  vm.runInContext(SRC, ctx);
  return { ctx, store, toasts };
}
const last = (t) => t.toasts[t.toasts.length - 1] || '';

(async () => {
  console.log('(a) payer contracts');
  let t = make({ code: 'INVALID_CONTRACT', message: 'sen_payer_contracts: rate_per_hour exceeds the cap' });
  await t.ctx.savePayerContract();
  check('C1. a REFUSED new contract is withdrawn from the device (cannot price claims)', t.store.sen_payer_contracts.length === 0, JSON.stringify(t.store.sen_payer_contracts));
  check('C2. ...the toast names the refusal and does not blame the connection',
    /refused/i.test(last(t)) && /exceeds the cap/.test(last(t)) && !/connection/i.test(last(t)), last(t));
  const OLD = { id: 'PC-1', payer: 'Medicaid', rate_per_hour: 25, effective_on: '2025-01-01', created_at: '2025-01-01' };
  t = make({ code: 'FORBIDDEN', message: 'Management only' }, { store: { sen_payer_contracts: [OLD] }, pcEditId: 'PC-1' });
  await t.ctx.savePayerContract();
  check('C3. a REFUSED edit restores the previous version, byte for byte', JSON.stringify(t.store.sen_payer_contracts) === JSON.stringify([OLD]), JSON.stringify(t.store.sen_payer_contracts));
  t = make({ code: 'NOT_PROVISIONED', message: 'That table is not set up yet — run sql/sairnsenior_payer_contracts_schema.sql in Supabase first.' });
  await t.ctx.savePayerContract();
  check('C4. an unprovisioned table keeps the device copy', t.store.sen_payer_contracts.length === 1);
  check('C5. ...and says the setup step, not the connection', /not set up/.test(last(t)) && /this device only/i.test(last(t)) && !/connection/i.test(last(t)), last(t));
  t = make('network');
  await t.ctx.savePayerContract();
  check('C6. NO answer keeps the device copy and says the server could not be reached',
    t.store.sen_payer_contracts.length === 1 && /could not be reached|connection/i.test(last(t)), last(t));
  t = make('network', { staleErr: { sen_payer_contracts: { code: 'INVALID_CONTRACT', message: 'old refusal' } } });
  await t.ctx.savePayerContract();
  check('C7. a STALE refusal from an earlier save does not turn a no-answer into a withdrawal',
    t.store.sen_payer_contracts.length === 1 && !/old refusal/.test(last(t)), last(t) + ' | ' + JSON.stringify(t.store.sen_payer_contracts));
  t = make('ok');
  await t.ctx.savePayerContract();
  check('C8. control: a saved contract stays and says saved', t.store.sen_payer_contracts.length === 1 && last(t) === 'Contract saved', last(t));

  console.log('(a) authorisations');
  t = make({ code: 'INVALID_AUTHORIZATION', message: 'units_authorized must be a whole number' });
  await t.ctx.saveAuthorization();
  check('A1. a REFUSED authorisation is withdrawn (cannot authorise claims)', t.store.sen_authorizations.length === 0, JSON.stringify(t.store.sen_authorizations));
  check('A2. ...named, not blamed on the connection', /refused/i.test(last(t)) && /whole number/.test(last(t)) && !/connection/i.test(last(t)), last(t));
  t = make({ code: 'NOT_PROVISIONED', message: 'That table is not set up yet.' });
  await t.ctx.saveAuthorization();
  check('A3. an unprovisioned table keeps it and says so', t.store.sen_authorizations.length === 1 && /not set up/.test(last(t)) && !/connection/i.test(last(t)), last(t));
  t = make('ok');
  await t.ctx.saveAuthorization();
  check('A4. control: saved', t.store.sen_authorizations.length === 1 && last(t) === 'Authorisation saved', last(t));

  console.log('(b) claims');
  t = make('ok');
  await t.ctx.generateClaim('V1');
  check('G1. no contract resolves: the message still says something about authorisation', /authori[sz]ation/i.test(last(t)), last(t));
  t = make({ code: 'ROW_REFUSED', message: 'the server refused the row' }, { rate: { status: 'applied', rate_per_hour: 30, reason: 'Contract PC-1.', requires_authorization: true, contract_id: 'PC-1' } });
  await t.ctx.generateClaim('V1');
  check('G2. a FAILED claim write keeps the pricing and authorisation message', /\$30\/hr/.test(last(t)) && /PRIOR AUTHORISATION IS REQUIRED/.test(last(t)), last(t));
  check('G3. ...and names the failure without blaming the connection', /refused the row/.test(last(t)) && !/connection/i.test(last(t)), last(t));
  // b59, H1 #1713: the refused draft used to STAY, so readyToBillVisits() counted V1 as billed and it left the list.
  check('G4. a REFUSED claim draft is withdrawn from the device', t.store.sen_claims.length === 0, JSON.stringify(t.store.sen_claims));
  check('G5. ...so its visit is back in Ready to bill', t.ctx.readyToBillVisits().map((v) => v.id).join() === 'V1');
  check('G6. ...and the biller is told it is back', /back in Ready to bill/.test(last(t)), last(t));
  t = make('network');
  await t.ctx.generateClaim('V1');
  check('G7. NO answer keeps the draft on the device (not a refusal), so the visit is not offered twice', t.store.sen_claims.length === 1 && t.ctx.readyToBillVisits().length === 0);
  t = make('ok');
  await t.ctx.generateClaim('V1');
  check('G8. control: a saved claim stays and its visit leaves Ready to bill', t.store.sen_claims.length === 1 && t.ctx.readyToBillVisits().length === 0);

  // b60: the sweep for drafts refused BEFORE b59, still on devices with their visits hidden.
  console.log('(c) local-only draft sweep');
  const DRAFT = { id: 'CLM-OLD', visit_id: 'V1', client_id: 'C1', status: 'draft' };
  t = make({ code: 'ROW_REFUSED', message: 'the server refused the row' }, { store: { sen_claims: [DRAFT] } });
  check('S0. control: the old draft hides V1 from Ready to bill before the sweep', t.ctx.readyToBillVisits().length === 0);
  let n = await t.ctx.senSweepLocalDrafts([]);
  check('S1. a local-only draft the server REFUSES on re-send is withdrawn', t.store.sen_claims.length === 0 && n === 1 && t.ctx.writes === 1, JSON.stringify(t.store.sen_claims));
  check('S2. ...so V1 is back in Ready to bill, and the biller is told', t.ctx.readyToBillVisits().map((v) => v.id).join() === 'V1' && /withdrawn/.test(last(t)), last(t));
  t = make('network', { store: { sen_claims: [DRAFT] } });
  await t.ctx.senSweepLocalDrafts([]);
  check('S3. NO answer keeps the draft (not a refusal) and says nothing', t.store.sen_claims.length === 1 && t.toasts.length === 0);
  t = make('ok', { store: { sen_claims: [DRAFT] } });
  n = await t.ctx.senSweepLocalDrafts([]);
  check('S4. an ACCEPTED re-send keeps the draft -- it is on the server now', t.store.sen_claims.length === 1 && t.ctx.writes === 1 && n === 1);
  t = make('ok', { store: { sen_claims: [DRAFT] } });
  await t.ctx.senSweepLocalDrafts([{ id: 'CLM-OTHER', visit_id: 'V1', status: 'submitted' }]);
  check('S5. the server already bills V1 under another claim: withdrawn WITHOUT a write (no double billing)',
    t.store.sen_claims.length === 0 && t.ctx.writes === 0, 'writes=' + t.ctx.writes + ' ' + JSON.stringify(t.store.sen_claims));
  t = make('ok', { store: { sen_claims: [DRAFT] } });
  await t.ctx.senSweepLocalDrafts([{ id: 'CLM-OLD', visit_id: 'V1', status: 'draft' }]);
  check('S6. a draft the server already holds is not re-sent', t.store.sen_claims.length === 1 && t.ctx.writes === 0);
  t = make({ code: 'ROW_REFUSED', message: 'x' }, { store: { sen_claims: [DRAFT] } });
  const full = Array.from({ length: 1000 }, (_, i) => ({ id: 'S' + i, visit_id: 'VX' + i }));
  await t.ctx.senSweepLocalDrafts(full);
  check('S7. a read AT the row cap proves no absence: nothing re-sent, nothing withdrawn', t.store.sen_claims.length === 1 && t.ctx.writes === 0);
  t = make({ code: 'ROW_REFUSED', message: 'x' }, { store: { sen_claims: [Object.assign({}, DRAFT, { status: 'submitted' })] } });
  await t.ctx.senSweepLocalDrafts([]);
  check('S8. only DRAFTS are swept -- a local-only submitted claim is left alone', t.store.sen_claims.length === 1 && t.ctx.writes === 0);

  console.log('\n' + (fail ? 'FAILED' : 'ok') + '  sairnsenior contract/auth save: ' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})().catch((e) => { console.log('HARNESS ERROR: ' + (e && e.stack || e)); process.exit(2); });
