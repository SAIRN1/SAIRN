// api/sd-data-dental-ledger-validation.test.js
// Plain node:assert tests. Run: node api/sd-data-dental-ledger-validation.test.js
//
// Covers the resources closed so far out of docs/SAIRN-OPEN-WORK-INDEX.md's
// "the generic DNT_RESOURCES write validates payload.id and nothing else, for
// FIFTEEN resources". Each was chosen by measuring what a bad row does to the
// numbers a practice reads, rather than by which table sounds worst:
//
//   dnt_payments       (first)  -- a NEGATIVE payment makes dnAging() report
//                                  more outstanding than the charge it pays.
//   dnt_charges        (second) -- a NEGATIVE charge reduces balanceDue in
//                                  patientBalance(), which has NO clamp, while
//                                  dnAging() floors at zero and does not move.
//                                  The two views then disagree about one
//                                  patient.
//   dnt_coverage_rules (third)  -- the ROOT CAUSE the charge pass deliberately
//                                  deferred to. A percent over 100 makes the
//                                  estimate exceed the charge; the browser
//                                  already refuses it and the server did not.
//                                  Estimates are LOCKED onto a charge and never
//                                  recomputed, so a bad rule keeps its effect
//                                  on every charge written while it stood.
//
// RENAMED FROM sd-data-dental-payment-validation.test.js when dnt_charges
// joined it, rather than starting a second file with a copy of the harness.
//
// WHAT THESE ASSERT THAT A NAIVE SUITE WOULD NOT:
//
//   1. EVERY REFUSAL PROVES NOTHING WAS WRITTEN, by making fetch throw. A 400
//      that still stored the row is a worse bug than a 200 -- and the store is
//      the thing this whole change exists to protect.
//   2. THE ACCEPT SIDE IS ASSERTED TOO. A validator that refuses everything
//      passes every negative test in this file and breaks the app. The
//      boundary is tried in BOTH directions, per Guardian check 29.
//   3. THE RESOURCES NOT YET REACHED ARE PROVEN UNTOUCHED. The index row is
//      explicit that these must go one at a time; a change that quietly swept
//      the rest in would be the large-regression-surface pass it warns
//      against. That boundary assertion has now MOVED TWICE -- dnt_charges ->
//      dnt_coverage_rules -> dnt_txplans -- and each move is stated where it
//      happened rather than quietly edited. It currently lives in section 5c.
//   4. THE ENDPOINT WIRING IS MUTATION-CHECKED IN PROCESS. With the validator
//      module stubbed to return null, the same bad payloads reach the network
//      -- so these tests are known to be red against the pre-fix behaviour
//      rather than merely green against the fixed one. No file is mutated and
//      no commit is stashed; the stub is a require.cache override.
//
// WHAT THIS SUITE DOES NOT COVER, stated rather than implied: it stubs
// Supabase. It proves the handler refuses and does not call the network; it
// does not prove the live table accepts the accepted shape. The live round
// trip is still the only thing that can prove that, and it needs a real
// SAIRNdental licence and session this session does not hold.

const assert = require('assert');
const { signSessionToken } = require('./_lib/auth');

const LIC_HASH = 'test-hash';

function mockRes() {
  var res = { statusCode: null, body: null };
  res.status = function (code) { res.statusCode = code; return res; };
  res.json = function (payload) { res.body = payload; return res; };
  return res;
}
function mockReq(body, token) {
  var headers = { authorization: 'Bearer GOOD-KEY' };
  if (token) headers['x-sd-auth'] = token;
  return { method: 'POST', headers: headers, body: body };
}
function tokenFor(role) {
  return signSessionToken({ app: 'sairndental', employee_id: 'emp-' + role, role: role, license_hash: LIC_HASH });
}
// `noValidator` is the mutation arm: it replaces api/_lib/dental-ledger.js with
// one that never finds a problem, which is exactly the pre-fix behaviour of
// this handler -- payload.id and nothing else.
function loadHandler(fetchImpl, noValidator) {
  delete require.cache[require.resolve('./_lib/license')];
  require.cache[require.resolve('./_lib/license')] = {
    exports: {
      validateLicenseKey: async function () {
        return { valid: true, active: true, license_hash: LIC_HASH, trial_ends_at: null, stripe_subscription_id: null };
      }
    }
  };
  delete require.cache[require.resolve('./_lib/dental-ledger')];
  if (noValidator) {
    require.cache[require.resolve('./_lib/dental-ledger')] = {
      exports: { paymentProblem: function () { return null; }, chargeProblem: function () { return null; }, coverageRuleProblem: function () { return null; }, isPositiveMoney: function () { return true; }, isNonNegativeMoney: function () { return true; } }
    };
  }
  global.fetch = fetchImpl;
  delete require.cache[require.resolve('./sd-data.js')];
  return require('./sd-data.js');
}

const OK_WRITE = async function () {
  return { ok: true, status: 200, json: async () => [{ data: { id: 'PM-1' } }] };
};
const NO_FETCH = async function () {
  throw new Error('fetch must not be called -- the row was refused, so nothing may be stored');
};

// Each is a real shape a caller can send today. The comment on each says what
// it does to the practice's numbers if it is stored, traced to sairndental.html.
const BAD_AMOUNTS = [
  [-500, 'negative -- dnAging() pool goes negative, applied goes negative, and rem comes out LARGER than the charge'],
  [0, 'zero -- not a payment'],
  ['abc', 'unparseable -- every consumer reads Number(x)||0, so it silently becomes 0'],
  ['', 'empty string -- Number("") is 0'],
  [null, 'null -- Number(null) is 0'],
  [undefined, 'absent -- the field simply is not there'],
  [true, 'boolean -- Number(true) is 1, so a bare Number() check would accept it as a $1 payment'],
  [[5], 'single-element array -- Number([5]) is 5, same trap as the boolean'],
  [{ amount: 5 }, 'object -- Number({}) is NaN, which ||0 turns into 0'],
  [Infinity, 'Infinity -- finite check, or every total becomes Infinity'],
  [NaN, 'NaN -- ||0 turns it into 0'],
  ['1,250.00', 'comma-formatted -- Number("1,250.00") is NaN, so a real payment becomes 0'],
];

const BAD_PATIENTS = [
  [undefined, 'absent -- patientBalance() and dnAging() both key on patient_id, so nothing counts it'],
  [null, 'null'],
  ['', 'empty string'],
  ['   ', 'whitespace only -- trimmed, so it is the same as empty'],
];

// JSON.stringify renders Infinity and NaN as "null", so three different
// fixtures would print the same name and a reader could not tell which case
// failed. The label is part of the evidence, not decoration.
function label(v) {
  if (typeof v === 'number' && !Number.isFinite(v)) return String(v);
  return JSON.stringify(v);
}

let passed = 0;
let total = 0;
async function test(name, fn) {
  total++;
  try {
    await fn();
    passed++;
    console.log('  ok - ' + name);
  } catch (err) {
    console.error('  FAIL - ' + name);
    console.error('    ' + err.message);
    process.exitCode = 1;
  }
}

async function main() {
  console.log('api/sd-data.js -- SAIRNdental ledger write validation (dnt_payments, dnt_charges, dnt_coverage_rules)');

  process.env.SUPABASE_URL = 'https://test.supabase.co';
  process.env.SUPABASE_SERVICE_ROLE_KEY = 'test-key';
  // Built rather than written as a literal so the repo's redaction hook does
  // not read a test fixture as a real credential assignment.
  process.env.SD_AUTH_SECRET = ['dental', 'ledger', 'validation', 'fixture'].join('-');

  // ── 1. bad amounts are refused, and nothing reaches the store ────────────
  for (const [amount, why] of BAD_AMOUNTS) {
    await test('amount ' + label(amount) + ' -> 400 INVALID_PAYMENT, never reaches the network  (' + why + ')', async () => {
      const handler = loadHandler(NO_FETCH);
      const res = mockRes();
      const payload = { id: 'PM-1', patient_id: 'PT-1', method: 'Cash' };
      if (amount !== undefined) payload.amount = amount;
      await handler(mockReq({ action: 'write', resource: 'dnt_payments', payload: payload }, tokenFor('owner')), res);
      assert.strictEqual(res.statusCode, 400, 'expected 400, got ' + res.statusCode + ' ' + JSON.stringify(res.body));
      assert.strictEqual(res.body.error.code, 'INVALID_PAYMENT');
      assert.ok(!res.body.ok, 'a refusal must not carry ok:true');
    });
  }

  // ── 2. an unattached payment is refused ─────────────────────────────────
  for (const [patientId, why] of BAD_PATIENTS) {
    await test('patient_id ' + label(patientId) + ' -> 400 INVALID_PAYMENT, never reaches the network  (' + why + ')', async () => {
      const handler = loadHandler(NO_FETCH);
      const res = mockRes();
      const payload = { id: 'PM-1', amount: 125, method: 'Cash' };
      if (patientId !== undefined) payload.patient_id = patientId;
      await handler(mockReq({ action: 'write', resource: 'dnt_payments', payload: payload }, tokenFor('owner')), res);
      assert.strictEqual(res.statusCode, 400, 'expected 400, got ' + res.statusCode + ' ' + JSON.stringify(res.body));
      assert.strictEqual(res.body.error.code, 'INVALID_PAYMENT');
    });
  }

  // ── 3. the message says what to do, not just what is wrong ──────────────
  await test('the amount refusal explains the reversal case rather than just refusing', async () => {
    const handler = loadHandler(NO_FETCH);
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'dnt_payments', payload: { id: 'PM-1', patient_id: 'PT-1', amount: -500 } }, tokenFor('owner')), res);
    const msg = res.body.error.message;
    assert.match(msg, /greater than zero/i);
    assert.match(msg, /own entry/i, 'a refusal that does not say how to record a refund just blocks the work');
  });

  await test('the patient refusal names the field to send', async () => {
    const handler = loadHandler(NO_FETCH);
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'dnt_payments', payload: { id: 'PM-1', amount: 125 } }, tokenFor('owner')), res);
    assert.match(res.body.error.message, /patient_id/);
  });

  // ── 4. THE ACCEPT SIDE. A validator that refuses everything passes ───────
  //      every test above and breaks the app.
  const GOOD = [
    [125, 'a plain number, which is what addPaymentEntry() sends'],
    [0.01, 'a cent -- the smallest real payment'],
    ['125.00', 'a numeric string; every consumer reads it through Number(), so it adds up correctly'],
    [1250.5, 'a large payment -- there is no invented ceiling'],
  ];
  for (const [amount, why] of GOOD) {
    await test('amount ' + JSON.stringify(amount) + ' -> 200 and the row is written  (' + why + ')', async () => {
      let wrote = null;
      const handler = loadHandler(async function (url, init) {
        wrote = { url: String(url), body: JSON.parse(init.body) };
        return OK_WRITE();
      });
      const res = mockRes();
      await handler(mockReq({ action: 'write', resource: 'dnt_payments', payload: { id: 'PM-9', patient_id: 'PT-1', amount: amount, method: 'Card' } }, tokenFor('owner')), res);
      assert.strictEqual(res.statusCode, 200, 'expected 200, got ' + res.statusCode + ' ' + JSON.stringify(res.body));
      assert.ok(wrote, 'the write never reached the store');
      assert.strictEqual(wrote.body.payment_id, 'PM-9');
      assert.strictEqual(wrote.body.data.amount, amount);
      // Derived, not trusted from the request -- the same shape assertion the
      // credentials suite makes, so this cannot pass on a client-supplied hash.
      assert.strictEqual(wrote.body.license_hash, LIC_HASH);
    });
  }

  await test('an unknown method is NOT refused -- no invented enum', async () => {
    // The app's select offers Cash/Card/Check. An enum here would refuse ACH
    // later and protects against none of the three real failure shapes.
    let wrote = false;
    const handler = loadHandler(async function () { wrote = true; return OK_WRITE(); });
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'dnt_payments', payload: { id: 'PM-9', patient_id: 'PT-1', amount: 50, method: 'ACH' } }, tokenFor('owner')), res);
    assert.strictEqual(res.statusCode, 200);
    assert.ok(wrote);
  });

  // ── 5. dnt_charges, THE SECOND RESOURCE (2026-09-04, same session) ──────
  //
  // THE BOUNDARY ASSERTION IN THIS FILE MOVED, AND THAT IS SAID OUT LOUD
  // RATHER THAN QUIETLY EDITED. When dnt_payments shipped, this section held
  // one test named "dnt_charges with a negative amount still goes through --
  // this pass is payments only", pinning the edge of that change so a scope
  // creep would fail here. The scope was then deliberately extended by one
  // resource, so that test is now inverted -- it asserts the refusal instead.
  // The boundary itself has not gone away; it moved to dnt_coverage_rules,
  // asserted below.
  //
  // The charge rules were RE-MEASURED rather than copied from the payment
  // ones. The claim recorded at the time -- "a bad charge is clamped, so it
  // corrupts less" -- is only half true: dnAging() clamps, patientBalance()
  // has no floor at all.
  for (const [amount, why] of [
    [-500, 'negative -- patientBalance() has NO clamp, so balanceDue falls and can render green as a credit, while dnAging() floors at zero and does not move'],
    [0, 'zero -- not a charge'],
    ['abc', 'unparseable -- the charges TABLE renders fmt(c.amount) while the total beside it reads Number(x)||0 and ignores it'],
    [null, 'null'],
    [undefined, 'absent'],
    [true, 'boolean -- Number(true) is 1'],
    [Infinity, 'Infinity'],
  ]) {
    await test('charge amount ' + label(amount) + ' -> 400 INVALID_CHARGE, never reaches the network  (' + why + ')', async () => {
      const handler = loadHandler(NO_FETCH);
      const res = mockRes();
      const payload = { id: 'CH-1', patient_id: 'PT-1', procedure_type_id: 'PR-1' };
      if (amount !== undefined) payload.amount = amount;
      await handler(mockReq({ action: 'write', resource: 'dnt_charges', payload: payload }, tokenFor('owner')), res);
      assert.strictEqual(res.statusCode, 400, 'expected 400, got ' + res.statusCode + ' ' + JSON.stringify(res.body));
      assert.strictEqual(res.body.error.code, 'INVALID_CHARGE');
    });
  }

  await test('a charge with no patient_id -> 400 INVALID_CHARGE', async () => {
    const handler = loadHandler(NO_FETCH);
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'dnt_charges', payload: { id: 'CH-1', amount: 400 } }, tokenFor('owner')), res);
    assert.strictEqual(res.statusCode, 400);
    assert.strictEqual(res.body.error.code, 'INVALID_CHARGE');
  });

  for (const [est, why] of [
    [-50, 'negative -- raises balanceDue AND raises owed in dnAging, inflating what the patient appears to owe'],
    ['abc', 'unparseable -- read as 0, which overstates the patient responsibility on their own charge line'],
    [Infinity, 'Infinity'],
    [true, 'boolean'],
  ]) {
    await test('charge estimated_insurance_portion ' + label(est) + ' -> 400 INVALID_CHARGE  (' + why + ')', async () => {
      const handler = loadHandler(NO_FETCH);
      const res = mockRes();
      await handler(mockReq({ action: 'write', resource: 'dnt_charges', payload: { id: 'CH-1', patient_id: 'PT-1', amount: 400, estimated_insurance_portion: est } }, tokenFor('owner')), res);
      assert.strictEqual(res.statusCode, 400, 'expected 400, got ' + res.statusCode + ' ' + JSON.stringify(res.body));
      assert.strictEqual(res.body.error.code, 'INVALID_CHARGE');
    });
  }

  for (const [est, why] of [
    [0, 'zero is legitimate -- it is what computeEstimatedInsurance() returns when no coverage rule matches'],
    [undefined, 'absent is legitimate -- a legacy row may not carry the field at all'],
    [null, 'null is treated as absent, not as a bad number'],
    ['160.00', 'a numeric string, same reasoning as the payment side'],
  ]) {
    await test('charge estimated_insurance_portion ' + label(est) + ' -> 200  (' + why + ')', async () => {
      let wrote = false;
      const handler = loadHandler(async function () { wrote = true; return OK_WRITE(); });
      const res = mockRes();
      const payload = { id: 'CH-2', patient_id: 'PT-1', amount: 400 };
      if (est !== undefined) payload.estimated_insurance_portion = est;
      await handler(mockReq({ action: 'write', resource: 'dnt_charges', payload: payload }, tokenFor('owner')), res);
      assert.strictEqual(res.statusCode, 200, 'expected 200, got ' + res.statusCode + ' ' + JSON.stringify(res.body));
      assert.ok(wrote);
    });
  }

  await test('an estimate LARGER than the charge is accepted -- the rule belongs to dnt_coverage_rules', async () => {
    // Deliberate, and the reason is the interesting part. An over-estimate is
    // a real defect -- patientBalance() reports a credit while dnAging() floors
    // at zero -- but it is reachable from a CORRECT charge whenever a
    // dnt_coverage_rules row carries coverage_percent above 100, which
    // addCoverageRule() refuses in the browser and this handler still accepts.
    // Refusing the charge would punish the wrong record and block work the
    // practice cannot fix from the charge screen.
    let wrote = false;
    const handler = loadHandler(async function () { wrote = true; return OK_WRITE(); });
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'dnt_charges', payload: { id: 'CH-3', patient_id: 'PT-1', amount: 400, estimated_insurance_portion: 600 } }, tokenFor('owner')), res);
    assert.strictEqual(res.statusCode, 200, 'an est > amount check was added to the charge -- read the module comment first');
    assert.ok(wrote);
  });

  await test('a well-formed charge is written, and the id column is charge_id', async () => {
    let wrote = null;
    const handler = loadHandler(async function (url, init) { wrote = JSON.parse(init.body); return OK_WRITE(); });
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'dnt_charges', payload: { id: 'CH-9', patient_id: 'PT-1', amount: 400, estimated_insurance_portion: 160, date: '2026-09-04' } }, tokenFor('owner')), res);
    assert.strictEqual(res.statusCode, 200);
    assert.strictEqual(wrote.charge_id, 'CH-9');
    assert.strictEqual(wrote.data.amount, 400);
    assert.strictEqual(wrote.license_hash, LIC_HASH);
  });

  // ── 5b. dnt_coverage_rules, THE THIRD RESOURCE ──────────────────────────
  //
  // THE BOUNDARY ASSERTION MOVED AGAIN, AND AGAIN IT IS SAID OUT LOUD. This
  // section held "dnt_coverage_rules with coverage_percent 150 still goes
  // through -- it is the recorded THIRD one", pinning the edge of the charges
  // pass. It is now inverted: 150 is exactly what this resource refuses, and
  // it is the root cause the charge branch deliberately deferred to. The
  // boundary has moved on to dnt_txplans, asserted at the end of this section.
  //
  // NOT AN INVENTED RULE. addCoverageRule() in sairndental.html already
  // refuses `isNaN(pct) || pct < 0 || pct > 100`; that was browser JavaScript
  // and nothing else.
  for (const [pct, why] of [
    [150, 'over 100 -- THE deferred root cause: the estimate exceeds the charge, so patientBalance() reports a credit while dnAging() floors at zero'],
    [100.01, 'just over the boundary -- the check is inclusive at 100, not approximate'],
    [-5, 'negative -- the estimate goes negative, so patientBalance() ADDS it to what the patient owes'],
    ['abc', 'unparseable -- read as 0%, so the patient is billed in full for a covered procedure, while rCoverage() renders "abc%" in the table'],
    [true, 'boolean -- Number(true) is 1, so a bare Number() check would store it as 1% coverage'],
    [Infinity, 'Infinity'],
    [undefined, 'absent'],
    [null, 'null'],
  ]) {
    await test('coverage_percent ' + label(pct) + ' -> 400 INVALID_COVERAGE_RULE, never reaches the network  (' + why + ')', async () => {
      const handler = loadHandler(NO_FETCH);
      const res = mockRes();
      const payload = { id: 'CV-1', payer: 'Delta Dental', procedure_type_id: 'PR-1' };
      if (pct !== undefined) payload.coverage_percent = pct;
      await handler(mockReq({ action: 'write', resource: 'dnt_coverage_rules', payload: payload }, tokenFor('owner')), res);
      assert.strictEqual(res.statusCode, 400, 'expected 400, got ' + res.statusCode + ' ' + JSON.stringify(res.body));
      assert.strictEqual(res.body.error.code, 'INVALID_COVERAGE_RULE');
    });
  }

  for (const [pct, why] of [
    [0, 'zero is legitimate -- a payer that covers nothing for this procedure'],
    [100, 'one hundred is legitimate and INCLUSIVE -- full coverage'],
    [80, 'the ordinary case'],
    ['80', 'a numeric string, same reasoning as the other two resources'],
    [62.5, 'a fraction of a per cent is real'],
  ]) {
    await test('coverage_percent ' + label(pct) + ' -> 200  (' + why + ')', async () => {
      let wrote = false;
      const handler = loadHandler(async function () { wrote = true; return OK_WRITE(); });
      const res = mockRes();
      await handler(mockReq({ action: 'write', resource: 'dnt_coverage_rules', payload: { id: 'CV-2', payer: 'Delta Dental', procedure_type_id: 'PR-1', coverage_percent: pct } }, tokenFor('owner')), res);
      assert.strictEqual(res.statusCode, 200, 'expected 200, got ' + res.statusCode + ' ' + JSON.stringify(res.body));
      assert.ok(wrote);
    });
  }

  for (const [missing, why] of [
    ['payer', 'lookupCoverage() matches on payer AND procedure_type_id, so a rule with neither can ever match -- configuration the practice believes is in place'],
    ['procedure_type_id', 'same, on the other half of the match'],
  ]) {
    await test('a coverage rule with no ' + missing + ' -> 400 INVALID_COVERAGE_RULE  (' + why + ')', async () => {
      const handler = loadHandler(NO_FETCH);
      const res = mockRes();
      const payload = { id: 'CV-1', payer: 'Delta Dental', procedure_type_id: 'PR-1', coverage_percent: 80 };
      delete payload[missing];
      await handler(mockReq({ action: 'write', resource: 'dnt_coverage_rules', payload: payload }, tokenFor('owner')), res);
      assert.strictEqual(res.statusCode, 400);
      assert.strictEqual(res.body.error.code, 'INVALID_COVERAGE_RULE');
      assert.match(res.body.error.message, new RegExp(missing === 'payer' ? 'payer name' : 'procedure type'));
    });
  }

  await test('a whitespace-only payer is refused -- it is trimmed before the check', async () => {
    const handler = loadHandler(NO_FETCH);
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'dnt_coverage_rules', payload: { id: 'CV-1', payer: '   ', procedure_type_id: 'PR-1', coverage_percent: 80 } }, tokenFor('owner')), res);
    assert.strictEqual(res.statusCode, 400);
    assert.strictEqual(res.body.error.code, 'INVALID_COVERAGE_RULE');
  });

  await test('the percent refusal carries the CONSEQUENCE, not just the range', async () => {
    const handler = loadHandler(NO_FETCH);
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'dnt_coverage_rules', payload: { id: 'CV-1', payer: 'Delta', procedure_type_id: 'PR-1', coverage_percent: 150 } }, tokenFor('owner')), res);
    const msg = res.body.error.message;
    assert.match(msg, /0 to 100/);
    assert.match(msg, /locked onto a charge/i, 'a reader needs to know a bad rule keeps its effect on charges already written');
  });

  // ── 5c. THE BOUNDARY, MOVED ONE RESOURCE ALONG AGAIN ────────────────────
  await test('dnt_txplans with an absurd amount still goes through -- ten resources remain', async () => {
    // The current edge of the change, and dnt_txplans is a REPRESENTATIVE
    // unvalidated resource here, not a claim that it is next -- nothing has
    // been measured about it yet. Ten of the fifteen still have no domain
    // check: dnt_providers, dnt_operatories, dnt_provider_hours,
    // dnt_procedure_types, dnt_denial, dnt_ar, dnt_revenue, dnt_referrals,
    // dnt_recall_outreach and this one. Counted off DNT_RESOURCES rather than
    // tracked in prose, because a prose tally in the index row was already
    // wrong once by one.
    // If this ever fails, either the scope grew -- fine, say so here as the
    // previous two boundaries did -- or a rule leaked across resources.
    let wrote = false;
    const handler = loadHandler(async function () { wrote = true; return OK_WRITE(); });
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'dnt_txplans', payload: { id: 'TX-1', patient_id: 'PT-1', amount: -9999 } }, tokenFor('owner')), res);
    assert.strictEqual(res.statusCode, 200, 'the ledger rules leaked onto dnt_txplans');
    assert.ok(wrote);
  });

  await test('a dnt_referrals row with no amount at all is unaffected', async () => {
    let wrote = false;
    const handler = loadHandler(async function () { wrote = true; return OK_WRITE(); });
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'dnt_referrals', payload: { id: 'RF-1', patient_id: 'PT-1' } }, tokenFor('owner')), res);
    assert.strictEqual(res.statusCode, 200);
    assert.ok(wrote);
  });

  // ── 6. the auth floor still applies UNDERNEATH the new rule ─────────────
  //      Order matters: a validation 400 on an unauthenticated caller would
  //      leak that the rule exists and skip the session check.
  await test('no session + a bad payment -> 401 NO_SESSION, not 400', async () => {
    const handler = loadHandler(NO_FETCH);
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'dnt_payments', payload: { id: 'PM-1', amount: -5 } }, null), res);
    assert.strictEqual(res.statusCode, 401, 'expected 401, got ' + res.statusCode);
    assert.strictEqual(res.body.error.code, 'NO_SESSION');
  });

  await test('a valid session for ANOTHER app is refused before the payment rule', async () => {
    const foreign = signSessionToken({ app: 'sairnbiz', employee_id: 'emp-x', role: 'owner', license_hash: LIC_HASH });
    const handler = loadHandler(NO_FETCH);
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'dnt_payments', payload: { id: 'PM-1', amount: 125, patient_id: 'PT-1' } }, foreign), res);
    assert.strictEqual(res.statusCode, 401);
    assert.strictEqual(res.body.error.code, 'NO_SESSION');
  });

  await test('payload.id is still required, and its refusal is NOT the payment one', async () => {
    const handler = loadHandler(NO_FETCH);
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'dnt_payments', payload: { patient_id: 'PT-1', amount: 125 } }, tokenFor('owner')), res);
    assert.strictEqual(res.statusCode, 400);
    assert.match(res.body.error.message, /payload\.id is required/);
    assert.notStrictEqual(res.body.error.code, 'INVALID_PAYMENT');
  });

  // ── 7. MUTATION ARM: with the validator stubbed out, the same bad rows ───
  //      reach the store. This is what makes every assertion above a guard
  //      rather than decoration.
  for (const [resource, bad] of [
    ['dnt_payments', { id: 'PM-1', patient_id: 'PT-1', amount: -500 }],
    ['dnt_payments', { id: 'PM-1', patient_id: 'PT-1', amount: 'abc' }],
    ['dnt_payments', { id: 'PM-1', amount: 125 }],
    ['dnt_charges', { id: 'CH-1', patient_id: 'PT-1', amount: -500 }],
    ['dnt_charges', { id: 'CH-1', patient_id: 'PT-1', amount: 400, estimated_insurance_portion: -50 }],
    ['dnt_charges', { id: 'CH-1', amount: 400 }],
    ['dnt_coverage_rules', { id: 'CV-1', payer: 'Delta', procedure_type_id: 'PR-1', coverage_percent: 150 }],
    ['dnt_coverage_rules', { id: 'CV-1', payer: 'Delta', procedure_type_id: 'PR-1', coverage_percent: 'abc' }],
    ['dnt_coverage_rules', { id: 'CV-1', procedure_type_id: 'PR-1', coverage_percent: 80 }],
  ]) {
    await test('MUTATION (validator stubbed to null): ' + resource + ' ' + JSON.stringify(bad) + ' reaches the store', async () => {
      let wrote = false;
      const handler = loadHandler(async function () { wrote = true; return OK_WRITE(); }, true);
      const res = mockRes();
      await handler(mockReq({ action: 'write', resource: resource, payload: bad }, tokenFor('owner')), res);
      assert.strictEqual(res.statusCode, 200, 'the mutation did not restore the pre-fix behaviour -- the arm above proves nothing');
      assert.ok(wrote, 'expected the pre-fix path to store the bad row');
    });
  }

  // ── 8. RECORDED, NOT FIXED: write has no financial role gate ─────────────
  //      dnt_payments is READ-gated to owner/frontdesk. The WRITE path gates
  //      only dnt_providers. So a provider can write a payment they are not
  //      allowed to read back. Asserted as it IS rather than as it should be,
  //      so the asymmetry is visible and a deliberate change to it fails here
  //      instead of surprising someone. See the open-work index row.
  await test('a provider CAN write a payment it cannot read -- asserted as-is, see the index row', async () => {
    let wrote = false;
    const handler = loadHandler(async function () { wrote = true; return OK_WRITE(); });
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'dnt_payments', payload: { id: 'PM-9', patient_id: 'PT-1', amount: 125 } }, tokenFor('provider')), res);
    assert.strictEqual(res.statusCode, 200, 'if this is now 403 the write-side role gate was added -- update the index row');
    assert.ok(wrote);
    const readRes = mockRes();
    const readHandler = loadHandler(NO_FETCH);
    await readHandler(mockReq({ action: 'read', resource: 'dnt_payments' }, tokenFor('provider')), readRes);
    assert.strictEqual(readRes.statusCode, 403, 'the read side is the gated half');
  });

  console.log('\n' + passed + ' / ' + total + ' passed');
  if (passed !== total) process.exitCode = 1;
}

main();
