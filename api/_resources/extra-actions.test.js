// api/_resources/extra-actions.test.js
// Plain node:assert tests -- no test framework, matching api/'s existing
// zero-npm-dependency convention (see api/_lib/auth.test.js).
// Run: node api/_resources/extra-actions.test.js
//
// Covers the 2026-08-24 verb-gate change: per-resource verbs beyond the
// universal read/write moved out of three hand-written conditions in
// api/sd-data.js and into each app's own registry file, merged here into
// EXTRA_ACTIONS.
//
// The gate itself is exercised through the REAL exported api/sd-data.js
// handler with a mock req/res, not a reimplementation of its logic -- a test
// that re-derives the condition it is checking would pass against a broken
// gate. No env vars are set, so anything that passes the gate lands on the
// SUPABASE_URL check and returns 500; that 500 IS the positive signal, and a
// 400 is the negative one. Neither path reaches Supabase or any real data.

const assert = require('assert');
const reg = require('./index');
const handler = require('../sd-data');

let passed = 0;
let failed = 0;
function test(name, fn) {
  try {
    fn();
    passed++;
    console.log('  ok - ' + name);
  } catch (err) {
    failed++;
    console.error('  FAIL - ' + name);
    console.error('    ' + err.message);
  }
}
async function atest(name, fn) {
  try {
    await fn();
    passed++;
    console.log('  ok - ' + name);
  } catch (err) {
    failed++;
    console.error('  FAIL - ' + name);
    console.error('    ' + err.message);
  }
}

// Drive the real handler and report only what the gate decides.
async function gate(action, resource) {
  const out = { code: null, body: null };
  const res = {
    status(c) { out.code = c; return res; },
    json(b) { out.body = b; return res; }
  };
  await handler({
    method: 'POST',
    headers: { authorization: 'Bearer extra-actions-test-not-a-real-key' },
    body: { action, resource, payload: {} }
  }, res);
  return out;
}
const PASSED_GATE = 500;   // reached the env check => the gate allowed it
const REJECTED = 400;      // the gate refused the verb

(async () => {
  console.log('EXTRA_ACTIONS merge:');

  test('every extraActions key is a registered resource', () => {
    for (const name of Object.keys(reg.EXTRA_ACTIONS)) {
      assert.ok(reg.RESOURCES[name], name + ' has verbs but is not registered');
    }
  });

  test('every sc_ resource grants exactly delete', () => {
    const sc = require('./sairncode').resources;
    assert.strictEqual(sc.length, 28);
    for (const name of sc) {
      assert.deepStrictEqual(reg.EXTRA_ACTIONS[name], ['delete'], name);
    }
  });

  test('each compute-only verb reaches exactly its declared owners', () => {
    assert.deepStrictEqual(reg.EXTRA_ACTIONS.alf_payer_rules, ['route']);
    assert.deepStrictEqual(reg.EXTRA_ACTIONS.alf_compliance_rules, ['evaluate']);
    assert.deepStrictEqual(reg.EXTRA_ACTIONS.alf_billing, ['derive_charges']);
    assert.deepStrictEqual(reg.EXTRA_ACTIONS.dnt_credentials, ['evaluate']);
    assert.deepStrictEqual(reg.EXTRA_ACTIONS.rf_certifications, ['evaluate']);
    const grants = (verb) => reg.RESOURCE_NAMES.filter(
      (n) => (reg.EXTRA_ACTIONS[n] || []).indexOf(verb) !== -1
    );
    // Enumerated, not counted: a new grant of one of these verbs must fail
    // here and be looked at, rather than passing because the total still
    // "looks about right". 'evaluate' is legitimately held by three resources
    // as of 2026-08-24 (SAIRNcare compliance, SAIRNdental credentials,
    // SAIRNroofing certifications) -- all compute-only, all read-only, each
    // declared by its own app. Growth here is expected and fine; an
    // UNDECLARED grant is what this line exists to catch.
    assert.deepStrictEqual(grants('route'), ['alf_payer_rules']);
    assert.deepStrictEqual(grants('evaluate').sort(),
      ['alf_compliance_rules', 'dnt_credentials', 'rf_certifications']);
    assert.deepStrictEqual(grants('derive_charges'), ['alf_billing']);
    // 'reconcile' (SAIRNroofing 3c) is owned by rf_claims alone.
    assert.deepStrictEqual(reg.EXTRA_ACTIONS.rf_claims, ['reconcile']);
    assert.deepStrictEqual(grants('reconcile'), ['rf_claims']);
  });

  test('no resource outside the sc_ family grants delete', () => {
    const sc = new Set(require('./sairncode').resources);
    for (const name of reg.RESOURCE_NAMES) {
      const verbs = reg.EXTRA_ACTIONS[name] || [];
      if (verbs.indexOf('delete') !== -1) assert.ok(sc.has(name), name + ' grants delete');
    }
  });

  test('SC_RESOURCES is derived, not a second copy', () => {
    const src = require('fs').readFileSync(require('path').join(__dirname, '..', 'sd-data.js'), 'utf8');
    const decl = src.match(/const SC_RESOURCES = ([^\n;]*)/);
    assert.ok(decl, 'SC_RESOURCES declaration not found in api/sd-data.js');
    assert.ok(
      /require\(['"]\.\/_resources\/sairncode['"]\)/.test(decl[1]),
      'SC_RESOURCES must be derived from the registry, found: ' + decl[1]
    );
  });

  test('a module cannot grant verbs to another app\'s resource', () => {
    const { REGISTRY_MODULES } = reg;
    const bad = REGISTRY_MODULES.slice();
    bad.push({ app: 'rogue', resources: ['rogue_thing'], extraActions: { profile: ['delete'] } });
    // Re-run the same assertion index.js runs at load, on a deliberately bad module.
    assert.throws(() => {
      for (const mod of bad) {
        const own = new Set(mod.resources);
        for (const name of Object.keys(mod.extraActions || {})) {
          if (!own.has(name)) throw new Error('not owned: ' + name);
        }
      }
    }, /not owned: profile/);
  });

  console.log('\nGate — POSITIVE (verb must be allowed):');
  await atest('read is allowed on a plain resource', async () => {
    assert.strictEqual((await gate('read', 'profile')).code, PASSED_GATE);
  });
  await atest('write is allowed on a plain resource', async () => {
    assert.strictEqual((await gate('write', 'profile')).code, PASSED_GATE);
  });
  await atest('delete is allowed on sc_denial', async () => {
    assert.strictEqual((await gate('delete', 'sc_denial')).code, PASSED_GATE);
  });
  await atest('delete is allowed on the newest sc_ resource (sc_dme)', async () => {
    assert.strictEqual((await gate('delete', 'sc_dme')).code, PASSED_GATE);
  });
  await atest('route is allowed on alf_payer_rules', async () => {
    assert.strictEqual((await gate('route', 'alf_payer_rules')).code, PASSED_GATE);
  });
  await atest('evaluate is allowed on alf_compliance_rules', async () => {
    assert.strictEqual((await gate('evaluate', 'alf_compliance_rules')).code, PASSED_GATE);
  });
  await atest('derive_charges is allowed on alf_billing', async () => {
    assert.strictEqual((await gate('derive_charges', 'alf_billing')).code, PASSED_GATE);
  });

  console.log('\nGate — NEGATIVE (verb must be refused):');
  await atest('delete is refused on a non-sc_ resource', async () => {
    const r = await gate('delete', 'profile');
    assert.strictEqual(r.code, REJECTED);
    assert.strictEqual(r.body.error.message, "action must be 'read' or 'write'");
  });
  await atest('route is refused on a resource that did not grant it', async () => {
    assert.strictEqual((await gate('route', 'profile')).code, REJECTED);
  });
  await atest('route is refused on the OTHER two carve-out resources', async () => {
    assert.strictEqual((await gate('route', 'alf_billing')).code, REJECTED);
    assert.strictEqual((await gate('route', 'alf_compliance_rules')).code, REJECTED);
  });
  await atest('evaluate is refused on alf_payer_rules', async () => {
    assert.strictEqual((await gate('evaluate', 'alf_payer_rules')).code, REJECTED);
  });
  await atest('derive_charges is refused on alf_payer_rules', async () => {
    assert.strictEqual((await gate('derive_charges', 'alf_payer_rules')).code, REJECTED);
  });
  await atest('an sc_ resource does not inherit route/evaluate/derive_charges', async () => {
    assert.strictEqual((await gate('route', 'sc_denial')).code, REJECTED);
    assert.strictEqual((await gate('evaluate', 'sc_denial')).code, REJECTED);
    assert.strictEqual((await gate('derive_charges', 'sc_denial')).code, REJECTED);
  });
  await atest('an unknown verb is refused everywhere', async () => {
    assert.strictEqual((await gate('bogus_verb', 'profile')).code, REJECTED);
    assert.strictEqual((await gate('bogus_verb', 'sc_denial')).code, REJECTED);
    assert.strictEqual((await gate('bogus_verb', 'alf_payer_rules')).code, REJECTED);
  });
  await atest('the sc_ error message still names delete, and only there', async () => {
    assert.strictEqual(
      (await gate('bogus_verb', 'sc_denial')).body.error.message,
      "action must be 'read' or 'write' or 'delete'"
    );
    assert.strictEqual(
      (await gate('bogus_verb', 'alf_payer_rules')).body.error.message,
      "action must be 'read' or 'write'"
    );
  });
  await atest('an unregistered resource is refused with the generated list', async () => {
    const r = await gate('read', '__no_such_resource__');
    assert.strictEqual(r.code, REJECTED);
    assert.ok(/^resource must be one of: /.test(r.body.error.message));
    assert.strictEqual(
      r.body.error.message,
      'resource must be one of: ' + reg.RESOURCE_LIST_TEXT
    );
  });
  await atest('verb gate runs BEFORE the resource gate (pre-existing order, unchanged)', async () => {
    // An unknown resource asked for an extra verb is refused by the ACTION
    // gate, not the resource gate -- the action check sits above it in
    // api/sd-data.js and always has. Asserted so the ordering is a documented
    // fact rather than a surprise to whoever changes either gate next; it is
    // also why an unregistered resource can never be granted a verb by
    // accident.
    const r = await gate('delete', '__no_such_resource__');
    assert.strictEqual(r.code, REJECTED);
    assert.strictEqual(r.body.error.message, "action must be 'read' or 'write'");
  });

  console.log('\n' + passed + ' passed, ' + failed + ' failed');
  if (failed > 0) process.exit(1);
})();
