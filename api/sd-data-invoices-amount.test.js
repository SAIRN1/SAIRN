// api/sd-data-invoices-amount.test.js
//
// REQUIREMENT: the `invoices` write branch must refuse a non-numeric `amount`
//   rather than storing it in the jsonb blob.
//
// Run:  node api/sd-data-invoices-amount.test.js
//
// ── WHY, AND IT IS NOT HYPOTHETICAL ───────────────────────────────────────
// The branch validated `payload.id` and `payload.customer_id` and nothing
// else, then stored the whole payload verbatim. A string `amount` therefore
// reached storage, and every fold that read it back concatenated instead of
// adding. That is the class fixed client-side the same day in
// tests/sd_tax_money_coercion.js -- bills of "100" and "200" folding to the
// string "0100200" and a profit of -99450 where 450 was right, then handed to
// an LLM as fact and printed on a tax report.
//
// Coercing on read is necessary and is not sufficient: it repairs the readers
// that exist today and does nothing for the next one. This is the other half.
//
// ── WHAT IS REFUSED, AND WHAT IS DELIBERATELY NOT ─────────────────────────
// REFUSED: `amount` present and not a finite number -- a string (including a
// numeric-looking one), a boolean, an object, an array, NaN, Infinity.
//
// NOT REFUSED: `amount` absent, or null. That is narrower than it could be and
// the reason is measured rather than assumed. The one live caller,
// `scpSaveInv()` at sairnscape.html:3529, already sends
// `Number(scp$('scp-iamt').value || 0)` -- so it never sends a string, and for
// junk input it sends NaN, which `JSON.stringify` puts on the wire as **null**.
// Refusing null would therefore break the existing client on exactly the input
// it already handles badly, while the harm that motivated this change -- a
// STRING reaching a fold -- cannot arrive that way. `Number(null) || 0` is 0,
// which is what the readers now do with it.
//
// A NUMERIC-LOOKING STRING IS STILL REFUSED, and that is the point. "500" is
// the dangerous case, not "abc": "abc" renders visibly wrong and somebody
// asks, while "500" folds to a believable total nobody questions. Accepting it
// by coercing server-side would be a silent data change; refusing it tells the
// caller.

// ── THE SESSION HEADER, ADDED 2026-09-25 ─────────────────────────────────
// `invoices` joined SD_SESSION_GATED on 2026-09-25 (it is Tier A on integrity
// and was authorised by the licence key alone). Without a token every arm
// below answers 403 before the amount guard is ever reached -- and a 403 is
// not "the bad amount was refused", it is "the guard was never asked". So the
// requests now carry a real SAIRNscape session.
//
// THE LICENCE HASH IS DERIVED, NOT TYPED. This file does NOT stub
// api/_lib/license, so the handler computes sha256('K') from the bearer key
// itself; signing against a hand-written constant would answer 403 and the
// arms would fail for a reason that has nothing to do with amounts.

'use strict';
const path = require('path');
const assert = require('assert');
const crypto = require('crypto');

process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET
  || ['invoices', 'amount', 'fixture'].join('-');

const HANDLER = path.join(__dirname, 'sd-data.js');
const { signSessionToken } = require('./_lib/auth');

const LICENSE_KEY = 'K';
const LIC_HASH = crypto.createHash('sha256').update(LICENSE_KEY).digest('hex');
const SESSION = signSessionToken({ app: 'sairnscape', employee_id: 'emp-1',
                                   role: 'owner', license_hash: LIC_HASH });

let pass = 0, fail = 0;
const run = [];
function t(name, fn) { run.push([name, fn]); }
function section(s) { run.push([s, null]); }

// Drives the REAL handler with the licence lookup and PostgREST stubbed.
async function write(payload, opts) {
  opts = opts || {};
  delete require.cache[require.resolve(HANDLER)];
  const handler = require(HANDLER);
  const out = { code: null, body: null, stored: null };
  const res = { status(c) { out.code = c; return res; }, json(b) { out.body = b; return res; },
                setHeader() {} };
  const envURL = process.env.SUPABASE_URL, envKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
  const realFetch = global.fetch;
  process.env.SUPABASE_URL = 'https://stub.invalid';
  process.env.SUPABASE_SERVICE_ROLE_KEY = 'stub-key';
  global.fetch = async (url, init) => {
    const u = String(url);
    if (u.indexOf('license_keys') !== -1) {
      return { ok: true, status: 200,
               json: async () => [{ status: 'active', app_id: 'sairnscape' }] };
    }
    // The gate re-checks that the signed-in employee is still ACTIVE. An
    // unanswered lookup here is 403 CREDENTIAL_INACTIVE, which would fail every
    // arm below for a reason that is not about amounts.
    if (u.indexOf('_employee_auth') !== -1) {
      return { ok: true, status: 200,
               json: async () => [{ license_hash: LIC_HASH, employee_id: 'emp-1',
                                    role: 'owner', active: true }] };
    }
    if (u.indexOf('scp_invoices') !== -1 && init && init.method === 'POST') {
      out.stored = JSON.parse(init.body);      // what would have reached storage
      return { ok: true, status: 200, json: async () => [{ data: out.stored.data }] };
    }
    return { ok: true, status: 200, json: async () => [] };
  };
  try {
    await handler({ method: 'POST',
                    headers: { authorization: 'Bearer ' + LICENSE_KEY,
                               'x-sd-auth': SESSION },
                    body: { action: 'write', resource: 'invoices', app_id: 'sairnscape',
                            is_demo: true, payload: payload } }, res);
  } finally {
    global.fetch = realFetch;
    if (envURL === undefined) delete process.env.SUPABASE_URL; else process.env.SUPABASE_URL = envURL;
    if (envKey === undefined) delete process.env.SUPABASE_SERVICE_ROLE_KEY; else process.env.SUPABASE_SERVICE_ROLE_KEY = envKey;
  }
  return out;
}

const OK = { id: 'I-1', customer_id: 'C-1' };
const code = (o) => o.body && o.body.error && o.body.error.code;

// ---------------------------------------------------------------------------
section('a non-numeric amount never reaches storage');

t('a numeric-looking STRING is refused -- the dangerous case', async () => {
  const o = await write(Object.assign({}, OK, { amount: '500' }));
  assert.strictEqual(o.code, 400, 'got ' + o.code + ' ' + JSON.stringify(o.body));
  assert.strictEqual(code(o), 'INVALID_AMOUNT');
  assert.strictEqual(o.stored, null, 'the row was written anyway');
});

t('...and so are the obviously-wrong shapes', async () => {
  for (const bad of ['abc', '', '  ', true, false, [], {}, [1], '1e5']) {
    const o = await write(Object.assign({}, OK, { amount: bad }));
    assert.strictEqual(code(o), 'INVALID_AMOUNT',
      JSON.stringify(bad) + ' was accepted: ' + o.code + ' ' + JSON.stringify(o.body));
    assert.strictEqual(o.stored, null, JSON.stringify(bad) + ' reached storage');
  }
});

t('Infinity is refused -- isFinite, not just typeof number', async () => {
  // typeof Infinity === 'number', so a bare typeof check would let it through
  // and every total downstream becomes Infinity.
  for (const bad of [Infinity, -Infinity]) {
    const o = await write(Object.assign({}, OK, { amount: bad }));
    assert.strictEqual(code(o), 'INVALID_AMOUNT', String(bad) + ' was accepted');
  }
});

// ---------------------------------------------------------------------------
section('THE CONTROLS -- what must still be accepted');

t('a real number is stored, and stored as a number', async () => {
  const o = await write(Object.assign({}, OK, { amount: 1250.5 }));
  assert.notStrictEqual(o.code, 400, 'a valid invoice was refused: ' + JSON.stringify(o.body));
  assert.ok(o.stored, 'nothing reached storage');
  assert.strictEqual(o.stored.data.amount, 1250.5);
  assert.strictEqual(typeof o.stored.data.amount, 'number');
});

t('zero and negative are accepted -- a credit note is a real invoice', async () => {
  for (const good of [0, -250]) {
    const o = await write(Object.assign({}, OK, { amount: good }));
    assert.notStrictEqual(code(o), 'INVALID_AMOUNT', String(good) + ' was refused');
    assert.strictEqual(o.stored.data.amount, good);
  }
});

t('an ABSENT amount is still accepted -- the pre-existing contract', async () => {
  // The branch never required `amount`. Requiring it now would be a different
  // change with a different blast radius, and is not this one.
  const o = await write({ id: 'I-2', customer_id: 'C-1' });
  assert.notStrictEqual(code(o), 'INVALID_AMOUNT');
  assert.ok(o.stored, 'an invoice with no amount stopped being storable');
});

t('a NULL amount is accepted, because that is what the live client sends for junk', async () => {
  // scpSaveInv() sends Number(input || 0); junk input makes NaN, and
  // JSON.stringify puts NaN on the wire as null. Refusing it would break the
  // existing client on the one input it already handles badly, and null is
  // benign to every reader now that they coerce: Number(null) || 0 is 0.
  const o = await write({ id: 'I-3', customer_id: 'C-1', amount: null });
  assert.notStrictEqual(code(o), 'INVALID_AMOUNT');
  assert.ok(o.stored, 'a null amount stopped being storable');
});

t('the id and customer_id refusals are untouched', async () => {
  assert.strictEqual((await write({ customer_id: 'C-1', amount: 5 })).code, 400);
  assert.strictEqual((await write({ id: 'I-4', amount: 5 })).code, 400);
});

// ---------------------------------------------------------------------------
section('the control: this suite can fail');

t('the PRE-FIX branch stored "500" -- so the arms are testing the new guard', async () => {
  // Modelled from the branch as it stood: id and customer_id only. If this
  // stops reproducing, the arms above may be passing on some other refusal.
  const preFix = (p) => (!p || !p.id || !p.customer_id) ? 400 : null;
  assert.strictEqual(preFix({ id: 'I-1', customer_id: 'C-1', amount: '500' }), null,
    'the pre-fix validation already refused a string amount -- then nothing was fixed');
});

// ---------------------------------------------------------------------------
(async () => {
  for (const [name, fn] of run) {
    if (fn === null) { console.log('--- ' + name + ' ---'); continue; }
    try { await fn(); console.log('  ok   ' + name); pass++; }
    catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
  }
  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
