# Hank handoff — 2026-10-15, batch b15, STOPPED EARLY ON INSTRUCTION

**Written BEFORE the report, at a point where nothing is half-edited.** Items
1, 2 and 3 are complete and pushed. **Items 4 and 5 were NOT STARTED** — no
file was touched for either — and item 6's push is done. Stopping was an
instruction, not a conclusion.

---

## A NAMING DISCREPANCY, FLAGGED RATHER THAN RESOLVED SILENTLY

**The wrap-up asked for `SAIRN-handoff-hank-b13.md`, the report
`SAIRN-report-hank-b13.txt` and the digest `SAIRN-digest-hank-b13.txt`.** Those
three files **already exist, are committed, and were uploaded and verified at
the close of batch b13** — and b14's equivalents likewise. This session's live
batch is **b15**.

Writing b15's content into the b13 names would have **destroyed the record of a
closed batch**, so I did not. These artefacts carry the **b15** names, which is
the non-destructive choice and the one that keeps both records true. If the b13
names were deliberate, say so and I will produce them as copies rather than
overwrites. The final chat message keeps the requested wording with the Drive
id of the digest I actually wrote.

---

## Push state — verified, not asserted

    git fetch origin
    git rev-parse --short HEAD        -> 11ffb660
    git rev-parse --short origin/main -> 11ffb660
    git rev-list --left-right --count HEAD...origin/main  -> 0  0

**NOT forced.** No `--force`, no `--force-with-lease`, no `--amend`. **No
override form used** — not `SAIRN_SEED_GATE=off`, not
`SAIRN_GATE_EXEMPT=seed`, not `SAIRN_SKIP`. **Three gate refusals, three
satisfied, zero overridden:** register-feed (two records fed), tier-a (an
obligation opened for `sen_pay_rates`/`sen_visits`), derived-docs
(MASTER-PLAN and traceability-matrix regenerated, never hand-merged).

**The b15 commits on `origin/main`:**

    49f6a752  fix(sairnsenior): F1 an APPROVED clock correction now reaches payroll -- 60 minutes and 2000 cents per visit
    c470c2e1  fix(sairnsenior): the corrections tab hydrates first, and no longer claims an empty queue is empty
    09042c11  chore(defect register): two records for b15
    11ffb660  chore(tier-a,derived): the b15 review obligation and the regenerated documents

---

## Item 1 — fourth b23 F1 and F3: DONE

**F1, and it is money.** `api/_lib/sen-payroll.js` read `row.clock_in_at` and
`row.clock_out_at` **raw** — `grep -c effectiveClock` over that file returned
0 — while `api/_lib/sen-evv-clock.js` says of `effectiveClock()` that the
approval rule is *"implemented HERE, in the function payroll reads"*. Payroll
was not reading it, so an **APPROVED** correction reached nothing. Fourth's
repro: **240 minutes / 8000 cents shipped vs 300 / 10000 corrected** — 60
minutes and 2000 cents unpaid, per visit, per correction.

It is **the mirror of what the same review verified safe**: that review asked
whether an *unapproved* time could reach payroll and drove the answer NO. One
cause — the module never looked at `clock_corrections` — and only one direction
was harmless.

**The substitution is in the MODULE, not the handler's map.** `api/sd-data.js`'s
payroll branch already spreads `x.data`, so the corrections were always on the
row; fixing the map would have fixed one caller of the thing that computes pay.
**Arm P7 drives the real endpoint with its map unchanged** and is the proof.
**The guards run on the effective values** — arm P6 drives an approved
correction that *inverts* a visit: excluded, counted, paid nothing. Substituting
after the ordering check would have been a route around it.

`corrected_clock_visits` is now on each caregiver, so a wage that differs from
the recorded clock can be reconciled against the EVV record.

`api/b15-payroll-effective-clock.test.js` — **RED 8 failed / 3 passed** in a
detached worktree at the pre-fix tree, **GREEN 11/0**. P0 and P3 are the
controls green **both** ways: the uncorrected baseline, and a **pending**
correction still reaching nothing. Without P3 the fix could have been "apply
every correction", which pays an unverified self-asserted time.

**F3, the same defect one layer up.** `sairnsenior.html` read the raw clock ~25
times and used `effective_clock` **zero** times. One helper, `senEffClock()`,
with **two sources in order** — the server's `effective_clock` first, then the
row's own corrections, because a row that has not round-tripped has no
`effective_clock` and a helper that only worked after a hydrate would report
the raw time on exactly the rows a caregiver is looking at.

**Three kinds of site; only two moved.** Duration/money (delivered hours in two
places, `visitHours`, `visitClockReversed`) and display use the helper — and the
display shows **both** values when they differ, because a screen showing only
the corrected value has become the overwrite the trail exists to avoid. The
**clock-action gates stay raw**: whether a clock *event* was recorded is a fact
about the raw field, and substituting would let an approved correction
re-enable the Clock In button on a visit already clocked. The **EVV anomaly
checks are untouched** — that is F2, held for Michael.

`api/b15-client-effective-clock.test.js` — **RED 7/2 → GREEN 10/0**, with C7
and C8 asserting that the two must-not-move classes did not.

## Item 2 — the Stedi backfill step: DONE, and it is deliberately NOT SQL

`docs/2026-10-15-hank-b15-stedi-backfill-step.md`, uploaded as
**`SAIRN-backfill-stedi-step.txt`**, 6,716 bytes, byte-identical on the mount.

**The ciphertext cannot be re-encrypted in Postgres** — the key never leaves
the Node process (`api/_lib/auth.js:874` derives AES-256-GCM from
`sha256(SD_ENCRYPTION_KEY)`). **An UPDATE that put anything into that field
would write a value no reader can decrypt while SATISFYING THE CENSUS**, which
would then report zero and authorise clearing the old key over a destroyed
credential. That is why the answer is an app action.

**The step:** a Compliance Admin re-saves the *same* Stedi key in SAIRNcode's
eligibility panel (`sairncode.html:6068` → `action:'set', service:'stedi'`),
which goes through `api/sc-credentials.js:200-205` and therefore calls
`encryptSecret()` and writes the `v2.` prefix. **The last-4 fingerprint is
compared before and after** so a wrong key cannot be substituted silently, and
`updated_at` must move or the write did not land. Then census PART 1 →
`legacy_rows = 0`.

**If the plaintext is not to hand, the file says STOP** and routes a
server-side re-wrap as a decision needing its own batch — it handles a
decrypted secret and must refuse when `decryptSecret()` returns null, or it
would write the ciphertext of an empty string and take the census green over a
destroyed credential. **I did not build it.**

Every cited line was re-read while writing the file, not remembered.

## Item 3 — hydrate first: DONE for the hydrate half, NOT for the slice check

`renderCorrectionsView()` now hydrates before it renders, and **the empty state
no longer says "Nothing is waiting."** Hydrating alone does not close it:
offline, a 503 or an expired session leaves the same empty list, so the panel
now says when it last reached the server **or that it could not and the list is
therefore not evidence nothing is waiting**. The approve handler no longer
hydrates twice.

`api/b15-corrections-hydrate.test.js` — **RED 3/1 → GREEN 4/0**.

**AND b14's SUITE FIXTURE WAS REPAIRED RATHER THAN THE SPLIT HIDDEN FROM IT.**
The render delegates markup to `_renderCorrectionsRows()`, so lifting only the
entry point threw a ReferenceError — reported as a hard error, which is the
honest signal that a fixture has stopped matching the code. 18/0.

**THE SLICE CHECK WAS NOT BUILT.** See open item 1.

## Items 4 and 5 — NOT STARTED

No file was touched for either. Nothing is half-edited. Both are listed below
with their exact next step, unchanged from the dispatch.

---

## Tests run for the files changed this batch

`docs/hank-evidence/b15/changed_file_suites.log` — **14 suites, all exit 0.**
`api/b14-clock-approval-two-person.test.js` was exit 1 until its fixture was
repaired for the split render, and the log says so rather than showing a clean
sweep.

**Not run:** the full 40-suite sweep, the push gate's own wider checks beyond
what the three refusals exercised, and any live post-push probe. **There is no
live verification for this batch** — stopping came before it.

---

## Open, with the exact next step

1. **THE SLICE CHECK WAS NOT BUILT** (item 3's second half). b14 found two
   false reds, one of them an arm asserting a source line inside
   `slice(at, at + 900)` that went red when comments pushed the line past the
   window. **Next step: a check that flags `slice(x, x + N)` over source text in
   any `*.test.js`, failing-first.** It is the mechanical half of a two-part
   finding and the other half is already closed.

2. **ITEM 4 WAS NOT STARTED.** Four distinct pieces: the Block 2 precondition in
   `sql/2026-10-14-michael-run-order.sql` (the `append_only_grant_audit`
   default-privilege fix) and `api/sd-data.js:1352`; the b13 report citation
   corrections (`api/sd-data.js:13777 -> 14010`,
   `api/sen-auth.js:263 -> 298`, three-vs-four-resources); cody b15's three
   failing `api/` suites in `docs/2026-10-15-cody-b15-fulltree-triage.md`; and
   the possible tenancy defect in `tests/sairnlegacy_fault_probe.py` (`app_id`
   from the client), **to be driven live**. **This has now stalled six
   batches.** Next step: take it as item 1 of b16, and do the tenancy one
   first — it is the only one of the four that is a possible security defect.

3. **ITEM 5 WAS NOT STARTED.** The 22 write branches folding 23514 into
   answer-run-the-migration (2644, 3206, 3567, 4123, 4182, 4431, 4513, 4588,
   8231, 9029, 9224, 10553, 10700, 10899, 11018, 11188, 11265, 11516, 11595,
   13660, 13791, 14348; `:3206` and `:11018` want the 4-arg preread form),
   helper F1 (branch on 23514) and F2 (drop bare `/does not exist/`); the
   **SD_LINEAGE/SD_HR id-shadow pick**, which is mine to make and which b14
   left with three mutually exclusive one-line options; and **ablation records
   for every b14–b15 arm lacking one**. Next step: b16, and the id-shadow pick
   is the smallest piece — b14's report already states the three options and
   why only one can be right.

4. **THE TIER A OBLIGATION IS OPEN**, `sen_pay_rates` + `sen_visits`, assigned
   to **fourth**. The question that matters: **a correction approved AFTER a pay
   run silently changes a historical total**, because nothing versions a paid
   period. `corrected_clock_visits` makes a figure reconcilable and that is
   **not** a restatement trail. **If a paid period must be frozen, this fix
   changes history quietly, which is worse than the underpayment it closes.**
   Also: whether the `require()` I added to a file whose header claims purity is
   defensible as written, and whether `effectiveClock` can throw on any row
   shape `computePayroll` accepts — a throw there takes out a whole pay run
   where the old code excluded one visit. **Next step: fourth discharges.**

5. **AN EVV EXPORT AND A PAY RUN CAN NOW DISAGREE ABOUT THE SAME VISIT.**
   `api/_lib/sen-evv-readiness.js` and the client's EVV anomaly checks still
   read the raw clock — that is **F2, held for Michael by decision**, and I did
   not build it. Nothing reconciles the two numbers. **Next step: Michael
   decides F2; the divergence is acceptable only for as long as F2 is open, and
   that should be a short time now that pay uses the corrected value.**

6. **THE ONE-PERSON-AGENCY SELF-APPROVAL EXCEPTION IS STILL HELD FOR MICHAEL**
   and was not built. A one-person agency has no route to make any clock
   correction effective. **Next step: Michael. If it is granted it must be a
   licence-level setting with an audit trail, not a fallback in the handler.**

7. **THE CENSUS ROW IS STILL LEGACY.** `legacy_rows = 1` on `sc_credentials`.
   **`SD_AUTH_SECRET_PREVIOUS` MUST NOT BE CLEARED.** **Next step: Michael runs
   the step in `SAIRN-backfill-stedi-step.txt`, then census PART 1.**

8. **NO LIVE VERIFICATION FOR THIS BATCH.** PR §3.2 was not satisfied: nothing
   was probed against the deployed URL after the push. The payroll change is
   server-side and behind a licence key, so a credential-free probe could only
   have checked that `sairnsenior.html`'s new helper is deployed. **Next step:
   run `docs/hank-evidence/b14_live_gate_probe.py` extended with
   `function senEffClock` once Vercel has deployed, or state it as unverified —
   which is what the report does.**

9. **FMEA DRAFTS ARE OWED** for `api/b15-payroll-effective-clock.test.js`,
   `api/b15-client-effective-clock.test.js`,
   `api/b15-corrections-hydrate.test.js` and
   `api/b14-clock-approval-two-person.test.js` — the register's own loop said
   `NO DRAFT` for each. `tools/fmea_draft.py` is **cc's**.

10. **TEN `api/` SUITES ARE OWED GATE-DRIVER WIRING** — b12's three, b13's
    three, b14's one and b15's three. Nothing under `tools/` references any of
    them. **`tools/` is cc's.**

---

## Claims held

**`hank`**, taken as the **first action** of this batch and **STILL HELD** — I
did not release it, because items 4 and 5 are unstarted work inside the same
claim and releasing would advertise them as free. **Next session: either
continue under it or release it explicitly.**

    python tools/sairn_claim.py release hank

**Conflicts respected:**

* **`tests/` is cody's.** `tests/sen_evv_payroll_wiring_probe.py` and
  `tests/sen_hydrate_comparator_review_probe.js` were **run, never edited**.
  `tests/sairnlegacy_fault_probe.py` was **not touched at all** — item 4 was not
  started.
* **`tools/` is cc's** — every tool was **run**, none edited.
* **`docs/` triage and routing docs are cody's and fourth's** — read, not
  edited. `docs/batch-manifest-fourth-b23.json` was read to recover F1's
  numbers.
* **No auditor clone was entered.**

Files written outside `api/` and the app HTML: the `docs/` files **the push gate
itself requires** (`defect-density-register.json`, `MASTER-PLAN.md`,
`traceability-matrix.md`, `tier-a-reviews.json`, plus `scrutiny-flags.json`
which the gate writes), my own
`docs/2026-10-15-hank-b15-stedi-backfill-step.md` and
`docs/hank-evidence/b15/`.

---

## Stashes — checked, not assumed

    git stash list
    stash@{0}  On main: b10-settings-park
    stash@{1}  On main: my 3 register records, re-addable from scratchpad/reg_add.py

**Neither was popped, dropped or inspected beyond `git stash list`.** No `git
stash` command of any kind was run. `.claude/settings.json` was **never
committed**; `.claude/settings.json.bak` and `.claude/settings.json.hooks.bak`
remain untracked and were left alone. **No hook was restored or added.**

---

## Transcript

    C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-hank\9ab77c34-c203-458f-9e45-7f384a672a77\

Scratch artefacts there, not committed. Worth keeping:
`scratchpad/reg_b15.py` (the register feed) and `scratchpad/pushloop.sh` (the
pull/push retry loop, which re-derives only the two generated documents and
bails on any other conflict).

**The detached worktree the pre-fix counterfactuals were captured in is
REMOVED:** `wt-b15` deleted with `git worktree remove --force`;
`git worktree list` shows **none** under the scratchpad.
