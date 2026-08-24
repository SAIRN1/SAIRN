---
name: sairn-session-handoff
description: 'How to write a SAIRN session handoff, codified from what actually worked across three real handoffs (65, 66, 67) rather than adopted wholesale from any single external source. Naming is APP-DATE-SUBJECT as of 2026-08-23 (the old app+counter scheme collided in production — see Naming convention), and a handoff is not considered written until it is committed in the same action. Trigger before capacity runs low, before a known stopping point, or any time a session needs to hand off to a fresh one.'
---

# SAIRN Session Handoff

Considered adopting alirezarezvani/claude-skills' "Handoff" skill (derived from Matt Pocock's original, MIT licensed) wholesale — decided against it, for a specific, real reason: its core discipline is referencing existing artifacts by path/URL instead of duplicating them. That's a reasonable design choice in general, but it's the wrong one for us specifically — our actual failure mode tonight (the SAIRNbuild claims that turned out to be entirely false) happened because something sat unverified in memory; a reference-by-path handoff doesn't force the re-verification that caught it. Our own three handoffs tonight (Sessions 65, 66, 67), fully self-contained and independently re-verified each time, already worked in exactly our environment. Codifying that instead of switching philosophies.

Two genuinely good mechanical ideas borrowed from the upstream skill, kept:

1. **Automated triggering** — a SessionStart hook that reminds a fresh session to read the latest handoff before touching anything, and a SessionEnd hook that prompts writing one if capacity is running low. (Add to `.claude/settings.json` if not already present — mechanical trigger, not just a remembered habit.)
2. **A redaction check before saving** — given tonight involved a real GitHub PAT and could easily have involved Stripe keys in a handoff doc, scan for anything credential-shaped before writing the file, same category of check as Guardian's "no API keys in HTML."

## Naming convention — CORRECTED 2026-08-23 (supersedes the 2026-07-26 resolution)

**Use `APP-YYYY-MM-DD-subject-handoff.md`.** Examples:

```
SAIRNLAW-2026-08-23-lemaj-handoff.md
STONEDESK-2026-08-23-st-wrapper-sweep-handoff.md
SAIRN-PLATFORM-2026-08-23-skills-inventory-handoff.md
```

App prefix, then ISO date, then a short subject slug. Sorts chronologically, and the subject means a session that opens the wrong file knows within one line.

### Why the previous convention was replaced — this is not a style preference

The 2026-07-26 resolution (below, kept for the record) settled on a **per-app prefix plus a counter**: `SAIRNLAW-SESSION-N-HANDOFF.md`. That fixed cross-app collisions and was correct as far as it went. It did not survive contact with concurrent sessions.

**What actually happened, 2026-08-23:** two `SAIRNLAW-SESSION6-HANDOFF.md` files existed simultaneously with completely different content — one on trust-disbursement work (2026-08-18), one on LeMAJ argument decomposition (2026-08-23). Neither session was wrong. Both were genuinely SAIRNlaw, both were genuinely the sixth. A fresh session was pointed at "the Session 6 handoff", read the wrong one, and found none of the work it had been sent to continue.

**The root cause is the counter itself.** `N` can only stay unique if every session agrees on what `N` is before writing. With multiple clones and concurrent sessions on the same app, no such agreement exists and none is enforceable. A date plus a subject needs no coordination — two sessions collide only if they work the same app on the same day on the same topic, and if that happens the subject slug still distinguishes them.

This is the **second** recorded instance of this failure class (the first is the `sairn_handoff_naming_correction` memory: STONEDESK numbering at 78 vs SAIRN-PLATFORM at 2, "re-derive latest, don't assume"). Treat a third as evidence the convention is still wrong, not that someone was careless.

### Consequences for reading handoffs

Do **not** find the latest handoff by taking the highest `N`. Sort by the date in the filename, and confirm the subject matches the work you were actually sent to do. If the content does not match the task you were given, say so immediately rather than proceeding on the wrong document.

### Historical record — the superseded 2026-07-26 resolution

Two conventions existed at that time: a general `SAIRN-SESSION-N` series (StoneDesk work, N=63 through 67) and a separate `SAIRNVET-SESSION-N` series (N=56 through 62). The resolution was per-app prefix always — `SAIRN-SESSION-N` understood as `STONEDESK-SESSION-N`, and `SAIRN-PLATFORM-SESSION-N` for cross-cutting work. **Do not renumber or rename existing files retroactively** under either convention; the old names stay as they are. Apply the date-stamped pattern going forward only.

## A handoff is not written until it is committed — standing rule, 2026-08-23

**Writing the file and committing it are one action, not two.** A handoff that exists only in a local working tree is not a handoff. It is invisible to every other clone, invisible to the fresh session that needs it, and — if a tracked file of the same name exists upstream — it will block that clone's next `git pull` outright.

This is not hypothetical. The colliding `SAIRNLAW-SESSION6-HANDOFF.md` described above sat **untracked for five days** in `C:\Users\marsh\`. Its blob was never in the object database at all. It was also the only untracked file in that working tree that would have aborted a pull ("untracked working tree file would be overwritten").

So, every time:

1. Write the file **in one of the real clones** (see next section).
2. Run the redaction check — scan for anything credential-shaped before it goes in a commit.
3. `git add` + `git commit` + `git push` **in the same action as writing it.**
4. Confirm it is actually on `origin/main` — `git cat-file -e origin/main:<file>` or equivalent. A clean `git push` is not proof, per the standing Push Protocol.

If you cannot commit it — dirty tree mid-task, unresolved conflict, no push access — **say so explicitly in your report to the human.** Do not leave a local-only handoff and describe the handoff as written.

## Where handoffs may be written — repo/clone structure

Write handoffs only inside a dedicated clone. **There are four, corrected 2026-08-24** — this section previously listed three paths and then called them "four independent clones" in the next sentence. The fourth is `SAIRN-fourth`, which is a real, permanent clone with the same standing as the other three, not an ad-hoc or temporary checkout:

| Session | Clone | Active-work file |
|---|---|---|
| Hank   | `C:\Users\marsh\Documents\SAIRN-hank`   | `SAIRN-ACTIVE-WORK-hank.md` |
| CC     | `C:\Users\marsh\Documents\SAIRN-cc`     | `SAIRN-ACTIVE-WORK-cc.md` |
| Cody   | `C:\Users\marsh\Documents\SAIRN-cody`   | `SAIRN-ACTIVE-WORK-cody.md` |
| Fourth | `C:\Users\marsh\Documents\SAIRN-fourth` | `SAIRN-ACTIVE-WORK-fourth.md` |

All four verified on disk 2026-08-24: each is a separate clone of `https://github.com/SAIRN1/SAIRN.git` checked out on `main`.

These are four independent **clones**, not `git worktree` checkouts of one repo — `SAIRN-ACTIVE-WORK.md` carries the verified correction on that point (that file is now historical-only; see the active-work section below). `C:\Users\marsh\Documents\SAIRN` is a fifth checkout that is **stale and abandoned (2026-08-18) — do not work in it either** (measured 157 commits behind `origin/main` on 2026-08-24). Re-derive this list rather than trusting it: check the actual directories, since clone layout has already changed once and been documented wrongly twice — first as worktrees, then as three clones described as four.

**Do not write handoffs — or any repo file — to `C:\Users\marsh\` directly.** That path is itself a working-tree checkout of `SAIRN1/SAIRN`, which is the structural cause of the collision above: it is the first place a fresh session looks, a stray file there is invisible to every other clone, and it sits far behind `origin/main` with untracked files capable of blocking a pull.

**This is flagged, not fixed.** Retiring that checkout is a repo-setup decision for whoever manages clone layout — raise it with them. Do not migrate, delete, or re-point it as a side effect of writing a handoff.

## The Template (proven across Sessions 65-67)

Save as `APP-YYYY-MM-DD-subject-handoff.md`, in a real clone, committed in the same action.

# APP — Handoff, YYYY-MM-DD (subject)

Written [mid-session before capacity ran out / at natural stopping point].
Claims below are independently verified against the actual repo/live site,
not assumed from memory — same standard as prior sessions in this series.

## 1. Verified current state
- origin/main HEAD: [SHA] — confirmed via `git rev-parse origin/main`
- [Any other directly-checkable facts: panel counts, script-block counts,
  live proxy status via a real curl, not assumed]

## 2. Commits this session, in order
[SHA + one-line summary each, pulled from real `git log`, not paraphrased
from memory of what was intended]

## 3. What was CORRECTED, not just added
[This section matters as much as new work — if anything reported earlier
as true turned out not to hold up on verification, say so explicitly here.
Sessions 66 and 67 both had real examples: a platform-context handoff that
didn't exist in the repo, a "duplicate ID" finding that didn't reproduce,
an output-style key that was never actually added despite being assumed
done. Naming the correction is not a failure — treating an unverified claim
as fact going forward would be.]

## 4. Open items, prioritized
[Real, current, re-verified — not carried forward from an older handoff
without re-checking it's still accurate]

## 5. Standard verification reminder for whoever reads this next
Verify main HEAD, verify branch, re-run relevant checks before trusting any
claim in this document — including this one.

## Active-work logging — per session as of 2026-08-24, not one shared file

A handoff is written at a stopping point; the active-work log is written
*during* the work. Both are covered here because sessions reach for them at
the same moments.

**Append active-work entries to your own session's file** — one per clone,
same four rows as the clone table above:

| Session | Clone | File |
|---|---|---|
| Hank   | `Documents\SAIRN-hank`   | `SAIRN-ACTIVE-WORK-hank.md` |
| CC     | `Documents\SAIRN-cc`     | `SAIRN-ACTIVE-WORK-cc.md` |
| Cody   | `Documents\SAIRN-cody`   | `SAIRN-ACTIVE-WORK-cody.md` |
| Fourth | `Documents\SAIRN-fourth` | `SAIRN-ACTIVE-WORK-fourth.md` |

**Do not append to `SAIRN-ACTIVE-WORK.md`.** It was the single shared log
until 2026-08-24, when four concurrent sessions appending to the same
end-of-file region produced repeated merge conflicts across Hank, CC, and
Cody in one night. Every historical entry was copied verbatim into the files
above, split by the `(Hank)`/`(CC)`/`(Cody)` tag each entry already carried
(`-fourth.md` started empty — that clone had logged nothing before the split);
the original is kept in place as the historical record (other files cite it by
name) with a header pointing here.

If a fifth clone is ever added, it gets the same treatment on day one: a
`SAIRN-ACTIVE-WORK-<name>.md` with the same header, plus a row in both tables
here and in `SAIRN-ACTIVE-WORK.md`. Never fall back to appending to the shared
file, and never leave a clone as an unlisted special case.

**Read all four before starting work.** The split removes the write collision,
not the coordination need — knowing what another session is touching is still
the reason these files exist, and that requires reading files you do not write
to.

## When to write one

- Proactively, before capacity runs low — never wait for a hard cutoff.
- At any natural stopping point where a session might not resume immediately.
- Before switching between local and cloud sessions, or before opening a fresh session for any reason.

## The one rule that matters most

Section 3 (corrections) is not optional and not a sign of a bad session — a handoff that never has anything to correct across a long project is more likely hiding an unverified claim than actually being perfect three times running. Look for what to correct before assuming there's nothing.
