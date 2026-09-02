// api/_lib/credential-expiry.js
//
// The primitives every SAIRN credential engine shares. PURE -- no I/O.
//
// ── WHY THIS EXISTS, AND WHY NOT SOONER ─────────────────────────────────────
// api/_lib/dental-credentials.js, api/_lib/roofing-credentials.js and
// api/_lib/mech-credentials.js each carried their own copy of isDate,
// daysUntil, ruleInForce and the expiry-boundary arithmetic.
// roofing-credentials.js named that cost in its own header and deferred the
// extraction on a stated condition:
//
//     "Revisit the extraction after 3c, when both shapes have stopped moving,
//      with the dental test suites as the proof they stayed identical."
//
// Roofing 3c has shipped and mechanical made it three copies, so the condition
// is met. This is that extraction, done as its own task rather than folded
// into either app's feature work.
//
// ── WHAT IS DELIBERATELY *NOT* EXTRACTED, AND WHY ───────────────────────────
// Reading the three side by side is the whole value of doing this, and they do
// NOT agree. A blanket extraction would have silently changed behaviour:
//
//   classify*  -- THREE DIFFERENT CONTRACTS.
//     dental    classifyExpiry(expiresOn, today, w) takes a DATE and returns
//               unknown | expired | expiring | ok. Dentistry has no lifetime
//               credential, so it has no 'current' and no no_expiry flag.
//     roofing   classifyRecord(rec, today, w) takes a RECORD and returns FIVE
//               states: 'current' means "valid and does NOT expire", 'ok'
//               means "valid, expires, not near it".
//     mechanical classifyRecord(rec, today, w) returns FOUR: 'current' covers
//               BOTH of roofing's 'current' and 'ok'.
//
//   So 'current' means different things in two live apps. That is a real
//   platform inconsistency and it is recorded here rather than resolved by
//   fiat: reconciling it changes what two shipped UIs display, which is a
//   product decision, not a refactor. Each app keeps its own wrapper and its
//   own vocabulary; only the arithmetic underneath is shared.
//
//   latestByKey -- also genuinely different. Roofing keys on
//     (employee_id, record_type, credential|jurisdiction) and ranks by
//     recorded_at then entry_id, and DROPS unknown record types. Mechanical
//     keys on (technician_id, record_type, epa_section|jurisdiction) and ranks
//     by issued_on. Parameterised here as latestBy(records, keyOf, rankOf)
//     rather than unified, because the difference is the data model, not an
//     accident.
//
// ── SCOPE OF THE REPOINT ────────────────────────────────────────────────────
// roofing-credentials.js and mech-credentials.js are repointed onto this.
// dental-credentials.js is NOT, deliberately: it is a third live app, its
// classifyExpiry takes a different argument shape entirely, and touching it
// was not part of this task. Its copies of isDate/daysUntil/ruleInForce are
// byte-identical to these and it is the obvious next candidate -- named here
// so the next person inherits the fact rather than rediscovering it.
//
// ── THE CONTRACT THIS MUST NOT BREAK ────────────────────────────────────────
// Nothing observable changes. Both apps' existing test suites are the proof,
// and they were run before and after with identical results.

'use strict';

// Platform-standard "expiring soon" window. sairncare.html, sairnbuild.html
// and all three credential engines already used 30 independently; this is the
// first place it is written once.
const DEFAULT_WARN_DAYS = 30;

function refuse(code, message, extra) {
  return Object.assign({ ok: false, error: { code: code, message: message } }, extra || {});
}

function isDate(s) {
  return typeof s === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(s);
}

// Whole days from `today` to `dateStr`. Negative = already past.
// UTC midnight on both sides so a run at 23:00 and a run at 01:00 agree, and
// so a licence does not expire an hour early for someone in another timezone.
function daysUntil(dateStr, today) {
  if (!isDate(dateStr) || !isDate(today)) return null;
  const a = Date.UTC(+dateStr.slice(0, 4), +dateStr.slice(5, 7) - 1, +dateStr.slice(8, 10));
  const b = Date.UTC(+today.slice(0, 4), +today.slice(5, 7) - 1, +today.slice(8, 10));
  return Math.round((a - b) / 86400000);
}

// The expiry boundary, in one place. Returns 'unknown' | 'expired' |
// 'expiring' | 'valid' -- deliberately NOT any app's vocabulary, so no caller
// can accidentally inherit another app's meaning of 'current' or 'ok'. Each
// engine maps this onto its own words.
//
// The boundary is INCLUSIVE at warnDays: exactly warnDays out is already
// 'expiring', because the day a renewal window opens is a day to act on, not
// the day after. All three engines already agreed on this; it is now asserted
// in one place instead of three.
function classifyDays(days, warnDays) {
  const w = typeof warnDays === 'number' && Number.isFinite(warnDays) ? warnDays : DEFAULT_WARN_DAYS;
  if (days === null || days === undefined) return { status: 'unknown', days: null, warn_days: w };
  if (days < 0) return { status: 'expired', days: days, warn_days: w };
  if (days <= w) return { status: 'expiring', days: days, warn_days: w };
  return { status: 'valid', days: days, warn_days: w };
}

// A rule is in force on a date if it has started, has not ended, and is not
// marked inactive. Byte-identical in dental and roofing before this; mechanical
// has no rule table and does not use it.
function ruleInForce(rule, onDate) {
  if (!rule || !rule.effective_from) return false;
  if (rule.status && rule.status !== 'active') return false;
  if (!isDate(onDate)) return false;
  if (rule.effective_from > onDate) return false;
  if (rule.effective_to && rule.effective_to < onDate) return false;
  return true;
}

// Append-only supersede. `keyOf(rec)` decides what counts as the same record;
// `rankOf(prev, next)` returns true when `next` should replace `prev`.
//
// Parameterised rather than unified because the two callers genuinely differ:
// roofing ranks by recorded_at then entry_id and drops unknown record types,
// mechanical ranks by issued_on. Forcing one shape would have changed which
// row a live board displays.
function latestBy(records, keyOf, rankOf) {
  const best = Object.create(null);
  (Array.isArray(records) ? records : []).forEach(function (rec) {
    if (!rec || typeof rec !== 'object') return;
    const key = keyOf(rec);
    if (key === null || key === undefined) return;   // keyOf may reject a record
    const prev = best[key];
    if (!prev || rankOf(prev, rec)) best[key] = rec;
  });
  return Object.keys(best).map(function (k) { return best[k]; });
}

module.exports = {
  DEFAULT_WARN_DAYS,
  refuse,
  isDate,
  daysUntil,
  classifyDays,
  ruleInForce,
  latestBy
};
