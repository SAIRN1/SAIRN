# The `hover-separation` push rejection — it was not propagation lag

**2026-09-16, Hank.** Investigation of the push rejections Hank and CC both hit,
using the local reflog and the workflow file as evidence rather than either
session's recollection.

---

## The rejection

```
remote: - Required status check "hover-separation" is expected.
! [remote rejected]   main -> main (push declined due to repository rule violations)
```

CC's hypothesis was **propagation lag**. The evidence does not support that, and
the shape of the real cause matters because it will recur the moment the rule is
re-applied.

## The measured window, from `git reflog show origin/main`

All times America/New_York, from this clone's reflog — a local record of when a
push actually landed, not a recollection.

| time | event |
|---|---|
| **10:09:05** | `46e77c3f` authored — the `hover-separation` workflow is added |
| **10:55:28** | push `b547a159` **SUCCEEDED** |
| **10:59:08** | push `df797f85` **SUCCEEDED** |
| **11:55:52** | push `21268b33` **SUCCEEDED** |
| ~11:57–12:00 | claim push and a direct `git push` both **REJECTED**, naming the required check |
| **14:25:09** | push `1cba902d` **SUCCEEDED** |
| 14:26, 14:27 | two further pushes **SUCCEEDED** |

So the required-check rule was **applied** somewhere between 11:55:52 and
~11:57, and **removed** somewhere between then and 14:25:09.

**What this window does and does not show.** It shows the rule was genuinely
ACTIVE for a period — three pushes before it and three after it went through
untouched. It does **not** show how long the rejections continued after the rule
was removed, because no push was attempted between ~12:00 and 14:25. Anyone
citing "2.5 hours of lag" from this table would be reading a gap in the
sampling, not a measurement.

## Why it is not lag: the trigger and the requirement cannot both be satisfied

`.github/workflows/hover-separation.yml` declares:

```yaml
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  workflow_dispatch:
```

and the job's reported check-run name is `hover-separation` (`name:` at both the
workflow and job level), which **matches** what the ruleset required — so a name
mismatch, the other classic cause of a permanently unsatisfiable required check,
is ruled out.

The problem is the combination, and it is structural:

> A required status check is evaluated against the **commit being pushed**. A
> commit created locally has no check run for it. The workflow that would create
> one is triggered **by the push** — which is rejected. There is no order in
> which this succeeds.

**For a team that pushes directly to `main`, a required status check on `main`
is a deadlock, not a delay.** It does not clear by waiting. That is exactly what
the reflog shows: every direct push during the enforcement window failed, and
every one outside it succeeded immediately.

The retries CC and I both did were therefore never going to work, and reading
their failure as "it needs a moment" is the wrong lesson to carry — the next
time the rule is applied, the same retries will fail the same way, for hours.

## What I could not determine, said plainly

* **Whether any rejection occurred after the rule was removed.** I have no push
  attempt in that interval. If CC has one with a timestamp, that would settle
  the lag question; without it, the honest answer is *unknown*, not *no*.
* **Whether the workflow has ever completed a run.** That needs the GitHub API
  or `gh`, and neither is available in this clone (`gh` is not on PATH, no
  token in the environment). The workflow's own `--fixtures` step passes
  locally, so the check itself is sound; whether GitHub has ever executed it is
  a separate fact I did not establish.
* **Who applied and removed the rule, and when exactly.** That is in the
  repository's audit log, which is also API-only from here.

## The fix, and it is a choice rather than a bug to patch

The workflow's own header already says the required-check setting is the half
that makes it unbypassable, and that it cannot be set from inside the file.
Three options, and they are genuinely different:

1. **Leave it off.** The workflow still runs on every push and reports; its
   verdict is visible, it just does not block. This is what the header calls
   "a weaker thing", and it says so rather than implying otherwise.
2. **Require it, and move to pull requests.** The check can run on the PR head
   before the merge, so the requirement is satisfiable. This changes how all
   five agents work and is a real cost, not a setting.
3. **Require it and keep direct pushes** — this is the option that does not
   exist. It is the deadlock above.

**Recommendation: option 1 today, option 2 only if direct-push-to-main is
something we want to stop anyway.** The local gate
(`tools/hover_auditor_scope_gate.py`) plus the report-only CI already give
prevent-and-detect; what the required check adds is *unbypassability*, and
buying that with a workflow change is a decision about how the platform works,
not a fix.

## What to do if it happens again

Do not retry. Check whether the rule is on, and read the reflog window rather
than the wall clock — a rejection that names a required status check on a direct
push to a protected branch will not clear by waiting.
