# Two sweeps and a denominator: the overrun inversion, and what nobody was counting

**2026-09-28, CC.** Three pieces of one session, written together because the
second explains why the first was findable and the third is why neither would
have been found by the tooling that already existed.

---

## 1. The overrun-inversion sweep

### The class

Found 2026-09-27 in SAIRNbuild's WIP schedule:

```js
var pct = estTotal > 0 ? Math.min(1, costToDate / estTotal) : 0;
var earned = Math.round(pct * revised);
```

A job that had spent 130% of its estimated cost reported **100% complete**, so
`earned` became the **whole contract** and over/under billing swung to its most
**under-billed** reading. **The cap did not round an overrun off. It inverted
the finding.**

Three parts, all of which have to be present:

1. a **ratio** — something over an estimate, budget, target or total;
2. a **cap** at the ratio's nominal maximum;
3. the capped value **feeding** a derived figure — money, a verdict, a status —
   rather than only being drawn.

**Without (3) a cap is usually right.** A progress bar capped at its own track
is correct; a 130%-wide div is a layout bug.

### What the sweep found

`tools/overrun_inversion_scan.py`, 0.6 s over the tracked `.js`/`.html` tree,
9-arm selftest locked against synthetic sources in both directions.

**17 hits: 3 HIGH, 8 MEDIUM, 6 LOW. All seventeen read by hand. Zero NEW
instances of the full class.**

The two that exist — `sairnbuild.html` `jobWIP()` and
`api/_lib/wip-accounting.js` — were fixed the day before, and **the scanner
finds both**, which is what makes the zero mean anything.

### The four verified non-hits, named because each looks like the defect

| site | why it is not the class |
|---|---|
| `stonedesk.html:26521` | caps a schedule bar, while `schedUrgency()` prints **OVERDUE** beside it — the overrun is surfaced by a different control |
| `stonedesk.html:20008` | `sairnRangeBar` prints the raw `value / max` next to the clamped fill |
| `stonedesk.html:26667` | inventory level bar; the status badge prints Out / Low / Warning independently |
| `api/_lib/dental-credentials.js:214-215` | **part (3) IS present** — the capped fractions feed a `behind` / `on_track` verdict — **but both caps are unreachable by construction**: `logged >= required` returns `complete` and `daysRemaining < 0` returns `overdue` before either line runs. The `: 1` fallbacks also point the safe way |

The dental one is the interesting negative. It is the only hit where a capped
ratio really does decide a verdict, and it is still correct — which is exactly
why the scanner ranks and does not gate.

### One minor instance, reported and not fixed

`stonedesk.html:6394` — the admin storage KPI renders
`Math.min(100, bytes/5MB*100)` as **the only figure on the tile**. 140% of quota
reads identically to exactly full. It is a gauge rather than money, and
`stonedesk.html` is not in this session's declared file set.

### Registered

Class **27** in `.claude/skills/sairn-code-scrubber/SKILL.md`, with the
question to ask of each hit — *when the input exceeds the estimate, does the
output move towards "fine"?* — and the companion defect that travels with it: a
**stale denominator**. SAIRNbuild had both, and either alone is survivable.

---

## 2. A wired checker that could not run

`tools/mutation_anchor_check.py` is in `report_only_checks.REGISTRY` and had
been exiting **2 — COULD NOT RUN — permanently**, on 84 arms across 19 probes.

**Not one of the 84 was a stale anchor.** Every one was a declaration shape the
resolver did not know, and the message was wrong about most of them: it said
*"target unresolved"* for arms whose target had resolved perfectly.

Four root causes, each measured before being fixed:

1. **The target resolved and was thrown away.** The type guard returned
   `(None, old)` whenever the mutation was a lambda, discarding a path it had
   just resolved. The STRUCTURAL bucket existed and was unreachable for these.
2. **The no-target fallback looked for `consts.get('TARGET')`.** `TARGET`
   appears in **exactly zero** of the 19 probes. They call it `SUITE` (11),
   `APP` (3), `HANDLER` (3), `API`, `ENDPOINT`, `REGISTRY`, `SERVING`, `ENGINE`,
   `LOCK`, `AUTH`, `SRC`, `TOOL`, `SUBJECT` and eight more.
3. **Tuple unpacking was invisible** to the constant reader, so
   `RAW_APP, RAW_H, RAW_REG = ...` read as *names that do not exist*.
4. **An inline `os.path.join` in the target slot** was not parsed.

**84 → 0 could-not-read. Exit 2 → exit 1. Nothing suppressed to get there.**

**And the exit 2 was hiding 16 real findings** — 15 vanished anchors and one
ambiguous, mostly in `api/sd-data.js`. Corroborated by a structurally different
method: `tests/active_credential_gate_probe.py`, which the checker says has 5
dead anchors, **exits 1 when run**.

The sole-subject fallback is decidable rather than a guess — a mutation probe
mutates the *subject* and watches the *suite*, so suite paths are dropped first.
**More than one candidate remaining stays unreadable with the candidates
named**: guessing there would count an anchor in the wrong file and report
ANCHOR-0 against a healthy arm, which is a *false* stale-anchor finding and
worse than the silence.

---

## 3. Coverage denominators, and the incident that earned them

### What nobody was counting

2026-09-27: this platform had **two** anchor-freshness checkers running side by
side, both wired, both correct, **and their populations did not overlap at
all.**

| convention | probes | checker |
|---|---|---|
| module-level `MUTATIONS` list | 82 | `mutation_anchor_check.py` |
| `arm(…, [(SUBJECT, old, new)])` and flat `arm(label, suite, old, new)` | 12 | `probe_anchor_freshness.py` |
| **union of the two** | **94 of 98** | — |

Three probes in the second population were **dead** while the first tool
reported clean results about its own 82. Nothing was broken and nothing was
stale: **the number of things being checked was never compared against the
number of things there are.**

A checker reporting "114 anchors agree" has said nothing about coverage. *114
out of what?*

### The unification

`probe_anchor_freshness.py` now reads the `MUTATIONS` convention too — by
**importing `mutation_anchor_check`'s reader, not copying it.** A second parser
would be a second thing to keep in step, which is the duplicate-scanner mistake
`conflict_marker_preflight.py` already records making against
`conflict_marker_check.py`.

**12 → 87 of 98 probe files.** The two tools now share a denominator, and the
remaining 11 are visible instead of imaginary.

It also **independently reproduces the same vanished anchors** that
`mutation_anchor_check` reports, through a different reader — two structurally
different methods agreeing about the same defect.

*(The first unified run produced four FALSE vanished rows — `@ENTRIES`,
`@GATE`, `@REFUSE`. A `@name` is a name, not text, so zero matches is the
correct and meaningless answer. Skipped now, because a false VANISHED is worse
than silence: it sends somebody to re-anchor a healthy arm.)*

### The ratchet

`tools/checker_denominator.py` publishes **checked / universe** for every
registered checker and **fails when the universe grows and the checked count
does not** — the exact shape of the incident: somebody adds probes in a
convention the tool cannot parse, the tool keeps reporting a clean number about
the subset it can see, and coverage silently falls.

First baseline, taken **after** the unification so the ratchet measures forward
from the corrected state rather than blessing the 12 that caused the incident:

| tool | checked | universe | coverage |
|---|---|---|---|
| `probe_anchor_freshness.py` | 87 | 98 | 89% |
| `mutation_anchor_check.py` | 82 | 98 | 84% |
| `overrun_inversion_scan.py` | 6 | 22 | 27% |
| `ai_action_approval_audit.py` | 22 | 22 | 100% |

**What it deliberately does not do**, each with a reason:

- **It does not trip on coverage being LOW.** A tool at 27% that has always
  been at 27% is a stated limit; failing on it produces a red nobody can clear
  and the whole thing gets switched off. The ratchet is about **regression**.
- **It does not trip when both shrink** — deleting probes is legitimate.
- **A missing baseline is `UNBASELINED`, never `OK`.** An unmeasured tool
  reported as clean is the failure this file exists for, one level up.
- **`--update` demands a 30-character reason**, stored beside the numbers.
  Re-baselining is how a ratchet is silently disarmed.

---

## 4. What none of this did

- **`overrun_inversion_scan.py` cannot follow a capped value to its consumer.**
  That is the judgement every hit exists to prompt, and a cap written without
  `Math.min` — `if (r > 1) r = 1`, a clamp helper, a ceiling in SQL — is
  invisible to it.
- **`checker_denominator.py` covers four checkers of the 63 in the registry.**
  The other 59 publish no denominator and are not measured. Extending it is one
  `universe`/`checked` pair per tool and is open.
- **The 16 anchor findings are NOT fixed.** They are re-anchors across 8 probe
  files, most against `api/sd-data.js`, which another session holds.
- **`checked` for `overrun_inversion_scan` means "produced at least one row"**,
  so a genuinely clean app is indistinguishable from an unparsed one. Stated in
  the tool's own note rather than left to be assumed the other way.
- **No claim is made that three anchor conventions is all there are.** A fourth
  would be invisible the same way the third was, and the denominator is now the
  only thing that would show it.
