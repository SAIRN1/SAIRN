// tests/sairnscape_save_reentry.js
//
// REQUIREMENT: a second press of a SAIRNscape quote sender, or of "Upload &
// Analyze", while the first press is still waiting creates NO second quote or
// photo record -- and the hold is released once the wait ends, whichever way.
//
// Run:  node tests/sairnscape_save_reentry.js [path-to-sairnscape.html]
//
// THE DEFECT (tools/reentry_hold_check.py, criteria 2026-10-30.cody-b69.4; the
// shape cody b64/b65 fixed in sairngrounds sendIrrZoneToQuote, sendWfToQuote
// and sendBoqToQuote). Four inline-wired async handlers each mint a NEW record
// per press -- a 'Q-'+Date.now() draft quote, or an SCPPH- progress photo --
// store it, and AWAIT a server write (and, for the photo, the AI call before
// it) while the button stays live. A second press during that wait filed a
// second draft quote, or a second copy of the same photo.
//
//   scpSendDesignToQuote   DQ  rec.quote_id is set only AFTER the quote write,
//                              so its own "Already sent" guard cannot see it.
//   scpSendIrrZoneToQuote  IZ
//   scpSendWfToQuote       WF
//   scpUploadProgressPhoto PA  (AI call pending)  PB  (photo write pending)
//                              scpPhotoB64 is cleared only at the very end.
//
// Arms <id>1-3, meanings in tests/lib/save_reentry_harness.js; <id>4 is the
// double press with NO refill between (below). Every handler
// stores locally BEFORE its write, so where a row exists a second row is the
// duplicate too.
//
// The functions are lifted from the shipped file by brace matching and run in
// a vm with stubs; no browser, no network. An extraction that fails exits 2.
// Exit: 0 all passed - 1 an arm FAILED - 2 COULD NOT RUN

'use strict';
const fs = require('fs');
const path = require('path');
const H = require('./lib/save_reentry_harness.js');

const FILE = process.argv[2] || path.join(__dirname, '..', 'sairnscape.html');
const html = fs.readFileSync(FILE, 'utf8').replace(/\r\n/g, '\n');

let pass = 0, fail = 0, finished = false;
function check(name, cond, detail) {
  if (cond) { pass++; console.log('  ok   ' + name); }
  else { fail++; console.log('  FAIL ' + name + (detail ? '\n       ' + String(detail).slice(0, 400) : '')); }
}

const L = H.makeLift(html, FILE);
// This file reaches the DOM through scp$ and reports through scpToast. Both
// are bound to the harness's own element getter and toast capture, so what
// the handler says is measured exactly as the harness measures $ and toast.
const SCP = 'var scp$ = $; var scpToast = toast;\n';
// THE REAL DOUBLE PRESS CANNOT RETYPE. H.drive refills the form before every
// press; a handler that clears its own inputs or source before its first
// await would refuse a real second press with no hold at all. <id>4 fills the
// form ONCE and presses twice with the wait held, so it shows the race exists
// in the shipped handler (red before the fix), not only in the harness.
async function noRefill(s) {
  const held = [];
  const w = H.mkFor(s)(() => new Promise((r) => held.push(r)));
  w.refill();
  const a = Promise.resolve().then(() => w.press());
  await H.flush();
  const b = Promise.resolve().then(() => w.press());
  await H.flush();
  const state = JSON.stringify({ writes: w.writes(), rows: w.rows ? w.rows() : undefined, toasts: w.toasts() });
  const one = w.writes() === 1 && (!w.rows || w.rows() === 1);
  held.forEach((r) => r(s.ok));
  await Promise.allSettled([a, b]); await H.settle();
  check(s.id + '4 ' + s.name + ': a real double press (form filled ONCE, no retyping) makes ONE record', one, state);
}
const lifted = (decl, name) =>
  SCP + H.optional(html, new RegExp('var ' + decl + '\\s*=\\s*false;')) + '\n' + L('async function ' + name + '(){');

(async () => {
  // 1. The quote senders. Each reads scp_quotes, appends a Draft, stores it,
  // then awaits scpData('write','scp_quotes',qrec).
  console.log('1. the quote senders: one draft quote at a time');
  const quoteWorld = (write, box) => ({
    scpLd: (k, d) => (k === 'scp_quotes' ? box.rows.slice() : (d || [])),
    scpSt: (k, list) => { if (k === 'scp_quotes') box.rows = list; return true; },
    scpDaysFromNow: () => '2026-11-29', scpData: write
  });
  const quoteSpec = (id, name, decl, fields) => ({
    id, name, fields,
    src: lifted(decl, name),
    given: quoteWorld, rows: (box) => box.rows.length, press: (ctx) => ctx[name](),
    ok: { id: 'x' }, refused: null
  });
  // scpSendDesignToQuote reads the open design walk. scpDesigns returns a
  // FRESH approved, unsent design on every read and scpSaveDesignRecord does
  // not persist it: the persisted rec.quote_id is the app's own guard AFTER a
  // send completes, and arms 2/3 measure the hold, not that guard. Arm 1 is
  // the real defect either way -- rec.quote_id is set only after the quote
  // write answers, so during that wait nothing the handler reads has changed.
  const designSpec = {
    id: 'DQ', name: 'scpSendDesignToQuote',
    src: lifted('scpDwQuoting', 'scpSendDesignToQuote'),
    given: (write, box) => Object.assign(quoteWorld(write, box), {
      scpDwid: 'DW-1',
      scpDesigns: () => [{
        id: 'DW-1', customer_id: 'C-1', approved: true, approved_by: 'Owner', approved_at: '2026-10-29',
        quote_id: null, elements: [{ type: 'sprinkler', label: 'Front bed' }, { type: 'plant', label: 'Maple' }]
      }],
      SCP_DW_TYPE_LABELS: { sprinkler: 'Sprinkler Head', no_dig: 'No-Dig Zone', plant: 'Landscape Element' },
      scpFdate: (d) => d, scpWriteRefused: () => false, scpPendingAdd: () => true,
      scpSaveDesignRecord: () => Promise.resolve(true), scpLastErrText: () => ''
    }),
    rows: (box) => box.rows.length, press: (ctx) => ctx.scpSendDesignToQuote(),
    ok: { id: 'x' }, refused: null
  };
  for (const s of [
    designSpec,
    quoteSpec('IZ', 'scpSendIrrZoneToQuote', 'scpIrrQuoting', { 'scp-izcustomer': 'C-1', 'scp-izname': 'Zone 3', 'scp-izchecklist': '4 rotors\n1 valve' }),
    quoteSpec('WF', 'scpSendWfToQuote', 'scpWfQuoting', { 'scp-wfcustomer': 'C-1', 'scp-wfname': 'Koi pond', 'scp-wfchecklist': '1 pump\n2 lights' })
  ]) {
    await H.drive({ check, id: s.id, name: s.name, mk: H.mkFor(s), ok: s.ok, refused: s.refused });
    await noRefill(s);
  }

  // 2. The progress photo. Two waits: the AI analysis (fetch), then the photo
  // record's write (scpData). The photo is stored only after the AI answers,
  // so during the AI wait there is no row to count -- the second AI call is
  // the duplicate there; during the write wait the second row is.
  console.log('2. the progress photo: one upload at a time, through both waits');
  const AI_OK = { json: () => Promise.resolve({ content: [{ text: 'Sod laid, edges cut clean.' }] }) };
  const AI_REFUSED = { json: () => Promise.resolve({ error: { message: 'rate limited' } }) };
  const photoSpec = (id, leg) => ({
    id, name: 'scpUploadProgressPhoto (' + leg + ' pending)',
    src: lifted('scpPhotoUploading', 'scpUploadProgressPhoto'),
    given: (write, box) => ({
      SCP_PROXY: '/api/claude', SCP_APP_ID: 'sairnscape', scpPhotoScheduleId: 'S-1',
      scpLd: (k, d) => (k === 'scp_schedule' ? [{ id: 'S-1', customer_id: 'C-1' }] : (d || [])),
      scpCustName: () => 'Acme', scpCurrentEmployeeLabel: () => 'Crew 2',
      bldScpProgressPhotos: () => box.rows.slice(),
      scpSt: (k, list) => { if (k === 'scp_progress_photos') box.rows = list; return true; },
      fetch: leg === 'AI call' ? write : () => Promise.resolve(AI_OK),
      scpData: leg === 'AI call' ? () => Promise.resolve({ id: 'x' }) : write
    }),
    // A photo is taken before every press: the handler clears scpPhotoB64
    // when it finishes.
    refill: (ctx) => { ctx.scpPhotoB64 = 'AAAA'; },
    rows: leg === 'AI call' ? undefined : (box) => box.rows.length,
    press: (ctx) => ctx.scpUploadProgressPhoto(),
    ok: leg === 'AI call' ? AI_OK : { id: 'x' }, refused: leg === 'AI call' ? AI_REFUSED : null
  });
  for (const s of [photoSpec('PA', 'AI call'), photoSpec('PB', 'photo write')]) {
    await H.drive({ check, id: s.id, name: s.name, mk: H.mkFor(s), ok: s.ok, refused: s.refused });
    await noRefill(s);
  }
  finished = true;
  console.log('\n' + (fail ? 'FAILED' : 'ok') + '  sairnscape save re-entry: ' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})().catch((e) => { console.log('COULD NOT RUN: ' + e.stack); process.exit(2); });
// A run that ends with an arm still waiting (the IIFE unsettled) exits 0 in
// node with nothing printed. It must read as COULD NOT RUN.
process.on('exit', () => { if (!finished) { console.log('COULD NOT RUN: the run ended before its last arm'); process.exitCode = 2; } });
