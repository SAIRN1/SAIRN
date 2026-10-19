#!/usr/bin/env node
// tests/sairnroofing_default_location_from_server.js
// OWNER: cody
//
// Run:  node tests/sairnroofing_default_location_from_server.js
//
// # REQUIREMENT: sairnroofing.html never carries its own copy of the
//   default-location sentinel. It answers "is this the implicit default?" only
//   from a fact the SERVER supplied -- `is_default` on a row, or
//   `default_location_id` on the response -- and says UNKNOWN when it has
//   neither.
//
// ── THE CONCEPT, stated before this file was written ──────────────────────
// rfIsDefaultLoc() answers true/false ONLY from a server-supplied fact, and
// returns null (UNKNOWN) before the server has answered, so neither call site
// can present a guess as a decision.
//
// ── WHY IT EXISTS: AN ARM WHOSE STATED REASON NAMED A UI AND CHECKED NO UI ─
// api/_lib/location-scope.js added isDefaultLocation() with its reason in the
// code: "sairnroofing.html asks this question inline twice, and a UI that
// hardcodes the sentinel is the next place the constant drifts." Measured in
// cody b22: BOTH SITES STILL HARDCODED IT AND COULD NOT STOP -- that module is
// CommonJS and this app is a single HTML file with no loader and no build step,
// so there was no path from the UI to the function. Arm E passed and proved the
// function WORKS, not that anything USES it.
//
// Michael's decision of the two options cody b23 routed was to SERVE THE
// ANSWER: the rf_locations read branch stamps `is_default` per row with that
// same function, and this file drives the client side of it.
//
// THE ENDPOINT HALF is asserted by api/_lib/location-scope.test.js arm F (no
// app file spells the sentinel in executable code) and by the stamping line in
// api/sd-data.js. THIS FILE IS THE BEHAVIOUR: what the helper answers, and
// what each call site does with an UNKNOWN.
//
// EXIT CODES: 0 clean, 1 an arm failed, 2 COULD NOT RUN. The third state is
// never folded into the first.
'use strict';

const fs = require('fs');
const path = require('path');
const assert = require('assert');

const APP = path.join(__dirname, '..', 'sairnroofing.html');

function couldNotRun(why) {
  console.log('COULD NOT RUN: ' + why + '.');
  console.log('  Nothing was asserted. This is a THIRD STATE and is not a pass.');
  process.exit(2);
}

if (!fs.existsSync(APP)) couldNotRun('sairnroofing.html not found at ' + APP);
const SRC = fs.readFileSync(APP, 'utf8').replace(/\r\n/g, '\n');

// ── EXTRACTION, FAILING CLOSED ON A NON-UNIQUE ANCHOR ─────────────────────
// A slice that starts in the wrong place produces arms that test nothing, and
// `indexOf` alone would silently take the first of several.
function region(startAnchor, endAnchor) {
  const nS = SRC.split(startAnchor).length - 1;
  const nE = SRC.split(endAnchor).length - 1;
  if (nS !== 1) couldNotRun('start anchor ' + JSON.stringify(startAnchor)
    + ' occurs ' + nS + ' times, expected exactly 1');
  if (nE !== 1) couldNotRun('end anchor ' + JSON.stringify(endAnchor)
    + ' occurs ' + nE + ' times, expected exactly 1');
  const a = SRC.indexOf(startAnchor);
  const b = SRC.indexOf(endAnchor, a);
  if (b <= a) couldNotRun('the end anchor does not follow the start anchor');
  return SRC.slice(a, b);
}

const HELPER = region('function rfIsDefaultLoc(id){', '\nfunction rfFillLocationSelect');

let api;
try {
  // eslint-disable-next-line no-new-func
  api = new Function(`
    var rfLocations = [];
    var rfDefaultLocId = null;
    ${HELPER}
    return {
      isDefault: rfIsDefaultLoc,
      setRows: function (r) { rfLocations = r; },
      setDefaultId: function (d) { rfDefaultLocId = d; }
    };
  `)();
} catch (e) {
  couldNotRun('the extracted helper does not evaluate: ' + e.message);
}

const failed = [];
let run = 0;
function arm(label, cond, detail) {
  run++;
  if (cond) { console.log('  ok   ' + label); return; }
  console.log('  FAIL ' + label);
  if (detail !== undefined) console.log('         got: ' + String(detail));
  failed.push(label);
}

console.log('sairnroofing: the default location comes from the SERVER');
console.log('');
console.log('PRECONDITIONS -- each a third state, never folded into a pass');

const stripped = SRC
  .replace(/<!--[\s\S]*?-->/g, ' ')
  .replace(/\/\*[\s\S]*?\*\//g, ' ')
  .replace(/\/\/[^\n]*/g, ' ');
arm('P1. the sentinel is spelled ZERO times in this app\'s EXECUTABLE code '
  + '-- comment-stripped, because the note recording the removal quotes it',
  (stripped.match(/LOC-DEFAULT/g) || []).length === 0,
  (stripped.match(/LOC-DEFAULT/g) || []).length + ' occurrence(s)');
arm('P2. ...and it IS still quoted in a comment, so P1 is comment-stripping '
  + 'rather than a file that never mentioned it -- the two look identical to '
  + 'a stripped-source test and only this pair tells them apart',
  SRC.indexOf('LOC-DEFAULT') !== -1);
arm('P3. rfLoadLocations() captures default_location_id OFF THE RESPONSE '
  + 'rather than typing it',
  /rfDefaultLocId\s*=\s*r\.data\.default_location_id/.test(stripped));

console.log('');
console.log('A. UNKNOWN IS A REAL ANSWER AND IS NOT false');

api.setRows([]);
api.setDefaultId(null);
arm('A1. with no server answer at all, a real id is UNKNOWN (null) -- not '
  + 'false, which would assert it is a named branch, and not true, which '
  + 'would assert it is the default',
  api.isDefault('YARD-2') === null, api.isDefault('YARD-2'));
arm('A2. ...but an ABSENT id is true without asking anything, because absent '
  + 'IS the implicit default and that needs no server fact',
  api.isDefault('') === true && api.isDefault(null) === true
  && api.isDefault(undefined) === true);

console.log('');
console.log('B. THE ROW\'S OWN is_default IS PREFERRED');

api.setRows([
  { location_id: 'LOC-DEFAULT', name: 'Main', is_default: true },
  { location_id: 'YARD-2', name: 'Cleveland', is_default: false }
]);
api.setDefaultId('LOC-DEFAULT');
arm('B1. a row flagged is_default:true answers true', api.isDefault('LOC-DEFAULT') === true);
arm('B2. a row flagged is_default:false answers false', api.isDefault('YARD-2') === false);
arm('B3. THE ROW WINS OVER THE RESPONSE-LEVEL ID, which is what makes this a '
  + 'per-row answer: a row the server flagged false is false even when its id '
  + 'equals default_location_id',
  (() => {
    api.setRows([{ location_id: 'LOC-DEFAULT', name: 'Main', is_default: false }]);
    const v = api.isDefault('LOC-DEFAULT');
    api.setRows([
      { location_id: 'LOC-DEFAULT', name: 'Main', is_default: true },
      { location_id: 'YARD-2', name: 'Cleveland', is_default: false }
    ]);
    return v === false;
  })());
arm('B4. a row present but carrying NO is_default is UNKNOWN, not false -- an '
  + 'older server that has not been redeployed must not be read as an answer',
  (() => {
    api.setRows([{ location_id: 'YARD-9', name: 'Akron' }]);
    const v = api.isDefault('YARD-9');
    api.setRows([
      { location_id: 'LOC-DEFAULT', name: 'Main', is_default: true },
      { location_id: 'YARD-2', name: 'Cleveland', is_default: false }
    ]);
    return v === null;
  })());

console.log('');
console.log('C. AN ID WITH NO ROW FALLS BACK TO default_location_id');

arm('C1. the sentinel with NO ROW OF ITS OWN still answers true -- the normal '
  + 'case, because a shop that never opened a second branch has every job on '
  + 'the implicit default and an EMPTY registry',
  (() => {
    api.setRows([]);
    api.setDefaultId('LOC-DEFAULT');
    return api.isDefault('LOC-DEFAULT') === true;
  })());
arm('C2. ...and an unknown id with the response answer present is false',
  api.isDefault('YARD-404') === false);
arm('C3. THE FALLBACK IS THE SERVER\'S STRING, not a typed one: change what '
  + 'the server said and the answer follows it',
  (() => {
    api.setRows([]);
    api.setDefaultId('MAIN-YARD');
    const a = api.isDefault('MAIN-YARD') === true;
    const b = api.isDefault('LOC-DEFAULT') === false;
    api.setDefaultId('LOC-DEFAULT');
    return a && b;
  })());

console.log('');
console.log('D. THE TWO CALL SITES SAY WHAT THEY DO WITH AN UNKNOWN');

const select = region('function rfFillLocationSelect(selected){', '\nfunction rfLocationName');
const nameFn = region('function rfLocationName(id){', '\nfunction rfSaveLocation');
const selCode = select.replace(/\/\*[\s\S]*?\*\//g, ' ').replace(/\/\/[^\n]*/g, ' ');
const nameCode = nameFn.replace(/\/\*[\s\S]*?\*\//g, ' ').replace(/\/\/[^\n]*/g, ' ');
arm('D1. the select compares against true EXPLICITLY (`!==true`), so an '
  + 'UNKNOWN keeps the explicit id selected instead of collapsing the job to '
  + 'Main -- a truthiness test would have treated null as "not default" by '
  + 'accident rather than by decision, which is the same answer for the wrong '
  + 'reason',
  /rfIsDefaultLoc\(\s*selected\s*\)\s*!==\s*true/.test(selCode), selCode.trim().slice(-160));
arm('D2. rfLocationName compares against true EXPLICITLY, so an UNKNOWN falls '
  + 'through to the row name or the raw id and never prints "Main" for '
  + 'something it could not classify',
  /rfIsDefaultLoc\(\s*id\s*\)\s*===\s*true/.test(nameCode), nameCode.trim().slice(0, 160));
arm('D3. neither call site spells the sentinel', nameCode.indexOf('LOC-DEFAULT') === -1
  && selCode.indexOf('LOC-DEFAULT') === -1);

console.log('');
console.log(run + ' checks run, ' + failed.length + ' failed');
if (failed.length) {
  console.log('');
  console.log(failed.length + ' ARM(S) FAILED:');
  failed.forEach((l) => console.log('  - ' + l));
  console.log('');
  console.log('NO ARM HERE IS EXPECTED RED. A P arm means the sentinel is back '
    + 'in executable code or the response capture was re-typed; an A or B arm '
    + 'means UNKNOWN has collapsed into a decided answer; a C arm means the '
    + 'fallback stopped following the server; a D arm means a call site started '
    + 'treating null as a decision.');
  process.exit(1);
}
process.exit(0);
