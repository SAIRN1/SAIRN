// tests/intake_no_false_success.js
//
// Run:  node tests/intake_no_false_success.js
//
// The Project Intake panel reported success it did not have, in four places at
// once. Every Supabase call in it was wrapped in a bare `try{...}catch(e){}`,
// and `anon` has never been granted anything on intake_submissions -- verified
// live with the real shipped key, which returns 42501 permission denied. So:
//
//   * the READ failed, the catch swallowed it, and the panel fell back to
//     localStorage and rendered that -- one line below a comment reading
//     "Supabase is the real source of truth here";
//   * intakeAccept() created a Customer and a Job, marked the submission
//     accepted, and the server update that makes that stick did nothing.
//     Nothing was shown. The shop believes an intake is handled;
//     intake_submissions still says pending, so it can be worked twice;
//   * intakeDismiss() deleted from this device only, so the row returns on the
//     next successful refresh and reads as the app undoing the user;
//   * intakeAnalyzePhoto() threw away a paid Claude call without saying so.
//
// And the Copy button answered with "Intake link copied!" for a URL that is a
// 404 -- an unqualified success at the exact moment the user is about to send
// a dead link to a paying customer's customer.
//
// This test drives the REAL functions against a fake Supabase client that can
// be told to fail with the real 42501, because a stub of intakeServerWrite()
// would be a stub of the thing under test.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const ROOT = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(ROOT, 'stonedesk.html'), 'utf8');

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

// ---------------------------------------------------------------------------
// Extract the real functions. Named list rather than a region grab, so adding
// an unrelated function between them cannot silently drop one from the test.
function grab(sig) {
  const s = html.indexOf(sig);
  assert.ok(s > 0, sig + ' not found in stonedesk.html');
  const rel = html.slice(s).search(/\r?\n\}/);
  assert.ok(rel > 0, sig + ' is not terminated');
  return html.slice(s, s + rel) + '\n}';
}
const SRC = [
  'function intakeServerNote() {',
  'function intakeDescribeError(e) {',
  'async function intakeRefresh() {',
  'async function intakeServerWrite(label, fn) {',
  'async function intakeAnalyzePhoto(id) {',
  'async function intakeAccept(id) {',
  'async function intakeDismiss(id) {',
  'function intakeCopyLink() {',
  'function intakeShareLink() {',
].map(grab).join('\n\n');

const PERMISSION_DENIED = { code: '42501', message: 'permission denied for table intake_submissions' };

// A fake Supabase client. `mode` decides what the chained call resolves to,
// which is how one harness covers a working server, a refusing server and no
// server at all without three different fixtures.
function fakeSb(mode, rows) {
  const result = mode === 'ok'
    ? { data: rows || [], error: null }
    : (mode === 'throws' ? null : { data: null, error: PERMISSION_DENIED });
  const chain = {
    select: () => chain, order: () => chain, limit: () => Promise.resolve(result),
    update: () => chain, delete: () => chain,
    eq: () => (mode === 'throws' ? Promise.reject(PERMISSION_DENIED) : Promise.resolve(result)),
  };
  if (mode === 'throws') chain.limit = () => Promise.reject(PERMISSION_DENIED);
  return { from: () => chain };
}

function makeCtx(opts) {
  opts = opts || {};
  const store = {};
  const toasts = [];
  const logs = { warn: [], error: [] };
  const listEl = { innerHTML: '' };
  const ctx = {
    INTAKE_TABLE: 'intake_submissions',
    INTAKE_FORM_LIVE: ('formLive' in opts) ? opts.formLive : false,
    intakeSubmissions: opts.submissions || [],
    intakeCurrentTab: 'pending',
    _intakeServerReachable: null,
    _intakeServerError: '',
    getSDSupabase: () => (opts.sb === null ? null : fakeSb(opts.sb || 'ok', opts.rows)),
    st: (k, v) => { store[k] = JSON.stringify(v); return true; },
    escHtml: (s) => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;'),
    showToast: (m) => toasts.push(m),
    intakeRender: function () { listEl.innerHTML = ctx.intakeServerNote(); },
    confirm: () => (('confirmAnswer' in opts) ? opts.confirmAnswer : true),
    localStorage: {
      getItem: (k) => (k in store ? store[k] : (opts.cache && k === 'sd_intake' ? JSON.stringify(opts.cache) : null)),
      setItem: (k, v) => { store[k] = v; },
    },
    navigator: {
      clipboard: { writeText: () => Promise.resolve() },
      share: undefined,
    },
    document: { getElementById: (id) => (id === 'intake-list' ? listEl : { value: 'https://sairn.vercel.app/stonedesk-intake?shop=Pinnacle' }) },
    console: {
      log: () => {}, warn: (...a) => logs.warn.push(a.join(' ')),
      error: (...a) => logs.error.push(a.map(String).join(' ')),
    },
  };
  ctx.window = ctx;
  vm.createContext(ctx);
  vm.runInContext(SRC, ctx);
  return { ctx, toasts, logs, listEl, store };
}

(async function () {

// -------------------------------------------------------------------------
section('the read no longer presents this device as the server');

await atest('a refused read is REPORTED, not swallowed', async () => {
  const h = makeCtx({ sb: 'error', cache: [{ id: 'A', status: 'pending' }] });
  await h.ctx.intakeRefresh();
  assert.strictEqual(h.ctx._intakeServerReachable, false, 'the failure was not recorded');
  assert.ok(/permission denied/i.test(h.ctx._intakeServerError),
    'the reason was lost: ' + h.ctx._intakeServerError);
});

await atest('...and ALWAYS logged -- a read that vanishes must not vanish from the console', async () => {
  const h = makeCtx({ sb: 'error' });
  await h.ctx.intakeRefresh();
  assert.ok(h.logs.error.length > 0, 'nothing was logged for a failed read');
  assert.ok(/intake/.test(h.logs.error[0]), 'the log does not name the feature');
});

await atest('the banner says the list is device-local and that actions will not stick', async () => {
  const h = makeCtx({ sb: 'error', cache: [{ id: 'A', status: 'pending' }] });
  await h.ctx.intakeRefresh();
  const note = h.ctx.intakeServerNote();
  assert.ok(/Not connected to the server/i.test(note), 'no banner: ' + note);
  assert.ok(/THIS device/i.test(note), 'the banner does not say the data is device-local');
  assert.ok(/will not stick/i.test(note), 'the banner does not warn that actions are lost');
});

await atest('THE EMPTY STATE IS THE MISLEADING ONE and it is covered', async () => {
  // "No pending submissions yet" and "we could not ask" look identical, and
  // only one of them means there is nothing to do.
  const h = makeCtx({ sb: 'error', cache: [] });
  await h.ctx.intakeRefresh();
  h.ctx.intakeRender = null;              // use the real one below
  vm.runInContext(grab('function intakeRender() {'), h.ctx);
  h.ctx.intakeRender();
  assert.ok(!/No pending submissions yet/.test(h.listEl.innerHTML),
    'an unreachable server still reports "no submissions yet"');
  assert.ok(/not the same as there being no submissions/i.test(h.listEl.innerHTML),
    'the empty state does not distinguish empty from unfetched');
});

await atest('a WORKING read reports no problem and caches what it really got', async () => {
  const h = makeCtx({ sb: 'ok', rows: [{ id: 'A', status: 'pending' }] });
  await h.ctx.intakeRefresh();
  assert.strictEqual(h.ctx._intakeServerReachable, true);
  assert.strictEqual(h.ctx.intakeServerNote(), '', 'a healthy panel is showing a warning');
  assert.strictEqual(h.ctx.intakeSubmissions.length, 1);
  assert.ok(h.store.sd_intake, 'a successful read was not cached');
});

await atest('no Supabase client at all is a failure, not a silent local mode', async () => {
  const h = makeCtx({ sb: null, cache: [{ id: 'A' }] });
  await h.ctx.intakeRefresh();
  assert.strictEqual(h.ctx._intakeServerReachable, false);
  assert.ok(h.logs.warn.length > 0, 'nothing was logged when there was no client');
});

// -------------------------------------------------------------------------
section('writes report whether they actually happened');

await atest('intakeServerWrite returns false on a PostgREST error object', async () => {
  const h = makeCtx({ sb: 'error' });
  const ok = await h.ctx.intakeServerWrite('probe', (sb) => sb.from('t').update({}).eq('id', 1));
  assert.strictEqual(ok, false);
  assert.strictEqual(h.ctx._intakeServerReachable, false);
});

await atest('...and on a THROWN error, which is a different path', async () => {
  const h = makeCtx({ sb: 'throws' });
  const ok = await h.ctx.intakeServerWrite('probe', (sb) => sb.from('t').update({}).eq('id', 1));
  assert.strictEqual(ok, false);
  assert.ok(h.logs.error.length > 0, 'a thrown write was not logged');
});

await atest('...and TRUE only when the server really answered', async () => {
  const h = makeCtx({ sb: 'ok' });
  const ok = await h.ctx.intakeServerWrite('probe', (sb) => sb.from('t').update({}).eq('id', 1));
  assert.strictEqual(ok, true);
  assert.strictEqual(h.ctx._intakeServerError, '');
});

await atest('THE WORST ONE: a failed accept does not report the job as filed', async () => {
  // intakeAccept() creates a Customer and a Job locally and then marks the
  // submission accepted on the server. Only the last step stops the same
  // intake being worked again from another device -- and it was the step that
  // failed silently while the toast said "Customer + Job created from intake!".
  const h = makeCtx({ sb: 'error', submissions: [{ id: 'A', status: 'pending', client_name: 'R Ochoa', project_type: 'kitchen', rough_run_a_ft: 12, shape: 'lshape' }] });
  Object.assign(h.ctx, { sdCustomers: [], sdJobs: [], sdSave3: () => {}, saveSD4: () => {}, sdLocalToday: () => '2026-09-03' });
  await h.ctx.intakeAccept('A');
  assert.strictEqual(h.ctx.sdCustomers.length, 1, 'the local customer was not created');
  assert.strictEqual(h.ctx.sdJobs.length, 1, 'the local job was not created');
  const t = h.toasts.join(' | ');
  assert.ok(!/^Customer \+ Job created from intake!$/.test(h.toasts[0]),
    'a failed accept still reported plain success: ' + t);
  assert.ok(/NOT updated/i.test(t) && /worked twice/i.test(t),
    'the toast does not say the intake stays pending elsewhere: ' + t);
});

await atest('...and a SUCCESSFUL accept still reads as plain success', async () => {
  const h = makeCtx({ sb: 'ok', submissions: [{ id: 'A', status: 'pending', client_name: 'R Ochoa' }] });
  Object.assign(h.ctx, { sdCustomers: [], sdJobs: [], sdSave3: () => {}, saveSD4: () => {}, sdLocalToday: () => '2026-09-03' });
  await h.ctx.intakeAccept('A');
  assert.strictEqual(h.toasts[0], 'Customer + Job created from intake!');
});

await atest('a lost photo analysis is announced -- it is billable work thrown away', async () => {
  // The photo goes to Claude again next time and the shop pays for it again.
  // The result is on screen either way, which is exactly why the loss was
  // invisible.
  const sub = { id: 'A', status: 'pending', photo_base64: 'data:image/jpeg;base64,QUJD' };
  const h = makeCtx({ sb: 'error', submissions: [sub] });
  const els = { 'intake-analyze-modal': { style: {} }, 'intake-analyze-result': { innerHTML: '' }, 'intake-analyze-actions': { innerHTML: '' } };
  h.ctx.document.getElementById = (id) => els[id] || { value: '', innerHTML: '', style: {} };
  h.ctx.SAIRN_API = 'https://example.invalid/api';
  h.ctx.APP_ID_LOCAL = 'stonedesk';
  h.ctx.fetch = () => Promise.resolve({ json: () => Promise.resolve({
    content: [{ text: '{"shape":"lshape","runA_in":144,"sinkCount":1,"summary":"L-shape kitchen."}' }] }) });
  await h.ctx.intakeAnalyzePhoto('A');
  const t = h.toasts.join(' | ');
  assert.ok(/NOT saved/i.test(t), 'a discarded analysis said nothing: ' + t);
  assert.ok(/re-running/i.test(t), 'the toast does not say it must be redone: ' + t);
});

await atest('...and a SAVED analysis stays quiet', async () => {
  const sub = { id: 'A', status: 'pending', photo_base64: 'data:image/jpeg;base64,QUJD' };
  const h = makeCtx({ sb: 'ok', submissions: [sub] });
  const els = { 'intake-analyze-modal': { style: {} }, 'intake-analyze-result': { innerHTML: '' }, 'intake-analyze-actions': { innerHTML: '' } };
  h.ctx.document.getElementById = (id) => els[id] || { value: '', innerHTML: '', style: {} };
  h.ctx.SAIRN_API = 'https://example.invalid/api';
  h.ctx.APP_ID_LOCAL = 'stonedesk';
  h.ctx.fetch = () => Promise.resolve({ json: () => Promise.resolve({
    content: [{ text: '{"shape":"lshape","runA_in":144,"sinkCount":1,"summary":"L-shape kitchen."}' }] }) });
  await h.ctx.intakeAnalyzePhoto('A');
  assert.strictEqual(h.toasts.length, 0, 'a working save nagged the user: ' + JSON.stringify(h.toasts));
  assert.ok(sub.claude_analysis && sub.claude_analysis.shape === 'lshape', 'the analysis was not attached');
});

await atest('a failed delete tells the user it will come back', async () => {
  const h = makeCtx({ sb: 'error', submissions: [{ id: 'A' }, { id: 'B' }] });
  await h.ctx.intakeDismiss('A');
  assert.ok(h.toasts.some((t) => /this device only/i.test(t) && /reappear/i.test(t)),
    'a failed delete said nothing: ' + JSON.stringify(h.toasts));
});

await atest('a SUCCESSFUL delete stays quiet -- no warning fatigue', async () => {
  const h = makeCtx({ sb: 'ok', submissions: [{ id: 'A' }] });
  await h.ctx.intakeDismiss('A');
  assert.strictEqual(h.toasts.length, 0, 'a working delete nagged the user: ' + JSON.stringify(h.toasts));
});

await atest('a cancelled delete does not touch the server at all', async () => {
  const h = makeCtx({ sb: 'error', submissions: [{ id: 'A' }], confirmAnswer: false });
  await h.ctx.intakeDismiss('A');
  assert.strictEqual(h.ctx.intakeSubmissions.length, 1, 'cancel still removed the row');
  assert.strictEqual(h.toasts.length, 0);
});

// -------------------------------------------------------------------------
section('the copy/share buttons stop claiming success for a 404');

test('Copy does not report plain success while the form is dead', () => {
  const h = makeCtx({ formLive: false });
  h.ctx.intakeCopyLink();
  assert.strictEqual(h.toasts.length, 1);
  assert.ok(!/^Intake link copied!$/.test(h.toasts[0]),
    'the toast still claims unqualified success: ' + h.toasts[0]);
  assert.ok(/404/.test(h.toasts[0]), 'the toast does not say why: ' + h.toasts[0]);
  assert.ok(/not send it to a client/i.test(h.toasts[0]), 'the toast gives no instruction');
});

test('Share ASKS FIRST, because it leaves the building in one tap', () => {
  let asked = null;
  const h = makeCtx({ formLive: false });
  h.ctx.confirm = (m) => { asked = m; return false; };
  h.ctx.intakeShareLink();
  assert.ok(asked, 'Share sent a dead link with no confirmation');
  assert.ok(/404/.test(asked), 'the confirm does not say the link is dead: ' + asked);
  assert.strictEqual(h.toasts.length, 0, 'declining the confirm still shared');
});

test('declining the Share confirm really does nothing', () => {
  const h = makeCtx({ formLive: false });
  let copied = 0;
  h.ctx.navigator.clipboard.writeText = () => { copied++; return Promise.resolve(); };
  h.ctx.confirm = () => false;
  h.ctx.intakeShareLink();
  assert.strictEqual(copied, 0, 'the share text was copied after the user said no');
});

test('when the form IS live, both buttons behave normally again', () => {
  const h = makeCtx({ formLive: true });
  h.ctx.intakeCopyLink();
  assert.strictEqual(h.toasts[0], 'Intake link copied!');
  let asked = false;
  h.ctx.confirm = () => { asked = true; return true; };
  h.ctx.intakeShareLink();
  assert.strictEqual(asked, false, 'a live form still nags before sharing');
});

test('INTAKE_FORM_LIVE is a single flag, not a claim repeated in three places', () => {
  const decls = html.match(/var INTAKE_FORM_LIVE\s*=/g) || [];
  assert.strictEqual(decls.length, 1, 'INTAKE_FORM_LIVE is declared ' + decls.length + ' times');
  assert.match(html, /var INTAKE_FORM_LIVE = false;/,
    'the flag is true while the form is still a 404 -- if the form shipped, this test should have been updated with it');
});

// -------------------------------------------------------------------------
section('the empty catches are gone, not merely bypassed');

test('no bare catch remains around an intake_submissions call', () => {
  const i = html.indexOf('var INTAKE_TABLE');
  const j = html.indexOf('function intakeLoadToDraw');
  assert.ok(i > 0 && j > i, 'could not bound the intake block');
  // Comments are stripped first. The block comment introducing the fix quotes
  // `try{...}catch(e){}` in prose to describe what was wrong, and the first
  // version of this assertion matched its own documentation -- the same
  // quoted-mention false positive that a naive override matcher hits.
  const block = html.slice(i, j).replace(/\/\/[^\n]*/g, '');
  const bare = block.match(/catch\s*\([A-Za-z_$][\w$]*\)\s*\{\s*\}/g) || [];
  assert.strictEqual(bare.length, 0,
    'bare empty catch still present in the intake block: ' + JSON.stringify(bare));
});

test('the "Supabase is the real source of truth" comment is gone', () => {
  // It sat directly above the line that rendered localStorage instead.
  assert.ok(!/Supabase is the real source of truth here/.test(html),
    'the comment that was backwards in practice is still there');
});

console.log('\n' + (fail === 0
  ? 'ALL ' + pass + ' INTAKE HONESTY ASSERTIONS PASS'
  : pass + ' passed, ' + fail + ' FAILED'));
process.exit(fail === 0 ? 0 : 1);

})();
