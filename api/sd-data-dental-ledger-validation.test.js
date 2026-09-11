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
    // ── THE STUB IS DERIVED FROM THE REAL MODULE, not hand-listed (2026-09-09) ──
    // It used to be a literal object naming each export. That went stale the
    // moment a fifth validator was added: sd-data.js destructured
    // `procedureTypeProblem` from a stub that did not have it, so the mutation
    // arms ran against an UNDEFINED validator rather than a permissive one.
    // Node reported it only as a "non-existent property ... inside circular
    // dependency" warning, and the arms would have failed with a TypeError
    // instead of proving that a bad row reaches the store without the check.
    //
    // A hand-written mirror of a module's exports is the same shape as a
    // generated gate that must be regenerated after every edit -- a forgotten
    // update is silently the failure the thing exists to catch. Deriving it
    // means the next resource added to dental-ledger.js is stubbed correctly
    // with no edit here at all.
    const real = require('./_lib/dental-ledger');
    const stub = {};
    Object.keys(real).forEach(function (k) {
      // NON-FUNCTION EXPORTS ARE CARRIED THROUGH UNCHANGED (2026-09-11). This
      // loop used to replace EVERY key with a function. That was harmless
      // while the module exported only functions, and dental-ledger.js gained
      // its first DATA export -- DAY_NAMES, the day list shared with
      // api/sairndental/public-availability.js -- with the provider-hours
      // validator. A stub that turned a shared array into a function would
      // hand the handler something it cannot iterate, and the mutation arm
      // would fail with a TypeError that looks like the arm proving nothing
      // rather than like a broken stub. Same defect class the derivation
      // itself was written to end, one type down.
      if (typeof real[k] !== 'function') { stub[k] = real[k]; return; }
      // *Problem() answers "what is wrong with this record", so a permissive
      // stub returns null (nothing wrong). The is*() predicates answer "is this
      // acceptable", so a permissive stub returns true. Getting these backwards
      // would make the mutation arm refuse everything and still look green.
      stub[k] = /^is[A-Z]/.test(k) ? function () { return true; } : function () { return null; };
    });
    require.cache[require.resolve('./_lib/dental-ledger')] = { exports: stub };
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
  // The title listed three resources while the suite covered five -- it went
  // stale when dnt_denial landed and again here. Derived from the module's own
  // exports instead, so it cannot: a name that appears in this banner is a
  // validator that exists.
  console.log('api/sd-data.js -- SAIRNdental write validation ('
    + Object.keys(require('./_lib/dental-ledger')).filter(function (k) { return /Problem$/.test(k); }).join(', ') + ')');

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

  // ── 5b-ii. NO TWO RULES MAY MATCH THE SAME LOOKUP ───────────────────────
  //
  // lookupCoverage() uses .find(), so two matching rules mean the applied
  // percentage is decided by ROW ORDER. Same defect the dnt_providers branch
  // already refuses for linked_employee_id, in the same handler.
  //
  // The comparison must MIRROR lookupCoverage() exactly -- payer trimmed and
  // lower-cased, procedure_type_id strict -- and that is what most of these
  // arms are for. A check looser than the reader refuses distinct rules; a
  // check tighter than the reader certifies "no conflict" while the reader
  // still collides. Both are worse than no check.
  //
  // `cvHandler` splits the two calls the handler makes: the uniqueness READ
  // and the actual WRITE. Counting them is the only way to prove a 409 stored
  // nothing -- the response alone cannot say.
  function cvHandler(existing, opts) {
    opts = opts || {};
    const calls = { reads: 0, writes: 0 };
    const handler = loadHandler(async function (url, init) {
      const isWrite = init && init.method === 'POST';
      if (isWrite) {
        calls.writes++;
        return OK_WRITE();
      }
      calls.reads++;
      if (opts.readStatus && opts.readStatus !== 200) {
        return { ok: false, status: opts.readStatus, json: async () => ({ message: 'boom' }) };
      }
      return { ok: true, status: 200, json: async () => existing };
    });
    return { handler: handler, calls: calls };
  }
  const CV_EXISTING = [{ coverage_rule_id: 'CV-OLD', data: { id: 'CV-OLD', payer: 'Delta Dental', procedure_type_id: 'PR-1', coverage_percent: 50 } }];
  const cvNew = (over) => Object.assign({ id: 'CV-NEW', payer: 'Delta Dental', procedure_type_id: 'PR-1', coverage_percent: 80 }, over || {});

  await test('a second rule for the same payer and procedure -> 409 COVERAGE_RULE_EXISTS, and NOTHING is written', async () => {
    const c = cvHandler(CV_EXISTING);
    const res = mockRes();
    await c.handler(mockReq({ action: 'write', resource: 'dnt_coverage_rules', payload: cvNew() }, tokenFor('owner')), res);
    assert.strictEqual(res.statusCode, 409, 'expected 409, got ' + res.statusCode + ' ' + JSON.stringify(res.body));
    assert.strictEqual(res.body.error.code, 'COVERAGE_RULE_EXISTS');
    assert.strictEqual(c.calls.writes, 0, 'a refused rule still reached the store');
    assert.strictEqual(c.calls.reads, 1);
  });

  await test('the refusal names the EXISTING percentage, so it is checkable against the rules table', async () => {
    const c = cvHandler(CV_EXISTING);
    const res = mockRes();
    await c.handler(mockReq({ action: 'write', resource: 'dnt_coverage_rules', payload: cvNew() }, tokenFor('owner')), res);
    assert.match(res.body.error.message, /50%/);
    // The app's removeCoverageRule() is local-only and says so. A refusal that
    // told the practice to "remove the existing rule first" would be advice
    // that does not work.
    assert.match(res.body.error.message, /local to that device/i);
  });

  for (const [payer, why] of [
    ['delta dental', 'lower-cased -- lookupCoverage() lower-cases both sides'],
    ['  Delta Dental  ', 'padded -- lookupCoverage() trims both sides'],
    ['DELTA DENTAL', 'upper-cased'],
    [' dElTa DeNtAl ', 'both at once'],
  ]) {
    await test('payer ' + JSON.stringify(payer) + ' still clashes -> 409  (' + why + ')', async () => {
      const c = cvHandler(CV_EXISTING);
      const res = mockRes();
      await c.handler(mockReq({ action: 'write', resource: 'dnt_coverage_rules', payload: cvNew({ payer: payer }) }, tokenFor('owner')), res);
      assert.strictEqual(res.statusCode, 409, 'a payer the READER would match was not caught -- the check is tighter than lookupCoverage()');
      assert.strictEqual(c.calls.writes, 0);
    });
  }

  for (const [over, why] of [
    [{ procedure_type_id: 'PR-2' }, 'same payer, different procedure -- a real, distinct rule'],
    [{ payer: 'Cigna' }, 'different payer, same procedure'],
    [{ id: 'CV-OLD' }, 'the SAME rule id -- an upsert of itself must not clash with itself'],
    [{ procedure_type_id: 1 }, 'a NUMERIC procedure_type_id: lookupCoverage() compares strictly, so it would not match the string form either -- refusing it would be tighter than the reader'],
  ]) {
    await test('accepted: ' + JSON.stringify(over) + '  (' + why + ')', async () => {
      const c = cvHandler(CV_EXISTING);
      const res = mockRes();
      await c.handler(mockReq({ action: 'write', resource: 'dnt_coverage_rules', payload: cvNew(over) }, tokenFor('owner')), res);
      assert.strictEqual(res.statusCode, 200, 'expected 200, got ' + res.statusCode + ' ' + JSON.stringify(res.body));
      assert.strictEqual(c.calls.writes, 1, 'the rule was accepted but never stored');
    });
  }

  await test('CONTROL: the identical payload is accepted when no rule exists -- the 409 is driven by the DATA', async () => {
    // Without this, every 409 above could be a payload the handler simply
    // refuses, and the uniqueness check would be proving nothing.
    const c = cvHandler([]);
    const res = mockRes();
    await c.handler(mockReq({ action: 'write', resource: 'dnt_coverage_rules', payload: cvNew() }, tokenFor('owner')), res);
    assert.strictEqual(res.statusCode, 200, 'expected 200, got ' + res.statusCode + ' ' + JSON.stringify(res.body));
    assert.strictEqual(c.calls.writes, 1);
  });

  await test('the check FAILS CLOSED: an unreadable rules table -> 503, and nothing is written', async () => {
    // A deliberate divergence from the dnt_providers precedent in the same
    // handler, which wraps its read in `if (dupR.ok)` and lets the write
    // through. A uniqueness check that silently does not run is
    // indistinguishable from one that passed.
    const c = cvHandler([], { readStatus: 500 });
    const res = mockRes();
    await c.handler(mockReq({ action: 'write', resource: 'dnt_coverage_rules', payload: cvNew() }, tokenFor('owner')), res);
    assert.strictEqual(res.statusCode, 503, 'expected 503, got ' + res.statusCode + ' ' + JSON.stringify(res.body));
    assert.strictEqual(res.body.error.code, 'COVERAGE_CHECK_UNAVAILABLE');
    assert.strictEqual(c.calls.writes, 0);
    assert.match(res.body.error.message, /row order/i, 'the refusal should say what the unrun check protects against');
  });

  await test('an UNPROVISIONED table is not a check failure -- the write proceeds and answers NOT_PROVISIONED', async () => {
    // 404/400 means the table does not exist, so there is nothing to
    // duplicate. Treating it as a failed check would mask the real state
    // behind a retry message that would never come good.
    const calls = { reads: 0, writes: 0 };
    const handler = loadHandler(async function (url, init) {
      if (init && init.method === 'POST') { calls.writes++; return { ok: false, status: 404, json: async () => ({}) }; }
      calls.reads++;
      return { ok: false, status: 404, json: async () => ({}) };
    });
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'dnt_coverage_rules', payload: cvNew() }, tokenFor('owner')), res);
    assert.strictEqual(res.statusCode, 503);
    assert.strictEqual(res.body.error.code, 'NOT_PROVISIONED', 'got ' + JSON.stringify(res.body));
    assert.strictEqual(calls.writes, 1, 'the write should have been attempted');
  });

  await test('an INVALID payload is refused before the uniqueness read is paid for', async () => {
    const c = cvHandler(CV_EXISTING);
    const res = mockRes();
    await c.handler(mockReq({ action: 'write', resource: 'dnt_coverage_rules', payload: cvNew({ coverage_percent: 150 }) }, tokenFor('owner')), res);
    assert.strictEqual(res.statusCode, 400);
    assert.strictEqual(res.body.error.code, 'INVALID_COVERAGE_RULE');
    assert.strictEqual(c.calls.reads, 0, 'a round trip was spent on a payload that could never be stored');
  });

  // ── THIS BOUNDARY TEST HAS NOW MOVED THREE TIMES, and each move is stated ──
  // dnt_charges -> dnt_coverage_rules -> dnt_procedure_types -> dnt_operatories.
  // Its job is to prove the uniqueness read is scoped to dnt_coverage_rules and
  // is not paid for by every DNT resource, so it needs a resource that reaches
  // the store with NO validator of its own. dnt_procedure_types stopped being
  // one on 2026-09-09 when it became the fifth validated resource -- the old
  // payload here, `{ id, code, description }`, does not even carry the field
  // the app writes (`cdt_code`, not `code`), so it is now correctly a 400.
  // dnt_operatories is the next unvalidated resource; when it acquires rules,
  // move this again and add a line rather than editing this comment away.
  await test('the uniqueness check is scoped to dnt_coverage_rules -- dnt_operatories is unaffected', async () => {
    const c = cvHandler(CV_EXISTING);
    const res = mockRes();
    await c.handler(mockReq({ action: 'write', resource: 'dnt_operatories', payload: { id: 'OP-9', name: 'Room 2' } }, tokenFor('owner')), res);
    assert.strictEqual(res.statusCode, 200);
    assert.strictEqual(c.calls.reads, 0, 'a uniqueness read ran for a resource that does not have the rule');
  });

  // ── 5b-iii. THE CLIENT HAD TO MOVE WITH THE SERVER ──────────────────────
  //
  // A refusal nobody can see is not much better than no refusal. addCoverageRule()
  // wrote to localStorage BEFORE calling the server and then toasted "Saved on
  // this device only -- server sync not yet enabled for this app" on any
  // failure. With a 409 now possible, that would leave the device applying a
  // rule the server rejected, and every estimate computed here would differ
  // from one computed anywhere else -- while the message blamed a sync feature
  // that has been enabled for weeks.
  //
  // Asserted against the source because this is an ordering property, and an
  // ordering property is exactly what a later edit reverts without noticing.
  await test('saveCoverageRule() calls the server BEFORE writing locally, and surfaces the real reason', () => {
    // ANCHOR MOVED 2026-09-04: addCoverageRule() became saveCoverageRule() when
    // it stopped only adding -- it now re-uses an existing rule's id so an edit
    // updates the row in place. A function called add that also updates is the
    // stale-name class this repo keeps correcting, and a test left anchored on
    // the old name would have gone green by absence.
    const fs = require('fs');
    const path = require('path');
    const html = fs.readFileSync(path.join(__dirname, '..', 'sairndental.html'), 'utf8').replace(/\r\n/g, '\n');
    const a = html.indexOf('async function saveCoverageRule()');
    assert.ok(a > 0, 'saveCoverageRule not found -- if it was renamed again, MOVE this anchor rather than deleting the test');
    const fn = html.slice(a, html.indexOf('\n}\n', a));
    const server = fn.indexOf("sdnData('write','dnt_coverage_rules'");
    const local = fn.indexOf("st('dnt_coverage_list'");
    assert.ok(server > 0 && local > 0, 'both calls should still be present');
    assert.ok(server < local,
      'the local write happens before the server call again -- a refused rule would be applied on this device only');
    assert.match(fn, /if\(!syncResult\)\{toast\(dntLastErrText\('dnt_coverage_rules'\)/,
      'the real refusal message is not surfaced');
    // COMMENTS STRIPPED FIRST, and this arm failed without it. The fix's own
    // comment QUOTES the stale string it replaced -- which is exactly the
    // false positive sairn-guardian-v2 records against its strict-args
    // scanner, where a fix commit's explanatory comment quoted the old line
    // and the re-scan flagged it. Match code, not prose.
    const code = fn.split('\n').filter((l) => !l.trim().startsWith('//')).join('\n');
    assert.strictEqual(code.indexOf('server sync not yet enabled'), -1,
      'the stale "sync not enabled" message came back -- sync IS enabled, and that string hid the real reason');
  });

  // ── 5d. dnt_denial, THE FOURTH (2026-09-05) ─────────────────────────────
  //
  // A DIFFERENT FAILURE SHAPE FROM THE THREE ABOVE, and that is why it was
  // taken next rather than another money field. A bad denial does not corrupt
  // a total -- it REMOVES A WARNING. dnAppealWindow() returns
  // { known, deadline, days }; given a denied_on that dnAddDays() cannot parse
  // it returns known:true with deadline:'' and days:null, and rDenials()'s
  // closing-soon filter is `w.known && w.days !== null && w.days <= 14`. The
  // denial silently leaves the warning while still looking like one with a
  // known window. An appeal window that passes unnoticed is money that cannot
  // be recovered afterwards.
  await test('a denial with an UNPARSEABLE date is refused -- it would vanish from the closing-soon warning', async () => {
    const handler = loadHandler(NO_FETCH);
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'dnt_denial', payload: { id: 'DN-1', patient_id: 'PT-1', amount: 250, denied_on: 'last tuesday', stage: 'none' } }, tokenFor('owner')), res);
    assert.strictEqual(res.statusCode, 400, 'expected 400, got ' + res.statusCode);
    assert.strictEqual(res.body.error.code, 'INVALID_DENIAL');
    assert.match(res.body.error.message, /closing soon/);
  });

  // THE ROLLOVER CASE IS ITS OWN ASSERTION because it is the dangerous one and
  // a naive date check passes it. new Date('2026-02-31T00:00:00') is NOT NaN in
  // JavaScript -- it is 3 March -- so dnAddDays() would compute a real-looking
  // appeal deadline counted from a day that never existed. A wrong deadline is
  // worse than a missing one, because nothing about it looks wrong.
  await test('2026-02-31 is refused -- JavaScript rolls it to 3 March rather than rejecting it', async () => {
    const handler = loadHandler(NO_FETCH);
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'dnt_denial', payload: { id: 'DN-1', patient_id: 'PT-1', amount: 250, denied_on: '2026-02-31', stage: 'none' } }, tokenFor('owner')), res);
    assert.strictEqual(res.statusCode, 400);
    assert.strictEqual(res.body.error.code, 'INVALID_DENIAL');
  });

  await test('a real leap day IS accepted -- the date check must not be a calendar it invented', async () => {
    let wrote = false;
    const handler = loadHandler(async function () { wrote = true; return OK_WRITE(); });
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'dnt_denial', payload: { id: 'DN-1', patient_id: 'PT-1', amount: 250, denied_on: '2028-02-29', stage: 'none' } }, tokenFor('owner')), res);
    assert.strictEqual(res.statusCode, 200, 'a valid leap day was refused -- got ' + JSON.stringify(res.body));
    assert.ok(wrote);
  });

  await test('a NEGATIVE denied amount is refused -- it reduces the at-stake total below the other denials', async () => {
    const handler = loadHandler(NO_FETCH);
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'dnt_denial', payload: { id: 'DN-1', patient_id: 'PT-1', amount: -250, denied_on: '2026-01-15', stage: 'none' } }, tokenFor('owner')), res);
    assert.strictEqual(res.statusCode, 400);
    assert.strictEqual(res.body.error.code, 'INVALID_DENIAL');
  });

  await test('a NON-NUMERIC denied amount is refused -- dnAtStake() reads it through Number(x) || 0', async () => {
    const handler = loadHandler(NO_FETCH);
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'dnt_denial', payload: { id: 'DN-1', patient_id: 'PT-1', amount: 'lots', denied_on: '2026-01-15', stage: 'none' } }, tokenFor('owner')), res);
    assert.strictEqual(res.statusCode, 400);
    assert.strictEqual(res.body.error.code, 'INVALID_DENIAL');
  });

  await test('an UNKNOWN stage is refused -- DN_DECIDED has no entry, so the row counts as open forever', async () => {
    const handler = loadHandler(NO_FETCH);
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'dnt_denial', payload: { id: 'DN-1', patient_id: 'PT-1', amount: 250, denied_on: '2026-01-15', stage: 'appealed' } }, tokenFor('owner')), res);
    assert.strictEqual(res.statusCode, 400);
    assert.strictEqual(res.body.error.code, 'INVALID_DENIAL');
    assert.match(res.body.error.message, /open forever/);
  });

  // EVERY stage the form can produce must pass. A validator that accepted only
  // the ones this author happened to think of would refuse real denials, and
  // 'drafted' is the one a DN_DECIDED-derived list would have missed -- it is
  // in the <select> and NOT in DN_DECIDED.
  for (const stage of ['none', 'drafted', 'submitted', 'won', 'partial', 'lost', 'abandoned']) {
    await test('stage "' + stage + '" is accepted -- it is in the form\'s own select', async () => {
      let wrote = false;
      const handler = loadHandler(async function () { wrote = true; return OK_WRITE(); });
      const res = mockRes();
      await handler(mockReq({ action: 'write', resource: 'dnt_denial', payload: { id: 'DN-1', patient_id: 'PT-1', amount: 250, denied_on: '2026-01-15', stage: stage } }, tokenFor('owner')), res);
      assert.strictEqual(res.statusCode, 200, 'stage ' + stage + ' was refused: ' + JSON.stringify(res.body));
      assert.ok(wrote);
    });
  }

  await test('recovered ABOVE the denied amount is refused -- the panel prints "recovered of denied"', async () => {
    const handler = loadHandler(NO_FETCH);
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'dnt_denial', payload: { id: 'DN-1', patient_id: 'PT-1', amount: 250, denied_on: '2026-01-15', stage: 'partial', recovered: 400 } }, tokenFor('owner')), res);
    assert.strictEqual(res.statusCode, 400);
    assert.match(res.body.error.message, /More was recovered/);
  });

  await test('recovered EQUAL to the denied amount is accepted -- a won appeal recovers all of it', async () => {
    let wrote = false;
    const handler = loadHandler(async function () { wrote = true; return OK_WRITE(); });
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'dnt_denial', payload: { id: 'DN-1', patient_id: 'PT-1', amount: 250, denied_on: '2026-01-15', stage: 'won', recovered: 250 } }, tokenFor('owner')), res);
    assert.strictEqual(res.statusCode, 200, 'a fully recovered appeal was refused: ' + JSON.stringify(res.body));
    assert.ok(wrote);
  });

  await test('recovered ABSENT is accepted -- most denials recover nothing and the field is optional', async () => {
    let wrote = false;
    const handler = loadHandler(async function () { wrote = true; return OK_WRITE(); });
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'dnt_denial', payload: { id: 'DN-1', patient_id: 'PT-1', amount: 250, denied_on: '2026-01-15', stage: 'none' } }, tokenFor('owner')), res);
    assert.strictEqual(res.statusCode, 200);
    assert.ok(wrote);
  });

  await test('a denial with no patient_id is refused', async () => {
    const handler = loadHandler(NO_FETCH);
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'dnt_denial', payload: { id: 'DN-1', amount: 250, denied_on: '2026-01-15', stage: 'none' } }, tokenFor('owner')), res);
    assert.strictEqual(res.statusCode, 400);
    assert.strictEqual(res.body.error.code, 'INVALID_DENIAL');
  });

  // The denial rule must not have leaked onto its neighbours. dnt_referrals is
  // checked at the end of this section for the amount rules; this checks the
  // DATE rule specifically, which is new to this pass and the likeliest to leak
  // because several resources carry a date field.
  await test('the DATE rule is scoped to dnt_denial -- dnt_recall_outreach with a junk date still writes', async () => {
    let wrote = false;
    const handler = loadHandler(async function () { wrote = true; return OK_WRITE(); });
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'dnt_recall_outreach', payload: { id: 'RO-1', patient_id: 'PT-1', denied_on: 'not a date', due: '2026-02-31' } }, tokenFor('owner')), res);
    assert.strictEqual(res.statusCode, 200, 'the denial date rule leaked onto dnt_recall_outreach');
    assert.ok(wrote);
  });

  // ── 5e. dnt_procedure_types, THE FIFTH (2026-09-09) ─────────────────────
  //
  // A THIRD FAILURE SHAPE. The money rules corrupt a total; the denial rule
  // removes a warning; this one INVERTS A COMPLIANCE VERDICT. cdtStatusFor()
  // compares effective_from/effective_to against the date of service as
  // STRINGS, so the comparison is correct only for zero-padded ISO.
  //
  // AND IT WAS TAKEN NEXT FOR A GATE THAT IS MISSING, not a number that is
  // wrong: dnt_procedure_types is not in DNT_FINANCIAL_RESOURCES and the write
  // branch role-gates only dnt_providers, so any authenticated role can write
  // this practice's fee schedule.
  const PT_OK = { id: 'PR-1', cdt_code: 'D2740', description: 'Crown, porcelain' };
  function ptWith(extra) {
    const p = {};
    Object.keys(PT_OK).forEach(function (k) { p[k] = PT_OK[k]; });
    Object.keys(extra || {}).forEach(function (k) { p[k] = extra[k]; });
    return p;
  }

  await test('a procedure type with no cdt_code -> 400 INVALID_PROCEDURE_TYPE, and nothing is written', async () => {
    const handler = loadHandler(NO_FETCH);
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'dnt_procedure_types', payload: { id: 'PR-1', description: 'Crown' } }, tokenFor('owner')), res);
    assert.strictEqual(res.statusCode, 400, 'expected 400, got ' + res.statusCode);
    assert.strictEqual(res.body.error.code, 'INVALID_PROCEDURE_TYPE');
    assert.match(res.body.error.message, /claim/);
  });

  await test('a whitespace-only cdt_code is refused -- it is trimmed before the check', async () => {
    const handler = loadHandler(NO_FETCH);
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'dnt_procedure_types', payload: ptWith({ cdt_code: '   ' }) }, tokenFor('owner')), res);
    assert.strictEqual(res.statusCode, 400);
    assert.strictEqual(res.body.error.code, 'INVALID_PROCEDURE_TYPE');
  });

  await test('a procedure type with no description is refused', async () => {
    const handler = loadHandler(NO_FETCH);
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'dnt_procedure_types', payload: { id: 'PR-1', cdt_code: 'D2740' } }, tokenFor('owner')), res);
    assert.strictEqual(res.statusCode, 400);
    assert.strictEqual(res.body.error.code, 'INVALID_PROCEDURE_TYPE');
  });

  // THE SHARP ONE. '2026-1-5' is a date a human reads as January and the string
  // comparison does not: '2026-03-01' < '2026-1-5' is TRUE because '0' < '1',
  // so a March service on a January-effective code reports "did not take effect
  // until 2026-1-5". The verdict is inverted, with a real-looking date in the
  // sentence. The browser cannot produce this -- pc-add-efffrom is an
  // <input type="date"> -- which is exactly why nothing caught it.
  await test('a non-ISO effective_from is refused -- cdtStatusFor() compares it as a STRING', async () => {
    const handler = loadHandler(NO_FETCH);
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'dnt_procedure_types', payload: ptWith({ effective_from: '2026-1-5' }) }, tokenFor('owner')), res);
    assert.strictEqual(res.statusCode, 400);
    assert.strictEqual(res.body.error.code, 'INVALID_PROCEDURE_TYPE');
    assert.match(res.body.error.message, /STRING/);
  });

  // CONTROL FOR THE LEXICOGRAPHIC CLAIM ABOVE, so the rule is not taken on
  // trust: this is the comparison cdtStatusFor() actually performs, and it
  // really does return the wrong answer for the shape the check now refuses.
  await test('the inversion is REAL, not asserted -- the string comparison is reproduced here', () => {
    assert.strictEqual('2026-03-01' < '2026-1-5', true, 'the premise of the ISO rule does not hold');
    assert.strictEqual('2026-03-01' < '2026-01-05', false, 'zero-padded ISO compares correctly, as the rule assumes');
  });

  await test('a rollover effective_to is refused -- 2026-02-31 is 3 March, not an error', async () => {
    const handler = loadHandler(NO_FETCH);
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'dnt_procedure_types', payload: ptWith({ effective_to: '2026-02-31' }) }, tokenFor('owner')), res);
    assert.strictEqual(res.statusCode, 400);
    assert.strictEqual(res.body.error.code, 'INVALID_PROCEDURE_TYPE');
  });

  await test('an INVERTED window is refused -- the code could never read "in effect" on any date', async () => {
    const handler = loadHandler(NO_FETCH);
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'dnt_procedure_types', payload: ptWith({ effective_from: '2026-06-01', effective_to: '2026-01-01' }) }, tokenFor('owner')), res);
    assert.strictEqual(res.statusCode, 400);
    assert.strictEqual(res.body.error.code, 'INVALID_PROCEDURE_TYPE');
    assert.match(res.body.error.message, /never come back/);
  });

  await test('a window of a single day is accepted -- equal dates are not inverted', async () => {
    let wrote = false;
    const handler = loadHandler(async function () { wrote = true; return OK_WRITE(); });
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'dnt_procedure_types', payload: ptWith({ effective_from: '2026-01-01', effective_to: '2026-01-01' }) }, tokenFor('owner')), res);
    assert.strictEqual(res.statusCode, 200, 'got ' + JSON.stringify(res.body));
    assert.ok(wrote);
  });

  // NO WINDOW AT ALL IS THE ORDINARY CASE and must stay writable. cdtStatusFor()
  // has a branch for exactly this -- 'unknown', "no effective window recorded"
  // -- so refusing it here would refuse the state the app is built to report.
  await test('a procedure type with NO effective window is accepted -- that state is reported, not refused', async () => {
    let wrote = false;
    const handler = loadHandler(async function () { wrote = true; return OK_WRITE(); });
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'dnt_procedure_types', payload: PT_OK }, tokenFor('owner')), res);
    assert.strictEqual(res.statusCode, 200, 'got ' + JSON.stringify(res.body));
    assert.ok(wrote);
  });

  await test('empty-string window fields are treated as absent, which is what the form sends', async () => {
    let wrote = false;
    const handler = loadHandler(async function () { wrote = true; return OK_WRITE(); });
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'dnt_procedure_types', payload: ptWith({ effective_from: '', effective_to: '' }) }, tokenFor('owner')), res);
    assert.strictEqual(res.statusCode, 200, 'the form sends "" for an untouched date input -- got ' + JSON.stringify(res.body));
    assert.ok(wrote);
  });

  await test('a NON-NUMERIC default_fee is refused -- the plan total would render NaN', async () => {
    const handler = loadHandler(NO_FETCH);
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'dnt_procedure_types', payload: ptWith({ default_fee: 'abc' }) }, tokenFor('owner')), res);
    assert.strictEqual(res.statusCode, 400);
    assert.strictEqual(res.body.error.code, 'INVALID_PROCEDURE_TYPE');
    assert.match(res.body.error.message, /NaN/);
  });

  // A NEGATIVE FEE IS ACCEPTED ON PURPOSE. parseFloat('-50') is not NaN, so
  // addProcedureType() stores it and the practice may well mean it. This module
  // does not get to overrule the form -- the same standard as "an unknown
  // payment method is NOT refused: no invented enum" earlier in this file.
  await test('a NEGATIVE default_fee is accepted -- the form permits it and this is not an invented rule', async () => {
    let wrote = false;
    const handler = loadHandler(async function () { wrote = true; return OK_WRITE(); });
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'dnt_procedure_types', payload: ptWith({ default_fee: -50 }) }, tokenFor('owner')), res);
    assert.strictEqual(res.statusCode, 200, 'got ' + JSON.stringify(res.body));
    assert.ok(wrote);
  });

  await test('an ABSENT default_fee is accepted -- Number(undefined || 0) is 0, which is honest', async () => {
    let wrote = false;
    const handler = loadHandler(async function () { wrote = true; return OK_WRITE(); });
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'dnt_procedure_types', payload: PT_OK }, tokenFor('owner')), res);
    assert.strictEqual(res.statusCode, 200);
    assert.ok(wrote);
  });

  await test('a negative recall_months is accepted -- it reads as "no recall", which is the common case', async () => {
    let wrote = false;
    const handler = loadHandler(async function () { wrote = true; return OK_WRITE(); });
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'dnt_procedure_types', payload: ptWith({ recall_months: -6 }) }, tokenFor('owner')), res);
    assert.strictEqual(res.statusCode, 200, 'a rule was invented for recall_months -- the form floors it at 0 and the reader filters > 0');
    assert.ok(wrote);
  });

  // THE ROLE LADDER, because the point of taking this resource was the gate
  // that is NOT there. Asserted as it IS: any authenticated role writes the fee
  // schedule. The role is `provider` and not `hygienist` because sairndental's
  // real roster in api/_lib/auth.js:87 is exactly owner, frontdesk, provider --
  // signSessionToken() refused the invented role outright, which is the auth
  // layer doing its job and is worth recording rather than quietly swapping. If this ever returns 403 a write-side role gate was added, and
  // the index row must be updated rather than this test quietly relaxed.
  await test('a PROVIDER can write the fee schedule -- asserted as-is, the write branch role-gates only dnt_providers', async () => {
    let wrote = false;
    const handler = loadHandler(async function () { wrote = true; return OK_WRITE(); });
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'dnt_procedure_types', payload: PT_OK }, tokenFor('provider')), res);
    assert.strictEqual(res.statusCode, 200, 'if this is now 403 a role gate was added -- update the index row, do not relax this test');
    assert.ok(wrote);
  });

  await test('no session + a bad procedure type -> 401 NO_SESSION, not 400', async () => {
    const handler = loadHandler(NO_FETCH);
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'dnt_procedure_types', payload: { id: 'PR-1' } }, null), res);
    assert.strictEqual(res.statusCode, 401, 'the validation refusal ran before the session check -- got ' + res.statusCode);
  });

  // The CDT rules must not have leaked onto neighbours that also carry dates
  // and codes.
  //
  // THE NEIGHBOUR MOVED, AND IT IS STATED HERE RATHER THAN QUIETLY EDITED --
  // the same convention the boundary assertions below follow. This used to use
  // dnt_provider_hours, chosen because its rows carry times that look like the
  // same family of field. dnt_provider_hours GAINED A VALIDATOR on 2026-09-11,
  // so the old payload -- no day_of_week, no times -- is now correctly refused
  // 400 by its own rules, and the test began failing for the right reason.
  // dnt_recall_outreach is the replacement: still unvalidated, and its rows
  // carry dates.
  await test('the CDT rules are scoped to dnt_procedure_types -- dnt_recall_outreach with junk fields still writes', async () => {
    let wrote = false;
    const handler = loadHandler(async function () { wrote = true; return OK_WRITE(); });
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'dnt_recall_outreach', payload: { id: 'RO-1', patient_id: 'PT-1', effective_from: '2026-6-1', effective_to: '2026-1-1', cdt_code: '' } }, tokenFor('owner')), res);
    assert.strictEqual(res.statusCode, 200, 'the procedure-type rules leaked onto dnt_recall_outreach');
    assert.ok(wrote);
  });

  // ── 5d. dnt_txplans, THE SIXTH (2026-09-10) ─────────────────────────────
  // A priced proposal -- the money a patient is asked to accept. Already on
  // DNT_FINANCIAL_RESOURCES and tiered A in docs/CRITICALITY-TIERS.md; the
  // payload shape was the part missing.
  //
  // IT IS THE FIRST OF THE SIX WHERE A BAD ROW BLANKS A PANEL RATHER THAN
  // MOVING A NUMBER, and that is why it was taken next. Every rule below is
  // one saveTxPlan() already refuses in the browser and nothing else.
  const TP_OK = {
    id: 'TP-1', patient_id: 'PT-1', title: 'Crown and two fillings',
    status: 'proposed', items: [{ fee: 900, procedure_type_id: 'PR-1' }],
  };

  // The shape that takes the whole panel down. tpPlanTotals() does
  // (plan.items||[]).forEach(...) INSIDE the .map() that builds the table
  // body, so a non-array items throws there and NO plans render at all.
  // Measured in node: "abc", {a:1}, 42 and true each give
  // `TypeError: forEach is not a function`.
  for (const bad of ['abc', { a: 1 }, 42, true]) {
    await test('items ' + JSON.stringify(bad) + ' is refused -- it would blank the whole panel, not one row', async () => {
      let wrote = false;
      const handler = loadHandler(async function () { wrote = true; return OK_WRITE(); });
      const res = mockRes();
      await handler(mockReq({ action: 'write', resource: 'dnt_txplans', payload: Object.assign({}, TP_OK, { items: bad }) }, tokenFor('owner')), res);
      assert.strictEqual(res.statusCode, 400, 'got ' + res.statusCode + ' ' + JSON.stringify(res.body));
      assert.strictEqual(res.body.error.code, 'INVALID_TREATMENT_PLAN');
      assert.ok(!wrote, 'REFUSED AND STILL WROTE -- the store is what this exists to protect');
    });
  }

  // A negative item fee REDUCES the open-value KPI. There is no clamp anywhere
  // in the plan path -- not tpItemMoney(), not tpPlanTotals(), not
  // rTxPlans()'s open.reduce(). Measured: items [100, -500] -> -400. Unlike
  // dnt_charges there is no second view that floors at zero, so nothing
  // disagrees and nothing flags it.
  await test('a negative item fee is refused -- it reduces open treatment value with no clamp', async () => {
    let wrote = false;
    const handler = loadHandler(async function () { wrote = true; return OK_WRITE(); });
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'dnt_txplans', payload: Object.assign({}, TP_OK, { items: [{ fee: 100 }, { fee: -500 }] }) }, tokenFor('owner')), res);
    assert.strictEqual(res.statusCode, 400);
    assert.ok(/negative/i.test(res.body.error.message), 'the message must name the shape: ' + res.body.error.message);
    assert.ok(/Item 2/.test(res.body.error.message), 'it must say WHICH item: ' + res.body.error.message);
    assert.ok(!wrote);
  });

  await test('a non-numeric item fee is refused -- it contributes 0 while the item still shows', async () => {
    let wrote = false;
    const handler = loadHandler(async function () { wrote = true; return OK_WRITE(); });
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'dnt_txplans', payload: Object.assign({}, TP_OK, { items: [{ fee: 'abc' }] }) }, tokenFor('owner')), res);
    assert.strictEqual(res.statusCode, 400);
    assert.ok(!wrote);
  });

  // A status outside the four-value <select> vocabulary falls out of BOTH KPI
  // filters. Measured on ['Accepted','accepted','proposed','weird']: open=1,
  // decided=1, and TWO plans in neither -- listed in the table, counted in no
  // KPI, invisible to the case-acceptance rate. 'Accepted' is in this list on
  // purpose: a capitalised value is the realistic accident and it fails the
  // strict comparison the app makes.
  for (const bad of ['Accepted', 'weird', '', undefined]) {
    await test('status ' + JSON.stringify(bad) + ' is refused -- it would count in NEITHER KPI', async () => {
      let wrote = false;
      const handler = loadHandler(async function () { wrote = true; return OK_WRITE(); });
      const res = mockRes();
      await handler(mockReq({ action: 'write', resource: 'dnt_txplans', payload: Object.assign({}, TP_OK, { status: bad }) }, tokenFor('owner')), res);
      assert.strictEqual(res.statusCode, 400, 'got ' + res.statusCode);
      assert.ok(!wrote);
    });
  }

  // saveTxPlan() refuses this and says why: it "would sit in the
  // case-acceptance denominator with an unknowable one. Asked for rather than
  // back-filled with today." The decided filter is on STATUS ALONE.
  for (const st of ['accepted', 'declined']) {
    await test('a ' + st + ' plan with no decided_on is refused -- the acceptance denominator would have no date', async () => {
      let wrote = false;
      const handler = loadHandler(async function () { wrote = true; return OK_WRITE(); });
      const res = mockRes();
      await handler(mockReq({ action: 'write', resource: 'dnt_txplans', payload: Object.assign({}, TP_OK, { status: st }) }, tokenFor('owner')), res);
      assert.strictEqual(res.statusCode, 400);
      assert.ok(/decided_on/.test(res.body.error.message));
      assert.ok(!wrote);
    });
  }

  await test('an empty items array is refused -- an empty accepted plan counts in the numerator for nothing', async () => {
    const handler = loadHandler(NO_FETCH);
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'dnt_txplans', payload: Object.assign({}, TP_OK, { items: [] }) }, tokenFor('owner')), res);
    assert.strictEqual(res.statusCode, 400);
  });

  await test('a plan with no patient is refused -- it renders as "(unknown patient)" and every item falls to uncovered', async () => {
    const handler = loadHandler(NO_FETCH);
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'dnt_txplans', payload: Object.assign({}, TP_OK, { patient_id: '' }) }, tokenFor('owner')), res);
    assert.strictEqual(res.statusCode, 400);
  });

  await test('a blank title is refused -- a patient shown two untitled plans cannot tell them apart', async () => {
    const handler = loadHandler(NO_FETCH);
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'dnt_txplans', payload: Object.assign({}, TP_OK, { title: '   ' }) }, tokenFor('owner')), res);
    assert.strictEqual(res.statusCode, 400);
  });

  // ── THE ACCEPT SIDE. A validator that refuses everything passes every
  //    negative test above and breaks the app (Guardian check 29).
  await test('ACCEPT: the record saveTxPlan() actually builds goes through', async () => {
    let wrote = false;
    const handler = loadHandler(async function () { wrote = true; return OK_WRITE(); });
    const res = mockRes();
    // Field for field what saveTxPlan() sends for an undecided plan, including
    // decided_on: '' -- the form stores empty string, not undefined, and a
    // validator that rejected that would break every ordinary save.
    await handler(mockReq({ action: 'write', resource: 'dnt_txplans', payload: { id: 'TP-9', patient_id: 'PT-1', provider_id: '', title: 'Plan', status: 'presented', decided_on: '', note: '', items: [{ fee: 250, procedure_type_id: 'PR-1', phase: 1 }], created_at: '2026-09-10' } }, tokenFor('owner')), res);
    assert.strictEqual(res.statusCode, 200, 'got ' + res.statusCode + ' ' + JSON.stringify(res.body));
    assert.ok(wrote);
  });

  await test('ACCEPT: an accepted plan WITH a decision date goes through', async () => {
    let wrote = false;
    const handler = loadHandler(async function () { wrote = true; return OK_WRITE(); });
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'dnt_txplans', payload: Object.assign({}, TP_OK, { status: 'accepted', decided_on: '2026-09-01' }) }, tokenFor('owner')), res);
    assert.strictEqual(res.statusCode, 200, JSON.stringify(res.body));
    assert.ok(wrote);
  });

  await test('ACCEPT: an item with no fee at all, and a fee of zero, both go through', async () => {
    for (const items of [[{ procedure_type_id: 'PR-1' }], [{ fee: 0 }], [{ fee: '900' }]]) {
      const handler = loadHandler(OK_WRITE);
      const res = mockRes();
      await handler(mockReq({ action: 'write', resource: 'dnt_txplans', payload: Object.assign({}, TP_OK, { items }) }, tokenFor('owner')), res);
      assert.strictEqual(res.statusCode, 200, JSON.stringify(items) + ' -> ' + JSON.stringify(res.body));
    }
  });

  // A FUTURE decided_on is DELIBERATELY allowed. saveTxPlan() refuses it
  // against the browser's local today; this module cannot know the practice's
  // timezone, and refusing against UTC would reject a plan decided on the
  // correct local day west of UTC in the evening. Same call denialProblem()
  // made for denied_on -- asserted so nobody "fixes" it later without reading
  // why. THE UTC-MIDNIGHT TRAP IS REAL ON THIS PLATFORM.
  await test('a FUTURE decided_on is allowed on purpose -- the UTC-midnight trap', async () => {
    const handler = loadHandler(OK_WRITE);
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'dnt_txplans', payload: Object.assign({}, TP_OK, { status: 'accepted', decided_on: '2099-01-01' }) }, tokenFor('owner')), res);
    assert.strictEqual(res.statusCode, 200, 'a UTC-based future check was added -- read the reasoning in dental-ledger.js first');
  });

  await test('no session + a bad treatment plan -> 401 NO_SESSION, not 400', async () => {
    const handler = loadHandler(NO_FETCH);
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'dnt_txplans', payload: { id: 'TP-1' } }, null), res);
    assert.strictEqual(res.statusCode, 401, 'the validation refusal ran before the session check');
  });

  // ── 5e. dnt_provider_hours, THE SEVENTH (2026-09-11) ────────────────────
  // THE ONLY ONE OF THE NINE THAT FED AN UNAUTHENTICATED, PATIENT-FACING
  // SURFACE. api/sairndental/public-availability.js reads every hours row for
  // the licence and generates the booking slots a member of the public is
  // offered. Every expectation below was measured against that real slot loop
  // in node, on a Monday with 30-minute appointments: a good 09:00-11:00 block
  // gives 4 slots.
  const PH_OK = {
    id: 'PH-1', provider_id: 'PV-1', day_of_week: 'Monday',
    start_time: '09:00', end_time: '11:00',
  };

  // THE SEVEN SILENT SHAPES. Each gives ZERO slots, so the provider reads as
  // fully booked to every patient, permanently, with nothing logged. That
  // outcome has already happened in production once from a different cause and
  // public-availability.js still carries the comment recording it.
  for (const [label, patch] of [
    ['start_time "9" (no minutes -- Date.UTC gets undefined)', { start_time: '9' }],
    ['start_time "abc"', { start_time: 'abc' }],
    ['start_time absent (String(undefined) -> "undefined")', { start_time: undefined }],
    ['end_time absent', { end_time: undefined }],
    ['end before start', { start_time: '11:00', end_time: '09:00' }],
    ['end equal to start', { end_time: '09:00' }],
    ['day_of_week "monday" -- the filter is ===', { day_of_week: 'monday' }],
    ['day_of_week "Mon"', { day_of_week: 'Mon' }],
    ['no provider_id -- the block belongs to nobody', { provider_id: '' }],
  ]) {
    await test('SILENT ZERO SLOTS refused: ' + label, async () => {
      let wrote = false;
      const handler = loadHandler(async function () { wrote = true; return OK_WRITE(); });
      const res = mockRes();
      await handler(mockReq({ action: 'write', resource: 'dnt_provider_hours', payload: Object.assign({}, PH_OK, patch) }, tokenFor('owner')), res);
      assert.strictEqual(res.statusCode, 400, 'got ' + res.statusCode + ' ' + JSON.stringify(res.body));
      assert.strictEqual(res.body.error.code, 'INVALID_PROVIDER_HOURS');
      assert.ok(!wrote, 'REFUSED AND STILL WROTE -- the store is what this protects');
    });
  }

  // THE ONE THAT FABRICATES INSTEAD OF HIDING, and the reason this resource
  // was taken ahead of the other eight. Date.UTC(y,m,d,29,0) rolls into the
  // NEXT DAY: measured, end_time "29:00" from a 22:00 start produced FOURTEEN
  // slots, the last at 04:30 the following morning -- appointments offered to
  // anonymous callers at times and on a day the practice is not open. An
  // <input type="time"> cannot produce it; this handler accepted it.
  for (const bad of ['29:00', '24:00', '09:60', '99:99']) {
    await test('OUT-OF-RANGE time refused: ' + bad + ' -- it would offer slots on the WRONG DAY', async () => {
      let wrote = false;
      const handler = loadHandler(async function () { wrote = true; return OK_WRITE(); });
      const res = mockRes();
      await handler(mockReq({ action: 'write', resource: 'dnt_provider_hours', payload: Object.assign({}, PH_OK, { start_time: '22:00', end_time: bad }) }, tokenFor('owner')), res);
      assert.strictEqual(res.statusCode, 400, bad + ' -> ' + res.statusCode);
      assert.ok(!wrote);
    });
  }

  // THE ACCEPT SIDE. A validator that refuses everything passes every negative
  // test above and closes the practice's whole calendar (Guardian check 29).
  await test('ACCEPT: the record addProviderHours() actually builds goes through', async () => {
    let wrote = false;
    const handler = loadHandler(async function () { wrote = true; return OK_WRITE(); });
    const res = mockRes();
    // Field for field what addProviderHours() sends: an <input type="time">
    // value is HH:MM, and the day comes from a <select> of the seven names.
    await handler(mockReq({ action: 'write', resource: 'dnt_provider_hours', payload: { id: 'PH-9', provider_id: 'PV-1', day_of_week: 'Wednesday', start_time: '08:30', end_time: '17:00', created_at: '2026-09-11' } }, tokenFor('owner')), res);
    assert.strictEqual(res.statusCode, 200, 'got ' + res.statusCode + ' ' + JSON.stringify(res.body));
    assert.ok(wrote);
  });

  // ALL SEVEN DAY NAMES, derived from the list the reader uses rather than
  // retyped here -- a second copy could drift from public-availability.js and
  // the drift would be invisible in the silent direction.
  await test('ACCEPT: every one of the seven DAY_NAMES the reader compares against', async () => {
    const { DAY_NAMES } = require('./_lib/dental-ledger');
    assert.strictEqual(DAY_NAMES.length, 7);
    for (const day of DAY_NAMES) {
      const handler = loadHandler(OK_WRITE);
      const res = mockRes();
      await handler(mockReq({ action: 'write', resource: 'dnt_provider_hours', payload: Object.assign({}, PH_OK, { day_of_week: day }) }, tokenFor('owner')), res);
      assert.strictEqual(res.statusCode, 200, day + ' -> ' + JSON.stringify(res.body));
    }
  });

  // ONE DAY LIST, NOT TWO. public-availability.js used to declare its own copy.
  // This asserts the endpoint now takes it from the validator module, because a
  // second copy is how the capitalisation rule above quietly stops matching.
  await test('public-availability.js imports DAY_NAMES rather than declaring its own', async () => {
    const src = require('fs').readFileSync(require('path').join(__dirname, 'sairndental', 'public-availability.js'), 'utf8');
    // Comment-stripped, per CLAUDE.md: a probe that asserts something about
    // CODE must not match the comment that explains the change. The comment
    // above the import names DAY_NAMES several times.
    const code = src.split('\n').filter((l) => !l.trim().startsWith('//')).join('\n');
    assert.ok(/require\(['"]\.\.\/_lib\/dental-ledger['"]\)/.test(code),
      'the endpoint no longer imports the shared day list');
    assert.ok(!/const\s+DAY_NAMES\s*=\s*\[/.test(code),
      'a second DAY_NAMES literal is back in the endpoint -- it can drift from the validator');
  });

  await test('ACCEPT: HH:MM:SS, a single-digit hour, and a block ending 23:59', async () => {
    for (const patch of [
      { start_time: '09:00:00', end_time: '11:00:00' },
      { start_time: '9:00' },
      { start_time: '23:00', end_time: '23:59' },
      { start_time: '00:00', end_time: '00:30' },
    ]) {
      const handler = loadHandler(OK_WRITE);
      const res = mockRes();
      await handler(mockReq({ action: 'write', resource: 'dnt_provider_hours', payload: Object.assign({}, PH_OK, patch) }, tokenFor('owner')), res);
      assert.strictEqual(res.statusCode, 200, JSON.stringify(patch) + ' -> ' + JSON.stringify(res.body));
    }
  });

  await test('no session + bad provider hours -> 401 NO_SESSION, not 400', async () => {
    const handler = loadHandler(NO_FETCH);
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'dnt_provider_hours', payload: { id: 'PH-1' } }, null), res);
    assert.strictEqual(res.statusCode, 401, 'the validation refusal ran before the session check');
  });

  // -- 5f. dnt_providers, THE EIGHTH (2026-09-11) ---------------------------
  // THE ROSTER IS THE ACCESS-CONTROL TABLE: dntLinkedProvider() finds the
  // caller's row by linked_employee_id and the result becomes the patient set
  // a non-broad-read role may see.
  //
  // DELIBERATELY SMALL, and that is the honest framing. The role gate
  // (management-only, 2026-08-27) and the duplicate-link 409 were already
  // here, and api/sd-data-dental-provider-scope.test.js owns them. What these
  // arms add is the payload shape.
  const PV_OK = { id: 'PV-1', name: 'Dr Ada Chen', role: 'Dentist', linked_employee_id: '' };

  for (const [label, patch] of [
    ['no name', { name: '' }],
    ['a whitespace-only name', { name: '   ' }],
    ['name absent', { name: undefined }],
  ]) {
    await test('a provider with ' + label + ' is refused -- three render sites draw a BLANK cell', async () => {
      let wrote = false;
      const handler = loadHandler(async function () { wrote = true; return OK_WRITE(); });
      const res = mockRes();
      await handler(mockReq({ action: 'write', resource: 'dnt_providers', payload: Object.assign({}, PV_OK, patch) }, tokenFor('owner')), res);
      assert.strictEqual(res.statusCode, 400, 'got ' + res.statusCode + ' ' + JSON.stringify(res.body));
      assert.strictEqual(res.body.error.code, 'INVALID_PROVIDER');
      assert.ok(!wrote, 'REFUSED AND STILL WROTE');
    });
  }

  // A non-string linked_employee_id can never match the token's string
  // employee_id, so a provider who IS linked reads as UNLINKED and every
  // patient read answers 403 PROVIDER_NOT_LINKED -- fail-closed, and a support
  // incident with no diagnosable cause because the roster still shows the link.
  // THE STUB HERE COUNTS ONLY POSTs, and that is not a convenience. A truthy
  // linked_employee_id makes this branch legitimately READ dnt_providers first
  // for the duplicate-link 409 check, so an arm that treats ANY fetch as a
  // write reports "refused and still wrote" on a refusal that stored nothing.
  // It did, on the first run of these four. The store is still what is being
  // protected -- the assertion just has to name it.
  for (const bad of [1001, { a: 1 }, true, ['x']]) {
    await test('linked_employee_id ' + JSON.stringify(bad) + ' is refused -- === can never match it', async () => {
      let posted = false;
      const handler = loadHandler(async function (url, opts) {
        if (opts && opts.method === 'POST') posted = true;
        return OK_WRITE();
      });
      const res = mockRes();
      await handler(mockReq({ action: 'write', resource: 'dnt_providers', payload: Object.assign({}, PV_OK, { linked_employee_id: bad }) }, tokenFor('owner')), res);
      assert.strictEqual(res.statusCode, 400, JSON.stringify(bad) + ' -> ' + res.statusCode);
      assert.strictEqual(res.body.error.code, 'INVALID_PROVIDER');
      assert.ok(!posted, 'REFUSED AND STILL POSTED -- the store is what this protects');
    });
  }

  await test('ACCEPT: an unlinked provider, a linked one, and one with no role at all', async () => {
    for (const patch of [
      {},
      { linked_employee_id: '1001' },
      { linked_employee_id: undefined },
      { linked_employee_id: null },
      { role: undefined },
    ]) {
      const handler = loadHandler(OK_WRITE);
      const res = mockRes();
      await handler(mockReq({ action: 'write', resource: 'dnt_providers', payload: Object.assign({}, PV_OK, patch) }, tokenFor('owner')), res);
      assert.strictEqual(res.statusCode, 200, JSON.stringify(patch) + ' -> ' + JSON.stringify(res.body));
    }
  });

  // role is DELIBERATELY not validated: the only reader is
  // `$('pv-edit-role').value = p.role || 'Dentist'`, which tolerates anything.
  // Asserted so nobody adds a rule the app itself defaults around.
  await test('an out-of-vocabulary role is ALLOWED on purpose -- the app defaults around it', async () => {
    const handler = loadHandler(OK_WRITE);
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'dnt_providers', payload: Object.assign({}, PV_OK, { role: 'Chief Wizard' }) }, tokenFor('owner')), res);
    assert.strictEqual(res.statusCode, 200, 'a role vocabulary was added -- read the reasoning in dental-ledger.js first');
  });

  // ── 5f. THE BOUNDARY, MOVED ONE RESOURCE ALONG AGAIN ────────────────────
  await test('dnt_referrals with a junk shape still goes through -- SEVEN resources remain', async () => {
    // The current edge, and dnt_referrals is a REPRESENTATIVE unvalidated
    // resource, not a claim that it is next -- nothing has been measured about
    // it yet.
    //
    // COUNTED OFF DNT_RESOURCES, NOT OFF THIS COMMENT, and the history is kept
    // because the count has now moved three times and been wrong twice. It
    // said "EIGHT of the fifteen" and listed eight; then SEVENTEEN and NINE,
    // after dnt_supplies and dnt_vendor_orders joined DNT_RESOURCES on
    // 2026-09-10 with the vendor-collections work.
    //
    // NOW: DNT_RESOURCES holds SEVENTEEN. NINE are validated --
    // dnt_patients, dnt_payments, dnt_charges, dnt_coverage_rules, dnt_denial,
    // dnt_procedure_types, dnt_txplans, dnt_provider_hours and dnt_providers
    // -- plus dnt_gfe's issue-time check. So SEVEN have no domain check:
    // dnt_operatories, dnt_ar, dnt_revenue, dnt_referrals,
    // dnt_recall_outreach, dnt_supplies, dnt_vendor_orders.
    //
    // dnt_provider_hours came off on 2026-09-11 -- the only one that fed an
    // UNAUTHENTICATED, PATIENT-FACING surface (public-availability.js
    // generates public booking slots from it). dnt_providers came off the same
    // day -- the roster IS the access-control table for patient scoping.
    //
    // If this ever fails, either the scope grew -- fine, say so here as the
    // previous four boundaries did -- or a rule leaked across resources.
    let wrote = false;
    const handler = loadHandler(async function () { wrote = true; return OK_WRITE(); });
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'dnt_referrals', payload: { id: 'RF-1', patient_id: 'PT-1', title: '', status: 'weird', items: 'not-an-array' } }, tokenFor('owner')), res);
    assert.strictEqual(res.statusCode, 200, 'the treatment-plan rules leaked onto dnt_referrals');
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
    ['dnt_denial', { id: 'DN-1', patient_id: 'PT-1', amount: 250, denied_on: 'last tuesday', stage: 'none' }],
    ['dnt_denial', { id: 'DN-1', patient_id: 'PT-1', amount: 250, denied_on: '2026-02-31', stage: 'none' }],
    ['dnt_denial', { id: 'DN-1', patient_id: 'PT-1', amount: -250, denied_on: '2026-01-15', stage: 'none' }],
    ['dnt_denial', { id: 'DN-1', patient_id: 'PT-1', amount: 250, denied_on: '2026-01-15', stage: 'appealed' }],
    ['dnt_denial', { id: 'DN-1', patient_id: 'PT-1', amount: 250, denied_on: '2026-01-15', stage: 'partial', recovered: 400 }],
    ['dnt_procedure_types', { id: 'PR-1', description: 'Crown' }],
    ['dnt_procedure_types', { id: 'PR-1', cdt_code: 'D2740' }],
    ['dnt_procedure_types', { id: 'PR-1', cdt_code: 'D2740', description: 'Crown', effective_from: '2026-1-5' }],
    ['dnt_procedure_types', { id: 'PR-1', cdt_code: 'D2740', description: 'Crown', effective_to: '2026-02-31' }],
    ['dnt_procedure_types', { id: 'PR-1', cdt_code: 'D2740', description: 'Crown', effective_from: '2026-06-01', effective_to: '2026-01-01' }],
    ['dnt_procedure_types', { id: 'PR-1', cdt_code: 'D2740', description: 'Crown', default_fee: 'abc' }],
    // dnt_txplans (2026-09-10). The first entry here is the one that matters
    // most: pre-fix, a non-array `items` reached the store, and every later
    // render of the Treatment Plans panel threw on it.
    ['dnt_txplans', { id: 'TP-1', patient_id: 'PT-1', title: 'Plan', status: 'proposed', items: 'abc' }],
    ['dnt_txplans', { id: 'TP-1', patient_id: 'PT-1', title: 'Plan', status: 'proposed', items: [{ fee: -500 }] }],
    ['dnt_txplans', { id: 'TP-1', patient_id: 'PT-1', title: 'Plan', status: 'Accepted', items: [{ fee: 100 }] }],
    ['dnt_txplans', { id: 'TP-1', patient_id: 'PT-1', title: 'Plan', status: 'accepted', items: [{ fee: 100 }] }],
    ['dnt_txplans', { id: 'TP-1', patient_id: 'PT-1', title: '', status: 'proposed', items: [{ fee: 100 }] }],
    ['dnt_txplans', { id: 'TP-1', title: 'Plan', status: 'proposed', items: [{ fee: 100 }] }],
    // dnt_provider_hours (2026-09-11). The last entry is the one that matters
    // most: pre-fix, end_time "29:00" reached the store and public-
    // availability.js then offered fourteen slots ending at 04:30 the next
    // morning, to anonymous callers.
    ['dnt_provider_hours', { id: 'PH-1', provider_id: 'PV-1', day_of_week: 'monday', start_time: '09:00', end_time: '11:00' }],
    ['dnt_provider_hours', { id: 'PH-1', provider_id: 'PV-1', day_of_week: 'Monday', start_time: '9', end_time: '11:00' }],
    ['dnt_provider_hours', { id: 'PH-1', provider_id: 'PV-1', day_of_week: 'Monday', start_time: '11:00', end_time: '09:00' }],
    ['dnt_provider_hours', { id: 'PH-1', day_of_week: 'Monday', start_time: '09:00', end_time: '11:00' }],
    ['dnt_provider_hours', { id: 'PH-1', provider_id: 'PV-1', day_of_week: 'Monday', start_time: '22:00', end_time: '29:00' }],
    // dnt_providers (2026-09-11).
    ['dnt_providers', { id: 'PV-1', name: '', linked_employee_id: '' }],
    ['dnt_providers', { id: 'PV-1', name: 'Dr Ada Chen', linked_employee_id: 1001 }],
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

  // ── 8. THE ASYMMETRY IS CLOSED (2026-09-10) ────────────────────────
  //      This test used to assert the DEFECT: dnt_payments was READ-gated to
  //      owner/frontdesk while the write path gated only dnt_providers, so a
  //      provider could write a payment they could not read back. It was
  //      asserted as-is, on purpose, so that changing it would fail here rather
  //      than surprise someone -- and it did exactly that when the gate landed.
  //      UPDATED, NOT RELAXED, which is what its own message asked for.
  //
  //      BOTH HALVES ARE STILL ASSERTED. Flipping the write to 403 and deleting
  //      the read assertion would leave the pair untested and a future
  //      one-sided change invisible again, which is the whole failure this test
  //      was written around.
  await test('a provider can NEITHER write NOR read a payment -- the tier is symmetric now', async () => {
    let wrote = false;
    const handler = loadHandler(async function () { wrote = true; return OK_WRITE(); });
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'dnt_payments', payload: { id: 'PM-9', patient_id: 'PT-1', amount: 125 } }, tokenFor('provider')), res);
    assert.strictEqual(res.statusCode, 403, 'the write side is gated now -- api/sd-data.js DNT_FINANCIAL_RESOURCES on the write branch');
    assert.strictEqual(res.body && res.body.error && res.body.error.code, 'ROLE_NOT_PERMITTED');
    assert.strictEqual(wrote, false, 'REFUSED BEFORE THE STORE, not after -- a 403 that already wrote is not a gate');
    const readRes = mockRes();
    const readHandler = loadHandler(NO_FETCH);
    await readHandler(mockReq({ action: 'read', resource: 'dnt_payments' }, tokenFor('provider')), readRes);
    assert.strictEqual(readRes.statusCode, 403, 'the read side was always the gated half and still is');
  });

  // NEGATIVE CONTROL. A gate that refuses everyone is not a tier, and a test
  // that only proves the refusal cannot tell the two apart.
  await test('CONTROL: front desk can still write a payment', async () => {
    let wrote = false;
    const handler = loadHandler(async function () { wrote = true; return OK_WRITE(); });
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'dnt_payments', payload: { id: 'PM-10', patient_id: 'PT-1', amount: 125 } }, tokenFor('frontdesk')), res);
    assert.strictEqual(res.statusCode, 200);
    assert.ok(wrote);
  });

  // CONTROL: a NON-financial resource is untouched by the new gate, so this is
  // a tier and not a blanket provider write ban.
  await test('CONTROL: a provider can still write a non-financial resource', async () => {
    let wrote = false;
    const handler = loadHandler(async function () { wrote = true; return OK_WRITE(); });
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'dnt_appointments', payload: { id: 'AP-1', patient_id: 'PT-1' } }, tokenFor('provider')), res);
    assert.strictEqual(res.statusCode, 200, 'dnt_appointments is not in DNT_FINANCIAL_RESOURCES');
    assert.ok(wrote);
  });

  console.log('\n' + passed + ' / ' + total + ' passed');
  if (passed !== total) process.exitCode = 1;
}

main();
