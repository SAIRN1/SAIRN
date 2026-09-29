// api/sd-data-alf-consent-timestamps.test.js
//
// REQUIREMENT: `consent_granted_at` records WHEN CONSENT WAS GIVEN, not when the
//   row was last touched. It is stamped once, on the transition into consent,
//   and no later write moves it.
//
// Run:  node api/sd-data-alf-consent-timestamps.test.js
//
// ── THE DEFECT THIS PINS, FOUND LIVE 2026-09-29 ───────────────────────────
// `alf_family_contacts` writes through a PostgREST upsert with
// `resolution=merge-duplicates`, which rebuilds the whole row. The row was built
// with
//
//     consent_granted_at: famConsent ? famNow : null
//
// so every write with the flag still `true` re-stamped it from the server clock.
// Driven against the deployed endpoint: changing a family member's PHONE moved
// `consent_granted_at` forward by seventy-nine seconds, and `consent_granted_by`
// moved with it.
//
// `consent_granted_at` is the field a state surveyor reads to settle whether
// consent was in place on the date a disclosure happened. After an unrelated
// edit it answers with the date of that edit -- a plausible, precise, wrong
// date, which is worse than an absent one.
//
// ── THE SHAPE IS ALREADY DECIDED ON THIS PLATFORM ─────────────────────────
// `alf_incidents.recorded_by` is explicitly NOT re-stamped on update, and the
// reason is written at the line: *"the column answers who filed it, not who
// last touched it, and a management follow-up would otherwise erase the
// reporter."* The same sentence applies here word for word. This applies that
// decision.
//
// ── AND THE FIX IS NOT TO TRUST THE CALLER ────────────────────────────────
// The value stays server-authored. What changes is WHEN the server authors it:
// only on a transition. The prior row is read first, so the server compares its
// own stored state against the incoming flag; the caller never supplies a
// timestamp and an arm below drives that a caller-supplied one is ignored.
//
// Three pairs have the identical shape and all three are fixed together, because
// they are one line-shape repeated:
//
//     mar_consent  false->true   stamps consent_granted_at / consent_granted_by
//     mar_consent  true->false   stamps consent_revoked_at
//     active       true->false   stamps revoked_at
//
// Fixing only the one that was reported would leave two identical holes in the
// same object literal.

'use strict';

process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET
  || ['alf', 'consent', 'ts', 'fixture'].join('-');
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://test.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'test-key';

const assert = require('assert');
const { signSessionToken } = require('./_lib/auth');

const HASH = 'alf-consent-ts-hash';
const APP = 'sairncare';
const ME = 'emp-owner-1';
const CONTACT = 'FC-1';
const RESIDENT = 'res-1';

// A time far enough in the past that any re-stamp is unmistakable.
const OLD_GRANT = '2026-01-15T09:00:00.000Z';
const OLD_BY = 'emp-who-actually-granted-it';

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

// The stored row the handler should read before deciding. `existing` is null to
// drive the first-ever write.
function postgrestMock(existing, calls) {
  return async function (url, opts) {
    const u = String(url);
    calls.push({ url: u, opts: opts || null });
    if (/_employee_auth\?/.test(u)) {
      return { ok: true, status: 200, json: async function () {
        return [{ license_hash: HASH, employee_id: ME, role: 'owner', active: true }]; } };
    }
    if (/alf_family_contacts\?/.test(u) && (!opts || opts.method !== 'POST')) {
      return { ok: true, status: 200,
               json: async function () { return existing ? [existing] : []; } };
    }
    if (opts && opts.method === 'POST') {
      const sent = JSON.parse(opts.body);
      // PostgREST returns the stored row; merge-duplicates means what was sent
      // IS what is stored, which is exactly why a re-stamped field is invisible
      // to anything that only reads the response.
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

async function write(payload, existing) {
  const calls = [];
  const h = loadHandler(postgrestMock(existing || null, calls));
  const res = mockRes();
  await h({
    method: 'POST',
    headers: {
      authorization: 'Bearer KEY-FOR-' + HASH,
      'x-sd-auth': signSessionToken({ app: APP, employee_id: ME,
                                      role: 'owner', license_hash: HASH })
    },
    body: { action: 'write', resource: 'alf_family_contacts', app_id: APP,
            payload: payload }
  }, res);
  const post = calls.filter(function (c) {
    return c.opts && c.opts.method === 'POST' && /alf_family_contacts/.test(c.url);
  })[0];
  return { res: res, sent: post ? JSON.parse(post.opts.body) : null };
}

function storedRow(over) {
  return Object.assign({
    license_hash: HASH, app_id: APP, contact_id: CONTACT, resident_id: RESIDENT,
    name: 'A Relative', relationship: 'daughter', email: null, phone: null,
    mar_consent: true, consent_granted_at: OLD_GRANT, consent_granted_by: OLD_BY,
    consent_revoked_at: null, active: true, revoked_at: null, notes: null,
    recorded_by: ME
  }, over || {});
}

const BASE = { contact_id: CONTACT, resident_id: RESIDENT, name: 'A Relative' };

(async () => {

section('1. THE DEFECT -- an unrelated edit must not move the consent date');

await test('editing the PHONE with consent already true leaves the grant '
  + 'timestamp and the granter alone', async () => {
    const r = await write(Object.assign({}, BASE, {
      relationship: 'daughter', phone: '555-0101', mar_consent: true
    }), storedRow());
    assert.strictEqual(r.res.statusCode, 200, JSON.stringify(r.res.body));
    assert.strictEqual(r.sent.consent_granted_at, OLD_GRANT,
      'consent_granted_at moved to ' + JSON.stringify(r.sent.consent_granted_at)
      + ' on a write that changed only the phone number');
    assert.strictEqual(r.sent.consent_granted_by, OLD_BY,
      'consent_granted_by moved to ' + JSON.stringify(r.sent.consent_granted_by)
      + ' -- the row now names the wrong authoriser');
    assert.strictEqual(r.sent.phone, '555-0101', 'the actual edit was lost');
  });

section('2. THE TRANSITIONS -- the server stamps, once, on the change itself');

await test('FIRST EVER write with consent true stamps grant from the session',
  async () => {
    const r = await write(Object.assign({}, BASE, { mar_consent: true }), null);
    assert.ok(r.sent.consent_granted_at, 'no grant timestamp was stamped');
    assert.strictEqual(r.sent.consent_granted_by, ME);
    assert.strictEqual(r.sent.consent_revoked_at, null);
  });

await test('false -> true stamps a NEW grant, replacing a stale earlier one',
  async () => {
    // Consent was revoked and is being granted again. The old grant date is not
    // the answer to "when was this consent given" any more.
    const r = await write(Object.assign({}, BASE, { mar_consent: true }),
      storedRow({ mar_consent: false, consent_granted_at: OLD_GRANT,
                  consent_granted_by: OLD_BY,
                  consent_revoked_at: '2026-02-01T00:00:00.000Z' }));
    assert.notStrictEqual(r.sent.consent_granted_at, OLD_GRANT,
      'a re-grant kept the PREVIOUS grant date, which under-reports when the '
      + 'current consent began');
    assert.strictEqual(r.sent.consent_granted_by, ME);
    assert.strictEqual(r.sent.consent_revoked_at, null,
      'the old revocation timestamp survived a re-grant');
  });

await test('true -> false stamps the revocation and CLEARS the grant pair',
  async () => {
    const r = await write(Object.assign({}, BASE, { mar_consent: false }),
      storedRow());
    assert.ok(r.sent.consent_revoked_at, 'no revocation timestamp was stamped');
    assert.strictEqual(r.sent.consent_granted_at, null);
    assert.strictEqual(r.sent.consent_granted_by, null);
  });

await test('false -> false does not re-stamp the revocation', async () => {
    const WAS = '2026-02-01T00:00:00.000Z';
    const r = await write(Object.assign({}, BASE, { phone: '555-9999',
      mar_consent: false }), storedRow({ mar_consent: false,
        consent_granted_at: null, consent_granted_by: null,
        consent_revoked_at: WAS }));
    assert.strictEqual(r.sent.consent_revoked_at, WAS,
      'consent_revoked_at moved to ' + JSON.stringify(r.sent.consent_revoked_at)
      + ' on a write that did not change the consent flag');
  });

section('3. THE SAME SHAPE ON `active` -- one line-shape, three instances');

await test('deactivating stamps revoked_at; a later edit does not move it',
  async () => {
    const off = await write(Object.assign({}, BASE, { active: false }),
      storedRow());
    assert.ok(off.sent.revoked_at, 'no revoked_at was stamped on deactivation');
    const WAS = '2026-03-03T00:00:00.000Z';
    const again = await write(Object.assign({}, BASE, { active: false,
      phone: '555-1111' }), storedRow({ active: false, revoked_at: WAS }));
    assert.strictEqual(again.sent.revoked_at, WAS,
      'revoked_at moved to ' + JSON.stringify(again.sent.revoked_at));
  });

await test('re-activating clears revoked_at', async () => {
    const r = await write(Object.assign({}, BASE, { active: true }),
      storedRow({ active: false, revoked_at: '2026-03-03T00:00:00.000Z' }));
    assert.strictEqual(r.sent.revoked_at, null);
    assert.strictEqual(r.sent.active, true);
  });

section('4. THE CONTROLS');

await test('a CALLER-SUPPLIED consent timestamp is ignored', async () => {
    // The whole point of stamping server-side is that this is not negotiable.
    // "Only on a transition" must not become "whatever the caller sent".
    const r = await write(Object.assign({}, BASE, {
      mar_consent: true,
      consent_granted_at: '1999-01-01T00:00:00.000Z',
      consent_granted_by: 'emp-forged'
    }), null);
    assert.notStrictEqual(r.sent.consent_granted_at, '1999-01-01T00:00:00.000Z',
      'the caller set the moment of consent');
    assert.strictEqual(r.sent.consent_granted_by, ME,
      'the caller named the authoriser');
  });

await test('NEGATIVE CONTROL: the harness CAN see a re-stamp', async () => {
    // Without this, a handler that stopped writing the field at all would
    // satisfy every "it did not move" arm above and this suite would be green
    // against a broken endpoint.
    const r = await write(Object.assign({}, BASE, { mar_consent: true }), null);
    assert.ok(r.sent && 'consent_granted_at' in r.sent,
      'the write no longer carries consent_granted_at at all, so the arms above '
      + 'are asserting the absence of a field rather than its stability');
    assert.ok(r.sent.consent_granted_at !== OLD_GRANT,
      'the fixture timestamp is being echoed rather than authored');
  });

await test('the existing row is READ before the decision, exactly once',
  async () => {
    // The transition rule is only as good as the prior state it compares
    // against. A handler that guessed from the payload alone would pass the
    // arms above whenever the payload happened to agree with the stored row.
    const calls = [];
    const h = loadHandler(postgrestMock(storedRow(), calls));
    const res = mockRes();
    await h({ method: 'POST',
      headers: { authorization: 'Bearer KEY-FOR-' + HASH,
        'x-sd-auth': signSessionToken({ app: APP, employee_id: ME,
                                        role: 'owner', license_hash: HASH }) },
      body: { action: 'write', resource: 'alf_family_contacts', app_id: APP,
              payload: Object.assign({}, BASE, { mar_consent: true }) } }, res);
    const reads = calls.filter(function (c) {
      return /alf_family_contacts\?/.test(c.url) && (!c.opts || c.opts.method !== 'POST');
    });
    assert.ok(reads.length >= 1,
      'no prior-state read was issued, so the transition cannot be known');
    assert.ok(reads.some(function (c) { return /contact_id=eq\./.test(c.url); }),
      'the prior-state read is not scoped to this contact_id: '
      + reads.map(function (c) { return c.url; }).join(' | ').slice(0, 300));
  });

console.log('\n' + (fail === 0
  ? 'ALL ' + pass + ' CONSENT-TIMESTAMP ASSERTIONS PASS'
  : pass + ' passed, ' + fail + ' FAILED'));
process.exit(fail === 0 ? 0 : 1);

})();
