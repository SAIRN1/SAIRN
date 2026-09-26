# SAIRN Verification Methodology — Implementation Plan
(Point-in-time snapshot, content as of 2026-09-15. Needs periodic refresh — not live-synced to chat's own planning notes.)

## TRIAGE PASS — Sept 15 (third regroup — the second regroup went stale within hours, proven not assumed: its own Tier 1 items 1-2 were already done when checked against real agent reports)
Real re-derivation against actual reports, not a re-read of the last pass.

- **DONE since the second regroup, filed for the record, not re-dispatched:** Hank's reverifySubscription() suite (14/14) and item 93 widened into the real per-tenant AI sub-budget (built, documented, pushed — pending only the SQL run, see consolidated list below); CC's tier_a_review_gate.py crash-to-false-accusation fix, the pinned-list-drift sweep tool, and the fail-open decode-bug finding (23 call sites, 2 fixed, 21 recorded as their own row); Cody's per-tenant sub-budget documentation-first work, the Tier A gate exclusion-rule shrink, and Carolyn's drawing-tool requirements (all four sub-features built); Ted's isPaid three-state fix, the second Tier A gate exclusion fix, and the sairncode fault-probe correction (found already existing, not duplicated).
- **Tier 0 — already in flight, confirm current state before assuming:** whatever CC/Cody/Ted/Hank are each mid-task on as of your next check-in — this plan cannot see live agent state, only what's been reported.
- **Tier 1 — real, ready, unclaimed as of this regroup:**
  1. Item 78 (formal verification) — real evidence and the FPV gap both flagged in the registry.
  2. sairn-resilience-patterns skill build — the buildable half of tonight's cross-industry research, still unclaimed.
  3. The recombination-pass standing rule (filed in recurring-bug-classes) — real, zero executions yet. Four candidates ready: the date-arithmetic trap, Number('') silently becoming 0, the negative-control-that-cannot-fail class, CRLF-vs-LF false alarms.
  4. Real, standing gap: nobody has ever swept the codebase to confirm "AI proposes, a human approves" is actually code-enforced everywhere it's cited as a safeguard, as opposed to just being the stated design. Real, concrete audit target: every financial-facing or customer-facing AI feature across every vertical, checked for a real, hard gate blocking an AI-proposed action from executing without an explicit human approval step in code.
  5. SOC2-readiness real gaps (NHI credential inventory, incident-response plan, SAIRNlaw privacy scoping) — status genuinely unclear as of this regroup, needs a real check before assuming stalled or progressing.
  6. The "optical recognition lens" research (in immune-system-research) — real, working code-embedding clone detection (VulCoCo-style, direct fix for finding a bug's shape elsewhere in the codebase regardless of wording), a real, direct fix for sairn_claim.py's known lexical-overlap matcher bug via semantic similarity, log-embedding clustering for catching the same failure shape across differently-worded errors, and neural code search for verifying a spec's claim against the real implementation instead of trusting the written description. Four real, distinct, buildable tools, none yet claimed.
  DECIDED (Michael): the automated embedding search does NOT replace the manual recombination-pass discipline (item 3) — one feeds the other. Automated search surfaces candidates, an agent still reads and judges which one is actually correct.
- **Tier 2 — blocked on Michael specifically:** the Railway project shutdown (agents structurally locked out per standing rule until confirmed dead).

## CONSOLIDATED — real SQL migrations pending in Supabase, Michael's action
- sql/sairnbuild_data_schema.sql — retainage-release feature, happy path unverifiable until run.
- sql/sairnbiz_timesheet_schema.sql — real hour-entry feature, writes answer 503 until run.
- sql/sairn_ai_tenant_subbudget_2026-09-15.sql — per-tenant AI budget enforcement, counts per-app (old behavior) until run.
- STANDING RULE: any future SQL migration reported by any agent gets added to this exact list the moment it's reported.

## STANDING MECHANISM — real staleness detection for this plan itself
This is what verification_plan_staleness_check.py exists to answer, first real run against real content starting today.

## TRIAGE PASS — Sept 15 (first regroup)
- **Tier 0 — already in flight, let it finish before adding anything new on top:** item 83's countersign fix (Cody), the fault-probe seam (sairncare → sairnbuild → sairncode), competitive-gap-audit mining against the real docs.
- **Tier 1 — real, fully written up, zero owner, dispatch next:** items 97-101 (SpaceX/NASA tier-assignment basis, ablation testing, Bitcoin Core graduated-consent for irreversible changes, the watchtower/penalty pre-signed-remedy pattern). Item 20 — real, separate problem: stale "BUILDING NOW" status since Sept 13 with zero committed code, while items 66/84 both assume it exists; needs a real status correction at minimum.
- **Tier 2 — batch 2, likely clear, needs a real confirm-closed sweep:** 34, 18, 52, 59, 90, 35, 65, 40, 43, 44.
- **Tier 3 — batch 4, gated but the gates are mostly open now:** 78 and 83 are the most-exercised items on the registry. 61/69/88 confirmed built (CC). 8/25/26 likely unblockable now that batch 3's independent-review practice has real data behind it.
- **Tier 4 — standing practices, not builds, confirm they're actually being followed:** 56, 71, 85, 86, 60.
- **Tier 5 — correctly held back, needs real incident volume before the numbers mean anything:** 51, 62, 66, 68, 80, 84.
- **Tier 6 — genuinely lower priority or infrastructure-blocked:** 13, 17, 25, 36, 46, 48, 5 (intentionally last).

## How to read this plan
Batches, not tiers — a batch is what can genuinely move together given real dependencies. Work within a batch in any order; don't start a later batch's items until the batch before it is substantially clear.

## BATCH 1 — already active, just let it finish
- Item 54 (heartbeat/watchdog) — claimed by Fourth, in progress.
- Item 77 (injection-phase field) — claimed by Hank, in progress.
- The already-dispatched three-way-match/StoneDesk-PO work (CC) and item 35 checkpoint design (Fourth).

## BATCH 2 — ready now, zero blockers, dispatch next
Items 20, 34, 18, 32, 52, 59, 90 (parse-don't-validate Guardian check — maps to four already-fixed real bugs), 35 and 65 (HIGH tier, no blocker), and: 40, 41, 43, 44, 45 (43 confirmed real and resolved — disciplines §7).

## BATCH 3 — the cheap unlock, dispatch as a RULE not a build
When Agent A finishes Tier A work, a DIFFERENT agent reviews it, recorded with detection_method set. Cheapest, highest-leverage single thing in the whole plan — already proven with real data (Hank's independent review of CC's sbThreeWayMatch found a real floating-point equality bug).

## BATCH 4 — gated on Batch 2/3, real dependencies
- 8, 25, 26 (both remaining branches) — gated on 2/24 (Batch 3) plus 4, 18, 21.
  - **26 phase 2 BUILT 2026-09-26 (Fourth): `tools/tiering_recheck.py`, control `tests/run_tiering_recheck_probe.py`.** The gate opened for real: 167 review records over 245 resources and 74 independent-review defects. It PROPOSES recheck candidates and never re-tiers. Recorded here because this snapshot is the document that dispatched a rebuild of an already-built tool once (disciplines §10) — check the tool before dispatching this item again.
- 4, 23, 11 (BUILT already), 10 (BUILT already) — 4 still blocked on the register's standing-rules-citation field; 23 is design-done, build-deferred until 2/24 and 4 produce real input.
- 69 (cell isolation) + 61 (credential inventory/rotation) — dispatch together, same root gap (the shared Supabase key).
- 88 (articulation points) — dispatch alongside 61/69, same dependency-graph data.
- 78 (formal verification) — first real target is SAIRN's own cross-app role-gate logic, second target is the already-known [0053] token-deduction concurrency bug.
- 83 (fail-safe verification tests) — apply to item 19 now (already live) and item 54 once Batch 1 lands it.

## BATCH 5 — standing practices, not code, adopt now regardless of build sequencing
56 (pointing-and-calling), 71 (blameless investigation), 85 (forceful-backup overrides "don't interrupt a running shell" for genuine emergencies), 86 (battleshort-style logging), 60 (audit whether local-re-derivation pattern shows up outside session handoffs).

## BATCH 6 — real, but needs volume before the numbers mean anything
51, 62, 66, 68, 80, 84 — build the STRUCTURE now if cheap, actual numbers stay rough estimates until SAIRN has real incident history.

## BATCH 7 — lower priority or genuinely deferred, not forgotten
13, 28, 29 (29 already BUILT, 13 already built into item 6), 17, 25 (gated in Batch 4, not deferred), 5 (intentionally last). 36, 46, 48 — genuinely blocked on infrastructure that doesn't exist yet.

## BATCH 8 — items 81, 91-96, integrated into the real sequence
- 81 (metastable failure/retry-storm) + 93 (jitter) — treat as one unit, ready now: send-reminder and alf-alerts firing at the identical minute every hour in vercel.json.
- 92 (functional core, imperative shell) — ready now. Real first targets: money-comparison logic (sbThreeWayMatch, ledger.js) and any state-mutation code shaped like the Quote Builder bug.
- 94 (deep modules, information leakage) — ready now. Real payoff target: the date-comparison logic (three separate bugs, likely explained by this).
- 95 (segmented verification) — not a new build, a confirmed design principle, apply as default.
- 91 (SPOF tracking) + 88 (articulation points) — one unit, gated: 91 has no data to track until 88's dependency-graph sweep produces a real list.
- 96 — folded into item 23's existing scope, not a standalone build.

## URGENT — "firm up the ship" priority list, agent-mapped
- Independent review as STANDING practice, not a one-off — keep applying by default to every Tier A dispatch going forward.
- CODY — meta-checker integrity: sairn_claim.py's confirmed blind spot — it trusts its own index-row documentation with no mechanism to verify that documentation's own freshness before trusting it.
- HANK — stale skill refresh: sairn-code-scrubber hasn't been updated despite several new recurring bug patterns found since.
- FOURTH — confirm the structural fix actually holds: Michael's decision was to make it structurally impossible to merge a new tool file without a matching inventory entry — confirm that's actually live and actually blocks.
- CC — already correctly loaded: items 61/69/88, item 22's unmeasured checkers, and the review of Fourth's items 35/54.

## Integration audit — do undispatched/recently-shipped items actually fit together
**CONFIRMED WORKING:** item 35's checkpoint endpoint was checked for whether it actually got wired to item 54's heartbeat table once 54 landed. Confirmed, not assumed — `require('./_lib/heartbeat')` and a real `beat` call are in the file.

**REAL GAP FOUND:** item 20 shows zero committed code anywhere in the repo despite carrying "BUILDING NOW" status since Sept 13. Items 66 and 84 both reference item 20's Goodhart-risk exposure as if it's live and built — it isn't. Don't let a future dispatch of 66 or 84 assume item 20 exists.

**REAL, FORWARD-LOOKING COORDINATION RISKS:**
- Item 7 (defect register) is a SINGLE shared resource multiple still-open items want to extend with their own new field — item 38, item 66, item 84. Migration collision risk if dispatched separately without this context.
- Item 8 (AI red-teaming) dispatched to Cody as a narrow slice; the full spec depends on item 18 (dispatched to Fourth). Needs an explicit interface handoff when item 18 lands.
- Item 90 (parse-don't-validate) and item 38 (completeness checking) are complementary, not competing — 90 makes a bug impossible to write, 38 is the detector for whatever 90 can't reach.
- No shared dependency-graph tool exists yet — if item 84's event tree or item 53's minimal-cut-set analysis get built later, they should REUSE CC's graph, not rebuild their own.
