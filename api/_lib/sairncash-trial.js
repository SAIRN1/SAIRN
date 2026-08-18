// api/_lib/sairncash-trial.js
// Pure trial-expiry/validity logic for SAIRNcash's 30-day free trial --
// no network/DB access, testable in isolation (sairncash-trial.test.js).
// Extracted so trial-start.js, trial-verify.js, and trial-renew.js all
// share one real computation instead of three copies that could drift.
// See docs/superpowers/specs/2026-08-18-sairncash-trial-flow-design.md.

var THIRTY_DAYS_MS = 30 * 24 * 60 * 60 * 1000;

function computeExpiry(startMs) {
  return new Date(startMs + THIRTY_DAYS_MS).toISOString();
}

function isTrialValid(row, nowMs) {
  if (!row || row.status === 'revoked') return false;
  return new Date(row.expires_at).getTime() > nowMs;
}

function daysLeft(expiresAtIso, nowMs) {
  var remainingMs = new Date(expiresAtIso).getTime() - nowMs;
  if (remainingMs <= 0) return 0;
  return Math.ceil(remainingMs / (24 * 60 * 60 * 1000));
}

module.exports = { computeExpiry: computeExpiry, isTrialValid: isTrialValid, daysLeft: daysLeft };
