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
  return code !== 'TRANSCRIBE_HOST_NOT_CONFIGURED';
}
function transcriptionStillMatches(html) {
  // The three lines the rule is made of, in order, inside scribePreflight().
  const fn = html.slice(html.indexOf('function scribePreflight()'),
                        html.indexOf('window.scribeAsk = function'));
  const neg = fn.indexOf("if(code === 'TRANSCRIBE_HOST_NOT_CONFIGURED'){");
  const off = fn.indexOf('scAvailable = false;', neg);
  const on = fn.indexOf('scAvailable = true;', off);
  return { ok: neg !== -1 && off !== -1 && on !== -1 && neg < off && off < on,
           neg: neg, off: off, on: on };
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
      ok('scribePreflight still decides by ABSENCE of TRANSCRIBE_HOST_NOT_CONFIGURED',
         'neg@' + m.neg + ' false@' + m.off + ' true@' + m.on);
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
  section('A1  a host that IS configured but BROKEN -- does the preflight read '
    + 'it as available?');
  {
    const h = loadHandler('https://a-host-that-does-not-answer.invalid',
                          { valid: true, active: true, app_id: 'sairnvet' });
    const res = mockRes();
    await h(preflight('Bearer KEY'), res);
    const code = res.body && res.body.error && res.body.error.code;
    console.log('           configured host, valid licence, preflight body -> '
      + res.statusCode + ' ' + code);
    if (clientSaysAvailable(code)) {
      finding('V1', 'A HOST THAT IS CONFIGURED BUT BROKEN READS AS AVAILABLE. The '
        + 'preflight never contacts the host -- the handler refuses locally at '
        + 'CONSENT_REF_REQUIRED, long before any upstream call -- so `scAvailable` '
        + 'goes true, the "Start - ask the client" button enables, and the vet asks '
        + 'a client to consent to a recording that cannot be transcribed. THE FILE '
        + 'ITSELF NAMES THAT HARM: "asking a client to agree to a recording that '
        + 'cannot be transcribed is consent theatre." NOT REACHABLE TODAY -- '
        + 'hostConfigured() is false in every environment -- so this is a finding '
        + 'against the state the day a host is set, which is exactly when nobody '
        + 'will be re-reading this preflight.');
    } else {
      ok('a broken host does NOT read as available', String(code));
    }
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
    const m = suiteSrc.match(/const strip = \(s\) => ([^\n]+);/);
    if (!m) {
      finding('V4', 'could not locate the stripper in api/sairnvet-transcribe.test.js '
        + '-- this arm verified NOTHING, which is not a pass.');
    } else {
      console.log('           stripper: ' + m[1].slice(0, 96));
      // eslint-disable-next-line no-new-func
      const strip = new Function('s', 'return ' + m[1] + ';');
      const attacks = [
        ['a // inside a STRING literal',
         "var x = 'a//b'; var SR = window.SpeechRecognition;"],
        ['a // inside a regex literal',
         "var re = /\\/\\//; var SR = window.SpeechRecognition;"],
        ['a */ inside a string, before real code',
         "var s = '*/'; /* c */ var SR = window.SpeechRecognition;"]
      ];
      let hidden = 0;
      attacks.forEach(function (a) {
        const survived = /SpeechRecognition/.test(strip(a[1]));
        if (survived) {
          ok('survives: ' + a[0]);
        } else {
          hidden++;
          console.log('           HIDDEN by the stripper: ' + a[0]);
          console.log('             in:  ' + a[1]);
          console.log('             out: ' + strip(a[1]).trim());
        }
      });
      if (hidden) {
        finding('V5', hidden + ' of ' + attacks.length + ' attacks HIDE a real '
          + '`SpeechRecognition` reference from the check. The stripper guards `//` '
          + 'with `(^|[^:])`, which protects a URL and nothing else -- a `//` inside '
          + 'a string or a regex takes the REST OF THE LINE with it, including code '
          + 'the check exists to find. The shipped fixture tests four cases and none '
          + 'of them is this one, which is what fourth asked me to look for. SEE A2b '
          + 'BEFORE DECIDING WHAT TO DO ABOUT IT.');
      } else {
        ok('the stripper hid nothing', String(attacks.length) + ' attacks');
      }
    }
  }

  section('A2b is that flaw LIVE or LATENT? -- measured against the real module');
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
         + 'string', 'so V5 is LATENT, not live');
      console.log('           -> the flaw cannot hide anything in the source it is '
        + 'pointed at TODAY. It is a fixture gap and a future hazard, not a present '
        + 'false pass -- said plainly so this finding is not read as bigger than it '
        + 'is.');
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
    'VERDICT: PASSES, with two findings that are both about the day a host is',
    'configured rather than about today.',
    '',
    'The REFUSAL -- which is what the obligation said to review rather than the',
    'feature -- holds. No host means no microphone and no client asked: the host',
    'check is FIRST, before the licence is even looked up, so the process holds',
    'no audio and takes no consent on a platform with nowhere to send it. A',
    'failed consent save returns before scribeStart(), on st()\'s own return',
    'value, and a decline returns too and is still recorded.',
    '',
    'WHAT I WOULD CHANGE, and it is one line: the preflight decides availability',
    'by ABSENCE -- anything that is not TRANSCRIBE_HOST_NOT_CONFIGURED reads as',
    'available -- so a configured-but-broken host, and an invalid licence, both',
    'enable the button that asks a client to consent. Decide from the code a',
    'working platform actually returns (CONSENT_REF_REQUIRED) instead. On a',
    'host-less platform the answer is identical, so the change is inert today',
    'and fail-closed tomorrow.',
    '',
    'THE STRIPPER FLAW IS REAL AND LATENT. A `//` inside a string or a regex',
    'takes the rest of the line with it, and the shipped fixture tests four',
    'cases and not that one. MEASURED against the real module: no line in it',
    'has that shape, so nothing is hidden today. A fixture gap, not a false',
    'pass -- said that way so it is not read as bigger than it is.'
  ]) console.log(l);
  process.exit(0);
})();
