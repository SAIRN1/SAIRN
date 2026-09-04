// tests/stonedesk_saved_drawings.js
//
// Run:  node tests/stonedesk_saved_drawings.js
//
// The Saved Drawings list, driven verbatim from stonedesk.html.
//
// WHY IT EXISTS. sdDrawSave() had written up to fifty canvas snapshots to
// sd_drawings since 2026-08-13 and NOTHING in the repo read them back -- no
// list, no viewer, no consumer of any kind. A rep could save a drawing and
// never see it again. Found while measuring that store's quota cost; Michael's
// call was to build the missing half rather than delete the feature.
//
// THE DESIGN DECISION THAT MATTERS, and it is a correctness one rather than a
// UI one: until today the store held a PICTURE and nothing else. "Reload a
// saved drawing" against that could only have meant painting a raster onto a
// canvas whose model still described something else -- the shape, the
// dimensions and the cutouts would all be whatever the rep had on screen, and
// the first recalculation would contradict the image. That is the
// displayed-versus-wired trap this platform has recorded more than once. So
// the save now also stores dcSnapshotDrawingState(), the same snapshot the
// quote history already keeps, and the loader goes through the same
// dcLoadDrawingState().
//
// Entries written before that change have a picture and no state. They are
// shown, labelled, and their Load button is disabled -- rather than hidden,
// which would read as data loss, or enabled and silently doing nothing.

'use strict';
const fs = require('fs');
const path = require('path');

const HTML = path.join(__dirname, '..', 'stonedesk.html');
const src = fs.readFileSync(HTML, 'utf8');

let pass = 0, fail = 0;
function check(name, actual, expected) {
  const a = JSON.stringify(actual), e = JSON.stringify(expected);
  if (a === e) { pass++; return; }
  fail++;
  console.log('FAIL  ' + name + '\n        expected ' + e + '\n        actual   ' + a);
}

function balanced(start) {
  let i = src.indexOf('{', start), depth = 0;
  for (; i < src.length; i++) {
    if (src[i] === '{') depth++;
    else if (src[i] === '}') { depth--; if (!depth) return src.slice(start, i + 1); }
  }
  throw new Error('unbalanced from ' + start);
}
function fn(decl) {
  const i = src.indexOf(decl);
  if (i < 0) throw new Error('not found: ' + decl);
  return balanced(i);
}

const STATE = { schemaVersion: 1, ctShape: 'ushape', dcPoly: [] };
const WITH_STATE = { id: 'DRW-2', date: '2026-09-04', name: 'Hartley kitchen', dataUrl: 'data:image/jpeg;base64,AAAA', drawingState: STATE };
const LEGACY = { id: 'DRW-1', date: '2026-08-20', name: 'Older job', dataUrl: 'data:image/png;base64,BBBB' };

// ── the list ──────────────────────────────────────────────────────────────
function renderWith(rows) {
  const data = { sd_drawings: JSON.stringify(rows) };
  const els = { 'sd-drawings-body': { innerHTML: '' } };
  new Function('localStorage', 'document', 'escHtml',
    fn('function sdDrawingsAll(){') + '\n' +
    fn('function sdDrawingsRender(){') + '\n' +
    'sdDrawingsRender();'
  )(
    { getItem: (k) => (k in data ? data[k] : null) },
    { getElementById: (id) => els[id] || null },
    (s) => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
  );
  return els['sd-drawings-body'].innerHTML;
}

{
  const html = renderWith([]);
  check('an empty store gets a real empty state, not a blank panel',
    /No saved drawings yet/.test(html), true);
  check('and it says what to do about it, naming the button',
    /Save Drawing/.test(html), true);
  check('with no Load button to click', /Load onto Canvas/.test(html), false);
}
{
  const html = renderWith([WITH_STATE]);
  check('a saved drawing shows its own snapshot, so the rep recognises it '
    + 'rather than picking a date out of a list',
    /<img src="data:image\/jpeg;base64,AAAA"/.test(html), true);
  check('with its name', /Hartley kitchen/.test(html), true);
  check('and its date', /2026-09-04/.test(html), true);
  check('and an enabled Load button wired to its id',
    /onclick="sdDrawingsLoad\('DRW-2'\)"/.test(html), true);
  check('not a disabled one', /disabled/.test(html), false);
}
{
  // The pre-2026-09-04 entry. Shown and labelled, never silently dropped.
  const html = renderWith([LEGACY]);
  check('a picture-only entry is still listed', /Older job/.test(html), true);
  check('its Load button is disabled', /disabled/.test(html), true);
  check('and the row says WHY, in words a rep can act on',
    /can be viewed but not reloaded/.test(html), true);
  check('so nothing offers to load it', /sdDrawingsLoad\(/.test(html), false);
}
{
  const html = renderWith([WITH_STATE, LEGACY]);
  check('a mixed list keeps both, in order',
    html.indexOf('Hartley kitchen') < html.indexOf('Older job'), true);
  check('with exactly one enabled Load',
    (html.match(/onclick="sdDrawingsLoad\(/g) || []).length, 1);
}
{
  // A name with markup in it must not become markup.
  const html = renderWith([Object.assign({}, WITH_STATE, { name: '<img src=x onerror=1>' })]);
  check('a job name is escaped, not rendered',
    /&lt;img src=x/.test(html) && !/<img src=x onerror/.test(html), true);
}
{
  const html = renderWith([{ id: 'DRW-3', date: '2026-09-04', name: 'No picture', drawingState: STATE }]);
  check('an entry whose image failed to encode still lists and still loads',
    /No image/.test(html) && /onclick="sdDrawingsLoad\('DRW-3'\)"/.test(html), true);
}

// ── the loader ────────────────────────────────────────────────────────────
function loadWith(rows, id, opts) {
  opts = opts || {};
  const data = { sd_drawings: JSON.stringify(rows) };
  const calls = { confirm: 0, loaded: 0, toasts: [], closed: 0, nav: 0 };
  const els = { 'sd-drawings-modal': { classList: { remove() { calls.closed++; }, add() {} } } };
  new Function('localStorage', 'document', 'showToast', 'confirm', 'sbNav',
    'dcLoadDrawingState', 'dcHasUnsavedWork', 'window',
    fn('function sdDrawingsAll(){') + '\n' +
    fn('window.sdDrawingsLoad=function(id){').replace(/^/, 'var __l = ') + ';\n' +
    '__l(' + JSON.stringify(id) + ');'
  )(
    { getItem: (k) => (k in data ? data[k] : null) },
    { getElementById: (i) => els[i] || null },
    (m) => calls.toasts.push(String(m)),
    () => { calls.confirm++; return !!opts.userSaysYes; },
    () => { calls.nav++; },
    () => { calls.loaded++; return opts.loadFails ? false : true; },
    () => !!opts.unsaved,
    {}
  );
  return calls;
}

{
  const c = loadWith([WITH_STATE], 'DRW-2', {});
  check('loading a stored drawing goes through dcLoadDrawingState',
    [c.loaded, c.confirm], [1, 0]);
  check('the modal closes and the Drawing Tool is brought forward',
    [c.closed, c.nav], [1, 1]);
  check('and the rep is told which drawing landed',
    c.toasts, ['Loaded: Hartley kitchen']);
}
{
  const c = loadWith([WITH_STATE], 'DRW-2', { unsaved: true, userSaysYes: false });
  check('unsaved work on the canvas warns first', c.confirm, 1);
  check('and declining loads nothing at all',
    [c.loaded, c.closed, c.nav], [0, 0, 0]);
}
{
  const c = loadWith([WITH_STATE], 'DRW-2', { unsaved: true, userSaysYes: true });
  check('accepting the warning proceeds', [c.confirm, c.loaded], [1, 1]);
}
{
  const c = loadWith([LEGACY], 'DRW-1', {});
  check('a picture-only entry refuses rather than half-loading', c.loaded, 0);
  check('and says why', /no stored measurements/.test(c.toasts[0] || ''), true);
}
{
  const c = loadWith([WITH_STATE], 'DRW-NOPE', {});
  check('an id that is not in the store refuses', c.loaded, 0);
}
{
  const c = loadWith([Object.assign({}, WITH_STATE, { drawingState: { schemaVersion: 2 } })], 'DRW-2', {});
  check('a snapshot from a schema this build does not know is refused, not '
    + 'guessed at', c.loaded, 0);
}
{
  // dcLoadDrawingState returns false on a malformed snapshot. Reporting that
  // is the difference between a failed load and a click that did nothing.
  const c = loadWith([WITH_STATE], 'DRW-2', { loadFails: true });
  check('a load that fails inside the engine is reported',
    /Could not load that drawing/.test(c.toasts[0] || ''), true);
}

// ── the save side, which is what makes any of this real ───────────────────
{
  const save = fn('window.sdDrawSave=function(){')
    .split('\n').filter((l) => !l.trim().startsWith('//')).join('\n');
  check('the save stores the drawing STATE, not only the picture',
    /entry\.drawingState = dcSnapshotDrawingState\(\);/.test(save), true);
  check('using the same snapshot function the quote history uses',
    (src.match(/dcSnapshotDrawingState\(\)/g) || []).length >= 2, true);
  check('and it is guarded, so a snapshot failure costs the reload and not '
    + 'the save', /try\{ entry\.drawingState = dcSnapshotDrawingState\(\); \}catch\(e\)\{\}/.test(save), true);
  check('the toolbar has an entry point',
    /onclick="sdDrawingsOpen\(\)"/.test(src), true);
  check('and the modal it opens exists',
    /id="sd-drawings-modal"/.test(src) && /id="sd-drawings-body"/.test(src), true);
}

console.log((fail ? 'FAILED' : 'ok') + '  stonedesk-saved-drawings: ' +
  pass + ' passed, ' + fail + ' failed');
if (fail) process.exit(1);
