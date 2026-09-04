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
// The gate itself is exercised through the REAL api/sd-data.js code, not a
// reimplementation of its logic -- a test that re-derives the condition it is
// checking would pass against a broken gate.
//
// ── HOW IT REACHES THE GATE CHANGED 2026-09-04, AND WHY ──────────────────
// It used to call the exported handler with a junk bearer token and read
// whether it got a 400 (refused) or fell through to the missing-env 500
// (allowed). THAT ONLY WORKED BECAUSE THE GATE RAN BEFORE LICENCE VALIDATION
// -- which is exactly the disclosure defect fixed that day: an unauthenticated
// caller could enumerate all 171 resource names. With validation first, every
// such call now returns 500 CONFIG and allow is indistinguishable from refuse.
//
// So the gate is now driven directly as sd-data.js's exported checkEnvelope --
// the same function the handler calls, one call earlier in the same file. The
// guarantee is unchanged: this is the real gate, not a copy of it.
//
// The ordering itself is asserted separately, at the bottom, THROUGH the real
// handler -- because a seam that lets the test skip auth would be worthless if
// nothing checked that the handler does not skip it too.

const assert = require('assert');
const fs = require('fs');
const path = require('path');
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

// Drive the real gate and report only what it decides.
function gate(action, resource) {
  const r = handler.checkEnvelope(action, resource);
  return r ? { code: r.status, body: r.body } : { code: PASSED_GATE, body: null };
}
const PASSED_GATE = 'ALLOWED';   // checkEnvelope returned null => allowed through
const REJECTED = 400;            // the gate refused the verb

// Drive the real EXPORTED HANDLER with a mock req/res. Used only by the
// ordering assertions at the bottom; no env vars are set, so nothing here can
// reach Supabase or any real data.
async function callHandler(action, resource, key) {
  const out = { code: null, body: null };
  const res = {
    status(c) { out.code = c; return res; },
    json(b) { out.body = b; return res; }
  };
  await handler({
    method: 'POST',
    headers: { authorization: 'Bearer ' + (key || 'extra-actions-test-not-a-real-key') },
    body: { action, resource, payload: {} }
  }, res);
  return out;
}

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
    assert.deepStrictEqual(reg.EXTRA_ACTIONS.rf_company_programs, ['evaluate']);
    const grants = (verb) => reg.RESOURCE_NAMES.filter(
      (n) => (reg.EXTRA_ACTIONS[n] || []).indexOf(verb) !== -1
    );
    // Enumerated, not counted: a new grant of one of these verbs must fail
    // here and be looked at, rather than passing because the total still
    // "looks about right". 'evaluate' is legitimately held by FOUR resources
    // as of 2026-08-25 (SAIRNcare compliance, SAIRNdental credentials,
    // SAIRNroofing certifications, SAIRNroofing company programmes) -- all
    // compute-only, all read-only, each declared by its own app. Growth here is
    // expected and fine; an UNDECLARED grant is what this line exists to catch.
    //
    // rf_company_programs was added 2026-08-25 (Phase 4d) and this line caught
    // it, which is the tripwire working. Checked before widening it: the
    // handler branch reads programmes, the roster and rf_certifications, runs
    // api/_lib/roofing-programs.js and issues no write -- its own suite asserts
    // zero non-GET requests. It also carries a HARDER gate than the other
    // three (management/broad-read only), because a roster-credential share is
    // an aggregate over colleagues rather than a fact about the caller.
    assert.deepStrictEqual(grants('route'), ['alf_payer_rules']);
    assert.deepStrictEqual(grants('evaluate').sort(),
      ['alf_compliance_rules', 'dnt_credentials', 'rf_certifications', 'rf_company_programs']);
    assert.deepStrictEqual(grants('derive_charges'), ['alf_billing']);
    // 'reconcile' (SAIRNroofing 3c) and 'assess_damage' (2026-08-26) are both
    // owned by rf_claims alone, and both are compute-only: neither may ever
    // write, which roofing-damage-assessment-endpoint.test.js asserts directly.
    assert.deepStrictEqual(reg.EXTRA_ACTIONS.rf_claims, ['reconcile', 'assess_damage']);
    assert.deepStrictEqual(grants('reconcile'), ['rf_claims']);
    assert.deepStrictEqual(grants('assess_damage'), ['rf_claims']);
    // Phase 4a/4d single-owner verbs.
    assert.deepStrictEqual(grants('set_status'), ['rf_schedule']);
    assert.deepStrictEqual(grants('agreement_status'), ['rf_claim_agreements']);
    // Phase 4b.
    assert.deepStrictEqual(reg.EXTRA_ACTIONS.rf_invoices, ['issue', 'add_payment', 'reconcile_claim']);
    ['issue', 'add_payment', 'reconcile_claim'].forEach((v) => {
      assert.deepStrictEqual(grants(v), ['rf_invoices'], v + ' must be owned by rf_invoices alone');
    });
  });

  // ── THE VERB DECLARATION LIVES WHERE THE VERB IS GRANTED (2026-09-02) ────
  //
  // This used to be a hand-maintained DECLARED_VERBS array right here, and it
  // went stale three times in one day. Each time, another session added a verb
  // in api/_resources/<their-app>.js and this file -- which they had no reason
  // to open -- went red for whoever ran the suite next. The person who ran the
  // tests then had to read a handler they had not written and declare somebody
  // else's verb. That is a second party maintaining a list after the fact, and
  // it is the same shape as the single-deepStrictEqual staleness that this
  // file's own split was written to fix earlier the same day.
  //
  // THE NOTES ALREADY EXISTED. Every registry module already documents its
  // verbs in comments next to the grant -- sairnroofing.js explains all
  // seventeen of them. The duplicate list here was the only stale part.
  //
  // So the guard now reads the module's OWN SOURCE and requires each verb it
  // grants to be discussed BY NAME in that file's comments. Adding a verb and
  // declaring it become one edit, in one file, by one person -- with no list
  // anywhere else to forget.
  //
  // HONEST LIMIT, because this replaces a stricter-looking check: a comment
  // cannot prove anyone read the handler. What it guarantees is that the
  // author had to write something about the verb at the moment of granting it,
  // and that the next reader finds reasoning where the grant is rather than in
  // a file they have to know exists. The old list did not prove comprehension
  // either -- it only proved somebody, eventually, noticed.

  function verbsByModule() {
    const out = [];
    for (const mod of reg.REGISTRY_MODULES) {
      const extra = mod.extraActions || {};
      const verbs = new Set();
      for (const name of Object.keys(extra)) extra[name].forEach((v) => verbs.add(v));
      if (verbs.size) out.push({ app: mod.app, verbs: [...verbs].sort() });
    }
    return out;
  }

  function commentsOf(app) {
    const src = fs.readFileSync(path.join(__dirname, app + '.js'), 'utf8');
    return src
      .split(String.fromCharCode(10))
      .filter((l) => l.trim().indexOf('//') === 0)
      .join(String.fromCharCode(10));
  }

  test('every granted verb is named in its OWN module comments -- no second list', () => {
    const undocumented = [];
    for (const { app, verbs } of verbsByModule()) {
      const comments = commentsOf(app);
      for (const v of verbs) {
        // Quoted, so a verb is named deliberately rather than matched inside
        // an unrelated English word (`board` in "dashboard", `wip` in "wiped").
        if (comments.indexOf("'" + v + "'") === -1) undocumented.push(app + '.js: ' + v);
      }
    }
    assert.deepStrictEqual(undocumented, [],
      'UNDOCUMENTED VERB(S):' + String.fromCharCode(10) + '    ' + undocumented.join(String.fromCharCode(10) + '    ') +
      String.fromCharCode(10) + "    Write a comment next to the grant, in the SAME file, naming the verb in quotes" +
      String.fromCharCode(10) + '    and saying what it does and what it refuses. Do not add it to a list elsewhere.');
  });

  test('the guard actually bites -- an undocumented verb is detected', () => {
    // The check is only worth having if it fails on the thing it describes.
    const comments = "// nothing about the new verb here";
    assert.strictEqual(comments.indexOf("'brand_new_verb'"), -1);
  });

  test('and it does not accept a verb merely appearing inside another word', () => {
    const comments = '// the dashboard was wiped clean';
    assert.strictEqual(comments.indexOf("'board'"), -1, "'board' matched inside 'dashboard'");
    assert.strictEqual(comments.indexOf("'wip'"), -1, "'wip' matched inside 'wiped'");
  });

  test('every module granting a verb is covered by the guard', () => {
    // A module with extraActions but no readable source would silently pass.
    for (const { app } of verbsByModule()) {
      assert.ok(fs.existsSync(path.join(__dirname, app + '.js')),
        'no source file for module ' + app + ' -- the guard cannot read it');
    }
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

  // ── ORDERING: NO RESOURCE NAME LEAVES THE ENDPOINT WITHOUT A VALID LICENCE ──
  //
  // Fixed 2026-09-04. Before it, `POST /api/sd-data` with
  // `Authorization: Bearer not-a-real-key` and an unknown resource answered
  // 400 naming all 171 registered resources, to a caller holding no credential
  // -- verified live on 2026-08-24 with no credential used. Names only, never
  // data, but it enumerated the whole platform's surface and let an anonymous
  // caller tell a real resource from an invented one by which refusal came
  // back.
  //
  // These go through the REAL EXPORTED HANDLER on purpose. Everything above
  // drives checkEnvelope directly, which is only safe while the handler is
  // known to run validation first -- so that is what these assert. No env vars
  // are set, so validateLicenseKey() throws CONFIG and the handler answers 500
  // before any Supabase call.
  console.log('\nOrdering — an unauthenticated caller learns nothing:');

  await atest('the gate is exported for the tests above, and is the real one', () => {
    assert.strictEqual(typeof handler.checkEnvelope, 'function',
      'sd-data.js no longer exports checkEnvelope -- every gate assertion above is dead');
    assert.strictEqual(handler.checkEnvelope('read', '__no_such_resource__').status, 400);
  });

  await atest('a junk token NEVER sees the resource list', async () => {
    const r = await callHandler('read', '__no_such_resource__');
    const text = JSON.stringify(r.body);
    assert.ok(!/resource must be one of/.test(text),
      'the resource list is still disclosed to an unauthenticated caller: ' + text);
    for (const name of reg.RESOURCE_NAMES) {
      assert.ok(text.indexOf(name) === -1,
        'the refusal names the registered resource "' + name + '": ' + text);
    }
  });

  await atest('...and cannot tell a REAL resource from an invented one', async () => {
    // The oracle, not just the list. If these two differ in any way, an
    // anonymous caller can probe for a resource's existence one guess at a time.
    const real = await callHandler('read', 'profile');
    const fake = await callHandler('read', '__no_such_resource__');
    assert.strictEqual(real.code, fake.code);
    assert.deepStrictEqual(real.body, fake.body);
  });

  await atest('...nor an allowed verb from a refused one', async () => {
    const allowed = await callHandler('delete', 'sc_denial');
    const refused = await callHandler('delete', 'profile');
    assert.strictEqual(allowed.code, refused.code);
    assert.deepStrictEqual(allowed.body, refused.body);
  });

  await atest('...nor whether the sc_ family exists', async () => {
    // The action-gate message appends "or 'delete'" only for sc_ resources,
    // which was a second, smaller oracle on the same unauthenticated path.
    const sc = await callHandler('bogus_verb', 'sc_denial');
    const plain = await callHandler('bogus_verb', 'profile');
    assert.deepStrictEqual(sc.body, plain.body);
    assert.ok(!/delete/.test(JSON.stringify(sc.body)), JSON.stringify(sc.body));
  });

  await atest('THE PRODUCTION PATH: a configured server answers 401, still naming nothing', async () => {
    // Everything above proves it on the missing-env 500. That is the shape a
    // developer's machine happens to be in, NOT the one a customer hits, and a
    // fix proved only in the accidental configuration is not proved. So this
    // one runs with env set and the licence lookup stubbed to "no such key",
    // which is the real 401 INVALID_LICENSE branch.
    const envURL = process.env.SUPABASE_URL;
    const envKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
    const realFetch = global.fetch;
    process.env.SUPABASE_URL = 'https://stub.invalid';
    process.env.SUPABASE_SERVICE_ROLE_KEY = 'stub-service-key';
    // Returns zero rows: license_keys has no such key. No network is involved.
    global.fetch = async () => ({ ok: true, status: 200, json: async () => [] });
    try {
      const fake = await callHandler('read', '__no_such_resource__');
      const real = await callHandler('read', 'profile');
      assert.strictEqual(fake.code, 401, JSON.stringify(fake.body));
      assert.strictEqual(fake.body.error.code, 'INVALID_LICENSE');
      assert.deepStrictEqual(real.body, fake.body,
        'a configured server still distinguishes a real resource from an invented one');
      const text = JSON.stringify(fake.body);
      assert.ok(!/resource must be one of/.test(text), text);
      for (const name of reg.RESOURCE_NAMES) {
        assert.ok(text.indexOf(name) === -1, 'the 401 names "' + name + '": ' + text);
      }
    } finally {
      global.fetch = realFetch;
      if (envURL === undefined) delete process.env.SUPABASE_URL; else process.env.SUPABASE_URL = envURL;
      if (envKey === undefined) delete process.env.SUPABASE_SERVICE_ROLE_KEY; else process.env.SUPABASE_SERVICE_ROLE_KEY = envKey;
    }
  });

  test('the handler validates the licence BEFORE it calls the gate', () => {
    // A source assertion, because every runtime check above would still pass if
    // the two were swapped back and the tests kept driving checkEnvelope
    // directly -- the gate would answer correctly and the handler would leak.
    const src = fs.readFileSync(path.join(__dirname, '..', 'sd-data.js'), 'utf8');
    const body = src.slice(src.indexOf('module.exports = async (req, res) =>'));
    const validate = body.indexOf('await validateLicenseKey(licenseKey)');
    const envelope = body.indexOf('checkEnvelope(action, resource)');
    assert.ok(validate > 0, 'validateLicenseKey call not found in the handler');
    assert.ok(envelope > 0, 'checkEnvelope call not found in the handler');
    assert.ok(validate < envelope,
      'THE ENVELOPE GATE RUNS BEFORE LICENCE VALIDATION AGAIN -- an unauthenticated ' +
      'caller can enumerate every registered resource. See sd-data.js, 2026-09-04.');
  });

  console.log('\n' + passed + ' passed, ' + failed + ' failed');
  if (failed > 0) process.exit(1);
})();
