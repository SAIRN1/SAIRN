# Hank handoff — 2026-10-13, batch b6

Written **before** the report, at a point where nothing is half-finished: every
code change is committed, every suite has been run and its exit code recorded,
the claim is confirmed released on `origin/main`, and no file is mid-edit.

**Push state is the one thing this file cannot assert.** It is written before
the push. Verify with `git log --oneline origin/main` rather than from here.

| sha | what |
|---|---|
| `54a58ad3` | the whole of items 1–4: SAIRNfreedom lock + 36×10 role matrix + server-side officer guards, `bld_draws` owner/office only, the audit-checkpoint coverage fix, `rf_schedule` status columns |
| `c6f64b3b` | `docs/2026-10-13-hank-b6-routing.md` — ten routed items and the methodology rule |

Three commits from b5 were still unpushed at pickup and are included:
`f0e81b92`, `dfb20c0c`, `1ecb650e`.

---

## Claims

**NONE HELD.** `sairnsenior` was released at the end of b5 and the release is on
`origin/main` — `git merge-base --is-ancestor 618cbd9f origin/main` succeeds,
and `sairn_claim.py list` shows only cody and cc active.

Re-running `release sairnsenior` this batch exits **3** with *"No active claim
of yours matches 'sairnsenior'"* plus a push complaint. **That is the correct
answer to an already-released claim**, not a failure — the push half fails only
because `.claude/settings.json` is deliberately unstaged (see below) and
`git rebase` refuses with unstaged changes.

**No claim was taken for b6.** Every file touched is in `api/` except the
routing doc, the handoff, the report and the digest, and no other live claim
declares any of them: cody's b6 claim is TESTS ONLY and explicitly says
`api/sd-data.js` is hank's; cc's b5 claim declares `.claude/settings.json` and
tools, and explicitly does not take `api/sd-data.js`.

---

## Hooks — the thing a fresh session will get wrong

`.claude/settings.json` carries **`hooks: {}`**, per Michael. **Never restore
them. Never commit this file — cc owns its merges.** It shows as
`M .claude/settings.json` and must stay unstaged. Both `.bak` files untouched.

**Every `git rebase` in this clone refuses** with `cannot rebase: You have
unstaged changes`. The pattern that works:

```
cp .claude/settings.json "$SCRATCH/hooks-empty.json"
git checkout -q -- .claude/settings.json
git fetch origin main -q && git rebase origin/main
cp "$SCRATCH/hooks-empty.json" .claude/settings.json
```

**A PLAIN `git checkout -- .claude/settings.json` RE-ARMS ALL 23 HOOKS
SILENTLY.** That happened in b5: a parked file was never restored and the hooks
ran again for several commands before it was noticed by reading the file. The
instruction "never restore the hooks" is violated by an ordinary git operation
and nothing announces it.

---

## OPEN — exact next step per item

### 1. Michael: two small SQL items. Both are in the routing doc §7.

**7a — the audit checkpoint covers 3 of 16 audit logs.** `api/audit-checkpoint.js`
now derives the list from `AUDIT_TABLE_BY_APP` but filters it through
`SCHEMA_PERMITTED`, which mirrors the checkpoint table's own CHECK constraint —
still the original three. **One ALTER** (written out in the routing doc) widens
it; then **one line** of code changes (`SCHEMA_PERMITTED = ALL_AUDIT_TABLES`).
Until then the job reports the gap in `uncovered` / `uncovered_why` on every
response and heartbeat rather than implying sixteen.

**AND CONFIRM `sql/audit_checkpoint_schema.sql` HAS BEEN RUN AT ALL.** Its own
header says *"WRITTEN 2026-09-14. NOT RUN."* and `docs/AUDIT-CHECKPOINT-STATUS.md`
has said `COULD NOT TELL` since that date. If the table does not exist the
endpoint 503s daily and nothing is checkpointed anywhere — which is also the
most likely explanation for the watchdog's DEAD email surviving a restart.

**7b — the `sql/*_audit_log_schema.sql` files no longer describe the database.**
`tools/audit_event_type_check.py` exits 1 on three tables because it reads
CHECKs out of `sql/` files and you widened them live on 2026-10-13.
`grep -c pin_setup sql/stonedesk_audit_log_schema.sql` is **0**. That exit 1 is
now a **false positive** and will stay one until the files are amended. `sql/`
was out of scope for this batch.

### 2. Michael: the one real-user product question. Routing doc §8.

`sairnfreedom.html:2314` declares **`trustee.audit`** in `CAPABILITIES`;
`ROLES_BY_APP.sairnfreedom` does not. So a post can assign the Trustee office in
the Access panel and then **cannot give that trustee a sign-in** —
`api/sf-auth.js` refuses to provision an unknown role.

`api/sf-auth.test.js` has been RED at HEAD for exactly this, **before and after
b6** (37 passed / 1 failed both ways, measured by stashing). **Should a trustee
be able to sign in?** If yes, three places change together (ROLES_BY_APP, the
`sf_trustee_audits` row in `api/_lib/sf-roles.js`, the employee-auth CHECK). If
no, the capability should say it is display-only.

Not decided here: a per-app role vocabulary is what CLAUDE.md names as needing
an explicit judgment call, and that arm exists to force it.

### 3. cody: four routed items. Routing doc §§3–6.

* **The driven SAIRNfreedom role matrix** — 10 roles × 36 resources × 2 verbs.
  The policy suite landed (`api/sd-data-sf-role-matrix.test.js`, 14 arms) and
  drives **no session**. Derive the EXPECTATION from `SF_ROLE_MATRIX` and the
  OBSERVATION from the handler, never both from the table. Two highest-value
  arms named in the doc.
* **The `bld_draws` arms** — `pm` denied on read and write, `owner` and
  `office` allowed. **The owner/office arms matter more than the pm arms**: a
  gate that refuses everybody passes every supervisor-denied arm.
* **`tests/sd_data_write_attribution_three_apps.js` arm D3** — `set_status` no
  longer merges into the `data` blob; re-point at `status_changed_by`,
  `status_changed_by_role`, `status_changed_at`, and keep the arm proving
  `created_by` is untouched.
* **`tests/run_audit_event_type_probe.py` arm H0 — failing since b4**, cause
  measured: it parses the `AUDIT_TABLES` literal and I made that literal
  derived. Parse `AUDIT_TABLE_BY_APP` and take its values.

### 4. cc: three groups. Routing doc §§1, 2, 9.

* **The 13 bare-run write findings**, with the three that edit another
  session's `status/*.json` listed first — that registry lives outside every
  clone, so those three are global.
* **`tools/audit_event_type_check.py` is disabled by a PROSE MENTION** of the
  pin-setup helper. Blank comments before that membership test and add a
  fixture arm: a file naming the helper only in a comment must not count as a
  caller. **Third instance in this family** of a checker whose universe
  includes the text describing its subject.
* **The three `api/` Tier A records**: re-seat the two orphaned shas, then
  discharge all three. Hank authored all three and the gate refuses a
  self-review, so this cannot be cleared from here. Re-seating is a judgement
  about the author's own files and is therefore routed rather than taken.

### 5. The methodology rule is a proposal, not a change. Routing doc §9.

> `--open` must REFUSE, at open time, to assign a reviewer that cannot
> discharge, and must stamp a sha the assignee can fetch.

Three checks, each failing closed: the assignee must be a LIVE session
(`sairn_status.py` already knows from a real PID check — this alone retires
`cloud`, which holds two and has never discharged one); the sha must be
REACHABLE from `origin/main`, not merely resolvable locally; never assign the
author. **At `--open` and not `--discharge`**, because at discharge the
information is useless — the push has landed and the author is the only person
present. Owner: cc.

### 6. Not touched, by instruction

Michael holds b4 Q1–Q3. The migration SQL doc was not run and not edited.
`tests/`, `tools/`, `sql/` and all of `docs/` except the routing doc, the
handoff and `docs/hank-evidence/` were not edited.

---

## What b6 found that nobody asked for

1. **The audit checkpoint covered 3 of 16 audit logs** and had done since the
   migration ran. A checkpoint is what makes an audit log *tamper-evident*, so
   thirteen logs — including credential grants for a dental practice, an
   assisted-living facility and an ORC 2915 gaming post — had **no
   tamper-evidence at all** and a back-dated row in any of them was
   undetectable. The daily job kept passing. Nothing announced it: the
   migration is SQL, the list was a JavaScript constant, no check compares
   them.

2. **My own comment disabled a checker** — the third instance in this batch
   family of one shape. `tools/audit_event_type_check.py` exited 2 COULD NOT
   RUN because a comment in `api/audit-checkpoint.js` *mentioned* the pin-setup
   helper by name.

3. **A new guard immediately made an existing test arm unreachable, and the arm
   said so.** The server-side SPEC 1c refusal made
   `api/sd-data-cross-tenant-dispatchers.test.js`'s `sf_officers` write arm
   report `UNREACHED: … 409 LAST_PROVISIONER`. The arm was right and the
   fixture was stale; re-pointed, not silenced — b5's GRD tripwire is the
   precedent for what leaving it red costs.

4. **`trustee.audit` is an office a post can assign and nobody can sign in
   as** (item 2 above).

---

## Live state

**The site is UP.** `/` answers 200 with 2,755,287 bytes; `/api/sd-data`
answers 405 to a GET, which is correct for a POST-only endpoint.

**THE GATES ARE NOW PROVEN LIVE IN BOTH DIRECTIONS** — the half b5 could not
drive. With a real SAIRNscape owner session (`SCP-DEMO-2026` /
`sairn-demo-owner`), all six gated resources answered **200 with rows** while
the same key bare answered **403**, the two ungated controls answered 200 both
ways, and an id-less write **with** the session answered **400 from the
handler** — which is what proves the session passed the gate rather than the
gate being absent. `docs/hank-evidence/b6_live_session_control_probe.py` and
`.out`.

**SAIRNfreedom could not be driven and that is recorded rather than skipped
silently:** `docs/2026-09-03-demo-credentials.md` has a row for every app with
a demo employee credential and **has no SAIRNfreedom row**, so there is no
`SF-PINNACLE-2026` PIN in this repo. The five tables locked this batch and the
36×10 matrix are **source-verified only**.

**`/api/audit-checkpoint` answers 401 to an unauthenticated GET**, so the route
exists and is deployed. Whether the scheduled job has beaten since the restart
**could not be told from this clone**: there is no `CRON_SECRET` here, so
`tools/cron_liveness_check.py` exits 3 without calling the watchdog. The cron is
`30 3 * * *` and the watchdog runs at `:15`, so a 3:15 DEAD report describes the
state *before* the 3:30 run. The 503 path does beat (`outcome: 'failed'`), so a
daily refusal would read as ALIVE-but-failing rather than DEAD — which points at
either the pause having suppressed the run entirely, or
`sql/audit_checkpoint_schema.sql` never having been run. See open item 1.

---

## Transcript

`C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-hank\08b87893-ec2b-4bd5-99bb-70843fa2df93\`

Scratchpad under `scratchpad/` in the same directory. It is `%TEMP%` and is
cleared without warning, so anything a committed document cites was copied into
`docs/hank-evidence/` — both b6 probe artefacts are there.
