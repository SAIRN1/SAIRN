// api/_lib/accounting-connector.js
// SHARED read-only accounting connector: consent, scope enforcement and the
// shape of a customer's connection to their own accounting package.
//
// PURE -- no I/O, no network, no LLM. Every function here decides; the
// endpoint is what acts.
//
// ── WHY THIS EXISTS, AND WHAT IT REPLACES ────────────────────────────────
// Nothing. That is the point. A 2026-09-02 verification found that the
// platform's supposed QuickBooks integration had NEVER been on main:
// api/accounting.js was created 2026-06-16 on the unmerged lucid-ptolemy
// branch and lives only under the archive tag, /api/accounting returns 404,
// there is no connection table among the 258 in the schema snapshot, and no
// QB_* environment variable exists. Three separate places were nevertheless
// telling customers it existed. Those were corrected; this is the build that
// makes the claim true rather than removing it.
//
// The archived file was read for the raw OAuth shape and nothing else. It is
// NOT revived: it was keyed on shop_id (StoneDesk-shaped, not shared), it
// bundled Gusto payroll into the same function to fit a Vercel limit that no
// longer applies, and it predates every discipline this platform now has.
//
// ── THE THREE PROMISES THIS FILE HAS TO KEEP ─────────────────────────────
// They are product commitments, so they are enforced in code rather than
// described in a comment and hoped for.
//
//   1. READ-ONLY. This platform never writes to a customer's books. Not a
//      journal entry, not an invoice, not a customer record. Enforced by an
//      allowlist: a request is refused unless its method is GET *and* its
//      entity is on the list. A deny-list would be the wrong shape -- it
//      fails open on anything nobody thought of.
//
//   2. EXPLICIT OPT-IN PER CUSTOMER. A connection cannot exist without a
//      consent RECORD naming who agreed, when, and to which scopes. Not a
//      boolean: an opt-in you cannot prove is not an opt-in, and "we have a
//      flag set" is not an answer to a customer asking why we hold a token.
//
//   3. NEVER AUTO-CONNECT. No code path here produces an authorisation URL
//      or accepts a callback without a consent record already in hand. There
//      is deliberately no "connect all licences" or "default on" affordance,
//      and adding one later should require deleting a test.
//
// ── WHAT IT DELIBERATELY DOES NOT DO ─────────────────────────────────────
// It does not host, replace, mirror or write back to the customer's
// accounting package. It does not persist their financial records: reads are
// pass-through, so there is no second copy of somebody's ledger to leak, go
// stale, or disagree with the source. Tokens and consent are the ONLY things
// stored, and tokens never leave the server.
//
// ── AND WHAT CANNOT BE VERIFIED YET, STATED PLAINLY ──────────────────────
// There is no Intuit application and no credential in any environment. So the
// live OAuth leg -- exchanging a real code for a real token against Intuit --
// is UNTESTED and cannot be tested from here. That is exactly what the
// archived file was, and the difference is that this one says so, keeps the
// untestable part behind one narrow boundary, and puts everything else under
// test. Nothing in this module calls the network.

'use strict';

// The accounting packages this connector is designed for. QuickBooks Online
// first because it is what customers asked about; the shape is deliberately
// not QBO-specific so a second provider does not mean a second connector.
const PROVIDERS = ['quickbooks_online'];

// READ-ONLY ALLOWLIST. Entities this platform may read, and nothing else.
// Chosen for the stated product purpose -- surfacing cost-saving and
// efficiency findings -- and NOT simply "everything QuickBooks exposes".
// Payroll detail, employee records and customer PII are absent on purpose:
// the findings do not need them, and holding them would be a liability with
// no matching benefit.
const READABLE_ENTITIES = [
  'CompanyInfo',      // fiscal year start, currency: needed to read anything else correctly
  'Account',          // chart of accounts
  'Item',             // products/services, for cost-vs-price findings
  'Vendor',           // who is being paid, for spend concentration
  'Bill',             // supplier bills
  'Purchase',         // expenses
  'Invoice',          // revenue
  'Payment',          // cash in
  'ProfitAndLoss',    // report
  'BalanceSheet'      // report
];

// Scopes a customer can consent to, coarser than the entity list on purpose:
// a consent screen that lists ten API entities is a consent screen nobody
// reads. Each maps to entities below.
const SCOPES = ['financial_summary', 'expenses_and_vendors', 'revenue_and_invoices'];

const SCOPE_ENTITIES = {
  financial_summary: ['CompanyInfo', 'Account', 'ProfitAndLoss', 'BalanceSheet'],
  expenses_and_vendors: ['Vendor', 'Bill', 'Purchase'],
  revenue_and_invoices: ['Invoice', 'Payment', 'Item']
};

const CONNECTION_STATUSES = ['pending_consent', 'connected', 'revoked', 'expired', 'error'];

function str(v) { return typeof v === 'string' ? v.trim() : ''; }
function isDate(s) { return typeof s === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(s); }
function uniq(a) {
  const seen = Object.create(null), out = [];
  (Array.isArray(a) ? a : []).forEach(function (x) {
    const v = str(x);
    if (v && !seen[v]) { seen[v] = true; out.push(v); }
  });
  return out;
}

// ── Is this a consent we can act on? ─────────────────────────────────────
// Called before ANY connection step, including producing the authorisation
// URL. A consent record that is missing a field is not a weaker consent, it
// is not a consent.
function validateConsent(input) {
  input = input || {};
  const c = input.consent || null;
  const today = isDate(input.today) ? input.today : null;
  if (!today) {
    return { ok: false, error: { code: 'NO_TODAY', message: 'today (YYYY-MM-DD) is required -- this engine will not assume a clock' } };
  }
  if (!c) return { ok: false, error: { code: 'NO_CONSENT', message: 'no consent record supplied -- this platform does not connect to an accounting package without one' } };

  const problems = [];
  if (!str(c.granted_by)) problems.push('nobody is named as having granted it');
  if (!isDate(c.granted_on)) problems.push('no grant date');
  if (PROVIDERS.indexOf(str(c.provider)) === -1) problems.push('provider "' + str(c.provider) + '" is not one this connector supports');

  const asked = uniq(c.scopes);
  const unknown = asked.filter(function (s) { return SCOPES.indexOf(s) === -1; });
  // An unrecognised scope is refused rather than dropped. Silently narrowing
  // what somebody consented to is its own kind of dishonesty, and silently
  // widening it is worse.
  if (unknown.length) problems.push('unrecognised scope(s): ' + unknown.join(', '));
  if (!asked.length) problems.push('no scopes were consented to');

  if (c.revoked_on) {
    if (!isDate(c.revoked_on)) problems.push('revoked_on is not a readable date');
    else if (c.revoked_on <= today) {
      return {
        ok: true, usable: false, state: 'revoked', scopes: [], entities: [],
        reasons: ['consent was revoked on ' + c.revoked_on],
        granted_by: str(c.granted_by) || null, granted_on: isDate(c.granted_on) ? c.granted_on : null
      };
    }
  }
  if (problems.length) {
    return { ok: true, usable: false, state: 'invalid', scopes: [], entities: [], reasons: problems,
      granted_by: str(c.granted_by) || null, granted_on: isDate(c.granted_on) ? c.granted_on : null };
  }

  // Entities are DERIVED from the consented scopes, never stored on the
  // consent record. Same reasoning as entity attribution in
  // roofing-consolidation.js: a stored derivation drifts from the thing it was
  // derived from. If the scope map ever changes, existing consents follow it
  // rather than keeping yesterday's expansion.
  const entities = uniq(asked.reduce(function (acc, s) {
    return acc.concat(SCOPE_ENTITIES[s] || []);
  }, []));

  return {
    ok: true, usable: true, state: 'valid',
    provider: str(c.provider),
    granted_by: str(c.granted_by),
    granted_on: c.granted_on,
    scopes: asked,
    entities: entities,
    reasons: []
  };
}

// ── May this specific request be made? ───────────────────────────────────
// The read-only guarantee, enforced. Three independent conditions, each of
// which alone refuses: the consent must be usable, the method must be GET,
// and the entity must be both allowlisted AND inside the consented scopes.
function authoriseRead(input) {
  input = input || {};
  const v = validateConsent(input);
  if (!v.ok) return v;

  const method = str(input.method).toUpperCase() || 'GET';
  const entity = str(input.entity);
  const reasons = [];

  if (!v.usable) reasons.push(v.state === 'revoked' ? 'consent has been revoked' : 'consent is not usable: ' + v.reasons.join('; '));
  // Checked even when consent is fine, so the refusal names EVERY reason
  // rather than the first one. A caller fixing them one at a time learns the
  // rules; a caller fixing them one at a time over five deploys does not.
  if (method !== 'GET') reasons.push('method ' + method + ' is refused: this connector is read-only and never writes to a customer\'s books');
  if (!entity) reasons.push('no entity named');
  else if (READABLE_ENTITIES.indexOf(entity) === -1) reasons.push('entity "' + entity + '" is not on the read allowlist');
  else if (v.usable && v.entities.indexOf(entity) === -1) reasons.push('entity "' + entity + '" is outside the scopes this customer consented to (' + v.scopes.join(', ') + ')');

  return {
    ok: true,
    allowed: reasons.length === 0,
    entity: entity || null,
    method: method,
    reasons: reasons,
    // Carried so a caller can show WHY without a second call, and so a log
    // line can record what was consented at the moment of the request.
    consent: { granted_by: v.granted_by, granted_on: v.granted_on, scopes: v.scopes, state: v.state }
  };
}

// ── What state is this connection actually in? ───────────────────────────
// Separate from consent because they fail differently: a customer who never
// consented and a customer whose token expired need opposite messages, and
// collapsing them is how a dashboard tells somebody to "reconnect" when they
// never connected.
function connectionState(input) {
  input = input || {};
  const today = isDate(input.today) ? input.today : null;
  if (!today) {
    return { ok: false, error: { code: 'NO_TODAY', message: 'today (YYYY-MM-DD) is required -- this engine will not assume a clock' } };
  }
  const conn = input.connection || null;
  const v = validateConsent(input);
  if (!v.ok) return v;

  if (!conn) {
    return { ok: true, status: v.usable ? 'pending_consent' : 'not_connected',
      // Never "connected". A customer with a valid consent and no token has
      // agreed to something that has not happened yet.
      reason: v.usable ? 'consent is on file; the customer has not completed the connection' : 'no connection and no usable consent' };
  }
  if (!v.usable) {
    return { ok: true, status: 'revoked',
      reason: 'a connection exists but consent is ' + v.state + ' -- the token must be discarded, not merely ignored' };
  }
  const st = CONNECTION_STATUSES.indexOf(str(conn.status)) === -1 ? null : str(conn.status);
  const out = { ok: true, status: st, realm_id: str(conn.realm_id) || null, provider: str(conn.provider) || null, problems: [] };
  if (st === null) { out.status = 'error'; out.problems.push('unrecognised connection status "' + String(conn.status) + '"'); }
  // A token this platform holds but cannot refresh is not a working
  // connection, whatever the stored status says -- the same
  // live-standing-over-stored-status correction roofing-warranties.js makes.
  if (!str(conn.refresh_token_present ? 'y' : '')) {
    out.status = 'error';
    out.problems.push('no refresh token is held, so this connection cannot survive the access token expiring');
  }
  if (isDate(conn.expires_on) && conn.expires_on < today) {
    out.problems.push('the stored access token expired on ' + conn.expires_on + '; it must be refreshed before the next read');
  }
  return out;
}

module.exports = {
  PROVIDERS,
  SCOPES,
  SCOPE_ENTITIES,
  READABLE_ENTITIES,
  CONNECTION_STATUSES,
  validateConsent,
  authoriseRead,
  connectionState
};
