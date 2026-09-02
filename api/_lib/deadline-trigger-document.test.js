// The trigger-document discriminator -- the mechanism, tested on synthetic
// rules so it is verified independently of any jurisdiction's data.
//
// WHAT IT GUARDS. computeDeadline() counts from whatever date it is handed and
// never asked what that date MEANT. For 48 seeded rows the trigger is a term of
// art naming one specific document, and four states start the appeal clock four
// different ways: Texas from the SIGNING of the judgment, Florida from its
// RENDITION, six jurisdictions from its ENTRY on the docket, New York from
// SERVICE of a copy with written notice of entry. West Virginia uses two
// different documents inside one state.
//
// THE TWO CLASSES FAIL IN OPPOSITE DIRECTIONS, WHICH IS WHY THERE ARE TWO
// BEHAVIOURS. Supplying an EARLIER document's date than the rule means reports
// EARLY, which is safe. Supplying a LATER one reports LATE -- and 31 of the 48
// are appellate, where a late notice of appeal is jurisdictional and not
// curable. So the appellate class REFUSES until the caller affirms which
// document, and the civil class returns a date with the assumption made
// visible.
//
// THE REFUSAL MUST HAPPEN BEFORE ANY ARITHMETIC. A guard that fires after a
// date has been computed leaves a date in the response for someone to read, and
// the whole point is that no date exists to be misread. Asserted directly.

const engine = require('./deadline-engine.js');

let pass = 0, fail = 0;
function check(name, actual, expected) {
  const a = JSON.stringify(actual), e = JSON.stringify(expected);
  if (a === e) { pass++; return; }
  fail++;
  console.log('FAIL  ' + name + '\n        expected ' + e + '\n        actual   ' + a);
}

const DOC = {
  id: 'signing_of_the_judgment',
  label: 'the date the trial court SIGNED the judgment',
  not_the: 'the date it was entered on the docket, filed, or mailed to the parties',
  authority: 'Tex. R. App. P. 26.1',
  on_unconfirmed: 'refuse'
};
const WARN_DOC = Object.assign({}, DOC, { on_unconfirmed: 'warn' });

// ── 1. The declaration validator ─────────────────────────────────────────
check('a complete declaration is valid', engine.triggerDocumentDefects(DOC), []);
check('an absent declaration is valid -- 360 rows have none', engine.triggerDocumentDefects(undefined), []);
check('null is valid', engine.triggerDocumentDefects(null), []);
check('a non-object is a defect', engine.triggerDocumentDefects('signing'), ['must be an object']);
check('an array is a defect', engine.triggerDocumentDefects([DOC]), ['must be an object']);
for (const k of ['id', 'label', 'not_the', 'authority', 'on_unconfirmed']) {
  const partial = Object.assign({}, DOC);
  delete partial[k];
  check('a declaration missing ' + k + ' is a defect',
    engine.triggerDocumentDefects(partial).some(d => d.indexOf(k) !== -1), true);
}
check('an empty string counts as missing',
  engine.triggerDocumentDefects(Object.assign({}, DOC, { label: '   ' })).length, 1);
check('on_unconfirmed must be refuse or warn',
  engine.triggerDocumentDefects(Object.assign({}, DOC, { on_unconfirmed: 'maybe' })).length, 1);
check('warn is accepted', engine.triggerDocumentDefects(WARN_DOC), []);

// ── 2. The resolver, in isolation ────────────────────────────────────────
const R = { rule_id: 'synthetic-refuse', trigger_document: DOC };
const W = { rule_id: 'synthetic-warn', trigger_document: WARN_DOC };
check('a rule with no declaration resolves to null',
  engine.resolveTriggerDocument({ rule_id: 'plain' }, {}), null);
check('refuse + nothing supplied -> TRIGGER_DOCUMENT_UNCONFIRMED',
  engine.resolveTriggerDocument(R, {}).code, 'TRIGGER_DOCUMENT_UNCONFIRMED');
check('and the refusal names the id the caller must send',
  engine.resolveTriggerDocument(R, {}).expected, 'signing_of_the_judgment');
check('and says which direction the wrong reading fails in',
  /LATE/.test(engine.resolveTriggerDocument(R, {}).message), true);
check('refuse + correct id -> confirmed',
  engine.resolveTriggerDocument(R, { trigger_document: 'signing_of_the_judgment' }).state, 'confirmed');
check('warn + nothing supplied -> unconfirmed, and it is NOT a refusal',
  [engine.resolveTriggerDocument(W, {}).ok, engine.resolveTriggerDocument(W, {}).state], [true, 'unconfirmed']);
check('and the warning says the readings run EARLIER, which is why a date is still returned',
  /EARLIER/.test(engine.resolveTriggerDocument(W, {}).detail), true);
// An affirmative WRONG answer is worse than silence.
check('warn + a MISMATCHED id still refuses',
  engine.resolveTriggerDocument(W, { trigger_document: 'entry_of_judgment' }).code, 'TRIGGER_DOCUMENT_MISMATCH');
check('refuse + a mismatched id refuses with the same code',
  engine.resolveTriggerDocument(R, { trigger_document: 'entry_of_judgment' }).code, 'TRIGGER_DOCUMENT_MISMATCH');
check('the mismatch reports both what was expected and what was claimed',
  [engine.resolveTriggerDocument(R, { trigger_document: 'rendition' }).expected,
   engine.resolveTriggerDocument(R, { trigger_document: 'rendition' }).supplied],
  ['signing_of_the_judgment', 'rendition']);
check('a malformed declaration refuses rather than degrading to warn',
  engine.resolveTriggerDocument({ rule_id: 'bad', trigger_document: { id: 'x' } }).code,
  'INVALID_TRIGGER_DOCUMENT');

// ── 3. End to end, through computeDeadline ───────────────────────────────
const calendars = { zz: { 2026: [{ date: '2026-12-25', name: 'Christmas', kind: 'declared' }] } };
function rule(extra) {
  return Object.assign({
    rule_id: 'zz-test-appeal-30',
    jurisdiction: 'zz', domain: 'appellate', label: 'test',
    trigger_event: 'trigger', computation: 'frcp_6a',
    count: { value: 30, unit: 'calendar_days', direction: 'forward' },
    authority: { citation: 'TEST', url: null, quote: null, note: null, retrieved_at: null },
    effective_from: '2000-01-01', effective_to: null
  }, extra);
}
function compute(rules, extra) {
  return engine.computeDeadline(Object.assign({
    jurisdiction: 'zz', domain: rules[0].domain, trigger_event: 'trigger',
    trigger_date: '2026-06-01', rules: rules, calendars: calendars, as_of: '2026-06-01'
  }, extra || {}));
}

// A rule with no declaration is completely untouched -- the 360-row case.
const plain = compute([rule()]);
check('a rule with no declaration computes as before', [plain.ok, plain.due_date], [true, '2026-07-01']);
check('and reports trigger_document: null rather than omitting the field',
  Object.prototype.hasOwnProperty.call(plain, 'trigger_document') && plain.trigger_document, null);

// The appellate class: refuse.
const unconfirmed = compute([rule({ trigger_document: DOC })]);
check('an appellate row REFUSES when the document is not confirmed',
  [unconfirmed.ok, unconfirmed.code], [false, 'TRIGGER_DOCUMENT_UNCONFIRMED']);
check('AND NO DATE IS RETURNED WITH THE REFUSAL -- the guard runs before any arithmetic',
  unconfirmed.due_date, undefined);
check('the refusal tells the caller exactly what to send',
  /trigger_document: "signing_of_the_judgment"/.test(unconfirmed.message), true);
check('and names the authority that makes it a term of art',
  /Tex\. R\. App\. P\. 26\.1/.test(unconfirmed.message), true);

const confirmed = compute([rule({ trigger_document: DOC })], { trigger_document: 'signing_of_the_judgment' });
check('a CORRECT confirmation computes the real date',
  [confirmed.ok, confirmed.due_date], [true, '2026-07-01']);
check('and the result records that it was confirmed, not assumed',
  confirmed.trigger_document.state, 'confirmed');

const mismatched = compute([rule({ trigger_document: DOC })], { trigger_document: 'entry_of_judgment' });
check('a WRONG confirmation refuses rather than computing',
  [mismatched.ok, mismatched.code], [false, 'TRIGGER_DOCUMENT_MISMATCH']);
check('and returns no date either', mismatched.due_date, undefined);

// The civil class: warn.
const warned = compute([rule({ domain: 'civil-litigation', trigger_document: WARN_DOC })]);
check('a civil row RETURNS a date when unconfirmed',
  [warned.ok, warned.due_date], [true, '2026-07-01']);
check('but records the assumption on the result rather than silently',
  warned.trigger_document.state, 'unconfirmed');
check('the same civil row confirms cleanly when the caller does affirm',
  compute([rule({ domain: 'civil-litigation', trigger_document: WARN_DOC })],
          { trigger_document: 'signing_of_the_judgment' }).trigger_document.state, 'confirmed');

// A malformed declaration withholds the date.
const malformed = compute([rule({ trigger_document: { id: 'x', label: 'y' } })]);
check('a malformed declaration refuses and returns no date',
  [malformed.ok, malformed.code, malformed.due_date], [false, 'INVALID_TRIGGER_DOCUMENT', undefined]);

// ── 4. The write-time guard ──────────────────────────────────────────────
// validateRulePayload is not exported, so this is a source-presence check and
// is labelled as one. The engine-side guard above is the load-bearing test;
// this exists so the write-time rejection cannot be deleted unnoticed.
const fs = require('fs');
const path = require('path');
const endpointSrc = fs.readFileSync(path.join(__dirname, '..', 'legal-deadlines.js'), 'utf8');
check('the endpoint validator rejects a malformed trigger_document at write time',
  /trigger_document\.on_unconfirmed must be "refuse" or "warn"/.test(endpointSrc), true);
check('and requires every declared key', /trigger_document\.' \+ k \+ ' is required/.test(endpointSrc), true);
check('the endpoint forwards the caller input', /trigger_document: body\.trigger_document/.test(endpointSrc), true);

console.log('\ndeadline-trigger-document: ' + pass + ' passed, ' + fail + ' failed');
if (fail) process.exit(1);
