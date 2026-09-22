// api/_lib/mech-redact.test.js
// REQUIREMENT: direct identifiers are removed from scanned-document text before
//   it is stored, the document's own subject matter (amounts, model numbers,
//   equipment serials) is NOT, and the pass never reports itself complete
//
// Run: node api/_lib/mech-redact.test.js
//
// BOTH DIRECTIONS ON EVERY RULE. A redactor tested only on what it should
// remove passes just as well when it removes everything -- and a redactor that
// eats the model numbers on a spec sheet is one a technician switches off,
// after which it redacts nothing at all. So each arm that asserts a removal has
// a partner asserting a keep.
'use strict';
const assert = require('assert');
const { redactDocumentText, NOT_REDACTED_NOTE } = require('./mech-redact');

let pass = 0, fail = 0;
function t(name, fn) {
  try { fn(); pass += 1; console.log('  ok   ' + name); }
  catch (e) { fail += 1; console.log('  FAIL ' + name + '\n         ' + e.message); }
}
const kinds = (r) => r.redactions.map((x) => x.kind).sort();

console.log('mech document redaction -- remove the identifiers, keep the subject\n');

// ── IDENTIFIERS OUT ─────────────────────────────────────────────────────
t('an email is removed', () => {
  const r = redactDocumentText('Contact j.smith@acme-hvac.com for access.');
  assert.ok(!/smith@/.test(r.text), r.text);
  assert.deepStrictEqual(kinds(r), ['EMAIL']);
});
t('a structured phone number is removed', () => {
  ['(440) 555-0100', '440-555-0100', '+1 440.555.0100'].forEach((p) => {
    const r = redactDocumentText('Call ' + p + ' on arrival.');
    assert.ok(/PHONE REDACTED/.test(r.text), p + ' -> ' + r.text);
  });
});
t('an SSN and an EIN are removed', () => {
  const r = redactDocumentText('SSN 123-45-6789 EIN 12-3456789');
  assert.deepStrictEqual(kinds(r), ['EIN', 'SSN']);
  assert.ok(!/123-45-6789/.test(r.text));
  assert.ok(!/12-3456789/.test(r.text));
});
t('a card-length digit run is removed, spaced or not', () => {
  ['4111111111111111', '4111 1111 1111 1111', '4111-1111-1111-1111'].forEach((c) => {
    const r = redactDocumentText('Paid with ' + c + '.');
    assert.ok(/CARD\/ACCOUNT REDACTED/.test(r.text), c + ' -> ' + r.text);
  });
});
t('a street address is removed', () => {
  const r = redactDocumentText('Site: 1425 Lakeshore Blvd, Suite 200');
  assert.ok(/ADDRESS REDACTED/.test(r.text), r.text);
});
t('a LABELLED name is removed -- the label is matched, never the name', () => {
  const r = redactDocumentText(
    'Customer: Eleanor Whitfield\nTechnician: D. Okoye\nUnit: Carrier 58MVC');
  assert.ok(!/Whitfield/.test(r.text), r.text);
  assert.ok(!/Okoye/.test(r.text), r.text);
  assert.ok(/Customer: \[NAME REDACTED\]/.test(r.text), r.text);
  assert.ok(/Carrier 58MVC/.test(r.text),
    'the equipment line has no person label and must survive untouched');
});

// ── THE SUBJECT MATTER STAYS ────────────────────────────────────────────
t('AMOUNTS ARE KEPT -- the money is the document, not the leak', () => {
  const r = redactDocumentText('Total $12,480.00, deposit $3,000.');
  assert.ok(/\$12,480\.00/.test(r.text), r.text);
  assert.ok(/\$3,000/.test(r.text), r.text);
});
t('MODEL NUMBERS AND SHORT CODES ARE KEPT', () => {
  const r = redactDocumentText('Unit Carrier 58MVC080-F-1-20, filter 16x25x1.');
  assert.strictEqual(r.redacted, false, r.text);
  assert.strictEqual(r.text, 'Unit Carrier 58MVC080-F-1-20, filter 16x25x1.');
});
t('A BARE TEN-DIGIT RUN IS NOT TREATED AS A PHONE NUMBER', () => {
  // A serial on a spec sheet. Eating it is the failure that gets a redactor
  // switched off, after which it redacts nothing at all.
  const r = redactDocumentText('Serial 4405550100 on the data plate.');
  assert.strictEqual(r.redacted, false, r.text);
});
t('A LONG EQUIPMENT SERIAL IS NOT TREATED AS A CARD', () => {
  // 22 digits -- past the 13-19 payment-card range, and bounded for exactly
  // this reason.
  const r = redactDocumentText('Compressor serial 1234567890123456789012.');
  assert.strictEqual(r.redacted, false, r.text);
});
t('an EPA 608 certificate number survives', () => {
  const r = redactDocumentText('EPA 608 Type II cert 608-II-2026-00417.');
  assert.strictEqual(r.redacted, false, r.text);
});

// ── THE HONESTY CONTRACT ────────────────────────────────────────────────
t('complete is ALWAYS false, even on text it fully handled', () => {
  const clean = redactDocumentText('Nothing identifying here at all.');
  const dirty = redactDocumentText('Customer: A B, a@b.co');
  assert.strictEqual(clean.complete, false);
  assert.strictEqual(dirty.complete, false,
    'there is no input for which this pass is complete, so no caller may '
    + 'branch on it being true');
});
t('A NAME IN PROSE SURVIVES, and the note says so rather than implying it did not', () => {
  const r = redactDocumentText('Spoke to Dave about the condenser.');
  assert.ok(/Dave/.test(r.text),
    'this is the documented limit -- asserting it keeps the limit honest '
    + 'rather than aspirational');
  assert.ok(/prose/.test(r.note));
  assert.strictEqual(r.note, NOT_REDACTED_NOTE);
});
t('the note travels on EVERY result, redacted or not', () => {
  assert.strictEqual(redactDocumentText('').note, NOT_REDACTED_NOTE);
  assert.strictEqual(redactDocumentText('plain').note, NOT_REDACTED_NOTE);
});
t('counts are per kind and only fired kinds appear', () => {
  const r = redactDocumentText('a@b.co and c@d.co and (440) 555-0100');
  const m = {}; r.redactions.forEach((x) => { m[x.kind] = x.count; });
  assert.strictEqual(m.EMAIL, 2);
  assert.strictEqual(m.PHONE, 1);
  assert.ok(!('SSN' in m), 'a kind that did not fire must not appear at zero');
});

// ── INPUT SHAPES ────────────────────────────────────────────────────────
t('non-string input yields empty text, not the string "null"', () => {
  [null, undefined, 7, {}, []].forEach((v) => {
    const r = redactDocumentText(v);
    assert.strictEqual(r.text, '');
    assert.strictEqual(r.redacted, false);
  });
});
t('redaction is IDEMPOTENT -- running it twice changes nothing and re-counts nothing', () => {
  const once = redactDocumentText('Customer: A B\nmail a@b.co\n(440) 555-0100');
  const twice = redactDocumentText(once.text);
  assert.strictEqual(twice.text, once.text,
    'a stored row re-saved must not accumulate tokens');
  assert.strictEqual(twice.redacted, false,
    'already-redacted text has nothing left to redact, and reporting a second '
    + 'round of counts would overstate what the pass found');
});

console.log('\n' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
