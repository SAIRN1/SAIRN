// tests/roofing_unprovisioned_is_not_empty.js
//
// Run:  node tests/roofing_unprovisioned_is_not_empty.js
//
// "NO BONDING LETTER RECORDED" IS A CLAIM ABOUT THIS CONTRACTOR'S SURETY
// POSITION. "NO HAZARD ASSESSMENTS RECORDED" IS A CLAIM ABOUT THEIR SAFETY
// FILE. Neither is true when the table simply does not exist.
//
// `rf_bonding` and `rf_job_hazard_assessments` are two of the 26 tables
// declared in sql/ and absent from the live schema (2026-09-13 capture).
// api/sd-data.js answers both with `200 {ok:true,data:[],provisioned:false}`
// rather than a 503 -- a deliberate soft shape, and a correct one, because the
// FLAG carries the answer. Two call sites in sairnroofing.html ignored the flag:
//
//     rfLoadPrequal()  ->  cd.capacity was null  ->  "No bonding letter recorded."
//     rfLoadSafety()   ->  rfJhas was []         ->  "No hazard assessments recorded."
//
// A contractor reads the first as "you have no bond" and the second as "none
// were needed". Both are the opposite of "we could not tell you", and on a
// surety position and a safety record that difference is the whole content.
//
// THE FIX WAS ALREADY IN THE FILE THREE TIMES. Prequal documents, safety
// equipment and warranty tiers all check `provisioned===false` and print "Not
// set up yet -- run sql/...". These two call sites just never did.
//
// THE REAL FUNCTIONS ARE EXTRACTED FROM THE SHIPPED sairnroofing.html AND RUN,
// not reimplemented, so this fails if what ships changes. Same method as
// tests/roofing_jobs_load_failure.js, which is the client-side half of the same
// sweep.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const ROOT = path.join(__dirname, '..');
// RF_HTML exists so a MUTATION CONTROL can point this at a copy with the guard
// removed and confirm the suite goes RED. Without that, "14 assertions pass" is
// only evidence that the assertions run -- a test that cannot fail on the
// pre-fix source is the shape this repo keeps recording against itself. The
// default is always the shipped file.
const HTML = fs.readFileSync(process.env.RF_HTML ||
  path.join(ROOT, 'sairnroofing.html'), 'utf8').replace(/\r\n/g, '\n');

let n = 0;
function ok(cond, label) { assert.ok(cond, label); n++; console.log('  ok   ' + label); }

function grabFunction(name) {
  const start = HTML.indexOf('\nfunction ' + name + '(');
  assert.ok(start > 0, 'not found in sairnroofing.html: ' + name);
  // Brace-match from the function's opening `{`, skipping strings, template
  // literals, regex-ish slashes and comments. A naive indexOf('\n}') stops at
  // the first `}` that happens to start a line inside a template string.
  let i = HTML.indexOf('{', start), depth = 0, q = null;
  for (; i < HTML.length; i++) {
    const c = HTML[i], p = HTML[i - 1];
    if (q) {
      if (c === q && p !== '\\') q = null;
      continue;
    }
    if (c === '"' || c === "'" || c === '`') { q = c; continue; }
    if (c === '/' && HTML[i + 1] === '/') { i = HTML.indexOf('\n', i); continue; }
    if (c === '/' && HTML[i + 1] === '*') { i = HTML.indexOf('*/', i) + 1; continue; }
    if (c === '{') depth++;
    else if (c === '}') { depth--; if (!depth) return HTML.slice(start, i + 1); }
  }
  throw new Error('unterminated function ' + name);
}

// ── a DOM stub that records what each element was given ─────────────────────
function makeSandbox(dataFor) {
  const els = {};
  const el = id => (els[id] || (els[id] = {
    id: id, innerHTML: '', textContent: '', value: '', style: {}
  }));
  const calls = [];
  const sandbox = {
    console: console,
    els: els,
    calls: calls,
    $: el,
    MANAGEMENT_ROLES: { owner: true, admin: true, manager: true },
    rfSession: { role: 'owner' },
    rfEsc: s => String(s),
    rfMoney: v => String(v),
    rfLocalToday: () => '2026-09-13',
    rfPqDocs: [], rfPqReadiness: null, rfBonding: null,
    rfEquipment: [], rfSafetyBoard: null, rfJhas: [],
    rfRenderPqDocs: () => { calls.push('rfRenderPqDocs'); },
    rfRenderPqReadiness: () => { calls.push('rfRenderPqReadiness'); },
    rfRenderBonding: () => {
      calls.push('rfRenderBonding');
      // The REAL renderer's empty branch, reproduced only so the wrong
      // outcome is visible if the guard is removed. It is asserted against
      // below as the thing that must NOT appear.
      if (!sandbox.rfBonding) el('pq-bonding').innerHTML =
        '<div class="empty">No bonding letter recorded.</div>';
    },
    rfRenderEquipment: () => { calls.push('rfRenderEquipment'); },
    rfRenderJhas: () => {
      calls.push('rfRenderJhas');
      if (!sandbox.rfJhas.length) el('safety-jha').innerHTML =
        '<div class="empty">No hazard assessments recorded.</div>';
    },
    rfDataRaw: (action, resource) => {
      calls.push(action + ':' + resource);
      return Promise.resolve(dataFor(action, resource));
    }
  };
  vm.createContext(sandbox);
  vm.runInContext(grabFunction('rfPqWarn'), sandbox);
  vm.runInContext(grabFunction('rfPqRequired'), sandbox);
  vm.runInContext(grabFunction('rfSafetyWarn'), sandbox);
  vm.runInContext(grabFunction('rfJhaValidFor'), sandbox);
  vm.runInContext(grabFunction('rfLoadPrequal'), sandbox);
  vm.runInContext(grabFunction('rfLoadSafety'), sandbox);
  return sandbox;
}

// Everything provisioned EXCEPT the one resource under test.
function responder(unprovisioned) {
  return (action, resource) => {
    if (resource === unprovisioned) {
      return { ok: true, data: { provisioned: false, data: [] } };
    }
    return { ok: true, data: { provisioned: true, data: [], capacity: null,
                               readiness: null, board: null } };
  };
}

async function main() {
  console.log('roofing: an unprovisioned table is not an empty one\n');

  // ── 1. rf_bonding ────────────────────────────────────────────────────────
  console.log('1. rf_bonding -- the surety position');
  let s = makeSandbox(responder('rf_bonding'));
  await s.rfLoadPrequal();
  const bond = s.els['pq-bonding'].innerHTML;
  ok(/capacity:rf_bonding/.test(s.calls.join(',')),
     'the capacity call really was made, so this arm exercised the path');
  ok(!/No bonding letter recorded/.test(bond),
     'it does NOT say "No bonding letter recorded" -- that is a claim about the bond');
  ok(/[Nn]ot set up yet/.test(bond),
     'it says the table is not set up');
  ok(/sairnroofing_prequal_schema\.sql/.test(bond),
     'and names the migration to run, the way the three sibling resources do');
  ok(/not the same as having no bond/i.test(bond),
     'and states the distinction outright, because that is the whole finding');

  // ── 2. rf_job_hazard_assessments ─────────────────────────────────────────
  console.log('\n2. rf_job_hazard_assessments -- the safety file');
  s = makeSandbox(responder('rf_job_hazard_assessments'));
  await s.rfLoadSafety();
  const jha = s.els['safety-jha'].innerHTML;
  ok(/crew_check:rf_job_hazard_assessments/.test(s.calls.join(',')),
     'the crew_check call really was made');
  ok(!/No hazard assessments recorded/.test(jha),
     'it does NOT say "No hazard assessments recorded" on a safety record');
  ok(/[Nn]ot set up yet/.test(jha), 'it says the table is not set up');
  ok(/sairnroofing_safety_schema\.sql/.test(jha),
     'and names the migration to run');

  // ── 3. THE CONTROL, and without it arms 1 and 2 prove nothing ────────────
  // A guard that fires on EVERYTHING would pass both arms above and would be
  // useless: the honest empty state must still be reachable.
  console.log('\n3. CONTROL -- a PROVISIONED table with no rows still reads as empty');
  s = makeSandbox(() => ({ ok: true, data: { provisioned: true, data: [],
                                             capacity: null, board: null } }));
  await s.rfLoadPrequal();
  await s.rfLoadSafety();
  ok(/No bonding letter recorded/.test(s.els['pq-bonding'].innerHTML),
     'a real empty bonding table still says "No bonding letter recorded"');
  ok(/No hazard assessments recorded/.test(s.els['safety-jha'].innerHTML),
     'a real empty assessments table still says "No hazard assessments recorded"');
  ok(!/[Nn]ot set up yet/.test(s.els['pq-bonding'].innerHTML +
                               s.els['safety-jha'].innerHTML),
     'and NEITHER claims the table is missing -- the guard is not firing on everything');

  // ── 4. the siblings that were already right stay right ───────────────────
  console.log('\n4. the three siblings that already handled it are unchanged');
  for (const [res, el, sql] of [
    ['rf_prequal_documents', 'pq-docs', 'sairnroofing_prequal_schema.sql'],
    ['rf_safety_equipment', 'safety-equipment', 'sairnroofing_safety_schema.sql']
  ]) {
    s = makeSandbox(responder(res));
    await (res.indexOf('prequal') >= 0 ? s.rfLoadPrequal() : s.rfLoadSafety());
    const html = s.els[el].innerHTML;
    ok(/[Nn]ot set up yet/.test(html) && html.indexOf(sql) !== -1,
       res + ' still says not set up and names ' + sql);
  }

  console.log('\nALL ' + n + ' ASSERTIONS PASS');
}

main().catch(e => { console.error('\nFAILED: ' + e.message); process.exit(1); });
