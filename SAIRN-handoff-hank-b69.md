# SAIRN handoff — hank b69 — 2026-10-29

**Subject:**
- The Stop hook for the done line.
- M5, the IOLTA reconciler's aged deposits in transit.
- J5, Vermont, from the official Judiciary page.
- H1x, the inline-handler id pass.
- Tier A SHAs cited inline.

This handoff was written before the report. HEAD was fast-forwarded to origin/main `14271a528` before any work.

**SHAs below are the local ones at the time of writing.** A rebase during the push rewrites them. The report and digest give the landed SHAs.

## 1. Stop hook — already built, armed in this clone, verified (no second copy built)
- **Where it is armed:** `.claude/settings.local.json` → `Stop` runs `.git/sairn-hooks/sairn_done_line.py --stop-hook` (cc b66).
- **The armed copy is byte-identical to `tools/sairn_done_line.py`.** This was checked with `cmp` after `tr -d '\r'`.
- **Selftest: 16 arms, 0 failed.** The arms cover:
  - the exact line, which is allowed;
  - the line plus a sentence, a sentence before it, or a trailing period, all refused;
  - an unreadable transcript while a line is recorded, refused rather than silently allowed;
  - three refusals, after which the stop is let through so it cannot loop.
- **Live evidence:** b68's record in `.git/sairn-done-line` shows `refusals: 0`, so it accepted b68's exact final line.
- **Stated limit:** the hook checks only once a done line has been recorded. A turn with no recorded line, such as a blocking question, is allowed through on purpose.

## 2. M5 — FIXED: a deposit in transit older than 30 days stops the reconciliation at PARTIAL
- **Commits:** `api/_lib/law-trust-reconcile.js` in `b3e717894`, register record in `f785ebb59`.
- **What changed:**
  - An uncleared deposit dated more than `STALE_DEPOSIT_IN_TRANSIT_DAYS` = **30** days before the statement no longer counts as in transit. It now:
    - stops the status at **PARTIAL**;
    - appears in `bank_vs_ledger.stale_deposits_in_transit`, with id, date, cents and days;
    - is named in the leg's `why`, which the Trust Accounting panel already renders.
  - The arithmetic of the bank leg is unchanged.
- **The 30-day threshold is my choice:** one monthly statement cycle, stated in the code. It is not a bar rule. **Michael may want a different number.**
- **Evidence:**
  - `law-trust-reconcile.test.js` passes 37/37, 4 of them new arms. With the status line removed, 2 of the new arms go red.
  - The stress probe now gives M5 **PASS**: 8 PASS and 1 FAIL. The remaining FAIL is M6, which is a limit of reconciliation.
- **Not changed:** stale *uncleared cheques* are not flagged. That is a different question (stale-dated cheques, escheat).
- **Pre-existing at HEAD, not mine:** `law-trust-reconcile-endpoint.test.js` has 2 FAILs. Both expect paralegal and attorney reads to get 403, and both get 200. It was the same before this change.
- **Tier A:** `tier_a_review_gate` says nothing needs recording for this range. I did not open an obligation. **Recommended:** a voluntary review, because the change is on the trust-money path.

## 3. J5 Vermont — NOT SEEDED: neither condition can be confirmed from the official page
- **Commit:** `1008b1e4a`. The detail is in `docs/sairnlaw-vermont-deadline-seed-blockers.md` §b69.
- **Current-through date: not available officially.**
  - vermontjudiciary.org/attorneys/rules has no compiled V.R.C.P. and no current-through date. It says "All Vermont court rules are available through LexisNexis", and it disclaims responsibility for Lexis's accuracy.
  - The promulgated list is "Promulgated Rules Over the Last Two Years". The orders on it are effective from 2022-10-01 to 2025-10-01.
- **E-service +3 under 6(e): unconfirmed after 2018.**
  - I fetched and read all 14 VRCP and VREF orders on the official list.
  - None touches 6(e), and none touches 5(b).
  - So 6(e) has not changed between about 2022-10 and 2026-10. The 2018-01-01 to 2022 window cannot be confirmed from any official page.
- **Unblock:** either of these, from a human:
  - a Lexis printout of V.R.C.P. 6/12/33/34/36/59 that shows its current-through line;
  - the Judiciary's answer: were those rules amended after 2018-01-01, and does 6(e) still add 3 days for e-service?

## 4. H1x — FIXED: every stored id passed from an inline handler goes through `JA()`
- **Commits:** `sairnlegacy.html` in `e4027b3e5`, register record in `36b302390`.
- **`JA(v)` is `H(JSON.stringify(String(v)))`.** It is a JS string literal, then HTML-escaped. That order matters because the browser HTML-decodes the attribute before the JS runs.
- **Count:** H1 counted 38 by grep. I measured 39 interpolations inside handler attributes:
  - **34 were record values, and all 34 are now `JA()`.** That is 33 `x.id` / `x.case_id` values plus `idArg`.
  - **The other 5 were left alone:** an array index ×3, a fixed status map and a literal ternary.
- **`idArg` was also unsafe:** it was built as `&#39;+H(id)+&#39;`. H() alone does not protect this context.
- **Evidence:** `tests/sairnlegacy_inline_handler_args.js` passes 15/15.
  - It drives the real `H` and `JA` from the file through attribute-decode and then JS-parse, using 5 hostile ids.
  - **Arm X: both old forms run injected code.**
  - The structural arms fail if a raw site comes back.
- **Pre-existing at HEAD, not mine:** `tests/sairnlegacy_reservation_lock.js` fails 1 arm ("refuse a write with no payload.id", 35/36). That was baselined in a clean worktree at HEAD, without my change.

## 5. Tier A obligations — SHA cited inline (methodology item 5)
- **No obligation is open or assigned to hank this batch** (`--list`). I discharged none in b69.
- The six from b68 are restated below. Each cites the reviewed sha, which is the obligation's `opened_at_sha`, and the commit I read where it differs.

| opened | author | resource | reviewed sha | verdict |
|---|---|---|---|---|
| 2026-10-22T16:02:10Z | cody b51 | leg_cremations | `42186dd4c` | SOUND |
| 2026-10-22T21:18:41Z | fourth b57 | slabs | `75eb3be83` (landed as `09e810819`; recorded `a7a8bb27a` does not resolve) | SOUND |
| 2026-10-23T16:49:24Z | cc b55 | law_trust_reconcile | `1eab88206` | SOUND-WITH-GAPS (M5 now fixed in `b3e717894`) |
| 2026-10-27T14:26:58Z | cc b56 | sd_approvals | `c6cea2250` | SOUND |
| 2026-10-27T14:59:52Z | cc b58 | leg_cremations, leg_invoices | `44e517968` | SOUND |
| 2026-10-29T11:22:16Z | cc b69 | dnt_* / exec_context / sd_crm | `c3fd884c4` | SOUND |

## 6. Cause tags
Two rows were added to `docs/recurring-bug-classes.md` under "batch 69 (hank)": the M5 domain-model gap, and the H1x output-encoding gap (the wrong layer).

## 7. CLAIMS HELD
`sairnlaw` and `sairnlegacy`. Both are released after the push lands.

## 8. OPEN — exact next steps
| # | item | owner | next step |
|---|---|---|---|
| J5 | Vermont | Michael | a Lexis printout of V.R.C.P. 6/12/33/34/36/59 with its current-through line, or the Judiciary's answer on post-2018 amendments and e-service +3. Then hank runs the ND pattern. |
| M5t | the 30-day stale threshold | Michael | keep 30, or name a number. It is one constant in `api/_lib/law-trust-reconcile.js`. |
| M5r | voluntary Tier A review of `b3e717894` (trust-money path) | any reviewer | `tier_a_review_gate.py --open` if wanted |
| RL1 | `sairnlegacy_reservation_lock.js` 35/36, pre-existing | sairnlegacy api owner | read why one LEG resource accepts a write with no payload.id |
| LE1 | `law-trust-reconcile-endpoint.test.js` 2 FAIL, pre-existing | sairnlaw owner | either the test or the role decision is stale. Paralegal and attorney now read 200. |
| H1y | the same raw inline-handler id shape in the other apps | app owners | sweep with the `tests/sairnlegacy_inline_handler_args.js` structure arm, adapted per app |
| SDP, LGP, J6, J4, J2, A1, P1, R1, G1, S5, S7, T1 | carried | as in b68 §4 / b67 §8 | unchanged |

**Left uncommitted on purpose (U1):** the same 7 untracked root files.
