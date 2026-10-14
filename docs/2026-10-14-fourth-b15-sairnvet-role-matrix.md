# ROLE MATRIX SPEC — SAIRNvet, 41 of 42 `sv_` resources ungated — 2026-10-14, fourth b15

**ROUTED TO hank (`api/`, `sql/`).** Nothing outside `docs/` is written here.
**SPEC ONLY.**

**MEASURED, AND THE ONE EXCEPTION IS THE INTERESTING PART:**

```
CMD python scratchpad/bands_b15.py            -> sairnvet : 42 resources
CMD grep -rn "PRESCRIBER_ROLES" api/ --include=*.js | grep -v test
    api/sv-auth.js:118  const PRESCRIBER_ROLES = roleSet({ owner: true, dvm: true });
    api/sv-auth.js:564  module.exports.PRESCRIBER_ROLES = PRESCRIBER_ROLES;
    api/sv-witness.js:54  (imports it rather than re-listing the names)
CMD grep -nE "SV_[A-Z_]*ROLES" api/sd-data.js
    (no output)
```

**ONE resource is role-gated — `sv_controlled`, the DEA-relevant register,
behind `PRESCRIBER_ROLES` (owner + dvm) and the witnessing lock. The other 41
are not.** So a `frontdesk` token today writes `sv_soapnotes`, `sv_labresults`,
`sv_surgery`, `sv_imaging` and `sv_invoicing` exactly as the owner does.

**THE VOCABULARY ALREADY EXISTS AND IS THE APP'S OWN**, read out of
`sairnvet.html`'s staff roster at `:1365` and `:6887` and documented at
`api/_lib/auth.js:259-290`. **So this spec adds almost no [CONFIRM] on names
— the open questions here are about READ scope, not vocabulary.**

**PRECEDENT:** `sairncare` (`api/_lib/auth.js:238`) and `sairnfreedom`
(`sql/sairnfreedom_employee_auth_schema.sql:73-85`) — owner + an upper-management
tier + task roles in one `CHECK` list, gated per resource server-side.

---

## 1. THE ROLE VOCABULARY — already decided, quoted not invented

| role | tier | what it is | confirmed? |
|---|---|---|---|
| `owner` | **owner** | Owner/DVM. Principal and the only provisioning role. | app's own |
| `dvm` | **licensed practitioner** | Associate DVM. | app's own |
| `manager` | **upper management** | Practice Manager. Runs the office; **explicitly NOT a clinician** (`api/_lib/auth.js:277`). | app's own |
| `tech` | task | Veterinary Technician (CVT/RVT/LVT by state). | app's own |
| `assistant` | task | Veterinary Assistant. | app's own |
| `frontdesk` | task | Front desk / reception. | app's own |

**`owner` + `dvm` are the licensed-practitioner tier and that is load-bearing,
not cosmetic** — a controlled-substance entry is a legal act by a licensed
veterinarian (`api/_lib/auth.js:285-288`). **`PRESCRIBER_ROLES` already encodes
exactly this pair; the matrix below reuses it rather than re-listing names.**

**`Other` was deliberately dropped from the roster list** and must stay dropped:
a role that means nothing cannot be gated on.

**TWO STRUCTURAL [CONFIRM]s, both about the real world rather than the code:**

* **[CONFIRM] does `manager` read clinical records?** `auth.js:277` says a
  practice manager is not a clinician. A manager who cannot open
  `sv_soapnotes` also cannot answer a client's billing question about a visit.
  Spec'd below as **read yes, write no** — the least-surprising answer, and the
  one most likely to be wrong.
* **[CONFIRM] is `tech` allowed to RECORD a controlled-substance administration
  the DVM ordered?** In many states a technician administers under direct
  supervision and the record is the technician's. Spec'd as **`sv_controlled`
  write stays `PRESCRIBER_ROLES` only**, with the witnessing lock as the place a
  technician's co-signature would go — **changing this is a legal reading, not a
  preference.**

---

## 2. THE MATRIX, by band

`R` = read, `W` = read + write, `—` = refused (403).

| band | n | owner | dvm | manager | tech | assistant | frontdesk |
|---|---:|---|---|---|---|---|---|
| **REGULATED — clinical** (SOAP notes, labs, imaging, surgery, dental, vitals, wellness, repro, lameness, farm calls, referrals, teleconsults, peer consults, pre-purchase, Coggins, equine dental, patients, clients, documents, compliance, consent, audit log) | 23 | **W** | **W** | R **[CONFIRM]** | **W** | R | R (`sv_clients`, `sv_patients` only; `—` for the rest) |
| **`sv_controlled`** — the DEA register, inside REGULATED above and called out because it is the one already gated | 1 | **W** | **W** | — | — **[CONFIRM]** | — | — |
| **MONEY** (`sv_billing`, `sv_financials`, `sv_invoicing`, `sv_petinsurance`) | 4 | **W** | R | **W** | — | — | R (`sv_invoicing` only) |
| **OPERATIONS** (scheduling, whiteboard, exam rooms, boarding, reminders, comms, portal, multisite, staff, mobile vet, herd health, wildlife rehab, conservation) | 13 | **W** | **W** | **W** | **W** | **W** | **W** |
| **REFERENCE** (`sv_reports`, `sv_speciesref`) | 2 | **W** | R | **W** | R | R | R |

**FOUR RULES THAT ARE NOT IN THE TABLE:**

1. **`sv_controlled` keeps its existing gate unchanged.** This spec adds 41
   gates; it does not touch the one that works. `PRESCRIBER_ROLES` is imported,
   never re-listed.
2. **`sv_audit_log` is append-only for every role, including `owner`.** It is
   the dosing trail (`api/_lib/auth.js:258`).
3. **`sv_scribe_consent` write is `owner`/`dvm` only.** A consent recorded by
   somebody who cannot take consent is worse than no record.
4. **`frontdesk` gets the narrowest REGULATED read on the platform** — client
   and patient identity so it can answer the phone, and nothing clinical.

---

## 3. EVERY RESOURCE, WITH ITS BAND AND REGISTER TIER

**REGULATED (23):** `sv_audit_log`(A), `sv_clients`(A), `sv_coggins`(A),
`sv_compliance`(A), `sv_controlled`(A), `sv_dental`(A), `sv_documents`(B),
`sv_equinedental`(A), `sv_farmcalls`(A), `sv_imaging`(A), `sv_labresults`(A),
`sv_lameness`(A), `sv_patients`(A), `sv_peerconsults`(A), `sv_prepurchase`(A),
`sv_referrals`(A), `sv_reproduction`(A), `sv_scribe_consent`(A),
`sv_soapnotes`(A), `sv_surgery`(A), `sv_teleconsults`(A), `sv_vitals`(A),
`sv_wellness`(A)

**MONEY (4):** `sv_billing`(A), `sv_financials`(A), `sv_invoicing`(A),
`sv_petinsurance`(A)

**OPERATIONS (13):** `sv_boarding`(A), `sv_comms`(B), `sv_conservation`(B),
`sv_examrooms`(B), `sv_herdhealth`(B), `sv_mobilevet`(B), `sv_multisite`(A),
`sv_portal`(A), `sv_reminders`(A), `sv_scheduling`(B), `sv_staff`(B),
`sv_whiteboard`(B), `sv_wildliferehab`(B)

**REFERENCE (2):** `sv_reports`(B), `sv_speciesref`(B)

**42 resources, 30 tier A.** `sv_boarding`, `sv_multisite`, `sv_portal` and
`sv_reminders` are tier A but banded OPERATIONS — **[CONFIRM]** each: a client
portal and an automated reminder both touch client-visible data, and if either
sends on the practice's behalf it may belong in a narrower band.

---

## 4. SERVER ENFORCEMENT

* **Vocabulary:** already in `ROLES_BY_APP.sairnvet` and
  `sql/sairnvet_employee_auth_schema.sql`'s `CHECK`. **Nothing to add** —
  `api/role-vocabulary-agreement.test.js` already compares them.
* **The gate** goes beside the existing `SV_RESOURCES` session gate
  (`api/sd-data.js:14007`) and the id-column map at `:14011`. Export the role
  sets from **`api/sv-auth.js`**, next to `PRESCRIBER_ROLES`, so there is one
  file naming SAIRNvet's roles.
* **`api/sv-witness.js` must not be touched by this work.** It imports
  `PRESCRIBER_ROLES`; adding 41 gates must not change the one that carries a
  legal act.

---

## 5. NEGATIVE CONTROLS

Routed to **cody**; hank writes the code they drive.

| # | bad input | must happen |
|---:|---|---|
| V1 | a `frontdesk` token writes `sv_soapnotes` | **403** |
| V2 | an `assistant` token writes `sv_labresults` | **403** |
| V3 | a `tech` token writes `sv_controlled` | **403** — and the message must name the licensed-practitioner requirement, not just "forbidden" |
| V4 | a `manager` token writes `sv_surgery` | **403** |
| V5 | a `dvm` token writes `sv_financials` | **403** — the clinician/money separation, which is the arm most likely to be argued with |
| V6 | **any** role edits an existing `sv_audit_log` row | **refused** — append-only |
| V7 | a `frontdesk` token reads `sv_clients` | **200** — the phone-answering control |
| V8 | a `tech` token writes `sv_vitals` and `sv_soapnotes` | **200 / 200** — the technician-does-clinical-work control |
| V9 | a `manager` token writes `sv_invoicing` | **200** — the money control |
| V10 | `sv_controlled` write by `owner` and by `dvm` | **200 / 200** — proves the 41 new gates did not break the one that existed |
| V11 | a role from another app (`'caregiver'`) | **refused at the token** |
| V12 | **CONTROL:** all 42 resources, `owner` token | **200** |

**V7–V10 and V12 are the over-refusal guards**, and **V10 is the regression
arm**: the whole risk of this change is breaking `sv_controlled`.

---

## 6. WHAT THIS SPEC DOES NOT DO

* **It does not change the role names.** They are the app's own and were read
  out of it, not designed here.
* **It does not decide the two structural [CONFIRM]s** — `manager`'s clinical
  read and `tech`'s controlled-substance record. The second is a state-law
  question.
* **It does not touch `sv_controlled`'s existing gate**, and the regression arm
  exists to prove that.
* **It does not claim the bands are clinically right.** Nobody here is a
  veterinarian; the bands come from resource names and register tiers, and the
  four tier-A OPERATIONS resources are flagged rather than assumed.
* **It does not touch `api/`, `sql/` or `tests/`.**
