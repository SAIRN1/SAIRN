// tests/sairndesign_pricing.js
// REQUIREMENT: SAIRNdesign's confirmed price book must read identically in the
//   AI advisors' context (api/_lib/exec-context.js) and in the document a human
//   reads (docs/2026-10-05-sairndesign-pricing-benchmark.md), and must never
//   acquire an entry tier or a Stripe-price-ids claim neither source supports
//
// Run: node tests/sairndesign_pricing.js
//
// ── WHY A SECOND PRODUCT NEEDED ITS OWN COPY OF THIS GUARD ────────────────
// tests/pricing_single_source.js exists because StoneDesk carried TWO price
// lists that disagreed, in two files, and the one a CUSTOMER SIGNS was the
// wrong one. Adding SAIRNdesign's pricing in a second format in a second place
// is how that starts again, so it went into exec-context.js in the same shape
// as the StoneDesk line and is pinned here the same way.
//
// THE THIRD-OPINION CONSTANT IS DELIBERATE, and copied from that file's
// reasoning: the tiers are written out once below rather than read from one
// source and compared to the other. Comparing the two sources to EACH OTHER
// would still pass if both were edited wrongly in the same way -- which is
// exactly how two wrong price lists survived together for months.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const ROOT = path.join(__dirname, '..');
const EXEC_PATH = path.join(ROOT, 'api', '_lib', 'exec-context.js');
const DOC_PATH = path.join(ROOT, 'docs', '2026-10-05-sairndesign-pricing-benchmark.md');
const exec = fs.readFileSync(EXEC_PATH, 'utf8');
const doc = fs.readFileSync(DOC_PATH, 'utf8');

// ══ THE CONFIRMED PRICE BOOK -- Michael, 2026-10-05 ══════════════════════
const TIERS = [
  { name: 'Business', price: 399 },
  { name: 'Professional', price: 599 },
  { name: 'Enterprise', price: 899 }
];
// Numbers that must NOT appear as a CURRENT SAIRNdesign tier. The first three
// are StoneDesk's and are the likeliest copy-paste error, since the two lines
// now sit together in one file. 199 and 499 are StoneDesk's retired tiers.
const NOT_SAIRNDESIGN = [299, 799, 199, 499];

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('\n' + t); }

// The one line in exec-context.js that carries SAIRNdesign's prices.
function execLine() {
  const m = exec.match(/^\s*'SAIRNdesign pricing:[^\n]*$/m);
  assert.ok(m, 'no "SAIRNdesign pricing:" line in api/_lib/exec-context.js');
  return m[0];
}

console.log('SAIRNdesign pricing -- one price book, in two places, that must agree\n');

section('A. the AI advisors\' context');
test('A0. the SAIRNdesign pricing line exists at all', () => {
  assert.ok(execLine().length > 40);
});
TIERS.forEach((t) => {
  test('A. ' + t.name + ' is $' + t.price + '/mo in exec-context.js', () => {
    assert.ok(new RegExp(t.name + ' \\$' + t.price + '/mo').test(execLine()),
      'not found in: ' + execLine().trim().slice(0, 160));
  });
});
test('A4. it states there is NO entry tier below Business', () => {
  assert.ok(/NO entry-level tier below Business/.test(execLine()),
    'the no-entry-tier statement is gone; a $199-style land-and-expand tier '
    + 'could be invented by the advisor');
});
test('A5. it does NOT claim Stripe price IDs -- none are on file, and the '
  + 'StoneDesk line directly above DOES claim them', () => {
  assert.ok(/No Stripe price IDs are on file for SAIRNdesign/.test(execLine()),
    'the explicit absence is gone from: ' + execLine().trim().slice(0, 200));
  assert.ok(!/Stripe price IDs on file\./.test(execLine()),
    'the SAIRNdesign line now carries StoneDesk\'s "Stripe price IDs on file" '
    + 'phrasing, which is a claim this repo cannot verify for SAIRNdesign');
});
test('A6. it offers a custom quote above Enterprise', () => {
  assert.ok(/custom quote/i.test(execLine()));
});

section('B. the document a human reads');
TIERS.forEach((t) => {
  test('B. ' + t.name + ' is $' + t.price + '/mo in the benchmark doc', () => {
    assert.ok(new RegExp('\\*\\*' + t.name + '\\*\\*\\s*\\|\\s*\\*\\*\\$' + t.price + '/mo\\*\\*').test(doc),
      'the confirmed price-book row for ' + t.name + ' is missing or changed');
  });
});

section('C. neither source has picked up another product\'s number');
NOT_SAIRNDESIGN.forEach((p) => {
  test('C. $' + p + ' is not presented as a SAIRNdesign tier', () => {
    const line = execLine();
    assert.ok(!new RegExp('(Business|Professional|Enterprise) \\$' + p + '/mo').test(line),
      '$' + p + ' appears as a SAIRNdesign tier in exec-context.js: ' + line.trim().slice(0, 200));
  });
});
test('C4. StoneDesk\'s own line is UNTOUCHED -- adding a second product must '
  + 'not have edited the first', () => {
  assert.ok(/StoneDesk pricing: Business \$299\/mo, Professional \$599\/mo, Enterprise \$799\/mo/.test(exec),
    'the StoneDesk price line has changed; tests/pricing_single_source.js is '
    + 'the authority on it and should be consulted before this is "fixed"');
});

section('D. controls -- this file must be able to fail');
test('D1. the regex really is matching a line and not an empty string', () => {
  const line = execLine();
  assert.ok(line.indexOf('SAIRNdesign pricing:') >= 0);
  assert.ok(line.length > 100, 'line is suspiciously short: ' + line);
});
test('D2. a WRONG price would be caught -- the matcher is exact, not fuzzy', () => {
  // Drive the same assertion A uses against a deliberately wrong number and
  // require it to fail. Without this, a regex that silently matched anything
  // would make every arm in section A vacuous.
  const line = execLine();
  assert.ok(!new RegExp('Business \\$398/mo').test(line),
    'a price one dollar off matched, so section A proves nothing');
  assert.ok(new RegExp('Business \\$399/mo').test(line),
    'the real price did not match, so D2 is testing the wrong thing');
});
test('D3. both files were actually read', () => {
  assert.ok(exec.length > 5000, 'exec-context.js read as ' + exec.length + ' chars');
  assert.ok(doc.length > 2000, 'the benchmark doc read as ' + doc.length + ' chars');
});

console.log('\n' + pass + ' passed, ' + fail + ' failed');
if (fail) process.exit(1);
