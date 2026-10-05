// tests/sairncash_plan_label.js
//
// REQUIREMENT: the sidebar Plan row must state the plan the user actually has,
//   derived from the same accessors the access gate uses -- and when the only
//   evidence is a client record the server cannot look up, it must say so
//   rather than claim Pro.
//
// WHY THIS EXISTS. Until 2026-10-05 the row was a literal:
//
//   <div class="stat-row"><span class="stat-label">Plan</span>
//        <span class="stat-val">Pro</span></div>
//
// So it read "Pro" for a 30-day trial user, for a user whose subscription had
// lapsed, and for a user who had forged `sairncash_sub` in devtools -- which
// sairncash.html's own comment records as a thing that happened, one line in
// devtools opening the paid product with zero network calls. A displayed value
// with no function behind it is the fabricated-KPI class, and this is the worst
// row in the app to have it on: it is the app answering "what am I paying
// for".
//
// THIS EXECUTES scPlanLabel() rather than asserting on source text. The
// function is extracted from sairncash.html and run against stubbed
// accessors, so an arm fails when the BEHAVIOUR changes. A failure to extract
// is exit 2 COULD NOT RUN -- never a pass.
//
// Run:  node tests/sairncash_plan_label.js

'use strict';
const fs = require('fs');
const path = require('path');

const HTML = fs.readFileSync(path.join(__dirname, '..', 'sairncash.html'),
                             'utf8');

let pass = 0, fail = 0;
function ok(l) { pass++; console.log('  ok   ' + l); }
function bad(l, why) {
  fail++;
  console.log('  FAIL ' + l);
  if (why) console.log('       ' + String(why).slice(0, 300));
}

const m = HTML.match(/function scPlanLabel\(\)\s*\{[\s\S]*?\n\}/);
if (!m) {
  console.error('COULD NOT RUN: scPlanLabel was not found in sairncash.html. ' +
                'This suite tested NOTHING, which is not a pass.');
  process.exit(2);
}

// Build the function with injectable accessors. The real ones read
// localStorage, which does not exist in node -- stubbing them is the point,
// because what is under test is the DECISION, not the storage.
function makeLabel(sub, trial, subscribed) {
  const src =
    'var getSub = function(){ return ' + JSON.stringify(sub) + '; };\n' +
    'var getTrial = function(){ return ' + JSON.stringify(trial) + '; };\n' +
    'var isSubscribed = function(){ return ' + (subscribed ? 'true' : 'false') +
    '; };\n' + m[0] + '\nreturn scPlanLabel;';
  return new Function(src)();
}

console.log('SAIRNCASH PLAN LABEL -- criteria 2026-10-05.1');
console.log('\nA. EVERY STATE THE OLD LITERAL CALLED "Pro"');

const CASES = [
  // label, sub, trial, isSubscribed(), expected
  ['a real paid subscriber',
   { valid: true, expiresAt: '2030-01-01', subscriptionId: 'sub_123' },
   null, true, 'Pro'],
  ['a 30-day trial, 30 days left',
   null, { trialToken: 'tk', daysLeft: 30 }, false, 'Trial — 30 days left'],
  ['a trial with 1 day left (singular)',
   null, { trialToken: 'tk', daysLeft: 1 }, false, 'Trial — 1 day left'],
  ['a trial that has run out',
   null, { trialToken: 'tk', daysLeft: 0 }, false, 'Trial ended'],
  ['a LAPSED subscription -- had one, it expired',
   { valid: true, expiresAt: '2020-01-01', subscriptionId: 'sub_123' },
   null, false, 'Expired'],
  ['never subscribed, no trial',
   null, null, false, 'Free'],
  ['a FORGED record with no subscriptionId for the server to look up',
   { valid: true, expiresAt: '2030-01-01' }, null, true, 'Pro (unverified)'],
];

let wrong = [];
CASES.forEach(function (c) {
  const got = makeLabel(c[1], c[2], c[3])();
  if (got !== c[4]) wrong.push({ case: c[0], got: got, want: c[4] });
});
if (!wrong.length) {
  ok('A1. all ' + CASES.length + ' states produce their own label. THE OLD ' +
     'LITERAL RETURNED "Pro" FOR EVERY ONE OF THEM');
} else {
  bad('A1. each plan state must have its own label',
      JSON.stringify(wrong[0]));
}

// The point of the change, stated as its own arm so it cannot be lost in A1.
const forged = makeLabel({ valid: true, expiresAt: '2030-01-01' }, null, true)();
if (forged === 'Pro (unverified)') {
  ok('A2. THE FORGEABLE CASE IS LABELLED, NOT TRUSTED. A record claiming ' +
     'validity with no subscriptionId is exactly the devtools forgery this ' +
     'file documents, and it reads "Pro (unverified)" -- not "Pro", which ' +
     'would repeat the old lie, and not "Free", which would be wrong for a ' +
     'real subscriber mid-sync');
} else {
  bad('A2. an unverifiable record must not read as Pro', forged);
}

const lapsed = makeLabel(
  { valid: true, expiresAt: '2020-01-01', subscriptionId: 's' }, null, false)();
if (lapsed === 'Expired') {
  ok('A3. a LAPSED subscription reads "Expired", not "Free" -- having had one ' +
     'and lost it is a different fact from never having had one, and the row ' +
     'no longer flattens them');
} else {
  bad('A3. a lapsed subscription must not read as Free', lapsed);
}

console.log('\nB. PAID OUTRANKS A STALE TRIAL RECORD');

const both = makeLabel(
  { valid: true, expiresAt: '2030-01-01', subscriptionId: 'sub_1' },
  { trialToken: 'tk', daysLeft: 3 }, true)();
if (both === 'Pro') {
  ok('B1. a paying customer who also has a leftover trial record reads ' +
     '"Pro". Without the paid-first order a real subscriber would be told ' +
     'their trial was running out');
} else {
  bad('B1. paid must outrank a stale trial', both);
}

console.log('\nC. THE SOURCE-LEVEL GUARDS -- what behaviour cannot see');

// Comments stripped: this file documents the old literal verbatim, so a naive
// grep matches the documentation. Third instance of that class this week; see
// tests/pycomments.py.
const CODE = HTML.split(/\r?\n/)
  .filter(function (l) { return !/^\s*(<!--|\/\/)/.test(l); }).join('\n');

const checks = [
  ['C1. the hardcoded Pro literal is GONE from the markup',
   !/stat-val">Pro</.test(CODE)],
  ['C2. the row has an id for the label to be written into',
   /id="planLabel"/.test(CODE)],
  ['C3. the label is derived from isSubscribed(), the same gate the access ' +
   'check uses, so the label and the entitlement cannot disagree',
   /isSubscribed\(\)/.test(HTML.split('function scPlanLabel')[1].slice(0, 500))],
  ['C4. and it is actually CALLED -- a derivation nothing invokes is the ' +
   'dormant-code class, and this row would then render the em-dash for ever',
   /updatePlanLabel\(\);/.test(CODE)],
  ['C5. the usage BAR is gone, not rescaled -- a filled track is a quota ' +
   'affordance whatever it is a proportion of, and the paywall promises ' +
   '"Unlimited AI with Claude"',
   !/id="usageFill"/.test(CODE)],
  ['C6. ...and the COUNT survives, because the count is true and useful',
   /id="usageCount"/.test(CODE)],
];
checks.forEach(function (c) { if (c[1]) ok(c[0]); else bad(c[0], 'pattern'); });

console.log('\n' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
