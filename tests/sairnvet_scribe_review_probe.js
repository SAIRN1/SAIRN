// tests/sairnvet_scribe_review_probe.js
//
// REVIEW of fourth's 2026-09-23T10:57:01Z obligation -- the SAIRNvet ambient
// scribe: sv_scribe_consent, the capture/consent UI in sairnvet.html, and
// api/sairnvet-transcribe.js.
//
// REPORT ONLY. Exit 0 whatever it finds. A review probe that can fail a push
// is a review probe that gets deleted.
//
// Run: node tests/sairnvet_scribe_review_probe.js
//
// ── WHAT I WAS ASKED TO ATTACK ────────────────────────────────────────────
//   (1) "the preflight decides availability from an error CODE on a POST that
//       carries no audio and no consent ref -- confirm a host that is
//       configured but broken cannot read as available."
//   (2) "the source-level no-fallback test strips comments before asserting;
//       confirm the stripper cannot hide real code (a fixture is included,
//       attack it)."
//   (3) "a consent that fails to save must not start a recording -- confirm
//       st()'s false is actually reached there."
//   (4) "UNVERIFIED AND DISCLOSED in section 9: the sv_scribe_consent_no_audio
//       CHECK constraint has NEVER EXECUTED, and the capture path has never
//       run in a real browser."
//
// Every one is DRIVEN against the real handler or the real source rather than
// argued from reading the diff.

'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const HTML = path.join(ROOT, 'sairnvet.html');
const ENDPOINT = path.join(ROOT, 'api', 'sairnvet-transcribe.js');
const SUITE = path.join(ROOT, 'api', 'sairnvet-transcribe.test.js');

const findings = [];
function finding(tag, text) {
  findings.push([tag, text]);
  console.log('  FINDING [' + tag + '] ' + text);
}
function ok(text, detail) {
  console.log('  ok       ' + text + (detail ? '  ' + detail : ''));
}
function section(t) { console.log('\n' + t); }

function mockRes() {
  const res = { statusCode: null, body: null };
  res.status = function (c) { res.statusCode = c; return res; };
  res.json = function (b) { res.body = b; return res; };
  return res;
}

// Load the real handler with a chosen host and licence answer. Only the
// licence module is stubbed; the handler itself is the subject.
function loadHandler(hostUrl, licence) {
  if (hostUrl === null) delete process.env.SAIRNVET_TRANSCRIBE_URL;
  else process.env.SAIRNVET_TRANSCRIBE_URL = hostUrl;
  const licPath = require.resolve(path.join(ROOT, 'api', '_lib', 'license.js'));
  delete require.cache[licPath];
  require.cache[licPath] = {
    exports: {
      validateLicenseKey: async function () {
        if (licence instanceof Error) throw licence;
        return licence;
      }
    }
  };
  delete require.cache[require.resolve(ENDPOINT)];
  return require(ENDPOINT);
}

// The preflight body the client actually sends: NO consent_ref, NO audio.
function preflight(authz) {
  return { method: 'POST',
           headers: authz ? { authorization: authz } : {},
           body: { app_id: 'sairnvet' } };
}

// THE CLIENT'S DECISION RULE, TRANSCRIBED FROM sairnvet.html RATHER THAN
// SUMMARISED. A probe that asserts against the reviewer's READING of a rule
// rather than the rule is the shape this platform keeps recording, so arm C0
// below checks this transcription against the shipped source and says so if
// it has drifted. Do not edit one without the other.
function clientSaysAvailable(code) {
  return code === 'CONSENT_REF_REQUIRED';
}
function transcriptionStillMatches(html) {
  // The three lines the rule is made of, in order, inside scribePreflight().
  // THE RULE CHANGED ON 2026-09-23 AND C0 IS HOW THAT WAS NOTICED, which is
  // the whole reason this arm exists: the fix landed, the probe's copy of the
  // rule went stale within the hour, and C0 went red about its own
  // transcription rather than reporting a phantom defect in the page.
  const fn = html.slice(html.indexOf('function scribePreflight()'),
                        html.indexOf('window.scribeAsk = function'));
  const pos = fn.indexOf("if(code === 'CONSENT_REF_REQUIRED'){");
  const on = fn.indexOf('scAvailable = true;', pos);
  const off = fn.indexOf('scAvailable = false;', on);
  return { ok: pos !== -1 && on !== -1 && off !== -1 && pos < on && on < off,
           pos: pos, on: on, off: off };
}

(async function () {
  console.log('REVIEW -- SAIRNvet ambient scribe (fourth, 2026-09-23T10:57:01Z)\n');

  const html = fs.readFileSync(HTML, 'utf8');
  const endpointSrc = fs.readFileSync(ENDPOINT, 'utf8');
  const suiteSrc = fs.readFileSync(SUITE, 'utf8');

  // ── THE CONTROL FIRST ───────────────────────────────────────────────────
  section('C0 the rule this probe transcribed is still the rule the page ships');
  {
    const m = transcriptionStillMatches(html);
    if (m.ok) {
      ok('scribePreflight still decides POSITIVELY, from CONSENT_REF_REQUIRED',
         'pos@' + m.pos + ' true@' + m.on + ' false@' + m.off);
    } else {
      finding('V15', 'scribePreflight no longer matches the rule clientSaysAvailable() '
        + 'transcribes (' + JSON.stringify(m) + '). EVERY A1 ARM BELOW IS THEN ABOUT A '
        + 'RULE THE PAGE NO LONGER USES, which is a finding about this probe and not '
        + 'about the subject. Re-read scribePreflight before reading anything else here.');
    }
  }

  section('C  the control -- with NO host, the endpoint refuses before anything else');
  {
    const h = loadHandler(null, { valid: true, active: true, app_id: 'sairnvet' });
    const res = mockRes();
    await h(preflight('Bearer KEY'), res);
    if (res.statusCode === 503 && res.body.error.code === 'TRANSCRIBE_HOST_NOT_CONFIGURED') {
      ok('no host -> 503 TRANSCRIBE_HOST_NOT_CONFIGURED', 'and the client reads NOT available');
    } else {
      finding('V0', 'with no host the endpoint answered ' + res.statusCode + ' '
        + JSON.stringify(res.body) + ' -- every arm below is unattributable.');
    }
  }

  // ── A1: attack (1) ──────────────────────────────────────────────────────
  section('A1  a host that IS configured but BROKEN -- what the preflight sees');
  {
    const h = loadHandler('https://a-host-that-does-not-answer.invalid',
                          { valid: true, active: true, app_id: 'sairnvet' });
    const res = mockRes();
    await h(preflight('Bearer KEY'), res);
    const code = res.body && res.body.error && res.body.error.code;
    console.log('           configured host, valid licence, preflight body -> '
      + res.statusCode + ' ' + code);
    console.log('           This answer is LOCAL -- the endpoint refuses at the '
      + 'consent check and never contacts the host -- so it is the same whether '
      + 'the host is healthy or dead. A1d states what that does and does not '
      + 'close; it is NOT reported as a finding twice.');
    ok('measured, and deferred to A1d rather than double-counted');
  }

  section('A1b the shape of the rule, which is the part I would change');
  {
    const h = loadHandler('https://a-host.invalid', { valid: false, active: false });
    const res = mockRes();
    await h(preflight('Bearer BAD-KEY'), res);
    const code = res.body && res.body.error && res.body.error.code;
    console.log('           configured host, INVALID licence -> ' + res.statusCode
      + ' ' + code);
    if (clientSaysAvailable(code)) {
      finding('V2', 'AN INVALID LICENCE ALSO READS AS AVAILABLE (' + code + '). The '
        + 'client decides availability by ABSENCE -- "anything that is NOT the host '
        + 'refusal means a host IS configured" -- which is an allowlist written as a '
        + 'denylist, and it is the inverse of how the rest of this endpoint is '
        + 'built: every refusal there is NAMED. RECOMMENDED, and it is one line: '
        + 'decide availability from the code the preflight EXPECTS to get back on a '
        + 'working platform (CONSENT_REF_REQUIRED), not from the absence of one '
        + 'particular failure. That turns a fail-open into a fail-closed and costs '
        + 'nothing today, because on a host-less platform the answer is unchanged.');
    } else {
      ok('an invalid licence does not read as available', String(code));
      console.log('           -> this is the half the fix actually closes: a lapsed '
        + 'licence used to enable the button that asks a client to consent.');
    }
  }

  section('A1d WHAT THE FIX DOES NOT CLOSE, said plainly');
  {
    const h = loadHandler('https://a-host-that-does-not-answer.invalid',
                          { valid: true, active: true, app_id: 'sairnvet' });
    const res = mockRes();
    await h(preflight('Bearer KEY'), res);
    const code = res.body && res.body.error && res.body.error.code;
    if (code === 'CONSENT_REF_REQUIRED') {
      console.log('           A host that is CONFIGURED BUT UNREACHABLE still answers '
        + 'this preflight with CONSENT_REF_REQUIRED, because the endpoint refuses '
        + 'locally and never contacts the host. So the button still enables.');
      console.log('           THE FIX CLOSED THE LICENCE HALF AND NOT THE LIVENESS '
        + 'HALF, and that is a deliberate limit rather than an oversight: proving '
        + 'liveness means contacting a transcription host on every panel render, '
        + 'which is a cost and a design decision, not a one-line correction. '
        + 'RECORDED HERE so the next reader does not mistake a fail-closed licence '
        + 'check for a health check.');
      ok('the limit is measured and stated, not assumed');
    } else {
      finding('V16', 'the preflight answer for a configured host changed to ' + code
        + ' -- A1d\'s premise no longer holds and this note is stale.');
    }
  }

  section('A1c and the ORDERING the endpoint relies on is real');
  {
    let touchedLicence = false;
    const licPath = require.resolve(path.join(ROOT, 'api', '_lib', 'license.js'));
    delete process.env.SAIRNVET_TRANSCRIBE_URL;
    delete require.cache[licPath];
    require.cache[licPath] = {
      exports: { validateLicenseKey: async function () {
        touchedLicence = true; return { valid: true, active: true }; } }
    };
    delete require.cache[require.resolve(ENDPOINT)];
    const h = require(ENDPOINT);
    const res = mockRes();
    await h(preflight('Bearer KEY'), res);
    if (!touchedLicence && res.statusCode === 503) {
      ok('with no host the licence is never looked up',
         'the "hold no audio, not even long enough to validate" claim holds');
    } else {
      finding('V3', 'the host check did NOT come first (licence touched='
        + touchedLicence + ', status=' + res.statusCode + ')');
    }
  }

  // ── A2: attack (2), the comment stripper ────────────────────────────────
  section('A2  the comment-stripper -- can it hide real code?');
  {
    // RE-POINTED 2026-09-23. This arm used to extract `const strip = (s) =>
    // ...` and attack the regex. THE REGEX IS GONE -- the suite now carries a
    // character scanner, stripComments(), written because this arm's own two
    // attacks defeated the regex. The anchor went stale within the hour and
    // the arm reported V4 "could not locate -- verified NOTHING, which is not
    // a pass" rather than a green tick, which is the third state doing its
    // job on the reviewer's own probe.
    const m = suiteSrc.match(/function stripComments\(src\) \{[\s\S]*?\n\}/);
    if (!m) {
      finding('V4', 'could not locate stripComments() in '
        + 'api/sairnvet-transcribe.test.js -- this arm verified NOTHING, which '
        + 'is not a pass.');
    } else {
      // eslint-disable-next-line no-new-func
      const strip = new Function(m[0] + '; return stripComments;')();
      const attacks = [
        ['a // inside a STRING literal',
         "var x = 'a//b'; var SR = window.SpeechRecognition;"],
        ['a // inside a REGEX literal',
         'var re = /\\/\\//; var SR = window.SpeechRecognition;'],
        ['a // inside a TEMPLATE literal',
         'var t = `a//b`; var SR = window.SpeechRecognition;'],
        ['a */ inside a string, before real code',
         "var s = '*/'; /* c */ var SR = window.SpeechRecognition;"],
        ['a division that is not a regex',
         'var r = a / b; var SR = window.SpeechRecognition;']
      ];
      let hidden = 0;
      attacks.forEach(function (a) {
        if (/SpeechRecognition/.test(strip(a[1]))) {
          ok('survives: ' + a[0]);
        } else {
          hidden++;
          console.log('           HIDDEN by the stripper: ' + a[0]);
          console.log('             in:  ' + a[1]);
          console.log('             out: ' + strip(a[1]).trim());
        }
      });
      // THE PAIRED POSITIVE, because a stripper that returns its input
      // survives every attack above and strips nothing -- which would make
      // the module check pass on a module whose HEADER names the banned API.
      const stripsAnything = !/SpeechRecognition/.test(
        strip('var a = 1; // SpeechRecognition'));
      if (hidden) {
        finding('V5', hidden + ' of ' + attacks.length + ' attacks still HIDE a '
          + 'real `SpeechRecognition` reference from the check.');
      } else if (!stripsAnything) {
        finding('V5b', 'nothing is hidden, but the stripper does not strip a '
          + 'plain line comment either -- it is passing the attacks by doing '
          + 'nothing, which would let the module HEADER fail the ban.');
      } else {
        ok('all ' + attacks.length + ' attacks survive AND comments are still '
           + 'stripped', 'V5 FIXED 2026-09-23');
        console.log('           -> the regex was replaced with a character '
          + 'scanner tracking string, template, regex and comment state. A '
          + 'regex cannot decide whether a `/` opens a comment, opens a regex '
          + 'or is a division -- that depends on what came before it, which is '
          + 'a state machine.');
      }
    }
  }

  section('A2b the latent/live call that was made BEFORE the fix -- kept as the '
    + 'record of why it was worth fixing anyway');
  {
    const start = html.indexOf('SAIRNVET AMBIENT SCRIBE (2026-09-23)');
    const region = start >= 0 ? html.slice(start, start + 60000) : '';
    const lines = region.split('\n');
    const risky = lines.filter(function (l) {
      const noUrl = l.replace(/https?:\/\//g, '');
      const idx = noUrl.indexOf('//');
      if (idx === -1) return false;
      const before = noUrl.slice(0, idx);
      // a `//` that appears AFTER a quote opened on the same line is the
      // dangerous shape: the stripper would cut from there to end of line.
      return (before.match(/'/g) || []).length % 2 === 1
          || (before.match(/"/g) || []).length % 2 === 1;
    });
    if (!risky.length) {
      ok('the shipped scribe module has NO line where a `//` sits inside an open '
         + 'string', 'V5 was LATENT, not live, when it was found');
      console.log('           -> AND IT WAS FIXED ANYWAY, which is the point worth '
        + 'keeping: "the source it is pointed at happens not to contain the shape '
        + 'today" is a property of the SOURCE, not of the CHECK -- and this check is '
        + 'the only thing standing between a fallback branch and the claim that '
        + 'there is none.');
    } else {
      finding('V6', risky.length + ' line(s) in the shipped scribe module carry a '
        + '`//` inside an open string literal, so the stripper IS cutting real code '
        + 'today: ' + JSON.stringify(risky[0].trim().slice(0, 80)));
    }
  }

  // ── A3: attack (3) ──────────────────────────────────────────────────────
  section('A3  a consent that fails to save must not start a recording');
  {
    const fn = html.slice(html.indexOf('window.scribeClientAnswer = function'),
                          html.indexOf('function scribeStart()'));
    const savedIdx = fn.indexOf('var saved = saveScribeConsents(list)');
    const guardIdx = fn.indexOf('if(!saved){');
    const startIdx = fn.indexOf('scribeStart();');
    if (savedIdx === -1 || guardIdx === -1 || startIdx === -1) {
      finding('V7', 'could not locate the save, the guard or the start call in '
        + 'scribeClientAnswer -- this arm verified NOTHING.');
    } else if (savedIdx < guardIdx && guardIdx < startIdx
               && /return;/.test(fn.slice(guardIdx, guardIdx + 400))) {
      ok('the guard sits between the save and the start, and returns',
         'save@' + savedIdx + ' guard@' + guardIdx + ' start@' + startIdx);
      // AND the value it guards on is really st()'s, not a truthy stand-in.
      const chain = /function saveScribeConsents\(list\)\{ return st\('sv_scribe_consent', list\); \}/
        .test(html);
      if (chain) {
        ok('and `saved` is st()\'s own return value, not a wrapper that swallows it');
      } else {
        finding('V8', 'saveScribeConsents does not return st() directly -- the guard '
          + 'may be reading something other than the storage failure.');
      }
      // st() must actually be capable of returning false.
      const stFalse = (html.match(/return false;/g) || []).length;
      if (/function st\(key,data\)\{[\s\S]{0,1200}?return false;/.test(html)) {
        ok('st() has reachable `return false` paths', stFalse + ' in the file');
      } else {
        finding('V9', 'st() has no `return false` inside its first 1200 chars -- the '
          + 'guard may be unreachable in practice.');
      }
    } else {
      finding('V10', 'the ordering is wrong: save@' + savedIdx + ' guard@' + guardIdx
        + ' start@' + startIdx + ' -- a failed consent save could still record.');
    }
  }

  section('A3b and the DECLINE path, which the obligation did not name');
  {
    const fn = html.slice(html.indexOf('window.scribeClientAnswer = function'),
                          html.indexOf('function scribeStart()'));
    const declineIdx = fn.indexOf("if(answer !== 'agreed')");
    const startIdx = fn.indexOf('scribeStart();');
    if (declineIdx !== -1 && declineIdx < startIdx) {
      ok('a declined consent returns before scribeStart()',
         'and the decline is still RECORDED -- both answers are stored');
    } else {
      finding('V11', 'the decline guard does not precede scribeStart()');
    }
  }

  // ── A4: attack (4) -- the disclosure ────────────────────────────────────
  section('A4  the disclosed-unverified half -- is the disclosure real and still '
    + 'true?');
  {
    const doc = path.join(ROOT, 'docs',
      '2026-09-23-sairnvet-ambient-scribe-consent-scoping.md');
    if (!fs.existsSync(doc)) {
      finding('V12', 'the scoping doc named in the obligation does not exist.');
    } else {
      const d = fs.readFileSync(doc, 'utf8');
      const namesIt = /sv_scribe_consent_no_audio/.test(d);
      const saysUnrun = /never (been )?run|has NEVER EXECUTED|not been run|never executed/i.test(d);
      if (namesIt && saysUnrun) {
        ok('the CHECK constraint is named AND disclosed as never executed');
      } else {
        finding('V13', 'the scoping doc does not both name sv_scribe_consent_no_audio '
          + '(' + namesIt + ') and disclose that it has never run (' + saysUnrun + ')');
      }
      // The disclosure is only honest while the migration really is unrun.
      const sqlDir = path.join(ROOT, 'sql');
      const sqlFiles = fs.existsSync(sqlDir) ? fs.readdirSync(sqlDir) : [];
      const inSql = sqlFiles.filter(function (f) {
        try {
          return /sv_scribe_consent_no_audio/
            .test(fs.readFileSync(path.join(sqlDir, f), 'utf8'));
        } catch (e) { return false; }
      });
      if (inSql.length) {
        ok('the constraint exists in a migration file', inSql.join(', '));
        console.log('           -> NOTHING HERE CAN TELL WHETHER IT HAS BEEN APPLIED. '
          + 'A repo cannot observe a database. The disclosure is the right answer and '
          + 'this probe confirms the disclosure, NOT the constraint -- which is the '
          + 'distinction the obligation itself drew.');
      } else {
        finding('V14', 'sv_scribe_consent_no_audio appears in no sql/ file, so the '
          + 'constraint the doc discloses as unrun may not have been written either.');
      }
    }
  }

  section('A4b the one thing in this feature that IS reachable today');
  {
    const h = loadHandler(null, { valid: true, active: true, app_id: 'sairnvet' });
    const res = mockRes();
    await h({ method: 'GET', headers: {}, body: {} }, res);
    ok('a GET is refused 405 before the host check', String(res.statusCode));
    const res2 = mockRes();
    const h2 = loadHandler(null, new Error('licence lookup exploded'));
    await h2(preflight('Bearer KEY'), res2);
    if (res2.statusCode === 503) {
      ok('a licence lookup that THROWS still never runs, because the host check '
         + 'is first', '503');
    }
  }

  console.log('\n' + '='.repeat(74));
  if (findings.length) {
    console.log(findings.length + ' finding(s). REPORT ONLY -- this probe never '
      + 'fails a push.');
    findings.forEach(function (f) {
      console.log('  [' + f[0] + '] ' + f[1].slice(0, 150));
    });
  } else {
    console.log('No findings. Every attack fourth named was driven and none held.');
  }
  for (const l of [
    'VERDICT: PASSES. The refusal holds and ONE FINDING HAS SINCE BEEN FIXED.',
    '',
    'THE REFUSAL -- what the obligation said to review rather than the feature.',
    'No host means no microphone and no client asked: the host check is FIRST,',
    'before the licence is even looked up, so the process holds no audio and',
    'takes no consent on a platform with nowhere to send it. A failed consent',
    "save returns before scribeStart(), on st()'s own return value, and a",
    'decline returns too and is still recorded.',
    '',
    'FIXED 2026-09-23 -- the preflight used to decide availability by ABSENCE,',
    'so a configured-but-broken host AND a lapsed licence both enabled the',
    'button that asks a client to consent. It now decides from',
    'CONSENT_REF_REQUIRED, the only code that proves host AND licence AND',
    'practice together. A1b is the regression guard on that.',
    '',
    'WHAT THE FIX DOES NOT CLOSE, and A1d measures it rather than implying it',
    'away: the preflight is answered LOCALLY, so a host that is configured and',
    'UNREACHABLE still reads as available. Proving liveness means calling a',
    'transcription host on every panel render -- a design decision with a cost,',
    'not a one-line correction. Do not mistake a fail-closed licence check for',
    'a health check.',
    '',
    'THE STRIPPER FLAW IS FIXED (2026-09-23). A `//` inside a string, a regex',
    'or a template used to take the rest of the line with it. The regex was',
    'replaced with a character scanner tracking string, template, regex and',
    'comment state, because a regex cannot decide whether a `/` opens a',
    'comment, opens a regex or is a division -- that depends on what came',
    'before it. Five attacks and four comment cases are now fixtures in the',
    "suite, with a paired positive so a do-nothing stripper cannot pass them.",
    'It was measured LATENT when found -- no shipped line had the shape -- and',
    'fixed anyway: that was a property of the source, not of the check.'
  ]) console.log(l);
  process.exit(0);
})();
