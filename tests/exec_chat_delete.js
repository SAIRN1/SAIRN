// tests/exec_chat_delete.js
//
// Run:  node tests/exec_chat_delete.js
//
// The executive private channel could be written to and never edited or cleared.
// A message sent to the wrong channel, or a figure typed wrong, stayed in front
// of the CEO, CFO and CTO for good.
//
// ── YOUR OWN MESSAGES ONLY, AND THAT IS THE WHOLE DESIGN ──────────────────
// This is a SHARED channel between three roles. A blanket Delete would let the
// CFO remove what the CEO said, which is a different feature from being able to
// take back your own line. The markup offers Delete only on `isMine` rows --
// the same test the bubble styling already uses -- and execDelete() RE-CHECKS
// the role rather than trusting the markup, because a button that is merely not
// drawn is not an access rule.
//
// ── AND THE CAP THAT WAS ABOUT TO DELETE THE CHANNEL'S HISTORY ────────────
// execSend() trimmed with `sdExecMsgs = sdExecMsgs.slice(-500)`. That is a
// localStorage bound on one browser, and sdSyncCollection()'s removal sweep
// would have read every trimmed message as a deletion and removed it from the
// server -- which has no such bound and was keeping the fuller channel. It is
// routed through sdCapLocalTail() now. The cap GUARD only recognised the
// `slice(0,N)` form and walked straight past this one; that hole is closed in
// tests/collection_delete_reaches_the_server.js.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const ROOT = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(ROOT, 'stonedesk.html'), 'utf8');

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('--- ' + t + ' ---'); }

function balanced(start) {
  let i = html.indexOf('{', start), depth = 0;
  for (; i < html.length; i++) {
    if (html[i] === '{') depth++;
    else if (html[i] === '}') { depth--; if (!depth) return html.slice(start, i + 1); }
  }
  throw new Error('unbalanced from ' + start);
}
function fn(decl) {
  const i = html.indexOf(decl);
  assert.ok(i > 0, 'not found in stonedesk.html: ' + decl);
  return balanced(i);
}

const MSGS = [
  { id: 'EM1', role: 'ceo', text: 'Board pack is ready', ts: '2026-09-10T09:00:00.000Z' },
  { id: 'EM2', role: 'cfo', text: 'Margin is 38%', ts: '2026-09-10T09:05:00.000Z' },
  { id: 'EM3', role: 'ceo', text: 'Typo: 48%', ts: '2026-09-10T09:06:00.000Z' }
];

function build(role, msgs, opts) {
  opts = opts || {};
  const out = { toasts: [], confirms: [], saves: 0, els: {} };
  ['exec-msgs', 'exec-online-count'].forEach(id => {
    out.els[id] = { innerHTML: '', textContent: '', scrollTop: 0, scrollHeight: 0 };
  });
  const ctx = {};
  const src =
    'var sdExecMsgs=' + JSON.stringify(msgs) + ';\n' +
    'var sdExecRole=' + JSON.stringify(role) + ';\n' +
    'function saveSD5(){ out.saves++; return !opts.saveFails; }\n' +
    fn('function renderExecChat(){') + '\n' +
    fn('function execDelete(id){') + '\n' +
    'ctx.render=renderExecChat; ctx.del=execDelete;'
    + 'ctx.msgs=function(){return sdExecMsgs;};';
  new Function('document', 'escHtml', 'escAttrJs', 'showToast', 'confirm', 'out', 'opts', 'ctx', src)(
    { getElementById: id => out.els[id] || null },
    s => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'),
    s => String(s),
    m => out.toasts.push(String(m)),
    m => { out.confirms.push(String(m)); return opts.confirm !== false; },
    out, opts, ctx
  );
  return { ctx, out };
}

(function main() {
  console.log('StoneDesk exec channel -- take back your own line, and nobody else\'s\n');

  section('the button appears only on your own messages');

  test('as CEO, Delete is offered on the two CEO messages and not the CFO one', () => {
    const b = build('ceo', MSGS);
    b.ctx.render();
    const h = b.out.els['exec-msgs'].innerHTML;
    assert.strictEqual((h.match(/execDelete\(/g) || []).length, 2);
    assert.ok(/execDelete\('EM1'\)/.test(h) && /execDelete\('EM3'\)/.test(h));
    assert.ok(!/execDelete\('EM2'\)/.test(h), 'the CEO was offered a delete on the CFO\'s message');
  });

  test('as CFO, the mirror image', () => {
    const b = build('cfo', MSGS);
    b.ctx.render();
    const h = b.out.els['exec-msgs'].innerHTML;
    assert.strictEqual((h.match(/execDelete\(/g) || []).length, 1);
    assert.ok(/execDelete\('EM2'\)/.test(h));
  });

  test('a role with nothing in the channel is offered nothing', () => {
    const b = build('cto', MSGS);
    b.ctx.render();
    assert.strictEqual((b.out.els['exec-msgs'].innerHTML.match(/execDelete\(/g) || []).length, 0);
  });

  test('message text is escaped, not rendered', () => {
    const b = build('ceo', [{ id: 'EM9', role: 'ceo', text: '<img src=x onerror=1>', ts: MSGS[0].ts }]);
    b.ctx.render();
    const h = b.out.els['exec-msgs'].innerHTML;
    assert.ok(h.indexOf('<img src=x') === -1 && h.indexOf('&lt;img') !== -1);
  });

  test('an empty channel still shows its explanation', () => {
    const b = build('ceo', []);
    b.ctx.render();
    assert.ok(/Private executive channel/.test(b.out.els['exec-msgs'].innerHTML));
  });

  // ══ THE ARM THIS FILE EXISTS FOR ════════════════════════════════════════
  section('the handler re-checks the role -- a button not drawn is not a rule');

  test('deleting someone ELSE\'s message is refused even when called directly', () => {
    const b = build('cfo', MSGS);
    b.ctx.del('EM1');                       // a CEO message, called as the CFO
    assert.strictEqual(b.ctx.msgs().length, 3, 'the CFO deleted the CEO\'s message');
    assert.ok(/only delete your own/i.test(b.out.toasts[0] || ''), JSON.stringify(b.out.toasts));
    assert.strictEqual(b.out.confirms.length, 0, 'it asked before checking whose message it was');
  });

  test('and your own goes', () => {
    const b = build('ceo', MSGS);
    b.ctx.del('EM1');
    assert.deepStrictEqual(b.ctx.msgs().map(x => x.id), ['EM2', 'EM3']);
  });

  section('the ordinary refusals');

  test('the confirm says kept, never "cannot be undone"', () => {
    const b = build('ceo', MSGS, { confirm: false });
    b.ctx.del('EM1');
    const m = b.out.confirms[0] || '';
    assert.ok(/hidden and kept, not destroyed/.test(m), m);
    assert.ok(!/cannot be undone/i.test(m));
  });

  test('declining changes nothing', () => {
    const b = build('ceo', MSGS, { confirm: false });
    b.ctx.del('EM1');
    assert.strictEqual(b.ctx.msgs().length, 3);
    assert.strictEqual(b.out.saves, 0);
  });

  test('an id matching nothing never asks and never saves', () => {
    const b = build('ceo', MSGS);
    b.ctx.del('EM-NO-SUCH');
    assert.strictEqual(b.out.confirms.length, 0);
    assert.strictEqual(b.out.saves, 0);
  });

  test('an empty id is refused outright', () => {
    const b = build('ceo', MSGS);
    b.ctx.del('');
    assert.strictEqual(b.out.confirms.length, 0);
    assert.strictEqual(b.out.saves, 0);
  });

  // A FAILED SAVE MUST NOT LOOK LIKE A DELETION. saveSD5() returns false when
  // localStorage refuses; reporting success would take the message off screen
  // while it survives on disk.
  test('a storage failure is reported, with no success toast', () => {
    const b = build('ceo', MSGS, { saveFails: true });
    b.ctx.del('EM1');
    assert.ok(/Could not delete that message/.test(b.out.toasts.join('|')), JSON.stringify(b.out.toasts));
    assert.ok(!/Message deleted/.test(b.out.toasts.join('|')));
  });

  section('the 500-message cap is a local bound, not a deletion');

  test('execSend trims through sdCapLocalTail, not a bare slice', () => {
    const send = fn('function execSend(){');
    assert.ok(/sdCapLocalTail\('sd_exec_msgs',sdExecMsgs,500\)/.test(send),
      'the cap would tell the server every trimmed message had been deleted');
    assert.ok(!/sdExecMsgs\.slice\(-500\)/.test(send), 'the bare trim is still there');
  });

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  if (fail) process.exit(1);
})();
