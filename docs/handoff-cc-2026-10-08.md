# Handoff — cc, batch 17 (b3) — 2026-10-08

**Subject: batch 17 (b3) — Tier A, the Maine seed, `superseded_by`, the
`gh_push` bare-run guard, the owner map's NONE split, hank's parked scrutiny
stash, `SELF_EXCLUDED`, the open-work-index read ceiling, the verification
sweep, and methodology.**

**Final local HEAD: `c5cae242`.** The batch opened 2026-10-07; the date rolled
over mid-batch, which is why the claim and early commits say the 7th.

---

## READ THIS FIRST — NOTHING IS PUSHED

**12 commits are local only. `main` is 12 ahead / 66 behind `origin/main`.**

The publish attempt is recorded, not glossed: `python tools/sairn_claim.py claim
cc` exited **3 — NOT CLAIMED**. The claim commit (`40dfac5c`) is on disk and
therefore **invisible to every other clone**. The push's rebase stopped with:

```
last error: Could not apply 5f0eb6cb... fix(scrutiny ledger): ...
```

`5f0eb6cb` touches `docs/scrutiny-flags.json`, which **cody's push gate also
writes**, so a conflict there is expected rather than surprising. That file
carries `merge_policy: {strategy: union-by-identity, records_key: flags,
identity: [sha, path]}` and **`tools/sairn_rebase_resolve.py` already knows how
to merge that shape** — that is the intended path, and it is the next action for
whoever picks this up. Do not hand-merge the ledger.

**A clean `git push` would not have been proof either** (PR §3.2). There is no
push to verify, so there is nothing claimed about `origin/main` below.

---

## State check, before anything else

| dispatch item | state | commit |
|---|---|---|
| 1 state check | done | — |
| 2 Tier A, my own, most overdue first | **done** — all 3 discharged, cc-owned open 3 → 0 | `609af817` |
| 3 Maine seed | **done** — proved by a changed compute | live write, no repo change |
| 4 `defect_register.py` Option A | **done** — 12/12, 3 runs byte-identical, register NOT touched | `e9780ea3` |
| 5 `gh_push.py:182` bare-run guard | **done** — 9/9, remote byte-identical before and after | `cd8b815b` |
| 6 `tool-owner-map.json` NONE split | **done** — 18/18 lock, UNRECORDED 614 / UNKNOWN 0 | `7b82997b` |
| 7 hank's scrutiny stash | **done** — all 20 rows DISCARDED with cause, root cause fixed | `5f0eb6cb` |
| 8 Tier A takeover, two oldest past 48h | **done** — both at 261h, takeover recorded | `475a2ed9` |
| 9 `SELF_EXCLUDED` = 8 | **done** — 3 stale counts corrected, none bumped to 8 | `9e4ea398` |
| 10 index read ceiling | **done** — 2 CLAUDE.md pointers, `--standing-doc-sizes` added | `785a8c99` |
| 11 verification sweep | **done** — and it found a defect in item 6 | `d562e53f`, `b0a128bc` |
| 12 run history for every cited green | **done** | `b0a128bc` |
| 13 methodology | **done** — paste-ready, 5 entries + 1 self-finding | `c5cae242` |
| final | this file, then the report | — |

Items 2, 3, 4, 5 and 8 landed **before** a mid-session compaction. Their
evidence is quoted from the per-item checkpoint record and is labelled as such
wherever a figure comes from there rather than from a run I can attest to
directly.

---

## Item 3 — the Maine seed. The only record of this is prose; no repo file changed

```
SAIRNLAW_LICENSE_KEY=LAW-PINNACLE-2026 SAIRNLAW_EMP=sairn-demo-owner \
  SAIRNLAW_PIN=80362514 python tools/load_deadline_seed.py maine
```

**`SAIRN_SEED_GATE=off` was NOT set at any point in this batch.**

Verified by a **changed compute on byte-identical inputs**, which is the only
form of proof that distinguishes "the loader ran" from "the rules are live":

| | before | after |
|---|---|---|
| deadline request | `503 NOT_PROVISIONED` — *"No deadline rules are loaded for me. No date is produced."* | `200`, **deadline 2026-12-10** |
| `sairn_load_state_check --app sairnlaw --key LAW-PINNACLE-2026` | exit **1**, MISSING 14 + 2 | exit **0**, MISSING 0 / STALE 0 / EXTRA 0 |

Inputs confirmed byte-identical between the two runs with `cmp`. The loader
printed *"All 2 calendars and 14 rules loaded."* and exited 0. The date checks
out by hand: trigger 2026-11-20 + 20 calendar days = 2026-12-10, a Thursday, so
no weekend shift applies.

---

## Item 7 — hank's parked stash: DISCARDED, and the reason is the finding

Read **read-only** with `git show stash@{N}:docs/scrutiny-flags.json` in hank's
clone. Nothing was popped, applied or written there; his `git status` is
identical before and after.

**20 new `(sha, path)` identities across five stashes. They are not 20 facts** —
they are **three paths re-keyed against seven shas**, the same push refused and
rewritten six times. **Six of the seven shas are orphaned**, checked in **hank's
own clone** rather than inferred from their absence in mine, which is the
difference between *rebased away* and *never fetched*.

**And the one survivor was still wrong, which is what turned this from a tidy-up
into a defect.** `bf174f30` resolves and is an ancestor of `origin/main`, so by
the rule I applied to Tier A its three rows would have been applied. They are
false on their face: it changes `docs/MASTER-PLAN.md`,
`docs/TOOLING-INVENTORY.md`, `docs/defect-density-register.json`,
`docs/tier-a-reviews.json` and `docs/traceability-matrix.md` — and **none** of
the three test files its rows name.

**Root cause, in my own code.** `tools/sairn_push_gate_hook.py` computed flags
from a diff over the whole range `base..tip` and recorded them under `tip`. The
2026-10-06 correction in that same block fixed the **shape** of the key and left
the **referent** wrong.

**No re-seat was attempted and none was guessed.** Subject-matching an orphan to
its landed replacement is provably ambiguous here: `a721bb25` and `ce54a630`
share the subject *"the three records this batch's fixes owe"* and **no landed
commit carries it**.

**Backfilled from the real commits instead** — the classifier run against each
landed commit's own diff, through the real `scrutiny_record` so the merge policy
and dedup apply. The 20 rows reduce to **four facts**, each self-verifiable with
`git show <sha> -- <path>`:

| sha | path | level |
|---|---|---|
| `320ddabe` | `tests/run_tool_usage_refusal_probe.py` | WEAKENING |
| `72d757ef` | `tests/run_audit_event_type_probe.py` | WEAKENING |
| `4ec0d5d5` | `tests/sd_data_write_attribution_three_apps.js` | CHANGE |
| `56bbce5e` | `tests/sd_data_write_attribution_three_apps.js` | CHANGE |

All four verified **ANCESTOR of `origin/main`** before writing. Flags 90 → 94,
diff 47 insertions / 0 deletions — append-only, as the policy says. A first
attempt rewrote the file with `sort_keys` and produced a 412/365 diff of pure
formatting noise; reverted and redone through the recorder.

**NOT retroactively complete, and the file says so.** Only the commits those
stashes were about were backfilled. Earlier `origin/main` commits that touched a
self-checking file while the tip-keyed bug was live are still unflagged and
nothing knows which they are.

---

## Item 11 — the sweep found a defect in work I had already reported green

**This is the most useful thing in the batch.** `python tools/tool_owner_map.py
--check` exited **0** at `7b82997b`, the commit where I reported it clean, and
**1** three of my own commits later. The entire diff was one row: a
`last_commit` field I had added, moving because a later commit of mine touched
that file. **614 rows carry that basis**, so the field had quietly turned the
map into a regenerate-after-every-commit obligation.

Fixed at `d562e53f`. Ablation in an isolated worktree, because otherwise this is
a story rather than a cause:

| state | `--check` |
|---|---|
| fixed tool, regenerated JSON | **exit 0** |
| then a commit touching an `UNRECORDED` file | **exit 0** ← the fix |
| `last_commit` restored, same commit | **exit 1** ← the cause |

Full sweep table, run history with the **first run in its own column**, and the
compaction boundary: `docs/2026-10-08-cc-routed-b17.md`.

**Three of fourteen exits are non-zero and all three are correct** —
`va_rule_currency.py` bare = **2** (it must refuse), `--standing-doc-sizes` =
**1** (7 documents over), `cross_tenant_isolation_scope.py` = **1** (findings).
The other eleven are 0. `cross_tenant_isolation_scope.py` was also **killed at a
120s ceiling** on one attempt; that is reported as a non-result, not a failure.

---

## Routed — with the reason each is not mine

| to | what |
|---|---|
| **hank** | Five stashes named *"cc scrutiny rows"* (rounds 2–6) **may be dropped** — `stash@{0}`, `{1}`, `{2}`, `{4}`, `{5}` as of 2026-10-08. All 20 rows discarded with cause; the four real facts are backfilled. `stash@{3}` is his own register records and is untouched. **He is not blocked** — his own live claim item (13) parks it deliberately. I did not drop them: another clone's stash is not mine to write. |
| **hank** | Six commits **orphaned in his own clone**, nothing re-seated: `47d69604`, `4d2e2964`, `75eab855`, `a721bb25`, `ce54a630`, `f0df3f91`. He has the reflog and the rewrite map. **Candidates only, not facts:** `320ddabe`, `661ff87c`, `e49b9e37` look like three of the landed replacements by subject, and subject-matching is ambiguous there. |
| **whoever regenerates `TOOLING-INVENTORY.md`** | `python tools/tooling_inventory.py --check` exits **1**. Verified identical against HEAD's own copy in a detached worktree, so **not** a regression from my `--standing-doc-sizes` addition. Regenerating would sweep in other sessions' tools. |
| **fourth** | Five paste-ready methodology entries in `docs/2026-10-08-cc-methodology-b17.md`. `docs/METHODOLOGY.md` and `docs/2026-09-13-cross-domain-disciplines.md` are **declared by fourth under a live claim**, re-checked at final HEAD, and neither is touched. |
| **whoever takes `SELF_EXCLUDED`** | Deriving the tuple from the predicate the importer arm already computes. Only its **stale count** was fixed; the structural item is open. **fourth reached the same conclusion independently as SEQ 13-C** and is credited. |
| **each owner** | **7 standing documents exceed 400,000 bytes**, not one: open-work index 2,380,170; `SAIRN-ACTIVE-WORK-cc.md` 1,091,609; `-fourth` 1,002,355; `-hank` 945,301; `-cody` 775,962; `docs/CRITICALITY-TIERS.md` 485,668; `SAIRN-ACTIVE-WORK.md` 404,392. `--standing-doc-sizes` now reports it on every run. |

---

## Declared — conflicts, deviations and things I got wrong

**My claim expired mid-run and I did not notice for seven commits.** Found at
item 13 while re-checking who held `METHODOLOGY.md` — **not** by checking my own
claim. **Items 6 through 12 landed under an expired claim**, invisible to every
other clone as live work. No collision resulted: every write target was
re-checked against the live claim list immediately before writing and all were
declared by nobody. But that is per-item conflict checks plus luck, not the
claim system working. The fix I did not have: **the per-item checkpoint should
re-check my own claim's age, not only other sessions' claims.** Claims expire at
4 hours; a batch this size runs longer.

**Files I wrote that were not in my original claim's FILES list**, each declared
rather than discovered later:

* `tools/va_rule_currency.py`, `tests/run_tool_usage_refusal_probe.py` —
  stale-citation repairs, one of them stale **because of my own `cd8b815b`**.
* `tools/sairn_push_gate_hook.py`, `tests/run_scrutiny_flag_probe.py` — fixing
  the generator that produced the garbage item 7 discarded is what makes the
  discard safe rather than a deferral.
* `tools/cross_tenant_isolation_scope.py` — mine by the owner map (cc,
  CONTESTED), no live claim.
* `docs/SAIRN-OPEN-WORK-INDEX.md` — **a direct deviation from my own claim
  text**, which said it "is still NOT written". One line. It is where the stale
  `SELF_EXCLUDED` count was stated worst. **PR §2.1 respected:** a
  unique-substring replacement inside one cell, not a split on `|`, and the pipe
  count on line 232 is **8 before and 8 after**, verified.

**`tools/tool_owner_map.py` carries `# OWNER: cody`** while cody's live claim
does not list it — so no write conflict, but the authoritative owner is cody and
the edit was made on dispatch, not on my own authority.

**`docs/defect-density-register.json` was NOT touched**, per the item's own
division of labour (cody applies the field to the 4 records), and that holds
regardless of cody's claim having released.

**Not done deliberately:** `gh_push.py:182` was not given arms in
`run_tool_usage_refusal_probe.py` even though it is now fixed and mine —
`tests/run_gh_push_argv_probe.py` already locks that line and a second lock is a
second copy of the same check.

I closed only findings I originated and reclassified none. I read and referenced
no auditor tool.

---

## Next session, in order

1. **Publish.** `tools/sairn_rebase_resolve.py` for the
   `docs/scrutiny-flags.json` conflict on `5f0eb6cb`, then re-run the **same**
   `sairn_claim.py claim cc` command — it is a retry and adds no second entry.
   12 commits are waiting and nothing is visible to any other clone until then.
2. **Confirm the claim is live** with `python tools/sairn_claim.py list` before
   trusting it. A claim that is committed and not pushed is not a claim.
3. **Re-run the sweep at whatever HEAD the rebase produces.** Every figure in
   `docs/2026-10-08-cc-routed-b17.md` is measured at `d562e53f`, and a rebase
   onto 66 commits of other people's work is exactly the condition under which
   item 11's own lesson applies: a green is evidence about the HEAD where it
   ran.
