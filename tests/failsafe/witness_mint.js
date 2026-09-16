// tests/failsafe/witness_mint.js
//
// Run:  node tests/failsafe/witness_mint.js
//
// THE MINT HALF OF THE WITNESSING LOCK -- the half NINETY-SIX arms never
// entered.
//
// ── WHY THIS FILE EXISTS ────────────────────────────────────────────────────
// `docs/2026-09-16-item83-independent-review.md`, an independent adversarial
// review of my own item-83 suites by a reviewer with no knowledge of the work,
// built a 32-mutation sabotage driver and measured it: 25 caught, SEVEN
// SURVIVED. Four of the seven sit inside `request` and `set_policy` -- the
// actions that MINT a witness token and set the two-person policy -- and
// `grep` across the whole repository found nothing anywhere driving either.
//
//   api/sv-witness.js:242  if (!svAuth.isPrescriber(caller))  -> if (false)
//   api/sv-witness.js:267  token_hash: hashToken(tok)         -> String(tok)
//   api/sv-witness.js:268  contentHash(resource, body.payload)-> ..., {})
//   api/sv-witness.js:214  set_policy owner gate              -> if (!caller)
//
// THE LOCK IS CORRECT TODAY. Every line above is right in the shipped file.
// What was missing is anything that would notice if it stopped being right --
// on a DEA-relevant controlled-substance register where a correction is a
// SECOND row and the wrong one stands forever. What ships undetected, in the
// reviewer's words and confirmed here:
//
//   * a RECEPTIONIST mints a witness token and the row records
//     witness_role: 'receptionist';
//   * the tokens table holds PLAINTEXT, SPENDABLE SIGNATURES -- and the lock
//     breaks outright, because mint would store plaintext while requireWitness
//     looks up a sha256;
//   * the token is BOUND TO NOTHING at mint time, which is exactly the hole
//     api/sv-witness.js:42-45 names in its own header;
//   * ANY SIGNED-IN EMPLOYEE turns require_two_person off, after which the
//     lock stops asking for a countersignature at all.
//
// ── WHY THE EXISTING ARMS LOOK LIKE THEY COVER THIS AND DO NOT ──────────────
// This is the part worth carrying away, because all three near-misses are the
// same shape -- an arm that reads the RIGHT SUBJECT in the WRONG PLACE:
//
//   api/sv-witness.test.js:146  tests `svAuth.isPrescriber` AS A PURE FUNCTION
//                               and asserts the tier is imported. It never
//                               asserts the HANDLER CALLS IT.
//   api/sv-witness.test.js:120  reads the BODY of hashToken().
//   api/sv-witness.test.js:447  reads sql/sairnvet_witness_schema.sql.
//                               Neither reads the CALL SITE.
//   every content-binding arm    FABRICATES the token row itself with a correct
//   in every suite               content_hash -- so the binding is proven on the
//                               CHECK side and never on the MINT side.
//
// A helper that is correct and a call site that does not call it produce
// identical green.
//
// ── EVERY ARM IS KEYED TO A MUTATION THAT SURVIVED ──────────────────────────
//   M1  isPrescriber gate      -> if (false)          §2
//   M2  token_hash plaintext   -> String(tok)         §3
//   M3  content bound to {}    -> contentHash(r, {})  §4
//   M4  set_policy owner gate  -> if (!caller)        §5
//   M5  activeCaller filter    -> drop active=eq.true §6  (source-anchored)
//
// ── WHAT THIS CANNOT SEE, STATED RATHER THAN IMPLIED ────────────────────────
// The HTTP session, licence and REST layers are STUBBED, exactly as the three
// sibling suites declare. These arms prove the DECISION LOGIC and the SHAPE OF
// THE ROW THE HANDLER POSTS. They prove nothing about PostgREST, about
// `_lib/auth`'s real signature verification, or about the live database.
//
// §6 is a SOURCE ANCHOR and is weaker than a behavioural arm on purpose. The
// countersign suite's own §55-57 discloses that `active=eq.true` doing what it
// says is a property of the database -- a stub answering an empty list proves
// the lock refuses an empty answer, not that the filter is spelled correctly.
// The reviewer's second finding is that the remedy already existed in that same
// file 430 lines later, source-anchoring SAME_PERSON "because deletion is
// invisible everywhere else", and was simply not applied to this guard. It is
// applied here.

'use strict';
const assert = require('assert');
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

// ── THE STUBS GO IN BEFORE THE LOCK IS REQUIRED ─────────────────────────────
// api/sv-witness.js DESTRUCTURES its dependencies at require time, so replacing
// the exports afterwards would change nothing and every arm below would be
// driving the real signature verifier while claiming to drive a stub. Same
// reasoning, same order, as witness_countersign.js.
const API = path.join(__dirname, '..', '..', 'api');
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://db.example';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'svc-key';
process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET || 'x'.repeat(48);

let SESSION = null;
let LICENSE = { valid: true, active: true, license_hash: 'L1' };

const authPath = require.resolve(path.join(API, '_lib', 'auth.js'));
require(authPath);
require.cache[authPath].exports = Object.assign({}, require.cache[authPath].exports, {
  tokenFromRequest: () => (SESSION ? 'stub-session-token' : null),
  verifySessionToken: () => SESSION
});

const licPath = require.resolve(path.join(API, '_lib', 'license.js'));
require(licPath);
require.cache[licPath].exports = Object.assign({}, require.cache[licPath].exports, {
  validateLicenseKey: async () => LICENSE
});

const W = require(path.join(API, 'sv-witness.js'));
const svAuth = require(path.join(API, 'sv-auth.js'));
const EMP = svAuth.EMPLOYEE_TABLE;

let pass = 0, fail = 0;
const queue = [];
function t(name, fn) { queue.push([name, fn]); }
function section(s) { queue.push([s, null]); }

const PAYLOAD = { id: 'c1', drug: 'ketamine', qty: 2, vet: 'dr-a' };
const OTHER_PAYLOAD = { id: 'c1', drug: 'ketamine', qty: 200, vet: 'dr-a' };

function fakeRest(plan) {
  const calls = [];
  global.fetch = async (url, init) => {
    const method = (init && init.method) || 'GET';
    calls.push({ url: String(url), method: method, body: init && init.body });
    for (const [needle, answer] of plan) {
      if (String(url).indexOf(needle) !== -1 && (answer.method || 'GET') === method) {
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

function caller(id, role) {
  return [EMP + '?license_hash=eq.L1&employee_id=eq.' + id,
          { body: [{ employee_id: id, role: role }] }];
}
const MINT_OK = ['sairnvet_witness_tokens', { method: 'POST', body: [{ id: 'r1' }] }];
const POLICY_READ = ['sairnvet_witness_policy?license_hash',
                     { method: 'GET', body: [{ require_two_person: false }] }];
const POLICY_WRITE = ['sairnvet_witness_policy?on_conflict',
                      { method: 'POST', body: [{ require_two_person: true }] }];

function mkRes() {
  const r = { code: 0, body: null, sent: 0 };
  r.status = (c) => { r.code = c; return r; };
  r.json = (b) => { r.body = b; r.sent++; return r; };
  return r;
}
function mkReq(body) {
  return { method: 'POST', headers: { authorization: 'Bearer LK-TEST' }, body: body };
}

// Mint as `who`, holding `role`, over `payload`.
async function mint(who, role, payload, extraPlan) {
  SESSION = who ? { employee_id: who, role: role, app: 'sairnvet' } : null;
  const plan = (extraPlan || []).concat([caller(who, role), MINT_OK, POLICY_READ]);
  const calls = fakeRest(plan);
  const res = mkRes();
  await W(mkReq({ action: 'request', resource: 'sv_controlled',
                 payload: payload === undefined ? PAYLOAD : payload }), res);
  return { res: res, calls: calls };
}

async function setPolicy(who, role, value) {
  SESSION = who ? { employee_id: who, role: role, app: 'sairnvet' } : null;
  const calls = fakeRest([caller(who, role), POLICY_WRITE]);
  const res = mkRes();
  await W(mkReq({ action: 'set_policy', require_two_person: value }), res);
  return { res: res, calls: calls };
}

// The row the handler POSTed to the tokens table -- the thing every arm in
// §3 and §4 is actually about. Reading the REQUEST BODY is the whole point:
// a fabricated row proves the checker, not the minter.
function mintedRow(calls) {
  const post = calls.filter((c) => c.method === 'POST'
                            && c.url.indexOf('sairnvet_witness_tokens') !== -1);
  assert.strictEqual(post.length, 1,
    'expected exactly one POST to the tokens table, got ' + post.length);
  return JSON.parse(post[0].body);
}

// ── 1. THE CONTROL: A PRESCRIBER CAN MINT ───────────────────────────────────
// FIRST, and it is not a formality. Every refusal arm below is satisfied by a
// handler that refuses everybody, and that failure would look exactly like a
// working lock.
section('1. CONTROL -- the lock still MINTS for the people it is supposed to');

t('a DVM mints a token and is handed it once', async () => {
  const { res } = await mint('dr-a', 'dvm', PAYLOAD);
  assert.strictEqual(res.code, 200, JSON.stringify(res.body));
  assert.ok(res.body.token, 'no token returned');
  assert.strictEqual(res.body.witness_employee_id, 'dr-a');
});

t('...and an owner-dvm mints too, so §2 is not passing because the tier list '
  + 'is empty', async () => {
  const { res } = await mint('dr-b', 'owner', PAYLOAD);
  assert.strictEqual(res.code, 200, JSON.stringify(res.body));
});

// ── 2. M1: THE TIER IS ENFORCED AT THE CALL SITE ────────────────────────────
section('2. M1 -- only a licensed veterinarian may MINT (the call site, not '
        + 'the helper)');

t('a RECEPTIONIST is refused NOT_A_PRESCRIBER and no row is written', async () => {
  const { res, calls } = await mint('rec-1', 'receptionist', PAYLOAD);
  assert.strictEqual(res.code, 403, JSON.stringify(res.body));
  assert.strictEqual(res.body.error.code, 'NOT_A_PRESCRIBER');
  const wrote = calls.filter((c) => c.method === 'POST'
                             && c.url.indexOf('sairnvet_witness_tokens') !== -1);
  assert.strictEqual(wrote.length, 0,
    'REFUSED AND STILL WROTE A ROW -- a 403 with a token row behind it is worse '
    + 'than either outcome alone');
});

t('a TECH is refused too, so the refusal is a TIER and not one bad role name',
  async () => {
    const { res } = await mint('tech-1', 'tech', PAYLOAD);
    assert.strictEqual(res.code, 403, JSON.stringify(res.body));
    assert.strictEqual(res.body.error.code, 'NOT_A_PRESCRIBER');
  });

t('the ROLE ON THE ROW is the one the database returned, not the one in the '
  + 'session -- a demotion takes effect at once', async () => {
    // Session still says dvm; the employee row says receptionist. The lock's
    // own rule is that the row wins, and if it ever stopped winning a demoted
    // vet could keep minting until the token aged out.
    SESSION = { employee_id: 'dr-a', role: 'dvm', app: 'sairnvet' };
    const calls = fakeRest([caller('dr-a', 'receptionist'), MINT_OK, POLICY_READ]);
    const res = mkRes();
    await W(mkReq({ action: 'request', resource: 'sv_controlled', payload: PAYLOAD }), res);
    assert.strictEqual(res.code, 403, JSON.stringify(res.body));
    assert.strictEqual(res.body.error.code, 'NOT_A_PRESCRIBER');
  });

// ── 3. M2: THE STORED TOKEN IS A HASH, AT THE CALL SITE ─────────────────────
section('3. M2 -- what is STORED is a sha256, and what is RETURNED is not');

t('the token_hash POSTed is NOT the token handed to the caller', async () => {
  const { res, calls } = await mint('dr-a', 'dvm', PAYLOAD);
  const row = mintedRow(calls);
  assert.notStrictEqual(row.token_hash, res.body.token,
    'THE TABLE HOLDS A PLAINTEXT, SPENDABLE SIGNATURE on a DEA register');
});

t('...it is exactly sha256(token), which is what requireWitness looks up -- so '
  + 'a mismatch here breaks the lock outright rather than weakening it',
  async () => {
    const { res, calls } = await mint('dr-a', 'dvm', PAYLOAD);
    const row = mintedRow(calls);
    const expect = crypto.createHash('sha256').update(String(res.body.token))
      .digest('hex');
    assert.strictEqual(row.token_hash, expect);
  });

t('CONTROL: two mints produce two DIFFERENT hashes, so the arm above is not '
  + 'passing against a constant', async () => {
    const a = mintedRow((await mint('dr-a', 'dvm', PAYLOAD)).calls);
    const b = mintedRow((await mint('dr-a', 'dvm', PAYLOAD)).calls);
    assert.notStrictEqual(a.token_hash, b.token_hash);
  });

// ── 4. M3: THE TOKEN IS BOUND TO THE PAYLOAD, AT MINT TIME ──────────────────
section('4. M3 -- the content binding is made by the MINTER, not asserted by '
        + 'the fixture');

t('the content_hash POSTed equals contentHash(resource, payload)', async () => {
  const { calls } = await mint('dr-a', 'dvm', PAYLOAD);
  const row = mintedRow(calls);
  assert.strictEqual(row.content_hash, W.contentHash('sv_controlled', PAYLOAD));
});

t('...and a DIFFERENT payload mints a DIFFERENT content_hash -- this is the arm '
  + 'that dies against contentHash(resource, {})', async () => {
    const a = mintedRow((await mint('dr-a', 'dvm', PAYLOAD)).calls);
    const b = mintedRow((await mint('dr-a', 'dvm', OTHER_PAYLOAD)).calls);
    assert.notStrictEqual(a.content_hash, b.content_hash,
      'A TOKEN BOUND TO NOTHING can be spent on a different record -- the hole '
      + 'api/sv-witness.js:42-45 names in its own header');
  });

t('...and the SAME payload mints the SAME hash, so the arm above is about the '
  + 'payload rather than about randomness', async () => {
    const a = mintedRow((await mint('dr-a', 'dvm', PAYLOAD)).calls);
    const b = mintedRow((await mint('dr-a', 'dvm', PAYLOAD)).calls);
    assert.strictEqual(a.content_hash, b.content_hash);
  });

t('a mint with no payload is refused and writes nothing', async () => {
  const { res, calls } = await mint('dr-a', 'dvm', null);
  assert.strictEqual(res.code, 400, JSON.stringify(res.body));
  assert.strictEqual(calls.filter((c) => c.method === 'POST'
    && c.url.indexOf('sairnvet_witness_tokens') !== -1).length, 0);
});

// ── 5. M4: ONLY AN OWNER CHANGES THE POLICY ─────────────────────────────────
section('5. M4 -- require_two_person is an OWNER setting');

t('a DVM cannot turn two-person witnessing OFF', async () => {
  const { res, calls } = await setPolicy('dr-a', 'dvm', false);
  assert.strictEqual(res.code, 403, JSON.stringify(res.body));
  assert.strictEqual(res.body.error.code, 'FORBIDDEN');
  assert.strictEqual(calls.filter((c) => c.method === 'POST').length, 0,
    'REFUSED AND STILL WROTE THE POLICY');
});

t('a RECEPTIONIST cannot either', async () => {
  const { res } = await setPolicy('rec-1', 'receptionist', false);
  assert.strictEqual(res.code, 403, JSON.stringify(res.body));
});

t('CONTROL: an OWNER can, so the two arms above are a role gate and not a '
  + 'handler that refuses everybody', async () => {
    const { res } = await setPolicy('own-1', 'owner', true);
    assert.strictEqual(res.code, 200, JSON.stringify(res.body));
    assert.strictEqual(res.body.require_two_person, true);
  });

t('the owner tier is IMPORTED from sv-auth, not re-typed here', () => {
  assert.deepStrictEqual(svAuth.PROVISIONING_ROLES, ['owner'],
    'if this changes, the two refusal arms above are testing a stale list');
});

// ── 6. M5: THE ACTIVE FILTER, SOURCE-ANCHORED ───────────────────────────────
section('6. M5 -- the caller lookup filters on active=eq.true (SOURCE)');

t('activeCaller() still filters on active=eq.true', () => {
  // WEAKER THAN A BEHAVIOURAL ARM, ON PURPOSE, AND THE REASON IS WORTH READING.
  // A stub answering an empty list proves the lock refuses an EMPTY ANSWER --
  // not that the query asked the right question. The filter living or dying is
  // a property of the URL, so the URL is what is asserted. This is the remedy
  // witness_countersign.js:490-498 already uses for SAME_PERSON, applied to the
  // guard that file discloses it cannot reach.
  const src = fs.readFileSync(path.join(API, 'sv-witness.js'), 'utf8');
  const m = src.match(/async function activeCaller\(\)[\s\S]*?\n  \}/);
  assert.ok(m, 'activeCaller() not found -- this anchor has rotted, which is a '
    + 'finding rather than a pass');
  assert.ok(/active=eq\.true/.test(m[0]),
    'A STRUCK-OFF VET WITH A LIVE SESSION -- up to 12h -- CAN REQUEST AND '
    + 'COUNTERSIGN CONTROLLED-SUBSTANCE ENTRIES. That is the hazard '
    + 'api/sv-witness.js:172-175 names in words.');
});

t('...and the anchor is UNIQUE, so it cannot drift onto a different query', () => {
  const src = fs.readFileSync(path.join(API, 'sv-witness.js'), 'utf8');
  const hits = (src.match(/async function activeCaller\(\)/g) || []).length;
  assert.strictEqual(hits, 1,
    'activeCaller() is defined ' + hits + ' times; the arm above would be '
    + 'asserting about whichever came first');
});

t('the lock still refuses when the caller lookup returns EMPTY -- the '
  + 'behavioural half the anchor cannot replace', async () => {
    SESSION = { employee_id: 'gone', role: 'dvm', app: 'sairnvet' };
    const calls = fakeRest([[EMP + '?license_hash=eq.L1&employee_id=eq.gone',
                             { body: [] }]]);
    const res = mkRes();
    await W(mkReq({ action: 'request', resource: 'sv_controlled', payload: PAYLOAD }), res);
    assert.strictEqual(res.code, 401, JSON.stringify(res.body));
    assert.strictEqual(calls.filter((c) => c.method === 'POST').length, 0);
  });

// ── RUN ─────────────────────────────────────────────────────────────────────
(async () => {
  for (const [name, fn] of queue) {
    if (fn === null) { console.log('\n' + name); continue; }
    try { await fn(); console.log('  PASS ' + name); pass++; }
    catch (e) {
      console.log('  FAIL ' + name + '\n        ' + String(e.message).slice(0, 400));
      fail++;
    }
  }
  console.log('\nwitness_mint: ' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
