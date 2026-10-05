# Stale `regfresh/*` branch tips — recorded before deletion, 2026-09-29 (CC)

**Every tip sha below is recorded so any branch here can be recreated exactly:**

```
git branch <name> <sha>          # local
git push origin <name>           # back on the remote
```

A tip sha is all that is needed. The commits are reachable from it, and this
table is written and committed BEFORE any deletion ran.

## The two containment tests, and why both are here

**ANCESTRY** — `git merge-base --is-ancestor <tip> origin/main`. The commit
object itself is in main's history.

**CONTENT** — every `+` line the branch introduces is present VERBATIM in
main's `docs/CRITICALITY-TIERS.md` today.

**ANCESTRY FAILS FOR ALL TWENTY-SEVEN, INCLUDING THE EIGHT MERGED HOURS AGO.**
`tools/push_retry.py` rebases on every contended push, so those merge commits
were replayed and landed as rewritten shas; the original tips are not ancestors
of anything. A strict ancestry gate would therefore have deleted nothing and
called the whole exercise impossible — which is true about shas and false about
the work.

So deletion is gated on **CONTENT**, which answers the question that actually
matters: *is anything lost by deleting this branch.*

**AND THE CONTENT TEST EARNED ITS PLACE IMMEDIATELY.** Two of the eight
branches merged today — `regfresh/2026-09-28-sairnvet` and
`regfresh/2026-09-28-sd-data` — **FAIL** it. Those are exactly the two whose
merges conflicted on `sv_mobilevet` and `sen_settings` and were resolved by
taking main's newer text, so part of what they proposed is genuinely not in
main. They are KEPT. An ancestry-only or a merged-vs-unmerged rule would have
deleted both.

Six of the 2026-09-25 and -26 branches pass CONTENT without ever having been
merged here: their repoints reached main by another route (another session
landing the same citation, or the proposal tool being re-run against a moved
file). Their content is in main, so nothing is lost by removing them.

## Result

| | count |
|---|---|
| tips recorded | **27** |
| in main by ancestry | **0** |
| in main by content — **DELETED** | **12** |
| not in main by content — **KEPT** | **15** |

## Every branch

| Branch | Tip sha | Date | In main by ancestry | In main by content | Verdict |
|---|---|---|---|---|---|
| `regfresh/2026-09-25-sairnbiz` | `ec52e2daa9c9548e3e239a6a4d4e5fc7d9a83a0e` | 2026-09-25 | no | no (2 of 2 lines absent) | KEPT |
| `regfresh/2026-09-25-sairncode` | `d4b41427183fa316baaf236793b0e2a8b919ccbd` | 2026-09-25 | no | no (10 of 10 lines absent) | KEPT |
| `regfresh/2026-09-25-sairndesign` | `952b7ea8b7dd34539ea5ff973c0190ca34fcb4d4` | 2026-09-25 | no | no (1 of 3 lines absent) | KEPT |
| `regfresh/2026-09-25-sairnfreedom` | `8b97f86062281c410e8569d491c86395827bf161` | 2026-09-25 | no | no (3 of 3 lines absent) | KEPT |
| `regfresh/2026-09-25-sairnlaw` | `988965b9ef4a793dd2e4b05b8cc7332de78d8995` | 2026-09-25 | no | **yes** (5/5 lines) | **DELETED** |
| `regfresh/2026-09-25-sairnroofing` | `0a5506f52f40e25ea0d1d5dc52660b4bacce83d5` | 2026-09-25 | no | **yes** (1/1 lines) | **DELETED** |
| `regfresh/2026-09-25-sairnsenior` | `ae6ea3dbcc6fba7a0931411ca318d79d0d0143cf` | 2026-09-25 | no | no (1 of 1 lines absent) | KEPT |
| `regfresh/2026-09-25-sairnvet` | `df25c986a34d2555d3546f8691383df5146bcc93` | 2026-09-25 | no | no (6 of 6 lines absent) | KEPT |
| `regfresh/2026-09-25-sd-data` | `f9a1954e8b417d7b62fc5e37bce41056ce67b6d7` | 2026-09-25 | no | no (1 of 1 lines absent) | KEPT |
| `regfresh/2026-09-25-stonedesk` | `e96289a7aa12938b5ac01258e985764a6e8ea52f` | 2026-09-25 | no | no (2 of 3 lines absent) | KEPT |
| `regfresh/2026-09-26-sairnbiz` | `29d42a14b60aa37cfcceb34054832c42c25c6d3a` | 2026-09-26 | no | no (2 of 2 lines absent) | KEPT |
| `regfresh/2026-09-26-sairnbuild` | `2b2a410af708b18f47cd82a788f556350c6f1530` | 2026-09-26 | no | no (4 of 4 lines absent) | KEPT |
| `regfresh/2026-09-26-sairncare` | `134504cc202013738888f3a02907f217f29a81dc` | 2026-09-26 | no | no (1 of 1 lines absent) | KEPT |
| `regfresh/2026-09-26-sairncode` | `775c7fc34dc819feaf309db0c081d1c7c90d5dd3` | 2026-09-26 | no | **yes** (12/12 lines) | **DELETED** |
| `regfresh/2026-09-26-sairndesign` | `9d91c6ff443a80d8639293ff67c9b709f671555c` | 2026-09-26 | no | **yes** (2/2 lines) | **DELETED** |
| `regfresh/2026-09-26-sairngrounds` | `036ef49985a0dff51b7bfebc92575600a11882f6` | 2026-09-26 | no | no (1 of 1 lines absent) | KEPT |
| `regfresh/2026-09-26-sairnvet` | `b0f8147cc9060559ef17309ef0c9956eaf37edd2` | 2026-09-26 | no | **yes** (6/6 lines) | **DELETED** |
| `regfresh/2026-09-26-sd-data` | `416237c8788134a539c3c54a5ae6af367f93daa3` | 2026-09-26 | no | **yes** (3/3 lines) | **DELETED** |
| `regfresh/2026-09-26-stonedesk` | `1a82c3742e107427b07edeae48911ed2181845f7` | 2026-09-26 | no | no (3 of 3 lines absent) | KEPT |
| `regfresh/2026-09-28-sairnbiz` | `5e5ac711f0eb83944353e8dcbfc232d39ab63855` | 2026-09-28 | no | **yes** (5/5 lines) | **DELETED** |
| `regfresh/2026-09-28-sairnbuild` | `22a6320325c8ef569d2118a209580bc422446d9a` | 2026-09-28 | no | **yes** (6/6 lines) | **DELETED** |
| `regfresh/2026-09-28-sairncare` | `d0c0c2ed2724e847395f3d453b7978566e114f72` | 2026-09-28 | no | **yes** (2/2 lines) | **DELETED** |
| `regfresh/2026-09-28-sairnfreedom` | `75ae84d7634b02f819a1dc50e2e8bf22ae80da42` | 2026-09-28 | no | **yes** (5/5 lines) | **DELETED** |
| `regfresh/2026-09-28-sairnsenior` | `ede899d27a6332a2f68deff613510290cf52a5f2` | 2026-09-28 | no | **yes** (4/4 lines) | **DELETED** |
| `regfresh/2026-09-28-sairnvet` | `ac58622d45e7b7ead288c0885548b6a759c8b9ba` | 2026-09-28 | no | no (2 of 2 lines absent) | KEPT |
| `regfresh/2026-09-28-sd-data` | `5b3579a312484e9a6f617187c83103e89a4e96b0` | 2026-09-28 | no | no (4 of 4 lines absent) | KEPT |
| `regfresh/2026-09-28-stonedesk` | `04269b8a4c6808166c61893041c9c174a8151fa5` | 2026-09-28 | no | **yes** (3/3 lines) | **DELETED** |

## WHAT WAS ACTUALLY DELETED, AND WHEN — the column above was a PLAN

**The `DELETED` verdict above was written BEFORE any deletion ran**, which is
the order this document argues for and is also a thing a later reader can
misread as history. The deletion ran afterwards, and this section is the
record of it. The two are separated on purpose: a table that says DELETED
while the branch is still on the remote is the same class of claim as a status
report nobody checked.

**RE-VERIFIED AGAINST `origin/main` AS IT EXISTED AT DELETION TIME, not against
the read behind the table.** Main had moved by several commits in between. All
27 rows were re-derived by the same CONTENT test:

| | count |
|---|---|
| rows re-derived | **27** |
| verdicts that CHANGED on re-verification | **0** |
| in main by content — deletable | **12** |
| not in main by content — kept | **15** |

**A zero there is the interesting number, not a formality.** It says the
proposals whose content had reached main had not been re-broken by the
intervening commits, and it is the only thing that licensed acting on a table
written hours earlier.

### What the deletion found

| | count |
|---|---|
| local branches deleted | **5** |
| local branches already absent | **7** |
| remote branches deleted | **0** |
| remote branches already absent | **12** |

**THE REMOTE SIDE WAS ALREADY CLEAN AND THAT IS NOT A NO-OP RESULT.** The 15
branches still on `origin` are **exactly** the 15 the CONTENT test says to KEEP —
checked name by name, not by count. Every one of the 12 deletable branches was
already gone from the remote, so nothing of theirs was on `origin` to remove.
Seven of those twelve were also already gone locally. The exercise removed five
local refs; what it mainly established is that the remote and the content test
already agreed.

The five deleted locally: `regfresh/2026-09-28-sairnbiz`,
`-sairnbuild`, `-sairncare`, `-sairnfreedom`, `-sairnsenior`.

### Recoverability was CHECKED after the deletion, not assumed

All twelve tip shas were confirmed still resolvable in this clone
(`git cat-file -t <tip>` → `commit`) **after** the branch refs were removed.
Deleting a ref does not delete the commit; it makes it unreachable, and it stays
in the object store until a `gc` prunes it. So the recreate recipe at the top of
this file works today, and stops working at some future `git gc --prune`.

**THE FIRST VERSION OF THAT CHECK REPORTED ALL TWELVE AS `GONE` AND WAS WRONG.**
It ran `git cat-file` inside a `while read` loop fed from a file, and git
consumed the loop's stdin; the direct one-at-a-time check answered `commit` for
every one. Recorded because a false alarm about data loss, believed, is how a
deletion gets reverted and re-run — and because it is the same shape as every
other check in this repo that was measuring its own harness.

## What the KEPT branches still hold

Fifteen branches carry proposals whose lines are not in main. Thirteen are the
2026-09-25 and -26 proposals whose target cells have since moved, so they cannot
be merged as they stand — re-running `tools/register_freshness_propose.py`
re-proposes those drifts against the file as it exists now, which is the point
of the mechanism. Two are today's, and those hold real unapplied repoints on
`sv_mobilevet` and `sen_settings` that a conflict resolution set aside.

**Nothing here is urgent and nothing here is lost.** The drifts these branches
address are still counted in `tools/register_freshness_check.py`, which reads
**54 DRIFTED** as of this file.

---

# ADDENDUM 2026-10-05 (CC) — EVERY REMOTE BRANCH RECORDED, AND THE "19" DOES NOT EXIST

**The record is pushed BEFORE any deletion, which is the whole point of this
file.** Recreate any row below with:

```
git branch <name> <tip sha>
git push origin <name>
```

## THE INSTRUCTION SAID 19 STALE BRANCHES. MEASURED AT HEAD, THERE IS NO SET OF 19.

Counted, not quoted: **27 remote branches besides `main`.** No subset of them
comes to nineteen under any test applied here — not ancestry, not content, not
age, not `regfresh/*` membership. The earlier pass in this file recorded 27
`regfresh/*` tips and deleted 12, leaving **15 `regfresh/*`** plus **12 others**
that pass had never looked at. 15 + 12 = 27, and 19 matches neither half nor
their sum.

**So nothing was deleted on the strength of a figure that cannot be reproduced.**
This addendum records all 27 and deletes only what a test says is safe. If 19
names a real set from somewhere outside this repo, say which and it is one
command — the tips are now on record either way, which is the part that cannot
be undone later.

## The test, unchanged from the first pass, and now stricter

A branch is deletable only if **all three** hold:

1. its tip **is an ancestor** of `origin/main`;
2. it has **zero commits** not reachable from `origin/main`;
3. `git diff merge-base..tip` is **zero files** — nothing it proposes is absent.

The first pass used CONTENT alone because `tools/push_retry.py` rebases on every
contended push, so `regfresh/*` tips are not ancestors of anything even when
their text landed. That reasoning still holds for those 15. The three deletions
below satisfy **all three** tests, which is a stronger claim than that pass
could make about anything.

## Every remote branch at HEAD

| Branch | Tip sha | Date | Ancestor of `main` | Commits unique to it | Files it changes | Tip subject |
|---|---|---|---|---|---|---|
| `claude/cloud-research-competitive-vet-law` | `01450b601544c46be12876a8523ed6b8de58106e` | 2026-09-25 | yes | **0** | **0** | **DELETABLE** &mdash; docs(cloud-research): external competitive-gap audits for SAIRNvet and SAIRNlaw |
| `claude/cloud-research-sairncare` | `74e029a5f3736492e59c8ac19486c0d85a633813` | 2026-09-25 | no | **1** | **1** | KEEP &mdash; docs(cloud-research): external competitive-gap audit — SAIRNcare |
| `claude/cloud-research-sairndental` | `49a7c5bb29f3ca1d316811aa2712b1569307dcbd` | 2026-09-25 | no | **1** | **1** | KEEP &mdash; docs(cloud-research): external competitive-gap audit — SAIRNdental |
| `claude/cloud-research-sairnroofing` | `b9a37c9f09b822285c44bb90c0c86ae781334197` | 2026-09-25 | no | **1** | **1** | KEEP &mdash; docs(cloud-research): external competitive-gap audit — SAIRNroofing |
| `claude/cloud-research-trades-mechanical` | `80b135695f5b41048b57e776ba5059a38df4f215` | 2026-09-25 | no | **3** | **2** | KEEP &mdash; docs(cloud-research): tunnel-vision re-pass — CARB R3, insurance parity, franchise det |
| `claude/jolly-gauss-uropwz` | `f295cabcbebde704d9bd5353b8841b2a89a93343` | 2026-09-24 | no | **1** | **1** | KEEP &mdash; docs(cloud-research): SOC 2 Trust Services Criteria evidence map |
| `claude/stonedesk-div-balance-dedup-6mju2o` | `07dd39f2429d3575b26da1a1012be768fc2a1bd7` | 2026-07-22 | yes | **0** | **0** | **DELETABLE** &mdash; cleanup: remove dead trailing content after </html> |
| `claude/wizardly-ride-wtun13` | `aba84c983e6173f025a92a1ccf1d4b8f69f21d00` | 2026-09-27 | no | **15** | **14** | KEEP &mdash; docs(cloud-research): SAIRNgrounds external competitive-gap audit, five lenses |
| `fourth-2026-09-16-g7-rebase-merge` | `0b9237cae3fd706892fa507e8a7ab813ba379f83` | 2026-09-16 | no | **3** | **4** | KEEP &mdash; docs(active-work): fourth -- rebase merge class, the two probe defects in my own work, L |
| `fourth/sairnvet-external-gap-audit-2026-09-26` | `f3cfb56eaeda9782bfef658e0e83e3bfe5ba9a72` | 2026-09-26 | no | **1** | **1** | KEEP &mdash; docs(cloud-research): SAIRNvet external gap audit -- the three axes 09-25 could not surv |
| `master` | `2c0cbdb8778b44d09808fbd32998b13093f217c0` | 2026-07-23 | no | **1** | **1** | KEEP &mdash; Add Model Selection guidance to CLAUDE.md |
| `regfresh/2026-09-25-sairnbiz` | `ec52e2daa9c9548e3e239a6a4d4e5fc7d9a83a0e` | 2026-09-25 | no | **1** | **1** | KEEP &mdash; docs(tiers): repoint 3 drifted citation(s) in sairnbiz -- PROPOSAL, line numbers only |
| `regfresh/2026-09-25-sairncode` | `d4b41427183fa316baaf236793b0e2a8b919ccbd` | 2026-09-25 | no | **1** | **1** | KEEP &mdash; docs(tiers): repoint 14 drifted citation(s) in sairncode -- PROPOSAL, line numbers only |
| `regfresh/2026-09-25-sairndesign` | `952b7ea8b7dd34539ea5ff973c0190ca34fcb4d4` | 2026-09-25 | no | **1** | **1** | KEEP &mdash; docs(tiers): repoint 6 drifted citation(s) in sairndesign -- PROPOSAL, line numbers only |
| `regfresh/2026-09-25-sairnfreedom` | `8b97f86062281c410e8569d491c86395827bf161` | 2026-09-25 | no | **1** | **1** | KEEP &mdash; docs(tiers): repoint 5 drifted citation(s) in sairnfreedom -- PROPOSAL, line numbers onl |
| `regfresh/2026-09-25-sairnsenior` | `ae6ea3dbcc6fba7a0931411ca318d79d0d0143cf` | 2026-09-25 | no | **1** | **1** | KEEP &mdash; docs(tiers): repoint 1 drifted citation(s) in sairnsenior -- PROPOSAL, line numbers only |
| `regfresh/2026-09-25-sairnvet` | `df25c986a34d2555d3546f8691383df5146bcc93` | 2026-09-25 | no | **1** | **1** | KEEP &mdash; docs(tiers): repoint 6 drifted citation(s) in sairnvet -- PROPOSAL, line numbers only |
| `regfresh/2026-09-25-sd-data` | `f9a1954e8b417d7b62fc5e37bce41056ce67b6d7` | 2026-09-25 | no | **1** | **1** | KEEP &mdash; docs(tiers): repoint 1 drifted citation(s) in sd-data -- PROPOSAL, line numbers only |
| `regfresh/2026-09-25-stonedesk` | `e96289a7aa12938b5ac01258e985764a6e8ea52f` | 2026-09-25 | no | **1** | **1** | KEEP &mdash; docs(tiers): repoint 4 drifted citation(s) in stonedesk -- PROPOSAL, line numbers only |
| `regfresh/2026-09-26-sairnbiz` | `29d42a14b60aa37cfcceb34054832c42c25c6d3a` | 2026-09-26 | no | **1** | **1** | KEEP &mdash; docs(tiers): repoint 2 drifted citation(s) in sairnbiz -- PROPOSAL, line numbers only |
| `regfresh/2026-09-26-sairnbuild` | `2b2a410af708b18f47cd82a788f556350c6f1530` | 2026-09-26 | no | **1** | **1** | KEEP &mdash; docs(tiers): repoint 8 drifted citation(s) in sairnbuild -- PROPOSAL, line numbers only |
| `regfresh/2026-09-26-sairncare` | `134504cc202013738888f3a02907f217f29a81dc` | 2026-09-26 | no | **1** | **1** | KEEP &mdash; docs(tiers): repoint 1 drifted citation(s) in sairncare -- PROPOSAL, line numbers only |
| `regfresh/2026-09-26-sairngrounds` | `036ef49985a0dff51b7bfebc92575600a11882f6` | 2026-09-26 | no | **1** | **1** | KEEP &mdash; docs(tiers): repoint 1 drifted citation(s) in sairngrounds -- PROPOSAL, line numbers onl |
| `regfresh/2026-09-26-stonedesk` | `1a82c3742e107427b07edeae48911ed2181845f7` | 2026-09-26 | no | **1** | **1** | KEEP &mdash; docs(tiers): repoint 6 drifted citation(s) in stonedesk -- PROPOSAL, line numbers only |
| `regfresh/2026-09-28-sairnvet` | `ac58622d45e7b7ead288c0885548b6a759c8b9ba` | 2026-09-28 | no | **1** | **1** | KEEP &mdash; docs(tiers): repoint 2 drifted citation(s) in sairnvet -- PROPOSAL, line numbers only |
| `regfresh/2026-09-28-sd-data` | `5b3579a312484e9a6f617187c83103e89a4e96b0` | 2026-09-28 | no | **1** | **1** | KEEP &mdash; docs(tiers): repoint 4 drifted citation(s) in sd-data -- PROPOSAL, line numbers only |
| `worktree-stonedesk-chamfered-corners` | `1d53e758ae67c14216baaf53b890b7d43bc57005` | 2026-08-13 | yes | **0** | **0** | **DELETABLE** &mdash; docs: plan -- SAIRNlaw AI Chain of Custody, server-side capture (Gap 1 fix) |

TOTAL 27; deletable 3

## Result

| | count |
|---|---|
| remote branches besides `main` | **27** |
| recorded here for the first time | **12** |
| satisfy all three containment tests — **DELETED** | **3** |
| carry content not in `main` — **KEPT** | **24** |

### The three deleted, and why each is genuinely empty

| Branch | Why nothing is lost |
|---|---|
| `claude/cloud-research-competitive-vet-law` | Tip is an ancestor of `main`; its two cloud-research audits are in `docs/cloud-research/` today |
| `claude/stonedesk-div-balance-dedup-6mju2o` | 2026-07-22. `cleanup: remove dead trailing content after </html>` — landed, ancestor, empty diff |
| `worktree-stonedesk-chamfered-corners` | 2026-08-13. A plan document that landed; ancestor, empty diff |

### Four of the 24 KEPT are kept for a reason beyond the test, stated so nobody deletes them later

* **`claude/wizardly-ride-wtun13`** — **15 unique commits, 14 files. This is the
  open PR SAIRN1/SAIRN#18 cloud-research lane.** Live work, not residue.
* **`regfresh/2026-09-28-sairnvet`** and **`regfresh/2026-09-28-sd-data`** — the
  two whose merges conflicted on `sv_mobilevet` and `sen_settings` and were
  resolved by taking `main`'s newer text. Part of what they propose is genuinely
  not in `main`. Same two the first pass kept, re-confirmed here.
* **`master`** — one commit ahead, and `CLAUDE.md` calls it the stale branch.
  **Deliberately not deleted:** `tools/git_push_master_guard.py` exists to refuse
  pushes to it, so removing the branch would leave a guard with no subject and a
  documented fact with nothing behind it. Deleting the default-branch-adjacent
  ref is also Michael's call, not a cleanup rider.

### Recoverability checked AFTER the deletion, not assumed

Each deleted tip was confirmed still resolvable in this clone with
`git cat-file -t <tip>` one at a time — **not** in a `while read` loop, because
the first pass's version of this check fed the loop from a file, git ate its
stdin, and it reported all twelve as `GONE` when none were. A false alarm about
data loss, believed, is how a deletion gets reverted and re-run.

**BLIND SPOTS: 3.** (1) The three tests prove nothing is lost *relative to
`main`* — a branch whose content was deliberately abandoned looks identical to
one whose content landed, and this file cannot tell those apart. (2) The 24 KEPT
branches are not audited for whether anyone still wants them; "has unique
content" is not "is wanted". (3) Tips stay recoverable only until some future
`git gc --prune` reaches them, and nothing schedules or monitors that.

---

## ADDENDUM 2026-10-05 (CC) — one more branch-only audit LANDED, tip recorded first

`claude/cloud-research-sairncare` tip **`74e029a5f3736492e59c8ac19486c0d85a633813`**, 1 unique commit, 1 file.

**IT WAS THE LAST BRANCH-ONLY COMPETITIVE AUDIT AND PR #18 DID NOT CONTAIN IT.**
That PR merged twelve audits and this branch was not among them, so SAIRNcare's
audit stayed invisible to anyone reading `main` for a further eight days — the
exact finding the PR #18 merge was supposed to close, surviving in one branch
nobody checked against the app list.

**FOUND BY DERIVING THE APP SET RATHER THAN TRUSTING THE INVENTORY.** The
2026-09-29 inventory tracked **17** apps and I had reported "every app now has
an audit" on the strength of closing its three gaps. `git ls-files '*.html'` at
the repo root returns **22**, and cross-referencing every name against
`docs/` filenames surfaced `sairncare` as having no audit ON MAIN.

The doc is landed on `main` (411 lines) after re-deriving all nine of its
internal code citations at HEAD — all nine resolve. **The branch is NOT
deleted**: its tip is recorded here, and deleting it is a separate decision
from landing its content.

**THE OTHER FOUR of the 22 are not products** and are deliberately not audited:
`sairndental-book` (18KB, "Book an Appointment"), `sairndental-complaint`
(10KB, "Patient Feedback"), `stonedesk-catalog` (20KB, "Slab Catalog") and
`stonedesk-intake` (19KB, "Project Intake") are public-facing forms with no
licence gate. `stonedesk-hr` (99KB, licence-gated) IS a real module and is
covered by StoneDesk's own audit.

**BLIND SPOTS: 2.** (1) The 22 figure is root-level `*.html` and excludes
`archive/`; an app living elsewhere would still be missed. (2) "Covered by
StoneDesk's audit" for `stonedesk-hr` is an assertion about scope that I did
not verify by reading that audit.
