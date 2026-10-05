# Hank inventory — landed, in flight, blocked, stale, unlogged

**2026-10-04/05.** Written to be read by the next session in this clone. Every
row below was re-derived at HEAD before it was written; where a premise I was
handed had already gone false, the re-derivation is what is recorded, not the
premise.

Predecessor: `docs/2026-09-29-inventory-hank.md`. Rows that closed since are
marked rather than dropped.

---

## 0. The pattern in this whole batch, stated first

**Five of the seven items I was sent had already been overtaken, and the
overtaking was invisible from the dispatch.** Not one was wrong when it was
written. The counts:

| Item | As dispatched | At HEAD |
|---|---|---|
| 3 — SAIRNgrounds offsets `grd_irr_schedules +24`, `grd_schedule +25` | repoint each | **both already SOUND.** Different rows are flagged, and repointing those would have **broken four correct citations** |
| 4 — register two H2 findings | register them | **cc landed both at `5ab3bcb5`** while I held the derivation |
| 5 — `api/_lib/job-risk.js:218` → `:222` in the register | repoint | **the citation is not in the register at HEAD.** `grep -n job-risk docs/CRITICALITY-TIERS.md` → nothing |
| 6 — four tools unbuilt | build in order | **all four landed**, shas in §1 |
| 2 — token expires Oct 4 | verify | works, and **carries no expiry at all** — see §1 |

**The dispatch was a snapshot and nothing between its writing and its execution
re-checked it against the repo.** That is cross-domain discipline 10 (no long
run whose first check is at the end) applied to a work queue rather than to a
tool, and it is the reason item 8's instruction — re-derive every claim from the
file at HEAD before acting — is the only reason this batch did not do damage.
**Had I executed item 3 as written, I would have pushed four regressions and
reported them as fixes.**

---

## 1. What landed, with shas

| What | Sha | Verified by |
|---|---|---|
| `tools/citation_line_drift_check.py` stops presenting an inference as an instruction; prints the **cited line's own source text** on every DRIFTED row | `04abf76e` (was `15da3f66` pre-rebase) | `tests/run_citation_line_drift_probe.py` **17 passed, 0 failed** (was 13/0). Real runs driven both ways: sairngrounds exit 1 / 4 rows, sairnfreedom exit 1 / 32 rows |
| Probe section **F**, 4 arms, incl. a known-bad render-site citation built to be indistinguishable from genuine drift by every signal the tool *can* measure | `04abf76e` | criteria `2026-09-30.1` → `2026-10-04.2` |
| `docs/SAIRN-OPEN-WORK-INDEX.md` row 73 closed, **rebuilt whole** per PR §2.1 | `04abf76e` | `grep -n "job-risk" docs/CRITICALITY-TIERS.md` → no match; `grep -n "'at_risk'" api/_lib/job-risk.js` → `:222`, sole occurrence |
| Defect record + the two FMEA drafts the register's own loop asked for | `eebe9bad` | `defect_register.py --add` accepted after four refusals (see §4) |
| Tier A review obligation opened, 5 attack points, assigned `fourth` | `eebe9bad` | gate confirms only `fourth` may discharge |

**Pushed at `eebe9bad`.** No live verification applies and that is stated rather
than skipped: this change touches one Python tool, one probe and three
documents. **Nothing deployed changed, so there is no deployed URL to check** —
PR §3.2's live-verify step has no subject here. Saying "live-verified" would be
the fabrication that step exists to prevent.

### Item 6's four, all already landed before this session

| Sub-item | Sha | State at HEAD |
|---|---|---|
| `hover_routing_gap_check.py` hardcoded *"2 of 686 routable"* in the header | `9b23fc27` | **gone.** The comment now says the ratio is printed on every run and is deliberately not written there, and names its own prior wrong number as the record |
| `hook_integrity_check.py` | pre-existing | **wired**, `.claude/settings.json:171`, SessionStart |
| `plugin_upgrade_check` credential dedupe | `ff6279ea` | **done.** Imports `gh_token` (`:62`); the third copy is removed and documented at `:186-209`; `resolve_token()` catches `TokenUnavailable`; driven by `tests/run_plugin_upgrade_token_probe.py` |
| `tier_a_review_gate.py:942` `hover*` exclusion | `b3ae64ad`, narrowed `29182877` | **done, and better than the ask.** It is `is_hover_session()` at `:1118-1129`, regex `^hover(\d\|[-_]\|$)`, applied `:1154`. Deliberately **not** `startswith('hover')`, so a build agent named `hoverboard` is not silently excluded. Line is `:1118`, not `:942` |

### Item 2 — the token, and the answer is not the one the dispatch expected

**LIVE PASS**, and `tools/gh_token.py` is **not** what established it.

That tool prints the source and the token's length and **never contacts
GitHub** — its exit 0 means "a token was found", not "a token works". Taking it
as a liveness check is PR §1.1 exactly: a check that tests something adjacent to
what you asked. Driven properly, an authenticated `GET /user`:

    http 200  login SAIRN1  scopes: gist, repo, workflow
    github-authentication-token-expiration: ABSENT

**`SAIRN-Session55` expires Oct 4 — and the credential manager is not serving a
token that expires.** GitHub returns that header for any PAT that has an expiry;
its absence means the live credential has none. So either Session55 is already
replaced, or it never was what the credential manager held. **Either way the
Oct-4 deadline in the dispatch does not apply to the token that is actually
answering, and nobody can see that from `gh_token.py`'s output.** Logged as a
gap in §5.

---

## 2. In flight

**Nothing of mine is half-built.** The one thing open is a handoff, not code:

| Item | State |
|---|---|
| Tier A review obligation on `04abf76e` | **assigned `fourth`**, 5 attack points named, undischarged. Attack point (a) is whether `DRIFTED` is still the wrong word now that the header redefines it — I think it probably is, and I did not rename it because the blast radius crosses historical records and a green probe |

---

## 3. Blocked, and on whom

| Blocked | Holder | Evidence |
|---|---|---|
| **Item 4 — the two H2 register cells** | **`cc`**, claimed `2026-10-04T23:33:10Z`, **0.0h before I checked** | Overlap was **genuine, not lexical**: cc's claim string names `mech_docs` and `msb_bottle_scans` outright. **Not started.** Landed by cc at `5ab3bcb5` while I held the read-only derivation. Refusal recorded in `.claude/claims/hank.json` |
| The surviving `job-risk.js:218` reference | **`hover`** | `.claude/skills/sairn-hover-auditor/tools/run_editor_review_v3_last30.py:10`. The auditor's own tree — hover's scope by `docs/2026-09-15-hover-auditor-separation-enforcement.md`, and `tools/hover_auditor_scope_gate.py` refuses a build agent for it. **Named in index row 73 rather than silently dropped** |

**My independent derivation of item 4 agreed with cc's on both findings**, which
is worth recording because it is two methods on one claim rather than one:

* `mech_docs` — `api/_lib/mech-redact.js:43-49` says in its own header *"A
  PERSON'S NAME WRITTEN IN PROSE IS NOT FOUND… The output therefore carries
  `complete: false` ALWAYS."* `LABELLED_NAME` catches only a name beside a
  label. The register cell claimed *"no PII… on this row"* **and in the same
  sentence that it was never individually read.** cc found two further sites I
  had not: the `:234` hardcoded `complete: false` and the
  `sairnmechanical.html:1814` toast.
* `msb_bottle_scans` — confirmed at `sairngrounds.html:4771-4779`:
  `ozUsed = ((prior.fill_pct − parsed.fillPct)/100) × bottle_oz`, priced at
  `(match.cost||0)/bottle_oz`, and `fmt(costOfUsage)` is written into
  `rec.note`. **One thing I had that cc's account does not name: `match.cost||0`
  means a product with no recorded cost yields `approx. cost of usage $0.00`
  rather than declining to estimate** — an absent cost and a free pour are
  indistinguishable in the stored string. Routed to cc rather than fixed, since
  they hold it.

---

## 4. Stale docs and tool headers

Found by re-reading at HEAD, not by a tool.

| Where | What it says | What is true |
|---|---|---|
| `tools/gh_token.py` | reads as the token check; `--report` prints source + length | **It never contacts GitHub.** Exit 0 is "a token was found". Honest about what it prints and silent about what it does not test — and it is the file the dispatch pointed at to verify the token *works*. §5 gap 2 |
| `docs/SAIRN-OPEN-WORK-INDEX.md` row 73 | *"NEXT ACTION: repoint `docs/CRITICALITY-TIERS.md:179` from `:218` to `:222`"* | **The citation is not in that file at HEAD.** Closed this session. The defect was real when logged and was closed by an unrelated rewrite of the cell, and **nothing told the row** |
| `docs/2026-09-29-inventory-hank.md` §4 item 1 | *"Four report-only checks are on no cadence… six, in fact"* | **Eight**, and the number is the smaller half of the finding — see §5 gap 1 |
| `docs/2026-09-29-register-cells-hank.md` (mine) | 7 replacement cells, incl. a `mech_docs` name-scoped fix | **Two of its citations had drifted and the `mech_docs` fix was already applied** — `MECH_SCANNED_TEXT` at `api/sd-data.js:14456` already covers all three resources. Found by cc, not by me. **Pasting my own prepared text would have been a no-op at best.** Left standing as the dated record of what was prepared |
| `tools/citation_line_drift_check.py` header, pre-`04abf76e` | *"the nearest one is reported with the signed offset, which is the correction to apply"* | Corrected this session. **It was wrong 4 of 4 on SAIRNgrounds** |
| `tests/run_citation_line_drift_probe.py` arm E2 | *"an offset nobody checked against the line it now names is the same kind of claim as the one being corrected"* | **True, and it did not apply its own sentence one step further back** — it never checked the line the citation *currently* names. Closed by section F |

---

## 5. Gaps found and never logged — ranked

**On the competitor axis, stated before the table because it changes how to read
it:** six of the seven gaps below are internal tooling and process. **No
competitor is affected by any of them and none is visible to a customer**, so
they are not ranked on that axis and no competitor evidence is cited for them,
because there is none to cite. Ranking an internal citation-hygiene gap against
a competitor would be a fabricated axis. Gap 6 is the only product-shaped one,
and **the honest finding there is that I could not establish the competitor
position at all** — see its row.

| # | Gap | Severity | Competitor beating us? |
|---|---|---|---|
| **1** | **Eight report-only checks are absent from the registry built to account for exactly them** | **HIGH** | n/a — internal |
| **2** | **`gh_token.py` is the platform's one credential lookup and cannot say whether the credential works** | **HIGH** | n/a — internal |
| **3** | **The review gate matched a resource name out of comments for the SIXTH time — my own commit prose, this session. Already a row; count corrected** | **HIGH** (as the row has it) | n/a — internal |
| **4** | **No convention requires a SAIRN tool to separate what it MEASURED from what it ADVISES** | **MODERATE** | n/a — internal |
| **5** | `tier_a_review_gate.py` still has no `--reseat` for a record whose file set matches no single commit | **MODERATE** | n/a — internal |
| **6** | A guestbook and a client portal no outside party can reach | **LOW–UNKNOWN** | **CANNOT SAY — and that is the finding** |
| **7** | `leg_clergy` carries `faith_tradition` beside a named individual | **LOW** | n/a — internal |

### 1. Eight report-only checks, absent from their own registry — HIGH

`tools/report_only_checks.py` exists to record, per tool, whether it is promoted
to the push path and **why not** when it is not. Its NOT-PROMOTED entries are
long and genuinely reasoned. Measured at HEAD:

    hover_routing_gap_check      ABSENT from the registry entirely
    hook_integrity_check         ABSENT from the registry entirely
    citation_no_source_report    ABSENT from the registry entirely
    hedge_carry_check            ABSENT from the registry entirely
    pattern_enumeration_sweep    ABSENT from the registry entirely
    idempotence_double_run       ABSENT from the registry entirely
    citation_line_drift_check    ABSENT from the registry entirely   <- mine, today
    message_assertion_audit      ABSENT from the registry entirely

**The count is the smaller half.** Seven of the eight are wired nowhere —
`settings.json` hits 0, push gate 0. The eighth, `hook_integrity_check`, **is**
wired at SessionStart and is *still* absent, **so the registry under-reports in
both directions**: it cannot be read as a list of what is unwired either. A
registry with a hole in it reads as complete, which is the whole defect class
this platform names. Promoted to §4 item 1's successor at **HIGH** from the
earlier "four, six in fact", because the real finding is not the number.

**I added the eighth.** `citation_line_drift_check.py` is report-only, I touched
it today, and I did not wire it or decline it either — recorded here rather than
quietly fixed, because one session adding a registry entry for its own tool on
the strength of one instance is the shape discipline 8 warns about.

### 2. The one credential lookup cannot verify the credential — HIGH

`tools/gh_token.py` was built to remove a seven-week silent failure where two
tools read a 0-byte `.env.local` and nothing said so. It fixed the duplication
and **kept the shape of the original problem one level up**: it answers "where
did a token come from" and is read as answering "is the token good". A revoked
or expired token returns exit 0 with a source and a length.

That is not hypothetical today. The dispatch said `SAIRN-Session55` expires Oct
4 and named this tool as the check. The tool said source + length; the live call
said **no expiration header at all**, i.e. a different, non-expiring credential
is answering. **The tool could not have told anybody that.**

Fix is small and is deliberately not applied by me this session: an opt-in
`--live` that does an authenticated `GET /user` and reports status, scopes and
the expiration header, **COULD NOT RUN on no network** rather than folding that
into either answer. Not built here because four of my seven items were already
overtaken and adding an eighth unrequested change to this batch is guardrail 3.

### 3. The review gate's SIXTH false resource match — HIGH, and already a row

The push gate blocked `04abf76e` naming `grd_irr_zones` and `grd_rounds` as Tier
A resources served by `tools/citation_line_drift_check.py`. **That tool is
report-only and serves no resource at all.** The names were matched out of the
comment and commit prose *explaining the defect* — writing about a resource
registered me as changing code that serves it.

**This is the SIXTH instance** (`quotes` vs *"unbalanced quotes"* in a shlex
comment; `leg_processions` and `msb_sale_hours` vs test fixtures;
`sc_anesthesia_base_units` vs a docstring; four money resources vs a worked
example). **PR §1.2 — grep cannot tell code from text that describes code —
inside the review gate itself.**

**CORRECTING MYSELF: I first wrote that this had never been a row and that I
would make it one. It already is — `docs/SAIRN-OPEN-WORK-INDEX.md` row 78,
opened 2026-09-29, severity HIGH, carrying the five.** I nearly filed a
duplicate of a row I opened myself five days earlier, and only caught it by
reading the neighbouring rows before inserting. **The row's count is updated to
six rather than a second row being added** — which is PR §2.1's reason for
existing running in the direction nobody warns about: not a corrupted row, a
redundant one.

I opened the obligation rather than overriding. That is the cheap correct move
and it is also how the gap stays invisible: every instance is individually
cheaper to comply with than to fix, which is why six of them have accumulated.

### 4. Measured versus advised — MODERATE

This session's own defect, generalised. A tool made a correct measurement ("this
citation is not anchored to a write site") and shipped an incorrect action
inferred from it ("this is the correction to apply"). **No control anywhere
requires a SAIRN tool to keep those two apart**, and the difference is invisible
in the output: both arrive in the same confident sentence.

Carried as `recurrence_open` on the defect record rather than closed by the fix,
and **not written as a convention by me** — a session that just committed the
defect inventing the rule on one instance is a detector blessing its own fix.
**Earns a convention when a second instance is found by somebody else.**

### 5. No `--reseat` for a record whose file set matches no commit — MODERATE

Unchanged from `docs/2026-09-29-inventory-hank.md` §4 item 3. 16 of 22 open
records were in that state because work lands across several pushes. The command
refuses correctly and **there is no path to repair them at all.** Still nobody's.

### 6. A guestbook and a client portal no outside party can reach — LOW–UNKNOWN

`leg_guestbook` entries are typed by staff and shown to nobody outside the firm;
SAIRNbuild's Client Portal has no homeowner link. Same product shape in two
apps: a feature named for an outside audience that cannot reach it. Only the
SAIRNbuild half is written up.

**THE COMPETITOR RANKING THE DISPATCH ASKED FOR CANNOT BE PRODUCED HERE, and
refusing it is the honest answer.** I looked:

* The build/grounds sweep (`docs/superpowers/specs/2026-09-03-…`) does not
  address a client portal.
* The one competitive doc that does discuss a portal
  (`docs/2026-09-15-competitive-gap-status-rederived-mechanical-and-five-apps.md`)
  is about a **different** feature — StoneDesk's Subcontractor Portal — and its
  finding is that the gap **was already built** while two documents still said
  *"Nothing built"*, one of them in its own `##` heading.

So the competitive corpus on this question is **absent for the feature and
demonstrably stale where it is present.** A severity ranked against a competitor
on that basis would be a number with nothing under it. **What is needed is a
scoping read, not a rank** — and it is unclaimed.

### 7. `leg_clergy.faith_tradition` beside a named individual — LOW

Unchanged and still unargued. Tier B. Religious affiliation is a special
category in several regimes; the counter-argument is that a clergy member's
tradition is their advertised professional qualification. **Genuinely arguable,
and nobody has argued it** — the cell has never been individually read.

### Closed since the last inventory

* **§4 item 8** — `redaction.complete` stored and nothing rendering it:
  **partly closed** by cc at `5ab3bcb5`, which found the
  `sairnmechanical.html:1814` toast does say it. The register cell no longer
  asserts the opposite of what the redactor admits.
* **§3 row 6** — `hover_routing_gap_check.py`'s hardcoded header measurement:
  **closed** at `9b23fc27`.

---

## 6. What I will not claim

* **I did not live-verify anything**, because nothing deployed changed. Stated
  rather than omitted — see §1.
* **I did not independently re-verify cc's `5ab3bcb5`.** My derivation of both
  findings agreed with theirs where the two overlap; cc found three sites I did
  not, and I found one detail (`match.cost||0`) they did not name. **That is two
  partial reads that agree, not a review.**
* **I did not run the full guardian check set against this change.** The push
  gate ran and passed, including the copy-exactly pass. The guardian's checks
  are aimed at `*.html` app code; this change is one tool, one probe and three
  documents, and **I am not claiming a sweep I did not run.**
* **I did not count how many of the 32 SAIRNfreedom citations are genuinely
  stale.** The uniform +825/+834 offsets and arm E2 are strong evidence and are
  not a per-citation read. **Nobody has read those 32 cells.**
* **I did not touch the auditor's clone**, including to fix the `:218` reference
  that is sitting there.
* **The 32 contradictory register rows named by `citation_no_source_report.py`
  remain unread by anybody.** Carried from the last inventory unchanged.
