// tests/stonedesk_damage_no_twin.js
//
// Run:  node tests/stonedesk_damage_no_twin.js
//
// STONEDESK CARRIED TWO COMPLETE DAMAGE-CLAIM SYSTEMS, AND BOTH WROTE THE
// SAME ELEMENT.
//
//   live   -- an IIFE on the `sd_damage` key, feeding #dmg-open,
//             #dmg-total-cost, #dmg-recovered, #dmg-ytd, rendering #dmg-list
//   orphan -- dmgAddClaim / dmgSave / dmgSetFilter / dmgUpdateStatus /
//             dmgDelete / dmgRender on `sd_damage_claims`, feeding
//             #dmg-kpi-* (ids that never existed) -- and rendering #dmg-list
//
// Nothing called the orphan, so nothing was broken. That is not the same as
// safe. Wiring up any one of those six -- dmgSetFilter() looks like it
// belongs on the panel's filter tabs -- would have rendered the orphan's own
// empty store over the live claim list, and a shop would watch its damage
// claims vanish on a filter click. It read four ids the live panel really has
// (#dmg-job, #dmg-type, #dmg-fault, #dmg-desc) next to eight that do not
// exist, so it looked wired enough for someone to finish connecting.
//
// A DORMANT TWIN THAT SHARES AN OUTPUT ELEMENT IS NOT DORMANT. It is one
// onclick away from being live, and that is why the orphan was deleted rather
// than left quarantined by name. The same shape was found and removed twice
// before in this file -- the NPS twin, and the TRAINING twin whose tombstone
// sits directly below this one's.
//
// This file exists so it cannot come back and so the deletion cannot be
// mistaken for the removal of the live panel: section 2 asserts the live
// module is intact, and section 3 asserts it is the ONLY writer of #dmg-list.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const ROOT = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(ROOT, 'stonedesk.html'), 'utf8').replace(/\r\n/g, '\n');

// COMMENTS STRIPPED, and it matters more here than usual: the tombstone left
// in place of the orphan NAMES every symbol it removed, so a check that reads
// prose as code would report the twin as still present forever.
const code = html.split('\n')
  .map((l) => l.replace(/^(\s*)\/\/.*$/, '$1'))
  .join('\n');

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   - ' + name); pass++; }
  catch (e) { console.log('  FAIL - ' + name + '\n         ' + e.message); fail++; }
}
function section(t) { console.log('\n' + t); }

// ═══════════════════════════════════════════════════════════════════════════
section('1. the orphan is gone from executable code');

const ORPHAN_SYMBOLS = ['dmgAddClaim', 'dmgSave', 'dmgSetFilter', 'dmgUpdateStatus',
  'dmgDelete', 'dmgRender', 'dmgClaims', 'dmgFilter'];

ORPHAN_SYMBOLS.forEach((sym) => {
  test('no code reference to ' + sym, () => {
    const hits = (code.match(new RegExp('\\b' + sym + '\\b', 'g')) || []).length;
    assert.strictEqual(hits, 0, sym + ' appears ' + hits + ' time(s) in code');
  });
});

test('the sd_damage_claims key exists nowhere in code', () => {
  assert.strictEqual((code.match(/sd_damage_claims/g) || []).length, 0);
});

test('the orphan-only ids are gone with it', () => {
  // These were referenced by the orphan and by nothing else, which is why
  // missing_dom_target_check reported them. Removing the code removes them
  // from that report: 149 -> 137 missing targets, exactly these twelve.
  ['dmg-kpi-open', 'dmg-kpi-cost', 'dmg-kpi-pending', 'dmg-kpi-resolved',
   'dmg-cust', 'dmg-date', 'dmg-cost', 'dmg-mat', 'dmg-assigned',
   'dmg-status', 'dmg-resolution', 'dmg-form'].forEach((id) => {
    assert.strictEqual((code.match(new RegExp("'" + id + "'", 'g')) || []).length, 0,
      id + ' is still referenced in code');
  });
});

test('a tombstone was left, naming what went and why', () => {
  // The convention this file already follows for the TRAINING and NPS twins.
  // A silent deletion invites the next session to rebuild it.
  const at = html.indexOf('// DAMAGE CLAIMS -- orphaned duplicate removed');
  assert.ok(at > 0, 'no tombstone comment where the orphan was');
  const tomb = html.slice(at, at + 2000);
  assert.ok(/sd_damage_claims/.test(tomb), 'the tombstone does not name the orphan key');
  assert.ok(/dmg-list/.test(tomb), 'the tombstone does not name the shared element');
});

// ═══════════════════════════════════════════════════════════════════════════
section('2. the LIVE damage panel is untouched');

test("the live module still loads and saves the sd_damage key", () => {
  assert.ok(/localStorage\.getItem\('sd_damage'\)/.test(code), 'the live load is gone');
  assert.ok(/st\('sd_damage',\s*d\)/.test(code), 'the live save is gone');
});

test('its four KPI ids are still written', () => {
  ['dmg-open', 'dmg-total-cost', 'dmg-recovered', 'dmg-ytd'].forEach((id) => {
    assert.ok(code.indexOf("getElementById('" + id + "')") > -1,
      'the live module no longer writes #' + id);
    assert.ok(html.indexOf('id="' + id + '"') > -1, '#' + id + ' is no longer in the markup');
  });
});

test('the damage panel and its list element still exist', () => {
  assert.ok(html.indexOf('id="panel-damage"') > -1, 'panel-damage is gone');
  assert.ok(html.indexOf('id="dmg-list"') > -1, '#dmg-list is gone');
});

// ═══════════════════════════════════════════════════════════════════════════
section('3. exactly ONE writer of #dmg-list -- the whole point');

test('#dmg-list is written from one place in code', () => {
  const writers = (code.match(/getElementById\('dmg-list'\)/g) || []).length;
  assert.strictEqual(writers, 1,
    '#dmg-list has ' + writers + ' code writers. Two systems rendering one '
    + 'element is exactly the defect this file exists to prevent: whichever '
    + "runs last wins, and one of them reads a store the panel's own form "
    + 'never writes.');
});

test('and that writer is the sd_damage one, not a second store', () => {
  const at = code.indexOf("getElementById('dmg-list')");
  // Walk back to the nearest storage read and confirm which key it is.
  const before = code.slice(Math.max(0, at - 4000), at);
  const keys = before.match(/sd_damage\w*/g) || [];
  assert.ok(keys.length > 0, 'no damage store read near the #dmg-list writer');
  assert.strictEqual(keys[keys.length - 1], 'sd_damage',
    'the nearest damage store to the #dmg-list writer is ' + keys[keys.length - 1]);
});

// ═══════════════════════════════════════════════════════════════════════════
console.log('\n' + pass + '/' + (pass + fail) + ' passed');
process.exit(fail ? 1 : 0);
