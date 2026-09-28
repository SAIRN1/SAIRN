# Verification residue — a probe that writes must say where the mess goes

**Written 2026-09-28 (Hank).** A standing convention, a guard in the code path,
an audit tool, and the enumeration that produced all three.

---

## 1. The incident

Verifying that `add_rule` strips forged identity fields **requires a write** —
you cannot see what an endpoint *stores* by reading it. So one probe rule went to
`LAW-TEST-2026`.

**And `DELETE` was revoked platform-wide on `law_deadline_rules` in August.**
`sql/sairnlaw_deadline_rules_schema.sql:120-125` says so in its own words:

> *"DELETE removed 2026-08-25 … the live grant was revoked platform-wide by
> `sql/unused_delete_grant_revoke_2026-08-24.sql` … do NOT re-add `delete` here
> when fixing a missing grant."*

So the row cannot be removed by the API (there is no delete action), by
`service_role` (no grant), or by me. It needs a human in the SQL editor:
`sql/zz_probe_residue_delete_2026-09-28.sql`.

**One probe. One un-deletable row. On a licence somebody may be shown.**

> **And the revoke is right.** A reference table holding the rules every filing
> deadline is computed from should not be deletable by the web tier, and one
> probe row is not a reason to change that. The fix is the licence, not the
> grant.

## 2. The argument was already settled, and not applied

`sql/stonedesk_recovery_admin_seed.sql`:

> *"A published PIN cannot safely persist on SD-PINNACLE-2026 … **THE FIX IS THE
> LICENCE, NOT THE PIN**."*

SAIRNroofing followed it on 2026-09-02 and **two roofing probes correctly use
`RF-AUDIT-2026` today**. Nothing made the others follow, because the rule lived
in a comment in a SQL file rather than anywhere a writing probe would meet it.

**That is the whole design lesson.** A convention enforced by prose is a
convention that holds for whoever read the prose.

## 3. The three obligations

> **A live probe that writes must:**
> 1. write only to an **audit licence** — enforced by `tools/audit_licence.py`,
>    in the code path;
> 2. **clean up** what it wrote, or record a **named residue** with the exact
>    path that removes it;
> 3. **fail its own run** when residue remains — a probe that writes, notices,
>    and still exits 0 has told you the subject is fine and said nothing about
>    the mess.

`tools/live_probe_residue_audit.py` decides 1 and 2.
`tests/run_live_probe_residue_probe.py` is its control pair, five directions.

## 4. The enumeration — checked / universe

**44 files** under `tools/ tests/ scripts/` address `sairn.vercel.app`.
**Seven** send a write action. (**818** candidate files scanned in total.)

| Probe | Class | Licence | Residue |
|---|---|---|---|
| `tools/load_deadline_seed.py` | **LOADER** | real licences, by design | n/a |
| `tools/load_compliance_seed.py` | **LOADER** | real licences, by design | n/a |
| `tools/rf_claim_gate_live_probe.py` | VERIFICATION | `RF-AUDIT-2026` ✅ already correct | none — upsert, overwritten |
| `tools/rf_roundtrip_probe.py` | VERIFICATION | `RF-AUDIT-2026` ✅ already correct | none — ids re-used |
| `tools/alf_facility_role_gate_live_probe.py` | VERIFICATION | now guarded | one upserted `alf_facility` row, fixed id `ZZ-GATE-FAC` |
| `tools/law_billing_code_trim_live_probe.py` | VERIFICATION | **was pointed at `LAW-PINNACLE-2026`** | one row **per run** — ids are generated, so runs **accumulate** |
| `tools/sc_tier_a_write_gate_live_probe.py` | VERIFICATION | **needs `SC-AUDIT-2026`, which does not exist** | see §6 |
| `tests/run_gate_caller_impact_probe.py` | **FIXTURE** | none — the write is a string | n/a |

**The class is DECLARED, never inferred**, and that is the load-bearing
decision. `load_deadline_seed.py` writes reference rules to real customer
licences because that is its entire job — gating it would break seeding on 48
jurisdictions. A tool guessing from filename, directory or action name would
either break the loaders or exempt the probes.
`tools/checker_control_check.py` records that three inference models were tried
for an equivalent question and all three were wrong within an hour:
*"WHICH CHECKER A TEST IS A CONTROL FOR IS A FACT ITS AUTHOR KNOWS AND NOTHING
ELSE RELIABLY DOES."*

### The sharpest finding

`tools/law_billing_code_trim_live_probe.py`'s own usage note read
*"LAW_LICENSE — the licence key (demo row: **LAW-PINNACLE-2026**)"* — the
**demo-facing** licence — and it drives a `write`. Its ids are **generated**, so
runs accumulate rather than overwrite. Corrected to require `LAW-AUDIT-2026`.

## 5. What was built

* **`tools/audit_licence.py`** — `require_audit_licence(key, tool, writes)`.
  Three states: an audit key proceeds; a non-audit key **exits 2 COULD NOT RUN**
  naming the key, the seed file and the bootstrap step; **no key at all also
  refuses**, because a probe that returns early on a missing key looks exactly
  like one that ran and found nothing. **Exit 2, never 1** — a refusal to run is
  not a finding about the subject. An allowlist entry requires a *sentence*, the
  same decision `--rule not-citable` and the `no-defect-record:` trailer made.
* **`sql/audit_license_seed_mech_law_2026-09-28.sql`** — mints
  `MECH-AUDIT-2026` and `LAW-AUDIT-2026`. Licence rows only, **no credential
  row**, following the roofing precedent: the account is bootstrapped through the
  app's own action afterwards so the SQL never carries a PIN. It also spells out
  provisioning the **second, non-management account**, because a role gate cannot
  be verified with one role.

## 6. Outstanding — and I cannot do these

1. **Michael runs `sql/audit_license_seed_mech_law_2026-09-28.sql`.** Licence
   provisioning has always been Michael-only: `license_keys` is service-role for
   read, `anon` gets `42501`, and `sql/demo_license_keys_seed.sql` records that
   *"there is no self-service key-generation system anywhere in this codebase"*.
   Probed live before writing this — both keys answer **401 INVALID_LICENSE**, so
   the seed is needed and is not a no-op.
2. **Michael runs `sql/zz_probe_residue_delete_2026-09-28.sql`** to remove my
   row. Step 1 of that file is a SELECT to read before deleting; step 3 verifies
   from the app rather than from the editor.
3. **`SC-AUDIT-2026` does not exist**, and
   `tools/sc_tier_a_write_gate_live_probe.py` drives `write`, `setup`,
   `set_active` **and `delete`** against Tier A SAIRNcode resources. Its guard
   now **refuses** rather than letting it run against `SC-PINNACLE-2026` again.
   That probe is out of service until the licence is minted — deliberately, and
   it is the loudest outstanding item here.
4. **The `alf_facility` role gate is still UNVERIFIED live.** Fixing its session
   header made the probe *capable* of answering; it has not been re-run, because
   it needs an audit licence and a non-management account that do not exist yet.

## 7. The tool committed two defects on its own first run

Recorded because it is the cheapest evidence that this class is nobody else's
mistake.

1. **It counted `verify` as a write.** `api/audit-checkpoint.js` branches
   `action === 'verify' ? verifyTable : checkpointTable`, and only
   `checkpointTable` issues a POST — so `verify` re-reads and compares stored
   hashes and writes nothing. `tools/audit_checkpoint_status.py` was in the
   writer set and never belonged there. **The verb is not a reliable guide**,
   which is why the action list is read rather than inferred.
2. **Its demo-key check read PROSE.** It flagged three probes for "hardcoding a
   demo-facing licence" — and every hit was *my own comment* explaining which
   licence the probe was being moved **away from**. A check that fires on its own
   documentation is PR §1.2, and **this repo has now paid for it twice in one
   session**: `tools/ghost_field_read_scan.py` was blinded by prose in exactly
   the mirror-image way. Comments are stripped before the key scan now; the class
   and residue declarations are real assignments, so they survive.
