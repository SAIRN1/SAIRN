// api/sd-data-sf-session-gate.test.js
// Run: node api/sd-data-sf-session-gate.test.js
//
// SOME SAIRNfreedom RESOURCES REQUIRE AN EMPLOYEE SESSION, and the count is
// deliberately not written here -- it has changed four times and the list in
// APPROVED below is the only place it should live. Three were armed 2026-09-21
// (sf_accounts, sf_ledger, sf_vendor_prices); eight more on 2026-09-22 after
// hover2 audited all 35 and Michael made the call; sf_members, sf_donor_awards
// and sf_donor_tiers later the same day; sf_signatures on 2026-09-24, closing
// the pair the 2026-09-22 finding named.
//
// ── WHAT THE EIGHT CARRY, because a gate with no recorded reason is the next
//    session's mystery and this suite is where a reader will look ───────────
//   sf_operators            name + DOB + a FELONY flag and a GAMBLING
//                           disqualification flag -- a criminal-history
//                           assertion about a named volunteer, and the single
//                           most sensitive field the audit found
//   sf_gaming_expenses      payee name + amount, ORC 2915.10(A)(2) and (C)
//   sf_disbursements        the giving side of the same statute
//   sf_donations            donor name + amount
//   sf_youth_participants   MINORS
//   sf_staff                DOB, which the app age-gates off
//   sf_waivers              health and military-status disclosure
//   sf_service_appointments a member tied to a VA-adjacent referral outcome
//
// ── THIS SUITE ASSERTS THE TWO LISTS AGREE, NOT WHAT EITHER CONTAINS ───────
// SD_SESSION_GATED says a resource needs a session. A SECOND map says which
// APP's session counts. The file's own comment records what happens when they
// disagree: expectedApp resolves to 'stonedesk' by default and every correctly
// signed-in caller is refused with FORBIDDEN "sign in first" -- it fails CLOSED
// and CONFUSINGLY, which is the hardest failure to read and the one that gets
// a security change reverted as "broken" rather than fixed.
//
// So the load-bearing assertion here is set equality between the two maps.
// Asserting a hardcoded list of eleven names instead would go stale the next
// time anyone gates a twelfth, and would pass while the second map was
// forgotten -- which is the actual defect.
//
// ── WHAT THIS SUITE CANNOT TELL YOU, said here rather than left to be assumed
// It reads SOURCE. It does not prove a live call is refused.
//
// THE PARAGRAPH THAT STOOD HERE WENT STALE AND NOTHING SAID SO. It read: "As of
// 2026-09-22 sql/sairnfreedom_employee_auth_schema.sql has NOT been run against
// the live database -- /api/sf-auth login answers 503 NOT_PROVISIONED -- so NO
// real caller can hold a session ... it is IMPOSSIBLE until that file is run."
//
// RE-DRIVEN 2026-09-29: /api/sf-auth login on SF-PINNACLE-2026 answers
// 401 INVALID_CREDENTIALS, not 503 NOT_PROVISIONED. The auth table exists. A
// real session IS now possible, so the half that could not be driven can be --
// and, more to the point, adding a gate here no longer locks every caller out,
// which is the question that paragraph was really answering for whoever read it
// next. That is exactly what it was relied on for in this change.
//
// The claim is left as a DATED MEASUREMENT rather than deleted, because the
// answer matters to the next person who adds a gate. Re-drive it; do not trust
// this line either.

'use strict';
const assert = require('assert');
const fs = require('fs');
const path = require('path');

let passed = 0;
function test(name, fn) {
  try { fn(); passed++; console.log('  ok - ' + name); }
  catch (e) { console.error('  FAIL - ' + name + '\n    ' + e.message); process.exitCode = 1; }
}

const SRC_PATH = path.join(__dirname, 'sd-data.js');
let SRC;
try {
  SRC = fs.readFileSync(SRC_PATH, 'utf8').replace(/\r\n/g, '\n');
} catch (e) {
  // FAIL CLOSED. PR 1.11 -- a check that cannot read its subject did not run,
  // and "did not run" is a third state that is never folded into "passed".
  console.error('COULD NOT RUN: ' + SRC_PATH + ' is unreadable (' + e.code + ').');
  console.error('  Nothing below was checked. This is NOT a pass.');
  process.exit(2);
}
// Comment lines blanked before any scan: the block above this change quotes
// both lists to explain them, and a raw file-wide match counts that prose as
// code. Same trap api/alf-append-only-fail-closed.test.js already records.
const CODE = SRC.split('\n')
  .map((l) => (/^\s*(\/\/|\*|\/\*)/.test(l) ? '' : l)).join('\n');

const EIGHT_ADDED = [
  'sf_disbursements', 'sf_donations', 'sf_gaming_expenses', 'sf_operators',
  'sf_service_appointments', 'sf_staff', 'sf_waivers', 'sf_youth_participants',
];
const THREE_PRIOR = ['sf_accounts', 'sf_ledger', 'sf_vendor_prices'];

// ── THE APPROVED SET, AS A SET ──────────────────────────────────────────────
// Every sf_ resource Michael has approved a session gate for, across all four
// batches. This is asserted as SET EQUALITY, which is the arm that used to be
// written as "sf_signatures must be absent".
//
// WHY IT CHANGED SHAPE RATHER THAN JUST LOSING A NAME (2026-09-24): that arm
// existed to catch a gate quietly widening to all 35. It did that by naming
// the ONE resource left out. Closing sf_signatures emptied the list, and an
// arm that iterates an empty list passes over no data -- the vacuous-green
// shape this same suite already guards against in its first test. Set equality
// has no such degenerate case: it fails on a resource added without approval
// AND on a resource that quietly loses its gate, which the old arm could only
// catch for three hardcoded names.
const APPROVED = [
  // 2026-09-21
  'sf_accounts', 'sf_ledger', 'sf_vendor_prices',
  // 2026-09-22, the eight hover2 audited and Michael approved
  'sf_disbursements', 'sf_donations', 'sf_gaming_expenses', 'sf_operators',
  'sf_service_appointments', 'sf_staff', 'sf_waivers', 'sf_youth_participants',
  // 2026-09-22, the three the batch above named and left
  'sf_members', 'sf_donor_awards', 'sf_donor_tiers',
  // 2026-09-24, the other half of the pair the 2026-09-22 finding named:
  // {docId, docTitle, version, hash, signer, typed, signed} -- a named person,
  // their typed signature, and the governance document it binds them to.
  'sf_signatures',
  // 2026-09-29, TWO -- and the first of them was RED ON MAIN before this edit.
  //
  // `sf_trustee_audits` was gated on arrival (hank) and appeared in NEITHER
  // this list NOR the expectedApp map, so this suite was failing on main on two
  // arms at once. That is the shape this file exists to catch, caught.
  //
  // `sf_vehicle_service` is the one with an ungated period to close:
  // docs/CRITICALITY-TIERS.md re-tiered it B -> A on INTEGRITY on 2026-09-23 --
  // it is the ONLY thing that advances the odometer `sf_vehicles` computes its
  // service-due flag from -- and it stayed out of SD_SESSION_GATED for six
  // days. DRIVEN LIVE BEFORE THE GATE rather than inferred from the absence:
  //     read sf_vehicle_service, SF-PINNACLE-2026, NO session -> 200
  //     read sf_trustee_audits,  SF-PINNACLE-2026, NO session -> 403
  // The licence key is shipped to the browser.
  'sf_trustee_audits',
  'sf_vehicle_service',
  // 2026-10-11, ONE, and it is the first on this list whose gate closes an
  // INTEGRITY hole rather than a disclosure one.
  //
  // `sf_officers` is the post's governance record -- who holds which office --
  // and docs/CRITICALITY-TIERS.md:365 has tiered it **A on integrity, B on
  // confidentiality** since 2026-09-23, eighteen days before this gate. Read
  // is the weaker half by that register's own words ("published by design in
  // an organisation of this kind"); it is gated anyway for the reason
  // sf_vehicle_service records above, and because gatedSet() below parses the
  // `['read', 'write']` shape, so a write-only entry would be invisible to
  // this suite rather than checked by it.
  //
  // WHY THE WRITE MATTERS, which is the half this closes: THREE guards over
  // that roster are client-side only --
  //   sairnfreedom.html:2849       activeProvisioners()
  //   sairnfreedom.html:2860-2869  SPEC 1c, refuses deactivating the LAST
  //                                active provisioner
  //   sairnfreedom.html:2878-2885  refuses a second sole-holder
  // -- and the generic SF_RESOURCES write branch stores `data: payload`
  // verbatim with no role check, so a licence key alone (shipped to the
  // browser) could rewrite the roster past all three and leave the post in the
  // zero-active-provisioners state SPEC 1c exists to make unreachable.
  // RF-PINNACLE-2026 is the live instance of that state.
  //
  // NOT A CREDENTIAL BYPASS, said here so the next reader does not overread
  // it: api/sf-auth.js:328 takes the provisioning role from the SIGNED SESSION
  // TOKEN, not from this table. A forged officer row mints nothing.
  //
  // Reproducing artifact, exit 1 REPRODUCES before this change and exit 0
  // after: .claude/skills/sairn-hover-auditor/tools-hover2/
  // sf_officers_provisioning_bypass_repro.py
  'sf_officers',
  // 2026-10-11, FOUR, the same day as sf_officers and a separate edit. THE
  // GAMING-FLOOR MONEY RECORDS, and they are the first entries on this list
  // chosen by a DERIVATION rather than by a finding naming them one at a time.
  //
  // THE DERIVATION, so it can be re-run rather than believed: SF_RESOURCES
  // carries 36 resources; 18 were gated before this edit; NINE of the other 18
  // are Tier A by docs/CRITICALITY-TIERS.md's own letters. These four are the
  // Tier A ones with a money or statutory figure ON THE ROW.
  //   sf_sessions  register:373 -- prizeCap, receipts, prizes. prizeCap IS A
  //                STATUTORY LIMIT under ORC Chapter 2915, not a house rule.
  //                The regulated event record the rest of the gaming family
  //                reconciles against; it sat at B until the 2026-09-23 re-audit
  //                while sf_ledger was already A.
  //   sf_shifts    register:374 -- the only one of the four that is A on
  //                CONFIDENTIALITY as well. The row attributes a CASH VARIANCE
  //                to a NAMED employee and the app's own toast states it. A
  //                recorded shortage is read as an accusation, which is the
  //                same reasoning bld_tna is Confidentiality-A under.
  //   sf_tickets   register:377 -- unitPrice and total snapshotted at the
  //                moment of sale, against a named member, rolling into takings.
  //   sf_rentals   register:369 -- charge and proceeds, plus the
  //                alcohol/notified compliance pair a hall rental turns on.
  //
  // FIVE MORE ARE TIER A AND ARE DELIBERATELY NOT HERE. Named, because the
  // set-equality arm below would otherwise be the only record that they are
  // missing and it cannot say WHY: sf_district_imports (register:353),
  // sf_events (:358), sf_permit_flags (:367), sf_products (:368), sf_vehicles
  // (:380). The arm at the bottom of this file says widening the gate is a
  // PRODUCT DECISION about who may see a duty roster or a bottle count. The
  // batch that sent this change named four resources and their client write
  // sites; it did not name those five, and inventing approval for them here is
  // exactly the decision that arm exists to stop. Routed with the derivation.
  //
  // THE CLIENT WRITE HALF NEEDED NO CHANGE and every site was read at this HEAD:
  // sairnfreedom.html :3424, :3523 (in sfRecordResults at :3509) and :4976 for
  // sf_sessions; :4628 sf_tickets; :4739 sf_shifts; :5168 sf_rentals. All go
  // through st() -> sfSyncCollection -> sfData, and sfData at :1986-1991
  // attaches X-SD-Auth whenever a token is held, for every resource.
  //
  // THE CLIENT **READ** HALF DID, and it is in the same push: sfHydrateAll()
  // is called once, from DOMContentLoaded at sairnfreedom.html:7684, which runs
  // BEFORE any interactive sign-in -- and sfEnterApp() did not re-run it. On a
  // fresh browser every GATED resource's hydrate answered 403, the per-resource
  // .catch swallowed it, and signing in did not go back for the server's copy.
  // That was already true for the 18 gated before this edit; this change would
  // have widened it to 22 rather than introduced it.
  //
  // NOT PROVEN LIVE. No bare-key call was driven against a real SAIRNfreedom
  // licence for any of the four, unlike sf_vehicle_service above which carries
  // one with a control. Source-level, the register letters, and the write sites.
  'sf_sessions',
  'sf_shifts',
  'sf_tickets',
  'sf_rentals',
  // 2026-10-13, FIVE, AND THEY CLOSE THE TIER A SET. Michael's decision, which
  // is what this list has always needed and what the arm at the bottom of this
  // file calls "a product decision about who may see a duty roster".
  //
  // b4 derived NINE Tier A resources still ungated, gated the four carrying a
  // money or statutory figure, and NAMED these five with their register lines
  // rather than sweeping them in -- because the derivation was mine and the
  // decision was not. It has now been made, so the asymmetry b4 recorded is
  // closed rather than carried.
  //
  //   sf_district_imports  register:353  records arriving from the district;
  //                        the post neither authors them nor can re-request
  //                        them, so a wrong row has no upstream to re-read.
  //   sf_events            register:358  the post calendar every programme,
  //                        ceremony and gaming session hangs off.
  //   sf_permit_flags      register:367  gaming permit state. A wrong flag is
  //                        a post running gaming it is not permitted to run --
  //                        an ORC Chapter 2915 exposure, not a UI bug.
  //   sf_products          register:368  the priced catalogue every sf_tickets
  //                        row snapshots unitPrice from, so a wrong price is
  //                        wrong takings for every sale after it.
  //   sf_vehicles          register:380  computes its service-due flag from
  //                        the odometer sf_vehicle_service advances -- and that
  //                        sibling has been gated since 2026-09-29, so the pair
  //                        sat split across the gate for two weeks with the
  //                        WRITER protected and the READER open.
  //
  // 27 OF 36 WERE GATED AT THIS POINT and the nine that were not are all B/B.
  // They are named in api/sd-data.js beside the role-matrix call site, because
  // that is where their absence had a consequence: a resource with no session
  // has no role, so the matrix could not reach them.
  'sf_district_imports',
  'sf_events',
  'sf_permit_flags',
  'sf_products',
  'sf_vehicles',

  // ── THE LAST NINE, 2026-10-13 (b7). 36 OF 36. ───────────────────────────
  // GATED FOR A DIFFERENT REASON FROM EVERY WAVE BEFORE THEM, and the reason
  // is why they could be taken without a fresh product decision. The earlier
  // waves gated on the SENSITIVITY of the row -- minors' names, a felony flag,
  // ORC 2915 payee records, a statutory prize cap -- and none of these nine
  // clears that bar: they are the only sf_ resources that are B on integrity
  // AND B on confidentiality, which is exactly why four previous waves stopped
  // short of them and said so.
  //
  // What they clear is a different bar: THE ROLE MATRIX ALREADY HELD A
  // REVIEWED POLICY FOR ALL NINE. api/_lib/sf-roles.js carries a row for every
  // one of the 36 on purpose, so that the day one of these is gated its policy
  // is already written and reviewed rather than invented in the same hurried
  // edit that gates it. A role policy cannot run on a licence-key-only
  // resource -- no session means no role -- so the policy existed and could
  // not fire. Gating them is what makes it fire; the policy itself is b6's,
  // reviewed there, and no cell was authored here.
  //
  // WHAT THAT MEANS IN PRACTICE, measured off decide() rather than described:
  // every one of the nine now DENIES at least five of the ten roles on write,
  // and five of them deny on read as well. Those refusals are the reviewed
  // policy arriving. Two examples so this is not an abstraction -- a
  // chaplain.pastoral session is now refused a write to the vendor list, and a
  // member.admit session is refused the bottle counts.
  //
  //   sf_bottle_fills         the bar's product movement; feeds inventory
  //                           reconciliation and therefore the takings a
  //                           gaming post has to be able to defend.
  //   sf_ceremonial_items     ritual equipment held by the post.
  //   sf_documents            the post's governance documents -- the things
  //                           sf_signatures (gated 2026-09-24) BINDS PEOPLE
  //                           TO, so the signature was protected and the
  //                           document it signs was not.
  //   sf_honor_details        honours detail; attaches to named members.
  //   sf_inventory_counts     the counted-stock record the bottle fills are
  //                           reconciled against; the other half of a pair
  //                           whose halves disagree is how a shortage hides.
  //   sf_national_categories  national reporting categories. THE WEAKEST OF
  //                           THE NINE AND LABELLED SO IT CAN BE REVERSED ON
  //                           ITS OWN: it stores bare strings with no id, and
  //                           both sfSyncCollection and sfServerWinsMerge skip
  //                           id-less records, so client-side this gate is a
  //                           no-op today. It is here for set completeness,
  //                           not on evidence of exposure.
  //   sf_service_hours        volunteer service hours, by named member.
  //   sf_service_referrals    referral records -- the sibling of
  //                           sf_service_appointments, which was gated on
  //                           2026-09-22 for a VA-adjacent referral outcome.
  //                           The appointment was protected and the referral
  //                           was not.
  //   sf_vendors              the supplier list sf_vendor_prices (gated
  //                           2026-09-21) prices against. Same split pair
  //                           shape as sf_vehicles/sf_vehicle_service, which
  //                           sat across the gate for two weeks.
  //
  // THREE OF THE NINE CLOSE A SPLIT PAIR, and that is the strongest argument
  // in this block: sf_documents/sf_signatures, sf_service_referrals/
  // sf_service_appointments, sf_vendors/sf_vendor_prices. In each the half
  // somebody deliberately protected was readable or rewritable through its
  // unprotected twin.
  'sf_bottle_fills',
  'sf_ceremonial_items',
  'sf_documents',
  'sf_honor_details',
  'sf_inventory_counts',
  'sf_national_categories',
  'sf_service_hours',
  'sf_service_referrals',
  'sf_vendors',
];

function gatedSet() {
  return new Set((CODE.match(/'(sf_\w+)':\s*\['read', 'write'\]/g) || [])
    .map((s) => s.match(/'(sf_\w+)'/)[1]));
}
function expectedAppSet() {
  return new Set((CODE.match(/'(sf_\w+)': 'sairnfreedom'/g) || [])
    .map((s) => s.match(/'(sf_\w+)'/)[1]));
}

function main() {
  console.log('SAIRNfreedom session gate: two lists that must agree, and a third state');

  test('the gated list was actually parsed -- a zero-length scan would make ' +
       'every set assertion below vacuously true', () => {
    assert.ok(gatedSet().size >= APPROVED.length,
      'expected at least the ' + APPROVED.length + ' approved gated sf_ ' +
      'resources, parsed ' + gatedSet().size + '. A regex that matched ' +
      'nothing passes set equality against another empty set, which is a ' +
      'green run over no data.');
  });

  test('every one of the eight added 2026-09-22 requires a session on BOTH verbs', () => {
    const g = gatedSet();
    const missing = EIGHT_ADDED.filter((r) => !g.has(r));
    assert.deepStrictEqual(missing, [],
      'ungated: ' + missing.join(', ') + ' -- these carry minors\' names, a ' +
      'felony flag, or an ORC 2915 payee record.');
  });

  test('...and the three armed 2026-09-21 were not disturbed', () => {
    const g = gatedSet();
    const missing = THREE_PRIOR.filter((r) => !g.has(r));
    assert.deepStrictEqual(missing, [],
      'a previously gated resource lost its gate: ' + missing.join(', '));
  });

  test('THE LOAD-BEARING ONE: the gated list and the expectedApp list are the ' +
       'SAME SET', () => {
    const g = [...gatedSet()].sort();
    const e = [...expectedAppSet()].sort();
    const gatedOnly = g.filter((r) => !e.includes(r));
    const appOnly = e.filter((r) => !g.includes(r));
    assert.deepStrictEqual(
      { gatedButNoExpectedApp: gatedOnly, expectedAppButNotGated: appOnly },
      { gatedButNoExpectedApp: [], expectedAppButNotGated: [] },
      'the two maps disagree. A resource gated with no expectedApp entry ' +
      'resolves to \'stonedesk\' and refuses every correctly signed-in ' +
      'SAIRNfreedom caller with FORBIDDEN "sign in first" -- it fails closed ' +
      'and confusingly, which is the failure that gets a security change ' +
      'reverted rather than fixed.');
  });

  test('the gate is a SINGLE check both verbs pass through, not a per-branch copy', () => {
    // One `if (SD_SESSION_GATED[resource] && ...indexOf(action) !== -1)` before
    // the dispatch. Asserted as EXACTLY ONE: a second copy is a second place
    // for the answer to drift, and the read branch losing its copy is the half
    // that leaks rather than the half that changes rows.
    const n = (CODE.match(/if \(SD_SESSION_GATED\[resource\] && SD_SESSION_GATED\[resource\]\.indexOf\(action\) !== -1\)/g) || []).length;
    assert.strictEqual(n, 1,
      'expected exactly 1 session-gate dispatch check, found ' + n);
  });

  test('the gated set is EXACTLY the approved set -- nothing swept in, ' +
       'nothing quietly dropped', () => {
    // A gate that widened to all 35 would pass every assertion above and would
    // be a product decision nobody made. A gate that LOST a resource would
    // also pass them, except for the handful named in EIGHT_ADDED and
    // THREE_PRIOR. Set equality catches both, for every resource, and cannot
    // be satisfied by an empty gate.
    //
    // WHY EACH OF THE LAST FOUR IS IN APPROVED, kept here because a gate with
    // no recorded reason is the next session's mystery:
    //   sf_members       member identity; the 2026-09-22 gate comment above it
    //                    already called it an acknowledged gap, not a decision.
    //   sf_donor_awards  {donorKey, tierId, ...} -- the row says THIS PERSON
    //                    GAVE AT LEAST THIS MUCH, the same disclosure
    //                    sf_donations was gated for.
    //   sf_donor_tiers   the weak one, and labelled so it can be reversed on
    //                    its own: NO PERSON on the row. Gated only so an awards
    //                    row's opaque tierId cannot be resolved back to an
    //                    amount. Defence in depth, not an identity finding.
    //   sf_signatures    a named signer, their typed signature, and the
    //                    document it binds them to. NOT a fact about a person
    //                    but a reusable instrument that can be lifted off one
    //                    document and re-applied to another -- which is why it
    //                    is the sharpest of the four rather than the softest.
    const g = [...gatedSet()].sort();
    const a = [...APPROVED].sort();
    const unapproved = g.filter((r) => !a.includes(r));
    const lostItsGate = a.filter((r) => !g.includes(r));
    assert.deepStrictEqual(
      { gatedWithoutApproval: unapproved, approvedButUngated: lostItsGate },
      { gatedWithoutApproval: [], approvedButUngated: [] },
      'the gate and the approved list disagree. Widening it is a product ' +
      'decision about who may see a duty roster or a bottle count; narrowing ' +
      'it reopens a disclosure somebody closed on purpose. Either way, update ' +
      'APPROVED here AND the open-work row in the same change -- do not let ' +
      'the row and the code drift apart.');
  });
}

main();
console.log('\n' + passed + ' assertions passed');
