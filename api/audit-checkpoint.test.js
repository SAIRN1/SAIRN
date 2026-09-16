// api/audit-checkpoint.test.js
//
// Run:  node api/audit-checkpoint.test.js
//
// Control for the daily audit checkpoints. Item 35d.
//
// THE ARM THAT MATTERS PLANTS A BACKDATED ROW INTO A CHECKPOINTED WINDOW AND
// DEMANDS THE VERIFIER FIND IT. Every other arm exists to stop that one being
// satisfied by a verifier that just always fails: an untouched table must come
// back clean, a window that legitimately grew AFTER its checkpoint window must
// not be flagged, and the two tamper shapes must be reported as DIFFERENT
// findings rather than one.
//
// WHY THE TWO SHAPES ARE KEPT APART, because collapsing them would lose the
// only diagnostic this mechanism produces: a row count that GREW is an
// INSERTION, which is the mode the grants leave open and the whole reason this
// exists. An unchanged count with a changed digest means a row's CONTENT moved,
// which `grant select, insert` says is impossible through the API -- so it
// points at direct database access, which is a different problem with a
// different response and no amount of checkpointing prevents it.
//
// DRIVEN AGAINST A FAKE REST LAYER. Stated rather than implied: these arms
// prove the DECISION LOGIC -- which verdict for which state -- and prove
// nothing about PostgREST. The paging arm in particular depends on
// Content-Range carrying an exact total, which only a live run can confirm; it
// is named in that arm.
//
// THE DIGEST ARMS NEED NO FAKE AT ALL and are the sharpest thing here. The
// canonical form IS the mechanism: if two serialisations of one window can
// differ, the verifier reports tampering on an untouched table, and this whole
// file is a machine for producing false alarms on a DEA-adjacent record.

'use strict';
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const AC = require('./audit-checkpoint.js');

let pass = 0, fail = 0;
const queue = [];
function t(name, fn) { queue.push([name, fn]); }
function section(s) { queue.push([s, null]); }

const DAY = 24 * 60 * 60 * 1000;
const D0 = Date.UTC(2026, 8, 10);           // 2026-09-10T00:00:00Z
const iso = (ms) => new Date(ms).toISOString();

function row(id, ms, extra) {
  return Object.assign({
    id: id, license_hash: 'L1', employee_id: 'e1', role: 'owner',
    event_type: 'login_success', detail: null, created_at: iso(ms)
  }, extra || {});
}

// ── A fake REST layer holding audit rows and checkpoints ────────────────────
// It answers the same shapes PostgREST does for the queries this file builds,
// and NOTHING ELSE -- an unrecognised URL throws rather than returning an empty
// array, because a silent [] is how a fake makes a broken query look clean.
function makeDb(opts) {
  opts = opts || {};
  // ALL THREE TABLES ARE MODELLED, EMPTY IF NOT SUPPLIED. The handler iterates
  // every table in AC.TABLES; a fake that models one of them makes the other
  // two throw, the outer catch turns that into a 502, and an arm asserting a
  // 200 then fails for a reason that has nothing to do with the subject. Found
  // by exactly that failure on the first run.
  const audit = {};
  for (const tbl of AC.TABLES) audit[tbl] = (opts.audit || {})[tbl] || [];
  const db = {
    audit: audit,                     // table -> rows[]
    checkpoints: [],                  // written rows
    missingCheckpointTable: !!opts.missingCheckpointTable,
    shortTotal: opts.shortTotal || 0, // force Content-Range to over-state
    countMode: opts.countMode || 'exact', // 'exact' | 'star' | 'none'
    writes: []
  };
  db.install = function () {
    global.fetch = async (url, init) => {
      const u = String(url);
      const q = u.slice(u.indexOf('/rest/v1/') + 9);
      const table = q.split('?')[0];
      const method = (init && init.method) || 'GET';
      const json = (body, status, hdrs) => ({
        ok: status === undefined || (status >= 200 && status < 300),
        status: status || 200,
        headers: { get: (k) => (hdrs || {})[String(k).toLowerCase()] || null },
        json: async () => body,
        text: async () => JSON.stringify(body)
      });
      if (table === 'sairn_audit_checkpoint') {
        if (db.missingCheckpointTable) {
          return json({ code: 'PGRST205', message: 'relation does not exist' }, 404);
        }
        if (method === 'POST') {
          const rec = JSON.parse(init.body);
          const dup = db.checkpoints.some((c) => c.audit_table === rec.audit_table &&
                                                 c.window_end === rec.window_end);
          if (dup) return json({ code: '23505', message: 'duplicate key' }, 409);
          db.checkpoints.push(rec);
          db.writes.push(rec);
          return json(null, 201);
        }
        const m = /audit_table=eq\.([^&]+)/.exec(q);
        const want = m ? decodeURIComponent(m[1]) : null;
        let rows = db.checkpoints.filter((c) => c.audit_table === want);
        rows = rows.slice().sort((a, b) => (a.window_end < b.window_end ? -1 : 1));
        if (q.indexOf('order=window_end.desc') !== -1) rows = rows.slice().reverse();
        if (q.indexOf('limit=1') !== -1) rows = rows.slice(0, 1);
        return json(rows, 200, { 'content-range': '0-' + rows.length + '/' + rows.length });
      }
      if (db.audit[table]) {
        const all = db.audit[table].slice()
          .sort((a, b) => (a.created_at < b.created_at ? -1
            : a.created_at > b.created_at ? 1 : (a.id < b.id ? -1 : 1)));
        if (q.indexOf('order=created_at.asc&limit=1') !== -1 ||
            (q.indexOf('limit=1') !== -1 && q.indexOf('created_at=gte.') === -1)) {
          return json(all.slice(0, 1), 200);
        }
        const g = /created_at=gte\.([^&]+)/.exec(q);
        const l = /created_at=lt\.([^&]+)/.exec(q);
        let rows = all;
        if (g && l) {
          const a = decodeURIComponent(g[1]), b = decodeURIComponent(l[1]);
          rows = all.filter((r) => r.created_at >= a && r.created_at < b);
        }
        const total = db.shortTotal || rows.length;
        // `countMode` models what the guard's INPUT can actually be. Added
        // 2026-09-14 after an independent review drove the handler with a
        // response that stated no total and watched it write a checkpoint over
        // one row of three.
        if (db.countMode === 'none') return json(rows, 200, {});
        if (db.countMode === 'star') {
          return json(rows, 200, { 'content-range': '0-' + rows.length + '/*' });
        }
        return json(rows, 200, { 'content-range': '0-' + rows.length + '/' + total });
      }
      throw new Error('the fake was asked something it does not model: ' + u);
    };
  };
  return db;
}

function makeRes() {
  const out = { code: null, body: null };
  return {
    out,
    status(c) { out.code = c; return this; },
    json(b) { out.body = b; return this; }
  };
}

async function call(db, action, now) {
  const realFetch = global.fetch;
  const realNow = Date.now;
  db.install();
  if (now !== undefined) Date.now = () => now;
  process.env.CRON_SECRET = 'secret';
  process.env.SUPABASE_URL = 'https://example.test';
  process.env.SUPABASE_SERVICE_ROLE_KEY = 'srv';
  const res = makeRes();
  try {
    await AC({ headers: { authorization: 'Bearer secret' }, body: { action: action } }, res);
  } finally {
    global.fetch = realFetch;
    Date.now = realNow;
  }
  return res.out;
}

// ── 1. the canonical form and the digest, no fake needed ───────────────────
section('1. the canonical form IS the mechanism');
t('key order does not change the digest', () => {
  assert.strictEqual(AC.canonical({ a: 1, b: 2 }), AC.canonical({ b: 2, a: 1 }));
});
t('...recursively, or a nested detail object would', () => {
  assert.strictEqual(AC.canonical({ d: { y: 1, x: 2 } }), AC.canonical({ d: { x: 2, y: 1 } }));
});
t('WHITESPACE INSIDE A STRING IS A DIFFERENT ROW -- nothing is normalised', () => {
  assert.notStrictEqual(AC.canonical({ a: 'x y' }), AC.canonical({ a: 'x  y' }));
});
t('null and the string "null" do not collide', () => {
  assert.notStrictEqual(AC.canonical({ a: null }), AC.canonical({ a: 'null' }));
});
t('the digest folds in the previous one, or the chain is not a chain', () => {
  const rows = [row('a', D0)];
  assert.notStrictEqual(AC.digestOf('p1', rows), AC.digestOf('p2', rows));
});
t('row ORDER does not change the digest -- it is sorted, not taken as given', () => {
  const a = [row('a', D0 + 1), row('b', D0 + 2)];
  assert.strictEqual(AC.digestOf('p', a), AC.digestOf('p', a.slice().reverse()));
});
t('...and the tiebreak is the id, so identical timestamps are still ordered', () => {
  const a = [row('a', D0), row('b', D0)];
  assert.strictEqual(AC.digestOf('p', a), AC.digestOf('p', a.slice().reverse()));
});
t('ADDING A ROW CHANGES THE DIGEST -- the whole point', () => {
  const a = [row('a', D0)];
  assert.notStrictEqual(AC.digestOf('p', a), AC.digestOf('p', a.concat([row('b', D0 + 1)])));
});
t('CHANGING A ROW CHANGES THE DIGEST', () => {
  assert.notStrictEqual(AC.digestOf('p', [row('a', D0)]),
                        AC.digestOf('p', [row('a', D0, { role: 'admin' })]));
});
t('dayStart is UTC, not the server\'s timezone', () => {
  assert.strictEqual(AC.dayStart(Date.UTC(2026, 8, 10, 23, 59, 59)), Date.UTC(2026, 8, 10));
});

// ── 2. the gate ────────────────────────────────────────────────────────────
section('2. cron-only');
t('a wrong bearer is refused', async () => {
  process.env.CRON_SECRET = 'secret';
  const res = makeRes();
  await AC({ headers: { authorization: 'Bearer nope' }, body: {} }, res);
  assert.strictEqual(res.out.code, 401);
});
t('no CRON_SECRET configured refuses rather than running open', async () => {
  const keep = process.env.CRON_SECRET;
  delete process.env.CRON_SECRET;
  const res = makeRes();
  await AC({ headers: { authorization: 'Bearer x' }, body: {} }, res);
  assert.strictEqual(res.out.code, 500);
  process.env.CRON_SECRET = keep;
});

// ── 3. checkpointing only CLOSED windows ───────────────────────────────────
section('3. a window is checkpointed only once it has closed');
t('three closed days produce three checkpoints', async () => {
  const db = makeDb({ audit: { sairnlaw_audit_log: [row('a', D0 + 1), row('b', D0 + DAY + 1)] } });
  const out = await call(db, 'checkpoint', D0 + 3 * DAY + 5000);
  assert.strictEqual(out.code, 200);
  const law = db.checkpoints.filter((c) => c.audit_table === 'sairnlaw_audit_log');
  assert.strictEqual(law.length, 3, 'expected days 10, 11, 12 -- got ' + law.length);
});
t('TODAY IS NOT CHECKPOINTED -- an open window would be hashed mid-flight', async () => {
  const db = makeDb({ audit: { sairnlaw_audit_log: [row('a', D0 + 1)] } });
  await call(db, 'checkpoint', D0 + 2 * DAY + 5000);
  const ends = db.checkpoints.filter((c) => c.audit_table === 'sairnlaw_audit_log')
    .map((c) => c.window_end);
  assert.ok(ends.indexOf(iso(D0 + 3 * DAY)) === -1, 'the open day was checkpointed');
});
t('the first link is the genesis string, not an empty one', async () => {
  const db = makeDb({ audit: { sairnlaw_audit_log: [row('a', D0 + 1)] } });
  await call(db, 'checkpoint', D0 + 2 * DAY);
  assert.strictEqual(db.checkpoints[0].prev_digest, AC.GENESIS);
});
// ── THE ARM ABOVE IS SELF-REFERENTIAL AND THESE TWO ARE NOT ────────────────
// Added 2026-09-16, after a negative control set GENESIS to '' and this suite
// stayed GREEN. It compares what was written against AC.GENESIS, so changing
// the constant moves the assertion with it -- the fixture-regenerated shape
// (PR 1.1): the tripwire now asserts that the current behaviour equals the
// current behaviour. It is kept, because it is still the right arm for "the
// value that was written is the genesis one"; what it cannot do is say WHICH
// value that is, or that the distinction survives.
t('GENESIS is a specific non-empty literal, pinned HERE rather than read from '
  + 'the module it is meant to constrain', () => {
    assert.strictEqual(AC.GENESIS, 'genesis:sairn-audit-checkpoint:v1');
    assert.ok(AC.GENESIS.length > 0);
  });
t('CONTROL: a stored prev_digest of "" is CHAIN_BROKEN, not a genesis link -- '
  + 'which is the whole reason the constant is a named string', async () => {
    // A prev_digest that was LOST or never set arrives as an empty string. If
    // GENESIS were '', that row would verify as a legitimate first link and a
    // broken chain would read as a new one. This is the behavioural half the
    // arm above cannot reach.
    const db = makeDb({ audit: { sairnlaw_audit_log: [row('a', D0 + 1)] } });
    await call(db, 'checkpoint', D0 + DAY + 5000);
    const law = db.checkpoints.filter((c) => c.audit_table === 'sairnlaw_audit_log');
    assert.strictEqual(law.length, 1, 'fixture did not produce the one checkpoint');
    law[0].prev_digest = '';
    const out = await call(db, 'verify', D0 + DAY + 5000);
    const rep = (out.body.results || []).find((x) => x.table === 'sairnlaw_audit_log');
    assert.ok(rep, 'no report for the table: ' + JSON.stringify(out.body));
    assert.strictEqual(rep.ok, false, 'an empty prev_digest verified CLEAN');
    assert.strictEqual(rep.kind, 'CHAIN_BROKEN', JSON.stringify(rep));
  });
t('each checkpoint chains onto the one before it', async () => {
  const db = makeDb({ audit: { sairnlaw_audit_log: [row('a', D0 + 1), row('b', D0 + DAY + 1)] } });
  await call(db, 'checkpoint', D0 + 3 * DAY);
  const law = db.checkpoints.filter((c) => c.audit_table === 'sairnlaw_audit_log');
  for (let i = 1; i < law.length; i++) {
    assert.strictEqual(law[i].prev_digest, law[i - 1].digest, 'link ' + i + ' is not chained');
  }
});
// ── AND ACROSS RUNS, WHICH IS THE ONLY WAY IT EVER RUNS ────────────────────
// Added 2026-09-16, after a negative control replaced
// `let prev = last ? last.digest : GENESIS` with `let prev = GENESIS` and this
// suite stayed GREEN. Every chain arm above drives ONE invocation, where the
// loop carries `prev` in a local and `last` is never consulted -- so the
// resume-from-the-last-checkpoint path, which is what the daily cron does on
// every day but the first, had no arm at all. The mutation is invisible on day
// one and breaks the chain on day two, permanently, with no UPDATE grant to
// repair it.
t('A SECOND RUN RESUMES FROM THE STORED LAST DIGEST, not from genesis -- the '
  + 'path the cron takes every day after the first', async () => {
    const db = makeDb({ audit: { sairnlaw_audit_log: [row('a', D0 + 1), row('b', D0 + DAY + 1)] } });
    await call(db, 'checkpoint', D0 + DAY + 5000);       // day 0 only
    const first = db.checkpoints.filter((c) => c.audit_table === 'sairnlaw_audit_log');
    assert.strictEqual(first.length, 1, 'fixture did not close exactly one window');
    await call(db, 'checkpoint', D0 + 2 * DAY + 5000);   // day 1, a SEPARATE run
    const law = db.checkpoints.filter((c) => c.audit_table === 'sairnlaw_audit_log');
    assert.strictEqual(law.length, 2, 'the second run wrote ' + (law.length - 1));
    assert.notStrictEqual(law[1].prev_digest, AC.GENESIS,
      'the second run started a NEW chain from genesis, so the link to day 0 is gone');
    assert.strictEqual(law[1].prev_digest, law[0].digest,
      'the second run did not chain onto the stored last digest');
  });
t('...and the chain the second run produced VERIFIES, so the arm above is not '
  + 'just asserting a field it also wrote', async () => {
    const db = makeDb({ audit: { sairnlaw_audit_log: [row('a', D0 + 1), row('b', D0 + DAY + 1)] } });
    await call(db, 'checkpoint', D0 + DAY + 5000);
    await call(db, 'checkpoint', D0 + 2 * DAY + 5000);
    const out = await call(db, 'verify', D0 + 2 * DAY + 5000);
    const rep = (out.body.results || []).find((x) => x.table === 'sairnlaw_audit_log');
    assert.ok(rep, 'no report for the table: ' + JSON.stringify(out.body));
    assert.strictEqual(rep.ok, true, JSON.stringify(rep));
    assert.strictEqual(rep.checkpoints, 2);
  });
t('AN EMPTY TABLE WRITES NOTHING -- a digest over nothing is a permanent lie', async () => {
  const db = makeDb({ audit: { sairnlaw_audit_log: [] } });
  const out = await call(db, 'checkpoint', D0 + 3 * DAY);
  assert.strictEqual(db.checkpoints.length, 0);
  assert.ok(/no audit rows yet/.test(JSON.stringify(out.body)));
});

// ── 4. THE CONTROL ─────────────────────────────────────────────────────────
section('4. the control -- a backdated INSERT must be found');
t('an untouched table verifies CLEAN', async () => {
  const db = makeDb({ audit: { sairnlaw_audit_log: [row('a', D0 + 1)] } });
  await call(db, 'checkpoint', D0 + 2 * DAY);
  const out = await call(db, 'verify', D0 + 2 * DAY);
  assert.strictEqual(out.body.ok, true, JSON.stringify(out.body));
});
t('A BACKDATED ROW INSERTED INTO A CHECKPOINTED WINDOW IS FOUND', async () => {
  const db = makeDb({ audit: { sairnlaw_audit_log: [row('a', D0 + 1)] } });
  await call(db, 'checkpoint', D0 + 2 * DAY);
  // the forgery: a sign-in that never happened, dated inside a closed window
  db.audit.sairnlaw_audit_log.push(row('forged', D0 + 2, { employee_id: 'attacker' }));
  const out = await call(db, 'verify', D0 + 2 * DAY);
  assert.strictEqual(out.body.ok, false);
  const bad = out.body.results.filter((r) => r.ok === false)[0];
  assert.strictEqual(bad.kind, 'WINDOW_CHANGED');
  assert.strictEqual(bad.window_end, iso(D0 + DAY), 'it must name WHICH window');
});
t('...and it says the row count GREW, which is what makes it an insertion', async () => {
  const db = makeDb({ audit: { sairnlaw_audit_log: [row('a', D0 + 1)] } });
  await call(db, 'checkpoint', D0 + 2 * DAY);
  db.audit.sairnlaw_audit_log.push(row('forged', D0 + 2));
  const out = await call(db, 'verify', D0 + 2 * DAY);
  const bad = out.body.results.filter((r) => r.ok === false)[0];
  assert.strictEqual(bad.rows_at_checkpoint, 1);
  assert.strictEqual(bad.rows_now, 2);
});
t('A ROW EDITED IN PLACE is the OTHER shape -- same count, changed digest', async () => {
  const db = makeDb({ audit: { sairnlaw_audit_log: [row('a', D0 + 1)] } });
  await call(db, 'checkpoint', D0 + 2 * DAY);
  db.audit.sairnlaw_audit_log[0].role = 'admin';   // impossible via the API; not via the console
  const out = await call(db, 'verify', D0 + 2 * DAY);
  const bad = out.body.results.filter((r) => r.ok === false)[0];
  assert.strictEqual(bad.kind, 'WINDOW_CHANGED');
  assert.strictEqual(bad.rows_now, bad.rows_at_checkpoint,
    'an equal count is the signal that separates an edit from an insertion');
});
t('TAMPERING WITH THE CHECKPOINT TABLE ITSELF is a DIFFERENT finding', async () => {
  const db = makeDb({ audit: { sairnlaw_audit_log: [row('a', D0 + 1), row('b', D0 + DAY + 1)] } });
  await call(db, 'checkpoint', D0 + 3 * DAY);
  const law = db.checkpoints.filter((c) => c.audit_table === 'sairnlaw_audit_log');
  law[1].prev_digest = 'rewritten';
  const out = await call(db, 'verify', D0 + 3 * DAY);
  const bad = out.body.results.filter((r) => r.ok === false)[0];
  assert.strictEqual(bad.kind, 'CHAIN_BROKEN',
    'a rewritten checkpoint must not be reported as the audit rows moving');
});
t('a row added AFTER the last checkpointed window is NOT a finding', async () => {
  const db = makeDb({ audit: { sairnlaw_audit_log: [row('a', D0 + 1)] } });
  await call(db, 'checkpoint', D0 + 2 * DAY);
  db.audit.sairnlaw_audit_log.push(row('legit', D0 + 2 * DAY + 10));  // today, still open
  const out = await call(db, 'verify', D0 + 2 * DAY + 20);
  assert.strictEqual(out.body.ok, true, 'a live write was called tampering');
});

// ── 4b. the DAILY run verifies too, and says how much it verified ──────────
// Vercel's cron sends a GET with no body, so `checkpoint` is what actually runs
// in production. If the verification lived only on the other action it would
// never run at all, and the checkpoint table would be a column of hashes nobody
// had ever seen detect anything.
section('4b. the daily run is also the verifier, within a stated bound');
t('a checkpoint run reports a recent verification alongside it', async () => {
  const db = makeDb({ audit: { sairnlaw_audit_log: [row('a', D0 + 1)] } });
  const out = await call(db, 'checkpoint', D0 + 3 * DAY);
  assert.ok(Array.isArray(out.body.recent_verify), 'the daily run did not verify at all');
  assert.strictEqual(typeof out.body.recent_verify_windows, 'number');
});
t('A TAMPER IS CAUGHT BY THE DAILY RUN, not only by an explicit verify', async () => {
  const db = makeDb({ audit: { sairnlaw_audit_log: [row('a', D0 + 1)] } });
  await call(db, 'checkpoint', D0 + 2 * DAY);
  db.audit.sairnlaw_audit_log.push(row('forged', D0 + 2));
  const out = await call(db, 'checkpoint', D0 + 3 * DAY);
  assert.strictEqual(out.body.ok, false, 'the daily run did not notice the forgery');
  const bad = out.body.recent_verify.filter((r) => r.ok === false)[0];
  assert.strictEqual(bad.kind, 'WINDOW_CHANGED');
});
t('THE BOUND IS REPORTED, never silent -- full is false when it is partial', async () => {
  // 40 days of history against a 14-window bound.
  const rows = [];
  for (let i = 0; i < 40; i++) rows.push(row('r' + i, D0 + i * DAY + 1));
  const db = makeDb({ audit: { sairnlaw_audit_log: rows } });
  const out = await call(db, 'checkpoint', D0 + 41 * DAY);
  const law = out.body.recent_verify.filter((r) => r.table === 'sairnlaw_audit_log')[0];
  assert.strictEqual(law.full, false, 'a bounded check reported itself as a full one');
  assert.ok(law.verified < law.checkpoints, 'verified=' + law.verified + ' of ' + law.checkpoints);
  assert.strictEqual(law.verified, out.body.recent_verify_windows);
});
t('...and an explicit verify IS full, so the bound is escapable', async () => {
  const rows = [];
  for (let i = 0; i < 40; i++) rows.push(row('r' + i, D0 + i * DAY + 1));
  const db = makeDb({ audit: { sairnlaw_audit_log: rows } });
  await call(db, 'checkpoint', D0 + 41 * DAY);
  const out = await call(db, 'verify', D0 + 41 * DAY);
  const law = out.body.results.filter((r) => r.table === 'sairnlaw_audit_log')[0];
  assert.strictEqual(law.full, true);
});
t('a tamper OUTSIDE the bound still breaks the chain walk, which is free', async () => {
  const rows = [];
  for (let i = 0; i < 40; i++) rows.push(row('r' + i, D0 + i * DAY + 1));
  const db = makeDb({ audit: { sairnlaw_audit_log: rows } });
  await call(db, 'checkpoint', D0 + 41 * DAY);
  const law = db.checkpoints.filter((c) => c.audit_table === 'sairnlaw_audit_log');
  law[2].prev_digest = 'rewritten';          // far outside the 14-window bound
  const out = await call(db, 'checkpoint', D0 + 42 * DAY);
  const bad = out.body.recent_verify.filter((r) => r.ok === false)[0];
  assert.ok(bad && bad.kind === 'CHAIN_BROKEN',
    'the bounded run walked past a rewritten link it could have seen for free');
});

// ── 5. the states that are neither clean nor a finding ─────────────────────
section('5. could-not-tell is a third answer');
t('a missing checkpoint table answers NOT_PROVISIONED and names the file', async () => {
  const db = makeDb({ audit: { sairnlaw_audit_log: [row('a', D0 + 1)] },
                      missingCheckpointTable: true });
  const out = await call(db, 'checkpoint', D0 + 2 * DAY);
  assert.strictEqual(out.code, 503);
  assert.strictEqual(out.body.error.code, 'NOT_PROVISIONED');
  assert.ok(/sql\/audit_checkpoint_schema\.sql/.test(out.body.error.message));
});
t('...and says that is not the same as a clean run', async () => {
  const db = makeDb({ audit: { sairnlaw_audit_log: [row('a', D0 + 1)] },
                      missingCheckpointTable: true });
  const out = await call(db, 'checkpoint', D0 + 2 * DAY);
  assert.ok(/not the same as a clean run/.test(out.body.error.message));
});
t('AN INCOMPLETE WINDOW READ REFUSES -- a short digest is not a digest', async () => {
  // Content-Range says 99 rows exist; the fake returns 1. LIVE-RUN CAVEAT: this
  // proves the DECISION, not that PostgREST reports an exact total -- only a
  // real run can confirm that, and `Prefer: count=exact` is what asks for it.
  const db = makeDb({ audit: { sairnlaw_audit_log: [row('a', D0 + 1)] }, shortTotal: 99 });
  const out = await call(db, 'checkpoint', D0 + 2 * DAY);
  assert.strictEqual(out.code, 503);
  assert.strictEqual(out.body.error.code, 'WINDOW_INCOMPLETE');
  assert.strictEqual(db.checkpoints.length, 0, 'it wrote a partial checkpoint anyway');
});

t('A WINDOW WHOSE ROW COUNT IS NOT STATED REFUSES TOO -- the guard must not vanish with its input', async () => {
  // FOUND 2026-09-14 BY AN INDEPENDENT REVIEW OF THIS FILE, by DRIVING the
  // shipped handler rather than re-reading it. The comparison was
  // `total !== null && total !== rows.length`, so a response with NO
  // Content-Range, or `0-0/*`, left `total` null and SKIPPED THE CHECK. Driven
  // with one row of three: `0-0/3` correctly refused, while `0-0/*` and a
  // missing header both returned 200 AND WROTE A CHECKPOINT WITH row_count 1.
  //
  // A vacuous checkpoint that verifies cleanly forever is the outcome this
  // file's own header names as the one it must never produce -- and it arrived
  // through the ABSENCE of the count, not a wrong one.
  for (const mode of ['star', 'none']) {
    const db = makeDb({ audit: { sairnlaw_audit_log: [row('a', D0 + 1)] },
                        countMode: mode });
    const out = await call(db, 'checkpoint', D0 + 2 * DAY);
    assert.strictEqual(out.code, 503, 'countMode=' + mode + ' did not refuse');
    assert.strictEqual(out.body.error.code, 'WINDOW_INCOMPLETE');
    assert.strictEqual(db.checkpoints.length, 0,
      'countMode=' + mode + ': it wrote a checkpoint over an unconfirmed read');
    // AND IT MUST SAY WHICH OF THE TWO FAILURES THIS WAS. The short-count arm
    // alone already refuses here (null !== 1), so without this assertion the
    // test passes on a handler that has no not-stated branch at all and reports
    // `expected: null` -- which reads as a bug in the checkpointer rather than
    // a server that did not answer the question it was asked.
    assert.match(String(out.body.error.detail.why), /no exact Content-Range total/,
      'countMode=' + mode + ': refused, but did not say the count was never stated');
  }
});
t('CONTROL: an exact count still writes -- the guard is not simply always shut', async () => {
  // Without this the arm above passes on a handler that refuses every window,
  // which would be the same as having no checkpoints at all.
  const db = makeDb({ audit: { sairnlaw_audit_log: [row('a', D0 + 1)] },
                      countMode: 'exact' });
  const out = await call(db, 'checkpoint', D0 + 2 * DAY);
  assert.strictEqual(out.code, 200);
  assert.ok(db.checkpoints.length > 0, 'a complete read wrote nothing');
});

// ── 6. the schema says what the code relies on ─────────────────────────────
section('6. the schema and the code agree');
{
  const SQL_RAW = fs.readFileSync(path.join(__dirname, '..', 'sql', 'audit_checkpoint_schema.sql'), 'utf8');
  // ── COMMENT-STRIPPED, AND THE FIRST DRAFT OF THIS FILE GOT IT WRONG ──────
  // The grant assertion matched the HEADER PROSE -- which explains at length
  // that there is no update and no delete -- and reported a correct schema as
  // ungranted. That is the house defect this repo names over and over: grep
  // cannot tell code from text that describes code. Length-preserving so any
  // offset stays true.
  const NL = String.fromCharCode(10);
  const SQL = SQL_RAW.split(NL).map((l) => {
    const i = l.indexOf('--');
    return i === -1 ? l : l.slice(0, i);
  }).join(NL);
  t('no UPDATE or DELETE grant on the checkpoint table', () => {
    assert.ok(!/grant[^;]*\b(update|delete)\b[^;]*sairn_audit_checkpoint/i.test(SQL));
    assert.ok(/revoke update, delete on public\.sairn_audit_checkpoint/i.test(SQL));
  });
  t('anon and authenticated are revoked', () => {
    assert.ok(/revoke all on public\.sairn_audit_checkpoint from anon, authenticated/i.test(SQL));
  });
  t('the uniqueness that stops a second run forking the chain is declared', () => {
    assert.ok(/unique \(audit_table, window_end\)/i.test(SQL));
  });
  t('every table the code checkpoints is allowed by the schema CHECK', () => {
    for (const tbl of AC.TABLES) {
      assert.ok(SQL.indexOf("'" + tbl + "'") !== -1, tbl + ' is not in the schema CHECK');
    }
  });
  t('the verify block is one query per statement with its expected answer', () => {
    assert.ok((SQL.match(/^select /gim) || []).length >= 4);
    // RAW on purpose: this arm's subject is the COMMENT beside each query.
    assert.ok(/Expect/i.test(SQL_RAW));
  });
}

(async () => {
  for (const [name, fn] of queue) {
    if (!fn) { console.log('--- ' + name + ' ---'); continue; }
    try { await fn(); console.log('  ok   ' + name); pass++; }
    catch (e) { console.log('  FAIL ' + name + '\n       ' + (e && e.message)); fail++; }
  }
  console.log('\naudit-checkpoint: ' + pass + ' passed, ' + fail + ' failed');
  if (fail) process.exit(1);
})();
