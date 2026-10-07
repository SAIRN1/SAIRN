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
