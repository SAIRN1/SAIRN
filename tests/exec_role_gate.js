// tests/exec_role_gate.js
//
// Run:  node tests/exec_role_gate.js
//
// The Executive Suite's advisor prompts carry SAIRN Technologies' own chart of
// accounts, StoneDesk's price book and the patent deadline. Before 2026-09-02 a
// paying customer's Sales Rep could open it, because:
//
//   1. #sb-executive carried no gating class and .admin-only only ever covered
//      .nav-btn, never the sidebar's .sb-btn;
//   2. showPanel() had no role check on any panel;
//   3. applyExecRole() read the 'sd_exec_role' localStorage preference BEFORE
//      checking any role, so one owner setting it once granted is-exec to every
//      later user of that browser -- localStorage is permanent and per-origin,
//      the session role is not;
//   4. setExecRoleAndClose() was a global with no check at all, and it WRITES
//      the preference (3) then trusts.
//
// This drives the REAL functions out of the real file rather than re-stating
// them, so the gate cannot be edited away without this failing. It asserts the
// refusal, not just the absence of a crash.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const ROOT = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(ROOT, 'stonedesk.html'), 'utf8');

// ---- extract the three real functions, by their exact source text ----------
function grab(startMarker, endMarker) {
  const s = html.indexOf(startMarker);
  assert.ok(s > 0, 'not found in stonedesk.html: ' + startMarker);
  const e = html.indexOf(endMarker, s);
  assert.ok(e > s, 'unterminated: ' + startMarker);
  return html.slice(s, e + endMarker.length);
}

const srcPrivileged = grab('function sdExecPrivileged(){', '\n}');
const srcApply      = grab('function applyExecRole(user){', '\n}');
const srcSetRole    = grab('function setExecRoleAndClose(role){', '\n}');

// showPanel is long; take only the gate at its head, which is what is under
// test. Ends at the first querySelectorAll, the original first statement.
const showPanelFull = grab('function showPanel(id) {', "document.querySelectorAll('.panel')");

// ---- a bare DOM/storage harness -------------------------------------------
function makeCtx(sessionRole, execPref) {
  const sessionStore = {};
  const localStore = {};
  if (sessionRole) sessionStore['sd_session_role'] = sessionRole;
  if (execPref) localStore['sd_exec_role'] = execPref;

  const classes = new Set();
  const notices = [];
  const removed = [];

  const ctx = {
    sessionStorage: {
      getItem: k => (k in sessionStore ? sessionStore[k] : null),
      setItem: (k, v) => { sessionStore[k] = String(v); },
      removeItem: k => { delete sessionStore[k]; }
    },
    localStorage: {
      getItem: k => (k in localStore ? localStore[k] : null),
      setItem: (k, v) => { localStore[k] = String(v); },
      removeItem: k => { delete localStore[k]; }
    },
    document: {
      body: {
        classList: {
          add: c => classes.add(c),
          remove: c => classes.delete(c),
          contains: c => classes.has(c)
        }
      },
      getElementById: id => ({ remove: () => removed.push(id) }),
      querySelectorAll: () => ({ forEach: () => {} })
    },
    // Collaborators the real functions call. Stubbed to RECORD, so the test can
    // assert they were never reached for an unprivileged session.
    notify: (msg, kind) => notices.push({ msg, kind }),
    setRoleBadge: () => { ctx.__badge = true; },
    renderExecContent: () => { ctx.__rendered = true; },
    stRaw: (k, v) => { localStore[k] = String(v); ctx.__persisted = true; },
    SD_EXEC_ROLES: ['ceo', 'cfo', 'cto', 'admin'],
    sdExecRole: '',
    setTimeout: () => { ctx.__pickerScheduled = true; },
    window: {},
    console: console,
    __classes: classes,
    __notices: notices,
    __removed: removed,
    __localStore: localStore
  };
  ctx.showExecRolePicker = () => { ctx.__pickerShown = true; };
  vm.createContext(ctx);
  // showPanel's gate, made standalone: the head is kept VERBATIM, then the body
  // is cut off at its original first statement and replaced with a report, so
  // the test exercises the real gate without dragging in a thousand lines of
  // panel switching. Closing brace re-added because the slice ends mid-function.
  const showPanelGate =
    showPanelFull.slice(0, showPanelFull.lastIndexOf("document.querySelectorAll('.panel')")) +
    '\n  __opened = true;\n  return;\n}';

  vm.runInContext(
    'var __opened = false;\n' +
    srcPrivileged + '\n' + srcApply + '\n' + srcSetRole + '\n' + showPanelGate +
    '\nfunction __tryOpen(id){ __opened = false; showPanel(id); return __opened; }',
    ctx
  );
  return ctx;
}

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('--- ' + t + ' ---'); }

// ---------------------------------------------------------------------------
section('the panel itself is refused, not merely hidden');

test('a sales rep cannot open the Executive Suite', () => {
  const c = makeCtx('sales');
  assert.strictEqual(c.__tryOpen('executive'), false, 'panel opened for role=sales');
  assert.strictEqual(c.__notices.length, 1, 'refusal was silent');
  assert.match(c.__notices[0].msg, /Owner and Manager/);
});

test('an installer cannot open it either', () => {
  const c = makeCtx('install');
  assert.strictEqual(c.__tryOpen('executive'), false);
});

test('NO session at all is refused -- not treated as trusted', () => {
  const c = makeCtx('');
  assert.strictEqual(c.__tryOpen('executive'), false);
});

test('an owner can open it', () => {
  const c = makeCtx('owner');
  assert.strictEqual(c.__tryOpen('executive'), true);
  assert.strictEqual(c.__notices.length, 0);
});

test('a manager (admin) can open it', () => {
  const c = makeCtx('admin');
  assert.strictEqual(c.__tryOpen('executive'), true);
});

test('the gate is scoped to this one panel and does not break the rest', () => {
  const c = makeCtx('sales');
  assert.strictEqual(c.__tryOpen('slabs'), true, 'a normal panel was blocked');
  assert.strictEqual(c.__tryOpen('quote'), true);
});

// ---------------------------------------------------------------------------
section('the localStorage preference no longer outranks the session role');

test('a stale sd_exec_role from a previous OWNER does not grant a sales rep', () => {
  const c = makeCtx('sales', 'cfo');
  c.applyExecRole({ role: 'sales' });
  assert.ok(!c.__classes.has('is-exec'), 'is-exec granted from a stale preference');
  assert.ok(!c.__rendered, 'exec content was rendered for an unprivileged role');
  assert.ok(!c.__badge, 'exec badge was set for an unprivileged role');
});

test('and the stale preference is CLEARED, not just ignored', () => {
  const c = makeCtx('sales', 'cfo');
  c.applyExecRole({ role: 'sales' });
  assert.strictEqual(c.__localStore['sd_exec_role'], undefined,
    'someone else\'s exec preference survived in localStorage');
});

test('an owner WITH a stored preference still gets the suite', () => {
  const c = makeCtx('owner', 'cfo');
  c.applyExecRole({ role: 'admin' });
  assert.ok(c.__classes.has('is-exec'));
  assert.ok(c.__rendered);
});

test('an owner with NO stored preference gets the picker, not a silent grant', () => {
  const c = makeCtx('owner');
  c.applyExecRole({ role: 'admin' });
  assert.ok(!c.__classes.has('is-exec'), 'is-exec granted before a role was picked');
  assert.ok(c.__pickerScheduled, 'the picker was never scheduled for an owner');
});

test('applying an unprivileged role STRIPS an is-exec left over from before', () => {
  const c = makeCtx('sales', 'cfo');
  c.document.body.classList.add('is-exec');   // e.g. a re-login in the same tab
  c.applyExecRole({ role: 'sales' });
  assert.ok(!c.__classes.has('is-exec'), 'is-exec survived a downgrade');
});

// ---------------------------------------------------------------------------
section('the writer of that preference is gated too');

test('setExecRoleAndClose refuses a sales rep', () => {
  const c = makeCtx('sales');
  c.setExecRoleAndClose('cfo');
  assert.ok(!c.__classes.has('is-exec'), 'is-exec granted by the picker handler');
  assert.ok(!c.__persisted, 'the preference was written for an unprivileged role');
  assert.strictEqual(c.__localStore['sd_exec_role'], undefined);
});

test('...and still dismisses the picker rather than leaving it stuck open', () => {
  const c = makeCtx('sales');
  c.setExecRoleAndClose('cfo');
  assert.ok(c.__removed.indexOf('exec-role-picker') >= 0, 'picker left on screen');
});

test('setExecRoleAndClose works for an owner', () => {
  const c = makeCtx('owner');
  c.setExecRoleAndClose('cfo');
  assert.ok(c.__classes.has('is-exec'));
  assert.strictEqual(c.__localStore['sd_exec_role'], 'cfo');
});

// ---------------------------------------------------------------------------
section('the markup half');

test('#sb-executive carries the admin-only class', () => {
  assert.match(html, /<button class="sb-btn admin-only" id="sb-executive"/);
});

test('.sb-btn.admin-only is actually hidden by CSS, and restored to FLEX', () => {
  assert.match(html, /\.sb-btn\.admin-only\{display:none\}/);
  assert.match(html, /body\.is-admin \.sb-btn\.admin-only\{display:flex\}/);
});

console.log('\n' + (fail === 0
  ? 'ALL ' + pass + ' EXEC-ROLE-GATE ASSERTIONS PASS'
  : pass + ' passed, ' + fail + ' FAILED'));
process.exit(fail === 0 ? 0 : 1);
