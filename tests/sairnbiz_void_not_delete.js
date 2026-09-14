// tests/sairnbiz_void_not_delete.js
//
// Run:  node tests/sairnbiz_void_not_delete.js
//
// TWO TIER A RESOURCES REACHED A SERVER WITH NO WAY TO CORRECT A WRONG ROW.
//
// `sb_po` and `sb_recv` were synced on 2026-09-14 and tiered A.
// `tools/removal_path_check.py` found them in the post-work sweep: neither had
// a removal verb, because this platform grants no `delete` and the generic
// SB_RESOURCES pair in api/sd-data.js has a read path and a write path and
// nothing else.
//
// WHY THAT IS SHARPER HERE THAN ON THE OTHER 53 IN THE BURN-DOWN QUEUE: these
// two are consumed by a CONTROL. `sbMatchPure` sums EVERY receipt against a PO,
// so a receipt entered in error inflated the received total FOR EVER and the
// bill was refused with "billed $X against $Y actually received" -- two figures
// and a refusal, against a number nobody in the product could correct. And two
// POs sharing a number refuse the match outright by design, so a PO raised in
// error on a second device was permanent and blocked a correct bill.
//
// A CONTROL A PERSON CANNOT CORRECT IS ONE THEY ROUTE AROUND, which is the
// failure the three-way match exists to prevent.
//
// ── WHAT THIS SUITE COVERS AND WHAT IT DOES NOT ─────────────────────────────
// tests/functional_core_is_pure.js already drives the MATCH half by argument --
// a voided PO, a voided receipt, the duplicate-number unblock, and six negative
// controls on statuses that are NOT 'Void'. This suite is the other half: the
// ACTIONS and the RENDER, which touch storage, a role and a prompt, and so
// cannot be reached from the pure core.
//
//   - the role gate, from both sides, and the fact that it is re-checked in the
//     action rather than trusted to a hidden button
//   - the reason: required, cancellable, trimmed, and never blank
//   - a failed write leaves the row UNVOIDED and says so
//   - the row stays visible in both tables after the void
//   - the Received column excludes voided receipts -- the same figure the gate
//     compares against, so a refusal can never name a total the screen does not
//     show
//   - a receipt against a voided PO is refused at entry
//   - a voided PO still holds its NUMBER, so the sequence never reuses it
//
// THE FUNCTIONS ARE EXTRACTED FROM THE SHIPPED sairnbiz.html AND DRIVEN.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const ROOT = path.join(__dirname, '..');
const HTML = fs.readFileSync(process.env.SB_HTML || path.join(ROOT, 'sairnbiz.html'),
                             'utf8').replace(/\r\n/g, '\n');

let n = 0;
function ok(cond, label) { assert.ok(cond, label); n++; console.log('  ok   ' + label); }
function section(s) { console.log('\n' + s); }

function grab(sig) {
  const start = HTML.indexOf(sig);
  assert.ok(start > 0, 'not found in sairnbiz.html: ' + sig);
  let i = HTML.indexOf('{', start + sig.length - 1), depth = 0, q = null;
  for (; i < HTML.length; i++) {
    const c = HTML[i], p = HTML[i - 1];
    if (q) { if (c === q && p !== '\\') q = null; continue; }
    if (c === '"' || c === "'" || c === '`') { q = c; continue; }
    if (c === '/' && HTML[i + 1] === '/') { i = HTML.indexOf('\n', i); continue; }
    if (c === '/' && HTML[i + 1] === '*') { i = HTML.indexOf('*/', i) + 1; continue; }
    if (c === '{') depth++;
    else if (c === '}') { depth--; if (!depth) return HTML.slice(start, i + 1); }
  }
  throw new Error('unterminated: ' + sig);
}

// THE ROLE LIST IS READ OUT OF THE SHIPPED FILE, not retyped here. A test that
// hardcodes ['owner','manager'] would keep passing after somebody widened the
// constant, which is the one change this suite most needs to notice.
const VOID_ROLES = (() => {
  const m = /var SB_VOID_ROLES=(\[[^\]]*\]);/.exec(HTML);
  assert.ok(m, 'SB_VOID_ROLES not found in sairnbiz.html');
  return JSON.parse(m[1].replace(/'/g, '"'));
})();

// SAIRNbiz's real role vocabulary, read from the server-side source of truth
// rather than from this file's memory of it. PR §3.4: read the app's own role
// list -- SAIRNcode's top role is 'admin', not 'owner', and guessing has cost
// this platform a session before.
const APP_ROLES = (() => {
  const auth = fs.readFileSync(path.join(ROOT, 'api/_lib/auth.js'), 'utf8').replace(/\r\n/g, '\n');
  const m = /sairnbiz:\s*(\[[^\]]*\])/.exec(auth);
  assert.ok(m, 'ROLES_BY_APP.sairnbiz not found in api/_lib/auth.js');
  return JSON.parse(m[1].replace(/'/g, '"'));
})();

// `prompt` is scripted per call rather than stubbed once: the reason path has
// three outcomes (a reason, a cancel, and a blank) and they must be told apart.
function makeCtx(store, opts) {
  opts = opts || {};
  const session = { sb_session_role: opts.role === undefined ? 'owner' : opts.role,
                    sb_session_employee_id: opts.employee || 'EMP-1' };
  const els = {};
  const ctx = {
    console: console,
    toasts: [],
    prompts: [],
    rendered: 0,
    store: store,
    promptReturns: opts.prompts === undefined ? ['keyed twice'] : opts.prompts,
    H: (s) => String(s === undefined || s === null ? '' : s)
                .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;').replace(/'/g, '&#39;'),
    fmt: (v) => '$' + Number(v || 0).toFixed(2),
    toast: function (m) { ctx.toasts.push(String(m)); },
    $: (id) => (id in els ? els[id] : null),
    sbLocalToday: () => '2026-09-14',
    sessionStorage: { getItem: (k) => (k in session ? session[k] : null) },
    ld: (k, d) => { try { const v = JSON.parse(store[k]); return v === null ? d : v; } catch (e) { return d; } },
    st: function (k, v) {
      if (opts.stFails) return false;
      store[k] = JSON.stringify(v);
      return true;
    },
    rAP: function () { ctx.rendered++; if (ctx.sbRenderPOs) ctx.sbRenderPOs(); }
  };
  ctx.window = { prompt: function (msg) { ctx.prompts.push(String(msg)); return ctx.promptReturns.shift(); } };
  ctx.addEl = (id) => { els[id] = { innerHTML: '' }; return els[id]; };
  ctx.setFields = (f) => { Object.keys(f).forEach((k) => { els[k] = { value: String(f[k]) }; }); };
  vm.createContext(ctx);
  vm.runInContext('var SB_ROLE_KEY=' + JSON.stringify('sb_session_role')
                  + ';var SB_EMPLOYEE_KEY=' + JSON.stringify('sb_session_employee_id') + ';', ctx);
  vm.runInContext(/var SB_VOID_ROLES=\[[^\]]*\];/.exec(HTML)[0], ctx);
  for (const sig of ['function sbMyRole(){', 'function sbMyEmployeeId(){',
                     'function sbPOAll(){', 'function sbRecvAll(){',
                     'function sbPONext(rows,year){',
                     'function sbCanVoid(){', 'function sbIsVoid(r){', 'function sbPOKey(p){',
                     'function sbVoidMark(r){', 'function sbRenderPOs(){',
                     'function sbVoidReason(what){', 'function sbVoidRefusal(what){',
                     'function sbPOVoid(key){', 'function sbRecvVoid(id){',
                     'function sbRecvLog(){']) {
    vm.runInContext(grab(sig), ctx);
  }
  return ctx;
}

const PO = (over) => Object.assign({ id: 'PO-a', po_num: 'PO-2026-001', vendor: 'Stone World',
                                     desc: 'Slabs', amt: 1200, date: '2026-09-14', status: 'Open' }, over || {});
const RC = (over) => Object.assign({ id: 'RC-a', po_num: 'PO-2026-001', vendor: 'Stone World',
                                     val: 1200, date: '2026-09-14' }, over || {});
const seeded = () => ({ sb_po: JSON.stringify([PO()]), sb_recv: JSON.stringify([RC()]) });
const posOf = (s) => JSON.parse(s.sb_po || '[]');
const recsOf = (s) => JSON.parse(s.sb_recv || '[]');

console.log('SAIRNbiz: a wrong row is VOIDED, never deleted\n');

// ── 1. THE ROLE VOCABULARY IS THIS APP'S OWN ────────────────────────────────
section('1. the gate names roles that actually exist in this app');
{
  ok(VOID_ROLES.length > 0, 'SB_VOID_ROLES is not empty: ' + JSON.stringify(VOID_ROLES));
  const unknown = VOID_ROLES.filter((r) => APP_ROLES.indexOf(r) === -1);
  ok(unknown.length === 0,
     'every role in SB_VOID_ROLES exists in ROLES_BY_APP.sairnbiz ('
     + APP_ROLES.join('|') + ')' + (unknown.length ? ' -- UNKNOWN: ' + unknown.join(', ') : ''));
  // THE ARM THAT RECORDS THE TRANSLATION. The decision said "Admin/Manager".
  // SAIRNbiz HAS NO 'admin' ROLE -- its top role is 'owner' -- so a literal
  // implementation would have shipped a gate no account on this app could ever
  // pass, and every void would have been refused with a message naming a role
  // that does not exist. Asserted rather than commented, because the next
  // person to widen this list will read the assertion, not the history.
  ok(APP_ROLES.indexOf('admin') === -1,
     'CONTROL: SAIRNbiz genuinely has no "admin" role, so mapping the '
     + 'decision\'s "Admin" onto "owner" was a translation and not a rename');
  ok(VOID_ROLES.indexOf('staff') === -1,
     'and the gate is not open to staff');
}

// ── 2. THE ROLE GATE, FROM BOTH SIDES ───────────────────────────────────────
section('2. who may void');
{
  for (const role of VOID_ROLES) {
    const store = seeded();
    const ctx = makeCtx(store, { role: role });
    ctx.sbPOVoid('PO-a');
    ok(posOf(store)[0].status === 'Void', role + ' may void a purchase order');
  }
  const denied = APP_ROLES.filter((r) => VOID_ROLES.indexOf(r) === -1);
  ok(denied.length > 0, 'CONTROL: there are roles to deny -- ' + denied.join(', '));
  for (const role of denied) {
    const store = seeded();
    const ctx = makeCtx(store, { role: role });
    ctx.sbPOVoid('PO-a');
    ctx.sbRecvVoid('RC-a');
    ok(posOf(store)[0].status === 'Open' && recsOf(store)[0].status === undefined,
       role + ' may NOT void either document -- nothing changed');
    ok(ctx.toasts.length === 2 && ctx.toasts.every((t) => /restricted to/.test(t)),
       '...and is told why, twice, rather than watching a button do nothing');
    ok(ctx.prompts.length === 0,
       '...and is never asked for a reason for a change that will not happen');
  }
  // THE GATE IS RE-CHECKED IN THE ACTION, NOT TRUSTED TO THE HIDDEN BUTTON.
  // sbRenderPOs() omits the button for a role that may not void, and a hidden
  // button is a UI state, not a control -- nothing repaints these tables when a
  // session changes underneath them.
  const store = seeded();
  const ctx = makeCtx(store, { role: '' });
  ctx.sbPOVoid('PO-a');
  ok(posOf(store)[0].status === 'Open',
     'a call that bypasses the button entirely is still refused -- the empty '
     + 'least-privileged default role cannot void');
}

// ── 3. A REASON IS REQUIRED ─────────────────────────────────────────────────
section('3. a void carries a reason or it does not happen');
{
  {
    const store = seeded();
    const ctx = makeCtx(store, { prompts: ['ordered from the wrong vendor'] });
    ctx.sbPOVoid('PO-a');
    const p = posOf(store)[0];
    ok(p.status === 'Void' && p.void_reason === 'ordered from the wrong vendor',
       'the reason is stored on the row');
    ok(p.voided_at === '2026-09-14' && p.voided_by === 'EMP-1',
       '...with WHEN and WHO -- ' + p.voided_at + ' / ' + p.voided_by);
    ok(/not deleted/i.test(ctx.prompts[0]),
       'and the prompt says the row is not deleted, so nobody cancels out of a '
       + 'correction believing it destroys the record');
  }
  {
    const store = seeded();
    const ctx = makeCtx(store, { prompts: [null] });   // Cancel
    ctx.sbPOVoid('PO-a');
    ok(posOf(store)[0].status === 'Open', 'CANCEL leaves the PO open');
    ok(ctx.toasts.length === 0, '...silently, because nothing happened');
  }
  for (const blank of ['', '   ', '\t\n ']) {
    const store = seeded();
    const ctx = makeCtx(store, { prompts: [blank] });
    ctx.sbPOVoid('PO-a');
    ok(posOf(store)[0].status === 'Open',
       'a blank reason (' + JSON.stringify(blank) + ') does NOT void');
    ok(ctx.toasts.some((t) => /reason is required/i.test(t)), '...and says so');
  }
  {
    const store = seeded();
    const ctx = makeCtx(store, { prompts: ['  spaces around it  '] });
    ctx.sbPOVoid('PO-a');
    ok(posOf(store)[0].void_reason === 'spaces around it', 'the reason is trimmed');
  }
  {
    const store = seeded();
    const ctx = makeCtx(store, { prompts: ['x'.repeat(900)] });
    ctx.sbPOVoid('PO-a');
    ok(posOf(store)[0].void_reason.length === 500,
       'and capped at 500 characters, the same cap sbSetActive uses');
  }
}

// ── 4. A FAILED WRITE LEAVES THE ROW UNVOIDED, LOUDLY ───────────────────────
section('4. a failed write is not a silent void');
{
  const store = seeded();
  const ctx = makeCtx(store, { stFails: true });
  ctx.sbPOVoid('PO-a');
  ok(posOf(store)[0].status === 'Open',
     'st() returning false leaves the STORED PO open -- not a half-applied void');
  ok(ctx.toasts.some((t) => /NOT voided/.test(t) && /Nothing was changed/.test(t)),
     '...and the refusal says so out loud rather than reporting success');
  ok(ctx.rendered === 0,
     '...and the table is not repainted, so the screen cannot show a void that '
     + 'was never written');

  const store2 = seeded();
  const ctx2 = makeCtx(store2, { stFails: true });
  ctx2.sbRecvVoid('RC-a');
  ok(recsOf(store2)[0].status === undefined && ctx2.toasts.some((t) => /NOT voided/.test(t)),
     'the same on the receipt half -- both halves, not one');
}

// ── 5. VOIDING IS IDEMPOTENT AND KEYED CORRECTLY ────────────────────────────
section('5. the right row, once');
{
  {
    const store = { sb_po: JSON.stringify([PO({ status: 'Void', void_reason: 'first reason' })]),
                    sb_recv: JSON.stringify([]) };
    const ctx = makeCtx(store);
    ctx.sbPOVoid('PO-a');
    ok(posOf(store)[0].void_reason === 'first reason',
       'voiding an already-void PO does not overwrite the original reason');
    ok(ctx.prompts.length === 0, '...and does not even ask for a new one');
    ok(ctx.toasts.some((t) => /already void/.test(t)), '...it says it is already void');
  }
  {
    const store = seeded();
    const ctx = makeCtx(store);
    ctx.sbPOVoid('PO-does-not-exist');
    ok(posOf(store)[0].status === 'Open' && ctx.toasts.some((t) => /no longer on this device/.test(t)),
       'a key that matches nothing changes nothing and says so');
  }
  // TWO POs SHARING A NUMBER MUST BE VOIDABLE ONE AT A TIME. This is the whole
  // point of keying on the minted id: po_num is NOT unique across devices, and
  // a po_num key would void both halves of the pair -- leaving the bill refused
  // for a different reason and destroying the correct PO along with the wrong
  // one.
  {
    const store = { sb_po: JSON.stringify([PO(), PO({ id: 'PO-b', amt: 9900 })]),
                    sb_recv: JSON.stringify([RC()]) };
    const ctx = makeCtx(store, { prompts: ['raised in error on the shop terminal'] });
    ctx.sbPOVoid('PO-b');
    const rows = posOf(store);
    ok(rows[1].status === 'Void' && rows[0].status === 'Open',
       'the duplicate is voided and the correct PO of the SAME NUMBER is untouched');
  }
  // MANY RECEIPTS ANSWER ONE PO. A po_num key on the receipt half would void a
  // whole delivery history to correct one line.
  {
    const store = { sb_po: JSON.stringify([PO()]),
                    sb_recv: JSON.stringify([RC(), RC({ id: 'RC-b', val: 700 })]) };
    const ctx = makeCtx(store);
    ctx.sbRecvVoid('RC-b');
    const rows = recsOf(store);
    ok(rows[1].status === 'Void' && rows[0].status === undefined,
       'only the named receipt is voided; the other receipt against the same PO survives');
  }
}

// ── 6. THE ROW STAYS VISIBLE, AND THE FIGURE DOES NOT ───────────────────────
section('6. voided rows are rendered, their values are not');
{
  const store = { sb_po: JSON.stringify([PO()]),
                  sb_recv: JSON.stringify([RC(), RC({ id: 'RC-b', val: 700 })]),
                  sb_ap: JSON.stringify([]) };
  const ctx = makeCtx(store);
  const pot = ctx.addEl('potbody'), rcv = ctx.addEl('rcvtbody');

  ctx.sbRenderPOs();
  ok(/\$1900\.00/.test(pot.innerHTML),
     'BEFORE: the Received column shows $1900.00 -- both receipts');

  ctx.sbRecvVoid('RC-b');
  ctx.sbRenderPOs();
  ok(/\$1200\.00/.test(pot.innerHTML) && !/\$1900\.00/.test(pot.innerHTML),
     'AFTER: the Received column shows $1200.00 -- the voided receipt is excluded');
  // THE SCREEN AND THE GATE MUST READ THE SAME NUMBER. If the panel showed one
  // total and sbMatchPure used another, a refusal would name a figure the
  // screen does not show -- the exact shape of the uncorrectable "billed $X
  // against $Y" refusal this mechanism exists to fix.
  ok(/RC-b|700/.test(rcv.innerHTML) || /\$700\.00/.test(rcv.innerHTML),
     'the voided receipt is still RENDERED in the goods-received table');
  ok(/keyed twice/.test(rcv.innerHTML),
     '...carrying its reason, so the correction is reviewable');
  ok(/badge bx">Void/.test(rcv.innerHTML), '...and marked Void');

  ctx.sbPOVoid('PO-a');
  ctx.sbRenderPOs();
  ok(/PO-2026-001/.test(pot.innerHTML),
     'a voided PO is still RENDERED -- the trail is what makes the control reviewable');
  ok(/badge bx">Void/.test(pot.innerHTML), '...and marked Void');
  ok(!/onclick="sbPOVoid/.test(pot.innerHTML),
     '...and offers no second Void button for a row that is already void');
}
{
  // The button is absent for a role that may not void. Not a security boundary
  // -- section 2 covers the real check -- but a button that toasts a refusal
  // every time is a worse screen than no button.
  const store = seeded();
  store.sb_ap = JSON.stringify([]);
  const ctx = makeCtx(store, { role: 'staff' });
  const pot = ctx.addEl('potbody'), rcv = ctx.addEl('rcvtbody');
  ctx.sbRenderPOs();
  ok(!/sbPOVoid/.test(pot.innerHTML) && !/sbRecvVoid/.test(rcv.innerHTML),
     'staff sees no Void button on either table');
  const ctx2 = makeCtx(seeded(), { role: VOID_ROLES[0] });
  ctx2.addEl('potbody'); ctx2.addEl('rcvtbody');
  ctx2.sbRenderPOs();
  ok(/sbPOVoid/.test(ctx2.$('potbody').innerHTML) && /sbRecvVoid/.test(ctx2.$('rcvtbody').innerHTML),
     'CONTROL: ' + VOID_ROLES[0] + ' does see both -- the arm above is not passing '
     + 'on a table that renders no buttons for anyone');
}

// ── 7. A RECEIPT AGAINST A VOIDED PO IS REFUSED AT ENTRY ────────────────────
section('7. nothing is received against a voided PO');
{
  const store = { sb_po: JSON.stringify([PO({ status: 'Void', void_reason: 'wrong vendor' })]),
                  sb_recv: JSON.stringify([]) };
  const ctx = makeCtx(store);
  ctx.setFields({ rcvpo: 'PO-2026-001', rcvvendor: 'Stone World', rcvval: '1200' });
  ctx.sbRecvLog();
  ok(recsOf(store).length === 0, 'the receipt is not written');
  ok(ctx.toasts.some((t) => /has been voided/.test(t) && /raise a new PO/.test(t)),
     '...and the refusal names the action to take, not just the problem');

  // CONTROL: the same entry against a LIVE PO still works. Without this arm the
  // one above would pass on a sbRecvLog() that refused everything.
  const store2 = { sb_po: JSON.stringify([PO()]), sb_recv: JSON.stringify([]) };
  const ctx2 = makeCtx(store2);
  ctx2.setFields({ rcvpo: 'PO-2026-001', rcvvendor: 'Stone World', rcvval: '1200' });
  ctx2.sbRecvLog();
  ok(recsOf(store2).length === 1, 'CONTROL: the same receipt against a live PO is accepted');

  // One live and one void sharing a number: the live one still accepts.
  const store3 = { sb_po: JSON.stringify([PO({ id: 'PO-b', status: 'Void', void_reason: 'dupe' }), PO()]),
                   sb_recv: JSON.stringify([]) };
  const ctx3 = makeCtx(store3);
  ctx3.setFields({ rcvpo: 'PO-2026-001', rcvvendor: 'Stone World', rcvval: '1200' });
  ctx3.sbRecvLog();
  ok(recsOf(store3).length === 1,
     'a number with one voided and one live PO still accepts the receipt');
}

// ── 8. A VOIDED PO STILL HOLDS ITS NUMBER ───────────────────────────────────
section('8. the sequence never reuses a voided number');
{
  const store = { sb_po_seq: JSON.stringify({ 2026: 3 }) };
  const ctx = makeCtx(store);
  const rows = [PO({ po_num: 'PO-2026-003', status: 'Void', void_reason: 'cancelled by the vendor' })];
  const next = ctx.sbPONext(rows, '2026');
  ok(next === 'PO-2026-004',
     'the next number after a voided PO-2026-003 is PO-2026-004, not a reuse -- '
     + 'got ' + next);
  // Handing PO-2026-003 out twice would put a bill against the replacement and
  // a bill against the void under one number, and the ambiguity guard would
  // then refuse both.
  ok(JSON.parse(store.sb_po_seq)[2026] === 4,
     '...and the counter advanced, so the gap is auditable and permanent');
}

console.log('\nALL ' + n + ' ASSERTIONS PASS');
