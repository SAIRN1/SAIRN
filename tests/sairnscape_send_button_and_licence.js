// tests/sairnscape_send_button_and_licence.js
//
// REQUIREMENT: a write that nobody looked at is never reported or treated as a
//   server refusal, and the send button's label, enabled state and handler
//   always agree about which design they belong to.
//
// Run:  node tests/sairnscape_send_button_and_licence.js
//
// ── WHY THIS EXISTS ────────────────────────────────────────────────────────
// Two HIGH findings from the independent review of the scp_quotes outbound
// queue (4f674484 + 9cfc8eec, CC), reached independently by two reviewers from
// opposite directions and fixed 2026-09-21. This is the STANDING GUARD on both
// fixes -- distinct from the review probes, which are report-only snapshots of
// the defects and exit 0 by design. This one FAILS.
//
// FINDING A -- scpData's no-licence guard returned null WITHOUT touching
//   scpLastErr, so after any real 4xx on the same resource a later call with no
//   licence inherited the old status and scpWriteRefused() answered TRUE for a
//   call the server never saw. scpSendDesignToQuote branches on that predicate,
//   so the row was NOT QUEUED, the toast quoted an unrelated row's reason as a
//   server judgement, and a queued row was marked 'refused' and never retried.
//
// FINDING B -- #scp-dw-send-quote-btn is ONE static element shared by every
//   design walk. The failure branch rebound `.onclick` to the queue flush and
//   nothing put it back, while scpOpenDesignModal restored only `.disabled` and
//   `.textContent`. After any failed send, every later approved-and-unsent
//   design opened with the right label, correctly enabled, and pressing it ran
//   the flush -- no quote minted for that design, no error, and a toast about a
//   different record.
//
// ── IT DRIVES THE REAL FUNCTIONS, NOT THEIR SOURCE TEXT ───────────────────
// Both defects are invisible to a regex over one function by construction:
// FINDING A lives in the part of scpData that cc's own harness replaces with a
// stub, and FINDING B is a property of a DOM node ACROSS two functions. The
// suite that shipped with the queue is 20/20 green on both defects. So this
// loads the real scpData and the real modal/send/approve functions into a vm
// and presses the button.
//
// ── THE ASSERTIONS ARE ABOUT BEHAVIOUR, NOT ABOUT THE FIX ────────────────
// Deliberately. `scpSetSendBtn` is the shape the fix happens to take; the
// requirement is that the three properties agree. An arm asserting the setter
// EXISTS would pass a setter nobody calls, which is the class of assertion
// sabotage has caught on this platform three times.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const ROOT = path.join(__dirname, '..');
const html = fs.readFileSync(process.env.SCP_HTML || path.join(ROOT, 'sairnscape.html'), 'utf8')
  .replace(/\r\n/g, '\n');

let pass = 0, fail = 0;
async function test(name, fn) {
  try { await fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('\n' + t); }

function grab(sig, terminator) {
  const at = html.indexOf(sig);
  assert.ok(at > 0, 'not found in sairnscape.html: ' + sig);
  const n = html.split(sig).length - 1;
  assert.strictEqual(n, 1, 'anchor is NOT UNIQUE (' + n + ' hits), refusing to guess: ' + sig);
  const end = html.indexOf(terminator, at);
  assert.ok(end > at, 'terminator not found after ' + sig);
  return html.slice(at, end + terminator.length);
}

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
    grab('function scpSetSendBtn(mode, qid){', '\n}\n'),
    grab('function scpOpenDesignModal(id){', '\n}\n'),
    grab('async function scpApproveDesign(){', '\n}\n'),
    grab('async function scpSendDesignToQuote(){', '\n}\n'),
    'var scpDwid=null;'
  ].join('\n');
  vm.runInContext(src, ctx);
  return ctx;
}

// The handlers do not return their promises, so a click has to be drained.
async function drain() { for (let i = 0; i < 40; i++) await Promise.resolve(); }

function designs() {
  return [
    { id: 'DW-1', customer_id: 'C-1', elements: [{ type: 'sprinkler', label: 'front' }],
      approved: true, approved_by: 'A', approved_at: '2026-09-20', quote_id: null },
    { id: 'DW-2', customer_id: 'C-2', elements: [{ type: 'sprinkler', label: 'back' }],
      approved: true, approved_by: 'B', approved_at: '2026-09-20', quote_id: null },
    { id: 'DW-3', customer_id: 'C-3', elements: [],
      approved: false, approved_by: '', approved_at: '', quote_id: null }
  ];
}

(async function () {
  console.log('SAIRNSCAPE -- no-licence is not a refusal, and the send button agrees with itself');

  // ════════════════════════════════════════════════════════════════════════
  section('FINDING A -- a call nobody answered is never a refusal');

  await test('after a real 4xx, a NO-LICENCE call does not inherit the refusal', async () => {
    const ctx = harness({
      fetch: async () => ({ ok: false, status: 400,
        json: async () => ({ error: { code: 'BAD_ROW', message: 'customer_id is required' } }) })
    });
    await ctx.scpData('write', 'scp_quotes', { id: 'Q-1' });
    assert.strictEqual(ctx.scpWriteRefused('scp_quotes'), true,
      'a real 400 must still read as a refusal -- the fix must not break the true positive');

    delete ctx.__store.scp_lic;
    const out = await ctx.scpData('write', 'scp_quotes', { id: 'Q-2' });
    assert.strictEqual(out, null, 'a no-licence call still returns null');
    assert.strictEqual(ctx.scpWriteRefused('scp_quotes'), false,
      'a call with NO LICENCE was reported as a SERVER REFUSAL. Nobody looked at '
      + 'the row; the reason still standing is "' + ctx.scpLastErrText('scp_quotes') + '", '
      + 'which came from an unrelated earlier row.');
  });

  await test('and the reason it records is NO_LICENCE, not a borrowed NETWORK', async () => {
    const ctx = harness({});
    delete ctx.__store.scp_lic;
    await ctx.scpData('write', 'scp_quotes', { id: 'Q-1' });
    assert.strictEqual(ctx.scpLastErrCode('scp_quotes'), 'NO_LICENCE',
      'scpPendingAdd labels the queued row from this code. `delete` would also '
      + 'clear the refusal but file a no-licence failure as NETWORK, which is a '
      + 'different thing to tell somebody. Got: '
      + JSON.stringify(ctx.scpLastErrCode('scp_quotes')));
  });

  await test('a timeout after a 4xx does not inherit it either (the catch, unchanged)', async () => {
    const ctx = harness({});
    ctx.scpLastErr['scp_quotes'] = { status: 400, code: 'BAD_ROW', message: 'old' };
    await ctx.scpData('write', 'scp_quotes', { id: 'Q-1' });  // the default fetch throws
    assert.strictEqual(ctx.scpWriteRefused('scp_quotes'), false,
      'the catch must still clear the status -- this arm exists so the fix to the '
      + 'licence guard cannot be mistaken for the catch already covering it');
  });

  await test('the SEND path queues instead of refusing when the licence is gone', async () => {
    const ctx = harness({ store: { scp_designs: JSON.stringify(designs()) } });
    // seed a real refusal on scp_quotes first, then remove the licence
    ctx.scpLastErr['scp_quotes'] = { status: 400, code: 'BAD_ROW', message: 'customer_id is required' };
    delete ctx.__store.scp_lic;
    ctx.scpOpenDesignModal('DW-1');
    await ctx.scpSendDesignToQuote();
    assert.strictEqual(ctx.scpPendingCount(), 2,
      'expected the quote AND the design to be queued; got ' + ctx.scpPendingCount()
      + ' pending and ' + ctx.scpRefusedAll().length + ' refused. A no-licence send '
      + 'was classified as a refusal, so the retry path was skipped entirely.');
    assert.strictEqual(ctx.scpRefusedAll().length, 0, 'nothing may be filed as refused');
    assert.ok(!/REFUSED/.test(ctx.__toasts.join(' ')),
      'the toast claimed a server refusal: ' + JSON.stringify(ctx.__toasts));
  });

  // ════════════════════════════════════════════════════════════════════════
  section('FINDING B -- the button\'s label, enabled state and handler always agree');

  await test('a failed send leaves DW-1 on Retry, wired to the flush', async () => {
    const ctx = harness({ store: { scp_designs: JSON.stringify(designs()) } });
    ctx.scpOpenDesignModal('DW-1');
    const b = ctx.scp$('scp-dw-send-quote-btn');
    await ctx.scpSendDesignToQuote();
    assert.ok(/^Retry upload \(/.test(b.textContent),
      'expected a Retry label after a failed send, got ' + JSON.stringify(b.textContent));
    assert.strictEqual(b.disabled, false, 'the retry control must be pressable');
    // ── THIS ASSERTION WAS TOO WEAK AND SABOTAGE CAUGHT IT ────────────────
    // It was `assert.ok(ctx.__toasts.length)`. A mutation that set the RETRY
    // LABEL and left the handler on SEND survived: pressing it hits
    // scpSendDesignToQuote's `rec.quote_id` guard, which toasts "Already sent
    // to Quoting", so a toast exists and the arm passed. That is the same
    // existence-assertion shape this suite exists to replace -- caught here
    // only because the arm was mutated on purpose.
    ctx.__toasts.length = 0;
    const before = ctx.scpPendingCount();
    b.onclick(); await drain();
    const said = ctx.__toasts.join(' | ');
    assert.ok(/waiting|uploaded|REFUSED|Nothing/.test(said),
      'pressing "' + b.textContent + '" did not run the flush. It said '
      + JSON.stringify(said) + ' -- the label says retry and the handler does '
      + 'something else, which is the contradiction this whole fix removes.');
    assert.ok(!/Already sent/.test(said),
      'pressing Retry reached scpSendDesignToQuote\'s already-sent guard, so the '
      + 'handler is the SEND path wearing a RETRY label: ' + JSON.stringify(said));
    assert.strictEqual(ctx.scpPendingCount(), before,
      'the flush ran against a dead connection, so the pending count must not move');
  });

  await test('opening a DIFFERENT approved design re-arms SEND, not the flush', async () => {
    const ctx = harness({ store: { scp_designs: JSON.stringify(designs()) } });
    ctx.scpOpenDesignModal('DW-1');
    const b = ctx.scp$('scp-dw-send-quote-btn');
    await ctx.scpSendDesignToQuote();          // fails: network is down

    ctx.scpDwid = null;
    ctx.scpOpenDesignModal('DW-2');
    assert.strictEqual(b.textContent, 'Send Approved Design to Quoting',
      'DW-2 opened with the wrong label: ' + JSON.stringify(b.textContent));
    assert.strictEqual(b.disabled, false, 'DW-2 is approved and unsent, so SEND must be enabled');

    // THE ASSERTION THAT MATTERS: press it and check DW-2 actually got a quote.
    // Asserting the handler's identity would pass a handler that is the right
    // function bound to the wrong design.
    ctx.__toasts.length = 0;
    b.onclick(); await drain();
    const dw2 = ctx.scpDesigns().find((d) => d.id === 'DW-2');
    assert.ok(dw2 && dw2.quote_id,
      'pressing "Send Approved Design to Quoting" on DW-2 minted NO quote for it. '
      + 'The handler is still the previous design\'s retry: DW-2.quote_id='
      + JSON.stringify(dw2 && dw2.quote_id) + ', toast=' + JSON.stringify(ctx.__toasts));
    const quotes = ctx.scpLd('scp_quotes', []);
    assert.ok(quotes.some((q) => q.customer_id === 'C-2'),
      'no quote was created for DW-2\'s customer. Quotes: '
      + JSON.stringify(quotes.map((q) => q.customer_id)));
  });

  await test('approving a design after a failed send also re-arms SEND', async () => {
    // The SECOND route to the stale handler, via scpApproveDesign rather than
    // the modal. Fixing only scpOpenDesignModal leaves this one open.
    const ctx = harness({ store: { scp_designs: JSON.stringify(designs()) } });
    ctx.scpOpenDesignModal('DW-1');
    const b = ctx.scp$('scp-dw-send-quote-btn');
    await ctx.scpSendDesignToQuote();          // fails, rebinds to the flush

    ctx.scpDwid = 'DW-3';                      // the unapproved one
    ctx.scp$('scp-dwapprover').value = 'Homeowner';
    ctx.scpDesigns();                          // ensure the store is read
    const all = ctx.scpLd('scp_designs', []);
    all.find((d) => d.id === 'DW-3').elements = [{ type: 'sprinkler', label: 'side' }];
    ctx.scpSt('scp_designs', all);
    await ctx.scpApproveDesign();

    assert.strictEqual(b.textContent, 'Send Approved Design to Quoting',
      'after approval the label is ' + JSON.stringify(b.textContent));
    assert.strictEqual(b.disabled, false, 'an approved design must be sendable');
    ctx.__toasts.length = 0;
    b.onclick(); await drain();
    const dw3 = ctx.scpDesigns().find((d) => d.id === 'DW-3');
    assert.ok(dw3 && dw3.quote_id,
      'pressing SEND after approving DW-3 minted no quote for it -- the handler '
      + 'is still DW-1\'s retry. scpApproveDesign re-enabled the button without '
      + 'restoring the handler.');
  });

  await test('a LANDED send disables the button and still leaves a coherent handler', async () => {
    const ctx = harness({
      store: { scp_designs: JSON.stringify(designs()) },
      fetch: async () => ({ ok: true, status: 200, json: async () => ({ ok: true, data: {} }) })
    });
    ctx.scpOpenDesignModal('DW-1');
    const b = ctx.scp$('scp-dw-send-quote-btn');
    await ctx.scpSendDesignToQuote();
    assert.strictEqual(b.disabled, true, 'a landed send must disable the button');
    assert.ok(/^Sent to Quoting \(/.test(b.textContent),
      'landed label is ' + JSON.stringify(b.textContent));
    assert.strictEqual(typeof b.onclick, 'function',
      'even the disabled state must carry a coherent handler -- a null handler '
      + 'restores the inline one on some paths and not others');
  });

  await test('an UNAPPROVED design opens disabled, whatever happened before', async () => {
    const ctx = harness({ store: { scp_designs: JSON.stringify(designs()) } });
    ctx.scpOpenDesignModal('DW-1');
    const b = ctx.scp$('scp-dw-send-quote-btn');
    await ctx.scpSendDesignToQuote();          // fails
    ctx.scpDwid = null;
    ctx.scpOpenDesignModal('DW-3');            // not approved
    assert.strictEqual(b.disabled, true,
      'an unapproved design must not offer a send control');
    assert.strictEqual(b.textContent, 'Send Approved Design to Quoting',
      'label is ' + JSON.stringify(b.textContent));
  });

  await test('an ALREADY-SENT design opens disabled and shows its quote id', async () => {
    const d = designs();
    d[1].quote_id = 'Q-OLD';
    const ctx = harness({ store: { scp_designs: JSON.stringify(d) } });
    ctx.scpOpenDesignModal('DW-1');
    const b = ctx.scp$('scp-dw-send-quote-btn');
    await ctx.scpSendDesignToQuote();          // fails
    ctx.scpDwid = null;
    ctx.scpOpenDesignModal('DW-2');
    assert.strictEqual(b.disabled, true, 'an already-sent design must not be re-sendable');
    assert.strictEqual(b.textContent, 'Sent to Quoting (Q-OLD)',
      'label is ' + JSON.stringify(b.textContent));
  });

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
