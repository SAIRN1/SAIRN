# Tier A review — DISCHARGE of hank's b11 obligation (33 resources, 3 surfaces)

**Obligation:** author `hank`, opened `2026-10-14T17:56:56Z`, **33 resources**,
5 files — `api/_lib/sv-roles.js`, `api/_resources/sairncare.js`,
`api/ai-provenance-client-sites.test.js`,
`api/sd-data-sv-role-matrix.test.js`, `api/sd-data.js`.
**Assigned to `fourth`; discharged at ~9h, INSIDE the 24h deadline.**
**Reviewer:** fourth, 2026-10-14, batch b21. `git cat-file -e d19971890058` →
**RESOLVES**, so this is a real diff review.

hank named three surfaces and a different thing to attack hardest on each. All
three were attacked. **Two surfaces survive. The third carries a finding that
silently voids the thing the change was for.**

---

## 0. VERDICT

| # | surface | hank's hardest-check | verdict |
|---|---|---|---|
| **1** | `alf_family_contacts` — `family_mar` loses the inherited read roles for a named, time-limited, audited grant | the grant-lookup ordering; the in-memory re-check; a 404/400 falling through to refusal | **THE MECHANISM IS RIGHT AND THE HEADLINE CLAIM IS WRONG.** Fail-closed holds, expiry holds, audit-on-use holds, the grant writer is `office_manager` only. **But billing is NOT refused by default (F1), the existence oracle survives for exactly that role (F2), and billing can bypass the grant entirely with a write it already has (F3)** |
| **2** | the 42 `sv_` resources | that `sv_controlled` is DERIVED from `PRESCRIBER_ROLES`, that `api/sv-witness.js` is untouched, that the append-only lock binds the owner | **ALL THREE VERIFIED.** 42 rows by three agreeing counts; one `decide()` before both dispatch branches, no bypass; no widening anywhere; two resources strictly narrow |
| **3** | `rf_photos` stamped `ai_source`, switching `HIGH_RISK_AI` on in production | whether *"reviewed by"* is honest when the operator reviews quantities, not prose | **THE HONESTY QUESTION IS THE WRONG WORRY, BECAUSE THE RECORD CARRIES NO CLAIM AT ALL (F4).** The gate fires, the approval is written onto the payload, and the handler then rebuilds the record and drops it. `aiFooter()` returns `''` |

**DISCHARGE VERDICT: surface 2 is clean. Surface 1's plumbing is sound and its
stated guarantee is not. Surface 3's gate works and its attribution does not.**
Four findings, none fixed here.

---

## 1. WHAT I OPENED, AND WHAT I LOOKED FOR

| opened | looked for |
|---|---|
| `api/sd-data.js`'s `family_mar` branch, statement by statement; `ALF_FAMILY_MAR_ROLES`, `ALF_FAMILY_READ_ROLES`, `ALF_MAR_GRANT_ROLES`, `ALF_MAR_GRANT_GRANTEE_ROLES`; the grants lookup and its status handling | the ORDER of role check / grant lookup / contact fetch; whether any 404/400/500/throw grants or skips; what the in-memory re-check covers |
| the `alf_clients` write path and `ALF_MANAGEMENT_ROLES` | whether a role refused at `family_mar` can put itself inside the tier that admits it |
| `api/_lib/sv-roles.js` — four band templates, the 42-row table, `decide()`, `isAppendOnly()` | the count, the single call site, and whether any `sv_` branch dispatches without passing the gate |
| `api/sv-auth.js`'s `PRESCRIBER_ROLES` and its export | whether `sv_controlled` is derived BY REFERENCE or re-listed as a literal |
| `git log -- api/sv-witness.js` and `git show --stat d19971890058` | whether the witness file is in the commit |
| `sairnroofing.html`'s `saveMeasurementReading()` and the measurement panel markup; `api/sd-data.js`'s `rf_photos` write; `api/_lib/ai-safeguards.js`'s `enforceAiApproval` and `aiFooter` | what the operator sees, what the gate writes, and what actually lands in the row |
| `tests/mar_billing_grant.test.js`, `api/sd-data-sv-role-matrix.test.js`, `api/ai-provenance-client-sites.test.js` | which claims are DRIVEN and which are asserted in isolation. **No suite was executed** |

---

## 2. SURFACE 1 — the mechanism is right; the guarantee is not

### What holds, said first

* **The role sets are separate and billing is out of the MAR set.**
  `ALF_FAMILY_MAR_ROLES = roleSet({ owner: true, nursing: true })`;
  `ALF_FAMILY_READ_ROLES` is referenced exactly once more, in the `read`
  action. `family_mar` no longer inherits.
* **FAIL-CLOSED ON THE GRANTS TABLE — hank's load-bearing claim, and it holds
  on every path I could construct.** 404/400 → the block is skipped and
  `marGrant` stays `null`; 403/401/500/503 → `!gr.ok` → `upstream()` → 502;
  a non-array 200 body → `null`; a `.json()` throw or a network throw → the
  outer catch → 502. **No path grants access and none skips the check.**
* **The in-memory re-check covers all three fields hank named** —
  `contact_id`, `grantee_employee_id`, `expires_at` — **plus `revoked_at`,
  which hank did not claim.**
* **Expiry is server-clock and numeric**, `Date.parse(g.expires_at) > nowMs`,
  against the **stored** value normalised at write time; a null `expires_at`
  is **refused**, not treated as open-ended; and creation refuses an absent,
  unparseable, past or >72h expiry.
* **Grant USE is audited, not just creation** — `mar_access_read` with the
  `grant_id`, alongside `mar_access_granted` and
  `mar_access_grant_refused`, all three in the audit table's CHECK list. **So
  "who looked" is recorded, which is the half that usually is not.**
* **Only `office_manager` may write a grant.** A billing session cannot grant
  itself and a grantee cannot extend its own grant — same gate, and the
  refusal is itself audited.

**That is a well-built control, and the fail-closed and audit-on-use halves are
better than the claim made for them.**

### F1 — billing is NOT refused by default

**There is no 403 on the role in the `family_mar` branch.** The role check
computes a boolean:

```
const marBroad = !!ALF_FAMILY_MAR_ROLES[session.role];
```

and nothing refuses on it. A grantless caller falls through to an
**assignment-scope tier**, whose only hard refusal is the empty-scope case
(*"No residents are assigned to you."*). **So "billing is refused by default
and gets in only via a grant" is false: billing also gets in by being assigned
the resident.**

### F2 — the existence oracle survives for exactly the role the change is about

hank's own hardest-check is *"a billing session with no grant must be refused
BEFORE the contact row is fetched (existence oracle)."* **The grant lookup does
precede the fetch — that part is right.** But the scope test is applied
**after** it:

```
const cr = await fetch(rest('alf_family_contacts?...&contact_id=eq.' + ...));
...
if (!marBroad && !marGrant
    && marScope.indexOf(String(contact.resident_id)) === -1) { 403 }
```

**A grantless billing session with ANY assigned resident passes the empty-scope
refusal, reaches the fetch, and can therefore distinguish `404
NO_SUCH_CONTACT` from `403 FORBIDDEN` for an arbitrary `contact_id`.** The
property hank wanted holds only for a caller whose assignment scope is empty.

### F3 — the bypass, and it is the finding

```
const ALF_MANAGEMENT_ROLES = roleSet({ owner: true, billing: true });
...
if (!isManagement && isBroadEdit) { ...assignment must not change... }
} else if (!isManagement) { ...narrow tier... }
...
assigned_employee_id: requestedAssignee,     // written verbatim
```

**`isManagement` includes `billing`, and it skips BOTH assignment
restrictions.** So a billing session may POST `alf_clients` with
`assigned_employee_id` set to its own `employee_id`, then call `family_mar` and
be admitted by the assignment tier — **with no grant row, and no
`mar_access_read` audit row, because that write is conditioned on
`if (marGrant)`.**

**The new control is bypassable by a write the same role already holds, and the
bypass is silent in the audit log.** *"Gets in only via a named, time-limited,
audited grant"* is false as stated.

**ROUTED TO hank:** refuse on the role in the `family_mar` branch before the
scope tier, or exclude `billing` from the assignment tier for this action.
**ROUTED TO cody:** the failing-first arm is a billing session that
self-assigns via `alf_clients` and then reads `family_mar` — it must be
refused, or at minimum audited.

### Two more, smaller

* **`license_hash` is server-filtered only and never re-verified in memory** —
  it cannot be, because the selected grant columns do not include it. The
  belt-and-braces re-check has its one hole on the tenant key.
* **No revoke action exists.** The read path honours `revoked_at` and the
  schema comment asserts the capability, but the resource registers only
  `family_mar` and `mar_access_grant`; nothing writes `revoked_at`. **Only
  direct database access can revoke a live grant.**

### And one thing that makes the whole surface less useful than it reads

**The granted read is still gated on family consent and yields no medication
data.** The projection is `date`, `time`, `status` over administration entries
only, and the view refuses an inactive contact or one without `mar_consent`.
**So an `office_manager` grant admits a billing clerk to a date/time/status
list, only if the family contact consented, and never to the medication names
coding work needs.** The access control is sound; it is wired to a view that
cannot serve the stated purpose. **That is hank's design question, not a
defect, and it is worth deciding before more is built on it.**

### Test coverage

| hank's hardest-check | arm |
|---|---|
| ordering (F2) | **effectively NONE.** An arm claims it, but its evidence is the status code alone — the fixture records only non-GET calls, so no GET ordering is observable, and its fixture gives the caller no assignment, so the oracle case is never driven |
| fail-closed (the one that holds) | **NONE EXISTS.** The grants mock is unconditionally 200 |
| expiry | **COVERED** — an expired row still in the table yields 403, plus ceiling arms |
| audit-on-use | **COVERED** — a granted read logs `mar_access_read`, plus a CHECK-constraint arm |
| the F3 bypass | **NONE** |

**So the two halves that hold are the two with arms, and the three findings are
in the three places with no arm or a vacuous one.** That is not a coincidence
worth passing over.

---

## 3. SURFACE 2 — all three checks verified, and nothing widened

* **42 resources, by three agreeing counts:** manual per band (23 REGULATED +
  4 MONEY + 13 OPERATIONS + 2 REFERENCE), `grep -cE "^  sv_[a-z_]+: +row\("`
  → 42, and `SV_RESOURCES` in `api/sd-data.js` → 42 keys. The section headers'
  own counts match.
* **ONE `decide()` and no bypass.** `grep -n "svRoles" api/sd-data.js` returns
  the require plus four lines in one block; the gate block opens on
  `if (SV_RESOURCES[resource])` and the two dispatch branches open **after** it
  on the identical predicate, so fall-through is the only route in. The session
  is verified against `'sairnvet'` first, so the role is never from the
  payload. `api/sd-data.js` is the only route to these tables.
* **`sv_controlled` IS DERIVED BY REFERENCE, not re-listed.** The row is built
  from an imported `PRESCRIBER_ROLES` in a loop that starts every role at
  refused and raises only prescribers — so a seventh role gets nothing by
  construction. **The literal `{owner, dvm}` exists in exactly one place on
  disk.** This is the copy-exactly trap avoided rather than walked into, and an
  arm pins the derivation role by role.
* **`api/sv-witness.js` is untouched.** Two commits in its whole history,
  neither the obligation's commit nor the commit that introduced the matrix.
  Its lock still runs, inside the write branch, now behind the role gate.
* **The append-only lock binds the owner.** The rule is keyed by resource only;
  the predicate takes no session; the deciding `if` reads `action`, `resource`
  and `payload.id` and **never the role**; it sits after `decide()` so no grant
  can reach past it; and the refusal message says so in as many words. There is
  no delete action for any `sv_` resource.
* **NO WIDENING, and it is establishable rather than assumed:** the handler
  diff is **56 insertions and zero deletions**, the only prior per-resource
  check (the witness lock) is intact, and the prior state for the other 41 was
  *any verified session, read and write* — the widest possible — so every new
  row is a subset. **`sv_controlled` and `sv_audit_log` both strictly narrow.**

**Two residuals, neither a finding against this change:** the append-only lock
is application-level, because the schema still grants `update` on
`sv_audit_log` to `service_role` (no `delete` grant anywhere, on any `sv_`
table); and `SV_RESOURCES` is a plain object literal, so a prototype key such
as `constructor` enters the gate block — it then gets `NOT_SV` rather than
`DENY`, queries a table of that name, 404s and returns an empty provisioned
answer. **Harmless today. Worth noting only because `SV_ROLE_MATRIX` was given
a null prototype for exactly this reason and `SV_RESOURCES` was not.**

---

## 4. SURFACE 3 — F4: the gate fires and the record carries no claim

hank asks whether *"reviewed by"* is an honest claim. **The prior question is
whether there is a claim at all, and there is not.**

```
CMD sed -n '8431,8435p' api/sd-data.js
  const photoData = {
    photo_base64: payload.photo_base64,
    ai_analysis: String(payload.ai_analysis || '').slice(0, 20000),
    parsed_quantities: ... };
CMD grep -n "ai_source\|ai_approved" api/sd-data.js
  2074:    // `ai_source`. A server cannot look at prose and know a model wrote it, so
       (one COMMENT line, and nothing else in the whole file)
```

**`enforceAiApproval` mutates `payload`; the `rf_photos` branch does not store
`payload`.** It rebuilds the record from three named fields and persists that.
So `ai_source`, `ai_approved_by` and `ai_approved_at` **never reach the row** —
and the redaction helper copies its input, so it cannot reintroduce fields that
were never there.

**The consequence is the one the safeguard exists to prevent:**

```
CMD sed -n '215,220p' api/_lib/ai-safeguards.js
  function aiFooter(payload) {
    if (!payload || !payload[AI_SOURCE_FIELD]) return '';
    ...
    return 'AI-assisted, reviewed by ' + by;
```

**`aiFooter()` returns `''` for the stored record — so it renders NO footer at
all, not even the "AI-assisted — not reviewed" line that exists specifically so
that an absent footer and an unreviewed one cannot read the same.** Nothing
distinguishes an approved `rf_photos` row from a pre-change unflagged one.

**The enforcement half works** — no session still yields 403
`AI_APPROVAL_REQUIRED`. **"The gate fired" and "the record says who approved
it" have come apart**, and only the first is true.

### Why no arm caught it

**Two arms exist and neither can see it.** One asserts the literal `ai_source:`
appears in the client function's body — a text test over the HTML. The other
drives `enforceAiApproval` **in isolation** and asserts the **local payload
object** was mutated. **Neither routes `rf_photos` through
`api/sd-data.js`.** The end-to-end footer assertion does exist — on
`mech_quotes`, whose branch stores the payload wholesale. **The resource that
was switched on is the one resource whose handler rebuilds the record, and the
end-to-end arm was run on a different one.**

### On the honesty question hank actually asked

**The operator never sees the model prose.** The raw reply is parked in a
variable with four occurrences in the file — declaration, reset, assignment,
and the payload — and **is never written to the DOM**; the panel markup has no
raw-text element and no AI label. What the operator confirms is the extracted
numeric quantity form.

**hank's own disclosure is accurate about the human act** — *"the operator
reviewed the QUANTITIES … They did not necessarily re-read the model's prose.
'Reviewed by' on this record means the numbers were checked, which is the thing
the estimate is built from."* **I accept that, and the quantities are indeed
what the estimate is built from.** But the sentence's premise — *"the footer
will carry their name"* — **is false in this build**: there is no footer. And
when there is one, it interpolates the `employee_id`, not a name.

**ROUTED TO hank:** carry the three provenance fields into `photoData`.
**ROUTED TO cody:** an end-to-end arm that routes `rf_photos` through
`api/sd-data.js` and asserts `aiFooter()` on the **stored** record — the arm
that would have caught this. **And one stale comment:**
`api/sd-data.js:2076-2079` still says no client stamps a high-risk resource
today. As of this change that is false.

---

## 5. WHAT THIS DISCHARGE DOES NOT CLAIM

1. **No suite was run.** Four suites are named in the obligation with counts
   (28/28, 31/31, 18/18, 81/81); **I did not execute any of them.** Every
   statement about an arm is a statement about what the arm's source asserts.
2. **Surface 1's findings are read from source, not driven.** I did not POST
   `alf_clients` and then call `family_mar`; **F3 is a traced path, not an
   observed exploit.**
3. **F4 is traced, not observed.** I did not write an `rf_photos` row and read
   it back.
4. **`api/_resources/sairncare.js` was examined only for which actions it
   registers** — that is how the missing revoke was found — and not reviewed
   otherwise.
5. **The `office_manager` migration is disclosed in the schema as not run**;
   that is Michael's block-5 work and **Michael has confirmed all six blocks
   ran on Oct 14 19:38 ET**, so this is recorded as closed rather than raised.
6. **No `api/`, `sql/`, `tools/` or `tests/` file was touched**, and neither
   auditor clone was entered.
