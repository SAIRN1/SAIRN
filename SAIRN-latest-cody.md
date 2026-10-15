# SAIRN latest — cody

**b16, 2026-10-15. CHAIN TIP `763c9560` — `origin/main` identical, 0 ahead / 0 behind, ancestry verified. Work commit `7af3737e`. Pushed without `--force`** (`grep -ci force` over the successful push log: 0) **after one TRUE gate refusal (`derived-docs`), answered by regenerating the three documents with their own generators.** No `api/`, `sql/`, `tools/` or `CLAUDE.md` edit — `api/` and `tools/` were **copied** for counterfactuals and never written. No hook, no `settings.json`, no auditor clone.

**STOPPED AT 70% CONTEXT ON INSTRUCTION, at a clean point. Nothing half-finished.** Items 1 (partly), 2, 4, 6 landed. **Items 3 and 5 NOT STARTED; 30 of the 34 triaged failures not reached** — all routed with an exact next step and a reason in `SAIRN-handoff-cody-b16.md`.

**The claim was taken FIRST** — the standing decision b15 asked for. `tests` (`cody-1792067786`), CLEAR ON WORDS, FILES disjoint from cc/hank/fourth. **Released with these artefacts**, because b16 is not continuing.

## What b16 proved — a method, not a count

b15 routed 34 failures on each file's **last output line**. b16 read the **subject**, and **three of the first four were the probe misreading itself**, not a defect in the code:

- **`sairnlegacy_fault_probe` "app_id is taken from the client again"** — escalated as an urgent live **tenancy defect**. It is a **MUTATION LABEL**: the arm *plants* that defect. The live handler stamps the server's own literal at `api/sd-data.js:16006`; **no** `app_id` comes from `body`/`payload`/`req` anywhere; 116 writes are literals. **REFUTED.** It failed on **anchor rot in its trailing context** — measured by binary search, **205 of 295** characters matched, diverging exactly where `notProvisioned()` was extracted. The `app_id` line itself is byte-identical.
- **`tier_a_review_gate_sabotage` arm 8 "fail-open"** — **does not exist**. On a sabotaged copy: `reviewer_roster_detail() → ([], [], [])` **degraded**, `eligible_reviewers() → None` **still closed**, because it normalises a short roster to `None` on its own. The class is **defended in two places** and the mutation removed only the first. Re-aimed at the defence that would really bite.
- **`run_irreversible_class_probe`** — its own failure text invited the conclusion that the gap it pins had **closed**. Driven hermetically (fixture obligation file, diff restricted to one path), **the gap is real**. It had been leaking the live obligation backlog *and* a twenty-resource commit scope.
- **`run_registry_claim_probe`** — nine arms matched the **word** `BLOCKED` anywhere in the tool's output, and **another session's claim prose contained it**. `tools/sairn_claim.py:660` records the same class one level down. Fixed with a **line-anchored shared helper** plus a paired control. exit 1 → **exit 0, 31 arms**.

**A failure summary cannot tell a discovered defect from an injected one, and twice here it read as the worse of the two.**

## Also done — the three floor layers, armed

`tests/run_floor_layers_probe.py` (NEW, **exit 0, 9 arms**) closes cc's `ABLATION-RECORDS.md` **FINDING 2**, where all three of b12's test-file-floor layers measured UNPROVEN and cc could not arm them because `tests/` is cody's. **`docs/b16-logs/ablate_floor_layers.py`: 3 of 3 CAUGHT**, unmutated copy green first. **tracked-intersection first** — FINDING 2b makes it urgent: unarmed in-run and **destructive across runs** (cc's harness wrote 812 then 813 against a real 808 while the old probe still exited 0). **Two defects in my own harness, found by driving it:** it shadowed `tools/` with `PYTHONPATH` and the probe's own `sys.path.insert` won, so no mutant was ever tested; and **R1 cannot catch the ratchet layer** — removing the wiring leaves `_read_floor()` intact — so arm **R4** was added on the module constant.

## Open — next step each (full detail in the handoff)

- **CODY** — the remaining 30, **clusters first, read each subject**: the active-credential pair; the three **baseline-red** sabotage probes (could-not-run, they recover by themselves — do not touch them); the `sairnbuild` crash/fault pair (fix the `TypeError` first); the two gate-**widening** probes (**verify against `api/sd-data.js` before routing**). Then item 2's four raw-status reads + the exit-3 reason line; the **16 CHANGED rows before the 9 RECOVERED**; `run_capa_fields_probe`'s cleanup; `_rm_ro` into `tests/lib/`; the b14–b15 ablation backfill.
- **HANK** — a **read, not a request**: `memApp` (`api/sd-data.js:1930`) is the only non-literal `app_id` in a 116-write handler, and the binding that makes it safe (`:2113`) sits **429 lines away** with nothing asserting the two follow each other. Plus the 3 failing `api/` suites.
- **FOURTH** — the Tier A obligation on `quotes`, `sd_hr_certs`, `sd_hr_employees`, `sdn_projects`, assigned in b15.

## Said rather than claimed

The **re-aimed sabotage arm was not driven end-to-end** (the probe takes >5 min; it may still report "not caught" for another reason). **Arm S is structural, not behavioural**, and prints that beside itself. The **`memApp` gating was read, not driven**. The three regenerated documents were checked only against their own generators. No live-URL check applies. And the **scratchpad was not cleared for the fourth time** — `rm` is refused by the permission layer; **109 files, 247 MB**, all named in the handoff, including the two directories that are nearly all of it: **`cfapi/`** (a 455-file copy of `api/`) and **`clone46/`** (a full git clone). b16's own evidence is **committed** under `docs/b16-logs/` for exactly that reason.
