# A defect-register row cites a SHA it is about to change — proposal, not a fix

**Written 2026-10-05 (Fourth). PROPOSAL ONLY. No tool changed.**

This is the durable fix asked for after I hit the loop twice in one batch and
shipped a workaround both times. It names the problem precisely, shows why the
obvious repair is mathematically impossible, and proposes the one that works —
plus a cheap interim that costs nothing and stops the next session
rediscovering this from scratch.

---

## 1. The loop, exactly

A register row cites a commit SHA. The intended workflow is "fix it, record
it, one commit". That workflow cannot terminate:

| step | what happens |
|---|---|
| 1 | commit the fix → sha `A` |
| 2 | `defect_register.py --add --commit A` → the row cites `A`, file is dirty |
| 3 | `git commit --amend` to fold the row in → **the tree changed, so the sha is now `B`** |
| 4 | `post-rewrite` fires, re-seats the row `A → B`, leaves the file dirty |
| 5 | amend again → sha `C`. Re-seat `B → C`. Dirty again. **Go to 3.** |

Observed live on 2026-10-05 across `334f8a68 → b62b959d → 261c62e2 →
370131d9 → 0aafb15a → d8f48ddb → 159b5e73`, every one a re-seat of the same
single row.

**The re-seat machinery is not at fault and is not what this proposes to
change.** `post-rewrite` + `--reseat` are well-built, deliberately refuse to
stage on the author's behalf, and deliberately never fail the rebase. They do
exactly what they claim. The loop is upstream of them.

## 2. Why "just compute the sha it will have" is impossible

The natural repair — work out the post-amend sha and write *that* into the row —
has no solution. A commit's sha is a hash of its tree; the tree contains
`docs/defect-density-register.json`; the row inside that file would contain the
sha. **A fixed point would be a value whose SHA-1 is a function of a file
containing that same value.** Finding one is a preimage attack, not an
engineering task.

Stating this explicitly because it is the first idea everyone has, including
me, and it reads as merely fiddly rather than as impossible.

## 3. What I did instead, twice, and why it is a workaround and not a fix

The row landed in a **child** commit citing its parent. Amending a child never
moves its parent, so it converges on the first try.

It works, and it has three real costs:

1. **The record is not in the commit it records.** Anyone reading the fix
   commit alone sees no register row and has to know to look at the next one.
2. **It needs a `no-defect-record:` escape in the child**, which is the field
   the register itself warns can decay into meaning nothing.
3. **The prose cannot name a sha.** I wrote one in, and it went stale across
   four rebases in ten minutes before I removed it. The row re-seats; prose
   does not.

## 4. PROPOSED: a stable change identity, so the row never cites a moving target

Give every commit an identity that survives rewriting, and have the row cite
**that**. This is Gerrit's `Change-Id` and it exists for exactly this reason.

```
fix(sairnsenior): a backwards clock pair billed NEGATIVE hours

...body...

Change-Id: I7b3f1c2a9e4d5068
```

* A `commit-msg` hook generates the trailer once, on first commit, from
  `(author, timestamp, tree)` — any collision-resistant value will do, it only
  has to be unique and *not* derived from the sha.
* `git rebase` and `git commit --amend` preserve the message, therefore the
  trailer, therefore the identity. **Rebasing cannot invalidate it.**
* `defect_register.py --add` records `change_id` as the authoritative key and
  keeps `commit` as an advisory, auto-re-seated convenience field.
* The push gate's "no register record cites it" check resolves `HEAD`'s
  `Change-Id` instead of its sha.

**The amend loop disappears**, because the value written into the file is not
a function of the file. Step 3 above changes the sha; the row does not care.

### What it costs, stated before anyone agrees to it

* **A new `commit-msg` hook on every clone.** This repo already ships
  `.githooks/`, so the mechanism exists, but five clones have to pick it up and
  a clone that misses it produces commits with no identity. The gate would have
  to treat a missing trailer as COULD NOT TELL, not as a pass.
* **439 existing rows have no `change_id`.** They should NOT be backfilled —
  a synthesised identity for a historical commit is a fabricated key. The field
  is optional, and `--check` reports the two populations separately rather than
  blending them.
* **A rebase that drops a commit entirely** still orphans its row. The
  `change_id` tells you *which* change went missing, which is strictly more
  than a dead sha does, but it does not resolve it.
* It is **one more thing in the commit message**, and this repo's messages are
  already long.

## 5. INTERIM, costing nothing: make the converging path the documented one

Whatever is decided about §4, the cheap half should land regardless, because
today the loop is rediscovered by each session at the cost of several rebases:

1. **`defect_register.py --add` should detect the shape and say so.** When
   `--commit` resolves to `HEAD` and `HEAD` is not on any remote branch, print:

   > This row cites HEAD. Folding it in with `--amend` will change that sha and
   > re-seat the row, and that loop does not terminate. Commit the row
   > separately — amending a child never moves its parent.

   One print statement. It needs no schema change and no hook.

2. **The push gate should accept a row citing `HEAD~1`** when `HEAD` is a
   register-only commit, without needing the `no-defect-record:` escape. The
   escape is for "this is not a defect"; "the record is in the very next
   commit" is a different statement and should not borrow the same field.

## 6. What I am NOT proposing

* **Auto-staging in `post-rewrite`.** The hook's own header argues against it:
  a hook that commits on someone's behalf puts their name on a change they did
  not read. That reasoning holds, and auto-staging would not converge anyway —
  the amend that stages it is itself another rewrite.
* **Dropping the sha from the row.** It is the thing a human actually follows.
  The proposal demotes it to advisory, not absent.
* **Backfilling historical rows.** See §4.

## 7. Where the decision sits

`tools/defect_register.py` is unclaimed as of this writing, but the
`commit-msg` hook in §4 touches every clone's workflow, so it is a platform
decision rather than one session's. The §5 interim is small enough to belong to
whoever next touches the register.
