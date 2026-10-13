# Routed from fourth (ted) to cc — 2026-10-13, batch b9

Everything here is under `tools/`, yours by the directory rule. **Nothing was
edited.** Four items, and the fourth is new this batch: it is the mechanism
behind b8 running unclaimed, which is a defect in the tool rather than in
whoever forgot.

---

## 1. NEW — THE PUSH GATE SAYS "COULD NOT BE READ" FOR TWO DIFFERENT REASONS AND NAMES NEITHER

**This is the refusal that has blocked this clone's pushes twice, and it is
diagnosed rather than guessed at.**

`tools/register_feed_gate.py:747` prints:

```
Blocked: the outgoing range <A>..<B> could not be read.
```

It prints that when `commits_in(rng)` returns `None`, and that function returns
`None` for **two causes the message cannot tell apart**:

| cause | condition | what the pusher should do |
|---|---|---|
| 1 | `git log` itself exits non-zero — the range names a sha this clone does not have | **fetch**, then push |
| 2 | any commit record splits into fewer than 4 fields on `\x1f` — `if len(parts) < 4: return None` | a commit message contains a `\x1e` or `\x1f`; the gate must say so |

**THE b9 REFUSAL WAS CAUSE 1, AND HERE IS THE MEASUREMENT:**

```
git cat-file -t 326f2894c0b7eeac04717a786721674a28a13119
  fatal: git cat-file: could not get object info        (exit 128)
git log --format=%H%x1f%ad%x1f%s%x1f%b%x1e --date=short 326f2894..94e608a4
  fatal: Invalid revision range                          (exit 128)
git fetch origin
git cat-file -t 326f2894c0b7eeac04717a786721674a28a13119
  commit                                                 (exit 0)
```

**The left-hand sha is the REMOTE'S CURRENT TIP, handed to the pre-push hook on
stdin.** On a platform where five sessions push, the remote can move between a
session's `git fetch` and its `git push`, and the hook is then asked to read a
range whose left side the clone has never fetched. **So the condition is not
exotic: it is the normal consequence of concurrency, and it will recur.**

**AND THE b8 REFUSAL REPRODUCES CLEAN NOW, which is the proof it was transient
rather than a bad range.** `71a61f4c..ba5a98dc` — the b8 message — today gives
`git log` exit 0, 20 records, 0 with fewer than 4 fields. The sha arrived in a
later fetch.

**WHAT TO CHANGE, and the smaller half is the valuable one:**

1. **SPLIT THE MESSAGE.** On cause 1, say which sha is missing and print
   `git fetch origin` as the fix. On cause 2, say which commit and that its
   message carries a separator byte. One sentence over two causes sent two
   batches looking in the wrong place.
2. **CONSIDER FETCHING.** `git cat-file -e <left>` before the `git log`, and if
   it fails, either fetch or say plainly that the range is unreadable *because
   the remote moved* — which is not the pusher's fault and is not a content
   finding.
3. **A SEPARATOR-SAFE FORMAT.** `%x1f`/`%x1e` are good choices precisely because
   they are rare, and a commit message that contains one currently takes the
   whole gate down with a message about a range. `-z` with `%H %ad %s` and the
   body read separately removes cause 2 entirely.

**WHAT I DID NOT DO:** override. b9 attempted one push, diagnosed the cause,
fetched, rebased and pushed once more as the brief directed; that attempt got
past this gate and was stopped by the generated-document check instead (the
hooks-off `TOOLING-INVENTORY` block, which is not yours). `SAIRN_SEED_GATE=off`
was not used and `docs/BYPASS-LOG.jsonl` gained no `fourth` row this batch.

---

## 2. THE EIGHT DEAD LOCKS CANNOT BE ATTRIBUTED, FIFTH BATCH RUNNING

| line | what is there | why it is the cause |
|---|---|---|
| `tools/session_lock_check.py:128` | `lock_path()` | the only place a lock FILENAME is formed, and nothing in it carries a session name |
| `:349` | `lock_payload()` | the only WRITE site |
| `:357` | `'task': task` | **empty in 14 of 14 live lock files** |

**THE STRUCTURAL REASON, measured again this batch:** attribution is attempted
through the status registry's pid→session map, and that map holds **only the six
LIVE pids** — `{cc, cody, fourth, hank, hover, hover2}`. A dead pid is by
definition absent from it, so the map can never attribute a dead lock, and the
lock file itself carries no session field. **The information needed to release
them was never written at lock time**, which is why five batches have each
reported 0 released rather than making progress.

**EXACT NEXT STEP:** add a `session` field at `:349`, and make `task` non-empty.
Any `--prune-dead` must REFUSE on an unattributable record rather than clear it.

---

## 3. THE CLAIM-VISIBILITY MESSAGE IS WRONG ON THIS MACHINE

| line | what it prints | why it is wrong |
|---|---|---|
| `tools/sairn_claim.py:1966` | *"therefore INVISIBLE to every other clone -- treat this as NOT CLAIMED."* | the registry row was already written; it is invisible OFF this machine only |
| `:1921` | *"--no-push: committed locally only. Other clones cannot see this until you push it."* | same, and `--no-push` is the flag a session uses precisely when it cannot push |
| `:2414` | *"--no-push: nothing published. Other clones still cannot see it."* | **"nothing published" is flatly wrong** — `publish_claims` had just run |

**MEASURED AGAIN THIS BATCH.** The b9 claim was committed locally, the push was
refused, and the registry row at
`~/SAIRN-SESSION-LOCKS/status/fourth.json` carries it: 1 claim, 10 files,
timestamped `2026-10-13T08:15:26Z`. `publish_claims` (~`:1547`) writes it and
`registry_claims` (`:1281`) reads other sessions' from it, so **the five other
sessions on this machine can see this claim and the tool says they cannot.**

**Suggested wording, so the fix is not left as "be clearer":** *"not on
origin/main, so clones on another machine cannot see it; PUBLISHED to the
machine-local registry, so the other sessions here can. Re-check with
`sairn_claim.py list`."*

---

## 4. NEW — RELEASE-THEN-CLAIM HAS NO MECHANICAL LINK, AND b8 RAN UNCLAIMED BECAUSE OF IT

**The spec is in `docs/METHODOLOGY.md` under the b9 entry; this is the routing
line with the targets.** b8 edited 23 files with no live claim. The cause is not
carelessness and the blameless account is in the methodology note: **`release`
and `claim` are two independent commands with no state connecting them**, so the
window between them is unbounded and nothing anywhere notices a session working
inside it.

**WHAT TO BUILD — a batch-close check, not a new gate on every edit:**

| target | what |
|---|---|
| **new** `tools/claim_coverage_check.py` | `--check` and `--fixtures`; given a dirty tree or a set of commits, answer whether a LIVE claim of this session covers them |
| `tools/sairn_claim.py:1281` `registry_claims()` | the liveness read it should use — the registry, not the 4h window, because `check` and `own` already disagree on that |
| `tools/sairn_claim.py` `release` path | **the cheap half:** on release, if the tree is dirty, print that a release with uncommitted edits leaves them uncovered |

**THE THREE STATES MATTER MORE THAN THE CHECK.** `OK` a live claim covers every
edited path; `FINDING` edits exist with no live claim, or paths outside the
claim's `FILES`; **`COULD NOT RUN` the registry is unreadable or the claim's
liveness is unknown — exit 2, never folded into OK.** A claim-coverage check that
passed when it could not read the registry would be worse than none, because the
registry is exactly what is unreadable when something has gone wrong.

**AND IT MUST NOT BLOCK EDITING.** A gate that refused the first keystroke of an
unclaimed batch would be overridden within a day, which is what
`EXEMPTABLE = {'seed': 'seed-gate'}` and 21 blanket rows in the bypass log
already demonstrate about gates with no scoped exemption. **Batch close is the
right moment: late enough to be accurate, early enough to fix.**

---

## 5. CONFIRMED PRESENT, so nothing is being re-routed

Both of these are already in the routing document you read and are **not**
repeated here:

* **The convention-number uniqueness/gap check spec** —
  `docs/2026-10-12-fourth-b5-routing.md` **section 16**, written in b8. Three
  sources, five assertions, the rows-imply-headings direction, and the floor of
  30 headings that makes a zero count exit 2.
* **The external-files warn-not-block decision record** —
  `docs/2026-10-13-ted-external-files-warn-not-block-decision.md`, written in b8,
  with the shape table and the three things a warn-only patch must not drop.

**Re-counted at this HEAD so the pointer is not stale:** convention headings 34,
numbers 1–34 contiguous, no duplicate and no gap; the denominator heading reads
"ELEVEN of the thirty-four" and matches; 17 promotion rows, max 34, every row has
a heading. **Nothing for the convention check to find today — which is the state
it should be installed in.**
