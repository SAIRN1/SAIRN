// api/greeting.test.js
//
// Run:  node --test api/greeting.test.js
//
// The greeting endpoint, which existed as a 404 for the life of the feature.
//
// Two properties carry the weight here and neither is about the wording:
//
//   1. IT NEVER ECHOES CALLER INPUT. sairnscape.html injects the result with
//      innerHTML inside a template literal, so anything this returns is parsed
//      as HTML by the browser. A greeting that contained a caller-supplied
//      string would be reflected XSS on every app open.
//   2. IT IS DETERMINISTIC. Same app, same hour, same weekday, same sentence.
//      No Math.random(), no clock read, no model call -- so it is testable, and
//      "what did it say to me" has an answer.

'use strict';
const test = require('node:test');
const assert = require('node:assert');
const handler = require('./greeting.js');
const { buildGreeting, APPS } = handler;

function mkRes() {
  const r = { statusCode: null, body: null, headers: {} };
  r.status = (c) => { r.statusCode = c; return r; };
  r.json = (b) => { r.body = b; return r; };
  r.setHeader = (k, v) => { r.headers[k] = v; };
  return r;
}
async function call(body, method, query) {
  const res = mkRes();
  await handler({ method: method || 'POST', body: body, query: query || {}, headers: {} }, res);
  return res;
}

// ── THE SECURITY PROPERTY ──────────────────────────────────────────────────

test('a hostile app_id is never echoed into the greeting', async () => {
  const payloads = [
    '<img src=x onerror=alert(1)>',
    '"><script>alert(1)</script>',
    'sairnscape<script>',
    "javascript:alert(1)",
    '{{constructor.constructor("alert(1)")()}}',
    '<script>'
  ];
  for (const p of payloads) {
    const r = await call({ app_id: p, client_hour: 9, client_day: 1 });
    assert.strictEqual(r.statusCode, 200);
    assert.strictEqual(r.body.greeting.indexOf('<'), -1, 'markup reached the greeting: ' + p);
    assert.strictEqual(r.body.greeting.indexOf(p.slice(0, 8)), -1, 'input was echoed: ' + p);
  }
});

test('an unknown app falls through to neutral copy rather than erroring', async () => {
  const r = await call({ app_id: 'sairnnotathing', client_hour: 9, client_day: 1 });
  assert.strictEqual(r.statusCode, 200);
  assert.match(r.body.greeting, /^Morning\./);
  // ...and it does not name a business it knows nothing about.
  assert.strictEqual(/properties|slabs|matters|residents/.test(r.body.greeting), false);
});

test('the response contains nothing but a greeting string', async () => {
  const r = await call({ app_id: 'sairnscape', client_hour: 9, client_day: 1 });
  assert.deepStrictEqual(Object.keys(r.body), ['greeting']);
  assert.strictEqual(typeof r.body.greeting, 'string');
});

test('no request field other than app_id, hour and day can reach the output', async () => {
  const r = await call({
    app_id: 'sairnscape', client_hour: 9, client_day: 1,
    name: 'INJECTED', greeting: 'INJECTED', extra: 'INJECTED', license_key: 'INJECTED'
  });
  assert.strictEqual(r.body.greeting.indexOf('INJECTED'), -1);
});

// ── DETERMINISM ────────────────────────────────────────────────────────────

test('same inputs, same sentence, every time', () => {
  const a = buildGreeting('sairnscape', 9, 1);
  for (let i = 0; i < 50; i++) {
    assert.strictEqual(buildGreeting('sairnscape', 9, 1), a);
  }
});

// CODE ONLY, comments stripped. The first version of these two tests matched
// the raw source and failed on this file's own header, which says "No
// Math.random()" -- the naive extraction finding the thing it was written to
// forbid. sql/demo_license_keys_seed.sql records the same mistake producing a
// phantom table count; stripping comments is the fix in both places.
function codeOnly() {
  const src = require('fs').readFileSync(require.resolve('./greeting.js'), 'utf8');
  return src.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');
}

test('no randomness and no server clock read', () => {
  const code = codeOnly();
  assert.strictEqual(/Math\.random\(/.test(code), false, 'the greeting is random');
  assert.strictEqual(/new Date\(/.test(code), false,
    'it reads the SERVER clock -- the client sends its own hour precisely because ' +
    'the server has no idea what timezone anybody is in');
});

test('it calls no model, touches no database, and pulls in nothing', () => {
  const code = codeOnly().toLowerCase();
  ['fetch(', 'supabase', 'anthropic', 'require('].forEach(function (needle) {
    assert.strictEqual(code.indexOf(needle), -1,
      'the greeting endpoint reaches out to ' + needle);
  });
});

// ── THE CONTENT ────────────────────────────────────────────────────────────

test('the time of day matches the hour the CLIENT reported', async () => {
  const cases = [[6, /^Morning\./], [13, /^Afternoon\./], [19, /^Evening\./],
                 [23, /^Working late\./], [2, /^Working late\./]];
  for (const [hour, re] of cases) {
    const r = await call({ app_id: 'sairnscape', client_hour: hour, client_day: 1 });
    assert.match(r.body.greeting, re, 'hour ' + hour);
  }
});

test('the closing line rotates by weekday but never randomly', () => {
  const seen = new Set();
  for (let d = 0; d <= 6; d++) seen.add(buildGreeting('sairnscape', 9, d));
  assert.strictEqual(seen.size, 7, 'two weekdays produce the same sentence');
});

test('every app in the table gets its own vocabulary', () => {
  const words = Object.keys(APPS).map((a) => buildGreeting(a, 9, 1));
  assert.strictEqual(new Set(words).size > 1, true);
  assert.match(buildGreeting('stonedesk', 9, 1), /slabs, quotes and jobs/);
  assert.match(buildGreeting('sairnlaw', 9, 1), /matters and deadlines/);
});

test('every app that CALLS this endpoint is in the table', () => {
  // A live caller missing from APPS silently gets neutral copy forever, which
  // reads as "the feature does not work for us".
  const fs = require('fs');
  const path = require('path');
  const root = path.join(__dirname, '..');
  fs.readdirSync(root).filter((f) => /\.html$/.test(f)).forEach((f) => {
    const src = fs.readFileSync(path.join(root, f), 'utf8');
    if (src.indexOf('/api/greeting') === -1) return;
    const app = f.replace('.html', '').replace('-hr', '');
    assert.ok(Object.prototype.hasOwnProperty.call(APPS, app),
      f + ' calls /api/greeting but "' + app + '" is not in the APPS table');
  });
});

// ── THE EDGES ──────────────────────────────────────────────────────────────

test('a missing hour still produces a real greeting, not a blank', async () => {
  const r = await call({ app_id: 'sairnscape' });
  assert.strictEqual(r.statusCode, 200);
  assert.ok(r.body.greeting.length > 10);
  assert.match(r.body.greeting, /Ready when you are/);
});

test('an out-of-range or non-numeric hour is treated as absent, not as midnight', async () => {
  // Number('') is 0, which would silently mean "late". parseInt plus a range
  // check is what stops an empty field becoming a specific wrong answer.
  for (const h of ['', 'nine', 99, -1, null, {}]) {
    const r = await call({ app_id: 'sairnscape', client_hour: h, client_day: 1 });
    assert.match(r.body.greeting, /Ready when you are/, 'hour ' + JSON.stringify(h));
  }
});

test('an out-of-range weekday falls back rather than returning undefined', async () => {
  const r = await call({ app_id: 'sairnscape', client_hour: 9, client_day: 77 });
  assert.strictEqual(r.body.greeting.indexOf('undefined'), -1);
  assert.ok(r.body.greeting.trim().endsWith('?'));
});

test('an empty body is a 200 with a usable greeting', async () => {
  const r = await call({});
  assert.strictEqual(r.statusCode, 200);
  assert.ok(r.body.greeting.length > 10);
});

test('a string body is parsed, and unparseable JSON does not 500', async () => {
  const ok = await call(JSON.stringify({ app_id: 'stonedesk', client_hour: 9, client_day: 1 }));
  assert.match(ok.body.greeting, /slabs/);
  const bad = await call('{not json');
  assert.strictEqual(bad.statusCode, 200);
});

test('GET works and reads the query string', async () => {
  const r = await call(null, 'GET', { app_id: 'sairnlaw', client_hour: '9', client_day: '1' });
  assert.strictEqual(r.statusCode, 200);
  assert.match(r.body.greeting, /^Morning\./);
  assert.match(r.body.greeting, /matters and deadlines/);
});

test('an unsupported method is refused', async () => {
  const r = await call({}, 'DELETE');
  assert.strictEqual(r.statusCode, 405);
});

test('the response is cacheable -- it is the same for everyone in that hour', async () => {
  const r = await call({ app_id: 'sairnscape', client_hour: 9, client_day: 1 });
  assert.match(r.headers['Cache-Control'] || '', /max-age=/);
});
