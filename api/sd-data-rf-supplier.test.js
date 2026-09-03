// api/sd-data-rf-supplier.test.js
// Run: node api/sd-data-rf-supplier.test.js
//
// SAIRNroofing B6 -- supplier documents and the three-way match. The engine's
// logic is covered in api/_lib/roofing-supplier-match.test.js; this covers the
// boundary: who may read, who may write, what is refused, and that asking
// whether an invoice is right never itself records anything.

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
    headers: { authorization: 'Bearer RF-TEST-KEY', 'x-sd-auth': 'tok' },
    body: { action: action, resource: 'rf_supplier_documents', payload: payload || {} }
  };
}

let passed = 0;
async function test(name, fn) {
  try { await fn(); passed++; console.log('  ok - ' + name); }
  catch (e) { console.error('  FAIL - ' + name + '\n    ' + e.message); process.exitCode = 1; }
}

function loadHandler(opts) {
  opts = opts || {};
  const calls = [];
  delete require.cache[require.resolve('./_lib/license')];
  require.cache[require.resolve('./_lib/license')] = {
    exports: {
      validateLicenseKey: async function () {
        return { valid: true, active: true, license_hash: 'test-hash', trial_ends_at: null, stripe_subscription_id: null };
      }
    }
  };
  const realAuth = require('./_lib/auth');
  delete require.cache[require.resolve('./_lib/auth')];
  require.cache[require.resolve('./_lib/auth')] = {
    exports: Object.assign({}, realAuth, {
      tokenFromRequest: function () { return 'tok'; },
      verifySessionToken: function () {
        return opts.noSession ? null : { employee_id: opts.employeeId || 'mgr-1', role: opts.role || 'owner' };
      }
    })
  };
  global.fetch = async function (url, init) {
    const method = (init && init.method) || 'GET';
    calls.push({ url: String(url), method: method, headers: (init && init.headers) || {}, body: init && init.body });
    if (opts.refuseNetwork) throw new Error('a refused request reached the database');
    if (method === 'GET') {
      const st = opts.readStatus || 200;
      return { ok: st === 200, status: st, json: async () => (st === 200 ? (opts.rows || []) : {}) };
    }
    const st = opts.writeStatus || 201;
    return { ok: st < 300, status: st, json: async () => (st < 300 ? [JSON.parse(init.body)] : {}) };
  };
  delete require.cache[require.resolve('./sd-data.js')];
  return { handler: require('./sd-data.js'), calls: calls };
}

const ORDER = {
  document_id: 'DOC-1', doc_type: 'order', po_number: 'PO-1', supplier: 'A Supplier',
  doc_date: '2026-09-01',
  lines: [{ item_code: 'SH-30', description: 'Shingle', qty_ordered: 100, unit_price: 32 }]
};

async function main() {
  console.log('api/sd-data.js -- rf_supplier_documents: append-only, management-write, match writes nothing');
  process.env.SUPABASE_URL = 'https://test.supabase.co';
  process.env.SUPABASE_SERVICE_ROLE_KEY = 'test-key';

  await test('the resource and its verb are registered', () => {
    const reg = require('./_resources');
    assert.ok(reg.RESOURCES['rf_supplier_documents']);
    assert.deepStrictEqual(reg.EXTRA_ACTIONS['rf_supplier_documents'], ['match']);
  });

  await test('no session -> 401, and never touches the database', async () => {
    const { handler, calls } = loadHandler({ noSession: true, refuseNetwork: true });
    const res = mockRes();
    await handler(mockReq('read'), res);
    assert.strictEqual(res.statusCode, 401);
    assert.strictEqual(calls.length, 0);
  });

  await test('a crew role cannot even read -- this is management information', async () => {
    const { handler } = loadHandler({ role: 'crew' });
    const res = mockRes();
    await handler(mockReq('read'), res);
    assert.strictEqual(res.statusCode, 403);
  });

  await test('an ESTIMATOR can read -- they need to see what material costs', async () => {
    const { handler } = loadHandler({ role: 'estimator', rows: [] });
    const res = mockRes();
    await handler(mockReq('read'), res);
    assert.strictEqual(res.statusCode, 200);
  });

  await test('...but an estimator CANNOT write -- these rows decide payment', async () => {
    const { handler, calls } = loadHandler({ role: 'estimator' });
    const res = mockRes();
    await handler(mockReq('write', ORDER), res);
    assert.strictEqual(res.statusCode, 403);
    assert.strictEqual(calls.filter(c => c.method === 'POST').length, 0);
  });

  // ---- validation --------------------------------------------------------
  await test('an unknown doc_type is refused, naming the three', async () => {
    const { handler } = loadHandler({});
    const res = mockRes();
    await handler(mockReq('write', Object.assign({}, ORDER, { doc_type: 'quote' })), res);
    assert.strictEqual(res.body.error.code, 'UNKNOWN_DOC_TYPE');
    assert.match(res.body.error.message, /order/);
  });

  await test('no po_number is refused -- it is the key all three share', async () => {
    const { handler } = loadHandler({});
    const res = mockRes();
    await handler(mockReq('write', Object.assign({}, ORDER, { po_number: '  ' })), res);
    assert.strictEqual(res.body.error.code, 'NO_PO_NUMBER');
    assert.match(res.body.error.message, /nowhere to go/);
  });

  await test('a document with no lines is refused, not stored as an empty shell', async () => {
    const { handler } = loadHandler({});
    const res = mockRes();
    await handler(mockReq('write', Object.assign({}, ORDER, { lines: [] })), res);
    assert.strictEqual(res.body.error.code, 'NO_LINES');
  });

  await test('QUANTITIES ARE NOT COERCED -- a blank stays blank through the write', async () => {
    // The whole pipeline depends on missing meaning UNKNOWN. Coercing to 0
    // here would turn every unscanned delivery into a short shipment.
    const { handler, calls } = loadHandler({});
    const doc = { document_id: 'D2', doc_type: 'receipt', po_number: 'PO-1',
      lines: [{ item_code: 'SH-30', qty_received: '' }] };
    await handler(mockReq('write', doc), mockRes());
    const sent = JSON.parse(calls.find(c => c.method === 'POST').body);
    assert.strictEqual(sent.lines[0].qty_received, '', 'a blank quantity was coerced');
    assert.ok(!('qty_received' in sent.lines[0]) || sent.lines[0].qty_received !== 0);
  });

  // ---- append-only -------------------------------------------------------
  await test('THE INSERT IS PLAIN -- a receipt must not be editable after the fact', async () => {
    const { handler, calls } = loadHandler({});
    await handler(mockReq('write', ORDER), mockRes());
    const post = calls.find(c => c.method === 'POST');
    assert.ok(!/merge-duplicates/.test(String(post.headers.Prefer || '')));
    assert.ok(!/on_conflict/.test(post.url));
  });

  await test('a duplicate document id -> 409 saying a correction is a NEW document', async () => {
    const { handler } = loadHandler({ writeStatus: 409 });
    const res = mockRes();
    await handler(mockReq('write', ORDER), res);
    assert.strictEqual(res.statusCode, 409);
    assert.match(res.body.error.message, /NEW document/);
  });

  await test('recorded_by and license_hash come from the server', async () => {
    const { handler, calls } = loadHandler({ employeeId: 'mgr-real' });
    await handler(mockReq('write', Object.assign({}, ORDER, { recorded_by: 'forged', license_hash: 'x' })), mockRes());
    const sent = JSON.parse(calls.find(c => c.method === 'POST').body);
    assert.strictEqual(sent.recorded_by, 'mgr-real');
    assert.strictEqual(sent.license_hash, 'test-hash');
  });

  // ---- match -------------------------------------------------------------
  await test('match without a po_number is refused, not run across everything', async () => {
    const { handler } = loadHandler({ rows: [] });
    const res = mockRes();
    await handler(mockReq('match', {}), res);
    assert.strictEqual(res.statusCode, 400);
    assert.strictEqual(res.body.error.code, 'NO_PO_NUMBER');
    assert.match(res.body.error.message, /compare unrelated documents/);
  });

  await test('match SCOPES THE QUERY to that PO', async () => {
    const { handler, calls } = loadHandler({ rows: [] });
    await handler(mockReq('match', { po_number: 'PO-77' }), mockRes());
    assert.ok(calls[0].url.includes('po_number=eq.PO-77'), 'the query was not scoped: ' + calls[0].url);
  });

  await test('MATCH WRITES NOTHING -- asking is not approving', async () => {
    const { handler, calls } = loadHandler({
      rows: [
        { doc_type: 'order', po_number: 'PO-1', lines: [{ item_code: 'SH-30', qty_ordered: 100, unit_price: 32 }] },
        { doc_type: 'receipt', po_number: 'PO-1', lines: [{ item_code: 'SH-30', qty_received: 90 }] },
        { doc_type: 'invoice', po_number: 'PO-1', lines: [{ item_code: 'SH-30', qty_invoiced: 100, unit_price: 32 }] }
      ]
    });
    const res = mockRes();
    await handler(mockReq('match', { po_number: 'PO-1' }), res);
    assert.strictEqual(res.statusCode, 200);
    assert.strictEqual(res.body.match.counts.over_invoiced_qty, 1);
    assert.strictEqual(calls.filter(c => c.method !== 'GET').length, 0, 'asking wrote something');
  });

  await test('match with an invoice and no order -> 400 NO_ORDER, the real finding', async () => {
    const { handler } = loadHandler({
      rows: [{ doc_type: 'invoice', po_number: 'PO-9', lines: [{ item_code: 'X', qty_invoiced: 1, unit_price: 5 }] }]
    });
    const res = mockRes();
    await handler(mockReq('match', { po_number: 'PO-9' }), res);
    assert.strictEqual(res.statusCode, 400);
    assert.strictEqual(res.body.error.code, 'NO_ORDER');
  });

  await test('the tolerance used is echoed back, never applied silently', async () => {
    const { handler } = loadHandler({
      rows: [
        { doc_type: 'order', po_number: 'PO-1', lines: [{ item_code: 'SH-30', qty_ordered: 100, unit_price: 32 }] },
        { doc_type: 'receipt', po_number: 'PO-1', lines: [{ item_code: 'SH-30', qty_received: 99 }] }
      ]
    });
    const res = mockRes();
    await handler(mockReq('match', { po_number: 'PO-1', qty_tolerance: 1 }), res);
    assert.strictEqual(res.body.match.qty_tolerance, 1);
    assert.ok(!res.body.match.counts.short_received);
  });

  // ---- provisioning ------------------------------------------------------
  await test('un-run migration: READ is provisioned:false, WRITE is 503 naming the file', async () => {
    const r1 = mockRes();
    await loadHandler({ readStatus: 404 }).handler(mockReq('read'), r1);
    assert.strictEqual(r1.body.provisioned, false);
    const r2 = mockRes();
    await loadHandler({ writeStatus: 404 }).handler(mockReq('write', ORDER), r2);
    assert.strictEqual(r2.statusCode, 503);
    assert.match(r2.body.error.message, /sairnroofing_supplier_documents_schema\.sql/);
  });

  console.log('\n' + (process.exitCode ? 'FAILURES ABOVE' : 'ALL ' + passed + ' RF-SUPPLIER-ENDPOINT ASSERTIONS PASS'));
}

main();
