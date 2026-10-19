// api/b19-iolta-reconcile-carveout.test.js
//
// Run:  node api/b19-iolta-reconcile-carveout.test.js
//
// C1's IOLTA RECONCILIATION CARVE-OUT, at the module level.
//
// ── WHAT THIS FILE IS, STATED PLAINLY BECAUSE IT IS LESS THAN USUAL ───────
// b19 was STOPPED MID-BATCH on instruction. These arms are the assertions
// that were DRIVEN against the real module before the carve-out was committed
// -- they are not a suite designed for this feature, they are the verification
// PERSISTED so it is re-runnable instead of being a line of terminal output
// nobody can repeat. There is NO handler arm, NO ablation and NO negative
// control beyond the ones below, and the b19 handoff says so.
//
// ── THE ONE DEFECT THESE ARMS ALREADY CAUGHT, WHICH IS WHY THEY EXIST ─────
// The first draft of the carve-out let a NAMED verb through anywhere the role
// held `rw`: `decide('law_invoices', 'bookkeeper', 'reconcile')` returned
// ALLOW, because law_invoices is not locked, `reconcile` was treated as
// WRITE-class like any unknown verb, and bookkeeper holds `rw` on invoices.
// So a verb meaning "perform leg (a) or (b) of a trust reconciliation" was
// granted on a resource with no legs. `prepare` had the identical hole since
// b18 and nobody had asked. FOUND BY DRIVING IT, not by reading it -- arms
// N1-N4 are that finding.
//
// Exit: 0 all arms passed · 1 an arm FAILED

'use strict';

const lawRoles = require('./_lib/law-roles');

const A = lawRoles.ALLOW;
const D = lawRoles.DENY;
const RECONCILE = lawRoles.LAW_RECONCILE_ACTION;
const PREPARE = lawRoles.LAW_PREPARE_ACTION;

let pass = 0, fail = 0;
const failed = [];
function is(cond, label, detail) {
  if (cond) { pass++; console.log('  ok    ' + label); return; }
  fail++; failed.push(label.split('.')[0]);
  console.log('  FAIL  ' + label);
  if (detail) console.log('        ' + String(detail).slice(0, 400));
}
function verdict(label, resource, role, action, want) {
  const got = lawRoles.decide(resource, role, action);
  is(got === want, label + ' -> ' + want, 'got ' + got);
}
function section(t) { console.log('\n' + t); }

console.log('b19 -- C1\'s IOLTA reconciliation carve-out (module level only)\n');

// ── R. THE CARVE-OUT ITSELF ────────────────────────────────────────────────
section('R. the two reconciliation legs go to the LEGAL SIDE and not to '
      + 'bookkeeper');

verdict('R1a. owner reconciles the ledger leg', 'law_trusttx', 'owner', RECONCILE, A);
verdict('R1b. attorney reconciles the ledger leg', 'law_trusttx', 'attorney', RECONCILE, A);
verdict('R1c. paralegal reconciles the ledger leg', 'law_trusttx', 'paralegal', RECONCILE, A);
verdict('R1d. owner reconciles the bank leg', 'law_bankstatements', 'owner', RECONCILE, A);
verdict('R1e. attorney reconciles the bank leg', 'law_bankstatements', 'attorney', RECONCILE, A);
verdict('R1f. paralegal reconciles the bank leg', 'law_bankstatements', 'paralegal', RECONCILE, A);

// THE DELIVERABLE IS AN ABSENCE, so it is asserted as one.
verdict('B1. BOOKKEEPER cannot reconcile the ledger leg -- the carve-out',
        'law_trusttx', 'bookkeeper', RECONCILE, D);
verdict('B2. BOOKKEEPER cannot reconcile the bank leg -- the carve-out',
        'law_bankstatements', 'bookkeeper', RECONCILE, D);

// ── R2. THE RELATIONSHIP TO THE LICENSURE TIER, ASSERTED NOT COMPUTED ─────
// LAW_RECONCILE_ROLES is written out rather than derived from
// LAW_BAR_ADMITTED_ROLES, so the difference is visible on the screen. This arm
// is what stops that choice from becoming a silent divergence: the reconcile
// set must be the tier PLUS EXACTLY `paralegal`. Same shape as
// api/sd-data-sv-role-matrix.test.js arm A5b.
section('R2. the reconcile set is the bar-admitted tier plus EXACTLY one '
      + 'named role');
{
  const tier = Object.keys(lawRoles.LAW_BAR_ADMITTED_ROLES).sort();
  const rec = Object.keys(lawRoles.LAW_RECONCILE_ROLES).sort();
  const extra = rec.filter((r) => tier.indexOf(r) === -1);
  const missing = tier.filter((r) => rec.indexOf(r) === -1);
  is(missing.length === 0 && extra.length === 1 && extra[0] === 'paralegal',
     'R2. LAW_RECONCILE_ROLES === LAW_BAR_ADMITTED_ROLES + { paralegal }, so a '
   + 'divergence has to be declared HERE rather than appearing',
     JSON.stringify({ tier: tier, reconcile: rec, extra: extra, missing: missing }));
  is(Object.isFrozen(lawRoles.LAW_RECONCILE_ROLES)
     && Object.getPrototypeOf(lawRoles.LAW_RECONCILE_ROLES) === null,
     'R2b. ...and it is FROZEN with a NULL PROTOTYPE, so `constructor` is not a '
   + 'truthy reconciler and no caller can add one at runtime',
     'frozen=' + Object.isFrozen(lawRoles.LAW_RECONCILE_ROLES));
}

// ── R3. THE LEGS ARE EXACTLY THE TRUST LOCK'S MEMBERS ────────────────────
section('R3. the legs are exactly the two locked resources');
{
  const legs = Object.keys(lawRoles.LAW_RECONCILE_LEGS).sort();
  const locked = Object.keys(lawRoles.LAW_TRUST_LOCKED).sort();
  is(legs.length === locked.length && legs.every((r, i) => r === locked[i]),
     'R3. LAW_RECONCILE_LEGS is the SAME SET as LAW_TRUST_LOCKED -- a third '
   + 'leg appearing in one and not the other is the drift this catches',
     JSON.stringify({ legs: legs, locked: locked }));
  is(legs.length === 2,
     'R3b. ...and there are TWO, not three. The third leg of a three-way '
   + 'reconciliation (the sum of the client sub-ledgers) is DERIVED from '
   + 'law_trusttx and is not a resource, which is why this list is short',
     JSON.stringify(legs));
}

// ── ARM B IS STILL ARM B. The thing that must not have been broken. ───────
section('L. b17\'s ARM B is intact -- a plain read is still refused');
verdict('L1. paralegal READ law_trusttx', 'law_trusttx', 'paralegal', 'read', D);
verdict('L2. paralegal WRITE law_trusttx', 'law_trusttx', 'paralegal', 'write', D);
verdict('L3. paralegal READ law_bankstatements', 'law_bankstatements', 'paralegal', 'read', D);
verdict('L4. bookkeeper READ law_trusttx', 'law_trusttx', 'bookkeeper', 'read', D);
verdict('L5. C2\'s prepare is untouched', 'law_trusttx', 'paralegal', PREPARE, A);
verdict('L6. and prepare is still NOT available on the bank leg',
        'law_bankstatements', 'paralegal', PREPARE, D);

// ── N. A NAMED VERB MEANS ONE THING. The defect these arms found. ─────────
section('N. a NAMED verb is refused off the resources that define it -- the '
      + 'hole the first draft had');
verdict('N1. bookkeeper reconcile law_invoices (holds rw there)',
        'law_invoices', 'bookkeeper', RECONCILE, D);
verdict('N2. bookkeeper prepare law_invoices (holds rw there)',
        'law_invoices', 'bookkeeper', PREPARE, D);
verdict('N3. OWNER reconcile law_invoices -- it binds the owner too',
        'law_invoices', 'owner', RECONCILE, D);
verdict('N4. owner prepare law_matters', 'law_matters', 'owner', PREPARE, D);

// THE SILENT HALF OF THE PAIR. Without these, a guard that refused every verb
// everywhere would have passed N1-N4 and broken the app.
section('N5. CLEAN -- the narrowing did not catch anything else');
verdict('N5a. an UNKNOWN verb is STILL write-class where the role has rw',
        'law_invoices', 'owner', 'soft_delete', A);
verdict('N5b. ...and still refused where it does not',
        'law_barcerts', 'paralegal', 'soft_delete', D);
verdict('N5c. an ordinary read is unaffected', 'law_invoices', 'bookkeeper', 'read', A);
verdict('N5d. an ordinary write is unaffected', 'law_optx', 'bookkeeper', 'write', A);
verdict('N5e. a non-law resource is still NOT_LAW', 'slabs', 'owner', 'read',
        lawRoles.NOT_LAW);

// ── M. THE REFUSAL MESSAGE SAYS WHOSE WORK IT IS ─────────────────────────
section('M. the bookkeeper refusal names the reason, not the generic sentence');
{
  const bk = lawRoles.denyMessage('law_trusttx', 'bookkeeper', 'read');
  const pg = lawRoles.denyMessage('law_trusttx', 'paralegal', 'write');
  is(/not part of the bookkeeping role/.test(bk)
     && /operating account is yours/.test(bk)
     && !/Your role \(/.test(bk),
     'M1. a bookkeeper refused a trust leg is told the work is the legal '
   + 'staff\'s and that the operating account is theirs -- not "available to '
   + 'the owner and attorneys only", which is true and useless to them',
     bk);
  is(/PREPARE/.test(pg) && !/bookkeeping role/.test(pg),
     'M2. and the paralegal write refusal still offers C2\'s prepare route -- '
   + 'the new branch did not swallow it',
     pg);
}

// ── A. THE ATTESTATION GAP IS A STRUCTURE, NOT A SENTENCE ────────────────
section('A. the half this does NOT build is carried in the code');
{
  const att = lawRoles.LAW_RECONCILE_ATTESTATION;
  is(att && att.required_by_rule === true && att.implemented === false,
     'A1. LAW_RECONCILE_ATTESTATION says the lawyer review IS required by the '
   + 'rule and is NOT implemented here. Two booleans, so "we know and have not '
   + 'built it" cannot decay into "it is fine"',
     JSON.stringify({ required: att && att.required_by_rule,
                      implemented: att && att.implemented }));
  is(att && typeof att.gap === 'string' && att.gap.length > 80
     && /never/.test(att.gap),
     'A2. ...and it states what the app must NOT present as attested',
     att && att.gap);
  is(Object.isFrozen(att), 'A3. and it is frozen', 'frozen=' + Object.isFrozen(att));
}

console.log('\n  ' + pass + ' passed, ' + fail + ' failed');
if (failed.length) console.log('  FAILED: ' + failed.join(', '));
process.exit(fail ? 1 : 0);
