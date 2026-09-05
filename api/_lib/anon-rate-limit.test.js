// api/_lib/anon-rate-limit.test.js
// Run:  node api/_lib/anon-rate-limit.test.js
//
// Covers the 2026-09-05 limiter on api/sd-data.js's now-unauthenticated
// licence lookup, and the property that matters more than the limit itself:
//
//   A CALLER WITH A VALID LICENCE CAN NEVER BE REFUSED BY IT.
//
// That is the whole reason this enforces by default where ai-rate-limit.js
// observes by default, so it is asserted through the REAL sd-data handler
// rather than argued for in a comment. If it ever stops holding, this fails.
//
// The handler cases stub global.fetch and the env; no network, no database.

const assert = require('assert');
const path = require('path');

let pass = 0, fail = 0;
function test(name, fn) { queue.push({ name, fn }); }
function section(t) { queue.push({ section: t }); }
const queue = [];

const LIMITER = path.join(__dirname, 'anon-rate-limit.js');
const HANDLER = path.join(__dirname, '..', 'sd-data.js');

// ENFORCEMENT IS TURNED ON EXPLICITLY FOR THIS SUITE, because as of 2026-09-05
// it is OFF by default -- production measurement showed scale-out gives every
// instance its own counter, so the 429 essentially never fires and all the
// default could still do was refuse a real customer behind a shared address.
// The counting and refusal MECHANISM is still correct code and is still worth
// testing, so the cases below opt in. Two cases deliberately do not, and assert
// the default: 'it OBSERVES by default' and 'the default never refuses anyone'.
process.env.SAIRN_ANON_RATE_LIMIT_MODE = 'enforce';

function freshLimiter() {
  delete require.cache[require.resolve(LIMITER)];
  return require(LIMITER);
}

// ── unit ───────────────────────────────────────────────────────────────────
section('the address it keys on');

test('prefers the platform-set header over the chain a caller can prepend to', () => {
  const rl = freshLimiter();
  assert.strictEqual(
    rl.clientAddress({ headers: { 'x-vercel-forwarded-for': '1.1.1.1', 'x-forwarded-for': '9.9.9.9' } }),
    '1.1.1.1');
});

test('falls back to the FIRST entry of x-forwarded-for', () => {
  const rl = freshLimiter();
  assert.strictEqual(rl.clientAddress({ headers: { 'x-forwarded-for': '2.2.2.2, 3.3.3.3' } }), '2.2.2.2');
});

test('an unknown address is never tracked, and therefore never refused', () => {
  // Fail open: no header is not a reason to refuse somebody.
  const rl = freshLimiter();
  const req = { headers: {} };
  for (let i = 0; i < 100; i++) rl.recordInvalidLicence(req);
  assert.strictEqual(rl.checkAnonRate(req).refuse, false);
  assert.strictEqual(rl._buckets.size, 0, 'an unkeyable request was still stored');
});

section('counting');

const req1 = { headers: { 'x-vercel-forwarded-for': '10.0.0.1' } };
const req2 = { headers: { 'x-vercel-forwarded-for': '10.0.0.2' } };

test('under the limit is allowed', () => {
  const rl = freshLimiter();
  for (let i = 0; i < rl.limit() - 1; i++) rl.recordInvalidLicence(req1);
  assert.strictEqual(rl.checkAnonRate(req1).refuse, false);
});

test('AT the limit is refused', () => {
  const rl = freshLimiter();
  for (let i = 0; i < rl.limit(); i++) rl.recordInvalidLicence(req1);
  const r = rl.checkAnonRate(req1);
  assert.strictEqual(r.refuse, true, 'count ' + r.count + ' of ' + r.limit);
});

test('one address does not refuse another', () => {
  const rl = freshLimiter();
  for (let i = 0; i < rl.limit() + 5; i++) rl.recordInvalidLicence(req1);
  assert.strictEqual(rl.checkAnonRate(req1).refuse, true);
  assert.strictEqual(rl.checkAnonRate(req2).refuse, false);
});

test('the window expires, so it self-heals rather than banning', () => {
  const rl = freshLimiter();
  const t0 = 1000000;
  for (let i = 0; i < rl.limit() + 5; i++) rl.recordInvalidLicence(req1, t0);
  assert.strictEqual(rl.checkAnonRate(req1, t0).refuse, true);
  assert.strictEqual(rl.checkAnonRate(req1, t0 + rl.windowMs() + 1).refuse, false,
    'the count outlived its window -- this is a ban, not a limit');
});

test('OBSERVE mode counts and reports the overage but never refuses', () => {
  const rl = freshLimiter();
  const prev = process.env.SAIRN_ANON_RATE_LIMIT_MODE;
  process.env.SAIRN_ANON_RATE_LIMIT_MODE = 'observe';
  try {
    for (let i = 0; i < rl.limit() + 5; i++) rl.recordInvalidLicence(req1);
    const r = rl.checkAnonRate(req1);
    assert.strictEqual(r.refuse, false);
    assert.strictEqual(r.over, true, 'observe mode hid the overage instead of reporting it');
  } finally {
    if (prev === undefined) delete process.env.SAIRN_ANON_RATE_LIMIT_MODE;
    else process.env.SAIRN_ANON_RATE_LIMIT_MODE = prev;
  }
});

test('it OBSERVES by default -- reversed 2026-09-05 on production evidence', () => {
  // It shipped enforcing, argued from "a refusal can only land on a request
  // that was already going to be refused". Production disagreed: 40 concurrent
  // junk requests produced zero 429s because scale-out gives every instance its
  // own counter. What enforcement could still do was refuse a real customer
  // behind a shared address who mistyped a key -- all cost, no benefit. This
  // assertion is the one that must be changed deliberately if that is revisited.
  const rl = freshLimiter();
  const prev = process.env.SAIRN_ANON_RATE_LIMIT_MODE;
  delete process.env.SAIRN_ANON_RATE_LIMIT_MODE;
  try {
    assert.strictEqual(rl.isEnforcing(), false,
      'the limiter enforces by default again -- see the measurement in its header');
  } finally {
    if (prev !== undefined) process.env.SAIRN_ANON_RATE_LIMIT_MODE = prev;
  }
});

test('the measured-inert finding is recorded in the module, not only in a row', () => {
  // A row is somewhere else. The next person to read this file must not have to
  // find it to learn that the thing does not work.
  const src = require('fs').readFileSync(LIMITER, 'utf8');
  assert.match(src, /MEASURED IN PRODUCTION 2026-09-05: THIS DOES NOT WORK/);
  assert.match(src, /HORIZONTAL SCALE-OUT DEFEATS A PER-INSTANCE COUNTER/);
});

test('the map cannot be grown without bound by a spread flood', () => {
  // A limiter that can be made to exhaust an instance's memory is a denial of
  // service wearing a fix's clothes.
  const rl = freshLimiter();
  const t0 = 2000000;
  for (let i = 0; i < 6000; i++) {
    rl.recordInvalidLicence({ headers: { 'x-vercel-forwarded-for': '10.1.' + (i >> 8) + '.' + (i & 255) } }, t0);
  }
  assert.ok(rl._buckets.size <= 5000, 'tracked ' + rl._buckets.size + ' addresses');
});

// ── through the real handler ───────────────────────────────────────────────
section('through the REAL sd-data handler');

function loadHandler() {
  delete require.cache[require.resolve(HANDLER)];
  delete require.cache[require.resolve(LIMITER)];
  return { handler: require(HANDLER), rl: require(LIMITER) };
}

async function call(handler, req) {
  const out = { code: null, body: null };
  const res = { status(c) { out.code = c; return res; }, json(b) { out.body = b; return res; } };
  await handler(req, res);
  return out;
}

function post(addr, key) {
  return {
    method: 'POST',
    headers: { authorization: 'Bearer ' + key, 'x-vercel-forwarded-for': addr },
    body: { action: 'read', resource: 'profile', payload: {} }
  };
}

async function withStubbedLicence(rows, fn) {
  const envURL = process.env.SUPABASE_URL;
  const envKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
  const realFetch = global.fetch;
  let lookups = 0;
  process.env.SUPABASE_URL = 'https://stub.invalid';
  process.env.SUPABASE_SERVICE_ROLE_KEY = 'stub-service-key';
  global.fetch = async () => { lookups++; return { ok: true, status: 200, json: async () => rows }; };
  try {
    return await fn(() => lookups);
  } finally {
    global.fetch = realFetch;
    if (envURL === undefined) delete process.env.SUPABASE_URL; else process.env.SUPABASE_URL = envURL;
    if (envKey === undefined) delete process.env.SUPABASE_SERVICE_ROLE_KEY; else process.env.SUPABASE_SERVICE_ROLE_KEY = envKey;
  }
}

test('a flood of junk keys is refused 429 -- WITHOUT a database lookup', async () => {
  const { handler, rl } = loadHandler();
  rl._reset();
  await withStubbedLicence([], async (lookups) => {
    let first429 = -1;
    for (let i = 0; i < rl.limit() + 3; i++) {
      const r = await call(handler, post('203.0.113.7', 'junk-' + i));
      if (r.code === 429) { first429 = i; break; }
      assert.strictEqual(r.code, 401, 'expected 401 before the limit, got ' + r.code);
    }
    assert.strictEqual(first429, rl.limit(), 'refused at attempt ' + first429 + ', limit is ' + rl.limit());
    const before = lookups();
    const r = await call(handler, post('203.0.113.7', 'junk-again'));
    assert.strictEqual(r.code, 429);
    assert.strictEqual(lookups(), before,
      'the 429 still cost a database lookup, which is the whole thing it exists to avoid');
  });
});

test('THE DEFAULT NEVER REFUSES ANYONE, however many failures', async () => {
  // The safe interim state while the design decision is open. If this ever
  // returns 429 with no explicit enforce, the default flipped back and the
  // production measurement in the module header was not read.
  const prev = process.env.SAIRN_ANON_RATE_LIMIT_MODE;
  delete process.env.SAIRN_ANON_RATE_LIMIT_MODE;
  try {
    const { handler, rl } = loadHandler();
    rl._reset();
    await withStubbedLicence([], async () => {
      for (let i = 0; i < rl.limit() * 2; i++) {
        const r = await call(handler, post('203.0.113.99', 'junk-' + i));
        assert.strictEqual(r.code, 401, 'got ' + r.code + ' on attempt ' + i);
      }
    });
  } finally {
    process.env.SAIRN_ANON_RATE_LIMIT_MODE = prev === undefined ? 'enforce' : prev;
  }
});

test('...and says nothing about what exists', async () => {
  const { handler, rl } = loadHandler();
  rl._reset();
  const reg = require('../_resources');
  await withStubbedLicence([], async () => {
    for (let i = 0; i <= rl.limit(); i++) await call(handler, post('203.0.113.8', 'junk-' + i));
    const r = await call(handler, {
      method: 'POST',
      headers: { authorization: 'Bearer junk', 'x-vercel-forwarded-for': '203.0.113.8' },
      body: { action: 'read', resource: '__no_such_resource__', payload: {} }
    });
    assert.strictEqual(r.code, 429);
    const text = JSON.stringify(r.body);
    assert.ok(!/resource must be one of/.test(text), text);
    for (const n of reg.RESOURCE_NAMES) assert.ok(text.indexOf(n) === -1, 'the 429 names "' + n + '"');
  });
});

test('A VALID LICENCE IS NEVER REFUSED, however many times it calls', async () => {
  // The load-bearing property. Only a FAILED validation is recorded, so no
  // volume of real traffic from one office can trip this.
  const { handler, rl } = loadHandler();
  rl._reset();
  await withStubbedLicence([{ status: 'active', app_id: 'stonedesk' }], async () => {
    for (let i = 0; i < rl.limit() * 3; i++) {
      const r = await call(handler, post('198.51.100.5', 'a-real-key'));
      assert.notStrictEqual(r.code, 429, 'a valid licence was rate limited on call ' + i);
    }
    assert.strictEqual(rl._buckets.size, 0, 'a valid licence was counted against its address');
  });
});

test('a valid licence from an address ALREADY over the limit is still refused', async () => {
  // Honest limit, asserted rather than glossed: the gate is checked before the
  // key is known, so one bad actor behind a shared NAT does affect the office.
  // Recorded here so the behaviour is a decision, not a surprise.
  const { handler, rl } = loadHandler();
  rl._reset();
  await withStubbedLicence([], async () => {
    for (let i = 0; i <= rl.limit(); i++) await call(handler, post('198.51.100.9', 'junk-' + i));
  });
  await withStubbedLicence([{ status: 'active', app_id: 'stonedesk' }], async () => {
    const r = await call(handler, post('198.51.100.9', 'a-real-key'));
    assert.strictEqual(r.code, 429,
      'if this ever returns 200, the limiter moved below validation -- update this test deliberately');
  });
});

test('an INACTIVE licence is not counted -- a real key was presented', async () => {
  const { handler, rl } = loadHandler();
  rl._reset();
  await withStubbedLicence([{ status: 'suspended', app_id: 'stonedesk' }], async () => {
    for (let i = 0; i < rl.limit() + 3; i++) {
      const r = await call(handler, post('198.51.100.6', 'a-suspended-key'));
      assert.strictEqual(r.code, 403, 'got ' + r.code);
    }
    assert.strictEqual(rl._buckets.size, 0, 'an inactive licence was counted as an attack');
  });
});

test('a MISSING bearer is not counted -- no lookup happened', async () => {
  const { handler, rl } = loadHandler();
  rl._reset();
  const r = await call(handler, { method: 'POST', headers: { 'x-vercel-forwarded-for': '198.51.100.7' }, body: {} });
  assert.strictEqual(r.code, 401);
  assert.strictEqual(r.body.error.code, 'NO_LICENSE');
  assert.strictEqual(rl._buckets.size, 0);
});

test('the limiter is wired ABOVE validateLicenseKey in the handler source', () => {
  // Runtime cannot distinguish "checked before the lookup" from "checked after
  // and the stub was cheap". This can. Comments stripped for the same reason
  // the ordering assertion in extra-actions.test.js strips them.
  const fs = require('fs');
  const raw = fs.readFileSync(HANDLER, 'utf8');
  const src = raw.split('\n').filter((l) => l.trim().indexOf('//') !== 0).join('\n');
  const body = src.slice(src.indexOf('module.exports = async (req, res) =>'));
  const check = body.indexOf('checkAnonRate(req)');
  const validate = body.indexOf('await validateLicenseKey(licenseKey)');
  assert.ok(check > 0 && validate > 0, 'call sites not found');
  assert.ok(check < validate,
    'the rate check moved BELOW the licence lookup -- every junk request pays for the lookup again');
});

(async () => {
  for (const item of queue) {
    if (item.section) { console.log('--- ' + item.section + ' ---'); continue; }
    try { await item.fn(); console.log('  ok   ' + item.name); pass++; }
    catch (e) { console.log('  FAIL ' + item.name + '\n       ' + e.message); fail++; }
  }
  console.log('\nanon-rate-limit: ' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
