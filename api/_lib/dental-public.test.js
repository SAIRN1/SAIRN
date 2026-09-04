// api/_lib/dental-public.test.js
// Run: node api/_lib/dental-public.test.js
//
// SAIRNdental's public, unauthenticated surface: booking, availability and
// patient complaints. Nobody signs in to reach any of it.
//
// ══ THE THREE SILENT FAILURES THIS HOLDS CLOSED ═══════════════════════════
// All three were found on 2026-09-03 while verifying a Supabase service_role
// key rotation. The StoneDesk copy of the same helpers had the first two; this
// one had all three, and guards patient-facing WRITES rather than catalog
// browsing.
//
//   1. resolveSlug() did `if (!r.ok) return null`, and every caller renders
//      null as 404 "Booking link not found". So a revoked key, an unreachable
//      database or a missing GRANT told a patient their perfectly good booking
//      link did not exist -- no error, no 502, no log.
//
//   2. checkAndIncrementRateLimit() read the counter with
//      `existing.ok ? await existing.json() : []`, so an unreachable store
//      read as count 0 and allowed everything.
//
//   3. The increment was `await fetch(...)` with NO .ok CHECK AT ALL. A failed
//      write meant the counter never rose, so the read kept returning 0 and
//      the limit could never re-engage for that window. This is the worst of
//      the three: the read succeeds, so nothing anywhere looks wrong.
//
// Together, 2 and 3 meant the limiter guarding 5 booking attempts and 5
// complaint submissions per hour could be entirely absent while reporting
// nothing at all.

'use strict';
const assert = require('assert');
const path = require('path');

const LIB = path.join(__dirname, 'dental-public.js');

let passed = 0;
async function test(name, fn) {
  try { await fn(); passed++; console.log('  ok - ' + name); }
  catch (e) { console.error('  FAIL - ' + name + '\n    ' + e.message); process.exitCode = 1; }
}

function load(fetchImpl) {
  process.env.SUPABASE_URL = 'https://test.supabase.co';
  process.env.SUPABASE_SERVICE_ROLE_KEY = 'test-key';
  global.fetch = fetchImpl;
  delete require.cache[require.resolve(LIB)];
  return require(LIB);
}
const REQ = { headers: { 'x-forwarded-for': '203.0.113.9' }, socket: {} };

function res(status, json) {
  return { ok: status >= 200 && status < 300, status: status, json: async () => json };
}

async function main() {
  console.log('api/_lib/dental-public.js -- a dead store is never an unknown practice, and never an open door');

  // ── 1. resolveSlug ──────────────────────────────────────────────────────
  await test('a real slug resolves', async () => {
    const lib = load(async () => res(200, [{ license_hash: 'hash-1' }]));
    assert.strictEqual(await lib.resolveSlug('smile-dental'), 'hash-1');
  });

  await test('a genuine miss is still null, so a wrong link is still a 404', async () => {
    const lib = load(async () => res(200, []));
    assert.strictEqual(await lib.resolveSlug('no-such-practice'), null);
  });

  await test('an empty slug is null without touching the database', async () => {
    let called = false;
    const lib = load(async () => { called = true; return res(200, []); });
    assert.strictEqual(await lib.resolveSlug(''), null);
    assert.strictEqual(called, false);
  });

  for (const status of [401, 403, 404, 500, 503]) {
    await test('HTTP ' + status + ' from the store THROWS -- it must not read as an unknown slug', async () => {
      const lib = load(async () => res(status, { message: 'nope' }));
      await assert.rejects(() => lib.resolveSlug('smile-dental'), (e) => {
        assert.strictEqual(e.code, 'UPSTREAM');
        assert.match(e.message, /slug lookup failed/);
        return true;
      });
    });
  }

  await test('and the callers already turn that throw into a logged 502, not a 404', async () => {
    // Not a behavioural drive -- an assertion about the four consumers, which
    // is why throwing was chosen over a sentinel nobody has to check.
    const fs = require('fs');
    ['public-availability.js', 'public-book.js', 'public-complaint-submit.js', 'public-complaint-thread.js']
      .forEach(function (f) {
        const src = fs.readFileSync(path.join(__dirname, '..', 'sairndental', f), 'utf8');
        assert.match(src, /catch \(err\)[\s\S]{0,200}res\.status\(502\)/,
          f + ' no longer answers 502 on a thrown lookup');
      });
  });

  // ── 2 + 3. the rate limiter ─────────────────────────────────────────────
  await test('under the limit: allowed, counted, and the increment is written', async () => {
    const calls = [];
    const lib = load(async (url, init) => {
      calls.push((init && init.method) || 'GET');
      return ((init && init.method) === 'POST') ? res(201, {}) : res(200, [{ count: 2 }]);
    });
    const r = await lib.checkAndIncrementRateLimit(REQ, 60, 5, 'book');
    assert.deepStrictEqual({ allowed: r.allowed, count: r.count }, { allowed: true, count: 3 });
    assert.deepStrictEqual(calls, ['GET', 'POST']);
  });

  await test('over the limit: refused as LIMITED, and no increment is written', async () => {
    const calls = [];
    const lib = load(async (url, init) => {
      calls.push((init && init.method) || 'GET');
      return res(200, [{ count: 5 }]);
    });
    const r = await lib.checkAndIncrementRateLimit(REQ, 60, 5, 'book');
    assert.strictEqual(r.allowed, false);
    assert.strictEqual(r.limited, true, 'a real limit must be distinguishable from an outage');
    assert.ok(!r.unavailable);
    assert.deepStrictEqual(calls, ['GET'], 'a refused request still wrote to the counter');
  });

  // Defect 2.
  for (const status of [401, 403, 500, 503]) {
    await test('counter READ fails (HTTP ' + status + ') -> UNAVAILABLE, not allowed', async () => {
      const lib = load(async () => res(status, { message: 'nope' }));
      const r = await lib.checkAndIncrementRateLimit(REQ, 60, 5, 'book');
      assert.strictEqual(r.allowed, false, 'an unreachable counter allowed the request');
      assert.strictEqual(r.unavailable, true);
      assert.ok(!r.limited, 'an outage must not be reported as a rate limit');
    });
  }

  await test('counter read THROWS -> UNAVAILABLE rather than an unhandled error', async () => {
    const lib = load(async () => { throw new Error('ECONNRESET'); });
    const r = await lib.checkAndIncrementRateLimit(REQ, 60, 5, 'book');
    assert.deepStrictEqual({ allowed: r.allowed, unavailable: r.unavailable }, { allowed: false, unavailable: true });
  });

  await test('counter read returns something that is not an array -> UNAVAILABLE, not count 0', async () => {
    const lib = load(async () => res(200, { unexpected: true }));
    const r = await lib.checkAndIncrementRateLimit(REQ, 60, 5, 'book');
    assert.strictEqual(r.unavailable, true);
  });

  // Defect 3 -- the one that had no check at all.
  for (const status of [401, 403, 409, 500]) {
    await test('counter INCREMENT fails (HTTP ' + status + ') -> UNAVAILABLE, not a silent allow', async () => {
      const lib = load(async (url, init) =>
        ((init && init.method) === 'POST') ? res(status, { message: 'nope' }) : res(200, [{ count: 0 }]));
      const r = await lib.checkAndIncrementRateLimit(REQ, 60, 5, 'book');
      assert.strictEqual(r.allowed, false,
        'an uncounted request was allowed -- the limit can never engage while the write keeps failing');
      assert.strictEqual(r.unavailable, true);
    });
  }

  await test('counter increment THROWS -> UNAVAILABLE', async () => {
    const lib = load(async (url, init) => {
      if ((init && init.method) === 'POST') throw new Error('ETIMEDOUT');
      return res(200, [{ count: 0 }]);
    });
    const r = await lib.checkAndIncrementRateLimit(REQ, 60, 5, 'book');
    assert.strictEqual(r.unavailable, true);
  });

  await test('a first-ever request for an IP starts at 1, not at NaN or 0', async () => {
    const lib = load(async (url, init) => ((init && init.method) === 'POST') ? res(201, {}) : res(200, []));
    const r = await lib.checkAndIncrementRateLimit(REQ, 60, 5, 'book');
    assert.deepStrictEqual({ allowed: r.allowed, count: r.count }, { allowed: true, count: 1 });
  });

  // ── the consumers answer 503, not 429 ───────────────────────────────────
  await test('all four consumers answer 503 UNAVAILABLE and keep 429 for a real limit', async () => {
    // "Too many requests" for an unreachable database is a wrong reason given
    // confidently -- the same class as a fabricated number.
    const fs = require('fs');
    ['public-availability.js', 'public-book.js', 'public-complaint-submit.js', 'public-complaint-thread.js']
      .forEach(function (f) {
        const src = fs.readFileSync(path.join(__dirname, '..', 'sairndental', f), 'utf8');
        assert.match(src, /if \(rl\.unavailable\)/, f + ' does not check rl.unavailable');
        assert.match(src, /res\.status\(503\)[\s\S]{0,120}UNAVAILABLE/, f + ' does not answer 503');
        assert.match(src, /rate-limit store unavailable/, f + ' does not log the outage');
        assert.match(src, /res\.status\(429\)[\s\S]{0,120}RATE_LIMITED/, f + ' lost its real rate-limit answer');
        // Order matters: the unavailable branch must come BEFORE the generic
        // !rl.allowed branch, or an outage still renders as 429.
        assert.ok(src.indexOf('rl.unavailable') < src.indexOf('!rl.allowed'),
          f + ' checks !rl.allowed first, so an outage still answers 429');
      });
  });

  // ── readRows: a failed read is not an empty table ───────────────────────
  await test('readRows returns the rows on a good read', async () => {
    const lib = load(async () => res(200, []));
    assert.deepStrictEqual(await lib.readRows(res(200, [{ a: 1 }]), 'x'), [{ a: 1 }]);
  });

  await test('a genuinely EMPTY table is still [] -- only could-not-ask changed', async () => {
    const lib = load(async () => res(200, []));
    assert.deepStrictEqual(await lib.readRows(res(200, []), 'x'), []);
  });

  for (const status of [400, 401, 403, 500, 503]) {
    await test('readRows THROWS on HTTP ' + status + ' -- it must not fabricate a calendar', async () => {
      const lib = load(async () => res(200, []));
      await assert.rejects(() => lib.readRows(res(status, { message: 'no' }), 'dnt_provider_hours'), (e) => {
        assert.strictEqual(e.code, 'UPSTREAM');
        assert.match(e.message, /dnt_provider_hours/, 'the message must name WHICH read failed');
        return true;
      });
    });
  }

  await test('readRows throws when the body is not an array', async () => {
    const lib = load(async () => res(200, []));
    await assert.rejects(() => lib.readRows(res(200, { oops: true }), 'x'), (e) => e.code === 'UPSTREAM');
  });

  await test('the nine fail-open reads are gone from the two public endpoints', async () => {
    // The calendar fabricated in BOTH directions: a failed provider-hours read
    // showed a practice as fully booked, a failed appointments read showed
    // every slot as free. Neither said anything to anyone.
    // public-availability.js still carries the comment recording that this
    // exact shape already shipped once and was found live.
    const fs = require('fs');
    ['public-availability.js', 'public-book.js'].forEach(function (f) {
      const src = fs.readFileSync(path.join(__dirname, '..', 'sairndental', f), 'utf8');
      assert.ok(!/\.ok \? await [A-Za-z]+\.json\(\) : \[\]/.test(src),
        f + ' still turns a failed read into an empty table');
      assert.match(src, /await readRows\(/, f + ' does not use the checked reader');
    });
  });

  console.log('\n' + passed + ' assertions passed');
}

main();
