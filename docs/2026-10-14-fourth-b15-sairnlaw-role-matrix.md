# ROLE MATRIX SPEC — SAIRNlaw, 19 of 20 `law_` resources ungated — 2026-10-14, fourth b15

**ROUTED TO hank (`api/`, `sql/`).** Nothing outside `docs/` is written here.
**SPEC ONLY.**

**MEASURED:**

```
CMD python scratchpad/bands_b15.py        -> sairnlaw : 20 resources (tier A 20, tier B 0)
CMD grep -n "sairnlaw:" api/_lib/auth.js
138:  sairnlaw: ['owner', 'attorney', 'paralegal'],
CMD grep -nE "LAW_[A-Z_]*ROLES" api/sd-data.js
16882:      const LAW_RECONCILE_ROLES = roleSet({ owner: true });
16883:      if (!LAW_RECONCILE_ROLES[recSess.role]) {
```

**ONE resource is role-gated — trust reconciliation, owner-only. The other 19
are not.** And **every one of the 20 is tier A**: this is the only app of the
three where the register has no tier-B resource at all, because a law firm's
data is money or regulated by definition.

So a `paralegal` token today writes `law_trusttx`, `law_opaccounts`,
`law_bankstatements`, `law_invoices` and `law_timeentries` exactly as the owner
does. **IOLTA is the sharpest thing on this platform: a trust-account
transaction written by the wrong person is a bar-discipline event, not a bug
report.**

**PRECEDENT:** `sairncare` (`api/_lib/auth.js:238`) and `sairnfreedom`
(`sql/sairnfreedom_employee_auth_schema.sql:73-85`) — owner + upper management +
task roles, one `CHECK` list, gated per resource server-side.

---

## 1. THE ROLE VOCABULARY

`owner`, `attorney` and `paralegal` are the app's own, from
`sairnlaw.html`'s role picker (`api/_lib/auth.js:133`). **The gap is not the
three names; it is the two jobs that are missing.**

| role | tier | what it is | confirmed? |
|---|---|---|---|
| `owner` | **owner** | Managing partner / firm owner. Only provisioning role. | app's own |
| `attorney` | **licensed practitioner** | Admitted lawyer. Signs, advises, appears. | app's own |
| `paralegal` | task | Drafts, files, manages matters and deadlines under supervision. | app's own |
| `bookkeeper` | task | **MISSING TODAY and the reason this spec exists.** Enters time, raises invoices, reconciles the operating account. | **[CONFIRM]** — many firms call this *office manager*, *business manager* or outsource it entirely; if outsourced, it may need a scoped external login rather than an employee row |
| `staff` | task | Reception, intake, scanning, portal messages. | **[CONFIRM]** — may be *legal secretary*, *assistant* or *receptionist*, and a legal secretary's real scope is wider than a receptionist's |

**WHY ADDING `bookkeeper` IS THE POINT.** With three roles, a firm either gives
its bookkeeper an `attorney` token — handing a non-lawyer every matter document
and every client file — or gives a `paralegal` token the trust ledger. **Both
are wrong, and today the app offers no third answer.**

**[CONFIRM] — the licensed-practitioner tier.** SAIRNvet encodes
`PRESCRIBER_ROLES` (owner + dvm) because a controlled-substance entry is a legal
act by a licensed person (`api/_lib/auth.js:285-288`). The equivalent here is
**`owner` + `attorney` = `BAR_ADMITTED_ROLES`**, and the acts that need it are
*giving advice*, *signing* and *authorising a trust disbursement*. **Whether a
paralegal may PREPARE a trust disbursement for an attorney to authorise is a
bar-rules question, not a preference.**

---

## 2. THE MATRIX, by band

`R` = read, `W` = read + write, `—` = refused (403).

| band | n | owner | attorney | paralegal | bookkeeper | staff |
|---|---:|---|---|---|---|---|
| **MONEY — trust** (`law_trusttx`, `law_trust_reconcile`, `law_bankstatements`) | 3 | **W** | R (`W` on `law_trusttx` **[CONFIRM]**) | — | R **[CONFIRM]** | — |
| **MONEY — operating / billing** (`law_invoices`, `law_opaccounts`, `law_optx`, `law_timeentries`) | 4 | **W** | **W** (`law_timeentries` own entries) | **W** (`law_timeentries` own entries) | **W** | — |
| **REGULATED — matters & client files** (`law_matters`, `law_matterdocs`, `law_mattertasks`, `law_mattermilestones`, `law_deadlines`, `law_clients`, `law_picases`, `law_pimedical`, `law_portalesign`, `law_portalmessages`) | 10 | **W** | **W** | **W** | — | R (`law_portalmessages`, `law_clients` only) |
| **REGULATED — professional standing** (`law_barcerts`, `law_clecredits`, `law_clerequirements`) | 3 | **W** | **W** (own records) | R | — | — |

**FIVE RULES THAT MATTER MORE THAN THE TABLE:**

1. **`law_trust_reconcile` keeps its existing owner-only gate.** This spec adds
   19 gates and does not touch the one that works (`api/sd-data.js:16882`).
2. **`law_trusttx` is append-only, for every role including `owner`.** A trust
   ledger whose rows can be edited cannot be reconciled. The three-way
   reconciliation named at `docs/CRITICALITY-TIERS.md` (`law_bankstatements`
   row) assumes exactly that.
3. **`law_timeentries` is scoped to the author.** An attorney and a paralegal
   write **their own** time; only `owner` and `bookkeeper` write anybody's. A
   role check alone does not express this — **it needs a row-level author
   check**, which is a different mechanism and is called out so it is not
   mistaken for a role.
4. **`law_pimedical` is medical records inside a law firm.** Read is
   `owner`/`attorney`/`paralegal`; **`staff` is `—`** even though `staff` reads
   `law_clients`.
5. **`law_deadlines` write must never be `—` for `paralegal`.** A missed
   statutory deadline is the classic malpractice event, and the person who
   maintains the calendar is usually the paralegal. **A matrix that locks the
   paralegal out of the deadline calendar is more dangerous than no matrix.**

---

## 3. EVERY RESOURCE, WITH ITS BAND AND REGISTER TIER

All 20 are tier A in `docs/CRITICALITY-TIERS.md`.

**MONEY (7):** `law_bankstatements`, `law_invoices`, `law_opaccounts`,
`law_optx`, `law_timeentries`, `law_trust_reconcile`, `law_trusttx`

**REGULATED (13):** `law_barcerts`, `law_clecredits`, `law_clerequirements`,
`law_clients`, `law_deadlines`, `law_matterdocs`, `law_mattermilestones`,
`law_matters`, `law_mattertasks`, `law_picases`, `law_pimedical`,
`law_portalesign`, `law_portalmessages`

**20 resources, 20 tier A, 0 tier B.** `law_barcerts` and `law_clerequirements`
carry a second-column tier of **B** in the register — a bar admission is a
public fact — which is why professional standing is its own band rather than
sitting with client files.

---

## 4. SERVER ENFORCEMENT

* **Vocabulary:** add `bookkeeper` and `staff` to **both**
  `sql/sairnlaw_employee_auth_schema.sql`'s `role` `CHECK` and
  `ROLES_BY_APP.sairnlaw` (`api/_lib/auth.js:138`). **Both or neither** —
  `api/role-vocabulary-agreement.test.js` refuses a disagreement, and
  `api/sd-data.js:16876-16881` records what happens when a role key names
  something the vocabulary does not have: it is a **configuration** defect,
  visible without a request.
* **The gate** goes beside `LAW_RESOURCES` (`api/sd-data.js:14706`), with the
  role sets exported as named constants from one place —
  `BAR_ADMITTED_ROLES` alongside the existing `LAW_RECONCILE_ROLES`.
* **The author scope for `law_timeentries`** is not a role set and must not be
  written as one.
* **MIGRATION:** no existing row changes role. Adding two values to a `CHECK`
  list is additive; **nobody is re-assigned by this change**, which is the
  difference between this app and SAIRNlegacy's deprecated `staff`.

---

## 5. NEGATIVE CONTROLS

Routed to **cody**; hank writes the code they drive.

| # | bad input | must happen |
|---:|---|---|
| W1 | a `paralegal` token writes `law_trusttx` | **403** |
| W2 | a `bookkeeper` token reads `law_matterdocs` | **403** |
| W3 | a `staff` token reads `law_pimedical` | **403** |
| W4 | an `attorney` token writes a time entry **authored by another attorney** | **403** — the author scope, not the role |
| W5 | **any** role edits an existing `law_trusttx` row | **refused** — append-only |
| W6 | a `paralegal` token writes `law_deadlines` | **200** — rule 5's control |
| W7 | a `bookkeeper` token writes `law_invoices` | **200** |
| W8 | an `attorney` token writes `law_matterdocs` and reads `law_trusttx` | **200 / 200** |
| W9 | `law_trust_reconcile` by `owner` | **200** — the regression arm for the gate that already exists |
| W10 | `law_trust_reconcile` by `attorney` | **403** — unchanged from today |
| W11 | a role from another app (`'dvm'`) | **refused at the token** |
| W12 | **CONTROL:** all 20 resources, `owner` token | **200** |

**W6–W9 and W12 are the over-refusal guards; W9 and W10 are the regression
arms** for the one gate this app already has.

---

## 6. WHAT THIS SPEC DOES NOT DO

* **It does not settle bar-rules questions.** Whether an attorney may write a
  trust transaction without the owner, whether a paralegal may prepare one, and
  whether a bookkeeper may see the trust ledger at all are **professional-
  conduct readings**, marked [CONFIRM] where they bite. Michael's cousin, a
  lawyer, is already reading the AI wording package
  (`docs/2026-10-14-ai-notice-wording-for-counsel.md`) — **these three
  questions are the natural second ask, and they are not in that package.**
* **It does not add the two new roles.** It specifies them.
* **It does not touch the existing owner-only reconciliation gate**, and W9/W10
  exist to prove that.
* **It does not touch `api/`, `sql/` or `tests/`.**
