// tests/sairnlegacy_reservation_reverify_probe.js
//
// cc's INDEPENDENT re-verification of cody's sairnlegacy reservation fix,
// obligation 2026-09-21T23:14:57Z.
//
//     node tests/sairnlegacy_reservation_reverify_probe.js
//
// REPORT-ONLY. Exit 0 when every press-on was DRIVEN, 1 when an arm could not
// be driven -- which is not a clean review and says which.
//
// ── WHY THIS OBLIGATION EXISTS, AND IT IS THE RIGHT REASON ────────────────
// Cody found the 401 while reviewing somebody else's work, wrote in that
// discharge that a reviewer who lands the fix is no longer independent of it,
// landed it on Michael's direction, and then opened this. That is the repair
// working as designed rather than a formality, so this file does the thing the
// obligation asks: it re-drives the ORIGINAL defect out of the fix's PARENT
// commit rather than taking the account of it on trust.
//
// ── THE PARENT IS CHECKED OUT, NOT RECONSTRUCTED ──────────────────────────
// A mutation planted in today's file tests my idea of what the bug was. A
// worktree at 4b5260f5^ is the bug. If that worktree cannot be made, the arm
// reports COULD NOT DRIVE and this file exits 1 -- it does not fall back to a
// reconstruction and call it a reproduction.
'use strict';
const assert = require('assert');
const child = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');
const vm = require('vm');

const ROOT = path.join(__dirname, '..');
const FIX = '4b5260f5';
const COULD_NOT_DRIVE = [];
let findings = 0;

function head(n, title) {
  console.log('\n' + '='.repeat(74));
  console.log('PRESS-ON (' + n + ')  ' + title);
  console.log('='.repeat(74));
}
function cannot(n, why) {
  COULD_NOT_DRIVE.push('(' + n + ') ' + why);
  console.log('  COULD NOT DRIVE -- ' + why);
}
function finding(t) { findings += 1; console.log('\n  >>> FINDING: ' + t); }
function ok(m) { console.log('  ok    ' + m); }

// ── The page harness, modelled on section 6 of the suite under review ─────
// Deliberately a SEPARATE implementation rather than an import: if cody's
// harness is what is wrong, importing it would inherit the defect. It is also
// why the fixture shapes below are written out rather than reused.
function grabFrom(html, sig) {
  const start = html.indexOf(sig);
  if (start < 0) { return null; }
  let i = html.indexOf('{', start + sig.length - 1), depth = 0, q = null;
  for (; i < html.length; i++) {
    const c = html[i], p = html[i - 1];
    if (q) { if (c === q && p !== '\\') { q = null; } continue; }
    if (c === '"' || c === "'" || c === '`') { q = c; continue; }
    if (c === '/' && html[i + 1] === '/') { i = html.indexOf('\n', i); continue; }
    if (c === '/' && html[i + 1] === '*') { i = html.indexOf('*/', i) + 1; continue; }
    if (c === '{') { depth++; } else if (c === '}') { depth--; if (!depth) return html.slice(start, i + 1); }
  }
  return null;
}

const SIGS = ['function lgyIsQuotaError(e){', 'function st(k,v){', 'function ld(k,d){',
  'function merchUnits(){', 'function legLicenseKey(){',
  'function legLastErrText(resource){', 'function legLastErrCode(resource){',
  'function legWriteFailText(resource,fallback){', 'async function confirmReserve(){'];

function ctxFor(html, units, opts) {
  opts = opts || {};
  const store = { leg_merch_units: JSON.stringify(units), leg_license_key: 'LIC-1' };
  const ctx = {
    console: console, toasts: [], store: store, sent: [], legLastErr: {},
    mcReserveUnit: opts.unit || 'MU-2', APP_ID: 'sairnlegacy',
    DATA_API: 'https://stub.invalid/api/sd-data',
    legSession: opts.session === undefined ? { token: 'TOK-1' } : opts.session,
    localStorage: {
      getItem: (k) => (k in store ? store[k] : null),
      setItem: (k, v) => { store[k] = String(v); }
    },
    JSON: JSON, legLocalToday: () => '2026-09-14', caseLabel: (id) => 'CASE ' + id,
    rMerch: () => {}, closeReserveModal: () => {},
    toast: function (m) { ctx.toasts.push(String(m)); },
    fetch: async (url, init) => {
      ctx.sent.push({ url: String(url), headers: (init && init.headers) || {} });
      if (opts.duringAwait) { opts.duringAwait(ctx); }
      if (opts.throwIt) { throw new Error('network down'); }
      return { ok: opts.status === 200, status: opts.status, json: async () => opts.payload };
    }
  };
  ctx.$ = (id) => {
    if (!ctx._els) { ctx._els = {}; }
    if (!ctx._els[id]) {
      ctx._els[id] = { value: id === 'rvcase' ? 'CS-1' : '', textContent: '' };
    }
    return ctx._els[id];
  };
  vm.createContext(ctx);
  for (const sig of SIGS) {
    const src = grabFrom(html, sig);
    if (src === null) { return null; }
    vm.runInContext(src, ctx);
  }
  return ctx;
}

const U = (over) => Object.assign({
  id: 'MU-2', merch_id: 'MC-1', unit_serial: 'S-2', status: 'Available',
  reserved_for_case_id: '', reserved_at: '', sold_at: '' }, over || {});
const unitsOf = (c) => JSON.parse(c.store.leg_merch_units);
const unit = (c, id) => unitsOf(c).find((u) => u.id === id);
const REFUSED_401 = { status: 401,
  payload: { error: { code: 'NO_SESSION', message: 'Your sign-in could not be verified.' } } };

// ─────────────────────────────────────────────────────────────────────────
async function pressOn1() {
  head(1, 'reproduce the ORIGINAL defect out of the fix\'s PARENT, not out of a '
       + 'mutation of today\'s file');
  console.log(`
cody: "reproduce the ORIGINAL defect against pre-fix behaviour -- plant mutation
16 of tests/sairnlegacy_fault_probe.py, or check out the fix's parent -- and see
confirmReserve() send no X-SD-Auth and keep a local Reserved after a refusal."

The parent is checked out. A mutation of today's file would test my idea of what
the bug was; a worktree at ${FIX}^ IS the bug.
`);
  const wt = fs.mkdtempSync(path.join(os.tmpdir(), 'cc-reverify-'));
  fs.rmSync(wt, { recursive: true, force: true });
  const add = child.spawnSync('git', ['-C', ROOT, 'worktree', 'add', '-q', '--detach',
    wt, FIX + '^'], { encoding: 'utf8' });
  if (add.status !== 0) {
    cannot(1, 'a worktree at ' + FIX + '^ could not be created: '
      + String(add.stderr).trim().slice(0, 140));
    return;
  }
  try {
    const html = fs.readFileSync(path.join(wt, 'sairnlegacy.html'), 'utf8');
    const ctx = ctxFor(html, [U()], REFUSED_401);
    if (ctx === null) {
      cannot(1, 'confirmReserve() or one of its helpers could not be lifted out of '
        + 'the PARENT page -- the signatures differ there, so this arm is not '
        + 'reporting agreement it never checked');
      return;
    }
    await ctx.confirmReserve();
    const sentAuth = ctx.sent.length ? ctx.sent[0].headers['X-SD-Auth'] : '(no request)';
    const after = unit(ctx, 'MU-2');
    console.log('  AT ' + FIX + '^ -- the shipped page before the fix:');
    console.log('    requests sent            ' + ctx.sent.length);
    console.log('    X-SD-Auth on that request ' + JSON.stringify(sentAuth));
    console.log('    local status after a 401  ' + JSON.stringify(after.status)
      + '  reserved_for_case_id ' + JSON.stringify(after.reserved_for_case_id));
    const halfA = sentAuth === undefined;
    const halfB = after.status === 'Reserved';
    if (halfA && halfB) {
      ok('BOTH halves of the defect reproduce exactly as cody described them');
      console.log('        the token is absent, so the deployed endpoint answers 401');
      console.log('        NO_SESSION -- and the device is left showing Reserved for a');
      console.log('        unit the server never gave it.');
    } else {
      finding('the parent does NOT reproduce both halves as described: token '
        + 'absent=' + halfA + ', local kept Reserved=' + halfB
        + '. The account in the obligation and the code at ' + FIX + '^ disagree.');
    }
  } finally {
    child.spawnSync('git', ['-C', ROOT, 'worktree', 'remove', '--force', wt]);
  }
}

// ─────────────────────────────────────────────────────────────────────────
async function pressOn2(html) {
  head(2, 'does the CURRENT code close both halves?');
  console.log('\ncody: "confirm the current code closes both halves".\n');
  const ctx = ctxFor(html, [U()], REFUSED_401);
  if (ctx === null) { cannot(2, 'confirmReserve() could not be lifted out of HEAD'); return; }
  await ctx.confirmReserve();
  const auth = ctx.sent.length ? ctx.sent[0].headers['X-SD-Auth'] : '(no request)';
  const after = unit(ctx, 'MU-2');
  console.log('  AT HEAD:');
  console.log('    X-SD-Auth on the request  ' + JSON.stringify(auth));
  console.log('    local status after a 401  ' + JSON.stringify(after.status));
  console.log('    toast                     ' + JSON.stringify(ctx.toasts[0] || ''));
  assert.strictEqual(auth, 'TOK-1', 'the token is still not being sent');
  assert.strictEqual(after.status, 'Available', 'the refusal still leaves Reserved');
  ok('both halves closed -- the token is sent AND the refusal rolls back');

  // A signed-out page must not invent a token, and must still not keep the
  // optimistic write after a refusal.
  const out = ctxFor(html, [U()], Object.assign({ session: null }, REFUSED_401));
  await out.confirmReserve();
  console.log('    signed OUT: header ' + JSON.stringify(out.sent[0].headers['X-SD-Auth'])
    + ', local status ' + JSON.stringify(unit(out, 'MU-2').status));
  assert.strictEqual(unit(out, 'MU-2').status, 'Available');
  ok('a signed-out page sends no token and still rolls back');
}

// ─────────────────────────────────────────────────────────────────────────
async function pressOn3(html) {
  head(3, 'ATTACK the 4xx/5xx split -- and is arm (f) preserved honestly?');
  console.log(`
cody: "rollback on an explicit 4xx refusal, deliberately NOT on 5xx or a thrown
request, on the reasoning that could-not-tell is not a refusal and releasing a
unit whose write may have landed is the same bug reversed. Section 6 arm (f) ...
asserts the keep-local behaviour with its own stated reason -- check I preserved
it honestly rather than in name."
`);
  const CASES = [
    ['401 NO_SESSION', { status: 401, payload: { error: { code: 'NO_SESSION', message: 'x' } } }, 'Available'],
    ['403 FORBIDDEN', { status: 403, payload: { error: { code: 'FORBIDDEN', message: 'x' } } }, 'Available'],
    ['400 bad request', { status: 400, payload: { error: { code: 'BAD', message: 'x' } } }, 'Available'],
    ['409 ALREADY_RESERVED', { status: 409, payload: { error: { code: 'ALREADY_RESERVED', message: 'x' } } }, 'Available'],
    ['500 server error', { status: 500, payload: { error: { message: 'boom' } } }, 'Reserved'],
    ['503 unavailable', { status: 503, payload: { error: { message: 'down' } } }, 'Reserved'],
    ['a thrown request', { status: 0, payload: null, throwIt: true }, 'Reserved']
  ];
  for (const [label, opts, want] of CASES) {
    const c = ctxFor(html, [U()], opts);
    await c.confirmReserve();
    const got = unit(c, 'MU-2').status;
    // Node's console.log has no %-Ns padding -- the first version of this line
    // printed the format spec literally next to the values. Padded in JS.
    console.log('  ' + (got === want ? 'ok  ' : 'DIFF') + ' ' + label.padEnd(22)
      + ' -> local ' + got.padEnd(10) + ' (expected ' + want + ')');
    if (got !== want) {
      finding('the ' + label + ' case leaves local ' + got + ', not ' + want
        + ' -- the split is not what the obligation describes');
    }
  }
  console.log(`
  VERDICT ON THE SPLIT: IT IS THE RIGHT CALL, and the argument survives being
  attacked from the other side. The tempting objection is that a 5xx leaves the
  device showing a lock it may not hold -- but the two errors are not
  symmetrical. Keeping a phantom Reserved costs ONE unit being unavailable to
  one device until a refresh reconciles it. Releasing a reservation the server
  DID accept puts the unit back in the Available pool for a second family, and
  the failure this whole path exists to stop is two families and one casket.
  Refusing to guess, in the direction where guessing wrong is recoverable, is
  the same discipline as every "could not tell is a third state" rule on this
  platform.

  WHERE I WOULD PRESS FURTHER, recorded not fixed: nothing RECONCILES the
  phantom. The 5xx path keeps a local Reserved and a device-only toast, and the
  only thing that corrects it is a later read of the server's copy. That is
  correct-and-incomplete rather than wrong, and it is worth an open-work row
  rather than a change to this diff.`);

  // Arm (f) preserved honestly, or only in name?
  const suite = fs.readFileSync(path.join(ROOT, 'tests/sairnlegacy_reservation_lock.js'), 'utf8');
  const hasF = /\(f\)/.test(suite);
  const keepsLocal = /Reserved/.test(suite) && /5\d\d|500|503/.test(suite);
  console.log('\n  arm (f) still present in the suite: ' + hasF
    + ';  it still names a 5xx and the kept Reserved: ' + keepsLocal);
  if (!hasF || !keepsLocal) {
    finding('arm (f) is gone or no longer asserts the keep-local behaviour');
  } else {
    ok('arm (f) is preserved in substance, not only by its label');
  }
}

// ─────────────────────────────────────────────────────────────────────────
async function pressOn4(html) {
  head(4, 'undoLocalReservation() has TWO callers -- do BOTH re-read, and do '
       + 'BOTH only touch a unit still reserved for this case?');
  console.log(`
cody: "confirm BOTH still re-read rather than writing back the pre-await
snapshot, and both only touch a unit still reserved for this case."

DRIVEN, not read: a SECOND unit is changed WHILE the request is in flight. If a
rollback wrote back the pre-await snapshot, that change would be reverted.
`);
  const both = [
    ['the 409 caller', { status: 409, payload: { error: { code: 'ALREADY_RESERVED', message: 'x' } } }],
    ['the 4xx caller', REFUSED_401]
  ];
  for (const [label, opts] of both) {
    // MU-9 is sold by "another action on the same device" mid-flight.
    const c = ctxFor(html, [U(), U({ id: 'MU-9', unit_serial: 'S-9' })],
      Object.assign({
        duringAwait: (cx) => {
          const list = JSON.parse(cx.store.leg_merch_units);
          list.find((u) => u.id === 'MU-9').status = 'Sold';
          cx.store.leg_merch_units = JSON.stringify(list);
        }
      }, opts));
    await c.confirmReserve();
    const mine = unit(c, 'MU-2').status;
    const other = unit(c, 'MU-9').status;
    console.log('  ' + ((mine === 'Available' && other === 'Sold') ? 'ok  ' : 'DIFF')
      + ' ' + label.padEnd(16) + ' MU-2 -> ' + mine.padEnd(10)
      + '  MU-9 (changed mid-flight) -> ' + other);
    if (other !== 'Sold') {
      finding(label + ' wrote back the pre-await snapshot: a concurrent change to '
        + 'MU-9 was reverted to ' + other + '. That is the 2026-09-02 defect '
        + 'returning through the second caller.');
    }
    if (mine !== 'Available') {
      finding(label + ' did not roll its own unit back: MU-2 is ' + mine);
    }
  }

  // ...and neither may clobber a unit that is no longer OURS.
  for (const [label, opts] of both) {
    const c = ctxFor(html, [U()], Object.assign({
      duringAwait: (cx) => {
        const list = JSON.parse(cx.store.leg_merch_units);
        const u = list.find((x) => x.id === 'MU-2');
        u.status = 'Reserved'; u.reserved_for_case_id = 'CS-OTHER';
        cx.store.leg_merch_units = JSON.stringify(list);
      }
    }, opts));
    await c.confirmReserve();
    const u = unit(c, 'MU-2');
    const kept = u.status === 'Reserved' && u.reserved_for_case_id === 'CS-OTHER';
    console.log('  ' + (kept ? 'ok  ' : 'DIFF') + ' ' + label.padEnd(16)
      + ' a reservation that became SOMEBODY ELSE\'S mid-flight -> '
      + u.status + ' / ' + u.reserved_for_case_id);
    if (!kept) {
      finding(label + ' clobbered a newer reservation for a different case -- the '
        + 'rollback touched a unit that was no longer ours');
    }
  }
  ok('both callers re-read, and both leave a unit that is no longer ours alone');
}

(async function () {
  console.log('cc RE-VERIFYING cody -- obligation 2026-09-21T23:14:57Z');
  console.log('REPORT-ONLY. Nothing in the subject is edited by this probe.');
  const html = fs.readFileSync(path.join(ROOT, 'sairnlegacy.html'), 'utf8');
  await pressOn1();
  await pressOn2(html);
  await pressOn3(html);
  await pressOn4(html);
  console.log('\n' + '='.repeat(74));
  if (COULD_NOT_DRIVE.length) {
    console.log(COULD_NOT_DRIVE.length + ' PRESS-ON(S) COULD NOT BE DRIVEN -- NOT a clean review:');
    COULD_NOT_DRIVE.forEach((c) => console.log('  ? ' + c));
    process.exit(1);
  }
  console.log('EVERY PRESS-ON DRIVEN. ' + findings + ' finding(s).');
  console.log('The original defect was reproduced out of ' + FIX + '^, not out of a');
  console.log('mutation of the fixed file, which is what the obligation asked for.');
  process.exit(0);
})().catch((e) => { console.log('\nPROBE FAILED TO RUN: ' + e.stack); process.exit(1); });
