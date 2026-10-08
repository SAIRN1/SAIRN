# Hank handoff — 2026-10-07, batch 18 (b2)

**Per-item checkpoint.** A row is appended below after EACH item, before the
next begins. Nothing here is a plan; every row is state at the moment it was
written.

Previous handoff: `docs/handoff-hank-2026-10-07c.md` (batch b1, pushed
`afe526b2`).

---

## PER-ITEM LOG

### item 1 — RESUME CHECK — DONE

- `origin/main` fetched and rebased onto: **HEAD `4fa9843a`, ahead 0, behind 0,
  tree clean.**
- **My batch-b1 claim had EXPIRED** — `sairn_claim.py list` showed only cc,
  hover2 and cody. Re-claimed `platform` for batch 18; the claim is pushed and
  verified on `origin/main`, and the matcher reports the three lexical matches
  as NON-blocking on disjoint FILES.
- **Batch b1 is fully landed and nothing from it is redone.** Confirmed with
  `git merge-base --is-ancestor` against `origin/main`, not from the handoff:

  | sha | ancestor of origin/main |
  |---|---|
  | `72d757ef` audit-event-type checker | *verified in item 12* |
  | `320ddabe` six argv tools | *verified in item 12* |
  | `4ec0d5d5` attribution, 0 of 49 | *verified in item 12* |
  | `1ae447cf` seventh argv tool | *verified in item 12* |
  | `947dfda0` retraction | *verified in item 12* |
  | `661ff87c` RULE E routed | *verified in item 12* |
  | `bf174f30` derived artefacts | *verified in item 12* |
  | `afe526b2` handoff b1 | *verified in item 12* |

- **The clean-worktree suite run is STILL ALIVE** — `python -u
  tools/run_all_tests.py`, PID **31292**, started 15:17, in
  `<scratchpad>/wt-suite2`. **440 ok / 0 FAIL at this moment and still
  running.** No second run started. Item 3 is held open until it exits.
  (A separate `run_all_tests.py --pinned` belonging to **cody** is also running;
  it is not mine and is not touched.)
- **Two claims known-blocked before they are re-checked**, from cc's live claim
  text: `docs/tier-a-reviews.json` is in **cc's** FILES (cc is discharging), and
  `docs/METHODOLOGY.md` is declared by **fourth** under a live claim. Both are
  re-derived from the tool in items 7 and 11 rather than taken from that text.
- Six stashes exist; `stash@{0}`, `{2}`, `{4}`, `{5}` are the
  **`docs/scrutiny-flags.json`** parks (cc's file). Item 13 leaves them.

### item 3 — THE CLEAN-WORKTREE SUITE — DONE. It exited; nothing was re-started while it was alive.

`python -u tools/run_all_tests.py` in `<scratchpad>/wt-suite2`, PID 31292.
**Captured exit code: `EXIT 1`** (the `SUITE_EXIT=1` line appended to the file).

```
RAN: 351 JS + 406 PY = 757 files
  ok          651
  FAIL        101
  SKIPPED       5     a precondition was not met, NOT a pass
  NOT RUN       2     known .sql fixtures
```

**AND IT DIRTIED ITS OWN TREE, in a worktree that started clean** — the suite's
own footer names 5 paths (`docs/MASTER-PLAN.md`, `docs/TOOLING-INVENTORY.md`,
`docs/report-only-reachability.json`, `docs/scrutiny-flags.json`,
`docs/traceability-matrix.md`) and says *"Results above may be CASCADE, not
real."* **The suite is self-dirtying**: the generators it runs regenerate
documents, and every clean-tree probe after that point fails for a reason that
is not its own. "Run it in a clean worktree" does not fix that; only running
each file alone does.

**EACH OF THE 101 RE-RUN ALONE, on a tree restored with `reset --hard` plus
`clean -fd` before every single file, 240 s bound, in a dedicated worktree:**

| verdict | count | meaning |
|---|---|---|
| **REAL** | **89** | non-zero alone, on a restored tree |
| **CASCADE** | **8** | exit 0 alone — failed in the suite only because something earlier dirtied the tree |
| **TIMEOUT** | **4** | exceeded 240 s alone. A third state, folded into neither |
| ERROR | 0 | |

**The 8 CASCADE, with what the suite said and what the file says alone:**

| file | suite said | alone |
|---|---|---|
| `tests/phi_cache_scoped_to_user.js` | 63 passed, 1 failed | **72 passed, 0 failed** |
| `tests/phi_cache_scope_probe.py` | "baseline is red, so no mutation below would mean anything" | **ALL 12 ARMS PASS** (7 mutations) |
| `tests/run_master_plan_probe.py` | "it passes on the committed document (got 1)" | ok |
| `tests/run_push_gate_preflight_probe.py` | 12 passed, 1 failed | **13 passed, 0 failed** |
| `tests/sairnbuild_fault_probe.py` | red | **0 failure(s)** |
| `tests/sairncare_fault_probe.py` | red | **0 failure(s)** |
| `tests/push_gate/redaction_base_probe.py` | 2 failure(s) | **0 failure(s)** |
| `tests/push_gate/refspec_and_override_probe.py` | red | **0 failure(s)** |

`tests/phi_cache_scoped_to_user.js` is the one to notice: **fourth's batch-16
item 4 took it as "basis NONE, no owner, blocks three register rows".** Alone,
on a restored tree, it is **72/0 green**. Its suite failure is cascade.

**The 4 TIMEOUT at 240 s alone:** `run_defect_register_probe.py`,
`run_hover_audit_method_sabotage_probe.py`, `stale_row_sweep_control.py`,
`push_gate/check12_probe.py`. Not classified either way — they need a larger
bound measured on an unloaded machine, which is item 4's discipline.

Full per-file table with the first failing line of each:
`<scratchpad>/i3.table.txt`, raw in `i3.rerun.json`.

### item 6 — THE COULD-NOT-RUN TOOLS — DONE, and the population is 62, not 67

**THE DISPATCH'S 67 AND THE SWEEP'S 62 ARE DIFFERENT MEASUREMENTS.**
`tools_sweep.tsv` at HEAD `7406ab27` is 153 / 83 / **62** / 2 / 15 = 315. The
**67** in my own b1 handoff counted tools that **refuse in words** on a bare
run — counted while fixing the argv tracebacks. A tool can refuse in words and
still exit 0 or 1, so the two were never the same number. 62 is the exit-2 set
and is what this item worked on. **All 62 are accounted for; none is dropped.**

**A. Re-run bare at this HEAD — 55 still exit 2, 7 have moved:**
`eaten_substitution_check.py` to 0, `sairn_session_identity.py` to 0,
`tier_a_review_gate.py` to 0, `sairn_self_state.py` to 1, `run_tlc.py` to
timeout, and **`restore_coherence_check.js` / `row_count_baseline.js` to 1,
which is a HARNESS ARTEFACT**: the 315-script sweep ran *every* file with
**python**, so those two reported a Python `SyntaxError: invalid decimal
literal` on JavaScript. Driven with `node` they exit **2** with a real
credential refusal.

**B. 34 driven with a COMPLETE command line** — green (0) **16**, findings (1)
**6**, still exit 2 **10**, plus `wait_for.py` exit **3** and
`bare_run_write_check.py` still in flight. Every command line is written out in
`<scratchpad>/b2_item6_pass2.py` and points at real artefacts in this repo.

**C. 15 NOT COMPLETABLE** — the refusal names a **credential or secret**
(`ALF_LICENSE`, `CRON_SECRET`, `RF_EMP` + `RF_PIN`, a JRE plus
`tla2tools.jar`, and so on). **No credential was manufactured.** These tools
are RIGHT to refuse and their exit 2 is the documented third state, not a
defect.

**D. 12 where exit 2 is about the REPO, not the command line** — the tool ran,
read the repo and failed CLOSED: `secrets_inventory.py` (two secrets with no
`SECRETS` entry), `service_role_tier_a_gate_check.py` (UNGATED Tier A writers),
`cleanup_residue_check.py` (COULD NOT READ 27 of 27), `hover_eqa_escalation.py`
(hover2 carries no `eqa_checkpoint` field at all), and eight more. More
arguments cannot change these; the repo has to.

**ONE FINDING WORTH MORE THAN THE TALLY — `known_red_check.py --from-run`
against this very suite run:** *101 red, 651 green; the registry records 75.*
**30 suites are RED AND NOT RECORDED** in `docs/known-red-suites.json`. That
register is **fourth's**; routed, not touched.

Table: `<scratchpad>/i6.table.txt`. Refusal texts: `i6.refusals.txt`.

### item 6a — A LIVE CLONE WAS CORRUPTED DURING THIS ITEM, AND THE WRITER IS NAMED

**`core.bare = true` appeared in `C:\Users\marsh\Documents\SAIRN-hank\.git\config`
during item 6.** `git status` was clean immediately before; immediately after,
every git command answered *"fatal: this operation must be run in a work tree"*.
Restored to `false` by hand; the corrupt config is kept at
`<scratchpad>/gitconfig.bare-true.bak`.

**IT IS NOT ONE OF THE 62, AND THAT IS MEASURED, NOT ASSUMED.** Two negative
controls, each changing exactly one thing:

| control | result |
|---|---|
| all 62 in order, **throwaway clone, no worktree** | `core.bare` stayed `false` throughout |
| all 62 in order, **same clone with a LINKED WORKTREE registered** | `core.bare` stayed `false` throughout |

**THE WRITER IS THE PUSH-GATE PROBE SUITE, RUNNING INSIDE A LINKED WORKTREE —
and the repo already documents the mechanism and already fixed one instance.**
`tests/push_gate/check8_probe.py:203` names the class as cody's
`SHARED_CONFIG_WRITE_FROM_WORKTREE`:

> *"A linked worktree SHARES `.git/config` with the clone that owns it. So a
> `git config` write made by anything running with cwd inside the worktree …
> lands in the REAL clone's config, and this probe's first dry-run push was
> reliably leaving `core.bare = true` behind."*

check8 was moved to a **throwaway clone** on 2026-10-06 for exactly this.
**`tests/push_gate/check4_probe.py` and `tests/push_gate/check7_probe.py` were
NOT** — both still `git worktree add` (check4 line 93) and then
`git push --dry-run origin HEAD:main` (check4 lines 171-172), and check4's own
header says *"worktrees share the common git dir, so `git push --dry-run` from
the worktree runs the real gate."* My suite was running in `wt-suite2`, a
linked worktree, for the whole window.

Both probes **SKIPPED** in that run — *"SKIPPED: a CLEAN push is already being
refused"* — **after** the dry-run push that discovers the refusal. The skip is
printed; the write already happened.

**This closes cody's "The WRITER of core.bare is still unidentified."**
`docs/tool-owner-map.json` gives `tests/push_gate/check4_probe.py` as
`"basis": "NONE", "owner": null`. Routed with the fix already proven in-repo:
**replace `git worktree add` with `git clone --local --no-hardlinks`**, exactly
as check8 did.

**AND A METHOD CHANGE MADE IMMEDIATELY:** every write-when-run sweep in this
batch after this point runs in a **CLONE**, never a linked worktree. A worktree
is isolation for the *files* and no isolation at all for `.git/config`.

### item 6b — TWO TOOLS DESTROY A GOOD RECORD WHEN THEIR SECRET IS ABSENT

A bare run of `tools/cron_liveness_check.py` **overwrote**
`docs/CRON-LIVENESS-STATUS.md`, replacing a real **OK** (4 jobs, measured
09:18:44Z) with **COULD NOT TELL**, because `CRON_SECRET` is not set in my
environment. `tools/audit_checkpoint_status.py` does the same to
`docs/AUDIT-CHECKPOINT-STATUS.md`. Both exit **2** — correctly — **after**
writing.

It is deliberate: *"says so rather than keeping a stale OK."* The design is
defensible and the **consequence** is not: any session without the secret
silently destroys the last good record produced by a session that had it, and
nothing records that an OK ever existed. Both files **restored**; the diffs are
at `<scratchpad>/i6.damage.cron.diff` and `i6.damage.audit.diff`.

Routed, not fixed — whether a could-not-tell should overwrite a dated OK is a
judgement about those documents, not a mechanical repair.

### item 8 — sv_audit_log — **THE ONE-LINE CHANGE WAS NOT MADE, AND THE REASON IS THE FINDING**

**Chat decided to add `sv_audit_log` to `AUDIT_TABLES`. That decision rests on a
false premise, and the premise is MINE — STEP 0d of my own migration document
called it "one line of JavaScript".**

Confirmed first, as the item asked: **no writer exists.** 28 `writeAuditLog`
call sites; the only `AUDIT_TABLE` constants are `sairncode_audit_log`
(`sc-ai.js:61`, `sc-auth.js:46`), `stonedesk_audit_log` (`sd-auth.js:47`,
`sd-sub-data.js:45`, `stonedesk-track.js:50`) and the `sairnlaw_audit_log`
default (`_lib/audit.js:41`). Nothing targets `sv_audit_log`.

**AND IN CONFIRMING THAT, THE DEEPER FACT:**

| `writeAuditLog` POSTs (`api/_lib/audit.js:59-64`) | `sv_audit_log` HAS (`sql/sairnvet_data_schema.sql:60-70`) |
|---|---|
| `license_hash` | `license_hash` ✓ |
| `employee_id` · `role` · `event_type` · `detail` | **all four ABSENT** |
| — | `audit_log_id` **`not null`, no default**, which writeAuditLog never sends |

**`sv_audit_log` HAS NO `event_type` COLUMN AT ALL.** Adding it to the allowlist
would send every SAIRNvet audit write to a table that cannot take the row:
PostgREST refuses, `writeAuditLog` is **non-fatal and returns false**, the
caller carries on, and **the row is absent** — visible only in a server log.
That is the exact defect this batch exists to remove, created in one line. And
there is nothing for the five-value CHECK to constrain.

**IT IS NOT AN AUDIT LOG IN THIS MODULE'S SENSE.** It is the SAIRNvet
controlled-substance **DOSING** trail — a per-app data table written through
`api/sd-data.js`'s `SV_RESOURCES` dispatcher (`api/sd-data.js:13100`, keyed
`audit_log_id`), declared as an app resource in `api/_resources/sairnvet.js:67`,
and carrying **`grant select, insert, update`**. The three real audit logs grant
only `select, insert`, and that grant pair *is* their immutability control
because `service_role` bypasses RLS. It is not in the allowlist because it is
not that kind of table, not because a line was forgotten.

**WHAT WAS BUILT INSTEAD — a guard, which is worth more than the edit was.**
`tests/run_audit_event_type_probe.py` gains **H0 / H1 / H2**: a table may be in
`AUDIT_TABLES` only if it has the columns `writeAuditLog` posts.

```
python -u tests/run_audit_event_type_probe.py      EXIT 0   11 passed, 0 failed
  ok   H0  the allowlist is found and parsed at all -- without this, H1 and H2
           would pass on an empty list
  ok   H1  every allowlisted table whose DDL is in sql/ has the four columns
  ok   H2  THE PAIRED NEGATIVE, measured off the real DDL: sv_audit_log really
           does lack all four, so H1 WOULD fail if it were added
```

**MUTATION — the asked-for change made, then shown red, then reverted:**

```
api/_lib/audit.js:40  + sv_audit_log: true
node --check          0
probe                 EXIT 1   10 passed, 1 failed
  FAIL H1  sv_audit_log lacks employee_id, role, event_type, detail
restored              byte-identical by sha256
                      9d56583113ddf404672a039bad73203f303259eacc858a98c0ff2abdc60a9e37
probe after restore   EXIT 0   11 passed, 0 failed
```

So the arm is not decoration: it goes red on exactly the change it exists to
refuse, and green again when it is undone.

**PRINTED, NOT APPLIED — `docs/2026-10-07-hank-migration-sql-for-michael.md`
STEP 13**, with three pre-flight queries. The first is designed to FAIL, and its
failure is the evidence:

```sql
select distinct event_type from public.sv_audit_log order by 1;
-- EXPECTED: ERROR 42703 undefined_column: column "event_type" does not exist
```

plus the `information_schema.columns` query that does run, a row count, and a
`jsonb_object_keys(data)` tally — the nearest thing to an event vocabulary that
exists in that table today.

STEP 13a/13b/13c print what the decision costs if it still stands: four
`add column` statements, a default for `audit_log_id`, and a CHECK in the
`event_type is null or event_type in (...)` form — **the strict form the twelve
new tables use cannot be added to a table with existing rows.** 13c prints the
`revoke update` and explicitly does **not** recommend it: revoking it breaks the
dosing write path, so one table cannot be both.

**STEP 13-ALT is the option I would put in front of chat first:** a new
`sairnvet_audit_log` in exactly the form of the twelve — more SQL, zero
judgement calls, and the dosing trail left alone.

### item 9 — rf_schedule.status_changed_by — PRINTED, NOT APPLIED, AND NO CODE CHANGED

`docs/2026-10-07-hank-migration-sql-for-michael.md` **STEP 14**. Three
`add column if not exists` statements — `status_changed_by text`,
`status_changed_by_role text`, `status_changed_at timestamptz` — **all
nullable**, plus the `information_schema` verification query.

**NULLABLE ON PURPOSE.** Every existing row had its status set before the column
did. `not null` would either reject them or need a backfill naming an employee
who did not do it — **a fabricated actor, which is worse than an honest null.**
NULL means "set before this column existed".

**`created_by` IS UNTOUCHED** and no statement in STEP 14 alters, drops or
backfills it. It is `not null` and means who **created** the day
(`sql/sairnroofing_locations_schema.sql:92`); overwriting it on a status change
would destroy the creation record to record an edit. That is the whole reason
this is a migration rather than a code change.

**`api/sd-data.js` IS NOT TOUCHED and keeps the b1 read-then-merge until Michael
confirms STEP 14 has run.** Writing the column before it exists makes every
`set_status` PATCH fail `42703 undefined_column`; PostgREST returns 400 and the
branch answers 502 `Data store error`. **A status change that silently stops
working is worse than the lost-update window it was meant to close.**

STEP 14 also carries the exact four-step code change for whoever takes it after
the SQL lands — including that **arm D3 of
`tests/sd_data_write_attribution_three_apps.js` must be rewritten in the same
commit.** It currently pins the read-then-merge, which is right until the column
exists and wrong afterwards, and a stale arm that passes is how the next reader
concludes the merge is still needed.

### item 11 — METHODOLOGY — BLOCKED, named, stopped. One re-check, no retry.

```
python tools/sairn_claim.py check methodology "land Rule E into docs/METHODOLOGY.md single write"
exit 1   BLOCKED
  cc      2026-10-07T23:20:05Z   (0.6h)   same file or resource: docs/methodology.md
  fourth  2026-10-07T20:30:06Z   (3.4h)   same file or resource: docs/methodology.md
```

**`docs/METHODOLOGY.md` NOT TOUCHED. Rule E stays unlanded** in
`docs/2026-10-07-hank-routed.md` §3. No second retry. cc's own live claim says
its methodology item is *"paste-ready because the target is held"* — the same
answer reached independently.

**SECOND HALF — is the ordering rule already covered? CHECKED, AND IT IS NOT.**
`docs/SAIRN-PROCESS-RULES.md` covers the **adjacent** case well: a *generated*
document must be *regenerated* after a rebase, never hand-merged, because a
resolved hunk is the generating function evaluated *at no state at all*. It even
carries the `docs/tier-a-reviews.json` incident where a hand-resolved conflict
took the wrong side of one record's status fields.

**Both of those are CONFLICT cases. The ordering rule has no conflict.** A rebase
replays my commits onto new upstream work and hands back new shas with a clean
tree and nothing to resolve. A register record written before that replay is
still valid JSON, passes every shape check, and its `commit` field now resolves
to nothing. There is no hunk, no marker, and no moment where anybody is asked a
question — so §2.1's "rebuild the row whole" cannot fire, because the row was
never touched.

Recorded as **ONE routed entry: RULE F**, `docs/2026-10-07-hank-routed.md` §4,
with the 2026-10-07 incident (three rewrites in one push), the mechanical form
(rebase → derive → commit → push, re-derived every cycle), the
`git restore --source=HEAD` footnote, and where it belongs — **beside the
generated-document rule as its no-conflict sibling**, not as a 26th cross-domain
convention. Those are about how a CHECK can be wrong; this is about the order of
operations in a push.

### item 7 — TIER A — STILL HELD. Holder and timestamp, then stopped.

```
python tools/sairn_claim.py list
  cc   0.6h ago   claimed 2026-10-07T23:20:05Z
       FILES: docs/tier-a-reviews.json  <- FIRST in its list
       its item 1 is "my own most-overdue eligible first" and item 7 is
       "Tier A takeover of the two oldest past-48h obligations"
```

**HOLDER: cc. TIMESTAMP: 2026-10-07T23:20:05Z. NOTHING DISCHARGED. No second
retry this batch.**

`sairn_claim.py check platform "tier a review discharge oldest eligible"`
returned **CLEAR on the task words** — and that is exactly the trap PR §4.3
exists for: the word matcher does not see a FILES declaration. The ledger is
declared first in cc's FILES and cc is actively discharging from it. **Taking
the word-matcher's CLEAR as permission would have put two sessions into the same
ledger.**

READ-ONLY NUMBERS at HEAD, for the next session rather than for action:
**239 records · 216 reviewed · 23 OPEN · 15 ELIGIBLE for hank · oldest 10.92
days (262 h)**, opened `2026-09-27T02:06:03Z`, author cody. Eligible by author:
cody 5, fourth 5, cc 3, hover2 2.

### item 5 — THE SIX exit-1 PROGRAMS — triaged, 1 fixed, 5 routed or classified

Each one's FIRST finding, then real-or-artefact, then fix or route.

**1. `comment_sensitivity_check.py` → REAL TOOL DEFECT, FIXED.**
First finding: *"nav_panel_check.py on sairncode.html — its answer depends on
the target COMMENTS: exit 1 raw vs 0 stripped. It is matching text that
describes code rather than code."*

Read the file rather than trusting the report: `sairncode.html` has **three**
occurrences of `mr-kx-ytd` and **one live element** (`:2388`). The second
(`:2367`) is inside a `<!-- -->` block documenting an input removed on purpose —
*"the year-to-date figure is no longer typed … a coder typing 2400 got a clean
KX not required with nothing behind it."* So `FAIL:DUPLICATE_IDS:['mr-kx-ytd']`
was a **FALSE POSITIVE produced by a comment that explains a past fix.**

**THE SAME DEFECT WAS FOUND AND CLOSED IN `tools/div_balance_check.py` ON
2026-08-07 AND THIS FILE NEVER GOT THE FIX** — its note describes the identical
shape: *"a bug-fix comment that DESCRIBES a past widget-bleed bug in prose got
counted as a real closing tag … a phantom DIFF:-4 with zero real defect behind
it."* A fix proven on one checker is not a fix on the others.

FIXED with div_balance_check's own line-preserving strip, applied once at read
time so every check in the file is comment-blind.

**MEASURED ACROSS ALL 22 APPS, BEFORE AND AFTER — EXACTLY ONE LINE CHANGED:**

```
sairncode.html   STATIC_IDS 609 -> 608   FAIL:DUPLICATE_IDS -> RESULT:PASS
every other app  byte-identical
```

**AND THE TWO REAL DUPLICATES SURVIVE**, which is what makes this a fix and not
a suppression: `sairncare.html` `fc-name` and `sairnfreedom.html`
`ac-name`/`ac-tbody` still FAIL.

**THE DETECTOR CONFIRMS IT:** `comment_sensitivity_check.py` now **EXIT 0**,
*"answers that CHANGE when comments are removed: 0"* (was 1).

Regression arms **5a/5b/5c** in `tests/run_comment_sensitivity_probe.py`, on a
**synthetic fixture, not sairncode.html** — pointing the arm at the real app
would make it pass or fail on whatever somebody edits there next. 5c is the
PAIRED POSITIVE: two *live* ids with the same name must still fail, so the strip
cannot turn the check off. Mutation against the pre-fix tool: **5a and 5b go
red**; restored byte-identical by sha256
(`80288f73b9fdc0115a94789cb56068deddeaa521a520038baf42ad20d2385784`).

**2. `cross_tenant_isolation_scope.py` → REAL, ROUTED (test-coverage, product).**
First finding: *"3 file(s) whose declaration and grade disagree —
`api/sd-data-exec-context-isolation.test.js` DECLARES coverage but grades NONE
[exec_context]"*. A test declaring cross-tenant coverage it does not provide.
Also `275 Tier A · 240 GENUINE · 10 WEAK · 25 NONE · 1 serving code UNLOCATED`.
The tool DISCLOSES all three rather than absorbing them, and exit 1 is its
report-only convention. Routed: these are other sessions' test files.

**3. `assurance_case.py` → the first NOT-SUPPORTED leaf is a THIRD STATE
rendered as a negative, which is correct and worth reading twice.**
`G3 NOT SUPPORTED — a change touching a Tier A resource RAISES A REVIEW
OBLIGATION`, evidence `E2 DOES NOT SUPPORT: no undischarged Tier A obligation
(exit 2) — the gate fails closed: a register it cannot parse is COULD NOT TELL,
never an empty set`. **NOT SUPPORTED is not refuted**, and the argument is right
to refuse to count a could-not-tell as support. Report-only; no defect in SAIRN
code. Not routed and not fixed.

**4. `first_article_inspection.py` → REAL COVERAGE OWED, not a defect.**
First finding: `NO SUITE AT ALL — tools/accepted_risk_trigger_check.py, 9
claim(s) in its own header`, and 13 more. Zero arms verify zero claims. A
standing coverage debt across 14+ tools; routed as owed rather than fixed.

**5. `landing_verification.py` → ENTIRELY INSIDE THE HOVER AUDITOR NAMESPACE.
NOT TOUCHED.** First finding: 18 files under
`.claude/skills/sairn-hover-auditor/tools-hover2/` absent from the user skill
store. `CLAUDE.md` forbids a build agent reaching into that namespace. **And the
tool's criteria are asymmetric**, which is worth one line to whoever owns it: it
counts *"28 in the store only"* as explicitly NOT a finding (third-party skills
the repo does not mirror) while counting repo-only auditor tools AS a finding —
and the auditor deliberately keeps its tools in the repo. Routed to chat.

**6. `report_only_checks.py` → TOOL ARTEFACT at the level of this question.**
It is an aggregator over 70+ report-only checkers; exit 1 means at least one
child had a finding, which is its documented convention and not a defect. Its
first child finding (`hover_routing_gap_check.py`) is in the auditor namespace
and is not mine. The real content belongs to each child's owner.

### item 10 — OWNERLESS TOOLS — 175 driven bare AND with one argument, 15 flagged, 2 fixed

**POPULATION, from `docs/tool-owner-map.json` (READ ONLY — it is in cc's live
FILES):** 980 entries, **680** with `"owner": null, "basis": "NONE"` — and
`owner is null` and `basis == NONE` are the *same* 680, with no entry in one set
and not the other. By prefix: **tests/ 502 · tools/ 175 · scripts/ 3**. The
**175 under `tools/`** are the population driven here; the rest are counted and
named as out of scope rather than silently dropped.

**350 runs — bare and one-argument (`CLAUDE.md`, a real file) — 25 s bound, in a
CLONE not a linked worktree** (item 6a is why). **15 flagged:**

| flag | count | verdict |
|---|---|---|
| TRACEBACK | 2 | `hover_separation_ci.py` (known, chat holds it) and **`vercel_config_check.py` — NEW, FIXED** |
| SILENT exit 0 | 13 | **12 are correct**; **1 was hiding an action — FIXED** |

**MY OWN CRITERION OVER-FLAGS, AND THAT IS REPORTED RATHER THAN QUIETLY
DROPPED.** "exit 0 with no output" cannot tell a measurement tool from a module
or a hook. Of the 13: **6 have no `__main__` at all** (`audit_licence.py`,
`checker_kit.py`, `closing_error.py`, `sairn_http.py`,
`testability_criteria.py`, `invariant_registry.js`) — importable libraries, so a
direct run correctly does nothing; **6 are hooks or no-argument programs**
(`conflict_marker_preflight_hook.py`, `staged_conflict_marker_check.py`,
`git_push_master_guard.py`, `hover_self_health_shim.py`, `redaction_check.py`,
`deploy_verify_notify.py`) where silence on a clean tree is the desired
behaviour. **Those 12 are not defects.**

**THE ONE THAT WAS: `tools/session_lock_check.py`.**

```
action = sys.argv[1] if len(sys.argv) > 1 else 'start'
```

**A bare run ACQUIRED A SESSION LOCK, printed nothing, and exited 0.** Measured,
not inferred: running it bare in a throwaway clone created
`~/SAIRN-SESSION-LOCKS/b2-i6-clone.lock`. It was the only one of the fifteen
where the silence hid an **action** rather than an absence of findings.

**AND THE REPO'S OWN DETECTOR FOR THIS CANNOT SEE IT.**
`tools/bare_run_write_check.py` exists to catch a bare run that mutates — and it
checks **the repo**. This writes to `~/SAIRN-SESSION-LOCKS/`, deliberately
**outside every clone**, which is why that registry is current without a fetch.
So the write is real, it matters to every session that reads the registry, and
it is invisible to the one tool built to find it. **A named blind spot, not a
guess.**

**THE LITTER IS THE EVIDENCE.** `~/SAIRN-SESSION-LOCKS/` holds locks named after
throwaway clones that no longer exist — **`bare_scratch.lock` (2026-09-30),
`b11wt2.lock` (2026-10-06), `b12wt2.lock` (2026-10-07 07:18)** — each one a bare
run of this file inside a scratch copy, sitting in a registry other sessions
consult to decide whether somebody is working. I removed **only the one my own
sweep created**; the other three are named for chat and left, because clearing
another session's registry entry is not mine to do.

FIXED: a bare run now exits **2** with a usage block that says which verb takes
a lock. `start` is unchanged and still available — it just has to be asked for.
Verified: bare exit 2, **no lock created**, and `status` still exits 0 and reads
the real lock.

**`tools/vercel_config_check.py` — the other traceback, and the direction
matters.** `json.load` was bare, so a path that is missing or not JSON raised,
and an uncaught exception exits **1 = FINDINGS**. **Its bare run is CLEAN**
because the default path is the real `vercel.json`, which parses — so every
bare-run-only check in this repo was blind to it, and only the one-argument run
found it. It also matters more than the other twelve: the message a traceback
replaces is *"Vercel will reject this at deploy time and silently keep serving
the last successful build."*

FIXED: exit **2** with a named reason for a missing file, for invalid JSON, and
for JSON that is not an object. Verified: `CLAUDE.md` → exit 2 "is not valid
JSON", `no-such-file.json` → exit 2 "does not exist", bare → exit 0 and still
`PASS: vercel.json config within known limits`.

**TWO REAL PRODUCT FINDINGS FALL OUT OF ITEM 5 AND ARE ROUTED, NOT FIXED** —
duplicate DOM ids, where `getElementById` returns the first match so the second
element is unreachable:

| file | id | lines |
|---|---|---|
| `sairncare.html` | `fc-name` | 320 and 1082 |
| `sairnfreedom.html` | `ac-name` | 371 and 1444 |
| `sairnfreedom.html` | `ac-tbody` | 380 and 1461 |

Both are app HTML in no claim of mine. Routed with file and line.

### item 4 — ONE of the three 1800 s measurements — **IT DID NOT FINISH, SO NO BOUND IS PROPOSED**

**SUBJECT: `tools/dead_rule_sweep.py`.** Chosen because `sairn_claim.py check`
returned CLEAR, it has no entry in `docs/tool-owner-map.json`, and cody's open
row disputes its *findings* (*"a re-run of dead_rule_sweep finds 35 dead rules
where the claim…"*) — so a real wall time is worth having for a tool somebody is
about to argue about.

**CONDITIONS, waited for rather than assumed.** The script polls until no other
python/node process is on the box, records the count at the start and at the
end, and reports both:

```
box is quiet after 12s of waiting
SUBJECT  tools/dead_rule_sweep.py
CLONE    C:/Users/marsh/AppData/Local/Temp/b2-i6-clone   (a CLONE, not a worktree)
CEILING  1800s, unbuffered
LOAD at start : 0 other python/node process(es)

EXIT      TIMEOUT-AT-1800
WALL TIME 1800.0s  (30.0 min)
LOAD at end   : 12 other python/node process(es)
```

**THE ANSWER IS A LOWER BOUND, NOT A NUMBER: > 1800 s.** The item says *"propose
a bound only from that number"* — and there is no number, so **no bound is
proposed.** Inventing one from a run that did not finish is the thing that rule
exists to prevent.

**AND THE RUN IS CONTAMINATED IN ITS SECOND HALF, which is stated rather than
buried:** the box went from **0 to 12** other python/node processes while it ran.
Other clones' push-gate hooks fire whenever their sessions push and I cannot
stop them. So even a completed run on this box would need the load curve printed
beside the number.

**WHAT 30 MINUTES PRODUCED: THREE LINES.**

```
DEAD RULE SWEEP -- criteria 2026-09-29.1
criteria lock: 6/6 fixtures classify correctly, on hand-built sources only
sandbox: C:\Users\marsh\AppData\Local\Temp\drs-sandbox-uu8ey11x
```

Then nothing, for 29 minutes, under `python -u` — so this is the subject's own
silence, not buffering. **That is cross-domain convention 10 inside the tool
being measured: a long run whose first check is at the end.** It cannot be
bounded because it cannot be observed, and the fix is to the TOOL before the
bound: emit a progress line per unit of work, and the first completed run then
gives a real number *and* tells you where the time goes.

**THE MEASUREMENT THAT WOULD ALLOW A BOUND, named instead of a guess:** one run
with **no ceiling** on a quiet box, after the tool emits progress, repeated
**three** times — a bound from a single sample has no variance behind it, and
`assurance_case.py` was failing a 90 s bound at 86.8 s on variance alone.

**THE OTHER TWO ARE NOT MEASURED AND ARE NOT GUESSED AT.**
`guard_ablation.py` and `red_suite_register_check.py` keep their only honest
figure: **> 600 s**. The item said measure ONE and that is what was done.

### item 4a — THE SWEEP LEAKS SANDBOX WORKTREES, AND THAT IS ITEM 6a's MECHANISM WITH 18 LIVE INSTANCES

`dead_rule_sweep.py` builds its sandbox as a **linked worktree** and leaves it
registered. **15 `drs-sandbox-*` directories are on disk**, and the run above
added `drs-sandbox-uu8ey11x` to the clone's registration list.

**It is not alone.** My live clone had **19 registered worktrees, 18 of them
leaked probe sandboxes** — `check4-probe-*`, `condcov-*`, `defreg-probe-*`,
`gate12-*`, `r5-*`, `sairn-abl-*`, `sairn-sab-*`.

**THAT IS THE SAME FINDING AS ITEM 6a, WITH A COUNT.** A linked worktree shares
`.git/config` with the clone that owns it, so every one of those 18 is a live
path by which a tool's `git config` write lands in the real clone's config. 6a
proved the write happens; this says there were **18 doors open** at the time.

**I pruned the FIVE that are mine** — `wt-i3`, `wt-suite2`, `wt9` from this
session and `wt-suite`, `wt-tools` from the previous one — taking the clone from
19 registrations to 14. `core.bare` confirmed `false` after. **The other 13 are
other sessions' probe leaks and I did not touch them**: pruning another session's
worktree registration while its probe may still be running is the same
cross-clone reach I refused in item 5's landing_verification entry.

Routed: the leak is per-probe and the fix is per-probe — a throwaway **clone**,
as `tests/push_gate/check8_probe.py` already does, or `shutil.rmtree` plus
`git worktree prune` in a `finally`.

### item 12 — THE THREE CHECKS AT FINAL HEAD, each exit captured on its own line

```
python -u tools/audit_event_type_check.py        EXIT 1
python -u scratchpad/attr_scan.py               EXIT 0
python -u tools/defect_register.py --check      EXIT 0
```

| check | headline | reading |
|---|---|---|
| `audit_event_type_check.py` | **3 of 3 tables with a CHECK reject at least one emitted value, 11 distinct values** | **EXIT 1 IS THE CORRECT ANSWER AND NOT A REGRESSION.** The repair is the three STEP 0 `ALTER`s and they are **printed, applied nowhere**. This number will not move until Michael runs them, and if it ever reads 0 without that having happened, the checker is what broke. |
| `attr_scan.py` | **UNATTRIBUTED: 0 of 49** | holds at this HEAD, as batch b1 left it. LEXICAL and over THREE apps — "0 of 49" is 0 of those three by that criterion. |
| `defect_register.py --check` | **OK: 489 records, every commit resolves, every field in vocabulary** | 486 at the close of b1; +3. 1 external and unverified by construction. |

### item 13 — THE scrutiny-flags STASHES — PARKED. Not dropped, not committed.

`docs/scrutiny-flags.json` is **CC'S FILE** — declared in cc's live batch-17
FILES. The rows in it were written by **cc's own `scrutiny_flag` tool**,
recording MY commits. I will not commit a file I do not own and I will not
revert a record another session's tool just wrote.

**FIVE PARKED STASH ENTRIES, all `docs/scrutiny-flags.json` only** — read off
`git stash list` rather than from memory, which is how the count was corrected
from four before this was pushed:

```
stash@{0}   "cc scrutiny rows (round 6)"
stash@{1}   "cc scrutiny rows (round 5)"
stash@{2}   "cc scrutiny rows (round 4)"
stash@{4}   "cc scrutiny rows (round 3)"
stash@{5}   "cc scrutiny rows (round 2)"
```

`stash@{3}` is MINE — "my 3 register records, re-addable from
scratchpad/reg_add.py", left from batch b1 — and is not part of this item.

**OWNER: cc. ACTION: cc decides.** cc's own batch-17 item 6 says it will *"READ
them read-only and decide with a stated reason; I do not pop or write another
clone's stash"* — which is the right posture from the other side and means this
is already in hand. **The stash indices shift as entries are added**, so cc
should match on the MESSAGE (`cc scrutiny rows (round N)`) rather than the index.

---

## PUSHED STATE

**`origin/main` and my commits are reported in the final report with
`merge-base --is-ancestor` verification taken AFTER the push, not from this
file.** At the moment this section was written the batch's commits were:

| sha at write time | what |
|---|---|
| `7829e3f0` | the batch-18 claim |
| `db7558e8` | handoff rows for items 1, 3, 6, 6a, 6b |
| `293152da` | the `sv_audit_log` refusal + H0/H1/H2 + STEP 13/14 SQL |
| `6c66f0e9` | the three tool fixes + RULE F |

**Shas later than `6c66f0e9` were rewritten by the landing rebase** — which is
RULE F's whole subject — so the authoritative list, verified against
`origin/main`, is in the final report and not here.

**NO GATE WAS OVERRIDDEN. `SAIRN_SEED_GATE=off` was never used.**

## CLAIMS HELD, AND WHAT WAS REFUSED

**HELD:** `hank` / `platform`, batch 18. My b1 claim had **expired** at session
start and was re-taken.

| work | state | holder and timestamp |
|---|---|---|
| Tier A discharge | **BLOCKED, nothing discharged** | **cc, 2026-10-07T23:20:05Z** — declares `docs/tier-a-reviews.json` FIRST in FILES |
| `docs/METHODOLOGY.md` | **BLOCKED, not touched** | **cc 2026-10-07T23:20:05Z** and **fourth 2026-10-07T20:30:06Z** |

Each re-checked **once**. No retry on either.

**AND ONE TRAP WORTH THE SPACE:** `sairn_claim.py check platform "tier a review
discharge oldest eligible"` returned **CLEAR**. The word matcher does not read a
FILES declaration. Taking that CLEAR as permission would have put two sessions
into the same ledger. **A CLEAR from the matcher is not a clear from PR §4.3.**

**READ ONLY, NEVER WRITTEN:** `docs/tool-owner-map.json` (cc's) —
the item 10 population came out of it and nothing went back in.

**APPENDED THROUGH A TOOL, NEVER EDITED:** `docs/defect-density-register.json`
via `defect_register.py --add` (the same posture as b1).

**NOT TOUCHED AT ALL:** `docs/METHODOLOGY.md`, `docs/tier-a-reviews.json`,
`docs/known-red-suites.json`, `docs/scrutiny-flags.json`, and **anything under
`.claude/skills/sairn-hover-auditor/`**.

## OPEN WORK, WITH THE EXACT NEXT STEP PER ITEM

| # | open item | exact next step | owner |
|---|---|---|---|
| 1 | **89 REAL suite failures** | they are real, alone, on a restored tree. Triage by owner from `<scratchpad>/i3.table.txt`; nothing here claims they are new | chat to split |
| 2 | 4 suite files **TIMEOUT alone at 240 s** | `run_defect_register_probe.py`, `run_hover_audit_method_sabotage_probe.py`, `stale_row_sweep_control.py`, `push_gate/check12_probe.py` — re-run each with no ceiling on a quiet box | next hank |
| 3 | **THE SUITE DIRTIES ITS OWN TREE** (5 paths) | so "run it in a clean worktree" does not produce a clean verdict; only per-file runs do. Either make the generators run in a copy or have the harness restore between files | chat → harness owner |
| 4 | **`core.bare` writer: `tests/push_gate/check4_probe.py` and `check7_probe.py`** | replace `git worktree add` with `git clone --local --no-hardlinks`, exactly as `check8_probe.py` did on 2026-10-06. Owner map: `basis NONE, owner null` | **chat to assign** |
| 5 | **13 leaked worktree registrations** on the live clone | each is a live door for a shared-config write. Per-probe fix: throwaway clone, or `rmtree` + `git worktree prune` in a `finally`. I pruned only my own 5 | **chat to assign** |
| 6 | `cron_liveness_check.py` / `audit_checkpoint_status.py` **destroy a good record** when their secret is absent | decide whether a could-not-tell may overwrite a dated OK. Both are in the bare-run-writers allowlist, so this is a design call, not a leak | **chat** |
| 7 | **3 stale session locks** — `bare_scratch.lock`, `b11wt2.lock`, `b12wt2.lock` | named after throwaway clones that no longer exist, in a registry other sessions read. Not mine to clear | **chat** |
| 8 | **`bare_run_write_check.py` cannot see outside the repo** | `~/SAIRN-SESSION-LOCKS/` is outside every clone by design, so a bare-run write there is invisible to it. Either widen the scope or declare the blind spot in its own output | **chat to assign** |
| 9 | **STEP 0 — THREE `ALTER`s** | run the PRE-FLIGHT `pg_constraint` query, then 0a / 0b / 0c. They repair code already pushed and currently inert | **Michael** |
| 10 | **STEP 13 — `sv_audit_log`** | decide between 13a/13b/13c (make the table take the row, and argue about `revoke update`) and **13-ALT, a new `sairnvet_audit_log`**, which I would put first | **chat → Michael** |
| 11 | **STEP 14 — `rf_schedule.status_changed_by`** | run the SQL, then the four-step code change, **including rewriting arm D3** of `sd_data_write_attribution_three_apps.js` in the same commit | **Michael, then a build session** |
| 12 | `dead_rule_sweep.py` **> 1800 s, no bound proposable** | make the tool emit progress FIRST, then one uncapped run on a quiet box, three times | next hank |
| 13 | `guard_ablation.py`, `red_suite_register_check.py` | still only **> 600 s**. Not measured this batch and not guessed at | next hank |
| 14 | **30 suites RED AND NOT RECORDED** in `docs/known-red-suites.json` (registry says 75, this run says 101) | `known_red_check.py --from-run <log>` reproduces it. Register is **fourth's** | **fourth** |
| 15 | **3 real duplicate DOM ids** | `sairncare.html` `fc-name` (:320, :1082); `sairnfreedom.html` `ac-name` (:371, :1444) and `ac-tbody` (:380, :1461). `getElementById` returns the first, so the second element is unreachable | **chat to assign** |
| 16 | `api/sd-data-exec-context-isolation.test.js` **declares cross-tenant coverage and grades NONE** | read it; either the declaration is wrong or the test is | **chat to assign** |
| 17 | **14+ tools with header claims and NO suite** | `first_article_inspection.py` names them. Coverage owed, not a defect | chat |
| 18 | **RULE E and RULE F** | land into `docs/METHODOLOGY.md` when it is unclaimed. RULE F belongs beside the generated-document rule in the **process rules**, as its no-conflict sibling | chat / fourth |
| 19 | `tools/gh_push.py:182` | **already taken by cc's batch 17 item 4** — routed from my b1 and picked up. Nothing owed by me | cc |
| 20 | `tools/hover_separation_ci.py:97` | unchanged from b1: decide which comparison the constant-plus-predicate API is meant to make | **chat** |
| 21 | `docs/scrutiny-flags.json` stashes | 4 parked entries, match on the MESSAGE not the index | **cc** |

## TRANSCRIPT AND ARTEFACTS

**This session's scratchpad** — every captured exit code, every sweep script,
every mutation backup:

```
C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-hank\a517bec7-3fd2-4475-835c-6432b2acaa34\scratchpad
```

| file | what |
|---|---|
| `suite.clean.out` | the clean-worktree suite run, unbuffered, with `SUITE_EXIT=1` on its last line |
| `i3.rerun.json` / `i3.table.txt` | all 101 FAILs re-run alone, with verdict and first failing line |
| `i4.log` / `i4.dead_rule_sweep.py.out` | the 1800 s measurement and the three lines it produced |
| `i6.pass1.json` / `i6.refusals.txt` / `i6.table.txt` | the 62 bare re-runs, every refusal text, the four-bucket accounting |
| `b2_item6_pass2.py` | every complete command line, written out |
| `i10.json` / `i10.log` | 175 ownerless tools × 2 runs, 15 flagged |
| `barehunt.out` / `barehunt2.out` | the two negative controls that eliminated the 62 tools as the `core.bare` writer |
| `gitconfig.bare-true.bak` | the corrupted `.git/config`, kept |
| `i6.damage.cron.diff` / `i6.damage.audit.diff` | the two status documents a bare run destroyed, before restoring them |
| `i5.nav.before.txt` / `i5.nav.after.txt` | nav_panel_check over all 22 apps, before and after |
| `land.sh` / `repoint.py` / `reg_add.py` | the landing order RULE F describes |

**Previous session's scratchpad**, which holds `tools_sweep.tsv` (the 315-script
sweep this batch's items 5, 6 and 9 all read from) and `f.rat.out`:

```
C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-hank\16753c01-e018-4c71-af08-342c1baa72e6\scratchpad
```

**Previous handoff:** `docs/handoff-hank-2026-10-07c.md` (batch b1, `afe526b2`).
**Routed findings:** `docs/2026-10-07-hank-routed.md` — §1 gh_push (taken by cc),
§2 the auditor-namespace retraction, §3 RULE E, §4 RULE F.
**Printed SQL:** `docs/2026-10-07-hank-migration-sql-for-michael.md` — STEP 0
(three ALTERs), STEP 1-12 (twelve tables), **STEP 13** (sv_audit_log, with
13-ALT), **STEP 14** (rf_schedule).
