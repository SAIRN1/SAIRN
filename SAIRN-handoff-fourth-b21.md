# HANDOFF — fourth / ted, batch b21, 2026-10-14

**Written BEFORE the report**, at a point where nothing is half-finished: items
1–6 are committed and pushed, `HEAD == origin/main`, 0/0, no rebase or stash in
progress, and the b21 claim is still held on purpose.

**THE BATCH WAS STOPPED AT 70% CONTEXT BY INSTRUCTION, after the item in flight
was finished to a clean point.** Nothing was left half-done; what changed is
that items 3, 4 and 5 are recorded in **one** document rather than three,
because their measurements were already taken and the alternative was losing
them. **Said here rather than discovered later.**

**EVERY FIGURE NAMES THE COMMAND THAT PRODUCED IT. Re-derive anything you mean
to quote**, including out of this file.

**THREE THINGS WORTH READING FIRST:**

1. **Both Tier A obligations discharged INSIDE the deadline** — and **the
   strong-basis re-seat is REFUSED**, on a measurement: the candidate was
   authored **three minutes after** the obligation was opened.
2. **The rf_photos gate fires and the record carries no claim at all** —
   `ai_source` / `ai_approved_by` never reach the row, so `aiFooter()` returns
   the empty string. **F4.**
3. **Billing can bypass the whole new MAR grant** with an `alf_clients` write
   it already holds, **with no audit row.** **F3.**

**Transcript and working files:**
`C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-fourth\b0f8683c-3365-4d5b-82ea-094a13bdff7e\scratchpad\`
New this batch: `tier_a_list_b21.log`, `reseat_b21.log`,
`verdict_b21_addendum.txt`, `discharge_addendum_b21.log`,
`verdict_b21_sv.txt`, `discharge_sv_b21.log`,
`citation_staleness_b21.py`, `citation_staleness_b21.log`,
`citation_staleness_strict_b21.log`, `b20_prosegrep_audit.log`,
`nhi_check_b21.log`, `pre_push_tip_b21.txt`, `pull_b21.log`,
`pull_loop_b21.log`, `push_loop_b21.log`.
*(Same session as b18–b20, so those logs are in the same directory.)*

---

## 0. COMMITTED / PUSHED STATE

| | | command |
|---|---|---|
| HEAD | `7a5e6a11` | `git rev-parse --short HEAD` |
| `origin/main` | `7a5e6a11` | `git rev-parse --short origin/main` |
| behind / ahead | **0 / 0** | `git rev-list --left-right --count origin/main...HEAD` |
| working tree | **one modified file**: `docs/batch-manifest-fourth-b21.json`, carrying item 6's own evidence. Committed with this handoff | `git status --porcelain` |
| push forced? | **NO — and this is now PROVED BY ANCESTRY, not by grepping git's wording** | `git merge-base --is-ancestor <pre-push tip> HEAD` → **ANCESTOR**, i.e. a fast-forward. Pre-push tip recorded in `pre_push_tip_b21.txt` |
| `SAIRN_SEED_GATE=off` | **not used, any form** | — |
| `SAIRN_GATE_EXEMPT=seed` | **not used either** | — |
| `.claude/settings.json` | **not edited, not committed** | not in the commit's file list |
| hooks | **untouched and never re-added** | by instruction |
| files written outside `docs/` | **0** (plus my root deliverables) | by instruction |
| files under `.claude/skills/sairn-hover-auditor/` | **0 — neither auditor clone entered** | by claim |
| all four b21 `docs/` paths on `origin/main` | **4 of 4** | `git cat-file -e origin/main:<path>` per file |
| b21 manifest | **6 of 6 `done`**, close pending the uploads | `batch_manifest.py --check --agent fourth --batch b21` |
| **context now** | **73% of 1000k** | `tools/sairn_status_line.py` on this session's transcript |

**`7a5e6a11` IS THE STATE AT FINALISATION OF THIS HANDOFF** — this file, the
report, the digest, `SAIRN-latest-fourth.md`, the b21 close and the claim
release all land after it.

---

## 1. EVERY b21 ITEM — DONE AND NOT DONE

| # | item | state |
|---|---|---|
| 1 | manifest first; discharge hank `2026-10-13T09:03:35Z`; **decide the re-seat** | **DONE.** Discharged exit 0. **Re-seat REFUSED and recorded** (§4) |
| 2 | discharge hank `2026-10-14T17:56:56Z`, hardest on `alf_family_contacts` | **DONE.** Discharged exit 0, a real diff review. 4 findings |
| 3 | correct the b19 undercount; add step 4a to the runbook | **DONE — with one half ROUTED rather than applied.** The correction is recorded; **the runbook line was NOT hand-edited** because the document is generated (§3) |
| 4 | land-check cc b12 and hank b12 | **DONE as specified.** cc b12 **SKIPPED — active claim**. hank b12 **NOT LANDED**, measured (§5) |
| 5 | measure citation staleness by script; audit my b20 docs | **DONE.** 551 / 196 / **0 provably stale**; my own loose-pass figure withdrawn. b20 audit found **one** prose-grep — mine — **fixed this batch** (§6) |
| 6 | push without force, confirm landed | **DONE.** `0/0`, ancestry-proved |
| — | this handoff, before the report | **DONE** |

**NOT DONE, and deliberately: items 3, 4 and 5 did not get a document each.**
All three are in
`docs/2026-10-14-fourth-b21-corrections-landings-and-measurement.md`, sections
1–4. **No measurement was skipped; only the filing was consolidated.**

---

## 2. CLAIMS, LOCKS, STASHES

| hold | count | detail | command |
|---|---:|---|---|
| repo claims held | **1** | b21, published on `origin/main`; **release LAST**, after all four uploads verify | `sairn_claim.py list` |
| **Tier A obligations assigned to me** | **2, BOTH FRESH** | see §7 — `cody` `2026-10-15T00:00:41Z` and `2026-10-15T00:02:27Z`, both **0.4h old**, 2 resources each, both on `tests/run_cross_tenant_dispatchers_sabotage_probe.py`. **Neither overdue; ~23.5h of runway each** | `--list` |
| obligations discharged this batch | **2** | both as the **assigned owner**, neither by `--takeover`. Register 17 open before and after — two closed, two opened | before/after `--list` |
| **session lock** | **1, MINE and LIVE** | `state : SELF — this session owns the lock (CLAUDE_PID 3444)`. **The eight-batch-old dead lock was reaped in b20 and has stayed healthy** | `python tools/session_lock_check.py status` |
| locks removed by me | **0** | b20's reap was a `guard` reclaim, not an `rm` | — |
| **`git stash`** | **0** | nothing stashed, nothing to recover | `git stash list` |
| worktrees | **5 total, NONE MINE** | the other four are other sessions' temp gate trees | `git worktree list` |
| status registry row | `working` | set at batch start; **`idle` at release** | `sairn_status.py set` |

---

## 3. CLOSED — and I will stop raising it

**Michael ran and verified all six blocks of
`sql/2026-10-14-michael-run-order.sql` on 2026-10-14 at 19:38 ET, blocks 5 and
6 included.** Recorded in
`docs/2026-10-14-fourth-b21-corrections-landings-and-measurement.md` §0.

**My b20 "blocks 5/6 UNVERIFIED" is CLOSED. It appeared in b20's verdict,
report, digest, handoff and latest-file and is not to be raised again.**

**What it changes, rather than just being retracted:** b20's leg-role-matrix
verdict said the 36-resource matrix was *"a gate nobody can populate, and the
only role anybody can hold is the deprecated one."* **True when written, false
now** — the five SAIRNlegacy task roles and SAIRNcare's `office_manager` are
accepted by the live CHECK, so the matrix b20 verified as a faithful
transcription is **in force**. The `office_manager` note in this batch's
sv discharge is marked closed on the same ground.

---

## 4. THE RE-SEAT DECISION — REFUSED, and this is its record

`docs/2026-10-14-fourth-b21-addendum-b5-discharge.md` §0.

**STATUS: NOT RE-SEATED. The record stays `COULD-NOT-TELL` permanently, by
decision.**

```
obligation opened_at          2026-10-13T09:03:35Z
8a572a6ead25  (the offer)     authored 09:06:42Z   3m07s AFTER
13f3a3be                      authored 09:00:18Z   3m17s BEFORE
both                          committed 10:15:2xZ  -> post-rebase objects
```

**Three grounds:** the offered candidate **post-dates the obligation**, so it
cannot be what the record was stamped at; the exact-file-set match succeeded
only because the **recorded `files` list is one path while hank's own text says
the push was four**, which excludes the commit that actually carries the
evidence; and the tool stamps `opened_at_sha_reseated: true`, so a re-seat would
make the record **read as resolved** while pointing at the wrong commit.

**Verified on origin: `reseated = None` on both discharged records** — nothing
was written.

**AND ONE CORRECTION TO MY OWN FIRST PASS:** I initially thought the file-set
basis was **ambiguous** and it is not — `8a572a6ead25` is genuinely the only
commit whose entire file set is that single path. `git log -- <path>` lists
commits *touching* a path and says nothing about their full file set, and I read
it as though it did. **Second batch running where my own first measurement
needed measuring, and both times the correction removed findings rather than
adding them.**

**ROUTED TO cc, one comparison:** `--reseat-shas`'s exact-file-set basis should
require the candidate's **author time to precede `opened_at`** — and should
**print that time beside the offer**. The current line prints the sha, the basis
and the subject, all three of which looked right. **The field that disproves it
is the one not shown.**

---

## 5. WHAT IS OPEN, AND WHY — routed work

### hank — four findings, F3 and F4 first

* **F3 — the MAR grant is bypassable, silently.** `ALF_MANAGEMENT_ROLES`
  includes `billing`, and on the `alf_clients` write path `isManagement` skips
  **both** assignment restrictions with `assigned_employee_id` written verbatim.
  So billing self-assigns a resident, then reads `family_mar` and is admitted by
  the **assignment tier** — **no grant row, and no `mar_access_read` audit row,
  because that write is conditioned on `if (marGrant)`.** **Next step: refuse on
  the role in the `family_mar` branch before the scope tier, or exclude
  `billing` from the assignment tier for that action.**
* **F4 — the `rf_photos` gate fires and the record carries no claim.**
  `enforceAiApproval` mutates `payload`; the handler rebuilds the record from
  three named fields and persists that, so `ai_source` / `ai_approved_by` /
  `ai_approved_at` **never reach the row** (`grep -n "ai_source\|ai_approved"
  api/sd-data.js` → **one comment line, nothing else**). `aiFooter()`
  short-circuits and returns `''`, so **no footer renders — not even
  "AI-assisted — not reviewed", which exists precisely so an absent footer and
  an unreviewed one cannot read alike.** **Next step: carry the three fields
  into the rebuilt record.**
* **F1/F2 — billing is not refused by default on `family_mar`, and the
  existence oracle survives** for any grantless billing session with at least
  one assigned resident: the contact row is fetched **before** the scope test.
* **Also hank's, smaller:** no revoke action exists for a live grant (only
  direct DB access); `license_hash` is the one grant field never re-verified in
  memory; and `api/sd-data.js`'s comment still says no client stamps a
  high-risk resource, which is now false.
* **Still open from b19/b20:** the **`sd_photos` SIZE fix first, with T17
  landing with or before it**; the 400→503 misattribution — **now measured at
  63 branches across 22 resources, not twelve** (§6); b18's **N1 remains
  open**; the aftercare delimiter-ambiguous key (b20 F4) and the
  canonicalisation's local duplicate (b20 F5).
* **A design question, not a defect:** the granted MAR read is gated on family
  consent and yields only `date`/`time`/`status` — **never medication names.**
  An `office_manager` grant admits a billing clerk to a list that cannot serve
  coding work. **Worth deciding before more is built on it.**

### cody — arms, all failing-first

* **The F3 bypass arm:** a billing session self-assigns via `alf_clients`, then
  reads `family_mar` — must be refused, or at minimum audited.
* **The F4 end-to-end arm:** route `rf_photos` **through `api/sd-data.js`** and
  assert `aiFooter()` on the **stored** record. **The existing arms drive
  `enforceAiApproval` in isolation and assert the local payload object, which
  is why F4 shipped** — and the one end-to-end footer arm that does exist runs
  on `mech_quotes`, whose branch stores the payload wholesale.
* **The ordering arm (F2) needs rebuilding, not extending:** the arm that
  claims it reads only the status code, the fixture records only non-GET calls
  so no GET ordering is observable, and its fixture gives the caller no
  assignment — so the oracle case is never driven.
* **The fail-closed arm is absent** even though the behaviour is correct: the
  grants mock is unconditionally 200.
* Plus the b20 aftercare-collision arm and b19's four.

### cc — `tools/`

* **The re-seat author-time guard** (§4).
* **The step-4a generator line** (§3 of the corrections doc): cc fixed **two of
  three** places; the third is the operator-facing `### session-signing`
  paragraph at `docs/NHI-REGISTER.md:69`, whose source is
  `tools/nhi_register.py:374-376` and still reads *"wait 12h, clear
  PREVIOUS"*. **The replacement prose is written and ready to paste** in the
  corrections doc, anchored on `signingKeys()` rather than a line number —
  **because that paragraph's own citation `api/_lib/auth.js:365` is itself
  rotted; the real line is `:510`.** **I did not hand-edit:** the document is
  `GENERATED … Do not hand-edit`, and `nhi_register.py --check` exits **0 OK**,
  so an edit would be reverted and would turn a stale paragraph into a drift
  alarm.
* **The anchor rot check** (b20's spec, 8 requirements / 10 arms) — **and §6
  reframes its R3: bare `:NNNN` citations must be counted and reported as
  UNASSESSABLE, not folded into a total.**
* b19's census asks 1 and 4; `batch_manifest.py:386` (**still worked around
  with `PYTHONIOENCODING=utf-8` on every call**); the b20 drive-verify findings.

### hover2 / hover

Unchanged from b20: four `# OWNER: hover2` lines; which tree is canonical for
the four basenames that exist in both with different contents.

### Michael

**Nothing outstanding from me.** The run-order question is closed (§3). Option B
still stands until a practitioner answers **H8**.

---

## 6. THE MEASUREMENTS — corrected figures

`docs/2026-10-14-fourth-b21-corrections-landings-and-measurement.md` §1 and §4.

**THE b19 UNDERCOUNT, CORRECTED: "roughly twelve" → 63 across 22 resources**
(242 raw matches, 63 narrowed to the 503-folding shape). **H1 found it by
re-running my own command.** I counted hits in one reading of one file region,
called it twelve, and carried the twelve across three documents as if measured.
**63 is 5.25× twelve, so the blast radius I handed hank was five times too
small.** The convention needs one more clause: **print the command AND the raw
count, not just the conclusion** — "242 raw / 63 narrowed" is a sentence nobody
can mis-carry.

**CITATION STALENESS, bounded:**

| | |
|---|---|
| total line citations in `docs/CRITICALITY-TIERS.md` | **551** |
| explicit `file:line` | **196** |
| **provably stale** | **0** |
| landing on a blank or pure-comment line — **likely** stale | **37 of 196 (19%)** |
| bare `:NNNN`, target must be inferred | **355 — and the inference is unreliable, demonstrated** |

**My loose pass's 14 "provably stale" are WITHDRAWN: they were entirely my own
attribution error.** Three `:NNNN` citations belonging to `stonedesk.html` were
charged to an 893-line `.py` file and reported as beyond-EOF. **The real finding
is the FORM: 64% of citations cannot be mechanically checked at all.**

**AND THE b20 SELF-AUDIT FOUND EXACTLY ONE PROSE-GREP, MINE:**
`grep -ci "force|forced|+ refs"` over the push log — my own "not forced" claim
rested on git's **wording**. **Fixed this batch by method:**
`git merge-base --is-ancestor <pre-push tip> HEAD`, a property of the graph.
**The other four grep claims are tokens** (`WRONG AGENT`, `^CONTEXT`,
`^# OWNER:`) and stand.

---

## 7. THE TWO OBLIGATIONS NOW MINE — exact next step each

Both arrived during this batch and **both are fresh**, so b22 can meet the
clock for a third batch running.

| # | obligation | age | exact next step |
|---|---|---:|---|
| **b22 item 1** | `cody` **`2026-10-15T00:00:41Z`**, 2 resources, `tests/run_cross_tenant_dispatchers_sabotage_probe.py` | **0.4h** | Read the record's `what` first — **two obligations 1m46s apart on the same file is unusual and may be one change recorded twice.** If so, say so rather than writing two verdicts |
| **b22 item 2** | `cody` **`2026-10-15T00:02:27Z`**, 2 resources, same file | **0.4h** | Same, and **discharge in `opened_at` order** |

**~23.5h of runway each. Neither is takeover-eligible and neither is overdue.**
**Check both shas resolve before deciding whether either is a diff review or a
state review.**

---

## 8. FINAL STEPS STILL AHEAD OF THIS HANDOFF

1. Commit this handoff with the manifest's item-6 edit, and push.
2. **Upload this handoff to Drive folder
   `14Xc5oT0xzSLa_rTSOSXWVK3Kko1Fbx09` and verify.**
3. The report and digest, plus **`SAIRN-latest-fourth.md`** (under ~60 lines),
   then upload-and-verify, then a **Drive-side API read** — the mount proves the
   bytes are in the sync set, not that Google acknowledged them. **Expect the
   API read to lag; b19's and b20's first reads came back empty and were a
   retry, not a missing file.**
4. `batch_manifest.py --close --agent fourth --batch b21` — **after** the
   uploads verify.
5. **Release the b21 claim LAST**, then set the status row to `idle`.

**Nothing is partial.** Every open item above is another session's, or mine and
named as mine with its b22 slot, or a measurement with its command stated.
