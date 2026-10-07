# Hank inventory — batch 11, 2026-10-07

**The measurements, with the command that produced each.** The narrative is in
`docs/handoff-hank-2026-10-07.md`; this file exists so no figure in that one has
to be taken on trust. Every exit code below was read from a
`tools/capture_exit.py` status file, never from a harness completion status.

---

## 1. `alf_staff` / `read` — PII, re-derived at HEAD `0f1f845b`

**Command:** `grep -n "resource === 'alf_staff'" api/sd-data.js`, then read the
branch.

**WHAT IT RETURNED:** `Object.assign({ id: r.staff_id }, r.data)` — the whole
jsonb blob, spread. Fields read off the writer (`sairncare.html` `saveStaff()`,
`:3379-3380`) plus `hire_date` from `alf_compliance_rules`/`evaluate`:

| field | kind |
|---|---|
| `name` | PII |
| `phone` | **PII — a personal mobile** |
| `bgcheck_date` | **PII — an employment-screening date** |
| `cert_expiry` | employment |
| `status` | employment |
| `notes` | **PII — free text a manager typed about an employee** |
| `hire_date` | employment |
| `position` | employment |

**WHICH ROLES REACHED IT:** all six. `api/_lib/auth.js:238` declares the
sairncare vocabulary as `owner, nursing, med_aide, caregiver, billing,
activities`. Only `owner` and `billing` (`ALF_MANAGEMENT_ROLES`, `:6889`) could
WRITE. So `caregiver`, `med_aide` and `activities` — no management function —
read every colleague's phone and screening date.

`docs/CRITICALITY-TIERS.md` rates the resource **A / A**.

**GATE PARITY AFTER:** `python tools/gate_parity_check.py --json` — 12
cross-resource tables before, 11 after, and `alf_staff` is **not** among them.

---

## 2. SAIRNgrounds — X of 17, measured by the auditor's own artifact

**Command:**
`python .claude/skills/sairn-hover-auditor/tools-hover2/grd_session_gate_repro.py --all`
→ **EXIT 1**.

| | |
|---|---|
| `grd_*` resources in `api/sd-data.js` | **17** |
| REPRODUCES on both read and write | **16** |
| PARTIAL (`grd_progress_photos`) | **1** — session checked only inside a `qc_status` conditional, never on the default write path |

**Command:** my own region enumeration (`scratchpad/grd_enum.py`) →
**30 distinct resources** between the SAIRNgrounds banner (`:4056`) and the
SAIRNSCAPE banner (`:4799`): 17 `grd_*`, 4 bare SAIRNgrounds names, **9 `msb_*`
belonging to a different app**.

**FIXED: 21** — the 17 plus `properties`, `jobs`, `quotes`, `golf_zones`. Each
bare name is dispatched EXACTLY ONCE in the file and maps to a `grd_*` table
(`grd_properties`, `grd_jobs`, `grd_quotes`, `grd_golf_zones`), checked before
gating so they cannot collide with another app's.

**NOT FIXED: the 9 `msb_*`.** Different app, not in the finding, not in the
claim, and arm D1 proves `msb_products` still answers without a session — a
measurement, not an endorsement.

---

## 3. SAIRNcare cross-resource — X of 4

**Command:**
`python .claude/skills/sairn-hover-auditor/tools-hover2/alf_cross_resource_repro.py --all`
→ **EXIT 1**.

| table | verdict |
|---|---|
| `alf_activities` | CLEAN — correct by design, the code's own comment declares broad-read / narrow-write |
| `alf_clients` | CLEAN — `derive_charges` is management-only and `alf_clients`/`read` already grants `ALF_BROAD_READ_ROLES` the unfiltered read |
| **`alf_mar`** | **REPRODUCES** — `ALF_MANAGEMENT_ROLES − ALF_MAR_ROLES = ['billing']`, and `derive_charges` returned `medication_name` |
| `alf_staff` | CLEAN for the cross question — the #894 fix made `evaluate` STRICTER than the owner, the safe direction |

**1 of 4 real. Fixed.**

**THE PRICE DID NOT MOVE, read off the module rather than assumed:**
`api/_lib/care-charges.js` prices on `e.type` through
`CHARGEABLE[type].rate_key` (`:70`, `:77`) and copies `description` to the line
(`:103`) without pricing on it. Owner and billing get the same line count and
the same total — 9.00 on the fixture, asserted by arm C1.

---

## 4. Attribution — what was measured and what could be fixed

**Command:** `scratchpad/audit_cap.py` over every `api/*-auth.js`.

| | |
|---|---|
| files with a `setup` action | **17** |
| recording NEITHER an audit row NOR a `created_by` | **16** |
| already attributing (`law-auth.js`) | **1** |
| **importing `writeAuditLog` at all** | **3** (law, sc, sd) |
| **declaring an `AUDIT_TABLE`** | **2** (sc, sd) |

`api/_lib/audit.js:40` allowlists exactly **three** audit tables: `sairnlaw`,
`sairncode`, `stonedesk`. **So 14 of the 17 have nowhere to write an audit row
and no column to write an author into — a migration, not a code change.**

**AND THE ASYMMETRY IS THE FINDING:** `set_active` in `sc-auth.js` and
`sd-auth.js` audits EVERY outcome including its refusals (`SELF_DEACTIVATE`,
`CREDENTIAL_INACTIVE`, `LAST_ADMIN`). Revoking access was reconstructible;
granting it was not.

**SIX PATHS FIXED**, and the route differs by schema rather than by preference:

| path | route | why |
|---|---|---|
| `sc-auth.js` `setup` | audit row | `sairncode_audit_log` exists |
| `sd-auth.js` `setup` | audit row | `stonedesk_audit_log` exists |
| `stonedesk-track` `create` | audit row | `sd_order_links` has no blob and no author column (`sql/stonedesk_public_surface_schema.sql:122-135`) |
| `stonedesk-track` `revoke` | audit row | same |
| `sd-sub-data` `roster`/`write` | audit row | `sd_subs` is all named columns, no blob |
| `sd-sub-data` `jobs`/`write` | **blob field** | `sd_sub_jobs.data` is open jsonb — **no migration at all** |

---

## 5. All twelve gate_parity cross-resource flags, hand-verified

**Command:** `python tools/gate_parity_check.py --json` at HEAD, plus the same
against `16b2cc70^`'s `api/sd-data.js` for the before/after.

| verdict | count | tables |
|---|---|---|
| REAL, fixed | **2** | `alf_mar` (PHI), `alf_staff` (owner ungated — a different class) |
| FALSE POSITIVE — safe direction | **7** | `alf_activities`, `dnt_settings`, `rf_cert_rules`, `rf_settings`, `sen_caregivers`, `sen_pay_rates`, `sen_settings` |
| FALSE POSITIVE — role-set containment | **3** | `alf_clients`, `rf_claims`, `rf_jobs` |

**Precision on this file: 2 of 12.** Printed by the tool on every run rather
than written in a document.

**THE CONTAINMENT PROOF, computed rather than argued** — `api/rf-auth.js:132-133`
via `node -e`:

    MANAGEMENT_ROLES : owner, admin
    BROAD_READ_ROLES : owner, admin, estimator
    MGMT not in BROAD: (none)

`rf_draws`/`wip` and `rf_invoices`/`reconcile_claim` are both gated to
`MANAGEMENT ∪ BROAD_READ`, and `rf_jobs`/`read` and `rf_claims`/`read` apply
their assignment filter only to roles OUTSIDE that same set. So every role
reaching the diverging branch already gets the owner's unfiltered read.

**CRITERIA CHANGE:** the verdict is WIDENED, not the match narrowed —
`WEAKER` / `OWNER-UNGATED` / `STRICTER-ONLY` / `NO-OWNER`, with an `UNBUCKETED`
residue line so a direction the report has no heading for is listed rather than
vanishing. Live at this tree: **WEAKER=4, OWNER-UNGATED=6, STRICTER-ONLY=1.**

---

## 6. Citations — re-measured after a fetch

**Command:** `git fetch origin`, then per citation `git cat-file -t`, then
`git merge-base --is-ancestor <sha> HEAD` and the same against `origin/main`
(`scratchpad/cite_measure.py`).

| | |
|---|---|
| distinct sha-shaped citations | **385** |
| resolve AND reachable from HEAD | **335** |
| **exist on origin but not from HEAD** | **0** |
| objects only THIS clone holds (rebase orphans) | **10** |
| **genuinely missing — not an object here** | **40** |

**ZERO are recoverable by fetching**, which is what the split was for.

**AND ONE OF THE 41 WAS MINE, MINTED LAST BATCH.** `16b2cc70d2d8` is not a
commit and never was; the real SHA is `16b2cc70a4e2fdd9…`. I verified the
8-character prefix three ways and then padded it to twelve by typing four more.
It survived last batch's own closing measurement because that reported a COUNT,
not a LIST. Re-seated from `git rev-parse`.

---

## 7. Tier A — listed, none taken

**Command:** `python tools/tier_a_review_gate.py --list` → EXIT 1 (overdue
present). 235 records, 31 open, **23 eligible to hank**. Most overdue eligible:
cody's `2026-09-27T02:06:03Z`, **236h**.

**Command:** `python tools/sairn_claim.py list` → **EXIT 0** (a fetch happened;
the same command with `--no-fetch` exits **4** and says its verdicts are as of
the last fetch, which is why the stale read was not used).

**cc, cody AND fourth all declare `docs/tier-a-reviews.json`.** Three-way
collision. None taken.

---

## 8. Suites at the final SHA

Recorded in the handoff with their exit codes read from status files. The
`run_all_tests.py` lock is worth knowing about: a run killed by a wall-clock
timeout leaves the lock held and the next run exits **3 SKIPPED** rather than
reporting a result — `LOCK_MAX_AGE` is 900s, so it clears itself after 15
minutes, and exit 3 is **not** a failure of the suite.
