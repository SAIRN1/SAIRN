# Work claims — one file per session

`<session>.json` per clone: `cc.json`, `hank.json`, `cody.json`, `fourth.json`.
Written by `tools/sairn_claim.py`. Read them with `list`, not by hand.

**One file per session, not one shared file, and that is deliberate.**
`SAIRN-ACTIVE-WORK.md` was a single shared append target until 2026-08-24, when
four sessions appending to one file's end produced repeated merge conflicts in a
single night and it was split per clone. A shared `active-claims.json` rebuilds
that exact failure inside the tool meant to reduce friction between parallel
sessions. Every write here goes to a file exactly one clone touches, so merge
conflicts are impossible by construction.

## Use

    python tools/sairn_claim.py check   sairnfreedom competitive scan
    python tools/sairn_claim.py claim   sairnfreedom competitive scan
    python tools/sairn_claim.py release sairnfreedom
    python tools/sairn_claim.py list

`check` exits 1 when blocked. `claim` runs `check` first and refuses if blocked.

## What it is not

**Not a lock.** Claims travel by git, so a claim is invisible to another clone
until it is pushed *and* that clone fetches. Two sessions starting within the
same minute can still both claim. This narrows a four-hour duplication window to
about a one-fetch window; it does not close it.

**It cannot tell you a claim is being worked**, only that one was made. A
crashed or context-compacted session leaves its claim behind, which is why
claims expire after 4 hours (`SAIRN_CLAIM_STALE_HOURS` to override).

An expired claim can mean the session died — or that the work was finished and
never released. Check before repeating it.

Released claims are kept rather than deleted: "who ran this gate, and when" is
the question the next session actually asks.

## Automatic half — SessionStart hook

`tools/sairn_claim_hook.py` runs at session start (registered in
`.claude/settings.json`). It lists every OTHER session's active claims, then
gets out of the way.

**The path is relative, so THE COPY THAT RUNS IS THIS CLONE'S** — corrected
2026-09-04, this line previously said it resolved from `C:/SAIRN/tools/`. A
byte-identical stale mirror does sit there, and no hook in any settings file
points at it; editing that copy changes nothing, which is the same shape as the
defect below.

It is **advisory and never blocks**. It cannot do a subject-specific overlap
test, because at session start nobody knows yet what the session will be asked
to do — that is still `sairn_claim.py check <subject>`, run manually before an
unassigned gate. The hook exists so a session that never runs the tool still
sees the other three.

- **Silent when there is nothing to say.** No other session holding a claim
  means no output.
- **Honest when it cannot tell.** `git fetch` is capped at 8s. On failure it
  reports what it has *and* says the list may be incomplete, rather than
  presenting stale local data as current. "No claims" then means "unknown",
  not "nobody is working".
- **Fails open.** Every error path exits 0. A session must always start.
- **Silent outside this system.** It only fires in a repo that actually has
  `.claude/claims/`. The home directory is itself a git repo on this machine,
  so without that guard the hook would fire in every unrelated project.
- **Read-only on the repo — fixed 2026-09-04, and it was not before.** It
  fetches, then reads origin/main's claim files with `git show`. It used to run
  `git checkout origin/main -- .claude/claims`, which **overwrites the working
  tree and stages what it wrote**. `sairn_claim.py` was fixed for exactly this
  earlier the same day and **the hook was missed** — so the danger was never
  actually closed, only closed in the copy a session is *less* likely to run.
  This one runs unattended at every single session start, in every clone.

  Caught by a plain `git status` in SAIRN-fourth showing `M
  .claude/claims/hank.json` staged, which nobody had staged. The general
  lesson: **a fix verified on the copy a human invokes, when a second copy runs
  unattended, is not verified.** `tests/claims/run_push_verify_probe.py`
  section 8 now runs the hook binary itself.
