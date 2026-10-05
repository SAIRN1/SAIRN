// tests/sairnsenior_referral_hours.js
//
// Run:  node tests/sairnsenior_referral_hours.js
//       SEN_HTML=<mutated copy> node tests/sairnsenior_referral_hours.js
//
// THE REFERRAL SOURCES TABLE REPORTED 0.0 h FOR EVERY SOURCE, ALWAYS, AND IT
// LOOKED LIKE A MEASUREMENT.
//
// `rfDeliveredHoursFor(clientId)` read `v.actual_start` and `v.actual_end`. A
// `sen_visits` row has no such fields. The clock is `clock_in_at` /
// `clock_out_at` -- which the authorisation burn-down (~:2540), the visit card
// (~:2964) and `visitHours()` (~:3925) all use correctly. So the guard was true
// for every visit, the loop added nothing, and `rfPerformance()` handed the
// renderer a zero.
//
// ── WHY THE ZERO WAS WORSE THAN A BLANK ────────────────────────────────────
// The renderer already distinguishes the two: `p.linked ? p.hours.toFixed(1)+' h'
// : '--'`. An UNLINKED source correctly shows `--`, "we cannot attribute hours
// to this". A LINKED source showed `0.0 h`, which reads as "we looked, and this
// source's clients received no care". Against real clocked visits. That is the
// fabricated-KPI shape reached through a field name rather than through a
// hardcoded number, so Guardian's fabrication check could not see it.
//
// ── WHAT THESE ARMS HOLD, AND WHY THEY ARE NOT A GREP ─────────────────────
// The function is EXTRACTED AND DRIVEN in a vm sandbox against visit fixtures,
// so the arms measure the arithmetic and not the spelling. Arm B3 is the one
// that would have caught the original: a clocked visit must produce hours > 0.
// A source-scan arm asserting "the string clock_in_at appears" would have
// passed the moment somebody added a comment mentioning it.
//
// AND ONE ARM IS ABOUT THE FIELD NAMES ON PURPOSE (C1): the function must not
// read `actual_start`/`actual_end` at all, because those are the names that were
// there and are the ones a later edit copying an older revision would restore.
// tools/ghost_field_read_scan.py is the standing detector for that class; this
// arm is the local one, on the specific function.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const html = fs.readFileSync(process.env.SEN_HTML
  || path.join(__dirname, '..', 'sairnsenior.html'), 'utf8')
  .replace(/\r\n/g, '\n');
const { stripComments } = require('./lib/strip_comments.js');
// Shared stripper for the same reason tests/sairnsenior_cert_gate.js gives:
// three suites grew three versions in one day and all three were wrong
// differently. A naive one treats `accept="image/*"` as a comment start.
const codeOnly = stripComments(html);

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('\n' + t); }

function grab(sig, terminator) {
  const at = html.indexOf(sig);
  assert.ok(at > 0, 'not found in sairnsenior.html: ' + sig);
  const end = html.indexOf(terminator, at);
  assert.ok(end > at, 'terminator not found after ' + sig);
  return html.slice(at, end + terminator.length);
}

// The two functions under test, plus the helper the fix now shares.
function ctxFor(visitRows) {
  const src = [
    grab('function visitHours(v){', '\n}'),
    grab('function rfDeliveredHoursFor(clientId){', '\n}')
  ].join('\n\n');
  const ctx = {
    Object, Array, String, Number, Math, Date, JSON, isFinite,
    visits: () => visitRows,
    console: { log() {}, warn() {} }
  };
  ctx.globalThis = ctx;
  vm.createContext(ctx);
  vm.runInContext(src, ctx, { filename: 'sairnsenior-rfhours-extract.js' });
  return ctx;
}
function hours(visitRows, clientId) {
  return ctxFor(visitRows).rfDeliveredHoursFor(clientId);
}

// Two hours clocked, on the REAL field names.
const CLOCKED = { id: 'V1', client_id: 'C1',
                  clock_in_at: '2026-09-20T09:00:00Z',
                  clock_out_at: '2026-09-20T11:00:00Z' };
// Ninety minutes, same client.
const CLOCKED2 = { id: 'V2', client_id: 'C1',
                   clock_in_at: '2026-09-21T13:00:00Z',
                   clock_out_at: '2026-09-21T14:30:00Z' };
// Scheduled and never clocked. Must contribute nothing -- that is the rule the
// function's own comment states.
const UNCLOCKED = { id: 'V3', client_id: 'C1', scheduled_date: '2026-09-22',
                    scheduled_start: '09:00', scheduled_end: '12:00' };
// Another client's clocked visit. Must not leak across.
const OTHER = { id: 'V4', client_id: 'C2',
                clock_in_at: '2026-09-20T09:00:00Z',
                clock_out_at: '2026-09-20T17:00:00Z' };
// Clocked out BEFORE clocking in. visitHours USED to return a negative here;
// since 2026-10-05 it clamps to 0 at source and generateClaim refuses the row
// outright (tests/sairnsenior_negative_hours_claim.js). B6 below is unchanged
// and still passes: it was written as a FLOOR (`h >= 0`), not as an equality,
// so it asserts the property rather than the old implementation's value --
// which is why the clamp did not turn it red.
const BACKWARDS = { id: 'V5', client_id: 'C3',
                    clock_in_at: '2026-09-20T11:00:00Z',
                    clock_out_at: '2026-09-20T09:00:00Z' };

console.log('SAIRNsenior -- delivered hours per referral source are real clocked hours');

section('A. the helper the fix reuses');
test('A1. visitHours reads clock_in_at/clock_out_at and returns real hours', () => {
  assert.strictEqual(ctxFor([]).visitHours(CLOCKED), 2);
});
test('A2. ...and an unclocked visit is 0, not null and not a throw', () => {
  assert.strictEqual(ctxFor([]).visitHours(UNCLOCKED), 0);
});

section('B. rfDeliveredHoursFor, driven');
test('B1. THE ARM THAT WOULD HAVE CAUGHT IT: one clocked visit is 2 hours, '
  + 'not 0 -- the old version read actual_start and returned 0 for every '
  + 'client that ever existed', () => {
  assert.strictEqual(hours([CLOCKED], 'C1'), 2);
});
test('B2. two clocked visits add: 2h + 1.5h = 3.5h', () => {
  assert.strictEqual(hours([CLOCKED, CLOCKED2], 'C1'), 3.5);
});
test('B3. a SCHEDULED visit nobody clocked contributes nothing -- the rule the '
  + 'function\'s own comment states, now actually enforced', () => {
  assert.strictEqual(hours([CLOCKED, UNCLOCKED], 'C1'), 2);
});
test('B4. another client\'s hours do not leak in', () => {
  assert.strictEqual(hours([CLOCKED, OTHER], 'C1'), 2);
  assert.strictEqual(hours([CLOCKED, OTHER], 'C2'), 8);
});
test('B5. a client with no visits at all is 0 -- which is the ONE case where a '
  + 'zero is the true answer, and is why the defect was invisible', () => {
  assert.strictEqual(hours([CLOCKED], 'C9'), 0);
});
test('B6. clocked out before clocking in does not subtract from the total -- a '
  + 'negative delivered hour would quietly cancel a real visit', () => {
  const h = hours([BACKWARDS], 'C3');
  assert.ok(h >= 0, 'got ' + h + ' -- a negative total means one bad row can '
    + 'erase another visit\'s hours');
});

section('C. the field names, because those are what regressed');
test('C1. rfDeliveredHoursFor reads NEITHER actual_start NOR actual_end', () => {
  const at = codeOnly.indexOf('function rfDeliveredHoursFor(clientId){');
  assert.ok(at > 0, 'function not found in the stripped source');
  const body = codeOnly.slice(at, codeOnly.indexOf('\n}', at));
  assert.ok(!/actual_start|actual_end/.test(body),
    'the dead field names are back: ' + body.replace(/\s+/g, ' ').slice(0, 200));
});
test('C2. ...and it delegates to visitHours rather than carrying a third copy '
  + 'of the arithmetic, which is what visitHours\' own header asks for', () => {
  const at = codeOnly.indexOf('function rfDeliveredHoursFor(clientId){');
  const body = codeOnly.slice(at, codeOnly.indexOf('\n}', at));
  assert.ok(/visitHours\(/.test(body),
    'no call to visitHours -- a fourth copy of the clock arithmetic is how '
    + 'this diverged in the first place');
});
test('C3. CONTROL: visitHours itself still contains the clock arithmetic, so '
  + 'C2 is not satisfied by a helper that was emptied out', () => {
  const at = codeOnly.indexOf('function visitHours(v){');
  const body = codeOnly.slice(at, codeOnly.indexOf('\n}', at));
  assert.ok(/clock_in_at/.test(body) && /clock_out_at/.test(body)
    && /3600000/.test(body), body.replace(/\s+/g, ' ').slice(0, 200));
});

console.log('\n' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
