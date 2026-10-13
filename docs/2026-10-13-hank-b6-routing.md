# hank b6 — routing and methodology, 2026-10-13

Everything here is OUTSIDE `api/`, which is the only directory this batch was
allowed to edit. Nothing below was touched; each item names its owner, the exact
file, and what to do.

---

## 1. TO cc — THE THIRTEEN BARE-RUN WRITE FINDINGS (carried from b5)

Full log: `docs/hank-evidence/b5_bare_run_write_check.out`. 313 tools swept, 2
`WRITES(bare)`, 11 `WRITES(SHARED)`, 4 allowlisted, **34 `COULD NOT RUN` at the
25s timeout — so the sweep is conclusive for 279 of 313, and "13 findings"
without that denominator overstates coverage.**

### THESE THREE FIRST. They edit another session's status row.

The shared registry is what every clone reads to decide whether somebody else
is working, and it lives **outside every clone** — so unlike the WORKTREES and
GITCONFIG findings, these are global and not artefacts of the scratch clone.

| tool | exit | what it changed |
|---|---|---|
| `tools/idempotency_check.py` | 1 | `SAIRN-SESSION-LOCKS/status/hover.json` |
| `tools/register_freshness_check.py --help` | 1 | `SAIRN-SESSION-LOCKS/status/fourth.json` |
| `tools/shape_antipattern_check.py` | 1 | `SAIRN-SESSION-LOCKS/status/hover2.json` |

### Then the rest

`WRITES(bare)` — both write a tracked document and are probably INTENDED
writers missing an allowlist entry rather than defects (`tool_owner_map.py` is
a generator by name):

* `tools/mech_gate_live_probe.py` → `docs/live-residue/…json`
* `tools/tool_owner_map.py` → `docs/tool-owner-map.json`

`WRITES(SHARED)`, worktrees or git config: `condition_coverage.py`,
`dead_rule_sweep.py`, `guard_ablation.py`, `guard_ablation.py --help`,
`install_git_hooks.py` (**GIT CONFIG** — and `core.hooksPath` is the setting
whose absence makes a clone arm no hooks at all),
`invisible_in_pattern_check.py --help`, `run_all_tests.py`, `run_semgrep.py`.

**FOUR OF THE THIRTEEN FIRE ON `--help`.** A read-only-sounding invocation that
mutates is PR §1.4. b5 hit a fresh instance of it —
`tools/sairn_rebase_resolve.py --help` *performed a merge* instead of printing
usage — and it happened to be the merge I wanted, which is the worst way to
find out.

---

## 2. TO cc — A CHECKER DISABLED BY A PROSE MENTION. Third instance of one shape.

**`tools/audit_event_type_check.py`.** Its `auditPinSetup` call-site detector
tests `PIN_SETUP_HELPER in s` against **raw source**. I wrote that detector in
b4. In b6 a comment in `api/audit-checkpoint.js` *mentioned the helper by name*
— that file is not a caller and has no `const APP` — and the tool exited **2
COULD NOT RUN**:

```
COULD NOT RUN: api/audit-checkpoint.js calls auditPinSetup but has no
`const APP = '...'` for this check to resolve its table from.
This is NOT "every event type is allowed". Nothing was compared.
```

**A prose mention disabled the whole check.** I reworded the comment, so the
tool runs again — but the next mention does it again.

**FIX:** blank comments before that membership test, the same way the file
already blanks them elsewhere (`stripComments` / the line-based idiom at
`api/sd-data-sf-session-gate.test.js:83`). Add a fixture arm: a file containing
the helper name **only in a comment** must NOT be treated as a caller.

**This is the third instance in this batch family of one shape** — a checker
whose universe includes the text that *describes* its subject. The first two
were the ghost-field probe's own payloads and `docs/known-red-suites.json`'s
write-up of its own failure, both in b5.

---

## 3. TO cody — THE SAIRNfreedom DRIVEN ROLE MATRIX

`api/_lib/sf-roles.js` and `api/sd-data-sf-role-matrix.test.js` landed in b6
(14 arms, exit 0). That suite proves the policy is **complete, locked, mirrored
and wired**. It drives **no session**, and says so in its own closing lines.

**What is yours:** the driven half — **10 roles × 36 resources × 2 verbs = 720
arms**, each with a real signed session, asserting ALLOW answers 200 and DENY
answers 403 with the `denyMessage` text.

Shape to copy: `api/sd-data-law-role-matrix.test.js`'s `loadHandler()` +
`withToken(app, role)` helpers. The policy table is importable:
`require('./api/_lib/sf-roles').SF_ROLE_MATRIX`, so the expected verdict per
cell is derivable rather than transcribed — **but derive the EXPECTATION from
the table and the OBSERVATION from the handler, never both from the table**, or
the suite asserts the table against itself.

**The two highest-value arms, if 720 is too many to start with:**

1. **`sf_officers` write by each of the eight non-provisioning roles → 403.**
   That roster is the post's governance record and three guards run off it.
2. **`sf_ledger` / `sf_disbursements` / `sf_gaming_expenses` write by
   `records.write` → 403.** `records.write` is "Records and minutes" and was
   the role most likely to be given money access by accident; these are ORC
   Chapter 2915 payee records.

---

## 4. TO cody — THE bld_draws ROLE ARMS (and tell H2)

`api/sd-data.js`'s `bld_draws` branch is now `BLD_DRAW_ROLES = ['owner',
'office']`, read **and** write.

**Arms wanted:**

| arm | expected |
|---|---|
| `pm` session, `read bld_draws` | **403 FORBIDDEN** |
| `pm` session, `write bld_draws` | **403 FORBIDDEN** |
| `owner` session, `read` / `write` | **allowed** (reaches the handler) |
| `office` session, `read` / `write` | **allowed** |
| no session | 401 `NO_SESSION` (already held) |

**THE NEGATIVE CONTROL MATTERS MORE THAN THE POSITIVE ONE HERE:** a gate that
refuses everybody passes every supervisor-denied arm. The `owner` and `office`
arms are what make the `pm` arms evidence.

**FOR H2 (the hover auditor), explicitly:** seq664's open product question —
*"NOT restricted to owner or office on purpose … that product question is
reported rather than shipped inside a security fix"* — **is now answered by
Michael and closed.** The b5 discharge verdict on that obligation left the same
line standing (*"ANY sairnbuild session can still author or inflate a draw
AMOUNT"*) and that is no longer true for `pm`. The verdict text is unchanged
and this is the amendment.

**Still open and NOT closed by this:** the Draw Requests panel is still not
role-gated client-side, so a `pm` can open it and will now see a 403 rather
than a hidden tab. Refusing is the server's job and hiding is the page's; the
panel half is a client change nobody has been asked for.

---

## 5. TO cody — `tests/sd_data_write_attribution_three_apps.js` arm D3

The brief asks for the D3 rewrite. **The cause is measured, not guessed:**
`rf_schedule/set_status` no longer merges the attribution into the `data` blob.
It now writes three real columns — `status_changed_by`,
`status_changed_by_role`, `status_changed_at` — because Michael ran STEP 14 on
2026-10-13.

So any arm asserting `data.updatedBy` / `data.updatedByRole` on that path is
now asserting a shape the handler no longer writes. **Re-point it at the three
columns**, and keep the arm that proves `created_by` is UNTOUCHED: that column
is `not null` and means who *created* the day, and overwriting it to record a
later edit was the thing the original note refused to do.

---

## 6. TO cody — `tests/run_audit_event_type_probe.py` arm H0 has been failing since b4

```
FAIL  H0. the AUDIT_TABLES allowlist is found and parsed at all.
      Without this the two arms below would pass on an empty list
```

**CAUSE, measured:** the arm does
`re.search(r'const AUDIT_TABLES = \{([^}]*)\}', audit_js)` and then
`re.findall(r'(\w+)\s*:\s*true', …)`. In **b4 I made `AUDIT_TABLES` DERIVED** —
it is now `const AUDIT_TABLES = {};` followed by a `forEach`, so the literal has
no `name: true` entries and `listed` comes back empty.

**FIX:** parse **`AUDIT_TABLE_BY_APP`** instead and take its *values*; that is
the authoritative literal now, and `AUDIT_TABLES` is derived from it. Arms H1
and H2 both pass and are unaffected.

**This is the same class as item 2 and the b5 convention candidate:** a refactor
that centralises a pattern silently removes it from every checker keyed to the
old shape, and the checker goes on printing a number.

---

## 7. TO MICHAEL — TWO SQL ITEMS, AND BOTH ARE SMALL

### 7a. The audit checkpoint covers 3 of 16 logs. One ALTER fixes it.

`api/audit-checkpoint.js` now derives its table list from
`AUDIT_TABLE_BY_APP` (16 tables) but **filters it through `SCHEMA_PERMITTED`**,
which mirrors `sql/audit_checkpoint_schema.sql:57-59` — still the original
three. Filtering is why this is not a break: deriving alone would have turned a
silent gap into thirteen rejected INSERTs.

```sql
alter table public.sairn_audit_checkpoint
  drop constraint sairn_audit_checkpoint_audit_table_check;
alter table public.sairn_audit_checkpoint
  add constraint sairn_audit_checkpoint_audit_table_check
  check (audit_table in (
    'sairnbiz_audit_log','sairnbuild_audit_log','sairncare_audit_log',
    'sairncode_audit_log','sairndental_audit_log','sairndesign_audit_log',
    'sairnfreedom_audit_log','sairngrounds_audit_log','sairnlaw_audit_log',
    'sairnlegacy_audit_log','sairnmechanical_audit_log','sairnroofing_audit_log',
    'sairnscape_audit_log','sairnsenior_audit_log','sairnvet_audit_log',
    'stonedesk_audit_log'));
```

**After it runs, ONE LINE of code changes:** set `SCHEMA_PERMITTED =
ALL_AUDIT_TABLES` in `api/audit-checkpoint.js`. Until then the job reports the
gap honestly in `uncovered` / `uncovered_why` on every response and heartbeat
rather than implying 16.

**ALSO CONFIRM `sql/audit_checkpoint_schema.sql` HAS BEEN RUN AT ALL.** Its own
header says *"WRITTEN 2026-09-14. NOT RUN."* and
`docs/AUDIT-CHECKPOINT-STATUS.md` has read `COULD NOT TELL` since that date. If
the table does not exist, the endpoint 503s daily and nothing is checkpointed
anywhere.

### 7b. The `sql/*_audit_log_schema.sql` files no longer describe the database.

`tools/audit_event_type_check.py` exits 1 on three tables
(`sairncode_audit_log`, `sairnlaw_audit_log`, `stonedesk_audit_log`) because it
reads CHECK constraints out of **`sql/` files**. You widened those constraints
live on 2026-10-13; the files still carry the narrow lists —
`grep -c pin_setup sql/stonedesk_audit_log_schema.sql` is **0**.

So the checker now reports a gap that **no longer exists in the database**, and
will keep doing so. Either amend the three schema files to match what was run
(`sql/` is not in my scope this batch) or add the STEP 0 ALTERs to them as
appended statements. Until then that exit 1 is a false positive and anyone
reading it will chase a closed finding.

---

## 8. TO MICHAEL — A REAL-USER PRODUCT QUESTION. The only one in this batch.

**`api/sf-auth.test.js` has been failing at HEAD, before and after b6** (37
passed, 1 failed both ways — measured by stashing):

```
FAIL  ROLES_BY_APP, the schema check constraint and CAPABILITIES agree
      ROLES_BY_APP.sairnfreedom and sairnfreedom.html CAPABILITIES disagree
```

**`sairnfreedom.html:2314` declares `trustee.audit`** in `CAPABILITIES` — added
2026-09-27 for the VFW quarterly trustee audit, with its own written
justification citing the VFW Manual of Procedure (trustees audit quarterly, are
individually liable, the Quartermaster must not prepare the audit, a missed
audit can void the bond).

**It is not in `ROLES_BY_APP.sairnfreedom`.** So `api/sf-auth.js` **refuses to
provision a credential with that role**. A post can assign the Trustee
capability in the Access panel and then **cannot give that trustee a sign-in**.

**THE QUESTION:** should a trustee be able to sign in?

* **If yes** — `trustee.audit` is added to `ROLES_BY_APP.sairnfreedom`, the
  `sf_trustee_audits` row in `api/_lib/sf-roles.js` gains an eleventh column
  granting it `rw`, and the employee-auth CHECK constraint needs the role too.
* **If no** — the capability is display-only and should say so in
  `sairnfreedom.html`, because it currently looks like an assignable office.

**I did not decide this**, and the reason is the rule rather than caution: a
per-app role vocabulary is the thing CLAUDE.md names as needing an explicit
judgment call, and that arm exists precisely to force it. Today
`sf_trustee_audits` write is governance-only and `finance.write` has READ ONLY
— deliberately, because the source says the Quartermaster must not prepare the
audit.

---

## 9. METHODOLOGY — the author cannot review his own record, and the gate lets him queue one anyway

**BLAMELESS, and the blame-free part is load-bearing:** nothing below is a
mistake anybody made. It is a rule interacting with an assignment policy.

### The state

Three `api/` Tier A obligations are open, all authored by hank, and **hank can
discharge none of them** — `tools/tier_a_review_gate.py` refuses a self-review
at write time, which is the one thing it exists to refuse.

| opened_at | reviewer | sha | note |
|---|---|---|---|
| `2026-09-27T03:42:29Z` | fourth | **ORPHANED** | 387h+. The sha resolves only in hank's clone; fourth cannot fetch the diff. |
| `2026-10-06T06:14:34Z` | cody | **ORPHANED** | Same. |
| `2026-10-12T01:51:33Z` | cc | REACHABLE | b4's nine-resource gate obligation. Reviewable as-is. |

Five of the fourteen open records are hank-authored; **zero are assigned to
hank**. My queue is empty and my own backlog is unclearable by me.

### Why it happens

The gate's `--open` **assigns a reviewer at open time**, and the author has no
say in it. So an author can queue a record whose reviewer never runs:
`cloud` holds two and has never discharged one; its last claim expired 386h ago.
Two of the three above also carry a sha the assigned reviewer **cannot fetch**,
which makes the record unreviewable by anybody rather than merely unassigned.

The author cannot fix either condition: he may not review it, and
`--reseat-shas` **refuses** an orphaned sha whose subject twin does not contain
the record's files, on the correct grounds that *"a wrong sha is worse than a
dangling one, because a dangling one is visibly broken."*

### THE PROPOSED RULE, which stops the author queuing a record the gate will refuse to let him review

> **`--open` must REFUSE, at open time, to assign a reviewer that cannot
> discharge — and must stamp a sha the assignee can actually fetch.**
>
> Concretely, three checks at `--open`, each failing closed:
>
> 1. **The assignee must be a LIVE session.** `tools/sairn_status.py` already
>    knows: it prints `LIVE` / `DEAD` per session from a real PID check. An
>    assignment to a session with no live row, or whose last claim expired more
>    than 48h ago, is refused with the list of eligible sessions. This alone
>    retires the `cloud` problem.
> 2. **The sha must be REACHABLE from `origin/main` at open time**, not merely
>    resolvable locally. An obligation stamped on an unpushed commit is
>    unreviewable the moment it is rebased, and that is the normal case on a
>    five-clone repo — both orphaned records above are exactly this.
>    `--open` already has the sha; `git merge-base --is-ancestor` is the check.
>    Refuse, and say "push first, then open".
> 3. **Never assign the author.** Already enforced at `--discharge`; moving it
>    to `--open` makes the refusal arrive when it can still be acted on rather
>    than days later.
>
> **Why `--open` and not `--discharge`:** at `--discharge` the information is
> useless — the push has landed, the rebase has happened, and the author is the
> only person present. At `--open` the author is still in the loop and can
> push, re-stamp, or pick a live reviewer. **This is the same reasoning the
> gate itself used to move the self-review refusal to write time: "refusing to
> WRITE a self-signed record and refusing to PASS one are different controls."**

**Owner: cc** (`tools/tier_a_review_gate.py` is cc's), plus the three records
themselves:

### TO cc — re-seat and discharge the three

* **Re-seat first.** The two orphaned records cannot be reviewed until their
  shas reach `origin/main`. `--reseat-shas` classifies both WEAK (file-set
  subset) and will not act without `--write --write-weak-basis`; that is a
  judgement for their *author's* files, and I am the author, so it is routed
  rather than taken.
* **Then discharge all three.** The reachable one (`2026-10-12T01:51:33Z`, nine
  gated resources) is ready now and is already assigned to cc.
* Full table and the eleven non-`api/` records:
  `docs/2026-10-13-hank-tier-a-routing.md` (b5).

---

## 10. Nothing in this batch touched

`tests/`, `tools/`, `sql/`, `docs/` other than this file and
`docs/hank-evidence/` (two probe artefacts, committed because the report cites
them and a cited file in `%TEMP%` is a dangling citation), the handoff, the
report and the digest. `.claude/settings.json` is modified and **uncommitted**,
deliberately: hooks stay cleared and cc owns that file's merges.
