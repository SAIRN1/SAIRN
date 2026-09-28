// api/legal-deadlines-auth.test.js
//
// Run:  node api/legal-deadlines-auth.test.js
//
// REQUIREMENT: authoring a DEADLINE RULE is a legal-authority act and needs a
//   signed-in person with authority. A licence key alone must not be able to
//   write or overwrite one.
//
// ── THE DEFECT ─────────────────────────────────────────────────────────────
// `add_rule` and `add_holidays` upserted into `law_deadline_rules` and
// `law_holidays` with NO 401 and NO role check. The caller WAS resolved -- at
// :692, `verifySessionToken(...)` -- and then used for exactly one thing: to
// stamp `verified_by`. The code says so in its own comment: *"A bearer-key load
// stamps null here and a session load stamps an employee id."*
//
// So a holder of a valid SAIRNlaw licence key, with no employee session at all,
// could author a rule -- or OVERWRITE one, because both writes are upserts keyed
// on `rule_id` / `jurisdiction:year`. The stored row then drives every computed
// answer date for that jurisdiction, for every user on that licence.
//
// A WRONG DEADLINE HERE IS MALPRACTICE EXPOSURE, which is the engine's own
// header's words about itself. The blast radius of an unauthenticated write is
// not one request, it is every future computation.
//
// ── WHY THIS WAS NOT OBVIOUS, AND WHY THE TEST-FIRST ORDER MATTERS ─────────
// The gap is invisible from the code that HAS the check: `audit_read`, the AI
// conflict-of-check actions and the credential paths all call
// `AI_COC_REVIEW_ROLES[caller.role]` or `PROVISIONING_ROLES`. Reading this file
// top to bottom you see gate after gate and then two branches that resolve a
// caller and never test it. Arms A1-A4 below were written and RUN RED before the
// fix, so they are known to distinguish the two states rather than to describe
// the one that exists.
//
// ── WHAT THE ROLE SET IS, AND WHY IT IS A NEW NAME ────────────────────────
// SAIRNlaw has three roles -- owner, attorney, paralegal -- and api/law-auth.js
// says plainly that *"this app has no MANAGEMENT_ROLES concept, and inventing one
// to serve a credential panel would add an authorisation tier as a side
// effect."* That warning is about a tier added AS A SIDE EFFECT. Here the tier
// IS the subject, so it gets its own purpose-named export rather than borrowing
// `AI_COC_REVIEW_ROLES`, which happens to have the same membership today and is
// named for a different job -- and two decisions sharing one constant is how the
// next person changes both by changing one.
//
// OWNER AND ATTORNEY, NOT PARALEGAL, and that is the substantive call: authoring
// a deadline rule means asserting what a rule of procedure says and citing the
// authority for it. That is the attorney's professional act. A paralegal
// computing a date from an existing rule is unaffected -- `compute`,
// `rules_status` and `rules_fingerprint` are untouched.

'use strict';
const assert = require('assert');
const path = require('path');

const LIC = 'law-test-hash';
const HANDLER = path.join(__dirname, 'legal-deadlines.js');

let pass = 0, fail = 0;
function test(name, fn) {
  return (async () => {
    try { await fn(); pass++; console.log('  ok   ' + name); }
    catch (e) { fail++; console.log('  FAIL ' + name + '\n       ' + e.message); }
  })();
}
function section(t) { console.log('\n' + t); }

// signSessionToken REFUSES without a secret, and a suite that lets that throw
// reports every role arm as a failure of the GATE. Set before the import.
process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET
  || ['legal', 'deadlines', 'auth', 'test', 'secret'].join('-');
const { signSessionToken } = require(path.join(__dirname, '_lib', 'auth'));

function mockRes() {
  const res = { statusCode: null, body: null };
  res.status = (c) => { res.statusCode = c; return res; };
  res.json = (b) => { res.body = b; return res; };
  res.setHeader = () => {};
  return res;
}

// A session token for a given role, or none at all -- which is the case the
// whole file is about.
function headersFor(role) {
  const h = { authorization: 'Bearer LAW-TEST-KEY' };
  if (role) {
    h['x-sd-auth'] = signSessionToken({ app: 'sairnlaw', employee_id: 'E-1',
                                        role: role, license_hash: LIC });
  }
  return h;
}

// THE FIXTURES ARE SHAPED FROM A REAL SEEDED ROW, not invented. The first
// version of this file guessed `period` / `computation_standard` / a bare date
// string, and every A-arm answered 400 INVALID_RULE -- so the request never
// reached the write and the arms reported "refused" for the wrong reason. A
// probe that is refused by the validator cannot tell you anything about the
// GATE, and it looks identical to one that was.
const GOOD_RULE = {
  rule_id: 'zz-probe-rule',
  jurisdiction: 'zz-probe',
  domain: 'civil-litigation',
  label: 'Probe rule -- never seeded, never loaded, never computed from',
  trigger_event: 'service_of_summons_and_complaint',
  count: { value: 21, unit: 'calendar_days', direction: 'forward' },
  computation: 'frcp_6a',
  effective_from: '2026-01-01',
  authority: { citation: 'Probe R. Civ. P. 1', url: 'https://example.invalid/probe' }
};
const GOOD_CALENDAR = {
  jurisdiction: 'zz-probe',
  year: 2026,
  // `kind` is load-bearing per FRCP 6(a)(6) and the validator says so.
  dates: [{ date: '2026-01-01', name: 'Probe Day', kind: 'federal' }],
  authority: { citation: 'Probe holidays', url: 'https://example.invalid/probe' }
};

// THE WRITE IS OBSERVED, not assumed. `wrote` is set by METHOD and never by call
// order -- the harness defect this session recorded twice (a probe that counted
// "the first fetch is the auth read" broke the day a second read was added ahead
// of the write).
function load(opts) {
  opts = opts || {};
  const out = { wrote: false, writes: [] };
  const licPath = path.join(__dirname, '_lib', 'license');
  delete require.cache[require.resolve(licPath)];
  require.cache[require.resolve(licPath)] = {
    exports: {
      validateLicenseKey: async () => ({ valid: true, active: true, license_hash: LIC,
                                         trial_ends_at: null, stripe_subscription_id: null,
                                         app_id: 'sairnlaw' })
    }
  };
  process.env.SUPABASE_URL = 'https://stub.invalid';
  process.env.SUPABASE_SERVICE_ROLE_KEY = 'stub-key';
  global.fetch = async (url, init) => {
    const method = (init && init.method) || 'GET';
    if (method === 'GET') {
      return { ok: true, status: 200,
               json: async () => [{ active: true, status: 'active' }] };
    }
    // ── THE AUDIT LOG IS NOT THE WRITE THIS FILE IS ABOUT ─────────────────
    // INSTRUMENT, NOT CODE: the first version counted every non-GET as "wrote",
    // and arm B1 then failed against a CORRECT refusal -- because refusing a
    // paralegal correctly AUDITS the refusal, which is a POST. A refusal that
    // left no trace would be the worse bug. `wrote` means "a deadline rule or a
    // holiday calendar was stored", so it is scoped to those two tables by name.
    out.writes.push({ url: String(url), method: method });
    if (/law_deadline_rules|law_holidays/.test(String(url))) out.wrote = true;
    return { ok: true, status: 200, json: async () => [{}] };
  };
  delete require.cache[require.resolve(HANDLER)];
  return { handler: require(HANDLER), out: out };
}

async function call(action, payload, role) {
  const { handler, out } = load();
  const res = mockRes();
  const body = Object.assign({ action: action }, payload);
  await handler({ method: 'POST', headers: headersFor(role), body: body }, res);
  return { code: res.statusCode, body: res.body, wrote: out.wrote, writes: out.writes };
}

async function main() {
  console.log('SAIRNlaw deadline-rule authoring -- a licence key is not authority\n');

  section('A. NO SESSION AT ALL -- the defect');
  await test('A1. add_rule with a licence key and NO session is REFUSED', async () => {
    const r = await call('add_rule', { rule: GOOD_RULE }, null);
    assert.ok(r.code === 401 || r.code === 403,
      'answered ' + r.code + ': ' + JSON.stringify(r.body).slice(0, 200));
  });
  await test('A2. ...and NOTHING is written -- the refusal must come before the '
    + 'upsert, because both writes are upserts and an overwrite is not undoable',
    async () => {
      const r = await call('add_rule', { rule: GOOD_RULE }, null);
      assert.strictEqual(r.wrote, false,
        'a rule was written with no session: ' + JSON.stringify(r.writes));
    });
  await test('A3. add_holidays with no session is REFUSED', async () => {
    const r = await call('add_holidays', { calendar: GOOD_CALENDAR }, null);
    assert.ok(r.code === 401 || r.code === 403,
      'answered ' + r.code + ': ' + JSON.stringify(r.body).slice(0, 200));
  });
  await test('A4. ...and writes nothing either', async () => {
    const r = await call('add_holidays', { calendar: GOOD_CALENDAR }, null);
    assert.strictEqual(r.wrote, false, JSON.stringify(r.writes));
  });

  section('B. THE ROLE TIER -- authoring a rule is the attorney\'s act');
  await test('B1. a PARALEGAL is refused 403, not 401 -- the session is real and '
    + 'the authority is not', async () => {
      const r = await call('add_rule', { rule: GOOD_RULE }, 'paralegal');
      assert.strictEqual(r.code, 403, JSON.stringify(r.body).slice(0, 200));
      assert.strictEqual(r.wrote, false, JSON.stringify(r.writes));
    });
  await test('B2. ...and the refusal says WHY, so a paralegal is not left '
    + 'guessing which field was wrong', async () => {
      const r = await call('add_rule', { rule: GOOD_RULE }, 'paralegal');
      const msg = JSON.stringify(r.body);
      assert.ok(/authority|attorney|owner/i.test(msg), msg.slice(0, 250));
    });
  await test('B3. an OWNER may author a rule', async () => {
    const r = await call('add_rule', { rule: GOOD_RULE }, 'owner');
    assert.strictEqual(r.code, 200, JSON.stringify(r.body).slice(0, 250));
    assert.strictEqual(r.wrote, true, 'the owner path stopped writing');
  });
  await test('B4. an ATTORNEY may author a rule', async () => {
    const r = await call('add_rule', { rule: GOOD_RULE }, 'attorney');
    assert.strictEqual(r.code, 200, JSON.stringify(r.body).slice(0, 250));
    assert.strictEqual(r.wrote, true);
  });
  await test('B5. and the same tier applies to add_holidays -- a holiday calendar '
    + 'moves every date in the jurisdiction, so it is not the softer case',
    async () => {
      const paralegal = await call('add_holidays', { calendar: GOOD_CALENDAR }, 'paralegal');
      assert.strictEqual(paralegal.code, 403, JSON.stringify(paralegal.body).slice(0, 200));
      const owner = await call('add_holidays', { calendar: GOOD_CALENDAR }, 'owner');
      assert.strictEqual(owner.code, 200, JSON.stringify(owner.body).slice(0, 250));
    });

  section('C. THE READ SIDE IS UNTOUCHED -- this is a gate, not a lockout');
  await test('C1. compute still works with NO session, because computing a date '
    + 'from a rule somebody else authored is not an authoring act', async () => {
      const r = await call('compute', { jurisdiction: 'zz-probe', domain: 'civil-litigation',
                                        trigger_event: 'service_of_summons',
                                        trigger_date: '2026-03-02' }, null);
      assert.notStrictEqual(r.code, 401,
        'compute was gated as a side effect: ' + JSON.stringify(r.body).slice(0, 200));
      assert.notStrictEqual(r.code, 403, JSON.stringify(r.body).slice(0, 200));
    });
  await test('C2. rules_status still works with no session', async () => {
    const r = await call('rules_status', {}, null);
    assert.ok(r.code !== 401 && r.code !== 403, JSON.stringify(r.body).slice(0, 200));
  });

  section('D. KNOWN-BAD CONTROL -- the arms must be shown to fail');
  await test('D1. CONTROL: asserting an UNAUTHENTICATED add_rule SUCCEEDS fails, '
    + 'so section A distinguishes the gate from its absence', async () => {
      const r = await call('add_rule', { rule: GOOD_RULE }, null);
      let caught = 0;
      try { assert.strictEqual(r.code, 200); } catch (e) { caught++; }
      assert.strictEqual(caught, 1,
        'an unauthenticated add_rule answered 200 -- the gate is gone');
    });
  await test('D2. CONTROL: the harness really does observe writes -- the OWNER '
    + 'path sets `wrote`, so `wrote === false` above is a fact and not a '
    + 'harness that never records anything', async () => {
      const r = await call('add_rule', { rule: GOOD_RULE }, 'owner');
      assert.strictEqual(r.wrote, true,
        'the harness never observes a write, so every A-arm is vacuous');
    });

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
}

main();
