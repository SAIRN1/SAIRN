# SAIRN handoff: cc, batch b73, 2026-10-29: resume, Tier A reviews

**Numbering.** The dispatch's closing line said `done b72`, but b72 was
already closed (`54c52e57`). So this is **b73**, and b72 was not overwritten.
This is the same shape b72 recorded for b71.

| | |
|---|---|
| Start | HEAD `54c52e57` was 3 behind origin. It was fast-forwarded to `fcc8bcaf`, with a clean tree. |
| Hook presence | 4/4 OK at blob `22b205e8`, and the install regression passed 37/0. Both were checked before any shared config was touched, and no shared config was touched. |
| Claims | none taken. This batch's only write is a review, a verdict doc and this handoff. |
| Context | the window was **declared 200,000** (conservative, see §3). The measured line is in the digest. |
| Transcript | `C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cc\a046cdf7-9eaf-4291-b1ac-b9b8bb34da67.jsonl` |

## 1. Done this batch

**C-2 is DISCHARGED: cody b64 re-entry guards** (opened 2026-10-29T13:40:41Z).
The verdict is PASS with one LOW finding.

- The full verdict is in `docs/2026-10-29-cc-b73-review-cody-b64-reentry.md`.
- All eight `tests/*_save_reentry.js` suites exit 0.
- Every hold is released in `finally`, and none is refused on a first press.
- No `await` comes between a check and its hold. For sairncode that is 24 of
  24, measured by script.
- **The LOW finding, routed to cody:** `sairndental.html:3104` runs
  `dntCredWriting++;rCredentials(null);` outside the `try`. A synchronous
  throw there leaves the counter stuck, and since b64's guard at :3044, every
  later credential add is refused until reload.
- **Cause tag:** a hold acquired outside the try/finally that releases it.

## 2. Every open item, with its exact next step

### cc's own

**C-1. Tier A review: hover b92 `test_965`** (opened 2026-10-28T21:14:26Z,
ASSIGNED TO cc). **A builder cannot discharge it.**

- The obligation is to read
  `.claude/skills/sairn-hover-auditor/empirical-tests/test_965_*.py`.
- `builder_auditor_deny_hook` REFUSES any builder Bash call that names that
  path. Measured this batch: `ls` and `git log` on it were both refused.
- That refusal is correct by the separation rule, so the assignment is
  structurally wrong, not merely late. hover picked cc by least-loaded, without
  roster or boundary checks (its own `owner_note` says so).
- **Next:** Michael or hover reassigns it to hover2. The independent second
  auditor is the only role that can read the script. Do not route around the
  hook.

**C-3. `ctxmeter.py` false-floor bug.** Michael chose to skip it (b71). Next:
Michael names the path. Then fix it and cause-tag the fix in
`docs/recurring-bug-classes-2.md`.

**C-4. Live blocks for `sd_crm.read`, `dnt_rollup.read` and
`exec_context.read`.** These need credentials Michael has to provision:
admin/sales/install on `SD-AUDIT-2026`, and a dental audit licence with
owner/frontdesk/provider. Then:
- generate the fixture SQL from `seed()` in
  `tools/sairn_field_scope_check.py`;
- add `live` blocks to `tools/field_scope_rules.json`;
- run `python tools/sairn_field_scope_check.py --live --only sd_crm.read,dnt_rollup.read,exec_context.read`.

**C-5. #1756 authenticated caregiver-device live run.** It needs readable
SEN-AUDIT-0002 caregiver credentials.
- Sign in as the caregiver, then hydrate.
- Confirm that `sen_caregivers` in localStorage holds only the caregiver's own
  row, with no `bgcheck_date`, `state_caregiver_id` or `notes`.

### Routed to other owners

| # | Item | Owner | Exact next step |
|---|---|---|---|
| R-11 | dental addCredential hold outside the `try` (LOW, from C-2) | cody | Move `rCredentials(null)` inside the `try` at `sairndental.html:3104`. Add an arm where `rCredentials` throws once, then assert that a second add is accepted. |
| R-12 | mechCredAdd and mechAssetAdd have no `.catch`, so a rejected write shows nothing (predates b64) | cody | Add a `.catch` that writes the error into `mech-cred-err` / `mech-asset-err`. |
| R-13 | hover b92 `test_965` review assigned to a builder | Michael / hover | Reassign to hover2 (see C-1). |
| R-1..R-10 | as listed in `SAIRN-handoff-cc-b72.md` §2 | unchanged | Not re-verified this batch. Read them there. |

## 3. Assumptions stated

- **The context window was declared at 200,000, not 1,000,000.** b72's digest
  measured against 1M. I could not confirm this session's window, so I took
  the size that makes the percentage the ceiling.
- **"Discharge the most overdue first" was read as cc's OWN obligations**,
  meaning `ASSIGNED TO cc`. Of the two, C-1 is older but cannot be done by a
  builder, so C-2 was done.
- **No `--takeover` was attempted.** The 580h `quotes` record (fourth, assigned
  to cody) is the most overdue of the 17 overdue obligations, and cc is
  eligible to take it over.
