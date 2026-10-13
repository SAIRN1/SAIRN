# sf_ "post staff" gate rule — adversarial test matrix and baseline (spec only)

Status: **NOT IMPLEMENTED.** This document specifies a rule and baselines
current (pre-fix) behavior. It does not change `api/sd-data.js`. Per the hover
auditor's scope, this role investigates and specifies; it does not write the
fix.

## 1. Source: what hank's handoff actually says

`docs/handoff-hank-2026-10-12.md`, section "Five Tier A SAIRNfreedom resources
are still ungated, by decision", names five resources that are Tier A by
`docs/CRITICALITY-TIERS.md`'s own letters and were deliberately NOT added to
the 2026-10-11 gating batch (which gated `sf_sessions`, `sf_shifts`,
`sf_tickets`, `sf_rentals`):

| Resource | Register line | id column (SF_RESOURCES) |
|---|---|---|
| `sf_district_imports` | 353 | `district_import_id` |
| `sf_events` | 358 | `event_id` |
| `sf_permit_flags` | 367 | `permit_flag_id` |
| `sf_products` | 368 | `product_id` |
| `sf_vehicles` | 380 | `vehicle_id` |

The handoff states the gap is a **named product decision**, not a bug nobody
noticed: "widening this gate is a product decision about who may see a duty
roster ... the batch that sent me here named these four and their client
write sites and not those five."

## 2. Confirmed by direct code read (not assumed)

`api/sd-data.js` dispatches **every** `sf_` resource, including all five
above, through two generic branches keyed only by membership in the
`SF_RESOURCES` id-column map (`api/sd-data.js:13738`), not through individual
`if (resource === 'sf_x' ...)` blocks:

```
if (SF_RESOURCES[resource] && action === 'read') { ... }   // api/sd-data.js:13767
if (SF_RESOURCES[resource] && action === 'write') { ... }   // api/sd-data.js:13775
```

Neither branch calls `verifySessionToken` or any session/credential check.
Each only scopes rows by `license_hash=eq.<licHash>`, where `licHash` is
derived solely from the bearer license key in the request (`api/sd-data.js:695`,
`lic.license_hash`) — **not** from any employee session.

Grepped individually across the whole file (`grep -n "\bsf_district_imports\b"`
etc.) — each of the five appears in exactly two places: the `SF_RESOURCES`
id-column map and the handoff's own explanatory comment block
(`api/sd-data.js:1115-1123`). **None of the five appears in `SD_SESSION_GATED`
(`api/sd-data.js:817`) or in `SD_GATE_APP` (`api/sd-data.js:1449`), and none
has an individual `resource === 'sf_x'` dispatch branch anywhere in the file.**
This rules out the possibility raised in the task — that one or two of the
five might carry partial/special-case protection not mentioned in the
handoff. There is none. All five are gated by NEITHER mechanism, on both
read and write.

Contrast with an already-gated sibling, `sf_officers` (`api/sd-data.js:1089`,
`':1531`): it is listed in `SD_SESSION_GATED['sf_officers'] = ['read',
'write']` and in `SD_GATE_APP['sf_officers'] = 'sairnfreedom'`. The actual
enforcement happens once, generically, at `api/sd-data.js:1739`:

```js
if (SD_SESSION_GATED[resource] && SD_SESSION_GATED[resource].indexOf(action) !== -1) {
  const gateApp = (resource === 'memory') ? memApp : (SD_GATE_APP[resource] || 'stonedesk');
  const gateSession = verifySessionToken(tokenFromRequest(req), licHash, gateApp);
  if (!gateSession) { res.status(403).json({ error: { code: 'FORBIDDEN', ... } }); return; }
}
```

This is the mechanism the five named resources do **not** go through at all.

## 3. SAIRNfreedom's tenancy model (confirmed by code read)

Tenancy is **license_hash-scoped per "post"**, the same pattern used by every
other `sf_`-gated resource and by SAIRNscape/SAIRNdesign/SAIRNlaw:

- `licHash` is resolved once per request from the bearer license key
  (`api/sd-data.js:695`, `lic.license_hash`), independent of any session.
- Every `SF_RESOURCES` read filters strictly by
  `license_hash=eq.<licHash>` (`api/sd-data.js:13768`); every write stores
  `license_hash: licHash` and upserts on `(license_hash, idCol)`
  (`api/sd-data.js:13782-13784`). **This row-level tenant filter already
  applies to all five named resources today** — a caller presenting Post A's
  license key cannot pull Post B's rows through these branches. The comment
  at `api/sd-data.js:827` states this directly: "THE TENANT BOUNDARY WAS
  NEVER THE PROBLEM."
- Employee session tokens (`api/_lib/auth.js:553` `signSessionToken`) carry
  `license_hash` **signed into the payload**, and `verifySessionToken`
  (`api/_lib/auth.js:584`) explicitly rejects a token whose signed
  `license_hash` does not match the request's `licHash`
  (`api/_lib/auth.js:606`: `if (!license_hash || payload.license_hash !==
  license_hash) return null;`), with the mechanism's own comment stating the
  property outright: "a token minted for one shop's license must never be
  accepted against a different shop's requests, even if somehow replayed."

**Conclusion:** once a resource is added to `SD_SESSION_GATED` (the same way
the other 22 gated `sf_` resources already are), `verifySessionToken` by
itself denies BOTH adversarial axes below, with no additional code beyond
what the sibling resources already use — this is an existing, already-proven
mechanism, not a new one that would need inventing.

## 4. The two adversarial axes

For each of the 5 resources x 2 actions (read, write):

- **Axis (a) — unauthenticated.** No `X-SD-Auth` session token at all
  (license key only, or no credentials at all). Under the new rule: **deny**
  (403 FORBIDDEN). Today: **no check exists**, so the request is authorized
  by the bare license key alone.
- **Axis (b) — cross-post.** A VALID, unexpired, correctly-signed session
  token for a *different* post (different `license_hash`) than the one the
  license key in the request resolves to — e.g., attacker holds Post B's
  real employee session plus Post A's bare license key (itself
  "shipped to the browser and readable by anyone who can open
  sairnfreedom.html" per the standing finding at `api/sd-data.js:822-824`
  applied to this same class of resource). Under the new rule: **deny**
  (403 — `verifySessionToken`'s `license_hash` check at `auth.js:606` fails
  because the token's signed `license_hash` is Post B's, not Post A's).
  Today: **the session token, present or absent, correct-tenant or not, is
  never inspected** for these five resources — the request succeeds or fails
  purely on the bare license key, so a cross-post session is neither checked
  nor needed. This axis is not merely "currently permitted", it is
  structurally unreachable as a distinct case today: there is no session
  check for either axis to differ against.

## 5. Baseline matrix — expected-after-fix vs. actual-today

All 20 cells confirmed by static code read (Section 2), not inferred from the
handoff prose alone.

| Resource | Action | Axis (a) unauth — after fix | Axis (a) today | Axis (b) cross-post — after fix | Axis (b) today |
|---|---|---|---|---|---|
| sf_district_imports | read | deny | **OPEN (leaks)** | deny | **OPEN (leaks)** |
| sf_district_imports | write | deny | **OPEN (leaks)** | deny | **OPEN (leaks)** |
| sf_events | read | deny | **OPEN (leaks)** | deny | **OPEN (leaks)** |
| sf_events | write | deny | **OPEN (leaks)** | deny | **OPEN (leaks)** |
| sf_permit_flags | read | deny | **OPEN (leaks)** | deny | **OPEN (leaks)** |
| sf_permit_flags | write | deny | **OPEN (leaks)** | deny | **OPEN (leaks)** |
| sf_products | read | deny | **OPEN (leaks)** | deny | **OPEN (leaks)** |
| sf_products | write | deny | **OPEN (leaks)** | deny | **OPEN (leaks)** |
| sf_vehicles | read | deny | **OPEN (leaks)** | deny | **OPEN (leaks)** |
| sf_vehicles | write | deny | **OPEN (leaks)** | deny | **OPEN (leaks)** |

No partial protection was found on any of the 10 action-cells for either axis.
All 10 are open today on both axes, by the same single root cause: absence
from `SD_SESSION_GATED`.

## 6. What the new rule would actually require (not implemented here)

Per the proven pattern already used by the other 22 `sf_` gated resources:

1. Add each of the 5 resource names to `SD_SESSION_GATED` with
   `['read', 'write']`.
2. Add each to `SD_GATE_APP` mapped to `'sairnfreedom'` — in the **same
   edit**, per the standing rule at `api/sd-data.js:1521-1528` /
   `:1090-1091` (two prior resources, `sf_trustee_audits` and
   `sf_vehicle_service`, were each gated without this second entry first and
   both incidents refused every correctly signed-in SAIRNfreedom officer with
   a confusing 403 until the omission was caught).
3. Confirm the SAIRNfreedom client (`sairnfreedom.html`) already attaches
   `X-SD-Auth` unconditionally for these resources (it does, per
   `sfData()` at `sairnfreedom.html:1986-1991`, which is unconditional across
   all resources) so gating does not newly break any signed-in caller.
4. Re-run `api/sd-data-sf-session-gate.test.js`, which asserts the gated set
   equals the approved set in both directions, so the approved set must be
   updated there too.

This is a product decision (per the handoff) about whether to widen the gate
to these five, not a bug fix — the hover auditor is not making that call, only
documenting what "deny both axes" would mean and what is true today absent it.
