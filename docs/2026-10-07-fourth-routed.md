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
The gate half is FIXED BY ME at `afd29524` and is not routed — this row is the
LEDGER DATA, which I did not touch.**

    00030f2d11b7b1e426724f90d1a3fb69c3cfcf6b
    13e40c9d79b7ac7b7a11f52d982899a9fe6b4458
    773fc2189cb044cc5d74d938171edf465045bbf8
    7d15d0a27af0fcee8be982dd49f26d541d2d06ba
    a9e35feef967b5c7440cd4dc13bd281f78b6ca0f
    c4dd292fd8a8ee8ad78ce3ab177511494e9b09ae
    e4b3f21a2ceb371e7364613665f004be58645749

All seven are 40-char, all seven `ORPHANED` by the command above. Before
`afd29524` the gate resolved them with `rev-parse --verify`, found them, diffed
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
