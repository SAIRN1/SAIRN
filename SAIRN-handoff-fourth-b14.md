# HANDOFF — fourth / ted, batch b14, 2026-10-14

**Written BEFORE the report**, at a point where nothing is half-finished: all
six items are committed and pushed in one commit, `HEAD == origin/main`, the
working tree is clean, no rebase or stash is in progress.

**EVERY FIGURE NAMES THE COMMAND THAT PRODUCED IT** (b11's rule). **Three
decisions in this batch were made by chat rather than asked of Michael**, and
§1 says which and why.

**Transcript and working files:**
`C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-fourth\240036a6-0d02-441d-a22d-73ed022c11a3\scratchpad\`
New this batch: `priority25_b14.py`, `register_rows_b14.py`.
Logs: `hook_b14.log`, `triage_b14.log`, `ownermap_b14.log`, `flagA_b14.log`,
`flagB_b14.log`, `weakening_b14.log`, `unfixtured_b14.log`,
`priority25_b14.log`, `priority25_tools_b14.log`, `cites_b14.log`,
`locks_b14.log`, `register_b14.log`, `push_b14.log`, `landed_b14.log`.

---

## 0. COMMITTED / PUSHED STATE

| | | command |
|---|---|---|
| HEAD | `73b5577e` | `git -C <repo> rev-parse HEAD` |
| `origin/main` | `73b5577e` | `git -C <repo> rev-parse origin/main` |
| behind / ahead | **0 / 0** | `git rev-list --left-right --count origin/main...HEAD` |
| working tree | clean | `git status --porcelain` (empty) |
| the b14 work commit | `dffabd95` → `73b5577e` after rebase, 6 files | `git log origin/main --oneline -1` |
| push forced? | **NO** | one rebase, then `225d0eb0..73b5577e` |
| `SAIRN_SEED_GATE=off` | **not used**, any form | — |
| `.claude/settings.json` | **not edited, not committed** | `git log --format=%h HEAD --not 6604d206 -- .claude/settings.json` → empty |
| hooks | **1 group, 1 entry — untouched, and cc's b8 is removing it** | `json.load(...)['hooks']` |
| files written outside `docs/` | **0** (plus my own three root deliverables) | by instruction |

**`73b5577e` IS THE STATE AT FINALISATION OF THIS HANDOFF** — the report, the
digest and the claim release land after it. **Re-derive HEAD rather than quoting
this table.**

---

## 1. ITEM BY ITEM

| # | item | state | exact next step |
|---|---|---|---|
| 1 | AI spec §7 decided, questions removed, routed | **DONE** | **hank + cody** act on §7's routing; one collision to resolve (§3.1) |
| 2 | triage the 13 hook-manifest findings | **DONE — 13 stale record, 0 real drift** | **cc runs `--regenerate` in cc's clone** (§3.2) |
| 3 | review the two open `[WEAKENING]` flags | **DONE — both signed off false** | **whoever may write `docs/scrutiny-flags.json`** marks the two rows reviewed, citing my review; one blind spot routed to **hank** |
| 4 | the first 25 fixtures, prioritised | **DONE — 21 `tools/` + 4 `tests/`** | **cc** rows 2–21, **cody** rows 1/7/14/18/19/22–25, **fourth** row 11 |
| 5 | three findings routed + recorded once each | **DONE — 4 rulings in the register, idempotent** | **cc answers each half of `DECIDE_OR_NOT_PROMOTED`** |
| 6 | push without force, confirm landed | **DONE — `225d0eb0..73b5577e`, 0/0** | nothing |
| — | this handoff, before the report | **DONE** | — |

### Item 1 — three decisions taken by chat, and the reason they were not Michael's

**7.1 owner acceptance is NOT a runtime gate** — a gate turns a paperwork gap
into an outage across every seat, and the first support call makes somebody
disable it, which removes the acceptance *and* the gate.
**7.2 SAIRNdental and SAIRNsenior ARE clinical / high-risk** — the old wording
("category 2 *if* it suggests clinical coding") is a per-output judgement made
at speed by whoever is on shift. Cost of being wrong this way: one extra button.
The other way: an unreviewed clinical suggestion in a document.
**7.3 notice version is `2026-11`**, bumped in the same commit as the lawyer's
final text. T4 is the test that proves a late bump re-prompts once without
destroying the earlier ack.

**All three are technical/product calls with a safe default and a cheap
reversal; none touches the customer wording.** Both `[DRAFT — LAWYER]` strings
stay placeholders and are **the only thing in that document still waiting on
anybody.**

---

## 2. CLAIMS, LOCKS AND EXTERNAL HOLDS

| hold | count | detail | command |
|---|---:|---|---|
| repo claims held | **1** | b14, published on `origin/main`; release after the report and digest are up | `sairn_claim.py list` |
| **my claim reads DEAD, third batch running** | — | `CLAUDE_PID 53204 no longer exists`. **Now recorded as a register ruling** (`2026-10-14-claim-reads-dead-stale-heartbeat`) instead of only a handoff paragraph | `sairn_claim.py own` |
| session locks held | **1** | `fourth.lock`, 25.7h, `claude_pid 53204` — the same dead PID. **14 locks total, 7 over 160h**, oldest 354.3h | `ls ~/SAIRN-SESSION-LOCKS/*.lock` |
| locks released / removed by me | **0** | `rm` is denied and I did **not** route around it this batch | — |
| worktrees besides main | **4** | **none mine**, unchanged since b11 | `git worktree list` |
| `git stash` | **0** | none taken | `git stash list` |
| `refs/salvage/*` | **0** | | `git for-each-ref refs/salvage/` |

**Nothing was written outside `docs/`** plus my own three root deliverables.
**One unintended write happened and was reverted:** `tools/tool_owner_map.py`
writes `docs/tool-owner-map.json` on a bare run, which I needed for owner
derivation; I reverted it with `git checkout --` and read the **committed**
version instead. `git status --porcelain` is empty, and the owner column in
item 4 comes from `git show HEAD:docs/tool-owner-map.json`.

---

## 3. WHAT IS OPEN, AND WHY — owner and exact next step

### 3.1 hank and cody — the AI spec, and ONE COLLISION TO RESOLVE BEFORE BOTH SHIP

**hank's live b9 claim is already building this in `api/`** —
`ai_source` + `ai_approved_by` + `ai_approved_at` on AI-sourced records, a
server refusal for high-risk leaving draft unapproved, and a per-employee
one-time notice ack, with `api/_lib/ai-safeguards.js` and `api/ai-notice.js` in
its declared FILES. **§7.4 of the spec records where my spec yields to that
rather than demanding rework.**

**THE COLLISION, and it is the one thing worth stopping for:** §2.1/§3.2 put the
notice ack on the existing `*_employee_auth` row and the action on the existing
`*-auth.js` endpoint; hank is building a separate `api/ai-notice.js`. **If both
land, there are two ack records for one fact** — and an employee acked in one
place reads as un-acked in the other, which is the repeat popup Michael's
decision exists to prevent. **Exact next step: hank picks one store, and
whichever loses gets deleted rather than left as a second writer.**

**cody's next step is unchanged by the collision:** T9 must exclude
`sairndental` and `sairnsenior`; T10 gains the negative arm; T4 goes from
hypothetical to load-bearing; T7/T8/T14 gain arms for the two new high-risk
surfaces.

### 3.2 cc — one command closes thirteen findings, and it must not be mine

```
python tools/hook_integrity_check.py --regenerate     # in cc's clone, then commit
```

**All 13 are stale record. Zero are real drift.** Measured:
`docs/hook-manifest.json` last regenerated `e8bfdf0d 2026-10-07T07:37:05`;
every changed subject's last commit postdates it; all four NOT-IN-MANIFEST
tools were **created** after it; `git status --porcelain -- tools/ .githooks/`
is empty, so nothing is a working-tree edit.

**Four of the thirteen are mine** (`commit_tool_entry_check.py`,
`report_sha_check.py`, `temp_state_leak_check.py`, and the `.githooks/pre-commit`
change from my b9), which is exactly why I must not regenerate the expectation
file they are then measured against.

**One interaction cc must know about:** cc's own live b8 claim item 1 is
*"remove the tracked SessionStart:compact hook group from eb53e267"*. If that
lands, findings 3 and 13 change shape — the hook goes, `compaction_brief.py`
may stay, and the manifest still needs regenerating either way. **Regenerate
after that removal, not before, or the manifest records a hook that is about to
be deleted.**

### 3.3 The two `[WEAKENING]` flags — signed off, and the rows are not mine to mark

Both are **false positives**, checked at `file:line` rather than agreed with:

* `api/role-vocabulary-agreement.test.js:320-333` — the matched line is the
  **title of a negative control**; `deepStrictEqual` against a one-element list
  refuses any new app.
* `api/sd-data-leg-bookings-toctou.test.js:149` is the harness's fetch stub (the
  real query is `api/_lib/auth.js:1125`); `:358-368` asserts the exemption **by
  call count**, which a 200 cannot do. **And the half nobody had checked:** the
  read side agrees — `api/sd-data.js:14967` skips the gate for `Cancelled` and
  `:14987` ignores `Cancelled` rows, so the row that dodged the check is
  invisible to every later check. Sections 4 and 5 of the suite assert both
  sides.

**Exact next step:** whoever may write `docs/scrutiny-flags.json` (the push gate
and hank's batch write it) marks those two rows reviewed, citing
`docs/2026-10-14-fourth-b14-weakening-review.md`. **I did not edit that file** —
a reviewer clearing flags in the file he is clearing them from is the shape I
just signed off two findings against. **One blind spot routed to hank** for that
file's own `blind_spots` list: *an allowlist under `deepStrictEqual` and one
under `includes()` are the same shape and opposite directions.*

### 3.4 The fixture backlog — 616, with the first 25 named

* **cc:** rows 2–21 of `docs/2026-10-14-fourth-b14-fixture-priority-25.md`.
  **Row 4 first, then row 2, then row 12** — the licence-recoverability guard, the
  fail-open scanner, the Tier A bypass check. **13 of the 21 `tools/` entries
  have no recorded owner at all**, which is a finding, not a routing
  convenience: either claim them or record them as platform-owned.
* **cody:** rows 22–25 (guard-of-a-guard probes; **row 22 first**, its docstring
  already claims a proven escape exists) plus rows 1, 7, 14, 18, 19.
* **fourth (me):** **row 11, `tools/text_gate_literal_sweep.py`** — a gate whose
  text match is satisfied by a token inside a comment, which is the exact defect
  my own b13 bad-input fixture shipped with. **Open, mine, not written: this
  batch writes under `docs/` only.**

### 3.5 Still open from earlier batches, unchanged

* **`tools/fixture_lock_check.py`** — specified in b13, built by nobody. Without
  it the 616 grows.
* **`docs/by-design-register.json` now has 4 rows and still no reader.** The
  validator spec (b12) is built by nobody. **Four rulings with no `--check` is
  four times the exposure one row had.**
* **The `compact` matcher has still never been observed firing** — and cc's b8
  may remove it before anybody sees it fire, which closes the question by
  deletion rather than by evidence.
* **b13's scratchpad litter is still there.** `rm` is denied; I did not use the
  python route this batch, by instruction. The register ruling
  `2026-10-14-rm-deny-bypassed-by-python` is the decision that unblocks it.

---

## 4. THE ONE THING THE NEXT SESSION MUST NOT DO

**Do not clean the scratchpad with a python `os.remove`.** It works, it is
denied by `.claude/settings.json:85-89`, the file's own note at `:185` already
calls it a known hole, **and b13 used it.** It is now register ruling
`2026-10-14-rm-deny-bypassed-by-python` awaiting cc's decision. Until that
decision lands, **leave the litter and say so** — which is what this handoff
does.

---

## 5. FINAL STEPS STILL TO RUN AFTER THIS HANDOFF

Recorded here because a handoff written before the report has to say what is
still ahead of it:

1. `python tools/drive_upload_verify.py --agent fourth --batch b14` — upload and
   prove. **`G:\My Drive` and `G:\My Drive\SAIRN-status` both exist**, so the
   mount is present; a `COULD NOT RUN` would mean it vanished.
2. `python tools/batch_manifest.py --close --agent fourth --batch b14`.
   **EXPECTED TO REFUSE:** only `docs/batch-manifest-cc-b6.json` and
   `-cc-b7.json` exist — **no manifest was ever written for fourth b14**, and
   the tool's design is that **chat writes the ids**. I will run it and report
   what it says rather than writing my own manifest to make it pass.
3. The report and digest, then the same upload-and-verify for both.
4. Release the b14 claim.

**Nothing is partial.** Every open item above is another session's, or mine and
named as mine, or a measurement with its command stated.
