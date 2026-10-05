# CC batch 7, 2026-10-05 — the 17→19 rise was mostly relocations, and the cheap measurement is now a rule

**Every figure measured at HEAD. Every exit code read with output redirected and
`$?` on its own line.** The attribution hook wired in this batch now says that
out loud on every command that needs it.

Methodology: **every screen reports its blind-spot count on its last line.**
§8 names the *cheap measurement not taken* pattern as its own lesson, which is
what this batch was asked to do and what it kept demonstrating.

---

## 1. What landed

| sha | What |
|---|---|
| `16e122dd` | The fail-open rise diagnosed; hook pipeline hardened; the ratchet now records **names** |
| `0e9419bd` | Both instruments **wired**; rows 82 and 845 applied; the attribution hook's **literal-backspace** defect |
| *(this commit)* | `PR §2.6` and `§2.7` as standing rules; this inventory |

---

## 2. The 17→19 fail-open rise: **seven relocations and two real sites**

Diagnosed by running the *same* scanner against the tree as of the baseline
commit in a throwaway worktree and diffing the site lists. **Nine entries looked
new. Seven were the same guard at a moved line number:**

| guard | was | now |
|---|---|---|
| `deploy_verify_notify.py` | 95 | 195 |
| `master_plan.py` | 251 | 257 |
| `push_retry.py` | 490 | 694 |
| `sairn_claim.py` | 1483 | 1844 |
| `sairn_push_gate_hook.py` | 781 | 812 |
| `sairn_push_gate_hook.py` | 832 | 863 |
| `.githooks/pre-commit` | 51 | 102 |

**Two were real:** `tools/gh_token.py:296` and `.githooks/pre-commit:70` — and
the second also took `hook_failopen` from **0 to 1**, which the headline never
said because it reported only the dependency count.

### So the real defect was that the ratchet could not name what rose

It pinned **counts**. A refactor that moved a line read identically to a new
fail-open, and the two that mattered were unfindable without bisecting. It said
*"rose from 17 to 19"* for over a week and nobody could act on it.

**Fixed by recording the site set, keyed on (file, shape) and not on a line
number**, with ADDED and REMOVED reported **by name**. Same lesson as
`seam_cannot_tell_watch.py` built eight hours earlier for the identical reason:
**the names are the point, not the count.**

**Driven three ways:** a padding line that shifts every guard below it → exit 0,
*"no worse than pinned"*; a genuinely new bare-except → exit 1 and
`+ tools/sairn_http.py :: bare-except-pass`; a pin with no site list **says so**
and falls back to the count rather than inventing a set.

### Site 1 — `.githooks/pre-commit:70`, and it is my own reading-error class

One pipeline with `|| true` on the end, which applies to the **whole pipeline**
and swallowed two different answers as one: grep exiting 1 on no match
(legitimate, and the reason the `|| true` was there) and **`git diff --cached`
failing** (not legitimate — "could not check"). The hook then saw an empty list
and **skipped the live-probe-residue audit in silence.** From a hook that is a
pass nobody performed.

**A status read off the wrong subject, in the highest-consequence place on the
platform** — which is the sweep item asked for, found inside the fail-open
investigation rather than separately. git's status is now checked on its own and
refuses with a reason; grep's is discarded deliberately and only where "no
match" is correct. Driven three ways.

**The shape stays flagged and that is correct.** `|| true` on a grep is still an
exit-0-on-failure shape a human should see; what was removed is the hazard, not
the shape. So the pin moved to **18 deliberately** rather than being chased back
to 17.

### Site 2 — `gh_token.py:296` was never a defect

A classification miss. The swallow is scoped to parsing an optional login out of
a 200; the credential answer is the HTTP status and is returned regardless. The
comment already said so — just not in the words the `DOCUMENTED` regex reads.

**And my first attempt at that comment did not work**, which is the useful half:
the classifier reads a window of `ln-6 .. ln+3` around the `except`, and I wrote
the reason five lines down. **The window was the constraint, not the
vocabulary.** Moving the word to the first line reclassified it: dependency
19 → **18**, DOCUMENTED 1 → **2**. The scanner was **not** loosened.

**BLIND SPOTS: 4.** (1) The `(file, shape)` key cannot distinguish **two** guards
of the same shape in one file — a second bare-except in a file that already has
one is invisible to the set comparison; the count check is kept for exactly that
and the output says so. (2) The pin is 18, so the pre-commit shape is accepted as
pinned rather than removed. (3) Relocations were identified against **one**
baseline commit; whether earlier ones were mistaken for regressions is
unmeasured. (4) The hook change is driven on fixtures, not by making
`git diff --cached` actually fail in a real commit.

---

## 3. Both instruments wired — and the hook **shipped broken**

**Collision checked before writing**, as asked: `.claude/settings.json` is
tracked, clean here, and **byte-identical in all four other clones** (hank, cody,
fourth, hover), so the write propagates by pull with nothing to reconcile. Both
entries are **appended, never reordered** — the attribution notice goes **last**
in `PreToolUse/Bash` so the four existing guards all refuse first. *A notice must
never delay a refusal.*

### The literal backspace

`SUBJECT_DIRS` was written as `'\b(tools|tests)/…\b'` through a shell heredoc
that ate one backslash. In a **non-raw** Python string `\b` is **U+0008
BACKSPACE**, not a word boundary — so the compiled pattern began and ended with
`\x08` and **matched nothing. The hook was silent on every command including the
one it exists for.**

**Silence from a report-only hook is indistinguishable from "nothing to
report",** which is the worst available failure mode. `CLAUDE.md` names this
exact shape as one of its six paid-for lessons: *"a regex that shipped with a
literal backspace and could never match."* Found by printing `repr(pattern)`
after the hook stayed quiet on a case I had just proven should fire.

**It then fired on my own next command** and has fired correctly on nearly every
command since, including inside this batch — which is the end-to-end proof.

Narrow on purpose: it speaks only when the command is non-attributable **and**
invokes something under `tools/` or `tests/`. `git push` through a filter — the
second of my two real errors — does **not** match. Not being noise is why a
report-only hook keeps being read.

`cron_beat_refusal_check --hook` runs the **criteria lock** on
`PostToolUse/Write|Edit`, self-scoped and silent otherwise. **Proven to speak:**
breaking the classifier makes it report *"5 of 6 fixtures misclassify … any CLEAN
it reports is unearned."*

### The hook manifest was NOT regenerated, deliberately

`hook_integrity` reports **7 drifts; 5 mine, 2 not** — `deploy_verify_notify.py`
and `sairn_push_gate_hook.py` both changed without a regenerate, and **the second
is hank's live claim file.** `--regenerate` is all-or-nothing, so closing my two
*"NOT IN THE MANIFEST"* gaps would silently bless another session's in-flight
edit to a **push gate**. Not a trade to make as a rider. Flagged for hank.

**BLIND SPOTS: 4.** (1) My two tools are therefore **not** in the manifest, so an
edit to either is unchecked by that control — a real gap chosen over the
alternative. (2) The hook cannot see the no-op-push half of my second error.
(3) Neither hook has a probe under `tests/`. (4) The settings write is verified
against four clones **as of now**; a clone that edits before pulling still
conflicts and nothing warns it.

---

## 4. Rows 82 and 845 — applied, and hank's figures had already drifted

**Hank delivered the text this round** (`docs/FOR-CC-rows-82-845-hank.md`, his
third attempt, in its own file so it could not be missed in a section heading).
Both rows are **retractions of false claims**, each verified by a deciding test.

**I re-ran both rather than pasting**, and `--reseat-shas` reports
**37 / 18 / 2 / 6 / 11** at HEAD against the **40 / 23 / 1 / 6 / 10** in his
text. **The capability claim holds; the numbers do not.** Third time prepared
text from that source has drifted between writing and application — which is a
property of *prepared text*, not of hank, and the reason the standing rule is
**re-derive, never paste.**

**BLIND SPOTS: 1.** I verified the two deciding tests and the cited line ranges;
I did not re-read the whole of `tier_a_review_gate.py` to confirm the
file-set-subset logic does what the row now says it does.

---

## 5. `PR §2.6` — the `-S` vs `--grep` rule, moved out of a dated file

The rule now lives in `docs/SAIRN-PROCESS-RULES.md §2.6`, beside the other
standing git conventions, so it is discoverable without finding one batch
inventory. The batch-5 doc keeps only the instance that paid for it and points
at the new home.

It records what cannot be fixed as well as what can: **nothing makes the stale
`-S` result go away.** A pushed commit message is immutable, `--amend` is refused
once other clones have it (`§2.4`), and `refs/notes/commits` **does not
propagate** here because the push gate correctly refuses a ref whose base it
cannot resolve.

**Numbered `2.6`, not `2.5`** — a `2.5` already existed, which I checked before
writing rather than after.

**BLIND SPOTS: 1.** No existing document was swept for other claims that only
`-S` can reach; the rule is stated, not applied retroactively.

---

## 6. `PR §2.7` — the pattern named as its own rule

**"Before writing a claim about a tool, run the tool."** Four instances in two
days across three sessions, listed in the rule itself: the false `exits 2`, the
false coverage off-by-one, the `--reseat-shas` row, and the
`assertion_label_shape_check` row.

**Why it earns a rule rather than four apologies:** `PR §1.11` makes a silent
COULD-NOT-RUN the costliest failure here, which makes **falsely accusing a
working checker of it the costliest false claim** — the accusation most likely to
get a sound control distrusted or switched off. **Two of the four were exactly
that, against the same tool.**

It carries the operational form (`> /tmp/out.txt 2>&1`, then `echo $?` alone) and
the corollary that keeps costing days: **when a row says a capability is missing,
run for it before acting** — two of the four were rows asserting a gap that had
already closed, and ~900 index rows have never been re-checked.

---

## 7. Items 4 and 5 — verified landed, not asserted from memory

| item | state at HEAD | where |
|---|---|---|
| seq 486b, the `marker` exemption | **gone** from `SCOPE_WORDS`; dependency-with-marker no longer exempt, hover-clone still exempt | `17343958` |
| seq 464/467, the law-auth arm | **consumer boundary present**, 19/19; `+=` build reddens only the canary, an unscoped lookup reddens three arms | `c6d66c11` |

Both re-driven today rather than taken from the previous batch's report — which
is §6 applied to my own records.

---

## 8. THE LESSON, as its own entry

**A cheap measurement not taken becomes a confident wrong claim in a standing
document, and the cheapest measurements are the ones most often skipped.**

Twice in two days I accused `tools/md_table_check.py` of a defect it did not
have. Both times a single direct re-check would have shown the tool was right:

1. *"exits 2 (COULD NOT RUN)"* — it exits **0**, and there is no code path in it
   that returns 2. The 2 came off a pipeline.
2. *"a coverage off-by-one, 111/110"* — the **document** had a `| | |` row. The
   tool was reporting correctly.

**What makes this worth a rule rather than an apology:** in both cases I was
*being careful* — I declined to relax a probe arm rather than force the file
through, which is what left the real cause findable. Care was not the missing
ingredient. **The missing ingredient was running the program before describing
it.**

**And the direction of the error is the serious part.** Both claims accused a
control of the one failure this platform treats as most costly. A false
COULD-NOT-RUN accusation does not merely waste time; it is the claim most likely
to get a working checker rewritten or distrusted.

**Now a standing rule at `PR §2.7`** rather than a note in a dated inventory —
which is the same move item 7 asked for on the `-S` rule, applied to this
lesson.

**Third instance in this batch, inside this batch's own history:** my first
attempt to commit the wiring failed, and I read the push gate's
generated-document refusal — printed in the same block — as the cause. It was
not: `git commit -F` exited **128** with *"could not read log file"* because the
message file was missing. **The gate's refusal was real and also unrelated.** The
hook wired here did not catch it, because a missing-file commit failure is not a
pipeline — its scope is attributability, not every wrong-subject read.

**BLIND SPOTS: 2.** (1) `§2.7` is a rule for the writer, not a gate — nothing
mechanically stops the next untested claim, and the attribution hook covers only
the pipeline half. (2) The four instances are the ones that were *caught*; how
many untested claims are sitting in the ~900 unchecked index rows is unmeasured
and is itself the corollary the rule names.

---

## 9. What this batch did NOT do

* **No hook-manifest regenerate** — would bless another session's in-flight push-gate edit.
* **No probes** under `tests/` for either new hook.
* **No retroactive sweep** for other claims only `-S` can reach.
* **No work on the ~900 unchecked index rows** beyond the two hank named.
* **No SAIRNbiz click-through**; finding 13 still open and unfixed.

**BLIND SPOTS: 1.** This is what I know I did not do; it cannot cover what I did
not think to check.
