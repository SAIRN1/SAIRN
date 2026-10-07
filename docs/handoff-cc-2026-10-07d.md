# CC handoff — 2026-10-07, batch 15

**Seventh handoff in this run.** Batch 9 → `handoff-cc-2026-10-06.md`; 10 → `-06b`;
11 → `-06c`; 12 → `handoff-cc-2026-10-07.md`; 13 → `-07b`; 14 → `-07c`; this is 15.

**Every figure carries its command, its commit and its date. Every exit code was
read from captured program output — never from a harness status.** Every green
states how many runs against that SHA and what the first run returned.

**Written at a point where nothing is half-finished.** Every item is DONE or
BLOCKED-with-a-named-blocker. Nothing is mid-edit, nothing is uncommitted, and
the push landed before this file was written.

---

## 1. Committed and pushed state

**`0d5077c7` on `origin/main`, `origin/main...HEAD` = `0 0`**, fetched
2026-10-07T18:4xZ immediately before the push that landed it. Fourteen commits
this batch, every one pushed:

| commit | item | what |
|---|---|---|
| `486634b3` | 0, 1 | Tier A: **one discharged**; the three-way chokepoint is **stale both ways** |
| `6860aee4` | 3 | `--reseat` reported success over a register its own `--check` refuses |
| `92071d45` | 4 | **eight** sites exited 1 (FINDINGS) where the message said COULD NOT RUN |
| `83da8d39` | 7 | `condition_coverage` cleanup discarded its exit code — H1's finding |
| `f97831ff` | 5, 6 | routed: item 5 blocked on a credential, item 6 already fixed and unproven |
| `02d2569e` | 9–13 | diagnostics |
| `1bbe4631` | — | MASTER-PLAN + traceability regenerated (the gate refused the push naming both) |
| *(+ merges and the register records)* | | |

**The scoped seed exemption was used, never the blanket one.** `SAIRN_SEED_GATE=off`
was not set at any point in this batch. The seed gate refuses because of **Maine**,
which is item 5, which is blocked — the drift is byte-identical before and after
my commits and was proved so in batch 14.

---

## 2. Claims held

**ONE: subject `cc`, batch 15**, taken 2026-10-07T17:0xZ, pushed and visible.
**Released at the close of this batch:**

    python tools/sairn_claim.py release cc

### THE THING TO READ BEFORE ANYTHING ELSE — four files are NOT mine

`cody`, `hank` and `fourth` each re-derived that **cc holds**
`tools/sairn_push_gate_hook.py`, `tools/report_only_checks.py`,
`tools/doc_sha_reseat.py` and `docs/tool-owner-map.json`. hank's live claim says
in so many words: *"the push-gate hook is CC'S in FILES at 2.5h, so the scrutiny
extension is NOT started."*

**I released that claim at the close of batch 14 and this batch did not re-take
any of the four.** All four are DECLARED IN FILES BY NOBODY. They are free.

### And the ledger was free too

cody (1.3h) and hank (1.2h) both narrowed their own item 1 to report-only citing
fourth's claim on `docs/tier-a-reviews.json` at `2026-10-07T16:01:18Z`. **That
claim was released.** Fourth's live claim is batch16, taken 16:36:02Z, and its
FILES list does not contain the ledger — its task text contains no Tier A mention
at all. So two sessions spent their most-overdue-first item **listing** their
eligible obligations on a hold that had ended 35 minutes before they read it.

**`tools/tier_a_review_gate.py` IS declared by cody and is the one real hold.** I
ran it; I did not edit it.

---

## 3. Per-item state

| item | state | commit / figure |
|---|---|---|
| 0 Tier A | **DONE — 1 of 4 cc-owned, most overdue first** | `486634b3` |
| 1 holds | **DONE** — nothing stale of mine; the chokepoint is | `486634b3` |
| 2 inventory | **DONE** — `G:\My Drive\builder-inventory.txt` | 317 tools / 62 skills / 8 methodology |
| 3 `--reseat` | **DONE** — prevention + backstop, 11-arm probe | `6860aee4` |
| 4 exit codes | **DONE — EIGHT, not six.** R4 now **zero** over 711 files | `92071d45` |
| 5 Maine | **BLOCKED on a credential only Michael has** | `f97831ff` |
| 6 `--open` HEAD | **DONE as coordination.** Already fixed; **unproven** | `f97831ff` |
| 7 condition_coverage | **DONE** — :266 fixed, :254 and :362 documented | `83da8d39` |
| 8 checkpoint cadence | **DONE — set to 1** | memory |
| 9 `/context` | **DONE with a refusal**: I cannot run it | `02d2569e` |
| 10 CLAUDE.md size | **DONE** — 17,618 bytes, ~4,762 tokens | `02d2569e` |
| 11 filtered runs | **DONE** — already filtered; idiom now fixed | `02d2569e` |
| 12 large reads | **DONE** — compliant; the risk is a **document** | `02d2569e` |
| 13 compaction | **DONE** — preserve-list stated and it IS the checkpoint file | `02d2569e` |
| 14 handoff | **DONE** | this file |

---

## 4. Open work — the exact next step for each

### Item 5 — Maine. BLOCKED, and the blocker is a person.

Everything is ready and verified. 14 rules; 2 calendar years with 11 and 10 dates
under *4 M.R.S. sec. 1051*, retrieved 2026-09-21. Drift re-measured read-only:
**MISSING 14 rules + 2 holiday years, DRIFT: 16 entries.**

`add_rule` and `add_holidays` were gated to an **OWNER or ATTORNEY session** on
2026-09-27, because before that the licence key alone could **overwrite** a
deadline rule. `SAIRNLAW_EMP` and `SAIRNLAW_PIN` are not set, are not readable
anywhere in this clone, and are a person's PIN on the canonical licence. **I did
not guess at a credential that authors legal deadline rules.**

    SAIRNLAW_LICENSE_KEY=LAW-PINNACLE-2026 \
    SAIRNLAW_EMP=<owner-or-attorney> SAIRNLAW_PIN=<pin> \
      python tools/load_deadline_seed.py maine

`maine`, not `me` — the loader resolves the FILE name. Then verify by a **changed
compute on identical inputs**; `sairn_load_state_check --app sairnlaw` going 1 → 0
is the cheap half and the loader's exit code is not evidence.

**This blocks every seed-touching push for every session**, which is how I met it.

### Item 6 — cody. Fixed, and never exercised.

`18078d38` fixed `--open` to derive the sha from the **file set** and it is an
ancestor of `origin/main`. Driven in the discriminating case: three file sets not
touched at HEAD all return the file-set commit, `basis='file-set'`, each equal to
`git log -1` over its own files, **all three differing from HEAD**.

**And zero of the 238 records carry `opened_at_sha_basis`** — the field the fixed
code writes on every record. The fix landed 16:52:34Z; the newest record was
opened 15:13:50Z, **1h39m earlier**. ted's 4/4 replication was against records
written *before* the fix. **The fixture that fails first is now a one-field
assertion on the next `--open` by anybody, and it is cody's to write.**

### Item 3's leftovers — fourth and hank. Four collision pairs.

`--reseat` refuses to collapse them and names all four; it exits **1**, because a
partial repair is not a success. `88d7543b2698`→`f2ee7be0d6da` (**fourth**);
`8ae20da10239`→`6a2690bec035`, `e90d8775c7b2`→`d051c89faa16`,
`f13f4f4982d3`→`7ed27c5e78fa` (**hank**). Which of each pair survives is a content
question the tool must not decide.

### Nine leftover worktrees — not mine to prune.

Including `condcov-69780`, `condition_coverage`'s own residue from a run that
predates item 7's fix. Full list in `docs/2026-10-07-cc-routed-b15.md` §4. **A
worktree belonging to a live run is not mine to delete**, and pruning across
another session's scratchpad is the destructive version of being helpful.

### Item 9 — Michael. `/context`.

It is a client-side command; a model turn cannot invoke it. **Please type
`/context` and paste it.** Everything measurable from inside is in
`docs/2026-10-07-cc-batch-15-diagnostics.md`, and the headline is that the primers
are not the problem: **`docs/SAIRN-OPEN-WORK-INDEX.md` is 2,379,765 bytes ≈ 643k
tokens, so one whole-file read is two thirds of the window**, and `CLAUDE.md`
points a fresh session straight at it.

---

## 5. My own defects this batch, cause-tagged

| what | cause tag | how it was caught |
|---|---|---|
| Counted a calendar key named `holidays` and got **0 holidays for all 34 jurisdictions**. The key is `dates` | `wrong-field-name-read-as-a-finding` | running the count across **every** jurisdiction, not just Maine — a result saying every state is broken is a result about the reader. Nothing was reported |
| Batch-14 R1 claimed `--reseat` "also writes `docs/scrutiny-flags.json`". It does not — one owner, `exit_status_attributable.py` | `co-occurrence-read-as-causation` | `grep -rn scrutiny-flags tools/*.py` while fixing the real half. Corrected in `f97831ff` |
| A patch script anchored on text containing an escaped newline; matched zero times | `anchor-escaping-mismatch` | the script refused and wrote nothing — the right failure. Redone by verified line range |

---

## 6. Methodology — routed, not written into `METHODOLOGY.md`

That file is **fourth's** at this HEAD. Routed in
`docs/2026-10-07-cc-routed-b15.md` §6:

**Re-check a declared conflict when the blocked item comes up, not only when the
claim was written.** A claim string is composed once at batch start and cannot be
updated without re-claiming, so every conflict analysis inside it ages. Three
sessions were blocked today on holds that had ended. And the half that makes it
actionable: **separate DECLARED-IN-FILES from MENTIONED-IN-PROSE** (PR §4.3) — of
six contested files, **five were prose-only** and exactly one was really held.

---

## 7. Transcript

This session's conversation. **No file on disk** — it must come from the terminal
scrollback. The commits carry the evidence; every figure in them was captured from
program output at the time, not reconstructed. The batch-15 checkpoint, rewritten
after every item under cadence 1, is
`~/.claude/projects/C--Users-marsh-Documents-SAIRN-cc/memory/batch15-progress.md`.
