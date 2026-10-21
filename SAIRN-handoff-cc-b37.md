# SAIRN handoff: cc, batch b37, 2026-10-21

**Three items, all three closed.** cody's b36 review is discharged and on
origin. It is sound for `sd_customers`, but it does **not** yet meet Michael's
"no exception" decision across the platform; that is routed. Nothing is
half-finished, and **no override** was used.

## 1. Pushed state

| | |
|---|---|
| Claim | My first claim was BLOCKED because fourth's b48 holds `docs/tier-a-reviews.json`. I re-claimed for the read-only review and the deliverables, and said so in the claim string. The discharge changed ONE existing record (union-by-identity) and was declared to fourth on my status row. This is the same as b35 |
| Discharge | `d1d4786c`. On origin it reads `reviewed` / `cc` at 16:38:35Z |
| Push | **LANDED first time, no force.** After `git fetch` the count was 0 0 |
| Overrides | **NONE** |
| Context | **39.1% of 1,000,000**, measured |

## 2. CLOSED

- **Item 1, cody 2026-10-21T15:48:45Z (b36): SOUND FOR sd_customers.**
  - Ablation: 5 red (D1–D5, every verb).
  - **Reviewer question answered: no StoneDesk flow mints a token without a
    row.** Bootstrap inserts the row before signing (`sd-auth.js:215`). Setup
    signs from the row (`:278`). Webauthn signs only from an active row
    (`sd-webauthn.js:320-326`). The sub portal is app `stonedesk_sub`, so the
    branch refuses it. No api/ path deletes an `sd_employee_auth` row.
  - **But the decision says "no exception", and the fix covers one resource.**
    `credentialStillActive` has one call site, and a deleted row is refused
    only where the pre-gate knows the app: the 66 gated resources, plus
    `memory`, plus `sd_customers`.
  - **Driven:** with the row deleted, `sd_quote_requests`, `sd_crm`,
    `sen_clients`, `alf_clients` and `rf_jobs` all answer **200 and read
    data**. With `active:false`, all of them answer 403.
  - Roughly 70 branch-gated resources across 10 apps are in the same position
    (heuristic count).
  - **Fix suggestion:** `api/_resources` `RESOURCE_NAMES_BY_APP` already maps
    401 resources to exactly one app each. Use it as the pre-gate's expected
    app.
  - Differential test: 71/71, and it has teeth (drop one strip key → A2 red).
- **Item 2:** the CRITERIA line opens the verdict.
- **Item 3:** pushed and confirmed.

## 3. OPEN

- **(a) Routed to cody, scope to Michael:** refuse a deleted row on every
  registered resource, not only `sd_customers`. Michael should confirm that
  "no exception" means every app.
- **(b) NEW Tier A owed by cc, not in this dispatch:** hank
  2026-10-21T16:17:56Z (b40, `stonedesk.html` `sd_quote_requests`, the new
  `pcShowRequestPho…` client caller). It is the client half of the
  `request_photos` read I reviewed in b34.
- **(c) Still routed:**
  - hank: `scp-licence-only` B tests and A3.
  - cody: the revoke discard by `consent_id`, plus the three b34 items.
  - fourth: the b47 tests.

## 4. Exact next step

| item | next step |
|---|---|
| (b) | next cc batch: discharge hank 2026-10-21T16:17:56Z, and check that the photo read's tenant filter still has no test (b34 finding) |
| (a) | cody, after Michael confirms the scope |
