# The four-part verification programme — scope, order, and what is already built

**Written 2026-09-10 (Cody), after building part 1.** Michael commissioned four
pieces on 2026-09-10: a requirements-to-test traceability matrix, a mock
adversarial audit, fault-injection testing, and a defect-density register. This
is the scope and the order, written down because it is a multi-session body of
work and the next session should not have to re-derive it.

**Part 1 is BUILT and wired** (`10a0aa67`). Parts 2–4 are scoped below. Part 4
depends on 2 and 3 producing findings, and says so.

---

## Part 1 — Requirements-to-test traceability — **DONE**

`tools/traceability_matrix.py` → `docs/traceability-matrix.md`, regenerated on
demand and verified by `--check` as report-only checker 17.

**The design decision worth repeating into parts 2–4: it is DERIVED.** A
hand-written matrix in this repo would be wrong within hours — the app map in
`sairn-guardian-v2` has been corrected six times and CLAUDE.md carries a
standing instruction to re-count rather than trust its own numbers.

**What its first run found, which is the honest baseline everything else builds
on:**

| Measure | Value |
|---|---|
| Test files on disk | 261 |
| Traced to a stated requirement | 77 |
| **Untraced** | **184** |
| Citations pointing at a file that does not exist | 2 |

The 184 are not bad tests. Nothing in the repo states what they are for in a
form a machine can read, so an auditor cannot tell what would be lost by
deleting one. **That number is the single most useful input to parts 2 and 3**:
it is where an outside auditor would start, and it is where fault injection has
the least existing cover.

---

## Part 2 — The mock adversarial audit

**Shape.** Two roles, deliberately separated, because the value is entirely in
the separation:

- **The auditor.** Context-blind by construction — no session history, no
  worklog, told to trust nothing and to treat every claim in the repo as
  unproven until independently verified. Its brief is the repo as a stranger
  finds it: `docs/traceability-matrix.md`, the open-work index, the app files.
  It reports findings with the evidence it gathered, not with what a commit
  message says.
- **The respondent.** Answers the way a real team answers an external audit:
  accept / dispute-with-evidence / already-known-and-recorded, one line each,
  and **no defending a claim without a fresh check**.

**Why it is not just another review pass.** Every review this platform runs is
by a session that has the context. The recurring failure this session recorded
four times — a checker's first real run flagging a *deliberate* pattern — is the
same shape from the other direction: context makes a reviewer generous. An
auditor with no context is generous about nothing, and the respondent's job is
to supply the context the auditor was denied, **in writing, with a check**.

**The scoring that matters** is not the finding count. It is: how many auditor
findings were REAL, and how many the repo could *already prove* were not.
A high false-positive rate against a repo that can prove it is a good result;
a low finding count from an auditor who read the commit messages is worthless.

**Concrete first target:** the 184 untraced tests and the 2 broken citations.
Those are exactly what a stranger would attack first.

**Handoff note.** The two halves should be different sessions. One session
playing both is the thing this is designed to avoid.

## Part 3 — Fault injection

**Distinct from the mutation testing this session did**, and the distinction is
the point. Mutation testing breaks the *logic* and asks whether a test notices.
Fault injection breaks the *world* — a timeout mid-write, a socket dropped
between two calls, a truncated response, a quota exceeded on the third write of
five — and asks whether the app stays honest.

**This is the highest-yield next layer, and tonight is the evidence.** Every one
of these was a real, live finding today and every one is a WORLD failure, not a
logic bug:

| Finding | The world event that exposes it |
|---|---|
| `svSyncSuppressed` left `true` with no `finally` | `st()` throws mid-hydration |
| a refused vendor push showing success | the write returns null and the next sync runs |
| `dnt_supplies` reappearing after a delete | a delete that never reached the server |
| the seed leak reaching the live server | a fresh device with an empty store |

None of them would be found by mutating logic. All four are one injected fault
away from being obvious.

**Shape.** A harness that wraps the app's own transport (`sdnData`, `svData`,
`sairn_http`) and can be told to fail on the Nth call, fail after a partial
write, or hang past a timeout — then asserts the app **reports** rather than
**claims**. The assertion is always the same one this platform cares about:
*does the UI say something true after the fault?*

**Start with the two-call sequences**, because that is where tonight's findings
clustered: write-then-sync, push-then-hydrate, delete-then-merge.

## Part 4 — Defect-density register

**Deliberately last.** It measures the output of 2 and 3, and a register built
before there is anything to put in it becomes a file nobody updates — which is
worse than no register, because its emptiness reads as "no defects".

**Shape.** `docs/defect-density-register.json`, append-only, one record per
CONFIRMED defect: date, app, severity, detection method, lines affected, fixing
commit. Derived where possible — the fixing commit and lines are in git.

**The denominator has to be real.** A density figure needs a line count per app
and a coverage tracker of which independent methods have swept which files.

**And the honest signal is not the number.** It is **consecutive zero-new-finding
sweeps by DIFFERENT methods** over the same file. One method returning zero
means that method is exhausted, not that the file is clean — which is exactly
what this session demonstrated: the mutation controls found two defects in test
code that reading the assertions had not, on the same files, the same hour.

---

## Order, and why

1. **Part 1** — done. It produces the baseline the rest are measured against.
2. **Part 3 (fault injection)** next, not part 2. It needs no second session,
   it has four concrete targets from tonight, and its findings give part 2
   something real to audit rather than a clean-looking repo.
3. **Part 2 (mock audit)** once part 3 has run, and split across two sessions.
4. **Part 4** last, once 2 and 3 are producing confirmed defects.

**One thing to decide, and it is Michael's:** whether the mock auditor should be
allowed to read `docs/` at all. Fully blind is a stronger test and will
re-derive things the repo already knows, at real cost. Blind to the worklogs but
allowed the index and the matrix is cheaper and still adversarial. I would start
with the second and tighten it if it turns out generous.
