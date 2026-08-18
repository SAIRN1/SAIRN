# SAIRNcode — Real Data Layer + Per-Employee Auth (closing the Phase-2 gap)

**Status:** Design drafted 2026-08-18, pending review. Not yet implemented.

Context: Michael asked to bring SAIRNcode up to the same 5-capability
AI-advancement standard already on StoneDesk/SAIRNbuild/SAIRNvet (AR
measurement, agentic follow-up, predictive business intelligence, voice
input, shared company-knowledge). Checking first (per instruction) found
all 5 already shipped 2026-08-05/2026-08-08 and still live — including AR
measurement being correctly evaluated and excluded after a real fit-check
("no sqft/measurement/dimensions workflow... medical coding/billing
platform"). Nothing to build on the literal checklist.

Checking the real data model underneath (also per instruction) found a
materially bigger, real gap: SAIRNcode never got the "Phase 2: real data
layer, per-employee auth" pass every comparable app (StoneDesk,
SAIRNgrounds, SAIRNscape) already has. Michael confirmed 2026-08-18: close
this gap — this spec covers that.

## 0. What's real right now (verified 2026-08-18, not assumed)

**Every clinical/business resource is local-only.** 13 distinct
`localStorage` keys hold real app data with zero server sync:
`sc_anesthesia`, `sc_ar`, `sc_compliance`, `sc_denial`, `sc_drg`,
`sc_encoder`, `sc_fraud`, `sc_hcc`, `sc_prebill`, `sc_providers`,
`sc_rac`, `sc_revenue`, `sc_telehealth`. Only two resources are actually
server-backed: `profile` and `shared_knowledge` (confirmed live via curl
with the real demo license, `SC-PINNACLE-2026` — that license is valid
today; the file's own "KNOWN GAP" comment claiming it 401s is stale,
someone closed it without updating the comment).

**Several local-only resources ship hardcoded fake-name fallback data.**
`getProviderEntries()` (`sairncode.html:2465`) returns a seeded default —
"Dr. Michael Chen," "Dr. Sarah Martinez," "Dr. James Patel" — when
`localStorage` is empty. On a fresh device/browser, the `get_providers`
agentic tool (`sairncode.html:2508`) would hand the AI, and therefore the
user, these fabricated names as if real. 15 separate `var seed = [...]`
blocks exist in the file (`sairncode.html:1594` onward) — not all are
necessarily fabrication risks (some may be genuinely-labeled example/
placeholder rows), but each needs individual review, not a blanket
assumption either way.

**RBAC is a hardcoded, shared, global PIN set — a live severity finding,
not a style nit.** `sairncode.html:1301`:

```javascript
var PINS = { coder: '1234', biller: '2345', auditor: '3456', admin: '4567' };
```

Identical for every SAIRNcode customer, in a **public** GitHub repo
(`SAIRN1/SAIRN`, confirmed via the Vercel deployment metadata's
`githubRepoVisibility: "public"`). `requireAdminForDelete()`
(`sairncode.html:1310`) is the only place `currentRole` is ever checked —
gating the 15 `remove*()` delete functions — and it's a pure client-side
`var`, trivially bypassable via devtools (`currentRole='admin'`) even
without knowing the PIN at all. This is the exact "DEFAULT_PINS = one
shared PIN per role... any role self-assertable by editing the DOM"
anti-pattern `sql/sairnlaw_employee_auth_schema.sql`'s own header
describes replacing elsewhere on this platform (§8 of that file) — same
bug class, unaddressed here, currently live and public, gating delete
access on real medical billing/coding records.

## 1. Scope of this pass

1. **Real per-employee auth**, mirroring `sql/sairnlaw_employee_auth_schema.sql`'s
   proven shape exactly (scrypt `pin_hash`/`pin_salt`, `license_hash`-scoped,
   `role` enum, `active`/`failed_attempts`/`locked_until` lockout fields) —
   role vocabulary `coder | biller | auditor | admin`, matching the roles
   the UI already presents. Kills the shared hardcoded-PIN vulnerability
   at the root, not just re-gates it harder client-side.
2. **Server-side RBAC re-check for every delete action**, same pattern as
   `a8afe3e` (SAIRNgrounds sale-void, SAIRNgrounds+SAIRNscape progress-photo
   QC-decision) — `requireAdminForDelete()` staying client-side-only, even
   backed by real auth, still means a compromised/tampered client could
   claim "admin" in the request; the server must independently verify the
   session's real role before honoring a delete, not just trust the client
   asserted it once at login.
3. **Real server-synced tables for all 13 `sc_*` resources**, following
   `api/sd-data.js`'s exact established convention: add `sc_denial: true`
   etc. to the `RESOURCES` map (`api/sd-data.js:34`), add
   `if (resource === 'sc_denial' && action === 'read')`-style branches,
   one new `sql/sairncode_data_schema.sql` migration, graceful `provisioned:
   false` degrade if the migration hasn't run yet — identical shape to
   every other app already in that file (`grd_*`, `scp_*`, `dnt_*`, etc.),
   not a new pattern invented for this app.
4. **Remove/replace the fabrication-risk seed fallbacks** — audit each of
   the 15 `var seed = [...]` blocks individually; delete or clearly
   `DEMO-ONLY, remove before real use`-label any block whose data could be
   mistaken for real (the "Dr. Michael Chen" class), matching Guardian
   0b's fabricated-content standard.
5. **One-time local→server migration path for existing users.** This app
   has been live since 2026-08-05 with local-only data — shipping real
   sync without a migration step would either silently lose existing
   users' data or silently duplicate it. Needs a real plan (likely:
   on first login after this ships, read whatever's in each `sc_*`
   `localStorage` key, POST it once to the new server resource, then
   switch reads/writes to server-authoritative) — full detail belongs in
   the implementation plan, flagged here as a hard requirement, not an
   afterthought.

## 2. Explicit non-goals for this pass

- No changes to the 5 already-shipped AI-advancement capabilities
  themselves (voice/insights/shared-knowledge/tool-calling/AR-exclusion) —
  they stay as-is; this pass makes the data underneath them real, not the
  capabilities.
- No new UI panels/features beyond what already exists — this is a data-
  integrity and auth pass, not a feature pass.
- No changes to any other app.

## 3. Security checklist applied (owasp-security pass)

- **A07 Authentication Failures / ASVS 6.3.2 (no default accounts)** —
  the hardcoded shared PIN set is the headline finding; real per-employee
  credentials close it.
- **A01 Broken Access Control / ASVS 8.3.1** — delete authorization moves
  to a trusted server-side check, matching `a8afe3e`'s precedent; client
  state is never the final word.
- **ASVS 7.2.3** — new PINs get real `scrypt` hashing with a per-row salt,
  same as every other `*_employee_auth` table on this platform, never
  stored or compared in plaintext.
- **Guardian 0b (fabricated content)** — every seed-fallback block gets
  individually reviewed, not blanket-trusted or blanket-deleted.
- **A09 Logging** — failed PIN attempts and lockouts logged the same way
  `sairnlaw_employee_auth`'s `failed_attempts`/`locked_until` columns
  already do; no new logging infra needed, just the same columns.

## 4. Open questions before an implementation plan gets written

1. **Migration timing/UX** — does existing local data get migrated
   silently on next login, or should there be a visible one-time "syncing
   your data" step the user sees? Affects the implementation plan's
   client-side flow directly.
2. **Employee bootstrap** — same pattern as SAIRNlaw (`action:'bootstrap'`
   creates the firm's first Owner/Admin, `action:'setup'` for everyone
   after), or does SAIRNcode need something different since it currently
   has no concept of "employees" at all, only shared role PINs?
3. **Seed-fallback audit** — should I do the full 15-block review as part
   of this same implementation pass, or as a quick separate pass before it
   (faster to review in isolation, since some blocks may turn out to be
   fine as-is and not worth bundling into the bigger auth/sync change)?
