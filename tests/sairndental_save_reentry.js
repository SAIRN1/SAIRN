// tests/sairndental_save_reentry.js
//
// REQUIREMENT: a second press of "Send Response" on a patient complaint while
// the first press's request is still in flight sends NO second response --
// and the hold is released once that request answers, is refused, or fails.
//
// Run:  node tests/sairndental_save_reentry.js [path-to-sairndental.html]
//
// THE DEFECT (cody b64 re-entry sweep, the shape cody b63 fixed in
// sairnmechanical saveDoc). respondToComplaint AWAITS the complaint-respond
// endpoint before it re-renders, so the reply box keeps its text and the
// button stays live for that whole wait. The endpoint
// (api/sairndental/complaint-respond.js) reads the thread fresh and APPENDS
// the text, so a second press posted the same reply into the patient's
// complaint thread twice -- a patient-facing message, on a regulated record.
//
//   R1  two presses while the request is in flight: ONE request, and the
//       second press is told why.
//   R2  once it answers, the next press goes through.
//   R3  after a REFUSED request and after a NETWORK failure, it is released.
//
// The function is lifted from the shipped file by brace matching and run in a
// vm with stubs; no browser, no network. An extraction that fails exits 2.
// Exit: 0 all passed - 1 an arm FAILED - 2 COULD NOT RUN

'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const FILE = process.argv[2] || path.join(__dirname, '..', 'sairndental.html');
const html = fs.readFileSync(FILE, 'utf8').replace(/\r\n/g, '\n');

let pass = 0, fail = 0, finished = false;
function check(name, cond, detail) {
  if (cond) { pass++; console.log('  ok   ' + name); }
  else { fail++; console.log('  FAIL ' + name + (detail ? '\n       ' + String(detail).slice(0, 400) : '')); }
}
function lift(head) {
  const i = html.indexOf(head);
  if (i < 0 || html.indexOf(head, i + 1) !== -1) {
    console.log('COULD NOT RUN: "' + head + '" found ' + (i < 0 ? 0 : 'more than one') + ' time(s) in ' + FILE);
    process.exit(2);
  }
  let k = html.indexOf('{', i), depth = 0;
  for (; k < html.length; k++) {
    if (html[k] === '{') depth++;
    else if (html[k] === '}' && --depth === 0) return html.slice(i, k + 1);
  }
  console.log('COULD NOT RUN: unbalanced ' + head); process.exit(2);
}
// The hold's declaration is lifted if it exists, so the pre-fix file (no
// declaration, no reference) runs unchanged and R1 measures the fix.
const guardDecl = (html.match(/var dntComplaintResponding\s*=\s*false;/) || [''])[0];
const SRC = guardDecl + '\n' + lift('async function respondToComplaint(id, action) {');

const flush = () => new Promise((r) => setImmediate(r));
const okReply = { status: 200, json: { ok: true, status: 'Awaiting Patient', messages: [{ from: 'owner', text: 'We are sorry' }] } };

function world(answer) {
  const store = { dnt_complaints_list: JSON.stringify([{ id: 'CP-1', status: 'Open', messages: [] }]) };
  const ctx = {
    toasts: [], requests: [],
    JSON, Object, Array, String, Promise,
    prole: 'owner', COMPLAINT_RESPOND_API: 'https://example.invalid/complaint-respond',
    $: (id) => (id === 'cp-reply-CP-1' ? { value: 'We are sorry' } : null),
    dntLicenseKey: () => 'DNT-LIC',
    complaints: () => JSON.parse(store.dnt_complaints_list),
    st: (k, v) => { store[k] = JSON.stringify(v); return true; },
    rComplaints() {},
    toast: (m) => ctx.toasts.push(String(m)),
    fetch: (url, opts) => {
      ctx.requests.push(JSON.parse(opts.body));
      return Promise.resolve(answer()).then((a) => ({ ok: a.status < 300, status: a.status, json: () => Promise.resolve(a.json) }));
    }
  };
  vm.createContext(ctx); vm.runInContext(SRC, ctx);
  return ctx;
}

(async () => {
  console.log('1. one response at a time while the request is in flight');
  {
    // EVERY held request is settled below -- an unsettled one would end the
    // run with the IIFE waiting, and node exits 0 on that.
    const held = [];
    let holding = true;
    const w = world(() => (holding ? new Promise((r) => held.push(r)) : okReply));
    const first = w.respondToComplaint('CP-1', 'reply');
    await flush();
    const second = w.respondToComplaint('CP-1', 'reply');   // the double press
    await flush();
    check('R1 a second press while the request is in flight sends NO second response, and says so',
      w.requests.length === 1 && w.toasts.some((t) => /Still sending/.test(t)),
      JSON.stringify({ requests: w.requests.length, toasts: w.toasts }));
    holding = false;
    held.forEach((r) => r(okReply));
    await first; await second; await flush();
    const before = w.requests.length;
    await w.respondToComplaint('CP-1', 'reply');
    check('R2 once the request answers, the next press goes through',
      w.requests.length === before + 1 && w.toasts[w.toasts.length - 1] === 'Response sent',
      JSON.stringify({ before, requests: w.requests.length, toasts: w.toasts }));
  }
  console.log('2. the hold is released whichever way the request ends');
  for (const [label, answer] of [
    ['a REFUSED request', () => ({ status: 502, json: { error: { message: 'Could not save -- try again' } } })],
    ['a NETWORK failure', () => Promise.reject(new Error('offline'))]
  ]) {
    const w = world(answer);
    await w.respondToComplaint('CP-1', 'reply');
    await w.respondToComplaint('CP-1', 'reply');
    check('R3 after ' + label + ' the next press is not held: two presses, two requests',
      w.requests.length === 2 && !w.toasts.some((t) => /Still sending/.test(t)),
      JSON.stringify({ requests: w.requests.length, toasts: w.toasts }));
  }
  finished = true;
  console.log('\n' + (fail ? 'FAILED' : 'ok') + '  sairndental save re-entry: ' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})().catch((e) => { console.log('COULD NOT RUN: ' + e.stack); process.exit(2); });
// A run that ends with an arm still waiting (the IIFE unsettled) exits 0 in
// node with nothing printed. It must read as COULD NOT RUN.
process.on('exit', () => { if (!finished) { console.log('COULD NOT RUN: the run ended before its last arm'); process.exitCode = 2; } });
