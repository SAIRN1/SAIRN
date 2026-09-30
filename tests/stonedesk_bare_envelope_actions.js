// tests/stonedesk_bare_envelope_actions.js
//
// REQUIREMENT: StoneDesk must not call an api/sd-data.js action whose success
//   response carries no `data` key through sdData(), which returns `j.data` --
//   such a caller receives `undefined` on every SUCCESS. If StoneDesk ever needs
//   one of those actions it needs a NAMED envelope transport first, the way
//   SAIRNroofing already has one.
//
// Run:  node tests/stonedesk_bare_envelope_actions.js
//
// ── THE ASYMMETRY THIS GUARDS, AND WHY NOTHING WAS BUILT ───────────────────
// sdData() ends with `return (action === 'write_batch') ? j : j.data;` -- one
// named action carved out of a rule, because write_batch's answer IS the
// envelope (`{ok, written, refused, skipped_without_id}`) and reading `j.data`
// handed back `undefined`. That carve-out was added 2026-09-26 after the
// batching fix reported every SUCCESSFUL save as a lost one.
//
// SIX MORE 200 RESPONSES IN api/sd-data.js CARRY NO `data` KEY, across five
// action names:
//
//   propose_clock_correction  sen_visits    -> {ok, entry}
//   issue                     rf_invoices   -> {ok, already_issued, invoice_*}
//   issue                     rf_invoices   -> {ok, invoice_number, issue_date…}
//   reconcile                 rf_claims     -> {ok, provisioned, worksheet}
//   preview_move              rf_schedule   -> {ok, preview}
//   set_status                rf_schedule   -> {ok, schedule_id, status}
//
// STONEDESK CALLS NONE OF THEM, so the asymmetry is LATENT here rather than
// live. Its two `'issue'` occurrences are a CATEGORY VALUE, not the action
// argument, which is why the detector below reads the first argument position of
// sdData() and not the bare string.
//
// AND SAIRNROOFING ALREADY SOLVED IT, THE OTHER WAY AND FOR ALL FOUR OF ITS
// REACHABLE ONES. sairnroofing.html carries two named transports: rfData()
// returns `d.data` and rfDataRaw() returns the whole envelope; `issue`,
// `reconcile_claim`, `preview_move` and `set_status` all go through rfDataRaw.
// The seam is named by WHAT IT RETURNS rather than by which action string is the
// exception, so a seventh data-less action costs nothing there and would cost a
// second carve-out here.
//
// DECIDED: NO BUILD NOW. StoneDesk calls none of the five, so a second transport
// today would be speculative. What is NOT acceptable is the asymmetry going live
// silently -- a future StoneDesk panel calling `set_status` through sdData()
// would get `undefined` on success, which is the exact shape of the defect
// write_batch already produced once. This file is the thing that notices.

'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const PAGE = fs.readFileSync(path.join(ROOT, 'stonedesk.html'), 'utf8');
const ENDPOINT = fs.readFileSync(path.join(ROOT, 'api', 'sd-data.js'), 'utf8');
const ROOFING = fs.readFileSync(path.join(ROOT, 'sairnroofing.html'), 'utf8');

// The five action names whose 200 carries no `data` key. Named, not derived:
// deriving them from the endpoint would mean this file's subject moves whenever
// the endpoint's response shapes move, and the point is to notice a STONEDESK
// caller appearing against a fixed list. D1 re-checks the list against the
// endpoint so a name that stops being data-less is reported rather than guarded
// forever.
const DATA_LESS = ['propose_clock_correction', 'issue', 'reconcile',
                   'preview_move', 'set_status'];

// The transports that return the whole envelope and are therefore safe for
// these actions. sdData() is NOT one of them.
const ENVELOPE_TRANSPORTS = ['sdDataRaw', 'sdDataEnvelope'];

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('\n' + t); }

// THE DETECTOR, one definition, used by the real arm and by both known-bad arms.
// Reads the FIRST ARGUMENT POSITION of a transport call, so a category value or
// a status string that happens to spell one of the names is not a hit.
function callsOf(src, transport) {
  const out = [];
  const rx = new RegExp('\\b' + transport + '\\(\\s*([\'"])([\\w]+)\\1', 'g');
  const lines = src.split('\n');
  for (let i = 0; i < lines.length; i++) {
    let m;
    rx.lastIndex = 0;
    while ((m = rx.exec(lines[i])) !== null) {
      out.push({ line: i + 1, action: m[2] });
    }
  }
  return out;
}

(function () {
  console.log('StoneDesk -- no caller of a data-less action through the '
            + 'payload-unwrapping transport');

  section('A. THE GUARD');

  test('A1. NO sdData() call in stonedesk.html names one of the five actions '
    + 'whose 200 carries no `data` key. Such a caller receives `undefined` on '
    + 'every SUCCESS -- the same shape write_batch produced when it reported '
    + 'every saved customer as lost',
    function () {
      const bad = callsOf(PAGE, 'sdData')
        .filter(function (c) { return DATA_LESS.indexOf(c.action) > -1; });
      assert.deepStrictEqual(bad.map(function (c) {
        return 'stonedesk.html:' + c.line + " sdData('" + c.action + "')";
      }), [], 'these actions answer with no data key and would be read as '
        + 'undefined-on-success. Add a named envelope transport first -- '
        + 'sairnroofing.html\'s rfDataRaw() is the precedent:\n       '
        + bad.map(function (c) {
            return 'stonedesk.html:' + c.line + "  sdData('" + c.action + "')";
          }).join('\n       '));
    });

  test('A2. ...and if a named envelope transport is ever added, THIS ARM MUST '
    + 'MOVE WITH IT: a call to one of the five through sdDataRaw() or '
    + 'sdDataEnvelope() is allowed and is not counted above. Recorded as an arm '
    + 'so the exemption is explicit rather than a gap',
    function () {
      const present = ENVELOPE_TRANSPORTS.filter(function (t) {
        return new RegExp('function\\s+' + t + '\\s*\\(').test(PAGE);
      });
      const viaEnvelope = present.reduce(function (n, t) {
        return n + callsOf(PAGE, t)
          .filter(function (c) { return DATA_LESS.indexOf(c.action) > -1; })
          .length;
      }, 0);
      console.log('       (envelope transports defined in stonedesk.html: '
        + (present.length ? present.join(', ') : 'none yet')
        + '; data-less calls through them: ' + viaEnvelope + ')');
      assert.ok(true);
    });

  section('B. THE KNOWN-BAD CONTROLS, on the same detector');

  test('B1. a synthetic StoneDesk caller IS detected -- '
    + "`var r = await sdData('set_status', 'sd_schedule', p);`",
    function () {
      const synthetic = "    var r = await sdData('set_status', 'sd_schedule', p);";
      const hits = callsOf(synthetic, 'sdData')
        .filter(function (c) { return DATA_LESS.indexOf(c.action) > -1; });
      assert.strictEqual(hits.length, 1,
        'the detector misses the exact call A1 exists to catch');
      assert.strictEqual(hits[0].action, 'set_status');
    });

  test('B2. THE FALSE-POSITIVE HALF, and this one is real in the file: '
    + "StoneDesk's two `'issue'` occurrences are a CATEGORY VALUE, not the "
    + 'action argument. A detector matching the bare word would fail A1 today '
    + 'and the guard would be turned off as noise',
    function () {
      const decoys = [
        "      var cat = 'issue';",
        "      opts.push({ value: 'issue', label: 'Issue' });",
        "      if (row.category === 'issue') n++;",
        "      var s = await sdData('write', 'issues', { status: 'set_status' });"
      ].join('\n');
      const hits = callsOf(decoys, 'sdData')
        .filter(function (c) { return DATA_LESS.indexOf(c.action) > -1; });
      assert.deepStrictEqual(hits, [],
        'the detector matched a value rather than the action argument: '
        + JSON.stringify(hits));
      // ...and the real file must genuinely contain such a decoy, or B2 is
      // testing a hypothetical.
      assert.ok(/'issue'/.test(PAGE),
        "stonedesk.html no longer contains the word 'issue' at all, so B2 is "
        + 'guarding against a false positive that can no longer occur -- '
        + 're-derive whether this arm still has a subject');
    });

  test('B3. and the detector does find a REAL sdData call in the page, so A1 is '
    + 'not passing because the regex matches nothing at all',
    function () {
      const all = callsOf(PAGE, 'sdData');
      assert.ok(all.length > 20,
        'only ' + all.length + " sdData('<action>') calls found in "
        + 'stonedesk.html -- the call style changed and A1 is now vacuous');
    });

  section('C. THE PRECEDENT IS REAL, not an argument');

  test('C1. sairnroofing.html defines BOTH transports -- rfData() returning '
    + 'd.data and rfDataRaw() returning the envelope. This is the evidenced '
    + 'alternative to a second carve-out, and if it disappears the '
    + '"no build now" decision rests on nothing',
    function () {
      assert.ok(/function rfData\(action,resource,payload\)/.test(ROOFING),
        'rfData() is gone');
      assert.ok(/function rfDataRaw\(action,resource,payload\)/.test(ROOFING),
        'rfDataRaw() is gone -- the precedent this decision cites no longer '
        + 'exists');
    });

  test('C2. and SAIRNroofing routes its data-less actions through rfDataRaw, '
    + 'not rfData. If it stopped doing that, the precedent is not a precedent',
    function () {
      const raw = callsOf(ROOFING, 'rfDataRaw')
        .filter(function (c) { return DATA_LESS.indexOf(c.action) > -1
                                   || c.action === 'reconcile_claim'; })
        .map(function (c) { return c.action; });
      const plain = callsOf(ROOFING, 'rfData')
        .filter(function (c) { return DATA_LESS.indexOf(c.action) > -1
                                   || c.action === 'reconcile_claim'; })
        .map(function (c) { return 'rfData(' + c.action + ')@' + c.line; });
      console.log('       (through rfDataRaw: ' + (raw.join(', ') || 'none')
        + ')');
      assert.ok(raw.length >= 3,
        'SAIRNroofing routes only ' + raw.length + ' data-less action(s) '
        + 'through rfDataRaw; the precedent was four');
      assert.deepStrictEqual(plain, [],
        'SAIRNroofing now reads a data-less action through the unwrapping '
        + 'transport: ' + plain.join(', '));
    });

  section('D. THE LIST IS STILL THE RIGHT LIST');

  test('D1. every action on DATA_LESS still has at least one 200 response in '
    + 'api/sd-data.js with no `data` key. A name that stopped being data-less '
    + 'would be guarded here forever for no reason, and this arm is what says '
    + 'so rather than leaving a stale list in place',
    function () {
      const lines = ENDPOINT.split('\n');
      const stale = [];
      DATA_LESS.forEach(function (act) {
        let found = false;
        for (let i = 0; i < lines.length && !found; i++) {
          if (lines[i].indexOf("action === '" + act + "'") === -1) continue;
          for (let j = i; j < Math.min(lines.length, i + 140); j++) {
            const r = /res\.status\(200\)\.json\((\{.*)/.exec(lines[j]);
            if (!r) continue;
            const body = r.group === undefined ? r[1] : r[1];
            if (/\bok:\s*true/.test(body) && !/\bdata\s*:/.test(body)) {
              found = true; break;
            }
          }
        }
        if (!found) stale.push(act);
      });
      assert.deepStrictEqual(stale, [],
        'these no longer have a data-less 200 and should come off DATA_LESS: '
        + stale.join(', '));
    });

  test('D2. and write_batch is still the ONE carve-out in sdData(). A second '
    + 'one appearing is the thing this file exists to make visible -- it means '
    + 'somebody chose a second exception over a named transport',
    function () {
      const m = /return \(action === 'write_batch'\) \? j : j\.data;/.test(PAGE);
      assert.ok(m, 'sdData no longer ends with the single write_batch '
        + 'carve-out -- read the new ending and re-derive whether A1 still '
        + 'describes the risk');
      const carveOuts = (PAGE.match(/action === '\w+'\) \? j : j\.data/g) || []);
      assert.strictEqual(carveOuts.length, 1,
        'more than one carve-out now: ' + JSON.stringify(carveOuts));
    });

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
