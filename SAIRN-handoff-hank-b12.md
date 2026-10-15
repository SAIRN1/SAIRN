# Hank handoff — 2026-10-14/15, batch b12

Written **before** the report, at a point where nothing is half-finished.
**Stopped on a context instruction at 70%, not on completion** — five of the six
items are done and the sixth (push) is done; what was cut is named in *Open*
below with its exact next step, including the two findings I had just started
reading and did not touch.

---

## Push state — verified, not asserted

    git fetch -q origin main
    git rev-list --left-right --count HEAD...origin/main   ->  0 0
    git rev-parse HEAD                                     ->  6446e570

`6446e570` is another session's claim commit, fast-forwarded in so this clone
matches the published trunk exactly. **b12's own last commit is `80297a3b`** and
the batch range is `9f488101..80297a3b`. No `--force` at any point. **Neither
override form was used** — not `SAIRN_SEED_GATE=off`, not the scoped
`SAIRN_GATE_EXEMPT=seed`. Four gate refusals, four satisfied, zero overridden.

| sha | what |
|---|---|
| `6e55b1d5` | **item 1** — the b11 handoff's push-state sha corrected |
| `e9d9c819` | **items 2 + 3a** — the sd_photos size fix, the 89-branch 400/404 split, the visible failure, and T17 |
| `4f69facd` | **item 3b** — the F1 census SQL, both files |
| `31406a87` | **item 4** — N1, N2, N3, N4 and the two SAIRNfreedom deletes |
| `88e0e47b` | **item 5** — the role-picker vs DB CHECK check |
| `065d1135` | three register records |
| `bf2b2474` | the two regenerated documents and the gate's ledger rows |
| `b678b175` | the Tier A obligation, 3 resources, assigned to `fourth` |
| `eeb637c3` | the live probe, its enumerated residue, and every captured red |
| `80297a3b` | the gate's ledger row for that commit |

Plus four merge commits from `pull --no-rebase`; every retry used that form so
no register record's sha moved.

---

## Item by item

### 1. The b11 sha disagreement — DONE, and only one file was wrong

`git -C` on `origin/main` showed **all three shas exist**, so this was not a
typo in one file; each was accurate at its own moment of writing. The
disagreement was real and had one wrong side:

| file | said | verdict |
|---|---|---|
| `SAIRN-handoff-hank-b11.md` | `21dd38d9` | **WRONG — corrected.** That commit *predates the handoff's own commit* (`ffb2463a`), so anybody checking it out to see "the state this handoff describes" gets a tree with no handoff in it. A standing document may not quote a HEAD earlier than itself. |
| `SAIRN-report-hank-b11.txt` | `ffb2463a` | **RIGHT — left alone.** It labels that sha as the handoff commit on its own line and states that a report cannot carry the sha of the commit that adds it. |
| `SAIRN-digest-hank-b11.txt` | `ffb2463a` | **RIGHT — left alone**, same reason. |

The handoff now names `9f488101` (b11's last commit) with the full range
`4c258b04..9f488101` and the one-line check that re-derives it. Re-uploaded to
Drive and **verified Drive-side through the API**, not only on the sync mount:
28,299 bytes, `modifiedTime` 20:50:54.

### 2. sd_photos — DONE, three parts, and the count was re-derived

Per `docs/2026-10-14-fourth-b19-sd-photos-premise.md`. Michael's decision was
option (a), client-side downscale.

**(a) THE DOWNSCALE MEASURES INSTEAD OF ASSUMING.** An 11-rung ladder from
1600px/q0.72 to 320px/q0.4; each rung is encoded and **its resulting length is
checked** against a 44,000-character budget. The budget is deliberately **not**
the cap: the same row later carries `aiAnalysis` (3–5 model sentences),
`ai_source`, the ids and JSON quoting, so ~21 KB is left for the rest. When no
rung fits the result is `null` — **not the original** — because a downscaler
that silently passes the original through is how an oversized row reaches the
server *looking* downscaled. The row records which rung won, the resulting
dimensions and the original byte length.

**(b) THE 400 MISATTRIBUTION — AND THE BRIEF'S COUNT OF 12 IS WRONG.**
Re-derived at source: **98** branches answer 503 NOT_PROVISIONED on
`(404||400)` and **89 of them read nothing at all** before deciding. All 89 now
go through one `notProvisioned()` helper with **four** answers: 404 → 503 with
the caller's message; 400 + pg class 23xxx → **400 ROW_REFUSED** naming the
64KB cap; 400 + "does not exist" → 503, because PostgREST really does answer a
missing table 400 with PGRST205 and that original reason is kept rather than
thrown away with the defect; 400 otherwise → **400 UPSTREAM_REJECTED**, which
says the reason could not be classified and explicitly does **not** say "run the
migration". The nine branches that already read the body and discriminate were
**left alone** — a Response body is readable once.

**THE FIRST DRAFT OF THAT REWRITE BROKE FIVE SITES AND THE SCRIPT DID NOT SEE
IT.** 2768, 2987, 3330, 3431 and 8449 do `const rows = await r.json()` *before*
the guard, so the helper's own `r.text()` got an empty string on a consumed
stream and classified a genuine 404 as unclassifiable — one wrong diagnosis
traded for another. Caught by **reading two rewritten sites in context** after
the mechanical pass: the script checked a property *inside* the branch and the
hazard was in what came before it. Those five now pass their body in.

**(c) THE FAILURE REACHES A HUMAN.** `sdDataFailed`'s whole body was one
`console.warn`, while this same file's `sdSyncCollection` comment already stated
the argument: *"silence would make a backup that is not happening look like one
that is."* It now toasts the first failure in a burst, names the row-too-large
case (the one a user can act on), and summarises the rest once the burst stops —
one toast per record on a 200-photo sync is its own kind of silence. Every
branch guarded, `showToast` reached through a `typeof` test.

### 3. T17 and the F1 census SQL — DONE

**T17 landed in the same commit as the size fix**, as the premise document
requires ("with or before"): until the row lands the provenance gap is latent
behind the size failure. `ai_source: 'claude:photo-qc'` on the row, `sd_photos`
added to `AI_SCANNED_TEXT` on `aiAnalysis` and **not** on `data` (redacting a
base64 payload corrupts the image), and a "Written by AI" label on **both**
success renders — the page's only AI wording was the spinner the answer
overwrites.

**CLASSIFIED NOT-HIGH-RISK, AND THE CONTENT ARGUES THE OTHER WAY**, so the
reason is recorded in full in `NOT_HIGH_RISK_AI`: the text is the same shape as
`bld_photo_analyses`, which *is* high-risk, but `sd_photos` is **not in
SD_SESSION_GATED**, so an approval gate would refuse every analysed photo 403 on
an app with no sign-in requirement. **Promoting the row is a session decision
first** — add it to `SD_SESSION_GATED`, *then* move it — and the entry says so
in that order.

**F1.** Both `sql/legacy_ciphertext_census.sql` and
`sql/sd_encryption_key_revoke_2026-09-24.sql:113` read
`sc_credentials.data->>'enc'`, which assumes a top-level key.
`api/sc-credentials.js:200-205` writes `next[service] = { enc, ... }`, so the
real path is `data->'stedi'->>'enc'`. **A wrong jsonb path returns NULL rather
than erroring**, so every count came back `legacy_rows = 0` — and *that zero is
the precondition* step 4 of the revoke file waits for before clearing
`SD_AUTH_SECRET_PREVIOUS`. The wrong path would have authorised clearing the old
key while legacy ciphertext was still in the table, and **the census is the
document that would have authorised it.** Fixed to walk `jsonb_each(data)` so a
second service is counted the day it is written, part 2 now returns **which**
service key is legacy, and a new **part 0** counts the flat and nested shapes
separately so both-zero reads as "no credential exists" rather than as the
step-4 precondition. `sairn_sql_preflight.py --live`: 0 findings on both.

### 4. The SAIRNfreedom deletes and N1–N4 — DONE

**F6 verified first, by reading both functions, and both hold.**
`sfDeleteEvent` chose its toast on `ev.sessionId` being *truthy* and never on
whether the filter removed anything, so a stale pointer made it announce "Event
and its bingo session removed" having removed nothing — affirmative false
success, worse than silence because it tells the operator a thing happened.
`sfDeleteSession` was what created those pointers: it removed the session and
never cleared `event.sessionId`, and the UI offers Remove on every session row.
Both fixed; the event delete now **counts the rows it removed** and reports
that, with three outcomes and three messages.

**N1** — the EVV write copied every payload field over the row, so a second
clock-in silently replaced a recorded one, on a path any caregiver reaches on
their own visit. Now **409 CLOCK_ALREADY_RECORDED** on a different value with
nothing written; an **identical** re-send is still accepted, because sairnsenior
queues clock events offline and replays them unchanged.

**N2** — `setup` could demote the last active Owner, reaching by **role** the end
state `set_active` has been guarded against by the **active flag** since the
lifecycle module was written. Six sibling endpoints already call
`soleRoleDemotionRefusal()`; SAIRNsenior did not. **The guard is called, not
rewritten.**

**N3** — a requirement that returned a clean `false` for a person's position
vanished from the response. Findings now carry `excluded_by_position` with
`matchAudience`'s own reason, absent when nothing was excluded. Also: a
present-but-wrong-shaped `applies_to_positions` (a string) was collapsed into
the same null as "absent", so the reader was told the rule used **prose** when
it had declared a machine-readable audience in the wrong shape — now recorded,
not coerced.

**N4** — the three comments now say *"driven by hand on 2026-09-29, NO COMMITTED
ARM"* and name the arms routed to cody. **And the shape-only hire date was
DRIVEN**, which found the reported case *and a worse one the report did not
reach*: `2024-02-30 -> '2026-02-30'` (impossible day, reported) **and
`2024-13-01 -> '2025-13-01'` (impossible month, not reported)** — the
day-decrement normalisation cannot touch a bad month at all, and `window_from`
is printed on a compliance finding a surveyor reads. Refused with
`HIRE_DATE_NOT_A_REAL_DATE`, **refused and not repaired**, because normalising
would be the code choosing which date somebody was hired on.

### 5. The role-picker vs DB CHECK check — DONE, and the finding is the UNPROVEN count

`api/role-picker-vs-check-constraint.test.js`, run over all **17** apps in
`ROLES_BY_APP` (derived, not typed):

* **6 CLEAN** — sairnbuild, sairncare, sairndesign, sairnlaw, sairnlegacy,
  sairnsenior.
* **0 FAILED** — no app currently offers a role its own CHECK refuses.
* **11 UNPROVEN**, and **that is the finding of the run, not a footnote**: no
  CHECK found in `sql/` for sairnbiz, sairngrounds, sairnscape, stonedesk; no
  role picker found in sairncode, sairndental, sairnfreedom, sairnmechanical,
  sairnroofing, sairnvet; no HTML at all for stonedesk_sub.

**The limit is printed every run.** It reads the CHECK out of `sql/` — the
repo's *intended* constraint, not production's — so it catches a picker ahead of
the schema file (**drift**) and cannot catch a schema file ahead of production
(**lag**), which is exactly the `office_manager` state today. The two dated
CHECK-widening migrations are listed by name with the one query that settles
them.

**My own first draft was PERMISSIVE and I found it by reading the output, not
the exit code** (the run already said "0 with a refused role"): it collected
every `check (role in (...))` from any file *mentioning* the table, so sairncare
reported 18 allowed roles drawn partly from sairnroofing's schema. Each
declaration is now bounded to the statement naming that app's table.

### 6. Push — DONE, `0 0`, after four refusals and four merges

register feed (three records) · the two generated documents · the Tier A
obligation (3 resources, assigned to `fourth`) · one `no-defect-record:`
sentence given with a real reason. Four `pull --no-rebase` merges; two ledger
conflicts resolved with `tools/sairn_rebase_resolve.py`, which 3-way merges by
the identity each ledger declares and stages nothing unless its validator
passes. **I verified my Tier A obligation survived that merge** rather than
trusting the tool's "0 local-only" line — it is present, `opened_at`
`2026-10-14T23:53:53Z`.

---

## Live verification — PR §3.2, `fail=0 couldnot=1`

`docs/hank-evidence/b12_live_gate_probe.py`, output in `.out`.

| | result |
|---|---|
| 404 leg of the 89-branch rewrite | **COULD NOT RUN** — five candidates tried, none reached an absent table |
| `sd_photos` read | **200 provisioned=true** (the control) |
| `sd_photos` write | **200** (the success leg survived the rewrite) |
| `sen_visits` clock write, unknown visit | **200, not 409** (N1's guard does not fire where nothing is recorded) |

**The 404 arm's first draft reported a failure that was its own**: it sent one
guessed resource the registry does not expose, and the dispatcher's 400
*"resource must be one of ..."* was read as the 404 leg breaking. That refusal
carries **no `error.code` on purpose** — the handler's comment says telling
FOREIGN_RESOURCE from UNKNOWN_RESOURCE is what a caller must not be able to do —
so it is now detected by its message, five candidates are tried, and finding no
absent table is COULD NOT RUN.

**IT WRITES ONE ROW AND THE ROW IS ENUMERATED** —
`docs/live-residue/2026-10-14-hank-b12-sd-photos-probe.json`: table, id column,
id (`ZZ-B12-SIZE-PROBE`, fixed so a re-run overwrites — confirmed, the second
run read `rows=1` not `rows=2`), licence, blast-radius select, delete, confirm.
**Unlike b10's residue this one does not need a human in the SQL editor**:
`sd_photos` has a `soft_delete` verb and `service_role` holds DELETE. The SQL is
given anyway because it does not depend on a session.

It had to write: a handler answering 503 to every `sd_photos` write would pass
every refusal arm while backing up nothing, and *the row landing* is the point
of the batch.

---

## Open, with the exact next step

1. **THE TWO FINDINGS I HAD JUST STARTED READING AND DID NOT TOUCH.** cody's
   `tests/run_b12_routed_findings_probe.py` is **exit 1, 5 holding / 3
   findings** at this HEAD. I read all three and stopped on the context
   instruction without editing either remaining one.
   * **T18** — `api/_lib/compliance-rules.js`: `mappable` accepts **any**
     non-empty `applies_to_positions` array without checking its contents
     against `STAFF_POSITIONS`, while the very next leg of the **same
     expression** validates `audience` against it. So a requirement declaring
     `['rn']` is counted MAPPED, is left out of
     `unmapped_requirements_caveat`, and then `matchAudience` returns a
     **decided `applies: false`** for every real position because
     `list.indexOf()` can never match — a training requirement that applies to
     nobody, reported as a decision rather than a gap. **Next step: validate
     the list's CONTENTS against `STAFF_POSITIONS`; a list with no valid token
     is `applies: null` (undecided) and counts as unmapped.** This sits
     directly beside my own `positions_malformed` work in the same function and
     is the same class — I would have folded it in with ~15 more minutes.
   * **N4 (cody's)** — one comment claims coverage by a file that does not
     exist: `api/sd-data-cross-tenant-dispatchers.test.js:577` cites
     `api/sd-data-grd-session-gate.test.js`. **Next step: one-line comment
     correction naming the file that really holds it, or the honest "no
     committed arm".** Population measured by their sweep: 330 coverage claims,
     1 bad.
   * **T16 — A DESIGN DISAGREEMENT, NOT AN UNFIXED FINDING, AND IT NEEDS A
     DECISION RATHER THAN CODE.** cody's arm asserts the prior clock value is
     **kept or appended**; my N1 fix **refuses** the second write instead.
     Both close the silent overwrite; theirs keeps an edit trail, mine admits
     no edit at all. Their arm is a source check and stays red against a
     refusal. **Next step: Michael or fourth picks one.** If append-a-trail
     wins, the shape already exists in `propose_clock_correction` and N1's
     refusal becomes the fallback for a caregiver with no scheduler.

2. **MY N1 REFUSAL HAS A PRODUCT CONSEQUENCE AND IT IS NOT A SECURITY
   QUESTION.** The only route left to change a recorded clock time is
   `propose_clock_correction`, which is **scheduler-only** — so a caregiver who
   clocks in at the wrong time on their own visit now cannot fix it themselves
   at all. That is the intended direction (an unverified self-assertion is what
   EVV exists to stop) but it is a real workflow change. **Flagged in the Tier A
   obligation as the thing to review hardest. Next step: `fourth` reviews it, or
   Michael overrules.**

3. **`sql/2026-10-14-hank-b11-mar-grant.sql` IS STILL UNRUN — both blocks.**
   Uploaded to the Drive folder in this batch (13,295 bytes, verified Drive-side
   through the API) precisely so it is in front of Michael. Until it runs,
   `mar_access_grant` answers 503 NOT_PROVISIONED naming the file and the three
   audit event types are rejected by the table's CHECK, so `writeAuditLog`
   returns false and logs nothing. **Next step: Michael runs block 1 and reads
   BOTH its verifies, then block 2 — pasted WHOLE, because between its DROP and
   its ADD the audit table accepts any `event_type` — and reads all three of
   its verifies.**

4. **b10's RUN-ORDER BLOCK 5 IS STILL UNRUN AND IS NOW REACHABLE FROM THE UI.**
   `sairncare.html:1018` offers `office_manager` in the owner's provisioning
   picker; the server mints the role and the database refuses the INSERT 23514,
   so the save fails rather than validating. b12's new role-picker check
   **cannot see this** — it reads the repo's CHECK, which already includes the
   role. **Next step: Michael runs block 5.**

5. **THE CENSUS SQL IS STILL UNRUN, AND IT NOW RETURNS A MEANINGFUL NUMBER.**
   Before this batch it always returned zero. **Next step: Michael runs
   `sql/legacy_ciphertext_census.sql` PART 0 FIRST** — if `flat_enc_rows` and
   `nested_enc_rows` are both 0 that means "no credential exists", which is
   **not** the step-4 precondition — then part 1. Only after `legacy_rows = 0`
   on a part 0 that found rows is step 4 of the revoke file safe.

6. **THE ROLE-PICKER CHECK'S 11 UNPROVIDED APPS.** Four have no CHECK in `sql/`
   (sairnbiz, sairngrounds, sairnscape, stonedesk) and six have no detectable
   picker (sairncode, sairndental, sairnfreedom, sairnmechanical, sairnroofing,
   sairnvet). **Next step: for each, decide which it is — the app provisions
   roles somewhere the detector cannot see, or the schema genuinely has no role
   CHECK.** The second is a finding in its own right. `stonedesk_sub` has no
   HTML and may simply be named differently.

7. **NOTHING INVOKES THE THREE NEW SUITES.**
   `api/sd-photos-size-and-provenance.test.js`,
   `api/n1-n4-and-sf-delete.test.js` and
   `api/role-picker-vs-check-constraint.test.js` are referenced by no file under
   `tools/`. **`tools/` is cc's. Next step: cc adds all three to the gate
   driver** — and note the third exits **3** by design on an unmeasurable app,
   so whatever drives it must treat 3 as "could not run" and not as a failure.

8. **FIVE FMEA DRAFTS ARE OWED AND THE LOOP NAMED THEM.**
   `api/_lib/ai-safeguards.js`, `api/_lib/ai-scan-redaction.js`,
   `api/_lib/compliance-rules.js`, `api/sen-auth.js`, plus the three new
   suites and the two `sql/` files. `tools/fmea_draft.py` is cc's. **Next step:
   `python tools/fmea_draft.py <file> --save` by whoever owns `tools/`.**

9. **THE SEAM CHECK SAID COULD NOT TELL** for at least one endpoint/engine pair
   and the push was allowed on that basis. Not a regression and not progress.
   **Next step: `python tools/sairn_seam_check.py` by whoever owns it.**

10. **N3's REMAINING HALF IS A PRODUCT DECISION AND I DID NOT MAKE IT.**
    Whether an excluded position should also appear **rule-level** and not only
    per finding. **Next step: fourth or Michael decides.**

11. **THE PROBE ROW IS STILL IN PRODUCTION.** `ZZ-B12-SIZE-PROBE` in
    `public.sd_photos` on `SD-AUDIT-2026`. Harmless and idempotent, and it is
    the only residue this batch created. **Next step: run the delete in
    `docs/live-residue/2026-10-14-hank-b12-sd-photos-probe.json` whenever
    convenient — unlike b10's, this one does not need the SQL editor.**

---

## Register

Three records, each with four contributing factors and an explicit
recurrence-open:

| sha | app | severity | method | rule |
|---|---|---|---|---|
| `e9d9c819` | stonedesk | **critical** | independent-review | 1.11 |
| `4f69facd` | sairncode | high | independent-review | 1.7 |
| `31406a87` | sairnsenior | high | independent-review | 1.11 |

`python tools/defect_register.py --check`: **OK, 577 records** at write time
(581 after the merge), every commit resolves and every field in vocabulary.

**The FMEA loop in both directions, not the flattering half:** PREDICTED on
`api/sd-data.js` for two of three (rule 1.11), **MISSED** on `stonedesk.html`
and `sairnfreedom.html` — drafts predate both and neither cites 1.11.

---

## Claims held

**None, and that is a DEVIATION I am naming rather than leaving to be
inferred.** `sairn-api-sql` was released at the end of b11 and **b12 ran with no
claim at all** — the dispatch named six items and no claim step, and I did not
add one. CLAUDE.md's rule is to claim *before* starting. Verified, not assumed:

    python tools/sairn_claim.py list   ->  active: hover2, hover, cc.  No hank row.

**The risk this took is real and it did not land**: three other sessions were
active in this window (cc under `tools/`, cody under `tests/`, two auditors) and
nothing but their own declared scopes kept us apart. **Next session: claim
first.**

**Conflicts respected without a claim to lean on:**

* **`tests/` is cody's** — every file there was **read, never edited**,
  including `tests/run_b12_routed_findings_probe.py`, which I RAN to get the
  measured 5-holding/3-findings figure above and did not touch.
* **`tools/` is cc's** — no file under it was edited. Two routed items.
* **`docs/` specs are fourth's** — the b19 premise document and the b18
  discharge were read and not edited.
* **No auditor clone was entered.**

Files I wrote outside `api/`, `sql/` and the app HTML: the four `docs/` files
the **push gate itself requires** (`defect-density-register.json`,
`MASTER-PLAN.md`, `traceability-matrix.md`, `tier-a-reviews.json`,
`scrutiny-flags.json` which the gate writes), plus my own
`docs/hank-evidence/b12/` and `docs/live-residue/`.

---

## Stashes — untouched, and that is checked not assumed

    git stash list
    stash@{0}  b10-settings-park
    stash@{1}  (older, from a previous batch)

**`stash@{0}` was not popped, not dropped and not inspected beyond `git stash
list`.** No `git stash` command of any kind was run in this batch.
`.claude/settings.json` was **never committed**; `.claude/settings.json.bak` and
`.claude/settings.json.hooks.bak` remain untracked and were left alone. **No
hook was restored or added.**

---

## Transcript

    C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-hank\6412a39c-c2ab-47d2-8e18-c725548a950f\

Scratch artefacts there, not committed. **The one worth keeping is
`rewrite_np.py`** — the mechanical rewriter for the 89 `notProvisioned` sites.
It refuses and changes nothing unless every target matches structurally, prints
one line per site, and names each of the nine it skipped with the reason. If a
98th branch of that shape ever appears, that file is how. Also `reg_b12.py` (the
register feed) and the per-item red/green/ablation logs (**also committed** under
`docs/hank-evidence/b12/`).

**The two detached worktrees the reds were captured in are REMOVED, not left for
somebody else.** `wt-b12head` (at `6e55b1d5`) and `wt-head` (at `4c258b04`, from
b11) both deleted with `git worktree remove --force`; `git worktree list` now
shows none under the scratchpad. Three unrelated worktrees under
`C:\Users\marsh\AppData\Local\Temp\sairn-*` belong to other sessions' tooling and
were left alone.
