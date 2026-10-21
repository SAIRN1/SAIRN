# SAIRN handoff — cody b47 (2026-10-21)

One item, explained and fixed. Nothing is half-finished.

## State
- Landed on origin/main, no force: `5195d38d6` (classifier fix + full-text file),
  `88885b711` (follow-up: that file only goes into a real git dir), claim `36d345842`.
  The follow-up push went through the fixed `push_retry.py --loop`, which landed on attempt 1.
- Files: `tools/push_retry.py`, and `docs/sairn-path-manifest.json`, where the cody override
  b47 replaces b46 with `tools/push_retry.py` only. No app code, no SQL, no live writes.
- Claim held: `platform` (b47). Release it at the start of the next batch, or let it expire.
- **One stray untracked file: `push_retry_last_refusal.txt` at the clone root.**
  My first selftest run wrote it (see below), and `rm` was denied by the harness.
  Michael: `! rm C:/Users/marsh/Documents/SAIRN-cody/push_retry_last_refusal.txt`
- Transcript: `C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cody\2d1bcf76-c842-40ed-b21d-9b20d98e7d45.jsonl`

## The b46 stops: the full message is not recoverable, but the cause is
**The full untruncated text no longer exists anywhere.** `--loop` printed 14 lines
plus up to 8 "remedy" lines. Its output files (scratchpad `pr46b.txt`, `pr46c.txt`)
hold only that excerpt, and nothing else captured git's stderr. Both excerpts show
gate NOTICES only (COPY-EXACTLY, CLAIM STATE, EXTRA SCRUTINY), and **no `Blocked:` line**.

**The gate did not deny either push.** Measured:
- The gate records every deny per (agent, tip) in `~/SAIRN-SESSION-LOCKS/push-retries/`,
  bumped in `_emit_collected()`, which every collected deny goes through. The two
  stopped tips were `0db1e0a6e` (16:10) and `aaedf44bd` (16:14), from the reflog.
  **Neither has a record**, and cody has no record at all after 15:34. The b46 ablation
  worktree's denies from the same minutes ARE recorded (`wt46b-*`, 16:07 and 16:10),
  so the recorder was working.

**Why `--loop` said "gate":** `_GATE_MARKERS` included the bare file name
`sairn_push_gate_hook.py`. **A passing gate prints that name.** Its EXTRA SCRUTINY
notice lists `[WEAKENING] tools/sairn_push_gate_hook.py` on any push that edits
the gate, and the b46 pushes did edit it. Reproduced: on commit `8aee7e758`, the
hook's stderr has the name 4 times, line 14 being that notice. The remote moved during
the ~85s hook run ("behind 14", then "behind 5", on a busy afternoon), so git rejected
with a race. `classify_refusal()` checks gate markers first, so the race was read as
"gate", and the loop STOPPED instead of fetch-rebase-retry.
**Inferred, not observed:** which race line it was (fetch-first or cannot-lock-ref).
That line is in the dropped part of the text. Both now classify the same way.
The direct preflight and hook runs exiting 0, and the plain push landing, are the same fact
seen from the other side.

## Fix (tools/push_retry.py)
1. `_GATE_MARKERS` keeps only text a DENY prints: `Blocked:`, the
   `(blocked by .githooks/pre-push ...)` trailer, `ESCALATING:`.
2. Three new selftest arms use the real notice lines: notice + lock race -> transient,
   notice + fetch-first -> transient, notice + real deny -> gate. All existing arms still
   pass, including "gate text wins over git's generic line". **ALL ARMS PASS.**
   **Ablation:** the old tuple returns `gate` on the b46 shape and the new one returns `transient`.
3. **The whole refusal is now kept** in `.git/push_retry_last_refusal.txt`, overwritten
   each attempt, and the excerpt prints its path. That is so the next stop is diagnosable.
   **My first version leaked:** the selftest stubs git, so `rev-parse --git-dir` came back
   `''`, the path resolved to the repo root, and the selftest wrote the stray file named
   above. It is now written only where `HEAD` exists. On a re-run, that file's mtime was
   unchanged and nothing new appeared.

## Open
- Michael: the one `rm` line above.
- A hook crash (a traceback naming the gate file, with no `Blocked:`) now classifies as
  `unknown` instead of `gate`. Both STOP, so behaviour is unchanged, but the label is different.
- cc: CHECK 5e review (routed). `tools/push_retry.py` is cc's too and should go in the same review.
- Carried: hank F2/F3; cc Tier A b31–b37; fourth defects 7/8.

## Exact next step
Release the `platform` claim. If Michael runs the `rm`, `git status` is clean.
