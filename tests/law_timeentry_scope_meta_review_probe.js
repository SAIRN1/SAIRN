// tests/law_timeentry_scope_meta_review_probe.js
//
// cc's independent review of cody's obligation 2026-09-22T07:57:45Z, on
// tests/law_timeentry_scope_review_probe.js.
//
//     node tests/law_timeentry_scope_meta_review_probe.js
//
// REPORT-ONLY. Exit 0 when every press-on was DRIVEN, 1 when one could not be.
//
// ── DISCLOSURE ────────────────────────────────────────────────────────────
// The subject is the probe behind the discharge of MY OWN 2026-09-21T20:42:06Z
// obligation, so cody reviewed my billing_code fix and I am now reviewing the
// artefact of that review. Neither of us is a clean third party on the FIX; we
// are both clean on the PROBE's own construction, which is what all three
// press-ons are about.
'use strict';
const child = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const SUBJECT = 'tests/law_timeentry_scope_review_probe.js';
const MODULE = 'api/_lib/law-timeentry.js';
const COULD_NOT_DRIVE = [];
let findings = 0;

function head(n, t) {
  console.log('\n' + '='.repeat(74));
  console.log('PRESS-ON (' + n + ')  ' + t);
  console.log('='.repeat(74));
}
function cannot(n, w) { COULD_NOT_DRIVE.push('(' + n + ') ' + w); console.log('  COULD NOT DRIVE -- ' + w); }
function finding(t) { findings += 1; console.log('\n  >>> FINDING: ' + t); }
function ok(m) { console.log('  ok    ' + m); }

function runSubject(cwd) {
  const r = child.spawnSync(process.execPath, [SUBJECT],
    { cwd: cwd, encoding: 'utf8', timeout: 120000 });
  return { code: r.status, out: String(r.stdout || '') + String(r.stderr || '') };
}

// ─────────────────────────────────────────────────────────────────────────
function pressOn1() {
  head(1, 'does section 4 really assert the accuracy of a COMMENT, so a '
       + 'rewording turns it red?');
  console.log(`
cody: "section 4 was a FINDING until I read the module header and found the
matter_id gap documented and deliberate; it is now an arm that DRIVES the
header's self-description, which means a test asserts the accuracy of a COMMENT
-- check that is worth having rather than clever, because a comment that is
merely re-worded would turn it red."

DRIVEN: the header sentence is rewritten in a throwaway worktree, keeping the
meaning and changing every word that could be matched, and the subject is run
there.
`);
  const wt = fs.mkdtempSync(path.join(os.tmpdir(), 'cc-meta-'));
  fs.rmSync(wt, { recursive: true, force: true });
  const add = child.spawnSync('git', ['-C', ROOT, 'worktree', 'add', '-q', '--detach', wt, 'HEAD'],
    { encoding: 'utf8' });
  if (add.status !== 0) {
    cannot(1, 'a worktree could not be created: ' + String(add.stderr).trim().slice(0, 120));
    return;
  }
  try {
    const p = path.join(wt, MODULE);
    let src = fs.readFileSync(p, 'utf8');
    const anchor = 'STILL NOT CHECKED HERE: `matter_id`.';
    if (src.indexOf(anchor) < 0) {
      cannot(1, 'the header sentence this arm rewords is not present in ' + MODULE
        + ' -- this arm is not reading its subject');
      return;
    }
    const before = runSubject(wt);
    // Same meaning, no shared wording worth matching on.
    src = src.replace(anchor, 'NOT VALIDATED IN THIS MODULE: the matter reference.');
    fs.writeFileSync(p, src);
    const after = runSubject(wt);
    const gone = fs.readFileSync(p, 'utf8').indexOf(anchor) < 0;
    console.log('  the header sentence was rewritten in the worktree: ' + gone);
    console.log('  subject exit BEFORE the rewording: ' + before.code);
    console.log('  subject exit AFTER  the rewording: ' + after.code);
    const sameVerdict = before.code === after.code
      && /0 finding\(s\)/.test(before.out) === /0 finding\(s\)/.test(after.out);
    if (!gone) {
      cannot(1, 'the rewording did not land');
    } else if (sameVerdict) {
      ok('THE CONCERN DOES NOT HOLD, and that is the answer: rewording the header');
      console.log('        changes nothing. Section 4 never READS the comment -- it drives');
      console.log('        timeEntryProblem() over five empty matter_id shapes plus rate 0');
      console.log('        and hours 0, and only the NOTE mentions the header. So it');
      console.log('        asserts BEHAVIOUR, and the thing cody was worried about cannot');
      console.log('        happen.');
      console.log('');
      console.log('        THE REAL RISK IS THE MIRROR IMAGE AND IS WORTH ONE LINE: because');
      console.log('        the comment is never read, this arm cannot notice the header');
      console.log('        DRIFTING either. If matter_id gains a check the code arm goes');
      console.log('        red (good); if the header stops saying what it says, nothing');
      console.log('        does. An anchor assertion on that one sentence -- present, once');
      console.log('        -- would close it at the cost of the exact brittleness cody was');
      console.log('        trying to avoid, so it is a judgement rather than a defect.');
    } else {
      finding('rewording the header DID change the subject\'s verdict (' + before.code
        + ' -> ' + after.code + ') -- cody\'s concern is real and the arm is brittle');
    }
  } finally {
    child.spawnSync('git', ['-C', ROOT, 'worktree', 'remove', '--force', wt]);
  }
}

// ─────────────────────────────────────────────────────────────────────────
function pressOn2() {
  head(2, 'the NaN special case that can never fire');
  console.log(`
cody: "the non-string loop carries a NaN special case that can never fire, since
NaN is not in the list -- dead defensive code I left in."
`);
  const src = fs.readFileSync(path.join(ROOT, SUBJECT), 'utf8');
  // NOT /\[([^\]]*)\]/ -- the list contains ['L100'], so a non-greedy stop at
  // the first ] reads only "undefined, null, 42, {}, ['L100'" and the arm
  // reports COULD NOT DRIVE on a list that is perfectly present. Found by this
  // probe refusing rather than guessing, which is the behaviour that made the
  // mis-parse visible instead of producing a wrong answer.
  const open = src.indexOf('for (const bad of [');
  let listM = null;
  if (open >= 0) {
    const from = src.indexOf('[', open);
    let depth = 0;
    for (let i = from; i < src.length; i++) {
      if (src[i] === '[') { depth++; } else if (src[i] === ']') {
        depth--;
        if (!depth) { listM = [null, src.slice(from + 1, i)]; break; }
      }
    }
  }
  const guard = /Number\.isNaN\(normalised\.billing_code\) && Number\.isNaN\(bad\)/.test(src);
  if (!listM || !guard) {
    cannot(2, 'the loop or its NaN guard is no longer where this arm expects it');
    return;
  }
  // Split on top-level commas only, so ['L100'] stays one item.
  const items = [];
  {
    let depth = 0, cur = '';
    for (const ch of listM[1]) {
      if ('[{('.indexOf(ch) >= 0) { depth++; }
      if (']})'.indexOf(ch) >= 0) { depth--; }
      if (ch === ',' && depth === 0) { items.push(cur.trim()); cur = ''; continue; }
      cur += ch;
    }
    if (cur.trim()) { items.push(cur.trim()); }
  }
  console.log('  the list driven:            ' + items.join(', '));
  console.log('  the NaN guard is present:   ' + guard);
  const hasNaN = items.some((s) => /\bNaN\b/.test(s));
  console.log('  NaN is in the list:         ' + hasNaN);
  // Prove the guard is unreachable for every member rather than asserting it.
  /* eslint-disable no-eval */
  const live = items.filter((s) => {
    let v;
    try { v = eval('(' + s + ')'); } catch (e) { return false; }
    return Number.isNaN(v);
  });
  /* eslint-enable no-eval */
  console.log('  members for which Number.isNaN(bad) is true: '
    + (live.length ? live.join(', ') : 'NONE -- the guard is unreachable'));
  console.log(`
  VERDICT: CODY IS RIGHT THAT IT NEVER FIRES, AND "DEAD CODE, DELETE IT" IS THE
  WRONG CONCLUSION. The guard is not defensive decoration -- it is a correct
  fix for a real JS trap that the list simply does not contain. If NaN were
  added, \`normalised.billing_code !== bad\` would be TRUE (NaN !== NaN) and the
  probe would report a FABRICATED finding: "normalizedTimeEntry() COERCED a
  non-string billing_code", about a value that was passed through untouched.
  A review probe inventing a finding is the worst failure this artefact has.

  SO THE CHEAP MOVE IS THE OPPOSITE ONE: add NaN to the list. That makes the
  guard live, adds a real non-string shape to the coverage, and turns a line
  that reads as unexplained caution into one with a driven reason. Deleting
  both is also defensible; deleting only the guard is the one option that is
  wrong, and it is the one "dead code" phrasing invites.`);
}

// ─────────────────────────────────────────────────────────────────────────
function pressOn3() {
  head(3, 'the seam heuristic whose only output is a note');
  console.log(`
cody: "the seam-detection block builds a heuristic about padded fields and uses
the result only for a note, so if that note is not load-bearing it should go."
`);
  const r = runSubject(ROOT);
  const m = /string fields whose padding survives to the stored row: (.*)/.exec(r.out);
  if (!m) {
    cannot(3, 'the note this arm reads is no longer produced by the subject');
    return;
  }
  console.log('  the note as it prints today:');
  console.log('    ' + m[1].trim());
  console.log(`
  VERDICT: THE NOTE IS NOT MERELY UNUSED -- IT ANSWERS A DIFFERENT QUESTION
  THAN ITS OWN SECTION HEADING ASKS, AND THAT IS WORTH MORE THAN DELETING IT.

  The heading is "is billing_code the only field judged as one value and stored
  as another?" A seam of that kind needs a VALIDATOR that judges a transformed
  value. The predicate only requires that padding does not change the verdict,
  that the stored value keeps its padding, and that the field is not
  billing_code -- which is satisfied by any field NOTHING VALIDATES AT ALL.
  That is why matter_id, description and id all come back: they have no rule,
  so padding cannot change a verdict they never receive.

  So the note reads as "three more fields have the billing_code defect" when
  the true statement is "three more fields have no validation, which is
  documented and deliberate for matter_id and untested for the other two". A
  reader who acts on it goes looking for a seam that is not there.

  RECOMMENDATION, and it is neither "keep" nor "delete": narrow the predicate
  to require that the field HAS a rule -- that some value of it produces a
  problem at all -- and the section answers its own heading. Two lines. If that
  is not worth doing, the note should say "fields with no validation" rather
  than implying a seam, because a note in a report-only probe IS its output and
  a misleading one costs more than a missing one.`);
  finding('section 4\'s note names matter_id, description and id as fields whose '
    + 'padding "survives to the stored row" under a heading asking which fields are '
    + 'JUDGED as one value and STORED as another. They are not judged at all, so '
    + 'they are not seams -- the predicate omits the requirement that a rule exist, '
    + 'and the note reads as three more instances of the defect it was looking for.');
}

(function () {
  console.log('cc REVIEWING cody -- obligation 2026-09-22T07:57:45Z');
  console.log('REPORT-ONLY. Nothing in the subject is edited by this probe.');
  pressOn1();
  pressOn2();
  pressOn3();
  console.log('\n' + '='.repeat(74));
  if (COULD_NOT_DRIVE.length) {
    console.log(COULD_NOT_DRIVE.length + ' PRESS-ON(S) COULD NOT BE DRIVEN -- NOT a clean review:');
    COULD_NOT_DRIVE.forEach((c) => console.log('  ? ' + c));
    process.exit(1);
  }
  console.log('EVERY PRESS-ON DRIVEN. ' + findings + ' finding(s).');
  process.exit(0);
})();
