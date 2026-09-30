// tests/sairnbiz_preview_fixes.js
// Run: node tests/sairnbiz_preview_fixes.js
//
// THE FOUR ANCHORED FINDINGS from docs/2026-09-29-sairnbiz-preview-check.md,
// each driven against the REAL sairnbiz.html rather than a paraphrase of it.
// Every function is extracted by name from the shipped file; an extraction that
// fails REFUSES rather than falling back to a copy, because a re-typed copy is a
// second source and this suite would then be testing the paraphrase.
//
// ══ A. THE SYNC LATCH -- and the root cause is NOT what the check reported ══
// The preview check reported "every save hits /api/ledger and 503s" and
// concluded nothing reaches the server. The 503 is real and it is NOT the
// reason. Reading the file settles it:
//
//   * sbBackupFetch() posts to DATA_API = /api/sd-data. The routing is correct.
//   * The nine collections that were empty server-side ARE provisioned --
//     re-read 2026-09-30, all answer provisioned: true.
//   * sbHydrateAll() reads all THIRTEEN SB_SYNCED resources at sign-in.
//     sb_incidents answers provisioned: false. sbReportHydrate() then sets
//     `sbBackupUnavailable = true` -- ONE GLOBAL BOOLEAN -- and
//     sbSyncCollection() returns early on it for EVERY resource thereafter.
//
// SO ONE UNPROVISIONED TABLE DISABLES THE BACKUP FOR TWELVE PROVISIONED ONES,
// at sign-in, before the user types anything. /api/ledger's 503 is a separate
// second-order posting and is orthogonal.
//
// The latch itself is deliberate and its reason is sound -- "nine collections
// times every record would otherwise be a burst of identical failures for one
// cause". What is wrong is its GRANULARITY.
//
// ══ B. PAYROLL IGNORES RECORDED HOURS ══════════════════════════════════════
// sbWeeklyHours() returns a flat 40 or 16 from employment_type. Marcus
// Thompson showed 80 h in payroll immediately after a timesheet recording 44 h,
// and the disclosure paragraph -- otherwise unusually candid -- does not say
// hours are assumed.
//
// ══ C. THE THREE-WAY MATCH CAN BE MADE UNREACHABLE ═════════════════════════
// PO vendor (#popvendor) and receipt vendor (#rcvvendor) are free-text inputs;
// the bill vendor (#blvendor) is a select restricted to registered vendors. A PO
// raised against an unregistered vendor can never have its bill entered.
//
// ══ D. ONE EMPTY MONTH, TWO ANSWERS ════════════════════════════════════════
// Expenses THIS MONTH renders $0 while LARGEST CATEGORY renders -- for the same
// empty month, a few pixels apart.

'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const FILE = path.join(__dirname, '..', 'sairnbiz.html');
const SRC = fs.readFileSync(FILE, 'utf8');

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('\n' + t); }

function extract(fnName) {
  const start = SRC.indexOf('function ' + fnName + '(');
  assert.ok(start !== -1, 'could not find function ' + fnName + ' in sairnbiz.html');
  let depth = 0, end = -1;
  for (let k = SRC.indexOf('{', start); k < SRC.length; k++) {
    if (SRC[k] === '{') depth++;
    else if (SRC[k] === '}') { depth--; if (depth === 0) { end = k; break; } }
  }
  assert.ok(end !== -1, 'unbalanced braces reading ' + fnName);
  return SRC.slice(start, end + 1);
}

console.log('SAIRNbiz: the four anchored preview-check findings\n');

// ══ A. THE SYNC LATCH ══════════════════════════════════════════════════════
section('A. one unprovisioned table must not disable the other twelve');

function latchSandbox(unprovisionedKeys) {
  // The real sbSyncCollection, plus the smallest environment it reads. Every
  // dependency is injected so the arm measures the function and not the page.
  const body = extract('sbSyncCollection');
  const attempted = [];
  const fn = new Function(
    '_sbSyncOn', 'sbSyncPaused', 'sbBackupUnavailable', 'sbUnprovisioned',
    'ld', 'sbEnsureIds', 'sbBackupFetch', 'console',
    body + '\nreturn sbSyncCollection;');
  const sandbox = fn(
    { sb_invs: true, sb_incidents: true, sb_exps: true },
    false,
    // THE LATCHED STATE. Before the fix this single boolean is what
    // sbReportHydrate() sets when ANY resource is unprovisioned.
    unprovisionedKeys.global,
    unprovisionedKeys.perResource || {},
    function () { return 'SB-TEST-2026'; },
    function () { },
    function (action, key, rec) {
      attempted.push(key + ':' + (rec && rec.id));
      return Promise.resolve({ ok: true });
    },
    { warn: function () { } });
  return { run: sandbox, attempted: attempted };
}

test('A1. THE DEFECT: with sb_incidents known unprovisioned, a write to a '
  + 'PROVISIONED collection is still attempted -- one missing table must not '
  + 'silence twelve', () => {
    const s = latchSandbox({ global: false,
                             perResource: { sb_incidents: true } });
    s.run('sb_invs', [{ id: 'INV-1', amt: 100 }], []);
    assert.ok(s.attempted.length > 0,
      'sb_invs was not pushed. If the unprovisioned latch is a single global '
      + 'boolean, sb_incidents answering provisioned:false at sign-in stops the '
      + 'backup for every other collection for the rest of the session -- which '
      + 'is the whole of blocker 2 in the preview check.');
  });

test('A1b. the GLOBAL latch is set only when EVERY synced resource is '
  + 'unprovisioned -- the fresh-database case the burst suppression was written '
  + 'for, and nothing narrower', () => {
    const body = extract('sbReportHydrate');
    assert.ok(body.indexOf('r.notProvisioned>=SB_SYNCED.length') !== -1
      || /notProvisioned\s*>=\s*SB_SYNCED\.length/.test(body),
      'sbReportHydrate does not gate the global latch on the full count, so one '
      + 'missing table can still set it');
    assert.ok(/sbUnprovisioned\[/.test(body),
      'sbReportHydrate does not record WHICH resources were unprovisioned, so '
      + 'the per-resource latch is never populated from the read path');
  });

test('A1c. ...and the warning NAMES the affected tables rather than saying "the '
  + 'server backup is not set up" -- that sentence was true of one table and '
  + 'read as true of thirteen, which is how this was misdiagnosed', () => {
    const body = extract('sbReportHydrate');
    assert.ok(/r\.missing/.test(body),
      'the warning does not name the affected resources');
    assert.ok(/SB_SYNCED\.length/.test(body),
      'the warning does not state the total, so one of thirteen reads as all');
  });

test('A1d. the READ path records the missing resources at all -- sbHydrateAll '
  + 'must return WHICH, not only how many', () => {
    const body = extract('sbHydrateAll');
    assert.ok(/missing/.test(body),
      'sbHydrateAll returns a count with no resource names, so the per-resource '
      + 'latch has nothing to populate from');
  });

test('A2. ...and a write to the collection that really IS unprovisioned is NOT '
  + 'attempted, so the fix is per-resource rather than a removed guard',
  () => {
    const s = latchSandbox({ global: false,
                             perResource: { sb_incidents: true } });
    s.run('sb_incidents', [{ id: 'INC-1' }], []);
    assert.strictEqual(s.attempted.length, 0,
      'sb_incidents was pushed even though it is known unprovisioned -- the '
      + 'burst of identical failures the latch exists to prevent');
  });

test('A3. CONTROL: an unchanged record is still not pushed, so A1 is not '
  + 'passing because the guard was deleted wholesale', () => {
    const s = latchSandbox({ global: false, perResource: {} });
    const rec = { id: 'INV-1', amt: 100 };
    s.run('sb_invs', [rec], [JSON.parse(JSON.stringify(rec))]);
    assert.strictEqual(s.attempted.length, 0,
      'an identical record was pushed; the unchanged-record skip is gone');
  });

test('A4. CONTROL: sbSyncPaused still stops everything -- seeding and hydration '
  + 'write back rows that came FROM the server and must not bounce', () => {
    const s = latchSandbox({ global: false, perResource: {} });
    // Re-build with sbSyncPaused true.
    const body = extract('sbSyncCollection');
    const attempted = [];
    const run = new Function(
      '_sbSyncOn', 'sbSyncPaused', 'sbBackupUnavailable', 'sbUnprovisioned',
      'ld', 'sbEnsureIds', 'sbBackupFetch', 'console',
      body + '\nreturn sbSyncCollection;')(
      { sb_invs: true }, true, false, {},
      function () { return 'SB-TEST-2026'; }, function () { },
      function (a, k, r) { attempted.push(k); return Promise.resolve({ ok: true }); },
      { warn: function () { } });
    run('sb_invs', [{ id: 'X' }], []);
    assert.strictEqual(attempted.length, 0, 'a paused sync still pushed');
  });

test('A5. the routing was never the defect: the writer posts to /api/sd-data, '
  + 'not to /api/ledger', () => {
    const f = extract('sbBackupFetch');
    assert.ok(/fetch\(DATA_API\b/.test(f),
      'sbBackupFetch does not post to DATA_API');
    assert.ok(!/LEDGER_API/.test(f),
      'sbBackupFetch references the ledger endpoint, which would make the '
      + 'preview check\'s routing theory correct after all');
    assert.ok(/DATA_API\s*=\s*'https:\/\/[^']*\/api\/sd-data'/.test(SRC),
      'DATA_API does not point at /api/sd-data');
  });

// ══ B. PAYROLL AND RECORDED HOURS ══════════════════════════════════════════
section('B. payroll must use recorded timesheet hours when there are any');

function hoursSandbox(tsRows) {
  const names = ['sbTsRows', 'sbWeeklyHours', 'sbRecordedWeeklyHours',
                 'sbWeeklyHoursIsAssumed'];
  const bodies = names.map((n) => {
    try { return extract(n); } catch (e) { return null; }
  });
  assert.ok(bodies[0] && bodies[1],
    'sbTsRows and sbWeeklyHours must both exist in sairnbiz.html');
  const missing = names.filter((n, i) => bodies[i] === null);
  const src = bodies.filter(Boolean).join('\n');
  const fn = new Function('ld', src
    + '\nreturn { weekly: sbWeeklyHours, recorded: '
    + (missing.indexOf('sbRecordedWeeklyHours') === -1
        ? 'sbRecordedWeeklyHours' : 'null')
    + ', assumed: '
    + (missing.indexOf('sbWeeklyHoursIsAssumed') === -1
        ? 'sbWeeklyHoursIsAssumed' : 'null')
    + ' };');
  const api = fn(function (key, dflt) {
    return key === 'sb_ts' ? tsRows : dflt;
  });
  api.missing = missing;
  return api;
}

// MARCUS'S CASE, VERBATIM FROM THE PREVIEW CHECK: 9/9/9/9/8 = 44 hours.
const MARCUS = { id: 'E-MARCUS', type: 'Full Time', rate: 28.50 };
const MARCUS_TS = [{ id: 'E-MARCUS|2026-09-28', emp: 'E-MARCUS',
                     week: '2026-09-28', hours: [9, 9, 9, 9, 8, 0] }];

test('B1. THE DEFECT, MARCUS\'S 44 HOURS: sbWeeklyHours returns the RECORDED '
  + 'hours, not a flat 40', () => {
    const s = hoursSandbox(MARCUS_TS);
    assert.deepStrictEqual(s.missing, [],
      'these helpers do not exist yet: ' + s.missing.join(', '));
    assert.strictEqual(s.weekly(MARCUS), 44,
      'sbWeeklyHours returned ' + s.weekly(MARCUS) + ' for an employee with a '
      + '44-hour timesheet on record. Payroll shows 80 h for the period off '
      + 'this, flat, for every full-timer.');
  });

test('B2. with NO timesheet on record it falls back to the schedule, and says '
  + 'the figure is ASSUMED', () => {
    const s = hoursSandbox([]);
    assert.strictEqual(s.weekly(MARCUS), 40,
      'the scheduled fallback changed; an employee with no hours recorded must '
      + 'not read as zero-hours');
    assert.strictEqual(s.assumed(MARCUS), true,
      'the figure is assumed and nothing says so -- which is the half of this '
      + 'finding the preview check singled out');
  });

test('B3. ...and with hours on record it is NOT reported as assumed', () => {
    const s = hoursSandbox(MARCUS_TS);
    assert.strictEqual(s.assumed(MARCUS), false);
  });

test('B4. a part-timer with no record still falls back to 16, not to 40', () => {
    const s = hoursSandbox([]);
    assert.strictEqual(s.weekly({ id: 'E-P', type: 'Part Time', rate: 18 }), 16);
  });

test('B5. the MOST RECENT week wins -- two weeks on record must not sum', () => {
    const s = hoursSandbox([
      { id: 'E-MARCUS|2026-09-21', emp: 'E-MARCUS', week: '2026-09-21',
        hours: [8, 8, 8, 8, 8, 0] },
      { id: 'E-MARCUS|2026-09-28', emp: 'E-MARCUS', week: '2026-09-28',
        hours: [9, 9, 9, 9, 8, 0] }
    ]);
    assert.strictEqual(s.weekly(MARCUS), 44,
      'got ' + s.weekly(MARCUS) + ' -- 84 would mean two weeks were added '
      + 'together, which would overstate every multi-week roster');
  });

test('B6. another employee\'s timesheet is not read as this one\'s', () => {
    const s = hoursSandbox([{ id: 'E-OTHER|2026-09-28', emp: 'E-OTHER',
                             week: '2026-09-28', hours: [9, 9, 9, 9, 8, 0] }]);
    assert.strictEqual(s.weekly(MARCUS), 40,
      'Marcus picked up E-OTHER\'s hours');
    assert.strictEqual(s.assumed(MARCUS), true);
  });

test('B7. a zero-hours week that was REALLY recorded is 0, not the schedule -- '
  + 'the timesheet panel\'s own note says a blank and a recorded zero are '
  + 'different facts', () => {
    const s = hoursSandbox([{ id: 'E-MARCUS|2026-09-28', emp: 'E-MARCUS',
                             week: '2026-09-28', hours: [0, 0, 0, 0, 0, 0] }]);
    assert.strictEqual(s.weekly(MARCUS), 0,
      'a recorded zero-hours week was replaced by the 40-hour schedule');
    assert.strictEqual(s.assumed(MARCUS), false);
  });

test('B8. the payroll row DISCLOSES an assumed hours figure, the way it already '
  + 'discloses an assumed pay frequency', () => {
    assert.ok(/sbWeeklyHoursIsAssumed\s*\(/.test(SRC),
      'nothing in the file asks whether the hours figure is assumed');
    // The row builder is the one that has to say it.
    const i = SRC.indexOf("$('py-gross')");
    assert.ok(i > 0, 'could not find the payroll row builder');
    const block = SRC.slice(Math.max(0, i - 4000), i);
    assert.ok(/sbWeeklyHoursIsAssumed/.test(block),
      'the payroll row does not consult sbWeeklyHoursIsAssumed, so an assumed '
      + 'figure renders identically to a recorded one');
  });

// ══ C. THE VENDOR FIELDS ═══════════════════════════════════════════════════
section('C. a PO must not be raisable against a vendor its bill cannot name');

function field(id) {
  const re = new RegExp('<(input|select)[^>]*id="' + id + '"', 'i');
  const m = SRC.match(re);
  assert.ok(m, 'could not find a form field with id="' + id + '"');
  return m[1].toLowerCase();
}

test('C1. THE DEFECT: the PO vendor field is the same KIND of control as the '
  + 'bill vendor field', () => {
    assert.strictEqual(field('popvendor'), field('blvendor'),
      'the PO vendor is a <' + field('popvendor') + '> and the bill vendor is a '
      + '<' + field('blvendor') + '>. A PO raised against an unregistered '
      + 'vendor can never have its bill entered, so the three-way match becomes '
      + 'unreachable for that PO.');
  });

test('C2. ...and so is the goods-receipt vendor field', () => {
    assert.strictEqual(field('rcvvendor'), field('blvendor'));
  });

// ONE FUNCTION, NOT THREE CALL SITES. Asserted on the FUNCTION rather than on a
// literal innerHTML assignment per id, which is what the first draft of this arm
// looked for: three selects filled in three places is three lists that come to
// disagree about which vendors exist, and a per-id literal check would pass for
// exactly that shape.
test('C3. all three are populated by ONE function reading ONE vendor list', () => {
    const body = extract('sbFillVendorSelects');
    ['blvendor', 'popvendor', 'rcvvendor'].forEach((id) => {
      assert.ok(body.indexOf(id) !== -1,
        id + ' is not filled by sbFillVendorSelects');
    });
    assert.ok(body.indexOf("ld('sb_vends'") !== -1,
      'the filler does not read the vendor store');
    assert.ok(body.indexOf('innerHTML') !== -1, 'the filler sets no options');
  });

test('C4. and the empty case SAYS SO rather than offering a blank dropdown', () => {
    const body = extract('sbFillVendorSelects');
    assert.ok(body.indexOf('No vendors on file') !== -1,
      'an empty vendor list renders as an empty dropdown with no explanation');
  });

test('C5. the filler runs when the AP panel paints, when the vendor list changes, '
  + 'AND when the bill modal opens -- a vendor added after load must reach all '
  + 'three dropdowns, or making them selects is a NEW way to make the match '
  + 'unreachable', () => {
    ['rAP', 'rVends', 'openBillModal'].forEach((fn) => {
      assert.ok(extract(fn).indexOf('sbFillVendorSelects()') !== -1,
        fn + ' does not refill the vendor selects');
    });
  });

// ══ D. ONE EMPTY MONTH, ONE ANSWER ═════════════════════════════════════════
section('D. the same empty month must not render two ways');

test('D1. THE DEFECT: the Expenses month figure and the largest-category figure '
  + 'agree on how an empty month looks', () => {
    const i = SRC.indexOf("$('ex-month').textContent");
    assert.ok(i > 0, 'could not find the expenses KPI writer');
    const line = SRC.slice(i, SRC.indexOf('\n', i));
    // Whatever the empty rendering is, BOTH must use it. The check is that the
    // month figure passes through the same dash-or-value helper the category
    // figure does, rather than formatting a raw 0.
    assert.ok(/sbEmptyOr|sbDashIfNone|SB_NO_DATA/.test(line),
      'the month figure is formatted directly rather than through the shared '
      + 'empty-state helper, so $0 and -- can disagree about the same month: '
      + line.trim().slice(0, 160));
  });

test('D2. ...and the empty markup in the panel matches it too, so the value '
  + 'before the first render agrees with the value after', () => {
    const m = SRC.match(/id="ex-month"[^>]*>([^<]*)</);
    assert.ok(m, 'could not read the ex-month initial value');
    const top = SRC.match(/id="ex-top"[^>]*>([^<]*)</);
    assert.ok(top, 'could not read the ex-top initial value');
    assert.strictEqual(m[1].trim(), top[1].trim(),
      'the panel ships ex-month as ' + JSON.stringify(m[1])
      + ' and ex-top as ' + JSON.stringify(top[1])
      + ' -- two cards a few pixels apart disagreeing before anything renders');
  });

console.log('\n' + (fail
  ? fail + ' FAILED, ' + pass + ' passed'
  : 'ALL ' + pass + ' SAIRNBIZ PREVIEW-FIX ASSERTIONS PASS'));
process.exit(fail ? 1 : 0);
