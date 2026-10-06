# Queue 17 — inventory and methodology: the upgrade beat my own finding, and 49 dead rules are none of mine

**2026-10-06 (Cody).** Seventeen items. **Every figure below carries its
denominator, its command, its commit and its date — item 15(b), applied to this
document rather than only written in it.**

Routing artefact: `docs/2026-10-06-cody-routed.md`.
Handoff: `docs/handoff-cody-2026-10-06.md`.

---

## WHERE EACH ITEM STANDS

| # | item | state |
|---|---|---|
| 1 | firebase-admin 14.5.0 driven in a scratch copy | **CLOSED** — green, and it drops node-forge entirely |
| 2 | the metamorphic index row | **CLOSED, WITHDRAWN** — the finding stopped reproducing |
| 3 | 49 rules dead to their own evidence | **ROUTED 49, diagnosed 0, fixed 0 — none is mine** |
| 4 | 36 COULD NOT RUN, causes and fixes | **36 → 23, and 21 of the 23 were MY bound** |
| 5 | exit codes into three docs | **CLOSED** — and re-running changed the answer |
| 6 | `push_retry.py` false attribution | **ROUTED to fourth** with file:line |
| 7 | two concurrent sweeps | **CLOSED** — both finish, driven |
| 8 | self-mutation digest sweep | **CLOSED** — 9 read, 17 routed, 0 new defects |
| 9 | CLI entry-point sweep | **CLOSED** — 7 sites of mine fixed |
| 10 | the first SQL file | **IN THE REPORT** — needs Michael |
| 11 | 28 Tier A obligations | **1 discharged adversarially, 27 open** |
| 12 | `db/schema_snapshot.json` | **OPEN** — `_constraints` absent |
| 13 | unregistered tools | **0 to register**; 1 of 2 pending tools landed and is registered |
| 14 | universe re-measure | **CLOSED** — figures below |
| 15 | methodology | **BELOW**, and the earlier three are **NOT** promoted |
| 16 | inventory | this document |
| 17 | handoff | written before this report |

---

## ITEM 1 — THE UPGRADE IS GREEN, AND IT MAKES MY OWN FINDING UNNECESSARY

Yesterday I measured that `firebase-admin@12.7.0` reaches node-forge in exactly
one place — `forge.pki.privateKeyFromPem`, a parser — and concluded the
vulnerable verification primitive was off our path. **That holds and is no
longer the best answer available.**

```
npm install firebase-admin@14.5.0 --package-lock-only   NPM_INSTALL_EXIT=0
npm install                       (full, scratch copy)  NPM_FULL_INSTALL_EXIT=0
npm ci                            (12.7.0 baseline)     NPM_CI_BASELINE_EXIT=0
node -e require('./api/_lib/firebase-admin.js')         FIREBASE_LIB_LOAD_EXIT=0
```

**No command was blocked.** `npm install` had been declined last session; run in
a scratch directory outside the repo it completed.

| | 12.7.0 | 14.5.0 |
|---|---|---|
| `node_modules/node-forge` | **1.4.0** | **ABSENT** |
| packages declaring it | `firebase-admin` | **none** |
| `forge.*` call sites in its `lib/` | **1** | **0** |
| locked packages | 195 | 232 |

**"The package is not in the tree" needs no trigger. "The function is not on our
path" needs one, and depends on there being exactly one call site.** Mine is
superseded, and that is said plainly rather than defended.

### The suites, as a DIFFERENTIAL — an absolute here would be a number about a temp directory

```
BASELINE-12.7.0 : 248 suites, 160 exit 0, 88 NOT 0
UPGRADE-14.5.0  : 248 suites, 160 exit 0, 88 NOT 0
SUITES WHOSE VERDICT CHANGED:  0
```

**Zero. Red and green sets identical, suite for suite.** All eight `sairncash`
suites — the only ones touching this dependency — **exit 0 under both**. The 88
red are red under 12.7.0 too, mostly `deadline-*` and `compliance-*` wanting
environment the scratch copy lacks: **that is why a baseline copy was built at
all.**

**NOT APPLIED.** `package.json` and `package-lock.json` in this repo are
untouched — measuring an upgrade and landing one on a live payment path are
different actions. **And no suite drives a real `mintCustomToken`**, so "nothing
changed" is bounded by coverage that does not include the mint path.

---

## ITEM 4 — 21 OF THE 23 SURVIVING REFUSALS WERE MY OWN 45-SECOND BOUND

COULD NOT RUN fell **36 → 23**. The surviving 23 are three groups, and each
cause was measured rather than assumed:

| group | rules | cause |
|---|---|---|
| `cross_tenant_isolation_scope.py` | **21** | **MY BOUND.** The tool needs **131s**; `CORPUS_TIMEOUT` was **45**, so its bare run timed out on every ablation |
| `run_all_tests.py` | 1 | mine, same tier |
| `guard_ablation.py` | 1 | owner unknown, same tier |

**AND THE REPORTED REASON WAS FALSE.** All 21 printed *"no fixture lock and no
control to ablate against"*. It has no lock — **but the real run WAS available
and my sweep declined to wait for it.** Two different causes printing one line
is the defect this tool exists to catch, arriving in its own output.

**Raising the default is not the fix:** 21 rules at 131s, twice, is 90 minutes
for one tool. So the bound is **overridable and PRINTED on every run**
(`--corpus-timeout`), and a timeout gets its own verdict that names itself.
`_bare_baseline()` re-asks with a 2-second bound to tell a timeout from a crash,
so *"needs longer"* and *"is broken"* stay different answers.

### RE-ASKED AT 200s, AND THE BOUND WAS HIDING FOUR REAL FINDINGS

```
python tools/dead_rule_sweep.py --tool cross_tenant_isolation_scope.py        --corpus-timeout 200                                      EXIT 1
  corpus bound: 200s per bare real run (--corpus-timeout)
  CHECKED / UNIVERSE: 21 of 21 rules could be ABLATED
  17 move the output, 4 DO NOT MOVE A BYTE
  FINDINGS (4)
    ! _HASH_LITERALS   DEAD EVEN ON THE REAL RUN
    ! _HASH_RETURNED   DEAD EVEN ON THE REAL RUN
    ! _REFUSAL_LENGTH  DEAD EVEN ON THE REAL RUN
    ! _DECL_BLOCK      DEAD EVEN ON THE REAL RUN
```

**21 of 21 answerable, and four of them are DEAD.** My 45-second bound was not
merely mislabelling those rules as unknown — **it was hiding four findings in
cc's tool**, and it had been doing so since the tier existed.

**So the platform's real refusal count, when the bound is lifted, is 2** —
`run_all_tests.py` and `guard_ablation.py`, one rule each. **That figure is only
honest with the bound printed beside it**, which is why the bound now prints on
every run.

---

## ITEM 14 — THE UNIVERSE AT HEAD

```
python tools/dead_rule_sweep.py --universe      EXIT 0
commit 6d19c775, 2026-10-06T14:17:34Z

tracked tools/*.py                   297
THE UNIVERSE -- files swept          152  ->  540 rule(s)
  of those, in the registry           45  ->  169 rule(s)
  of those, OUTSIDE it               107  ->  371 rule(s)
exempt, declared with a reason         0
no module-level rule -- mechanical   145
```

### The delta from the last figures, with both commits named

| | queue 16 (`a86e2948`, 10-05) | queue 17 (`6d19c775`/`8f204050`, 10-06) | delta |
|---|---|---|---|
| tracked `tools/*.py` | 295 | **297** | +2 |
| files in the universe | 150 | **152** | +2 |
| rules in the universe | **528** | **540** | **+12** |
| outside the registry | 352 | **371** | +19 |
| CHECKED | 492 of 528 | **517 of 540** | +25 |
| DEAD to own evidence | 43 | **49** | +6 |
| DEAD on the real run | 94 | **101** | +7 |
| **COULD NOT RUN** | **36** | **23** | **−13** |
| FINDINGS | 137 | **150** | +13 |

**The ablation figures are from `8f204050`** (the full run, `EXIT 2` from its
status file); **the universe figures are from `6d19c775`**, four commits later.
**Two commits, named, rather than one figure pretending to be simultaneous.**

**+12 rules in a day is the drift rate, and it is the number to keep.** Queue
16 measured +7 in an hour. **`gate_parity_check.py` alone brought 9**, six of
them dead on arrival.

### AND THE OLD POPULATION'S VERDICT CHANGED

```
python tools/dead_rule_sweep.py --registry-only --segment 1/1   EXIT 1
  169 of 169 CHECKED, 0 COULD NOT RUN, 33 FINDINGS
```

**On the exact pre-2026-10-05 population — 75 tools, 169 rules — every rule is
now answerable.** That run used to exit **2**. The 22 write-when-run refusals
are measured by the writer tier. **That is the cleanest statement of what this
batch bought, because the population is held fixed.**

---

## METHODOLOGY (ITEM 15)

### (a) A FIX THAT CLOSES NAMED INSTANCES LEAVES THE MECHANISM OPEN

**Re-measure the whole population that produced the defect, not the instances
it named.**

| when | what I did | what the population turned out to be |
|---|---|---|
| 10-05 | `gap_ledger.py` was missing from the sweep's universe. Added it and `gate1_verify.py`, pushed the fix | **"162 of 169"** |
| 10-06 | replaced the universe with a `git ls-files` glob | **169 of 521** — the hole was **352 rules in 105 files**, not 7 in one |

**Closing two names cost a commit and left the mechanism exactly as it was.**
The cheap test is: *what produced this instance, and can I count all of it?*

**It repeated inside this batch.** Item 9 fixed seven undecoded `subprocess`
sites of mine; the tool that found them still reports **64** in other sessions'
files. **Mine are closed and the class is not**, and the difference is written
down rather than implied by a green line.

### (b) EVERY FIGURE CARRIES ITS DENOMINATOR, COMMAND, COMMIT AND DATE

**A bare number is not a measurement.** "49 dead rules" means nothing without
*of 540, by `python tools/dead_rule_sweep.py`, at `8f204050`, on 2026-10-06*.

Three of my own documents reported this sweep **with no exit code at all**
(item 5) — figures printed, status absent, absence reading as a pass. **And
re-running instead of quoting changed two answers in this batch:** the
metamorphic rewording finding stopped reproducing (item 2, row withdrawn before
anybody pasted it) and the registry-only population moved from exit 2 to exit 1.

**The denominator is the half most often dropped and the most load-bearing.**
*"162 of 169"* and *"169 of 521"* are the same numerator with two different
denominators, and only one of them is the platform.

### (c) A TIER THAT CLEARS A CATEGORY AND FINDS NOTHING IN IT IS THE OUTCOME TO DISTRUST

**Measured 2026-10-06.** The writer tier's first run cleared all 22
write-when-run rules and reported **22 of 22 exercised, 0 dead**. That is
exactly what a tier which can only say *"exercised"* produces.

It was not believed, and the arm written with it — a hand-built writer carrying
one rule it provably never reads — **failed**. Cause: the comparison digest
included the swept tool's own mutated source, so it differed every time because
of the **mutation** rather than its **effect**. After the fix: **17 exercised, 5
DEAD.** *The blanket refusal had been hiding five real findings and my first
version reported zero.*

**The operational form: when a change clears a whole category, the arm that must
exist is the one proving the tier can still say NO.** Three further cases this
batch:

- the escape check that **accused an innocent tool** — fixed, then accused
  nothing and still voided the run; fixed again with a discriminator;
- the 21 refusals whose reason was *"no evidence"* when the evidence existed;
- the Tier A sabotage control whose **paired positive S3 failed first** — had it
  been omitted, three sabotage arms would have "passed" against a tool returning
  nothing, and an obligation would have been discharged on nothing.

### THE EARLIER THREE ARE **NOT** PROMOTED, AND THAT IS A GAP I AM REPORTING

The three from queue 16 — the trailing-echo rule chief among them — were written
into a **dated inventory** and routed for promotion. **They are still there.**

`docs/METHODOLOGY.md` **does not exist at HEAD** and is in **fourth's** live
claim; `docs/2026-09-13-cross-domain-disciplines.md` still holds **12** headings
and the claim matcher blocks me on subject. **So six cross-cutting rules now sit
in dated files**, which is the eighth standing convention with a queue of its
own. Routed to fourth again, and said rather than left to be discovered.

---

## THREE DEFECTS OF MINE, ALL IN CODE I WROTE EARLIER IN THE SAME DAY

1. **The escape check accused `primitive_obsession_check.py`** and voided a
   23-minute run. The tool is innocent — driven alone the clone is
   byte-identical. The cause was **my own `git commit`**. Fixed with a HEAD
   discriminator; it then voided a *second* run, blaming nothing, because my own
   `traceability_matrix.py` dirtied the tree. Fixed properly: the question is
   whether the clone changed **in a file the tool wrote inside the sandbox**,
   which `_writer_sig` already returned and I was not using.
2. **The 45-second bound reported 21 rules as having no evidence** when the
   evidence existed and my tool would not wait.
3. **Seven undecoded `subprocess` sites**, six written that morning, found by a
   tool I was driving as a *subject* rather than reading as a checker. **The one
   that mattered — `tasklist` inside `_pid_alive` — failed CLOSED**, so the
   sandbox guard held by construction rather than by luck.

**And my `sed` wrote a raw cp1252 `0x97` byte into a document three times**,
hours after fixing seven sites of the same class. Repaired in Python.

---

## WHAT THIS DOES NOT ESTABLISH

- **That 49 dead rules are 49 defects.** DEAD means nothing the tool ships as
  evidence would notice the rule vanishing. The repair is a fixture **or** a
  named limit — different answers. **None of the 49 has been diagnosed.**
- **That 540 is every rule on the platform.** Only a module-level
  `NAME = re.compile(...)` is reachable, and `tools/*.py` is not `tests/`,
  `scripts/` or `api/`. **A floor that moved +12 in a day.**
- **That the 27 remaining Tier A obligations are low-risk.** They are unread.
- **That `firebase-admin@14.5.0` is safe.** 0 suites changed verdict; no suite
  drives a real `mintCustomToken`, and 37 transitive packages arrive unaudited.
- **That three defects is all of mine in this batch.** Each was found by a
  control, and two of those controls were written in the same change as the
  defect. **The ones with no control are the ones I cannot count.**
