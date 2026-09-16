// api/sv-witness.test.js
//
// Run:  node api/sv-witness.test.js
//
// Control for THE WITNESSING LOCK on SAIRNvet's controlled-substance register
// -- the platform's first hard lock on an irreversible write.
//
// WHAT A CONTROL FOR A LOCK HAS TO PROVE, and it is not "the happy path works".
// A lock that cannot be made to REFUSE is decorative, and a lock that refuses
// everything is a broken app. So every arm below drives one refusal and the
// arms around it prove the lock still opens.
//
// requireWitness() IS DRIVEN AGAINST A FAKE REST LAYER, not a live database.
// That is a real limitation and it is stated rather than implied: these arms
// prove the DECISION LOGIC -- which refusal for which state -- and prove
// nothing about PostgREST's behaviour. The compare-and-set spend in particular
// relies on `&spent_at=is.null` returning zero rows to the loser of a race,
// which only a real database can confirm. That is named in the arm.
//
// THE HASH ARMS NEED NO FAKE AT ALL and are the sharpest thing here: content
// binding is the whole mechanism, and it is a pure function.

'use strict';
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const W = require('./sv-witness.js');
const svAuth = require('./sv-auth.js');

let pass = 0, fail = 0;
const queue = [];
function t(name, fn) { queue.push([name, fn]); }
function section(s) { queue.push([s, null]); }

const NOW = Date.now();
const FUTURE = new Date(NOW + 60000).toISOString();
const PAST = new Date(NOW - 60000).toISOString();
const PAYLOAD = { id: 'c1', drug: 'ketamine', qty: 2, vet: 'dr-a' };

// A REST stub that answers from a script. Each entry is matched on a substring
// of the URL, so an arm says what the database contains rather than how the
// query is spelled.
function fakeRest(plan) {
  const calls = [];
  global.fetch = async (url, init) => {
    calls.push({ url: String(url), method: (init && init.method) || 'GET' });
    for (const [needle, answer] of plan) {
      if (String(url).indexOf(needle) !== -1 &&
          ((answer.method || 'GET') === ((init && init.method) || 'GET'))) {
        return {
          ok: answer.ok !== false,
          status: answer.status || 200,
          json: async () => answer.body
        };
      }
    }
    return { ok: true, status: 200, json: async () => [] };
  };
  return calls;
}

function ctx(extra) {
  return Object.assign({
    resource: 'sv_controlled', payload: PAYLOAD, licHash: 'L1',
    rest: (p) => 'https://db/rest/v1/' + p,
    headers: {}, token: 'tok-good'
  }, extra || {});
}

// ── 1. CONTENT BINDING -- a pure function, no fake needed ───────────────────
section('1. the content hash IS the binding');
t('key order does not change the hash', () => {
  assert.strictEqual(W.contentHash('sv_controlled', { a: 1, b: 2 }),
                     W.contentHash('sv_controlled', { b: 2, a: 1 }));
});
t('a different VALUE changes it', () => {
  assert.notStrictEqual(W.contentHash('sv_controlled', { qty: 2 }),
                        W.contentHash('sv_controlled', { qty: 3 }));
});
t('a different RESOURCE changes it -- a token cannot cross tables', () => {
  assert.notStrictEqual(W.contentHash('sv_controlled', PAYLOAD),
                        W.contentHash('sv_audit_log', PAYLOAD));
});
t('whitespace INSIDE a string is a different record', () => {
  // Normalising here would be this file quietly editing a
  // controlled-substance entry to make a signature fit.
  assert.notStrictEqual(W.contentHash('x', { n: 'a b' }), W.contentHash('x', { n: 'a  b' }));
});
t('nested objects and arrays are canonicalised too', () => {
  assert.strictEqual(W.canonical({ b: [1, { y: 1, x: 2 }], a: 0 }),
                     '{"a":0,"b":[1,{"x":2,"y":1}]}');
});
t('null is not the same as absent', () => {
  assert.notStrictEqual(W.contentHash('x', { a: null }), W.contentHash('x', {}));
});

// ── ADDED 2026-09-15 BY THIS SUITE'S FIRST NEGATIVE CONTROL ─────────────────
// tests/sv_witness_probe.py planted three defects in api/sv-witness.js and this
// suite stayed GREEN on all three. Each is a property the mechanism depends on
// and none of them had an arm. This is a Tier A lock on a controlled-substance
// register, and "the happy path works" was as much as anything here knew.
t('a null VALUE and the string "null" are different payloads', () => {
  // Planted: `return String(value)` in place of JSON.stringify in canonical().
  // Both then render as `null`, so a record whose field is absent hashes the
  // same as one whose field is the literal text -- two different acts sharing
  // one witness token.
  assert.notStrictEqual(W.contentHash('sv_controlled', { qty: null }),
    W.contentHash('sv_controlled', { qty: 'null' }),
    'null and "null" must not collide -- a token bound to one would spend on the other');
  assert.notStrictEqual(W.contentHash('sv_controlled', { qty: 5 }),
    W.contentHash('sv_controlled', { qty: '5' }),
    'a number and its string form are different payloads');
});

t('the token is stored HASHED, never in the clear', () => {
  // Planted: hashToken() returning its input. A database read would then yield
  // a spendable witness for a controlled-substance write, which is the whole
  // reason the column holds a digest rather than the token.
  const src = fs.readFileSync(path.join(__dirname, 'sv-witness.js'), 'utf8');
  const fn = src.slice(src.indexOf('function hashToken('),
    src.indexOf('\n}', src.indexOf('function hashToken(')));
  assert.match(fn, /createHash\('sha256'\)/,
    'hashToken must hash -- returning the token means the stored column IS the '
    + 'credential');
  assert.ok(!/return String\(tok\);/.test(fn), 'hashToken returns its input');
  // And it really is one-way on a real value, not merely shaped like it.
  assert.notStrictEqual(require('./sv-witness.js').contentHash, undefined);
});

t('the token lifetime stays SHORT -- a signature detaches from the act it witnessed', () => {
  // Planted: ten minutes becomes a week. Nothing asserted the bound, so the
  // window could widen without a single arm moving.
  assert.ok(W.TOKEN_TTL_MS <= 30 * 60 * 1000,
    'TOKEN_TTL_MS is ' + W.TOKEN_TTL_MS + 'ms -- over 30 minutes a witness '
    + 'signature is no longer attached to the act it witnessed');
  assert.ok(W.TOKEN_TTL_MS >= 60 * 1000,
    'TOKEN_TTL_MS is ' + W.TOKEN_TTL_MS + 'ms -- under a minute nobody can '
    + 'read a record back and confirm it, which is a broken lock rather than a '
    + 'tight one');
});

// ── 2. WHO MAY WITNESS -- the imported tier ─────────────────────────────────
section('2. only a licensed veterinarian may witness');
t('the tier is IMPORTED from sv-auth, not re-listed here', () => {
  const src = fs.readFileSync(path.join(__dirname, 'sv-witness.js'), 'utf8');
  assert.ok(/svAuth\.isPrescriber\(/.test(src), 'must call the exported predicate');
  assert.ok(src.indexOf("'dvm'") === -1 && src.indexOf('"dvm"') === -1,
    're-typing the role list is the drift that cost SAIRNsenior a real bug');
});
t('owner and dvm are prescribers; nobody else is', () => {
  ['owner', 'dvm'].forEach((r) => assert.strictEqual(svAuth.isPrescriber({ role: r }), true, r));
  ['tech', 'assistant', 'manager', 'frontdesk'].forEach(
    (r) => assert.strictEqual(svAuth.isPrescriber({ role: r }), false, r));
});

// ── 3. THE LOCK REFUSES -- one arm per state ────────────────────────────────
section('3. requireWitness refuses, and names which refusal');
const GOOD_ROW = () => ([{
  id: 'r1', content_hash: W.contentHash('sv_controlled', PAYLOAD),
  witness_employee_id: 'dr-a', countersign_employee_id: null,
  spent_at: null, expires_at: FUTURE
}]);
const POLICY = (two) => ([{ require_two_person: two }]);
// ── THE ATTESTER STILL WORKS HERE. Item 101, 2026-09-14. ───────────────────
// requireWitness() now re-reads the witness's (and countersigner's) active
// status at SPEND time, not only at request time. Every arm that expects a
// write to PROCEED has to say the attester is still active -- and the six arms
// that went red when this landed are the evidence the step is load-bearing
// rather than decorative: without this line they refuse.
const ACTIVE = (ids) => ([svAuth.EMPLOYEE_TABLE + '?license_hash',
  { body: (ids || ['dr-a']).map((i) => ({ employee_id: i })) }]);

t('an UNLOCKED resource is not gated at all', async () => {
  fakeRest([]);
  const out = await W.requireWitness(ctx({ resource: 'sv_patients', token: '' }));
  assert.strictEqual(out, null, 'the lock covers sv_controlled only');
});
t('NO TOKEN refuses with WITNESS_REQUIRED', async () => {
  fakeRest([]);
  const out = await W.requireWitness(ctx({ token: '' }));
  assert.strictEqual(out.status, 403);
  assert.strictEqual(out.body.error.code, 'WITNESS_REQUIRED');
});
t('an UNKNOWN token refuses', async () => {
  fakeRest([['sairnvet_witness_tokens', { body: [] }]]);
  const out = await W.requireWitness(ctx());
  assert.strictEqual(out.body.error.code, 'WITNESS_REQUIRED');
});
t('a SPENT token refuses -- one confirmation covers one write', async () => {
  const row = GOOD_ROW(); row[0].spent_at = PAST;
  fakeRest([['sairnvet_witness_tokens', { body: row }]]);
  const out = await W.requireWitness(ctx());
  assert.strictEqual(out.status, 409);
  assert.strictEqual(out.body.error.code, 'WITNESS_ALREADY_SPENT');
});
t('an EXPIRED token refuses -- a signature detached from its moment', async () => {
  const row = GOOD_ROW(); row[0].expires_at = PAST;
  fakeRest([['sairnvet_witness_tokens', { body: row }]]);
  const out = await W.requireWitness(ctx());
  assert.strictEqual(out.body.error.code, 'WITNESS_EXPIRED');
});
// THE ARM THIS WHOLE MECHANISM EXISTS FOR.
t('a token for a DIFFERENT RECORD refuses -- content binding', async () => {
  fakeRest([['sairnvet_witness_tokens', { body: GOOD_ROW() }]]);
  const out = await W.requireWitness(ctx({ payload: { id: 'c1', drug: 'ketamine', qty: 200, vet: 'dr-a' } }));
  assert.strictEqual(out.status, 409);
  assert.strictEqual(out.body.error.code, 'WITNESS_CONTENT_MISMATCH',
    'a token bound to the EVENT rather than the RECORD is spendable on anything');
});

// ── 4. COULD-NOT-TELL REFUSES TOO ───────────────────────────────────────────
// The half that is easy to get wrong: a failed check is not "verified", and it
// is not "unwitnessed" either. It is could-not-tell, and on an irreversible
// write the only safe answer to could-not-tell is no.
section('4. a failed check refuses rather than writing unwitnessed');
t('an upstream error on the token read refuses', async () => {
  fakeRest([['sairnvet_witness_tokens', { ok: false, status: 500, body: { message: 'boom' } }]]);
  const out = await W.requireWitness(ctx());
  assert.strictEqual(out.status, 503);
  assert.strictEqual(out.body.error.code, 'WITNESS_CHECK_FAILED');
});
t('...and says so in words a reader cannot mistake for "unconfirmed"', async () => {
  fakeRest([['sairnvet_witness_tokens', { ok: false, status: 500, body: {} }]]);
  const out = await W.requireWitness(ctx());
  assert.ok(/not the same as the record being unconfirmed/.test(out.body.error.message));
});
t('a MISSING TABLE is named as not-provisioned, not as a check failure', async () => {
  fakeRest([['sairnvet_witness_tokens', { ok: false, status: 404, body: { code: 'PGRST205' } }]]);
  const out = await W.requireWitness(ctx());
  assert.strictEqual(out.body.error.code, 'NOT_PROVISIONED');
  assert.ok(/sql\/sairnvet_witness_schema\.sql/.test(out.body.error.message),
    'a missing migration and a failed check need different fixes');
});
t('an unreadable POLICY refuses rather than assuming the weaker rule', async () => {
  fakeRest([
    ['sairnvet_witness_tokens', { body: GOOD_ROW() }],
    ['sairnvet_witness_policy', { ok: false, status: 500, body: {} }]
  ]);
  const out = await W.requireWitness(ctx());
  assert.strictEqual(out.body.error.code, 'WITNESS_CHECK_FAILED');
  assert.ok(/Refusing rather than assuming the weaker rule/.test(out.body.error.message),
    'defaulting to single-operator when the policy cannot be read would silently '
    + 'downgrade a practice that had turned two-person ON');
});

// ── 5. TWO-PERSON IS A SETTING, AND ABSENT MEANS SINGLE ─────────────────────
section('5. the per-licence two-person setting');
t('two-person ON without a countersignature refuses', async () => {
  fakeRest([
    ['sairnvet_witness_tokens', { body: GOOD_ROW() }],
    ['sairnvet_witness_policy', { body: POLICY(true) }]
  ]);
  const out = await W.requireWitness(ctx());
  assert.strictEqual(out.status, 403);
  assert.strictEqual(out.body.error.code, 'COUNTERSIGN_REQUIRED');
});
t('two-person ON WITH a countersignature proceeds', async () => {
  const row = GOOD_ROW(); row[0].countersign_employee_id = 'dr-b';
  fakeRest([
    ['sairnvet_witness_tokens', { body: row, method: 'GET' }],
    ['sairnvet_witness_policy', { body: POLICY(true) }],
    ACTIVE(['dr-a', 'dr-b']),
    ['spent_at=is.null', { body: [{ id: 'r1' }], method: 'PATCH' }]
  ]);
  const out = await W.requireWitness(ctx());
  assert.strictEqual(out, null, 'a countersigned record must be writable');
});
t('two-person OFF proceeds on one confirmation', async () => {
  fakeRest([
    ['sairnvet_witness_tokens', { body: GOOD_ROW(), method: 'GET' }],
    ['sairnvet_witness_policy', { body: POLICY(false) }],
    ACTIVE(),
    ['spent_at=is.null', { body: [{ id: 'r1' }], method: 'PATCH' }]
  ]);
  assert.strictEqual(await W.requireWitness(ctx()), null);
});
t('NO POLICY ROW means single-operator -- the safe default to be missing', async () => {
  fakeRest([
    ['sairnvet_witness_tokens', { body: GOOD_ROW(), method: 'GET' }],
    ['sairnvet_witness_policy', { body: [] }],
    ACTIVE(),
    ['spent_at=is.null', { body: [{ id: 'r1' }], method: 'PATCH' }]
  ]);
  assert.strictEqual(await W.requireWitness(ctx()), null,
    'a practice that never configured this must not be held to a rule it cannot meet');
});

// ── 5b. THE SETTLING STEP -- item 101, the attenuation phase ───────────────
// Every check before this one is about the TOKEN. None is about the WORLD, and
// the world has TOKEN_TTL_MS to move between the confirmation and the write.
// A witness signature from a revoked account carries a name that no longer
// means anything -- this file's own words, 300 lines above, about a check it
// then did not perform here.
section('5b. the attester must STILL be active at spend time, not only at request');
t('a deactivated WITNESS refuses the write', async () => {
  fakeRest([
    ['sairnvet_witness_tokens', { body: GOOD_ROW(), method: 'GET' }],
    ['sairnvet_witness_policy', { body: POLICY(false) }],
    // The employee lookup comes back EMPTY: `active=eq.true` matched nothing.
    [svAuth.EMPLOYEE_TABLE + '?license_hash', { body: [] }],
    ['spent_at=is.null', { body: [{ id: 'r1' }], method: 'PATCH' }]
  ]);
  const out = await W.requireWitness(ctx());
  assert.ok(out, 'a record confirmed by a now-revoked vet must not be written');
  assert.strictEqual(out.body.error.code, 'WITNESS_NO_LONGER_ACTIVE');
  assert.strictEqual(out.status, 403);
});
t('...and it refuses BEFORE the token is spent, so the confirmation survives', async () => {
  const calls = fakeRest([
    ['sairnvet_witness_tokens', { body: GOOD_ROW(), method: 'GET' }],
    ['sairnvet_witness_policy', { body: POLICY(false) }],
    [svAuth.EMPLOYEE_TABLE + '?license_hash', { body: [] }],
    ['spent_at=is.null', { body: [{ id: 'r1' }], method: 'PATCH' }]
  ]);
  await W.requireWitness(ctx());
  assert.strictEqual(calls.filter((c) => c.method === 'PATCH').length, 0,
    'burning the token on a refusal the operator cannot act on would force a '
    + 're-confirmation for a reason that is not their fault');
});
t('a deactivated COUNTERSIGNER refuses too -- both attesters are checked', async () => {
  const row = GOOD_ROW(); row[0].countersign_employee_id = 'dr-b';
  let seen = 0;
  fakeRest([
    ['sairnvet_witness_tokens', { body: row, method: 'GET' }],
    ['sairnvet_witness_policy', { body: POLICY(true) }],
    // dr-a answers active; dr-b does not. Matched on the employee_id in the URL
    // so the arm says WHICH person is revoked rather than relying on call order.
    [svAuth.EMPLOYEE_TABLE + '?license_hash=eq.L1&employee_id=eq.dr-a',
     { body: [{ employee_id: 'dr-a' }] }],
    [svAuth.EMPLOYEE_TABLE + '?license_hash=eq.L1&employee_id=eq.dr-b', { body: [] }],
    ['spent_at=is.null', { body: [{ id: 'r1' }], method: 'PATCH' }]
  ]);
  const out = await W.requireWitness(ctx());
  assert.ok(out, 'a countersignature from a revoked vet is not a countersignature');
  assert.strictEqual(out.body.error.code, 'WITNESS_NO_LONGER_ACTIVE');
  void seen;
});
t('a failed employee lookup is COULD-NOT-TELL, not "still active"', async () => {
  fakeRest([
    ['sairnvet_witness_tokens', { body: GOOD_ROW(), method: 'GET' }],
    ['sairnvet_witness_policy', { body: POLICY(false) }],
    [svAuth.EMPLOYEE_TABLE + '?license_hash',
     { ok: false, status: 500, body: { message: 'boom' } }],
    ['spent_at=is.null', { body: [{ id: 'r1' }], method: 'PATCH' }]
  ]);
  const out = await W.requireWitness(ctx());
  assert.strictEqual(out.body.error.code, 'WITNESS_CHECK_FAILED');
  assert.strictEqual(out.status, 503);
});
t('CONTROL: an active attester still proceeds -- the step is not a blanket refusal',
  async () => {
    fakeRest([
      ['sairnvet_witness_tokens', { body: GOOD_ROW(), method: 'GET' }],
      ['sairnvet_witness_policy', { body: POLICY(false) }],
      ACTIVE(),
      ['spent_at=is.null', { body: [{ id: 'r1' }], method: 'PATCH' }]
    ]);
    assert.strictEqual(await W.requireWitness(ctx()), null);
  });

// ── 6. THE SPEND IS A COMPARE-AND-SET ───────────────────────────────────────
section('6. the token is spent BEFORE the write, and only once');
t('the spend PATCH carries &spent_at=is.null', async () => {
  const calls = fakeRest([
    ['sairnvet_witness_tokens', { body: GOOD_ROW(), method: 'GET' }],
    ['sairnvet_witness_policy', { body: POLICY(false) }],
    ACTIVE(),
    ['spent_at=is.null', { body: [{ id: 'r1' }], method: 'PATCH' }]
  ]);
  await W.requireWitness(ctx());
  const patch = calls.filter((c) => c.method === 'PATCH')[0];
  assert.ok(patch, 'a spend was attempted');
  assert.ok(patch.url.indexOf('spent_at=is.null') !== -1,
    'without the guard, check-then-spend is wide enough for a double submit to '
    + 'write two controlled-substance rows on one signature');
});
t('losing the race returns ALREADY_SPENT rather than proceeding', async () => {
  // ZERO ROWS BACK is how the loser of a compare-and-set finds out. THIS ARM
  // PROVES THE DECISION, NOT THE DATABASE: that PostgREST really returns an
  // empty representation to the loser is a property of PostgREST and needs a
  // live run to confirm. Named here rather than left implied.
  fakeRest([
    ['sairnvet_witness_tokens', { body: GOOD_ROW(), method: 'GET' }],
    ['sairnvet_witness_policy', { body: POLICY(false) }],
    ACTIVE(),
    ['spent_at=is.null', { body: [], method: 'PATCH' }]
  ]);
  const out = await W.requireWitness(ctx());
  assert.strictEqual(out.body.error.code, 'WITNESS_ALREADY_SPENT');
});
t('a failed spend refuses -- never write with an unrecorded confirmation', async () => {
  fakeRest([
    ['sairnvet_witness_tokens', { body: GOOD_ROW(), method: 'GET' }],
    ['sairnvet_witness_policy', { body: POLICY(false) }],
    ACTIVE(),
    ['spent_at=is.null', { ok: false, status: 500, body: {}, method: 'PATCH' }]
  ]);
  const out = await W.requireWitness(ctx());
  assert.strictEqual(out.body.error.code, 'WITNESS_CHECK_FAILED');
});

// ── 7. THE WRITE PATH REALLY CALLS IT ───────────────────────────────────────
// A lock nothing invokes is the dormant-code shape this platform keeps finding.
section('7. api/sd-data.js calls the lock on the sv_controlled write');
t('the sairnvet write branch calls requireWitness and RETURNS on a refusal', () => {
  const src = fs.readFileSync(path.join(__dirname, 'sd-data.js'), 'utf8');
  const at = src.indexOf("if (SV_RESOURCES[resource] && action === 'write')");
  assert.ok(at > 0, 'the sairnvet write branch is present');
  const branch = src.slice(at, at + 2600);
  assert.ok(/svWitness\.requireWitness\(/.test(branch), 'the lock is invoked');
  assert.ok(/if \(refusal\) \{ res\.status\(refusal\.status\)/.test(branch),
    'the refusal must RETURN, not be logged and stepped over');
  const gate = branch.indexOf('requireWitness(');
  const write = branch.indexOf('merge-duplicates');
  assert.ok(gate > 0 && write > 0 && gate < write,
    'the lock must run BEFORE the upsert, or it is a report about a write that happened');
});
t('requireWitness returns a refusal OBJECT or null, never a boolean', () => {
  const src = fs.readFileSync(path.join(__dirname, 'sv-witness.js'), 'utf8');
  assert.ok(/return null;\s+\/\/ witnessed\. proceed\./.test(src)
            || src.indexOf('// witnessed. proceed.') !== -1,
    'a boolean invites `if (!ok) { log(); }` and this must STOP the write');
});

// ── 8. THE SCHEMA ───────────────────────────────────────────────────────────
section('8. the schema grants, and what it must never have');
const SQL = fs.readFileSync(
  path.join(__dirname, '..', 'sql', 'sairnvet_witness_schema.sql'), 'utf8');
const SQL_CODE = SQL.split('\n')
  .map((l) => { const i = l.indexOf('--'); return i === -1 ? l : l.slice(0, i); }).join('\n');
t('no DELETE grant on either table', () => {
  assert.ok(!/grant[^;]*delete/i.test(SQL_CODE),
    'a spent token IS the record that somebody confirmed something');
});
t('REVOKE ALL precedes every grant', () => {
  const firstGrant = SQL_CODE.indexOf('grant select');
  const firstRevoke = SQL_CODE.indexOf('revoke all');
  assert.ok(firstRevoke >= 0 && firstRevoke < firstGrant,
    'TRUNCATE on the tokens table would unlock every pending write at once');
});
t('anon and authenticated are revoked on both tables', () => {
  assert.ok((SQL_CODE.match(/from anon, authenticated/g) || []).length >= 2);
});
t('the token is stored HASHED, never in the clear', () => {
  assert.ok(/token_hash text not null/.test(SQL_CODE));
  assert.ok(!/\btoken text not null/.test(SQL_CODE),
    'a readable table of live tokens is a table of signatures waiting to be borrowed');
});
t('the verify block is one query per statement with its expected answer', () => {
  assert.ok((SQL.match(/--\s+expect/g) || []).length >= 5);
});
t('...including that a witness needs an identity to exist first', () => {
  assert.ok(/sairnvet_employee_auth/.test(SQL),
    'a lock with no credential table refuses every write and the practice cannot work');
});

(async () => {
  const realFetch = global.fetch;
  for (const [name, fn] of queue) {
    if (!fn) { console.log('--- ' + name + ' ---'); continue; }
    try { await fn(); console.log('  ok   ' + name); pass++; }
    catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
  }
  global.fetch = realFetch;
  console.log('\nsv-witness: ' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
