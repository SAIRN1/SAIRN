// tests/stonedesk_quote_load_state.js
//
// Run:  node tests/stonedesk_quote_load_state.js
//
// The two open-work rows about loading a saved quote into the Drawing Tool,
// driven verbatim from stonedesk.html.
//
// DEFECT 1 -- the overwrite confirm fired on a merely-opened tab. The gate
// asked `gN('da-len') > 0 || gN('da-dep') > 0`. initDrawPanel() calls
// selectDrawShape('straight'), which WRITES 96 and 25.5 into exactly those
// boxes, so the test was true before the rep had touched anything. Loading a
// quote into a freshly-opened tab asked "this will replace your current
// drawing - continue?" about a drawing that did not exist. The cost is not
// the click: it is that a confirm which appears when there is nothing to lose
// teaches a rep to dismiss confirms without reading them, and the next one
// will be real.
//
// The fix is not "drop the dimension check" -- that would silently discard a
// rep's typed dimensions on a preset with no polygon, which is the case the
// old test was reaching for. dcDimsEdited() compares each box against the
// value THIS shape wrote, captured as it was written rather than re-listed,
// because the defaults live inline in selectDrawShape()'s if/else chain and a
// second copy would drift the first time one changed.
//
// DEFECT 2 -- dcMode was restored in one direction only:
//
//     if (state.dcMode === 'draw' && ...) setDCMode('draw');
//
// Loading a PRESET quote while the session was in draw mode left dcMode as
// 'draw' with the freshly-restored dcPoly empty. drawCTPreview() dispatches
// on dcMode, so the canvas rendered the polygon view -- of nothing -- instead
// of the preset rectangle. Pricing was unaffected, because isCustom also
// requires dcPolyClosed and that was false, which is exactly why it read as a
// display glitch rather than the state bug it is.

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

// ── dcDimsEdited(), driven for real ───────────────────────────────────────
function dims(defaults, current) {
  return new Function('gN', 'dcPresetDefaults',
    fn('function dcDimsEdited() {') + '\nreturn dcDimsEdited;'
  )((id) => (id in current ? current[id] : 0), defaults);
}

const STRAIGHT = { 'da-len': 96, 'da-dep': 25.5 };

check('a freshly-opened tab, still holding the shape defaults, is NOT edited',
  dims(STRAIGHT, { 'da-len': 96, 'da-dep': 25.5 })(), false);
check('a length the rep changed IS edited',
  dims(STRAIGHT, { 'da-len': 120, 'da-dep': 25.5 })(), true);
check('a depth the rep changed IS edited',
  dims(STRAIGHT, { 'da-len': 96, 'da-dep': 22.5 })(), true);
check('a box the rep CLEARED is edited too -- deleting a default is an edit',
  dims(STRAIGHT, { 'da-len': 0, 'da-dep': 25.5 })(), true);
check('before any shape has been built there is nothing to have edited',
  dims({}, {})(), false);
// A shape whose defaults are 0 must not read as edited just for being empty.
check('zero-default sections sitting empty are not edits',
  dims({ 'da-len': 96, 'da-dep': 25.5, 'db-len': 0, 'db-dep': 0 },
       { 'da-len': 96, 'da-dep': 25.5 })(), false);

// ── the confirm gate, driven through the real handler ─────────────────────
function loader(opts) {
  const calls = { confirm: 0, loaded: 0, toast: 0 };
  const state = { schemaVersion: 1, dcMode: 'preset' };
  const quote = { id: 'q1', drawingState: state };
  const els = {
    'sd-history-detail-modal': { classList: { remove() {}, add() {} } }
  };
  // The REAL shared guard, built from source with the drawing globals
  // injected -- so this drives dcHasUnsavedWork() rather than a stand-in for
  // it. That matters more since 2026-09-04, when the guard moved out of this
  // handler so the Saved Drawings loader could use the same one.
  const dcHasUnsavedWork = new Function(
    'dcPoly', 'dcCutouts', 'dcSeams', 'dcRaisedBar', 'dcChamferedCorners', 'dcDimsEdited',
    fn('function dcHasUnsavedWork() {') + '\nreturn dcHasUnsavedWork;'
  )(
    opts.dcPoly || [], opts.dcCutouts || [], opts.dcSeams || [],
    opts.dcRaisedBar || null, opts.dcChamferedCorners || {},
    () => !!opts.dimsEdited
  );

  const api = new Function(
    'sdHistoryDetailOpenId', 'load', 'dcHasUnsavedWork', 'confirm',
    'document', 'sbNav', 'dcLoadDrawingState', 'showToast', 'window',
    fn('window.sdHistoryLoadIntoDrawingTool=function(){').replace(/^/, 'var __h = ') + ';\n' +
    'return __h;'
  )(
    'q1', () => [quote],
    dcHasUnsavedWork,
    () => { calls.confirm++; return !!opts.userSaysYes; },
    { getElementById: (id) => els[id] || null },
    () => {},
    () => { calls.loaded++; return true; },
    () => { calls.toast++; },
    {}
  );
  api();
  return calls;
}

check('an untouched tab loads with NO confirm -- the reported bug',
  loader({}), { confirm: 0, loaded: 1, toast: 0 });
check('a rep who typed real dimensions IS warned',
  loader({ dimsEdited: true, userSaysYes: true }), { confirm: 1, loaded: 1, toast: 0 });
check('and declining that warning loads nothing',
  loader({ dimsEdited: true, userSaysYes: false }), { confirm: 1, loaded: 0, toast: 0 });
check('an in-progress polygon still warns, dimensions untouched or not',
  loader({ dcPoly: [{ x: 0, y: 0 }], userSaysYes: true }),
  { confirm: 1, loaded: 1, toast: 0 });
check('so does a placed cutout',
  loader({ dcCutouts: [{ label: 'Sink' }], userSaysYes: true }),
  { confirm: 1, loaded: 1, toast: 0 });
check('so does a raised bar',
  loader({ dcRaisedBar: { len: 40 }, userSaysYes: true }),
  { confirm: 1, loaded: 1, toast: 0 });
check('so does a chamfered corner',
  loader({ dcChamferedCorners: { 0: 3 }, userSaysYes: true }),
  { confirm: 1, loaded: 1, toast: 0 });

// ── the two source-level properties, which no stub can hold ───────────────
{
  const load = fn('function dcLoadDrawingState(');
  check('the load path restores dcMode in BOTH directions',
    /setDCMode\(state\.dcMode \|\| 'preset'\)/.test(load), true);
  check('and no longer sets draw mode only',
    /state\.dcMode === 'draw' && typeof setDCMode/.test(load), false);

  const shape = fn('function selectDrawShape(id) {');
  check('the shape builder records the defaults it writes, both field kinds',
    (shape.match(/dcPresetDefaults\[id\] = def \|\| 0;/g) || []).length, 2);
  check('and clears them first, so they cannot describe a previous shape',
    /dcPresetDefaults = \{\};/.test(shape), true);

  // Comments stripped first. The fix's own comment quotes the old expression
  // verbatim, which is worth keeping and would otherwise make this assertion
  // fail on the very change it is checking -- the same trap as a scanner
  // re-flagging a fix because the fix explains what it replaced.
  const gate = fn('window.sdHistoryLoadIntoDrawingTool=function(){')
    .split('\n').filter((l) => !l.trim().startsWith('//')).join('\n');
  check('the confirm gate no longer reads the raw boxes',
    /gN\('da-len'\) > 0 \|\| gN\('da-dep'\) > 0/.test(gate), false);
  check('it defers to the shared guard instead of inlining the test',
    /dcHasUnsavedWork\(\)/.test(gate), true);
  // ONE definition, used by both loaders. Two copies of a guard drift, and
  // the half that drifts is the half that stops warning.
  const guard = fn('function dcHasUnsavedWork() {');
  check('the shared guard is the thing that asks about edited dimensions',
    /dcDimsEdited\(\)/.test(guard), true);
  const drawingsLoad = fn('window.sdDrawingsLoad=function(id){')
    .split('\n').filter((l) => !l.trim().startsWith('//')).join('\n');
  check('and the Saved Drawings loader calls the SAME guard, not a copy',
    /dcHasUnsavedWork\(\)/.test(drawingsLoad), true);
  check('there is exactly one definition of it in the file',
    (src.match(/function dcHasUnsavedWork\(\)/g) || []).length, 1);
}

console.log((fail ? 'FAILED' : 'ok') + '  stonedesk-quote-load-state: ' +
  pass + ' passed, ' + fail + ' failed');
if (fail) process.exit(1);
