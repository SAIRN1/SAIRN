# CC batch 15 — diagnostics (items 9–13)

**2026-10-07 (cc), at `f97831ff`.** Every number is program output captured at
that HEAD. Token figures are **bytes ÷ 3.7**, which is an estimate and is labelled
as one everywhere it appears; byte counts are exact.

---

## ITEM 9 — `/context`: I CANNOT RUN IT, and here is everything I can measure instead

**`/context` is a client-side Claude Code command, not a tool and not a skill.** A
model turn cannot invoke it; only Michael typing `/context` produces that
breakdown. Reporting an estimate as if it were that output is exactly the thing
this batch keeps fixing, so I am not going to.

**Michael: please type `/context` and paste it.** What follows is the part that is
measurable from inside the session, which is a minority of the window.

### Measurable — injected at session start

| what | bytes | ~tokens |
|---|---|---|
| `CLAUDE.md` (project primer) | **17,618** | ~4,762 |
| `~/.claude/CLAUDE.md` (global primer) | **1,345** | ~364 |
| `MEMORY.md` (auto-memory **index**) | **3,180** | ~859 |
| **subtotal** | **22,143** | **~5,985** |

The memory **bodies** total 39,783 bytes (~10,752 tokens) across 15 files, but
they are recalled on demand rather than injected, so they are not in that
subtotal. They are the thing that grows fastest now that the cadence is 1 — see
item 13.

### NOT measurable from inside, and these are the big four

1. **The MCP tool-definition block.** This session has the full Vercel surface
   (~250 tools), Gmail, Drive, Docs, Chrome, plus the built-ins. Most are
   deferred — I see names only until I `ToolSearch` them — but the *name list
   itself* is in the prompt, and it is long.
2. **The deferred-tool name list.** ~300 names.
3. **The harness system prompt**, including the output style, the environment
   block, the skills listing (62 names + one-line descriptions each), the agent
   listing (7), and the hook text.
4. **The conversation transcript** — by far the largest and the only one that
   grows. Batch 14 ran to a compaction; batch 15 has not.

### What I can say with certainty about what is eating it

**Not the primers.** `CLAUDE.md` at 17.6 KB is ~0.5% of a 1M window. The
standing documents are the opposite story, and this is the finding:

| document | bytes | ~tokens | whole-file read is |
|---|---|---|---|
| `docs/SAIRN-OPEN-WORK-INDEX.md` | **2,379,765** | **~643,180** | **64% of a 1M window** |
| `docs/CRITICALITY-TIERS.md` | **485,668** | ~131,262 | 13% |
| `docs/TOOLING-INVENTORY.md` | **348,026** | ~94,061 | 9% |
| `docs/2026-09-13-cross-domain-disciplines.md` | 75,171 | ~20,316 | 2% |
| `docs/SAIRN-PROCESS-RULES.md` | 52,480 | ~14,184 | 1.4% |
| `docs/METHODOLOGY.md` | 20,060 | ~5,422 | 0.5% |
| **all six** | **3,361,170** | **~908,424** | **would not fit** |

**One `Read` of the open-work index would consume roughly two thirds of the
window.** CLAUDE.md tells a fresh session to consult it; nothing tells the session
not to read it whole. That is the real context risk in this repo and it is
item 12's discipline applied to documents rather than apps.

---

## ITEM 10 — `CLAUDE.md` size

    CLAUDE.md                        17,618 bytes   308 lines   2,614 words   ~4,762 tokens
    ~/.claude/CLAUDE.md               1,345 bytes    12 lines     190 words     ~364 tokens

Measured with `os.path.getsize` and a line count, not estimated. **It is not a
problem** — together they are under 1% of the window. The six standing documents
above are 190× the project primer.

---

## ITEM 11 — run capture: ALREADY FILTERED, and now it has a fixed idiom

**Already filtered, and it was filtered before this item asked.** The pattern used
throughout batches 14 and 15:

    CMD > /tmp/out 2>&1 ; echo "EXIT=$?"      # raw to a FILE, exit code read ALONE
    grep -E "FAIL|^R[1-4] |^read |finding" /tmp/out | head -20

Two properties, both load-bearing on this platform:

* **The exit code is read on its own line, from the program, never from a
  pipeline.** `tools/exit_status_attributable.py` warns on every command that
  pipes a tool into a text filter, because `head` exits 0 for "I ran" and says
  nothing about the program before it. Capture-then-filter is the shape that
  satisfies that; `CMD | grep` is the shape that does not.
* **Raw is kept, on disk, and only a slice is read into context.** Nothing is
  discarded — `/tmp/out` is there when a verdict needs re-reading.

### What changed

The pattern was a habit with no fixed form, so the filter was improvised per
command and twice I read more than I needed (`cat` on a 31-line arm list, `cat` on
a 24-line reseat report — small, but unfiltered). **The idiom is now fixed:**

    CMD > /tmp/out 2>&1 ; echo "EXIT=$?"
    grep -nE "FAIL|ERROR|Traceback|COULD NOT|DRIFT|^[0-9]+ (finding|arm)|passed|failed" /tmp/out | head -20

### The honest limit

**When a command fails, the harness surfaces its stderr in full regardless of my
redirection.** The push-gate refusals in batch 14 arrived as complete 40-line
blocks because the gate exits non-zero — I did not read them in, they were handed
to me. No filter I write changes that, and pretending otherwise would be the
false claim. It is also usually what I want from a gate.

---

## ITEM 12 — large single-file reads: COMPLIANT, and the measurement is the point

**18 of 22 app files are over 1,000 lines.** Whole-file reads are not
*discouraged* here, they are **impossible**:

| file | bytes | lines | ~tokens |
|---|---|---|---|
| `stonedesk.html` | 2,755,227 | **43,946** | **~744,656** |
| `sairncode.html` | 940,045 | 13,048 | ~254,066 |
| `sairnvet.html` | 864,521 | 10,846 | ~233,654 |
| `sairnbuild.html` | 592,739 | 9,485 | ~160,200 |
| `sairnlaw.html` | 462,744 | 7,334 | ~125,066 |
| `sairnfreedom.html` | 454,669 | 7,699 | ~122,884 |
| `sairndental.html` | 433,203 | 6,953 | ~117,082 |
| **`sairnbiz.html`** | **416,986** | **6,321** | **~112,699** |
| `sairnsenior.html` | 382,000 | 6,165 | ~103,243 |
| `sairnroofing.html` | 369,469 | 6,283 | ~99,856 |
| `sairnlegacy.html` | 347,995 | 5,474 | ~94,053 |
| `sairngrounds.html` | 343,066 | 5,408 | ~92,721 |
| `sairncare.html` | 322,378 | 5,068 | ~87,129 |
| `sairndesign.html` | 280,825 | 4,477 | ~75,899 |
| `sairnscape.html` | 259,355 | 4,274 | ~70,096 |
| `sairnmechanical.html` | 229,246 | 3,549 | ~61,958 |
| `sairncash.html` | 132,627 | 2,242 | ~35,845 |
| `stonedesk-hr.html` | 99,830 | 1,447 | ~26,981 |
| *(4 files under 1,000 lines)* | | | |
| **total** | **9,754,455** | **151,326** | **~2,636,339** |

**`stonedesk.html` alone is ~745k tokens** — one read is three quarters of the
window. The 22 files together are **2.6× a 1M window**.

### Nothing to fix: no app file was read whole in batch 14 or 15

Every app-file access in both batches was `grep`, `git show --stat`, a `sed`
line range, or a `Read` with `offset`/`limit`. The largest whole-file `Read` I
made was `tools/role_gate_mc_config.py` — 278 lines — and even that was taken in
two ranges. No `.html` was opened by `Read` or `cat` at all.

**The real exposure is DOCUMENTS, not apps** (item 9): `SAIRN-OPEN-WORK-INDEX.md`
at ~643k tokens is comparable to `stonedesk.html`, it is prose so there is no
`node --check` reflex guarding it, and `CLAUDE.md` actively points a fresh session
at it. Read it with `grep` and a line range, the same as an app.

---

## ITEM 13 — proactive compaction between queue items

**Adopted.** Compaction happens between items, not when the window forces it.
Batch 14 compacted *mid-item-1* and lost the single most consequential fact in
the batch — that its own claim had been committed and never pushed — which took
a rebase and a divergence to rediscover.

### The preserve-list, stated BEFORE each compaction

Four things, in this order, every time:

1. **Claims held** — subject, and the files DECLARED in the claim, separated from
   files merely mentioned. Plus: *do not re-take*
   `sairn_push_gate_hook.py`, `report_only_checks.py`, `doc_sha_reseat.py`,
   `tool-owner-map.json`.
2. **Committed SHA and push state** — `git rev-parse --short HEAD`, and
   `origin/main...HEAD` ahead/behind with the time of the fetch that produced it.
   A SHA with no push state is the batch-14 failure exactly.
3. **The exact next item**, as a command rather than a description.
4. **What is BLOCKED and on whom** — item 5 on `SAIRNLAW_EMP`/`SAIRNLAW_PIN`
   from Michael; item 6 on cody.

That list is not written fresh each time: it **is**
`memory/batch15-progress.md`, rewritten after every item under the cadence-1 rule
([[batch-checkpoint-cadence]]). The checkpoint file is the preserve-list, so a
compaction cannot land between "I decided what to preserve" and "I wrote it
down".

### The cost, stated

Compacting proactively throws away context that is still useful — the reasoning
behind a decision two items back is gone, and only the conclusion in the
checkpoint survives. That is the trade and it is the right one: a lost conclusion
is re-derivable from the commit, and a lost *claim state* is what sends a session
into a rebase it did not need.
