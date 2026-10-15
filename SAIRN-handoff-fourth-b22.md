# HANDOFF — fourth / ted, batch b22, 2026-10-15

**Written BEFORE the report**, at a point where nothing is half-finished: items
1 and 3–6 are committed and pushed, `HEAD == origin/main`, 0/0, no rebase and no
stash in progress, and the b22 claim is still held on purpose.

**ITEM 2 WAS NOT STARTED AND THAT IS THE ONE THING TO READ FIRST.** The claim
record refused it and **two** live claims cover it, not one. Nothing about it is
half-done — it is zero-done, deliberately, and it needs Michael to route it.

**EVERY FIGURE NAMES THE COMMAND THAT PRODUCED IT. Re-derive anything you mean
to quote, including out of this file.**

**THREE THINGS WORTH READING FIRST:**

1. **cody's two obligations are ONE change recorded twice** — the `what` text is
   byte-identical, 987 chars, `sha256 599ff05bfc1a3756` on both. **And neither
   recorded sha points at the change**: one does not resolve, the other is a
   36-file encoding sweep **that reads FRESH.** §4.
2. **The 400→503 count is wrong in both directions it has been counted.** 157
   branches, not hank's 98 and not my b21 63 — **and the cause is one
   identifier**: 99 of the 157 use a response variable literally named `r`. §6.
3. **The instruction said the sf_events SEVENTH anchor. Measured, it is the
   SIXTH** — anchor 7 resolves exactly once and needed nothing. §7.

**Transcript:**
`C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-fourth\578e6f48-a2d0-4543-b65b-e5b79ea4e6c8.jsonl`

**Working files (this session's scratchpad):**
`C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-fourth\578e6f48-a2d0-4543-b65b-e5b79ea4e6c8\scratchpad\`
New this batch: `sabotage_b22.log`, `m1_drive_b22.py`, `m1_b22.log`,
`verdict_b22_cody_A.txt`, `verdict_b22_cody_B.txt`, `discharge_A_b22.log`,
`discharge_B_b22.log`, `sdphotos_suite_b22.log`, `notprov_count_b22.py`,
`notprov_count_b22.log`, `np_shapes_b22.py`, `np_shapes_b22.log`,
`np_population_b22.py`, `np_population_b22.log`, `sf_events_anchors_b22.py`,
`sf_events_anchors_b22.log`, `sf_events_allspans_b22.py`,
`sf_events_allspans_b22.log`, `reanchor_sf_events_b22.py`,
`reanchor_sf_events_b22.log`, `citation_staleness_b22.py`,
`citation_staleness_b22.log`, `tiers_head.md`, `pre_push_tip_b22.txt`,
`pull_b22.log`, `push_b22.log`, `lock_b22.log`.
**This is a NEW session directory** — b18–b21's logs are under
`b0f8683c-3365-4d5b-82ea-094a13bdff7e` and are not here.

---

## 0. COMMITTED / PUSHED STATE

| | | command |
|---|---|---|
| HEAD | `86a27458` | `git rev-parse --short HEAD` |
| `origin/main` | `86a27458` | `git rev-parse --short origin/main` |
| behind / ahead | **0 / 0** | `git rev-list --left-right --count origin/main...HEAD` |
| working tree | **clean at the time of this line**; this handoff and the manifest's item-6 edit commit with it | `git status --porcelain` |
| push forced? | **NO — PROVED BY ANCESTRY, not by grepping git's wording** | pre-push tip `86a27458e05e` in `pre_push_tip_b22.txt`; `git merge-base --is-ancestor <tip> HEAD` → **ANCESTOR**, i.e. a fast-forward |
| first push attempt | **DENIED, and it was not about my commits** | `register_feed_gate` got no ref lines because the clone was 1 ahead / 4 behind — a non-fast-forward git was about to refuse itself. `git pull --rebase origin main` exit 0, then pushed clean |
| `SAIRN_SEED_GATE` | **not used, any form** | — |
| `SAIRN_GATE_EXEMPT` / `SAIRN_SKIP` | **neither used** | — |
| `.claude/settings.json` | **not edited, not committed** | not in the commit's file list |
| hooks | **untouched and never re-added** | by instruction |
| files written outside `docs/` | **0**, plus my own root deliverables | by instruction |
| files under `.claude/skills/sairn-hover-auditor/` | **0 — neither auditor clone entered** | by claim |
| all six b22 `docs/` paths on `origin/main` | **6 of 6** | `git cat-file -e origin/main:<path>` per file |
| b22 manifest | **5 `done`, 1 `blocked` with its reason** | `batch_manifest.py --check --agent fourth --batch b22` |
| **context now** | **24% of 1000k** | `tools/sairn_status_line.py` on this session's transcript |

**`86a27458` IS THE STATE BEFORE THIS HANDOFF** — this file, the report, the
digest, `SAIRN-latest-fourth.md`, the b22 close and the claim release all land
after it.

---

## 1. EVERY b22 ITEM — DONE AND NOT DONE

| # | item | state |
|---|---|---|
| 1 | cody's two obligations: one change or two, discharge accordingly | **DONE.** One change, **measured**. Both discharged exit 0 in `opened_at` order with the same body (§4) |
| 2 | hank's obligations F3/F4 then F1/F2 (leg_aftercare delimiter, census SQL) | **NOT STARTED — BLOCKED BY THE CLAIM RECORD AND FLAGGED BACK** (§3) |
| 3 | hank's `sd_photos` size fix with T17: Tier A review | **DONE.** `docs/2026-10-15-fourth-b22-sd-photos-size-t17-review.md`, 2 findings (§5) |
| 4 | hank's 400→503 helper: Tier A review | **DONE.** `docs/2026-10-15-fourth-b22-not-provisioned-helper-review.md`, 4 findings, **and the count re-derived** (§6) |
| 5 | the sf_events seventh anchor + re-count staleness from source | **DONE, and the instruction was off by one** (§7) |
| 6 | push without force, confirm landed | **DONE.** 0/0, ancestry-proved |
| — | this handoff, before the report | **DONE** |

**Nothing was consolidated this batch.** Items 3, 4 and 5 each got their own
document, which is the thing b21 could not do.

---

## 2. CLAIMS, LOCKS, STASHES

| hold | count | detail | command |
|---|---:|---|---|
| repo claims held | **1** | b22, published on `origin/main`; **release LAST**, after all four uploads verify | `sairn_claim.py list` |
| **Tier A obligations assigned to me** | **0** | both were discharged this batch; register open owned by `fourth` went **2 → 0** | `tier_a_review_gate.py --list` |
| obligations discharged this batch | **2** | both as the **assigned owner**, neither by `--takeover`. Register total open **15** after | before/after `--list` |
| **session lock** | **1, MINE and LIVE** | it was **DEAD on arrival** — `CLAUDE_PID 3444`, the b18–b21 session, 263m idle. Reclaimed by `session_lock_check.py guard` (a reclaim, **not** an `rm`); now `SELF`, `CLAUDE_PID 15120` | `session_lock_check.py status` |
| locks removed by me | **0** | — | — |
| **`git stash`** | **0** | nothing stashed, nothing to recover | `git stash list` |
| worktrees | **5 total, NONE MINE** | other sessions' temp gate trees | `git worktree list` |
| status registry row | `working` | set at batch start; **`idle` at release** | `sairn_status.py set` |

---

## 3. ITEM 2 — WHY IT IS ZERO-DONE, AND WHAT MICHAEL HAS TO DECIDE

**`python tools/sairn_claim.py check fourth "<the b22 task string>"` returned
BLOCKED**, verbatim:

```
session   : hank
task      : b13 ... fourth F4 F5 leg_aftercare key ambiguity ...
            FILES: api/sd-data.js api/sen-auth.js
            api/sd-data-cross-tenant-dispatchers.test.js
claimed   : 2026-10-15T00:22:44Z (0.3h ago)
blocked by: same file or resource: leg_aftercare
also share: aftercare, fourth, hank, leg, t17
DO NOT start this. Flag it back to the coordinating chat session.
```

**And it is not one claim, it is two.** `cody`'s live **b14** claim reads
*"leg_aftercare key-collision arm"* with `tests/run_b14_leg_aftercare_probe.py`
in its FILES list. So **hank is fixing the leg_aftercare delimiter collision and
cody is arming it, right now, concurrently.** A third session editing the same
subject is the shape the claim record exists to stop.

**PER PR §4.3 THE TASK STRING WAS NOT REWORDED TO SLIP PAST THE MATCHER.** Item
2 was **dropped from my claim** and the claim I did take says so in its own text.
The other half of item 2's parenthetical — **the census SQL — is hank's own b12
F1 and hank already fixed it** in `4f69facd` (`sql/legacy_ciphertext_census.sql`
and `sql/sd_encryption_key_revoke_2026-09-24.sql` now walk `jsonb_each(data)`
instead of assuming a top-level `enc`; `sairn_sql_preflight.py --live` 0
findings on both). **So there is nothing for me to do on that half even if the
first half were unblocked.**

**EXACT NEXT STEP — and it is Michael's, not mine:** either (a) leave
leg_aftercare with hank and cody and strike item 2 from fourth's queue, or (b)
tell hank and cody to release it and re-issue it to me. **Do not hand it to a
fourth agent while two claims are live on it.** If (b): the subject is my own
b20 F4/F5 — the delimiter-ambiguous aftercare key and the canonicalisation's
local duplicate — and the starting point is
`docs/2026-10-14-fourth-b20-leg-role-matrix-discharge.md`.

---

## 4. ITEM 1 — ONE OBLIGATION RECORDED TWICE, AND BOTH SHAS ARE WRONG

`docs/tier-a-reviews.json`, records `cody 2026-10-15T00:00:41Z` and
`cody 2026-10-15T00:02:27Z`.

**THE DUPLICATE IS MEASURED, NOT INFERRED.** Field by field: `author_session`,
`opened_at_sha_basis`, `resources`, `rules`, `irreversible`, `files`, `what`,
`reviewer_owner` **identical**; the `what` **byte-identical, 987 characters,
`sha256 599ff05bfc1a3756` on both**. Only `opened_at` (1m46s apart) and
`opened_at_sha` differ. **One review body was recorded on both records** rather
than split into two half-reviews or closed on one and left open on the other.

**NEITHER RECORDED SHA POINTS AT THE RECORDED CHANGE:**

```
bc24af59f3db   git cat-file -t -> could not get object info  (rebased away)
f8baf814bfd9   RESOLVES -- and is a 36-FILE repo-wide encoding sweep. Its
               ENTIRE hunk on the named path is:
                 -  capture_output=True, text=True)
                 +  capture_output=True, text=True, encoding='utf-8',
                    errors='replace'
44fad1f9       the REAL change, 2 files: "the tripwire list is DERIVED, and the
               pre-fix counterfactual is RETIRED with its finding"
```

`subject_sha()` (`tools/tier_a_review_gate.py:1570-1590`) seats a record on **the
last commit TOUCHING the named files** and stamps basis `file-set`. **That rule
is working as written** — and the record it produced reads **FRESH**, the
strongest provenance the tool has, while pointing at a one-line encoding
argument. **ROUTED TO cc:** print the touched-file count beside the basis —
`file-set (36 files touched; this record names 1)` — so FRESH stops reading as
*"this sha is the change"*. **This is the sibling of the b21 author-time
finding, not a repeat:** that one was `--reseat-shas` offering a candidate
authored AFTER `opened_at`; this is the ORIGINAL stamp landing on a later
unrelated commit.

**THE REVIEW ITSELF — three checks the author asked for, each driven:**

* **M1 CONFIRMED EXACTLY, AND BY MY OWN DRIVE.** The GRD unit header at
  `api/sd-data-cross-tenant-dispatchers.test.js:648` set to `app: null, role:
  null` in a `tempfile.mkdtemp()` copy → **405 passed, 14 failed**, exactly the
  claimed 14 (`m1_drive_b22.py`, `m1_b22.log`). `git status --porcelain api/`
  empty afterwards. **And the derivation self-heals:** the same regex returns
  `[]` on the live suite and exactly `grd_boq_rates` on the mutant — the FIRST
  member, which the `[L-rev]` arm requires.
* **THE REPLACEMENT COVERAGE ARM DID NOT GENERALISE WITH THE DERIVATION.**
  `derive_tripwires` reads every `{ map: … app: null … }` unit; the arm that
  makes an empty list honest is hardcoded to `re.match(r"\s*\{ map: 'GRD ")` and
  one gate-suite path. Measured: **20 units, 0 of them `app: null`**. Any of the
  other 19 can trade the tripwire property away with no replacement asserted,
  and at a derived count of zero that drop is invisible. **The hardcoded list
  was removed from the tripwires and left in place one layer up.**
* **THE ARM'S QUALITY GATES ARE FILE-GLOBAL where the property is
  per-resource** — `m not in _gate_src` is substring-anywhere, and
  `'NO_SESSION' in src and '401' in src` is one test for the whole file.
  **The property genuinely holds today anyway**, and more strongly than the arm
  checking it: `tests/sd_data_grd_session_gate.js:129-150` **loops** its own GRD
  array driving every resource/action pair to `401 NO_SESSION`.
* **NOT CORROBORATED, and said rather than implied:** cody's *"5 of 5 mutants
  driven"* — four of the five mutate the gate suite, which the probe reads from
  `ROOT` and not from its sandbox, so driving them means writing a live-clone
  file inside another session's read-only zone. **M1 was the one that needed no
  live write; it matches exactly. The other four remain the author's
  measurement.**

**Probe re-run at HEAD:** `python -u
tests/run_cross_tenant_dispatchers_sabotage_probe.py` → **exit 0**, baseline
**419 passed / 0 failed**, 15/15 mutations refused each in its own branch,
`derived 0 'app: null' unit(s)`, `ok grd replacement`.

---

## 5. ITEM 3 — THE `sd_photos` SIZE FIX AND T17

`docs/2026-10-15-fourth-b22-sd-photos-size-t17-review.md`. Subject
`e9d9c8192620`, 5 files, 938+/92−. Suite **26 passed / 0 failed / 0 unproven**,
`node --check` clean on all three JS files.

**WHAT HOLDS, and the one assumption everything rests on:** the 64 KB constraint
is **per row** — `sdSyncCollection()` pushes `sdData('write', key, r)` one row
per photo (`stonedesk.html:2101`) and skips unchanged rows (`:2100`) — so the
44,000-character budget does not compound across the 200 locally-held photos.
**Had the collection been blob-wrapped, which is exactly what
`SD_SYNCED_OBJECT` does twenty lines earlier (`:2060-2071`), the budget would
have blown at photo two.** The ladder measures each rung's resulting length
rather than predicting it, and `null` is a real answer.

**T17 IS ON THE ROW, and it is the clean counter-example to my own b21 F4.**
`p.ai_source = 'claude:photo-qc'` is set on the row object immediately before
`saveSD3Data()` (`:26191-26192`), so it reaches the server copy. `rf_photos`
drops its equivalent because the handler rebuilds the record; **nothing rebuilds
`sd_photos`.** Only `aiAnalysis` is in the redaction partition
(`api/_lib/ai-scan-redaction.js:96`) — `data` is deliberately absent, because
redacting a base64 payload corrupts the image.

**TWO FINDINGS, both in the caller rather than the mechanism:**

* **F1 — the failed-downscale branch stores AND SYNCS the original.**
  `stonedesk.html:26078` is `data: small ? small.data : e.target.result`, and
  eighteen lines above it the function's own comment states the rule this breaks.
  It is not silent (`downscaled: null`, `dims: null`, `src_bytes` recorded), **but
  the toast's claim is the one thing that can be false**: *"Photo kept on this
  device only"* is asserted before the write that would make it true, on a row up
  to ~13.3 MB against a 5–10 MB whole-origin `localStorage` quota — `st()`
  reports that honestly, so the user gets two messages for one photograph and
  they disagree. **And `photoAiAnalyze()` re-saves the row, so it is refused a
  second time.** **Next step: skip the row in the sync set (`backup: false`, the
  same shape as the existing idless-row skip at `:2098`) or keep a thumbnail.**
  **Not theoretical** — `small === null` is also `img.onerror`, a null 2D context
  and any `toDataURL` throw, which is the phone.
* **F2 — the margin is counted in UTF-16 characters and the constraint counts
  octets.** 65,536 − 44,000 = **21,536 bytes** for the rest of the row, against
  an `aiAnalysis` of ~600 characters — roughly 30× the expected need, **but
  nothing measures it, and `name: file.name` is unbounded and OS-supplied.**
  **Next step, if anything: cap `name` on the row.**

**NOT CHECKED, said rather than left implicit:** the downscale was not driven in
a browser (no real `canvas`), so *"an 11-rung ladder gets a phone photo under
44,000 characters"* remains hank's measurement. What I verified is that the code
**checks** rather than assumes, which is what makes the claim self-correcting.

---

## 6. ITEM 4 — THE 400→503 HELPER, AND A COUNT ANCHORED ON A VARIABLE NAME

`docs/2026-10-15-fourth-b22-not-provisioned-helper-review.md`. Predicate printed
with the result: a single line matching
`(\w+)\.status === 404 \|\| \1\.status === 400`, over `api/sd-data.js` at HEAD
(18,503 lines), comment lines excluded.

| bucket | what the branch does on a 400 | count |
|---|---|---:|
| **RAW** | lines matching the predicate | **331** |
| **A** | rewritten — `notProvisioned()` within 5 lines | **88** |
| **B** | **NOT rewritten** — `res.status(503) NOT_PROVISIONED` inline, no body read | **69** |
| **C** | `res.status(200) { ok: true, data: [], provisioned: false }` | **151** |
| | other | 23 |
| | A + B + C + other | **331** |

**So the 503-answering population is 157 — not hank's 98 and not my b21 63.**
By call site instead of by guard: **89 `notProvisioned()` sites, 89/89 awaited,
89/89 with control provably stopping, 0 that may continue, 5 passing a preread
body** (lines 2769, 2988, 3331, 3434, 8486).

**THE CAUSE IS ONE IDENTIFIER, AND IT IS MEASURED:** of the 157, **99 are
guarded on a response variable literally named `r`**; the other 58 use
`existingR` (10), `w` (7), `cur` (4), `cr` (4), `sr` (3), `existingPhoto`, `jr`,
`rr`, `exq` (2 each), `sfoRows`, `wr` (1 each). **hank's 98 is within one of 99.**
A predicate written as `r.status === …` reads like a **shape** and is actually a
**name**, and its output reported a sample as a population. **Mine was the same
defect in the other direction four days ago** ("roughly twelve" → 63). **The
convention needs one more clause: when a predicate names an identifier, say
which identifier.**

**FOUR FINDINGS ROUTED TO hank, F1 and F2 FIRST because 88 branches now depend
on the helper:**

* **F1 — `pgCode.slice(0, 2) === '23'` is the WHOLE integrity class and only
  `23514` is the row cap** (`api/sd-data.js:18431`). A unique violation
  (`23505`), an FK violation (`23503`) or a not-null violation (`23502`) now
  tells the operator the record *"most often"* exceeded a 64 KB row cap. **A new
  misattribution created by the fix** — narrower and less damaging than the one
  it replaced, but it names a specific wrong cause. **Next step: branch on
  `23514`.**
* **F2 — the 503 arm's bare `/does not exist/i` is tested against the whole raw
  body**, which includes PostgREST's `details`/`hint` echo of offending values.
  **Next step: drop the bare alternative** and keep the specific ones.
* **F3 — the 69 un-rewritten branches** are the identical un-read 503 fold, line
  numbers in `np_population_b22.log`. Sampled and confirmed at `:2239`, `:2605`,
  `:4123`, `:10129`, `:18205`. **The commit's "nine were left alone because they
  already read the body" does not describe these — these do not read the body.**
* **F4 — the 151 read branches are a WORSE fold and nothing in this change
  reached them.** On a 404, `{ ok: true, data: [], provisioned: false }` is a
  reasonable product choice. **On a 400 it is a silent failure in the strict
  sense**: `ok: true`, no error code, an empty list, and a flag asserting a cause
  the server did not establish. **Strictly worse than the wrong 503 this commit
  set out to fix**, and **it is in nobody's open work.**

**CREDIT WHERE IT IS DUE:** the `preread` parameter is the part that shows this
was reviewed rather than scripted — a `Response` body is readable once, the
first draft broke five sites, and hank found it by reading two rewritten sites
in context after the mechanical pass and said so in the commit message.

---

## 7. ITEM 5 — THE ANCHOR WAS THE SIXTH, AND b21'S CITATION FIGURES DO NOT REPRODUCE

`docs/2026-10-15-fourth-b22-sf-events-reanchor-and-citation-recount.md`.

**THE INSTRUCTION SAID THE SEVENTH ANCHOR.** Enumerated from the cell's own
backticked spans rather than by hand (`sf_events_allspans_b22.py`) — because
hand-numbering a 22-span table cell is how an off-by-one becomes a confident
edit to the wrong anchor:

```
anchor 1..5  count=1  OK
anchor 6     count=0  ** ROTTED **   if(ev && ev.sessionId) st(K_SESSIONS, getSessions().filter(
anchor 7     count=1  OK             if(getEvents().some(function(e){ return e.sessionId===s.id; })) return;
```

**Anchor 7 resolves exactly once and needed nothing.** Anchor 6 had gone to zero
because hank b12 F6 rewrote `sfDeleteEvent()` (`sairnfreedom.html:5222-5254`) to
**count the rows it removes** instead of choosing its toast on the pointer being
truthy. Replaced with two anchors — `var after = before.filter(function(s){
return s.id!==ev.sessionId; });` and `removedSessions = before.length -
after.length;` — **both verified to resolve exactly once BEFORE the write**. The
cell now carries **eight** anchors and says so. **The row's integrity argument
is unchanged and better evidenced:** the delete still matches on the stored id
alone, and it can now distinguish a pointer that resolved from one that resolved
to nothing.

**EDIT METHOD, because the row is one 4,292-character table line:** no split on
`|`. `reanchor_sf_events_b22.py` locates the row by its prefix, refuses unless
the substring occurs **exactly once**, refuses a pipe in the replacement,
asserts the line's **pipe count 7 → 7**, and verifies the new anchors before
writing. After: all 8 anchors count 1, `criticality_tier_check.py`
**PROBLEMS:0**, `RESOURCE_ROWS:391`, `TIER_A:275`.

**THE CITATION RECOUNT, and b21's numbers are NOT re-derivable:**

| | **b22, measured** | b21, as written |
|---|---:|---:|
| TOTAL line citations | **571** | 551 |
| EXPLICIT, path resolves | **198** | 196 |
| path-shaped but absent | **0** | — |
| **BARE `:NNNN`**, UNASSESSABLE | **373** | 355 |
| **PROVABLY STALE** | **0 of 198** | 0 of 196 |
| LIKELY STALE (blank/comment line) | **39 of 198 (20%)** | 37 of 196 (19%) |

**THE DELTA IS ENTIRELY PREDICATE, AND THAT IS PROVED:**
`git diff --stat 7a5e6a11 HEAD -- docs/CRITICALITY-TIERS.md` is **EMPTY**, and
the same script gives **571 / 198 / 373** against both `git show
HEAD:docs/CRITICALITY-TIERS.md` and the working tree — so my own re-anchor added
zero citations. **The file is byte-identical and the numbers differ. Carry the
b22 figures, with the predicate attached.** The standing conclusion is
unchanged: **0 provably stale, and 65% (373/571) cannot be mechanically checked
at all**, which is a form problem and not a staleness problem.

**One thing found and NOT fixed:** the cell also carries bare prose spans
`` `eventRefusals()` ``, `` `liquorServiceCheck()` `` and `` `sc_auth` ``, each
counting **0** in the app — not because the functions are missing, but because
the register writes them with empty parentheses and the source writes them with
arguments. **They are prose, not anchors. If cc's anchor-rot check treats every
backticked span as an anchor, these three are its first three false positives**
— routed to cc with that example.

---

## 8. WHAT IS OPEN, AND WHY — routed work

### hank — F1 and F2 of the helper first

* **The four helper/population findings** above: `23514` vs class `23`, the bare
  `/does not exist/i`, the **69** un-rewritten branches, the **151** read
  branches. **F1 and F2 are two-line changes inside the thing 88 branches
  depend on, and should go first.**
* **The two `sd_photos` caller findings**: the failed-downscale branch, and the
  `name` field inside the octet margin.
* **Still open from b19–b21 and NOT re-verified this batch:** b18's **N1**; the
  MAR grant bypass via `alf_clients` with no audit row (my b21 F3); the
  `rf_photos` record rebuild dropping `ai_source` (my b21 F4); `license_hash`
  never re-verified in memory; no revoke action for a live grant.
* **A design question, not a defect, still unanswered:** the granted MAR read
  yields only `date`/`time`/`status` and never medication names, so an
  `office_manager` grant admits a billing clerk to a list that cannot serve
  coding work.

### cody — arms, all failing-first

* **The REPLACEMENT COVERAGE generalisation arm:** flip a NON-GRD unit from a
  real app to `app: null` and back, and assert the suite notices the trade. Today
  it only notices for `GRD`.
* **A per-resource refusal arm** for the gate-suite check: a gate suite that
  drives ONE resource to 401 and lists the other five in a comment must FAIL the
  probe's arm. It currently passes.
* Plus the b20 aftercare-collision arm (**now contested — cody's own b14 claim
  has it**), the F3/F4 arms from my b21, and b19's four.

### cc — `tools/`

* **The `subject_sha()` disclosure** (§4): print the touched-file count beside
  the `file-set` basis.
* **The anchor-rot check's first three false positives** (§7): prose spans with
  empty parentheses.
* **The re-seat author-time guard** from b21, still open.
* b19's census asks 1 and 4; `batch_manifest.py:386` (**still worked around with
  `PYTHONIOENCODING=utf-8` on every call**); the b20 drive-verify findings.

### Michael

* **ITEM 2, and it is the only thing I am waiting on.** §3: strike it from
  fourth's queue, or have hank and cody release it. **Two live claims cover it.**
* **F4 of §6 — the 151 read branches** are the largest un-owned population I
  found this batch and belong in somebody's queue.

### hover2 / hover

Unchanged from b21: four `# OWNER: hover2` lines; which tree is canonical for
the four basenames that exist in both with different contents.

---

## 9. FINAL STEPS STILL AHEAD OF THIS HANDOFF

1. Commit this handoff with the manifest's item-6 edit, and push.
2. **Upload this handoff to Drive folder
   `14Xc5oT0xzSLa_rTSOSXWVK3Kko1Fbx09` and verify.**
3. The report and digest, plus **`SAIRN-latest-fourth.md`**, then
   upload-and-verify, then a **Drive-side API read** — the mount proves the bytes
   are in the sync set, not that Google acknowledged them. **Expect the API read
   to lag; b19's, b20's and b21's first reads came back empty and were a retry,
   not a missing file.**
4. `batch_manifest.py --close --agent fourth --batch b22` — **after** the uploads
   verify.
5. **Release the b22 claim LAST**, then set the status row to `idle`.

**Nothing is partial.** Every open item above is another session's, or Michael's
with its decision named, or a measurement with its command stated. **Item 2 is
zero-done and the reason is a tool's refusal, quoted in §3.**
