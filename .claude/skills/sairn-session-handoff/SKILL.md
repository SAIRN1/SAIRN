---
name: sairn-session-handoff
description: 'How to write a SAIRN session handoff, codified from what actually worked across three real handoffs (65, 66, 67) rather than adopted wholesale from any single external source. Naming is SAIRN-handoff-<session>-b<N>.md as of 2026-10-20 (a per-SESSION counter has one writer; the 2026-08-23 APP-DATE-SUBJECT scheme did not take -- see Naming convention), and a handoff is not considered written until it is committed in the same action. Trigger before capacity runs low, before a known stopping point, or any time a session needs to hand off to a fresh one.'
---

# SAIRN Session Handoff

Considered adopting alirezarezvani/claude-skills' "Handoff" skill (derived from Matt Pocock's original, MIT licensed) wholesale — decided against it, for a specific, real reason: its core discipline is referencing existing artifacts by path/URL instead of duplicating them. That's a reasonable design choice in general, but it's the wrong one for us specifically — our actual failure mode tonight (the SAIRNbuild claims that turned out to be entirely false) happened because something sat unverified in memory; a reference-by-path handoff doesn't force the re-verification that caught it. Our own three handoffs tonight (Sessions 65, 66, 67), fully self-contained and independently re-verified each time, already worked in exactly our environment. Codifying that instead of switching philosophies.

Two genuinely good mechanical ideas borrowed from the upstream skill, kept:

1. **Automated triggering** — a SessionStart hook that reminds a fresh session to read the latest handoff before touching anything, and a SessionEnd hook that prompts writing one if capacity is running low. (Add to `.claude/settings.json` if not already present — mechanical trigger, not just a remembered habit.)
2. **A redaction check before saving** — given tonight involved a real GitHub PAT and could easily have involved Stripe keys in a handoff doc, scan for anything credential-shaped before writing the file, same category of check as Guardian's "no API keys in HTML."

## Naming convention — CORRECTED 2026-10-20 (supersedes the 2026-08-23 correction below)

**Use `SAIRN-handoff-<session>-b<N>.md`** — e.g. `SAIRN-handoff-cc-b31.md`.
It is what every batch dispatch asks for by name, and what the build sessions
actually write: **103 of the 157 handoff files in the repo root**, measured
2026-10-20 (cc b31). Only 8 follow the 2026-08-23 `APP-YYYY-MM-DD-subject`
scheme, and that share was falling by about three files a day (cody b30:
80 → 83 → 86 non-conforming across three batches). **Michael's b29 decision:
record the practice, do not rename the old files.**

**Why a counter is safe now when it was the root cause in August.** The
collision below was two sessions sharing ONE counter (`SAIRNLAW-SESSION6`
written twice, by different clones). Here the counter is scoped to a SESSION
prefix, and each prefix has exactly one writer — the clone that owns it. The
coordination the August text said was unenforceable is not needed, because
nobody else increments `cc`'s `N`.

**Reading:** take the highest `N` within your own session's prefix, **compared
as a number** (`b9` < `b28`; a lexical sort reverses them), then confirm the
subject matches the work you were sent to do, exactly as below.

### The 2026-08-23 correction, kept for the record

**It said: use `APP-YYYY-MM-DD-subject-handoff.md`.** Examples:

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

### Consequences for reading handoffs (2026-08-23 text -- SUPERSEDED for `SAIRN-handoff-<session>-b<N>.md`, where the highest `N` in your own prefix IS the latest; see the top of this section)

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

Save as `SAIRN-handoff-<session>-b<N>.md`, in a real clone, committed in the same action.

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

- **At 80% of real context, measured — `python tools/context_verify.py
  --digest-line`.** This line used to read *"before capacity runs low"* with no
  number, which is a rule enforced by remembering, and the agents that breached
  it were not being careless: there was nothing to be careless about. 80% is a
  **wrap-up trigger, not a hard cutoff** — all three deliverables have to fit
  inside the remaining 20%.
- At any natural stopping point where a session might not resume immediately.
- Before switching between local and cloud sessions, or before opening a fresh session for any reason.

## The digest — added 2026-10-20, and it was missing entirely

**This skill is invoked for three deliverables and covered one.** A handoff, a
report and a digest are written at the same moment by the same session, and
until this section existed the digest's shape lived nowhere a fresh session
reads — measured in `docs/2026-10-20-fourth-b38-currency-sweep.md`, which found
no threshold, no digest shape and no done-line in `CLAUDE.md`,
`docs/SAIRN-PROCESS-RULES.md`, the cross-domain disciplines or any of the 34
skills on the build side.

**The three are not three lengths of the same document.**

| | what it is for | length |
|---|---|---|
| **handoff** | the next session in **this** clone: committed state, what is open and why, claims held, the exact next step per open item, the transcript path | as long as the open work is |
| **report** | the record of what this batch actually did and how each claim was verified | as long as the batch was |
| **digest** | **routing** — what the other five sessions need to know and where to look | **30 lines, maximum** |

- **30 lines is a cap, not a target, and it is the ONLY digest ceiling.** The
  digest is read by sessions that are not going to open the report. If it does
  not fit, the content belongs in the report — which is uncapped for exactly
  that reason, so nothing is ever lost by shortening a digest.
  **Checked by two tools that agree on the number AND the definition:**
  `python tools/digest_lint.py <digest>` (exits 1) and `python
  tools/drive_upload_verify.py --agent <you> --batch b<n>` (a finding; the file
  still uploads). Both count with `splitlines()`, so a final line with no
  trailing newline counts and `wc -l` may report one fewer.
- **THE 150-WORD RULE IS RETIRED — Michael's decision, 2026-10-20.** It is
  named here because a reader of an older handoff will meet it. It lived in
  `digest_lint.py` from 2026-10-13 and **no agent ever met it**: re-measured
  that day, cc b27 11 lines / 596 words, fourth b40 15 / 837, hank b24 34 /
  391, cody b26 239 / 2011. Two ceilings disagreeing was worse than either —
  every digest passed one and failed the other. The word count is still
  printed and is no longer a finding. Do not reinstate it; `digest_lint
  --fixtures` has two arms that fail if somebody does.
- **SQL goes in `sql/<name>.sql` and the digest gives the PATH ONLY.** A digest
  that pastes a schema is a second copy, and the second copy goes stale with
  nothing to announce it. Same for a diff, a config block or a long refusal
  message: name the file.
- **The `CONTEXT` line is MEASURED, never typed:** `python
  tools/context_verify.py --digest-line` emits it and nothing else should ever
  write one. b20 measured all four build agents under-reporting their own
  context by 7 to 12 points; push-gate CHECK 5c now checks the line against a
  real turn in the session's own transcript, to the token.
- **Checked mechanically as of 2026-10-20:** `python
  tools/drive_upload_verify.py --agent <you> --batch b<n>` defaults to
  `--max-lines 30` on the digest. Over the cap is a finding and the file still
  uploads, because a missing deliverable is worse than a long one.
- **The final chat message is exactly `done b<n> <Drive file id of the
  digest>`** — the Drive file id, not the filename, and nothing else.

## The one rule that matters most

Section 3 (corrections) is not optional and not a sign of a bad session — a handoff that never has anything to correct across a long project is more likely hiding an unverified claim than actually being perfect three times running. Look for what to correct before assuming there's nothing.
