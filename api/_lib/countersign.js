// api/_lib/countersign.js
// ---------------------------------------------------------------------------
// THE COUNTERSIGNATURE LOCK, ONE MECHANISM, TWO APPS.
//
// Not a checker that flags a bad write and not a gate that blocks a push: a
// HARD WORKFLOW LOCK. The write cannot fire at all until a DIFFERENT,
// currently-active, qualified employee has signed that exact record on the
// server.
//
// ── WHY THIS EXISTS (2026-10-17, b18, practitioner answers F1 / C2 / F3) ──
// Michael answered three of the six practitioner questions in
// docs/2026-10-16-hank-b17-practitioner-questions.md and all three landed on
// one shape. That document predicted it in writing -- "three of the six
// converge on ONE pattern ... which is worth knowing before any of them is
// answered" -- and the three are:
//
//   F1  A cremation authorisation needs a SECOND named, signing person.
//       SAIRNlegacy, leg_cremations, EVERY write.
//   C2  A paralegal may PREPARE a trust disbursement for an attorney to
//       authorise. SAIRNlaw, law_trusttx, the prepared path only.
//   F3  Where an apprentice may do the work but a licensed director must sign
//       the record, that is F1's lock with a different preparer. Per-home
//       config in api/_lib/leg-roles.js decides which resources.
//
// ── WHY ONE MODULE AND NOT TWO COPIES, WHICH IS A DEPARTURE ──────────────
// The platform's precedent is the opposite: api/sairncare-witness.js is a
// deliberate SECOND implementation of api/sv-witness.js, copied and narrowed,
// with its three divergences enumerated. That was right there and it is not
// right here, for a reason that is about the artefacts and not about taste:
//
//   sv_controlled and alf_mar are two different regulated records in two
//   different trades whose locks genuinely differ in SHAPE -- in SAIRNvet the
//   requester IS the first signature, in SAIRNcare the requester is the
//   witness and somebody else performs the write. Two shapes, two files.
//
//   leg_cremations and law_trusttx have the SAME shape: prepared by one named
//   person, signed by a different qualified one, bound to the exact record.
//   What differs is a role list, a table name and whether the lock covers
//   every write or only the prepared path -- THREE VALUES, not three
//   behaviours. A second copy would be a third and fourth spelling of
//   sv-witness's token lifecycle, and the settling step below is 40 lines of
//   reasoning that must not exist in four places with three of them stale.
//
// SO THE DIVERGENCES ARE A PROFILE, and `api/countersign-profile.test.js`
// asserts each app's profile is complete rather than trusting that a caller
// passed one. ITEM 7 OF docs/2026-09-13-cross-domain-disciplines.md CUTS BOTH
// WAYS: byte-identical is not safe-in-context, and the answer to that is to
// re-qualify the DIFFERENCES explicitly, which a named profile does better
// than a copied file nobody diffs again.
//
// ── THE FOUR PROPERTIES, UNCHANGED FROM api/sv-witness.js ────────────────
// Read that file for the full argument; they are not restated here.
//   1. The token is bound to a HASH OF THE RECORD, not to "a write is coming".
//   2. CHECKED AGAINST THE TABLE, never an in-memory map -- this runs
//      serverless and a second request is a second process.
//   3. A FAILED CHECK REFUSES rather than writing unsigned. "Could not tell"
//      is a third state and is never folded into "signed".
//   4. THE SETTLING STEP re-verifies the signers are STILL ACTIVE at write
//      time, because between the signature and the write the world has up to
//      TOKEN_TTL_MS to move.
//
// ── AND THREE THINGS THIS DOES NOT HAVE, EACH A NARROWING ────────────────
//   1. NO `require_two_person` POLICY TABLE, so no policy read and no second
//      table per app. SAIRNvet made it per-licence because a one-vet practice
//      cannot staff a second witness and the count still has to happen. HERE
//      BOTH ANSWERS ARE LEGAL READINGS, NOT STAFFING QUESTIONS -- F1 asked
//      whether the state requires it or the house does, and a bar rule is not
//      something a licensee turns off in Settings. A home or firm that cannot
//      produce a second signer cannot file, which is the paper position too.
//   2. NO `set_policy` ACTION, for the same reason.
//   3. NO SELF-SIGNATURE, EVER, AND IT IS REFUSED RATHER THAN FLAGGED. A
//      cremation authorisation signed twice by one person is not a
//      two-person authorisation, and there is no undoing a cremation.
//
// ── WHAT A COUNTERSIGNATURE DOES NOT CLAIM ───────────────────────────────
// It attests that a second qualified person looked. It does not attest that
// they were right. Electronic witnessing exists because independent
// double-review has a measured, non-zero failure rate where mistakes cannot be
// undone -- which is an argument for a lock and equally an argument against
// believing a lock makes anything safe. The refusals below say so; none of
// them implies a signed write is a correct one.
// ---------------------------------------------------------------------------

'use strict';

const crypto = require('crypto');

// Ten minutes, the same as api/sv-witness.js. Long enough to read a record
// back and sign it, short enough that a signature stays attached to the act it
// witnessed. NOT a per-app value: a shorter window on one of these two would
// be a difference with no reason behind it.
const TOKEN_TTL_MS = 10 * 60 * 1000;

// The two modes a locked resource can be in. SPELLED, not booleans, because
// `always` and `prepared_only` are a real policy difference between F1 and C2
// and a `true`/`false` would read as the same idea with opposite values.
const MODE_ALWAYS = 'always';
const MODE_PREPARED_ONLY = 'prepared_only';
const MODES = [MODE_ALWAYS, MODE_PREPARED_ONLY];

// ── THE CANONICAL FORM IS THE WHOLE BINDING ─────────────────────────────────
// Two JSON encodings of the same record must produce the same hash or the
// write endpoint refuses a token that was legitimately issued; two DIFFERENT
// records must never collide or the lock is decorative. Keys are sorted
// recursively and nothing else is normalised -- no trimming, no case folding,
// no dropping of nulls. A record differing only in whitespace inside a STRING
// is a different record, and deciding otherwise here would be this file
// quietly editing a cremation authorisation.
function canonical(value) {
  if (value === null || typeof value !== 'object') return JSON.stringify(value);
  if (Array.isArray(value)) return '[' + value.map(canonical).join(',') + ']';
  const keys = Object.keys(value).sort();
  return '{' + keys.map((k) => JSON.stringify(k) + ':' + canonical(value[k])).join(',') + '}';
}

function contentHash(resource, payload) {
  // The RESOURCE is inside the hash. Without it a token issued for one table
  // could be spent on another, which is the content-binding hole wearing a
  // different hat.
  return crypto.createHash('sha256')
    .update(String(resource) + '\n' + canonical(payload))
    .digest('hex');
}

function hashToken(tok) {
  return crypto.createHash('sha256').update(String(tok)).digest('hex');
}

function newToken() {
  return crypto.randomBytes(32).toString('base64url');
}

function isMissingTable(detail) {
  const s = JSON.stringify(detail || '');
  return s.indexOf('PGRST205') !== -1 || s.indexOf('does not exist') !== -1;
}

// ── THE PROFILE, VALIDATED AND NOT TRUSTED ──────────────────────────────────
// A caller that passes an incomplete profile must be REFUSED, not served with
// whatever defaults this file would have invented. An empty `signerRoles` is
// the shape that matters: with a permissive default it would mean "anyone may
// sign", which is the lock inverted, and with a silent empty it would mean
// "nobody may sign", which is a cremation nobody can ever authorise. Both are
// wrong and neither should be reachable, so this throws at the call site
// instead.
//
// THROWS RATHER THAN RETURNING A REFUSAL, deliberately: a malformed profile is
// a programming error in this repo, not a condition a user can produce, and a
// 503 would hide it behind something that looks operational.
function assertProfile(p) {
  const problems = [];
  if (!p || typeof p !== 'object') throw new Error('countersign: no profile given');
  ['app', 'employeeTable', 'tokenTable', 'sqlFile', 'signerLabel']
    .forEach((k) => { if (!p[k] || typeof p[k] !== 'string') problems.push(k); });
  if (!p.lockedResources || typeof p.lockedResources !== 'object'
      || Object.keys(p.lockedResources).length === 0) {
    problems.push('lockedResources (must name at least one resource)');
  } else {
    Object.keys(p.lockedResources).forEach((r) => {
      if (MODES.indexOf(p.lockedResources[r]) === -1) {
        problems.push('lockedResources.' + r + ' must be one of: ' + MODES.join(', '));
      }
    });
  }
  if (!p.signerRoles || typeof p.signerRoles !== 'object'
      || Object.keys(p.signerRoles).filter((k) => p.signerRoles[k] === true).length === 0) {
    problems.push('signerRoles (must grant at least one role `true`)');
  }
  if (problems.length) {
    throw new Error('countersign: incomplete profile for '
      + String((p && p.app) || 'unknown app') + ' -- ' + problems.join('; '));
  }
  return p;
}

function isSigner(profile, role) {
  return profile.signerRoles[role] === true;
}

// Who may REQUEST a token, i.e. stage a record for signature. Signers always
// may -- a director may of course prepare what they may file. `preparerRoles`
// adds the roles that may prepare and may NOT file: paralegal for C2, and
// whichever roles a home's F3 config names for an apprentice.
//
// THE UNION IS COMPUTED HERE AND NOWHERE ELSE, so no call site can disagree
// about whether a signer is implicitly a preparer.
function isPreparer(profile, role) {
  if (isSigner(profile, role)) return true;
  const extra = profile.preparerRoles || {};
  return extra[role] === true;
}

// ── ONE PLACE THAT ASKS THE ROSTER WHAT AN EMPLOYEE IS **NOW** (b28) ───────
// Returns `{ role }` or `{ refusal }` and never both, so a caller cannot read
// a role out of a result that is actually a refusal. Three outcomes and they
// are not two:
//
//   refusal 503  the roster could not be read. NOT "no longer qualified" and
//                NOT "still qualified" -- it is could-not-tell, and on an
//                irreversible write the only safe answer to that is refusal.
//   refusal 403  no active row for this employee. `active=eq.true` is in the
//                filter, so "deactivated" and "not on the roster at all" arrive
//                identically here and share one message, which is honest: both
//                mean nobody currently employed stands behind this.
//   { role }     the role the roster holds for them at this instant.
//
// THE COLUMN LIST IS `employee_id,role` AND THAT IS THE WHOLE b28 FIX in the
// settling step -- it selected `employee_id` alone, so the one check that did
// reach the database was asking the wrong question. A disbarred attorney still
// on the payroll is `active`.
async function currentStanding(profile, ctx, employeeId) {
  const enc = encodeURIComponent;
  const r = await fetch(ctx.rest(profile.employeeTable
    + '?license_hash=eq.' + enc(ctx.licHash)
    + '&employee_id=eq.' + enc(employeeId)
    + '&active=eq.true&select=employee_id,role&limit=1'), { headers: ctx.headers });
  const rows = await r.json().catch(() => null);
  if (!r.ok) {
    return { refusal: { status: 503, body: { error: {
      code: 'COUNTERSIGN_CHECK_FAILED',
      message: 'Whether the signing employee still holds that role could not '
             + 'be verified, so nothing was written. This is not the same as '
             + 'the record being unsigned.' } } } };
  }
  const row = (Array.isArray(rows) && rows[0]) || null;
  if (!row) {
    return { refusal: { status: 403, body: { error: {
      code: 'COUNTERSIGN_NO_LONGER_ACTIVE',
      message: 'An employee who signed this record is no longer active. Have '
             + 'it signed again by a current employee -- the record was not '
             + 'saved.' } } } };
  }
  return { role: row.role };
}

/**
 * THE HALF api/sd-data.js CALLS, and it returns A REFUSAL OR NULL -- never a
 * boolean. A boolean invites `if (!ok) { /* log and continue *\/ }`, and this
 * must be the thing that stops the write rather than a fact about it. Copied
 * in INTENT from api/sv-witness.js's requireWitness and not in text: the
 * mode switch below does not exist there.
 *
 * @param {object} profile  see assertProfile
 * @param {object} ctx { resource, payload, licHash, rest, headers, token,
 *                       callerRole, callerEmployeeId }
 */
async function requireCountersignature(profile, ctx) {
  assertProfile(profile);
  const { resource, payload, licHash, rest, headers, token } = ctx;
  const enc = encodeURIComponent;
  const mode = profile.lockedResources[resource];
  if (!mode) return null;                               // not a locked resource

  // ── THE MODE SWITCH, WHICH IS THE WHOLE F1/C2 DIFFERENCE ────────────────
  // MODE_PREPARED_ONLY: a caller who may FILE the record files it, exactly as
  // before this lock existed. C2's answer widened who may participate; it did
  // NOT say an attorney now needs a second attorney to move trust money, and
  // inventing that would be this file deciding a bar-rules question nobody
  // asked it. The lock bites on the PREPARED path -- a paralegal's row -- and
  // there it is absolute.
  //
  // MODE_ALWAYS: every write, including the owner's. F1's answer is that the
  // paperwork takes a second named person, and a rule the owner is exempt from
  // is not that.
  // ── AND THE ROLE IN THE TOKEN IS NOT THE ROLE IN THE ROSTER (b28) ───────
  // THE DEFECT THIS CLOSES. The line below used to be
  //
  //     if (mode === MODE_PREPARED_ONLY && isSigner(profile, ctx.callerRole))
  //
  // and `ctx.callerRole` is `gateSession.role` -- the role inside the SIGNED
  // SESSION TOKEN. The signature is unforgeable, which is exactly what made
  // this easy to miss: every instinct saying "that token is valid" was right.
  // A token proves WHO ASKED and WHEN THEY SIGNED IN. It cannot prove what
  // they may do NOW, because it was minted before now. Authentication survives
  // in a token; authorisation does not.
  //
  // So an attorney demoted to paralegal went on moving client trust money,
  // with no countersignature and no second person, for as long as the token
  // lived -- SESSION_TTL_MS, **12 hours** (api/_lib/auth.js:104). The firm
  // does the one thing it can do about a person it no longer trusts with
  // trust money, and the platform honours the old answer until tomorrow.
  //
  // ── IT ONLY EVER REFUSES MORE, AND THAT IS A DECISION ──────────────────
  // The roster role is required IN ADDITION to the token role, not INSTEAD of
  // it. A paralegal PROMOTED to attorney still presents a paralegal token and
  // still gets COUNTERSIGN_REQUIRED until they sign in again -- a refusal with
  // an obvious remedy, and the b28 arm R3 asserts it. Reading authority purely
  // from the roster would have been tidier and would have WIDENED who can
  // write from a path that refuses today, which is not what the defect report
  // asked for and is not a change to make inside a security fix.
  //
  // ── AND IT FAILS CLOSED, WHICH DIFFERS FROM THE CHECK ABOVE IT ─────────
  // api/sd-data.js's per-request active-credential re-check LOGS and CONTINUES
  // when the roster cannot be read ("NO_ACTIVE_CHECK ... NOT an admission").
  // That is right for a request that something downstream will still gate.
  // It is wrong here: this IS the downstream gate, the write is money out of a
  // client trust account, and the only safe answer to could-not-tell on an
  // irreversible write is refusal (PR 1.11).
  if (mode === MODE_PREPARED_ONLY && isSigner(profile, ctx.callerRole)) {
    const standing = await currentStanding(profile, ctx, ctx.callerEmployeeId);
    if (standing.refusal) return standing.refusal;
    if (!isSigner(profile, standing.role)) {
      return { status: 403, body: { error: { code: 'COUNTERSIGN_ROLE_REVOKED',
        message: 'Your sign-in still says ' + profile.signerLabel + ', and the '
               + 'employee roster no longer does. Nothing was written. Sign in '
               + 'again to pick up your current role -- or have this record '
               + 'countersigned by someone who is.' } } };
    }
    return null;
  }

  if (!token) {
    return { status: 403, body: { error: { code: 'COUNTERSIGN_REQUIRED',
      message: profile.requiredMessage } } };
  }
  const r = await fetch(rest(profile.tokenTable + '?license_hash=eq.' + enc(licHash) +
    '&token_hash=eq.' + enc(hashToken(token)) +
    '&select=id,content_hash,prepared_by,prepared_role,countersign_employee_id,'
    + 'countersign_role,spent_at,expires_at&limit=1'), { headers });
  const rows = await r.json().catch(() => null);
  if (!r.ok) {
    // A FAILED CHECK IS NOT "SIGNED". It is also not "unsigned" -- it is
    // could-not-tell, and the only safe answer to could-not-tell on an
    // irreversible write is refusal.
    if (isMissingTable(rows)) {
      return { status: 503, body: { error: { code: 'NOT_PROVISIONED',
        message: 'The ' + profile.app + ' countersignature table is not set up yet '
               + '-- run ' + profile.sqlFile + '. The write was refused rather '
               + 'than filed unsigned.' } } };
    }
    return { status: 503, body: { error: { code: 'COUNTERSIGN_CHECK_FAILED',
      message: 'The signature could not be verified, so nothing was written. '
             + 'This is not the same as the record being unsigned.' } } };
  }
  const row = (Array.isArray(rows) && rows[0]) || null;
  if (!row) {
    return { status: 403, body: { error: { code: 'COUNTERSIGN_REQUIRED',
      message: 'That signature is not recognised.' } } };
  }
  if (row.spent_at) {
    return { status: 409, body: { error: { code: 'COUNTERSIGN_ALREADY_SPENT',
      message: 'That signature has already been used. Each signature covers '
             + 'exactly one write.' } } };
  }
  if (new Date(row.expires_at).getTime() <= Date.now()) {
    return { status: 409, body: { error: { code: 'COUNTERSIGN_EXPIRED',
      message: 'That signature has expired -- prepare and sign the record again.' } } };
  }
  // THE CONTENT BINDING. Recomputed from the payload actually being written,
  // so a token issued for one record cannot be spent on another.
  if (row.content_hash !== contentHash(resource, payload)) {
    return { status: 409, body: { error: { code: 'COUNTERSIGN_CONTENT_MISMATCH',
      message: 'This is not the record that was signed. Have it signed again '
             + 'before saving it.' } } };
  }
  // ── THE SIGNATURE ITSELF, THREE CONDITIONS AND ALL THREE ARE REQUIRED ───
  if (!row.countersign_employee_id) {
    return { status: 403, body: { error: { code: 'COUNTERSIGN_REQUIRED',
      message: profile.requiredMessage } } };
  }
  // A SIGNATURE BY THE PREPARER IS NOT A COUNTERSIGNATURE. This is the entire
  // content of "a second named person", and without it the lock is a second
  // click by the same hand. Re-checked HERE as well as at `countersign`,
  // because the write is the moment that matters and a check that only runs
  // earlier is a check an edit can route around.
  if (row.countersign_employee_id === row.prepared_by) {
    return { status: 409, body: { error: { code: 'COUNTERSIGN_SAME_PERSON',
      message: 'A second person must sign. This record was prepared and signed '
             + 'by the same employee, so it was not saved.' } } };
  }
  // AND THE SIGNER MUST BE QUALIFIED, re-derived from the role STORED on the
  // row. Not from the current caller -- it is the signer's standing the record
  // claims, not the saver's.
  if (!isSigner(profile, row.countersign_role)) {
    return { status: 403, body: { error: { code: 'COUNTERSIGN_NOT_QUALIFIED',
      message: 'The signature on this record is not from ' + profile.signerLabel
             + ', so it was not saved.' } } };
  }

  // ── THE SETTLING STEP ───────────────────────────────────────────────────
  // Everything above re-checks the TOKEN -- that it exists, is unspent, is
  // unexpired, covers THIS payload and carries a qualified second signature.
  // Not one of those is a fact about the WORLD, and between the signature and
  // the write the world has up to TOKEN_TTL_MS to move.
  //
  // THE SHAPE IS NASA'S DOCKING SEQUENCE and api/sv-witness.js records paying
  // for the missing middle phase: soft capture, then ATTENUATION -- re-check
  // alignment, still able to back out -- and only then hard capture. The TTL
  // is a DEADLINE, and a deadline re-verifies nothing.
  //
  // THE REACHABLE CASE HERE IS THE SHARPER OF THE TWO: a director signs a
  // cremation authorisation, has their licence pulled, and the write still
  // lands attributed to them inside the next ten minutes -- on a record with
  // no undo and no amended version that helps.
  // ── AND IT ASKED ABOUT `active` AND NOTHING ABOUT ROLE (b28) ──────────
  // This loop selected `employee_id` under `active=eq.true` and nothing else,
  // so the whole argument above -- the world has up to TOKEN_TTL_MS to move --
  // was being applied to ONE of the two ways it can move. A struck-off
  // attorney who is still on the payroll is `active`, and the write landed
  // attributed to a signature that no longer means what the record claims.
  //
  // TWO DIFFERENT QUESTIONS, NOT ONE ASKED TWICE. The signer must still be
  // QUALIFIED TO FILE (`isSigner`); the preparer must still be QUALIFIED TO
  // PREPARE (`isPreparer`, the wider set). Asking `isSigner` of both would
  // refuse every paralegal-prepared record, which is the normal C2 case.
  //
  // AND IT IS "STILL QUALIFIED", NEVER "STILL THE SAME STRING". An attorney
  // promoted to owner is more qualified, not less, and a string match would
  // have refused them -- arm S4 of api/b28-role-from-token.test.js is that
  // case and it must stay green.
  const attesters = [
    { who: row.prepared_by, qualified: isPreparer, what: 'prepare' },
    { who: row.countersign_employee_id, qualified: isSigner, what: 'sign' }
  ];
  for (const a of attesters) {
    if (!a.who) continue;
    const standing = await currentStanding(profile, ctx, a.who);
    if (standing.refusal) return standing.refusal;
    if (!a.qualified(profile, standing.role)) {
      return { status: 403, body: { error: { code: 'COUNTERSIGN_ROLE_REVOKED',
        message: 'An employee who signed this record no longer holds the role '
               + 'that let them ' + a.what + ' it. Have it prepared and signed '
               + 'again -- the record was not saved.' } } };
    }
  }

  // SPEND IT BEFORE THE WRITE, NOT AFTER. If the write then fails the token is
  // burned and the record must be signed again -- which is the direction to
  // fail in. Spending afterwards leaves a window where a retry reuses the same
  // signature, and a reusable signature is the defect this exists to prevent.
  //
  // `&spent_at=is.null` makes the spend a COMPARE-AND-SET: two concurrent
  // writes racing the same token, one wins and the other gets zero rows back.
  // Without it the check-then-spend gap is exactly wide enough for a double
  // submit to file two cremation authorisations on one signature.
  const spend = await fetch(rest(profile.tokenTable + '?id=eq.' + enc(row.id)
    + '&spent_at=is.null'), {
    method: 'PATCH',
    headers: Object.assign({}, headers, { Prefer: 'return=representation' }),
    body: JSON.stringify({ spent_at: new Date().toISOString(), spent_on_resource: resource })
  });
  const spent = await spend.json().catch(() => null);
  if (!spend.ok) {
    return { status: 503, body: { error: { code: 'COUNTERSIGN_CHECK_FAILED',
      message: 'The signature could not be recorded as used, so nothing was written.' } } };
  }
  if (!Array.isArray(spent) || spent.length === 0) {
    return { status: 409, body: { error: { code: 'COUNTERSIGN_ALREADY_SPENT',
      message: 'That signature was used by another request a moment ago. '
             + 'Prepare and sign the record again.' } } };
  }
  return null;                                          // signed. proceed.
}

module.exports = {
  TOKEN_TTL_MS,
  MODE_ALWAYS, MODE_PREPARED_ONLY, MODES,
  canonical, contentHash, hashToken, newToken, isMissingTable,
  assertProfile, isSigner, isPreparer,
  requireCountersignature
};
