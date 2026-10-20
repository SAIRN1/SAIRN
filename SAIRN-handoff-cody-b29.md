# Handoff — cody, batch b29, 2026-10-20

**Five instructed items. Four done as instructed, one done differently and §4.4
says exactly why.** Written at a point where nothing is half-finished: pushed,
verified by reading the remote, every suite green.

---

## 1. THE FIVE ITEMS, PLAINLY

| item | state | what that means |
|---|---|---|
| **1. defect 1606 — the raw `detail`** | **DONE — 11 sites, 3 shapes, 11 arms** | The brief said nine. **It is eleven**, and the two extra ride on an Error property so a grep cannot see them. **Shape 2 could return PHI** |
| **2. the six oversized caps** | **DONE — and three of the six were never this gate's business** | b28 over-counted by mapping constraint prefixes to TABLE names. `rf_invoices` is **UNCAPPED**, not under-capped. `sd_locations` lowered to 16,384 |
| **3. `rt_stops.license_hash`** | **DONE — 7 arms, no SQL run** | It was already safe and safe for a **weaker reason**. Now derived from the route row, and a disagreement is **refused**, not reconciled |
| **4. the paralegal** | **DONE — PREPARE-ONLY, on a SECOND set** | The literal one-line reading would have restored exactly what b20 withdrew. b19 R2c/A1 re-aimed and **38/0** (was 32/2) |
| **5. F2/F3 + b22 D1** | **PROMOTION DONE — 21 arms. THE D1 DELETION IS NOT DONE** | F2's widening is reachable for the first time since b18. **D1 is the one instruction b29 did not follow — §4.4** |
| **6. push, no force** | **DONE — see §2** | Read back off the remote, not inferred from the push's exit |

---

## 2. Committed and pushed state

| | |
|---|---|
| commits | **FIVE, and one is the work.** `bc5ca0d18 b29(cody): the database's error message is not the client's, three caps that were never this gate's business, and a policy nothing passed the arguments to`. The other four are what the gates asked for: a derived-doc regeneration, the S1 window fix, the defect record, and the register's own write-back |
| pushed | **LANDED AND VERIFIED BY READING THE REMOTE.** **Tip `9325e694b184`, `0 ahead / 0 behind`.** `bc5ca0d18` proved an ANCESTOR with `git merge-base --is-ancestor`, and eleven files read back off the remote tree. **PUSHED WITHOUT `--force`** |
| claim | `platform`, taken **BEFORE any work** with a FILES list. Released at the close of the batch |
| overrides | **NONE.** No `SAIRN_SKIP`, no `SAIRN_GATE_EXEMPT`, no `SAIRN_SEED_GATE`, no call to `tools/gate_skip.py` |
| SQL | **ONE FILE WRITTEN, NOTHING RUN.** `sql/sairnlegacy_settings_livery_grants.sql` — one column, for Michael. §4.2 |
| live writes | **NONE.** One read-only live measurement (`sd_locations`), §4.6 |
| boundaries | **`tools/` NOT touched** (cc's) — several RUN. **`.claude/skills/` and `CLAUDE.md` NOT touched** — the handoff-naming correction Michael decided is **REPORTED for cc** with pasteable text. **No `.html`**, **no `docs/CRITICALITY-TIERS.md`** (fourth's). `api/_lib/law-roles.js` is hank's app and is in **no active claim** — hank's own b26 claim declares `NOT-api-ANYTHING-codys` |
| path override | **REPLACED, not extended.** Three of b28's six paths dropped, `docs/b27-logs/` dropped. **It took a real merge conflict** — §7 |

---

## 3. The five items, and what each turned out to be about

### 3.1 Item 1 — a database error message is not the client's

Eleven sites, three shapes, **measured and reported rather than quoted**: the
brief said nine, and a grep for `detail: <body-variable>` finds exactly nine.
The two in `api/audit-checkpoint.js` assign the body to an Error property first
(`e.detail = body`) and echo it a function later.

A PostgREST error names the **table**, the **constraint**, the **column** and
frequently the **offending value** — an internal schema map plus a slice of
customer data, handed to any holder of a licence key. `api/sd-data.js`'s own
`upstream()` helper has had this right since it was written: log the body,
answer *"Data store error — try again"*. **Eleven sites bypassed it.**

**SHAPE 2 IS THE SHARPEST AND IT IS NOT PostgREST.**
`api/sc-eligibility.js:309` is the 270/271 eligibility check, whose **request**
carries subscriber first name, last name, member id and date of birth — and a
payer's rejection routinely echoes the subscriber block it could not match. So
that `detail` could hand **PHI** back inside an error envelope, in an app whose
subject is medical coding. The sibling site defended the behaviour in a comment:
*"Surface Stedi's real message. Never substitute a generic 'no payers found' for
what was actually an auth or quota error."* **The second sentence is right and
the first does not follow from it** — distinguishing auth from quota needs the
status and the code, both of which are still there and neither of which was ever
the `detail`.

**Every body is still logged.** Deleting it would make the next 400
undiagnosable, which is a different defect wearing the shape of a fix. Each arm
plants a marker in the upstream body and asserts it appears **nowhere** in the
serialised response **and** does appear in the captured `console.error`.

### 3.2 Item 2 — three of b28's six were never this gate's business

b28 pinned six uncovered oversized tables. **Re-derived:**

| table | DB | governed by | verdict |
|---|---|---|---|
| `rf_claim_agreements` | 1,572,864 | this gate | **CAPPED in b29** |
| `rf_proposals` | 1,572,864 | this gate | **CAPPED in b29** |
| `rf_photos` | 1,572,864 | this gate | **CAPPED in b29** |
| `rf_invoices` | 262,144 | **custom verbs only** | **UNCAPPED, not under-capped. ROUTED** |
| `sd_progress_photos` | 1,572,864 | `api/sd-sub-data.js` | already 1,572,864 — never a defect |
| `sd_quote_request_photos` | 1,572,864 | `api/stonedesk-public.js` | already sized FROM that cap, and says so |

**b28's error was mapping each constraint prefix to a TABLE name and assuming
the table was the resource.** `tools/gate1_verify.py`'s header already warned:
*"THE RESOURCE IS NOT THE TABLE and that is the whole trap this map exists
for."* **C7 is now a three-state pin** — covered, uncovered,
not-this-gate's-business — and **C7b** refuses to let an exempted table quietly
stop being oversized.

**`rf_invoices` IS THE SHAPE THAT MATTERS BEYOND ITSELF.** The gate reads
`if (action === 'write')`. Any resource writing through a declared verb —
`issue`, `add_payment`, `upsert`, `optimize`, `route` — never reaches it.
**ROUTED, not fixed**: closing it would start refusing payloads that work today,
a 200-stop `rt_routes` upsert first among them. §4.1.

**`sd_locations` GOES DOWN, NOT UP.** Its own constraint is 16,384 and the gate
permitted **four times** it, so a 40KB yard record was accepted here and refused
by Postgres — the slabs failure in the direction that paragraph did not consider.
**The key is `locations`, not `sd_locations`:** the gate is keyed on the
dispatched resource and an entry under the table name would be inert. §4.6 is
the measurement.

### 3.3 Item 3 — already safe, and safe for a weaker reason

The `rt_stops` insert has always written an **explicit field list**, so a client
`license_hash` was never copied — there is no spread for it to ride in on. But
the value came from `licHash`, the **licence key**, while cc's composite FK binds
a stop to `(route_id, license_hash)` **of the route**. The same number on every
well-formed request; **not the same fact**, and the gap between "the same today"
and "the same by construction" is where a tenancy bug lives.

**AND A DISAGREEMENT IS REFUSED, NOT RECONCILED** — 409
`ROUTE_TENANCY_MISMATCH`, with no stop insert **and no stop delete**.
`routeHash || licHash` would have been one character shorter and would have
turned a tenancy inconsistency into a write under the caller's own licence. Arm
**S2** goes red on exactly that edit, which no behaviour arm can see because the
condition is unreachable through a correct PostgREST.

**NO SQL RUN.** cc owns `sql/rt_stops_license_hash_composite_fk.sql`.

### 3.4 Item 4 — the work is delegable, the duty is not

Michael: *"goes back on the IOLTA reconcile list as PREPARE-ONLY."*

**The literal reading — `paralegal: true` on `LAW_RECONCILE_ROLES` — would have
delivered the exact state b20 withdrew the grant to avoid**: a non-lawyer
producing a finished reconciliation that nothing records a lawyer as having
reviewed, on the one figure a bar association audits. Rule 1.15 puts the duty on
the lawyer and makes it non-delegable; Rule 5.3 makes the **work** delegable
under supervision. **Two sentences, two sets.**

**THE HALF THAT MAKES IT SAFE IS THE STAMP, NOT THE PERMISSION.** Every
reconcile reply now carries `attested: false`, `prepared_by_role`,
`prepare_only` and `attestation_required_from` — **including an owner's own
run**, because running the comparison and attesting to it are two acts even when
one person does both. `attested: recMayRun` is the natural-looking one-liner and
is the lie the stamp exists to prevent; arm **P4** is that case.

### 3.5 Item 5 — a policy nothing passed the arguments to

`decide()`'s `grants` argument was a **literal `null`** at the call site since
b18 — not an oversight: **nothing stored it**, so F2's widening branch was
unreachable in production while every module-level arm for it stayed green.
`sql/sairnlegacy_settings_livery_grants.sql` is the column, **written for
Michael and not run**, and **the handler works before and after it**: a missing
column answers 400 undefined_column, the read is **re-issued without it**, and
the answer is a **refusal**. Arm **G5** is that case and it is the state
production is in today.

---

## 4. Open — every item, why, and the exact next step

### 4.1 → whoever owns the write-cap policy. The gate covers ONE verb

`api/sd-data.js:892` is `if (action === 'write')`. **Every resource writing
through a declared verb bypasses the payload cap entirely** — `rf_invoices`
(`issue`, `add_payment`, `reconcile_claim`, `gl_export`), `rt_routes`/`rt_stops`
(`upsert`, `reorder`, `optimize`), `alf_payer_rules` (`route`).

**NOT FIXED, and the reason is risk not effort:** closing it would start
refusing payloads that work today. **Next step:** split `EXTRA_ACTIONS` into
write-class and compute-only, measure the largest real payload per write-class
verb, then cap per `(resource, action)` rather than per resource. Arm **C7b**
keeps the declaration honest meanwhile.

### 4.2 → Michael. One SQL file, and running it grants nobody anything

`sql/sairnlegacy_settings_livery_grants.sql` — `livery_grants jsonb not null
default '{}'`. **Two separate things must then be true** before one driver reads
one booking: the home sets `direct_to_family`, **and** somebody with personnel
authority writes that employee's id into the map. Neither alone does anything.
`leg_liveryvendors` stays ungrantable under every setting and with any entry in
the map — arm **V1** drives all three settings **with an explicit grant**.

**Nothing is blocked on this.** The handler is correct and refusing today.

### 4.3 → cc. `CLAUDE.md:33` — record the practice, per Michael's decision

**83 of the 86 handoffs on disk** use `SAIRN-handoff-<session>-b<NN>.md`; the
documented `APP-YYYY-MM-DD-subject-handoff.md` describes **three**. Michael's
b29 decision: **record the practice, do not rename 83 files.** The edit is cc's
— `CLAUDE.md` is shared and b29 did not touch it. **Pasteable text is in
`docs/2026-10-20-cody-b29-notes.md` §3.3**, and
`.claude/skills/sairn-session-handoff/SKILL.md` §Naming convention needs the
same correction.

### 4.4 ~~b22 D1: DELETE it~~ — NOT DONE. THE ONE INSTRUCTION b29 DID NOT FOLLOW

**The promotion is done — 21 arms. The deletion is not.**

D1 was an **inverted** arm: it asserted that no call site passed
`grants`/`home` and said in its own text *"A FAILURE HERE IS GOOD NEWS."* It
fired when b27 wired `home`. **Hank's b24 then RE-AIMED it**, and at HEAD it
asserts the opposite — that the five-argument call site is still there — and it
is green.

**So the arm the instruction described no longer exists.** What exists is the
only regression guard on the wiring, and hank's own comment at it says why:
*"Deleting it HERE would leave nothing asserting that the wiring is still there
— the gap stopped being the risk and a REGRESSION became one."*

**"Both halves or neither" is honoured in substance**: the deletion's purpose
was to retire a stale inverted arm, and the arm is not stale. **One line
reverses this if Michael disagrees** — arm D1 of
`api/b22-funeral-f1-f2-f3-wiring.test.js`, with D2 and D3 which exist to keep it
honest. Full account: notes §3.4.

### 4.5 → cody, next batch. `docs/defect-density-register.json` has one dangling citation

    python tools/defect_register.py --check
    -> FAIL: 1 register problem(s)
       ce15ddaa6a3c -- the commit RESOLVES IN THIS CLONE BUT IS NOT AN ANCESTOR
       of origin/main or HEAD... Subject: 'b27(cody): the rt_routes primitive
       made reachable, three routed role changes, and three routings that were
       incomplete'

**It is cody's own, from b27, and it is a real finding**: b27's work commit was
rewritten by a rebase and the record still cites the pre-rebase sha, so *"in
every other clone this record names nothing."* **RED AT HEAD BEFORE b29** and
not caused by this batch. **NOT FIXED because the fix is a judgment call I did
not want to make at the end of a batch:** the subject no longer matches any
commit either, so re-seating it means deciding which of b27's five surviving
commits the record is actually about. **Next step:** `--reseat` refuses this
shape by design, so it is a hand edit of the `commit` field to
`864e6b764`/its successor after confirming by diff which one carries the
rt_routes branch.

### 4.6 `sd_locations` — the measurement, and what it could not tell

Measured live on `SD-AUDIT-2026`: the table answers **`provisioned: false`,
zero rows**. That is a could-not-tell about other licences and is recorded as
one. **The decisive argument is the constraint, not the sample:**
`octet_length(data::text) <= 16384` means Postgres has refused every row above
16,384 for as long as it has existed, so **no stored row anywhere can be above
it** and lowering the API cap cannot refuse a write that works today.

### 4.7 Still open from b28, unchanged

§4.5 of the b28 handoff (the two `unproven_arm_check` findings, cc's), §4.7
(`SAIRN-ACTIVE-WORK-cody.md` at **795KB**, 2× the ceiling — the remedy is
fourth's `-closed-N` split and it is still a decision about where the cut goes)
and §4.8 (my digest-length and wrap-up record; **both rules now exist in writing
and b29 wrapped at 67%**). **b28 §4.1, §4.3 and §4.4 are CLOSED by this batch.**

### 4.8 → Michael. Nothing is blocked on you

One SQL file is **offered**, not owed (§4.2). One decision is **open and
reversible in one line** (§4.4). One edit is **routed to cc** (§4.3).

---

## 5. Verification — every line is a command that was run

```
EXIT=0  node --check  api/sd-data.js  api/_lib/law-roles.js
                      api/sc-eligibility.js  api/audit-checkpoint.js
                      all four b29 suites

RED BEFORE, GREEN AFTER -- the methodology, per item:
  item 1   api/b29-error-detail.test.js       10 failed / 1 passed -> 11/0
  item 2   api/b28-photo-cap.test.js          10 arms red          -> 23/0
  item 3   api/b29-rt-stops-hash.test.js       3 arms red          ->  7/0
  item 4   api/b29-law-reconcile-prepare.test.js 5 arms red        ->  8/0
           api/b19-iolta-reconcile-carveout.test.js   32/2         -> 38/0
  item 5   api/b29-funeral-f2-f3.test.js       3 arms red          -> 21/0
  Each "red" figure is an ABLATION: the b29 source change stashed and the
  suite re-run, which is the same measurement the brief asked for and is
  reproducible rather than a remembered first run.

EXIT=0  node api/b22-funeral-f1-f2-f3-wiring.test.js   23, regression
EXIT=0  node api/b27-leg-settings.test.js              18, P1 RE-AIMED
EXIT=0  node api/b18-countersign-lock.test.js          59, regression
EXIT=0  node api/b23-iolta-attestation.test.js         66, regression
EXIT=0  node api/b28-role-from-token.test.js           15, regression
EXIT=0  node api/_lib/routes.test.js                   63, regression
EXIT=0  node api/sd-data-leg-role-matrix.test.js       37, regression
EXIT=0  node api/sd-data-leg-overlap.test.js           36, regression
EXIT=0  node api/sd-data-cross-tenant-dispatchers.test.js  418, regression
EXIT=0  node api/audit-checkpoint.test.js              50, regression
EXIT=0  node api/sd-data-approvals.test.js             23, regression
EXIT=0  node api/sd-data-appointments-photos.test.js    3, regression
EXIT=0  node api/_lib/dental-photo-validation.test.js  26, regression
EXIT=0  node api/b16-slice-window-check.test.js         6, the gate's own suite
EXIT=0  node tests/role_maps_have_no_prototype.js      13, the guard
EXIT=0  python tests/audit_checkpoint_probe.py         11 arms, 7 mutations
EXIT=0  python tools/md_table_check.py                 all files clean
EXIT=0  python tools/sairn_path_manifest.py --outgoing 39/39 arms, IN SCOPE
EXIT=0  python tools/live_probe_declaration_check.py
EXIT=0  zero control bytes in every file this batch wrote (measured)

RED AT HEAD, NOT CAUSED BY b29:
EXIT=1  python tools/defect_register.py --check   1 dangling b27 citation -> §4.5
```

**ONE REGRESSION WAS CAUSED AND CAUGHT BY AN EXISTING SUITE.** Removing both
`detail: err.detail` lines in `api/audit-checkpoint.js` turned its own arm *"A
WINDOW WHOSE ROW COUNT IS NOT STATED REFUSES TOO"* red — it reads
`error.detail.why`. **The arm was right and my removal was one step too far:**
`WINDOW_INCOMPLETE`'s detail is **composed** by `readWindow` (`{table, read,
why}`), not an upstream body. Same `detail: err.detail` spelling, opposite
facts. **Restored, with the distinction written at both sites**, and arm C1 now
carries a **declared allowlist of one** with its reason rather than a narrowed
pattern — because narrowing a check after it fires looks identical to moving the
goalposts, and the difference is whether the reason is written down.

---

## 6. THREE DEFECTS I INTRODUCED, AND THE CONTROL THAT CAUGHT EACH

**Recorded because the controls are the finding.**

1. **A LITERAL BACKSPACE.** `/detail: *(null|...)\b/` was authored through a
   script and `\b` reached the file as **byte 0x08** rather than a word
   boundary, so the null exclusion **silently never fired**. **C1 was green at
   the time** — the real source happens to contain no `detail: null` in a
   response. Only **C2**, which runs the same function over a fixture that
   SHOULD match, could tell. This platform has written this exact defect down
   once already: *"a regex that shipped with a literal backspace and could never
   match."*
2. **A FIXED-WIDTH SPAN, TWICE.** The sweep took twelve lines after each
   `res.status(`, which from a one-line response ran into the next statement and
   flagged an internal `auditAlf({ ... detail: detail ... })`. **C2 caught that
   too, on a fixture.** And separately the **push gate** refused a
   character-counted source window in arm S1 of the rt_stops suite —
   `api/b16-slice-window-check.test.js` — for the same reason in the same batch.
3. **MY OWN PROSE TRIPPING MY OWN SCANNERS, THREE TIMES.** `S2` asserts there is
   no `routeHash || licHash` fallback and the fix's comment **explains** why
   there is none, containing the string. The S1 window fix's comment **quoted**
   the forbidden form. Both now read comment-stripped source or avoid the
   pattern. **The answer is to blank comments, never to stop writing the reason
   down.**

---

## 7. The push — FOUR GATES REFUSED AND ALL FOUR WERE SATISFIED AT CAUSE

**NOTHING WAS OVERRIDDEN.**

1. **`derived-docs`** — three generated documents regenerated with their own
   generators.
2. **`path-scope`, through a REAL MERGE CONFLICT in the ownership manifest.**
   cody b29 **replaced** its own override list while fourth b42 **added** a new
   `fourth` list, and git produced markers across both. **Resolved by hand, by
   union of the populations and replacement within cody's own** — fourth's two
   entries and hank's six untouched, `docs/b27-logs/` dropped because b29 does
   not touch it. The file's own note predicted this collision would recur and it
   recurred the same day; a second note records it. **Never `--ours`/`--theirs`:
   a conflict in an ownership manifest must not silently drop one side's
   permission.**
3. **`api/b16-slice-window-check.test.js` S1** — a fixed-width source window in
   a new api/ test. Fixed at cause; the fix's first spelling re-tripped it by
   quoting the forbidden form in a comment. §6.
4. **`register-feed`** — the push closed a defect and no record cited it.
   **Record WRITTEN**, not skipped: `PLATFORM / product / high / code-review`,
   three contributing factors with kinds and action statuses, `--rule
   not-citable` with a note arguing which rule *should* exist,
   `--injection-unknown` with the reason (eleven sites, three files, three
   authors, no single injecting commit) and a `recurrence_open` naming both
   halves that are **not** closed. The arm-window commit carries a
   `no-defect-record:` note instead, because a test-harness window is not
   shipped behaviour.
5. **`duplicate-subject`** — my push-retry loop names commits by ATTEMPT NUMBER,
   so two unrelated changesets wore one message and the gate refused them out
   loud. **Reworded to describe the changeset**, and the loop now names the
   files. The gate's own text is why it matters: on 2026-09-16 a commit reached
   `origin/main` wearing a `chore(register)` message while containing a real
   performance fix, so nothing asked it for a defect record.

---

## 8. Scratch, transcript and where the detail is

* **Concepts, the measured corrections, every routed finding:**
  `docs/2026-10-20-cody-b29-notes.md`
* **The SQL for Michael:** `sql/sairnlegacy_settings_livery_grants.sql`
* **The four new suites:** `api/b29-error-detail.test.js`,
  `api/b29-rt-stops-hash.test.js`, `api/b29-law-reconcile-prepare.test.js`,
  `api/b29-funeral-f2-f3.test.js`
* **Transcript:**
  `C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cody\cc73112b-c907-4081-b7af-37c09862bb32.jsonl`
  — **this window carries b28 AND b29**; b29 begins at the dispatch naming the
  five items and the 85% wrap-up trigger.
* **Wrapped at 67%**, measured with `python tools/context_verify.py
  --digest-line`, against an 85% trigger. b27 wrapped at 92% and had to revert a
  half-finished item; b28 at 38%.
