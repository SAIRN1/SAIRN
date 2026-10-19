# b20 concepts — one line each, written BEFORE the code

**Same method as `docs/2026-10-19-hank-b19-concepts.md`:** state the concept
first, then write the logic, then leave the statement unedited so a reader can
tell what the design was *intended* to be from what it became. The dispatch
asks for this on items 4 and 5 (the new schema and the new panel). The item-2
decision is recorded here too, because a routing withdrawal with no written
reason is the thing that gets re-granted by the next session.

---

## Item 2 — `paralegal` comes OFF `LAW_RECONCILE_ROLES`

> **DECISION (Michael, 2026-10-19).** The delegation grant is DEFERRED behind
> the attestation step, not refused: `LAW_RECONCILE_ROLES` becomes
> `{ owner, attorney }` and `LAW_RECONCILE_ATTESTATION` keeps naming the
> mechanism that would make the grant safe.

b19 raised this as its own DECISION-NEEDED rather than guessing. The reasoning
behind the answer is the **direction of the error**: with the grant and no
attestation record, the app lets a non-lawyer produce a finished reconciliation
that nothing records a lawyer as having reviewed — and Rule 1.15 puts that duty
on the lawyer, non-delegably. Without the grant, a firm that delegates the
arithmetic in practice is inconvenienced and asks for the feature. The first is
a compliance claim the record cannot support; the second is a missing feature.
**The narrow one ships.**

### THREE ARMS GO RED, NOT ONE, AND THAT IS THE MECHANISM WORKING

The dispatch predicted arm **R2**. Measured by running it:
`api/b19-iolta-reconcile-carveout.test.js` → **29 passed, 3 failed — R1c, R1f,
R2.**

| arm | what it asserted | why it is now red |
|---|---|---|
| R1c | paralegal reconciles the **ledger** leg → ALLOW | the grant is gone |
| R1f | paralegal reconciles the **bank** leg → ALLOW | the grant is gone |
| R2 | reconcile set === bar-admitted tier **+ exactly `{ paralegal }`** | the sets are now equal |

**All three are the same decision, asserted three ways, and NOT suppressed.**
R2 exists precisely so that writing the set out by hand instead of deriving it
cannot become a silent divergence. It did its job: a one-line policy change
could not be made quietly. The arms are re-aimed when the suite is next edited
by its owner, with the new expected answer written down — not deleted to go
green, which is item 8's shape one step later.

### AND THE CHANGE ALTERS NO SHIPPED BEHAVIOUR TODAY — MEASURED, THREE WAYS

This matters for the register record below and it is not a comfortable claim to
make by eye, so it was driven:

1. **The one shipped reconciliation feature never consults the module.**
   `api/sd-data.js:18765` is `resource === 'law_trust_reconcile' && action ===
   'read'` and carries its own hand-written `roleSet({ owner: true })`. That is
   the literal b19 **routed to cody** to replace with a read of
   `lawRoles.LAW_RECONCILE_ROLES`; §3 below reports it still unapplied. So the
   live gate is OWNER-ONLY under b19's grant and under b20's withdrawal alike.
2. **The `reconcile` VERB is not reachable at the envelope.** Driven, not read:
   `require('api/_resources/index.js').EXTRA_ACTIONS['law_trusttx']` is
   `undefined`, same for `law_bankstatements`. `api/sd-data.js:502` refuses any
   action that is not `read`/`write` and not in that list, **before** the role
   gate at `:16410` ever runs. A `reconcile` request on either leg is a 400.
3. **Even past the envelope there is no handler.** `LAW_RESOURCES` branches on
   `action === 'read'` and `action === 'write'` only; anything else falls to
   `api/sd-data.js:19515`, `400 Unsupported action/resource combination`.

**So the b19 grant was INERT and the b20 withdrawal is INERT, and b20 is what
makes cody's routed change safe to apply** — when the derive lands, the gate
becomes `{ owner, attorney }` and never passes through a state where a paralegal
could reconcile.

**The inertness of the whole `reconcile` verb is itself open work** and is
reported as UNVERIFIED rather than fixed here: declaring the verb in
`api/_resources/sairnlaw.js` would make the legs reachable on a new verb, which
is a widening decision in the opposite direction to the one Michael just made.
It is not hank's to take this batch.

---

## Item 4 — `sql/sairnlegacy_settings_schema.sql`

> **CONCEPT.** ONE row per home keyed by `license_hash`, holding b18's two
> policy answers as NAMED COLUMNS — the livery-billing arrangement as `text`
> with a database `CHECK` on the two-value enum, the apprentice config as
> `jsonb` because it is genuinely a list-of-names shape — so an invalid value
> is refused at the boundary instead of normalised away at read time, and **an
> absent row means the NARROW default** rather than an error.

Carried forward unchanged from b19's item-3 concept, which stated the same
thing before the file existed; b19 stopped before writing it.

**Why both halves, when `api/_lib/leg-roles.js` already fails narrow.**
`liveryBilling()` and `apprenticePolicy()` already return the narrow answer for
anything they cannot read, and that is the layer that must never be removed —
the row is untrusted input. The schema's job is the *other* direction: the
normaliser silently rewrites a bad value to the default, so a home that typed
`direct-to-family` with a hyphen would be running `through_the_home` and nothing
would say so. **The CHECK makes that a refused write instead of a silent
one** — the enum is closed, two values, and a third needs a migration that a
reader can see.

**And the apprentice config is `jsonb` ON PURPOSE, not for convenience.** Its
three fields are two resource-name LISTS and a boolean, and the lists are
filtered against `LEG_ROLE_MATRIX` at read time because a resource name is not
a database enum this app can keep in sync. A `CHECK` could assert the top-level
SHAPE and not the membership, so asserting the shape is exactly what it does —
no more, and the comment says the normaliser is still the authority.

---

## Item 5 — the `sairnlaw.html` countersignature panel

> **CONCEPT.** One read-only "Needs your authorisation" list in the Trust
> Accounting area, rendering **ONE NAMED STAGE per row** — the stage the
> endpoint computes — because four nullable columns is four chances for a panel
> to show "signed" for a spent-and-expired record.

**AND A CORRECTION TO THE SPEC, FOUND BY READING THE ENDPOINT RATHER THAN THE
ROUTING NOTE.** b19's routed spec and the b20 dispatch both say the list is
"driven by the `status` action" and that `idx_sairnlaw_countersign_open` "exists
to serve that query". Those two sentences cannot both be satisfied by what
ships:

* `api/_lib/countersign-endpoint.js:250` — **`status` takes `{ token }`** and
  returns ONE row. It is a per-record lookup keyed on
  `token_hash = hashToken(token)`.
* The clear token is returned **once**, at `prepare`, to the PREPARER. The
  signer does not hold it. So the signer cannot drive `status` for anything.
* `idx_sairnlaw_countersign_open` is `(license_hash, resource, expires_at)
  WHERE spent_at IS NULL` — a LIST index, and **no action queries it.** The
  index the dispatch names as serving the panel is served by nothing.

> **SO THE PANEL NEEDS A LIST ACTION AND b20 ADDS ONE:** `open`, in
> `api/_lib/countersign-endpoint.js`, returning the outstanding rows with the
> SAME computed stage `status` already returns — and **never a token or a
> token_hash**, because handing a signer a bearer credential out of a list is
> the "readable table of signatures waiting to be borrowed" both SQL schemas
> warn about in their own comments.

The panel is therefore **read-only by construction, not by politeness**. It
tells a signer what is waiting; signing still requires the token the preparer
hands them, which is the mechanism's design and not a gap. The panel says so on
screen rather than offering a button that cannot work.

Role gating on the panel is **UX-only** — `LAW_BAR_ADMITTED_ROLES`, the way
`sdRefreshLoginAccessGate()` does it in stonedesk. The server re-checks; the
panel only hides.

---

## What these concepts deliberately do NOT include

* **No attestation mechanism for the IOLTA reconciliation.** Still
  DECISION-NEEDED, now with Michael's answer recorded as "not until the
  mechanism exists" rather than left open in both directions.
* **No edit to `api/b19-iolta-reconcile-carveout.test.js`.** Three arms are red
  and the red is the deliverable's own evidence.
* **No `reconcile` entry in `api/_resources/sairnlaw.js`.** Widening the legs
  to a new verb runs opposite to the decision this batch implements.
* **No `sairnlegacy.html` panel.** fourth's file, still claimed (b33). The
  `open` action b20 adds serves it unchanged when fourth builds it.
* **No `leg_settings` resource registration.** `api/sd-data.js` is cody's;
  routed in b19 and still unapplied, see §3 of the handoff.
