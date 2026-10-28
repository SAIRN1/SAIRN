# SAIRN handoff: cc, batch b64, 2026-10-28

**All five items are closed.** The registry check found one real missing rule,
`sen_branches.read`. It is now declared and verified live.

| | |
|---|---|
| Landed | `11bf769f` (items 1–3) and `08345692` (Tier A discharges); see the digest for the final tip. The clone reads 0 0 against origin. No `--force`, no override, no skip. |
| Claims held | `field-scope` (b64, released with this handoff). An earlier `platform` claim was **refused** because fourth holds it for the push-timeout guard and hook wiring, with no shared files; the refusal row is committed (`73ad93c3`). |
| Context | see the digest's CONTEXT line (measured) |
| Transcript | `C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cc\332ab89b-94aa-4880-931e-d17413636dfc.jsonl` |

## 1. Item 1: CLAUDE.md now says 85%

- The line "Wrap up at 80%" now reads **85%**, citing the source: Michael's
  2026-10-20 change, commit `0ac259bf`.
- It names the two constants that enforce it:
  - `tools/builder_context_watch.py` `THRESHOLD = 85.0`;
  - `tools/sairn_status_line.py` `RED_AT_BUILD = 85`.
  It says to read those constants if the prose and the code ever disagree.
- The "remaining 20%" became 15%.
- The b25/b26 breach sentence now says it was "the 80% rule then in force".
- **Left alone on purpose:** three dated notes still mention 80% as a record of
  their own day — `docs/2026-10-20-cc-b27-notes.md`,
  `docs/2026-10-20-cody-b28-currency-sweep.md` and
  `docs/2026-10-20-fourth-b38-currency-sweep.md`. They are history, not
  standing documents.

## 2. Item 2: the registry at full scope

**What the existing checks said:**
- `--validate`: 0 schema errors.
- Handler mode clean at HEAD and at origin/main.

**What the wider look found:** discovery only ever read one-line
`resource === 'x' && action === 'y'` dispatch. That means **26 compound branches
`(action === 'read' || …)` were never scanned.**
- Widened to read compound branches, it found **`sen_branches/read`**: a real
  tier (management gets the row, everyone else gets id/name/state/active) that no
  rule covered.
- It also produced two false positives, from the `'MISSING_FIELDS'` error code
  and the write-side `SV_LOCAL_ONLY_FIELDS`. The "fields" signal is therefore now
  a field list being APPLIED: `_FIELDS.forEach(` or `delete out[`.
- `validate()` now also refuses two rules that make the same request.
- The blind lock went from 20 to **22**: a compound two-line dispatch is seen,
  and an error code is not a redaction.

**The new rule, `sen_branches.read`:**
- Declared from the b9 design, with a live block on SEN-AUDIT-0002.
- Its fixture row is in
  `sql/field_scope_live_fixture_sen_branches_2026-10-28.sql`, generated from
  `seed()`. It was rehearsed (always-rollback), then RUN.

**Results:**
- Handler mode: **27/27**.
- Live on sairn.vercel.app: **27/27, exit 0**.
- Replay at the real pre-tiering commit `e444dc83^`: LEAK of address, phone,
  updatedBy and updatedByRole to scheduler, coordinator and caregiver.
- An ablated tier is caught too.

**Still NOT covered — ROUTED:**
- `alf_family_contacts/family_mar`. The FAMILY_FIELDS projection lives in
  `api/_lib/alf-family-mar.js`, and the action is not read-named, so discovery
  does not see it. It needs a rule (hank, sairncare).
- Data-returning non-read actions in general: readiness, wip, board, portfolio,
  gl_export, payroll and others. They are outside discovery, and that is
  disclosed in the tool's header.

## 3. Item 3: the 12 credentials round-trip in the format other tools expect

**The platform's shared credential-lookup format** is `tools/demo_credentials_check.py`'s
`{app, endpoint, license_key, employee_id, pin}`, read from a local gitignored
file.
- I wrote all **17** audit credentials in that schema to
  `scratchpad\audit-creds-0002.local.json`: the 5 for SEN-AUDIT-0002 plus the 12
  for RF and ALF.
- I ran `demo_credentials_check.py --file <that>` against production: **17/17
  OK**, each returning the expected role.
- No PIN was printed; the tool guarantees that.

**Stored rows, compared in the database:** all three licences have the same
shape — 128-character hash, 32-character salt, active, 0 failed attempts, none
locked.

**`--live` itself:** it signed in with all 17 (27 arms).

**One mismatch, informational, NOT changed.** Older per-app live probes use
different environment-variable names:
- `tools/alf_facility_role_gate_live_probe.py` uses `ALF_LICENSE`, `ALF_EMP` /
  `ALF_PIN` and `ALF_MEDAIDE_*`;
- the roofing probes use `RF_LICENSE`, `RF_EMP` and `RF_PIN`.

The field-scope tool uses `<APP>_AUDIT_LICENSE` and `<APP>_<ROLE>_EMP|PIN`
across all three apps, the same as SEN-AUDIT-0002.

**Do NOT point those write probes at the `*-0002` licences.** They write rows
(for example ZZ-GATE-FAC), and the field-scope judge needs a closed-world,
fully known fixture table. They should stay on RF-AUDIT-2026 and ALF-AUDIT-2026.

## 4. Item 4: Tier A obligations assigned to cc

**How the open set was read.** The union view of `tools/tier_a_reviews_store.py`
(the legacy file plus shards) showed **6 open with `reviewer_owner = cc`**, and
one more was opened today. fourth's earlier `dnt_gfe` / `dnt_credentials`
assignment was already discharged (record 273, 2026-10-20).

**How each was reviewed:**
- Five reviews were done by read-only agents that cc dispatched. Each one ran
  the suites and drove ablations in temp copies.
- cc spot-checked the key claims against the code:
  - `write_batch` has no per-action cap;
  - `encodeURIComponent` leaves `)` raw.
- hank b60 was reviewed by cc directly.
- Each was discharged with `tier_a_review_gate.py --discharge`.

| Obligation | Verdict | The finding that matters |
|---|---|---|
| hank b51 `76193dc9` family_mar grantee gate | SOUND-WITH-GAPS (low) | N6 proves only that the message differs. **Outside the diff (MEDIUM, a decision for Michael):** `alf_clients/read` gives billing and activities the resident's free-text **medications and diagnosis**. |
| hank b52 `6a3755ca`+`29739fe1` | SOUND-WITH-GAPS (low-med) | An HTTP **400** on the leg_ settings read proceeds on the default. Driven: an apprentice read of `leg_bookings` returns 200 ALLOW. `[]` does clear (driven) but no test asserts it. |
| hank b53 `8e617d19`+`dbbf43b6` | SOUND-WITH-GAPS (**MEDIUM**) | `write_batch` `in.(ids)` leaves `)` raw. A 400 is then treated as "not provisioned" and **a tombstoned customer is resurrected** (driven on a grammar-faithful mock; live UNVERIFIED). Also, `sd-sub-data.js:443`'s compliance gate runs only on create. |
| hank b60 `cdf71e89` readiness projection | the diff is SOUND; gap **MEDIUM**, pre-existing | `summarize()` looks up `caregivers[v.assigned_employee_id]`, but the map is keyed by `caregiver_id`. **Every real assigned visit reads "caregiver record could not be found."** The b60 fixture masks this by using the same id for both. |
| cody b52 `7e794838` (=`d8f47f7a`) | SOUND-WITH-GAPS (low) | Exponent-form numbers are under-counted, by up to ~320 bytes. |
| cody b53 `a46ed992` (=`f45edc2c`) | **UNSOUND (MEDIUM)** against its own criterion | The 64KB whole-request cap refuses `sd_customers` `write_batch` at about 140 realistic customers: a 413, and the only sign is a console.warn, so the customer list silently stops syncing. **Pre-existing HIGH:** the ceiling was about 150 before this commit. |

**Remaining items:**
- **cody b19 (2026-10-16)** is already discharged in the legacy file the gate
  reads (cc, 2026-10-20). It shows "open" in the union view only because
  `docs/tier-a-reviews/cody.jsonl:71` is a stale mirror, and only cody may write
  that shard.
- My b64 re-review of b19 is SOUND-WITH-GAPS (medium): the failing-first framing
  is superseded, A1/C1 assert only "not 503", and the census misses 13 ternary
  `400->[]` reads. It is routed to cody below.
- **Legacy file: 0 obligations open for cc.**

## 5. OPEN (routed; also in the status-registry note "FOR HANK / FOR CODY / FOR MICHAEL")

| Item | Owner | Next step |
|---|---|---|
| `write_batch` `in.()` resurrection | hank | Quote the `in.()` values, or reject `)` and `,` in ids; add an arm that drives a 400. |
| readiness caregiver key mismatch | hank | Key `caregiversById` by `data.employee_id`; give the b60 test distinct ids. |
| leg_ gate on an HTTP 400 | hank | Refuse the sensitive roles on a 400 as well, or prove the 400 means not-provisioned. |
| `sd-sub-data` compliance gate on update | hank | Run the gate whenever `sub_id` changes. |
| 64KB cap on `write_batch` | cody (or hank) | Give it a per-action cap measured per record. |
| stale `cody.jsonl:71` mirror; b19 suite gaps | cody | Append a reviewed mirror line; tighten A1/C1; widen the census. |
| `alf_clients` medications and diagnosis visible to billing/activities | Michael | Decide whether the "billing never reads the MAR" rule covers the profile fields. |
| `family_mar` field-scope rule | hank | Declare it in `tools/field_scope_rules.json`. |
| The 23 routed reads (b62) | hank | Unchanged; `alf_mar` first. |
