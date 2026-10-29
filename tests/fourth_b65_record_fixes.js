'use strict';
// tests/fourth_b65_record_fixes.js -- four defects the b64 worldwide audits
// found in records the apps already write, each lifted out of its real file
// and driven against stubs.
//   grounds  saveMsbHours / msbIsAlcoholSaleAllowedNow: a cleared day saved OPEN ALL DAY
//   build    awardSubBid: has awarded nothing since 66cf7b930 (2026-08-09)
//   cash     saveProfile: the hidden checkbox manufactured a "no" that hid the 110% warning;
//            calcRetirementEstimate: Solo 401(k) room was not capped at earnings
//   mech     saveQuote: the quote did not store its client
// Run: node tests/fourth_b65_record_fixes.js
const fs = require('fs');
const path = require('path');
const vm = require('vm');

let pass = 0, fail = 0;
function check(name, ok, detail) {
  if (ok) { pass++; console.log('  ok   ' + name); return; }
  fail++; console.log('  FAIL ' + name + (detail ? '\n         ' + detail : ''));
}
function lift(file, decl) {
  const src = fs.readFileSync(path.join(__dirname, '..', file), 'utf8');
  const i = src.indexOf(decl);
  if (i < 0) throw new Error(file + ': anchor no longer matches: ' + decl);
  let j = src.indexOf('{', i), d = 0;
  for (; j < src.length; j++) { if (src[j] === '{') d++; else if (src[j] === '}' && !--d) break; }
  return src.slice(i, j + 1);
}

(async () => {
  console.log('fourth b65 record fixes\n');

  // ── grounds ────────────────────────────────────────────────────────────
  {
    const vals = {}, toasts = []; let stored = null;
    const g = {
      MSB_DAY_LABELS: ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'],
      $: (id) => ({ value: vals[id] || '' }), toast: (m) => toasts.push(m), rMsbHours() {},
      st: (k, v) => { stored = v; return true; }, grdData: async () => true,
      bldMsbSaleHours: () => stored || [], Date,
    };
    vm.createContext(g);
    vm.runInContext(lift('sairngrounds.html', 'async function saveMsbHours(') + '\n' +
                    lift('sairngrounds.html', 'function msbIsAlcoholSaleAllowedNow('), g);
    for (let d = 0; d < 7; d++) { vals['msbhour-' + d + '-start'] = '10:00'; vals['msbhour-' + d + '-end'] = '22:00'; }
    const today = new Date().getDay();
    vals['msbhour-' + today + '-start'] = ''; vals['msbhour-' + today + '-end'] = '';
    await g.saveMsbHours();
    const row = stored && stored.find((h) => h.day === today);
    check('grounds: a day with BOTH fields cleared saves as closed', !!row && row.closed === true, JSON.stringify(row));
    check('grounds: ...and alcohol sales are refused on it, at any time of day',
          g.msbIsAlcoholSaleAllowedNow().allowed === false);
    stored = null; toasts.length = 0;
    vals['msbhour-' + today + '-start'] = '10:00';
    await g.saveMsbHours();
    check('grounds: exactly one field cleared is REFUSED, not guessed', stored === null && toasts.length === 1, JSON.stringify(toasts));
    vals['msbhour-' + today + '-start'] = '00:00'; vals['msbhour-' + today + '-end'] = '23:59';
    await g.saveMsbHours();
    check('grounds: CONTROL -- an explicit all-day window still allows a sale', g.msbIsAlcoholSaleAllowedNow().allowed === true);
  }

  // ── build ──────────────────────────────────────────────────────────────
  {
    let bids = [{ id: 'B1', job_id: 'J', cost_code: 'E', sub: 'Kessler', awarded: false },
                { id: 'B2', job_id: 'J', cost_code: 'E', sub: 'Voltline', awarded: true },
                { id: 'B3', job_id: 'J', cost_code: 'P', sub: 'Pipe Co', awarded: true }];
    let saved = null; const toasts = [];
    const b = {
      bldSubBids: () => JSON.parse(JSON.stringify(bids)), bldSubs: () => [], eligibleToBid: () => true,
      PREQUAL: {}, st: (k, v) => { saved = v; return true; }, rSubBids() {}, toast: (m) => toasts.push(m),
    };
    vm.createContext(b);
    vm.runInContext(lift('sairnbuild.html', 'function awardSubBid('), b);
    b.awardSubBid('B1');
    const by = (id) => saved && saved.find((x) => x.id === id);
    check('build: the awarded bid is marked awarded', !!by('B1') && by('B1').awarded === true, JSON.stringify(saved));
    check('build: ...the rival on the same job and cost code is un-awarded', !!by('B2') && by('B2').awarded === false);
    check('build: ...and a bid on another cost code is untouched', !!by('B3') && by('B3').awarded === true);
  }

  // ── cash ───────────────────────────────────────────────────────────────
  {
    const els = { profFilingStatus: { value: 'single' }, profPriorYearTax: { value: '12000' },
                  profPriorYearAgi: { value: '' }, profAgiOver150k: { checked: false },
                  profRetirementVehicle: { value: 'sep' } };
    let written = null;
    const c = {
      document: { getElementById: (id) => els[id] }, showToast() {}, profileCache: {},
      window: { _fbProfileRef: {}, _fbSetRaw: async (r, v) => { written = v; } },
      TAX_YEAR_2026: { sepCap: 72000, solo401kDeferral: 24500 }, Math, Number, isFinite,
    };
    vm.createContext(c);
    vm.runInContext(lift('sairncash.html', 'async function saveProfile(') + '\n' +
                    lift('sairncash.html', 'function priorYearAgiForCalc(') + '\n' +
                    lift('sairncash.html', 'function calcRetirementEstimate('), c);
    await c.saveProfile();
    check('cash: a user who never gave the old AGI answer is NOT saved as "no"',
          !!written && written.prior_year_agi_over_150k === null, JSON.stringify(written));
    c.profileCache = { prior_year_tax_liability: 12000, prior_year_agi_over_150k: null };
    check('cash: ...so the calculation still receives "AGI unknown" (the 110% warning path)',
          c.priorYearAgiForCalc() === null);
    c.profileCache = { prior_year_agi_over_150k: true };
    await c.saveProfile();
    check('cash: CONTROL -- a real legacy answer is still carried', written.prior_year_agi_over_150k === true);
    const seTax = 5000 * 0.9235 * 0.153;
    const r = c.calcRetirementEstimate(5000, seTax, 'solo401k');
    const earned = 5000 * 0.9235 - seTax / 2;
    check('cash: Solo 401(k) room at $5,000 profit is capped at what was earned',
          r.estimate <= earned + 1e-9 && r.estimate > 0, 'estimate ' + r.estimate + ' earned ' + earned);
    const hi = c.calcRetirementEstimate(400000, 400000 * 0.9235 * 0.029 + 176100 * 0.124, 'solo401k');
    check('cash: CONTROL -- at high profit the statutory cap still binds', hi.estimate === 72000, String(hi.estimate));
  }

  // ── mechanical ─────────────────────────────────────────────────────────
  {
    let q = null;
    const m = {
      APP_ID: 'mech', fqTrade: 'hvac', fqQuoteTxt: 'Replace condenser', Date, JSON,
      localStorage: { getItem: () => '[]' },
      document: { getElementById: (id) => (id === 'fq-client' ? { value: '  Acme Dental, 12 Main St ' } : null) },
      mechSt: (k, v) => { q = v; return true; }, mechBackup() {}, showToast() {},
    };
    vm.createContext(m);
    vm.runInContext(lift('sairnmechanical.html', 'function saveQuote('), m);
    m.saveQuote();
    check('mechanical: the saved quote names its client', !!q && q[0].client === 'Acme Dental, 12 Main St', JSON.stringify(q && q[0]));
  }

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})().catch((e) => { console.log('COULD NOT RUN: ' + e.message); process.exit(2); });
