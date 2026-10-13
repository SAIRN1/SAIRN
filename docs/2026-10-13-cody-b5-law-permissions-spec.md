# Spec: owner-adjustable SAIRNlaw permissions, per firm — and the one thing an owner may never adjust

**Status: SPEC ONLY. Nothing in this document is built.** b5 item 4 was
explicit about that, and the reason is in §9: the hard part is not the storage,
it is deciding which of three things an override is allowed to mean.

**Author:** cody, batch 27 b5, 2026-10-13
**Depends on:** `api/_lib/law-roles.js` (landed b5 item 1) — the 19-row table
and the `decide(resource, role, action)` function this spec extends.
**Audience:** whoever builds it, and Michael for the decisions in §8.

---

## 1. The problem this solves, and the problem it does not

The b5 table is **one policy for every firm on the platform**. That is right as
a default and wrong as a permanent answer: a two-attorney practice where the
paralegal reconciles the operating account and a twelve-attorney firm with a
dedicated bookkeeper do not want the same `law_optx` rule, and today neither can
change it without a platform deploy.

**What this does NOT solve.** It does not make the DEFAULT better. If the
default is wrong for most firms, overrides will hide that rather than fix it —
every firm will carry the same correction and nobody will ever see it as one
finding. So the first question for any override request is *"is this an
override, or is the default wrong?"*, and the answer belongs in the defect
register either way.

---

## 2. Shape: a sparse DELTA, never a copy of the table

**An override row stores only what DIFFERS from the platform default.**

The alternative — storing a firm's complete 19-row matrix — is the shape to
refuse, and this platform has already paid for it twice (the App File Map, the
Guardian check count). A full copy is a **second source of truth that stops
agreeing with the first the moment the default changes**: add a 20th resource
and every firm that has ever touched permissions is silently missing a row for
it. Which is, exactly, the defect `law-roles.js` was written to end.

With a delta, a new resource arrives with its platform default for every firm
automatically, and an override has to be stated to exist.

```
law_firm_permissions
  license_hash   text    not null        -- the firm. scoped like every other table
  resource       text    not null        -- must be one of the 19. validated server-side
  role           text    not null        -- must be in ROLES_BY_APP.sairnlaw
  grant_value    text    not null        -- 'rw' | 'r' | ''  (same vocabulary as the table)
  set_by         text    not null        -- employee_id of the OWNER who set it
  set_at         timestamptz not null default now()
  reason         text                    -- free text, see §6
  primary key (license_hash, resource, role)
```

**`grant_value` reuses the table's own vocabulary deliberately.** A second
spelling (`true`/`false`, `allow`/`deny`) would need a translation layer, and a
translation layer is a place for the two to disagree.

---

## 3. Where it is read: ONE more lookup inside the ONE function

`decide()` stays the single entry point. Nothing in `api/sd-data.js` learns
about overrides — both call sites keep passing three arguments to the same
function, and a fourth (`licenseHash`) is added to it.

```
decide(resource, role, action, licenseHash)
  1. not one of the 19?                       -> NOT_LAW (or DENY for a new law_*)
  2. TRUST-LOCKED and role is not owner/attorney? -> DENY. STOP HERE.    <-- §4
  3. override row for (licenseHash, resource, role)?  -> use grant_value
  4. otherwise                                 -> use the platform default
  5. action is not 'read'? require 'rw'. else require 'rw' or 'r'.
```

**Step 2 sits BEFORE step 3 and that ordering is the whole security property.**
In the b5 code the lock is consulted *after* the table agrees, which is correct
when the table is the only input. Once an override can widen a grant, the lock
has to be the **first** thing asked, or an override row is a path around it.

**The override is a CACHED READ, not a per-request query.** A role check that
costs a database round trip per request is a role check somebody will be asked
to remove for latency. Per-licence, TTL in minutes, and — stated because it is
the real cost — **a revoked permission stays live until the cache expires.**
That is acceptable for widening and is NOT acceptable for the trust lock, which
is why the lock is not overridable and therefore never cached.

---

## 4. The trust lock: what an owner may never do

**`law_trusttx` and `law_bankstatements` are not overridable. By any role, in
any direction, for any firm.**

Not "overridable with a confirmation dialog". Not "overridable by the owner".
Not present in the override UI at all.

**Why it is a hard lock rather than a strong default:**

- IOLTA client trust money is the one figure a bar association audits. A
  misconfigured firm does not discover this in a code review; it discovers it in
  a trust-account audit, and the finding is against the attorney personally.
- The failure is **silent and permanent**. Nothing in the app can tell a
  deliberate widening from a misclick six months later, and the row that would
  prove which one it was is the row an override replaces.
- `api/sd-data.js:15719` already refused to widen `law_trust_reconcile` from
  owner to attorney on exactly this reasoning — *"widening it is a bar-rules
  judgement for the firm"* — and that is a NARROWER change than letting a firm
  owner grant a paralegal write access to the trust ledger through a settings
  screen.

**Enforcement, three layers, because one is a promise and three is a design:**

1. **The server refuses the WRITE.** A `law_firm_permissions` insert naming a
   trust-locked resource is rejected with a named code (`TRUST_LOCKED`), not
   silently dropped. A silent drop reads as success and the owner believes the
   permission is live.
2. **The server refuses the READ-SIDE EFFECT.** Step 2 of §3 runs before the
   override lookup, so even a row that somehow exists has no effect. Belt and
   braces, because layer 1 is one `if` and this one is the invariant.
3. **A constraint in the schema**, so a hand-run `insert` from the SQL editor
   cannot do it either:
   ```sql
   constraint lfp_trust_locked
     check (resource not in ('law_trusttx', 'law_bankstatements'))
   ```
   This is the layer that survives the application being wrong. The resource
   names are **literals here on purpose** — a check constraint cannot read a JS
   module, and the duplication is the price of the database enforcing it. It
   needs a drift tripwire: a test asserting the constraint's name list equals
   `LAW_TRUST_LOCKED` in `api/_lib/law-roles.js`, failing loudly when one moves.

---

## 5. Which resources an owner MAY override

| group | resources | overridable | direction allowed |
|---|---|---|---|
| **TRUST** | `law_trusttx`, `law_bankstatements` | **NO** | none |
| **CASE WORK** | `law_matters`, `law_picases`, `law_clients`, `law_matterdocs`, `law_portalesign`, `law_deadlines`, `law_mattermilestones`, `law_mattertasks`, `law_timeentries` | yes | **narrow only** |
| **FINANCIAL, non-trust** | `law_invoices`, `law_opaccounts`, `law_optx` | yes | both |
| **MEDICAL** | `law_pimedical` | yes | **narrow only** |
| **CORRESPONDENCE** | `law_portalmessages` | yes | both |
| **LICENSURE** | `law_barcerts`, `law_clecredits`, `law_clerequirements` | yes | both |

**"Narrow only" means an override may REMOVE a grant the default gives and may
not ADD one.** Case work and `law_pimedical` are where the default is already
permissive — paralegal read+write on nine resources, read on medical — so the
useful adjustment is a firm that wants LESS. Allowing widening there buys
little and opens the two Tier A/A rows (`law_picases`, `law_pimedical`) to a
settings screen.

The three both-direction groups are where the default is a guess rather than a
judgment, and the report for b5 item 1 says so in the table itself:
`law_portalmessages` is **denied by the stated default** because client
correspondence is not "documents" and not "contacts", and it is flagged there
as the single row most likely to be operationally wrong. A firm that needs a
paralegal reading client messages should not need a platform deploy.

**The monotonicity relation still holds and must still be tested.** An override
that grants a paralegal more than an attorney has must be refused at write
time, by the same relation
`api/sd-data-law-role-matrix.test.js` already drives over the defaults. An
override layer that can break the invariant the test asserts over the base
table is an override layer that makes the test a lie.

---

## 6. Who may set one, and what gets recorded

**Only `owner`.** Not attorney. Granting access is not practising law; it is
running the firm, and SAIRNlaw already treats owner as the provisioning role
(`PROVISIONING_ROLES = ['owner']` in `api/law-auth.js:130`).

**`set_by` is the acting employee_id, taken from the verified session and never
from the payload.** This is the same rule the b4 `sen_caregivers` write follows
— `caregiverData.updatedBy = session.employee_id` assigned AFTER the blob is
built, so a caller-supplied value cannot survive. A permission change whose
author is a request field is a permission change with no author.

**Every change writes an audit row** through `api/_lib/audit.js`, which this app
already uses: who, when, which resource, which role, from what to what. The
audit row is the artefact that answers "who gave the paralegal the operating
account" a year later, and it is the one thing here that cannot be
reconstructed afterwards.

**`reason` is free text and is NOT required.** A required reason field produces
"asdf" — and a mandatory field filled with noise is worse than an absent one,
because it looks like evidence. Prompt for it, store it when given, and let the
audit row carry the facts.

---

## 7. What the UI must not do

- **No "reset to defaults" that silently deletes override rows.** Deleting the
  delta is right; doing it without naming what is about to change is how a firm
  loses a deliberate narrowing it set eight months ago. Show the diff first.
- **No trust resources in the list at all.** Not greyed out with a tooltip —
  absent. A disabled control is a control somebody will try to enable.
- **No free-text resource entry.** The 19 come from the table; a typo must be
  impossible rather than validated.
- **Show the DEFAULT beside the override**, always. A screen that shows only
  the effective value cannot be read to find out what was changed, and that is
  the question an auditor asks.

---

## 8. Decisions this spec does NOT make

These are Michael's or the firm's, and the spec is deliberately incomplete
without them:

1. **Is `law_portalmessages` denied-by-default correct?** It is currently denied
   because it fell outside every named category, not because anyone judged it.
   If the answer is "paralegals obviously read client messages", that is a
   DEFAULT change in `law-roles.js`, not an override — and it should land as one
   so every firm gets it.
2. **May a firm widen `law_picases`?** It is Tier A/A on settlement figures and
   attorney work product, and the default already grants paralegal read+write.
   So the question is only about narrowing, which §5 allows — but if any firm
   wants it narrowed, that is a signal the DEFAULT is too permissive.
3. **Does `law_trust_reconcile` join the trust lock?** It is the 20th resource,
   owner-only today, and `api/sd-data.js:15719` records adding attorney as *"the
   open question, not a rejected one"*. Whatever that answer is, it should be
   the same answer as the trust lock's or the inconsistency needs stating.
4. **Per-branch or per-matter overrides.** Deliberately out of scope: this is
   per-firm per-resource per-role and nothing finer. A per-matter permission
   model is a different product, and the first firm to ask for it is the right
   time to design it.

---

## 9. Why this is a spec and not a build

The storage is twenty lines and the lookup is five. **The hard part is §4 and
§5** — deciding that an override may narrow but not widen in two groups, that
trust is unreachable in three independent layers, and that the ordering of the
lock before the lookup is a security property rather than an implementation
detail. Building it before those are agreed would produce a mechanism whose
rules nobody chose, which is how the thing it replaces came to exist: nineteen
resources with no role distinction and a comment explaining that the decision
had not been made.

**Nothing here is in the codebase.** `law-roles.js` has no `licenseHash`
parameter, there is no `law_firm_permissions` table, and `decide()` has four
steps rather than five.
