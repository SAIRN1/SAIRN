// api/_lib/fail-closed-mode.js
// ---------------------------------------------------------------------------
// RESOLVING AN observe/enforce FLAG, FAILING CLOSED.
//
// CONCEPT, stated before this file existed (docs/2026-10-20-hank-b25-notes.md):
//   A control whose setting is MISSING or MISSPELLED must refuse, not permit.
//   `observe` and `enforce` are the only two answers either flag has, and
//   anything else -- absent, empty, whitespace, a typo, a value from a newer
//   version of this code -- is a configuration nobody made, and is treated as
//   `enforce`.
//
// ── WHY THIS IS A FILE AND NOT TWO COPIES OF ONE LINE ─────────────────────
// Two controls read a flag of this shape and BOTH defaulted permissive:
//
//   api/claude.js        String(process.env.SAIRN_CLAUDE_AUTH_MODE || 'observe')
//   api/_lib/ai-rate-limit.js
//                        String(process.env.SAIRN_AI_RATE_LIMIT_MODE || '')
//                          .toLowerCase() === 'enforce'
//
// Both are one line, both are obviously correct in isolation, and both have
// the same two holes: an ABSENT variable permits, and so does a MISSPELLED
// one, because every spelling that is not exactly `enforce` falls into the
// same branch as `observe`. A second copy of this reasoning is a second place
// for it to drift, which is the defect class this repo has paid for in seven
// `strip_comments` implementations.
//
// ── THE THREE ANSWERS, AND THE THIRD IS THE POINT ─────────────────────────
//   'observe'  the operator set it, in as many words. Nothing is refused.
//   'enforce'  the operator set it. The control bites.
//   anything else -> 'enforce', AND `configured: false` so the caller can SAY
//              SO. A control that silently hardened is as hard to operate as
//              one that silently relaxed; the log line is what makes the
//              difference reportable.
//
// ── WHAT THIS IS NOT ──────────────────────────────────────────────────────
// It is NOT the "could not read the store" axis. A rate limiter that cannot
// reach its counter is DEGRADED and may legitimately fail open -- that is a
// measurement failure, not a configuration one, and `api/_lib/ai-rate-limit.js`
// keeps its own answer for it. This file answers one question only: what did
// the operator ask for, and did they actually ask.
// ---------------------------------------------------------------------------

'use strict';

const OBSERVE = 'observe';
const ENFORCE = 'enforce';

/**
 * @param {string} name  the env var's name, for the caller's log line
 * @param {*} raw        process.env[name], passed in rather than read here so
 *                       a test can drive it without mutating the environment
 * @returns {{mode:'observe'|'enforce', configured:boolean, raw:string,
 *            reason:string|null}}
 */
function resolveMode(name, raw) {
  const s = (raw === undefined || raw === null) ? '' : String(raw).trim().toLowerCase();
  if (s === OBSERVE) return { mode: OBSERVE, configured: true, raw: s, reason: null };
  if (s === ENFORCE) return { mode: ENFORCE, configured: true, raw: s, reason: null };
  return {
    mode: ENFORCE,
    configured: false,
    raw: s,
    reason: s === ''
      ? name + ' is NOT SET, so this control is ENFORCING. An absent flag is '
        + 'not permission -- set it to "observe" in as many words if that is '
        + 'what you want.'
      : name + ' is "' + s.slice(0, 40) + '", which is neither "observe" nor '
        + '"enforce", so this control is ENFORCING. A misspelled flag used to '
        + 'read as "observe" because every value that is not exactly "enforce" '
        + 'fell into the same branch.'
  };
}

/** Convenience: is this control biting? */
function isEnforcing(name, raw) {
  return resolveMode(name, raw).mode === ENFORCE;
}

module.exports = { resolveMode, isEnforcing, OBSERVE, ENFORCE };
