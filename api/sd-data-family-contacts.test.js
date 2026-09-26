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
        if (opts.marNonArray) {
          return { ok: true, status: 200, json: async () => ({ message: 'not an array' }) };
        }
        // ── THE STUB HONOURS limit/offset, AND IT HAS TO (2026-09-26) ──────
        // The handler pages this read now. A stub that returned the same array
        // for every call would loop for ever on any fixture of a full page, and
        // -- worse -- would make a pagination arm pass while proving nothing,
        // because every page would look full of the same rows. Slicing is a
        // no-op for every pre-existing arm, whose fixtures are 0-2 rows.
        const rows = opts.mar || [ADMIN_ROW];
        const lm = /[?&]limit=(\d+)/.exec(u);
        const om = /[?&]offset=(\d+)/.exec(u);
        const off = om ? Number(om[1]) : 0;
        const lim = lm ? Number(lm[1]) : rows.length;
        return { ok: st === 200, status: st,
                 json: async () => rows.slice(off, off + lim) };
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

  // ══ WHO MAY READ A CONTACT AT ALL (2026-09-26) ═══════════════════════════
  // The read had NO role gate -- verifySessionToken alone -- so any employee of
  // any role could list every family contact on the licence with phone, email,
  // notes and the whole consent trail. Eighteen arms above passed the entire
  // time, because every one of them ran as `owner`. The role was a parameter the
  // suite never varied, which is how a missing gate stays invisible.

  await test('ROLE GATE: a med_aide is REFUSED the contact list, and the refusal '
    + 'happens before any contact row is fetched', async () => {
      const { handler, calls } = loadHandler({ role: 'med_aide' });
      const res = mockRes();
      await handler(mockReq('read', {}), res);
      assert.strictEqual(res.statusCode, 403, JSON.stringify(res.body));
      assert.strictEqual(res.body.error.code, 'FORBIDDEN');
      assert.strictEqual(
        calls.filter(c => c.url.indexOf('alf_family_contacts') !== -1).length, 0,
        'contact rows were fetched for a role that may not see them');
    });

  await test('...and an activities role too -- the two roles the old gate\'s '
    + 'absence exposed this data to', async () => {
      const { handler } = loadHandler({ role: 'activities' });
      const res = mockRes();
      await handler(mockReq('read', {}), res);
      assert.strictEqual(res.statusCode, 403, JSON.stringify(res.body));
    });

  await test('...and the refusal NAMES what is withheld rather than saying "no" '
    + '-- a 403 the app renders as "sign in" is a wrong explanation', async () => {
      const { handler } = loadHandler({ role: 'med_aide' });
      const res = mockRes();
      await handler(mockReq('read', {}), res);
      const m = res.body.error.message;
      assert.ok(/phone/.test(m) && /consent/.test(m) && /role/.test(m), m);
    });

  await test('ROLE GATE CONTROL: nursing IS allowed -- reaching a resident\'s '
    + 'family is care work, so this is not a refusal of everybody', async () => {
      const { handler } = loadHandler({ role: 'nursing' });
      const res = mockRes();
      await handler(mockReq('read', {}), res);
      assert.strictEqual(res.statusCode, 200, JSON.stringify(res.body));
      assert.strictEqual(res.body.data.length, 1);
    });

  await test('ROLE GATE CONTROL: owner and billing are allowed, so the 18 arms '
    + 'above are still exercising a reachable path', async () => {
      for (const role of ['owner', 'billing']) {
        const { handler } = loadHandler({ role: role });
        const res = mockRes();
        await handler(mockReq('read', {}), res);
        assert.strictEqual(res.statusCode, 200, role + ': ' + JSON.stringify(res.body));
      }
    });

  // ══ THE SILENT 500-ROW CAP (2026-09-26) ══════════════════════════════════
  // `limit=500` with nothing said. familyMarView computes an ADHERENCE
  // PERCENTAGE over whatever rows it is handed, so a resident past 500
  // administrations gave a family member a number and a history presented as
  // complete, computed from part of the record.

  function admin(i) {
    return { entry_id: 'ADM' + i, resident_id: 'RES-1', entry_type: 'administration',
             data: { id: 'ADM' + i, medication_id: 'MED-9', date: '2026-09-25',
                     time: '08:00', status: 'given', administered_by: 'emp-7' } };
  }
  const many = (n) => Array.from({ length: n }, (_, i) => admin(i));

  await test('PAGINATION: 1200 administrations are read in FULL across three '
    + 'pages, not truncated at 500', async () => {
      const { handler, calls } = loadHandler({ mar: many(1200) });
      const res = mockRes();
      await handler(mockReq('family_mar', { contact_id: 'FC1' }), res);
      assert.strictEqual(res.statusCode, 200, JSON.stringify(res.body).slice(0, 300));
      assert.strictEqual(res.body.family_mar.events.length, 1200,
        'the view was built from a truncated MAR');
      const marCalls = calls.filter(c => c.url.indexOf('alf_mar') !== -1);
      assert.strictEqual(marCalls.length, 3, marCalls.map(c => c.url).join('\n'));
      assert.ok(/[?&]offset=0\b/.test(marCalls[0].url), marCalls[0].url);
      assert.ok(/[?&]offset=500\b/.test(marCalls[1].url), marCalls[1].url);
      assert.ok(/[?&]offset=1000\b/.test(marCalls[2].url), marCalls[2].url);
    });

  await test('...and the pages are ordered ASCENDING, which is what makes offset '
    + 'paging stable on an append-only trail', async () => {
      // In created_at.desc a concurrent insert lands at offset 0 and shifts every
      // later window -- one row duplicated, one skipped, silently. Asserted on
      // the QUERY because the defect is in the query, and the output order is
      // unaffected either way: familyMarView sorts the rows itself.
      const { handler, calls } = loadHandler({ mar: many(600) });
      await handler(mockReq('family_mar', { contact_id: 'FC1' }), mockRes());
      for (const c of calls.filter(c => c.url.indexOf('alf_mar') !== -1)) {
        assert.ok(c.url.indexOf('order=created_at.asc') !== -1, c.url);
        assert.ok(c.url.indexOf('created_at.desc') === -1, c.url);
      }
    });

  await test('...and a full FINAL page still triggers one more read, so exactly '
    + '500 rows is not mistaken for "there might be more"', async () => {
      const { handler, calls } = loadHandler({ mar: many(500) });
      const res = mockRes();
      await handler(mockReq('family_mar', { contact_id: 'FC1' }), res);
      assert.strictEqual(res.body.family_mar.events.length, 500);
      assert.strictEqual(
        calls.filter(c => c.url.indexOf('alf_mar') !== -1).length, 2,
        'a full page must be followed by a probe for the next one');
    });

  await test('...and a SHORT first page reads once -- the loop does not cost a '
    + 'second request on every ordinary resident', async () => {
      const { handler, calls } = loadHandler({ mar: many(3) });
      const res = mockRes();
      await handler(mockReq('family_mar', { contact_id: 'FC1' }), res);
      assert.strictEqual(res.body.family_mar.events.length, 3);
      assert.strictEqual(
        calls.filter(c => c.url.indexOf('alf_mar') !== -1).length, 1);
    });

  await test('CEILING: past the hard cap it REFUSES rather than serving a partial '
    + 'history with an adherence figure computed from part of it', async () => {
      const { handler } = loadHandler({ mar: many(10500) });
      const res = mockRes();
      await handler(mockReq('family_mar', { contact_id: 'FC1' }), res);
      assert.strictEqual(res.statusCode, 413, JSON.stringify(res.body).slice(0, 300));
      assert.strictEqual(res.body.error.code, 'MAR_TOO_LARGE');
      assert.ok(!res.body.family_mar, 'a partial view was served alongside the error');
    });

  await test('...and an UNREADABLE page is 502, not an early break that serves '
    + 'what had accumulated', async () => {
      const { handler } = loadHandler({ marNonArray: true });
      const res = mockRes();
      await handler(mockReq('family_mar', { contact_id: 'FC1' }), res);
      assert.strictEqual(res.statusCode, 502, JSON.stringify(res.body).slice(0, 300));
      assert.strictEqual(res.body.error.code, 'MAR_PAGE_UNREADABLE');
      assert.ok(!res.body.family_mar);
    });

  await test('CONSENT STILL COMES FIRST: no consent means ZERO pages are read, '
    + 'not one page then a refusal', async () => {
      // The pagination loop is new code between the consent check and the rows.
      // This re-asserts the original property against it.
      const { handler, calls } = loadHandler({
        mar: many(1200),
        contacts: [Object.assign({}, CONTACT_CONSENTED, { mar_consent: false })] });
      const res = mockRes();
      await handler(mockReq('family_mar', { contact_id: 'FC1' }), res);
      assert.strictEqual(res.body.error.code, 'NO_MAR_CONSENT');
      assert.strictEqual(
        calls.filter(c => c.url.indexOf('alf_mar') !== -1).length, 0,
        'the paging loop ran for a contact with no consent');
    });

  console.log('\n' + (process.exitCode
    ? 'FAILURES ABOVE'
    : 'ALL ' + passed + ' FAMILY-CONTACTS ENDPOINT ASSERTIONS PASS'));
}

main();
