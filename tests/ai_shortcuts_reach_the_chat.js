// tests/ai_shortcuts_reach_the_chat.js
//
// Run:  node tests/ai_shortcuts_reach_the_chat.js
//
// StoneDesk's legacy chat was removed and its input box, #userInput, went with
// it. What survived is the CSS rule `textarea#userInput{...}` -- so a grep for
// "userInput" still finds something, and the ELEMENT still does not exist.
//
// Callers were migrated to sdAIQuick() -- the widget that really fills #ai-input
// and sends via #ai-chat -- but the migration was never finished. Four sites
// were done (custFollowUpAI, vendorSpendAI, getAIQuoteAdvice, warrAskClaude) and
// three live ones were missed:
//
//   safetyAIRootCause()          "5-Why Root Cause" on a logged incident
//   ecpGenerate()                "Generate Written Exposure Control Plan"
//   safetyGenerateAttestation()  "Generate STOP Act Attestation"
//
// Every one is a wired button. Every one did:
//
//     sbNav('ai');
//     setTimeout(function(){
//       var input=document.getElementById('userInput');
//       if(input){ input.value = '<prompt>'; sendMessage(); }
//     },400);
//
// The `if(input)` guard is why nobody noticed. The button navigated to the AI
// panel and then did NOTHING -- no request, no error, no message. The user
// watches the panel open and sees an empty chat, which reads as "the AI had
// nothing to say" rather than "this button is not connected".
//
// These are not cosmetic buttons. Two of them generate OSHA and Cal/OSHA
// compliance documents a shop is legally required to hold.
//
// sendMessage() itself was the other half: `input.value.trim()` unguarded, so
// any caller that DID reach it threw a TypeError into a console nobody has
// open. Silent both ways round, which is why the guard added here reports
// instead of doing either.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const ROOT = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(ROOT, 'stonedesk.html'), 'utf8');

let pass = 0, fail = 0;
async function test(name, fn) {
  try { await fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('--- ' + t + ' ---'); }

function grab(sig) {
  const s = html.indexOf(sig);
  assert.ok(s > 0, 'not found in stonedesk.html: ' + sig);
  const rest = html.slice(s);
  const m = rest.match(/\r?\n\}(?=\r?\n)/);
  assert.ok(m, 'not terminated: ' + sig);
  return rest.slice(0, m.index + m[0].length);
}

// Full-line comments are dropped before matching. The fix's own comments NAME
// the dead functions they retargeted away from -- "the dead
// #userInput/sendMessage() legacy chat" -- so a naive search finds them and
// reports the fix as the bug. Guardian's dead-button audit learned exactly this
// and now strips comments first; the same trap, in a different tool.
const codeOnly = src => src.split('\n')
  .filter(l => l.trim().indexOf('//') !== 0)
  .join('\n');

const RETARGETED = [
  { fn: 'safetyAIRootCause', sig: 'function safetyAIRootCause(' },
  { fn: 'ecpGenerate', sig: 'function ecpGenerate(' },
  { fn: 'safetyGenerateAttestation', sig: 'function safetyGenerateAttestation(' }
];

console.log('StoneDesk AI shortcuts -- a button that opens the panel and sends nothing\n');

async function main() {
  section('the premise: #userInput really is gone');

  await test('no element in the file carries id="userInput"', () => {
    assert.ok(html.indexOf('id="userInput"') === -1, 'the element is back -- re-check this suite');
  });

  await test('...and its CSS rule survives, which is why a grep looks reassuring', () => {
    // Recorded so the next person greping "userInput" knows why they get hits.
    assert.match(html, /textarea#userInput\s*\{/);
  });

  section('the three missed buttons now reach the real widget');

  RETARGETED.forEach(({ fn, sig }) => {
    const src = grab(sig);
    test(fn + '() calls sdAIQuick', () => {
      assert.match(src, /sdAIQuick\(/, fn + ' still does not use the live widget');
    });
    test(fn + '() no longer touches the dead input or the dead sender', () => {
      const code = codeOnly(src);
      assert.ok(code.indexOf("getElementById('userInput')") === -1,
        fn + ' still looks up #userInput');
      assert.ok(!/(?<![\w$.])sendMessage\s*\(/.test(code),
        fn + ' still calls sendMessage()');
    });
    test(fn + '() guards on sdAIQuick existing, like the four earlier migrations', () => {
      assert.match(src, /typeof sdAIQuick\s*===\s*'function'/);
    });
  });

  await test('the prompts survived the retarget intact', () => {
    // A retarget that quietly dropped half a compliance prompt would be worse
    // than the bug: the button would work and produce a thinner document.
    assert.match(grab('function ecpGenerate('), /29 CFR 1910\.1053/);
    assert.match(grab('function safetyGenerateAttestation('), /Labor Code Section 6717/);
    assert.match(grab('function safetyAIRootCause('), /5-Why analysis/);
  });

  section('no reachable code routes through sendMessage() any more');

  await test('every remaining sendMessage() caller is itself unreachable', () => {
    const lines = html.split('\n');
    const encl = ln => {
      for (let i = ln - 1; i >= Math.max(0, ln - 300); i--) {
        const m = lines[i].match(/^\s*(?:window\.)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(/) ||
                  lines[i].match(/^\s*(?:window\.)?([A-Za-z_$][\w$.]*)\s*=\s*(?:async\s+)?function\s*\(/);
        if (m) return m[1].split('.').pop();
      }
      return '(top)';
    };
    const callers = new Set();
    lines.forEach((l, i) => {
      if (/(?<![\w$.])sendMessage\s*\(/.test(l) && l.indexOf('function sendMessage') === -1 &&
          l.trim().indexOf('//') !== 0) callers.add(encl(i + 1));
    });
    callers.delete('sendMessage');   // its own retry button, inside its error HTML
    const reachable = [...callers].filter(fn => {
      const wired = lines.some(l => new RegExp('on\\w+\\s*=\\s*["\'][^"\']*\\b' + fn + '\\s*\\(').test(l));
      const refs = lines.reduce((n, l) =>
        n + (l.match(new RegExp('(?<![\\w$.])' + fn + '\\s*\\(', 'g')) || []).length, 0) - 1;
      return wired || refs > 0;
    });
    assert.deepStrictEqual(reachable, [],
      'these are reachable and still route through the dead chat: ' + reachable.join(', '));
  });

  section('sendMessage() itself fails visibly rather than either silently');

  function driveSendMessage(hasInput) {
    const logs = [], toasts = [];
    const el = { value: 'hello', style: {} };
    const ctx = {
      console: { error: (...a) => logs.push(a.join(' ')), log: () => {} },
      document: { getElementById: id => (hasInput && id === 'userInput') ? el : null },
      showToast: m => toasts.push(m),
      isTyping: false,
      chatHistory: [],
      addMessage: () => {},
      sendToClaudeAndRender: async () => { toasts.push('__SENT__'); },
      window: {}
    };
    vm.createContext(ctx);
    vm.runInContext(grab('async function sendMessage() {') + '\nthis.run=sendMessage;', ctx);
    return { ctx, logs, toasts, run: ctx.run };
  }

  await test('with no #userInput it returns cleanly instead of throwing a TypeError', async () => {
    const b = driveSendMessage(false);
    await b.run();   // must not throw
    assert.ok(b.logs.join(' ').indexOf('#userInput no longer exists') !== -1,
      'logs: ' + b.logs.join(' | '));
  });

  await test('...and tells the user, rather than leaving an empty panel to explain itself', async () => {
    const b = driveSendMessage(false);
    await b.run();
    assert.match(b.toasts.join(' | '), /not wired to the chat/);
    assert.ok(b.toasts.indexOf('__SENT__') === -1, 'it tried to send anyway');
  });

  await test('and it still works normally if the element is ever restored', async () => {
    const b = driveSendMessage(true);
    await b.run();
    assert.ok(b.toasts.indexOf('__SENT__') !== -1, 'a working chat stopped sending');
  });

  section('MUTATION: put the old shape back and the button goes quiet again');

  await test('MUTANT: the pre-fix shape sends nothing when #userInput is absent', async () => {
    // Rebuilds what safetyAIRootCause used to do, verbatim in shape, and proves
    // the failure was silent -- no throw, no send, nothing to see.
    const sent = [], navs = [];
    const ctx = {
      document: { getElementById: () => null },
      sbNav: id => navs.push(id),
      sendMessage: () => sent.push('sent'),
      console
    };
    vm.createContext(ctx);
    vm.runInContext(
      "function oldShape(){ sbNav('ai');" +
      "  var input=document.getElementById('userInput');" +
      "  if(input){ input.value='prompt'; sendMessage(); } }" +
      '\nthis.run=oldShape;', ctx);
    ctx.run();
    assert.deepStrictEqual(navs, ['ai'], 'the mutant did not even navigate');
    assert.deepStrictEqual(sent, [],
      'the mutant sent something -- it no longer reproduces the defect');
  });

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  if (fail) process.exitCode = 1;
}

main();
