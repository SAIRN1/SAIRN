# Queue 16 — inventory and methodology: two hidden universes, three defects of my own, and one premise that was false

**2026-10-05/06 (Cody).** Eight items. **Do not quote a figure from this file —
run the command printed beside it.** Three of the figures below exist precisely
because a previous document of mine was quoted instead of re-run.

---

## LANDED

| # | item | where | result |
|---|---|---|---|
| 1 | The open-work row for `metamorphic_check` exit 1 | `docs/2026-10-05-cody-routed-to-cc.md` | **authored, not inserted** — cc holds the index |
| 2 | Sweep docs/ for "green" claims about the two tools | 3 dated corrections | **nothing claimed green; three reported a run with NO exit code** |
| 3 | Replace the hand-maintained sweep universe with a glob | `tools/dead_rule_sweep.py`, `docs/2026-10-05-dead-rule-universe-delta.md` | **169 of 521 rules was the real coverage, not 162 of 169** |
| 4 | Make the 22 COULD NOT RUN tools runnable | the writer tier | **22 → 0, and 5 real DEAD rules were being hidden** |
| 5 | The dependabot HIGH, decided | `docs/2026-10-05-dependabot-high-triage.md` addendum | **the vulnerable primitive is NOT on our path — measured** |
| 6 | Re-run after hank's `register_feed_gate` cp1252 fix | — | **the fix IS in origin/main and DEAD is still 2, not 0** |
| 7 | A capture-exit wrapper, registered | `tools/capture_exit.py` | built, locked, and **its own `--read` raised on first use** |
| 8 | The methodology lesson | below | written, and routed for promotion |

---

## ITEM 3 — THE UNIVERSE WAS 169 OF 521, NOT 162 OF 169

`python tools/dead_rule_sweep.py --universe`

| | files | rules |
|---|---|---|
| tracked `tools/*.py` | **295** | &mdash; |
| compile a module-level rule — **THE UNIVERSE** | **150** | **521** |
| &nbsp;&nbsp;IN the report-only registry — *the old universe* | 45 | **169** |
| &nbsp;&nbsp;**OUTSIDE it** — *invisible until this batch* | **105** | **352** |
| compile none — nothing to ablate, derived per file | 145 | 0 |
| **exempt by declaration** | **0** | 0 |

**Yesterday I found this hole one name at a time** — `gap_ledger.py` was absent,
the figure was corrected to "162 of 169", two entries were added, and the fix
was pushed. **That closed two names and left the mechanism.** The glob says the
hole was **352 rules in 105 files**.

**The declared exemption list is EMPTY and that is measured.** The one entry I
wrote — `dead_rule_sweep.py` itself, *"neutralising its own rule mid-run
measures the harness, not the subject"* — is a true sentence and a useless
exemption: that file compiles no module-level rule, so the mechanical branch
already excluded it. The `STALE_EXEMPT` check I wrote in the same change refused
the run and named it, **on its author, within minutes.**

---

## ITEM 4 — THE WRITER TIER, AND MY FIRST VERSION REPORTED ALL 22 AS GREEN

The item asked for a scratch copy "so write-when-run side effects can't touch
the repo." **That was already true** — every run has happened in a throwaway
worktree since 2026-09-30. The tool's own comment said the surviving problem was
**attribution**, not safety, and it was right: a tool that regenerates its own
subject compares its output against a corpus it has just rewritten.

So the fix is **resetting the corpus between runs**, and three things are proved
on each tool *before* any ablation counts: the reset really restores, two
identical baseline runs agree on exit code **and** stdout **and** the bytes of
every file written, and the clone's own porcelain state is unchanged.

### The first measured output was "22 of 22 cleared, 22 of 22 exercised"

**That is exactly what a tier which can only say "exercised" produces.** It was
not believed, because the probe arm written in the same change — a hand-built
writer carrying `USED` and `UNUSED`, where `UNUSED` is compiled, documented and
never read — came back **exercised** for `UNUSED` and failed.

**The cause:** the comparison digest covered every dirty path in the sandbox,
and the ablation writes the neutralised source *into* the sandbox. So the swept
tool's own file was dirty on every patched run and on no baseline run. **The
signature differed every time because of the MUTATION rather than its EFFECT.**

### The real answer — 17 exercised, 5 DEAD

| tool | rules | exercised | DEAD |
|---|---|---|---|
| `tooling_inventory.py` | 2 | 2 | 0 |
| `traceability_matrix.py` | 3 | 3 | 0 |
| `master_plan.py` | 2 | 2 | 0 |
| `criticality_tier_check.py` | 5 | 4 | **1** — `_TAIL_OK` |
| `defect_register.py` | 2 | 0 | **2** — `EXTERNAL_RE`, `HOVER_SESSION_SHAPE` |
| `hover_separation_audit.py` | 8 | 6 | **2** — `AUDITOR_SESSION_RE`, `SELF_MARKER` |
| **total** | **22** | **17** | **5** |

**The blanket refusal had been hiding five real dead rules, and my pre-fix
version would have reported zero.** A tier that clears a whole category and
finds nothing in it is the outcome to distrust.

**Every fixture writes nothing to stdout, deliberately.** If stdout carried the
signal the tier could pass its arms while the file comparison did nothing — and
a generator rewriting a whole document without changing a byte of stdout is the
normal case here, not the edge case.

---

## ITEM 6 — THE PREMISE WAS FALSE, AND THE FIX IS GENUINELY LANDED

The item said: when hank's `register_feed_gate.py` cp1252 fix is in
`origin/main`, confirm DEAD **2 → 0**.

**The fix is in** — `cd19bd7f`, two `sys.std*.reconfigure(encoding='utf-8')`
lines present at HEAD. **DEAD is still 2.**

```
python tools/dead_rule_sweep.py --tool register_feed_gate.py   -> exit 1
  5 module-level rules, 3 exercised and 2 dead
  ! TIER_A_ROW  DEAD TO ITS OWN EVIDENCE
  ! REST_PATH   DEAD TO ITS OWN EVIDENCE
```

**They are unrelated defects that happened to share a file.** The cp1252 fix
stops the gate dying on a console that cannot encode its own output. `TIER_A_ROW`
and `REST_PATH` are dead to the tool's **own self-check** — neutralise either
and nothing the tool ships as evidence goes red. **An encoding fix cannot move
an evidence verdict**, and expecting it to was a reasonable guess from a commit
subject rather than from the finding.

**Not mine to fix:** `register_feed_gate.py` is fourth's tool, and hank has been
holding the file. Reported, unchanged.

---

## ITEM 5 — UNDETERMINED BECAME A VERDICT, AND IT DID NOT NEED AN INSTALL

Full account in `docs/2026-10-05-dependabot-high-triage.md`. The short form:

`firebase-admin@12.7.0` calls node-forge in **exactly one place** —
`lib/app/credential-internal.js:150`, `forge.pki.privateKeyFromPem(...)`, a PEM
**parser** whose return value is discarded. The advisory is about RSA PKCS#1 v1.5
signature **verification**. **Nothing on our path reaches it.**

**It worked because the packages were already on disk outside the clone** at the
lockfile's exact versions — firebase-admin 12.7.0 and node-forge 1.4.0 — which
is the only reason the reading counts.

**So the two-major upgrade is not indicated**, and it carries a four-point
re-check trigger whose first point is that the whole basis is *exactly one call
site*. **`npm install` is unavailable in this session, so 14.5.0 was never
resolved or tested — and the order matters: the measurement is what makes the
upgrade unnecessary, not the inability to perform it.** Had it come out the other
way this item would be BLOCKED, not closed.

---

## METHODOLOGY (ITEM 8) — A GREEN CLAIM MUST CITE A CAPTURED EXIT CODE

**The rule, in one sentence:** *a standing document may not call a tool green
without an exit code captured from the run itself; a backgrounded run's
"completed (exit code 0)" is the status of whatever ran LAST, not of the tool.*

### What happened

The repo's own advice for an attributable status is correct, and
`tools/exit_status_attributable.py` is right to give it:

```
python tools/some_check.py > /tmp/out 2>&1
echo "EXIT=$?"
```

**In the foreground it is completely correct.** Backgrounded, the caller
receives the status of the **compound command**, whose last element is the
`echo` — so it reports **0** no matter what the tool did:

| run | harness notification | real code |
|---|---|---|
| `metamorphic_check.py` | completed (exit code 0) | **1** |
| `dead_rule_sweep.py` | completed (exit code 0) | **2** |

**Two not-green tools were one step from entering a standing document as green.**
Nothing was hidden — both real numbers sat in the captured stdout. **What was
wrong was the number that looked authoritative.**

### Why a habit cannot fix it, and a file can

The backgrounding decision is made **after** the command text is written, by
something other than the person writing it. The same text is safe in one context
and misleading in the other, so no care at writing time can tell which it will
be. `tools/exit_status_attributable.py` reasons about command TEXT — the right
place for it — and cannot see the layer that makes that text wrong.

`tools/capture_exit.py` records the status in a **named file**, written by the
process that actually waited on the child:

```
python tools/capture_exit.py --status run.status -- python tools/some_check.py
python tools/capture_exit.py --read run.status     # exits WITH that code
```

### The third state is the hard part, one level down

A status file that does not exist yet and one saying `EXIT 0` are the same bytes
to a careless reader: nothing, then zero. **That is PR §1.11 again.** So the file
is written twice — `RUNNING <pid>` before the child starts, `EXIT <code>` after
it is reaped, `COULD_NOT_RUN` when it never started — and `--read` exits **2,
never 0**, on ABSENT / RUNNING / UNREADABLE.

### And the corollary this batch paid for twice

**Reporting a run WITHOUT its exit code is the same defect arriving quietly.**
Three of my own documents did it — `queue13`, `queue14`,
`2026-09-29-dead-rules` — printing the sweep's figures with no status anywhere
in the file. The sweep exits **2** whenever rules stay uncleared, so none of
those runs was ever green and nothing said so. All three now carry a dated
correction, and **the exit code of a past run is not recoverable and was not
invented** — each says so and records a re-run instead.

**ROUTED, NOT PROMOTED.** This belongs in the standing conventions, not in a
dated inventory, because a lesson in a dated file is the eighth convention
waiting to happen. `docs/METHODOLOGY.md` is **fourth's** this hour and
`docs/2026-09-13-cross-domain-disciplines.md` is under a subject-level block, so
it is written here and handed over — the same route cc is using for her three.

---

## THREE DEFECTS OF MINE, ALL FOUND BY USE RATHER THAN BY READING

Recorded together because the pattern is one pattern.

1. **The writer-tier digest included its own mutation** and reported 22 of 22
   rules exercised. Caught by the negative arm written with it. Lived for one
   probe run.
2. **`capture_exit.py --read` raised `AttributeError` on its first real use** —
   a `.strip()` inside the `%`-format parentheses bound to the tuple. **Every
   existing arm passed**, because every one called `read_status()` and none went
   through the CLI wrapping it. *A strong lock over one half of a tool says
   nothing about the other half* — a sentence I wrote about `metamorphic_check`
   the day before and then repeated. Worse: the traceback's exit **1** happened
   to equal the sweep's real **1**, so the number I read was right by accident.
3. **A concurrent sweep deleted the live one's sandbox.** The first full
   151-tool run died 29 tools in with `FileNotFoundError` naming
   `tools/copy_exactly_gate.py` — a file that had done nothing. I had started a
   one-tool run in another shell, and the reap removed every `drs-sandbox-`
   directory regardless of owner. **28 tools of verdicts went with it and the
   failure named the wrong subject.** The reap is now owner-aware and fails
   closed: COULD NOT TELL never licences a delete.

**And my first version of the arm that proves (3) was itself wrong** — I marked
the fixture sandbox with `os.getpid()`, and the arm failed correctly, because the
reap *does* collect a tree marked with its own pid. **The fix went into the
FIXTURE, not the production code.** Changing the tool to pass that arm would have
removed the guard the arm exists to prove.

---

## RAISED, NOT ACTED ON

1. **5 newly-found DEAD rules in three tools I do not own** —
   `criticality_tier_check.py` (`_TAIL_OK`), `defect_register.py` (2),
   `hover_separation_audit.py` (2). Found, reported, not fixed.
2. **2 DEAD rules in `register_feed_gate.py` survive hank's cp1252 fix.**
   Fourth's tool. Item 6's premise was false and is recorded as false.
3. **`tools/push_retry.py --loop` refused my push with a FALSE ATTRIBUTION.** It
   reported *"a rebase this tool just performed SHRANK an append-only ledger:
   docs/known-red-suites.json 17 → 13"*. **My tree was byte-identical to
   origin/main on that file and my commit did not touch it** — the four records
   were removed by hank's `34c834aa` ("the red register reconciled against a real
   run"). The guard is right that records vanished and **wrong about who did
   it**; it compares pre- and post-rebase and blames the rebase. Hank's tool,
   routed, not touched.
4. **The metamorphic rewording finding is still unlogged in the index** — row
   authored in `docs/2026-10-05-cody-routed-to-cc.md`. **cc is now working on
   `fmea/alf_facility_role_gate_live_probe.py` directly**, which is that
   finding's exact subject, so the routing reached the right place.
5. **A FALSE NEGATIVE in `exit_status_attributable.py`**, proposed not patched —
   it cannot see the backgrounding layer. cc holds that file and is mid-fix on
   its false positives.
6. **Michael's 20 SQL files are still unrun** and nothing in this batch moved
   them. The recorded baseline is `PRESENT 0 / MISSING 26` and **I did not
   re-drive it** this batch either.

---

## WHAT THIS DOES NOT ESTABLISH

- **That 521 is every rule on the platform.** Only a module-level
  `NAME = re.compile(...)` is reachable, and `tools/*.py` is not `tests/`,
  `scripts/` or `api/`. **521 is a floor at 3.1x the old floor, not a total.**
- **That the 352 newly visible rules are mostly alive.** See the full-sweep
  section; the verdicts are measured, and the tier that carries most of them is
  the weakest one the tool has.
- **That `firebase-admin@14.5.0` is safe, or unsafe.** It was never installed.
- **That the dependabot banner will clear.** It will not — the vulnerable
  version is still in the tree. **Not-reachable and not-present are different
  states** and only one silences a scanner.
- **That three defects is all of mine in this batch.** Each was found by a
  control, and two of those controls were written in the same change as the
  defect. The ones with no control are the ones I cannot count.
