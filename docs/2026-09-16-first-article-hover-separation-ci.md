# First Article Inspection — `tools/hover_separation_ci.py`

**Inspected 2026-09-16 by Cody. SELF-INSPECTION: I wrote the tool, I wrote its
control, and I am the one reading them against each other.** That is the weakest
kind of evidence in `docs/first-article-inspections.json` and it is recorded as
such rather than presented as an independent pass. It should be re-read by
another session.

It is recorded at all because the tool arrived unowned — nobody had logged an
inspection, and an uninspected artefact under the item 47 requirement date is
worse than a self-inspected one that says so.

## The mechanical half

    python tools/first_article_inspection.py --subject tools/hover_separation_ci.py

    artefact                          claims   arms  suite(s)
    tools/hover_separation_ci.py          10     11  hover_separation_ci_probe.py

Every new artefact has at least one suite; this one is not in NO-SUITE-AT-ALL or
UNWIRED. **The columns are not a score** — the item 47 document says so and it
matters here, because eleven arms on ten claims tells you nothing about whether
they are the *same* ten.

## The human half — and it found the tool contradicting itself

Reading the ten header claims against the eleven arms produced **one real
finding, in the artefact's own drawing rather than in its behaviour.**

The header's `WHAT THIS CAN AND CANNOT SAY` section still described v1, which
keyed on *attribution*:

> "Attribution of a hover commit rests on the commit touching ONLY the auditor's
> skill directory, so a commit in which the auditor also edited `api/sd-data.js`
> fails that test and lands in UNATTRIBUTED rather than being caught."

**That is backwards for the shipped tool.** v1 was replaced precisely because it
could never fire — a commit in which the auditor touches platform code is
unattributable by construction, so the one commit the gate exists to refuse was
the one it could not see. The replacement keys on **commit shape**: does this
commit touch the auditor's signature path *and* something outside its scope.
The mixed commit the header says is missed is now the single case it refuses.

`review()` carried the correct account the whole time, three screens below a
header that contradicted it. Both compile. Nothing mechanical could see it: the
claims are prose and the arms are code, and matching them by word overlap
scored 38% accuracy on this platform with five false positives out of five,
which is why item 47 requires a human pass. **This is what that pass is for.**

Corrected in the same change, with the superseded sentence quoted in place so
the next reader sees what it used to say rather than a clean header that was
never clean.

## Claim-to-arm, the remaining nine

| Claim | Covered by | Note |
|---|---|---|
| Refuses a commit mixing the auditor's directory with code outside its scope | `a commit mixing the auditor's directory with PLATFORM CODE is REFUSED` | the core claim, driven against a real commit in a real repository |
| Names the offending path | `...and the refusal NAMES the offending path` | |
| Quotes the rule rather than only failing | `...and quotes the rule rather than only failing` | |
| A clean auditor commit passes | `a commit inside the auditor's own directory PASSES` + `...and it was seen, not skipped` | the second arm is why the first means anything |
| Bookkeeping is not platform code | `the auditor's directory plus a CLAIM FILE is not a violation` | carve-out forced by a fixture, not chosen in advance |
| Catches the boundary running the other way (a build agent reaching in) | `--fixtures` arm `a BUILD AGENT reaching into the auditor's skill dir` | synthetic only — see gaps |
| The two scope definitions must still agree | `--fixtures` scope-drift arm, driven in both directions | |
| An unreadable range is COULD NOT RUN, never a pass | `an unreadable range is COULD NOT RUN (exit 2)` + `...and it says nothing was checked` | |
| Runs where a local hook cannot be switched off | *not verified by any arm* | see gaps |
| `.claude/claims/hover.json` has never existed | *not verified by any arm* | measured once, by hand, on 2026-09-16 |

## Gaps this inspection found and did NOT close

1. **The server-side claim is unverified by anything.** The tool's central
   argument is that it runs where a local hook cannot be switched off — and no
   arm tests that, because it cannot: it is a property of the GitHub workflow,
   not of this file. The workflow is currently **reporting-only**, and a
   required-status-check attempt on 2026-09-16 had to be reverted after it
   deadlocked direct pushes to `main` for every clone. **Until that is resolved
   the tool's headline claim is true of its code and not yet true of the
   platform.**
2. **The `hover.json` measurement is a hand-reading with no arm.** It was true
   when taken. Nothing re-takes it, so it will go stale silently the day the
   file is created — which is the outcome the claim is arguing *for*.
3. **The build-agent-reaching-in case is synthetic only.** It is a `--fixtures`
   arm over a constructed commit dict; the end-to-end probe never builds that
   commit in real git the way it does for the auditor's own case.

## What this inspection does not claim

That the tool is correct. It claims that ten stated claims were read against
eleven arms by a person, that one claim was found false and corrected, and that
three are carried by nothing. A self-inspection cannot tell you whether the
design is right — the author chose the design, and the control was written to
the same understanding that produced it.
