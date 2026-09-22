// api/_lib/last-admin-sole-role.test.js
//
// REQUIREMENT: on an app with MORE THAN ONE provisioning role, the holder of a
// non-sole provisioning role cannot deactivate the last holder of the sole one.
//
// ── WHY THIS SUITE EXISTS, AND IT IS NOT A HYPOTHETICAL ─────────────────────
// api/_lib/employee-lifecycle.js setActive() counts its last-admin guard over
// `provisioningRoles` unless the caller names a `soleRole`. That was exactly
// right while every app had ONE provisioning role, because "who may provision"
// and "who must not reach zero" were the same set.
//
// THREE APPS HAVE TWO, and there the questions come apart. SAIRNgrounds
// ['owner','superintendent'], SAIRNbiz ['owner','hr'] and SAIRNscape
// ['owner','crew_lead'] each passed no soleRole, so a superintendent / HR
// officer / crew lead deactivating the only active owner saw TWO active
// provisioners, the guard never fired, and the licence reached ZERO owners.
// Driven before the fix: 200 ALLOWED and the PATCH was sent, in all three.
//
// AND THERE IS NO WAY BACK, which is what makes it terminal rather than untidy.
// Three facts, read out of each of the three endpoints at fix time rather than
// carried over from SAIRNfreedom: `bootstrap` creates role 'owner'; its
// existence check is `select=id&limit=1` with NO `active` filter, so it answers
// 409 even when every credential is inactive; and `setup` refuses `role ===
// 'owner' && caller.role !== 'owner'`, so the surviving deputy cannot mint a
// replacement. A licence dead through the API, recoverable only by direct
// database access -- which is how SD-AUDIT-2026 was lost.
//
// THOSE THREE ARE RATIONALE, NOT ARMS, and saying so is the point: no assertion
// below re-checks them, so this paragraph is as of 2026-09-21 and nothing will
// announce the day it stops being true. It is written down because it is what
// makes 'owner' the right sole role for these three, and a reader deciding
// whether to change that needs the reasoning, not a restatement of the fix.
// An earlier draft DID assert them across every app here and was wrong:
// SAIRNfreedom's `setup` admits any provisioning-role caller, so a deputy CAN
// appoint a new governor there and zero holders is recoverable. Same guard,
// different weight -- load-bearing in three apps, defence-in-depth in the
// fourth -- which is exactly why one shape must not be asserted across all of
// them.
//
// ── THE OVER-RESTRICTION HALF IS THE POINT, NOT A COURTESY ──────────────────
// A guard that refuses everything also "fixes" this, and would be a worse bug
// than the one it replaced: nobody could ever deactivate anybody. Every arm
// below therefore comes in both directions -- the refusal AND the three
// legitimate deactivations that must still go through, with the PATCH asserted
// either sent or not sent rather than inferred from the status code.
//
// ── THE CONSTANTS ARE PARSED OUT OF THE ENDPOINTS, NOT RETYPED HERE ─────────
// A role list retyped into a test is a test of the typing. These are read from
// the endpoint source, so renaming a role in the endpoint without updating it
// here fails rather than silently testing a role nobody has.

const fs = require('fs');
const path = require('path');
const assert = require('assert');

const API = path.join(__dirname, '..');
const lifecycle = require('./employee-lifecycle.js');

// Every endpoint wired onto the shared helper that has MORE THAN ONE
// provisioning role. Derived below rather than listed, so a fourth such app
// cannot be added without this suite seeing it.
function endpointConsts(file) {
  const s = fs.readFileSync(path.join(API, file), 'utf8');
  const roles = /const PROVISIONING_ROLES = (\[[^\]]*\]);/.exec(s);
  if (!roles) return null;
  const label = /const PROVISIONING_LABEL = '([^']*)';/.exec(s);
  const sole = /const SOLE_ROLE = '([^']*)';/.exec(s);
  // What the call site ACTUALLY passes -- not what the file merely declares. A
  // SOLE_ROLE constant that no call site forwards is a comment, not a guard.
  const call = /lifecycle\.setActive\(\{[\s\S]*?\n {6}\}\);/.exec(s);
  const passed = call ? /soleRole:\s*([A-Za-z_.]+|null)/.exec(call[0]) : null;
  return {
    file: file,
    roles: JSON.parse(roles[1].replace(/'/g, '"')),
    label: label ? label[1] : 'a provisioner',
    soleRoleConst: sole ? sole[1] : null,
    soleRolePassed: passed ? passed[1] : undefined
  };
}

const ALL_MULTI = fs.readdirSync(API)
  .filter((f) => /^[a-z-]+-auth\.js$/.test(f))
  .map(endpointConsts)
  .filter((c) => c && c.roles.length > 1)
  .sort((a, b) => a.file.localeCompare(b.file));

// ── AN ENDPOINT THAT DOES NOT CALL THE ENGINE CANNOT BE TESTED THROUGH IT ───
// Split, and the split is NOT a skip. The arms below drive
// api/_lib/employee-lifecycle.js, so they can only speak for endpoints that
// call it. api/sd-auth.js declares ['owner','admin'] and has its OWN
// hand-written set_active -- it is in the wiring suite's PRE_EXISTING list --
// so running the engine arms against ITS constants would report on code
// StoneDesk does not execute, which is worse than not testing it.
//
// NOT_WIRED IS THEREFORE ASSERTED, NOT IGNORED. The arm below names every
// multi-role endpoint that is off the helper, so one cannot quietly drop out
// of this suite's reach by never having been in it -- which is exactly how
// api/sd-auth.js's identical defect survived the 2026-09-21 sweep of the other
// three.
//
// api/sd-auth.js IS NOW FIXED (2026-09-21, later the same day) -- it narrows
// its own guard to GUARD_ROLES = ['owner'] instead of passing soleRole, and
// api/sd-auth-last-admin.test.js plus
// tests/run_sd_auth_last_admin_sabotage_probe.py cover it. It stays on this
// list because the list is about REACH, not about health: these arms drive the
// shared engine and still cannot speak for an endpoint that does not call it.
// ── MATCHES THE CALL, NOT THE WORD, AND IT HAD TO LEARN THAT ───────────────
// This was `src.indexOf('employee-lifecycle') !== -1` and it broke the same
// day: api/sd-auth.js got a comment explaining that the other three apps use
// the shared helper, and the substring match promptly classified StoneDesk as
// WIRED on the strength of a sentence describing somebody else's code. The
// engine arms then ran against an endpoint that never calls the engine, and
// the pinned NOT_WIRED list emptied itself.
//
// Caught by this suite's own arms rather than by review, which is the argument
// for pinning the list by name. A predicate that cannot tell a call from a
// mention of a call is reading prose, not wiring -- so this matches the actual
// require and the actual call site.
const isWired = (c) => {
  const s = fs.readFileSync(path.join(API, c.file), 'utf8');
  return /require\([^)]*employee-lifecycle[^)]*\)/.test(s)
      && /lifecycle\.setActive\(/.test(s);
};
const MULTI = ALL_MULTI.filter(isWired);
const MULTI_NOT_WIRED = ALL_MULTI.filter((c) => !isWired(c));

// Drive setActive() against a roster, with the store mocked at fetch().
// `patched` is recorded separately from the status so a refusal that still
// wrote cannot pass as a refusal.
async function drive(o) {
  const roster = o.roster;
  let patched = null;
  const realFetch = global.fetch;
  global.fetch = async (url, opt) => {
    if (!opt || opt.method === undefined) return { ok: true, json: async () => roster };
    if (opt.method === 'PATCH') {
      patched = JSON.parse(opt.body);
      return { ok: true, json: async () => [{}] };
    }
    return { ok: true, json: async () => [] };
  };
  try {
    const out = await lifecycle.setActive({
      caller: { employee_id: o.callerId, role: o.callerRole, license_hash: 'L' },
      body: { employee_id: o.targetId, active: false, reason: 'left the company' },
      licHash: 'L', table: 't',
      provisioningRoles: o.roles, roleLabel: o.label,
      soleRole: o.soleRole,
      rest: (q) => 'http://x/' + q, headers: {}
    });
    return {
      status: out.status,
      code: (out.body && out.body.error && out.body.error.code) || null,
      patched: !!patched
    };
  } finally { global.fetch = realFetch; }
}

let pass = 0, fail = 0;
function ok(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
async function okAsync(name, fn) {
  try { await fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('\n' + t); }

(async function () {
  console.log('the last-admin guard on apps with MORE THAN ONE provisioning role');

  section('THE SET IS DERIVED, so a fourth such app cannot arrive unnoticed');

  ok('there is at least one multi-provisioning-role endpoint to test', () => {
    assert.ok(MULTI.length > 0,
      'no endpoint declares more than one PROVISIONING_ROLES entry -- either the '
      + 'parse broke or the endpoints were restructured; either way this suite is '
      + 'no longer reading its subject');
  });

  ok('every one of them names a sole role AND the call site passes it', () => {
    const bad = MULTI.filter((c) => !c.soleRoleConst
      || c.soleRolePassed === 'null' || c.soleRolePassed === undefined);
    assert.deepStrictEqual(bad.map((c) => c.file), [],
      'these declare more than one provisioning role and do not pass a soleRole, '
      + 'so their last-admin guard counts over BOTH roles and the second role can '
      + 'empty the licence of the first: ' + bad.map((c) => c.file).join(', '));
  });

  // ── THE KNOWN-UNFIXED LIST, PINNED BY NAME AND BY COUNT ──────────────────
  // A multi-role endpoint off the shared helper is NOT covered by anything
  // below. Pinning the exact list means a FOURTH one cannot appear silently,
  // and it means this suite states what it does not cover instead of implying
  // it covers everything it enumerated.
  ok('every multi-role endpoint that is OFF the shared helper is named here', () => {
    assert.deepStrictEqual(MULTI_NOT_WIRED.map((c) => c.file), ['sd-auth.js'],
      'the set of multi-provisioning-role endpoints NOT on '
      + 'api/_lib/employee-lifecycle.js has changed. Nothing below tests these -- '
      + 'they run their own hand-written set_active. If an endpoint APPEARED '
      + 'here, it needs its own driven check and its own suite the way '
      + 'api/sd-auth.js got one; if one DISAPPEARED, it was wired and this list '
      + 'should shrink deliberately rather than by accident.');
  });

  ok('the sole role each one names is actually one of its provisioning roles', () => {
    MULTI.forEach((c) => {
      assert.ok(c.roles.indexOf(c.soleRoleConst) !== -1,
        c.file + ' names SOLE_ROLE ' + JSON.stringify(c.soleRoleConst)
        + ' which is not in PROVISIONING_ROLES ' + JSON.stringify(c.roles)
        // ── THIS SENTENCE SAID THE OPPOSITE UNTIL 2026-09-21 ──────────────
        // It read "the guard would then count zero holders and refuse every
        // deactivation, which is the over-restrictive failure". That is
        // backwards, and this was the ONLY place on the platform describing
        // the scenario. DRIVEN: guardRoles becomes the one-member array,
        // activeProvisioners counts ZERO, and the refusal condition also
        // tests `guardRoles.indexOf(target.role) !== -1` -- false for every
        // real row -- so the branch is UNREACHABLE and the deactivation is
        // ALLOWED. Permissive, not restrictive. A reader who hit this arm and
        // believed its message would have downgraded a trapdoor to an
        // annoyance. The arms below drive it in the real direction rather
        // than asserting it in prose.
        + ' -- the guard then counts zero holders AND its role test can never '
        + 'match, so the refusal branch is unreachable and the last holder can '
        + 'be deactivated. Permissive, not restrictive.');
    });
  });

  // ── AND THE STATIC ARM ABOVE IS NOT ENOUGH, WHICH IS WHY THESE EXIST ────
  // It parses `const SOLE_ROLE = '...'` and the call site with a regex, and it
  // only looks at MULTI endpoints. A single-role endpoint passing a wrong
  // soleRole, a value that is not a literal, a spelling the regex misses, or a
  // brand-new caller are all invisible to it. The guard's behaviour is decided
  // at RUNTIME by a string, so the runtime is where it has to be checked.
  section('A soleRole THAT NAMES NO REAL ROLE -- it must fail CLOSED and say so');

  await okAsync('a mistyped soleRole is REFUSED, not silently unguarded', async () => {
    const r = await drive({
      roster: [
        { employee_id: 'GOV', role: 'post.govern', active: true },
        { employee_id: 'DEP', role: 'post.govern.deputy', active: true }
      ],
      callerId: 'DEP', callerRole: 'post.govern.deputy', targetId: 'GOV',
      roles: ['post.govern', 'post.govern.deputy'], label: 'an officer',
      soleRole: 'post.governor'                       // one letter, no such role
    });
    assert.strictEqual(r.patched, false,
      'the sole-role holder was DEACTIVATED -- guardRoles matched no row, so the '
      + 'refusal branch was unreachable and the guard silently did nothing');
    assert.strictEqual(r.status, 500, 'status was ' + r.status);
    assert.strictEqual(r.code, 'GUARD_MISCONFIGURED', 'code was ' + r.code);
  });

  await okAsync('...and an EMPTY-STRING soleRole is treated as absent, not as a typo', async () => {
    // '' is falsy, so `ctx.soleRole || null` already means "no sole role" and
    // the guard counts over every provisioning role. That is the OLD behaviour
    // and it is safe; refusing it would break the nine callers passing null.
    const r = await drive({
      roster: [
        { employee_id: 'A', role: 'owner', active: true },
        { employee_id: 'B', role: 'hr', active: true }
      ],
      callerId: 'B', callerRole: 'hr', targetId: 'A',
      roles: ['owner', 'hr'], label: 'an admin', soleRole: ''
    });
    assert.strictEqual(r.status, 200, 'an absent soleRole changed behaviour: ' + r.status);
    assert.strictEqual(r.patched, true);
  });

  await okAsync('a VALID soleRole still refuses -- the check does not refuse everything', async () => {
    const r = await drive({
      roster: [
        { employee_id: 'GOV', role: 'post.govern', active: true },
        { employee_id: 'DEP', role: 'post.govern.deputy', active: true }
      ],
      callerId: 'DEP', callerRole: 'post.govern.deputy', targetId: 'GOV',
      roles: ['post.govern', 'post.govern.deputy'], label: 'an officer',
      soleRole: 'post.govern'
    });
    assert.strictEqual(r.status, 409);
    assert.strictEqual(r.code, 'LAST_ADMIN');
    assert.strictEqual(r.patched, false);
  });

  await okAsync('...and a valid soleRole still ALLOWS a deactivation it should allow', async () => {
    const r = await drive({
      roster: [
        { employee_id: 'GOV', role: 'post.govern', active: true },
        { employee_id: 'GOV2', role: 'post.govern', active: true },
        { employee_id: 'DEP', role: 'post.govern.deputy', active: true }
      ],
      callerId: 'GOV', callerRole: 'post.govern', targetId: 'GOV2',
      roles: ['post.govern', 'post.govern.deputy'], label: 'an officer',
      soleRole: 'post.govern'
    });
    assert.strictEqual(r.status, 200, 'the guard refused a safe deactivation: ' + r.status);
    assert.strictEqual(r.patched, true);
  });

  await okAsync('the misconfiguration is refused BEFORE the roster is even read', async () => {
    // A 500 that still fetched would mean the check runs after the work, and
    // an unreachable store could then mask the misconfiguration entirely.
    let reads = 0;
    const realFetch = global.fetch;
    global.fetch = async () => { reads += 1; return { ok: true, json: async () => [] }; };
    try {
      const out = await lifecycle.setActive({
        caller: { employee_id: 'DEP', role: 'hr' },
        body: { employee_id: 'A', active: false, reason: 'x' },
        licHash: 'L', table: 't', provisioningRoles: ['owner', 'hr'],
        roleLabel: 'an admin', soleRole: 'ownr',
        rest: (q) => 'http://x/' + q, headers: {}
      });
      assert.strictEqual(out.status, 500);
      assert.strictEqual(out.body.error.code, 'GUARD_MISCONFIGURED');
      assert.strictEqual(reads, 0, 'the roster was read ' + reads + ' time(s) before refusing');
    } finally { global.fetch = realFetch; }
  });

  await okAsync('the refusal NAMES the bad value and the roles it was checked against', async () => {
    const out = await lifecycle.setActive({
      caller: { employee_id: 'DEP', role: 'hr' },
      body: { employee_id: 'A', active: false, reason: 'x' },
      licHash: 'L', table: 't', provisioningRoles: ['owner', 'hr'],
      roleLabel: 'an admin', soleRole: 'ownr',
      rest: (q) => 'http://x/' + q, headers: {}
    });
    const m = out.body.error.message;
    assert.match(m, /ownr/, 'the message does not name the bad value: ' + m);
    assert.match(m, /owner/, 'the message does not name the real roles: ' + m);
  });

  // ── THE BEHAVIOUR, DRIVEN THROUGH THE REAL ENGINE ────────────────────────
  section('THE REFUSAL -- the deputy role cannot take the last sole-role holder');

  for (const c of MULTI) {
    const deputy = c.roles.filter((r) => r !== c.soleRoleConst)[0];
    const base = { roles: c.roles, label: c.label, soleRole: c.soleRoleConst };

    await okAsync(c.file + ': ' + deputy + ' deactivating the only ' + c.soleRoleConst
      + ' is REFUSED 409 and no PATCH is sent', async () => {
        const r = await drive(Object.assign({}, base, {
          callerId: 'E2', callerRole: deputy, targetId: 'E1',
          roster: [{ employee_id: 'E1', role: c.soleRoleConst, active: true },
                   { employee_id: 'E2', role: deputy, active: true }]
        }));
        assert.strictEqual(r.status, 409, 'status was ' + r.status + ' ' + r.code);
        assert.strictEqual(r.code, 'LAST_ADMIN');
        assert.strictEqual(r.patched, false,
          'REFUSED AND STILL WROTE -- the status is a refusal and the store was '
          + 'patched anyway, which is worse than no guard because it reads as safe');
      });

    // ── THE CONTROL THAT MAKES THE ARM ABOVE MEAN SOMETHING ────────────────
    // Without these three, a guard that refused every deactivation would pass.
    await okAsync(c.file + ': with TWO active ' + c.soleRoleConst
      + 's the same call is ALLOWED', async () => {
        const r = await drive(Object.assign({}, base, {
          callerId: 'E2', callerRole: deputy, targetId: 'E1',
          roster: [{ employee_id: 'E1', role: c.soleRoleConst, active: true },
                   { employee_id: 'E3', role: c.soleRoleConst, active: true },
                   { employee_id: 'E2', role: deputy, active: true }]
        }));
        assert.strictEqual(r.status, 200, 'status was ' + r.status + ' ' + r.code);
        assert.strictEqual(r.patched, true, 'allowed but nothing was written');
      });

    await okAsync(c.file + ': deactivating the last ' + deputy
      + ' is ALLOWED -- the guard is about ' + c.soleRoleConst + 's only', async () => {
        const r = await drive(Object.assign({}, base, {
          callerId: 'E1', callerRole: c.soleRoleConst, targetId: 'E2',
          roster: [{ employee_id: 'E1', role: c.soleRoleConst, active: true },
                   { employee_id: 'E2', role: deputy, active: true }]
        }));
        assert.strictEqual(r.status, 200, 'status was ' + r.status + ' ' + r.code);
        assert.strictEqual(r.patched, true, 'allowed but nothing was written');
      });

    await okAsync(c.file + ': an INACTIVE second ' + c.soleRoleConst
      + ' does not count as cover', async () => {
        const r = await drive(Object.assign({}, base, {
          callerId: 'E2', callerRole: deputy, targetId: 'E1',
          roster: [{ employee_id: 'E1', role: c.soleRoleConst, active: true },
                   { employee_id: 'E3', role: c.soleRoleConst, active: false },
                   { employee_id: 'E2', role: deputy, active: true }]
        }));
        assert.strictEqual(r.status, 409, 'an inactive holder was counted as cover');
        assert.strictEqual(r.patched, false);
      });
  }

  // ── THE NEGATIVE CONTROL ON THE HARNESS ITSELF ───────────────────────────
  // If passing no soleRole did NOT reproduce the defect, this harness would be
  // proving nothing about the fix -- the refusal could be coming from anywhere.
  section('THE HARNESS REPRODUCES THE DEFECT -- without soleRole, the write lands');

  for (const c of MULTI) {
    const deputy = c.roles.filter((r) => r !== c.soleRoleConst)[0];
    await okAsync(c.file + ': soleRole ABSENT -> 200 and the PATCH IS SENT '
      + '(this is what shipped until 2026-09-21)', async () => {
        const r = await drive({
          roles: c.roles, label: c.label, soleRole: undefined,
          callerId: 'E2', callerRole: deputy, targetId: 'E1',
          roster: [{ employee_id: 'E1', role: c.soleRoleConst, active: true },
                   { employee_id: 'E2', role: deputy, active: true }]
        });
        assert.strictEqual(r.status, 200,
          'the defect no longer reproduces without soleRole -- the guard moved, '
          + 'and every arm above may now be passing for a different reason');
        assert.strictEqual(r.patched, true);
      });
  }

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  if (fail) { console.log('FAILURES ABOVE'); process.exit(1); }
})();
