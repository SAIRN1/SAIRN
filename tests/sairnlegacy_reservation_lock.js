// tests/sairnlegacy_reservation_lock.js
//
// Run:  node tests/sairnlegacy_reservation_lock.js
//
// SAIRNLEGACY OWNS 36 RESOURCES -- THE SECOND MOST ON THE PLATFORM -- AND HAD
// ONE TEST FILE.
//
// docs/MASTER-PLAN.md gate 3 measured it at 36 resources, 1 suite, 1 traced,
// 0 fault probes: the worst coverage-to-resources ratio of any app holding Tier
// A data. Its Tier A list is leg_certs, leg_invoices and leg_preneed -- pre-need
// funeral money, which is a trust product a family pays into years before the
// service.
//
// ── WHAT THIS SUITE IS AIMED AT, AND WHY IT IS THAT AND NOT A SWEEP ─────────
// The one genuinely load-bearing control in this app's server path is the
// RESERVATION LOCK on leg_merch_units, and NOTHING EXERCISED IT. Its own
// comment in api/sd-data.js states the consequence:
//
//     "two staff on two devices, each holding a stale local copy showing
//      'Available', could otherwise both pass their own client-side check and
//      both upsert 'Reserved' for different cases ... (real risk: the same
//      physical casket/urn promised to two grieving families)"
//
// It is a narrow, resource-AND-transition-specific gate: `Reserved` takes an
// atomic conditional PATCH, and every other transition -- release, mark Sold,
// catalogue and unit creation -- deliberately keeps blind-upsert semantics. A
// suite that only checked "reserving works" would pass just as happily on a
// gate widened to every transition, which would turn ordinary saves into 409s.
// So the NARROWNESS is asserted, not just the lock.
//
// THE CLIENT HALF HAS BEEN FIXED TWICE AND TESTED NEVER, which is the sharper
// half. `confirmReserve()` writes optimistically, then rolls back on 409 --
// and the rollback:
//
//   * RE-READS rather than writing back the pre-await snapshot (fixed
//     2026-09-02). Writing back `list` would silently undo every other change
//     made to leg_merch_units while the request was in flight -- a release, a
//     mark-sold, or another unit's reservation on the same device.
//   * only rolls back IF THE RESERVATION IS STILL OURS. If something else
//     changed the unit during the await, that newer state is more correct and
//     clobbering it is the same bug in the other direction.
//
// Both of those are one-line conditions guarding a money-and-grief path, and
// both are invisible in review. They are driven here.
//
// Gate 4 for this vertical is tests/sairnlegacy_fault_probe.py, which plants
// real defects in sairnlegacy.html and in the handler and proves this suite
// refuses them.

'use strict';
const assert = require('assert');
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ROOT = path.join(__dirname, '..');
// Assembled rather than written as a literal assignment, so this file carries
// nothing credential-shaped -- the convention tests/app_session_isolation.js
// uses. Set BEFORE api/_lib/auth.js is required, which reads it at module load.
process.env[['SD', 'AUTH', 'SECRET'].join('_')] =
  ['sairnlegacy', 'reservation', 'fixture', String(process.pid)].join('-');

const reg = require(path.join(ROOT, 'api/_resources'));
const LEG = require(path.join(ROOT, 'api/_resources/sairnlegacy.js'));
const HANDLER = path.join(ROOT, 'api/sd-data.js');
const HTML = fs.readFileSync(process.env.LEG_HTML
  || path.join(ROOT, 'sairnlegacy.html'), 'utf8').replace(/\r\n/g, '\n');

let n = 0;
function ok(cond, label) { assert.ok(cond, label); n++; console.log('  ok   ' + label); }
function section(s) { console.log('\n' + s); }

const LICENSE_KEY = 'k';
const LIC_HASH = crypto.createHash('sha256').update(LICENSE_KEY).digest('hex');

function loadHandler() {
  delete require.cache[require.resolve(HANDLER)];
  return require(HANDLER);
}

// Drives the REAL handler and RECORDS EVERY UPSTREAM CALL. The URLs and methods
// are the assertion: "the lock is atomic" is a claim about the request that goes
// to Postgres, and a suite that only read the response code could not tell an
// atomic conditional PATCH from a read-then-write that happens to answer 409.
async function call(handler, opts) {
  const out = { code: null, body: null, calls: [] };
  const res = { status(c) { out.code = c; return res; }, json(b) { out.body = b; return res; },
                setHeader() {} };
  const names = { url: ['SUPABASE', 'URL'].join('_'),
                  key: ['SUPABASE', 'SERVICE', 'ROLE', 'KEY'].join('_') };
  const envURL = process.env[names.url], envKey = process.env[names.key];
  const realFetch = global.fetch;
  process.env[names.url] = 'https://stub.invalid';
  process.env[names.key] = ['stub', 'fixture', 'value'].join('-');
  let first = true;
  const replies = (opts.replies || []).slice();
  global.fetch = async (url, init) => {
    if (first) {
      first = false;
      // The licence row. app_id null = the documented unattributable fallback.
      return { ok: true, status: 200, json: async () => [{ status: 'active', app_id: null }] };
    }
    out.calls.push({ url: String(url), method: (init && init.method) || 'GET',
                     body: (init && init.body) || null,
                     prefer: (init && init.headers && init.headers.Prefer) || null });
    const r = replies.length ? replies.shift() : { status: 200, rows: [] };
    return { ok: r.status >= 200 && r.status < 300, status: r.status,
             json: async () => (r.rows === undefined ? [] : r.rows) };
  };
  try {
    await handler({ method: 'POST',
                    headers: { authorization: 'Bearer ' + LICENSE_KEY },
                    body: { action: opts.action, resource: opts.resource,
                            app_id: opts.app_id === undefined ? 'sairnlegacy' : opts.app_id,
                            payload: opts.payload === undefined ? {} : opts.payload } }, res);
  } finally {
    global.fetch = realFetch;
    if (envURL === undefined) delete process.env[names.url]; else process.env[names.url] = envURL;
    if (envKey === undefined) delete process.env[names.key]; else process.env[names.key] = envKey;
  }
  return out;
}

// ── THE POSTURE, HAND-WRITTEN ───────────────────────────────────────────────
// Read from api/sd-data.js's LEG_RESOURCES branch on 2026-09-14. NOT ONE of the
// 36 requires an employee session: the branch is licence-only for both read and
// write, while api/leg-auth.js exists, so a session is available to bind to and
// nothing records why it is not bound. That is an open finding in
// docs/SAIRN-OPEN-WORK-INDEX.md and Michael's decision, not a thing to change
// inside a test -- so it is MEASURED here, which makes a gate that silently
// appears fail as loudly as one that disappears.
const SESSION_GATED = [];

console.log('SAIRNlegacy: the reservation lock, both halves, and the posture of '
            + 'all 36\n');

(async () => {
  const h = loadHandler();

  // ── 0. THE FIXTURE ────────────────────────────────────────────────────────
  section('0. the registry and the fixture are real');
  ok(LEG.resources.length === 36,
     'the registry still owns 36 SAIRNlegacy resources -- ' + LEG.resources.length);
  const notOwned = LEG.resources.filter((r) => reg.OWNER_BY_RESOURCE[r] !== 'sairnlegacy');
  ok(notOwned.length === 0,
     'and every one is owned by sairnlegacy in the shared registry'
     + (notOwned.length ? ' -- NOT: ' + notOwned.join(', ') : ''));
  ok(LEG.resources.indexOf('leg_merch_units') !== -1,
     'leg_merch_units -- the resource the lock is on -- is among them');
  ok(['leg_certs', 'leg_invoices', 'leg_preneed'].every((r) => LEG.resources.indexOf(r) !== -1),
     'and so are the three Tier A resources, including leg_preneed');

  // ── 1. THE LOCK IS AN ATOMIC CONDITIONAL WRITE ───────────────────────────
  section('1. reserving is an atomic conditional PATCH, not a read-then-write');
  {
    const r = await call(h, { resource: 'leg_merch_units', action: 'write',
                              payload: { id: 'MU-2', status: 'Reserved',
                                         reserved_for_case_id: 'CS-1' },
                              replies: [{ status: 200, rows: [{ data: { id: 'MU-2', status: 'Reserved' } }] }] });
    ok(r.code === 200, 'a reservation that wins returns 200 -- ' + r.code);
    ok(r.calls.length === 1,
       'and it takes exactly ONE upstream call -- a read-then-write would take '
       + 'two and would not be atomic. Took ' + r.calls.length);
    const c = r.calls[0];
    ok(c.method === 'PATCH',
       'the call is a PATCH, not a POST upsert -- ' + c.method);
    ok(/data->>status=eq\.Available/.test(c.url),
       'and its URL carries the CONDITION data->>status=eq.Available, which is '
       + 'the whole lock: Postgres decides, not the app');
    ok(c.url.indexOf('license_hash=eq.' + LIC_HASH) !== -1,
       '...scoped to this licence, so one funeral home cannot reserve another\'s unit');
    ok(/merch_unit_id=eq\.MU-2/.test(c.url),
       '...and to this unit -- ' + (c.url.split('?')[1] || '').slice(0, 120));
    ok(r.body && r.body.data && r.body.data.status === 'Reserved',
       'and the row Postgres actually wrote is what comes back, not the payload '
       + 'the client sent');
  }

  // ── 2. NOBODY ELSE'S RESERVATION IS OVERWRITTEN ──────────────────────────
  // An empty result from the conditional PATCH means the row was no longer
  // Available. That is the lock firing, and it must be a REFUSAL rather than a
  // 200 with nothing written -- the second of which is the silent failure this
  // platform keeps finding.
  section('2. a lost race is a 409, not a quiet success');
  {
    const r = await call(h, { resource: 'leg_merch_units', action: 'write',
                              payload: { id: 'MU-2', status: 'Reserved',
                                         reserved_for_case_id: 'CS-9' },
                              replies: [{ status: 200, rows: [] }] });
    ok(r.code === 409, 'zero rows matched -> 409, not 200 -- ' + r.code);
    ok(r.body && r.body.error && r.body.error.code === 'ALREADY_RESERVED',
       'and the code is ALREADY_RESERVED, which is what the client branches on');
    const m = (r.body && r.body.error && r.body.error.message) || '';
    // THE MESSAGE IS HONEST ABOUT WHAT IT DOES NOT KNOW. The server cannot tell
    // "somebody else reserved it" from "this device has not finished syncing",
    // and a message that picked one would send a funeral director looking for a
    // colleague who did nothing.
    ok(/already been reserved or sold/.test(m) && /finished syncing/.test(m),
       'and the message names BOTH causes it cannot distinguish rather than '
       + 'guessing one: ' + m.slice(0, 110));
  }

  // ── 3. THE GATE IS NARROW, AND THAT IS DELIBERATE ────────────────────────
  // Every other transition keeps blind-upsert semantics. A gate widened to all
  // of them would turn an ordinary release or mark-sold into a 409 the moment
  // two devices disagreed, which is worse than the problem it solves.
  section('3. every OTHER transition stays a blind upsert');
  {
    for (const status of ['Available', 'Sold', '', undefined]) {
      const payload = { id: 'MU-2' };
      if (status !== undefined) payload.status = status;
      const r = await call(h, { resource: 'leg_merch_units', action: 'write',
                                payload: payload,
                                replies: [{ status: 200, rows: [{ data: payload }] }] });
      const c = r.calls[0] || {};
      ok(r.code === 200 && c.method === 'POST' && /on_conflict=license_hash,merch_unit_id/.test(c.url || ''),
         'status=' + JSON.stringify(status) + ' is an upsert, not a conditional '
         + 'PATCH -- ' + c.method + ' ' + ((c.url || '').split('?')[1] || '').slice(0, 60));
      ok(!/data->>status/.test(c.url || ''),
         '...and carries no status condition at all');
    }
    // CONTROL: and a DIFFERENT resource sending status:'Reserved' must not be
    // caught by the lock. The gate is resource-specific as well as
    // transition-specific, and this is the arm that proves the resource half.
    const other = await call(h, { resource: 'leg_bookings', action: 'write',
                                  payload: { id: 'BK-1', status: 'Reserved' },
                                  replies: [{ status: 200, rows: [{ data: { id: 'BK-1' } }] }] });
    ok(other.code === 200 && (other.calls[0] || {}).method === 'POST',
       'CONTROL: leg_bookings with status Reserved is an ordinary upsert -- the '
       + 'lock is scoped to leg_merch_units');
  }

  // ── 4. THE INVARIANTS EVERY ONE OF THE 36 SHARES ─────────────────────────
  section('4. the generic branch, across all 36 resources');
  {
    let missingId = 0, notProvisionedWrite = 0, honestEmptyRead = 0;
    const odd = [];
    for (const resource of LEG.resources) {
      const a = await call(h, { resource, action: 'write', payload: {} });
      if (a.code === 400 && a.calls.length === 0) missingId += 1;
      else odd.push(resource + ' (no id -> ' + a.code + ')');

      // A table that does not exist yet must be a DISTINGUISHABLE 503, not a
      // 200 the client reads as "saved".
      const b = await call(h, { resource, action: 'write', payload: { id: 'X' },
                                replies: [{ status: 404, rows: [] }] });
      if (b.code === 503 && b.body && b.body.error
          && b.body.error.code === 'NOT_PROVISIONED') notProvisionedWrite += 1;
      else odd.push(resource + ' (unprovisioned write -> ' + b.code + ')');

      // ...and on the READ side the same upstream 404 is an honest EMPTY with
      // provisioned:false, so "nothing saved yet" and "never migrated" are
      // different answers rather than one.
      const c = await call(h, { resource, action: 'read',
                                replies: [{ status: 404, rows: [] }] });
      if (c.code === 200 && c.body && c.body.provisioned === false
          && Array.isArray(c.body.data) && c.body.data.length === 0) honestEmptyRead += 1;
      else odd.push(resource + ' (unprovisioned read -> ' + c.code + ' '
                    + JSON.stringify(c.body && c.body.provisioned) + ')');
    }
    ok(missingId === 36, 'all 36 refuse a write with no payload.id, before any '
       + 'upstream call -- ' + missingId + '/36');
    ok(notProvisionedWrite === 36,
       'all 36 turn an upstream 404 into 503 NOT_PROVISIONED on write -- '
       + notProvisionedWrite + '/36');
    ok(honestEmptyRead === 36,
       'and all 36 turn the SAME upstream 404 into an honest empty read with '
       + 'provisioned:false -- ' + honestEmptyRead + '/36. Two different answers '
       + 'to two different questions is the point');
    ok(odd.length === 0, 'no resource behaved differently: '
       + (odd.slice(0, 5).join('; ') || 'none'));

    // app_id IS SET BY THE SERVER. A client that sends another app's id must not
    // have it stored -- that column is what every cross-app query filters on.
    const forged = await call(h, { resource: 'leg_preneed', action: 'write',
                                   app_id: 'stonedesk',
                                   payload: { id: 'PN-1', amount: 5000 },
                                   replies: [{ status: 200, rows: [{ data: { id: 'PN-1' } }] }] });
    const sent = JSON.parse((forged.calls[0] || {}).body || '{}');
    ok(sent.app_id === 'sairnlegacy',
       'the stored app_id is the server\'s own literal, not the client\'s -- got '
       + JSON.stringify(sent.app_id));
    ok(sent.license_hash === LIC_HASH,
       '...and the licence hash is derived from the bearer token, not sent');
  }

  // ── 5. THE POSTURE OF ALL 36, MEASURED ───────────────────────────────────
  section('5. the session posture, measured against a written table');
  {
    const gated = [];
    for (const resource of LEG.resources) {
      const r = await call(h, { resource, action: 'read',
                                replies: [{ status: 200, rows: [] }] });
      if (r.code !== 200) gated.push(resource + ':' + r.code);
    }
    ok(JSON.stringify(gated) === JSON.stringify(SESSION_GATED),
       'NOT ONE of the 36 requires an employee session to read -- measured, and '
       + 'recorded rather than changed. gated: [' + gated.join(', ') + ']');
    ok(fs.existsSync(path.join(ROOT, 'api/leg-auth.js')),
       'CONTROL: api/leg-auth.js EXISTS, so a session is available to bind to -- '
       + 'which is what makes the line above a finding rather than a fact about '
       + 'an app with no identity');
  }

  // ── 6. THE CLIENT HALF: THE ROLLBACK THAT HAS BEEN FIXED TWICE ───────────
  section('6. confirmReserve() -- the optimistic write and its rollback');
  {
    function grab(sig) {
      const start = HTML.indexOf(sig);
      assert.ok(start > 0, 'not found in sairnlegacy.html: ' + sig);
      let i = HTML.indexOf('{', start + sig.length - 1), depth = 0, q = null;
      for (; i < HTML.length; i++) {
        const c = HTML[i], p = HTML[i - 1];
        if (q) { if (c === q && p !== '\\') q = null; continue; }
        if (c === '"' || c === "'" || c === '`') { q = c; continue; }
        if (c === '/' && HTML[i + 1] === '/') { i = HTML.indexOf('\n', i); continue; }
        if (c === '/' && HTML[i + 1] === '*') { i = HTML.indexOf('*/', i) + 1; continue; }
        if (c === '{') depth++;
        else if (c === '}') { depth--; if (!depth) return HTML.slice(start, i + 1); }
      }
      throw new Error('unterminated: ' + sig);
    }

    // `duringAwait` is the whole point of this section: it runs WHILE the server
    // call is in flight, which is the only way to reproduce a concurrent local
    // change. A fixture that mutates before or after cannot see either bug.
    function ctxFor(units, opts) {
      opts = opts || {};
      const store = { leg_merch_units: JSON.stringify(units),
                      leg_license_key: opts.noLicence ? '' : 'LIC-1' };
      const ctx = {
        console: console,
        toasts: [],
        errs: {},
        store: store,
        mcReserveUnit: opts.unit || 'MU-2',
        APP_ID: 'sairnlegacy',
        DATA_API: 'https://stub.invalid/api/sd-data',
        legLastErr: {},
        localStorage: {
          getItem: (k) => (k in store ? store[k] : null),
          setItem: (k, v) => { store[k] = String(v); },
        },
        JSON: JSON,
        legLocalToday: () => '2026-09-14',
        caseLabel: (id) => 'CASE ' + id,
        rMerch: () => {},
        closeReserveModal: () => {},
        toast: function (m) { ctx.toasts.push(String(m)); },
        $: (id) => ({ value: opts.caseId === undefined ? 'CS-1' : opts.caseId,
                      textContent: '' }),
        fetch: async () => {
          if (opts.duringAwait) opts.duringAwait(ctx);
          if (opts.throwIt) throw new Error('network down');
          return { ok: opts.status === 200, status: opts.status,
                   json: async () => opts.payload };
        },
      };
      ctx.$ = (id) => {
        if (!ctx._els) ctx._els = {};
        if (!ctx._els[id]) {
          ctx._els[id] = { value: id === 'rvcase'
            ? (opts.caseId === undefined ? 'CS-1' : opts.caseId) : '', textContent: '' };
        }
        return ctx._els[id];
      };
      vm.createContext(ctx);
      for (const sig of ['function lgyIsQuotaError(e){', 'function st(k,v){',
                         'function ld(k,d){', 'function merchUnits(){',
                         'function legLicenseKey(){',
                         'function legLastErrText(resource){',
                         'function legLastErrCode(resource){',
                         'function legWriteFailText(resource,fallback){',
                         'async function confirmReserve(){']) {
        vm.runInContext(grab(sig), ctx);
      }
      return ctx;
    }
    const U = (over) => Object.assign({ id: 'MU-2', merch_id: 'MC-1',
                                        unit_serial: 'S-2', status: 'Available',
                                        reserved_for_case_id: '', reserved_at: '',
                                        sold_at: '' }, over || {});
    const unitsOf = (ctx) => JSON.parse(ctx.store.leg_merch_units);
    const unit = (ctx, id) => unitsOf(ctx).find((u) => u.id === id);

    // (a) a stale local copy is refused BEFORE any request.
    {
      const ctx = ctxFor([U({ status: 'Reserved', reserved_for_case_id: 'CS-9' })],
                         { status: 200, payload: { ok: true } });
      await ctx.confirmReserve();
      ok(ctx.toasts.length === 0 && unit(ctx, 'MU-2').reserved_for_case_id === 'CS-9',
         'a unit the local copy already shows as Reserved is refused with no '
         + 'request and no overwrite');
    }

    // (b) the happy path.
    {
      const ctx = ctxFor([U()], { status: 200, payload: { ok: true } });
      await ctx.confirmReserve();
      ok(unit(ctx, 'MU-2').status === 'Reserved',
         'a winning reservation is Reserved locally');
      ok(ctx.toasts.some((t) => /Unit reserved for CASE CS-1/.test(t)),
         '...and the toast names the case rather than saying "saved"');
      ok(Object.keys(ctx.legLastErr).length === 0,
         '...and legLastErr is CLEARED, so a later failure message cannot be '
         + 'left over from this success');
    }

    // (c) 409 -> rolled back.
    {
      const ctx = ctxFor([U()], { status: 409,
                                  payload: { error: { code: 'ALREADY_RESERVED',
                                                      message: 'lost the race' } } });
      await ctx.confirmReserve();
      const u = unit(ctx, 'MU-2');
      ok(u.status === 'Available' && !u.reserved_for_case_id && !u.reserved_at,
         'a 409 rolls the optimistic local write back completely -- status, case '
         + 'and timestamp');
      ok(ctx.toasts.some((t) => /lost the race/.test(t)),
         '...and shows the SERVER\'s message, not a local invention');
    }

    // (d) THE 2026-09-02 FIX. A concurrent change to ANOTHER unit during the
    //     await must survive the rollback. Writing back the pre-await snapshot
    //     would silently undo it.
    {
      const ctx = ctxFor([U(), U({ id: 'MU-3', status: 'Reserved',
                                   reserved_for_case_id: 'CS-7' })], {
        status: 409,
        payload: { error: { code: 'ALREADY_RESERVED', message: 'lost' } },
        duringAwait: (c) => {
          // another staff action on the SAME device, mid-flight: MU-3 released
          const fresh = JSON.parse(c.store.leg_merch_units);
          const other = fresh.find((x) => x.id === 'MU-3');
          other.status = 'Available'; other.reserved_for_case_id = '';
          c.store.leg_merch_units = JSON.stringify(fresh);
        },
      });
      await ctx.confirmReserve();
      ok(unit(ctx, 'MU-2').status === 'Available',
         'the rollback still releases the unit this call owns');
      ok(unit(ctx, 'MU-3').status === 'Available'
         && unit(ctx, 'MU-3').reserved_for_case_id === '',
         'AND the release of MU-3 that happened DURING the await survives -- the '
         + 'rollback re-reads instead of writing back its pre-await snapshot');
    }

    // (e) ...and the other direction: if THIS unit changed during the await, the
    //     newer state is more correct and must not be clobbered.
    {
      const ctx = ctxFor([U()], {
        status: 409,
        payload: { error: { code: 'ALREADY_RESERVED', message: 'lost' } },
        duringAwait: (c) => {
          const fresh = JSON.parse(c.store.leg_merch_units);
          const mine = fresh.find((x) => x.id === 'MU-2');
          mine.status = 'Sold'; mine.sold_at = '2026-09-14';
          c.store.leg_merch_units = JSON.stringify(fresh);
        },
      });
      await ctx.confirmReserve();
      ok(unit(ctx, 'MU-2').status === 'Sold',
         'a unit marked Sold during the await is NOT rolled back to Available -- '
         + 'clobbering newer state is the same bug in the other direction');
    }

    // (f) any OTHER failure records the real reason and says device-only.
    {
      const ctx = ctxFor([U()], { status: 503,
                                  payload: { error: { code: 'NOT_PROVISIONED',
                                                      message: 'tables not set up' } } });
      await ctx.confirmReserve();
      ok(ctx.legLastErr.leg_merch_units
         && ctx.legLastErr.leg_merch_units.code === 'NOT_PROVISIONED',
         'a non-409 failure records the SERVER\'s own code, not a local guess');
      ok(ctx.toasts.some((t) => /tables not set up/.test(t)),
         '...and the message shown is the server\'s');
      ok(unit(ctx, 'MU-2').status === 'Reserved',
         '...and the local write is KEPT, because this is not a lost race -- the '
         + 'reservation is real on this device and the rollback would lose it');
    }

    // (g) no licence: refused locally, with the reason that is actually true.
    {
      const ctx = ctxFor([U()], { noLicence: true, status: 200, payload: { ok: true } });
      await ctx.confirmReserve();
      ok(ctx.legLastErr.leg_merch_units
         && ctx.legLastErr.leg_merch_units.code === 'NO_LICENSE',
         'no licence key records NO_LICENSE');
      ok(ctx.toasts.some((t) => /no licence key entered/.test(t)),
         '...and the message says to enter it in Settings rather than blaming '
         + 'the server: ' + (ctx.toasts[0] || '').slice(0, 80));
    }

    // (h) a thrown request is a NETWORK reason, not silence.
    {
      const ctx = ctxFor([U()], { throwIt: true, status: 200, payload: null });
      await ctx.confirmReserve();
      ok(ctx.legLastErr.leg_merch_units
         && ctx.legLastErr.leg_merch_units.code === 'NETWORK',
         'a thrown fetch records NETWORK rather than being swallowed');
      ok(ctx.toasts.length === 1,
         '...and says so exactly once');
    }
  }

  console.log('\nALL ' + n + ' ASSERTIONS PASS');
})().catch((e) => { console.error('\nFAILED: ' + (e && e.message)); process.exit(1); });
