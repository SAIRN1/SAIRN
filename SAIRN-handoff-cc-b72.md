# SAIRN handoff: cc, batch b72, 2026-10-29: STOP AND CLOSE OUT

This is a **stop-and-close-out batch.** No new tasks and no new claims.

**Numbering.** The dispatch's closing line said `done b71`, but b71 was
already closed (`ef064e78`). So this is **b72**, and b71 was not overwritten.

| | |
|---|---|
| In-flight change at the stop | **none**: `git status` clean, no stash, 0 commits ahead of origin, no cc claim active |
| Final SHA | see §1, measured after the push of this handoff |
| Context | see the digest's CONTEXT line (measured) |
| Transcript | `C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cc\52164776-0b08-422d-94e1-7a56daf3eaaa.jsonl` |

## 1. Final state

**At the stop:**
- The clone was clean, with nothing to commit, and 36 commits behind other
  sessions. It was fast-forwarded to `1d90a1c2`.
- HEAD was `ef064e78`, the b71 handoff tip.

**The final SHA after this handoff's push** is in the report and the digest.
It is read with `git rev-parse HEAD` and compared with `git rev-parse
origin/main` after a fetch. It is never guessed.

## 2. Every open item, with its exact next step

### cc's own

**C-1. Tier A review: hover b92 `test_965`** (opened 2026-10-28T21:14:26Z).
- Blocked until hover lands
  `.claude/skills/sairn-hover-auditor/empirical-tests/test_965_sen_caregivers_phone_unredacted.py`
  on main.
- Then read the script against the `sen_caregivers` read branch
  (`api/sd-data.js`, about line 7524) and drive its two negative controls:
  phone added to the redaction list must exit 1; the list renamed must exit 3.
- Discharge with:

      python tools/tier_a_review_gate.py --discharge hover 2026-10-28T21:14:26Z --body-file <verdict>

**C-2. Tier A review: cody b64 re-entry guards** (opened
2026-10-29T13:40:41Z; NEW, arrived after b71).
- It covers push-then-toast save handlers in sairncare, sairncode,
  sairndental and sairngrounds, across 35 resources.
- Find the commit with:

      git log --oneline --author-date-order -20 -- sairncare.html sairndental.html sairncode.html | grep "cody b64"

- Review that each re-entry guard is released on every exit path (success,
  failure, throw), so a save button cannot stay disabled.
- Discharge with:

      python tools/tier_a_review_gate.py --discharge cody 2026-10-29T13:40:41Z --body-file <verdict>

**C-3. `ctxmeter.py` false-floor bug.** Not found anywhere; Michael chose to
skip it (b71). Next: Michael names the path, then fix it and cause-tag the fix
in `docs/recurring-bug-classes-2.md`.

**C-4. Live blocks for `sd_crm.read`, `dnt_rollup.read` and
`exec_context.read`.** The credentials are genuinely missing (b70).
- Next, once Michael provisions admin/sales/install on `SD-AUDIT-2026` and a
  dental audit licence with owner/frontdesk/provider:
  - generate the fixture SQL from `seed()` in
    `tools/sairn_field_scope_check.py`, the way
    `sql/field_scope_live_fixture_sen_branches_2026-10-28.sql` was built;
  - add `live` blocks to `tools/field_scope_rules.json`;
  - run `python tools/sairn_field_scope_check.py --live --only sd_crm.read,dnt_rollup.read,exec_context.read`.

**C-5. #1756 authenticated caregiver-device live run** (b67). It needs
readable SEN-AUDIT-0002 caregiver credentials.
- Next: sign in as the caregiver on a device whose localStorage holds the
  full roster.
- Hydrate, then confirm that `sen_caregivers` in localStorage holds only the
  caregiver's own row, with no `bgcheck_date`, `state_caregiver_id` or
  `notes`.

### Routed to other owners (cc does not act on these)

| # | Item | Owner | Exact next step |
|---|---|---|---|
| R-1 | Declare the routed field-scope reads | hank 6, fourth 6, cody 8 | Per `docs/2026-10-29-cc-b69-field-scope-routing.md`, `alf_mar` first. Then `python tools/sairn_field_scope_check.py --validate` and run it bare. |
| R-2 | Review the three new field-scope rules (Tier A, cc b69) | hank | `tier_a_review_gate.py --discharge cc <opened_at>` |
| R-3 | O7: push-script regeneration | cody | Apply the block in `docs/2026-10-29-cc-b70-o7-push-script.md` to `push_once.sh`, or switch to `python tools/push_retry.py`. |
| R-4 | b58 test gaps | cody | Assert the MECH_RECORDS request shape (merge-duplicates / on_conflict); gitignore `api/.sd-data-ablate-*.js`. |
| R-5 | b61 test gaps | cody | Execute `sfConfirmOnServer` in a test; add arms for an id-only key, pre-network confirmation and the unreadable guard (`:2138`); expire entries; wipe on a legacy device. |
| R-6 | b57 mechBackup test gaps, and the redaction probe broken by b58 | cody | As routed in cc b67 §3. |
| R-7 | Registry row behind its handoff (the watchdog flags it every 15 min) | hank | `python tools/sairn_status.py set --state ... --task "<current batch>"` |
| R-8 | `block_log` CRLF (b66) | H1 | Done by H1 in `5c572340`. No action. |
| R-9 | `alf_clients/read` gives billing and activities medications and diagnosis (b64) | Michael | Decide whether "billing never reads the MAR" covers profile fields. |
| R-10 | `agent-ad8f80cc19dee3bb4` worktree in `Documents/SAIRN` holds an uncommitted `api/claude.js` edit | Michael | Keep, commit, or `git worktree remove --force` it. |

### Running infrastructure a cold session should know is live

- **Windows Task Scheduler `SAIRN-watchdog`** runs every 15 minutes and
  writes `~/SAIRN-SESSION-LOCKS/watchdog-findings.json`. "Last Result 1"
  means findings, not failure.
- **The deny hook and presence check are in all four builder clones**, at
  blob `22b205e8`.
  - Re-verify at batch start with `python tools/builder_hook_presence.py`
    and `python tests/run_builder_hook_install_regression.py`.
  - After any landed hook change, refresh with
    `python tools/builder_hook_presence.py --install`.
- **The done-line Stop hook is armed.** End every batch with
  `python tools/sairn_done_line.py --batch b<n>`, then send exactly its line.
