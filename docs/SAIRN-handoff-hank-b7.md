# Hank handoff — 2026-10-13, batch b7

Written **before** the report, at a point where nothing is half-finished: all
five code/doc items are committed, every suite has been run in an isolated
worktree at HEAD with its exit code read from the program's own output, the
worktree has been removed, and no file is mid-edit.

**Push state is the one thing this file cannot assert.** It is written before
the push. Verify with `git log --oneline origin/main`, not from here.

**Naming note.** The brief asked for `SAIRN-handoff-hank-b7.md`. It is in
`docs/` because that is where every handoff in this repo lives, and because
CLAUDE.md's rule is that a handoff lives only in a real clone — never written to
`C:\Users\marsh\` directly. The filename is the one asked for.

---

## Committed this batch

**THESE SHAS ARE POST-REBASE AND EVERY EARLIER SET IS DEAD.** `origin/main`
moved 65 commits while b7 ran and **moved again between the first push attempt
and the second**, so the batch was rebased TWICE and every sha was rewritten
each time. Two earlier printings of this table cited `1400bd90` / `e064ceee` /
`972eeb9d` / `c3983131` and then `1315205f` / `8fff5bab` / `807c26de` /
`58ba1b31`; none of those resolves in any clone but this one's reflog. **A
dangling citation is what a rebase silently creates in every document that
stamps a sha** — which is exactly the condition that left two `api/` Tier A
obligations unreviewable by anybody, and the reason the b6 methodology proposal
asks `--open` to stamp a sha the assignee can actually fetch.

| sha | item |
|---|---|
| `a13b4466` | the claim |
| `90228883` | **items 1 + 2** — audit-checkpoint sixteen-log coverage as one idempotent SQL block, the `CHECK_NOT_WIDENED` refusal, four new ablated test arms; three stale `sql/*_audit_log_schema.sql` CHECKs synced to what ran; `api/sf-auth.test.js` split into four arms |
| `dde6aaed` | **item 3** — the SAIRNfreedom demo credential, round-tripped twice |
| `bc9b87f3` | **item 4** — the last nine `sf_` resources gated, 36 of 36 |
| `a247322f` | **item 5** — `docs/2026-10-13-context-budget-procedure.md` |
| `8722b141`, `8779b21e` | this handoff, first two printings |
| `ebe6d2ff` | the claim release |
| `f023569f` | the defect-register record the push gate required |

**THE REGISTER RECORD'S SHA WAS RE-SEATED AUTOMATICALLY AND THAT IS WORTH
KNOWING.** The record was written against `1315205f`; the repo's own
post-rebase git hook re-pointed it to `90228883` in the working tree, leaving
the change UNSTAGED — so a session that committed and pushed without looking at
`git status` again would have published a record citing a sha nobody can fetch.
`python tools/defect_register.py --reseat` then reported a COLLISION rather than
a re-seat, because the destination already held the re-seated record; the
message is right and the state was already correct.

Nothing from an earlier batch was carried: `origin/main` was at `f779644e`
(0 ahead / 0 behind) at pickup.

**THE REBASE WAS CLEAN AND THE VERIFICATION WAS RE-RUN AFTER IT, not before.**
All eight suites and five `tools/*.py` checks were driven again at the rebased
HEAD — identical results to the table below, 65 other-session commits
notwithstanding — and the second worktree was clean after and removed. A pass
measured before a rebase is a pass against a tree that no longer exists.

---

## Claims

**`sairnfreedom`, taken at `52be9eb3`.** Released at the end of the batch; the
release commit is in the push, so confirm it landed with
`python tools/sairn_claim.py list` rather than from this line.

Declared a FILES list per PR §4.3 and **declared the conflict rather than
overriding it**: all of `tools/`, `.claude/settings.json`,
`docs/SAIRN-OPEN-WORK-INDEX.md` and `docs/tier-a-reviews.json` are in **cc's
LIVE b6 claim** and none was taken. That is why item 4's open-work row is routed
below instead of applied.

**Two files were edited that are NOT in my declared FILES list**, and that is
stated rather than left for someone to notice:

* `docs/known-red-suites.json` — the row for `api/sf-auth.test.js`, whose tail
  and arm name my own change moved. Leaving it would have made the register
  describe a suite that no longer exists. No active claim names this file.
* `api/sd-data-session-gate.test.js`, `api/sd-data-sf-session-gate.test.js`,
  `api/sf-session-gate.test.js` — the three suites that hold the gate table I
  changed. A gate edit that does not move its own tripwires is an edit that
  turns its tests red for someone else to find.

---

## Hooks — the thing a fresh session will get wrong

`.claude/settings.json` carries **`hooks: {}`**, per Michael. **Never restore
them. Never commit this file — cc owns its merges.** It shows as
`M .claude/settings.json` and must stay unstaged. Both `.bak` files untouched.
It stayed modified and uncommitted for the whole of b7.

**No `git rebase` was needed this batch** (0 behind at pickup and at push), so
the park-and-restore dance was not run. If you do need it:

```
cp .claude/settings.json "$SCRATCH/hooks-empty.json"
git checkout -q -- .claude/settings.json
git fetch origin main -q && git rebase origin/main
cp "$SCRATCH/hooks-empty.json" .claude/settings.json
```

**A PLAIN `git checkout -- .claude/settings.json` RE-ARMS ALL 23 HOOKS
SILENTLY**, and nothing announces it. That happened in b5.

**Note for the record: git-level hooks DID run on commit** — `install_git_hooks.py`'s
`core.hooksPath` hooks printed staged-credential and doc-sha-reseat output. Those
are not the 23 cleared Claude Code hooks and were not re-armed by me.

---

## Verification — what was run, where, and what it said

Every suite was run **in an isolated git worktree at HEAD**, one process each,
because several `tools/*.py` write when run. **The worktree was `git
status --porcelain` clean after all of it, and was then removed.** Exit codes
are the programs' own.

| suite | exit | tail |
|---|---|---|
| `api/audit-checkpoint.test.js` | **0** | 50 passed, 0 failed (was 46 at origin/main) |
| `api/sf-auth.test.js` | **1** | **39 passed, 1 failed** (was 37 passed, 1 failed) |
| `api/sd-data-session-gate.test.js` | **0** | ALL 22 SESSION-GATE ASSERTIONS PASS |
| `api/sd-data-sf-session-gate.test.js` | **0** | 6 assertions passed |
| `api/sf-session-gate.test.js` | **0** | 88 passed, 0 failed |
| `api/sd-data-cross-tenant-dispatchers.test.js` | **0** | 419 passed, 0 failed |
| `api/sd-data-sf-role-matrix.test.js` | **0** | policy only; drives no session |
| `api/hydrate-gate-coupling.test.js` | **0** | 4 passed, 0 failed |

| tool | exit |
|---|---|
| `tools/audit_event_type_check.py` | **0** — was **1** at origin/main (item 2b) |
| `tools/employee_auth_guard_check.py` | **0** — 30 writers, 11 guarded, 0 unguarded |
| `tools/criticality_tier_check.py` | **0** |
| `tools/md_table_check.py` | **0** |
| `tools/truthy_sum_check.py` | **0** |
| `tools/idempotency_check.py` | **1 — PRE-EXISTING, measured not assumed** |
| `tools/fabricated_kpi_check.py`, `tools/silent_failure_check.py` | **NOT PRESENT** — named in the b7 check plan, absent from `tools/`. Not substituted. |

**On that exit 1:** `idempotency_check.py` is report-only and exits 1 on a
standing population of 27 unguarded files. It lists `api/audit-checkpoint.js`
as `UNGUARDED (1 write)`. **b7 did not introduce it** — the same line appears in
a run against `origin/main`, which is why this is a measurement and not a
reassurance. That write is in fact protected durably by the table's
`unique (audit_table, window_end)` constraint, which the tool's own disclosed
limit covers: *"a real guard may be guarded under a name this list lacks."* Not
fixed, not swept, and not mine to re-triage.

**Check 0a (syntax): `node --check` clean on all eight changed `.js` files; no
`.html` was touched this batch.** Checks 0b and 0d are about rendered panels and
KPI elements and have no subject here for the same reason. `docs/known-red-suites.json`
re-parsed with `json.load` after editing.

**Ablation, per the twelfth cross-domain convention — one named layer removed on
already-clean code, four times:**

| ablation | arm that failed | arm that did NOT |
|---|---|---|
| `isNarrowCheck` branch disabled | `AN UNWIDENED DATABASE IS REFUSED BY NAME` | — |
| the ALTER half removed from `sql/audit_checkpoint_schema.sql` | `THE SCHEMA FILE WIDENS A TABLE THAT ALREADY EXISTS` | — |
| gate table lookup → `sf_` prefix test | `the gate is a SINGLE check both verbs pass through` (in `sd-data-sf-session-gate`) | `sf-session-gate`'s table-driven control — **and that is recorded in the arm** |
| gate made to refuse everything | `THE GATE IS TABLE-DRIVEN, NOT BLANKET` | — |

The third row is the useful one: it is how the first rewrite of that control was
caught being vacuous, and both halves are now written into the arm so the next
reader does not re-derive which arm covers which failure.

---

## OPEN — exact next step per item

### 1. MICHAEL: four SQL runs. All four are printed in full in the report.

**1a — `sql/audit_checkpoint_schema.sql`. ONE PASTE, IDEMPOTENT, RUN IT WHOLE.**
It now handles both states a clone cannot tell apart: table absent (`create
table if not exists` builds it with all sixteen names) and table present with
the old three-name CHECK (a `drop constraint if exists` / `add constraint` pair
widens it). **Both halves are required** — `create table if not exists` skips an
existing table constraint and all, so re-running the OLD file to "fix the
coverage" would have reported success and changed nothing.

After it runs, verify with queries **1b and 1c** at the foot of that file: 1b
must answer **16**, and 1c must name the sixteen with **no `sv_audit_log`**. A
count of 16 over the wrong names passes 1b alone, which is why 1c exists.

**Nothing in the code is waiting on it.** `SCHEMA_PERMITTED` is already
`ALL_AUDIT_TABLES`, so the job asks for sixteen today. If the ALTER has not run,
the INSERT comes back 23514 and the endpoint answers **503 CHECK_NOT_WIDENED**
naming the file, with a heartbeat carrying `retry_helps: false`. It will not
silently cover three of sixteen again.

**1b — `sql/sairnfreedom_demo_owner_credential_2026-10-13.sql`.** One
transaction, with the recoverability guard, and a second guard clause beyond the
house pattern: it refuses if the row does not carry the PIN salt the file wrote,
so a pre-existing `sairn-demo-owner` whose `on conflict` update did not apply
cannot leave the documented PIN wrong and the guard green. **PIN `64927108`,
employee `sairn-demo-owner`, role `post.govern`** (SAIRNfreedom has no `owner`
role at all).

**Run `sql/sairnfreedom_license_seed.sql` first if it has not been run** —
query 2 in the credential file distinguishes that case, which otherwise presents
as a bad PIN.

**1c — STILL OPEN FROM b6 AND NOT SUPERSEDED: confirm whether the checkpoint
table ever existed.** `docs/AUDIT-CHECKPOINT-STATUS.md` has read **COULD NOT
TELL** since 2026-09-14 and still does; it is a GENERATED file and was
deliberately not hand-edited. It cannot be regenerated from this clone —
`CRON_SECRET` is not set here, so `tools/audit_checkpoint_status.py` would
rewrite it with the same COULD NOT TELL and a newer timestamp, which is worse
than leaving it.

### 2. MICHAEL: the trustee sign-in question. THE SINGLE REMAINING RED, by design.

`api/sf-auth.test.js` is **39 passed, 1 failed**. The one red arm is
`ROLES_BY_APP and sairnfreedom.html CAPABILITIES agree`, and the only
disagreement is `trustee.audit`.

**Untouched exactly as instructed:** the `ROLES_BY_APP.sairnfreedom` entry, and
also the `role in (...)` CHECK in `sql/sairnfreedom_employee_auth_schema.sql` —
**both lack `trustee.audit`, which is ONE pending decision and not two.** The
`sf_trustee_audits` row in `api/_lib/sf-roles.js` is likewise untouched.

**THE QUESTION:** should a trustee be able to sign in? `sairnfreedom.html:2314`
declares `trustee.audit` in `CAPABILITIES` (added 2026-09-27, citing the VFW
Manual of Procedure: trustees audit quarterly, are individually liable, the
Quartermaster must not prepare the audit, a missed audit can void the bond), and
`api/sf-auth.js` refuses to provision an unknown role — so a post can assign the
Trustee office and then cannot give that trustee a sign-in.

* **If yes** — three places change together: `ROLES_BY_APP.sairnfreedom`, the
  `sf_trustee_audits` row in `api/_lib/sf-roles.js` (an eleventh column granting
  `rw`), and the employee-auth CHECK.
* **If no** — the capability is display-only and `sairnfreedom.html` should say
  so, because today it looks like an assignable office.

**What b7 DID fix in that arm, and this is the part worth reading:** it was ONE
arm with three sequential asserts, so the trustee failure **masked** the other
two. The `ROLES_BY_APP`-vs-schema-CHECK comparison — the pair that breaks at
RUNTIME, as a 400 nobody can read, at the moment a post tries to give somebody a
sign-in — **had not run since 2026-09-27**. It passes. And a second red cause
was hidden in the same arm: a transcribed `caps.size === 10`, stale since the
day `trustee.audit` was added, whose next correct value would go stale again on
whichever day this decision lands. Replaced with a non-vacuity arm asserting a
floor and a named anchor in each of the three lists.

### 3. cc: `docs/SAIRN-OPEN-WORK-INDEX.md` **row 221**. Routed, not applied.

That file is in cc's live claim FILES, so per PR §4.3 it was not taken. **Do not
open the file to find the row** — it is 2.38 MB; use `awk 'NR==221'`.

The row is stale in both halves. It reads *"The ones still ungated are still a
decision NOBODY HAS MADE"* and its owner cell reads *"24 ungated resources:
**unassigned**"*. **There are now zero ungated `sf_` resources.** Replacement
text for those two cells is printed in the report. **Never edit the row by
splitting on `|`** — rebuild it whole, or replace a unique substring inside one
cell and check the pipe count on that line is identical before and after
(PR §2.1).

### 4. Nobody yet — the client half of the role matrix. NOT a defect I introduced.

`sairnfreedom.html` does **no per-panel role gating** (only the Access tab is
hidden), and a backup refused by the matrix **warns to the console and nothing
else**. So a role the matrix denies still saves locally while its server copy
silently does not.

**This is pre-existing and was already true for the 27 gated resources.** b7
made it reachable for nine more, and the numbers are measured off `decide()`
rather than described: **every one of the nine now denies at least five of the
ten roles on write, and five of them deny on read as well.** A chaplain is
refused a write to the vendor list; a member-admissions officer is refused the
bottle counts.

Refusing is the server's job and hiding is the page's. **The page half is a
client change nobody has been asked for**, and it is the same shape b6 recorded
for the `bld_draws` Draw Requests panel — so this is a second instance, not a
new finding.

### 5. cody — still open from b6, unchanged by b7

The **driven** SAIRNfreedom role matrix: 10 roles × 36 resources × 2 verbs with
real signed sessions. `api/sd-data-sf-role-matrix.test.js` proves the policy is
complete, locked, mirrored and wired and **drives no session**, and says so in
its own closing lines. **Derive the EXPECTATION from `SF_ROLE_MATRIX` and the
OBSERVATION from the handler, never both from the table.**

**b7 removed the blocker that made the driven half impossible for anybody**:
`SF-PINNACLE-2026` now has a demo credential in the repo. It is UNVERIFIED until
Michael runs the SQL (open item 1b).

### 6. Not touched, by instruction or by claim

`tools/`, `.claude/settings.json`, `docs/SAIRN-OPEN-WORK-INDEX.md`,
`docs/tier-a-reviews.json`, `docs/CRITICALITY-TIERS.md` (no tier moved),
`sairnfreedom.html` (the client half above), and the three open `api/` Tier A
obligations — hank authored all three and the gate refuses a self-review, so
they remain cc's, exactly as routed in b6.

---

## Live state

**Not driven this batch, and that is the honest state rather than a caveat.** No
HTTP call was made to the deployed app in b7: every change is in `api/`, `sql/`
and `docs/`, the one credential that would make SAIRNfreedom drivable is in a
SQL file that has not been run, and inventing a live-verification claim from a
source read is the exact failure this platform keeps recording.

**What b6 established and b7 did not re-drive:** the site answered 200, and
SAIRNscape's gates were proven live in both directions with
`SCP-DEMO-2026` / `sairn-demo-owner` — six gated resources 200 with a session
and 403 bare, two ungated controls 200 both ways, and an id-less write WITH the
session answering 400 from the handler. Re-drive it; do not trust this
paragraph.

**`/api/audit-checkpoint` answered 401 to an unauthenticated GET as of b6**, so
the route exists and is deployed. Whether the daily job has beaten still cannot
be told from this clone — no `CRON_SECRET`, so `tools/cron_liveness_check.py`
exits 3 without calling the watchdog.

---

## Transcript

`C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-hank\7ec24d5b-8a65-4021-a50f-4294e97bb0ed\`

Scratchpad under `scratchpad/` in the same directory, holding every suite log
(`b7_*.log`, `wt_*.log`) and the four ablation logs. **It is `%TEMP%` and is
cleared without warning**, so the one artefact the report cites by path was
copied into the repo: `docs/hank-evidence/b7_sf_demo_credential_roundtrip.js`
and `.out`. The `wt-b7` worktree created for verification has been removed; the
other worktrees in `git worktree list` belong to other sessions and were not
touched.
