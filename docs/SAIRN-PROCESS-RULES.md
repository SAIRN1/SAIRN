# SAIRN Process Rules — the in-task reference

**`CLAUDE.md` is the fresh-session primer: concrete facts, and what to check
before you start. This file is the other half — the discipline and the judgment
calls, read during the work rather than before it.**

Split out 2026-09-12 because one file was serving two audiences. A session
starting work needs *"where do handoffs live, which branch, what do I check
first"*. A session mid-task needs *"why did this check go green while the code
was broken"*. Interleaved, the second kind buried the first: 594 lines where the
answer to *"which branch"* sat between a four-paragraph incident narrative and a
tool's defect history. Both halves are load-bearing. Neither is optional.

**Read this file when:** you are about to write a check, a probe, a hook or a
tool; you are editing a standing document; a gate blocked you; a check passed
and you are not sure it tested anything; or something failed and said nothing.

---

## Part 1 — The class rules

These are stated as **patterns**, deliberately, and the incidents are dated
footnotes under them. A rule anchored to a literal example goes stale the moment
that example is fixed: the rule stays true, but a reader who checks the citation
finds it no longer reproduces and reasonably distrusts the rule. **Cite the
pattern; date the example.**

### 1.1 A check that stopped checking

**The rule: a check that cannot fail is indistinguishable from one that is not
running. Before trusting any new check, make it fail on purpose.**

This is the single most-repeated failure on this platform. Every instance below
is real, and they are grouped here because each was fixed in isolation, three
times, before anyone noticed they were one disease.

The four shapes it takes:

- **The check matched text that DESCRIBES code, not code.** See §1.2 — it has
  its own section because it recurred often enough to earn three tools.
- **The check's fixture was regenerated, which disarmed it.** Re-capturing a
  snapshot or golden file to "update" it silently rewrites the thing the
  tripwire was comparing against, so the tripwire now asserts that the current
  behaviour equals the current behaviour. *(2026-09-12, `48a0c844`: re-capturing
  the snapshot disarmed the only tripwire on the trial gate.)*
- **The check asserted an end state it never created.** A sweep arm that
  asserts "zero findings" passes on an empty input set just as happily as on a
  genuinely clean one. *(2026-09-12, `352c8e1a`: an arm asserted a clean sweep
  without ever creating one.)*
- **The check's anchor drifted onto different code.** See §1.3.

**The mechanism that makes this survivable:** every checker in this repo is held
by a probe that **plants the defect on a throwaway fixture and demands the tool
see it**. A checker that finds nothing is indistinguishable from one that looks
at nothing, and the probe is the only thing that tells them apart. When you add
a checker, add the probe in the same commit.

**The related trap, and it is the quieter one:** an assertion of **absence**
that goes red is loud and self-correcting — somebody investigates. An assertion
of **presence** that goes green off the wrong thing is silent and nothing is
looking for it. When you are auditing checks, spend the time on the green ones.

### 1.2 Grep cannot tell code from text that describes code

**The rule: do not grep raw source and call it a check. Parse it, or strip
comments and strings first. If the subject genuinely IS a comment — asserting a
historical record survives, or locating a block by its heading — that is fine
and must be DECLARED, not left to look accidental.**

This was the comment-quoting class, and it recurred **four times in two days**
across unrelated code before the general rule was written down. The canonical
statement is here; the three tools each carry their own measured detail and
point back at this section.

| Tool | The question it asks | Held by |
|---|---|---|
| `tools/comment_quote_check.py` | Does a probe's assertion match its target's COMMENTS instead of its code? | `tests/run_comment_quote_probe.py` |
| `tools/comment_sensitivity_check.py` | Does any checker's ANSWER change when the target's comments are removed? | `tests/run_comment_sensitivity_probe.py` |
| `tools/literal_drift_check.py` | (Consumer) blanks comments before counting, because a commented-out copy is not a second place a literal appears. | `tests/run_literal_drift_determinism_probe.py` |

Three things worth carrying out of that history, none of which are about
probes:

1. **The naive comment-stripper is wrong in two specific ways**, and both were
   hit here: blanking from any `//` to end of line eats `https://` and reports
   real code as comment; and a `//` inside a string literal is not a comment.
   `strip_comments` in `comment_quote_check.py` is the shared implementation —
   import it rather than writing a fifth one.
2. **Grep was the wrong instrument for the audit, too.** Surveying the checker
   fleet by grepping each tool for a comment-stripping *idiom* called two of the
   most careful tools in the repo unsafe, because both hand-write a full
   character-level scanner that uses no recognisable idiom. The behavioural
   question — *run it twice, once with comments blanked, and compare the
   answers* — is the one that works. That is what
   `comment_sensitivity_check.py` does, and it is why it is behavioural rather
   than structural.
3. **A tool written for this class committed this class.** More than once. That
   is not irony to be enjoyed; it is the argument for the plant-the-defect
   probe in §1.1.

### 1.3 An anchor that still matches is not an anchor that still points at the right thing

**The rule: a string anchor can only verify UNIQUENESS, never CORRECTNESS. An
anchor that has drifted onto different code while still matching exactly once is
invisible to every check, including the one written to check anchors. When an
anchor is load-bearing, pin it to something a refactor cannot silently move — a
function name, a parsed node, an explicit marker — or re-read what it currently
points at rather than trusting that it matched.**

Written up 2026-09-12. This lesson produced a real fix and a real tool and then
sat only inside that tool's docstring, which is exactly the gap this rulebook
exists to close.

Anchors are used in two places here, and they fail the same way in both:

- **Mutation probes.** A mutation probe reintroduces a defect, asserts the suite
  goes red, and restores the file. Its anchor is an exact string. A refactor
  that collapses `}else if(storeKey){` into a flat `if` makes the anchor match
  **zero** times — loud, the harness reports `ANCHOR-0`. An anchor shared by two
  writers matches **twice** — also loud. **An anchor that matches once, on the
  wrong branch, is silent.** *(Measured 2026-09-11: a six-space anchor sat on
  the missing-fields branch of `dntPushOne()` instead of the refused branch it
  was named for, matched exactly once, and reported SILENT for weeks.)*
- **Standing-document edits.** §2.1 says to rebuild a markdown row whole by
  anchoring on a unique substring rather than splitting on `|`. That is still
  the right rule — and it inherits this limitation exactly. **Assert the anchor
  appears exactly once AND read what it matched before replacing it.**

`tools/mutation_anchor_check.py` sweeps every `tests/*_probe.py` that declares
`MUTATIONS` and counts each anchor. It **parses with `ast` and never imports** —
importing a probe RUNS it, because most have no `if __name__ == "__main__"`
guard. The first version of that tool imported, hung, was killed mid-probe, and
left `api/_lib/dental-guardian.js` modified on disk.

**The standing rule that came out of that, and it is bigger than anchors: a
read-only checker must not be able to change the thing it inspects.** See §1.4
for the other instance of it.

### 1.4 A read-only-sounding command that mutates

**The rule: before using a command in a checker, confirm it writes nothing. "It
reads X" is a claim about intent, not about behaviour.**

Two instances, different tools, same shape:

- **`git checkout <ref> -- <path>` writes the working tree AND stages what it
  writes.** Used to "read claims as they exist on origin", it silently destroyed
  any claim written but not yet committed, and left a staged revert of a claim
  the clone had already committed — so a later `git commit` sweeping the index
  would have deleted the record. `git show <ref>:<path>` reads the same bytes
  and cannot write anything. *(2026-09-04.)*
- **Importing a Python probe runs it**, mutating a live source file. See §1.3.

### 1.5 The confident line printed after the error

**The rule: the expensive part of a false success is never the error — it is the
success message printed after it. A function that reports failure by return
value needs a caller that reads it.**

- A claim whose push failed was still reported as `CLAIMED.` — the save function
  printed a failure line and returned `None`, and both callers printed success
  regardless. So a non-fast-forward (the *ordinary* case when two clones claim
  within seconds) left the claim local and invisible while the tool said it was
  claimed. **The collision the tool exists to prevent, happening inside the
  tool.** It now verifies the commit is an ancestor of `origin/main` before
  reporting success, and exits non-zero with `NOT CLAIMED` / `NOT RELEASED`
  otherwise. *(2026-09-04.)*
- The post-push watcher swallowed a **403** and exited silently, so every push
  during that window got a check that did not run and said nothing. See §3.2 —
  **a 403 means UNVERIFIED, which is not the same as verified-good.**
- A failed rule read rendered as an **empty rule set**, which the app then
  advised the seed from. *(2026-09-12, `dd0fc32f`; `caf0632c` found the same
  ambiguity — `null` meaning both "no data" and "read failed" — across eight
  apps.)*

### 1.6 A fix verified on the copy a human invokes is not verified

**The rule: when you fix a defect, `grep` the whole repo for the defective line
before calling it closed.**

The `git checkout` defect in §1.4 was fixed in the tool a session runs **by
hand**, and the identical line survived in `tools/sairn_claim_hook.py` — which
runs **unattended at every session start, in every clone**. The danger was never
actually closed, only closed in the copy you are less likely to hit. It was
found the next session by a plain `git status` showing a staged claim file
nobody had staged.

Related, and a live trap: `C:/SAIRN/tools/` holds byte-identical stale mirrors
of several hooks, and **no settings file points at any of them** — every hook
command in `.claude/settings.json` is a relative `tools/...` path resolving
inside the clone. Editing a mirror there changes nothing.

### 1.7 A sampling window silently exempts what it does not reach

**The rule: any fixed-size window, head/tail, sample or truncation in a checker
must say what it did not look at. A scan that covered 60% and reports "clean" is
a wrong answer, not a partial one.**

*(2026-09-12, `42257545`: a fixed 2,500-character window silently exempted a
Tier A resource from the removal-path queue.)* The general form —
**a truncated read is indistinguishable from a complete one** — is the subject
of the `sairn-context-budget` skill; read it before quoting any count from a
file, export or command output.

### 1.8 A generated artefact is safe to generate; a generated GATE is not

Two rules in this repo look like they contradict each other. They do not, and
the distinction has never been written down until now.

- **`docs/TOOLING-INVENTORY.md` is GENERATED**, because the hand-written one was
  stale in three days. Its generator **refuses** when it meets a tool it does
  not recognise, rather than quietly emitting an incomplete document.
- **`tools/sairn_load_state_check.py` must NOT be generated** — see the
  superseded header on `tools/sairn_build_load_gates.py`. A gate that must be
  regenerated after every seed edit reproduces the exact silent-failure shape it
  exists to catch.

**The distinguishing question: what does this artefact do when it is out of
date?** An inventory that is stale is *visibly wrong* and its generator refuses
rather than guessing. A gate that is stale **passes**, and a passing gate is
indistinguishable from a safe change. Generate the first; never the second.

### 1.9 A checker must answer the same on identical input

Non-determinism in a checker's output turns every diff into noise and every
"it's clean now" into a coin flip. Set-iteration and dict ordering are the usual
sources. *(2026-09-12, `ac8f8491`: near-duplicate pair A/B labels swapped
between runs. The sweep in `docs/2026-09-12-checker-determinism-sweep.md` found
1 of 26 affected, and it was already known.)*

---

## Part 2 — Editing standing documents

### 2.1 Never edit an index row by splitting on `|`

`docs/SAIRN-OPEN-WORK-INDEX.md` is the file every session reads to choose work
and edits to record the outcome. Rows get updated by splitting the line on `|`,
replacing a cell by index, and rejoining. **That is only safe while every pipe in
the row is a column separator, and it is not.** A cell whose prose contains one —
a hook matcher written `Write|Edit`, a `||` inside a code span, a regex
alternation — adds separators nobody intended. Two real consequences:

- **markdown renders extra columns**, so trailing cells fall off the end. On
  both rows found on 2026-09-04 the **Sz** column was gone and narrative text
  was rendering where a column value belongs;
- **an edit by cell index writes into the wrong cell** — a status landing where
  an owner belongs, silently, in the file every session trusts to say who is
  doing what.

**The rule: rebuild a row whole. Do not split and rejoin by index.** Anchor on a
unique substring, assert it appears exactly once, **read what it matched**
(§1.3), then replace it.

**The mechanism:** `python tools/md_table_check.py` checks every table in the
standing docs, per table rather than per file (that document holds three tables
of different widths), honouring `\|` as content the way markdown does. It
**reports and never writes** — its first version had a `--fix`, and its own
probe caught that fixer escaping the *real* separator and merging two genuine
columns. Held by `tests/run_md_table_check_probe.py`.

### 2.2 Not written until committed, in the same action

A handoff, a claim, or a correction that exists only on local disk is invisible
to every other clone. The entire point of writing it down is cross-session
reach, and an uncommitted file has none.

This applies identically to **handoffs**, **claims**, and **corrections to a
standing document**, and it has been learned separately for each. One rule.

### 2.3 A fact with a tense needs a read, and a number needs a single source

Anything with a tense — *is*, *has*, *currently*, a count, a status — is only
true as of the read behind it. **Write the read into the sentence**, or do not
write the number.

The failure mode is specific and this repo has hit it repeatedly: a count gets
copied into a second document, then a third, and now there are three live
numbers and no way to tell which is current. **Name the single source that moves
when the thing changes, and point at it instead of copying the value.** Guardian's
check count lives in the skill's own `## The N Checks` heading, and nowhere else
should state a digit.

**When a recorded claim turns out wrong, strike it through — do not delete it.**
A struck-through line shows the next reader that the error was found. A deleted
one lets them make it again with no trace.

---

## Part 3 — Push protocol, in full

The two-line version is in `CLAUDE.md`. This is what each step actually means.

### 3.1 Before pushing

Run full Check 0 plus **every** `sairn-guardian-v2` check against the changed
files. **Do not state the number of checks here or anywhere else** — re-read the
skill's own `## The N Checks` heading, which is the only source that moves when
a check is added. That count has been wrong in three places at once before
(§2.3).

Do not push on a partial check, and do not push on "syntax passed" alone.
Syntax-clean is necessary, not sufficient.

### 3.2 After pushing

Live-verify the specific fix against the real deployed URL. A clean `git push`
is not proof the live app reflects the change.

**Not with bare `curl`.** Vercel's platform bot mitigation answers an
automated-looking User-Agent with **403 + `X-Vercel-Mitigated: challenge`**.
That is not an outage and not a failed deploy — real browsers are unaffected and
the project's deployment protection is off. Measured same-second, same URL:
`python-urllib` default UA → 403; a browser UA → 200.

- **From a script:** fetch through `tools/sairn_http.py`, which sends
  browser-shaped headers and raises a distinct `Challenged` rather than letting
  a block look like an answer.
- **From a Claude turn:** `mcp__claude_ai_Vercel__web_fetch_vercel_url`
  authenticates past it.

**A 403 means UNVERIFIED, which is not the same as verified-good** (§1.5).

### 3.3 Seed files must already match the live licence

Step 3.2 covers deployed **code**. A seed-file change is **inert until a loader
runs**, and nothing covered that until a committed legal correction went
unloaded and a production licence computed federal answer deadlines three days
late for a day.

`tools/sairn_push_gate_hook.py` runs as a PreToolUse Bash hook on every
`git push`, inspects the commits actually being pushed, and acts only if one
touches a seed file:

- live matches the repo → allows silently (the normal case if you loaded first,
  which is why a correct workflow feels no friction);
- **drift → the push is DENIED**, naming the app, the rule id, and the reload
  command;
- could not tell (no key, endpoint unreachable) → allows with a loud note.
  **That is not a pass.** Run
  `python tools/sairn_load_state_check.py --app <app> --key <key>` and report the
  real result rather than treating silence as agreement.

Load-then-push and push-then-load both end with live == repo; the hook only
cares that they agree by the time you push. Load first anyway — a denied push
costs nothing, a shipped-but-unloaded correction costs a wrong legal date.

**The override is `SAIRN_SEED_GATE=off`, and it goes at the FRONT of the push
command itself** — `SAIRN_SEED_GATE=off git push ...`, not a separate `export`
line. The hook reads the assignment out of the command text, because as a
PreToolUse hook it runs inside Claude Code's process and inherits Claude Code's
environment, not the environment of the command it inspects. A mention inside a
quoted string — a commit message quoting the flag, which this repo's messages
really do — deliberately does **not** count.

**Say out loud when you use the override.** An override nobody mentions is how a
gate gets hollowed out.

The hook **fails OPEN** on any internal error, the same standard as the other
hooks, because one that crashes closed gets disabled and then protects nothing.
*(A 2026-09-11 report that an empty push range was a fail-open defect was
retracted in `0d4b087a`: the range is empty only when the pushed tip is already
an ancestor of what origin has, which ships no new objects. The widening that
was briefly applied turned an accurate `[]` into a 1,671-file scan of the whole
history handed to every check — which is how a gate gets switched off.)*

### 3.4 SQL that writes credential rows must carry the recoverability guard

A licence with `*_employee_auth` rows and **zero** rows that are both `active`
and in that app's `PROVISIONING_ROLES` is **unrecoverable through the API**:
`bootstrap` refuses 409 while any row exists, and `setup` and `set_active` both
need an active provisioner.

**The API cannot create that state** — `set_active` refuses self-deactivation,
refuses the last active provisioner, and re-reads that the caller's own row is
still active, so the count cannot cross 1 → 0. **SQL is the only door**, which
is why the guard lives in the SQL file and not in the app.

`tools/employee_auth_guard_check.py` enforces it as check 2 of the same push
hook. **Two end states are safe and only two:** zero rows (this RE-ARMS
`bootstrap` — recovery, not lockout), or at least one active provisioner.
Deleting or deactivating *some* provisioners while leaving others is the only
dangerous shape.

**Read the app's own `PROVISIONING_ROLES` — SAIRNcode's is `admin`, not
`owner`.** A guard that hardcodes `owner` passes SAIRNcode clean forever while
checking nothing. Nineteen pre-2026-08-29 writers are grandfathered in an
explicit list in that tool; they are **visible, not fixed**, and the list is
meant to be burned down rather than added to.

---

## Part 4 — Coordination, in full

The operating rules are in `CLAUDE.md`. This is why they are shaped the way they
are, and what the tool cannot do.

### 4.1 Why a claim and not just a check

"Read all four active-work files before starting" was already the rule and it
was not enough, because it was understood as **collision avoidance on files**
rather than **collision avoidance on work**. Two sessions can run the same
research without touching a single common file, and nothing catches it.

*(2026-08-30: two sessions independently ran all three SAIRNfreedom pre-build
gates the same night. Discovered only when a rebase pulled three unexpected
commits into an unrelated push, by which point both were finished. Roughly four
hours duplicated.)*

A check only works if the other session has **already written something down**,
and the expensive window is precisely the hours before anyone has results to
log. The claim closes that window. **The claim is worth more than the result
is:** a result tells the next session what was found; a claim stops them finding
it again.

### 4.2 It is not a lock, and the honest scope of the fix

Claims travel by git, so two sessions starting within the same minute can still
both claim. It narrows a four-hour window to about a one-fetch window. It
reduces the odds; it does not eliminate them. Read `.claude/claims/README.md`
for the full limits.

The genuine fix is the coordinating session assigning gates explicitly — and
**that was tested on 2026-09-01 and is not enough on its own**, because an
explicit assignment made without reading the claims is the same collision with a
clearer author. One session was dispatched four times in a row and the first
three were already claimed. Nothing was lost only because the receiving session
checked each time. **Whoever dispatches: run `list` and name the FILE first.**
"SAIRNvet is untouched tonight" is a claim about state and needs the same
verification as any other.

### 4.3 A block is a claim to verify, not a fact

The overlap matcher has had one real defect (fixed 2026-09-02 — a generic token
can no longer block on its own, held by `tests/claims/run_matcher_probe.py`).
False positives are now **narrower, not impossible**: a SUBJECT-level block
still fires on a shared namespace (`platform`, `accounting`) even when the files
do not overlap at all.

So: read the named session's actual task and file. If the block is lexical, **say
so out loud and proceed** — but **do not reword your task string to slip past the
matcher.** That is trivially easy and is exactly how a gate gets hollowed out;
write the claim directly with a note recording why, the same standard as
announcing `SAIRN_SEED_GATE=off`. **Naming the subject accurately**
(`live-verify-tooling` rather than `platform`) is the honest fix for a namespace
collision and is not the same thing as gaming the matcher — say which one you
did.

`list` and `check` **read with `git show` and write nothing** (§1.4). All three
historical defects in `sairn_claim.py` are fixed and each is held by a probe in
`tests/claims/`.

### 4.4 Duplication is not always a total loss — and that is not an argument

The 2026-08-30 duplication caught a real factual error about ORC 2915.01(V)(2)
vs (V)(3) that would have shipped one shared charitable-purpose enum, wrong for
every fraternal lodge in the product. It was found **only** because two readers
hit the same statute independently.

That is a defence of the outcome, not of the process. **Do not use it as an
argument for running gates twice on purpose.**

---

## Part 5 — Verification discipline

A status report is a claim, not a fact, until checked against the real current
state.

- **Never** report a migration, config change, or prior fix as "already done"
  from memory or a prior session's summary. Verify it live — query the DB, fetch
  the real deployed endpoint (§3.2), re-read the current file.
- When re-confirming something already marked done, check the **current** state,
  not a cached read from earlier in the session. Code changes mid-session,
  including from a parallel session.
- A claim of "verified" needs the **evidence** in the report — the command run
  and its real output — not just the conclusion.
- When assumed and actual state disagree, **report it plainly** rather than
  downplaying it or auto-correcting silently. The correction is usually the most
  valuable part of the report.
- **A CRLF-vs-LF difference is not drift.** Compare after `tr -d '\r'` before
  reporting one. The one-time normalization step per clone is in `CLAUDE.md`.

---

## Part 6 — Provenance worth keeping

Kept because a future session will otherwise rediscover or "restore" these.

- **`sairn-code-guardian`** is Guardian v2's ancestor and the origin of the
  duplicate-global check, *"added after the June 2026 StoneDesk outage."* It is
  absent from every skill store — but 1,230 lines of it were on an unmerged
  branch the whole time while a correction here said it did not exist. It now
  lives at `archive/branch-lucid-ptolemy-b73vu0/skills/sairn-code-guardian/` on
  `main` and holds **two** artefacts: `SKILL.md` and `sairn_static_checks.py`,
  the executable half. Full history is under the tag
  `archive/lucid-ptolemy-b73vu0`, which reaches 901 commits unreachable from
  `main` — deleting the source branch was safe **because** that tag exists and
  for no other reason. Not fetched by default:
  `git fetch origin tag archive/lucid-ptolemy-b73vu0`.
  **Do not recreate or run it.** v2 supersedes it and the archived copy predates
  every current discipline. Read it for provenance only.
  *The lesson worth keeping: "it does not exist" was a claim about three
  directories, stated as a claim about the whole repo.*
- **`security-auditor`** was removed 2026-09-03 (its Top 10 was the 2017 list),
  verified absent from both the user store and this repo. **Do not reinstate
  it.** `owasp-security` is the canonical general layer.
- **`SAIRN1/Fabricor`** on Railway is an abandoned duplicate codebase.
  StoneDesk's real code lives only in `stonedesk.html` on `SAIRN1/SAIRN`
  (Vercel). Do not resurrect or reference it without a specific new reason.
- **`SAIRN-ACTIVE-WORK.md`** (unsplit) keeps every pre-split entry as the
  historical record; code comments and SQL headers cite it by name. It is not an
  append target — see `CLAUDE.md` for the per-clone files.
- **Handoff naming was a counter and is now date-and-subject.** Two real
  `SAIRNLAW-SESSION6-HANDOFF.md` files existed at once on 2026-08-23 in separate
  clones, and a session sent to continue the second read the first and found
  none of its work. A counter cannot stay unique across concurrent clones. Older
  files keep their existing names and are **not** renamed — both patterns are on
  disk, and that is expected, not drift.

---

*This file is the process half. Concrete facts and start-of-session checks live
in `CLAUDE.md`. When a lesson turns out to be wrong, strike it through here
rather than deleting it (§2.3).*
