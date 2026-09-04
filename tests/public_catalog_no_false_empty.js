// tests/public_catalog_no_false_empty.js
//
// Run:  node tests/public_catalog_no_false_empty.js
//
// StoneDesk's Public Catalog panel turned every failed read into a confident
// empty answer, and one of the three could destroy data rather than only
// mislead.
//
//   * pcRead('sd_public_shop') returning null became {shop_slug:'',published:false},
//     and pcRenderShop() wrote that into the form -- every field cleared, the
//     Publish box unticked -- above the sentence "No public address set yet, so
//     nothing is reachable". A shop with a LIVE published catalog was told it
//     had never set one up. If they then pressed Save, pcSaveShop() sent the
//     form as it stood: blanks over their real record, published:false over a
//     live page. THE CATALOG GOES DARK AND THE CONTACT DETAILS ARE GONE, and
//     the screen that caused it looked like a first-run setup form.
//
//   * pcRead('sd_quote_requests') returning null became [] and the panel said
//     "No quote requests yet" -- a claim about inbound business, made from a
//     request that never reached a table.
//
//   * pcLoadLinks()'s `(r && Array.isArray(r.data)) ? r.data : []` did the same
//     to order-tracking links, so a shop could reissue a link that was already
//     live and could not revoke one it wanted dead.
//
// NONE OF THIS IS HYPOTHETICAL ON THIS APP TODAY. Proven from production on
// 2026-09-04: sql/stonedesk_public_surface_schema.sql has never been run, so
// sd_public_shop and sd_quote_requests do not exist and every read of them
// 404s. The panel has been showing all three fabricated empties since it
// shipped on 2026-09-02.
//
// The root enabler was one layer down. sdData() recorded 401/403 in
// _sdAuthRefused -- added 2026-09-02 for exactly this class -- and recorded
// NOTHING for a 404, a 500, an `ok:false` body or a network throw. All of those
// returned the same null an empty resource returns. That is fixed here too, and
// tested first, because every panel on this platform reads through it.
//
// These drive the REAL functions out of stonedesk.html against a fake fetch and
// a fake DOM. A stub of sdData() would be a stub of the thing under test.

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

// ---------------------------------------------------------------------------
// Extraction. Named signatures rather than a region grab, so a function added
// between them cannot silently drop one out of the suite -- and every grab
// asserts it found its terminator, so a rename fails loudly here instead of
// quietly testing less than it claims to.
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
  const e = html.indexOf('\n', s);
  return html.slice(s, e);
}

// The shared data layer, at top level (closing brace in column 0). The two
// state maps are taken by line and asserted present -- they are the whole
// mechanism, and a rename that left the functions intact would otherwise make
// this suite pass while testing a different variable.
const LAYER = [
  grabLine('var _sdAuthRefused = {};'),
  grabLine('var _sdReadFailed  = {};')
].join('\n') + '\n\n' + [
  'function sdAuthWasRefused(resource) {',
  'function sdReadFailed(resource) {',
  'function sdReadFailedNote(what) {',
  'async function sdData(action, resource, payload) {'
].map(sig => grabAt(sig, '')).join('\n\n');

// The panel, two spaces in (it lives inside an IIFE).
const PANEL = [
  grabLine('function pcEl(id){return document.getElementById(id);}'),
  grabAt('function pcNote(msg,kind){', '  '),
  grabAt('async function pcRead(resource){', '  '),
  grabAt('async function pcWrite(resource,payload){', '  '),
  grabAt('function pcReadFailed(resource){', '  '),
  grabAt('function pcSetShopFormEnabled(on){', '  '),
  grabAt('function pcRenderShop(){', '  '),
  grabAt('window.pcSaveShop=async function(){', '  '),
  grabAt('function pcRenderRequests(){', '  '),
  grabAt('async function pcTrackCall(payload){', '  '),
  grabAt('async function pcLoadLinks(){', '  '),
  grabAt('function pcRenderLinks(){', '  '),
  grabAt('window.pcRenderPublicCatalog=async function(){', '  ')
].join('\n\n');

// pcHtml is two lines and ends mid-line, so it is taken by span rather than by
// the brace matcher.
const PC_HTML = (() => {
  const s = html.indexOf('function pcHtml(v){');
  assert.ok(s > 0, 'pcHtml not found');
  const e = html.indexOf('\n', html.indexOf(".replace(/'/g,'&#39;');}", s));
  return html.slice(s, e);
})();

// ---------------------------------------------------------------------------
// A fake DOM with only what these functions touch.
function makeDoc() {
  const els = {};
  function mk(id) {
    return { id, value: '', checked: false, disabled: false, innerHTML: '', _el: true };
  }
  ['pc-slug', 'pc-name', 'pc-phone', 'pc-email', 'pc-address', 'pc-blurb',
   'pc-published', 'pc-save-shop', 'pc-shop-status', 'pc-requests-tbody',
   'pc-track-tbody'].forEach(id => { els[id] = mk(id); });
  return { els, getElementById: id => els[id] || null };
}

// One sandbox per test, so no flag can leak between them.
function build(opts) {
  opts = opts || {};
  const doc = makeDoc();
  const calls = { fetch: [], writes: [] };
  const ctx = {
    console,
    document: doc,
    window: {},
    sessionStorage: { getItem: () => 'tok', setItem: () => {} },
    location: { origin: 'https://sairn.vercel.app' },
    escHtml: s => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;'),
    escAttrJs: s => String(s),
    sdLicenseKey: () => opts.noLicence ? '' : 'SD-TEST-2026',
    fetch: async (url, init) => {
      calls.fetch.push({ url: String(url), body: init && init.body ? JSON.parse(init.body) : null });
      const body = init && init.body ? JSON.parse(init.body) : {};
      if (body.action === 'write') calls.writes.push(body);
      const r = opts.route(body, String(url));
      if (r && r.thrown) throw new Error(r.thrown);
      return {
        ok: r.status >= 200 && r.status < 300,
        status: r.status,
        json: async () => r.json
      };
    },
    // Panel neighbours this suite does not exercise.
    pcRenderSlabs: () => {}, pcRenderRemnants: () => {}, pcFillCustomerSelect: () => {},
    pcCustName: id => String(id), notify: () => {}
  };
  ctx.globalThis = ctx;
  vm.createContext(ctx);
  const panel = opts.mutate ? opts.mutate(PANEL) : PANEL;
  vm.runInContext(
    LAYER + '\n\n(function(){\n' +
    '  var pcShop=null, pcRequests=[], pcLinks=[];\n' +
    '  var pcShopLoadFailed=false, pcRequestsLoadFailed=false, pcLinksLoadFailed=false;\n' +
    '  var TRACK_API="/api/stonedesk-track";\n' +
    PC_HTML + '\n' + panel + '\n' +
    '  window._probe=function(){return {pcShop:pcShop,pcRequests:pcRequests,pcLinks:pcLinks,' +
    'shopFailed:pcShopLoadFailed,reqFailed:pcRequestsLoadFailed,linkFailed:pcLinksLoadFailed};};\n' +
    '})();', ctx, { filename: 'stonedesk-public-catalog-extract.js' });
  return { ctx, doc, calls, probe: () => ctx.window._probe() };
}

// Route helpers. `resource` on a sd-data body, `action` on a track body.
function routes(map) {
  return body => {
    if (body.resource) return map[body.resource] || { status: 200, json: { ok: true, data: null } };
    return map.track || { status: 200, json: { ok: true, data: [] } };
  };
}
const OK_NULL = { status: 200, json: { ok: true, data: null } };
const OK_EMPTY_ARR = { status: 200, json: { ok: true, data: [] } };
const NOT_FOUND = { status: 404, json: { message: 'Could not find the table' } };

async function main() {
  console.log('StoneDesk Public Catalog -- a read that failed is not a shop with no settings\n');

  // ══ 1. the shared data layer ═════════════════════════════════════════════
  section('sdData records every failure, not only 401/403');

  for (const status of [404, 500, 502]) {
    await test('HTTP ' + status + ' marks the resource as FAILED (it used to mark it clean)', async () => {
      const b = build({ route: () => ({ status, json: { message: 'nope' } }) });
      const out = await b.ctx.sdData('read', 'sd_public_shop', {});
      assert.strictEqual(out, null);
      assert.strictEqual(b.ctx.sdReadFailed('sd_public_shop'), true);
      assert.strictEqual(b.ctx.sdAuthWasRefused('sd_public_shop'), false,
        'a 404 must not be reported as an auth refusal');
    });
  }

  for (const status of [401, 403]) {
    await test('HTTP ' + status + ' still marks an AUTH REFUSAL, and now also a failure', async () => {
      const b = build({ route: () => ({ status, json: { message: 'no' } }) });
      await b.ctx.sdData('read', 'employees', {});
      assert.strictEqual(b.ctx.sdAuthWasRefused('employees'), true, 'the 2026-09-02 behaviour regressed');
      assert.strictEqual(b.ctx.sdReadFailed('employees'), true);
    });
  }

  await test('a 200 carrying ok:false is a failure, not an empty resource', async () => {
    const b = build({ route: () => ({ status: 200, json: { ok: false, error: 'boom' } }) });
    assert.strictEqual(await b.ctx.sdData('read', 'sd_quote_requests', {}), null);
    assert.strictEqual(b.ctx.sdReadFailed('sd_quote_requests'), true);
  });

  await test('a network throw is a failure, and does not leave the previous state standing', async () => {
    const b = build({ route: body => body.resource === 'x' ? { thrown: 'ECONNRESET' } : OK_NULL });
    await b.ctx.sdData('read', 'x', {});          // fails
    assert.strictEqual(b.ctx.sdReadFailed('x'), true);
  });

  await test('a genuine empty read is NOT a failure -- this is the whole distinction', async () => {
    const b = build({ route: () => OK_NULL });
    assert.strictEqual(await b.ctx.sdData('read', 'sd_public_shop', {}), null);
    assert.strictEqual(b.ctx.sdReadFailed('sd_public_shop'), false);
  });

  await test('a success after a failure clears the flag, so one blip is not permanent', async () => {
    let first = true;
    const b = build({ route: () => { const r = first ? NOT_FOUND : OK_NULL; first = false; return r; } });
    await b.ctx.sdData('read', 'sd_public_shop', {});
    assert.strictEqual(b.ctx.sdReadFailed('sd_public_shop'), true);
    await b.ctx.sdData('read', 'sd_public_shop', {});
    assert.strictEqual(b.ctx.sdReadFailed('sd_public_shop'), false);
  });

  // ══ 2. the shop record -- the one that could destroy data ════════════════
  section('the shop record: a failed read must not become a blank form');

  await test('a 404 on sd_public_shop does NOT say "No public address set yet"', async () => {
    const b = build({ route: routes({ sd_public_shop: NOT_FOUND, sd_quote_requests: OK_EMPTY_ARR }) });
    await b.ctx.window.pcRenderPublicCatalog();
    const note = b.doc.els['pc-shop-status'].innerHTML;
    assert.ok(!/No public address set yet/.test(note),
      'a dead table still reported the shop as never set up');
    assert.ok(/Could not load your public settings/.test(note), 'note was: ' + note);
    assert.strictEqual(b.probe().shopFailed, true);
  });

  await test('and it does NOT blank the form -- nothing is written into the fields', async () => {
    const b = build({ route: routes({ sd_public_shop: NOT_FOUND, sd_quote_requests: OK_EMPTY_ARR }) });
    b.doc.els['pc-slug'].value = 'main-street-stone';
    b.doc.els['pc-name'].value = 'Main Street Stone';
    b.doc.els['pc-published'].checked = true;
    await b.ctx.window.pcRenderPublicCatalog();
    assert.strictEqual(b.doc.els['pc-slug'].value, 'main-street-stone', 'the slug was cleared');
    assert.strictEqual(b.doc.els['pc-name'].value, 'Main Street Stone', 'the name was cleared');
    assert.strictEqual(b.doc.els['pc-published'].checked, true, 'the Publish box was unticked');
  });

  await test('the form and the Save button are DISABLED, not merely annotated', async () => {
    const b = build({ route: routes({ sd_public_shop: NOT_FOUND, sd_quote_requests: OK_EMPTY_ARR }) });
    await b.ctx.window.pcRenderPublicCatalog();
    ['pc-slug', 'pc-name', 'pc-phone', 'pc-email', 'pc-address', 'pc-blurb', 'pc-published', 'pc-save-shop']
      .forEach(id => assert.strictEqual(b.doc.els[id].disabled, true, id + ' was left enabled'));
  });

  await test('pcSaveShop REFUSES after a failed load, and sends no write at all', async () => {
    const b = build({ route: routes({ sd_public_shop: NOT_FOUND, sd_quote_requests: OK_EMPTY_ARR }) });
    await b.ctx.window.pcRenderPublicCatalog();
    b.calls.writes.length = 0;
    await b.ctx.window.pcSaveShop();
    assert.strictEqual(b.calls.writes.length, 0,
      'a live catalog was overwritten with the form the panel had filled in itself');
    assert.ok(/Not saving/.test(b.doc.els['pc-shop-status'].innerHTML));
  });

  await test('a shop that genuinely has no record STILL sees the first-run wording', async () => {
    const b = build({ route: routes({ sd_public_shop: OK_NULL, sd_quote_requests: OK_EMPTY_ARR }) });
    await b.ctx.window.pcRenderPublicCatalog();
    assert.strictEqual(b.probe().shopFailed, false);
    assert.ok(/No public address set yet/.test(b.doc.els['pc-shop-status'].innerHTML),
      'the real empty state was swallowed by the fix');
    assert.strictEqual(b.doc.els['pc-save-shop'].disabled, false, 'a first-run shop cannot save');
  });

  await test('a published shop reads back as live, and saving works', async () => {
    const shop = { shop_slug: 'main-street-stone', shop_name: 'Main Street Stone', published: true };
    const b = build({ route: routes({
      sd_public_shop: { status: 200, json: { ok: true, data: shop } },
      sd_quote_requests: OK_EMPTY_ARR
    }) });
    await b.ctx.window.pcRenderPublicCatalog();
    assert.strictEqual(b.probe().shopFailed, false);
    assert.ok(/Live at/.test(b.doc.els['pc-shop-status'].innerHTML));
    b.calls.writes.length = 0;
    await b.ctx.window.pcSaveShop();
    assert.strictEqual(b.calls.writes.length, 1, 'a healthy panel could not save');
  });

  await test('a 401 on the shop record is refused the same way -- signed out is not "no settings"', async () => {
    const b = build({ route: routes({ sd_public_shop: { status: 401, json: {} }, sd_quote_requests: OK_EMPTY_ARR }) });
    await b.ctx.window.pcRenderPublicCatalog();
    assert.strictEqual(b.probe().shopFailed, true);
    assert.strictEqual(b.doc.els['pc-save-shop'].disabled, true);
  });

  // ══ 3. quote requests ════════════════════════════════════════════════════
  section('quote requests: "none yet" is a claim about inbound business');

  await test('a failed read does not say "No quote requests yet"', async () => {
    const b = build({ route: routes({ sd_public_shop: OK_NULL, sd_quote_requests: NOT_FOUND }) });
    await b.ctx.window.pcRenderPublicCatalog();
    const tb = b.doc.els['pc-requests-tbody'].innerHTML;
    assert.ok(!/No quote requests yet/.test(tb), 'a dead table reported zero leads');
    assert.ok(/Could not load/.test(tb), 'row was: ' + tb);
  });

  await test('a genuinely empty list still says "No quote requests yet"', async () => {
    const b = build({ route: routes({ sd_public_shop: OK_NULL, sd_quote_requests: OK_EMPTY_ARR }) });
    await b.ctx.window.pcRenderPublicCatalog();
    assert.ok(/No quote requests yet/.test(b.doc.els['pc-requests-tbody'].innerHTML));
  });

  await test('real requests still render', async () => {
    const b = build({ route: routes({
      sd_public_shop: OK_NULL,
      sd_quote_requests: { status: 200, json: { ok: true, data: [
        { id: 'QR-1', name: 'A. Customer', status: 'pending', received_at: '2026-09-04' }] } }
    }) });
    await b.ctx.window.pcRenderPublicCatalog();
    assert.ok(/A. Customer/.test(b.doc.els['pc-requests-tbody'].innerHTML));
  });

  // ══ 4. tracking links ════════════════════════════════════════════════════
  section('tracking links: a shop that thinks it issued none cannot revoke one');

  await test('a failed list does not say "No tracking links issued yet"', async () => {
    const b = build({ route: body => body.resource
      ? (body.resource === 'sd_quote_requests' ? OK_EMPTY_ARR : OK_NULL)
      : { status: 500, json: { error: { message: 'nope' } } } });
    await b.ctx.window.pcRenderPublicCatalog();
    const tb = b.doc.els['pc-track-tbody'].innerHTML;
    assert.ok(!/No tracking links issued yet/.test(tb), 'a failed list reported zero links');
    assert.ok(/Could not load/.test(tb), 'row was: ' + tb);
    assert.strictEqual(b.probe().linkFailed, true);
  });

  await test('a genuinely empty list still says "No tracking links issued yet"', async () => {
    const b = build({ route: body => body.resource
      ? (body.resource === 'sd_quote_requests' ? OK_EMPTY_ARR : OK_NULL)
      : { status: 200, json: { ok: true, data: [] } } });
    await b.ctx.window.pcRenderPublicCatalog();
    assert.strictEqual(b.probe().linkFailed, false);
    assert.ok(/No tracking links issued yet/.test(b.doc.els['pc-track-tbody'].innerHTML));
  });

  await test('a real link still renders, and a 200 with ok:false counts as failed', async () => {
    const live = build({ route: body => body.resource
      ? (body.resource === 'sd_quote_requests' ? OK_EMPTY_ARR : OK_NULL)
      : { status: 200, json: { ok: true, data: [{ link_id: 'L1', job_id: 'C-9', active: true, created_at: '2026-09-04' }] } } });
    await live.ctx.window.pcRenderPublicCatalog();
    assert.ok(/C-9/.test(live.doc.els['pc-track-tbody'].innerHTML));

    const bad = build({ route: body => body.resource
      ? (body.resource === 'sd_quote_requests' ? OK_EMPTY_ARR : OK_NULL)
      : { status: 200, json: { ok: false } } });
    await bad.ctx.window.pcRenderPublicCatalog();
    assert.strictEqual(bad.probe().linkFailed, true, 'ok:false was read as an empty list');
  });

  // ══ 5. MUTATION: rebuild the original bug and prove it was a bug ═════════
  // The tests above show the fixed panel behaving. On their own they cannot
  // show that the GUARD is what produces that behaviour -- they would pass just
  // as happily against a panel that got the right answer by accident. So put the
  // two original lines back, in memory, and assert the defect reappears exactly
  // as it was reported. If this section ever stops reproducing it, the guard has
  // been made redundant by something else and this suite needs re-aiming, not
  // deleting.
  section('MUTATION: the pre-fix lines, restored, must reproduce the defect');

  const UNGUARD = src => {
    const out = src
      .replace("pcShopLoadFailed = !shop && pcReadFailed('sd_public_shop');",
               'pcShopLoadFailed = false;')
      .replace('pcShop = shop || null;',
               "pcShop = shop || {shop_slug:'',published:false};");
    assert.notStrictEqual(out, src,
      'neither pre-fix line was found -- the mutation is a no-op and this section is asserting nothing');
    return out;
  };

  await test('MUTANT: without the guard, a 404 really does say "No public address set yet"', async () => {
    const b = build({ mutate: UNGUARD, route: routes({ sd_public_shop: NOT_FOUND, sd_quote_requests: OK_EMPTY_ARR }) });
    await b.ctx.window.pcRenderPublicCatalog();
    assert.ok(/No public address set yet/.test(b.doc.els['pc-shop-status'].innerHTML),
      'the mutant did not reproduce the defect -- the guard is not what fixes it');
  });

  await test('MUTANT: without the guard, a live catalog IS blanked and Save DOES write', async () => {
    const b = build({ mutate: UNGUARD, route: routes({ sd_public_shop: NOT_FOUND, sd_quote_requests: OK_EMPTY_ARR }) });
    b.doc.els['pc-slug'].value = 'main-street-stone';
    b.doc.els['pc-published'].checked = true;
    await b.ctx.window.pcRenderPublicCatalog();
    assert.strictEqual(b.doc.els['pc-slug'].value, '', 'the mutant did not blank the form');
    assert.strictEqual(b.doc.els['pc-published'].checked, false, 'the mutant did not untick Publish');
    b.calls.writes.length = 0;
    await b.ctx.window.pcSaveShop();
    assert.strictEqual(b.calls.writes.length, 1, 'the mutant did not send the destructive write');
    // This is the write that would have gone to production: the real record
    // replaced by the form the panel had filled in itself.
    assert.strictEqual(b.calls.writes[0].payload.published, false);
    assert.strictEqual(b.calls.writes[0].payload.shop_slug, '');
  });

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  if (fail) process.exitCode = 1;
}

main();
