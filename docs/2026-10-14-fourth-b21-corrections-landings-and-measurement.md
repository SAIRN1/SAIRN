# b21 — the b19 correction, the step-4a routing, the land-checks, and the citation measurement

**fourth, batch b21, 2026-10-14.** Everything here was **measured in this
batch**; the batch was then stopped at 70% context before these could become
separate documents, so they are recorded together rather than lost.

---

## 0. CLOSED BY MICHAEL — and I will stop raising it

**Michael ran and verified all six blocks of
`sql/2026-10-14-michael-run-order.sql` on 2026-10-14 at 19:38 ET, blocks 5 and
6 included.**

**That closes "run-order blocks 5/6 UNVERIFIED", which I raised in b20's
verdict, report, digest, handoff and latest-file.** It is recorded here as a
fact of record and **is not to be raised again.**

**What it means for b20's finding, said properly rather than just retracted:**
b20's leg-role-matrix verdict said the 36-resource matrix was *"today a gate
nobody can populate, and the only role anybody can hold is the deprecated
one."* **That was true when written and is now false.** The five SAIRNlegacy
task roles and SAIRNcare's `office_manager` are accepted by the live CHECK, so
the matrix b20 verified as a faithful transcription is now **populatable and
in force.** The same applies to the `office_manager` note in this batch's
sv-role-matrix discharge, which is marked closed there.

---

## 1. ITEM 3 — the b19 item-5 undercount, corrected

**MY b19 FIGURE WAS "roughly twelve". THE REAL FIGURE IS 63, ACROSS 22
RESOURCES.**

**H1 re-ran my own command and got what I should have got:** **242 raw
matches**, of which **63 narrow to the 503-folding shape** — the
`if (r.status === 404 || r.status === 400) { ... 503 NOT_PROVISIONED }`
pattern — **across 22 resources.** My b19 and b20 documents said "twelve
branches" and b20's report repeated it as a measured number.

**The correction, and the lesson is the one that keeps recurring in my own
work:** I counted `grep -n "status === 404 || r.status === 400"` hits **in one
reading of one file region**, called it twelve, and then **carried the twelve
forward across three documents as though it had been measured.** A figure
quoted once becomes a figure trusted thereafter. **63 is 5.25x twelve**, so the
blast radius of the 400→503 misattribution I routed to hank is five times
larger than I told them.

**ROUTED TO hank, with the number corrected:** the 400→503 misattribution is
not a dozen branches, it is **63 across 22 resources**. That changes it from a
tidy-up into a pattern worth one shared helper rather than 63 edits. **The
`sd_photos` instance remains the one with a live consequence** (b19's size
finding), and the other 62 are the same wrong diagnosis waiting on a different
resource.

**AND THE METHOD NOTE THAT MATTERS MORE THAN THE NUMBER:** H1 found this by
**re-running my command**, not by reading my prose. **A figure with its command
printed beside it is auditable; a figure without one is a rumour.** My
documents did print the command — which is the only reason this was findable —
and **the command was right while my count of its output was wrong.** So the
convention needs one more clause: **print the command AND the raw count, not
just the conclusion.** 242 raw / 63 narrowed is a sentence nobody can
mis-carry.

---

## 2. ITEM 3 — step 4a in the operator runbook: the content is mine, the mechanism is cc's

**The task said "cc's `secrets_inventory.py` step 4a is fixed; the doc is
yours." Both halves are true and they do not meet, and this is the finding.**

### cc fixed two of three places

```
CMD grep -n "4a\|legacy_ciphertext_census" tools/secrets_inventory.py
   74:  # ── STEP 4a RESTORED 2026-10-14 (cc b11), ROUTED BY fourth b18 ──
   89:  'SD_AUTH_SECRET_PREVIOUS': (... '(4a) CONFIRM NO LEGACY CIPHERTEXT
        REMAINS -- run sql/legacy_ciphertext_census.sql and require
        legacy_rows = 0 on every table it reports, per api/_lib/auth.js:442-445;
        (4b) only then clear this value' ...)

CMD grep -n "4a\|legacy_ciphertext_census" tools/nhi_register.py
  335:  # STEP 4a RESTORED 2026-10-14 (cc b11), routed by fourth b18
  344-345: '... (4a) CONFIRM NO LEGACY CIPHERTEXT REMAINS -- run
           sql/legacy_ciphertext_census.sql and require ...'
```

**Both the inventory and the register's `SD_AUTH_SECRET_PREVIOUS` identity
entry now carry step 4a. That is cc's fix and it is real.**

### The third place still omits it, and it is the one I routed

**`docs/NHI-REGISTER.md:69` is the `### session-signing` REVOKE paragraph** —
the operator-facing runbook, and the line my b18 and b19 findings named. Its
source is `tools/nhi_register.py:374-376`:

```
'current secret, change SD_AUTH_SECRET, wait one SESSION_TTL_MS '
'(12h), clear PREVIOUS. The dilemma above -- certain cost against '
'an uncertain compromise -- is GONE, ...'
```

**"wait 12h, clear PREVIOUS" — no 4a.** So the identity entry warns and the
**procedure an operator would actually follow still does not.**

### Why I did not hand-edit the doc

```
CMD head -3 docs/NHI-REGISTER.md
  **GENERATED by `python tools/nhi_register.py --write`. Do not hand-edit.**
CMD python tools/nhi_register.py --check            ->  EXIT 0
  OK: docs\NHI-REGISTER.md matches the repo.
```

**The document is generated and currently matches its generator.** A hand-edit
would be reverted by the next `--write` and would make `--check` fail — turning
a stale paragraph into a drift alarm. **The staleness is in `tools/`, which is
cc's, and PR §1.8 says a generated document is not hand-written.**

**So: the prose is mine and is below; the one-line generator edit is cc's.**

### ROUTED TO cc — the replacement sentence, ready to paste

> *"…so a rotation no longer logs anyone out: set PREVIOUS to the current
> secret, change SD_AUTH_SECRET, wait one SESSION_TTL_MS (12h) for every old
> token to expire, **then — and this is the only irreversible step — CONFIRM NO
> LEGACY CIPHERTEXT REMAINS by running `sql/legacy_ciphertext_census.sql` and
> requiring `legacy_rows = 0` on every table it reports (step 4a, per
> `signingKeys()` in `api/_lib/auth.js`), and only then clear PREVIOUS.**
> Clearing it ends the only route to a legacy ciphertext for good, and
> `decryptSecret()` then returns null, which a caller reads as 'no secret
> stored' — silent as well as permanent."*

**AND A SECOND DEFECT IN THE SAME PARAGRAPH, found while re-deriving it:** it
cites **`api/_lib/auth.js:365`** for the line that accepts
`SD_AUTH_SECRET_PREVIOUS` on verify.

```
CMD sed -n 365p api/_lib/auth.js
  // THE LIST LIVES IN THREE PLACES and that is a real drift risk, named here
CMD grep -n "push(process.env.SD_AUTH_SECRET_PREVIOUS)" api/_lib/auth.js
  510:  push(process.env.SD_AUTH_SECRET_PREVIOUS);
CMD grep -n "function signingKeys" api/_lib/auth.js
  491:function signingKeys(app) {
```

**The real line is `:510`, inside `signingKeys()` at `:491`.** The replacement
sentence above therefore **anchors on the function name and not on a number** —
b20's lesson applied in the one place I am authoring.

---

## 3. ITEM 4 — the land-checks

### cc b12 — **SKIPPED, by the instruction, because the claim is ACTIVE**

```
CMD python tools/sairn_claim.py list | grep '^\[active.*cc '
  cc   b12 drive status bridge; runbook-constant guard; wire 2 hank suites;
       fmea drafts; cody b11 followups.
       FILES: ... tools/drive_upload_verify.py ...   (0.6h ago)
```

**`tools/drive_upload_verify.py` is in that live FILES list**, which is the file
the F3 probe arm is about. **So the WRONG AGENT token re-point and
`run_drive_upload_verify_probe.py`'s 35/35 are in flight and were NOT graded.**

**EXACT NEXT STEP: after cc b12 closes, run
`python tests/run_drive_upload_verify_probe.py` and expect 35/35 at exit 0.**
b20 measured it at **34/35, exit 1**; anything other than 35/35 means the arm
was re-pointed at a different sentence rather than at the token.

### hank b12 — **NOT LANDED**, measured

```
CMD python tools/sairn_claim.py list   ->  hank: 0 active claims
CMD ls SAIRN-handoff-hank-b12.md SAIRN-report-hank-b12.txt   ->  neither exists
CMD grep -n "downscale|canvas|toDataURL|drawImage|maxDim|resize" stonedesk.html
      | grep -i photo                                        ->  no photo-path hit
CMD grep -n "ai_source" stonedesk.html
  42249:  ... ai_source:'claude:review-request' ...   (the REVIEW LOG row, not sd_photos)
CMD grep -n "sd_photos" api/_lib/ai-safeguards.js api/_lib/ai-scan-redaction.js
                                                            ->  no match
```

**So: no client-side downscale on the photo path, no `ai_source` on the
`sd_photos` row, `sd_photos` still in neither AI registry, no b12 artifacts,
and no claim in flight.** **hank b12's `sd_photos` work has not happened** —
it is not blocked, it is not closed, it is pending.

**EXACT NEXT STEP, unchanged from b19 and worth repeating because the ordering
is the actionable part: the SIZE fix first, with T17's `ai_source` stamp landing
WITH or BEFORE it** — fixing size alone makes every photo land and turns the
latent provenance gap live on the same day.

**One thing the check did find:** `ai_source` **has** reached StoneDesk, on the
review-request log row (`claude:review-request`). **So the convention is being
adopted in the app; it just has not reached the resource with the open
finding.**

---

## 4. ITEM 5 — the citation-staleness measurement, and my own measurement corrected

**Script:** `<scratchpad>/citation_staleness_b21.py`, **read-only, writes
nothing**, run twice. **Not added to `tools/` — that is cc's directory.**

### The loose pass, and why its headline number is MINE and not the register's

```
CMD python <scratchpad>/citation_staleness_b21.py
  total line citations found                 551
    no file named on the line (bare, no ctx)  59   not counted either way
    named file absent from this clone          5   "provably stale"
    line beyond the end of the file            9   "provably stale"
    lands on a BLANK or pure-comment line     72   likely stale, not proof
    lands on a code line                     406   NOT VERIFIED
```

**Then I measured my own measurement, and the 14 "provably stale" collapsed.**
For a bare `` `:NNNN` `` the script attributes the citation to the **nearest
preceding file token on the line**, and that heuristic is wrong often enough to
manufacture findings:

```
CMD doc line 163, around the :10582 citation
  '... `commsEnsureIds()` back-fills a CONTENT-DERIVED id ... Verified
   reachable: three call sites at `:10582`, `:10618` and `:10649`.'
```

**Those three cite `stonedesk.html`. My script charged them to
`tools/confidentiality_candidate_flagger.py` — an 893-line file — and reported
three "BEYOND-EOF provably stale" citations that are nothing of the kind.**

### The strict pass — explicit `file:line` only, no attribution guessing

```
CMD the same script, FILE_CITE matches only
  total explicit citations                   196
  named file absent from this clone            0   PROVABLY STALE
  line beyond the end of the file              0   PROVABLY STALE
  lands on blank / pure-comment line          37   LIKELY STALE, not proof
  lands on a code line                       159   NOT VERIFIED
```

### THE ANSWER, bounded

| | |
|---|---|
| **total line citations in `docs/CRITICALITY-TIERS.md`** | **551** (663-line document) |
| of those, **explicit `file:line`** | **196** |
| of those, **provably stale** | **0** |
| of those, **landing on a blank or pure-comment line — likely stale** | **37 of 196, 19%** |
| **bare `:NNNN` citations whose target must be INFERRED** | **355**, and **the inference is unreliable — demonstrated, not supposed** |

**So the honest headline is: 0 provably stale, 37 likely stale of 196
checkable, and 355 unassessable because the citation form does not name its
file.** The b20 report's claim that *"hundreds exist"* is confirmed — **551** —
and b20's refusal to extrapolate from the `sf_events` row's 7-of-7 was right:
the register-wide provable rate is **zero**, not seven-sevenths.

**AND THE REAL FINDING IS THE FORM, NOT THE RATE: 355 of 551 citations — 64% —
cannot be mechanically checked at all**, because a bare `:NNNN` does not say
which file it belongs to. **That is the strongest argument yet for the anchor
form specified in b20's rot-check spec**, and it reframes that spec's R3:
**counting surviving `file:line` citations is not enough; the bare ones must be
counted separately and reported as UNASSESSABLE rather than folded in.**

### The second half: my own b20 docs, audited for prose-grepping

**Audited all five b20 artifacts. Exactly ONE real instance, and it is mine:**

```
  SAIRN-report-fourth-b20.txt:693
    CMD grep -ci "force|forced|+ refs" over the push log      ->  0
```

**My "the push was not forced" claim was established by grepping git's HUMAN
OUTPUT WORDING for the words "force" and "forced".** If git rewords its
forced-update line, that check silently passes. **It is the exact defect I
routed to cc about their probe arm, in my own evidence, in the same batch.**

**FIXED THIS BATCH, by method rather than by wording — the token-grade check is
ancestry:**

```
CMD git merge-base --is-ancestor f3c7612a HEAD
  ANCESTOR -> fast-forward, not forced
```

**A non-forced push means the pre-push tip is an ANCESTOR of the new tip. That
is a property of the graph, not of a sentence**, and it is what this batch's
push confirmation uses.

**The other four grep-based claims in those documents are fine and I checked
each:** `grep -rn "WRONG AGENT|NO AGENT NAMED"` matches the **labels**, which
are the tokens; `grep -c '^CONTEXT'` is a field name anchored at line start;
`grep -m1 -E '^#\s*OWNER:'` is a convention token anchored the same way. **Four
tokens, one sentence — and the sentence was the one carrying a verification
claim.**

---

## 5. UNVERIFIED

1. **The 63 / 242 figures are H1's re-run of my command, not my own re-run.** I
   accepted them and corrected the record; **I did not re-execute the grep
   myself this batch.** The 22-resource breakdown is likewise H1's.
2. **"37 likely stale" is not 37 stale.** Landing on a comment line is strong
   evidence, not proof — a cell may legitimately cite a comment.
3. **The 159 "lands on a code line" are NOT verified correct.** They exist and
   are not blank; whether each holds the construct its cell names needs the
   cell read, which is judgement.
4. **The 355 bare citations are unassessed**, by design, because assessing them
   needs the attribution heuristic that just produced three false findings.
5. **cc b12 was not graded** (§3), by instruction.
6. **The step-4a generator edit is routed, not made** (§2).
