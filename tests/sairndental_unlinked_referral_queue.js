// tests/sairndental_unlinked_referral_queue.js
//
// Run:  node tests/sairndental_unlinked_referral_queue.js
//
// A referral could be filed without linking a patient record -- "Link to
// Existing Patient (optional)" is deliberate -- and api/sd-data.js then scoped
// dnt_referrals by patient_id, where an EMPTY id matched nothing. So an
// unlinked referral was filtered out for EVERY provider role: the front desk
// saw it, the clinician who had to act on it did not, and nothing said so.
//
// It failed CLOSED, so nothing leaked. The cost ran the other way, and that is
// the whole point of this queue: a referral nobody can see is a patient who
// does not get seen.
//
// Michael's call was NOT to require the link. The server half makes unlinked
// rows visible (DNT_UNLINKED_VISIBLE_RESOURCES, asserted in
// api/sd-data-dental-provider-scope.test.js); this file covers the half that
// presents them as WORK rather than as ordinary rows.
//
// THE FUNCTIONS ARE DRIVEN, NOT REIMPLEMENTED -- the bodies are extracted from
// sairndental.html and run in a vm context, the same method
// tests/sairndental_coverage_edit.js uses. A test that rebuilt the render would
// pass against a render that no longer exists.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const html = fs.readFileSync(path.join(__dirname, '..', 'sairndental.html'), 'utf8')
  .replace(/\r\n/g, '\n');

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

const LINKED = {
  id: 'RF-1', direction: 'incoming', patient_name: 'Alice Smith', patient_id: 'PT-1',
  external_party: 'Dr Jones Oral Surgery', internal_provider_id: 'PV-1',
  date: '2026-09-11', reason: 'surgical extraction', status: 'Pending',
};
const UNLINKED = {
  id: 'RF-2', direction: 'outgoing', patient_name: 'Bobby Reyes', patient_id: '',
  external_party: 'Dr Patel Endodontics', internal_provider_id: '',
  date: '2026-09-10', reason: 'root canal', status: 'Pending',
};
const NO_KEY = {
  id: 'RF-3', direction: 'incoming', patient_name: 'Carol Diaz',
  external_party: 'Dr Wu Periodontics', date: '2026-09-09', reason: 'graft',
  status: 'Scheduled',
};
const PATIENTS = [
  { id: 'PT-1', name: 'Alice Smith' },
  { id: 'PT-2', name: 'Robert Reyes' },
];

function harness(opts) {
  opts = opts || {};
  const els = {
    'rf-unlinked-note': { style: { display: 'none' }, innerHTML: '' },
    'referrals-tbody': { innerHTML: '' },
  };
  const calls = { sent: [], stored: [], toasts: [] };
  let list = JSON.parse(JSON.stringify(
    opts.referrals === undefined ? [LINKED, UNLINKED, NO_KEY] : opts.referrals));
  const ctx = {
    JSON, Object, Array, String, Number, Promise,
    $: (id) => els[id],
    referrals: () => JSON.parse(JSON.stringify(list)),
    patients: () => JSON.parse(JSON.stringify(opts.patients || PATIENTS)),
    providers: () => [{ id: 'PV-1', name: 'Dr Ada Chen' }],
    // The real H() is an escaper; a pass-through would hide an escaping bug, so
    // the minimal real behaviour is used.
    H: (v) => String(v == null ? '' : v)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;'),
    dntEmptyRow: (res, cols, text) => '<tr><td colspan="' + cols + '">' + text + '</td></tr>',
    dntWriteFailText: (res, text) => text,
    st: (k, v) => { calls.stored.push({ key: k, value: v }); if (k === 'dnt_referrals_list') list = v; return true; },
    toast: (m) => { calls.toasts.push(String(m)); },
    sdnData: (action, resource, payload) => {
      calls.sent.push({ action, resource, payload });
      return Promise.resolve(opts.writeFails ? null : payload);
    },
    setReferralStatus: () => {},
    __els: els, __calls: calls, __list: () => list,
  };
  vm.createContext(ctx);
  vm.runInContext(
    fnBody('function rfUnlinked(') + '\n'
    + fnBody('function rReferrals()') + '\n'
    + fnBody('async function linkReferralPatient('), ctx);
  // RENDER ONCE, because that is the state of the page after load and the state
  // every assertion below is about. The first version of this file left the
  // harness unrendered, and four arms failed on empty DOM stubs -- while a
  // FIFTH passed on them: the seven-cells arm iterated zero rows and asserted
  // nothing at all. A check that finds nothing is indistinguishable from one
  // that looks at nothing, so that arm now counts the rows before trusting the
  // loop.
  if (!opts.noRender) ctx.rReferrals();
  return ctx;
}

// ═══════════════════════════════════════════════════════════════════════════
section('the count is DERIVED, and it counts every shape of "not linked"');

test('rfUnlinked counts an empty id, an absent key, and whitespace alike', () => {
  const c = harness();
  assert.deepStrictEqual(c.rfUnlinked([LINKED, UNLINKED, NO_KEY]).map((r) => r.id),
    ['RF-2', 'RF-3']);
  assert.deepStrictEqual(
    c.rfUnlinked([{ id: 'W', patient_id: '   ' }]).map((r) => r.id), ['W'],
    'a whitespace-only id is not a link -- the server filter trims too');
  assert.deepStrictEqual(c.rfUnlinked([LINKED]).map((r) => r.id), []);
  assert.deepStrictEqual(c.rfUnlinked([]).map((r) => r.id), []);
  // LENGTH, not deepStrictEqual, and the reason is the vm boundary rather than
  // laziness. For a null list the function returns the result of filtering an
  // array literal created INSIDE the vm context, so its prototype is the vm's
  // Array and not this file's -- deepStrictEqual compares prototypes and fails
  // on two empty arrays that are equal in every way that matters. The
  // non-empty arms above pass because they filter a HOST array handed in as a
  // fixture. Worth knowing before trusting deepStrictEqual across a vm.
  assert.strictEqual(c.rfUnlinked(null).length, 0,
    'a null list must not throw -- rReferrals runs before any data exists');
});

section('the note appears with a real count and HIDES at zero');

test('the note shows the count and says what it means', () => {
  const c = harness();
  c.rReferrals();
  const note = c.__els['rf-unlinked-note'];
  assert.strictEqual(note.style.display, 'block');
  assert.ok(/2 referrals not linked to a patient record/.test(note.innerHTML),
    'the count or the sentence is missing: ' + note.innerHTML);
  assert.ok(/provider feed/.test(note.innerHTML),
    'the note must say WHY it matters, not just that it happened');
});

test('one unlinked referral is singular, not "1 referrals"', () => {
  const c = harness({ referrals: [LINKED, UNLINKED] });
  c.rReferrals();
  const h = c.__els['rf-unlinked-note'].innerHTML;
  assert.ok(/1 referral not linked/.test(h), h);
  assert.ok(!/1 referrals/.test(h), h);
});

test('with nothing unlinked the note is HIDDEN and emptied', () => {
  const c = harness({ referrals: [LINKED] });
  c.rReferrals();
  const note = c.__els['rf-unlinked-note'];
  assert.strictEqual(note.style.display, 'none',
    'a banner that is always on screen stops being read');
  assert.strictEqual(note.innerHTML, '',
    'hidden is not enough -- stale markup left behind reappears the moment '
    + 'something else sets display');
});

test('the note is amber, NOT the app brand blue -- a warning stays semantic', () => {
  const c = harness();
  const h = c.__els['rf-unlinked-note'].innerHTML;
  assert.ok(/#FEF3C7/.test(h) && /#92400E/.test(h), h);
  assert.ok(!/var\(--p\)/.test(h) && !/#0EA5E9/.test(h),
    'the brand colour was used for a warning state');
});

section('the row marks itself as work, and the table keeps its seven columns');

test('an unlinked row carries the Unlinked badge and a link control; a linked row carries neither', () => {
  const c = harness();
  const rows = c.__els['referrals-tbody'].innerHTML.split('<tr>').filter(Boolean);
  assert.strictEqual(rows.length, 3, 'expected three rendered rows');
  const linkedRow = rows.find((r) => r.indexOf('Alice Smith') !== -1);
  const unlinkedRow = rows.find((r) => r.indexOf('Bobby Reyes') !== -1);
  assert.ok(/badge bw">Unlinked/.test(unlinkedRow), unlinkedRow);
  assert.ok(/linkReferralPatient/.test(unlinkedRow), 'no way to resolve it');
  assert.ok(!/Unlinked/.test(linkedRow), 'a linked referral was flagged as work');
  assert.ok(!/linkReferralPatient/.test(linkedRow), linkedRow);
});

test('every row still has SEVEN cells -- dntEmptyRow hardcodes colspan 7', () => {
  const c = harness();
  const rows = c.__els['referrals-tbody'].innerHTML.split('<tr>').filter(Boolean);
  assert.strictEqual(rows.length, 3,
    'this arm iterated ' + rows.length + ' rows -- it passed on zero once');
  rows.forEach((r) => {
    const cells = (r.match(/<td[ >]/g) || []).length;
    assert.strictEqual(cells, 7, 'row has ' + cells + ' cells, not 7: ' + r.slice(0, 120));
  });
});

test('the link control offers real patients and a neutral first option', () => {
  const c = harness();
  const h = c.__els['referrals-tbody'].innerHTML;
  assert.ok(/Link patient/.test(h));
  assert.ok(/value="PT-1">Alice Smith/.test(h), h);
  assert.ok(/value="PT-2">Robert Reyes/.test(h), h);
});

section('resolving one -- and what it must NOT do');

test('linking sets patient_id, persists, and pushes the row to the server', async () => {
  const c = harness();
  await c.linkReferralPatient('RF-2', 'PT-2');
  const sent = c.__calls.sent[0];
  assert.strictEqual(sent.resource, 'dnt_referrals');
  assert.strictEqual(sent.action, 'write');
  assert.strictEqual(sent.payload.id, 'RF-2');
  assert.strictEqual(sent.payload.patient_id, 'PT-2');
  assert.strictEqual(c.__list().find((r) => r.id === 'RF-2').patient_id, 'PT-2');
  assert.ok(/linked to Robert Reyes/.test(c.__calls.toasts.join(' ')), c.__calls.toasts);
});

test('linking does NOT overwrite the typed patient_name', async () => {
  const c = harness();
  await c.linkReferralPatient('RF-2', 'PT-2');
  // 'Bobby Reyes' is what the outside practice sent; 'Robert Reyes' is the
  // record. Rewriting the first would destroy the only evidence of what
  // arrived, which is exactly what a referral record is for.
  assert.strictEqual(c.__calls.sent[0].payload.patient_name, 'Bobby Reyes');
  assert.strictEqual(c.__list().find((r) => r.id === 'RF-2').patient_name, 'Bobby Reyes');
});

test('linking clears it from the queue, so the note count drops', async () => {
  const c = harness();
  assert.ok(/2 referrals not linked/.test(c.__els['rf-unlinked-note'].innerHTML));
  await c.linkReferralPatient('RF-2', 'PT-2');
  assert.ok(/1 referral not linked/.test(c.__els['rf-unlinked-note'].innerHTML),
    'the note did not re-derive after the link: ' + c.__els['rf-unlinked-note'].innerHTML);
});

test('the neutral first option is a no-op, not a link to nothing', async () => {
  const c = harness();
  await c.linkReferralPatient('RF-2', '');
  assert.strictEqual(c.__calls.sent.length, 0, 'an empty selection was pushed as a link');
  assert.strictEqual(c.__calls.stored.length, 0);
});

test('a patient that is not on file is refused rather than stored', async () => {
  const c = harness();
  await c.linkReferralPatient('RF-2', 'PT-GONE');
  assert.strictEqual(c.__calls.sent.length, 0);
  assert.ok(/not on file/.test(c.__calls.toasts.join(' ')), c.__calls.toasts);
  assert.strictEqual(c.__list().find((r) => r.id === 'RF-2').patient_id, '',
    'a nonexistent patient id reached the stored row');
});

test('a referral that is not on file is refused', async () => {
  const c = harness();
  await c.linkReferralPatient('RF-GONE', 'PT-2');
  assert.strictEqual(c.__calls.sent.length, 0);
  assert.ok(/not found/.test(c.__calls.toasts.join(' ')), c.__calls.toasts);
});

test('A REFUSED PUSH DOES NOT CLAIM SUCCESS -- it says the referral is still unlinked elsewhere', async () => {
  const c = harness({ writeFails: true });
  await c.linkReferralPatient('RF-2', 'PT-2');
  const said = c.__calls.toasts.join(' ');
  assert.ok(!/linked to Robert Reyes/.test(said), 'claimed a link the server refused: ' + said);
  assert.ok(/still unlinked everywhere else/.test(said), said);
});

// ═══════════════════════════════════════════════════════════════════════════
(async () => {
  for (const item of queue) {
    if (item.section) { console.log('\n-- ' + item.section); continue; }
    try { await item.fn(); pass++; console.log('  ok - ' + item.name); }
    catch (e) { fail++; console.log('  FAIL - ' + item.name + '\n    ' + (e && e.message)); }
  }
  console.log('\n' + pass + '/' + (pass + fail) + ' passed');
  if (fail) process.exitCode = 1;
})();
