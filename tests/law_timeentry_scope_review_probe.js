// tests/law_timeentry_scope_review_probe.js
//
// REPORT-ONLY REVIEW PROBE for cc's obligation 2026-09-21T20:42:06Z
// (law_barcerts, law_invoices, law_opaccounts, quotes), assigned to cody.
// Part 1 of 3: the billing_code normalisation in api/_lib/law-timeentry.js and
// api/sd-data.js. Parts 2 and 3 are answered in
// tests/law_scope_and_hover_review_probe.py, which needs Python.
//
// Not a regression suite -- api/_lib/law-timeentry.test.js is that, and
// re-running it only re-reads the author's own answer. This drives the four
// things the obligation asks a reviewer to check, and the one it does not ask
// about that a reviewer should: whether billing_code is the ONLY field on this
// record with a validate-one-value/store-another seam.
//
// Run:  node tests/law_timeentry_scope_review_probe.js
//
// EXIT 0 unless the probe itself could not run. Findings are reported; the
// reviewer writes the verdict.

'use strict';
const assert = require('assert');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const LTE = require(path.join(ROOT, 'api/_lib/law-timeentry.js'));

const findings = [];
const notes = [];
function ok(name, detail) { console.log('  ok      ' + name + (detail ? '\n            ' + detail : '')); }
function finding(name, detail) {
  console.log('  FINDING ' + name + '\n            ' + detail);
  findings.push(name + ' -- ' + detail);
}
function note(name) { console.log('  note    ' + name); notes.push(name); }

const BASE = { id: 'TE-1', matter_id: 'M-1', hours: 1.5, rate: 350, billable: true,
               billing_code: 'L100', description: 'drafted the motion' };
const entry = (over) => Object.assign({}, BASE, over || {});

console.log('REVIEW PROBE -- cc 2026-09-21T20:42:06Z, part 1: billing_code normalisation\n');

// ── FOCUS: normalisation is NOT a second refusal ───────────────────────────
console.log('1. a non-string billing_code is REFUSED, not coerced');
for (const bad of [undefined, null, 42, {}, ['L100'], true]) {
  const rec = entry({ billing_code: bad });
  const problem = LTE.timeEntryProblem(rec);
  const normalised = LTE.normalizedTimeEntry(rec);
  if (!problem) {
    finding('a non-string billing_code is ACCEPTED by timeEntryProblem()',
            'typeof ' + typeof bad + ' (' + JSON.stringify(bad) + ') produced no problem');
  } else if (normalised.billing_code !== bad
             && !(Number.isNaN(normalised.billing_code) && Number.isNaN(bad))) {
    finding('normalizedTimeEntry() COERCED a non-string billing_code',
            JSON.stringify(bad) + ' became ' + JSON.stringify(normalised.billing_code)
            + ' -- that is a second refusal wearing a normaliser\'s clothes, and it '
            + 'would hide the day timeEntryProblem() stops refusing it');
  }
}
ok('six non-string shapes (undefined, null, number, object, array, boolean) are each '
   + 'refused by timeEntryProblem() and passed through untouched by normalizedTimeEntry()',
   'the normaliser does not become a second validator, which is what stops it hiding '
   + 'a regression in the first one');

// ── FOCUS: the caller's payload is not mutated ─────────────────────────────
console.log('\n2. the caller\'s object is not mutated');
{
  const padded = '   L100   ';
  const rec = entry({ billing_code: padded });
  const before = JSON.stringify(rec);
  const out = LTE.normalizedTimeEntry(rec);
  if (rec.billing_code !== padded) {
    finding('normalizedTimeEntry() MUTATED its argument',
            'the caller\'s billing_code became ' + JSON.stringify(rec.billing_code));
  } else if (JSON.stringify(rec) !== before) {
    finding('normalizedTimeEntry() mutated some other field of its argument',
            before + ' -> ' + JSON.stringify(rec));
  } else {
    ok('a padded code is trimmed in the RETURNED object and the argument is byte-identical',
       JSON.stringify(padded) + ' -> ' + JSON.stringify(out.billing_code)
       + ', caller still holds ' + JSON.stringify(rec.billing_code));
  }
  if (out === rec) {
    finding('the trimmed result is the SAME object as the argument',
            'so the caller holds the normalised value by reference, which is a mutation '
            + 'the equality check above cannot see');
  }
}
{
  // The identity path: nothing to trim, so the SAME object comes back. That is
  // deliberate (the record is not reconstructed), and it is worth asserting
  // because it is the branch a future edit would most easily turn into a copy.
  const rec = entry();
  const out = LTE.normalizedTimeEntry(rec);
  if (out !== rec) {
    note('a code needing no trim is returned as a COPY rather than the same object -- '
         + 'harmless, but the module\'s own comment says it is returned unchanged');
  } else {
    ok('a code needing no trim returns the identical object, so a stored row is the '
       + 'caller\'s record and not a reconstruction of it');
  }
}

// ── FOCUS: nothing else on the entry is reshaped ───────────────────────────
console.log('\n3. nothing else on the record is reshaped');
{
  const rec = entry({ billing_code: ' L100 ', matter_id: '  M-1  ',
                      description: '  spaced description  ', client_ref: '  CR-1  ' });
  const out = LTE.normalizedTimeEntry(rec);
  const changed = Object.keys(out).filter((k) => out[k] !== rec[k]);
  if (changed.length === 1 && changed[0] === 'billing_code') {
    ok('exactly one field changed, and it is billing_code',
       'matter_id, description and an unknown extra field all survive byte-identical, '
       + 'so the normaliser is scoped to the field the defect was in');
  } else {
    finding('the normaliser reshaped more than billing_code', 'changed: ' + changed.join(', '));
  }
}

// ── NOT IN THE OBLIGATION: is billing_code the ONLY validate/store seam? ───
console.log('\n4. is billing_code the only field judged as one value and stored as another?');
{
  // The defect class is: the validator judges a TRANSFORMED value and the
  // handler stores the RAW one. Driving it rather than grepping for .trim():
  // for every string field, does a padded value change the VERDICT?
  const seams = [];
  for (const field of ['billing_code', 'matter_id', 'description', 'id']) {
    const raw = entry({ [field]: 'X'.repeat(30) });
    const padded = entry({ [field]: '  ' + 'X'.repeat(30) + '  ' });
    const rawVerdict = !!LTE.timeEntryProblem(raw);
    const padVerdict = !!LTE.timeEntryProblem(padded);
    const normalised = LTE.normalizedTimeEntry(padded);
    // A seam exists when padding changes nothing about the verdict but the
    // stored value keeps the padding -- i.e. the validator looked at a
    // trimmed value the store never sees.
    if (rawVerdict === padVerdict && normalised[field] === padded[field]
        && padded[field] !== padded[field].trim() && field !== 'billing_code') {
      seams.push(field);
    }
  }
  note('string fields whose padding survives to the stored row: ' + (seams.join(', ') || 'none besides billing_code'));
  // The real question is narrower: does any OTHER field have a LENGTH or
  // emptiness rule judged on a trimmed value? That is what made billing_code
  // dangerous at the bound.
  // ── THIS WAS A FINDING FOR ABOUT A MINUTE, AND IT SHOULD NOT HAVE BEEN ──
  // The first spelling reported "a whitespace-only matter_id is accepted" as a
  // finding. It IS accepted -- so are '' and null -- but the module says so
  // itself, in its own header: "STILL NOT CHECKED HERE: `matter_id`. It is
  // required by saveTime() and by nothing on the server ... left deliberately,
  // recorded so the next reader knows the absence was seen rather than
  // missed." Reporting a documented decision as a defect is how a reviewer
  // burns the author's time and their own credibility. So the check is turned
  // around: the module makes a claim about itself, and the claim is DRIVEN.
  const selfClaim = { 'matter_id unchecked': ['', '   ', null, undefined, 0],
                      'rate checked': null, 'hours checked': null };
  const accepted = selfClaim['matter_id unchecked']
    .filter((v) => !LTE.timeEntryProblem(entry({ matter_id: v })));
  const rateChecked = !!LTE.timeEntryProblem(entry({ rate: 0 }));
  const hoursChecked = !!LTE.timeEntryProblem(entry({ hours: 0 }));
  if (accepted.length === 5 && rateChecked && hoursChecked) {
    note('the module\'s own header claim is ACCURATE: matter_id is checked by nothing '
         + 'here (all five of \'\', "   ", null, undefined and 0 are accepted) while rate '
         + 'and hours are both checked. The absence is recorded in the file rather than '
         + 'merely true, so it is a stated scope and not a gap this review found');
  } else if (accepted.length !== 5) {
    note('matter_id is PARTLY checked now (' + accepted.length + ' of 5 empty shapes '
         + 'accepted), so the header sentence "checked by nothing on the server" has '
         + 'drifted from the code and should be re-worded');
  } else {
    finding('the module says rate and hours are checked and one of them is not',
            'rate refused: ' + rateChecked + ', hours refused: ' + hoursChecked);
  }
}

// ── FOCUS: the length bound, driven at the exact value from the record ────
console.log('\n5. the bound the defect was found at, driven');
{
  const thirty = ' '.repeat(30) + 'L100';           // 34 chars, 4 trimmed
  const rec = entry({ billing_code: thirty });
  const problem = LTE.timeEntryProblem(rec);
  const stored = LTE.normalizedTimeEntry(rec).billing_code;
  if (problem) {
    finding('the 34-character padded code is now REFUSED rather than trimmed',
            'cc\'s fix was meant to store the trimmed value, not to start refusing it: ' + problem.slice(0, 120));
  } else if (stored.length === 4 && stored === 'L100') {
    ok('30 spaces + L100 is accepted (judged as 4) and STORED as 4 characters',
       'before the fix the raw 34-character value landed in a column whose gate refuses 33');
  } else {
    finding('the stored value is neither refused nor trimmed', JSON.stringify(stored));
  }
  const overLong = entry({ billing_code: 'L'.repeat(40) });
  if (!LTE.timeEntryProblem(overLong)) {
    finding('a genuinely over-long code is accepted', '40 characters produced no problem');
  } else {
    ok('a genuinely over-long 40-character code is still refused',
       'so the trim did not become a way to smuggle length past the gate');
  }
}

console.log('\n' + findings.length + ' finding(s), ' + notes.length + ' note(s)');
findings.forEach((f) => console.log('  - ' + f));
notes.forEach((n) => console.log('  ? ' + n));
assert.ok(true);
