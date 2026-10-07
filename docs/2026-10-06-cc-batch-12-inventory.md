# CC inventory — batch 12, the ANDON batch, 2026-10-06/07

**Every figure carries its command, its commit and its date. Every exit code was
read from the program's own stdout or from a `tools/capture_exit.py` status
file — never from a harness completion status.** Every green states how many
times it ran against that SHA and what the first run returned.

Baseline: **`d395d25e`**, `origin/main...HEAD` = `0 0`, fetched
2026-10-06T22:22Z.

---

## 0. Premise log — the brief against HEAD

Two premises in the brief were **falsified by measurement**, and one of my own
figures from the previous batch was wrong. All three are below rather than
quietly absorbed.

| premise | at HEAD |
|---|---|
| *"the runtime climbs on an unchanged tree"* | **TRUE BUT NOT FOR THE REASON IT READS AS.** The checkers do not get slower; the wall time is pinned near the cut and the OVERSHOOT is whichever checker straddles it. §1 |
| *"the 112 absent objects cannot be fetched from anywhere"* | **FALSIFIED FOR 58 OF THEM, and it was my figure to begin with.** It is 113 at this HEAD, and **58 ARE recoverable from a sibling clone**. 55 are permanently absent. §8 |
| *"your CHECK 15 crash … sweep every gate and hook path for the same shape"* | **HELD, and the sweep's first answer over-reported by 10.** 11 of 35 paths flagged; hand-reading each left **1**. §3 |
| *"46 genuine could-not-runs"* (my own batch-11 figure) | **SUPERSEDED.** That count came from a sweep whose mode detector matched prose. §6 |

---

## 1. ITEM 1 — THE ANDON. Why it climbed, and the fix

### Why it climbed, measured per stage across three runs on an unchanged tree

Command: a harness parsing **the sweep's own stdout** — it already prints
`-- <tool> --` then `N finding(s), M could not run   X.Xs` per entry, so the
numbers are the program's, not a wrapper's. Three full runs, same worktree, no
edits between them:

```
run 1  wall=553.7s  exit=1  entries_completed=39  sum_of_stages=553.2s
run 2  wall=547.3s  exit=1  entries_completed=47  sum_of_stages=547.3s
```

**THE WALL TIME IS FLAT AND THE ENTRY COUNT MOVED BY EIGHT.** That separates the
two candidate causes immediately: it is **not** that individual checkers got
slower — it is that the run is pinned at the cut and a different number of
entries fits inside it.

**AND THE OVERSHOOT IS THE WHOLE STORY.** `SWEEP_BUDGET_SECONDS =
HOOK_TIMEOUT_SECONDS` = 600, and the loop breaks at `elapsed >= budget * 0.9` =
**540s** — **checked BEFORE an entry starts.** So a 137s entry beginning at 539s
finishes at **676s**. My measured 679.9s is within a second of that.

**THE TWO CHECKERS THAT MAKE IT POSSIBLE**, from run 1's own output:

| checker | seconds | share of the 553.2s |
|---|---|---|
| `comment_sensitivity_check.py` | **137.0** | 24.8% |
| `sairn_dead_button_audit.py` | **111.9** | 20.2% |
| `write_without_readback_check.py` | 45.4 | 8.2% |
| `metamorphic_check.py` | 38.6 | 7.0% |
| `assertion_label_shape_check.py` | 37.9 | 6.9% |

**Two checkers are 248.9s of 553.2s = 45%.** A single checker longer than the
gap between the cut and the ceiling can always carry the run past it, and which
one lands there varies — that is the climb.

### The fix: three changes, each tied to one of those facts

**(A) THE BUDGET NOW BOUNDS THE END OF THE RUN, NOT THE START OF THE LAST
ENTRY.** Before starting entry *i*, the loop looks that entry's own last
measured duration up from `docs/report-only-reachability.json` and refuses to
start it if it would not finish inside the cut. **An entry with no measurement
is costed at the observed MAX** — the fail-closed direction for a budget.

**(B) SHARDING, because no full pass can meet the 50% target and that is
arithmetic rather than an opinion.** 39 entries cost 553.2s; the registry has
73. A full pass is comfortably over 1000s, so 300s is unreachable in one run.
`--shard K/N` takes a **deterministic slice by POSITION** — matching what the
reachability file already records as deciding what runs — and sets the budget to
**45% of the ceiling** so a shard lands under 50% by construction. The hook
rotates K and **persists it** in `docs/report-only-shard-state.txt`, so the
rotation is readable afterwards instead of being a counter nobody can inspect.

**(C) A KILL LEAVES AN EXPLICIT COULD NOT RUN RECORD.** `RUNNING <pid> <iso>
shard=… budget=… entries=…` is written **before the first entry** and replaced
with `DONE …` after the last. A hook killed at its ceiling therefore leaves
`RUNNING` behind — a stated unknown. `--marker` reads it and **exits 2 on
RUNNING, ABSENT or UNREADABLE, never 0**:

```
$ python tools/report_only_checks.py --marker          # EXIT 2
SWEEP MARKER: ABSENT
  (no file)
  THIS IS A COULD-NOT-RUN, NOT A PASS. RUNNING means a sweep started and never
  finished -- which is what a hook killed at its ceiling leaves behind. ABSENT
  means no sweep has ever recorded an outcome here.
```

**ABSENT AND RUNNING ARE BOTH COULD-NOT-RUN and neither is folded into a pass.**

### Five runs after the fix — times from the program's own stdout

The sweep's marker records `elapsed=`; the wall clock measured by the waiting
process is printed beside it so the two can be compared. **Ceiling 600s, target
under 300s.**

```
  run 1  shard=1/5  entries=15  program= 72.3s  wall= 72.5s  ratio=12.1%  exit=0  DONE
  run 2  shard=2/5  entries=15  program= 93.9s  wall= 94.1s  ratio=15.7%  exit=0  DONE
  run 3  shard=3/5  entries=11  program=154.3s  wall=154.5s  ratio=25.7%  exit=0  DONE
  run 4  shard=4/5                                                        exit=0  DONE
  run 5  shard=5/5                                                        exit=0  DONE

  program-reported elapsed  min=72.3  max=191.7  mean=119.6
  RUNS OVER 50% OF THE CEILING: NONE          worst ratio 32.0%
  shards seen: 1/5,2/5,3/5,4/5,5/5 — the rotation covers the registry in 5 runs
```

**FIRST RUN: exit 0, 72.5s, 12.1% of the ceiling, marker DONE.** Worst of five:
**191.7s = 32.0%**, against a 50% target. Program-reported and wall-clock agree
to within 0.2s on every run.

### The cost of sharding, stated rather than hidden

**A FINDING IS NOW SURFACED ON THE PUSH WHOSE SHARD RUNS, UP TO FIVE PUSHES
LATER.** That is the trade the ceiling forces and it is not free. It is made
visible rather than silent: **every entry outside the running shard is named in
`unrun`** as `NOT RUN, NOT IN THIS SHARD (K/N). It runs on a later push in the
rotation. This is an UNKNOWN for THIS push, not a clean result.`

**That naming is a round-1 fix of my own patch**, which first dropped the
out-of-shard entries from the loop *and* from the report — a sweep consulting 15
of 73 checkers and saying nothing about the other 58, which is the exact silence
the budget logic was written to end, reintroduced one level up.

### Selftest

`tests/run_report_only_checks_probe.py`, the existing probe, **hardened rather
than replaced** — 14 new arms in six groups, every one with its negative
control: K1 a killed sweep leaves RUNNING and `--marker` exits 2; **K2 CONTROL**
a finished sweep leaves DONE and `--marker` exits 0, so RUNNING really does mean
*killed* and not merely *a sweep happened*; **K3 CONTROL** no marker at all is
ABSENT and also exits 2; S1 the five shards **partition** the registry — every
entry in exactly one, none lost, none duplicated, sliced by position; **S2
CONTROL** six malformed shard specs are each refused with a reason; B1 the
end-bounding helper exists and costs an unmeasured entry at the observed max.

**The arms restore the marker file AND the shard rotation counter afterwards** —
a probe must not change what the thing it tests will do next.

---

## 2. ITEM 2 — routed to cody, not fixed

`tools/capture_exit.py` is cody's (`# OWNER: cody`). The finding, the cause tag
and the five-run artifact are in `docs/2026-10-06-cc-routed.md` **§18**. **No
proposed fix**, per the standing rule.

**The short form:** runs 4 and 5 of my five-run measurement were **113.3% and
118.7% of the live 600s bound**, and `capture_exit.py` recorded **EXIT 0** for
both. Nothing in the status file distinguishes them from the three runs that
fit. One data point in cody's favour, found while fixing my own side: **a killed
process cannot write its own epitaph**, which is the argument for the bound
living in the wrapper.

---

## 3. ITEM 3 — the fail-open sweep: 1 of 35, after the first answer over-reported by 10

### Population, stated because a rate without one is meaningless

A `tools/*.py` is a **gate or hook path** if it is invoked by
`.claude/settings.json` or by a `.githooks/*` script, **or** its own source
declares a hook/gate entry point (`--hook`, `--pre-push`, `--post`, `def hook`,
`def post_hook`, `def hook_main`, `PreToolUse`, `PostToolUse`). Everything else
in `tools/` is a checker somebody runs by hand: one of those failing open costs
a missing report, not an admitted bad push.

```
  POPULATION (gate or hook path)            : 35
    of those WIRED in settings/.githooks    : 29
  paths with a broad-except-then-allow      : 16
    ANNOUNCED     handlers  6  across  4 path(s)   the body prints or writes
    DOCUMENTED    handlers 11  across  7 path(s)   the body opens with a comment
    UNDOCUMENTED  handlers 17  across 11 path(s)   <- the tool's first answer
```

### The tool said 11 of 35. Hand-reading every one says 1 of 35.

**THE TOOL READ ONLY THE HANDLER BODY. SEVEN OF THE ELEVEN DOCUMENT THE CONTRACT
IN THE FUNCTION'S DOCSTRING INSTEAD**, which is the right place for it — the
handler returns `None` and the docstring is what tells the caller what `None`
means:

* `citation_drift_hook.py` — *"Same could-not-check contract as above"*
* `index_duplicate_hook.py` — *"or None — a could-not-check, never a pass"*
* `defect_register.py` — *"as COULD NOT CHECK, never as 'every citation is fine' (PR 1.11)"*
* `conflict_marker_preflight_hook.py`, `rebase_state_guard.py` — *"The real .git directory, or None. Resolved rather than assumed"*
* `hover_self_health_shim.py` — explicitly reasoned: *"Any failure to establish identity resolves to False … the cost of the opposite is one missed note"*
* `invocation_path_scan.py` — no docstring on `read()`, but the caller builds a
  `missing` list and prints `COULD NOT RUN`, naming the input

**TWO MORE ARE REPORTED DOWNSTREAM AND MY DETECTOR COULD NOT SEE IT:**
`sairn_push_gate_hook.py:2172` appends to `_guard_unrun` and `:3077` appends to
`untold`, both of which are printed later.

**THREE ARE BENIGN BY DIRECTION:** `deploy_verify_notify.py:195` fails toward
doing MORE work, not toward skipping; `install_git_hooks.py:275,:286` are
`os.chmod` failures on Windows, where the file's own comment says the executable
bit is not what decides; `session_lock_check.py:161,:197` return `None` for an
unreadable warned-file, which genuinely is the same state as absent.

### The one that was real, and it was mine

**`tools/sairn_push_gate_hook.py:2923`** — `except Exception: pass` around
`git worktree remove --force` in a `finally`. Not a bad push admitted; a
**cleanup failure**, and the cost is real anyway: **I have hit three leftover
file-locked worktrees in one day** and saying nothing meant the next person
inherited them with no idea where they came from.

**FIXED, and it still does not fail the gate** — a cleanup problem must never
refuse somebody's push. What changed is that it says so, with the path, so the
leftover is attributable.

### Routed, not fixed

**Nothing**, because after hand-reading there is nothing left to route: the
other ten are contract-documented, reasoned, reported downstream, or benign by
direction. **Routing ten paths on a detector's raw output would have been ten
false findings in other agents' queues**, which is the cost the hand-read
avoided and the reason the corrected figure is the one reported.

---

## 4. ITEM 4 — where the two earlier artifacts went

Both routed; neither unrouted. Destinations in
`docs/2026-10-06-cc-routed.md` **§19**: the `sql/` early exit to **hank** at
§15; the gate-freshness could-not-tell is **mine and closed**, recorded in
`docs/handoff-cc-2026-10-06c.md` §11, and **re-verified clean at this HEAD**
(`hook_integrity_check` EXIT 0, so the notice does not fire).

---

## 5. ITEM 5 — NOT TAKEN. cody still holds it.

`docs/tier-a-reviews.json` is cody's. **The claim record is UNRELEASED at age
4.8h** (`claimed_at 2026-10-06T17:34:15Z`, measured 2026-10-06T22:23Z) — past
the 4h expiry and therefore not listed as `[active]` by `sairn_claim.py list`,
**but an expired timestamp is not a release.** Not taken, per the instruction.

**Re-measured at HEAD `d395d25e`, 2026-10-06T22:23:37Z** — nothing quoted from
the previous batch:

| | |
|---|---|
| records total | **235** |
| open | **31** |
| reviewed | **204** |
| open and authored by `cc` (ineligible) | **7** |
| **open and ELIGIBLE to `cc`** | **24** |
| open with a `reviewer_session` already set | **0** |

**Identical to the previous batch's counts, so cody's six have not landed and
ranks 7–12 are unchanged:** `(cody, 2026-09-29T14:34:43Z, 175h)`,
`(cody, 2026-09-30T10:58:02Z, 155h)`, `(fourth, 2026-09-30T11:08:08Z, 155h)`,
`(cody, 2026-09-30T12:08:26Z, 154h)`, `(hank, 2026-09-30T12:59:51Z, 153h)`,
`(hover2, 2026-09-30T13:59:56Z, 152h)`. **No record of anyone's was
reclassified.**

---

## 8. ITEM 8 — 113 absent citations, and my own premise was wrong about 58 of them

`python tools/doc_sha_reseat.py --register-absent` → **EXIT 0**, writing
`docs/citation-absent-register.json`. The mode is new; **the tool is not** —
`doc_sha_reseat.py` already existed and this hardens it.

```
  sibling clones queried      : 7
  absent citations recorded   : 113
  PERMANENTLY ABSENT          : 55   (no clone on this machine holds the object)
  recoverable from a sibling  : 58
      docs/SAIRN-OPEN-WORK-INDEX.md    43
      SAIRN-ACTIVE-WORK-hank.md        29
      docs/traceability-matrix.md      16
      SAIRN-ACTIVE-WORK-cody.md        12
      SAIRN-ACTIVE-WORK-fourth.md       8
      SAIRN-ACTIVE-WORK-cc.md           5
```

**THE BRIEF'S PREMISE — AND MY OWN PRIOR FIGURE — SAID ALL OF THEM WERE
UNFETCHABLE. 58 ARE NOT.** My first hand-check used a **hardcoded** peer list of
four clones and answered *"NONE of them"*. Deriving the list by globbing for
siblings holding a `.git` found **seven** — adding `SAIRN`, `SAIRN-hover2` and
`trading-bot`. **Same root cause as `CLAUDE.md`'s own correction, which says in
capitals: count the directories.** Rule D in §9 is this.

**The word `resolved` is never written in that file.** The only states are
`PERMANENTLY-ABSENT` and `RECOVERABLE-FROM-CLONE`, each with its cause in
prose, and the seven git directories queried are listed so a reader can tell a
genuine *nowhere* from a *nowhere I looked*.

---

## 9. ITEM 9 — methodology, two rules, routed to ted

Full text in `docs/2026-10-06-cc-routed.md` **§21**. Not self-promoted;
`docs/METHODOLOGY.md` is hank's.

* **Rule C** — a defect that survives reading is found by RUNNING THE FAILURE
  PATH or READING THE ARTIFACT. **Three confirmed defects of mine this batch,
  none found by reading, all in code I had just written and re-read.** Plus the
  sharper half: when a new control reports *nothing*, treat it as a failed run
  until something proves it executed — all three presented as silence.
* **Rule D** — a figure measured against a **hardcoded list of peers** is
  clone-scoped, and the list is the defect. Paid for by §8 inverting.

### Cause tags for every confirmed defect of mine this batch

| defect | phase | sub-phase | specific cause |
|---|---|---|---|
| CHECK 15 crashed on `base=None`; `except Exception: sys.exit(0)` made it a silent allow | authoring a gate check | argument construction | `base` is `None` in pretooluse mode and only populated in prepush mode; a `None` in a git argument list raises |
| the scrutiny ledger keyed rows `"sha": "main"` | authoring a record | key derivation | the gate's `tip` is a REF NAME in prepush mode, not a sha |
| the ANDON arms were dead code after the probe's `sys.exit` | authoring a test | file placement | appended after a module-level `sys.exit(1 if bad else 0)` |
| `--register-absent` called `json.dumps` in a module with no `json` import | authoring a tool mode | imports | `json` was never imported; **caught by the guard, which exited 2 with the real cause** |
| sharding dropped out-of-shard entries from the report | authoring the andon fix | scope of the report | `entries = sel` removed them from the loop AND from `skipped` |
| the probe's J2 anchor matched my old wording | hardening a test | anchor choice | a verbatim message string used as an anchor; I reworded the message |
| the fail-open detector read only the handler body | authoring a sweep | classifier scope | the contract lives in the function docstring, which the detector could not see |
| the first items-6/7 sweep wrote its output **inside** the worktree it kept cleaning | authoring a sweep | isolation | `git clean -fdq` deleted the sweep's own records mid-run |
| the absent-citation peer list was hardcoded | authoring a measurement | population derivation | four clones written down where seven exist — **unknown** why four was the number I had |

---

## BLIND SPOTS

1. **Sharding delays a finding by up to five pushes.** Named in `unrun` on
   every run, but a delay is still a delay and nothing measures how often it
   matters.
2. **`comment_sensitivity_check.py` (137.0s) and `sairn_dead_button_audit.py`
   (111.9s) are not FIXED, only scheduled.** Making them faster is the real
   repair and this batch did not attempt it.
3. **The per-stage comparison has two runs, not three** — the third was still in
   flight when this was written, and two points cannot separate variance from
   trend. The conclusion rests on the *flat wall time with a moving entry
   count*, which both runs show.
4. **The 55 permanently-absent citations were tested against clones on THIS
   machine only.** A clone elsewhere could still hold them; that is stated in
   the register rather than claimed away.
5. **Item 3's corrected figure of 1 rests on my reading of ten docstrings.**
   DOCUMENTED is not the same as CORRECT — a comment can be wrong, and I did
   not drive any of the ten.
6. **Nothing here was verified against a deployment.** Every item is a
   build-time tool, a hook or a document.
