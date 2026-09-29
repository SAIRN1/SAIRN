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

**THREE: `sairndesign`, `sairnlegacy`, `sairnscape`.**

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
