# SAIRN — latest from `fourth` (ted) — batch b22, 2026-10-15

**CHAIN TIP** `142ef3ca` *(the hover2-b36 followup; the six dispatched items closed at `86a27458`. Re-derive with `git rev-parse HEAD`)*
**STATE** `HEAD == origin/main`, 0/0, clean, **not forced on any push this batch — proved by ancestry** (`git merge-base --is-ancestor <pre-push tip> HEAD` → ANCESTOR each time), not by grepping git's wording.
**MANIFEST** 5 done, **1 BLOCKED with its reason** — closed, and **deliberately not reopened** for the followup. No `SAIRN_SEED_GATE`, no `SAIRN_GATE_EXEMPT`, no `SAIRN_SKIP`; `settings.json` untouched; neither auditor clone entered.
**CONTEXT** 35% of 1000k, measured by `tools/sairn_status_line.py` on this session's transcript.

**THIS FILE IS A RE-WRITE.** The six items closed and all four deliverables were uploaded and verified Drive-side; then hover2 b36's routing arrived, was re-derived from source, and changed what these files say. Nothing below is retracted.

## DIGEST

**Item 2 is ZERO-DONE and that is the headline.** `sairn_claim.py check` returned **BLOCKED** on `leg_aftercare` and `t17`, and it is **two live claims, not one** — hank's b13 is fixing the delimiter collision and cody's b14 is arming it, concurrently. Per PR §4.3 the task string was **not reworded** to slip past the matcher; the item was dropped from my claim. The other half, the census SQL, is hank's own b12 F1 and **hank already fixed it** in `4f69facd`.

**cody's two obligations are ONE change recorded twice** — the `what` text is **byte-identical, 987 chars, `sha256 599ff05bfc1a3756`** on both; only `opened_at` (1m46s apart) and `opened_at_sha` differ. One review body was recorded on both. **And neither recorded sha points at the change:** `bc24af59f3db` does not resolve, `f8baf814bfd9` resolves and is a **36-file encoding sweep** whose entire hunk on the named path adds `encoding='utf-8'` — **and it reads FRESH.** The real change is `44fad1f9`.

**M1 driven independently: 405 passed, 14 failed — exactly the claimed 14**, in a `tempfile` copy, live tree never written. The derivation self-heals. **But the REPLACEMENT COVERAGE arm did not generalise with it** — hardcoded to `{ map: 'GRD ` and one gate-suite path, against 20 units of which **0** are `app: null`.

**The 400→503 count is wrong in both directions it has been counted.** Measured from source: **331** raw guard lines → **88** rewritten, **69** still folding a 400 into 503 with no body read, **151** read branches folding a 400 into `ok: true, data: []`, 23 other. **The population is 157**, not hank's 98 and not my b21 63 — **and the cause is one identifier: 99 of the 157 use a response variable literally named `r`.**

**The `sd_photos` size fix holds, and T17 is genuinely on the row** — the clean counter-example to my own b21 F4. Suite 26/0/0. The 64 KB cap is **per row**, so the 44,000-char budget does not compound; it would have blown at photo two had the collection been blob-wrapped.

**The sf_events anchor: the instruction said the seventh, measured it is the SIXTH.** Anchor 7 resolves exactly once and needed nothing. Re-anchored, pipe count asserted 7 → 7, `criticality_tier_check.py` **PROBLEMS:0**.

**b21's citation figures do not reproduce.** 571 / 198 / 373 / 0 provably stale / 39 likely, against b21's 551 / 196 / 355 / 0 / 37 — **on a byte-identical file** (`git diff --stat 7a5e6a11 HEAD` empty). The delta is **entirely predicate**. *(The 373 is an **upper bound**: the sf_events cell's only `:NNNN`-shaped token is `4301:1`, an OAC regulation number, so regulation numbers are being counted as bare code citations.)*

## THE FOLLOWUP — hover2 b36, RE-DERIVED

**hover2 routed `docs/CRITICALITY-TIERS.md:358` as "still unfixed, re-grepped" — and said itself why that might be wrong**: *"fourth's b22 appears to have landed new commits as this batch wrapped up … not confirmed whether the actual fix landed with it."* **It had.** Re-derived from source, both rows against the same live app: **the row at `7a5e6a11` is 7 anchors with 1 ROTTED (anchor 6 of 7); the row at HEAD is 8 anchors with 0 findings.**

**And it settles the ordinal independently.** hover2 said *"the 7th"*, the b22 instruction said *"the seventh"*, the program says **6 of 7** — twice, by two enumerations written on different days.

**The cell's code facts were re-read, not assumed** — `liquorServiceCheck()` on both ends with the (B)(3) reasoning in the source comment; the gaming interlock is `sfSessionRefusals()` itself; `sfScheduleEvent()` returns before any write and mints a real `K_SESSIONS` row; and the stored `alcohol` has exactly the two readers the cell names, the others at `:5335-5376` being **`sf_rentals`**.

**NEW `tools/sf_events_anchor_check.py`, and its failing-first arm is the real pre-b22 anchor text.** The cell stated its acceptance rule in its own prose with nothing driving it, so **the rule went quiet for a day** when a legitimate bug-fix moved the text. 10/10 locked arms, both failure directions (ROTTED and AMBIGUOUS), the prose-span false positive armed explicitly, no-anchors-at-all a finding, **fails closed**, and it prints what it cannot tell you. Live: **exit 0, 8 of 8**. **The cell now names the check inside its own rule sentence.**

**The pre-commit gate refused the first attempt and was right** — a `tools/` file with no inventory entry. Entry written, `docs/TOOLING-INVENTORY.md` regenerated rather than hand-edited, `--check` **OK**.

## DECISIONS WAITING

1. **ITEM 2** — strike it from fourth's queue, or have **hank and cody both** release it and re-issue. Do not hand it to a third agent while two claims are live.
2. **The 151 read branches** fold a 400 into `ok: true, data: [], provisioned: false` — a silent failure strictly worse than the wrong 503 the reviewed commit fixed. **It is in nobody's open work.**

## OPEN, BY OWNER

* **hank** — helper **F1** (branch on `23514`, not class `23`) and **F2** (drop the bare `/does not exist/i`) **first**, because 88 branches now depend on that code; then the 69; then the 151. Plus the two `sd_photos` caller findings — the failed-downscale branch stores **and syncs** the original while the toast says it will not be backed up, and the 21,536-byte margin is counted in UTF-16 characters while `octet_length` counts bytes.
* **cody** — a REPLACEMENT COVERAGE generalisation arm (flip a **non-GRD** unit to `app: null` and back), and a per-resource refusal arm that **fails** a gate suite naming six resources and driving one.
* **cc** — print the touched-file count beside the `file-set` basis; the anchor-rot check's first three false positives (prose spans with empty parentheses); the b21 re-seat author-time guard, still open.
* **Michael** — the two decisions above.

## METHOD NOTE

**Three times in this batch a measurement was taken with a predicate narrower than the population, and every time the output read like a population.** b21's clause — *print the command and the raw count* — is necessary and not sufficient: all three would have printed a command. **When a predicate names an identifier, say which identifier**; and when a figure is carried into a second document, carry the predicate with it or re-derive it. **And: a list long enough to need an ordinal is long enough to need a program** — the instruction's own ordinal was wrong, hover2 got the same ordinal wrong independently, and hand-counting would have hidden it both times.

**One more, from the followup, and it is about rules rather than counts: a document that states its own acceptance criterion in its own prose, with nothing driving it, is a rule nobody is told about the day it breaks.** The sf_events cell said *"every quoted anchor must resolve EXACTLY ONCE"* and went quiet for a day. **Either give the sentence a program or stop writing it as a criterion.**

*Full detail: `SAIRN-report-fourth-b22.txt`, `SAIRN-handoff-fourth-b22.md`. Every figure names the command that produced it — re-derive anything you mean to quote, including out of this file.*
