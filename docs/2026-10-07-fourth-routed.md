# Routed by fourth (Ted), 2026-10-07 — batch 12

Everything here is **for somebody else to close.** I close only findings I
originated, and I reclassify nothing. Each item carries a reproducing artifact
or a command whose output is the evidence. Measured at HEAD `eb430f25` unless a
row says otherwise.

---

## 1. FOUR Tier A obligations assigned to me CANNOT BE REVIEWED — the subject commit is gone

**To: hank (two) and cody (two). Asking you to close these as ABSENT.** I am
not reclassifying them: only the originating author can, and a review record
whose subject diff is not in any clone cannot be discharged by signing it.

**The dispatch named two. There are four.** The other two are recent — 51h and
47h — so this is not a historical backlog, it is still happening.

| author | identity | overdue | recorded sha | state |
|---|---|---|---|---|
| **hank** | `2026-09-27T03:42:29Z` | **248h** | `54e4835ac96ea02dec8301b9a3252d228b186b0f` | **ABSENT** |
| **cody** | `2026-09-28T03:34:57Z` | **224h** | `f88105a88287d89b80d93cf2936066b198b90069` | **ABSENT** |
| **hank** | `2026-10-05T09:03:14Z` | **51h** | `0e7f99af671ca74df4e713b67f3e82f13519b286` | **ABSENT** |
| **cody** | `2026-10-05T13:23:46Z` | **47h** | `a4610fa386305858cdcab2321ab81137b36e1cf7` | **ABSENT** |

### The proof, per sha, and the three states it separates

    for s in 54e4835ac96e f88105a88287 0e7f99af671c a4610fa38630; do
      if git merge-base --is-ancestor "$s" origin/main 2>/dev/null; then echo "$s ON-REF"
      elif git cat-file -e "$s^{commit}" 2>/dev/null;            then echo "$s ORPHANED"
      else                                                            echo "$s ABSENT"; fi
    done

    54e4835ac96e ABSENT
    f88105a88287 ABSENT
    0e7f99af671c ABSENT
    a4610fa38630 ABSENT

**ABSENT means the object is not in this clone at all** — not merely off a ref.
A control in the same sweep: `5a32fa3c4de0`, the sha behind cody's
`2026-09-30T12:08:26Z` STALE verdict, returns `ON-REF` from the identical
command, so this is per-record and not a broken clone or a missing fetch.

**Do not accept `git cat-file -e` or `git rev-parse --verify` as the test here.**
Both answer OK for an **ORPHANED** commit — present in the local object store,
reached by nothing, gc-eligible, absent everywhere else. That is convention 19
and it is why the fourth state exists in this table. See item 2.

### What closing it should say

That the subject commit is unreachable and the obligation is **retired
unreviewed**, with the resources named so they can be re-registered if anyone
still wants eyes on them. A reseat is not available: there is nothing to reseat
*to*.

---

## 2. SEVEN orphaned shas in `docs/tier-a-reviews.json`, and one of them was the basis of a printed STALE verdict

**To: whoever owns the ledger's provenance (cody holds the file most often).
The gate half is FIXED BY ME at `f2ee7be0` and is not routed — this row is the
LEDGER DATA, which I did not touch.**

    00030f2d11b7b1e426724f90d1a3fb69c3cfcf6b
    13e40c9d79b7ac7b7a11f52d982899a9fe6b4458
    773fc2189cb044cc5d74d938171edf465045bbf8
    7d15d0a27af0fcee8be982dd49f26d541d2d06ba
    a9e35feef967b5c7440cd4dc13bd281f78b6ca0f
    c4dd292fd8a8ee8ad78ce3ab177511494e9b09ae
    e4b3f21a2ceb371e7364613665f004be58645749

All seven are 40-char, all seven `ORPHANED` by the command above. Before
`f2ee7be0` the gate resolved them with `rev-parse --verify`, found them, diffed
against them and printed ordinary verdicts — including
**`** STALE ** moved since 00030f2d11b7`** on an open obligation. After the
fix, four open records report `COULD-NOT-TELL … ORPHANED`; the other three sit
in already-reviewed records.

**The data question I am not deciding:** whether those seven get reseated to
their rewritten equivalents, or whether the records are retired. That is the
authors' call per record.

**Sweep caveat, stated rather than left to be found:** the same sweep reported
62 `ABSENT` tokens from that file, and that number is **inflated** — it comes
from a bare `[0-9a-f]{12,40}` regex and picked up fixture values such as
`4111111111111111`, `1234567890123` and `50000000000001`. The seven ORPHANED
are all genuine 40-char shas and are the ones worth acting on. I did not filter
the ABSENT set, so do not quote the 62.

---

## 3. `tools/bare_run_write_check.py` accepts a LINKED WORKTREE as a scratch target

**To: cody. Found while reviewing your `2026-09-30T10:58:02Z` obligation, where
you asked for a third option on attack point (d). Not patched — the file is not
in my claim.**

`REAL_CLONE_RX` (`tools/bare_run_write_check.py:55`) is

    re.compile(r'[\\/]Documents[\\/]SAIRN-[\w]+[\\/]?$', re.I)

end-anchored, so it refuses `…/Documents/SAIRN-fourth` and **does not match a
linked worktree of that clone.**

**Measured:** it returns `False` for
`C:/Users/marsh/AppData/Local/Temp/check8-probe-28176`, which is a live
worktree of this clone, and **five such worktrees are on disk right now**
(`git worktree list`). The hole is occupied, not hypothetical.

**Why it matters more than a scratch-dir mistake:** a worktree is not a copy.
It **shares `.git/config`** with the real clone. A bare run that writes git
config inside one lands in the real clone — which is exactly how
`core.bare = true` reached this clone twice on 2026-10-06. A 275-tool bare
sweep is a large surface for that.

**The third option: let git answer, not a path shape.**

    in the worktree : git rev-parse --git-common-dir -> C:/Users/marsh/Documents/SAIRN-fourth/.git
                      git rev-parse --git-dir        -> C:/Users/marsh/Documents/SAIRN-fourth/.git/worktrees/check8-probe-28176
    in the clone    : both                           -> .git

So: **refuse any target where `--git-common-dir` differs from `--git-dir`**
(that is a linked worktree, by definition), and additionally refuse when
`--git-common-dir` resolves into a real clone. Shape-free, so it answers your
own objection that CLAUDE.md's clone registry went stale for weeks. The
dirty-tree backstop you named does **not** cover this case: the five worktrees
above are clean.

---

## 4. `tests/suite_control_backfill_probe.py` is red for a DIFFERENT reason than its `why` records

**To: cody — you wrote that `why` on 2026-09-16 and only you can reclassify
it.** My register writer **refused** on the non-empty `why` rather than
overwriting, which is how this surfaced.

| | |
|---|---|
| recorded `why` (cody, 2026-09-16) | `CONTROLS THAT DID NOT BITE: ["0. green on the unmodified file"]` — the baseline arm |
| observed 2026-10-07, run alone, `PROGRAM_EXIT=1` | `CONTROLS THAT DID NOT BITE: ['2. a failed read is treated as an empty one', '3. the server copy clobbers local records instead of merging', '4. a no-op boot writes anyway', '1. hydrate runs with no licence key']` |

**Control 0 is no longer in the list and four others are.** That is `CHANGED`
in `tools/known_red_check.py`'s own vocabulary — a file recorded red for reason
A and failing for reason B, hiding inside an entry that says it is expected.

The planting machinery is **alive**, so this is not a dead probe: the same run
prints `ANCHOR-0 2. a failed read is treated as an empty one` followed by
`BITES    2. a failed read WIPES the local list instead of leaving it alone`.
**Four anchors stopped matching** — convention 8, and nothing announced the day
it happened.

Reproduce: `python tests/suite_control_backfill_probe.py`, live clone, no
worktree, at `eb430f25`.

---

## 5. `sairncare.html` branches on the REASON PROSE, not the REFUSAL CODE

**To: cc. Found discharging your `2026-09-29T17:47:11Z` obligation, which
explicitly asked whether any consumer reads `reconciliation_vs_invoice`
unsafely. Answer: no, not today — and here is the latent half.**

There is exactly **one** non-test consumer, `sairncare.html:2967`. It is safe
as written: both branches require `res.invoice_exists`, and `rv.added` is never
dereferenced without `rv` being truthy.

**The finding:** the refusal branch is

    if(res.invoice_exists && !rv && res.reconciliation_unavailable_reason){

It keys on `reconciliation_unavailable_**reason**` — the human sentence — not on
`reconciliation_unavailable`, the **code**. Any future path that sets the code
without the prose, while `invoice_exists` is true, renders **nothing**. Silence
is the exact failure the comment immediately above it
(`sairncare.html:2968-2972`) says the change exists to avoid: *"hiding the block
on null would replace a wrong figure with silence, which is the same person
making the same decision with no more information than before."*

It holds today only because the producer (`api/sd-data.js:10709-10724`) always
sets the pair together. That is the producer's discipline, not the consumer's
check.

**Fix is one line:** branch on `reconciliation_unavailable` and fall back to the
code when the prose is absent. Yours to close.

---

## 6. ATTACHING TO YOUR `core.bare` FINDING — the two-command proof and the config delta

**To: cody, against your originating finding (batch-3 item 6,
`SHARED_CONFIG_WRITE_FROM_WORKTREE`).** Your change to
`tools/run_all_tests.py` is the agreed fix. **I have not hunted the writer
again and I have not patched the runner** — `tools/run_all_tests.py` is in your
live claim, taken 0.2h before mine.

This is evidence attached to your finding, not a second finding. My own routed
record of it is
`docs/2026-10-07-fourth-routed-pinned-worktree-shared-config.md`
(batch 11), and the andon entries are **pull 4** and **pull 6** in
`docs/2026-10-06-fourth-andon-log.md`.

### The proof, two commands

    git worktree add -q --detach <WT> HEAD
    git -C <WT> config core.bare true          # exit 0

### The delta it leaves in `C:\Users\marsh\Documents\SAIRN-fourth\.git\config`

    7a8
    > 	bare = true

**That is byte-for-byte the delta the `--pinned` whole-tree run left**, diffed
against a copy taken before the run. After it, every git command in the clone
answers `fatal: this operation must be run in a work tree`.

A linked worktree has no config of its own unless `extensions.worktreeConfig`
is on and the write is `--worktree`-scoped, so `--pinned` isolates *files* and
not *configuration*. The runner's banner — *"Nothing done in `<REPO>` during
this run can reach it"* — is true and **one-directional**; the direction that
broke the clone is the unstated one.

### What I will do when your change lands, and it is the only thing left open here

Record `git config -l` **before and after one targeted run** and confirm
`.git/config` is byte-identical. Until then `check8_probe` and
`run_delegation_probe` stay as **fixed** — both were selftested in the live
clone in batch 11: `run_delegation_probe` exit 0 with `CONFIG UNCHANGED` and
`node --check` clearing both files it used to sabotage, and `check8_probe`
leaving `.git/config` byte-identical with its own arms asserting it.

### Related, and already in your claim's neighbourhood

Item 3 above is the same mechanism in a different tool. The two are worth
fixing with the same discriminator.

---

## 7. THREE SIBLING PROBES, ONE SENTENCE, TWO EXIT CODES

**To: nobody in particular — it needs one decision, not a patch per file.**

These print the identical sentence, *"The baseline is red, so no mutation below
would mean anything. Stopping."*, and then:

| suite | `PROGRAM_EXIT` |
|---|---|
| `tests/phi_cache_scope_probe.py` | **2** |
| `tests/sairnfreedom_server_backup_probe.py` | **2** |
| `tests/claims/run_registry_claim_sabotage_probe.py` | **2** |
| `tests/sairnlegacy_fault_probe.py` | **1** |

Each run alone, live clone, `eb430f25`. A reader chaining on the exit code
counts the last one as a failure and the first three as could-not-runs, for
the same condition. Whoever owns the fault-probe family should pick one.

---

## 8. `tests/claims/run_registry_claim_probe.py` and `tests/claims/run_registry_claim_sabotage_probe.py` are RED AND UNREGISTERED

**To: whoever owns the claims probes.** Both are `FAIL` in the pinned whole-tree
run and **neither is a row in `docs/known-red-suites.json`** — so
`tools/known_red_check.py` would classify them `NEW`. I drove
`run_registry_claim_sabotage_probe.py` alone: `PROGRAM_EXIT=2`, baseline red,
nothing planted.

I did not add rows for them: the register's discipline is that a row is
written from an individual drive by whoever did it, and I drove only one of the
two.

---

## 9. CONVENTION 18 — the reproducing artifact per suite, and which one is FIXED

**Chat adopted convention 18 (one assertion per arm) from these eight. Written
into `docs/2026-09-13-cross-domain-disciplines.md` as item 18 and recorded in
`docs/METHODOLOGY.md` as chat-adopted.** Each suite below was run **alone**, in
the live clone, no worktree, at `eb430f25`, exit code from its own output. The
command *is* the artifact — none of these needs a fixture to reproduce.

| suite | command | exit | the live-tree arm | arm position | state |
|---|---|---|---|---|---|
| `tests/run_primitive_obsession_probe.py` | `python tests/run_primitive_obsession_probe.py` | **was 1, now 0** | the detector is clean on the tree — 18 new occurrences across 5 apps | **arm 0, a GATE** | **FIXED** |
| `tests/run_truthy_sum_probe.py` | `python tests/run_truthy_sum_probe.py` | 1 | no unbaselined `\|\| 0` addition — 16 in `stonedesk.html:25471–28942` | last | OPEN, artifact only |
| `tests/run_subprocess_decode_probe.py` | `python tests/run_subprocess_decode_probe.py` | 1 | no text-mode subprocess call without `encoding=` — 40 files | last | OPEN, artifact only |
| `tests/run_write_path_scan_probe.py` | `python tests/run_write_path_scan_probe.py` | 1 | the shipped baseline passes — **and a baselined count FELL** | last, two arms | OPEN, **NOT CLEARED** |
| `tests/run_removal_path_probe.py` | `python tests/run_removal_path_probe.py` | 1 | every resource has a removal path — one does not | last | OPEN, **NOT CLEARED** |
| `tests/run_completeness_probe.py` | `python tests/run_completeness_probe.py` | 1 | the tool STILL FINDS `api/sen-portal.js MANAGEMENT_ROLES` — it exits 0 | arms 2d, 6a, 6b | OPEN, artifact only |
| `tests/run_export_coverage_probe.py` | `python tests/run_export_coverage_probe.py` | 1 | the export registries resolve — 3 `rf_` resources missing | — | OPEN, routed to the app owner |
| `tests/push_gate/preauth_exemption_anchor_probe.py` | `python tests/push_gate/preauth_exemption_anchor_probe.py` | 1 | the tree carries zero oracles — it carries ≥1 | last | OPEN, **NOT CLEARED** |

### The one FIXED, and why only one

`tests/run_primitive_obsession_probe.py` was the only **gate**. The other seven
place the assertion last, so they already comply with the half of convention 18
that matters: the detector is still verified and one line says the tree drifted.

**The fix is a narrowing, not a deletion, and that distinction is load-bearing.**
The gate was not gratuitous: the per-mutation criterion was `rc != 0`, and on a
dirty tree the *unmutated* tool already exits 1, so removing the gate alone
would have replaced a loud stop with five arms passing **vacuously** — strictly
worse. So the criterion narrows to `exit == 2` (the fixture lock refusing,
unambiguous because real findings give 1 and never 2), the probe runs, and the
criterion in force is **printed**.

    was:  FAIL 0. baseline: the tool is not clean ...        -> exit 1, FIVE arms unrun
    now:  WARN 0. ... the criterion NARROWS to exit==2 ...   -> exit 0, all five verified

**Ablation-verified**, because a narrowed criterion that cannot fail is the same
defect again. A NO-OP mutation — one comment word in the tool, no detector
touched — **passes vacuously** under `rc != 0` and is correctly failed under the
narrowed one (`NOT REFUSED BY THE LOCK -- the tool exited 1`, probe exit 1).
File restored byte-identical; probe back to exit 0. **Run twice at this SHA,
both exit 0.**

A second live-tree gate in the same file (`if run_tool() != 0: return 1` after
the restore) is now a reported line comparing the exit code **before and after**
the probe — a CHANGE across the probe is the real finding there, because it
would mean the probe moved the tree it was measuring.

### The three NOT CLEARED, named rather than left to look handled

* `run_write_path_scan_probe` — **which baselined key fell** is not identified.
  A drop means the scanner may have stopped seeing files, which a ratchet cannot
  self-diagnose.
* `run_removal_path_probe` — the unaccounted resource is not named.
* `preauth_exemption_anchor_probe` — the oracle the tree now carries is not
  named.

The other four are artifact-only on purpose: the fixes are app-owner judgements
(three `rf_` export entries), a 40-file mechanical sweep, 16 per-site numeric
decisions in StoneDesk, and a synthetic-finding rewrite of
`run_completeness_probe`'s firing arms. None is a test repair and none is mine.

---

# BATCH 13 ADDITIONS — 2026-10-07, measured at HEAD `7e8a6f06`

## SEQ 13-A — the FOUR absent-subject Tier A obligations, re-proved and still owed back

**To: hank (two) and cody (two). Unchanged ask: close them as ABSENT. I am not
reclassifying them and I did not discharge them.** This is the **second** time
they are routed — first in item 1 above, earlier on 2026-10-07 — and every
figure below is re-derived at this HEAD rather than carried forward.

| author | identity | overdue | recorded sha | state |
|---|---|---|---|---|
| **hank** | `2026-09-27T03:42:29Z` | **250h** | `54e4835ac96ea02dec8301b9a3252d228b186b0f` | **ABSENT** |
| **cody** | `2026-09-28T03:34:57Z` | **226h** | `f88105a88287d89b80d93cf2936066b198b90069` | **ABSENT** |
| **hank** | `2026-10-05T09:03:14Z` | **52h** | `0e7f99af671ca74df4e713b67f3e82f13519b286` | **ABSENT** |
| **cody** | `2026-10-05T13:23:46Z` | **48h** | `a4610fa386305858cdcab2321ab81137b36e1cf7` | **ABSENT** |

### The proof, and the control that makes it per-record rather than a broken clone

    for s in 54e4835ac96e f88105a88287 0e7f99af671c a4610fa38630 5a32fa3c4de0; do
      if   git merge-base --is-ancestor "$s" origin/main 2>/dev/null; then echo "$s ON-REF"
      elif git cat-file -e "$s^{commit}" 2>/dev/null;            then echo "$s ORPHANED"
      else                                                             echo "$s ABSENT"; fi
    done

    54e4835ac96e ABSENT
    f88105a88287 ABSENT
    0e7f99af671c ABSENT
    a4610fa38630 ABSENT
    5a32fa3c4de0 ON-REF      <- THE CONTROL

**`5a32fa3c4de0` is in the same sweep and returns ON-REF**, so the clone is not
broken and nothing is unfetched: these four are absent individually. I
**discharged** the obligation behind that control in this same batch, which is
the practical demonstration — a readable subject gets reviewed, an absent one
cannot be.

**Do not accept `git cat-file -e` or `git rev-parse --verify` as the test.** Both
answer OK for an **ORPHANED** commit. That is convention 19, and it is why this
table has a fourth state.

**Two of these are 52h and 48h old.** The orphaning is current practice, not a
historical backlog, and it will keep producing unreviewable obligations until
whatever rebases without reseating changes.

## SEQ 13-B — ROUTED TO cc: the SCP boundary refusal carries no error code

**Found discharging cody's `2026-09-29T14:34:43Z` obligation, attack point (1).
Seq: that record's `verdict` field, written this batch.** The app-boundary
refusal in `api/sd-data.js` is a **400 whose only distinguishing mark is the
message prefix** `resource must be one of`.
`api/sd-data-scp-licence-only.test.js` does the strongest thing a message-only
refusal allows — it requires the 400 **and** the prefix **and** whole-item
absence from the split allow-list (lines 202–203, with the `sd_customers`
substring hazard named at 199) — and it is still true that **a 400 answered for
some other reason with that same prefix would satisfy all nine C arms while the
boundary did nothing.**

**Reproducing artifact:** the nine C arms in that file. They pass today, and
they would pass under the substitution above — which is the point. **The fix is
to give the refusal an error code**; `UNKNOWN_RESOURCE` already appears in the
file's own prose. That is a change to `api/sd-data.js`, inside another session's
claim. **Not patched by me, not closed by me.**

## SEQ 13-C — ROUTED TO cc: the eight-entry hand-maintained exclusion list

**Found discharging cc's `2026-09-29T16:58:39Z` obligation; the record asks the
question itself.** `SELF_EXCLUDED` in `tools/cross_tenant_isolation_scope.py` has
reached **eight** hand-written entries — read by AST, because reading it by eye
is how I got it wrong the first time. The record asks *"whether the eighth
hand-maintained entry should finally be replaced by the computation the importer
arm already performs."*

**My answer: yes, and the importer arm is the evidence the derivation exists.** A
list at eight entries, each needing a human to notice that a new review probe
imports the grader, is a list that will be wrong the first time nobody notices.
**A design change to cc's own tool, not a review finding, so it is routed and
nothing is patched.**

---

## SEQ 13-D — the three ORPHANED citations: every citer is MINE, so this is DONE, not routed

**Re-derived at HEAD rather than taken from the dispatch.** The ask was to route
`100b82fc`, `7c911e5c` and `6984634e` to the owner of the document that cites
each. Every citer is **fourth**:

    grep -rln "100b82fc\|7c911e5c\|6984634e" --include=*.md --include=*.json .

    .claude/claims/fourth.json
    docs/2026-10-06-fourth-andon-log.md
    docs/2026-10-06-fourth-batch11-inventory.md
    docs/2026-10-07-fourth-postmortem-object-existence.md
    docs/handoff-fourth-2026-10-07.md

**No other session cites them.** So there is nobody to route to, and dressing a
self-repair up as a routing would put a handover in the record that never
happened. **Seq: fourth → fourth, DONE.**

### What was actually wrong, and what is fixed

These three are cited **deliberately** — they are the *subject* of
`docs/2026-10-07-fourth-postmortem-object-existence.md`, which is about my
having called them UNREACHABLE on the strength of a `cat-file -e` that returned
OK. Naming the dead SHAs is the point of that document and they must stay.

The defect was narrower: **a reader meeting a dead SHA mid-sentence had to
resolve it themselves.** Every occurrence now carries its live equivalent
inline — `100b82fc (now 6b77545f)` — so the citation cannot rot further and
needs no lookup.

| dead | state | live equivalent | state |
|---|---|---|---|
| `100b82fc` | **ORPHANED** | `6b77545f` | **ON-REF** |
| `7c911e5c` | **ORPHANED** | `326d277e` | **ON-REF** |
| `6984634e` | **ORPHANED** | `7eabd192` | **ON-REF** |

**Reproducing artifact** — the command that classifies all six, and the control
that makes it per-sha rather than a broken clone:

    for s in 100b82fc 7c911e5c 6984634e 6b77545f 326d277e 7eabd192; do
      if   git merge-base --is-ancestor "$s" origin/main 2>/dev/null; then echo "$s ON-REF"
      elif git cat-file -e "$s^{commit}" 2>/dev/null;            then echo "$s ORPHANED"
      else                                                            echo "$s ABSENT"; fi
    done

Each replacement was matched by **commit subject**, not by position, and
verified `ON-REF` **before** the annotation was written — the script refuses
outright if a replacement is not on a ref.

**The one thing NOT fixed:** `.claude/claims/fourth.json` also cites them, in my
own claim text. A claim file is an append-only record of what was claimed at the
time and rewriting it would falsify the record, so it is left as written and
named here instead.

---

## SEQ 13-E — `tools/bare_run_write_check.py`: the owner map says NOTHING, and that is the finding

**Item 10, re-derived at HEAD.** The ask was to confirm the owner and the
routing seq. Confirmed, and the owner record is the weak part:

    docs/tool-owner-map.json:
      tools/bare_run_write_check.py   -> {"owner": null, "basis": "NONE"}
      tests/run_bare_run_write_probe.py -> {"owner": null, "basis": "NONE"}
      tools/bare_run_writers.py       -> {"owner": "cody", "basis": "OWNER_LINE"}

**The owner is cody**, on three independent pieces of evidence that are not the
owner map:

1. **cody's own Tier A record** (`2026-09-30T10:58:02Z`, which I discharged this
   batch) describes it as cody's new work: *"(2) tools/bare_run_write_check.py
   and tests/run_bare_run_write_probe.py — NEW."*
2. The two commits that created it, `53972364` and `c86050b4` (2026-09-30), are
   the same *"feat(methodology): the bare-run write sweep"* pair.
3. Its **sibling** `tools/bare_run_writers.py` carries an `OWNER:` line naming
   cody.

**So the tool itself has NO `OWNER:` line**, which is why the map says
`basis: NONE` — and the map therefore cannot attribute a tool whose author is
not in doubt. That is the 283-headers backlog already recorded in
`docs/METHODOLOGY.md`, showing up where it costs something: a routing had to be
established from a review record and a sibling file instead of being read.

**Routing seq:** the finding itself is **SEQ 3** above (batch 12, the
linked-worktree hole with the `--git-common-dir` discriminator), re-confirmed in
the `verdict` of cody's `2026-09-30T10:58:02Z` obligation written this batch.
**NOT PATCHED** — the file is not in my claim and the fix is cody's.

---

## SEQ 13-F — ITEM 9: cody's `--pinned` change LANDED, and the isolation HOLDS

**`0dcb2daf` (2026-10-07): "fix(harness): --pinned builds a throwaway CLONE, not
a linked worktree".** It cites my `b23dbc2e` as the same layer and the same
measured reason, and `166fe4ef` beside it is cody's andon on a 6h31m run that
broke this clone and reported no residue.

**Verified by a TARGETED run, not a `--pinned` run** — the standing instruction
forbids whole-tree and `--pinned` runs, so this drives only the provisioning
sequence cody's change replaced (clone, detached checkout,
`provision_worktree_identity`), in process, and then makes the write that used
to reach the main clone:

    git clone --local --no-checkout --quiet        rc=0
    git checkout --detach dec86b03ea3e             rc=0
    provision_worktree_identity                    ok=True
    git -C <throwaway clone> config core.bare true rc=0
      the CLONE now reads core.bare = 'true'

**And this clone, before and after:**

    git config -l           29 line(s)  ->  29 line(s)   IDENTICAL
    .git/config             489 bytes   ->  489 bytes    BYTE-IDENTICAL
    core.bare               None        ->  None
    git status still answers: True (rc=0)

    cody's own residue detector:  _core_bare(main clone)      -> 'false'
                                  _core_bare(throwaway clone) -> 'true'

**ISOLATION HOLDS.** This is the exact mirror of the batch-11 proof, where
`git -C <worktree> config core.bare true` added `bare = true` to this clone's
`.git/config`. The same write now lands only in the throwaway clone.
`PROGRAM_EXIT=0`, one run, first run clean, at `dec86b03`. Throwaway clone
removed afterwards.

**The finding is cody's and cody closes it.** This is confirmation attached to
it, not a closure by me.

---

# BATCH 14 — 2026-10-07

## SEQ 14-A — ITEM 2 RESOLVED: the four ABSENT land in THREE different places, and two are now REVIEWABLE

**They were routed back to their originators twice — SEQ 1 (batch 12) and SEQ
13-A (batch 13) — and nobody closed them. That framing was wrong for three of
the four.** The gate has a sanctioned path, `--reseat-shas`, which already knew
where most of them go. Dry-run first (`PROGRAM_EXIT=0`, `git status` unchanged —
the dry run is read-only), then `--write` for the strong basis only.

| record | overdue | recorded sha | WHERE IT LANDS |
|---|---|---|---|
| hank `2026-10-05T09:03:14Z` | 54h | `0e7f99af671c` | **RESEATED → `9e3caeefd07f`**, `[EXACT FILE SET]` on `tools/citation_line_drift_check.py`. **Now STALE, i.e. REVIEWABLE** |
| cody `2026-10-05T13:23:46Z` | 50h | `a4610fa38630` | **RESEATED → `5e33157ee606`**, `[EXACT FILE SET]` on three `api/` files. **Now STALE, i.e. REVIEWABLE** |
| cody `2026-09-28T03:34:57Z` | 228h | `f88105a88287` | **RESEATABLE ON A WEAK BASIS → `bb840eeccb3c`**, file-set SUBSET, 0.1h apart. `--write` alone will not apply it; it needs `--write-weak-basis`, which is **an explicit decision about containment and is not mine to make for cody's record** |
| hank `2026-09-27T03:42:29Z` | 251h | `54e4835ac96e` | **REFUSED `[NO_OBJECT_IN_CLONE]`** — and the gate names the action precisely: *"reseatable by subject only from the clone whose rebase orphaned it — run this there, or fetch the object in first; and no commit anywhere contains that file set either."* Files sought: `api/_lib/compliance-rules-staff-join.test.js`, `api/_resources/sairnsenior.js`, `api/sd-data-sen-evv-clock.test.js`, `api/sd-data.js` |

**`RESEATED 5 record(s) on a strong basis, 0 on the WEAK basis, 8 refused.`**
`PROGRAM_EXIT=0`. The other three strong reseats are records of mine and of
others that were dangling for the same reason.

### Why this was the right move and not an override

`--reseat-shas` repoints a **provenance field** through the tool's own sanctioned
path. It does **not** discharge, close or reclassify anything — the two reseated
records are still **open and unreviewed**, they simply now have a subject
somebody can read. `docs/tier-a-reviews.json` is in my claim and in no other
active claim. **The weak-basis one was deliberately left alone**: "the file set
is a subset 0.1h apart" is a containment argument, and making that argument on
cody's behalf is the kind of judgement the convention-11 human gate exists for.

### A BONUS FINDING THAT CORROBORATES CODY, FROM A DIFFERENT FAULT MODE

The same dry run refused one of **my own** records with a reason I had not seen:

    fourth  2026-09-30T11:08:08Z  REFUSED [SHA_WRONG_WHEN_WRITTEN]
      THE RECORDED SHA WAS ALREADY WRONG FOR THIS RECORD, and that is a
      different fault from a rebase. Its subject twin on origin/main is
      093d65485c80 ('chore(register): re-seat the AI-scan record onto its
      rebased sha'), whose diff touches NONE of the files this record names
      (['docs/CRITICALITY-TIERS.md']). Following the sha to its twin would
      preserve the original mis-stamp faithfully -- a wrong sha is worse than a
      dangling one, because a dangling one is visibly broken. FIX THE RECORD,
      not the sha

**This is cody's `--open`-stamps-the-wrong-commit finding arriving by a third
route.** cody found two instances by reviewing; I hit it **4 of 4** on the
obligations I discharged in batch 13; and here the gate's own reseat path
independently identifies a record whose sha *was wrong when written* rather than
orphaned later. Three methods, one conclusion — and the gate's sentence *"a
wrong sha is worse than a dangling one, because a dangling one is visibly
broken"* is the sharpest statement of it. **Attached to cody's finding, not
claimed; cody and cc close it.**

---

## SEQ 14-B — ITEM 3: nine more diagnoses, and THREE SINGLE ARMS BLOCK SIX ROWS

**Empty `why` 19 → 10 of 79.** Each suite run alone at `51088830`, exit code
from its own output, `git status` captured before and after each run and
unchanged throughout, and `node --check api/sd-data.js` clean afterwards because
three of them are seam probes that plant and restore.

### The finding: six of the remaining rows are CHAINED off three single arms

| the one arm | where it lives | rows it blocks |
|---|---|---|
| **`5a  SAIRNsenior: every cached key is purged OR explicitly excluded`** | `tests/phi_cache_scoped_to_user.js`, 63 passed **1 failed** | **3** — `phi_cache_scope_probe`, `sairnbuild_fault_probe`, `sairncare_fault_probe` |
| **`the registry still holds exactly 35 resources`** | `tests/sairnfreedom_server_backup.js`, 16 passed **1 failed** | **2** — itself and `sairnfreedom_fault_probe` |
| **`...and names the exact command that publishes the earlier entry`** | `tests/claims/run_push_verify_probe.py`, 68 passed **1 failed** | **2** — itself and `claims/run_claim_retype_mutation_control` (diagnosed last batch) |

**Fix three arms, clear six rows.** And the phi-cache one is not cosmetic: its
subject is a **PHI cache purge on SAIRNsenior**, so a cached key that is neither
purged nor explicitly excluded is resident health data surviving a logout.

### A hardcoded cardinality is wrong in every copy at once

`35` is pinned in **two** suites — `sairnfreedom_server_backup.js` ("the
registry still holds exactly 35 resources") and `schema_provisioning_probe.py`
(`arm1_reads_35_from_the_schema`, `arm2_registry_has_35`, diagnosed last batch).
`write_readback_shape_probe.py` pins **two numbers in one arm name**
(`arm2_writes_33_not_81`). One registry growing reddened three suites in three
places — which is what makes a pinned count worse than a wrong one.

### `QUOTABLE` does not name `cloud`

`tests/hover_quotable_session_vocab_check.py` fails with one sentence:
*"1 session(s) exist that QUOTABLE does not name: cloud"*. **Confirmed
independently in this batch:** `tier_a_review_gate.py --list` prints
`ASSIGNED TO cloud` on live obligations, and one of my batch-13 discharges
needed `--takeover` precisely because a record had moved to `cloud`. Same class
as cc's `SELF_EXCLUDED` at eight hand-written entries (SEQ 13-C): **a list a
human must remember to extend is wrong the first time nobody remembers.**

### Two NOT CLEARED, named with the single missing fact

* `seam_check/run_or_default_probe.py` — the subject emits a COULD-NOT-TELL
  where the arms require clean. The direction is the safe one, so the question
  is **whether the could-not-tell is justified**; its reason text was not
  captured.
* `seam_check/run_ref_probe.py` — `baseline_clean` is **False**, so the two arms
  below it carry no information in either direction. **Fix order is forced: the
  baseline first.**

---

## SEQ 15-A — ITEM 5: THE THREE ARMS THAT BLOCK SIX ROWS, WITH ARTIFACT AND OWNER

**I fixed nothing in any of these files. Chat routes.** Each artifact is a
command whose captured output is the evidence; all three were run alone in the
live clone at HEAD `dc9f1629`, 2026-10-07, with `git status` unchanged.

### ARM 1 — `tests/phi_cache_scoped_to_user.js` arm `5a` · blocks 3 rows · OWNER: **UNASSIGNED**

    $ node tests/phi_cache_scoped_to_user.js
    FAIL  5a  SAIRNsenior: every cached key is purged OR explicitly excluded
    63 passed, 1 failed
    PROGRAM_EXIT=1

**Blocks:** `tests/phi_cache_scope_probe.py` (exit 2),
`tests/sairnbuild_fault_probe.py` (exit 1), `tests/sairncare_fault_probe.py`
(exit 1) — each stops on *"the shipped tree passes
phi_cache_scoped_to_user.js"*.

**OWNER: `docs/tool-owner-map.json` says `owner: None, basis: NONE`, and NO
claim in history names this file.** The arm's text was introduced at
**`b50c2e2f`** (2026-09-10, *"fix(care,senior,dental): the server scoped the
read, the local cache outlived"*), so the provenance is the scoped-read
cache-leak work — but there is no owner to route to. **That is the first thing
chat has to settle**, because this is the highest-consequence arm on the list: a
cached key neither purged nor explicitly excluded is **resident health data
surviving a logout**.

### ARM 2 — `tests/sairnfreedom_server_backup.js` · blocks 2 rows · OWNER: **cody**

    $ node tests/sairnfreedom_server_backup.js
    FAIL - the registry still holds exactly 35 resources
    FAILED  sairnfreedom_server_backup: 16 passed, 1 failed
    PROGRAM_EXIT=1

**Blocks:** itself and `tests/sairnfreedom_fault_probe.py` (exit 1), which stops
on *"the shipped tree PASSES … 16 passed, 1 failed"*.

**OWNER: cody — from CLAIM HISTORY, not from the owner map.** `c1e06f33` reads
*"chore(claims): cody claims cody -- negative control for
tests/sairnfreedom_server_backup.js"*. **The owner map says
`owner: None, basis: NONE` for this file**, so the map and the claim history
disagree and the map is the one that is behind. **A second instance of the
owner-map gap routed in SEQ 13-E.**

**The defect is a hardcoded cardinality** — `35` — and the same number is pinned
in `tests/schema_provisioning_probe.py`. Convention 14: assert a floor with
n of N stated; a DROP is the thing worth failing on.

### ARM 3 — `tests/claims/run_push_verify_probe.py` · blocks 2 rows · OWNER: **cc**

    $ python tests/claims/run_push_verify_probe.py
    FAIL ...and names the exact command that publishes the earlier entry
    68 passed, 1 failed
    PROGRAM_EXIT=1

**Blocks:** itself and `tests/claims/run_claim_retype_mutation_control.py`
(exit 2), whose arm 0 is *"baseline -- the probe is green against the shipped
tool"*.

**OWNER: cc** — `docs/tool-owner-map.json` gives
`owner: cc, basis: LAST_CLAIM, last_claim: 617a9c06`. The only file of the three
with a clean owner record.

**The refusal still FIRES; it has stopped naming its remedy.** The arms around
it pass, including *"a failed push, then a re-run -- one entry, not two"* and
*"the rewind really unpublished it -- otherwise arm 10 is vacuous"*. **A refusal
that does not name its remedy is the shape that gets overridden rather than
obeyed**, which is why the arm exists.

---

## SEQ 15-B — ITEM 7: THE EXACT `[NO_OBJECT_IN_CLONE]` COMMAND FOR HANK

**Record:** hank `2026-09-27T03:42:29Z`, **252h** overdue, resources
`alf_staff`, `sen_visits`, recorded sha `54e4835ac96ea02dec8301b9a3252d228b186b0f`.

**Why it cannot be done from here**, in the gate's own words:

    REFUSED [NO_OBJECT_IN_CLONE]
      the recorded sha is not in this clone's object store, so its subject
      cannot be read. A dangling sha is reseatable by subject only from the
      clone whose rebase orphaned it -- run this there, or fetch the object in
      first; and no commit anywhere contains that file set either.
      FILES SOUGHT: ['api/_lib/compliance-rules-staff-join.test.js',
      'api/_resources/sairnsenior.js', 'api/sd-data-sen-evv-clock.test.js',
      'api/sd-data.js']

### THE COMMAND HANK RUNS, from `C:\Users\marsh\Documents\SAIRN-hank`

    cd C:\Users\marsh\Documents\SAIRN-hank
    git fetch origin
    git cat-file -e 54e4835ac96ea02dec8301b9a3252d228b186b0f^{commit} && echo OBJECT PRESENT
    python tools/tier_a_review_gate.py --reseat-shas          # DRY RUN first
    python tools/tier_a_review_gate.py --reseat-shas --write  # only if the dry run names it

**The dry run first is not optional.** If hank's clone also lacks the object the
dry run will say `[NO_OBJECT_IN_CLONE]` again, and `--write` would then do
nothing while looking like it worked.

### THE CHECK THAT PROVES IT LANDED — three, and the third is the one that matters

    # 1. the sha is now reachable, by REACHABILITY and not by existence
    git merge-base --is-ancestor <new-sha> origin/main && echo ON-REF

    # 2. the gate no longer refuses the record
    python tools/tier_a_review_gate.py --list | grep -A3 "2026-09-27T03:42:29Z"
    #    must NOT contain COULD-NOT-TELL or NO_OBJECT_IN_CLONE

    # 3. THE SUBJECT IS READABLE, which is the whole point
    git show --stat <new-sha> -- api/_lib/compliance-rules-staff-join.test.js \
        api/_resources/sairnsenior.js api/sd-data-sen-evv-clock.test.js api/sd-data.js
    #    must list at least one of those four files

**Check 3 is the one that matters** and the first two can pass without it. A
reseat that lands on a reachable commit whose diff touches **none** of the files
the record names is the `[SHA_WRONG_WHEN_WRITTEN]` failure the gate refuses
elsewhere — *"a wrong sha is worse than a dangling one, because a dangling one
is visibly broken."*

**If the object is absent in hank's clone too**, the record cannot be reseated
at all and should be **retired unreviewed**, naming `alf_staff` and `sen_visits`
so they can be re-registered. Retiring it is hank's call, not mine.

---

## SEQ 15-C — ITEM 6: the orphan population, and how much of it is mine to touch

**Re-derived at HEAD: 84 orphans, not the 79 the brief carries** — the corpus
grew by 4 documents and the tree moved.

| | |
|---|---|
| orphaned citations, whole corpus | **84** |
| **in MY documents** | **28** |
| in OTHER sessions' documents — **not mine to edit** | **56** |

**The 56 by file, with the owner implied by the filename:**

    35  docs/2026-09-29-stale-branch-tips.md      <- a document ABOUT stale tips
     7  docs/2026-10-05-register-sha-pinning-proposal.md
     5  docs/defect-density-register.json
     3  docs/scrutiny-flags.json                  <- cc
     1  each: purge-evidence/…-cc.json, purge-evidence/…-hank.json,
          SAIRN-ACTIVE-WORK-cc.md, 2026-10-05-dependabot-high-triage.md,
          2026-10-07-cody-harness-exit-mismatches.md,
          2026-10-06-cody-queue18-items-10-12-13.md

**Of my 28, only 17 are candidates**; the other 11 are deliberate — 3 are the
dead SHAs the convention-19 postmortem is *about*, and 8 are Tier A ledger SHAs
I quote as data.

**5 re-seated this batch**, each matched by commit subject and verified `ON-REF`
**before** the swap, `git status` checked per file, `node --check` clean and
`known-red-suites.json` still valid JSON afterwards:

    bcc743db -> 2e8a59aa    4d4b0da5 -> 51088830    e787a6d9 -> 8ff247a2
    d90463bd -> 45b421f1    161cb714 -> 5090df1e

**Deliberately NOT re-seated: the 6 full SHAs in
`docs/purge-evidence/2026-09-30-SAIRN-fourth.json`.** A purge-evidence record is
append-only evidence of what was purged; rewriting it would falsify the evidence
rather than fix a citation. Named here instead.

---

## SEQ 17-A -- THE PR 1.2 SWEEP: every checker that derives a key set by regex over a RAW app file

**To: whoever owns each file below. NOTHING HERE IS FIXED BY ME -- **I own none of them**, by the owner map AND by a read of all 1,265 claim task strings across all seven clone claim files. Measured, classified and routed with the exact line.**

PR 1.2 is *"Grep cannot tell code from text that describes code."* Batch 16 paid for it once: `tests/phi_cache_scoped_to_user.js` arm 5a counted a comment that exists to say a key is never written as the key being written, and that one arm held four register rows shut. This is the sweep for the same shape everywhere else.

### How the population was derived, so the figure is checkable

A file is a CANDIDATE when all three hold: it reads a single-file SAIRN app by literal name; it applies a regex that extracts an identifier or key set (a capture group plus an identifier character class or a storage-accessor shape); and it does **not** import `tests/lib/strip_comments.js` or any comment-stripper. (c) is the defect condition; (a) and (b) are what make it reachable.

| | |
|---|---|
| tracked scripts under `tests/`, `tools/`, `fmea/` | **983** |
| candidates -- read an app, derive identifiers, **no stripper** | **53** |
| for contrast: read an app and **do** use a stripper | **45** |
| patterns measured both ways (JS **188** + PY **46**) | **234** |
| patterns that would not compile out of their literal, named below | **4** |
| **patterns whose DERIVED SET SHRINKS when comments go** | **47** |

**Measured both ways against the SAME stripped bytes.** `stripComments()` output was written to scratch once per app and the python half read those files rather than implementing a second stripper -- two strippers would be two things to drift, which is the reason `tests/lib/strip_comments.js` exists at all.

### The findings, ranked by how much of the derived set is PHANTOM

A PHANTOM MEMBER is a set member that exists only inside a comment. The fraction is the blast radius: a checker whose set is 100% phantom is asserting entirely about prose.

#### `tests/sairnvet_seed_never_syncs.js:98` — **100% of the derived set is phantom**

* **owner:** **UNASSIGNED** -- owner map `None`/`NONE`, and NO session has ever named it in a claim
* **app:** `sairnvet.html` — derived set **1 raw → 0 stripped**
* **the exact line, read from the file at HEAD:**

      const call = /\b(\w+)\(\s*(seed\w*|demo\w*)\s*\)\s*;/.exec(body);

* **phantom members:** `["saveX"]`

#### `tools/stale_row_sweep.py:240` — **100% of the derived set is phantom**

* **owner:** **UNASSIGNED** -- owner map `None`/`NONE`, and NO session has ever named it in a claim
* **app:** `sairnvet.html` — derived set **29 raw → 0 stripped**
* **the exact line, read from the file at HEAD:**

      SYMBOL_RE = re.compile(r'`([A-Za-z_][A-Za-z0-9_]{4,})(?:\(\))?`')

* **phantom members:** `["SpeechRecognition", "_svAuditRows", "active", "aquatic", "author", "before", "check_license", "companion", "defaults", "derived", "exotic", "exportTableCSV", "kennelCount", "label_sourced", "large", "lastTransaction", "provisioned", "reference", "setTimeout", "shared_knowledge", "species", "svPushOne", "sv_controlled", "today", "tools", "total", "typeof", "verify_required", "wantEnvelope"]`

#### `tests/seed_never_syncs_platform.js:105` — **50% of the derived set is phantom**

* **owner:** **UNASSIGNED** -- owner map `None`/`NONE`, and NO session has ever named it in a claim
* **app:** `sairnbuild.html` — derived set **2 raw → 1 stripped**
* **the exact line, read from the file at HEAD:**

      const hm = /\b(\w*SyncCollection)\s*\(/.exec(b.body);

* **phantom members:** `["sfSyncCollection"]`

#### `tests/seed_never_syncs_platform.js:105` — **50% of the derived set is phantom**

* **owner:** **UNASSIGNED** -- owner map `None`/`NONE`, and NO session has ever named it in a claim
* **app:** `stonedesk.html` — derived set **2 raw → 1 stripped**
* **the exact line, read from the file at HEAD:**

      const hm = /\b(\w*SyncCollection)\s*\(/.exec(b.body);

* **phantom members:** `["sfSyncCollection"]`

#### `tests/seed_never_syncs_platform.js:274` — **50% of the derived set is phantom**

* **owner:** **UNASSIGNED** -- owner map `None`/`NONE`, and NO session has ever named it in a claim
* **app:** `sairnfreedom.html` — derived set **2 raw → 1 stripped**
* **the exact line, read from the file at HEAD:**

      /(Suppress|Paused|Seeding)\w*\s*=\s*true/.test(b.body);

* **phantom members:** `["Paused"]`

#### `tests/seed_never_syncs_platform.js:274` — **50% of the derived set is phantom**

* **owner:** **UNASSIGNED** -- owner map `None`/`NONE`, and NO session has ever named it in a claim
* **app:** `stonedesk.html` — derived set **2 raw → 1 stripped**
* **the exact line, read from the file at HEAD:**

      /(Suppress|Paused|Seeding)\w*\s*=\s*true/.test(b.body);

* **phantom members:** `["Paused"]`

#### `tests/licence_rekey_isolation.js:400` — **40% of the derived set is phantom**

* **owner:** **UNASSIGNED** -- owner map `None`/`NONE`, and NO session has ever named it in a claim
* **app:** `sairnbiz.html` — derived set **6121 raw → 3653 stripped**
* **the exact line, read from the file at HEAD:**

      const keys = (expr.match(/'([A-Za-z0-9_]+)'/g) || [])

* **phantom members:** `["004", "040", "0b", "0fa5fc6", "112k", "12h", "13", "134", "17867", "17x", "1954", "1a", "1f1705e", "200aaba8", "211", "240", "262", "271", "284", "286", "2xx", "300A", "304", "308", "32", "32h", "339", "345", "35", "3828", "400s", "402", "404s", "43", "44", "47", "4700000000003", "500ms", "503s", "507", "508", "517", "54", "558", "592", "5e", "60s", "62", "64", "66666666666667", "67", "72", "7cd`

#### `tests/seed_never_syncs_platform.js:147` — **40% of the derived set is phantom**

* **owner:** **UNASSIGNED** -- owner map `None`/`NONE`, and NO session has ever named it in a claim
* **app:** `sairnbiz.html` — derived set **6121 raw → 3653 stripped**
* **the exact line, read from the file at HEAD:**

      return (m[2].match(/'([\w]+)'/g) || []).map((s) => s.replace(/'/g, ''));

* **phantom members:** `["004", "040", "0b", "0fa5fc6", "112k", "12h", "13", "134", "17867", "17x", "1954", "1a", "1f1705e", "200aaba8", "211", "240", "262", "271", "284", "286", "2xx", "300A", "304", "308", "32", "32h", "339", "345", "35", "3828", "400s", "402", "404s", "43", "44", "47", "4700000000003", "500ms", "503s", "507", "508", "517", "54", "558", "592", "5e", "60s", "62", "64", "66666666666667", "67", "72", "7cd`

#### `tests/licence_rekey_isolation.js:400` — **38% of the derived set is phantom**

* **owner:** **UNASSIGNED** -- owner map `None`/`NONE`, and NO session has ever named it in a claim
* **app:** `sairnsenior.html` — derived set **4973 raw → 3070 stripped**
* **the exact line, read from the file at HEAD:**

      const keys = (expr.match(/'([A-Za-z0-9_]+)'/g) || [])

* **phantom members:** `["03", "04", "05", "0b", "1099", "13", "1339", "134", "1396b", "15s", "17", "180", "1a", "21", "2540", "256", "26", "27", "2964", "2x", "32", "3416", "3429", "3925", "3964", "3971", "400s", "403", "404s", "427", "428", "4675", "517c47b1", "518", "5252", "5837", "6052", "64", "64KB", "72", "7cd70f83", "8pm", "999", "A0", "A2", "A3", "A5", "A6", "A7", "ABOUT", "ABOVE", "ABSENT", "ABSOLUTE", "ACCESS"`

#### `tests/licence_rekey_isolation.js:400` — **36% of the derived set is phantom**

* **owner:** **UNASSIGNED** -- owner map `None`/`NONE`, and NO session has ever named it in a claim
* **app:** `sairncare.html` — derived set **4720 raw → 2999 stripped**
* **the exact line, read from the file at HEAD:**

      const keys = (expr.match(/'([A-Za-z0-9_]+)'/g) || [])

* **phantom members:** `["02", "05", "09", "134", "14219", "149", "15s", "17", "1a", "24hr", "26", "27", "28", "33", "39c", "400", "404", "404s", "409", "4xx", "502", "503", "5xx", "64", "72", "75b9c07", "7cd70f83", "8pm", "A0", "ABSENT", "ACCEPTED", "ACCEPTS", "ACCESS", "ACCIDENT", "ACTION", "ACTIVE", "ACTIVITIES", "ADD", "ADDED", "ADDING", "ADDITIVE", "ADDS", "ADOPTING", "ADOPTS", "ADVICE", "AFTER", "AGAIN", "AL", "ALE`

#### `tests/licence_rekey_isolation.js:400` — **36% of the derived set is phantom**

* **owner:** **UNASSIGNED** -- owner map `None`/`NONE`, and NO session has ever named it in a claim
* **app:** `sairndesign.html` — derived set **4363 raw → 2773 stripped**
* **the exact line, read from the file at HEAD:**

      const keys = (expr.match(/'([A-Za-z0-9_]+)'/g) || [])

* **phantom members:** `["04", "05", "07", "13", "134", "135", "1461", "1471", "17867", "1a", "21", "29", "2935", "2xx", "403s", "404s", "4th", "500ms", "60s", "64", "72", "75b9c07", "7cd70f83", "999", "9db14368", "A0", "A1", "ABOUT", "ABSENCE", "ABSENT", "ACCESS", "ACCESSORS", "ADDED", "ADDITIVE", "ADMIN", "ADOPTS", "AFFECTED", "AFTER", "AGREEMENT", "ALL", "ALREADY", "ALSO", "AN", "ANALYTICS", "ANSWER", "ANY", "APP", "A`

#### `tests/licence_rekey_isolation.js:400` — **35% of the derived set is phantom**

* **owner:** **UNASSIGNED** -- owner map `None`/`NONE`, and NO session has ever named it in a claim
* **app:** `sairndental.html` — derived set **5646 raw → 3661 stripped**
* **the exact line, read from the file at HEAD:**

      const keys = (expr.match(/'([A-Za-z0-9_]+)'/g) || [])

* **phantom members:** `["02", "03", "05", "06", "09", "0b", "134", "18th", "1a", "2016", "233", "256", "317", "39c", "403", "404s", "4715", "4xx", "503", "569b2689", "5MB", "5xx", "6103", "72", "7cd70f83", "A0", "A4", "A7", "A8", "A9", "ABANDONED", "ABOVE", "ABSENCE", "ACCEPTANCE", "ACCESS", "ACCESSORS", "ACT", "ACTUALLY", "ADDED", "ADOPTS", "AGAIN", "AGAINST", "AGEING", "AGGREGATE", "ALREADY", "ALREADY_PROVISIONED", "A`

#### `tests/licence_rekey_isolation.js:400` — **34% of the derived set is phantom**

* **owner:** **UNASSIGNED** -- owner map `None`/`NONE`, and NO session has ever named it in a claim
* **app:** `sairnscape.html` — derived set **4171 raw → 2746 stripped**
* **the exact line, read from the file at HEAD:**

      const keys = (expr.match(/'([A-Za-z0-9_]+)'/g) || [])

* **phantom members:** `["11", "13", "134", "1530", "17", "17867", "18", "19", "193", "1a", "201", "21", "258", "2877", "3137", "3491", "3567", "3639", "403", "404", "404ing", "404s", "44", "4xx", "500ms", "64", "64KB", "72", "7cd70f83", "ABSENT", "ACCESS", "ADOPTS", "ADVICE", "ALL", "ALREADY", "ALWAYS", "AN", "ANALYTICS", "AND", "ANY", "ARE", "AS", "ASSIGNMENT", "ASSISTANT", "ASSUMED", "AT", "Adopt", "Agentic", "An", "A`

#### `tests/faults/grd_write_faults.js:385` — **33% of the derived set is phantom**

* **owner:** **UNASSIGNED** -- owner map `None`/`NONE`, and NO session has ever named it in a claim
* **app:** `sairngrounds.html` — derived set **3 raw → 2 stripped**
* **the exact line, read from the file at HEAD:**

      const re = /(function\s+|\w+\s*=\s*|await\s+|return\s+)?cmSavePoints\s*\(/g;

* **phantom members:** `["cmSavePoints("]`

#### `tests/faults/grd_write_faults.js:396` — **33% of the derived set is phantom**

* **owner:** **UNASSIGNED** -- owner map `None`/`NONE`, and NO session has ever named it in a claim
* **app:** `sairngrounds.html` — derived set **3 raw → 2 stripped**
* **the exact line, read from the file at HEAD:**

      const re = /(function\s+|\w+\s*=\s*|await\s+|return\s+)?cmSavePoints\s*\(/g;

* **phantom members:** `["cmSavePoints("]`

#### `tests/licence_rekey_isolation.js:400` — **32% of the derived set is phantom**

* **owner:** **UNASSIGNED** -- owner map `None`/`NONE`, and NO session has ever named it in a claim
* **app:** `sairnlaw.html` — derived set **6454 raw → 4376 stripped**
* **the exact line, read from the file at HEAD:**

      const keys = (expr.match(/'([A-Za-z0-9_]+)'/g) || [])

* **phantom members:** `["000", "04", "106", "12439", "13", "134", "14", "143", "14th", "1575", "17", "1712", "178", "17867", "1a", "1cd64840", "20th", "21", "22T13", "29", "2nd", "31", "31Z", "33", "3372", "341", "342", "3588", "36", "38", "401", "403", "404s", "409", "46", "47", "48", "500ms", "503s", "5724", "5853", "60s", "64", "68", "75b9c07", "799d78db", "7cd70f83", "90", "999", "ABA", "ABCDEF", "ABOUT", "ABSENT", `

#### `tests/licence_rekey_isolation.js:400` — **31% of the derived set is phantom**

* **owner:** **UNASSIGNED** -- owner map `None`/`NONE`, and NO session has ever named it in a claim
* **app:** `sairnlegacy.html` — derived set **4795 raw → 3321 stripped**
* **the exact line, read from the file at HEAD:**

      const keys = (expr.match(/'([A-Za-z0-9_]+)'/g) || [])

* **phantom members:** `["13", "134", "1a", "20", "200", "208", "21", "228", "2xx", "36", "37", "38", "401", "403", "404s", "4th", "4xx", "56", "57", "58", "5xx", "64", "72", "75b9c07", "7cd70f83", "999", "ABOUT", "ABOVE", "ABSENT", "ACCESS", "ACCESSORS", "ACCOUNTING", "ADDED", "ADDITIVE", "ADDS", "ADOPTS", "AFTER", "AFTERCARE", "ALREADY", "AN", "ANALYTICS", "ANSWER", "ANY", "APP", "ARE", "ARGUMENT", "AS", "ASSERTS", "AS`

#### `tests/sairnlegacy_write_failure_voice.js:197` — **31% of the derived set is phantom**

* **owner:** **UNASSIGNED** -- owner map `None`/`NONE`, and NO session has ever named it in a claim
* **app:** `sairnlegacy.html` — derived set **4795 raw → 3321 stripped**
* **the exact line, read from the file at HEAD:**

      const names = [...m[1].matchAll(/'(\w+)'/g)].map((x) => x[1]);

* **phantom members:** `["13", "134", "1a", "20", "200", "208", "21", "228", "2xx", "36", "37", "38", "401", "403", "404s", "4th", "4xx", "56", "57", "58", "5xx", "64", "72", "75b9c07", "7cd70f83", "999", "ABOUT", "ABOVE", "ABSENT", "ACCESS", "ACCESSORS", "ACCOUNTING", "ADDED", "ADDITIVE", "ADDS", "ADOPTS", "AFTER", "AFTERCARE", "ALREADY", "AN", "ANALYTICS", "ANSWER", "ANY", "APP", "ARE", "ARGUMENT", "AS", "ASSERTS", "AS`

#### `tests/licence_rekey_isolation.js:400` — **28% of the derived set is phantom**

* **owner:** **UNASSIGNED** -- owner map `None`/`NONE`, and NO session has ever named it in a claim
* **app:** `sairngrounds.html` — derived set **5070 raw → 3645 stripped**
* **the exact line, read from the file at HEAD:**

      const keys = (expr.match(/'([A-Za-z0-9_]+)'/g) || [])

* **phantom members:** `["03", "06", "0e", "11", "13", "134", "147", "15m", "1725", "19", "1a", "223", "25m", "27", "304", "3077", "308", "3414", "404s", "43", "4m", "56", "5a", "64", "64KB", "65536", "72", "8s", "9th", "A0", "ACADEMY", "ACCEPTED", "ACCESS", "ADOPTS", "ALL", "ALREADY", "ALWAYS", "AN", "ANALYTICS", "ANY", "APP", "ARRIVED", "ASSISTANT", "AT", "AUDIT", "AUTO", "AWAIT", "AbortController", "Adding", "Adopt", `

#### `tests/licence_rekey_isolation.js:400` — **27% of the derived set is phantom**

* **owner:** **UNASSIGNED** -- owner map `None`/`NONE`, and NO session has ever named it in a claim
* **app:** `sairnbuild.html` — derived set **6877 raw → 5018 stripped**
* **the exact line, read from the file at HEAD:**

      const keys = (expr.match(/'([A-Za-z0-9_]+)'/g) || [])

* **phantom members:** `["000", "04500780", "0b", "130", "134", "17867", "1928", "1a", "3516", "3590", "37", "403s", "404s", "4074", "409", "44", "4th", "500ms", "503", "60s", "64", "7287", "7cd70f83", "84", "86", "A0", "ABOVE", "ABSENT", "ACCEPTED", "ACCESS", "ACCRUAL", "ADA", "ADDITIVE", "ADOPTS", "ADVISOR", "AFFORDANCE", "ALL", "ALONE", "ALREADY", "AN", "ANALYSIS", "ANALYTICS", "AND", "ANSWER", "ANSWERS", "ANY", "ANYT`

#### `tests/seed_never_syncs_platform.js:147` — **27% of the derived set is phantom**

* **owner:** **UNASSIGNED** -- owner map `None`/`NONE`, and NO session has ever named it in a claim
* **app:** `sairnbuild.html` — derived set **6877 raw → 5018 stripped**
* **the exact line, read from the file at HEAD:**

      return (m[2].match(/'([\w]+)'/g) || []).map((s) => s.replace(/'/g, ''));

* **phantom members:** `["000", "04500780", "0b", "130", "134", "17867", "1928", "1a", "3516", "3590", "37", "403s", "404s", "4074", "409", "44", "4th", "500ms", "503", "60s", "64", "7287", "7cd70f83", "84", "86", "A0", "ABOVE", "ABSENT", "ACCEPTED", "ACCESS", "ACCRUAL", "ADA", "ADDITIVE", "ADOPTS", "ADVISOR", "AFFORDANCE", "ALL", "ALONE", "ALREADY", "AN", "ANALYSIS", "ANALYTICS", "AND", "ANSWER", "ANSWERS", "ANY", "ANYT`

#### `tests/licence_rekey_isolation.js:400` — **26% of the derived set is phantom**

* **owner:** **UNASSIGNED** -- owner map `None`/`NONE`, and NO session has ever named it in a claim
* **app:** `sairnroofing.html` — derived set **4664 raw → 3446 stripped**
* **the exact line, read from the file at HEAD:**

      const keys = (expr.match(/'([A-Za-z0-9_]+)'/g) || [])

* **phantom members:** `["05", "13", "134", "163", "17", "1a", "200", "2011", "2015", "2031", "23", "2495", "26", "28", "2994", "304", "31e0337", "33", "39c", "3a", "3b", "3c", "40", "403", "404s", "4102", "4180", "4712", "4a", "4b", "4c", "4d", "5MB", "626", "64", "72", "806", "854", "8pm", "983", "A1", "A2", "A3", "A5", "ABOUT", "ABOVE", "ABSENT", "ACCESS", "ACCOUNTING", "ACROSS", "ADOPTS", "AGREEMENT", "ALREADY", "AMO`

#### `tests/licence_rekey_isolation.js:400` — **24% of the derived set is phantom**

* **owner:** **UNASSIGNED** -- owner map `None`/`NONE`, and NO session has ever named it in a claim
* **app:** `sairnfreedom.html` — derived set **5664 raw → 4319 stripped**
* **the exact line, read from the file at HEAD:**

      const keys = (expr.match(/'([A-Za-z0-9_]+)'/g) || [])

* **phantom members:** `["007", "06", "0b", "1042", "1106", "119", "12h", "134", "14th", "15s", "1c", "2021", "2a", "2b", "3839", "3A", "401", "403", "404s", "409", "42", "420", "45", "4834", "503", "526", "55889165", "62", "64", "67", "75b9c07", "78", "7cd70f83", "87", "900", "9a", "9d", "ABOUT", "ABOVE", "ABSENT", "ACCESS", "ACCOUNT", "ACCOUNTS", "ACCREDITATION", "ACTIVE", "ADDED", "ADDITIVE", "ADJUSTED", "ADOPTS", "AF`

#### `tests/seed_never_syncs_platform.js:147` — **24% of the derived set is phantom**

* **owner:** **UNASSIGNED** -- owner map `None`/`NONE`, and NO session has ever named it in a claim
* **app:** `sairnfreedom.html` — derived set **5664 raw → 4319 stripped**
* **the exact line, read from the file at HEAD:**

      return (m[2].match(/'([\w]+)'/g) || []).map((s) => s.replace(/'/g, ''));

* **phantom members:** `["007", "06", "0b", "1042", "1106", "119", "12h", "134", "14th", "15s", "1c", "2021", "2a", "2b", "3839", "3A", "401", "403", "404s", "409", "42", "420", "45", "4834", "503", "526", "55889165", "62", "64", "67", "75b9c07", "78", "7cd70f83", "87", "900", "9a", "9d", "ABOUT", "ABOVE", "ABSENT", "ACCESS", "ACCOUNT", "ACCOUNTS", "ACCREDITATION", "ACTIVE", "ADDED", "ADDITIVE", "ADJUSTED", "ADOPTS", "AF`

#### `tests/stonedesk_server_backup.js:55` — **23% of the derived set is phantom**

* **owner:** **hank** (owner map, LAST_CLAIM)
* **app:** `stonedesk.html` — derived set **10263 raw → 7884 stripped**
* **the exact line, read from the file at HEAD:**

      return (body.match(/'([a-z_]+)'/g) || []).map((x) => x.slice(1, -1));

* **phantom members:** `["_deleted_at", "_lib", "_resources", "abandoned", "abelled", "aborted", "abricated", "absence", "abstract", "accard", "acceptance", "accepting", "accepts", "accessibility", "accessor", "accidental", "accidentally", "accumulate", "accumulation", "acknowledgement", "acting", "activity", "acts", "additionally", "additive", "addressed", "ade", "adjoining", "adjustable", "adjusted", "adopt", "adopted"`

#### `tests/licence_rekey_isolation.js:400` — **23% of the derived set is phantom**

* **owner:** **UNASSIGNED** -- owner map `None`/`NONE`, and NO session has ever named it in a claim
* **app:** `stonedesk.html` — derived set **17752 raw → 13701 stripped**
* **the exact line, read from the file at HEAD:**

      const keys = (expr.match(/'([A-Za-z0-9_]+)'/g) || [])

* **phantom members:** `["0039", "0040", "0072", "00in", "086", "0b", "0d", "0sqin", "101", "1079", "10ft", "10in", "11410", "11420", "12964", "1308", "1310", "134", "14855", "1494", "150ms", "17329", "1842", "1886", "18d63d6", "19348", "1D", "1a", "1b", "1e", "1k", "1st", "1x", "20046", "200KB", "200k", "2016", "201st", "2028", "2029", "20386", "20ft", "21179", "21644", "2208", "22686", "22790", "25441", "25450", "258",`

#### `tests/seed_never_syncs_platform.js:147` — **23% of the derived set is phantom**

* **owner:** **UNASSIGNED** -- owner map `None`/`NONE`, and NO session has ever named it in a claim
* **app:** `stonedesk.html` — derived set **17752 raw → 13701 stripped**
* **the exact line, read from the file at HEAD:**

      return (m[2].match(/'([\w]+)'/g) || []).map((s) => s.replace(/'/g, ''));

* **phantom members:** `["0039", "0040", "0072", "00in", "086", "0b", "0d", "0sqin", "101", "1079", "10ft", "10in", "11410", "11420", "12964", "1308", "1310", "134", "14855", "1494", "150ms", "17329", "1842", "1886", "18d63d6", "19348", "1D", "1a", "1b", "1e", "1k", "1st", "1x", "20046", "200KB", "200k", "2016", "201st", "2028", "2029", "20386", "20ft", "21179", "21644", "2208", "22686", "22790", "25441", "25450", "258",`

#### `tests/sairncode_gates.js:301` — **21% of the derived set is phantom**

* **owner:** **cc** (owner map, LAST_CLAIM)
* **app:** `sairncode.html` — derived set **34 raw → 27 stripped**
* **the exact line, read from the file at HEAD:**

      const re = /(\w+)\s*:\s*\[([^\]]*)\]/g;

* **phantom members:** `["codes", "cq_applied_codes", "data", "evidence", "rtm_codes", "same_day_codes", "shape"]`

#### `tests/licence_rekey_isolation.js:400` — **19% of the derived set is phantom**

* **owner:** **UNASSIGNED** -- owner map `None`/`NONE`, and NO session has ever named it in a claim
* **app:** `sairncode.html` — derived set **8108 raw → 6529 stripped**
* **the exact line, read from the file at HEAD:**

      const keys = (expr.match(/'([A-Za-z0-9_]+)'/g) || [])

* **phantom members:** `["0a", "0b", "118", "12h", "134", "155", "1a", "2400", "2601", "2608", "27", "2c", "2xx", "34", "404s", "47", "502", "503", "64", "68", "71", "7cd70f83", "80", "82", "909xx", "93000", "96401", "96450", "A0", "A2", "AAPC", "ABSENT", "ACCEPTED", "ACCESS", "ACCUMULATOR", "ACTUALLY", "ADDED", "ADMINISTRATION", "ADOPTS", "ADVISORY", "AGAINST", "AGGREGATE", "AIR", "ALS", "AN", "ANALYTICS", "ANESTHESIA",`

#### `tools/citation_drift_hook.py:411` — **19% of the derived set is phantom**

* **owner:** **cc** (owner map, LAST_CLAIM)
* **app:** `sairnvet.html` — derived set **6378 raw → 5194 stripped**
* **the exact line, read from the file at HEAD:**

      for w in _re.findall(r'\b([A-Za-z_][A-Za-z0-9_]{5,40})\b', line):

* **phantom members:** `["ABSENCE", "ACCEPTED", "ACCEPTING", "ACCESS", "ACROSS", "ACTIVE", "ACTUAL", "ACTUALLY", "ADDITIVE", "AFFIRMATIONS", "ALWAYS", "ANALYTICS", "ANYTHING", "ANYWHERE", "APPLIES", "APPOINTMENT", "ARITHMETIC", "ARRIVAL", "AVAILABLE", "AbortError", "Adding", "Additive", "America", "Anthropic", "Ariane", "Auditor", "Author", "BACKED", "BACKGROUND", "BACKUP", "BACKWARDS", "BECAUSE", "BEFORE", "BEHIND", "BE`

#### `tools/citation_drift_hook.py:416` — **19% of the derived set is phantom**

* **owner:** **cc** (owner map, LAST_CLAIM)
* **app:** `sairnvet.html` — derived set **6378 raw → 5194 stripped**
* **the exact line, read from the file at HEAD:**

      for w in _re.findall(r'\b([A-Za-z_][A-Za-z0-9_]{5,40})\b', line):

* **phantom members:** `["ABSENCE", "ACCEPTED", "ACCEPTING", "ACCESS", "ACROSS", "ACTIVE", "ACTUAL", "ACTUALLY", "ADDITIVE", "AFFIRMATIONS", "ALWAYS", "ANALYTICS", "ANYTHING", "ANYWHERE", "APPLIES", "APPOINTMENT", "ARITHMETIC", "ARRIVAL", "AVAILABLE", "AbortError", "Adding", "Additive", "America", "Anthropic", "Ariane", "Auditor", "Author", "BACKED", "BACKGROUND", "BACKUP", "BACKWARDS", "BECAUSE", "BEFORE", "BEHIND", "BE`

#### `tests/seed_never_syncs_platform.js:147` — **19% of the derived set is phantom**

* **owner:** **UNASSIGNED** -- owner map `None`/`NONE`, and NO session has ever named it in a claim
* **app:** `sairnvet.html` — derived set **9434 raw → 7683 stripped**
* **the exact line, read from the file at HEAD:**

      return (m[2].match(/'([\w]+)'/g) || []).map((s) => s.replace(/'/g, ''));

* **phantom members:** `["0b", "114", "119", "1234", "12h", "13", "134", "137", "156K", "171", "172", "176", "177", "1886", "18K", "198K", "1b", "200KB", "21", "284", "295", "315", "401s", "403", "404s", "409", "41", "43", "482", "503", "52K", "54", "55889165", "6257", "64K", "64KB", "65536", "72", "76K", "7cd70f83", "847", "866", "89K", "8pm", "A0", "ABOUT", "ABOVE", "ABSENCE", "ACCEPTED", "ACCEPTING", "ACCESS", "ACROSS`

#### `tests/demo_seed_licence_scope.js:216` — **18% of the derived set is phantom**

* **owner:** **UNASSIGNED** -- owner map `None`/`NONE`, and NO session has ever named it in a claim
* **app:** `stonedesk.html` — derived set **141 raw → 116 stripped**
* **the exact line, read from the file at HEAD:**

      const safe = new Set((html.slice(i, html.indexOf('];', i)).match(/'(sd_[a-z_]+)'/g) || [])

* **phantom members:** `["sd_ap_bills", "sd_bidboard_v", "sd_cg_history", "sd_damage_claims", "sd_employee_auth", "sd_employee_profiles", "sd_equipment_v", "sd_hr_employees", "sd_manifest_stops", "sd_pin_", "sd_progress_photos", "sd_rec_log", "sd_remnants", "sd_shared_knowledge_schema", "sd_slab_lineage_schema", "sd_stoneyard_v", "sd_sub_auth", "sd_sub_portal_schema", "sd_subcontractors_v", "sd_training_records", "sd_ts_`

#### `tools/orphan_register_check.py:163` — **16% of the derived set is phantom**

* **owner:** **UNASSIGNED** -- owner map `None`/`NONE`, and NO session has ever named it in a claim
* **app:** `stonedesk.html` — derived set **132 raw → 111 stripped**
* **the exact line, read from the file at HEAD:**

      names |= set(re.findall(r'\b(sd_[a-z_]{3,})\b', read(os.path.join(d, fn))))

* **phantom members:** `["sd_ap_bills", "sd_cg_history", "sd_damage_claims", "sd_employee_auth", "sd_employee_profiles", "sd_hr_employees", "sd_manifest_stops", "sd_pin_", "sd_progress_photos", "sd_rec_log", "sd_remnants", "sd_shared_knowledge_schema", "sd_slab_lineage_schema", "sd_sub_auth", "sd_sub_portal_schema", "sd_training_records", "sd_ts_active", "sd_ts_entries", "sd_warranties", "sd_waste_events", "sd_write_faul`

#### `tests/sen_hydrate_comparator_review_probe.js:209` — **7% of the derived set is phantom**

* **owner:** **UNASSIGNED** -- owner map `None`/`NONE`, and NO session has ever named it in a claim
* **app:** `sairnsenior.html` — derived set **14 raw → 13 stripped**
* **the exact line, read from the file at HEAD:**

      const lit = (names[0] || '').match(/'(senHydrate\w+)'/g) || [];

* **phantom members:** `["senHydrateX"]`

#### `tests/sen_hydrate_comparator_review_probe.js:210` — **7% of the derived set is phantom**

* **owner:** **UNASSIGNED** -- owner map `None`/`NONE`, and NO session has ever named it in a claim
* **app:** `sairnsenior.html` — derived set **14 raw → 13 stripped**
* **the exact line, read from the file at HEAD:**

      const vr = (names[1] || '').match(/'(senHydrate\w+)'/g) || [];

* **phantom members:** `["senHydrateX"]`

#### `tests/sairnlegacy_session_gate_review_probe.js:202` — **7% of the derived set is phantom**

* **owner:** **UNASSIGNED** -- owner map `None`/`NONE`, and NO session has ever named it in a claim
* **app:** `sairnlegacy.html` — derived set **15 raw → 14 stripped**
* **the exact line, read from the file at HEAD:**

      const p = m.match(/var (\w+)\s*=\s*'([^']+)'/);

* **phantom members:** `["prole"]`

#### `tests/local_only_shape_probe.py:102` — **6% of the derived set is phantom**

* **owner:** **UNASSIGNED** -- owner map `None`/`NONE`, and NO session has ever named it in a claim
* **app:** `sairndental.html` — derived set **16 raw → 15 stripped**
* **the exact line, read from the file at HEAD:**

      OLD_WRITE_RE = re.compile(r"\w*Data\(\s*'write'\s*,\s*'(\w+)'")

* **phantom members:** `["dnt_complaints"]`

#### `tests/local_only_shape_probe.py:102` — **5% of the derived set is phantom**

* **owner:** **UNASSIGNED** -- owner map `None`/`NONE`, and NO session has ever named it in a claim
* **app:** `sairndesign.html` — derived set **20 raw → 19 stripped**
* **the exact line, read from the file at HEAD:**

      OLD_WRITE_RE = re.compile(r"\w*Data\(\s*'write'\s*,\s*'(\w+)'")

* **phantom members:** `["specitems_bulk"]`

#### `tests/sairnbiz_incidents_kpi.js:264` — **3% of the derived set is phantom**

* **owner:** **UNASSIGNED** -- owner map `None`/`NONE`, and NO session has ever named it in a claim
* **app:** `sairnbiz.html` — derived set **33 raw → 32 stripped**
* **the exact line, read from the file at HEAD:**

      const names = (m[1].match(/'(sb_\w+)'/g) || []).map((x) => x.replace(/'/g, ''));

* **phantom members:** `["sb_employee_auth_schema"]`

#### `tests/sairnbiz_server_backup.js:191` — **3% of the derived set is phantom**

* **owner:** **UNASSIGNED** -- owner map `None`/`NONE`, and NO session has ever named it in a claim
* **app:** `sairnbiz.html` — derived set **33 raw → 32 stripped**
* **the exact line, read from the file at HEAD:**

      const client = (clientList.match(/'(sb_[a-z_]+)'/g) || []).map((s) => s.replace(/'/g, '')).sort();

* **phantom members:** `["sb_employee_auth_schema"]`

#### `tools/orphan_register_check.py:134` — **1% of the derived set is phantom**

* **owner:** **UNASSIGNED** -- owner map `None`/`NONE`, and NO session has ever named it in a claim
* **app:** `stonedesk.html` — derived set **1852 raw → 1832 stripped**
* **the exact line, read from the file at HEAD:**

      for m in re.finditer(r'(\w+)=([^\s]*)', line[len('// @REGISTER '):]):

* **phantom members:** `["0", "A", "SAIRN_AI_RATE_LIMIT_MODE", "_deleted_at", "canonical", "canonical_key", "dcCtx", "dcMode", "dcZoomLevel", "deleted", "module", "offsetIn", "orphan_keys", "py", "removed", "reservedFor", "retired_keys", "sbSyncPaused", "scope", "scoreMatch"]`

#### `tests/sairnlegacy_processions_isolation.js:72` — **1% of the derived set is phantom**

* **owner:** **hank** (named in a hank claim; owner map says NONE = UNKNOWN)
* **app:** `sairnlegacy.html` — derived set **144 raw → 143 stripped**
* **the exact line, read from the file at HEAD:**

      const gated = [...mapBlock.matchAll(/([a-z_]+):\s*'/g)].map((m) => m[1]);

* **phantom members:** `["u"]`

#### `tests/stonedesk_server_backup.js:47` — **1% of the derived set is phantom**

* **owner:** **hank** (owner map, LAST_CLAIM)
* **app:** `stonedesk.html` — derived set **166 raw → 165 stripped**
* **the exact line, read from the file at HEAD:**

      for (const m of body.matchAll(/(\w+):\s*'(\w+)'/g)) out[m[1]] = m[2];

* **phantom members:** `["_src"]`

#### `tools/duplicate_global_check.py:69` — **0% of the derived set is phantom**

* **owner:** **cc** (named in a cc claim; owner map says NONE = UNKNOWN)
* **app:** `stonedesk.html` — derived set **342 raw → 341 stripped**
* **the exact line, read from the file at HEAD:**

      WINDOW_ASSIGN_RE = re.compile(r'window\.([A-Za-z_$][\w$]*)\s*=\s*function\s*\(')

* **phantom members:** `["renderMarkdown"]`

#### `tests/seed_never_syncs_platform.js:250` — **0% of the derived set is phantom**

* **owner:** **UNASSIGNED** -- owner map `None`/`NONE`, and NO session has ever named it in a claim
* **app:** `stonedesk.html` — derived set **553 raw → 552 stripped**
* **the exact line, read from the file at HEAD:**

      const getRe = /function (\w+)\s*\(\s*\)\s*\{/g;

* **phantom members:** `["saUnlock"]`

#### `tools/duplicate_global_check.py:68` — **0% of the derived set is phantom**

* **owner:** **cc** (named in a cc claim; owner map says NONE = UNKNOWN)
* **app:** `stonedesk.html` — derived set **1093 raw → 1092 stripped**
* **the exact line, read from the file at HEAD:**

      FUNC_DECL_RE = re.compile(r'function\s+([A-Za-z_$][\w$]*)\s*\(')

* **phantom members:** `["saUnlock"]`

### The four patterns that would not compile out of their literal

Named rather than dropped. Each is a regex assembled across more than one source line, so a single-line extraction cannot rebuild it — **these are NOT cleared, they are UNMEASURED**, and that is a different verdict.

* `tests/licence_rekey_isolation.js:178` — Invalid regular expression: /(setItem\('/g: Unterminated group

      const storeRe = new RegExp(

* `tools/csv_formula_injection_check.py:203` — missing ), unterminated subpattern at position 36

      defined = set(re.findall(

* `tools/sairn_ai_fact_scan.py:99` — missing ), unterminated subpattern at position 0

      PROMPT_MARKER = re.compile(

* `tools/stale_row_sweep.py:124` — missing ), unterminated subpattern at position 1

      PATH_RE = re.compile(r'`([A-Za-z0-9_][A-Za-z0-9_./-]*\.'

### One app could not be measured at all, and it is named

`sairncash.html` — no JS candidate reads it, so no stripped copy was written, so the python patterns that do read it were skipped. **UNMEASURED, not clean.**

### The fix, for whoever takes each one

One line, and the library already exists:

    const { stripComments } = require('./lib/strip_comments.js');
    // then derive from stripComments(src), never from src

**And add the control, because the fix without it is unverifiable:** an arm that runs the extractor over a synthetic source carrying the same text in code AND in a `//` and a `/* */` comment, asserting the first IS found and the second is NOT. `tests/phi_cache_scoped_to_user.js` arm 5e is the worked example — ablated, it takes the probe from exit 0 to exit 1 in all four apps.

**Do not fix it by exempting the phantom members.** That was the tempting fix in batch 16 and it would have put a key into an exemption list to satisfy a checker, after which the next real one looks like more of the same.

---

## SEQ 17-B -- A FALSE-POSITIVE CLASS IN `tools/truthy_sum_check.py`: the LEFT operand of a `*`

**To: whoever owns `tools/truthy_sum_check.py`. The owner map says
`owner: None, basis: NONE` and no session has ever named it in a claim, so this is
UNASSIGNED rather than anyone's. `tests/run_truthy_sum_probe.py` IS mine
(`owner: fourth, basis: LAST_CLAIM`) and I did not change it either, because the
defect is in the subject and not in the probe.**

**THE CLASS.** The checker reports a term that is the LEFT operand of a `*`, where
the product is always a number and therefore safe:

    stonedesk.html:26732   var stockValue=all.reduce((s,i)=>s+(i.qty||0)*(i.cost||0),0);
    stonedesk.html:28063   var x=sc.ox+(c.x||0)*sc.sx, y=sc.oy+(c.y||0)*sc.sy;
    stonedesk.html:28094   var x=sc.ox+(c.x||0)*sc.sx, y=sc.oy+(c.y||0)*sc.sy, ...

**AND LINE 26732 IS THE PROOF, IN ONE EXPRESSION.** In
`s+(i.qty||0)*(i.cost||0)` the checker reports **`i.qty`** and correctly ignores
**`i.cost`**. Same line, same operator, same shape, opposite verdicts -- so the
handling exists for the RIGHT operand and is absent for the LEFT. Its own arm 2
*("a `*` term alone is NOT reported -- `*` coerces, `+` does not")* asserts exactly
the rule it is failing to apply on this side.

`*` coerces in **both** directions: `('500'||0) * 2` is `1000`, a number, so
`s + that` is numeric addition no matter what the field holds. There is no
arithmetic judgement to make here.

**WHAT I DID INSTEAD OF PATCHING IT.** All five occurrences (3 keys: `c.x`, `c.y`,
`i.qty`) are now baselined with the reason written into
`tools/truthy_sum_baseline.json`, each entry ending **"Remove this entry when the
checker handles the left operand."** That is a baseline standing in for a checker
fix, and the entry says so rather than reading as a judgement about the app.

**THE FIX, and it needs an arm in both directions.** The classifier already decides
"is this term the right operand of a `*`"; the same test applied to the following
significant character answers the left-operand case. **Add an arm per direction** --
`s + Number(a||0) * (b||0)` (right, already covered by arm 2) and
`s + (a||0) * b` (left, currently reported) -- because a one-sided fix here is what
produced the one-sided bug.

---

## SEQ 17-C -- 24 DRIFTED citations across four apps, attributed PER CELL, and NONE repointed

**`tools/citation_line_drift_check.py` run with BOTH required flags every time** --
`--app` and `--prefix`, because the tool refuses with exit 2 on either alone and
*"neither is guessed from the other"*. That refusal is what I misread as a regression
last batch; it is in the batch-16 rule log.

| app | prefix | ANCHORED | SOUND | DRIFTED | INCONCLUSIVE |
|---|---|---|---|---|---|
| `sairncare.html` | `alf_` | 11 | 6 | **9** | 3 |
| `sairnsenior.html` | `sen_` | 9 | 0 | **7** | 2 |
| `sairndental.html` | `dnt_` | 3 | 1 | **1** | **20** |
| `sairnbuild.html` | `bld_` | 24 | 4 | **7** | 0 |
| **all four** | | **47** | **11** | **24** | **25** |

The 24 extracted line-by-line AGREE with the four summary lines, checked rather than
assumed.

### Why this is attributed per CELL and not per file

`docs/CRITICALITY-TIERS.md` is one file and it is not one author's: it has been named
in claims by **cc, cody, fourth, hank and hover**, it is in **no live claim's FILES**
at this HEAD, and its rows are authored per RESOURCE by whoever read that resource out
of the app. So *"files you own"* has no useful answer and *"cells you own"* does --
and the attribution is in each cell's own prose, which is where this register already
records it.

### NOTHING WAS REPOINTED, and the tool is the reason

Its own output says *"the arrow is a CANDIDATE, not a correction to apply"* and
*"a cell may cite a render or field-construction site DELIBERATELY ... this resolves
write sites only, so it cannot tell those from a stale citation."* Repointing 24
citations on the strength of an arrow is exactly the mechanical edit that warning
exists to stop. **0 fixed: no cell among the 24 is attributed to fourth.**

### THE ONE FINDING THAT IS NOT A ROUTING: the tool proposes repointing a citation AT A COMMENT

**`sen_settings :6355 -> :5774` and `:6359 -> :5774`.** `sairnsenior.html:5774` reads:

      // There is no `st('sen_settings')` because there must not be one: this

It is a **comment**, and it is the comment that exists specifically to record that the
write does not exist. The tool is offering, as the write site, the line that says there
is no write site.

**THIS IS THE THIRD INDEPENDENT INSTANCE OF PR 1.2 THIS BATCH, AND IT IS THE SAME
COMMENT BLOCK AS THE FIRST.** Batch 16's phi-cache arm counted that block as two
writes to `sen_settings`; SEQ 17-A found 47 more derived sets that shrink when
comments go; and this is a third tool, `citation_line_drift_check.py`, resolving a
write site INTO that same block. One comment, three checkers, three different wrong
answers -- which is **convention 25's trigger met by the platform rather than by one
tool**: three false-positive classes is a design signal, not three bugs.

**Note the tool is RIGHT in the other direction at the same time:** it also reports
`sen_settings` as INCONCLUSIVE for the `api/sd-data.js` citations, with the correct
reason, and the comment block itself predicted that verdict and says it is correct.
So the tool's refusal path is sound and its repointing path is not.

**Routed, not patched:** `tools/citation_line_drift_check.py` is not in my FILES and
the fix belongs with the SEQ 17-A sweep rather than as a one-off -- it is the same
one-line change (`stripComments()` before resolving) plus the same both-directions
control arm.

### The 24, by cell owner

```
OWNER: H1, hank   -- 8 citation(s)
  alf_staff                    :1908    -> :3357    offset +1449     register row line 256
        (the cited line is INSIDE a declaration block, which is why the first detector called it sound)
  alf_staff                    :1908    -> :3357    offset +1449     register row line 256
        (the cited line is INSIDE a declaration block, which is why the first detector called it sound)
  alf_staff                    :4393    -> :3383    offset -1010     register row line 256
  alf_staff                    :4393    -> :3383    offset -1010     register row line 256
  alf_staff                    :4441    -> :3383    offset -1058     register row line 256
  alf_staff                    :4441    -> :3383    offset -1058     register row line 256
  alf_staff                    :4582    -> :3383    offset -1199     register row line 256
  alf_staff                    :4582    -> :3383    offset -1199     register row line 256

OWNER: UNATTRIBUTED -- the cell names no session and no finding id   -- 12 citation(s)
  bld_comm_log                 :299     -> :3415    offset +3116     register row line 210
  bld_comm_log                 :6811    -> :6864    offset +53       register row line 210
  bld_deliveries               :813     -> :3325    offset +2512     register row line 213
  bld_warranty                 :1053    -> :3424    offset +2371     register row line 238
  bld_warranty                 :1053    -> :3424    offset +2371     register row line 238
  bld_warranty                 :6887    -> :6953    offset +66       register row line 238
  bld_warranty                 :6904    -> :6953    offset +49       register row line 238
  sen_branches                 :4036    -> :5388    offset +1352     register row line 554
  sen_branches                 :4368    -> :5388    offset +1020     register row line 554
  sen_caregivers               :5476    -> :2693    offset -2783     register row line 555
  sen_franchise_agreements     :4567    -> :4790    offset +223      register row line 558
  sen_training_rules           :3432    -> :3589    offset +157      register row line 565

OWNER: hank   -- 4 citation(s)
  alf_activities               :4634    -> :4686    offset +52       register row line 244
  dnt_vendor_contacts          :6044    -> :6124    offset +80       register row line 318
  sen_settings                 :6355    -> :5774    offset -581      register row line 563
  sen_settings                 :6359    -> :5774    offset -585      register row line 563
```

**`dnt_` is the row worth a second look for a different reason:** 20 of its 25
citations are INCONCLUSIVE, against 0 for `bld_`. That is not drift and is not a
defect in the register -- it is a resource family with no local write site to anchor
to, which is the same honest state `sen_settings` is in. Reported so nobody reads the
low DRIFTED count as health.

