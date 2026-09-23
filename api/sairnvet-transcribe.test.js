// api/sairnvet-transcribe.test.js
// REQUIREMENT: the ambient scribe refuses to transcribe until a self-hosted
//   transcription host is configured, and never degrades to a third-party one
//
// Run:  node --test api/sairnvet-transcribe.test.js
//
// WHAT THESE TESTS ARE ACTUALLY DEFENDING. The decision recorded on 2026-09-23
// was that exam-room audio goes to a SELF-HOSTED model -- not Chrome's
// SpeechRecognition, not a paid ASR. The host does not exist yet, so the only
// correct behaviour today is a refusal that says why.
//
// The failure this suite is built to catch is not a crash. It is somebody, at
// some point, adding a "just for now" fallback so the feature demos -- which
// silently reverses the decision, because a temporary route to the exact vendor
// that was rejected is indistinguishable from choosing that vendor.
//
// So the assertions are deliberately blunt: a perfectly-formed request with a
// valid-looking licence and real audio must STILL be refused, and the source
// must contain no third-party speech vendor at all.

'use strict';
const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');
const handler = require('./sairnvet-transcribe.js');

function mkRes() {
  const r = { statusCode: null, body: null, headers: {} };
  r.status = (c) => { r.statusCode = c; return r; };
  r.json = (b) => { r.body = b; return r; };
  r.setHeader = (k, v) => { r.headers[k] = v; };
  return r;
}

// A request with nothing wrong with it. Every field the contract asks for is
// present and well-formed. It must still be refused.
function goodRequest() {
  return {
    method: 'POST',
    headers: { authorization: 'Bearer SV-TEST-0000-0000' },
    body: {
      app_id: 'sairnvet',
      consent_ref: 'svc-1758600000000',
      audio: 'UklGRiQAAABXQVZFZm10IBAAAAABAAEAgD4AAAB9AAACABAAZGF0YQAAAAA=',
      mime: 'audio/webm',
      sample_ms: 4200
    }
  };
}

async function call(req) {
  const res = mkRes();
  await handler(req, res);
  return res;
}

// ── THE PROPERTY THE WHOLE FILE EXISTS FOR ─────────────────────────────────

test('a perfectly-formed request is refused while no host is configured', async () => {
  delete process.env.SAIRNVET_TRANSCRIBE_URL;
  const res = await call(goodRequest());
  assert.strictEqual(res.statusCode, 503);
  assert.strictEqual(res.body.ok, false);
  assert.strictEqual(res.body.error.code, 'TRANSCRIBE_HOST_NOT_CONFIGURED');
});

test('the refusal SAYS WHY, and says dictation still works -- a bare 503 would read as an outage', async () => {
  delete process.env.SAIRNVET_TRANSCRIBE_URL;
  const res = await call(goodRequest());
  const m = res.body.error.message;
  assert.ok(/self-hosted/i.test(m), 'the refusal must name the reason, not just fail');
  assert.ok(/will NOT fall back/i.test(m), 'the refusal must say there is no degraded mode');
  assert.ok(/dictation/i.test(m), 'the refusal must point at the path that does work');
});

test('an empty or whitespace host env is NOT configured -- a blank var is absence, not a value', async () => {
  for (const v of ['', '   ']) {
    process.env.SAIRNVET_TRANSCRIBE_URL = v;
    const res = await call(goodRequest());
    assert.strictEqual(res.body.error.code, 'TRANSCRIBE_HOST_NOT_CONFIGURED',
      'blank host env must refuse, not be read as a host');
  }
  delete process.env.SAIRNVET_TRANSCRIBE_URL;
});

// ── THE PRIVACY ORDERING ───────────────────────────────────────────────────

test('the host check runs BEFORE the licence check, so unconfigured never touches the audio path', async () => {
  delete process.env.SAIRNVET_TRANSCRIBE_URL;
  // No Authorization header at all. If the licence were checked first this
  // would be 401. It must be 503: with no host, the request is refused before
  // anything reads the body.
  const req = goodRequest();
  req.headers = {};
  const res = await call(req);
  assert.strictEqual(res.statusCode, 503);
  assert.strictEqual(res.body.error.code, 'TRANSCRIBE_HOST_NOT_CONFIGURED');
});

test('no refusal ever echoes the audio, the consent ref, or any caller string', async () => {
  delete process.env.SAIRNVET_TRANSCRIBE_URL;
  const req = goodRequest();
  req.body.consent_ref = '<script>alert(1)</script>';
  req.body.audio = 'AAAA-DISTINCTIVE-AUDIO-MARKER-AAAA';
  const res = await call(req);
  const serialised = JSON.stringify(res.body);
  assert.ok(!serialised.includes('DISTINCTIVE-AUDIO-MARKER'), 'audio must never appear in a response');
  assert.ok(!serialised.includes('<script>'), 'caller input must never be echoed');
});

test('GET is refused and does not leak the host state', async () => {
  process.env.SAIRNVET_TRANSCRIBE_URL = 'https://example.invalid/asr';
  const res = await call({ method: 'GET', headers: {}, body: {} });
  assert.strictEqual(res.statusCode, 405);
  delete process.env.SAIRNVET_TRANSCRIBE_URL;
});

// ── THE SOURCE-LEVEL GUARD ─────────────────────────────────────────────────
//
// The tests above prove the behaviour of the handler as written. This one
// proves something the behaviour cannot: that no fallback was ADDED. A
// SpeechRecognition fallback would live in the client, or behind a branch this
// suite does not reach, and would still pass every assertion above.

test('the endpoint source names no third-party speech vendor and has no fallback branch', () => {
  const src = fs.readFileSync(path.join(__dirname, 'sairnvet-transcribe.js'), 'utf8');
  // Comments in this file legitimately NAME the rejected vendors in order to
  // reject them, so the check is on executable intent, not on the strings: no
  // network call to anywhere at all lives in this file today.
  assert.ok(!/\bfetch\s*\(/.test(src), 'this endpoint makes no outbound call while the host does not exist');
  assert.ok(!/webkitSpeechRecognition|SpeechRecognition\s*\(/.test(src),
    'a browser speech API must never appear in server code');
});

test('hostConfigured() is the SINGLE place the host env is read', () => {
  const src = fs.readFileSync(path.join(__dirname, 'sairnvet-transcribe.js'), 'utf8');
  const reads = src.match(/process\.env\.SAIRNVET_TRANSCRIBE_URL/g) || [];
  assert.strictEqual(reads.length, 1,
    'more than one read of the host env means the fail-closed gate can be bypassed in one of them');
});

// ── AND THE CLIENT HALF, CHECKED FROM HERE ─────────────────────────────────
//
// The scoping document's warning is about the APP falling back, not the
// endpoint. sairnvet.html already ships browser-native SpeechRecognition for
// push-to-talk dictation and that is unchanged and correct -- so the check is
// not "the string is absent from the app", it is "the scribe module does not
// reach for it".

// ── THE COMMENT STRIPPER, AND WHY IT IS A SCANNER AND NOT A REGEX ─────────
// The regex version was `s.replace(/\/\*[\s\S]*?\*\//g,' ')` then
// `.replace(/(^|[^:])\/\/[^\n]*/g,'$1')`, and it HID REAL CODE. The `[^:]`
// guard protects `http://` and nothing else, so a `//` inside a STRING or a
// REGEX literal took the whole rest of that line with it -- including the
// `SpeechRecognition` reference the check exists to find. Two attacks that
// defeated it, both now fixtures below:
//
//     var x = 'a//b'; var SR = window.SpeechRecognition;
//     var re = /\/\//;  var SR = window.SpeechRecognition;
//
// Found by tests/sairnvet_scribe_review_probe.js on 2026-09-23 and measured
// LATENT at the time -- no line in the shipped scribe module had that shape,
// so nothing was actually hidden. It is fixed anyway, because "the source it
// is pointed at happens not to contain the shape today" is a property of the
// source, not of the check, and this check is the only thing standing between
// a fallback branch and the claim that there is none.
//
// A REGEX CANNOT DO THIS. Whether a `/` opens a comment, opens a regex, or is
// a division depends on what came before it, and that is a state machine.
// This is a small one: normal / line-comment / block-comment / single /
// double / template / regex-literal, walking one character at a time.
//
// THE ONE HEURISTIC, NAMED because it is the part that can be wrong: telling
// a regex literal from division. A `/` starts a regex when the previous
// meaningful character is one of `( , = : [ ! & | ? { } ; return` or nothing
// -- the standard rule. It is not a parser and it does not need to be: the
// worst case of getting it wrong is that a division is treated as a regex,
// which swallows text up to the next `/` on that line and would make the
// check REPORT A REFERENCE IT SHOULD HAVE FOUND -- loud, not silent. The
// fixtures at the bottom drive that direction too.
function stripComments(src) {
  let out = '';
  let i = 0;
  let prev = '';                     // last emitted non-space character
  const n = src.length;
  while (i < n) {
    const c = src[i], d = src[i + 1];
    if (c === '/' && d === '/') {            // line comment
      while (i < n && src[i] !== '\n') i++;
      continue;
    }
    if (c === '/' && d === '*') {            // block comment
      i += 2;
      while (i < n && !(src[i] === '*' && src[i + 1] === '/')) i++;
      i += 2;
      out += ' ';
      continue;
    }
    if (c === '"' || c === "'" || c === '`') {   // string or template
      const q = c;
      out += c; i++;
      while (i < n) {
        if (src[i] === '\\') { out += src[i] + (src[i + 1] || ''); i += 2; continue; }
        out += src[i];
        if (src[i] === q) { i++; break; }
        i++;
      }
      prev = q;
      continue;
    }
    if (c === '/' && /[(,=:[!&|?{};]|^$/.test(prev || '')) {   // regex literal
      out += c; i++;
      let inClass = false;
      while (i < n) {
        if (src[i] === '\\') { out += src[i] + (src[i + 1] || ''); i += 2; continue; }
        if (src[i] === '[') inClass = true;
        else if (src[i] === ']') inClass = false;
        out += src[i];
        if (src[i] === '/' && !inClass) { i++; break; }
        if (src[i] === '\n') { i++; break; }   // unterminated: do not run away
        i++;
      }
      prev = '/';
      continue;
    }
    out += c;
    if (!/\s/.test(c)) prev = c;
    i++;
  }
  return out;
}

test('the scribe module in sairnvet.html does not reference SpeechRecognition', () => {
  const app = fs.readFileSync(path.join(__dirname, '..', 'sairnvet.html'), 'utf8');
  const start = app.indexOf('SAIRNVET AMBIENT SCRIBE');
  assert.ok(start > -1, 'the ambient scribe module must be present and findable by its banner');
  const end = app.indexOf('END AMBIENT SCRIBE', start);
  assert.ok(end > start, 'the ambient scribe module must carry a closing banner so this check has bounds');
  const mod = app.slice(start, end);

  // COMMENTS ARE STRIPPED BEFORE THE ASSERTION, and that is not a loophole.
  // The module's own header NAMES SpeechRecognition in order to reject it --
  // "there is no fallback branch in this module and there must never be one"
  // -- and a check that failed on the explanation would push the next author
  // to delete the reasoning rather than keep the rule. The ban is on CODE.
  // This was not foreseen: the first run of this test failed on its own
  // module's header, which is the check working.
  const code = stripComments(mod);

  assert.ok(!/SpeechRecognition/.test(code),
    'the scribe must not fall back to the browser speech API that 6.2 rejected');
  assert.ok(/sairnvet-transcribe/.test(code),
    'the scribe must call the first-party endpoint');
});

// ── THE FIXTURE, AND IT NOW CARRIES THE TWO SHAPES THAT DEFEATED V1 ──────
// Every case below is a real attack or its paired positive. The two marked
// WAS BROKEN are the ones the regex version hid: an independent review drove
// them on 2026-09-23 and both took the rest of the line with them, which
// would have let a real fallback branch sit behind a string containing `//`
// and still pass this suite.
test('the comment-stripper does not swallow executable code', () => {
  const survives = [
    ['a reference after a line comment on an earlier line',
     '// the api\nvar SR = window.SpeechRecognition;'],
    ['a url containing // on the same line',
     "fetch('/api/sairnvet-transcribe', o); var SR = window.SpeechRecognition; // call"],
    ['WAS BROKEN: a // inside a STRING literal',
     "var x = 'a//b'; var SR = window.SpeechRecognition;"],
    ['WAS BROKEN: a // inside a REGEX literal',
     'var re = /\\/\\//; var SR = window.SpeechRecognition;'],
    ['a // inside a template literal',
     'var t = `a//b`; var SR = window.SpeechRecognition;'],
    ['a */ inside a string before real code',
     "var s = '*/'; /* c */ var SR = window.SpeechRecognition;"],
    ['an apostrophe inside a double-quoted string',
     'var s = "it\'s fine"; var SR = window.SpeechRecognition;'],
    ['a division that is not a regex',
     'var r = a / b; var SR = window.SpeechRecognition;']
  ];
  survives.forEach(function (c) {
    const out = stripComments(c[1]);
    // Both tokens the module check reads back: the banned one must still be
    // FINDABLE (or the ban is unenforceable) and the required one must
    // survive too (or `the scribe must call the first-party endpoint` could
    // fail on a stripper rather than on the module).
    if (/sairnvet-transcribe/.test(c[1])) {
      assert.ok(/sairnvet-transcribe/.test(out),
        'the endpoint URL was hidden by the stripper -- ' + c[0]);
    }
    assert.ok(/SpeechRecognition/.test(out),
      'the reference was HIDDEN by the stripper -- ' + c[0] + '\n  in:  ' + c[1]
      + '\n  out: ' + out);
  });

  const removed = [
    ['a line comment', '// we rejected SpeechRecognition'],
    ['a block comment', '/* we rejected\n SpeechRecognition */'],
    ['a trailing line comment', 'var a = 1; // SpeechRecognition'],
    ['a block comment mid-line', 'var a = /* SpeechRecognition */ 1;']
  ];
  removed.forEach(function (c) {
    assert.ok(!/SpeechRecognition/.test(stripComments(c[1])),
      'a comment survived stripping -- ' + c[0] + ': ' + c[1]);
  });
});

// THE PAIRED NEGATIVE CONTROL ON THE SCANNER ITSELF. Every assertion above is
// satisfied by a stripper that returns its input unchanged -- and that
// stripper would make the module check pass on a module whose HEADER names
// SpeechRecognition, which is the exact case stripping exists for. This arm
// fails such a stripper.
test('the stripper really strips -- a do-nothing one would fail here', () => {
  const src = 'var a = 1; // SpeechRecognition\n/* SpeechRecognition */';
  const out = stripComments(src);
  assert.ok(out !== src, 'the stripper returned its input unchanged');
  assert.ok(!/SpeechRecognition/.test(out));
  assert.ok(/var a = 1;/.test(out), 'it removed code as well as comments');
});
