# Ablation records — cc's arms from b12, b13 and b14

**What an ablation record is, and why an arm alone is not enough.** An arm
proves a check *fires* on bad input. It does not prove the check is what
caught it. Only removing the layer and watching a **named arm** go red does
that — and the one time this platform skipped the step, b12's `latest-ceiling`
layer turned out to be deletable with no arm noticing. Per the twelfth
cross-domain convention: **ablation over chaos — remove ONE named layer on
already-clean code and measure what it alone catches, per ARM and not per exit
code.**

This file exists because cc b14 item 5 asked for an ablation record for every
arm landed in b12–b13 that lacked one, and **two of the answers are findings
rather than confirmations.** Those are at the bottom.

Re-run everything here with:

    python tools/sairn_board_publish.py --ablation
    python tools/runbook_constant_agreement.py --ablation
    python tools/citation_anchor_rot_check.py --ablation
    python tools/sairn_push_gate_hook.py --selftest     # inline ablations
    python tools/sairn_claim.py selftest                # inline ablation
    python tools/route_suite_failures.py --fixtures      # inline ablation

---

## Tools with a `--ablation` mode

| tool | arms | layers | all load-bearing? |
|---|---|---|---|
| `tools/sairn_board_publish.py` | 22 | 14 | yes |
| `tools/runbook_constant_agreement.py` | 10 | 4 | yes |
| `tools/citation_anchor_rot_check.py` | 12 | 6 | yes — **added b14**, it landed in b13 with no ablation at all |

### `sairn_board_publish.py` — 14 layers

`row-absence` (3 arms), `context-unknown`, `beacon-lag` (6),
`mirror-freshness` (2), `digest-tip-source` (5), `seq-glue`,
`unlisted-agent`, `readback` (2), `digest-label-bounds`, `highest-batch`,
`latest-ceiling`, `claim-subject`, `claims-survive-set`, `manifest` (2).

**`latest-ceiling` is the layer that justifies this whole file.** In b12 it
reported **NOTHING CAUGHT IT**: A8's fixture used a long digest field, which is
one line and capped at 900 characters, so the ceiling could be deleted and no
arm noticed. The real path to an overlong per-agent file is the uncapped
`claims` list. A8 was rebuilt on that, and now asserts against a **literal
60** rather than against `LATEST_MAX_LINES` — an arm that checks the file
against the same constant the code used is a tautology.

### `citation_anchor_rot_check.py` — 6 layers, added b14

`exactly-once`, `zero-count-finding` (2 arms), `declared-target`,
`fail-closed-target`, `r6-anchor-filter` (3), `near-match-report`.

**`fail-closed-target` reported UNPROVEN twice before the ablation was
right, and the reason is a good property of the code.** The fail-closed path is
ONE layer implemented TWICE: an `os.path.isfile` existence test *and*
`read_text()` returning `None`. Patching either half alone left the other
standing, so A4 stayed green and the layer looked deletable. The ablation now
removes both legs, because the layer is *"an unusable target is never a pass"*
and an ablation has to remove the whole of it. **A redundantly-guarded layer is
a trap for a lazy ablation.**

Two hooks exist purely so a layer can be *removed* rather than *rewritten*:
`_COUNT_IS_FINDING(n)` and `_TARGET_EXISTS(path)`. An ablation that rewrites
the function it measures tells you nothing about which layer caught the defect.

---

## Inline ablations, where the arm and its ablation live together

| tool | the layer removed | the arm that must go red |
|---|---|---|
| `tools/sairn_claim.py selftest` | the audit's active set selected on the raw `status` field instead of `is_active()` | A2 — driven against the pre-fix selector, **6/7, exit 1** |
| `tools/sairn_push_gate_hook.py --selftest` | `OVERRIDE_HINT` restored to its **b11 text** | the four b12 arms; the b11 text passes all eight original arms and fails exactly those four |
| `tools/sairn_push_gate_hook.py --selftest` | `exit3_reason()` restored to the **pre-b13 function** | the three b13 exit-3 arms — see the finding below |
| `tools/route_suite_failures.py --fixtures` | the ACTIVE selector restored to the raw field | the raw-status arm — see the finding below |

**Each of these restores the version it replaced, not some older one.** An
ablation against a distant ancestor proves only that *something* changed; an
ablation against the immediately-preceding version proves what the new arms
are for. The `OVERRIDE_HINT` case is the clearest: the b11 text was green on
all eight arms that existed while being false in two ways.

---

## FINDING 1 — the b13 exit-3 "ablation" was a string assertion, not an ablation

b13 wrote it as:

```python
ck('ABLATION: the PRE-FIX message asserted the platform cause ...',
   ('SKIPPED as not applicable on this platform -- exit 3'
    ).startswith('SKIPPED as not applicable'), True)
```

That asserts a property of a **literal**. It is true regardless of what the
code does — a comment wearing an arm's clothes, and it would have passed if
`exit3_reason()` had been deleted outright.

**Corrected in b14** to restore the pre-fix function and require all three b13
arms to go red on it, plus a control establishing that the pre-fix version was
never *silent* — it was confidently wrong, which is why no arm caught it for a
day.

---

## FINDING 2 — all three of b12's test-file-floor layers are UNPROVEN, and cc
cannot arm them

Measured in b14 by removing each layer from `tools/run_all_tests.py` and
running **cody's** `tests/run_all_tests_floor_probe.py` as a subprocess:

```
BASELINE  cody probe exit 0 -- ALL CHECKS PASS

ratchet                probe exit 0  STILL GREEN -- UNPROVEN
tracked-intersection   probe exit 0  STILL GREEN -- UNPROVEN
silence-breaking       probe exit 0  STILL GREEN -- UNPROVEN

RESTORED  sha256 0306a0e214b0b4fe  IDENTICAL
AFTER RESTORE  cody probe exit 0 -- ALL CHECKS PASS
```

**This is not cody's probe being wrong.** That probe predates b12 and tests
the shrinking-suite floor, that `MIN_TEST_FILES` is defined exactly once, and
that both bodies compare against it. It was never asked about the ratchet.

**So three real layers have no arm anywhere:**

| layer | what it does | what would have caught its removal |
|---|---|---|
| **ratchet** | the floor is read from `docs/test-file-floor.json` and rises, instead of a hand-maintained literal that sat at **370 against a real 802** — 432 files deletable with the guard silent | an arm that writes a floor file below the real count and requires the floor to come from the file, not the literal |
| **tracked-intersection** | the ratchet rises only as far as the discovered list **intersected with `git ls-files`** | an arm that drops an UNTRACKED `.py` into `tests/` and requires the floor NOT to rise past the tracked count. This is the one with a real incident behind it: the first ratchet raised the floor to **807 against a real 802** because this very probe writes five fixture files into `tests/` |
| **silence-breaking** | `behind` is part of the hook's early-return condition, so a clean tree whose floor has gone stale still produces output | an arm that sets the floor below the real count on an otherwise-clean tree and requires the hook to print something |

**`tests/` is cody's and cc does not write there**, so these three arms are
routed rather than added. The ablation harness that measured it is kept at
`docs/ablation/floor_layers.py` so cody can re-run it after adding them and
watch the three UNPROVEN lines turn into failures.

**The restore is verified by sha256 and the tree was confirmed clean
afterwards** — a script that edits a tracked tool and dies halfway leaves the
repo subtly wrong, which is worse than having no record.

### FINDING 2b — `tracked-intersection` is unarmed, but NOT harmless, and the
harness had to contaminate itself to show it

The first two runs of the harness **reproduced b12's incident on demand.**
With the intersection removed, the ratchet counted the floor probe's five
untracked fixture files and wrote a floor of **812, then 813, against a real
808** — exactly the 807-against-802 shape the layer exists to stop.

**cody's probe still exited 0 in the run that did it.** The harm lands on the
*next* run: the floor is now above the tree, so the probe reports
`discovered (808) >= MIN_TEST_FILES (813)` and fails for a reason that has
nothing to do with the code under test. So the precise verdict is: **the layer
is unarmed in-run and destructive across runs**, which is worse than merely
unarmed and is the strongest argument for the arm cody is being asked to add.

**And the harness itself was the second defect.** It restored the TOOL and left
the FLOOR FILE poisoned, so the third layer's verdict changed between runs —
`silence-breaking` read `FAILS (load-bearing)` in the contaminated run and
`UNPROVEN` in the clean one. **An ablation that leaves its subject's state
behind has contaminated every measurement after it.** The harness now
snapshots and restores `docs/test-file-floor.json` **per layer**, not once at
the end, and the clean measurement above is the one taken afterwards.

The floor file was corrected to 808 by hand, with the reason recorded in the
file, because the ratchet only ever rises — lowering it is a human edit and
this was one.

---

## What this file does not claim

- **It is not a coverage figure.** "Every layer load-bearing" means every
  layer breaks *at least one* arm. It does not mean the arms are sufficient,
  and three layers above have *zero*.
- **An ablation cannot see a layer nobody wrote an arm for in the first
  place** — which is exactly how Finding 2 surfaced, and only because the
  ablation was driven from outside the file that owns the arms.
- **Nothing here is a statement about `tests/`.** Every arm counted above is
  in a file cc owns.
