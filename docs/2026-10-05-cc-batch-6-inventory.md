# CC batch 6, 2026-10-05 — seq 486 landed for real, one of the two was latent, and the tool I accused was right again

**Every figure measured at HEAD. Every exit code read with output redirected and
the status taken on its own — the lesson this batch also built a check for.**

Methodology: **every screen reports its blind-spot count on its last line.**

---

## 1. What landed

`17343958` — one commit, nine files. Closing invariants, each read with the
status alone:

| | exit |
|---|---|
| `tools/md_table_check.py` | **0** |
| `tools/cron_beat_refusal_check.py --fixtures` | **0** (6/6) |
| `tests/run_cron_beat_refusal_probe.py` | **0** (23/23) |
| `tests/run_md_table_check_probe.py` | **0** (41 cases) |
| `tools/exit_status_attributable.py --selftest` | **0** |
| `tools/doc_checker_coverage.py --selftest` | **0** |
| `tests/run_fail_open_probe.py` | **0** (22/22) |
| `tools/tooling_inventory.py --check` | **0** |
| `api/law-auth-custody-matter-attribution.test.js` | **0** (19/19) |

---

## 2. seq 486 was right on **both** counts, and I had reported both discharged

Both were written up on 2026-09-29 and **neither landed in code**, so the record
and the behaviour disagreed for six days. The two are **not** equally severe and
saying so is part of the fix.

### 5a — the trailing comment. **LIVE.**

`cron_beat_refusal_check.py` kept `i <= auth` beside the structural test, and
`auth_line()` returned the **last** auth marker anywhere in the file, comments
included.

**Driven before fixing.** A handler whose post-auth 502 is a genuine FINDING
reports `FINDING`. Append one line —

```
// NOTE: callers must send CRON_SECRET in the Authorization header.
```

— and the **same handler** reports `pre-auth refusal -- must NOT beat`. **One
comment, a real monitoring gap erased, and the tool says CLEAN.** `PR §1.11` in a
checker rather than a gate.

**Fixed** by excluding comments from the fallback boundary, through
`tools/jscomments` rather than a regex of my own — that module already handles
the case a hand-rolled stripper gets wrong, a `//` inside a string literal. **And
it fails toward the stricter answer:** if the stripper cannot run, or returns a
different line count, the fallback is **dropped entirely** rather than guessed,
so a stripper outage cannot hide a finding. The structural `own_auth` test is
untouched — comment-proof by construction, and it carries the real work.

**Proven five directions:** FINDING stays FINDING; a trailing `//` no longer
flips it; a trailing `/* block */` no longer flips it; the real pre-auth 401
stays correctly clean; a handler carrying an `https://` literal is not
mis-stripped.

**A trailing-comment fixture is added at the head of the lock**, because the
reason this survived a report of its own fix is that nothing held it. **My first
two expectations for that fixture were wrong** — a bare verdict string, then a
comma-joined one — and the lock rejected both before they landed; it compares a
list. *The fixture found my error before I could call it green, which is what a
lock is for.*

### 5b — the `marker` exemption. **LATENT, and that is stated rather than dressed up.**

`fail_open_scan.py`'s `SCOPE_WORDS` carried a bare `marker` alternative matching
anywhere on a line, **including inside a tool filename**.

**Driven:** `[ -f "$ROOT/tools/staged_conflict_marker_check.py" ] || exit 0` — a
**dependency** test, which must be reported — was classified SCOPE and exempted,
while the otherwise identical `staged_conflict_check.py` line was not. **Two
identical guards, different verdicts, decided by a filename.**

**And it was not live.** Measured by running the scan **both ways**: the report is
**byte-identical** with and without the word, and a sweep of every *non-comment*
guard line in `.githooks/` and `scripts/` finds **zero** that relied on it. The
one real instance sits inside a comment block the scan already masks. **A loaded
gun with no current target** — what the fix closes is the next tool whose
filename contains the word.

**Removing it is free, not a trade:** the genuine scope tests match on
`.git/sairn-hover-clone` and `auditor-clone`, never on the bare noun. Proven
three ways — dependency guard no longer exempt, hover-clone still exempt,
auditor-clone still exempt.

**The shape is the lesson and it is recorded in place:** every surviving
alternative is hyphen-anchored, path-anchored, or a word whose only reading *is*
applicability. **A bare noun that can appear in a filename is the shape to
refuse.**

**A pre-existing regression I am not claiming:** the scan reports *"dependency
fail-opens rose from 17 to 19"*. It said that before my change too — the
before/after diff was empty — so it is **live, real, and not mine**.

**BLIND SPOTS: 3.** (1) The cron fallback is now dropped on a stripper failure,
which will report refusals `own_auth` alone cannot classify — a false-positive
direction I prefer and have **not** measured. (2) The 17→19 fail-open regression
is unexamined. (3) Both of these were found by an **auditor re-raising them**, not
by any check of mine; nothing here closes the gap of a tool reporting a fix it
never made.

---

## 3. The `| | |` row — and **the tool I accused was right, again**

**Found by my own `doc_checker_coverage.py` on its first run.** Fixed by giving
that timing table a real header.

**And it corrects a finding I logged against `md_table_check` yesterday.** I had
reported `111/110 rows checked` as an **off-by-one in the tool's coverage pair**
and declined to add the file rather than relax the probe arm that asserts the two
agree.

**The tool was right and the document was wrong.** Line 2008 was `| | |` —
nothing but pipes and spaces, so `SEPARATOR` matched it: counted one way,
tallied the other. With a real header the pair agrees at **111/111** with zero
findings. **There was no accounting defect; there was a malformed row, which is
exactly what that tool exists to say.**

**That is the second time in two days I have accused `md_table_check` of a defect
it did not have** — first the false "exits 2", now a false off-by-one. Both times
the measurement I had not taken was the cheap one.

**So the file is now in `DEFAULT_FILES`: seven files, 2,301 rows, 41 probe
cases.** And the sequence is the point: **declining to relax the arm is what left
the real cause findable.** Relaxing it would have admitted the file, gone green,
and buried a malformed row in a standing document.

**BLIND SPOTS: 2.** (1) I checked **one** file for the all-pipes row shape;
whether the other six standing files carry one is unmeasured. (2) The arm I
declined to relax asserts `checked == looks`, which I now know can be broken by a
document rather than by the tool — so a future genuine tool-side off-by-one and a
malformed row will present identically.

---

## 4. `git log -S` will surface the stale claim forever — the pointer is now in the doc

`-S` matches text a commit **adds or removes**. No later commit adds that exact
uppercase phrase, so **no correction can ever appear in that result set.** It is
not a thing to fix; it is a thing to warn about.

`docs/2026-10-05-cc-batch-5-inventory.md` now carries a blockquote addressed to a
reader who arrives that way, with the two `--grep` commands, and the rule that
generalises:

> **`-S` answers "which commit introduced this text", never "is this text still
> true".** A claim withdrawn in prose is invisible to it by construction, so a
> `-S` hit on an assertion is a lead to check, not a fact to quote.

**BLIND SPOTS: 1.** The warning only helps a reader who reaches *that document*.
Somebody who reads `51548ec9` in isolation still needs `--grep`, and the git note
that would have told them in place is local to this clone — the push gate
correctly refuses a notes ref whose base it cannot resolve.

---

## 5. The standing check for my own reading error — `tools/exit_status_attributable.py`

Both errors were **one shape: a status read off the wrong subject.**

1. A tool piped into `tail` inside an `&&` chain → exit 2 → I wrote
   *"md_table_check.py EXITS 2 (COULD NOT RUN)"* into a standing index and a
   commit message. **It exits 0 and has no path returning 2.**
2. A **no-op** push printed a refusal-shaped gate message → I read it as a
   refusal of my push. `rev-list --left-right --count` answered `0 0`.

**The hazardous half is decidable from the command text and needs no intent
inference:** a pipeline or an `&&`/`||` chain returns **one** status, and it is
not the status of the program you named.

It **names the owning element** rather than merely refusing — *"the status will
come from `tail`, a text filter, which exits 0 for 'I ran' and says NOTHING
about the program before it"* — and prints the measurement that would be sound.
Splits on **raw text** rather than shlex tokens (shlex splits on whitespace, so
`a;b` arrives as one token — the same reason `git_push_master_guard.py` splits on
text) and skips leading `VAR=value` assignments so `SAIRN_SEED_GATE=off git push`
is attributed to **git**.

**Selftest drives both directions and includes both real commands verbatim in
shape**, plus three attributable controls so it is not simply reporting
everything as hazardous. Fails closed at exit 2 on a command it cannot tokenise.

**It worked on me the same day.** A push in this batch failed with *"the outgoing
range … could not be read"*. I checked `git status -sb` **first** — `ahead 1,
behind 1` — rebased, and it pushed. **Last time I read a push message like that
as a refusal of my work; this time I measured the specific thing.**

**BLIND SPOTS: 3.** (1) **Unwired.** Wiring needs `.claude/settings.json`, which
every clone shares, and a hook naming a tool on no commit yet would fail in four
other clones — that decision is not taken as a rider. (2) It **cannot** see the
second half of error 2 — that a no-op push produces a refusal-shaped message —
because nothing in the command text says whether there is anything to push; named
and not claimed. (3) It judges *attributability*, never whether the conclusion
drawn was right.

---

## 6. seq 464/467 — re-verified at HEAD rather than assumed

Applied in `c6d66c11` last batch. Re-driven here:

| Planted | Result |
|---|---|
| the `+=` variable build, licence scope intact | **only the canary reddens** — exactly what its own text says should happen |
| a genuinely **unscoped** lookup | **three arms red**, including the substantive licence-scoping one |

`api/law-auth.js` byte-identical after both; 19/19 at HEAD.

**BLIND SPOTS: 1.** The other two move-proofed files (`dental-gfe.test.js`,
`cron_schedules_do_not_collide.js`) are still **not** driven against a planted
refactor.

---

## 7. Left alone, as directed — claims re-checked fresh first

`python tools/sairn_claim.py list` at batch start: **cody held
`docs/tier-a-reviews.json`** (reviews9) and nothing else was active. Neither
`citation_line_drift_check.py`, `push_retry.py` nor `schema_provisioning_check.py`
was held at that moment — **but all three were left untouched anyway**, because
the instruction named them and a claim rotating off is not permission.

**Rows 82 / 845** — hank has not delivered the paste-ready text. Untouched.

**BLIND SPOTS: 1.** The claim record is only as fresh as the last push to it, and
I read it once at the start rather than before each file.

---

## 8. What this batch did NOT do

* **No wiring** of `exit_status_attributable.py`, `doc_checker_coverage.py` or the
  seam watch.
* **No work on the 17→19 fail-open regression**, which is live.
* **No sweep** of the other six standing files for an all-pipes row.
* **No SAIRNbiz click-through**; finding 13 still open and unfixed.

**BLIND SPOTS: 1.** This is what I know I did not do; it cannot cover what I did
not think to check.
