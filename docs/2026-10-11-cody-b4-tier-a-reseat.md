# Tier-A dangling review-record shas: what was reseated, and who owns the rest

**cody, batch 27 item 2. Written 2026-10-12, at HEAD `60b7a9c9`.**

Regenerate every figure below with:

```
python tools/tier_a_review_gate.py --reseat-shas --include-reviewed
```

That command is the only source here. Nothing in this document is a count
carried over from a handoff -- the batch brief said "~21 of 32" and the
measured population is different, which is recorded below rather than
smoothed over.

---

## The population, measured

| | count |
|---|---:|
| records in `docs/tier-a-reviews.json` | 240 |
| examined by the reseat walk (open + reviewed) | 243 |
| sha already reachable from `origin/main` -- not touched | 59 |
| **RESEATED this batch, strong basis** | **3** |
| **WEAK basis -- NOT reseated, routed below** | **11** |
| refused, carrying a sha | 25 |
| refused, NO sha at all -- `--backfill-shas` owns these | 145 |

**THE BRIEF'S ARITHMETIC DID NOT SURVIVE THE MEASUREMENT, AND THAT IS THE
FIRST FINDING.** It asked for "~21 of 32" dangling records reseated with 11
cross-session ones held back. The real dangling-with-a-sha population at this
HEAD is 39: 3 with a basis strong enough to repoint, 11 with a WEAK one, 25
refused. The **11 is real and is exactly the weak set**; the **21 is the
REFUSED set**, and a refused record cannot be reseated by this clone at all
-- so the two halves of that sentence were the wrong way round. A further 145
records carry no sha of any kind and are outside this tool's job entirely.

---

## RESEATED -- 3, strong basis only

Each carries `opened_at_sha_reseated: true` and an
`opened_at_sha_reseat_basis` naming WHICH basis was used, so a reseated sha,
a weakly reseated one and one stamped at open time are never
indistinguishable. `opened_at_sha_was` keeps the orphan, so every one of
these is reversible from the ledger alone.

| author | opened_at | reviewer | basis | old sha | new sha |
|---|---|---|---|---|---|
| `cc` | 2026-09-26T13:13:44Z | `cody` | EXACT FILE SET | `26eabb054364` | `f0c0cb7ac160` |
| `fourth` | 2026-09-27T02:17:49Z | `hank` | EXACT FILE SET | `191d2dce5369` | `c123a9250021` |
| `cody` | 2026-10-12T01:49:28Z | `--` | SUBJECT TWIN | `30bb20220d26` | `ca81d59d6e66` |

**A JUDGMENT CALL, STATED RATHER THAN IMPLIED: two of these three are not
cody's records.** `opened_at_sha` is a pointer to the commit a record
describes, stamped by the author at open time. Repairing a dangling pointer
on a strong basis changes no verdict, no reviewer, no finding and no owner
-- and the previous session on this item reseated only its own five. The
wider choice is taken here because the narrower one leaves known-good
repairs undone with nobody likely to do them, and because every reseat is
stamped with its basis and keeps the orphan, so any session can reverse one
without asking. **The WEAK set below is where that reasoning stops.**

---

## NOT RESEATED -- the 11 WEAK-basis records, with every session that touched each

These are the ones the brief asked to be listed rather than written.
`--write` alone will not apply them; `--write-weak-basis` is a second flag
on purpose, because **containment is a different claim from equality**: the
record names a file set and the candidate commit changed those files AND
MORE, so the match says the commit touched everything the record names, not
that it is the commit the record is about.

**9 of the 11 genuinely span two sessions** -- an author who stamped the sha
and a different reviewer who signed the verdict. The remaining 2 are `open`
and name one session each. A weak reseat on a cross-session record would
repoint one session's stamp underneath another session's verdict on a basis
that is explicitly not identity, which is the case for routing rather than
writing.

| opened_at | author | reviewer | status | sessions on the record | candidate | gap | basis |
|---|---|---|---|---|---|---|---|
| 2026-09-26T00:13:53Z | `hank` | `cc` | reviewed | `cc`, `hank` | `72ba2261048b` | 0.2h | FILE-SET SUBSET |
| 2026-09-26T01:04:07Z | `cc` | `fourth` | reviewed | `cc`, `fourth` | `e683f59b52b8` | 0.1h | FILE-SET SUBSET |
| 2026-09-26T12:36:06Z | `hank` | `fourth` | reviewed | `fourth`, `hank` | `c0ae9a0a5354` | 0.0h | FILE-SET SUBSET |
| 2026-09-26T13:38:34Z | `cc` | `cody` | reviewed | `cc`, `cody` | `f3484b3c5889` | 0.1h | FILE-SET SUBSET |
| 2026-09-26T17:39:03Z | `fourth` | `cc` | reviewed | `cc`, `fourth` | `1f9936429432` | 0.0h | FILE-SET SUBSET |
| 2026-09-26T18:53:22Z | `fourth` | `cody` | reviewed | `cody`, `fourth` | `944a5faadae5` | 0.0h | FILE-SET SUBSET |
| 2026-09-27T02:06:03Z | `cody` | `cc` | reviewed | `cc`, `cody` | `94fbf115ffcd` | -- | SUBJECT TWIN, FILES PARTIAL |
| 2026-09-28T21:33:14Z | `hank` | `cc` | reviewed | `cc`, `hank` | `cc956d9ec115` | 0.0h | FILE-SET SUBSET |
| 2026-09-29T14:46:23Z | `fourth` | `cody` | reviewed | `cody`, `fourth` | `c66a32854e5a` | 3.3h | FILE-SET SUBSET |
| 2026-10-06T06:14:34Z | `hank` | `--` | open | `hank` | `8246d8bab707` | 0.1h | FILE-SET SUBSET |
| 2026-10-06T06:18:11Z | `cc` | `--` | open | `cc` | `3cf3d5ec3e2c` | 0.4h | FILE-SET SUBSET |

### What each one names, so a reviewer need not re-run the tool to triage it

**2026-09-26T00:13:53Z -- author `hank`, reviewer `cc` (reviewed)**

- record files: `api/_resources/sairnmechanical.js`, `api/sd-data.js`
- resources: `mech_credentials`, `mech_site_assets`
- recorded sha (dangling): `7be498714a9c`
- the record names ['api/_resources/sairnmechanical.js', 'api/sd-data.js']; that commit changed those AND more
- commit subject: feat(sairnmechanical): business insurance and COI -- the company's position, not a techn
- WEAKER BASIS. --write alone will NOT apply this.

**2026-09-26T01:04:07Z -- author `cc`, reviewer `fourth` (reviewed)**

- record files: `api/sd-data-cross-tenant-dispatchers.test.js`, `tools/cross_tenant_isolation_scope.py`
- resources: `sdn_timeentries`, `sf_accounts`, `sf_members`, `sf_vehicle_service`
- recorded sha (dangling): `0800cd7d99be`
- the record names ['api/sd-data-cross-tenant-dispatchers.test.js', 'tools/cross_tenant_isolation_scope.py']; that commit changed those AND more
- commit subject: review+fix: the comment-strip went into ONE of the TWO places that derive DRIVEN, and th
- WEAKER BASIS. --write alone will NOT apply this.

**2026-09-26T12:36:06Z -- author `hank`, reviewer `fourth` (reviewed)**

- record files: `api/_lib/alf-family-mar.js`, `api/sd-data-family-contacts.test.js`, `api/sd-data.js`
- resources: `alf_mar`, `mech_credentials`
- recorded sha (dangling): `82aaa2fd628d`
- the record names ['api/_lib/alf-family-mar.js', 'api/sd-data-family-contacts.test.js', 'api/sd-data.js']; that commit changed those AND more
- commit subject: feat(sairncare): the family record, and MAR access gated to administration STATUS only
- WEAKER BASIS. --write alone will NOT apply this.

**2026-09-26T13:38:34Z -- author `cc`, reviewer `cody` (reviewed)**

- record files: `tests/sairnvet_dose_audit_reader.js`
- resources: `sv_audit_log`
- recorded sha (dangling): `1d8137609814`
- the record names ['tests/sairnvet_dose_audit_reader.js']; that commit changed those AND more
- commit subject: fix(sairnvet): 284 dosing rows displayed a green "Verified" tick and NOTHING in the app
- WEAKER BASIS. --write alone will NOT apply this.

**2026-09-26T17:39:03Z -- author `fourth`, reviewer `cc` (reviewed)**

- record files: `api/bridge-push-auth.test.js`, `api/bridge.js`
- resources: `invoices`
- recorded sha (dangling): `11f5f4181e42`
- the record names ['api/bridge-push-auth.test.js', 'api/bridge.js']; that commit changed those AND more
- commit subject: fix(bridge): the one endpoint of forty-one that never asked whether the licence was stil
- WEAKER BASIS. --write alone will NOT apply this.

**2026-09-26T18:53:22Z -- author `fourth`, reviewer `cody` (reviewed)**

- record files: `api/sd-data.js`, `tests/roofing_claim_gate_single_source.js`, `tests/run_blob_conversion_coverage_probe.py`, `tools/blob_conversion_coverage.py`
- resources: `rf_certifications`, `rf_claims`, `sd_quote_requests`
- recorded sha (dangling): `496ca6514724`
- the record names ['api/sd-data.js', 'tests/roofing_claim_gate_single_source.js', 'tests/run_blob_conversion_coverage_probe.py', 'tools/blob_conversion_coverage.py']; that commit changed those AND more
- commit subject: fix(blob): item 94 was reported COMPLETE by a grep that could not match the sites it lef
- WEAKER BASIS. --write alone will NOT apply this.

**2026-09-27T02:06:03Z -- author `cody`, reviewer `cc` (reviewed)**

- record files: `sairnmechanical.html`, `tests/sairnmechanical_site_asset_export.js`, `tools/panel_depth.py`
- resources: `mech_credentials`, `mech_site_assets`, `sc_claims`, `sc_drg`, `sc_eligibility`, `sc_fraud`, `sc_hcc`, `sc_pctc`, `sc_prebill`
- recorded sha (dangling): `0f9d1eb9f143`
- the twin's diff covers SOME of the record's files and not all of them: ['sairnmechanical.html', 'tests/sairnmechanical_site_asset_export.js', 'tools/panel_depth.py']
- a partial overlap is not a match and is not a refusal either -- it is the third state, and the record may name files from more than one commit
- commit subject: feat(sairnmechanical): the site-asset register exports, and the three refrigerant rules
- WEAKER BASIS. --write alone will NOT apply this.

**2026-09-28T21:33:14Z -- author `hank`, reviewer `cc` (reviewed)**

- record files: `tools/rebase_state_guard.py`
- resources: `quotes`
- recorded sha (dangling): `50c32b02a46d`
- the record names ['tools/rebase_state_guard.py']; that commit changed those AND more
- commit subject: feat(guard): the amend rule was prose, was broken anyway, and is now a hook
- WEAKER BASIS. --write alone will NOT apply this.

**2026-09-29T14:46:23Z -- author `fourth`, reviewer `cody` (reviewed)**

- record files: `api/sd-data-mech-redaction-scope.test.js`, `api/sd-data-session-gate.test.js`, `api/sd-data.js`
- resources: `mech_quotes`, `scp_quotes`, `sf_trustee_audits`, `sf_vehicle_service`, `sf_vehicles`
- recorded sha (dangling): `c4dd292fd8a8`
- the record names ['api/sd-data-mech-redaction-scope.test.js', 'api/sd-data-session-gate.test.js', 'api/sd-data.js']; that commit changed those AND more
- commit subject: fix(sairnmechanical): mech_docs WRITE was reachable on a licence key alone, on the one m
- WEAKER BASIS. --write alone will NOT apply this.

**2026-10-06T06:14:34Z -- author `hank`, reviewer `none yet` (open)**

- record files: `api/sd-data.js`, `tests/sd_data_family_mar_gate.js`
- resources: `alf_clients`, `alf_family_contacts`, `alf_mar`
- recorded sha (dangling): `c0be1a702088`
- the record names ['api/sd-data.js', 'tests/sd_data_family_mar_gate.js']; that commit changed those AND more
- commit subject: fix(sairncare): family_mar disclosed any resident's MAR to any session -- the consent ch
- WEAKER BASIS. --write alone will NOT apply this.

**2026-10-06T06:18:11Z -- author `cc`, reviewer `none yet` (open)**

- record files: `sairnbiz.html`, `tests/sairnbiz_undated_payee_notes.js`, `tools/exit_status_attributable.py`
- resources: `quotes`, `sb_ap`
- recorded sha (dangling): `c0ef09bdad7e`
- the record names ['sairnbiz.html', 'tests/sairnbiz_undated_payee_notes.js', 'tools/exit_status_attributable.py']; that commit changed those AND more
- commit subject: fix(sb_ap+attribution): an unlisted undated payee was invisible to both notes, and the w
- WEAKER BASIS. --write alone will NOT apply this.

---

## REFUSED, carrying a sha -- 25, and why each is not this clone's to fix

| refusal | count | what it means |
|---|---:|---|
| `NO_OBJECT_IN_CLONE` | 8 | the recorded sha is not in THIS clone's object store, so its subject cannot be read. Reseatable by subject only from the clone whose rebase orphaned it -- a genuinely cross-CLONE case, not merely cross-session |
| `SHA_WRONG_WHEN_WRITTEN` | 5 | the sha was ALREADY wrong for this record -- a different fault from a rebase. Its subject twin on origin/main touches none of the files the record names. FIX THE RECORD, not the sha |
| `AMBIGUOUS_EXACT_SET` | 4 | more than one commit changed exactly that file set; uniqueness is what the basis rests on and there is none |
| `NO_OBJECT_IN_CLONE+SUBSET_AMBIGUOUS` | 4 | as above, and more than one commit in the window contains the file set, so containment does not single one out either |
| `EXACT_SET_OUT_OF_WINDOW` | 3 | exactly one commit changed that file set but it is outside the 6h window -- the refusal added THIS batch, after an 18-day-older commit was offered as a strong basis |
| `TWIN_CROSSCHECK_UNREADABLE` | 1 | the twin was found but the cross-check against the record's files could not be read, so the match cannot be confirmed |

**The 12 `NO_OBJECT_IN_CLONE` records are the only genuinely CROSS-CLONE set
in this document** and they are the ones no amount of work in `SAIRN-cody`
can close. Listed with their sessions so the owning clone can run the same
command locally:

| opened_at | author | reviewer | sessions | files sought |
|---|---|---|---|---|
| 2026-09-26T17:36:42Z | `hank` | `cody` | `cody`, `hank` | `tools/load_compliance_seed.py`, `tools/sc_tier_a_write_gate_live_probe.py` |
| 2026-09-27T01:22:40Z | `hank` | `cody` | `cody`, `hank` | `tests/stonedesk_server_backup.js`, `tools/mech_panels_live_check.py` |
| 2026-09-27T02:31:54Z | `hank` | `cc` | `cc`, `hank` | `api/_lib/compliance-rules-staff-join.test.js`, `api/_lib/compliance-rules.js`, `api/sd-data-alf-training-join.test.js`, `api/sd-data.js` |
| 2026-09-27T03:42:29Z | `hank` | `--` | `hank` | `api/_lib/compliance-rules-staff-join.test.js`, `api/_resources/sairnsenior.js`, `api/sd-data-sen-evv-clock.test.js`, `api/sd-data.js` |
| 2026-09-27T12:34:26Z | `hank` | `cc` | `cc`, `hank` | `api/sd-data.js`, `sairnsenior.html`, `tests/sairnsenior_referral_hours.js` |
| 2026-09-28T00:16:59Z | `fourth` | `--` | `fourth` | `api/sd-data-alf-isolation.test.js`, `tests/role_gate_loop_rule_probe.py`, `tools/alf_facility_role_gate_live_probe.py`, `tools/role_gate_negative_coverage.py` |
| 2026-09-28T19:34:37Z | `fourth` | `cc` | `cc`, `fourth` | `tools/fail_open_scan.py` |
| 2026-09-29T12:46:19Z | `fourth` | `cc` | `cc`, `fourth` | `api/sd-data-alf-consent-timestamps.test.js`, `api/sd-data-sen-self-correction-flag.test.js`, `api/sd-data.js` |
| 2026-09-29T14:00:49Z | `fourth` | `cody` | `cody`, `fourth` | `api/sd-data-sf-session-gate.test.js`, `api/sd-data.js`, `tools/staging_discipline_scan.py` |
| 2026-10-05T12:35:55Z | `hank` | `cody` | `cody`, `hank` | `tests/run_citation_line_drift_probe.py`, `tools/citation_line_drift_check.py` |
| 2026-10-07T13:46:11Z | `hank` | `cc` | `cc`, `hank` | `api/sd-data.js`, `tests/sd_data_alf_mar_derive_charges_gate.js`, `tests/sd_data_alf_staff_read_gate.js`, `tests/sd_data_grd_session_gate.js`, `tools/gate_parity_check.py` |
| 2026-10-07T15:13:50Z | `hank` | `cc` | `cc`, `hank` | `tests/sd_data_write_attribution_three_apps.js` |

And the 5 `SHA_WRONG_WHEN_WRITTEN`, which need the RECORD edited by
somebody who knows what it was about -- following the sha to its twin would
preserve the original mis-stamp faithfully:

| opened_at | author | reviewer | sessions | files |
|---|---|---|---|---|
| 2026-09-27T03:05:32Z | `cody` | `fourth` | `cody`, `fourth` | `docs/CRITICALITY-TIERS.md` |
| 2026-09-27T03:24:52Z | `cody` | `fourth` | `cody`, `fourth` | `docs/CRITICALITY-TIERS.md` |
| 2026-09-27T23:49:53Z | `cody` | `cc` | `cc`, `cody` | `tests/sairnfreedom_segregation_of_duties.js` |
| 2026-09-28T03:34:57Z | `cody` | `--` | `cody` | `tests/reachability/resource_demand_probe.py` |
| 2026-09-30T15:15:56Z | `cody` | `hank` | `cody`, `hank` | `docs/CRITICALITY-TIERS.md` |

---

## 145 records carry NO SHA AT ALL and are in no figure above

`--backfill-shas` owns these, not `--reseat-shas`, and the tool says so per
record rather than skipping them. Named here only so the number is not
mistaken for "nothing left to do":

| author | records with no sha |
|---|---:|
| `cc` | 45 |
| `hank` | 36 |
| `cody` | 35 |
| `fourth` | 29 |

**This is the largest single group in the ledger and nothing in this batch
touched it.** Reported, not claimed.
