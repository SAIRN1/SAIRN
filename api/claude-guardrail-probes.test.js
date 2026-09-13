// api/claude-guardrail-probes.test.js
//
// Run:  node api/claude-guardrail-probes.test.js
//
// ITEM 8, THE HALF THAT NEEDS NO ENGINE AND NO MODEL CALL. Every assertion
// here is about this proxy's OWN branching, so the suite is free to run, is
// deterministic, and never sends a token to Anthropic. The generic
// jailbreak/toxicity corpus is Anthropic's surface and is a separate,
// separately-approved piece of work (docs/2026-09-13-ai-red-teaming-scoping.md).
//
// ── WHY A SECOND FILE RATHER THAN MORE OF claude-cost-controls.test.js ────
// That suite is scoped to the two 2026-09-05 cost findings -- the max_tokens
// clamp and the limiter's is_demo bypass -- and it already covers max_tokens
// coercion and all four licence states in both modes. Nothing here repeats it.
// What was uncovered, and is covered here, is the OTHER three guardrails:
//
//   1. the app_id allowlist          -- KNOWN_APP_IDS
//   2. the server-tool type whitelist -- ALLOWED_SERVER_TOOL_TYPES
//   3. the tool-use ceiling           -- MAX_TOOL_USES_CEILING
//
// ── TWO REAL DEFECTS, FOUND BY RUNNING sanitizeTools RATHER THAN READING IT ─
// Both are the SAME CLASS the file already documents one screen earlier for
// max_tokens, resolved the opposite way on the neighbouring function:
//
//   * GARBAGE BOUGHT THE CEILING. `Number(t.max_uses) || MAX_TOOL_USES_CEILING`
//     is falsy for 0, "abc", NaN and null, so every one of them came out as 5
//     -- the MAXIMUM number of billed web searches. cappedMaxTokens(), thirty
//     lines up, deliberately falls back to the DEFAULT and says in its own
//     comment that "garbage in should not buy the largest generation
//     available". Measured: 0 -> 5, "abc" -> 5, null -> 5.
//   * AN ARRAY COERCED. `[2]` came out as max_uses 2, because Number([2]) is 2
//     -- verbatim the trap cappedMaxTokens() type-checks against and this line
//     did not.
//
// ABSENT is deliberately NOT treated as garbage and is unchanged at the
// ceiling: a caller that sends no max_uses is not sending a wrong value, and
// the server cap is the documented answer for it. Changing that would be a
// behaviour change nobody asked for, dressed as a bug fix.
//
// ── THE CONTROL AT THE BOTTOM IS NOT OPTIONAL ────────────────────────────
// Section 5 rebuilds a deliberately-broken sanitizeTools and asserts THIS
// SUITE'S OWN checks reject it. Five promoted checkers on this platform had no
// control proving they could fire, and 21 of 37 negative controls never verify
// their sabotage landed. A suite that has only ever been green is not known to
// be a suite.

'use strict';
const assert = require('assert');

let pass = 0, fail = 0;
const run = [];
function t(name, fn) { run.push([name, fn]); }
function section(s) { run.push([s, null]); }

// The limiter and the licence store are stubbed for the reason
// claude-cost-controls.test.js records: on a developer machine SUPABASE_URL is
// unset, the real ones throw, and every state would collapse to `error` -- a
// suite written against that would pass whether the logic is right or not.
const LIMITER = require.resolve('./_lib/ai-rate-limit');
let limiterCalls = [];
require.cache[LIMITER] = {
  id: LIMITER, filename: LIMITER, loaded: true,
  exports: {
    checkAiRateLimit: async (appId) => { limiterCalls.push(appId); return { allowed: true, rowId: 'r', degraded: false }; },
    recordAiUsage: async () => {},
  },
};
const LICENCE = require.resolve('./_lib/license');
require.cache[LICENCE] = {
  id: LICENCE, filename: LICENCE, loaded: true,
  exports: { validateLicenseKey: async () => ({ valid: true, active: true, license_hash: 'h' }) },
};

process.env.ANTHROPIC_API_KEY = process.env.ANTHROPIC_API_KEY || 'test-key';
process.env.SAIRN_CLAUDE_AUTH_MODE = 'observe';

delete require.cache[require.resolve('./claude.js')];
const handler = require('./claude.js');
const { sanitizeTools, KNOWN_APP_IDS, ALLOWED_SERVER_TOOL_TYPES, MAX_TOOL_USES_CEILING } = handler;

// Anthropic is stubbed. This suite must never make a real paid call.
let sentBody = null;
let anthropicCalls = 0;
global.fetch = async function (url, opts) {
  anthropicCalls += 1;
  sentBody = JSON.parse(opts.body);
  return {
    ok: true, status: 200,
    json: async () => ({ content: [{ type: 'text', text: 'ok' }], usage: { input_tokens: 1, output_tokens: 1 } }),
  };
};

function mockRes() {
  const res = { _s: 0, _j: null };
  res.status = function (c) { res._s = c; return res; };
  res.json = function (o) { res._j = o; return res; };
  res.setHeader = function () { return res; };
  return res;
}

async function call(body) {
  sentBody = null; anthropicCalls = 0; limiterCalls = [];
  const res = mockRes();
  await handler({ method: 'POST', headers: {}, body }, res);
  return { status: res._s, body: res._j, sent: sentBody, anthropicCalls: anthropicCalls };
}

const MSG = [{ role: 'user', content: 'hi' }];
const SERVER_TOOL = ALLOWED_SERVER_TOOL_TYPES[0];

// ─────────────────────────────────────────────────────────────────────────
section('--- 1. the app_id allowlist ---');

t('an app_id that is not on the list is refused with 400', async () => {
  const r = await call({ app_id: 'sairnnotreal', is_demo: true, messages: MSG });
  assert.strictEqual(r.status, 400, JSON.stringify(r.body));
  assert.ok(/app_id/i.test(r.body.error.message), 'the refusal does not say what was wrong');
});

t('AND IT NEVER REACHES ANTHROPIC -- a refusal that still spends the key is not a refusal', async () => {
  const r = await call({ app_id: 'sairnnotreal', is_demo: true, messages: MSG });
  assert.strictEqual(r.anthropicCalls, 0);
});

t('a MISSING app_id is refused too, not defaulted', async () => {
  const r = await call({ is_demo: true, messages: MSG });
  assert.strictEqual(r.status, 400);
});

t('an EMPTY-STRING app_id is refused -- falsy, and the check must not let it through', async () => {
  const r = await call({ app_id: '', is_demo: true, messages: MSG });
  assert.strictEqual(r.status, 400);
});

t('EVERY id on the list is actually accepted -- this list has silently 400d live '
  + 'apps three times (2026-07-26 nine apps, SAIRNsenior, and two caught at build time)', async () => {
  const refused = [];
  for (const id of KNOWN_APP_IDS) {
    const r = await call({ app_id: id, is_demo: true, messages: MSG });
    if (r.status !== 200) refused.push(id + ' -> ' + r.status);
  }
  assert.deepStrictEqual(refused, [], 'allowlisted ids the proxy still refuses');
});

t('the allowlist is not empty and has no duplicates -- a duplicate is the trace '
  + 'of a merge that added an id twice', () => {
  assert.ok(KNOWN_APP_IDS.length > 0);
  assert.strictEqual(new Set(KNOWN_APP_IDS).size, KNOWN_APP_IDS.length);
});

// ─────────────────────────────────────────────────────────────────────────
section('--- 2. the server-tool type whitelist ---');

t('an allowlisted server tool passes through', () => {
  const out = sanitizeTools([{ type: SERVER_TOOL, name: 'web_search' }]);
  assert.strictEqual(out.length, 1);
  assert.strictEqual(out[0].type, SERVER_TOOL);
});

t('a server tool type that is NOT allowlisted is dropped', () => {
  assert.strictEqual(sanitizeTools([{ type: 'code_execution_20250522' }]), undefined);
});

t('dropping every tool returns undefined, not an empty array -- Anthropic rejects '
  + 'tools:[] and a caller would see a 400 it could not explain', () => {
  assert.strictEqual(sanitizeTools([{ type: 'bash_20250124' }, { type: 'nope' }]), undefined);
});

t('a MIXED array keeps only the allowlisted one', () => {
  const out = sanitizeTools([{ type: 'code_execution_20250522' }, { type: SERVER_TOOL }]);
  assert.strictEqual(out.length, 1);
  assert.strictEqual(out[0].type, SERVER_TOOL);
});

t('a null or non-object entry does not crash the filter', () => {
  assert.strictEqual(sanitizeTools([null, undefined, 0, '']), undefined);
});

t('a non-array tools value is ignored entirely', () => {
  assert.strictEqual(sanitizeTools('web_search'), undefined);
  assert.strictEqual(sanitizeTools({ type: SERVER_TOOL }), undefined);
});

t('THE WHITELIST REACHES THE WIRE, not just the helper -- the HTTP path must '
  + 'send the sanitized tools and not the raw body', async () => {
  const r = await call({
    app_id: 'stonedesk', is_demo: true, messages: MSG,
    tools: [{ type: 'code_execution_20250522' }, { type: SERVER_TOOL, max_uses: 99 }],
  });
  assert.strictEqual(r.status, 200, JSON.stringify(r.body));
  assert.strictEqual(r.sent.tools.length, 1, 'a non-allowlisted server tool reached Anthropic');
  assert.strictEqual(r.sent.tools[0].max_uses, MAX_TOOL_USES_CEILING);
});

// ─────────────────────────────────────────────────────────────────────────
section('--- 3. the tool-use ceiling, and the direction garbage falls ---');

function uses(v) { return sanitizeTools([{ type: SERVER_TOOL, max_uses: v }])[0].max_uses; }

t('above the ceiling is clamped DOWN to it', () => {
  assert.strictEqual(uses(99), MAX_TOOL_USES_CEILING);
});

t('below one is clamped UP to one', () => {
  assert.strictEqual(uses(-3), 1);
  assert.strictEqual(uses(0.2), 1);
});

t('a legitimate value in range is untouched', () => {
  assert.strictEqual(uses(1), 1);
  assert.strictEqual(uses(3), 3);
});

t('ABSENT is not garbage -- no max_uses means the server cap, and that is '
  + 'unchanged behaviour rather than a bug', () => {
  assert.strictEqual(uses(undefined), MAX_TOOL_USES_CEILING);
  const bare = sanitizeTools([{ type: SERVER_TOOL }]);
  assert.strictEqual(bare[0].max_uses, MAX_TOOL_USES_CEILING);
});

t('GARBAGE MUST NOT BUY THE CEILING -- the same rule cappedMaxTokens() states '
  + 'thirty lines up, on the neighbouring function', () => {
  // Measured before this assertion existed: every one of these came out as 5.
  assert.strictEqual(uses('abc'), 1, '"abc" bought the maximum billed searches');
  assert.strictEqual(uses(0), 1, '0 bought the maximum');
  assert.strictEqual(uses(null), 1, 'null bought the maximum');
  assert.strictEqual(uses(NaN), 1, 'NaN bought the maximum');
  assert.strictEqual(uses({}), 1, 'an object bought the maximum');
});

t('AN ARRAY DOES NOT COERCE -- Number([2]) is 2, verbatim the trap '
  + 'cappedMaxTokens() type-checks against', () => {
  assert.strictEqual(uses([2]), 1, 'a single-element array coerced to a use count');
  assert.strictEqual(uses([]), 1);
});

t('a BOOLEAN does not coerce either -- Number(true) is 1, which looks harmless '
  + 'and is still a value nobody sent', () => {
  assert.strictEqual(uses(true), 1);
  assert.strictEqual(uses(false), 1);
});

t('a NUMERIC STRING is honoured, because that is a real value expressed in the '
  + 'shape a form sends -- refusing it would break a legitimate caller', () => {
  assert.strictEqual(uses('3'), 3);
  assert.strictEqual(uses('99'), MAX_TOOL_USES_CEILING);
});

// ─────────────────────────────────────────────────────────────────────────
section('--- 4. custom (client-executed) tools are a different category ---');

t('a tool with NO type is custom and passes through unmodified', () => {
  const tool = { name: 'lookup_slab', input_schema: { type: 'object' } };
  const out = sanitizeTools([tool]);
  assert.deepStrictEqual(out, [tool], 'a custom tool was rewritten');
});

t('an explicit type:"custom" passes through unmodified too -- both are valid '
  + 'Anthropic custom-tool shapes', () => {
  const tool = { type: 'custom', name: 'x', input_schema: {} };
  assert.deepStrictEqual(sanitizeTools([tool]), [tool]);
});

t('a custom tool is NOT given a max_uses -- the ceiling is a server-tool concept '
  + 'and Anthropic never executes a custom tool', () => {
  const out = sanitizeTools([{ name: 'x', input_schema: {} }]);
  assert.strictEqual(out[0].max_uses, undefined);
});

// ─────────────────────────────────────────────────────────────────────────
section('--- 5. THE CONTROL: these checks must be able to go RED ---');

// A copy of sanitizeTools with the type filter removed and the clamp inverted.
// If section 2 and 3's assertions pass against THIS, they are not testing
// anything. Rebuilt here rather than monkey-patched because the real one is a
// module-scope const the suite cannot reach -- and a control that silently
// fails to apply is the 21-of-37 shape this platform is burning down.
function brokenSanitizeTools(tools) {
  if (!Array.isArray(tools)) return undefined;
  const clean = tools.filter(Boolean).map((tt) => {
    if (tt.type === undefined || tt.type === 'custom') return tt;
    return { type: tt.type, name: tt.name || 'web_search', max_uses: Number(tt.max_uses) || 5 };
  });
  return clean.length ? clean : undefined;
}

t('CONTROL APPLIED: the broken copy really does differ from the real one', () => {
  const real = sanitizeTools([{ type: 'code_execution_20250522' }]);
  const mutant = brokenSanitizeTools([{ type: 'code_execution_20250522' }]);
  assert.notDeepStrictEqual(real, mutant,
    'the control is a no-op -- it is not testing the suite, it is testing nothing');
});

t('CONTROL FIRES: the whitelist assertion rejects the broken copy', () => {
  assert.throws(() => {
    assert.strictEqual(brokenSanitizeTools([{ type: 'code_execution_20250522' }]), undefined);
  }, 'a sanitizer with no type filter passed the whitelist check');
});

t('CONTROL FIRES: the garbage-direction assertion rejects the broken copy', () => {
  assert.throws(() => {
    assert.strictEqual(brokenSanitizeTools([{ type: SERVER_TOOL, max_uses: 'abc' }])[0].max_uses, 1);
  }, 'a sanitizer where garbage buys the ceiling passed the ceiling check');
});

// ─────────────────────────────────────────────────────────────────────────
(async function main() {
  for (const [name, fn] of run) {
    if (fn === null) { console.log('\n' + name); continue; }
    try { await fn(); pass += 1; console.log('  PASS  ' + name); }
    catch (e) { fail += 1; console.log('  FAIL  ' + name + '\n        ' + e.message); }
  }
  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  console.log('anthropic calls made: 0 by construction -- global.fetch is stubbed for the whole file');
  process.exit(fail ? 1 : 0);
})();
