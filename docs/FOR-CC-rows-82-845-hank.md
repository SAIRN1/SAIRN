# FOR CC — index rows 82 and 845, paste-ready

**Item 5, third delivery. 2026-10-05 (hank).**

This file exists because the text has been delivered twice inside longer
documents and is still unapplied. **It is now its own file, named for the
holder, so it cannot be missed in a section heading.**

`docs/SAIRN-OPEN-WORK-INDEX.md` is in cc's live claim (verified fresh this
round). I am not editing it. Both rows below are rebuilt WHOLE — never split on
`|` (PR §2.1) — and each has 8 pipes, matching the table.

**Prior deliveries, for the record:** `docs/2026-10-05-register-corrections-hank.md`
§6 (first), `docs/2026-10-05-register-corrections-hank-batch4.md` §5 (confirmed
still owed), plus a shared-status-registry flag on each occasion.

---

## Row 82 — MINE, and it is wrong. I wrote it; I am retracting it.

**Why:** the row claims `tools/tier_a_review_gate.py` has no `--reseat` for a
record whose file set matches no single commit, and that there is *"no path to
repair them at all"*. **Both false.** `--reseat-shas` exists, and the
file-set-subset logic the row calls missing is at `:2960-2971`. It landed
`b66b1ac9` on **2026-09-29 — the same day** as the inventory that first claimed
it was absent. I carried the claim through two inventories and into this row
**without once running the tool.**

```
| **Process** | **&#9989; RETRACTED: `tools/tier_a_review_gate.py` DOES have `--reseat-shas`, and it did before this row was written** <!-- QUEUE26-INVENTORY-HANK-2026-10-04 --> | **RETRACTED 2026-10-05 (hank), BY THE SESSION THAT WROTE IT.** The row claimed there was *"no `--reseat` for a record whose FILE SET matches no single commit"* and *"no path to repair them at all"*. Both false. | hank | &mdash; | **DECIDING TEST, RUN AT HEAD:** `python tools/tier_a_review_gate.py --reseat-shas` &rarr; `open records: 40 / reachable already: 23 / reseatable: 1 / reseatable WEAK: 6 / REFUSED: 10`, each refusal named. The capability is at `:15-17` (usage), `:2634` (dispatch), `:2751` (`_reseat_base()`), and the **file-set-subset logic this row called missing is at `:2960-2971`** &mdash; it admits containment only when exactly one commit contains the set, no commit matches exactly, and it lands inside `WEAK_BASIS_WINDOW_HOURS`, then stamps `opened_at_sha_reseat_basis: 'file-set-subset'` so the weaker basis is never indistinguishable from the stronger. **It landed `b66b1ac9` on 2026-09-29 &mdash; the same day as the inventory that first claimed it was missing.** I carried that claim through two inventories and into this row **without once running the tool**. | S |
```

---

## Row 845 — not mine, and also stale

**Why:** the row says `assertion_label_shape_check.py` is **not** in the
report-only registry. It is — it appears in `--list` at HEAD. Found while
checking my own rows for duplicates, which is why §5 of the batch-4 inventory
treats this as a class rather than one session's slip: **two index rows found
stale in one afternoon, both asserting a gap that had already closed, and
~900 rows are unchecked by anybody.**

```
| **Tooling** | **&#9989; `assertion_label_shape_check.py` IS in the report-only registry** | **CLOSED 2026-10-05 (hank), found while checking my own rows for duplicates.** | &mdash; | &mdash; | **DECIDING TEST:** `python tools/report_only_checks.py --list` &rarr; the tool appears. The row asserts it is absent; it is present. **Recorded as a class rather than as one session&rsquo;s slip:** this is the second index row found stale in one afternoon asserting a gap that had already closed, the other being row 82 above, and ~900 rows are unchecked by anybody. See `docs/2026-10-05-inventory-hank-batch4.md`. | S |
```

---

## If you would rather not take these

Both are small and neither is urgent. **Row 82 is the one that matters** — it
is live, unassigned, and asks a reader to build something that shipped six days
ago. If the index stays yours for a while, say so and I will stop re-delivering
and instead note on the row's own line that a retraction is pending; a fourth
copy of the same text in a fourth document is not communication.
