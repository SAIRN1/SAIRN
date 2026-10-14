// api/ai-provenance-client-sites.test.js
//
// Run:  node api/ai-provenance-client-sites.test.js
//
// REQUIREMENT: every CLIENT site that saves model output carries the
//   provenance field, every surface that SHOWS model output says it is AI, and
//   no client ever writes the approver name itself.
//
// ── WHY A CLIENT-SIDE SUITE, WHEN THE GATE IS ON THE SERVER ───────────────
// api/_lib/ai-safeguards.js says the honest limit out loud: `ai_source` is a
// CLAIM BY THE WRITER, so "a client that does not stamp it gets no gate". The
// server half landed in b9 with NO production client stamping the field on a
// high-risk resource -- a gate that is reachable and never reached. That is
// not a server defect and no server test can find it. This suite is the other
// half: it reads the real HTML files and fails when a save site that stores
// model output does not say so.
//
// ── THE FOUR SITES H2 TRACED (seq852), AND THEY ARE NOT THE SAME SHAPE ────
//   sairnmechanical  saveDoc                  -> mech_docs          not high-risk
//   sairnroofing     saveMeasurementReading   -> rf_photos          HIGH-RISK
//   sairngrounds     grdUploadProgressPhoto   -> grd_progress_photos not high-risk
//   sairnscape       scpUploadProgressPhoto   -> scp_progress_photos not high-risk
// rf_photos is the one that changes behaviour rather than adding a label: it
// is in HIGH_RISK_AI, so stamping the field makes the approval gate fire for
// the first time in production. Section F drives that, because a safeguard
// that is switched on for real deserves to be driven and not inferred.
//
// ── SOURCE ARMS, AND THE RULE THEY ALL FOLLOW ─────────────────────────────
// Every arm that measures source asserts its anchor matched EXACTLY ONCE
// before it reads anything out of the region. An anchor that matches twice
// grades a block nobody chose, and an anchor that matches zero times reports a
// pass by absence -- both have happened on this platform, which is why this is
// a rule and not a habit. ZERO MATCHES IS UNPROVEN, NEVER A PASS.
//
// Exit: 0 all arms passed · 1 an arm FAILED · 3 an arm is UNPROVEN

'use strict';
const fs = require('fs');
const path = require('path');
const ROOT = path.join(__dirname, '..');

const ai = require('./_lib/ai-safeguards');
const red = require('./_lib/ai-scan-redaction');

let pass = 0, fail = 0, unproven = 0;
const failed = [], notProved = [];
function ok(l) { pass++; console.log('  ok       ' + l); }
function bad(l, why) {
  fail++; failed.push(l.split('.')[0]);
  console.log('  FAIL     ' + l);
  if (why) console.log('           ' + String(why).slice(0, 400));
}
function cannot(l, why) {
  unproven++; notProved.push(l.split('.')[0]);
  console.log('  UNPROVEN ' + l);
  if (why) console.log('           ' + String(why).slice(0, 400));
}
function is(c, l, why) { if (c) ok(l); else bad(l, why); }

const cache = {};
function src(file) {
  if (!cache[file]) cache[file] = fs.readFileSync(path.join(ROOT, file), 'utf8');
  return cache[file];
}

// Reads the body of a named function, from its declaration to the next
// top-level `function ` at column zero. Crude on purpose: these are
// single-file apps with flat function declarations, and a real parse would be
// a second implementation of something only this suite needs.
function fnBody(file, decl) {
  const s = src(file);
  const i = s.indexOf(decl);
  if (i < 0) return null;
  const count = s.split(decl).length - 1;
  if (count !== 1) return { ambiguous: count };
  const rest = s.slice(i + decl.length);
  const nxt = rest.search(/\n(?:async )?function [a-zA-Z_$]/);
  return { text: nxt === -1 ? rest : rest.slice(0, nxt) };
}

// ONE assertion shape for all four sites, so a fifth is one line rather than
// a fifth hand-written arm.
async function stampsSource(id, file, decl, resource, label) {
  const b = fnBody(file, decl);
  if (b === null) {
    cannot(id + '. ' + decl + ' was not found in ' + file
         + ', so this site could not be measured', 'anchor absent');
    return;
  }
  if (b.ambiguous) {
    cannot(id + '. ' + decl + ' matched ' + b.ambiguous + ' times in ' + file
         + ', so this arm cannot say which one it graded', 'uniqueness guard');
    return;
  }
  const hasResource = b.text.indexOf(resource) !== -1;
  const hasSource = /ai_source\s*:/.test(b.text);
  if (!hasResource) {
    cannot(id + '. ' + decl + ' no longer writes ' + resource
         + ', so the provenance requirement cannot be judged here',
           'the write moved');
    return;
  }
  is(hasSource, id + '. ' + file + ' ' + decl + ' stamps ai_source on its '
     + resource + ' record -- ' + label,
     'ai_source absent from the function body');
}

console.log('AI PROVENANCE AT THE CLIENT -- criteria 2026-10-14.1\n');

(async () => {
  // ── A. THE FOUR SAVE SITES H2 TRACED ────────────────────────────────────
  console.log('A. the four save sites that stored model output unflagged');

  await stampsSource('A1', 'sairnmechanical.html', 'function saveDoc()',
    'mech_docs',
    'the stored text IS the model\'s read of a scanned work order');
  await stampsSource('A2', 'sairnroofing.html',
    'function saveMeasurementReading()', 'rf_photos',
    'ai_analysis is the model\'s read of a measurement photograph and an '
    + 'insurance supplement is built on it. HIGH-RISK: this stamp switches the '
    + 'server approval gate on for the first time in production');
  await stampsSource('A3', 'sairngrounds.html',
    'async function grdUploadProgressPhoto()', 'grd_progress_photos',
    'ai_analysis is the model\'s description of a job-site photograph');
  await stampsSource('A4', 'sairnscape.html',
    'async function scpUploadProgressPhoto()', 'scp_progress_photos',
    'the sibling of grd_progress_photos, same panel shape');

  // THE TAGS MUST BE DISTINCT, because the whole reason ai_source is a tag and
  // not a boolean is to answer "which surface produced this".
  {
    const tags = [];
    [['sairnmechanical.html', 'function saveDoc()'],
     ['sairnroofing.html', 'function saveMeasurementReading()'],
     ['sairngrounds.html', 'async function grdUploadProgressPhoto()'],
     ['sairnscape.html', 'async function scpUploadProgressPhoto()']]
      .forEach(function (p) {
        const b = fnBody(p[0], p[1]);
        if (b && b.text) {
          const m = b.text.match(/ai_source\s*:\s*'([^']+)'/);
          if (m) tags.push(m[1]);
        }
      });
    if (tags.length !== 4) {
      cannot('A5. only ' + tags.length + ' of the four tags could be read out '
           + 'of the source, so uniqueness could not be measured',
             'tags: ' + tags.join(', '));
    } else {
      const uniq = tags.filter((v, i, a) => a.indexOf(v) === i);
      is(uniq.length === 4,
         'A5. the four tags are DISTINCT (' + tags.join(', ') + ') -- a tag '
       + 'that is the same on two surfaces makes "which surface wrote this" '
       + 'unanswerable, which is the whole reason the field is not a boolean',
         'tags: ' + tags.join(', '));
    }
  }

  // ── B. NO CLIENT WRITES THE APPROVER ────────────────────────────────────
  console.log('\nB. the approver is the server\'s to write, never the client\'s');

  // THE AUTO-SAVE SITES HAVE NO APPROVER AND MUST NOT CLAIM ONE. All four of
  // these save the moment the model answers -- there is no review step between
  // the reply and the write. The honest consequence is that aiFooter() reads
  // "AI-assisted -- not reviewed" on those records, and that is the correct
  // sentence. A client that filled in ai_approved_by with the person who
  // pressed the button would turn "nobody has checked this" into "checked by
  // the person who took the photograph", which is worse than no field at all.
  {
    const offenders = [];
    ['sairnmechanical.html', 'sairnroofing.html', 'sairngrounds.html',
     'sairnscape.html', 'sairnfreedom.html', 'stonedesk.html'].forEach(
      function (f) {
        const lines = src(f).split(/\r?\n/);
        lines.forEach(function (l, i) {
          // An ASSIGNMENT of the field, not a mention of it: these files
          // discuss the safeguard in comments, and a naive search matches the
          // documentation -- the class tools/pycomments.py exists for.
          if (/^\s*(\/\/|\*|\/\*)/.test(l)) return;
          if (/ai_approved_by\s*[:=]/.test(l)) {
            offenders.push(f + ':' + (i + 1));
          }
        });
      });
    is(offenders.length === 0,
       'B1. no client file ASSIGNS ai_approved_by anywhere -- the server sets '
     + 'it from the verified session and overwrites whatever arrives, which is '
     + 'the control that keeps a forged reviewer name out of a record',
       offenders.join(', '));
  }

  // AND THE FOOTER SAYS SO, which is the arm that proves B1 is a disclosure
  // and not just an omission.
  is(ai.aiFooter({ ai_source: 'claude:x' }) === 'AI-assisted — not reviewed',
     'B2. an ai-sourced record with no approver renders "AI-assisted — not '
   + 'reviewed" rather than an EMPTY footer -- a missing footer and an '
   + 'unreviewed one read identically to a reader and only one of them is true',
     JSON.stringify(ai.aiFooter({ ai_source: 'claude:x' })));

  // ── C. STONEDESK'S REVIEW REQUEST GENERATOR ─────────────────────────────
  console.log('\nC. stonedesk: the Review Request Generator said nothing');

  {
    const b = fnBody('stonedesk.html', 'async function revGenerate()');
    if (b === null || b.ambiguous) {
      cannot('C1. revGenerate() could not be located uniquely in '
           + 'stonedesk.html', 'anchor');
    } else {
      // THE TEXT IS WRITTEN BY A MODEL AND SENT TO A CUSTOMER AS THE SHOP'S
      // OWN WORDS. The generator put it straight into the preview with no
      // indication of where it came from; the operator copies it into SMS.
      is(/revAiLabel|AI_SURFACE_LABEL|Written by AI/.test(b.text),
         'C1. revGenerate() labels the drafted message as AI on the surface '
       + 'that shows it. The operator sends this text to a customer under the '
       + 'shop\'s name, so "who wrote this" has to be visible at the moment '
       + 'they read it, not in a policy document',
         'no AI label in the preview render');
    }
    const bs = fnBody('stonedesk.html', 'function revSend()');
    if (bs === null || bs.ambiguous) {
      cannot('C2. revSend() could not be located uniquely in stonedesk.html',
             'anchor');
    } else {
      is(/ai_source\s*:/.test(bs.text),
         'C2. and the sd_rev_log row carries ai_source, so the record of what '
       + 'was sent says the words were a model\'s. The log is local-only, '
       + 'which is why the server gate cannot supply this and the client must',
         'ai_source absent from the logged row');
    }
  }

  // ── D. SAIRNFREEDOM: VERIFIED, NOT REBUILT ──────────────────────────────
  // This was landed in b9 (sfAiLabel on all four surfaces, the one-time notice
  // and ai_source on sf_bottle_fills). It is RE-MEASURED here rather than
  // taken on trust, and rather than skipped silently: an arm that confirms
  // somebody else's work still costs nothing to run and is the only thing that
  // notices when a fifth AI surface is added without a label.
  console.log('\nD. sairnfreedom: four AI surfaces, four labels (re-measured)');

  {
    const s = src('sairnfreedom.html');
    const code = s.split(/\r?\n/)
      .filter((l) => !/^\s*(\/\/|\*|\/\*)/.test(l)).join('\n');
    const calls = (code.match(/callClaude\(\{/g) || []).length;
    const labels = (code.match(/sfAiLabel\(/g) || []).length;
    if (calls === 0) {
      cannot('D1. no callClaude({ sites found in sairnfreedom.html, so the '
           + 'label coverage could not be measured', 'zero matches');
    } else {
      // labels includes the helper's own definition, so the render count is
      // labels - 1. Said in the arm rather than silently subtracted.
      is(calls > 0 && (labels - 1) >= calls,
         'D1. all ' + calls + ' callClaude sites are matched by ' + (labels - 1)
       + ' sfAiLabel renders (' + labels + ' occurrences less the helper\'s '
       + 'own definition) -- every surface that shows model output says so',
         'calls=' + calls + ' renders=' + (labels - 1));
    }
    is(/ai_source\s*:\s*'claude:bottle-fill'/.test(code),
       'D2. sf_bottle_fills still carries its ai_source tag -- the one record '
     + 'this app stores that a model wrote',
       'tag absent');
  }

  // ── E. THE msb_bottle_scans DISCREPANCY, RESOLVED FROM BOTH SIDES ───────
  // THE TWO SIDES, READ AT file:line RATHER THAN RECONCILED FROM MEMORY:
  //
  //   EXCLUDED  api/_lib/ai-scan-redaction.js:100 lists msb_bottle_scans in
  //             DELIBERATELY_EXCLUDED, reason "NO MODEL PROSE IS STORED".
  //             Verified at sairngrounds.html:4779: the record is
  //             {id, product_id, brand_read, fill_pct, date, note} -- two
  //             scalars from msbParseScanResult() and a `note` the APP
  //             computes at :4771-4777 from local cost data. Correct: there is
  //             no free model prose on the row to redact.
  //
  //   FLAGGED   the same row is a model's output. `brand_read` is the string
  //             the model read off a label (sairngrounds.html:4756) and it is
  //             synced to the server at :4781 with no provenance field at all.
  //
  // THEY ARE NOT IN CONFLICT AND THAT IS THE RESOLUTION: redaction and
  // disclosure are two different safeguards, and an exclusion from one was
  // being read as an exemption from the other. Redaction has nothing to do
  // because there is no prose; disclosure has everything to do because the
  // content came from a model. So the row gets ai_source and stays out of
  // BOTH risk maps -- adding it to NOT_HIGH_RISK_AI would fail
  // api/ai-safeguards.test.js's phantom arm, which requires every entry there
  // to be an AI_SCANNED_TEXT resource, and this one deliberately is not.
  console.log('\nE. msb_bottle_scans: the exclusion-vs-flagged discrepancy');

  is(Object.prototype.hasOwnProperty.call(
       red.DELIBERATELY_EXCLUDED || {}, 'msb_bottle_scans'),
     'E1. side one -- msb_bottle_scans IS in ai-scan-redaction\'s '
   + 'DELIBERATELY_EXCLUDED, and the reason holds: the row carries two scalars '
   + 'and an app-computed note, so there is no model prose to redact',
     'not in DELIBERATELY_EXCLUDED');

  is(!ai.isHighRisk('msb_bottle_scans')
     && !Object.prototype.hasOwnProperty.call(ai.NOT_HIGH_RISK_AI, 'msb_bottle_scans'),
     'E2. ...and it is in NEITHER risk map, which is correct rather than an '
   + 'omission: those maps partition AI_SCANNED_TEXT, and this resource is '
   + 'deliberately outside that population. An entry here would fail '
   + 'api/ai-safeguards.test.js\'s phantom arm',
     'high=' + ai.isHighRisk('msb_bottle_scans') + ' notHigh='
   + Object.prototype.hasOwnProperty.call(ai.NOT_HIGH_RISK_AI, 'msb_bottle_scans'));

  {
    const b = fnBody('sairngrounds.html', 'async function msbHandleScanResult(');
    if (b === null || b.ambiguous) {
      cannot('E3. msbHandleScanResult could not be located uniquely',
             'anchor');
    } else {
      is(/ai_source\s*:/.test(b.text),
         'E3. side two -- the record IS stamped, because brand_read is what a '
       + 'model read off a label and the row is synced to the server. The '
       + 'exclusion from REDACTION was never an exemption from DISCLOSURE, and '
       + 'that conflation is the whole discrepancy',
         'ai_source absent from the scan record');
    }
  }

  // ── F. rf_photos IS THE FIRST HIGH-RISK ADOPTER, SO DRIVE THE GATE ──────
  // api/sd-data-ai-approval.test.js drives the gate generically on
  // mech_quotes. This drives the resource a real client now stamps, because
  // "the gate works" and "the gate works for the surface that just switched it
  // on" are different claims.
  console.log('\nF. the server gate, driven on the resource now stamped');

  {
    const never = () => null;
    const signed = (app) => ({ employee_id: 'emp-7', app: app });
    const now = () => '2026-10-14T00:00:00.000Z';

    const r1 = ai.enforceAiApproval('rf_photos',
      { ai_source: 'claude:measurement-photo' }, never, now);
    is(r1 && r1.status === 403 && r1.code === 'AI_APPROVAL_REQUIRED',
       'F1. an ai-sourced rf_photos record with NOBODY signed in is refused '
     + '403 AI_APPROVAL_REQUIRED -- this is the refusal that was reachable and '
     + 'never reached in production until this batch stamped the field',
       JSON.stringify(r1));

    const p = { ai_source: 'claude:measurement-photo', ai_approved_by: 'forged' };
    const r2 = ai.enforceAiApproval('rf_photos', p, signed, now);
    is(r2 === null && p.ai_approved_by === 'emp-7'
       && p.ai_approved_at === now(),
       'F2. with a signed-in session the record is allowed AND the approver is '
     + 'OVERWRITTEN from the session -- a forged "forged" in the payload does '
     + 'not survive, which is the control, not a side effect',
       JSON.stringify({ refusal: r2, by: p.ai_approved_by }));

    const r3 = ai.enforceAiApproval('rf_photos',
      { ai_source: 'claude:measurement-photo', status: 'draft' }, never, now);
    is(r3 === null,
       'F3. CONTROL -- a DRAFT is exempt with nobody signed in, so F1 is the '
     + 'gate firing on a final record rather than the gate refusing '
     + 'everything',
       JSON.stringify(r3));

    const r4 = ai.enforceAiApproval('grd_progress_photos',
      { ai_source: 'claude:progress-photo' }, never, now);
    is(r4 === null,
       'F4. CONTROL -- the three NOT-high-risk sites get disclosure and no '
     + 'approval gate, so A1/A3/A4 cannot have switched a refusal on by '
     + 'accident. grd_progress_photos has its own QC authority gate and that '
     + 'is the one that decides',
       JSON.stringify(r4));
  }

  console.log('\n' + pass + ' passed, ' + fail + ' failed, '
            + unproven + ' unproven');
  if (failed.length) console.log(failed.length + ' ARM(S) FAILED: ' + failed.join(', '));
  if (notProved.length) console.log(notProved.length + ' ARM(S) UNPROVEN: ' + notProved.join(', '));
  process.exit(fail ? 1 : (unproven ? 3 : 0));
})().catch((e) => { console.error(e); process.exit(1); });
