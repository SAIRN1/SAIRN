# Competitive-gap audit doc inventory — 2026-09-29 (CC)

**For the gap ledger Cody is building. READ-ONLY: no branch was merged, and
none was checked out. Everything below is read through `git ls-tree` and
`git log` against refs already fetched.**

## The stale memory is corrected first

A note claiming the build/vet/biz/grounds/cash audits "were never committed" is
**wrong**. `docs/superpowers/specs/2026-09-03-competitive-gap-audit-build-vet-biz-grounds-cash.md`
is on **origin/main** and has been since 2026-09-03. Verified by `git ls-tree`,
not by recall.

## Scope read

**10 refs**: `origin/main` plus 9 branches — the eight `claude/*` cloud-research
branches and `fourth/sairnvet-external-gap-audit-2026-09-26`.

> **2026-10-05 — ONE REF IN THAT SCOPE NO LONGER EXISTS, and this note is here so
> the table is not read as describing live branches.**
> `claude/cloud-research-competitive-vet-law` was deleted today
> (`docs/2026-09-29-stale-branch-tips.md`, addendum). **Nothing in this inventory
> changes:** that branch's tip was an ancestor of `main` with a zero-file diff —
> its SAIRNvet and SAIRNlaw audits are on `main` today at
> `docs/cloud-research/SAIRNvet-external-competitive-gap-audit-2026-09-25.md` and
> `…SAIRNlaw-external-competitive-gap-audit-2026-09-25.md`, which is why it was
> deletable at all. **The nine-of-fourteen finding below is UNCHANGED and still
> the live risk:** the branch that holds eight of those nine,
> `claude/wizardly-ride-wtun13`, is PR #18 and was explicitly KEPT. Scope is now
> 9 refs; the per-app table was not re-derived and is as of 2026-09-29.

## DEDICATED versus SHARED, and why the distinction is in this table

**DEDICATED** — the app's name is in the FILENAME and no other app's is.
**SHARED** — the filename names several apps, and this app is one line inside a
sweep.

They are counted apart deliberately. A ledger that scores a line in a five-app
sweep the same as a dedicated audit is overstating its own coverage, which is
the failure this inventory exists to prevent rather than repeat.

## Per app

| App | Has a doc? | Dedicated doc | Where | Date | Shared-sweep docs |
|---|---|---|---|---|---|
| `stonedesk` | yes | `docs/superpowers/specs/2026-09-02-stonedesk-worldwide-competitive-gap-audit.md` | **main** | 2026-09-26 | 0 |
| `sairnbiz` | yes | `docs/cloud-research/sairnbiz-external-competitive-gap-audit-2026-09-26.md` | `claude/wizardly-ride-wtun13` | 2026-09-26 | 1 |
| `sairnbuild` | yes | `docs/cloud-research/sairnbuild-external-competitive-gap-audit-2026-09-27.md` | `claude/wizardly-ride-wtun13` | 2026-09-27 | 1 |
| `sairncare` | yes | `docs/cloud-research/sairncare-external-competitive-gap-audit-2026-09-25.md` | `claude/cloud-research-sairncare` | 2026-09-25 | 0 |
| `sairncash` | yes | `docs/cloud-research/sairncash-external-competitive-gap-audit-2026-09-26.md` | `claude/wizardly-ride-wtun13` | 2026-09-26 | 1 |
| `sairncode` | yes | `docs/cloud-research/sairncode-external-competitive-gap-audit-2026-09-26.md` | `claude/wizardly-ride-wtun13` | 2026-09-26 | 0 |
| `sairndental` | yes | `docs/2026-09-17-sairndental-competitive-gap-rederived.md` | **main** | 2026-09-26 | 1 |
| `sairndesign` | **NO** | &mdash; | &mdash; | &mdash; | 0 |
| `sairnfreedom` | yes | `docs/cloud-research/sairnfreedom-external-competitive-gap-audit-2026-09-27.md` | `claude/wizardly-ride-wtun13` | 2026-09-27 | 0 |
| `sairngrounds` | yes | `docs/cloud-research/sairngrounds-external-competitive-gap-audit-2026-09-27.md` | `claude/wizardly-ride-wtun13` | 2026-09-27 | 1 |
| `sairnlaw` | yes | `docs/cloud-research/sairnlaw-external-competitive-gap-audit-2026-09-26.md` | `claude/wizardly-ride-wtun13` | 2026-09-26 | 0 |
| `sairnlegacy` | **NO** | &mdash; | &mdash; | &mdash; | 0 |
| `sairnmechanical` | yes | `docs/superpowers/specs/2026-08-27-sairnmechanical-shared-platform-competitive-research.md` | **main** | 2026-09-26 | 1 |
| `sairnroofing` | yes | `docs/2026-09-17-sairnroofing-competitive-gap-rederived.md` | **main** | 2026-09-26 | 1 |
| `sairnscape` | **NO** | &mdash; | &mdash; | &mdash; | 0 |
| `sairnsenior` | yes | `docs/cloud-research/sairnsenior-external-competitive-gap-audit-2026-09-26.md` | `claude/wizardly-ride-wtun13` | 2026-09-26 | 2 |
| `sairnvet` | yes | `docs/cloud-research/sairnvet-external-competitive-gap-audit-pricing-cds-2026-09-26.md` | `claude/wizardly-ride-wtun13` | 2026-09-26 | 1 |

## Apps with NO competitive-gap doc of any kind

~~**THREE: `sairndesign`, `sairnlegacy`, `sairnscape`.**~~ **ZERO, AS OF 2026-10-05 — ALL THREE WERE WRITTEN THE SAME DAY and this section is the only reason they were findable:**

* `docs/cloud-research/sairnlegacy-competitive-gap-audit-2026-10-05.md` (`88ee8fe7` internal half, `24ba5c08` the vendor-claim half — **which killed the internal half's main claim**)
* `docs/cloud-research/sairndesign-competitive-gap-audit-2026-10-05.md` (`5a4ea4fb`, both halves in one pass)
* `docs/cloud-research/sairnscape-competitive-gap-audit-2026-10-05.md` (`29d738a7`, both halves in one pass)

**THE METHOD CHANGED BETWEEN THE FIRST AND THE SECOND, and the reason is worth more than the three documents.** SAIRNlegacy shipped its internal half alone and its own Part 2 then overturned its central claim — breadth across four businesses, which turned out to be a named product category with at least four vendors selling exactly it. **An internal-only read invites a guess, and the guess runs IN FAVOUR OF THE PLATFORM.** The other two carry both halves in one pass for that reason.

**AND ONE OF THIS SECTION'S OWN SUPPORTING MEASUREMENTS WAS WRONG.** The pick order was justified partly on panel count, with `sairnscape` recorded as *"0 found by that pattern"*. That app is a landing page plus a single app view (`showPage('home')` / `showPage('app')`), so it does not use the `id="panel-…"` idiom at all — the zero was a structural fact misread as an absence, and panel count was never evidence about how much app there is. Corrected in that audit's §0.

Not "thin coverage" — nothing at all, on main or on any cloud branch, dedicated
or shared. Those are the three rows the gap ledger should open empty.

## Where the coverage actually lives, and the risk in that

**NINE of the fourteen covered apps have their newest audit ONLY on a cloud
branch**, eight of them on `claude/wizardly-ride-wtun13` alone. Those are not on
main:

`sairnbiz` `sairnbuild` `sairncare` `sairncash` `sairncode` `sairnfreedom`
`sairngrounds` `sairnlaw` `sairnsenior` `sairnvet`

Five have their newest on main: `stonedesk` `sairndental` `sairnmechanical`
`sairnroofing`, and `sairncare`'s older one.

**So most of the platform's competitive research is one unmerged branch away
from being invisible to anybody reading main.** That is the same shape as the
`regfresh/*` backlog closed today: work done, verified, and parked on a branch
nobody merges. It is recorded here rather than acted on — merging ten
cloud-research branches is a decision with an owner, and this is an inventory.

## What this inventory does NOT claim

* **It has not read the CONTENTS of any doc.** A file whose name says it audits
  an app is counted as covering it. Whether the audit is current, correct, or
  finished is not answered here.
* **Filename matching cannot see an app covered inside a doc that does not name
  it.** A sweep called `competitive-gap-status-rederived` names no app in its
  filename and is credited to none, so the SHARED counts are a floor.
* **Dates are the last-commit date of the file on that ref**, not the date the
  research was done. A doc touched by a rebase reads newer than it is — four of
  the main rows read 2026-09-26 for exactly that reason.
