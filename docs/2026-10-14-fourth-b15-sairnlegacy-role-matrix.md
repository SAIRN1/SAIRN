# ROLE MATRIX SPEC — SAIRNlegacy, all 36 `leg_` resources — 2026-10-14, fourth b15

**ROUTED TO hank (`api/`, `sql/`).** Nothing outside `docs/` is written here.
**SPEC ONLY.**

**THE FINDING THIS EXISTS FOR, measured:** SAIRNlegacy has **three** roles and
**no per-resource role check anywhere**.

```
CMD grep -n "sairnlegacy:" api/_lib/auth.js
177:  sairnlegacy: ['owner', 'director', 'staff'],
CMD grep -nE "LEG_[A-Z_]*ROLES" api/sd-data.js
(no output)
CMD python scratchpad/bands_b15.py        -> sairnlegacy : 36 resources
```

So **`staff` is every employee who is not the owner or a director**, and a
`staff` token today reads and writes the same 36 resources an owner does —
including `leg_deathrecords`, `leg_cremations`, `leg_custodylog` and
`leg_preneed`. **Compare: `sairnlaw` has one gate (`api/sd-data.js:16882`,
owner-only trust reconciliation) and `sairnvet` has one
(`api/sv-auth.js:118`, `PRESCRIBER_ROLES` on the controlled register).
SAIRNlegacy has none.**

**THE PRECEDENT THIS FOLLOWS** is `sairncare`
(`api/_lib/auth.js:238` — `owner, nursing, med_aide, caregiver, billing,
activities`, mirrored in `sql/sairncare_employee_auth_schema.sql:29`) and
`sairnfreedom` (`sql/sairnfreedom_employee_auth_schema.sql:73-85` — eleven
scope-named roles, `post.govern` as owner and `post.govern.deputy` as upper
management). Both put **owner + an upper-management tier + task roles** in one
`CHECK` list and gate per resource **server-side**.

---

## 1. THE ROLE VOCABULARY

**`owner` and `director` are the app's own words and are NOT marked
[CONFIRM].** Everything below `director` is, because "staff" is where a funeral
home's real job titles have been collapsed.

| role | tier | what it is | confirmed? |
|---|---|---|---|
| `owner` | **owner** | The licence holder. The only provisioning role, as in every other app. | app's own |
| `director` | **upper management** | Licensed funeral director. Signs what the state requires a licensed director to sign. | app's own |
| `arranger` | task | Takes the arrangement conference, sells merchandise and services, builds the invoice. | **[CONFIRM]** — some homes call this *counselor*, *advisor* or *pre-need counselor*, and some do not separate it from `director` at all |
| `prep` | task | Embalming / preparation room. | **[CONFIRM]** — *embalmer* is the licensed title in most states and is often a **separate licence** from funeral director; if so this role may need its own licensed-tier flag the way `PRESCRIBER_ROLES` does in SAIRNvet |
| `office` | task | Billing, insurance assignment, records filing, portal messages. | **[CONFIRM]** — may be *administrator*, *bookkeeper* or a shared office manager |
| `apprentice` | task | Licensed-in-training. Works under a director, cannot sign. | **[CONFIRM]** — the regulated title varies by state (*apprentice*, *intern*, *resident trainee*) and the supervision rule is a **legal** constraint, not a UI one |
| `livery` | task | Drivers and pallbearer staff; needs the schedule and nothing else. | **[CONFIRM]** — often contractors rather than employees, in which case they may not belong in `leg_employee_auth` at all |

**MIGRATION, AND IT MUST NOT BREAK A LIVE PRACTICE:** every existing `staff` row
has to land somewhere. **`staff` stays in the `CHECK` list as a deprecated
value** that maps to the **narrowest** band (OPERATIONS read/write, no MONEY,
no REGULATED write) until a human re-assigns each person. **A migration that
silently promotes `staff` to `arranger` grants 15 money resources to everyone
who had a login yesterday.**

---

## 2. THE MATRIX, by band

Bands are assigned by name, reproducibly (`scratchpad/bands_b15.py`), and
every resource is listed in §3 so a wrong band is visible rather than averaged
away. `R` = read, `W` = read + write, `—` = refused (403).

| band | n | owner | director | arranger | prep | office | apprentice | livery | `staff` (deprecated) |
|---|---:|---|---|---|---|---|---|---|---|
| **REGULATED** — death records, cremation authority, custody, certificates, documents, dispatches, cases, aftercare | 9 | **W** | **W** | R | R [CONFIRM: `prep` writes `leg_custodylog`?] | R | R | — | R |
| **MONEY** — invoices, pre-need, insurance, merchandise, plots, monuments, vendor orders | 15 | **W** | **W** | **W** | — | **W** | — | — | — |
| **OPERATIONS** — bookings, facilities, vehicles, clergy, processions, obituaries, guestbook, tributes, memorials, maintenance | 12 | **W** | **W** | **W** | R | **W** | R | R (`leg_bookings`, `leg_processions`, `leg_vehicles` only) | **W** |

**FOUR RULES THAT ARE NOT IN THE TABLE AND MATTER MORE THAN IT:**

1. **`leg_custodylog` is append-only for everyone including the owner.** A
   chain-of-custody log that can be edited is not a chain of custody. (The
   platform already has append-only audit tables; this is that shape applied to
   a body-custody record.)
2. **`leg_cremations` write requires `director` or `owner`, never a task role**,
   and **[CONFIRM]** whether a second named person is legally required — a
   cremation authorisation is the sharpest irreversible act in this app, and
   SAIRNvet already has the witnessing pattern (`api/sv-witness.js`) to copy.
3. **`leg_preneed` is money AND a long-dated obligation.** Write is
   `owner`/`director`/`arranger`/`office`; **deletion is owner-only** and should
   be a state change rather than a delete.
4. **`leg_deathrecords` read is NOT broad.** It is the one REGULATED resource
   where even `R` for `livery` is wrong, and the table says `—`.

---

## 3. EVERY RESOURCE, WITH ITS BAND AND ITS REGISTER TIER

Tier is from `docs/CRITICALITY-TIERS.md` (`A` = money or regulated).

**REGULATED (9):** `leg_aftercare`(A), `leg_cases`(A), `leg_certs`(A),
`leg_cremations`(A), `leg_custodylog`(A), `leg_deathrecords`(A),
`leg_dispatches`(A), `leg_documents`(A), `leg_petcases`(B)

**MONEY (15):** `leg_catererorders`(A), `leg_caterers`(B),
`leg_floristorders`(A), `leg_florists`(A), `leg_gplservices`(A),
`leg_insurance`(A), `leg_invoices`(A), `leg_keepsakes`(A),
`leg_liverybookings`(B), `leg_liveryvendors`(B), `leg_merch_catalog`(A),
`leg_merch_units`(A), `leg_monuments`(B), `leg_plots`(A), `leg_preneed`(A)

**OPERATIONS (12):** `leg_bookings`(B), `leg_clergy`(B),
`leg_clergybookings`(B), `leg_facilities`(B), `leg_guestbook`(B),
`leg_keepsakeorders`(B), `leg_maintenance`(B), `leg_memorials`(B),
`leg_obituaries`(B), `leg_processions`(A), `leg_tributes`(B),
`leg_vehicles`(B)

**36 resources, 20 tier A.** `leg_liverybookings` and `leg_liveryvendors` are
banded MONEY by the vendor-order pattern; **[CONFIRM]** whether livery is
invoiced through the home or billed direct, because that decides whether
`livery` needs any MONEY read at all.

---

## 4. SERVER ENFORCEMENT — where it goes, and what already exists

* **The vocabulary** goes in `sql/sairnlegacy_employee_auth_schema.sql`'s `role`
  `CHECK` list **and** `ROLES_BY_APP.sairnlegacy` (`api/_lib/auth.js:177`). **Both
  or neither:** `api/role-vocabulary-agreement.test.js` is the suite that
  refuses a disagreement, and its arm at `:320-333` refuses an app with no
  table at all.
* **`verifySessionToken` already refuses a role outside the app's vocabulary** —
  stated in `api/sd-data.js:16876-16881`, which is why a phantom role key can
  never be reached by a request. **So the role names are safe to add first and
  gate second.**
* **The gate** goes in the `leg_`-resource branch of `api/sd-data.js`, beside
  the existing `LEG_RESOURCES` session gate at `:14809`. Export the role sets
  as named constants (`LEG_REGULATED_WRITE_ROLES`, …) from one place, the way
  `PRESCRIBER_ROLES` is exported from `api/sv-auth.js:564` so the witnessing
  lock imports it rather than re-listing names — **the drift that cost
  SAIRNsenior a real bug**.

---

## 5. NEGATIVE CONTROLS — the arms that must FAIL before they pass

Routed to **cody** as the suite owner; hank writes the code they drive.

| # | bad input | must happen |
|---:|---|---|
| L1 | a `staff` (deprecated) token writes `leg_invoices` | **403**, and the body names the role, not the resource alone |
| L2 | a `livery` token reads `leg_deathrecords` | **403** |
| L3 | an `apprentice` token writes `leg_cremations` | **403** — the regulated-signature case |
| L4 | an `office` token writes `leg_custodylog` | **403** |
| L5 | **any** role, including `owner`, EDITS an existing `leg_custodylog` row | **refused** — append-only, rule 1 |
| L6 | a `director` token writes `leg_cremations` | **200** — the control that proves the gate is not refusing everyone |
| L7 | an `arranger` token writes `leg_invoices` and reads `leg_documents` | **200 / 200** — the money-and-read control |
| L8 | a role string not in the `CHECK` list (`'embalmer'`) | **refused at the token**, by `verifySessionToken`, before any resource logic |
| L9 | a valid role from **another app** (`'nursing'`) | **refused** — cross-app vocabulary leak |
| L10 | **CONTROL:** every one of the 36 resources, `owner` token | **200** — an owner locked out of its own app is the failure mode that gets a gate deleted |

**L5, L6, L7 and L10 are the over-refusal guards.** A matrix that refuses an
owner, or refuses the arranger who sells the funeral, is a matrix somebody
switches off by Friday.

---

## 6. WHAT THIS SPEC DOES NOT DO

* **It does not decide the role NAMES below `director`.** Six are
  **[CONFIRM]** and a funeral home's own titles win over mine.
* **It does not claim a legal reading.** Whether an apprentice may sign, whether
  an embalmer needs a separate licence tier, and whether a cremation needs two
  named people are **state-law questions**, flagged where they bite.
* **It does not touch `api/`, `sql/` or `tests/`.**
* **It does not re-tier anything.** Tiers are quoted from
  `docs/CRITICALITY-TIERS.md` as they stand.
* **It has not been run against a live practice.** Nobody here has arranged a
  funeral; the bands are read off resource names and tiers, which is why every
  domain judgement is marked rather than asserted.
