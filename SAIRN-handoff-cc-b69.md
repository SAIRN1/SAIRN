# SAIRN handoff: cc, batch b69, 2026-10-29

**All six items are closed.** Landed at `f0d9151c` (see the digest for the
final tip). No `--force`, no override, no skip.

| | |
|---|---|
| Claims | `platform` (b69), released with this handoff. |
| Context | see the digest's CONTEXT line (measured). |
| Transcript | `C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cc\52164776-0b08-422d-94e1-7a56daf3eaaa.jsonl` |

## 4 (done first). Start-of-batch re-verification, before touching shared config

- **Hook presence: 4/4 OK.** The install regression test passed 37/37.
- **Owner-map authority:** every cc tool is `OWNER_LINE` cc.
- **But `tool_owner_map --check` exited 1.** The map had drifted from git
  since b68 through other sessions' commits. It was regenerated this batch.

## 1. The watchdog's operator is hank

- **Recorded in the tool's own header** (`OPERATOR: hank`). hank runs it at
  the START of each of its batches; the findings always go to
  `~/SAIRN-SESSION-LOCKS/watchdog-findings.json`; cc owns and fixes the tool.
- **Recorded in its TOOLING-INVENTORY entry** (OWNER cc, OPERATOR hank).
- **`docs/tool-owner-map.json` is generated** and has no operator field, so
  the owner row stays cc (OWNER_LINE) and the operator lives in the two
  places above.

## 2. The 23 undeclared role-scoped reads

**Why they were still open.** b62 routed all 23 to hank as `api/` owner.
None was declared, and the rules file was assigned to hank alone.

**How the owners were derived** (`docs/2026-10-29-cc-b69-field-scope-routing.md`):
- `git blame` could not say who designed each branch. 21 of them blame to
  one sweeping refactor (`48866588`) or to subjects that name no session.
- So each read goes to its app's most frequent claimant **all-time**:
  sairnsenior → hank, sairncare → fourth, roofing and build → cody,
  stonedesk and dental → cc.
- Two exceptions:
  - `alf_mar` stays with hank, for his b51/b53 MAR role-scope work.
  - The platform reads (`employees`, `employee_profile`, `sdn_clients`) go to
    hank as the `api/` owner.

**cc's three, DECLARED from their design commits:**
- `sd_crm.read` (`a4f0a1a0`): management sees every lead; others see only
  their own assigned leads; unassigned leads are management-only.
- `dnt_rollup.read` (`af5aeddf`): owner only; no row markers in the body;
  frontdesk and provider refused.
- `exec_context.read` (`562d1ded`): owner/admin only.

**How they were checked:**
- Handler mode across all 8 rules: **38/38 clean**.
- My first `dnt_rollup` seed made `location_id` a marker, and the run
  reported a LEAK. The roll-up's output is *keyed by office*, so the seed was
  corrected to a literal office id. The reason is in `declared_from`.
- Ablation: four wrong declarations were each caught, as LEAK, MISSING and
  2× COULD NOT RUN, never as a pass.
- **A Tier A obligation is opened** for the three rules and assigned to hank.

**The other 20, queued with owners:** hank 6, fourth 6, cody 8.
`tools/field_scope_rules.json` is added to **cody's and fourth's**
`assigned_overrides` (`_assigned_overrides_why_cc_b69`), so each can declare
its own.

**Not live-driven:** stonedesk and dental have no audit credentials or
seeded fixtures for this check yet.

## 3. CRLF audit of cc's write paths

**The scan:** an AST pass over all **69** cc-owned tools and tests found
**54** text-mode writes with no `newline=`.

**One is a persisted, LF-sensitive production writer:** the two log appends
in `tools/logged_exec.py`.
- They write `.git/sairn-exec-log.jsonl`. The live file has 3 of 3 rows
  ending CRLF.
- Both now go through `append_line()` with `newline='\n'`.
- A new fixture reads the bytes back. Removing the fix turns it red with the
  CRLF bytes.
- The 3 existing CRLF rows are left in place (append-only log).

**The other 53** are selftest or temp-harness fixtures:
- the hook, presence, done-line and watchdog selftests;
- `field_scope_check`'s temp replay config, which is JSON and tolerant of
  CRLF;
- the stress tools' node harness files;
- the `prepush_refline_repro` temp repo.

None of them persists or is byte-compared.

**Already binary, re-checked:**
- the deny hook's log append (`os.open` with `O_BINARY`) and its mirror (a
  byte copy);
- `builder_hook_presence`'s `atomic_write` (`wb`);
- `sairn_done_line`'s state file and `sairn_watchdog`'s findings file (both
  `newline='\n'`).

## 5. Deny-block log format: field parity with H1

**The last difference.** H1's live `block_log()` replaces **each** tab, CR or
LF character with one space. cc's `re.sub('[\t\r\n]+')` collapsed a whole run
into one space. That was H1 b103's 2-of-6 one-byte differences.

**The fix.** `block_line()` now uses H1's formula character for character.
Everything else was already identical:
- the same 5 columns: ts, agent[/subagent], path, tool, reason;
- the same UTC format;
- the 400-character cap;
- `O_APPEND` with LF.

A **PARITY** arm compares the two on a hostile field. Reverting to the old
sanitiser turns it red. The selftest is 95 arms.

**Live**, after refreshing all four clones (settings byte-identical,
regression test 37/37):
- a fresh refusal at 11:30:17Z wrote an LF-only row, byte-identical when
  re-sanitised by H1's formula;
- all **35 rows have 5 columns**; the 15 CRLF rows are H1's older rows, kept
  because the log is append-only;
- the Drive mirror is a byte copy (4,852 = 4,852).

## For H1 (routed; audit layer, not touched)

H1's b105 drafted recurring-bug-class row (4) lists **#1756 as unfixed**. It
was **fixed and live-verified in cc b67** (`c2b3a90b`): the served
`sairnsenior.html` purges out-of-scope caregiver rows and HR fields on merge.

## 6. OPEN

| Item | Owner | Next |
|---|---|---|
| Declare the routed reads (`docs/2026-10-29-cc-b69-field-scope-routing.md`) | hank 6, fourth 6, cody 8 | `alf_mar` first |
| Review the three new field-scope rules (Tier A obligation) | hank | discharge |
| Run the watchdog at batch start | hank | from now on |
| hank's registry row still names b61 (b68 finding) | hank | `sairn_status.py set` |
| Live blocks for `sd_crm`, `dnt_rollup` and `exec_context` | cc | needs audit credentials and seeded fixtures |
