# Handoff — cody, batch b21, 2026-10-16

**Written BEFORE the report**, at a point where **everything is committed except
this file and the two artefacts that follow it**. Nothing is half-edited: both
index rows are rebuilt or patched with their pipe count asserted either side,
the shards are regenerated and `--check`ed CLEAN, convention 37 is landed with
its membership question asked and answered, and `METHODOLOGY.md` carries the
promotion row and a re-measured count block.

**THE HEADLINE: A DECISION I WAS ASKED TO RECORD TURNED INTO A CORRECTION OF MY
OWN b20 FINDING.** Michael decided the §45B floor is $5.15 and that the IRS
page's $7.25 is the error. Recording that honestly meant naming the one cheap
check still outstanding — read Form 8846's own wage line — and **running it
settled the point and changed the shape of the finding: $7.25 is a REAL §45B
figure belonging to the beauty-service limb, so the page's error is a MISPLACED
LIMB and not a wrong number.** The decision is confirmed by an employer-facing
IRS form rather than only by a statute reading.

---

## 1. Committed state

| | |
|---|---|
| commits | **`f5a9138e`** `chore(claims): cody claims platform` and **`cae2791e`** `docs(b21): Michael's $5.15 decision…` |
| claim | `platform`, taken **BEFORE any work**, published to `origin/main`. **STILL HELD as this file is written** — §5 |
| overrides | **NONE.** No `SAIRN_SKIP`, no `SAIRN_GATE_EXEMPT`, no `SAIRN_SEED_GATE`, in any form |
| boundaries | **NO `api/`, `sql/` or `tools/` file edited.** `open_work_shard.py`, `index_duplicate_check.py` and `tier_a_review_gate.py` were **RUN**. No hook restored. `.claude/settings.json` never committed. No auditor clone entered |
| HOLD honoured | **`api/sd-data.js:14445` and `:2851` are HANK's and were NOT touched** — declared in the claim string as a hold rather than left implicit, and no `api/` file is in the diff |
| Stripe | **NO further Stripe work of any kind.** No object created, no Vercel environment read, no dashboard opened |
| committer | `fx <fx@example.invalid>`, this clone's local config, unchanged |

**Files in `cae2791e` — six, all under `docs/`:**

```
docs/2026-09-17-sairnfreedom-tips-tax-treatment.md    +§12.6a, +§12.6b, §12.8 corrected
docs/2026-10-16-cody-b20-sairncash-billing-live-status.md   status re-headed, hold recorded
docs/SAIRN-OPEN-WORK-INDEX.md                         2 rows: 224 re-worded, 896 rebuilt whole
docs/open-work/ACTIVE.md | sairncash.md | sairnfreedom.md   regenerated
docs/2026-09-13-cross-domain-disciplines.md           +convention 37
docs/METHODOLOGY.md                                   +promotion row, +count block
```

---

## 2. Item by item

### ITEM 1 — the $5.15 decision, and the better finding it produced

**§12.6a records the decision.** $5.15/hour, the FLSA minimum as in effect on
**January 1, 2007**, per **§45B(b)(1)(B)** and **IR-2007-155**. The IRS *FICA
Tip Credit for employers* page's **$7.25 / July 24, 2009** is recorded as that
page's error and is **not followed**. **The paragraph §12.6 originally closed
with is carried unchanged beneath it** — it declined to call the page wrong, and
that caution is the reason the decision is safe to make: the disagreement was
documented with both sides quoted and dated before anybody chose between them.

**§12.6b is the outstanding check, run.** Form 8846 (2025) carries **two
floors, one per limb of §45B(b)(2)**:

> **Food or beverage employers.** … the federal minimum wage rate **in effect
> on January 1, 2007, of $5.15 an hour.**
>
> **Beauty service employers.** … the federal minimum wage rate **currently in
> effect, of $7.25 an hour.**

**The 2025 expansion to barbering, hair care, nail care, esthetics and body/spa
brought its own UNFROZEN floor, and nothing in the research above knew that.**
So the decision is confirmed on the face of the form the credit is claimed on,
and the page's defect is precisely located.

**AND A PRECONDITION IS RECORDED WHERE THE NUMBER WILL BE READ:** the floor is
a **function of which limb**, not a constant. **A single hardcoded `5.15` is
right for a canteen and silently wrong for any beauty-service employer**, and
this platform has fifteen other apps. Nothing computes a §45B figure today and
§7.3's warning against building toward the credit is unchanged.

**STILL NOT CHECKED, said rather than skipped:** `irs.gov/instructions/i8846`
returned **HTTP 404** this session, so the separate instructions document was
not read. The form's own text is the stronger source here.

### ITEM 2 — SAIRNcash is CODE-COMPLETE, BLOCKED ON BUSINESS SETUP

Both the status doc and the index row now lead with it, and **all three
remaining items are marked ON HOLD BY DECISION, NOT BY OVERSIGHT.** The "next
step" column is re-headed **"next step WHEN THE HOLD LIFTS"** and every row
carries **HELD**, so the table cannot be read as a queue to work.

**WHY THE WORD MATTERS AND IS NOT A LABEL** — it is in the doc because it is
the reusable part: *"incomplete"* points an engineer at the repo, **and the repo
is finished.** A status that sends somebody to look for missing code costs a
session every time it is read, and that row has been read at least three times
across b19 and b20. **"Blocked on business setup" points at the thing actually
blocking and tells the next session to STOP rather than start.**

**The index row was REBUILT WHOLE**, never by splitting on a pipe, pipe count
asserted at 8 either side. Old cells struck through and kept — it quoted
`{"error":"Stripe not configured"}`, **a string that no longer exists as a
response** — and the half of its old next-action that still stands (the
estimator regression is still blocked) **is said to still stand** rather than
dropped.

### ITEM 3 — HELD, and nothing was done

`api/sd-data.js:14445` and `:2851` are hank's. Declared as a hold in the claim
string; no `api/` file in the diff.

### ITEM 4 — the §9 index row, re-worded on Michael's instruction

b20 routed this and **deliberately did not take it**, because re-wording another
session's open-work row to carry my own answer is the edit this platform has
least tolerance for. **Michael's instruction removes that objection — the
finding is mine.**

Headline, status, owner and next action all replaced, **old text struck through
and kept.** The row now leads with Rev. Rul. 2003-64's holding and states where
the ruling **stops**: a §501(c)(7) ruling against a usually-(c)(19) post, with
§512(a)(3) not applying to (c)(19) — **and Pub. 3386 makes that live rather than
academic**, because a veterans' organisation running a bar, restaurant or
canteen for members *may be recognised under IRC 501(c)(7)*; and the ruling has
one activity serving two classes of customer where §9.1 posits two activities.

**AND THE ROW'S OWN "SECOND HURDLE" CLAIM IS CORRECTED RATHER THAN DELETED.**
It published that limiting the credit to tips *"received from CUSTOMERS OR
CLIENTS"* might be self-defeating for a member buying a drink in their own
post's canteen. The same ruling answers it. **The superseded sentence is kept
struck through, because the row published it and a published claim needs a
correction and not a silent overwrite.**

**Residuals went from TWO to ONE**, and the row and the document both say so.

### ITEM 5 — convention 37, and this file. ITEM 6 — the push, §6

---

## 3. The methodology item

> **37. A TWO-SOURCE CONFLICT IS UNDER-DETERMINED — the resolving source is the
> one the quantity is USED on, and when both sides turn out correct the error
> was in your MODEL of the subject.**

**The instance is this session's own published finding from one batch earlier.**
A defining source and a describing source cannot settle each other: the
definition says what the number should be, the description says what somebody
published, and **neither says which POPULATION the number applies to.** The
arbiter is the **operational artefact** — the form, the config, the table the
value is read out of — because that artefact has to name the population to be
usable at all.

**The second half is the harder one: both sides of the conflict I documented
were CORRECT.** The statute quote was right, the page quote was right, and the
model was one amendment stale. **§7.4 of the tips document already listed the
beauty-service limb and never asked whether the limb had its own floor** —
which is the whole distance between having the fact and having the model.
**Writing a conflict down carefully is exactly what makes it feel resolved**, so
a well-documented conflict reads as understood and a misdiagnosis inside one is
invisible.

**The checkable form:** name the population each source addresses; find the
artefact the quantity is read out of and check whether it carries **more than
one** value for what you assumed was one; and ask **what would have to be true
for BOTH sources to be correct** — if that state is possible, the conflict is
not established and your model is the first suspect.

**MEMBERSHIP ASKED AND ANSWERED: 37 IS NOT A MEMBER of the cannot-fire group
and the group stays at TWELVE** — nothing failed to fire, both sources spoke
correctly, so it sits beside 21, 22 and 35 as a measurement fault. **36 was
asked and ADMITTED, 37 was asked and REFUSED, both on the same day**, and the
note says so because reading the pair together is the clearest statement of
where that group's boundary is.

---

## 4. Verification — exit codes from `echo "EXIT=$?"` on its own line, never a pipeline

```
EXIT=0  python tools/open_work_shard.py --check    CLEAN, 813 rows byte for byte
EXIT=0  python tools/tier_a_review_gate.py          nothing to record
EXIT=1  python tools/index_duplicate_check.py       3 similar-row pairs
                                                    -- PRE-EXISTING, see below
```

**STRUCTURE MEASURED BOTH WAYS:** **851** table rows and **1,005** lines in
`docs/SAIRN-OPEN-WORK-INDEX.md` **before and after every edit**; pipe count
**8 → 8** on both touched rows; row 224 grew 4,278 → 9,146 chars and row 896
was rebuilt 326 → 3,082.

**THE DUPLICATE CHECK'S EXIT 1 IS PRE-EXISTING AND WAS MEASURED, NOT ASSUMED.**
Stashing this diff and re-running at HEAD gives **the same exit and the same
three pairs** — SAIRNgrounds 144/145, Tooling 255/257, Platform 295/299. **None
is a row this batch touched** and none is fixed here.

**CONVENTION COUNT:** 37 headings, **1–37, no gap, no duplicate**, counted
before assigning; **25** promotion rows in `METHODOLOGY.md`.

---

## 5. Claims held

**`platform`, taken BEFORE any work, STILL HELD as this file is written**,
because the push in §6 has not happened and **a claim released before the work
lands is a claim that was never true.** It is released with the report and
digest, and the report records the release.

**Nothing was inherited:** b20's claim was released at the end of b20.

---

## 6. Open — every item, why, and the exact next step

### 6.1 → NOBODY, AND THAT IS THE POINT. SAIRNcash is HELD

**Do not pursue any Stripe item until Michael says go.** The three held items —
`STRIPE_PRICE_ID` presence, whether the present key authenticates, the
billing-portal token design — are recorded with what the step *would* be, under
a column heading that says so. **A session that picks one up has misread the
row.**

### 6.2 → THE POST's CPA. One question, one line

**Is this post's canteen held under §501(c)(19) or a companion §501(c)(7)?**
It decides which authority is on all fours, because §512(a)(3) does not apply
to (c)(19) and Rev. Rul. 2003-64's facts run through it.

### 6.3 → WHOEVER COMPUTES A §45B FIGURE, IF ANYONE EVER DOES

**The floor is a function of which limb of §45B(b)(2) the service falls in.**
$5.15 frozen for food and beverage; the current federal minimum, $7.25 today,
for the beauty-service limb. **A hardcoded constant is wrong for one of the
two.** Nothing computes this today and §7.3 says not to build toward it.

### 6.4 → WHOEVER WANTS THE LAST CHEAP CHECK ON THE WAGE FIGURE

`irs.gov/instructions/i8846` returned **HTTP 404** this session. The Form 8846
*instructions* document was never read. **Not a gap in the conclusion** — the
form's own text is the stronger source and it is quoted — but it is the one
unread thing on this point.

### 6.5 → HANK. Unchanged from b19/b20, and NOT re-sent

`api/sd-data.js:14445` raw 503 → `await notProvisioned(res, w, <same message>)`
(arms A2/A3 drive it on a copy); then decide what distinguishes a 42703 from a
404 at `:2851`. **Re-derive both line numbers.** A third guard is named and not
driven: `:14316`. **The index row added in b20 is still the live routing.**

### 6.6 → CC. The Tier A obligation opened 2026-10-16T12:24:12Z. cody cannot discharge its own

### 6.7 → WHOEVER OWNS THE THREE DUPLICATE INDEX PAIRS

SAIRNgrounds 144/145, Tooling 255/257, Platform 295/299. **Pre-existing, not
mine, measured rather than inherited as a claim.** `index_duplicate_check.py`
will keep exiting 1 until somebody merges or marks each pair.

### 6.8 → NOT TOUCHED IN b21, named so it is not mistaken for done

The b17/b18 carry-overs are exactly as b19 and b20 left them: `tooling_inventory
--hooked` failing open on an empty hook set; the two claims probes' retyped-task
fixtures; `sairnbuild.html`'s bare `catch(e){}` in `st()`; six named
`recurrence_open` register records; `run_capa_fields_probe.py`'s 200–420s
per-arm 2.46MB register rewrite; b16's three deterministic ablation arms. **And
the 151/67 sibling `NOT_PROVISIONED` guards are NOT converted — a decision, not
a backlog** (cross-domain item 7).

---

## 7. Scratch and transcript

**Transcript:**
`C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cody\0f5c2c46-aab3-44b3-997b-47c60e2fbcce.jsonl`

**Scratch:**
`C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-cody\0f5c2c46-aab3-44b3-997b-47c60e2fbcce\scratchpad\`
— `reword_row.py`, `patch_row_8846.py`, `reword_cash_row.py`, `add_row37.py`,
`conv37.md`, `pdftext.py`, `f8846.txt`, `rr2003-64.txt`, `p3386_v2.txt`,
`cash_probe.py`, and the commit messages.

**No worktree was created this batch.**
`C:/Users/marsh/AppData/Local/Temp/gate-probe3-17976` is registered against this
clone, is **not mine**, and was left alone. The 109 files / 247 MB that `rm` has
refused across b14–b16 are still at the b16 path, listed in
`SAIRN-handoff-cody-b16.md` §6. **Nothing in the repo or on the Drive depends on
any of them.**

---

*Written before the report, at a point where everything above is committed
except this file and the two artefacts that follow it.*
