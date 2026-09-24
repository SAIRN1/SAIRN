// tests/sairncode_pt_gp_modifier.js
//
// Run:  node tests/sairncode_pt_gp_modifier.js
//
// ── WHY THIS FILE EXISTS ───────────────────────────────────────────────────
// SAIRNcode's Physical Therapy panel checked the 8-minute rule, the KX
// threshold, CQ, MPPR and the 2026 RTM windows, and had NO field and NO rule
// for GP -- the therapy DISCIPLINE modifier. `\bGP\b` returned zero hits in
// the whole app. Every always-therapy service furnished under a physical
// therapy plan of care carries GP (GO for occupational therapy, GN for
// speech-language pathology), and a therapy line submitted without one is
// returned as UNPROCESSABLE: the claim is not denied, it is never adjudicated.
//
// SO IT IS THE ONE MISSING MODIFIER THAT STOPS THE CLAIM ENTIRELY rather than
// changing what it pays. CQ costs 15%. KX costs an appeal. A missing discipline
// modifier costs the whole submission, and the panel's summary line --
// "No blocking issues found by the checks that ran" -- said exactly that while
// the check that would have caught it did not exist.
//
// ── WHY IT WAS EASY TO MISS, WHICH IS WORTH A TEST AND NOT JUST A COMMENT ──
// "PT" already means something else in this app. The Modifier Routing panel's
// first section is the PT modifier -- a screening colonoscopy converting to
// diagnostic mid-procedure -- so a reader searching for therapy modifiers finds
// "PT" throughout the file and reads the area as covered. The nav tooltip on
// the therapy panel listed "KX threshold, CQ modifier, MPPR, 2026 RTM codes"
// and was accurate about everything it named.
//
// ── WHAT THIS DOES NOT ASSERT ──────────────────────────────────────────────
// It does not check that the CODE LIST is right. This app holds no copy of the
// CMS always-therapy list, deliberately -- the KX constants are shared for the
// same reason -- so the rule is scoped to the timed codes the panel was given,
// which the 8-minute rule has already treated as therapy. RTM codes are
// excluded and the exclusion is asserted below rather than left to be noticed:
// whether a given RTM service furnished by a therapist takes a discipline
// modifier was NOT verified, and a block on an unverified rule refuses
// compliant claims -- the direction this app's own DMEPOS gate records getting
// wrong.

'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ROOT = path.dirname(__dirname);
const html = fs.readFileSync(path.join(ROOT, 'sairncode.html'), 'utf8');

let n = 0, failed = 0;
function ok(cond, name) {
  n += 1;
  console.log((cond ? '  ok   ' : '  FAIL ') + name);
  if (!cond) failed += 1;
}
function section(t) { console.log('\n' + t); }

// Balanced-brace extraction, the same shape tests/sairncode_gates.js uses:
// quote- and comment-aware, so a brace inside a string or a comment does not
// end the function early.
function grab(sig) {
  const start = html.indexOf(sig);
  assert.ok(start > 0, 'not found in sairncode.html: ' + sig);
  let i = html.indexOf('{', start + sig.length - 1), depth = 0, q = null;
  for (; i < html.length; i++) {
    const c = html[i], p = html[i - 1];
    if (q) { if (c === q && p !== '\\') q = null; continue; }
    if (c === '"' || c === "'" || c === '`') { q = c; continue; }
    if (c === '/' && html[i + 1] === '/') { i = html.indexOf('\n', i); continue; }
    if (c === '/' && html[i + 1] === '*') { i = html.indexOf('*/', i) + 1; continue; }
    if (c === '{') depth++;
    else if (c === '}') { depth--; if (!depth) return html.slice(start, i + 1); }
  }
  throw new Error('unterminated: ' + sig);
}

function grabVar(name) {
  // `\s*=` and not ` = `: SC_RTM_LONG_WINDOW is written with two spaces to
  // align with its sibling, and a single-space pattern found nothing and threw.
  const re = new RegExp('var ' + name + '\\s*=\\s*[^;]*;');
  const m = re.exec(html);
  assert.ok(m, 'not found in sairncode.html: var ' + name);
  return m[0];
}

console.log('SAIRNcode PT: the GP discipline modifier\n');

// ── THE FIXTURE IS THE REAL CODE, PULLED OUT OF THE REAL FILE ─────────────
// Not a re-implementation. A copy of the validator here would agree with
// itself forever and say nothing about what the panel does.
const ctx = {};
vm.createContext(ctx);
for (const v of ['KX_THRESHOLD_2026', 'KX_MR_THRESHOLD_2026',
                 'SC_RTM_SHORT_WINDOW', 'SC_RTM_LONG_WINDOW',
                 'SC_RTM_SOMETIMES_THERAPY']) {
  vm.runInContext(grabVar(v), ctx);
}
vm.runInContext(grab('var SC_PT_SOURCES = '), ctx);
vm.runInContext(grab('function scPtUnitsFromMinutes(totalMinutes){'), ctx);
vm.runInContext(grab('function scPtFinding(sev, rule, detail, srcKey){'), ctx);
vm.runInContext(grab('function scValidatePtSession(input){'), ctx);

const run = (input) => ctx.scValidatePtSession(input);
const blocks = (res, frag) =>
  res.findings.filter((f) => f.severity === 'block' && f.rule.indexOf(frag) !== -1);
const warns = (res, frag) =>
  res.findings.filter((f) => f.severity === 'warn' && f.rule.indexOf(frag) !== -1);

// ── 0. THE FIXTURE IS REAL ────────────────────────────────────────────────
section('0. the fixture is the real validator, not a copy');
{
  ok(typeof ctx.scValidatePtSession === 'function',
     'scValidatePtSession was extracted from sairncode.html and runs');
  // CONTROL: without this, every arm below could pass against a validator that
  // had stopped doing anything at all.
  const r = run({ timed_minutes_by_code: { '97110': 23 }, gp_applied_codes: ['97110'] });
  ok(r.total_timed_minutes === 23 && r.units_supported === 2,
     'CONTROL: the 8-minute rule still computes -- 23 minutes supports 2 units, '
     + 'so a clean GP result below is not a validator that returns nothing');
  ok(ctx.SC_PT_SOURCES && typeof ctx.SC_PT_SOURCES.gp === 'string'
     && ctx.SC_PT_SOURCES.gp.length > 40,
     'SC_PT_SOURCES carries a `gp` citation, so the finding renders with a '
     + 'source like every other rule in this panel');
}

// ── 1. THE RULE ───────────────────────────────────────────────────────────
section('1. a timed therapy service with no GP is BLOCKED');
{
  const r = run({ timed_minutes_by_code: { '97110': 22 } });
  const b = blocks(r, 'GP modifier missing');
  ok(b.length === 1, 'one timed code, no GP -> exactly 1 blocking finding, got ' + b.length);
  ok(b.length === 1 && b[0].rule.indexOf('97110') !== -1,
     '...and it names the code: ' + (b[0] && b[0].rule));
  ok(b.length === 1 && /UNPROCESSABLE/.test(b[0].detail),
     '...and says the claim is never adjudicated rather than denied, which is '
     + 'the difference that decides what a coder does next');
  ok(b.length === 1 && /GO|GN/.test(b[0].detail),
     '...and names GO and GN, so a service on the wrong panel sends the coder '
     + 'to the right question instead of to a second modifier');
  ok(b.length === 1 && b[0].source === ctx.SC_PT_SOURCES.gp,
     '...and carries the CMS citation rather than an empty source string');
  ok(r.blocking >= 1, 'the session reports blocking > 0, so the panel headline '
     + 'cannot read "No blocking issues found"');
}

section('2. GP present clears it, and clears ONLY it');
{
  const r = run({ timed_minutes_by_code: { '97110': 22 }, gp_applied_codes: ['97110'] });
  ok(blocks(r, 'GP modifier missing').length === 0,
     'GP recorded on the one timed code -> no GP finding');
  // CONTROL: the arm above must not pass because the rule stopped firing for
  // everyone. A second code with no GP in the SAME session still blocks.
  const r2 = run({ timed_minutes_by_code: { '97110': 22, '97140': 15 },
                   gp_applied_codes: ['97110'] });
  const b2 = blocks(r2, 'GP modifier missing');
  ok(b2.length === 1 && b2[0].rule.indexOf('97140') !== -1,
     'CONTROL: GP on one of two codes still blocks the other, by name: '
     + (b2[0] && b2[0].rule));
}

section('3. it is case- and whitespace-insensitive the way the CQ rule is');
{
  const r = run({ timed_minutes_by_code: { '97110': 22 }, gp_applied_codes: [' 97110 '] });
  ok(blocks(r, 'GP modifier missing').length === 0,
     'a padded entry matches -- scParseList trims and uppercases, and the rule '
     + 'must not undo that');
}

section('4. GP on a code that is not in the session is a WARN, not a block');
{
  const r = run({ timed_minutes_by_code: { '97110': 22 },
                  gp_applied_codes: ['97110', '97530'] });
  ok(blocks(r, 'GP modifier missing').length === 0, 'the session code is satisfied');
  const w = warns(r, 'GP recorded on 97530');
  ok(w.length === 1, 'the extra code produces exactly 1 warning, got ' + w.length);
  ok(w.length === 1 && w[0].severity === 'warn',
     '...at WARN and not BLOCK -- a modifier on the wrong code is a mismatch to '
     + 'resolve, not a claim that cannot go out');
}

section('5. an empty session produces NO GP finding at all');
{
  const r = run({ timed_minutes_by_code: {} });
  ok(blocks(r, 'GP modifier missing').length === 0
     && warns(r, 'GP recorded').length === 0,
     'nothing entered -> nothing claimed. A rule that fires on an empty form '
     + 'trains people to ignore it');
  // ...and neither does a session of ONLY GP entries with no minutes, which is
  // the half that would otherwise warn about every code the user typed.
  const r2 = run({ timed_minutes_by_code: {}, gp_applied_codes: ['97110'] });
  ok(warns(r2, 'GP recorded').length === 0,
     'GP entries with no timed minutes at all are silent too -- the panel has '
     + 'no session to judge them against yet');
}

// ── 6. THE DISCLOSED SCOPE, ASSERTED ──────────────────────────────────────
section('6. RTM codes are NOT swept into the rule -- the disclosed scope, driven');
{
  const r = run({ timed_minutes_by_code: { '97110': 22 },
                  gp_applied_codes: ['97110'],
                  rtm_codes: ['98985'], rtm_monitoring_days: 10 });
  const b = blocks(r, 'GP modifier missing');
  ok(b.length === 0,
     'an RTM code in the same submission does NOT get a GP block: it is not a '
     + 'timed therapy service and whether it takes a discipline modifier was '
     + 'not verified. Silence is the honest answer and this asserts it rather '
     + 'than leaving it to be noticed');
  // CONTROL: the RTM window rule itself still fires, so the arm above is about
  // the GP rule's scope and not about RTM checking having died.
  const r2 = run({ timed_minutes_by_code: { '97110': 22 },
                   gp_applied_codes: ['97110'],
                   rtm_codes: ['98985'], rtm_monitoring_days: 40 });
  ok(r2.findings.some((f) => f.severity === 'block' && f.rule.indexOf('98985') !== -1),
     'CONTROL: the RTM window rule still blocks 40 days on 98985, so arm 6 is '
     + 'measuring scope and not a dead RTM check');
}

// ── 6b. THE RTM SILENCE BECAME A WARN, 2026-09-24 ────────────────────────
// Section 6 above asserted the SILENCE, on the ground the question was
// unverified. The independent review answered it: CMS designated the RTM
// family SOMETIMES THERAPY (CY2022 PFS final rule), and everything in this
// panel is a PT plan-of-care context by construction -- so an RTM line here
// takes GP on CMS's own framing. Added as a WARN and not a block, at exactly
// the confidence the review stated: the rule is cited from review knowledge,
// not from a primary source reached in-session, and blocking on an unverified
// rule refuses compliant claims. Section 6's arms still hold -- no BLOCK is
// ever produced for an RTM line -- which is asserted here too, so an
// escalation to block cannot land without a deliberate edit to both.
section('6b. an RTM line with no GP now WARNS -- and never blocks');
{
  const r = run({ timed_minutes_by_code: {}, gp_applied_codes: [],
                  rtm_codes: ['98985'], rtm_monitoring_days: 10 });
  const w = r.findings.filter((f) => /RTM code 98985 has no GP/.test(f.rule));
  ok(w.length === 1 && w[0].severity === 'warn',
     'an RTM code with no GP produces exactly one WARN: '
     + JSON.stringify(r.findings.map((f) => f.severity + ':' + f.rule)));
  ok(r.blocking === 0,
     'and it is NOT a block -- blocking on a rule cited from review knowledge '
     + 'refuses compliant claims, the DMEPOS direction');
  ok(/CY2022/.test(w[0].source || ''),
     'the finding carries its CY2022 PFS source, so the confidence level '
     + 'travels with the warning');
  // FLIPPED 2026-09-24, by the review the source text itself asked for. The
  // arm used to assert the source SAYS the cite is unpinned; the discharge
  // reached the primary source (CMS MLN Matters MM14250 / CR 14250, which
  // quotes the CY2022 designation and the GP/GO/GN requirement verbatim) and
  // pinned it. The confidence still travels with the finding -- it is just a
  // different confidence now, and the source must say WHICH document pinned
  // it so the next reader can re-verify rather than take a naked citation.
  ok(/PINNED/.test(w[0].source || '') && /MM14250/.test(w[0].source || ''),
     'the source names the primary CMS document that pinned the cite '
     + '(MM14250) -- a precise-looking citation nobody can re-check is worse '
     + 'than an honest unpinned one');
  ok(/WARN AND NOT A BLOCK|warning/i.test(w[0].source || ''),
     'and it still states why warn survives the pinning: the requirement '
     + 'attaches to therapist-RENDERED lines, and the panel cannot see who '
     + 'rendered one');

  // GP recorded on the RTM code itself silences the warn.
  const r2 = run({ timed_minutes_by_code: {}, gp_applied_codes: ['98985'],
                   rtm_codes: ['98985'], rtm_monitoring_days: 10 });
  ok(r2.findings.filter((f) => /RTM code .* has no GP/.test(f.rule)).length === 0,
     'GP recorded on the RTM code silences the warn -- the coder who already '
     + 'did the thing is not nagged about it');

  // Only the KNOWN RTM family warns: an arbitrary code in the RTM field is
  // not this rule's business.
  const r3 = run({ timed_minutes_by_code: {}, gp_applied_codes: [],
                   rtm_codes: ['12345'], rtm_monitoring_days: 10 });
  ok(r3.findings.filter((f) => /RTM code .* has no GP/.test(f.rule)).length === 0,
     'a code outside the sometimes-therapy family gets no RTM-GP warn');

  // ── THE FAMILY BOUNDARY IS CMS'S LIST, NOT THE WINDOW MAPS (2026-09-24) ──
  // The author's own attack point 2 asked whether the window maps -- built
  // for the day-window rule -- were the right boundary. Pinning the citation
  // answered it: they disagree with CMS in BOTH directions. MM14250's family
  // is 98975/76/77/79/80/81/84/85; the window maps ALSO hold 98978/98986
  // (the CBT device codes, which CMS has not designated sometimes therapy)
  // and MISS 98975 and the treatment-management codes (which carry the
  // designation and have no day window). One arm per direction:
  const r4 = run({ timed_minutes_by_code: {}, gp_applied_codes: [],
                   rtm_codes: ['98975'], rtm_monitoring_days: null });
  ok(r4.findings.filter((f) => /RTM code 98975 has no GP/.test(f.rule)).length === 1,
     '98975 (setup -- designated CY2022, in NO window map) now warns: the '
     + 'under-coverage direction');
  const r5 = run({ timed_minutes_by_code: {}, gp_applied_codes: [],
                   rtm_codes: ['98986'], rtm_monitoring_days: 10 });
  ok(r5.findings.filter((f) => /RTM code 98986 has no GP/.test(f.rule)).length === 0,
     '98986 (CBT -- in a window map, NOT CMS-designated) gets no GP warn: '
     + 'warning on it would attribute a designation CMS never made');
  ok(!!ctx.SC_RTM_SOMETIMES_THERAPY && ctx.SC_RTM_SOMETIMES_THERAPY['98980'] === true
     && ctx.SC_RTM_SOMETIMES_THERAPY['98986'] === undefined,
     'the family is its own list (SC_RTM_SOMETIMES_THERAPY), not a reuse of '
     + 'the window maps -- the boundary and the day-window rule can now move '
     + 'independently, which is how CMS actually moves them');

  // NEGATIVE CONTROL: the warn is capable of being broken. Escalate it to a
  // block in a mutated copy and the never-blocks arm above must be the one
  // that would catch it -- proven by driving the mutant, not asserted.
  // SRC and freshRun are section 8's locals, re-derived here the same way --
  // grab() is top-level and cheap, and borrowing across block scopes is how
  // an arm quietly starts depending on section ordering.
  const SRC = grab('function scValidatePtSession(input){');
  const freshRun = (mutatedSrc) => {
    const c2 = {};
    vm.createContext(c2);
    for (const v of ['KX_THRESHOLD_2026', 'KX_MR_THRESHOLD_2026',
                     'SC_RTM_SHORT_WINDOW', 'SC_RTM_LONG_WINDOW',
                 'SC_RTM_SOMETIMES_THERAPY']) {
      vm.runInContext(grabVar(v), c2);
    }
    vm.runInContext(grab('var SC_PT_SOURCES = '), c2);
    vm.runInContext(grab('function scPtUnitsFromMinutes(totalMinutes){'), c2);
    vm.runInContext(grab('function scPtFinding(sev, rule, detail, srcKey){'), c2);
    vm.runInContext(mutatedSrc, c2);
    return c2.scValidatePtSession;
  };
  const mutated = SRC.replace(
    "findings.push(scPtFinding('warn', 'RTM code ' + c + ' has no GP recorded'",
    "findings.push(scPtFinding('block', 'RTM code ' + c + ' has no GP recorded'");
  ok(mutated !== SRC, 'ANCHOR: the escalation mutation planted nothing');
  const fnMut = freshRun(mutated);
  const rm = fnMut({ timed_minutes_by_code: {}, gp_applied_codes: [],
                     rtm_codes: ['98985'], rtm_monitoring_days: 10 });
  ok(rm.blocking > 0,
     'CONTROL: the escalated mutant DOES block, so the never-blocks arm is '
     + 'testing a live property rather than one nothing could change');
}

// ── 7. THE PANEL IS WIRED TO IT ───────────────────────────────────────────
// A rule the form cannot reach is worse than no rule: it reads as covered.
section('7. the panel field exists and reaches the validator');
{
  ok(/id="pt-gp"/.test(html), 'the PT panel has a pt-gp input');
  ok(/gp_applied_codes:\s*scParseList\(document\.getElementById\('pt-gp'\)\.value\)/
     .test(html),
     'runPtCheck passes it through as gp_applied_codes, via the same '
     + 'scParseList the CQ field uses');
  const tip = /data-tip="Physical Therapy[^"]*"/.exec(html);
  ok(tip && /\bGP\b/.test(tip[0]),
     'the nav tooltip names GP -- it listed every other modifier this panel '
     + 'checks and was accurate about all of them: ' + (tip && tip[0].slice(0, 90)));
}

// ── 8. THE NEGATIVE CONTROL, AND IT WRITES NOTHING ────────────────────────
// Every arm above passes against the rule as it stands. That says nothing about
// whether they would NOTICE the rule being removed -- which is the failure this
// platform keeps finding: an arm written as "expect no findings" stays green on
// a file nobody touched.
//
// NO FILE IS MUTATED. The validator is already extracted as TEXT, so the
// mutation is applied to that string and re-run in a fresh context. A control
// that has to write into sairncode.html to test sairncode.html is a control
// that can lose another session's work on a tree four clones share -- and this
// one cannot, structurally, because it never opens the file for writing.
//
// EACH MUTATION ASSERTS ITS ANCHOR MATCHES EXACTLY ONCE before it is applied.
// A no-op mutation re-runs the ORIGINAL validator and reports the arm as
// caught, which is the same false pass dressed as a negative control.
section('8. NEGATIVE CONTROL -- each arm is shown to fail when the rule is broken');
{
  const SRC = grab('function scValidatePtSession(input){');
  const freshRun = (mutatedSrc) => {
    const c2 = {};
    vm.createContext(c2);
    for (const v of ['KX_THRESHOLD_2026', 'KX_MR_THRESHOLD_2026',
                     'SC_RTM_SHORT_WINDOW', 'SC_RTM_LONG_WINDOW',
                 'SC_RTM_SOMETIMES_THERAPY']) {
      vm.runInContext(grabVar(v), c2);
    }
    vm.runInContext(grab('var SC_PT_SOURCES = '), c2);
    vm.runInContext(grab('function scPtUnitsFromMinutes(totalMinutes){'), c2);
    vm.runInContext(grab('function scPtFinding(sev, rule, detail, srcKey){'), c2);
    vm.runInContext(mutatedSrc, c2);
    return c2.scValidatePtSession;
  };
  const MUTATIONS = [
    ['the GP block is deleted outright',
     "                    findings.push(scPtFinding('block', 'GP modifier missing on ' + code,",
     "                    if (false) findings.push(scPtFinding('block', 'GP modifier missing on ' + code,",
     (fn) => fn({ timed_minutes_by_code: { '97110': 22 } })
              .findings.filter((f) => f.rule.indexOf('GP modifier missing') !== -1).length === 0],
    ['the GP finding is downgraded from block to warn',
     "scPtFinding('block', 'GP modifier missing on ' + code,",
     "scPtFinding('warn', 'GP modifier missing on ' + code,",
     (fn) => fn({ timed_minutes_by_code: { '97110': 22 } }).blocking === 0],
    ['GP is treated as satisfied whenever ANY code carries it',
     '                    if (gpApplied.indexOf(code) !== -1) return;',
     '                    if (gpApplied.length) return;',
     (fn) => fn({ timed_minutes_by_code: { '97110': 22, '97140': 15 },
                  gp_applied_codes: ['97110'] })
              .findings.filter((f) => f.rule.indexOf('97140') !== -1).length === 0],
  ];
  for (const [label, find, replace, broke] of MUTATIONS) {
    const hits = SRC.split(find).length - 1;
    ok(hits === 1, '[' + label + '] the anchor matches EXACTLY once (found '
       + hits + ')');
    if (hits !== 1) continue;
    const mutated = SRC.replace(find, replace);
    ok(mutated !== SRC, '...and the mutation changed the source');
    let fn = null, why = '';
    try { fn = freshRun(mutated); } catch (e) { why = String(e && e.message); }
    ok(!!fn, '...and the mutated validator still PARSES, so a caught arm is '
       + 'the rule failing and not a syntax error: ' + why);
    if (fn) ok(broke(fn), '...and the arm above NOTICES it');
  }
  // AND THE CONTROL ON THE CONTROL: the unmutated source, run through the same
  // fresh-context path, must still be clean. Without this, a broken freshRun()
  // would report every mutation as caught.
  const clean = freshRun(SRC);
  ok(clean({ timed_minutes_by_code: { '97110': 22 }, gp_applied_codes: ['97110'] })
       .findings.filter((f) => f.rule.indexOf('GP') !== -1).length === 0,
     'CONTROL: the UNMUTATED source through the same path is clean -- otherwise '
     + 'every mutation above would read as caught for the wrong reason');
}

console.log('\n' + (failed
  ? failed + ' OF ' + n + ' ASSERTIONS FAILED'
  : 'ALL ' + n + ' ASSERTIONS PASS'));
process.exit(failed ? 1 : 0);
