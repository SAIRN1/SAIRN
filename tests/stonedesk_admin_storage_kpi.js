// tests/stonedesk_admin_storage_kpi.js
// REQUIREMENT: the Admin Overview "Storage" KPI reports a MEASURED quantity,
//   over a population its label names, with no assumed browser quota behind it
//
// Run:  node tests/stonedesk_admin_storage_kpi.js
//
// ── THE DEFECT ─────────────────────────────────────────────────────────────
// `renderAdminOverviewKPIs` computed
//
//     var pct = Math.min(100, Math.round((totalBytes/1024/5120)*100));
//
// and wrote it into a card labelled simply "Storage Used". Three things were
// wrong with that one line and only one of them is the `Math.min` that
// tools/overrun_inversion_scan.py flagged:
//
//   1. THE `Math.min` IS NOT THE DEFECT and the scan's own header says it
//      cannot tell. A browser localStorage quota is a HARD ceiling -- a write
//      past it throws -- so the ratio cannot legitimately exceed 1 and the cap
//      can never hide an overrun. FALSE POSITIVE for that class, recorded as
//      one rather than "fixed" into something else.
//   2. THE DENOMINATOR WAS ASSUMED. `5120` KB is a guess at the quota. Real
//      quotas vary by browser and by origin, and where the true quota is
//      larger this reported a store as FULL that was half used -- a number an
//      owner acts on by deleting data.
//   3. THE POPULATION WAS NOT THE ONE THE LABEL NAMED. The loop sums EVERY
//      key in localStorage, which on this platform is every SAIRN app in the
//      browser, and presented it as StoneDesk's. The paragraph eleven lines
//      below the card makes exactly that distinction for the delete buttons:
//      "removes only what StoneDesk stored -- other SAIRN apps in this browser
//      are untouched."
//
// So the card showed a percentage of a guess, over a population it did not
// name. The fix reports the measured bytes and names the population; the
// browser's real limit is not knowable synchronously and the app does not
// guess at it.

'use strict';
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const HTML = fs.readFileSync(path.join(__dirname, '..', 'stonedesk.html'),
                             'utf8').replace(/\r\n/g, '\n');

let passed = 0;
function test(name, fn) {
  try {
    fn();
    passed++;
    console.log('  ok - ' + name);
  } catch (err) {
    console.error('  FAIL - ' + name);
    console.error('    ' + err.message);
    process.exitCode = 1;
  }
}

// The function body, located by its own name rather than by a line number.
function bodyOf(src) {
  const i = src.indexOf('function renderAdminOverviewKPIs(){');
  assert.ok(i > 0, 'renderAdminOverviewKPIs is gone or renamed');
  // to the end of the IIFE that calls it
  const j = src.indexOf('renderAdminOverviewKPIs();', i + 10);
  assert.ok(j > i, 'the call site that runs it on load is gone');
  return src.slice(i, j);
}
// COMMENTS NEVER COUNT, and this arm found that out the hard way on its first
// run: the fix's own comment EXPLAINS the 5120 guess it removed, in those
// digits, and the "no assumed quota" arm matched the explanation and went red
// against correct code. A check that forbids a token has to say whether it
// means the code or the file, because a fix that documents what it removed is
// the normal case and not an edge one. Same rule as
// api/sd-data-active-credential.test.js, which strips before asserting.
const BODY = bodyOf(HTML)
  .replace(/^[ \t]*\/\/[^\n]*$/gm, '')
  .replace(/\/\*[\s\S]*?\*\//g, '');

test('NO ASSUMED QUOTA: the browser storage limit is not hardcoded', () => {
  assert.ok(!/\b5120\b/.test(BODY),
    'the 5120 KB quota guess is back. Real quotas vary by browser and origin; '
    + 'where the true limit is larger this reports a half-used store as full, '
    + 'and a full store is a figure an owner acts on by deleting data.');
  assert.ok(!/Math\.min\(100/.test(BODY),
    'a cap at 100 implies a percentage, which implies a denominator. If a '
    + 'real quota has been obtained, assert it here instead of deleting '
    + 'this arm.');
});

test('MEASURED: the figure still comes from summing real keys, so the fix is '
  + 'not a card that stopped reporting', () => {
    assert.ok(/localStorage\.length/.test(BODY)
      && /localStorage\.getItem\(k\)/.test(BODY),
      'nothing iterates localStorage any more -- the KPI has no source');
    assert.ok(/totalBytes/.test(BODY),
      'the measured total is gone');
  });

test('THE LABEL NAMES THE POPULATION IT SUMS -- every SAIRN app in this '
  + 'browser, not StoneDesk alone', () => {
    // The loop reads EVERY key in localStorage. The delete-buttons paragraph
    // below this card already draws that distinction for the user, so the KPI
    // above it must not quietly contradict it.
    const card = HTML.slice(HTML.indexOf('id="adm-storage"') - 200,
                            HTML.indexOf('id="adm-storage"') + 400);
    const m = /<div class="kpi-label">([^<]*)<\/div>/.exec(
      card.slice(card.indexOf('id="adm-storage"')));
    assert.ok(m, 'the KPI label beside adm-storage could not be read');
    assert.ok(/all SAIRN apps|every SAIRN app|browser/i.test(m[1]),
      'the label reads ' + JSON.stringify(m[1]) + ', which does not say whose '
      + 'data is being counted. The loop sums every key in localStorage -- '
      + 'every SAIRN app in this browser -- and the paragraph below this card '
      + 'tells the user those are different things.');
  });

test('CONTROL: the card still exists and is still written to, so the arms '
  + 'above are not passing over a deleted feature', () => {
    assert.ok(/id="adm-storage"/.test(HTML), 'the KPI card is gone');
    assert.ok(/getElementById\('adm-storage'\)/.test(BODY)
      && /\.textContent\s*=/.test(BODY),
      'nothing writes the storage KPI any more');
  });

test('CONTROL: this file would notice the whole function being deleted -- the '
  + 'anchors it reads are the real ones', () => {
    assert.ok(HTML.indexOf('function renderAdminOverviewKPIs(){') > 0);
    assert.ok(HTML.indexOf('renderAdminOverviewKPIs();') > 0);
    assert.ok(BODY.length > 200,
      'the extracted body came out too short to assert over');
  });

console.log(passed + ' passed'
  + (process.exitCode ? ', with failures above' : ''));
