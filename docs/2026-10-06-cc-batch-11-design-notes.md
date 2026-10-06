# Design note — scrutiny flag on self-weakening diffs

**Written before any code, 2026-10-06, at HEAD `f588ef02`.** Claims-checked
first: `tools/exit_status_attributable.py`, `tools/sairn_push_gate_hook.py` and
`.githooks/pre-commit` are all **FREE** at this commit
(`python <scratch>/whoholds.py <paths>` against `.claude/claims/*.json`).

---

## The problem, stated as a failure mode rather than a feature

**An agent must not quietly weaken the thing that checks its own work.** Three
diff shapes do that, and none of them is a bug — each is a legitimate edit most
of the time:

* **a test file** — relaxing an assertion, deleting an arm, widening a fixture;
* **CI configuration** — `.github/workflows/*`, the hooks wiring in
  `.claude/settings.json`, `.githooks/*`;
* **push-gate logic** — `tools/sairn_push_gate_hook.py` and the tools its checks
  invoke.

**THE REASON THIS IS NOT ALREADY COVERED.** The gate has 15 numbered checks and
every one asks *"is this push's content wrong?"* None asks *"is this push's
content a change to the thing that answers that question?"* Check 13 comes
closest — it opens a review obligation on Tier A **resource** code — and a gate
check is not a Tier A resource, so a diff that deletes a gate check opens
nothing.

**THE CONCRETE PRIOR.** `docs/2026-10-06-cc-batch-10-inventory.md` §4 records
`tests/run_export_coverage_probe.py` already sitting in
`docs/known-red-suites.json`, and §16 of the batch-9 inventory records
`checker_selftest_check.py` answering a true third state with a false reason for
an unknown number of runs. **Neither was noticed by a gate.** The pattern that
would be invisible is smaller still: one `assertEqual` becoming `assertTrue`.

---

## Goals

1. **Flag, never block.** A test edit is normal work. The flag must survive being
   seen hundreds of times without anybody wanting it switched off.
2. **Visible in the gate output at push time**, so the person pushing sees it
   before the push lands rather than in a report later.
3. **Written to a record a review obligation can pick up** — a flag nobody can
   query later is a warning, not a control.
4. **Name the file and the reason**, not a count. "3 files flagged" sends
   somebody to read a diff; "`tests/foo.py` — an assertion was removed" does not.
5. **Distinguish WEAKENING from CHANGE where it is cheap to do so**, and say
   plainly when it cannot. An added arm and a deleted arm are both "a test file
   changed"; only one of them is the failure mode.

## Non-goals

1. **Not a judgement about intent.** It reports shape. "Why" is a human read.
2. **Not a blocker, ever** — including when it is confident. A control that can
   block its own author's gate edits is a control that gets `SAIRN_SEED_GATE=off`
   put in front of it permanently, which is worse than not having it.
3. **Not a replacement for check 9** (the named guard and seam tests block) or
   **check 13** (the independent-review rule). Those two refuse; this one
   annotates.
4. **Not a coverage measure.** It does not know whether the remaining assertions
   are sufficient, and must not imply it does.
5. **No semantic analysis of test logic.** A regex-and-counting layer whose
   limits are stated beats an AST layer whose limits are discovered.

---

## Alternatives considered

### A — a new standalone tool, wired as its own hook *(REJECTED)*

A `tools/self_weakening_check.py` on its own `PreToolUse` entry.

* **For:** zero risk to the existing gate; its own exit code; trivially testable.
* **Against, and decisive:** it would be the **third** program parsing a push's
  outgoing diff, after the gate and `exit_status_attributable`. The repo has a
  recorded cost for exactly that —
  `84eb61ea` *"my conflict pre-flight duplicated an existing push gate"* — and
  `docs/2026-10-06-cc-batch-10-inventory.md` §3 rejected a parallel re-seater on
  the same grounds. A second diff parser drifts from the first, and the drift is
  silent because both keep passing.
* **Also against:** a separate hook has a separate failure mode. The gate already
  computes `outgoing_files(repo, base, tip)` correctly, including the
  `git push origin <sha>:main` case that cost a real miss on 2026-09-01.

### B — extend the push gate only, as CHECK 16 *(REJECTED as insufficient)*

* **For:** one diff parser, the right place, existing `deny`/collect plumbing.
* **Against:** the gate runs **at push**. Nothing then flags the edit at the
  moment it is made, and nothing outside a push can ask *"what has been flagged
  this week?"* Goal 3 is unmet: the gate's output is transient.

### C — extend BOTH, with the classifier in `exit_status_attributable.py` *(CHOSEN)*

`exit_status_attributable.py` already owns *"read a command or a diff and say
what it really does"*, already has `--selftest` with paired arms, already
exposes a `post_hook()` the wiring calls, and is already **registered in
`report_only_checks.REGISTRY`** — so a flag it emits has an existing cadence.

* The **classifier** (which paths are self-checking, which diff shapes are
  weakening) lives in `exit_status_attributable.py` as importable functions.
* The **push gate** imports it and prints the flags to stderr on the allow path.
  One new numbered check, non-blocking.
* The **record** is a JSON ledger, append-only, that a review obligation can
  read.
* **Against, and accepted:** it grows a file that is already large, and it
  couples the gate to an import. Mitigated by the import being guarded — the
  batch-10 shape — so a missing classifier makes the gate **say so** rather than
  fall silent or crash.

### D — a `PostToolUse` hook on Write/Edit *(REJECTED for now, worth revisiting)*

Flag at the moment of the edit, which is the earliest possible point.

* **Against:** it fires on every Write/Edit in the session, including the
  intermediate states of a correct edit. Flagging a file I am halfway through
  rewriting is noise, and noise is what kills a non-blocking control. The push
  boundary is the first point at which the edit is final.
* **Recorded as the next step rather than discarded**: once the ledger exists and
  its false-positive rate on real pushes is measured, the same classifier can be
  wired at edit time with the rate known in advance.

---

## Cross-cutting concerns

| concern | decision |
|---|---|
| **Fail-closed vs fail-open (PR §1.11)** | The gate's own contract is fail-open on a bug, and that is not changed. But the classifier import is **guarded and reported**: if it cannot be imported, the new check prints `COULD NOT RUN` naming the import error, and does not pretend the diff is clean. A silent skip here is the defect this whole batch has been about. |
| **It must not block** | No `deny()` call anywhere on this path. The flag goes to **stderr**, which git relays in `prepush` mode and Claude Code surfaces as hook feedback in `pretooluse` mode, in both cases without touching the permission decision. |
| **Ownership / claims** | All three target files were **FREE** at `f588ef02`. The new ledger `docs/scrutiny-flags.json` is new, so it is nobody's. **`docs/METHODOLOGY.md`, `docs/SAIRN-OPEN-WORK-INDEX.md`, `docs/TOOLING-INVENTORY.md` and `tools/tooling_inventory.py` are HANK'S** — so the PURPOSES entry this build will need is the same coupling recorded as a finding in §5 of this batch, and it will be declared again rather than quietly repeated. |
| **The ledger must not become a write race** | Four clones push into one branch. The ledger is **append-only with a union-by-identity merge policy**, the shape `docs/tier-a-reviews.json` already uses and `tools/sairn_rebase_resolve.py` already knows how to merge. Identity is `(sha, path)`. |
| **The ledger must not grow without bound** | Entries are keyed by commit, so a flag is written once per commit per path, not once per push attempt. A rebase that rewrites the commit writes a new entry — and `.githooks/post-rewrite` plus `tools/doc_sha_reseat.py` exist for precisely that, so the ledger joins the set the rewrite map already repairs. |
| **False positives** | A test file edit is the common case, so the flag must be cheap to read and must say which shape it matched. Measured on real data before the numbers are quoted: the selftest uses planted diffs, and the real-corpus rate is reported separately rather than inferred from the fixtures. |
| **Self-application** | **This build touches `tools/sairn_push_gate_hook.py`, which is push-gate logic — so the control flags its own landing commit.** That is correct and is the first real end-to-end evidence. It is also the honest reason it must not block: a control that blocked self-weakening diffs could not be installed. |
| **Who reviews it** | The whole point is that an agent should not be the only reader of a weakening of its own checks. The ledger is the hand-off: a review obligation can read it. **I am not the reviewer of my own flag.** |

---

## What "weakening" means mechanically, and what it cannot see

Per changed path, from the outgoing diff only:

* **`SELF_CHECKING` path classes** — `tests/**`, `api/**/*.test.js`,
  `.github/workflows/**`, `.githooks/**`, `.claude/settings.json`, and the
  gate/attributable/report-only tools by name.
* **`WEAKENING` shapes** — net removal of assertion-shaped lines; an arm count
  that falls; a bound that rises (`timeout=`, `--max`, a threshold literal); a
  deny becoming a report; an added skip/exemption/allowlist entry.
* **`CHANGE` otherwise** — flagged at a lower level, because "a test file moved"
  is still worth a reviewer's eye and is not the same claim.

**IT CANNOT SEE:** an assertion that still exists and no longer tests anything;
a fixture that was quietly made easier; a mutation that keeps the arm count and
inverts the sense. Those are stated in the tool's own `BLIND_SPOTS` rather than
left for somebody to assume covered.
