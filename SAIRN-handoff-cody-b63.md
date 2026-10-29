# SAIRN handoff — cody b63 (2026-10-29)

All six items are done. Nothing is half-finished in the tree.

## Committed / pushed state
- **LANDED, tip `e5819b09c`, full gate.** `merge-base --is-ancestor` is true.
- **A rebase conflict on `docs/recurring-bug-classes-2.md`, resolved.** cc b70 had added its own **C4**. I kept cc's section byte for byte and renumbered mine to **C5**.
- **The manifest gained `sairnmechanical.html`** in cody's override, for the item-2 code fix you directed.
- **Claim:** sairnmechanical, cody b63. It is released at close.

## 1. sd-data.js:2301, the app-agnostic `verifySessionToken`: INTENDED design, verified
- **The evidence, measured rather than taken from the comment:**
  - `api/sd-data.js` makes 145 `verifySessionToken(` calls. 144 pass `expectedApp`. The active-credential pre-gate is the only two-argument call.
  - **It grants nothing.** A token that verifies is only asked whether its credential is still active. An explicit `active:false` is refused.
  - **A token from another app is still refused** with FORBIDDEN by its branch gate, which does pass `expectedApp`. `api/sd-data-law-phase2-session.test.js` holds that arm.
  - **Asserting the app at the entry point** would need every one of the 132 branches' expected app copied up there: a second copy of a fact that is spread over the whole file.
- **What changed:** the Semgrep rule's only hit was this known-intended line, so `run_semgrep` exited 1 on every run. A standing red that nobody reads is how a real one gets missed.
  - `// nosemgrep: verify-session-token-missing-expected-app` is on that one call line, with the reason beside it.
  - run_semgrep now reports 0 findings and exits 0. The rule still fires on any other two-argument call; rule tests pass 2/2.

## 2. The 4 mechBackup Tier A gaps: CLOSED
These come from cc b67's review of cody b57 (`docs/tier-a-reviews.json`, cc b67 verdict; `SAIRN-handoff-cc-b67.md:139-147`). Each gap was found by ablation, and each new arm is red under the ablation cc named.
- **(a)** Arms L record what localStorage holds at the moment the push is called, in both saveDoc and saveTakeoff. Moving the write into `.then` turns them red.
- **(b)** P1 and P4: a 200 `{ok:true}` with no data is truthy, and saveDoc then says "Saved and synced". Reverting to `return r.body.data` turns them red.
- **(c)** The unprovisioned fixture now uses the server's real shape, `{ok:true,data:[],provisioned:false}`. The old fixture never reached the branch the server drives: an ablation that warns there stayed green on the old test and is red on the new one.
- **(d), a CODE FIX.** saveDoc waited up to 15 s on the push with the button live, so a double click saved a duplicate.
  - A `mechDocSaving` re-entry guard is set after the local write and released on resolve and on reject. The push runs inside `Promise.resolve().then`, so a throw lands in reject.
  - D1–D3 are red on the pre-fix saveDoc.
  - saveTakeoff toasts synchronously, so it is unchanged.
- **The fifth routed item: the redaction wiring probe was exiting 2 since b58.** It was anchored on the `rows[0].data : mPayload` fallback, which `10e914b1` removed.
  - It is now `stores_and_returns_redacted()`, scoped to the MECH_RECORDS write branch, plus mutation arm 9b.
  - That is stricter than before.
- **Suites:**
  - mech_backup_not_silent 23/0 (was 13);
  - register_identity 20/0;
  - redaction probe 0 failures (was exit 2);
  - fault probe 0;
  - mech write-unconfirmed 22/0;
  - mech redaction-scope 20/20;
  - ai-provenance-client-sites 18/0.
  - `node --check` is clean on all 7 script blocks.
- **Known uncovered:** an engine with no `AbortSignal.timeout` gives mechData no 15 s timeout. A fetch that never settles then holds the guard until the browser's own network timeout.

## 3. The 28 names for H1 #909: PRODUCED
- **File:** `docs/2026-10-29-cody-b63-909-dead-rule-names.md`.
- **Method:** a re-run of `dead_rule_sweep.py --registry-only` in a worktree of `a86e29481`, the commit H1 cites. It found 75 tools and 169 rules.
- **Result:** FINDINGS 35 = 2 + 33. H1's split is reproduced.
- **The 28** are given by tool and name. The per-tool counts match cody's 2026-10-05 table exactly.
- **The other 5 of the 33, stated in the file:**
  - 3 are H1's writer-tier rules.
  - 2 are `verification_owed_report` OWED/DONE. They appear in today's run only and are reported, not counted.
  - hover_separation's 8 rules were COULD NOT RUN: writer, not reproducible today.
- The worktree was removed after its node_modules link was unlinked; the real node_modules has 154 entries.

## 4. Formal routed entries for H1 and H2: FILED
These are index rows in `docs/SAIRN-OPEN-WORK-INDEX.md`, in the Platform table. Each has an owner, a DECIDING TEST and a NEXT ACTION. The shards were regenerated and `--check` is CLEAN.
- `B63-H2-SEQ813-CODY-2026-10-29`, owner **hover2**: seq813's "retired" is wrong (b19 widened the gate; seq871, b33, is the removal), and seq1111/1147/1156 contradict 871.
- `B63-H1-DRILL-CODY-2026-10-29`, owner **hover1**, plus Michael for the scope question: "DRILL PASSED" in seq1704/1715/1721 overstates the result.
- `B63-H1-909-CODY-2026-10-29`, owner **hover1**: the 28 names, from item 3.
- Nothing in the auditor layer was written.

## 5. Cause tags: `docs/recurring-bug-classes-2.md` C5
- Every b63 fix is tagged phase → sub-phase → cause.
- **Two are classes:**
  - re-entrant push-then-toast saves. Other apps were not swept; this is open in the register record.
  - fixtures that cannot reach the branch they claim to test, which is C2's sibling.

## Open, and the exact next step
| # | open | next step |
|---|---|---|
| O1 | **cc b70 discharged cody b58 and b61 Tier A as SOUND-WITH-GAPS (low)** and routed gaps to cody (`docs/tier-a-reviews.json`, cc b70 verdicts) | cody next batch: read the gap lists and close them |
| O2 | The push-then-toast re-entry window in other save paths | cody: sweep saveQuote/saveCheck and the other apps |
| O3 | hover1/hover2 rows above | the auditors |
| O4 | Michael: does the b33 email-leg removal cover H1's mirror? | Michael |
