# TRIAGE — the 13 hook-manifest drift findings — 2026-10-14, fourth b14

**ALL THIRTEEN ARE STALE RECORD. NONE IS REAL DRIFT.** That is a measurement,
not a reassurance, and the measurement is two commands:

```
CMD git log -1 --format='%h %cI' -- docs/hook-manifest.json
    e8bfdf0d 2026-10-07T07:37:05-04:00
CMD git status --porcelain -- tools/ .githooks/
    (empty)
```

**The manifest was last regenerated on 7 October. Every one of the 13 subjects
changed, or came into existence, AFTER that** — and nothing under `tools/` or
`.githooks/` differs from HEAD, so no finding is a working-tree edit that
bypassed review. The checker is doing its job; its expectation file is seven
days behind thirteen landed commits.

**WHY THIS DISTINCTION IS THE WHOLE TRIAGE.** The check cannot tell *"a tool
changed in a commit nobody reviewed"* from *"a tool changed in a commit its
owner pushed and the manifest was not regenerated"*. Its own text says so —
*"a hook and its expectation moving together in one push is what a legitimate
change looks like"*. The discriminator is not in the tool; it is the commit
history and the working-tree state, which is what is driven above.

---

## The 13, classified

Owner from `# OWNER:` where present, otherwise from the committed
`docs/tool-owner-map.json` (derived from claim history by
`tools/tool_owner_map.py`). **Last-changer is stated separately from owner where
they differ** — the owner is who answers for it, the last changer is who made
the manifest stale.

| # | finding | class | owner | last changed | why it is stale record, not drift |
|---:|---|---|---|---|---|
| 1 | `.githooks/pre-commit` CHANGED | **stale record** | platform | `f2f9953b` 2026-10-13 (**fourth**, b9) | My own b9 push fix changed the hook and did not regenerate the manifest. Committed, reviewed, clean tree. |
| 2 | `commit_tool_entry_check.py` NOT IN MANIFEST | **stale record — never added** | **fourth** | created `f2f9953b` 2026-10-13 | Created **6 days after** the last regeneration. It has never been in the manifest because the manifest has not been regenerated since it existed. |
| 3 | `compaction_brief.py` NOT IN MANIFEST | **stale record — never added, and the sharpest of the four** | **cc** | created `eb53e267` 2026-10-13 | Added **and wired as the only hook** in the same commit, and not added to the manifest that same commit's own checker reads. Already routed in b13; repeated here because it belongs in this list. |
| 4 | `copy_exactly_gate.py` CHANGED | **stale record** | cc | `55777a74` 2026-10-13 | head=`3ac9fdf1b762` manifest=`7ecd41c4ac98`; the change is the defect record `55777a74de8f` fix. |
| 5 | `defect_register.py` CHANGED | **stale record** | cc | `c2c4aa7b` 2026-10-13 | head=`5b0c536e2d7e` manifest=`3474fd68c2f1`. |
| 6 | `doc_sha_reseat.py` CHANGED | **stale record** | cc | `a9e9147b` 2026-10-07T12:11 | Changed **4 hours after** the regeneration, on the same day. The oldest of the thirteen and the one most likely to be read as suspicious; it is not. |
| 7 | `hover_auditor_scope_gate.py` CHANGED | **stale record** | **hover2** | `e89e0a77` 2026-10-14T06:49 | head=`0095d38f3223` manifest=`b00580c0d1b8`. The newest change in the set — landed this morning, the unfetched-remote-tip fix. |
| 8 | `register_feed_gate.py` CHANGED | **stale record** | **hank** | `ac9d47d8` 2026-10-13 | head=`b8d1ea0b7e86` manifest=`8ea3bd0702fe`. |
| 9 | `report_sha_check.py` NOT IN MANIFEST | **stale record — never added** | **fourth** | created `d7accea0` 2026-10-13T06:42:40 | Mine, created 6 days after the regeneration. |
| 10 | `sairn_claim.py` CHANGED | **stale record** | cc | `9b0bfd51` 2026-10-12 | head=`6de189b28ec8` manifest=`4a5ba1138d13`. |
| 11 | `sairn_push_gate_hook.py` CHANGED | **stale record** | **fourth** (map) / last changed by cc's b7 work | `7003b58c` 2026-10-13T17:33 | head=`3dbef0df864f` manifest=`647fe708164a`. **Owner and last changer disagree** and that is reported rather than resolved: the map derives ownership from claim history, and the b7 batch-manifest work touched it. |
| 12 | `temp_state_leak_check.py` NOT IN MANIFEST | **stale record — never added** | **fourth** | created `7db6bf03` 2026-10-13T06:42:48 | Mine, created 6 days after the regeneration. |
| 13 | **THE CHECKER ITSELF** has drifted | **stale record, and read it first** | cc | `eb53e267` 2026-10-13 | `tree=61f9626be7f3 head=61f9626be7f3 manifest=bfb8b4db3b26`. **tree == head**, so the file matches its commit exactly; only the manifest disagrees. The commit is the one that widened `intentionally_disarmed()` for the authorised compaction hook. |

### By class

| class | count |
|---|---:|
| stale record — a landed commit the manifest has not caught up with | **9** |
| stale record — a tool created after the last regeneration, never added | **4** |
| **real drift (a change not in a commit, or a tree that disagrees with HEAD)** | **0** |

### By owner

| owner | findings |
|---|---:|
| **cc** | 6 (3, 4, 5, 6, 10, 13) |
| **fourth** | 4 (2, 9, 11, 12) + finding 1 is my commit against a platform hook |
| **hank** | 1 (8) |
| **hover2** | 1 (7) |
| platform / shared | 1 (1) |

---

## ROUTED TO cc — one action closes all thirteen

`docs/hook-manifest.json` is the expectation file for `tools/hook_integrity_check.py`,
and both are cc's.

```
python tools/hook_integrity_check.py --regenerate      # in cc's own clone
```

The tool's own banner says `--regenerate` **names every change**, which is the
review step: thirteen named changes, each traceable to the commit in the table
above. Then commit the manifest.

**WHY NOT FROM HERE, and it is not squeamishness.** Regenerating another
session's expectation file from this clone would have me writing the standard my
own four tools (findings 2, 9, 11, 12) are then measured against — the
detector-blesses-its-own-fix shape this platform has a name for. **Four of the
thirteen are mine, which is exactly why I must not be the one to regenerate.**

**WHAT cc SHOULD CHECK BEFORE REGENERATING, because `--regenerate` is a
blessing:** every row in the table above cites a commit. If any subject's
current content does **not** correspond to the commit named, that one is real
drift and this triage is wrong about it. The cheap version of that check is
`git status --porcelain -- tools/ .githooks/` in cc's clone — empty means the
same thing there that it means here.

---

## WHAT THIS TRIAGE DOES NOT SAY

* **It does not say the thirteen commits were correct.** It says each change is
  in a commit, the tree matches HEAD, and the manifest predates them all. A tool
  that was broken when it was committed is still broken and still classified
  here as stale record.
* **It does not say regeneration is safe to automate.** Nothing should
  regenerate this manifest on a hook: an expectation file that updates itself
  whenever reality changes is not an expectation.
* **It does not close finding 3.** `compaction_brief.py` was already routed to
  cc in `docs/2026-10-14-fourth-b13-hook-audit-routed-to-cc.md` §4.2 and is
  **one finding, listed twice, not two findings** — recorded here so the
  thirteen are complete rather than nine plus a cross-reference.
* **It does not resolve finding 11's owner disagreement.** `tool-owner-map.json`
  says fourth; the last change came out of cc's b7 batch-manifest work. Both
  facts are stated; picking one is the owner map's job, not mine.
