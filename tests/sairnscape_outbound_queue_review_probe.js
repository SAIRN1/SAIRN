// tests/sairnscape_outbound_queue_review_probe.js
//
// Run:  node tests/sairnscape_outbound_queue_review_probe.js
//
// INDEPENDENT REVIEW of SAIRNscape's outbound queue -- 4f674484 and 9cfc8eec
// (CC) -- under the Tier A obligation cc opened 2026-09-18T13:20:49Z on
// scp_quotes. The brief named five things to press on: (1) that the server
// writes the queue rests on are UPSERTs and that no other scp_ write is a plain
// insert, (2) that no path can leave a stale 4xx behind so a later network
// failure reads as a fresh refusal, (3) that a REFUSED row is legible rather
// than looking pending, (4) that a later re-render cannot leave the send button
// labelled one thing and wired to another, (5) that the banner's coverage
// wording cannot be read as covering the writes it does not cover.
//
// ── REPORT-ONLY AND EXIT 0, DELIBERATELY ──────────────────────────────────
// Same precedent as tests/dnt_rollup_review_probe.js and
// tests/failsafe/countersign_coverage_probe.py: these are findings in another
// agent's file, and turning them into a failing suite would block every other
// session's push on a defect they did not write and cannot land a fix for from
// their own claim. It PRINTS, it does not gate. I am not fixing any of them --
// I hold a review claim, not the file, and a reviewer who lands the fix is no
// longer independent of it. Each carries a suggested fix that is the author's
// to take or refuse.
//
// ── WHAT THE REVIEW CONFIRMED AS CORRECT, said first ──────────────────────
// Press-on (1) HOLDS, and holds wider than asserted. Every one of the 12 scp_
// table writes in api/sd-data.js -- not just scp_quotes and scp_designs -- is
// POSTed to `?on_conflict=license_hash,<idCol>` with
// `Prefer: resolution=merge-duplicates`, and both on_conflict targets are real
// unique constraints in the schema files (`unique (license_hash, quote_id)` at
// sql/sairnscape_data_schema.sql:70, `unique (license_hash, design_id)` at
// sql/sairnscape_data_schema_phase2.sql:44), so the on_conflict clause cannot
// 42P10 at runtime. Asserted below rather than restated. Nothing in the app
// would have to change for the queue to be extended to the other ten.
//
// Press-on (5) HOLDS as measured. SCP_QUEUED_PATH and SCP_UNQUEUED_QUOTE_PATHS
// match the file: one queued call site, three sibling quote-writing paths that
// are not, and the banner names all four. The wording does not overstate.
//
// Press-on (3) is legible in isolation -- but see FINDING 3, which puts rows in
// the refused list that do not belong there, and note that nothing in the app
// can ever clear one: there is no dismiss, no edit-and-requeue, and the only
// button is "Try uploading now", which only touches pending rows. A single
// refused row makes the banner permanent for the life of the browser profile.
//
// FINDING 1 is the answer to press-on (4) and the hazard is the reverse of the
// one asked about: not a "Retry upload" button wired to the send, but a "Send
// Approved Design to Quoting" button wired to the flush.
//
// FINDING 2 was not among the five and is the most serious: a row the queue
// ACCEPTED can be erased by a flush that was already running.
//
// ── THE THREE DOM BEHAVIOURS FINDING 1 RESTS ON were verified in real Chrome
// on 2026-09-21, not assumed, because the element here is modelled:
//   a) `<button onclick="origSend()">` installs an onclick HANDLER  -> true
//   b) `el.onclick = g` REPLACES it, while `el.getAttribute('onclick')`
//      still reads "origSend()"                                     -> true
//   c) after the rebind, setting textContent/disabled and clicking runs g
//      -> hits ["origSend","flushAndReport"], label unchanged
// (b) is the load-bearing one: the markup and the DOM attribute both still say
// scpSendDesignToQuote(), so nothing short of reading the live property shows
// the rebinding.

'use strict';

const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ROOT = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(ROOT, 'sairnscape.html'), 'utf8').replace(/\r\n/g, '\n');
const sdData = fs.readFileSync(path.join(ROOT, 'api', 'sd-data.js'), 'utf8').replace(/\r\n/g, '\n');

let findings = 0;

function grab(sig, term) {
  const at = html.indexOf(sig);
  if (at < 0) throw new Error('not found in sairnscape.html: ' + sig);
  const end = html.indexOf(term, at);
  if (end < 0) throw new Error('terminator missing after ' + sig);
  return html.slice(at, end + term.length);
}

// The real queue functions, sliced out of the tracked file. Everything the
// findings turn on is the page's own code; only storage, transport and the
// element are stubbed.
const QUEUE_SRC = [
  grab('function scpLastErrCode(', '\n'),
  grab('function scpLastErrText(', '\n'),
  grab('function scpWriteRefused(', '\n'),
  "var SCP_PENDING_KEY='scp_pending_writes';",
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
].join('\n');

const UI_SRC = [
  grab('function scpUpdateApprovalUI(rec){', '\n}\n'),
  // ADDED 2026-09-21 by hank, when FINDING 1 below was FIXED. scpOpenDesignModal
  // now routes the button through one setter that assigns label, enabled state
  // and handler together, so extracting the modal without the setter throws
  // ReferenceError and this report-only probe stops exiting 0. Added rather
  // than the probe deleted: it is the only runnable reproduction of four
  // findings, two of which are still open, and it now correctly reports
  // FINDING 1 as closed instead of reproducing it.
  grab('function scpSetSendBtn(mode, qid){', '\n}\n'),
  grab('function scpOpenDesignModal(id){', '\n}\n'),
  grab('function scpCloseDesignModal(){', '\n'),
  grab('async function scpSendDesignToQuote(){', '\n}\n'),
].join('\n');

function baseContext(transport) {
  const STORE = {};
  const ctx = {
    console: { warn() {}, error() {}, log() {} },
    setTimeout: setTimeout,
    scpLd(k, d) { return STORE[k] === undefined ? d : JSON.parse(JSON.stringify(STORE[k])); },
    scpSt(k, v) { STORE[k] = JSON.parse(JSON.stringify(v)); return true; },
    scpH(s) { return String(s == null ? '' : s); },
    scpToast(m) { ctx.__toast = m; },
    scpRQuotes() {},
    scpFillCustomerSelects() {},
    scpRenderDesignElemTable() {},
    scpFdate(d) { return String(d); },
    scpDaysFromNow() { return '2026-10-21'; },
    SCP_DW_TYPE_LABELS: { sprinkler: 'Sprinkler' },
    scpLastErr: {},
    scpDwid: null,
    __store: STORE,
    __writes: [],
  };
  ctx.scpDesigns = function () { return ctx.scpLd('scp_designs', []); };
  ctx.scpData = transport(ctx);
  ctx.scpSaveDesignRecord = async function (rec) {
    ctx.scpSt('scp_designs', ctx.scpDesigns().map(function (x) { return x.id === rec.id ? rec : x; }));
    return await ctx.scpData('write', 'scp_designs', rec);
  };
  return ctx;
}

function queueOnly(transport) {
  const ctx = baseContext(transport);
  ctx.__banner = { innerHTML: '', style: { display: 'none' } };
  ctx.scp$ = function (id) { return id === 'scp-pending-banner' ? ctx.__banner : null; };
  vm.createContext(ctx);
  vm.runInContext(QUEUE_SRC, ctx);
  return ctx;
}

function withDesignUI(transport) {
  const ctx = baseContext(transport);
  const els = {
    'scp-pending-banner': { innerHTML: '', style: { display: 'none' } },
    'scp-dw-approval-status': { style: {}, textContent: '' },
    'scp-dw-approval-form': { style: {} },
    'scp-dwcustomer': { value: '' },
    'scp-dwelemtype': { value: 'sprinkler' },
    'scp-dwelemlabel': { value: '' },
    'scp-dwapprover': { value: '' },
    'scp-designmodal': { classList: { add() {}, remove() {} } },
  };
  // The element, with only the three DOM behaviours verified in Chrome above.
  // The inline handler is READ FROM THE FILE, not retyped, so if the markup's
  // onclick ever changes this probe follows it.
  const btnAt = html.indexOf('id="scp-dw-send-quote-btn"');
  const btnHtml = html.slice(html.lastIndexOf('<button', btnAt), html.indexOf('</button>', btnAt) + 9);
  const inline = new RegExp('onclick="([^"]+)"').exec(btnHtml)[1];   // see the note above
  if (inline !== 'scpSendDesignToQuote()') {
    throw new Error('the send button\'s inline handler is no longer scpSendDesignToQuote(): ' + inline);
  }
  const btn = {
    id: 'scp-dw-send-quote-btn',
    disabled: true,
    textContent: 'Send Approved Design to Quoting',
    style: {},
    classList: { add() {}, remove() {} },
    onclick() { return ctx.scpSendDesignToQuote(); },      // (a)
    click() { return this.onclick && this.onclick(); },    // (c)
  };
  els['scp-dw-send-quote-btn'] = btn;
  ctx.scp$ = function (id) { return els[id] || null; };
  ctx.__btn = btn;
  vm.createContext(ctx);
  vm.runInContext(QUEUE_SRC + '\n' + UI_SRC, ctx);
  return ctx;
}

const OFFLINE = (ctx) => async function (action, resource, rec) {
  ctx.__writes.push(resource + ':' + (rec && rec.id));
  ctx.scpLastErr[resource] = { code: 'NETWORK', message: '' };   // no status: nobody looked
  return null;
};
const ACCEPTS = (ctx) => async function (action, resource, rec) {
  ctx.__writes.push(resource + ':' + (rec && rec.id));
  delete ctx.scpLastErr[resource];
  return { ok: true };
};
const Q = (id) => ({ id: id, customer_id: 'C-1', lines: [], status: 'Draft' });

function head(n, t) { console.log('\n=== FINDING ' + n + ': ' + t + '\n'); }

(async function () {

  // ── the press-on (1) precondition, asserted rather than restated ─────────
  console.log('=== PRESS-ON (1): the UPSERT precondition, measured across every scp_ write ===\n');
  const scpWrites = [];
  // BUILT WITH new RegExp RATHER THAN A LITERAL, DELIBERATELY. A regex literal
  // containing an odd number of quote characters desyncs
  // tools/tier_a_review_gate.py's _strip_code_noise -- it does not recognise
  // regex literals, so the `'` inside `[^']` opens a phantom string and every
  // quote after it is mispaired for the rest of the file. That made
  // is_report_only_artefact() answer False on this probe (the process.exit(0)
  // was swallowed) and the push gate demand an obligation for a file that
  // cannot fail. Said out loud in the commit rather than only worked around.
  const re = new RegExp('rest\\(\'(scp_[a-z_]+)\\?(on_conflict=[^\']*)\'', 'g');
  let m;
  while ((m = re.exec(sdData))) {
    const seg = sdData.slice(m.index, m.index + 600);
    scpWrites.push({ table: m[1], key: m[2], merge: /resolution=merge-duplicates/.test(seg) });
  }
  const plain = scpWrites.filter((w) => !w.merge);
  console.log('  ' + scpWrites.length + ' scp_ table writes, all POSTed with on_conflict='
    + '(license_hash, <id>); ' + plain.length + ' without resolution=merge-duplicates.');
  console.log('  scp_quotes  : ' + JSON.stringify(scpWrites.filter((w) => w.table === 'scp_quotes')));
  console.log('  scp_designs : ' + JSON.stringify(scpWrites.filter((w) => w.table === 'scp_designs')));
  const q1 = /create table if not exists public\.scp_quotes \([\s\S]*?unique \(license_hash, quote_id\)/.test(
    fs.readFileSync(path.join(ROOT, 'sql', 'sairnscape_data_schema.sql'), 'utf8'));
  const d1 = /create table if not exists public\.scp_designs \([\s\S]*?unique \(license_hash, design_id\)/.test(
    fs.readFileSync(path.join(ROOT, 'sql', 'sairnscape_data_schema_phase2.sql'), 'utf8'));
  console.log('  the on_conflict targets are real unique constraints: scp_quotes=' + q1
    + ', scp_designs=' + d1 + '  (a missing one would 42P10 at runtime, not merge)');
  if (plain.length || !q1 || !d1) {
    console.log('  ** the precondition no longer holds -- the queue would DOUBLE rows on retry **');
  } else {
    console.log('  press-on (1) HOLDS.');
  }

  // ── FINDING 1 ───────────────────────────────────────────────────────────
  head(1, 'the send button is rebound to the queue flush PERMANENTLY, so a later\n'
    + '            design shows "Send Approved Design to Quoting" and runs the flush');
  {
    const ctx = withDesignUI(OFFLINE);
    const btn = ctx.__btn;
    ctx.scpSt('scp_designs', [
      { id: 'DW-1', customer_id: 'C-1', elements: [{ type: 'sprinkler', label: 'front bed' }], approved: true, approved_by: 'Homeowner A', approved_at: '2026-09-20', quote_id: null },
      { id: 'DW-2', customer_id: 'C-1', elements: [{ type: 'sprinkler', label: 'side strip' }], approved: true, approved_by: 'Homeowner B', approved_at: '2026-09-20', quote_id: null },
    ]);
    ctx.scpSt('scp_quotes', []);

    ctx.scpOpenDesignModal('DW-1');
    console.log('  open DW-1              label=' + JSON.stringify(btn.textContent) + ' disabled=' + btn.disabled);
    await ctx.scpSendDesignToQuote();
    const rebound = () => btn.onclick.toString().indexOf('scpFlushAndReport') >= 0;
    console.log('  send, server offline   label=' + JSON.stringify(btn.textContent)
      + ' disabled=' + btn.disabled + ' -> onclick is the flush: ' + rebound());
    ctx.scpCloseDesignModal();
    ctx.scpOpenDesignModal('DW-2');
    console.log('  reopen on DW-2         label=' + JSON.stringify(btn.textContent)
      + ' disabled=' + btn.disabled + ' -> onclick is STILL the flush: ' + rebound());

    ctx.scpData = ACCEPTS(ctx);           // the connection is back
    ctx.__writes.length = 0;
    btn.click();                          // the user presses what reads as Send
    await new Promise((r) => setTimeout(r, 30));
    const d2 = ctx.scpDesigns().find((x) => x.id === 'DW-2');
    console.log('  press it               writes=' + JSON.stringify(ctx.__writes));
    console.log('                         DW-2.quote_id=' + JSON.stringify(d2.quote_id)
      + '  quotes on device=' + JSON.stringify(ctx.scpLd('scp_quotes', []).map((q) => q.id)));
    console.log('                         toast=' + JSON.stringify(ctx.__toast));
    if (!d2.quote_id) {
      findings++;
      console.log(`
  sairnscape.html:3197 rebinds the shared button with
  \`sendBtn.onclick=function(){scpFlushAndReport();};\` inside the failure
  branch, and NOTHING EVER PUTS IT BACK. #scp-dw-send-quote-btn is a single
  static element (sairnscape.html:1530) shared by every design walk, and
  scpOpenDesignModal (:2935-2937) resets only .disabled and .textContent.

  So after any failed send, every subsequent approved, never-sent design walk
  opens with the correct label "Send Approved Design to Quoting", correctly
  enabled, and pressing it runs the QUEUE FLUSH. The design is never sent, no
  quote is minted, and the toast reports on the OTHER design's upload -- above,
  "2 uploaded" -- so the user is told something succeeded.

  This is press-on (4) answered in the reverse direction from the one asked
  about. The commit worried about a button labelled "Retry upload" wired to the
  send; what exists is a button labelled "Send" wired to the retry. It is also
  the same defect class 4f674484 was written to remove -- a control that does
  not do what its label says -- one layer further out, and the failure is now
  silent rather than contradictory.

  Section 4 of tests/sairnscape_outbound_queue.js cannot see it: all four of its
  assertions are regexes over the source of the branch. The rebinding is
  correct AT the branch; the defect is what happens afterwards, and only driving
  the button shows it. Note that \`btn.getAttribute('onclick')\` still reads
  "scpSendDesignToQuote()" in real Chrome after the rebind, so an inspector does
  not show it either.

  SUGGESTED FIX, one line, in scpOpenDesignModal beside the two resets already
  there: \`sendBtn.onclick=function(){scpSendDesignToQuote();};\` -- so opening a
  design restores the handler the same way it restores the label. Setting the
  handler in BOTH places keeps the two in step; setting it in neither is what
  leaves them free to disagree.`);
    } else {
      console.log('  CLOSED -- opening a design now restores the send handler.');
    }
  }

  // ── FINDING 2 ───────────────────────────────────────────────────────────
  head(2, 'a row the queue ACCEPTED is erased if a flush was already running --\n'
    + '            scpPendingAdd returns true and the record is gone');
  {
    let release;
    const hang = new Promise((r) => { release = r; });
    const ctx = queueOnly((c) => async function (action, resource, rec) {
      c.__writes.push(resource + ':' + (rec && rec.id));
      await hang;                                   // the SCP_FETCH_TIMEOUT_MS window
      c.scpLastErr[resource] = { code: 'NETWORK', message: '' };
      return null;
    });
    ctx.scpLastErr['scp_quotes'] = { code: 'NETWORK', message: '' };
    ctx.scpPendingAdd('scp_quotes', Q('Q-OLD'));
    console.log('  queue before         ' + JSON.stringify(ctx.scpPendingAll().map((p) => p.rec.id)));
    const flushing = ctx.scpFlushAndReport(true);   // boot fires this UN-AWAITED, :2624
    await new Promise((r) => setTimeout(r, 10));
    const accepted = ctx.scpPendingAdd('scp_quotes', Q('Q-NEW'));   // the user sends
    console.log('  mid-flight add       scpPendingAdd -> ' + accepted
      + '   queue=' + JSON.stringify(ctx.scpPendingAll().map((p) => p.rec.id)));
    release();
    await flushing;
    const after = ctx.scpPendingAll().map((p) => p.rec.id);
    console.log('  after the flush      ' + JSON.stringify(after)
      + '   banner=' + (ctx.__banner.style.display === 'none' ? 'HIDDEN' : 'visible'));
    if (after.indexOf('Q-NEW') < 0) {
      findings++;
      const t = /SCP_FETCH_TIMEOUT_MS\s*=\s*(\d+)/.exec(html)[1];
      console.log(`
  scpFlushPending (:3070) snapshots the queue at entry -- \`var q=scpPendingAll()\`
  -- and writes \`keep\`, built from that snapshot, at exit (:3103). \`_scpFlushing\`
  guards a second FLUSH; nothing guards a concurrent scpPendingAdd. So any row
  queued while a flush is in flight is overwritten and lost.

  The window is real and is opened by the app itself: boot calls
  \`scpFlushAndReport(true)\` UN-AWAITED at sairnscape.html:2624, the
  \`online\` listener does the same at :2625, and the banner's own "Try uploading
  now" button is never disabled while a flush runs. Each hung attempt can take
  SCP_FETCH_TIMEOUT_MS = ${t}ms, and the loop awaits once PER pending row, so
  with three queued rows the window is around ${(Number(t) * 3) / 1000}s of a
  page the user is actively using.

  WHAT MAKES THIS THE WORST OF THE THREE: scpPendingAdd returned TRUE, so
  scpSendDesignToQuote took the \`quoteQueued\` branch and told the user "It is
  queued and will upload when a connection returns." The record is then in
  localStorage under scp_quotes and NOT in the queue, and the banner -- if the
  flush drained everything else -- reports nothing waiting. That is a silent
  loss of the exact promise the feature exists to make, and scpSt()'s return
  being read (which this queue is careful about) does not help: the write
  succeeded and was undone afterwards.

  SUGGESTED FIX, and it is small: re-read the queue at the END of the flush
  instead of trusting the snapshot -- merge by (resource, id), the key
  scpPendingAdd already uses, keeping any row that is not in the snapshot and
  dropping the ones just sent. An alternative that is one line but weaker is to
  have scpPendingAdd refuse while \`_scpFlushing\` is true and return false, which
  at least makes the toast tell the truth ("could NOT be queued") rather than
  making a promise that has already been broken.`);
    } else {
      console.log('  CLOSED -- a row queued during a flush now survives it.');
    }
  }

  // ── FINDING 3 ───────────────────────────────────────────────────────────
  head(3, 'every retryable server failure is filed as a PERMANENT refusal --\n'
    + '            including 502 "try again" and 503 NOT_PROVISIONED');
  {
    const cases = [
      { status: 429, code: 'TOO_MANY_INVALID_KEYS', message: 'Too many failed license attempts from this address. Wait 900 seconds and try again.', where: 'api/sd-data.js:513' },
      { status: 502, code: 'HTTP_502', message: 'Data store error — try again', where: 'api/sd-data.js:12525, upstream()' },
      { status: 503, code: 'NOT_PROVISIONED', message: 'SAIRNscape data tables are not set up yet — run sql/sairnscape_data_schema.sql in Supabase first.', where: 'api/sd-data.js:3503' },
      { status: 500, code: 'HTTP_500', message: 'Server configuration error — contact support', where: 'api/sd-data.js:527' },
      { status: 400, code: 'BAD_ROW', message: 'quote payload.id and payload.customer_id are required', where: 'api/sd-data.js:3497 -- a GENUINE refusal, for contrast' },
    ];
    let misfiled = 0;
    for (const c of cases) {
      const ctx = queueOnly((cc) => async function (action, resource) {
        cc.scpLastErr[resource] = { status: c.status, code: c.code, message: c.message };
        return null;
      });
      ctx.scpPendingAdd('scp_quotes', Q('Q-' + c.status));
      const r = await ctx.scpFlushPending();
      ctx.scpRenderPendingBanner();
      const refused = r.refused === 1;
      console.log('  ' + c.status + ' ' + c.code + ' -> '
        + (refused ? 'REFUSED, never retried' : 'kept pending') + '   [' + c.where + ']');
      if (refused && c.status >= 500) misfiled++;
      if (refused && c.status === 429) misfiled++;
      if (refused && /try again|not set up/i.test(c.message)) {
        console.log('       banner: '
          + ctx.__banner.innerHTML.replace(/<[^>]*>/g, '').replace(/\s+/g, ' ')
            .split('Only ')[0].trim());
      }
    }
    if (misfiled) {
      findings++;
      console.log(`
  scpWriteRefused is \`!!(e && e.status)\` (:2149). The comment three lines above
  it states the rule as "A 4xx, or a 200 carrying ok:false" -- which is the right
  rule -- but the code says "any status at all", and api/sd-data.js can answer a
  scp_quotes write with 429, 500, 502 and 503 on paths that have nothing to do
  with the row. Every one of them is filed as a permanent refusal: the row stops
  being pending, is never retried, and the banner tells the user the server
  refused it.

  Two of the messages the banner then prints END IN "try again", inside a
  sentence that says the row will not be retried. That is the same
  control-contradicts-the-text-beside-it defect 4f674484 was written to remove,
  relocated into the banner the same commit added.

  503 NOT_PROVISIONED is the worst of them in practice: it is what a brand-new
  licence gets until sql/sairnscape_data_schema.sql has been run, so the FIRST
  quotes a new customer creates are stranded as permanently refused, and running
  the schema afterwards does not bring them back -- nothing retries a refused
  row and nothing can clear one. A 502 from upstream() is the most likely at
  steady state: it is what the proxy answers for any PostgREST error, including
  a transient one.

  This also reaches the send path, not only the flush: scpSendDesignToQuote
  (:3172-3173) uses the same scpWriteRefused() to decide whether to queue at
  all, so a quote that hits a 502 is never queued in the first place and the
  toast says it "was REFUSED by the server ... and will NOT be retried
  automatically".

  SUGGESTED FIX: make the predicate say what the comment already says --
  \`!!(e && e.status && e.status < 500 && e.status !== 429)\`, i.e. a 4xx other
  than 429, plus the 200/ok:false case which already sets status 200. 401 and
  403 are the judgement call I would leave to the author: the server did look,
  but at the licence rather than the row, and an expired session that resolves
  on re-auth is retryable. Keeping them as refusals is defensible; 429 and 5xx
  are not.`);
    } else {
      console.log('  CLOSED -- retryable statuses now stay pending.');
    }
  }

  // ── FINDING 4, read-verified rather than driven ──────────────────────────
  head(4, 'the one exit from scpData that neither sets nor clears scpLastErr,\n'
    + '            so a stale 4xx can answer for a call the server never saw');
  {
    const seg = html.slice(html.indexOf('async function scpData(action, resource, payload, appId) {'),
      html.indexOf('async function scpData(action, resource, payload, appId) {') + 400);
    const early = /var licKey = scpLd\('scp_lic', null\);\s*\n\s*if \(!licKey\) return null;/.test(seg);
    console.log('  scpData still returns early on a missing licence WITHOUT touching '
      + 'scpLastErr: ' + early);
    if (early) {
      findings++;
      console.log(`
  This is press-on (2), and the answer is that one path does. scpData's three
  other exits are all careful -- a !res.ok sets the status, a 200/ok:false sets
  status 200, a success \`delete\`s the entry, and the catch deliberately records
  a code with NO status so a dead connection cannot read as a judgement. The
  no-licence guard at :2077-2078 predates all of that and was not revisited: it
  returns null and leaves whatever was in scpLastErr[resource] in place.

  So if a write took a 4xx and the licence then becomes unreadable -- a licence
  change (the scp_ wipe at :2494 clears scp_lic), a localStorage read that
  throws, a cleared profile -- the next write for that resource returns null
  with the OLD status still standing, scpWriteRefused() answers true, and the
  row is filed as refused by a server that was never contacted. It is the same
  defect shape the catch's comment names sairndental as having shipped, in the
  one exit the fix did not reach.

  Narrower than the first three: it needs a 4xx followed by a licence
  disappearing, and I have not driven it, because scpData itself is not
  extractable without the fetch layer -- I am reporting it as read, not as
  reproduced. Recorded because it is exactly what press-on (2) asked to be
  checked and the answer is not a clean yes.

  SUGGESTED FIX, one line: \`if (!licKey) { delete scpLastErr[resource]; return
  null; }\` -- nobody looked, so nothing should claim they did.`);
    } else {
      console.log('  CLOSED -- the no-licence exit now clears the recorded status.');
    }
  }

  // ── not findings ─────────────────────────────────────────────────────────
  console.log('\n=== CHECKED AND CORRECT ===');
  console.log(`  * press-on (1): every scp_ write is an upsert on (license_hash, <id>) with
    merge-duplicates, and both on_conflict targets are real unique constraints.
    The queue cannot double a row whose response was lost.
  * press-on (5): SCP_QUEUED_PATH and SCP_UNQUEUED_QUOTE_PATHS match the file --
    one queued call site, three sibling quote paths named as uncovered. The
    wording cannot be read as covering them.
  * the re-queue key (resource, id) really does replace rather than append, and
    an id-less row is refused, so the queue cannot grow a duplicate.
  * scpSt()'s return is read, so a full localStorage produces "could NOT be
    queued" rather than a promise it cannot keep.
  * the flush stops at the first unreachable row rather than throwing the rest
    of the queue at a dead connection, and _scpFlushing prevents a second
    concurrent flush (it just does not prevent a concurrent ADD -- finding 2).
  * the toast branches are exhaustive over (quote landed, design landed) and
    name which of the two failed, including the both-failed-and-could-not-queue
    case.

  ONE OBSERVATION, not raised as a finding because it is a design gap rather
  than a defect: nothing in the app can ever clear a refused row. There is no
  dismiss, no delete, no edit-and-requeue; "Try uploading now" only touches
  pending rows. One refused row makes the banner permanent for the life of the
  browser profile, which is alarm fatigue on the one banner that matters. It
  becomes urgent if finding 3 stands, since that is what puts rows there
  wrongly.`);

  console.log('\n' + findings + ' finding(s). Report-only: exit 0 by design.');
  process.exit(0);
})();
