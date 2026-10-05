# Queue 15 — inventory, and the whole batch shows up in one number with nothing left over

**2026-10-05 (Cody).** Written after a context reset, so **every claim below was
re-derived against the repo rather than carried across** — including the ones
the pre-reset summary stated as finished. Two of those statements were wrong in
the same direction and are corrected in **WHAT THE RESET GOT WRONG** at the end.

**Do not quote any figure from this file. Run the command named beside it.**

---

## LANDED

| # | what | where |
|---|---|---|
| 1 | Nine Tier A review obligations discharged, one of them correcting a false escalation of mine | `c0f3a821` |
| 2 | The dependabot HIGH triaged — three advisories, one closed, two raised as a decision | `d788ee83`, `docs/2026-10-05-dependabot-high-triage.md` |
| 3 | Michael's SQL runbook: 20 files, a confirm file, and a verifier that asks the APP | `d8bc39e4`, `docs/2026-10-05-michael-sql-runbook.md` |
| 4 | `append_only_read_order_scan.py` grant pattern no longer requires `public.` | `cef3ec2d` |
| 5 | Two sweeps anchored to the REPO instead of the cwd | `cef3ec2d` |
| 6 | Six metamorphic rules dead to my own lock get a fixture each — and the fixtures found a seventh defect | `b70b040f` |
| 7 | `gap_ledger.py` and `gate1_verify.py` registered, closing the under-counted sweep universe | `31a1d4fc` |

---

## THE ONE MEASUREMENT THAT CARRIES THE WHOLE BATCH

`python tools/dead_rule_sweep.py` — re-run at HEAD for this file. The previous
batch's run is in `docs/2026-10-05-cody-queue14-inventory.md` and is the
baseline below.

| | queue14 | queue15 | delta |
|---|---|---|---|
| registered tools | 73 | **75** | +2 |
| module-level rules — THE UNIVERSE | 162 | **169** | **+7** |
| could be ablated against SOME evidence | 140 | **147** | +7 |
| against evidence the tool SHIPS | 75 | **82** | +7 |
| &nbsp;&nbsp;of those, exercised | 67 | **80** | **+13** |
| &nbsp;&nbsp;of those, **DEAD** | **8** | **2** | **−6** |
| against the REAL RUN only | 65 | 65 | 0 |
| COULD NOT RUN | 22 | 22 | 0 |
| FINDINGS | 36 | **30** | −6 |

**EVERY MOVED NUMBER IS ACCOUNTED FOR BY A NAMED CHANGE IN THIS BATCH, AND
NOTHING ELSE MOVED.** That is the reason to print the table rather than the
verdict:

- **+7 rules** are `gap_ledger.py`'s seven, and **all seven**. `gate1_verify.py`
  was registered in the same commit and contributes **ZERO** — it compiles no
  module-level rules. Measured separately: `dead_rule_sweep --tool
  gap_ledger.py` reads *7 module-level compiled rules, 7 of 7, CLEAN*;
  `--tool gate1_verify.py` reads *0 module-level compiled rules*.
- **+13 exercised** is those 7 plus the **6** metamorphic rules that were dead
  and now carry fixtures. `--tool metamorphic_check.py`: *6 of 6 rules, 6
  exercised and 0 dead, CLEAN.*
- **−6 DEAD** is the same six. The **2 that remain** are
  `register_feed_gate.py`'s `TIER_A_ROW` and `REST_PATH` — **fourth's tool, not
  mine**, and hank currently holds that file under a live claim.
- **22 COULD NOT RUN did not move**, which is the right outcome: all 22 belong
  to tools that WRITE when run, a tier this batch did not touch.

**The arithmetic closes in both directions** — 80 + 2 = 82; 82 + 65 = 147;
147 + 22 = 169 — which is what makes "nothing else moved" a measurement instead
of an impression.

---

## ITEM 4 ANSWERED PRECISELY: THE UNIVERSE IS 169 OF 169. COVERAGE IS 147 OF 169. THEY ARE DIFFERENT NUMBERS

The question asked of this batch was whether registering the two tools makes the
sweep's universe **169 of 169**. It does, and the distinction is worth stating
because the sweep prints both figures and they are easy to merge:

- **THE UNIVERSE IS COMPLETE AT 169.** Queue 14 recorded the platform figure as
  "162 rules, 8 dead" and flagged that it was really **162 of 169** — gap_ledger
  was absent from `report_only_checks.REGISTRY`, which is the only list the
  sweep derives its universe from, so its 7 rules were counted by nothing.
  Those 7 are now counted. **The exclusion is closed.**
- **COVERAGE WITHIN THAT UNIVERSE IS 147 OF 169, AND THAT IS NOT A FAILURE —
  IT IS THE TOOL REFUSING.** The 22 uncleared rules all belong to tools that
  write when run, so the real run is not safe evidence for them. The sweep says
  so by name, exits **2**, and prints *"The findings above are a FLOOR, not a
  total -- part of this run did not happen."* A 147/169 that printed as a pass
  would be the fail-open this platform names in PR §1.11.

### WHAT REGISTERING TWO TOOLS DID NOT FIX, AND WILL NOT

**The mechanism that produced the exclusion is untouched.** The universe is
still derived from a **hand-maintained list**: `report_only_checks.REGISTRY`
holds **75 entries**, against **293 `.py` files in `tools/`**.

**293 IS NOT THE CORRECT DENOMINATOR AND I AM NOT GOING TO PRETEND IT IS** —
most of those 293 are gates, drivers, probes and generators that this registry
was never meant to hold. **But I do not have the correct denominator, and
neither does the sweep**, and that is exactly the gap: *a universe derived from
a hand-maintained list reports confidently about the part of the fleet that list
happens to name, and cannot say what is outside it.* Registering two names
closed two names.

**The shape to notice is that the exclusion was never a DECISION.** Nothing
refused `gap_ledger.py`. It was written while its registry was under somebody
else's claim, the two halves of the promotion happened hours apart, and the
sweep had no way to report the hole. That note is in `report_only_checks.py`
above both entries so it is not re-learned.

---

## TOOL-BY-TOOL: WHAT IS GREEN, AND THE TWO THINGS THAT ARE NOT

Every tool run once at HEAD, **each measured alone** with its exit status read
on its own line after a redirect — because the status of `tool > out; echo $?`
piped anywhere at all is the status of the pipe, which is the misreading that
put a false `EXITS 2` accusation into a standing document on 2026-10-04.

| tool | exit | verdict |
|---|---|---|
| `gate1_verify.py --fixtures` | **0** | GREEN — 7 verdict fixtures + the derived table count, lock holds |
| `sairn_dead_function_sweep.py` | **0** | GREEN — **22 files swept from a non-root cwd** |
| `sairn_reachability_probe.py` | **0** | GREEN — **22 files probed from a non-root cwd** |
| `append_only_read_order_scan.py` | **0** | GREEN — 402 grant lines read, population 25 |
| `dead_rule_sweep.py --tool gap_ledger.py` | **0** | GREEN — 7 of 7, CLEAN |
| `dead_rule_sweep.py --tool gate1_verify.py` | **0** | GREEN — 0 rules, vacuously CLEAN |
| `dead_rule_sweep.py --tool metamorphic_check.py` | **0** | GREEN — 6 of 6, CLEAN |
| `metamorphic_check.py` | **1** | **NOT GREEN — 1 finding.** See below |
| `dead_rule_sweep.py` (full) | **2** | **NOT GREEN — 22 COULD NOT RUN.** See above |

**THE TWO ANCHORING FIXES ARE PROVEN BY THE 22, NOT BY THE EXIT CODE.** Both
sweeps exited **0 before the fix too** — over an **empty corpus**, from any cwd
that was not the repo root. The number that distinguishes a working sweep from
that is the file count, which is why both now print it, and why this table
records *22 files* rather than *exit 0*.

### `metamorphic_check.py` EXITS 1 AND THAT IS ITS NORMAL STATE, NOT A REGRESSION

```
relations violated  : 0      (90 comparisons, 6 checkers x 15)
blind lock          : LOCKED (24 fixture comparisons)
rewording           : 2063 applicable of 2565, 1 violated
FINDINGS (1):
  ! fmea/alf_facility_role_gate_live_probe.py, rewording case:
    the verdict MOVED
```

This is the **one pre-existing finding** `b70b040f` names explicitly. All six
previously-dead rules are exercised, the metamorphic family is clean at 0 of 90,
and the single finding is in the rewording family and predates this batch.

**IT IS NOT LOGGED AS AN OPEN-WORK ROW AND I DID NOT ADD ONE.** Checked:
`alf_facility_role_gate_live_probe` and `rewording case` both appear **0 times**
in `docs/SAIRN-OPEN-WORK-INDEX.md`. The tool is mine, so this is my gap, not a
routing one. **I am surfacing it rather than editing the index**, which cc holds
under a live claim this hour; a row added by splitting on `|` is PR §2.1's named
defect and a row added in a contested file is worse. **NEXT ACTION: a row for
the rewording finding, by whoever next holds the index.**

**AND THE EXIT CODE NEARLY WENT INTO THIS FILE AS A 0.** Both long runs were
backgrounded, and the harness reported *"completed (exit code 0)"* for each —
the status of the trailing `echo`, not the tool. The real codes, read out of the
captured stdout, were **1** and **2**. The attribution hook fired on nearly
every command in this session and it was right to.

---

## MICHAEL'S ACTION, STILL OWED — AND NOTHING IN THIS BATCH MOVED IT

**`docs/2026-10-05-michael-sql-runbook.md` is ready and has NOT been run.** The
20 SQL files exist in `sql/`, every one is idempotent, the paste order, the
confirm queries and the after-check are written, and **none of it needs a
decision.** It needs a human at a SQL editor.

The recorded pre-run baseline, driven live and signed in on all six demo
licences, is `PRESENT : 0 / MISSING : 26`, and **re-running
`python tools/gate1_verify.py` after the pastes is the entire after-check.**

**I did not re-drive that baseline in this session and it is not re-verified
here.** The `--fixtures` arm is green, which proves the verdict logic, **not
that the live state is still 0/26** — a different question, answerable only by
signing in again. Treating the fixture pass as a live confirmation would be the
eighth discipline exactly: *nothing announces the day a check stops testing
anything.*

**And the one thing to carry into the paste session:** the catalogue and the app
can disagree. A `CREATE TABLE` that lands while its `GRANT` block does not
leaves a table `information_schema` reports happily and that `api/sd-data.js`
answers **503 NOT_PROVISIONED** on — byte-identical to a table that was never
created. `sql/zz_confirm_*.sql` asks Postgres; `gate1_verify.py` asks the app.
**Running one is not running the other.**

---

## WHAT THE RESET GOT WRONG, IN THE DIRECTION THAT MATTERS

The pre-reset summary listed the batch as committed. **It was committed and
NOT pushed** — `main` was **ahead 1, behind 4** when this session opened, and
the unpushed commit was the registry one, the item the whole measurement above
depends on. A commit that is not pushed is invisible to every other clone, which
is PR §2.2 about claims and is just as true about work.

**Two statements that would have been reported as green and are not:**

1. *"metamorphic_check.py ... confirm each is green"* — it exits **1** with one
   finding. Its six fixed rules are green; **the tool is not.**
2. *"Re-run dead_rule_sweep.py and confirm the universe is now 169/169"* — the
   **universe** is 169; the sweep's own coverage line reads **147 of 169**, and
   reporting the second as the first would have published a 22-rule hole as a
   pass.

Both are the same error shape: **a summary of a measurement, re-read later as
the measurement.** The fix is not better summaries, it is re-running the
command, which is why no figure in this file is quotable from it.

---

## WHAT THIS DOES NOT ESTABLISH

- **That the 20 SQL files work.** They have never been run. The baseline says
  all 26 tables are absent from the app's side; nothing has changed that.
- **That the sweep's universe is now complete in any sense beyond its own
  list.** 169 is every rule in 75 registered tools. It is not every rule on the
  platform, and the sweep still cannot say how far short it falls.
- **That the 2 remaining DEAD rules are the platform's last.** They are the last
  in the 147 that could be cleared. The 22 that could not run are a FLOOR, and
  the sweep says so itself.
- **That the rewording finding is benign.** It has not been diagnosed — only
  confirmed as pre-existing and reported as unlogged.
