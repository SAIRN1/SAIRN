# LATEST — fourth / ted — batch b26 — 2026-10-15

**ALL SIX ITEMS DONE, manifest 6/6, and it was opened as the FIRST action of the
batch.** `HEAD == origin/main` at **`0851dbff`** when this was written, 0/0,
clean, **NOT forced** (ancestry-proved; `grep -c force` → 0 on every push log),
and **landed verified ON ORIGIN by reading the file back**, because a clean exit
from `git push` is not proof. No `SAIRN_SEED_GATE` / `GATE_EXEMPT` /
`SAIRN_SKIP` in any form. `settings.json` untouched, hooks untouched. **0 files
written under `api/ sql/ tests/ tools/`** — every drive ran against a COPY.
Auditor clones not entered. **The live tip is ahead of that sha by the commits
carrying this file**, by design. **CONTEXT 54.6% of 1000k** (545,603 tokens).

## The four things worth knowing

1. **A PAID PERIOD CAN BE SILENTLY UNFROZEN BY ANY MANAGEMENT ROLE** — `billing`
   included, and **`billing` is also the role that runs payroll**. One
   `sen_settings` POST → HTTP 200 → the next pay run reports **$100.00 for a
   period already paid at $80.00**, `period_closed: null`, and **no record the
   frozen list ever existed**. It defeats the freeze's own safety argument in its
   own words.
2. **AN ADJUSTMENT CAN BE NEGATIVE.** A downward approved correction yields
   `adjustment_cents = -2000` and reduces a later period's payable total — a
   silent wage deduction, which is recovery of an overpayment and a separate
   regulated act.
3. **TWO OF MY OWN PUBLISHED FIGURES ARE WITHDRAWN**, both from b23 and both too
   generous about reachability: **CALLER was low by 19** (13 → 32), and
   *"0 of the 151 interpolates a caller value"* is wrong — **16 do**.
4. **THE TRUST HARD-LOCK IS UNTESTED** — delete `LAW_TRUST_LOCKED` entirely and
   the suite stays green, proved by a 2×2 ablation in which ARM B also proves
   the lock does work.

## Open items

| owner | item |
|---|---|
| hank | **H3 FIRST, money on a federally mandated record:** a **named** refusal of `payroll_closed_periods` at the generic `sen_settings` path, plus an **append-only** closings resource (the `leg_custodylog` shape) with the read unioning rows and a reopen as a new appended row |
| hank | **H2:** floor `adjustment_cents` at 0; surface `overpayments[]` requiring a human act, never netted; assert `total_payable_cents >= gross_cents`; add `premium_may_be_owed` per adjustment — **a disclosure that names a class is a note, a flag that names a person is payable** |
| hank | **H1:** assert `LAW_TRUST_LOCKED` directly (already exported), add a `law_bankstatements` arm, **then re-run the 2×2 and confirm ARM A goes RED** |
| hank | **Q4** a `partially_closed` third state; **Q(b)2** the EVV basis for a closed period once Michael decides; **Q(c)** both "pure" headers say what they now mean |
| hank | **b24 F3** delete the replaced id **server-side**; **b24 F4** field-merge `legAdoptServerId` on the write's own payload (`Object.assign` is not the fix); then **the 22** from report §2 and the caller GETs **now known to be 32, not 13** |
| hank | **5 still open from b25:** b21 F3, b21 F4, `license_hash`, no-revoke, both `sd_photos`; plus b23 F4 and the status-less-entry guard. **b18 N1 and b23 F1/F2/F3 are CLOSED** |
| cody | **arm Z's `else`, then RE-RUN THE ABLATION** — the arm does not count until it comes back RED; the known-red blob-scope row → **RECOVERED**; the control arm's hardcoded *"ten failures above"* → read off `failed.length` |
| cody | **b24 F1** re-anchor **with an arm that fails when the anchor stops matching**; and a failing-first arm driving a `23514` through one of the 22 and a `42703` through one of the 151 — **observed**, never driven |
| cc | **INSTALL THE CENSUS** from `docs/2026-10-15-fourth-b26-branch-census-routed-to-cc.md` — full source inline, fixtures included. **Three scratchpad censuses in three batches each re-introduced a predecessor's bug.** Then `--amend`, one anchor-rot tool wired into a gate, R3's 48 ranges, and **the convention-numbering check, still unbuilt after b25 and b26 both moved the prose denominator by hand** |
| fourth | **`cody 2026-10-15T15:12:47Z` (`bld_bids`) — FRESH, UNTOUCHED, clock from 15:12:47Z.** Mechanically settleable: the suite's assertion was satisfied by the **comment documenting the removal of the thing it asserted**, and the sabotage arm guarding it was ANCHOR-0 at the same time. Then the census's inter-procedural half, **with fixtures in both directions** |
| Michael | **the EVV basis for a closed period** (§3.4 — your same-clock decision is unimplemented there); the **back-payment** question; and the one-person-agency question **stays held** |

## Said rather than left as an absence

**No live verification. No production row read, no table touched, no deployment
fetched — and no agency has a `payroll_closed_periods` row, so the freeze has
never run on real data by anyone.** The census **is not a gate**; nothing runs it
on a push. **26 `UNRESOLVED` census lines stand**, one already known to be
CALLER, so the caller count is **no longer a hidden lower bound but is still a
named one**.

**THREE ARMS DID NOT REACH THEIR SUBJECT THIS BATCH AND TWO WERE MINE:** my
`LATE_REPLAY` arm 3 was refused `400` before it arrived (exit code 0, the miss
invisible); my first census fixture used a layout the file does not contain; and
hank's arm 3a cannot reach the lock it cites. **In all three the cheapest guard
was a control or an ablation, not a closer reading** — item 16 and item 20.

**Convention 35 gains one operational clause, not a 36th number** — *the span
rule itself has to be a fixture, not a sentence*. 35 headings, 1–35, no gap, no
duplicate, denominator still *"ELEVEN of the thirty-five"*.

**Chain tip when these four were written:** `0851dbff` —
*manifest(fourth b26): item 6 done — the push landed and was verified ON ORIGIN*.
Report SHA256 `e27c725c5fdd1535456fc44c684e9e57a273b0972da9b0239fb81f063820fe4f`.
