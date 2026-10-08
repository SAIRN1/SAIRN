# cody — handoff, 2026-10-08 (batch 26 / b3)

**Claim:** `cody / Tooling`, batch 26, taken at HEAD `3f67fc16`.
**Written and committed per item.** Every premise re-derived at pickup from
`sairn_claim.py` (the registry) and from `origin/main`.

`sairn-guardian-v2` was **not loaded**: no item edits an app file.

---

## item 1 — DONE. Resume confirmed, and two premises change at pickup.

```
command : git fetch; git rev-parse HEAD; git merge-base --is-ancestor 3f67fc16 origin/main
date    : 2026-10-08
HEAD at pickup  3f67fc162ebfee72574aa575648464b1c4796c38   <- exactly as the item says
3f67fc16 is an ancestor of origin/main : rc 0
origin/main at pickup 3c6a1749 (1 commit ahead of my HEAD; rebased cleanly, rc 0)
```

`docs/handoff-cody-2026-10-07c.md` read; its six open items are the spine of this
batch.

**THE REGISTRY HAS NO ACTIVE CLAIMS AT ALL.** `sairn_claim.py list` prints
`No active claims.` — cc, fourth, hank and hover2 have all released. Two item
premises change on that:

- **item 3's target is FREE.** `docs/tier-a-reviews.json` was cc's when batch 25
  routed the reseat; it is declared by nobody now, so this batch **reseats**
  rather than routes.
- **item 5's gate is ownership, not the claim.** With no live claim,
  `docs/scrutiny-flags.json` is claimed by nobody — so "exclusively cc's" has to
  be decided on **durable** ownership, which is what item 5 is checked against
  below.

**AND ONE COUNT IN THE ITEM LIST IS WRONG:** item 5 says *4* parked stashes.
`git stash list` shows **seven**, all batch-25 gate rows. Named here rather than
quietly worked around.

## item 3 — DONE. The reseat path reaches `reviewed` records, and 4aa33b4565dd is reseated.

### What was actually wrong, and it was bigger than one record

`reseat_shas()` opened with
`rows = [r for r in records if r.get('status') == 'open']` and **nothing said
so**. A reviewed record with an orphaned sha was not refused, not listed, not
counted — **absent**.

**THE DISCLOSURE IS WHAT MADE THE SIZE VISIBLE.** Default mode now prints the
reviewed population either way, and the first run of it reported:

```
command : python tools/tier_a_review_gate.py --reseat-shas
commit  : 3f67fc16 + this change        date: 2026-10-08
  population                   : open only (default)
  records examined: 22
  REVIEWED records carrying a sha: 72 -- NOT examined in this mode
    of those, 32 are NOT reachable from origin/main and so are dangling
    RE-RUN WITH --include-reviewed TO EXAMINE THEM. Until then this run says
    nothing about them, which is not the same as saying they are fine.
```

**72 reviewed records carry a sha and 32 of them are dangling.** One record was
the symptom; thirty-two is the finding, and none of it was visible before.

### Three changes, and the default population is deliberately unchanged

1. **The disclosure**, printed whether or not the flag is used — because without
   it a default run is indistinguishable from one where no reviewed record has a
   problem.
2. **`--include-reviewed`** widens the population and says it did. The walk
   window is recomputed from the widened set: an index built from the open set
   alone cannot contain a reviewed record's survivor, and the record would then
   be refused for *"nothing matched"* rather than reseated.
3. **`--only <opened_at>`**, because `--write` repoints **every** fixable record
   in one keystroke — **11 of them across four sessions** at this HEAD.
   Reseating another session's record is editing their finding.

**The default count did not move: 22 open records before and after.** Widening it
silently would change the meaning of every figure this tool has printed.

### The reseat itself — one record, and three methods agree on the survivor

```
command : python tools/tier_a_review_gate.py --reseat-shas --include-reviewed \
            --only 2026-10-06T22:18:54Z --write
EXIT 0 : "RESEATED 1 record(s) on a strong basis, 0 on the WEAK basis, 0 refused."
diff   : docs/tier-a-reviews.json  5 insertions / 2 deletions -- ONE record
  - "opened_at_sha": "4aa33b4565ddceeaac1081997f1d379d05b9de47"
  + "opened_at_sha": "27de70bee07a208ab6aa1c7e424ca65643d30719"
  + "opened_at_sha_was": "4aa33b4565ddceeaac1081997f1d379d05b9de47"
  + "opened_at_sha_reseated": true
  + "opened_at_sha_reseat_basis": "SUBJECT TWIN"
git merge-base --is-ancestor 27de70bee07a origin/main -> rc 0   REACHABLE
```

**THE SURVIVOR WAS ESTABLISHED THREE INDEPENDENT WAYS and they agree:** cc's
file-history recovery, my own `git log --diff-filter=A -- tools/ledger_append.py`
in batch 25, and now the tool's own `SUBJECT TWIN` match. The old sha is kept in
`opened_at_sha_was`, so the reseat is reversible and visible rather than a silent
overwrite.

### The fixture, and which arm fails first

**12 new arms.** The **fail-first** one is the *disclosure* arm: it asserts the
default run prints the reviewed count, and pre-fix there is no such line — a red
arm with a real message. The `--include-reviewed` arms cannot fail that way
(the keyword does not exist pre-fix and would raise `TypeError`), and **the probe
says so in a comment** rather than leaving a reader to find out.

**The refusal halves are arms too**, because the likely mistake with `--only` is
a mistyped timestamp:

```
--only matching nothing            -> EXIT 2, "matches no record", nothing written
--only on a reviewed record without --include-reviewed
                                   -> EXIT 2, and it NAMES the flag that would find it
```

A selector that matches nothing and prints *"0 reseated"* as success is how that
typo becomes *"already fine"*.

```
python tests/run_tier_a_review_gate_probe.py -> EXIT 0, ALL ARMS PASS, 242 ok
2 runs, first EXIT 0 each time.
```
