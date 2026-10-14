# HANDOFF — fourth / ted, batch b17, 2026-10-14

**Written BEFORE the report**, at a point where nothing is half-finished: items
1–6 are committed and pushed in one commit, `HEAD == origin/main`, the working
tree is clean, no rebase or stash in progress.

**EVERY FIGURE NAMES THE COMMAND THAT PRODUCED IT.** **The sharpest finding of
this batch is a correction to MY OWN ruling** (§3.1), and the second is that one
of the two premises I was handed does not reproduce (§3.5).

**Transcript and working files:**
`C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-fourth\240036a6-0d02-441d-a22d-73ed022c11a3\scratchpad\`
New this batch: `tier_a_verdict_b17.txt`, `commit_b17.txt`.
Logs: `b17_scan1.log`, `tier_a_open.log`, `tier_a_b9.log`,
`tier_a_b9_full.log`, `ainotice_read.log`, `b9_read2.log`, `b9_read3.log`,
`tier_a_discharge.log`, `item3_scan.log`, `item3_scan2.log`,
`item3_scan3.log`, `item4_scan.log`, `item4_scan2.log`, `item4_scan3.log`,
`cite_b12_b14.log`, `defect_check_b17.log`, `register_dups.log`,
`register_owner_b17.log`, `register_pair_b17.log`, `push_b17.log`,
`landed_b17.log`.

---

## 0. COMMITTED / PUSHED STATE

| | | command |
|---|---|---|
| HEAD | `a3457d65` | `git -C <repo> rev-parse HEAD` |
| `origin/main` | `a3457d65` | `git -C <repo> rev-parse origin/main` |
| behind / ahead | **0 / 0** | `git rev-list --left-right --count origin/main...HEAD` |
| working tree | clean | `git status --porcelain` (empty) |
| the b17 work commit | `a3457d65`, 8 files | `git log origin/main --oneline -1` |
| push forced? | **NO** | one rebase, then `031f91c3..a3457d65` |
| `SAIRN_SEED_GATE=off` | **not used**, any form | — |
| `.claude/settings.json` | **not edited, not committed** | `git log --format=%h HEAD --not 1c86243e -- .claude/settings.json` → empty |
| hooks | **0 groups, 0 entries** — unchanged this batch | §5 of the b16 handoff |
| files written outside `docs/` | **0** (plus my three root deliverables) | by instruction |
| b17 manifest | 6 of 6 `done`, close pending the deliverables | `batch_manifest.py --check` |

**`a3457d65` IS THE STATE AT FINALISATION OF THIS HANDOFF** — the report, the
digest, the b17 close and the claim release all land after it. **Re-derive
HEAD.**

---

## 1. ITEM BY ITEM

| # | item | state | exact next step |
|---|---|---|---|
| 1 | manifest first, closed with the env var | **DONE** | **cc fixes `tools/batch_manifest.py:386`** |
| 2 | discharge the Tier A obligation for hank b9; spec the missing test | **DONE — discharged, exit 0** | **cody writes T16; hank acts on two conditions** (§3.1, §3.2) |
| 3 | the `sen_*`/`rf_*` write map, both options | **DONE — both spec'd in full** | **MICHAEL PICKS**; hank then edits one constant (§3.3) |
| 4 | removal paths for the four resources | **DONE — four specs, `sv_scribe_consent` first** | **hank implements; cody writes the failing-first arms** (§3.4) |
| 5 | re-derive b12–b14 citations; the register duplicates | **DONE — 2 fixed; the register premise does NOT reproduce** | **cc: three ordered asks on the register** (§3.5) |
| 6 | push without force | **DONE — `031f91c3..a3457d65`, 0/0** | nothing |
| — | this handoff, before the report | **DONE** | — |

---

## 2. CLAIMS, LOCKS AND HOLDS

| hold | count | detail | command |
|---|---:|---|---|
| repo claims held | **1** | b17, published on `origin/main`; release after the report and digest are up | `sairn_claim.py list` |
| **Tier A obligations assigned to me** | **1 OVERDUE, and it is not the one I discharged** | `tier_a_review_gate.py --list` line 2: hank's `2026-09-27T03:42:29Z` obligation on `alf_staff, sen_visits` is **ASSIGNED TO fourth, held 417h, past the 48h window** — *"anybody may `--takeover`"*. **I did not touch it this batch** | `--list` |
| session locks held | **1** | `fourth.lock`, still carrying the dead `claude_pid 53204` — **six batches** | `ls ~/SAIRN-SESSION-LOCKS/*.lock` |
| locks removed by me | **0** | `rm` is denied and I did **not** route around it | — |
| worktrees besides main | **4** | **none mine** | `git worktree list` |
| `git stash` | **0** | | `git stash list` |

**THE 417-HOUR OBLIGATION IS THE BIGGEST THING I AM LEAVING OPEN**, and it is
mine: 19 obligations are open platform-wide and the oldest one assigned to me
has been held for 17 days. **Exact next step: discharge it or hand it back with
`--takeover`.** It was not in this batch's six items and I did not quietly add
it, but it should be item 1 of b18.

---

## 3. WHAT IS OPEN, AND WHY

### 3.1 THE CORRECTION THAT MATTERS MOST — my own b15 §7.5 ruling was wrong

**`docs/2026-10-14-ai-safeguards-spec.md` §7.5 told hank to delete
`api/ai-notice.js` and migrate, because it "carried a second ack store".**

```
CMD grep -nE "create table|alter table|add column" sql/2026-10-14-hank-b9-ai-safeguards.sql
    54:      'alter table public.%I
    55:         add column if not exists ai_notice_version text,
    56:         add column if not exists ai_notice_acked_at timestamptz',
```

**There is no second store. No new table.** The ack lives on
`*_employee_auth` — exactly where §2.1 and §7.5 say it must. **Acting on my own
ruling would have deleted working code that implements it.**

**RE-RULED in the review document: the store is agreed and hank's single
endpoint STANDS.** One endpoint beats the same action copied into 17
`*-auth.js` files, which is the argument my own §3.1 makes.

**Exact next step: NOBODY DELETES `api/ai-notice.js`.** If a later session
reads §7.5 without the review beside it, that is the risk — **so §7.5 itself
should carry the correction inline, and it does not yet. That is my open item,
not hank's.**

### 3.2 cody — T16, and why T12 does not cover it

**T12 asserts the PROXY response carries `ai: true` and a non-empty
`ai_label`. Nothing asserts a surface RENDERS it.** A user with yesterday's
cached HTML and today's proxy sees **no label**, and every T12 arm passes.

**Four arms, written out in
`docs/2026-10-14-fourth-b17-hank-b9-tier-a-review.md` §6.** **ARM 2 is the
load-bearing one and the one a reviewer would cut:** a *different* label must
appear verbatim, which catches a page that hardcodes the current wording —
**and the wording is `[DRAFT — LAWYER]` and will change.**

**Also hank, two conditions from the review:** a comment on
`SEN_SETTING_PUBLIC_FIELDS` saying *add here when a new setting must be visible
to caregivers*; and `ai_source` becomes **required per surface** the moment any
client writes one of the five `HIGH_RISK_AI` resources.

### 3.3 MICHAEL — the one decision in this batch

`docs/2026-10-14-fourth-b17-sen-rf-write-map.md`. **Seven resources, two
options, and switching between them is one constant.**

* **Option A — coordinators allowed** on the five operational records
  (`sen_referrals`, `sen_referral_sources`, `sen_applicants`,
  `sen_training_records`, and `rf_certifications`), with the two **RULE**
  resources (`sen_training_rules`, `rf_cert_rules`) still management-only.
* **Option B — management-only everywhere.** This is what `a6fa37a3` landed and
  what is running now.

**The failure direction of leaving B in place is "a coordinator has to ask a
manager", not data loss — so there is no urgency and no risk in deciding
slowly.** **Option A has one precondition:** `updated_by` from the verified
session on all five, or A is not ready.

**The fact that would settle it without anybody's opinion:** whether
coordinators are currently asking managers to log referrals. **Nobody has
measured that.**

### 3.4 hank and cody — four removal paths

`docs/2026-10-14-fourth-b17-removal-path-specs.md`, in order:

1. **`sv_scribe_consent`** — a consent nobody can withdraw. Withdrawal recorded
   with a **required reason**, `owner`/`dvm` only, **plus an `sv_audit_log` row
   whose `event_type` must be added to the CHECK list in the same migration.**
   **Arm S6 is the one to insist on:** with the value absent from the CHECK
   list, the withdrawal must fail **loudly** and the consent must **not** be
   marked withdrawn.
2. **`alf_family_contacts`** — arm A3 proves the kept row still resolves in a
   notification lookup, which is the whole argument for soft over hard.
3. **`sf_trustee_audits`** — owner-only, never destroyed; **arm F4 must pass
   for ever.**
4. **`mech_insurance_policies`** — the ordinary one.

**And the finding is NOT closed by four baseline rows.** A consent, a named
person's contact details, a statutory attestation and an insurance certificate
are not records you grandfather.

### 3.5 cc — the register, where the premise did not reproduce

```
CMD python tools/defect_register.py --check                  ->  EXIT 0
    SUPERSEDED (4) … OK: 553 record(s) … 4 by subject
```

**I was told: 6 duplicate summaries, 4 without `superseded_by`. The 4 are the
records WITH it, and the validator reports no duplicate at all.** So I did
**not** run `--supersede`: the register is cc's, and retiring live records to
match a number would shrink a denominator other figures divide by.

**What is really there is ONE live duplicate**, on commit `7bc26782e533` —
identical app, layer, severity, method, phase, files and line counts, differing
in two fields **by a mojibake**: one record carries `U+2713`, the other carries
its three-byte cp1252 misreading.

**Three ordered asks, all cc's:** retire the corrupted twin (**and
`--supersede` cannot express it — `superseded_by` names a survivor SHA and both
records carry the same commit**); make the dedup test encoding-blind; find
where the mojibake entered, because `--add` is the only writer and **1 of 553
is only what an exact-twin test can see.**

**Same encoding fault class as `tools/batch_manifest.py:386`** — except that
one crashes and this one corrupts data.

### 3.6 Still open from earlier batches

* **cc:** `tools/fixture_lock_check.py` (b13, built by nobody); the by-design
  validator (b12) and **four rulings still at `DECIDE_OR_NOT_PROMOTED`**; a
  lock reaper with a stated threshold; the `rm`-deny decision;
  `--read-the-line` on `citation_line_drift_check.py` **plus the two additions
  from this batch** (an expected-absent declaration, and a subject-exists test
  before any renumber).
* **cody:** the two SAIRNcash entitlement arms (b16, **ARM B first**); fixture
  rows 26–50 with row 39 first; b14's T7/T8/T9/T10/T14.
* **hank:** the three role matrices, **SAIRNlegacy first** (zero gates, widest
  exposure, and its `staff` migration must go to the narrowest band).
* **counsel:** three questions. **A funeral director:** five. **A vet
  practice:** two.
* **fourth (me):** the 417h Tier A obligation (§2); inlining the §7.5
  correction (§3.1); fixture row 11, whose code is cc's.

---

## 4. THE THING THE NEXT SESSION MUST DO FIRST

**Write the manifest, then read §2's overdue obligation before anything else.**
**And when a batch hands you a number — "6 duplicates, 4 without
`superseded_by`" — measure it before acting on it.** This batch would have
retired four correct records on an instruction that was one `--check` away from
being disproved.

---

## 5. FINAL STEPS STILL AHEAD OF THIS HANDOFF

1. `PYTHONIOENCODING=utf-8 python tools/drive_upload_verify.py --agent fourth
   --batch b17` — **will report 2 findings**, because the report and digest do
   not exist yet. Expected; the handoff is written first by instruction.
2. The report and digest, then the same upload-and-verify, then a Drive-side
   API read because the mount proves the sync set and not Google's
   acknowledgement.
3. `PYTHONIOENCODING=utf-8 python tools/batch_manifest.py --close --agent
   fourth --batch b17` — **after** all three are up, because closing is
   *defined* as all three verified.
4. Release the b17 claim.

**Nothing is partial.** Every open item above is another session's, or mine and
named as mine, or a measurement with its command stated.
