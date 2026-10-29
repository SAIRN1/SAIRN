# HANDOFF — fourth / ted, batch b69, 2026-10-29

**READ THIS FILE ONLY.** It is the whole state.

- All four dispatch items are landed or resolved.
- Item 1 was already built by cody b66. This batch re-armed it in this clone.
- Item 2 was **API side only**, on Michael's in-session answer. hank holds the `sairnlegacy` claim, so `sairnlegacy.html` was not touched.
- Nothing is held locally. Both claims are released.

**Transcript:** `C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-fourth\83c60d05-1589-4389-a5cf-cd99265bab76.jsonl`

## 1. STATE — every commit, with its own ancestor check

Run after `git fetch`, against **origin/main = `b024198ae3e6`**. Each row is the literal command and its exit code (0 = the commit is on origin/main).

| commit | what | check | result |
|---|---|---|---|
| `75f6f1582` | claim stonedesk | `git merge-base --is-ancestor 75f6f1582 origin/main` | exit 0 |
| `8138dc48d` | fix stonedesk T2/T3/T4 (item 4) | `git merge-base --is-ancestor 8138dc48d origin/main` | exit 0 |
| `d42225897` | register record for 8138dc48d | `git merge-base --is-ancestor d42225897 origin/main` | exit 0 |
| `79f59f818` | claim platform | `git merge-base --is-ancestor 79f59f818 origin/main` | exit 0 |
| `c7d7e74d8` | fix deploy_verify_notify (item 3) | `git merge-base --is-ancestor c7d7e74d8 origin/main` | exit 0 |
| `21eff244f` | register record for c7d7e74d8 | `git merge-base --is-ancestor 21eff244f origin/main` | exit 0 |
| `0d4588f5c` | SDP + LGP open-work rows (item 4) | `git merge-base --is-ancestor 0d4588f5c origin/main` | exit 0 |
| `43f145f8b` | Tier A obligation, classifier | `git merge-base --is-ancestor 43f145f8b origin/main` | exit 0 |
| `a02ed68cf` | fix leg F3 supervisor rule, api (item 2) | `git merge-base --is-ancestor a02ed68cf origin/main` | exit 0 |
| `e5ebbfa4b` | register + Tier A obligation for a02ed68cf | `git merge-base --is-ancestor e5ebbfa4b origin/main` | exit 0 |
| `ebd227c3d` | release stonedesk | `git merge-base --is-ancestor ebd227c3d origin/main` | exit 0 |
| `b024198ae` | release platform | `git merge-base --is-ancestor b024198ae origin/main` | exit 0 |

**Live checks:**
- **Measured:** `stonedesk.html` is byte-identical to origin/main. It contains `INCOMPLETE:` and "Not tracked in StoneDesk", and no `>Dry Cut Violations<` tile.
- **Measured:** `/api/leg-countersign` answers, with a 401 on a bad licence.
- **UNVERIFIED:** the new F3 refusals have not been driven live. That needs an apprentice credential and an F3 row on the audit licence.

## 2. DISPATCH ITEMS

1. **Done-line Stop hook.**
   - **cody b66 had already built exactly this** (`bea263709`): a done-shaped final message with no record from this turn is refused.
   - I wrote the same arms, saw them red, and then found cody's landed fix while resolving a rebase. My duplicate patch was dropped, not pushed.
   - **Armed in this clone:**
     - `builder_hook_presence.py --install --only fourth` reports OK;
     - `.git/sairn-hooks/sairn_done_line.py` is byte-identical to `tools/`;
     - its selftest passes 20/0;
     - the wiring is `settings.local.json` Stop → that copy.
   - **cc's armed copy is STALE** (`MODIFIED-OR-STALE`, blob 6b3fba6e6fd6 vs 01cd849f7b96). That is §3.
2. **leg_cremations F3** (`a02ed68cf`).
   - **The rule:** an apprentice prepares a cremation only when (a) the home's F3 clears it, through `decide(...,'prepare')` (empty, no row or no table → **deny**; `forbidden` wins; unreadable → 502), AND (b) `payload.authorized_by_supervisor` names an active licensed director other than the preparer.
   - At filing, that director **must be the countersigner**.
   - Both are checked at prepare (no token is minted) and again at filing, before the spend.
   - **How it is built:** two optional profile hooks in `api/_lib/countersign.js`. SAIRNlaw sets neither, so law is unchanged (arm L1).
   - **Assumption, stated:** "recorded as authorising" = named in the signed record AND is the signer.
   - **Tests:**
     - `api/b69-leg-f3-supervisor.test.js` was **12/17 RED before** the fix and is 17/0 after.
     - Each of the 4 new guards was ablated, and each turns its arms red.
     - `b48` and `b51` PAYLOADs gained the supervisor field (8/0, 5/0).
     - 9 other countersign and role suites are exit 0.
3. **deploy_verify_notify** (`c7d7e74d8`).
   - `classify_command` now judges each shell SEGMENT, split outside quotes, with `#` comments dropped.
   - cc's probe went from 3 of 10 wrong to **0 of 10**. The entry probe is 27/0, and 4 of its new rows were red before.
4. **SDP/LGP.**
   - **SDP, fourth's rows: FIXED** (`8138dc48d`).
     - The COMPLIANT pill needs COI + licence + W-9.
     - The safety score is computed from evidence; empty shows `--`, and a blank expiry is not current.
     - The silica tiles say Not tracked.
     - cc's stress tool: T2a/T2b/T3a/T3b/T4a **FAIL → PASS**, controls unchanged. The new suite is 8/0 (5/8 red before).
   - **E/I/M/X** (16 more StoneDesk FAILs) and **LGP** (L1/L2 hank's api, L3 fourth's `sairnlegacy.html`) are **ROUTED** as open-work rows `SDP-PRESENCE-FOURTH-B69` and `LGP-PRESENCE-FOURTH-B69`, not fixed.
5. **Methodology.** §1 gives each commit its own literal ancestor command and exit code.
6. Handoff, then report, then push.

**Claims this batch:**
- **Items 1 and 3:** briefly BLOCKED by cody's live `platform` claim. I flagged it and parked it; it cleared within the batch.
- **Item 2:** BLOCKED by hank's live `sairnlegacy` claim. I asked Michael, who answered "API side now".

## 3. OPEN — exact next steps

| # | item | owner | next step |
|---|---|---|---|
| 1 | **SAIRNlegacy UI: no supervisor picker.** An apprentice cannot complete an F3 prepare from the app until `saveCremation`'s prepare call sends `authorized_by_supervisor` | fourth (sairnlegacy.html), after hank releases the claim | Add a "Supervising director" select (active owner/director roster) to the apprentice prepare path; arm it against `api/b69-leg-f3-supervisor.test.js` P8 |
| 2 | Live-drive the F3 refusals | fourth | On the audit licence: one apprentice credential plus an F3 row; drive P1, P4 and P8 against the deployed endpoint |
| 3 | cc's armed done-line hook is stale | cc | `python tools/builder_hook_presence.py --install --only cc` |
| 4 | StoneDesk E/I/M/X presence FAILs | fourth | Index row `SDP-PRESENCE-FOURTH-B69`; M3 (a crash) first |
| 5 | LGP L3 (`legComposeStatement` $0 / netted lines) | fourth, after hank's claim | Index row `LGP-PRESENCE-FOURTH-B69` |
| 6 | LGP L1/L2, plus SDP T1 (api) | hank | The same rows |
| 7 | Two Tier A obligations opened (classifier `43f145f8b`; F3 `e5ebbfa4b`) | any non-fourth session | `python tools/tier_a_review_gate.py --list` |
| 8 | Seven test/api overrides declared in the manifest (`_b69_added_*`) | cody / hank | Review, then remove the lines |
| 9 | Carried from b68 §4 | as listed there | Unchanged |
