# StoneDesk Saved Quote History: Drawing Tool State Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `sdQuoteSaveHistory()` capture the Drawing Tool's full state (shape, dimensions, cutouts, seams, chamfers, raised bar, job details) alongside the flat dollar total it already saves, and let a rep reopen a saved quote from the History panel to see a real itemized breakdown and, on demand, fully re-load it back into the live Drawing Tool to keep editing.

**Architecture:** Two new mirror-image functions in `stonedesk.html`'s drawing-tool script region — `dcSnapshotDrawingState()` (capture) and `dcLoadDrawingState()` (restore) — sharing one set of field-list constants so the two can never drift apart. `sdQuoteSaveHistory()` gets one new line calling the capture function. `sdHistoryView()` (currently a toast stub) becomes a real modal showing the saved detail, with a "Load into Drawing Tool" button gated by an unsaved-work confirm and disabled for quotes saved before this ships.

**Tech Stack:** Vanilla JS, single `<script>` block regions inside `stonedesk.html`. No dependencies, no build step, no server changes.

## Global Constraints

- `node --check` must pass on every touched script block before any commit — run `python tools/checkblocks.py stonedesk.html` and confirm `FAILED_BLOCKS:0` (baseline before this plan: `TOTAL_BLOCKS:128`, `FAILED_BLOCKS:0`).
- Never bulk find-replace. Every edit below is a targeted, unique-context change.
- Storage: `drawingState` is a new field on the *existing* `sd_quote_history` entry (localStorage key unchanged). No second localStorage key.
- The dimension/extras/job-detail field-id lists (`DC_STATE_DIM_FIELDS`, `DC_STATE_EXTRAS_CB_FIELDS`, `DC_STATE_EXTRAS_NUM_FIELDS`, `DC_STATE_JOB_TEXT_FIELDS`, `DC_STATE_JOB_SELECT_FIELDS`) are defined exactly once and consumed by both `dcSnapshotDrawingState()` and `dcLoadDrawingState()` — never duplicated as a second literal list.
- `dcSnapshotDrawingState()`'s `summary` strings are built from the exact same formulas `printDrawCutSheet()` already uses (seam LF, chamfer setback, raised-bar dims, cutout labels) — computed once at save time against live globals, not re-derived later against an inert stored snapshot. This is a deliberate refinement of the design spec's "reuse the existing label-building logic" requirement: `printDrawCutSheet()`'s logic is inline inside a `win.document.write()` chain operating on live DOM/globals, not a callable helper that can run against an arbitrary past snapshot, so the summary is captured once, correctly, while the data is still live.
- All new user-facing strings written into the History modal via `innerHTML` go through the existing `escHtml()` helper (`stonedesk.html:1765`) — matches this session's own adversarial-review fix on `printDrawCutSheet()`.
- Both new functions (`dcSnapshotDrawingState`, `dcLoadDrawingState`) are wrapped in `try/catch` and degrade to `null`/`false` on any error — a malformed snapshot must never break Save or break the History panel's render.
- `dcLoadDrawingState()` must not duplicate `selectDrawShape()`'s shape-dependent DOM-rebuild logic (the dimension-input creation in particular) — it calls the real `selectDrawShape()` to get fresh, correctly-shaped inputs, then overwrites their values with the snapshot's real data.
- Load into Drawing Tool must confirm before overwriting real unsaved canvas content (non-empty `dcPoly`, non-blank shape dimensions, or any non-empty `dc*` detail object) — proceeds immediately onto a blank/untouched canvas.
- An entry with no `drawingState`, or a `drawingState.schemaVersion` this build doesn't recognize, must render its existing fields (customer/total/status/date) unchanged, with Load disabled and an explanatory note — never a crash, never a silently-hidden feature.

---

## File Structure

Single file touched: `stonedesk.html`. No new files.

| Region (function) | Responsibility for this feature |
|---|---|
| ~L3405 (`sdQuoteSaveHistory`) | One new line: attach `dcSnapshotDrawingState()`'s result as `drawingState` on the saved entry. |
| ~L13731 (new, before `printDrawCutSheet`) | New `DC_STATE_*` field-list constants, `dcSnapshotDrawingState()`, `dcLoadDrawingState()`. |
| ~L4198 (`sdHistoryView`) | Rewritten from a toast stub into a real modal populate function; adds `sdHistoryDetailOpenId` module var and `window.sdHistoryLoadIntoDrawingTool`. |
| ~L4137 (`load()`, same IIFE as `sdHistoryView`) | New `var sdHistoryDetailOpenId = null;` near the top of the IIFE. |
| ~L14626 (HTML, near the other `sairn-*-modal` blocks) | New `#sd-history-detail-modal` markup, same `.sairn-modal-overlay`/`.sairn-modal` skeleton every other modal in this file already uses. |

Line numbers are as of this plan's base commit and will drift by a few lines as earlier tasks land — every edit below is anchored to unique surrounding code, not the raw number.

---

### Task 1: Capture — field-list constants, `dcSnapshotDrawingState()`, wire into Save

**Files:**
- Modify: `stonedesk.html` (new code before `printDrawCutSheet()` ~L13731; `sdQuoteSaveHistory()` ~L3405-3426)

**Interfaces:**
- Produces: `var DC_STATE_DIM_FIELDS`, `DC_STATE_EXTRAS_CB_FIELDS`, `DC_STATE_EXTRAS_NUM_FIELDS`, `DC_STATE_JOB_TEXT_FIELDS`, `DC_STATE_JOB_SELECT_FIELDS` (arrays of DOM element id strings); `function dcSnapshotDrawingState()` returning an object `{schemaVersion, ctShape, dims, dcPoly, dcCutouts, dcSeams, dcRaisedBar, dcChamferedCorners, dcEdgeTypes, extras, jobDetails, summary}` or `null` on error. All consumed by Task 2 (restore) and Task 3 (detail modal).
- Consumes: existing globals `ctShape`, `dcPoly`, `dcCutouts`, `dcSeams`, `dcRaisedBar`, `dcChamferedCorners`, `dcEdgeTypes`; existing helpers `gN(id)`, `getCBV(id)`, `dcChamferActiveKeys()`, `dcChamferEffectiveSetbackIn(key)`, `dcRaisedBarPricingSummary()`.

- [ ] **Step 1: Add the field-list constants and `dcSnapshotDrawingState()`**

Find (around line 13730-13733):

```js
  } catch(e) {
    sugText.textContent='Connection error. Please try again.';
  }
}

// Print cut sheet
function printDrawCutSheet() {
```

Replace with:

```js
  } catch(e) {
    sugText.textContent='Connection error. Please try again.';
  }
}

// Saved-quote drawing state (2026-08-13): everything the Drawing Tool needs to fully reconstruct
// itself later, not just the flat dollar total sdQuoteSaveHistory() already saves. These five
// field lists are the single source of truth for "which DOM ids count as drawing state" -- both
// dcSnapshotDrawingState() (capture) and dcLoadDrawingState() (restore, below) read the SAME
// arrays, so the two functions can never drift out of sync with each other the way this app's old
// duplicated sink-deduction table once did (see the BUGFIX comment above printDrawCutSheet()).
var DC_STATE_DIM_FIELDS = ['da-len','da-dep','db-len','db-dep','dc-len','dc-dep','dd-len','dd-dep'];
var DC_STATE_EXTRAS_CB_FIELDS = ['dh-wf-left','dh-wf-right','dh-splashceiling','dh-splashfull','dh-splash6','dh-faucet1','dh-faucet3','dh-soap','dh-airswitch','dh-potfiller','dh-ro','dh-outlet-std','dh-outlet-usb','dh-outlet-pop','dh-gfci'];
var DC_STATE_EXTRAS_NUM_FIELDS = ['dh-wf-ht','dh-splashlen','dh-splashht','dh-outlet-count'];
var DC_STATE_JOB_TEXT_FIELDS = ['draw-job-name','draw-material','draw-edge','draw-notes'];
var DC_STATE_JOB_SELECT_FIELDS = ['draw-sink','draw-cooktop'];

// Captures a full snapshot of the Drawing Tool -- called from sdQuoteSaveHistory() below. The
// `summary` strings are built here, once, against LIVE globals, using the exact same formulas
// printDrawCutSheet() uses for its Seams/Chamfered Corners/Raised Bar/Placed Cutouts rows --
// captured now rather than re-derived later against an inert stored object, so the History
// panel's detail view never needs a second copy of this labeling logic.
function dcSnapshotDrawingState() {
  try {
    var dims = {}, extras = {}, jobDetails = {};
    DC_STATE_DIM_FIELDS.forEach(function(id){ dims[id] = gN(id); });
    DC_STATE_EXTRAS_CB_FIELDS.forEach(function(id){ extras[id] = getCBV(id); });
    DC_STATE_EXTRAS_NUM_FIELDS.forEach(function(id){ extras[id] = gN(id); });
    DC_STATE_JOB_TEXT_FIELDS.concat(DC_STATE_JOB_SELECT_FIELDS).forEach(function(id){
      var e = document.getElementById(id);
      jobDetails[id] = e ? e.value : '';
    });

    var summary = { seams: null, chamfers: null, raisedBar: null, cutouts: null };
    if (typeof dcSeams !== 'undefined' && dcSeams.length) {
      summary.seams = dcSeams.length + ' — ' + dcSeams.map(function(s){
        return s.label + ' (' + (Math.hypot(s.x2-s.x1,s.y2-s.y1)/12).toFixed(1) + ' LF)';
      }).join(', ');
    }
    if (typeof dcChamferActiveKeys === 'function') {
      var chamferLabels = { 'lshape-AB':'Inside corner (A-B)', 'ushape-BackLeft':'Inside corner (Back-Left)', 'ushape-BackRight':'Inside corner (Back-Right)' };
      var activeChamfers = dcChamferActiveKeys();
      if (activeChamfers.length) {
        summary.chamfers = activeChamfers.map(function(k){
          return (chamferLabels[k]||k) + ': ' + dcChamferEffectiveSetbackIn(k).toFixed(2) + 'in chamfer';
        }).join(', ');
      }
    }
    var barInfo = (typeof dcRaisedBarPricingSummary === 'function') ? dcRaisedBarPricingSummary() : {active:false};
    if (barInfo.active && typeof dcRaisedBar !== 'undefined' && dcRaisedBar) {
      var barEdgeLabel = dcRaisedBar.edgeKey.slice(dcRaisedBar.edgeKey.indexOf(':')+1);
      summary.raisedBar = barEdgeLabel + ': ' + barInfo.effLenIn.toFixed(1) + 'in x ' + barInfo.effDepthIn.toFixed(1) + 'in overhang, ' + dcRaisedBar.heightIn + 'in height' + (barInfo.corbelFlag ? ' (corbel support recommended)' : '');
    }
    if (typeof dcCutouts !== 'undefined' && dcCutouts.length) {
      summary.cutouts = dcCutouts.map(function(c){ return c.label; }).join(', ');
    }

    return {
      schemaVersion: 1,
      ctShape: (typeof ctShape !== 'undefined') ? ctShape : '',
      dims: dims,
      dcPoly: JSON.parse(JSON.stringify((typeof dcPoly !== 'undefined') ? dcPoly : [])),
      dcCutouts: JSON.parse(JSON.stringify((typeof dcCutouts !== 'undefined') ? dcCutouts : [])),
      dcSeams: JSON.parse(JSON.stringify((typeof dcSeams !== 'undefined') ? dcSeams : [])),
      dcRaisedBar: (typeof dcRaisedBar !== 'undefined' && dcRaisedBar) ? JSON.parse(JSON.stringify(dcRaisedBar)) : null,
      dcChamferedCorners: JSON.parse(JSON.stringify((typeof dcChamferedCorners !== 'undefined') ? dcChamferedCorners : {})),
      dcEdgeTypes: JSON.parse(JSON.stringify((typeof dcEdgeTypes !== 'undefined') ? dcEdgeTypes : {})),
      extras: extras,
      jobDetails: jobDetails,
      summary: summary
    };
  } catch (e) {
    return null;
  }
}

// Print cut sheet
function printDrawCutSheet() {
```

- [ ] **Step 2: Wire the snapshot into `sdQuoteSaveHistory()`**

Find (around line 3405-3426):

```js
  window.sdQuoteSaveHistory=function(){
    var name=(document.getElementById('client-name')||{value:''}).value||'Unknown';
    var matEl=document.getElementById('material');
    var stone=(matEl&&matEl.selectedOptions&&matEl.selectedOptions[0]?matEl.selectedOptions[0].textContent:'')||'';
    var totalEl=document.getElementById('total-price');
    var totalStr=totalEl?totalEl.textContent.replace(/[^0-9.]/g,''):'0';
    var total=parseFloat(totalStr)||0;
    var h=loadQH();
    // Field names/id type match panel-history's schema (project/amount,
    // numeric id) -- panel-history is the canonical quote-history manager
    // (search/filter/sort/status-update/CSV/print) sharing this same
    // sd_quote_history key; it reads x.project/x.amount and looks entries
    // up via parseInt(select.value)===x.id, so writing stone/total with a
    // string 'Q-' id (as this used to) meant every quote saved from here
    // showed up there with blank project/$0 amount and could never have
    // its status updated (parseInt('Q-...') is NaN).
    h.unshift({id:Date.now(),date:sdLocalToday(),customer:name,project:stone,amount:total,status:'Pending'});
    if(h.length>200)h=h.slice(0,200);
    try{localStorage.setItem('sd_quote_history',JSON.stringify(h));}catch(e){}
    updateKPIs();
    showToast('Quote saved to history for '+name+'!');
  };
```

Replace with:

```js
  window.sdQuoteSaveHistory=function(){
    var name=(document.getElementById('client-name')||{value:''}).value||'Unknown';
    var matEl=document.getElementById('material');
    var stone=(matEl&&matEl.selectedOptions&&matEl.selectedOptions[0]?matEl.selectedOptions[0].textContent:'')||'';
    var totalEl=document.getElementById('total-price');
    var totalStr=totalEl?totalEl.textContent.replace(/[^0-9.]/g,''):'0';
    var total=parseFloat(totalStr)||0;
    var h=loadQH();
    // Field names/id type match panel-history's schema (project/amount,
    // numeric id) -- panel-history is the canonical quote-history manager
    // (search/filter/sort/status-update/CSV/print) sharing this same
    // sd_quote_history key; it reads x.project/x.amount and looks entries
    // up via parseInt(select.value)===x.id, so writing stone/total with a
    // string 'Q-' id (as this used to) meant every quote saved from here
    // showed up there with blank project/$0 amount and could never have
    // its status updated (parseInt('Q-...') is NaN).
    // drawingState (2026-08-13): captures the Drawing Tool's full state so this saved quote can
    // be reopened later with more than just its flat total -- see dcSnapshotDrawingState(). Guarded
    // so a save from a page state where the drawing tool script hasn't initialized can't throw.
    var drawingState = (typeof dcPoly !== 'undefined' && typeof dcSnapshotDrawingState === 'function')
      ? dcSnapshotDrawingState() : null;
    h.unshift({id:Date.now(),date:sdLocalToday(),customer:name,project:stone,amount:total,status:'Pending',drawingState:drawingState});
    if(h.length>200)h=h.slice(0,200);
    try{localStorage.setItem('sd_quote_history',JSON.stringify(h));}catch(e){}
    updateKPIs();
    showToast('Quote saved to history for '+name+'!');
  };
```

- [ ] **Step 3: Run node --check**

Run: `python tools/checkblocks.py stonedesk.html`
Expected: `FAILED_BLOCKS:0`

- [ ] **Step 4: Manual verification (browser console)**

Open `stonedesk.html`, log in past the PIN/trial gate, go to the Quote Builder, select the `lshape` preset with real dimensions (e.g. Run A 96/25.5, Run B 72/25.5), then in devtools console:

```js
var snap = dcSnapshotDrawingState();
snap.schemaVersion;              // -> 1
snap.ctShape;                    // -> 'lshape'
snap.dims['da-len'];              // -> 96
snap.dims['da-dep'];              // -> 25.5
snap.dims['db-len'];              // -> 72
Array.isArray(snap.dcPoly);       // -> true
snap.dcRaisedBar;                 // -> null (none placed yet)
typeof snap.summary;               // -> 'object'
```

Then, in the Quote Builder's Customer Name field type a test name, and:

```js
sdQuoteSaveHistory();
var h = JSON.parse(localStorage.getItem('sd_quote_history'));
h[0].drawingState.schemaVersion;   // -> 1
h[0].drawingState.ctShape;         // -> 'lshape'
h[0].drawingState.dims['da-len'];  // -> 96
```

Expected: matches comments — the snapshot is real, and the newest `sd_quote_history` entry carries it.

- [ ] **Step 5: Commit**

```bash
git add stonedesk.html
git commit -m "feat: StoneDesk -- saved quote history captures full drawing tool state (dcSnapshotDrawingState)"
```

---

### Task 2: Restore — `dcLoadDrawingState()`

**Files:**
- Modify: `stonedesk.html` (new code immediately after `dcSnapshotDrawingState()`, before `printDrawCutSheet()`)

**Interfaces:**
- Consumes: `DC_STATE_*` constants and `dcSnapshotDrawingState()`'s exact shape (Task 1); existing `selectDrawShape(id)`, `buildEdgeAssignmentArea()`, `buildRaisedBarArea()`, `drawCTPreview()`, `calcDrawing()`.
- Produces: `function dcLoadDrawingState(state)` returning `true`/`false` — consumed by Task 3's Load button handler.

- [ ] **Step 1: Add `dcLoadDrawingState()`**

Find (the end of `dcSnapshotDrawingState()` added in Task 1, immediately before the `// Print cut sheet` comment):

```js
  } catch (e) {
    return null;
  }
}

// Print cut sheet
function printDrawCutSheet() {
```

Replace with:

```js
  } catch (e) {
    return null;
  }
}

// Saved-quote drawing state -- restore (2026-08-13). Mirror image of dcSnapshotDrawingState()
// above. Calls the REAL selectDrawShape() first so the shape-button active state, the freshly
// rebuilt dimension inputs, and buildEdgeAssignmentArea()/buildRaisedBarArea() all get created
// exactly as they would on an ordinary shape switch -- no shape-specific rebuild logic is
// duplicated here. selectDrawShape() only ever fills those fresh inputs with hardcoded DEFAULT
// values (it has no idea a snapshot is being loaded), so every field is then overwritten with the
// snapshot's real saved value, and buildEdgeAssignmentArea()/buildRaisedBarArea() are called a
// SECOND time -- both read dcChamferedCorners/dcRaisedBar at build time to sync their own
// dropdowns, so they must run again AFTER those globals hold the restored values, not before.
function dcLoadDrawingState(state) {
  try {
    if (!state || state.schemaVersion !== 1) return false;
    if (typeof selectDrawShape === 'function') selectDrawShape(state.ctShape);

    DC_STATE_DIM_FIELDS.forEach(function(id){
      var e = document.getElementById(id);
      if (e) e.value = (state.dims && state.dims[id]) ? state.dims[id] : '';
    });
    DC_STATE_EXTRAS_CB_FIELDS.forEach(function(id){
      var e = document.getElementById(id);
      if (e) e.checked = !!(state.extras && state.extras[id]);
    });
    DC_STATE_EXTRAS_NUM_FIELDS.forEach(function(id){
      var e = document.getElementById(id);
      if (e) e.value = (state.extras && state.extras[id]) ? state.extras[id] : '';
    });
    DC_STATE_JOB_TEXT_FIELDS.concat(DC_STATE_JOB_SELECT_FIELDS).forEach(function(id){
      var e = document.getElementById(id);
      if (e && state.jobDetails && state.jobDetails[id] != null) e.value = state.jobDetails[id];
    });

    dcPoly = JSON.parse(JSON.stringify(state.dcPoly || []));
    dcPolyClosed = dcPoly.length > 0;
    dcCutouts = JSON.parse(JSON.stringify(state.dcCutouts || []));
    dcSeams = JSON.parse(JSON.stringify(state.dcSeams || []));
    dcRaisedBar = state.dcRaisedBar ? JSON.parse(JSON.stringify(state.dcRaisedBar)) : null;
    dcChamferedCorners = JSON.parse(JSON.stringify(state.dcChamferedCorners || {}));
    dcEdgeTypes = JSON.parse(JSON.stringify(state.dcEdgeTypes || {}));
    dcHistory = [];

    if (typeof buildEdgeAssignmentArea === 'function') buildEdgeAssignmentArea();
    if (typeof buildRaisedBarArea === 'function') buildRaisedBarArea();
    if (typeof drawCTPreview === 'function') drawCTPreview();
    if (typeof calcDrawing === 'function') calcDrawing();
    return true;
  } catch (e) {
    return false;
  }
}

// Print cut sheet
function printDrawCutSheet() {
```

- [ ] **Step 2: Run node --check**

Run: `python tools/checkblocks.py stonedesk.html`
Expected: `FAILED_BLOCKS:0`

- [ ] **Step 3: Manual verification (browser console)**

With the Drawing Tool on a fresh `straight` preset (default dims):

```js
selectDrawShape('lshape');
document.getElementById('da-len').value = 96;
document.getElementById('db-len').value = 72;
drawCTPreview(); calcDrawing();
var snap = dcSnapshotDrawingState();

selectDrawShape('straight');                 // simulate a different shape being on screen
document.getElementById('da-len').value = 40;
drawCTPreview();

dcLoadDrawingState(snap);                      // -> true
ctShape;                                       // -> 'lshape'
document.getElementById('da-len').value;       // -> '96'
document.getElementById('db-len').value;       // -> '72'

dcLoadDrawingState(null);                      // -> false (no throw)
dcLoadDrawingState({schemaVersion: 99});       // -> false (no throw, unrecognized version)
```

Expected: matches comments — loading a snapshot really does switch the shape and restore its dimensions; malformed input returns `false` without throwing.

- [ ] **Step 4: Commit**

```bash
git add stonedesk.html
git commit -m "feat: StoneDesk -- dcLoadDrawingState() restores a saved snapshot into the live Drawing Tool"
```

---

### Task 3: History panel — detail modal, itemized breakdown, Load button

**Files:**
- Modify: `stonedesk.html` (HTML ~L14626, `load()`'s IIFE ~L4137, `sdHistoryView()` ~L4198-4203)

**Interfaces:**
- Consumes: `dcLoadDrawingState()` (Task 2); existing `load()` (panel-history's own reader of `sd_quote_history`), `escHtml()`, `sbNav(id)`.
- Produces: `window.sdHistoryLoadIntoDrawingTool` — consumed only by the new Load button's `onclick`.

- [ ] **Step 1: Add the detail modal markup**

Find (around line 14625-14628):

```html
<!-- TOAST -->
<div class="sairn-toast-msg" id="sairn-toast"></div>




```

Replace with:

```html
<!-- TOAST -->
<div class="sairn-toast-msg" id="sairn-toast"></div>



<!-- ===== QUOTE HISTORY DETAIL MODAL (2026-08-13) ===== -->
<div class="sairn-modal-overlay" id="sd-history-detail-modal">
<div class="sairn-modal">
  <div class="sairn-modal-hdr">
    <div class="sairn-modal-title" id="sd-hdm-title">Quote Detail</div>
    <button class="sairn-modal-close" onclick="document.getElementById('sd-history-detail-modal').classList.remove('open')">✕</button>
  </div>
  <div id="sd-hdm-body"></div>
  <button class="sairn-btn sairn-btn-primary" id="sd-hdm-load-btn" style="width:100%;margin-top:14px" onclick="sdHistoryLoadIntoDrawingTool()">Load into Drawing Tool</button>
</div>
</div>
```

- [ ] **Step 2: Add `sdHistoryDetailOpenId` to panel-history's IIFE**

Find (around line 4137):

```js
  function load(){
    var d=[];
    try{d=JSON.parse(localStorage.getItem('sd_quote_history')||'null')||[];}catch(e){}
```

Replace with:

```js
  var sdHistoryDetailOpenId = null; // 2026-08-13: which entry's id the detail modal currently shows -- lets the Load button (no id param) know what to load
  function load(){
    var d=[];
    try{d=JSON.parse(localStorage.getItem('sd_quote_history')||'null')||[];}catch(e){}
```

- [ ] **Step 3: Rewrite `sdHistoryView()` into a real modal, add `sdHistoryLoadIntoDrawingTool()`**

Find (around line 4198-4203):

```js
  window.sdHistoryView=function(id){
    var d=load();
    var x=d.find(function(q){return q.id===id;});
    if(!x)return;
    showToast(escHtml(x.customer||'')+' — $'+(x.amount||0).toLocaleString()+' — '+x.status);
  };
```

Replace with:

```js
  window.sdHistoryView=function(id){
    var d=load();
    var x=d.find(function(q){return q.id===id;});
    if(!x)return;
    sdHistoryDetailOpenId = id;
    document.getElementById('sd-hdm-title').textContent = (x.customer||'Quote') + ' — $' + (x.amount||0).toLocaleString() + ' — ' + (x.status||'Pending');
    var row = function(label, val){
      return '<div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid var(--border);font-size:13px"><span style="color:var(--muted)">'+escHtml(label)+'</span><span style="font-weight:600;text-align:right;margin-left:12px">'+val+'</span></div>';
    };
    var body = document.getElementById('sd-hdm-body');
    var loadBtn = document.getElementById('sd-hdm-load-btn');
    var ds = x.drawingState;
    if (!ds || ds.schemaVersion !== 1) {
      body.innerHTML = '<div style="color:var(--muted);padding:10px 0;font-size:13px">No drawing detail saved — quotes saved before this update show total only.</div>';
      loadBtn.disabled = true;
      loadBtn.title = 'No drawing detail saved for this quote';
    } else {
      var rows = [];
      rows.push(row('Shape', escHtml(ds.ctShape||'')));
      if (ds.dims && ds.dims['da-len'] && ds.dims['da-dep']) rows.push(row('Section A', ds.dims['da-len']+'" × '+ds.dims['da-dep']+'"'));
      if (ds.dims && ds.dims['db-len'] && ds.dims['db-dep']) rows.push(row('Section B', ds.dims['db-len']+'" × '+ds.dims['db-dep']+'"'));
      if (ds.dims && ds.dims['dc-len'] && ds.dims['dc-dep']) rows.push(row('Section C', ds.dims['dc-len']+'" × '+ds.dims['dc-dep']+'"'));
      if (ds.jobDetails && ds.jobDetails['draw-material']) rows.push(row('Material', escHtml(ds.jobDetails['draw-material'])));
      if (ds.jobDetails && ds.jobDetails['draw-edge']) rows.push(row('Edge Profile', escHtml(ds.jobDetails['draw-edge'])));
      if (ds.summary && ds.summary.seams) rows.push(row('Seams', escHtml(ds.summary.seams)));
      if (ds.summary && ds.summary.chamfers) rows.push(row('Chamfered Corners', escHtml(ds.summary.chamfers)));
      if (ds.summary && ds.summary.raisedBar) rows.push(row('Raised Bar', escHtml(ds.summary.raisedBar)));
      if (ds.summary && ds.summary.cutouts) rows.push(row('Placed Cutouts', escHtml(ds.summary.cutouts)));
      if (ds.jobDetails && ds.jobDetails['draw-notes']) rows.push(row('Notes', escHtml(ds.jobDetails['draw-notes'])));
      body.innerHTML = rows.join('');
      loadBtn.disabled = false;
      loadBtn.title = '';
    }
    document.getElementById('sd-history-detail-modal').classList.add('open');
  };
  window.sdHistoryLoadIntoDrawingTool=function(){
    var id = sdHistoryDetailOpenId;
    if (id == null) return;
    var d = load();
    var x = d.find(function(q){return q.id===id;});
    if (!x || !x.drawingState || x.drawingState.schemaVersion !== 1) return;
    var hasUnsaved = (typeof dcPoly !== 'undefined' && dcPoly.length > 0)
      || (typeof dcCutouts !== 'undefined' && dcCutouts.length > 0)
      || (typeof dcSeams !== 'undefined' && dcSeams.length > 0)
      || (typeof dcRaisedBar !== 'undefined' && dcRaisedBar)
      || (typeof dcChamferedCorners !== 'undefined' && Object.keys(dcChamferedCorners).length > 0)
      || (typeof gN === 'function' && (gN('da-len') > 0 || gN('da-dep') > 0));
    if (hasUnsaved && !confirm('Loading this quote will replace your current drawing — continue?')) return;
    document.getElementById('sd-history-detail-modal').classList.remove('open');
    if (typeof dcLoadDrawingState === 'function') dcLoadDrawingState(x.drawingState);
    if (typeof sbNav === 'function') sbNav('draw');
  };
```

- [ ] **Step 4: Run node --check**

Run: `python tools/checkblocks.py stonedesk.html`
Expected: `FAILED_BLOCKS:0`

- [ ] **Step 5: Manual verification (browser console)**

With at least one quote already saved via Task 1's Step 4 (real `drawingState`), and `sd_quote_history` also containing an old-format entry with no `drawingState` (the seed data at `stonedesk.html:4126-4136` has none — use `id:1` for this):

```js
sdHistoryRender();                                  // populate the table
sdHistoryView(1);                                    // seed entry, no drawingState
document.getElementById('sd-history-detail-modal').classList.contains('open'); // -> true
document.getElementById('sd-hdm-load-btn').disabled; // -> true
document.getElementById('sd-hdm-body').textContent.indexOf('No drawing detail saved') >= 0; // -> true

var h = JSON.parse(localStorage.getItem('sd_quote_history'));
var realId = h[0].id;                                 // the entry saved in Task 1 Step 4
sdHistoryView(realId);
document.getElementById('sd-hdm-load-btn').disabled;  // -> false
document.getElementById('sd-hdm-body').textContent.indexOf('lshape') >= 0; // -> true (or whatever shape was saved)

selectDrawShape('straight');
document.getElementById('da-len').value = 12;         // real unsaved-looking content
window.confirm = () => true;                           // auto-accept the guard for this check
sdHistoryLoadIntoDrawingTool();
ctShape;                                                // -> 'lshape' (loaded back in)
document.getElementById('da-len').value;                // -> '96'
document.getElementById('sd-history-detail-modal').classList.contains('open'); // -> false
```

Expected: matches comments — legacy entry shows the disabled Load state and the explanatory note; the real entry's Load button is enabled, shows a real breakdown, and loading it actually restores the drawing.

- [ ] **Step 6: Commit**

```bash
git add stonedesk.html
git commit -m "feat: StoneDesk -- History panel quote-detail modal, itemized breakdown, Load into Drawing Tool"
```

---

### Task 4: Full verification sweep, live-verify, and push

**Files:** none (verification only)

- [ ] **Step 1: Full local syntax sweep**

Run: `python tools/checkblocks.py stonedesk.html`
Expected: `FAILED_BLOCKS:0` across all blocks.

- [ ] **Step 2: Scoped Guardian checks**

Run: `python tools/duplicate_global_check.py stonedesk.html`
Expected: `DUPLICATE_NAMES:0`

Run: `python tools/div_balance_check.py stonedesk.html`
Expected: `RESULT:PASS`

Run: `python tools/nav_panel_check.py stonedesk.html`
Expected: `RESULT:PASS` (this feature doesn't touch panels/nav; a regression here would indicate an unintended change elsewhere).

Run: `python tools/sairn_dead_button_audit.py stonedesk.html`
Expected: no new findings referencing `sd-hdm-load-btn`, `sdHistoryLoadIntoDrawingTool`, `dcSnapshotDrawingState`, `dcLoadDrawingState`.

Search: grep `stonedesk.html` for `console.log` inside the diff introduced by this plan — confirm none was left in.

- [ ] **Step 3: Run the full Guardian review before commit/push**

Invoke the `sairn-guardian-v2` skill's full Check 0 + numbered checks against the diff, per CLAUDE.md's standing Push Protocol. Pay particular attention to Check 25 (escaped user content) on the new modal body — every field sourced from a rep-typed input (`jobDetails['draw-material']`, `draw-edge`, `draw-notes`) must go through `escHtml()`, matching this session's earlier fix to `printDrawCutSheet()`. Resolve any findings before proceeding.

- [ ] **Step 4: Combined end-to-end manual verification (browser console)**

The proof no single task's check above fully covers: a save/reload/load round-trip through `localStorage` (not just in-memory), on a quote carrying every kind of drawing-tool detail at once.

```js
selectDrawShape('ushape');
document.getElementById('da-len').value = 72; document.getElementById('da-dep').value = 25.5;
document.getElementById('db-len').value = 84; document.getElementById('db-dep').value = 25.5;
document.getElementById('dc-len').value = 72; document.getElementById('dc-dep').value = 25.5;
document.getElementById('draw-job-name').value = 'Round-Trip Test';
document.getElementById('draw-material').value = 'Test Quartz';
drawCTPreview(); calcDrawing();
document.getElementById('client-name').value = 'Round Trip QA';
sdQuoteSaveHistory();

// Simulate a fresh page load reading only from localStorage, not from any in-memory state:
var h = JSON.parse(localStorage.getItem('sd_quote_history'));
var saved = h[0];
saved.drawingState.jobDetails['draw-job-name'];   // -> 'Round-Trip Test'
saved.drawingState.dims['db-len'];                // -> 84

selectDrawShape('straight');                       // simulate navigating away
document.getElementById('da-len').value = 1;
drawCTPreview();

sdHistoryRender();
sdHistoryView(saved.id);
window.confirm = () => true;
sdHistoryLoadIntoDrawingTool();
ctShape;                                            // -> 'ushape'
document.getElementById('db-len').value;            // -> '84'
document.getElementById('draw-job-name').value;     // -> 'Round-Trip Test'
```

Expected: matches every comment — a real save/reload/load cycle through actual `localStorage` JSON reproduces the exact original state, not just an in-memory copy.

- [ ] **Step 5: Push**

```bash
git push origin main
```

- [ ] **Step 6: Live-verify against production**

Per CLAUDE.md's Push Protocol: drive `sairn.vercel.app/stonedesk`'s deployed functions directly (Playwright, using the license-gate workaround documented in `STONEDESK-SESSION79-HANDOFF.md` §3) and repeat Step 4's console checks against the live site. Confirm the deployed file hash matches the pushed commit (normalize line endings before comparing — CRLF/LF, not content, was the cause of the one false-positive deploy-mismatch hit earlier this session).

- [ ] **Step 7: Write the session handoff**

Use the `sairn-session-handoff` skill to record this feature's landing in a new `STONEDESK-SESSION-N-HANDOFF.md` (next number in sequence). Note explicitly that this closes the `SAIRN-BACKLOG.md` item "StoneDesk saved quote history doesn't capture the drawing tool's own state" logged 2026-08-13 — remove or mark it resolved in `SAIRN-BACKLOG.md` in the same commit.

---

## Self-Review Notes

- **Spec coverage:** capture (Task 1) and restore (Task 2) match the spec's Architecture section exactly, including the `schemaVersion` guard and try/catch degradation. The History modal, itemized breakdown, Load button, and overwrite-guard confirm (Task 3) match the spec's Restore Flow and Legacy/Degradation sections. The full save→reload→load round-trip through real `localStorage` (Task 4, Step 4) is the concrete proof of the spec's central "reopening a saved quote... has something to reconstruct from" goal. `dcEdgeTypes` was added to the snapshot beyond the spec's literal data-model list — in scope under the spec's own stated principle ("everything that affects the total or cut sheet"), since Custom Draw mode's per-edge type assignments feed edge-cost pricing the same way the four named `dc*` objects do; noted here rather than silently expanding scope.
- **Placeholder scan:** no TBD/TODO, no "add appropriate handling" — every step shows real code (matching the actual current file content, re-read immediately before writing this plan) or a real runnable console check with a stated expected result.
- **Type/name consistency:** `DC_STATE_DIM_FIELDS`/`DC_STATE_EXTRAS_CB_FIELDS`/`DC_STATE_EXTRAS_NUM_FIELDS`/`DC_STATE_JOB_TEXT_FIELDS`/`DC_STATE_JOB_SELECT_FIELDS`, `dcSnapshotDrawingState`, `dcLoadDrawingState`, `sdHistoryDetailOpenId`, `sdHistoryLoadIntoDrawingTool` are spelled identically everywhere they're produced (Task 1/2/3) and consumed (Task 2/3/4). The `drawingState` object's field names (`schemaVersion`, `ctShape`, `dims`, `dcPoly`, `dcCutouts`, `dcSeams`, `dcRaisedBar`, `dcChamferedCorners`, `dcEdgeTypes`, `extras`, `jobDetails`, `summary`) are identical between the object `dcSnapshotDrawingState()` returns (Task 1) and every place `dcLoadDrawingState()` (Task 2) and `sdHistoryView()` (Task 3) read them.
