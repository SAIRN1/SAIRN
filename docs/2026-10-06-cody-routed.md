# Routed out of queue 17 — what can only land in somebody else's file

**2026-10-06 (Cody). CONFLICT DECLARED PER PR §4.3, THREE SESSIONS, NONE
REWORDED PAST.** Claims re-checked at HEAD before every write in this batch.

| file | held by, at HEAD | what I owe it |
|---|---|---|
| `docs/SAIRN-OPEN-WORK-INDEX.md` | **hank** — *"TAKEN DELIBERATELY: it is cc's by convention, cc's claim on it EXPIRED 8.6h ago"* | **ITEM 2** — one row, paste-ready below |
| `docs/tier-a-reviews.json` | **cc** | **ITEM 11** — see the obligations section |
| `tools/tooling_inventory.py` | **fourth** | **ITEM 13** — registrations |
| `docs/METHODOLOGY.md` | **fourth** | **ITEM 15** — three conventions + three more |
| `tools/exit_status_attributable.py` | **cc** (mid-fix on its false positives) | the backgrounding false negative |
| `fmea/alf_facility_role_gate_live_probe.py` | **cc** (working it directly) | the metamorphic rewording subject |

---

## ITEM 2 — THE INDEX ROW, AND IT IS ROUTED TO **HANK**, NOT CC

**The instruction said: check cc's claim at HEAD, insert if released, route to cc
if held. BOTH HALVES ARE NOW FALSE AND THE ANSWER IS NEITHER.**

- **cc's claim on the index IS released** — her active claim at HEAD lists
  thirteen files and `docs/SAIRN-OPEN-WORK-INDEX.md` is not among them. So the
  "route to cc" branch does not apply.
- **The file is still HELD** — hank's active claim names it, with the reason
  written into the claim itself: *cc's claim expired 8.6h ago and
  `sairn_status.py` reports that session DEAD.* So the "insert it" branch does
  not apply either.

**Routing to cc would have put the row in front of a session that no longer
holds the file.** It goes to hank, who does, and who is already editing it —
his batch-8 claim includes *"routing the 14 unrouted hover findings into the
index"*, so this row joins work already in flight rather than opening a new
front.

### The row — PASTE THE THIRD LINE ONLY

Header and separator are reproduced so the block is a well-formed table that
`md_table_check.py` can read; a bare row is an `ORPHAN` to that tool and it is
right to say so.

```
| App | Item | Status | Owner | Blocked by | Next action | Sz |
|---|---|---|---|---|---|---|
| **Tooling** | **&#128993; `metamorphic_check.py` EXITS 1 on a rewording finding that appears in NO index row &mdash; the tool is cody&rsquo;s and so is the gap** <!-- QUEUE16-ITEM1-CODY-2026-10-05 --> | **MEASURED 2026-10-05 and re-measured 2026-10-06 at HEAD, and the tool is otherwise green: the file-transform family is CLEAN at 0 violated of 90 comparisons, `blind_lock()` is LOCKED at 24 fixture comparisons, and all SIX rules `dead_rule_sweep` called DEAD on 2026-09-29 are now exercised (`--tool metamorphic_check.py`: 6 of 6, 0 dead, CLEAN). The ONE finding is in the REWORDING family: `fmea/alf_facility_role_gate_live_probe.py`, relation `case`, 504 applicable and 1 violated. The verdict MOVED &mdash; `('_d_falsy_from_except', '_d_fixed_window')` gained `_d_checker_without_probe`. PRE-EXISTING, not introduced by the fixture work: `b70b040f` names it as &ldquo;its one existing finding&rdquo;** | cody (the tool); row routed to hank | **The ROW was blocked, never the diagnosis.** `docs/SAIRN-OPEN-WORK-INDEX.md` was cc&rsquo;s on 2026-10-05 and is **hank&rsquo;s** at HEAD on 2026-10-06 (taken deliberately, cc&rsquo;s claim expired). Authored and handed over in `docs/2026-10-06-cody-routed.md` rather than inserted, twice, to two different holders | **Reproduce in seconds, not 200: `python tools/metamorphic_check.py --prose` isolates the rewording family and exits 1.** Then decide between TWO hypotheses, which are opposite findings and must not be merged: **(a)** the `case` rewording is NOT meaning-preserving on this subject, so the RELATION is over-broad and the fix is to narrow or declare it, or **(b)** `_d_checker_without_probe` is case-sensitive where it should not be, so the FMEA DETECTOR has a real defect and the relation caught it. **cc holds `fmea/alf_facility_role_gate_live_probe.py` at HEAD and is working it directly, which is where (b) would be settled** | S |
```

### ⚠ WITHDRAWN 2026-10-06 — **DO NOT PASTE THAT ROW. THE FINDING NO LONGER REPRODUCES.**

Re-measured before handing it over, under `capture_exit` so the status comes
from a file:

```
python tools/metamorphic_check.py --prose     EXIT 0   (twice, 10 minutes apart)
  case   506 applicable, 0 violated
  CLEAN -- every applicable rewording held
```

**It was `case 504 applicable, 1 violated` this morning. It is 0 violated now.**

### AND I CHECKED THE OBVIOUS FALSE EXPLANATION FIRST

The FMEA subject is a **DECLARED SAMPLE — the first 12 tools alphabetically**
(`FMEA_SAMPLE = 12` in `_c_fmea()`). **Two tools were added to `tools/` today**
— my `capture_exit.py` and hank's `gate_parity_check.py` — so the obvious
reading is that the violating subject got pushed out of the sample and the
"CLEAN" is a subject that is no longer measured. **That would be the eighth
standing convention with my name on it.**

**It did not happen.** `alf_facility_role_gate_live_probe.py` is **index 9 of
12** — still sampled, still measured, and now holding. The applicable-unit count
rose 504 → 506, so the subject's own comment text changed.

**Cause NOT attributed.** No commit touches a `fmea/` path (that directory does
not exist — the label is a subject family, not a file), and the probe's last
commit is `26e72a90`, too old. Most likely cc's work on
`tools/alf_facility_role_gate_live_probe.py` or on `fmea_draft`'s detectors,
both of which she holds. **Recorded as unattributed rather than guessed.**

**ITEM 2 IS CLOSED, NOT BLOCKED, AND NOT BY ME.** The row was authored twice,
for two different holders, and is withdrawn before being inserted because the
thing it asserts is no longer true. **The check that caught it was re-running
the tool instead of quoting my own earlier measurement** — which is the rule
item 15(b) exists to make a habit.

---

## ITEM 8 — THE SELF-MUTATION SWEEP, AND THE PATTERN WAS ALREADY WRITTEN DOWN

**The shape, stated so it can be argued with:** *a tool whose VERDICT comes from
reading the state of a tree, or a set of changed paths, that the SAME TOOL
writes into — so its own write is inside the thing it measures.*

**Universe: 296 tracked `tools/*.py`.** Candidates carry all three signals — a
tree-state read, a write, and a before/after comparison. **26 do.** Of those I
read the **6 that are mine** plus the 4 structurally closest to the defect.

### THE SENTENCE WAS ALREADY IN THE REPO, IN A TOOL I DO NOT OWN

`tools/flaky_checker_quarantine.py:107` — its own comment:

> **THE LEDGER IS EXCLUDED FROM ITS OWN TREE HASH, and this is not a nicety.**
> Without it the tool cannot accumulate ANY evidence… **A tool whose own output
> invalidates its own input is its own subject. The fix is to take itself out of
> the measurement, not to loosen the filter.**

**That is my defect, diagnosed and fixed by somebody else before I wrote it**,
with the measurement attached ("three passes in a row each left exactly 3
observations"). My writer tier shipped the same shape anyway. **The pattern
being documented did not stop it, which is the finding worth more than the
list.**

### VERDICTS — the 6 mine, all read rather than routed

| tool | file:line | verdict |
|---|---|---|
| `dead_rule_sweep.py` | `tools/dead_rule_sweep.py:645` | **HAD THE SHAPE — FIXED** 2026-10-06, swept source excluded from the digest by name |
| `sairn_claim.py` | `tools/sairn_claim.py:1459` | **HAS THE SHAPE — ALREADY GUARDED.** `self_overlap()` exists for it, with the measurement in the comment at `:1447`; control `tests/claims/run_own_claim_overlap_probe.py` **exit 0** |
| `metamorphic_check.py` | `tools/metamorphic_check.py:249` | **NOT THE SHAPE** — compares checker STDOUT with the target path and dir substituted out (`<TARGET>`/`<DIR>`); fixtures live in a tempdir, not in the `ls-files` set |
| `dependency_graph.py` | `tools/dependency_graph.py:394` | **NOT THE SHAPE** — writes fixtures into `depgraph-fixtures-*` tempdirs; measures `api/` |
| `nhi_register.py` | `tools/nhi_register.py:1049` | **NOT THE SHAPE** — reads `sql/*.sql`, writes `docs/NHI-REGISTER.md`; disjoint sets |
| `run_all_tests.py` | `tools/run_all_tests.py:674` | **NOT THE SHAPE** — writes into the worktree's `.git` dir, outside the walked `tests/` tree |

### TWO MORE READ BECAUSE THEY ARE THE SAME FAMILY — both already guarded

| tool | file:line | verdict |
|---|---|---|
| `flaky_checker_quarantine.py` | `tools/flaky_checker_quarantine.py:107` | **ALREADY FIXED** — the quote above |
| `idempotence_double_run.py` | `tools/idempotence_double_run.py:44` | **ALREADY GUARDED** — *"are named and excluded rather than reported as broken"*; writes only inside its own scratch directory |
| `guard_ablation.py` | `tools/guard_ablation.py:175` | **NOT THE SHAPE** — `diff --name-only` is used to COPY dirty files into the worktree so the ablation sees the working tree, not as a verdict comparison |

### ROUTED — 10 candidates owned by another session, NOT read by me

Ownership derived from the claim-commit history (see the note below on why it
could not be read from the files). **These are routed on the SIGNAL, not on a
diagnosis — three of the nine I did read turned out not to be the shape at all,
so expect the same rate here.**

| tool | file:line | owner | last claimed |
|---|---|---|---|
| `checker_denominator.py` | `tools/checker_denominator.py:75` | **cc** | `ba0e26ab` |
| `fail_open_scan.py` | `tools/fail_open_scan.py:226` | **cc** | `701d3c88` |
| `report_only_checks.py` | `tools/report_only_checks.py:73` | **cc** | `e7322755` |
| `sabotage_control_check.py` | `tools/sabotage_control_check.py:604` | **cc** | `3074a08b` |
| `sairn_status.py` | `tools/sairn_status.py:279` | **cc** | `b1eac459` |
| `auth_header_name_sweep.py` | `tools/auth_header_name_sweep.py:114` | **fourth** | `ad82bf83` |
| `credential_purge_check.py` | `tools/credential_purge_check.py:172` | **fourth** | `7739487b` |
| `primitive_obsession_check.py` | `tools/primitive_obsession_check.py:248` | **fourth** | `dcc50055` |
| `push_retry.py` | `tools/push_retry.py:13` | **fourth** | `17442d94` |
| `tooling_inventory.py` | `tools/tooling_inventory.py:30` | **fourth** | `70aa2ed8` |

### AND SEVEN WITH NO OWNER AT ALL — unknown, not unowned

`first_article_check.py:559`, `fmea_draft.py:521`,
`git_discovery_anchoring_check.py:20`, `message_assertion_audit.py:234`,
`second_pass_coverage_scan.py:188`, `traceability_matrix.py:74`,
`write_path_fault_scan.py:151`.

**No `chore(claims)` commit in 2381 of them has ever named these files**, so
there is nobody to route to. They go to the open-work queue, which is hank's
file this hour.

### THE REASON OWNERSHIP HAD TO BE DERIVED AT ALL

**Only 13 of 296 tracked `tools/*.py` carry an `# OWNER:` line.** The other 283
have no owner recorded anywhere in the file, so every routing decision in this
batch was reconstructed from 2381 `chore(claims)` commit subjects by taking the
most recent session to name each file in a `FILES:` list.

**That derivation is a floor and it is weaker than a line in the file.** It
cannot see a tool somebody built without claiming it, it attributes to the last
*claimer* rather than the author, and `push_retry.py` resolves to **fourth**
while hank has also edited it. **An `# OWNER:` line in all 296 is the fix and it
belongs in `tooling_inventory.py`, which is fourth's** — see item 13.

---

## ITEM 9 — THE CLI ENTRY-POINT SWEEP, AND IT FOUND SEVEN SITES OF MINE IN A DIFFERENT TOOL

**Universe: 296 tracked `tools/*.py`. 105 carry a selftest arm. 99 of those
drive their own real entry point** — they spawn `sys.executable __file__` or
call `main(argv)` — **which is the shape `capture_exit.py` lacked.**

### SIX WHOSE SELFTEST NEVER DRIVES THE CLI — each driven once, exit code on its own line

```
python tools/accepted_risk_expiry_audit.py --selftest    EXIT=0   (cody)
python tools/ai_action_approval_audit.py  --selftest     EXIT=0   (UNKNOWN)
python tools/citation_drift_hook.py       --selftest     EXIT=0   (cc)
python tools/sabotage.py                  --selftest     EXIT=0   (UNKNOWN)
python tools/subprocess_decode_check.py   --selftest     EXIT=1   (UNKNOWN)
python tools/pycomments.py --help                        EXIT=0   (hank)
```

### SIX WITH NO RECOGNISED FLAG — and TWO of those were MY SCANNER being wrong

```
python tools/criticality_tier_check.py                   EXIT=0   (cody)
python tools/mutation_anchor_check.py                    EXIT=2   (cc)
python tools/stored_data_criticality_check.py            EXIT=0   (UNKNOWN)
python tools/tooling_inventory.py --check                EXIT=0   (fourth)
python tools/pycomments.py --help                        EXIT=0   (hank)
python tools/run_all_tests.py                            -- see below
```

- **`criticality_tier_check.py` is a FALSE POSITIVE, and the truth is stronger
  than a flag:** `run_fixtures()` is called **unconditionally at line 746 on
  every run**, and a failing lock returns 2 before anything real is judged. A
  lock that always runs beats a lock behind a flag nobody types.
- **`run_all_tests.py` is a FALSE POSITIVE too** — my regex matched the *words*
  `--selftest` inside strings describing **other** tools' selftests
  (`tools/run_all_tests.py:632`). It has no selftest of its own to skip.

**So 2 of the 6 I owned in that group were my scanner, not the tools.** Said
here because the same error rate applies to the four I am routing.

### THE REAL FINDING: `subprocess_decode_check.py` EXIT 1 NAMED SEVEN SITES OF MINE — FIXED

That tool is not a broken selftest; **`--selftest` runs its real check** and
exit 1 is findings. It reported **71 text-mode subprocess calls with no explicit
`encoding=`** on a machine whose locale default is cp1252. **Seven were mine:**

```
tools/dead_rule_sweep.py              534, 567, 583, 586, 657, 715
tests/run_dead_rule_sweep_probe.py    391
```

**Six of those I wrote TODAY**, in the owner-aware reap and the writer-tier
reset. All seven now carry `encoding='utf-8', errors='replace'`.

**Line 534 is the one that mattered:** the `tasklist` call inside `_pid_alive`,
which is what stops a concurrent sweep reaping a live sandbox. A decode error
there would have raised inside its `try`, which returns `True` — *could not
tell, do not reap* — **so it failed closed and the guard held.** Correct by
construction rather than by luck, and still wrong to leave.

```
python tools/subprocess_decode_check.py --selftest   BEFORE: 71 sites, EXIT=1
python tools/subprocess_decode_check.py --selftest   AFTER:  64 sites, EXIT=1
```

**Still exit 1, and that is honest:** 64 sites remain in other sessions' files.
Mine are gone — `grep` for `dead_rule_sweep` in the output returns nothing.

### ROUTED

| finding | file:line | owner |
|---|---|---|
| **64 remaining undecoded `text=True` subprocess calls** | the tool's own list | **UNKNOWN** for the tool; the sites span cc, hank and fourth files |
| `mutation_anchor_check.py` **EXIT 2** — *"could not read: 5 (NOT a pass)"* plus 2 anchors not matching exactly once | `tools/mutation_anchor_check.py` | **cc** |
| the 2 bad anchors it names | `tests/claims/run_fileset_matcher_sabotage_probe.py` | **UNKNOWN** — no claim has ever named it, though `tools/sairn_claim.py` is mine |
| 3 selftests that never drive their CLI and could not be attributed | `ai_action_approval_audit.py`, `sabotage.py`, `stored_data_criticality_check.py` | **UNKNOWN** |

**The `tests/claims/` anchor finding is the one to look at first** — the probe
lives beside controls for a tool I own, so it is probably mine in practice even
though no claim records it. **I did not touch it: `mutation_anchor_check.py` is
cc's and she is the one holding the verdict.**

---

## ITEM 11 — 28 OBLIGATIONS PULLED, ONE DISCHARGED ADVERSARIALLY, AND IT FOUND FOUR DEFECTS

### The list, and the assignment rule that defines it

`docs/tier-a-reviews.json` holds **234 records: 194 reviewed, 40 open.** The
file's own `_how_it_works` sets the rule:

> The gate … **DENIES any record whose reviewer is its own author.** Recording
> the obligation is the author's job; **discharging it is somebody else's and
> cannot be faked by the author.**

So "owed to me" means **open records I did not author** — I am an eligible
reviewer for those and for no others. **28 of the 40.** The other 12 are mine by
authorship and are owed *by* the other sessions *to* me.

| author | open records I can review |
|---|---|
| hank | 11 |
| fourth | 8 |
| cc | 7 |
| hover2 | 2 |
| **total** | **28** |

**`reviewer_session` is empty on all 40**, so nothing is pre-assigned to me by
name; eligibility is what the rule produces.

### DISCHARGED ADVERSARIALLY: hank, `2026-10-05T21:33:08Z`, `citation_line_drift_check.py`, `sd_comms`

**The verdict under review**, driven at HEAD
(`--app stonedesk.html --prefix sd_`, exit 1):

```
ANCHORED-VIA sd_comms  :10582   load() at :10526 reaches it in 2 hop(s)
ANCHORED-VIA sd_comms  :10618   load() at :10526 reaches it in 2 hop(s)
ANCHORED-VIA sd_comms  :10649   load() at :10526 reaches it in 2 hop(s)
DRIFTED      sd_comms  :10483 -> :10527  offset +44
```

**Three of the four rest entirely on the hop graph, and
`tests/run_citation_line_drift_probe.py` — 22 arms, exit 0, a good probe — has
no arm for it.** Its G2/G3 pair covers the wrong-file attack, A1/A2 the
declaration spans, E2/F2/F3 the drift arrow. **The hop graph is the uncovered
half carrying most of this resource's answer**, so that is where the attack
went.

**New control: `tests/run_citation_anchor_hop_sabotage.py`, exit 1, 4 findings.**

| arm | attack point | result |
|---|---|---|
| **S3** | PAIRED POSITIVE — a real one-hop chain must anchor | **ok** |
| **S3b** | a definition below its call site — `_nearest_def` searches backward only | **ok, LIMIT not finding** — it loses anchors, cannot invent one, **fails safe** |
| **S1** | a `//` comment naming the resource in a body | **FAIL — `via`** |
| **S1b** | a string literal naming it | **FAIL — `via`** |
| **S2** | the flat 60-line window spilling into the next function | **FAIL — credits `shortFn()` for its neighbour's write** |
| **S0** | the CITED LINE itself being a comment | **FAIL — reads as `direct`, "the cited line names the resource"** |

**Cause, one line of code:** `_direct_line()` is a **substring test over raw
lines**, and `_body_lines()` is a **flat 60-line window**, not a braced body —
its own docstring says so deliberately. Prose about a resource therefore reads
as access to it, and a short function is credited with its neighbour's write.

### AND THE REAL `sd_comms` VERDICT IS CORRECT TODAY BUT UNPROTECTED

I checked whether the live rows actually rest on a comment. **They do not:**

```
:10526  CODE     function load(){ ... localStorage.getItem('sd_comms') ... }
:10527  CODE     function save(d){return st('sd_comms',d);}
:10531  COMMENT  // sd_comms sat in SD_SYNCED, which reads as "this is backed up" ...
```

**So the three ANCHORED-VIA rows are sound on their merits — and they would
survive the write being deleted**, because a comment naming `sd_comms` sits
five lines below it inside the same window. **The evidence would not notice the
thing it exists to notice.** That is the eighth standing convention arriving in
somebody else's tool.

**VERDICT: the obligation CANNOT be discharged as sound.** Not because the
rows are wrong — they are right — but because **the evidence class cannot tell
a right row from a comment.** Routed to hank with the control, the four
reproductions and the `:10531` line that makes it live rather than theoretical.

### AND THE REMAINING 27 ARE NOT DISCHARGED

**Pulled, listed, and not reviewed.** `docs/tier-a-reviews.json` is **cc's** at
HEAD, so even a completed review cannot be written as a record. **Discharged
against owed: 0 written, 1 reviewed, 27 untouched** — and the honest reason the
figure is 1 and not 28 is that an adversarial discharge with a sabotage control
per attack point costs what the one above cost, not less.

---

## ITEM 12 — THE `db/schema_snapshot.json` OBLIGATION: OPEN, AND REVIEWING IT NOW WOULD REVIEW A HALF-STATE

| field | value |
|---|---|
| author | **fourth** |
| opened | `2026-10-05T21:25:19Z` |
| status | **open** |
| files | `db/schema_snapshot.json` |
| resources | **246** |

Its own `what`: *the file was replaced with the REAL Supabase output Michael ran
2026-10-05 15:10:30 UTC, pasted verbatim: 442 keys, 439 tables, 3560 columns.*

**The `_constraints` key is NOT present.** Measured at HEAD — the top-level keys
are `_anon_grant_baseline_2026_08_26`, `_anon_nontable_baseline_2026_08_26`,
`_generated_at` and the table names. **No `_constraints`, no `constraints`.**

**I did not merge it and will not — that is assigned to fourth.**

**Does it satisfy my obligation?** Not yet, and the question is the wrong way
round: the obligation is **fourth's to have reviewed**, and I am an eligible
reviewer. **Reviewing it now would review a half-state** — a snapshot missing
the constraints half, where the missing half is the part that says what the
database *refuses*. **When `_constraints` lands, the review becomes possible and
this is the record to re-read.** Left open deliberately.

---

## ITEM 13 — THERE IS NOTHING TO REGISTER. EVERY TOOL IS ALREADY DESCRIBED

| | count |
|---|---|
| tracked files under `tools/` | **324** |
| described in `tooling_inventory.PURPOSES` | 234 |
| described in `report_only_checks.REGISTRY` | 75 |
| **described by NEITHER** | **15** |

**And all 15 are DATA, not tools** — `activity_cadence.json`,
`fail_open_accepted.json`, `gate_column_accepted.json`,
`idempotency_triage.json`, `ownership_evidence_drift.json`,
`preauth_oracle_accepted.json`, `primitive_obsession_baseline.json`,
`production_activity_snapshot.json`, `public_endpoint_declarations.json`,
`reachability_exemptions.json`, `removal_path_baseline.json`,
`truthy_sum_baseline.json`, `verify-session-token-app-scope.yml`,
`waf_rules_expected.json`, `write_path_hazard_baseline.json`.

**Zero executable tools are unregistered.** The generator refuses to run with an
undescribed tool, which is why — it has been holding this invariant the whole
time.

### The two pending tools are NOT in HEAD, so the item stays OPEN

```
tools/gate_parity_check.py           ABSENT from HEAD   (hank, claimed)
tools/red_suite_register_check.py    ABSENT from HEAD   (fourth, claimed)
```

Both are named in live claims and neither has landed. **Nothing to register and
nothing to wait on inside this batch — item 13 stays open on those two.**

### The `# OWNER:` HALF IS THE REAL GAP, AND IT IS 283 FILES

**Only 13 of 296 tracked `tools/*.py` carry an `# OWNER:` line.** Adding one to
each is the fix that would have made every routing decision in this batch a
read instead of a reconstruction from 2381 claim commits. **It is not a
`tooling_inventory` entry — it is 283 file headers**, and the generator that
would enforce it is fourth's. **Routed to fourth as a proposal, with the
derivation this batch had to use instead.**

---

## ITEM 3 — 49 RULES DEAD TO THEIR OWN EVIDENCE, AND **NONE OF THEM IS MINE**

Measured at commit `8f204050`, 2026-10-06, `python tools/dead_rule_sweep.py`
under `capture_exit` — **status file says `EXIT 2`**, 152 tools, 540 rules.

**DIAGNOSED: 0. FIXED: 0. ROUTED: 49.** The item asked me to diagnose every one
in my own tools and there are **zero in my own tools** — not a dodge, a result.
`metamorphic_check.py`'s six were fixed 2026-10-05 and hold; `gap_ledger.py` is
7 of 7; `dead_rule_sweep.py`, `capture_exit.py` and `gate1_verify.py` compile no
module-level rule at all; `sairn_claim.py`, `run_all_tests.py`,
`nhi_register.py` and `dependency_graph.py` appear nowhere in the 49.

| owner | tools | rules |
|---|---|---|
| **cc** | 5 | **9** |
| **hank** | 4 | **10** |
| **UNKNOWN** | 16 | **30** |
| | | **49** |

### cc — 9 rule(s)

```
copy_exactly_gate.py                 EXEMPT_RE              tools/copy_exactly_gate.py:170
copy_exactly_gate.py                 NONE_RE                tools/copy_exactly_gate.py:188
copy_exactly_gate.py                 TRAILER_RE             tools/copy_exactly_gate.py:187
exit_status_attributable.py          SEPARATORS             tools/exit_status_attributable.py:68
report_only_checks.py                COUNT_RE               tools/report_only_checks.py:136
sabotage_control_check.py            NEVER_A_FILE           tools/sabotage_control_check.py:267
sabotage_control_check.py            STRINGISH              tools/sabotage_control_check.py:294
tier_a_review_gate.py                _PROSE                 tools/tier_a_review_gate.py:695
tier_a_review_gate.py                _SQL_GRANT_RE          tools/tier_a_review_gate.py:1583
```

### hank — 10 rule(s)

```
dispatch_state.py                    STRIKE                 tools/dispatch_state.py:87
gate_parity_check.py                 ACTION_IN_RE           tools/gate_parity_check.py:197
gate_parity_check.py                 ASSIGN_RE              tools/gate_parity_check.py:114
gate_parity_check.py                 COMMENT_LINE_RE        tools/gate_parity_check.py:263
gate_parity_check.py                 DATA_200_RE            tools/gate_parity_check.py:118
gate_parity_check.py                 ROLE_RE                tools/gate_parity_check.py:111
gate_parity_check.py                 SELECT_RE              tools/gate_parity_check.py:117
register_feed_gate.py                REST_PATH              tools/register_feed_gate.py:420
register_feed_gate.py                TIER_A_ROW             tools/register_feed_gate.py:418
unreachable_failure_path_scan.py     DIRECT_CALL_RE         tools/unreachable_failure_path_scan.py:168
```

### UNKNOWN — 30 rule(s)

```
adversarial_prompt_corpus.py         SYSTEM_SITE            tools/adversarial_prompt_corpus.py:251
adversarial_prompt_corpus.py         _IDENT                 tools/adversarial_prompt_corpus.py:287
ai_prompt_refusal_check.py           OWN_RULES_RE           tools/ai_prompt_refusal_check.py:227
benford_check.py                     FIELD_RE               tools/benford_check.py:130
csv_formula_injection_check.py       GUARD_SPLIT            tools/csv_formula_injection_check.py:87
hedge_carry_check.py                 RESOLVED               tools/hedge_carry_check.py:143
hedge_carry_check.py                 _SENT_END              tools/hedge_carry_check.py:155
idempotence_double_run.py            SIDE_EFFECT            tools/idempotence_double_run.py:136
idempotence_double_run.py            WRITES                 tools/idempotence_double_run.py:70
idempotency_check.py                 FILTER_COL             tools/idempotency_check.py:130
idempotency_check.py                 KEY_SHAPE              tools/idempotency_check.py:125
idempotency_check.py                 MUTATING               tools/idempotency_check.py:131
known_red_check.py                   TOTAL_RE               tools/known_red_check.py:74
live_probe_declaration_check.py      BLOCK_C                tools/live_probe_declaration_check.py:123
live_probe_declaration_check.py      LINE_C                 tools/live_probe_declaration_check.py:124
live_probe_declaration_check.py      TRIPLE                 tools/live_probe_declaration_check.py:122
push_failure_reason.py               COULD_NOT              tools/push_failure_reason.py:64
register_freshness_propose.py        DRIFT_RE               tools/register_freshness_propose.py:69
retry_backoff_check.py               BREAKER_NEEDS_EXIT     tools/retry_backoff_check.py:125
retry_backoff_check.py               EXIT_STMT              tools/retry_backoff_check.py:126
retry_backoff_check.py               _KEYWORD_BEFORE_REGEX  tools/retry_backoff_check.py:151
retry_policy_audit.py                BREAKER                tools/retry_policy_audit.py:103
retry_policy_audit.py                DEADLINE               tools/retry_policy_audit.py:236
retry_policy_audit.py                IDENT                  tools/retry_policy_audit.py:107
retry_policy_audit.py                RETRY_BOUND            tools/retry_policy_audit.py:237
shape_search.py                      JS_FUNC                tools/shape_search.py:289
suite_override_consistency.py        APP_RX                 tools/suite_override_consistency.py:60
suite_override_consistency.py        ENV_RX                 tools/suite_override_consistency.py:58
tier_sentence_gate.py                CORRECTED              tools/tier_sentence_gate.py:147
tier_sentence_gate.py                QUOTED                 tools/tier_sentence_gate.py:144
```

**30 OF 49 HAVE NO OWNER ANYWHERE.** No `chore(claims)` commit in 2381 has named
their file in a `FILES:` list, and only 13 of 296 tools carry an `# OWNER:`
line. **They cannot be routed to a session; they go to the open-work queue**,
which is hank's file this hour.

### WHAT A `DEAD` VERDICT DOES AND DOES NOT MEAN, because 49 is a big number

It does **not** mean the rule is wrong, or unused on real data. It means
**nothing the tool ships as evidence would notice the rule vanishing** — it
could be deleted, mistyped, or shipped with a literal backspace and every green
light stays green, which is the 2026-09-29 defect this sweep was built from.

**The repair is one of two and they are not the same answer:** add a fixture
that exercises the rule when it is load-bearing, or register it as a **NAMED
LIMIT** when it is defensive or covers a shape that no longer occurs. **A named
limit is honest; an unexercised rule presented as a criterion is not.**

**`gate_parity_check.py` arrives with 6 of its 9**, which is worth saying to
hank plainly: the tool landed today, it is a good tool, and more than half its
module-level rules are invisible to its own `--selftest`.
