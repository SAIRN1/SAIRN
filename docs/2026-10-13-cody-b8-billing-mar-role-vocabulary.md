# ROUTED TO THE `api/` OWNER — billing and the MAR, a role-vocabulary decision

**cody, batch b8, 2026-10-13. Owner: `api/` (hank). Nothing in `api/` or `sql/`
is edited by this note.** What cody landed is this document and one
failing-first suite, `tests/mar_billing_grant.test.js`, registered in
`docs/known-red-suites.json` and read by no gate.

---

## 1. The decision, verbatim

> **Billing never reads the MAR by default. For coding work only, an office
> manager may grant billing access to a MAR, time-limited, expiring on its own,
> and audit-logged.** — Michael, 2026-10-13

This closes open item 4 of `SAIRN-handoff-cody-b7.md` §8, which routed
*"`billing` reading a MAR"* to Michael as a SAIRNcare role-vocabulary judgement
rather than a code fix. It is a vocabulary decision and it has code consequences;
this note separates the two so the owner can land the second without re-deciding
the first.

---

## 2. Where billing already cannot read the MAR — and this is green at HEAD

`alf_mar` is the resource that OWNS the medication-administration table, and it
already agrees with the decision:

| what | where |
|---|---|
| `ALF_MAR_ROLES = roleSet({ owner: true, nursing: true, med_aide: true })` | `api/sd-data.js:11148` |
| `read` gates on it | `api/sd-data.js:11191` |
| `write` gates on it | `api/sd-data.js:11234` |
| a billing caller cannot even see a medication NAME in the derived charge view | `api/sd-data.js:11710` — `derived.mar_description_withheld = !ALF_MAR_ROLES[session.role]` |

`billing` is absent from that set, so the direct door is shut. Arms A4 and A5 of
the suite are **regression pins on this**, and they pass at HEAD. They exist so
that landing the rest of the feature cannot quietly widen the one gate that was
already right.

---

## 3. Where billing CAN read the MAR right now — the sibling door, open at HEAD

`alf_family_contacts` action `family_mar` returns a named resident's full
medication-administration record, and it gates on a different set:

| what | where |
|---|---|
| `const ALF_FAMILY_READ_ROLES = roleSet({ owner: true, billing: true, nursing: true })` | `api/sd-data.js:12551` |
| `family_mar` inherits it — `const marBroad = !!ALF_FAMILY_READ_ROLES[session.role]` | `api/sd-data.js:12654` |
| and because `billing` is in the BROAD half, the assignment-scope query is skipped entirely — `if (!marBroad) { … }` | `api/sd-data.js:12656` |

**So the scope of the hole is every resident on the licence, not one.** A
billing clerk who is 403'd from `alf_mar` receives any resident's MAR by asking
for that resident's family contact, with no assignment restriction at all.

**THE AUTHOR OF THAT CODE DECLARED THIS AND DECLINED TO NARROW IT, AND THAT WAS
THE RIGHT CALL.** `api/sd-data.js:12649-12653` says so in the source: *"THE ROLE
SET IS INHERITED, NOT CHOSEN BY ME … a gate that disagrees with its sibling is
the defect being fixed. Flagged in the batch inventory instead."* The Tier A
record for that fix (`2026-10-06T06:14:34Z`, hank) names it as attack point (2)
and cody's b7 review passed the record while recording that the PASS does not
discharge this question. **The decision is what was missing, not the diagnosis.**

### It is the third door, which is why the answer is a vocabulary rule

| when | door | outcome |
|---|---|---|
| 2026-10-05 | `family_mar` had **no caller gate at all** | fixed by inheriting `read`'s role set — which is how `billing` got in |
| 2026-10-07 | `derive_charges` handed billing the medication NAME per dose for a named resident for a month, via `ALF_MANAGEMENT_ROLES = { owner, billing }` (`api/sd-data.js:7690`) | redacted at `api/sd-data.js:11710` |
| **now** | `family_mar` itself | **open at HEAD** |

Three one-off patches to three doors is the pattern a vocabulary rule replaces.

---

## 4. What the decision requires, as four properties

The suite is one section per property. **Nothing below exists at HEAD.**

**A. DENIED BY DEFAULT.** `family_mar` must refuse `billing` with 403
`FORBIDDEN` when no grant exists, and must refuse *before* the contact row is
fetched so the refusal is not an existence oracle. Either
`ALF_FAMILY_READ_ROLES` drops `billing`, or `family_mar` stops reading that
constant. **Arm A9 accepts either** — asserting one would dictate the
implementation.

**B. THE GRANT REQUIRES THE OFFICE MANAGER.** A named constant
(`ALF_MAR_GRANT_ROLES` is the suite's proposal) rather than an inline literal,
and a self-grant by the grantee must be refused.

**C. IT EXPIRES ON ITS OWN.** The comparison must happen **on the read path**,
against `expires_at`, every time. A grant that expires only when a sweeper
deletes the row is live for as long as the sweeper is down, and nothing would
say so. A grant must be bounded by a *named* ceiling constant
(`ALF_MAR_GRANT_MAX_HOURS`), because a magic number in a test is a number nobody
owns. A grant must not generalise to another employee or another resident.

**D. AUDIT-LOGGED, AND THAT MEANS THREE EVENTS, NOT ONE.** The grant, the
refused grant attempt, and **each granted read**. One row per grant tells you
access was possible; one row per read tells you what was actually looked at, and
only the second is an access log.

---

## 5. THE DECISION THE OWNER STILL HAS TO MAKE, AND IT IS NOT A CODE DETAIL

**There is no office manager in SAIRNcare.** Measured:

    api/_lib/auth.js:238
      sairncare: ['owner', 'nursing', 'med_aide', 'caregiver', 'billing', 'activities']

No `office_manager`. The same six values are the CHECK constraint on the
credential table — `sql/sairncare_employee_auth_schema.sql:29` and
`sql/sairncare_all_remaining_migrations.sql:50` — and provisioning is
`PROVISIONING_ROLES = ['owner']` at `api/alf-auth.js:52`.

**So the role the decision names cannot currently hold a session, and arm B2
fails on exactly that.** It is the one arm in the suite that is a question
rather than a defect. Two legitimate resolutions:

| option | what it costs |
|---|---|
| **Add `office_manager` to the vocabulary** | three places must change TOGETHER — `ROLES_BY_APP` (`api/_lib/auth.js:238`), the provisioning set (`api/alf-auth.js:52`), and the `role` CHECK in BOTH schema files. Miss the CHECK and credential creation fails at the database with the app believing the role exists. |
| **Declare `owner` to BE the office manager for this purpose** | no schema change, and it is honest about a small facility where one person is the owner. But it means the grant has no separation from the role that can already read the MAR directly, so "an office manager may grant" adds an audit trail and a time bound without adding a second pair of eyes. |

**Both are defensible. Picking one silently is not.** SAIRNcare's app-specific
role vocabulary is the thing `sairn-training-needs-assessment` warns must be an
explicit judgement each time rather than a copy from a sibling app — and
`api/alf-auth.js:57` already carries a *different* management set
(`MANAGEMENT_ROLES = { owner, billing }`) from the one `api/sd-data.js:7690`
declares under the same name, which is what silent copying produces.

---

## 6. ONE MECHANICAL TRAP, AND IT FAILS SILENTLY

**The three audit event types must be added to the table's CHECK constraint in
the same change as the code that emits them.** Today the constraint lists five
values and none of them is a MAR-access event:

    sql/sairncare_audit_log_schema.sql:31-37
      event_type text not null check (event_type in (
        'pin_bootstrap', 'pin_setup', 'credential_deactivated',
        'credential_reactivated', 'credential_change_refused'
      ))

An `event_type` outside that list makes `writeAuditLog`'s POST fail, and it
`return false`s with a server-log line only (`api/_lib/audit.js:133`). **The
grant would succeed and the audit row would silently not exist** — which is the
shape `tools/audit_event_type_check.py` exists to catch, and `api/_lib/audit.js`
surfaces `attributed` for the same reason. Arm D5 pins it.

---

## 7. What cody landed, and what it measures

`tests/mar_billing_grant.test.js` — **FAILING-FIRST, deliberately red, wired
into no gate.** MEASURED with `node tests/mar_billing_grant.test.js` at
`e9d6d40c`: **exit 1, 5 passed, 16 failed, 4 unproven.**

* **16 failed** — the feature does not exist.
* **4 unproven, counted and not merely printed.** A2, C1, C3 and D2 cannot be
  evaluated while the `mar_access_grant` action is absent, and the suite's
  `process.exit` reads the unproven counter, so it can never exit 0 with one
  outstanding. That rule is `docs/2026-10-13-cody-b6-methodology-unproven.md`
  §3, and `tools/unproven_arm_check.py` confirms this file is IN SCOPE and
  clean.
* **5 passed, and they are the pins and the controls** — A4/A5 (billing stays
  403 on `alf_mar` read and write), A6/A7 (nursing and the assigned narrow role
  still get 200, so *"deny everything"* cannot satisfy this suite), and C4.

**C4's pass is VACUOUS while A1 is red and the arm says so in its own text.** At
HEAD `billing` gets 200 on `family_mar` with or without a grant row, so C4 only
becomes load-bearing once A1 refuses. It is disclosed in the arm rather than in
this document alone, because a prose disclosure protects only the reader who was
going to read the log.

**TWO ARMS ALREADY PASSED FOR THE WRONG REASON AND WERE CAUGHT.** On the first
run C1 (*"a grant with no `expires_at` is 400"*) and C3 (*"a grant a year out is
400"*) both went green — against a handler with no grant action at all. The
dispatcher was answering `400 {"error":{"message":"action must be 'read' or
'write' or 'family_mar'"}}` to every malformed-grant arm, so the two arms meant
to prove the TIME BOUND was enforced were in fact proving the action is
unimplemented. There is now an `unknownAction()` guard
(`tests/mar_billing_grant.test.js:236-240`) and both are UNPROVEN instead. **A
400 from an action that does not exist is not a refusal about the payload** —
and seven passes looked like seven regression pins.

**It drives the real handler.** Same technique and the same fixture shape as
`tests/sd_data_family_mar_gate.js`, with auth, licence and `fetch` mocked,
including `mar_consent` rather than an invented field name. A reimplementation
would pass against the unfixed code.

**Every identifier the suite proposes is collected in one block
(`tests/mar_billing_grant.test.js:61-87`) so landing the feature under different
names is an edit to that block, not a rewrite of the suite.**

---

## 8. Exact next step for the `api/` owner

1. **Answer §5** — add `office_manager` across all four places, or declare
   `owner` to be it. Write the answer down; it is the premise of section B.
2. Land A–D in `api/sd-data.js` plus the grant table and the three audit
   `event_type` values in `sql/sairncare_audit_log_schema.sql` **in one change**
   (§6).
3. Re-run `node tests/mar_billing_grant.test.js`. **Exit 3 means arms are still
   unproven and is not a pass.**
4. On exit 0, **remove the `tests/mar_billing_grant.test.js` row from
   `docs/known-red-suites.json`.** A register entry whose suite has gone green
   swallows the next real failure of that file.

*Citations in this document were read out of the files at `e9d6d40c`. Re-derive
them rather than trusting the line numbers; `api/sd-data.js` moves.*
