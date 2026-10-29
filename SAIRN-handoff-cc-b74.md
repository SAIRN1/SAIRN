# SAIRN handoff: cc, batch b74, 2026-10-29

| | |
|---|---|
| Start | Fast-forwarded to `df92c570`. The tree was clean. |
| Claims | None. Everything this batch wrote is under `docs/`, plus `docs/tier-a-reviews.json` and this handoff. |
| Context | The window is declared at 200,000. The digest's CONTEXT line is the measured figure. |
| Transcript | `C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cc\a046cdf7-9eaf-4291-b1ac-b9b8bb34da67.jsonl` |

## 1. Done

**Item 1: `docs/licensing-product-plan.md`**
- 413 lines, written by a subagent and spot-checked by me.
- It puts the agent control platform as the parent product, with the
  verification certificate and the skills marketplace package as modules.
- It also covers the competitor and pricing table, the pricing proposal, the
  one-page pitch, sequencing against dev services, and the open decisions.
- **What the repo search found:**
  - "verification certificate" and "agent control platform" match nothing in
    the repo. The doc says both are new framing written today.
  - No SAIRN dev-services plan exists in the repo.
  - The prior skills-marketplace decision was
    `docs/DECISION-2026-08-26-skills-marketplace-gate.md`: no-bid on the paid
    path, go on the free path.
- **Pricing that was published but not used:**
  - Vendors with no published price are marked "not published".
  - Airia figures from third-party sites were left out because the sites
    disagree.
  - Anthropic taking a 15% cut of a skills marketplace is unconfirmed.
- The doc states that the certificate must never be called an accredited
  certification.

**Item 2: hooks.**
- `builder_hook_presence.py` reports 4/4 OK, which means the hooks are armed:
  there is a settings entry and `disableAllHooks` is off.
- The install regression passed 37/0. Its R3 check runs `decide()` on 6
  payloads per clone and gets 3 refused, 3 allowed. That is the firing logic.
- A live refusal was witnessed only in cc. Literal output is in the report.

**Item 3: took over the 580h `quotes` record** (fourth,
2026-10-05T15:02:28Z, on `tools/deploy_verify_notify.py` `classify_command()`).
- It was held by cody for 580.3h. I took it over and discharged it locally,
  but **lost the race**. cody, the assigned owner, discharged the same record
  on origin at 2026-10-29T18:56:37Z: SOUND-WITH-GAPS (medium), cody b65.
- The rebase resolver refused to merge the two (correctly). I kept origin's
  ledger, so **cody's verdict is the one on record**. My verdict below is an
  independent second review and is not in `docs/tier-a-reviews.json`.
- **cody's verdict does not mention the echo-chain miss.** The finding below
  is new.
- **Verdict: FAIL, MEDIUM.**
  - The `_MENTION_ONLY` line-prefix filter classifies `echo x && git push
    origin main` as `not-a-push`, and does the same after `;` and after
    `grep ... ||`. A real push after one of those is silently skipped.
  - PUSHING_TOOLS has no missing fifth tool.
  - The `k=v` regex is sound.
- The verdict is in `docs/2026-10-29-cc-b74-review-fourth-deploy-verify-classify.md`.
  The probe is `docs/2026-10-29-cc-b74-classify-command-probe.py.txt`, which exits
  1 until fixed.

**Item 4:** hover b92 `test_965` was dropped from cc's queue and not touched.
It is being reassigned off the builder path.

## 2. Open, with the exact next step

| # | Item | Owner | Next step |
|---|---|---|---|
| F-1 | `classify_command` misses a push chained after echo, cat, grep or `#` | fourth | Classify per shell segment: split on `&&`, `\|\|`, `;` and `\|` outside quotes. Add the 3 BAD rows to `tests/run_deploy_verify_entry_probe.py`. When it is fixed, `python docs/2026-10-29-cc-b74-classify-command-probe.py.txt` exits 0. |
| R-11 | Dental addCredential hold outside the try (b73) | cody | See `SAIRN-handoff-cc-b73.md` §2. |
| R-12 | mechCredAdd and mechAssetAdd have no `.catch` (b73) | cody | See b73 §2. |
| N-1 | New Tier A obligation assigned to cc: the b65 gap fixes (`60dd8a59`) | cc | `python tools/tier_a_review_gate.py --list`, then review and `--discharge cody <opened_at>`. |
| L-1 | Licensing plan, §7 open decisions | Michael | Read §7 of `docs/licensing-product-plan.md`. |
| C-3..C-5 | ctxmeter path, audit credentials, caregiver credentials | Michael | Unchanged; see b73 §2. |
