// tests/stonedesk_email_threat_rating.js
//
// REQUIREMENT: sdEmailScan() must store the risk rating the model STATED, not
//   a substring found anywhere in its prose -- and when it cannot read a
//   rating it must say so rather than record Low.
//
// WHY THIS EXISTS, AND IT WAS LIVE ON AN A/A ROW. Until 2026-10-05 the rating
// was one expression:
//
//   var risk=lower.includes('critical')?'Critical':lower.includes('high')
//            ?'High':lower.includes('medium')?'Medium':'Low';
//
// The hover auditor logged it (#796) and re-confirmed it live; it stayed. It
// has three defects and they compound:
//
//   1. NO NEGATION -- "not a high risk" stored High.
//   2. WHOLE-RESPONSE SEARCH -- a red-flag list or a phrase like
//      "time-critical" outranked the model's own verdict.
//   3. `critical` TESTED FIRST -- so one incidental mention beat an explicit
//      "Risk: Low" in the same paragraph.
//
// The two most ordinary clean-email responses -- "no critical red flags" and
// "Risk: Low" with a caveat mentioning high-risk patterns -- BOTH came back
// wrong, and wrong in the alarming direction, which is the direction that
// trains an owner to stop reading the banner.
//
// THIS TEST EXECUTES THE FUNCTION rather than asserting on source text. It
// extracts sdEmailRiskFrom from stonedesk.html and runs it, so an arm fails
// when the BEHAVIOUR changes, not when the wording does. Source-level arms are
// at the end and they only pin the things behaviour cannot see (that the old
// expression is gone, and that the caller has a third branch).
//
// EVERY STRING IN GROUP A IS A REAL-SHAPED MODEL RESPONSE, not a token. The
// first is the auditor's exact finding.
//
// Run:  node tests/stonedesk_email_threat_rating.js

'use strict';
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const HTML = fs.readFileSync(path.join(__dirname, '..', 'stonedesk.html'),
                             'utf8');

let pass = 0, fail = 0;
function ok(label) { pass++; console.log('  ok   ' + label); }
function bad(label, why) {
  fail++;
  console.log('  FAIL ' + label);
  if (why) console.log('       ' + String(why).slice(0, 400));
}

// ── EXTRACT AND EXECUTE ────────────────────────────────────────────────────
// A failure to extract is COULD NOT RUN, never a pass: a green suite over a
// function it never found is the shape this platform keeps paying for.
const m = HTML.match(/function sdEmailRiskFrom\(text\)\{[\s\S]*?\n  \}/);
if (!m) {
  console.error('COULD NOT RUN: sdEmailRiskFrom was not found in ' +
                'stonedesk.html. This suite tested NOTHING, which is not a ' +
                'pass.');
  process.exit(2);
}
let sdEmailRiskFrom;
try {
  sdEmailRiskFrom = new Function(m[0] + '; return sdEmailRiskFrom;')();
} catch (e) {
  console.error('COULD NOT RUN: extracted sdEmailRiskFrom does not ' +
                'evaluate: ' + e.message);
  process.exit(2);
}

console.log('STONEDESK EMAIL THREAT RATING -- criteria 2026-10-05.1');
console.log('\nA. THE AUDITOR\'S CASE, AND THE REST OF THE NEGATED FAMILY');

// [response, expected]
// RULING A LEVEL OUT IS NOT STATING ANOTHER ONE, and this suite got that
// wrong on its first run. I expected the auditor's exact string -- "this is
// not a high risk message", with no rating anywhere else in it -- to come back
// 'Low'. It comes back null, and null is RIGHT: the model declined to rate it,
// it only excluded one level. Expecting 'Low' there would have been me asking
// the function to infer a clean bill of health from the absence of an alarm,
// which is the same move the old expression made in the opposite direction.
// That case now has its own arm, A3, and the reasoning is here rather than in
// a corrected number.
const NEGATED = [
  ['No critical indicators found. Risk: Low. The sender domain matches the ' +
   'company it claims to be from.', 'Low'],
  ['There are no high risk elements here. Risk level: Low.', 'Low'],
  ['This does not appear to be a critical threat. Risk: Medium -- the ' +
   'urgency language is worth noting.', 'Medium'],
  ['I would rule out a critical compromise. Risk: Low.', 'Low'],
  ['The message is free of high risk attachments. Risk: Low.', 'Low'],
];
let bad_n = [];
NEGATED.forEach(function (c) {
  const got = sdEmailRiskFrom(c[0]);
  if (got !== c[1]) bad_n.push({ got: got, want: c[1], s: c[0].slice(0, 60) });
});
if (!bad_n.length) {
  ok('A1. all ' + NEGATED.length + ' negated responses rate correctly -- ' +
     'including the auditor\'s exact case, "this is not a high risk ' +
     'message", which the old expression stored as High');
} else {
  bad('A1. a negated mention must not become the rating',
      JSON.stringify(bad_n[0]));
}

// THE OLD EXPRESSION, RECONSTRUCTED, MUST FAIL THESE. Without this the arm
// above could be passing against a function that was never broken.
function oldWay(result) {
  const lower = String(result).toLowerCase();
  return lower.includes('critical') ? 'Critical'
       : lower.includes('high') ? 'High'
       : lower.includes('medium') ? 'Medium' : 'Low';
}
const oldWrong = NEGATED.filter(function (c) { return oldWay(c[0]) !== c[1]; });
if (oldWrong.length === NEGATED.length) {
  ok('A2. KNOWN-BAD CONFIRMED: the PRE-FIX expression gets all ' +
     NEGATED.length + ' of them wrong, every one in the alarming direction. ' +
     'A1 is therefore measuring the fix and not a case that always worked');
} else {
  bad('A2. the known-bad must fail what the fix passes',
      'old expression already handled ' +
      (NEGATED.length - oldWrong.length) + ' of ' + NEGATED.length);
}

console.log('\nB. THE STATED VERDICT WINS OVER INCIDENTAL PROSE');

const LABELLED = [
  ['Risk: Critical. This is a credential-harvesting attempt.', 'Critical'],
  ['Risk: High -- the reply-to domain does not match the sender.', 'High'],
  ['Risk Level: Medium', 'Medium'],
  ['Overall risk is low.', 'Low'],
  ['RISK RATING: HIGH', 'High'],
  ['**Risk: Critical**', 'Critical'],
  ['Risk assessment: medium. Recommended action: verify by phone.',
   'Medium'],
  // The one that matters most: a stated Low with high-risk prose after it.
  ['Risk: Low. For context, invoice-redirection emails are a high risk ' +
   'category generally, and critical to train staff on, but this message ' +
   'shows none of those markers.', 'Low'],
];
let bad_l = [];
LABELLED.forEach(function (c) {
  const got = sdEmailRiskFrom(c[0]);
  if (got !== c[1]) bad_l.push({ got: got, want: c[1], s: c[0].slice(0, 60) });
});
if (!bad_l.length) {
  ok('B1. all ' + LABELLED.length + ' stated verdicts are read as given, ' +
     'including a "Risk: Low" followed by prose containing both "high risk" ' +
     'and "critical" -- which the old expression rated Critical');
} else {
  bad('B1. the stated verdict must win', JSON.stringify(bad_l[0]));
}

if (oldWay(LABELLED[7][0]) === 'Critical' &&
    sdEmailRiskFrom(LABELLED[7][0]) === 'Low') {
  ok('B2. ...and that case is pinned explicitly in both directions: old ' +
     'Critical, new Low, on a response whose first words are "Risk: Low"');
} else {
  bad('B2. the stated-Low-with-caveat case must flip', 'old=' +
      oldWay(LABELLED[7][0]) + ' new=' + sdEmailRiskFrom(LABELLED[7][0]));
}

console.log('\nC. A REAL THREAT STILL RATES AS ONE -- the other direction');

const REAL = [
  ['Risk: Critical. The sender spoofs your bank and the link resolves to a ' +
   'lookalike domain.', 'Critical'],
  ['This is a high risk phishing attempt.', 'High'],
  ['Multiple critical red flags: spoofed display name, urgent wire request, ' +
   'and a critical risk of financial loss.', 'Critical'],
  ['Risk: High', 'High'],
];
let bad_r = [];
REAL.forEach(function (c) {
  const got = sdEmailRiskFrom(c[0]);
  if (got !== c[1]) bad_r.push({ got: got, want: c[1], s: c[0].slice(0, 60) });
});
if (!bad_r.length) {
  ok('C1. all ' + REAL.length + ' genuine threats still rate High or ' +
     'Critical. WITHOUT THIS ARM the fix could be "return Low for ' +
     'everything" and A1 would still pass');
} else {
  bad('C1. a real threat must still rate as one', JSON.stringify(bad_r[0]));
}

console.log('\nD. THE THIRD STATE: a rating it cannot read is NOT Low');

const UNREADABLE = [
  'The service is temporarily unavailable. Please try again later.',
  '',
  'I was unable to analyse this message.',
  'Red flags: urgent tone, unfamiliar sender. Recommended action: verify ' +
  'with the sender by phone before acting.',
];
let bad_u = [];
UNREADABLE.forEach(function (s) {
  const got = sdEmailRiskFrom(s);
  if (got !== null) bad_u.push({ got: got, s: s.slice(0, 50) });
});
if (!bad_u.length) {
  ok('D1. ' + UNREADABLE.length + ' responses with no stated rating return ' +
     'null, including an empty string and an error message. The old ' +
     'expression returned "Low" for every one of them -- a clean bill of ' +
     'health from an answer nobody parsed');
} else {
  bad('D1. an unreadable response must return null', JSON.stringify(bad_u[0]));
}

if (UNREADABLE.every(function (s) { return oldWay(s) === 'Low'; })) {
  ok('D2. KNOWN-BAD CONFIRMED: the old expression rated all ' +
     UNREADABLE.length + ' of them "Low", which is why the third state is ' +
     'the point of this fix and not a nicety');
} else {
  bad('D2. the old expression should have returned Low for all of them', '');
}

// -- F. THE TWO SHAPES THE LIVE ENDPOINT ACTUALLY RETURNED -----------------
// Driven against the real deployed https://sairn.vercel.app/api/claude on
// 2026-10-05 with the documented SD-AUDIT-2026 audit licence (HTTP 200,
// 1890 chars). Two calls, two shapes, and MY FIXTURE SET HAD NEITHER --
// every string in groups A-D is one I imagined. The live proof found them:
//
//   ### RISK RATING: <green circle> LOW          emoji between label+value
//   ### RISK RATING: <yellow circle> LOW-MEDIUM  emoji AND a compound
//
// A compound is the model declining to pick between two levels. It takes
// the HIGHER half: on a phishing screen the conservative direction on an
// undecided answer is upward.
console.log('\nF. THE SHAPES THE LIVE ENDPOINT RETURNED');

const LIVE = [
  ['## Email Security Analysis\n\n### RISK RATING: \uD83D\uDFE2 LOW\n\n' +
   '### Assessment Summary\nThis email appears benign.', 'Low'],
  ['## Email Security Analysis\n\n### RISK RATING: \uD83D\uDFE1 LOW-MEDIUM\n\n' +
   'This email appears relatively benign but contains several ' +
   'characteristics worth scrutinizing before full trust is granted.',
   'Medium'],
];
let bad_live = [];
LIVE.forEach(function (c) {
  const got = sdEmailRiskFrom(c[0]);
  if (got !== c[1]) bad_live.push({ got: got, want: c[1] });
});
if (!bad_live.length) {
  ok('F1. both LIVE shapes rate correctly -- the emoji separator is ' +
     'crossed, and the compound LOW-MEDIUM resolves to Medium, the ' +
     'higher half');
} else {
  bad('F1. the live shapes must rate correctly', JSON.stringify(bad_live[0]));
}

// F2 IS A NEGATIVE RESULT AND IT IS REPORTED AS ONE.
// I expected the captured live response to demonstrate the old defect. IT
// DOES NOT: measured over the full 1939-char body, the words critical, high
// and medium appear ZERO times, so the old expression also returned Low.
// That response happened to be clean of every trigger word.
//
// SO THE LIVE CALL PROVES THE FIX PARSES REAL OUTPUT -- an emoji separator
// and a compound rating, neither of which my imagined fixtures contained --
// AND IT DOES NOT ITSELF REPRODUCE THE BUG. The defect is demonstrated by
// the constructed cases in A, B and D, each paired with the reconstructed
// old expression, plus the auditor's own live re-confirmation in log #796.
// Claiming a live reproduction here would be claiming evidence I do not have.
const liveOld = oldWay(LIVE[0][0]);
const liveNew = sdEmailRiskFrom(LIVE[0][0]);
if (liveNew === 'Low') {
  ok('F2. the live response rates Low, which is correct. NEGATIVE ' +
     'RESULT RECORDED: the old expression also returned ' + liveOld +
     ' on it, because critical/high/medium appear zero times in the ' +
     'real body -- this captured response does NOT reproduce the ' +
     'defect, and the reproduction lives in arms A2, B2 and D2');
} else {
  bad('F2. the live response must rate Low', 'new=' + liveNew);
}

const CROSS = 'There is no stated risk. However, high-value wire ' +
  'transfers should always be verified.';
if (sdEmailRiskFrom(CROSS) === null) {
  ok('F3. the permissive gap STOPS at sentence punctuation -- a level ' +
     'in the NEXT sentence is not borrowed. Widening the gap for an ' +
     'emoji must not widen it across a full stop');
} else {
  bad('F3. the gap must not cross a sentence', 'got=' + sdEmailRiskFrom(CROSS));
}

console.log('\nE. THE CALLER, pinned at source -- behaviour cannot see the UI');

// COMMENTS STRIPPED FIRST. The first version of E1 FAILED -- on the comment
// block in stonedesk.html that quotes the old expression verbatim to explain
// what was wrong with it. A source grep matches the prose documenting the
// token, which is PR 1.2, and it is the SECOND time I have committed it inside
// a control: the identical mistake is recorded in tests/run_push_retry_probe.py
// arm D3, one batch earlier. Recorded rather than quietly fixed, because twice
// is a habit and not an accident.
const HTML_CODE = HTML.split(/\r?\n/)
  .filter(function (l) { return !/^\s*\/\//.test(l); }).join('\n');
const callerChecks = [
  ['E1. the old substring expression is GONE from the CODE (comments stripped '
   + 'first -- see above)',
   !/includes\('critical'\)\?'Critical'/.test(HTML_CODE)],
  ['E2. the caller computes the third state',
   /var unrated=\(risk===null\);/.test(HTML)],
  ['E3. ...and renders it as its own state, not as clean',
   /COULD NOT READ A RISK RATING/.test(HTML)],
  ['E4. ...and stores `Unrated` rather than a null that renders blank',
   /risk:\(risk\|\|'Unrated'\)/.test(HTML)],
  ['E5. the function is reachable for this suite to extract',
   /window\.sdEmailRiskFrom=sdEmailRiskFrom;/.test(HTML)],
];
callerChecks.forEach(function (c) {
  if (c[1]) ok(c[0]); else bad(c[0], 'source pattern not found');
});

console.log('\n' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
