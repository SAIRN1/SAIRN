# SAIRN handoff: cc, batch b38, 2026-10-21

**Five items, all five closed.** A deleted employee row is now refused on
every registered resource. hank's b40 review is discharged. Both are on origin.
Nothing is half-finished, and **no override** was used.

## 1. Pushed state

| | |
|---|---|
| Claim | `cc` b38; the files are declared, including the three api/ files |
| Fix commit (as landed) | `1b8ac96f` `fix(cc b38): a deleted employee row is refused on every registered resource...` |
| Push | **LANDED at `ad0cc51e`, no force.** It took several remote races. One rebase conflict each in `docs/sairn-path-manifest.json` (resolved by hand, both notes kept), the ledgers (union tool) and the derived docs (regenerated). The gate refused two bookkeeping commits with the same subject, so I reworded them. After `git fetch` the count was **0 0** |
| Register | one product record, re-seated through each rebase. It reads `1b8ac96fac7b`, matching the fix |
| Tier A | MY obligation, cc 2026-10-21T17:13:48Z, is **assigned to fourth**, and its sha is reachable on origin |
| Overrides | **NONE** |
| Context | **48.6% of 1,000,000**, measured |

## 2. CLOSED

- **Items 1, 2 and 4, the platform-wide deleted-row gate.**
  - Concept first: the registry already says which app owns each resource,
    so that app is the pre-gate's expected app.
  - `preExpectedApp = OWNER_BY_RESOURCE[resource]`. `shared` and `routes`
    resources follow the caller's `app_id`, as `memory` does. A wrong-app
    token still reaches its branch's FORBIDDEN.
  - **Measured, and much bigger than b37's "about 70":** before the fix,
    **323** registered resources answered 200 and touched data for a deleted
    employee's token.
  - New `api/b38-deleted-row-platform.test.js` derives its population from the
    registry: 392 resources across 16 apps. It is **1184/1184**; the old code
    fails 330.
  - Mutant: shared resources stop following `app_id` → S1 red.
  - The b36 differential is 71/71 and still has teeth (drop a strip key → A2
    red).
  - **Full api/ suite before and after:** one changed exit,
    `api/_lib/routes.test.js`. Its blanket `[]` mock now reads as a deleted
    employee, so one mock line answers an active row instead (63/63). On the
    rebased tree, 332 suites run and 4 fail, all of which were already
    failing.
  - Every app's bootstrap was read: each inserts the row before it mints a
    token, so no owner gets locked out.
- **Item 3, hank 2026-10-21T16:17:56Z (b40 photo overlay): SOUND AS SHIPPED.**
  - Public intake checks only the prefix, so a stored
    `…base64,AAAA" onerror=…` is possible. **The escaping is the real
    barrier**, and it holds (cc probe, 6/6).
  - SVG and `text/html` are not rendered.
  - **But hank's suite holds neither barrier.** Un-escaping `src`, widening
    the filter to `/^data:/` and un-escaping the slot each leave his suite
    11/11. Routed to hank, along with the missing keyboard close.
- **Item 5:** pushed and confirmed.

## 3. OPEN

- **(a) Live verification: UNVERIFIED for the specific behaviour.** Proving it
  on the deployment needs a valid token whose employee row has been deleted
  on a real licence, and I will not delete a row to get one. The deployment's
  state is in the report.
- **(b) Residual:** an UNREGISTERED resource is still unknown to the
  pre-gate. Nothing asserts that every resource `sd-data.js` serves is in the
  registry. This is recorded as `recurrence_open` on the register record.
- **(c) Tier A owed by cc, not in this dispatch:**
  - cody 2026-10-21T17:05:11Z (b37: the accounting.js revoke discard scoped
    by consent);
  - cody 2026-10-21T17:07:10Z (b37: the two-tenant `request_photos` arm,
    test-only).
- **(d) Routed to hank:** the b40 barrier tests and the keyboard close.

## 4. Exact next step

| item | next step |
|---|---|
| (c) | next cc batch: discharge cody 17:05:11Z, then cody 17:07:10Z |
| my obligation | fourth reviews cc 2026-10-21T17:13:48Z |
| (b) | a registry-completeness check for `sd-data.js` resources, if Michael wants it |
