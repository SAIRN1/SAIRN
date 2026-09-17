// tests/roofing_claim_photo_export.js
//
// Run:  node tests/roofing_claim_photo_export.js
//
// The reports list exported `claims` and nothing else from that pair.
// api/_resources/sairnroofing.js says what the pair is, in its own words:
// "rf_claims is a MUTABLE claim record (evolves over a 45-90 day lifecycle);
// rf_claim_photos is APPEND-ONLY tagged evidence." An adjuster dispute is about
// the photographs, and there was no way to produce them.
//
// THE LOADER IS DRIVEN, NOT READ. It fans out per claim -- the server requires
// payload.claim_id and gates each read on the same assignment rule as the claim
// -- so the things worth asserting are behavioural: does it ask once per claim,
// does a refused claim get NAMED rather than silently dropped, does it carry
// the claim's own identifiers onto each photo row, and does it keep the image
// bytes OUT of the file while saying that it did.
//
// THE LAST ONE IS THE POINT. photo_base64 is a full data URL, routinely
// megabytes. Inlining it would produce a CSV nothing can open, and dropping it
// silently would be a file that looks like an evidence inventory and does not
// say what it is missing. The row records photo_present and photo_chars
// instead, and both are asserted.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

// RF_HTML lets a negative control point this suite at a MUTATED COPY in a temp
// directory instead of patching the tracked file and restoring it afterwards.
// Same convention SB_HTML, SV_HTML, DNT_HTML, LAW_HTML and BLD_HTML already
// carry. Unset -- every ordinary run, including CI -- this is exactly what it
// was.
const html = fs.readFileSync(process.env.RF_HTML
  || path.join(__dirname, '..', 'sairnroofing.html'), 'utf8')
  .replace(/\r\n/g, '\n');

let pass = 0, fail = 0;
const ASYNC = [];
function test(name, fn) { ASYNC.push([name, fn]); }
function section(t) { ASYNC.push([t, null]); }

function grab(sig, terminator) {
  const at = html.indexOf(sig);
  assert.ok(at > 0, 'not found in sairnroofing.html: ' + sig);
  const end = html.indexOf(terminator, at);
  assert.ok(end > at, 'terminator not found after ' + sig);
  return html.slice(at, end + terminator.length);
}

const BIG = 'data:image/jpeg;base64,' + 'A'.repeat(4096);

function harness(opts) {
  opts = opts || {};
  const asked = [];
  const claims = opts.claims === undefined
    ? [{ claim_id: 'CL-1', job_id: 'JOB-1', carrier: 'Statewide', claim_number: 'SW-88' },
       { claim_id: 'CL-2', job_id: 'JOB-2', carrier: 'Northfield', claim_number: 'NF-12' }]
    : opts.claims;
  const photos = opts.photos || {
    'CL-1': [{ photo_id: 'RFCPH-1', claim_id: 'CL-1', phase: 'pre_repair',
               elevation: 'north', damage_type: 'hail bruising',
               photo_base64: BIG, captured_by: 'EMP-4',
               created_at: '2026-09-04T12:00:00Z' },
             { photo_id: 'RFCPH-2', claim_id: 'CL-1', phase: 'post_repair',
               elevation: 'north', damage_type: '', photo_base64: '',
               captured_by: 'EMP-4', created_at: '2026-09-09T12:00:00Z' }],
    'CL-2': []
  };
  const ctx = {
    JSON, Object, Array, String, Number, Math, Promise,
    RF_FANOUT_WIDTH: 6,
    rfDataRaw: (action, resource, payload) => {
      asked.push({ action, resource, payload });
      if (resource === 'rf_claims') {
        if (opts.claimsRefuse) return Promise.resolve({ ok: false, status: 403, code: 'FORBIDDEN' });
        if (opts.claimsUnprovisioned) {
          return Promise.resolve({ ok: true, data: { data: [], provisioned: false } });
        }
        return Promise.resolve({ ok: true, data: { data: claims, provisioned: true } });
      }
      const id = payload && payload.claim_id;
      if (opts.refuseClaim === id) {
        return Promise.resolve({ ok: false, status: 403, code: 'FORBIDDEN' });
      }
      return Promise.resolve({ ok: true, data: { data: photos[id] || [], provisioned: true } });
    }
  };
  ctx.globalThis = ctx;
  vm.createContext(ctx);
  vm.runInContext(grab('function rfLoadClaimPhotosAcrossClaims(){', '\n}'), ctx,
    { filename: 'roofing-claim-photo-extract.js' });
  return { ctx, asked };
}

section('1. it fans out per claim, because the read is per claim');

test('one photo read per claim, and the claim list read exactly once', async () => {
  const h = harness();
  await h.ctx.rfLoadClaimPhotosAcrossClaims();
  const claimReads = h.asked.filter((a) => a.resource === 'rf_claims');
  const photoReads = h.asked.filter((a) => a.resource === 'rf_claim_photos');
  assert.strictEqual(claimReads.length, 1, 'the claim list was read ' + claimReads.length + ' times');
  assert.deepStrictEqual(photoReads.map((a) => a.payload.claim_id).sort(), ['CL-1', 'CL-2']);
});

test('every photo row carries its claim identifiers, not just claim_id', async () => {
  const h = harness();
  const r = await h.ctx.rfLoadClaimPhotosAcrossClaims();
  const rows = r.data.data;
  assert.strictEqual(rows.length, 2, 'expected CL-1s two photos, got ' + rows.length);
  assert.strictEqual(rows[0].claim_number, 'SW-88');
  assert.strictEqual(rows[0].carrier, 'Statewide');
  assert.strictEqual(rows[0].job_id, 'JOB-1');
});

section('2. a claim that refuses is NAMED, not quietly missing');

test('a 403 on one claim leaves the other claim\'s evidence in the file', async () => {
  const h = harness({ refuseClaim: 'CL-1' });
  const r = await h.ctx.rfLoadClaimPhotosAcrossClaims();
  assert.strictEqual(r.data.data.length, 0, 'CL-1 rows appeared despite the refusal');
  assert.strictEqual(r.fanout.jobs, 2);
  assert.strictEqual(r.fanout.failed.length, 1, JSON.stringify(r.fanout));
  assert.ok(r.fanout.failed[0].indexOf('CL-1') === 0, r.fanout.failed[0]);
});

test('a refused CLAIM LIST is a refusal, not an empty export', async () => {
  // An empty list standing in for a broken read is the failure this whole
  // phase came out of. The caller prints the refusal; it must reach it.
  const h = harness({ claimsRefuse: true });
  const r = await h.ctx.rfLoadClaimPhotosAcrossClaims();
  assert.strictEqual(r.ok, false, 'a 403 on the claim list became a clean result');
});

test('an unprovisioned table is reported as unprovisioned, not as zero rows', async () => {
  const h = harness({ claimsUnprovisioned: true });
  const r = await h.ctx.rfLoadClaimPhotosAcrossClaims();
  assert.strictEqual(r.data.provisioned, false, JSON.stringify(r.data));
});

section('3. the image bytes stay OUT of the file, and the file says so');

test('photo_base64 is not carried into the exported column set', async () => {
  const h = harness();
  const r = await h.ctx.rfLoadClaimPhotosAcrossClaims();
  const at = html.indexOf("key:'claim_photos'");
  assert.ok(at > 0, 'the claim_photos report entry is gone');
  const entry = html.slice(at, html.indexOf('\n  },', at));
  assert.ok(entry.indexOf("'photo_base64'") === -1,
    'the export declares a photo_base64 column -- a CSV cell is not where a '
    + 'multi-megabyte data URL belongs');
  assert.ok(entry.indexOf("['photo_present','photo_present']") !== -1
    && entry.indexOf("['photo_chars','photo_chars']") !== -1,
    'the inventory columns that say what the file does NOT contain are gone');
  // And the loader really computes them.
  assert.strictEqual(r.data.data[0].photo_present, 'yes');
  assert.strictEqual(r.data.data[0].photo_chars, BIG.length);
});

test('a row with NO stored image says no rather than looking the same', async () => {
  const h = harness();
  const r = await h.ctx.rfLoadClaimPhotosAcrossClaims();
  const empty = r.data.data.find((x) => x.photo_id === 'RFCPH-2');
  assert.strictEqual(empty.photo_present, 'no');
  assert.strictEqual(empty.photo_chars, 0);
});

section('4. the report is registered, gated, and reachable');

test('claim_photos is in RF_REPORTS with its own loader and a stated gate', () => {
  const at = html.indexOf("key:'claim_photos'");
  const entry = html.slice(at, html.indexOf('\n  },', at));
  assert.ok(entry.indexOf('load:function(){return rfLoadClaimPhotosAcrossClaims();}') !== -1,
    'the per-claim loader is not wired -- a plain read would 400 with no claim_id');
  assert.ok(/gate:'[^']*image FILES are not in this CSV/.test(entry),
    'the gate text no longer states that the images are not in the file');
});

(async function run() {
  for (const [name, fn] of ASYNC) {
    if (!fn) { console.log('\n' + name); continue; }
    try { await fn(); console.log('  ok   ' + name); pass++; }
    catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
  }
  console.log('\n' + (fail ? 'FAILED' : 'ok') + '  roofing_claim_photo_export: '
    + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
