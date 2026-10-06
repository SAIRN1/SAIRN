# Handoff — hank, 2026-10-06

**Written before the final report and at a point where nothing is half-finished.**
Every item below is either committed and pushed to `origin/main`, or explicitly
open with its next step named. There is no in-progress edit on disk.

- **Clone:** `C:\Users\marsh\Documents\SAIRN-hank`, branch `main`.
- **Working tree at the time of writing:** clean except this file and the batch-9
  inventory, both committed in the same change.
- **Full account:** `docs/2026-10-06-inventory-hank-batch9.md` (batch 9),
  `docs/2026-10-05-inventory-hank-batch8.md` (batch 8).
- **Session transcript:** this session's Claude Code transcript lives under
  `C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-hank\`,
  alongside the auto-memory directory. **Identify it by date — 2026-10-06 — not
  by a counter**, the same rule the handoff naming convention uses. The hover
  auditors' logs referenced throughout are **outside the repo**, at
  `C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-hover\hover-audit-log\hover-audit-log.jsonl`
  and the matching `…-SAIRN-hover2\…` path. There are **two** instances and both
  number from 1, so a bare `seq 551` is ambiguous — always say H1 or H2.

---

## 1. Claims held

**`platform`, claimed 2026-10-06 (re-claimed after my first claim expired
mid-session).** Released at the end of this batch — if you are reading this and
`sairn_claim.py list` shows a hank claim, it is a newer one, not mine.

**Declared conflicts, none reworded past:**

| file | owner at the time | what I did |
|---|---|---|
| `tools/tooling_inventory.py` | fourth (claim **expired** 6.9h mid-session) | wrote a `PURPOSES` entry, found another session had already landed one in `8f204050`, **reverted mine in full**, kept only two measured facts appended to theirs |
| `docs/tier-a-reviews.json` | cc (claim expired) | **not written this batch.** My three batch-8 obligations are intact, still `open`, assigned `cody` |
| `tools/capture_exit.py` | cody | **adopted as a caller, not edited** |
| `docs/METHODOLOGY.md` | fourth (expired) | added one row to its **routed queue**; did not promote anything into the standing conventions |
| `docs/SAIRN-OPEN-WORK-INDEX.md` | cc by convention; **in no active claim's file set at HEAD** | took it and wrote 15 rows |

### The claim-system finding, which matters more than any single file

At **2026-10-06T13:54Z**, `sairn_claim.py list` returned **No active claims** —
cc's, fourth's, cody's and my own all past the 4h expiry — while
`sairn_status.py` showed **every session LIVE with a running PID**, cc's status
row last written 11 hours earlier.

**A live session with an expired claim and a stale status row is
indistinguishable from a dead one**, and the claim record's own 4h rule then says
its files are takeable. I took two such files deliberately and said so in the
claim string. **This is a gap somebody should decide about, not a thing I did
wrong** — but the next session will face the same ambiguity.

---

## 2. Committed and pushed

All on `origin/main`. Verify with `git log --oneline` rather than this list.

| what | sha |
|---|---|
| `tools/gate_parity_check.py` landed (registration pending at the time) | `ab1526a4` |
| the `SAIRN_SEED_GATE=off` bypass recorded | `0bbffb7c` |
| 21 unrouted hover pairs → 6 routing rows | `cd38d31c` |
| three rows for work that landed and was never recorded | `f5c2fa02` |
| the `sfBottleFill` phantom corrected **at its source comment** | `5d54cc1f` |
| fourth's two routed findings merged | `d4b20258` |
| six subagent definitions scoped | `fc123175` |
| three hardcoded clone paths + `tools/cp1252_console_sweep.py` | `c07b308e` |
| `TOOLING-INVENTORY` regenerated (311 → 312) | `430fd894` |
| ten more drift rows | `264d8c3f` |
| the blinding fixture deleted + methodology routed | `4489d4f3` |
| the billing-in-a-clinical-role-set sweep | `ea3fcb06` |

---

## 3. OPEN — in priority order, with the exact next step

### 3.1 THE ONE THAT MATTERS: `alf_compliance_rules` / `evaluate`

**It is #877 with the resources swapped, it is HIGH, and it is not fixed.**

`api/sd-data.js:11948` gates on `verifySessionToken` **alone** (`:11949-11950`).
With `payload.include_staff === true` (`:11994`) it fetches **every**
`alf_staff_credentials` row on the licence filtered by `license_hash` alone
(`:12033-12034`), builds a per-staff structure carrying `name`, `position`,
`hire_date` and the full training-hours array, and returns it at `:12077`.

**The sibling reading the same table does not do that:**
`alf_staff_credentials`/`read` at `:12080` resolves `ALF_CRED_READ_ROLES`
(`:11865`) and filters every other role to `staff_id === session.employee_id`
(`:12091`), echoing `scoped_to_self` at `:12098`.

**Failing roles:** `med_aide`, `activities`, and every role outside
`{owner, billing, nursing}`. `owner`/`billing`/`nursing` are correctly
unrestricted on both and are the control proving this is about the other roles
rather than about `include_staff`.

**NEXT STEP:** resolve `ALF_CRED_READ_ROLES` in the `evaluate` branch and apply
the same self-scope filter to `opts.staff` **before** `evaluateTraining()` sees
it. Drive it with a suite shaped like `tests/sd_data_family_mar_gate.js` (real
handler, auth/licence/`fetch` mocked), two staff rows distinguishable by
`staff_id`, a DENIED arm per failing role, an **ALLOWED arm per broad role** so
the fix cannot be *deny everything*, and an ablation against the unmodified file.

**`tools/gate_parity_check.py` does NOT catch this** — measured with `--json`, not
assumed. It groups by the resource the **branch** is keyed on; a cross-resource
disclosure is outside its model. Do not take a clean run there as cover.

**The hover auditor has confirmed the same uncommitted state six times and has
stopped re-routing it.** Open ~16h25m with a complete spec for ~9h by its
measurement. Index row: search `HOVER-H1-892-894-913-ROUTED-HANK-2026-10-06`.

### 3.2 `employee_id` is case-sensitive in 14 verticals

Deactivating `Alice` then creating `alice` yields two rows, the second active —
**the deactivation accomplishes nothing.** Driven end to end against the real
`api/mech-auth.js` with `fetch` mocked to behave as a plain-text unique index
actually does: 6 passed, 0 failed. 17 verticals exist, 16 checked, **0 clean**.

**NEXT STEP is a migration decision before any code:** `citext` fixes reads and
the unique index together but migrates live credential tables; normalise-on-write
fixes new rows and leaves existing variants; both needs a backfill that decides
which of two rows wins. **Whoever takes it must drive the `set_active` sequence
as the acceptance test** — a suite that only proves login still works passes
against the unfixed code. Index row: `HOVER-H2-551-556-564-ROUTED-HANK-2026-10-06`.

### 3.3 Seven role sets with a money-facing role over clinical data

Listed with file:line in the inventory §11 and in the index row
`ROLE-SET-SWEEP-HANK-2026-10-06`. **Nothing narrowed, deliberately.**

**NEXT STEP:** a product decision per app. If any set is narrowed it must be
narrowed **at its declaration** so every consumer moves together —
`ALF_FAMILY_READ_ROLES` is consulted on two actions and
`DNT_PATIENT_BROAD_READ_ROLES` on five resources plus `dnt_appointments`.

### 3.4 Smaller, each with a row

- **SAIRNscape Tier A gating** — `scp_designs` became a third Tier A resource in
  batch 8 and is still authorised by the licence key alone.
- **`stonedesk_shop_slug` / `sb_employees` / `dnt_linked_employee_id`** — three
  more of the normalisation class; the `shop_slug` one is cheapest and most
  customer-visible (a published shop unreachable by casing).
- **The `data: payload` sweep** — batch 8 fixed the SDN branch; nothing swept the
  rest of `api/sd-data.js`.
- **`citation_line_drift_check.py` cannot anchor any SAIRNscape row** (it does not
  know the `scpSt`/`scpLd` idiom) and prints no SEEN/EXIST line.
- **cc's three routed items** — row-95 exact-10 list, row-82 figures,
  `dnt_supplies` B→A — **named in her claim, never delivered.** Do not invent
  them.
- **`tools/gate_parity_check.py` registration** is landed, but the tool is
  **UNWIRED**: nothing points it at the codebase on a schedule.

---

## 4. Things that will mislead you if nobody says them

1. **The drift backlog going UP is not the register getting worse.** 158 → 178 →
   168 across two batches. Every correct function-name anchor added is one more
   cite the nearest-write-site **proxy** can disagree with. On `sv_herdhealth`,
   **seven flagged citations are all correct.** A backlog count is not a defect
   count.
2. **`hover_routing_gap_check` EXIT=0 is true of a moment, not a state.** It was 0
   at the end of batch 8 and 21 a few hours later. Two more arrived during the
   final verification of this batch and were routed. Re-run it; do not quote it.
3. **A harness's "completed (exit code N)" is never a program's exit status.** Use
   `python tools/capture_exit.py --status <f> -- <cmd>` then `--read <f>` for
   anything backgrounded.
4. **Regenerate `TOOLING-INVENTORY.md` AFTER the commit that adds a tool**, not
   before. Its universe is `git ls-files tools/`, so the count changes when the
   file becomes tracked — two runs, and the push gate regenerates independently.
5. **Commit messages go through a file.** `-m "...with \"quotes\"..."` closed the
   shell string early and git read the remainder as pathspecs, exiting 127 with an
   error about a FILE for a defect in a MESSAGE.
6. **`.claude/agents/*.md`:** `tools:` is enforced (a documented allowlist);
   **`disallowedTools:` and `isolation:` in frontmatter are NOT verified** — pass
   `isolation: "worktree"` on the `Agent` call for `sweep-runner`, where it is
   load-bearing.

---

## 5. If you take only one thing

**Everything I got wrong this batch — five separate defects — was found by
running the thing, never by reading it.** Three were inside a checker whose own
fixtures were tidier than production, and two of those three blinded it to the
very defect it was built to catch.

The cheap detector is in `docs/METHODOLOGY.md`'s routed queue: **run the checker
against the real pre-fix file, not only against its fixtures.**
