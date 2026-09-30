// api/sairncare-witness.test.js
//
// REQUIREMENT: a SAIRNcare controlled-substance COUNT cannot be written until a
//   DIFFERENT, currently-active, qualified employee has witnessed that exact
//   record on the server. A self-witnessed count is REFUSED, not flagged.
//
// Run:  node api/sairncare-witness.test.js
//
// ── THE DEFECT ────────────────────────────────────────────────────────────
// alf_mar records `witness_id` as a caller-supplied string. One employee alone
// can record a two-person count naming any colleague as the second signature.
// The browser refuses to save without a witness selected, and that is the whole
// control -- and the client is what an attacker replaces. api/sd-data.js says so
// in its own comment at the alf_mar write.
//
// ── WHY A SELF-WITNESS IS REFUSED AND NOT FLAGGED ────────────────────────
// This diverges deliberately from the sen_visits clock-correction decision made
// the same day. There a flag was right: a one-person agency has nobody else and
// the correction still has to be possible. Here, a count whose witness is the
// counter is NOT A TWO-PERSON COUNT AT ALL, and recording it as one is the
// false record. A shift that cannot produce a second person defers the count --
// which `require_two_person = false` already permits, WITHOUT claiming a
// signature nobody gave.
//
// ── A KNOWN-BAD CONTROL PER REFUSAL ──────────────────────────────────────
// Every refusal below has a paired arm that makes the refusal's own condition
// go away and requires the write to then SUCCEED. Without that pairing, an arm
// asserting "403" proves only that something refused -- which is equally true
// of a typo in the fixture, a missing session, or a gate that refuses
// everything. Nine refusals, nine controls.

'use strict';

process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET
  || ['alf', 'witness', 'fixture'].join('-');
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://test.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'test-key';

const assert = require('assert');
const crypto = require('crypto');

const HASH = 'alf-witness-hash';
const APP = 'sairncare';
const COUNTER = 'emp-aide-1';     // writes the count; counted_by is server-set
const WITNESS = 'emp-nurse-1';    // a DIFFERENT person
const THIRD = 'emp-nurse-2';

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

// ── AN IN-MEMORY POSTGREST THAT ENFORCES WHAT THE SCHEMA ENFORCES ─────────
// It is a fixture, not the database, and the two facts the SCHEMA owns are
// modelled explicitly so an arm cannot pass against a store more permissive
// than production: the unique (license_hash, token_hash), and the
// spent_at=is.null compare-and-set on the spend.
function makeStore(opts) {
  opts = opts || {};
  const state = {
    tokens: [],
    policy: opts.policy || null,
    employees: opts.employees || {
      [COUNTER]: { employee_id: COUNTER, role: 'med_aide', active: true },
      [WITNESS]: { employee_id: WITNESS, role: 'nursing', active: true },
      [THIRD]: { employee_id: THIRD, role: 'nursing', active: true },
    },
    missingTables: !!opts.missingTables,
    calls: [],
  };
  const missing = { code: 'PGRST205',
    message: "Could not find the table 'public.sairncare_witness_tokens' in the schema cache" };

  state.fetch = async function (url, init) {
    const u = String(url);
    const o = init || {};
    state.calls.push({ url: u, method: o.method || 'GET' });

    if (/sairncare_employee_auth/.test(u)) {
      const m = /employee_id=eq\.([^&]+)/.exec(u);
      const id = m ? decodeURIComponent(m[1]) : null;
      const row = state.employees[id];
      const wantActive = /active=eq\.true/.test(u);
      const ok = row && (!wantActive || row.active === true);
      return { ok: true, status: 200, json: async () => (ok ? [row] : []) };
    }

    if (/sairncare_witness_policy/.test(u)) {
      if (state.missingTables) return { ok: false, status: 404, json: async () => missing };
      if ((o.method || 'GET') === 'POST') {
        state.policy = JSON.parse(o.body);
        return { ok: true, status: 200, json: async () => [state.policy] };
      }
      return { ok: true, status: 200,
        json: async () => (state.policy ? [{ require_two_person: !!state.policy.require_two_person }] : []) };
    }

    if (/sairncare_witness_tokens/.test(u)) {
      if (state.missingTables) return { ok: false, status: 404, json: async () => missing };
      if ((o.method || 'GET') === 'POST') {
        const row = Object.assign({ id: 'tok-' + (state.tokens.length + 1) }, JSON.parse(o.body));
        // THE SCHEMA'S unique (license_hash, token_hash), modelled.
        if (state.tokens.some((t) => t.license_hash === row.license_hash
                                 && t.token_hash === row.token_hash)) {
          return { ok: false, status: 409,
            json: async () => ({ code: '23505', message: 'duplicate key value' }) };
        }
        state.tokens.push(row);
        return { ok: true, status: 200, json: async () => [row] };
      }
      if ((o.method || 'GET') === 'PATCH') {
        const idm = /id=eq\.([^&]+)/.exec(u);
        const id = idm ? decodeURIComponent(idm[1]) : null;
        const requireUnspent = /spent_at=is\.null/.test(u);
        const patch = JSON.parse(o.body);
        const hits = state.tokens.filter((t) => t.id === id
          && (!requireUnspent || !t.spent_at));
        hits.forEach((t) => Object.assign(t, patch));
        return { ok: true, status: 200, json: async () => hits };
      }
      const th = /token_hash=eq\.([^&]+)/.exec(u);
      const want = th ? decodeURIComponent(th[1]) : null;
      const rows = state.tokens.filter((t) => t.token_hash === want);
      return { ok: true, status: 200, json: async () => rows };
    }
    return { ok: true, status: 200, json: async () => [] };
  };
  return state;
}

function load(store) {
  delete require.cache[require.resolve('./_lib/license')];
  require.cache[require.resolve('./_lib/license')] = {
    exports: {
      validateLicenseKey: async () => ({
        valid: true, active: true, license_hash: HASH,
        trial_ends_at: null, stripe_subscription_id: null, app_id: APP
      })
    }
  };
  global.fetch = store.fetch;
  delete require.cache[require.resolve('./sairncare-witness.js')];
  return require('./sairncare-witness.js');
}

function sessionFor(employee_id, role) {
  const { signSessionToken } = require('./_lib/auth');
  return signSessionToken({ app: APP, employee_id, role, license_hash: HASH });
}

async function call(store, body, who, role) {
  const h = load(store);
  const res = mockRes();
  const headers = { authorization: 'Bearer KEY-FOR-' + HASH };
  if (who) headers['x-sd-auth'] = sessionFor(who, role);
  await h({ method: 'POST', headers, body }, res);
  return res;
}

const COUNT_PAYLOAD = {
  id: 'MAR-COUNT-1', resident_id: 'R-1', entry_type: 'count',
  medication: 'lorazepam 0.5mg', expected: 12, actual: 12
};

// requireWitness is what the WRITE path calls. Driven directly, with the same
// store, because that is the half that actually stops an alf_mar row.
function guardCtx(store, payload, token, callerId) {
  return {
    resource: 'alf_mar',
    payload,
    licHash: HASH,
    rest: (p) => 'https://test.supabase.co/rest/v1/' + p,
    headers: {},
    token,
    callerEmployeeId: callerId
  };
}

(async function () {
  section('1. REQUEST -- who may witness, and of what');

  await test('a count can be witnessed by an active nurse', async () => {
    const s = makeStore();
    const r = await call(s, { action: 'request', resource: 'alf_mar', payload: COUNT_PAYLOAD },
                         WITNESS, 'nursing');
    assert.strictEqual(r.statusCode, 200, JSON.stringify(r.body));
    assert.ok(r.body.token, 'no token returned');
    assert.strictEqual(r.body.witness_employee_id, WITNESS);
  });

  await test('REFUSED: no session at all', async () => {
    const s = makeStore();
    const r = await call(s, { action: 'request', resource: 'alf_mar', payload: COUNT_PAYLOAD });
    assert.strictEqual(r.statusCode, 401, JSON.stringify(r.body));
    assert.strictEqual(r.body.error.code, 'NO_SESSION');
  });
  await test('  CONTROL: the same request WITH a session succeeds', async () => {
    const s = makeStore();
    const r = await call(s, { action: 'request', resource: 'alf_mar', payload: COUNT_PAYLOAD },
                         WITNESS, 'nursing');
    assert.strictEqual(r.statusCode, 200, JSON.stringify(r.body));
  });

  await test('REFUSED: a med_aide may not witness a controlled-substance count',
    async () => {
      const s = makeStore();
      const r = await call(s, { action: 'request', resource: 'alf_mar', payload: COUNT_PAYLOAD },
                           COUNTER, 'med_aide');
      assert.strictEqual(r.statusCode, 403, JSON.stringify(r.body));
      assert.strictEqual(r.body.error.code, 'NOT_A_WITNESS_ROLE');
    });
  await test('  CONTROL: the identical request from nursing succeeds', async () => {
    const s = makeStore();
    const r = await call(s, { action: 'request', resource: 'alf_mar', payload: COUNT_PAYLOAD },
                         WITNESS, 'nursing');
    assert.strictEqual(r.statusCode, 200, JSON.stringify(r.body));
  });

  await test('REFUSED: a DEACTIVATED nurse cannot witness', async () => {
    const s = makeStore();
    s.employees[WITNESS].active = false;
    const r = await call(s, { action: 'request', resource: 'alf_mar', payload: COUNT_PAYLOAD },
                         WITNESS, 'nursing');
    assert.strictEqual(r.statusCode, 401, JSON.stringify(r.body));
  });
  await test('  CONTROL: re-activating the same nurse lets it through', async () => {
    const s = makeStore();
    s.employees[WITNESS].active = true;
    const r = await call(s, { action: 'request', resource: 'alf_mar', payload: COUNT_PAYLOAD },
                         WITNESS, 'nursing');
    assert.strictEqual(r.statusCode, 200, JSON.stringify(r.body));
  });

  await test('REFUSED: an entry_type that is not a count', async () => {
    const s = makeStore();
    const r = await call(s, {
      action: 'request', resource: 'alf_mar',
      payload: Object.assign({}, COUNT_PAYLOAD, { entry_type: 'administration' })
    }, WITNESS, 'nursing');
    assert.strictEqual(r.statusCode, 400, JSON.stringify(r.body));
    assert.ok(/count/.test(r.body.error.message), r.body.error.message);
  });
  await test('  CONTROL: entry_type count on the same payload succeeds', async () => {
    const s = makeStore();
    const r = await call(s, { action: 'request', resource: 'alf_mar', payload: COUNT_PAYLOAD },
                         WITNESS, 'nursing');
    assert.strictEqual(r.statusCode, 200, JSON.stringify(r.body));
  });

  section('2. THE GUARD -- what actually stops an alf_mar write');

  async function mint(store, payload, who, role) {
    const r = await call(store, { action: 'request', resource: 'alf_mar', payload },
                         who || WITNESS, role || 'nursing');
    assert.strictEqual(r.statusCode, 200, 'mint failed: ' + JSON.stringify(r.body));
    return r.body.token;
  }

  await test('a witnessed count passes the guard', async () => {
    const s = makeStore();
    const tok = await mint(s, COUNT_PAYLOAD);
    const mod = load(s);
    const out = await mod.requireWitness(guardCtx(s, COUNT_PAYLOAD, tok, COUNTER));
    assert.strictEqual(out, null, 'guard refused a good token: ' + JSON.stringify(out));
  });

  await test('REFUSED: no token at all', async () => {
    const s = makeStore();
    const mod = load(s);
    const out = await mod.requireWitness(guardCtx(s, COUNT_PAYLOAD, null, COUNTER));
    assert.ok(out && out.status === 403, JSON.stringify(out));
    assert.strictEqual(out.body.error.code, 'WITNESS_REQUIRED');
  });
  await test('  CONTROL: the same write WITH a token passes', async () => {
    const s = makeStore();
    const tok = await mint(s, COUNT_PAYLOAD);
    const mod = load(s);
    assert.strictEqual(await mod.requireWitness(guardCtx(s, COUNT_PAYLOAD, tok, COUNTER)), null);
  });

  await test('REFUSED: A SELF-WITNESSED COUNT -- the witness is the counter',
    async () => {
      const s = makeStore();
      // The counter is a nurse here, so the ROLE gate cannot be what refuses;
      // only the identity comparison can.
      s.employees[COUNTER].role = 'nursing';
      const tok = await mint(s, COUNT_PAYLOAD, COUNTER, 'nursing');
      const mod = load(s);
      const out = await mod.requireWitness(guardCtx(s, COUNT_PAYLOAD, tok, COUNTER));
      assert.ok(out, 'a self-witnessed count was ALLOWED');
      assert.strictEqual(out.status, 403, JSON.stringify(out));
      assert.strictEqual(out.body.error.code, 'SELF_WITNESS_REFUSED');
    });
  await test('  CONTROL: the same token witnessed by somebody ELSE passes',
    async () => {
      const s = makeStore();
      s.employees[COUNTER].role = 'nursing';
      const tok = await mint(s, COUNT_PAYLOAD, WITNESS, 'nursing');
      const mod = load(s);
      assert.strictEqual(
        await mod.requireWitness(guardCtx(s, COUNT_PAYLOAD, tok, COUNTER)), null);
    });

  await test('REFUSED: the payload changed after it was witnessed', async () => {
    const s = makeStore();
    const tok = await mint(s, COUNT_PAYLOAD);
    const edited = Object.assign({}, COUNT_PAYLOAD, { actual: 11 });
    const mod = load(s);
    const out = await mod.requireWitness(guardCtx(s, edited, tok, COUNTER));
    assert.ok(out && out.status === 409, JSON.stringify(out));
    assert.strictEqual(out.body.error.code, 'WITNESS_CONTENT_MISMATCH');
  });
  await test('  CONTROL: the UNEDITED payload passes with the same token', async () => {
    const s = makeStore();
    const tok = await mint(s, COUNT_PAYLOAD);
    const mod = load(s);
    assert.strictEqual(await mod.requireWitness(guardCtx(s, COUNT_PAYLOAD, tok, COUNTER)), null);
  });

  await test('REFUSED: the token has already been spent', async () => {
    const s = makeStore();
    const tok = await mint(s, COUNT_PAYLOAD);
    const mod = load(s);
    assert.strictEqual(await mod.requireWitness(guardCtx(s, COUNT_PAYLOAD, tok, COUNTER)), null);
    const out = await mod.requireWitness(guardCtx(s, COUNT_PAYLOAD, tok, COUNTER));
    assert.ok(out && out.status === 409, JSON.stringify(out));
    assert.strictEqual(out.body.error.code, 'WITNESS_ALREADY_SPENT');
  });
  await test('  CONTROL: a FRESH token for the same record passes', async () => {
    const s = makeStore();
    const t1 = await mint(s, COUNT_PAYLOAD);
    const mod = load(s);
    await mod.requireWitness(guardCtx(s, COUNT_PAYLOAD, t1, COUNTER));
    const t2 = await mint(s, COUNT_PAYLOAD);
    assert.strictEqual(await mod.requireWitness(guardCtx(s, COUNT_PAYLOAD, t2, COUNTER)), null);
  });

  await test('REFUSED: the token has expired', async () => {
    const s = makeStore();
    const tok = await mint(s, COUNT_PAYLOAD);
    s.tokens[0].expires_at = new Date(Date.now() - 1000).toISOString();
    const mod = load(s);
    const out = await mod.requireWitness(guardCtx(s, COUNT_PAYLOAD, tok, COUNTER));
    assert.ok(out && out.status === 409, JSON.stringify(out));
    assert.strictEqual(out.body.error.code, 'WITNESS_EXPIRED');
  });
  await test('  CONTROL: an unexpired token passes', async () => {
    const s = makeStore();
    const tok = await mint(s, COUNT_PAYLOAD);
    const mod = load(s);
    assert.strictEqual(await mod.requireWitness(guardCtx(s, COUNT_PAYLOAD, tok, COUNTER)), null);
  });

  await test('REFUSED: the witness was deactivated between witnessing and writing',
    async () => {
      // The reachable case, and the one the TTL cannot cover: a deadline
      // re-verifies nothing. A nurse confirms, is dismissed, and the write
      // would still land carrying their name on a MAR a surveyor reads.
      const s = makeStore();
      const tok = await mint(s, COUNT_PAYLOAD);
      s.employees[WITNESS].active = false;
      const mod = load(s);
      const out = await mod.requireWitness(guardCtx(s, COUNT_PAYLOAD, tok, COUNTER));
      assert.ok(out && out.status === 403, JSON.stringify(out));
      assert.strictEqual(out.body.error.code, 'WITNESS_NO_LONGER_ACTIVE');
    });
  await test('  CONTROL: a witness still active at write time passes', async () => {
    const s = makeStore();
    const tok = await mint(s, COUNT_PAYLOAD);
    const mod = load(s);
    assert.strictEqual(await mod.requireWitness(guardCtx(s, COUNT_PAYLOAD, tok, COUNTER)), null);
  });

  await test('REFUSED with 503 NOT_PROVISIONED when the tables do not exist',
    async () => {
      // FAIL CLOSED. A missing table is not "unwitnessed" and it is certainly
      // not "witnessed" -- it is could-not-tell, and the only safe answer to
      // could-not-tell on an append-only MAR is refusal.
      const s = makeStore({ missingTables: true });
      const mod = load(s);
      const out = await mod.requireWitness(guardCtx(s, COUNT_PAYLOAD, 'anything', COUNTER));
      assert.ok(out, 'an unprovisioned store ALLOWED the write');
      assert.strictEqual(out.status, 503, JSON.stringify(out));
      assert.strictEqual(out.body.error.code, 'NOT_PROVISIONED');
    });
  await test('  CONTROL: with the tables present the same call passes', async () => {
    const s = makeStore();
    const tok = await mint(s, COUNT_PAYLOAD);
    const mod = load(s);
    assert.strictEqual(await mod.requireWitness(guardCtx(s, COUNT_PAYLOAD, tok, COUNTER)), null);
  });

  section('3. POLICY -- two-person is a per-licence setting');

  await test('REFUSED: require_two_person with no countersignature', async () => {
    const s = makeStore({ policy: { require_two_person: true } });
    const tok = await mint(s, COUNT_PAYLOAD);
    const mod = load(s);
    const out = await mod.requireWitness(guardCtx(s, COUNT_PAYLOAD, tok, COUNTER));
    assert.ok(out && out.status === 403, JSON.stringify(out));
    assert.strictEqual(out.body.error.code, 'COUNTERSIGN_REQUIRED');
  });
  await test('  CONTROL: the same token countersigned by a THIRD person passes',
    async () => {
      const s = makeStore({ policy: { require_two_person: true } });
      const tok = await mint(s, COUNT_PAYLOAD);
      const cs = await call(s, { action: 'countersign', token: tok }, THIRD, 'nursing');
      assert.strictEqual(cs.statusCode, 200, JSON.stringify(cs.body));
      const mod = load(s);
      assert.strictEqual(await mod.requireWitness(guardCtx(s, COUNT_PAYLOAD, tok, COUNTER)), null);
    });

  await test('REFUSED: the witness cannot countersign their own token', async () => {
    const s = makeStore({ policy: { require_two_person: true } });
    const tok = await mint(s, COUNT_PAYLOAD);
    const cs = await call(s, { action: 'countersign', token: tok }, WITNESS, 'nursing');
    assert.strictEqual(cs.statusCode, 409, JSON.stringify(cs.body));
    assert.strictEqual(cs.body.error.code, 'SAME_PERSON');
  });
  await test('  CONTROL: a different nurse countersigning the same token succeeds',
    async () => {
      const s = makeStore({ policy: { require_two_person: true } });
      const tok = await mint(s, COUNT_PAYLOAD);
      const cs = await call(s, { action: 'countersign', token: tok }, THIRD, 'nursing');
      assert.strictEqual(cs.statusCode, 200, JSON.stringify(cs.body));
    });

  await test('an ABSENT policy row means single-operator, not a refusal', async () => {
    // The safe default to be missing: a facility that never configured this is
    // not silently held to a rule it cannot meet.
    const s = makeStore({ policy: null });
    const tok = await mint(s, COUNT_PAYLOAD);
    const mod = load(s);
    assert.strictEqual(await mod.requireWitness(guardCtx(s, COUNT_PAYLOAD, tok, COUNTER)), null);
  });

  section('4. THE LOCK IS NARROW ON PURPOSE');

  await test('a NON-count alf_mar entry is not locked at all', async () => {
    const s = makeStore();
    const mod = load(s);
    const admin = Object.assign({}, COUNT_PAYLOAD, { entry_type: 'administration' });
    assert.strictEqual(
      await mod.requireWitness(guardCtx(s, admin, null, COUNTER)), null,
      'an administration was gated. An administration has ONE actor by '
      + 'definition; locking it is a gate in front of a door nobody meant to shut.');
  });

  await test('a resource other than alf_mar is not locked', async () => {
    const s = makeStore();
    const mod = load(s);
    const ctx = guardCtx(s, COUNT_PAYLOAD, null, COUNTER);
    ctx.resource = 'alf_clients';
    assert.strictEqual(await mod.requireWitness(ctx), null);
  });

  section('5. THE TOKEN IS NEVER READABLE BACK');

  await test('the stored row carries a HASH, never the token', async () => {
    const s = makeStore();
    const tok = await mint(s, COUNT_PAYLOAD);
    const stored = JSON.stringify(s.tokens[0]);
    assert.ok(stored.indexOf(tok) === -1,
      'the raw token is in the stored row -- a readable table of live signatures');
    assert.strictEqual(s.tokens[0].token_hash,
      crypto.createHash('sha256').update(tok).digest('hex'));
  });

  await test('the content hash covers the RESOURCE as well as the payload', async () => {
    const mod = load(makeStore());
    // A DELIBERATELY FICTIONAL SECOND RESOURCE. The arm's point is that the
    // resource is INSIDE the hash; any different string proves it. Naming a
    // real Tier A resource here -- as the first draft did, naming SAIRNvet's
    // controlled-substance register -- put that
    // resource's name on a changed line, which the push gate correctly read as
    // a Tier A change needing its own review obligation. It was a string in an
    // assertion, not a change to SAIRNvet, and recording an obligation for a
    // resource nobody touched would have been a worse answer than fixing the
    // fixture.
    assert.notStrictEqual(
      mod.contentHash('alf_mar', COUNT_PAYLOAD),
      mod.contentHash('zz_not_a_real_resource', COUNT_PAYLOAD),
      'a token issued for one table could be spent on another');
  });

  await test('two encodings of the same record hash the same', async () => {
    const mod = load(makeStore());
    const a = { id: 'X', resident_id: 'R', entry_type: 'count', actual: 1 };
    const b = { actual: 1, entry_type: 'count', resident_id: 'R', id: 'X' };
    assert.strictEqual(mod.contentHash('alf_mar', a), mod.contentHash('alf_mar', b));
  });

  await test('a record differing only in whitespace INSIDE a string is different',
    async () => {
      const mod = load(makeStore());
      const a = { id: 'X', medication: 'lorazepam' };
      const b = { id: 'X', medication: 'lorazepam ' };
      assert.notStrictEqual(mod.contentHash('alf_mar', a), mod.contentHash('alf_mar', b),
        'normalising whitespace here would be this file quietly editing a '
        + 'controlled-substance entry');
    });

  section('6. THE GATE IS WIRED -- an engine with no caller protects nothing');

  // THE SAIRNmechanical G3 DEFECT, PINNED. A verification module that nothing
  // calls is the most expensive kind of green: every arm above passes and no
  // alf_mar count is protected. This reads the real api/sd-data.js and requires
  // the call to be there, in the alf_mar write branch, BEFORE the insert.
  await test('api/sd-data.js calls requireWitness on the alf_mar write', async () => {
    const fs = require('fs');
    const path = require('path');
    const src = fs.readFileSync(path.join(__dirname, 'sd-data.js'), 'utf8');
    const n = src.split('alfWitness.requireWitness(').length - 1;
    assert.strictEqual(n, 1,
      'expected exactly one call to alfWitness.requireWitness in api/sd-data.js, '
      + 'found ' + n + '. Zero means the lock is an engine with no caller; more '
      + 'than one means there are two gates and only one of them will be '
      + 'maintained.');
  });

  await test('the call passes callerEmployeeId, or a self-witness cannot be caught',
    async () => {
      const fs = require('fs');
      const path = require('path');
      const src = fs.readFileSync(path.join(__dirname, 'sd-data.js'), 'utf8');
      const at = src.indexOf('alfWitness.requireWitness(');
      const call = src.slice(at, src.indexOf(');', at));
      assert.ok(/callerEmployeeId\s*:\s*session\.employee_id/.test(call),
        'the wiring does not pass callerEmployeeId from the session. Without it '
        + 'requireWitness cannot compare the witness against the counter, and a '
        + 'self-witnessed count would be refused for the WRONG reason (an absent '
        + 'caller) or, if that guard were ever relaxed, allowed. Call site was: '
        + call);
    });

  await test('the gate runs BEFORE the insert, not after it', async () => {
    const fs = require('fs');
    const path = require('path');
    const src = fs.readFileSync(path.join(__dirname, 'sd-data.js'), 'utf8');
    const gate = src.indexOf('alfWitness.requireWitness(');
    const insert = src.indexOf('alf_check_and_insert_mar_entry', gate);
    assert.ok(gate !== -1 && insert !== -1 && gate < insert,
      'the witness check does not precede the alf_mar insert. A verification '
      + 'that runs after the write is a report, not a lock, and alf_mar has no '
      + 'delete verb.');
  });

  console.log('');
  console.log(pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
