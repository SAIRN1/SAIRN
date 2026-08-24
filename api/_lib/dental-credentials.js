// api/_lib/dental-credentials.js
// SAIRNdental licensing / credentialing engine.
//
// PURE -- no I/O. Same shape and same reasoning as api/_lib/compliance-rules.js
// (SAIRNcare Phase 2) and api/_lib/payer-routing.js: requirements arrive as
// versioned data with a real citation, this module only evaluates them, so
// every branch is testable against the statute text without a database.
//
// FAILS CLOSED. An unseeded state gets NO_RULE_FOR_STATE naming the state, and
// an unseeded role within a seeded state gets NO_RULE_FOR_ROLE naming the role.
// Neither is ever silently substituted with another state's numbers. Ohio is
// the only seeded state as of 2026-08-24; a two-state practice must not be
// shown Ohio's thirty hours for its other state's licence.
//
// ── THE ONE FINDING THAT SHAPED THIS FILE ────────────────────────────────
// ORC 4715.24(A), read verbatim: "A license expires on the date that is two
// years from the date of issuance and may be registered for additional
// two-year periods." That is a PER-LICENSEE ANNIVERSARY, not a statewide
// calendar date. Secondary sources variously claim "December 31 of odd years"
// and "December 31 of even years" -- they disagree with each other and with
// the statute. So every expiry in here is READ FROM THE RECORD the practice
// entered, never derived from a state-wide date. There is deliberately no
// function in this file that computes an expiration date from a state.
//
// ── THRESHOLDS ARE CITED, NOT PICKED ─────────────────────────────────────
// 30 days is the existing platform threshold, unchanged: sairncare.html and
// sairnbuild.html both render "Expiring Soon ... Within 30 days" off the same
// certDaysUntil()/complianceDaysUntil() shape. Reused rather than reinvented.
//
// 60 days for DEA specifically is NOT a preference. 21 CFR 1301.13 states a
// registrant "may apply to be reregistered not more than 60 days before the
// expiration date of his/her registration" -- 60 days is the first day the
// renewal can actually be filed, so warning earlier would tell a dentist to do
// something the government will not yet accept.
//
// CE gets NO day threshold at all. Ohio requires thirty hours biennially
// (ORC 4715.141(A)); thirty hours cannot be earned in thirty days. CE is paced
// -- hours remaining against time remaining -- so a dentist who has logged
// nothing eighteen months into a two-year cycle is flagged while a dentist who
// is simply near the end but finished is not.

'use strict';

// Platform-standard "expiring soon" window, matching SAIRNcare/SAIRNbuild.
const DEFAULT_WARN_DAYS = 30;
// 21 CFR 1301.13: the earliest a DEA renewal may be filed.
const DEA_WARN_DAYS = 60;

const RECORD_TYPES = {
  state_license: true,
  dea_registration: true,
  ce_cycle: true,
  certification: true
};

function refuse(code, message, extra) {
  return Object.assign({ ok: false, error: { code: code, message: message } }, extra || {});
}

function isDate(s) {
  return typeof s === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(s);
}

// Whole days from `today` to `dateStr`. Negative = already past.
// UTC midnight on both sides so a run at 23:00 and a run at 01:00 agree.
function daysUntil(dateStr, today) {
  if (!isDate(dateStr) || !isDate(today)) return null;
  const a = Date.UTC(+dateStr.slice(0, 4), +dateStr.slice(5, 7) - 1, +dateStr.slice(8, 10));
  const b = Date.UTC(+today.slice(0, 4), +today.slice(5, 7) - 1, +today.slice(8, 10));
  return Math.round((a - b) / 86400000);
}

// expired | expiring | ok | unknown, plus the day count that decided it.
// Boundary is INCLUSIVE: exactly warnDays out is already "expiring", because
// the day the renewal window opens is a day to act on, not the day after.
function classifyExpiry(expiresOn, today, warnDays) {
  const w = typeof warnDays === 'number' ? warnDays : DEFAULT_WARN_DAYS;
  const days = daysUntil(expiresOn, today);
  if (days === null) return { status: 'unknown', days: null, warn_days: w };
  if (days < 0) return { status: 'expired', days: days, warn_days: w };
  if (days <= w) return { status: 'expiring', days: days, warn_days: w };
  return { status: 'ok', days: days, warn_days: w };
}

function warnDaysFor(recordType) {
  return recordType === 'dea_registration' ? DEA_WARN_DAYS : DEFAULT_WARN_DAYS;
}

// ── Requirement lookup ───────────────────────────────────────────────────
function ruleInForce(rule, onDate) {
  if (!rule || !rule.effective_from) return false;
  if (rule.status && rule.status !== 'active') return false;
  if (!isDate(onDate)) return false;
  if (rule.effective_from > onDate) return false;
  if (rule.effective_to && rule.effective_to < onDate) return false;
  return true;
}

// The CE rule for one state + role. Fails closed, loudly, on both axes.
function selectCeRule(rules, opts) {
  const state = String((opts && opts.state) || '').toUpperCase();
  const role = String((opts && opts.role) || '').toLowerCase();
  const onDate = (opts && opts.on_date) || '';

  const inState = (rules || []).filter(function (r) {
    return String(r.state || '').toUpperCase() === state;
  });
  if (!inState.length) {
    return refuse('NO_RULE_FOR_STATE',
      'No dental CE requirements are loaded for ' + (state || '(no state given)') +
      '. This state is not covered -- do not rely on this app for its requirements ' +
      'until real, sourced rules are loaded.');
  }
  const forRole = inState.filter(function (r) {
    return r.requirement_type === 'continuing_education' &&
      String(r.role || '').toLowerCase() === role &&
      ruleInForce(r, onDate);
  });
  if (!forRole.length) {
    return refuse('NO_RULE_FOR_ROLE',
      'No continuing-education rule in force on ' + onDate + ' for role "' +
      (role || '(none given)') + '" in ' + state + '. Ohio states different hour ' +
      'totals for dentists and hygienists, so one role\'s figure must never stand ' +
      'in for another\'s.');
  }
  // Latest effective_from wins if a state has superseding versions.
  forRole.sort(function (a, b) { return a.effective_from < b.effective_from ? 1 : -1; });
  return { ok: true, rule: forRole[0] };
}

// ── CE pacing ────────────────────────────────────────────────────────────
// complete | overdue | behind | on_track, with the arithmetic exposed so the
// UI never has to recompute (and so a wrong number is visible in a test).
//
// "behind" compares the fraction of the cycle elapsed against the fraction of
// hours earned. It is a PACE signal, not a compliance verdict: being behind
// pace breaks no rule, and the copy must not say it does. Missing the hours at
// cycle end does.
function evaluateCeCycle(cycle, today) {
  if (!cycle || !isDate(cycle.cycle_start) || !isDate(cycle.cycle_end)) {
    return refuse('BAD_CYCLE', 'A CE cycle needs a real cycle_start and cycle_end (YYYY-MM-DD).');
  }
  if (!isDate(today)) return refuse('BAD_DATE', 'today must be YYYY-MM-DD.');
  if (cycle.cycle_end < cycle.cycle_start) {
    return refuse('BAD_CYCLE', 'cycle_end is before cycle_start.');
  }
  const required = Number(cycle.hours_required);
  const logged = Number(cycle.hours_logged || 0);
  if (!isFinite(required) || required < 0) {
    return refuse('BAD_CYCLE', 'hours_required must be a non-negative number.');
  }
  if (!isFinite(logged) || logged < 0) {
    return refuse('BAD_CYCLE', 'hours_logged must be a non-negative number.');
  }

  const hoursRemaining = Math.max(0, required - logged);
  const daysRemaining = daysUntil(cycle.cycle_end, today);
  const cycleDays = daysUntil(cycle.cycle_end, cycle.cycle_start);
  const daysElapsed = cycleDays - daysRemaining;

  let status;
  if (hoursRemaining === 0) {
    status = 'complete';
  } else if (daysRemaining < 0) {
    status = 'overdue';
  } else {
    // Guard a zero-length cycle rather than dividing by it.
    const timeFraction = cycleDays > 0 ? Math.min(1, Math.max(0, daysElapsed / cycleDays)) : 1;
    const hoursFraction = required > 0 ? Math.min(1, logged / required) : 1;
    status = hoursFraction < timeFraction ? 'behind' : 'on_track';
  }

  return {
    ok: true,
    status: status,
    hours_required: required,
    hours_logged: logged,
    hours_remaining: hoursRemaining,
    days_remaining: daysRemaining,
    cycle_days: cycleDays,
    days_elapsed: daysElapsed
  };
}

// ── The alert board ──────────────────────────────────────────────────────
// One pass over every stored credential row, producing per-record status plus
// the counts the panel's KPIs render. Records are append-only, so only the
// LATEST row per (provider_id, record_type, subject_key) is evaluated -- an
// earlier, superseded licence row must not keep firing as expired forever.
function latestByKey(records) {
  const best = Object.create(null);
  (records || []).forEach(function (rec) {
    if (!rec || !RECORD_TYPES[rec.record_type]) return;
    const key = [
      rec.provider_id || '',
      rec.record_type,
      rec.record_type === 'state_license' ? String(rec.state || '').toUpperCase() :
        rec.record_type === 'ce_cycle' ? String(rec.cycle_start || '') :
          rec.record_type === 'certification' ? String(rec.credential || '') : ''
    ].join('|');
    const prev = best[key];
    // recorded_at is server-stamped; entry_id is the tiebreak so the result is
    // deterministic even if two rows share a timestamp.
    if (!prev ||
      String(rec.recorded_at || '') > String(prev.recorded_at || '') ||
      (String(rec.recorded_at || '') === String(prev.recorded_at || '') &&
        String(rec.entry_id || '') > String(prev.entry_id || ''))) {
      best[key] = rec;
    }
  });
  return Object.keys(best).map(function (k) { return best[k]; });
}

function evaluateBoard(records, rules, today) {
  if (!isDate(today)) return refuse('BAD_DATE', 'today must be YYYY-MM-DD.');

  const current = latestByKey(records);
  const items = [];
  const counts = { expired: 0, expiring: 0, ok: 0, unknown: 0 };
  const ce = { complete: 0, on_track: 0, behind: 0, overdue: 0, unresolved: 0 };
  let mateOutstanding = 0;

  current.forEach(function (rec) {
    const base = {
      entry_id: rec.entry_id,
      provider_id: rec.provider_id,
      record_type: rec.record_type,
      label: rec.label || ''
    };

    if (rec.record_type === 'ce_cycle') {
      // hours_required comes from the seeded rule when the record does not
      // carry its own -- and if neither has it, the cycle is reported
      // unresolved rather than silently assigned a number.
      let required = rec.hours_required;
      let sourced_from = 'record';
      let ruleRef = null;
      if (required === undefined || required === null || required === '') {
        const sel = selectCeRule(rules, { state: rec.state, role: rec.role, on_date: today });
        if (!sel.ok) {
          ce.unresolved++;
          items.push(Object.assign(base, {
            status: 'unresolved',
            reason: sel.error.code,
            message: sel.error.message
          }));
          return;
        }
        required = sel.rule.data && sel.rule.data.hours_required;
        sourced_from = 'rule:' + sel.rule.rule_id;
        ruleRef = sel.rule.rule_id;
      }
      const out = evaluateCeCycle({
        cycle_start: rec.cycle_start,
        cycle_end: rec.cycle_end,
        hours_required: required,
        hours_logged: rec.hours_logged
      }, today);
      if (!out.ok) {
        ce.unresolved++;
        items.push(Object.assign(base, {
          status: 'unresolved', reason: out.error.code, message: out.error.message
        }));
        return;
      }
      ce[out.status]++;
      items.push(Object.assign(base, out, {
        ok: undefined, hours_required_from: sourced_from, rule_id: ruleRef
      }));
      return;
    }

    const warn = warnDaysFor(rec.record_type);
    const cls = classifyExpiry(rec.expires_on, today, warn);
    counts[cls.status]++;
    const item = Object.assign(base, {
      status: cls.status,
      days: cls.days,
      warn_days: cls.warn_days,
      expires_on: rec.expires_on || null
    });

    if (rec.record_type === 'dea_registration') {
      // MATE Act: "at least 8 hours of training", "a one-time attestation"
      // (DEA MATE Act FAQ), required of all DEA-registered practitioners
      // except solely-veterinarians, since June 27 2023. Not an expiring
      // credential -- it is attested once, at the next registration
      // submission -- so it is reported alongside the registration rather
      // than as its own expiry row.
      item.mate_attested = rec.mate_attested === true;
      item.mate_attested_on = rec.mate_attested_on || null;
      if (!item.mate_attested) mateOutstanding++;
    }
    items.push(item);
  });

  // Most urgent first: expired, then soonest expiry, then everything else.
  const rank = { expired: 0, expiring: 1, unknown: 2, ok: 3, overdue: 0, behind: 1, unresolved: 2, on_track: 3, complete: 4 };
  items.sort(function (a, b) {
    const ra = rank[a.status] === undefined ? 5 : rank[a.status];
    const rb = rank[b.status] === undefined ? 5 : rank[b.status];
    if (ra !== rb) return ra - rb;
    const da = a.days === null || a.days === undefined ? 1e9 : a.days;
    const db = b.days === null || b.days === undefined ? 1e9 : b.days;
    return da - db;
  });

  return {
    ok: true,
    as_of: today,
    counts: counts,
    ce: ce,
    mate_outstanding: mateOutstanding,
    action_required: counts.expired + counts.expiring + ce.overdue + mateOutstanding,
    items: items
  };
}

// Which states this practice has real, sourced rules for. Same honest-gap
// reporting as complianceCoverage() in api/_lib/compliance-rules.js.
function credentialCoverage(rules, claimedStates) {
  const have = {};
  (rules || []).forEach(function (r) {
    const s = String(r.state || '').toUpperCase();
    if (!s) return;
    have[s] = have[s] || [];
    have[s].push(r.rule_id);
  });
  const claimed = (claimedStates || []).map(function (s) { return String(s).toUpperCase(); });
  const uncovered = claimed.filter(function (s) { return !have[s]; });
  return {
    covered_states: Object.keys(have).sort(),
    uncovered_states: uncovered,
    detail: Object.keys(have).sort().map(function (s) { return { state: s, rule_ids: have[s].sort() }; })
  };
}

module.exports = {
  DEFAULT_WARN_DAYS,
  DEA_WARN_DAYS,
  RECORD_TYPES,
  daysUntil,
  classifyExpiry,
  warnDaysFor,
  ruleInForce,
  selectCeRule,
  evaluateCeCycle,
  latestByKey,
  evaluateBoard,
  credentialCoverage
};
