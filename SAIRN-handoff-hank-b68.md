# SAIRN handoff — hank b68 — 2026-10-29

**Subject:**
- The four H1 findings routed to hank: #1734, #1740, #1744 and #1747.
- The most overdue Tier A obligation assigned to hank.
- The b67 backlog, picked up where it stopped.

This handoff was written before the report.

**Re-orientation.** HEAD was `1fcd7e9f2`, which was 12 behind origin/main. It was fast-forwarded to `fcc8bcaf0` before any work started. The b67 handoff was read from the repo copy.

## 1. H1 items — each checked against HEAD, fixed, and cause-tagged

All fixes are in commit `d4867af07`. The cause tags are in `docs/recurring-bug-classes.md`, under "batch 68 (hank)".

| H1 | what | live state at HEAD | action |
|---|---|---|---|
| #1734 | `o.quantity` was written into innerHTML unescaped | present, at `sairnlegacy.html:4836`; it was `:4823` | `H(String(o.quantity==null?'':o.quantity))` |
| #1740 | the register cells for `leg_memorials` and `leg_liveryvendors` said "no PII" and "not individually read" | present | both rows rebuilt whole from their write sites (`saveMemorial` `:4342`, `saveLiveryVendor` `:5173`). Both stay **B**. The "no PII" clause is corrected. The `service_details_visible` no-consumer limit is stated. Pipe count checked. |
| #1744 | a wildlife case with a closing status and a blank date dropped out of the KPIs | present, at `saveWildlifeEdit` `sairnvet.html:6595` | the save is now refused, with a toast. The register cell notes this, the line drift, and that Transferred is outside Release Rate. |
| #1747 | three weaknesses in the `sql_placeholder_check` lexer and declarations | present | E-string escapes are handled. A quoted identifier is now lexed as code. Declarations must be an exact token on a whole comment line. Criteria are now `2026-10-29.1`. Fixtures pass 26/26. **Ablation: 5 of the 6 new arms are red on the old code.** The sixth is a direction guard. `--ref HEAD --all` over 312 files is clean. |

- **Not fixed (#1734 scope):** the raw `o.id` in an inline onclick is an app-wide pattern, 38 sites by H1's count. It is not new, and it needs a separate pass.
- **Not changed (#1744):** the label and semantics of the Release Rate KPI. The register states the Transferred gap, and changing the KPI is a product decision.
- **Not done:** I did not write a defect-density-register record for the four fixes.

## 2. Tier A reviews — every obligation ASSIGNED TO hank, discharged, most overdue first
| opened | author | resource | verdict |
|---|---|---|---|
| 2026-10-22T16:02:10Z | cody b51 | leg_cremations (countersign off-profile -> 500) | **SOUND**. There are 4 production callers, and each one's table is a subset of its PROFILE (measured with node). b51 test 5/5. |
| 2026-10-22T21:18:41Z | fourth b57 | slabs (a11y names) | **SOUND**. The recorded sha `a7a8bb27a` does not resolve; the landed commit is `09e810819`. Only aria-labels moved, and the applier never overrides an existing name. a11y 49/49. |
| 2026-10-23T16:49:24Z | cc b55 | law_trust_reconcile (IOLTA stress) | **SOUND-WITH-GAPS**. **M5 is a real reconciler defect**: an uncleared deposit 91 days old balances the bank leg, because outstanding items have no age limit. **M6 is a real IOLTA failure but a LIMIT of reconciliation**, so it should not be counted as a reconciler FAIL. |
| 2026-10-27T14:26:58Z | cc b56 | sd_approvals (StoneDesk presence) | **SOUND**. All 8 named FAILs are real at HEAD. T1 (signature not checked; deposit_status passed through verbatim), T2 (`:36672` one-untracked → COMPLIANT, w9 ignored) and T4a (`:10828-9` literal tiles) were confirmed at the source. |
| 2026-10-27T14:59:52Z | cc b58 | leg_cremations, leg_invoices (legacy presence) | **SOUND**. L1: no api code reads `authorization_on_file`/`waiting_period_observed`. L3: `legComposeStatement` has no zero-price or negative-price refusal. |
| 2026-10-29T11:22:16Z | cc b69 | dnt_rollup / exec_context / sd_crm (field-scope rules) | **SOUND**. Each declaration matches its commit's stated design. The office-id literal is right. Field scope 38/38. |

- "Your own eligible" was read as *assigned to hank*. No obligation assigned to hank is still open.
- The oldest obligation that anybody may take over is fourth's 2026-10-05 `quotes`, at 580h, held by cody.

## 2b. Backlog
- **S4 fixed (`a4069b882`):** `api/agent/poll.js` now delivers by compare-and-set.
  - The PATCH carries `&status=eq.pending` and `return=representation`.
  - Only the poll whose PATCH returned the row delivers it.
  - A failed PATCH delivers nothing: the response is 502 and the row stays pending.
  - `api/b68-agent-poll-cas.test.js` passes 4/4. **Arm X is red on the pre-fix file**: the same race delivered the command twice.
- **S6 fixed (`aeb3f2b80`):** the push_retry fold returns `nothing to fold` when nothing is staged. The new selftest arm was red before the fix, and ALL ARMS PASS after it.
- **J5 NOT seeded (`aca5b364f`):** the 2018 V.R.C.P. text and the 1 V.S.A. § 371 holiday list are tabled in `docs/sairnlaw-vermont-deadline-seed-blockers.md` §b68. Three named gaps would each force a guess:
  - amendments after 2018 cannot be ruled out, because the official page is a rolling window from 2020;
  - whether electronic service still gets +3 days under 6(e);
  - the observed days under § 371(b).
- **Cause tags:** all 6 fixes have one, in `docs/recurring-bug-classes.md` under "batch 68".

## 3. CLAIMS HELD

`sairnlegacy`, `sairnvet` and `platform`. All three are released after the push lands.

## 4. OPEN — exact next steps

| # | item | owner | next step |
|---|---|---|---|
| J5 | Vermont | Michael / hank | Michael: a current compiled V.R.C.P. with an "as amended through" date, or confirmation that the promulgated page covers 2018 onward, and whether e-service gets +3. hank: then the ND pattern; rows triggered by entry can go first |
| M5 | IOLTA reconciler: an aged deposit in transit balances the bank leg | sairnlaw owner (cc's probe found it) | in `api/_lib/law-trust-reconcile.js`, surface uncleared deposits older than a stated threshold as their own status; the probe's M5 then turns PASS |
| SDP | StoneDesk presence FAILs (T1a/b/d, T2a/b, T3a/b, T4a + E/I/M/X) | StoneDesk owner | route into the open-work index; T4a is a fabricated KPI on an OSHA panel |
| LGP | SAIRNlegacy presence FAILs L1a/b, L2a, L3a/b | sairnlegacy owner | route; L1 has the countersign lock read the record's authorisation fields |
| H1x | raw `o.id` in inline onclick, 38 sites in sairnlegacy | hank | a separate pass; quote it with `H()` / `JSON.stringify`, or use closures |
| J6, J4, J2, A1, P1, R1, G1, S5, S7, T1 | carried | as in b67 §8 | unchanged |

- **Left uncommitted on purpose (U1):** the same 7 untracked root files listed in b67 §8.
- **Context:** the window was first declared as 200,000, a guess, then re-declared as 1,000,000. The evidence for 1M is that b67 in this clone measured 758,507 tokens, which a 200K window cannot hold. 222,443 tokens at this point.
