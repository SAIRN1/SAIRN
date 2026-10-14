// api/_lib/ai-safeguards.js
// ---------------------------------------------------------------------------
// THE TWO SAFEGUARDS THAT NEEDED A SERVER, AND NOTHING ELSE.
//
// Scope, taken from Michael's b9 instruction rather than widened:
//
//   1. `ai_source` / `ai_approved_by` / `ai_approved_at` on a record whose
//      content came from a model and which becomes a DOCUMENT OR A DECISION.
//      The server refuses a HIGH-RISK ai-sourced record leaving draft unless it
//      can set `ai_approved_by` from the signed-in employee -- and it sets that
//      name ITSELF, never from the payload.
//   2. A per-employee, ONE-TIME acknowledgement of the AI-suggestion notice,
//      stored under that employee's own credential row with a DATE and a
//      NOTICE VERSION, so the popup never comes back for a version already
//      acknowledged.
//
// THE PRECEDENT IS api/sd-data.js's sc_auth_requests SIGN-OFF GATE, and this
// follows it deliberately rather than inventing a shape: a client-side
// "reviewed" checkbox is a UI convenience and never the real boundary; only a
// real, currently-valid session can make a record final; and the server writes
// the attributed name from the verified session so a forged name in the payload
// can never end up in the record.
//
// ── WHAT THIS FILE DOES NOT DO, so the next reader does not look for it ───
// It does not implement the owner-level agreement acceptance, the inline
// Reviewed button, or the per-surface `ai: true` marker on api/claude.js
// responses. Those are in docs/2026-10-14-ai-safeguards-spec.md -- which is in
// ANOTHER SESSION'S LIVE CLAIM and was read, not edited. This file is the
// `api/` half of that spec's items (a) and the record-field half of (c)/(d),
// which is what b9 asked for.
//
// ── THE FOOTER IS DERIVED AND NOTHING EXTRA IS STORED ─────────────────────
// "AI-assisted, reviewed by <name>" is a function of the three fields on the
// record. Storing the sentence would be a second copy of a fact that can drift
// from the first, and the first is the one a regulator would ask about.
// ---------------------------------------------------------------------------

'use strict';

const { AI_SCANNED_TEXT } = require('./ai-scan-redaction');

// ── THE NOTICE VERSION IS A STRING, NOT A BOOLEAN, AND THAT IS THE POINT ──
// A boolean cannot express "acknowledged the OLD wording". When the notice text
// changes this constant changes, every employee is asked exactly once more, and
// the previously-acknowledged version stays readable in the row until the new
// ack lands -- so "which text did this person actually see" is answerable.
//
// NOT TIED TO THE LAWYER-APPROVED AGREEMENT VERSION YET. That is one of the
// three open questions in the spec and it is Michael's to answer; until then
// this is a plain date-shaped tag and the coupling is deliberately absent
// rather than guessed at.
const CURRENT_NOTICE_VERSION = '2026-11';

// ── A RECORD IS AI-SOURCED WHEN THE CLIENT SAYS SO ────────────────────────
// There is no way for a server to look at a block of prose and know a model
// wrote it. So `ai_source` is a CLAIM BY THE WRITER, and the honest consequence
// is stated rather than hidden: a client that does not stamp it gets no
// approval gate. That is why the field is a short machine tag naming the
// surface (`claude:newsletter`, `claude:photo-fill`), not a boolean -- a
// boolean would make "which surface produced this" unanswerable the moment a
// second one existed on the same resource.
const AI_SOURCE_FIELD = 'ai_source';
const APPROVED_BY_FIELD = 'ai_approved_by';
const APPROVED_AT_FIELD = 'ai_approved_at';

// ── DRAFT IS A CLOSED LIST, AND AN ABSENT STATUS IS NOT A DRAFT ───────────
// The direction matters: treating a missing status as "draft" would make the
// gate silent on every resource that has no status field at all, which is most
// of them. So absent => FINAL => the gate applies. A client that genuinely
// wants to save an unapproved working copy has to say `status: 'draft'`.
const DRAFT_STATUSES = ['draft', 'Draft', 'DRAFT', 'new', 'New', 'pending', 'Pending'];

// ── HIGH RISK = IT BECOMES A DOCUMENT OR A DECISION ───────────────────────
// Judgment, so it is written down per resource with the reason and the write
// site. It is NOT derived, because "does this leave the building" is not a
// property of the code -- but it is CHECKED against a derived population
// below, which is the part that cannot go stale quietly.
//
// EACH ENTRY CARRIES ITS OWNING APP, and that is not redundancy -- the gate has
// to verify a session for the app that OWNS the row, and api/sd-data.js does
// not import the resource registry. The app written here is CHECKED against
// api/_resources' OWNER_BY_RESOURCE by the suite, so a wrong one fails a test
// rather than quietly verifying a token for an app with no business approving
// the record (Guardian Check 28 -- role names like 'owner' exist in several
// apps' vocabularies, so a cross-app session supplies a plausible name).
const HIGH_RISK_AI = {
  mech_quotes: { app: 'sairnmechanical', why:
    'A QUOTE A CUSTOMER SIGNS. `text` is the model\'s reply over a '
    + 'photographed plan (api/_lib/ai-scan-redaction.js lists it), and '
    + 'sairnmechanical.html:1441 shares it from memory -- so the model\'s '
    + 'words are the priced offer. Money, and it leaves the building.' },
  mech_takeoffs: { app: 'sairnmechanical', why:
    'THE QUANTITIES A PRICE IS BUILT FROM. Same surface as the quote one step '
    + 'earlier; a takeoff that is wrong produces a quote that is wrong and '
    + 'nobody re-reads the takeoff afterwards.' },
  grd_ecosystem_reports: { app: 'sairngrounds', why:
    'A REPORT THAT GOES TO A PROPERTY OWNER. sairngrounds.html:4183-4189 '
    + 'concatenates SEVEN model sections into `summary` and stores it as the '
    + 'deliverable. Nothing between the model and the owner reads it.' },
  rf_photos: { app: 'sairnroofing', why:
    'AN INSURANCE ESTIMATE IS BUILT ON IT. `ai_analysis` is the model\'s read '
    + 'of a measurement photograph (sairnroofing.html:5348) and '
    + '`parsed_quantities` are extracted from it -- a roofing supplement is a '
    + 'claim against an insurer, which is a decision with money on it.' },
  bld_photo_analyses: { app: 'sairnbuild', why:
    'A JOB-SITE FINDING THAT DRIVES WORK. sairnbuild.html:3666-3667 stores the '
    + 'model\'s answer over a site photograph verbatim as `full`, with '
    + '`summary` as its first 140 characters -- the summary is what a reader '
    + 'sees in the list, so the decision is taken on a slice nobody opened.' }
};

// ── AND THE REST OF THE AI-WRITING RESOURCES, EXCLUDED ON PURPOSE ─────────
// EVERY resource that stores model prose is in exactly one of these two maps.
// The arm that proves it is in api/ai-safeguards.test.js and it is the reason
// this file cannot quietly stop covering a new AI surface: adding a resource to
// AI_SCANNED_TEXT without deciding its risk fails that test.
const NOT_HIGH_RISK_AI = {
  mech_docs: 'A STORED DOCUMENT READ, not a document the app issues. The '
    + 'model reads a plan somebody already has; no new artefact leaves.',
  grd_progress_photos: 'QC EVIDENCE WITH ITS OWN AUTHORITY GATE. The '
    + 'ai_analysis annotates a photograph; the QC DECISION on it is already '
    + 'role-gated and refuses self-QC against the server\'s captured_by.',
  scp_progress_photos: 'Sibling of grd_progress_photos, same panel shape and '
    + 'the same QC authority gate. Same answer.',
  msb_food_scans: 'AN INVENTORY LINE. `raw` is the model reply and `items` is '
    + 'the parsed product list -- a count of what is in a fridge. No person, '
    + 'no money and no regulated determination on the row.',
  memory: 'INTERNAL AND NOBODY READS IT. A one-sentence summary stored to be '
    + 'fed back into later prompts (stonedesk.html:30425). It becomes no '
    + 'document and drives no decision; it is already redacted for PII.',
  // Added 2026-10-14 (b9) with the SAIRNfreedom wiring, and it is the one
  // entry here that is an ARGUMENT rather than an observation:
  sf_bottle_fills: 'AN AUTOMATIC-ONLY DETERMINATION, AND REQUIRING A HUMAN '
    + 'APPROVAL WOULD CONTRADICT A RECORDED PRODUCT DECISION. '
    + 'sairnfreedom.html:4896-4901 states the binding decision: fill level is '
    + 'determined from a photograph or not at all -- "no slider, no '
    + 'tap-to-set, no adjustable guess" -- for patent-avoidance reasons. An '
    + 'approve step is a human adjusting the guess. The row carries a bottle '
    + 'id, a date and a percentage: no person, no money, no regulated '
    + 'determination. It DOES get ai_source, because disclosure and approval '
    + 'are different safeguards and only one of them conflicts.'
};

/**
 * Is this employee owed the AI notice?
 *
 * Takes the credential row (or null) and never a token, so a caller cannot
 * accidentally answer from something the database did not say. A null row is
 * `required: true` -- the state every existing row starts in, and not an error.
 */
function aiNoticeState(row) {
  const version = (row && row.ai_notice_version) || null;
  const at = (row && row.ai_notice_acked_at) || null;
  return {
    required: version !== CURRENT_NOTICE_VERSION,
    current_version: CURRENT_NOTICE_VERSION,
    acked_version: version,
    acked_at: at
  };
}

function isHighRisk(resource) {
  return Object.prototype.hasOwnProperty.call(HIGH_RISK_AI, resource);
}

function isDraft(payload) {
  const s = payload && payload.status;
  if (s === undefined || s === null || s === '') return false;   // absent => FINAL
  return DRAFT_STATUSES.indexOf(String(s)) !== -1;
}

/**
 * The gate. Returns null when there is nothing to do, or a refusal
 * `{ status, code, message }` the caller sends verbatim.
 *
 * ON SUCCESS IT MUTATES THE PAYLOAD -- `ai_approved_by` and `ai_approved_at`
 * are written from the VERIFIED SESSION, overwriting whatever the client sent.
 * That overwrite is the control: a forged reviewer name in a payload must never
 * reach a record, and the sc_auth_requests precedent does exactly this.
 *
 * @param resource  the resource name being written
 * @param payload   the record (mutated on success)
 * @param verifyForApp (app) => session|null, called with the app that OWNS
 *                     this resource. The caller supplies it because only the
 *                     caller has the request and the licence hash.
 * @param nowISO    () => string, injected so tests do not race the clock
 */
function enforceAiApproval(resource, payload, verifyForApp, nowISO) {
  if (!payload || typeof payload !== 'object') return null;
  if (!payload[AI_SOURCE_FIELD]) return null;          // not claimed as AI-sourced
  if (!isHighRisk(resource)) return null;              // disclosure only
  if (isDraft(payload)) return null;                   // a draft may be unapproved

  const session = verifyForApp(HIGH_RISK_AI[resource].app);
  if (!session || !session.employee_id) {
    return {
      status: 403,
      code: 'AI_APPROVAL_REQUIRED',
      message: 'This record was written by AI and is leaving draft, so it has '
        + 'to be approved by a signed-in employee before it is saved. Sign in '
        + 'and save it again. Nothing was saved.'
    };
  }
  payload[APPROVED_BY_FIELD] = session.employee_id;
  payload[APPROVED_AT_FIELD] = nowISO();
  return null;
}

/**
 * The footer sentence, derived. Returns the "not reviewed" wording rather than
 * an empty string for an AI-sourced record nobody approved -- a MISSING footer
 * and an unreviewed one read identically to a reader, and only one of them is
 * true.
 */
function aiFooter(payload) {
  if (!payload || !payload[AI_SOURCE_FIELD]) return '';
  const by = payload[APPROVED_BY_FIELD];
  if (!by) return 'AI-assisted — not reviewed';
  return 'AI-assisted, reviewed by ' + by;
}

module.exports = {
  CURRENT_NOTICE_VERSION,
  AI_SOURCE_FIELD, APPROVED_BY_FIELD, APPROVED_AT_FIELD,
  DRAFT_STATUSES,
  HIGH_RISK_AI, NOT_HIGH_RISK_AI,
  AI_PROSE_RESOURCES: Object.keys(AI_SCANNED_TEXT),
  aiNoticeState, isHighRisk, isDraft, enforceAiApproval, aiFooter
};
