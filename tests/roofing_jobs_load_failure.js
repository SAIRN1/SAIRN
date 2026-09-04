// tests/roofing_jobs_load_failure.js
//
// Run:  node tests/roofing_jobs_load_failure.js
//
// "NO JOBS YET" IS A CLAIM ABOUT THIS CONTRACTOR'S BUSINESS.
//
// rfData() returns null on ANY failure -- an expired session, a 403, a 500, a
// dead connection. rfLoadJobs() did `currentJobs = data || []`, so a roofer
// whose session had lapsed was shown:
//
//     "No jobs yet. Click '+ New Job' to add one."
//
// while their real job board sat on the server -- and was invited to create a
// job that already exists. The same null reached two more places: the claim
// form's job picker said "Add a job first" to somebody filing an insurance
// claim against an existing job, and refreshCurrentEditingJob() filtered over
// an empty array and nulled the job being edited, silently stopping the
// measurement and estimate tabs from refreshing after a save.
//
// This is the client-side half of the server sweep finished earlier today: the
// endpoints now refuse honestly, and it would count for nothing if the browser
// rendered a refusal as "none".
//
// The functions are extracted from the real sairnroofing.html and driven, so
// this fails if what ships changes.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const ROOT = path.join(__dirname, '..');
const HTML = fs.readFileSync(path.join(ROOT, 'sairnroofing.html'), 'utf8').replace(/\r\n/g, '\n');

function grab(startMarker, endMarker) {
  const s = HTML.indexOf(startMarker);
  assert.ok(s > 0, 'not found in sairnroofing.html: ' + startMarker);
  const e = HTML.indexOf(endMarker, s);
  assert.ok(e > s, 'unterminated: ' + startMarker);
  return HTML.slice(s, e + endMarker.length);
}

let n = 0;
function ok(cond, label) { assert.ok(cond, label); n++; }
function eq(a, b, label) { assert.deepStrictEqual(a, b, label); n++; }

// A stand-in DOM: one #jobs-list element and one #clm-job <select>.
function makeCtx(readResult) {
  const els = {
    'jobs-list': { innerHTML: '' },
    'clm-job': { innerHTML: '' }
  };
  const ctx = {
    console, Array, String, Promise, JSON,
    currentJobs: [],
    editingJobId: 'RF-1',
    currentEditingJob: null,
    toasts: [],
    toast: function (m) { ctx.toasts.push(m); },
    rfEsc: function (v) { return String(v == null ? '' : v); },
    renderMeasurementTab: function () { ctx.rendered = (ctx.rendered || 0) + 1; },
    renderEstimateTab: function () { ctx.rendered = (ctx.rendered || 0) + 1; },
    $: function (id) { return els[id] || null; },
    // The real contract: null on ANY failure, an array on success.
    rfData: function () { return Promise.resolve(readResult); }
  };
  ctx.els = els;
  vm.createContext(ctx);
  vm.runInContext(
    grab('var rfJobsLoadFailed=false;', '\n}') + '\n' +
    grab('function rJobs(){', "'</tbody></table>';\n}") + '\n' +
    grab('function rfFillClaimJobs(){', 'rfLoadJobs().then(fill);\n}') + '\n' +
    grab('function refreshCurrentEditingJob(){', 'renderEstimateTab();}\n  });\n}'),
    ctx
  );
  return ctx;
}

const JOBS = [{ id: 'RF-1', name: 'Ruiz re-roof', address: '1 Elm', job_class: 'residential', status: 'lead' }];

async function main() {
  // ── the failure path ────────────────────────────────────────────────────
  {
    const c = makeCtx(null);
    const out = await c.rfLoadJobs();
    eq(out, null, 'a failed load returns null, not an empty array -- callers must be able to tell');
    eq(c.currentJobs, [], 'nothing was invented');
    ok(c.rfJobsLoadFailed === true, 'the failure is remembered');
    const html = c.els['jobs-list'].innerHTML;
    ok(!/No jobs yet/.test(html),
       'THE BUG: a failed load still tells the contractor they have no jobs');
    ok(!/\+ New Job/.test(html),
       'and still invites them to create one that already exists');
    ok(/Could not load your jobs/.test(html), 'it says the load failed');
    ok(/does not mean you have none/.test(html),
       'and says plainly that this is not a statement about their business');
  }

  // A non-array body is the same class of answer as null.
  for (const bad of [undefined, {}, 'nope', 0]) {
    const c = makeCtx(bad);
    const out = await c.rfLoadJobs();
    eq(out, null, 'a non-array read (' + JSON.stringify(bad) + ') is treated as a failure');
    ok(/Could not load your jobs/.test(c.els['jobs-list'].innerHTML), 'and is disclosed');
  }

  // ── the success path is untouched ───────────────────────────────────────
  {
    const c = makeCtx(JOBS);
    const out = await c.rfLoadJobs();
    eq(out.length, 1, 'a good load returns the rows');
    ok(c.rfJobsLoadFailed === false, 'and clears the failure flag');
    const html = c.els['jobs-list'].innerHTML;
    ok(/Ruiz re-roof/.test(html), 'the job renders');
    ok(!/Could not load/.test(html), 'with no failure banner');
  }

  // A genuinely empty board still says so. This is the distinction that makes
  // the fix worth anything: empty and unreadable must not collapse together.
  {
    const c = makeCtx([]);
    await c.rfLoadJobs();
    const html = c.els['jobs-list'].innerHTML;
    ok(/No jobs yet/.test(html), 'a REAL empty board still reads "No jobs yet"');
    ok(!/Could not load/.test(html), 'and is not mislabelled as a failure');
  }

  // ── a stale list is marked, not silently served as current ──────────────
  {
    const c = makeCtx(JOBS);
    await c.rfLoadJobs();                 // succeeds, cache populated
    c.rfData = function () { return Promise.resolve(null); };
    await c.rfLoadJobs();                 // now fails
    eq(c.currentJobs.length, 1, 'the cache is NOT wiped by a failed refresh');
    const html = c.els['jobs-list'].innerHTML;
    ok(/Ruiz re-roof/.test(html), 'the last-known list is still shown');
    ok(/Could not load your jobs/.test(html),
       'but carries the warning -- a stale list served as current is the other half of this bug');
  }

  // ── the claim form's job picker ─────────────────────────────────────────
  {
    const c = makeCtx(null);
    await c.rfFillClaimJobs();
    const html = c.els['clm-job'].innerHTML;
    ok(!/Add a job first/.test(html),
       'THE BUG: somebody filing an insurance claim was told to create a job that exists');
    ok(/Could not load jobs/.test(html), 'the picker says the load failed instead');
  }
  {
    const c = makeCtx([]);
    await c.rfFillClaimJobs();
    ok(/Add a job first/.test(c.els['clm-job'].innerHTML),
       'a genuinely empty board still says "Add a job first"');
  }

  // ── the job being edited ────────────────────────────────────────────────
  {
    const c = makeCtx(JOBS);
    await c.rfLoadJobs();
    c.currentEditingJob = JOBS[0];
    c.rfData = function () { return Promise.resolve(null); };
    await c.refreshCurrentEditingJob();
    ok(c.currentEditingJob !== null,
       'a failed refresh no longer nulls the job being edited and blanks its tabs');
    ok(c.toasts.some((t) => /may be out of date/.test(t)),
       'and the user is told the view may be stale rather than watching it silently stop updating');
  }

  // ── the shape is gone ───────────────────────────────────────────────────
  {
    const code = HTML.split('\n').filter((l) => !/^\s*\/\//.test(l)).join('\n');
    ok(!/currentJobs\s*=\s*data\s*\|\|\s*\[\]/.test(code),
       'sairnroofing.html still turns a failed jobs read into an empty board');
  }

  console.log('roofing_jobs_load_failure: ' + n + '/' + n + ' assertions passed');
}

main().catch((e) => { console.error(e.message); process.exitCode = 1; });
