# Hank handoff — 2026-10-14, batch b10

Written **before** the report, at a point where nothing is half-finished: all
six items are committed and pushed, `HEAD == origin/main` with no divergence,
every suite green at the published HEAD, and the post-push live probe run
against production with **`fail=0 couldnot=0`**.

**Naming note.** The brief asked for `SAIRN-handoff-hank-b10.md`. It is in
`docs/` because that is where every handoff in this repo lives and because
CLAUDE.md's rule is that a handoff lives only in a real clone — never written
to `C:\Users\marsh\` directly. The filename is the one asked for.

---

## Push state — verified, not asserted

    git rev-list --left-right --count HEAD...origin/main   ->   0   0

No `--force` at any point. `SAIRN_SEED_GATE=off` was **never** used — every
gate refusal was satisfied, not overridden. **Re-verify with
`git log --oneline origin/main`**: five sessions push to this branch and these
shas are current only as of this sentence.

| sha | item |
|---|---|
| `49780043` | **item 2** — `office_manager` in all four SAIRNcare places |
| `9731d880` | **item 3** — the `sen_visits` `clock_flags` merge |
| `85206564` | **item 4** — the shared overlap helper, and the `rf_settings` tier |
| `fdd06d06` | **item 5** — the SAIRNlegacy role matrix, 36 resources |
| `ad128e5c` | **item 1** — `sql/2026-10-14-michael-run-order.sql` |
| `1b7f9bfa` | the adversarial review's seven findings |
| `2d04cc07` | the prototype leak the push gate caught |
| `92612e5b` | the post-push live probe and its output |

Plus register feeds, two sha re-seats, two scrutiny-ledger rows, the Tier A
obligation, the regenerated documents, and **three merge commits** — see *The
push* below.

---

## Item by item

### 1. The Michael run order — DONE

`sql/2026-10-14-michael-run-order.sql`. **SIX numbered blocks**, each
independently runnable, each idempotent, each with its verification query and
**the answer it must give**. No transaction spans two blocks.

The brief named five. **The sixth is the SAIRNlegacy role CHECK and it is
flagged in the file as an addition rather than folded in silently** — without
it the 36-resource gate that landed in this same batch cannot be populated at
all, because nobody can be given a role other than `owner`/`director`/`staff`.

**It is an EXTRACTION, not a second authoring.** Every statement was pulled
verbatim from its source by a scratch script, not retyped: a transcription
error in a credential insert or a CHECK list is invisible in review and
presents as a 23514 or a 401 with correct-looking SQL. The source SHA256s are
in the header, and `api/sql-run-order-agreement.test.js` (16 arms) re-reads
every source and fails if a block is no longer a verbatim substring of it.
Containment rather than a hash pin, deliberately — a hash goes red when
somebody fixes a comment typo three hundred lines away, and a check that cries
wolf gets deleted.

**Two of the six blocks did not exist before this batch** and were written into
their own schema files first, so the repo stays the source of truth: the
`office_manager` widening in `sql/sairncare_employee_auth_schema.sql` and the
five-role widening in `sql/sairnlegacy_employee_auth_schema.sql`. Both follow
the drop/add pattern `sql/sairnlaw_audit_log_schema.sql` has carried since
2026-10-13, and **both are wrapped in `begin;`/`commit;`** — between the DROP
and the ADD the table has **no role check at all**, and a paste that applies
partway leaves it that way while the editor reports success.

**Ablated twice.** Breaking an end anchor gives `UNPROVEN`, exit 3. Changing a
constraint name mid-block gives `FAIL`, exit 1, naming the line that diverged
and what each side holds. The second ablation **found a real weakness and it is
fixed**: section C was searching the whole file, so `'office_manager'` matched
block 5's prose and the arm reported the statement present on a broken block.

### 2. `office_manager` in SAIRNcare — DONE, suite exit 0

Four places: `ROLES_BY_APP.sairncare`, `api/alf-auth.js`, and both SQL role
CHECKs. `tests/sairncare_office_manager_role.test.js` **10 passed, 0 failed,
0 unproven, exit 0** — from 5 failed.

**The authority is exactly one thing and it is declared as its own named set.**
Michael's decision was "an office manager may grant billing access to a MAR",
so `ALF_MAR_GRANT_ROLES` is a separate constant rather than an entry in
`PROVISIONING_ROLES` or `MANAGEMENT_ROLES`. Both omissions are deliberate:
credential creation stays owner-only, and the roster's full-resident view is
unchanged.

**DECLARED, NOT ENFORCED, and said out loud rather than implied.** No handler
reads that constant yet — the `mar_access_grant` action, `alf_mar_access_grants`
and the expiry evaluation are **not in this batch**.
`tests/mar_billing_grant.test.js` is the failing-first suite that specifies
them; it still exits 1 with 16 failed arms, **including B1, which looks for
the constant in `api/sd-data.js`** (where the action will live) and not in
`api/alf-auth.js` where it currently sits.

SAIRNcare gates every resource in `api/sd-data.js` by explicit allowlist, so an
`office_manager` session is **refused 403 everywhere today**. Fail-closed is why
the name was safe to add before the action exists.

### 3. The `clock_flags` merge — DONE, suite exit 0

`api/sd-data.js` assigned `visitData.clock_flags = clockCheck.flags`, and a
visit's two halves arrive as **two separate writes**. `checkClockEvent` only
reports on the clock fields present in THIS payload, so the clock-out's write
**replaced** the clock-in's flags and a `LATE_REPLAY` on the way in vanished.

**The superseded set is taken from the PAYLOAD, not from the new flags, and
that is the whole correctness of it.** A field this payload re-reported has
been re-checked, so its stale flag must go **even if the re-check produced
none** — otherwise a corrected clock-in keeps a LATE_REPLAY forever. A field
the payload did not mention was not checked, so its flag is kept.

The key stays **absent** when there is nothing to say;
`api/sd-data-sen-evv-clock.test.js:200` asserts that on a clean write.
`CLOCK_FIELDS` hoisted out of `api/_lib/sen-evv-clock.js` and exported rather
than re-listed. `tests/sd_data_clock_flags_merge.test.js` **8 passed, exit 0**,
from 2 failed.

### 4. One overlap helper for two resources — DONE, 36 arms

`api/_lib/leg-overlap.js`. Both `leg_bookings` and `leg_clergybookings` now go
through it rather than a third copy of the block, **because the one thing a
copy would have got wrong is the status literal**: `leg_bookings` exempts
`'Cancelled'`, `leg_clergybookings` skips `'Completed'`
(`sairnlegacy.html:4839`), and **there is no Cancelled status on the clergy
resource at all**. A byte-identical propagation would have refused clergy
bookings against services that had already happened.

So `exemptStatus` is a **required parameter with no default** and `check()`
throws without one. `api/sd-data-leg-overlap.test.js` is written as **pairs**
over the two specs — two separate suites, each correct about its own resource,
would both pass while the clergy resource carried the wrong word. **Arm D3 is
the one that catches the copy-paste** and D4 reads both client literals out of
the HTML at runtime instead of hardcoding them.

**Ablated:** against the pre-fix handler, 27 passed / **6 FAILED**, all six on
`leg_clergybookings`.

**`rf_settings` is tiered**, which b9's handoff named as item 6 and
UNVERIFIED. Verified: it is the identical open-read shape `sen_settings` had.
The tier is **narrower on purpose** — the whole `damage_threshold` value stays
public *including* `source`, because the branch comment justifies the open read
precisely on the number being unexplainable without it. What a non-management
reader loses is `updated_by`/`updated_at` and any undecided key.

### 5. The SAIRNlegacy role matrix — DONE, 32 arms

**Measured before it was built:** three roles, and `grep -nE
"LEG_[A-Z_]*ROLES" api/sd-data.js` returned **nothing**. A `staff` token read
and wrote all 36 `leg_` resources exactly as an owner did, including
`leg_deathrecords`, `leg_cremations`, `leg_custodylog` and `leg_preneed`. The
2026-09-21 session gate closed "no session" and left "any session" open.

`api/_lib/leg-roles.js`: one table, 36 rows, one `decide()`, consulted ONCE
before the read/write dispatch. Bands verified 9 REGULATED / 15 MONEY / 12
OPERATIONS against the handler's own `LEG_RESOURCES` dict **read out of the
source**, not a hand-written list.

**`staff` stays, deprecated, mapped to the narrowest band.** Promoting it to
`arranger` would have granted 15 money resources to everyone who had a login
yesterday. It is removed from the provisioning picker so no new one can be
made, and it stays in the CHECK so every existing row remains valid.

Two rules that cannot be expressed as role grants:

* **`leg_custodylog` is append-only for every role including the owner.**
  Proven live in both directions (below).
* **`leg_aftercare` gets a deterministic id** from `(case_id, checkin_type)`,
  on both halves. b9's survey finding 5: two unsynced devices each create the
  three standard check-ins and a grieving family gets duplicate grief-support
  follow-ups. A conflict check is the wrong tool when the collision can be made
  impossible by the key.

**L8 came back STRONGER than the spec predicted and is recorded as what
happens rather than reworded to match:** a role outside the vocabulary cannot
be *signed* into a token at all, so there is nothing to present.

### 6. Push — DONE, after three refusals and three merges

1. **register feed gate** — three records written (below).
2. **generated-document gate** — `MASTER-PLAN.md` and `traceability-matrix.md`
   regenerated with their own generators (PR §2.5).
3. **Tier A review gate** — 21 resources. Obligation opened, assigned to
   `fourth`, naming the four things to review hardest.
4. **`tests/role_maps_have_no_prototype.js`** — a **real defect in this
   batch's own new code**: `RF_SETTING_PUBLIC_KEYS` was a plain object
   literal, so `['constructor']` was truthy and a stored setting named
   `constructor` would have been disclosed to every foreman by exactly the
   mechanism the tier was added to close. The write path accepts any key, so
   that row is creatable. Fixed with `roleSet()`; the suite's fixture gained a
   `constructor` row and arm B6. **The suite I had just written would have
   stayed green on the broken code** — the push gate caught it, which is worth
   the extra arm.
5. **Three ref-lock / fetch-first rejections.** The gate takes minutes and
   other sessions push during it. The first retry was a `pull --rebase`, which
   **moved every register record's sha and needed a re-seat**; after that I
   switched to `pull --no-rebase`, which preserves them. b9's handoff says the
   same thing from the other direction and it is the right default here.

---

## Live verification — PR §3.2, `fail=0 couldnot=0`

`docs/hank-evidence/b10_live_gate_probe.py`, output in `.out`.

| | result |
|---|---|
| `leg_clergybookings` write, no window | **400 `CLERGY_BOOKING_WINDOW_REQUIRED`** |
| `leg_bookings` write, no window | **400 `BOOKING_WINDOW_REQUIRED`** (regression control) |
| `leg_custodylog` APPEND | **200** |
| `leg_custodylog` EDIT, same id | **409 `APPEND_ONLY`** |
| `leg_deathrecords` read, owner | **200** (over-refusal control) |
| `rf_settings` read, management | **200 `tiered=false`** |

`CLERGY_BOOKING_WINDOW_REQUIRED` is a code that did not exist before this
batch, so receiving it is proof the helper is deployed and reached.
`BOOKING_WINDOW_REQUIRED` is unchanged code and is therefore the regression
control on the refactor.

**THE PROBE WRITES ONE ROW.** `guard=yes
residue=docs/live-residue/2026-10-14-hank-b10-live-gate-probe.json` — one
`leg_custodylog` row, id `ZZ-B10-APPEND-PROBE`, on the demo licence
`LEG-PINNACLE-2026`, with the table, id column, id and
select/blast-radius/delete/confirm SQL enumerated, licence hash derived rather
than pasted. **`service_role` has no DELETE on that table and the handler now
refuses every edit, so only a human in the SQL editor can remove it.** That is
the append-only rule working as designed and the price of proving it live.

It had to write: one half of append-only is a refusal and the other is not, and
a probe that sent only the refusal could not tell *"edits refused, appends
work"* from *"the log is read-only and nothing can be recorded"* — the second
being the worse bug.

**The probe prints what it did NOT drive**, so an absence cannot read as a
pass: every role-matrix refusal arm, the `rf_settings` tiered half, the
`clock_flags` merge, and `office_manager` end to end. The first and last are
the same fact as open item 1 below.

---

## Open, with the exact next step

1. **THE CODE HALF OF BOTH ROLE WIDENINGS IS LIVE AND THE DATABASE HALF IS
   NOT.** This is the largest open item and it is an **ordering** risk, not a
   hidden one. `api/_lib/auth.js` mints the new SAIRNcare and SAIRNlegacy roles
   the moment Vercel deploys; the matching Postgres CHECKs only widen when
   somebody runs **run-order blocks 5 and 6**. Until then every new-role INSERT
   is refused 23514 at the last step — and **`sairnlegacy.html:1316` already
   offers the five new roles in the owner's provisioning picker**, so the
   failing path is reachable from the UI today. Guardian check 29 is
   **COULD NOT RUN**, not passed. **Next step: Michael runs
   `sql/2026-10-14-michael-run-order.sql` blocks 5 and 6**, reads each verify,
   and only then is the matrix usable.

2. **`sql/2026-10-14-michael-run-order.sql` HAS NOT BEEN RUN — none of the six
   blocks.** Block 1 carries forward b9's open item verbatim: until it runs
   `api/ai-notice.js` answers 503 and no employee sees the notice. **Next step:
   Michael runs them one at a time, reading each verify's answer against the
   expected result printed beside it.** A clean Supabase run is not evidence.

3. **NOTHING INVOKES THE FOUR NEW SUITES.** `api/sd-data-leg-role-matrix.test.js`,
   `api/sd-data-leg-overlap.test.js`, `api/sd-data-rf-settings-tier.test.js` and
   `api/sql-run-order-agreement.test.js` are referenced by **no file under
   `tools/`**. The critical-severity fix in this batch has 32 green arms that
   nothing will ever re-run. **`tools/` is cc's**, so this is routed, not done.
   **Next step: cc adds the four to whatever drives suites at the gate.**

4. **THE FIVE SAIRNlegacy ROLE NAMES BELOW `director` ARE `[CONFIRM]` AND STILL
   ARE.** `arranger`, `prep`, `office`, `apprentice`, `livery` are fourth's
   spec's names for job titles a funeral home may call something else. **`prep`
   in particular may need its own licensed tier** the way SAIRNvet's
   `PRESCRIBER_ROLES` does, because embalmer is a separate state licence in
   most states. **Next step: Michael or a practitioner confirms or renames**,
   before any real practice is provisioned.

5. **TWO SPEC RULES ARE NOT IMPLEMENTED AND NEITHER IS A BUG.**
   `leg_preneed`'s owner-only **deletion** rule — this handler has **no delete
   verb**, so there is nothing to gate; and whether a cremation authorisation
   legally needs a **second named person** — a state-law question this code
   does not answer. SAIRNvet's `api/sv-witness.js` is the pattern if the answer
   is yes.

6. **AN OBSERVATION FOR A HUMAN, NOT A CODE FAULT.** `livery` is refused on
   both `leg_dispatches` and `leg_custodylog`. If the removal driver IS the
   custody-taker, the person who physically collects a body can neither see
   their own dispatch nor append to the chain of custody. Correct if livery is
   an external contractor; a functional hole if not. **Next step: the same
   practitioner question as item 4.**

7. **`sairncare.html` STILL OFFERS SIX ROLES.** `:651`, `:1018` (the two
   Position/Role selects) and `:1964` (the label map). `office_manager` cannot
   be provisioned from the SAIRNcare UI. **Deliberately out of this batch** —
   the brief named four places and none of them is the HTML, and the role has
   no authority to exercise yet. **Next step: add it when the MAR grant action
   is built, in the same change.**

8. **THE MAR GRANT ACTION IS NOT BUILT.** `tests/mar_billing_grant.test.js`
   exits 1 with 16 failed arms specifying it: the action, the
   `alf_mar_access_grants` table, `ALF_MAR_GRANT_MAX_HOURS`, the expiry
   evaluation at read time, and three audit event types **that are not in the
   CHECK constraint** and would be rejected by the table. **Next step: that
   suite is the spec; B1 expects the grantor constant in `api/sd-data.js`.**

9. **FOUR OF b9's FIVE SURVEY FINDINGS ARE STILL OPEN.** `leg_aftercare`
   closed in this batch. `leg_monuments`, `leg_deathrecords`, `leg_invoices`
   and `leg_cases` each need a *different* fix and
   `docs/2026-10-14-hank-b9-sairnlegacy-client-authority-survey.md` says which.
   `leg_invoices`' is a product decision about where pricing authority lives,
   not a bug fix.

10. **THE REGISTER'S SIX DUPLICATE SUMMARIES ARE STILL THERE**, four with no
    `superseded_by`. Unchanged from b9 — none is this batch's. **Next step: the
    register's owner picks a survivor per pair and runs `--supersede <stale>
    --by <survivor>`.**

11. **THE SEAM CHECK'S 19 COULD-NOT-TELLS ARE UNCHANGED** — one seam
    (`roleSet`) across 19 callers, exactly b9's figure. Not a regression and
    not progress.

12. **SIX FILES IN THIS BATCH HAVE NO FMEA DRAFT** and the loop named them:
    `api/_lib/sen-evv-clock.js`, `api/_lib/leg-overlap.js`,
    `api/_lib/leg-roles.js`, `api/_lib/auth.js`,
    `sql/sairnlegacy_employee_auth_schema.sql`, and the new suites.
    `tools/fmea_draft.py` is cc's. **Next step: `python tools/fmea_draft.py
    <file> --save` for each, by whoever owns `tools/`.**

13. **`tests/sd_data_clock_flags_merge.test.js`'s FOOTER IS NOW STALE.** It
    still prints *"EXPECTED RED until the api/ owner merges instead of
    assigning … FIX ROUTED TO hank"* while exiting 0. `tests/` is cody's.
    **Next step: cody updates the footer and the `docs/known-red-suites.json`
    row for both that suite and
    `tests/sairncare_office_manager_role.test.js`, which is also green now.**

---

## Register

Three records, each with four contributing factors and an explicit
recurrence-open:

| sha | app | severity | method | rule |
|---|---|---|---|---|
| `9731d880` | sairnsenior | high | code-review | 1.11 |
| `85206564` | sairnlegacy | high | independent-review | 1.7 |
| `fdd06d06` | sairnlegacy | **critical** | independent-review | 1.7 |

`python tools/defect_register.py --check`: **OK, 564 records**, every commit
resolves and every field is in vocabulary.

**The FMEA loop returned PREDICTED for all three** on `api/sd-data.js`, and
**MISSED for `sairnlegacy.html`** on the third. Both halves are recorded;
quoting only the PREDICTED would be the flattering number.

**The shas were re-seated twice**, because two `pull --rebase` runs rewrote
them. A record pointing at a sha that no longer exists is a citation that
resolves to nothing.

---

## The adversarial review, and what it found in my own work

A full `sairn-guardian-v2` pass was run **over this batch's diff before the
push**, read-only, hostile. It is recorded because the findings matter more
than the fixes:

* **A real defect introduced by my own refactor.** `leg-overlap.js` returned
  `{ upstream: held }` with no status and the call site branched on its
  truthiness — so a non-ok reply with a **falsy** body fell through to
  `res.status(undefined)`, a hard 500 where the inline code it replaced gave a
  clean 502. No arm covered it. Fixed, and arm E4 now sends `rows: null`.
* **Four line citations had drifted by exactly the number of lines the same
  commit inserted** — written before the insertion, never re-derived. PR §1.3.
* **A comment named a test file that has never existed.**
* **A number that did not hold**: "six of the seven role names" naming five, of
  eight.
* **`rf_settings` shipped with zero arms** — a response-shape change on a live
  app. Now 12.
* **Dormant code**: the `why` field on all 36 rows had no consumer. Arm A6 is
  now the consumer, and **it failed on first run** — `leg_plots` said
  `"plots"`, a noun restating the resource name rather than a reason. 21 values
  rewritten.

The count of checks was re-derived from the skill rather than quoted: the
heading says 31 and there are **32 numbered entries spanning 1–31**, because
16 appears twice and 23 is retired.

---

## Claims held

**`sairn-api-sql`, claimed at the start of this batch, still held as this is
written.** Released as the last action, after the final push.

**The `sairnscape` claim the brief asked me to release last was already
released**, by b9, in commit `a6bf4dad` — `chore(claims): hank releases
sairnscape`. `sairn_claim.py list` shows one active hank claim, this batch's.
Stated rather than silently skipped.

**Conflicts declared and NOT overridden:** cody's `tests/` files were **read,
never edited** — including the two failing-first suites this batch turns green,
whose footers are now stale and are routed in open item 13. No `tools/` file
was edited by this batch at all (cc's). No `docs/` file of fourth's was edited.
No auditor clone was entered.

**Three deviations from the claim's FILES list, stated rather than hidden.**
The claim declared `api/` and `sql/` plus my own root artifacts:

* **`sairnlegacy.html`** was edited — the deterministic `legAftercareId`, the
  provisioning picker, and a corrected comment. The aftercare fix is not real
  without the client half, and the picker is the only way to perform the
  migration the role matrix requires.
* **`docs/defect-density-register.json`** — three feeds and two re-seats. The
  push gate requires the feed.
* **`api/_lib/sen-evv-clock.js`**, `api/sd-data-rf-settings-tier.test.js` and
  the other new `api/` files were not named individually in the list, though
  they are inside the declared `api/` scope.

---

## Hooks and settings

**No hook was restored or added, and `.claude/settings.json` was never
committed by this session.** It was stashed at the start of the batch
(`git stash push -m "b10-settings-park"`) because a rebase refuses outright
with unstaged changes, and **it is still parked**. It is `stash@{0}` as this is
written — **check the message before popping**, because `stash@{1}` is an older
entry from a previous batch (*"my 3 register records, re-addable from
scratchpad/reg_add.py"*) and a bare `git stash pop` takes the top of the stack,
not the one you meant:

    git stash list                       # confirm the b10-settings-park line
    git stash pop stash@{0}              # only after reading it

`.claude/settings.json.bak` and `.claude/settings.json.hooks.bak` are untracked
and were left alone.

---

## Transcript

    C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-hank\a5dbf223-4471-4755-8b4b-46ec67d14478\

Scratch artefacts there, not committed: `assemble_run_order.py` (the extractor
that builds the run order from its sources), `fix_cites.py`, `fix_why.py`,
`abl.txt`, `suites.log`, `suites2.log`, `suites3.log`, and the register payload
files `f1.json`, `f2.json`, `f3.json`, `sum2.txt`, `sum3.txt`, `rec2.txt`,
`rec3.txt`, `rn2.txt`, `rn3.txt`.

**`assemble_run_order.py` is the one worth keeping.** It is not under `tools/`
because `tools/` is cc's, and it is not committed because an uncommitted
generator is honest about being a one-off — but if the run order ever needs
re-assembling after a source moves, that file is how, and
`api/sql-run-order-agreement.test.js` is what will tell you it is needed.

**`b9-save-404dae85` was deleted at the start of this batch**, as instructed,
after confirming b9 had landed.
