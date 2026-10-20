# Handoff — cody, batch b30, 2026-10-20

**Six items. Three done, one diagnosed and routed because another session holds
the file, one HELD on instruction, one is the push.** Pushed and verified by
reading the remote; every suite green.

---

## 1. THE SIX ITEMS

| item | state | what that means |
|---|---|---|
| **1. cap per (resource, action)** | **DONE — 18 arms, 7 red under ablation** | The gate covered **1 of 38** declared verbs. Now fail-closed on every verb except `read`, and `rt_routes` keeps its ~109KB legitimate payload |
| **2. the dangling b27 citation** | **DIAGNOSED, EDIT ROUTED to fourth** | **fourth holds the register on a live claim and refused my first claim on exactly that file.** The hard half is done: the target is confirmed by the record's own numbers, and the trap is that subject AND patch-id both point at the wrong commit |
| **3. split the 795KB log** | **DONE — 795,238 → 372,166 live + 395,093 + 33,368** | **Two attempts refused before one was right**, and the second refusal found that this log has two formats in it |
| **4. CLAUDE.md:33** | **HELD, as instructed** | cc has not called it. Nothing in b30 touches `CLAUDE.md` or the skill |
| **5. state the concept first** | **DONE** | §1 of `docs/2026-10-20-cody-b30-notes.md`, and in the code at each site |
| **6. push, no force** | **DONE — see §2** | Read back off the remote |

---

## 2. Committed and pushed state

| | |
|---|---|
| commits | **TWO.** `a0504cd8cadf b30(cody): the payload cap now belongs to the (resource, action) pair, and an append-only log split that refused twice before it was right`, plus one squashed bookkeeping commit |
| pushed | **LANDED AND VERIFIED BY READING THE REMOTE.** **Tip `9d198c8929ac`, `0 ahead / 0 behind`.** `a0504cd8cadf` proved an ANCESTOR with `git merge-base --is-ancestor`; eight files read back off the remote tree at the expected sizes. **PUSHED WITHOUT `--force`** |
| claim | `platform`. **My FIRST b30 claim was REFUSED** — fourth held `docs/defect-density-register.json`. Re-claimed without it, with the routing declared in the task string. The refusal is recorded in `.claude/claims/cody.json` |
| overrides | **NONE.** No `SAIRN_SKIP`, no `SAIRN_GATE_EXEMPT`, no `SAIRN_SEED_GATE` |
| SQL / live writes | **NONE of either** |
| boundaries | **`docs/defect-density-register.json` NOT touched** (fourth's, live claim) — routed. **`CLAUDE.md` and `.claude/skills/` NOT touched** — **HELD on instruction**, which is stronger than unclaimed. **`tools/` NOT touched** (cc's) — three RUN. No `sql/`, no `.html` |
| path override | **REPLACED, not extended** — eight of b29's eleven paths dropped, three remain |

---

## 3. Item 1 — the gate covered one verb class of thirty-eight

**THE CONCEPT:** a payload cap belongs to the **(resource, action) pair** that
writes, because *which verb writes* is a fact about the handler and *how big a
row may be* is a fact about the table — and the gate asked **neither**. It read
`if (action === 'write')`.

cody's own b29 finding. **38 declared verbs across 77 resources bypassed the cap
entirely.** `rf_invoices` carries `rfinv_data_size <= 262144` and writes only
through `issue`, `add_payment`, `reconcile_claim` and `gl_export`: not
under-capped, **uncapped**, so a 10MB payload reached Postgres and came back as
an opaque constraint error.

**IT IS FAIL-CLOSED ON THE VERB, AND THAT ORDERING IS THE SAFETY ARGUMENT.** The
gate caps **every action except `read`** rather than every action on a declared
list, so a verb misclassified in `ACTION_CLASS` is **still capped** — a wrong
entry costs a comment, not a hole. `read` is excluded because a read payload is
a filter; capping it would be a new restriction on something that was never the
defect. **Arm G4** is that boundary.

**Three-step resolution in one function** (`payloadCapFor`): the
`(resource, action)` entry → b28/b29's per-resource entry → 64KB. Step 2 is why
the six resources b28 and b29 capped now keep those caps on **every** verb
instead of only on `write` (**G5**).

**THE ONE PLACE "THIS BREAKS NOTHING" FAILS IS `rt_routes`, WHICH IS WHY STEP 1
EXISTS.** `upsert` and `optimize` carry the whole stop **list**:
`api/_lib/routes.js` permits 200 stops (`:464`) with 500-character addresses
(`:470`), so a full route is **109KB measured** of legitimate payload and the
64KB default would have refused it — **the regression b29 declined to ship
blind.** **R1** sends the real 200-stop payload; **R2** proves the ceiling is a
cap and not an exemption; **R3** asserts `reorder` is deliberately absent,
because *"we forgot reorder"* and *"reorder does not need it"* look identical in
a table.

**THE CLASS MAP IS A DECLARATION AND ARM M1 IS WHY THAT IS HONEST.** Deriving it
was tried first and **the derivation is not trustworthy** — it reported
`consolidate` as having **no branch at all**, and `reserve` and
`release_retainage` as compute-only. So `ACTION_CLASS` is declared by hand with
a **load-time completeness assertion that throws**, and **M1 runs the rejected
derivation anyway** and pins the disagreements at exactly three: a new
disagreement means a new blind spot or a changed class, and one that
**disappears** means the pin is stale.

---

## 4. Open — every item, why, and the exact next step

### 4.1 → fourth. The register reseat: target CONFIRMED, edit not mine

**fourth holds `docs/defect-density-register.json` on a live claim** and that
claim refused my first b30 claim on exactly that file.

**THE TRAP, AND IT IS WHY THIS WAS WORTH DOING CAREFULLY.** The dangling
`ce15ddaa6a3c` is not an ancestor of `origin/main`. Two candidates carry a
b27(cody) rt_routes subject, and **both the subject and the patch-id point at
`977bec59a` — which is not on `origin/main` either.** Matching on either would
have re-seated the record onto a second commit that names nothing.

**THE DECIDING EVIDENCE IS THE RECORD'S OWN MEASUREMENTS.** It names
`['api/_lib/routes.test.js', 'api/_resources/index.js']` and
`lines_added 287, lines_removed 0`:

    git show --numstat 864e6b764 -- api/_lib/routes.test.js api/_resources/index.js
    -> 239  0      and      48  0        = 287 added, 0 removed

**Exact match on the files the record itself chose to name.** `864e6b764` is the
squash that reached `origin/main` and b27's handoff recorded it as the work
commit proved an ancestor.

**NEXT STEP — two fields in the record whose `commit` is `ce15ddaa6a3c`:**

```json
"commit": "864e6b76490904c6649f5a45eaa6c86b35bab080",
"subject": "b27(cody): rt_routes made reachable, three routed role changes, and three routings that were incomplete"
```

**The subject must move with the commit** — the register's check matches on
subject as a fallback, so leaving the old wording makes the record fail for a
different reason. Nothing else changes. Then
`python tools/defect_register.py --check` should drop from 1 problem to 0.
**`--reseat` will not do this and that is by design:** it refuses a record whose
commit resolves locally but is not an ancestor, because automating it would pick
a sha out of a reflog. **RED AT HEAD before b30**, recorded in b29 §4.5.

### 4.2 → cody, next batch. `rf_invoices` is capped at the DEFAULT, not its own ceiling

Item 1 made it capped; it did not make the cap right. `rfinv_data_size` is
**262,144** and the verb now falls to the 64KB default, so a legitimate invoice
larger than 64KB is refused where the table would accept it. **Next step:**
measure the largest real `issue` payload (a live read on the audit licence, as
b29 did for `sd_locations`), then add
`PAYLOAD_CAP_BY_RESOURCE.rf_invoices = 262144` and an arm. **Not done blind:**
raising a cap without measuring is how b29's notes describe the opposite
mistake.

### 4.3 → cc, and the FIVE things I most want broken

`docs/tier-a-reviews.json` carries the obligation, **assigned to cc**, over six
Tier A resources. The one I least trust is **(b)**: *is 700 bytes per stop
really the worst case for a 200-stop route?* `job_ref`, `accuracy_m` and
`status` have no length bound I checked, and **arm R1 uses short `job_ref`s and
would not see a longer one.** If that is wrong, a legitimate route is refused
and my own arm cannot tell.

### 4.4 → HELD. `CLAUDE.md:33` and the handoff skill

**3 of 86 handoffs** follow the documented convention. b29 routed the correction
to cc with pasteable text; **b30's instruction was to hold until cc's next
report settles it**, and nothing here touches either file. **It is getting worse
at roughly three files a day** — 80 at b28, 83 at b29, **86 now** — which is the
one fact worth carrying: the cost of holding is measurable and small, and
acting unilaterally on a shared standing document is the thing being avoided.

### 4.5 `api/_resources/extra-actions.test.js` is 41/7 RED AT HEAD

**Not caused by b30** — proved by stashing both b30 source files and re-running
to the identical 41/7. b26 registered it known-red at exactly that figure.
**Next step:** it is the suite that drives `checkEnvelope` for ~20 assertions,
so its 7 reds are worth a read before the next change to `EXTRA_ACTIONS` —
b30 added a sibling structure (`ACTION_CLASS`) in the same file and did not
touch what those arms assert.

### 4.6 → cody. My push-retry loop accumulates commits

The push gate writes `docs/scrutiny-flags.json` on **every** attempt, and my
loop commits whatever the tree holds each round — so four lost races produced
four near-identical bookkeeping commits over one file, **squashed into one
before the push landed**. b29 was refused by the duplicate-subject gate for the
same loop; naming the files stopped the subjects colliding but not the commits
accumulating. **Next step:** stage the gate's write-back into the SAME commit
with `--amend` rather than a new one per round.

### 4.7 → Michael. Nothing is blocked on you

No SQL is owed and no decision is required to proceed. One decision is pending
with **cc** (§4.4) and one review obligation is **assigned to cc** (§4.3).

---

## 5. Verification — every line is a command that was run

```
EXIT=0  node --check api/sd-data.js  api/_resources/index.js
                     api/b30-cap-per-action.test.js

RED BEFORE, GREEN AFTER (ablation: the b30 source change stashed, suite re-run)
  item 1   api/b30-cap-per-action.test.js      7 arms red  ->  18/0

EXIT=0  node api/b28-photo-cap.test.js                23, regression
EXIT=0  node api/b29-rt-stops-hash.test.js             7, regression
EXIT=0  node api/b29-funeral-f2-f3.test.js            21, regression
EXIT=0  node api/b29-error-detail.test.js             11, regression
EXIT=0  node api/b29-law-reconcile-prepare.test.js     8, regression
EXIT=0  node api/_lib/routes.test.js                  63, regression
EXIT=0  node api/b19-iolta-reconcile-carveout.test.js 38, regression
EXIT=0  node api/b22-funeral-f1-f2-f3-wiring.test.js  23, regression
EXIT=0  node api/b27-leg-settings.test.js             18, regression
EXIT=0  node api/sd-data-cross-tenant-dispatchers.test.js 418, regression
EXIT=0  python tools/md_table_check.py                all files clean
EXIT=0  python tools/sairn_path_manifest.py --outgoing     IN SCOPE
EXIT=1  python tools/tooling_inventory.py --standing-doc-sizes
        7 over the ceiling, WAS 8 -- cody's log is no longer one of them

ITEM 3, THE SPLIT, VERIFIED BY MULTISET AND RE-READ FROM DISK:
  before  795,238 bytes, 215 entries, multiset 23779075228a6557
  after   SAIRN-ACTIVE-WORK-cody-closed-1.md  395,093   79 entries
          SAIRN-ACTIVE-WORK-cody-closed-2.md   33,368    9 entries
          SAIRN-ACTIVE-WORK-cody.md           372,166  127 entries
          multiset 23779075228a6557 over the UNION of all three, read back
          from disk after the write

RED AT HEAD, NOT CAUSED BY b30:
EXIT=1  node api/_resources/extra-actions.test.js  41/7  -> §4.5
EXIT=1  python tools/defect_register.py --check    1 dangling citation -> §4.1
```

**TWO REFUSALS BY MY OWN SPLIT SCRIPT, AND THE SECOND IS THE FINDING.** Attempt
1 (one archive part) refused: no single cut leaves both files under the ceiling
— fourth hit the identical wall on 2026-10-12. Attempt 2 refused on *"not even
one section fits the live file"*, **because what it treated as a document header
is 425,249 bytes.** That is not a header: this log has **two formats in one
file** — 88 bullet entries in the original format and 127 dated `## ` sections.
**A script that guessed instead of refusing would have written a live file still
over the ceiling and reported success.** The bullets archive and the sections
stay live, which is both the right size split and the right editorial one.

**ONE GATE REFUSED THE PUSH AND IT WAS SATISFIED AT CAUSE:** `tier-a`, over six
Tier A resources with no open obligation. Record **opened**, assigned to cc,
naming five things to try to break rather than a summary.

---

## 6. Scratch, transcript and where the detail is

* **Concepts, both refusals, and item 2's confirmation with the pasteable
  change:** `docs/2026-10-20-cody-b30-notes.md`
* **The new suite:** `api/b30-cap-per-action.test.js`
* **The split:** `SAIRN-ACTIVE-WORK-cody-closed-1.md`, `-closed-2.md`, and the
  note at the top of the live file
* **Transcript:**
  `C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cody\cc73112b-c907-4081-b7af-37c09862bb32.jsonl`
  — this window carries **b28, b29 and b30**; b30 begins at the dispatch naming
  the six items and the 85% hard wrap-up rule.
* **Wrapped at 78%**, measured with `python tools/context_verify.py
  --digest-line`, against the 85% hard trigger. b27 wrapped at 92% and had to
  revert a half-finished item; b29 at 69%.
