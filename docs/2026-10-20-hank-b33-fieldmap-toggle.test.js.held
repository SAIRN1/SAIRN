// api/b33-fieldmap-toggle.test.js
//
// Run:  node api/b33-fieldmap-toggle.test.js
//
// The Field Map shows the directions link always and the image as an option
// (Michael, b33). Lifts the SHIPPED fmRenderMap and its helpers out of
// stonedesk.html and runs them against a stub DOM, storage and fetch.
//
// Exit: 0 all arms passed - 1 an arm FAILED

'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const HTML = fs.readFileSync(path.join(__dirname, '..', 'stonedesk.html'), 'utf8');
let pass = 0, fail = 0;
function ok(name, cond, detail) {
  if (cond) { pass++; console.log('  ok   ' + name); }
  else { fail++; console.log('  FAIL ' + name + (detail ? '\n       ' + String(detail).slice(0, 300) : '')); }
}
const start = HTML.indexOf('function fmRenderMap(');
const end = HTML.indexOf('\n// HARD GATE (2026-08-06)', start);
const SRC = HTML.slice(start, end);

function world(pref, answer) {
  const els = {}; const store = { sd_fm_map_image: pref }; const calls = [];
  const get = (id) => (els[id] = els[id] || { id, innerHTML: '' });
  const ctx = {
    document: { getElementById: get },
    localStorage: { getItem: (k) => (k in store ? store[k] : null) },
    sessionStorage: { getItem: (k) => (k === 'sd_session_token' ? 'TOK' : null) },
    stRaw: (k, v) => { store[k] = v; return true; },
    sdLicenseKey: () => 'SD-LIC',
    escHtml: (x) => String(x).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/"/g, '&quot;'),
    fetch: (u, o) => { calls.push({ u, o }); return Promise.resolve({ status: answer.status, json: () => Promise.resolve(answer.body) }); },
    Object, JSON, Promise, encodeURIComponent, Math
  };
  vm.createContext(ctx);
  vm.runInContext(SRC, ctx);
  return { ctx, els, calls, store };
}
const stops = [{ address: '1 A St' }, { address: '2 B St' }];
const tick = () => new Promise((r) => setTimeout(r, 0));

(async () => {
  let w = world('0', { status: 200, body: {} });
  w.ctx.fmRenderMap('fm', stops); await tick();
  ok('1. toggle OFF: the link is shown and NO image request is made',
    w.els.fm.innerHTML.indexOf('google.com/maps/dir/') !== -1 && w.calls.length === 0 && w.els.fm.innerHTML.indexOf('Show map image') !== -1);
  w = world('1', { status: 200, body: { ok: true, image: 'data:image/png;base64,AAAA', stops: 2, drawn: 2 } });
  w.ctx.fmRenderMap('fm', stops); await tick(); await tick();
  ok('2. toggle ON: the link is STILL shown', w.els.fm.innerHTML.indexOf('google.com/maps/dir/') !== -1);
  ok('3. ...one request to api/route-map with the licence AND the session',
    w.calls.length === 1 && /api\/route-map$/.test(w.calls[0].u) && w.calls[0].o.headers.Authorization === 'Bearer SD-LIC' && w.calls[0].o.headers['X-SD-Auth'] === 'TOK');
  ok('4. ...and the image lands in the map box', (w.els['fm-img'] || {}).innerHTML.indexOf('<img src="data:image/png;base64,AAAA"') === 0, (w.els['fm-img'] || {}).innerHTML);
  w = world('1', { status: 503, body: { error: { code: 'NO_MAPS_KEY' } } });
  w.ctx.fmRenderMap('fm', stops); await tick(); await tick();
  ok('5. no key on the server: says so in words and points at the link -- not an empty box',
    /no map key is configured/.test(w.els['fm-img'].innerHTML) && /link above still works/.test(w.els['fm-img'].innerHTML), w.els['fm-img'].innerHTML);
  w = world('1', { status: 200, body: { ok: true, image: 'data:image/png;base64,AAAA', stops: 15, drawn: 12 } });
  w.ctx.fmRenderMap('fm', stops); await tick(); await tick();
  ok('6. a capped image says how many stops it shows', /first 12 of 15 stops/.test(w.els['fm-img'].innerHTML));
  w = world('1', { status: 200, body: { ok: true, image: 'javascript:alert(1)', stops: 2, drawn: 2 } });
  w.ctx.fmRenderMap('fm', stops); await tick(); await tick();
  ok('7. anything that is not a data:image URL is NOT put in an <img src>', w.els['fm-img'].innerHTML.indexOf('<img') === -1);
  w = world('0', { status: 200, body: {} });
  w.ctx.fmRenderMap('fm', stops); w.ctx.fmSetMapImage(true); await tick();
  ok('8. flipping the toggle stores the choice and re-renders with the image request', w.store.sd_fm_map_image === '1' && w.calls.length === 1);
  console.log('\n' + (fail ? 'FAILED' : 'ok') + '  b33 field map toggle: ' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})().catch((e) => { console.log('HARNESS ERROR: ' + (e && e.stack || e)); process.exit(2); });
