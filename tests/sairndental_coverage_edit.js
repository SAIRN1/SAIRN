// tests/sairndental_coverage_edit.js
//
// Run:  node tests/sairndental_coverage_edit.js
//
// A coverage rule could only ever be CREATED. addCoverageRule() minted a fresh
// newId('CV') every time and removeCoverageRule() is local-only, so changing
// Delta/D2740 from 50% to 80% had no path at all.
//
// IT LOOKED LIKE IT WORKED, which is why nobody noticed: adding a second rule
// for the same payer and procedure saved fine, and lookupCoverage() -- a
// .find() -- silently kept using the first. The practice believed it had
// changed a rule it had not. The duplicate refusal added earlier the same day
// made the attempt visible; this makes it possible.
//
// The functions are DRIVEN, not reimplemented, and the assertions are about
// what reaches the server and what the local list ends up holding -- per
// sairn-code-scrubber item 16 Shape B, asserting that an edit path EXISTS is
// satisfied by one that appends a duplicate, which is the bug.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const html = fs.readFileSync(path.join(__dirname, '..', 'sairndental.html'), 'utf8').replace(/\r\n/g, '\n');

let pass = 0, fail = 0;
const queue = [];
function test(name, fn) { queue.push({ name, fn }); }
function section(t) { queue.push({ section: t }); }

function fnBody(name) {
  const at = html.indexOf(name);
  assert.ok(at > 0, 'not found in sairndental.html: ' + name);
  const open = html.indexOf('{', at);
  let depth = 0;
  for (let i = open; i < html.length; i++) {
    if (html[i] === '{') depth++;
    else if (html[i] === '}') { depth--; if (depth === 0) return html.slice(at, i + 1); }
  }
  throw new Error('unbalanced braces after ' + name);
}

const RULE = { id: 'CV-1', payer: 'Delta Dental', procedure_type_id: 'PR-1', coverage_percent: 50, created_at: '2026-01-05' };

function harness(opts) {
  opts = opts || {};
  const fields = { 'cv-add-payer': '', 'cv-add-procedure': '', 'cv-add-percent': '' };
  const els = {};
  Object.keys(fields).forEach((id) => { els[id] = { value: '' }; });
  els['cv-save-btn'] = { textContent: 'Add Coverage Rule' };
  els['cv-cancel-btn'] = { style: { display: 'none' } };
  const calls = { sent: [], stored: [], toasts: [], renders: 0 };
  let list = JSON.parse(JSON.stringify(opts.rules === undefined ? [RULE] : opts.rules));
  const ctx = {
    JSON, Object, Array, String, Number, parseFloat, isNaN, Promise,
    $: (id) => els[id],
    coverageRules: () => JSON.parse(JSON.stringify(list)),
    st: (k, v) => { calls.stored.push({ key: k, value: v }); if (k === 'dnt_coverage_list') list = v; return true; },
    rCoverage: () => { calls.renders++; },
    toast: (m) => { calls.toasts.push(String(m)); },
    newId: (p) => p + '-NEW',
    dntLocalToday: () => '2026-09-04',
    dntLastErrText: () => (opts.errText || ''),
    sdnData: (action, resource, payload) => {
      calls.sent.push({ action, resource, payload });
      return Promise.resolve(opts.writeFails ? null : payload);
    },
    __els: els, __calls: calls, __list: () => list,
  };
  vm.createContext(ctx);
  vm.runInContext(fnBody('var cvEditId=null;').replace(/^var cvEditId=null;\{[\s\S]*$/, 'var cvEditId=null;') + '\n'
    + 'var cvEditId=null;\n'
    + fnBody('function editCoverageRule(') + '\n'
    + fnBody('function cancelCoverageEdit(') + '\n'
    + fnBody('async function saveCoverageRule()') + '\n'
    + fnBody('function removeCoverageRule('), ctx);
  return ctx;
}

// ═══════════════════════════════════════════════════════════════════════════
section('editing loads the rule and marks the form');

test('editCoverageRule fills all three fields from the real row', () => {
  const c = harness();
  c.editCoverageRule('CV-1');
  assert.strictEqual(c.__els['cv-add-payer'].value, 'Delta Dental');
  assert.strictEqual(c.__els['cv-add-procedure'].value, 'PR-1');
  assert.strictEqual(c.__els['cv-add-percent'].value, 50);
  assert.strictEqual(c.__els['cv-save-btn'].textContent, 'Save Changes');
  assert.strictEqual(c.__els['cv-cancel-btn'].style.display, '');
});

test('editing a rule that is no longer on file refuses instead of half-loading', () => {
  const c = harness();
  c.editCoverageRule('CV-GONE');
  assert.match(c.__calls.toasts[0], /no longer on file/);
  assert.strictEqual(c.__els['cv-save-btn'].textContent, 'Add Coverage Rule', 'the form went into edit mode for a rule that does not exist');
});

test('cancel clears the form and the mode', () => {
  const c = harness();
  c.editCoverageRule('CV-1');
  c.cancelCoverageEdit();
  assert.strictEqual(c.__els['cv-add-payer'].value, '');
  assert.strictEqual(c.__els['cv-save-btn'].textContent, 'Add Coverage Rule');
  assert.strictEqual(c.__els['cv-cancel-btn'].style.display, 'none');
});

// ═══════════════════════════════════════════════════════════════════════════
section('saving an edit UPDATES -- it does not add a second rule');

test('the SAME id is sent, which is what makes the server upsert an update', async () => {
  const c = harness();
  c.editCoverageRule('CV-1');
  c.__els['cv-add-percent'].value = '80';
  await c.saveCoverageRule();
  assert.strictEqual(c.__calls.sent.length, 1);
  assert.strictEqual(c.__calls.sent[0].resource, 'dnt_coverage_rules');
  assert.strictEqual(c.__calls.sent[0].payload.id, 'CV-1',
    'a fresh id was minted -- the server would insert a SECOND rule and lookupCoverage() would keep using the first');
  assert.strictEqual(c.__calls.sent[0].payload.coverage_percent, 80);
});

test('created_at is preserved, not stamped with today', async () => {
  const c = harness();
  c.editCoverageRule('CV-1');
  c.__els['cv-add-percent'].value = '80';
  await c.saveCoverageRule();
  assert.strictEqual(c.__calls.sent[0].payload.created_at, '2026-01-05');
});

test('the local list is REPLACED in place, not appended to', async () => {
  const c = harness();
  c.editCoverageRule('CV-1');
  c.__els['cv-add-percent'].value = '80';
  await c.saveCoverageRule();
  const rows = c.__list();
  assert.strictEqual(rows.length, 1, 'the edit appended a duplicate locally -- lookupCoverage() would pick by row order');
  assert.strictEqual(rows[0].coverage_percent, 80);
});

test('the form leaves edit mode and says "updated", not "added"', async () => {
  const c = harness();
  c.editCoverageRule('CV-1');
  c.__els['cv-add-percent'].value = '80';
  await c.saveCoverageRule();
  assert.ok(c.__calls.toasts.some((t) => /updated/i.test(t)));
  assert.ok(!c.__calls.toasts.some((t) => /^Coverage rule added$/.test(t)));
  assert.strictEqual(c.__els['cv-save-btn'].textContent, 'Add Coverage Rule');
});

test('a NEW rule still mints an id and appends', async () => {
  const c = harness();
  c.__els['cv-add-payer'].value = 'Cigna';
  c.__els['cv-add-procedure'].value = 'PR-2';
  c.__els['cv-add-percent'].value = '60';
  await c.saveCoverageRule();
  assert.strictEqual(c.__calls.sent[0].payload.id, 'CV-NEW');
  assert.strictEqual(c.__calls.sent[0].payload.created_at, '2026-09-04');
  assert.strictEqual(c.__list().length, 2);
});

test('a REFUSED save changes nothing locally and stays in edit mode so it can be retried', async () => {
  const c = harness({ writeFails: true, errText: 'A coverage rule already covers this payer and procedure, at 50%.' });
  c.editCoverageRule('CV-1');
  c.__els['cv-add-percent'].value = '80';
  await c.saveCoverageRule();
  assert.strictEqual(c.__list()[0].coverage_percent, 50, 'a refused edit was applied locally anyway');
  assert.strictEqual(c.__calls.stored.length, 0, 'a refused edit still wrote to localStorage');
  assert.strictEqual(c.__els['cv-save-btn'].textContent, 'Save Changes', 'the edit was abandoned, so the user has to start again');
  assert.ok(c.__calls.toasts.some((t) => /already covers this payer/.test(t)),
    "the server's own reason is not shown");
});

test('editing a row that vanished between Edit and Save refuses and resets', async () => {
  const c = harness();
  c.editCoverageRule('CV-1');
  c.st('dnt_coverage_list', []);   // another device removed it, sync replaced the list
  c.__els['cv-add-percent'].value = '80';
  await c.saveCoverageRule();
  assert.strictEqual(c.__calls.sent.length, 0, 'a rule that no longer exists was written back to the server');
  assert.ok(c.__calls.toasts.some((t) => /no longer on file/.test(t)));
  assert.strictEqual(c.__els['cv-save-btn'].textContent, 'Add Coverage Rule');
});

test('the browser 0-100 check still runs before anything is sent', async () => {
  const c = harness();
  c.editCoverageRule('CV-1');
  c.__els['cv-add-percent'].value = '150';
  await c.saveCoverageRule();
  assert.strictEqual(c.__calls.sent.length, 0);
  assert.ok(c.__calls.toasts.some((t) => /0-100/.test(t)));
});

// ═══════════════════════════════════════════════════════════════════════════
section('remove tells the truth about what it does');

test('the message says the row comes back, and names the 0% substitute', () => {
  // It said "Coverage rule removed on this device" -- true, and misleading:
  // dntSyncFromServer() reads the server's rules back and the row REAPPEARS.
  const c = harness();
  c.removeCoverageRule('CV-1');
  const m = c.__calls.toasts[0];
  assert.match(m, /come back on the next sync/i, 'the message still implies the removal sticks');
  assert.match(m, /set the percent to 0/i, 'no substitute is offered for a rule that must stop applying');
});

test('removing the row being edited exits edit mode', () => {
  const c = harness();
  c.editCoverageRule('CV-1');
  c.removeCoverageRule('CV-1');
  assert.strictEqual(c.__els['cv-save-btn'].textContent, 'Add Coverage Rule',
    'the form is still editing a rule that is no longer in the list');
});

// ═══════════════════════════════════════════════════════════════════════════
section('the panel wiring matches the functions');

test('both buttons point at handlers that exist, and only the id is interpolated', () => {
  // The payer is free text a practice types. H() makes a string safe as HTML,
  // not as a JS string literal inside an attribute -- sairn-code-scrubber
  // item 8 -- so nothing but the generated id may go into an onclick.
  const render = fnBody('function rCoverage()');
  assert.match(render, /onclick="editCoverageRule\(\\'"\+c\.id\+"\\'\)"|editCoverageRule\(\\'/, 'no Edit control is rendered');
  assert.strictEqual(render.indexOf('+H(c.payer)+'), render.lastIndexOf('+H(c.payer)+'),
    'the payer appears more than once in the row markup -- check it is not inside an onclick');
  const onclickArgs = render.match(/onclick="\w+\(\\'\+([^+]+)\+/g) || [];
  onclickArgs.forEach((a) => assert.match(a, /c\.id/, 'something other than the id is interpolated into an onclick: ' + a));
  assert.ok(html.indexOf('onclick="saveCoverageRule()"') > 0, 'the Save button still calls the old name');
  assert.ok(html.indexOf('onclick="cancelCoverageEdit()"') > 0, 'no Cancel control is wired');
});

// ═══════════════════════════════════════════════════════════════════════════
(async () => {
  for (const item of queue) {
    if (item.section) { console.log('--- ' + item.section + ' ---'); continue; }
    try { await item.fn(); console.log('  ok   ' + item.name); pass++; }
    catch (e) { console.log('  FAIL ' + item.name + '\n       ' + e.message); fail++; }
  }
  console.log('\nsairndental_coverage_edit: ' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
