// api/b33-route-map.test.js
//
// Run:  node api/b33-route-map.test.js
//
// CONCEPT: the map image is drawn on the server so the Maps key never reaches
// the page, and only for a signed-in employee of a licence that has a Field Map.
// Every arm drives the real handler with the licence store and Google stubbed.
//
// Exit: 0 all arms passed - 1 an arm FAILED

'use strict';
const path = require('path');

// A placeholder-marked value on purpose: tools/redaction_check.py treats a
// "secret = '<16+ chars>'" literal without a placeholder marker as a credential.
process.env.SD_AUTH_SECRET = 'fake-b33-signing-value-for-this-test-only';
const KEY = 'test-maps-key-for-b33-only';

const LICENCE = require.resolve('./_lib/license');
let lic = { valid: true, active: true, app_id: 'stonedesk', license_hash: 'h-stonedesk' };
require.cache[LICENCE] = { id: LICENCE, filename: LICENCE, loaded: true,
  exports: { validateLicenseKey: async () => lic } };

const auth = require('./_lib/auth');
const handler = require('./route-map.js');

let pass = 0, fail = 0;
function ok(name, cond, detail) {
  if (cond) { pass++; console.log('  ok   ' + name); }
  else { fail++; console.log('  FAIL ' + name + (detail ? '\n       ' + String(detail).slice(0, 300) : '')); }
}

let upstream = [];
let upstreamAnswer = () => ({ ok: true, status: 200, headers: { get: () => 'image/png' },
  arrayBuffer: async () => Uint8Array.from([0x89, 0x50, 0x4e, 0x47]).buffer });
global.fetch = async (url) => { upstream.push(String(url)); return upstreamAnswer(); };

function mockRes() {
  const r = { code: 0, body: null };
  r.status = (c) => { r.code = c; return r; };
  r.json = (b) => { r.body = b; return r; };
  return r;
}
async function call(opts) {
  const o = opts || {};
  const headers = {};
  if (o.licence !== false) headers.authorization = 'Bearer SD-AUDIT-2026';
  if (o.token) headers['x-sd-auth'] = o.token;
  const res = mockRes();
  upstream = [];
  await handler({ method: o.method || 'POST', headers, body: o.body === undefined ? { addresses: ['1 A St', '2 B St'] } : o.body }, res);
  return { code: res.code, body: res.body, upstream: upstream.slice() };
}
const TOKEN = auth.signSessionToken({ app: 'stonedesk', employee_id: 'e1', role: 'owner', license_hash: 'h-stonedesk' });

(async () => {
  console.log('A. the gate, in order');
  process.env.GOOGLE_MAPS_API_KEY = KEY;
  let r = await call({ method: 'GET', token: TOKEN });
  ok('A1. GET is refused 405', r.code === 405);
  r = await call({ licence: false, token: TOKEN });
  ok('A2. no licence -> 401 NO_LICENSE, Google never asked', r.code === 401 && r.body.error.code === 'NO_LICENSE' && r.upstream.length === 0);
  lic = { valid: true, active: true, app_id: 'sairnlaw', license_hash: 'h-law' };
  r = await call({ token: TOKEN });
  ok('A3. a licence for an app with no Field Map -> 403, Google never asked', r.code === 403 && r.upstream.length === 0, JSON.stringify(r.body));
  lic = { valid: true, active: true, app_id: 'stonedesk', license_hash: 'h-stonedesk' };
  r = await call({});
  ok('A4. licence but NO SESSION -> 401 NO_SESSION (customer addresses need a person)', r.code === 401 && r.body.error.code === 'NO_SESSION' && r.upstream.length === 0);
  const otherShop = auth.signSessionToken({ app: 'stonedesk', employee_id: 'e2', role: 'owner', license_hash: 'h-other' });
  r = await call({ token: otherShop });
  ok('A5. a session from ANOTHER licence -> 401', r.code === 401 && r.upstream.length === 0);
  lic = { valid: true, active: false, app_id: 'stonedesk', license_hash: 'h-stonedesk' };
  r = await call({ token: TOKEN });
  ok('A6. inactive licence -> 403 LICENSE_INACTIVE', r.code === 403 && r.body.error.code === 'LICENSE_INACTIVE');
  lic = { valid: true, active: true, app_id: 'stonedesk', license_hash: 'h-stonedesk' };

  console.log('\nB. the request it builds');
  r = await call({ token: TOKEN, body: { addresses: [] } });
  ok('B1. empty list -> 400 BAD_STOPS', r.code === 400 && r.body.error.code === 'BAD_STOPS');
  r = await call({ token: TOKEN, body: { addresses: ['ok', 7] } });
  ok('B2. a non-string address -> 400 BAD_STOPS', r.code === 400);
  r = await call({ token: TOKEN, body: { addresses: ['x'.repeat(201)] } });
  ok('B3. a 201-character address -> 400 BAD_STOPS', r.code === 400);
  const many = Array.from({ length: 15 }, (_, i) => (100 + i) + ' Probe St');
  r = await call({ token: TOKEN, body: { addresses: many } });
  ok('B4. 15 stops -> 200 with drawn 12 and stops 15, so the page can say some were left off',
    r.code === 200 && r.body.drawn === handler.MAX_STOPS && r.body.stops === 15, JSON.stringify(r.body).slice(0, 120));
  ok('B5. ...and the upstream URL carries 12 markers and one path', r.upstream.length === 1
    && (r.upstream[0].match(/markers=/g) || []).length === 12 && (r.upstream[0].match(/path=/g) || []).length === 1, r.upstream[0]);

  console.log('\nC. the key stays on the server');
  r = await call({ token: TOKEN });
  ok('C1. success -> 200 with a PNG data URL', r.code === 200 && /^data:image\/png;base64,/.test(r.body.image), JSON.stringify(r.body).slice(0, 80));
  ok('C2. the key is in the UPSTREAM request...', r.upstream[0].indexOf(encodeURIComponent(KEY)) !== -1);
  ok('C3. ...and NOWHERE in the response the page receives', JSON.stringify(r.body).indexOf(KEY) === -1);
  upstreamAnswer = () => ({ ok: false, status: 403, headers: { get: () => 'text/plain' },
    arrayBuffer: async () => Buffer.from('The Google Maps Platform server rejected your request. key=' + KEY) });
  r = await call({ token: TOKEN });
  ok('C4. Google refuses -> 502 UPSTREAM naming the status, and its body (which can quote the key) is NOT relayed',
    r.code === 502 && r.body.error.code === 'UPSTREAM' && JSON.stringify(r.body).indexOf(KEY) === -1, JSON.stringify(r.body));
  upstreamAnswer = () => ({ ok: true, status: 200, headers: { get: () => 'text/html' }, arrayBuffer: async () => Buffer.from('<html>') });
  r = await call({ token: TOKEN });
  ok('C5. a 200 that is not an image -> 502, not a broken <img>', r.code === 502);
  delete process.env.GOOGLE_MAPS_API_KEY;
  r = await call({ token: TOKEN });
  ok('C6. no key configured -> 503 NO_MAPS_KEY and Google is never asked', r.code === 503 && r.body.error.code === 'NO_MAPS_KEY' && r.upstream.length === 0);

  console.log('\n' + (fail ? 'FAILED' : 'ok') + '  b33 route map: ' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})().catch((e) => { console.log('HARNESS ERROR: ' + (e && e.stack || e)); process.exit(2); });
