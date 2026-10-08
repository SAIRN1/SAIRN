# `docs/hank-evidence/` — the scripts and data that committed documents CITE

**WHY THIS DIRECTORY EXISTS.** Committed documents, test headers and
defect-register records were citing files that lived only in a session scratchpad
under `%TEMP%`. A citation that resolves to a temp directory is a **dangling
citation the moment that directory is cleared** — and this platform already keeps
`docs/citation-absent-register.json` because that failure has happened before.

Audited 2026-10-08 (batch 19 item 10): committed artefacts in this repo cite
**six of my scratchpad files by name**. Those, plus the generators for documents
that are committed, are here.

**DELIBERATELY NOT IN `tools/`.** These are **one-off evidence scripts**, not
platform tools. Putting them in `tools/` would enrol them in the tool inventory,
`report_only_checks.REGISTRY`, `first_article_inspection.py`'s header-claim
population and the bare-run sweep — four populations that exist to govern tools
somebody depends on. `docs/purge-evidence/` is the precedent for evidence that
belongs in the repo without being a tool.

**READ-ONLY BY CONSTRUCTION unless the header says otherwise.** Each one states
what it reads and what it writes in its own docstring; nothing here writes to the
repository.

| file | cited by | what it is |
|---|---|---|
| `attr_scan.py` | `tests/sd_data_write_attribution_three_apps.js` header, two defect-register records, two handoffs | the write-attribution scan behind **UNATTRIBUTED 0 of 49**. Read-only: opens `api/sd-data.js` once and writes nothing |
| `audit_gap.py` | `docs/2026-10-07-hank-migration-sql-for-michael.md` | the audit-table gap scan that produced STEP 0's three ALTERs |
| `tools_sweep.tsv` | two handoffs, batch 18 items 5/6/9 | the captured exit code of all **315** scripts under `tools/` at HEAD `7406ab27`. The **data**, not a script — every later tally derives from it |
| `b2_item3_rerun.py` | `docs/2026-10-08-hank-suite-failure-owners.md` | re-runs each failing suite file ALONE on a restored tree. Produces `i3.rerun.json` |
| `b3_item3.py` | — (it GENERATES `docs/2026-10-08-hank-suite-failure-owners.md`) | the generator. **A committed document whose generator is not committed cannot be regenerated**, which is the whole reason this one is here |
| `b2_item6_pass2.py` | batch 18 item 6 | every complete command line for the could-not-run tools, written out rather than described |
| `b2_barehunt.py` | batch 18 item 6a | the negative control that eliminated 62 tools as the `core.bare` writer |
| `b3_item4_evidence.py` | `docs/handoff-hank-2026-10-08.md` item 4 | the lock/worktree removal-evidence gatherer. **Removes nothing** |
| `b3_item8.py` | `docs/handoff-hank-2026-10-08.md` item 8 | times one tool to completion with the load sampled throughout |
| `appendfrag.py` | — | appends a fragment to a handoff with LF endings. Here because a heredoc kept truncating documents on apostrophes, and that is worth not rediscovering |

**WHAT IS *NOT* HERE, and why.** Session plumbing with no citation and no reuse —
landing scripts, report builders, sha-repointing, per-item `.out` captures. Those
are registered in **`docs/external-files-index.json`** with their directory, so a
reader can find them while they exist and knows not to expect them later.

**OTHER SESSIONS' SCRATCHPAD CITATIONS ARE NOT MINE TO MOVE.** The same audit found
`gapverify.py`, `verify_specs.py`, `prefix_demo.py`, `grd_enum.py`,
`cite_measure.py`, `sfdrift.py` and several `b2x`/`r21`/`pinned_*` artefacts cited
by cc's, cody's and fourth's committed documents. **Those are the same defect in
their files** and are named in my handoff for them, not relocated by me.
