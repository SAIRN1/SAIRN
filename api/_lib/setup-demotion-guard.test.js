// api/_lib/setup-demotion-guard.test.js
//
// REQUIREMENT: on every app that names a role its licence must never lose, a
//   `setup` call that CHANGES that role's last holder to something else must
//   be refused -- the deactivation guard does not watch this route, and the
//   end state is identical
//
// ── WHAT WAS OPEN, MEASURED RATHER THAN ASSERTED ──────────────────────────
// `setActive()` refuses deactivating the last holder of a sole role. Every
// `setup` on this platform upserts on (license_hash, employee_id) writing the
// role column, so demoting that same person reaches zero holders through a
// door nothing was standing at. Counted across api/*-auth.js on 2026-09-21:
// 17 setup paths, ONE carried a guard (api/sf-auth.js), 16 did not, and FOUR
// were REACHABLE -- grd, sb, scp and sd each declare a SOLE_ROLE, so their
// set_active guard counts only that role. Those four are the same apps
// hardened against DEACTIVATION hours earlier.
//
// ── IT DRIVES THE SHARED FUNCTION AND THEN PROVES THE WIRING SEPARATELY ───
// Two different failures. The guard can be correct and unwired, or wired and
// wrong, and a suite that only drove one would miss the other. Section 1
// drives soleRoleDemotionRefusal() against a real roster through a fake
// PostgREST; section 2 asserts each of the four endpoints actually calls it,
// on the setup path and NOT on bootstrap.
'use strict';
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const LC = require('./employee-lifecycle.js');
const APPS = ['grd-auth.js', 'sb-auth.js', 'scp-auth.js', 'sd-auth.js',
  'sf-auth.js'];

let pass = 0, fail = 0;
function section(s) { console.log('\n' + s); }
async function t(name, fn) {
  try { await fn(); pass += 1; console.log('  ok   ' + name); }
  catch (e) { fail += 1; console.log('  FAIL ' + name + '\n       ' + e.message); }
}

// One active owner, one active admin, plus an INACTIVE second owner -- which
// must not count as cover, the same way it does not in set_active.
const ROSTER = [
  { employee_id: 'OWN', role: 'owner', active: true },
  { employee_id: 'ADM', role: 'admin', active: true },
  { employee_id: 'OLD', role: 'owner', active: false }
];

function ctx(o) {
  return Object.assign({
    provisioningRoles: ['owner', 'admin'], soleRole: 'owner',
    // REQUIRED, not defaulted -- the engine refuses 500 without it. See the
    // seam-check note in employee-lifecycle.js: a field with a silent default
    // is how a refusal ends up in words the app does not use.
    soleMessage: 'This is the only active Owner on this license.',
    licHash: 'L', table: 't', rest: (q) => 'http://x/' + q, headers: {}
  }, o);
}

async function withRoster(rows, fn) {
  const saved = global.fetch;
  let reads = 0;
  global.fetch = async () => { reads += 1; return { ok: true, json: async () => rows }; };
  try { return { out: await fn(), reads: reads }; } finally { global.fetch = saved; }
}

(async function () {
  console.log('the OTHER way to reach zero provisioners -- setup, not set_active');

  section('1. the shared guard, driven against a real roster');

  await t('demoting the ONLY active owner is REFUSED 409 LAST_ADMIN', async () => {
    const { out } = await withRoster(ROSTER, () => LC.soleRoleDemotionRefusal(
      ctx({ newRole: 'admin', employee_id: 'OWN' })));
    assert.ok(out, 'the demotion was allowed');
    assert.strictEqual(out.status, 409);
    assert.strictEqual(out.body.error.code, 'LAST_ADMIN');
  });

  await t('an INACTIVE second owner is not cover -- same rule as set_active', async () => {
    // ROSTER already carries OLD, an inactive owner. If it counted, the arm
    // above would pass for the wrong reason, so this states it explicitly.
    const only = ROSTER.filter((r) => r.employee_id !== 'OLD');
    const { out } = await withRoster(only, () => LC.soleRoleDemotionRefusal(
      ctx({ newRole: 'admin', employee_id: 'OWN' })));
    assert.ok(out && out.status === 409, 'the refusal depends on the inactive row');
  });

  await t('with TWO active owners the same demotion is ALLOWED', async () => {
    const two = ROSTER.concat([{ employee_id: 'OWN2', role: 'owner', active: true }]);
    const { out } = await withRoster(two, () => LC.soleRoleDemotionRefusal(
      ctx({ newRole: 'admin', employee_id: 'OWN' })));
    assert.strictEqual(out, null, 'a safe demotion was refused: ' + JSON.stringify(out));
  });

  await t('demoting a NON-owner is ALLOWED -- the guard is about owners only', async () => {
    const { out } = await withRoster(ROSTER, () => LC.soleRoleDemotionRefusal(
      ctx({ newRole: 'viewer', employee_id: 'ADM' })));
    assert.strictEqual(out, null, 'a non-owner change was refused');
  });

  await t('PROMOTING somebody TO owner is ALLOWED and reads nothing', async () => {
    // Promotion cannot reduce the count, so the roster read is skipped too --
    // a guard that fetched on every setup would be a cost with no answer.
    const { out, reads } = await withRoster(ROSTER, () => LC.soleRoleDemotionRefusal(
      ctx({ newRole: 'owner', employee_id: 'ADM' })));
    assert.strictEqual(out, null);
    assert.strictEqual(reads, 0, 'the roster was read ' + reads + ' time(s) on a promotion');
  });

  await t('re-saving the only owner AS owner is ALLOWED -- a PIN reset is not a demotion', async () => {
    const { out } = await withRoster(ROSTER, () => LC.soleRoleDemotionRefusal(
      ctx({ newRole: 'owner', employee_id: 'OWN' })));
    assert.strictEqual(out, null, 'changing the only owner\'s PIN was refused as a demotion');
  });

  await t('an app that names NO sole role is unaffected, and reads nothing', async () => {
    const { out, reads } = await withRoster(ROSTER, () => LC.soleRoleDemotionRefusal(
      ctx({ soleRole: null, newRole: 'admin', employee_id: 'OWN' })));
    assert.strictEqual(out, null);
    assert.strictEqual(reads, 0);
  });

  await t('a soleRole naming NO REAL ROLE is refused 500, not counted as zero', async () => {
    // The same failure the deactivation guard had: guardRoles matches no row,
    // the refusal is unreachable, and the write goes through.
    const { out, reads } = await withRoster(ROSTER, () => LC.soleRoleDemotionRefusal(
      ctx({ soleRole: 'ownr', newRole: 'admin', employee_id: 'OWN' })));
    assert.ok(out, 'a misconfigured guard allowed the demotion');
    assert.strictEqual(out.status, 500);
    assert.strictEqual(out.body.error.code, 'GUARD_MISCONFIGURED');
    assert.strictEqual(reads, 0, 'it read the roster before noticing it could not run');
  });

  await t('an unreadable roster is an UPSTREAM answer, never a silent allow', async () => {
    const saved = global.fetch;
    global.fetch = async () => ({ ok: false, status: 503, json: async () => ({ m: 'down' }) });
    try {
      const out = await LC.soleRoleDemotionRefusal(ctx({ newRole: 'admin', employee_id: 'OWN' }));
      assert.ok(out && out.upstream,
        'a store that could not answer produced ' + JSON.stringify(out)
        + ' -- "could not tell" must not become "allowed"');
    } finally { global.fetch = saved; }
  });

  section('2. and every reachable endpoint REFUSES it end to end');
  // ── THESE WERE STRING CHECKS AND THE PROBE KILLED THEM ──────────────────
  // The first version asserted that the literal `soleRoleDemotionRefusal`
  // appeared inside each setup block. tests/run_setup_demotion_sabotage_probe.py
  // planted `const demote = null && await lifecycle.soleRoleDemotionRefusal({`
  // in one endpoint at a time -- the call disabled, the STRING still there --
  // and all four arms went SILENT. A check that reads source text cannot see a
  // call that has been short-circuited, and "the name appears in the file" was
  // never the property worth asserting.
  //
  // So each endpoint is now DRIVEN: real handler, real setup action, a roster
  // with exactly one active owner, and the assertion is that the upsert was
  // NOT sent. A refusal that still writes is the failure a status-only check
  // cannot see, so the write is reported separately from the status.
  process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://fake.supabase.co';
  process.env.SUPABASE_SERVICE_ROLE_KEY =
    process.env.SUPABASE_SERVICE_ROLE_KEY || 'fake-service-key';
  process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET || 'test-secret-do-not-use-in-prod';

  const licenseMod = require('./license.js');
  const authMod = require('./auth.js');
  const auditMod = require('./audit.js');
  auditMod.writeAuditLog = async () => true;
  authMod.tokenFromRequest = (req) => req.headers['x-test-token'] || null;
  authMod.verifySessionToken = (tok) => (tok ? JSON.parse(tok) : null);

  const ENDPOINTS = [
    { file: 'grd-auth.js', app: 'sairngrounds', second: 'superintendent',
      sole: 'owner' },
    { file: 'sb-auth.js', app: 'sairnbiz', second: 'hr', sole: 'owner' },
    { file: 'scp-auth.js', app: 'sairnscape', second: 'crew_lead', sole: 'owner' },
    { file: 'sd-auth.js', app: 'stonedesk', second: 'admin', sole: 'owner' },
    // ── THE FIFTH, ADDED WHEN ITS INLINE COPY WAS FOLDED IN (2026-09-22) ──
    // sf-auth.js wrote this guard FIRST, inline, when it was the only app that
    // needed one. It is now a caller of the shared function like the others,
    // so it is driven like the others -- a consolidation that is not driven is
    // a claim that the two implementations agreed.
    { file: 'sf-auth.js', app: 'sairnfreedom', second: 'records.write',
      sole: 'post.govern' }
  ];

  function fakeRes() {
    const r = { statusCode: null, body: null };
    r.status = (c) => { r.statusCode = c; return r; };
    r.json = (b) => { r.body = b; return r; };
    return r;
  }

  // One active owner and one active second-role holder. The owner is the
  // caller, so no role gate can refuse first and make a pass look like a
  // guard firing.
  async function drive(ep, roster, targetId, newRole) {
    licenseMod.validateLicenseKey = async () => ({
      valid: true, active: true, license_hash: 'HASH1', app_id: ep.app
    });
    delete require.cache[require.resolve('../' + ep.file)];
    const handler = require('../' + ep.file);
    let upserted = null;
    const realFetch = global.fetch;
    global.fetch = async (url, opt) => {
      if (!opt || !opt.method || opt.method === 'GET') {
        return { ok: true, status: 200, json: async () => roster };
      }
      if (opt.method === 'POST') {
        upserted = JSON.parse(opt.body);
        return { ok: true, status: 200, json: async () => ([upserted]) };
      }
      return { ok: true, status: 200, json: async () => ([]) };
    };
    try {
      const req = {
        method: 'POST',
        headers: {
          authorization: 'Bearer testkey',
          'x-test-token': JSON.stringify({ employee_id: 'OWN', role: ep.sole })
        },
        body: {
          action: 'setup', employee_id: targetId, pin: '123456', role: newRole
        }
      };
      const res = fakeRes();
      await handler(req, res);
      return { status: res.statusCode, body: res.body, upserted: upserted };
    } finally { global.fetch = realFetch; }
  }

  for (const ep of ENDPOINTS) {
    // Each app's OWN sole role, not a hardcoded 'owner'. SAIRNfreedom's is
    // post.govern, and a fixture that said owner would have driven a roster
    // with no sole-role holder at all -- every arm would then pass because
    // nothing could be the last one.
    const only = [
      { employee_id: 'OWN', role: ep.sole, active: true },
      { employee_id: 'TWO', role: ep.second, active: true }
    ];

    await t(ep.file + ': demoting the ONLY ' + ep.sole + ' through setup is REFUSED and NOT written',
      async () => {
        const r = await drive(ep, only, 'OWN', ep.second);
        assert.strictEqual(r.upserted, null,
          'the upsert was sent -- the licence now has zero active owners and '
          + 'bootstrap still 409s, which is the SD-AUDIT-2026 end state: '
          + JSON.stringify(r.upserted));
        assert.strictEqual(r.status, 409, 'status was ' + r.status
          + ' ' + JSON.stringify(r.body));
        assert.strictEqual(r.body.error.code, 'LAST_ADMIN');
      });

    await t(ep.file + ': ...with a SECOND active ' + ep.sole + ' the same call is allowed',
      async () => {
        const two = only.concat([{ employee_id: 'OWN2', role: ep.sole, active: true }]);
        const r = await drive(ep, two, 'OWN', ep.second);
        assert.ok(r.upserted, 'a safe demotion was refused: ' + r.status
          + ' ' + JSON.stringify(r.body));
        assert.strictEqual(r.status, 200);
      });

    await t(ep.file + ': ...and provisioning a NEW ' + ep.second + ' still works',
      async () => {
        const r = await drive(ep, only, 'NEW', ep.second);
        assert.ok(r.upserted, 'provisioning was refused: ' + r.status
          + ' ' + JSON.stringify(r.body));
        assert.strictEqual(r.status, 200);
      });
  }

  for (const ep of ENDPOINTS) {
    await t(ep.file + ' does NOT guard bootstrap, which mints the first owner', async () => {
      const src = fs.readFileSync(path.join(__dirname, '..', ep.file), 'utf8');
      const i2 = src.indexOf("if (action === 'bootstrap') {");
      if (i2 < 0) { return; }
      const seg = src.slice(i2);
      const end = seg.indexOf("if (action === '", 1);
      const boot = end > 0 ? seg.slice(0, end) : seg;
      assert.strictEqual(boot.indexOf('soleRoleDemotionRefusal'), -1,
        'bootstrap consults the demotion guard -- that path creates the FIRST '
        + 'credential on a licence and cannot demote anybody, so guarding it '
        + 'refuses the one call that makes an owner exist');
    });
  }

  await t('sf-auth.js keeps ITS OWN refusal wording through the shared guard', async () => {
    // The logic is shared; the vocabulary is not. SAIRNfreedom has POSTS with
    // GOVERNING OFFICERS holding CAPABILITIES that you APPOINT, and the shared
    // function's default sentence says license, role and provision. Folding the
    // implementations together without this would have quietly replaced a
    // customer-facing refusal with one using words the app does not use.
    const ep = ENDPOINTS.filter((e) => e.file === 'sf-auth.js')[0];
    const only = [
      { employee_id: 'OWN', role: ep.sole, active: true },
      { employee_id: 'TWO', role: ep.second, active: true }
    ];
    const r = await drive(ep, only, 'OWN', ep.second);
    assert.strictEqual(r.status, 409);
    assert.strictEqual(
      r.body.error.message,
      'This is the only active governing officer on this license. '
      + 'Changing their capability would leave the post with none and lock '
      + 'everyone out with no way back in through the app. Appoint another '
      + 'governing officer first, then change this one.',
      'the consolidation changed the sentence a governing officer reads: '
      + JSON.stringify(r.body.error.message));
  });

  await t('...and every other app states its own sentence too', async () => {
    const ep = ENDPOINTS.filter((e) => e.file === 'grd-auth.js')[0];
    const only = [
      { employee_id: 'OWN', role: ep.sole, active: true },
      { employee_id: 'TWO', role: ep.second, active: true }
    ];
    const r = await drive(ep, only, 'OWN', ep.second);
    assert.strictEqual(r.status, 409);
    assert.match(r.body.error.message, /only active Owner on this license/,
      'got ' + JSON.stringify(r.body.error.message));
    assert.match(r.body.error.message, /leave the property with none/,
      'grd-auth states its OWN sentence now rather than taking a shared '
      + 'default: ' + JSON.stringify(r.body.error.message));
  });

  await t('the five are exactly the apps that name a sole role AND upsert a role', async () => {
    // Derived, so a FIFTH such app cannot appear without this suite noticing.
    const dir = path.join(__dirname, '..');
    const reachable = fs.readdirSync(dir).filter((f) => /-auth\.js$/.test(f)).filter((f) => {
      const s = fs.readFileSync(path.join(dir, f), 'utf8');
      const i = s.indexOf("if (action === 'setup') {");
      if (i < 0) { return false; }
      const seg = s.slice(i);
      const end = seg.indexOf("if (action === '", 1);
      const setup = end > 0 ? seg.slice(0, end) : seg;
      return /const SOLE_ROLE = '/.test(s)
        && setup.indexOf('on_conflict=license_hash,employee_id') !== -1
        && /body: JSON\.stringify\(\{[\s\S]{0,400}\brole\b/.test(setup);
    }).sort();
    assert.deepStrictEqual(reachable, APPS.slice().sort(),
      'the set of endpoints that name a sole role and upsert a role in setup has '
      + 'changed. A new one is UNGUARDED until it is wired. This list used to '
      + 'carry sf-auth.js as an EXCEPTION, because it held its own inline copy of '
      + 'the guard; that copy was folded onto the shared function on 2026-09-22 '
      + 'and the exception went with it. Got: ' + reachable.join(', '));
  });

  console.log('\n' + (fail ? 'FAILED' : 'ok') + '  setup demotion guard: '
    + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
