// tests/stonedesk_followup_chip.js
//
// Run:  node tests/stonedesk_followup_chip.js
//
// A user asks the AI something, gets an answer over 150 characters, and three
// "Ask a follow-up" chips appear under it. Clicking one did NOTHING -- silently
// -- because the handler drove the retired legacy chat:
//
//     addMessage('user', q)              -> appends to #messages, which does
//                                           not exist anywhere in the file
//     chatHistory.push(...)              -> only ever declared inside setMode()
//     sendToClaudeAndRender()            -> posts from #userInput, also gone
//
// The file's own DEAD CODE FLAG above panel-ai has recorded that container as
// missing since the chat was replaced, and several other callers were
// retargeted to sdAIQuick() at the time. This one was missed, and unlike the
// rest of that cluster IT IS REACHABLE: installHook() wraps the LIVE addMsg(),
// so generateFollowUps() renders the chips into #chatArea after every real
// answer. The chips stayed on screen after the failed click, inviting another.
//
// THE POINT OF THIS SUITE IS THE PAIRING, not the absence of a string: the
// handler must call the live sender AND must not fall back to silence.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const FILE = path.join(__dirname, '..', 'stonedesk.html');
const html = fs.readFileSync(FILE, 'utf8');

let pass = 0, fail = 0;
const queue = [];
function test(n, f) { queue.push({ n, f }); }
function section(t) { queue.push({ section: t }); }

// The real handler, lifted from the file and driven -- not a reimplementation.
function handlerSource() {
  const at = html.indexOf('      chip.onclick = function() {');
  assert.ok(at > 0, 'the follow-up chip handler is gone from stonedesk.html');
  let depth = 0, i = html.indexOf('{', at);
  for (let j = i; j < html.length; j++) {
    if (html[j] === '{') depth++;
    else if (html[j] === '}') { depth--; if (depth === 0) return html.slice(at, j + 1); }
  }
  throw new Error('unterminated handler');
}

function drive(opts) {
  opts = opts || {};
  const calls = { quick: [], notify: [], errors: [], removed: 0 };
  const ctx = {
    q: 'How should I price a bookmatched island?',
    document: {
      querySelectorAll: () => ({ forEach: (fn) => { calls.removed++; fn({ remove() {} }); } }),
      getElementById: () => null,
    },
    console: { error: (...a) => calls.errors.push(a.join(' ')) },
  };
  if (!opts.noQuick) ctx.sdAIQuick = (q) => calls.quick.push(q);
  if (!opts.noNotify) ctx.notify = (m, k) => calls.notify.push({ m, k });
  vm.createContext(ctx);
  vm.runInContext('var chip={};' + handlerSource() + '\nchip.onclick();', ctx);
  return calls;
}

section('the click reaches the live chat');

test('clicking a chip sends the question through sdAIQuick', () => {
  const c = drive();
  assert.deepStrictEqual(c.quick, ['How should I price a bookmatched island?']);
});

test('...and clears the chips, so the answered question does not linger', () => {
  assert.ok(drive().removed >= 1, 'the follow-up row was never removed');
});

section('it can no longer fail silently');

test('a missing live sender TELLS the user, rather than doing nothing', () => {
  const c = drive({ noQuick: true });
  assert.strictEqual(c.quick.length, 0);
  assert.strictEqual(c.notify.length, 1, 'the user was told nothing');
  assert.match(c.notify[0].m, /follow-up/i);
});

test('...and with no notify either, it still says so somewhere', () => {
  const c = drive({ noQuick: true, noNotify: true });
  assert.strictEqual(c.errors.length, 1, 'nothing was logged; the click vanished');
  assert.match(c.errors[0], /not sent/);
});

section('the retired chat is really gone from this path');

test('the handler names none of the three dead symbols', () => {
  // A negative control on the exact defect. Each of these is a TypeError the
  // moment the handler runs, because none of their targets exist.
  const src = handlerSource().split('\n').filter((l) => l.trim().indexOf('//') !== 0).join('\n');
  ['addMessage(', 'chatHistory', 'sendToClaudeAndRender('].forEach((dead) => {
    assert.strictEqual(src.indexOf(dead), -1, 'the handler still calls ' + dead);
  });
});

test('...and the assertion above is not vacuous -- it matches the old handler', () => {
  const old = "chip.onclick = function() {\n  addMessage('user', q);\n  chatHistory.push({});\n  sendToClaudeAndRender();\n}";
  const hits = ['addMessage(', 'chatHistory', 'sendToClaudeAndRender('].filter((d) => old.indexOf(d) !== -1);
  assert.strictEqual(hits.length, 3, 'the negative control no longer describes the defect');
});

section('the container it used to write to really is absent');

test('#messages exists nowhere, which is what made the old handler throw', () => {
  assert.strictEqual((html.match(/id="messages"/g) || []).length, 0,
    'a #messages container was added back -- re-read whether the legacy chat is live again');
});

test('the live targets DO exist, so the retarget points somewhere real', () => {
  assert.ok(html.indexOf('id="ai-input"') > 0, '#ai-input is missing');
  assert.ok(html.indexOf('id="ai-chat"') > 0, '#ai-chat is missing');
  assert.ok(html.indexOf('id="chatArea"') > 0, '#chatArea is missing -- the chips would never render');
  assert.ok(html.indexOf('window.sdAIQuick=function(q){') > 0, 'sdAIQuick is gone');
});

(async () => {
  for (const item of queue) {
    if (item.section) { console.log('--- ' + item.section + ' ---'); continue; }
    try { await item.f(); console.log('  ok   ' + item.n); pass++; }
    catch (e) { console.log('  FAIL ' + item.n + '\n       ' + e.message); fail++; }
  }
  console.log('\nstonedesk_followup_chip: ' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
