# Routed from fourth (ted) to cody — 2026-10-13, batch b9

Three things, all in `tests/`, which is yours by the directory rule Michael gave
this batch. **Nothing here was fixed by me** — one of the three is a suite that
reports green while printing a crash, and a build agent editing somebody else's
fault-injection harness to make a symptom go away is how the symptom gets lost.

---

## 1. `tests/run_tier_a_review_gate_probe.py` EXITS 0 WHILE PRINTING TWO REAL TRACEBACKS

**Repro, one line:**

```
python tests/run_tier_a_review_gate_probe.py
```

**Measured 2026-10-13 at HEAD `94e608a4`: exit 0, last line `ALL ARMS PASS`, and
THREE tracebacks in the output.**

**ONE OF THE THREE IS YOURS AND IS CORRECT** — the probe plants a crash on
purpose to exercise the COULD-NOT-TELL path, and the output says so:

```
COULD NOT TELL -- the Tier A review gate raised an unexpected exception, so NOTHING WAS CHECKED. This is NOT a pass, and it is NOT a finding either:
  RuntimeError: planted crash
```

That one is the probe working. **THE OTHER TWO ARE NOT PLANTED.** Full lines,
verbatim:

```
PermissionError: [WinError 5] Access is denied: 'C:\Users\marsh\AppData\Local\Temp\owner6-5ilug6yk\atomic.json.tmp-xt1tfxjf' -> 'C:\Users\marsh\AppData\Local\Temp\owner6-5ilug6yk\atomic.json'
PermissionError: [WinError 5] Access is denied: 'C:\Users\marsh\AppData\Local\Temp\owner6-5ilug6yk\atomic.json.tmp-uzyuma5j' -> 'C:\Users\marsh\AppData\Local\Temp\owner6-5ilug6yk\atomic.json'
```

An atomic write — `os.replace` of a `.tmp-*` onto `atomic.json` — denied twice in
a throwaway temp directory. On Windows that is the ordinary shape: the
destination is still open, or a scanner holds it for the instant the rename
happens, so the atomic-replace idiom that is correct on POSIX fails
intermittently here.

**WHY THIS IS ROUTED RATHER THAN FIXED, and it is the whole point:** the suite
**exits 0** and prints **ALL ARMS PASS** with those in its output. So either

* the two arms that exercise the atomic write caught the exception and passed on
  a path that did not test the atomicity — a green arm over an unperformed
  check, which is the platform's most expensive shape; or
* the exceptions are printed from a non-asserting helper and no arm was affected,
  in which case the output is noise and should say so.

**Which of the two it is cannot be told from the outside**, and the difference
matters: the first is a defect in a Tier-A review gate's own probe.

**EXACT NEXT STEP:** find the two arms that touch `atomic.json`, and make the
`PermissionError` path either (a) fail the arm, or (b) print `COULD NOT RUN` and
be counted apart from pass and fail — the third state this probe already
implements correctly for the planted crash. **An exit code and an output that
disagree is the thing to close, not the Windows rename.**

---

## 2. `tests/seam_check/run_delegation_probe.py` — THE FAIL-OPEN RESTORE, FOUR LINES

Routed since b6 and unchanged. Carried again because it is the mechanism behind
a measured incident rather than a tidiness note.

| line | what is there | why it is a fail-open |
|---|---|---|
| `:76` | `subprocess.run(['git','checkout','--',p], cwd=REPO, capture_output=True)` in the atexit net | the return code is never read |
| `:113` | the same call in the context manager's `finally` | same |
| `:80` | `os.remove(SENTINEL)` in the atexit net | runs whether or not the checkout landed |
| `:119` | `os.remove(SENTINEL)` in the context manager | same |

**MEASURED IN b5, not theorised.** With `core.bare = true` set in the clone — which
`tests/push_gate/check8_probe.py:209` records a dry-run push as "reliably
leaving behind" — **every `git checkout` fails silently**, so the restore does
nothing and the sentinel that exists to leave evidence of a failed restore
**removes itself anyway**. b5 found `api/sd-data.js` missing
`, warn_days: gateWarn` and `api/_lib/subcontractor-compliance.js` failing
`node --check` with `SyntaxError: Identifier 'today' has already been declared`,
with the sentinel absent.

**AND THE THREE LAYERS SHARE A DEPENDENCY, which is why all three failed at
once.** The probe's own header describes a context manager, an atexit net and a
sentinel as three layers; all three are built on `git`, and in a clone where
`git` cannot operate there is one layer, not three. **A layer is not independent
of another layer if they share a dependency.**

**EXACT NEXT STEP:** read the return code at `:76` and `:113` and fail loud on
non-zero; remove the sentinel at `:80` and `:119` only after the restore
verifies. b7 drove this probe with `core.bare = false` and it restored both files
perfectly, so the code is right when git works — the defect is only what it does
when git does not.

---

## 3. THE 34 seq 17-A FINDINGS IN `tests/` ARE YOURS BY THE DIRECTORY RULE

`docs/2026-10-13-ted-seq17a-owners.tsv` — 36 rows, one per finding, of which
**34 are under `tests/`** and 2 under `tools/` (cc's). Every row carries the
site, the line, the ordinal within the site, the subject class, the owner and
the basis.

**THE SUBJECT OF EVERY ONE IS NOW VERIFIED AT HEAD** — 3 sites in b4, 16 in b8,
the 4 WITHDRAWN rows in b9, so 23 of 23 — which means the classification is not
the open question any more. The findings themselves are.

**Two rows are worth taking before the rest and the TSV says so per row:**

* `tests/sairnlegacy_session_gate_review_probe.js:202` — its own comment records
  that its first spelling *"could never have matched and the arm was vacuous in
  the reassuring direction"*. A site with that history is the one most likely to
  have it again.
* `tests/seed_never_syncs_platform.js:274` — records switching to `indexOf`
  because a constructed regex *"silently matches nothing"*. Same reason.

**THREE CITATIONS MOVED and the TSV carries the correction rather than the
original:** `tests/sairncode_gates.js` should be cited `:301-303` (`:301`
declares the regex, `:303` makes `m[1]` the subject), and the two
`tools/citation_drift_hook.py` rows should cite `:406` for the subject, where
`lines` is bound — `:411` and `:416` only consume it.

**AND TWO MORE MOVED BECAUSE OF ME.** The WITHDRAWN rows at
`tests/faults/grd_write_faults.js:385` and `:396` are now at **`:403`** and
**`:417`**: b5's stripper consolidation inserted 18 lines of comment above them.
Both reasons still hold — `:403` is `const code = stripComments(SRC)`, so the
"already stripped" reason is now STRONGER because the strip is the shared
implementation rather than the private regex the row described; `:417` is still
`const fake = 'function f(){ cmSavePoints(z); }'`, a literal in a control arm.
**I moved those lines, so the stale citation is mine and this is the
correction.**
