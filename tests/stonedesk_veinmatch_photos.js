// tests/stonedesk_veinmatch_photos.js
//
// Run:  node tests/stonedesk_veinmatch_photos.js
//
// VEIN MATCH ACCEPTS A REAL IMAGE NOW, AND THIS SUITE EXISTS BECAUSE THE
// INTERESTING FAILURES ARE ALL INVISIBLE IN A DIFF.
//
// Until 2026-09-26 the Vein Match panel had no image input of any kind --
// `type="file"` appeared zero times between its own <div> and the next panel's
// -- and sdVeinAnalyze() sent six text and number fields to /api/claude asking
// for "vein matching guidance". The 2026-09-02 worldwide competitive-gap audit's
// GAP 4 asserted that Vein Match "works from photos"; it did not, which
// docs/2026-09-26-gap-triage-four-verticals.md §4 corrected. This is step 1 of
// two: accepting an image AT ALL. Accepting a CALIBRATED one -- a scanner feed
// with known scale and a colour reference -- is step 2 and is not built.
//
// ── THE FOUR THINGS A DIFF CANNOT SEE, WHICH IS WHY EACH IS DRIVEN ────────
//
// (1) media_type. Every other image call in stonedesk.html hardcodes
//     'image/jpeg' -- eight of them -- while accepting `image/*`. A PNG sent as
//     image/jpeg produces a well-formed request, so the bug is SILENT. Arm 2c
//     uploads a PNG and asserts the outgoing block says image/png.
//
// (2) The cap, under real asynchrony. The change handler cannot count against
//     _veinPhotos.length, because FileReader is async and nothing has pushed yet
//     when the loop runs -- a six-file selection would read length 0 six times
//     and admit all six. THE FAKE FileReader HERE IS DEFERRED ON PURPOSE and
//     must be flushed, so a revert to the length check goes red in arm 3b. A
//     synchronous fake would pass either implementation, which would make this
//     arm worthless in the exact case it was written for.
//
// (3) The row's `photos` count on the FAILURE path. The fetch catch renders
//     generic canned guidance and always has. With photos attached, a row
//     reading photos:2 beside that fallback would be the log asserting an
//     analysis nobody ran. Arm 5b drives a rejected fetch and asserts 0.
//
// (4) That the bytes never reach storage. A 3MB photo is ~4MB of base64 and
//     this panel persists through st() to localStorage; writing the image would
//     fill the quota and take every other sd_* collection with it. Arm 4c
//     asserts the serialized value contains no base64 payload.
//
// Negative controls: set SD_HTML to a mutated copy. Arm 0 fails loudly if the
// block could not be located at all, so a rename cannot turn this suite green
// by making it test nothing.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const html = fs.readFileSync(process.env.SD_HTML
  || path.join(__dirname, '..', 'stonedesk.html'), 'utf8')
  .replace(/\r\n/g, '\n');

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
async function atest(name, fn) {
  try { await fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('\n' + t); }

// The markup belonging to one panel: its id to the next panel's. Bounded on
// purpose so a control in a neighbouring panel cannot be credited here -- which
// matters especially in this file, where panel-visualize sits immediately after
// panel-veinmatch and DOES have a photo input of its own.
function panelSlice(id) {
  const at = html.indexOf('id="panel-' + id + '"');
  assert.ok(at > 0, 'no panel-' + id + ' in stonedesk.html');
  const next = html.indexOf('id="panel-', at + 10);
  return html.slice(at, next === -1 ? at + 4000 : next);
}

function grab(sig, terminator) {
  const at = html.indexOf(sig);
  assert.ok(at > 0, 'not found in stonedesk.html: ' + JSON.stringify(sig.slice(0, 60)));
  const end = html.indexOf(terminator, at);
  assert.ok(end > at, 'terminator not found after ' + JSON.stringify(sig.slice(0, 60)));
  return html.slice(at, end + terminator.length);
}

console.log('StoneDesk -- Vein Match accepts real slab photos (step 1, uncalibrated)');

// ── 0. THE SUITE CAN FIND ITS SUBJECT ────────────────────────────────────
const VEIN_SIG = "(function(){\n  function load(){try{return JSON.parse(localStorage.getItem('sd_veinmatch')";
const VEIN_END = '\n  updateKPIs();\n})();';
let veinSrc = null;

section('0. the subject is located (a rename must not silently empty this suite)');
test('the Vein Match module is found and contains its own analyze function', () => {
  veinSrc = grab(VEIN_SIG, VEIN_END);
  assert.ok(veinSrc.length > 2000,
    'the located Vein Match block is only ' + veinSrc.length + ' chars -- the grab '
    + 'boundaries have drifted and every arm below would be testing a fragment');
  assert.ok(veinSrc.indexOf('window.sdVeinAnalyze=function(){') !== -1,
    'sdVeinAnalyze is not inside the located block');
  assert.ok(veinSrc.indexOf('vein-photo-input') !== -1,
    'the located block has no reference to vein-photo-input -- the photo feature '
    + 'is absent or lives outside this module');
});

// ── 1. THE MARKUP ────────────────────────────────────────────────────────
section('1. the input exists, in THIS panel, and declares real types');
test('panel-veinmatch has its own file input', () => {
  const s = panelSlice('veinmatch');
  assert.ok(s.indexOf('id="vein-photo-input"') !== -1,
    'no vein-photo-input inside panel-veinmatch. NOTE: panel-visualize next '
    + 'door has viz-file-input -- that is not this feature');
  assert.ok(/id="vein-photo-input"[^>]*\bmultiple\b/.test(s),
    'the input is not `multiple`, so a bookmatch pair cannot be attached at once');
});
test('accept names concrete types, not image/*', () => {
  const s = panelSlice('veinmatch');
  const m = s.match(/id="vein-photo-input"[^>]*accept="([^"]*)"/);
  assert.ok(m, 'vein-photo-input has no accept attribute');
  assert.strictEqual(m[1].indexOf('image/*'), -1,
    'accept is image/*, which admits HEIC and AVIF that the API image block '
    + 'cannot take -- and the refusal would then happen at the vendor, not here');
  ['image/jpeg', 'image/png', 'image/webp', 'image/gif'].forEach(t => {
    assert.ok(m[1].indexOf(t) !== -1, 'accept is missing ' + t);
  });
});
test('the panel does NOT hardcode image/jpeg anywhere', () => {
  const s = panelSlice('veinmatch');
  assert.strictEqual(s.indexOf("media_type:'image/jpeg'"), -1,
    "panel-veinmatch hardcodes media_type:'image/jpeg' -- the defect the other "
    + 'eight image call sites in this file carry');
});

// ── THE BEHAVIOURAL HALF ─────────────────────────────────────────────────
// A fake DOM, a DEFERRED FileReader, and a fetch whose body is captured.

function dataUrl(mime, body) { return 'data:' + mime + ';base64,' + body; }

function mkFile(name, type, size, body) {
  return { name: name, type: type, size: size, _url: dataUrl(type, body) };
}

function harness(opts) {
  opts = opts || {};
  const els = {};
  const toasts = [];
  const store = {};
  const readerQueue = [];
  const requests = [];

  function mk(id, kind) {
    const e = { id: id, value: '', textContent: '', innerHTML: '',
                style: {}, files: [], _listeners: {} };
    e.addEventListener = function (ev, fn) { (this._listeners[ev] = this._listeners[ev] || []).push(fn); };
    e.click = function () {};
    if (kind === 'select') e.value = '';
    els[id] = e;
    return e;
  }
  ['vein-proj', 'vein-stone', 'vein-style', 'vein-slabs', 'vein-sqft', 'vein-desc',
   'vein-out', 'vein-jobs', 'vein-match', 'vein-waste', 'vein-saved',
   'vein-saved-list', 'vein-photo-input', 'vein-photo-strip', 'vein-photo-status',
  ].forEach(id => mk(id));
  els['vein-proj'].value = 'Hilltop Kitchen';
  els['vein-stone'].value = 'Calacatta Gold Marble';
  els['vein-style'].value = 'Bookmatch (mirror)';
  els['vein-slabs'].value = '2';
  els['vein-sqft'].value = '84';
  els['vein-desc'].value = 'strong diagonal veining';

  // DEFERRED ON PURPOSE. See header note (2).
  function FakeFileReader() { this.onload = null; this.onerror = null; }
  FakeFileReader.prototype.readAsDataURL = function (f) {
    const self = this;
    readerQueue.push(function () {
      if (f._fail) { if (self.onerror) self.onerror(); return; }
      if (self.onload) self.onload({ target: { result: f._url } });
    });
  };

  const ctx = {
    document: {
      getElementById: id => els[id] || null,
      createElement: () => ({ style: {}, click() {}, setAttribute() {} }),
    },
    window: {},
    localStorage: {
      getItem: k => (k in store ? store[k] : null),
      setItem: (k, v) => { store[k] = String(v); },
      removeItem: k => { delete store[k]; },
    },
    FileReader: FakeFileReader,
    showToast: m => toasts.push(String(m)),
    confirm: () => true,
    // st() is the app's real storage writer. Stubbed to the same contract:
    // serialize, write, return whether it stuck.
    st: (k, d) => { store[k] = JSON.stringify(d); return true; },
    sdEnsureRowIds: (d, pfx, keys) => {
      let changed = false;
      d.forEach((r, i) => {
        if (!r.id) { r.id = pfx + '-' + keys.map(k => String(r[k] || '')).join('-') + '-' + i; changed = true; }
      });
      return changed;
    },
    escHtml: v => String(v == null ? '' : v).replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;'),
    escAttrJs: v => String(v == null ? '' : v),
    sdLocalToday: () => '2026-09-26',
    sdCsvCell: v => String(v == null ? '' : v),
    sdShopSlug: () => 'testshop',
    sdShopName: () => 'Test Shop',
    sdThemeColor: () => '#1B3A6B',
    encodeURIComponent: encodeURIComponent,
    fetch: (url, init) => {
      requests.push({ url: url, body: JSON.parse(init.body) });
      if (opts.reject) return Promise.reject(new Error('network down'));
      return Promise.resolve({ json: () => Promise.resolve(
        opts.payload || { content: [{ text: 'ORIENTATION: flow front-bottom to back-top.' }] }) });
    },
    console: { log() {}, warn() {}, error() {} },
    setTimeout: (fn) => { fn(); return 0; },
    Object, Array, String, Number, Boolean, JSON, Math, RegExp, Set, Date, Promise, Error,
  };
  ctx.globalThis = ctx;
  vm.createContext(ctx);
  vm.runInContext(veinSrc, ctx, { filename: 'veinmatch-module' });

  return {
    ctx, els, toasts, store, requests,
    // Fires the change handler the module registered on the real input id.
    pick(files) {
      const input = els['vein-photo-input'];
      input.files = files;
      const ls = input._listeners.change || [];
      assert.ok(ls.length, 'the module registered no change listener on vein-photo-input');
      ls.forEach(fn => fn.call(input));
    },
    flushReaders() {
      while (readerQueue.length) readerQueue.shift()();
    },
    rows() { return store.sd_veinmatch ? JSON.parse(store.sd_veinmatch) : []; },
  };
}

const JPG = () => mkFile('slab-a.jpg', 'image/jpeg', 1024, 'QUFBQQ==');
const PNG = () => mkFile('slab-b.png', 'image/png', 2048, 'QkJCQg==');

async function main() {
  section('2. a real image is accepted, and its OWN type travels with it');

  await atest('2a. a JPEG is attached and previewed', async () => {
    const h = harness();
    h.pick([JPG()]);
    h.flushReaders();
    assert.ok(/photo-thumb/.test(h.els['vein-photo-strip'].innerHTML),
      'no thumbnail was rendered for an accepted photo');
    assert.ok(/1 photo attached/.test(h.els['vein-photo-status'].textContent),
      'the status line does not say one photo is attached: '
      + JSON.stringify(h.els['vein-photo-status'].textContent));
  });

  await atest('2b. with no photos the request body is a plain STRING (no regression)', async () => {
    const h = harness();
    await h.ctx.window.sdVeinAnalyze();
    assert.strictEqual(h.requests.length, 1, 'expected exactly one /api/claude call');
    const content = h.requests[0].body.messages[0].content;
    assert.strictEqual(typeof content, 'string',
      'with no photos attached the content should stay the original string form, got '
      + (Array.isArray(content) ? 'an array' : typeof content));
    assert.ok(/vein matching guidance/.test(content),
      'the text-only prompt lost its original wording');
  });

  await atest('2c. a PNG is sent as image/png, NOT image/jpeg', async () => {
    const h = harness();
    h.pick([PNG()]);
    h.flushReaders();
    await h.ctx.window.sdVeinAnalyze();
    const content = h.requests[0].body.messages[0].content;
    assert.ok(Array.isArray(content), 'content is not an array of blocks');
    const img = content.filter(b => b.type === 'image');
    assert.strictEqual(img.length, 1, 'expected one image block, got ' + img.length);
    assert.strictEqual(img[0].source.media_type, 'image/png',
      'a PNG was declared as ' + img[0].source.media_type
      + ' -- this is the silent defect the other eight call sites carry');
    assert.strictEqual(img[0].source.data, 'QkJCQg==',
      'the base64 payload is not the file body, or the data: prefix was not stripped');
  });

  await atest('2d. images come FIRST and the text block LAST', async () => {
    const h = harness();
    h.pick([JPG(), PNG()]);
    h.flushReaders();
    await h.ctx.window.sdVeinAnalyze();
    const content = h.requests[0].body.messages[0].content;
    assert.deepStrictEqual(content.map(b => b.type), ['image', 'image', 'text'],
      'block order is ' + JSON.stringify(content.map(b => b.type)));
  });

  await atest('2e. the prompt FORBIDS a measurement, because the input cannot support one', async () => {
    const h = harness();
    h.pick([JPG()]);
    h.flushReaders();
    await h.ctx.window.sdVeinAnalyze();
    const txt = h.requests[0].body.messages[0].content.filter(b => b.type === 'text')[0].text;
    assert.ok(/NO scale reference/i.test(txt) && /NO colour target|NO color target/i.test(txt),
      'the prompt does not tell the model the photos are uncalibrated -- step 2 is '
      + 'not built, so anything dimensional read off these is fabricated');
    assert.ok(/do not give a numeric match score/i.test(txt),
      'the prompt does not forbid a numeric match score. The orphaned vmAnalyze() '
      + 'in this same file regexes a score out of prose and DEFAULTS TO 5 when the '
      + 'regex misses; this panel must not reintroduce that');
  });

  section('3. every refusal is named, and the cap holds under real asynchrony');

  await atest('3a. an unsupported type is refused BY NAME and not attached', async () => {
    const h = harness();
    h.pick([mkFile('IMG_4021.heic', 'image/heic', 900, 'SEVJQw==')]);
    h.flushReaders();
    assert.ok(h.toasts.some(t => /unsupported image type/i.test(t) && /IMG_4021\.heic/.test(t)),
      'no toast named the refused file: ' + JSON.stringify(h.toasts));
    assert.strictEqual(h.els['vein-photo-strip'].innerHTML, '',
      'a HEIC was attached anyway');
  });

  await atest('3b. THE CAP: five files attach four and the fifth is reported', async () => {
    const h = harness();
    h.pick([JPG(), JPG(), JPG(), JPG(), JPG()]);
    h.flushReaders();
    const thumbs = (h.els['vein-photo-strip'].innerHTML.match(/photo-thumb"/g) || []).length;
    assert.strictEqual(thumbs, 4,
      'expected 4 attached, got ' + thumbs + '. If this reads 5, the handler is '
      + 'counting against _veinPhotos.length, which is still 0 during the loop '
      + 'because FileReader is asynchronous');
    assert.ok(h.toasts.some(t => /limit is 4/.test(t)),
      'the over-cap file was dropped silently: ' + JSON.stringify(h.toasts));
  });

  await atest('3c. an over-8MB file is refused by name', async () => {
    const h = harness();
    h.pick([mkFile('huge.jpg', 'image/jpeg', 9 * 1024 * 1024, 'QQ==')]);
    h.flushReaders();
    assert.ok(h.toasts.some(t => /over 8MB/.test(t) && /huge\.jpg/.test(t)),
      'the oversize file was not named: ' + JSON.stringify(h.toasts));
    assert.strictEqual(h.els['vein-photo-strip'].innerHTML, '');
  });

  await atest('3d. a read ERROR says so rather than attaching nothing quietly', async () => {
    const h = harness();
    const f = JPG(); f._fail = true;
    h.pick([f]);
    h.flushReaders();
    assert.ok(h.toasts.some(t => /Could not read/.test(t)),
      'a FileReader error produced no message: ' + JSON.stringify(h.toasts));
  });

  await atest('3e. a photo can be removed again', async () => {
    const h = harness();
    h.pick([JPG(), PNG()]);
    h.flushReaders();
    h.ctx.window.sdVeinPhotoRemove(0);
    const thumbs = (h.els['vein-photo-strip'].innerHTML.match(/photo-thumb"/g) || []).length;
    assert.strictEqual(thumbs, 1, 'remove did not drop exactly one photo');
    await h.ctx.window.sdVeinAnalyze();
    const img = h.requests[0].body.messages[0].content.filter(b => b.type === 'image');
    assert.strictEqual(img[0].source.media_type, 'image/png',
      'the removed photo is the one still being sent');
  });

  section('4. the log records the COUNT and never the bytes');

  await atest('4a. a successful photo analysis records photos:2', async () => {
    const h = harness();
    h.pick([JPG(), PNG()]);
    h.flushReaders();
    await h.ctx.window.sdVeinAnalyze();
    const rows = h.rows();
    assert.strictEqual(rows.length, 1, 'expected one saved row, got ' + rows.length);
    assert.strictEqual(rows[0].photos, 2, 'photos recorded as ' + rows[0].photos);
  });

  await atest('4b. a text-only analysis records photos:0', async () => {
    const h = harness();
    await h.ctx.window.sdVeinAnalyze();
    assert.strictEqual(h.rows()[0].photos, 0);
  });

  await atest('4c. NO base64 reaches storage', async () => {
    const h = harness();
    h.pick([JPG(), PNG()]);
    h.flushReaders();
    await h.ctx.window.sdVeinAnalyze();
    const raw = h.store.sd_veinmatch || '';
    ['QUFBQQ==', 'QkJCQg==', 'data:image'].forEach(needle => {
      assert.strictEqual(raw.indexOf(needle), -1,
        'the stored row contains ' + needle + ' -- the image bytes are being '
        + 'persisted, which fills the localStorage quota and takes every other '
        + 'sd_* collection down with it');
    });
  });

  await atest('4d. the CSV carries Photos Read, and a pre-2026-09-26 row exports BLANK not 0', async () => {
    const h = harness();
    // A legacy row: written before `photos` existed, so the field is absent.
    h.store.sd_veinmatch = JSON.stringify([{ id: 'VM-old', proj: 'Old Job', stone: 'Statuario Marble', style: 'Sequential flow', date: '2026-09-01' }]);
    let href = '';
    h.ctx.document.createElement = () => ({ style: {}, click() {}, set href(v) { href = v; }, get href() { return href; } });
    h.ctx.window.sdVeinExport();
    const csv = decodeURIComponent(href.replace('data:text/csv;charset=utf-8,', ''));
    const lines = csv.split('\n');
    assert.ok(/Photos Read/.test(lines[0]), 'the header has no Photos Read column: ' + lines[0]);
    const cells = lines[1].split(',');
    assert.strictEqual(cells[cells.length - 1], '',
      'a row with no `photos` key exported as ' + JSON.stringify(cells[cells.length - 1])
      + ' -- absent and zero are different answers and only one was measured');
  });

  section('5. the failure path does not inherit the photos\' credit');

  await atest('5a. a rejected fetch says the photos were NOT looked at', async () => {
    const h = harness({ reject: true });
    h.pick([JPG(), PNG()]);
    h.flushReaders();
    await h.ctx.window.sdVeinAnalyze();
    const out = h.els['vein-out'].innerHTML;
    assert.ok(/NOT LOOKED AT/.test(out),
      'the fallback renders generic guidance without saying the photos were '
      + 'never read, so an operator reads it as an assessment of their slabs:\n'
      + out.slice(0, 400));
  });

  await atest('5b. ...and records photos:0, not the attached count', async () => {
    const h = harness({ reject: true });
    h.pick([JPG(), PNG()]);
    h.flushReaders();
    await h.ctx.window.sdVeinAnalyze();
    assert.strictEqual(h.rows()[0].photos, 0,
      'the row claims ' + h.rows()[0].photos + ' photos were read on a run where '
      + 'the request failed and the canned fallback was shown');
  });

  await atest('5c. a SUCCESSFUL photo run labels the output as not-a-measurement', async () => {
    const h = harness();
    h.pick([JPG()]);
    h.flushReaders();
    await h.ctx.window.sdVeinAnalyze();
    const out = h.els['vein-out'].innerHTML;
    assert.ok(/Read 1 slab photo/.test(out), 'the output does not say what it read: ' + out.slice(0, 300));
    assert.ok(/Not a measurement/i.test(out),
      'the output does not disclaim measurement, and step 2 (calibrated input) is not built');
  });

  section('6. the three fabricated KPIs stay neutralised');

  await atest('6a. Match Quality / Waste Reduction / Material Savings still read --', async () => {
    const h = harness();
    h.pick([JPG()]);
    h.flushReaders();
    await h.ctx.window.sdVeinAnalyze();
    ['vein-match', 'vein-waste', 'vein-saved'].forEach(id => {
      assert.strictEqual(h.els[id].textContent, '--',
        id + ' reads ' + JSON.stringify(h.els[id].textContent)
        + ' -- accepting a photo must not become a licence to compute these. '
        + 'They were set to -- because nothing measures them.');
    });
    assert.strictEqual(h.els['vein-jobs'].textContent, 1,
      'Layouts Analyzed is a real count and should have moved to 1');
  });

  console.log('\n' + (fail ? 'FAIL' : 'ALL')
    + ' -- ' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
}

main().catch(e => { console.error('HARNESS ERROR: ' + e.stack); process.exit(1); });
