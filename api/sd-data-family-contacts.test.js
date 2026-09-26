// api/sd-data-family-contacts.test.js
// REQUIREMENT: a family member sees medication administration STATUS and
//   nothing else, and only when consent for THAT contact is explicitly true --
//   with the consent checked BEFORE any clinical row is fetched
//
// Run: node api/sd-data-family-contacts.test.js
//
// ── THE TWO ARMS THAT MATTER ───────────────────────────────────────────────
// (1) NO CONSENT MUST NOT READ THE MAR AT ALL. Refusing after loading the rows
//     would be correct output and the wrong mechanism: the cheapest guarantee
//     that nothing leaks is that nothing is loaded. So the arm counts the
//     alf_mar fetch and requires ZERO.
// (2) THE RESIDENT IS TAKEN FROM THE STORED CONTACT, NEVER THE CALLER. A
//     resident_id parameter on this action would be a parameter somebody
//     edits, which is the property api/sen-portal.js's view action was built
//     around. The arm sends a hostile resident_id and requires the query to
//     name the stored one.

const assert = require('assert');

function mockRes() {
  var res = { statusCode: null, body: null };
  res.status = function (c) { res.statusCode = c; return res; };
  res.json = function (b) { res.body = b; return res; };
  return res;
}
function mockReq(action, payload) {
  return {
    method: 'POST',
    headers: { authorization: 'Bearer ALF-TEST-KEY', 'x-sd-auth': 'tok' },
    body: { action: action, resource: 'alf_family_contacts', payload: payload || {} }
  };
}

let passed = 0;
async function test(name, fn) {
  try { await fn(); passed++; console.log('  ok - ' + name); }
  catch (e) { console.error('  FAIL - ' + name + '\n    ' + e.message); process.exitCode = 1; }
}

const CONTACT_CONSENTED = {
  contact_id: 'FC1', resident_id: 'RES-1', name: 'Jane Doe',
  relationship: 'daughter', email: 'j@example.invalid', phone: '555-0100',
  mar_consent: true, consent_granted_at: '2026-09-26T00:00:00Z',
  consent_granted_by: 'owner-1', active: true
};
const ADMIN_ROW = {
  entry_id: 'ADM1', resident_id: 'RES-1', entry_type: 'administration',
  data: { id: 'ADM1', medication_id: 'MED-9', date: '2026-09-25', time: '08:00',
          status: 'given', administered_by: 'emp-7',
          prn_reason: 'agitation', refusal_reason: '', notes: 'family called' }
};

function loadHandler(opts) {
  opts = opts || {};
  const calls = [];
  delete require.cache[require.resolve('./_lib/license')];
  require.cache[require.resolve('./_lib/license')] = {
    exports: {
      validateLicenseKey: async function () {
        return { valid: true, active: true, license_hash: 'test-hash',
                 trial_ends_at: null, stripe_subscription_id: null };
      }
    }
  };
  const realAuth = require('./_lib/auth');
  delete require.cache[require.resolve('./_lib/auth')];
  require.cache[require.resolve('./_lib/auth')] = {
    exports: Object.assign({}, realAuth, {
      tokenFromRequest: function () { return 'tok'; },
      verifySessionToken: function () {
        return opts.noSession ? null : { employee_id: 'owner-1', role: opts.role || 'owner' };
      }
    })
  };
  global.fetch = async function (url, init) {
    const u = String(url);
    const method = (init && init.method) || 'GET';
    calls.push({ url: u, method: method, body: init && init.body });
    if (method === 'GET') {
      if (u.indexOf('alf_family_contacts') !== -1) {
        const st = opts.contactStatus || 200;
        return { ok: st === 200, status: st,
                 json: async () => (opts.contacts !== undefined ? opts.contacts : [CONTACT_CONSENTED]) };
      }
      if (u.indexOf('alf_mar') !== -1) {
        const st = opts.marStatus || 200;
        return { ok: st === 200, status: st, json: async () => (opts.mar || [ADMIN_ROW]) };
      }
      return { ok: true, status: 200, json: async () => [] };
    }
    const st = opts.writeStatus || 201;
    return { ok: st < 300, status: st, json: async () => (st < 300 ? [JSON.parse(init.body)] : {}) };
  };
  delete require.cache[require.resolve('./sd-data.js')];
  return { handler: require('./sd-data.js'), calls: calls };
}

async function main() {
  console.log('SAIRNcare family contacts + consent-gated MAR status\n');

  await test('THE ARM THAT MATTERS: with consent FALSE the MAR is never fetched '
    + 'at all -- refusing after loading would be the right output by the wrong '
    + 'mechanism', async () => {
      const { handler, calls } = loadHandler({
        contacts: [Object.assign({}, CONTACT_CONSENTED, { mar_consent: false })] });
      const res = mockRes();
      await handler(mockReq('family_mar', { contact_id: 'FC1' }), res);
      assert.strictEqual(res.statusCode, 403, JSON.stringify(res.body));
      assert.strictEqual(res.body.error.code, 'NO_MAR_CONSENT');
      assert.strictEqual(calls.filter(c => c.url.indexOf('alf_mar') !== -1).length, 0,
        'clinical rows were fetched for a contact with no consent');
    });

  await test('...and the same for a DEACTIVATED contact whose consent flag is '
    + 'still true -- revocation must not depend on a second field', async () => {
      const { handler, calls } = loadHandler({
        contacts: [Object.assign({}, CONTACT_CONSENTED, { active: false })] });
      const res = mockRes();
      await handler(mockReq('family_mar', { contact_id: 'FC1' }), res);
      assert.strictEqual(res.body.error.code, 'CONTACT_INACTIVE');
      assert.strictEqual(calls.filter(c => c.url.indexOf('alf_mar') !== -1).length, 0);
    });

  await test('THE SECOND ARM THAT MATTERS: the resident comes from the STORED '
    + 'contact, not the caller -- a hostile resident_id changes nothing', async () => {
      const { handler, calls } = loadHandler({});
      await handler(mockReq('family_mar',
        { contact_id: 'FC1', resident_id: 'RES-SOMEBODY-ELSE' }), mockRes());
      const marCall = calls.find(c => c.url.indexOf('alf_mar') !== -1);
      assert.ok(marCall.url.indexOf('RES-1') !== -1, marCall.url);
      assert.ok(marCall.url.indexOf('RES-SOMEBODY-ELSE') === -1,
        'the caller-supplied resident reached the query');
    });

  await test('the MAR query asks for administration entries ONLY -- counts, '
    + 'orders and reconciliations are excluded at the QUERY, not just in the '
    + 'projection', async () => {
      const { handler, calls } = loadHandler({});
      await handler(mockReq('family_mar', { contact_id: 'FC1' }), mockRes());
      const marCall = calls.find(c => c.url.indexOf('alf_mar') !== -1);
      assert.ok(/entry_type=eq\.administration/.test(marCall.url), marCall.url);
    });

  await test('with consent, the payload carries STATUS and no clinical field', async () => {
    const { handler } = loadHandler({});
    const res = mockRes();
    await handler(mockReq('family_mar', { contact_id: 'FC1' }), res);
    const v = res.body.family_mar;
    assert.strictEqual(v.ok, true, JSON.stringify(res.body));
    assert.strictEqual(v.events.length, 1);
    assert.deepStrictEqual(Object.keys(v.events[0]).sort(),
      ['date', 'resident_id', 'status', 'time']);
    const blob = JSON.stringify(res.body);
    ['MED-9', 'agitation', 'family called', 'emp-7'].forEach(function (leak) {
      assert.ok(blob.indexOf(leak) === -1, leak + ' reached the family payload');
    });
  });

  await test('...and it says in the payload what it is NOT showing', async () => {
    const { handler } = loadHandler({});
    const res = mockRes();
    await handler(mockReq('family_mar', { contact_id: 'FC1' }), res);
    assert.ok(/controlled-substance/.test(res.body.family_mar.not_included));
  });

  await test('an unknown contact is a 404, not an empty view', async () => {
    const { handler } = loadHandler({ contacts: [] });
    const res = mockRes();
    await handler(mockReq('family_mar', { contact_id: 'NOPE' }), res);
    assert.strictEqual(res.statusCode, 404);
    assert.strictEqual(res.body.error.code, 'NO_SUCH_CONTACT');
  });

  await test('family_mar with no contact_id is refused rather than defaulting '
    + 'to a resident', async () => {
      const res = mockRes();
      await loadHandler({}).handler(mockReq('family_mar', {}), res);
      assert.strictEqual(res.body.error.code, 'NO_CONTACT_ID');
    });

  await test('WRITE IS MANAGEMENT ONLY -- granting consent is a disclosure '
    + 'decision, not a form field', async () => {
      const res = mockRes();
      await loadHandler({ role: 'caregiver' })
        .handler(mockReq('write', Object.assign({}, CONTACT_CONSENTED)), res);
      assert.strictEqual(res.statusCode, 403);
      assert.strictEqual(res.body.error.code, 'FORBIDDEN');
    });

  await test('consent DEFAULTS TO FALSE when the field is absent', async () => {
    const { handler, calls } = loadHandler({});
    const p = Object.assign({}, CONTACT_CONSENTED); delete p.mar_consent;
    await handler(mockReq('write', p), mockRes());
    const sent = JSON.parse(calls.find(c => c.method === 'POST').body);
    assert.strictEqual(sent.mar_consent, false);
    assert.strictEqual(sent.consent_granted_at, null);
  });

  await test('a NON-BOOLEAN consent flag is REFUSED, never coerced -- the '
    + 'string "false" is truthy and this flag discloses clinical information',
    async () => {
      for (const v of ['false', 'true', 'yes', 1, 0]) {
        const res = mockRes();
        await loadHandler({}).handler(mockReq('write',
          Object.assign({}, CONTACT_CONSENTED, { mar_consent: v })), res);
        assert.strictEqual(res.statusCode, 400, 'accepted ' + JSON.stringify(v));
        assert.strictEqual(res.body.error.code, 'BAD_CONSENT_FLAG');
      }
    });

  await test('WHO GRANTED IT COMES FROM THE SESSION, never the body', async () => {
    const { handler, calls } = loadHandler({});
    await handler(mockReq('write', Object.assign({}, CONTACT_CONSENTED,
      { consent_granted_by: 'somebody-else', consent_granted_at: '1999-01-01T00:00:00Z' })),
      mockRes());
    const sent = JSON.parse(calls.find(c => c.method === 'POST').body);
    assert.strictEqual(sent.consent_granted_by, 'owner-1');
    assert.notStrictEqual(sent.consent_granted_at, '1999-01-01T00:00:00Z');
  });

  await test('revoking consent stamps consent_revoked_at and keeps the grant '
    + 'fields clear, so the row still reads as not-consented', async () => {
      const { handler, calls } = loadHandler({});
      await handler(mockReq('write', Object.assign({}, CONTACT_CONSENTED,
        { mar_consent: false })), mockRes());
      const sent = JSON.parse(calls.find(c => c.method === 'POST').body);
      assert.strictEqual(sent.mar_consent, false);
      assert.ok(sent.consent_revoked_at);
      assert.strictEqual(sent.consent_granted_at, null);
    });

  await test('deactivating a contact stamps revoked_at rather than deleting -- '
    + 'and no DELETE is ever issued', async () => {
      const { handler, calls } = loadHandler({});
      await handler(mockReq('write', Object.assign({}, CONTACT_CONSENTED,
        { active: false })), mockRes());
      const sent = JSON.parse(calls.find(c => c.method === 'POST').body);
      assert.strictEqual(sent.active, false);
      assert.ok(sent.revoked_at);
      assert.strictEqual(calls.filter(c => c.method === 'DELETE').length, 0);
    });

  await test('the write refuses without contact_id, resident_id or name', async () => {
    for (const f of ['contact_id', 'resident_id', 'name']) {
      const p = Object.assign({}, CONTACT_CONSENTED); delete p[f];
      const res = mockRes();
      await loadHandler({}).handler(mockReq('write', p), res);
      assert.strictEqual(res.body.error.code, 'MISSING_FIELDS', f);
    }
  });

  await test('read scopes to a resident when asked, and needs a session', async () => {
    const { handler, calls } = loadHandler({});
    await handler(mockReq('read', { resident_id: 'RES-1' }), mockRes());
    assert.ok(calls.find(c => /resident_id=eq\.RES-1/.test(c.url)));
    const res = mockRes();
    await loadHandler({ noSession: true }).handler(mockReq('read', {}), res);
    assert.strictEqual(res.statusCode, 401);
  });

  await test('an unprovisioned table fails CLOSED -- provisioned:false, never '
    + 'an empty list that reads as "no family recorded"', async () => {
      const res = mockRes();
      await loadHandler({ contactStatus: 404 }).handler(mockReq('read', {}), res);
      assert.strictEqual(res.body.provisioned, false);
    });

  await test('IS IT REACHABLE: family_mar is declared in the resource registry',
    async () => {
      const reg = require('./_resources/sairncare');
      assert.ok(reg.resources.indexOf('alf_family_contacts') !== -1);
      assert.ok((reg.extraActions.alf_family_contacts || []).indexOf('family_mar') !== -1,
        'family_mar is implemented and undeclared -- the dispatcher would answer 400');
    });

  console.log('\n' + (process.exitCode
    ? 'FAILURES ABOVE'
    : 'ALL ' + passed + ' FAMILY-CONTACTS ENDPOINT ASSERTIONS PASS'));
}

main();
