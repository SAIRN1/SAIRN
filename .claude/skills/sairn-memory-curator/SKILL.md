---
name: sairn-memory-curator
description: Turn what a session learned into something the next session cannot miss — and stop a stale note from becoming a lie. Covers where a fact belongs (auto-memory vs CLAUDE.md vs a skill vs a work log vs an index row), the tense/verification rules that keep it true, and the pruning pass that removes what has been overtaken. Trigger at session end, before a handoff, after any correction to a standing document, whenever the same thing is explained twice, and whenever a note turns out to have been wrong. Every rule here comes from a SAIRN document that went stale and cost real time.
allowed-tools: Read Write Grep Glob Bash
---

# SAIRN Memory Curator

This platform's most expensive failures have not been bad code. They have been
**true statements that stopped being true and did not change**, and **real
findings that were never written where anyone would look**.

---

## 1. Where a fact belongs — pick before writing

| Kind of fact | Home | Test |
|---|---|---|
| Who the user is, how they want work done | auto-memory `user`/`feedback` | Would a fresh session get this wrong without it? |
| A rule every session must follow | `CLAUDE.md` | Would breaking it cost more than a session? |
| A repeatable method | a skill in `.claude/skills/` | Is it a *procedure* rather than a fact? |
| What THIS session did | `SAIRN-ACTIVE-WORK-<clone>.md` | Is it a record, not an instruction? |
| Open work someone must pick up | `docs/SAIRN-OPEN-WORK-INDEX.md` | Does it need an owner and a next action? |
| Verified research | `docs/<date>-<subject>.md` | Does it carry citations someone will re-check? |

**The failure this table prevents:** a real go-to-market scoping decision for
SAIRNvet — *"focus: companion + equine + farm/food animal + small exotics common
in Ohio; zoo/wildlife stays built but dormant"* — lived **only inside a session
handoff**. It was never in the backlog or the index. A later session had to
re-scope it from scratch. A decision recorded only in a handoff costs the next
session a re-derivation.

## 2. A fact with a tense needs a read

Anything with a tense — *is*, *has*, *currently*, *now*, a count, a status — is
only true as of the read behind it. Write the read into the sentence.

**Incident:** a HIGH-PRIORITY index row said a named production licence had
**zero active owners** and was API-unrecoverable. A live roster read showed **two active
owners** — someone had applied the exact promotion the row proposed as its
recovery action, and nothing recorded it.

**Incident:** a row said `rf_contingency_rules` held 0 rows while the seed had 2.
True when written; the rows were loaded hours later and the row stayed.

Both were correct findings that became false without changing. **Date the
claim, name the query, and expect to re-verify rather than trust.**

## 3. A comment describing a CONDITION is a lie waiting to happen

**Incident:** `dnt_cred_rules` carried *"no role gate, because SAIRNdental has no
employee auth… whoever adds employee auth should re-gate this."* Auth was added.
Nobody came back. The note stopped being true silently, and the gap went back to
being undiscovered — any signed-in employee could rewrite a state credentialing
requirement.

**Incident:** `sql/sairndental_credentials_schema.sql` carried the same promise
in its header, and failed the same way.

If a note's truth depends on a condition, say which condition, and prefer a
**mechanical check** over a note. Nothing greps comments.

## 3b. A COMMIT SHA is a fact with a tense, and rebasing changes it

**Added 2026-08-30, from an error in this platform's own skill pack.**

`sairn-api-tester` cited `a877978^` as the pre-fix commit for the
`dnt_cred_rules` role gate. **That SHA does not exist in this repository** — not
as a commit, not in `git log --all`. A verification pass caught it. The real fix
is `06ba0b8`.

**The mechanism, and it will happen again:** the SHA was correct when written.
Four sessions push to one repo, so every push means `git fetch && git rebase
origin/main` — and **rebasing rewrites every commit it replays.** The SHA
recorded in a document written before a rebase names a commit that no longer
exists anywhere.

**Rules:**

- **Do not cite a SHA in a document until it has been pushed and re-read from
  the remote.** `git rev-parse HEAD` after the push, not the local SHA from
  before it.
- **Prefer a stable identifier over a SHA** where one exists: the commit
  *subject line*, a file path, a tag. A subject survives rebasing; a SHA does
  not.
- **Audit cited SHAs before shipping anything that sells checkability.** One
  line:

      grep -ohE '`[0-9a-f]{7,10}`' <files> | sort -u | while read h; do
        git cat-file -e "$h^{commit}" 2>/dev/null || echo "MISSING $h"; done

- **A skill whose value is "every incident is real and checkable" cannot carry
  an uncheckable citation.** That is not a typo, it is the product claim
  failing in miniature.

The correction was made **in place with a dated note** rather than a silent
swap, per §4 — a reader who saw the old SHA can see what changed and why.

## 4. Strike through, don't delete

When a recorded claim turns out wrong, **keep it visible and mark it wrong.**

- A struck-through row shows a reader the error was found, not that it never
  existed.
- Deleting it means the next session can make the same mistake with no trace.

**Incident:** the canonical SAIRNfreedom research doc listed
*"charitable purpose enumerates scholarships, flags, patriotism…"* as VERIFIED at
ORC 2915.01(V). Those words are in **(V)(2)**, the veteran's limb only; **(V)(3)**,
which governs Elks/Moose/Eagles, contains none of them. The row was struck
through with the correction beside it, not quietly replaced — so anyone who read
the old version can see what changed.

## 5. Do not save what the repo already records

Skip code structure, past fixes, git history, anything in `CLAUDE.md`.

If asked to remember one of those, **ask what was non-obvious about it** and save
that instead. "We fixed the login bug" is in git. "The fix looked like a UI
problem and was an env-var typo, and the guard reported it as a missing secret"
is the fact worth keeping — that one cost real time twice
(`RESEND_FROM_ADDRESS`, a name that has never existed in this Vercel project,
read by two apps, one of which sent **zero reminders for months** while logging a
500 every hour).

## 6. Promote when a thing is explained twice

The second explanation is the signal. One-off → work log. Twice → a rule or a
skill.

**Incident:** *"read all four `SAIRN-ACTIVE-WORK` files before starting"* existed
in `CLAUDE.md` and still did not prevent two sessions running the same three
SAIRNfreedom research gates the same night — roughly four hours duplicated,
discovered only when a rebase pulled in three unexpected commits. The rule was
there; it was **read as being about file collisions**. Restating it was not
enough, so it became a tool (`tools/sairn_claim.py`) and a `SessionStart` hook.

**When a rule fails twice, it needs a mechanism, not a louder sentence.**

## 7. Prune what has been overtaken — and say who overtook it

**Incident:** `CLAUDE.md` listed specific known-broken script indices for
`stonedesk.html`. **That list went stale within hours.** It is now replaced by an
instruction to re-verify against the file directly, and the file says so about
its own former content.

**Incident:** the same file described the latest handoff as the
highest-numbered `SAIRN-SESSION-N-HANDOFF.md`. Two real `SESSION6` files existed
at once in separate clones and a session read the wrong one. Naming is now
date-and-subject.

A pruned entry should leave a one-line scar explaining what replaced it. That
scar is what stops the old idea being "restored" by a future session that finds
it missing.

## 8. Beware the number that exists in three places

**Incident:** `CLAUDE.md` said Guardian had 26 checks. The loaded global copy of
the skill said 28. The committed skill said 30. **Three live numbers at once.**

Resolution: name the **single source that moves when the thing changes** — the
skill's own `## The N Checks` heading — and instruct readers to distrust every
copy including the correction itself.

## 9. Not written until committed, in the same action

A handoff, claim, or correction that is only on local disk is invisible to every
other clone. This is not pedantry: the whole point of writing it down is
cross-session reach, and an uncommitted file has none.

**Incident:** a session summary stated two tool edits were *"already made and
committed."* They were made. `git status` showed them dirty in the worktree, one
context-limit interruption from being lost.

## 10. Audit the memory itself, on a schedule

Once a session, ask of the standing documents: *which claim here would I be
embarrassed to find is false?* Then check that one.

`CLAUDE.md` has now corrected itself about: which branch is stale, how many
clones exist, how to find a handoff, whether a skill exists, what a tool is
called, and its own check count. **Every one was written in good faith.** The
rate of drift is the argument for the audit, not evidence of carelessness.

---

## What this skill does not cover

**It cannot tell you whether a claim is true — only whether it is checkable and
current.** Every rule here is about tense, placement, provenance and pruning. A
false statement written carefully, dated correctly and filed in the right place
passes every check in this file. Verification is a separate act.

**It cannot reach the chat-side memory system.** Facts that live only in a
conversation's own memory are invisible to every clone — that is exactly how a
research file described as being at `/areas/sairnveterans.md` turned out to
exist nowhere on disk, after an exhaustive search. This file governs what is
written *into the repo*; it has no authority over what was never written down.

**It has no scheduler.** §10 says to audit the standing documents once a
session. Nothing enforces that, and a rule that depends on remembering is the
failure mode §6 describes. If the audit matters more than it currently does, it
needs a hook, not a stronger sentence here.
