// api/b22-claude-logline.test.js
//
// Run:  node api/b22-claude-logline.test.js
//
// REQUIREMENT (b22): api/claude.js's pre-auth `auth_observe` log line must
// render `app_id` as a single safe token -- validated against KNOWN_APP_IDS,
// and otherwise emitted sanitised, labelled and length-capped -- so no request
// body can inject a forged log line.
//
// ── WHY A LOG LINE IS WORTH A SUITE ───────────────────────────────────────
// `console.log('api/claude auth_observe app_id=' + body.app_id + ' state=' +
// authState + ' mode=' + claudeAuthMode)` ran on EVERY call, BEFORE the
// allowlist check, including unauthenticated ones. A newline in `app_id`
// writes a SECOND line that is indistinguishable from a real one:
//
//   api/claude auth_observe app_id=x
//   api/claude auth_observe app_id=stonedesk state=valid mode=enforce
//
// The forged `state=valid` is the point. `auth_observe` exists BECAUSE
// SAIRN_CLAUDE_AUTH_MODE defaults to `observe` -- the log IS the evidence an
// operator reads to decide whether auth is working. A log an attacker can
// write entries into is not evidence, and the entries it cannot be trusted on
// are exactly the ones somebody is looking at during an incident.
//
// ── WHY THE VALUE IS SANITISED RATHER THAN DROPPED ────────────────────────
// This file's own history is the argument. SAIRNsenior's every AI call 400ed
// silently for weeks and was found because a refusal NAMED the unrecognised
// app_id. Erasing an unrecognised value "to be safe" would remove the one
// diagnostic here that has already paid for itself. So: recognised prints
// verbatim, anything else prints sanitised AND LABELLED.
//
// Exit: 0 all arms passed - 1 an arm FAILED

'use strict';
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const handler = require('./claude.js');
const logSafeAppId = handler.logSafeAppId;
const KNOWN_APP_IDS = handler.KNOWN_APP_IDS;
const LOG_APP_ID_MAX = handler.LOG_APP_ID_MAX;

// Everything a log reader or a terminal could treat as a break. The arms test
// the CLASS, not the one character in the proof-of-concept.
const BREAKERS = [
  ['\n', 'LF -- the proof of concept'],
  ['\r', 'CR alone -- forges a line on a CR-splitting reader'],
  ['\r\n', 'CRLF'],
  ['\u2028', 'U+2028 LINE SEPARATOR -- a break to many log viewers'],
  ['\u2029', 'U+2029 PARAGRAPH SEPARATOR'],
  ['\u001b', 'ESC -- drives a terminal that renders the log'],
  ['\u0000', 'NUL -- truncates a C-string consumer'],
  ['\u0008', 'BACKSPACE -- rewrites what a terminal already printed'],
  ['\u007f', 'DEL'],
  ['\u0085', 'NEL (C1) -- a line break in some encodings'],
];
const CTRL = /[\u0000-\u001f\u007f-\u009f\u2028\u2029]/;

let pass = 0, fail = 0;
const failed = [];
function t(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) {
    console.log('  FAIL ' + name + '\n       ' + e.message);
    fail++; failed.push(name.split('.')[0]);
  }
}
function section(s) { console.log('\n' + s); }

console.log('b22 -- the pre-auth auth_observe log line cannot be forged');

// ── A. THE FORGED-NEWLINE ARM ─────────────────────────────────────────────
section('A. a forged log line is impossible, for every break character');

t('A1. THE EXACT FORGERY: an app_id carrying a newline and a complete fake '
  + 'auth_observe entry renders as ONE line with no break in it', () => {
  const forgery = 'x\napi/claude auth_observe app_id=stonedesk state=valid mode=enforce';
  const out = logSafeAppId(forgery);
  assert.strictEqual(out.indexOf('\n'), -1, 'a newline survived: ' + JSON.stringify(out));
  assert.ok(!CTRL.test(out), 'a control character survived: ' + JSON.stringify(out));
  // AND THE FORGED FIELDS CANNOT READ AS REAL ONES. The sanitised text may
  // still contain the words, but it is inside a labelled, single-line token --
  // so assert there is no second ` state=` that a reader or a parser would
  // attribute to a separate entry.
  const line = 'api/claude auth_observe app_id=' + out + ' state=valid mode=observe';
  assert.strictEqual(line.split('\n').length, 1,
    'the rendered line is still two lines: ' + JSON.stringify(line));
});

t('A2. ...and that holds for EVERY break character, not just LF. A fix that '
  + 'stripped only newlines would pass A1 and leave CR, U+2028 and ESC open',
  () => {
    const survived = [];
    for (const pair of BREAKERS) {
      const ch = pair[0], why = pair[1];
      const out = logSafeAppId('pre' + ch + 'post');
      if (CTRL.test(out) || out.indexOf('\n') !== -1 || out.indexOf('\r') !== -1) {
        survived.push(why + ' -> ' + JSON.stringify(out));
      }
    }
    assert.strictEqual(survived.length, 0,
      'these break characters survived:\n       ' + survived.join('\n       '));
  });

t('A3. the sanitised value is LABELLED, so a reader and a grep can tell it '
  + 'from a real app_id. Without the label, "x" sanitised and the real app "x" '
  + 'would render identically', () => {
  const out = logSafeAppId('x\nforged');
  assert.ok(/^\(unrecognised:/.test(out),
    'the sanitised value is not labelled: ' + JSON.stringify(out));
  assert.ok(out.indexOf('xforged') !== -1,
    'the value was erased rather than sanitised -- the diagnostic is gone: '
    + JSON.stringify(out));
});

// ── B. THE NEGATIVE CONTROL ───────────────────────────────────────────────
section('B. NEGATIVE CONTROL -- real app_ids are untouched and the field still works');

t('B1. EVERY id in KNOWN_APP_IDS prints VERBATIM. Without this arm the fix '
  + 'could be labelling or truncating every real call and the forgery arms '
  + 'would all still pass', () => {
  assert.ok(Array.isArray(KNOWN_APP_IDS) && KNOWN_APP_IDS.length > 10,
    'KNOWN_APP_IDS is not the list this arm thinks it is');
  const wrong = KNOWN_APP_IDS.filter((a) => logSafeAppId(a) !== a);
  assert.strictEqual(wrong.length, 0,
    'these recognised app_ids were altered: ' + JSON.stringify(wrong));
});

t('B2. ...and the longest real app_id is comfortably inside the cap, so the '
  + 'cap can never truncate a legitimate value. If a future app name exceeds '
  + 'this, THIS ARM is the one that fails rather than the log quietly '
  + 'shortening it', () => {
  const longest = KNOWN_APP_IDS.reduce((a, b) => (b.length > a.length ? b : a), '');
  assert.ok(longest.length < LOG_APP_ID_MAX,
    'the longest app_id (' + longest + ', ' + longest.length + ') is not inside '
    + 'the cap of ' + LOG_APP_ID_MAX);
});

t('B3. an ABSENT app_id still reads "(none)" -- the pre-fix behaviour for the '
  + 'ordinary case is preserved exactly, because that is what an operator '
  + 'grepping old log lines expects to find', () => {
  assert.strictEqual(logSafeAppId(undefined), '(none)');
  assert.strictEqual(logSafeAppId(null), '(none)');
  assert.strictEqual(logSafeAppId(''), '(none)');
});

t('B4. a NON-STRING app_id names its type instead of being coerced. '
  + 'String({}) would print "[object Object]" as though somebody had typed it, '
  + 'which is a different wrong answer rather than a safe one', () => {
  assert.ok(/non-string:object/.test(logSafeAppId({})), logSafeAppId({}));
  assert.ok(/non-string:object/.test(logSafeAppId(['a'])), logSafeAppId(['a']));
  assert.ok(/non-string:number/.test(logSafeAppId(7)), logSafeAppId(7));
  for (const v of [{}, ['a'], 7, true]) {
    assert.ok(!CTRL.test(logSafeAppId(v)), 'control char from ' + typeof v);
  }
});

// ── C. THE CAP ────────────────────────────────────────────────────────────
section('C. the length cap, which is the hole stripping alone leaves open');

t('C1. a 5,000-character app_id is capped. Stripping control characters stops '
  + 'a FORGED line; it does nothing about an unbounded value making every real '
  + 'line unreadable on every call', () => {
  const out = logSafeAppId('A'.repeat(5000));
  assert.ok(out.length <= LOG_APP_ID_MAX + '(unrecognised:)'.length,
    'the value was not capped: length ' + out.length);
  assert.ok(out.indexOf('A'.repeat(LOG_APP_ID_MAX)) !== -1,
    'the cap kept fewer characters than it claims: ' + JSON.stringify(out));
});

t('C2. the cap is applied AFTER stripping, not before. 5,000 newlines followed '
  + 'by a forgery must not slip the forgery past a cap that already spent its '
  + 'budget on characters that were about to be removed', () => {
  const out = logSafeAppId('\n'.repeat(5000) + 'api/claude auth_observe app_id=stonedesk state=valid');
  assert.ok(!CTRL.test(out), JSON.stringify(out).slice(0, 120));
  assert.ok(out.length <= LOG_APP_ID_MAX + '(unrecognised:)'.length,
    'length ' + out.length);
  // The visible remainder is the START of the sanitised text, which is what a
  // reader needs to recognise what was sent.
  assert.ok(out.indexOf('api/claude') !== -1,
    'stripping-then-capping lost the diagnostic entirely: ' + JSON.stringify(out));
});

// ── D. THE ABLATION ───────────────────────────────────────────────────────
section('D. ABLATION -- restore the raw interpolation and A1 must go RED');

t('D1. with logSafeAppId REMOVED from the log line, the forgery renders as TWO '
  + 'lines -- the pre-b22 behaviour reproduced on purpose, so A1 is testing '
  + 'this helper and not something else', () => {
  const src = fs.readFileSync(path.join(__dirname, 'claude.js'), 'utf8');
  const ENCODED = "'api/claude auth_observe app_id=' + logSafeAppId(body.app_id) +";
  const RAW = "'api/claude auth_observe app_id=' + (body.app_id || '(none)') +";
  assert.notStrictEqual(src.indexOf(ENCODED), -1,
    'the log line no longer calls logSafeAppId -- the ablation anchor has '
    + 'drifted, so this arm is not ablating anything. RE-SEAT THE ANCHOR, do '
    + 'not delete the arm.');
  // The ablation is proved on the RENDERING, which is what the defect was:
  // reproduce both spellings of the same concatenation and compare.
  const forgery = 'x\napi/claude auth_observe app_id=stonedesk state=valid mode=enforce';
  const rawLine = 'api/claude auth_observe app_id=' + (forgery || '(none)')
                + ' state=absent mode=observe';
  const safeLine = 'api/claude auth_observe app_id=' + logSafeAppId(forgery)
                 + ' state=absent mode=observe';
  assert.strictEqual(rawLine.split('\n').length, 2,
    'the RAW rendering did not forge a second line, so the payload is not '
    + 'actually an injection and A1 proves nothing');
  assert.strictEqual(safeLine.split('\n').length, 1,
    'the SAFE rendering still forges a line');
  // And the ablated source really would carry the raw form.
  const ablated = src.replace(ENCODED, RAW);
  assert.ok(ablated.indexOf(RAW) !== -1 && ablated.indexOf(ENCODED) === -1,
    'the ablation did not actually swap the call out');
});

t('D2. CLEAN -- the helper is not doing this by refusing everything. A '
  + 'recognised app_id renders in a one-line entry that still carries state '
  + 'and mode, which is the line an operator actually reads', () => {
  const line = 'api/claude auth_observe app_id=' + logSafeAppId('stonedesk')
             + ' state=valid mode=observe';
  assert.strictEqual(line,
    'api/claude auth_observe app_id=stonedesk state=valid mode=observe');
});

// ── E. THE LITERAL-BYTES RULE, ASSERTED ON THE SOURCE ─────────────────────
section('E. the sanitiser regex contains no literal control bytes');

t('E1. the character class is written with \\u escapes and contains NO literal '
  + 'control byte. The first draft embedded real control characters, which is '
  + 'the "regex shipped with a literal backspace" defect this platform has a '
  + 'standing rule about -- invisible in review, and here a hard SyntaxError',
  () => {
    const src = fs.readFileSync(path.join(__dirname, 'claude.js'), 'utf8');
    const i = src.indexOf('.replace(/[');
    assert.notStrictEqual(i, -1, 'the sanitiser replace() was not found');
    const line = src.slice(i, src.indexOf('\n', i));
    assert.ok(!CTRL.test(line),
      'the regex source carries a LITERAL control byte: ' + JSON.stringify(line));
    assert.ok(line.indexOf('\\u0000') !== -1 && line.indexOf('\\u2028') !== -1,
      'the class is not written with \\u escapes: ' + line);
  });

console.log('\nb22 claude logline: ' + pass + ' passed, ' + fail + ' failed');
if (fail) console.log('FAILED: ' + failed.join(', '));
process.exit(fail ? 1 : 0);
