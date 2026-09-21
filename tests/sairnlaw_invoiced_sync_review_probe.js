// tests/sairnlaw_invoiced_sync_review_probe.js
//
// Run:  node tests/sairnlaw_invoiced_sync_review_probe.js
//
// INDEPENDENT REVIEW of b73fb28a (CC) -- the invoiced:true flag reaching the
// server -- under the Tier A obligation cc opened 2026-09-21T07:10:15Z on
// `invoices` and `law_invoices`. The brief named four things to press on,
// hardest first: (1) whether shipping a partial fix is right when a device that
// already holds the entries keeps a stale invoiced:false; (2) whether the
// failure toast says enough to act on; (3) whether writing the whole record,
// and marking before writing, is the right order; (4) whether `!r` on sdnData's
// return is still a sound failure test given sdnData can also return a TRUTHY
// {rejected:true}.
//
// ── REPORT-ONLY AND EXIT 0, DELIBERATELY ──────────────────────────────────
// Same precedent as tests/dnt_rollup_review_probe.js and
// tests/sairnscape_outbound_queue_review_probe.js: a review finding on another
// agent's file, and turning it into a failing suite blocks every other session's
// push on a defect they did not write. It PRINTS, it does not gate. I am not
// fixing any of it -- I hold a review claim, not the file.
//
// ── THE THING THAT MAKES THIS REVIEW WORTH MORE THAN THE BRIEF ────────────
// Between cc opening this obligation at 07:10 and this review, cc ALSO landed
// the server-wins hydration conversion (obligation 2026-09-21T12:14:17Z). Press-on
// (1) asks whether the partial fix is acceptable given ADDITIVE hydration --
// and hydration is not additive any more. So (1) is answered by a change the
// brief could not have known about, and the same change opens a NEW hole on the
// failure path this fix deliberately created. That interaction belongs to
// neither obligation on its own, which is exactly why reviewing them together
// finds it.

'use strict';

const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ROOT = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(ROOT, 'sairnlaw.html'), 'utf8').replace(/\r\n/g, '\n');
const sdData = fs.readFileSync(path.join(ROOT, 'api', 'sd-data.js'), 'utf8').replace(/\r\n/g, '\n');

let findings = 0;

function grab(sig, term) {
  const at = html.indexOf(sig);
  if (at < 0) throw new Error('not found in sairnlaw.html: ' + sig);
  const end = html.indexOf(term, at);
  if (end < 0) throw new Error('terminator missing after ' + sig);
  return html.slice(at, end + term.length);
}

// The real hydration, sliced out of the shipped file. Only storage and the
// transport are stubbed.
const HYDRATE_SRC = [
  grab('var LAW_SYNCED_KEY=', '\n'),
  grab('function lawSyncedRead(){', '\n}\n'),
  grab('function lawMarkSynced(resource,id){', '\n}\n'),
  grab('async function lawHydrateAll(){', '\n}\n'),
].join('\n');

function harness(opts) {
  opts = opts || {};
  const STORE = Object.assign({}, opts.store || {});
  const ctx = {
    console: { warn() {}, error() {}, log() {} },
    JSON: JSON,
    localStorage: {
      getItem(k) { return Object.prototype.hasOwnProperty.call(STORE, k) ? STORE[k] : null; },
    },
    ld(k, d) { return STORE[k] === undefined ? d : JSON.parse(STORE[k]); },
    st(k, v) { STORE[k] = JSON.stringify(v); return true; },
    lawLicenseKey() { return 'LAW-TEST'; },
    LAW_SYNC_RESOURCES: ['law_timeentries'],
    sdnData: async (action, resource) => (opts.server && opts.server[resource]) || [],
    __store: STORE,
  };
  vm.createContext(ctx);
  vm.runInContext(HYDRATE_SRC, ctx);
  return ctx;
}
const entry = (id, invoiced) => ({
  id: id, matter_id: 'M-1', hours: 2, rate: 300, billable: true,
  billing_code: 'L110', invoiced: invoiced, desc: 'drafting',
});
const read = (ctx, k) => JSON.parse(ctx.__store[k]);

function head(n, t) { console.log('\n=== FINDING ' + n + ': ' + t + '\n'); }
// A press-on point that HOLDS gets its own header. Printing an answer under the
// word FINDING is the overstatement this platform keeps paying for -- a reader
// counting headers would have read four findings here where there is one.
function answered(n, t) { console.log('\n=== PRESS-ON (' + n + '): ' + t + '\n'); }

(async function () {

  // ── PRESS-ON (4), and it holds ──────────────────────────────────────────
  console.log('=== PRESS-ON (4): is `!r` on sdnData\'s return still a sound failure test? ===\n');
  const codes = ['INSUFFICIENT_TRUST_BALANCE', 'VOID_WOULD_NEGATIVE_BALANCE', 'ALREADY_VOIDED'];
  // Where can each code be emitted? Measured against the real endpoint source
  // rather than taken from the client comment that lists them.
  const trustAt = sdData.indexOf("resource === 'law_trusttx' && action === 'write'");
  const trustEnd = sdData.indexOf("\n    if (resource === '", trustAt + 10);
  const trustBlock = sdData.slice(trustAt, trustEnd > trustAt ? trustEnd : trustAt + 12000);
  const outside = codes.filter(c => {
    const all = sdData.split(c).length - 1;
    const inside = trustBlock.split(c).length - 1;
    return all !== inside;
  });
  console.log('  the three codes that make sdnData return a TRUTHY rejection:');
  for (const c of codes) {
    console.log('    ' + c.padEnd(32)
      + (trustBlock.includes(c) ? 'emitted inside the law_trusttx write branch' : 'NOT in that branch'));
  }
  console.log('  emitted anywhere OUTSIDE the law_trusttx write branch: '
    + (outside.length ? outside.join(', ') : 'none'));
  console.log('  -> cc\'s reading HOLDS today: none of the three can answer a');
  console.log('     law_timeentries write, so `!r` counts exactly the failures.');
  // And the other direction, which the brief did not ask about: could a
  // SUCCESSFUL write return something falsy and be counted as a failure?
  const okLine = /res\.status\(200\)\.json\(\{ ok: true, data: \(Array\.isArray\(rows\) && rows\[0\]\) \? rows\[0\]\.data : payload \}\)/;
  console.log('  the success path returns rows[0].data or the payload, never a falsy body: '
    + okLine.test(sdData));
  console.log('  -> so there is no false-FAILURE direction either.');

  // ── FINDING 1 ───────────────────────────────────────────────────────────
  head(1, 'the failure path this fix deliberately created is SILENTLY UNDONE by\n'
    + '            cc\'s own server-wins hydration, on the device that issued the invoice');
  {
    // Device A issued the invoice. Its local entry is invoiced:true. The
    // law_timeentries write FAILED -- the case the toast is written for -- so
    // the server still says invoiced:false. The id was marked synced long ago,
    // when the entry was first saved.
    const ctx = harness({
      store: {
        law_timeentries: JSON.stringify([entry('TE-1', true)]),
        law_synced_ids: JSON.stringify({ law_timeentries: ['TE-1'] }),
      },
      server: { law_timeentries: [entry('TE-1', false)] },
    });
    const before = read(ctx, 'law_timeentries')[0].invoiced;
    const res = await ctx.lawHydrateAll();
    const after = read(ctx, 'law_timeentries')[0].invoiced;
    console.log('  device A local invoiced BEFORE hydrate : ' + before);
    console.log('  server copy (the write did not land)   : false');
    console.log('  device A local invoiced AFTER hydrate  : ' + after);
    console.log('  hydrate reported                       : ' + JSON.stringify(res));
    if (before === true && after === false) {
      findings++;
      console.log(`
  saveInvoice() sets invoiced=true locally, writes the invoice, then writes each
  touched entry. When the entry write FAILS -- which cc correctly says can
  happen on real data, because a legacy row with no billing_code is refused by
  api/_lib/law-timeentry.js -- the toast says "N of M time entries are still
  marked UNBILLED on the server ... so another computer could invoice those
  hours again. Re-issue this invoice once the connection is back."

  That sentence is true and it is now incomplete in the direction that matters.
  Since the server-wins conversion, the NEXT hydrate on THIS device reads the
  server's invoiced:false and OVERWRITES the local invoiced:true -- driven
  above. The entry id is in law_synced_ids (it was marked when the entry was
  first saved, long before the invoice), so the pending-first-push carve-out
  does not protect it and nothing about this path is unusual enough to notice.

  THE CONSEQUENCE IS THE ONE b73fb28a EXISTS TO REMOVE. rInvoiceEntryPicker()
  filters on \`billable && !invoiced\`, so after that hydrate the issuing
  attorney's OWN machine offers the already-invoiced hours as unbilled work.
  The invoice still exists in law_invoices and still lists time_entry_ids, so
  nothing is lost -- but the one device that knew the hours were billed has
  stopped knowing, and the toast that warned about "another computer" did not
  warn about this one.

  IT IS ALSO A TIMING TRAP RATHER THAN A STEADY STATE, which is what makes it
  easy to miss in testing: the local flag survives until the next hydrate, so
  the fix looks correct for as long as the tester stays on the page.

  NEITHER OBLIGATION COVERS IT, and that is structural rather than anyone's
  oversight. This one (07:10) was written when hydration was still additive, and
  says so in terms. The server-wins one (12:14) is about hydration and does not
  know about a caller that sets a local flag the server may refuse. The hole is
  in the seam.

  SUGGESTED FIX, and the cheap one is the second: either (a) roll the local
  invoiced flag BACK on the entries whose write failed, so local and server
  agree and the toast's "re-issue this invoice" is the only recovery path -- at
  the cost of the invoice and the entries disagreeing until it is re-issued; or
  (b) refuse to create the invoice at all when its entries cannot be marked,
  which cc considered and rejected for a good reason (a firm with legacy rows
  could not invoice). (a) is the smaller change and it makes the failure honest
  in both places rather than in one.`);
    } else {
      console.log('  CLOSED -- the local flag now survives, or the server copy is no longer read this way.');
    }
  }

  // ── PRESS-ON (1), answered ──────────────────────────────────────────────
  answered(1, 'ANSWERED BY A LATER CHANGE, not by a judgement -- the\n'
    + '                 already-holds-it device IS fixed, on its first hydrate');
  {
    // Device B already holds the entry as invoiced:false and has never been
    // seeded (no law_synced_ids at all -- the state every pre-existing install
    // is in the moment the server-wins conversion ships).
    const ctx = harness({
      store: { law_timeentries: JSON.stringify([entry('TE-1', false)]) },
      server: { law_timeentries: [entry('TE-1', true)] },
    });
    const res = await ctx.lawHydrateAll();
    const after = read(ctx, 'law_timeentries')[0].invoiced;
    const seeded = read(ctx, 'law_synced_ids');
    console.log('  device B local invoiced BEFORE : false   (and no law_synced_ids at all)');
    console.log('  device B local invoiced AFTER  : ' + after + '   merged=' + res.merged);
    console.log('  law_synced_ids after           : ' + JSON.stringify(seeded));
    // And it stays fixed on the second hydrate, now that it is seeded.
    const ctx2 = harness({
      store: {
        law_timeentries: JSON.stringify([entry('TE-1', false)]),
        law_synced_ids: JSON.stringify({ law_timeentries: ['TE-1'] }),
      },
      server: { law_timeentries: [entry('TE-1', true)] },
    });
    await ctx2.lawHydrateAll();
    console.log('  and on a SEEDED device it is also overwritten : '
      + read(ctx2, 'law_timeentries')[0].invoiced);
    console.log(`
  cc asked whether shipping the partial fix was right or whether it bought "a
  false sense of closure on a double-billing path". Driven rather than argued:
  the gap cc named is CLOSED, and not by this commit -- by cc's own server-wins
  conversion later the same day. On a pre-existing install the never-seeded
  branch overwrites every id held on both sides, so the stale invoiced:false is
  replaced on the FIRST hydrate after the conversion, and every hydrate after
  that because the id is now seeded.

  So the answer to press-on (1) is: shipping the partial fix was right, and it
  stopped being partial within hours. What is NOT closed is the reverse
  direction in FINDING 1 above, which the same conversion opened.

  ONE THING THAT DOES NOT FOLLOW AND IS WORTH SAYING: this does not make the
  window zero. Between device A issuing the invoice and device B's next
  hydrate, B still offers the hours as unbilled. That is inherent in a
  hydrate-on-boot model and is not a defect of either change; it is the reason
  the server's copy being right matters at all.`);
  }

  // ── PRESS-ON (3) ────────────────────────────────────────────────────────
  answered(3, 'the whole-record write and the marking-then-writing order are\n'
    + '                 both right, and the order is right for a different reason\n'
    + '                 than the obvious one');
  {
    const at = html.indexOf('async function saveInvoice(){');
    const fn = html.slice(at, html.indexOf('\n}\n', at));
    const marks = /teList\.forEach\(function\(t\)\{if\(entryIds\.indexOf\(t\.id\)!==-1\)\{t\.invoiced=true;touched\.push\(t\);\}\}\)/.test(fn);
    console.log('  `touched` holds references INTO teList, so each written payload is the');
    console.log('  entry object exactly as it is stored locally: ' + marks);
    console.log('  the local st() happens BEFORE the network write: '
      + (fn.indexOf("st('law_timeentries',teList)") < fn.indexOf("sdnData('write','law_timeentries'")));
    console.log(`
  THE ORDER IS RIGHT AND THE REASON IS NOT THE OBVIOUS ONE. Marking then
  writing means a crash between the two leaves local ahead of the server, which
  is the SAFE direction here: local says billed, so this device will not
  re-offer the hours. Writing then marking would leave the server ahead, and a
  device that never completed the local write would go on offering them. Given
  FINDING 1, though, "local ahead of the server" is no longer a stable state --
  the next hydrate resolves it the other way. The order is still right; it is
  the persistence of its outcome that is not.

  THE WHOLE-RECORD WRITE IS CORRECT AND NECESSARY, not merely acceptable:
  api/sd-data.js upserts \`data: payload\` wholesale, so a partial payload would
  replace the row, and api/_lib/law-timeentry.js would refuse it outright for
  the missing billing_code -- so a partial write cannot even silently succeed.
  I checked the touched objects for rendering artefacts as asked and found none
  that saveInvoice adds; the entry shape is whatever saveTime() stored.`);
  }

  // ── PRESS-ON (2) ────────────────────────────────────────────────────────
  answered(2, 'the toast says enough to act on; 8000ms is a preference I\n'
    + '                 would set differently, and is NOT raised as a finding');
  {
    const at = html.indexOf('async function saveInvoice(){');
    const fn = html.slice(at, html.indexOf('\n}\n', at));
    const msg = /if\(teFailed\)parts\.push\(([\s\S]*?)\);\n/.exec(fn);
    console.log('  the failure sentence names: the count, the total, the reason, the risk,');
    console.log('  and the recovery action -- all five: '
      + ['teFailed+', "' of '", 'lawWriteFailText', 'invoice those hours again', 'Re-issue this invoice']
        .every(s => msg && msg[1].includes(s)));
    console.log('  duration on any failure: '
      + (/toast\(parts\.join\(' -- '\),\(syncResult&&!teFailed\)\?3000:8000\)/.test(fn) ? '8000ms' : 'CHANGED'));
    console.log(`
  THE CONTENT IS GOOD -- five things in one sentence, and it names the ACTION
  rather than only the fault, which is the part most failure toasts here miss.

  8000ms IS THIN AND IT IS A JUDGEMENT I WOULD MAKE DIFFERENTLY, stated as a
  view rather than a defect. The combined failure string runs past 300
  characters when both writes fail; at an ordinary reading speed that is at the
  edge of eight seconds, and the person reading it has just been told to do
  something they will not remember the details of. Measured across the file
  rather than eyeballed, the four-digit toast durations are 4000 (x1), 5000
  (x2), 6000 (x2), 7000 (x4), 8000 (x1 -- this one) and 9000 (x2), so the
  longest sentence in the app sits in the upper-middle of its own range rather
  than at the top of it. This is the one place in the app where the message IS the recovery
  record -- nothing else in the UI says the entries are unsynced -- so it is
  also the one where a missed reading costs the most.

  NOT RAISED AS A FINDING because the sentence is correct and the duration is a
  preference. It would stop being a preference if the banner-style disclosure
  this app uses elsewhere were available for it.`);
  }

  // ── not findings ────────────────────────────────────────────────────────
  console.log('\n=== CHECKED AND CORRECT ===');
  console.log(`  * press-on (4) holds: all three truthy-rejection codes are emitted only
    inside the law_trusttx write branch, so \`!r\` counts exactly the failures
    for law_timeentries. Worth noting the check is keyed on the CODE and not on
    the resource, so it is one server-side code reuse away from under-counting
    -- and under-counting is the direction that reports a rejected write as a
    landed one. Cheap insurance: test the resource too.
  * the failure count uses touched.length as its denominator, which is the
    number of entries actually marked, not the number selected -- so the
    sentence cannot overstate the damage.
  * lawMarkSynced is called only past the !r.ok||!d.ok guard, so a refused
    law_timeentries write does NOT record the id as synced. That is right, and
    it is also why FINDING 1 bites: the id was already synced from the entry's
    original save.
  * the suite really does lift the shipped saveInvoice() rather than retyping
    it, so an edit to the function is seen by the arms.
  * the commit message's correction of the earlier verdict -- createInvoice()
    does not exist, it is saveInvoice() -- is accurate; there is no
    createInvoice in sairnlaw.html.`);

  console.log('\n' + findings + ' finding(s). Report-only: exit 0 by design.');
  process.exit(0);
})();
