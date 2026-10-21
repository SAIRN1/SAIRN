// tests/sairnroofing_unreadable_reads.js
// Run: node tests/sairnroofing_unreadable_reads.js
//
// cody b35 routed defect 7. CONCEPT: a read that could not answer, or a table
// that does not exist, is SAID on screen and never rendered as an empty list --
// on a job-hazard panel and a warranty panel, an empty list reads as "none".
//
//   JHA  rfLoadSafety():      `(j.ok && j.data) || {}` turned a refused or failed
//        crew_check into {}, so rfRenderJhas printed "No hazard assessments
//        recorded."
//   WARR rfLoadWarranties():  `(a.ok && a.data) || {}` did the same for job
//        warranties, and provisioned:false was never read at all -- an absent
//        table printed "No roofs registered yet."
//
// rfLoadSafety and rfLoadWarranties are EXTRACTED BY NAME from the shipped
// sairnroofing.html and run in a vm with rfDataRaw stubbed per resource. An
// extraction that fails REFUSES (exit 2) rather than testing a copy.
//
// Exit: 0 all passed - 1 an arm FAILED - 2 COULD NOT RUN

'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const FILE = process.argv[2] || path.join(__dirname, '..', 'sairnroofing.html');
const html = fs.readFileSync(FILE, 'utf8');
function grab(head) {
  const i = html.indexOf(head);
  if (i < 0 || html.indexOf(head, i + 1) !== -1) {
    console.log('COULD NOT RUN: "' + head + '" found ' + (i < 0 ? 0 : 'more than one') + ' time(s) in ' + FILE);
    process.exit(2);
  }
  return html.slice(i, html.indexOf('\n}\n', i) + 2);
}
const SRC = grab('function rfLoadSafety(){') + '\n' + grab('function rfLoadWarranties(){');

let pass = 0, fail = 0;
function check(name, cond, detail) {
  if (cond) { pass++; console.log('  ok   ' + name); }
  else { fail++; console.log('  FAIL ' + name + (detail ? '\n       ' + String(detail).slice(0, 300) : '')); }
}

// answers: { 'action resource': rfDataRaw result }
async function run(fn, answers) {
  const els = {};
  const el = (id) => (els[id] = els[id] || { innerHTML: '', textContent: '', style: {}, value: '' });
  const rendered = { jhas: null, warranties: null };
  const ctx = {
    $: el, MANAGEMENT_ROLES: { owner: true }, rfSession: { role: 'owner', token: 't' },
    rfLocalToday: () => '2026-10-21', rfSafetyWarn: () => undefined, rfJhaValidFor: () => undefined,
    rfWarrWarnDays: () => undefined,
    rfEsc: (s) => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;'),
    rfRenderEquipment: () => {}, rfRenderWarrTiers: () => {},
    rfRenderJhas: () => { rendered.jhas = ctx.rfJhas; },
    rfRenderWarranties: () => { rendered.warranties = ctx.rfWarranties; },
    rfEquipment: [], rfJhas: null, rfSafetyBoard: null, rfWarrTiers: [], rfWarrTierEval: null, rfWarranties: null,
    rfDataRaw: (action, resource) => Promise.resolve(answers[action + ' ' + resource]
      || { ok: true, status: 200, data: { ok: true, data: [] }, msg: '', code: '' }),
  };
  vm.createContext(ctx);
  vm.runInContext(SRC, ctx);
  await ctx[fn]();
  return { els, rendered };
}
const H = (r, id) => (r.els[id] || {}).innerHTML || '';
const OK = (data) => ({ ok: true, status: 200, data: Object.assign({ ok: true }, data), msg: '', code: '' });
const ERR = (status, code, msg) => ({ ok: false, status, data: { error: { code, message: msg } }, msg, code });
const SAFETY_BASE = { 'read rf_safety_equipment': OK({ data: [] }), 'board rf_safety_equipment': OK({ board: { disclaimer: 'd' } }) };
const WARR_BASE = { 'read rf_warranty_tiers': OK({ data: [], availability: null }) };

(async () => {
  console.log('JHA (rfLoadSafety -> crew_check rf_job_hazard_assessments)');
  let r = await run('rfLoadSafety', Object.assign({}, SAFETY_BASE, { 'crew_check rf_job_hazard_assessments': ERR(500, 'UPSTREAM', 'Upstream error') }));
  check('J1. a FAILED read is not rendered as a list', r.rendered.jhas === null, JSON.stringify(r.rendered));
  check('J2. ...it says it could not load, and that this is not "none"',
    /Upstream error|could not/i.test(H(r, 'safety-jha')) && /not the same as having no hazard assessments/i.test(H(r, 'safety-jha')),
    H(r, 'safety-jha'));
  r = await run('rfLoadSafety', Object.assign({}, SAFETY_BASE, { 'crew_check rf_job_hazard_assessments': ERR(0, 'NETWORK', 'Network error — check your connection.') }));
  check('J3. a network failure the same', r.rendered.jhas === null && /not the same as having no hazard assessments/i.test(H(r, 'safety-jha')), H(r, 'safety-jha'));
  r = await run('rfLoadSafety', Object.assign({}, SAFETY_BASE, { 'crew_check rf_job_hazard_assessments': OK({ provisioned: false, data: [] }) }));
  check('J4. control: provisioned:false still says not set up', r.rendered.jhas === null && /Not set up yet/.test(H(r, 'safety-jha')), H(r, 'safety-jha'));
  r = await run('rfLoadSafety', Object.assign({}, SAFETY_BASE, { 'crew_check rf_job_hazard_assessments': OK({ data: [] }) }));
  check('J5. control: a real empty answer IS rendered (genuinely none)', Array.isArray(r.rendered.jhas) && r.rendered.jhas.length === 0, JSON.stringify(r.rendered));

  console.log('WARRANTIES (rfLoadWarranties -> read rf_job_warranties)');
  r = await run('rfLoadWarranties', Object.assign({}, WARR_BASE, { 'read rf_job_warranties': ERR(500, 'UPSTREAM', 'Upstream error') }));
  check('W1. a FAILED read is not rendered as "No roofs registered yet"', r.rendered.warranties === null, JSON.stringify(r.rendered));
  check('W2. ...it says it could not load, and that this is not "none"',
    /Upstream error|could not/i.test(H(r, 'warr-list')) && /not the same as/i.test(H(r, 'warr-list')), H(r, 'warr-list'));
  r = await run('rfLoadWarranties', Object.assign({}, WARR_BASE, { 'read rf_job_warranties': ERR(403, 'FORBIDDEN', 'Forbidden') }));
  check('W3. FORBIDDEN says the role cannot see them', r.rendered.warranties === null && /role cannot see/i.test(H(r, 'warr-list')), H(r, 'warr-list'));
  r = await run('rfLoadWarranties', Object.assign({}, WARR_BASE, { 'read rf_job_warranties': OK({ provisioned: false, data: [] }) }));
  check('W4. provisioned:false says not set up, never "No roofs registered yet"',
    r.rendered.warranties === null && /Not set up yet/.test(H(r, 'warr-list')), H(r, 'warr-list'));
  r = await run('rfLoadWarranties', Object.assign({}, WARR_BASE, { 'read rf_job_warranties': OK({ data: [] }) }));
  check('W5. control: a real empty answer IS rendered (genuinely none)', Array.isArray(r.rendered.warranties) && r.rendered.warranties.length === 0, JSON.stringify(r.rendered));

  console.log('\n' + (fail ? 'FAILED' : 'ok') + '  sairnroofing unreadable reads: ' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})().catch((e) => { console.log('HARNESS ERROR: ' + (e && e.stack || e)); process.exit(2); });
