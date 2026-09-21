// api/sd-auth-last-admin.test.js
//
// REQUIREMENT: an `admin` cannot deactivate the last active `owner` on a
// StoneDesk licence, and everything else about deactivation still works.
//
// ── WHY THIS IS A SEPARATE SUITE FROM THE OTHER THREE APPS ─────────────────
// SAIRNgrounds, SAIRNbiz and SAIRNscape had the identical defect and it was
// fixed by passing `soleRole` to api/_lib/employee-lifecycle.js, with
// api/_lib/last-admin-sole-role.test.js covering them. StoneDesk is in that
// suite's PRE_EXISTING list -- it runs its OWN hand-written set_active and
// never calls the shared helper -- so those arms cannot speak for it. That is
// exactly how this instance survived the sweep of the other three: it was
// never in the shared suite's reach to begin with.
//
// ── THE DEFECT, AND THE COMMENT THAT PROTECTED IT ──────────────────────────
// The guard counted active PROVISIONERS (owner + admin) rather than active
// OWNERS, so an admin deactivating the last owner saw two provisioners, the
// guard never fired, and the call answered 200 with the PATCH sent. The
// licence reached zero owners -- and `bootstrap` 409s without filtering on
// active while `setup` refuses a non-owner creating an owner, so there is no
// route back through the app. That is the SD-AUDIT-2026 loss.
//
// The guard's own comment called itself "unreachable by construction", which
// is the defect stated as a reassurance: it never fired, and non-firing was
// recorded as proof it was not needed. Both the logic and the comment are
// corrected; this suite is what stops either from coming back.
//
// ── BOTH DIRECTIONS, ALWAYS ────────────────────────────────────────────────
// A guard that refuses every deactivation also makes the first arm pass and
// would be worse than the bug. Three of the cases below MUST still be
// allowed, and every case asserts whether the PATCH was actually SENT rather
// than inferring it from the status code -- a refusal that still writes is
// the failure a status-only assertion cannot see.

const path = require('path');
const assert = require('assert');

const ROOT = path.join(__dirname, '..');
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://fake.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'fake-service-key';
// Same form api/_lib/auth.test.js uses. Never reached in anger here -- the
// token verifier is stubbed below -- but the module reads it at require time.
process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET || 'test-secret-do-not-use-in-prod';

const licenseMod = require(path.join(ROOT, 'api/_lib/license.js'));
licenseMod.validateLicenseKey = async () => ({
  valid: true, active: true, license_hash: 'HASH1', app_id: 'stonedesk'
});
const authMod = require(path.join(ROOT, 'api/_lib/auth.js'));
authMod.tokenFromRequest = (req) => req.headers['x-test-token'] || null;
authMod.verifySessionToken = (t) => (t ? JSON.parse(t) : null);
const auditMod = require(path.join(ROOT, 'api/_lib/audit.js'));
const auditCalls = [];
auditMod.writeAuditLog = async (u, k, entry) => { auditCalls.push(entry); return true; };

const handler = require(path.join(ROOT, 'api/sd-auth.js'));

// Drive the real handler. `patched` is captured from the PATCH leg and
// reported separately from the status, so "refused" means refused AND did not
// write.
async function setActive(roster, callerRole, targetId) {
  const caller = roster.filter(
    (x) => x.role === callerRole && x.active && x.employee_id !== targetId)[0];
  assert.ok(caller, 'the fixture has no active ' + callerRole + ' to act as caller');
  let patched = null;
  const realFetch = global.fetch;
  global.fetch = async (url, opt) => {
    if (!opt || !opt.method || opt.method === 'GET') {
      return { ok: true, status: 200, json: async () => roster };
    }
    if (opt.method === 'PATCH') {
      patched = JSON.parse(opt.body);
      return { ok: true, status: 200, json: async () => [{}] };
    }
    return { ok: true, status: 200, json: async () => [] };
  };
  const res = { statusCode: null, body: null,
    status(c) { this.statusCode = c; return this; },
    json(b) { this.body = b; return this; } };
  try {
    await handler({
      method: 'POST',
      headers: { authorization: 'Bearer SD-TEST',
        'x-test-token': JSON.stringify({ employee_id: caller.employee_id,
          role: callerRole, license_hash: 'HASH1', app: 'stonedesk' }) },
      body: { action: 'set_active', employee_id: targetId, active: false,
              reason: 'left the company' }
    }, res);
  } finally { global.fetch = realFetch; }
  return { status: res.statusCode, body: res.body,
           code: (res.body && res.body.error && res.body.error.code) || null,
           patched: !!patched };
}

const OWNER = { employee_id: 'E1', role: 'owner', active: true };
const OWNER2 = { employee_id: 'E4', role: 'owner', active: true };
const OWNER_OFF = { employee_id: 'E5', role: 'owner', active: false };
const ADMIN = { employee_id: 'E2', role: 'admin', active: true };
const ADMIN2 = { employee_id: 'E3', role: 'admin', active: true };

let pass = 0, fail = 0;
async function test(name, fn) {
  try { await fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('\n' + t); }

(async function () {
  console.log('api/sd-auth.js -- an admin cannot empty the licence of owners');

  section('THE REFUSAL');

  await test('an ADMIN deactivating the ONLY active OWNER is refused 409 '
    + 'LAST_ADMIN and NOTHING is written', async () => {
      const r = await setActive([OWNER, ADMIN], 'admin', 'E1');
      assert.strictEqual(r.status, 409, 'status was ' + r.status + ' ' + r.code);
      assert.strictEqual(r.code, 'LAST_ADMIN');
      assert.strictEqual(r.patched, false,
        'REFUSED AND STILL WROTE -- the status says no and the store says yes, '
        + 'which reads as safe and is not');
    });

  await test('an INACTIVE second owner does NOT count as cover', async () => {
    const r = await setActive([OWNER, OWNER_OFF, ADMIN], 'admin', 'E1');
    assert.strictEqual(r.status, 409, 'an inactive owner was counted as cover');
    assert.strictEqual(r.patched, false);
  });

  await test('the refusal is AUDITED, and the number it logs is the OWNER '
    + 'count that triggered it', async () => {
      auditCalls.length = 0;
      await setActive([OWNER, ADMIN, ADMIN2], 'admin', 'E1');
      const refusals = auditCalls.filter(
        (a) => a.detail && a.detail.reason_code === 'LAST_ADMIN');
      assert.strictEqual(refusals.length, 1, 'the refusal was not audited');
      // THE POINT OF THIS ARM: with two admins and one owner the provisioner
      // count is 3 and the owner count is 1. Logging 3 beside a LAST_ADMIN
      // refusal would be a number that contradicts the entry it explains.
      assert.strictEqual(refusals[0].detail.active_admins, 1,
        'the audit logged the provisioner count, not the owner count that '
        + 'actually triggered the refusal');
    });

  section('THE CONTROLS -- a guard that refuses everything is a worse bug');

  await test('with a SECOND active owner, the same call is ALLOWED', async () => {
    const r = await setActive([OWNER, OWNER2, ADMIN], 'admin', 'E1');
    assert.strictEqual(r.status, 200, 'status was ' + r.status + ' ' + r.code);
    assert.strictEqual(r.patched, true, 'allowed but nothing was written');
  });

  await test('an OWNER deactivating the last ADMIN is ALLOWED -- the guard is '
    + 'about owners, not provisioners', async () => {
      const r = await setActive([OWNER, ADMIN], 'owner', 'E2');
      assert.strictEqual(r.status, 200, 'status was ' + r.status + ' ' + r.code);
      assert.strictEqual(r.patched, true, 'allowed but nothing was written');
    });

  await test('an ADMIN deactivating another ADMIN is ALLOWED', async () => {
    const r = await setActive([OWNER, ADMIN, ADMIN2], 'admin', 'E3');
    assert.strictEqual(r.status, 200, 'status was ' + r.status + ' ' + r.code);
    assert.strictEqual(r.patched, true, 'allowed but nothing was written');
  });

  section('THE GUARD SET IS NARROWER THAN THE PROVISIONING SET, ON PURPOSE');

  await test('GUARD_ROLES is owner-only while PROVISIONING_ROLES keeps both',
    () => {
      const fs = require('fs');
      const src = fs.readFileSync(path.join(ROOT, 'api/sd-auth.js'), 'utf8');
      assert.match(src, /const PROVISIONING_ROLES = \['owner', 'admin'\];/,
        'the provisioning set changed -- who may provision is a separate '
        + 'decision from who must not reach zero, and narrowing THIS one would '
        + 'lock admins out of provisioning entirely');
      assert.match(src, /const SOLE_ROLE = 'owner';/);
      assert.match(src, /const GUARD_ROLES = \[SOLE_ROLE\];/);
    });

  await test('the "unreachable by construction" claim is GONE from the file',
    () => {
      const fs = require('fs');
      const src = fs.readFileSync(path.join(ROOT, 'api/sd-auth.js'), 'utf8');
      // ── THIS ARM FAILED ON ITS FIRST RUN, FOR THE RIGHT REASON ──────────
      // It was a bare search for the old phrase, and the corrected comment
      // QUOTES that phrase in order to record what was wrong -- so the arm
      // matched the correction and reported the defect as present. The lesson
      // is the string-anchor one: an anchor that cannot tell a claim from a
      // quotation of that claim is not reading its subject.
      //
      // So the assertion is about CONTEXT, not presence. The phrase may appear
      // exactly once, and it must sit inside the passage that introduces it as
      // history. A second occurrence -- or one outside that passage -- means
      // somebody is asserting it again.
      // NORMALISED FIRST, because the phrase is wrapped across two comment
      // lines in the real file and a raw search finds ZERO -- which this arm
      // reported as "the claim is gone" on its second run. A checker that is
      // defeated by line wrapping is not reading prose, it is reading layout.
      const flat = src.replace(/\n\s*\/\/ ?/g, ' ').replace(/\s+/g, ' ');
      const PHRASE = 'unreachable by construction';
      const hits = flat.split(PHRASE).length - 1;
      assert.strictEqual(hits, 1, 'expected the old claim to survive exactly '
        + 'once, as a quotation inside its own correction; found ' + hits);
      const quoteAt = flat.indexOf('It read: "Quarantined guard');
      assert.ok(quoteAt > 0,
        'the passage that records WHY this comment was wrong is gone. The '
        + 'sentence mattered more than the code: the guard never fired, and '
        + 'non-firing was written down as proof it was not needed.');
      const phraseAt = flat.indexOf(PHRASE);
      assert.ok(phraseAt > quoteAt && phraseAt - quoteAt < 400,
        'the phrase is no longer inside the quotation that marks it as the '
        + 'OLD text -- it reads as a live claim again');
    });

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  if (fail) { console.log('FAILURES ABOVE'); process.exit(1); }
})();
