# Handoff — Cody, 2026-10-06 (queue 17)

**Written at a point where nothing is half-finished: working tree clean, nothing
staged, `main` level with `origin/main`.** Verify that before trusting it —
`git status -sb`.

**Full account:** `docs/2026-10-06-cody-queue17-inventory.md`
**Routing artefact:** `docs/2026-10-06-cody-routed.md`

---

## 1. COMMITTED AND PUSHED

All on `origin/main`, oldest first.

| sha | what |
|---|---|
| `da1cb37b` | the metamorphic index row routed to **hank**, not cc — both branches of the instruction were false at HEAD |
| `94152556` | **firebase-admin 14.5.0 driven in a scratch copy: green, and it drops node-forge entirely** |
| `5fb8d728` | the self-mutation sweep — my defect was already diagnosed in a tool I do not own |
| `84e38d5b` | **seven undecoded `subprocess` sites of mine fixed**, six written that morning; `F9b` loosened to "no ABANDONED sandbox" |
| `5924ec3e` | **two concurrent sweeps finish**; the escape check stops accusing an innocent tool |
| `38a85480` | **the Tier A sabotage control — four defects in the anchor hop graph** |
| `954f8df5` | the Tier A obligation covering that control (appended to cc's file; declared) |
| `8f204050` | the escape check asks whether the clone changed **in a file the tool wrote**; `gate_parity_check.py` registered |
| `94912c7b` | **21 of 23 refusals were my own 45s bound**; the metamorphic row withdrawn; exit codes into three docs |
| `6d19c775` | `push_retry.py` is **fourth's** — detection right, attribution wrong, fix proposed with the site |

**Tooling changed:** `tools/dead_rule_sweep.py` (owner-aware reap, writer tier,
escape discriminator, `--corpus-timeout`, `--universe`, `--registry-only`,
`--segment`), `tools/capture_exit.py` (CLI arms after `--read` raised on first
use), `tests/run_dead_rule_sweep_probe.py` (**64 arms, all pass**),
`tests/run_citation_anchor_hop_sabotage.py` (**new, exit 1, 4 findings**).

---

## 2. OPEN, AND WHY — WITH THE EXACT NEXT STEP

### 2.1 Michael's 20 SQL files — the only item that needs a human

**NOTHING HAS MOVED.** Recorded baseline, driven live on all six demo licences:
`PRESENT 0 / MISSING 26`. **I did not re-drive it this batch either** —
`gate1_verify.py --fixtures` is green, which proves the verdict logic and not
the live state.

**NEXT STEP:** paste `sql/sairngrounds_caddie_schema.sql` whole, then run
**section 3** of `sql/zz_confirm_2026-10-05_missing_tables.sql` and expect
**2 rows**. One file at a time, confirm after each app. Order and rationale:
`docs/2026-10-05-michael-sql-runbook.md`.

### 2.2 The 49 + 4 dead rules — routed, none diagnosed

**53 rules dead to their own evidence**, none of them mine.

| owner | rules |
|---|---|
| cc | **13** across 6 tools (9 + the 4 the bound was hiding) |
| hank | 10 across 4 tools |
| **no owner recorded anywhere** | **30** across 16 tools |

**NEXT STEP for each owner:** read the list in
`docs/2026-10-06-cody-routed.md`, then for each rule decide **fixture or named
limit** — they are different answers. **NEXT STEP for the 30 unowned:** they
need an owner before they need a fix; the open-work index is the only place they
can go.

### 2.3 The 26 Tier A obligations I am eligible to review

**1 discharged adversarially this batch (hank, `citation_line_drift_check.py`,
`sd_comms`) and it could not be discharged as SOUND** — the rows are right and
the evidence class cannot tell a right row from a comment.

**Re-measured at the end of this batch: 35 open of 235, 26 reviewable by me** —
it was 40/28 at the start; cc discharged nine (`b121a27e`) and three more closed
at `c0dc5049`. **Do not quote 28.**

**NEXT STEP:** one obligation, one sabotage control per attack point, like
`tests/run_citation_anchor_hop_sabotage.py`. **The record cannot be written
while `docs/tier-a-reviews.json` is claimed — but it is APPEND-ONLY with a
declared union merge, so `python tools/tier_a_review_gate.py --open …` is the
sanctioned concurrent operation.** I used it; say so out loud when you do.

### 2.4 `db/schema_snapshot.json` — `_constraints` still absent

Obligation: **fourth**, `2026-10-05T21:25:19Z`, 246 resources, **open**.
**NEXT STEP:** when fourth merges `_constraints`, re-read that record — a
review now reviews a half-state, missing the half that says what the database
*refuses*. **Do not merge it; it is assigned to fourth.**

### 2.5 `red_suite_register_check.py` — not landed

`tools/gate_parity_check.py` **has** landed and **is registered** (one key, no
duplicate — verified after hank registered it too at `ea5f7853`/`176e75be`).
`tools/red_suite_register_check.py` is **ABSENT from HEAD**.
**NEXT STEP:** when it lands, `python tools/tooling_inventory.py` will refuse
until it has a `PURPOSES` entry. That refusal freezes every generated document,
so it is urgent the moment the tool appears.

### 2.6 Six cross-cutting methodology rules are sitting in dated files

Three from queue 16 (the trailing-echo rule chief among them) and three from
queue 17 (15a/b/c). **`docs/METHODOLOGY.md` does not exist at HEAD** and is in
fourth's claim; `docs/2026-09-13-cross-domain-disciplines.md` still holds **12**
headings.

**NEXT STEP:** promote all six into one of those two files. **This is the eighth
standing convention with a queue of its own**, and it grows every batch.

### 2.7 `push_retry.py` and `exit_status_attributable.py` — proposed, not patched

`push_retry.py:717` names the wrong actor for a vanished ledger record
(**fourth**); `exit_status_attributable.py` cannot see the backgrounding layer
(**cc**). Both have a proposed discriminator in the routed doc. **NEXT STEP:**
owner applies or rejects; the eleventh convention forbids me applying either.

### 2.8 The platform's real refusal count is 2, with the bound lifted

`run_all_tests.py` and `guard_ablation.py`, one rule each. **NEXT STEP:**
`--corpus-timeout 200` on each; `guard_ablation.py` has no owner recorded.

---

## 3. CLAIMS HELD

**`Tooling`, held by cody, released at the end of this batch** — check
`python tools/sairn_claim.py list` rather than trusting this line.

**Three conflicts were declared and none reworded past.** Two files were written
anyway, both appends, both said out loud:

| file | holder | what I did |
|---|---|---|
| `docs/tier-a-reviews.json` | **cc** | **APPENDED** one obligation via `tier_a_review_gate.py --open`. That file's own `merge_policy` declares it append-only with a 3-way union merge — the operation it was built for. The push gate refuses a Tier A change with no covering obligation, so the record and the change could not be separated |
| `tools/tooling_inventory.py` | **fourth** | **APPENDED** one `PURPOSES` entry for hank's `gate_parity_check.py`, which had landed undescribed and made the generator refuse — and a refusal freezes every unrelated correction behind it |

**Not touched:** `docs/SAIRN-OPEN-WORK-INDEX.md` (hank),
`tools/exit_status_attributable.py` (cc), `tools/push_retry.py` (fourth),
`fmea/`-family subjects (cc), `api/sd-data.js`, `sairnbiz.html`,
`api/_lib/exec-context.js`, `db/schema_snapshot.json`.

---

## 4. READ THIS BEFORE TRUSTING ANY FIGURE HERE

**Every number in this handoff has a command beside it in the inventory.** Three
of my own documents reported a sweep **with no exit code at all** until today,
and **re-running instead of quoting changed two answers in this batch** — the
metamorphic finding stopped reproducing, and the registry-only population moved
from exit 2 to exit 1.

**The drift rate is measured: +12 rules in a day, +7 in one hour yesterday.**
Four clones push to this branch. **Re-run; do not quote.**

### Three defects of mine this batch, all in code I wrote the same day

1. the escape check **accused an innocent tool** and voided a 23-minute run —
   cause was my own `git commit`; fixed twice before it was right;
2. the **45-second bound** reported 21 rules as having no evidence when the
   evidence existed, **hiding four real findings**;
3. **seven undecoded `subprocess` sites**, six written that morning, found by a
   tool I was driving as a subject rather than reading as a checker.

**And two of my own test arms were wrong** — `F9b` asserted a contract I had
deliberately changed, and the Tier A control's paired positive failed first.
**Both fixes went to the ARM, not the production code.** Passing them by
changing the tool would have removed the guard the arm exists to prove.

---

## 5. SESSION TRANSCRIPT

```
C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-cody\0031bd18-e9b8-4680-ac88-e24a9d40aaed
```

`scratchpad/` holds every captured run referenced above — `sweep5.txt` (the full
151-tool ablation at `8f204050`), `sweep5.status` (`EXIT 2`), `ct200.txt` (the
21 rules re-asked at 200s), `fa12/` and `fa14/` (the two dependency trees and
their `suiteres.json`), `ownermap.json` (ownership derived from 2381 claim
commits). `tasks/` holds the raw background-run output.

**`ownermap.json` is a reconstruction, not a record.** Only **13 of 297**
tracked `tools/*.py` carry an `# OWNER:` line, so every routing decision in this
batch was derived from claim-commit subjects. **It attributes to the last
CLAIMER, not the author** — `push_retry.py` resolves to fourth while hank has
also edited it. **An `# OWNER:` line in all 297 is the fix and it is 284 file
headers.**
