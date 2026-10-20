# SAIRN handoff: cc, batch b31, 2026-10-20

**Seven items, all seven closed.** Michael's snapshot re-capture is also
committed. Everything is pushed, the tree is clean, there are zero stashes, and
**no override of any kind** was used.

## 1. Pushed state

| | |
|---|---|
| Claim commit | `0860564f` (claims) |
| **Push range start** | **`b2b02bbd`** `chore(snapshot b31): commit Michael's 13:13Z re-capture...` |
| Content commits | `b2b02bbd` snapshot, `3f9e48e0` tier-a obligation, `6969d23d` three discharges, `2288e151` fmea fix + convention, `7dfd2557` `70f9c3c5` `8ba94e01` `671e387b` `6da9b98d` drafts, parts 1–5 |
| Push | **LANDED, no force.** After `git fetch`, `rev-list --left-right --count origin/main...HEAD` gave **0 0** after every part |
| Overrides | **NONE.** The Tier A gate was satisfied by `--open`, not skipped. The two could-not-run checks were satisfied by splitting the commit, not skipped |
| Exclusions | `api/`, `tests/`, `sql/` and every `.html` file **untouched** |

**The range end is not named;** take the tip from origin.

## 2. CLOSED

- **Snapshot re-capture (b30 item 4, closed now).**
  - Michael's 13:13Z capture was sitting uncommitted in this clone, wrapped as
    `{"tables": {...}}`.
  - Unwrapped mechanically and committed.
  - The freshness tool now reports **498 tables, 0 absent-and-queried**.
- **Item 1.** "hank 10-16" is hank's b17 obligation
  **2026-10-16T13:03:47Z**. Discharged.
  - **MEDIUM, latent:** a ledger close named `legacy:<start>..<end>`
    replaces a legacy freeze. Driven: September was unfrozen.
  - Overlapping closings are still accepted.
- **Item 4.** cody 2026-10-20T11:47:22Z, discharged. **The 700 bytes per
  stop assumption is broken.**
  - A 210-character `job_ref`, or a 500-character multibyte address, gets a
    413 on a valid route.
  - `api/sd-sub-data.js` still caps only `write`.
  - `consolidate` is mislabelled write-class.
- **Item 5.** cody 2026-10-20T13:03:28Z (`sc_claims`/`sc_dme`), discharged.
  The suite passes 48/48.
- **Item 2.** **b30's "multi-path --save writes nothing" was wrong.**
  - The real cause was a closed pipe killing the process before the save
    phase. It now saves first: 0 of 8 before the fix, 8 of 8 after.
  - A second defect also fixed: one bad target lost the whole batch; each
    target is now saved independently.
  - **720 drafts saved.** Owed fell from 745 to **18**: 16 hover-auditor
    files and 2 the tool refuses.
- **Item 3.** The **convention** was wrong, not the practice.
  - 103 of 157 handoffs use `SAIRN-handoff-<session>-b<N>.md`; 8 use the
    documented scheme.
  - `CLAUDE.md` and the skill now describe the practice: compare `N` as a
    number, with one writer per session prefix.
  - The skill is mirrored to the user store.
- **Item 6.** The concept was stated before each new piece of logic (notes
  §1, §2, §4).
- **Item 7.** Pushed and confirmed.

## 3. OPEN, and why

**(a) Findings routed, not fixed** (`api/` was excluded):

- **hank:** the `legacy:` closing-id collision; overlapping closings.
- **cody:**
  - bound `job_ref`, and either bound the address in BYTES or derive the cap
    from characters × 6;
  - `api/sd-sub-data.js:171` caps only `write`, and `qc-review` is uncapped;
  - `consolidate` is mislabelled write-class;
  - the `rf_invoices` jsonb-text note.

**(b) Reopen role set:** I recommend **owner-only** reopen of a closed pay
period. This is **Michael's decision.**

**(c) The snapshot obligation** (`3f9e48e0`) is assigned to cody to review.

**(d) Still waiting from earlier batches:**

- b29's eight routed defects, starting with the false success in
  `api/accounting.js:296`;
- hank's `inert_until` and arm A4;
- cody's P2 label.

**(e) My push loop retried a deterministic Tier A refusal four times before
stopping.** The gate escalated at the third. Lesson: a loop may retry only
fetch-first or lock-ref races, never a gate refusal.

**(f) Remaining cc-owned Tier A obligation:** fourth 2026-10-20T13:42:06Z
(`rt_routes` optimiser, `stonedesk.html`). Not started.

## 4. Exact next step

| item | next step |
|---|---|
| (a) | hank and cody, per the verdicts in `docs/tier-a-reviews.json` |
| (b) | Michael: owner-only, or owner + billing, for reopening a closed pay period |
| (c) | cody: review `3f9e48e0`; three checks are named in the record |
| (f) | Next cc batch: fourth's `rt_routes` optimiser obligation, attack points (1)–(3) |

## 5. Transcript

```
C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cc\d7c0c45c-9fc3-4704-80ea-61d13ebeabb2.jsonl
```

The durable record is `docs/2026-10-20-cc-b31-notes.md`, the tier-a ledger,
`tools/fmea_draft.py` and `docs/fmea/`.
