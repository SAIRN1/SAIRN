// api/_lib/roofing-credentials.js
// SAIRNroofing Phase 3a -- per-employee certifications and licensing.
//
// PURE -- no I/O. Same shape and same reasoning as api/_lib/dental-credentials.js
// and api/_lib/compliance-rules.js: requirements arrive as versioned data with a
// real citation, this module only evaluates them.
//
// ── DUPLICATION WITH dental-credentials.js, DELIBERATE FOR NOW ───────────
// daysUntil/classifyExpiry/latestByKey/ruleInForce are near-identical between
// this file and api/_lib/dental-credentials.js, and that is a real cost, named
// rather than hidden. Extracting them was considered and NOT done as part of
// 3a: SAIRNdental shipped and was live-verified hours ago, and refactoring it
// is orthogonal to "build roofing certifications" -- every changed line should
// trace to the request. The two shapes also differ in ways that would make a
// premature shared abstraction wrong (see NO-EXPIRY below; dentistry has no
// equivalent). Revisit the extraction after 3c, when both shapes have stopped
// moving, with the dental test suites as the proof they stayed identical.
//
// ── NO-EXPIRY IS A FIRST-CLASS STATE, NOT A MISSING FIELD ────────────────
// The finding that shaped this file. An OSHA 10/30 Outreach card has NO federal
// expiration -- OSHA does not place one on the card. Expiry comes from a state,
// a general contractor, or an owner: NY (Labor Law 220-h), CT, MO and NV impose
// refresh windows, and large GCs commonly require a card issued within five
// years.
//
// So a record carries has_expiry explicitly. `has_expiry:false` yields status
// 'current' -- a positive, correct answer -- while a MISSING expiry date on a
// record that should have one yields 'unknown'. Collapsing those two into a
// null date would report a valid lifetime card as incomplete data, and would
// hide a genuinely missing renewal date behind the same symbol.
//
// ── FAILS CLOSED ─────────────────────────────────────────────────────────
// Ohio is the only seeded state. An unseeded state gets NO_RULE_FOR_STATE
// naming the state; nothing borrows Ohio's answer. That matters more here than
// in dentistry, because Ohio's answer is "no state licence exists" -- and
// applying that to, say, California, would tell a contractor they need no
// licence in a state that heavily regulates roofing.

'use strict';

// Platform-standard "expiring soon" window (sairncare.html, sairnbuild.html,
// and api/_lib/dental-credentials.js all use 30).
const DEFAULT_WARN_DAYS = 30;

const RECORD_TYPES = {
  osha_card: true,          // OSHA 10 / 30-hour Outreach card
  safety_training: true,    // fall protection, ladder, competent-person, etc.
  installer_cert: true,     // manufacturer per-installer cert (Tesla Certified)
  local_license: true       // municipal/county registration where required
};

// EXTRACTED 2026-09-02, on the condition this file's own header set: "revisit
// after 3c, when both shapes have stopped moving". 3c has shipped and
// mech-credentials.js made it three copies. Only the arithmetic moved --
// classifyRecord's FIVE-state vocabulary below is unchanged and stays this
// app's, because mechanical's 'current' means something narrower and
// reconciling them would change what a shipped board displays. See the header
// of api/_lib/credential-expiry.js.
const shared = require('./credential-expiry');

const refuse = shared.refuse;
const isDate = shared.isDate;
const daysUntil = shared.daysUntil;

// current | expired | expiring | ok | unknown.
//
// 'current' means "valid and does not expire" -- an answer, not an absence.
// 'unknown' means "this record should carry an expiry and does not".
// Boundary is INCLUSIVE at warnDays, matching the platform.
function classifyRecord(rec, today, warnDays) {
  const w = typeof warnDays === 'number' ? warnDays : DEFAULT_WARN_DAYS;
  if (rec && rec.has_expiry === false) {
    return { status: 'current', days: null, warn_days: w, no_expiry: true };
  }
  // Shared arithmetic, this app's vocabulary. The primitive answers 'valid'
  // and deliberately never any app's word: mapping it to 'ok' HERE is what
  // keeps roofing's five-state contract ('current' = lifetime, 'ok' = valid
  // and dated) from silently becoming mechanical's four-state one.
  const c = shared.classifyDays(daysUntil(rec && rec.expires_on, today), w);
  return {
    status: c.status === 'valid' ? 'ok' : c.status,
    days: c.days,
    warn_days: c.warn_days,
    no_expiry: false
  };
}

// Was byte-identical to dental's copy. dental-credentials.js still carries its
// own and is NOT repointed here -- a third live app was outside this task --
// which makes it the obvious next candidate rather than a forgotten one.
const ruleInForce = shared.ruleInForce;

// Licensing answer for one state. Federal rules (state 'US') are returned
// separately and always apply -- they are not a substitute for a state answer.
function selectLicensingRule(rules, opts) {
  const state = String((opts && opts.state) || '').toUpperCase();
  const onDate = (opts && opts.on_date) || '';
  const inState = (rules || []).filter(function (r) {
    return String(r.state || '').toUpperCase() === state &&
      r.requirement_type === 'state_licensing' && ruleInForce(r, onDate);
  });
  if (!inState.length) {
    return refuse('NO_RULE_FOR_STATE',
      'No roofing licensing rule is loaded for ' + (state || '(no state given)') +
      '. This state is not covered -- do not rely on this app for its ' +
      'requirements until real, sourced rules are loaded. Ohio\'s answer in ' +
      'particular must never be reused: Ohio licenses no roofing trade at the ' +
      'state level, and applying that to a state which does would tell a ' +
      'contractor they need no licence when they do.');
  }
  inState.sort(function (a, b) { return a.effective_from < b.effective_from ? 1 : -1; });
  return { ok: true, rule: inState[0] };
}

function federalRules(rules, onDate) {
  return (rules || []).filter(function (r) {
    return String(r.state || '').toUpperCase() === 'US' && ruleInForce(r, onDate);
  });
}

// Append-only: only the LATEST row per (employee, type, subject) is evaluated.
function latestByKey(records) {
  // Shared supersede, this app's key and ranking. keyOf returns null for an
  // unknown record type, which the shared helper treats as "not a record" --
  // preserving this function's original behaviour of DROPPING them rather than
  // grouping them under an empty key.
  //
  // Parameterised rather than unified with mechanical's, which keys on
  // (technician_id, type, epa_section|jurisdiction) and ranks by issued_on.
  // Forcing one shape would change which row a live board displays.
  return shared.latestBy(
    records,
    function (rec) {
      if (!RECORD_TYPES[rec.record_type]) return null;
      return [
        rec.employee_id || '',
        rec.record_type,
        String(rec.credential || rec.jurisdiction || '')
      ].join('|');
    },
    function (prev, rec) {
      return String(rec.recorded_at || '') > String(prev.recorded_at || '') ||
        (String(rec.recorded_at || '') === String(prev.recorded_at || '') &&
          String(rec.entry_id || '') > String(prev.entry_id || ''));
    }
  );
}

function evaluateBoard(records, rules, today) {
  if (!isDate(today)) return refuse('BAD_DATE', 'today must be YYYY-MM-DD.');

  const current = latestByKey(records);
  const counts = { expired: 0, expiring: 0, ok: 0, current: 0, unknown: 0 };
  const items = [];

  current.forEach(function (rec) {
    const cls = classifyRecord(rec, today, DEFAULT_WARN_DAYS);
    counts[cls.status]++;
    items.push({
      entry_id: rec.entry_id,
      employee_id: rec.employee_id,
      record_type: rec.record_type,
      credential: rec.credential || '',
      jurisdiction: rec.jurisdiction || '',
      issuer: rec.issuer || '',
      issued_on: rec.issued_on || null,
      expires_on: rec.expires_on || null,
      status: cls.status,
      days: cls.days,
      warn_days: cls.warn_days,
      no_expiry: cls.no_expiry
    });
  });

  const rank = { expired: 0, expiring: 1, unknown: 2, ok: 3, current: 4 };
  items.sort(function (a, b) {
    const ra = rank[a.status], rb = rank[b.status];
    if (ra !== rb) return ra - rb;
    const da = a.days === null ? 1e9 : a.days;
    const db = b.days === null ? 1e9 : b.days;
    return da - db;
  });

  return {
    ok: true,
    as_of: today,
    counts: counts,
    // 'unknown' is action_required: a record that should carry a renewal date
    // and does not is a real gap, not a cosmetic one.
    action_required: counts.expired + counts.expiring + counts.unknown,
    items: items
  };
}

function credentialCoverage(rules, claimedStates) {
  const have = {};
  (rules || []).forEach(function (r) {
    const s = String(r.state || '').toUpperCase();
    if (!s) return;
    have[s] = have[s] || [];
    have[s].push(r.rule_id);
  });
  const claimed = (claimedStates || []).map(function (s) { return String(s).toUpperCase(); });
  return {
    covered_states: Object.keys(have).sort(),
    uncovered_states: claimed.filter(function (s) { return !have[s]; }),
    detail: Object.keys(have).sort().map(function (s) { return { state: s, rule_ids: have[s].sort() }; })
  };
}

module.exports = {
  DEFAULT_WARN_DAYS,
  RECORD_TYPES,
  daysUntil,
  classifyRecord,
  ruleInForce,
  selectLicensingRule,
  federalRules,
  latestByKey,
  evaluateBoard,
  credentialCoverage
};
