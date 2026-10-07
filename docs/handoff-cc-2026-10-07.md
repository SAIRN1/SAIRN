# CC handoff — 2026-10-07, batch 12, the ANDON batch

**Fourth handoff in this run.** Batch 9 → `handoff-cc-2026-10-06.md`; batch 10 →
`-06b`; batch 11 → `-06c`; this is batch 12.

**Every figure carries its command, its commit and its date. Every exit code was
read from the program's own stdout or from a `tools/capture_exit.py` status
file — never from a harness completion status.** Every green states how many
times it ran against that SHA and what the first run returned.

**Transcript:** this session's conversation. No file on disk — it has to come
from the terminal scrollback.

---

## 1. Claims held — item 10, at the top as instructed

**ONE: subject `cc`, batch 12.** At the start of this batch I held **none**
(released at the end of batch 11; `sairn_claim.py list` showed only `fourth` and
`hover2`).

**No claim was stacked on a path another agent holds.** Three conflicts were
declared in the claim text and none overridden:

| path | holder | what I did |
|---|---|---|
| `docs/tier-a-reviews.json` | **cody** | read only. Item 5 **not taken** |
| `docs/tool-owner-map.json` | **cody** | read only. Item 6 routed into a doc of mine |
| `docs/METHODOLOGY.md`, `docs/SAIRN-OPEN-WORK-INDEX.md`, `docs/TOOLING-INVENTORY.md` | **hank** | not touched at all |

**Release when this handoff is accepted:**

    python tools/sairn_claim.py release cc

---

## 2. Committed and pushed

| commit | what |
|---|---|
| **`eb430f25`** | the ANDON resolution — end-bounded budget, `--shard`, the sweep marker, 20 new probe arms, the fail-open fix, `--register-absent`, the inventory and routed §18–21 |
| **`08f078fb`** | the `LEDGER NOT WRITTEN` false reassurance, plus the four records the gate and sweep wrote |

**Not yet pushed at the time of writing:** routed §22–23 (the item-6 and item-7
routing tables), the inventory's items 6/7/10, and this file. Next step in §9.

**Verify rather than trust this table:**

    git fetch origin && git rev-list --left-right --count origin/main...HEAD
    git log --oneline -4 origin/main

---

## 3. ITEM 1 — THE ANDON IS RESOLVED

**Why it climbed:** the budget bounded the **START** of the last checker, not
the END of the run. `elapsed >= budget * 0.9` = 540s, checked **before** an
entry begins, so a 137s entry starting at 539s finishes at 676s — within one
second of the 679.9s measured. Per-stage timing across two full runs on an
unchanged tree: **wall 553.7s / 39 entries, then 547.3s / 47 entries.** Flat
wall, eight more entries — so the checkers did **not** get slower; the run is
pinned at the cut and the overshoot is whichever checker straddles it.
`comment_sensitivity_check.py` (137.0s) and `sairn_dead_button_audit.py`
(111.9s) are 248.9s of 553.2s = 45%.

**Fixed three ways:** the budget now bounds the END (an entry is refused if its
last measured duration would not fit, and an unmeasured entry is costed at the
observed MAX); `--shard K/N` at 45% of the ceiling with the rotation persisted
in `docs/report-only-shard-state.txt`; and a `RUNNING`/`DONE` marker so a
ceiling kill leaves an explicit record.

**Five runs after the fix — NONE over 50% of the ceiling:**

```
  run 1  shard=1/5  program= 72.3s  wall= 72.5s  12.1%  exit 0  DONE
  run 2  shard=2/5  program= 93.9s  wall= 94.1s  15.7%  exit 0  DONE
  run 3  shard=3/5  program=154.3s  wall=154.5s  25.7%  exit 0  DONE
  runs 4 and 5 completed the rotation; worst of five 191.7s = 32.0%
  min 72.3  max 191.7  mean 119.6   FIRST RUN: exit 0 at 12.1%
```

**Selftest:** `tests/run_report_only_checks_probe.py` — **20 new arms, ALL
PASS**; whole probe **85 checks, 0 failed, EXIT 0, THREE runs against this SHA,
first run 0.** `--marker` exits **2** on RUNNING, ABSENT and UNREADABLE.

**THE COST IS REAL AND IS NOT HIDDEN: a finding now surfaces on the push whose
shard runs, up to five pushes later.** Every out-of-shard entry is named in
`unrun` as an UNKNOWN for that push.

**STILL OPEN, and it is the actual repair:** the two slow checkers are
**scheduled, not fixed**. Nothing here made them faster. **Exact next step:**
profile `comment_sensitivity_check.py` and `sairn_dead_button_audit.py` and
decide whether either can be bounded or narrowed. Until then the rotation is
carrying them.

---

## 4. ITEM 5 — NOT TAKEN. Current age of cody's claim.

`docs/tier-a-reviews.json` is cody's. **`claimed_at 2026-10-06T17:34:15Z`,
age 4.8h at 2026-10-06T22:23Z** — past the 4h expiry, so `sairn_claim.py list`
does not show it as `[active]`, **but the record has no `released_at` and an
expired timestamp is not a release.** Not taken.

**Re-measured at HEAD `d395d25e`, 2026-10-06T22:23:37Z:** 235 records, 31 open,
204 reviewed, **7 authored by `cc` (ineligible), 24 eligible to `cc`, 0 with a
`reviewer_session` set.** Identical to batch 11, so cody's six have not landed.
**No record of anyone's was reclassified.**

**EXACT NEXT STEP:** when cody releases, **re-measure before acting** — ranks
7–12 as of 22:23Z are `(cody, 2026-09-29T14:34:43Z)`,
`(cody, 2026-09-30T10:58:02Z)`, `(fourth, 2026-09-30T11:08:08Z)`,
`(cody, 2026-09-30T12:08:26Z)`, `(hank, 2026-09-30T12:59:51Z)`,
`(hover2, 2026-09-30T13:59:56Z)`, and cody's six discharges will shift every
one of them.

---

## 5. Open, with the exact next step for each

| # | open item | exact next step |
|---|---|---|
| **1** | the two slow checkers are scheduled, not faster | profile `comment_sensitivity_check.py` (137.0s) and `sairn_dead_button_audit.py` (111.9s); decide bound-or-narrow |
| **2** | `capture_exit.py` has no timeout | **cody's.** Routed with the five-run artifact in `docs/2026-10-06-cc-routed.md` §18, no proposed fix. Nothing for me to do |
| **5** | 24 eligible Tier A obligations, ranks 7–12 mine | wait for cody's release, re-measure, then discharge from the top of the NEW measurement |
| **6** | **67 of 101 routed rows have no owner in the map** | the ownership question itself — `docs/tool-owner-map.json` records 209 of 312 unattributable and it is cody's file |
| **6a** | 1 of my sweep's 6 false exit-2s survives | an `ast` walk, not string blanking — see §6 below for why blanking cannot work |
| **6b** | 7 tools declare a mode their own `--help` does not list | **re-run `--help` against the committed detector first.** That comparison came out of a measurement I discarded and I will not carry one number out of a run I threw away |
| **7** | 2 of the 17 writers exit 2 while writing a status document | read `audit_checkpoint_status.py` and `cron_liveness_check.py`; decide whether a could-not-run page is honest or stale |
| **8** | 55 citations permanently absent | nothing to do — `docs/citation-absent-register.json` records each with its tested cause and the word `resolved` never appears |

---

## 6. The measurement I DISCARDED rather than reported

**My fix for the last false exit-2 blanked string-literal contents before
matching and re-derived all 305 modes. It reported 73 changes, 72 of them to
`(bare)`** — including `tooling_inventory.py --check`,
`exit_status_attributable.py --selftest` and `traceability_matrix.py --check`,
**all three of which I personally ran successfully earlier in the same
session.**

**The cause is structural and no threshold fixes it: the flag literal in a
genuine `if '--check' in argv:` IS a string**, so blanking strings blanks the
real declarations and the quoted copies identically.

**Discarded under my own Rule A from batch 11** — a measurement whose
instrument is broken is not a weak measurement, it is no measurement.
**Reporting "72 tools declare no read-only mode after all" would have been a
confident, precise and entirely false finding**, and it would have looked like
the batch's biggest result.

---

## 7. Defects of mine this batch — eight, cause-tagged, none found by reading

Full table in `docs/2026-10-06-cc-batch-12-inventory.md` §9 and the trailing
section. The headline: **sharding silently dropped 58 of 73 entries from the
report** (found by running the probe), **an unconditional `print` inside a quiet
sweep** broke "a clean sweep stays silent" (round 2 of a 2-round recheck cap),
**the end-bounding read a file this repo's own probe under-measures at
`--budget 20`**, and **`LEDGER NOT WRITTEN` was printed on the success path**
(found by reading the push output).

**Fix-recheck took exactly 2 rounds and did not exceed the cap.**

---

## 8. What this batch did NOT do

* **Did not discharge a review obligation.** 24 eligible; cody holds the file.
* **Did not make the two slow checkers faster** — only scheduled around them.
* **Did not route the 67 unattributed rows to anybody.** No owner exists and I
  did not invent one.
* **Did not route the 7 `--help` disagreements** — they came out of the
  discarded run.
* **Did not read the 101 routed tools.** Exit 1 on this platform usually means
  *findings, report-only*; a row is a thing to look at, not a verdict.
* **Did not touch** `docs/tier-a-reviews.json`, `docs/tool-owner-map.json`,
  `docs/METHODOLOGY.md`, `docs/SAIRN-OPEN-WORK-INDEX.md`,
  `docs/TOOLING-INVENTORY.md`.
* **Built no new tools.** `--shard`, `--marker`, `--register-absent` are modes;
  the probe arms were appended to the probe that already existed.
* **Live-verified nothing against a deployment** — every item is a build-time
  tool, a hook or a document.
* **Closed only findings I originated** and reclassified none.

---

## 9. Still to push

    git fetch origin && git rebase origin/main
    git push origin main:refs/heads/main      # explicit refspec; the gate
                                              # denies "no ref lines on stdin"

Carrying routed §22–23, the inventory's items 6/7/10 and the extra cause tags,
and this file. **CHECK 15 will flag it** — it touched push-gate logic earlier in
the batch — and that is correct.

**A gate-freshness notice fired on `eb430f25`:** *"the push gate that just ran
is NOT the one on origin/main."* True and expected — I had just changed the
gate. **That push's clean pass is a could-not-tell, not a full pass.** The push
after it got the real answer.
