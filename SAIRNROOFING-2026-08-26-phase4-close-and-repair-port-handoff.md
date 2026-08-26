# SAIRNroofing — Phase 4 closed, the read bug, tax provenance, and the repair-vs-replace port (CC, 2026-08-26)

Closing handoff. This session is being wound down; the likely next owner is
**Cody**, who owns the repair-vs-replace implementation this session ported
into.

**Read §5 first if you are short of time — it is the only part with unverified
code in production.**

Commits, in order:
`0df5699` · `ee2411f` · `4d86518` · `7d7708e` · `0de4c66` · `b044f35` ·
`1bf062a` · `3f17236` · `a7103a3`

---

## 0. A correction I owe, made before it got written down as fact

At the end of the port I told Michael that
`sql/sairnroofing_settings_schema.sql` had not been run and that `assess_damage`
and `rf_settings` were returning 503 in production. **That was wrong.** Cody's
`03791f2` ran the migration and live-verified the base implementation 24/24 on
`RF-PINNACLE-2026` — all three outcomes on real data, both refusal branches
against real config, and the density rule proven live (12 hits over 3 squares =
4/square, correctly below an 8 threshold).

I asserted a provisioning state from the last thing I had read rather than from
the log. Checking `git log` for a verify commit would have taken one command.
**What is genuinely unverified is narrower and is in §5.**

---

## 1. Phase 4 is complete (4a, 4d, 4b, 4c)

4c was the last piece: the **Reports panel**, five CSV exports plus Proposals.

The gate is **inherited, not re-asserted** — each report calls the ordinary
gated read for its resource, so a CSV cannot contain a row the caller could not
open on screen. Structural, not a remembered rule. **Zero new lines in
`api/sd-data.js`.** A server-side `export` action was rejected deliberately: it
would put the gate in two places that must agree forever, the shape
`api/rf-auth.js`'s own header records SAIRNsenior drifting on.

Proposals (`b044f35`) is the one report whose read is per-job, so it fans out
over visible jobs — **bounded at 6 in flight, disclosed not silent**, and any
job that fails is **named** rather than quietly missing from a file that looks
complete.

Gate proven against a narrow role, not asserted: `rf-verify-fmA` sees Jobs
1-of-8, Claims 0-of-1, Schedule 0-of-1, Certifications 0-of-3, Invoices **403**.
Rows visible to the foreman but not the owner: **0**. In the browser the
Invoices button is **absent from the DOM**, not disabled.

---

## 2. The bug that mattered most — `rfDataRaw` returned `d.data` (`ee2411f`)

`rfDataRaw` set `data:(d&&d.data)` while its sibling `rfAuth` sets `data:d`, and
**every consumer was written against rfAuth's convention** (`r.data.<field>`).
A read body is `{ok,provisioned,data:[...]}`, so `r.data` *was* the rows array
and `r.data.data` was `undefined` on every call.

Latent from Phase 2 (`31e0337`), where callers were writes touching only
`r.ok`/`r.msg`. **Live from Phase 3b.** Thirteen consumers across Phases
3b/4a/4b/5 silently rendered empty: schedule, locations, invoices, proposal
state, agreement chain, agreement status (×2), programmes board and its
`roster_size` footer, the claim ACV note, and both invoice-issue toasts.

**Every one of those phases passed live API verification.** `curl` exercised the
endpoint; nothing exercised the page. An empty panel reads as "no data yet".

**The fix was not one line, and assuming it was would have regressed.** Audited
per call site: OLD 0/13 correct, NEW 13/13, zero regressions. That is how the
claim ACV note surfaced as the **one** consumer correct under the old
convention — a *write* reply nests its record under `data`
(`api/sd-data.js:2994`) while reads and compute actions sit at the top level.

---

## 3. Tax provenance (`b044f35`) — broader than open-work row 141 recorded

Three failing cases, not one. Money correct in all; only provenance wrong.

| Expressed | Write decided | Every read reported |
|---|---|---|
| rate 7.5% only | `basis=rate` | `basis=amount`, rate lost, **spurious** "both were given" warning |
| nothing at all | `basis=none` | `basis=amount` — an explicit tax of zero nobody entered |
| rate **and** amount | `basis=amount` **+ warning** | warning **silently dropped** |

The third was new and worst: the one case where the warning is *true* is the
case it vanished.

Root cause was at the storage boundary, not in `computeTotals` — the write
persisted the **derived** tax and the read fed it back as an input.
`taxFieldsToStore()` now stores the *question*, not the answer. Live-verified
against the deployed API, all four cases plus the proposal branch, **0
failures**.

---

## 4. Repair-vs-replace was built TWICE the same night

Cody's shipped; **mine was deleted, not merged** (`git reset --hard`, nothing of
mine ever reached `origin/main`). Full comparison:
`docs/superpowers/specs/2026-08-26-repair-vs-replace-two-implementations.md`.
Lesson and prevention: `2026-08-26-parallel-duplicate-build-lesson.md`.

The prevention shipped into `sairn-parallel-app-scaling` (`3f17236`), applied to
**both** the canonical store and the tracked copy, verified byte-identical,
`verify-skill-store.sh` **CLEAN, exit 0**: `git fetch` then grep
**`origin/main`**, not the working tree. The duplicating session *did* grep
correctly — against a tree level with origin *at that moment*, before the other
clone's commit landed.

**Reading my comparison would have saved me a full feature.** Cody's density
model was right where mine was wrong: mine compared the raw count to the
threshold, so 12 hits over 3 squares would have read as 12 against a threshold
of 8.

---

## 5. ⚠ WHAT IS NOT LIVE-VERIFIED — the only unverified code in production

`a7103a3` landed **after** Cody's `03791f2` verification run. **These three
changes have never been exercised against production:**

1. **The strict photo rule.** A count now reaches `meets_threshold` only if a
   photo backs the slope; unbacked counts report in full as
   `insufficient_evidence`. Binds `meets_threshold` **only** — `below_threshold`
   still reports without a photo, deliberately.
2. **Server-verified photo ids.** `api/sd-data.js` reads `rf_claim_photos` for
   the claim; an id resolving to nothing returns **by name** in
   `unresolved_photo_ids`. **The highest-risk piece** — it adds a fetch to the
   hot path and changes outcomes based on its result.
3. **`material_unavailable`** — `discontinued_material` no longer returns
   `meets_threshold`.

**Test coverage is real but is not production**: 28 engine + 18 endpoint + 24
registry passing, every roofing suite green.

**The specific thing to check first**, because it is the one that fails
silently and in the dangerous direction:

> An **absent** `rf_claim_photos` table must read as *cannot-verify*, NOT as
> *nothing-verifies*. Passing `[]` on a 404 would silently downgrade every
> assessment on a licence whose photo table was never provisioned. The endpoint
> passes `undefined` and the result reports
> `photo_verification: 'not_verified'`, with the panel saying so in red. Unit-
> tested both ways; **never seen against a real 404.**

Suggested live run, reusing `rf-verify-admin` (still active, §6): a slope citing
a real `RFCPH-` id → `meets_threshold`; the same slope citing an invented id →
`insufficient_evidence` with the id named; a `discontinued_material` slope →
`material_unavailable` and `summary.meets_threshold === 0`.

---

## 6. Open items

1. **`rf_settings` threshold row has `source: "SYNTHETIC verification"`** —
   Cody's own note flags this as *itself* the unsourced-number problem the
   engine exists to prevent. Both options are written out commented in their
   cleanup file. **Product decision, still unmade.**
2. **`rf-verify-admin` is still active** on `RF-PINNACLE-2026` (PIN in
   `sql/sairnroofing_verify_admin_seed.sql`). Its seed file's cleanup was never
   run. Used by this session and Cody's; deliberately left.
3. **Open-work row 141 can be closed** — the tax-provenance fix is live-verified.
4. **Row 142 (duplicated signature pad, `rfSigInit`/`rfPropSigInit`)** — still
   open, still drifting.
5. **Two doc drifts on origin, logged not fixed** (both Cody's files): the
   patent boundary comment says the action and UI "are in progress" when
   `4d4410f` landed them; and the IP screen's §5.1 still reads *"do not build a
   repair-vs-replace indicator"* while it is built and pushed.
6. **`extra-actions.test.js` was failing on `origin/main`** since `4d4410f` —
   `assess_damage` registered without updating the suite that exists to catch a
   new verb. Verified in a clean worktree of `origin/main` before touching it,
   then fixed in `a7103a3`. Worth knowing that suite is *meant* to fail on a new
   verb; answer it, don't route around it.

---

## 7. The methodology point, which outlives every item above

**Every real defect this session was found by opening the artefact** — the
rendered panel, the downloaded file — never by the operation reporting success.
Two separate bugs had a green success message sitting directly on top of them:
thirteen dead reads under five phases of passing API tests, and a Jobs CSV that
announced *"Exported 8 jobs — 7 columns"* with a blank identifier in every row.

Corollaries earned the hard way tonight:

- **A claimed-but-unbuilt feature invites a second person to build it.** The
  boundary comment's past-tense claim is why repair-vs-replace was built twice.
- **A cleanup or migration is not done when it is run; it is done when its
  result is queried back.**
- **Verify against `origin/main`, not your working tree** — for features, and
  for failing tests before you adopt them as your own.
- I was wrong twice tonight in the same shape (a counter "regression" that was
  per-branch numbering working correctly, and §0's provisioning claim). Both
  were asserting state from memory instead of querying it. **The correction is
  usually worth more than the original finding.**
