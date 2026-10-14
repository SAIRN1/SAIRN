# Hank handoff — 2026-10-14, batch b9

Written **before** the report, at a point where nothing is half-finished: all
six items are committed and pushed, `HEAD == origin/main` with no divergence,
every suite green at the published HEAD, and the post-push live probe run
against production with `fail=0`.

**Naming note.** The brief asked for `SAIRN-handoff-hank-b9.md`. It is in
`docs/` because that is where every handoff in this repo lives and because
CLAUDE.md's rule is that a handoff lives only in a real clone — never written to
`C:\Users\marsh\` directly. The filename is the one asked for.

---

## Push state — verified, not asserted

    git rev-list --left-right --count HEAD...origin/main   ->   0   0

No `--force` at any point. `SAIRN_SEED_GATE=off` was **never** used — every
gate refusal was satisfied, not overridden. **Re-verify with
`git log --oneline origin/main`**: five sessions push to this branch and these
shas are current only as of this sentence.

| sha | item |
|---|---|
| `5776ef19` | **item 1** — `schedule` gated, SAIRNscape 12 of 12 |
| `a6fa37a3` | **item 2** — `api/_lib/ai-safeguards.js`, `api/ai-notice.js`, the sd-data gate, the SQL |
| `a428abca` | **item 3** — SAIRNfreedom's four AI disclosures, `ai_source`, the one-time notice |
| `e444dc83` | **item 4** — the three SAIRNsenior asymmetries, and the SAIRNlegacy survey |
| `9733963d` | **item 5** — the seam count de-staled, seven FMEA drafts re-saved |
| `12627753` | the envelope-ordering fix the push gate caught |
| `ecb674aa` | the post-push live probe and its output |

Plus nine register / scrutiny / generated-document commits, one history
rewrite, and **one merge commit** — see *The push* below, because the shape of
that merge is the thing worth carrying forward.

---

## Item by item

### 1. `schedule` gated — DONE, live-verified

b8 closed five SAIRNscape resources and then found the repro had only ever
measured **eleven of twelve** (22 pairs = 11 × 2). `schedule` was in neither
the gate nor the suite's licence-only list, so no arm could see it in either
direction. Michael decided it; it is closed.

**The one fact that had to be read first** was read at this HEAD: `schedule` is
the only SAIRNscape resource whose bare name is also a StoneDesk **panel id**,
and all seven `stonedesk.html` mentions are navigation, not `sd-data` calls.

**It cost the suite its licence-only control**, and that is the part worth
knowing: the loop that drove "what is not gated is still not gated" now has
nothing to drive, and a zero-length loop passes forever. Replaced by an
explicit empty-on-purpose arm, a registry-derived count, and a **cross-app**
arm (`employees` must answer with its OWN gate, not this table's "sign in
first"). 73 arms → 80.

**hover2's repro still reports 22 of 22 FIXED and CANNOT MOVE for this change**,
because `schedule` was never in its 22. The unchanged number is not evidence
about the twelfth resource.

### 2. The AI safeguards — DONE, with one bounded dormancy named

`api/_lib/ai-safeguards.js` holds the policy **as data**. The rule: a record
carrying `ai_source`, on a resource that becomes a document or a decision,
leaving draft, is refused `403 AI_APPROVAL_REQUIRED` unless a session for the
app that **owns** the resource is present — and then the server writes
`ai_approved_by` / `ai_approved_at` from that session, **overwriting** whatever
the payload sent. The precedent is this file's own `sc_auth_requests` sign-off
gate.

**The policy is a total partition.** Every resource in
`AI_SCANNED_TEXT` — the platform's existing, justified list of what stores
model prose — is either high-risk (5) or excluded with a real reason (6), and
`api/ai-safeguards.test.js` fails if one is in neither or in both. A new AI
surface added to that map with no risk decision breaks a test.

`sql/2026-10-14-hank-b9-ai-safeguards.sql` adds `ai_notice_version` (text, not
boolean) and `ai_notice_acked_at` to every credential table, **derived from
`information_schema`** rather than listing sixteen names, and raises if the
loop matches nothing.

`api/ai-notice.js` is **one shared endpoint**, a stated deviation from the
spec's §3.2 (seventeen login payloads). The employee comes from the session,
never the body.

### 3. SAIRNfreedom — DONE

All four AI surfaces label their output (`sfEstimateFill`, `sfMarketSearch`,
`sfOutreachIdeas`, `sfDraftNewsletter`), through one helper. The one record AI
writes carries `ai_source: 'claude:bottle-fill'`. The one-time notice is a
banner, server-state, per-version, hung off `sfEnterApp` after
`sfRenderAll()` and inside a `try`.

`sf_bottle_fills` is deliberately **not** high-risk and the argument is in the
policy file: the app records a binding product decision that fill level is
automatic-only, *"no slider, no tap-to-set, no adjustable guess"*, and an
approve step is a human adjusting the guess.

**The suite found two defects in itself** — a fifth `callClaude(` call site that
was a sentence inside a comment (PR §1.2), and a function name
(`sfMerchSearch`) that has never existed. Both are written into the suite.

### 4. SAIRNsenior + the survey — DONE

`sen_branches` and `sen_settings` reads are tiered by **allowlist**;
`SEN_REFERRAL_RESOURCES` writes moved from `SEN_CLIENT_BROAD_READ_ROLES` to
`MANAGEMENT_ROLES`. A flat role gate would have broken a named screen, so both
reads are minimum-necessary instead.

The survey — `docs/2026-10-14-hank-b9-sairnlegacy-client-authority-survey.md` —
found **5 of 34 match the shape, 0 have a server re-check, 29 have no blocking
guard.** `leg_clergybookings` is the b8 defect with a different resource name,
verified by hand.

### 5. Methodology — DONE

The seam check's COULD NOT TELL is **one seam (`roleSet`) × 19 callers**, not a
pair. The hand-written test it asks for already existed — what was wrong was
the **number**: it said 18 while the tool said 19 and the source held 21. Now
derived and printed.

Seven FMEA drafts saved. The `api/sd-data.js` draft was a **thirty-day-old**
prediction over 57 of 548 register records with the wrong app attributed —
which is why it scored MISSED twice. **And the re-saved draft then returned
`PREDICTED` for item 1's register record, citing rule 1.7.** That is the first
PREDICTED this loop has returned for a hank batch and it is only true because
the draft was re-saved an hour earlier.

### 6. Push — DONE, after six refusals, a history rewrite and a merge

Recorded in sequence because the next session will meet these:

1. **register feed gate** — two `fix()` commits with no record. Written.
2. **generated-document gate** — `MASTER-PLAN.md` and
   `traceability-matrix.md` regenerated with their own generators (PR §2.5).
3. **Tier A review gate** — ten resources. Obligation opened, assigned to
   `fourth`, naming which are substantive and which are negative controls.
4. **`api/preauth-envelope-ordering.test.js`** — a real defect in this batch's
   own new endpoint: `api/ai-notice.js` named its verb vocabulary **before**
   validating the licence. The only `PREAUTH_DISCLOSURE` on the platform, 71
   handlers scanned. Fixed; 0 disclosures now.
5. **`tools/redaction_check.py`** — a test fixture assigned an eighteen-character
   string to a field named `api_secret`, and that matched
   `generic_credential_assignment`. **This paragraph originally quoted the
   line, and the gate refused the HANDOFF for it on the next attempt** — which
   is the detector working exactly as designed and worth leaving in the record:
   a document describing a credential-shaped literal is itself a
   credential-shaped literal, and the pattern cannot tell prose from code. The
   gate reads the
   **added lines of every commit a push would send**, so deleting it later does
   not clear it. The introducing commit was amended and the thirteen after it
   replayed with `git rebase --onto`; verified the string appears zero times in
   the outgoing range. **No credential was rotated** and that is a judgement:
   the value was never a secret, it is a sentence written to be asserted
   ABSENT from a response.
6. **`timeout 170 git push`** — a WRAPPER breaks the pre-push hook's stdin
   exactly as a redirect does. b8 learned "do not redirect a push"; the rule is
   **do not wrap one either**. A pipe to `tail` is fine.

**Then the fifth rebase conflicted on the register at every register commit,
and `tools/sairn_rebase_resolve.py` refused — correctly.** From the ancestor's
point of view a **re-seat** (the same record pointed at a new sha) is
indistinguishable from a delete plus an append, and that tool says so: *"A
union would put every one of them back, which is a different wrong answer, not
a safer one."* Replaying nine re-seat commits asks it the same unanswerable
question nine times. **A merge asks it once**, with both final states in hand:
548 ancestor + 4 upstream + 1 local = 553, merged by that tool and validated by
`--check` before staging.

**Three ref-lock collisions** followed — `cannot lock ref 'refs/heads/main'` —
because the gate takes a minute or more to run and other sessions push during
it. The only remedy is a prompt re-merge and retry.

---

## Live verification — PR §3.2, `fail=0`

`docs/hank-evidence/b9_live_gate_probe.py`, output in `.out`.

| | bare licence key | with a real session |
|---|---|---|
| all twelve SAIRNscape resources | **403 FORBIDDEN** | **200** |
| `employees` (cross-app control) | 403 *its own* gate's words | — |
| `mech_quotes` + `ai_source` | **403 AI_APPROVAL_REQUIRED** | — |
| `mech_quotes`, no `ai_source` | **200** — the over-refusal control | — |
| `api/ai-notice.js` state | **401 NO_SESSION** — deployed | — |
| `leg_bookings` write, no window | **400 BOOKING_WINDOW_REQUIRED** | — |

**THIS PROBE WRITES ONE ROW and b8's header said it wrote none.** Corrected:
`guard=yes residue=docs/live-residue/README.md` — one upserted `mech_quotes`
row, id `ZZ-AI-PROBE-CONTROL`, on the audit licence `MECH-PINNACLE-2026`,
fixed id so re-runs overwrite. It has to write: the only way to tell "refuses
AI-sourced writes" from "refuses all writes" live is to send the same request
without the field and watch it succeed.

---

## Open, with the exact next step

1. **`sql/2026-10-14-hank-b9-ai-safeguards.sql` HAS NOT BEEN RUN.** Until it
   is, `api/ai-notice.js` answers 503 `AI_NOTICE_NOT_PROVISIONED` and no
   employee ever sees the notice. **Next step: Michael runs it in Supabase**,
   then compares the verification query's row count against
   `node -e "console.log(Object.keys(require('./api/_lib/auth').AUTH_TABLE_BY_APP).length)"`
   — 16 at this HEAD, and a figure to re-derive rather than trust.

2. **NO PRODUCTION CLIENT STAMPS `ai_source` ON A HIGH-RISK RESOURCE.** The
   approval refusal is reachable — proven live — but not reached. A server
   cannot look at prose and know a model wrote it, so the field is a claim by
   the writer. **Next step: the first high-risk surface to adopt it.**
   `mech_quotes` is the obvious candidate (its `text` IS model output) and it
   needs a draft/final status the client does not yet send.

3. **A COORDINATOR CAN NO LONGER LOG A REFERRAL.** The write set is
   management-only because that was the instruction. If intake is a
   coordinator's job — and the code's own comment argues it is, for referrals
   specifically — **the fix is a per-resource write map in ONE place**, not a
   return to the broad set. **Next step: Michael confirms or reverses.**

4. **`leg_clergybookings` is the b8 defect, third instance.** **Next step:** the
   b8 fix applied to that branch — a SELECT of the server's non-`Completed`
   rows for the same `clergy_id`, 409 on overlap, and the rollback.
   `api/sd-data.js:15154` is the template. **Do NOT copy its status literal:**
   `leg_bookings` exempts `Cancelled`, `clergyBookingConflict` skips
   `Completed`. Cross-domain convention 7.

5. **The other four survey findings** each need a *different* fix and the
   survey says which. `leg_aftercare`'s cheapest real fix is a **deterministic
   id**, not a gate — a conflict check is the wrong tool when the collision can
   be made impossible by the key.

6. **`rf_settings` (`api/sd-data.js:8757`) has the identical open-read shape
   `sen_settings` just had.** Noticed in passing, **unverified**, not surveyed.
   **Next step:** read it and decide; it is one tier away from the same fix.

7. **`docs/tier-a-reviews.json` — ten resources, assigned to `fourth`.** This
   session cannot discharge its own. The obligation names the four things to
   review hardest, in order.

8. **THE REGISTER HAS SIX DUPLICATE SUMMARIES AND FOUR HAVE NO
   `superseded_by` POINTER.** `--reseat` reported them and refused to resolve
   them — *"deciding which survives is a content question and is not this
   command's to make"* — and it is not this session's either. **None is this
   batch's**; all four are 2026-09-26 to 2026-10-13 from other sessions. **Next
   step: the register's owner picks a survivor per pair and runs
   `--supersede <stale> --by <survivor>`.** Until then four defects are
   double-counted in every figure that file produces.

9. **The FMEA staleness check is ROUTED, NOT BUILT.** Making the loop say
   "this draft is stale" rather than "MISSED" is a `tools/` change and `tools/`
   is cc's. The other drafts in `docs/fmea/` were not audited for age.

10. **The owner-level AI agreement acceptance, the inline Reviewed button, and
    the `ai: true` marker on `api/claude.js`** are specified in
    `docs/2026-10-14-ai-safeguards-spec.md` and **not built**. The spec's three
    questions for Michael are unanswered.

---

## Claims held

**`sairnscape`, claimed and pushed at the start of this batch, still held as
this is written.** Released as the last action, after the final push — so a
reader finding it released should not read that as a contradiction.

**Conflicts declared and NOT overridden:**
`docs/2026-10-14-ai-safeguards-spec.md` and fourth's other b13 docs were
**read, never edited**. `tools/tier_a_review_gate.py`,
`tools/batch_manifest.py` and `tools/drive_upload_verify.py` are in **cc's**
claim and were not touched. hover's b27/b29 files were not touched. **No
`tools/` file was edited by this batch at all.** No auditor clone was entered;
hover2's repro was run read-only from this clone and writes only to a tempdir.

**Two deviations from the claim's FILES list, stated rather than hidden:**
`api/sd-data-sen-session-gate.test.js` was not created — the file is
`api/sd-data-sen-role-asymmetry.test.js`, which is what it is about. And
`tests/sairnfreedom_ai_disclosure.js` was added without being in the list.

---

## Hooks and settings

**No hook was restored or added, and `.claude/settings.json` was never
committed by this session.** It was stashed before the first rebase (and backed
up outside the repo), because a rebase refuses outright with unstaged changes.

**The merge commit does contain a change to that file, and it is upstream's,
byte for byte** — checked with
`git diff --quiet origin/main -- .claude/settings.json`, which was clean.
Taking an already-published version through a merge is the neutral choice;
keeping "mine" would have been this session asserting content for a file it is
instructed never to commit. This session's own modification is still parked and
is restored at the end of the batch.

`.claude/settings.json.bak` and `.claude/settings.json.hooks.bak` are untracked
and were left alone.

---

## Transcript

    C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-hank\66861005-8bc6-4dc0-b30b-e56ad9ef0f85\

Scratch artefacts there, not committed: `b9reg.log`, `b9final.log`, `fmea.log`,
`register_b9.py`, `register_b9b.py`, `fixed-sen-test.js`, `blockcheck.py`, and
the b8 logs. The parked settings copy is in a sibling directory
`a0fa3a3e-b9-settings/`.

**One branch left behind on purpose:** `b9-save-404dae85`, a safety ref taken
before the history rewrite. It still holds the commit carrying the
credential-shaped fixture value, so **it should be deleted** once this batch is
confirmed landed: `git branch -D b9-save-404dae85`. Not deleted here, because
deleting the only copy of the pre-surgery state while the surgery is still
being verified is the wrong order.
