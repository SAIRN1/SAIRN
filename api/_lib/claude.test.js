// api/_lib/claude.test.js
// ---------------------------------------------------------------------------
// Plain node:assert tests — no test framework, matching api/'s existing
// zero-npm-dependency convention (see api/_lib/auth.test.js).
// Lives under api/_lib/ (not api/) because Vercel's filesystem routing turns
// every top-level api/*.js file into a live serverless function, but
// excludes underscore-prefixed paths -- a test file directly under api/
// would otherwise be a public endpoint that 500s on every request.
// Run: node api/_lib/claude.test.js
//
// WHY THIS EXISTS: sanitizeTools() is a security boundary (the file's own
// comment: "this endpoint has no other auth beyond a client-supplied
// app_id"). Confirms the existing web_search allowlist/cap behavior is
// unchanged, and that a custom client-executed tool (no cost/abuse risk —
// Anthropic never runs it, the browser does) now survives sanitization,
// before any app is wired to send one.
// ---------------------------------------------------------------------------

const assert = require('assert');
const { sanitizeTools } = require('../claude.js');

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

console.log('api/claude.js sanitizeTools()');

test('non-array input returns undefined', () => {
  assert.strictEqual(sanitizeTools(null), undefined);
  assert.strictEqual(sanitizeTools('not an array'), undefined);
});

test('empty array returns undefined', () => {
  assert.strictEqual(sanitizeTools([]), undefined);
});

test('web_search_20250305 passes through with default name and capped max_uses', () => {
  const out = sanitizeTools([{ type: 'web_search_20250305' }]);
  assert.strictEqual(out.length, 1);
  assert.strictEqual(out[0].type, 'web_search_20250305');
  assert.strictEqual(out[0].name, 'web_search');
  assert.strictEqual(out[0].max_uses, 5);
});

test('web_search_20250305 max_uses is capped at 5 even if the client asks for more', () => {
  const out = sanitizeTools([{ type: 'web_search_20250305', max_uses: 999 }]);
  assert.strictEqual(out[0].max_uses, 5);
});

test('an unknown server-tool type is still stripped', () => {
  const out = sanitizeTools([{ type: 'some_future_billed_tool' }]);
  assert.strictEqual(out, undefined);
});

test('a custom client tool (no type field) passes through unmodified', () => {
  const customTool = {
    name: 'get_employees',
    description: 'Look up the current employee roster.',
    input_schema: { type: 'object', properties: {}, required: [] }
  };
  const out = sanitizeTools([customTool]);
  assert.strictEqual(out.length, 1);
  assert.deepStrictEqual(out[0], customTool);
});

test('a custom client tool with type:"custom" passes through unmodified', () => {
  const customTool = {
    type: 'custom',
    name: 'get_employees',
    description: 'Look up the current employee roster.',
    input_schema: { type: 'object', properties: {}, required: [] }
  };
  const out = sanitizeTools([customTool]);
  assert.strictEqual(out.length, 1);
  assert.deepStrictEqual(out[0], customTool);
});

test('a mix of one allowed server tool and one custom tool both survive', () => {
  const out = sanitizeTools([
    { type: 'web_search_20250305' },
    { name: 'get_employees', description: 'x', input_schema: { type: 'object' } }
  ]);
  assert.strictEqual(out.length, 2);
});

console.log(passed + ' passed');
