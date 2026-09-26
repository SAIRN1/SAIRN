# SAIRNcare family/resident portal — scoping, not a build

**Written 2026-09-25 (Hank).** Scope only, by instruction: panel shape, data
model, and the real integration points with the MAR and Care Plans panels. The
build is a later dispatch.

**Measured before anything was designed**, because this platform has twice
nearly rebuilt something it already had:

| Question | Answer, measured |
|---|---|
| Portal markers in `sairncare.html` | **0** — `grep -ci portal` returns zero. There is no portal concept in the app. |
| A family/responsible-party record on a resident | **None the app collects.** `sql/sairncare_clients_schema.sql`'s own comment lists `emergency_contact` among the `data` jsonb fields — and the UI never writes or reads it. The only "emergency" in `sairncare.html` is emergency-preparedness drills in the Operational Audit panel. |
| An existing portal on the platform | **YES — and it is the thing to copy.** `api/sen-portal.js` + `sql/sairnsenior_portal_links_schema.sql`, SAIRNsenior's family/client portal, built to Michael's explicit instruction. |

**So this is not a design problem, it is a port plus one genuinely new
decision.** The security model is settled and running; what is not settled is
what a family member may see in a *licensed residential* setting, which is a
different question from what they may see about a home-care visit schedule.

---

## 1. The security model is inherited wholesale. Do not redesign it.

`api/sen-portal.js`'s header states it and `sql/sairnsenior_portal_links_schema.sql`
argues it at length. Every line of it transfers:

- **Family is a different ACTOR CLASS from an employee.** Not a PIN account, not
  an extension of `sairncare_employee_auth`. There is no login, no PIN, no
  session on the family side.
- **The token IS the credential** — 32 bytes of `crypto.randomBytes`, 64 hex
  characters, unique-indexed, looked up directly on every read.
- **There is no `client_id` parameter on the read action.** The resident the
  token resolves to is never supplied by the caller and never trusted from
  anywhere but the links table. *A family member cannot reach another
  resident's record by editing a parameter, because there is no parameter to
  edit.* This is the single most important property and it is a shape, not a
  check — it cannot be forgotten in a later refactor the way a permission test
  can.
- **Revoke, never delete.** `active=false` + `revoked_at`, so staff can see
  revocation history — the same discipline every `*_employee_auth` table keeps.
- **The token is never re-displayed** after creation. If staff needs the URL
  again, revoke and issue a new one. Same rule as PIN hashes.
- **`create`/`revoke`/`list` still require a real employee session.** Only the
  read action runs without one.

**What must be re-decided rather than copied:** who may create a link.
SAIRNsenior mirrors its `sen_clients` write gate — broad tier for any client, a
caregiver only for a client assigned to them. SAIRNcare's equivalent gate is
`alf_clients`, and `sairncare.html` already carries `alfIsBroadRead()` and
`alfIsReadOnlyBroad()` with an **Activities role that is read-only on
residents**. Whether an activities coordinator may hand out a family link is a
product decision, not a copy.

---

## 2. The data model — and the part that will surprise whoever builds it

### Residents are `alf_clients`, and the care plan lives INSIDE the resident row

There is **no `alf_careplans` table and no `alf_careplans` resource.** The app's
own cache-purge comment records this in so many words: *"the first version of
this array named `alf_careplans`, which is not a key this app ever writes."*

`rCareplans()` reads `r.adl_assessments` off each resident — an array inside the
`alf_clients.data` jsonb, appended by `openAdlModal()`. Each entry carries a
date, an `assessed_by` employee id, the ADL domain scores and notes.

**Three consequences for the portal, and the third is the trap:**

1. A "care plan" surface in the portal is a read of `alf_clients.data
   .adl_assessments`, not a join to another table.
2. `alf_clients.data` has a **64KB size constraint**
   (`alfclients_data_size`). Assessments accumulate in that budget. A portal
   that encourages more frequent assessment pushes against a ceiling that
   already exists — worth knowing before, not after.
3. **The AI-drafted care plan (`openCarePlanAiModal`) is model output.** If any
   of it ever reaches a family member, this app will be showing generated
   clinical prose to a resident's relative. That is a decision with real weight
   and it should be made explicitly, not inherited by a field being in the blob.

### The three server resources a portal would touch

| Resource | What it is | Portal posture |
|---|---|---|
| `alf_activities` | The activities calendar. Its registry entry already records a **broad-read / narrow-write** design. | **The obvious first surface.** Closest to SAIRNsenior's "upcoming visits", lowest sensitivity, and a family member seeing next week's activities is the feature families actually ask for. |
| `alf_clients` | The resident record — name, room, DOB, diagnosis, care level, payer type. | **Name and room only.** Diagnosis, care level and payer type are not portal data. SAIRNsenior's `view` returns client name and visit windows and explicitly no diagnosis, no authorised hours, no caregiver identity — that list is the precedent. |
| `alf_mar` | The medication administration record. | **See §3. This is the whole question.** |

`alf_billing`, `alf_incidents`, `alf_staff`, `alf_op_audits`,
`alf_staff_credentials` and `alf_compliance_rules` are **not portal surfaces**
and should not become ones by accident. `alf_incidents` in particular carries an
asymmetric read/write design for reasons its schema header gives.

---

## 3. The MAR is the real decision, and it is not a technical one

SAIRNsenior's portal shows **visit schedule**. SAIRNcare's equivalent question is
whether a family member sees **medication administration** — and the two are not
comparable. A MAR entry is a clinical record of a controlled act, and this
platform already treats the SAIRNcare MAR as high-sensitivity.

**Three postures, and they are genuinely different products:**

- **A. Nothing from the MAR.** The portal shows activities and a resident name.
  Safest, ports cleanly, and is what SAIRNsenior does. It will also read as thin
  to a family that was told there is a portal.
- **B. Administration EVENTS without the drug.** "Morning medications given at
  08:14" — the fact that care happened, not what was given. This is the shape
  that answers the question families actually ask ("is she being looked after")
  without disclosing a medication list.
- **C. The MAR itself.** Only defensible where the family member is the
  **resident's legal representative**, which the app has no field for today (see
  §2's first table) and no way to verify.

**This is Michael's call, and it should be made before any schema is written,**
because A and B want the same table and C wants a representative-authority
concept that does not exist. Building A first and adding C later is a schema
change plus a legal question; building C first is a legal question now.

**What this document will not do is recommend C by default because competitors
ship it.** The research note behind this item says a portal is table stakes for
the category; it does not say a MAR view is.

---

## 4. The shape of the build, if and when it is dispatched

Ordered so each step is useful alone and nothing is half-built:

1. **`sql/sairncare_portal_links_schema.sql`** — a near-copy of
   `sairnsenior_portal_links_schema.sql` with `client_id` meaning an
   `alf_clients.client_id`. Keep the header's security argument, do not
   summarise it.
2. **`api/alf-portal.js`** — `create` / `revoke` / `list` / `view`, the first
   three employee-gated, `view` taking the token and nothing else. The
   minimum-necessary payload is **posture A** until Michael decides otherwise.
3. **A Family Links card inside the existing Residents panel**, not a new
   nav item. Issuing a link is something you do *to a resident*, and a separate
   panel would invite a "manage all links" screen that nobody needs.
4. **The family-facing page** — its own file
   (`sairncare-family.html`), like `stonedesk-intake.html` and
   `sairndental-book.html`. It must not be a mode of `sairncare.html`: that file
   carries the employee session, the PHI caches and the role logic, and shipping
   it to an unauthenticated audience is how a cache leak becomes a disclosure.
5. **`tests/` arms before anything is called done**, and the four that matter:
   a token resolving to exactly one resident; a second resident's data
   unreachable with a valid token; a revoked token refused; and the payload
   asserted **field by field** against an allow-list, so a later field added to
   `alf_clients.data` cannot arrive in the portal by being in the blob.

**The PHI cache discipline applies to the family page too.** `sairncare.html`
keeps `ALF_SCOPED_CACHES`, purged when the employee or role changes, held by
`tests/phi_cache_scoped_to_user.js`. A family page that caches anything needs
the same treatment or an explicit "caches nothing" statement — and a probe
either way.

---

## 5. What is NOT scoped here, named rather than implied

- **Resident (not family) self-access.** The item says "family/resident portal".
  A resident reading their own record is a different actor with different rights
  and a different consent question, and nothing in this document addresses it.
- **Two-way communication.** Messaging, requests, acknowledgements. SAIRNsenior's
  portal is read-only and the reasoning transfers.
- **Whether the link satisfies any HIPAA requirement.** A revocable bearer link
  is an access-control mechanism, not a compliance conclusion, and this document
  does not assert it is one. That is a `sairn-decision-gate` question before any
  claim is made to a customer.
- **The MAR posture.** §3 lays out three options and deliberately picks none.

---

## Where this sits

- `api/sen-portal.js`, `sql/sairnsenior_portal_links_schema.sql` — the working
  precedent. **Read both headers before writing a line.**
- `sql/sairncare_clients_schema.sql` — the resident row and its 64KB `data`
  ceiling.
- `sql/sairncare_mar_schema.sql` — the MAR's own research-grounded header,
  required reading before §3 is decided.
- `tests/phi_cache_scoped_to_user.js` — the cache discipline any new
  family-facing surface inherits.
