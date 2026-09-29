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
