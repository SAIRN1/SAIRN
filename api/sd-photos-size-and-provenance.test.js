// api/sd-photos-size-and-provenance.test.js
//
// Run:  node api/sd-photos-size-and-provenance.test.js
//
// REQUIREMENT: a StoneDesk photo fits the row it is written to, the server
//   says WHY when a row is refused instead of blaming a migration, the model's
//   QC note carries provenance, and a backup that does not happen says so to a
//   human.
//
// ── WHAT WAS TRUE BEFORE THIS BATCH, MEASURED BY fourth's b19 PREMISE DOC ──
// sd_photos carries the house constraint `octet_length(data::text) <= 65536`
// and handlePhotoFiles put the WHOLE FileReader data URL on the row, accepting
// files up to 10 MB. Base64 is a 4/3 expansion, so ~48.9 KB of image was the
// most that could ever land -- a phone photo is 2-5 MB. EVERY REAL PHOTOGRAPH
// was refused 400 by Postgres, reported as 503 "tables are not set up yet",
// and the only trace was a console.warn nobody reads.
//
// ── THE RED, CAPTURED AGAINST THE PRE-FIX FILES AND NOT DESCRIBED ──────────
// This suite was run against HEAD before the fix landed, in a detached
// worktree. The figures are in docs/hank-evidence/b12/.
//
// ── THE ONE ARM THAT IS NOT HERE, ON PURPOSE ───────────────────────────────
// The oversized-write arm -- a sd_photos write whose `data` exceeds the cap
// must not produce 503 NOT_PROVISIONED -- is ROUTED TO cody by fourth's b19
// document, which owns tests/. Section A drives the status mapping from the
// other direction (what the upstream answered -> what the caller is told), so
// the two are complements and not duplicates. Said here so it is not written
// twice.
//
// Exit: 0 all arms passed · 1 an arm FAILED · 3 an arm is UNPROVEN

'use strict';
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const ROOT = path.join(__dirname, '..');

process.env[['SD', 'AUTH', 'SECRET'].join('_')] =
  ['stonedesk', 'photos', 'fixture', String(process.pid)].join('-');

const APP = 'stonedesk';
const KEY = 'k';
const HASH = crypto.createHash('sha256').update(KEY).digest('hex');
let LIC_APP = APP;

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

const HTML = fs.readFileSync(path.join(ROOT, 'stonedesk.html'), 'utf8');
const SRC = fs.readFileSync(path.join(__dirname, 'sd-data.js'), 'utf8');
// Comment lines stripped before any shape scan: this batch DOCUMENTS the old
// behaviour at length, and a raw file-wide match would score the prose as the
// code being present -- the class tools/pycomments.py exists for.
const CODE = SRC.split(/\r?\n/)
  .filter((l) => !/^\s*(\/\/|\*|\/\*)/.test(l)).join('\n');
const HCODE = HTML.split(/\r?\n/)
  .filter((l) => !/^\s*(\/\/|\*|\/\*|<!--)/.test(l)).join('\n');

const eCode = (r) => (r && r.body && r.body.error && r.body.error.code) || '';

function mockRes() {
  const r = { statusCode: null, body: null };
  r.status = (c) => { r.statusCode = c; return r; };
  r.json = (b) => { r.body = b; return r; };
  return r;
}

// THE UPSTREAM IS THE SUBJECT OF SECTION A, so it is the thing the fixture
// varies: each arm says what PostgREST answered and the arm asserts what the
// caller is told. `text()` and `json()` are BOTH provided and each records
// that it was called, because the whole defect class this section covers is a
// body that was already consumed.
function upstreamMock(spec, seen) {
  return async function (url) {
    // The active-credential re-check is not the subject of any arm here, so it
    // is answered and NOT counted -- counting it would make `seen.json` say a
    // body had been read when the body in question had not.
    if (/_employee_auth\?/.test(String(url))) {
      return { ok: true, status: 200, headers: { get: () => '' },
               text: async () => '[]',
               json: async () => [{ license_hash: HASH, employee_id: 'emp-1',
                                    role: 'owner', active: true }] };
    }
    return {
      ok: spec.status === 200,
      status: spec.status,
      headers: { get: () => '' },
      text: async () => { seen.text += 1; return spec.raw || ''; },
      json: async () => {
        seen.json += 1;
        if (spec.raw) { return JSON.parse(spec.raw); }
        return spec.rows !== undefined ? spec.rows : [];
      }
    };
  };
}

require.cache[require.resolve('./_lib/license')] = {
  id: require.resolve('./_lib/license'),
  filename: require.resolve('./_lib/license'),
  loaded: true,
  exports: {
    // MUTABLE app_id, because arm A8 drives a SAIRNroofing resource through the
    // same handler and the app-boundary gate refuses a foreign resource before
    // any branch is reached -- which is correct, and which made A8 fail with
    // FOREIGN_RESOURCE until the licence said what app it was for.
    validateLicenseKey: async () => ({
      valid: true, active: true, license_hash: HASH,
      trial_ends_at: null, stripe_subscription_id: null, app_id: LIC_APP })
  }
};
delete require.cache[require.resolve('./sd-data.js')];
const handler = require('./sd-data.js');

async function write(spec) {
  const seen = { text: 0, json: 0 };
  global.fetch = upstreamMock(spec, seen);
  const res = mockRes();
  await handler({ method: 'POST',
                  headers: { authorization: 'Bearer ' + KEY },
                  body: { action: 'write', resource: 'sd_photos',
                          payload: { id: 'P1', job: 'J', data: 'x' } } }, res);
  return { res: res, seen: seen };
}

console.log('sd_photos: the size cap, the 400 misattribution, T17 provenance '
          + '-- criteria 2026-10-14.1\n');

(async () => {
  // ── A. A 400 IS NOT A 404 ───────────────────────────────────────────────
  console.log('A. the server says WHY, instead of blaming a migration');

  {
    // THE CASE THE WHOLE SECTION IS FOR. 23514 is Postgres's check-violation
    // code and it is what the 65,536-byte cap raises.
    const { res } = await write({ status: 400, raw: '{"code":"23514","message":"violates check constraint"}' });
    is(res.statusCode === 400 && eCode(res) === 'ROW_REFUSED',
       'A1. an upstream 400 carrying pg code 23514 answers 400 ROW_REFUSED. '
     + 'THIS IS THE DEFECT: it used to answer 503 NOT_PROVISIONED -- "run the '
     + 'migration" -- for a table that exists and a row that is too big',
       'status=' + res.statusCode + ' code=' + eCode(res));
  }
  {
    const { res } = await write({ status: 404, raw: '' });
    is(res.statusCode === 503 && eCode(res) === 'NOT_PROVISIONED',
       'A2. CONTROL -- an upstream 404 still answers 503 NOT_PROVISIONED. '
     + 'Without this arm the fix could be "never say NOT_PROVISIONED again", '
     + 'and a genuinely unmigrated table would stop being diagnosable',
       'status=' + res.statusCode + ' code=' + eCode(res));
  }
  {
    // PostgREST answers a missing table 400 with PGRST205 on some versions.
    // That is the real reason 400 was folded in with 404 in the first place,
    // and it is PRESERVED rather than discarded.
    const { res } = await write({ status: 400, raw: '{"code":"PGRST205","message":"relation \\"public.sd_photos\\" does not exist"}' });
    is(res.statusCode === 503 && eCode(res) === 'NOT_PROVISIONED',
       'A3. a 400 whose body says the relation does not exist is STILL 503 '
     + 'NOT_PROVISIONED -- the original reason for folding 400 in with 404 was '
     + 'real and is kept, not thrown away with the defect',
       'status=' + res.statusCode + ' code=' + eCode(res));
  }
  {
    const { res } = await write({ status: 400, raw: '{"message":"something else entirely"}' });
    is(res.statusCode === 400 && eCode(res) === 'UPSTREAM_REJECTED',
       'A4. THE THIRD STATE -- a 400 that can be classified as neither answers '
     + '400 UPSTREAM_REJECTED and says the reason could not be classified. It '
     + 'does NOT say "run the migration". Folding could-not-tell into either '
     + 'of the other two answers is how this defect was built',
       'status=' + res.statusCode + ' code=' + eCode(res));
  }
  {
    const { res } = await write({ status: 200, rows: [{ data: { id: 'P1' } }] });
    is(res.statusCode === 200,
       'A5. CONTROL -- a successful write is still 200, so A1-A4 are not '
     + 'passing because everything now fails',
       'status=' + res.statusCode + ' code=' + eCode(res));
  }

  // THE POPULATION, MEASURED AT SOURCE AND NOT QUOTED FROM A DOCUMENT.
  // fourth's premise document put the figure at twelve; the real number is
  // larger, and this arm is the one that will notice the 90th.
  {
    const GUARD = 'if (r.status === 404 || r.status === 400) {';
    let bare = 0, routed = 0, reads = 0, idx = 0;
    for (;;) {
      const at = CODE.indexOf(GUARD, idx);
      if (at === -1) break;
      idx = at + GUARD.length;
      // brace-match the branch body
      let d = 0, k = CODE.indexOf('{', at + GUARD.length - 1);
      const open = k;
      for (; k < CODE.length; k++) {
        if (CODE[k] === '{') d++;
        else if (CODE[k] === '}') { d--; if (d === 0) break; }
      }
      const body = CODE.slice(open + 1, k);
      // BOTH SPELLINGS, AND THE FIRST DRAFT OF THIS ARM HAD ONLY ONE. It
      // tested `body.indexOf('NOT_PROVISIONED')`, which is the code of the
      // UNFIXED shape -- a rewritten branch says `notProvisioned(` and nothing
      // else, so the arm skipped all 89 and reported `routed=0` as a failure
      // against correct code. A detector that can only see the defect cannot
      // see the fix, and it failed loudly, which is the only reason it took a
      // minute.
      if (body.indexOf('NOT_PROVISIONED') === -1
          && body.indexOf('notProvisioned(') === -1) continue;
      if (/\br\.(text|json)\s*\(/.test(body)) { reads++; continue; }
      if (body.indexOf('notProvisioned(res, r,') !== -1) routed++;
      else bare++;
    }
    is(bare === 0 && routed > 0,
       'A6. ZERO (404||400) branches answer 503 NOT_PROVISIONED without '
     + 'reading the body: ' + routed + ' go through notProvisioned() and '
     + reads + ' discriminate for themselves. A branch that decides blind is '
     + 'the defect, so the arm counts them rather than naming a number',
       'bare=' + bare + ' routed=' + routed + ' self-deciding=' + reads);
  }

  // THE FIVE SITES THAT HAD ALREADY CONSUMED THE BODY. The first draft of the
  // mechanical rewrite broke all five by calling r.text() on a read stream.
  {
    const pre = (CODE.match(/await notProvisioned\(res, r, [^;]*?, rows\);/g) || []).length;
    is(pre === 5,
       'A7. the ' + pre + ' call sites that already did `const rows = await '
     + 'r.json()` BEFORE the guard pass that body in, so the helper does not '
     + 'read an already-consumed stream. A Response body can be read once, and '
     + 'a helper that reads it again turns one wrong diagnosis into another',
       'sites passing a pre-read body: ' + pre + ' (expected 5)');
  }

  // A8 DRIVES A PRE-READ SITE FOR REAL, and it exists because the SOURCE arm
  // above was not enough: ablating the helper's `preread` branch -- making it
  // re-read a consumed stream -- left A7 GREEN, because A7 only proves the
  // argument is PASSED and not that it is USED. rf_photos' write branch
  // (api/sd-data.js:8449) does `const rows = await r.json()` before its guard,
  // so this is that path end to end.
  {
    const { signSessionToken } = require('./_lib/auth');
    LIC_APP = 'sairnroofing';
    const seen = { text: 0, json: 0 };
    // THE FAILING STATUS IS SCOPED TO THE PHOTO INSERT, and the first draft of
    // this arm was not: rf_photos' write looks the JOB up first, that lookup
    // got the 400, and the answer came from the job branch -- one of the nine
    // that decide for themselves -- so the arm was measuring a branch it had
    // not named. Everything but sairnroofing_photos answers 200 with a row.
    global.fetch = async function (url, init) {
      const u = String(url);
      if (/_employee_auth\?/.test(u)) {
        return { ok: true, status: 200, headers: { get: () => '' },
                 text: async () => '[]',
                 json: async () => [{ license_hash: HASH, employee_id: 'emp-1',
                                      role: 'owner', active: true }] };
      }
      if (/\/rf_photos/.test(u) && init && init.method === 'POST') {
        // SINGLE CONSUMPTION, MODELLED. A real fetch Response body can be read
        // ONCE; a mock that happily serves text() after json() makes the
        // pre-read bug invisible, and an ablation proved exactly that -- with
        // a forgiving mock, ignoring the `preread` argument left every arm
        // green. So the second read returns '' here, which is what the
        // platform does.
        let used = false;
        return { ok: false, status: 400, headers: { get: () => '' },
                 text: async () => { seen.text += 1; if (used) return ''; used = true; return '{"code":"23514"}'; },
                 json: async () => { seen.json += 1; if (used) return null; used = true; return { code: '23514', message: 'violates check constraint' }; } };
      }
      return { ok: true, status: 200, headers: { get: () => '' },
               text: async () => '[]',
               json: async () => [{ id: 'J1', job_id: 'J1',
                                    license_hash: HASH, data: {} }] };
    };
    const res = mockRes();
    await handler({ method: 'POST',
      headers: { authorization: 'Bearer ' + KEY,
                 'x-sd-auth': signSessionToken({ app: 'sairnroofing',
                   employee_id: 'emp-1', role: 'owner', license_hash: HASH }) },
      body: { action: 'write', resource: 'rf_photos',
              payload: { job_id: 'J1', ai_analysis: 'note',
                         photo_base64: 'AAAA' } } }, res);
    is(res.statusCode === 400 && eCode(res) === 'ROW_REFUSED',
       'A8. a call site that had ALREADY consumed the body still classifies '
     + 'correctly -- rf_photos\' write reads `rows` before its guard and hands '
     + 'it in, and a 23514 there answers ROW_REFUSED. A7 proves the argument '
     + 'is passed; this proves it is READ, which is the half an ablation '
     + 'showed A7 alone could not see',
       'status=' + res.statusCode + ' code=' + eCode(res)
     + ' body=' + JSON.stringify(res.body).slice(0, 160));
    LIC_APP = APP;
  }

  // ── B. THE PHOTO FITS THE ROW ───────────────────────────────────────────
  console.log('\nB. the image is downscaled to fit, measured rather than assumed');

  // THE REAL FUNCTION, EXTRACTED AND RUN. A reimplementation here would pass
  // against the unfixed client, which is the failure mode this platform keeps
  // paying for.
  function extract(name) {
    const m = new RegExp('function\\s+' + name + '\\s*\\(').exec(HTML);
    if (!m) return null;
    const o = HTML.indexOf('{', m.index);
    let d = 0, k = o;
    for (; k < HTML.length; k++) {
      if (HTML[k] === '{') d++;
      else if (HTML[k] === '}') { d--; if (d === 0) break; }
    }
    return HTML.slice(m.index, k + 1);
  }
  const fnSrc = extract('sdDownscalePhoto');
  const ladderM = /var SD_PHOTO_LADDER = \[[\s\S]*?\];/.exec(HTML);
  const budgetM = /var SD_PHOTO_DATAURL_BUDGET = (\d+);/.exec(HTML);

  if (!fnSrc || !ladderM || !budgetM) {
    cannot('B1. sdDownscalePhoto / the ladder / the budget could not be found '
         + 'in stonedesk.html, so nothing in section B was measured',
           'fn=' + !!fnSrc + ' ladder=' + !!ladderM + ' budget=' + !!budgetM);
    cannot('B2. depends on B1', 'extraction failed');
    cannot('B3. depends on B1', 'extraction failed');
  } else {
    const BUDGET = Number(budgetM[1]);
    is(BUDGET > 0 && BUDGET < 65536,
       'B1. the data-URL budget is ' + BUDGET + ' characters -- under the '
     + '65,536-byte row cap with ' + (65536 - BUDGET) + ' bytes left for the '
     + 'rest of the row, which carries aiAnalysis (3-5 model sentences), '
     + 'ai_source, the ids and the JSON quoting. The budget is NOT the cap and '
     + 'that difference is the point',
       'budget=' + BUDGET);

    // A FAKE CANVAS WHOSE OUTPUT LENGTH DEPENDS ON THE RUNG, so the ladder is
    // really walked. `len = px*px*q/K` is a stand-in for an encoder, chosen so
    // that the first few rungs overshoot and a later one fits -- which is
    // exactly the case a "1024px at q0.7 is comfortably under" rule of thumb
    // gets wrong on a detailed photograph.
    function runLadder(K, imgW, imgH) {
      const tried = [];
      const ctx = {
        Math, Number, String, document: {
          createElement: () => ({
            width: 0, height: 0,
            getContext: () => ({ drawImage: () => {} }),
            toDataURL: function (type, q) {
              const px = Math.max(this.width, this.height);
              const len = Math.round(px * px * q / K);
              tried.push(px + '/' + q + '=' + len);
              return 'data:image/jpeg;base64,' + 'A'.repeat(Math.max(1, len - 23));
            }
          })
        },
        Image: function () {
          const self = this;
          Object.defineProperty(this, 'src', { set: function () {
            self.width = imgW; self.height = imgH;
            setTimeout(function () { self.onload && self.onload(); }, 0);
          } });
        },
        setTimeout
      };
      vm.createContext(ctx);
      vm.runInContext(budgetM[0] + '\n' + ladderM[0] + '\n' + fnSrc, ctx);
      return new Promise((resolve) => {
        ctx.sdDownscalePhoto('data:image/jpeg;base64,AAAA', function (out) {
          resolve({ out: out, tried: tried });
        });
      });
    }

    {
      // K chosen so 1600 and 1280 overshoot and a smaller rung fits.
      const { out, tried } = await runLadder(40, 4000, 3000);
      is(out && out.bytes <= BUDGET && tried.length > 1,
         'B2. the ladder is WALKED and the result MEASURED: ' + tried.length
       + ' rung(s) tried, the winner is ' + (out && out.rung) + ' at '
       + (out && out.bytes) + ' bytes, under the ' + BUDGET + ' budget. The '
       + 'first rung that actually fits wins -- the length is checked, not '
       + 'predicted from the dimensions',
         'tried=' + tried.join(' ') + ' out=' + JSON.stringify(out && out.rung));
    }
    {
      // An encoder that can never get under budget at any rung.
      const { out } = await runLadder(0.00001, 4000, 3000);
      is(out === null,
         'B3. when NO rung fits the budget the result is null -- not the '
       + 'original, and not a silent pass-through. A downscaler that returns '
       + 'the original on failure is how an oversized row reaches the server '
       + 'looking like a downscaled one',
         'out=' + JSON.stringify(out));
    }
  }

  // AND THE CALLER USES IT. A perfect downscaler nothing calls is dormant.
  is(/data:\s*small \? small\.data : e\.target\.result/.test(HCODE),
     'B4. handlePhotoFiles stores the DOWNSCALED data URL when the downscale '
   + 'succeeded, and falls back to the original only when it did not -- so the '
   + 'row that is written is the row that was measured',
     'the assignment was not found in stonedesk.html');

  is(/showToast\([^)]*could not be resized/.test(HTML),
     'B5. a FAILED downscale tells the user the photo is on this device only. '
   + 'The local copy is kept -- refusing it would lose the photograph to '
   + 'protect a backup -- but the silence is what ends',
     'no toast on the failed-downscale path');

  // ── C. T17: THE ROW SAYS A MODEL WROTE IT ───────────────────────────────
  console.log('\nC. T17 -- provenance on the QC note');

  {
    const high = ai.isHighRisk('sd_photos');
    const notHigh = Object.prototype.hasOwnProperty.call(ai.NOT_HIGH_RISK_AI, 'sd_photos');
    is((high ? 1 : 0) + (notHigh ? 1 : 0) === 1,
       'C1. sd_photos resolves in EXACTLY ONE of HIGH_RISK_AI / '
     + 'NOT_HIGH_RISK_AI (high=' + high + ', not-high=' + notHigh + '). '
     + 'Unclassified fails: the b18 spec requires the decision to exist, not '
     + 'to go a particular way',
       'high=' + high + ' notHigh=' + notHigh);
    if (notHigh) {
      const why = String(ai.NOT_HIGH_RISK_AI.sd_photos || '');
      is(/SD_SESSION_GATED/.test(why) && why.length > 200,
         'C2. ...and the not-high-risk entry says WHY IN TERMS OF THE APP '
       + 'rather than the content: sd_photos is not in SD_SESSION_GATED, so an '
       + 'approval gate would refuse every analysed photo on an app with no '
       + 'sign-in requirement. The entry names the order a promotion has to '
       + 'happen in',
           'reason length=' + why.length);
    } else {
      ok('C2. sd_photos is HIGH-RISK, so the approval gate applies and no '
       + 'not-high-risk reason is owed');
    }
  }

  // THE SAME LOOP THAT COVERS THE THREE SIBLINGS, so a fourth cannot be
  // forgotten the way this one was.
  {
    const SIBLINGS = ['rf_photos', 'bld_photo_analyses', 'grd_progress_photos',
                      'sd_photos'];
    const missing = SIBLINGS.filter(
      (k) => !Object.prototype.hasOwnProperty.call(red.AI_SCANNED_TEXT, k));
    is(missing.length === 0,
       'C3. all four photo-QC siblings are in AI_SCANNED_TEXT, driven by ONE '
     + 'loop: ' + SIBLINGS.join(', ') + '. sd_photos was the one that was '
     + 'missed, and a per-resource arm would have been written for the three '
     + 'that were already there',
       'missing: ' + missing.join(', '));
    const fields = red.AI_SCANNED_TEXT.sd_photos || [];
    is(fields.indexOf('aiAnalysis') !== -1 && fields.indexOf('data') === -1,
       'C4. sd_photos\' redacted field is `aiAnalysis` and NOT `data` -- the '
     + 'model prose is redacted and the base64 photograph is not, because '
     + 'redacting an image payload corrupts the image',
       JSON.stringify(fields));
  }

  is(/ai_source\s*=\s*'claude:photo-qc'/.test(HCODE),
     'C5. photoAnalyze stamps ai_source = claude:photo-qc on the row. Before '
   + 'this batch `grep -c "ai_source" stonedesk.html` was 0 for the photo '
   + 'path: aiAnalysis was d.content[0].text verbatim with no source, no '
   + 'approver and no model id',
     'the stamp was not found');

  is(!/^\s*[^/]*p\.ai_approved_by\s*=/m.test(HCODE),
     'C6. and NOTHING assigns ai_approved_by on this path. The write happens '
   + 'the moment the model answers, so there is no approver; aiFooter() reads '
   + '"AI-assisted - not reviewed", which is the true sentence',
     'an approver is being assigned client-side');

  {
    const lbl = /function sdPhotoAiLabel\s*\(\s*\)\s*\{([\s\S]*?)\n\}/.exec(HTML);
    if (!lbl) {
      cannot('C7. sdPhotoAiLabel() was not found, so the render label could '
           + 'not be measured', 'anchor absent');
    } else {
      const body = lbl[1];
      is(/Written by AI/.test(body) && !/Analyzing with Claude/.test(body),
         'C8. the render carries a label that is NOT the spinner string. '
       + '"Analyzing with Claude..." is overwritten by the answer the instant '
       + 'it arrives, so a page whose only AI wording is the spinner has no AI '
       + 'wording at all -- the b18 spec names exactly that',
         body.slice(0, 120));
      const calls = (HCODE.match(/sdPhotoAiLabel\(\)/g) || []).length;
      is(calls >= 2,
         'C9. ...and it is rendered on BOTH success paths -- the cached '
       + 'analysis and the fresh one (' + calls + ' call sites). A label on '
       + 'one of two paths is a label that is absent half the time',
         'call sites=' + calls);
    }
  }

  // ── D. A BACKUP THAT DOES NOT HAPPEN SAYS SO ────────────────────────────
  console.log('\nD. the failure reaches a human');

  {
    const m = /function sdDataFailed\s*\([^)]*\)\s*\{([\s\S]*?)\n\}/.exec(HTML);
    if (!m) {
      cannot('D1. sdDataFailed() was not found in stonedesk.html', 'anchor');
    } else {
      const body = m[1];
      // ── D1 IS DRIVEN, NOT GREPPED, AND AN ABLATION IS WHY ────────────────
      // The first version of this arm tested `/showToast\(/.test(body)`.
      // Ablating the function by putting `return;` at the top of its reporting
      // block left that arm GREEN -- the call was still in the text, just
      // unreachable. A source grep cannot see control flow, so the function is
      // extracted and RUN against a stub.
      const burstM = /var _sdFailBurst = \{[^;]*;/.exec(HTML);
      const ctx = { console: { warn: () => {} }, setTimeout, clearTimeout,
                    toasts: [] };
      ctx.showToast = function (t) { ctx.toasts.push(String(t)); };
      vm.createContext(ctx);
      try {
        vm.runInContext((burstM ? burstM[0] : '') + '\n' + m[0], ctx);
        ctx.sdDataFailed('write', 'sd_photos', 'ROW_REFUSED 23514');
      } catch (e) { ctx.toasts.push('THREW: ' + e.message); }
      is(ctx.toasts.length === 1 && /sd_photos/.test(ctx.toasts[0])
         && /device only/i.test(ctx.toasts[0]),
         'D1. sdDataFailed, RUN against a stub, reports to a HUMAN: '
       + JSON.stringify((ctx.toasts[0] || '').slice(0, 90)) + '. Its whole body '
       + 'was one console.warn, while the platform\'s own comment in '
       + 'sdSyncCollection already said the argument -- "silence would make a '
       + 'backup that is not happening look like one that is"',
         'toasts=' + JSON.stringify(ctx.toasts));
      is(/too large/i.test(ctx.toasts[0] || ''),
         'D1b. ...and the row-too-large case is NAMED, because it is the one a '
       + 'user can act on. The server now answers 400 ROW_REFUSED for a CHECK '
       + 'violation instead of 503 "tables are not set up yet", so the reason '
       + 'that reaches this function is a real one',
         'toast=' + JSON.stringify((ctx.toasts[0] || '').slice(0, 120)));
      is(/console\.warn\(/.test(body),
         'D2. ...and the console line is KEPT. The toast is for the user, the '
       + 'warn is for whoever reads a console later, and removing one to add '
       + 'the other would trade one audience for another',
         'the console.warn is gone');
      // A FAILURE PATH THAT CAN FAIL. Same rule this batch applied to three
      // transports: a report that throws takes the caller down with it.
      const guards = (body.match(/try\s*\{/g) || []).length;
      is(guards >= 2 && /typeof showToast === 'function'/.test(body),
         'D3. every branch of it is guarded and showToast is reached through a '
       + 'typeof test, so this failure path cannot itself fail -- the rule '
       + 'sdData\'s own catch records paying for twice',
         'try blocks=' + guards);
      is(/_sdFailBurst/.test(body),
         'D4. a burst is summarised rather than toasted per record. One toast '
       + 'per failure on a sync of 200 photos is its own kind of silence, '
       + 'because a user dismisses the first three and stops reading',
         'no burst counter');
    }
  }

  console.log('\n' + pass + ' passed, ' + fail + ' failed, '
            + unproven + ' unproven');
  if (failed.length) console.log(failed.length + ' ARM(S) FAILED: ' + failed.join(', '));
  if (notProved.length) console.log(notProved.length + ' ARM(S) UNPROVEN: ' + notProved.join(', '));
  process.exit(fail ? 1 : (unproven ? 3 : 0));
})().catch((e) => { console.error(e); process.exit(1); });
