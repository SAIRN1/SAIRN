# The remaining 19 SQL files — smallest app first, one at a time

**2026-10-06 (Cody).** File 1 of 20 (`sql/sairngrounds_caddie_schema.sql`)
was handed over in the previous report. **These are the other 19.**

**MICHAEL RUNS ONE FILE AT A TIME.** This table is the map, not a queue —
nothing here is handed over until the file before it has been confirmed.

| # | file | app | tables created | bytes | prerequisite order | destructive statement | confirm | expect |
|---|---|---|---|---|---|---|---|---|
| 2 | `sql/mech_credentials_schema.sql` | SAIRNmechanical | 1 (`mech_credentials`) | 7240 | only file in app group 2 | **NONE.** No `drop`, `truncate`, `delete` or `alter column` of any kind | **section 5** | **1 rows** |
| 3 | `sql/stonedesk_locations_schema.sql` | StoneDesk | 1 (`sd_locations`) | 5770 | run 1 of 2 in app group 3 | **NONE destructive.** 1 x `drop policy if exists` <name> on public.<table> — idempotent policy replacement, named here because the word `drop` appears in the file and a reader scanning for it must not have to guess | **section 1** | **2 rows** |
| 3 | `sql/sd_approvals_schema.sql` | StoneDesk | 1 (`sd_approvals`) | 5578 | run 2 of 2 in app group 3 | **NONE.** No `drop`, `truncate`, `delete` or `alter column` of any kind | **section 1** | **2 rows** |
| 4 | `sql/sd_supplier_lead_times_schema.sql` | StoneDesk | 1 (`sd_supplier_lead_times`) | 5902 | only file in app group 4 | **NONE.** No `drop`, `truncate`, `delete` or `alter column` of any kind | **section 2** | **1 rows** |
| 5 | `sql/sairndental_gfe_schema.sql` | SAIRNdental | 1 (`dnt_gfe`) | 3669 | run 1 of 3 in app group 5 | **NONE destructive.** 1 x `drop policy if exists` <name> on public.<table> — idempotent policy replacement, named here because the word `drop` appears in the file and a reader scanning for it must not have to guess | **section 4** | **3 rows** |
| 5 | `sql/sairndental_recall_schema.sql` | SAIRNdental | 1 (`dnt_recall_outreach`) | 4324 | run 2 of 3 in app group 5 | **NONE destructive.** 1 x `drop policy if exists` <name> on public.<table> — idempotent policy replacement, named here because the word `drop` appears in the file and a reader scanning for it must not have to guess | **section 4** | **3 rows** |
| 5 | `sql/sairndental_treatment_plans_schema.sql` | SAIRNdental | 1 (`dnt_txplans`) | 4760 | run 3 of 3 in app group 5 | **NONE destructive.** 1 x `drop policy if exists` <name> on public.<table> — idempotent policy replacement, named here because the word `drop` appears in the file and a reader scanning for it must not have to guess | **section 4** | **3 rows** |
| 6 | `sql/sairnroofing_entities_schema.sql` | SAIRNroofing | 1 (`rf_entities`) | 6993 | run 1 of 5 in app group 6 | **NONE destructive.** 1 x `drop policy if exists` <name> on public.<table> — idempotent policy replacement, named here because the word `drop` appears in the file and a reader scanning for it must not have to guess | **section 7** | **8 rows** |
| 6 | `sql/sairnroofing_prequal_schema.sql` | SAIRNroofing | 2 (`rf_prequal_documents`, `rf_bonding`) | 8938 | run 2 of 5 in app group 6 | **NONE destructive.** 2 x `drop policy if exists` <name> on public.<table> — idempotent policy replacement, named here because the word `drop` appears in the file and a reader scanning for it must not have to guess | **section 7** | **8 rows** |
| 6 | `sql/sairnroofing_safety_schema.sql` | SAIRNroofing | 2 (`rf_safety_equipment`, `rf_job_hazard_assessments`) | 9586 | run 3 of 5 in app group 6 | **NONE destructive.** 2 x `drop policy if exists` <name> on public.<table> — idempotent policy replacement, named here because the word `drop` appears in the file and a reader scanning for it must not have to guess | **section 7** | **8 rows** |
| 6 | `sql/sairnroofing_supplier_documents_schema.sql` | SAIRNroofing | 1 (`rf_supplier_documents`) | 6568 | run 4 of 5 in app group 6 | **NONE.** No `drop`, `truncate`, `delete` or `alter column` of any kind | **section 7** | **8 rows** |
| 6 | `sql/sairnroofing_warranties_schema.sql` | SAIRNroofing | 2 (`rf_warranty_tiers`, `rf_job_warranties`) | 9533 | run 5 of 5 in app group 6 | **NONE destructive.** 2 x `drop policy if exists` <name> on public.<table> — idempotent policy replacement, named here because the word `drop` appears in the file and a reader scanning for it must not have to guess | **section 7** | **8 rows** |
| 7 | `sql/sairnsenior_applicants_schema.sql` | SAIRNsenior | 1 (`sen_applicants`) | 4501 | run 1 of 7 in app group 7 | **NONE destructive.** 1 x `drop policy if exists` <name> on public.<table> — idempotent policy replacement, named here because the word `drop` appears in the file and a reader scanning for it must not have to guess | **section 6** | **9 rows** |
| 7 | `sql/sairnsenior_authorizations_schema.sql` | SAIRNsenior | 1 (`sen_authorizations`) | 7073 | run 2 of 7 in app group 7 | **NONE destructive.** 1 x `drop policy if exists` <name> on public.<table> — idempotent policy replacement, named here because the word `drop` appears in the file and a reader scanning for it must not have to guess | **section 6** | **9 rows** |
| 7 | `sql/sairnsenior_branches_schema.sql` | SAIRNsenior | 1 (`sen_branches`) | 4866 | run 3 of 7 in app group 7 | **NONE destructive.** 1 x `drop policy if exists` <name> on public.<table> — idempotent policy replacement, named here because the word `drop` appears in the file and a reader scanning for it must not have to guess | **section 6** | **9 rows** |
| 7 | `sql/sairnsenior_franchise_schema.sql` | SAIRNsenior | 1 (`sen_franchise_agreements`) | 6296 | run 4 of 7 in app group 7 | **NONE destructive.** 1 x `drop policy if exists` <name> on public.<table> — idempotent policy replacement, named here because the word `drop` appears in the file and a reader scanning for it must not have to guess | **section 6** | **9 rows** |
| 7 | `sql/sairnsenior_payer_contracts_schema.sql` | SAIRNsenior | 1 (`sen_payer_contracts`) | 4957 | run 5 of 7 in app group 7 | **NONE destructive.** 1 x `drop policy if exists` <name> on public.<table> — idempotent policy replacement, named here because the word `drop` appears in the file and a reader scanning for it must not have to guess | **section 6** | **9 rows** |
| 7 | `sql/sairnsenior_referrals_schema.sql` | SAIRNsenior | 2 (`sen_referral_sources`, `sen_referrals`) | 5238 | run 6 of 7 in app group 7 | **NONE destructive.** 2 x `drop policy if exists` <name> on public.<table> — idempotent policy replacement, named here because the word `drop` appears in the file and a reader scanning for it must not have to guess | **section 6** | **9 rows** |
| 7 | `sql/sairnsenior_training_schema.sql` | SAIRNsenior | 2 (`sen_training_rules`, `sen_training_records`) | 6011 | run 7 of 7 in app group 7 | **NONE destructive.** 2 x `drop policy if exists` <name> on public.<table> — idempotent policy replacement, named here because the word `drop` appears in the file and a reader scanning for it must not have to guess | **section 6** | **9 rows** |

## WHAT IS AND IS NOT DESTRUCTIVE HERE, FLAGGED BY NAME

**NOT ONE OF THE 19 CARRIES A DESTRUCTIVE STATEMENT.** No `drop table`, no
`truncate`, no `delete from`, no `alter column`. Every table is
`create table if not exists` and every file is re-runnable.

**The word `drop` DOES appear, 18 times across 13 files, and every one is
`drop policy if exists "<name>" on public.<table>`** immediately followed by
`create policy` with the same name. That is idempotent policy replacement —
it removes a POLICY, never a row and never a column. **Flagged by name
anyway**, because a reader scanning a 9KB file for the word `drop` should not
have to work out which kind it is.

## THE COUNT RECONCILES, AND MY FIRST COUNT DID NOT

```
19 files here            24 tables
+ file 1, sairngrounds    2 tables
                         --
                         26  <- matches the runbook figure of 26
```

**AND EVERY ONE OF THE 26 APPEARS IN A CONFIRM QUERY** — checked by
name against `sql/zz_confirm_2026-10-05_missing_tables.sql`: zero created and
unconfirmed.

**MY FIRST COUNT SAID 27 AND IT WAS WRONG.** A looser regex
(`create\s+table\s+if\s+not\s+exists` with no `public.` anchor) counted a
mention inside a comment in `sairndental_gfe_schema.sql` and made dental read
as 4 tables against the runbook's 3. **The runbook was right and my regex was
loose** — the same narrower-than-the-corpus-or-wider-than-the-corpus class
this platform keeps paying for, in the direction that invents a discrepancy.
Re-derived with the `public.` anchor: 26, reconciled.

## HOW TO USE THIS

1. **One file.** Paste it whole; do not retype it and do not run it in pieces.
2. **Then that app group's confirm section**, immediately — not all of them
   at the end. A total at the end cannot tell you WHICH paste truncated.
3. **Fewer rows than the `expect` column?** Re-paste that one file and re-run
   that one section. Do not carry on.

Sections 8, 9 and 10 (the total of 26, the grants, RLS) run **once, at the
end**. The snapshot re-capture is separate and goes **last**.
