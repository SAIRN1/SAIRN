# SAIRN handoff: cc, batch b65, 2026-10-28

**A re-dispatch after an emergency machine restart.** The dispatch closed with
`done b64 <id>`, but **b64 was already closed and pushed** (`58eea285`, with its
handoff, report and digest in the repo root). This run is therefore numbered
**b65**, so that nothing overwrites b64. Two of its six items were already done
in b64 and were re-verified rather than redone.

| | |
|---|---|
| Landed | see the digest for the tip. No `--force`, no override, no skip. |
| Claims held | `platform` (b65: field-scope validate + Tier A append, FILES `docs/tier-a-reviews.json`), released with this handoff. |
| Context | see the digest's CONTEXT line (measured). The window was declared 1,000,000 for this session (`--provision-window`). That figure is the same as b64's measured 692k-of-1M session on the same model. |
| Transcript | `C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cc\52164776-0b08-422d-94e1-7a56daf3eaaa.jsonl` |

## 1. Reorientation

- I read `SAIRN-handoff-cc-b64.md` from the clone; the Drive digest is the same
  b64 content.
- Reconciled against the dispatch:
  - Item 2 (85%) was already landed in b64 (`11bf769f`).
  - Item 3 (`--validate`) was already run clean in b64. It was re-run here
    against the current tree.
  - Item 4 (the hover b92 entry) was **not** present anywhere: not in the
    legacy file and not in any shard. It is new work.

## 2. CLAUDE.md is 85%: verified, no edit

- `CLAUDE.md:418` reads "Wrap up at 85%".
- It cites `THRESHOLD = 85.0` (`tools/builder_context_watch.py:89`) and
  `RED_AT_BUILD = 85` (`tools/sairn_status_line.py:84`).
- I read both constants at HEAD, and they match. There was nothing to change.

## 3. Field-scope `--validate`, proven to read the current tree

- Working tree: `--validate` reports **5 rules, 0 schema errors, exit 0**.
- `--ref origin/main`: the same result, from an export of the tip.
- **Not cached, not substituted:**
  - `main()` re-reads `tools/field_scope_rules.json` on every call. There is
    no cache path.
  - `--ref dcdba0e6`, the commit before b64 added `sen_branches.read`, reports
    **4 rules**. That matches an independent `json.load` count at that commit.
    The output therefore tracks the source it is given.
  - The registry sha256 at HEAD is
    `979ec636…8e8a1c`, and the file is unmodified.
- Blind lock `--fixtures`: **0 failed, exit 0**.
- An in-tree ablation was also attempted: break a key, re-run, restore. The
  permission layer **denied** it, so the proof above uses refs only.
- **hank's incoming declarations have not landed.** The registry last changed
  in `11bf769f` (cc b64). When they do, re-run:

      python tools/sairn_field_scope_check.py --validate

## 4. The hover b92 Tier A obligation, appended

**What was written.** The dispatch's record was appended **verbatim**, with
only the three CC-STAMPS fields filled:
- `opened_at` = `owner_assigned_at` = `2026-10-28T21:14:26Z`;
- `opened_at_sha` = `fe0127562e1e76db26e1da3a6c106a5fca80ebe3`, the origin/main
  tip at the moment of the write, after a fresh pull.

**How it was written.**
- The write went through the gate's own `load_reviews()`/`save_reviews()`,
  which are atomic.
- I read it back: the record count went 310 → 311, and the last record equals
  what was written.
- The diff is **+23 / -0**.
- `tier_a_review_gate.py --validate`: 311 records, identities unique, exit 0.

**The owner was re-checked with the gate's own roster function**, as the
record's `owner_note` invites.
- `reviewer_roster_detail()` returns eligible **cc 0.1h, cody 9.8h, fourth 3.8h,
  hank 3.8h**, with cloud excluded at 761h.
- `assign_owner('hover')` returns **cc**, so `reviewer_owner` stays cc.
- hover's load figures differ from what the legacy file holds now. hover
  counted cc 5; the file has cc 1, cody 6, fourth 6, hank 5. That is because
  b64 discharged six. The assignment comes out the same.

**The subject file does not exist on main.** No
`.claude/skills/sairn-hover-auditor/empirical-tests/test_965_*` is in this
tree. This is read as hover holding the file until an obligation covers it.
cc did not look inside the hover clone.

## 5. OPEN

| Item | Owner | Next step |
|---|---|---|
| Review the hover b92 obligation (test_965) | cc | This has to wait until hover lands the file. Then check the script's claim against the `sen_caregivers` read branch, and drive its two negative controls. |
| cody b57 `mech_backup_not_silent` (opened 2026-10-28T18:57:29Z) | cc | A new cc-owned open obligation, outside this dispatch. Not reviewed. |
| hank's field-scope declarations | hank | `--validate` once they land. |
| Everything routed in b64 §5 | hank / cody / Michael | Unchanged by this batch. |

**The audit-layer boundary was respected.** Nothing under
`.claude/skills/sairn-hover-auditor/` was edited or created. The only access
was one filename glob, which found nothing. Nothing in `SAIRN-hover` was
touched.
