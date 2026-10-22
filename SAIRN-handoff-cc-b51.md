# SAIRN handoff: cc, batch b51, 2026-10-22

**Both items are closed.** The seven register problems are listed below and
routed to fourth. fourth's b49 Tier A obligation is discharged (`39eb41d6`)
with the verdict SOUND-WITH-GAPS. No `--force` and no override were used. The
clone reads 0 0 against origin.

| | |
|---|---|
| Landed | `39eb41d6` (the ledger discharge), then these deliverables |
| Context | see the digest's CONTEXT line (measured) |
| Transcript | `C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cc\87a27b9f-55e9-45e8-b017-01ed1febac1a.jsonl` |

## 1. The 7 register problems, for fourth

All seven are in `docs/CRITICALITY-TIERS.md`, which is fourth's file. To
reproduce them, run `python tools/criticality_tier_check.py` (exit 1,
`PROBLEMS:7`). Every one is a data drift in the register, not a checker
defect.

| # | Kind | Exact problem | Source | Exact fix |
|---|---|---|---|---|
| 1 | NO TIER | `sairnlegacy/leg_settings` is registered (`api/_resources/sairnlegacy.js:66`) and has **no row** | `38b2b506`, hank b45, 2026-10-21, added the resource | Add a two-axis row for `leg_settings`. It holds the owner's F2/F3 policy, which decides whether an apprentice may read or prepare regulated records, so check it against the A criteria. Tiering it is fourth's call. |
| 2 | NO TIER | `sairnsenior/sen_period_closings` is registered (`api/_resources/sairnsenior.js:83`) and has **no row** | `144dfb71`, 2026-10-16, added it (the close/reopen of payroll periods) | Add a row. It records which pay periods are closed and drives payroll adjustments, which is money, so check it against the A criteria. |
| 3 | COUNT | the sairnlegacy rollup (line 133) says **A=20**; the rows say **21** | `1c9ad7cf`, 2026-10-19 14:45, moved `leg_clergy` B→A in its row only | Change the A cell to `**21**`. |
| 4 | COUNT | the same rollup says **B=16**; the rows say **15** | the same commit | Change the B cell to `15`. The total of 36 is unchanged until `leg_settings` gets a row; then it becomes 37, and A or B moves again. |
| 5 | LIST MISSING | `leg_clergy` is Tier A and is not named in the sairnlegacy rollup list | the same commit | `python tools/criticality_tier_check.py --fix-rollup-list` inserts exactly this name. Do not retype it. |
| 6 | COUNT | the sairnscape rollup (line 136) says **A=3**; the rows say **4** | `899597b5`, 2026-10-19 11:14, moved `customers` B→A in its row. The list already names `customers`; the count was never bumped | Change the A cell to `**4**`. |
| 7 | COUNT | the same rollup says **B=9**; the rows say **8** | the same commit | Change the B cell to `8`. |

**Order:**
- Add the two rows (problems 1 and 2) first, because they change the
  sairnlegacy and sairnsenior counts.
- Then run `--fix-rollup-list` for problem 5.
- Then hand-correct the A/B cells (problems 3, 4, 6 and 7).
- Re-run the check until it reports `PROBLEMS:0`.
- The file's headline sentence ("400 resources, 283 A, 117 B") also moves
  when the rows land. The check reports a HEADLINE problem if it is not
  re-derived.

## 2. fourth's b49 Tier A obligation: DISCHARGED, SOUND-WITH-GAPS

The obligation covers `02cec2f8` (senior), `5e38373c` (roofing) and
`dd3c45f6` (biz Z8). The review was done by a read-only subagent; the
scratch files are in `scratchpad\rev-f49\`. I re-read the MEDIUM finding in
the code myself.

**What holds:**
- Refused contracts and authorisations are withdrawn and named
  (`sairnsenior.html:4766`, `:5503`).
- Toasts use `textContent`, and `rfEsc` escapes, so the fix adds no XSS.
- The suites drive the real extracted functions: 15/0, 10/0 and 19/0. With
  the fixes removed, senior goes RED at 5/15 and roofing at 3/10.
- `checkblocks` is clean.
- No later commit touches these files.

**Gaps, for fourth:**

| Severity | Gap | Where | Next step |
|---|---|---|---|
| **MEDIUM**, pre-existing (the same code is at the parent `02cec2f8^:4361`) | A **refused** `sen_claims` write stays local. It is pushed to localStorage before the `await`, so `readyToBillVisits` hides the visit and it cannot be re-billed. The toast says "Not saved", but the row persists and `senServerWinsMerge` never drops it. | `sairnsenior.html:4374`, `:4190`, `:2289` | Withdraw the claim on refusal, the same way as contracts and authorisations. Add an arm: refuse it, then check the visit is back in ready-to-bill. |
| low-med | A non-JSON answer (a WAF 403, 413, or a 500 with an HTML body) is treated as "no answer", so a refused contract stays and can still price claims | `senWriteFail` / `senData` catch | Map an HTTP status that has no code to refused, except 5xx. |
| low | A 503 SCHEMA_OUTDATED is withdrawn as "refused" while NOT_PROVISIONED is kept, which is inconsistent and loses the edit | the `/^HTTP_5/` test; `api/sd-data.js:8855`, `:8946` | Keep the row on SCHEMA_OUTDATED, as for NOT_PROVISIONED. |
| low-med | When the parent read fails (equipment or warranty tiers), the child JHA or warranty panel is left stale: "Loading…" for ever on first load, or the old rows and Edit buttons after a Refresh | `sairnroofing.html:4166`, `:4836` | Say the failure in the child panel and clear its arrays. |
| low | 6 mutants survive: the HTTP_5 keep, the authorisation-edit restore, two stale-error clears, and roofing `rfEsc` ×2. The biz R7 arm can pass vacuously (its try/catch hides a throw). | the three suites | Add arms that kill them. Drive the real `senData` status mapping. |

## 3. Methodology item

**A register problem is not routed until it names the commit that caused it
and the exact cell to change.** "7 register problems" told fourth only that
the check was red. Each row above tells fourth what to do, in which order,
and why. Three of the seven come from one commit (`1c9ad7cf`) that changed a
row without its rollup, and two from another (`899597b5`) with the same
shape. That is the same pattern `--fix-rollup-list` was built for, applied
one column further over.

## 4. OPEN

| Item | Owner | Next step |
|---|---|---|
| Register problems 1-7 | fourth | the table in §1, in the order given |
| A refused `sen_claims` write stays local (MEDIUM), plus the other b49 gaps | fourth | the table in §2 |
| `38b2b506` partial-apprentice reset, and the fail-open read at `:17047` (from b50) | hank | refuse a partial object or merge it onto the stored one; answer 502 on a body that is not an array |
| `d6b37bb1` lock/profile drift (from b50) | cody | require `PROFILE.lockedResources` in the deferral |
