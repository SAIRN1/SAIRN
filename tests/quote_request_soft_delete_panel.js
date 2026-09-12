// tests/quote_request_soft_delete_panel.js
//
// Run:  node tests/quote_request_soft_delete_panel.js
//
// The Quote requests panel rendered EVERY request with no status filter, so a
// declined one stayed in the table permanently -- red, button-less, and
// forever. Unlike every other collection in StoneDesk the feed is an
// UNAUTHENTICATED PUBLIC FORM, so the list is bounded by what strangers submit
// rather than by staff effort: the inbox could only grow and a shop had no way
// to clear it.
//
// Michael's decision, 2026-09-12: soft delete on the server plus a default
// filter in the panel. The server half is api/sd-data-quote-request-soft-delete.test.js
// and it drives the real handler; this file is the panel half.
//
// TWO THINGS THAT LOOK ALIKE AND ARE NOT, and most of these arms exist to keep
// them apart:
//
//   FILTERED  -- a promoted or declined request, hidden from the default view,
//                one keystroke away, and COUNTED ON SCREEN. Nothing left.
//   DELETED   -- `_deleted_at` set on the server, not returned by any read,
//                and still recoverable. The text is never altered.
//
// A filter that silently removed rows would be the same class of thing as an
// empty state that is really a failed read: the screen stops matching the data
// and nothing says so. So the hidden COUNT is asserted, not just the absence.
//
// THE FUNCTIONS ARE THE REAL ONES, pulled out of stonedesk.html and run in a
// vm against a fake DOM and a fake fetch. sdData() is the real one too -- a
// stub of it would let the call shape rot while these arms stayed green.

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

// Named signatures, each asserting it found its terminator, so a rename fails
// loudly here rather than quietly testing less than this file claims to.
function grabAt(sig, indent) {
  const s = html.indexOf(sig);
  assert.ok(s > 0, 'not found in stonedesk.html: ' + sig);
  const close = new RegExp('\\r?\\n' + indent + '\\};?(?=\\r?\\n)');
  const rest = html.slice(s);
  const m = rest.match(close);
  assert.ok(m, 'not terminated at indent ' + JSON.stringify(indent) + ': ' + sig);
  return rest.slice(0, m.index + m[0].length);
}
function grabLine(sig) {
  const s = html.indexOf(sig);
  assert.ok(s > 0, 'not found in stonedesk.html: ' + sig);
  return html.slice(s, html.indexOf('\n', s));
}

const LAYER = [
  grabLine('var _sdAuthRefused = {};'),
  grabLine('var _sdReadFailed  = {};'),
  // ADDED 2026-09-12 WITH THE MAP ITSELF. sdData() sets _sdLastStatus on
  // every path, so leaving it out of this list makes the real transport
  // throw ReferenceError inside the vm -- and the catch turns that into a
  // null return, i.e. every call in this suite silently 'failing'. A
  // hand-listed mirror of the layer's declarations is a mirror that goes
  // stale; this is the third suite this week to be broken by one.
  grabLine('var _sdLastStatus  = {};')
].join('\n') + '\n\n' + [
  'function sdAuthWasRefused(resource) {',
  'function sdReadFailed(resource) {',
  'function sdReadFailedNote(what) {',
  'function sdFetchTimeoutSignal(){',
  'async function sdData(action, resource, payload) {'
].map(s => grabAt(s, '')).join('\n\n') + '\n\nvar SD_FETCH_TIMEOUT_MS = 15000;\n';

const PANEL = [
  grabLine('function pcEl(id){return document.getElementById(id);}'),
  grabAt('async function pcRead(resource){', '  '),
  grabAt('async function pcWrite(resource,payload){', '  '),
  grabAt('function pcReadFailed(resource){', '  '),
  grabAt('function pcRenderRequests(){', '  '),
  grabAt('window.pcToggleHandled=function(){', '  '),
  grabAt('window.pcDeleteRequest=async function(id){', '  '),
  grabAt('window.pcSetRequest=async function(id,status){', '  ')
].join('\n\n');

const PC_HTML = (() => {
  const s = html.indexOf('function pcHtml(v){');
  assert.ok(s > 0, 'pcHtml not found');
  return html.slice(s, html.indexOf('\n', html.indexOf(".replace(/'/g,'&#39;');}", s)));
})();

// ---------------------------------------------------------------------------
// A fake DOM. `omit` leaves an element out entirely, because the panel's null
// guards are a real requirement: pcEl() returns null for an id that is not
// there, and a render that throws takes the whole panel with it.
function makeDoc(omit) {
  const els = {};
  const skip = omit || [];
  ['pc-requests-tbody', 'pc-show-handled', 'pc-requests-hidden'].forEach(id => {
    if (skip.indexOf(id) !== -1) return;
    els[id] = { id, value: '', checked: false, disabled: false,
                innerHTML: '', textContent: '' };
  });
  return { els, getElementById: id => els[id] || null };
}

function build(opts) {
  opts = opts || {};
  const doc = makeDoc(opts.omit);
  const calls = { fetch: [], notes: [], confirms: [] };
  const ctx = {
    console,
    document: doc,
    window: {},
    sessionStorage: { getItem: () => 'tok', setItem: () => {} },
    location: { origin: 'https://sairn.vercel.app' },
    escHtml: s => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;'),
    escAttrJs: s => String(s),
    sdLicenseKey: () => 'SD-TEST-2026',
    confirm: msg => { calls.confirms.push(String(msg)); return opts.confirm !== false; },
    notify: (msg, kind) => { calls.notes.push({ msg: String(msg), kind: kind }); },
    fetch: async (url, init) => {
      const body = init && init.body ? JSON.parse(init.body) : {};
      calls.fetch.push({ url: String(url), body });
      const r = (opts.route || (() => ({ status: 200, json: { ok: true, data: null } })))(body);
      if (r && r.thrown) throw new Error(r.thrown);
      return { ok: r.status >= 200 && r.status < 300, status: r.status, json: async () => r.json };
    }
  };
  ctx.globalThis = ctx;
  vm.createContext(ctx);
  const panel = opts.mutate ? opts.mutate(PANEL) : PANEL;
  vm.runInContext(
    LAYER + '\n\n(function(){\n' +
    '  var pcRequests=' + JSON.stringify(opts.requests || []) + ';\n' +
    '  var pcRequestsLoadFailed=' + (opts.loadFailed ? 'true' : 'false') + ';\n' +
    // Taken from the real file for the same reason every other grab here is:
    // a hand-written copy of a declaration is a copy that goes stale, which is
    // exactly what happened to public_catalog_no_false_empty.js on the day
    // this variable was added.
    '  ' + grabLine('var pcShowHandled=false;').trim() + '\n' +
    PC_HTML + '\n' + panel + '\n' +
    '  window._probe=function(){return {pcRequests:pcRequests,pcShowHandled:pcShowHandled};};\n' +
    '  window._render=pcRenderRequests;\n' +
    '})();', ctx, { filename: 'stonedesk-quote-requests-extract.js' });
  return { ctx, doc, calls, probe: () => ctx.window._probe() };
}

const R = (id, status, name) => ({ id, status, name, received_at: '2026-09-1' + id.slice(-1) });
const MIXED = [R('QR-1', 'pending', 'Pending Pat'),
               R('QR-2', 'promoted', 'Promoted Pru'),
               R('QR-3', 'declined', 'Declined Dan')];

function tbody(b) { return b.doc.els['pc-requests-tbody'].innerHTML; }

(async function main() {
  console.log('StoneDesk quote requests -- default filter and soft delete\n');

  // ══ 1. the default view is the work, not the archive ═════════════════════
  section('the inbox shows what is waiting, and says what it is hiding');

  await test('promoted and declined are NOT rendered by default', () => {
    const b = build({ requests: MIXED });
    b.ctx.window._render();
    const t = tbody(b);
    assert.ok(/Pending Pat/.test(t), 'the pending request is missing');
    assert.ok(!/Promoted Pru/.test(t), 'a promoted request rendered by default');
    assert.ok(!/Declined Dan/.test(t), 'a declined request rendered by default');
  });

  await test('and the count of what is hidden is stated on screen', () => {
    const b = build({ requests: MIXED });
    b.ctx.window._render();
    assert.strictEqual(b.doc.els['pc-requests-hidden'].textContent,
      '2 promoted or declined requests are hidden');
  });

  await test('one hidden request is described in the singular', () => {
    const b = build({ requests: [R('QR-1', 'pending', 'P'), R('QR-2', 'declined', 'D')] });
    b.ctx.window._render();
    assert.strictEqual(b.doc.els['pc-requests-hidden'].textContent,
      '1 promoted or declined request is hidden');
  });

  await test('ticking the box shows them, and clears the hidden count', () => {
    const b = build({ requests: MIXED });
    b.doc.els['pc-show-handled'].checked = true;
    b.ctx.window.pcToggleHandled();
    const t = tbody(b);
    assert.ok(/Promoted Pru/.test(t) && /Declined Dan/.test(t), 'handled rows still hidden');
    assert.strictEqual(b.doc.els['pc-requests-hidden'].textContent, '');
  });

  await test('nothing pending is NOT the same sentence as nothing at all', () => {
    const b = build({ requests: [R('QR-2', 'promoted', 'P'), R('QR-3', 'declined', 'D')] });
    b.ctx.window._render();
    const t = tbody(b);
    assert.ok(/Nothing waiting on you/.test(t), 'did not say the queue is clear: ' + t);
    assert.ok(/2 handled requests/.test(t), 'did not say how many are hidden: ' + t);
    assert.ok(!/No quote requests yet/.test(t),
      'a shop with two real requests was told it has none');
  });

  await test('a genuinely empty table still says "No quote requests yet"', () => {
    const b = build({ requests: [] });
    b.ctx.window._render();
    assert.ok(/No quote requests yet/.test(tbody(b)));
    assert.strictEqual(b.doc.els['pc-requests-hidden'].textContent, '');
  });

  // The whole point of the 2026-09-04 fix, which this change must not undo.
  await test('a FAILED read still does not claim an empty inbox', () => {
    const b = build({ requests: [], loadFailed: true });
    b.ctx.window._render();
    assert.ok(!/No quote requests yet/.test(tbody(b)));
    assert.ok(!/Nothing waiting on you/.test(tbody(b)));
  });

  await test('the panel does not throw when the filter controls are absent', () => {
    const b = build({ requests: MIXED, omit: ['pc-show-handled', 'pc-requests-hidden'] });
    b.ctx.window._render();          // must not throw
    assert.ok(/Pending Pat/.test(tbody(b)));
    b.ctx.window.pcToggleHandled();  // must not throw either
  });

  // ══ 2. delete is a soft delete, and it says so ═══════════════════════════
  section('delete hides and keeps -- it never edits and never destroys');

  await test('every rendered row offers Delete, handled ones included', () => {
    const b = build({ requests: MIXED });
    b.doc.els['pc-show-handled'].checked = true;
    b.ctx.window.pcToggleHandled();
    const t = tbody(b);
    assert.strictEqual((t.match(/pcDeleteRequest/g) || []).length, 3,
      'Delete is not offered on all three rows');
    // Promote/Decline remain pending-only -- a handled request is not re-decided.
    assert.strictEqual((t.match(/pcSetRequest/g) || []).length, 2);
  });

  await test('the confirm says the record is KEPT, and never "cannot be undone"', async () => {
    const b = build({ requests: MIXED, confirm: false });
    await b.ctx.window.pcDeleteRequest('QR-1');
    const msg = b.calls.confirms[0] || '';
    assert.ok(/kept/i.test(msg) && /restored/i.test(msg),
      'the confirm does not say the record is kept and restorable: ' + msg);
    assert.ok(!/cannot be undone/i.test(msg),
      'the confirm claims an irreversible delete, which is false here');
  });

  await test('declining the confirm sends nothing at all', async () => {
    const b = build({ requests: MIXED, confirm: false });
    await b.ctx.window.pcDeleteRequest('QR-1');
    assert.strictEqual(b.calls.fetch.length, 0);
    assert.strictEqual(b.probe().pcRequests.length, 3);
  });

  await test("the call is action:'soft_delete' on sd_quote_requests, carrying only the id", async () => {
    const b = build({ requests: MIXED,
      route: () => ({ status: 200, json: { ok: true, data: { _deleted_at: 'now' } } }) });
    await b.ctx.window.pcDeleteRequest('QR-1');
    const sent = b.calls.fetch[0];
    assert.ok(sent, 'no request was sent');
    assert.strictEqual(sent.body.action, 'soft_delete');
    assert.strictEqual(sent.body.resource, 'sd_quote_requests');
    assert.deepStrictEqual(sent.body.payload, { id: 'QR-1' });
  });

  await test('a successful delete removes the row and says it is recoverable', async () => {
    const b = build({ requests: MIXED,
      route: () => ({ status: 200, json: { ok: true, data: { _deleted_at: 'now' } } }) });
    await b.ctx.window.pcDeleteRequest('QR-1');
    assert.strictEqual(b.probe().pcRequests.length, 2);
    assert.ok(!/Pending Pat/.test(tbody(b)));
    const note = b.calls.notes[b.calls.notes.length - 1];
    assert.strictEqual(note.kind, 'ok');
    assert.ok(/restored/i.test(note.msg), 'the success note does not say it can be restored');
  });

  // THE ARM THAT MATTERS. This panel has no local cache -- pcRequests is what
  // the server last returned -- so an optimistic removal would show a deletion
  // that did not happen, and the next load would bring the row back with no
  // explanation. Same reason pcSetRequest() refuses to patch its local copy
  // when the write comes back null.
  await test('A FAILED DELETE LEAVES THE ROW ON SCREEN and says nothing changed', async () => {
    const b = build({ requests: MIXED, route: () => ({ status: 500, json: { error: { message: 'no' } } }) });
    // Rendered FIRST, because the failure path returns without re-rendering --
    // asserting against a table that was never drawn would pass on an empty
    // string and prove nothing about what the user is looking at.
    b.ctx.window._render();
    assert.ok(/Pending Pat/.test(tbody(b)), 'precondition: the row was not on screen to begin with');
    await b.ctx.window.pcDeleteRequest('QR-1');
    assert.strictEqual(b.probe().pcRequests.length, 3, 'the row was removed on a failed delete');
    assert.ok(/Pending Pat/.test(tbody(b)), 'the row vanished from the table');
    const note = b.calls.notes[b.calls.notes.length - 1];
    assert.strictEqual(note.kind, 'err');
    assert.ok(/still there/i.test(note.msg), 'the failure note does not say the request survives');
  });

  await test('a network throw is handled the same way, not as a success', async () => {
    const b = build({ requests: MIXED, route: () => ({ thrown: 'offline' }) });
    await b.ctx.window.pcDeleteRequest('QR-1');
    assert.strictEqual(b.probe().pcRequests.length, 3);
    assert.strictEqual(b.calls.notes[b.calls.notes.length - 1].kind, 'err');
  });

  // ══ 3. mutation: the pre-fix render must reproduce the defect ════════════
  section('MUTATION: the unfiltered render, restored, must bring the archive back');

  await test('MUTANT: without the status filter, declined requests render again', () => {
    const b = build({
      requests: MIXED,
      mutate: src => {
        const before = src;
        const out = src.replace(
          'var sorted=(pcShowHandled?pcRequests:pcRequests.filter(function(q){return q.status===\'pending\';}))',
          'var sorted=(pcRequests)');
        assert.notStrictEqual(out, before,
          'the mutation anchor no longer matches pcRenderRequests -- this arm is proving nothing');
        return out;
      }
    });
    b.ctx.window._render();
    const t = tbody(b);
    assert.ok(/Declined Dan/.test(t) && /Promoted Pru/.test(t),
      'the mutant did not reproduce the defect, so the filter is not what hides them');
  });

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  if (fail) process.exit(1);
})();
