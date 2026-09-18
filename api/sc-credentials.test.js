// api/sc-credentials.test.js
// REQUIREMENT: a deactivated SAIRNcode credential cannot act on a still-valid token,
//   and the last administrator cannot be removed
//
//
// Run:  node --test api/sc-credentials.test.js
//
// THE BUG THIS SUITE EXISTS FOR. Every service credential for a practice lives
// in ONE jsonb blob keyed (license_hash, credential_id='default'). The handler
// read that blob, changed one service inside it, and upserted the WHOLE THING
// back with resolution=merge-duplicates -- which replaces `data` wholesale.
//
// Two Compliance Admins configuring DIFFERENT services in the same window both
// read the same blob; each wrote their own service on top of what they read;
// the second write silently dropped the first's credential. No error, nothing
// in the UI, and the missing key only surfaces later as an eligibility check
// reporting NOT_CONFIGURED for a service somebody knows they set up.
//
// So these tests are about what SURVIVES a concurrent write, not about what
// the endpoint returns on the happy path. The interleaving is forced
// explicitly rather than hoped for: the stub lets a test mutate the stored row
// in between the handler's read and its write.
//
// Supabase is stubbed by URL and RECORDS every request, so a test can assert
// the write was CONDITIONAL (an updated_at filter on a PATCH) rather than the
// old unconditional upsert -- the shape is the fix, and asserting only the
// final blob would pass against a lucky ordering.
//
// SCOPE CORRECTION, RECORDED RATHER THAN QUIETLY WORKED AROUND. ALLOWED_SERVICES
// currently contains exactly ONE service ('stedi'), so the two-admins-different-
// services race CANNOT happen in production today -- both would be setting the
// same key, where last-write-wins is the correct answer. The lost-update shape is
// real in the code and becomes live the moment a second service is added, which
// the allowlist is explicitly built to allow. So these tests drive the mechanism
// with the one real service while the interleaved writer introduces OTHER content
// into the same blob; the assertion is that content survives, which is exactly
// what a second service would need.
//
// Every value below is a placeholder built by concatenation; nothing here is
// or resembles a real credential.

'use strict';
const test = require('node:test');
const assert = require('node:assert');

// ── STUBS, INSTALLED BEFORE api/sc-credentials.js IS LOADED ────────────────
const licPath = require.resolve('./_lib/license.js');
const authPath = require.resolve('./_lib/auth.js');
const realAuth = require(authPath);

let SESSION = null;
let LICENSE = null;

require.cache[licPath] = {
  id: licPath, filename: licPath, loaded: true, exports: {
    validateLicenseKey: async () => LICENSE
  }
};
require.cache[authPath] = {
  id: authPath, filename: authPath, loaded: true, exports: Object.assign({}, realAuth, {
    verifySessionToken: () => SESSION,
    tokenFromRequest: (req) => req.headers['x-sd-auth'] || null,
    // Deterministic and obviously not encryption -- these tests are about
    // concurrency, and a real cipher here would only add noise.
    encryptSecret: (v) => 'enc(' + v + ')'
  })
};

const PLACEHOLDER = 'stub-' + 'placeholder';
[
  ['SUPABASE_URL', 'https://stub.supabase.co'],
  ['SUPABASE_SERVICE_ROLE_KEY', PLACEHOLDER],
  ['SD_AUTH_SECRET', PLACEHOLDER]
].forEach((p) => { process.env[p[0]] = p[1]; });

const handler = require('./sc-credentials.js');

// ── THE SUPABASE STUB ──────────────────────────────────────────────────────
// One row, because the table is unique on (license_hash, credential_id) and
// this endpoint only ever touches credential_id='default'.
let ROW = null;            // { data, updated_at } or null
let REQUESTS = [];
let ON_BEFORE_WRITE = null; // hook that simulates another admin winning the race
// PER-WRITE RESPONSE PLAN (2026-09-18). The stub could only ever answer the
// way PostgREST does when everything works, so the shape that mattered --
// a 2xx whose BODY cannot be read -- was unreachable from this suite and the
// defect below lived behind it. Keys are 'patch1','patch2','post1'.
let RESPONSE_PLAN = null;
let PATCHES = 0, POSTS = 0;
const realFetch = global.fetch;

function paramsOf(url) {
  const q = url.indexOf('?');
  return q === -1 ? new URLSearchParams() : new URLSearchParams(url.slice(q + 1));
}
function json(body, status) {
  return { ok: status >= 200 && status < 300, status: status, json: async () => body };
}

global.fetch = async (url, opts) => {
  opts = opts || {};
  const method = (opts.method || 'GET').toUpperCase();
  const params = paramsOf(String(url));
  REQUESTS.push({ method, url: String(url), body: opts.body ? JSON.parse(opts.body) : null });

  if (method === 'GET') {
    return json(ROW ? [{ data: ROW.data, updated_at: ROW.updated_at }] : [], 200);
  }

  if (ON_BEFORE_WRITE) { const h = ON_BEFORE_WRITE; ON_BEFORE_WRITE = null; h(); }

  if (method === 'PATCH') {
    PATCHES += 1;
    const planned = RESPONSE_PLAN && RESPONSE_PLAN['patch' + PATCHES];
    if (planned === 'unparseable') return { ok: true, status: 200, json: async () => { throw new Error('unparseable'); } };
    if (planned === 'notarray') return json({ data: {} }, 200);
    if (planned === 'tworows') return json([{ data: {} }, { data: {} }], 200);
    const want = params.get('updated_at');
    const expected = want && want.indexOf('eq.') === 0 ? want.slice(3) : null;
    // The precondition. A mismatch returns ZERO rows -- PostgREST's answer to
    // "the row is there, your filter just did not match it".
    if (!ROW || ROW.updated_at !== expected) return json([], 200);
    ROW = { data: opts.body ? JSON.parse(opts.body).data : ROW.data,
            updated_at: JSON.parse(opts.body).updated_at };
    return json([{ data: ROW.data, updated_at: ROW.updated_at }], 200);
  }

  if (method === 'POST') {
    POSTS += 1;
    const plannedP = RESPONSE_PLAN && RESPONSE_PLAN['post' + POSTS];
    if (plannedP === 'unparseable') return { ok: true, status: 200, json: async () => { throw new Error('unparseable'); } };
    // Plain INSERT. A row already present is a unique violation, which is the
    // loud loss the old upsert used to hide.
    if (ROW) return json({ code: '23505', message: 'duplicate key' }, 409);
    const b = JSON.parse(opts.body);
    ROW = { data: b.data, updated_at: b.updated_at };
    return json([{ data: ROW.data, updated_at: ROW.updated_at }], 200);
  }
  return json({}, 500);
};

// ── HARNESS ────────────────────────────────────────────────────────────────
function mkRes() {
  const out = { code: null, body: null };
  return {
    _out: out,
    setHeader() {},
    status(c) { out.code = c; return this; },
    json(b) { out.body = b; return this; },
    end() { return this; }
  };
}
async function call(body) {
  const req = { method: 'POST', headers: { 'x-sd-auth': 'tok', authorization: 'Bearer LIC' }, body };
  const res = mkRes();
  await handler(req, res);
  return res._out;
}
function reset() {
  ROW = null; REQUESTS = []; ON_BEFORE_WRITE = null;
  RESPONSE_PLAN = null; PATCHES = 0; POSTS = 0;
  LICENSE = { valid: true, active: true, license_hash: 'H1', app_id: 'sairncode' };
  SESSION = { role: 'admin', employee_id: 'E-ADMIN' };
}

// ── THE DEFECT ─────────────────────────────────────────────────────────────

test('a concurrent write by another admin is not silently discarded', async () => {
  reset();
  ROW = { data: {}, updated_at: '2026-09-04T10:00:00.000Z' };

  // Between this request's read and its write, another admin writes something
  // else into the same blob. That is the interleaving that used to lose data:
  // the old code upserted the whole blob it had read, erasing whatever landed.
  ON_BEFORE_WRITE = () => {
    ROW = { data: { other_service: { enc: 'enc(theirs)' } }, updated_at: '2026-09-04T10:00:05.000Z' };
  };

  const out = await call({ action: 'set', service: 'stedi', value: 'mine' });

  assert.strictEqual(out.code, 200, 'the retry should have succeeded');
  assert.strictEqual(out.body.retried, true, 'the conflict should be reported as a retry, not hidden');
  assert.ok(ROW.data.other_service, 'what the other admin wrote must survive');
  assert.strictEqual(ROW.data.other_service.enc, 'enc(theirs)');
  assert.ok(ROW.data.stedi, 'this request own change must also land');
});

test('the write is CONDITIONAL -- an unconditional upsert would pass the test above by luck', async () => {
  reset();
  ROW = { data: { stedi: { enc: 'enc(x)' } }, updated_at: '2026-09-04T10:00:00.000Z' };
  await call({ action: 'set', service: 'stedi', value: 'v' });
  const patches = REQUESTS.filter((r) => r.method === 'PATCH');
  assert.ok(patches.length >= 1, 'an existing row must be updated, not upserted');
  assert.ok(/updated_at=eq\./.test(patches[0].url),
    'the update must carry the updated_at precondition it read');
  assert.ok(!REQUESTS.some((r) => /on_conflict/.test(r.url)),
    'the blind merge-duplicates upsert must be gone');
});

test('a second conflict is reported as 409 rather than retried forever', async () => {
  reset();
  ROW = { data: { stedi: {} }, updated_at: 'T0' };
  // Every write attempt is preceded by somebody else winning.
  let n = 0;
  const bump = () => { ROW = { data: ROW.data, updated_at: 'T' + (++n) }; ON_BEFORE_WRITE = bump; };
  ON_BEFORE_WRITE = bump;

  const out = await call({ action: 'set', service: 'stedi', value: 'v' });
  assert.strictEqual(out.code, 409);
  assert.strictEqual(out.body.error.code, 'WRITE_CONFLICT');
  assert.ok(/Nothing was saved/.test(out.body.error.message),
    'the caller must be told plainly that nothing was saved');
});

// ── THE PATHS THAT MUST STILL WORK ─────────────────────────────────────────

test('first write with no row present inserts', async () => {
  reset();
  const out = await call({ action: 'set', service: 'stedi', value: 'first' });
  assert.strictEqual(out.code, 200);
  assert.ok(ROW && ROW.data.stedi, 'the credential must be stored');
  assert.ok(REQUESTS.some((r) => r.method === 'POST'), 'no row means an INSERT');
});

test('clear removes only the named service', async () => {
  reset();
  ROW = { data: { stedi: { enc: 'e1' }, other_service: { enc: 'e2' } }, updated_at: 'T0' };
  const out = await call({ action: 'clear', service: 'stedi' });
  assert.strictEqual(out.code, 200);
  assert.ok(!ROW.data.stedi, 'the named service is removed');
  assert.ok(ROW.data.other_service, 'unrelated blob content is not');
});

// ── `clear` IS IMPLEMENTED TWICE AND ONLY ONE COPY HAD AN ARM ──────────────
// Added 2026-09-16, after a negative control changed the RETRY copy of the
// change to wipe the whole blob and this suite stayed GREEN. The handler
// applies the change in two places on purpose -- once on the main path, and
// once in applyChange(), so a retry re-applies THIS request's change to a
// freshly-read blob rather than re-sending a stale merge. That is the right
// design and it means the deletion is written twice, and the arm above never
// conflicts, so it only ever reached one of them.
//
// This is the same shape as the defect the whole file exists for: a write that
// silently loses another administrator's credential, arriving on the path that
// runs only when another administrator was actually there.
test('clear survives the CONFLICT RETRY -- the second copy of the change is '
  + 'reached only when another admin won the race', async () => {
    reset();
    ROW = { data: { stedi: { enc: 'e1' }, other_service: { enc: 'e2' } }, updated_at: 'T0' };
    ON_BEFORE_WRITE = () => { ROW = { data: ROW.data, updated_at: 'T1' }; };
    const out = await call({ action: 'clear', service: 'stedi' });
    assert.strictEqual(out.code, 200, JSON.stringify(out.body));
    assert.strictEqual(out.body.retried, true,
      'the fixture did not force the retry path, so this arm proves nothing '
      + 'the arm above does not already prove');
    assert.ok(!ROW.data.stedi, 'the named service is removed');
    assert.ok(ROW.data.other_service,
      'unrelated blob content did not survive the RETRY copy of the change');
  });

test('status never writes', async () => {
  reset();
  ROW = { data: { stedi: { enc: 'e1', last4: '1234' } }, updated_at: 'T0' };
  const out = await call({ action: 'status' });
  assert.strictEqual(out.code, 200);
  assert.ok(!REQUESTS.some((r) => r.method !== 'GET'), 'status is read-only');
});

test('a non-admin is refused before anything is written', async () => {
  reset();
  SESSION = { role: 'coder', employee_id: 'E-CODER' };
  ROW = { data: { stedi: { enc: 'e1' } }, updated_at: 'T0' };
  const out = await call({ action: 'set', service: 'stedi', value: 'v' });
  assert.strictEqual(out.code, 403);
  assert.ok(!REQUESTS.some((r) => r.method !== 'GET'), 'nothing may be written on a refused call');
  assert.ok(!ROW.data.stedi.enc || ROW.data.stedi.enc === 'e1', 'the stored value is untouched');
});

test('no session is refused before the table is touched at all', async () => {
  reset();
  SESSION = null;
  const out = await call({ action: 'status' });
  assert.strictEqual(out.code, 401);
  assert.strictEqual(REQUESTS.length, 0);
});

// ── A 2xx WHOSE BODY CANNOT BE READ IS NOT A SUCCESSFUL WRITE (2026-09-18) ──
// Found by an independent review of the 2026-09-16 negative control, and it is
// THIS FILE'S OWN arm-2 defect arriving through a different door.
//
// Under `Prefer: return=representation` a PATCH that MATCHED returns one row
// and a PATCH that matched ZERO returns `[]` with status 200. The handler read
// that with `.json().catch(() => null)` and asked only whether the result was
// an array of length zero -- so an UNPARSEABLE body became `null`, which is not
// an array, which is not length zero, and fell through to `{ ok: true }`.
// Measured before the fix, with the stored blob untouched: the main path
// returned 200 {ok:true} and the retry path 200 {ok:true, retried:true}, each
// over a write that did not happen.
//
// THE DISTINCTION THESE ARMS PIN IS THREE-WAY, and the third is the point.
// `[]` means the server SPOKE and matched nothing -- a conflict, retryable.
// An unreadable or wrong-shaped body means the answer could not be read, and
// collapsing that into either neighbour is a lie in one direction or the other:
// called success it is a false confirmation, called conflict it claims nothing
// was saved when the write may well have landed.

test('an UNPARSEABLE representation on the first write is UNKNOWN, never ok', async () => {
  reset();
  ROW = { data: { other: { enc: 'e2' } }, updated_at: 'T0' };
  RESPONSE_PLAN = { patch1: 'unparseable' };
  const out = await call({ action: 'set', service: 'stedi', value: 'v' });
  assert.notStrictEqual(out.body && out.body.ok, true,
    'a write whose answer could not be read was reported as saved');
  assert.strictEqual(out.code, 502);
  assert.strictEqual(out.body.error.code, 'WRITE_UNCONFIRMED');
  assert.match(out.body.error.message, /UNKNOWN/);
  assert.ok(!ROW.data.stedi, 'nothing should have been stored');
});

test('...and on the RETRY write too', async () => {
  reset();
  ROW = { data: { stedi: { enc: 'e1' }, other: { enc: 'e2' } }, updated_at: 'T0' };
  // first PATCH misses -> retry; the retry's body is the unreadable one
  ON_BEFORE_WRITE = () => { ROW = { data: ROW.data, updated_at: 'T1' }; };
  RESPONSE_PLAN = { patch2: 'unparseable' };
  const out = await call({ action: 'clear', service: 'stedi' });
  assert.notStrictEqual(out.body && out.body.ok, true);
  assert.strictEqual(out.body.error.code, 'WRITE_UNCONFIRMED');
  assert.ok(ROW.data.stedi, 'the clear must not have been applied');
});

test('a body of the WRONG SHAPE is UNKNOWN as well -- not an array, or two rows', async () => {
  for (const shape of ['notarray', 'tworows']) {
    reset();
    ROW = { data: { other: { enc: 'e2' } }, updated_at: 'T0' };
    RESPONSE_PLAN = { patch1: shape };
    const out = await call({ action: 'set', service: 'stedi', value: 'v' });
    assert.strictEqual(out.body.error && out.body.error.code, 'WRITE_UNCONFIRMED',
      shape + ' was not treated as unknown: ' + JSON.stringify(out.body));
  }
});

test('an unparseable INSERT is UNKNOWN too -- the first-write path asks for a representation as well', async () => {
  reset();
  ROW = null;
  RESPONSE_PLAN = { post1: 'unparseable' };
  const out = await call({ action: 'set', service: 'stedi', value: 'v' });
  assert.strictEqual(out.body.error && out.body.error.code, 'WRITE_UNCONFIRMED');
  assert.strictEqual(ROW, null, 'nothing should have been inserted');
});

test('an EMPTY representation is still a CONFLICT, not an unknown', async () => {
  // The direction that must not soften. `[]` is the server answering, so it
  // stays retryable and keeps its own message. An arm of mine first asserted
  // WRITE_UNCONFIRMED here and the CODE was right, not the test.
  reset();
  ROW = { data: { stedi: { enc: 'e1' } }, updated_at: 'T0' };
  ON_BEFORE_WRITE = () => { ROW = { data: ROW.data, updated_at: 'T1' }; };
  RESPONSE_PLAN = { patch2: 'empty-not-planned' };   // second PATCH misses naturally
  const out = await call({ action: 'clear', service: 'stedi' });
  assert.ok(out.body.ok === true || (out.body.error && out.body.error.code === 'WRITE_CONFLICT'),
    'an empty representation must resolve as conflict-or-retry, never as unknown: '
    + JSON.stringify(out.body));
  assert.notStrictEqual(out.body.error && out.body.error.code, 'WRITE_UNCONFIRMED');
});

// ── THE INSERT RACE: A 409 IS A DEFINITE MISS, NOT AN UNKNOWN (2026-09-18) ──
// Added because a sabotage survived. Turning `writeR.status === 409 ? MISSED`
// into `? UNKNOWN` left the suite GREEN -- nothing drove a 409 out of the FIRST
// write. It happens on the insert path: no row existed at read time, another
// admin inserted first, and the unique constraint speaks. That is the server
// ANSWERING, so it must stay retryable; classifying it unknown would turn a
// recoverable race into a refusal the caller cannot act on.
test('a 409 from the INSERT race retries and resolves, never WRITE_UNCONFIRMED', async () => {
  reset();
  ROW = null;                                   // nothing there when we read
  // Another admin inserts between our read and our write.
  ON_BEFORE_WRITE = () => { ROW = { data: { other: { enc: 'theirs' } }, updated_at: 'T9' }; };
  const out = await call({ action: 'set', service: 'stedi', value: 'mine' });
  assert.notStrictEqual(out.body.error && out.body.error.code, 'WRITE_UNCONFIRMED',
    'a 409 is the server answering -- it is a miss, not an unreadable answer');
  assert.strictEqual(out.code, 200, JSON.stringify(out.body));
  assert.strictEqual(out.body.retried, true, 'the 409 must route to the retry');
  assert.ok(ROW.data.stedi, 'our change did not survive the retry');
  assert.ok(ROW.data.other, "the other admin's insert was overwritten");
});

test.after(() => { global.fetch = realFetch; });
