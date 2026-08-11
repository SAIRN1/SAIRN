// api/_lib/dental-reminder-copy.test.js
// Plain node:assert tests -- no test framework, matching api/'s existing
// zero-npm-dependency convention (see api/_lib/auth.test.js).
// Run: node api/_lib/dental-reminder-copy.test.js

const assert = require('assert');
const { buildReminderEmail } = require('./dental-reminder-copy');

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

console.log('api/_lib/dental-reminder-copy.js');

var BASE = {
  practiceName: 'Pinnacle Dental', practicePhone: '(555) 123-4567',
  practiceAddress: '123 Main St, Springfield, IL', patientName: 'Jane Doe',
  providerName: 'Dr. Smith', procedureLabel: 'D0120 -- Periodic Oral Evaluation',
  startTimeISO: '2026-08-13T14:00:00.000Z'
};

test('48h stage includes practice name, patient name, provider, procedure, and phone', () => {
  var r = buildReminderEmail(Object.assign({}, BASE, { stage: '48h' }));
  assert.ok(r.subject.indexOf('Pinnacle Dental') !== -1, 'subject should name the practice');
  assert.ok(r.text.indexOf('Jane Doe') !== -1, 'text should greet the patient by name');
  assert.ok(r.text.indexOf('Dr. Smith') !== -1, 'text should name the provider');
  assert.ok(r.text.indexOf('D0120 -- Periodic Oral Evaluation') !== -1, 'text should name the procedure');
  assert.ok(r.text.indexOf('(555) 123-4567') !== -1, 'text should include the callback number');
});

test('2h stage uses different, shorter-fuse subject/lead-in than 48h', () => {
  var r48 = buildReminderEmail(Object.assign({}, BASE, { stage: '48h' }));
  var r2 = buildReminderEmail(Object.assign({}, BASE, { stage: '2h' }));
  assert.notStrictEqual(r48.subject, r2.subject, '48h and 2h subjects should differ');
  assert.ok(r2.subject.indexOf('2 hours') !== -1, '2h subject should mention the short fuse');
});

test('no cancel/reschedule link anywhere in the output (spec §0 non-goal)', () => {
  var r = buildReminderEmail(Object.assign({}, BASE, { stage: '48h' }));
  assert.strictEqual(r.text.indexOf('http'), -1, 'text must contain no link');
  assert.strictEqual(r.html.indexOf('<a '), -1, 'html must contain no anchor tag');
});

test('practiceAddress appears in the footer of both text and html (CAN-SPAM physical address)', () => {
  var r = buildReminderEmail(Object.assign({}, BASE, { stage: '48h' }));
  assert.ok(r.text.indexOf('123 Main St, Springfield, IL') !== -1, 'text footer should include the address');
  assert.ok(r.html.indexOf('123 Main St, Springfield, IL') !== -1, 'html footer should include the address');
});

test('missing practicePhone falls back to a generic call-the-office line, not a blank/broken sentence', () => {
  var r = buildReminderEmail(Object.assign({}, BASE, { stage: '48h', practicePhone: '' }));
  assert.ok(r.text.indexOf('call the office') !== -1, 'should fall back to a generic call line');
});

test('a name containing HTML-special characters is escaped in html but literal in text', () => {
  var r = buildReminderEmail(Object.assign({}, BASE, { stage: '48h', patientName: 'A & B <Co>' }));
  assert.ok(r.html.indexOf('A &amp; B &lt;Co&gt;') !== -1, 'html should escape the name');
  assert.ok(r.text.indexOf('A & B <Co>') !== -1, 'text should keep the name literal, unescaped');
});

test('missing practiceName falls back to a generic label, never a blank subject', () => {
  var r = buildReminderEmail({ stage: '48h', startTimeISO: BASE.startTimeISO });
  assert.ok(r.subject.indexOf('Your dental practice') !== -1, 'should fall back to a generic practice label');
});

console.log(passed + ' passed' + (process.exitCode ? ', with failures above' : ''));
