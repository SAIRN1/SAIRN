# SAIRN handoff — hank b43 — 2026-10-21

**Subject:** removing the b42 test quote request on SD-AUDIT-2026; carried items reviewed. No application code
changed. Written before the report, nothing half-finished.

## 1. PUSHED STATE
This batch commits `sql/sd_audit_b42_test_request_cleanup.sql` and these three documents. **NOT FORCED.**
Re-derive the tip after the push.

## 2. CLAIMS HELD
None (released at the end of the batch).

## 3. THE ITEMS
**Test request — concept:** *remove it through the app's own path, which is a reversible soft delete;
permanently erasing the row and its photo is an irreversible data delete, so it goes to Michael as a reviewed SQL
file rather than being run by an agent.*
- Live, as audit-owner on `SD-AUDIT-2026`: `soft_delete` `QR-1792602627030-534` → **200 ok**. Read-back: inbox
  **0 rows** (no longer listed); `tombstones` **lists it**; `request_photos` still returns **1** — soft delete does
  not touch `sd_quote_request_photos`, by design.
- **Permanent removal is NOT done.** `sql/sd_audit_b42_test_request_cleanup.sql` deletes the photo row, the
  request row and the unpublished test shop row (`sd-audit-b42-test`), each scoped to the audit licence hash AND
  the exact test id, with BEFORE counts (expect 1/1/1) and AFTER counts (expect 0/0/0). Column names checked
  against `sql/stonedesk_public_surface_schema.sql` and `sql/stonedesk_intake_photos_2026-09-03.sql`.

**Carried items (b38 §4) — none is actionable from this clone:**
| # | item | why it waits |
|---|---|---|
| H2 | Bash deny on cc, cody, fourth | each clone's untracked `settings.local.json`; the classifier refuses an agent writing permission settings — Michael runs `add-deny-cs.ps1` per clone (b38 §4 has the command) |
| H3 | `~/fix-deny.ps1` case-insensitive dedup | file is outside the repo, in Michael's home dir — Michael |
| C | Static Maps on the Maps key | Google Cloud Console — Michael |
| B | snapshot re-export (b35 G) | Michael, per `SAIRN-handoff-hank-b35.md` §4 |
| D | untracked `conflict_excerpt.txt` etc. | not mine; not touched |

**Incident, mine, repaired:** retrying a raced push I ran `git stash -- docs/scrutiny-flags.json` on a clean file
(stashed nothing) and then `git stash pop`, which applied an OLDER stash — `b10-settings-park` — and rewrote
`.claude/settings.json` (+20/−155). Not committed, not pushed. Repaired: the diff saved to the scratchpad, the
file restored to HEAD, and the dropped stash commit `3a6d455fd` put back with `git stash store` (now
`stash@{0}`). Lesson: never `pop` after a `stash` whose output was suppressed — check it created an entry.

## 4. OPEN, AND THE EXACT NEXT STEP
| # | open | next step |
|---|---|---|
| X1 | permanent removal of the test request, photo, shop row | Michael: run `sql/sd_audit_b42_test_request_cleanup.sql` in the Supabase SQL editor; send back the AFTER counts |
| S1 | other suites slicing `SD_DATA` by a fixed window from `indexOf(name)` (b42) | available to hank if dispatched |
| T1 | Tier A on `sd_quote_requests` | cc |
| H2/H3/C/B/D | above | Michael |

## 5. TRANSCRIPT
 C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-hank\a9d72ca8-d218-42be-9363-f759795e9517.jsonl
