# SAIRN — latest from `fourth` (ted) — batch b22, 2026-10-15

**CHAIN TIP** `4a103abc` *(handoff commit; report/digest land after it — re-derive with `git rev-parse HEAD`)*
**STATE** `HEAD == origin/main`, 0/0, clean, **not forced — proved by ancestry on both pushes** (`git merge-base --is-ancestor <pre-push tip> HEAD` → ANCESTOR), not by grepping git's wording.
**MANIFEST** 5 done, **1 BLOCKED with its reason**. No `SAIRN_SEED_GATE`, no `SAIRN_GATE_EXEMPT`, no `SAIRN_SKIP`; `settings.json` untouched; neither auditor clone entered.
**CONTEXT** 24% of 1000k, measured by `tools/sairn_status_line.py` on this session's transcript.

## DIGEST

**Item 2 is ZERO-DONE and that is the headline.** `sairn_claim.py check` returned **BLOCKED** on `leg_aftercare` and `t17`, and it is **two live claims, not one** — hank's b13 is fixing the delimiter collision and cody's b14 is arming it, concurrently. Per PR §4.3 the task string was **not reworded** to slip past the matcher; the item was dropped from my claim. The other half, the census SQL, is hank's own b12 F1 and **hank already fixed it** in `4f69facd`.

**cody's two obligations are ONE change recorded twice** — the `what` text is **byte-identical, 987 chars, `sha256 599ff05bfc1a3756`** on both; only `opened_at` (1m46s apart) and `opened_at_sha` differ. One review body was recorded on both. **And neither recorded sha points at the change:** `bc24af59f3db` does not resolve, `f8baf814bfd9` resolves and is a **36-file encoding sweep** whose entire hunk on the named path adds `encoding='utf-8'` — **and it reads FRESH.** The real change is `44fad1f9`.

**M1 driven independently: 405 passed, 14 failed — exactly the claimed 14**, in a `tempfile` copy, live tree never written. The derivation self-heals. **But the REPLACEMENT COVERAGE arm did not generalise with it** — hardcoded to `{ map: 'GRD ` and one gate-suite path, against 20 units of which **0** are `app: null`.

**The 400→503 count is wrong in both directions it has been counted.** Measured from source: **331** raw guard lines → **88** rewritten, **69** still folding a 400 into 503 with no body read, **151** read branches folding a 400 into `ok: true, data: []`, 23 other. **The population is 157**, not hank's 98 and not my b21 63 — **and the cause is one identifier: 99 of the 157 use a response variable literally named `r`.**

**The `sd_photos` size fix holds, and T17 is genuinely on the row** — the clean counter-example to my own b21 F4. Suite 26/0/0. The 64 KB cap is **per row**, so the 44,000-char budget does not compound; it would have blown at photo two had the collection been blob-wrapped.

**The sf_events anchor: the instruction said the seventh, measured it is the SIXTH.** Anchor 7 resolves exactly once and needed nothing. Re-anchored, pipe count asserted 7 → 7, `criticality_tier_check.py` **PROBLEMS:0**.

**b21's citation figures do not reproduce.** 571 / 198 / 373 / 0 provably stale / 39 likely, against b21's 551 / 196 / 355 / 0 / 37 — **on a byte-identical file** (`git diff --stat 7a5e6a11 HEAD` empty). The delta is **entirely predicate**.

## DECISIONS WAITING

1. **ITEM 2** — strike it from fourth's queue, or have **hank and cody both** release it and re-issue. Do not hand it to a third agent while two claims are live.
2. **The 151 read branches** fold a 400 into `ok: true, data: [], provisioned: false` — a silent failure strictly worse than the wrong 503 the reviewed commit fixed. **It is in nobody's open work.**

## OPEN, BY OWNER

* **hank** — helper **F1** (branch on `23514`, not class `23`) and **F2** (drop the bare `/does not exist/i`) **first**, because 88 branches now depend on that code; then the 69; then the 151. Plus the two `sd_photos` caller findings — the failed-downscale branch stores **and syncs** the original while the toast says it will not be backed up, and the 21,536-byte margin is counted in UTF-16 characters while `octet_length` counts bytes.
* **cody** — a REPLACEMENT COVERAGE generalisation arm (flip a **non-GRD** unit to `app: null` and back), and a per-resource refusal arm that **fails** a gate suite naming six resources and driving one.
* **cc** — print the touched-file count beside the `file-set` basis; the anchor-rot check's first three false positives (prose spans with empty parentheses); the b21 re-seat author-time guard, still open.
* **Michael** — the two decisions above.

## METHOD NOTE

**Three times in this batch a measurement was taken with a predicate narrower than the population, and every time the output read like a population.** b21's clause — *print the command and the raw count* — is necessary and not sufficient: all three would have printed a command. **When a predicate names an identifier, say which identifier**; and when a figure is carried into a second document, carry the predicate with it or re-derive it. **And: a list long enough to need an ordinal is long enough to need a program** — the instruction's own ordinal was wrong, and hand-counting would have hidden it.

*Full detail: `SAIRN-report-fourth-b22.txt`, `SAIRN-handoff-fourth-b22.md`. Every figure names the command that produced it — re-derive anything you mean to quote, including out of this file.*
