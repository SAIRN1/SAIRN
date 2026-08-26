# Two sessions built the same feature the same night

**2026-08-26.** SAIRNroofing's repair-vs-replace indicator was built twice,
independently, within hours. Cody's shipped (`a411eae` + `4d4410f`); CC's was
committed locally, never pushed, and deleted rather than merged after a
behaviour-level comparison
(`2026-08-26-repair-vs-replace-two-implementations.md`).

Both were complete: engine, migration, endpoint, panel, tests. Neither session
knew the other was building it.

## What it cost

A full feature's worth of work discarded. Not wasted entirely — the comparison
found a **real defect in the surviving implementation's rival and one in the
survivor's blind spot**, so the duplicate did buy something. But that is a
consolation, not a justification.

## Why the usual protections did not fire

- **The session lock did fire, and it was not enough.** It reported another
  session in the *same clone*. This was a different clone, which the lock's own
  warning text says it cannot see: *"this check only catches two sessions in
  the SAME clone directory."*
- **The active-work files did not help.** Each clone appends to its own file,
  and neither session had written its entry yet — an entry is written at the
  end of a work item, and both were mid-build.
- **The open-work index did not list it.** It was a fresh decision, not a
  tracked row.
- **CC did grep before starting** — `grep -rn -i "repair.vs.replace"` across
  the repo — and found only the patent boundary comment. **That grep ran
  against the local working tree, which was level with `origin/main` at that
  moment. Cody's first commit landed afterwards.** The check was correct and
  still missed, because a working tree is a snapshot of a moment.

## The one thing that would have caught it

`git fetch` first, then grep `origin/main` — not the working tree — immediately
before starting a feature, and again before writing the first line of code if
any time has passed. Cheap, and it is the only check in the list that sees work
another clone pushed five minutes ago.

## A compounding factor worth its own line

The boundary comment in `sairnroofing.html` asserted, in the past tense, that
element 4 **had already been supplied** while no such code existed anywhere.
CC read that, could not find the feature, and reasonably concluded the work was
still to do. **A claimed-but-unbuilt feature does not just mislead a reader
about status — it actively invites a second person to build it.** Corrected
since (the comment now says "is being supplied" and names the in-flight legs),
but the lesson generalises: past-tense claims about unbuilt work are a
duplicate-work hazard, not only an honesty one.

---

# Proposed addition to `sairn-parallel-app-scaling`

Not applied. This skill's canonical content lives at `C:\SAIRN\skills\sairn\`
with the repo copy tracked under `.claude/skills/` — a two-place change, so it
needs `scripts/verify-skill-store.sh` run after, and applying it unilaterally
mid-session is the same shape as the problem it describes.

> ## Before building: check what the OTHER clones already pushed
>
> Run this immediately before starting a feature, not at session start:
>
> ```bash
> git fetch origin -q
> git log --oneline HEAD..origin/main | head -20      # what landed since you last looked
> git grep -n -i "<feature name>" origin/main -- <likely paths>
> ```
>
> **Grep `origin/main`, not the working tree.** A working tree is a snapshot of
> the moment you last pulled. On 2026-08-26 a session grepped correctly, found
> nothing, and built a feature another clone had pushed minutes earlier —
> because the grep answered "was this here when I pulled?" and the question was
> "is this here now?".
>
> Re-run the `git log HEAD..origin/main` line before the first commit too. A
> long build gives another clone a long window.
>
> **Also check what is CLAIMED but not built.** A comment or doc asserting a
> feature exists, when it does not, reads to the next session as work still to
> do — and is therefore an invitation to build it twice. If a grep finds only
> prose describing a feature and no code implementing it, that discrepancy is
> itself the finding: surface it before building, because someone may be
> mid-build on exactly that.

---

## Two residual drifts on `origin/main`, not fixed here

1. `sairnroofing.html`'s boundary comment says the server action and UI "are in
   progress as of this comment". They landed in `4d4410f`. Minor staleness in a
   patent comment.
2. The IP screen's §5.1 still reads **"do not build a repair-vs-replace
   indicator or a facet diagram"** while the indicator is built and pushed. The
   spec and the code now disagree about whether the feature should exist.
   Michael's decision supersedes the recommendation; the document should record
   that rather than contradict it.
