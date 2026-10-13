# SAIRNfreedom (sf_) role-matrix adversarial checklist

Written by the hover auditor role (read-only). This is a checklist/spec only —
no role matrix is implemented here, no `.test.js` is added, nothing outside
this file was touched.

## Premise correction (read this before anything else below)

The task that commissioned this file said to model it "on SAIRNlaw's
role-matrix and monotonicity tests," implying those already exist as a landed
file. **They do not.** `api/sd-data-law-role-matrix.test.js` is not in the
repo. The only trace is claim commit `2c4d7ecc` ("cody claims cody — batch 27
(b5)"), whose own task text *describes* the planned shape — a 19×3
owner/attorney/paralegal matrix for sairnlaw resources, a test failing on any
law resource with no rule, and a monotonicity metamorphic relation,
control-pair tested — but that work was never landed. Only one unrelated file
from that same claim exists (`api/sd-data-sen-caregiver-pii-scope.test.js`).

So what follows is modeled on a **described spec, not a real template**. The
shape (role × resource matrix, current-vs-recommended columns, a monotonicity
section) is borrowed from that description. Nothing here was copied from a
real SAIRNlaw file.

## Role vocabulary correction

The task that commissioned this file suggested example role/population names
"officers, canteen, members." **Those are not SAIRNfreedom's real role
strings.** Verified against `api/_lib/auth.js` `ROLES_BY_APP.sairnfreedom`
(lines ~327–331):

```js
sairnfreedom: [
  'post.govern', 'post.govern.deputy', 'records.write', 'finance.write',
  'member.admit', 'services.refer', 'legal.review', 'history.write',
  'ceremonial.manage', 'chaplain.pastoral'
]
```

These are **capability IDs lifted verbatim from `sairnfreedom.html`'s own
`CAPABILITIES` array**, not invented by auth.js and not a generic
owner/admin/staff set. The app's own comment explains why: it serves five org
types (American Legion, VFW, Elks, Moose, Eagles) that use different officer
titles for the same function (a VFW finance officer is "Quartermaster," an
Elks one is "Treasurer," a Moose post is governed by a "Governor" not a
"Commander") — capability IDs are the stable enum; officer titles are
per-org-type display labels mapped onto it. "Officers, canteen, members" does
not appear in this list at all; it is not the real vocabulary.

Provisioning (who can create/deactivate credentials) is `post.govern` and
`post.govern.deputy` only (`api/sf-auth.js` `PROVISIONING_ROLES`, line 90).
`post.govern` alone carries `sole: true` in the app's own `CAPABILITIES` — one
per post — which is what the last-admin / sole-holder refusal keys on.

**This is not a linear hierarchy.** `post.govern` / `post.govern.deputy` are
the two governance roles with (intended) cross-domain reach. The other eight
— `records.write`, `finance.write`, `member.admit`, `services.refer`,
`legal.review`, `history.write`, `ceremonial.manage`, `chaplain.pastoral` —
are domain-scoped capabilities, parallel to each other, not nested inside one
another. A monotonicity relation across this role set has to respect that
shape; see the Monotonicity section below.

## Current gating mechanism (how access is actually decided today)

Read directly from `api/sd-data.js`, not probed live:

- **`SF_RESOURCES`** (~line 13738) is the resource dispatcher: 36 `sf_`
  resources, each mapped to an id column. A resource reaching this map with
  `action === 'read'` or `'write'` is served — this is the only place that
  decides whether a resource is wired at all.
- **`SD_SESSION_GATED`** (~line 817 onward) is a second, independent map:
  resource → list of actions (`'read'`, `'write'`) that require a verified,
  app-scoped session token. A resource/action pair **not** in this map is
  reachable with the bare licence key alone — which is shipped to the browser
  and readable by anyone who can open the app.
- **There is no role check anywhere in this path.** Confirmed by grep: no
  `caller.role`, no `ROLES_BY_APP[...]` lookup, no role/capability comparison
  exists between the `SD_SESSION_GATED` check and the Supabase read/write at
  ~line 13767–13790. The `sf_officers` comment (line ~1014) states this
  explicitly for that resource and it is true of the whole family: *"the
  generic `SF_RESOURCES` write branch stores `data: payload` verbatim with no
  role or capability check between the resource guard and the store."*
  Session gating in this file means **"any signed-in employee of this post,
  any role"** — not a specific role. A gated resource is not a role-checked
  resource.

So the only two real current states for every `sf_` resource are **ungated**
(licence key alone) and **session-only** (any valid session for this app, any
role). **Zero of the 36 are role-checked today.** That is the baseline this
matrix proposes against, not something the matrix found as a gap by surprise —
the file's own comments already name it repeatedly as an open product
decision nobody has made.

## Per-resource matrix: current state vs. proposed role access

**"Proposed" columns are this auditor's own reasoned recommendation only.**
No authoritative owner/attorney/paralegal-style mapping has been decided for
SAIRNfreedom. Treat every proposed cell as a draft for a product owner to
accept, reject, or override — not as a spec to implement as-is.

Legend for **Current**: `UNGATED` = licence key alone, no session required;
`SESSION` = valid session token required (this app, any role) — read from
`SD_SESSION_GATED`, both actions unless noted.

| Resource | Current | Proposed read roles | Proposed write roles | Why (sensitivity, read from the file's own comments where available) |
|---|---|---|---|---|
| `sf_accounts` | SESSION | `post.govern`, `post.govern.deputy`, `finance.write` | `finance.write`, `post.govern` | Chart of accounts, Tier A financial. |
| `sf_ledger` | SESSION | `post.govern`, `post.govern.deputy`, `finance.write` | `finance.write`, `post.govern` | General ledger, Tier A financial. |
| `sf_vendor_prices` | SESSION | `post.govern`, `finance.write` | `finance.write`, `post.govern` | Tier A, vendor pricing. |
| `sf_disbursements` | SESSION | `post.govern`, `finance.write` | `finance.write`, `post.govern` | ORC 2915 reportable charitable disbursement; payee + amount. |
| `sf_donations` | SESSION | `post.govern`, `finance.write`, `records.write` | `finance.write`, `post.govern` | Donor name + amount. |
| `sf_donor_awards` | SESSION | `post.govern`, `records.write` | `records.write`, `post.govern` | Carries `donorKey` — same disclosure shape as `sf_donations`. |
| `sf_donor_tiers` | SESSION | broader (not PII-equivalent per file's own comment) | `records.write`, `post.govern` | File explicitly distinguishes this from `sf_staff`/`sf_youth_participants` — lower sensitivity, still session-worthy. |
| `sf_gaming_expenses` | SESSION | `post.govern`, `finance.write` | `finance.write`, `post.govern` | ORC 2915 payee + amount, gaming-floor money. |
| `sf_members` | SESSION | `post.govern`, `member.admit` | `member.admit`, `post.govern` | Member identity. |
| `sf_operators` | SESSION | `post.govern`, `finance.write` | `finance.write`, `post.govern` | "The sharpest field in the whole audit" per file comment — licensed gaming operators. |
| `sf_service_appointments` | SESSION | `post.govern`, `services.refer` | `services.refer`, `post.govern` | VA-adjacent referral record. |
| `sf_signatures` | SESSION | `post.govern`, `legal.review` | `legal.review`, `post.govern` | Executed signatures. |
| `sf_staff` | SESSION | `post.govern`, `records.write` | `records.write`, `post.govern` | Carries DOB; app age-gates off it. |
| `sf_trustee_audits` | SESSION | `post.govern`, `finance.write` | `finance.write`, `post.govern` | ORC 2915 controls record, fidelity bond. |
| `sf_vehicle_service` | SESSION | `post.govern`, `records.write` | `records.write`, `post.govern` | Only writer of the odometer figure `sf_vehicles`' service-due flag derives from; write already refuses a reading below the one on record. |
| `sf_waivers` | SESSION | `post.govern`, `legal.review` | `legal.review`, `post.govern` | Health + military-status disclosure. |
| `sf_youth_participants` | SESSION | `post.govern`, `member.admit` | `member.admit`, `post.govern` | **Minors.** Most sensitive population in the set — consider also restricting read, not just write, to named roles once a matrix lands. |
| `sf_officers` | SESSION | `post.govern`, `post.govern.deputy` | `post.govern`, `post.govern.deputy` **only** | Governance roster; backs the client-side sole-provisioner trapdoor guard (`sairnfreedom.html` `sfToggleOfficer`/`sfAddOfficer`). Read is "published by design" per the file's own comment, but write should not be open to any other capability — a forged row cannot mint a session credential (server checks the signed token, not this table) but can corrupt the governance record and defeat the client trapdoor guard. |
| `sf_sessions` | SESSION | `post.govern`, `finance.write` | `finance.write`, `post.govern` | Bingo session record; `prizeCap` is a statutory limit (ORC 2915), not a house rule. |
| `sf_shifts` | SESSION | `post.govern`, `finance.write` | `finance.write`, `post.govern` | Attributes a cash variance to a **named employee** — also Tier A on confidentiality per the file's own comment. |
| `sf_tickets` | SESSION | `post.govern`, `finance.write` | `finance.write`, `post.govern` | Sale at snapshotted price against a named member. |
| `sf_rentals` | SESSION | `post.govern`, `finance.write` | `finance.write`, `legal.review` (compliance pair), `post.govern` | Hall rental charge + alcohol/notified compliance pair. |
| `sf_bottle_fills` | **UNGATED** | `post.govern`, `records.write` | `records.write`, `post.govern` | Tier A/B boundary per file's framing ("a duty roster or a bottle count") — currently open to the bare licence key. |
| `sf_ceremonial_items` | **UNGATED** | broad (low sensitivity) | `ceremonial.manage`, `post.govern` | Ceremonial inventory. |
| `sf_district_imports` | **UNGATED** | `post.govern`, `post.govern.deputy` | `post.govern`, `post.govern.deputy` | Named Tier A and explicitly left ungated as "a decision I did not make rather than an oversight" (file comment, 2026-10-11) — district-level import, admin-scoped. |
| `sf_documents` | **UNGATED** | broad | `records.write`, `post.govern` | General document store. |
| `sf_events` | **UNGATED** | broad | `records.write` or `ceremonial.manage`, `post.govern` | Named Tier A, explicitly left ungated (same 2026-10-11 comment). |
| `sf_honor_details` | **UNGATED** | broad | `ceremonial.manage`, `post.govern` | Awards/honors detail. |
| `sf_inventory_counts` | **UNGATED** | broad | `records.write`, `post.govern` | General inventory. |
| `sf_national_categories` | **UNGATED** | broad (reference data) | `post.govern`, `post.govern.deputy` | Looks like lookup/reference data — lowest-risk candidate for staying open, but verify before assuming. |
| `sf_permit_flags` | **UNGATED** | `post.govern`, `legal.review` | `legal.review`, `post.govern` | Named Tier A, explicitly left ungated (same 2026-10-11 comment) — compliance/permit status. |
| `sf_products` | **UNGATED** | broad | `records.write`, `post.govern` | Named Tier A, explicitly left ungated (same 2026-10-11 comment) — canteen/gaming product catalog. |
| `sf_service_hours` | **UNGATED** | broad | `services.refer` or `history.write`, `post.govern` | Service-hours log. |
| `sf_service_referrals` | **UNGATED** | `post.govern`, `services.refer` | `services.refer`, `post.govern` | Referral record — same family as `sf_service_appointments`, which IS gated; worth asking why this sibling isn't. |
| `sf_vehicles` | **UNGATED** | broad | `records.write`, `post.govern` | Named Tier A, explicitly left ungated (same 2026-10-11 comment) — vehicle roster `sf_vehicle_service` (gated) derives its service-due flag against. |
| `sf_vendors` | **UNGATED** | broad | `finance.write`, `post.govern` | Vendor roster — sibling of `sf_vendor_prices`, which IS gated. |

**Totals, counted from the above, not estimated:** 36 `sf_` resources
dispatched in `SF_RESOURCES`. 22 are session-gated (both read and write,
per `SD_SESSION_GATED`); 14 are ungated (licence key alone). **Zero are
role-checked** — "session+specific-role" does not currently exist as a gating
shape for any `sf_` resource; the task's third category is aspirational, not
observed.

Gated set (22): `sf_accounts`, `sf_disbursements`, `sf_donor_awards`,
`sf_donor_tiers`, `sf_members`, `sf_donations`, `sf_gaming_expenses`,
`sf_ledger`, `sf_operators`, `sf_service_appointments`, `sf_signatures`,
`sf_staff`, `sf_trustee_audits`, `sf_vehicle_service`, `sf_vendor_prices`,
`sf_waivers`, `sf_youth_participants`, `sf_officers`, `sf_sessions`,
`sf_shifts`, `sf_tickets`, `sf_rentals`.

Ungated set (14): `sf_bottle_fills`, `sf_ceremonial_items`,
`sf_district_imports`, `sf_documents`, `sf_events`, `sf_honor_details`,
`sf_inventory_counts`, `sf_national_categories`, `sf_permit_flags`,
`sf_products`, `sf_service_hours`, `sf_service_referrals`, `sf_vehicles`,
`sf_vendors`.

Five of the ungated 14 are called out **by the file's own comments** as Tier A
and left open as "a decision I did not make rather than an oversight":
`sf_district_imports`, `sf_events`, `sf_permit_flags`, `sf_products`,
`sf_vehicles`. A role matrix that lands should resolve these five first —
they already have an owner's attention on record, just not a decision.

## Monotonicity check (for a future matrix — not implemented, checklist only)

The SAIRNlaw spec description calls for "a monotonicity metamorphic relation,
control-pair tested": conceptually, a more-privileged role must never be
denied something a less-privileged role is allowed. For SAIRNfreedom this
needs restating against the real shape of the role set, because it is **not**
a single total order the way owner > attorney > paralegal reads.

- [ ] **Confirm the intended partial order before writing any test.**
      Proposed shape: `post.govern` and `post.govern.deputy` dominate every
      domain role (`records.write`, `finance.write`, `member.admit`,
      `services.refer`, `legal.review`, `history.write`, `ceremonial.manage`,
      `chaplain.pastoral`) — i.e. governance can see/do anything a domain
      capability can. The eight domain roles are **not** ordered against each
      other (parallel, not nested) — a monotonicity test between e.g.
      `finance.write` and `records.write` has no defined direction and should
      not be asserted either way.
- [ ] **Decide whether `post.govern` and `post.govern.deputy` are equal for
      this purpose, or whether deputy is strictly weaker.** `sole:true` only
      marks `post.govern` as the one-per-post irreplaceable holder for
      *provisioning*; it does not by itself say deputy should be weaker on
      *resource* access. Pick one before the test is written, and record which
      was picked and why.
- [ ] **For every resource R and every domain role D with a proposed access
      level on R:** assert `post.govern`'s access to R is **>=** `D`'s access
      to R (read implies read, write implies write). Control pair per
      resource: (`post.govern`, `D`) must never show `post.govern` denied
      something `D` is allowed.
- [ ] **Negative control, so the test isn't vacuously true:** include at
      least one deliberately-engineered bad row (a resource where governance
      is wrongly scoped below a domain role) in the test's own fixture set,
      and confirm the relation actually fails on it — same discipline as
      locking a check's criteria against a synthetic fixture before trusting
      it on real data.
- [ ] **Flag the one plausible exception before assuming universal override:**
      `chaplain.pastoral` suggests clergy/pastoral-care content may carry a
      confidentiality norm that governance roles should *not* automatically
      override, the way clergy-penitent material generally isn't subject to
      ordinary chain-of-command access even when the chain outranks everyone
      involved. No such resource exists in the current 36 — but if one is
      added (pastoral notes, counseling records), the monotonicity relation
      proposed above should be revisited for that resource specifically
      rather than assumed to extend automatically. Name this as an open
      question for whoever owns the product decision, not a default.
- [ ] **Re-run `SD_SESSION_GATED` vs `SF_RESOURCES` agreement** (the existing
      two-lists-agree discipline already enforced by
      `api/sd-data-sf-session-gate.test.js`) as a precondition — a monotonicity
      test is meaningless on a resource that isn't even correctly gated yet.
