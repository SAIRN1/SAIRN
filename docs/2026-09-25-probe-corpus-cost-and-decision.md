# The sabotage-probe corpus: measured cost, and the gate decision

**2026-09-25 (CC).** The open-work row filed yesterday said the corpus cannot
become a push gate without measuring wall-clock first. Measured. **Decision
below, made rather than deferred.**

---

## 1. The corpus is 65 probes, not 27 — and my own earlier figure was wrong

**CORRECTED FIRST, because it is a number I published yesterday.**
`docs/2026-09-25-ablation-sabotage-harness.md` and the open-work row both say
"27 probes". The real count is **65**. The 27 came from a grep matching one
import spelling (`from sabotage_harness import`); the corpus also contains
probes that `import sabotage_harness` plainly, and the ablation therefore ran
against a subset of the corpus it claimed to sweep.

That does not invalidate the ablation's findings — every arm it fixed was really
broken — but it does mean **the ablation's coverage claim was overstated by more
than half**, and the 15 dead arms it found were 15 out of a bigger population
than stated. The corrected sweep is what this document's numbers come from.

Re-derive rather than trusting either number:

    python - <<'EOF'
    import io,os,re
    t='tests'
    n=[f for f in sorted(os.listdir(t)) if f.endswith('.py') and
       re.search(r'^\s*(?:from|import)\s+sabotage_harness\b',
                 io.open(os.path.join(t,f),encoding='utf-8',errors='replace').read(),re.M)]
    print(len(n))
    EOF

## 2. The measurement

Serial, one at a time, on this clone, 2026-09-25:

| | |
|---|---|
| probes | **65** |
| total wall-clock | **1,837 s = 30.6 min** |
| median probe | **10.9 s** |
| slowest | 237.0 s (`run_hover_audit_method_sabotage_probe.py`) |
| slowest five combined | 741.6 s — **40% of the total** |
| failing at measurement time | **9** |

The cost shape is the important part: **the median probe is 11 seconds and the
distribution has a long tail.** Five probes carry 40% of the runtime, because
each spins a git worktree per mutation and runs a real suite inside it, and the
slowest ones wrap suites that are themselves expensive (the hover-audit probe's
subject is a 149-check suite).

## 3. The decision: NOT a push gate. Scoped-on-push + a full scheduled run.

**A 30-minute addition to every push is disqualified on this platform's own
evidence, not on taste.** The repo records, in three separate places, that a
gate which must be routinely talked past produces overrides, and that overrides
cost more than the gate saved. `tools/register_feed_gate.py`'s own header
records the same arithmetic and chose a requirement date over a wall for exactly
this reason. A 30-minute pre-push wait would be overridden by the second day.

So, three parts:

**(a) ON PUSH — scoped, not all.** Run only the probes whose subject the push
touches: a probe names its subject files in `MUTATIONS` and in `stage`, so the
selection is mechanical and needs no new declaration. At a median of 11 s, a
push touching one or two subjects pays ~10-30 s, which is inside the noise of
the existing gate. **This is the part that still has to be built** — see §5.

**(b) NIGHTLY — the whole corpus, per ARM.** 30.6 min is nothing on a schedule
and everything on a push. The report must be **per arm, not per exit code**: 6
of the 15 arms the ablation found were invisible at the exit-code level, because
those probes exited non-zero in both conditions for different reasons.

**(c) NEITHER PART MAY REPORT A SKIP AS A PASS.** A probe that could not run is
`COULD NOT RUN` with its own exit (the harness already does this — exit 3), and
the nightly summary must carry that count separately or the whole exercise
recreates the defect it exists to catch.

**What is explicitly NOT decided here:** whether the nightly runner is a GitHub
Action or a cron on this machine. The workflows already pin node 24 and run on
schedule, so the Action is the obvious host — but `run_tlc.py`'s precedent
(vendored jar, gitignored, cannot run in CI) says the environment question gets
answered by trying, not by assuming. That is a build step with a measurable
outcome, not a judgement call to make in a document.

## 4. And the 9 failures are a finding about the corpus, not about the runner

Nine probes were red at measurement time, on a clean tree, after yesterday's 15
repairs. They are **not** the same nine: yesterday's sweep covered the 27-probe
subset, and these come from the corrected 65. Three are already understood —
`run_hover_audit_method_sabotage_probe.py` and
`run_defect_register_vocab_sabotage_probe.py` are both blocked by the single
malformed register record filed yesterday, and `app_session_isolation_probe.py`
was red before any of this work.

**The other six are new information and are NOT diagnosed here.** Diagnosing six
probes is its own body of work with its own claim, and folding it into a costing
document is how a measurement turns into an afternoon. They are listed so the
next session starts from a list rather than a sweep:

    approval_persistence_probe.py
    demo_seed_licence_scope_probe.py
    exec_role_gate_probe.py
    intake_link_no_credential_probe.py
    run_body_file_wiring_sabotage_probe.py
    run_sf_session_gate_sabotage_probe.py

**Expect the same three classes yesterday's fifteen fell into** — a malformed
mutant, a stale anchor, an expired premise — because that is what the corrected
count implies: the class was never confined to the 27.

## 5. The one thing to build, and its acceptance test

The scoped-on-push selector. Its acceptance test is not "it runs" but:

* given a push touching `api/sd-data.js`, it selects every probe naming that
  file in `MUTATIONS` or `stage`, and **not** the ones that do not;
* given a push touching only `docs/`, it selects **none** and says so, rather
  than running the corpus "to be safe" — which is how the 30-minute wall gets in
  through the back door;
* a probe whose subject cannot be determined is **reported, never silently
  skipped**: an undeterminable subject is the third state, and a selector that
  quietly drops it is the silent-pass shape this whole corpus exists to catch.
