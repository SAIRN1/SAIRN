// tests/prompt_budget.js
//
// Run:  node tests/prompt_budget.js
//
// [0039] The StoneDesk chat posted its ENTIRE conversation on every turn.
// `var history=[]` was appended to at four sites and cleared at exactly one --
// the user pressing Clear. A single tool_result can carry the whole Job
// Financials table, so one tool call adds more than a dozen ordinary turns.
//
// The bound is only worth having if the drop policy is correct, and the way a
// naive "drop the oldest N" breaks THIS chat is specific: Anthropic rejects a
// tool_result whose tool_use is missing, and vice versa. Most of the assertions
// below are about that pairing, not about the arithmetic.
//
// Functions are extracted from the real stonedesk.html rather than re-stated,
// so the test fails if the shipped implementation changes.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const ROOT = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(ROOT, 'stonedesk.html'), 'utf8');

function grab(startMarker, endMarker) {
  const s = html.indexOf(startMarker);
  assert.ok(s > 0, 'not found in stonedesk.html: ' + startMarker);
  const e = html.indexOf(endMarker, s);
  assert.ok(e > s, 'unterminated: ' + startMarker);
  return html.slice(s, e + endMarker.length);
}

const ctx = { console };
vm.createContext(ctx);
vm.runInContext(
  grab('var SD_TOK_CHARS = 4;', 'var SD_PROMPT_BUDGET_TOKENS = 20000;') + '\n' +
  grab('function sdEstTokens(v){', '\n  }') + '\n' +
  grab('function sdMsgGroups(msgs){', '\n  }') + '\n' +
  grab('function sdBudgetMessages(msgs, fixedTokens, budget){', '\n  }'),
  ctx
);
const { sdEstTokens, sdMsgGroups, sdBudgetMessages, SD_TOK_CHARS, SD_PROMPT_BUDGET_TOKENS } = ctx;

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('--- ' + t + ' ---'); }

const txt = n => 'x'.repeat(n);
const user = n => ({ role: 'user', content: txt(n) });
const asst = n => ({ role: 'assistant', content: txt(n) });
const toolUse = (id, n) => ({ role: 'assistant', content: [{ type: 'text', text: txt(n) }, { type: 'tool_use', id, name: 'get_job_profitability', input: {} }] });
const toolRes = (id, n) => ({ role: 'user', content: [{ type: 'tool_result', tool_use_id: id, content: txt(n) }] });

// ---------------------------------------------------------------------------
section('the estimate is an estimate, and says so by being simple');

test('a string estimates at chars/4, rounded up', () => {
  assert.strictEqual(SD_TOK_CHARS, 4);
  assert.strictEqual(sdEstTokens('x'.repeat(400)), 100);
  assert.strictEqual(sdEstTokens('xyz'), 1);
});

test('a structured content array is measured as its JSON, not skipped', () => {
  const blocks = [{ type: 'tool_result', tool_use_id: 'a', content: txt(4000) }];
  assert.ok(sdEstTokens(blocks) >= 1000, 'structured content was under-counted');
});

test('null and undefined cost nothing rather than throwing', () => {
  assert.strictEqual(sdEstTokens(null), 0);
  assert.strictEqual(sdEstTokens(undefined), 0);
});

// ---------------------------------------------------------------------------
section('a tool_use and its tool_result are ONE unit and never separated');

test('grouping pairs a tool_use assistant turn with the next message', () => {
  const h = [user(10), toolUse('t1', 10), toolRes('t1', 10), asst(10)];
  const g = sdMsgGroups(h);
  assert.strictEqual(g.length, 3);
  assert.strictEqual(g[1].length, 2, 'the tool pair was not grouped');
  assert.strictEqual(g[1][0].role, 'assistant');
  assert.strictEqual(g[1][1].role, 'user');
});

test('an assistant turn WITHOUT a tool_use is its own group', () => {
  const g = sdMsgGroups([asst(10), user(10)]);
  assert.strictEqual(g.length, 2);
});

test('a plain-string assistant turn is not mistaken for a tool turn', () => {
  const g = sdMsgGroups([{ role: 'assistant', content: 'tool_use' }, user(10)]);
  assert.strictEqual(g.length, 2, 'a string containing "tool_use" was grouped as one');
});

test('THE ONE THAT MATTERS: every surviving tool_use still has ITS OWN tool_result', () => {
  // Four tool pairs, none of which all fit. Whatever survives must be matched
  // BY ID -- an orphan of either half is a 400 from the API.
  //
  // Swept across budgets on purpose. A single budget can come out balanced by
  // luck even with the pairing logic disabled (it did, while this test was
  // being written), which would have made this the weakest assertion in the
  // file while reading as the strongest.
  const h = [];
  for (let i = 0; i < 4; i++) { h.push(toolUse('t' + i, 3000)); h.push(toolRes('t' + i, 3000)); }
  h.push(user(20));
  for (let budget = 100; budget <= 6500; budget += 137) {
    const plan = sdBudgetMessages(h, 0, budget);
    const useIds = plan.messages
      .filter(m => Array.isArray(m.content) && m.content.some(b => b.type === 'tool_use'))
      .map(m => m.content.find(b => b.type === 'tool_use').id).sort();
    const resIds = plan.messages
      .filter(m => Array.isArray(m.content) && m.content.some(b => b.type === 'tool_result'))
      .map(m => m.content.find(b => b.type === 'tool_result').tool_use_id).sort();
    assert.strictEqual(useIds.join(','), resIds.join(','),
      'orphaned tool block at budget=' + budget + ' (uses=[' + useIds + '] results=[' + resIds + '])');
  }
});

test('and it drops in whole pairs, never a half pair, even at the boundary', () => {
  const h = [toolUse('t0', 400), toolRes('t0', 400), toolUse('t1', 400), toolRes('t1', 400), user(20)];
  for (let budget = 50; budget <= 800; budget += 25) {
    const plan = sdBudgetMessages(h, 0, budget);
    const uses = plan.messages.filter(m => Array.isArray(m.content) && m.content.some(b => b.type === 'tool_use')).length;
    const ress = plan.messages.filter(m => Array.isArray(m.content) && m.content.some(b => b.type === 'tool_result')).length;
    assert.strictEqual(uses, ress, 'unbalanced at budget=' + budget);
  }
});

// ---------------------------------------------------------------------------
section('the drop policy itself');

test('a short conversation is passed through untouched', () => {
  const h = [user(100), asst(100), user(100)];
  const plan = sdBudgetMessages(h, 700, SD_PROMPT_BUDGET_TOKENS);
  assert.strictEqual(plan.dropped, 0);
  assert.strictEqual(plan.over, false);
  // Reference identity, not deep equality: the array comes back from the vm
  // realm, so its prototype differs from this realm's Array and
  // deepStrictEqual would fail on a correct result.
  assert.strictEqual(plan.messages.length, h.length);
  h.forEach((m, i) => assert.strictEqual(plan.messages[i], m));
});

test('over budget, the OLDEST go first', () => {
  const h = [user(4000), asst(4000), user(4000), asst(4000), user(40)];
  const plan = sdBudgetMessages(h, 0, 2200);
  assert.ok(plan.dropped > 0, 'nothing was dropped on an over-budget history');
  assert.strictEqual(plan.messages[plan.messages.length - 1], h[h.length - 1],
    'the newest message was not kept');
  assert.strictEqual(plan.messages.length + plan.dropped, h.length);
});

test('the last group is NEVER dropped, however small the budget', () => {
  const h = [user(4000), asst(4000), user(4000)];
  const plan = sdBudgetMessages(h, 0, 1);
  assert.strictEqual(plan.messages.length, 1);
  assert.strictEqual(plan.messages[0], h[2]);
});

test('and when even that does not fit, it is REPORTED, not swallowed', () => {
  const h = [user(4000), asst(4000), user(4000)];
  const plan = sdBudgetMessages(h, 0, 1);
  assert.strictEqual(plan.over, true, 'an irreducibly oversized request reported over:false');
});

test('over is false when the trimmed request genuinely fits', () => {
  const h = [user(4000), asst(4000), user(40)];
  const plan = sdBudgetMessages(h, 0, 2200);
  assert.strictEqual(plan.over, false);
});

test('the fixed cost (system prompt + tool defs) counts against the budget', () => {
  const h = [user(400), asst(400), user(40)];
  const loose = sdBudgetMessages(h, 0, 300);
  const tight = sdBudgetMessages(h, 290, 300);
  assert.ok(tight.dropped > loose.dropped,
    'raising the fixed cost did not tighten the budget');
});

test('history is NEVER mutated -- the on-screen chat stays whole', () => {
  const h = [user(4000), asst(4000), user(4000), user(40)];
  const before = JSON.stringify(h);
  sdBudgetMessages(h, 0, 100);
  assert.strictEqual(JSON.stringify(h), before, 'the caller\'s history array was modified');
});

test('an empty history does not throw and reports nothing dropped', () => {
  const plan = sdBudgetMessages([], 100, 20000);
  assert.strictEqual(plan.messages.length, 0);
  assert.strictEqual(plan.dropped, 0);
});

// ---------------------------------------------------------------------------
section('the call sites actually use it');

test('both fetches send the PLANNED messages, not the raw history', () => {
  // Anchored on the request body, not the bare phrase -- the explanatory
  // comment above sendMsg legitimately contains the words "messages:history".
  assert.ok(!/JSON\.stringify\(\{[^}]*messages:history/.test(html),
    'a fetch still posts the unbounded history array');
  assert.match(html, /messages:_plan\.messages/);
  assert.match(html, /messages:_plan2\.messages/);
});

test('dropping is surfaced to the user, not done silently', () => {
  assert.match(html, /were left out of this request to stay inside/);
});

test('an oversized tool result is truncated AND the model is told so', () => {
  assert.match(html, /\[TRUNCATED: this tool returned more data than fits/);
  assert.match(html, /Do not total, count, average or summarise across the full set/);
});

test('the truncation cap is derived from the budget, not a second magic number', () => {
  assert.match(html, /var _trMax=Math\.floor\(SD_PROMPT_BUDGET_TOKENS\/2\)\*SD_TOK_CHARS;/);
});

test('an ERROR tool result is not truncated -- it is short and must arrive whole', () => {
  assert.match(html, /if\(outcome\.ok&&toolResultContent\.length>_trMax\)\{/);
});

console.log('\n' + (fail === 0
  ? 'ALL ' + pass + ' PROMPT-BUDGET ASSERTIONS PASS'
  : pass + ' passed, ' + fail + ' FAILED'));
process.exit(fail === 0 ? 0 : 1);
