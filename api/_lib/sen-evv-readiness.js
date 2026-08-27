// api/_lib/sen-evv-readiness.js
// SAIRNsenior EVV submission-readiness engine. 2026-08-27.
//
// PURE -- no I/O, no database, no network. Takes a visit plus the client and
// caregiver it references, returns whether that visit carries the data an EVV
// submission would need and NAMES what is missing. Same shape as
// api/_lib/payer-routing.js and api/_lib/compliance-rules.js, for the same
// reason: the rules can be tested without infrastructure.
//
// ── WHAT THIS IS FOR, AND WHAT IT DELIBERATELY IS NOT ────────────────────
// This REPORTS. It does not transmit, does not persist, and does not modify a
// visit. SAIRNsenior has no transmission path to Sandata, HHAeXchange, Tellus
// or CareBridge, and building one is blocked on three things that are not
// engineering decisions: a trading-partner agreement per aggregator, a place to
// hold per-agency aggregator credentials (an OPEN decision, deliberately not
// resolved here -- see docs/SAIRN-OPEN-WORK-INDEX.md), and a wire format that
// could not be verified from primary sources. Readiness needs none of those and
// is useful on its own: it makes the real cost of compliance visible per visit,
// BEFORE anyone commits to the field work.
//
// It also builds exactly the data model transmission will consume later, which
// is why it is worth doing first rather than instead.
//
// ── THE FEDERAL FLOOR — VERIFIED 2026-08-27, AND WHAT IT ACTUALLY SAYS ───
// The six items in FEDERAL_ELEMENTS below are PRIMARY-VERIFIED, word for word,
// against 42 U.S.C. sec. 1396b(l)(5)(A)(i)-(vi) -- read from two independent
// official hosts (uscode.house.gov and govinfo.gov) that returned identical
// text. Citation: SSA sec. 1903(l), added by Pub. L. 114-255, div. B, title XII,
// sec. 12006(a), Dec. 13, 2016.
//
// A CORRECTION THIS MODULE PREVIOUSLY GOT WRONG, kept visible rather than
// quietly overwritten: this header used to say the statute "requires six data
// elements per EVV visit". IT DOES NOT. The six are the statutory DEFINITION of
// the term "electronic visit verification system" -- things a qualifying system
// "electronically verifie[s]". The operative requirement, at sec. 1396b(l)(1),
// is that a State REQUIRE THE USE of such a system for personal care and home
// health services "requiring an in-home visit by a provider". Practically the
// same effect, but "data element" is CMS/vendor vocabulary and was being
// attributed to the statute, which is exactly the kind of small false precision
// a compliance module should not ship.
//
// TWO RESIDUAL GAPS, AND THEY ARE WHY `verified` IS NOT SIMPLY `true`:
//   1. CMS's own EVV guidance has NOT been read -- medicaid.gov and cms.gov
//      return 403 to automated fetch. That matters more than it sounds: a full
//      Federal Register sweep confirms there is NO EVV rulemaking at all, so
//      every operational detail CMS has published lives in sub-regulatory
//      guidance nobody here has seen.
//   2. See the per-state note below.
//
// ── PER-STATE RULES ARE NOT ENCODED, AND THAT IS A REFUSAL, NOT A GAP ────
// NOTHING is seeded. A state with no verified rule set is reported as
// `state_rules: 'not_verified'` with the federal floor applied alone -- never as
// "compliant". Inventing a state's requirements would put a green tick on a
// screen with nothing real behind it, which is exactly what Guardian Check 0b
// exists to catch.
//
// PRECISION ON WHY, because the earlier wording overstated it: this module used
// to assert that "states add their own required elements on top of the federal
// floor". That is an INFERENCE FROM STATUTORY SILENCE, not a quoted rule. The
// statute contains no "at a minimum" language and no preemption clause; the six
// appear only inside a definitional "means ... verified with respect to--"
// clause. The inference is defensible and uncontradicted -- sec. 1396b(l)(2)(A)
// requires each State to consult providers so its system is "minimally
// burdensome" and reflects "existing best practices ... in the State", which
// points toward variation rather than uniformity. But the honest phrasing is
// "the statute specifies six verification points and does not preempt
// additional State requirements", and it must NEVER be written as "CMS states
// these are minimum requirements" until that CMS guidance is actually read.

'use strict';

// The six things a qualifying EVV system must electronically verify per visit,
// quoted from 42 U.S.C. sec. 1396b(l)(5)(A)(i)-(vi). NOT a captured-field list
// -- see the header correction.
// `key` is stable and is what the UI groups on; `label` is what a user reads.
const FEDERAL_ELEMENTS = [
  { key: 'service_type', label: 'Type of service performed' },
  { key: 'recipient', label: 'Individual receiving the service' },
  { key: 'service_date', label: 'Date of the service' },
  { key: 'location', label: 'Location of service delivery' },
  { key: 'provider', label: 'Individual providing the service' },
  { key: 'time_span', label: 'Time the service begins and ends' }
];

// Reported alongside every result so a caller cannot present this as settled
// law without also carrying what is still open. See the header.
//
// `verified` refers to THE SIX ITEMS ONLY, which are now confirmed against
// primary statutory text. It is deliberately NOT a claim that this module knows
// everything required of an EVV submission -- `residual_gaps` carries what it
// does not know, and a caller showing a green result is expected to show that
// too. Narrowing an honest disclosure is not the same as dropping it.
const FEDERAL_SOURCE = {
  authority: '42 U.S.C. § 1396b(l)(5)(A)(i)–(vi) (Social Security Act § 1903(l), added by Pub. L. 114-255 § 12006(a), Dec. 13, 2016)',
  verified: true,
  verified_on: '2026-08-27',
  verified_against: ['uscode.house.gov', 'govinfo.gov'],
  note: 'The six items are the statutory DEFINITION of a qualifying electronic visit verification system — not a required-field list. The operative requirement (§ 1396b(l)(1)) is that a State require the USE of such a system.',
  residual_gaps: [
    'CMS sub-regulatory EVV guidance has not been read (medicaid.gov and cms.gov return 403 to automated fetch). There is no EVV rulemaking, so that guidance is where CMS operational detail lives.',
    'That States may impose requirements beyond these six is an inference from statutory silence, not a quoted rule. The statute neither sets a minimum nor preempts additional State requirements.'
  ]
};

// A visit is only worth checking once it is finished. An in-progress or
// scheduled visit is not "not ready" -- it is not done, which is a different
// statement, and conflating them would fill the panel with false alarms every
// morning.
const CHECKABLE_STATUSES = ['completed'];

function nonEmpty(v) {
  return typeof v === 'string' ? v.trim().length > 0 : (v !== null && v !== undefined && v !== '');
}

// A coordinate pair is only usable if BOTH halves are real numbers. A lone
// latitude is not a location, and `0` is a valid coordinate so a truthiness
// test would silently discard the Gulf of Guinea -- unlikely for home care, but
// the bug class is the point, not the odds.
function hasCoordPair(lat, lng) {
  return typeof lat === 'number' && isFinite(lat) && typeof lng === 'number' && isFinite(lng);
}

function isIsoInstant(v) {
  return typeof v === 'string' && !isNaN(Date.parse(v));
}

// ── THE CHECK ────────────────────────────────────────────────────────────
// visit    -- a sen_visits row, flattened the way the client holds it
// client   -- the sen_clients row this visit references, or null if unresolved
// caregiver-- the sen_caregivers row for assigned_employee_id, or null
// options  -- { state } from sen_settings.evv_config, optional
//
// Returns:
//   {
//     visit_id, checkable, status,
//     ready,                       // true only when missing[] is empty
//     missing: [ {element, label, reason, fixable_in} ],
//     warnings: [ {element, label, reason} ],
//     state_rules: 'not_verified' | 'none_configured',
//     federal_source: FEDERAL_SOURCE
//   }
function checkVisit(visit, client, caregiver, options) {
  const opts = options || {};
  const v = visit || {};
  const out = {
    visit_id: v.id || null,
    status: v.status || null,
    checkable: CHECKABLE_STATUSES.indexOf(v.status) !== -1,
    ready: false,
    missing: [],
    warnings: [],
    state_rules: opts.state ? 'not_verified' : 'none_configured',
    federal_source: FEDERAL_SOURCE
  };

  // Not an error and not a failure -- just not finished. Callers filter on
  // `checkable` rather than treating this as a gap.
  if (!out.checkable) return out;

  const miss = (element, label, reason, fixable_in) => {
    out.missing.push({ element: element, label: label, reason: reason, fixable_in: fixable_in });
  };

  // 1. TYPE OF SERVICE PERFORMED
  // SAIRNsenior has no service-type field anywhere today -- verified 2026-08-27,
  // zero occurrences of service_type/hcpcs/procedure_code in sairnsenior.html,
  // and the visit modal collects only client, caregiver, date, start and end.
  // This is reported, NOT added: adding the field is a real schema + UI change
  // and is deliberately out of scope for a report-only pass. The point of
  // surfacing it per visit is to show what that change would actually cost.
  if (!nonEmpty(v.service_type)) {
    miss('service_type', 'Type of service performed',
      'No service type is recorded on this visit. SAIRNsenior does not capture one yet.',
      'visit');
  }

  // 2. INDIVIDUAL RECEIVING THE SERVICE
  if (!nonEmpty(v.client_id)) {
    miss('recipient', 'Individual receiving the service', 'This visit is not linked to a client record.', 'visit');
  } else if (!client) {
    miss('recipient', 'Individual receiving the service',
      'This visit references a client record that could not be found.', 'client');
  } else {
    if (!nonEmpty(client.name)) {
      miss('recipient', 'Individual receiving the service', 'The client record has no name.', 'client');
    }
    // A member/Medicaid identifier is what an aggregator actually matches on; a
    // name is not sufficient. SAIRNsenior does not capture one (client fields
    // are name/address/phone/payer/diagnosis/hours/tasks/status/notes/photo).
    // Reported as MISSING rather than a warning: a submission without it would
    // be rejected, so calling it advisory would be misleading.
    if (!nonEmpty(client.member_id)) {
      miss('recipient', 'Individual receiving the service',
        'No payer member/Medicaid ID on the client record. SAIRNsenior does not capture one yet.',
        'client');
    }
  }

  // 3. DATE OF THE SERVICE
  if (!nonEmpty(v.scheduled_date)) {
    miss('service_date', 'Date of the service', 'No service date is recorded.', 'visit');
  }

  // 4. LOCATION OF SERVICE DELIVERY
  // vsGetPosition() resolves null when geolocation is denied or times out at 8s
  // and the lat/lng are then simply omitted (sairnsenior.html:1195-1196,
  // :1209-1210). That behaviour is CORRECT -- the code comment at :1182 says
  // location is disclosed, never faked, and faking it would be far worse. What
  // was missing is any signal that the resulting visit cannot be submitted.
  // That signal is this check.
  const hasIn = hasCoordPair(v.clock_in_lat, v.clock_in_lng);
  const hasOut = hasCoordPair(v.clock_out_lat, v.clock_out_lng);
  if (!hasIn && !hasOut) {
    miss('location', 'Location of service delivery',
      'No GPS captured at clock-in or clock-out. Location was unavailable or permission was denied.', 'visit');
  } else if (!hasIn) {
    // Partial capture is a real, separate state. Some aggregators accept
    // clock-out-only location, some do not -- and which is which is exactly the
    // per-state/per-aggregator detail this module refuses to guess. Warned, not
    // failed, with the ambiguity named.
    out.warnings.push({ element: 'location', label: 'Location of service delivery',
      reason: 'Clock-out location captured but not clock-in. Whether a partial location is accepted depends on the aggregator and has not been verified.' });
  } else if (!hasOut) {
    out.warnings.push({ element: 'location', label: 'Location of service delivery',
      reason: 'Clock-in location captured but not clock-out. Whether a partial location is accepted depends on the aggregator and has not been verified.' });
  }

  // 5. INDIVIDUAL PROVIDING THE SERVICE
  if (!nonEmpty(v.assigned_employee_id)) {
    miss('provider', 'Individual providing the service', 'This visit has no assigned caregiver.', 'visit');
  } else if (!caregiver) {
    miss('provider', 'Individual providing the service',
      'This visit references a caregiver record that could not be found.', 'caregiver');
  } else {
    if (!nonEmpty(caregiver.name)) {
      miss('provider', 'Individual providing the service', 'The caregiver record has no name.', 'caregiver');
    }
    // Same reasoning as member_id: aggregators match a caregiver on a
    // state-assigned identifier, not a display name. Not captured today
    // (caregiver fields are name/phone/status/bgcheck/cpr/notes).
    if (!nonEmpty(caregiver.state_caregiver_id)) {
      miss('provider', 'Individual providing the service',
        'No state caregiver ID on the caregiver record. SAIRNsenior does not capture one yet.',
        'caregiver');
    }
  }

  // 6. TIME THE SERVICE BEGINS AND ENDS
  // Checked against the ACTUAL clock in/out, never the scheduled window -- EVV
  // verifies what happened, not what was planned, and substituting the schedule
  // would manufacture a compliant-looking record for a visit nobody verified.
  const inOk = isIsoInstant(v.clock_in_at);
  const outOk = isIsoInstant(v.clock_out_at);
  if (!inOk && !outOk) {
    miss('time_span', 'Time the service begins and ends', 'No clock-in or clock-out time recorded.', 'visit');
  } else if (!inOk) {
    miss('time_span', 'Time the service begins and ends', 'No clock-in time recorded.', 'visit');
  } else if (!outOk) {
    miss('time_span', 'Time the service begins and ends', 'No clock-out time recorded.', 'visit');
  } else if (Date.parse(v.clock_out_at) <= Date.parse(v.clock_in_at)) {
    // A non-positive duration is a data-integrity problem, not a missing field.
    // It is reported as missing anyway because a submission carrying it would be
    // rejected, and silently passing it would be the more expensive outcome.
    miss('time_span', 'Time the service begins and ends',
      'Clock-out is not after clock-in, so the visit has no positive duration.', 'visit');
  }

  out.ready = out.missing.length === 0;
  return out;
}

// ── ROLL-UP ──────────────────────────────────────────────────────────────
// Aggregates checkVisit across a set of visits. Returns REAL counts computed
// from real rows -- there is no estimated, annualised or partial figure
// anywhere in here, and no denominator that is not the number of rows actually
// examined.
//
// `by_element` is the number that makes the panel worth building: it answers
// "which single missing field is blocking the most visits", which is what turns
// a compliance gap into a prioritised piece of work.
function summarize(visits, clientsById, caregiversById, options) {
  const rows = Array.isArray(visits) ? visits : [];
  const clients = clientsById || {};
  const caregivers = caregiversById || {};
  const results = rows.map((v) =>
    checkVisit(v, clients[v && v.client_id] || null, caregivers[v && v.assigned_employee_id] || null, options));

  const checkable = results.filter((r) => r.checkable);
  const byElement = {};
  FEDERAL_ELEMENTS.forEach((e) => { byElement[e.key] = 0; });
  checkable.forEach((r) => {
    // One visit counts once per ELEMENT even if it has two reasons under that
    // element (e.g. missing name AND missing member ID both sit under
    // 'recipient'). Counting reasons instead would inflate the number and make
    // the worst-blocker ranking wrong.
    const seen = {};
    r.missing.forEach((m) => {
      if (!seen[m.element]) { seen[m.element] = true; byElement[m.element] += 1; }
    });
  });

  return {
    total_visits: rows.length,
    checkable: checkable.length,
    not_checkable: rows.length - checkable.length,
    ready: checkable.filter((r) => r.ready).length,
    not_ready: checkable.filter((r) => !r.ready).length,
    with_warnings: checkable.filter((r) => r.warnings.length > 0).length,
    by_element: byElement,
    elements: FEDERAL_ELEMENTS,
    state_rules: (options && options.state) ? 'not_verified' : 'none_configured',
    federal_source: FEDERAL_SOURCE,
    results: results
  };
}

module.exports = {
  FEDERAL_ELEMENTS: FEDERAL_ELEMENTS,
  FEDERAL_SOURCE: FEDERAL_SOURCE,
  CHECKABLE_STATUSES: CHECKABLE_STATUSES,
  checkVisit: checkVisit,
  summarize: summarize
};
