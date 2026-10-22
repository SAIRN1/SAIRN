# SAIRN handoff — cody b49 (2026-10-22)

Four items, all closed. Nothing is half-finished.

## Committed / pushed state
On origin/main, no force, via `push_retry.py --loop` (it landed on attempt 2; attempt 1 was a transient race):
- `05e92c154` fix(tests): the adversarial-corpus probe was re-derived and its anchors made countable.
- `d6a136606` feat(push-gate): CHECK 5e names `skipped` rows.
- `d14b3b343` the live-residue enumeration for the F3 drive.
- `2f6b51efa` the register record for `05e92c154`.

Each was checked with `git merge-base --is-ancestor` after a fetch. `defect_register --check` reports OK.

Claim held: `sairnlegacy` (b49). The b48 `platform` claim was released at the start of the batch.
The path manifest's cody override for b49 replaces b48's: `tools/sairn_push_gate_hook.py` and the one residue file.

Transcript: `C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cody\2d1bcf76-c842-40ed-b21d-9b20d98e7d45.jsonl`

## 1. "Eight still-open defects": all eight are CLOSED at HEAD
The list is cc's b29 table (`docs/2026-10-20-cc-b29-notes.md` §1), not a cody list. Status of each, with its guarding suite run green today:

| # | defect | closed by | suite (today) |
|---|---|---|---|
| 1 | dental 503 names the wrong schema file | cody b34 | b34-routed-defects 12/0 |
| 2 | prequal/bonding write on a missing table → 502 | cody b34/b35 | b35-missing-table-writes 24/0 |
| 3 | accounting revoke false success | cody b34, b35, b37 | b34-revoke 9/0, b35-repeat 8/0, b37-scope 5/0 |
| 4 | accounting any 400 → NOT_PROVISIONED | cody b34 | b34-routed-defects, b37-routed-arms 6/0 |
| 5 | request photos never read | `9f9cf9235`, hank b41 live | b40 style-profile/request-photos 27/0 |
| 6 | stonedesk style profile reads the wrong level | `9f9cf9235` | same, 27/0 |
| 7 | roofing JHA/warranty read error shown as "none" | fourth `5e38373c6` | sairnroofing_unreadable_reads 10/0 |
| 8 | senior contract/auth stays local | fourth `02cec2f84` | sairnsenior_contract_auth_save 15/0 |

**The routing line "still not resolved as of b48" is stale.** cc b31's "b29's eight still waiting" was true on 2026-10-20. All eight closed on 2026-10-21.

## 2. CHECK 5e `skipped` anchors: RESOLVED, and they were hiding a real red
- **Root of it:** `tests/run_adversarial_prompt_corpus_probe.py` computed its subject from REPO and passed anchors positionally. So probe_anchor_freshness listed its 3 anchors as `skipped`, and 5e ignored `skipped`.
- **What it hid:** the probe was **RED at HEAD**, and had been since `34d1ff0ed` (2026-09-26).
  - Arm 8's anchor had vanished.
  - Arm 4 asserted "5 fenced", but there are 8 today.
  - Arm 10 asserted pre-fixture counts, but the lock now refuses first.
- **Probe fix (tests/, mine):**
  - Arm 8 is re-anchored to the current line.
  - Arm 4 is now a floor (>= 5 fenced).
  - Arm 10 now requires the lock to refuse, the same correction M1 already records.
  - The anchors are `[(SUBJECT, old, new)]`, with SUBJECT a module-level literal.
- **Probe result:** 12/12.
  - Freshness `ok` went from 645 to 648 and `skipped` from 1 to 0.
  - Ablation: the pre-`34d1ff0ed` anchor now reads VANISHED.
- **5e fix (gate, cc's file, under override):** every `skipped` row is a SKIPPED finding.
  - It denies when the push touches that probe; otherwise it is printed as owed.
  - Ablation through the real `--pre-push` in a throwaway worktree: touching the old probe gave a DENY naming SKIPPED, and an unrelated push printed the note only.
  - Hook `--selftest` 56/56.
- **Tool gap found and NOT fixed (cc's tool):** probe_anchor_freshness silently ignores an edit passed as a **bare tuple** argument. It is neither counted nor skipped. My first rewrite hit exactly this: skipped went to 0 while ok stayed at 645. Routed to cc.

## 3. Live F3 verification: DONE through the deployed API; a UI click-through is impossible today
**No UI calls `/api/leg-countersign`** (grep of `sairnlegacy.html`: none), so the flow can only be driven through the API. I drove it on https://sairn.vercel.app with licence LEG-PINNACLE-2026:
1. The demo owner from `docs/2026-09-03-demo-credentials.md` provisioned `b49-f3-apprentice` and `b49-f3-director` with random PINs, never printed or stored.
2. Results:

| step | result |
|---|---|
| C0 — no F3 list | 403 FORBIDDEN |
| owner sets countersign `[leg_cremations]` | 200 |
| D1 — on the list, unsigned | 403 COUNTERSIGN_REQUIRED |
| prepare | 200 |
| apprentice signs own record | 403 NOT_QUALIFIED_TO_SIGN |
| director countersigns | 200 |
| **D2 — apprentice files the signed record** | **200** |
| D2b — same signature again | 409 COUNTERSIGN_ALREADY_SPENT |
| read-back | record present |
| settings restored to prior (`[]`) | confirmed by re-read |
| C1 — after restore | 403 FORBIDDEN |
| both test credentials | deactivated, roster shows `active=false` |

**Residue:** `docs/live-residue/2026-10-22-cody-b49-leg-f3-live.json`.
- It covers 1 leg_cremations TEST row (`CR-B49-F3-LIVE-F3D9FB`), 1 spent token row and 2 deactivated credentials.
- Each comes with blast-radius, removal and confirm SQL. Nothing was deleted by me.
- Audit-log rows are kept by design.

## 4. Methodology
**A checker's `skipped` list is a silent pass.** A probe sat there red for 26 days. In fixing it, "skipped 1→0" was not proof either: the bare-tuple form left it in neither list.

The check is that the **counted total rises by the expected number**, plus an ablation that makes the old anchor read VANISHED. I saved this as a memory. I did not add it to the cross-domain disciplines doc, which is a standing doc owned by fourth; it is offered for #40 if Michael wants it.

## Open, and the exact next step
| # | open | next step |
|---|---|---|
| O1 | probe_anchor_freshness ignores bare-tuple edits (neither counted nor skipped) | cc: lock a fixture for `arm(x, (SUBJ, old, new))`, then count it or report it as unresolved |
| O2 | no countersign UI in sairnlegacy.html (prepare / sign / file) | fourth: a UI over `/api/leg-countersign` + sd-data `x-leg-countersign` |
| O3 | live residue on LEG-PINNACLE-2026 | Michael: run the residue file's SQL, one statement at a time, after its blast-radius query |
| O4 | Tier A review of the b48 F3 deferral `d6b37bb1c` | cc (assigned b48) — the live drive above is evidence for it |
| O5 | cc's routing note "b29's eight still waiting" | anyone editing cc's open list: mark it closed, using the table above |
| O6 | the 2 deactivated test credentials | removal SQL is in the residue file; the app has no delete |

Exact next step for cody: release the `sairnlegacy` claim.
