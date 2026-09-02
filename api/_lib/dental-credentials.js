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

// ── PAYER ENROLMENT (2026-09-02, competitive-gap audit B1) ───────────────
// The audit's own words: enterprise credentialing and payer-enrolment
// lifecycle is "the clearest whitespace in the entire dental audit -- no core
// PM vendor does it natively". Verified absent from this app before building:
// `enroll`/`enrol` 0 occurrences, `CAQH` 0, `revalidat` 0, `provider number`
// 0. What DOES exist is LICENSURE credentialing -- state licences, DEA, CE,
// BLS -- which is a different thing wearing a similar word, and conflating the
// two is the easy mistake here.
//
// A LICENCE SAYS THE DENTIST MAY PRACTISE. AN ENROLMENT SAYS A PARTICULAR
// PAYER WILL PAY THEM. A fully-licensed provider who is not yet effective with
// a plan generates claims that are denied, and the practice usually finds out
// weeks later on the remittance.
//
// IT IS A RECORD TYPE ON THE EXISTING STORE, NOT A NEW TABLE. dnt_credentials
// is already append-only, per-provider, session-gated and registered as a
// resource, and it already carries an `evaluate` action. A new table would
// have meant a schema file, a resource registration, a server branch and a
// provisioning risk, for data with the same owner, the same lifetime and the
// same access rule.
//
// NO DATE IS EVER DERIVED, the same discipline the licence half already
// states about ORC 4715.24(A): effective, termination and revalidation dates
// come from the payer's own letter and are typed in. There is deliberately no
// function here that computes an enrolment date from a payer name.
const RECORD_TYPES = {
  state_license: true,
  dea_registration: true,
  ce_cycle: true,
  certification: true,
  payer_enrollment: true
};

// Revalidation gets the platform's ordinary 30-day window rather than a cited
// one. Unlike the DEA's 60 days (21 CFR 1301.13, the earliest a renewal may be
// filed), payer revalidation cycles are set per contract and there is no
// single authority to cite -- so this reuses the existing platform threshold
// and says that is what it is.
const REVALIDATION_WARN_DAYS = DEFAULT_WARN_DAYS;

// Normalised so "Delta Dental" and "delta dental " are one payer. The same
// normalisation computeEstimatedInsurance already applies in the app, kept
// identical on purpose: an enrolment that does not match the payer the
// coverage rule matched would be worse than no check at all.
function payerKey(s) {
  return String(s == null ? '' : s).trim().toLowerCase();
}

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
          rec.record_type === 'certification' ? String(rec.credential || '') :
            // THE PAYER IS PART OF THE KEY. Without it every enrolment for one
            // provider would collapse into a single "latest", so adding a
            // Cigna record would silently retire that provider's Delta Dental
            // one -- a superseding bug in a store whose whole design is that
            // nothing is ever superseded by accident.
            rec.record_type === 'payer_enrollment' ? payerKey(rec.payer) : ''
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

// ── IS THIS PROVIDER EFFECTIVE WITH THIS PAYER ON THIS DATE? ─────────────
// The load-bearing function, and the one the market gap is actually about.
//
// FIVE ANSWERS, AND `no_record` IS THE IMPORTANT ONE. Reporting "not enrolled"
// when the practice simply has not entered the record would invent a denial;
// reporting "enrolled" would hide one. Neither is knowable from an absence, so
// the absence gets its own answer and the caller must say so. This is the same
// call the deadline engine makes on an unprovisioned calendar year: refuse to
// resolve rather than pick a side.
//
//   effective          effective_on <= date, and no term_on, or term_on >= date
//   not_yet_effective  an effective_on in the future -- the common real case,
//                      a provider seeing patients while the application is
//                      still in process
//   terminated         term_on < date
//   in_process         a record exists with a status but no effective_on
//   no_record          nothing on file for this provider and payer
//
// PURE, and evaluated against the SERVICE date rather than today, because the
// question a denied claim asks is about the day the work was done.
function enrollmentOnDate(records, query) {
  const q = query || {};
  if (!isDate(q.on_date)) return refuse('BAD_DATE', 'on_date must be YYYY-MM-DD.');
  const provider = String(q.provider_id || '');
  const payer = payerKey(q.payer);
  if (!provider) return refuse('BAD_QUERY', 'provider_id is required.');
  if (!payer) {
    // A patient with no payer recorded is self-pay or unknown; either way
    // there is no enrolment question to answer, and saying "no_record" would
    // read as a problem with the provider.
    return { ok: true, status: 'no_payer_on_file', provider_id: provider, payer: null,
      message: 'No payer is recorded, so there is no enrolment to check.' };
  }
  const rows = latestByKey(records).filter(function (r) {
    return r.record_type === 'payer_enrollment' &&
      String(r.provider_id || '') === provider && payerKey(r.payer) === payer;
  });
  if (!rows.length) {
    return { ok: true, status: 'no_record', provider_id: provider, payer: q.payer,
      message: 'No payer-enrolment record is on file for this provider with this payer. Whether the claim will be paid cannot be answered from what is stored -- this is an absence, not a finding that the provider is out of network.' };
  }
  const rec = rows[0];
  const base = {
    ok: true, provider_id: provider, payer: rec.payer || q.payer,
    entry_id: rec.entry_id || null,
    provider_number: rec.provider_number || null,
    effective_on: rec.effective_on || null,
    term_on: rec.term_on || null,
    revalidation_due_on: rec.revalidation_due_on || null,
    network_status: rec.network_status || null
  };
  if (!isDate(rec.effective_on)) {
    return Object.assign(base, { status: 'in_process',
      message: 'An enrolment record exists but carries no effective date, so this provider is not confirmed effective with this payer on ' + q.on_date + '.' });
  }
  if (rec.effective_on > q.on_date) {
    return Object.assign(base, { status: 'not_yet_effective',
      days_until_effective: daysUntil(rec.effective_on, q.on_date),
      message: 'This provider becomes effective with this payer on ' + rec.effective_on + ', which is after ' + q.on_date + '.' });
  }
  if (isDate(rec.term_on) && rec.term_on < q.on_date) {
    return Object.assign(base, { status: 'terminated',
      message: 'This provider\'s enrolment with this payer ended on ' + rec.term_on + ', before ' + q.on_date + '.' });
  }
  return Object.assign(base, { status: 'effective',
    message: 'Effective with this payer on ' + q.on_date + '.' });
}

// Charges whose provider was NOT confirmed effective with the patient's payer
// on the service date. Computed entirely from records already stored; nothing
// is written, and a charge is never blocked -- this reports what is already
// billed or about to be.
//
// `no_record` AND `no_payer_on_file` ARE REPORTED SEPARATELY FROM THE REST.
// Rolling them in would turn "we have not entered this yet" into "this claim
// will be denied", which is the fabrication this whole module avoids.
function claimsAtEnrollmentRisk(records, lines) {
  const at_risk = [], unknown = [];
  (lines || []).forEach(function (ln) {
    if (!ln || !isDate(ln.service_date)) return;
    const out = enrollmentOnDate(records, {
      provider_id: ln.provider_id, payer: ln.payer, on_date: ln.service_date
    });
    if (!out.ok) return;
    const row = {
      charge_id: ln.charge_id || null, patient_name: ln.patient_name || '',
      provider_id: ln.provider_id || '', payer: ln.payer || '',
      service_date: ln.service_date, amount: Number(ln.amount) || 0,
      status: out.status, message: out.message
    };
    if (out.status === 'not_yet_effective' || out.status === 'terminated' || out.status === 'in_process') at_risk.push(row);
    else if (out.status === 'no_record') unknown.push(row);
  });
  const sum = function (a) { return Math.round(a.reduce(function (s, r) { return s + r.amount; }, 0) * 100) / 100; };
  return {
    at_risk: at_risk.sort(function (a, b) { return b.amount - a.amount; }),
    amount_at_risk: sum(at_risk),
    unknown: unknown.sort(function (a, b) { return b.amount - a.amount; }),
    amount_unknown: sum(unknown),
    note: 'at_risk are charges where a stored enrolment record says the provider was not effective with that payer on the service date. unknown are charges with no enrolment record at all -- an absence, not a denial prediction. The two are never added together.'
  };
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

    // PAYER ENROLMENT IS NOT AN EXPIRY ROW AND IS NOT FORCED INTO ONE. A
    // licence has one date that matters; an enrolment has three -- when it
    // starts, when it ends, and when it must be revalidated -- and the state
    // that matters most (not yet effective) has no expiry at all. Running it
    // through classifyExpiry would report `unknown` for a provider whose
    // application is simply still in process, which is a real, common and
    // entirely knowable situation.
    if (rec.record_type === 'payer_enrollment') {
      const en = enrollmentOnDate([rec], { provider_id: rec.provider_id, payer: rec.payer, on_date: today });
      const reval = classifyExpiry(rec.revalidation_due_on, today, REVALIDATION_WARN_DAYS);
      const item = Object.assign(base, {
        payer: rec.payer || '',
        provider_number: rec.provider_number || null,
        network_status: rec.network_status || null,
        enrollment_status: en.ok ? en.status : 'unresolved',
        effective_on: rec.effective_on || null,
        term_on: rec.term_on || null,
        revalidation_due_on: rec.revalidation_due_on || null,
        revalidation_status: reval.status,
        revalidation_days: reval.days,
        message: en.ok ? en.message : en.error.message
      });
      // The board's own counts stay about EXPIRY, which is what its KPIs mean.
      // An enrolment contributes to them only through its revalidation date --
      // the only part of it that expires -- and a record with no revalidation
      // date on file counts as unknown rather than ok, because "we did not
      // enter one" is not "there isn't one".
      item.status = reval.status;
      counts[reval.status]++;
      items.push(item);
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
  credentialCoverage,
  REVALIDATION_WARN_DAYS,
  payerKey,
  enrollmentOnDate,
  claimsAtEnrollmentRisk
};
