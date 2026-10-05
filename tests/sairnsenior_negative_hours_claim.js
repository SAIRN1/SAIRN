// tests/sairnsenior_negative_hours_claim.js
// REQUIREMENT: a sen_visits row whose clock_out_at precedes its clock_in_at must
//   never reach a claim -- visitHours() clamps it to 0 at source rather than
//   returning a negative to its six callers, and generateClaim() REFUSES it
//   outright instead of writing a silent zero-hour claim over a corrupt record
//
// Run:  node tests/sairnsenior_negative_hours_claim.js
//       SEN_HTML=<mutated copy> node tests/sairnsenior_negative_hours_claim.js
//
// ── WHAT WAS WRONG, AND WHY THE FLAG SAT THERE FOR A WEEK ─────────────────
// `visitHours()` had no non-negative guard. `sairnsenior.html` said so itself,
// in a comment beside a DIFFERENT function, ending "Changing visitHours()
// touches claim generation and is its own change, not a line in a sweep fix."
// That was the right call and it is this change.
//
// The flag named three consumers. A re-count before fixing found SIX, and
// FOUR of them were unguarded -- generateClaim (bills it), visitLabourCost (a
// negative COST, which makes a badly-recorded branch look profitable), the
// branch rollup (`r.hours += visitHours(v)`, so one bad row subtracts from a
// branch's total) and the authorisation-gap AI tool (inflates a shortfall and
// would send staff to a client who is not short). A clamp at four call sites
// is four chances to miss the fifth, so it is clamped at source.
//
// ── WHY A CLAMP ALONE WOULD HAVE BEEN THE WORSE FIX ───────────────────────
// 0 is already what "nobody clocked this visit" means. Clamping without more
// would turn a corrupt record into a $0 claim -- which a biller reads as a
// PRICING problem to fix by hand, because that is exactly what a $0 claim
// means everywhere else in this app (see the rate_source note generateClaim
// already writes). The data defect would be laundered into a familiar-looking
// pricing gap at the one screen that could have surfaced it. So the billing
// path gets a predicate that distinguishes the two facts, and refuses.
//
// ── THE SERVER ALREADY REFUSES, AND THAT IS NOT A REASON TO SKIP THIS ─────
// api/_lib/sen-evv-clock.js refuses CLOCK_OUT_BEFORE_IN. It is not the only
// path: `visits()` reads LOCAL storage, which that module never sees, and rows
// written before it existed are not covered by it. Arm D2 pins that reasoning
// to the source so a later reader cannot delete the guard as unreachable
// without first making it true.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const HTML_PATH = process.env.SEN_HTML
  || path.join(__dirname, '..', 'sairnsenior.html');
const html = fs.readFileSync(HTML_PATH, 'utf8').replace(/\r\n/g, '\n');
const { stripComments } = require('./lib/strip_comments.js');
// Same shared stripper, and the same reason tests/sairnsenior_cert_gate.js
// gives: three suites grew three private versions in one day and all three
// were wrong differently.
const codeOnly = stripComments(html);

// ── THE RUNNER IS ASYNC AND THAT IS NOT INCIDENTAL ───────────────────────
// generateClaim is `async`. A synchronous runner -- `try { fn() } catch`,
// which is the shape every other suite in this directory uses -- returns
// BEFORE an async arm's assertions run, counts it a pass, and turns a failure
// into an unhandled rejection the summary never sees. Written that way once in
// this file's first draft and caught by running it against a deliberately
// broken guard, which still printed all-green. Arms are queued and AWAITED.
// THE AWAIT IS NOW ASSERTED, NOT JUST COMMENTED (2026-10-05). The paragraph
// above was the whole defence against a regression to `try { fn() } catch`,
// and a comment does not fail. The loop is extracted so section E can drive it
// with SYNTHETIC arms -- a passing one, a sync-throwing one, and an
// async-rejecting one -- and assert the tally. A sync runner scores the third
// as a pass, which is exactly what section E refuses.
const QUEUE = [];
let pass = 0, fail = 0;
function test(name, fn) { QUEUE.push([name, fn]); }
function section(t) { QUEUE.push([t, null]); }

async function runQueue(queue, log) {
  let p = 0, f = 0;
  for (const [name, fn] of queue) {
    if (!fn) { log('\n' + name); continue; }
    try { await fn(); log('  ok   ' + name); p++; }
    catch (e) { log('  FAIL ' + name + '\n       ' + e.message); f++; }
  }
  return { pass: p, fail: f };
}

async function run() {
  const r = await runQueue(QUEUE, (s) => console.log(s));
  pass = r.pass; fail = r.fail;
}

function grab(sig, terminator) {
  const at = html.indexOf(sig);
  assert.ok(at > 0, 'not found in ' + path.basename(HTML_PATH) + ': ' + sig);
  const end = html.indexOf(terminator, at);
  assert.ok(end > at, 'terminator not found after ' + sig);
  return html.slice(at, end + terminator.length);
}

// ── The world generateClaim runs in ───────────────────────────────────────
// Everything it calls that is NOT under test is stubbed to the simplest thing
// that lets the real control flow run. The three functions under test are
// EXTRACTED from the app, never reimplemented -- a reimplementation would test
// this file's idea of the guard rather than the shipped one.
function build(visitRows) {
  const toasts = [];
  const created = [];
  const src = [
    grab('function visitHours(v){', '\n}'),
    grab('function visitClockReversed(v){', '\n}'),
    grab('async function generateClaim(visitId){', '\n}')
  ].join('\n\n');

  const ctx = {
    Object, Array, String, Number, Math, Date, JSON, isFinite, Promise,
    visits: () => visitRows,
    clients: () => [{ id: 'C1', name: 'Ada Reyes', payer: 'MEDICAID_OH' }],
    claims: () => created,
    authorizations: () => [],
    // Applied rate, so a refusal cannot be mistaken for "no contract resolved"
    // -- the zero-rate path writes a claim too, and this arm is about whether
    // a claim is written AT ALL.
    pcResolveRate: () => ({ status: 'applied', rate_per_hour: 30,
                            reason: 'contract CT1 in force', contract_id: 'CT1',
                            requires_authorization: false, auth_note: '' }),
    pcStateForClient: () => 'OH',
    // azResolve returns a STATUS OBJECT, never null -- generateClaim reads
    // `auth.status` unconditionally. The first draft of this stub returned
    // null and arms C4/C5/C6 went red with a TypeError while C1-C3 stayed
    // green, because a throw before the write also creates no claim. That is
    // precisely what the controls are for: without them this file would have
    // "proved" the refusal using a crash.
    azResolve: () => ({ status: 'none', reason: 'no authorisation on file',
                        auth_id: '', auth_number: '' }),
    azBurnDown: () => null,
    newId: (p) => p + '-TEST',
    fmt: (n) => '$' + Number(n || 0).toFixed(2),
    st: () => {},
    senData: async () => ({ ok: true }),
    renderClaimsTable: () => {},
    renderReadyToBill: () => {},
    blRenderKpis: () => {},
    toast: (m) => { toasts.push(String(m)); },
    console: { log() {}, warn() {} }
  };
  ctx.globalThis = ctx;
  vm.createContext(ctx);
  vm.runInContext(src, ctx, { filename: 'sairnsenior-claim-extract.js' });
  return { ctx, toasts, created };
}

// Two real hours.
const GOOD = { id: 'V1', client_id: 'C1', scheduled_date: '2026-09-20',
               clock_in_at: '2026-09-20T09:00:00Z',
               clock_out_at: '2026-09-20T11:00:00Z' };
// THE DEFECT: clocked out two hours BEFORE clocking in.
const BACKWARDS = { id: 'V2', client_id: 'C1', scheduled_date: '2026-09-20',
                    clock_in_at: '2026-09-20T11:00:00Z',
                    clock_out_at: '2026-09-20T09:00:00Z' };
// Scheduled, never clocked. Also yields 0 hours -- and is NOT the same fact.
const UNCLOCKED = { id: 'V3', client_id: 'C1', scheduled_date: '2026-09-22' };
// Timestamps that do not parse. "I cannot read this" is a third state.
const UNPARSEABLE = { id: 'V4', client_id: 'C1', scheduled_date: '2026-09-23',
                      clock_in_at: 'not-a-date', clock_out_at: 'also-not' };

console.log('SAIRNsenior -- a backwards clock pair cannot become a claim\n');

section('A. visitHours() is non-negative at source');
test('A1. a backwards pair clamps to 0, not to a negative', () => {
  const { ctx } = build([BACKWARDS]);
  const h = ctx.visitHours(BACKWARDS);
  assert.strictEqual(h, 0, 'got ' + h + ' -- a negative here reaches six callers');
});
test('A2. ...and NOT to the absolute value, which would invent a 2h visit '
  + 'nobody recorded', () => {
  const { ctx } = build([BACKWARDS]);
  assert.notStrictEqual(ctx.visitHours(BACKWARDS), 2);
});
test('A3. CONTROL: a real pair still returns its real hours, so A1 is not '
  + 'satisfied by a function that returns 0 for everything', () => {
  const { ctx } = build([GOOD]);
  assert.strictEqual(ctx.visitHours(GOOD), 2);
});
test('A4. an unclocked visit is still 0 -- unchanged by this fix', () => {
  const { ctx } = build([UNCLOCKED]);
  assert.strictEqual(ctx.visitHours(UNCLOCKED), 0);
});
test('A5. unparseable timestamps yield 0 rather than NaN, because NaN '
  + 'propagates into amount and renders as a blank, not as an error', () => {
  const { ctx } = build([UNPARSEABLE]);
  assert.strictEqual(ctx.visitHours(UNPARSEABLE), 0);
});

section('B. visitClockReversed() separates three facts that all yield 0 hours');
test('B1. a backwards pair is reversed', () => {
  const { ctx } = build([BACKWARDS]);
  assert.strictEqual(ctx.visitClockReversed(BACKWARDS), true);
});
test('B2. an UNCLOCKED visit is NOT reversed -- it is missing, and billing it '
  + 'at zero hours is a different (legitimate) path', () => {
  const { ctx } = build([UNCLOCKED]);
  assert.strictEqual(ctx.visitClockReversed(UNCLOCKED), false);
});
test('B3. UNPARSEABLE timestamps are NOT reversed -- "I cannot read this" is '
  + 'not the same claim as "this is backwards"', () => {
  const { ctx } = build([UNPARSEABLE]);
  assert.strictEqual(ctx.visitClockReversed(UNPARSEABLE), false);
});
test('B4. a good pair is not reversed', () => {
  const { ctx } = build([GOOD]);
  assert.strictEqual(ctx.visitClockReversed(GOOD), false);
});
test('B5. equal in and out is NOT reversed -- a zero-length visit is a '
  + 'different defect and this predicate must not claim it', () => {
  const { ctx } = build([GOOD]);
  assert.strictEqual(ctx.visitClockReversed(
    { clock_in_at: '2026-09-20T09:00:00Z', clock_out_at: '2026-09-20T09:00:00Z' }), false);
});

section('C. THE CLAIM REFUSES -- the arm this file exists for');
test('C1. generateClaim on a backwards visit REFUSES -- it returns normally, '
  + 'creates no claim, and does NOT throw', async () => {
  // "CREATED NOTHING" IS NOT THE SAME CLAIM AS "REFUSED", and the first draft
  // of this file could not tell them apart: a TypeError before the write also
  // leaves created.length at 0, and that is precisely how C4-C6 went red here
  // on a null azResolve stub while C1-C3 stayed green. A crash is not a
  // refusal -- it skips the toast, loses the reason, and would break the happy
  // path too. So the arm asserts the call RESOLVED.
  const { ctx, created, toasts } = build([BACKWARDS]);
  let threw = null;
  try { await ctx.generateClaim('V2'); }
  catch (e) { threw = e; }
  assert.strictEqual(threw, null,
    'generateClaim THREW instead of refusing -- a crash leaves created.length '
    + 'at 0 and would pass a naive arm: ' + (threw && threw.message));
  assert.strictEqual(created.length, 0,
    'a claim was created over a corrupt visit record: '
    + JSON.stringify(created[0] || null));
  assert.ok(toasts.length > 0,
    'nothing was created AND nothing was said -- silence is not a refusal');
});
test('C2. ...and it says WHY, naming both timestamps so the record can be '
  + 'found and corrected', async () => {
  const { ctx, toasts } = build([BACKWARDS]);
  await ctx.generateClaim('V2');
  const msg = toasts.join(' | ');
  assert.ok(/before/i.test(msg), 'the refusal does not say what is wrong: ' + msg);
  assert.ok(msg.indexOf(BACKWARDS.clock_in_at) >= 0
         && msg.indexOf(BACKWARDS.clock_out_at) >= 0,
    'the refusal does not name the two timestamps: ' + msg);
});
test('C3. the refusal does NOT read as a pricing problem -- a $0 claim is what '
  + 'this app means by "set the rate by hand", and this is not that', async () => {
  const { ctx, toasts } = build([BACKWARDS]);
  await ctx.generateClaim('V2');
  const msg = toasts.join(' | ');
  assert.ok(!/set the rate/i.test(msg),
    'the refusal was worded as the zero-rate path: ' + msg);
});
test('C4. CONTROL: a GOOD visit still bills -- C1 is not satisfied by a '
  + 'generateClaim that refuses everything', async () => {
  const { ctx, created } = build([GOOD]);
  await ctx.generateClaim('V1');
  assert.strictEqual(created.length, 1, 'the happy path stopped creating claims');
  assert.strictEqual(created[0].hours_billed, 2);
  assert.strictEqual(created[0].amount, 60);
});
test('C5. CONTROL: an UNCLOCKED visit still bills at zero hours -- the refusal '
  + 'is scoped to reversal and did not swallow the zero-hour path', async () => {
  const { ctx, created } = build([UNCLOCKED]);
  await ctx.generateClaim('V3');
  assert.strictEqual(created.length, 1,
    'the reversal guard also blocked an unclocked visit, which is a different fact');
  assert.strictEqual(created[0].hours_billed, 0);
});
test('C6. no NEGATIVE amount can be produced on any of the four fixtures -- '
  + 'the property, stated directly rather than inferred from the arms', async () => {
  for (const v of [GOOD, BACKWARDS, UNCLOCKED, UNPARSEABLE]) {
    const { ctx, created } = build([v]);
    await ctx.generateClaim(v.id);
    for (const c of created) {
      assert.ok(c.hours_billed >= 0, v.id + ' billed ' + c.hours_billed + ' hours');
      assert.ok(c.amount >= 0, v.id + ' billed ' + c.amount);
    }
  }
});

section('D. the source properties a later edit would quietly undo');
test('D1. visitHours contains a non-negative guard, not just a rounding call', () => {
  const at = codeOnly.indexOf('function visitHours(v){');
  assert.ok(at > 0, 'visitHours not found in the stripped source');
  const body = codeOnly.slice(at, codeOnly.indexOf('\n}', at));
  assert.ok(/<\s*0|>=\s*0|Math\.max/.test(body),
    'no non-negative guard survives in visitHours: ' + body.replace(/\s+/g, ' '));
});
test('D2. generateClaim calls visitClockReversed BEFORE it computes hours -- '
  + 'a guard placed after the arithmetic still writes the row', () => {
  const at = codeOnly.indexOf('async function generateClaim(visitId){');
  assert.ok(at > 0, 'generateClaim not found in the stripped source');
  const body = codeOnly.slice(at, codeOnly.indexOf('\n}', at));
  const guard = body.indexOf('visitClockReversed');
  const hours = body.indexOf('visitHours(');
  assert.ok(guard > 0, 'the reversal guard is gone from generateClaim');
  assert.ok(hours > 0, 'generateClaim no longer calls visitHours -- this arm is stale');
  assert.ok(guard < hours,
    'the guard runs AFTER hours are computed, so it no longer gates the write');
});
test('D3. CONTROL: the stripped source really is code -- D1 and D2 would pass '
  + 'vacuously against an empty string', () => {
  assert.ok(codeOnly.length > 100000,
    'stripComments returned ' + codeOnly.length + ' chars; D1/D2 prove nothing');
  assert.ok(codeOnly.indexOf('function visitHours(v){') > 0);
});

section('E. THE HARNESS ITSELF -- the two defects this file shipped in draft');
// Both arms here guard a defect that was IN THIS FILE and was caught by
// running it, not by reading it. Neither had an arm afterwards, which left the
// only protection a paragraph of prose. A comment does not fail.
test('E1. an ASYNC arm that rejects is counted as a FAILURE -- the sync-runner '
  + 'defect that printed all-green against a deliberately broken guard',
  async () => {
    const quiet = () => {};
    const r = await runQueue([
      ['passes', async () => { }],
      ['throws synchronously', () => { throw new Error('sync boom'); }],
      ['rejects asynchronously', async () => {
        await new Promise((res) => setTimeout(res, 0));
        throw new Error('async boom');
      }]
    ], quiet);
    assert.strictEqual(r.pass, 1, 'expected exactly 1 pass, got ' + r.pass);
    assert.strictEqual(r.fail, 2,
      'expected 2 failures, got ' + r.fail + ' -- if this is 1, the runner is '
      + 'not awaiting and every async arm in section C is scoring itself');
  });
test('E2. a REJECTION AFTER A TICK is still caught -- an arm that fails only '
  + 'after the microtask queue drains is the shape a sync runner misses most',
  async () => {
    const quiet = () => {};
    const r = await runQueue([['late', async () => {
      await new Promise((res) => setTimeout(res, 5));
      assert.strictEqual(1, 2, 'deliberate');
    }]], quiet);
    assert.strictEqual(r.fail, 1, 'a late rejection scored as a pass');
  });
test('E3. CONTROL: runQueue is the SAME function the real run uses, so E1/E2 '
  + 'are not testing a copy that agrees until it does not', () => {
  const src = fs.readFileSync(__filename, 'utf8');
  const runBody = src.slice(src.indexOf('async function run()'));
  assert.ok(/runQueue\(QUEUE/.test(runBody.slice(0, 300)),
    'run() no longer delegates to runQueue; section E now proves nothing '
    + 'about the harness that actually executes these arms');
});

// ── THE SUMMARY LINE REFUSES TO LIE (2026-10-05) ─────────────────────────
// Found by sabotage, not by reading. Reverting runQueue to the synchronous
// `try { fn() }` shape and re-running printed:
//
//     22 passed, 0 failed
//     FAIL unhandled rejection: expected exactly 1 pass, got 2
//
// E1 DID catch the regression and the process DID exit 1 -- but the green
// tally printed FIRST, because a sync runner resolves before the rejection
// surfaces. A human reading that output sees "22 passed, 0 failed" and stops.
// That is PR 1.5 exactly: the expensive part of a false success is the
// success message printed after the error, and this file's own subject is a
// guard that must not report a corrupt record as a clean one.
//
// Two changes. The handler no longer exits immediately -- it COUNTS, so the
// summary can see it. And the summary waits one macrotask (`setImmediate`)
// for pending rejections to land before it prints anything at all.
let unhandled = 0;
process.on('unhandledRejection', (e) => {
  unhandled++;
  console.log('  FAIL unhandled rejection: ' + (e && e.message));
});
run().then(async () => {
  // One macrotask turn. A rejection queued during the run is a microtask and
  // has already run by here; setImmediate additionally clears anything a
  // setTimeout(0) arm left behind -- E2's shape.
  await new Promise((r) => setImmediate(r));

  // AND THE ARM COUNT IS RECONCILED, which catches a different failure: an
  // arm that never ran at all contributes to neither tally and is invisible
  // in "N passed, 0 failed".
  const queued = QUEUE.filter(([, fn]) => fn).length;
  const tallied = pass + fail;
  const problems = [];
  if (unhandled) {
    problems.push(unhandled + ' unhandled rejection(s) -- the per-arm tally '
      + 'was computed before they surfaced, which is the sync-runner shape');
  }
  if (tallied !== queued) {
    problems.push(queued + ' arm(s) queued but ' + tallied + ' tallied -- '
      + (queued - tallied) + ' never reported either way');
  }
  if (problems.length) {
    console.log('\nRESULT WITHHELD -- ' + problems.join('; '));
    console.log(pass + ' passed, ' + (fail + unhandled) + ' failed');
    process.exit(1);
  }
  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  if (fail) process.exit(1);
});
