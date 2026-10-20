# SAIRN handoff — hank b29 — 2026-10-20

**Subject:** two defects in `stonedesk.html` that had been routed from batch to batch and never
fixed — a sync button that said "All apps synced" after the server said 400, and an AI question
and answer posted to an endpoint that refuses it on every exchange. Both closed, driven on the
deployed page before and after. The two live-credential probes stay held, as instructed.
Written before the report, with nothing half-finished. Notes: `docs/2026-10-20-hank-b29-notes.md`.

## 1. PUSHED STATE
The fix landed at `origin/main` **`df8118c90`** (fix `e9083a146`, derived docs + register `df8118c90`),
`0 ahead, 0 behind`, **NOT FORCED, ZERO gate overrides.** This handoff, the report and the digest land
in a later commit — re-derive the tip before quoting it. Gates met: **register-feed** (one record, four
factors) and **derived-docs** (MASTER-PLAN and traceability regenerated after the final rebase).
Path-scope clean (`stonedesk.html` is assigned to hank in the manifest; the test is under `api/`).

## 2. CLAIMS HELD
Mine (`hank`, b29), released at the end. cc b28 still holds `tools/tooling_inventory.py` and `CLAUDE.md`;
I edited none of cc's files.

## 3. THE ITEMS
**Concept for the sairnSyncAll fix (item 3), stated before the code:** *a sync is reported as done only
when the server said ok; a non-ok answer is shown as a failure and the "Last sync" time is left alone.*

1. **`sairnSyncAll` — FIXED, live-verified before and after.** `fetch` resolves on a 4xx, so the
   try/catch never saw the 400.
   * **Before** (real page, real `fetch`, toast and element captured): bridge **400**, toasts
     `Syncing all connected apps...` → **`All apps synced`**, `Last sync: --` → `Last sync: 7:32:13 AM`.
   * **After** (same drive, after the deploy): bridge **400**, toasts `Syncing all connected apps...` →
     **`Sync failed (HTTP 400) -- nothing was synced`**, `Last sync: --` → **`Last sync: --`** (untouched).
   * Offline: `api/b29-stonedesk-sync-honesty.test.js`, 17 arms, lifts the shipped function; 400/401/500
     fail honestly, the 200 control still succeeds, a transport failure is unchanged, and **removing
     the ok check reproduces the bug**.
2. **`sendToNetwork` — REMOVED, and the endpoint should NOT accept it.** The bridge's
   `KNOWN_ACTIONS` is `push, proxy_get`; it has no `learn`. The Intelligence Network is `api/network.js`,
   which accepts only `[a-z0-9_]{1,64}` identifiers **by construction** so free text cannot be stored;
   `sendToNetwork` posted the raw question (100 chars) and answer (200 chars). The anonymised path
   (`sendNetworkInsight`, `:4842`, `:31293`) is live and unchanged. Deleted the function and its one call;
   the local-memory write is unchanged (test B3) and `learnFromResponse` now makes **no network call** (B4).
   Deployed page: `typeof sendToNetwork` is `undefined`, `learnFromResponse` is still a function.
3. **Concept statement:** above.
4. **Push:** §1.

## 4. OPEN, AND THE EXACT NEXT STEP
| # | open | why | next step |
|---|---|---|---|
| A | **straight-time-floor live proof** | credentials I may not create or type (held, as instructed) | Michael confirms `audit-owner` is bootstrapped, then `SEN_LICENSE=SEN-AUDIT-2026 SEN_OWNER_PIN=… SEN_CAREGIVER_PIN=… python docs/2026-10-20-hank-b27-sen-straight-time-floor-live-probe.py` |
| B | **trust-lock live proof** | same (held) | `LAW_LICENSE=LAW-AUDIT-2026 LAW_OWNER_PIN=… LAW_PARALEGAL_PIN=… python tools/law_trust_lock_live_probe.py` |
| C | the sync button can never succeed | the bridge has no `full-sync` action | decide what "sync" should be, or remove the button. Until then users see a true failure on every click |
| D | `sairnSyncAll`'s catch arm says "Bridge offline -- will retry"; nothing retries | untouched, outside the request | change the wording or add the retry |
| E | `NET_URL` (`stonedesk.html:2921`) is a dead constant | not asked | delete it |
| F | production AI limiter enforcing because the variable is unset | b27, measured | Michael sets `SAIRN_AI_RATE_LIMIT_MODE` in Vercel |
| G | everything else in the b27 handoff §4 | unchanged | `SAIRN-handoff-hank-b27.md` |

## 5. EVIDENCE
Live, before and after (§3.1); `typeof sendToNetwork` on the deployed page. Offline:
`b29-stonedesk-sync-honesty` 17/0, `b21-bridge-unknown-action` 20/0, stonedesk 128 blocks 0 errors.
**Not covered:** the two held live probes; no whole-tree run.

## 6. TRANSCRIPT
    C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-hank\8dd2a9db-f15f-4fee-9950-08bcb26892c0.jsonl
CONTEXT 49.8% of 1,000,000 -- 497,564 tokens, measured. Trigger was 85%, set as my red-flag threshold.

## 7. WHAT I GOT WRONG
Nothing I know of in this batch's code. The pattern worth naming: this bug was found by the hover
auditor in b22 and again by fourth, both times routed, and sat for seven batches because a routed finding
has no owner until somebody schedules it — which is the process factor recorded in the register.
