# SAIRN handoff -- cc batch b8 -- 2026-10-14

**Written by:** cc, in `Documents\SAIRN-cc`, on `main`.
**Written BEFORE the report**, at a point where nothing is half-finished: all
six items are committed and on `origin/main`, every suite named below has been
run to completion, no background job is still in flight, and no file is
mid-edit.
**Companions:** `SAIRN-report-cc-b8.txt`, `SAIRN-digest-cc-b8.txt`,
`docs/batch-manifest-cc-b8.json` (6 items, all `done` with re-runnable
evidence).
**Transcript:** this session's scratchpad is
`C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-cc\ac16263c-6d67-4305-aa08-5af5dd4be99b\scratchpad\`
— every figure in the report has its raw log there: `hook_wiring.log`,
`statusline_fix.log`, `prepush_repro.log`, `prepush_repro2.log`,
`prepush_repro_results.json`, `rfg_empty.log`, `rfg_branches.log`,
`red_suite_run.log`, `nhi_selftest_wt.log`, `nhi_live4.log`,
`nhi_wt_after2.log`, `selftest_indep.log`, `uac_run2.log`, `uac_probe.log`,
`attack_point_source.log`, `attack_point_live.log`,
`user-settings-before-b8.json`, `install_user_settings_b8.py`.

---

## Committed / pushed state

**HEAD `385606cb`, `git rev-list --left-right --count origin/main...HEAD` = `0 0`.**
No `--force` in any spelling. **`SAIRN_SEED_GATE` was never used.** Two rebases
during the landing, both resolved by `tools/sairn_rebase_resolve.py`, with the
defect record re-seated onto the rewritten commit each time.

| SHA | what |
|---|---|
| `af71d006` | chore(hooks) — the tracked `SessionStart:compact` group removed, `hooks` is `{}` again |
| `54abe65f` | feat(status line) + fix(register feed gate) — the context percentage, and the refusal that stops blaming a wrapper |
| `811292cb` | fix(red suite check + nhi self-test) — isolation for the registered suites, and a self-test that stops reporting its machine |
| `3a35d129` | feat(unproven arm check) — the fourth signal |
| `2d627c11`, `4dde8ecd`, `385606cb` | chore(defect register) — the record this push owed, re-seated twice |
| `786047ad`, `9862c71c` | chore(derived docs + ledger) — the inventory regenerated, the gate's own scrutiny rows |

**NO HOOK WAS ADDED OR RESTORED. 0 tracked files wire a Claude Code hook** —
measured by parsing every tracked `*settings*.json` / `*hook*.json` for a
non-empty `hooks` key. The two that match are RECORDS, not wiring:
`docs/hooks-disabled-2026-10-13.json` (the 23 cleared hooks, preserved
verbatim on purpose) and `docs/hook-manifest.json` (the four **git** hooks in
`.githooks/`, which are the push gate itself and are not Claude hooks).

---

## The six items

| # | item | state | evidence |
|---|---|---|---|
| 1 | remove the tracked `SessionStart:compact` group | **DONE** | `af71d006`, 2 insertions / 16 deletions, all inside `hooks` and `_hooks_note`; `hook_integrity_check --wiring-only` = INTENTIONALLY DISARMED, exit 0 |
| 2 | standing allow rule for `git -C` under `Documents\SAIRN-*` | **DONE** | `~/.claude/settings.json`: 7 allow rules, **27 derived deny rules**, 7 `additionalDirectories`. See the pick-up instructions below |
| 3 | status line, context % used, red at 70%, all six folders | **DONE** | `tools/sairn_status_line.py`, 21/21 fixtures; one USER-LEVEL `statusLine` entry covers all six; live render `cc | Opus 5 (1M) | ctx 33% of 1000k` |
| 4 | cody-routed record `2026-10-12T01:51:33Z` + the fourth signal | **DONE, and the attack point is still UNVERIFIED by design** | source half re-checked at HEAD; live anonymous call `401 NO_LICENSE`; A4 shipped, 1 finding over 407 files |
| 5 | reproduce before patching; `red_suite_register_check.py:96`; the nhi red self-test | **DONE** | 8-state git reproduction, then the patch; 85 registered entries driven **in a worktree**; nhi self-test exit 0 in a clone AND in a temp worktree |
| 6 | push without force, confirm landed | **DONE** | `0 0` against `origin/main`, HEAD `385606cb` |

---

## Item 2 — EXACTLY what each agent folder must do to pick this up

**Two different things were changed and they propagate differently. Nothing
about this is a guess: it follows from where each file lives.**

**(a) The `git -C` rules and the status line: NOTHING TO FETCH, EVER.** They are
in `~/.claude/settings.json` — `C:\Users\marsh\.claude\settings.json` — which is
**outside every clone and in no repository**. It is already live for all six
folders. What each folder must do is **start a new session** (or `/config`):
Claude Code loads settings at session start, so a session already running keeps
the rules it loaded. No pull, no rebase, no merge.

**(b) The hook removal IS in the repo, and each folder must pull it:**

```
git -C C:\Users\marsh\Documents\SAIRN-hank    pull --rebase origin main
git -C C:\Users\marsh\Documents\SAIRN-cody    pull --rebase origin main
git -C C:\Users\marsh\Documents\SAIRN-fourth  pull --rebase origin main
git -C C:\Users\marsh\Documents\SAIRN-hover   pull --rebase origin main
git -C C:\Users\marsh\Documents\SAIRN-hover2  pull --rebase origin main
git -C C:\Users\marsh\Documents\SAIRN         pull --rebase origin main
```

**MEASURED, read-only, 2026-10-14, so these are facts and not expectations:**

| folder | `hooks` in its working copy now | what the pull will do |
|---|---|---|
| `SAIRN-cc` | **`{}`** | nothing; it is the source of the change |
| `SAIRN-hank` | 1 event (`SessionStart`) | **clean update to `{}`** — no local change to that file |
| `SAIRN-cody` | 1 event (`SessionStart`) | **clean update to `{}`** — same |
| `SAIRN-fourth` | 1 event (`SessionStart`) | **clean update to `{}`** — same |
| `SAIRN` (the original, non-agent clone) | **3 events** (`PostToolUse`, `PreToolUse`, `PreCompact`) **and a locally modified `.claude/settings.json`** | **the pull will REFUSE** rather than overwrite — git will not clobber a local change. That is a safe failure, and whether those three hooks go is **Michael's decision, not mine** |
| `SAIRN-hover`, `SAIRN-hover2` | **not read** | the auditors run their own pull. A build agent does not reach into the auditor clones, including to clear their hooks |

**And the honest limit on item 2, stated rather than buried:** I could not
prove the prompt is gone, because proving it means triggering the prompt this
batch exists to remove. What IS measured: `git -C` ran against
`SAIRN-cody` and `SAIRN-fourth` in both path spellings during this batch with
no prompt. What is NOT measured: whether the harness treats a mid-argument `*`
in a permission pattern as a glob. So four spellings are installed rather than
one, and the directory half (`additionalDirectories`) is installed as well —
belt-and-braces by design. **If a prompt still appears, the next step is in the
report, not another guess.**

---

## Open, and whose — with the exact next step

| item | owner | exact next step |
|---|---|---|
| **6 stale entries in `docs/known-red-suites.json`** | **cody** (holds that file in a live b9 claim) | `python tools/red_suite_register_check.py`. FIVE were RECOVERED at HEAD `4673965e`: `api/sf-auth.test.js`, `tests/push_gate/check8_probe.py`, `tests/run_truthy_sum_probe.py`, `api/sd-data-cross-tenant-dispatchers.test.js`, `tests/run_committer_identity_probe.py`. The SIXTH is `tests/run_selftest_independence_probe.py`, recovered by this batch's nhi fix — it now reports ALL ARMS PASS. **A stale entry absorbs the next real failure of that file**, which is why they are findings and not clutter |
| the `known-red-suites` entry's **wrong diagnosis** | **cody** | the entry for `tests/run_selftest_independence_probe.py` blames `nhi_register.py`'s "unreadable repo root" arm. **That arm passes in both environments** — measured in `nhi_selftest_wt.log` line 14 before any fix. The real cause was the clone-parent cap. Correct the text when deleting the entry |
| `tests/mar_billing_grant.test.js:258` — the one **A4** finding | **cody** (live claim on that file) | `python tools/unproven_arm_check.py --file tests/mar_billing_grant.test.js`. It can report an arm UNPROVEN and persists nothing, so "unproven at most once" can never be enforced for it. REPORT-ONLY; not a gate |
| **the Tier A record `2026-10-12T01:51:33Z` has no verdict written** | **cc**, next batch | `docs/tier-a-reviews.json` was NOT edited: this batch is scoped to `tools/` plus my own settings. The re-check is in the report section 4 and needs transcribing into the record's `verdict` / `reviewed_at` by whoever next holds that file |
| **attack point (2) is still UNVERIFIED and needs a credential** | **Michael** | what is missing is now exact: **(i) a tenant licence key** for SAIRNfreedom/SAIRNscape — the anonymous call is refused at the LICENCE layer (`api/sd-data.js:537`, `401 NO_LICENSE`) before the session gate at `:2004` is ever reached, so no credential-free call can observe the gate at all; **(ii) a session token** for the positive half (that a real session PASSES); **(iii) a service-role key** to seed one row, so a 403-vs-200 distinction is about the gate rather than about an empty table |
| the 3 FMEA drafts the register asked for | any session | `python tools/fmea_draft.py <path> --save` for `tools/red_suite_register_check.py`, `tools/nhi_register.py`, `tools/sairn_status_line.py`. Not written here: three unreviewed drafts filed by the session that caused the defects is the detector-blesses-its-own-fix shape |
| `red_suite_register_check.py` **exits 2 on every ordinary run** | that tool's reader | by design — without `--from-run` it cannot look for UNREGISTERED reds and says so. The pairing is `python tools/known_red_check.py` over a whole-tree log. Not a defect; it is the honest half of a cheap check |
| the two-run half of the **A4** rule | unassigned | still unimplemented and still printed as unchecked every run. It needs a RUNNER that persists each run's unproven set; a static reader cannot see a second run |

---

## Claims held

**`cc`, claimed and pushed as the first action of this batch**, and **not yet
released** — release it with `python tools/sairn_claim.py release cc` once these
three deliverables are uploaded. Status registry row set to `working` at the
start.

**Conflicts declared and NOT overridden (PR §4.3):**
`docs/known-red-suites.json` and `tests/mar_billing_grant.test.js` are in
**cody's live b9 FILES**; `api/sd-data.js` and `docs/defect-density-register.json`
are in **hank's live b9 FILES**. `api/sd-data.js` was READ ONLY (the gate
measurement in section 4) and never written. The defect register WAS written —
`docs/defect-density-register.json` is in hank's FILES and the push gate
REQUIRES a record before it will accept a defect-closing push, so the two rules
collide; I chose the gate, appended one record, and say so here rather than
leaving it to a diff. **Nothing else of another session's was touched.**

**Files written that were NOT in cc's declared b8 FILES**, said out loud:
`tools/prepush_refline_repro.py` (new), `docs/defect-density-register.json`,
`docs/scrutiny-flags.json`, `docs/TOOLING-INVENTORY.md`,
`~/.claude/settings.json` (mine), and this batch's three deliverables. The
claim named `tools/sairn_status_line.py` and both tools exist now.

---

## Three things that will cost the next session time if nobody says them

1. **A `print()` in a status line is the only output you get, so it has to be
   honest about not knowing.** There is no context-usage field in the payload:
   the number comes from the transcript's last `message.usage`. A fresh session
   has none, and the tempting default — 0% — is the one value that reads as
   reassuring. It prints `ctx ??%` with a reason instead, and the fixture that
   locks the display to the threshold is the one worth copying: 139,000 of
   200,000 prints as `70%` and must therefore be red.

2. **`git` runs a pre-push hook even when it is not going to send anything.**
   Measured across eight states: the ref lines are ABSENT when the push is a
   non-fast-forward git will refuse itself, when there is nothing to push, and
   when the branch is up to date — and they are PRESENT through a pipe, a
   `/dev/null` stdin, a `.sh` file and a python subprocess. So "the push came
   from a wrapper" was never the explanation, and b7 spent two refusals
   looking for one. `python tools/prepush_refline_repro.py` re-measures it in
   about twenty seconds.

3. **A self-test that reads the directory it was launched from will go red in
   every isolated worktree, and the register will blame the wrong arm.**
   `nhi_register.py --selftest` failed three arms from a temp worktree because
   the system temp directory holds 80 repositories and the clone enumeration
   correctly refuses to walk them. The fix is a fixture parent for the arms
   that are about the code, and a NOT-CHECKED control for the arms that are
   about the machine. **If a suite's redness changes with where you run it,
   that is the finding — not the thing it reports.**
