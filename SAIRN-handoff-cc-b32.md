# SAIRN handoff: cc, batch b32, 2026-10-20

**Five items, all five closed.** Everything is pushed, the tree is clean, there
are zero stashes, and no override of any kind was used.

## 1. Pushed state

| | |
|---|---|
| Claim commit | `9846be14` |
| **Push range start** | **`c57e65a8`** `fix(cc b32): the push-retry loop stops on a gate refusal and retries only remote races` |
| Then | `35ed0fac` register record for that fix |
| Push | **LANDED, no force.** After `git fetch`, `rev-list --left-right --count origin/main...HEAD` returned **0 0**. `c57e65a8` is an ancestor of origin/main, and `def classify_refusal` reads back from origin |
| Gate refusals this batch | **One**, from the register-feed gate: the `fix(` commit needed a register record. The loop stopped on it rather than retrying, it was **answered at its cause** (record `c57e65a899cf` added), and the next single push landed |
| Overrides | **NONE** |
| Exclusions | `api/`, `tests/`, `sql/`, every `.html` file and the hover-auditor's scope **untouched**. The 16 hover drafts are written in `docs/fmea/` |

The range end is not named; take the tip from origin.

## 2. CLOSED

- **Item 1, the concept.** Classify a refused push by who said it.
  - Git's race and transport rejections are retried.
  - Gate text is deterministic for that tip, so the loop stops.
  - A gate refusal naming a generated document is retried once, and only after
    a successful regenerate-and-fold.
  - Unknown text stops.
- **Item 2, the fix.** `tools/push_retry.py` had the same retry-everything
  shape as my b31 inline loop.
  - Added `classify_refusal()`, and `cmd_loop` now acts on its class; the stop
    exits 5.
  - **Driven with a stubbed git: a Tier A refusal went from 4 pushes to 1.** A
    fetch-first race still gets 4.
  - 11 new selftest arms, all passing. Two of them drive the loop itself.
  - Register record `c57e65a899cf`: tooling, moderate, injected in `ad11ef1c`.
- **Item 3.** fourth's 2026-10-20T13:42:06Z `rt_routes` optimiser obligation
  is **discharged**.
  - The drift in `sdDataEnvelope` has no consumer.
  - The permutation check is exact, because `orderStops` always returns a full
    permutation.
  - No other caller is affected.
  - **LOW:** a failed optimise toasts "NOT backed up… saved on this device
    only", even when silent. Routed to fourth.
- **Item 4, FMEA.** The owed count was **20 at the start**, because the
  register grew after b31.
  - **16 saved** (hover-auditor tools).
  - **4 refused by fmea_draft's own records-not-code rule:** `CLAUDE.md`, the
    code-scrubber `SKILL.md`, and two hover routing notes. They are permanently
    out of scope and documented.
  - **Owed is 0** once the definition excludes what the tool refuses.
- **Item 5.** Pushed and confirmed.

## 3. OPEN, and why

**(a) Routed findings still waiting:**

- **fourth:** the optimise toast.
- **hank:** the `legacy:` closing-id collision; overlapping closings;
  `inert_until` and arm A4.
- **cody:**
  - bound `job_ref`, and measure the route cap in bytes;
  - `api/sd-sub-data.js` caps `write` only;
  - `consolidate` is mislabelled;
  - P2's label;
  - review of `3f9e48e0`;
  - `ce15ddaa6a3c` still fails `defect_register --check` for every session.
- **b29's eight defects**, starting with the false success in
  `api/accounting.js:296`.

**(b) Michael:** may only the owner reopen a closed pay period, or the owner
plus billing (today's set)?

**(c) Two Tier A obligations owned by cc are STILL OPEN.** My first draft
of this line said "none" without checking. Measured from the ledger:

- **cody 2026-10-20T05:51:44Z:** b27, `rt_routes` made reachable, plus
  three role changes; 10 resources. It has been open since b29, and my
  b30 and b31 NEXT lines dropped it.
- **cody 2026-10-20T14:09:30Z:** `rf_jobs`, the
  `api/b32-rf-jobs-projection.test.js` change. It is new this batch.

Neither was in this batch's dispatch.

**(d) A FMEA MISS against my own fix.** The register loop reports that
`tools/push_retry.py`'s draft predates this defect and cites nothing like it.
That is the prediction check working, not a gap to paper over.

## 4. Exact next step

| item | next step |
|---|---|
| (a) | The named owners, per the verdicts in `docs/tier-a-reviews.json` |
| (b) | Michael: decide the reopen role set |
| (c) | Next cc batch: discharge cody 05:51:44Z (oldest; its attack points are arms D4, D2, S0, H1) and cody 14:09:30Z (`rf_jobs`) |

## 5. Transcript

```
C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cc\d7c0c45c-9fc3-4704-80ea-61d13ebeabb2.jsonl
```

The durable record is `docs/2026-10-20-cc-b32-notes.md`,
`tools/push_retry.py` (its selftest), the tier-a ledger and the register.
