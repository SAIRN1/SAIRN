# SAIRN handoff — hank b24 — 2026-10-20

**Subject:** the IOLTA attestation **proven end to end on the real store** —
Guardian **check 29 satisfied**; a stale present-tense header naming a function
that no longer exists; **two recordable injuries printing as the same OSHA Form
300 case number**, reproduced before it was fixed; a **currency sweep** of my own
skills, tools and methodology against the standing rules, report-only on
everything shared; and an **ablation pass across b18–b23** that found three
suites with no ablation at all and **two more arms passing for the wrong
reason**.

**Written before the report, at a point where nothing is half-finished.** Every
figure re-driven at the landed sha.

---

## 1. COMMITTED AND PUSHED STATE

**LANDED on `origin/main`, `0 ahead, 0 behind` by sha after a fresh fetch.
NOT FORCED. ZERO gate overrides** — no `SAIRN_SKIP`, no `SAIRN_GATE_EXEMPT`, no
`SAIRN_SEED_GATE`.

| sha | commit |
|---|---|
| `44861f237` | `docs(law-reconcile b24)` — the header stops naming a function that no longer exists |
| `5941a119c` | `fix(sairnbiz b24)` — two recordable injuries printed as the same OSHA case number |
| `a49cbddf2` | `test(ablations b24)` — the three b18–b23 suites that had none |
| `864ed5e5d` | `feat(tools b24)` — the attestation PROVEN END TO END, check 29 satisfied |
| `5a1f68302` | `chore(derived b24)` — MASTER-PLAN, TOOLING-INVENTORY, traceability |
| `8847837b4` | `chore(defect register b24)` — the duplicate case number, four factors |
| **`ac4816c29`** | `test(b22-funeral b24)` — **D1 FIRED and it was good news** — re-aimed |

**Artefacts confirmed present on origin by `git cat-file -e`**, not by trusting
the push: `api/b24-osha-caseno-collision.test.js`,
`tools/law_attest_live_probe.py`, `docs/2026-10-20-hank-b24-notes.md`,
`sairnbiz.html`.

### THE GATES, AND ONE REAL MERGE CONFLICT

* **`register-feed` refused**, six attempts in a row, naming `fix(sairnbiz b24)`.
  **Fed, not escaped:** a real record with **four contributing factors**,
  injection commit `fb85a4d95` found with `git log -S sbNextCaseNo` rather than
  guessed, and a `recurrence_open` naming what the fix does **not** close.
  **Two of the four factors are DETECTION, not technical** — the 300A summary
  counts rows and stayed correct, and no arm existed on case_no uniqueness at
  all.
* **`commit_tool_entry_check`** — a `PURPOSES` entry for the new probe naming
  what it **CATCHES**.
* **`path-scope`** — three more `assigned_overrides` entries, each an **exact
  filename**, each with its reason in the manifest, and each marked **remove
  once its owner has reviewed it**.
* **A REAL MERGE CONFLICT in `docs/sairn-path-manifest.json`.** cody's b27 added
  their own override block to the same key in the same hour.
  **`tools/sairn_rebase_resolve.py` REFUSED it** — *"no GENERATED-by
  declaration, a human has to read these"* — which is the right answer for a
  policy file. **Resolved by hand as a UNION**: cody's nine entries and my five,
  nothing dropped, both prose notes kept, and a note added saying the real
  lesson is that a flat map every population appends to during its own batch
  will keep colliding and the entries are meant to be short-lived.
* **A ref-lock race**, twice — *"cannot lock ref: is at X but expected Y"*.
  **Not a gate finding**; another clone pushed mid-upload. Rebase and retry.
* **`docs/defect-density-register.json` was re-stamped by the DOC SHA RE-SEAT
  mechanism** after a rebase moved the fix commit, and that correction was
  amended in rather than fought.

---

## 2. CLAIMS HELD

**Mine, held through the batch, released at the end:**

    hank -> hank   b24: attestation end-to-end live proof on the real store
                   (Guardian check 29); law-trust-reconcile.js stale header fix;
                   duplicate OSHA case_no reproduce+fix+arm; currency sweep of
                   own skills/tools/methodology (report-only on shared);
                   ablation pass across b18-b23 arms; push.

**Held by others, and all three shaped this batch:**

* **cody** → `api/sd-data.js`, `tests/`, `api/b19-iolta-reconcile-carveout.test.js`
  (b27). **Their wiring landed mid-batch and fired my own arm** — see §4 D.
* **cc** → `tools/sabotage.py`, `tools/drive_upload_verify.py`, **`CLAUDE.md`**,
  `docs/fmea/` (b27). **Every currency finding against `CLAUDE.md` is
  report-only because of this.**
* **fourth** → `sairndental.html` (b39). `sairnbiz.html` is **not** in their
  claim, which is why the override was takeable.

**THREE OTHER-POPULATION FILES WERE EDITED, ALL DECLARED:** `sairnbiz.html`
(where the OSHA number is issued, and the dispatch said fix it),
`tests/sairnbiz_incidents_kpi.js` (a harness whose lift lost a dependency
**because of** that fix) and `tools/tooling_inventory.py` + the new probe (the
pre-commit gate refuses a `tools/` addition without a PURPOSES entry).
**Nothing in `~/.claude/` was edited at all**, per the dispatch.

---

## 3. THE SIX ITEMS

### Item 1 — the attestation, end to end. **GUARDIAN CHECK 29 SATISFIED.**

`sql/sairnlaw_trust_attestations.sql` **has been run** — measured, not assumed:
`policy` answered **200** where b23 recorded 503.

> **CONCEPT, before the probe existed.** An attestation is proven only when
> **the row comes back from the database** saying single-signer with one name in
> both places; a one-cent-different comparison is refused against a token signed
> for another; and the single-signer route **stops working the moment a second
> attorney is active**.

`tools/law_attest_live_probe.py` — **28 arms, exit 0**, two real bar-admitted
sessions on `LAW-AUDIT-2026`. The write, **the read-back from the database**,
the boundary **in both directions** (float refused, AGREES-one-cent-apart
refused, unknown field refused, **the same unequal legs with `DISAGREES`
accepted**, duplicate id 409), **the stale-setting refusal with a second
attorney active and the setting still on**, the full two-signer path including
**the row naming the countersigner and not the saver**, a spent token refused,
a token spent on a one-cent-different comparison refused, and a teardown **read
back twice**.

**The residue is permanent and bounded, stated rather than softened:** the table
is granted SELECT and INSERT and **not DELETE**, so nothing can remove an
attestation. The two ids are **fixed constants** — at most two rows, ever.

### Item 2 — the stale present-tense header. **FIXED.**

`api/_lib/law-trust-reconcile.js` said *"`reconcileTrust()` **already compares**
three figures"* and *"**compares** an ALL-TIME ledger balance"*. **That function
does not exist** — deleted when the client was repointed at this module, with
`sairnlaw.html:3287` recording it. The line number `:3134` now points at an
unrelated toast.

**Rewritten rather than deleted**: the dissection is the whole argument for the
file existing, and a reader who cannot find the function it dissects concludes
the argument is about code that is not there. Now past tense, names where the
deletion is recorded, and adds **the half still live** —
`trustLedgerBalance()`/`clientLedgerBalance()` at `sairnlaw.html:3281`/`:3284`
still read one device's store; what was removed is the verdict, not the
arithmetic. Line numbers re-derived with `grep -n`. Suites 33/0 and 12/0.

### Item 3 — the duplicate OSHA case number. **REPRODUCED, FIXED, ARMED.**

Issued at `sairnbiz.html` `sbNextCaseNo(list, year)` — `max+1` over **one
browser's localStorage** — while `sb_incidents` is in `SB_SYNCED` and
`sbServerWinsMerge()` matches rows **by `id`**.

**The reproduction ran red first.** A1 both devices issue 1; A2 after the merge
both rows print `2026-1`; **A3 the YTD count is correct at 2** — which is why
nothing caught it: *the 300A totals are right while Column A is wrong, and an
inspector reads both*. **B1 FAILED before the fix** — a second hole on one
device, where a row with no `year` field was invisible to the max scan.

**The fix:** the date as the year fallback; `sbCaseNoCollisions()`, one finding
per duplicated **number**; and a **DUPLICATE warning rendered in Column A
itself**, because that is where a reader transcribing onto Form 300 is already
looking. **Nothing renumbers** — resolving a duplicate on a filed Form 300 is a
human act.

**25 arms, 0 failed**, three ablations. **The residual is named:** two devices
both offline at the moment of issue can still collide; the complete fix is a
server-side per-year sequence in `api/sd-data.js` — **cody's, routed.**

### Item 4 — the currency sweep. **REPORT ONLY ON SHARED ITEMS.**

| what | standing text | measured 2026-10-20 | verdict |
|---|---|---|---|
| skippable gates | CLAUDE.md: *"eight named gates"* | **11**, and **FOUR DECLARED BUT NOT WIRED** | **STALE** |
| cross-domain disciplines | CLAUDE.md: *"Twelve"* | **39** numbered conventions | **STALE by 27** |
| standing docs over 400kB | CLAUDE.md names **7** | **8**, membership moved | **STALE list** |
| that tool's exit code | *"exits 1 while any exists"* | **exit 1** | **CORRECT** |
| `WRITE_ACTIONS` in the residue audit | 17 verbs | **`attest` absent** | **GAP** |

**THE SHARPEST ONE:** `control-bytes`, `credential-sql`, `register-feed` and
`scrutiny-ledger` are skippable *on paper* — the tool says a skip for them is
**granted and then IGNORED**. **b23 and b24 were each refused by
`credential-sql` and `register-feed`**, so the scoped form would have changed
nothing. Recorded in hank's memory as
`four-skippable-gates-are-declared-but-not-wired`. **Memory also pruned:**
`hank-b1-progress.md` was a checkpoint for a batch 23 batches old — deleted.

### Item 5 — the ablation pass. **SIX OF NINE HAD ONE. THREE DID NOT.**

`b18-countersign-lock`, `b18-passkey-profile-e2e`, `b21-bridge-unknown-action`,
`b22-claude-logline`, `b22-postgrest-filter-encoding` and
`b23-iolta-attestation` carry a real mutation-and-measure mechanism.
**`b19` (cody's, routed), `b20-countersign-open` and
`b22-funeral-f1-f2-f3-wiring` had none.**

**b20: 15 → 20 arms**, three ablations (stage-ladder order → A3; the unspent
filter → D1; `token_hash` in the shared select → C1/C2), plus a `cannot()` that
is a **FAIL and not a third state**, with the reason at the function.

**b22-funeral: 18 → 23 arms**, four ablations — **and F2 failed on its first
draft**, the second instance of b23's F2 class: it ablated a layer that
`decide()`'s earlier DENY already covers, so nothing reddened. Re-aimed, and the
redundant layer is now **asserted as redundant** (`F2b`) so nobody mistakes it
for a control.

**b24's own arms were ablated too, and F3 initially did not redden D2** — the
third instance: D1/D2 were satisfied by a **comment** containing the words they
searched for. Comments are stripped now, with `D0` asserting the strip.

**Every ablation restores its file byte-for-byte** (`md5sum` before and after),
`Buffer`-based, trying the CRLF spelling of each anchor.

### Item 6 — push. **PUSHED WITHOUT FORCE, CONFIRMED BY SHA.** §1.

---

## 4. WHAT IS OPEN, AND THE EXACT NEXT STEP

### A. The F2/F3 module arms should be promoted to handler level — **cody's**

`api/sd-data.js:16702` now passes `legHome` as `decide()`'s fifth argument, so
F2/F3 are consulted on real requests. My arm **D1 was re-aimed to require that
wiring**, so a revert cannot pass unnoticed.

**NEXT STEP:** move b22-funeral's **module-level** F2/F3 arms to **handler
level** — drive the real dispatcher with a `leg_settings` row and assert the
livery and apprentice answers end to end. **cody's wiring, cody's batch; routed.**

### B. The complete OSHA fix is a server-side per-year sequence — **cody's**

**NEXT STEP:** issue Column A server-side in `api/sd-data.js`'s `sb_incidents`
write branch, per `license_hash` + year, and have the client stop issuing it.
Until then the collision is **detected and shown**, not prevented.

### C. Three FMEA drafts are absent and the register said so

The register's own FMEA loop answered **NO DRAFT** for
`api/b24-osha-caseno-collision.test.js` and `tests/sairnbiz_incidents_kpi.js`,
and **MISSED** for `sairnbiz.html` (one draft predates it and none cites rule
1.11).

**NEXT STEP:** `python tools/fmea_draft.py <file> --save` for each. Not run.

### D. The five `assigned_overrides` entries must be PRUNED

**NEXT STEP:** cc reviews the two `tools/` entries and
`tests/sairnbiz_incidents_kpi.js`; fourth reviews `sairnbiz.html`; then delete
them. **An override nobody prunes becomes an allowlist**, and the manifest now
says so in two places.

### E. Four skippable gates are declared and not wired — **cc's**

**NEXT STEP:** wire `control-bytes`, `credential-sql`, `register-feed` and
`scrutiny-ledger` — the tool says it is *"one `gate=` kwarg at that check's
`deny()`"* — or move them out of the skippable list. Right now a `SAIRN_SKIP`
for any of them is granted and ignored, which is the worst of both.

### F. `CLAUDE.md`'s three stale figures — **cc's**

*"eight named gates"* → **11**; *"Twelve standing conventions"* → **39**; the
seven-file over-ceiling list → **eight, with different membership**. All three
are figures CLAUDE.md itself says to measure rather than trust, which is why
they are reported and not edited.

### G. `attest` is absent from `WRITE_ACTIONS` — **cc's**

`tools/live_probe_residue_audit.py` counts the new probe as a writer only
because it also calls `setup`/`set_active`. **NEXT STEP:** add `attest`, with
the reason in the commit, the way `verify` was removed.

### H. Carried forward

`api/b19-iolta-reconcile-carveout.test.js` still carries its expected reds
including b23's A1 (**re-aim, do not delete** — cody's); `api/sd-data.js` still
unswept for the raw-PostgREST-filter class; no rendered pass on the attestation
and **`sairnlaw.html` still has no attestation UI** — the route exists and
nothing calls it.

---

## 5. EVIDENCE — RE-DRIVEN AT THE LANDED SHA

| suite / probe | result |
|---|---|
| `tools/law_attest_live_probe.py` | **28 arms, exit 0 — VERIFIED live, check 29 satisfied** |
| `api/b24-osha-caseno-collision.test.js` | **25 passed, 0 failed, 0 unproven** (new) |
| `api/b20-countersign-open.test.js` | **20 passed, 0 failed** (was 15) |
| `api/b22-funeral-f1-f2-f3-wiring.test.js` | **23 passed, 0 failed** (was 18) |
| `tests/sairnbiz_incidents_kpi.js` | **25/25** — broken to 16/25 by the fix, then repaired |
| `api/_lib/law-trust-reconcile.test.js` | 33 passed, 0 failed |
| `api/_lib/law-trust-reconcile-endpoint.test.js` | 12 passed, 0 failed |
| `api/b18-countersign-lock.test.js` | 59 passed, 0 failed, 0 unproven |
| `api/b18-passkey-profile-e2e.test.js` | 37 passed, 0 failed, 0 unproven |
| `api/b21-bridge-unknown-action.test.js` | 20 passed, 0 failed |
| `api/b22-claude-logline.test.js` | 12 passed, 0 failed |
| `api/b22-postgrest-filter-encoding.test.js` | 9 passed, 0 failed |
| `api/b23-iolta-attestation.test.js` | 66 passed, 0 failed, 0 unproven |
| `api/b19-iolta-reconcile-carveout.test.js` | **28 passed, 4 failed — expected, cody's** |
| sairnbiz script-block syntax | 5 blocks, clean |
| `live_probe_declaration_check` / `residue_audit` | exit 0 / exit 0 |

**WHAT THIS DOES NOT COVER:**

* **No rendered pass.** Nothing visual was looked at; `sairnlaw.html` has no
  attestation UI and the Column A warning was **not** viewed in a browser — it
  is asserted on the rendered string, not on a screenshot.
* **No whole-tree suite run.** Suites were chosen by what the diff touches.
* **The cross-device OSHA collision is detected, not prevented.**
* **`api/sd-data.js` still unswept** for the raw-filter class.
* **Three FMEA drafts named and not written.**

---

## 6. TRANSCRIPT

    C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-hank\f904c24c-ad35-4782-b977-90b0346b7b9e.jsonl

**Context when this section was written: 67.3% — 673,275 of 1,000,000**, printed
by `python tools/context_verify.py --digest-line`, not self-reported.

---

## 7. THINGS I GOT WRONG IN THIS BATCH

1. **My fix broke a green suite and I found it by running it, not by thinking
   about it.** `rIncidents()` gained a dependency and
   `tests/sairnbiz_incidents_kpi.js` lifts the render without it — nine arms died
   on `sbCaseNoCollisions is not defined`, 25/25 → 16/25.
2. **Arm D2 of my own new suite was satisfied by a COMMENT**, and only the
   ablation could see it. Third instance of this class in two batches.
3. **My first ablation of b22-funeral targeted the wrong layer** — the redundant
   second narrowing rather than the early DENY that C3 actually tests. Nothing
   reddened, and I nearly recorded that as "the layer is not load-bearing"
   instead of "my anchor is in the wrong place".
4. **I read `tail`'s exit code and reported it as the tool's.** The first
   measurement of `--standing-doc-sizes` said exit 0; the tool exits 1.
   Re-measured, and CLAUDE.md was right.
5. **I wrote the register record four times before it validated** — wrong
   `--factors` form, then a field the method does not accept, then two invalid
   enum values. The tool refused each time rather than storing a half-record,
   which is the gate working; the waste was mine for not reading a stored record
   first.
