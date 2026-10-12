# Handoff — cody, batch 27 (b4), 2026-10-11/12

**Landed at `f12e6042` on `main`, pushed and confirmed 0 ahead / 0 behind.**
Written before the report, per the batch instruction.

Verify everything below against the repo. Every figure here was measured with a
named command and the command is given; nothing is carried from the brief.

---

## 0. READ THIS FIRST — THE TWO THINGS THAT WILL COST YOU TIME

### This clone was running with EVERY HOOK STRIPPED, and the stripped file was uncommitted

At session start `.claude/settings.json` in the working tree had `"hooks": {}`
against HEAD's five events and eight hook commands, with two backups beside it:
`.claude/settings.json.bak` (a strict subset of HEAD) and
`.claude/settings.json.hooks.bak` (**byte-identical to HEAD**). HEAD was intact.
Restored with `git checkout --` and both backups removed; git history holds
them.

**THIS IS THE SECOND CLONE IT HAPPENED IN, THE SAME EVENING.**
`SAIRN-digest-ted-b4.txt` records the identical shape in `Documents/SAIRN-fourth`
— `"hooks": {}` in an uncommitted working-tree file, staged through two `.bak`
copies, the content change hidden inside a reformat. **Nine of that clone's
hooks were controls over the clone itself, including
`tools/hook_integrity_check.py`, which is wired as a hook and so was silenced by
the same edit.** Two clones is not a coincidence worth leaving unnamed.

**What to do in a fresh session, before anything else:**

    python -c "import json;d=json.load(open('.claude/settings.json'));print({k:len(v) for k,v in d['hooks'].items()})"
    git status --short .claude/

An empty dict is the failure. The only signal either session got was an
ABSENCE — the status registry not being handed over at session start.

### SEVEN other-session handoffs on the shared Drive blocked this clone's push, and three arrived mid-declaration

`tools/external_file_index_check.py` denies a push while any tool, script or
handoff sits in a declared external directory unindexed. `G:\My Drive\SAIRN-status`
is declared and is shared by every session. Over this batch:

| # | file | session | when it was found |
|---|---|---|---|
| 1 | `handoff-h2-2026-10-11.md` | hover2 | declared by cc, 2026-10-11 |
| 2 | `handoff-h2-2026-10-11b.md` | hover2 | start of this batch |
| 3 | `handoff-fourth-2026-10-11.md` | fourth | first push attempt |
| 4 | `SAIRN-handoff-h1-b10.md` | hover | first push attempt |
| 5 | `handoff-h2-2026-10-12.md` | hover2 | **predicted by row 2's own note; arrived inside the hour** |
| 6 | `handoff-fourth-2026-10-12.md` | fourth | **arrived DURING the write that declared 5** |
| 7 | `SAIRN-handoff-h1-b11.md` | hover | **arrived DURING the push that declared 6** |
| 8 | `handoff-h2-2026-10-12b.md` | hover2 | after the push; still unindexed |

**DECLARING THEM ONE AT A TIME CANNOT CONVERGE** — three sessions write to that
directory faster than one session can index it, and every push is gated on a
race it does not participate in. All seven are declared in
`docs/external-files-index.json` with `belongs_in_git: true`, routed to the
session that wrote each, and NOT moved: a build agent must not write into an
auditor clone.

`SAIRN_SEED_GATE=off` was **not** used, deliberately — it skips all fourteen
checks including the Tier A obligation and the two regenerated documents the
same push had just satisfied properly, and `SAIRN_GATE_EXEMPT` names only
`seed`, so no scoped form exists for this check.

**The two repairs, with owners, neither taken here:**
1. **The check's blocking scope is wrong.** It should keep exit 1 for the session
   that OWES a file and stop denying everyone else's push. It already reads a
   `belongs_in_git` field and ignores it. **`tools/external_file_index_check.py`
   is cc's**, and cc's own row in the index raised this before I did.
2. **Each auditor should write its handoff into its own clone**, which CLAUDE.md
   already says by name. That is each agent's own to change.

---

## 1. What landed

| item | subject | state |
|---|---|---|
| 1 | route the 76 REAL suite failures by app | **landed before this session** (`ca81d59d`), not redone |
| 2 | Tier-A dangling-sha reseat + routing | **done** — 3 reseated, 11 WEAK routed, 25 refused routed |
| 3 | `law_role_granularity` (hover2 seq 757) | **NOT FIXED — a product/bar-rules decision, see §3** |
| 4a | seq 951, citator feedback attribution | **done** — both layers; schema half NOT live-verified |
| 4b | seq 965, `sen_caregivers` PII scope | **done** — field redaction + client half + 18-arm suite |
| 5 | `check4_probe.py` / `check7_probe.py` worktree | **done** — clone mechanism verified; the probes' own verdicts COULD NOT RUN, see §5 |
| 6 | duplicate DOM ids | **done** — 3 of them, all live defects |
| 7 | the two unlocatable queue16 conventions | **REMOVED from scope — fourth holds it, see §7** |
| 8 | compaction discipline | held; no file over 400KB opened whole, no mid-task model or MCP switch |
| 9 | handoff / report / digest | this file, then the two beside it |

---

## 2. Tier-A reseat — and the brief's two numbers were the wrong way round

Full account: **`docs/2026-10-11-cody-b4-tier-a-reseat.md`**, every figure
generated from the tool rather than typed. Regenerate with:

    python tools/tier_a_review_gate.py --reseat-shas --include-reviewed

The brief asked for "~21 of 32 reseated, 11 cross-session ones held back".
Measured: **39 dangling records carried a sha — 3 strong-basis, 11 WEAK, 25
refused**, plus **145 with no sha at all** which belong to `--backfill-shas` and
were not touched. **The 11 is real and is exactly the WEAK set; the 21 is the
REFUSED set, which this clone cannot reseat at all.** The halves were inverted.

**Reseated, 3, all strong basis, each stamped and reversible from the ledger:**

| author | opened_at | basis |
|---|---|---|
| `cc` | 2026-09-26T13:13:44Z | EXACT FILE SET |
| `fourth` | 2026-09-27T02:17:49Z | EXACT FILE SET |
| `cody` | 2026-10-12T01:49:28Z | SUBJECT TWIN |

**Two of the three are not cody's records and that was a judgment call.**
`opened_at_sha` is a pointer to the commit a record describes; repairing a
dangling one on a strong basis changes no verdict, reviewer, finding or owner,
and every reseat keeps `opened_at_sha_was`. The previous session on this item
reseated only its own five. **If you disagree, each one is reversible from the
ledger alone** — that is why the basis is stamped.

**Not reseated: the 11 WEAK, 9 of which genuinely span two sessions.** Each is
listed in the doc with its files, resources, dangling sha, the candidate, the
gap in hours and every session on the record. `--write-weak-basis` is a second
flag because containment is a different claim from equality.

**Re-measured after the push: 242 records, 60 reachable, 0 strong-basis
reseatable, 11 WEAK, 37 still dangling.** The number moves on every rebase by
any clone — it moved twice during this batch. **Do not quote 39 or 37; run the
command.**

### Two tooling defects in the reseat tool itself, both found by running it

Registered against the tool's commit:

1. **A SELECTOR decided the walk window.** `dates` read from `rows`, which
   `--only` has already narrowed, so the same record got RESEATABLE in the full
   population and REFUSED under `--only` — the careful path saw less.
2. **An EXACT FILE SET was a strong basis with no time bound** and offered an
   **18-day-older** commit as one, which `--write` alone would have applied.
3. And a probe arm (`--only NARROWS the population`) asserted `rc == 0` against
   a fixture whose sha is forty zeros on purpose. **It had never passed**, and
   that was confirmed by running HEAD's own gate against the same ledger.

---

## 3. `law_role_granularity` — WHY IT IS NOT FIXED, and what the next session must decide

**This is the one item that was not completed, and it is not blocked on effort.**

**First, three corrections to the brief, all measured:**

- **It is MODERATE, not HIGH.** hover2's log entry and its routing doc both say
  `moderate`.
- **`docs/2026-10-08-hover2-law-role-granularity-routing.md` DOES NOT EXIST IN
  THIS CLONE.** It is in `Documents/SAIRN-hover2/docs/`. The `:1037` /
  `:1067-1069` citations come from that doc's 19-row table, not from the log
  entry's own prose.
- **`seq 757` is ambiguous across the two auditors.** H1's seq 757 is an
  unrelated batch-close entry. The one meant is **hover2's**.

**The finding is real and I re-derived it from the code:** 19 sairnlaw
resources are session-gated and carry no role distinction. Only
`law_trust_reconcile` has a role check (`LAW_RECONCILE_ROLES`, owner-only).

**The fix is a product and bar-rules decision, and the code has twice declined
to invent it — in writing, with reasons:**

- `api/sd-data.js:13789` — *"A SESSION GATE, NOT A ROLE GATE. ROLES_BY_APP.sairnlaw
  is owner / attorney / paralegal, and all three legitimately work matters, time
  and documents. Which role may see which record is a product decision with no
  obvious answer, and inventing one here would break the app for the people it
  is for."*
- `api/sd-data.js:15719` on the one role gate that exists — *"WHO SHOULD BE IN
  THE SET IS NOT DECIDED HERE, AND THAT IS DELIBERATE … widening it is a
  bar-rules judgement for the firm … Tracked as an open decision; NOT closed by
  this fix."*

**And hover2 did not prescribe a fix either** — its own entry says *"routed, not
a prescribed fix"*.

**I checked for the one case that would NOT be a product decision and it is not
present.** SAIRNlaw already has two decided professional-responsibility
boundaries, both enforced: `AI_COC_REVIEW_ROLES` (owner+attorney, AI chain of
custody) and `RULE_AUTHORING_ROLES` (owner+attorney, deadline-rule authoring,
used by `api/legal-deadlines.js:964`). Both are live, neither is a dead
constant. **None of the 19 resources carries either of those acts**, so there is
no already-decided boundary that `sd-data.js` merely fails to enforce.

**THE QUESTION ONLY MICHAEL OR THE FIRM CAN ANSWER**, and it is the whole of
what remains: *for a three-role law firm (owner / attorney / paralegal), which
of these should a paralegal be able to read and write?* The three sharpest,
which hover2 also named: **`law_picases`** (settlement figures, attorney work
product, Tier A/A), **`law_pimedical`** (the code's own comment calls it as
sensitive as `law_trusttx`), **`law_bankstatements`** (Tier A on integrity).
`law_trusttx` is IOLTA client trust money and is the one a bar association
audits.

**Do not let a future session "fix" this by inventing a role split.** A wrong
one 403s paralegals out of matters they legitimately work, which the code says
in two places.

---

## 4. The two fixes, and exactly what is NOT verified about each

### 4b — `sen_caregivers/read`, hover2 seq 965, HIGH

The read returned the whole blob, every row, to any authenticated sairnsenior
role — including each caregiver's **background-check date**, a **state-issued
caregiver ID** and **free-text HR notes about a colleague**. The branch's
justification — *"Employment/certification data, not client PHI"* — was true and
was the wrong comparison: it is employee PII.

Fixed at **field** level, not by a flat role refusal, which would have broken
the roster the lighter gate exists to serve. Three fields now go to
owner/billing only; nine survive. A **new constant**, not
`SEN_CLIENT_MANAGEMENT_ROLES`, because who may see a colleague's background check
is not the same decision as who may reassign a client.

**The client half is in the same commit and is the part most likely to be
undone by someone tidying up:** the roster table rendered
`fdate(c.bgcheck_date)` for every role, and after a redaction that renders
**identically to a caregiver with no background check on file** — on a
compliance column. Non-management now sees an explicit `Restricted` badge.

**NOT VERIFIED:** no request was made to the deployed endpoint. The suite drives
the handler against a mocked PostgREST. **A Tier A review obligation is recorded
and assigned to `hank`**; its text names the CUT, the TIER and the
round-trip-wipe dependency as the three things to attack first.

### 4a — `cl_feedback_log`, hover2 seq 951

No employee was recorded against a legal-citation treatment confirm or
correction, at the application layer **and** the schema layer, while the
schema's own comment three lines above the table said *"individual feedback
stays attributable"*. The caller was in scope at `:184` the whole time.

Columns are **nullable on purpose** — the session token on this endpoint is
optional by design, so a row can legitimately have no person on it and NULL is
written rather than a guess.

**WHAT IS STILL OWED, and it is Guardian Check 29's subject:** the two columns
arrive only via `alter table`, and nothing has been run against a real database.
**Whoever can reach Supabase must: run `sql/sairnlaw_citator_schema.sql`, POST a
real feedback with a session and without one, and read both rows back.** Until
then the feedback action answers **503 NOT_PROVISIONED naming the file** — which
is loud rather than silent, and is not the same as a verified write.

---

## 5. The probe pair — the mechanism is verified, the probes' verdicts are not

`check4_probe.py` and `check7_probe.py` planted fixtures in a linked
`git worktree`, which **shares `.git/config` with the owning clone**. The
reproduction is two commands and is in
`docs/2026-10-07-fourth-routed-pinned-worktree-shared-config.md`: a `git config`
write from inside the worktree left `bare = true` in
`Documents/SAIRN-fourth/.git/config`, after which every git command there failed.

Converted to a throwaway clone — the move `check8_probe.py` made on 2026-10-06
and these two never got. **Hardlinked, not `--no-hardlinks`, which is a
deliberate deviation from the brief**: measured here, `--no-hardlinks` costs
**7.7s and 207MB per run** against no measurable cost hardlinked, and these
probes run in the whole-tree suite in four clones after every push.

**VERIFIED by running both:** the clone builds, the **pre-push hook fires from
it** (it received a real gate refusal, which cannot happen if `core.hooksPath`
is missing — the silent failure this conversion could most easily have caused),
`.git/config` **byte-identical** across both runs, **no worktree registered**,
and **no new `%TEMP%` residue** (the six leftovers there are dated Sep 21,
Oct 5 and Oct 6 ×4 — four of them the leaks `check8`'s own docstring describes).

**NOT VERIFIED: check 4's and check 7's own verdicts.** Both exit **3 COULD NOT
RUN**, correctly, because a CLEAN push is refused by the external-file-index
gate over an eighth Drive handoff. That is the honest third state and the probes
say so themselves rather than reporting a check-4 or check-7 failure. **Re-run
both once §0's loop is closed** — that is the only outstanding verification on
item 5.

---

## 6. Duplicate DOM ids — all three were live defects

Measured with an HTML-parser id scan (`tools/` carries **no** duplicate-DOM-id
checker, which is its own finding): sairncare 303/1 → **304/0**, sairnfreedom
398/2 → **400/0**, sairnsenior 327/**0** unchanged.

- `sairnfreedom.html` **`ac-tbody`** — the worst. `sfRenderAccess()` and the
  accounts renderer both wrote into the OFFICER roster tbody. The accounts table
  never rendered, or the officer roster was replaced by account rows.
- `sairnfreedom.html` **`ac-name`** — `sfOpenAccount()` read the officer name
  box, so a post could not open the **ORC 2915.10(C)** exclusive bingo-session
  account under the name typed in.
- `sairncare.html` **`fc-name`** — `saveFacility()` stored the family-contact
  box's value as `alf_facility.name`, normally empty, and opening the profile
  overwrote whatever the user had typed into the family-contact form.

Renames follow each file's own existing prefix (`acct-` from `acct-kpis`,
`fc-facname` beside `fc-company`/`fc-state`/`fc-licnum`).

**NOT LIVE-VERIFIED.** Id uniqueness is measured; the behaviour is reasoned from
the call sites. No click-through, no screenshot. Guardian's own auth-gated-scope
limitation applies.

---

## 7. Item 7 was REMOVED from scope, not reworded

The two unlocatable "queue16" conventions blocked on **fourth's live claim** over
the phrase `conventions queue16`, and that is a **real** overlap — fourth's own
task (b) is literally *"recount cody's two unlocatable queue16 conventions"*.
Per PR §4.3 the item was dropped rather than rephrased to clear the matcher.
**Ask fourth.**

**Contrast, so the difference is on the record:** the claim itself was blocked on
hover2's b9 claim over the phrase `"digest plus"` — an English fragment, no
shared file, app, subject or resource, against a read-only audit role. That one
is lexical, so the claim was **written directly with the collision recorded
inside it**, which is the move PR §4.3 permits. The task string was not
reworded.

---

## 8. Open, with owners

| # | what | owner |
|---|---|---|
| 1 | **`law_role_granularity`** — the role split for 19 sairnlaw resources | **Michael / the firm.** Do not let a session invent it |
| 2 | **Run `sql/sairnlaw_citator_schema.sql`** and verify a real feedback write both ways | whoever can reach Supabase |
| 3 | **Live-verify `sen_caregivers/read`** against the deployed endpoint | next session with network |
| 4 | **Discharge the `sen_caregivers` Tier A obligation** | **hank** (assigned) |
| 5 | **Discharge the `route_suite_failures.py` Tier A obligation** | **cc** (assigned) |
| 6 | **Re-run `check4_probe.py` / `check7_probe.py`** for their real verdicts | after open #7 |
| 7 | **The external-file-index blocking scope** — read `belongs_in_git`, keep exit 1 for the owing session only | **cc** |
| 8 | **Auditors writing handoffs to Drive instead of their own clone** | hover, hover2, fourth |
| 9 | **11 WEAK-basis dangling records**, 9 spanning two sessions | listed per-record in the reseat doc |
| 10 | **12 `NO_OBJECT_IN_CLONE` records** — only the clone whose rebase orphaned each can resolve it | that clone |
| 11 | **5 `SHA_WRONG_WHEN_WRITTEN`** — fix the RECORD, not the sha | the record's author |
| 12 | **145 records with no sha at all** — `--backfill-shas`, untouched here | unassigned |
| 13 | **A duplicate-DOM-id checker** — `tools/` has none; all three found by an inline scan | unassigned |
| 14 | **`sd-data-cross-tenant-dispatchers.test.js` 14 `grd_*` failures** — unchanged, already routed | cc+fourth+hank |
| 15 | **`run_tier_a_review_gate_sabotage_probe.py` flake** — one run's baseline died on a Windows `os.replace` PermissionError inside `save_reviews`' own temp fixture; passed unchanged on re-run | unassigned |
| 16 | **FMEA drafts absent** for `tier_a_review_gate.py` and its probe, so this batch's defects are unscoreable against a prediction | unassigned |

---

## 9. Claim

Released at the end of this session. It was **written directly** rather than
through `sairn_claim.py claim` — see §7 — and the shared status registry at
`~/SAIRN-SESSION-LOCKS/status` had to be restamped with
`sairn_status.py set --state working` first, because it still carried a cody row
for a dead `CLAUDE_PID 23640` and `own_claim_state()` therefore read **DEAD**.
