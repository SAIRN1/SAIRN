// tests/sairnfreedom_confirmed_ttl.js
//
// REQUIREMENT: a record the server confirmed reads as confirmed for 90 days
//   from the server's last answer for it, and then as NOT confirmed until the
//   server answers for it again (a write it accepted, or a read that returned
//   it). An entry with no confirmation time -- written before the TTL existed
//   -- reads as not confirmed, so it is re-verified rather than trusted.
//
// Run:  node tests/sairnfreedom_confirmed_ttl.js
//
// THE GAP (cc b70 gap (a) on cody b61, decided by Michael in b66: "a 90-day
// re-verify TTL"): entries in sf_server_confirmed never expired, so a row
// deleted out-of-band read as confirmed forever. This suite also EXECUTES
// sfConfirmOnServer, which cc b70 gap (c) noted no test did (D4c is a regex).
//
// sfConfirmedRead and sfConfirmOnServer are lifted from the shipped file and
// run in a vm against a fake Storage and a controllable clock.

'use strict';

const fs = require('fs');
const path = require('path');
const vm = require('vm');

const FILE = path.join(__dirname, '..', 'sairnfreedom.html');
const html = fs.readFileSync(FILE, 'utf8');
const DAY = 86400000;
const NOW = Date.parse('2026-10-29T12:00:00Z');

let pass = 0, fail = 0;
function check(name, cond, detail) {
  if (cond) { pass++; console.log('  ok   ' + name); }
  else { fail++; console.log('  FAIL ' + name + (detail ? '\n       ' + detail : '')); }
}

function lift() {
  const start = html.indexOf("var SF_CONFIRMED_KEY='sf_server_confirmed';");
  const sig = 'function sfConfirmOnServer(resource,ids){';
  const head = html.indexOf(sig);
  if (start < 0 || head < start || html.split(sig).length !== 2) return null;
  let i = html.indexOf('{', head), depth = 0;
  for (; i < html.length; i++) {
    if (html[i] === '{') depth++;
    else if (html[i] === '}' && --depth === 0) break;
  }
  return html.slice(start, i + 1);
}

function world(init, now) {
  const m = new Map(Object.entries(init || {}));
  const localStorage = {
    getItem: (k) => (m.has(k) ? m.get(k) : null),
    setItem: (k, v) => { m.set(k, String(v)); }
  };
  const clock = { t: now };
  class FixedDate extends Date {
    constructor(...a) { if (a.length) super(...a); else super(clock.t); }
    static now() { return clock.t; }
  }
  const ctx = {
    localStorage, JSON, Array, Object, String, Number, Math, Date: FixedDate,
    st: (k, v) => { localStorage.setItem(k, JSON.stringify(v)); return true; },
    console: { warn() {}, error() {}, log() {} }
  };
  vm.createContext(ctx);
  vm.runInContext(src, ctx);
  const confirmed = (res) => {
    const r = ctx.sfConfirmedRead();
    return { state: r.state, ids: Array.isArray(r.map[res]) ? r.map[res].slice() : [] };
  };
  return { ctx, m, clock, confirmed };
}

const src = lift();
console.log('sairnfreedom.html -- server confirmations expire after 90 days and are re-verified');
if (!src) { console.log('COULD NOT RUN: sfConfirmedRead / sfConfirmOnServer are not in ' + FILE + ' exactly once'); process.exit(2); }

const R = 'sf_trustee_audits';
{
  const w = world({}, NOW);
  w.ctx.sfConfirmOnServer(R, ['A1']);
  check('T1 a confirmation made now reads as confirmed', w.confirmed(R).ids.includes('A1'), JSON.stringify(w.confirmed(R)));
  w.clock.t = NOW + 89 * DAY;
  check('T2 ...and still at 89 days', w.confirmed(R).ids.includes('A1'), JSON.stringify(w.confirmed(R)));
  w.clock.t = NOW + 91 * DAY;
  check('T3 ...and NOT at 91 days: an expired confirmation reads as not confirmed',
    w.confirmed(R).state === 'ok' && !w.confirmed(R).ids.includes('A1'), JSON.stringify(w.confirmed(R)));
  w.ctx.sfConfirmOnServer(R, ['A1']);
  check('T4 the server answering for it again re-confirms it from that moment',
    w.confirmed(R).ids.includes('A1'), JSON.stringify(w.confirmed(R)));
  w.clock.t = NOW + 91 * DAY + 89 * DAY;
  check('T5 ...for another 90 days from the re-confirmation, not from the first',
    w.confirmed(R).ids.includes('A1'), JSON.stringify(w.confirmed(R)));
}
{
  // Written before the TTL existed: an id list with no confirmation times.
  const w = world({ sf_server_confirmed: JSON.stringify({ [R]: ['OLD1', 'OLD2'] }) }, NOW);
  check('T6 a legacy entry with no confirmation time reads as NOT confirmed (re-verify, never assume)',
    w.confirmed(R).state === 'ok' && w.confirmed(R).ids.length === 0, JSON.stringify(w.confirmed(R)));
  w.ctx.sfConfirmOnServer(R, ['OLD1']);
  check('T7 ...and the server answering for one re-confirms that one only',
    JSON.stringify(w.confirmed(R).ids) === '["OLD1"]', JSON.stringify(w.confirmed(R)));
}
{
  const w = world({ sf_server_confirmed: JSON.stringify({ [R]: ['A1'] }), sf_server_confirmed_at: '{not json' }, NOW);
  check('T8 an unreadable confirmation-time record reads as COULD NOT TELL, not as confirmed or as empty',
    w.confirmed(R).state === 'unreadable', JSON.stringify(w.confirmed(R)));
  w.ctx.sfConfirmOnServer(R, ['A2']);
  check('T9 ...and is never overwritten while unreadable', w.m.get('sf_server_confirmed_at') === '{not json');
}
{
  const w = world({}, NOW);
  w.ctx.sfConfirmOnServer(R, ['A1', null, undefined, 7]);
  check('T10 ids are stored as strings and null/undefined are skipped',
    JSON.stringify(w.confirmed(R).ids) === '["A1","7"]', JSON.stringify(w.confirmed(R)));
}

console.log('\n' + (fail ? 'FAILED' : 'ok') + '  sairnfreedom confirmed-set TTL: ' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
