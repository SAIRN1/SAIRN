# Tier A review — DISCHARGE of hover2's retrospective obligation (`leg_insurance`, `mech_checks`)

**Obligation:** author `hover2` (corrected in the opening commit; **opened by
`hank` on hover2's behalf** because the auditor's own scope gate refuses
`docs/tier-a-reviews.json` from the auditor clone), opened
`2026-09-30T13:59:56Z`, resources `leg_insurance`, `mech_checks`, file
`.claude/skills/sairn-hover-auditor/tools-hover2/hover_citation_linter.py`,
change `c78b545b` *"sync 6 fixed tools to the platform-repo backup"*.
**Assigned to `fourth`; held 339 hours — 14 days — at discharge.**
**Reviewer:** fourth, 2026-10-14, batch b19.

**ELIGIBILITY, because this obligation names its reviewer by ROLE rather than
by agent.** It requires *"any build session other than the author of the
change, holding no claim on `.claude/skills/sairn-hover-auditor/` at the time of
review"*, and it explicitly excludes **both** hover instances. I am a build
session, I did not write the linter, and **my b19 claim declares
`docs/` only and names the auditor skill tree READ-ONLY.** Eligible.

**AND THE BOUNDARY WAS HELD, WHICH IS ITSELF PART OF THE VERDICT.**
`C:\Users\marsh\Documents\SAIRN-hover` was **never entered** — not read, not
listed, not `cd`-ed into. Everything below is against **this clone's mirror** at
`.claude/skills/sairn-hover-auditor/tools-hover2/`, which is a tracked path in
the platform repo and is exactly what the change under review put there.

---

## 0. THE RECORDED COMMIT RESOLVES — this is a REAL DIFF REVIEW

Stated first because it is the opposite of the other two obligations I have
discharged this week:

```
CMD git cat-file -e 82b69588a125e9b730cfafeb5a95e29aee55f5a1   ->  RESOLVES
CMD git cat-file -e c78b545b                                   ->  RESOLVES
```

**Both the `opened_at_sha` and the change's own commit are in this clone's
object store.** So unlike b18's queue14 (dangling) and b19's queue16 (dangling,
weak candidate), **this review is not bounded by a missing commit.** The one
bound it does have is named in §4.

---

## 1. WHAT I OPENED, AND WHAT I LOOKED FOR

**The obligation's own words: *"WHAT THE REVIEW MUST DRIVE, NOT READ"*, and
*"a verdict of 'reviewed, no findings' is refused unless it names what it opened
and what it looked for."*** So both, concretely.

| what I opened | what I looked for |
|---|---|
| **`hover_citation_linter.py` in full — 701 lines** (`wc -l` → 701), its module docstring, its CLI dispatch, and every function | whether it is auditor tooling only; **every construct that could mutate state outside the process** |
| the same file's `selftest()` body and its three `subprocess.run` argv lists | whether running it writes anything, and **where** |
| `hover_log.py` in the same directory, module level only | whether the linter's `import hover_log` has a file side effect (it is imported inside `selftest()`) |
| every occurrence of the strings `leg_insurance` and `mech_checks` in the file | whether either name is in a **write path** or only in a **fixture literal**, which is what the obligation asserts |
| every read site and every path constant in the file | whether it reads platform data — anything under `api/`, `sql/`, `*.html`, platform `docs/` |
| **the tool itself, RUN, four ways** | that the three claims above hold **in execution**, not only in reading |

### The four drives, with their real exit codes

| # | invocation | exit | what it proves |
|---|---:|---|---|
| **D1** | `--lint --target "leg_insurance" --text "per seq 275 this still holds, 122 of 122 rows carry it"` | **0** | the full lint path end to end, on the exact resource name the obligation is about |
| **D2** | `--selftest` | **0** | **33 ok, 0 failed** — the fixture lock, including five arms labelled KNOWN-BAD CONTROL |
| **D3** | `--lint --target x --file <a path that does not exist>` | **2** | **fail-closed, verified in practice:** `COULD NOT RUN: FileNotFoundError` — not 0, not a silent skip |
| **D4** | no arguments | **0** | prints the docstring and touches no file at all |

**D1's real output, quoted because it is the evidence the drive happened:**

```
  seq 275    UNVERIFIED-CROSS-LOG seq 275 exists in the OTHER auditor's log, not
             this one -- this tool cannot check a citation it does not own; read
             it there before trusting this citation
  count 122  STALE  '122 of 122' does not match the current pool size (116) --
             recompute before logging
  (1 citation(s) UNVERIFIED-CROSS-LOG -- counted separately, never passed as
   clean or failed as missing)
ADVISORY: one or more candidates above -- read them in context before trusting
          this draft; this is a heuristic, not a verdict.
LINT-TOKEN: 482dabe28893bef6
```

**That is a tool behaving well under review.** `UNVERIFIED-CROSS-LOG` is a third
state, counted separately and *"never passed as clean or failed as missing"*;
the staleness verdict is computed against a **live** pool size (116), not a
hardcoded one; and the whole report is labelled **ADVISORY, a heuristic, not a
verdict**. The file says the same in its own header — *"a standalone advisory
tool, not a hard gate"*.

### The integrity check on the drive itself

```
CMD sha256 of hover_citation_linter.py BEFORE the four drives  ->  c226563783a8e56e
CMD sha256 of hover_citation_linter.py AFTER  the four drives  ->  c226563783a8e56e
CMD git status --porcelain BEFORE / AFTER
    -> only `?? docs/batch-manifest-fourth-b19.json`, which is mine
```

**Nothing in the auditor tree changed, and nothing in the working tree changed.**
That is the mechanical form of "read-only toward platform data", and it is
checked rather than asserted.

---

## 2. THE THREE THINGS THE OBLIGATION ASKS — each answered

### 2.1 "auditor tooling only" — YES

The module's own purpose line: *"the standing self-check scoped and justified in
`docs/2026-09-29-hover-gap-research-h2.md`'s third pass: a deterministic,
non-LLM pre-flight check against Class A of this role's own real, counted
mistakes this session"*. It implements exactly two checks, both named in the
header — **repeated-count staleness** and **backward seq-reference target
mismatch** — and the header explicitly refuses to oversell them (*"WHAT THIS
ACTUALLY CATCHES, STATED NARROWLY, NOT OVERSOLD"*).

Its CLI is three forms: `--selftest`, `--lint --target … --file …`,
`--lint --target … --text …`. There is no other mode. **There is no `git`
anywhere in the file** — `grep -n '\bgit\b'` → **zero matches** — so there is no
`git checkout` / `git stash` / `git reset` question to answer.

### 2.2 "READ-ONLY toward platform data" — YES, and this is the precise answer

**It is not write-free. It is write-free toward platform data, and the
distinction is the finding-shaped part of this review, so it is spelled out
rather than summarised.**

**Every write construct in the file lives inside `selftest()`. The `--lint`
path and every importable function write nothing.** Exhaustively:

| construct | verdict |
|---|---|
| `tempfile.mkdtemp()` | **WRITES** — a new directory under `%TEMP%` |
| `io.open(draft_path, 'w', …)` + `f.write('a real draft with a real trailing newline\n')` | **WRITES** — `<that tmp dir>/draft.txt` |
| `tempfile.mkstemp(suffix='.jsonl', prefix='citelint_2745_')` + `os.fdopen(_fd, 'w', …)` + `_f.write(...)` | **WRITES** — a fixture file under `%TEMP%` |
| `os.remove(_fixpath)` inside a `finally:` | **DELETES** — only its own `mkstemp` fixture |
| three `subprocess.run([sys.executable, os.path.abspath(__file__), '--lint', …])` | **READ-ONLY** — re-invocations of *this same file* on the `--lint` path; one deliberately points at a nonexistent file to drive the fail-closed arm |
| `sys.path.insert(0, HERE)` then `import hover_log` | in-process only; `hover_log`'s module level is constants and regexes with its CLI behind `if __name__ == '__main__':`, so **no file side effect** |

**ABSENT ENTIRELY**, established by grep rather than by reading: no `shutil.*`,
no `os.makedirs` / `os.mkdir`, no `os.rename` / `os.replace`, no `rmtree`, no
`pathlib` at all, no `json.dump(` to a file (only `dumps` to a string), **no
network of any kind** (`requests|urllib|http://|https://|socket` → no matches),
no `os.system` / `popen`, no `chmod`, no `chdir`, and **no `sys.stdout`
redirection** — every output is a bare `print()`.

**The three writes are all under the OS temp directory. None touches a repo
path, a platform file, or any path under either auditor clone.** So the
obligation's phrase is satisfied in the strong form: *platform data* is never
written.

**F1 — the one real defect, and it is small and honest to name: `--selftest`
leaks a temp directory on every run.** The `finally:` removes only the
`mkstemp` fixture; the `mkdtemp()` directory and the `draft.txt` inside it are
**never removed**. Outside any repo, zero risk to platform data — **and still a
residual write on every run of a tool whose whole subject is self-discipline
about evidence.** Two lines of `shutil.rmtree(tmp2, ignore_errors=True)` in the
same `finally:` closes it. **ROUTED TO hover2**, lowest severity in this review.

### 2.3 "constructs no write to `leg_insurance` or `mech_checks`" — YES, and the obligation's own description of where they appear is VERIFIED

Nine occurrences, all of them data or prose. **Not one is in a path, a read
target, a SQL statement, or a write:**

* **1 in the module docstring** — prose citing the real seq 274/275 history.
* **2 synthetic fixture literals** — `{'seq': 274, 'target': 'leg_insurance'}`
  and, the file's only `mech_checks`, one comma-token inside a longer target
  string `'upstream-of-money-sweep,mech_checks,leg_keepsakeorders,…'`.
* **3 as the `current_target` argument** to `check_seq_refs(...)` in test arms.
* **3 inside test *name* strings.**

The obligation says they appear *"as short string tokens inside
`hover_citation_linter.py`'s fixtures"*. **Verified exactly.** Both names flow
only into `check_seq_refs()`, which does set-intersection on tokens and returns
strings — **no SQL, no table access, no HTTP, no file write.**

**And the fixture is frozen on purpose, for the reason this review would have
asked for:** *"the real target strings captured from the live log the day this
arm was written are frozen here as a synthetic fixture, written to a real temp
file and read via `load_rows(path=…)` explicitly — never the default, never any
real log, from any location."* **That is a probe refusing to depend on live data
it cannot control, which is the ninth cross-domain convention done right.**

---

## 3. WHAT IT DOES READ — and none of it is platform data

Four read sites, all plain text, all `io.open(..., encoding='utf-8')` with no
mode argument:

| path | what it is | state in this clone |
|---|---|---|
| `LOG_PATH` = `<HERE>/hover-audit-log.jsonl` | the auditor's **own** log, beside the tool | **does not exist here**, and the guard returns `[]` rather than raising |
| `DEFAULT_TIERS` = `SAIRN-hover2\docs\CRITICALITY-TIERS.md` | the **auditor's own** criticality register | exists; this is where D1's live pool size of **116** came from |
| `H1_LOG_PATH` = H1's log under `.claude/projects/…SAIRN-hover\hover-audit-log\` | **the other auditor's log, read-only by explicit contract** — *"never written to, never trusted as this tool's own chain"* | exists; **I did not open it myself**, and the tool only reads it |
| the operator's `--file` draft | whatever text is being linted | supplied per run |

**`grep -n 'api/\|sql/\|\.html\|docs/\|\.sql\|\.js\b'` over the file yields
exactly two hits, both citations inside the docstring, neither a path.**
**Nothing under `api/`, `sql/`, `*.html` or platform `docs/` is read at all.**

**One thing worth saying plainly rather than scoring as a finding:** the file
hardcodes two absolute Windows paths into *other* clones
(`C:\Users\marsh\Documents\SAIRN-hover2\…` and the H1 project path). That is
brittle across machines, it is **inside the auditor's own scope**, and it is not
mine to route as a platform defect. It is noted because a reader of this verdict
should know the tool's behaviour is **environment-dependent**: `--selftest`'s
historical-regression arm re-derives the pool size live and **counts the no-op
case as a FAIL rather than a skip** (*"an undriven regression proves nothing"*),
so that arm turns red if the hover2 register goes missing or if its Tier-B row
count happens to equal 123. **That is the right trade and it is declared; it
also means a green 33/33 here is partly a statement about my machine.**

---

## 4. VERDICT

**NO FINDING AGAINST THE PREMISE OF THE CHANGE. `hover_citation_linter.py` is
auditor tooling only, is read-only toward platform data, and constructs no
write to `leg_insurance` or `mech_checks`.** Verified by reading all 701 lines,
by exhaustive grep for every write and network construct, and by **four real
drives whose exit codes are 0 / 0 / 2 / 0** — with the file's own sha256 and the
working tree both unchanged before and after.

**ONE FINDING, F1: `--selftest` leaks one temp directory and one file per run.**
hover2's, lowest severity, two lines to fix.

**THE PREMISE THE SKIP CLAUSE RESTS ON IS CONFIRMED.** The obligation says this
is *"the same premise the `SKIP_REASONS` auditor-tree clause landed today rests
on, checked against a file that landed before the clause existed."* **That
premise holds for this file:** a tool in the auditor tree that reads only
auditor logs and its own fixtures, writes only to `%TEMP%`, and names platform
resources only as frozen fixture tokens is correctly skipped by a platform
gate. **What this review does NOT establish is that the premise holds for the
other five tools in `c78b545b`** — see below.

### What this discharge does not claim

1. **It covers ONE file.** `c78b545b` synced **six** tools. The obligation's
   resource list was derived from this one file, and this review opened this one
   file. **The other five are not reviewed and are not blessed by this verdict.**
   That is the bound on this review, and it is the analogue of b18's lesson: an
   unreviewed part of a change that nobody names reads as reviewed.
2. **It did not enter the auditor clone.** Everything is from this clone's
   mirror. If the mirror has diverged from `Documents\SAIRN-hover2`'s working
   copy, **this review is about the mirror** — which is the artefact the commit
   under review actually created, so that is the right subject, but it is not a
   claim about the auditor's live copy.
3. **It did not read H1's log.** The tool reads it; I did not. So *"read-only
   toward H1's chain"* is verified **from the call sites and the absence of any
   write construct**, not by inspecting that file.
4. **No platform file was modified and no SQL was run.** `docs/` only, plus the
   register write the discharge itself makes through the gate.
5. **It does not re-open the separation question.** Whether a tool belongs in
   the auditor tree at all is `docs/2026-09-15-hover-auditor-separation-
   enforcement.md`'s subject, not this verdict's.

**THE ONE THING WORTH KEEPING, and it is a credit rather than a finding:** this
tool does three things the platform asks for and rarely gets — it **names a
third state** (`UNVERIFIED-CROSS-LOG`, never folded into pass or fail), it
**fails closed with exit 2** on a missing input rather than printing zero
findings, and it **counts a skipped regression as a failure** on the explicit
ground that an undriven regression proves nothing. **Those are the three
conventions this review would otherwise have been written to enforce, already
implemented by the subject.**
