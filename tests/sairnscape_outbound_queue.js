// tests/sairnscape_outbound_queue.js
// REQUIREMENT: a quote that did not reach the server leaves the send button
//   PRESSABLE and queued for retry, and a quote the server REFUSED is never
//   retried and never reported as sent
//
// Run:  node tests/sairnscape_outbound_queue.js
//
// ── WHY THIS EXISTS ────────────────────────────────────────────────────────
// scpSendDesignToQuote ran `sendBtn.disabled=true` and
// `sendBtn.textContent='Sent to Quoting (Q-...)'` UNCONDITIONALLY, three lines
// before the branch that decided whether anything had been sent. Both failure
// messages said "try again with a connection" while the only control that would
// retry was disabled and wearing the exact claim the message was retracting.
// Raised reviewing fourth's 2026-09-15 scp_quotes fix: the sentence was
// corrected and the affordance was not. SAIRNscape also had no retry path at
// all, so "it will upload later" was not a promise anything could keep.
//
// ── THE PRECONDITION IS THE LOAD-BEARING ASSERTION, AND IT IS ABOUT THE SERVER
// The queue is only safe because api/sd-data.js's scp_* writes are UPSERTS on
// (license_hash, <id>) with `Prefer: resolution=merge-duplicates`. If one ever
// becomes a plain insert, retrying a row whose response was lost on the way
// back starts DOUBLING it -- silently, and a quote is what a customer is priced
// from. So the contract is asserted HERE, in the suite for the feature that
// depends on it, rather than trusted.
//
// ── AND THE DISTINCTION THE QUEUE RESTS ON ─────────────────────────────────
// scpData used to return one undifferentiated null for every failure, so a 4xx
// refusal and a dead connection were indistinguishable. A queue built on that
// retries a refused row forever and drops a lost one. scpWriteRefused() is the
// distinction, and both directions are driven below.
//
// SCP_HTML points this at a mutated copy so a negative control can prove the
// arms bite without patching the tracked file.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const ROOT = path.join(__dirname, '..');
const html = fs.readFileSync(process.env.SCP_HTML || path.join(ROOT, 'sairnscape.html'), 'utf8')
  .replace(/\r\n/g, '\n');
const sdData = fs.readFileSync(path.join(ROOT, 'api', 'sd-data.js'), 'utf8');

let pass = 0, fail = 0;
function test(name, fn) {
  const r = fn();
  const done = () => { console.log('  ok   ' + name); pass++; };
  const bad = (e) => { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; };
  if (r && typeof r.then === 'function') return r.then(done, bad);
  done();
}
async function run(list) { for (const [n, f] of list) { try { await test(n, f); } catch (e) { /* handled */ } } }
function section(t) { console.log('\n' + t); }

function grab(sig, terminator) {
  const at = html.indexOf(sig);
  assert.ok(at > 0, 'not found in sairnscape.html: ' + sig);
  const end = html.indexOf(terminator, at);
  assert.ok(end > at, 'terminator not found after ' + sig);
  return html.slice(at, end + terminator.length);
}

// ── the harness: real queue functions, stubbed storage and transport ───────
function harness(opts) {
  opts = opts || {};
  const store = {};
  const calls = { writes: [] };
  const ctx = {
    console: { warn() {}, error() {}, log() {} },
    scpLd: (k, d) => (store[k] === undefined ? d : JSON.parse(JSON.stringify(store[k]))),
    scpSt: (k, v) => {
      if (opts.storageFull) return false;
      store[k] = JSON.parse(JSON.stringify(v)); return true;
    },
    scpH: (s) => String(s || ''),
    // A REAL ELEMENT, because the banner arms have to be DRIVEN. With scp$
    // returning null the renderer no-ops and every assertion about it collapses
    // into a grep over the source -- which is exactly how an
    // `if(false)parts.push(...)` sabotage walked past the first version of
    // these arms.
    scp$: (id) => (id === 'scp-pending-banner' ? ctx.__banner : null),
    __banner: { innerHTML: '', style: { display: 'none' } },
    scpToast: (m) => { calls.toast = m; },
    scpRQuotes: () => {},
    scpLastErr: {},
    // The transport. `mode` decides what the server did, per attempt.
    scpData: async (action, resource, rec) => {
      calls.writes.push({ action, resource, id: rec && rec.id });
      const mode = (opts.modes && opts.modes[calls.writes.length - 1]) || opts.mode || 'accepted';
      if (mode === 'accepted') { delete ctx.scpLastErr[resource]; return { ok: true }; }
      if (mode === 'refused') {
        ctx.scpLastErr[resource] = { status: 400, code: 'BAD_ROW', message: 'quote payload.id is required' };
        return null;
      }
      ctx.scpLastErr[resource] = { code: 'NETWORK', message: '' };   // no status -- nobody looked
      return null;
    },
    __store: store, __calls: calls,
  };
  vm.createContext(ctx);
  vm.runInContext([
    grab('function scpLastErrCode(', '\n'),
    grab('function scpLastErrText(', '\n'),
    grab('function scpWriteRefused(', '\n'),
    "var SCP_PENDING_KEY='scp_pending_writes';",
    // PULLED FROM THE PAGE, NOT RESTATED HERE. These were two literals typed
    // into this harness, and a harness that restates a constant cannot notice
    // when the page's copy changes -- which is how the banner claim under test
    // drifted from the code in the first place.
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
  ].join('\n'), ctx);
  return ctx;
}

const Q = (id) => ({ id: id || 'Q-1', customer_id: 'C-1', lines: [], status: 'Draft' });

(async () => {

section('1. THE PRECONDITION -- the server write must be an UPSERT');

await test('scp_quotes writes upsert on (license_hash, quote_id)', () => {
  const at = sdData.indexOf("resource === 'scp_quotes' && action === 'write'");
  assert.ok(at > 0, 'the scp_quotes write branch is gone');
  const seg = sdData.slice(at, at + 1400);
  assert.ok(/on_conflict=license_hash,quote_id/.test(seg),
    'the scp_quotes write is no longer keyed on (license_hash, quote_id) -- a '
    + 'retry would INSERT a second row rather than update the first, and this '
    + 'queue would start doubling quotes');
  assert.ok(/resolution=merge-duplicates/.test(seg),
    'the scp_quotes write no longer merges duplicates');
});

await test('scp_designs writes upsert too -- the queue carries both', () => {
  const at = sdData.indexOf("resource === 'scp_designs' && action === 'write'");
  assert.ok(at > 0, 'the scp_designs write branch is gone');
  const seg = sdData.slice(at, at + 1400);
  assert.ok(/on_conflict=license_hash,/.test(seg) && /resolution=merge-duplicates/.test(seg),
    'scp_designs is no longer an upsert');
});

section('2. REFUSED IS NOT UNREACHABLE');

await test('a 4xx is a refusal; a dead connection is not', () => {
  const c = harness({ mode: 'refused' });
  c.scpLastErr['scp_quotes'] = { status: 400, code: 'BAD_ROW', message: 'nope' };
  assert.strictEqual(c.scpWriteRefused('scp_quotes'), true);
  c.scpLastErr['scp_quotes'] = { code: 'NETWORK', message: '' };
  assert.strictEqual(c.scpWriteRefused('scp_quotes'), false,
    'a network failure was read as a server judgement -- a refused row would be '
    + 'retried forever and a lost row dropped');
});

await test('scpLastErrText is silent when nobody looked', () => {
  const c = harness({});
  c.scpLastErr['scp_quotes'] = { code: 'NETWORK', message: '' };
  assert.strictEqual(c.scpLastErrText('scp_quotes'), '',
    'a message with no status would read as a fresh server sentence');
});

section('3. THE QUEUE');

await test('an UNREACHABLE quote is queued', () => {
  const c = harness({ mode: 'offline' });
  c.scpLastErr['scp_quotes'] = { code: 'NETWORK', message: '' };
  assert.strictEqual(c.scpPendingAdd('scp_quotes', Q()), true);
  assert.strictEqual(c.scpPendingCount(), 1);
});

await test('re-queueing the SAME id REPLACES rather than appends', () => {
  const c = harness({ mode: 'offline' });
  c.scpPendingAdd('scp_quotes', Q('Q-9'));
  c.scpPendingAdd('scp_quotes', Q('Q-9'));
  assert.strictEqual(c.scpPendingCount(), 1,
    'the queue would upload the same quote twice -- reintroducing the '
    + 'duplication it exists to stop');
});

await test('a record with no id is refused by the queue', () => {
  const c = harness({});
  assert.strictEqual(c.scpPendingAdd('scp_quotes', { customer_id: 'C-1' }), false,
    'an id-less row cannot be keyed, so it could never replace and would '
    + 'accumulate on every attempt');
});

await test('a full localStorage makes the promise FALSE and says so', () => {
  const c = harness({ storageFull: true });
  assert.strictEqual(c.scpPendingAdd('scp_quotes', Q()), false,
    '"it will upload when you reconnect" was promised over a store that '
    + 'refused the write');
});

await test('a flush that lands clears the queue', async () => {
  const c = harness({ mode: 'accepted' });
  c.scpPendingAdd('scp_quotes', Q('Q-2'));
  const r = await c.scpFlushPending();
  assert.strictEqual(r.sent, 1);
  assert.strictEqual(r.left, 0);
  assert.strictEqual(c.scpPendingCount(), 0);
});

await test('a REFUSED row stops being pending and is KEPT as refused', async () => {
  const c = harness({ mode: 'refused' });
  c.scpPendingAdd('scp_quotes', Q('Q-3'));
  const r = await c.scpFlushPending();
  assert.strictEqual(r.refused, 1);
  assert.strictEqual(c.scpPendingCount(), 0, 'a refused row is still being retried');
  assert.strictEqual(c.scpRefusedAll().length, 1, 'a refused row was silently dropped');
  assert.ok(/required|nope|not accept/.test(c.scpRefusedAll()[0].refused_message),
    'the refusal carries no reason');
});

await test('an UNREACHABLE row stays pending and the flush STOPS there', async () => {
  const c = harness({ mode: 'offline' });
  c.scpPendingAdd('scp_quotes', Q('Q-4'));
  c.scpPendingAdd('scp_designs', { id: 'D-1' });
  const r = await c.scpFlushPending();
  assert.strictEqual(r.sent, 0);
  assert.strictEqual(r.left, 2, 'the flush kept going against a connection that is down');
  assert.strictEqual(c.__calls.writes.length, 1,
    'it threw the whole queue at a dead connection instead of stopping');
});

await test('a re-entrant flush does not double-send', async () => {
  const c = harness({ mode: 'accepted' });
  c.scpPendingAdd('scp_quotes', Q('Q-5'));
  const [a, b] = await Promise.all([c.scpFlushPending(), c.scpFlushPending()]);
  assert.strictEqual(a.sent + b.sent, 1, 'two concurrent flushes both sent the row');
});

section('4. THE BUTTON FOLLOWS THE OUTCOME');

await test('success disables it; every failure leaves it PRESSABLE', () => {
  const src = grab('async function scpSendDesignToQuote(){', '\n}\n');
  assert.ok(/var landed=quoteSynced&&syncResult;/.test(src),
    'nothing computes whether BOTH writes landed');
  assert.ok(/if\(landed\)\{[\s\S]{0,200}sendBtn\.disabled=true/.test(src),
    'the button is not disabled on the success path');
  assert.ok(/\}else\{[\s\S]{0,400}sendBtn\.disabled=false/.test(src),
    'a failed send still disables the button, so the toast tells the user to '
    + 'retry with no control that can');
  assert.ok(/Retry upload/.test(src), 'the failed state is not labelled for retry');
  // The original defect exactly: an unconditional disable before the branch.
  const beforeBranch = src.slice(0, src.indexOf('var landed='));
  assert.ok(!/sendBtn\.disabled=true/.test(beforeBranch),
    'the button is disabled BEFORE the outcome is known -- the original defect');
});

await test('a failed send queues, and the message says which state it is in', () => {
  const src = grab('async function scpSendDesignToQuote(){', '\n}\n');
  assert.ok(/scpPendingAdd\('scp_quotes',qrec\)/.test(src), 'the quote is not queued');
  assert.ok(/scpPendingAdd\('scp_designs',rec\)/.test(src), 'the design is not queued');
  // THE GUARD HAS TO BE ON THE QUEUE EXPRESSION ITSELF. The first version of
  // this arm asked only whether scpWriteRefused appeared ANYWHERE in the
  // function -- and it still does, on the `quoteRefused` line -- so deleting it
  // from the queue condition left the arm GREEN while a refused quote went into
  // a queue that would retry it forever. Found by sabotage, not by review.
  assert.ok(/var quoteQueued=\(!quoteSynced&&!scpWriteRefused\('scp_quotes'\)\)\?scpPendingAdd/.test(src),
    'the queue condition does not exclude a REFUSED quote, so a row the server '
    + 'has already rejected would be retried until the queue never drains');
  assert.ok(/var designQueued=\(!syncResult&&!scpWriteRefused\('scp_designs'\)\)\?scpPendingAdd/.test(src),
    'the design queue condition does not exclude a refusal either');
  assert.ok(/could NOT be queued/.test(src),
    'a queue write that itself failed is reported as queued');
});

section('5. THE BANNER CANNOT IMPLY MORE COVERAGE THAN EXISTS');

// ── THE BANNER SHIPPED OVERSTATING ITS COVERAGE, AND THIS IS THE ARM THAT
// ── WOULD HAVE CAUGHT IT (corrected 2026-09-18) ──────────────────────────
// The first version said "Queued writes cover scp_quotes, scp_designs only" and
// the arm asserted exactly that string, so the suite agreed with the claim
// instead of checking it. Coverage is per CALL SITE: scp_quotes is written at
// four sites and one is queued. A resource-level sentence told a user that the
// irrigation and water-feature "send to Quoting" buttons -- the same action from
// a different panel -- were protected. They are not.
//
// So this arm no longer asks whether the banner says a particular thing. It
// asks whether what the banner says MATCHES THE FILE, and the count arms below
// are what make that answer move when the code does.
await test('the banner names the covered CALL SITE, not a resource -- RENDERED', () => {
  const c = harness({});
  assert.strictEqual(typeof c.scpPendingCoverage(), 'string',
    'coverage is still expressed as a list of resources, which cannot be true '
    + 'while one of those resources has unqueued write sites');
  c.scpPendingAdd('scp_quotes', Q('Q-B1'));
  c.scpRenderPendingBanner();
  const out = c.__banner.innerHTML;
  assert.ok(/Design Walk/.test(out), 'the rendered banner does not name the queued path: ' + out);
  assert.ok(!/cover scp_quotes/.test(out),
    'the banner still makes a resource-level claim: ' + out);
  assert.ok(/Send Irrigation Zone to Quoting/.test(out) && /Send Water Feature to Quoting/.test(out)
    && /Save Quote/.test(out),
    'the three UNQUEUED quote paths are not named, so "other writes" is '
    + 'something no user can act on: ' + out);
  assert.ok(/1 record\(s\) are on this device only/.test(out), 'no count rendered: ' + out);
});

// ── THE COUNTS, PINNED AGAINST THE REAL FILE ─────────────────────────────
// These are what force the sentence above to be re-read. A new
// scpData('write', ...) site, or a newly queued one, moves a number here and
// turns this suite RED rather than letting the banner quietly outgrow its own
// claim -- which is exactly what happened between writing it and checking it.
await test('EXACTLY 18 write sites and EXACTLY 2 are queued', () => {
  const sites = html.match(/scpData\('write','[a-z_]+'/g) || [];
  // One of the matches is inside a comment recording the original defect.
  const inComment = (html.match(/\/\/ This was `scpData\('write','scp_quotes'/g) || []).length;
  const real = sites.length - inComment;
  assert.strictEqual(real, 18,
    'the number of scpData write sites changed to ' + real + '. Read them, decide '
    + 'whether the new one needs the queue, and update the banner sentence -- do '
    + 'not just raise this number.');
  const queued = (html.match(/scpPendingAdd\('scp_[a-z_]+'/g) || []).length;
  assert.strictEqual(queued, 2,
    'the number of queued call sites changed to ' + queued + '. The banner names '
    + 'ONE path; if that is no longer true it has to say so.');
});

await test('the three sibling quote paths are still UNQUEUED -- the banner says they are', () => {
  // If one of these ever gets the queue, the banner becomes wrong in the
  // opposite direction: it would be telling a user their quote is unprotected
  // when it is not. Both directions matter.
  ['scpSaveQuote', 'scpSendIrrZoneToQuote', 'scpSendWfToQuote'].forEach((fn) => {
    const at = html.indexOf('async function ' + fn);
    assert.ok(at > 0, fn + ' is gone -- the banner names it and it must exist');
    const end = html.indexOf('\n}\n', at);
    const body = html.slice(at, end);
    assert.ok(/scpData\('write','scp_quotes'/.test(body), fn + ' no longer writes a quote');
    assert.ok(!/scpPendingAdd/.test(body),
      fn + ' IS now queued, so the banner listing it as unqueued is wrong');
  });
});

await test('and the ONE queued path really is the Design Walk send', () => {
  const at = html.indexOf('async function scpSendDesignToQuote');
  const body = html.slice(at, html.indexOf('\n}\n', at));
  assert.ok(/scpPendingAdd\('scp_quotes',qrec\)/.test(body),
    'the path the banner names as covered does not queue its quote');
});

await test('a REFUSED entry is named in the banner, with its reason', async () => {
  const c = harness({ mode: 'refused' });
  c.scpPendingAdd('scp_quotes', Q('Q-B2'));
  await c.scpFlushPending();
  c.scpRenderPendingBanner();
  const out = c.__banner.innerHTML;
  assert.ok(/REFUSED by the server/.test(out), 'a refused row is invisible: ' + out);
  assert.ok(/Q-B2/.test(out), 'the refused row is not named: ' + out);
});

await test('it is hidden when there is nothing to say -- DRIVEN', () => {
  const c = harness({});
  c.__banner.style.display = '';
  c.__banner.innerHTML = 'stale';
  c.scpRenderPendingBanner();
  assert.strictEqual(c.__banner.style.display, 'none',
    'a banner that is always visible is one nobody reads');
  assert.strictEqual(c.__banner.innerHTML, '', 'stale banner content survived');
});

console.log('\n' + (fail === 0
  ? 'ALL ' + pass + ' SAIRNSCAPE QUEUE ASSERTIONS PASS'
  : pass + ' passed, ' + fail + ' FAILED'));
process.exit(fail === 0 ? 0 : 1);

})();
