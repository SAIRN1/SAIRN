# LATEST — fourth / ted — batch b27 (RESUMED) — 2026-10-16

**FIVE OF SIX ITEMS DONE, manifest 5 done / 1 blocked, and the blocked one says
why.** `HEAD == origin/main` at **`1ce94b6b`** when this was written, 0/0,
**NOT forced** (ancestry-proved — `git merge-base --is-ancestor <pre-push tip>
HEAD` → ANCESTOR; `grep -ci force` → 0 on all three push logs), and **landed
verified ON ORIGIN by reading the files back**, because a clean exit from
`git push` is not proof. No `SAIRN_SEED_GATE` / `GATE_EXEMPT` / `SAIRN_SKIP` in
any form — **the push was REFUSED THREE TIMES and every refusal was read rather
than overridden.** `settings.json` untouched, hooks untouched. **0 files written
under `api/ sql/ tools/`** — every mutation ran against a COPY in a tempdir.
Auditor clones not entered. **The live tip is ahead of that sha by the commits
carrying this file**, by design. **CONTEXT 24.7% of 1000k** (246,727 tokens).

**b27 WAS DISPATCHED 2026-10-15 AND LANDED NOTHING.** Both test files sat
uncommitted, the manifest untracked, and its item-1 evidence cited
`docs/2026-10-15-fourth-b27-findings.md` — **which does not exist at HEAD, on
origin, or on disk.** This is the resume.

---

## The four things

1. **MY PREDECESSOR'S REPAIR OPENED A HOLE AND ONLY A SECOND ABLATION FOUND
   IT.** Collapsing every string literal to `''` closes the block-comment
   mutation and blinds the assertion to **which** string the first argument was.
   `'write'` → `'read'` at the retry call site was **ACCEPTED at 25 passed, 0
   failed** — a retry that reads drains the pending queue saving nothing while
   reporting success, and the arm whose entire subject is the retry's **write**
   stayed green. Fixed with **two copies and two assertions, neither sufficient
   alone**; re-ablated **10 of 10 REFUSED**, each on the named arm.
2. **THE TIER A DISCHARGE WRITE IS BLOCKED FOR THE SECOND CONSECUTIVE BATCH** —
   `docs/tier-a-reviews.json`, by **cc** at `2026-10-15T16:55:20Z` and by
   **hank** at `2026-10-16T11:17:27Z` (`CLAUDE_PID 26072` confirmed RUNNING
   twice). **Flagged back, not reworded.** The review work is complete and
   ablated; only the write is outstanding, and it is one command.
3. **THE 26 UNRESOLVED CENSUS LINES ARE 0, AND b26's STATED REASON WAS RIGHT
   FOR 3 OF THEM.** `api/sd-data.js:748` is `const resource = body &&
   body.resource;` — one line, 14,000 lines above its last reader, and the
   table name the caller chooses. **Three separate mechanisms each
   independently hid it:** a 400-line lookback (**b23's 14-line window a third
   time, inside the rule built to kill it**), `body` being in `CALLER_ROOTS`
   *and* `NOISE` with `NOISE` filtered first, and the `IDENT` regex tracing JS
   keywords and property names.
4. **ONE OF THOSE FIXES REMOVED AN OVER-REPORT**, at `:13364`, where
   `session.employee_id` had been read as a caller value. **Every under-report
   had already gone to zero, so the over-reporting direction was the only one
   left that could find anything.**

## The census figures — `CRITERIA_VERSION 2026-10-16.b27r.1`, 26/26 fixtures

| shape | total | write-guarded | GET CALLER | SESSION | UNRESOLVED | SERVER-ONLY | UNCLASS |
|---|---|---|---|---|---|---|---|
| `A-helper` | 88 | 88 | 0 | 0 | 0 | 0 | 0 |
| `B-inline-503` | 70 | **22** | **35** | 1 | **0** | 10 | 2 |
| `C-200-empty` | 151 | 0 | **34** | 2 | **0** | 115 | 0 |
| `other` | 23 | 1 | 10 | 0 | **0** | 12 | 0 |

**b23 said class B was 13/33; b26 withdrew that to 32/9; it is 35/10. b23 said
"0 of the 151 interpolates a caller value"; b26 withdrew that to 16; it is 34.**
The **22 did not move** and the list is byte-identical to b26's. All seven rules
load-bearing by per-fixture ablation. **0 UNRESOLVED is not the third state
retired** — three fixtures still produce it.

## Deliverables

* `SAIRN-handoff-fourth-b27.md` — Drive `1JH_3OauqBYq8QxQhB23-ll_nBlNQWUTe`,
  `2026-10-16T11:43:30.220Z`, 21,315 bytes **read back through the Drive API**
* `SAIRN-report-fourth-b27.txt`, `SAIRN-digest-fourth-b27.txt`
* `docs/2026-10-16-fourth-b27-findings.md`
* `docs/2026-10-16-fourth-b27-branch-census-routed-to-cc.md` — full census
  source inline, and **the b26 routing doc now carries a SUPERSEDED banner**
  because its three-rule version reports a SESSION branch as CALLER
* `docs/defect-density-register.json` — one record, six contributing factors,
  the latent condition recorded as **`planned` with the owed action named**

## Next, shortest first

**cc:** install the census from the **b27** routing doc; make
`batch_manifest.py --check` resolve the paths inside evidence strings and report
COULD NOT RESOLVE per path; make `docs/tier-a-reviews.json` append-only.
**fourth/next:** the Tier A discharge write is one command once hank releases —
re-check with `sairn_claim.py` and read the runway from
`tier_a_review_gate.py --list`, not from any document.

**NO LIVE VERIFICATION.** Nothing ran against a real Supabase. No production row
read, no table touched, no deployment fetched. `tools/branch_census.py` still
does not exist — fifth batch, fifth scratchpad.
