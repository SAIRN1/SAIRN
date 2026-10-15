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
    python docs/ablation/b15_arms.py                     # the 5 tools with
                                                         # no --ablation mode

---

## Tools with a `--ablation` mode

| tool | arms | layers | all load-bearing? |
|---|---|---|---|
| `tools/sairn_board_publish.py` | **28** | **21** | yes — **b15 added 7**, see below |
| `tools/runbook_constant_agreement.py` | 10 | 4 | yes |
| `tools/citation_anchor_rot_check.py` | **16** | **9** | yes — **added b14**, it landed in b13 with no ablation at all; **b15 added 3 arms and 2 layers** |

**These counts are as of b15 and will be wrong the next time somebody adds an
arm.** Re-read them from each tool's own `--ablation` output rather than from
this table; that is the eighth cross-domain convention applied to this file.

### `sairn_board_publish.py` — 21 layers

**b15 added seven**, all for one defect shape: b14 fixed *"the whole mirror
directory stopped"* and left *"one file in it kept moving"*, which reads more
reassuring than silence. `mirror-oldest-component` (2 arms),
`mirror-allowlist` (3), `append-only-family`, `partial-refresh-note`,
`digest-publish-age`, `seq-cross-check` (2), `mirror-notice`.

**`append-only-family` exists because the first version of the b15 fix was
wrong, and running it against the live mount is what said so.** Aged by the
oldest *file*, it reported `chain-tip-seq1098.tsr is 187h old` about a mirror
that had just been republished — the `chain-tip-*` set is **append-only** and
its old members are supposed to be old, so an oldest-file basis pins every
mirror with any history FROZEN for ever, and a verdict that is always FROZEN
is a verdict nobody reads. A23 is the arm for the defect; **A28 is the arm for
the trap the fix walked into.**

**`mirror-allowlist` is the self-reference guard.** b15 also made the
publisher write `MIRROR-FRESHNESS.md` into each mirror on every event, and an
age-by-newest-file basis would have made that notice the evidence that the
mirror it describes is fresh — a detector refreshing its own subject. A25
drives exactly that: write the notice into a frozen mirror, and the mirror
must still read FROZEN *and* the notice must be listed as UNAGED.

### `citation_anchor_rot_check.py` — 9 layers

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

### `citation_anchor_rot_check.py` — ablation added b14, 9 layers at b15

**b15 added `r1-anchor-keyword` and `trailing-newline-not-a-line`.**

`r1-anchor-keyword` answers a routed concern by **measurement rather than by a
code change**: fourth b22 routed `` `eventRefusals()` ``,
`` `liquorServiceCheck()` `` and `` `sc_auth` `` as this tool's likely first
three false positives. They are not — the real register measures **8 anchors,
8 resolving exactly once, 0 not**. R1 already requires the literal word
`anchor` and R6 already rejects a bare identifier, but **nothing held either
against these three spans and R1 had no ablation at all**, so the correct
behaviour was undemonstrated rather than proven. A8b is the arm; removing R1
reads every backticked span as an anchor and breaks A8b, A7 and A7b.

`trailing-newline-not-a-line` is an off-by-one caught by an arm asserting a
**number**: `--resolve-targets`' first version used `text.count(NL) + 1`,
calling a 3-line file 4 lines long, which would have blessed exactly one
citation past the end of every file in the repo — **stale reported as fresh**.
A12 asserts `file has 3 line(s)` and not merely the PAST-EOF verdict, which is
the only reason it failed.

The b14 six: `exactly-once`, `zero-count-finding` (2 arms), `declared-target`,
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

## b15 — the five tools that had arms and no ablation at all

**The population was measured, not assumed.** Over the b12–b14 range
(`9603441d..HEAD`), every `tools/*.py` cc touched that carries `@arm(`,
`def selftest(` or `def run_fixtures(` was classified by whether it also
carries any ablation:

    for f in $(git log --name-only --format="" 9603441d..HEAD -- tools/ \
                 | grep "^tools/.*\.py$" | sort -u); do
      grep -qE "@arm\(|def selftest\(|def run_fixtures\(" "$f" || continue
      grep -qE "_ABLATIONS|def ablation\(|ABLATION" "$f" \
        && echo "HAS  $f" || echo "NONE $f"
    done

**6 HAS, 12 NONE.** Of the 12, **six had arms LANDED in the range** and are
therefore in scope; the other six had only logic changed and are named at the
bottom of this section rather than dropped.

Re-run all of them with one command, which is the point:

    python docs/ablation/b15_arms.py            # all
    python docs/ablation/b15_arms.py <name>     # one

**It is a pass/fail/pass sandwich per layer, and that is not ceremony.** b14's
first lesson was a harness that restored its subject and left the subject's
*state* behind, so one layer read `load-bearing` in one run and `UNPROVEN` in
the next. This driver requires the baseline to pass, the ablated run to fail,
**and the restored run to pass again** — a restore that does not bring the
baseline back is reported `CONTAMINATED` and the measurement is discarded
rather than published. It also refuses to swap unless the old substring occurs
**exactly once**: a swap matching twice ablates the wrong thing, and one
matching nothing ablates nothing and reports a load-bearing layer.

| layer | tool | verdict |
|---|---|---|
| `bare-run-unattributable` | `bare_run_write_check.py` | **LOAD-BEARING** — 11→9 passed, 2 failed |
| `status-line-no-default-window` | `sairn_status_line.py` | **LOAD-BEARING** — 26/26 → criteria broken |
| `secrets-irreversible-runbook` | `secrets_inventory.py` | **LOAD-BEARING — only after b15 fixed it.** See Finding 3 |
| `red-suite-notice-not-couldnotrun` | `red_suite_register_check.py` | **LOAD-BEARING** — 10 cases, 2 failed |
| `batch-manifest-child-env` | `batch_manifest.py` | **LOAD-BEARING — only after the recipe was corrected.** See Finding 4 |

**Deferred, with its recipe recorded so it is not lost:**
`sf-events-exactly-once` in `tools/sf_events_anchor_check.py`. fourth holds a
**live claim** on that file (b23, declared FILES list), so per PR §4.3 the
conflict is declared and **not overridden** — the swap is written down in
`DEFERRED` inside the driver and runs after fourth releases.

**Arms did NOT land in the range for these six, so they are out of scope here
and said so rather than counted as clean:** `drive_upload_verify.py`,
`external_file_index_audit.py`, `live_probe_declaration_check.py`,
`mech_gate_live_probe.py`, `sql_column_exists_check.py`,
`tool_owner_map.py`. **Three of them are a layer with no arm anywhere** — the
`encoding='utf-8', errors='replace'` added to `git ls-files` calls in
`external_file_index_audit.py:60`, `live_probe_declaration_check.py:99` and
`:107`, and `sql_column_exists_check.py:104` and `:270` — landed in b12's
`070efcd3` with nothing driving a non-ASCII path through them. That is a gap
in the ARMS, which an ablation cannot see, and it is the same shape as
Finding 2.

### FINDING 3 — `secrets_inventory.py` reported a clean lock with ZERO arms run

Emptying `_IRREVERSIBLE` made the runbook loop iterate nothing, `bad` stayed
empty, and the tool printed its clean line. **The five arms guarding
`SD_AUTH_SECRET_PREVIOUS`'s rotation runbook could have been deleted and
nothing would have noticed** — a suite that runs zero tests and prints ALL
PASS, which is the exact shape `run_all_tests.py` carries a floor for.

Fixed in b15: `_MIN_RUNBOOK_ARMS = 5`, counted as the loop runs, with the
failure naming both numbers. **Pinned as a literal and not as
`len(_IRREVERSIBLE)`** — an arm that counts the subject against the subject
agrees with an empty table. Ablated after the fix: exit 2, *"only 0 runbook
arm(s) RAN, against a floor of 5"*.

### FINDING 4 — the first recipe ablated the half the arms do not see

`batch-manifest-child-env` reported **UNPROVEN** on its first run, and the
layer was fine. The child's utf-8 environment is passed at **two** call sites —
`return runner(cmd, CHILD_ENV)` and `subprocess.run(..., env=CHILD_ENV)` — and
the three fixtures drive the **runner** seam. The first recipe removed the
other one, so the arms never saw the ablation.

**Same trap as b14's `fail-closed-target`, inverted.** There, one layer written
twice survived either half being removed. Here, the arms cover only one half,
so an ablation of the *other* half proves nothing. **A layer written in two
places needs its ablation aimed at the half the arms actually reach — or at
both.** Recipe corrected to the runner seam: 35/35 → 32/35, exit 1.

**And the real `subprocess.run` call site still has no arm of its own.**
Recorded rather than papered over: the honest fixture there would have to spawn
a real subprocess under a forced cp1252 console, which is
`tools/cp1252_console_sweep.py`'s job and not this tool's. Routed as such.

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
