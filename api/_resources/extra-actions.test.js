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

  // ── SPLIT BY TIER, NOT UNIFORM (2026-09-15, item 97) ─────────────────────
  // This arm asserted ['delete'] for all 28 and was GREEN the whole time seven
  // Tier A medical-billing records could be destroyed by a uniform grant nobody
  // had decided per resource. The assertion was true; the thing it asserted was
  // the defect. It is split now so the two populations are checked separately
  // and a name moving between them has to move here too.
  test('every sc_ resource grants exactly one removal verb, split by tier', () => {
    const mod = require('./sairncode');
    const sc = mod.resources;
    const soft = mod.tierASoftDeleteOnly;
    assert.strictEqual(sc.length, 28);
    assert.ok(Array.isArray(soft) && soft.length > 0,
              'tierASoftDeleteOnly is missing or empty, so the split below is vacuous');
    for (const name of soft) {
      assert.ok(sc.indexOf(name) !== -1, name + ' is soft-delete-only but not registered');
    }
    let hard = 0;
    for (const name of sc) {
      const expected = soft.indexOf(name) === -1 ? ['delete'] : ['soft_delete'];
      assert.deepStrictEqual(reg.EXTRA_ACTIONS[name], expected, name);
      if (expected[0] === 'delete') hard += 1;
    }
    // CONTROL: without this, a tierASoftDeleteOnly listing all 28 would pass
    // every assertion above while removing the app's only removal path.
    assert.strictEqual(hard, 28 - soft.length,
                       'the two populations do not partition the 28');
    assert.ok(hard > 0, 'no sc_ resource can be hard-deleted at all any more');
  });

  test('no sc_ resource grants BOTH removal verbs', () => {
    // The failure that would make the tier split meaningless: a Tier A record
    // that still accepts a destroying delete alongside the soft one.
    for (const name of require('./sairncode').resources) {
      const verbs = reg.EXTRA_ACTIONS[name] || [];
      assert.ok(!(verbs.indexOf('delete') !== -1 && verbs.indexOf('soft_delete') !== -1),
                name + ' grants both delete and soft_delete');
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
    // Phase 4b, plus 'gl_export' (2026-09-17, gap A5).
    //
    // THE TRIPWIRE FIRED AND THIS IS THE WIDENING IT ASKS FOR, not a number
    // raised to get past it. `gl_export` was granted on rf_invoices when
    // SAIRNroofing's accounting export shipped, this pin was not updated with
    // it, and the arm has been RED on origin/main since -- with nothing
    // blocking on it, because this suite is not in GUARD_TESTS. A red arm
    // nobody acts on is how the next genuinely red arm beside it gets read as
    // noise, and this file is the gate on every verb on every resource.
    //
    // TWO SESSIONS FOUND AND FIXED THIS INDEPENDENTLY, hours apart, and the
    // resolution keeps both halves rather than one: the sentence above is
    // Hank's account of the red, and the paragraph below is the verification
    // that justifies widening rather than merely silencing it.
    //
    // CHECKED BEFORE WIDENING, the same way rf_company_programs was in
    // 2026-08-25, and read rather than inferred from the verb's name: the
    // handler branch (api/sd-data.js) issues three GETs and no POST, PATCH or
    // DELETE; it reuses the read branch's query and the SAME summarizeInvoice()
    // the customer's own screen uses; and its own suite carries a dedicated arm
    // -- roofing-billing-endpoint.test.js:356, "gl_export writes NOTHING -- an
    // export must never change a book". Compute-only and single-owner like the
    // other three.
    assert.deepStrictEqual(reg.EXTRA_ACTIONS.rf_invoices,
      ['issue', 'add_payment', 'reconcile_claim', 'gl_export']);
    ['issue', 'add_payment', 'reconcile_claim', 'gl_export'].forEach((v) => {
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
  // sc_denial is Tier A as of 2026-09-15 and grants soft_delete, not delete.
  // Both directions are asserted here rather than swapping one for the other:
  // the verb it DOES grant must pass the gate, and the destroying verb it no
  // longer grants must be refused BY THE GATE -- which is the half that makes
  // this a tier split rather than a rename.
  await atest('soft_delete is allowed on sc_denial (Tier A)', async () => {
    assert.strictEqual((await gate('soft_delete', 'sc_denial')).code, PASSED_GATE);
  });
  await atest('...and delete is REFUSED on sc_denial by the gate itself', async () => {
    assert.notStrictEqual((await gate('delete', 'sc_denial')).code, PASSED_GATE);
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
  // ── THIS ARM WAS PINNING THE DEFECT (2026-09-17) ───────────────────────
  // It asserted that `sc_denial` -- one of the SEVEN Tier A records that item
  // 97 made soft-delete-only -- was told the allowed verb is 'delete'. That is
  // the verb the registry no longer grants there and which now answers 403
  // SOFT_DELETE_ONLY, so the arm was holding the message to the one answer
  // item 97 exists to prevent. The old message was built from isSc(), which
  // covers all 28; it is derived from EXTRA_ACTIONS[resource] now.
  //
  // THE SPLIT IS THE POINT, so both halves are driven: a Tier A sc_ resource
  // must name soft_delete and a hard-deletable one must still name delete.
  // Asserting only the first would pass on a message that had simply stopped
  // mentioning delete anywhere.
  await atest('a Tier A sc_ resource names SOFT_DELETE, not delete', async () => {
    assert.strictEqual(
      (await gate('bogus_verb', 'sc_denial')).body.error.message,
      "action must be 'read' or 'write' or 'soft_delete'"
    );
  });
  await atest('...and a hard-deletable sc_ resource still names delete', async () => {
    assert.strictEqual(
      (await gate('bogus_verb', 'sc_dme')).body.error.message,
      "action must be 'read' or 'write' or 'delete'"
    );
  });
  await atest('CONTROL: the two sc_ messages actually DIFFER -- without this '
              + 'both arms would pass on a message that named neither verb',
    async () => {
      const a = (await gate('bogus_verb', 'sc_denial')).body.error.message;
      const b = (await gate('bogus_verb', 'sc_dme')).body.error.message;
      assert.notStrictEqual(a, b);
      assert.ok(!/'delete'/.test(a), 'a Tier A record is still being offered delete: ' + a);
    });
  await atest('a resource with no extra verbs names only read and write', async () => {
    // `profile`, not alf_payer_rules. THE OLD ARM USED alf_payer_rules AND
    // PASSED FOR THE WRONG REASON: that resource really does grant `route`, and
    // the isSc()-based message simply never named a non-sc_ extra verb. The
    // derived message names it, correctly, so the old expectation was pinning
    // the message's blind spot rather than a resource with no extra verbs.
    assert.strictEqual(
      (await gate('bogus_verb', 'profile')).body.error.message,
      "action must be 'read' or 'write'"
    );
  });
  await atest('...and a NON-sc_ resource with an extra verb now names it too, '
              + 'which the old message never did', async () => {
    assert.strictEqual(
      (await gate('bogus_verb', 'alf_payer_rules')).body.error.message,
      "action must be 'read' or 'write' or 'route'"
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
  await atest('THE RESOURCE GATE NOW RUNS FIRST -- reversed 2026-09-08, deliberately', async () => {
    // THIS ASSERTION USED TO SAY THE OPPOSITE, and reversing it is the point.
    // It documented that the ACTION gate sat above the resource gate, so
    // `delete` on an unknown resource was refused for the verb rather than the
    // name. The independent review of the app-boundary commit showed that
    // ordering IS an enumeration oracle: the action message depends on facts
    // about the resource, so sending an extra verb told a caller whether a
    // guessed name exists and which app owns it. Confirmed live, including
    // `bogus_verb` on a foreign sc_ resource still answering "or 'delete'".
    const r = await gate('delete', '__no_such_resource__');
    assert.strictEqual(r.code, REJECTED);
    assert.match(r.body.error.message, /^resource must be one of: /,
      'an unknown resource answered for its VERB again -- the oracle is back');
  });

  await atest('...and an extra verb cannot distinguish a real name from an invented one', async () => {
    // The exact probe the reviewer ran against production.
    const real = handler.checkEnvelope('delete', 'sc_denial', 'stonedesk');
    const fake = handler.checkEnvelope('delete', 'sc_not_a_real_name', 'stonedesk');
    assert.deepStrictEqual(real.body, fake.body, 'the extra-verb oracle is open');
    const realBogus = handler.checkEnvelope('bogus_verb', 'sc_denial', 'stonedesk');
    const fakeBogus = handler.checkEnvelope('bogus_verb', 'sc_not_a_real_name', 'stonedesk');
    assert.deepStrictEqual(realBogus.body, fakeBogus.body,
      'the "or delete" suffix still confirms the sc_ family to an outsider');
  });

  await atest('...but an OWNER still gets the accurate verb message', async () => {
    // Closing the oracle must not make the endpoint useless to the app that
    // owns the resource.
    // soft_delete since 2026-09-17: sc_denial is Tier A and may be hidden,
    // never destroyed. The owner gets the ACCURATE verb, which is the whole
    // point of this arm -- it was previously accurate about the wrong one.
    assert.strictEqual(
      handler.checkEnvelope('bogus_verb', 'sc_denial', 'sairncode').body.error.message,
      "action must be 'read' or 'write' or 'soft_delete'");
    assert.strictEqual(
      handler.checkEnvelope('bogus_verb', 'profile', 'stonedesk').body.error.message,
      "action must be 'read' or 'write'");
  });

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

  // ── PER-APP SCOPING OF THE LIST (2026-09-05) ──────────────────────────
  // The reorder above closed the ANONYMOUS hole. It left an authenticated one:
  // any single app's customer still got all of every other app's resource
  // names. These assert the scoping, and — more importantly — the two ways it
  // could be wrong in the caller's favour.
  console.log('\nScoping — a caller is told about its own app, and shared:');

  await atest('a known app sees ITS OWN resources plus shared, and nothing else', () => {
    const own = new Set(reg.RESOURCE_NAMES_BY_APP.sairndental);
    const shared = new Set(reg.RESOURCE_NAMES_BY_APP.shared);
    const named = handler.checkEnvelope('read', '__nope__', 'sairndental')
      .body.error.message.replace('resource must be one of: ', '').split(', ');
    assert.ok(named.length < reg.RESOURCE_NAMES.length, 'nothing was scoped away');
    named.forEach((n) => assert.ok(own.has(n) || shared.has(n),
      '"' + n + '" belongs to ' + reg.OWNER_BY_RESOURCE[n] + ', not to sairndental'));
    own.forEach((n) => assert.ok(named.indexOf(n) !== -1, 'its own "' + n + '" was withheld'));
    shared.forEach((n) => assert.ok(named.indexOf(n) !== -1, 'shared "' + n + '" was withheld'));
  });

  await atest('...and specifically NOT another app\'s', () => {
    const msg = handler.checkEnvelope('read', '__nope__', 'sairndental').body.error.message;
    ['sc_denial', 'alf_billing', 'rf_claims', 'law_matters'].forEach((n) => {
      if (!reg.RESOURCES[n]) return;      // registry moved; do not assert on a name that left
      assert.ok(msg.indexOf(n) === -1, 'a dental caller was told about "' + n + '"');
    });
  });

  await atest('every registered app scopes to strictly fewer names than the whole platform', () => {
    // One app at a time would pass while a typo'd module quietly fell back.
    reg.APP_NAMES.filter((a) => a !== 'shared').forEach((app) => {
      const named = handler.checkEnvelope('read', '__nope__', app)
        .body.error.message.replace('resource must be one of: ', '').split(', ');
      assert.ok(named.length < reg.RESOURCE_NAMES.length, app + ' was not scoped at all');
    });
  });

  await atest('an UNRECOGNISED app falls back to the full list, deliberately', () => {
    // The conservative direction, chosen because nothing read lic.app_id before
    // this change and a legacy licence with no app_id must not be handed a list
    // missing its own resources. The residual is logged by the handler and
    // recorded in the open-work row -- it is not claimed to be closed.
    [null, undefined, '', '   ', 'not-an-app', 'shared'].forEach((appId) => {
      const msg = handler.checkEnvelope('read', '__nope__', appId).body.error.message;
      assert.strictEqual(msg, 'resource must be one of: ' + reg.RESOURCE_LIST_TEXT,
        'app_id ' + JSON.stringify(appId) + ' scoped to something other than the full list');
    });
  });

  await atest('the response SHAPE is unchanged, because a client matches on it', () => {
    // sairnlaw.html:1389 lawWriteFailText() tests /resource must be one of/.
    // Scoping the names must not change the sentence that client reads.
    assert.match(handler.checkEnvelope('read', '__nope__', 'sairnlaw').body.error.message,
      /^resource must be one of: /);
  });

  test('the handler passes the LICENCE\'s app, never the body\'s', () => {
    // A scoping rule the caller chooses is not a scoping rule. body.app_id is
    // client-supplied and this file's own history records what trusting it cost.
    const raw = fs.readFileSync(path.join(__dirname, '..', 'sd-data.js'), 'utf8');
    const src = raw.split('\n').filter((l) => l.trim().indexOf('//') !== 0).join('\n');
    assert.ok(src.indexOf('checkEnvelope(action, resource, lic.app_id)') > 0,
      'the handler does not pass lic.app_id to checkEnvelope');
    assert.ok(src.indexOf('checkEnvelope(action, resource, body.app_id') === -1 &&
              src.indexOf('checkEnvelope(action, resource, memApp') === -1,
      'the scoping is being fed from the request body');
  });

  test('the handler validates the licence BEFORE it calls the gate', () => {
    // A source assertion, because every runtime check above would still pass if
    // the two were swapped back and the tests kept driving checkEnvelope
    // directly -- the gate would answer correctly and the handler would leak.
    //
    // COMMENTS ARE STRIPPED FIRST, and that is not tidiness. `indexOf` is
    // lexical: a comment quoting `await validateLicenseKey(licenseKey)` placed
    // ABOVE the gate would let this pass while the real call sat below it --
    // and the 27-line block explaining this very ordering sits directly above
    // that call, so quoting the line is the obvious next edit somebody makes.
    // Raised by the independent review of the reorder (2026-09-04); neither
    // string was in a comment at the time, so this closes it before it opens.
    //
    // HONEST LIMIT: this still proves textual order, not execution order. A
    // gate moved into a differently-named helper called earlier would pass it.
    // The five runtime assertions above cover the semantic case; this is
    // defence in depth, and is written down as such rather than oversold.
    const raw = fs.readFileSync(path.join(__dirname, '..', 'sd-data.js'), 'utf8');
    const src = raw.split('\n').filter((l) => l.trim().indexOf('//') !== 0).join('\n');
    const body = src.slice(src.indexOf('module.exports = async (req, res) =>'));
    const validate = body.indexOf('await validateLicenseKey(licenseKey)');
    // Prefix, not the whole call: the third argument was added on 2026-09-05
    // and this assertion went red for the right reason, which is the only
    // evidence it was ever anchored on anything real.
    const envelope = body.indexOf('checkEnvelope(action, resource');
    assert.ok(validate > 0, 'validateLicenseKey call not found in the handler');
    assert.ok(envelope > 0, 'checkEnvelope call not found in the handler');
    assert.ok(validate < envelope,
      'THE ENVELOPE GATE RUNS BEFORE LICENCE VALIDATION AGAIN -- an unauthenticated ' +
      'caller can enumerate every registered resource. See sd-data.js, 2026-09-04.');
  });

  console.log('\n' + passed + ' passed, ' + failed + ' failed');
  if (failed > 0) process.exit(1);
})();
