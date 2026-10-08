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

## item 4 — DONE. The row is **CLOSED as not needed**, with the reasoning measured, plus one change that costs no new noise.

### Why there is no new check, and it is not a judgement call

```
command : scratchpad/b26/i4_measure.py over every `python tools/...` /
          `node tests/...` command line in docs/*.md
commit  : f7bab1b0        date: 2026-10-08
corpus  : 398 command lines, 107 distinct
  already flagged by the EXISTING rules : 0
  already route through capture_exit.py : 1
  judged attributable, no status file   : 106
A STANDALONE BACKGROUNDING WARNING WOULD BE NEW OUTPUT ON 106 OF 107 (99%).
```

And the hook fires on **every** Bash call, not only documented ones, so 99% is a
**floor** on the live rate rather than an estimate of it.

**THREE REASONS, IN ORDER OF WEIGHT:**

1. **IT IS OUTSIDE THE TOOL'S INPUT.** This tool reads command **text**. Whether
   a run is backgrounded is decided by the harness **after** the text exists.
   `grep -cin background tools/exit_status_attributable.py` → **0**, and that is
   correct rather than an omission: the signal is not in its input.
2. **THE GAP IS ALREADY CLOSED BY ANOTHER TOOL, and that tool says so.**
   `tools/capture_exit.py`'s own docstring reads: *"That advice is CORRECT and
   `tools/exit_status_attributable.py` is right to give it. IT STOPS BEING
   CORRECT THE MOMENT THE RUN IS BACKGROUNDED."* The division of labour is
   recorded; what was missing was a **pointer**, not a checker.
3. **A 99% FIRING RATE IS HOW A HOOK GETS SWITCHED OFF**, and a disabled hook
   protects nothing. That is this platform's own stated failure mode, and it
   would trade a real warning for a wall of text.

### The one change made instead — zero new firings

The existing warning now ends with:

> *AND IF THIS RUN MAY BE BACKGROUNDED, `$?` will be the wrapper's and not the
> program's: use `python tools/capture_exit.py --status <file> -- <command>` and
> read the status FILE.*

**It rides on a warning that was already firing**, so it adds words to an
existing message and **no new messages**. Verified by driving the hook:

```
echo '{"tool_name":"Bash","tool_input":{"command":"python tools/metamorphic_check.py | tail -5"}}' \
  | python tools/exit_status_attributable.py --hook
  -> names "capture_exit.py --status" and "read the status FILE", 775 bytes
python tools/exit_status_attributable.py --selftest -> EXIT 0, 40 ok, 0 FAIL
```

**ROW CLOSED.** `docs/2026-10-08-cody-b26-routed.md` records the close so the
routing table in `docs/2026-10-06-cody-routed.md` is no longer pointing at
unfinished work — which was the actual complaint: a row with no body.
