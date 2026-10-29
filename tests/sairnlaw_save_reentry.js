// tests/sairnlaw_save_reentry.js
//
// REQUIREMENT: a second press of "Save as document" while the first press's
// server write is still in flight files NO second document on the matter --
// and the hold is released once that write answers, is refused, rejects or
// throws.
//
// Run:  node tests/sairnlaw_save_reentry.js [path-to-sairnlaw.html]
//
// THE DEFECT (cody b64 re-entry sweep, fixed cody b65). saveDraftAsDocument
// files the draft locally, then AWAITS the server write before it says
// anything. The button stayed live for that wait with the draft still in the
// box, so a second press filed the same AI draft on the matter again under a
// new document id, and synced it.
//
//   D1-D3  saveDraftAsDocument. Arm meanings: tests/lib/save_reentry_harness.js.
//
// No browser, no network. An extraction that fails exits 2.
// Exit: 0 all passed - 1 an arm FAILED - 2 COULD NOT RUN

'use strict';
const fs = require('fs');
const path = require('path');
const H = require('./lib/save_reentry_harness.js');

const FILE = process.argv[2] || path.join(__dirname, '..', 'sairnlaw.html');
const html = fs.readFileSync(FILE, 'utf8').replace(/\r\n/g, '\n');
const lift = H.makeLift(html, FILE);

let pass = 0, fail = 0, finished = false;
function check(name, cond, detail) {
  if (cond) { pass++; console.log('  ok   ' + name); }
  else { fail++; console.log('  FAIL ' + name + (detail ? '\n       ' + String(detail).slice(0, 400) : '')); }
}

let seq = 0;
const SPEC = {
  src: H.optional(html, /var lawDraftSaving\s*=\s*false;/) + '\n' + lift('async function saveDraftAsDocument(){'),
  fields: { draftmatter: 'M-1', draftresult: 'Dear counsel, ...' },
  given: (write, box) => ({
    newId: (p) => p + '-' + (++seq), lawLocalToday: () => '2026-10-29',
    matterDocs: () => box.rows.slice(), st: (k, list) => { box.rows = list; return true; },
    sdnData: write, lawWriteFailText: (r, f) => f
  }),
  // Filed locally BEFORE the write, so a second row is the duplicate too.
  rows: (box) => box.rows.length,
  press: (ctx) => ctx.saveDraftAsDocument()
};

(async () => {
  await H.drive({ check, id: 'D', name: 'saveDraftAsDocument', mk: H.mkFor(SPEC), ok: { id: 'x' }, refused: null });
  finished = true;
  console.log('\n' + (fail ? 'FAILED' : 'ok') + '  sairnlaw save re-entry: ' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})().catch((e) => { console.log('COULD NOT RUN: ' + e.stack); process.exit(2); });
// A run that ends with an arm still waiting (the IIFE unsettled) exits 0 in
// node with nothing printed. It must read as COULD NOT RUN.
process.on('exit', () => { if (!finished) { console.log('COULD NOT RUN: the run ended before its last arm'); process.exitCode = 2; } });
