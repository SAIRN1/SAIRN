// api/_lib/employee-lifecycle.test.js
// Isolation suite for the shared credential-deactivation lifecycle.
//
// Run:  node --test api/_lib/employee-lifecycle.test.js
//
// Nine apps are about to route their only deactivation path through this file,
// and the failure mode is not a wrong answer on screen -- it is a licence with
// zero active provisioners, which cannot be recovered through the API at all
// (`bootstrap` refuses 409 while any row exists; `setup` and `set_active` both
// require an active provisioner). RF-PINNACLE-2026 was found in exactly that
// state. So the tests that matter most here are the refusals.
//
// The PostgREST layer is stubbed and RECORDS its requests, because several of
// these claims are about what was NOT written: a refusal that still issues the
// PATCH is a passing test and a broken guard.

'use strict';
const test = require('node:test');
const assert = require('node:assert');
const lc = require('./employee-lifecycle.js');

const LIC = 'LIC-1';
const TABLE = 'sairnsenior_employee_auth';

let ROWS = [];
let REQUESTS = [];
let FAIL_READ = false;
let FAIL_PATCH = false;
const realFetch = global.fetch;

global.fetch = async function (url, opts) {
  opts = opts || {};
  const method = opts.method || 'GET';
  REQUESTS.push({ url: String(url), method: method, body: opts.body ? JSON.parse(opts.body) : null });
  if (method === 'GET') {
    if (FAIL_READ) return { ok: false, status: 404, json: async () => ({ code: 'PGRST205' }) };
    return { ok: true, status: 200, json: async () => ROWS.map((r) => Object.assign({}, r)) };
  }
  if (method === 'PATCH') {
    if (FAIL_PATCH) return { ok: false, status: 500, json: async () => ({ message: 'boom' }) };
    const m = /employee_id=eq\.([^&]+)/.exec(String(url));
    const id = m ? decodeURIComponent(m[1]) : null;
    const row = ROWS.filter((r) => r.employee_id === id)[0];
    if (row) Object.assign(row, JSON.parse(opts.body));
    return { ok: true, status: 200, json: async () => (row ? [row] : []) };
  }
  return { ok: false, status: 405, json: async () => ({}) };
};

function ctx(caller, body, extra) {
  return Object.assign({
    caller: caller,
    body: body,
    licHash: LIC,
    table: TABLE,
    provisioningRoles: ['owner'],
    roleLabel: 'an Owner',
    rest: (p) => 'https://stub/rest/v1/' + p,
    headers: { apikey: 'stub' }
  }, extra || {});
}

const OWNER = { employee_id: 'e-owner', role: 'owner' };
const OWNER2 = { employee_id: 'e-owner2', role: 'owner' };
const CARER = { employee_id: 'e-carer', role: 'caregiver' };

function seed(rows) {
  REQUESTS = [];
  FAIL_READ = false;
  FAIL_PATCH = false;
  ROWS = rows || [
    { employee_id: 'e-owner', display_name: 'Ann Owner', role: 'owner', active: true },
    { employee_id: 'e-owner2', display_name: 'Bo Owner', role: 'owner', active: true },
    { employee_id: 'e-carer', display_name: 'Cy Carer', role: 'caregiver', active: true },
    { employee_id: 'e-gone', display_name: 'Di Gone', role: 'caregiver', active: false }
  ];
}
const patches = () => REQUESTS.filter((r) => r.method === 'PATCH');

// ── WHO MAY CALL IT ────────────────────────────────────────────────────────

test('no session is refused, and writes nothing', async () => {
  seed();
  const r = await lc.setActive(ctx(null, { employee_id: 'e-carer', active: false, reason: 'left' }));
  assert.strictEqual(r.status, 403);
  assert.strictEqual(r.body.error.code, 'FORBIDDEN');
  assert.strictEqual(patches().length, 0);
});

test('a non-provisioning role is refused even with a valid session', async () => {
  seed();
  const r = await lc.setActive(ctx(CARER, { employee_id: 'e-owner2', active: false, reason: 'x' }));
  assert.strictEqual(r.status, 403);
  assert.strictEqual(patches().length, 0);
});

test('the provisioning roles are READ FROM THE APP, not assumed to be owner', async () => {
  // CLAUDE.md records a guard that hardcoded `owner` and so checked nothing on
  // SAIRNcode forever. SAIRNbiz allows hr; SAIRNgrounds superintendent;
  // SAIRNscape crew_lead. This is the property that makes those work.
  seed([
    { employee_id: 'e-hr', display_name: 'H', role: 'hr', active: true },
    { employee_id: 'e-owner', display_name: 'O', role: 'owner', active: true },
    { employee_id: 'e-staff', display_name: 'S', role: 'staff', active: true }
  ]);
  const hr = { employee_id: 'e-hr', role: 'hr' };
  const refused = await lc.setActive(ctx(hr, { employee_id: 'e-staff', active: false, reason: 'x' }));
  assert.strictEqual(refused.status, 403, 'hr passed a roles list that did not include it');

  const allowed = await lc.setActive(ctx(hr, { employee_id: 'e-staff', active: false, reason: 'x' },
    { provisioningRoles: ['owner', 'hr'], roleLabel: 'Owner or HR' }));
  assert.strictEqual(allowed.status, 200);
  assert.strictEqual(allowed.body.active, false);
});

test('the refusal message names this app\'s roles, not a generic one', async () => {
  seed();
  const r = await lc.setActive(ctx(CARER, { employee_id: 'e-owner2', active: false, reason: 'x' },
    { provisioningRoles: ['owner', 'crew_lead'], roleLabel: 'Owner or Crew Lead' }));
  assert.match(r.body.error.message, /Owner or Crew Lead/);
});

// ── INPUT VALIDATION ───────────────────────────────────────────────────────

test('employee_id is required', async () => {
  seed();
  const r = await lc.setActive(ctx(OWNER, { active: false, reason: 'x' }));
  assert.strictEqual(r.status, 400);
  assert.strictEqual(patches().length, 0);
});

test('active must be a real boolean -- "false" the string is refused', async () => {
  // Otherwise the string "false" is truthy-adjacent in the wrong hands and a
  // deactivation silently becomes an activation.
  seed();
  for (const v of ['false', 'true', 0, 1, null, undefined]) {
    const r = await lc.setActive(ctx(OWNER, { employee_id: 'e-carer', active: v, reason: 'x' }));
    assert.strictEqual(r.status, 400, 'active=' + JSON.stringify(v) + ' was accepted');
  }
  assert.strictEqual(patches().length, 0);
});

test('a reason is required to deactivate', async () => {
  seed();
  const r = await lc.setActive(ctx(OWNER, { employee_id: 'e-carer', active: false }));
  assert.strictEqual(r.status, 400);
  assert.match(r.body.error.message, /reason is required/);
  assert.strictEqual(patches().length, 0);
});

test('a reason is NOT required to reactivate -- turning someone back on is safe', async () => {
  seed();
  const r = await lc.setActive(ctx(OWNER, { employee_id: 'e-gone', active: true }));
  assert.strictEqual(r.status, 200);
  assert.strictEqual(r.body.active, true);
});

test('a whitespace-only reason does not count as a reason', async () => {
  seed();
  const r = await lc.setActive(ctx(OWNER, { employee_id: 'e-carer', active: false, reason: '     ' }));
  assert.strictEqual(r.status, 400);
});

test('an overlong reason is refused rather than truncated', async () => {
  seed();
  const r = await lc.setActive(ctx(OWNER, { employee_id: 'e-carer', active: false, reason: 'x'.repeat(501) }));
  assert.strictEqual(r.status, 400);
  assert.match(r.body.error.message, /500/);
});

// ── THE FOUR LOCKOUT GUARDS ────────────────────────────────────────────────

test('nobody can deactivate themselves', async () => {
  seed();
  const r = await lc.setActive(ctx(OWNER, { employee_id: 'e-owner', active: false, reason: 'leaving' }));
  assert.strictEqual(r.status, 409);
  assert.strictEqual(r.body.error.code, 'SELF_DEACTIVATE');
  assert.strictEqual(patches().length, 0);
  assert.strictEqual(ROWS[0].active, true, 'the row changed anyway');
});

test('but anyone may REactivate themselves -- that is not a lockout risk', async () => {
  // Not reachable in practice (an inactive caller is refused below) but the
  // rule is deliberately about deactivation only, and this pins that.
  seed();
  const r = await lc.setActive(ctx(OWNER, { employee_id: 'e-owner', active: true }));
  assert.strictEqual(r.status, 200);
  assert.strictEqual(r.body.unchanged, true);
});

test('a caller whose OWN credential was deactivated is refused', async () => {
  // A session token outlives the credential it was minted from. Without this
  // re-read, somebody deactivated an hour ago still holds a working
  // provisioning token.
  seed([
    { employee_id: 'e-owner', display_name: 'A', role: 'owner', active: false },
    { employee_id: 'e-owner2', display_name: 'B', role: 'owner', active: true },
    { employee_id: 'e-carer', display_name: 'C', role: 'caregiver', active: true }
  ]);
  const r = await lc.setActive(ctx(OWNER, { employee_id: 'e-carer', active: false, reason: 'x' }));
  assert.strictEqual(r.status, 403);
  assert.strictEqual(r.body.error.code, 'CREDENTIAL_INACTIVE');
  assert.strictEqual(patches().length, 0);
});

test('a caller with no row at all on this licence is refused', async () => {
  seed();
  const ghost = { employee_id: 'e-ghost', role: 'owner' };
  const r = await lc.setActive(ctx(ghost, { employee_id: 'e-carer', active: false, reason: 'x' }));
  assert.strictEqual(r.status, 403);
  assert.strictEqual(r.body.error.code, 'CREDENTIAL_INACTIVE');
  assert.strictEqual(patches().length, 0);
});

test('LAST_ADMIN fires when the caller row no longer holds a provisioning role', async () => {
  // Guard 4 looks unreachable and the five existing copies say so: an active
  // provisioning caller plus a DIFFERENT active provisioning target implies at
  // least two. That reasoning assumes the caller's TOKEN role and the caller's
  // ROW role agree. They need not -- a session token carries a role snapshot
  // and outlives a role change, while activeProvisioners is counted from the
  // ROWS. So: token says owner (passes the gate), the row says caregiver and
  // is active (passes the caller re-check), and the target is the only active
  // owner left. Count is 1 and the guard fires. This is why it is kept.
  seed([
    { employee_id: 'e-owner', display_name: 'A', role: 'caregiver', active: true },
    { employee_id: 'e-owner2', display_name: 'B', role: 'owner', active: true },
    { employee_id: 'e-carer', display_name: 'C', role: 'caregiver', active: true }
  ]);
  const staleToken = { employee_id: 'e-owner', role: 'owner' };
  const r = await lc.setActive(ctx(staleToken, { employee_id: 'e-owner2', active: false, reason: 'x' }));
  assert.strictEqual(r.status, 409);
  assert.strictEqual(r.body.error.code, 'LAST_ADMIN');
  assert.strictEqual(patches().length, 0, 'the last provisioner was written off anyway');
  assert.strictEqual(ROWS[1].active, true);
});

test('the LAST_ADMIN message tells the operator how to get out of it', async () => {
  seed([
    { employee_id: 'e-owner', display_name: 'A', role: 'caregiver', active: true },
    { employee_id: 'e-owner2', display_name: 'B', role: 'owner', active: true }
  ]);
  const staleToken = { employee_id: 'e-owner', role: 'owner' };
  const r = await lc.setActive(ctx(staleToken, { employee_id: 'e-owner2', active: false, reason: 'x' }));
  assert.match(r.body.error.message, /provision another first/i);
});

test('the sole provisioner on a one-row licence cannot be switched off', async () => {
  seed([{ employee_id: 'e-owner', display_name: 'A', role: 'owner', active: true }]);
  // Self-deactivation catches this first, which is the correct answer and the
  // likeliest real attempt. Both doors to zero are closed; this is one of them.
  const self = await lc.setActive(ctx(OWNER, { employee_id: 'e-owner', active: false, reason: 'x' }));
  assert.strictEqual(self.body.error.code, 'SELF_DEACTIVATE');
  assert.strictEqual(patches().length, 0);
  assert.strictEqual(ROWS[0].active, true);
});

test('two active provisioners: deactivating one is allowed, and the last is then self-protected', async () => {
  seed([
    { employee_id: 'e-owner', display_name: 'A', role: 'owner', active: true },
    { employee_id: 'e-owner2', display_name: 'B', role: 'owner', active: true }
  ]);
  const first = await lc.setActive(ctx(OWNER, { employee_id: 'e-owner2', active: false, reason: 'x' }));
  assert.strictEqual(first.status, 200);
  assert.strictEqual(first.body.remaining_admins, 1);
  // e-owner is now the only active provisioner, and the only remaining route
  // to zero is self-deactivation -- which is closed.
  const second = await lc.setActive(ctx(OWNER, { employee_id: 'e-owner', active: false, reason: 'x' }));
  assert.strictEqual(second.body.error.code, 'SELF_DEACTIVATE');
  assert.strictEqual(ROWS.filter((x) => x.active === true && x.role === 'owner').length, 1);
});

test('a non-provisioner target is never blocked by the last-admin guard', async () => {
  seed([
    { employee_id: 'e-owner', display_name: 'A', role: 'owner', active: true },
    { employee_id: 'e-carer', display_name: 'C', role: 'caregiver', active: true }
  ]);
  const r = await lc.setActive(ctx(OWNER, { employee_id: 'e-carer', active: false, reason: 'left' }));
  assert.strictEqual(r.status, 200);
  assert.strictEqual(r.body.remaining_admins, 1);
});

// ── THE WRITE ITSELF ───────────────────────────────────────────────────────

test('an unknown target is a 404 and writes nothing', async () => {
  seed();
  const r = await lc.setActive(ctx(OWNER, { employee_id: 'e-nobody', active: false, reason: 'x' }));
  assert.strictEqual(r.status, 404);
  assert.strictEqual(patches().length, 0);
});

test('a no-op is reported as unchanged and issues NO write', async () => {
  // A double-click must not read as two deactivations in an audit log.
  seed();
  const r = await lc.setActive(ctx(OWNER, { employee_id: 'e-gone', active: false, reason: 'x' }));
  assert.strictEqual(r.status, 200);
  assert.strictEqual(r.body.unchanged, true);
  assert.strictEqual(patches().length, 0);
});

test('a real deactivation writes exactly one PATCH, scoped to licence and employee', async () => {
  seed();
  const r = await lc.setActive(ctx(OWNER, { employee_id: 'e-carer', active: false, reason: 'left the agency' }));
  assert.strictEqual(r.status, 200);
  const p = patches();
  assert.strictEqual(p.length, 1);
  assert.match(p[0].url, /license_hash=eq\.LIC-1/);
  assert.match(p[0].url, /employee_id=eq\.e-carer/);
  assert.strictEqual(p[0].body.active, false);
  assert.ok(p[0].body.updated_at, 'updated_at was not stamped');
  // And nothing else was touched.
  assert.strictEqual(ROWS.filter((x) => x.active === true).length, 2);
});

test('the PATCH never carries a role, a pin or a display name', async () => {
  // The only field this action is allowed to change is `active`. A role that
  // rode along here would be a privilege-escalation path through a
  // deactivation endpoint.
  seed();
  await lc.setActive(ctx(OWNER, { employee_id: 'e-carer', active: false, reason: 'x',
    role: 'owner', pin: '000000', display_name: 'Escalated', license_hash: 'OTHER' }));
  const b = patches()[0].body;
  assert.deepStrictEqual(Object.keys(b).sort(), ['active', 'updated_at']);
});

test('remaining_admins is recomputed, not decremented', async () => {
  // Subtracting one is wrong the moment the target was not a provisioner.
  seed();
  const nonProv = await lc.setActive(ctx(OWNER, { employee_id: 'e-carer', active: false, reason: 'x' }));
  assert.strictEqual(nonProv.body.remaining_admins, 2, 'a non-provisioner changed the provisioner count');

  seed();
  const prov = await lc.setActive(ctx(OWNER, { employee_id: 'e-owner2', active: false, reason: 'x' }));
  assert.strictEqual(prov.body.remaining_admins, 1);
});

test('reactivating a provisioner raises the count', async () => {
  seed([
    { employee_id: 'e-owner', display_name: 'A', role: 'owner', active: true },
    { employee_id: 'e-owner2', display_name: 'B', role: 'owner', active: false }
  ]);
  const r = await lc.setActive(ctx(OWNER, { employee_id: 'e-owner2', active: true }));
  assert.strictEqual(r.body.remaining_admins, 2);
});

// ── UPSTREAM FAILURES ──────────────────────────────────────────────────────

test('a failed roster read returns upstream, so the endpoint can name its own SQL file', async () => {
  seed();
  FAIL_READ = true;
  const r = await lc.setActive(ctx(OWNER, { employee_id: 'e-carer', active: false, reason: 'x' }));
  assert.ok(r.upstream, 'a PostgREST failure was turned into a decision');
  assert.ok(!r.status);
  assert.strictEqual(patches().length, 0);
});

test('a failed PATCH returns upstream rather than reporting success', async () => {
  seed();
  FAIL_PATCH = true;
  const r = await lc.setActive(ctx(OWNER, { employee_id: 'e-carer', active: false, reason: 'x' }));
  assert.ok(r.upstream);
  assert.ok(!r.status, 'a failed write reported a status');
});

// ── AUDIT ──────────────────────────────────────────────────────────────────

test('with no audit function, the response carries no audited field at all', async () => {
  // `audited:false` on an app with no audit log reads as "we tried and failed".
  seed();
  const r = await lc.setActive(ctx(OWNER, { employee_id: 'e-carer', active: false, reason: 'x' }));
  assert.ok(!('audited' in r.body));
});

test('with an audit function, every outcome is recorded -- refusals included', async () => {
  const events = [];
  const audit = async (e, d) => { events.push({ e: e, d: d }); return true; };

  seed();
  await lc.setActive(ctx(OWNER, { employee_id: 'e-owner', active: false, reason: 'x' }, { audit: audit }));
  assert.strictEqual(events[0].e, 'credential_change_refused');
  assert.strictEqual(events[0].d.reason_code, 'SELF_DEACTIVATE');

  seed();
  const ok = await lc.setActive(ctx(OWNER, { employee_id: 'e-carer', active: false, reason: 'left' }, { audit: audit }));
  const last = events[events.length - 1];
  assert.strictEqual(last.e, 'credential_deactivated');
  assert.strictEqual(last.d.reason, 'left');
  assert.strictEqual(last.d.target_role, 'caregiver');
  assert.strictEqual(ok.body.audited, true);
});

test('a reactivation is a distinct audit event from a deactivation', async () => {
  const events = [];
  const audit = async (e, d) => { events.push(e); return true; };
  seed();
  await lc.setActive(ctx(OWNER, { employee_id: 'e-gone', active: true }, { audit: audit }));
  assert.strictEqual(events[0], 'credential_reactivated');
});

test('an audit that fails is reported as audited:false, not swallowed', async () => {
  seed();
  const audit = async () => false;
  const r = await lc.setActive(ctx(OWNER, { employee_id: 'e-carer', active: false, reason: 'x' }, { audit: audit }));
  assert.strictEqual(r.body.audited, false);
  assert.strictEqual(r.body.ok, true, 'the write still happened');
});

// ── ROSTER ─────────────────────────────────────────────────────────────────

test('roster returns inactive rows, which is the whole point', async () => {
  seed();
  const r = await lc.roster(ctx(OWNER, {}, { canView: true, viewLabel: 'an Owner' }));
  assert.strictEqual(r.status, 200);
  assert.strictEqual(r.body.employees.length, 4);
  assert.ok(r.body.employees.some((e) => e.active === false), 'no inactive row came back');
});

test('roster never returns a pin hash, salt, or lockout state', async () => {
  seed();
  const r = await lc.roster(ctx(OWNER, {}, { canView: true }));
  const s = JSON.stringify(r.body);
  ['pin_hash', 'pin_salt', 'failed_attempts', 'locked_until'].forEach((f) => {
    assert.strictEqual(s.indexOf(f), -1, f + ' reached the roster');
  });
  // And it is not merely absent from the fixture -- the SELECT names its columns.
  assert.strictEqual(lc.ROSTER_SELECT, 'employee_id,display_name,role,active');
  const read = REQUESTS.filter((q) => q.method === 'GET')[0];
  assert.match(read.url, /select=employee_id,display_name,role,active/);
});

test('roster refuses a caller who may not view it', async () => {
  seed();
  const r = await lc.roster(ctx(CARER, {}, { canView: false, viewLabel: 'Owner or Billing' }));
  assert.strictEqual(r.status, 403);
  assert.match(r.body.error.message, /Owner or Billing/);
});

test('roster refuses a caller whose own credential was deactivated', async () => {
  seed([
    { employee_id: 'e-owner', display_name: 'A', role: 'owner', active: false },
    { employee_id: 'e-carer', display_name: 'C', role: 'caregiver', active: true }
  ]);
  const r = await lc.roster(ctx(OWNER, {}, { canView: true }));
  assert.strictEqual(r.status, 403);
  assert.strictEqual(r.body.error.code, 'CREDENTIAL_INACTIVE');
});

test('roster scopes to one licence', async () => {
  seed();
  await lc.roster(ctx(OWNER, {}, { canView: true }));
  assert.match(REQUESTS.filter((q) => q.method === 'GET')[0].url, /license_hash=eq\.LIC-1/);
});

test.after(() => { global.fetch = realFetch; });
