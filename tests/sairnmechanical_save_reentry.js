// tests/sairnmechanical_save_reentry.js
//
// REQUIREMENT: a second press of "Add credential" or "Add asset" while the
// first press's server write is still in flight records NOTHING a second time
// -- and the hold is released once that write answers, is refused, rejects or
// throws.
//
// Run:  node tests/sairnmechanical_save_reentry.js [path-to-sairnmechanical.html]
//
// THE DEFECT (cody b64 re-entry sweep, fixed cody b65; the shape cody b63 fixed
// in saveDoc). mechCredAdd and mechAssetAdd send a record with a fresh
// client-made id and clear the form only after mechData answers. The button
// stayed live for that wait with every field still filled, so a second press
// sent the same technician credential, or the same site asset, again under a
// second id -- which the server takes as a second, separate record.
//
//   MC1-MC3  mechCredAdd
//   MA1-MA3  mechAssetAdd
//   Arm meanings: tests/lib/save_reentry_harness.js.
//
// No browser, no network. An extraction that fails exits 2.
// Exit: 0 all passed - 1 an arm FAILED - 2 COULD NOT RUN

'use strict';
const fs = require('fs');
const path = require('path');
const H = require('./lib/save_reentry_harness.js');

const FILE = process.argv[2] || path.join(__dirname, '..', 'sairnmechanical.html');
const html = fs.readFileSync(FILE, 'utf8').replace(/\r\n/g, '\n');
const lift = H.makeLift(html, FILE);

let pass = 0, fail = 0, finished = false;
function check(name, cond, detail) {
  if (cond) { pass++; console.log('  ok   ' + name); }
  else { fail++; console.log('  FAIL ' + name + (detail ? '\n       ' + String(detail).slice(0, 400) : '')); }
}

const OK = { status: 200, body: { ok: true } };
const REFUSED = { status: 409, body: { ok: false, error: { message: 'refused by the server' } } };
const SPECS = [
  {
    id: 'MC', name: 'mechCredAdd',
    src: H.optional(html, /var mechCredSaving\s*=\s*false;/) + '\n' + lift('window.mechCredAdd = function () {'),
    fields: { 'mc-tech': 'T-7', 'mc-type': 'nate', 'mc-has-expiry': 'false', 'mc-number': 'N-123' },
    given: (write) => ({ mechData: write }),
    press: (ctx) => ctx.mechCredAdd()
  },
  {
    id: 'MA', name: 'mechAssetAdd',
    src: H.optional(html, /var mechAssetSaving\s*=\s*false;/) + '\n' + lift('window.mechAssetAdd = function () {'),
    fields: { 'ma-id': '', 'ma-customer': 'Acme Foods', 'ma-type': 'rtu', 'ma-has-warranty': 'false', 'ma-serial': 'SN-9' },
    given: (write) => ({ mechData: write }),
    press: (ctx) => ctx.mechAssetAdd()
  }
];

(async () => {
  for (const s of SPECS) {
    console.log(s.name);
    await H.drive({ check, id: s.id, name: s.name, mk: H.mkFor(s), ok: OK, refused: REFUSED });
  }
  // 4. A FAILED WRITE IS SHOWN, NOT SWALLOWED (cc b73 R-12, 69c36d5ff). The
  // .then chain had no .catch: a mechData that rejected, or answered with no
  // response object, released the hold and told the user nothing, leaving an
  // unhandled rejection. The form's own error line must say it was not saved.
  console.log('a write that fails is reported');
  for (const s of SPECS) {
    for (const [label, push] of [
      ['REJECTS', () => Promise.reject(new Error('offline'))],
      ['answers with NO response', () => Promise.resolve(undefined)]
    ]) {
      const before = H.unhandled.length;
      const w = H.mkFor(s)(push);
      w.refill(); await Promise.resolve().then(() => w.press()).catch(() => {}); await H.settle();
      check(s.id + '4 ' + s.name + ': a write that ' + label + ' says it was not saved, and leaves no unhandled rejection',
        w.toasts().some((t) => /not saved/i.test(t)) && H.unhandled.length === before,
        JSON.stringify({ said: w.toasts(), unhandled: H.unhandled.length - before }));
    }
  }
  finished = true;
  console.log('\n' + (fail ? 'FAILED' : 'ok') + '  sairnmechanical save re-entry: ' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})().catch((e) => { console.log('COULD NOT RUN: ' + e.stack); process.exit(2); });
// A run that ends with an arm still waiting (the IIFE unsettled) exits 0 in
// node with nothing printed. It must read as COULD NOT RUN.
process.on('exit', () => { if (!finished) { console.log('COULD NOT RUN: the run ended before its last arm'); process.exitCode = 2; } });
