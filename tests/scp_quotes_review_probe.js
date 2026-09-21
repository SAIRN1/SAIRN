// tests/scp_quotes_review_probe.js
//
// Run:  node tests/scp_quotes_review_probe.js
//
// INDEPENDENT REVIEW of the SAIRNscape scp_quotes outbound queue (4f674484 +
// 9cfc8eec, CC), discharging the Tier A obligation cc opened at
// 2026-09-18T13:20:49Z. Reviewer: hank. The brief named five things to press
// on; two of them turn out to be real, and both are reproduced below rather
// than argued in prose.
//
// ── REPORT-ONLY AND EXIT 0, DELIBERATELY ──────────────────────────────────
// Same precedent as tests/dnt_rollup_review_probe.js: these are findings on
// somebody else's file, and turning them into a failing suite would block
// every other session's push on a defect they did not write and cannot land a
// fix for from their own claim. It PRINTS, it does not gate.
//
// Delete this file when both findings are closed -- OR, better, keep it and
// re-aim it at the closures, which is what the dnt_rollup probe became.
//
// ── IT DRIVES THE REAL FUNCTIONS, NOT THEIR SOURCE TEXT ───────────────────
// The author's own suite (tests/sairnscape_outbound_queue.js) stubs scpData
// wholesale and checks scpSendDesignToQuote by regex over `grab()`ed source.
// Both findings below are invisible to that shape by construction: one lives
// in the part of scpData the stub replaces, and the other is a property of a
// DOM node surviving across two calls, which no regex over one function can
// see. So this probe loads the real scpData and the real
// scpOpenDesignModal/scpSendDesignToQuote into a vm and drives them.

'use strict';

const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ROOT = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(ROOT, 'sairnscape.html'), 'utf8').replace(/\r\n/g, '\n');

let findings = 0;

function grab(sig, terminator) {
  const at = html.indexOf(sig);
  if (at < 0) throw new Error('not found in sairnscape.html: ' + sig);
  const n = html.split(sig).length - 1;
  if (n !== 1) throw new Error('anchor is NOT UNIQUE (' + n + ' hits), refusing to guess: ' + sig);
  const end = html.indexOf(terminator, at);
  if (end < 0) throw new Error('terminator not found after ' + sig);
  return html.slice(at, end + terminator.length);
}

// ── element stubs: enough of a node for the code under test to drive ──────
function elStub() {
  return { disabled: false, textContent: '', innerHTML: '', value: '',
           onclick: null, style: {}, classList: { add() {}, remove() {} } };
}

function harness(opts) {
  opts = opts || {};
  const store = Object.assign({ scp_lic: JSON.stringify('LIC-TEST') }, opts.store || {});
  const els = {};
  const ctx = {
    console: { warn() {}, error() {}, log() {} },
    JSON, Date, String, Number, Array, Object, Boolean, Math, isNaN, setTimeout,
    sessionStorage: { getItem() { return null; } },
    localStorage: {
      getItem(k) { return Object.prototype.hasOwnProperty.call(store, k) ? store[k] : null; },
      setItem(k, v) { store[k] = v; }
    },
    AbortSignal: undefined,
    fetch: opts.fetch || (async () => { throw new Error('offline'); }),
    // -- app helpers the functions under test call, stubbed --
    scp$(id) { if (!els[id]) els[id] = elStub(); return els[id]; },
    scpToast(m) { ctx.__toasts.push(m); },
    scpH(s) { return String(s || ''); },
    scpFdate(d) { return String(d || '--'); },
    scpLocalToday() { return '2026-09-21'; },
    scpDaysFromNow() { return '2026-10-21'; },
    scpRQuotes() {},
    scpFillCustomerSelects() {},
    scpRenderDesignElemTable() {},
    scpDesigns() { return ctx.scpLd('scp_designs', []); },
    SCP_DW_TYPE_LABELS: { sprinkler: 'Sprinkler Head' },
    async scpSaveDesignRecord(rec) {
      const all = ctx.scpLd('scp_designs', []);
      const i = all.findIndex((x) => x.id === rec.id);
      if (i >= 0) all[i] = rec; else all.push(rec);
      ctx.scpSt('scp_designs', all);
      return await ctx.scpData('write', 'scp_designs', rec);
    },
    __toasts: [], __els: els, __store: store
  };
  ctx.window = ctx;
  ctx.globalThis = ctx;
  vm.createContext(ctx);

  const src = [
    grab('function scpSt(k,v){', '\n}\n'),
    grab('function scpLd(k,d){', '\n}\n'),
    'var SCP_FETCH_TIMEOUT_MS = 15000;',
    grab('function scpFetchTimeoutSignal(){', '\n}\n'),
    grab('async function scpData(action, resource, payload, appId) {', '\n}\n'),
    'var scpLastErr = {};',
    grab('function scpLastErrCode(', '\n'),
    grab('function scpLastErrText(', '\n'),
    grab('function scpWriteRefused(', '\n'),
    grab('var SCP_PENDING_KEY=', '\n'),
    grab('var SCP_QUEUED_PATH=', '\n'),
    grab('var SCP_UNQUEUED_QUOTE_PATHS=', '\n'),
    grab('function scpPendingCoverage(', '\n'),
    grab('function scpUnqueuedQuotePaths(', '\n'),
    grab('function scpPendingAll(', '\n'),
    grab('function scpPendingCount(', '\n'),
    grab('function scpRefusedAll(', '\n'),
    grab('function scpPendingAdd(resource,rec){', '\n}\n'),
    'var _scpFlushing=false;',
    grab('async function scpFlushPending(){', '\n}\n'),
    grab('async function scpFlushAndReport(quiet){', '\n}\n'),
    grab('function scpRenderPendingBanner(){', '\n}\n'),
    grab('function scpUpdateApprovalUI(rec){', '\n}\n'),
    grab('function scpOpenDesignModal(id){', '\n}\n'),
    grab('async function scpSendDesignToQuote(){', '\n}\n'),
    'var scpDwid=null;'
  ].join('\n');
  vm.runInContext(src, ctx);
  return ctx;
}

// ══════════════════════════════════════════════════════════════════════════
// FINDING 1 -- press-on (2): a stale 4xx DOES survive, on the one path that
// returns before the recorder. This is the exact defect cc asked to be
// checked for and the exact defect sairndental is recorded as having shipped.
// ══════════════════════════════════════════════════════════════════════════
async function finding1() {
  // A genuine server refusal happens first, and is recorded correctly.
  const ctx = harness({
    fetch: async () => ({ ok: false, status: 400,
      json: async () => ({ error: { code: 'BAD_ROW', message: 'quote payload.customer_id is required' } }) })
  });
  await ctx.scpData('write', 'scp_quotes', { id: 'Q-1' });
  const refusedAfterRealRefusal = ctx.scpWriteRefused('scp_quotes');

  // Now the licence goes away. Three ways this happens and none of them are
  // contrived: the licence-change wipe clears every scp_ key; localStorage
  // can throw (`scpLd` catches and returns the DEFAULT, which is null); and a
  // corrupted scp_lic value fails JSON.parse and also returns the default.
  delete ctx.__store.scp_lic;

  // scpData now returns at `if (!licKey) return null;` -- BEFORE the fetch,
  // and before any line that touches scpLastErr.
  const out = await ctx.scpData('write', 'scp_quotes', { id: 'Q-2' });
  const stillRefused = ctx.scpWriteRefused('scp_quotes');
  const staleReason = ctx.scpLastErrText('scp_quotes');

  console.log('\n=== FINDING 1 (HIGH) -- a no-licence failure inherits an earlier 4xx ===');
  console.log('  sairnscape.html:2077-2078');
  console.log('    var licKey = scpLd(\'scp_lic\', null);');
  console.log('    if (!licKey) return null;          // <-- scpLastErr NOT cleared');
  console.log('');
  console.log('  after a real 400:            scpWriteRefused = ' + refusedAfterRealRefusal + '   (correct)');
  console.log('  after the licence is gone:   scpData         = ' + out);
  console.log('                               scpWriteRefused = ' + stillRefused
    + (stillRefused ? '   <-- WRONG, nobody looked' : '   (correct)'));
  console.log('                               reason shown    = "' + staleReason + '"');

  if (!stillRefused) { console.log('  NOT REPRODUCED -- this finding appears to be closed.'); return; }
  findings++;
  console.log(`
  WHY IT MATTERS. scpSendDesignToQuote branches on exactly this value:

      var quoteQueued=(!quoteSynced&&!scpWriteRefused('scp_quotes'))?...:false;
      var quoteRefused=!quoteSynced&&scpWriteRefused('scp_quotes');

  so a send with no licence is classified as a SERVER REFUSAL. Three
  consequences, and the first is the one that loses work:
    1. the row is NOT QUEUED -- the whole retry path is skipped;
    2. the toast says "was REFUSED by the server -- quote payload.customer_id
       is required", quoting a reason from an unrelated earlier row;
    3. if the row had already been queued, scpFlushPending marks it
       'refused' and it is never retried again.

  The code's OWN COMMENT (sairnscape.html:2143-2144) names this case and
  states the opposite of what the code does: "Anything without a status --
  NO LICENCE, a timeout, a dead connection -- means nobody looked." The catch
  block is careful to clear the status for exactly this reason; the
  no-licence return, which is the other half of the same rule, is not.

  THE AUTHOR'S SUITE CANNOT SEE THIS. harness() in
  tests/sairnscape_outbound_queue.js replaces scpData with its own stub, so
  the licence guard -- the only line at fault -- is never executed by it.

  FIX, one line:
      if (!licKey) { scpLastErr[resource] = { code: 'NO_LICENCE', message: '' }; return null; }
  No status, same as the catch. Then add an arm that drives the REAL scpData
  across two calls, because a stub cannot fail this way.`);
}

// ══════════════════════════════════════════════════════════════════════════
// FINDING 2 -- press-on (4): cc asked whether a re-render could leave a
// button labelled "Retry upload" wired to the original send. It is the other
// direction that happens, and it is worse: a button labelled "Send Approved
// Design to Quoting" wired to the FLUSH.
// ══════════════════════════════════════════════════════════════════════════
async function finding2() {
  const designs = [
    { id: 'DW-1', customer_id: 'C-1', elements: [{ type: 'sprinkler', label: 'front' }],
      approved: true, approved_by: 'A', approved_at: '2026-09-20', quote_id: null },
    { id: 'DW-2', customer_id: 'C-2', elements: [{ type: 'sprinkler', label: 'back' }],
      approved: true, approved_by: 'B', approved_at: '2026-09-20', quote_id: null }
  ];
  const ctx = harness({
    store: { scp_designs: JSON.stringify(designs) },
    fetch: async () => { throw new Error('offline'); }   // nobody looked
  });

  // 1. Open design DW-1 and send it. The network is down.
  ctx.scpOpenDesignModal('DW-1');
  const btn = ctx.scp$('scp-dw-send-quote-btn');
  const originalOnclick = btn.onclick;                  // null: inline HTML handler
  await ctx.scpSendDesignToQuote();
  const rewired = btn.onclick;
  const labelAfterFailure = btn.textContent;

  // 2. Close the modal and open a DIFFERENT approved design.
  ctx.scpDwid = null;
  ctx.scpOpenDesignModal('DW-2');
  const labelNow = btn.textContent;
  const disabledNow = btn.disabled;
  const onclickNow = btn.onclick;

  console.log('\n=== FINDING 2 (HIGH) -- the rebound onclick outlives the design it was bound for ===');
  console.log('  sairnscape.html:3197   sendBtn.onclick=function(){scpFlushAndReport();};');
  console.log('  sairnscape.html:2935-2937  scpOpenDesignModal resets .disabled and .textContent');
  console.log('                             and does NOT reset .onclick');
  console.log('');
  console.log('  after DW-1 fails to send:  label = "' + labelAfterFailure + '"');
  console.log('                             onclick rebound to flush = ' + (rewired !== originalOnclick));
  console.log('  after opening DW-2:        label    = "' + labelNow + '"');
  console.log('                             disabled = ' + disabledNow);
  console.log('                             onclick  = ' + (onclickNow === rewired
    ? 'STILL THE FLUSH  <-- WRONG' : 'restored'));

  if (onclickNow !== rewired) { console.log('  NOT REPRODUCED -- this finding appears to be closed.'); return; }
  findings++;

  // 3. Prove the consequence: press it and see what DW-2 gets.
  ctx.__toasts.length = 0;
  onclickNow();
  // the handler does not return its promise, so drain the microtask queue
  for (let i = 0; i < 20; i++) await Promise.resolve();
  const dw2 = ctx.scpDesigns().find((d) => d.id === 'DW-2');
  console.log('');
  console.log('  pressing "' + labelNow + '":');
  console.log('    toast          = "' + (ctx.__toasts[0] || '(none)') + '"');
  console.log('    DW-2.quote_id  = ' + JSON.stringify(dw2 && dw2.quote_id));
  console.log('    quotes stored  = ' + JSON.stringify(ctx.scpLd('scp_quotes', []).map((q) => q.id)));
  console.log(`
  WHY IT MATTERS. The send button is STATIC MARKUP (sairnscape.html:1530,
  inside the modal, with an inline onclick). It is never destroyed and
  recreated, so assigning .onclick replaces the inline handler for the
  LIFETIME OF THE PAGE. scpOpenDesignModal puts the label and the enabled
  state back for the next design and leaves the handler pointing at the
  flush.

  So after any failed send, EVERY subsequent design in that session shows a
  button reading "Send Approved Design to Quoting", enabled, which does not
  send that design to quoting. It flushes the previous design's queue and
  reports on THAT. No quote is created, no error is shown, and the toast
  describes a different record. That is the same defect class this whole fix
  was written to remove -- a control wearing a claim it does not perform --
  reintroduced one call away from the fix.

  scpApproveDesign (sairnscape.html:2974) re-enables the same button without
  restoring the handler either, so approving a design after a failed send
  reaches the same state by a second route.

  THE AUTHOR'S SUITE CANNOT SEE THIS EITHER. It asserts over the source text
  of scpSendDesignToQuote alone (/Retry upload/.test(src)); the defect is a
  property of the DOM node ACROSS two functions, and no regex over one of
  them can express it.

  FIX. Restore the handler wherever the label is restored -- one line in
  scpOpenDesignModal and one in scpApproveDesign:
      sendBtn.onclick=function(){scpSendDesignToQuote();};
  Better: set the handler from one place that also sets the label, so the two
  cannot drift again. A sabotage arm that opens a SECOND design after a
  failed send is what pins it.`);
}

// ══════════════════════════════════════════════════════════════════════════
// The three press-on points that came back clean, recorded so the next
// reviewer does not re-derive them.
// ══════════════════════════════════════════════════════════════════════════
function clean() {
  const sd = fs.readFileSync(path.join(ROOT, 'api', 'sd-data.js'), 'utf8');
  // Built with RegExp rather than as literals: the Tier A gate's source
  // scanner does not model regex literals, so a literal carrying an odd number
  // of apostrophes reads to it as an unterminated string and swallows the rest
  // of the file -- including the process.exit(0) that makes this artefact
  // report-only. Quote-balanced construction keeps that from happening.
  const q = String.fromCharCode(39);
  const scpWrites = (sd.match(new RegExp(
    'resource === ' + q + 'scp_[a-z_]+' + q + ' && action === ' + q + 'write' + q, 'g')) || []).length;
  const scpUpserts = (sd.match(new RegExp(
    'rest\\(' + q + 'scp_[a-z_]+\\?on_conflict=license_hash,', 'g')) || []).length;

  console.log('\n=== CHECKED AND CORRECT ===');
  console.log(`  (1) THE PRECONDITION HOLDS, AND MORE WIDELY THAN CLAIMED. cc read the
      right branches: api/sd-data.js posts scp_quotes to
      '?on_conflict=license_hash,quote_id' and scp_designs to
      '?on_conflict=license_hash,design_id', both with
      'Prefer: resolution=merge-duplicates,return=representation'. Retrying a
      row whose response was lost updates it rather than adding a second.

      cc also asked whether any other scp_ write the queue might later cover
      is a plain insert. None is: every scp_ table write in api/sd-data.js
      carries the same on_conflict+merge-duplicates shape, counted here rather
      than eyeballed --
        scp_* write branches : ` + scpWrites + `
        scp_* upsert targets : ` + scpUpserts + `
      (the second figure is larger because customers/schedule/invoices reach
      scp_ tables under resource names without the scp_ prefix). Extending the
      queue to the three unqueued quote paths is safe on the server side
      today. The suite already pins the two contracts it depends on, which is
      the right place for them.

  (3) THE REFUSED PATH IS RIGHT. scpFlushPending moves a refused row out of
      'pending' into 'refused', keeps it, never retries it (the flush only
      ever iterates status==='pending'), and the local copy is deliberately
      not deleted. The banner names the resource, the id and the reason, and
      says the two disagree -- it cannot be misread as a pending upload,
      because the pending sentence is a separate <b> clause with its own
      count and only appears when something is actually pending.

  (5) THE BANNER'S COVERAGE WORDING IS NOT OVERSTATED, and 9cfc8eec made it
      stronger than the obligation text describes. It now reads "Only
      <coverage> is queued for retry. <the unqueued quote paths> are NOT --
      nor is any other write in this app." Naming the sibling quote paths
      explicitly is the part that matters: those are the ones a reader would
      otherwise assume were covered.`);
}

(async () => {
  console.log('INDEPENDENT REVIEW -- SAIRNscape scp_quotes outbound queue');
  console.log('obligation cc 2026-09-18T13:20:49Z, reviewed by hank');
  await finding1();
  await finding2();
  clean();
  console.log('\n' + findings + ' finding(s). Report-only: exit 0 by design.');
  process.exit(0);
})();
