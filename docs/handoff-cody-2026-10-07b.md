# cody — handoff, 2026-10-07b (batch 24)

**Claim:** `cody / Tooling`, batch 24, claimed at HEAD `81bd8814`.
**Written per item, not at the end.** Item 2 of this batch sets the checkpoint
habit to **every single item**: the item's line below is written *before the next
item begins*, so a stopped terminal loses at most one item of context. The
previous habit wrote a line per item too, but only into the final handoff at the
end of the batch — if the session died mid-batch the log died with it. The
change is **when** it is written, not how often.

Batch detail as it accumulates: `docs/2026-10-07-cody-batch24.md`.

---

# BATCH 24 CHECKPOINT LOG — one line per item, written before the next starts

## item 1 — REPORT ONLY. The item's premise is wrong, and wrong about WHO.

The item says my 6 eligible Tier A obligations are blocked by **fourth**. They
are not.

```
command : read all seven .claude/claims/*.json with the 4h expiry applied
commit  : 81bd8814        date: 2026-10-07T17:41Z
  fourth  fourth-1791390962   1.08h  active   -- does NOT declare the ledger
  hank    hank-1791305269    24.89h  EXPIRED  -- declares it, but dead
  hank    hank-1791326357    19.03h  EXPIRED  -- declares it, but dead
  hank    hank-1791389299     1.55h  active   -- does NOT declare it
  cc      (none in this clone's copy)
```

fourth's batch15 claim — the one that blocked me in batch 23 — was **released**
and replaced at 16:36:02Z by a batch16 claim whose FILES list does not contain
`docs/tier-a-reviews.json` and whose task text has no Tier A mention. So on that
read the ledger was free and I moved to discharge.

**THE MATCHER CORRECTED ME, AND THE REAL HOLDER IS CC.** My first claim attempt
was **REFUSED**:

```
python tools/sairn_claim.py claim Tooling "<batch 24, ledger in FILES>"  -> EXIT 1
  BLOCKED -- session cc, claimed 2026-10-07T17:24:00Z (0.3h ago)
  blocked by: same declared FILES: docs/tier-a-reviews.json
  REFUSAL RECORD: cc held 'cc' on docs/tier-a-reviews.json
                  (registry, not yet on origin)
```

cc claimed it **17 minutes before my attempt**, declares it in FILES, and cc's
own item 0 is the *identical* most-overdue-first discharge. The reason my own
read missed it is worth keeping: **cc's claim was in the shared registry but not
yet pushed**, so a read of this clone's `.claude/claims/cc.json` showed no active
claim. The file read was correct and stale at the same time; only the matcher,
which reads the registry, could see it.

**Not overridden, not reworded past.** The claim was re-made with the ledger
**removed from FILES** and the narrowing stated in the claim text itself. I
discharge **none**.

**My 6 eligible obligations, re-derived at `615ea3d4`, 2026-10-07, most overdue
first** (authored by somebody else AND `reviewer_owner == cody`; 23 open total):

| age | author | opened | resources |
|---|---|---|---|
| 52.3h | fourth | 2026-10-05T15:02:28Z | `quotes` |
| 45.9h | fourth | 2026-10-05T21:25:19Z | `alf_activities, alf_billing, alf_claim_routes, alf_clients, …` |
| 37.1h | hank | 2026-10-06T06:14:34Z | `alf_clients, alf_family_contacts, alf_mar` |
| 37.0h | cc | 2026-10-06T06:18:11Z | `quotes, sb_ap` |
| 35.8h | hank | 2026-10-06T07:29:58Z | `sdn_projects` |
| 35.4h | hank | 2026-10-06T07:56:17Z | `sen_settings` |

A further **9** are open, authored by others, owned elsewhere and past the 48h
takeover line. I took none of those either, for the same reason.

**NEXT STEP:** when cc releases, discharge the 52.3h `quotes` record first and
work down the table. **Do not re-derive the block from the claim FILES alone** —
check with `sairn_claim.py` itself, which reads the registry a clone's own copy
can lag behind.

## item 2 — DONE. The habit is now per item, and NO tool was built.

The habit: **the item's line goes into this file before the next item starts.**
Not every 5–6 items, not at the end of the batch. This section is the proof — it
was written before item 3 began.

**Nothing was built**, as the item instructs. There is still no
memory-checkpoint tool, and `tools/audit_checkpoint_status.py` remains unrelated
(it concerns audit checkpoints, not my working state). The habit has no trigger
but my own discipline; that is unchanged and is stated rather than papered over.

**What changed, concretely:** batch 23 wrote its 12 item lines into
`docs/handoff-cody-2026-10-07.md` *at the end*, in one pass. Batch 24 writes
each line as the item closes. The failure this addresses is the one that opened
batch 23 — a stopped terminal that left an uncompiled probe and no record saying
so.

## item 5 — DONE. 30 registrations → 2, and the config is byte-identical.

```
command : git worktree remove --force <path>  x29, then git worktree prune
commit  : 615ea3d4        date: 2026-10-07
```

**CHECKED BEFORE ACTING, because `prune` would have removed nothing.** All 30
registered directories **still existed on disk**, so they were not stale in
git's sense — `git worktree prune` only drops registrations whose directory is
gone, and running it first would have reported success having done nothing.
That is why `remove --force` was used instead.

**And checked for live use, because deleting another session's working worktree
would break its run:** newest mtime among the 29 was **2026-10-06 16:10**, over
a day old, and `Get-CimInstance Win32_Process` showed **no live process command
line referencing any of the 29 paths**.

```
removed rc=0 : 28
skipped      :  1  (the locked one)
failed       :  0
after        : 2 registrations -- this clone, plus the locked one
```

**The config did not move, which was the actual risk:**

```
.git/config BEFORE  sha256 93070fe59db24a5bdcf7aca3bc619fd5bd14247986522ad8f624aeceb108ad98  506 bytes
.git/config AFTER   sha256 93070fe59db24a5bdcf7aca3bc619fd5bd14247986522ad8f624aeceb108ad98  506 bytes
core.bare           false before, false after, rc 0 both times
```

Same hash as the one recorded in batch 22's targeted proof, so the file has not
drifted since.

**WHAT HOLDS THE LOCKED ONE, read rather than assumed:**
`C:/Users/marsh/AppData/Local/Temp/newchk-27740`, detached at `3e738db0`.
`.git/worktrees/newchk-27740/locked` contains exactly one word:
**`initializing`**. That is the lock git itself writes during `worktree add` and
removes when the add completes — so this is **not a deliberate lock, it is an
interrupted `worktree add` that never finished**, left behind since the
directory's mtime of 2026-09-21. **Left in place as instructed.** Removing it
needs `--force` twice (once for the lock, once for the worktree) and that is a
judgement about somebody else's interrupted run, not bookkeeping.

## item 9 — DONE. All four runbook artefacts are on `origin/main`.

```
command : git log -1 --format=%H -- <path>  then  git merge-base --is-ancestor <sha> origin/main
commit  : 7ce70c6c        date: 2026-10-07
```

| path | last commit | rc | bytes |
|---|---|---|---|
| `docs/2026-10-05-michael-sql-runbook.md` | `d8bc39e4db7d` | **0 — PUSHED** | 8,740 |
| `sql/zz_confirm_2026-10-05_missing_tables.sql` | `d8bc39e4db7d` | **0 — PUSHED** | 10,975 |
| `tools/gate1_verify.py` | `d8bc39e4db7d` | **0 — PUSHED** | 12,553 |
| `docs/2026-10-06-sql-runbook-remaining-19.md` | `ae47c86ad62e` | **0 — PUSHED** | 9,116 |

`git branch -r --contains d8bc39e4` also lists `origin/main`. **Nothing to
push.** The commit subject is *"the 20 SQL files are ready to paste, with a
confirm file and a verifier that asks the APP rather than the catalogue."*

**ONE DISCREPANCY, REPORTED NOT SMOOTHED OVER:** the doc is called the 20-file
runbook, and `grep -oE "sql/[A-Za-z0-9_.-]+\.sql"` over it returns **24 distinct
`sql/` paths**, while its numbered table has **7** rows. So the three counts —
20 in the title, 24 referenced, 7 tabulated — do not agree. The *push status*
asked for is settled; the count is not, and whether 20 is the right number is a
separate question for whoever owns the runbook's content. Not silently
corrected here.

## item 10 — DONE. 53 of 322 in the real leak class, 17 mine, 7 of those genuine — and the predicate was WRONG TWICE before it was right.

**THE MEASUREMENT, and the two corrections are the useful part.**

```
command : scratchpad/b24/i10_scan.py, i10_scan2.py, i10_percall.py, i10_ordered.py
commit  : 7ce70c6c        date: 2026-10-07
```

| pass | predicate | result | why it was wrong |
|---|---|---|---|
| 1 | file mentions git at all | 85 of 160 files | over-counts every file that merely runs `git log` |
| 2 | per call, identifier appears on a git-creating line | 87 calls, 26 mine | **WRONG**: it flagged `rmtree` calls that run *before* the repo exists |
| 3 | ordered — the repo must be created at a line BEFORE the removal | **53 of 322 calls, 17 mine** | the number reported |

**What pass 2 got wrong, found by reading two of its own hits rather than
trusting the count.** `tests/entitlement_freshness_control.py:78`:

```python
wt = tempfile.mkdtemp(prefix='sairn-ent-')
shutil.rmtree(wt, ignore_errors=True)          # <- flagged by pass 2
subprocess.run(['git','-C',REPO,'worktree','add','-q','--detach',wt,'HEAD'])
```

That removal runs **before** anything exists. It is not cleanup — it is the
"mkdtemp for a unique name, then delete so `worktree add` will accept the path"
idiom, because `worktree add` refuses an existing directory. The tree is EMPTY
there, so `ignore_errors=True` is **correct** and changing it would be a
pointless edit to working code. **26 calls were excluded on that ground.**

**AND THE CLASS IS NARROWER THAN "A TREE WITH A REPO IN IT" — MEASURED, NOT
REASONED:**

```
command : a throwaway git init + worktree add, counting files without S_IWRITE
commit  : 7ce70c6c        date: 2026-10-07
  CLONE/INIT repo dir   read-only  3 of 33 files
  LINKED WORKTREE dir   read-only  0 of  2 files   (.git there is a FILE)
  shutil.rmtree(base, ignore_errors=True) -> left base behind: True
```

So **a linked worktree directory has no read-only files at all** and is not in
this class; only an `init`ed or `clone`d directory is. The last line is the leak
**reproduced live in one command**, which is the strongest evidence here — not
an inference from the 239-file incident.

**MY 17, CLASSIFIED BY READING EVERY ONE:**

**GENUINE — 7.** A repo directory, no prior `worktree remove`, no assertion that
it is gone:

| file:line | what it removes |
|---|---|
| `tools/run_all_tests.py:835` | the throwaway **clone**, on the checkout-FAILURE path |
| `tests/claims/run_freshness_probe.py:536` | a clone of the repo |
| `tests/push_gate/redaction_base_probe.py:200` | a local clone (its own comment notes the hardlinks) |
| `tests/push_gate/refspec_and_override_probe.py:219` | a clone-based sandbox |
| `tests/push_gate/refspec_and_override_probe.py:453` | a second clone-based sandbox |
| `tests/run_bare_run_write_probe.py:267` | seven `git init` fixture dirs, in a loop |
| `tools/clone_health_check.py:399` | a mkdtemp holding an `init`ed repo |

**NOT THIS CLASS — 5.** A *linked worktree* directory, which the measurement
above shows carries no read-only files:
`tests/entitlement_freshness_control.py:265`,
`tests/failsafe/countersign_coverage_probe.py:178`,
`tests/run_dead_rule_sweep_probe.py:588`,
`tests/run_tool_owner_header_probe.py:246`,
`tests/sairnroofing_fault_probe.py:177`.
Two of those also *print* whether the directory is gone, so even a failure would
be visible.

**NOT A LEAK — 5.** `git worktree remove --force` runs first and does the real
work, or an arm asserts the directory is gone:
`tests/run_dead_rule_sweep_probe.py:394`, `tools/condition_coverage.py:269`,
`tools/dead_rule_sweep.py:677`, `tools/dead_rule_sweep.py:753`,
`tools/clone_health_check.py:328`.

**FIXED — 1 of the 7, and only one is in this batch's declared FILES.**
`tools/run_all_tests.py:835` now uses the `_force_rm` retry handler **that
already existed 134 lines above it**, plus the same leftover-file NOTE the
success path prints. The shape worth naming: that helper was added on
2026-10-07 for the success path, and **the sibling failure path 68 lines away
kept `ignore_errors=True`** — a fix reached the line somebody was looking at and
not the one beside it.

**ROUTED, NOT FIXED — 6 of the 7.** `run_freshness_probe.py`,
`redaction_base_probe.py`, `refspec_and_override_probe.py` (two sites),
`run_bare_run_write_probe.py`, `clone_health_check.py`. All six are mine by my
own records and **none is in this batch's declared FILES**, so editing them
would be widening a claim without declaring it. **NEXT STEP:** declare those
five files in the next batch and apply the identical `onerror` change; the patch
shape is already proven in `run_all_tests.py`.

**NOT MINE — 36 calls.** Listed in full in
`scratchpad/b24/i10_ordered.txt`; the largest single holder is
`tests/run_fail_open_probe.py` with 8. **Routed to chat for assignment**, with
the caveat that my attribution floor (my own append log plus my claim FILES)
under-counts mine, so some of the 36 may also be mine.

**ATTRIBUTION LIMIT, stated rather than left implicit:** every commit in this
repo has the same git author, so `git log --format=%an` cannot say which session
wrote a file. Authorship here comes from `SAIRN-ACTIVE-WORK-cody.md` and the
FILES sections of `.claude/claims/cody.json`. Both under-count — my batch-23
fixture file was not matched by the first version of that test — so **17 is a
floor, not a total.**

## item 6 — DONE. There is NO moderate left, nothing is lockfile-only, and the lock is byte-verified UNCHANGED.

```
command : npm audit --json   +   grep over the installed firebase-admin
commit  : 7ce70c6c        date: 2026-10-07
TOTALS  : info 0, low 0, moderate 0, high 2, critical 0, total 2
```

**THE ITEM'S PREMISE IS HALF WRONG AND THIS IS THE CORRECTION.** It asks for
*"the 2 advisories beyond busboy (1 high chain, 1 moderate)"*. **There is no
moderate.** The busboy fix at `a1386313` took moderate 1 → 0, and the 2 that
remain are **both high and both the same advisory**, counted once as the
vulnerable package and once as its effect on the dependent:

| # | package | direct | range affected | fixAvailable | semver-major |
|---|---|---|---|---|---|
| 1 | `node-forge` | no | `*` (advisory `<=1.4.0`) | `firebase-admin@14.5.0` | **YES** |
| 2 | `firebase-admin` | **yes** | `5.0.0 – 13.9.0` | `firebase-admin@14.5.0` | **YES** |

Advisory: **GHSA-86w9-cpqp-85rv**, *"node-forge RSA PKCS#1 v1.5 signature
verification accepts extra nested …"*.

**DEPENDENCY PATH:** `package.json` → `firebase-admin ^12.7.0` (locked 12.7.0) →
`node_modules/node-forge` (locked 1.4.0). One edge, one consumer.

**REACHABLE? NO — re-derived at HEAD rather than quoted from batch 23:**

```
grep -rn "require(['\"]node-forge" node_modules/firebase-admin/lib
  -> 1 hit  : lib/app/credential-internal.js:148
grep -rno "forge\.[A-Za-z.]*"      node_modules/firebase-admin/lib
  -> 1 hit  : lib/app/credential-internal.js:150  forge.pki.privateKeyFromPem
```

The whole of the call site:

```js
const forge = require('node-forge');
try { forge.pki.privateKeyFromPem(this.privateKey); }
catch (error) { throw new FirebaseAppError(INVALID_CREDENTIAL,
                  'Failed to parse private key: ' + error); }
```

**The return value is discarded.** It is a parse check on *our own* private key
from *our own* env var, used only to turn a malformed key into
`INVALID_CREDENTIAL`. The advisory is about **signature verification** accepting
extra nested data — `node-forge`'s `lib/rsa.js` verify path, which is present in
the installed tree and **has no caller in firebase-admin at all**. So the
vulnerable code is installed and unreachable through this dependency.

**FIXED VERSION: none for node-forge.** `npm view node-forge version` → **1.4.0**,
which is what is installed; the advisory range is `<=1.4.0`. The only offered fix
is `firebase-admin@14.5.0` with `isSemVerMajor=true` — a **major bump of a direct
dependency**, not a lockfile edit.

**SO NOTHING IS LOCKFILE-ONLY AND NOTHING WAS FIXED.** The lock is byte-verified
untouched:

```
package-lock.json sha256 9c6833b5951d4a6f83190c675eec9a56f355dfaabb79166e3602265dafc99ed0
                  bytes 85031
git diff --stat package-lock.json -> empty (identical to HEAD)
last touched by   a1386313 2026-10-07 "the busboy moderate, applied"
```

**WAIT holds**, on the same four triggers, with the reachability half now
re-derived at this HEAD rather than carried.

## item 8 — DONE, two halves. ITEM 15 found with evidence; the reseat narrowing REVERSED.

### (a) What ITEM 15 was — found, not guessed

`docs/2026-10-06-cody-routed.md` has no `## ITEM 15` body, and **its own routing
table at line 11 names it**:

```
| docs/METHODOLOGY.md | fourth | ITEM 15 — three conventions + three more |
```

So the item was not lost, it was **routed and its section never written** — the
table row points at a heading that does not exist in that file. The content is
in a different document: `docs/2026-10-06-cody-queue17-inventory.md:182`,
under `## METHODOLOGY (ITEM 15)`. Line 84 of the routed doc also refers to
*"the rule item 15(b) exists to make a habit"*, which is the second cross-check
that the item existed and had sub-parts.

**ITEM 15 was three new methodology conventions plus three earlier ones owed for
promotion**, all for `docs/METHODOLOGY.md`, which is **fourth's**:

- **(a) A fix that closes named instances leaves the mechanism open.**
  Re-measure the population that produced the defect, not the instances it
  named. Evidence: *"162 of 169"* on 10-05 became **169 of 521** on 10-06 once
  the universe was a `git ls-files` glob — the hole was **352 rules in 105
  files**, not 7 in one. It repeated inside that same batch: 7 undecoded
  `subprocess` sites of mine fixed while the tool still reported **64** in other
  sessions' files.
- **(b) Every figure carries its denominator, command, commit and date.**
  *"49 dead rules"* means nothing without *of 540, by `dead_rule_sweep.py`, at
  `8f204050`, 2026-10-06*. Three of my own documents reported that sweep **with
  no exit code at all**. Re-running instead of quoting changed two answers in
  that batch.
- **(c) A tier that clears a category and finds nothing in it is the outcome to
  distrust.** The writer tier first reported **22 of 22 exercised, 0 dead**; the
  arm built with it failed, the cause was the digest including the tool's own
  mutated source, and after the fix it was **17 exercised, 5 DEAD** — the
  blanket pass had been hiding five real findings.
- **plus the three from queue 16**, the trailing-echo rule among them, which
  were written into a dated inventory and routed for promotion and **were still
  sitting there** — reported as a gap by that document itself.

**STILL OWED, and `docs/METHODOLOGY.md` is not mine:** these six are routed, not
promoted. **NEXT STEP:** hand them to whoever holds that file; they are
paste-ready in the inventory doc.

### (b) The weak-basis reseat call — **REVERSED**

**The claim, from batch 23's handoff §C.4 and its commit message:** *"this is the
`--post-rewrite` path and it produced a ONE-LINE diff … so the routed finding
narrows: `--post-rewrite` is minimal and correct; `--reseat` is the one that
re-serialises the file."* Basis: **one observation.**

**Re-derived at HEAD. It is wrong, and both commands share one writer:**

```
command : read tools/defect_register.py at HEAD + compare the stored file to json.dumps
commit  : 7ce70c6c        date: 2026-10-07

cmd_post_rewrite calls save()  : True
cmd_reseat       calls save()  : True
save() is        json.dumps(d, indent=2, sort_keys=False) + '\n'

docs/defect-density-register.json as stored : 2,085,776 bytes, 25,432 lines
  dumps(indent=1) byte-identical to stored  : False  (1,991,645 bytes)
  dumps(indent=2) byte-identical to stored  : True   (2,085,776 bytes)
  dumps(indent=4) byte-identical to stored  : False  (2,274,038 bytes)
```

**There is one write path, not two.** The diff I saw was one line because the
stored file already matches `indent=2` exactly — not because `--post-rewrite`
writes narrowly. The 24,724-line diff in the original incident came from a file
stored at **indent=1**, and at that moment **either** command would have
produced it; today **either** command produces a minimal one.

**VERDICT: REVERSE.** The narrowing is withdrawn and the finding routed to cc
stands at full width: the defect is in `save()`, which re-serialises the whole
register on every write, so "minimal diff" is a property of the stored file
happening to match the serialiser and not a property of the command. The next
writer that stores it differently makes every subsequent write a whole-file
diff again.

**Cause-tag for my own wrong narrowing: lifecycle = verification, sub-phase =
evidence sufficiency, specific cause = a structural claim about two code paths
drawn from a single observed diff without reading either path.** The convention
that would have caught it is item 15(b) above, the one I had already written
down — *re-run instead of quoting*, extended to *read the code instead of
inferring it from one output*.

## item 12 — DIAGNOSTIC. **I cannot run `/context`, and I am not going to estimate one and call it a breakdown.**

`/context` is a **built-in CLI command**, not a skill and not a tool. Nothing in
my tool surface invokes it — the skill list does not contain it, and the harness
exposes no equivalent. Inventing a plausible-looking breakdown would be the
fabricated-KPI shape this platform has a whole check for.

**ASK: Michael runs `/context` in this session and pastes the output.** That is
one keystroke and it is authoritative.

**WHAT I CAN MEASURE, and did** (`scratchpad/b24/i12_i13.txt`, 2026-10-07):

| auto-loaded input | bytes | est. tokens |
|---|---|---|
| `~/.claude/CLAUDE.md` (global) | 1,345 | ~336 |
| `CLAUDE.md` (project) | 17,618 | ~4,404 |
| `MEMORY.md` (auto-memory index) | 2,604 | ~651 |
| **subtotal, always loaded** | **21,567** | **~5,391** |

Not auto-loaded but large when pulled in:

```
62 skill directories with a SKILL.md, 1,194,836 bytes on disk total
  sairn-hover-auditor      283,729   (never loaded by me -- out of my scope)
  design-taste-frontend     87,253
  sairn-guardian-v2         77,363   <- I DID load this in batch 23, ~19k tokens
  claude-api                72,136
  graphify                  43,292
```

**The biggest identifiable single consumer in my recent history is a skill body
I invoked**, not the standing files: `sairn-guardian-v2` at 77,363 bytes is 3.6×
the whole auto-loaded set. Other known consumers this session are the
`SessionStart` dispatch block, the four `WORK CLAIMS` task texts (cc's alone is
~4,600 characters), and the deferred-tool listing — all of which arrive before I
act and none of which I can size from inside.

**Token columns are estimates and say so:** `bytes // 4`. There is no local
tokenizer for this model, so bytes are the measurement and tokens are derived.

## item 13 — DIAGNOSTIC. CLAUDE.md size, measured.

```
command : byte/char/word/line count over both files
commit  : 7ce70c6c        date: 2026-10-07

GLOBAL   ~/.claude/CLAUDE.md    1,345 bytes   1,339 chars    190 words   12 lines  ~  336 tok
PROJECT  CLAUDE.md             17,618 bytes  17,505 chars  2,614 words  308 lines  ~4,404 tok
                               ------
TOTAL                          18,963 bytes                                        ~4,740 tok
```

Token figures are `bytes // 4`, labelled as estimates for the reason above. The
project file is **13× the global one** and is the one worth watching; it is
already split, with the judgment half in `docs/SAIRN-PROCESS-RULES.md`, which is
**not** auto-loaded.

## item 14 — DIAGNOSTIC. Capture is RAW to disk, reads into the window are FILTERED. Measured, with one change made.

**What the practice actually is, evidenced rather than asserted.** This batch
wrote **224,970 bytes** of raw program output to
`scratchpad/b24/`, 29 files plus the run directory:

```
claim2.out            45,519     i10_all.txt       27,755
suite.out + wrapper   36,673     i10_ordered.txt    7,726
i10_scan.txt          13,763     i10_percall.txt    7,115
i5_live_procs.txt     10,016     i5_wt_before.txt   3,510   ... 29 files
```

**None of the four largest was read whole.** They were reached with `wc -l`,
`grep`, `tail -N`, `sed -n 'a,bp'` and small Python extractors. So the shape is
already the right one: **the full artefact stays on disk and is citable; a
filtered slice reaches the window.** Exit codes come from `capture_exit.py`
`.status` files, never from a shell pipeline — the `exit_status_attributable`
hook fires on every such command and was heeded each time.

**One honest exception:** `head -40 claim.out` pulled ~4.6 KB of a claim refusal
in whole, deliberately, because the refusal text *was* the finding for item 1.

**WHAT CHANGED.** Suite output was still being reached ad hoc (`tail -2`,
`wc -l`). From here it goes through one fixed filter, so a 785-line run costs a
dozen lines instead of a judgement call each time:

```sh
# the standing read for any run_all_tests.py / probe output
grep -E '^(FAIL|ERROR|[0-9]+ (ARM|FAILING)|EXIT|RAN:|THE (TREE|SUITE))' <out> ; tail -3 <out>
```

That is the change: **a named filter instead of an improvised one**, applied to
the item-3 result below.

## item 15 — DIAGNOSTIC. No whole-file read over ~1000 lines this batch. Audited, not assumed.

**Every large file reached this batch, and how:**

| file | lines | how it was read |
|---|---|---|
| `docs/defect-density-register.json` | **25,432** | Python, in-process; only counts and one record's keys reached the window |
| `SAIRN-ACTIVE-WORK-cody.md` | **7,108** | `grep`, and read in-process by the attribution scanner |
| `docs/handoff-cody-2026-10-07.md` | 1,148 | `grep` + `sed -n` ranges |
| `tools/run_all_tests.py` | ~1,200 | `grep -n` then `sed -n '694,716p'`, `'826,840p'` |
| `tools/defect_register.py` | ~2,100 | `grep -n` then three `sed` ranges |
| `tests/run_tier_a_review_gate_probe.py` | ~2,260 | `grep -n` + `Read` with `offset`/`limit` |
| `docs/2026-10-06-cody-routed.md` | 635 | `grep -n '^#+ '` for structure, then two `sed` ranges |
| `.claude/claims/*.json` | 191 KB–209 KB | Python, in-process; only the active claim's fields printed |

**Zero violations.** The structural habit that produces this: **ask for the
shape first** (`grep -n '^#\+ '`, `grep -n 'def '`, `wc -l`), then open only the
range the shape points at. A whole-file read of a 25,432-line register would
have been both useless and a truncation risk — `sairn-context-budget`'s rule
that a truncated read is indistinguishable from a complete one.

**PROACTIVE COMPACTION, adopted from here.** Between queue items, not when the
window forces it. **What must survive a compaction, in this order:**

1. **Claims held** — `cody / Tooling`, batch 24, and the exact FILES list, plus
   the fact that `docs/tier-a-reviews.json` is **cc's** and not mine.
2. **Committed/pushed SHA** — the last pushed sha and whether the tree is clean,
   read from `git ls-remote` not from a push message.
3. **The next item and its exact next step** — including anything mid-flight:
   the pinned suite's status-file path, and the saved
   `i10_run_all_tests.patch` that is **reverted in the tree on purpose** and must
   be re-applied after the run.
4. **The two scratchpad paths** — `scratchpad/b24/` and the transcript root, so
   every figure above stays citable.

Items 1–15's own state does not need preserving in context: it is in this file,
written per item, which is what item 2 is for.

## item 11 — DONE. Every defect confirmed this batch, cause-tagged.

Tags are *(lifecycle phase / sub-phase / specific cause)*. `unknown` is used where
it is the honest answer rather than filling the column.

### D1 — `tools/run_all_tests.py:835` left `ignore_errors=True` on the checkout-FAILURE path

- **confirmed:** yes, by reading the site; the success path 68 lines below had
  already been fixed on 2026-10-07 and the `_force_rm` helper sits 134 lines
  above both.
- **tag:** *implementation / incomplete-fix-propagation / a fix was applied to
  the branch the author was looking at and not to the sibling branch in the same
  function.*
- **why it survived review:** the commit that added `_force_rm` cited the success
  path by line and was correct about it. Nothing compared the two call sites.
- **fixed:** yes, with the existing helper plus the same leftover-file NOTE.
- **mechanism still open:** every other tool with two exit paths out of one
  resource acquisition. Not swept.

### D2 — my own batch-23 narrowing of the `defect_register` reseat finding was wrong

- **confirmed:** yes. Both `cmd_post_rewrite` and `cmd_reseat` call the same
  `save()`; the register is byte-identical to `json.dumps(indent=2)`.
- **tag:** *verification / evidence-sufficiency / a structural claim about two
  code paths drawn from one observed diff, without reading either path.*
- **why it survived:** the observation was real and the inference was not
  labelled as an inference. A one-line diff is consistent with both "this command
  writes narrowly" and "the stored formatting happens to match the serialiser",
  and only the second is true.
- **fixed:** the claim is **reversed** in item 8(b); the routed finding is
  restored to full width. No code change — the file is cc's.
- **mechanism still open:** nothing checks that a narrowing in a handoff was
  derived from more than one observation.

### D3 — my own leak-class predicate over-counted by 26 calls

- **confirmed:** yes, by reading two of its own hits.
- **tag:** *detection / predicate-ordering / a positional predicate written
  without position — "the identifier appears on a git-creating line" cannot tell
  a pre-create delete from a post-create cleanup.*
- **why it nearly shipped:** 26 extra findings in the *safe-looking* direction.
  A number that is too high reads as thoroughness.
- **fixed:** pass 3 requires the repo-creating line to precede the removal, and
  the exclusion is stated in the output rather than silently applied.
- **and a second correction inside the same item:** the class was narrowed again
  by **measurement** — an `init`ed repo dir has 3 of 33 read-only files, a linked
  worktree dir has **0 of 2** — which moved 5 more calls out.

### D4 — `docs/2026-10-06-cody-routed.md` has a routing-table row for a section that does not exist

- **confirmed:** yes. The table at line 11 routes ITEM 15 to
  `docs/METHODOLOGY.md`; there is no `## ITEM 15` heading in the file.
- **tag:** *documentation / index-body divergence / a summary table written
  separately from the sections it indexes, with nothing checking that every row
  has a body.*
- **fixed:** no. The content exists in
  `docs/2026-10-06-cody-queue17-inventory.md:182` and is restated in item 8(a).
  The routed doc is not in this batch's declared FILES.
- **note:** this is the same shape as the platform's own repeated
  *"count written in prose next to a list that disagrees with it"* — an index
  that is not derived from what it indexes.

### D5 — the 20-file SQL runbook's three counts disagree (20 / 24 / 7)

- **confirmed:** yes — title says 20, `grep` finds 24 distinct `sql/` paths, the
  numbered table has 7 rows.
- **tag:** *documentation / undefined denominator / three different populations
  counted under one noun ("the SQL files") with no definition of which.*
- **fixed:** no, and deliberately. Item 9 asked for **push status**, which is
  settled; the count is a content question for the runbook's owner, and
  "correcting" it would mean choosing which of three populations is meant.

### D6 — a claim-file read reported no holder while the registry had one

- **confirmed:** yes. `.claude/claims/cc.json` in this clone showed no active
  claim; `sairn_claim.py` refused with *"cc held … (registry, not yet on origin)"*.
- **tag:** *process / staleness-of-a-local-replica / the claim record is only as
  fresh as the last push, while the registry is live — and a per-file read of the
  replica cannot see the difference.*
- **whose:** not a defect I introduced and not mine to fix. It is the exact
  failure `CLAUDE.md` already warns about for the claim record versus the shared
  status registry; what is new is that **my conflict check used the stale half**.
- **fixed:** my own method, yes — the conflict check now goes through
  `sairn_claim.py` and the file read is treated as corroboration only.

### D7 — the batch's own premise about who held the Tier A ledger

- **confirmed:** yes, wrong at HEAD: fourth's blocking claim was released.
- **tag:** *process / premise-staleness / an instruction written against a claim
  state that changed between writing and execution.*
- **fixed:** reported and worked around; the real holder was found by the matcher
  and not overridden.
- **note:** this is convention 10's *no long run whose first check is at the end*
  applied to instructions rather than to runs — the premise was re-derived before
  acting, which is the only reason the wrong session was not blamed in a standing
  document.

### Not defects, recorded so the list is not read as exhaustive-by-silence

- The **29 worktree registrations** (item 5) were abandoned state, not a defect in
  any tool's logic; the one locked registration is an interrupted `worktree add`.
- The **node-forge advisory** (item 6) is a real upstream vulnerability with **no
  patched release**, not a defect in this repo. Its reachability verdict is
  re-derived, not inherited.

## interleaved task — DONE. The one-field fixture for `opened_at_sha_basis`, 11 new arms.

Asked for mid-batch, not part of the 16. cc's batch confirmed the item-8 fix
landed and recorded it **UNPROVEN**, because at that moment the measurement was
`0 of 238 records carry the field` — nobody had run `--open` since. That is the
state in which a field quietly stops being written and nothing notices.

```
command : python tests/run_tier_a_review_gate_probe.py
commit  : f8d73c48 + this change        date: 2026-10-07
result  : EXIT 0, ALL ARMS PASS, 236 ok  -- 2 runs, first EXIT 0 each time
          (224 arms before this change, 236 after: 11 new, +1 NOTE line)
```

**IT LIVES IN THE PROBE THAT IS ALREADY IN MY DECLARED FILES.** A new
`tests/run_tier_a_basis_probe.py` would have been cleaner to read and would have
widened the claim without declaring it — the same thing I declined to do for item
10's six files an hour earlier. Consistency won.

**(A) "BY ANYBODY" IS TESTED AS WRITTEN.** `session_name` is the only thing in
the write path that varies by who runs it, so the fixture rebinds it and drives
`_open_record` as **`somebody-else`**, then asserts both the basis *and* that the
record really was attributed to that session — otherwise the arm would be quietly
testing my own name.

**(B) AND THE OTHER BRANCH, or a writer that hardcoded `'file-set'` would pass
everything above:** a record naming no files must get `'head'`, and a third arm
asserts the two fixtures really returned different values.

**(C) THE STANDING LEDGER RULE — the part that answers cc.** Every record opened
**after the fix landed** must carry a basis that is in vocabulary and consistent
with its own fields: `file-set` ⇒ files non-empty, `head` ⇒ files empty,
`could-not-tell` ⇒ no sha stamped. One field; it deliberately does **not**
re-check the sha against the files, which is the historical 34-of-63 problem and
depends on what a given clone can resolve.

**THE CUTOFF IS DERIVED FROM CONTENT, NOT A HARDCODED SHA.** `18078d38` was
itself the *post-rebase* sha of that fix, and a literal sha here would resolve
today and silently stop resolving later — exempting every record and passing.
`git log --reverse -S 'def subject_sha(' -- tools/tier_a_review_gate.py` finds the
introducing commit instead; derived this run as **`2026-10-07T13:14:59-04:00`**.
A cutoff that cannot be derived **fails** rather than exempting the ledger.

**COVERAGE IS DISCLOSED, NOT ASSERTED, and this is the one judgement call.** The
rule currently examines **0 of 238** records — all 238 predate the cutoff. The
first version of this made that a FAILING arm; it was changed, because no code
change can clear it (only the next real `--open` can) and reddening a shared
suite on an unfixable condition gets the file muted, which is worse than a loud
line. So it prints:

```
  NOTE  the ledger rule examined 0 of 238 record(s); 238 predate the cutoff and are exempt.
        NOT YET EXERCISED BY REAL DATA -- ... the first real --open changes this number.
```

**Three arms stop that from becoming a check that tests nothing:**

- the **planted set** — 5 bad shapes (absent, out-of-vocabulary,
  `file-set`-with-no-files, `head`-when-derivable, `could-not-tell`-with-a-sha),
  all 5 caught, which proves the rule can say NO;
- **the ledger arm's own data path** — the real record list **plus one** bad
  post-cutoff record must yield exactly one more violation than the real list
  alone, so a clean verdict over real data is a measurement rather than a masked
  rule;
- **the exemption counted a second way** — `exempt` must equal an independently
  computed count of records whose `opened_at` really predates the cutoff, so the
  exemption cannot be a blanket.

**ISOLATION FROM THE RUNNING PINNED SUITE, verified rather than assumed:**

```
suite.status            still RUNNING 74488, suite.out advanced 371 -> 431 lines
worktree registrations  2 before, 2 after
core.bare               false
.git/config sha256      93070fe59db2... unchanged
tierA_basis_* temp dirs left behind : none
docs/tier-a-reviews.json : READ ONLY, never written (it is cc's)
```

The fixture uses `tempfile.mkdtemp` + `git init` — **no worktree**, so it cannot
touch this clone's shared `.git/config` — and cleans up with the chmod-retry
`onerror` helper rather than `ignore_errors=True`, with an arm asserting the
tempdir is gone. The change is committed immediately so the pinned run's own
residue check stays attributable to the suite.

**ALSO SEEN, not acted on:** four `sairn-suite-pinned-*` directories exist in
`%TEMP%`; only `w8n86z0u` is mine and live. The other three are earlier or other
clones' leftovers, and they are **not** worktree registrations so item 5's prune
had nothing to do with them. Reported, not deleted.
