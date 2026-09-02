// tests/refusal_not_empty.js
//
// Run:  node tests/refusal_not_empty.js
//
// The gate on slabs/profile/memory could not ship alone. sdData() answered
// every failure with `null` and said nothing, so a now-legitimate 403 would
// have rendered as "No slabs in inventory yet" -- a confident wrong answer
// about a yard that may be full. That is the fabricated-emptiness class this
// codebase keeps finding, and it is the reason the client change and the
// server gate are one commit.
//
// "You may not have this" and "there is none of this" are different facts and
// must not render the same. That is what these assert.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const html = fs.readFileSync(path.join(__dirname, '..', 'stonedesk.html'), 'utf8');

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
async function atest(name, fn) {
  try { await fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('--- ' + t + ' ---'); }

function grab(startMarker, endRe) {
  const s = html.indexOf(startMarker);
  assert.ok(s > 0, 'not found in stonedesk.html: ' + startMarker);
  const rel = html.slice(s).search(endRe);
  assert.ok(rel > 0, 'unterminated: ' + startMarker);
  return html.slice(s, s + rel);
}

// Comment lines are stripped before locating code. The explanatory comments
// next to these guards quote the very strings the guards exist to suppress,
// so an unstripped search finds the documentation before the implementation
// -- a test defeated by its own subject's comments.
function stripComments(s) {
  return s
    .split(String.fromCharCode(10))
    .filter(function (l) { return l.trim().indexOf('//') !== 0; })
    .join(String.fromCharCode(10));
}

// sdAuthWasRefused is a one-liner, so it is taken to its own closing brace on
// the same line rather than to a blank line.
const oneLiner = (() => {
  const i = html.indexOf('function sdAuthWasRefused(resource)');
  assert.ok(i > 0, 'sdAuthWasRefused not found');
  const end = html.indexOf('\n', i);
  return html.slice(i, end);
})();

const src =
  'var _sdAuthRefused = {};\n' +
  oneLiner + '\n' +
  grab('function sdAuthRefusedNote(what)', /\r?\n\}/) + '\n}\n' +
  grab('async function sdData(action, resource, payload) {', /\r?\n\}/) + '\n}\n';

function harness(opts) {
  opts = opts || {};
  const ctx = {
    console,
    sdLicenseKey: () => 'SD-TEST',
    sessionStorage: { getItem: () => (opts.token || null) },
    escHtml: (s) => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;'),
    fetch: async function () {
      if (opts.throws) throw new Error('offline');
      const st = opts.status || 200;
      return { ok: st < 300, status: st, json: async () => (opts.body || { ok: true, data: [1, 2] }) };
    }
  };
  vm.createContext(ctx);
  vm.runInContext(src, ctx);
  return ctx;
}

(async function () {
  section('sdData tells the difference between refused and empty');

  await atest('a 403 marks the resource refused, and still returns null', async () => {
    const c = harness({ status: 403 });
    assert.strictEqual(await c.sdData('read', 'slabs', {}), null, 'the return contract changed');
    assert.strictEqual(c.sdAuthWasRefused('slabs'), true);
  });

  await atest('a 401 counts as refused too', async () => {
    const c = harness({ status: 401 });
    await c.sdData('read', 'memory', {});
    assert.strictEqual(c.sdAuthWasRefused('memory'), true);
  });

  await atest('a 500 is NOT a refusal -- it is a broken server, a different message', async () => {
    const c = harness({ status: 500 });
    await c.sdData('read', 'slabs', {});
    assert.strictEqual(c.sdAuthWasRefused('slabs'), false,
      'an outage would tell the user to sign in, which they already have');
  });

  await atest('a successful read CLEARS a previous refusal', async () => {
    // Otherwise signing in leaves the panel stuck saying "sign in".
    const c = harness({ status: 403 });
    await c.sdData('read', 'slabs', {});
    assert.strictEqual(c.sdAuthWasRefused('slabs'), true);
    c.fetch = async () => ({ ok: true, status: 200, json: async () => ({ ok: true, data: [1] }) });
    await c.sdData('read', 'slabs', {});
    assert.strictEqual(c.sdAuthWasRefused('slabs'), false, 'the sign-in message would never clear');
  });

  await atest('refusal is tracked PER RESOURCE, not globally', async () => {
    // profile/read is still open on purpose; a refusal on slabs must not make
    // the profile surfaces claim they need a login.
    const c = harness({ status: 403 });
    await c.sdData('read', 'slabs', {});
    assert.strictEqual(c.sdAuthWasRefused('profile'), false);
  });

  await atest('a thrown fetch does not mark a refusal', async () => {
    const c = harness({ throws: true });
    assert.strictEqual(await c.sdData('read', 'slabs', {}), null);
    assert.strictEqual(c.sdAuthWasRefused('slabs'), false);
  });

  test('the note says it is not empty, in as many words', () => {
    const c = harness({});
    const n = c.sdAuthRefusedNote('slab inventory');
    assert.match(n, /Sign in to see slab inventory/);
    assert.match(n, /This is not empty/);
  });

  test('the note escapes what it is given', () => {
    const c = harness({});
    assert.ok(!c.sdAuthRefusedNote('<img src=x>').includes('<img src=x'));
  });

  section('the surfaces ask before they claim');

  test('the Slabs panel checks for a refusal BEFORE the empty state', () => {
    // Anchored inside sdSlabsRender -- `if(!data.length){` occurs elsewhere in
    // the file and the first hit is not this panel.
    const fn = html.indexOf('window.sdSlabsRender=function(){');
    assert.ok(fn > 0, 'sdSlabsRender not found');
    const i = html.indexOf('if(!data.length){', fn);
    assert.ok(i > fn, 'the empty-state branch is gone');
    // COMMENT LINES STRIPPED FIRST. The explanatory comment above the check
    // quotes "No slabs in inventory yet" to say why it must not be shown, and
    // an unstripped search finds the comment before the code -- a test defeated
    // by its own subject's documentation.
    const block = stripComments(html.slice(i, i + 1400));
    const refusal = block.indexOf("sdAuthWasRefused('slabs')");
    const claim = block.indexOf('No slabs in inventory yet');
    assert.ok(refusal > 0, 'the Slabs panel never checks');
    assert.ok(claim > 0, 'the empty state is gone');
    assert.ok(refusal < claim, 'it claims an empty yard before asking whether it was allowed to look');
  });

  test('the quote/POS slab picker does the same', () => {
    const i = html.indexOf('function qbOpenSlabPicker');
    const block = html.slice(i, i + 1600);
    assert.match(block, /sdAuthWasRefused\('slabs'\)/);
    assert.match(block, /No in-stock slabs yet/);
  });

  section('the loads moved, which is what makes the gate survivable');

  test('profile, memory and slabs no longer load on DOMContentLoaded', () => {
    // Same anchoring problem: locate the BOOT listener via the lineage call it
    // still contains, not via the first listener in the file.
    const anchor = html.indexOf("if(typeof sdLoadLineage==='function')");
    const i = html.lastIndexOf("document.addEventListener('DOMContentLoaded'", anchor);
    assert.ok(i > 0, 'the boot listener was not found');
    const block = html.slice(i, anchor + 400);
    const code = block.split(/\r?\n/).filter(l => !/^\s*\/\//.test(l)).join('\n');
    assert.ok(!/loadSDProfile\(\)/.test(code), 'profile still loads pre-login');
    assert.ok(!/loadSDMemories\(\)/.test(code), 'memory still loads pre-login');
    assert.ok(!/loadSlabs\(\)/.test(code), 'slabs still load pre-login');
  });

  test('...and are in the post-login init list instead', () => {
    assert.match(html, /'sdApprovalsLoad',\s*\r?\n\s*'loadSDProfile','loadSDMemories','loadSlabs'/);
  });

  test('lineage deliberately stays pre-login, because it is not gated', () => {
    // Anchored on the lineage call itself -- there are ten DOMContentLoaded
    // listeners in this file and indexOf finds the first, not this one.
    const i = html.indexOf("if(typeof sdLoadLineage==='function')");
    assert.ok(i > 0, 'the lineage load is gone entirely');
    const before = html.lastIndexOf("document.addEventListener('DOMContentLoaded'", i);
    assert.ok(before > 0 && i - before < 4000,
      'the lineage load is no longer inside the boot listener');
  });

  test('_slabLoaded is set by the load itself, not by a caller that moved', () => {
    const i = html.indexOf('function loadSlabs(){');
    assert.match(html.slice(i, i + 600), /_slabLoaded = true;/);
  });

  console.log('\n' + (fail === 0
    ? 'ALL ' + pass + ' REFUSAL-NOT-EMPTY ASSERTIONS PASS'
    : pass + ' passed, ' + fail + ' FAILED'));
  process.exit(fail === 0 ? 0 : 1);
})();
