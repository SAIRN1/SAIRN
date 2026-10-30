// tests/sairnsenior_save_reentry.js
//
// REQUIREMENT: a second press of "Generate Claim" while the first press's
// claim write is still waiting on the server creates NO second claim -- and
// the hold is released once that write answers, is refused, rejects or throws.
//
// Run:  node tests/sairnsenior_save_reentry.js [path-to-sairnsenior.html]
//
// THE DEFECT (tools/reentry_hold_check.py, criteria 2026-10-30.cody-b69.4).
// generateClaim builds a claim under a NEW id (newId('CLM')), stores it, then
// AWAITS senData('write','sen_claims',...). Nothing in the handler refuses a
// visit that already has a claim, so a second call during that wait sends a
// second claim for the same visit -- a payer billed twice. In the page the
// Ready-to-bill row is normally re-rendered away before the await, but only
// when the local store write succeeds: st() returns false on a full or
// blocked localStorage, the row and its button stay live, and the second
// press goes through. The hold does not depend on that.
//
//   C1-C3  generateClaim   (one billing claim per visit)
//   Arm meanings: tests/lib/save_reentry_harness.js.
//
// No browser, no network. An extraction that fails exits 2.
// Exit: 0 all passed - 1 an arm FAILED - 2 COULD NOT RUN

'use strict';
const fs = require('fs');
const path = require('path');
const H = require('./lib/save_reentry_harness.js');

const FILE = process.argv[2] || path.join(__dirname, '..', 'sairnsenior.html');
const html = fs.readFileSync(FILE, 'utf8').replace(/\r\n/g, '\n');
const lift = H.makeLift(html, FILE);

let pass = 0, fail = 0, finished = false;
function check(name, cond, detail) {
  if (cond) { pass++; console.log('  ok   ' + name); }
  else { fail++; console.log('  FAIL ' + name + (detail ? '\n       ' + String(detail).slice(0, 400) : '')); }
}

let seq = 0;
const SPECS = [
  {
    id: 'C', name: 'generateClaim',
    ok: { id: 'x' }, refused: null,
    src: H.optional(html, /var senClaimGenerating\s*=\s*false;/) + '\n' + lift('async function generateClaim(visitId){'),
    fields: {},
    given: (write, box) => ({
      visits: () => [{ id: 'V-1', client_id: 'CL-1', client_name: 'Pat Client', status: 'completed', scheduled_date: '2026-10-20' }],
      clients: () => [{ id: 'CL-1', name: 'Pat Client', payer: 'medicaid' }],
      visitClockReversed: () => false,
      visitHours: () => 2,
      pcResolveRate: () => ({ status: 'applied', rate_per_hour: 30, contract_id: 'PC-1', reason: 'contract PC-1 in force.', requires_authorization: false }),
      pcStateForClient: () => 'XX',
      azResolve: () => ({ status: 'none', reason: 'no authorisation on file.' }),
      authorizations: () => [],
      newId: (p) => p + '-' + (++seq),
      claims: () => box.rows.slice(),
      st: (k, list) => { if (k === 'sen_claims') box.rows = list; return true; },
      senLastErr: {},
      senData: write,
      senWriteFail: () => ({ kept: false, text: 'Not saved.' }),
      fmt: (n) => '$' + n
    }),
    rows: (box) => box.rows.length,
    press: (ctx) => ctx.generateClaim('V-1')
  }
];

(async () => {
  for (const s of SPECS) {
    console.log(s.name);
    await H.drive({ check, id: s.id, name: s.name, mk: H.mkFor(s), ok: s.ok, refused: s.refused });
  }
  finished = true;
  console.log('\n' + (fail ? 'FAILED' : 'ok') + '  sairnsenior save re-entry: ' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})().catch((e) => { console.log('COULD NOT RUN: ' + e.stack); process.exit(2); });
// A run that ends with an arm still waiting (the IIFE unsettled) exits 0 in
// node with nothing printed. It must read as COULD NOT RUN.
process.on('exit', () => { if (!finished) { console.log('COULD NOT RUN: the run ended before its last arm'); process.exitCode = 2; } });
