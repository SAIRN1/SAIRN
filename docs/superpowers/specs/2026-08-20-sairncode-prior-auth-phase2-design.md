# SAIRNcode Phase 2 — Prior Authorization: scope (design only, nothing built)

**Status:** scope for review. No code written. Phase 1 (BYO credential layer +
270/271 eligibility) shipped `fba67d9`, confirmed closed.

**Skills run:** `sairn-software-architect`, `sairn-decision-gate`.
`graphify` could not be invoked — it is disabled for model invocation in
`skillOverrides`. The CLI is installed (`~/.local/bin/graphify`) and no
`graphify-out/` exists in this repo yet; say the word and it can be run
directly instead.

---

## Headline

Michael was right that this needs a real re-scope, and the reason is bigger
than the credential shape. **Phase 2 should not be built as one thing.** It
splits cleanly into two halves with completely different risk profiles:

- **2a + 2b — build now.** AI documentation assembly, request-lifecycle
  tracking, and a payer capability registry. Real value today, no new
  credential model, no new external dependency.
- **2c — do NOT build now.** Real FHIR PAS submission. It fails the
  Bid/No-Bid gate on today's facts, and building it now would ship a button
  essentially no practice could use.

---

## What changed since the Phase 1 plan assumed "prior-auth extends Phase 1"

Four findings, all verified rather than assumed.

### 1. FHIR PAS is not an API key — it is per-payer registered asymmetric crypto

`POST [base]/Claim/$submit` with a conformant FHIR Bundle (Claim + Patient +
Practitioner + Organization + Coverage + supporting resources); the payer
converts it to X12 278 and returns a Bundle containing a ClaimResponse.
Authentication is **SMART Backend Services**: OAuth 2.0 `client_credentials`,
where the client authenticates with a **one-time-use JWT signed by its own
private key** (RS384 or ES384), after **registering its public key (JWKS) with
each payer individually**.

Concretely, that means per payer: a `client_id`, a private signing key, a
token endpoint, a FHIR base URL, scopes, and a completed registration —
versus Phase 1's single opaque string.

### 2. The Phase 1 singleton row physically cannot hold this — measured, not estimated

`sc_credentials` is one row per license (`credential_id='default'`) with a
64KB CHECK constraint. Measured with the real `encryptSecret()` helper and
real generated keys:

| Key type | Encrypted key | Full per-payer record | 10 payers | 20 payers | 30 payers |
|---|---|---|---|---|---|
| RS384 (RSA-2048) | 2312 B | **2642 B** | 26 KB ✅ | 53 KB ✅ | **79 KB ❌ over cap** |
| ES384 (EC P-384) | 448 B | **778 B** | 8 KB ✅ | 16 KB ✅ | 23 KB ✅ |

SMART says the signature *SHOULD* be RS384 **or** ES384 — we do not get to
force the small one, since the payer's registration process may dictate it. A
practice dealing with 25–30 payers on RSA keys **exceeds the row cap and the
write starts failing**. So this is genuinely a different storage shape:
**one row per payer** (`entry_id = payerId`), not the singleton.

That is exactly the "expensive to reverse" data-model call
`sairn-software-architect` says to settle before building, so it is settled
here even though 2c is deferred — designing it is cheap, migrating it later
is not.

### 3. There is no cheap reuse path through Stedi

Checked directly rather than assumed: Stedi's documented transaction support
is **270/271, 837P/I/D, 276/277, 835, 277CA**. There is **no 278**, and no
prior-auth item in docs, beta, or roadmap. So the Phase 1 credential the
practice already has cannot be reused to submit prior auths. If a
clearinghouse path is wanted, it needs a *different* vendor, which is its own
BYO integration and its own scoping pass.

### 4. `sc_auth` today tracks authorizations held, not requests sent

Current record is `{id, authId, proc, exp, units}` — status is *derived* from
`exp` (Active / Expiring Soon / Expired). There is no payer, no submission
date, no decision. That is a record of an auth you **already have**.

A prior-auth *request* is a different lifecycle object: submitted → pending →
approved / denied / more-info-needed, with a payer and a clock. Bolting
submission fields onto `sc_auth` repeats the exact mistake item 3 fixed for
denials (aggregate `sc_denial` had no payer and could not answer real
questions, so `sc_denial_events` was added alongside it rather than mangling
it). **Same call here: a new `sc_auth_requests` resource, linked to `sc_auth`
when a request is approved.** Existing `sc_auth` rows stay untouched — no
localStorage migration, no rows silently missing new fields.

---

## Decision gate

### Bid/No-Bid — "build real FHIR PAS submission now"

| # | Question | Answer |
|---|---|---|
| 1 | Opportunity real? | Regulation yes (Jan 1 2027, dated). Payer availability today ≈ zero. |
| 2 | Qualified **today**? | No. No payer registrations, no JWKS hosting, no PAS Bundle builder. |
| 3 | True cost? | High — Bundle construction, JWKS endpoint, OAuth client, per-payer credential model, testing against payers we cannot reach. |
| 4 | Cost of "no"? | Low. Portal submission is what practices do today regardless. |
| 5 | Strategic fit? | Yes long-term, weak near-term. |
| 6 | Can we deliver? | Not from a browser app alone — a JWKS endpoint must be publicly hosted and stable. New infra. |
| 7 | What don't we have? | Payer registrations, key custody policy, JWKS hosting, Bundle builder, any payer sandbox. |
| 8 | Fixable before deadline? | The deadline binds **payers**, not us. There is real time. |

**Result: well below the 60–65% threshold. Do not build 2c now.** This is a
deliberate, documented defer — not an oversight.

Critically: *the Jan 1 2027 deadline is an obligation on payers to expose the
API, not on providers or their software to consume it.* Any marketing framing
of SAIRNcode as "CMS-0057-F compliant" would be a false claim about someone
else's obligation.

### Premortem — "it is six months on and SAIRNcode's prior-auth feature embarrassed us"

1. **We shipped a FHIR submit button nobody could use.** No practice had payer
   registrations, so it sat dead — a dormant-code violation *and* a false
   capability claim on the panel. → Prevented by deferring 2c.
2. **SAIRN was holding practices' private signing keys when something went
   wrong.** A Stedi API key reaches Stedi and bills $0. A private signing key
   lets the holder **impersonate that practice to every payer it registered
   with**. That is a materially higher custody bar than Phase 1's, and Phase
   1's own documented limitation (all tenants encrypted under one
   platform-wide `SD_AUTH_SECRET`) is not good enough for it. → Must be
   resolved before 2c, not during.
3. **We claimed CMS-0057-F readiness and someone checked.** → Addressed above.
4. **AI-assembled documentation contained an unsupported clinical assertion
   and it was submitted to a payer.** → See the RMF finding below; this is the
   sharpest risk in the buildable half.

### NIST AI RMF — on the AI documentation assembly (2a)

- **Govern** — no named owner today for "AI-assembled prior-auth documentation
  was wrong." This affects a patient's access to care, not just a billing
  number. Needs an explicit owner before 2a ships to a real practice.
- **Map** — clinical note (PHI) → `api/claude.js` → Anthropic → assembled
  justification → payer. Anthropic is a subprocessor on a real PHI path.
  Already true of the existing note-to-code tool; worth stating plainly rather
  than rediscovering during a compliance review.
- **Measure — the real finding.** Reusing `quoteFoundInNote()` verifies a
  quoted phrase **is present in the note**. It does **not** verify the phrase
  **supports the medical-necessity conclusion drawn from it**. For code
  suggestion that gap was tolerable; for prior auth, a real quote paired with
  an unsupported inference is exactly the failure that gets a claim denied or,
  worse, approved on a bad basis. Citation-presence checking is necessary here
  but **not sufficient**, and the UI must not imply otherwise.
- **Manage** — no incident path for a bad assembled packet. Minimum: every
  assembled document is draft-only, requires explicit human sign-off before it
  can be marked submitted, and records who signed off.

---

## Recommended scope

### 2a — AI-assisted documentation assembly (build)

Given a clinical note plus the requested procedure/code, assemble a
payer-facing medical-necessity draft. Same forced-explainability contract as
`suggestCodesFromNote()`: every assertion carries an exact verbatim quote,
independently verified client-side with the existing `quoteFoundInNote()`.

Hard requirements from the RMF pass, not optional polish:
- Output is labelled **DRAFT** and is never auto-submitted.
- Each assertion shows its quote and a verified/unverified badge.
- The panel states explicitly that verification confirms the quote **appears
  in the note**, not that it **justifies medical necessity** — a human coder
  makes that call.
- Explicit human sign-off (who, when) recorded before a request can move to
  a submitted state.

Reuses: `quoteFoundInNote`, `normalizeForMatch`, `extractJsonArray`,
`APP_CONFIG.proxy`. No new endpoint, no new credential.

### 2b — Request lifecycle tracking (build)

New `sc_auth_requests` resource (20th SC_RESOURCES entry), generic handler,
same shape as every other `sc_*` table.

Record: `{id, payer, patientRef, procedure, urgency, submittedVia, submittedOn,
status, decisionOn, decisionNotes, signedOffBy}`.

- `submittedVia` — `Portal` / `Fax` / `Phone` / `FHIR PAS` (the last one
  inert until 2c exists, and clearly labelled as unavailable rather than
  offered and broken).
- `urgency` — drives a real clock against the CMS-0057-F operational rules
  already in force since Jan 1 2026: **72 hours expedited, 7 calendar days
  standard**. Those are real, current, and useful *today* regardless of FHIR.
  A request past its clock is flagged from real dates, never a placeholder.
- Approved request → optionally creates the matching `sc_auth` row, which is
  what that panel was always for.

`sc_auth` itself is **not modified**. No migration.

### 2c — Real FHIR PAS submission (do NOT build now)

Deferred with concrete re-open triggers, so this is a decision with a date
rather than a shrug. Revisit when **any** of these is true:

1. A payer the practice actually bills publishes a working provider-facing
   PAS endpoint and will register us.
2. A clearinghouse the practice already uses exposes 278 or PAS behind a
   simple credential (Stedi does not today — recheck, since their API surface
   is actively expanding).
3. Michael decides to pursue it commercially ahead of demand, accepting the
   custody and infra work below with eyes open.

Design decided now (cheap) so it is not re-litigated later:
- **Storage:** one row per payer, `entry_id = payerId` — **not** the Phase 1
  singleton (see the measured table above).
- **Custody:** must be resolved *before* any private key is stored. Options
  worth weighing then: per-tenant key derivation, a real KMS, or — likely
  best — **never hold the key at all**, and have the practice register
  SAIRN's own JWKS so the signing key stays SAIRN-side and no practice
  private key is ever custodied. That last option inverts the problem and
  deserves first consideration.
- **Infra:** a publicly reachable, stable JWKS endpoint. New requirement; the
  single-file + serverless model can host it, but it becomes a versioned
  contract like `/api/bridge`.

---

## Open questions for Michael

1. **Is 2a's real target the payer packet, or the coder's own file?** A draft
   that goes to a payer carries the RMF risk above. A draft that only helps a
   coder assemble their own notes is much lower stakes. This changes how hard
   the sign-off gate needs to be.
2. **Do you want the `submittedVia: FHIR PAS` option visible-but-disabled, or
   absent entirely until 2c ships?** Visible-but-disabled signals roadmap;
   absent avoids any implication of a capability that does not exist. Leaning
   absent, consistent with how this app has handled unbuilt things.
3. **On 2c's custody question** — is "practices register SAIRN's JWKS, we never
   hold their private key" acceptable to you as the target design? It removes
   the worst risk but means SAIRN is cryptographically acting on their behalf,
   which is its own conversation.
4. Want `graphify` run over the repo? It is disabled for model invocation but
   the CLI works.

---

## Verification (when 2a/2b are approved and built)

Standard Push Protocol. Specific to this phase:

- The CMS clock math (72h / 7d) isolated-logic tested against real dates
  including boundaries, the way the denial aggregation and citation checks
  were — not asserted from reading the code.
- A request with no `submittedOn` must render as "not submitted", never as an
  overdue clock computed from `undefined`.
- The unverified-citation path proven to actually fire, by feeding a
  fabricated quote — the same way `quoteFoundInNote(false)` was proven in
  item 2 rather than waiting for the model to misbehave.
- `sc_auth_requests` confirmed live through the resource allowlist and the
  delete gate by real curl, with a bogus resource name as the contrast
  control.
- Confirmed that existing `sc_auth` rows are untouched and still render
  correctly after the new resource exists.

**Recurring blocker unchanged:** new migrations cannot be run from a coding
session. `sc_auth_requests` would join the queue alongside the still-unrun
`sairncode_denial_events_schema.sql`, `sairncode_credentials_schema.sql`, and
`sairncode_eligibility_schema.sql`.
