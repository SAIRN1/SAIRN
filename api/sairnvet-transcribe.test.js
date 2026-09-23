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
  const code = mod
    .replace(/\/\*[\s\S]*?\*\//g, ' ')
    .replace(/(^|[^:])\/\/[^\n]*/g, '$1');

  assert.ok(!/SpeechRecognition/.test(code),
    'the scribe must not fall back to the browser speech API that 6.2 rejected');
  assert.ok(/sairnvet-transcribe/.test(code),
    'the scribe must call the first-party endpoint');
});

// The comment-stripper above must not be able to hide real code. If it ever
// strips something it should not, this fixture catches it.
test('the comment-stripper used by the check above does not swallow executable code', () => {
  const strip = (s) => s.replace(/\/\*[\s\S]*?\*\//g, ' ').replace(/(^|[^:])\/\/[^\n]*/g, '$1');
  assert.ok(/SpeechRecognition/.test(strip('var SR = window.SpeechRecognition; // the api')),
    'a real reference must survive stripping');
  assert.ok(/sairnvet-transcribe/.test(strip("fetch('/api/sairnvet-transcribe', o); // call")),
    'a url with // inside it must survive stripping');
  assert.ok(!/SpeechRecognition/.test(strip('// we rejected SpeechRecognition')),
    'a line comment must be stripped');
  assert.ok(!/SpeechRecognition/.test(strip('/* we rejected\n SpeechRecognition */')),
    'a block comment must be stripped');
});
