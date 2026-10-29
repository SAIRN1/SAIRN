# SAIRN handoff: cc, batch b68, 2026-10-29

**All six items are closed.** Landed at `c0213b1d` (see the digest for the
final tip). No `--force`, no override, no skip.

| | |
|---|---|
| Claims | `platform` (b68), released with this handoff. |
| Context | see the digest's CONTEXT line (measured). |
| Transcript | `C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cc\52164776-0b08-422d-94e1-7a56daf3eaaa.jsonl` |

## 1. cody's deny hook is refreshed

Run on Michael's ruling: `python tools/builder_hook_presence.py --install`.
- The presence check reports **4 of 4** clones carrying hook blob `b7d0f20b`.
- `settings.local.json` was untouched: the refresh copies the hook files only.

## 2. The watchdog, operated live

**Run 1 (10:15Z): 0 findings, 0 could-not-check.** A run that clears
everything is the result to distrust, so I printed its inputs:
- Only **cc** holds an active claim, so a zero for OVERLAP, STALE-CLAIM and
  NEXT-DRIFT was **correct**.
- The tracked claim files agree with the registry.

**The inputs showed a real mismatch the tool never checked.** Two registry
rows name an older batch than the agent's own last handoff:
- **cody**: the row says `b59`; the last handoff is `SAIRN-handoff-cody-b60.md`.
- **hank**: the row says `b61: push_retry pure-base fast retry (C1)…` and was
  last updated 2026-10-28T20:00 local; the last handoff is
  `SAIRN-handoff-hank-b63.md`.

No flag looked at idle rows, so I added **REGISTRY-BEHIND** (mechanical, any
state). The watchdog is now 16 arms.

**Run 2 (10:16Z): exactly those 2 findings.**

**Run 3 (10:35Z):** only hank's is still open. cody's row had moved on in
between, so the tool tracks live state.

**Open real hit: hank's registry row is stale.** hank needs to run
`sairn_status.py set` at the next batch start.

Output: `~/SAIRN-SESSION-LOCKS/watchdog-findings.json`.

## 3. Full-corpus deny-hook replay

**The corpus.** It uses the b67 selection rule: every write and command tool
call in each builder's last three transcripts.
- It is now **6,041 calls**: cc 1,735, hank 1,421, cody 1,388, fourth 1,497.
- It was 5,874 at b67. The transcripts have grown since, and that cannot be
  frozen after the fact.

**Results:**
- **The 2 b67 false-positive shapes** (cody heredocs rewriting the path
  manifest that name hover tools only as data) are **present in the corpus
  and refused 0 times**.
- 89 refusals in total:
  - 65 are text references to auditor paths, refused by spec;
  - 10 are Edit/Write into hover clones;
  - **14 are write-only, every one a real write**: cc's Edits of the scope
    gate and separation audit, cc's `git show HEAD:x > tools/hover_…`, cody's
    `git stash push tools/hover_separation_audit.py`, and my own three b67
    live tests.
- Latency: p50 5 ms.

## 4. Install regression test: `tests/run_builder_hook_install_regression.py`

**What it asserts, after an install, per builder clone:**
- **R1**: each `.git/sairn-hooks` copy equals `git show origin/main:tools/<f>`
  **byte for byte**, with no newline normalisation. This closes two drift
  classes: a stale copy after a change landed (b66), and a text-mode
  "copy" (the b66 mirror).
- **R2**: the installed hook, *imported from its installed path*, computes
  the same auditor dirs and auditor-tracked list as the tracked tool reading
  **that clone's** live path manifest and the live hover-scope manifest, and
  it actually read the hover-scope manifest.
- **R3**: `decide()` agrees with the tracked tool on 6 payloads, and gives
  the intended 3 refusals and 3 allows.
- **C1**: a one-byte change is detected.

**Live: 37/37 across cc, cody, fourth and hank.**

**Ablations.** These ran cumulatively in one process, so the counts stack:
- CRLF reference bytes: R1 ×12;
- floor-only scope: +4 R2;
- an allow-all `decide()`: +R3.

**One choice to state.** I read "the live tracked manifest" as two things:
the tracked tool files on origin/main (R1), and the manifests the hook reads
its scope from (R2). The test checks both.

## 5. Ownership

`tools/tool_owner_map.py` regenerated `docs/tool-owner-map.json`. It was
stale by 286 rows.

| Tool | Basis | Owner |
|---|---|---|
| `tools/sairn_watchdog.py` | OWNER_LINE | cc |
| `tools/builder_auditor_deny_hook.py` | OWNER_LINE | cc |
| `tools/builder_hook_presence.py` | OWNER_LINE | cc |
| `tools/tooling_inventory.py` | **OWNER_LINE (new)**; it was CONTESTED | cc |
| `tools/sairn_done_line.py` | OWNER_LINE | cc |
| `tests/run_builder_hook_install_regression.py` | OWNER_LINE | cc |

**None are ownerless.**

**Why cc for `tooling_inventory.py`.** I added `# OWNER: cc`. The path
manifest gives `tools/` to cc, and the derived owner was cc. hank, fourth and
cody have also claimed it, and hank and fourth keep their assigned overrides
to edit it.

The test and `docs/tool-owner-map.json` (a fourth-owned area) are declared as
cc's assigned b68 paths (`_assigned_overrides_why_cc_b68`).

## 6. OPEN

| Item | Owner | Next |
|---|---|---|
| Registry row stale: task "b61" against handoff b63 | hank | `python tools/sairn_status.py set ...` at the next start |
| The watchdog has no operator or cadence | Michael | Choose where it runs: a SessionStart line, cron, or chat |
| #1756 authenticated device run (b67) | cc | Needs readable audit credentials |
| H1 `block_log()` CRLF (b66) | H1 | `O_BINARY` |
| mechBackup test gaps (b67) | cody | as routed |
