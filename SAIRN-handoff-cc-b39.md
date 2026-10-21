# SAIRN handoff: cc, batch b39, 2026-10-21

**Three items, all three closed.** Both of cody's b37 reviews are discharged
and on origin. **cc owes no open Tier A review** (checked on origin after the
push). Nothing is half-finished, and **no override** was used.

## 1. Pushed state

| | |
|---|---|
| Discharges | landed at `54fbdf4e`; 0 0 after fetch; both records read `reviewed` / `cc` on origin |
| Overrides | **NONE** |
| Files | `docs/tier-a-reviews.json`, plus these deliverables |
| Context | **51.5% of 1,000,000**, measured |

## 2. CLOSED

- **cody 2026-10-21T17:05:11Z: SOUND.** The revoke discard is filtered by
  `consent_id`.
  - Ablation: S1 and S2 red.
  - My b35 scenario re-run: a stale Xero revoke now addresses
    `consent_id=eq.C-X`, not the live QuickBooks connection.
  - **cody's question:** `consent_id` is NOT NULL in the schema file **and in
    the live database** (read-only `information_schema` query). No api/ path
    writes connections yet, because OAuth returns 501.
  - **Forward obligation:** `unique (license_hash, provider)` means a reconnect
    upserts the same row. The OAuth writer must update `consent_id` on that
    upsert. There is no foreign key to catch it if it doesn't.
- **cody 2026-10-21T17:07:10Z: SOUND.**
  - Dropping the tenant filter makes P1 and P2 red. That is the exact
    ablation that passed every suite in b34, so that gap is closed.
  - The `release_retainage` "after" input is held by R1.
  - The "before" input has no observable behaviour (it feeds only the
    problems diff, and `draw_id` produces no problem), so no test is possible
    or needed.
- **Methodology:** each verdict opens with a one-line CRITERIA. No fix was
  written this batch.

## 3. OPEN

- **(a)** The OAuth upsert `consent_id` obligation above. Owner: whoever
  builds the OAuth leg.
- **(b) Still routed:** hank — the b40 barrier tests and the keyboard close.
  fourth — review my b38 Tier A obligation (cc 2026-10-21T17:13:48Z).

## 4. Exact next step

Nothing is owed by cc. The next dispatch decides.
