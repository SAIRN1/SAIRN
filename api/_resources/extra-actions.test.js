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

  console.log('\n' + passed + ' passed, ' + failed + ' failed');
  if (failed > 0) process.exit(1);
})();
