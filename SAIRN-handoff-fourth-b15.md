# HANDOFF — fourth / ted, batch b15, 2026-10-14

**Written BEFORE the report**, at a point where nothing is half-finished: all
six items are committed and pushed in one commit, `HEAD == origin/main`, the
working tree is clean, no rebase or stash in progress.

**EVERY FIGURE NAMES THE COMMAND THAT PRODUCED IT** (b11's rule).

**Transcript and working files:**
`C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-fourth\240036a6-0d02-441d-a22d-73ed022c11a3\scratchpad\`
New this batch: `bands_b15.py`, `priority_26_50_b15.py`.
Logs: `manifest_new_b15.log`, `manifest_set_b14.log`, `manifest_close_b14b.log`
(the crash), `manifest_close_b14c.log` (the pass), `manifest_set_b15.log`,
`resources_b15.log`, `tiers_b15.log`, `bands_b15.log`, `roles_b15.log`,
`rolegates_b15.log`, `svgate_b15.log`, `item2_scan.log`,
`priority_26_50_b15.log`, `subjects_26_50.log`, `row11_run.log`,
`push_b15.log`, `landed_b15.log`.

---

## 0. COMMITTED / PUSHED STATE

| | | command |
|---|---|---|
| HEAD | `83b5a7e9` | `git -C <repo> rev-parse HEAD` |
| `origin/main` | `83b5a7e9` | `git -C <repo> rev-parse origin/main` |
| behind / ahead | **0 / 0** | `git rev-list --left-right --count origin/main...HEAD` |
| working tree | clean | `git status --porcelain` (empty) |
| the b15 work commit | `ef8f55d0` → `83b5a7e9` after rebase, 9 files | `git log origin/main --oneline -1` |
| push forced? | **NO** | one rebase, then `0b7a7a0d..83b5a7e9` |
| `SAIRN_SEED_GATE=off` | **not used**, any form | — |
| `.claude/settings.json` | **not edited, not committed** | `git log --format=%h HEAD --not 2e3fe02f -- .claude/settings.json` → empty |
| files written outside `docs/` | **0** (plus my three root deliverables) | by instruction |
| b14 manifest | **CLOSED** | `batch_manifest.py --close --agent fourth --batch b14` → exit 0 |
| b15 manifest | 6 of 6 `done`, close pending the three deliverables | `batch_manifest.py --check` |

**`83b5a7e9` IS THE STATE AT FINALISATION OF THIS HANDOFF** — the report, the
digest, the b15 close and the claim release all land after it. **Re-derive
HEAD rather than quoting this table.**

---

## 1. ITEM BY ITEM

| # | item | state | exact next step |
|---|---|---|---|
| 1 | ack store decided; loser routed | **DONE** | **hank deletes `api/ai-notice.js` and migrates** (§3.1) |
| 2 | three role-matrix specs, 98 resources | **DONE** | **hank implements; 10 `[CONFIRM]`s need a practitioner's answer** (§3.2) |
| 3 | both manifests written; b14 closed | **DONE — and `--close` crashes without an env var** (§3.3) | **cc fixes `tools/batch_manifest.py:386`** |
| 4 | fixture rows 26–50 + row 11 build spec | **DONE** | **cody rows 26–50; cc builds row 11's lock, then triages 82→111** (§3.4) |
| 5 | wording package for counsel | **DONE — all `[DRAFT — LAWYER]`** | **counsel answers the five questions in §7 of that document** |
| 6 | push without force | **DONE — `0b7a7a0d..83b5a7e9`, 0/0** | nothing |
| — | this handoff, before the report | **DONE** | — |

### The order I worked in, and why it is not 1→6

**Item 3 came first.** Its own instruction is *"start every future batch by
writing its manifest first"*, and a batch that writes its manifest at step 3
has not followed the rule it is setting. So: claim → `--new fourth b15` →
`--new fourth b14` → close b14 → items 1, 2, 4, 5 → push. **The numbered order
is preserved in the manifest and in the report; only the manifest creation
moved, and it moved because item 3 says to.**

---

## 2. CLAIMS, LOCKS AND EXTERNAL HOLDS

| hold | count | detail | command |
|---|---:|---|---|
| repo claims held | **1** | b15, published on `origin/main`; release after the report and digest are up | `sairn_claim.py list` |
| session locks held | **1** | `fourth.lock`, still carrying the dead `claude_pid 53204`; **14 locks total, 7 over 160h** — register ruling `2026-10-14-orphaned-session-locks` | `ls ~/SAIRN-SESSION-LOCKS/*.lock` |
| locks removed by me | **0** | `rm` is denied and I did **not** route around it | — |
| worktrees besides main | **4** | **none mine**, unchanged since b11 | `git worktree list` |
| `git stash` | **0** | none taken | `git stash list` |

**Nothing was written outside `docs/`** plus my three root deliverables.
**No unintended writes this batch:** `scratchpad/bands_b15.py` and
`priority_26_50_b15.py` are read-only, and I did **not** re-run
`tools/tool_owner_map.py` (which writes `docs/tool-owner-map.json` on a bare
run, as b14 reported) — owners came from
`git show HEAD:docs/tool-owner-map.json` instead.

---

## 3. WHAT IS OPEN, AND WHY

### 3.1 hank — delete `api/ai-notice.js` and migrate the ack

`docs/2026-10-14-ai-safeguards-spec.md` §7.5. **The winner is the two
`*_employee_auth` columns** (`ai_notice_version`, `ai_notice_acked_at`), because
Michael's decision is that the ack is *"stored under that employee's login"*
and **the credential row is the login**.

**Exact next step, in this order:**

1. Delete `api/ai-notice.js` and its route registration.
2. If it has already shipped a table: copy rows into the credential columns
   matched on `(license_hash, employee_id)`, **then drop the table in a LATER
   commit** — a drop in the same commit leaves nothing to re-run the copy from.
3. **A row that matches no credential row is a FINDING, printed, not dropped.**
4. `CURRENT_NOTICE_VERSION` stays one constant in `api/_lib/ai-safeguards.js`.
5. **cody adds one arm:** `api/ai-notice.js` is gone and nothing imports it.

**Not decided by §7.5:** hank's `ai_source` / `ai_approved_by` /
`ai_approved_at` record-level columns, which §7.4 already adopted.

### 3.2 hank — the three role matrices, and the 10 questions only a practitioner can answer

| app | resources | gates today | the ask |
|---|---:|---|---|
| **sairnlegacy** | **36** (20 tier A) | **0** | 7 roles (3 existing + 4–5 new), `staff` deprecated to the narrowest band, 10 negative controls |
| **sairnvet** | **42** (30 tier A) | **1** — `PRESCRIBER_ROLES`, `api/sv-auth.js:118` | gates for the other 41; vocabulary already correct; 12 negative controls |
| **sairnlaw** | **20** (20 tier A, 0 tier B) | **1** — `LAW_RECONCILE_ROLES`, `api/sd-data.js:16882` | gates for the other 19, **plus two missing jobs**: `bookkeeper` and `staff`; 12 negative controls |

**THE SHARPEST OPEN ITEM IN THIS BATCH:** SAIRNlegacy's `staff` role. Every
employee who is not the owner or a director currently reads and writes
`leg_deathrecords`, `leg_cremations`, `leg_custodylog` and `leg_preneed`. **The
migration must map `staff` to the narrowest band, not to `arranger`** — the
latter grants 15 money resources to everyone who had a login yesterday.

**The `[CONFIRM]`s are not stylistic.** They include whether an embalmer needs
a separate licensed tier, whether a cremation authorisation needs two named
people, whether a veterinary technician may record a controlled-substance
administration, and whether a paralegal may prepare a trust disbursement.
**Three of those are state law or bar rules, not preferences**, and each is
marked where it bites.

### 3.3 cc — `tools/batch_manifest.py:386` crashes `--close` on a non-ASCII first line

```
CMD python tools/batch_manifest.py --close --agent fourth --batch b14
    exit 1, UnicodeEncodeError: 'charmap' codec can't encode '\ufffd'
    at tools/batch_manifest.py:386  print('  | %s' % line)
CMD PYTHONIOENCODING=utf-8 python tools/batch_manifest.py --close --agent fourth --batch b14
    exit 0, CLOSED: fourth b14, 3 deliverable(s) verified
```

`cmd_close` echoes `drive_upload_verify`'s output, and that output **quotes
each deliverable's first line**. My handoffs begin `# HANDOFF — fourth` with an
em dash, so on a cp1252 stdout the echo raises and **`--close` traceback-exits
on any batch whose handoff title is not pure ASCII**.

**Exact next step for cc:** make that echo encoding-safe — write through a
stream reconfigured to UTF-8, or replace unencodable characters at the print.
**Not a wording fix:** telling six agents to keep their titles ASCII is a rule
nobody will remember, and the tool is the single place.

**What I did instead of editing it:** set `PYTHONIOENCODING=utf-8` on the
command. That is an environment variable, not a code change and not a route
around a permission rule, and it is recorded in the commit message.

### 3.4 cody and cc — fixtures

* **cody: rows 26–50** (`docs/2026-10-14-fourth-b15-fixture-priority-26-50.md`),
  21 of the 25 cody's. **Row 39 first** — the missing-checker probe is the
  fail-closed rule's own control, and if it has degraded every other push-gate
  verdict is worth less. Then rows 46 and 40 (the crediting rules that decide
  whether other gates get credited), then 47 with row 1 (one subject, two
  sides), then 28/29/30 (one shared helper, three apps).
* **cc: row 11's lock**
  (`docs/2026-10-14-fourth-b15-text-gate-fixture-spec-routed-to-cc.md`), 14
  synthetic arms plus 3 decoy arms. **Arm 5 is expected to FAIL on first run**
  — that is the point. **Then** triage the live `82 → 111` regression; not
  before, because re-pinning an unlocked classifier pins whatever it believes.
* **fourth: rows 44 and 50 are mine** (`run_removal_path_probe.py`,
  `sairncash_entitlement_gate_probe.py`), plus row 11's own open status on the
  priority list. **None written: this batch writes under `docs/` only.**

### 3.5 Counsel — the five questions

`docs/2026-10-14-ai-notice-wording-for-counsel.md` §7: approve or rewrite the
four wording blocks; say where the owner clause belongs and whether existing
customers re-accept; say whether the employee notice carries the responsibility
sentence; say whether the footer names a person or the business; and flag
anything missing for clinical, trust-account and personal-injury work.
**Nothing is blocked on the answer** — the version string exists so the wording
can land after the mechanism.

### 3.6 Still open from earlier batches, unchanged

* **`tools/fixture_lock_check.py`** (b13) — built by nobody. Without it the
  616 regrows.
* **`docs/by-design-register.json`** — 4 rulings, **still no reader**. The
  validator spec (b12) is built by nobody.
* **The `compact` matcher** has still never been observed firing, and cc's b8
  may remove the hook before anybody sees it.
* **b13's scratchpad litter** is still on disk; `rm` is denied and the register
  ruling `2026-10-14-rm-deny-bypassed-by-python` is the decision that unblocks
  it.

---

## 4. THE THING THE NEXT SESSION MUST DO FIRST

**Write the batch manifest before doing any item.**
`python tools/batch_manifest.py --new fourth b<n> --items <n>` — then `--set`
each item as it closes, and `--close` at the end **with
`PYTHONIOENCODING=utf-8`** until §3.3 is fixed. A batch with no manifest cannot
be closed, which is exactly what b14 discovered the hard way.

---

## 5. FINAL STEPS, AND WHAT THE TWO EARLY RUNS ACTUALLY SAID

1. `PYTHONIOENCODING=utf-8 python tools/drive_upload_verify.py --agent fourth
   --batch b15` → **exit 1**: `PASS SAIRN-handoff-fourth-b15.md` (11,594 bytes,
   sha256 `3dc88fbfc9d35b91`) **and 2 findings — the report and digest did not
   exist yet.** Expected: the handoff is written first by instruction.
2. `PYTHONIOENCODING=utf-8 python tools/batch_manifest.py --close --agent
   fourth --batch b15` → **exit 1, NOT CLOSED**, with the tool's own words:
   *"the Drive verify reported findings … Fix the upload, not this file."*
   **THE INSTRUCTION'S ORDER CANNOT BE SATISFIED AS WRITTEN** — closing is
   *defined* as all three deliverables verified, so a close before the report
   exists must fail. Run and reported rather than worked around; the close that
   counts runs after the report and digest are up, and its result is in the
   digest.
3. **This handoff was then re-opened once, deliberately**, to add §6 below. Its
   byte count and sha therefore change, and the Drive copy is replaced in the
   final upload — which is why §6's own numbers are the last thing written.
4. Release the b15 claim.

**Nothing is partial.** Every open item above is another session's, or mine and
named as mine, or a measurement with its command stated.

---

## 6. STARTUP CONTEXT — what was already in the window before I did anything

**`/context` IS NOT AVAILABLE TO ME.** It is a CLI slash command the operator
runs in the terminal; I have no tool that returns the harness's own token
accounting, and inventing a number from it would be the fabricated-figure
defect this platform has a register for. **So: everything below marked
MEASURED is a real byte count taken this session; everything marked ESTIMATED
is my own count of the text I was handed, at ~4 bytes per token.** If the
operator runs `/context`, its numbers win over mine.

### 6.1 The measured half

```
CMD python scratchpad/startup_context_b15.log (the measuring script's output)
  user CLAUDE.md                1,345 B   ~336 tok
  project CLAUDE.md            20,006 B  ~5,001 tok
  auto-memory MEMORY.md           644 B   ~161 tok
  skills name+desc, user        30,287 B  ~7,571 tok   (62 skills on disk)
  skills name+desc, project     23,247 B  ~5,811 tok   (34 skills)
  skills name+desc, plugin      33,948 B  ~8,487 tok   (111 skills)
```

**Skill BODIES are not injected** — 207 `SKILL.md` files totalling **3.25 MB
(~814k tokens)** sit on disk and only the name and description lines of the
model-visible subset reach the window. The injected listing I received was
roughly **100 entries**, so the skills line is **~6–8k tokens**, not 22k.

### 6.2 The estimated half, in descending order

| component | ~tokens | basis |
|---|---:|---|
| **loaded tool schemas** (14 built-in + 3 Claude Docs MCP) | **~9,000–11,000** | ESTIMATED from the text. `Workflow` and `Artifact` alone are ~20k characters of description between them; `Bash`, `Agent`, `ScheduleWakeup` and `Skill` are each 1.5–3k |
| **skills listing** (~100 names + descriptions) | **~6,000–8,000** | MEASURED per-file, scaled to the visible subset |
| **`CLAUDE.md` × 2** | **~5,300** | MEASURED |
| **system prompt** (identity, output style, harness rules, delivering-work, corrections, environment) | **~2,500** | ESTIMATED |
| **`SessionStart` hook output** — the full `superpowers:using-superpowers` skill text | **~1,100** | ESTIMATED; it is injected in full, not as a name |
| **MCP server instructions** (claude-in-chrome + Claude Docs) | **~1,200** | ESTIMATED |
| **deferred tool NAMES** (~100) | **~1,000** | names only; schemas load on demand |
| **`gitStatus` block** (branch, status, 5 recent commit subjects) | **~200–1,200** | MEASURED, and **highly variable** — see §6.3 |
| **auto-memory `MEMORY.md`** | **~160** | MEASURED |
| **the batch brief itself** | **~600** | ESTIMATED |
| **TOTAL BEFORE ANY WORK** | **≈ 28,000–32,000 tok ≈ 3% of a 1M window** | sum of the above |

### 6.3 The largest items, and what could actually be trimmed

1. **Tool schemas (~10k, the biggest single item).** `Workflow` and `Artifact`
   are the two heaviest and **neither has been used in b12, b13, b14 or b15** —
   this role writes docs and runs checkers. If the harness can defer them the
   way it defers the other ~100, that is the cheapest ~6k available. **Not
   mine to change**, and not worth a code change either; worth knowing.
2. **The skills listing (~7k).** 207 `SKILL.md` files exist and ~100 are
   listed. The plugin set (111 files) contributes the largest share and
   includes skills this role has never invoked. **Pruning the marketplace
   plugins actually installed would cut the listing proportionally.**
3. **`project CLAUDE.md` at 20,006 B (~5k).** It is already split — the
   discipline half lives in `docs/SAIRN-PROCESS-RULES.md` — and it earns its
   place: the measured-size warnings in it are what stop a session reading a
   2.38 MB index. **The trimmable part is the duplication**: PR §1.11 is
   restated in full inside it, and the clone table plus the skills-precedence
   notes could be one line each pointing at the process rules. **Realistic
   saving ~1.5k, and it is a judgement call, not an obvious win.**
4. **The `gitStatus` commit subjects — the one clear defect, and it is ours.**
   MEASURED on this repo:
   ```
   CMD git log -40 --format=%s | awk '/chore\(claims\)/{...}'
       claims: 12 msgs, mean 788 B
       other : 28 msgs, mean 106 B
   CMD git log -20 --format=%s | awk '{print length($0)}' | sort -rn | head -1
       2383
   ```
   **A claim commit subject averages 788 bytes against 106 for every other
   commit, and the longest is 2,383 bytes.** Five of those in the startup
   `gitStatus` is up to ~1.2k tokens of claim prose in every session in every
   clone. **The fix is ours and it is not the harness's:** put the claim's
   detail in the commit BODY and keep the subject to one line
   (`chore(claims): fourth claims fourth -- b15, 6 items`). `tools/sairn_claim.py`
   writes these; it is cc's file. **Routed as a finding in the report, not
   edited here.**
5. **`SessionStart` hook output (~1.1k).** The using-superpowers skill is
   injected in full on every start. It is one hook and it was authorised; it is
   listed for completeness, not as a complaint.

**WHAT IS NOT WORTH TRIMMING:** `MEMORY.md` at 644 B, the user `CLAUDE.md` at
1,345 B, and the deferred tool names. Together they are under 1.5k tokens and
each one prevents a specific, repeated mistake.

**AND THE ONE NUMBER THAT MATTERS MORE THAN ALL OF THEM:** startup is ~3% of
the window. **The real consumption in this role is reading repo files** —
`docs/SAIRN-OPEN-WORK-INDEX.md` is **2,382,161 B (~595k tokens)**,
`stonedesk.html` is **2,755,287 B (~689k)**, `api/sd-data.js` is
**1,160,184 B (~290k)**. **Any one of them read whole would cost 20–200× the
entire startup cost**, which is exactly why `CLAUDE.md` forbids reading the
first and why this batch read `api/sd-data.js` only through `grep` and
line-ranges.
