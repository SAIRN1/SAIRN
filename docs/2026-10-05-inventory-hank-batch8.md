# Hank inventory — batch 8, 2026-10-05

Thirteen items. This file is written as each lands, not at the end, so a
session that dies halfway leaves a true partial record rather than nothing.

---

## 1. `family_mar` had no caller gate at all — H1 #877

**Premise at HEAD: HELD.** `api/sd-data.js`, resource `alf_family_contacts`.
`action === 'read'` at `:11506` resolves `ALF_FAMILY_READ_ROLES` and then the
caller's assigned residents from `alf_clients`, and 403s a resident that is not
theirs. `action === 'family_mar'` at `:11566`, sixty lines below it in the same
handler, did **neither**. It checked `famLib.familyMarView()` — the *contact's*
consent — and shipped the MAR.

**The consent check was standing in for an authorisation check.** That is the
defect in one sentence, and it is why it survived review: there *was* a check
on the path, it was just answering a different question. `familyMarView()`
answers "may this FAMILY CONTACT see anything", which is about the contact.
Nothing asked "may this EMPLOYEE read this resident's MAR", which is about the
session. Any authenticated session on the licence — a `med_aide` or an
`activities` employee with no resident assigned to them at all — could pass any
`contact_id` and receive that resident's full medication administration record.

**The fix, in two halves, because the resident is not knowable up front.**

1. `:11604` — role and assignment scope resolved **before** the contact is
   fetched. A narrow caller with an empty scope is `403 FORBIDDEN` and never
   reaches the query. Lookup-then-authorise was the tempting order and it is
   wrong: it answers "does this contact_id exist on this licence" to a caller
   who may not ask anything at all, which is the existence oracle `read`'s own
   comment already refuses.
2. `:11648` — the stored contact row's `resident_id` checked against that
   scope. `403 FORBIDDEN`, deliberately **distinct from `NO_SUCH_CONTACT`**, so
   the two answers are never collapsed into one oracle. The id comes off the
   stored row, never off the payload — a caller-supplied `resident_id` is a
   parameter somebody edits.

### FLAGGED, NOT FIXED: `ALF_FAMILY_READ_ROLES` includes `billing`

`:11501` — `roleSet({ owner: true, billing: true, nursing: true })`. A
**billing** role is in the broad set that now reaches a **medication
administration record**, with no assignment required. On a clinical record that
is arguable, and I did not narrow it.

**Deliberately not my call in this change.** The whole defect being fixed is a
gate that disagreed with its sibling. Fixing it by introducing a *second*
disagreement — `family_mar` admitting a narrower set than `read` on the same
resource — would leave the handler in the same class of inconsistency one layer
down, and would do it silently, under a commit whose subject is "add the
missing gate". It is a separate decision with a separate owner: whether a
billing role should see clinical detail at all, on this resource and on the
`read` path it already reaches today. Logged here so it is a decision somebody
makes rather than a default nobody noticed.

### Verification

`tests/sd_data_family_mar_gate.js`, new. Drives the **real handler** with auth,
licence and `fetch` mocked — not a reimplementation, which would have passed
against the unfixed code.

    node tests/sd_data_family_mar_gate.js      EXIT=0    10 passed, 0 failed

**Ablation, the number that makes the case.** The same test against
`git show HEAD:api/sd-data.js`, byte-unmodified:

    EXIT=1    4 passed, 6 failed
    FAIL A1  unassigned med_aide got the MAR
    FAIL A2  activities assigned to R2 got R1's MAR   <- the real attack
    FAIL A3  ...and not even as a FORBIDDEN
    FAIL C1/C2/C3  no gate in the source
    ok   B1/B2/B3  the authorised paths — unchanged

The three B arms staying green through the ablation is the half that matters
as much as the six failures: without them the "fix" could be *deny everything*
and every A arm would still pass.

### A false pass I found in my own test, and it was the worse half

C1 failed and C2 passed, and **C2 was the bug**. The source anchor was the bare
string `action === 'family_mar'`, which occurs **twice** — once in the action
allow-list at `:11448` (`action === 'read' || action === 'write' || action ===
'family_mar'`) and once on the branch itself at `:11566`. So `split(...)[1]`
returned the text *between* them, which is **`read`'s body**. C1 failed
honestly — no `marBroad` in `read`. C2 passed on **`read`'s own
`assigned_employee_id` query**: a green arm that never touched the code it
names, in a test written specifically to prove that code exists.

Fixed by anchoring on the branch statement `if (action === 'family_mar')` and
asserting the match count is **exactly 1** (new arm C0, which exits before
C1–C3 run if the anchor is ambiguous). This is the UNIQUENESS guard shape from
`sabotage_control_check` — `count(anchor) != 1` rather than `anchor in src` —
and it is here because the weaker shape had already cost one false pass in this
file's first run.

### Regression

Each exit code read on its own line, immediately after the process, never from
a pipeline's last element:

    tests/sairncare/test-alf-mar.js                 EXIT=0
    tests/sairncare_transport_refusal.js            EXIT=0
    tests/sd_data_unconfirmed_write_review_probe.js EXIT=0
    tests/role_maps_have_no_prototype.js            EXIT=0
    tests/exec_role_gate.js                         EXIT=0
    tools/role_gate_invariants.js                   EXIT=0
    tests/sd_data_dental_provider_scope_probe.py    EXIT=0
    tests/sd_data_food_temp_unevaluated_probe.py    EXIT=0
    tests/sd_data_mech_credentials_probe.py         EXIT=0
    tests/sd_data_numeric_guards_probe.py           EXIT=0
    tests/sd_data_sb_void_role_probe.py             EXIT=0
    tests/active_credential_gate_probe.py           EXIT=0
    tests/alf_append_only_probe.py                  EXIT=0

`node --check api/sd-data.js` EXIT=0 before and after.

### Observed, not caused by this change

Every arm of the new test prints:

    sd-data: active-credential re-check DID NOT RUN for app "sairncare"
    (NO_ACTIVE_CHECK) on alf_family_contacts/family_mar. The request was
    allowed on the token alone.

That is the handler's own disclosure firing because the test mocks auth, and it
fires identically on the unfixed code in the ablation. Not a regression and not
in scope here, but it is the right warning in the right place and worth not
mistaking for noise later.
