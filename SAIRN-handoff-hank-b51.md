# SAIRN handoff — hank b51 — 2026-10-22

**Subject:** D1 (billing MAR read through the assignment tier) fixed and verified live. D2 (criticality_tier_check)
was fixed upstream by cc first; hank verified cc's fix. Written before the report, nothing half-finished.

**Naming:** this is the batch after b50. Michael's confirmation message called it "b50" and asked for
`done b50 <id>`. The files are named b51 so the b50 handoff is not overwritten. The final line follows the
instruction as written.

**Methodology concept:** *a grantee role is admitted by its grant or not at all, and the log row is the grant's
condition, so a read that cannot be logged is not served.*

## 1. PUSHED STATE — NOT FORCED
- `76193dc91` fix(sairncare b51): D1 + D1b, `api/sd-data.js` and `api/b51-mar-billing-assigned.test.js`.
- `d1fb6d5c5` sql(sairncare b51): `sql/alf_audit_owner_credential_2026-10-22.sql`. Michael ran it; the
  audit-owner/owner row was confirmed live.
- `1eacd46ea` chore: register record, Tier A obligation (assigned to cc), derived docs. LANDED. Production deploy
  `dpl_Hh2ysc61ihPgd9SVodwowmRg8Jj4` READY on that sha.
- The handoff, report and digest are pushed after this file is written. Re-derive the tip.

## 2. CLAIMS HELD
`sairncare` (b51) is released at the end of the batch.

## 3. THE ITEMS
**1. D1 — FIXED, VERIFIED LIVE.**
- *Code.* In `family_mar`, a role in `ALF_MAR_GRANT_GRANTEE_ROLES` (billing) with no live grant is refused
  `403 FORBIDDEN` before the assignment-tier query. The refusal is audited as `mar_access_grant_refused`,
  reason `NO_LIVE_GRANT`, with no new event type, so no SQL was needed.
- *D1b.* A granted read is refused `503 AUDIT_UNAVAILABLE` if its `mar_access_read` row fails to write. Grant
  and refusal audits stay best-effort.
- *Local.* `api/b51-mar-billing-assigned.test.js` 11/0: N1–N6, A1–A2, and mutants M1–M3 all red.
  `tests/mar_billing_grant.test.js` 28/0.
- *Live method.* On `ALF-AUDIT-2026` only, through the deployed `/api/alf-auth` and `/api/sd-data` (via
  `tools/sairn_http.py`):
  - audit-owner signed in (whoami owner);
  - provisioned `hank-b51-billing` (billing; PIN in the scratchpad only);
  - resident `zz-b51-resident` assigned to it, and contact `zz-b51-contact` with mar_consent true, all read back.
- **BEFORE the deploy** (pre-fix code): billing `family_mar` → **200 with the full family_mar body.** The
  defect is reproduced live.
- **AFTER deploy `1eacd46ea`:** billing → **403 FORBIDDEN**, no MAR in the body. Owner control → 200.
- DB: exactly one `sairncare_audit_log` row for hank-b51-billing: `mar_access_grant_refused`
  `{action: family_mar, reason: NO_LIVE_GRANT, contact_id: zz-b51-contact}`, at 15:33:06Z.
- Evidence files: `C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-hank\a9d72ca8-d218-42be-9363-f759795e9517\scratchpad\b51\evidence_before.json` and `...\b51\evidence_after.json`. Script: `...\b51\live.py`.
- *Residue (audit licence):* 1 billing credential, 1 resident, 1 contact, 1 audit row, plus the audit-owner credential.

**2. D2 — fixed upstream by cc b50 (`9bb0abf3e`) while my fix was in flight.**
- My duplicate commit was dropped with `git rebase --skip`, with Michael's approval (the classifier had denied
  it), along with its manifest override and register record.
- I ran my scratch-worktree scenarios against cc's version:

| scenario | before | after (cc's fix) |
|---|---|---|
| registry with resources and no `app:` | exit 1, invisible | **exit 2**, SHAPE ERROR named |
| filename/declared-name disagreement | TypeError, exit 1 | **exit 2** COULD NOT RUN |
| `--fix-rollup-list` on that tree | exit 0 with "success" | **exit 1**, REFUSED, "not read" |
| clean tree | unchanged | unchanged |

- One residual difference: the fixer refuses with exit 1, not 2. It no longer claims success. Noted, not changed.

**3. Methodology:** stated above.

## 4. OPEN, AND THE EXACT NEXT STEP
| # | open | owner | next step |
|---|---|---|---|
| T1 | Tier A review of `76193dc91` (family_mar gate) | cc | review per the obligation's 3 points |
| T2 | Tier A reviews of `040ac5a95`, `38b2b5069`, `2fe89f267` | cc | unchanged |
| R1 | Sweep other grant-or-assignment two-tier reads for the same fall-through | unassigned | needs dispatch |
| G1 | cody suite gaps from the b50 reviews | cody | unchanged |
| F1 | criticality fixer refuses with exit 1, not 2 | cc | optional |

## 5. TRANSCRIPT
C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-hank\a9d72ca8-d218-42be-9363-f759795e9517.jsonl
