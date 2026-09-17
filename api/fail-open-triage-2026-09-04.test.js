// api/fail-open-triage-2026-09-04.test.js
// REQUIREMENT: the twelve fail-open reads fixed on 2026-09-04 cannot quietly
//   come back, held at SOURCE level because deleting a guard leaves no
//   fail-open ternary for the shape checker to match -- measured by reverting
//   three fixes one at a time and watching the count not move
//
// Run: node api/fail-open-triage-2026-09-04.test.js
//
// The twelve fail-open reads fixed in the 2026-09-04 triage pass, held so they
// cannot quietly come back.
//
// ══ WHY A SOURCE-LEVEL TEST, STATED PLAINLY ═══════════════════════════════
// tools/fail_open_check.py finds the SHAPE `x.ok ? await x.json() : []`. It
// does NOT notice a guard being deleted: replacing `if (!jr.ok) { ...refuse }`
// with `if (false)` leaves no fail-open ternary to match, and the checker
// reports a clean run. That was measured, not assumed -- three fixes were
// reverted one at a time and the count never moved.
//
// So the checker guards against the shape RETURNING; this file guards against
// the refusals being REMOVED. Neither replaces the other, and neither is a
// behavioural drive: the handlers here sit behind licence and session gates,
// and the ones with dedicated behavioural suites already have them
// (dental-public, ledger, food-temp, append-only, duplicate-check).
//
// ══ WHAT EACH ONE WAS CLAIMING ════════════════════════════════════════════
// Every fix below replaced a FALSE STATEMENT, not merely a missing error:
//   * a patient's valid complaint link reported as "not valid"
//   * a family member told there are no visits scheduled
//   * patients recorded in a run summary as having no email on file
//   * a facility told to set a medication window it had already set
//   * a customer reported as having no accounting consent on record
//   * staff told a quote request "no longer exists"
//   * WIP and consolidation totals published from a partial read
//   * a warranty gate reporting tiers unavailable because it read no programs

'use strict';
const assert = require('assert');
const fs = require('fs');
const path = require('path');

let passed = 0;
function test(name, fn) {
  try { fn(); passed++; console.log('  ok - ' + name); }
  catch (e) { console.error('  FAIL - ' + name + '\n    ' + e.message); process.exitCode = 1; }
}

function src(rel) {
  return fs.readFileSync(path.join(__dirname, '..', rel), 'utf8').replace(/\r\n/g, '\n');
}
// Comments are stripped everywhere: every fix quotes the wording it replaced,
// so a raw match would find the explanation and pass on the strength of it.
function code(rel) {
  return src(rel).split('\n').filter((l) => !/^\s*(\/\/|\*|\/\*)/.test(l)).join('\n');
}

const CASES = [
  ['api/sairndental/public-complaint-thread.js',
   [/const e = new Error\('dnt_complaints token lookup read failed/, /e\.code = 'UPSTREAM'/],
   "a patient's valid complaint link must not report as invalid"],
  ['api/sairndental/complaint-respond.js',
   [/const e = new Error\('dnt_complaints lookup read failed/, /e\.code = 'UPSTREAM'/],
   'staff must not be told a complaint does not exist'],
  ['api/sairndental/send-reminder.js',
   [/e\.code = 'UPSTREAM'/, /read failed: HTTP/],
   'the reminder run must not record patients as having no email'],
  ['api/alf-alerts.js',
   [/return 'UNREADABLE'/, /This is not a missing policy/],
   'a facility must not be told to set a window it already set'],
  ['api/alf-alerts.js',
   [/SWEEP_READ_FAILED/],
   'the medication sweep must not report zero after checking nothing'],
  ['api/accounting.js',
   [/return \{ unreadable: true/, /STATE_UNREADABLE/, /not a statement that consent is absent/],
   'a customer must not be reported as having no consent on record'],
  ['api/sen-portal.js',
   [/does not mean there are no visits/],
   'a family member must not be told there are no visits'],
  ['api/sd-data.js',
   [/It has not been deleted -- try again/],
   'staff must not be told a quote request no longer exists'],
  ['api/sd-data.js',
   [/so no WIP figures were computed/],
   'WIP must not be published from a partial job read'],
  ['api/sd-data.js',
   [/so no consolidation was computed/],
   'consolidation must not attribute against an unread location list'],
  ['api/sd-data.js',
   [/so no tier availability was evaluated/],
   'the warranty gate must not run on an unread programs table'],
  ['api/sd-data.js',
   [/return \{ unavailable: true \};/],
   'the entity job filter must not silently drop unattributed rows'],
];

// ── HOW MANY CALL SITES EACH REPEATED MARKER GUARDS ───────────────────────
// MEASURED against the tree on 2026-09-17, not chosen: the four WIP sites are
// two call sites each guarding `!jr.ok` and `!Array.isArray`, and the same
// doubling explains the others. Anything not listed here is expected exactly
// once and is asserted as present rather than counted, which is the same thing.
//
// A NUMBER IN A TEST IS A THING THAT GOES STALE, so it fails in BOTH
// directions and says which: a guard removed and a call site added are
// different events and both deserve a person reading the diff.
const COUNTS = {
  '/so no WIP figures were computed/': 4,
  '/so no consolidation was computed/': 2,
  '/so no tier availability was evaluated/': 2,
  '/return \\{ unavailable: true \\};/': 3,
  '/does not mean there are no visits/': 2,
  '/SWEEP_READ_FAILED/': 4,
};

function main() {
  console.log('fail-open triage 2026-09-04: twelve refusals, held against removal');

  CASES.forEach(function (c) {
    const [rel, patterns, why] = c;
    test(why + '  [' + path.basename(rel) + ']', () => {
      const s = code(rel);
      patterns.forEach((rx) => {
        // ── EXISTENCE IS NOT ENOUGH WHERE THE MARKER REPEATS (2026-09-17) ──
        // FOUND BY THE NEGATIVE CONTROL, not by review. Several of these
        // messages appear at more than one call site -- "so no WIP figures
        // were computed" four times in sd-data.js, the visit message twice in
        // sen-portal.js -- and `rx.test(s)` is satisfied by ONE survivor. So
        // a mutation deleting a single guard left this suite GREEN: it was
        // holding "somebody still refuses somewhere", not "each of these call
        // sites refuses". The count is pinned where it is above one, and a
        // count that GROWS fails too: a new call site carrying this message
        // is a new place somebody has to check, not a free pass.
        const want = COUNTS[String(rx)];
        const got = (s.match(new RegExp(rx.source, 'g')) || []).length;
        if (want !== undefined) {
          assert.strictEqual(got, want,
            rel + ': expected ' + want + ' guarded site(s) matching ' + rx +
            ', found ' + got + '. A removed guard and an added call site both '
            + 'land here, and both need a person.');
        } else {
          assert.ok(got > 0, 'missing in ' + rel + ': ' + rx);
        }
      });
    });
  });

  test('the accounting unreadable check runs BEFORE the provisioned check', () => {
    // An unreadable state carries no `provisioned` field, so falling through
    // would report "the tables are not set up" -- one false reason swapped for
    // another. Order is the fix.
    const s = code('api/accounting.js');
    let i = s.indexOf('st.unreadable');
    let n = 0;
    while (i !== -1) {
      const prov = s.indexOf('!st.provisioned', i);
      assert.ok(prov > i, 'a provisioned check precedes its unreadable check');
      n++;
      i = s.indexOf('st.unreadable', i + 1);
    }
    assert.strictEqual(n, 2, 'expected both loadState call sites guarded, found ' + n);
  });

  test('no fixed site still carries the fail-open ternary', () => {
    const files = new Set(CASES.map((c) => c[0]));
    files.forEach((rel) => {
      const s = code(rel);
      const hits = s.match(/\.ok \? await [A-Za-z0-9_]+\.json\(\)(\.catch\(.*?\))? : \[\]/g) || [];
      assert.deepStrictEqual(hits, [],
        rel + ' still has ' + hits.length + ' fail-open read(s): ' + hits.join(' | '));
    });
  });

  test('the acceptance file parses and every entry carries a reason', () => {
    // load_accepted() used to swallow a malformed file and silently drop ALL
    // acceptances while reporting "accepted 0" -- the tool doing the exact
    // thing it exists to catch. It warns now; this makes sure the file it
    // reads is actually valid.
    const raw = fs.readFileSync(path.join(__dirname, '..', 'tools', 'fail_open_accepted.json'), 'utf8');
    const entries = JSON.parse(raw);
    const real = entries.filter((e) => e && e.file && e.var);
    // ── A FLOOR WITH FIVE ENTRIES OF SLACK IS NOT A CHECK (2026-09-17) ────
    // This was `>= 6` against eleven real entries, so up to five acceptances
    // could lose their `file` or `var` -- and with them their appearance in
    // this arm entirely -- while it stayed green. Same shape the item-83
    // independent review recorded against witness_countersign.js:477: an arm
    // that makes an uncovered case "visible" by means of a floor it is nowhere
    // near. Pinned exactly, and it fails upward too: a NEW acceptance is a new
    // fail-open somebody decided to keep, which is precisely the event this
    // file exists to put in front of a person.
    assert.strictEqual(real.length, 11,
      'the acceptance count moved: expected 11, found ' + real.length +
      '. An acceptance added or removed is a decision, not a detail.');
    real.forEach((e) => {
      assert.ok(e.reason && e.reason.length > 40,
        e.file + ' ' + e.var + ' has no substantive reason -- an acceptance nobody justified is not one');
    });
  });

  console.log('\n' + passed + ' assertions passed');
}

main();
