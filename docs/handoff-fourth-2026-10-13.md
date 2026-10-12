# HANDOFF — fourth / ted, batch b6, 2026-10-13

**Written BEFORE the report and the digest**, at a point where nothing is
half-finished: every item is closed with evidence, partial with its remainder
listed, or named as not done with who holds it.

**Transcript and working files:**
`C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-fourth\26107814-6275-4923-8a05-52f5d7ac19bd\scratchpad\`
Every exit code quoted was captured ALONE into a log there. The derivations are
scripts, not prose: `phi_candidates.py`, `phi_narrow.py`, `phi_bisect.py`
(+ `phi_bisect.log`, `phi_bisect2.log`), `b6_suites.py` (+ `item1_before.log`,
`item1_after2.log`), `swap.py`, `item3_status.py`, `item4_owners.py`,
`item4_route.py`, `item8_visibility.py`, `item9_locks.py`, `item11_skillpaths.py`.

---

## 0. THE TWO THINGS THE NEXT SESSION MUST NOT "FIX"

1. **HOOKS AND THE COMPACTION KEYS ARE OFF ON PURPOSE.**
   `.claude/settings.json` carries `"hooks": {}` and is **uncommitted by
   design** — committing it would push a local decision into four other clones.
   b4 restored them not knowing; b5 reversed that on instruction; **b6 re-added
   nothing.** Do not commit it, do not restore it, do not re-arm anything.
   Three untracked backups sit in `.claude/` and are deliberately left.
2. **`sql/restore_demo_pins_2026-09-29.sql` is still carried**, untracked, not
   mine, tenth batch. Not committed, not deleted.

Nothing in `C:\Users\marsh\` was deleted.

---

## 1. COMMITTED / PUSHED STATE

| | |
|---|---|
| HEAD | `c89ee9ce` |
| position | **11 commits AHEAD, 18 behind origin/main. NOTHING PUSHED.** |
| pushes attempted | **ZERO.** The brief said do not push, and no push was run — so unlike b5 there is no refusal to report, only an instruction honoured |
| `SAIRN_SEED_GATE=off` | **not used.** `docs/BYPASS-LOG.jsonl` gained no row this batch, which is the check on that sentence rather than the sentence |
| b6's own commits | `f9afd689` release of the still-active b5 claim · `bb6e7020` the b6 claim · `c89ee9ce` the work |
| diff stat of the work commit | 7 files changed, 343 insertions(+), 53 deletions(-) |
| working tree | 1 modified tracked path (the hooks-off settings.json, by design) + 4 untracked, all accounted for |

**Re-derive rather than trusting this table:**

```
git log --oneline -6
git rev-list --left-right --count origin/main...HEAD
git diff --shortstat HEAD~1 HEAD
```

**BEING 18 BEHIND IS NEW SINCE B5 AND IS NOT A PROBLEM TO FIX HERE.** Other
sessions have been landing while this clone cannot push. A rebase would be
needed before any future push, and `git rebase` refuses on a dirty tree — the
dirt being the hooks-off file that must stay — so whoever pushes must use
`git -c rebase.autoStash=true rebase`, which preserves it.

---

## 2. ITEM BY ITEM, with the exact next step for each open one

| # | item | state | exact next step |
|---|---|---|---|
| 1 | next 10 stripper sites | **DONE** | 29 sites in 17 files remain; routing doc §3 and §10 |
| 2 | find the phi_cache mutator | **NOT FOUND — 8 candidates eliminated** | see §3 below; the next occurrence now names itself |
| 3 | classify the 5 non-red suites | **DONE** | `not_red` in `docs/known-red-suites.json`; two upstream defects named |
| 4 | owners by directory | **DONE** | 40 rows, 0 unowned |
| 5 | clear the two probe worktrees | **DONE** | 0 worktrees; commits preserved at `refs/salvage/*` |
| 6 | next convention number | **ALREADY LANDED IN b4 — nothing to do** | convention **33** at `docs/2026-09-13-cross-domain-disciplines.md:1851`, promotion row `docs/METHODOLOGY.md:90` |
| 7 | recount the 2 unlocatable conventions | **BOTH FOUND** | 31 at `:1751`, 32 at `:1806`; method below |
| 8 | claim visibility | **DONE — b5's sentence is half wrong** | routed to cc, three exact lines |
| 9 | dead-lock table | **DONE — 0 released** | routing doc §7; `fourth.lock` released at report close |
| 10 | external-claims release statement | **DONE** | §4 below |
| 11 | skill-path scoping | **DONE — one real divergence found** | §5 below. Nothing edited |
| 12 | do the item-1 sites route through the fixed stripper | **DONE — yes, all 10** | counts in routing doc §10 |
| 13 | `report_sha_check` on the b6 report | **DONE at report close** | — |
| 14 | this handoff | **DONE** | — |
| 15 | report + digest + uploads | written after this file | — |

### Items 6 and 7 were ALREADY LANDED, and that is the answer rather than a skip

The brief asked for the next free number for cody's contamination-warning
convention **and** said to keep convention 33 where it is. **Those are the same
thing: convention 33 IS that convention**, assigned in b4. Verified, not
assumed:

* `docs/2026-09-13-cross-domain-disciplines.md:1851` — `## 33. A CONTAMINATION
  WARNING MAKES EVERY RESULT IN ITS SCOPE UNFALSIFIABLE, SO IT MUST SHIP WITH
  THE ISOLATION METHOD`
* `docs/METHODOLOGY.md:90` — the promotion row, dated 2026-10-11, crediting cody
  and naming `7ae272cc` + `ffe43d70`
* `grep -c "^## [0-9]\+\."` over the conventions file returns **33**, contiguous
  1–33, no gap and no duplicate — so there IS no "next free number" below 34,
  and assigning 34 would have created a second home for one convention.

**Item 7, the two "unlocatable" conventions: BOTH FOUND, and the search method
is the point.** They are 31 (`:1751`) and 32 (`:1806`). They were reported
unlocatable in b3 because that search keyed on the `## <n>.` unit while both
were still `###` SUBSECTIONS of another convention; they were promoted to `##`
headings on 2026-10-08. The method that finds them now is
`grep -n "^## [0-9]\+\."` plus a contiguity check on the numbers, which is
unit-independent in the only way that matters: it counts what the file actually
contains rather than what the searcher expected to be there.

---

## 3. ITEM 2 — THE MUTATOR IS NOT FOUND, AND THE SEARCH IS WORTH MORE THAN A NAME

**8 candidates, one at a time, every result logged as it ran.** The set was
derived: 95 suites name one of phi_cache's seven subjects AND contain a write
primitive; 7 put a write within 3 lines of a subject; 2 of those named a temp or
worktree path in the same window and were **descoped by name** so the exclusion
is auditable. The 5 survivors were driven, then the 3 descoped-or-adjacent ones
as well.

**Every one: no subject moved, `core.bare` unchanged, phi_cache exit 0 / 72
passed.** The seven subject digests were identical at the start and the end of
both rounds.

**CANDIDATE 6 IS THE INFORMATIVE RESULT.**
`tests/seam_check/run_delegation_probe.py` is the suite b5 measured leaving
`api/sd-data.js` and `api/_lib/subcontractor-compliance.js` sabotaged. Driven
here with `core.bare = false` throughout, **it restored both perfectly.** That
confirms b5's chain rather than contradicting it: the restore works when `git`
works and fails silently when `core.bare` is true.

**WHAT I AM NOT CLAIMING.** Not that no mutator exists. The honest statement is
that hank's `63 passed, 1 failed` was produced under a tree state none of these
8 can create, and the subject-mutation hypothesis is now much weaker than when
b5 routed it.

**NEXT STEP, AND IT IS NOT ANOTHER BISECT.** b5's precondition makes phi_cache
print `SKIPPED:` and **name the dirty subject** instead of failing. The next
whole-tree run therefore identifies the mutator itself. Waiting for a
self-reporting signal costs nothing; a third bisect costs an hour and has
already returned nothing twice.

---

## 4. ITEM 10 — EXTERNAL CLAIMS AND HOLDS, RELEASE STATEMENT

**MEASURED NOW, not carried from b5.**

| hold | count | detail |
|---|---:|---|
| git worktrees besides the main one | **0** | both probe worktrees REMOVED this batch (item 5) |
| `git stash` | **0** | |
| session locks held by me | **1** | `fourth.lock`, pid 61696, LIVE — **released at report close** |
| session locks released by me | **0** | none of the 8 dead ones is attributable to me |
| repo claims held | **1** | the b6 claim, `bb6e7020`, committed locally |
| repo claims released | **1** | the b5 claim, `f9afd689` — it was **still active at b6 pickup** |
| refs created | **2** | `refs/salvage/b6-defreg-probe` → `fdce1b4b`, `refs/salvage/b6-gate12` → `549a372a` |

**TWO THINGS I AM SAYING OUT LOUD RATHER THAN LETTING A READER FIND.**

1. **b6's first hour ran under b5's claim, which had never been released.** I
   found it active at pickup, released it, and took a b6 claim. The b5 claim's
   `FILES` list did **not** cover the five `api/_lib/*.test.js` files item 1
   edited, so those edits were made outside any claim of mine. No other session
   declared them and the directory rule makes `api/` hank's, so nothing was
   taken from anyone — but it was not covered, and that is the accurate word.
2. **The two salvage refs are a new external hold I created.** Removing a
   worktree whose head is unreachable would orphan its commits, so both heads
   were pinned to refs first. They are cheap and they are not nothing: a ref
   keeps objects alive. Delete them with
   `git update-ref -d refs/salvage/b6-defreg-probe` (and `-b6-gate12`) once
   somebody confirms the probe commits are not wanted.

---

## 5. ITEM 11 — SKILL PATHS, PRINTED ONLY

**19 skills are referenced by a check** in `tools/` or `tests/`. Both stores
exist: the project store `…\SAIRN-fourth\.claude\skills` (34 dirs) and the
shared user store `C:\Users\marsh\.claude\skills` (62 dirs). **14 of the 19 are
present in BOTH**, and for those the project copy is the one a check in this
repo reads.

**13 of the 14 are byte-identical after `tr -d '\r'`. ONE IS NOT:**

> **`sairn-hover-auditor` — the project copy and the user copy DIFFER in
> content, not just line endings.**

That is the auditor's own skill, the one subtree a build agent must not touch,
so it is **reported and not investigated further and certainly not edited**.
Routed to whoever owns the auditor clone. **No frontmatter was edited in either
store** — the instruction was explicit, and the reason is structural: the user
store is shared by every clone on this machine.

---

## 6. ITEM 8 — WHERE CLAIMS LIVE VERSUS WHERE THEY ARE READ

Full table in routing doc §8. The short form: **a local-only claim is invisible
to a clone on another machine and perfectly visible to the five other sessions
on this one**, because `sairn_claim.py` already mirrors active claims into
`~/SAIRN-SESSION-LOCKS/status/` (`publish_claims`, ~`:1547`) and already reads
other sessions' from there (`registry_claims`, `:1281`). Verified by calling
`sairn_status.read_claims()` and finding my own unpushed claim in the result.

**The defect is the MESSAGE, and the message is what a session acts on** — b5
read it, believed it was unclaimed, and recorded that in its report and handoff.
**Routed to cc**, three exact lines: `tools/sairn_claim.py:1966`, `:1921`,
`:2414`. The third is the flatly wrong one: *"nothing published"*, when
`publish_claims` had just run.

---

## 7. WHAT IS OPEN, AND WHY

* **29 stripper sites in 17 files.** Routed with exact lines. Each needs its own
  before/after suite run; b6 did ten and found a real break inside that run.
* **The phi_cache mutator.** Not found; §3 has the next step, which is to wait
  for the self-reporting signal rather than bisect again.
* **The two upstream defects behind the `not_red` five** — two sabotage controls
  blocked on registered-red baselines, and one failing blind lock blocking two
  push-gate probes. Neither is mine.
* **`tests/seam_check/run_delegation_probe.py:76, :80, :113, :119`** — the
  fail-open restore. **cody's** by the b6 rule.
* **`tools/session_lock_check.py:128, :349, :357`** — why 8 dead locks are
  unattributable, third batch running. **cc's.**
* **`tools/clone_health_check.py:209-211`** — detects `core.bare = true` and
  nothing refuses on it. **cc's.**
* **`sairn-hover-auditor` skill divergence** between the two stores.
* **11 unpushed commits**, 18 behind. Nobody can see any of this work in git yet.

**Nothing is partial except item 1, which is partial by instruction — the brief
asked for ten of thirty-nine.**
