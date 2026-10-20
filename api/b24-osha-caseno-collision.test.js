// api/b24-osha-caseno-collision.test.js
//
// Run:  node api/b24-osha-caseno-collision.test.js
//
// TWO RECORDABLE INJURIES PRINTED AS THE SAME OSHA FORM 300 CASE NUMBER.
//
// CONCEPT, stated before any fix (docs/2026-10-20-hank-b24-notes.md item 3):
//   An OSHA Form 300 case number must be unique within its establishment-year
//   wherever it was issued. Column A is issued from ONE DEVICE'S store and the
//   server merge is keyed on `id`, so two devices issue the same number and
//   nothing ever notices. The number that is already printed is NOT silently
//   rewritten -- the collision is DETECTED and shown in the column that is
//   wrong, because a duplicate Column A is a records problem a human resolves.
//
// ── WHERE THE NUMBER IS ISSUED ────────────────────────────────────────────
// sairnbiz.html `sbNextCaseNo(list, year)` -- max(case_no for that year) + 1,
// over `ld('sb_incidents', [])`, which is ONE BROWSER'S localStorage.
// `saveIncident()` calls it and stores the result on the row.
//
// ── WHY IT COLLIDES, AND THIS IS THE REPRODUCTION IN SECTION A ────────────
// `sb_incidents` IS in SB_SYNCED, and `sbServerWinsMerge()` matches rows BY
// `id`. `id` is `'IN' + Date.now().toString(36)`, generated per device. So:
//
//   device 1 list is empty -> sbNextCaseNo -> 1 -> row {id:'INa', case_no:1}
//   device 2 list is empty -> sbNextCaseNo -> 1 -> row {id:'INb', case_no:1}
//   hydrate: ids differ, so BOTH rows land, both saying 2026-1
//
// The merge has no reason to notice: its identity is `id`, and both ids are
// genuinely distinct records. The 300A summary totals stay correct, because
// they count rows -- so every number on the summary is right while the case
// numbers on the log are wrong, which is the version an inspector cannot
// reconcile.
//
// ── AND A SECOND, NARROWER HOLE IN THE SAME FUNCTION (section B) ──────────
// `if(!r||String(r.year)!==String(year))return;` SKIPS any row whose `year`
// field is absent or does not match, even when its `date` is plainly inside
// that year. A row that reached the device by any route other than
// saveIncident() is therefore INVISIBLE to the max scan, and the next save
// re-issues a number that row already holds -- a collision on ONE device, with
// no second device involved.
//
// ── WHAT THIS SUITE DOES NOT CLAIM ───────────────────────────────────────
// It drives the REAL functions, lifted out of sairnbiz.html by brace matching
// (the harness in tests/sairnbiz_incidents_kpi.js, same approach), in a `vm`
// context. It touches no browser and no server. THE RESIDUAL IS NAMED RATHER
// THAN CLOSED: two devices that are BOTH offline at the moment of issue can
// still mint the same number, and nothing client-side can prevent that. The
// complete fix is a server-side per-year sequence in api/sd-data.js, which is
// cody's file and is ROUTED, not done here.
//
// Exit: 0 all arms passed · 1 an arm FAILED · 3 an arm is UNPROVEN

'use strict';

const fs = require('fs');
const path = require('path');
const vm = require('vm');

const { execFileSync } = require('child_process');

const ROOT = path.join(__dirname, '..');
const SRC = path.join(ROOT, 'sairnbiz.html');
const SELF = __filename;
const ARMS_ONLY = process.env.B24_CASENO_ARMS_ONLY === '1';
const html = fs.readFileSync(SRC, 'utf8').replace(/\r\n/g, '\n');

// ── THE ABLATION HARNESS (api/b23-iolta-attestation.test.js's shape) ──────
function runSuite(file, armsOnly) {
  const env = armsOnly
    ? Object.assign({}, process.env, { B24_CASENO_ARMS_ONLY: '1' })
    : process.env;
  try {
    const out = execFileSync(process.execPath, [file], {
      env: env, encoding: 'utf8', stdio: 'pipe' });
    return { exit: 0, out: String(out || '') };
  } catch (e) {
    return { exit: typeof e.status === 'number' ? e.status : -1,
             out: String((e && e.stdout) || '') + String((e && e.stderr) || '') };
  }
}
function failedArms(out) {
  const m = String(out || '').match(/FAILED:\s*(.+)/);
  return m ? m[1].trim().split(/\s*,\s*/).filter(Boolean) : [];
}
/**
 * MUTATES sairnbiz.html, runs this file's arms in a child, and RESTORES in a
 * finally. THE FILE IS READ AND WRITTEN IN BINARY-FAITHFUL FORM: this repo has
 * mixed line endings file by file and sairnbiz.html is CRLF, so a text-mode
 * round trip would rewrite all 6,000+ lines and the restore would not be a
 * restore. Read as a Buffer, replace on the utf8 view, write the bytes back.
 */
function ablate(file, find, replace) {
  const originalBuf = fs.readFileSync(file);
  const original = originalBuf.toString('utf8');
  // The anchors in this file are written with \n; the file on disk is CRLF.
  const findCrlf = find.replace(/\n/g, '\r\n');
  const replCrlf = replace.replace(/\n/g, '\r\n');
  let needle = find, repl = replace;
  let hits = original.split(find).length - 1;
  if (hits !== 1) {
    const crlfHits = original.split(findCrlf).length - 1;
    if (crlfHits === 1) { needle = findCrlf; repl = replCrlf; hits = 1; }
  }
  if (hits !== 1) {
    return { ok: false, why: 'the ablation anchor matched ' + hits + ' time(s) in '
      + path.basename(file) + ' (and ' + (original.split(findCrlf).length - 1)
      + ' with CRLF), not exactly 1 -- REFUSING to mutate. FIX THE ANCHOR, do '
      + 'not delete the arm. Anchor: ' + find.slice(0, 110) };
  }
  try {
    fs.writeFileSync(file, Buffer.from(original.replace(needle, repl), 'utf8'));
    const mine = runSuite(SELF, true);
    return { ok: true, exit: mine.exit, arms: failedArms(mine.out), out: mine.out };
  } finally {
    fs.writeFileSync(file, originalBuf);
  }
}

let pass = 0, fail = 0, unproven = 0;
const failed = [], notProved = [];
function ok(l) { pass++; console.log('  ok       ' + l); }
function bad(l, why) {
  fail++; failed.push(l.split('.')[0]);
  console.log('  FAIL     ' + l);
  if (why) console.log('           ' + String(why).slice(0, 600));
}
function cannot(l, why) {
  unproven++; notProved.push(l.split('.')[0]);
  console.log('  UNPROVEN ' + l);
  if (why) console.log('           ' + String(why).slice(0, 600));
}
function is(cond, label, detail) { if (cond) ok(label); else bad(label, detail); }
function section(t) { console.log('\n' + t); }

// ── LIFT THE REAL FUNCTIONS, NEVER RETYPE THEM ────────────────────────────
// A retyped copy of sbNextCaseNo would pass this suite forever while the real
// one drifted, which is the defect class the whole repo keeps paying for.
function fnBodyAt(at) {
  const open = html.indexOf('{', at);
  let depth = 0;
  for (let i = open; i < html.length; i++) {
    if (html[i] === '{') depth++;
    else if (html[i] === '}') { depth--; if (depth === 0) return html.slice(at, i + 1); }
  }
  throw new Error('unbalanced braces from offset ' + at);
}
function lift(decl) {
  const at = html.indexOf(decl);
  if (at < 0) throw new Error('NOT FOUND in sairnbiz.html: ' + decl);
  if (html.indexOf(decl, at + 1) >= 0) {
    throw new Error('AMBIGUOUS -- ' + decl + ' appears more than once; the lift '
      + 'would take whichever came first. FIX THE ANCHOR.');
  }
  return fnBodyAt(at);
}

let ctx = null;
let liftError = null;
try {
  const parts = [
    lift('function sbNextCaseNo('),
    lift('function sbIncidentsYTD('),
  ];
  // sbCaseNoCollisions is the FIX and does not exist before it is written.
  // Lifted separately so the reproduction arms still run without it -- a suite
  // that cannot run until its own fix lands cannot be used to prove the defect.
  let collisions = null;
  try { collisions = lift('function sbCaseNoCollisions('); } catch (e) { collisions = null; }
  if (collisions) parts.push(collisions);
  ctx = vm.createContext({});
  vm.runInContext(parts.join('\n'), ctx);
  ctx.__hasCollisionFn = typeof ctx.sbCaseNoCollisions === 'function';
} catch (e) {
  liftError = e;
}

function nextCaseNo(list, year) {
  return vm.runInContext('sbNextCaseNo(' + JSON.stringify(list) + ','
    + JSON.stringify(year) + ')', ctx);
}
function collisionsOf(list) {
  return vm.runInContext('sbCaseNoCollisions(' + JSON.stringify(list) + ')', ctx);
}

// `sbServerWinsMerge`'s identity rule, in four lines, because the real one
// needs localStorage, a licence and a synced-id map. THE PROPERTY BEING
// REPRODUCED IS ITS IDENTITY RULE AND NOTHING ELSE: rows are matched BY `id`.
// Arm A0 asserts that rule is still what the real function uses, so this
// stand-in cannot quietly stop representing it.
function mergeById(local, server) {
  const out = local.slice();
  const idx = {};
  out.forEach((r, n) => { if (r && r.id != null) idx[String(r.id)] = n; });
  server.forEach((row) => {
    if (!row || row.id == null) return;
    const at = idx[String(row.id)];
    if (at === undefined) { out.push(row); idx[String(row.id)] = out.length - 1; }
    else out[at] = row;
  });
  return out;
}

function incident(id, year, caseNo, extra) {
  return Object.assign({ id: id, year: year, case_no: caseNo,
    date: year + '-03-04', emp: 'A. Worker', desc: 'crush injury',
    classification: 'away', type: 'injury', days_away: 3, days_restricted: 0,
    privacy: false, created_at: year + '-03-05' }, extra || {});
}

(async () => {
  console.log('b24 OSHA Form 300 Column A -- duplicate case numbers\n');

  if (liftError) {
    cannot('A0. the real functions could not be lifted out of sairnbiz.html, so '
         + 'NOTHING below ran', liftError.message);
    console.log('\n  ' + pass + ' passed, ' + fail + ' failed, ' + unproven + ' unproven');
    process.exit(3);
  }

  // ══ A. THE REPRODUCTION ═════════════════════════════════════════════════
  section('A. THE REPRODUCTION -- two devices, one case number');

  is(/serverRows\.forEach/.test(html) && /var id=String\(row\.id\),at=idx\[id\]/.test(html),
     'A0. sbServerWinsMerge still matches rows BY `id` in sairnbiz.html, so the '
   + 'four-line stand-in below still represents it. If this fails, RE-SEAT IT '
   + 'rather than trusting the stand-in',
     'identity-by-id markers present');

  const device1 = [];
  const device2 = [];
  const n1 = nextCaseNo(device1, '2026');
  const n2 = nextCaseNo(device2, '2026');
  is(n1 === 1 && n2 === 1,
     'A1. two devices with their own empty store BOTH issue case number 1 for '
   + '2026 -- neither is wrong on its own evidence',
     'device1=' + n1 + ' device2=' + n2);

  const rowA = incident('INa', '2026', n1);
  const rowB = incident('INb', '2026', n2, { emp: 'B. Worker', desc: 'laceration' });
  const merged = mergeById([rowA], [rowB]);
  const keys = merged.map((r) => r.year + '-' + r.case_no);
  is(merged.length === 2 && keys[0] === keys[1],
     'A2. THE DEFECT: after the server merge BOTH rows are present and BOTH '
   + 'print as ' + keys[0] + '. The merge had no reason to notice -- its '
   + 'identity is `id`, and the two ids are genuinely different records',
     JSON.stringify(keys));

  is(vm.runInContext('sbIncidentsYTD(' + JSON.stringify(merged) + ',"2026")', ctx) === 2,
     'A3. ...and the YTD count is CORRECT at 2, which is why nothing catches '
   + 'it: the 300A totals are right while Column A is wrong, and an inspector '
   + 'reads both',
     'count=2');

  // ══ B. THE SECOND HOLE, ON ONE DEVICE ═══════════════════════════════════
  section('B. THE NARROWER HOLE -- a row the max scan cannot see');

  const noYear = incident('INc', '2026', 7);
  delete noYear.year;                       // reached the device another way
  const nextAfter = nextCaseNo([noYear], '2026');
  is(nextAfter === 8,
     'B1. a row with case_no 7 and NO `year` field, whose date is plainly in '
   + '2026, must still block -- the next number has to be 8. Before the fix '
   + 'this answered 1 and collided on ONE device with no second device '
   + 'involved',
     'got ' + nextAfter);

  const strYear = incident('INd', 2026, 4);  // numeric year, as JSON round-trip
  is(nextCaseNo([strYear], '2026') === 5,
     'B2. and a NUMERIC year still matches the string year -- String() on both '
   + 'sides, asserted rather than assumed',
     'got ' + nextCaseNo([strYear], '2026'));

  is(nextCaseNo([incident('INe', '2025', 9)], '2026') === 1,
     'B3. THE NEGATIVE CONTROL: a row from ANOTHER year does NOT block. '
   + 'Without this, B1 is equally consistent with "every row blocks", which '
   + 'would make the log one continuous sequence instead of per-year',
     'got ' + nextCaseNo([incident('INe', '2025', 9)], '2026'));

  // ══ C. THE FIX: A DETECTOR, BECAUSE A PRINTED NUMBER IS NOT REWRITTEN ═══
  section('C. THE DETECTOR');

  if (!ctx.__hasCollisionFn) {
    cannot('C1. sbCaseNoCollisions() is not in sairnbiz.html, so the detector '
         + 'arms DID NOT RUN. This is the pre-fix state and it is UNPROVEN '
         + 'rather than passed',
      'function sbCaseNoCollisions( not found');
  } else {
    const dup = collisionsOf(merged);
    is(Array.isArray(dup) && dup.length === 1 && dup[0] === '2026-1',
       'C1. the detector names the duplicated Column A value, once, as '
     + '`<year>-<case_no>`',
       JSON.stringify(dup));
    is(collisionsOf([rowA]).length === 0,
       'C2. THE CLEAN CONTROL: one row is not a collision. A detector that '
     + 'always returns something is a detector nobody can act on',
       JSON.stringify(collisionsOf([rowA])));
    is(collisionsOf([incident('INa', '2026', 1), incident('INb', '2025', 1)]).length === 0,
       'C3. the same case number in TWO DIFFERENT YEARS is not a collision -- '
     + 'Column A is per-year and a cross-year match is the normal case',
       'no collision across years');
    const triple = [incident('INa', '2026', 1), incident('INb', '2026', 1),
                    incident('INc', '2026', 1)];
    is(collisionsOf(triple).length === 1 && collisionsOf(triple)[0] === '2026-1',
       'C4. three rows on one number report ONE finding, not two -- a reader '
     + 'needs the NUMBER that is wrong, not a count of pairs',
       JSON.stringify(collisionsOf(triple)));
    is(collisionsOf([]).length === 0 && collisionsOf(null).length === 0,
       'C5. an empty or absent list is not a collision and does not throw -- '
     + 'this runs on every render',
       'empty-safe');
    const missing = [incident('INa', '2026', null), incident('INb', '2026', null)];
    is(collisionsOf(missing).length === 0,
       'C6. two rows with NO case number are not reported as a duplicate '
     + 'Column A. They are a different defect -- an unnumbered case -- and '
     + 'reporting them as "duplicate --" would send a reader looking for a '
     + 'number neither row has',
       JSON.stringify(collisionsOf(missing)));
  }

  // ══ D. THE RENDER SHOWS IT, IN THE COLUMN THAT IS WRONG ═════════════════
  section('D. THE LOG SAYS SO');

  const rendersWarning = /sbCaseNoCollisions\(/.test(html)
    && /function rIncidents\(/.test(html);
  if (!rendersWarning) {
    cannot('D1. rIncidents() does not consult sbCaseNoCollisions(), so a '
         + 'duplicate is detected and never SHOWN. A finding nothing renders '
         + 'is a finding nobody acts on',
      'no sbCaseNoCollisions reference near the render');
  } else {
    const at = html.indexOf('function rIncidents(');
    // ── COMMENTS STRIPPED FIRST, AND ABLATION F3 IS WHY ───────────────────
    // The first draft of D1/D2 tested the raw function body. The body carries
    // a comment block that itself contains the words `sbCaseNoCollisions` and
    // `DUPLICATE`, so BOTH ARMS WERE SATISFIED BY THE PROSE ABOUT THE CODE
    // rather than by the code. F3 removed the rendered warning and D2 stayed
    // GREEN -- the same shape as b23's arm F2 passing in both worlds, caught
    // the same way, by an ablation rather than by review.
    //
    // Line-based rather than a state machine, and the limit is stated: a `//`
    // inside a string literal on one of these lines would be stripped too.
    // There is none in this function, asserted by D0 below, so the cheap form
    // is correct HERE and would not be in general.
    const body = fnBodyAt(at).split('\n')
      .filter((l) => !l.trim().startsWith('//')).join('\n');
    is(body.indexOf('//') === -1 || /https?:\/\//.test(body) === false,
       'D0. the comment-stripped render body has no `//` left, so the strip '
     + 'took whole comment lines and nothing else',
       'residual // count: ' + (body.split('//').length - 1));
    is(/sbCaseNoCollisions\(/.test(body),
       'D1. rIncidents() consults the detector -- in CODE, not in a comment '
     + 'about the code',
       'present in the comment-stripped render body');
    is(/DUPLICATE/.test(body),
       'D2. ...and the warning carries the word DUPLICATE, in Column A itself '
     + 'rather than in a banner somewhere else on the page -- the column that '
     + 'is wrong is where a reader is already looking',
       'DUPLICATE present in the comment-stripped render body');
    is(!/case_no\s*=\s*/.test(body),
       'D3. AND THE RENDER NEVER REASSIGNS A NUMBER. A case number already '
     + 'printed on a filed Form 300 is not silently rewritten by a render; '
     + 'resolving a duplicate is a human act on a regulatory record',
       'no assignment to case_no in the render');
  }

  // ══ E. THE RESIDUAL, ASSERTED SO IT CANNOT BE FORGOTTEN ═════════════════
  section('E. WHAT IS STILL OPEN');

  is(/ONE DEVICE'S localStorage|one device's localStorage|per-year sequence/i.test(html),
     'E1. sairnbiz.html says in its own source that the issuance is '
   + 'device-local and that the complete fix is a server-side sequence. Two '
   + 'devices offline at the same instant can still collide, the detector '
   + 'catches it after the fact, and NOTHING CLIENT-SIDE CAN PREVENT IT',
     'residual disclosed in the source');

  if (ARMS_ONLY) {
    console.log('\n  ' + pass + ' passed, ' + fail + ' failed, ' + unproven + ' unproven');
    if (failed.length) console.log('  FAILED: ' + failed.join(', '));
    if (notProved.length) console.log('  UNPROVEN: ' + notProved.join(', '));
    process.exit(fail ? 1 : (unproven ? 3 : 0));
  }

  // ══ F. THE ABLATIONS ════════════════════════════════════════════════════
  // Remove ONE named layer from already-clean code and measure what IT ALONE
  // catches, per ARM rather than per exit code. b23's arm F2 passed in both
  // worlds and only an ablation could see it; every arm here gets the same
  // treatment.
  section('F. ABLATIONS');

  const f0 = runSuite(SELF, true);
  is(f0.exit === 0,
     'F0. THE CONTROL: with nothing ablated the arms-only child run is GREEN '
   + '(exit 0). Every ablation below is measured against this',
     'child exit ' + f0.exit + '\n' + String(f0.out).slice(-400));

  // F1. The date fallback in the max scan. Put the old year-only test back and
  // B1 must go red -- and ONLY B1, because the other arms' rows all carry a
  // `year`.
  const f1 = ablate(SRC,
    "    var ry=(r.year===undefined||r.year===null||r.year==='')\n"
    + "      ?String(r.date||'').slice(0,4):String(r.year);\n"
    + "    if(ry!==String(year))return;\n"
    + "    var v=parseInt(r.case_no,10);\n"
    + "    if(!isNaN(v)&&v>n)n=v;",
    "    if(String(r.year)!==String(year))return;\n"
    + "    var v=parseInt(r.case_no,10);\n"
    + "    if(!isNaN(v)&&v>n)n=v;");
  if (!f1.ok) {
    cannot('F1. the date fallback is load-bearing', f1.why);
  } else {
    is(f1.exit === 1 && f1.arms.indexOf('B1') !== -1,
       'F1. restoring the year-only test makes arm B1 FAIL -- so the date '
     + 'fallback is what stops a row the device already holds from being '
     + 'invisible to the max scan',
       'exit ' + f1.exit + ' arms=' + f1.arms.join(','));
    is(f1.arms.indexOf('B3') === -1 && f1.arms.indexOf('A1') === -1,
       'F1b. ...and B3 and A1 stay GREEN, so one condition was removed and not '
     + 'the per-year scoping',
       'arms=' + f1.arms.join(','));
  }

  // F2. The detector's duplicate bookkeeping. Report EVERY repeat rather than
  // one per number, and C4 must go red while C1 stays green -- the difference
  // between "the number that is wrong" and "a count of pairs".
  const f2 = ablate(SRC,
    "    if(seen[k]){if(!dup[k]){dup[k]=true;out.push(k);}}",
    "    if(seen[k]){out.push(k);}");
  if (!f2.ok) {
    cannot('F2. the one-finding-per-number rule is load-bearing', f2.why);
  } else {
    is(f2.exit === 1 && f2.arms.indexOf('C4') !== -1,
       'F2. reporting one finding per colliding PAIR makes arm C4 FAIL',
       'exit ' + f2.exit + ' arms=' + f2.arms.join(','));
    is(f2.arms.indexOf('C1') === -1,
       'F2b. ...and C1 stays GREEN, so the detector still detects',
       'arms=' + f2.arms.join(','));
  }

  // F3. The render's warning. Remove the mark and D2 must go red while D1
  // stays green -- detecting and SHOWING are two different properties and the
  // whole point of section D is that a finding nothing renders is a finding
  // nobody acts on.
  const f3 = ablate(SRC,
    "      ?'<br><strong style=\"color:#b45309\">&#9888; DUPLICATE case number -- '",
    "      ?'<br><strong style=\"color:#b45309\">&#9888; see the log -- '");
  if (!f3.ok) {
    cannot('F3. the rendered warning is load-bearing', f3.why);
  } else {
    is(f3.exit === 1 && f3.arms.indexOf('D2') !== -1,
       'F3. softening the warning out of Column A makes arm D2 FAIL -- the '
     + 'detector still runs and the reader is no longer told',
       'exit ' + f3.exit + ' arms=' + f3.arms.join(','));
    is(f3.arms.indexOf('D1') === -1,
       'F3b. ...and D1 stays GREEN, which is exactly the split: DETECTED and '
     + 'SHOWN are two properties and only one of them was removed',
       'arms=' + f3.arms.join(','));
  }

  console.log('\n  ' + pass + ' passed, ' + fail + ' failed, ' + unproven + ' unproven');
  if (failed.length) console.log('  FAILED: ' + failed.join(', '));
  if (notProved.length) console.log('  UNPROVEN: ' + notProved.join(', '));
  process.exit(fail ? 1 : (unproven ? 3 : 0));
})().catch((e) => {
  console.error('\n  HARNESS ERROR -- the suite did not finish, which is NOT a '
    + 'pass:\n', e);
  process.exit(1);
});
