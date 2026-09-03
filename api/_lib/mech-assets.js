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
      return {
        asset_id: a.asset_id,
        customer_name: a.customer_name || null,
        site_name: a.site_name || null,
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
        refrigerant_reason: r.reason
      };
    });

  const warranty = { in_warranty: 0, expiring: 0, expired: 0, none: 0, unknown: 0 };
  const refrigerant = { at_or_above: 0, below: 0, not_applicable: 0, unknown_charge: 0 };
  rows.forEach(function (r) {
    warranty[r.warranty_status] = (warranty[r.warranty_status] || 0) + 1;
    refrigerant[r.refrigerant_scope] = (refrigerant[r.refrigerant_scope] || 0) + 1;
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
    // Surfaced beside the totals rather than under them, same as the credential
    // board: a registry that buries its unknowns reads as a clean bill.
    unknown_charge_count: refrigerant.unknown_charge,
    unknown_warranty_count: warranty.unknown,
    rows: rows
  };
}

module.exports = {
  DEFAULT_WARN_DAYS,
  EPA_LEAK_THRESHOLD_LB,
  EPA_THRESHOLD_CITATION,
  ASSET_TYPES,
  REFRIGERANTS,
  classifyWarranty,
  refrigerantScope,
  evaluateRegistry
};
