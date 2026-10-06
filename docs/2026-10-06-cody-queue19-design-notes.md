# Queue 19 design notes — four new tools, written before any code

**2026-10-06 (Cody).** Required before the builds in items 2, 3, 5 and 10.
Each section: **Goals / Non-goals / Alternatives considered / Security / Data /
Test plan.** Alternatives are recorded with the reason they lost, so nobody pays
for the same idea twice.

**Two of these exist because of mistakes of mine recorded in
`docs/handoff-cody-2026-10-06b.md`.** That is stated in their goals, not as
colour.

---

## 1. `tools/ledger_append.py` — item 2

### Goals

1. **Append to an append-only ledger from a FILE or STDIN ONLY.** Never from a
   shell argument. This closes a real incident: a verdict passed as an argument
   had two backticked fragments command-substituted away and **a third replaced
   by the output of `id`**, pasting a local uid and gid into
   `docs/tier-a-reviews.json`.
2. **Refuse if any existing byte would change.** The other incident: a
   `json.dumps(indent=1)` repair produced **5681 insertions and 5674 deletions**
   on a 235-record ledger four clones merge, against a correct diff of **15 and
   8**.
3. **Refuse if `git diff --numstat` shows more added lines than the entry
   holds.** A structural, post-hoc check that does not trust the writer.
4. **JSON ledgers get a targeted single-object insert**, never a whole-file
   re-serialisation.

### Non-goals

- **Not a replacement for `tier_a_review_gate.py --discharge`.** That tool owns
  the Tier A schema and its own `--body-file` path. This is the general
  primitive for *any* append-only ledger, and for ledgers that have no tool.
- **Not a merge tool.** `sairn_rebase_resolve.py` owns 3-way union merges.
- **Not a validator of ledger CONTENT.** It checks that the write is an append;
  whether the appended record is true is somebody else's job.

### Alternatives considered

| alternative | why it lost |
|---|---|
| **A. Teach every ledger-writing tool to take `--body-file`** | It is the right fix *per tool* and `tier_a_review_gate.py` already has it. But it is N fixes, it does nothing for a ledger with no tool, and it does not catch the whole-file-rewrite half at all. Rejected as the *only* measure; still worth doing per tool. |
| **B. A git pre-commit hook that rejects large diffs on ledger paths** | Catches incident 2 and nothing of incident 1, fires after the damage is in the index, and a size threshold is a guess. A hook is also platform-wide policy, which is not mine to set. **Kept as a possible second layer, routed.** |
| **C. This tool: a narrow writer that refuses structurally** | Catches both incidents at the moment of writing, needs no policy change, and is opt-in per call site. Chosen. |
| **D. Nothing; rely on the lesson being written down** | The lesson WAS written down — `--body-file` exists and its own comment says *"THE SHELL IS WHERE THE TEXT DIES, NOT THIS TOOL"* — and I did not use it. **A documented lesson that was already documented is not a fix.** |

### Security

- **Never evaluates its input.** Body text is read as bytes from a file handle
  or `sys.stdin.buffer`; no `eval`, no shell, no `subprocess` with `shell=True`.
- **Refuses to write outside the repo** — the target path must resolve inside
  `REPO`.
- **Does not create a ledger.** A missing target is `COULD NOT RUN`, because
  creating one is how a typo becomes a second ledger nobody reads.
- **Scrubs nothing and redacts nothing.** If a body carries a secret that is the
  caller's problem; silently editing a ledger entry would be worse.

### Data

- **Reads:** the target ledger, the body file or stdin, and `git diff --numstat`
  for the target.
- **Writes:** exactly one file, the target, atomically (`os.replace` over a
  sibling temp).
- **Preserves byte-for-byte:** everything before the insertion point.

### Test plan

Selftest arms, each with its negative half:

1. backticks in the body survive verbatim;
2. `$(...)` survives verbatim;
3. embedded single and double quotes survive;
4. **the `id`-output case** — a body containing `` `id` `` must still contain
   `` `id` `` afterwards and must NOT contain `uid=`;
5. **the 5681-vs-15 case** — a 200-record JSON ledger gains one record and the
   numstat added-lines count must be bounded by the entry's own line count;
6. **NEGATIVE: a body passed as an argument is refused** — there is no code path
   that accepts one;
7. **NEGATIVE: a mutated existing byte is refused** — a deliberately corrupting
   insert must be rejected, or arms 1–5 prove nothing;
8. a missing ledger is `COULD NOT RUN`, never a created file.

---

## 2. `tools/clone_health_check.py` — item 3

### Goals

Report, read-only, on the clone's own health: **`core.bare`**, whether
`git status` works at all, **every registered worktree against whether its
directory exists**, each one's last write, and **any claim naming it** — from
claims history, not git authorship.

**Why:** the clone was found with `core.bare = true`. Every `add`, `commit` and
`status` failed while **`git log` kept working**, so HEAD read normally and the
failure looked like a commit-message problem. There was no one command that
would have said *"this clone is sick, and here is which part."*

### Non-goals

- **Sweeps nothing.** 28 registered worktrees exist and every directory is
  present; removing another session's worktree is not a call a health report
  gets to make.
- **Does not fix `core.bare`.** It reports it. The fix is one line and belongs
  to whoever reads the report.
- **Not a claim tool.** It reads the claim history to attribute a worktree; it
  does not claim, release or validate.

### Alternatives considered

| alternative | why it lost |
|---|---|
| **A. Extend `sairn_status.py`** | That tool reports what each *session* says it is doing, out-of-clone. Clone health is a different subject and a different failure mode; folding them hides both. |
| **B. A pre-push gate that refuses on `core.bare`** | A gate cannot help: with `core.bare = true` the push machinery is the thing that is broken. A report that a human or another tool runs is the only thing that works in that state. **Noted as not viable, not merely rejected.** |
| **C. This tool, read-only, with a third state on timeout** | Works in the broken state, attributes worktrees to sessions, and refuses to guess. Chosen. |

### Security

- **Read-only.** No `git config --set`, no `worktree remove`, no `rmtree`.
- Every `subprocess` call carries an explicit `encoding='utf-8'` — the cp1252
  class this platform has paid for seven times.
- **Third state on timeout**: a git call that does not answer inside its bound
  is `COULD NOT TELL`, never folded into healthy. A health check that reports
  "fine" because it could not ask is the worst possible output.

### Data

- **Reads:** `git config --get core.bare`, `git status --porcelain`,
  `git worktree list --porcelain`, directory `stat` per worktree, and
  `chore(claims)` commit subjects.
- **Writes:** nothing.

### Test plan

1. `core.bare` is reported for both values, driven in a throwaway repo;
2. a registered worktree whose directory is GONE is reported ORPHAN;
3. one whose directory EXISTS is reported LIVE — the paired positive;
4. **NEGATIVE: a timeout is `COULD NOT TELL`, never `ok`**;
5. a worktree whose prefix appears in a claim is attributed; one that appears
   nowhere is `UNATTRIBUTED`, not `unowned`;
6. the tool exits non-zero when anything is unhealthy and 0 only when
   everything was actually checked.

---

## 3. `tools/dep_surface_check.py` — item 5

### Goals

Given a package and a target version: **statically enumerate every symbol this
repo uses from it**, install the target in a throwaway directory, **assert each
symbol resolves**, and report **X of Y per call site**.

**Why:** `firebase-admin@14.5.0` was recommended on *"0 of 248 suites changed
verdict"* plus a smoke test that loaded the module and listed its exports. The
smoke test passed under both versions because `initializeApp` survived — while
`admin.credential`, `admin.auth`, `admin.apps`, `admin.app` and `admin.database`
all became `undefined`. **A load-and-list is not evidence of no behaviour
change.**

### Non-goals

- **Not a test runner.** It answers "does the symbol exist", not "does the code
  still work". A symbol that exists and behaves differently is invisible to it,
  and that limit is printed.
- **Not an upgrade tool.** It installs into a throwaway directory and never
  touches `package.json` or `package-lock.json`.
- **Not transitive.** It checks the symbols *this repo* names, not the ones the
  package uses internally.

### Alternatives considered

| alternative | why it lost |
|---|---|
| **A. Run the full suite against the target** | Already done, and it is what failed: 248 suites did not cover the path. A suite can only report what it covers, and coverage is the variable. |
| **B. Read the package's own CHANGELOG / release notes for breaking changes** | Depends on the maintainer having written them and on the reader mapping them to *our* call sites. Useful input, not a measurement. |
| **C. A types/`.d.ts` diff** | Only works for typed packages and reports the package's whole surface rather than our slice — hundreds of irrelevant changes. |
| **D. This tool: our call sites, resolved against the target** | Bounded by what we actually use, mechanical, and it reproduces the known-bad case. Chosen. |

### Security

- Installs into `tempfile.mkdtemp`, never the repo, and **never with
  `--force`**.
- Resolution is done in a **child `node -e`**, so a package with a side-effecting
  entry point cannot touch this process.
- **No network assertion is made about the installed tarball** — `npm` integrity
  checking is relied on and that reliance is printed, not assumed.

### Data

- **Reads:** `api/`, `tests/`, `tools/` for `require('<pkg>')` and member
  access; the installed package in the throwaway dir.
- **Writes:** only inside the throwaway dir, removed in a `finally`.

### Test plan

1. **POSITIVE CONTROL, and it is the whole reason for the tool:** against
   `firebase-admin@14.5.0` it must report `credential`, `auth`, `apps`, `app`
   and `database` as **MISSING** and `initializeApp` as present;
2. **PAIRED POSITIVE:** against `firebase-admin@12.7.0` all six resolve, so arm
   1 is not passing because everything reports missing;
3. the static enumerator finds a member access it is given in a fixture, and
   does **not** match a same-named member on a different object;
4. an uninstallable version is `COULD NOT RUN`, never "all symbols missing";
5. per-call-site counts sum to the total.

---

## 4. `tools/rework_tracker.py` — item 10

### Goals

Count **rework events** over time, where an event is one of four named shapes:

| tag | shape |
|---|---|
| `COLLISION` | sandbox or shared-state collision between sessions |
| `HARNESS_STATUS` | a claim cited from a harness *"completed (exit code N)"* rather than a captured code |
| `AGENT_SCOPE` | a sub-agent or fork given full instructions, or writing shared state |
| `STALE_FIGURE` | a stale or reused figure later corrected |

Output **events per week and per batch**, plus a short report doc.

**My own seven mistakes from `docs/handoff-cody-2026-10-06b.md` are the first
test data** — which is the point: a tracker that cannot find known events is not
measuring.

### Non-goals

- **Not a blame tool.** It counts shapes and names the commit; it does not rank
  sessions. The postmortem in item 12 is blameless and this must not undo that.
- **Not a detector of new rework.** It reads what was already written down. A
  rework event nobody recorded is invisible, and that is the headline limit.
- **Does not judge severity.** A `STALE_FIGURE` that cost a minute and one that
  cost a run count the same, because weighting them is a judgement no regex has.

### Alternatives considered

| alternative | why it lost |
|---|---|
| **A. Count `no-defect-record:` trailers** | Measures *disclosure*, not rework, and would reward sessions that write fewer trailers. |
| **B. Count reverts and `--amend`s in git** | Catches a narrow slice. Most rework here is a *second attempt that was never reverted* — a corrected figure, a re-run at a higher bound. |
| **C. Hand-maintain a rework ledger** | It would go stale exactly like every hand-maintained list this platform has corrected, including the one `tool_owner_map.py` replaced. |
| **D. This tool: derive from five existing sources** | Every source is already written for another reason, so the data is not maintained for the tracker's benefit. Chosen. |

### Security

- **Read-only.** Writes exactly one report doc, and only when asked.
- No network. No subprocess except `git log`, with an explicit encoding.
- **Never attributes to a person** — sessions are build agents.

### Data

- **Reads:** hover-audit-log entries, `git log` subjects and bodies,
  `docs/tier-a-reviews.json`, the red-suite register,
  `docs/defect-density-register.json`.
- **Writes:** one dated report doc.

### Test plan

1. **Each of the four tags fires on a hand-built fixture string**;
2. **NEGATIVE per tag:** a near-miss string does NOT fire — e.g. the phrase
   "exit code" inside prose *about* the harness-status rule must not count as an
   instance of it, or the tracker will count its own documentation;
3. **the seven known events from my handoff are found**, by tag;
4. a source that cannot be read is `COULD NOT RUN` for that source and is named,
   never silently zero;
5. weekly and per-batch buckets sum to the total.

---

## WHAT THESE FOUR DO NOT COVER

- **`ledger_append.py` cannot stop a wrong record**, only a wrong *write*.
- **`clone_health_check.py` cannot say who broke the clone** — attribution of
  `core.bare` is item 4 and is explicitly undetermined.
- **`dep_surface_check.py` cannot see a symbol that still exists and behaves
  differently.** That is the next class after this one, and it needs a suite.
- **`rework_tracker.py` cannot see unrecorded rework**, which is most likely the
  majority.
