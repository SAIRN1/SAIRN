// tests/sairncare_payer_routing_integration.js
//
// THE CALL SITE, NOT THE FUNCTION. rPayerRouting() renders the Payer Routing
// panel, and one line inside it -- `prRenderRecorded();` at sairncare.html:3054
// -- is what puts the RECORDED DETERMINATIONS on screen beside the rules.
//
// tests/sairncare_route_record.js drives prRenderRecorded() thoroughly: section
// 8 exercises its four states and NEVER MIGRATED as its own. What nothing drove
// was the CALL. Measured before this file existed, in a throwaway worktree:
// deleting that line from sairncare.html leaves that suite at ALL ARMS PASS and
// its 10-mutation sabotage probe untouched, because neither ever executes
// rPayerRouting(). hover flagged it; this reproduces it and closes it.
//
// WHAT THE DEFECT WOULD LOOK LIKE IN THE APP, which is why it is worth an arm:
// the rules render, the coverage line renders, and the determinations that were
// actually recorded silently stop appearing. Nothing errors. A biller reading
// the panel sees a complete-looking screen with the trail missing -- and the
// trail is the half that says what was already decided for this resident.
//
// WHY A NEW FILE RATHER THAN AN ARM IN THE EXISTING SUITE: fourth holds an
// active claim on tests/sairncare_route_record.js (sairncare-route-correction-
// path). Adding a property in a new file touches nothing they are editing.
// Disclosed here rather than negotiated in a rebase.
//
// Run:  node tests/sairncare_payer_routing_integration.js

// NO 'use strict' HERE, DELIBERATELY, and it is the same decision
// tests/sairncare_route_record.js records: a direct eval in STRICT mode puts
// its function declarations in a scope of their own, so the lifted
// rPayerRouting() would be unreachable and every arm would die on
// "rPayerRouting is not defined". Non-strict direct eval puts it in this
// module's scope, which is the whole point. Measured here by hitting it.
const fs = require('fs');
const path = require('path');

const APP = path.join(__dirname, '..', 'sairncare.html');
const LINES = fs.readFileSync(APP, 'utf8').split('\n');

// Same counted-anchor discipline the route-record suite uses, and for the same
// reason: an anchor that matches twice tests whichever came first, and one that
// matches zero times tests nothing while still passing the file.
function grab(anchor) {
  const hits = [];
  for (let i = 0; i < LINES.length; i++) if (LINES[i].startsWith(anchor)) hits.push(i);
  if (hits.length !== 1) {
    throw new Error('ANCHOR-' + hits.length + ' for ' + JSON.stringify(anchor)
      + ' in sairncare.html -- this suite is not testing what it says it tests. '
      + 'Fix the anchor, do not delete the arm.');
  }
  const start = hits[0];
  for (let j = start; j < LINES.length; j++) {
    if (LINES[j] === '}') return LINES.slice(start, j + 1).join('\n');
    // A single-line `var x = ...;` declaration, the same form the
    // route-record suite's grab() accepts. Without this branch, lifting the
    // claimed-states list runs on to the next closing brace and drags a whole
    // function in with it.
    if (LINES[j].startsWith('var ') && LINES[j].endsWith(';')) return LINES[j];
  }
  throw new Error('no closing brace found after ' + JSON.stringify(anchor));
}

let failed = 0;
function ok(name, cond, detail) {
  if (cond) { console.log('  ok   ' + name); return; }
  failed++;
  console.log('  FAIL ' + name + (detail ? '\n         ' + detail : ''));
}
function section(s) { console.log('\n' + s); }

// ── The browser the function expects, and nothing more ────────────────────
let RENDERS = 0;
let ELEMENTS = {};
function el(id) {
  if (!ELEMENTS[id]) ELEMENTS[id] = { id: id, textContent: '', innerHTML: '' };
  return ELEMENTS[id];
}
// eslint-disable-next-line no-unused-vars
var $ = function (id) { return ELEMENTS[id] === null ? null : el(id); };
// eslint-disable-next-line no-unused-vars
var prRenderRecorded = function () { RENDERS++; };
// eslint-disable-next-line no-unused-vars
var _prRules = null, _prReadFailed = false, _cqRules = null, _cqReadFailed = false;
// eslint-disable-next-line no-unused-vars
var residents = function () { return []; };
// eslint-disable-next-line no-unused-vars
var H = function (s) { return String(s == null ? '' : s); };
// eslint-disable-next-line no-unused-vars
var toast = function () {};
// LIFTED FROM THE PAGE, NOT RETYPED. rPayerRouting() filters this list to work
// out coverage, so a hand-written copy here would let the suite agree with
// itself about which states the app claims -- exactly the sort of figure this
// platform has watched drift between a document and its source.
eval(grab('var ALF_CLAIMED_HCBS_STATES='));   // eslint-disable-line no-eval

eval(grab('function rPayerRouting()'));        // eslint-disable-line no-eval

function reset(opts) {
  RENDERS = 0;
  ELEMENTS = {};
  el('pr-rules'); el('pr-coverage');
  _prRules = (opts && 'rules' in opts) ? opts.rules : null;
  _prReadFailed = !!(opts && opts.failed);
}

console.log('sairncare -- rPayerRouting() renders the RECORDED trail, in every state');

section('1. the recorded trail is rendered in EVERY state of the rules read');
// The three states the panel itself distinguishes. The trail read is
// deliberately independent of the rules read -- the function's own comment says
// so -- so a rules failure must NOT suppress the determinations that were
// already recorded, and vice versa. That independence is the property; the call
// is how it is delivered.
const STATES = [
  ['never loaded this session (null, not failed)', { rules: null, failed: false }],
  ['the rules read FAILED (null, failed)', { rules: null, failed: true }],
  ['the server really has no rules ([])', { rules: [], failed: false }],
  ['rules present', { rules: [{ id: 'R1', payer: 'Medicaid', state: 'OH' }], failed: false }]
];
for (const [label, opts] of STATES) {
  reset(opts);
  rPayerRouting();
  ok('rPayerRouting() calls prRenderRecorded() when ' + label,
     RENDERS === 1,
     'called ' + RENDERS + ' time(s) -- the rules half rendered and the recorded '
     + 'determinations silently did not, which errors nowhere and leaves a '
     + 'complete-looking panel with the trail missing');
}

section('2. ...and it is called ONCE, not once per rule');
reset({ rules: [{ id: 'R1' }, { id: 'R2' }, { id: 'R3' }], failed: false });
rPayerRouting();
ok('three rules still produce exactly one trail render', RENDERS === 1,
   'called ' + RENDERS + ' time(s)');

section('3. the guard clause still wins -- no panel, no render, no crash');
// `if(!box||!cov)return;` runs before everything. An arm that did not check
// this would pass just as happily against a function that rendered the trail
// into a page with no panel on it.
RENDERS = 0;
ELEMENTS = {};
ELEMENTS['pr-rules'] = null;
el('pr-coverage');
_prRules = null; _prReadFailed = false;
rPayerRouting();
ok('a missing panel returns before rendering anything', RENDERS === 0,
   'called ' + RENDERS + ' time(s) with no panel in the DOM');

section('4. the call is INSIDE the function, not a coincidence of this harness');
// The arms above would all still pass if `prRenderRecorded` were called by
// something else this file happens to evaluate. This asserts the line is in the
// function body that was lifted -- the same property, read a second way, so a
// harness mistake and a product defect cannot look identical.
const BODY = grab('function rPayerRouting()');
ok('rPayerRouting()\'s own body contains the prRenderRecorded() call',
   /(^|\n)\s*prRenderRecorded\(\);/.test(BODY),
   'the call is not in the body this suite evaluated');

console.log('\n' + (failed ? failed + ' FAILED' : 'ALL ARMS PASS'));
process.exit(failed ? 1 : 0);
