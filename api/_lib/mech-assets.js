// api/_lib/mech-assets.js
// SAIRNmechanical -- site asset registry (customer -> site -> asset).
//
// PURE -- no I/O.
//
// ── WHY THIS SECOND ─────────────────────────────────────────────────────────
// docs/superpowers/specs/2026-08-27-sairnmechanical-shared-platform-competitive-research.md
// §9d ranks this SECOND of ten capabilities: "Prerequisite for A3, A5, A7, B8,
// G13. Table stakes -- every incumbent has it." §3 A2 records that the named
// fields are identical across HVAC, electrical and plumbing -- make, model,
// serial, install date, warranty, and a service-history chain -- and that only
// the asset TAXONOMY differs by trade. So the schema is shared and the type
// vocabulary is the trade-gated part.
//
// Verified before building, same as the credential registry: the Equipment
// page was an honest empty state and its "+ Add Equipment" button had NO
// handler.
//
// ── NOT APPEND-ONLY, AND THAT IS A DELIBERATE DIFFERENCE ────────────────────
// mech_credentials is append-only because a licence is EVIDENCE and a renewal
// must not overwrite what someone held on a given day. An asset is not
// evidence, it is a description of a physical thing: a serial gets corrected, a
// unit gets relocated, a nameplate is re-read. Copying the append-only shape
// here by reflex would have forced a new row for every typo and made "which
// row is the unit" ambiguous.
//
// The SERVICE HISTORY on an asset is a different matter and is genuinely
// append-only -- it is not built in this pass, and is called out here rather
// than half-built.
//
// ── THE PART WITH LEGAL WEIGHT: REFRIGERANT CHARGE ──────────────────────────
// EPA refrigerant-management rules key their leak-repair provisions to
// appliances whose FULL CHARGE is at or above 50 pounds (40 CFR 82.157). That
// number is the reason charge is a first-class field here rather than a note.
//
// THIS ENGINE DOES NOT ISSUE A COMPLIANCE VERDICT, and that is deliberate.
// Leak-rate percentages differ by appliance category, and the HFC picture has
// moved (2016 rule, the 2020 partial rollback, the AIM Act rulemaking since).
// Encoding a rate here would be this app asserting current federal law from a
// hardcoded number. So the engine answers one narrow, checkable question:
//
//     is the recorded full charge at or above the configured threshold?
//     -> at_or_above | below | unknown_charge
//
// and the caller is told the threshold and its citation so the answer can be
// checked. "May be in scope, confirm against current rules" is the honest
// output; "you must inspect quarterly" is not one this app has earned.
//
// ── AND UNKNOWN IS NEVER "BELOW" ────────────────────────────────────────────
// The rule this file exists to keep. A unit with no recorded charge is
// `unknown_charge`, never `below`. Telling a shop a machine is under threshold
// when nobody ever weighed it is a compliance claim with no evidence behind
// it, and it is the exact shape of the EPA 608 mistake the credential engine
// was built to avoid: an answer that looks like clearance.

'use strict';

const shared = require('./credential-expiry');

const DEFAULT_WARN_DAYS = shared.DEFAULT_WARN_DAYS;

// 40 CFR 82.157 -- the leak-repair provisions apply to appliances with a full
// charge at or above this. Exported and passed in rather than buried, so a
// caller can see the number the answer depends on.
const EPA_LEAK_THRESHOLD_LB = 50;
const EPA_THRESHOLD_CITATION = '40 CFR 82.157';

// ── AND A SECOND RULE, WHICH IS NOT THE SAME RULE (2026-09-17) ─────────────
// 40 CFR 82.157 above is the SECTION 608 leak-repair rule, and 50 lb is correct
// for it. The AIM Act's HFC rule is a DIFFERENT regulation -- 40 CFR 84.106,
// Part 84 subpart C -- and it has applied since 2026-01-01 to appliances holding
// 15 lb or more of an HFC with a GWP above 53. An appliance can be out of scope
// under one and in scope under the other, and until today this engine modelled
// only the first. The 2026-08-21 trades research flagged the change and dated it
// correctly; nothing had acted on it.
//
// THE APP DOES NOT DECIDE WHICH RULE APPLIES, and that is the whole design.
// Both scopes are computed independently, both carry their own threshold and
// citation, and the board reports both side by side. Picking one would be this
// app asserting which federal rule governs a customer's appliance -- the same
// judgement the header above already refuses to make about leak RATES.
//
// ── WHY THERE IS NO GWP TABLE HERE, AND WHY THAT PRODUCES A FOURTH STATE ───
// Deciding whether r410a is "an HFC above GWP 53" needs a substance table, and
// seeding one would be the mistake roofing-warranties.js refuses about GAF
// tiers: a number this file asserted, which a contractor then acted on, with no
// source behind it. GWP figures are also revised, and a stale table reads as
// authoritative.
//
// So the substance half is STATED BY THE CONTRACTOR -- `hfc_gwp_over_53`, a
// tri-state -- and an appliance at or over 15 lb whose substance nobody has
// stated is `unknown_substance`. NOT `below`, and not in scope either. Same
// discipline `unknown_charge` already keeps on the weight axis: an answer that
// looks like clearance is worse than no answer.
//
// The one thing CHARGE ALONE can settle is the negative -- under 15 lb is out of
// scope whatever the refrigerant is -- so that is answered without asking.
const AIM_LEAK_THRESHOLD_LB = 15;
const AIM_THRESHOLD_CITATION = '40 CFR 84.106';
const AIM_GWP_FLOOR = 53;
// The repair window and its follow-up verification, both from the same rule.
const AIM_REPAIR_DAYS = 30;
const AIM_VERIFY_FOLLOWUP_DAYS = 10;

// ── AND A THIRD RULE, WHICH IS A STATE ONE (2026-09-25) ────────────────────
// CARB's Refrigerant Management Program, 17 CCR 95380 et seq. Both rules above
// are FEDERAL and reach every asset in the registry; this one reaches only
// assets in California, and until now the registry had no way to say where an
// asset was. THAT IS THE FIRST GAP, not the threshold: a state rule applied to
// an asset whose state nobody recorded is a guess with a citation on it.
//
// SO THERE IS A SIXTH SCOPE HERE THAT NEITHER FEDERAL LIMB HAS:
// `unknown_jurisdiction`. Not `below`, not `not_applicable`. An asset with no
// state recorded is NOT a finding that CARB does not reach it, exactly as
// `unknown_substance` is not a finding that the AIM Act does not.
//
// ── THE 50 lb BOUNDARY IS NOT THE SAME 50 lb, AND THAT IS WHY THIS IS ITS
// ── OWN LIMB RATHER THAN A FLAG ON refrigerantScope.
// 40 CFR 82.157 reaches an appliance normally containing 50 pounds OR MORE.
// The CARB program reaches a system containing MORE THAN 50 pounds. A unit
// weighed at exactly 50.0 lb is therefore IN scope federally and OUT of scope
// under the state rule, and a shared threshold constant with a shared
// comparison would have silently answered one of those wrongly. Driven both
// ways in the test file at exactly 50.
//
// ── THE GWP FLOOR IS DIFFERENT TOO, AND ONE DIRECTION OF IT IS DEDUCIBLE ───
// CARB's high-GWP floor for this program is 150; the AIM Act's is 53. Those
// are different questions and the contractor answers them separately --
// `gwp_over_150` is its own tri-state for the same reason `hfc_gwp_over_53`
// is: this file carries no GWP table and will not seed one.
//
// BUT ONE IMPLICATION IS SOUND AND IS TAKEN: if the contractor has already
// stated the refrigerant is NOT above 53, it cannot be above 150, so the CARB
// substance test answers `not_applicable` without asking again. The converse
// is NOT sound -- above 53 says nothing about 150 -- and is not taken. A
// refrigerant in the 54-149 band (R-152a sits at about 124) is in AIM scope
// and out of CARB's, which is precisely the case the asymmetry protects.
//
// ── WHAT THIS LIMB DOES NOT ASSERT ────────────────────────────────────────
// Inspection frequency, registration deadlines, reporting cadence and the
// tiering by system size are NOT encoded. They are real parts of the program
// and this file does not carry them, because the same rule the AIM block
// states applies here: a number this app asserted, which a contractor then
// acted on, with no source behind it. The scope answer says the program may
// reach the unit and says to confirm the duties against the current rule.
const CARB_RMP_THRESHOLD_LB = 50;
const CARB_RMP_CITATION = '17 CCR 95380 et seq.';
const CARB_GWP_FLOOR = 150;
const CARB_STATE = 'CA';

// Trade taxonomy. The research is explicit that this is the ONLY part that
// differs per trade -- the schema does not. Unknown types are refused on write
// rather than stored, so a board can never group by a category nobody defined.
const ASSET_TYPES = {
  rtu: true,                // rooftop unit
  split_system: true,
  chiller: true,
  boiler: true,
  furnace: true,
  heat_pump: true,
  ahu: true,                // air handling unit
  vrf: true,
  cooling_tower: true,
  water_heater: true,
  pump: true,
  exhaust_fan: true,
  controls: true,           // BMS / controls panel
  other: true
};

// Refrigerants seen in the field. `none` is a real answer for a boiler or a
// pump and is NOT the same as nobody having recorded one.
const REFRIGERANTS = {
  none: true, r22: true, r410a: true, r454b: true, r32: true,
  r407c: true, r134a: true, r513a: true, r717: true, r744: true, other: true
};

function refuse(code, message, extra) {
  return Object.assign({ ok: false, error: { code: code, message: message } }, extra || {});
}

const isDate = shared.isDate;
const daysUntil = shared.daysUntil;

// A recorded weight, or null. NOT Number() directly, and this is the reason:
// Number('') and Number(null) are both 0, and Number('   ') is 0 too -- so an
// EMPTY CHARGE FIELD would have read as a genuine zero-pound measurement and
// classified the unit as BELOW THRESHOLD. That is precisely the
// unknown-reported-as-cleared failure this file exists to prevent, and the
// test suite caught it here rather than a shop discovering it on a chiller.
function chargeLb(v) {
  if (v === null || v === undefined) return null;
  if (typeof v === 'string' && v.trim() === '') return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

// Warranty, in this app's words. Reuses the shared boundary arithmetic --
// 'valid' is the primitive's word and is mapped here, exactly as the two
// credential engines do, so nobody inherits another app's meaning.
//   in_warranty / expiring / expired / unknown / none
function classifyWarranty(asset, today, warnDays) {
  const w = Number.isFinite(warnDays) ? warnDays : DEFAULT_WARN_DAYS;
  if (!asset || typeof asset !== 'object') return { status: 'unknown', days: null, warn_days: w };
  // has_warranty === false is a POSITIVE answer -- an out-of-warranty unit
  // somebody checked -- and must not read the same as one nobody checked.
  if (asset.has_warranty === false) return { status: 'none', days: null, warn_days: w };
  const c = shared.classifyDays(daysUntil(asset.warranty_expires_on, today), w);
  return {
    status: c.status === 'valid' ? 'in_warranty' : c.status,
    days: c.days,
    warn_days: c.warn_days
  };
}

// The narrow, checkable question -- NOT a compliance verdict. See the header.
function refrigerantScope(asset, thresholdLb) {
  const t = Number.isFinite(thresholdLb) ? thresholdLb : EPA_LEAK_THRESHOLD_LB;
  const base = { threshold_lb: t, citation: EPA_THRESHOLD_CITATION };
  if (!asset || typeof asset !== 'object') {
    return Object.assign({ scope: 'unknown_charge', reason: 'no asset' }, base);
  }
  // A unit that genuinely holds no refrigerant is a real answer.
  if (asset.refrigerant_type === 'none') {
    return Object.assign({ scope: 'not_applicable', reason: 'this unit holds no refrigerant' }, base);
  }
  const lb = chargeLb(asset.refrigerant_charge_lb);
  if (lb === null || lb < 0) {
    // NEVER 'below'. Nobody weighed it.
    return Object.assign({
      scope: 'unknown_charge',
      reason: 'no full charge recorded, so the threshold cannot be applied to this unit'
    }, base);
  }
  return Object.assign({
    scope: lb >= t ? 'at_or_above' : 'below',
    charge_lb: lb,
    reason: lb >= t
      ? 'recorded full charge is at or above the threshold — leak-repair provisions may be in scope; confirm against the current rule'
      : 'recorded full charge is below the threshold'
  }, base);
}

// ── THE SECOND, INDEPENDENT SCOPE. Deliberately NOT a variant of the one
// ── above: it is a different rule with a different threshold, a different
// ── citation and an extra axis the other does not have.
// Written as its own function rather than a parameter on refrigerantScope for
// the reason this platform keeps relearning -- a flag threaded through one
// function is a flag somebody passes the wrong way, and the two answers must be
// producible side by side without either being "the" answer.
function aimScope(asset, thresholdLb, gwpFloor) {
  const t = Number.isFinite(thresholdLb) ? thresholdLb : AIM_LEAK_THRESHOLD_LB;
  const g = Number.isFinite(gwpFloor) ? gwpFloor : AIM_GWP_FLOOR;
  const base = { threshold_lb: t, citation: AIM_THRESHOLD_CITATION, gwp_floor: g };
  if (!asset || typeof asset !== 'object') {
    return Object.assign({ scope: 'unknown_charge', reason: 'no asset' }, base);
  }
  if (asset.refrigerant_type === 'none') {
    return Object.assign({ scope: 'not_applicable', reason: 'this unit holds no refrigerant' }, base);
  }
  const lb = chargeLb(asset.refrigerant_charge_lb);
  if (lb === null || lb < 0) {
    return Object.assign({
      scope: 'unknown_charge',
      reason: 'no full charge recorded, so the threshold cannot be applied to this unit'
    }, base);
  }
  // CHARGE ALONE SETTLES THE NEGATIVE. Under the threshold is out of scope
  // whatever the substance is, so the substance is not asked for.
  if (lb < t) {
    return Object.assign({
      scope: 'below', charge_lb: lb,
      reason: 'recorded full charge is below the threshold, so this rule does not '
        + 'reach it whatever the refrigerant is'
    }, base);
  }
  // At or over the threshold, the substance decides -- and only the contractor
  // can state it. `true` and `false` are both ANSWERS; absent is not.
  if (asset.hfc_gwp_over_53 === true) {
    return Object.assign({
      scope: 'at_or_above', charge_lb: lb,
      reason: 'recorded full charge is at or above the threshold and the refrigerant '
        + 'is recorded as an HFC above the GWP floor — leak-repair provisions may be '
        + 'in scope; confirm against the current rule'
    }, base);
  }
  if (asset.hfc_gwp_over_53 === false) {
    return Object.assign({
      scope: 'not_applicable', charge_lb: lb,
      reason: 'recorded as not an HFC above the GWP floor, so this rule does not reach it'
    }, base);
  }
  // NEITHER 'below' NOR IN SCOPE. Nobody stated the substance.
  return Object.assign({
    scope: 'unknown_substance', charge_lb: lb,
    reason: 'recorded full charge is at or above the threshold, but nobody has '
      + 'stated whether this refrigerant is an HFC above the GWP floor — this is '
      + 'NOT a finding that the rule does not apply'
  }, base);
}

// ── THE THIRD, STATE-SCOPED LIMB. See the CARB block above the constants.
// Written as its own function for the same reason aimScope is: three answers
// must be producible side by side without any of them being "the" answer, and
// this one has an axis -- jurisdiction -- that neither federal limb has.
function carbScope(asset, thresholdLb, gwpFloor) {
  const t = Number.isFinite(thresholdLb) ? thresholdLb : CARB_RMP_THRESHOLD_LB;
  const g = Number.isFinite(gwpFloor) ? gwpFloor : CARB_GWP_FLOOR;
  const base = { threshold_lb: t, citation: CARB_RMP_CITATION, gwp_floor: g,
                 state: CARB_STATE };
  if (!asset || typeof asset !== 'object') {
    return Object.assign({ scope: 'unknown_jurisdiction', reason: 'no asset' }, base);
  }
  // JURISDICTION IS ASKED FIRST, and a missing answer stops here. Reaching the
  // charge test with no state would mean reporting a Californian threshold
  // against an asset that may be in Ohio.
  const st = String(asset.site_state == null ? '' : asset.site_state).trim().toUpperCase();
  if (!st) {
    return Object.assign({
      scope: 'unknown_jurisdiction',
      reason: 'no state recorded for this site, so a state rule cannot be applied — '
        + 'this is NOT a finding that the program does not reach it'
    }, base);
  }
  if (st !== CARB_STATE) {
    return Object.assign({
      scope: 'not_applicable', site_state: st,
      reason: 'this site is recorded in ' + st + ', and this is a California program'
    }, base);
  }
  if (asset.refrigerant_type === 'none') {
    return Object.assign({ scope: 'not_applicable', site_state: st,
      reason: 'this unit holds no refrigerant' }, base);
  }
  const lb = chargeLb(asset.refrigerant_charge_lb);
  if (lb === null || lb < 0) {
    return Object.assign({
      scope: 'unknown_charge', site_state: st,
      reason: 'no full charge recorded, so the threshold cannot be applied to this unit'
    }, base);
  }
  // MORE THAN, not at-or-above. See the boundary note above the constants: the
  // federal leak-repair rule reaches 50 lb exactly and this one does not.
  if (lb <= t) {
    return Object.assign({
      scope: 'below', charge_lb: lb, site_state: st,
      reason: 'recorded full charge is not above the threshold, so this program does '
        + 'not reach it whatever the refrigerant is'
    }, base);
  }
  if (asset.gwp_over_150 === true) {
    return Object.assign({
      scope: 'at_or_above', charge_lb: lb, site_state: st,
      reason: 'recorded full charge is above the threshold and the refrigerant is '
        + 'recorded as high-GWP for this program — registration, leak inspection and '
        + 'reporting duties may apply; this app does NOT encode their frequency or '
        + 'deadlines, so confirm them against the current rule'
    }, base);
  }
  if (asset.gwp_over_150 === false) {
    return Object.assign({
      scope: 'not_applicable', charge_lb: lb, site_state: st,
      reason: 'recorded as not high-GWP for this program, so it does not reach it'
    }, base);
  }
  // THE ONE SOUND DEDUCTION, AND ONLY THIS ONE. At or below 53 is necessarily
  // below 150. The converse is not taken -- see the constants block.
  if (asset.hfc_gwp_over_53 === false) {
    return Object.assign({
      scope: 'not_applicable', charge_lb: lb, site_state: st,
      derived_from: 'hfc_gwp_over_53',
      reason: 'the refrigerant is already recorded as at or below GWP 53, which is '
        + 'necessarily below ' + g + ', so this program does not reach it — derived, '
        + 'not asked again'
    }, base);
  }
  return Object.assign({
    scope: 'unknown_substance', charge_lb: lb, site_state: st,
    reason: 'recorded full charge is above the threshold, but nobody has stated '
      + 'whether this refrigerant is high-GWP for this program — this is NOT a '
      + 'finding that the program does not apply'
  }, base);
}

// ── THE REPAIR CLOCK, AND IT ONLY RUNS ON A DATE SOMEBODY RECORDED ─────────
// 40 CFR 84.106 gives 30 days from a leak exceeding the applicable rate to
// identify and repair it, with an initial verification test in that window and a
// follow-up within 10 days of the initial.
//
// WHAT THIS DOES NOT DO: decide whether a leak exceeded the rate. The rates
// differ by appliance category and the header above already refuses to encode
// them. This runs the clock from a date the contractor recorded as the day the
// leak was found, and says so.
//
// NO DATE MEANS NO CLOCK, reported as such. Inventing a start date -- from the
// install date, from today, from anything -- would put a deadline on a screen
// that no fact supports.
function aimRepairClock(asset, today, repairDays, followupDays) {
  const rd = Number.isFinite(repairDays) ? repairDays : AIM_REPAIR_DAYS;
  const fd = Number.isFinite(followupDays) ? followupDays : AIM_VERIFY_FOLLOWUP_DAYS;
  const base = { repair_days: rd, followup_days: fd, citation: AIM_THRESHOLD_CITATION };
  const on = asset && asset.leak_detected_on;
  if (!isDate(on)) {
    return Object.assign({
      state: 'no_leak_recorded', detected_on: null, repair_due_on: null, days_left: null,
      reason: on ? 'a leak date is recorded but is not YYYY-MM-DD, so no clock is run'
                 : 'no leak detection date recorded, so no repair clock is running'
    }, base);
  }
  // isoPlusDays, unconditionally. An earlier draft read
  // `shared.addDays ? shared.addDays(on, rd) : isoPlusDays(on, rd)` -- and
  // `shared.addDays` does not exist, so the first arm was dead the day it was
  // written and would have woken up silently the first time anybody added an
  // `addDays` to credential-expiry.js with a different argument order or a
  // Date return. A deadline computed by whichever function happened to exist
  // is the quiet-wrong-number shape; there is one way to add days here.
  const dueOn = isoPlusDays(on, rd);
  const left = daysUntil(dueOn, today);
  // A repair the contractor has recorded as verified stops the clock. Recorded,
  // never inferred from the passage of time.
  if (asset.leak_repair_verified_on && isDate(asset.leak_repair_verified_on)) {
    return Object.assign({
      state: 'repair_verified', detected_on: on, repair_due_on: dueOn,
      days_left: left, verified_on: asset.leak_repair_verified_on,
      followup_due_on: isoPlusDays(asset.leak_repair_verified_on, fd),
      reason: 'an initial verification is recorded; the follow-up verification is '
        + 'due within ' + fd + ' days of it'
    }, base);
  }
  return Object.assign({
    state: left === null ? 'unknown' : (left < 0 ? 'overdue' : 'open'),
    detected_on: on, repair_due_on: dueOn, days_left: left,
    reason: left === null
      ? 'the repair deadline could not be computed from the recorded dates'
      : (left < 0
        ? 'the ' + rd + '-day repair window has passed with no verification recorded — '
          + 'the rule requires a retrofit or retirement plan at that point; confirm '
          + 'against the current rule'
        : 'within the ' + rd + '-day repair window; an initial verification test is '
          + 'required inside it')
  }, base);
}

// Date arithmetic kept local and explicit. UTC only, because a repair deadline
// that shifts with the reader's timezone is a different date for two people
// looking at the same screen -- the defect fixed across nine SAIRNvet panels.
function isoPlusDays(iso, n) {
  if (!isDate(iso)) return null;
  const d = new Date(iso + 'T00:00:00Z');
  if (!Number.isFinite(d.getTime())) return null;
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
}

function assetKey(a) {
  return String(a && a.asset_id != null ? a.asset_id : '').trim();
}

// The board. No aggregate "is this site compliant" verdict, deliberately --
// that is a join into agreements and certificates that does not exist yet, and
// inventing it from asset rows alone would be exactly the fabricated-KPI shape
// this app was cleaned of on 2026-08-27.
function evaluateRegistry(assets, today, opts) {
  if (!isDate(today)) return refuse('BAD_TODAY', 'today must be YYYY-MM-DD');
  const o = opts || {};
  const rows = (Array.isArray(assets) ? assets : [])
    .filter(function (a) { return a && typeof a === 'object' && assetKey(a); })
    .map(function (a) {
      const w = classifyWarranty(a, today, o.warn_days);
      const r = refrigerantScope(a, o.threshold_lb);
      // BOTH RULES, SIDE BY SIDE. Neither is "the" answer -- see the AIM Act
      // block at the top of this file.
      const aim = aimScope(a, o.aim_threshold_lb, o.aim_gwp_floor);
      // THE THIRD RULE, and the only state-scoped one. Reported beside the two
      // federal limbs rather than merged into them -- see the CARB block.
      const carb = carbScope(a, o.carb_threshold_lb, o.carb_gwp_floor);
      const clock = aimRepairClock(a, today, o.aim_repair_days, o.aim_followup_days);
      return {
        asset_id: a.asset_id,
        customer_name: a.customer_name || null,
        site_name: a.site_name || null,
        site_state: a.site_state ? String(a.site_state).trim().toUpperCase() : null,
        asset_type: a.asset_type || null,
        make: a.make || null,
        model: a.model || null,
        serial_no: a.serial_no || null,
        location_on_site: a.location_on_site || null,
        installed_on: isDate(a.installed_on) ? a.installed_on : null,
        warranty_status: w.status,
        warranty_days: w.days,
        refrigerant_type: a.refrigerant_type || null,
        refrigerant_charge_lb: chargeLb(a.refrigerant_charge_lb),
        refrigerant_scope: r.scope,
        refrigerant_reason: r.reason,
        aim_scope: aim.scope,
        aim_reason: aim.reason,
        aim_repair_state: clock.state,
        aim_repair_due_on: clock.repair_due_on,
        aim_repair_days_left: clock.days_left,
        aim_repair_reason: clock.reason,
        carb_scope: carb.scope,
        carb_reason: carb.reason
      };
    });

  const warranty = { in_warranty: 0, expiring: 0, expired: 0, none: 0, unknown: 0 };
  const refrigerant = { at_or_above: 0, below: 0, not_applicable: 0, unknown_charge: 0 };
  // A SEPARATE TALLY, NOT A MERGED ONE. Summing the two rules into a single
  // "in scope" number would be the app deciding which one governs, which is the
  // thing this file refuses to do.
  const aimCounts = { at_or_above: 0, below: 0, not_applicable: 0,
                      unknown_charge: 0, unknown_substance: 0 };
  const aimRepair = { open: 0, overdue: 0, repair_verified: 0,
                      no_leak_recorded: 0, unknown: 0 };
  // SIX BUCKETS, NOT FIVE. `unknown_jurisdiction` is the state-rule axis the
  // two federal tallies do not have, and folding it into unknown_charge would
  // hide the fact that the registry does not know where its assets are.
  const carbCounts = { at_or_above: 0, below: 0, not_applicable: 0,
                       unknown_charge: 0, unknown_substance: 0,
                       unknown_jurisdiction: 0 };
  rows.forEach(function (r) {
    warranty[r.warranty_status] = (warranty[r.warranty_status] || 0) + 1;
    refrigerant[r.refrigerant_scope] = (refrigerant[r.refrigerant_scope] || 0) + 1;
    aimCounts[r.aim_scope] = (aimCounts[r.aim_scope] || 0) + 1;
    aimRepair[r.aim_repair_state] = (aimRepair[r.aim_repair_state] || 0) + 1;
    carbCounts[r.carb_scope] = (carbCounts[r.carb_scope] || 0) + 1;
  });

  // Sites, derived rather than stored: the research's shape is
  // customer -> site -> asset, and a site with no assets does not exist yet.
  const sites = {};
  rows.forEach(function (r) {
    const k = (r.customer_name || '') + ' | ' + (r.site_name || '');
    sites[k] = (sites[k] || 0) + 1;
  });

  return {
    ok: true,
    today: today,
    threshold_lb: Number.isFinite(o.threshold_lb) ? o.threshold_lb : EPA_LEAK_THRESHOLD_LB,
    citation: EPA_THRESHOLD_CITATION,
    counts: { assets: rows.length, sites: Object.keys(sites).length },
    warranty: warranty,
    refrigerant: refrigerant,
    // ── THE SECOND RULE, REPORTED AS ITS OWN BLOCK ─────────────────────────
    // Its own threshold and its own citation, so a reader can never mistake
    // which number produced which count. Deliberately NOT nested under
    // `refrigerant` above: nesting would imply one is a refinement of the
    // other, and they are two different regulations.
    aim: {
      threshold_lb: Number.isFinite(o.aim_threshold_lb) ? o.aim_threshold_lb : AIM_LEAK_THRESHOLD_LB,
      citation: AIM_THRESHOLD_CITATION,
      gwp_floor: Number.isFinite(o.aim_gwp_floor) ? o.aim_gwp_floor : AIM_GWP_FLOOR,
      scope: aimCounts,
      repair: aimRepair,
      // Same discipline as unknown_charge_count: the count that could be read
      // as clearance is surfaced beside the totals, not under them.
      unknown_substance_count: aimCounts.unknown_substance,
      overdue_repair_count: aimRepair.overdue
    },
    // ── THE THIRD RULE, AND THE ONLY STATE ONE ─────────────────────────────
    // Its own block for the same reason `aim` has one, plus a reason neither
    // federal limb needs: `unknown_jurisdiction_count`. A registry that does
    // not know where its assets are cannot answer a state rule at all, and
    // that number says so on the face of the board rather than leaving every
    // such asset looking out of scope.
    carb: {
      threshold_lb: Number.isFinite(o.carb_threshold_lb) ? o.carb_threshold_lb : CARB_RMP_THRESHOLD_LB,
      citation: CARB_RMP_CITATION,
      gwp_floor: Number.isFinite(o.carb_gwp_floor) ? o.carb_gwp_floor : CARB_GWP_FLOOR,
      state: CARB_STATE,
      scope: carbCounts,
      unknown_substance_count: carbCounts.unknown_substance,
      unknown_jurisdiction_count: carbCounts.unknown_jurisdiction,
      // SAID IN THE PAYLOAD, not only in a comment, because this block will be
      // read by somebody who never opens this file.
      not_asserted: 'inspection frequency, registration deadlines, reporting '
        + 'cadence and tiering by system size are NOT encoded by this app'
    },
    // Surfaced beside the totals rather than under them, same as the credential
    // board: a registry that buries its unknowns reads as a clean bill.
    unknown_charge_count: refrigerant.unknown_charge,
    unknown_warranty_count: warranty.unknown,
    rows: rows
  };
}

module.exports = {
  DEFAULT_WARN_DAYS,
  CARB_RMP_THRESHOLD_LB,
  CARB_RMP_CITATION,
  CARB_GWP_FLOOR,
  CARB_STATE,
  carbScope,
  EPA_LEAK_THRESHOLD_LB,
  EPA_THRESHOLD_CITATION,
  AIM_LEAK_THRESHOLD_LB,
  AIM_THRESHOLD_CITATION,
  AIM_GWP_FLOOR,
  AIM_REPAIR_DAYS,
  AIM_VERIFY_FOLLOWUP_DAYS,
  ASSET_TYPES,
  REFRIGERANTS,
  classifyWarranty,
  refrigerantScope,
  aimScope,
  aimRepairClock,
  evaluateRegistry
};
