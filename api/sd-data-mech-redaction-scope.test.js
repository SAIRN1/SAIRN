// api/sd-data-mech-redaction-scope.test.js
//
// REQUIREMENT: every SAIRNmechanical field that holds text a MODEL EXTRACTED
//   FROM A PHOTOGRAPH goes through the server-side redaction pass -- not just
//   the one resource the gate happened to name.
//
// Run:  node api/sd-data-mech-redaction-scope.test.js
//
// ── THE DEFECT, RE-DERIVED AT HEAD ────────────────────────────────────────
// api/sd-data.js gated on `if (resource === 'mech_docs')`. A resource NAME, not
// a property of the data. `mech_takeoffs` sits in the same MECH_RECORDS table
// map four lines above it and stores the same shape:
//
//   sairnmechanical.html:1784-1794  saveTakeoff()
//       reads #bp-out.textContent -- the model's answer to
//       "Analyze for HVAC takeoff" over a PHOTOGRAPHED PLAN (:1906) --
//       and pushes {id, date, text} straight to mech_takeoffs.
//
//   sairnmechanical.html:1766-1773  the doc writer, for contrast
//       calls mechRedactLocal(txt) FIRST and carries a redaction block.
//
// So the client redacts one and not the other, and the server -- which is the
// only boundary that counts -- redacted one and not the other for the same
// reason: it was written when only one existed.
//
// ── WHAT IS IN SCOPE, AND WHY THE OTHER TWO ARE NOT ───────────────────────
// The property that earns redaction is PROVENANCE: text a model extracted from
// an image, which contains whatever was in the photograph and which no human
// chose to store. Both scan-derived fields are covered.
//
// mech_quotes.text and mech_checks.payee/memo are DELIBERATELY NOT COVERED, and
// this is a decision rather than an oversight:
//   * mech_quotes.text is generated from form fields the user filled in
//     (sairnmechanical.html:1442). Redacting a customer's name out of the quote
//     the technician is about to send destroys the deliverable.
//   * mech_checks.payee is the payee of a cheque, typed on purpose
//     (:1528-1530). A cheque register with the payee redacted is not a register.
// Over-redaction is not the safe direction here; it is a different way to lose
// the record, and the doc gate's own comment already says a feature nobody uses
// protects nothing.
//
// ── AND THE GATE IS NOW DRIVEN BY A MAP, NOT A NAME ───────────────────────
// Adding a third scan-derived field is a line in that map. The known-bad control
// below reintroduces the name-scoped form and requires it to FAIL.

'use strict';

process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET
  || ['mech', 'redact', 'fixture'].join('-');
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://test.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'test-key';

const assert = require('assert');
const fs = require('fs');
function chr10() { return String.fromCharCode(10); }

const HASH = 'mech-redact-hash';
const APP = 'sairnmechanical';

let pass = 0, fail = 0;
async function test(name, fn) {
  try { await fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('\n' + t); }

function mockRes() {
  const res = { statusCode: null, body: null };
  res.status = function (c) { res.statusCode = c; return res; };
  res.json = function (b) { res.body = b; return res; };
  return res;
}

function postgrestMock(calls) {
  return async function (url, opts) {
    calls.push({ url: String(url), opts: opts || null });
    if (opts && opts.method === 'POST') {
      const sent = JSON.parse(opts.body);
      return { ok: true, status: 200, text: async function () { return opts.body; },
               json: async function () { return [sent]; } };
    }
    return { ok: true, status: 200, json: async function () { return []; } };
  };
}

function loadHandler(fetchImpl) {
  delete require.cache[require.resolve('./_lib/license')];
  require.cache[require.resolve('./_lib/license')] = {
    exports: {
      validateLicenseKey: async function () {
        return { valid: true, active: true, license_hash: HASH,
                 trial_ends_at: null, stripe_subscription_id: null, app_id: APP };
      }
    }
  };
  global.fetch = fetchImpl;
  delete require.cache[require.resolve('./sd-data.js')];
  return require('./sd-data.js');
}

// A string carrying the things the redactor exists to remove. Assembled from
// parts so this file is not itself a finding in any PII scan.
const NAME = ['Dana', 'Whitfield'].join(' ');
// THE PHONE IS THE TEN-DIGIT FORM ON PURPOSE. Driving this suite turned up a
// real gap in api/_lib/mech-redact.js that nobody had hit: it redacts
// `(216) 555-0142` and does NOT redact a bare seven-digit `555-0142`. That is
// a PATTERN question about the redactor -- widening it risks eating the
// equipment serials the note says are kept deliberately -- so it is registered
// and NOT changed here, because this change is about the GATE'S SCOPE. The
// arm at the end of section 1 pins the gap so it cannot be forgotten.
const LOCAL_PHONE = ['555', '0142'].join('-');
const PHONE = '(216) ' + LOCAL_PHONE;
const EMAIL = ['dana', 'example.invalid'].join('@');
const SCAN = 'WORK ORDER\nCustomer: ' + NAME + '\nPhone: ' + PHONE
  + '\nEmail: ' + EMAIL + '\nUnit: RTU-4  Tons: 7.5';

async function write(resource, payload) {
  const calls = [];
  const h = loadHandler(postgrestMock(calls));
  const res = mockRes();
  await h({
    method: 'POST',
    headers: { authorization: 'Bearer KEY-FOR-' + HASH },
    body: { action: 'write', resource: resource, app_id: APP, payload: payload }
  }, res);
  const post = calls.filter(function (c) {
    return c.opts && c.opts.method === 'POST';
  })[0];
  return { res: res, stored: post ? JSON.parse(post.opts.body).data : null };
}

// mech_quotes JOINED THIS LIST on 2026-09-29, correcting my own exclusion of
// it. I had it down as "generated from form fields the user filled in"; re-
// reading the app showed sairnmechanical.html:1416-1417 seeds the conversation
// with a BASE64 IMAGE and :1435 generates the quote from it. Same provenance as
// the other two. My objection -- that redacting destroys the deliverable -- does
// not hold either: :1441 shares fqQuoteTxt FROM MEMORY, never from the row.
const SCANNED = ['mech_docs', 'mech_takeoffs', 'mech_quotes'];

(async () => {

section('1. EVERY SCAN-DERIVED FIELD IS REDACTED SERVER-SIDE');

for (const resource of SCANNED) {
  await test(resource + ': the phone number does not reach the row', async () => {
    const r = await write(resource, { id: 'T-1', date: 'x', text: SCAN });
    assert.strictEqual(r.res.statusCode, 200, JSON.stringify(r.res.body));
    assert.ok(r.stored, 'no write reached the database');
    assert.ok(String(r.stored.text || '').indexOf(PHONE) === -1,
      'the stored text still contains the phone number: '
      + JSON.stringify(String(r.stored.text || '').slice(0, 200)));
  });

  await test(resource + ': the email does not reach the row', async () => {
    const r = await write(resource, { id: 'T-2', date: 'x', text: SCAN });
    assert.ok(String(r.stored.text || '').indexOf(EMAIL) === -1,
      'the stored text still contains the email address');
  });

  await test(resource + ': the row CARRIES its redaction account', async () => {
    // A row that looked redacted with no account of its limits is the false
    // confidence the doc gate's own comment exists to avoid.
    const r = await write(resource, { id: 'T-3', date: 'x', text: SCAN });
    assert.ok(r.stored.redaction, 'no redaction block on the stored row');
    assert.ok('complete' in r.stored.redaction,
      'the redaction block does not say whether it was complete: '
      + JSON.stringify(r.stored.redaction));
    assert.ok(r.stored.redaction.applied_at, 'no applied_at');
  });

  await test(resource + ': the TECHNICAL content survives -- this is not a '
    + 'refusal and not a wipe', async () => {
      // Over-redaction is a different way to lose the record. If the unit tag
      // and the tonnage go, the technician's work is gone and people stop
      // scanning, which protects nothing.
      const r = await write(resource, { id: 'T-4', date: 'x', text: SCAN });
      const t = String(r.stored.text || '');
      assert.ok(t.indexOf('RTU-4') !== -1, 'the unit tag was redacted away: ' + t);
      assert.ok(t.indexOf('7.5') !== -1, 'the tonnage was redacted away: ' + t);
    });
  await test(resource + ': the labelled local number goes AND the equipment '
    + 'label survives -- both halves of the 2026-09-29 defect', async () => {
      // THIS ARM WAS WRITTEN TO DOCUMENT THE BUG AND NOW ASSERTS THE FIX, which
      // is the transition it existed for. It recorded that
      // `Phone: 555-0142  Unit: RTU-4` came back as
      // `Phone: 555-[ADDRESS REDACTED]: RTU-4` -- the number half-surviving AND
      // the equipment label destroyed, two independent faults in one input.
      //
      // Both are closed in api/_lib/mech-redact.js: `Unit`/`Apt`/`Ste`/`Suite`
      // can no longer ANCHOR an address match (they are secondary designators
      // and now only follow a primary street type), and a seven-digit local
      // number is removed WHEN IT IS LABELLED -- never bare, because
      // `2100-0142` is a part number.
      const r = await write(resource, { id: 'T-5', date: 'x',
        text: 'Phone: ' + LOCAL_PHONE + '  Unit: RTU-4' });
      const t = String(r.stored.text || '');
      assert.ok(t.indexOf(LOCAL_PHONE) === -1,
        'the labelled local number still reaches the row: ' + JSON.stringify(t));
      assert.ok(t.indexOf('ADDRESS REDACTED') === -1,
        'the address pattern still fires on an equipment label: '
        + JSON.stringify(t));
      assert.ok(t.indexOf('Unit: RTU-4') !== -1,
        'the equipment label is still collateral: ' + JSON.stringify(t));
      assert.strictEqual(r.stored.redaction.complete, false,
        'complete is now true -- this pass has never been complete and the row '
        + 'must not claim otherwise');
    });
}

section('2. THE FIELDS DELIBERATELY NOT IN SCOPE');

await test('mech_checks.payee is UNTOUCHED -- it is typed, not extracted',
  async () => {
    const r = await write('mech_checks', { id: 'C-1', num: 1, date: 'x',
      payee: NAME, amount: '250.00', memo: 'replaced contactor' });
    assert.strictEqual(r.stored.payee, NAME,
      'the cheque payee was redacted, which makes the register useless: '
      + JSON.stringify(r.stored.payee));
  });

await test('mech_quotes.text IS redacted -- and the deliverable is untouched',
  async () => {
    // FLIPPED from asserting the opposite. The arm that pinned mech_quotes as
    // out of scope was pinning MY WRONG READING, which is the risk a pinning
    // arm carries: it makes a decision durable whether or not it was right.
    const r = await write('mech_quotes', { id: 'Q-1', date: 'x', trade: 'hvac',
      text: 'Customer: ' + NAME + chr10() + 'Quote: RTU replacement, 7.5 tons' });
    assert.ok(String(r.stored.text).indexOf(NAME) === -1,
      'the labelled customer name still reaches the stored quote: '
      + JSON.stringify(r.stored.text));
    assert.ok(String(r.stored.text).indexOf('7.5 tons') !== -1,
      'the priced scope was redacted away: ' + JSON.stringify(r.stored.text));
    assert.ok(r.stored.redaction, 'no redaction account on the stored quote');
  });

section('3. THE GATE IS DRIVEN BY A MAP, NOT A RESOURCE NAME');

await test('KNOWN-BAD CONTROL: the name-scoped form is gone from the source',
  async () => {
    // Reintroducing `if (resource === 'mech_docs')` around the redaction is the
    // exact regression this suite exists for, and it would leave every arm in
    // section 1 for mech_takeoffs red -- but only if somebody runs them. This
    // arm names the shape so the diff is refused rather than the behaviour
    // rediscovered.
    const raw = fs.readFileSync(require.resolve('./sd-data.js'), 'utf8');
    // COMMENTS STRIPPED FIRST, and the first draft of this arm did not: it
    // matched the sentence in the fix's OWN comment quoting the shape it
    // replaced, and reported the defect as still present. Sixth time a
    // text-reading check on this platform has read documentation as code.
    const src = raw.split(chr10()).filter(function (l) {
      return l.trim().indexOf('//') !== 0;
    }).join(chr10());
    const nameScoped = /if\s*\(\s*resource\s*===\s*'mech_docs'\s*\)/;
    assert.ok(!nameScoped.test(src),
      'the redaction gate is scoped to the literal resource name again. That is '
      + 'how mech_takeoffs stored unredacted scan text for as long as it did.');
  });

await test('...and the control can SEE that shape when it is present', () => {
    // Without this, a regex that stopped matching passes the arm above for ever.
    const nameScoped = /if\s*\(\s*resource\s*===\s*'mech_docs'\s*\)/;
    assert.ok(nameScoped.test("      if (resource === 'mech_docs') {"),
      'the pattern no longer matches the shape it is meant to refuse');
  });

await test('the scan-derived field map is DECLARED and covers both resources',
  () => {
    const src = fs.readFileSync(require.resolve('./sd-data.js'), 'utf8');
    // A REAL BOUNDARY, NOT A FIXED WINDOW. This was
    // /const MECH_SCANNED_TEXT[\s\S]{0,400}?\};/ and it stopped matching the
    // moment the map gained a comment longer than 400 characters -- reporting
    // "no declared map found" about a map that was right there. That is the
    // magic-window shape this platform has now named four times, in the test
    // written to police a gate that was itself scoped by a fixed window.
    const start = src.indexOf('const MECH_SCANNED_TEXT');
    assert.ok(start !== -1, 'no declared scan-derived field map found in api/sd-data.js');
    let depth = 0, end = start;
    for (let k = src.indexOf('{', start); k < src.length; k++) {
      if (src[k] === '{') depth++;
      else if (src[k] === '}') { depth--; if (depth === 0) { end = k; break; } }
    }
    const m = [src.slice(start, end + 1)];
    assert.ok(m, 'no declared scan-derived field map found in api/sd-data.js');
    SCANNED.forEach(function (r) {
      assert.ok(m[0].indexOf(r) !== -1, r + ' is not in the map');
    });
    assert.ok(m[0].indexOf('mech_checks') === -1,
      'mech_checks is in the scan-derived map -- its payee and memo come from '
      + 'typed form fields (sairnmechanical.html:1528-1530), with no model and '
      + 'no image anywhere in their provenance');
  });

console.log('\n' + (fail === 0
  ? 'ALL ' + pass + ' MECH REDACTION-SCOPE ASSERTIONS PASS'
  : pass + ' passed, ' + fail + ' FAILED'));
process.exit(fail === 0 ? 0 : 1);

})();
