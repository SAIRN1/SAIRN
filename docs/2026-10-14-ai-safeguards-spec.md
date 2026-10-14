# AI safeguards — SPEC ONLY — 2026-10-14

**ROUTED TO: hank (`api/`, `sql/`) and cody (`tests/`).** Nothing under `api/`,
`sql/` or `tests/` is written by this document. It is a specification and a
list of acceptance tests; the code is theirs.

**AUTHORITY AND DATE.** The requirement is **Anthropic's usage policy, in
effect 2026-11-12**. That is 29 days from this document. **The final
customer-facing WORDING is not settled here and must not be shipped from this
document** — Michael's cousin, a lawyer, reads the final wording. Everything
below is **mechanism**: where a fact is stored, what is shown, what is logged,
and what must fail closed. Where wording is unavoidable it is marked
`[DRAFT — LAWYER]` and is a placeholder.

**MICHAEL'S DECISION, AND THE SPEC DOES NOT RE-OPEN IT.** Simple design, and
**no repeat popups**. Every safeguard below is one-time-per-person or inline.
Anything that would nag a user twice is out of scope by decision, not by
oversight.

**ONE TERM CORRECTED BEFORE IT PROPAGATES: there is no face recognition on
this platform.**

```
CMD grep -rin "face[-_ ]?login|facelogin|face recognition" --include=*.js --include=*.sql --include=*.md api/ sql/ docs/
(no output)
```

So **"first face-login" is read as the first interactive login at the app's own
login face** — the PIN screen served by `api/<prefix>-auth.js`. If Michael
meant a future biometric login, this spec still holds: the ack hangs off the
employee credential row, whatever proves identity.

---

## 1. THE FIVE SAFEGUARDS

### (a) ONE-TIME AI notice, acknowledged per user at first login

* Shown **once per employee**, at the first successful login after the notice
  version ships. Acknowledged by one button.
* Stored **under that employee's login**: the notice **version** and the
  **date**.
* **Never shown again** unless the notice version changes.
* `[DRAFT — LAWYER]` *"This app uses AI to make suggestions. Suggestions can be
  wrong. A person is responsible for what is sent out or acted on."*
* **NOT** a modal on every AI panel. **NOT** a per-session banner. **NOT** a
  consent the user can withdraw — it is a notice, acknowledged.

### (b) ONE-TIME owner acceptance, in the customer agreement

* The owner accepts **once per licence**, as part of the service agreement.
* **The owner is responsible for telling staff.** The platform does not chase
  employees, does not email them, does not report per-employee ack rates to
  the owner.
* Stored on the licence, with who accepted and when.
* **NOT** a second acceptance per app, per seat, or per renewal.

### (c) A small inline **Reviewed** button, ONLY on high-risk AI output

**ONLY where the AI output becomes a document or a decision**, which is five
categories and no others:

| # | category | examples on this platform |
|---|---|---|
| 1 | **legal documents** | SAIRNlaw drafts and citations, SAIRNlegacy estate documents |
| 2 | **medication or clinical suggestions** | SAIRNcare MAR/med suggestions, SAIRNvet treatment notes |
| 3 | **hiring, pay or discipline** | StoneDesk HR, SAIRNhr |
| 4 | **claim outcomes** | SAIRNroofing / insurance claim determinations |
| 5 | **investment or tax** | SAIRNcash, SAIRNacc |

* **Inline and small.** A button in the output's own footer row. Not a modal,
  not a blocking step, not a second confirmation.
* **The approver is logged**: who clicked, when, which output.
* **NOT on**: chat replies, search, summaries, drafting help that stays
  internal, greeting text, cost estimates, scheduling suggestions. A Reviewed
  button on everything is a Reviewed button nobody reads.

### (d) An "AI-assisted, reviewed by [name]" footer on anything leaving the building

* Applied to **outbound artefacts**: PDFs, printed documents, emailed
  quotes/invoices/letters, customer-facing portal documents.
* **The name comes from the (c) review row.** If nothing was reviewed, the
  footer reads **"AI-assisted — not reviewed"** rather than omitting the line.
  **An absent footer and an unreviewed document must not look the same.**
* **NOT** on internal screens.

### (e) Every chat or assistant surface says it is AI

* A persistent one-line label on the surface itself — not a popup.
* `[DRAFT — LAWYER]` *"AI assistant. Answers can be wrong."*
* **NOT** dismissible, because a dismissible label is a popup with extra steps.

---

## 2. DATA MODEL

### 2.1 (a) The per-employee ack — two columns on the EXISTING credential table

Every app already has `<prefix>_employee_auth` with `license_hash`,
`employee_id`, `role`, `pin_hash`, `active`, … (e.g.
`sql/grd_employee_auth_schema.sql:22`). **Add two columns, not a new table:**

```sql
alter table <prefix>_employee_auth
  add column if not exists ai_notice_version text,
  add column if not exists ai_notice_acked_at timestamptz;
```

* `ai_notice_version` — the notice version acknowledged, e.g. `2026-11`.
  **Text, not a boolean**: a boolean cannot express "acked the old wording".
* `ai_notice_acked_at` — when.
* **Nullable on purpose.** Null = not yet acknowledged, which is the state
  every existing row starts in and is not an error.
* **No `ai_notice_acked_by`** — it is the row's own employee, by construction.

### 2.2 (b) The owner acceptance — three columns on the licence row

```sql
alter table license_keys
  add column if not exists ai_terms_version text,
  add column if not exists ai_terms_accepted_at timestamptz,
  add column if not exists ai_terms_accepted_by text;
```

`ai_terms_accepted_by` is the owner's `employee_id` or the contracting name
captured at signature. One row per licence; **never per app and never per
seat.**

### 2.3 (c) The review row — the EXISTING audit log, and ONE HAZARD THAT WILL BITE

Reviews go into the app's existing `<app>_audit_log`, with a new
`event_type` of **`ai_output_reviewed`** and a payload carrying
`surface`, `risk_category` (1–5 above), `output_hash`, `reviewer_employee_id`.

**THE HAZARD, AND IT IS MEASURED, NOT PREDICTED:** those tables constrain
`event_type` with a `CHECK (event_type in (...))` list —

```
CMD grep -rn "check (event_type" sql/*.sql | head -4
sql/sairnbiz_audit_log_schema.sql:31
sql/sairnbuild_audit_log_schema.sql:31
sql/sairncare_audit_log_schema.sql:31
sql/sairncode_audit_log_credential_events.sql:30
```

**An insert with an unlisted `event_type` is rejected by Postgres, and this
platform has already shipped audit writes that were rejected silently** — the
hover auditors' standing finding is *3 of 16 logs rejecting 11 emitted values*,
plus `sv_audit_log` with no `event_type` CHECK at all. So:

1. The DDL adding `ai_output_reviewed` to **every** app's CHECK list must land
   **in the same migration** as the write path, per app; and
2. **the write must fail LOUDLY.** A review that was not recorded must not
   render a footer naming a reviewer. See acceptance test T7.

### 2.4 (d) The footer — derived, nothing new stored

Rendered from the (c) row at document-generation time. **No new column**: a
document's footer is a function of its review row, and storing the footer text
would be a second copy of a fact that can drift from the first.

---

## 3. API SURFACE — hank (`api/`)

### 3.1 One shared helper, not seventeen copies

There are **17** per-app auth endpoints:

```
CMD ls api/*-auth.js
alf- bld- dnt- grd- law- leg- mech- rf- sb- sc- scp- sd- sd-sub- sdn- sen- sf- sv-
```

so the ack logic belongs in **`api/_lib/ai-safeguards.js`** beside the existing
`api/_lib/ai-rate-limit.js` and `api/_lib/ai-scan-redaction.js`, exporting:

| export | contract |
|---|---|
| `CURRENT_NOTICE_VERSION` | one constant, e.g. `'2026-11'` |
| `aiNoticeState(row)` | `{required: bool, version, acked_at}` from a credential row |
| `recordNotice(app, license_hash, employee_id, version)` | idempotent; **re-ack of the same version is a no-op, not a second row** |
| `ownerTermsState(license_hash)` | `{accepted: bool, version, at, by}` |
| `recordReview({app, surface, risk_category, output_hash, reviewer})` | writes the audit row; **throws on refusal** |
| `isHighRisk(app, surface)` | the §1(c) table, as data |

### 3.2 Login response carries the flag — no new endpoint for (a)

Each `*-auth.js` `login` action adds `ai_notice_required` and
`ai_notice_version` to its success payload. Acknowledgement is **one new action
on the same endpoint** (`ack_ai_notice`), authenticated by the session token
that login just issued.

### 3.3 `api/claude.js` is the chokepoint for (e), and it already is one

`api/claude.js` is the shared proxy every app's AI calls route through, with
`KNOWN_APP_IDS` at `api/claude.js:35`. The response gains a constant marker
(`ai: true`, `ai_label`) so **no surface can render an AI answer without having
been handed the label.** Per-app AI entry points that must carry it too:

```
CMD ls api/*.js api/*/*.js | grep -Ei "ai\.js|-ai|agent|claude\.js|citator|greeting" | grep -v test
api/claude.js  api/sc-ai.js  api/sairncash/ai.js  api/sd-agent.js
api/legal-citator.js  api/greeting.js  api/agent/{enqueue,poll,register,result}.js
```

**A MEASURED DEFECT FOUND WHILE WRITING THIS, hank's to fix or decline:**

```
CMD node -e "...match KNOWN_APP_IDS..."
count 21
stonedesk sairnbiz sairnscape sairncode sairnbuild sairnlaw sairndesign sairncare
sairnvet sairnfuneral sairnmechanical sairnhr sairnacc sairngrounds sairnlegacy
sairncash sairndental sairnsenior sairnsenior sairnfreedom sairnroofing
```

**`sairnsenior` appears TWICE** — 21 entries, 20 distinct (`api/claude.js:35`).
Harmless to `includes()`, and exactly the kind of duplicate that makes a
per-app safeguard rollout count 21 surfaces and verify 20.

---

## 4. PER-APP SURFACE LIST

**20 distinct app ids** (`api/claude.js:35`, de-duplicated) against **22
`*.html` front ends** (`ls *.html`). Risk column = §1(c) category, or `—` for
no Reviewed button.

| app id | front end | AI surface | high-risk category | Reviewed button |
|---|---|---|---|---|
| stonedesk | `stonedesk.html`, `stonedesk-hr.html`, `stonedesk-intake.html`, `stonedesk-catalog.html` | `api/sd-agent.js`, field-sketch quote | **3** (HR panel only) | HR panel only |
| sairnhr | — (platform HR) | `api/claude.js` | **3** | yes |
| sairnlaw | `sairnlaw.html` | `api/legal-citator.js`, `api/law-auth.js` scoped AI | **1** | yes |
| sairnlegacy | `sairnlegacy.html` | `api/claude.js` | **1** | yes |
| sairncare | `sairncare.html` | `api/claude.js`, ALF/MAR panels | **2** | yes |
| sairnvet | `sairnvet.html` | `api/claude.js` | **2** | yes |
| sairnroofing | `sairnroofing.html` | `api/claude.js` | **4** | yes |
| sairncash | `sairncash.html` | `api/sairncash/ai.js` | **5** | yes |
| sairnacc | — | `api/accounting.js`, `api/claude.js` | **5** | yes |
| sairnbiz | `sairnbiz.html` | `api/claude.js` | — | no |
| sairnbuild | `sairnbuild.html` | `api/claude.js` | — | no |
| sairncode | — | `api/sc-ai.js` | — | no |
| sairndesign | `sairndesign.html` | `api/claude.js` | — | no |
| sairnscape | `sairnscape.html` | `api/claude.js` | — | no |
| sairngrounds | `sairngrounds.html` | `api/claude.js` | — | no |
| sairnmechanical | `sairnmechanical.html` | `api/claude.js` | — | no |
| sairndental | `sairndental.html` + book/complaint | insurance-card capture | **2** if it suggests clinical coding | decide, then yes or a NOT_PROMOTED row |
| sairnsenior | `sairnsenior.html` | AI Assistant panel | **2** if care suggestions | same |
| sairnfuneral | — | `api/claude.js` | — | no |
| sairnfreedom | `sairnfreedom.html` | `api/claude.js` | — | no |

**Every row in the "no" column still needs (a), (b) and (e).** Only (c) and (d)
are scoped by risk. **The two "decide" rows are the only judgment calls in this
table** and they belong to whoever owns those apps' panels — not to me, and not
to a default.

---

## 5. ACCEPTANCE TESTS — cody (`tests/`)

**Each test names its BAD INPUT and the refusal it must produce.** Per
`docs/METHODOLOGY.md` (2026-10-13), a check with no deliberately-bad-input arm
proving it fails closed is not finished — and these are the arms.

| # | bad input / scenario | must happen |
|---:|---|---|
| **T1** | employee logs in, `ai_notice_version` is null | login payload has `ai_notice_required: true` and the current version |
| **T2** | same employee logs in again after acking | `ai_notice_required: false` — **no second prompt, ever** (this is the no-repeat-popups test) |
| **T3** | `ack_ai_notice` called twice with the same version | **idempotent**: one stored ack, `acked_at` unchanged on the second call |
| **T4** | notice version bumped to `2026-12` | `required: true` again for everyone, and the stored `2026-11` is **not overwritten until the new ack lands** |
| **T5** | `ack_ai_notice` called with **no session token**, or a token for a different employee, or a different `license_hash` | **401/403, nothing written.** Cross-tenant ack is the highest-value bug in this feature |
| **T6** | the ack UPDATE fails (DB error) | the API returns an error and the client **re-shows the notice next login**. **A failed ack must never read as acked** |
| **T7** | `recordReview` inserts `event_type='ai_output_reviewed'` into an app whose CHECK list does not include it | **the call throws and the UI shows the review did not save.** Must NOT return success, must NOT render a reviewer footer |
| **T8** | a high-risk output rendered with no review row | footer reads **"AI-assisted — not reviewed"**; the document still generates |
| **T9** | a **non**-high-risk surface | **no Reviewed button at all** — a test that fails if one appears, because scope creep here is what makes the button meaningless |
| **T10** | owner acceptance absent for a licence | app still works; **acceptance is an agreement artefact, not a runtime gate** (unless Michael says otherwise — see §7) |
| **T11** | owner acceptance recorded twice | one row, second is a no-op |
| **T12** | any `api/claude.js` success response | carries `ai: true` and a non-empty `ai_label` — asserted at the proxy, so a new surface cannot forget it |
| **T13** | all 20 app ids from `KNOWN_APP_IDS`, de-duplicated | each resolves to exactly one entry in the §4 table. **Catches the `sairnsenior` duplicate** |
| **T14** | a document generated by the PDF/print path | the footer line exists. **A missing footer fails the test**; an "AI-assisted — not reviewed" footer passes |
| **T15** | **CONTROL:** an app with no AI surface at all | no notice, no label, no button, and the tests **pass** rather than demanding a safeguard that has nothing to guard |

**T15 and T9 are the over-refusal guards.** A safeguard suite that fails every
non-AI screen gets switched off, and then none of T1–T14 runs either.

---

## 6. WHAT THIS SPEC DOES NOT DO

* **It does not settle the wording.** Both `[DRAFT — LAWYER]` strings are
  placeholders. Michael's cousin reads the final text; shipping my phrasing
  would be exactly the "AI wrote the legal notice" failure the policy is about.
* **It does not claim compliance.** It describes mechanism against a policy
  effective **2026-11-12**; whether the mechanism satisfies the policy is a
  legal reading, not a test result.
* **It does not touch `api/`, `sql/` or `tests/`.** No file in those
  directories is written by this batch.
* **It does not decide the two "decide" rows in §4**, and it does not decide
  whether (b) is a runtime gate.
* **It does not specify retention.** How long an ack or a review row lives is a
  data-retention question the DPA answers, not this document.

---

## 7. THE THREE QUESTIONS FOR MICHAEL, each answerable in one word

1. **Is (b) a runtime gate?** If an owner has not accepted, does the app's AI
   still answer? Spec'd as **no gate** (T10) because a gate turns a paperwork
   gap into an outage. One word changes it.
2. **SAIRNdental and SAIRNsenior** — are their AI outputs clinical (category 2,
   Reviewed button) or not? Two one-word answers.
3. **Notice version string** — `2026-11` as spec'd, or tie it to the agreement
   version the lawyer approves? If the lawyer changes the wording after launch,
   the version string is what re-prompts every user exactly once.
