// tests/sairnfreedom_segregation_of_duties.js
//
//     node tests/sairnfreedom_segregation_of_duties.js
//
// REQUIREMENT: SAIRNfreedom gained three controls on 2026-09-27 -- two-person
//   approval on money leaving a gaming account, a trustee audit the finance
//   officer may not prepare, and a standing flag on every transfer out of the
//   bingo account. This file drives their refusals in BOTH directions, and pins
//   the ORC 2915.101 threshold correction with the DIRECTION of the old error.
//
// Exit 0 clean / 1 findings.
//
// ── WHY THESE THREE AND NOT A GENERAL AUDIT ────────────────────────────────
// A 2026-09-27 external audit mapped Ohio's 2024-2026 charitable-gaming record
// against this app. No post in it was penalised because of software; every theft
// was a segregation-of-duties failure that ran for years:
//
//   FOE No. 213, Youngstown -- licence REVOKED Nov 2025; findings included
//     "blank checks signed without the two required signatures".
//   AMVETS Post 24, Dayton -- ~$622,000, 41 months federal prison, from
//     transfers between accounts nobody reconciled for ~2.5 years.
//   VFW Post 4044 -- $35,007.30; charitable-account cheques with false memos
//     passed review for ~2 years.
//   Miamisburg Moose -- $119,420.67 restitution; no board review of card
//     statements or payroll changes.
//
// The app already tagged disbursements to the ORC 2915.01(V) purpose lists,
// which stops the wrong CATEGORY and cannot stop a false MEMO. These arms are
// about the controls that were missing.
//
// ── THE SILENT HALF IS THE HALF THAT MATTERS ───────────────────────────────
// A gate that refuses everything passes every "it refuses" arm. So every refusal
// arm below is paired with a CLEAN arm on input that must go through, and
// section A5 exists for exactly that reason.
//
// ── AND ONE ABLATION, because a refusal list is easy to satisfy by accident ─
// Section A6 removes the same-person check from a COPY of the extracted source
// and asserts the A2 case then passes. If A2 can be green with the check gone,
// A2 was never testing the check. Nothing on disk is mutated: the copy is a
// string in this process.
//
// ── THE ANCHOR DISCIPLINE ──────────────────────────────────────────────────
// Every function is extracted from sairnfreedom.html by a literal marker and
// grab() THROWS if the marker is absent. An arm whose anchor has moved must fail
// loudly rather than pass against a function it never found.
'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const ROOT = path.join(__dirname, '..');
const APP = path.join(ROOT, 'sairnfreedom.html');
const html = fs.readFileSync(APP, 'utf8');
// THE SHARED STRIPPER, not a local regex. Section D asserts a sentence is GONE,
// and this file's own header quotes that sentence -- the exact shape where an
// ad-hoc strip produces a green run against a file that should be red.
const { stripComments } = require(path.join(ROOT, 'tests/lib/strip_comments.js'));

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('\n' + t); }

function grab(startMarker, endRe) {
  const s = html.indexOf(startMarker);
  assert.ok(s > 0, 'ANCHOR GONE from sairnfreedom.html: ' + startMarker);
  assert.strictEqual(html.indexOf(startMarker, s + 1), -1,
    'ANCHOR IS NOT UNIQUE, so which copy was extracted is unknown: ' + startMarker);
  const rel = html.slice(s).search(endRe);
  assert.ok(rel > 0, 'unterminated: ' + startMarker);
  return html.slice(s, s + rel);
}

const END = /\r?\n\}/;
const SRC = [
  grab('function activeOfficerNames(){', END) + '\n}\n',
  grab('function isActiveOfficer(name){', END) + '\n}\n',
  grab('function dualApprovalRefusals(preparedBy, approvedBy, payee, whatLabel){', END) + '\n}\n',
  grab('function officerHolds(name, capId){', END) + '\n}\n',
  grab('function trusteeAuditRefusals(a){', END) + '\n}\n',
  grab('function p4ThresholdStale(){', END) + '\n}\n',
  grab('function tieredRequirement(net, threshold){', END) + '\n}\n',
].join('\n');

// The three real constants, extracted rather than retyped -- a hand-copied
// 330000 here would agree with itself if the app's changed.
function grabNum(marker) {
  const line = grab(marker, /;/);
  const m = line.match(/=\s*([0-9.]+)/);
  assert.ok(m, 'no number on: ' + marker);
  return Number(m[1]);
}
const AG_ADJUSTED = grabNum('var P4_AG_ADJUSTED_THRESHOLD');
const STAT_BASE = grabNum('var P4_STATUTORY_BASE_THRESHOLD');

function harness(opts) {
  opts = opts || {};
  const officers = opts.officers || [];
  const ctx = {
    console,
    P4_AG_ADJUSTED_THRESHOLD: AG_ADJUSTED,
    P4_STATUTORY_BASE_THRESHOLD: STAT_BASE,
    TIER1_MIN_DISTRIBUTION: 0.25,
    TIER2_MIN_DISTRIBUTION: 0.50,
    TIER2_OWN_PURPOSE_ALLOWANCE: 0.05,
    getOfficers: () => officers,
    getPost: () => ({ orgType: 'vfw' }),
    getP4Config: () => ({ threshold: opts.threshold }),
    titleFor: (cap) => ({ 'finance.write': 'Quartermaster',
                          'trustee.audit': 'Trustee' }[cap] || cap),
    localToday: () => (opts.today || '2026-09-27'),
    parseLocalDate: (s) => {
      if (!s) return null;
      const m = String(s).match(/^(\d{4})-(\d{2})-(\d{2})$/);
      if (!m) return null;
      return new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
    },
  };
  vm.createContext(ctx);
  vm.runInContext(opts.src || SRC, ctx);
  return ctx;
}

const OFFICERS = [
  { name: 'Ray Dunn',    capability: 'post.govern',   active: true },
  { name: 'Ed Marsh',    capability: 'finance.write', active: true },
  { name: 'Tom Byrne',   capability: 'trustee.audit', active: true },
  { name: 'Al Pike',     capability: 'trustee.audit', active: true },
  { name: 'Gone Guy',    capability: 'records.write', active: false },
];
const reasons = (list) => list.map((r) => r.text).join(' || ');

console.log('SAIRNfreedom -- the three segregation-of-duties controls, driven');

// ── A. TWO-PERSON APPROVAL ──────────────────────────────────────────────────
section('A. two named officers, and not the same one twice');
const A = harness({ officers: OFFICERS });

test('A1. NO approver is refused, and the refusal names the case it comes from',
  () => {
    const r = A.dualApprovalRefusals('Ray Dunn', '', 'Acme Supply', 'payment');
    assert.ok(r.length >= 1, 'a payment with no second approver was accepted');
    assert.ok(/second officer must approve/i.test(reasons(r)), reasons(r));
    assert.ok(/213/.test(reasons(r)),
      'the refusal does not name the revocation it comes from, so a user reads '
      + 'it as an app rule rather than a real consequence: ' + reasons(r));
    assert.ok(r.every((x) => x.fatal === true),
      'a segregation refusal that is not fatal is advice');
  });

test('A2. approver === preparer is refused -- the FOE 213 shape exactly',
  () => {
    const r = A.dualApprovalRefusals('Ray Dunn', 'Ray Dunn', 'Acme Supply', 'payment');
    assert.ok(/same officer/i.test(reasons(r)),
      'one person on both lines was accepted as two approvals: ' + reasons(r));
  });

test('A3. approver === payee is refused -- self-directed money, the Moose shape',
  () => {
    const r = A.dualApprovalRefusals('Ray Dunn', 'Ed Marsh', 'ed marsh', 'payment');
    assert.ok(/approver is the payee/i.test(reasons(r)),
      'case-differing payee slipped past the comparison: ' + reasons(r));
  });

test('A4. an INACTIVE officer cannot prepare or approve -- FOE 213 also had an '
  + 'officer not on the application running bingo',
  () => {
    const p = A.dualApprovalRefusals('Gone Guy', 'Tom Byrne', 'Acme', 'payment');
    const q = A.dualApprovalRefusals('Ray Dunn', 'Gone Guy', 'Acme', 'payment');
    assert.ok(/not an active officer/i.test(reasons(p)), 'preparer: ' + reasons(p));
    assert.ok(/not an active officer/i.test(reasons(q)), 'approver: ' + reasons(q));
  });

test('A5. THE SILENT HALF: two different active officers and a third-party payee '
  + 'passes with NO refusals. A gate that refuses everything would pass A1-A4',
  () => {
    const r = A.dualApprovalRefusals('Ray Dunn', 'Ed Marsh', 'Acme Supply', 'payment');
    assert.strictEqual(r.length, 0, 'a correct payment was refused: ' + reasons(r));
  });

test('A6. ABLATION: with the same-person check removed from a COPY of the source, '
  + 'A2\'s case PASSES -- so A2 is testing that check and not something else',
  () => {
    const cut = SRC.replace(/if\(p && a && p===a\)\{[\s\S]*?\n  \}\n/,
      '\n');
    assert.notStrictEqual(cut, SRC,
      'THE ABLATION DID NOT APPLY -- the replace matched nothing, so this arm '
      + 'ran against the UNMODIFIED source and proves nothing. That is the '
      + 'silent-sabotage failure this platform measures with '
      + 'sabotage_control_check.py; fix the pattern, do not delete the arm.');
    const B = harness({ officers: OFFICERS, src: cut });
    const r = B.dualApprovalRefusals('Ray Dunn', 'Ray Dunn', 'Acme Supply', 'payment');
    assert.strictEqual(r.length, 0,
      'with the check ablated the same-officer case is STILL refused, so A2 was '
      + 'passing for some other reason: ' + reasons(r));
  });

// ── B. THE 2915.101 THRESHOLD, AND WHICH WAY THE OLD DEFAULT WAS WRONG ──────
section('B. the threshold correction, and the direction of the error it fixed');

test('B1. the two figures are what the law says: base ' + STAT_BASE
  + ', AG-adjusted ' + AG_ADJUSTED,
  () => {
    assert.strictEqual(STAT_BASE, 250000,
      'ORC 2915.101 prints "two hundred fifty thousand dollars"');
    assert.strictEqual(AG_ADJUSTED, 330000,
      'OAC 109:1-4-21, effective 2023-11-01, replaces it with "three hundred '
      + 'thirty thousand dollars"');
    assert.ok(AG_ADJUSTED > STAT_BASE,
      'the statute allows only a GREATER amount -- an adjustment below the base '
      + 'would mean one of these two numbers is wrong');
  });

test('B2. a device still holding the statutory base is flagged, with HOW FAR off',
  () => {
    assert.strictEqual(harness({ threshold: 250000 }).p4ThresholdStale(),
      AG_ADJUSTED - 250000);
  });

test('B3. the AG-adjusted amount is not stale, and neither is a HIGHER one -- a '
  + 'later adjustment this app has not been told about must not read as an error',
  () => {
    assert.strictEqual(harness({ threshold: AG_ADJUSTED }).p4ThresholdStale(), null);
    assert.strictEqual(harness({ threshold: 400000 }).p4ThresholdStale(), null);
  });

test('B4. an ABSENT or unusable threshold is null, not "stale" -- unconfigured '
  + 'and misconfigured are different facts and the flag text only fits one',
  () => {
    assert.strictEqual(harness({ threshold: 0 }).p4ThresholdStale(), null);
    assert.strictEqual(harness({ threshold: undefined }).p4ThresholdStale(), null);
    assert.strictEqual(harness({ threshold: 'abc' }).p4ThresholdStale(), null);
  });

test('B5. THE DIRECTION, ASSERTED RATHER THAN CLAIMED IN A COMMENT: on $300,000 '
  + 'the stale base demanded MORE than the law requires, not less',
  () => {
    const t = harness({});
    const atBase = t.tieredRequirement(300000, STAT_BASE);
    const atAG = t.tieredRequirement(300000, AG_ADJUSTED);
    assert.strictEqual(Math.round(atBase.required), 87500,
      '0.25*250000 + 0.50*50000');
    assert.strictEqual(Math.round(atAG.required), 75000,
      '0.25*300000, all of it inside tier 1');
    assert.ok(atBase.required > atAG.required,
      'THE WHOLE POINT OF THIS ARM: a lower threshold pushes money into the 50% '
      + 'tier, so the stale default over-stated the duty. It was conservative on '
      + 'the amount owed and wrong about the shortfall -- which is the harm, '
      + 'because a treasurer moves money to close a gap that is printed.');
  });

test('B6. ...and above the adjusted amount the two agree again, so B5 is about '
  + 'the BAND between them and not a blanket difference',
  () => {
    const t = harness({});
    const hi = 500000;
    assert.ok(t.tieredRequirement(hi, STAT_BASE).required
              > t.tieredRequirement(hi, AG_ADJUSTED).required,
      'still differs above the band, as it must -- tier1 is capped at the '
      + 'threshold, so a higher threshold always means a smaller tier 2');
    assert.strictEqual(t.tieredRequirement(200000, STAT_BASE).required,
                       t.tieredRequirement(200000, AG_ADJUSTED).required,
      'BELOW both thresholds the figures are identical: a post under $250,000 '
      + 'was never affected by the stale default, which bounds who this touches');
  });

// ── C. THE TRUSTEE AUDIT ────────────────────────────────────────────────────
section('C. the audit the finance officer may not prepare');
const GOOD = { quarter: '2026-Q3', date: '2026-09-27', by: 'Tom Byrne',
               bond: 50000, bondExpires: '2027-06-30',
               notes: 'reconciled both gaming accounts to the July statements' };
const C = harness({ officers: OFFICERS });
const withGood = (over) => Object.assign({}, GOOD, over || {});

test('C1. THE SILENT HALF FIRST: a trustee who is not the finance officer, with '
  + 'notes and a live bond, passes with no refusals',
  () => {
    const r = C.trusteeAuditRefusals(withGood());
    assert.strictEqual(r.length, 0, 'a correct audit was refused: ' + reasons(r));
  });

test('C2. the FINANCE OFFICER is refused, and the refusal says why rather than '
  + 'just saying no',
  () => {
    const r = C.trusteeAuditRefusals(withGood({ by: 'Ed Marsh' }));
    assert.ok(/must not prepare the audit of their own books/i.test(reasons(r)),
      reasons(r));
    assert.ok(/Quartermaster/.test(reasons(r)),
      'the refusal does not use the post\'s OWN title for the role, so a VFW '
      + 'quartermaster reads a message about somebody else: ' + reasons(r));
  });

test('C3. somebody with no audit role is refused -- an audit signed by a '
  + 'non-trustee is not an independent audit',
  () => {
    const r = C.trusteeAuditRefusals(withGood({ by: 'Ray Dunn' }));
    assert.ok(/not assigned the Trustee/i.test(reasons(r)), reasons(r));
  });

test('C4. a bond that EXPIRED BEFORE the audit date is refused',
  () => {
    const r = C.trusteeAuditRefusals(withGood({ bondExpires: '2026-01-01' }));
    assert.ok(/expired on 2026-01-01/.test(reasons(r)), reasons(r));
    assert.ok(/VOID the bond/i.test(reasons(r)),
      'the refusal does not say what the consequence is: ' + reasons(r));
  });

test('C5. an ABSENT bond is NOT a refusal -- refusing the whole record for a '
  + 'figure not to hand would push the audit out of the app entirely',
  () => {
    const r = C.trusteeAuditRefusals(withGood({ bond: 0, bondExpires: '' }));
    assert.strictEqual(r.length, 0,
      'a missing bond figure destroyed the audit record: ' + reasons(r));
  });

test('C6. an audit with NO notes is refused -- a record with no content is the '
  + 'shape American Legion Post 366 settled over',
  () => {
    const r = C.trusteeAuditRefusals(withGood({ notes: '' }));
    assert.ok(/actually counted and compared/i.test(reasons(r)), reasons(r));
  });

test('C7. a bond expiring AFTER the audit date is fine, so C4 is about the '
  + 'comparison and not about any bond date at all',
  () => {
    const r = C.trusteeAuditRefusals(withGood({ date: '2026-03-01',
                                                bondExpires: '2026-03-02' }));
    assert.strictEqual(r.length, 0, reasons(r));
  });

// ── D. WHAT THE FILE ITSELF NOW SAYS ────────────────────────────────────────
section('D. the app\'s own text, read with comments stripped');
const bare = stripComments(html);

test('D0. the stripper actually stripped something, so every arm below is not '
  + 'passing against the raw file',
  () => {
    assert.ok(bare.length < html.length,
      'stripComments returned the file unchanged -- these arms would then be '
      + 'satisfiable by a comment quoting the string they claim is gone');
  });

test('D1. the profit-chain panel NO LONGER tells a treasurer the distribution '
  + 'rules are not built',
  () => {
    assert.ok(!/Those rules are Phase 4 and are not built/.test(bare),
      'the stale sentence is still in the rendered copy');
    assert.ok(!/Disbursement\s+is Phase 4 and is not built/.test(bare),
      'the second stale sentence is still in the rendered copy');
  });

test('D2. and the corrected copy points at the panel that DOES exist',
  () => {
    assert.ok(/those rules ARE built/.test(bare),
      'the correction is not in the rendered copy, only in a comment');
  });

test('D3. the beer tile no longer says the purchase must be for cash, and names '
  + 'the rule that lists the permitted instruments',
  () => {
    assert.ok(!/the sale must be for cash/.test(bare),
      'the wrong advisory wording is still rendered');
    assert.ok(/4301-9-01/.test(bare),
      'the rule that actually lists cash/check/card/EFT is not cited anywhere');
  });

test('D4. sf_trustee_audits is NOT in SF_SYNCED -- the panel TELLS the user this '
  + 'record is device-only, and a claim about a limitation has to be true',
  () => {
    const m = bare.match(/var SF_SYNCED=\[([\s\S]*?)\];/);
    assert.ok(m, 'SF_SYNCED not found -- anchor moved');
    assert.ok(!/sf_trustee_audits/.test(m[1]),
      'it IS synced now. GOOD -- but the panel still says it is device-only, '
      + 'and that sentence and this arm must both be rewritten.');
    assert.ok(/held on this\s+device only/.test(bare),
      'the panel does not disclose the limitation this arm just confirmed');
  });

test('D5. the trustee capability carries a VFW title and is NOT invented for the '
  + 'other four orders',
  () => {
    assert.ok(/'trustee\.audit':'Trustee'/.test(bare),
      'the VFW title, the one the Manual of Procedure supports, is missing');
    const titleLines = bare.split('\n').filter((l) => /'trustee\.audit':'/.test(l));
    assert.strictEqual(titleLines.length, 1,
      'a trustee title exists for more than one org type. Only the VFW Manual of '
      + 'Procedure was read; the others must fall back to the capability label '
      + 'rather than carry a title that reads as researched. Found '
      + titleLines.length + '.');
  });

test('D6. online raffles are recorded as NOT LAW rather than built',
  () => {
    assert.ok(/NOT LAW/.test(bare),
      'the law-currency table does not state the online-raffle status');
    assert.ok(!/online raffle platform/i.test(bare.replace(/NOT LAW[\s\S]{0,900}/g, '')),
      'something outside the law-currency note refers to an online raffle '
      + 'platform, which would mean a flow was built against an unenacted bill');
  });

console.log('\n' + (fail ? 'FAIL' : 'ALL') + ' -- ' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
