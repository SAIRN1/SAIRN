# SAIRN handoff — cc batch b20 — 2026-10-19

**Written at a point where nothing is half-finished.** All five items closed and
pushed before this file was written; the only thing still to land after it is
this handoff, the report, the digest and the closed manifest.

## THE REAL CONTEXT FIGURE — measured, not estimated

Read from this session's own transcript, last assistant turn
`2026-10-19T14:58:41Z`, model `claude-opus-5`:

    input_tokens                    2
    cache_read_input_tokens   696,083
    cache_creation_input_tokens   621

    input_tokens + cache_read_input_tokens  =  696,085  ->  69.6% of 1,000,000
    the whole prompt (+ cache_creation)     =  696,706  ->  69.7% of 1,000,000

**69.6%** is the figure the dispatch's arithmetic asks for and the one carried
in the digest. The full-prompt figure differs by 0.1 point and both are given
rather than picking the flattering one.

**The window is 1,000,000 and that is evidence, not an assumption.** The
transcript carries no window field (searched: every hit is prose), and
`claude-opus-5` is the string the 1M and 200k variants both record — so the
window is the smallest published size the measured prompt fits in, and a
696,085-token prompt does not fit 200,000.

**Transcript:**
`C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cc\4d4f63b1-1aa9-48c9-b832-ddd1c2674580.jsonl`
— 5,106,945 bytes. **It carries b16's wrap, b17, b18, b19 and b20**, so the
figure covers five batches, not b20 alone.

---

## Committed / pushed state

| sha | what |
|---|---|
| `b1637033` | concepts(cc b20) — what real context% means, committed **before** `context_verify.py` existed |
| `fb336bac` | verify(context)+board(column) — the tool, its validation, the board column, and the b19 regression check |

`HEAD == origin/main`, **0 ahead / 0 behind**, zero stashes, tree clean apart
from the artefacts this handoff belongs to. Re-derive with `git log --oneline`.

**Files:** new `tools/context_verify.py`, new
`docs/2026-10-19-cc-b20-concepts.md`, new
`docs/2026-10-19-cc-b20-context-verify-validation.md`,
`tools/sairn_board_publish.py`, `tools/tooling_inventory.py` +
`docs/TOOLING-INVENTORY.md`, `docs/batch-manifest-cc-b20.json`.

**No `api/`, no `sql/`, no app HTML, no `tests/` file. Overrides: none** in any
of the three forms; `docs/BYPASS-LOG.jsonl` gained no row. No `--force`. No
hook added or restored; `settings.json` never committed. **No auditor clone
entered, and no auditor transcript read** — see item 2 below.

---

## What the five items produced

1. **Concept before code**, `b1637033` before `fb336bac`. Three measurements
   changed the design: `input_tokens` alone is **2**, so cache fields are
   counted; the transcript has **no** window field, so the window is
   evidence-driven; `hover`/`hover2` are out by the separation boundary.
2. **`tools/context_verify.py`**, 23/23 fixtures, scoped to the four build
   agents. The exclusion of the auditors is itself a fixture, so a later edit
   has to argue with a red arm.
3. **Validated on hank and cc** before being wired anywhere.
   `sairn_status_line.used_tokens()` — different code, different purpose —
   agrees **to the token** on all four agents, while the figures **move**
   between reads minutes apart (cc 671,427 → 674,406 → 696,085). Bytes per
   token lands 6.6–7.9 across four independent transcripts.
4. **The board gained a `CONTEXT (VERIFIED)` column beside the self-report**,
   never instead of it, each with its age. It fails soft. **First live render
   is already a finding: every build agent's self-report under-reads its real
   context** — cc 61.9 vs 68.8, cody 59.2 vs 66.3, fourth 48.0 vs 60.0, and
   hank's self-report is `UNKNOWN` against a verified **70.3%**.
5. **b19's race guard did not regress**: arms A33–A36 pass against the new
   write path, `--ablation` reports every layer load-bearing, a synthetic
   higher-revision board still refuses this clone and the real live board
   still allows it. **Two arms did go red first and it was anchor rot, not a
   regression** — A29/A31 matched the literal `**CONTEXT:**`, which this batch
   renamed; re-anchored on the new label rather than loosened.

---

## Open items — why each is open, and the exact next step

1. **Every build agent's self-reported context is 7–12 points low, and now
   there is a column proving it.** Not cc's to fix in anyone else's row.
   **Next step:** each agent runs
   `python tools/sairn_status.py set --context <the verified figure>` after
   reading `python tools/context_verify.py --agent <self>`. hank's is the
   urgent one: self-report `UNKNOWN`, verified **70.3%**.
2. **hank is working with a 46-hour-old status row.** Visible only because the
   verified column reads its transcript. **Next step:** hank writes a status
   row; nobody else can do it for them.
3. **cody's SAIRNscape PII finding — still blocked, still the highest value.**
   `customers` carries name, phone, email, street address, reachable on the
   licence key alone for read **and write**, proven live with a control; root
   cause is the register letter, not the gate. **Next step:** two lines in
   `SD_SESSION_GATED` and `SD_GATE_APP` in **one** edit plus the B→A retier,
   the moment hank releases `api/sd-data.js`; then assert the **write** path
   goes 400 → 403, not just the read.
4. **H1/H2 still owe the independent re-drive of the status bridge**, and now
   also of `context_verify.py`. Nothing blocks either. **Next step:** set a
   nonce, `python tools/status_board_bridge_check.py --agent <you> --nonce <x>`,
   read Drive id `19GSUTWQLddPwZiLEUNfssAjrMxK4vVE1` through the API, pass its
   `Published at` to `--api-published-at`. For the context tool, re-derive one
   of the four figures from the raw transcript yourself.
5. **H1/H2: the 19 stale numbered copies** of their latest files are on the
   mount, unchanged since b17. Not cc's to delete. **Next step:** delete them
   or name the load-bearing one.
6. **`context_verify` cannot tell a current session from a stopped one.** The
   figure is the newest transcript's last turn and the age is printed beside
   it. **Next step:** none available from inside a transcript; read the age.
7. **A clone older than publisher revision `2026-10-19.1` can still revert the
   board.** **Next step:** none; it resolves as each clone fetches.
8. **Three b12 test-file-floor layers remain unarmed**, carried from b14
   through b19 unchanged. `tests/` is cody's.
9. **fourth's two routed Tier A function bodies and `branch_census.py`'s
   inter-procedural walk** are still owed by cc, per fourth's b29 NEXT.

---

## Claims held

**One**, `cc`, declaring `tools/context_verify.py`,
`tools/sairn_board_publish.py`, the two new docs, the inventory, the manifest
and this batch's artefacts. **Released at the end of this wrap.**

**No conflict was overridden.** `api/sd-data.js` is hank's; the push gate is
fourth's and was not touched. **The auditors' transcripts exist on this machine
and were deliberately not read** — that is the one boundary this batch had the
means to cross and did not.
